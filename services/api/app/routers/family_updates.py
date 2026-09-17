"""A note home about one learner, from their teacher to their family.

This is the narrow counterpart to the class blog. A class photo goes to every family in the
room; a family update goes to exactly the guardians linked to one child, because it is about
that child's day: the thing that went well, or the thing the family should hear from the
teacher before they hear it from the child.

Who may see what is decided here, never by the client:

- Only the teacher of the child's own class may write one.
- Only guardians linked to that child may read it. There is no route that returns another
  family's updates, so a guessed id returns the same 404 as an id that does not exist.
- Students never reach this router at all. A note that says "today was hard" is written for
  an adult, and a child reading it in the student portal is a different product decision.

An update carries no category. A good day and a hard day arrive in the same shape, because a
label on the envelope changes how a family reads what is inside before they have read it, and
because the language guide in docs/GUIDELINES.md rules out the deficit vocabulary a "concern"
or "problem" tag would introduce. What happened is in the teacher's own words.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import Actor, require_role
from ..models import now
from ..storage import store

router = APIRouter(tags=["family updates"])

HEADLINE_MAX = 80
NOTE_MAX = 600


class NewUpdate(BaseModel):
    student_id: str
    headline: str = Field(min_length=1, max_length=HEADLINE_MAX)
    note: str = Field(min_length=1, max_length=NOTE_MAX)
    happened_on: str = Field(default="", max_length=10)


def _students() -> dict[str, dict]:
    return {s["id"]: s for s in store.read("students")}


def _guardian_ids(student_id: str) -> list[str]:
    return [link["parent_id"] for link in store.read("links") if link["student_id"] == student_id]


def _guardian_names(student_id: str) -> list[str]:
    parents = {p["id"]: p for p in store.read("parents")}
    return [parents[pid]["display_name"] for pid in _guardian_ids(student_id) if pid in parents]


def _rows_newest_first(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (r.get("happened_on") or "", r["created_at"]), reverse=True)


@router.post("/teacher/family-updates", status_code=201)
def write_update(body: NewUpdate, actor: Actor = Depends(require_role("teacher"))):
    student = _students().get(body.student_id)
    # Same answer for "no such learner" and "not your learner": the teacher of 4B should not be
    # able to discover who is in 4A by watching which ids come back 403.
    if student is None or student["class_id"] not in actor.class_ids:
        raise HTTPException(404, "unknown learner")

    guardians = _guardian_ids(student["id"])
    if not guardians:
        raise HTTPException(409, "No family is linked to this learner yet.")

    teacher = next((t for t in store.read("teachers") if t["id"] == actor.user_id), {})
    row = {
        "id": f"upd-{uuid4().hex[:10]}",
        "student_id": student["id"],
        "class_id": student["class_id"],
        "teacher_id": actor.user_id,
        "teacher_name": teacher.get("display_name", "Your teacher"),
        "headline": body.headline.strip()[:HEADLINE_MAX],
        "note": body.note.strip()[:NOTE_MAX],
        "happened_on": body.happened_on.strip()[:10] or now()[:10],
        "created_at": now(),
        "read_by": [],
    }
    store.append("family_updates", row)
    store.append("audit", {"actor": actor.user_id, "action": "family_update.send",
                           "object_id": row["id"], "at": row["created_at"]})
    return _for_teacher(row)


def _for_teacher(row: dict) -> dict:
    """What the sender sees: their own note, plus who it actually reached."""
    students = _students()
    return {
        **{k: row[k] for k in ("id", "student_id", "headline", "note",
                               "happened_on", "created_at")},
        "student_name": students.get(row["student_id"], {}).get("display_name", ""),
        "sent_to": _guardian_names(row["student_id"]),
        "seen": bool(row.get("read_by")),
    }


def _for_parent(row: dict, actor: Actor) -> dict:
    students = _students()
    return {
        **{k: row[k] for k in ("id", "student_id", "headline", "note",
                               "happened_on", "created_at")},
        "student_name": students.get(row["student_id"], {}).get("display_name", ""),
        "teacher_name": row.get("teacher_name", "Your teacher"),
        "unread": actor.user_id not in row.get("read_by", []),
    }


@router.get("/teacher/family-updates/recipients")
def recipients(actor: Actor = Depends(require_role("teacher"))):
    """Each learner in this class with the guardians a note about them would reach.

    The composer needs this before anything is sent. A teacher picking "Sam" should see that
    the note goes to Jordan Bell by name — a note home is addressed to a person, and a list
    that shows only the child leaves the teacher guessing who is on the other end.

    A learner with nobody linked is returned with an empty list rather than hidden, so the
    gap is visible and fixable instead of the name simply being missing from the menu.
    """
    students = [s for s in store.read("students") if s["class_id"] in actor.class_ids]
    return [{
        "student_id": s["id"],
        "student_name": s["display_name"],
        "guardians": _guardian_names(s["id"]),
    } for s in sorted(students, key=lambda s: s["display_name"])]


@router.get("/teacher/family-updates")
def teacher_updates(actor: Actor = Depends(require_role("teacher"))):
    mine = [r for r in store.read("family_updates") if r["teacher_id"] == actor.user_id]
    return [_for_teacher(r) for r in _rows_newest_first(mine)]


@router.delete("/teacher/family-updates/{update_id}")
def delete_update(update_id: str, actor: Actor = Depends(require_role("teacher"))):
    rows = store.read("family_updates")
    row = next((r for r in rows if r["id"] == update_id), None)
    if row is None or row["teacher_id"] != actor.user_id:
        raise HTTPException(404, "unknown update")
    store.write_all("family_updates", [r for r in rows if r["id"] != update_id])
    store.append("audit", {"actor": actor.user_id, "action": "family_update.delete",
                           "object_id": update_id, "at": now()})
    return {"ok": True}


@router.get("/parent/family-updates")
def parent_updates(actor: Actor = Depends(require_role("parent"))):
    """Updates about this family's own children. actor.student_ids comes from the link table."""
    mine = [r for r in store.read("family_updates") if r["student_id"] in actor.student_ids]
    rows = [_for_parent(r, actor) for r in _rows_newest_first(mine)]
    return {"updates": rows, "unread": sum(1 for r in rows if r["unread"])}


@router.post("/parent/family-updates/{update_id}/read")
def mark_read(update_id: str, actor: Actor = Depends(require_role("parent"))):
    rows = store.read("family_updates")
    row = next((r for r in rows if r["id"] == update_id), None)
    if row is None or row["student_id"] not in actor.student_ids:
        raise HTTPException(404, "unknown update")
    if actor.user_id not in row.get("read_by", []):
        row.setdefault("read_by", []).append(actor.user_id)
        store.write_all("family_updates", [row if r["id"] == update_id else r for r in rows])
    return {"ok": True}
