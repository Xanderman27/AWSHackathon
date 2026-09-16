"""Student-facing practice path.

The path shows progress as steps on a track, never as a score, percentage, or label
(PRD §6: students do not see mastery numbers). Steps are derived server-side from the
same mastery estimate the teacher sees, so practicing genuinely moves the path.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..models import now

from ..auth import Actor, require_role
from ..storage import store

router = APIRouter(prefix="/student", tags=["student"])

SUBJECT_ORDER = ["english", "science", "math", "history", "geography"]


def _benchmarks_for(student_id: str) -> dict:
    return {b["subject"]: b["at"] for b in store.read("benchmarks") if b["student_id"] == student_id}


def _growth_steps(student_id: str, skill_id: str, since: str | None, cap: int) -> int:
    """Steps are GROWTH: one per quiz finished after the subject check-in.

    The mastery estimate from the check-in only tunes which questions appear; it never
    pre-fills the path. Every learner starts their path at zero and earns forward.
    """
    if since is None:
        return 0
    done = sum(1 for a in store.read("attempts")
               if a["student_id"] == student_id and a["skill_id"] == skill_id
               and a.get("completed") and a.get("started_at", "") > since)
    return min(cap, done)


@router.get("/path")
def path(actor: Actor = Depends(require_role("student"))):
    total_steps = 5
    mastery = {m["skill_id"]: m for m in store.read("mastery") if m["student_id"] == actor.user_id}
    skills = sorted(store.read("skills"),
                    key=lambda s: (SUBJECT_ORDER.index(s["subject"]) if s["subject"] in SUBJECT_ORDER else 99,
                                   s["grade"]))
    benchmarks = _benchmarks_for(actor.user_id)
    tracks = []
    per_subject: dict[str, int] = {}
    bench_skill: dict[str, str] = {}
    for sk in skills:
        subj = sk["subject"]
        per_subject[subj] = per_subject.get(subj, 0) + 1
        # The check-in runs on the subject's grade-level skill (the highest grade listed).
        cur = bench_skill.get(subj)
        if cur is None or sk["grade"] >= next(x["grade"] for x in skills if x["id"] == cur):
            bench_skill[subj] = sk["id"]
        tracks.append({
            "skill_id": sk["id"],
            "unit": per_subject[subj],
            "title": sk["child_name"],
            "subject": subj,
            "steps_done": _growth_steps(actor.user_id, sk["id"], benchmarks.get(subj), total_steps),
            "total_steps": total_steps,
            "started": sk["id"] in mastery,
        })
    return {
        "tracks": tracks,
        "stars": sum(t["steps_done"] for t in tracks),
        "benchmarks": {subj: benchmarks.get(subj) for subj in SUBJECT_ORDER},
        "bench_skill": bench_skill,
    }


@router.post("/benchmarks/{subject}", status_code=201)
def mark_benchmark(subject: str, actor: Actor = Depends(require_role("student"))):
    """Called when the learner finishes a subject check-in. Idempotent."""
    if subject not in SUBJECT_ORDER:
        raise HTTPException(404, "unknown subject")
    rows = store.read("benchmarks")
    if any(b["student_id"] == actor.user_id and b["subject"] == subject for b in rows):
        return {"subject": subject, "already": True}
    row = {"student_id": actor.user_id, "subject": subject, "at": now()}
    store.append("benchmarks", row)
    store.append("audit", {"actor": actor.user_id, "action": "benchmark.complete",
                           "object_id": subject, "at": row["at"]})
    return row


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
