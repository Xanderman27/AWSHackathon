"""Real-time rooms for the collaborative beat-building game.

Rooms are deliberately ephemeral for the hackathon: they live in this API process,
contain no assessment data, and disappear when the server restarts. A production
adapter can move the same small state object to DynamoDB/ElastiCache later.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ..storage import store

router = APIRouter()

TRACK_IDS = ("drums", "claps", "bass", "bells")
STEP_COUNT = 8
PLAYER_COLORS = ("#2869dd", "#c84b7a", "#2e8b57", "#9b5de5")
STARTER_PATTERN = {
    "drums": [True, False, False, False, True, False, False, False],
    "claps": [False, False, True, False, False, False, True, False],
    "bass": [True, False, False, True, True, False, False, True],
    "bells": [False, True, False, False, False, True, False, False],
}


@dataclass
class Participant:
    id: str
    name: str
    color: str


@dataclass
class BeatRoom:
    activity_id: str
    grid: dict[str, list[bool]] = field(
        default_factory=lambda: {track: list(steps) for track, steps in STARTER_PATTERN.items()}
    )
    updated_by: dict[str, list[str | None]] = field(
        default_factory=lambda: {track: [None] * STEP_COUNT for track in TRACK_IDS}
    )
    tempo: int = 96
    playing: bool = False
    started_at: int | None = None
    revision: int = 0
    participants: dict[str, Participant] = field(default_factory=dict)
    connections: dict[str, WebSocket] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "type": "state",
            "activity_id": self.activity_id,
            "grid": self.grid,
            "updated_by": self.updated_by,
            "tempo": self.tempo,
            "playing": self.playing,
            "started_at": self.started_at,
            "revision": self.revision,
            "participants": [
                {"id": person.id, "name": person.name, "color": person.color}
                for person in self.participants.values()
            ],
        }


rooms: dict[str, BeatRoom] = {}
rooms_lock = asyncio.Lock()


async def broadcast(room: BeatRoom) -> None:
    payload = room.snapshot()
    stale: list[str] = []
    for player_id, socket in list(room.connections.items()):
        try:
            await socket.send_json(payload)
        except Exception:
            stale.append(player_id)
    for player_id in stale:
        room.connections.pop(player_id, None)
        room.participants.pop(player_id, None)


@router.websocket("/games/beat/ws/activity/{activity_id}")
async def beat_socket(
    websocket: WebSocket,
    activity_id: str,
    student_id: str = Query(..., min_length=1, max_length=40),
) -> None:
    activity = next(
        (
            row for row in store.read("group_activities")
            if row["id"] == activity_id
            and row["status"] == "published"
            and student_id in row["member_ids"]
        ),
        None,
    )
    student = next((row for row in store.read("students") if row["id"] == student_id), None)
    if activity is None or student is None:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "This group activity is not assigned to you."})
        await websocket.close(code=4403)
        return

    async with rooms_lock:
        room = rooms.get(activity_id)
        if room is None:
            room = BeatRoom(activity_id=activity_id)
            rooms[activity_id] = room

        existing = room.participants.get(student_id)
        if existing is None and len(room.participants) >= len(activity["member_ids"]):
            await websocket.accept()
            await websocket.send_json({"type": "error", "message": "This activity group is already full."})
            await websocket.close(code=4409)
            return

        color = existing.color if existing else PLAYER_COLORS[len(room.participants) % len(PLAYER_COLORS)]
        room.participants[student_id] = Participant(student_id, student["display_name"], color)
        room.connections[student_id] = websocket

    await websocket.accept()
    await broadcast(room)

    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")

            if message_type == "set_step":
                track = message.get("track")
                step = message.get("step")
                active = message.get("active")
                if track in TRACK_IDS and isinstance(step, int) and 0 <= step < STEP_COUNT and isinstance(active, bool):
                    room.grid[track][step] = active
                    room.updated_by[track][step] = student_id
                    room.revision += 1

            elif message_type == "tempo":
                tempo = message.get("tempo")
                if isinstance(tempo, int):
                    room.tempo = max(60, min(140, tempo))
                    if room.playing:
                        room.started_at = int(time.time() * 1000) + 300
                    room.revision += 1

            elif message_type == "transport":
                playing = message.get("playing")
                if isinstance(playing, bool):
                    room.playing = playing
                    room.started_at = int(time.time() * 1000) + 300 if playing else None
                    room.revision += 1

            elif message_type == "clear":
                room.grid = {track: [False] * STEP_COUNT for track in TRACK_IDS}
                room.updated_by = {track: [None] * STEP_COUNT for track in TRACK_IDS}
                room.playing = False
                room.started_at = None
                room.revision += 1

            else:
                continue

            await broadcast(room)

    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        room.connections.pop(student_id, None)
        room.participants.pop(student_id, None)
        await broadcast(room)
