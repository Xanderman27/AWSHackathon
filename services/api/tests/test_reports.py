"""The summary a family can take to their child's doctor.

This is the one payload in the product designed to leave it, so the tests are mostly about
what must not travel: another family's child, a comparison, a teacher-only field, or a
recommendation the teacher never approved. The disclaimer is asserted too, because a summary
that lands on a clinician's desk without it is exactly the misread the product is built to
avoid (docs/GUIDELINES.md §1.5).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import store

PARENT = {"X-Role": "parent", "X-User-Id": "parent-01"}       # linked to student-01 (Sam)
OTHER_PARENT = {"X-Role": "parent", "X-User-Id": "parent-02"}  # linked to student-02 (Ava)
TEACHER = {"X-Role": "teacher", "X-User-Id": "teacher-01"}
STUDENT = {"X-Role": "student", "X-User-Id": "student-01"}

STUDENTS = [
    {"id": "student-01", "display_name": "Sam", "grade": 4, "class_id": "class-4a",
     "has_goal_link": True},
    {"id": "student-02", "display_name": "Ava", "grade": 4, "class_id": "class-4a",
     "has_goal_link": False},
]
SKILLS = [{"id": "maths-a", "subject": "math", "name": "Equivalent fractions",
           "child_name": "fractions that are the same amount", "standard_id": "4.NF.A.1"}]
ITEMS = [{"id": f"m{i}", "skill_id": "maths-a"} for i in range(1, 7)]
ATTEMPTS = [{
    "id": "a1", "student_id": "student-01", "skill_id": "maths-a", "current_skill_id": "maths-a",
    "completed": True, "started_at": "2026-09-10T09:00:00+00:00",
    "responses": [{"item_id": f"m{i}", "choice_id": "a", "correct": i % 2 == 0,
                   "hint_used": i == 1, "at": f"2026-09-1{i}T09:00:00+00:00"} for i in range(1, 6)],
}]
MASTERY = [
    {"student_id": "student-01", "skill_id": "maths-a", "estimate": 0.62,
     "evidence_count": 5, "history": [0.2, 0.35, 0.48, 0.55, 0.62]},
    {"student_id": "student-02", "skill_id": "maths-a", "estimate": 0.91,
     "evidence_count": 6, "history": [0.5, 0.6, 0.7, 0.8, 0.86, 0.91]},
]
RECOMMENDATIONS = [
    {"id": "r1", "student_id": "student-01", "status": "approved", "audience": "family",
     "title": "Fraction strips at the kitchen table", "why": "Connects pictures to numbers.",
     "minutes": 15, "approved_by": "Ms. Rivera", "approved_on": "2026-09-15"},
    {"id": "r2", "student_id": "student-01", "status": "draft", "audience": "family",
     "title": "A draft nobody approved", "why": "", "minutes": 10,
     "approved_by": "", "approved_on": ""},
    {"id": "r3", "student_id": "student-01", "status": "approved", "audience": "teacher",
     "title": "A teacher-only note", "why": "", "minutes": 5,
     "approved_by": "Ms. Rivera", "approved_on": "2026-09-15"},
    {"id": "r4", "student_id": "student-02", "status": "approved", "audience": "family",
     "title": "Another family's next step", "why": "", "minutes": 10,
     "approved_by": "Ms. Rivera", "approved_on": "2026-09-15"},
]

FIXTURE = {
    "students": STUDENTS, "skills": SKILLS, "items": ITEMS, "attempts": ATTEMPTS,
    "mastery": MASTERY, "recommendations": RECOMMENDATIONS,
    "links": [{"parent_id": "parent-01", "student_id": "student-01"},
              {"parent_id": "parent-02", "student_id": "student-02"}],
    "parents": [{"id": "parent-01", "display_name": "Jordan Bell"},
                {"id": "parent-02", "display_name": "Priya Raman"}],
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(store, "read", lambda name: FIXTURE.get(name, []))
    return TestClient(app)


def report(client, headers=PARENT, student="student-01"):
    return client.get(f"/parent/children/{student}/report", headers=headers)


def test_a_parent_can_export_their_own_child(client):
    body = report(client).json()
    assert body["child"]["name"] == "Sam"
    assert body["skills"] and body["skills"][0]["skill"] == "Equivalent fractions"
    assert body["practice"]["questions_answered"] == 5


def test_the_disclaimer_always_travels_with_it(client):
    body = report(client).json()
    text = body["what_this_is_not"].lower()
    for phrase in ("not a medical", "diagnosis", "eligibility", "placement"):
        assert phrase in text


def test_nobody_else_can_pull_this_childs_summary(client):
    assert report(client, OTHER_PARENT).status_code == 403
    assert report(client, TEACHER).status_code == 403
    assert report(client, STUDENT).status_code == 403


def test_a_parent_cannot_reach_another_familys_child(client):
    assert report(client, PARENT, "student-02").status_code == 403


def test_no_other_child_and_no_comparison_leaks_in(client):
    blob = str(report(client).json())
    assert "Ava" not in blob and "student-02" not in blob
    # No ranking or averaging vocabulary: a comparison is not this family's to share.
    for word in ("rank", "percentile", "class average", "compared"):
        assert word not in blob.lower()


def test_only_teacher_approved_family_steps_are_included(client):
    titles = [n["title"] for n in report(client).json()["teacher_approved_next_steps"]]
    assert titles == ["Fraction strips at the kitchen table"]


def test_teacher_only_fields_stay_behind(client):
    blob = str(report(client).json())
    # The goal-link marker is a teacher-side field (PRD §6) and must not ride along.
    assert "has_goal_link" not in blob and "goal_link" not in blob


def test_direction_is_words_not_a_slope(client):
    row = report(client).json()["skills"][0]
    assert row["direction"] in ("moving up", "moving down", "holding steady",
                               "not enough history yet")
