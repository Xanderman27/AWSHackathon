"""Student quiz flow: start an attempt, get the next item, answer, finish."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..auth import Actor, get_actor, require_student_access
from ..mastery import bkt
from ..mastery.select import next_item, should_route_to_prerequisite
from ..models import AnswerIn, AnswerOut, Attempt, Item, ItemResponse, MasteryState, NextItem, Skill, now
from ..storage import store

router = APIRouter(prefix="/attempts", tags=["attempts"])

ENCOURAGE_CORRECT = [
    "Nice work. You looked carefully.",
    "That's it. You kept going.",
    "Great thinking.",
]
ENCOURAGE_TRY = [
    "Good try. Let's look at another one.",
    "That one was tricky. Keep going.",
    "Thanks for trying. Here's the next one.",
]


def _items() -> dict[str, Item]:
    return {i["id"]: Item(**i) for i in store.read("items")}


def _skills() -> dict[str, Skill]:
    return {s["id"]: Skill(**s) for s in store.read("skills")}


def _mastery(student_id: str, skill_id: str) -> MasteryState:
    for m in store.read("mastery"):
        if m["student_id"] == student_id and m["skill_id"] == skill_id:
            return MasteryState(**m)
    return MasteryState(student_id=student_id, skill_id=skill_id, estimate=bkt.SkillParams().p_init)


def _save_attempt(a: Attempt) -> None:
    store.upsert("attempts", a.model_dump())


def _fresh_exclusions(a: Attempt, items: dict[str, Item], seen_now: set[str]) -> set[str]:
    """Items to avoid because the learner met them in recent quizzes.

    The most recently seen items are excluded first, but never so many that the bank runs
    dry - with a small bank this rotates the questions instead of repeating them, and with a
    big bank every quiz feels new. Deterministic, because the answer endpoint re-derives the
    served item and must land on the same one.
    """
    bank_size = sum(
        1 for i in items.values() if i.skill_id == a.current_skill_id and i.approved
    )
    room = bank_size - len(seen_now) - 1  # always leave at least one candidate
    if room <= 0:
        return set()
    rows = [r for r in store.read("attempts")
            if r["student_id"] == a.student_id and r["id"] != a.id and r["responses"]]
    rows.sort(key=lambda r: r["started_at"], reverse=True)
    avoid: set[str] = set()
    for row in rows:
        for resp in reversed(row["responses"]):
            item_id = resp["item_id"]
            if item_id in seen_now or item_id in avoid:
                continue
            avoid.add(item_id)
            if len(avoid) >= room:
                return avoid
    return avoid


def _pick(a: Attempt, items: dict[str, Item], estimate: float) -> Item | None:
    seen = {r.item_id for r in a.responses}
    exclude = seen | _fresh_exclusions(a, items, seen)
    return next_item(estimate, a.current_skill_id, list(items.values()), exclude,
                     variety_key=f"{a.id}:{len(a.responses)}")


def _next(a: Attempt) -> NextItem:
    items = _items()
    skills = _skills()
    position = len(a.responses) + 1
    if a.completed or len(a.responses) >= a.max_items:
        a.completed = True
        _save_attempt(a)
        skill = skills[a.skill_id]
        return NextItem(
            attempt_id=a.id,
            position=a.max_items,
            total=a.max_items,
            item=None,
            completed=True,
            summary=f"You practiced {skill.child_name}.",
        )
    est = _mastery(a.student_id, a.current_skill_id).estimate
    item = _pick(a, items, est)
    if item is None:
        a.completed = True
        _save_attempt(a)
        return NextItem(attempt_id=a.id, position=position, total=a.max_items, item=None, completed=True,
                        summary=f"You practiced {skills[a.skill_id].child_name}.")
    # Strip the answer before it reaches the student screen.
    safe = item.model_copy(update={"answer": "", "explanation": ""})
    return NextItem(attempt_id=a.id, position=position, total=a.max_items, item=safe, completed=False)


@router.post("/start", response_model=NextItem)
def start(skill_id: str, actor: Actor = Depends(get_actor)) -> NextItem:
    if actor.role != "student":
        raise HTTPException(403, "not permitted")
    if skill_id not in _skills():
        raise HTTPException(404, "unknown skill")
    # Resume an open attempt on the same objective if one exists (PRD FR-03).
    for row in store.read("attempts"):
        if row["student_id"] == actor.user_id and row["skill_id"] == skill_id and not row["completed"]:
            return _next(Attempt(**row))
    a = Attempt(id=f"att-{uuid.uuid4().hex[:8]}", student_id=actor.user_id, skill_id=skill_id,
                current_skill_id=skill_id)
    _save_attempt(a)
    store.append("audit", {"actor": actor.user_id, "action": "attempt.start", "object_id": a.id, "at": a.started_at})
    return _next(a)


@router.get("/{attempt_id}/next", response_model=NextItem)
def get_next(attempt_id: str, actor: Actor = Depends(get_actor)) -> NextItem:
    a = _load(attempt_id, actor)
    return _next(a)


@router.post("/{attempt_id}/answer", response_model=AnswerOut)
def answer(attempt_id: str, body: AnswerIn, actor: Actor = Depends(get_actor)) -> AnswerOut:
    a = _load(attempt_id, actor)
    if a.completed:
        raise HTTPException(409, "attempt is complete")
    items = _items()
    est_state = _mastery(a.student_id, a.current_skill_id)
    item = _pick(a, items, est_state.estimate)
    if item is None:
        raise HTTPException(409, "no item pending")
    correct = body.choice_id == item.answer
    new_est = bkt.update(est_state.estimate, correct, bkt.SkillParams(), item.irt_a, item.irt_b, body.hint_used)
    est_state.estimate = new_est
    est_state.evidence_count += 1
    est_state.history.append(round(new_est, 3))
    est_state.updated_at = now()
    store.upsert_mastery(est_state.model_dump())

    resp = ItemResponse(item_id=item.id, choice_id=body.choice_id, correct=correct, hint_used=body.hint_used)
    a.responses.append(resp)

    # Explicit routing rule: two misses in the easy band -> prerequisite.
    skills = _skills()
    prereq = skills[a.current_skill_id].prerequisites
    if prereq and a.current_skill_id == a.skill_id and should_route_to_prerequisite(a.responses, items):
        a.current_skill_id = prereq[0]
        resp.route_reason = f"Two misses on easy items; routed to {skills[prereq[0]].name}."
    _save_attempt(a)

    n = len(a.responses)
    feedback = (ENCOURAGE_CORRECT if correct else ENCOURAGE_TRY)[n % 3]
    return AnswerOut(correct=correct, feedback=feedback, next=_next(a))


def _load(attempt_id: str, actor: Actor) -> Attempt:
    for row in store.read("attempts"):
        if row["id"] == attempt_id:
            a = Attempt(**row)
            require_student_access(actor, a.student_id)
            return a
    raise HTTPException(404, "unknown attempt")
