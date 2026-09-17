"""DynamoStore against a fake table.

Both bugs this file pins were found by running the real thing and are invisible on the local
JSON back end: DynamoDB hands every number back as Decimal, and a single BatchWriteItem may
not both put and delete the same key.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from app.storage import DynamoStore


class FakeBatch:
    """Stands in for boto3's batch_writer, and rejects duplicate keys exactly as DynamoDB does."""

    def __init__(self, table):
        self.table = table
        self.seen: set[tuple[str, str]] = set()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def _claim(self, key):
        if key in self.seen:
            raise ValueError("Provided list of item keys contains duplicates")
        self.seen.add(key)

    def put_item(self, Item):
        self._claim((Item["pk"], Item["sk"]))
        self.table.items[(Item["pk"], Item["sk"])] = Item

    def delete_item(self, Key):
        self._claim((Key["pk"], Key["sk"]))
        self.table.items.pop((Key["pk"], Key["sk"]), None)


class FakeTable:
    def __init__(self):
        self.items: dict[tuple[str, str], dict] = {}

    def put_item(self, Item):
        self.items[(Item["pk"], Item["sk"])] = Item

    def batch_writer(self):
        return FakeBatch(self)

    def query(self, **kwargs):
        # The condition is always pk == <collection>; pull the value back out of it.
        wanted = kwargs["KeyConditionExpression"]._values[1]
        rows = [dict(item) for (pk, _), item in self.items.items() if pk == wanted]
        if kwargs.get("ProjectionExpression") == "sk":
            rows = [{"sk": r["sk"]} for r in rows]
        return {"Items": rows}


@pytest.fixture
def store():
    table = FakeTable()
    with patch.object(DynamoStore, "__init__", lambda self, name: None):
        instance = DynamoStore("fake")
    instance.table = table
    instance.blobs = None
    instance._counter = 0
    return instance


def test_replacing_a_collection_does_not_put_and_delete_the_same_key(store):
    """The first version of write_all queued a delete and a put for every surviving row in one
    batch, which DynamoDB rejects outright — so demo reset silently did nothing."""
    store.write_all("links", [{"parent_id": "p1", "student_id": "s1"},
                              {"parent_id": "p2", "student_id": "s2"}])
    # No exception, and a second identical write is also fine.
    store.write_all("links", [{"parent_id": "p1", "student_id": "s1"},
                              {"parent_id": "p2", "student_id": "s2"}])
    assert len(store.read("links")) == 2


def test_rows_that_vanished_are_actually_removed(store):
    store.append("links", {"parent_id": "p1", "student_id": "s1"})
    store.append("links", {"parent_id": "extra", "student_id": "s3"})
    assert len(store.read("links")) == 2

    store.write_all("links", [{"parent_id": "p1", "student_id": "s1"}])
    assert [r["parent_id"] for r in store.read("links")] == ["p1"]


def test_numbers_come_back_as_python_not_decimal(store):
    """The app does float arithmetic on mastery estimates; Decimal * float raises."""
    store.upsert_mastery({"student_id": "s1", "skill_id": "k1", "estimate": 0.48,
                          "evidence_count": 6, "history": [0.3, 0.48]})
    row = store.read("mastery")[0]
    assert isinstance(row["estimate"], float) and row["estimate"] == 0.48
    assert isinstance(row["evidence_count"], int) and row["evidence_count"] == 6
    assert all(isinstance(value, float) for value in row["history"])
    assert row["estimate"] * 4 == pytest.approx(1.92)  # would raise on a Decimal


def test_floats_are_stored_as_decimal(store):
    store.upsert_mastery({"student_id": "s1", "skill_id": "k1", "estimate": 0.48})
    stored = next(iter(store.table.items.values()))
    assert isinstance(stored["estimate"], Decimal)


def test_a_natural_key_makes_upsert_replace_rather_than_duplicate(store):
    for estimate in (0.1, 0.9):
        store.upsert_mastery({"student_id": "s1", "skill_id": "k1", "estimate": estimate})
    rows = store.read("mastery")
    assert len(rows) == 1 and rows[0]["estimate"] == 0.9


def test_rows_without_a_natural_key_all_survive_and_keep_their_order(store):
    """Audit lines have no id. They must not collide onto one key."""
    for step in range(5):
        store.append("audit", {"actor": "t", "action": f"step-{step}"})
    assert [r["action"] for r in store.read("audit")] == [f"step-{i}" for i in range(5)]
