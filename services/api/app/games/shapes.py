"""Shape Shift: the group turns and flips pieces to fill one shared outline.

Every puzzle here is guaranteed solvable, because each piece set is taken from a tiling the
outline already has. Any arrangement that covers the outline wins, not one exact answer, so
a group can find its own way in.
"""

from __future__ import annotations

from typing import Any

from .base import GameSpec

GAME = GameSpec(
    id="shape-shift",
    title="Shape Shift",
    glyph="🔷",
    tone="rose",
    blurb="Turn and flip shapes to see how they fit.",
    instructions="Fill the whole outline together. Turn or flip a piece before you drop it in.",
    skill_hint="Space and shape",
    grouping_skill_id=None,
    solo=True,
    teacher_note="Good for learners who show what they know by moving things rather than reading.",
)

TONES = ("mint", "sky", "cream", "rose", "brand")

ROUNDS: tuple[dict[str, Any], ...] = (
    {
        "title": "The quilt square",
        "rows": 4,
        "cols": 4,
        "silhouette": [[row, col] for row in range(4) for col in range(4)],
        "pieces": (
            {"id": "corner", "name": "Corner", "cells": [[0, 0], [1, 0], [2, 0], [2, 1]]},
            {"id": "hook", "name": "Hook", "cells": [[0, 0], [0, 1], [0, 2], [1, 2]]},
            {"id": "step", "name": "Step", "cells": [[0, 0], [0, 1], [1, 1], [1, 2]]},
            {"id": "bar", "name": "Bar", "cells": [[0, 0], [0, 1], [0, 2], [0, 3]]},
        ),
    },
    {
        "title": "The little tree",
        "rows": 4,
        "cols": 5,
        "silhouette": (
            [[row, col] for row in range(2) for col in range(5)] + [[2, 2], [3, 2]]
        ),
        "pieces": (
            {"id": "block-a", "name": "Block", "cells": [[0, 0], [0, 1], [1, 0], [1, 1]]},
            {"id": "block-b", "name": "Block", "cells": [[0, 0], [0, 1], [1, 0], [1, 1]]},
            {"id": "trunk", "name": "Trunk", "cells": [[0, 0], [1, 0], [2, 0], [3, 0]]},
        ),
    },
)


def _normalise(cells: list[list[int]]) -> list[list[int]]:
    top = min(cell[0] for cell in cells)
    left = min(cell[1] for cell in cells)
    return sorted([[cell[0] - top, cell[1] - left] for cell in cells])


def _rotate(cells: list[list[int]]) -> list[list[int]]:
    """A quarter turn clockwise: (row, col) becomes (col, height - 1 - row)."""
    height = max(cell[0] for cell in cells) + 1
    return _normalise([[cell[1], height - 1 - cell[0]] for cell in cells])


def _flip(cells: list[list[int]]) -> list[list[int]]:
    width = max(cell[1] for cell in cells) + 1
    return _normalise([[cell[0], width - 1 - cell[1]] for cell in cells])


def _round_payload(index: int) -> dict[str, Any]:
    puzzle = ROUNDS[index]
    return {
        "title": puzzle["title"],
        "rows": puzzle["rows"],
        "cols": puzzle["cols"],
        "silhouette": [list(cell) for cell in puzzle["silhouette"]],
    }


def _fresh_pieces(index: int) -> list[dict[str, Any]]:
    return [
        {
            "id": piece["id"],
            "name": piece["name"],
            "tone": TONES[order % len(TONES)],
            "cells": _normalise([list(cell) for cell in piece["cells"]]),
            "placed": None,   # {"row": r, "col": c} anchor of the piece's top-left corner
            "by": None,       # who dropped it in
            "held_by": None,  # who has it selected right now
        }
        for order, piece in enumerate(ROUNDS[index]["pieces"])
    ]


def _covered(state: dict[str, Any]) -> set[tuple[int, int]]:
    filled: set[tuple[int, int]] = set()
    for piece in state["pieces"]:
        if piece["placed"]:
            anchor = piece["placed"]
            for cell in piece["cells"]:
                filled.add((anchor["row"] + cell[0], anchor["col"] + cell[1]))
    return filled


def _refresh(state: dict[str, Any]) -> None:
    outline = {(cell[0], cell[1]) for cell in state["puzzle"]["silhouette"]}
    state["solved"] = _covered(state) == outline


def initial_state() -> dict[str, Any]:
    state = {
        "round": 0,
        "total_rounds": len(ROUNDS),
        "puzzle": _round_payload(0),
        "pieces": _fresh_pieces(0),
        "solved": False,
    }
    _refresh(state)
    return state


def _find(state: dict[str, Any], piece_id: Any) -> dict[str, Any] | None:
    return next((piece for piece in state["pieces"] if piece["id"] == piece_id), None)


def apply(state: dict[str, Any], action: dict[str, Any], player_id: str) -> bool:
    kind = action.get("type")
    piece = _find(state, action.get("piece")) if "piece" in action else None

    if kind == "select" and piece:
        for other in state["pieces"]:
            if other["held_by"] == player_id:
                other["held_by"] = None
        piece["held_by"] = player_id
        return True

    if kind in ("rotate", "flip") and piece:
        # Turning a piece takes it back out of the outline, so the board stays honest.
        piece["placed"] = None
        piece["by"] = None
        piece["held_by"] = player_id
        piece["cells"] = _rotate(piece["cells"]) if kind == "rotate" else _flip(piece["cells"])
        _refresh(state)
        return True

    if kind == "lift" and piece:
        if piece["placed"] is None:
            return False
        piece["placed"] = None
        piece["by"] = None
        _refresh(state)
        return True

    if kind == "place" and piece:
        row = action.get("row")
        col = action.get("col")
        if not isinstance(row, int) or not isinstance(col, int):
            return False
        outline = {(cell[0], cell[1]) for cell in state["puzzle"]["silhouette"]}
        taken = {
            (other["placed"]["row"] + cell[0], other["placed"]["col"] + cell[1])
            for other in state["pieces"]
            if other["placed"] and other["id"] != piece["id"]
            for cell in other["cells"]
        }
        wanted = {(row + cell[0], col + cell[1]) for cell in piece["cells"]}
        if not wanted.issubset(outline) or wanted & taken:
            return False
        piece["placed"] = {"row": row, "col": col}
        piece["by"] = player_id
        piece["held_by"] = None
        _refresh(state)
        return True

    if kind == "clear":
        state["pieces"] = _fresh_pieces(state["round"])
        _refresh(state)
        return True

    if kind == "set_round":
        target = action.get("round")
        if isinstance(target, int) and 0 <= target < len(ROUNDS):
            state["round"] = target
            state["puzzle"] = _round_payload(target)
            state["pieces"] = _fresh_pieces(target)
            _refresh(state)
            return True

    return False
