"""The grounded recommendation pipeline.

Two things matter most here and both are tested against the real request payload rather than
by reading the code: what we send to Bedrock contains nothing that identifies a child, and
nothing generated reaches a family without a teacher approving it.
"""

import json
import re
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.ai import generate, retrieval
from app.ai.config import Settings
from app.ai.schema import ActivityDraft
from app.main import app
from app.storage import store
from authhelp import auth

TEACHER = auth("teacher", "teacher-01")
PARENT = auth("parent", "parent-01")

LIVE = Settings(region="us-east-1", model_id="test-model", guardrail_id="gr-1",
                guardrail_version="1", offline=False)
OFFLINE = Settings(region="us-east-1", model_id="test-model", guardrail_id=None,
                   guardrail_version="DRAFT", offline=True)

GOOD_DRAFT = {
    "title": "Paper strips on the table",
    "why": "Your child can match fractions as pictures, and folding strips connects that to the numbers.",
    "minutes": 12,
    "materials": ["Paper", "Scissors"],
    "steps": ["Cut four strips.", "Fold them into halves and quarters.", "Compare what you shaded."],
    "citations": ["ccss-4nf-a1"],
}


def converse_returning(payload, name="submit_activity"):
    return {"output": {"message": {"content": [{"toolUse": {"name": name, "input": payload}}]}}}


@pytest.fixture
def live_bedrock():
    """A stand-in bedrock-runtime client, so the request we build is inspectable."""
    client = MagicMock()
    with (
        patch.object(generate, "settings", lambda: LIVE),
        patch("boto3.client", return_value=client),
    ):
        yield client


# --- what leaves this machine -------------------------------------------------------------

def test_nothing_identifying_reaches_the_model(live_bedrock):
    live_bedrock.converse.return_value = converse_returning(GOOD_DRAFT)
    generate.propose("fraction_equivalence", "Equivalent fractions", "building", 5, 0.4)

    sent = live_bedrock.converse.call_args.kwargs
    said = sent["messages"][0]["content"][0]["text"].lower()

    # Whole words only: "same size" is not a learner called Sam.
    def leaks(word: str, text: str) -> bool:
        return re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text) is not None

    # No identity anywhere in the message: every seeded learner, both parents, the teacher,
    # the class, a user id, and the photo paths.
    for name in ("sam", "ava", "leo", "mia", "noah", "zoe", "eli", "ivy", "kai", "ruby",
                 "owen", "lily", "jordan", "priya", "rivera", "class-4a", "student-01", "/faces/"):
        assert not leaks(name, said), f"{name!r} reached the model"

    # The learner-derived part carries no sensitive category either. (The approved sources and
    # the system block do use words like "disability" — as the rule never to mention one, which
    # is the point of shipping them.)
    summary = said.split("approved sources:")[0]
    for sensitive in ("iep", "504", "disability", "diagnosis", "goal link", "plan"):
        assert not leaks(sensitive, summary), f"{sensitive!r} reached the model about this learner"

    system = " ".join(block["text"] for block in sent["system"]).lower()
    for rule in ("disability", "diagnosis", "never diagnose"):
        assert rule in system, f"the system block should forbid {rule!r}"


def test_the_summary_says_where_a_learner_is_without_saying_who():
    summary = generate.summarise("building", 5, 0.4, "Equivalent fractions").lower()
    assert "equivalent fractions" in summary and "5 answers" in summary
    assert "sam" not in summary and "student" not in summary.replace("students", "")


def test_the_request_forces_the_tool_and_carries_the_guardrail(live_bedrock):
    live_bedrock.converse.return_value = converse_returning(GOOD_DRAFT)
    generate.propose("fraction_equivalence", "Equivalent fractions", "practicing", 4)

    sent = live_bedrock.converse.call_args.kwargs
    assert sent["modelId"] == "test-model"
    assert sent["toolConfig"]["toolChoice"] == {"tool": {"name": "submit_activity"}}
    assert sent["guardrailConfig"] == {"guardrailIdentifier": "gr-1", "guardrailVersion": "1"}
    # Only the approved sources we chose are in the prompt.
    prompt = sent["messages"][0]["content"][0]["text"]
    assert "[ccss-4nf-a1]" in prompt


