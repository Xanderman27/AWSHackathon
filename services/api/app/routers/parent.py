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
            "mastery": mastery_rows, "average_score": avg,
            **_profile_extras(student_id, skills)}


STEP_THRESHOLDS = [0.15, 0.35, 0.55, 0.75, 0.92]


def _profile_extras(student_id: str, skills: dict) -> dict:
    """Duolingo-profile-style stats, computed fresh from the child's own records."""
    responses = 0
    quests_done = 0
    hints = 0
    for a in store.read("attempts"):
        if a["student_id"] != student_id:
            continue
        responses += len(a["responses"])
        hints += sum(1 for r in a["responses"] if r.get("hint_used"))
        if a.get("completed"):
            quests_done += 1

    stars = 0
    subjects = set()
    for m in store.read("mastery"):
        if m["student_id"] != student_id:
            continue
        stars += sum(1 for t in STEP_THRESHOLDS if m["estimate"] >= t)
        sk = skills.get(m["skill_id"])
        if sk and m.get("evidence_count", 0) > 0:
            subjects.add(sk["subject"])

    groups = []
    students = {st["id"]: st["display_name"] for st in store.read("students")}
    for g in store.read("group_activities"):
        if g.get("status") == "published" and student_id in g.get("member_ids", []):
            groups.append({
                "id": g["id"], "title": g["title"], "group_name": g["group_name"],
                "teammates": [students.get(m, "A classmate") for m in g["member_ids"] if m != student_id],
            })

    stats = {"stars": stars, "checkins": responses, "quests_done": quests_done,
             "subjects": len(subjects), "hints": hints, "group_count": len(groups)}

    def ach(id, title, desc, icon, have, need):
        return {"id": id, "title": title, "desc": desc, "icon": icon,
                "progress": min(have, need), "goal": need, "earned": have >= need}

    achievements = [
        ach("first-quest", "First Steps", "Finish 1 quest", "flag", quests_done, 1),
        ach("star-collector", "Star Collector", "Earn 5 stars on the path", "star", stars, 5),
        ach("adventurer", "Adventurer", "Practice in 3 different subjects", "map", len(subjects), 3),
        ach("practice-pro", "Practice Pro", "Answer 25 questions", "bolt", responses, 25),
        ach("team-player", "Team Player", "Join a group activity", "team", len(groups), 1),
        ach("wise-owl", "Good Asker", "Use a hint 3 times (asking for help is smart!)", "bulb", hints, 3),
    ]
    return {"stats": stats, "achievements": achievements, "group_activities": groups}
