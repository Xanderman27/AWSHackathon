"""Teacher views: class summary and per-student evidence. Neutral language only (PRD §13)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import classcode
from ..models import now

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
    quests_done_map: dict = {}
    for a in attempts:
        if a.get("completed"):
            key = (a["student_id"], a["skill_id"])
            quests_done_map[key] = quests_done_map.get(key, 0) + 1
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
                "quests_done": quests_done_map.get((s["id"], m["skill_id"]), 0),
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
    # Proficiency buckets follow the learner-model bands (below 0.40 / 0.40-0.80 / above 0.80).
    subject_stats = [{
        "subject": k, "learners": len(v), "avg": round(sum(v) / len(v), 2),
        "below": sum(1 for e in v if e < 0.40),
        "proficient": sum(1 for e in v if 0.40 <= e <= 0.80),
        "above": sum(1 for e in v if e > 0.80),
    } for k, v in sorted(by_subject.items())]
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


# ---- Quest assignments (PRD FR-02) ----

class AssignIn(BaseModel):
    skill_id: str
    student_ids: list[str] | None = None  # None means the whole class


def _assignment_view(a: dict, skills: dict, students: dict) -> dict:
    sk = skills.get(a["skill_id"], {})
    return {
        **a,
        "skill_name": sk.get("name", a["skill_id"]),
        "subject": sk.get("subject", ""),
        "who": "Whole class" if not a.get("student_ids")
               else ", ".join(students.get(i, i) for i in a["student_ids"]),
    }


@router.get("/assignments")
def list_assignments(actor: Actor = Depends(require_role("teacher"))):
    skills = {s["id"]: s for s in store.read("skills")}
    students = {s["id"]: s["display_name"] for s in store.read("students")}
    rows = [a for a in store.read("assignments") if a["class_id"] in actor.class_ids]
    rows.sort(key=lambda a: a["at"], reverse=True)
    return [_assignment_view(a, skills, students) for a in rows]


@router.post("/assignments", status_code=201)
def create_assignment(body: AssignIn, actor: Actor = Depends(require_role("teacher"))):
    skills = {s["id"]: s for s in store.read("skills")}
    if body.skill_id not in skills:
        raise HTTPException(404, "unknown skill")
    if body.student_ids is not None:
        if not body.student_ids:
            raise HTTPException(400, "pick at least one learner or assign to the whole class")
        if not set(body.student_ids).issubset(actor.student_ids):
            raise HTTPException(403, "one or more learners are outside this class")
    row = {
        "id": f"assign-{uuid.uuid4().hex[:8]}",
        "class_id": sorted(actor.class_ids)[0],
        "skill_id": body.skill_id,
        "student_ids": body.student_ids,
        "assigned_by": actor.user_id,
        "at": now(),
    }
    store.append("assignments", row)
    store.append("audit", {"actor": actor.user_id, "action": "assignment.create",
                           "object_id": row["id"], "at": row["at"]})
    students = {s["id"]: s["display_name"] for s in store.read("students")}
    return _assignment_view(row, skills, students)


@router.delete("/assignments/{assignment_id}")
def remove_assignment(assignment_id: str, actor: Actor = Depends(require_role("teacher"))):
    rows = store.read("assignments")
    keep = [a for a in rows if not (a["id"] == assignment_id and a["class_id"] in actor.class_ids)]
    if len(keep) == len(rows):
        raise HTTPException(404, "unknown assignment")
    store.write_all("assignments", keep)
    store.append("audit", {"actor": actor.user_id, "action": "assignment.remove",
                           "object_id": assignment_id, "at": now()})
    return {"ok": True}


# --- Class code --------------------------------------------------------------------------
# The code a teacher reads out so families can find this classroom. It is the only thing
# standing between a stranger and a sign-up form, so the teacher can replace it at any time
# and old codes stop working the moment they do.


def _my_class(actor: Actor) -> dict:
    klass = classcode.class_for_teacher(actor.user_id, actor.class_ids)
    if klass is None:
        raise HTTPException(404, "no class found for this teacher")
    return klass


def _code_payload(klass: dict) -> dict:
    students_in_class = {s["id"] for s in store.read("students") if s["class_id"] == klass["id"]}
    linked_parents = {
        link["parent_id"] for link in store.read("links") if link["student_id"] in students_in_class
    }
    waiting = sum(1 for p in store.read("parents") if p.get("pending_class_id") == klass["id"])
    return {
        "class_id": klass["id"],
        "class_name": klass.get("name", klass["id"]),
        "code": klass.get("code", ""),
        "families_joined": len(linked_parents),
        "families_choosing": waiting,
    }


@router.get("/class-code")
def class_code(actor: Actor = Depends(require_role("teacher"))):
    return _code_payload(_my_class(actor))


@router.post("/class-code/rotate")
def rotate_class_code(actor: Actor = Depends(require_role("teacher"))):
    """Issue a new code. Families already joined keep their access; the old code stops working."""
    klass = _my_class(actor)
    klass["code"] = classcode.generate()
    store.upsert("classes", klass)
    store.append("audit", {"actor": actor.user_id, "action": "class_code.rotate",
                           "object_id": klass["id"], "at": now()})
    return _code_payload(klass)
