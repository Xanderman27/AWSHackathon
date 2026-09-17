"""Role resolution from a verified token, and authorization on the data layer (PRD FR-26).

The caller presents a bearer token; `identity` verifies its signature and hands back a
Principal. Nothing here trusts anything the client says about itself — the previous X-Role
and X-User-Id headers let anyone claim to be a teacher and read any learner's IEP.

Authorization still happens here, on the data layer, not by hiding buttons: every route
receives an Actor carrying the ids it may touch, and the scope is derived from stored records
rather than from the request.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Header, HTTPException

from .identity import InvalidToken, Principal, principal_from_token
from .storage import store

UNAUTHENTICATED = "Sign in to continue."


@dataclass
class Actor:
    role: str
    user_id: str
    student_ids: set[str] = field(default_factory=set)  # students this actor may read
    class_ids: set[str] = field(default_factory=set)


def _bearer(header: str | None) -> str:
    if not header or not header.lower().startswith("bearer "):
        raise HTTPException(401, UNAUTHENTICATED)
    return header[7:].strip()


def actor_for(principal: Principal) -> Actor:
    """Widen a verified identity into the set of records it may reach."""
    actor = Actor(role=principal.role, user_id=principal.user_id)
    if principal.role == "student":
        actor.student_ids = {principal.user_id}
    elif principal.role == "parent":
        actor.student_ids = {
            link["student_id"] for link in store.read("links")
            if link["parent_id"] == principal.user_id
        }
    elif principal.role == "teacher":
        # From the teacher's own record, not a constant: a token proves who you are, and the
        # data decides what that reaches. A teacher with no record reaches nothing.
        actor.class_ids = {
            row["class_id"] for row in store.read("teachers")
            if row["id"] == principal.user_id and row.get("class_id")
        }
        actor.student_ids = {
            s["id"] for s in store.read("students") if s.get("class_id") in actor.class_ids
        }
    return actor


def get_actor(authorization: str | None = Header(default=None)) -> Actor:
    try:
        principal = principal_from_token(_bearer(authorization))
    except InvalidToken:
        raise HTTPException(401, UNAUTHENTICATED) from None
    return actor_for(principal)


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
