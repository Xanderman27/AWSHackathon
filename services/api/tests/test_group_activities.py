from unittest.mock import patch

from fastapi.testclient import TestClient

from app.games.base import rooms
from app.main import app
from app.storage import store


def activity(activity_id, members, game_id="beat-together"):
    return {
        "id": activity_id,
        "class_id": "class-4a",
        "game_id": game_id,
        "title": "Test Activity",
        "group_name": "Test Team",
        "member_ids": members,
        "rationale": "Test group",
        "status": "published",
        "created_by": "teacher-01",
        "published_at": "2026-09-16T18:00:00+00:00",
    }


def reading(rows, name="group_activities"):
    original = store.read
    return lambda collection: rows if collection == name else original(collection)


def test_two_players_share_live_beat_edits():
    activity_id = "group-activity-test"
    rooms.pop(activity_id, None)
    client = TestClient(app)

    with patch.object(store, "read", side_effect=reading([activity(activity_id, ["student-01", "student-02"])])):
        with client.websocket_connect(
            f"/games/ws/activity/{activity_id}?student_id=student-01"
        ) as first:
            first_state = first.receive_json()
            assert first_state["room_id"] == activity_id
            assert first_state["game_id"] == "beat-together"
            assert [person["name"] for person in first_state["participants"]] == ["Sam"]

            with client.websocket_connect(
                f"/games/ws/activity/{activity_id}?student_id=student-02"
            ) as second:
                joined_for_first = first.receive_json()
                joined_for_second = second.receive_json()
                assert {person["name"] for person in joined_for_first["participants"]} == {"Sam", "Ava"}
                assert len(joined_for_second["participants"]) == 2

                second.send_json({"type": "set_step", "track": "bells", "step": 3, "active": True})
                update_for_first = first.receive_json()
                update_for_second = second.receive_json()

                assert update_for_first["state"]["grid"]["bells"][3] is True
                assert update_for_first["state"]["updated_by"]["bells"][3] == "student-02"
                assert update_for_second["revision"] == update_for_first["revision"]
    rooms.pop(activity_id, None)


def test_a_learner_outside_the_group_is_refused_the_room():
    activity_id = "group-activity-closed"
    rooms.pop(activity_id, None)
    client = TestClient(app)

    with patch.object(store, "read", side_effect=reading([activity(activity_id, ["student-01", "student-02"])])):
        with client.websocket_connect(
            f"/games/ws/activity/{activity_id}?student_id=student-03"
        ) as intruder:
            message = intruder.receive_json()
            assert message["type"] == "error"
    assert activity_id not in rooms


def test_every_registered_game_shares_live_state():
    """One room per game, so a new game cannot silently ship without working for a group."""
    from app import games

    client = TestClient(app)
    for game_id in games.BY_ID:
        activity_id = f"group-activity-{game_id}"
        rooms.pop(activity_id, None)
        rows = [activity(activity_id, ["student-01", "student-02"], game_id=game_id)]
        with patch.object(store, "read", side_effect=reading(rows)):
            with client.websocket_connect(f"/games/ws/activity/{activity_id}?student_id=student-01") as socket:
                state = socket.receive_json()
                assert state["game_id"] == game_id, game_id
                assert state["state"], game_id
        rooms.pop(activity_id, None)


def test_solo_rooms_are_private_and_only_for_solo_games():
    client = TestClient(app)
    with client.websocket_connect("/games/ws/activity/solo:memory-meadow?student_id=student-01") as socket:
        state = socket.receive_json()
        assert state["room_id"] == "solo:memory-meadow:student-01"
        assert len(state["state"]["cards"]) == 12

    # Beat Together is a group game; there is no solo door into it.
    with client.websocket_connect("/games/ws/activity/solo:beat-together?student_id=student-01") as socket:
        assert socket.receive_json()["type"] == "error"


def test_student_sees_only_their_published_group_activity():
    activities = [
        activity("assigned", ["student-01", "student-02"]),
        activity("not-assigned", ["student-03", "student-04"]),
    ]
    client = TestClient(app)
    with patch.object(store, "read", side_effect=reading(activities)):
        response = client.get(
            "/student/group-activities",
            headers={"X-Role": "student", "X-User-Id": "student-01"},
        )
        assert response.status_code == 200
        assert [row["id"] for row in response.json()] == ["assigned"]
        assert response.json()[0]["teammates"] == [{"id": "student-02", "display_name": "Ava"}]


