"""Draft the periodic progress note for one goal — the thing IDEA actually asks for.

IDEA requires the IEP to state how progress toward annual goals is measured and when periodic
reports go to the family (34 CFR 300.320(a)(3)). In practice that is a checkbox on a quarterly
form. The whole product exists to make it evidence instead, and this is the piece that turns
the evidence into the sentence a teacher can send.

An agent, because writing it means going and looking: which of this learner's skills relate to
the goal, what each trajectory shows, what was tried at home and when. The model decides what
to inspect.

    skills_with_evidence()      what there is to look at, by name
    evidence_for_skill(name)    band, trajectory, how much evidence
    activities_tried()          approved home activities and when
    submit_progress_note(...)   terminal

What it is NOT given: the plan document. No eligibility category, no services, no present
levels, no accommodations, and not the goal's free-text `why` — a teacher wrote that and it
routinely contains the child's name and the word IEP. The model sees a goal title, skill
names, and numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from .config import settings
from .grouping import trend

MAX_TURNS = 8

SYSTEM = (
    "You draft one periodic progress note about a single learning goal, for a teacher to "
    "review before it reaches a family.\n\n"
    "Investigate before you write: look at the skills that relate to this goal, and at what "
    "has already been tried at home. Then call submit_progress_note.\n\n"
    "Rules:\n"
    "- Say only what the evidence supports. If it is thin, say so and mark it thin; do not "
    "round a trajectory up into a claim.\n"
    "- Lead with what the learner can already do, then what is next.\n"
    "- Plain language for a family. Two to four sentences. No percentages, no jargon, no "
    "mastery scores.\n"
    "- Never mention a disability, a diagnosis, a plan, an IEP, a 504, services, or another "
    "child. You have not been told any of those and must not guess.\n"
    "- Refer to the learner as 'your child'. You have not been told their name."
)


class ProgressNote(BaseModel):
    statement: str = Field(
        min_length=60, max_length=900,
        description="Two to four sentences for the family, under 600 characters: what the "
                    "learner can do now on this goal, and what comes next.")
    evidence_cited: list[str] = Field(
        min_length=1, max_length=8,
        description="The skills and activities you actually looked at and used.")
    sufficiency: Literal["enough", "thin"] = Field(
        description="'thin' when the evidence cannot yet support a progress claim. Saying so "
                    "is the correct answer, not a failure.")


def _tools() -> dict:
    return {
        "tools": [
            {"toolSpec": {"name": "skills_with_evidence",
                          "description": "Names of the skills this learner has any evidence on.",
                          "inputSchema": {"json": {"type": "object", "properties": {}}}}},
            {"toolSpec": {"name": "evidence_for_skill",
                          "description": "Band, trajectory and how much evidence, for one skill.",
                          "inputSchema": {"json": {
                              "type": "object",
                              "properties": {"skill": {"type": "string"}},
                              "required": ["skill"]}}}},
            {"toolSpec": {"name": "activities_tried",
                          "description": "Home activities a teacher approved for this learner, "
                                         "and when.",
                          "inputSchema": {"json": {"type": "object", "properties": {}}}}},
            {"toolSpec": {"name": "submit_progress_note",
                          "description": "Give the teacher the draft note.",
                          "inputSchema": {"json": ProgressNote.model_json_schema()}}},
        ],
        "toolChoice": {"auto": {}},
    }


@dataclass
class Evidence:
    """Everything the tools can answer from. Assembled here so the model reaches nothing else."""

    skills: dict[str, dict[str, Any]] = field(default_factory=dict)
    activities: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def build(cls, student_id: str, mastery: list[dict], skills: dict[str, dict],
              recommendations: list[dict]) -> "Evidence":
        from ..mastery import bkt
        bands = {"building": "building foundations", "practicing": "practicing",
                 "extension": "ready for extension"}
        found = {}
        for row in mastery:
            if row["student_id"] != student_id:
                continue
            name = skills.get(row["skill_id"], {}).get("name", row["skill_id"])
            found[name] = {
                "skill": name,
                "subject": skills.get(row["skill_id"], {}).get("subject", ""),
                "band": bands[bkt.band(float(row["estimate"]))],
                "evidence_count": row.get("evidence_count", 0),
                "trajectory": trend(row.get("history", [])),
            }
        tried = [
            {"activity": r["title"], "approved_on": (r.get("approved_on") or "")[:10]}
            for r in recommendations
            if r["student_id"] == student_id and r.get("status") == "approved"
        ]
        return cls(found, tried)

    def answer(self, name: str, payload: dict[str, Any]) -> Any:
        if name == "skills_with_evidence":
            return {"skills": sorted(self.skills)}
        if name == "evidence_for_skill":
            wanted = str(payload.get("skill", "")).strip()
            match = next((k for k in self.skills if k.lower() == wanted.lower()), None)
            return self.skills[match] if match else {
                "error": f"No evidence for {wanted!r}.", "available": sorted(self.skills)}
        if name == "activities_tried":
            return {"activities": self.activities}
        return {"error": f"Unknown tool {name}."}


@dataclass
class NoteResult:
    note: ProgressNote | None
    origin: str                                     # "bedrock" | "fallback"
    looked_at: list[str] = field(default_factory=list)
    turns: int = 0
    warning: str = ""


def _fallback(goal_title: str, evidence: Evidence) -> NoteResult:
    return NoteResult(
        note=ProgressNote(
            statement=(f"Your child has been practising towards “{goal_title}”. There is "
                       "some evidence from recent check-ins, and their teacher will add what "
                       "they have seen in class before this goes out."),
            evidence_cited=sorted(evidence.skills)[:3] or ["recent check-ins"],
            sufficiency="thin",
        ),
        origin="fallback",
        warning="Bedrock was not available, so this is a placeholder for the teacher to write over.",
    )


def draft(goal_title: str, student_id: str, mastery: list[dict], skills: dict[str, dict],
          recommendations: list[dict]) -> NoteResult:
    evidence = Evidence.build(student_id, mastery, skills, recommendations)
    if settings().offline:
        return _fallback(goal_title, evidence)

    import boto3
    current = settings()
    client = boto3.client("bedrock-runtime", region_name=current.region)

    messages: list[dict[str, Any]] = [{"role": "user", "content": [{"text":
        f"The goal is: “{goal_title}”.\n"
        "Find the evidence that bears on it, then submit the note."}]}]
    looked_at: list[str] = []
    retried = False
    blocked = False

    try:
        for turn in range(1, MAX_TURNS + 1):
            request: dict[str, Any] = {
                "modelId": current.model_id,
                "system": [{"text": SYSTEM}],
                "messages": messages,
                "toolConfig": _tools(),
                "inferenceConfig": {"maxTokens": 1100, "temperature": 0.2},
            }
            # Teacher-facing draft: it compares nothing, but it is written about a child, so
            # the stricter family policy is the right one.
            if current.guardrail:
                request["guardrailConfig"] = current.guardrail
            response = client.converse(**request)

            message = response.get("output", {}).get("message", {})
            calls = [b["toolUse"] for b in message.get("content", []) if "toolUse" in b]

            if not calls:
                if response.get("stopReason") == "guardrail_intervened":
                    blocked = True
                if retried:
                    break
                retried = True
                messages.append({"role": "user", "content": [{"text":
                    "Call submit_progress_note now, in plain language about what the evidence "
                    "shows. Mark it thin if that is what it is."}]})
                continue

            submitted = next((c for c in calls if c["name"] == "submit_progress_note"), None)
            if submitted:
                return NoteResult(ProgressNote.model_validate(submitted["input"]),
                                  "bedrock", looked_at, turn)

            messages.append({"role": "assistant", "content": message["content"]})
            results = []
            for call in calls:
                answer = evidence.answer(call["name"], call.get("input", {}))
                if call["name"] == "evidence_for_skill" and "skill" in answer:
                    looked_at.append(answer["skill"])
                elif call["name"] in ("skills_with_evidence", "activities_tried"):
                    looked_at.append(call["name"].replace("_", " "))
                results.append({"toolResult": {"toolUseId": call["toolUseId"],
                                               "content": [{"json": answer}]}})
            messages.append({"role": "user", "content": results})

        result = _fallback(goal_title, evidence)
        result.looked_at = looked_at
        result.warning = ("The guardrail stopped the draft, so this is a placeholder."
                          if blocked else
                          "The model did not settle on a note, so this is a placeholder.")
        return result
    except ValidationError as problem:
        result = _fallback(goal_title, evidence)
        result.looked_at = looked_at
        fields = ", ".join(str(e["loc"][0]) for e in problem.errors()) or "unknown field"
        result.warning = f"The note came back malformed ({fields}), so this is a placeholder."
        return result
    except Exception as problem:
        result = _fallback(goal_title, evidence)
        result.looked_at = looked_at
        result.warning = (f"Bedrock was unavailable ({type(problem).__name__}), so this is a "
                          "placeholder for the teacher to write over.")
        return result