def test_no_guardrail_configured_means_no_guardrail_key():
    client = MagicMock()
    client.converse.return_value = converse_returning(GOOD_DRAFT)
    unguarded = Settings(region="us-east-1", model_id="m", guardrail_id=None,
                         guardrail_version="DRAFT", offline=False)
    with patch.object(generate, "settings", lambda: unguarded), patch("boto3.client", return_value=client):
        generate.propose("fraction_equivalence", "Equivalent fractions", "practicing", 4)
    assert "guardrailConfig" not in client.converse.call_args.kwargs


# --- what comes back ----------------------------------------------------------------------

def test_a_valid_response_is_presented_as_generated(live_bedrock):
    live_bedrock.converse.return_value = converse_returning(GOOD_DRAFT)
    result = generate.propose("fraction_equivalence", "Equivalent fractions", "building", 5)
    assert result.origin == "bedrock"
    assert result.path[-1] == "present"
    assert result.draft.title == "Paper strips on the table"


def test_an_invented_citation_is_stripped_and_flagged(live_bedrock):
    made_up = {**GOOD_DRAFT, "citations": ["ccss-4nf-a1", "journal-of-things-i-made-up"]}
    live_bedrock.converse.return_value = converse_returning(made_up)
    result = generate.propose("fraction_equivalence", "Equivalent fractions", "building", 5)
    assert result.draft.citations == ["ccss-4nf-a1"]
    assert "did not match an approved source" in result.warning


def test_a_draft_citing_nothing_real_is_handed_over_marked_unverified(live_bedrock):
    live_bedrock.converse.return_value = converse_returning({**GOOD_DRAFT, "citations": ["nope"]})
    result = generate.propose("fraction_equivalence", "Equivalent fractions", "building", 5)
    assert result.draft.citations == []
    assert "unverified" in result.warning


def test_a_malformed_response_is_retried_once_then_falls_back(live_bedrock):
    live_bedrock.converse.return_value = converse_returning({"title": "too short"})
    result = generate.propose("fraction_equivalence", "Equivalent fractions", "building", 5)
    assert live_bedrock.converse.call_count == 2
    assert "template_fallback" in result.path
    assert result.origin == "cached"


def test_bedrock_being_down_shows_a_cached_draft_and_says_so(live_bedrock):
    live_bedrock.converse.side_effect = RuntimeError("AccessDeniedException")
    result = generate.propose("fraction_equivalence", "Equivalent fractions", "practicing", 4)
    assert result.origin == "cached"
    assert "bedrock_error" in result.path
    assert "unavailable" in result.warning


def test_offline_never_reaches_the_network():
    with patch.object(generate, "settings", lambda: OFFLINE), patch("boto3.client") as client:
        result = generate.propose("fraction_equivalence", "Equivalent fractions", "building", 5)
    client.assert_not_called()
    assert result.origin == "cached"


def test_a_skill_with_no_approved_source_drafts_nothing():
    with patch.object(generate, "settings", lambda: OFFLINE):
        result = generate.propose("underwater_basket_weaving", "Underwater basket weaving", "building", 2)
    assert result.draft is None
    assert "no_source_fallback" in result.path


# --- the corpus gate ----------------------------------------------------------------------

def test_a_document_without_provenance_is_not_retrievable():
    incomplete = [{"id": "sketchy", "tier": 2, "doc_type": "misconception", "title": "No citation",
                   "text": "fractions fractions fractions", "source_org": "", "source_url": "",
                   "citation": "", "approved_by": "", "approved_on": ""}]
    retrieval._documents.cache_clear()
    with patch.object(retrieval, "_documents", lambda: [d for d in incomplete
                                                        if all(d.get(f) for f in retrieval.REQUIRED)]):
        assert retrieval.retrieve("fractions") == []
    retrieval._documents.cache_clear()


def test_every_cached_draft_only_cites_sources_the_pipeline_actually_retrieves():
    """A cached draft is a frozen pipeline output, so it must pass the same grounding check a
    live one does. Without this, the demo shows 'citations were removed' on its own fixtures."""
    from app.ai.cached import CACHED_DRAFTS
    names = {"fraction_equivalence": "Equivalent fractions",
             "main_idea": "Main idea and supporting details"}
    for (skill_id, band), draft in CACHED_DRAFTS.items():
        available = {s.id for s in generate.gather(skill_id, names[skill_id], band)}
        assert set(draft.citations) <= available, f"{skill_id}/{band} cites something not retrieved"


