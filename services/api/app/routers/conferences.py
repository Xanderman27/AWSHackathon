"""Parent-teacher conference scheduling (PRD §15).

Teacher publishes slots, parent requests one with an optional agenda, teacher confirms.
No model is involved: scheduling is deterministic and auditable.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import Actor, get_actor, require_role, require_student_access
from ..models import now
from ..storage import store

router = APIRouter(prefix="/conferences", tags=["conferences"])

TEACHER_ID = "teacher-01"
TEACHER_NAME = "Ms. Rivera"
SLOT_TIMES = [time(15, 30), time(16, 0), time(16, 30), time(17, 0)]
HORIZON_DAYS = 21
# Times the teacher has kept for other commitments, so the calendar is not uniformly full.
BUSY = {(0, 2), (0, 3), (1, 1), (2, 0), (3, 2), (3, 3)}

ACTIVE = ("pending", "confirmed")


def _ensure_slots() -> list[dict]:
    """Materialise open slots for the next three weeks so the demo always has real dates."""
    slots = store.read("conference_slots")
    existing = {s["start"] for s in slots}
    today = date.today()
    added = False
    for offset in range(1, HORIZON_DAYS + 1):
        d = today + timedelta(days=offset)
        if d.weekday() > 3:  # Monday–Thursday only
            continue
        for idx, t in enumerate(SLOT_TIMES):
            if (d.weekday(), idx) in BUSY:
                continue
            start = datetime.combine(d, t).isoformat(timespec="minutes")
            if start in existing:
                continue
            slots.append({
                "id": f"slot-{uuid.uuid4().hex[:8]}",
                "teacher_id": TEACHER_ID,
                "teacher_name": TEACHER_NAME,
                "start": start,
                "minutes": 20,
                "status": "open",
            })
            added = True
    if added:
        slots.sort(key=lambda s: s["start"])
        store.write_all("conference_slots", slots)
    return slots


def _taken_slot_ids() -> set[str]:
    return {r["slot_id"] for r in store.read("conference_requests") if r["status"] in ACTIVE}


class RequestIn(BaseModel):
    student_id: str
    slot_id: str
    agenda: str = Field(default="", max_length=500)


class DecisionIn(BaseModel):
    decision: Literal["confirm", "decline"]


@router.get("/slots")
def open_slots(actor: Actor = Depends(get_actor)):
    """Open times a parent can request. Students never see this."""
    if actor.role == "student":
        raise HTTPException(403, "not permitted")
    taken = _taken_slot_ids()
    return [s for s in _ensure_slots() if s["status"] == "open" and s["id"] not in taken]


@router.get("/requests")
def list_requests(actor: Actor = Depends(get_actor)):
    rows = store.read("conference_requests")
    if actor.role == "parent":
        rows = [r for r in rows if r["parent_id"] == actor.user_id]
    elif actor.role == "teacher":
        rows = [r for r in rows if r["student_id"] in actor.student_ids]
    else:
        raise HTTPException(403, "not permitted")
    students = {s["id"]: s["display_name"] for s in store.read("students")}
    for r in rows:
        r["student_name"] = students.get(r["student_id"], "")
    return sorted(rows, key=lambda r: r["start"])


@router.post("/requests", status_code=201)
def create_request(body: RequestIn, actor: Actor = Depends(require_role("parent"))):
    require_student_access(actor, body.student_id)
    slot = next((s for s in _ensure_slots() if s["id"] == body.slot_id), None)
    if slot is None:
        raise HTTPException(404, "unknown time")
    if body.slot_id in _taken_slot_ids():
        raise HTTPException(409, "That time was just taken. Please pick another.")
    row = {
        "id": f"conf-{uuid.uuid4().hex[:8]}",
        "parent_id": actor.user_id,
        "student_id": body.student_id,
        "teacher_id": slot["teacher_id"],
        "teacher_name": slot["teacher_name"],
        "slot_id": slot["id"],
        "start": slot["start"],
        "minutes": slot["minutes"],
        "agenda": body.agenda.strip(),
        "status": "pending",
        "created_at": now(),
        "decided_at": None,
    }
    store.append("conference_requests", row)
    store.append("audit", {"actor": actor.user_id, "action": "conference.request",
                           "object_id": row["id"], "at": row["created_at"]})
    return row


@router.post("/requests/{request_id}/decision")
def decide(request_id: str, body: DecisionIn, actor: Actor = Depends(require_role("teacher"))):
    rows = store.read("conference_requests")
    row = next((r for r in rows if r["id"] == request_id), None)
    if row is None or row["student_id"] not in actor.student_ids:
        raise HTTPException(404, "unknown request")
    row["status"] = "confirmed" if body.decision == "confirm" else "declined"
    row["decided_at"] = now()
    store.upsert("conference_requests", row)
    store.append("audit", {"actor": actor.user_id, "action": f"conference.{body.decision}",
                           "object_id": row["id"], "at": row["decided_at"]})
    return row


@router.delete("/requests/{request_id}")
def cancel(request_id: str, actor: Actor = Depends(require_role("parent"))):
    rows = store.read("conference_requests")
    row = next((r for r in rows if r["id"] == request_id), None)
    if row is None or row["parent_id"] != actor.user_id:
        raise HTTPException(404, "unknown request")
    row["status"] = "cancelled"
    row["decided_at"] = now()
    store.upsert("conference_requests", row)
    store.append("audit", {"actor": actor.user_id, "action": "conference.cancel",
                           "object_id": row["id"], "at": row["decided_at"]})
    return row
