"""Direct messages between a parent and their child's teacher.

Who may talk to whom is decided by the server, never by the client. A parent can only reach
the teacher of a child they are linked to; a teacher can only reach parents of students in
their own class. Students have no access to messaging at all.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import Actor, get_actor
from ..models import now
from ..storage import store

router = APIRouter(prefix="/messages", tags=["messages"])

PREVIEW_CHARS = 90


def _people() -> tuple[dict, dict, dict]:
    teachers = {t["id"]: t for t in store.read("teachers")}
    parents = {p["id"]: p for p in store.read("parents")}
    students = {s["id"]: s for s in store.read("students")}
    return teachers, parents, students


def _teacher_for_student(student_id: str, students: dict, teachers: dict) -> dict | None:
    klass = students.get(student_id, {}).get("class_id")
    return next((t for t in teachers.values() if t["class_id"] == klass), None)


def _parents_for_student(student_id: str) -> list[str]:
    return [l["parent_id"] for l in store.read("links") if l["student_id"] == student_id]


def _pairs_for(actor: Actor) -> list[dict]:
    """Every (parent, teacher, student) triple this actor is allowed to message about."""
    teachers, parents, students = _people()
    out: list[dict] = []
    if actor.role == "parent":
        for link in store.read("links"):
            if link["parent_id"] != actor.user_id:
                continue
            student = students.get(link["student_id"])
            teacher = _teacher_for_student(link["student_id"], students, teachers)
            if student and teacher:
                out.append({
                    "student_id": student["id"], "student_name": student["display_name"],
                    "parent_id": actor.user_id, "teacher_id": teacher["id"],
                    "contact_id": teacher["id"], "contact_name": teacher["display_name"],
                    "contact_role": "teacher", "contact_subtitle": f"{student['display_name']}'s teacher",
                })
    elif actor.role == "teacher":
        me = teachers.get(actor.user_id)
        if not me:
            return []
        for student in students.values():
            if student["class_id"] != me["class_id"]:
                continue
            for parent_id in _parents_for_student(student["id"]):
                parent = parents.get(parent_id)
                if not parent:
                    continue
                out.append({
                    "student_id": student["id"], "student_name": student["display_name"],
                    "parent_id": parent_id, "teacher_id": me["id"],
                    "contact_id": parent_id, "contact_name": parent["display_name"],
                    "contact_role": "parent", "contact_subtitle": f"{student['display_name']}'s guardian",
                })
    return out


def _my_threads(actor: Actor) -> list[dict]:
    key = "parent_id" if actor.role == "parent" else "teacher_id"
    return [t for t in store.read("message_threads") if t.get(key) == actor.user_id]


def _require_role(actor: Actor) -> None:
    if actor.role not in ("parent", "teacher"):
        raise HTTPException(403, "not permitted")


def _decorate(thread: dict, actor: Actor, msgs: list[dict], teachers: dict, parents: dict, students: dict) -> dict:
    mine = [m for m in msgs if m["thread_id"] == thread["id"]]
    mine.sort(key=lambda m: m["at"])
    last = mine[-1] if mine else None
    other_id = thread["teacher_id"] if actor.role == "parent" else thread["parent_id"]
    other = (teachers if actor.role == "parent" else parents).get(other_id, {})
    return {
        **thread,
        "with_name": other.get("display_name", "Unknown"),
        "with_role": "teacher" if actor.role == "parent" else "parent",
        "student_name": students.get(thread["student_id"], {}).get("display_name", ""),
        "preview": (last["body"][:PREVIEW_CHARS] + "…") if last and len(last["body"]) > PREVIEW_CHARS
                   else (last["body"] if last else ""),
        "last_at": last["at"] if last else thread["created_at"],
        "unread": sum(1 for m in mine if m["sender_id"] != actor.user_id and actor.user_id not in m.get("read_by", [])),
    }


class NewThread(BaseModel):
    student_id: str
    subject: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=4000)


class NewMessage(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


@router.get("/contacts")
def contacts(actor: Actor = Depends(get_actor)):
    """Who this person is allowed to start a conversation with."""
    _require_role(actor)
    return _pairs_for(actor)


@router.get("/threads")
def threads(actor: Actor = Depends(get_actor)):
    _require_role(actor)
    teachers, parents, students = _people()
    msgs = store.read("messages")
    rows = [_decorate(t, actor, msgs, teachers, parents, students) for t in _my_threads(actor)]
    rows.sort(key=lambda r: r["last_at"], reverse=True)
    return {"threads": rows, "unread": sum(r["unread"] for r in rows)}


@router.post("/threads", status_code=201)
def create_thread(body: NewThread, actor: Actor = Depends(get_actor)):
    _require_role(actor)
    pair = next((p for p in _pairs_for(actor) if p["student_id"] == body.student_id), None)
    if pair is None:
        # Either the student does not exist or this actor has no relationship to them.
        raise HTTPException(403, "not permitted")
    thread = {
        "id": f"thr-{uuid.uuid4().hex[:8]}",
        "parent_id": pair["parent_id"],
        "teacher_id": pair["teacher_id"],
        "student_id": pair["student_id"],
        "subject": body.subject.strip(),
        "created_by": actor.user_id,
        "created_at": now(),
    }
    store.append("message_threads", thread)
    _append_message(thread["id"], actor, body.body)
    store.append("audit", {"actor": actor.user_id, "action": "message.thread.create",
                           "object_id": thread["id"], "at": thread["created_at"]})
    teachers, parents, students = _people()
    return _decorate(thread, actor, store.read("messages"), teachers, parents, students)


@router.get("/threads/{thread_id}")
def read_thread(thread_id: str, actor: Actor = Depends(get_actor)):
    _require_role(actor)
    thread = _load(thread_id, actor)
    msgs = [m for m in store.read("messages") if m["thread_id"] == thread_id]
    msgs.sort(key=lambda m: m["at"])
    # Opening a thread marks it read for this reader only.
    changed = False
    for m in msgs:
        if m["sender_id"] != actor.user_id and actor.user_id not in m.get("read_by", []):
            m.setdefault("read_by", []).append(actor.user_id)
            changed = True
    if changed:
        everything = store.read("messages")
        by_id = {m["id"]: m for m in msgs}
        store.write_all("messages", [by_id.get(m["id"], m) for m in everything])
    teachers, parents, students = _people()
    return {"thread": _decorate(thread, actor, store.read("messages"), teachers, parents, students),
            "messages": msgs}


@router.post("/threads/{thread_id}", status_code=201)
def send(thread_id: str, body: NewMessage, actor: Actor = Depends(get_actor)):
    _require_role(actor)
    _load(thread_id, actor)
    msg = _append_message(thread_id, actor, body.body)
    return msg


def _append_message(thread_id: str, actor: Actor, body: str) -> dict:
    teachers, parents, _ = _people()
    who = (teachers if actor.role == "teacher" else parents).get(actor.user_id, {})
    msg = {
        "id": f"msg-{uuid.uuid4().hex[:8]}",
        "thread_id": thread_id,
        "sender_id": actor.user_id,
        "sender_role": actor.role,
        "sender_name": who.get("display_name", actor.user_id),
        "body": body.strip(),
        "at": now(),
        "read_by": [actor.user_id],
    }
    store.append("messages", msg)
    return msg


def _load(thread_id: str, actor: Actor) -> dict:
    key = "parent_id" if actor.role == "parent" else "teacher_id"
    for t in store.read("message_threads"):
        if t["id"] == thread_id:
            if t.get(key) != actor.user_id:
                raise HTTPException(403, "not permitted")
            return t
    raise HTTPException(404, "unknown conversation")
