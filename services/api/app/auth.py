"""Synthetic role resolution for the hackathon. Cognito replaces this later (PRD FR-26).

The caller sends X-Role and X-User-Id headers. Authorization is enforced here, on the data
layer, not by hiding buttons: every route receives an Actor with the IDs it may touch.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Header, HTTPException

from .storage import store


@dataclass
class Actor:
    role: str
    user_id: str
    student_ids: set[str] = field(default_factory=set)  # students this actor may read
    class_ids: set[str] = field(default_factory=set)


def get_actor(
    x_role: str = Header(default="student"),
    x_user_id: str = Header(default="student-01"),
) -> Actor:
    if x_role not in ("student", "teacher", "parent"):
        raise HTTPException(400, "unknown role")
    actor = Actor(role=x_role, user_id=x_user_id)
    students = store.read("students")
    if x_role == "student":
        actor.student_ids = {x_user_id}
    elif x_role == "parent":
        actor.student_ids = {l["student_id"] for l in store.read("links") if l["parent_id"] == x_user_id}
    elif x_role == "teacher":
        # Skeleton: one teacher owns one class. Class assignments come from seed later.
        actor.class_ids = {"class-4a"}
        actor.student_ids = {s["id"] for s in students if s["class_id"] in actor.class_ids}
    return actor


def require_student_access(actor: Actor, student_id: str) -> None:
    if student_id not in actor.student_ids:
        # Deny with no data, and do not reveal whether the student exists.
        raise HTTPException(403, "not permitted")


def require_role(*roles: str):
    def dep(actor: Actor = Depends(get_actor)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(403, "not permitted")
        return actor

    return dep
