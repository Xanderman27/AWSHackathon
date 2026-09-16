"""Grounded activity recommendations: propose, review, approve (PRD FR-10, FR-11, FR-17, FR-18).

Nothing generated here reaches a family until a teacher approves it. The draft is written
with status "proposed" so the proposal itself is on the record, the teacher's decision is a
second audited event, and only an approved family-audience row is picked up by the parent
dashboard — which already reads exactly this collection.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..ai import config as ai_config
from ..ai.generate import propose
from ..ai.schema import DraftDecision
from ..auth import Actor, require_role, require_student_access
from ..mastery import bkt
from ..models import now
from ..storage import store

router = APIRouter(prefix="/teacher", tags=["recommendations"])


class DraftIn(BaseModel):
    student_id: str
    skill_id: str


def _evidence(student_id: str, skill_id: str) -> tuple[str, int, float]:
    """Band, how much evidence, and how often they reach for a hint. Nothing identifying."""
    row = next((m for m in store.read("mastery")
                if m["student_id"] == student_id and m["skill_id"] == skill_id), None)
    if row is None:
        return "building", 0, 0.0

    items = {i["id"]: i for i in store.read("items")}
    answers = [
        r for a in store.read("attempts") if a["student_id"] == student_id
        for r in a["responses"] if items.get(r["item_id"], {}).get("skill_id") == skill_id
    ]
    hint_rate = (sum(1 for r in answers if r.get("hint_used")) / len(answers)) if answers else 0.0
    return bkt.band(row["estimate"]), row.get("evidence_count", 0), hint_rate


@router.get("/ai/status")
def ai_status(actor: Actor = Depends(require_role("teacher"))):
    """Where drafts are coming from right now, so the screen never implies a live model."""
    return ai_config.status()


@router.get("/recommendations")
def list_recommendations(student_id: str | None = None,
                         actor: Actor = Depends(require_role("teacher"))):
    rows = [r for r in store.read("recommendations") if r["student_id"] in actor.student_ids]
    if student_id:
        require_student_access(actor, student_id)
        rows = [r for r in rows if r["student_id"] == student_id]
    rows.sort(key=lambda r: r.get("proposed_at") or r.get("approved_on") or "", reverse=True)
    return rows


@router.post("/recommendations/draft", status_code=201)
def draft(body: DraftIn, actor: Actor = Depends(require_role("teacher"))):
    require_student_access(actor, body.student_id)
    skill = next((s for s in store.read("skills") if s["id"] == body.skill_id), None)
    if skill is None:
        raise HTTPException(404, "unknown skill")

    band, evidence_count, hint_rate = _evidence(body.student_id, body.skill_id)
    result = propose(body.skill_id, skill["name"], band, evidence_count, hint_rate)
    if result.draft is None:
        # Insufficient or unsupported: ask for more evidence rather than assert (FR-19).
        raise HTTPException(422, result.warning or "No draft could be grounded in an approved source.")

    row = {
        "id": f"rec-{uuid4().hex[:8]}",
        "student_id": body.student_id,
        "skill_id": body.skill_id,
        "audience": "family",
        "status": "proposed",
        **result.draft.model_dump(),
        "citations": result.citations,
        "origin": result.origin,
        "pipeline_path": result.path,
        "warning": result.warning,
        "proposed_at": now(),
        "approved_by": None,
        "approved_on": None,
    }
    store.append("recommendations", row)
    store.append("audit", {"actor": actor.user_id, "action": "recommendation.proposed",
                           "object_id": row["id"],
                           "after": {"origin": result.origin, "path": result.path,
                                     "citations": [c["id"] for c in result.citations]},
                           "at": row["proposed_at"]})
    return row


@router.post("/recommendations/{recommendation_id}/decision")
def decide(recommendation_id: str, body: DraftDecision,
           actor: Actor = Depends(require_role("teacher"))):
    rows = store.read("recommendations")
    row = next((r for r in rows if r["id"] == recommendation_id), None)
    if row is None or row["student_id"] not in actor.student_ids:
        raise HTTPException(404, "unknown recommendation")
    if row["status"] != "proposed":
        raise HTTPException(409, "that recommendation has already been decided")

    if body.edited is not None:
        # A teacher edit is the teacher's text now, so the origin says so.
        row.update(body.edited.model_dump())
        row["origin"] = f"{row.get('origin', 'cached')}+teacher-edited"

    decided_at = now()
    if body.decision == "approve":
        row["status"] = "approved"
        row["approved_by"] = actor.user_id
        row["approved_on"] = decided_at
    else:
        row["status"] = "rejected"
        row["approved_by"] = None
        row["approved_on"] = None
    row["teacher_note"] = body.note.strip()
    store.upsert("recommendations", row)
    store.append("audit", {"actor": actor.user_id, "action": f"recommendation.{body.decision}",
                           "object_id": row["id"], "at": decided_at})
    return row
