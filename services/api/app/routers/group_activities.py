"""Teacher-approved collaborative activities and the student's view of what they were given.

Grouping is a suggestion, never an assignment the platform makes on its own: the teacher sees
the reason, moves anyone they like, and has to publish before a single learner sees anything.
Groups are temporary and activity-specific (PRD §12), and the rationale never reaches a
student or a parent.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import games
from ..auth import Actor, require_role
from ..models import now
from ..storage import store

router = APIRouter(tags=["group activities"])

DEFAULT_GROUP_SIZE = 3
MIN_EVIDENCE = 3


class GroupDraft(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    member_ids: list[str] = Field(min_length=2, max_length=4)
    rationale: str = Field(default="Teacher-created group", max_length=500)


class PublishGroupsIn(BaseModel):
    game_id: str
    groups: list[GroupDraft] = Field(min_length=1, max_length=6)


def _require_game(game_id: str):
    spec = games.spec(game_id)
    if spec is None:
        raise HTTPException(404, "unknown game")
    return spec


def _chunk(rows: list, size: int) -> list[list]:
    """Split into groups of `size`, folding a leftover single into the group before it."""
    chunks = [rows[index:index + size] for index in range(0, len(rows), size)]
    if len(chunks) > 1 and len(chunks[-1]) == 1:
        chunks[-2].extend(chunks.pop())
    return chunks


def _recommendation(actor: Actor, game_id: str) -> dict:
    spec = _require_game(game_id)
    students = [student for student in store.read("students") if student["id"] in actor.student_ids]
    students.sort(key=lambda student: student["display_name"])
    skill_id = spec.grouping_skill_id

    if skill_id:
        evidence = {
            row["student_id"]: row
            for row in store.read("mastery")
            if row["skill_id"] == skill_id and row["student_id"] in actor.student_ids
        }
        eligible = [row for row in evidence.values() if row.get("evidence_count", 0) >= MIN_EVIDENCE]
        eligible.sort(key=lambda row: row["estimate"])
        chunks = _chunk(eligible, DEFAULT_GROUP_SIZE)
        skill_name = next(
            (skill["name"].lower() for skill in store.read("skills") if skill["id"] == skill_id),
            skill_id,
        )
        method = f"Similar need · recent {skill_name} evidence · groups of {DEFAULT_GROUP_SIZE}–4"
        groups = [
            {
                "id": f"recommended-{index + 1}",
                "name": f"Team {index + 1}",
                "member_ids": [row["student_id"] for row in chunk],
                "rationale": (
                    f"Similar-need recommendation: these learners have recent evidence on "
                    f"{skill_name} in a nearby range "
                    f"({min(row['estimate'] for row in chunk):.2f}–{max(row['estimate'] for row in chunk):.2f}). "
                    "Goal links, disability, demographic, and behavior data were not used."
                ),
            }
            for index, chunk in enumerate(chunks)
        ]
        needs_more = [
            student["id"] for student in students
            if evidence.get(student["id"], {}).get("evidence_count", 0) < MIN_EVIDENCE
        ]
        counts = {student["id"]: evidence.get(student["id"], {}).get("evidence_count", 0) for student in students}
    else:
        # This game does not read from any objective, so nobody is held back for want of
        # evidence and the class is simply split into even, mixed groups.
        chunks = _chunk(students, DEFAULT_GROUP_SIZE)
        method = f"Mixed groups · no assessment evidence used · groups of {DEFAULT_GROUP_SIZE}–4"
        groups = [
            {
                "id": f"recommended-{index + 1}",
                "name": f"Team {index + 1}",
                "member_ids": [student["id"] for student in chunk],
                "rationale": (
                    "This activity is free play and is not tied to an objective, so the class "
                    "is split into even mixed groups. No assessment, goal-link, disability, "
                    "demographic, or behavior data was used."
                ),
            }
            for index, chunk in enumerate(chunks)
        ]
        needs_more = []
        counts = {student["id"]: 0 for student in students}

    return {
        "game_id": spec.id,
        "title": spec.title,
        "glyph": spec.glyph,
        "teacher_note": spec.teacher_note,
        "uses_evidence": skill_id is not None,
        "method": method,
        "students": [
            {
                "id": student["id"],
                "display_name": student["display_name"],
                "evidence_count": counts[student["id"]],
            }
            for student in students
        ],
        "groups": groups,
        "needs_more_evidence": needs_more,
        "student_names": {student["id"]: student["display_name"] for student in students},
    }


@router.get("/teacher/group-activities/recommendation")
def recommended_groups(
    game_id: str = Query(...),
    actor: Actor = Depends(require_role("teacher")),
):
    return _recommendation(actor, game_id)


@router.get("/teacher/group-activities")
def teacher_group_activities(actor: Actor = Depends(require_role("teacher"))):
    return [
        activity for activity in store.read("group_activities")
        if activity["class_id"] in actor.class_ids and activity["status"] == "published"
    ]


@router.post("/teacher/group-activities/publish")
def publish_group_activities(
    body: PublishGroupsIn,
    actor: Actor = Depends(require_role("teacher")),
):
    spec = _require_game(body.game_id)
    seen: set[str] = set()
    for group in body.groups:
        if not spec.min_group <= len(group.member_ids) <= spec.max_group:
            raise HTTPException(400, f"each group needs {spec.min_group}–{spec.max_group} learners")
        duplicate = seen.intersection(group.member_ids)
        if duplicate:
            raise HTTPException(400, "a learner can be assigned to only one group for this activity")
        if not set(group.member_ids).issubset(actor.student_ids):
            raise HTTPException(403, "one or more learners are outside this class")
        seen.update(group.member_ids)

    class_id = sorted(actor.class_ids)[0]
    published_at = now()
    # Republishing replaces this class's groups for this game only; other games keep theirs.
    activities = [
        activity for activity in store.read("group_activities")
        if not (activity["class_id"] == class_id and activity["game_id"] == spec.id)
    ]
    new_activities = []
    for group in body.groups:
        activity = {
            "id": f"group-activity-{uuid4().hex[:10]}",
            "class_id": class_id,
            "game_id": spec.id,
            "title": spec.title,
            "group_name": group.name.strip(),
            "member_ids": group.member_ids,
            "rationale": group.rationale,
            "status": "published",
            "created_by": actor.user_id,
            "published_at": published_at,
        }
        activities.append(activity)
        new_activities.append(activity)
    store.write_all("group_activities", activities)
    store.append("audit", {
        "id": f"audit-{uuid4().hex[:12]}",
        "actor": actor.user_id,
        "action": "group_activities_published",
        "object_id": spec.id,
        "after": {"activity_ids": [activity["id"] for activity in new_activities]},
        "timestamp": published_at,
    })
    return {"activities": new_activities}


@router.delete("/teacher/group-activities/{game_id}")
def unpublish_group_activities(game_id: str, actor: Actor = Depends(require_role("teacher"))):
    """Take one game's groups back off every learner's screen."""
    _require_game(game_id)
    class_id = sorted(actor.class_ids)[0]
    remaining = [
        activity for activity in store.read("group_activities")
        if not (activity["class_id"] == class_id and activity["game_id"] == game_id)
    ]
    store.write_all("group_activities", remaining)
    store.append("audit", {
        "id": f"audit-{uuid4().hex[:12]}",
        "actor": actor.user_id,
        "action": "group_activities_unpublished",
        "object_id": game_id,
        "timestamp": now(),
    })
    return {"activities": remaining}


@router.get("/student/group-activities")
def student_group_activities(actor: Actor = Depends(require_role("student"))):
    students = {student["id"]: student for student in store.read("students")}
    assigned = []
    for activity in store.read("group_activities"):
        if activity["status"] != "published" or actor.user_id not in activity["member_ids"]:
            continue
        spec = games.spec(activity["game_id"])
        if spec is None:
            continue
        assigned.append({
            "id": activity["id"],
            "game_id": activity["game_id"],
            "title": spec.title,
            "glyph": spec.glyph,
            "tone": spec.tone,
            "group_name": activity["group_name"],
            "teammates": [
                {"id": student_id, "display_name": students[student_id]["display_name"]}
                for student_id in activity["member_ids"]
                if student_id != actor.user_id and student_id in students
            ],
            "member_count": len(activity["member_ids"]),
            # The teacher's reason for the grouping stays with the teacher (PRD §12).
            "instructions": spec.instructions,
            "published_at": activity["published_at"],
        })
    return assigned
