"""Layer 2: adaptive item selection by maximum Fisher information with a success floor.

Routing rules (PRD §9.4) are explicit here, not learned.
"""

from __future__ import annotations

import math
import zlib
from typing import Optional

from ..models import Item, ItemResponse
from .bkt import theta

SUCCESS_FLOOR = 0.60
EASY_BAND_MAX_DIFFICULTY = 2


def p_correct(th: float, a: float, b: float) -> float:
    return 1.0 / (1.0 + math.exp(-a * (th - b)))


def information(th: float, a: float, b: float) -> float:
    p = p_correct(th, a, b)
    return a * a * p * (1 - p)


def should_route_to_prerequisite(responses: list[ItemResponse], items_by_id: dict[str, Item]) -> bool:
    if len(responses) < 2:
        return False
    last_two = responses[-2:]
    return all(
        not r.correct and items_by_id[r.item_id].difficulty <= EASY_BAND_MAX_DIFFICULTY for r in last_two
    )


VARIETY_TOP = 3


def next_item(
    estimate: float,
    skill_id: str,
    bank: list[Item],
    seen_ids: set[str],
    variety_key: str = "",
) -> Optional[Item]:
    """Most informative item the learner has a fair shot at.

    `variety_key` breaks ties among the top few near-equally-informative items with a stable
    hash instead of always taking the single maximum. It must be the same for every call
    within one selection (the answer endpoint re-derives the served item), which is why it
    is a caller-supplied key and not a random draw.
    """
    th = theta(estimate)
    candidates = [i for i in bank if i.skill_id == skill_id and i.approved and i.id not in seen_ids]
    if not candidates:
        return None
    above_floor = [i for i in candidates if p_correct(th, i.irt_a, i.irt_b) >= SUCCESS_FLOOR]
    if not above_floor:
        return min(candidates, key=lambda i: i.irt_b)  # nothing meets the floor: easiest available
    ranked = sorted(above_floor, key=lambda i: information(th, i.irt_a, i.irt_b), reverse=True)
    if not variety_key:
        return ranked[0]
    top = ranked[:VARIETY_TOP]
    return top[zlib.crc32(variety_key.encode()) % len(top)]
