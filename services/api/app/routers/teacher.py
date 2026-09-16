"""Teacher views: class summary and per-student evidence. Neutral language only (PRD §13)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import Actor, require_role, require_student_access
from ..mastery import bkt
from ..storage import store

router = APIRouter(prefix="/teacher", tags=["teacher"])

BAND_LABEL = {"building": "Building foundations", "practicing": "Practicing", "extension": "Ready for extension"}


@router.get("/class")
def class_summary(actor: Actor = Depends(require_role("teacher"))):
    students = [s for s in store.read("students") if s["id"] in actor.student_ids]
    mastery = store.read("mastery")
    attempts = store.read("attempts")
    skills = {s["id"]: s for s in store.read("skills")}
    rows = []
    for s in students:
        for m in mastery:
            if m["student_id"] != s["id"]:
                continue
            flags = _correct_flags(attempts, s["id"], m["skill_id"])
            # Seeded mastery has history but no item log; treat it as consistent evidence.
            if len(flags) < m.get("evidence_count", 0):
                flags = [True] * m["evidence_count"]
            rows.append({
                "student_id": s["id"],
                "display_name": s["display_name"],
                "has_goal_link": s.get("has_goal_link", False),
                "skill_id": m["skill_id"],
                "skill_name": skills[m["skill_id"]]["name"],
                "band": BAND_LABEL[bkt.band(m["estimate"])],
                "estimate": round(m["estimate"], 2),
                "confidence": bkt.confidence(m.get("history", []), flags),
                "evidence_count": m.get("evidence_count", 0),
            })
    counts = {"needs_more_evidence": sum(1 for r in rows if r["confidence"] == "low"),
              "ready_for_extension": sum(1 for r in rows if r["band"] == "Ready for extension")}
    # Classwide statistics (neutral, aggregate; no rankings).
    my_ids = {s["id"] for s in students}
    responses = 0
    hints = 0
    quests_done = 0
    active = set()
    for a in store.read("attempts"):
        if a["student_id"] not in my_ids:
            continue
        responses += len(a["responses"])
        hints += sum(1 for r in a["responses"] if r.get("hint_used"))
        if a.get("completed"):
            quests_done += 1
        if a["responses"]:
            active.add(a["student_id"])
    thresholds = [0.15, 0.35, 0.55, 0.75, 0.92]
    stars = sum(sum(1 for t in thresholds if m["estimate"] >= t)
                for m in mastery if m["student_id"] in my_ids)
    ests = [m["estimate"] for m in mastery if m["student_id"] in my_ids]
    by_subject: dict = {}
    for m in mastery:
        if m["student_id"] not in my_ids:
            continue
        subj = skills[m["skill_id"]]["subject"]
        by_subject.setdefault(subj, []).append(m["estimate"])
    subject_stats = [{"subject": k, "learners": len(v), "avg": round(sum(v) / len(v), 2)}
                     for k, v in sorted(by_subject.items())]
    class_stats = {
        "checkins": responses, "quests_done": quests_done, "stars": stars, "hints": hints,
        "active_learners": len(active | {m["student_id"] for m in mastery if m["student_id"] in my_ids}),
        "avg_estimate": round(sum(ests) / len(ests), 2) if ests else None,
        "subjects": subject_stats,
    }
    return {"class_id": sorted(actor.class_ids)[0], "students": students, "mastery": rows,
            "counts": counts, "class_stats": class_stats}


@router.get("/students/{student_id}")
def student_evidence(student_id: str, actor: Actor = Depends(require_role("teacher"))):
    require_student_access(actor, student_id)
    items = {i["id"]: i for i in store.read("items")}
    attempts = [a for a in store.read("attempts") if a["student_id"] == student_id]
    evidence = []
    for a in attempts:
        for r in a["responses"]:
            it = items[r["item_id"]]
            evidence.append({
                "attempt_id": a["id"], "at": r["at"], "item_id": r["item_id"], "prompt": it["prompt"],
                "difficulty": it["difficulty"], "correct": r["correct"], "hint_used": r["hint_used"],
                "route_reason": r.get("route_reason"),
            })
    mastery = [m for m in store.read("mastery") if m["student_id"] == student_id]
    return {"student_id": student_id, "mastery": mastery, "evidence": evidence}


def _correct_flags(attempts, student_id, skill_id):
    flags = []
    for a in attempts:
        if a["student_id"] != student_id:
            continue
        for r in a["responses"]:
            flags.append(r["correct"])
    return flags