def test_the_grouping_rationale_never_reaches_a_student():
    client = TestClient(app)
    with patch.object(store, "read", side_effect=reading([activity("assigned", ["student-01", "student-02"])])):
        row = client.get(
            "/student/group-activities",
            headers={"X-Role": "student", "X-User-Id": "student-01"},
        ).json()[0]
    assert "rationale" not in row


def test_teacher_publishes_groups_before_students_can_join():
    memory = {"group_activities": [], "audit": []}
    original_read = store.read

    client = TestClient(app)
    with (
        patch.object(store, "read", side_effect=lambda name: memory.get(name, None) if name in memory else original_read(name)),
        patch.object(store, "write_all", side_effect=lambda name, rows: memory.__setitem__(name, rows)),
        patch.object(store, "append", side_effect=lambda name, row: memory[name].append(row)),
    ):
        response = client.post(
            "/teacher/group-activities/publish",
            headers={"X-Role": "teacher", "X-User-Id": "teacher-01"},
            json={"game_id": "fraction-strips", "groups": [{
                "name": "Rhythm Crew",
                "member_ids": ["student-01", "student-02"],
                "rationale": "Teacher approved the platform suggestion.",
            }]},
        )
        assert response.status_code == 200
        assert memory["group_activities"][0]["status"] == "published"
        assert memory["group_activities"][0]["game_id"] == "fraction-strips"
        assert memory["audit"][0]["action"] == "group_activities_published"

        student_response = client.get(
            "/student/group-activities",
            headers={"X-Role": "student", "X-User-Id": "student-01"},
        )
        assert student_response.status_code == 200
        assert student_response.json()[0]["group_name"] == "Rhythm Crew"


def test_publishing_one_game_leaves_another_games_groups_alone():
    memory = {"group_activities": [activity("beat-one", ["student-03", "student-04"])], "audit": []}
    original_read = store.read

    client = TestClient(app)
    with (
        patch.object(store, "read", side_effect=lambda name: memory[name] if name in memory else original_read(name)),
        patch.object(store, "write_all", side_effect=lambda name, rows: memory.__setitem__(name, rows)),
        patch.object(store, "append", side_effect=lambda name, row: memory[name].append(row)),
    ):
        client.post(
            "/teacher/group-activities/publish",
            headers={"X-Role": "teacher", "X-User-Id": "teacher-01"},
            json={"game_id": "shape-shift", "groups": [{
                "name": "Shape Crew",
                "member_ids": ["student-01", "student-02"],
                "rationale": "Teacher approved.",
            }]},
        )
    published = {(row["game_id"], row["group_name"]) for row in memory["group_activities"]}
    assert published == {("beat-together", "Test Team"), ("shape-shift", "Shape Crew")}


def test_a_teacher_cannot_group_learners_from_another_class():
    client = TestClient(app)
    response = client.post(
        "/teacher/group-activities/publish",
        headers={"X-Role": "teacher", "X-User-Id": "teacher-01"},
        json={"game_id": "memory-meadow", "groups": [{
            "name": "Outsiders",
            "member_ids": ["student-01", "student-99"],
            "rationale": "Should fail.",
        }]},
    )
    assert response.status_code == 403


def test_mixed_group_recommendation_holds_nobody_back_for_evidence():
    client = TestClient(app)
    fractions = client.get(
        "/teacher/group-activities/recommendation?game_id=fraction-strips",
        headers={"X-Role": "teacher", "X-User-Id": "teacher-01"},
    ).json()
    assert fractions["uses_evidence"] is True

    memory_game = client.get(
        "/teacher/group-activities/recommendation?game_id=memory-meadow",
        headers={"X-Role": "teacher", "X-User-Id": "teacher-01"},
    ).json()
    assert memory_game["uses_evidence"] is False
    assert memory_game["needs_more_evidence"] == []
    grouped = [member for group in memory_game["groups"] for member in group["member_ids"]]
    assert sorted(grouped) == sorted(student["id"] for student in memory_game["students"])
