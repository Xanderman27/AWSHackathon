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


@router.get("/children")
def children(actor: Actor = Depends(require_role("parent"))):
    return [{"id": s["id"], "display_name": s["display_name"], "grade": s["grade"]}
            for s in store.read("students") if s["id"] in actor.student_ids]


@router.get("/children/{student_id}/progress")
def progress(student_id: str, actor: Actor = Depends(require_role("parent"))):
    require_student_access(actor, student_id)
    skills = {s["id"]: s for s in store.read("skills")}
    student = next(s for s in store.read("students") if s["id"] == student_id)
    out = []
    for m in store.read("mastery"):
        if m["student_id"] != student_id:
            continue
        sk = skills[m["skill_id"]]
        out.append({
            "skill": sk["child_name"],
            "practiced": f"{student['display_name']} {PLAIN[bkt.band(m['estimate'])]} {sk['child_name']}.",
            "sessions": m.get("evidence_count", 0),
        })
    # Parents see only what they need: name and grade. No class, no goal-link marker (PRD §6).
    safe_student = {"id": student["id"], "display_name": student["display_name"], "grade": student["grade"]}
    return {"student": safe_student, "what_we_practiced": out, "next_steps": [], "conference": None}
