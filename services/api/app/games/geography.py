"""Globe Trotters: hear a clue, find the continent or ocean together.

One clue at a time, one shared board of the seven continents and five oceans. Anyone may
tap an answer, so the group talks it out. A wrong tap just dims that tile for the round —
there is no strike count, no timer, and nothing leaves the room (free play, PRD §13).
"""

from __future__ import annotations

import random
from typing import Any

from .base import GameSpec, now_ms

GAME = GameSpec(
    id="globe-trotters",
    title="Globe Trotters",
    glyph="🌍",
    tone="sky",
    blurb="Read the clue and find the continent or ocean it belongs to.",
    instructions="Read each clue together and tap the continent or ocean it describes. Wrong guesses just dim, so keep trying until you find it.",
    skill_hint="Continents and oceans",
    grouping_skill_id="maps_continents",
    solo=True,
    teacher_note="Pairs well after the maps unit. Clues are read-aloud friendly and every learner can tap.",
)

# The fixed answer board. The client draws the same twelve tiles.
TILES = (
    {"id": "africa", "label": "Africa", "kind": "continent"},
    {"id": "antarctica", "label": "Antarctica", "kind": "continent"},
    {"id": "asia", "label": "Asia", "kind": "continent"},
    {"id": "australia", "label": "Australia", "kind": "continent"},
    {"id": "europe", "label": "Europe", "kind": "continent"},
    {"id": "north-america", "label": "North America", "kind": "continent"},
    {"id": "south-america", "label": "South America", "kind": "continent"},
    {"id": "arctic", "label": "Arctic Ocean", "kind": "ocean"},
    {"id": "atlantic", "label": "Atlantic Ocean", "kind": "ocean"},
    {"id": "indian", "label": "Indian Ocean", "kind": "ocean"},
    {"id": "pacific", "label": "Pacific Ocean", "kind": "ocean"},
    {"id": "southern", "label": "Southern Ocean", "kind": "ocean"},
)
TILE_IDS = {tile["id"] for tile in TILES}

QUESTIONS: tuple[dict[str, str], ...] = (
    {"clue": "Kangaroos hop across this continent, and most of its middle is a huge red desert.",
     "answer": "australia", "fact": "Australia is the only continent that is also a single country."},
    {"clue": "The biggest and deepest ocean on Earth. It touches Asia on one side and the Americas on the other.",
     "answer": "pacific", "fact": "The Pacific is so big that all the land on Earth could fit inside it."},
    {"clue": "This icy continent at the very bottom of the world has no cities, just penguins and scientists.",
     "answer": "antarctica", "fact": "Antarctica is the coldest, windiest, and driest continent of all."},
    {"clue": "The largest continent, home to pandas, tigers, and more people than anywhere else.",
     "answer": "asia", "fact": "About 6 out of every 10 people on Earth live in Asia."},
    {"clue": "This warm ocean sits between Africa, Asia, and Australia.",
     "answer": "indian", "fact": "The Indian Ocean is the warmest ocean on Earth."},
    {"clue": "Lions, elephants, and giraffes roam this continent, and the world's longest river flows through it.",
     "answer": "africa", "fact": "The Sahara in Africa is the largest hot desert in the world."},
    {"clue": "This ocean lies between the Americas on one side and Europe and Africa on the other.",
     "answer": "atlantic", "fact": "The Atlantic gets about 4 centimeters wider every year - the continents are drifting!"},
    {"clue": "A small continent packed with countries, castles, and the Eiffel Tower.",
     "answer": "europe", "fact": "Europe has about 44 countries squeezed into the second-smallest continent."},
    {"clue": "This continent stretches from snowy Canada down to sunny Mexico.",
     "answer": "north-america", "fact": "North America has the world's largest freshwater lake system, the Great Lakes."},
    {"clue": "The icy ocean at the very top of the world, where polar bears live on the sea ice.",
     "answer": "arctic", "fact": "The Arctic is the smallest and shallowest of the five oceans."},
    {"clue": "The Amazon rainforest covers a huge part of this continent.",
     "answer": "south-america", "fact": "The Andes in South America are the longest mountain range on land."},
    {"clue": "This ocean circles all the way around Antarctica.",
     "answer": "southern", "fact": "The Southern Ocean was only given its name officially in the year 2000."},
)

ROUND_COUNT = 8
CELEBRATE_MS = 2600  # how long the "you found it" banner stays before the next clue


def _current(state: dict[str, Any]) -> dict[str, str]:
    return QUESTIONS[state["order"][state["index"]]]


def _public_round(state: dict[str, Any]) -> dict[str, Any]:
    """What everyone sees. The answer and fact only ship once the round is solved."""
    question = _current(state)
    payload: dict[str, Any] = {"clue": question["clue"]}
    if state["solved"]:
        payload["answer"] = question["answer"]
        payload["fact"] = question["fact"]
    return payload


def _fresh(state: dict[str, Any]) -> None:
    order = random.sample(range(len(QUESTIONS)), ROUND_COUNT)
    state.update({
        "order": order,
        "index": 0,
        "total": ROUND_COUNT,
        "score": 0,
        "missed": [],       # tile ids dimmed this round
        "solved": False,
        "solved_by": None,
        "first_try": True,
        "done": False,
        "wake_at": None,
    })
    state["round"] = _public_round(state)


def initial_state() -> dict[str, Any]:
    state: dict[str, Any] = {}
    _fresh(state)
    return state


def apply(state: dict[str, Any], action: dict[str, Any], player_id: str) -> bool:
    kind = action.get("type")

    if kind == "guess":
        tile = action.get("tile")
        if state["done"] or state["solved"] or tile not in TILE_IDS or tile in state["missed"]:
            return False
        if tile == _current(state)["answer"]:
            state["solved"] = True
            state["solved_by"] = player_id
            if state["first_try"]:
                state["score"] += 1
            state["round"] = _public_round(state)
            state["wake_at"] = now_ms() + CELEBRATE_MS
        else:
            state["missed"].append(tile)
            state["first_try"] = False
        return True

    if kind == "restart":
        _fresh(state)
        return True

    return False


def wake(state: dict[str, Any]) -> bool:
    """The celebration pause is over: move to the next clue, or finish the trip."""
    if not state.get("wake_at"):
        return False
    state["wake_at"] = None
    if state["index"] + 1 >= state["total"]:
        state["done"] = True
        return True
    state["index"] += 1
    state["missed"] = []
    state["solved"] = False
    state["solved_by"] = None
    state["first_try"] = True
    state["round"] = _public_round(state)
    return True
