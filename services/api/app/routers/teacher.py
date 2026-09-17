"""Teacher views: class summary and per-student evidence. Neutral language only (PRD §13)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import classcode
from ..models import now

from ..auth import Actor, require_role, require_student_access
from ..mastery import bkt
from ..storage import store

router = APIRouter(prefix="/teacher", tags=["teacher"])

# How many days of history the dashboard's activity series covers.
DAILY_DAYS = 14

BAND_LABEL = {"building": "Building foundations", "practicing": "Practicing", "extension": "Ready for extension"}


@router.get("/class")
def class_summary(actor: Actor = Depends(require_role("teacher"))):
    students = [s for s in store.read("students") if s["id"] in actor.student_ids]
    mastery = store.read("mastery")
    attempts = store.read("attempts")
    skills = {s["id"]: s for s in store.read("skills")}
    item_skill = {i["id"]: i["skill_id"] for i in store.read("items")}
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
            flags = _correct_flags(attempts, s["id"], m["skill_id"], item_skill)
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
    # Stars are growth: quizzes finished after each learner's subject check-in.
    benchmarks: dict = {}
    for b in store.read("benchmarks"):
        benchmarks[(b["student_id"], b["subject"])] = b["at"]
    per_pair: dict = {}
    for a in attempts:
        if a["student_id"] in my_ids and a.get("completed"):
            sk = skills.get(a["skill_id"])
            since = benchmarks.get((a["student_id"], sk["subject"])) if sk else None
            if since and a.get("started_at", "") > since:
                key = (a["student_id"], a["skill_id"])
                per_pair[key] = per_pair.get(key, 0) + 1
    stars = sum(min(5, n) for n in per_pair.values())
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
        **_depth(rows, attempts, my_ids, store.read("group_activities"), actor.class_ids),
    }
    return {"class_id": sorted(actor.class_ids)[0], "students": students, "mastery": rows,
            "counts": counts, "class_stats": class_stats}


@router.get("/students/{student_id}")
def student_evidence(student_id: str, actor: Actor = Depends(require_role("teacher"))):
    """Everything the learner's own page shows: who they are, where they are per skill, and
    the item-level evidence behind it. One call, because a teacher opening a child wants the
    whole picture, not three spinners."""
    require_student_access(actor, student_id)
    student = next((s for s in store.read("students") if s["id"] == student_id), None)
    if student is None:
        raise HTTPException(404, "unknown learner")

    items = {i["id"]: i for i in store.read("items")}
    skills = {s["id"]: s for s in store.read("skills")}
    attempts = [a for a in store.read("attempts") if a["student_id"] == student_id]

    evidence = []
    questions = 0
    hints = 0
    quests_done = 0
    for a in attempts:
        if a.get("completed"):
            quests_done += 1
        for r in a["responses"]:
            it = items.get(r["item_id"], {})
            questions += 1
            if r.get("hint_used"):
                hints += 1
            evidence.append({
                "attempt_id": a["id"], "at": r["at"], "item_id": r["item_id"],
                "prompt": it.get("prompt", ""), "difficulty": it.get("difficulty"),
                "skill_name": skills.get(it.get("skill_id"), {}).get("name", ""),
                "correct": r["correct"], "hint_used": r["hint_used"],
                "route_reason": r.get("route_reason"),
            })
    evidence.sort(key=lambda row: row["at"], reverse=True)

    mastery = []
    for m in store.read("mastery"):
        if m["student_id"] != student_id:
            continue
        skill = skills.get(m["skill_id"], {})
        flags = [r["correct"] for a in attempts for r in a["responses"]
                 if items.get(r["item_id"], {}).get("skill_id") == m["skill_id"]]
        if len(flags) < m.get("evidence_count", 0):
            flags = [True] * m["evidence_count"]
        mastery.append({
            "skill_id": m["skill_id"],
            "skill_name": skill.get("name", m["skill_id"]),
            "subject": skill.get("subject", ""),
            "standard_id": skill.get("standard_id", ""),
            "estimate": round(m["estimate"], 3),
            "band": BAND_LABEL[bkt.band(m["estimate"])],
            "confidence": bkt.confidence(m.get("history", []), flags),
            "evidence_count": m.get("evidence_count", 0),
            "history": [round(h, 3) for h in m.get("history", [])],
        })
    mastery.sort(key=lambda row: row["estimate"])

    groups = [
        {"id": g["id"], "title": g["title"], "group_name": g["group_name"],
         "teammates": [
             other["display_name"] for other in store.read("students")
             if other["id"] in g["member_ids"] and other["id"] != student_id
         ]}
        for g in store.read("group_activities")
        if g.get("status") == "published" and student_id in g.get("member_ids", [])
    ]

    return {
        "student_id": student_id,
        "student": {
            "id": student["id"], "display_name": student["display_name"],
            "grade": student.get("grade"), "has_goal_link": student.get("has_goal_link", False),
            "photo": student.get("photo"), "avatar": student.get("avatar"),
        },
        "totals": {"questions": questions, "quests_done": quests_done, "hints": hints,
                   "skills_with_evidence": len(mastery)},
        "mastery": mastery,
        "evidence": evidence,
        "group_activities": groups,
    }


def _depth(rows, attempts, my_ids, group_activities, class_ids):
    """The deeper half of the class statistics, all aggregate and all neutral.

    Three things docs/GUIDELINES.md asks a teacher dashboard to show, which class totals alone
    cannot:

    - **Confidence beside the estimate** (§7). A class average with no confidence mix invites a
      decision the evidence cannot support, so the spread of low/medium/high is reported and
      "needs more evidence" is a first-class number rather than an error state (§5.4).
    - **Recent activity, not lifetime totals** (§5.4). Evidence older than a fortnight is not
      evidence of where a learner is now, so the daily series and the "active this week" count
      are both windowed.
    - **Collaboration drift** (§5.9). A grouping feature can satisfy every composition rule on
      any single run and still produce tracking over a term, so groupmate diversity, repeat
      pairings and learners never grouped are surfaced to the teacher.

    Nothing here ranks a learner or names one: this is the classwide tab, and an individual's
    evidence lives on their own page.
    """
    today = datetime.now(timezone.utc).date()
    window_start = today - timedelta(days=DAILY_DAYS - 1)

    # ---- Accuracy, hints and the daily series, from responses inside the window ----
    answered = correct = hinted = 0
    per_day = {str(window_start + timedelta(days=i)): {"answers": 0, "quests": 0}
               for i in range(DAILY_DAYS)}
    active_week = set()
    week_start = str(today - timedelta(days=6))

    for a in attempts:
        if a["student_id"] not in my_ids:
            continue
        for r in a["responses"]:
            answered += 1
            correct += bool(r.get("correct"))
            hinted += bool(r.get("hint_used"))
            day = (r.get("at") or "")[:10]
            if day in per_day:
                per_day[day]["answers"] += 1
            if day >= week_start:
                active_week.add(a["student_id"])
        if a.get("completed"):
            day = (a.get("started_at") or "")[:10]
            if day in per_day:
                per_day[day]["quests"] += 1

    daily = [{"date": day, **counts} for day, counts in sorted(per_day.items())]

    # ---- Confidence mix across every (learner, skill) row ----
    mix = {"low": 0, "medium": 0, "high": 0}
    for row in rows:
        if row["confidence"] in mix:
            mix[row["confidence"]] += 1

    # ---- Collaboration: diversity, repeats, and who has been left out ----
    partners: dict[str, set] = {}
    pair_counts: dict[tuple, int] = {}
    mine = [g for g in group_activities if g.get("class_id") in class_ids]
    for g in mine:
        members = [m for m in g.get("member_ids", []) if m in my_ids]
        for member in members:
            partners.setdefault(member, set()).update(x for x in members if x != member)
        for i, one in enumerate(members):
            for two in members[i + 1:]:
                key = tuple(sorted((one, two)))
                pair_counts[key] = pair_counts.get(key, 0) + 1

    possible = max(len(my_ids) - 1, 1)
    collaboration = {
        "activities": len(mine),
        "learners_grouped": len(partners),
        "never_grouped": len(my_ids - set(partners)),
        # Groupmate diversity: distinct partners as a share of the classmates available.
        "diversity": round(sum(len(v) for v in partners.values()) / len(partners) / possible, 2)
                     if partners else 0.0,
        "repeat_pairs": sum(1 for n in pair_counts.values() if n > 1),
    }

    return {
        "answered_window": answered,
        "accuracy": round(correct / answered, 2) if answered else None,
        "hint_rate": round(hinted / answered, 2) if answered else None,
        "confidence_mix": mix,
        "needs_more_evidence": mix["low"],
        "active_this_week": len(active_week),
        "daily": daily,
        "collaboration": collaboration,
    }


def _correct_flags(attempts, student_id, skill_id, item_skill=None):
    """This learner's correct/incorrect run *for one skill*.

    Each response is attributed to the skill of the item that was answered, not to the skill
    the quest was assigned under, because a quest that routes down to a prerequisite produces
    evidence about the prerequisite (PRD §9.3). `current_skill_id` is the fallback when an
    item is not in the bank any more.

    Filtering by skill is the whole point: confidence gates definitive recommendations and
    cohort placement (docs/GUIDELINES.md §5.4), so pooling a learner's entire answer log
    across every subject would report high confidence on a skill they have barely touched.
    """
    item_skill = item_skill or {}
    flags = []
    for a in attempts:
        if a["student_id"] != student_id:
            continue
        fallback = a.get("current_skill_id") or a.get("skill_id")
        for r in a["responses"]:
            if item_skill.get(r["item_id"], fallback) == skill_id:
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
