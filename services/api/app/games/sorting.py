"""Sort It Out: the group invents its own groups and explains them.

There is no answer key on purpose. The learning is in naming a group and arguing about what
belongs in it, so the server only keeps the bins the children make and where they put things.
"""

from __future__ import annotations

from typing import Any

from .base import GameSpec

GAME = GameSpec(
    id="sort-it-out",
    title="Sort It Out",
    glyph="🧺",
    tone="cream",
    blurb="Put things into groups and say why they belong together.",
    instructions="Make your own groups, name them, and sort every card. There is no one right answer.",
    skill_hint="Sorting and reasoning",
    grouping_skill_id=None,
    solo=True,
    teacher_note="Open-ended, so it suits a mixed group. Ask each bin's maker to explain the rule.",
)

MAX_BINS = 4
BIN_NAME_MAX = 24

ROUNDS: tuple[dict[str, Any], ...] = (
    {
        "title": "The big mix-up",
        "prompt": "How could these go together? You decide.",
        "items": (
            {"id": "a1", "label": "apple", "glyph": "🍎"},
            {"id": "a2", "label": "bus", "glyph": "🚌"},
            {"id": "a3", "label": "dog", "glyph": "🐕"},
            {"id": "a4", "label": "banana", "glyph": "🍌"},
            {"id": "a5", "label": "bike", "glyph": "🚲"},
            {"id": "a6", "label": "cat", "glyph": "🐈"},
            {"id": "a7", "label": "rocket", "glyph": "🚀"},
            {"id": "a8", "label": "fish", "glyph": "🐟"},
            {"id": "a9", "label": "carrot", "glyph": "🥕"},
        ),
    },
    {
        "title": "Number cards",
        "prompt": "Groups of numbers. Even and odd? Big and small? Counting by fives?",
        "items": (
            {"id": "n1", "label": "2", "glyph": "2️⃣"},
            {"id": "n2", "label": "5", "glyph": "5️⃣"},
            {"id": "n3", "label": "10", "glyph": "🔟"},
            {"id": "n4", "label": "7", "glyph": "7️⃣"},
            {"id": "n5", "label": "12", "glyph": "🕛"},
            {"id": "n6", "label": "20", "glyph": "💯"},
            {"id": "n7", "label": "3", "glyph": "3️⃣"},
            {"id": "n8", "label": "15", "glyph": "🕒"},
            {"id": "n9", "label": "8", "glyph": "8️⃣"},
        ),
    },
    {
        "title": "Out in the weather",
        "prompt": "What goes with what? Maybe by season, maybe by how it feels.",
        "items": (
            {"id": "w1", "label": "umbrella", "glyph": "☂️"},
            {"id": "w2", "label": "snowman", "glyph": "⛄"},
            {"id": "w3", "label": "sun hat", "glyph": "👒"},
            {"id": "w4", "label": "rain cloud", "glyph": "🌧️"},
            {"id": "w5", "label": "mittens", "glyph": "🧤"},
            {"id": "w6", "label": "beach ball", "glyph": "🏖️"},
            {"id": "w7", "label": "fallen leaf", "glyph": "🍂"},
            {"id": "w8", "label": "rainbow", "glyph": "🌈"},
        ),
    },
)

STARTER_BINS = ("Group 1", "Group 2")


def _round_payload(index: int) -> dict[str, Any]:
    game_round = ROUNDS[index]
    return {
        "title": game_round["title"],
        "prompt": game_round["prompt"],
        "items": [dict(item) for item in game_round["items"]],
    }


def _item_ids(index: int) -> set[str]:
    return {item["id"] for item in ROUNDS[index]["items"]}


def _starter_bins() -> list[dict[str, Any]]:
    return [{"id": f"bin-{index}", "name": name, "created_by": None} for index, name in enumerate(STARTER_BINS)]


def initial_state() -> dict[str, Any]:
    return {
        "round": 0,
        "total_rounds": len(ROUNDS),
        "set": _round_payload(0),
        "bins": _starter_bins(),
        "placements": {},  # item id -> {"bin": bin id, "by": player id}
        "next_bin": len(STARTER_BINS),
    }


def apply(state: dict[str, Any], action: dict[str, Any], player_id: str) -> bool:
    kind = action.get("type")
    bin_ids = {group["id"] for group in state["bins"]}

    if kind == "place":
        item = action.get("item")
        target = action.get("bin")
        if item in _item_ids(state["round"]) and (target in bin_ids or target is None):
            if target is None:
                state["placements"].pop(item, None)
            else:
                state["placements"][item] = {"bin": target, "by": player_id}
            return True

    elif kind == "add_bin":
        if len(state["bins"]) >= MAX_BINS:
            return False
        name = str(action.get("name") or "").strip()[:BIN_NAME_MAX]
        state["bins"].append({
            "id": f"bin-{state['next_bin']}",
            "name": name or f"Group {state['next_bin'] + 1}",
            "created_by": player_id,
        })
        state["next_bin"] += 1
        return True

    elif kind == "rename_bin":
        target = action.get("bin")
        name = str(action.get("name") or "").strip()[:BIN_NAME_MAX]
        for group in state["bins"]:
            if group["id"] == target:
                group["name"] = name
                return True

    elif kind == "remove_bin":
        target = action.get("bin")
        if target in bin_ids and len(state["bins"]) > 1:
            state["bins"] = [group for group in state["bins"] if group["id"] != target]
            state["placements"] = {
                item: where for item, where in state["placements"].items() if where["bin"] != target
            }
            return True

    elif kind == "clear":
        state["placements"] = {}
        return True

    elif kind == "set_round":
        target = action.get("round")
        if isinstance(target, int) and 0 <= target < len(ROUNDS):
            state["round"] = target
            state["set"] = _round_payload(target)
            state["placements"] = {}
            return True

    return False
