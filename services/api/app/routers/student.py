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
    skills = sorted(store.read("skills"), key=lambda s: (s["grade"], s["subject"]))
    tracks = []
    for i, sk in enumerate(skills):
        est = mastery.get(sk["id"], {}).get("estimate", 0.0)
        steps = sum(1 for t in STEP_THRESHOLDS if est >= t)
        tracks.append({
            "skill_id": sk["id"],
            "unit": i + 1,
            "title": sk["child_name"],
            "subject": sk["subject"],
            "steps_done": steps,
            "total_steps": len(STEP_THRESHOLDS),
            "started": sk["id"] in mastery,
        })
    return {"tracks": tracks, "stars": sum(t["steps_done"] for t in tracks)}
