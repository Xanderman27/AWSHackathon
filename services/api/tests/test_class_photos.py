"""Classroom photos are shared with every family in the class, by product decision. These
tests pin the boundaries that decision does NOT relax: another class, a student, a guessed
filename, and anything a parent might infer about another family's child."""

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.blobs import LocalBlobs, check_name
from app.main import app
from app.storage import store

TEACHER = {"X-Role": "teacher", "X-User-Id": "teacher-01"}
PARENT = {"X-Role": "parent", "X-User-Id": "parent-01"}
STUDENT = {"X-Role": "student", "X-User-Id": "student-01"}

# Smallest thing a PNG decoder will accept.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


@pytest.fixture
def client(tmp_path):
    """Route uploads to a temp folder so tests never touch the demo's own photos."""
    with patch.object(store, "blobs", LocalBlobs(tmp_path)):
        yield TestClient(app)


def upload(client, caption="Fraction wall day", rows=None):
    with patch.object(store, "append", side_effect=lambda name, row: rows.append(row) if rows is not None else None):
        return client.post(
            "/teacher/class-photos", headers=TEACHER,
            files={"file": ("moment.png", io.BytesIO(PNG), "image/png")},
            data={"caption": caption, "taken_on": "2026-09-16"},
        )


def test_a_teacher_uploads_and_the_class_families_see_it(client):
    rows = []
    response = upload(client, rows=rows)
    assert response.status_code == 201
    body = response.json()
    assert body["caption"] == "Fraction wall day"
    # The stored filename is ours and never leaves the server.
    assert "filename" not in body and "uploaded_by" not in body

    stored = next(row for row in rows if row.get("id", "").startswith("photo-"))
    with patch.object(store, "read", side_effect=lambda n: [stored] if n == "class_photos" else store_read(n)):
        assert [p["id"] for p in client.get("/parent/class-photos", headers=PARENT).json()] == [stored["id"]]
        assert client.get(f"/class-photos/{stored['id']}/file", headers=PARENT).status_code == 200


store_read = store.read


def test_a_parent_cannot_see_photos_from_a_class_their_child_is_not_in(client):
    other = {"id": "photo-other", "class_id": "class-9z", "filename": "x.png",
             "content_type": "image/png", "caption": "Another class", "taken_on": "",
             "uploaded_by": "teacher-99", "uploaded_by_name": "Someone", "uploaded_at": "2026-09-16T00:00:00+00:00"}
    with patch.object(store, "read", side_effect=lambda n: [other] if n == "class_photos" else store_read(n)):
        assert client.get("/parent/class-photos", headers=PARENT).json() == []
        # Knowing the id is not enough; the bytes are gated by the same rule as the listing.
        assert client.get(f"/class-photos/{other['id']}/file", headers=PARENT).status_code == 404


def test_students_never_reach_classroom_photos(client):
    mine = {"id": "photo-mine", "class_id": "class-4a", "filename": "x.png",
            "content_type": "image/png", "caption": "", "taken_on": "",
            "uploaded_by": "teacher-01", "uploaded_by_name": "Ms. Rivera", "uploaded_at": "2026-09-16T00:00:00+00:00"}
    with patch.object(store, "read", side_effect=lambda n: [mine] if n == "class_photos" else store_read(n)):
        assert client.get(f"/class-photos/{mine['id']}/file", headers=STUDENT).status_code == 404
    assert client.get("/parent/class-photos", headers=STUDENT).status_code == 403
    assert client.post("/teacher/class-photos", headers=STUDENT,
                       files={"file": ("a.png", io.BytesIO(PNG), "image/png")}).status_code == 403


def test_only_real_images_are_accepted(client):
    assert client.post(
        "/teacher/class-photos", headers=TEACHER,
        files={"file": ("notes.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    ).status_code == 400


def test_a_stored_filename_cannot_climb_out_of_the_uploads_folder(tmp_path):
    """Stored names are generated server-side, so anything else is refused by both back ends
    before it can become a path or an S3 key."""
    local = LocalBlobs(tmp_path)
    for attempt in ("../../students.json", "../secrets", "a/../../b", "notes.pdf",
                    "", "..", "photo.jpg/../../x.jpg"):
        with pytest.raises(ValueError):
            check_name(attempt)
        with pytest.raises(ValueError):
            local.get(attempt)
    # The shape we actually generate is accepted.
    assert check_name("0123456789abcdef0123456789abcdef.jpg")


def test_a_parent_sees_a_teammates_face_and_nothing_else_about_them():
    client = TestClient(app)
    body = client.get("/parent/children/student-01/progress", headers=PARENT).json()
    teammates = [mate for group in body["group_activities"] for mate in group["teammates"]]
    assert teammates, "Sam is seeded into a group, so there should be teammates to check"
    for mate in teammates:
        # A first name and a face. No grade, no class, no goal marker, no progress.
        assert set(mate) == {"id", "display_name", "photo", "avatar"}
    # The teacher's reason for grouping them is not in the parent payload at all.
    assert all("rationale" not in group for group in body["group_activities"])


def test_a_parent_still_cannot_read_another_familys_child():
    client = TestClient(app)
    assert client.get("/parent/children/student-02/progress", headers=PARENT).status_code == 403
