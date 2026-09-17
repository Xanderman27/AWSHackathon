"""A family update is the narrowest audience in the product: one child's guardians.

Where the class blog deliberately reaches every family in the room, these tests pin the
boundaries that this feature does not relax — another family, a student, a learner outside the
teacher's own class, and a guessed update id.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import store
from authhelp import auth

TEACHER = auth("teacher", "teacher-01")
PARENT = auth("parent", "parent-01")       # linked to student-01 (Sam)
OTHER_PARENT = auth("parent", "parent-02")  # linked to student-02 (Ava)
STUDENT = auth("student", "student-01")

NOTE = {
    "student_id": "student-01",
    "headline": "A rough start after lunch",
    "note": "Sam asked for the quiet corner and came back to finish. Nothing to worry about.",
    "happened_on": "2026-09-16",
}


@pytest.fixture
def client(monkeypatch):
    """Writes go to a list, so a test never leaves a note in the running demo's state."""
    written: list[dict] = []
    real_read = store.read

    def read(name):
        return [*real_read(name), *[r for r in written if r.get("_c") == name]] if name == "family_updates" \
            else real_read(name)

    monkeypatch.setattr(store, "append",
                        lambda name, row: written.append({**row, "_c": name}) if name == "family_updates" else None)
    yield TestClient(app)


def send(client, **overrides):
    return client.post("/teacher/family-updates", headers=TEACHER, json={**NOTE, **overrides})


def test_a_teacher_writes_home_and_is_told_who_it_reached(client):
    response = send(client)
    assert response.status_code == 201
    body = response.json()
    assert body["student_name"] == "Sam"
    # The teacher is shown the actual guardians, not a count, so "who will read this" is never a guess.
    assert body["sent_to"] and all(isinstance(name, str) for name in body["sent_to"])
    assert body["seen"] is False


def test_a_teacher_cannot_write_about_a_learner_who_is_not_theirs(client):
    # Same answer as a learner who does not exist: an id probe must not reveal the roster.
    assert send(client, student_id="student-99").status_code == 404


def test_a_parent_cannot_write_one(client):
    assert client.post("/teacher/family-updates", headers=PARENT, json=NOTE).status_code == 403


def test_a_family_reads_only_its_own_childs_updates(client):
    mine = client.get("/parent/family-updates", headers=PARENT)
    assert mine.status_code == 200
    assert all(row["student_id"] == "student-01" for row in mine.json()["updates"])

    theirs = client.get("/parent/family-updates", headers=OTHER_PARENT).json()["updates"]
    assert all(row["student_id"] == "student-02" for row in theirs)


def test_a_student_cannot_reach_the_feed_at_all(client):
    # A note that says the day was hard is written for an adult.
    assert client.get("/parent/family-updates", headers=STUDENT).status_code == 403


def test_marking_another_familys_update_read_is_a_404(client):
    seeded = client.get("/parent/family-updates", headers=PARENT).json()["updates"]
    if not seeded:
        pytest.skip("no seeded update to aim at")
    target = seeded[0]["id"]
    assert client.post(f"/parent/family-updates/{target}/read", headers=OTHER_PARENT).status_code == 404


def test_a_guessed_update_id_is_a_404(client):
    assert client.post("/parent/family-updates/upd-doesnotexist/read", headers=PARENT).status_code == 404
    assert client.delete("/teacher/family-updates/upd-doesnotexist", headers=TEACHER).status_code == 404
