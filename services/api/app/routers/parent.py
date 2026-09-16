"""Parent view: linked children only, plain language, no numbers, no peers."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import Actor, require_role, require_student_access
from ..mastery import bkt
from ..storage import store

router = APIRouter(prefix="/parent", tags=["parent"])

PLAIN = {
    "building": "is building the first steps of",
    "practicing": "is practicing",
    "extension": "is ready to stretch further with",
}

BAND_LABEL = {"building": "Building foundations", "practicing": "Practicing", "extension": "Ready to stretch"}

NEXT_STEP_FIELDS = ("id", "title", "why", "minutes", "materials", "steps", "approved_by", "approved_on")


def _safe(student: dict) -> dict:
    """Parents see name and grade. No class, no goal-link marker (PRD §6)."""
    return {"id": student["id"], "display_name": student["display_name"], "grade": student["grade"]}


@router.get("/children")
def children(actor: Actor = Depends(require_role("parent"))):
    return [_safe(s) for s in store.read("students") if s["id"] in actor.student_ids]


@router.get("/children/{student_id}/progress")
def progress(student_id: str, actor: Actor = Depends(require_role("parent"))):
    require_student_access(actor, student_id)
    skills = {s["id"]: s for s in store.read("skills")}
    student = next(s for s in store.read("students") if s["id"] == student_id)
    practiced = []
    mastery_rows = []
    for m in store.read("mastery"):
        if m["student_id"] != student_id:
            continue
        sk = skills[m["skill_id"]]
        band = bkt.band(m["estimate"])
        practiced.append({
            "skill": sk["child_name"],
            "practiced": f"{student['display_name']} {PLAIN[band]} {sk['child_name']}.",
            "sessions": m.get("evidence_count", 0),
        })
        # This child only. The 0-4 score is the mastery estimate on a family-friendly scale;
        # no classmates, no ranks (PRD §6).
        mastery_rows.append({
            "skill_id": m["skill_id"],
            "skill": sk["name"],
            "child_name": sk["child_name"],
            "estimate": round(m["estimate"], 3),
            "score": round(m["estimate"] * 4, 1),
            "band": band,
            "band_label": BAND_LABEL[band],
            "evidence_count": m.get("evidence_count", 0),
            "history": [round(h * 4, 2) for h in m.get("history", [])],
        })
    avg = round(sum(r["estimate"] for r in mastery_rows) / len(mastery_rows) * 4, 1) if mastery_rows else None
    # Only teacher-approved, family-facing activities reach a parent (PRD FR-15).
    next_steps = [
        {k: r[k] for k in NEXT_STEP_FIELDS}
        for r in store.read("recommendations")
        if r["student_id"] == student_id and r["status"] == "approved" and r["audience"] == "family"
    ]
    return {"student": _safe(student), "what_we_practiced": practiced, "next_steps": next_steps,
            "mastery": mastery_rows, "average_score": avg}
