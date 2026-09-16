"""Registry of collaborative activities.

Adding a game means writing one module here and listing it below. Nothing else in the app
hard-codes a game id: the router, the teacher's grouping tool, and the student game list all
read this registry.
"""

from __future__ import annotations

from types import ModuleType
from typing import Optional

from . import beat, checkers, detectives, fractions, geography, memory, shapes, sorting
from .base import GameSpec

MODULES: tuple[ModuleType, ...] = (beat, fractions, detectives, memory, sorting, shapes, checkers, geography)

BY_ID: dict[str, ModuleType] = {module.GAME.id: module for module in MODULES}


def spec(game_id: str) -> Optional[GameSpec]:
    module = BY_ID.get(game_id)
    return module.GAME if module else None


def catalog() -> list[dict]:
    """Everything a client needs to render the game list, without importing game logic."""
    return [
        {
            "id": game.id,
            "title": game.title,
            "glyph": game.glyph,
            "tone": game.tone,
            "blurb": game.blurb,
            "instructions": game.instructions,
            "skill_hint": game.skill_hint,
            "min_group": game.min_group,
            "max_group": game.max_group,
            "solo": game.solo,
            "teacher_note": game.teacher_note,
        }
        for game in (module.GAME for module in MODULES)
    ]
