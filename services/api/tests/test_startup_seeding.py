"""Seeding empty collections has to happen under the entry point production actually uses.

The bug this pins was invisible in every local check. `serve.py` mounts the API at /api, and
Starlette hands a mounted sub-application http and websocket scopes only — never the lifespan
scope. So a startup handler registered on `app.main:app` runs for anyone typing
`uvicorn app.main:app` and runs on no deployed instance, which is precisely the environment
the seeding exists to repair. The deployed dashboard kept reporting a class that had answered
nothing while every laptop showed a full fortnight.

Both entry points are asserted here on purpose. Testing only the dev one is what let it
through the first time.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app as api
from app.serve import root
from app.storage import store


@pytest.fixture
def empty_store(monkeypatch):
    """A store where one collection is empty and the seed for it is not."""
    state = {"attempts": [], "students": [{"id": "student-01", "class_id": "class-4a"}]}
    seeded: dict[str, list] = {}

    monkeypatch.setattr(store, "read", lambda name: state.get(name, []))
    # seed_missing writes through the store's own writer, not write_all.
    monkeypatch.setattr(store, "_write",
                        lambda name, rows: (state.__setitem__(name, rows), seeded.__setitem__(name, rows)))
    monkeypatch.setattr("app.storage._read_seed_file",
                        lambda name: [{"id": "att-1"}] if name == "attempts" else [])
    return seeded


def test_the_production_entry_point_seeds_on_startup(empty_store):
    # uvicorn app.serve:root — what scripts/dori.service actually runs.
    with TestClient(root):
        pass
    assert "attempts" in empty_store, (
        "the root app did not seed on startup; a handler registered only on the mounted "
        "API never receives the lifespan scope"
    )


def test_the_dev_entry_point_seeds_on_startup(empty_store):
    # uvicorn app.main:app — what the README tells a developer to run.
    with TestClient(api):
        pass
    assert "attempts" in empty_store


def test_seeding_never_overwrites_a_collection_that_has_rows(monkeypatch):
    """Runtime state is not seed data. A collection with rows is left exactly alone."""
    state = {"attempts": [{"id": "real-attempt"}]}
    written: list[str] = []
    monkeypatch.setattr(store, "read", lambda name: state.get(name, []))
    monkeypatch.setattr(store, "_write", lambda name, rows: written.append(name))
    monkeypatch.setattr("app.storage._read_seed_file",
                        lambda name: [{"id": "seed-attempt"}] if name == "attempts" else [])

    with TestClient(root):
        pass

    assert "attempts" not in written
    assert state["attempts"] == [{"id": "real-attempt"}]
