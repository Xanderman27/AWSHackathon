"""The shape of an activity draft.

This model is the contract in three places at once: the Bedrock tool definition the model is
told to call, the validator every response passes through before anyone sees it, and the row
written to the `recommendations` collection. One definition, so a model that drifts from the
shape fails validation rather than reaching a family.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ActivityDraft(BaseModel):
    title: str = Field(min_length=4, max_length=90, description="A short, warm name for the activity.")
    why: str = Field(
        min_length=20, max_length=700,
        description="Two or three short sentences, under 500 characters, in plain language a "
                    "family can read. Describe what the learner can already do and what this "
                    "builds next. Never name a disability, a diagnosis, or a deficit.",
    )
    minutes: int = Field(ge=5, le=30, description="Realistic minutes at a kitchen table.")
    materials: list[str] = Field(
        min_length=1, max_length=6,
        description="Everyday household items only. No purchases, no printing.",
    )
    steps: list[str] = Field(
        min_length=3, max_length=6,
        description="What the adult and child do, one short sentence each, in order.",
    )
    citations: list[str] = Field(
        min_length=1,
        description="The source ids this draft was built from. Use only ids that were provided.",
    )


TOOL_NAME = "submit_activity"


def tool_config() -> dict:
    """The Converse toolConfig. The model is required to answer by calling this tool, which is
    how a free-text reply becomes a validated object instead of something to parse."""
    schema = ActivityDraft.model_json_schema()
    schema.pop("title", None)  # the JSON Schema's own title, not our field
    return {
        "tools": [{
            "toolSpec": {
                "name": TOOL_NAME,
                "description": "Return one teacher-reviewable activity for a family to try at home.",
                "inputSchema": {"json": schema},
            }
        }],
        "toolChoice": {"tool": {"name": TOOL_NAME}},
    }


class DraftDecision(BaseModel):
    decision: Literal["approve", "reject"]
    # A teacher may fix wording before it reaches a family; FR-11 says approve or edit.
    edited: ActivityDraft | None = None
    note: str = Field(default="", max_length=400)
