"""Core entities from PRD §18. Kept minimal for the skeleton; fields grow with features."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["student", "teacher", "parent"]
Confidence = Literal["low", "medium", "high"]
Band = Literal["building", "practicing", "extension"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Choice(BaseModel):
    id: str
    text: str
    misconception: Optional[str] = None  # tag used by the pattern classifier (Layer 3)


class Item(BaseModel):
    id: str
    skill_id: str
    prerequisite_skill_id: Optional[str] = None
    difficulty: int = Field(ge=1, le=5)  # author rating; IRT calibration overrides later
    irt_a: float = 1.0  # discrimination
    irt_b: float = 0.0  # difficulty on the theta scale
    prompt: str
    image_alt: Optional[str] = None
    choices: list[Choice]
    answer: str
    hint: str
    explanation: str
    passage: Optional[str] = None
    passage_read_aloud_allowed: bool = True
    approved: bool = True


class Skill(BaseModel):
    id: str
    subject: str
    name: str
    child_name: str  # what the child sees
    standard_framework: str
    standard_id: str
    grade: int
    prerequisites: list[str] = []


class Student(BaseModel):
    id: str
    display_name: str
    grade: int
    class_id: str
    has_goal_link: bool = False  # teacher-only marker; never sent to models


class ParentStudentLink(BaseModel):
    parent_id: str
    student_id: str


class MasteryState(BaseModel):
    student_id: str
    skill_id: str
    estimate: float
    evidence_count: int = 0
    history: list[float] = []
    updated_at: str = Field(default_factory=now)


class ItemResponse(BaseModel):
    item_id: str
    choice_id: str
    correct: bool
    hint_used: bool
    route_reason: Optional[str] = None
    at: str = Field(default_factory=now)


class Attempt(BaseModel):
    id: str
    student_id: str
    skill_id: str  # assigned objective
    current_skill_id: str  # may route to a prerequisite
    responses: list[ItemResponse] = []
    max_items: int = 6
    completed: bool = False
    started_at: str = Field(default_factory=now)


class NextItem(BaseModel):
    """What the student screen receives. No mastery numbers."""

    attempt_id: str
    position: int
    total: int
    item: Optional[Item]
    completed: bool
    summary: Optional[str] = None


class AnswerIn(BaseModel):
    choice_id: str
    hint_used: bool = False


class AnswerOut(BaseModel):
    correct: bool
    feedback: str
    next: NextItem
