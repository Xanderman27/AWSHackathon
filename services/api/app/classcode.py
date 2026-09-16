"""Class codes: the thing a teacher reads out so a family can find their classroom.

Codes are short, spoken aloud, and typed by someone who may be doing it on a phone in a
corridor, so the alphabet leaves out every character people mix up: no O/0, no I/1/L, no
lowercase. Lookup is case-insensitive and ignores spaces and dashes.
"""

from __future__ import annotations

import secrets

from .storage import store

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LENGTH = 7


def generate() -> str:
    """A fresh code that no class is already using."""
    taken = {row.get("code", "").upper() for row in store.read("classes")}
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
        if code not in taken:
            return code


def normalise(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def find_class(code: str) -> dict | None:
    wanted = normalise(code)
    if not wanted:
        return None
    return next((row for row in store.read("classes") if normalise(row.get("code", "")) == wanted), None)


def class_for_teacher(teacher_id: str, class_ids: set[str]) -> dict | None:
    return next(
        (row for row in store.read("classes")
         if row["id"] in class_ids or row.get("teacher_id") == teacher_id),
        None,
    )
