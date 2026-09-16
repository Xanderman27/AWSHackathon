"""Student-facing practice path.

The path shows progress as steps on a track, never as a score, percentage, or label
(PRD §6: students do not see mastery numbers). Steps are derived server-side from the
same mastery estimate the teacher sees, so practicing genuinely moves the path.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import Actor, require_role
from ..storage import store

router = APIRouter(prefix="/student", tags=["student"])

# A step lights up once the mastery estimate clears its threshold.
STEP_THRESHOLDS = [0.15, 0.35, 0.55, 0.75, 0.92]


@router.get("/path")
def path(actor: Actor = Depends(require_role("student"))):
    mastery = {m["skill_id"]: m for m in store.read("mastery") if m["student_id"] == actor.user_id}
    order = ["english", "science", "math", "history", "geography"]
    skills = sorted(store.read("skills"),
                    key=lambda s: (order.index(s["subject"]) if s["subject"] in order else 99, s["grade"]))
    tracks = []
    per_subject: dict[str, int] = {}
    for sk in skills:
        est = mastery.get(sk["id"], {}).get("estimate", 0.0)
        steps = sum(1 for t in STEP_THRESHOLDS if est >= t)
        per_subject[sk["subject"]] = per_subject.get(sk["subject"], 0) + 1
        tracks.append({
            "skill_id": sk["id"],
            "unit": per_subject[sk["subject"]],
            "title": sk["child_name"],
            "subject": sk["subject"],
            "steps_done": steps,
            "total_steps": len(STEP_THRESHOLDS),
            "started": sk["id"] in mastery,
        })
    return {"tracks": tracks, "stars": sum(t["steps_done"] for t in tracks)}


@router.get("/assignments")
def my_assignments(actor: Actor = Depends(require_role("student"))):
    me = next((s for s in store.read("students") if s["id"] == actor.user_id), None)
    if me is None:
        return []
    skills = {s["id"]: s for s in store.read("skills")}
    out = []
    for a in store.read("assignments"):
        if a["class_id"] != me["class_id"]:
            continue
        if a.get("student_ids") and actor.user_id not in a["student_ids"]:
            continue
        sk = skills.get(a["skill_id"])
        if sk:
            out.append({"assignment_id": a["id"], "skill_id": sk["id"], "title": sk["child_name"],
                        "subject": sk["subject"], "at": a["at"]})
    out.sort(key=lambda r: r["at"], reverse=True)
    return out
