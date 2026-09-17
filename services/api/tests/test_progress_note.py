"""The progress-note agent (FR-25).

IDEA requires periodic reports on progress toward annual goals. This is the piece that turns
evidence into that sentence, so the tests that matter are about what the model is allowed to
know — the plan document must never reach it — and that a thin evidence base is reported as
thin rather than rounded up into a claim.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.ai import progress
from app.ai.config import Settings
from app.main import app
from app.storage import store
from authhelp import auth

TEACHER = auth("teacher", "teacher-01")
PARENT = auth("parent", "parent-01")

LIVE = Settings(region="r", model_id="m", guardrail_id="g", guardrail_version="1", offline=False)
OFFLINE = Settings(region="r", model_id="m", guardrail_id=None, guardrail_version="DRAFT", offline=True)

MASTERY = [
    {"student_id": "student-01", "skill_id": "main_idea", "estimate": 0.62,
     "evidence_count": 5, "history": [0.4, 0.55, 0.62]},
    {"student_id": "student-01", "skill_id": "fraction_equivalence", "estimate": 0.48,
     "evidence_count": 5, "history": [0.19, 0.38, 0.48]},
]
SKILLS = {"main_idea": {"name": "Main idea and supporting details", "subject": "english"},
          "fraction_equivalence": {"name": "Equivalent fractions", "subject": "math"}}
RECS = [{"student_id": "student-01", "status": "approved", "title": "Read together and say it back",
         "approved_on": "2026-09-10T00:00:00+00:00"}]

NOTE = {"statement": "Your child can find the main idea some of the time, and their recent "
                     "check-ins have been moving the right way. Next is doing it consistently.",
        "evidence_cited": ["Main idea and supporting details"], "sufficiency": "enough"}


def tool_use(name, payload, use_id="t1"):
    return {"stopReason": "tool_use",
            "output": {"message": {"content": [{"toolUse": {"name": name, "input": payload,
                                                            "toolUseId": use_id}}]}}}


@pytest.fixture
def client():
    fake = MagicMock()
    with patch.object(progress, "settings", lambda: LIVE), patch("boto3.client", return_value=fake):
        yield fake


# --- what the model is allowed to know ----------------------------------------------------

def test_the_plan_document_never_reaches_the_model(client):
    """plans.json holds an eligibility category, services and present levels. None of it is
    the model's business, and the goal's free-text 'why' is excluded too: a teacher wrote it
    and it routinely contains the child's name and the word IEP."""
    client.converse.return_value = tool_use("submit_progress_note", NOTE)
    progress.draft("Find the main idea without a hint", "student-01", MASTERY, SKILLS, RECS)

    sent = json.dumps(client.converse.call_args.kwargs["messages"]).lower()
    for forbidden in ("specific learning disability", "eligibility", "present levels",
                      "accommodation", "services", "case manager", "sam", "student-01",
                      "iep", "504"):
        assert forbidden not in sent, f"{forbidden!r} reached the model"
    assert "find the main idea without a hint" in sent  # the goal title itself is the subject


def test_the_evidence_tools_expose_only_learning(client):
    evidence = progress.Evidence.build("student-01", MASTERY, SKILLS, RECS)
    everything = json.dumps([evidence.answer("skills_with_evidence", {}),
                             evidence.answer("evidence_for_skill", {"skill": "Main idea and supporting details"}),
                             evidence.answer("activities_tried", {})]).lower()
    for forbidden in ("student-01", "sam", "estimate", "0.62"):
        assert forbidden not in everything, f"{forbidden!r} is exposed by a tool"
    # What it does expose: a band and a trajectory in words.
    assert "practicing" in everything and "rising" in everything


# --- the loop ------------------------------------------------------------------------------

def test_it_investigates_before_writing(client):
    client.converse.side_effect = [
        tool_use("skills_with_evidence", {}, "a"),
        tool_use("evidence_for_skill", {"skill": "Main idea and supporting details"}, "b"),
        tool_use("submit_progress_note", NOTE, "c"),
    ]
    result = progress.draft("Find the main idea", "student-01", MASTERY, SKILLS, RECS)
    assert result.origin == "bedrock" and result.turns == 3
    assert "Main idea and supporting details" in result.looked_at


