"""Layer 2: adaptive item selection by maximum Fisher information with a success floor.

Routing rules (PRD §9.4) are explicit here, not learned.
"""

from __future__ import annotations

import math
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


def next_item(
    estimate: float,
    skill_id: str,
    bank: list[Item],
    seen_ids: set[str],
) -> Optional[Item]:
    th = theta(estimate)
    candidates = [i for i in bank if i.skill_id == skill_id and i.approved and i.id not in seen_ids]
    if not candidates:
        return None
    above_floor = [i for i in candidates if p_correct(th, i.irt_a, i.irt_b) >= SUCCESS_FLOOR]
    pool = above_floor or candidates  # if nothing meets the floor, take the easiest available
    if not above_floor:
        return min(pool, key=lambda i: i.irt_b)
    return max(pool, key=lambda i: information(th, i.irt_a, i.irt_b))
