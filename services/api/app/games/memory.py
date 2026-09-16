"""Memory Meadow: a shared concentration board.

Anyone may flip; the board is one board, so the group has to remember together. A pair that
does not match stays face up briefly and then turns back on its own, which is what wake()
does. Free play: no score, no timer, no turn order to lose.
"""

from __future__ import annotations

import random
from typing import Any

from .base import GameSpec, now_ms

GAME = GameSpec(
    id="memory-meadow",
    title="Memory Meadow",
    glyph="🌼",
    tone="mint",
    blurb="Flip the cards and remember where things are hiding.",
    instructions="Find every matching pair. Anyone can flip, so say what you remember out loud.",
    skill_hint="Working memory",
    grouping_skill_id=None,
    solo=True,
    teacher_note="No reading needed, so it works for any group in the class.",
)

FACES = ("🐝", "🦋", "🌻", "🐞", "🍄", "🐛")
LOOK_MS = 1100  # how long an unmatched pair stays face up


def initial_state() -> dict[str, Any]:
    deck = [face for face in FACES for _ in range(2)]
    random.shuffle(deck)
    return {
        "cards": deck,
        "matched": [False] * len(deck),
        "matched_by": [None] * len(deck),
        "flipped": [],
        "found": 0,
        "pairs": len(FACES),
        "wake_at": None,
    }


def _shuffle(state: dict[str, Any]) -> None:
    state.update(initial_state())


def apply(state: dict[str, Any], action: dict[str, Any], player_id: str) -> bool:
    kind = action.get("type")

    if kind == "flip":
        index = action.get("index")
        if not isinstance(index, int) or not 0 <= index < len(state["cards"]):
            return False
        # Two cards are already showing; the board is resolving, so ignore the tap.
        if len(state["flipped"]) >= 2 or index in state["flipped"] or state["matched"][index]:
            return False

        state["flipped"].append(index)
        if len(state["flipped"]) < 2:
            return True

        first, second = state["flipped"]
        if state["cards"][first] == state["cards"][second]:
            state["matched"][first] = True
            state["matched"][second] = True
            state["matched_by"][first] = player_id
            state["matched_by"][second] = player_id
            state["found"] += 1
            state["flipped"] = []
        else:
            # Leave both showing so everyone gets a good look, then wake() turns them back.
            state["wake_at"] = now_ms() + LOOK_MS
        return True

    if kind == "shuffle":
        _shuffle(state)
        return True

    return False


def wake(state: dict[str, Any]) -> bool:
    if not state.get("wake_at"):
        return False
    state["wake_at"] = None
    state["flipped"] = []
    return True
