"""The loop between the teacher and the family, around one child.

One place holds the child's support plan (IEP or 504), shared goals, and the family's
requests to change the plan. The rules mirror real life: a family does not edit an IEP
directly - plan changes go through the team - so a family SUGGESTS an update and the
teacher (as case manager here) records the decision. Goals a teacher writes are active at
once; goals a family proposes wait for teacher approval. Everything is auditable.

Access is the same server-side rule as everywhere else: a teacher sees learners in their
class, a family sees only their own child. Students do not see this surface at all.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import Actor, get_actor, require_role, require_student_access
from ..models import now
from ..storage import store

router = APIRouter(prefix="/support", tags=["support"])


class GoalIn(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    why: str = Field(default="", max_length=600)


class RequestIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class DecideIn(BaseModel):
    action: str  # approve | decline | complete (goals only)


def _require_parent_or_teacher(actor: Actor, student_id: str) -> None:
    if actor.role not in ("teacher", "parent"):
        raise HTTPException(403, "not permitted")
    require_student_access(actor, student_id)


def _plan(student_id: str) -> dict | None:
    return next((p for p in store.read("plans") if p["student_id"] == student_id), None)


def _guardians(student_id: str) -> list[dict]:
    parents = {p["id"]: p for p in store.read("parents")}
    out = []
    for link in store.read("links"):
        if link["student_id"] == student_id and link["parent_id"] in parents:
            person = parents[link["parent_id"]]
            out.append({
                "id": person["id"],
                "display_name": person.get("display_name", ""),
                "relation": person.get("relation", "Parent"),
                "email": person.get("email", ""),
                "phone": person.get("phone", ""),
            })
    return out


@router.get("/students/{student_id}")
def overview(student_id: str, actor: Actor = Depends(get_actor)):
    _require_parent_or_teacher(actor, student_id)
    goals = [g for g in store.read("goals") if g["student_id"] == student_id]
    goals.sort(key=lambda g: g["at"], reverse=True)
    requests = [r for r in store.read("plan_requests") if r["student_id"] == student_id]
    requests.sort(key=lambda r: r["at"], reverse=True)
    return {
        "plan": _plan(student_id),
        "goals": goals,
        "plan_requests": requests,
        "guardians": _guardians(student_id),
    }


@router.post("/students/{student_id}/goals", status_code=201)
def add_goal(student_id: str, body: GoalIn, actor: Actor = Depends(get_actor)):
    _require_parent_or_teacher(actor, student_id)
    names = {p["id"]: p.get("display_name", "") for p in store.read("parents")}
    names.update({t["id"]: t.get("display_name", "") for t in store.read("teachers")})
    row = {
        "id": f"goal-{uuid.uuid4().hex[:8]}",
        "student_id": student_id,
        "title": body.title.strip(),
        "why": body.why.strip(),
        # A teacher's goal is live at once; a family's waits for the teacher.
        "status": "active" if actor.role == "teacher" else "proposed",
        "created_by": actor.user_id,
        "created_by_name": names.get(actor.user_id, ""),
        "created_by_role": actor.role,
        "at": now(),
        "decided_by": None,
    }
    store.append("goals", row)
    store.append("audit", {"actor": actor.user_id, "action": "goal.create",
                           "object_id": row["id"], "at": row["at"]})
    return row


@router.post("/goals/{goal_id}/decide")
def decide_goal(goal_id: str, body: DecideIn, actor: Actor = Depends(require_role("teacher"))):
    rows = store.read("goals")
    row = next((g for g in rows if g["id"] == goal_id), None)
    if row is None:
        raise HTTPException(404, "unknown goal")
    require_student_access(actor, row["student_id"])
    moves = {"approve": ("proposed", "active"), "decline": ("proposed", "declined"),
             "complete": ("active", "met")}
    if body.action not in moves:
        raise HTTPException(400, "unknown action")
    was, becomes = moves[body.action]
    if row["status"] != was:
        raise HTTPException(409, f"goal is {row['status']}, not {was}")
    row["status"] = becomes
    row["decided_by"] = actor.user_id
    store.upsert("goals", row)
    store.append("audit", {"actor": actor.user_id, "action": f"goal.{body.action}",
                           "object_id": goal_id, "at": now()})
    return row


@router.post("/students/{student_id}/plan-requests", status_code=201)
def request_plan_update(student_id: str, body: RequestIn,
                        actor: Actor = Depends(require_role("parent"))):
    require_student_access(actor, student_id)
    if _plan(student_id) is None:
        raise HTTPException(404, "no plan on file")
    names = {p["id"]: p.get("display_name", "") for p in store.read("parents")}
    row = {
        "id": f"planreq-{uuid.uuid4().hex[:8]}",
        "student_id": student_id,
        "text": body.text.strip(),
        "status": "proposed",
        "by": actor.user_id,
        "by_name": names.get(actor.user_id, ""),
        "at": now(),
        "decided_by": None,
    }
    store.append("plan_requests", row)
    store.append("audit", {"actor": actor.user_id, "action": "plan_request.create",
                           "object_id": row["id"], "at": row["at"]})
    return row


@router.post("/plan-requests/{request_id}/decide")
def decide_plan_request(request_id: str, body: DecideIn,
                        actor: Actor = Depends(require_role("teacher"))):
    rows = store.read("plan_requests")
    row = next((r for r in rows if r["id"] == request_id), None)
    if row is None:
        raise HTTPException(404, "unknown request")
    require_student_access(actor, row["student_id"])
    if body.action not in ("approve", "decline"):
        raise HTTPException(400, "unknown action")
    if row["status"] != "proposed":
        raise HTTPException(409, "already decided")
    row["status"] = "accepted" if body.action == "approve" else "declined"
    row["decided_by"] = actor.user_id
    store.upsert("plan_requests", row)
    if body.action == "approve":
        plan = _plan(row["student_id"])
        teachers = {t["id"]: t.get("display_name", "") for t in store.read("teachers")}
        if plan is not None:
            plan.setdefault("amendments", []).append({
                "text": row["text"],
                "by": f"{row['by_name']} (family), agreed by {teachers.get(actor.user_id, 'the teacher')}",
                "role": "family",
                "at": now()[:10],
            })
            store.upsert("plans", plan)
    store.append("audit", {"actor": actor.user_id, "action": f"plan_request.{body.action}",
                           "object_id": request_id, "at": now()})
    return row