def test_the_band_changes_which_template_is_retrieved():
    """Retrieval responds to where the learner is; otherwise this is a fixed prompt with the
    skill pasted in."""
    first_template = {}
    for band in ("building", "practicing"):
        sources = generate.gather("fraction_equivalence", "Equivalent fractions", band)
        first_template[band] = next(s.id for s in sources if s.doc_type == "activity-template")
    assert first_template["building"] != first_template["practicing"]


def test_every_shipped_source_carries_its_provenance():
    for source in retrieval.retrieve("", limit=999):
        assert source.citation and source.source_url and source.tier in (1, 2, 3)


# --- the approval gate --------------------------------------------------------------------

@pytest.fixture
def recs():
    real = store.read
    data = {"recommendations": [], "audit": []}
    with (
        patch.object(store, "read", side_effect=lambda n: data[n] if n in data else real(n)),
        patch.object(store, "append", side_effect=lambda n, row: data[n].append(row)),
        patch.object(store, "upsert", side_effect=lambda n, row, key="id": data.__setitem__(
            n, [row if r.get(key) == row[key] else r for r in data[n]])),
    ):
        yield TestClient(app), data


def test_a_proposal_is_recorded_before_anyone_decides(recs):
    client, data = recs
    response = client.post("/teacher/recommendations/draft", headers=TEACHER,
                           json={"student_id": "student-01", "skill_id": "fraction_equivalence"})
    assert response.status_code == 201
    row = response.json()
    assert row["status"] == "proposed" and row["approved_by"] is None
    assert [a["action"] for a in data["audit"]] == ["recommendation.proposed"]
    assert row["citations"], "a draft always ships with the sources it was built from"


def test_an_unapproved_draft_never_reaches_a_family(recs):
    client, _ = recs
    client.post("/teacher/recommendations/draft", headers=TEACHER,
                json={"student_id": "student-01", "skill_id": "fraction_equivalence"})
    steps = client.get("/parent/children/student-01/progress", headers=PARENT).json()["next_steps"]
    assert steps == [], "only an approved, family-audience recommendation is a next step"


def test_approving_publishes_it_and_rejecting_does_not(recs):
    client, data = recs
    for decision, expected in (("approve", 1), ("reject", 0)):
        data["recommendations"].clear()
        rec_id = client.post("/teacher/recommendations/draft", headers=TEACHER,
                             json={"student_id": "student-01", "skill_id": "fraction_equivalence"}).json()["id"]
        client.post(f"/teacher/recommendations/{rec_id}/decision", headers=TEACHER,
                    json={"decision": decision})
        steps = client.get("/parent/children/student-01/progress", headers=PARENT).json()["next_steps"]
        assert len(steps) == expected, decision


def test_a_teacher_edit_is_marked_as_the_teachers_words(recs):
    client, _ = recs
    rec_id = client.post("/teacher/recommendations/draft", headers=TEACHER,
                         json={"student_id": "student-01", "skill_id": "fraction_equivalence"}).json()["id"]
    edited = ActivityDraft(**{**GOOD_DRAFT, "title": "My own version"})
    row = client.post(f"/teacher/recommendations/{rec_id}/decision", headers=TEACHER,
                      json={"decision": "approve", "edited": edited.model_dump()}).json()
    assert row["title"] == "My own version"
    assert row["origin"].endswith("+teacher-edited")


def test_a_decision_cannot_be_made_twice(recs):
    client, _ = recs
    rec_id = client.post("/teacher/recommendations/draft", headers=TEACHER,
                         json={"student_id": "student-01", "skill_id": "fraction_equivalence"}).json()["id"]
    client.post(f"/teacher/recommendations/{rec_id}/decision", headers=TEACHER, json={"decision": "approve"})
    again = client.post(f"/teacher/recommendations/{rec_id}/decision", headers=TEACHER, json={"decision": "reject"})
    assert again.status_code == 409


def test_only_a_teacher_can_draft_or_decide(recs):
    client, _ = recs
    for headers in (PARENT, auth("student", "student-01")):
        assert client.post("/teacher/recommendations/draft", headers=headers,
                           json={"student_id": "student-01", "skill_id": "fraction_equivalence"}).status_code == 403
        assert client.get("/teacher/ai/status", headers=headers).status_code == 403


def test_a_teacher_cannot_draft_for_a_learner_outside_their_class(recs):
    client, _ = recs
    assert client.post("/teacher/recommendations/draft", headers=TEACHER,
                       json={"student_id": "student-99", "skill_id": "fraction_equivalence"}).status_code == 403
