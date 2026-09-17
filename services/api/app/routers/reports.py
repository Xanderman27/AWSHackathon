"""A summary a family can hand to their child's doctor.

Families are routinely asked to bring "something from school" to a paediatric or
developmental appointment, and what they can usually produce is a report card, which says
what a child scored and nothing about how they got there. This endpoint assembles what the
product actually knows — which skills a child has practised, over what period, how much
evidence sits behind each one, and which next steps the teacher approved — in plain language,
for the family to share or not share as they choose.

Boundaries, and they are the important part of this file:

- **This is not a clinical document and says so on its face.** The product does not diagnose,
  determine eligibility, or recommend services (docs/GUIDELINES.md §1.5), and a summary that
  travels to a doctor is exactly where that line is most likely to blur. Every payload
  carries the disclaimer; the front end is not trusted to add it.
- **One child, and only a linked one.** The parent's own link table decides, never a path
  parameter (§8).
- **Nothing about anybody else.** No classmates, no class averages, no rank, no percentile.
  A comparison is not this family's data to share.
- **No teacher-only fields.** Goal-link markers, cohort rationales and teacher notes stay
  behind; PRD §6 keeps those on the teacher's side of the wall.
- **The family holds the export.** The server hands back JSON, the browser turns it into a
  file the family can print or attach. Nothing is emailed, uploaded, or sent anywhere by us:
  the moment a product mails a child's learning record to a clinic on a family's behalf is
  the moment it needs a consent flow it does not have.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import Actor, require_role, require_student_access
from ..mastery import bkt
from ..models import now
from ..storage import store

router = APIRouter(prefix="/parent", tags=["parent"])

# Plain language, aimed at roughly a grade 6-8 reading level (§8). A clinician can read
# anything; the family reading it over their shoulder is who this wording is for.
BAND_SENTENCE = {
    "building": "is building the first steps of this",
    "practicing": "is practising this at grade level",
    "extension": "is ready to stretch further with this",
}
CONFIDENCE_SENTENCE = {
    "low": "Not enough practice yet to say much",
    "medium": "Some practice behind this",
    "high": "A steady amount of practice behind this",
}

DISCLAIMER = (
    "This summary comes from a classroom practice app. It is not a medical or diagnostic "
    "document, it is not an assessment, and it does not say anything about a diagnosis, "
    "eligibility for services, or placement. It describes what this child practised in "
    "class and how much practice sits behind each skill. Please read it alongside what the "
    "school and the family can tell you, not instead of it."
)


def _dates(attempts: list[dict]) -> tuple[str | None, str | None]:
    stamps = sorted(r["at"] for a in attempts for r in a["responses"] if r.get("at"))
    return (stamps[0][:10], stamps[-1][:10]) if stamps else (None, None)


@router.get("/children/{student_id}/report")
def report(student_id: str, actor: Actor = Depends(require_role("parent"))):
    """Everything the export contains. Assembled server-side so the boundaries travel with it."""
    require_student_access(actor, student_id)

    student = next(s for s in store.read("students") if s["id"] == student_id)
    skills = {s["id"]: s for s in store.read("skills")}
    items = {i["id"]: i for i in store.read("items")}
    attempts = [a for a in store.read("attempts") if a["student_id"] == student_id]

    first_seen, last_seen = _dates(attempts)
    answered = sum(len(a["responses"]) for a in attempts)
    correct = sum(1 for a in attempts for r in a["responses"] if r.get("correct"))
    hinted = sum(1 for a in attempts for r in a["responses"] if r.get("hint_used"))
    days = len({r["at"][:10] for a in attempts for r in a["responses"] if r.get("at")})

    rows = []
    for m in store.read("mastery"):
        if m["student_id"] != student_id:
            continue
        skill = skills.get(m["skill_id"], {})
        flags = [r["correct"] for a in attempts for r in a["responses"]
                 if items.get(r["item_id"], {}).get("skill_id") == m["skill_id"]]
        if len(flags) < m.get("evidence_count", 0):
            flags = [True] * m["evidence_count"]
        band = bkt.band(m["estimate"])
        history = m.get("history", [])
        # Direction of travel over the recorded history, in words rather than a number: a
        # slope is the kind of thing that gets over-read once it reaches a clinic.
        trend = "not enough history yet"
        if len(history) >= 3:
            change = history[-1] - history[0]
            trend = ("moving up" if change > 0.08 else
                     "moving down" if change < -0.08 else "holding steady")
        rows.append({
            "subject": skill.get("subject", ""),
            "skill": skill.get("name", m["skill_id"]),
            "in_plain_words": skill.get("child_name", ""),
            "standard": skill.get("standard_id", ""),
            "where_they_are": f"{student['display_name']} {BAND_SENTENCE[band]}.",
            "practice_behind_it": CONFIDENCE_SENTENCE[bkt.confidence(history, flags)],
            "questions_answered": m.get("evidence_count", 0),
            "direction": trend,
        })
    rows.sort(key=lambda r: (r["subject"], r["skill"]))

    next_steps = [{
        "title": r.get("title", ""),
        "why": r.get("why", ""),
        "minutes": r.get("minutes"),
        "approved_by": r.get("approved_by", ""),
        "approved_on": r.get("approved_on", ""),
    } for r in store.read("recommendations")
        if r["student_id"] == student_id and r["status"] == "approved" and r["audience"] == "family"]

    # Supports the child uses in the app. Stated as settings, never as findings: an
    # accessibility preference is available to every learner and is not evidence of anything
    # (§1.5, rule 5). It is here because a family may want to mention it, and it is theirs.
    supports = student.get("supports") or []

    return {
        "child": {"name": student["display_name"], "grade": student.get("grade")},
        "generated_on": now()[:10],
        "covers": {"first_activity": first_seen, "last_activity": last_seen, "days_active": days},
        "practice": {
            "questions_answered": answered,
            "answered_correctly": correct,
            "hints_opened": hinted,
            "quests_finished": sum(1 for a in attempts if a.get("completed")),
        },
        "skills": rows,
        "teacher_approved_next_steps": next_steps,
        "supports_used_in_the_app": supports,
        "what_this_is_not": DISCLAIMER,
        "prepared_by": "Dori, a classroom practice app",
    }
