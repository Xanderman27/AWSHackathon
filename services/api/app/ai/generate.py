"""The recommendation pipeline: retrieve, fill, verify.

The graph the tech stack describes, written as plain functions so the edges are readable:

    summarise -> retrieve -> fill_template -> validate -(fails once)-> fill_template
                                           -> verify_grounding -> present
                                           -(no sources)-> no_source_fallback
                                           -(offline)-> cached_draft

What reaches Bedrock is deliberately thin: a pseudonymous mastery summary, the retrieved
chunks, and the template. No name, no grade, no class, no goal link, no photo, no disability
anything — there is nothing of the kind in the context to leak (PRD §10, "Generation input").
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from . import retrieval
from .config import settings
from .schema import TOOL_NAME, ActivityDraft, tool_config

SYSTEM = (
    "You write one short at-home learning activity for the family of an elementary school "
    "learner. A teacher reviews everything you write before any family sees it.\n\n"
    "Rules:\n"
    "- Use only the sources provided. If the sources do not support a claim, leave it out.\n"
    "- Cite the ids of every source you used.\n"
    "- Write for an adult at home with ten minutes and no printer. Everyday materials only.\n"
    "- Describe what the learner can already do before what comes next.\n"
    "- Never mention a disability, a diagnosis, a plan, a grade level, or other children.\n"
    "- Never diagnose, assess, or predict. You are proposing one activity, nothing more.\n"
    "- Answer only by calling the submit_activity tool."
)

BAND_WORDS = {
    "building": "is early in this skill and needs the idea made concrete",
    "practicing": "has the idea and needs more practice to make it reliable",
    "extension": "is secure on this skill and is ready to stretch",
}


@dataclass
class PipelineResult:
    draft: ActivityDraft | None
    citations: list[dict]
    origin: str                      # "bedrock" | "cached" | "none"
    path: list[str] = field(default_factory=list)   # the edges taken, for the audit record
    warning: str = ""


def summarise(band: str, evidence_count: int, hint_rate: float, skill_name: str) -> str:
    """The only thing about the learner that reaches the model. No identity of any kind."""
    hints = "often asks for a hint" if hint_rate >= 0.34 else "rarely asks for a hint"
    return (
        f"A learner working on {skill_name}. Evidence so far: {evidence_count} answers. "
        f"The learner {BAND_WORDS.get(band, 'is practicing this skill')}, and {hints}."
    )


# What kind of activity suits a learner at each point, and which accessibility note matters
# most there. A learner who needs the idea made concrete wants something to hold; one who
# already has it wants to meet the idea somewhere unfamiliar.
BAND_QUERIES = {
    "building": ("hands on physical model built from everyday materials",
                 "multiple representation something to hold and say out loud"),
    "practicing": ("find the idea in daily life and talk about it",
                   "low working memory load one instruction per step"),
    "extension": ("stretch the idea somewhere new and unfamiliar",
                  "low working memory load one instruction per step"),
}


def gather(skill_id: str, skill_name: str, band: str = "practicing") -> list[retrieval.Source]:
    """Standard, misconceptions, a template that suits this band, an accessible way in, and
    the family tone rule. The band changes which template is retrieved, which is what makes
    this retrieval rather than a fixed prompt with the skill pasted in."""
    template_query, access_query = BAND_QUERIES.get(band, BAND_QUERIES["practicing"])
    picks: dict[str, retrieval.Source] = {}
    for query, doc_types, limit in (
        (skill_name, ("standard",), 1),
        (skill_name, ("misconception",), 2),
        (f"{template_query} {skill_name}", ("activity-template",), 2),
        (access_query, ("accessibility",), 1),
        ("writing for families plain language", ("family-guidance",), 1),
    ):
        for source in retrieval.retrieve(query, skill_id=skill_id, doc_types=doc_types, limit=limit):
            picks.setdefault(source.id, source)
    return list(picks.values())


def _prompt(summary: str, sources: list[retrieval.Source]) -> str:
    blocks = "\n\n".join(
        f"[{s.id}] ({s.doc_type}, {s.source_org})\n{s.text}" for s in sources
    )
    return (
        f"Learner summary:\n{summary}\n\n"
        f"Approved sources:\n{blocks}\n\n"
        "Write one activity. Cite the source ids you used."
    )


def _call_bedrock(summary: str, sources: list[retrieval.Source]) -> dict[str, Any]:
    import boto3  # imported here so the app runs on a machine with no AWS at all

    current = settings()
    client = boto3.client("bedrock-runtime", region_name=current.region)
    request: dict[str, Any] = {
        "modelId": current.model_id,
        "system": [{"text": SYSTEM}],
        "messages": [{"role": "user", "content": [{"text": _prompt(summary, sources)}]}],
        "toolConfig": tool_config(),
        "inferenceConfig": {"maxTokens": current.max_tokens, "temperature": current.temperature},
    }
    if current.guardrail:
        request["guardrailConfig"] = current.guardrail
    return client.converse(**request)


def _tool_input(response: dict[str, Any]) -> dict[str, Any] | None:
    for block in response.get("output", {}).get("message", {}).get("content", []):
        use = block.get("toolUse")
        if use and use.get("name") == TOOL_NAME:
            return use.get("input")
    return None


def _verify_grounding(draft: ActivityDraft, sources: list[retrieval.Source]) -> tuple[ActivityDraft, str]:
    """Citations must name sources we actually supplied. Invented ids are dropped, and a draft
    left with none is handed to the teacher flagged rather than quietly presented as grounded."""
    allowed = {s.id for s in sources}
    kept = [c for c in draft.citations if c in allowed]
    if kept == draft.citations:
        return draft, ""
    if not kept:
        return draft.model_copy(update={"citations": []}), (
            "The draft cited no approved source. Treat every claim in it as unverified."
        )
    return draft.model_copy(update={"citations": kept}), (
        "Some citations did not match an approved source and were removed."
    )


def _cached(skill_id: str, band: str) -> ActivityDraft | None:
    from .cached import CACHED_DRAFTS
    return CACHED_DRAFTS.get((skill_id, band)) or CACHED_DRAFTS.get((skill_id, "practicing"))


def propose(skill_id: str, skill_name: str, band: str, evidence_count: int,
            hint_rate: float = 0.0) -> PipelineResult:
    path: list[str] = ["summarise"]
    summary = summarise(band, evidence_count, hint_rate, skill_name)

    sources = gather(skill_id, skill_name, band)
    path.append("retrieve")
    # General guidance on tone and accessibility can shape a draft but cannot be the whole
    # grounding for one. Without a source that actually covers this skill there is nothing to
    # be grounded in, so we ask for a source rather than assert something (PRD §10, FR-19).
    if not any(skill_id in source.skill_ids for source in sources):
        return PipelineResult(None, [s.as_citation() for s in sources], "none",
                              path + ["no_source_fallback"],
                              "No approved source covers this skill yet, so nothing was drafted.")

    citations = [s.as_citation() for s in sources]

    if settings().offline:
        path.append("cached_draft")
        draft = _cached(skill_id, band)
        if draft is None:
            return PipelineResult(None, citations, "none", path,
                                  "No cached draft for this skill. Connect Bedrock to generate one.")
        draft, warning = _verify_grounding(draft, sources)
        return PipelineResult(draft, citations, "cached", path + ["verify_grounding"], warning)

    last_error = ""
    for attempt in range(2):  # one retry, then give up rather than loop on a bad response
        path.append("fill_template" if attempt == 0 else "fill_template_retry")
        try:
            payload = _tool_input(_call_bedrock(summary, sources))
            if payload is None:
                last_error = "The model did not call the tool."
                continue
            draft = ActivityDraft.model_validate(payload)
        except ValidationError as problem:
            last_error = f"The draft did not match the required shape: {problem.error_count()} problem(s)."
            continue
        except Exception as problem:  # network, throttling, access denied
            path.append("bedrock_error")
            fallback = _cached(skill_id, band)
            if fallback is None:
                return PipelineResult(None, citations, "none", path, f"Bedrock call failed: {problem}")
            fallback, _ = _verify_grounding(fallback, sources)
            return PipelineResult(fallback, citations, "cached", path,
                                  "Bedrock was unavailable, so a previously generated draft is shown.")
        path.append("verify_grounding")
        draft, warning = _verify_grounding(draft, sources)
        return PipelineResult(draft, citations, "bedrock", path + ["present"], warning)

    path.append("template_fallback")
    fallback = _cached(skill_id, band)
    if fallback is None:
        return PipelineResult(None, citations, "none", path, last_error)
    fallback, _ = _verify_grounding(fallback, sources)
    return PipelineResult(fallback, citations, "cached", path,
                          f"{last_error} A previously generated draft is shown instead.")
