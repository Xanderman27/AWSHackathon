"""Local JSON storage adapter. Same interface a DynamoDB adapter will implement later.

State lives in data/state/ (gitignored). Seed lives in data/seed/. reset() copies seed over state.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SEED = ROOT / "data" / "seed"
STATE = ROOT / "data" / "state"

COLLECTIONS = ["skills", "items", "students", "links", "attempts", "mastery", "audit",
               "recommendations", "conference_slots", "conference_requests",
               "teachers", "parents", "message_threads", "messages", "group_activities", "accounts",
               "assignments", "class_photos"]

# Binary uploads (classroom photos) sit next to the JSON rather than inside it.
SEED_UPLOADS = SEED / "uploads"
UPLOADS = STATE / "uploads"


class LocalStore:
    def __init__(self) -> None:
        STATE.mkdir(parents=True, exist_ok=True)
        UPLOADS.mkdir(parents=True, exist_ok=True)
        for name in COLLECTIONS:
            if not (STATE / f"{name}.json").exists():
                src = SEED / f"{name}.json"
                if src.exists():
                    shutil.copy(src, STATE / f"{name}.json")
                else:
                    self._write(name, [])

    def _path(self, name: str) -> Path:
        return STATE / f"{name}.json"

    def read(self, name: str) -> list[dict[str, Any]]:
        return json.loads(self._path(name).read_text(encoding="utf-8"))

    def read_seed(self, name: str) -> list[dict[str, Any]]:
        """Read static content that is never mutated (e.g. the resources library)."""
        return json.loads((SEED / f"{name}.json").read_text(encoding="utf-8"))

    def write_all(self, name: str, rows: list[dict[str, Any]]) -> None:
        self._write(name, rows)

    def _write(self, name: str, rows: list[dict[str, Any]]) -> None:
        self._path(name).write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def upsert(self, name: str, row: dict[str, Any], key: str = "id") -> None:
        rows = self.read(name)
        for i, r in enumerate(rows):
            if r.get(key) == row[key]:
                rows[i] = row
                break
        else:
            rows.append(row)
        self._write(name, rows)

    def upsert_mastery(self, row: dict[str, Any]) -> None:
        rows = self.read("mastery")
        for i, r in enumerate(rows):
            if r["student_id"] == row["student_id"] and r["skill_id"] == row["skill_id"]:
                rows[i] = row
                break
        else:
            rows.append(row)
        self._write("mastery", rows)

    def append(self, name: str, row: dict[str, Any]) -> None:
        rows = self.read(name)
        rows.append(row)
        self._write(name, rows)

    def upload_path(self, filename: str) -> Path:
        """Resolve a stored filename, refusing anything that climbs out of the folder."""
        candidate = (UPLOADS / filename).resolve()
        if candidate.parent != UPLOADS.resolve():
            raise ValueError("bad upload path")
        return candidate

    def reset(self) -> None:
        # Wipe uploads and restore the seeded ones, so a reset really is a clean classroom.
        if UPLOADS.exists():
            shutil.rmtree(UPLOADS)
        UPLOADS.mkdir(parents=True, exist_ok=True)
        if SEED_UPLOADS.exists():
            for src in SEED_UPLOADS.iterdir():
                if src.is_file():
                    shutil.copy(src, UPLOADS / src.name)
        for name in COLLECTIONS:
            src = SEED / f"{name}.json"
            if src.exists():
                shutil.copy(src, STATE / f"{name}.json")
            else:
                self._write(name, [])


store = LocalStore()