def test_asking_about_a_skill_with_no_evidence_gets_an_answer_not_a_crash(client):
    client.converse.side_effect = [
        tool_use("evidence_for_skill", {"skill": "Underwater basket weaving"}, "a"),
        tool_use("submit_progress_note", NOTE, "b"),
    ]
    progress.draft("A goal", "student-01", MASTERY, SKILLS, RECS)
    second = client.converse.call_args_list[1].kwargs["messages"]
    answer = second[-1]["content"][0]["toolResult"]["content"][0]["json"]
    assert "error" in answer and answer["available"]


def test_thin_evidence_is_reported_as_thin_not_rounded_up(client):
    """FR-19: ask for more evidence rather than assert mastery."""
    thin = {**NOTE, "sufficiency": "thin"}
    client.converse.return_value = tool_use("submit_progress_note", thin)
    result = progress.draft("A goal", "student-01", MASTERY, SKILLS, RECS)
    assert result.note.sufficiency == "thin"


def test_offline_produces_a_placeholder_marked_thin():
    with patch.object(progress, "settings", lambda: OFFLINE), patch("boto3.client") as client:
        result = progress.draft("Find the main idea", "student-01", MASTERY, SKILLS, RECS)
    client.assert_not_called()
    assert result.origin == "fallback"
    # A placeholder must never claim progress it has not checked.
    assert result.note.sufficiency == "thin"


# --- the approval gate ---------------------------------------------------------------------

@pytest.fixture
def goals():
    real = store.read
    data = {"goals": [{"id": "goal-01", "student_id": "student-01", "title": "Find the main idea",
                       "why": "Sam's IEP reading goal", "status": "active",
                       "created_by": "teacher-01", "created_by_name": "Ms. Rivera",
                       "created_by_role": "teacher", "at": "2026-09-10T00:00:00+00:00",
                       "decided_by": None}], "audit": []}
    with (
        patch.object(store, "read", side_effect=lambda n: data[n] if n in data else real(n)),
        patch.object(store, "append", side_effect=lambda n, row: data[n].append(row)),
        patch.object(store, "upsert", side_effect=lambda n, row, key="id": data.__setitem__(
            n, [row if r.get(key) == row[key] else r for r in data[n]])),
        patch.object(progress, "settings", lambda: OFFLINE),
    ):
        yield TestClient(app), data


def test_drafting_saves_nothing(goals):
    client, data = goals
    response = client.post("/support/goals/goal-01/progress-note/draft", headers=TEACHER)
    assert response.status_code == 200 and response.json()["statement"]
    assert "progress_note" not in data["goals"][0], "a draft is not a published note"
    assert data["audit"][0]["action"] == "goal.progress_note.drafted"


def test_only_a_published_note_lands_on_the_goal(goals):
    client, data = goals
    client.post("/support/goals/goal-01/progress-note", headers=TEACHER,
                json={"statement": "The teacher's own words, edited from the draft."})
    assert data["goals"][0]["progress_note"] == "The teacher's own words, edited from the draft."
    assert data["goals"][0]["progress_noted_by"] == "teacher-01"
    assert [a["action"] for a in data["audit"]] == ["goal.progress_note.published"]


def test_a_parent_cannot_draft_or_publish(goals):
    client, _ = goals
    assert client.post("/support/goals/goal-01/progress-note/draft", headers=PARENT).status_code == 403
    assert client.post("/support/goals/goal-01/progress-note", headers=PARENT,
                       json={"statement": "x" * 30}).status_code == 403


def test_a_teacher_cannot_touch_a_goal_outside_their_class(goals):
    client, data = goals
    data["goals"][0]["student_id"] = "student-99"
    assert client.post("/support/goals/goal-01/progress-note/draft", headers=TEACHER).status_code == 404
