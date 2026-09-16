"""Fraction Strips Together: a shared fraction wall for building equivalent fractions.

Free play, not assessment. The group is given a target such as one half and shades strips of
different sizes until they find every row that covers the same amount. Nothing here is scored
or sent to the teacher; the value is the talking the group does while they shade.
"""

from __future__ import annotations

from typing import Any

from .base import GameSpec

GAME = GameSpec(
    id="fraction-strips",
    title="Fraction Strips Together",
    glyph="🍫",
    tone="sky",
    blurb="Shade the strips together until different rows cover the same amount.",
    instructions="Shade strips until you find every row that covers the same amount as the target.",
    skill_hint="Equivalent fractions",
    grouping_skill_id="fraction_equivalence",
    solo=True,
    teacher_note="Mirrors the equivalent-fractions objective the group already has evidence on.",
)

# (row id, child-facing name, number of pieces)
ROWS: tuple[tuple[str, str, int], ...] = (
    ("halves", "Halves", 2),
    ("thirds", "Thirds", 3),
    ("fourths", "Fourths", 4),
    ("sixths", "Sixths", 6),
    ("eighths", "Eighths", 8),
    ("twelfths", "Twelfths", 12),
)

TARGETS: tuple[dict[str, Any], ...] = (
    {"num": 1, "den": 2, "label": "one half", "words": "1 out of 2 equal pieces"},
    {"num": 2, "den": 3, "label": "two thirds", "words": "2 out of 3 equal pieces"},
    {"num": 3, "den": 4, "label": "three fourths", "words": "3 out of 4 equal pieces"},
    {"num": 1, "den": 3, "label": "one third", "words": "1 out of 3 equal pieces"},
)

ROW_IDS = {row[0] for row in ROWS}
ROW_SIZE = {row[0]: row[2] for row in ROWS}


def _blank_rows() -> dict[str, list[bool]]:
    return {row_id: [False] * size for row_id, _, size in ROWS}


def _blank_editors() -> dict[str, list[str | None]]:
    return {row_id: [None] * size for row_id, _, size in ROWS}


def _matching_rows(state: dict[str, Any]) -> list[str]:
    """Rows whose shaded amount equals the target. Cross-multiplied, so no float rounding."""
    target = TARGETS[state["round"]]
    matched = []
    for row_id, _, size in ROWS:
        shaded = sum(1 for cell in state["rows"][row_id] if cell)
        if shaded and shaded * target["den"] == target["num"] * size:
            matched.append(row_id)
    return matched


def initial_state() -> dict[str, Any]:
    return {
        "round": 0,
        "total_rounds": len(TARGETS),
        "target": TARGETS[0],
        "rows": _blank_rows(),
        "updated_by": _blank_editors(),
        "matched": [],
    }


def _refresh(state: dict[str, Any]) -> None:
    state["target"] = TARGETS[state["round"]]
    state["matched"] = _matching_rows(state)


def apply(state: dict[str, Any], action: dict[str, Any], player_id: str) -> bool:
    kind = action.get("type")

    if kind == "set_cell":
        row = action.get("row")
        index = action.get("index")
        active = action.get("active")
        if row in ROW_IDS and isinstance(index, int) and 0 <= index < ROW_SIZE[row] and isinstance(active, bool):
            state["rows"][row][index] = active
            state["updated_by"][row][index] = player_id if active else None
            _refresh(state)
            return True

    elif kind == "clear_row":
        row = action.get("row")
        if row in ROW_IDS:
            state["rows"][row] = [False] * ROW_SIZE[row]
            state["updated_by"][row] = [None] * ROW_SIZE[row]
            _refresh(state)
            return True

    elif kind == "clear":
        state["rows"] = _blank_rows()
        state["updated_by"] = _blank_editors()
        _refresh(state)
        return True

    elif kind == "set_round":
        index = action.get("round")
        if isinstance(index, int) and 0 <= index < len(TARGETS):
            state["round"] = index
            state["rows"] = _blank_rows()
            state["updated_by"] = _blank_editors()
            _refresh(state)
            return True

    return False
