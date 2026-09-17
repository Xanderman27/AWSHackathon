"""The class summary's confidence and its deeper aggregates.

The regression pinned here is a quiet one. `_correct_flags` accepted a `skill_id` and then
ignored it, so every skill's confidence was computed from the learner's entire answer log
across every subject. It was invisible for as long as the attempt log was empty; the moment
demo activity was seeded, a learner with one answer in science read "high confidence" on the
strength of their maths practice.

That matters beyond a wrong label: confidence gates definitive recommendations and cohort
placement (docs/GUIDELINES.md §5.4), so an inflated one lets the product act on evidence it
does not have.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import store

TEACHER = {"X-Role": "teacher", "X-User-Id": "teacher-01"}

STUDENTS = [{"id": "student-01", "display_name": "Sam", "grade": 4, "class_id": "class-4a"}]
SKILLS = [
    {"id": "maths-a", "subject": "math", "name": "Equivalent fractions"},
    {"id": "science-a", "subject": "science", "name": "States of matter"},
]
ITEMS = [{"id": "m1", "skill_id": "maths-a"}, {"id": "m2", "skill_id": "maths-a"},
         {"id": "m3", "skill_id": "maths-a"}, {"id": "m4", "skill_id": "maths-a"},
         {"id": "m5", "skill_id": "maths-a"}, {"id": "m6", "skill_id": "maths-a"},
         {"id": "s1", "skill_id": "science-a"}]

# Six answers in maths, one in science. Science must not inherit maths' confidence.
ATTEMPTS = [
    {"id": "a1", "student_id": "student-01", "skill_id": "maths-a", "current_skill_id": "maths-a",
     "completed": True, "started_at": "2026-09-10T09:00:00+00:00",
     "responses": [{"item_id": f"m{i}", "choice_id": "a", "correct": True, "hint_used": i == 1,
                    "at": "2026-09-10T09:0%d:00+00:00" % i} for i in range(1, 7)]},
    {"id": "a2", "student_id": "student-01", "skill_id": "science-a", "current_skill_id": "science-a",
     "completed": False, "started_at": "2026-09-11T09:00:00+00:00",
     "responses": [{"item_id": "s1", "choice_id": "b", "correct": False, "hint_used": False,
                    "at": "2026-09-11T09:01:00+00:00"}]},
]

MASTERY = [
    {"student_id": "student-01", "skill_id": "maths-a", "estimate": 0.72,
     "evidence_count": 6, "history": [0.3, 0.4, 0.5, 0.6, 0.68, 0.72]},
    {"student_id": "student-01", "skill_id": "science-a", "estimate": 0.30,
     "evidence_count": 1, "history": [0.30]},
]

FIXTURE = {
    "students": STUDENTS, "skills": SKILLS, "items": ITEMS, "attempts": ATTEMPTS,
    "mastery": MASTERY, "benchmarks": [], "group_activities": [], "links": [],
    "teachers": [{"id": "teacher-01", "display_name": "Ms. Rivera", "class_id": "class-4a"}],
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(store, "read", lambda name: FIXTURE.get(name, []))
    return TestClient(app)


def summary(client):
    response = client.get("/teacher/class", headers=TEACHER)
    assert response.status_code == 200
    return response.json()


def test_confidence_is_per_skill_not_pooled_across_subjects(client):
    rows = {r["skill_id"]: r for r in summary(client)["mastery"]}
    # Six steady answers is the high-confidence threshold in bkt.confidence.
    assert rows["maths-a"]["confidence"] == "high"
    # One answer cannot be anything but low, whatever the learner did in another subject.
    assert rows["science-a"]["confidence"] == "low"


def test_needs_more_evidence_counts_the_low_rows(client):
    body = summary(client)
    assert body["counts"]["needs_more_evidence"] == 1
    assert body["class_stats"]["confidence_mix"] == {"low": 1, "medium": 0, "high": 1}
    assert body["class_stats"]["needs_more_evidence"] == 1


def test_accuracy_and_hint_rate_come_from_the_response_log(client):
    stats = summary(client)["class_stats"]
    assert stats["checkins"] == 7          # six maths answers plus one science
    assert stats["accuracy"] == round(6 / 7, 2)
    assert stats["hint_rate"] == round(1 / 7, 2)


def test_the_daily_series_is_a_fixed_window_and_never_ranks_a_learner(client):
    stats = summary(client)["class_stats"]
    assert len(stats["daily"]) == 14
    assert [d["date"] for d in stats["daily"]] == sorted(d["date"] for d in stats["daily"])
    # Aggregate only: no learner name appears anywhere in the class statistics block.
    assert "Sam" not in str(stats)


def test_collaboration_reports_who_has_been_left_out(client):
    collab = summary(client)["class_stats"]["collaboration"]
    assert collab["activities"] == 0
    # With no group work at all, the one learner in this class is the one left out.
    assert collab["never_grouped"] == 1
    assert collab["diversity"] == 0.0
