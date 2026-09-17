import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (attempts, class_photos, conferences, family_updates, games,
                      group_activities, login, messages, parent, recommendations, resources,
                      student, support, teacher)
from .storage import store

app = FastAPI(title="Adaptive Learning Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attempts.router)
app.include_router(teacher.router)
app.include_router(parent.router)
app.include_router(conferences.router)
app.include_router(resources.router)
app.include_router(messages.router)
app.include_router(games.router)
app.include_router(group_activities.router)
app.include_router(class_photos.router)
app.include_router(family_updates.router)
app.include_router(recommendations.router)
app.include_router(student.router)
app.include_router(login.router)
app.include_router(support.router)


@app.get("/health")
def health():
    return {"ok": True}


def _commit() -> str:
    """The commit this process is running, read once at import.

    The instance updates itself from main, so "which version is live" is a real question with
    a changing answer. Without this you are comparing timestamps and hoping.
    """
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parents[3], capture_output=True, text=True, timeout=3,
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


COMMIT = _commit()
STARTED_AT = datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.get("/version")
def version():
    """What is actually deployed right now. Public: it reveals nothing but a commit hash."""
    return {"commit": COMMIT, "started_at": STARTED_AT}


@app.get("/skills")
def skills():
    return store.read("skills")


@app.post("/demo/reset")
def reset():
    store.reset()
    return {"ok": True}
