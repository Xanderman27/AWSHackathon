"""Classroom photos a teacher shares with the families in their class.

The teacher uploads; every family in that class sees them on the parent dashboard. That
audience is a deliberate product decision (see docs/PRIVACY_POSTURE.md): a photo of one
child is visible to the other families in the class, which in a real district needs photo
consent on file per child.

What the code does enforce:

- Only a teacher may upload, and only to their own class.
- A parent may only read photos for a class one of their linked children is actually in.
- The image bytes are served through an authorised route, not a public static folder, so a
  leaked filename is not a leaked photo. Production swaps this for short-lived presigned S3
  URLs (TECH_STACK "Delivery and config"); the authorisation check stays the same.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from ..auth import Actor, get_actor, require_role
from ..models import now
from ..storage import store

router = APIRouter(tags=["class photos"])

# Formats a phone camera actually produces, and a cap that keeps the demo snappy.
ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/heic": ".heic"}
MAX_BYTES = 8 * 1024 * 1024
CAPTION_MAX = 600
TITLE_MAX = 80


def _visible(row: dict, fields: tuple[str, ...]) -> dict:
    return {key: row.get(key) for key in fields}


PHOTO_FIELDS = ("id", "class_id", "title", "caption", "taken_on", "uploaded_at", "uploaded_by_name")


def _parent_class_ids(actor: Actor) -> set[str]:
    """Classes this parent may see, derived from their linked children — never from input."""
    return {
        student["class_id"]
        for student in store.read("students")
        if student["id"] in actor.student_ids
    }


def _readable_class_ids(actor: Actor) -> set[str]:
    if actor.role == "teacher":
        return set(actor.class_ids)
    if actor.role == "parent":
        return _parent_class_ids(actor)
    return set()


@router.post("/teacher/class-photos", status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    caption: str = Form(default=""),
    taken_on: str = Form(default=""),
    actor: Actor = Depends(require_role("teacher")),
):
    if file.content_type not in ALLOWED:
        raise HTTPException(400, "Please choose a JPEG, PNG, WebP, or HEIC image.")
    payload = await file.read()
    if not payload:
        raise HTTPException(400, "That file was empty.")
    if len(payload) > MAX_BYTES:
        raise HTTPException(413, "That photo is larger than 8 MB. Please choose a smaller one.")

    # The stored name is ours, never the client's: an uploaded filename is untrusted input.
    stored = f"{uuid4().hex}{ALLOWED[file.content_type]}"
    store.blobs.put(stored, payload, file.content_type)

    teacher = next((t for t in store.read("teachers") if t["id"] == actor.user_id), {})
    row = {
        "id": f"photo-{uuid4().hex[:10]}",
        "class_id": sorted(actor.class_ids)[0],
        "filename": stored,
        "content_type": file.content_type,
        "title": title.strip()[:TITLE_MAX],
        "caption": caption.strip()[:CAPTION_MAX],
        "taken_on": taken_on.strip()[:10],
        "uploaded_by": actor.user_id,
        "uploaded_by_name": teacher.get("display_name", "Your teacher"),
        "uploaded_at": now(),
    }
    store.append("class_photos", row)
    store.append("audit", {"actor": actor.user_id, "action": "class_photo.upload",
                           "object_id": row["id"], "at": row["uploaded_at"]})
    return _visible(row, PHOTO_FIELDS)


def _for_class(class_ids: set[str]) -> list[dict]:
    rows = [row for row in store.read("class_photos") if row["class_id"] in class_ids]
    rows.sort(key=lambda row: (row.get("taken_on") or "", row["uploaded_at"]), reverse=True)
    return [_visible(row, PHOTO_FIELDS) for row in rows]


@router.get("/teacher/class-photos")
def teacher_photos(actor: Actor = Depends(require_role("teacher"))):
    return _for_class(set(actor.class_ids))


@router.get("/parent/class-photos")
def parent_photos(actor: Actor = Depends(require_role("parent"))):
    """Photos from the classes this parent's children are in. Nothing else reaches them."""
    return _for_class(_parent_class_ids(actor))


@router.get("/class-photos/{photo_id}/file")
def photo_file(photo_id: str, actor: Actor = Depends(get_actor)):
    """The image bytes, gated by the same rule as the listing. Students never get here."""
    allowed = _readable_class_ids(actor)
    row = next((r for r in store.read("class_photos") if r["id"] == photo_id), None)
    # Same answer whether the photo does not exist or is not this caller's to see.
    if row is None or row["class_id"] not in allowed:
        raise HTTPException(404, "unknown photo")
    data = store.blobs.get(row["filename"])
    if data is None:
        raise HTTPException(404, "unknown photo")
    # Private either way: these bytes only leave here for a caller the check above allowed.
    return Response(content=data, media_type=row["content_type"],
                    headers={"Cache-Control": "private, max-age=300"})


@router.delete("/teacher/class-photos/{photo_id}")
def delete_photo(photo_id: str, actor: Actor = Depends(require_role("teacher"))):
    rows = store.read("class_photos")
    row = next((r for r in rows if r["id"] == photo_id), None)
    if row is None or row["class_id"] not in actor.class_ids:
        raise HTTPException(404, "unknown photo")
    store.write_all("class_photos", [r for r in rows if r["id"] != photo_id])
    store.blobs.delete(row["filename"])
    store.append("audit", {"actor": actor.user_id, "action": "class_photo.delete",
                           "object_id": photo_id, "at": now()})
    return {"ok": True}
