"""Shared plumbing for every collaborative activity.

Rooms are deliberately ephemeral for the hackathon: they live in this API process, hold no
assessment data, and disappear when the server restarts. A production adapter can move the
same small state object to DynamoDB/ElastiCache later.

Games are free play (PRD §13). Nothing a room holds reaches the mastery model, the teacher
dashboard, or a parent. A game module supplies a GameSpec plus three pure-ish functions:

    initial_state()                 -> the dict every player sees
    apply(state, action, player_id) -> True when the change should be broadcast
    wake(state)                     -> optional; runs once when state["wake_at"] passes
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from fastapi import WebSocket

PLAYER_COLORS = ("#2869dd", "#c84b7a", "#2e8b57", "#9b5de5")


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class GameSpec:
    """Everything the rest of the app needs to know about a game without importing it."""

    id: str
    title: str
    glyph: str
    tone: str  # pastel class used by the student cards: mint | sky | cream | rose
    blurb: str  # one child-facing sentence
    instructions: str  # what the group is asked to do together
    skill_hint: str  # child-facing skill label, e.g. "Working memory"
    # Skill the grouping recommendation reads evidence from. None means any recent evidence
    # is irrelevant, so every learner in the class is groupable.
    grouping_skill_id: Optional[str] = None
    min_group: int = 2
    max_group: int = 4
    solo: bool = False  # may a learner open this on their own, outside an assigned group?
    teacher_note: str = ""


class GameModule(Protocol):
    GAME: GameSpec

    def initial_state(self) -> dict[str, Any]: ...

    def apply(self, state: dict[str, Any], action: dict[str, Any], player_id: str) -> bool: ...


@dataclass
class Participant:
    id: str
    name: str
    color: str
    photo: str | None = None
    avatar: dict[str, Any] | None = None


@dataclass
class Room:
    room_id: str
    game_id: str
    state: dict[str, Any]
    capacity: int
    revision: int = 0
    participants: dict[str, Participant] = field(default_factory=dict)
    connections: dict[str, WebSocket] = field(default_factory=dict)
    # Live pointer positions, normalized 0..1 over the shared play surface. Presence sugar,
    # not game state: games never read it and reconnects start clean.
    cursors: dict[str, list[float]] = field(default_factory=dict)
    waker: Optional[asyncio.Task] = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "type": "state",
            "room_id": self.room_id,
            "game_id": self.game_id,
            "revision": self.revision,
            "state": self.state,
            "cursors": self.cursors,
            "participants": [
                {"id": person.id, "name": person.name, "color": person.color,
                 "photo": person.photo, "avatar": person.avatar}
                for person in self.participants.values()
            ],
        }


rooms: dict[str, Room] = {}
rooms_lock = asyncio.Lock()


async def broadcast(room: Room) -> None:
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


def schedule_wake(room: Room, wake: Optional[Callable[[dict[str, Any]], bool]]) -> None:
    """Run a game's deferred step (a memory pair flipping back, say) without blocking anyone.

    Only one timer is ever pending per room; a newer wake_at replaces the older task.
    """
    if wake is None:
        return
    wake_at = room.state.get("wake_at")
    if not wake_at:
        return
    if room.waker and not room.waker.done():
        room.waker.cancel()

    async def run() -> None:
        try:
            delay = max(0.0, (room.state.get("wake_at") or 0) - now_ms()) / 1000
            await asyncio.sleep(delay)
            if not room.state.get("wake_at"):
                return
            if wake(room.state):
                room.revision += 1
                await broadcast(room)
        except asyncio.CancelledError:
            pass

    room.waker = asyncio.create_task(run())
