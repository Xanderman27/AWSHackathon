from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.routers.beat_game import rooms
from app.storage import store


def test_two_players_share_live_beat_edits():
    activity_id = "group-activity-test"
    activity = {
        "id": activity_id,
        "class_id": "class-4a",
        "game_id": "beat-together",
        "title": "Beat Together",
        "group_name": "Test Team",
        "member_ids": ["student-01", "student-02"],
        "rationale": "Test group",
        "status": "published",
        "created_by": "teacher-01",
        "published_at": "2026-09-16T18:00:00+00:00",
    }
    original_read = store.read
    fake_read = lambda name: [activity] if name == "group_activities" else original_read(name)
    rooms.pop(activity_id, None)
    client = TestClient(app)

    with patch.object(store, "read", side_effect=fake_read):
        with client.websocket_connect(
            f"/games/beat/ws/activity/{activity_id}?student_id=student-01"
        ) as first:
            first_state = first.receive_json()
            assert first_state["activity_id"] == activity_id
            assert [person["name"] for person in first_state["participants"]] == ["Sam"]

            with client.websocket_connect(
                f"/games/beat/ws/activity/{activity_id}?student_id=student-02"
            ) as second:
                joined_for_first = first.receive_json()
                joined_for_second = second.receive_json()
                assert {person["name"] for person in joined_for_first["participants"]} == {"Sam", "Ava"}
                assert len(joined_for_second["participants"]) == 2

                second.send_json({"type": "set_step", "track": "bells", "step": 3, "active": True})
                update_for_first = first.receive_json()
                update_for_second = second.receive_json()

                assert update_for_first["grid"]["bells"][3] is True
                assert update_for_first["updated_by"]["bells"][3] == "student-02"
                assert update_for_second["revision"] == update_for_first["revision"]
    rooms.pop(activity_id, None)


def test_student_sees_only_their_published_group_activity():
    activities = [
        {
            "id": "assigned",
            "class_id": "class-4a",
            "game_id": "beat-together",
            "title": "Beat Together",
            "group_name": "Blue Notes",
            "member_ids": ["student-01", "student-02"],
            "rationale": "Test",
            "status": "published",
            "created_by": "teacher-01",
            "published_at": "2026-09-16T18:00:00+00:00",
        },
        {
            "id": "not-assigned",
            "class_id": "class-4a",
            "game_id": "beat-together",
            "title": "Beat Together",
            "group_name": "Other Team",
            "member_ids": ["student-03", "student-04"],
            "rationale": "Test",
            "status": "published",
            "created_by": "teacher-01",
            "published_at": "2026-09-16T18:00:00+00:00",
        },
    ]
    original_read = store.read
    fake_read = lambda name: activities if name == "group_activities" else original_read(name)
    client = TestClient(app)
    with patch.object(store, "read", side_effect=fake_read):
        response = client.get(
            "/student/group-activities",
            headers={"X-Role": "student", "X-User-Id": "student-01"},
        )
        assert response.status_code == 200
        assert [activity["id"] for activity in response.json()] == ["assigned"]
        assert response.json()[0]["teammates"] == [{"id": "student-02", "display_name": "Ava"}]


def test_teacher_publishes_groups_before_students_can_join():
    memory = {"group_activities": [], "audit": []}
    original_read = store.read

    def fake_read(name):
        return memory[name] if name in memory else original_read(name)

    def fake_write(name, rows):
        memory[name] = rows

    def fake_append(name, row):
        memory[name].append(row)

    client = TestClient(app)
    with (
        patch.object(store, "read", side_effect=fake_read),
        patch.object(store, "write_all", side_effect=fake_write),
        patch.object(store, "append", side_effect=fake_append),
    ):
        response = client.post(
            "/teacher/group-activities/publish",
            headers={"X-Role": "teacher", "X-User-Id": "teacher-01"},
            json={"groups": [{
                "name": "Rhythm Crew",
                "member_ids": ["student-01", "student-02"],
                "rationale": "Teacher approved the platform suggestion.",
            }]},
        )
        assert response.status_code == 200
        assert memory["group_activities"][0]["status"] == "published"
        assert memory["audit"][0]["action"] == "group_activities_published"

        student_response = client.get(
            "/student/group-activities",
            headers={"X-Role": "student", "X-User-Id": "student-01"},
        )
        assert student_response.status_code == 200
        assert student_response.json()[0]["group_name"] == "Rhythm Crew"
