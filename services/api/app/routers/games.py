"""One real-time endpoint for every collaborative activity.

Authorisation is the same rule for all of them: a learner may open a group room only if the
teacher published that activity to a group they belong to. Solo rooms are private to one
learner and exist only for games the registry marks as playable alone.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from .. import games
from ..games.base import PLAYER_COLORS, Participant, Room, broadcast, rooms, rooms_lock, schedule_wake
from ..storage import store

router = APIRouter()

SOLO_PREFIX = "solo:"


@router.get("/games")
def game_catalog():
    """The game registry. Public to any signed-in role; it contains no student data."""
    return games.catalog()


def _student(student_id: str) -> dict | None:
    return next((row for row in store.read("students") if row["id"] == student_id), None)


def _group_activity(activity_id: str, student_id: str) -> dict | None:
    return next(
        (
            row for row in store.read("group_activities")
            if row["id"] == activity_id
            and row["status"] == "published"
            and student_id in row["member_ids"]
        ),
        None,
    )


def _resolve(activity_id: str, student_id: str) -> tuple[str, str, int, str | None]:
    """Return (room key, game id, capacity, error). The room key is never client-supplied."""
    if activity_id.startswith(SOLO_PREFIX):
        game_id = activity_id[len(SOLO_PREFIX):]
        spec = games.spec(game_id)
        if spec is None or not spec.solo:
            return "", "", 0, "This game cannot be played on your own."
        # One private room per learner, so nobody can join someone else's solo game.
        return f"{SOLO_PREFIX}{game_id}:{student_id}", game_id, 1, None

    activity = _group_activity(activity_id, student_id)
    if activity is None:
        return "", "", 0, "This group activity is not assigned to you."
    if games.spec(activity["game_id"]) is None:
        return "", "", 0, "This activity is no longer available."
    return activity["id"], activity["game_id"], len(activity["member_ids"]), None


async def _reject(websocket: WebSocket, message: str, code: int) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "error", "message": message})
    await websocket.close(code=code)


@router.websocket("/games/ws/activity/{activity_id}")
async def activity_socket(
    websocket: WebSocket,
    activity_id: str,
    student_id: str = Query(..., min_length=1, max_length=60),
) -> None:
    student = _student(student_id)
    room_key, game_id, capacity, error = _resolve(activity_id, student_id)
    if student is None or error:
        await _reject(websocket, error or "This activity is not available.", 4403)
        return

    module = games.BY_ID[game_id]

    async with rooms_lock:
        room = rooms.get(room_key)
        if room is None:
            room = Room(
                room_id=room_key,
                game_id=game_id,
                state=module.initial_state(),
                capacity=capacity,
            )
            rooms[room_key] = room

        existing = room.participants.get(student_id)
        if existing is None and len(room.participants) >= room.capacity:
            await _reject(websocket, "This activity group is already full.", 4409)
            return

        color = existing.color if existing else PLAYER_COLORS[len(room.participants) % len(PLAYER_COLORS)]
        room.participants[student_id] = Participant(
            student_id, student["display_name"], color,
            photo=student.get("photo"), avatar=student.get("avatar"),
        )
        room.connections[student_id] = websocket

    await websocket.accept()
    await broadcast(room)

    wake = getattr(module, "wake", None)

    try:
        while True:
            action = await websocket.receive_json()
            if not isinstance(action, dict):
                continue
            if module.apply(room.state, action, student_id):
                room.revision += 1
                await broadcast(room)
                schedule_wake(room, wake)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        # Only tear down the slot if it is still this socket. A learner who reopens the
        # activity (or a dev-mode double mount) briefly has two sockets for one id, and the
        # older one closing must not evict the newer one's connection.
        if room.connections.get(student_id) is websocket:
            room.connections.pop(student_id, None)
            room.participants.pop(student_id, None)
            await broadcast(room)
            # An empty solo room is worth dropping; a group room is kept so teammates who
            # step away and come back find the work they left behind.
            if not room.connections and room.room_id.startswith(SOLO_PREFIX):
                rooms.pop(room.room_id, None)
