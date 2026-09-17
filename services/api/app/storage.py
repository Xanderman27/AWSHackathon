"""State, in one of two places: JSON files on disk, or a DynamoDB table.

`STORAGE_BACKEND=local` (the default) keeps the demo runnable on a laptop with no AWS.
`STORAGE_BACKEND=aws` puts every collection in one DynamoDB table and every uploaded photo in
S3, so a restart loses nothing — which is the difference between a container you can deploy
and a container you can only run once.

Both back ends answer the same small interface, and `seed` is always read from the repository:
seed data is content, not state.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from .blobs import Blobs, LocalBlobs, S3Blobs

ROOT = Path(__file__).resolve().parents[3]
SEED = ROOT / "data" / "seed"
STATE = ROOT / "data" / "state"

COLLECTIONS = ["skills", "items", "students", "links", "attempts", "mastery", "audit",
               "recommendations", "conference_slots", "conference_requests",
               "teachers", "parents", "message_threads", "messages", "group_activities", "accounts",
               "assignments", "class_photos", "classes", "benchmarks", "plans", "goals", "plan_requests"]

SEED_UPLOADS = SEED / "uploads"
UPLOADS = STATE / "uploads"

# Rows are identified differently per collection. Anything not listed here is keyed by "id";
# anything with no usable key at all (audit lines) gets a generated one at write time.
NATURAL_KEY: dict[str, tuple[str, ...]] = {
    "mastery": ("student_id", "skill_id"),
    "links": ("parent_id", "student_id"),
    "accounts": ("username",),
}


def _read_seed_file(name: str) -> list[dict[str, Any]]:
    path = SEED / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


class LocalStore:
    """JSON files under data/state/. The demo default."""

    def __init__(self) -> None:
        STATE.mkdir(parents=True, exist_ok=True)
        self.blobs: Blobs = LocalBlobs(UPLOADS)
        for name in COLLECTIONS:
            if not (STATE / f"{name}.json").exists():
                self._write(name, _read_seed_file(name))

    def _path(self, name: str) -> Path:
        return STATE / f"{name}.json"

    def read(self, name: str) -> list[dict[str, Any]]:
        return json.loads(self._path(name).read_text(encoding="utf-8"))

    def read_seed(self, name: str) -> list[dict[str, Any]]:
        """Static content that is never mutated (the resources library)."""
        return _read_seed_file(name)

    def write_all(self, name: str, rows: list[dict[str, Any]]) -> None:
        self._write(name, rows)

    def _write(self, name: str, rows: list[dict[str, Any]]) -> None:
        self._path(name).write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def upsert(self, name: str, row: dict[str, Any], key: str = "id") -> None:
        rows = self.read(name)
        for i, existing in enumerate(rows):
            if existing.get(key) == row[key]:
                rows[i] = row
                break
        else:
            rows.append(row)
        self._write(name, rows)

    def upsert_mastery(self, row: dict[str, Any]) -> None:
        rows = self.read("mastery")
        for i, existing in enumerate(rows):
            if existing["student_id"] == row["student_id"] and existing["skill_id"] == row["skill_id"]:
                rows[i] = row
                break
        else:
            rows.append(row)
        self._write("mastery", rows)

    def append(self, name: str, row: dict[str, Any]) -> None:
        rows = self.read(name)
        rows.append(row)
        self._write(name, rows)

    def reset(self) -> None:
        self.blobs.reset(SEED_UPLOADS)
        for name in COLLECTIONS:
            self._write(name, _read_seed_file(name))


class DynamoStore:
    """One table, partitioned by collection name.

    pk = collection, sk = that row's natural key. Insertion order is preserved with a monotonic
    `_seq` because several callers (attempts, audit, messages) assume append order and a
    DynamoDB query returns sort-key order instead.
    """

    def __init__(self, table_name: str) -> None:
        import boto3
        region = os.getenv("AWS_REGION", "us-east-1")
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)
        self.blobs: Blobs = S3Blobs(os.environ["UPLOADS_BUCKET"])
        self._counter = 0

    def _next_seq(self) -> str:
        # Time plus a counter, so two writes in the same millisecond still order.
        self._counter += 1
        return f"{int(time.time() * 1000):013d}-{self._counter:06d}"

    def _sort_key(self, name: str, row: dict[str, Any]) -> str:
        fields = NATURAL_KEY.get(name, ("id",))
        if all(row.get(field) for field in fields):
            return "#".join(str(row[field]) for field in fields)
        # Audit lines and other append-only rows have no natural key of their own.
        return f"_gen#{self._next_seq()}"

    @staticmethod
    def _clean(item: dict[str, Any]) -> dict[str, Any]:
        # DynamoDB hands back every number as Decimal, and the rest of the app does float
        # arithmetic on mastery estimates — Decimal * float raises. Convert on the way out so
        # a row read from DynamoDB is indistinguishable from one read from JSON.
        return _numbers_to_python({k: v for k, v in item.items() if k not in ("pk", "sk", "_seq")})

    def read(self, name: str) -> list[dict[str, Any]]:
        from boto3.dynamodb.conditions import Key
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {"KeyConditionExpression": Key("pk").eq(name)}
        while True:
            page = self.table.query(**kwargs)
            items.extend(page.get("Items", []))
            if "LastEvaluatedKey" not in page:
                break
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
        items.sort(key=lambda item: item.get("_seq", ""))
        return [self._clean(item) for item in items]

    def read_seed(self, name: str) -> list[dict[str, Any]]:
        return _read_seed_file(name)

    def _put(self, name: str, row: dict[str, Any], seq: str | None = None) -> None:
        self.table.put_item(Item=_floats_to_decimal({
            **row, "pk": name, "sk": self._sort_key(name, row), "_seq": seq or self._next_seq(),
        }))

    def append(self, name: str, row: dict[str, Any]) -> None:
        self._put(name, row)

    def upsert(self, name: str, row: dict[str, Any], key: str = "id") -> None:
        # The natural key already makes this a put: same key, same item, overwritten.
        self._put(name, row)

    def upsert_mastery(self, row: dict[str, Any]) -> None:
        self._put("mastery", row)

    def write_all(self, name: str, rows: list[dict[str, Any]]) -> None:
        """Replace a collection. Rows that survive are overwritten in place, and only the ones
        that disappeared are deleted — a single BatchWriteItem may not both put and delete the
        same key, and DynamoDB rejects the whole request if it does."""
        from boto3.dynamodb.conditions import Key

        existing: set[str] = set()
        kwargs: dict[str, Any] = {"KeyConditionExpression": Key("pk").eq(name),
                                  "ProjectionExpression": "sk"}
        while True:
            page = self.table.query(**kwargs)
            existing.update(item["sk"] for item in page.get("Items", []))
            if "LastEvaluatedKey" not in page:
                break
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

        keep: set[str] = set()
        with self.table.batch_writer() as batch:
            for index, row in enumerate(rows):
                sort_key = self._sort_key(name, row)
                keep.add(sort_key)
                batch.put_item(Item=_floats_to_decimal({
                    **row, "pk": name, "sk": sort_key, "_seq": f"{index:013d}-000000",
                }))

        gone = existing - keep
        if gone:
            with self.table.batch_writer() as batch:
                for sort_key in gone:
                    batch.delete_item(Key={"pk": name, "sk": sort_key})

    def reset(self) -> None:
        self.blobs.reset(SEED_UPLOADS)
        for name in COLLECTIONS:
            self.write_all(name, _read_seed_file(name))


def _numbers_to_python(value: Any) -> Any:
    """Decimal back to int or float, whichever it started as."""
    from decimal import Decimal
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: _numbers_to_python(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_numbers_to_python(v) for v in value]
    return value


def _floats_to_decimal(value: Any) -> Any:
    """DynamoDB stores Decimal, not float. Mastery estimates are floats everywhere else."""
    from decimal import Decimal
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _floats_to_decimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_floats_to_decimal(v) for v in value]
    return value


def _build():
    if os.getenv("STORAGE_BACKEND", "local").strip().lower() == "aws":
        return DynamoStore(os.getenv("STATE_TABLE", "dori-state"))
    return LocalStore()


store = _build()
