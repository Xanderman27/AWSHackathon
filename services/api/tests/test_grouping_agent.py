"""The grouping agent.

Unlike the activity pipeline, this one really is an agent: toolChoice is "auto", so the model
decides whom to look up and when to stop. These tests pin the loop mechanics and — the part
that matters — that a learner's identity never reaches the model.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.ai import grouping
from app.ai.config import Settings

LIVE = Settings(region="us-east-1", model_id="m", guardrail_id="family-1",
                guardrail_version="1", offline=False,
                teacher_guardrail_id="teacher-1", teacher_guardrail_version="1")
OFFLINE = Settings(region="us-east-1", model_id="m", guardrail_id=None,
                   guardrail_version="DRAFT", offline=True)

MASTERY = [
    {"student_id": "student-01", "skill_id": "fraction_equivalence", "estimate": 0.35,
     "evidence_count": 4, "history": [0.19, 0.38, 0.27, 0.35]},
    {"student_id": "student-02", "skill_id": "fraction_equivalence", "estimate": 0.58,
     "evidence_count": 6, "history": [0.5, 0.54, 0.58]},
]
SKILLS = {"fraction_equivalence": {"name": "Equivalent fractions"}}
GROUP = ["student-01", "student-02"]

GOOD = {"why_together": "L1 and L2 both have recent evidence on equivalent fractions and sit "
                        "close together, so one activity suits both.",
        "watch_for": "Whether one of them does all the talking."}


def tool_use(name, payload, use_id="t1"):
    return {"stopReason": "tool_use",
            "output": {"message": {"content": [{"toolUse": {"name": name, "input": payload,
                                                            "toolUseId": use_id}}]}}}


@pytest.fixture
def client():
    fake = MagicMock()
    with patch.object(grouping, "settings", lambda: LIVE), patch("boto3.client", return_value=fake):
        yield fake


# --- privacy -----------------------------------------------------------------------------

def test_no_learner_identity_reaches_the_model(client):
    client.converse.return_value = tool_use("submit_explanation", GOOD)
    grouping.explain(GROUP, "Equivalent fractions", MASTERY, SKILLS)

    sent = json.dumps(client.converse.call_args.kwargs).lower()
    for identifying in ("student-01", "student-02", "sam", "ava", "class-4a", "/faces/"):
        assert identifying not in sent, f"{identifying!r} reached the model"
    # It gets tags and evidence, nothing else.
    assert "l1" in sent and "equivalent fractions" in sent


def test_the_roster_holds_the_mapping_back(client):
    roster = grouping.Roster.build(GROUP, MASTERY, SKILLS)
    assert list(roster.by_ref) == ["L1", "L2"]
    assert roster.ref_of == {"student-01": "L1", "student-02": "L2"}
    # What the model sees about one learner: band, evidence, trajectory. No id.
    assert set(roster.by_ref["L1"]) == {"ref", "skills"}
    assert "student" not in json.dumps(roster.by_ref).lower()


# --- the agent loop ----------------------------------------------------------------------

def test_the_model_chooses_whether_to_call_tools(client):
    """toolChoice is auto. Forcing a tool would make this structured output, not an agent."""
    client.converse.return_value = tool_use("submit_explanation", GOOD)
    grouping.explain(GROUP, "Equivalent fractions", MASTERY, SKILLS)
    assert client.converse.call_args.kwargs["toolConfig"]["toolChoice"] == {"auto": {}}


def test_a_lookup_is_answered_and_the_loop_continues(client):
    client.converse.side_effect = [
        tool_use("look_up_learner", {"ref": "L2"}, "call-1"),
        tool_use("submit_explanation", GOOD, "call-2"),
    ]
    result = grouping.explain(GROUP, "Equivalent fractions", MASTERY, SKILLS)

    assert result.origin == "bedrock"
    assert result.inspected == ["L2"]
    assert result.turns == 2

    # The second call carries the tool result for exactly the learner that was asked about.
    second = client.converse.call_args_list[1].kwargs["messages"]
    payload = second[-1]["content"][0]["toolResult"]["content"][0]["json"]
    assert payload["ref"] == "L2"
    assert payload["skills"][0]["trajectory"]


def test_an_unknown_tag_is_answered_with_an_error_not_a_crash(client):
    client.converse.side_effect = [
        tool_use("look_up_learner", {"ref": "L9"}, "call-1"),
        tool_use("submit_explanation", GOOD, "call-2"),
    ]
    result = grouping.explain(GROUP, "Equivalent fractions", MASTERY, SKILLS)
    assert result.inspected == []
    second = client.converse.call_args_list[1].kwargs["messages"]
    assert "error" in second[-1]["content"][0]["toolResult"]["content"][0]["json"]


def test_teacher_guardrail_is_used_not_the_family_one(client):
    """Comparison is the point here and forbidden in family text, so the policies differ."""
    client.converse.return_value = tool_use("submit_explanation", GOOD)
    grouping.explain(GROUP, "Equivalent fractions", MASTERY, SKILLS)
    assert client.converse.call_args.kwargs["guardrailConfig"]["guardrailIdentifier"] == "teacher-1"


def test_a_missing_teacher_guardrail_falls_back_to_the_stricter_one():
    only_family = Settings(region="r", model_id="m", guardrail_id="family-1",
                           guardrail_version="1", offline=False)
    assert only_family.teacher_guardrail == only_family.guardrail


# --- when it does not work ----------------------------------------------------------------

def test_a_guardrail_block_is_reported_as_that_not_as_a_turn_limit(client):
    client.converse.return_value = {"stopReason": "guardrail_intervened",
                                    "output": {"message": {"content": [{"text": "withheld"}]}}}
    result = grouping.explain(GROUP, "Equivalent fractions", MASTERY, SKILLS)
    assert result.origin == "fallback"
    assert "guardrail" in result.warning.lower()


def test_prose_instead_of_a_tool_call_is_nudged_once(client):
    prose = {"stopReason": "end_turn", "output": {"message": {"content": [{"text": "sure thing"}]}}}
    client.converse.side_effect = [prose, tool_use("submit_explanation", GOOD)]
    result = grouping.explain(GROUP, "Equivalent fractions", MASTERY, SKILLS)
    assert result.origin == "bedrock"
    assert client.converse.call_count == 2


def test_a_malformed_explanation_names_the_field(client):
    client.converse.return_value = tool_use("submit_explanation", {"why_together": "too short"})
    result = grouping.explain(GROUP, "Equivalent fractions", MASTERY, SKILLS)
    assert result.origin == "fallback"
    assert "why_together" in result.warning


def test_offline_never_touches_the_network():
    with patch.object(grouping, "settings", lambda: OFFLINE), patch("boto3.client") as client:
        result = grouping.explain(GROUP, "Equivalent fractions", MASTERY, SKILLS)
    client.assert_not_called()
    assert result.origin == "fallback" and result.explanation is not None


# --- the trajectory wording ---------------------------------------------------------------

@pytest.mark.parametrize("history, expected", [
    ([0.19, 0.38, 0.51], "rising steadily"),
    ([0.19, 0.38, 0.27, 0.35], "rising overall but up and down between checks"),
    ([0.66, 0.41, 0.62, 0.55], "slipping overall but up and down between checks"),
    ([0.5, 0.5, 0.51], "flat across recent checks"),
    ([0.66], "only one check so far, so no direction yet"),
])
def test_a_trajectory_reads_as_an_observation(history, expected):
    """A single reversal matters: calling 0.19, 0.38, 0.27, 0.35 simply 'rising' would flatten
    the thing a teacher most needs to notice."""
    assert grouping.trend(history) == expected
