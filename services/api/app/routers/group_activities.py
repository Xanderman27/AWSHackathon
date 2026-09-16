"""Teacher-approved collaborative activities and student assignment views."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import Actor, require_role
from ..models import now
from ..storage import store

router = APIRouter(tags=["group activities"])

GAME_ID = "beat-together"
TARGET_SKILL = "fraction_equivalence"


class GroupDraft(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    member_ids: list[str] = Field(min_length=2, max_length=4)
    rationale: str = Field(default="Teacher-created group", max_length=500)


class PublishGroupsIn(BaseModel):
    groups: list[GroupDraft] = Field(min_length=1, max_length=6)


def _recommendation(actor: Actor) -> dict:
    students = [student for student in store.read("students") if student["id"] in actor.student_ids]
    student_by_id = {student["id"]: student for student in students}
    evidence = {
        row["student_id"]: row
        for row in store.read("mastery")
        if row["skill_id"] == TARGET_SKILL and row["student_id"] in actor.student_ids
    }
    eligible = [
        row for row in evidence.values()
        if row.get("evidence_count", 0) >= 3
    ]
    eligible.sort(key=lambda row: row["estimate"])

    chunks = [eligible[index:index + 3] for index in range(0, len(eligible), 3)]
    if len(chunks) > 1 and len(chunks[-1]) == 1:
        chunks[-2].extend(chunks.pop())

    groups = []
    for index, chunk in enumerate(chunks):
        low = min(row["estimate"] for row in chunk)
        high = max(row["estimate"] for row in chunk)
        groups.append({
            "id": f"recommended-{index + 1}",
            "name": f"Jam Team {index + 1}",
            "member_ids": [row["student_id"] for row in chunk],
            "rationale": (
                "Similar-need recommendation: these learners have recent evidence on equivalent "
                f"fractions in a nearby range ({low:.2f}–{high:.2f}). Goal links, disability, "
                "demographic, and behavior data were not used."
            ),
        })

    needs_more = [
        student["id"] for student in students
        if student["id"] not in evidence or evidence[student["id"]].get("evidence_count", 0) < 3
    ]
    return {
        "game_id": GAME_ID,
        "title": "Beat Together",
        "method": "Similar need · recent equivalent-fractions evidence · groups of 3–4",
        "students": [
            {
                "id": student["id"],
                "display_name": student["display_name"],
                "evidence_count": evidence.get(student["id"], {}).get("evidence_count", 0),
            }
            for student in students
        ],
        "groups": groups,
        "needs_more_evidence": needs_more,
        "student_names": {student_id: student["display_name"] for student_id, student in student_by_id.items()},
    }


@router.get("/teacher/group-activities/recommendation")
def recommended_groups(actor: Actor = Depends(require_role("teacher"))):
    return _recommendation(actor)


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
    seen: set[str] = set()
    for group in body.groups:
        duplicate = seen.intersection(group.member_ids)
        if duplicate:
            raise HTTPException(400, "a learner can be assigned to only one group for this activity")
        if not set(group.member_ids).issubset(actor.student_ids):
            raise HTTPException(403, "one or more learners are outside this class")
        seen.update(group.member_ids)

    class_id = sorted(actor.class_ids)[0]
    published_at = now()
    activities = [
        activity for activity in store.read("group_activities")
        if not (activity["class_id"] == class_id and activity["game_id"] == GAME_ID)
    ]
    new_activities = []
    for group in body.groups:
        activity = {
            "id": f"group-activity-{uuid4().hex[:10]}",
            "class_id": class_id,
            "game_id": GAME_ID,
            "title": "Beat Together",
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
        "object_id": GAME_ID,
        "after": {"activity_ids": [activity["id"] for activity in new_activities]},
        "timestamp": published_at,
    })
    return {"activities": new_activities}


@router.get("/student/group-activities")
def student_group_activities(actor: Actor = Depends(require_role("student"))):
    students = {student["id"]: student for student in store.read("students")}
    assigned = []
    for activity in store.read("group_activities"):
        if activity["status"] != "published" or actor.user_id not in activity["member_ids"]:
            continue
        assigned.append({
            "id": activity["id"],
            "game_id": activity["game_id"],
            "title": activity["title"],
            "group_name": activity["group_name"],
            "teammates": [
                {"id": student_id, "display_name": students[student_id]["display_name"]}
                for student_id in activity["member_ids"]
                if student_id != actor.user_id and student_id in students
            ],
            "member_count": len(activity["member_ids"]),
            "instructions": "Make one looping song together. Everyone can add or remove sounds.",
            "published_at": activity["published_at"],
        })
    return assigned
