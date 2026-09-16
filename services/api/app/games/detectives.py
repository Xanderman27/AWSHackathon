"""Story Detectives: a group sorts clue cards into main idea, helpful detail, and not-in-story.

Free play. The group may reveal the answers whenever they like; nothing is scored, timed, or
reported. Passages are short, original, and written at roughly a Grade 3 reading level.
"""

from __future__ import annotations

from typing import Any

from .base import GameSpec

GAME = GameSpec(
    id="story-detectives",
    title="Story Detectives",
    glyph="🔎",
    tone="cream",
    blurb="Read a story together, then sort the clue cards.",
    instructions="Read the story, then decide together where each clue card belongs.",
    skill_hint="Main idea and details",
    grouping_skill_id="main_idea",
    solo=True,
    teacher_note="Mirrors the main-idea objective. Best with one reader and one card mover.",
)

COLUMNS: tuple[dict[str, str], ...] = (
    {"id": "main", "name": "The big idea", "help": "What the whole story is mostly about."},
    {"id": "detail", "name": "A helpful detail", "help": "A true bit from the story that backs up the big idea."},
    {"id": "not", "name": "Not in the story", "help": "It might be true, but the story never says it."},
)

ROUNDS: tuple[dict[str, Any], ...] = (
    {
        "title": "The Class Garden",
        "passage": (
            "Room 4A started a garden by the door. Every morning two students fill the "
            "watering can. On Friday the first green shoot pushed up through the soil, and "
            "the whole class cheered. Now the garden grows beans, carrots, and one tall "
            "sunflower."
        ),
        "cards": (
            {"id": "g1", "text": "Room 4A grew a garden together.", "answer": "main"},
            {"id": "g2", "text": "Two students water the seeds every morning.", "answer": "detail"},
            {"id": "g3", "text": "The first green shoot came up on Friday.", "answer": "detail"},
            {"id": "g4", "text": "The garden grows beans, carrots, and a sunflower.", "answer": "detail"},
            {"id": "g5", "text": "The class cheered for the new shoot.", "answer": "detail"},
            {"id": "g6", "text": "The class sold the carrots at a fair.", "answer": "not"},
            {"id": "g7", "text": "Sunflowers can grow taller than a door.", "answer": "not"},
        ),
    },
    {
        "title": "Maya and the Ramp",
        "passage": (
            "Maya wanted to ride her skateboard down the big ramp. The first time, she fell "
            "before she reached the bottom. She checked her helmet, stood up, and tried "
            "again. It took eleven tries. On the twelfth try, Maya rolled all the way down "
            "and did not fall once."
        ),
        "cards": (
            {"id": "m1", "text": "Maya kept trying until she rode down the ramp.", "answer": "main"},
            {"id": "m2", "text": "Maya fell on her very first try.", "answer": "detail"},
            {"id": "m3", "text": "She checked her helmet before trying again.", "answer": "detail"},
            {"id": "m4", "text": "The twelfth try was the one that worked.", "answer": "detail"},
            {"id": "m5", "text": "Maya taught her little brother to skate.", "answer": "not"},
            {"id": "m6", "text": "Skate parks are usually made of concrete.", "answer": "not"},
        ),
    },
)

COLUMN_IDS = {column["id"] for column in COLUMNS}


def _round_payload(index: int) -> dict[str, Any]:
    story = ROUNDS[index]
    return {"title": story["title"], "passage": story["passage"], "cards": [dict(card) for card in story["cards"]]}


def _card_ids(index: int) -> set[str]:
    return {card["id"] for card in ROUNDS[index]["cards"]}


def initial_state() -> dict[str, Any]:
    return {
        "round": 0,
        "total_rounds": len(ROUNDS),
        "story": _round_payload(0),
        "columns": [dict(column) for column in COLUMNS],
        # card id -> {"column": id, "by": player id}. A card missing from this map is still
        # in the pile, which is what the clients render as "not sorted yet".
        "placements": {},
        "revealed": False,
    }


def apply(state: dict[str, Any], action: dict[str, Any], player_id: str) -> bool:
    kind = action.get("type")
    index = state["round"]

    if kind == "place":
        card = action.get("card")
        column = action.get("column")
        if card in _card_ids(index) and (column in COLUMN_IDS or column is None):
            if column is None:
                state["placements"].pop(card, None)
            else:
                state["placements"][card] = {"column": column, "by": player_id}
            return True

    elif kind == "reveal":
        show = action.get("revealed")
        if isinstance(show, bool):
            state["revealed"] = show
            return True

    elif kind == "clear":
        state["placements"] = {}
        state["revealed"] = False
        return True

    elif kind == "set_round":
        target = action.get("round")
        if isinstance(target, int) and 0 <= target < len(ROUNDS):
            state["round"] = target
            state["story"] = _round_payload(target)
            state["placements"] = {}
            state["revealed"] = False
            return True

    return False
