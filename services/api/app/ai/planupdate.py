"""AI-drafted updates to a learner's support plan (IEP or 504).

Same discipline as the activity pipeline: retrieve from the approved corpus (standards,
district policy, teacher guidance, accessibility research), send a PSEUDONYMOUS package -
the plan's current supports and the evidence bands, never a name, id, grade or eligibility
label - force a typed tool call, verify every citation, and hand the draft to the teacher.
The draft is a proposal for the team; nothing changes in the plan until the teacher adopts
it, and the UI says who drafted it.

Offline (`DEMO_OFFLINE=1`) the same signals drive a deterministic rule-based draft, so the
demo works with no AWS and the teacher screen never breaks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from . import retrieval
from .config import settings

TOOL_NAME = "suggest_plan_update"

SYSTEM = (
    "You help a special-education team tune one child's support plan using fresh practice "
    "evidence. You see the plan's current supports and pseudonymous evidence bands only.\n\n"
    "Rules:\n"
    "- Propose exactly ONE small, concrete change: an accommodation to add or adjust, or a "
    "goal criterion to tune.\n"
    "- Ground it only in the provided sources and evidence; cite the source ids you used.\n"
    "- Name when the support applies and which evidence motivated it.\n"
    "- Never diagnose, never mention a disability or eligibility, never rank the learner.\n"
    "- The team decides; write the change as a proposal, not an instruction.\n"
    "- Answer only by calling the suggest_plan_update tool."
)


class PlanUpdateDraft(BaseModel):
    section: str = Field(pattern="^(accommodations|goals|services)$",
                         description="Which part of the plan the change belongs to.")
    change: str = Field(min_length=12, max_length=300,
                        description="The proposed change, one or two sentences, concrete "
                                    "enough to paste into the plan.")
    rationale: str = Field(min_length=20, max_length=500,
                           description="Why now: the evidence pattern and the guidance that "
                                       "supports it, in plain language for the team.")
    citations: list[str] = Field(min_length=1,
                                 description="Source ids used. Only ids that were provided.")


def _tool_config() -> dict:
    schema = PlanUpdateDraft.model_json_schema()
    schema.pop("title", None)
    return {"tools": [{"toolSpec": {"name": TOOL_NAME,
                                    "description": "Return one proposed plan update for the team.",
                                    "inputSchema": {"json": schema}}}],
            "toolChoice": {"tool": {"name": TOOL_NAME}}}


@dataclass
class PlanUpdateResult:
    draft: PlanUpdateDraft | None
    citations: list[dict]
    origin: str                      # "bedrock" | "rules" | "none"
    path: list[str] = field(default_factory=list)
    warning: str = ""


def summarise(plan: dict, mastery_rows: list[dict], skills: dict[str, dict]) -> str:
    """Everything the model may know. Supports and evidence bands - no identity of any kind."""
    supports = "; ".join(plan.get("accommodations", [])[:8]) or "none on file"
    goals = " | ".join(plan.get("plan_goals", [])[:3]) or "none on file"
    lines = []
    for m in mastery_rows[:8]:
        skill = skills.get(m["skill_id"], {})
        band = "building" if m["estimate"] < 0.40 else "practicing" if m["estimate"] <= 0.80 else "extension"
        trend = ""
        history = m.get("history") or []
        if len(history) >= 3:
            trend = ", rising" if history[-1] > history[0] + 0.05 else \
                    ", falling" if history[-1] < history[0] - 0.05 else ", steady"
        lines.append(f"- {skill.get('name', m['skill_id'])}: {band}{trend}, "
                     f"{m.get('evidence_count', 0)} answers")
    return (f"Plan type: {plan.get('type', 'IEP')}.\n"
            f"Current accommodations: {supports}.\n"
            f"Current plan goals: {goals}.\n"
            f"Fresh practice evidence:\n" + "\n".join(lines))


def _rules_draft(plan: dict, mastery_rows: list[dict], skills: dict[str, dict]) -> PlanUpdateDraft:
    """The offline path: the same signals, decided by rules instead of a model."""
    weakest = min(mastery_rows, key=lambda m: m["estimate"], default=None) if mastery_rows else None
    skill_name = skills.get(weakest["skill_id"], {}).get("name", "the current focus skill") if weakest else "the current focus skill"
    if plan.get("type") == "504":
        change = (f"Add a posted visual checklist for multi-step tasks during {skill_name} "
                  f"practice, reviewed at the next term check.")
        cites = ["district-accommodation-menu", "udl-reduce-load"]
    else:
        change = (f"Extend read-aloud with word highlighting to independent practice on "
                  f"{skill_name}, and note it in the accommodations list.")
        cites = ["teacher-readaloud-evidence", "district-accommodation-menu"]
    return PlanUpdateDraft(
        section="accommodations",
        change=change,
        rationale=(f"Recent practice shows {skill_name} is the least settled skill, and the "
                   "district guidance prefers the least intrusive support that removes the "
                   "barrier the evidence shows. Proposed for the team to consider - adopted "
                   "only if you agree."),
        citations=cites,
    )


def propose(plan: dict, mastery_rows: list[dict], skills: dict[str, dict]) -> PlanUpdateResult:
    path = ["summarise", "retrieve"]
    weakest = min(mastery_rows, key=lambda m: m["estimate"], default=None) if mastery_rows else None
    skill_name = skills.get(weakest["skill_id"], {}).get("name", "") if weakest else ""
    sources = retrieval.retrieve(
        f"accommodation supports plan goal {plan.get('type', '')} {skill_name} evidence",
        doc_types=("district-policy", "teacher-guidance", "accessibility", "standard"),
        limit=5,
    )
    current = settings()
    if current.offline:
        path.append("rules_fallback")
        draft = _rules_draft(plan, mastery_rows, skills)
        return PlanUpdateResult(draft=draft, citations=_cite(draft, sources), origin="rules", path=path)

    summary = summarise(plan, mastery_rows, skills)
    try:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=current.region)
        blocks = "\n\n".join(f"[{s.id}] ({s.doc_type}, {s.source_org})\n{s.text}" for s in sources)
        request: dict[str, Any] = {
            "modelId": current.model_id,
            "system": [{"text": SYSTEM}],
            "messages": [{"role": "user", "content": [{"text": f"{summary}\n\nApproved sources:\n{blocks}\n\nPropose one plan update."}]}],
            "toolConfig": _tool_config(),
            "inferenceConfig": {"maxTokens": 1400, "temperature": 0.2},
        }
        # This surface gets its own guardrail (dori-guardrail-plan): diagnosis and
        # medication stay denied, but proposing a support for the team is allowed -
        # the family/teacher guardrails deny that very topic and would block every
        # draft. Provisioned by scripts/provision_guardrail.py's plan variant and
        # read from Parameter Store like the others.
        if current.plan_guardrail:
            request["guardrailConfig"] = current.plan_guardrail
        path.append("bedrock")
        response = client.converse(**request)
        stop_reason = response.get("stopReason", "?")
        path.append(f"stop:{stop_reason}")
        payload = None
        for block in response.get("output", {}).get("message", {}).get("content", []):
            use = block.get("toolUse")
            if use and use.get("name") == TOOL_NAME:
                payload = use.get("input")
        # Coerce before validating: models capitalise section names and run long, and neither
        # is a reason to throw away an otherwise grounded draft.
        payload = dict(payload or {})
        payload["section"] = str(payload.get("section", "accommodations")).strip().lower()
        if payload["section"] not in ("accommodations", "goals", "services"):
            payload["section"] = "accommodations"
        payload["change"] = str(payload.get("change", ""))[:300]
        payload["rationale"] = str(payload.get("rationale", ""))[:500]
        cites = payload.get("citations")
        payload["citations"] = [str(c) for c in cites] if isinstance(cites, list) else []
        if not payload["citations"]:
            payload["citations"] = [s.id for s in sources[:2]] or ["unverified"]
        draft = PlanUpdateDraft(**payload)
    except (ValidationError, Exception) as problem:  # noqa: BLE001 - demo must not 500
        path.append("rules_fallback")
        draft = _rules_draft(plan, mastery_rows, skills)
        detail = str(problem).replace("\n", " ")[:180]
        return PlanUpdateResult(draft=draft, citations=_cite(draft, sources), origin="rules",
                                path=path,
                                warning=f"live draft unavailable ({type(problem).__name__}: {detail})")

    # Grounding check: invented citations are dropped; a draft left with none is flagged.
    allowed = {s.id for s in sources}
    real = [c for c in draft.citations if c in allowed]
    warning = ""
    if not real:
        warning = "The draft cited nothing we supplied; treat it as unverified."
        real = draft.citations
    draft = draft.model_copy(update={"citations": real})
    path.append("verify")
    return PlanUpdateResult(draft=draft, citations=_cite(draft, sources), origin="bedrock",
                            path=path, warning=warning)


def _cite(draft: PlanUpdateDraft, sources: list) -> list[dict]:
    by_id = {s.id: s for s in sources}
    out = []
    for cid in draft.citations:
        s = by_id.get(cid)
        out.append({"id": cid, "title": s.title if s else cid,
                    "source_org": s.source_org if s else "", "doc_type": s.doc_type if s else ""})
    return out
