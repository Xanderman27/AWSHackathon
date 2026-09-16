"""Beat Together: an 8-count loop four learners build at the same time."""

from __future__ import annotations

from typing import Any

from .base import GameSpec, now_ms

GAME = GameSpec(
    id="beat-together",
    title="Beat Together",
    glyph="🎵",
    tone="mint",
    blurb="Build one looping song together. Everyone can add or remove sounds.",
    instructions="Make one looping song together. Everyone can add or remove sounds.",
    skill_hint="Listening and turn-taking",
    grouping_skill_id="fraction_equivalence",
    solo=False,
    teacher_note="Pairs well with a lesson on counting beats in groups.",
)

TRACK_IDS = ("drums", "claps", "bass", "bells")
STEP_COUNT = 8
STARTER_PATTERN = {
    "drums": [True, False, False, False, True, False, False, False],
    "claps": [False, False, True, False, False, False, True, False],
    "bass": [True, False, False, True, True, False, False, True],
    "bells": [False, True, False, False, False, True, False, False],
}


def initial_state() -> dict[str, Any]:
    return {
        "grid": {track: list(steps) for track, steps in STARTER_PATTERN.items()},
        "updated_by": {track: [None] * STEP_COUNT for track in TRACK_IDS},
        "tempo": 96,
        "playing": False,
        "started_at": None,
    }


def apply(state: dict[str, Any], action: dict[str, Any], player_id: str) -> bool:
    kind = action.get("type")

    if kind == "set_step":
        track = action.get("track")
        step = action.get("step")
        active = action.get("active")
        if track in TRACK_IDS and isinstance(step, int) and 0 <= step < STEP_COUNT and isinstance(active, bool):
            state["grid"][track][step] = active
            state["updated_by"][track][step] = player_id
            return True

    elif kind == "tempo":
        tempo = action.get("tempo")
        if isinstance(tempo, int):
            state["tempo"] = max(60, min(140, tempo))
            if state["playing"]:
                state["started_at"] = now_ms() + 300
            return True

    elif kind == "transport":
        playing = action.get("playing")
        if isinstance(playing, bool):
            state["playing"] = playing
            state["started_at"] = now_ms() + 300 if playing else None
            return True

    elif kind == "clear":
        state["grid"] = {track: [False] * STEP_COUNT for track in TRACK_IDS}
        state["updated_by"] = {track: [None] * STEP_COUNT for track in TRACK_IDS}
        state["playing"] = False
        state["started_at"] = None
        return True

    return False
