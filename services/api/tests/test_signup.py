"""Sign-up, class codes, and the child-claiming step.

A class code says which classroom, never which child, so the interesting tests are about
what a code does NOT get you: someone else's child, another class's roster, or a way in
after the teacher has changed the code.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import classcode
from app.main import app
from app.routers.login import check_password, hash_password
from app.storage import store

TEACHER = {"X-Role": "teacher", "X-User-Id": "teacher-01"}
CODE = "BRIGHT4"


@pytest.fixture
def world():
    """An in-memory classroom so sign-ups never write to the demo's own state."""
    real = store.read
    data = {
        "classes": [{"id": "class-4a", "name": "Class 4A", "teacher_id": "teacher-01", "code": CODE}],
        "parents": [], "accounts": [], "links": [], "audit": [],
    }
    with (
        patch.object(store, "read", side_effect=lambda n: data[n] if n in data else real(n)),
        patch.object(store, "append", side_effect=lambda n, row: data[n].append(row)),
        patch.object(store, "write_all", side_effect=lambda n, rows: data.__setitem__(n, rows)),
        patch.object(store, "upsert", side_effect=lambda n, row, key="id": data.__setitem__(
            n, [row if r.get(key) == row[key] else r for r in data[n]])),
    ):
        yield TestClient(app), data


def signup(client, email="new@example.com", code=CODE, password="a-good-password"):
    return client.post("/auth/signup", json={
        "name": "Alex Hulet", "email": email, "password": password, "class_code": code,
    })


def test_sign_up_joins_the_class_the_code_belongs_to(world):
    client, data = world
    response = signup(client)
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "parent" and body["needs_child"] is True and body["class_name"] == "Class 4A"
    # The family is in the classroom but linked to no child yet.
    assert data["parents"][0]["pending_class_id"] == "class-4a"
    assert data["links"] == []


def test_a_typed_code_survives_spaces_dashes_and_lowercase(world):
    client, _ = world
    assert signup(client, code=" bright-4 ").status_code == 201


def test_an_unknown_code_gets_in_nowhere(world):
    client, data = world
    assert signup(client, code="ZZZZZZZ").status_code == 404
    assert data["accounts"] == []


def test_the_same_email_cannot_sign_up_twice(world):
    client, _ = world
    assert signup(client).status_code == 201
    assert signup(client).status_code == 409


def test_a_chosen_password_is_hashed_not_stored(world):
    client, data = world
    signup(client, password="correct-horse-battery")
    stored = data["accounts"][0]["password"]
    assert "correct-horse-battery" not in stored
    assert stored.startswith("pbkdf2$")
    assert check_password(stored, "correct-horse-battery")
    assert not check_password(stored, "correct-horse-batteryX")


def test_seeded_demo_logins_still_work_alongside_hashed_ones():
    # Judges read the demo passwords off the screen, so those stay plaintext on purpose.
    assert check_password("otter123", "otter123")
    assert not check_password("otter123", "nope")
    assert check_password(hash_password("otter123"), "otter123")


def test_a_short_password_is_refused(world):
    client, _ = world
    assert signup(client, password="short").status_code == 422


def test_claiming_a_child_outside_the_joined_class_is_refused(world):
    client, data = world
    parent_id = signup(client).json()["user_id"]
    headers = {"X-Role": "parent", "X-User-Id": parent_id}
    assert client.post("/parent/join", headers=headers, json={"student_id": "student-99"}).status_code == 403
    assert client.post("/parent/join", headers=headers, json={"student_id": "nobody"}).status_code == 403
    assert data["links"] == []


def test_choosing_a_child_links_them_once_and_closes_the_offer(world):
    client, data = world
    parent_id = signup(client).json()["user_id"]
    headers = {"X-Role": "parent", "X-User-Id": parent_id}

    assert client.get("/parent/join", headers=headers).json()["needs_child"] is True
    assert client.post("/parent/join", headers=headers, json={"student_id": "student-01"}).status_code == 200
    assert data["links"] == [{"parent_id": parent_id, "student_id": "student-01"}]

    # The roster is gone the moment they have a child; it is not a browsable class list.
    after = client.get("/parent/join", headers=headers).json()
    assert after["needs_child"] is False and after["candidates"] == []
    assert client.post("/parent/join", headers=headers, json={"student_id": "student-02"}).status_code == 409


def test_a_new_family_still_cannot_read_another_familys_child(world):
    client, _ = world
    parent_id = signup(client).json()["user_id"]
    headers = {"X-Role": "parent", "X-User-Id": parent_id}
    client.post("/parent/join", headers=headers, json={"student_id": "student-01"})
    assert client.get("/parent/children/student-02/progress", headers=headers).status_code == 403


def test_rotating_the_code_shuts_the_old_one_out(world):
    client, data = world
    fresh = client.post("/teacher/class-code/rotate", headers=TEACHER).json()["code"]
    assert fresh != CODE and len(fresh) == classcode.LENGTH
    assert data["classes"][0]["code"] == fresh
    assert signup(client, code=CODE).status_code == 404
    assert signup(client, code=fresh).status_code == 201


def test_generated_codes_avoid_characters_people_confuse():
    for _ in range(50):
        assert not (set(classcode.generate()) & set("O0I1L"))


def test_only_a_teacher_sees_or_changes_the_class_code(world):
    client, _ = world
    parent_id = signup(client).json()["user_id"]
    for headers in ({"X-Role": "parent", "X-User-Id": parent_id},
                    {"X-Role": "student", "X-User-Id": "student-01"}):
        assert client.get("/teacher/class-code", headers=headers).status_code == 403
        assert client.post("/teacher/class-code/rotate", headers=headers).status_code == 403
