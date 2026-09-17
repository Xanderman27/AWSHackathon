"""Why these learners belong in one group — explained by an agent, for the teacher only.

This one really is an agent, unlike the activity pipeline next door. The model is handed a
roster of pseudonymous learners and two tools, and it decides for itself whom to investigate
before it will explain anything:

    look_up_learner(ref)    one learner's full picture: every skill, band, trajectory
    submit_explanation(...) terminal; the only way to finish

`toolChoice` is "auto", so the calls are the model's choice and the loop runs until it submits
or hits the turn cap. That is the difference from the activity pipeline, where a single tool
call is forced purely to guarantee the shape of the JSON.

Privacy is the same as everywhere else: the model sees "Learner A", a band and a trajectory.
No name, no id, no photo, no goal link, no plan. The teacher sees real names because the
mapping back happens here, after the model has finished.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .config import settings

MAX_TURNS = 6

SYSTEM = (
    "You help a teacher understand why a suggested activity group holds together.\n\n"
    "You have a roster of learners referred to only as Learner A, Learner B and so on. Use "
    "look_up_learner to see any learner's full picture before you judge. Look up as many as "
    "you need, then call submit_explanation.\n\n"
    "Rules:\n"
    "- Write for the teacher, about learning, in two or three plain sentences.\n"
    "- Say what these learners have in common that makes the pairing useful, and be concrete "
    "about the evidence: bands, how much evidence there is, whether a trajectory is rising, "
    "flat or wobbling.\n"
    "- If the grouping looks weak, say so plainly. The teacher can move anyone.\n"
    "- Never mention a disability, a diagnosis, a plan, or a goal link. You have not been told "
    "any and must not guess.\n"
    "- Never rank learners against each other or call anyone behind, low or weak.\n"
    "- Refer to each learner by their exact tag, L1, L2 and so on, every time. Write "
    "'L1 and L2', never 'Learners L1 and L2' and never a bare letter.\n"
    "- Be brief. why_together is at most 35 words, as one plain sentence. Do not pack it "
    "with semicolons or dashes to fit more in; leave detail out instead. A teacher reads "
    "three of these at once.\n"
    "  Good: \"All three are practicing equivalent fractions with similar evidence, so one "
    "activity pitched at that level suits them.\"\n"
    "  Good: \"L1 and L2 are building foundations while L3 is a band ahead, so this pairing "
    "only works if L3 explains rather than races.\"\n"
    "- watch_for is at most 20 words."
)


class GroupExplanation(BaseModel):
    # Caps sized from what the model actually writes for a three-learner group, with headroom.
    # A constraint that rejects good output is not a safety feature, it is a bug that hides
    # behind a fallback.
    # The cap stays generous so a long answer is trimmed rather than failing validation and
    # dropping the whole thing to the canned fallback. Brevity is asked for in the prompt and
    # then guaranteed by _tighten below.
    why_together: str = Field(
        min_length=40, max_length=900,
        description="At most 35 words, one plain sentence: what these learners share and why "
                    "working together helps. Say plainly if the grouping is weak.")
    watch_for: str = Field(
        # Generous for the same reason as why_together: a wordy answer should be shortened,
        # never rejected. 300 was tight enough that a chatty run lost the whole explanation.
        min_length=15, max_length=600,
        description="At most 20 words: the single thing worth watching while this group works.")


def tighten(text: str, limit: int) -> str:
    """Keep whole sentences up to a limit.

    Asking for brevity mostly works; this makes it true. Cutting at a sentence boundary means
    a teacher never sees a clause that stops mid-thought, and trimming here rather than
    tightening the schema means an over-long answer is shortened instead of failing validation
    and falling back to the canned sentence.
    """
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    kept = ""
    for piece in re.split(r"(?<=[.!?])\s+", text):
        candidate = f"{kept} {piece}".strip()
        if kept and len(candidate) > limit:
            break
        kept = candidate
    # A first sentence longer than the limit still needs cutting, so check rather than
    # assume the loop produced something short enough.
    if kept and len(kept) <= limit:
        return kept
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:") + "\u2026"


def _tools() -> dict:
    return {
        "tools": [
            {"toolSpec": {
                "name": "look_up_learner",
                "description": "Everything known about one learner: every skill with evidence, "
                               "the band, how much evidence, and the trajectory over time.",
                "inputSchema": {"json": {
                    "type": "object",
                    "properties": {"ref": {"type": "string",
                                           "description": "A learner tag, e.g. 'L1'."}},
                    "required": ["ref"],
                }},
            }},
            {"toolSpec": {
                "name": "submit_explanation",
                "description": "Give the teacher the explanation. Call this once you have "
                               "looked up everyone you need.",
                "inputSchema": {"json": GroupExplanation.model_json_schema()},
            }},
        ],
        # The model decides. This is what makes it an agent rather than forced JSON.
        "toolChoice": {"auto": {}},
    }


def trend(history: list[float]) -> str:
    """A trajectory in words, because a list of numbers is not an observation.

    A single reversal matters here: a learner going 0.19, 0.38, 0.27, 0.35 is not simply
    "rising", and telling a teacher that would flatten the very thing worth noticing.
    """
    points = [float(h) for h in (history or [])]
    if len(points) < 2:
        return "only one check so far, so no direction yet"
    move = points[-1] - points[0]
    reversals = sum(1 for a, b, c in zip(points, points[1:], points[2:])
                    if (b - a) * (c - b) < 0)
    if abs(move) < 0.06:
        return "unsettled, ending where it started" if reversals else "flat across recent checks"
    direction = "rising" if move > 0 else "slipping"
    if reversals:
        return f"{direction} overall but up and down between checks"
    return f"{direction} steadily"


@dataclass
class Roster:
    """Pseudonymous learners, and the map back to real ids that never leaves this process."""

    by_ref: dict[str, dict] = field(default_factory=dict)
    ref_of: dict[str, str] = field(default_factory=dict)

    @classmethod
    def build(cls, member_ids: list[str], mastery: list[dict], skills: dict[str, dict]) -> "Roster":
        roster = cls()
        for index, student_id in enumerate(member_ids):
            # A tag that cannot collide with ordinary words the way a bare "A" can, so
            # putting the real names back afterwards is a plain token swap.
            ref = f"L{index + 1}"
            rows = [m for m in mastery if m["student_id"] == student_id]
            roster.by_ref[ref] = {
                "ref": ref,
                "skills": [{
                    "skill": skills.get(m["skill_id"], {}).get("name", m["skill_id"]),
                    "band": _band(m["estimate"]),
                    "evidence_count": m.get("evidence_count", 0),
                    "trajectory": trend(m.get("history", [])),
                } for m in rows],
            }
            roster.ref_of[student_id] = ref
        return roster


def _band(estimate: float) -> str:
    from ..mastery import bkt
    return {"building": "building foundations", "practicing": "practicing",
            "extension": "ready for extension"}[bkt.band(float(estimate))]


@dataclass
class AgentResult:
    explanation: GroupExplanation | None
    origin: str                                  # "bedrock" | "fallback"
    inspected: list[str] = field(default_factory=list)   # refs the model chose to look up
    turns: int = 0
    warning: str = ""


def _fallback(roster: Roster, skill_name: str) -> AgentResult:
    bands = {s["band"] for learner in roster.by_ref.values() for s in learner["skills"]
             if s["skill"] == skill_name}
    where = bands.pop() if len(bands) == 1 else "a similar place"
    return AgentResult(
        explanation=GroupExplanation(
            why_together=(f"These learners have recent evidence on {skill_name} and are in "
                          f"{where}, so one activity suits all of them."),
            watch_for="Whether one learner ends up doing the work while the others watch.",
        ),
        origin="fallback",
        warning="Bedrock was not available, so this is the standard explanation.",
    )


def explain(member_ids: list[str], skill_name: str, mastery: list[dict],
            skills: dict[str, dict]) -> AgentResult:
    roster = Roster.build(member_ids, mastery, skills)
    if settings().offline:
        return _fallback(roster, skill_name)

    import boto3
    current = settings()
    client = boto3.client("bedrock-runtime", region_name=current.region)

    opening = (
        f"A teacher has grouped these learners for an activity on {skill_name}.\n"
        f"Roster: {', '.join(roster.by_ref)}.\n"
        "Look up whoever you need, then submit your explanation."
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": [{"text": opening}]}]
    inspected: list[str] = []
    retried = False
    blocked = False

    try:
        for turn in range(1, MAX_TURNS + 1):
            request: dict[str, Any] = {
                "modelId": current.model_id,
                "system": [{"text": SYSTEM}],
                "messages": messages,
                "toolConfig": _tools(),
                "inferenceConfig": {"maxTokens": 900, "temperature": 0.2},
            }
            # Teacher-facing: comparison is allowed here, pejorative labels are not.
            if current.teacher_guardrail:
                request["guardrailConfig"] = current.teacher_guardrail
            response = client.converse(**request)

            message = response.get("output", {}).get("message", {})
            stop = response.get("stopReason")
            calls = [block["toolUse"] for block in message.get("content", []) if "toolUse" in block]

            if not calls:
                # Either the guardrail stepped in, or the model answered in prose instead of
                # calling a tool. Both are worth one nudge before giving up, and neither is a
                # turn limit, which is what this used to claim.
                if stop == "guardrail_intervened":
                    blocked = True
                if retried:
                    break
                retried = True
                messages.append({"role": "user", "content": [{"text":
                    "Call submit_explanation now, in neutral language about what the evidence "
                    "shows. Do not describe any learner as behind, weak or struggling."}]})
                continue

            submitted = next((c for c in calls if c["name"] == "submit_explanation"), None)
            if submitted:
                note = GroupExplanation.model_validate(submitted["input"])
                note = note.model_copy(update={
                    "why_together": tighten(note.why_together, 260),
                    "watch_for": tighten(note.watch_for, 150),
                })
                return AgentResult(note, "bedrock", inspected, turn)

            messages.append({"role": "assistant", "content": message["content"]})
            results = []
            for call in calls:
                ref = str(call.get("input", {}).get("ref", "")).strip().upper()
                learner = roster.by_ref.get(ref)
                if learner and ref not in inspected:
                    inspected.append(ref)
                results.append({"toolResult": {
                    "toolUseId": call["toolUseId"],
                    "content": [{"json": learner or {"error": f"No learner {ref} in this group."}}],
                }})
            messages.append({"role": "user", "content": results})

        result = _fallback(roster, skill_name)
        result.inspected = inspected
        result.warning = (
            "The guardrail stopped the explanation, so this is the standard one."
            if blocked else
            "The model did not settle on an explanation, so this is the standard one.")
        return result
    except ValidationError as problem:
        result = _fallback(roster, skill_name)
        result.inspected = inspected
        # Say which field was wrong. "Malformed" on its own is not something you can act on.
        fields = ", ".join(str(e["loc"][0]) for e in problem.errors()) or "unknown field"
        result.warning = f"The explanation came back malformed ({fields}), so this is the standard one."
        return result
    except Exception as problem:
        result = _fallback(roster, skill_name)
        result.inspected = inspected
        result.warning = f"Bedrock was unavailable ({type(problem).__name__}), so this is the standard explanation."
        return result
