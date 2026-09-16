"""Layer 1: Bayesian Knowledge Tracing, item-aware variant (KT-IDEM).

Pure functions. No I/O. See docs/LEARNER_MODEL.md for the derivation and a worked example.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillParams:
    p_init: float = 0.30
    p_learn: float = 0.15
    p_guess: float = 0.20
    p_slip: float = 0.10


HINT_GUESS = 0.35  # a correct answer after a hint is weaker evidence

# Bands from PRD §9.3
BUILDING_MAX = 0.40
EXTENSION_MIN = 0.80


def item_guess_slip(params: SkillParams, irt_a: float, irt_b: float) -> tuple[float, float]:
    """Derive per-item guess and slip from IRT parameters.

    Harder items (b > 0) raise guess slightly and lower slip; easier items do the opposite.
    Discrimination sharpens both. Bounded so the update stays well behaved.
    """
    shift = 0.05 * irt_b * irt_a
    guess = min(0.45, max(0.05, params.p_guess + shift))
    slip = min(0.30, max(0.02, params.p_slip - shift))
    return guess, slip


def update(
    estimate: float,
    correct: bool,
    params: SkillParams,
    irt_a: float = 1.0,
    irt_b: float = 0.0,
    hint_used: bool = False,
) -> float:
    guess, slip = item_guess_slip(params, irt_a, irt_b)
    if hint_used and correct:
        guess = max(guess, HINT_GUESS)
    if correct:
        knew = estimate * (1 - slip)
        did_not = (1 - estimate) * guess
    else:
        knew = estimate * slip
        did_not = (1 - estimate) * (1 - guess)
    posterior = knew / (knew + did_not)
    return posterior + (1 - posterior) * params.p_learn


def band(estimate: float) -> str:
    if estimate < BUILDING_MAX:
        return "building"
    if estimate > EXTENSION_MIN:
        return "extension"
    return "practicing"


def confidence(history: list[float], correct_flags: list[bool]) -> str:
    n = len(correct_flags)
    if n < 3:
        return "low"
    alternating = all(correct_flags[i] != correct_flags[i + 1] for i in range(n - 1))
    if alternating:
        return "medium"
    if n >= 6:
        return "high"
    return "medium"


def theta(estimate: float) -> float:
    """Map a mastery probability onto the IRT ability scale (logit)."""
    e = min(0.98, max(0.02, estimate))
    return math.log(e / (1 - e))
