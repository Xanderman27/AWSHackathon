"""What a caller cannot do (PRD FR-26).

Before this, the API believed the X-Role and X-User-Id headers a client sent, so two headers
anyone could type returned a learner's full IEP — eligibility, present levels, accommodations,
services, guardians — from the public internet with no credentials at all. These tests exist
so that hole cannot reopen quietly. Most of them assert a refusal rather than a feature, which
is the point: the interesting behaviour of an authorization layer is what it says no to.
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app import identity
from app.identity import InvalidToken, Principal, issue_local_token, principal_from_token
from app.main import app
from authhelp import auth

# The route that reads a support plan. If anything is going to be protected, it is this one.
PLAN = "/support/students/student-01"

client = TestClient(app)


# --------------------------------------------------------------------------- the old hole

def test_the_old_identity_headers_grant_nothing():
    """The exact request that used to return a full IEP over the public internet."""
    res = client.get(PLAN, headers={"X-Role": "teacher", "X-User-Id": "teacher-01"})
    assert res.status_code == 401


def test_no_credentials_at_all_is_refused():
    assert client.get(PLAN).status_code == 401


def test_a_teacher_token_still_reaches_the_plan():
    """The counterpart: the lock is on, and the right key still opens it."""
    res = client.get(PLAN, headers=auth("teacher", "teacher-01"))
    assert res.status_code == 200
    assert "plan" in res.json()


# --------------------------------------------------------------------------- token forgery

def test_a_tampered_token_is_refused():
    token = issue_local_token(Principal(role="student", user_id="student-01"))[0]
    # Flip a character in the signature.
    head, payload, sig = token.split(".")
    forged = f"{head}.{payload}.{'a' if sig[0] != 'a' else 'b'}{sig[1:]}"
    assert client.get(PLAN, headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_a_token_signed_with_another_secret_is_refused():
    forged = jwt.encode(
        {"iss": identity.LOCAL_ISSUER, "sub": "teacher-01", "custom:user_id": "teacher-01",
         "cognito:groups": ["teacher"], "exp": int(time.time()) + 600},
        "not-our-secret", algorithm="HS256",
    )
    assert client.get(PLAN, headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_an_unsigned_token_is_refused():
    """`alg: none` is the oldest JWT trick there is."""
    forged = jwt.encode(
        {"iss": identity.LOCAL_ISSUER, "sub": "teacher-01", "custom:user_id": "teacher-01",
         "cognito:groups": ["teacher"], "exp": int(time.time()) + 600},
        key="", algorithm="none",
    )
    assert client.get(PLAN, headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_an_expired_token_is_refused():
    expired = jwt.encode(
        {"iss": identity.LOCAL_ISSUER, "sub": "student-01", "custom:user_id": "student-01",
         "cognito:groups": ["student"], "exp": int(time.time()) - 5},
        identity._local_secret(), algorithm="HS256",
    )
    assert client.get("/student/path",
                      headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_a_token_with_no_role_group_is_refused():
    """Authenticated is not the same as authorised. A user who is in no role group has no
    place in the product yet, and must not fall through to a default."""
    roleless = jwt.encode(
        {"iss": identity.LOCAL_ISSUER, "sub": "someone", "custom:user_id": "someone",
         "cognito:groups": [], "exp": int(time.time()) + 600},
        identity._local_secret(), algorithm="HS256",
    )
    with pytest.raises(InvalidToken):
        principal_from_token(roleless)


def test_a_role_the_product_does_not_have_is_refused():
    inflated = jwt.encode(
        {"iss": identity.LOCAL_ISSUER, "sub": "x", "custom:user_id": "x",
         "cognito:groups": ["admin", "superuser"], "exp": int(time.time()) + 600},
        identity._local_secret(), algorithm="HS256",
    )
    with pytest.raises(InvalidToken):
        principal_from_token(inflated)


def test_a_malformed_authorization_header_is_refused():
    for value in ("", "Bearer", "Bearer ", "Basic abc", "token abc"):
        assert client.get(PLAN, headers={"Authorization": value}).status_code == 401


# --------------------------------------------------------------------------- role and scope

def test_a_student_cannot_reach_a_teacher_route():
    assert client.get(PLAN, headers=auth("student", "student-01")).status_code in (401, 403)


def test_a_learner_cannot_read_another_learners_plan():
    """The scope check, not just the role check: student-02 holds a perfectly valid token
    and is still refused student-01's record."""
    assert client.get(PLAN, headers=auth("student", "student-02")).status_code == 403


def test_a_parent_sees_their_own_child_and_only_their_own():
    """Both halves, so this cannot pass because the endpoint is simply broken: a linked
    parent gets their child, and a parent with no link gets an empty list rather than the
    class roster."""
    linked = client.get("/parent/children", headers=auth("parent", "parent-01"))
    assert linked.status_code == 200
    mine = [child["id"] for child in linked.json()]
    assert mine, "the linked parent should see their child"

    stranger = client.get("/parent/children", headers=auth("parent", "parent-not-a-real-parent"))
    assert stranger.status_code == 200
    assert stranger.json() == []


def test_teacher_scope_comes_from_the_record_not_a_constant():
    """The class a teacher can see is read from their own row. Someone holding a teacher
    token for an id with no teacher record reaches nothing — it used to be hardcoded to
    class-4a, which would have handed them the whole class."""
    from app.auth import actor_for

    stranger = actor_for(Principal(role="teacher", user_id="teacher-does-not-exist"))
    assert stranger.class_ids == set()
    assert stranger.student_ids == set()

    real = actor_for(Principal(role="teacher", user_id="teacher-01"))
    assert real.class_ids and real.student_ids


# --------------------------------------------------------------------------- the socket

def test_the_activity_socket_refuses_an_unauthenticated_caller():
    with client.websocket_connect("/games/ws/activity/solo:memory-meadow?token=nonsense") as ws:
        assert ws.receive_json()["type"] == "error"


def test_the_socket_seats_the_token_holder_not_a_named_learner():
    """It used to take student_id off the query string, so a learner could sit down as
    anybody. The seat now comes from the token's claims, and a stray student_id is ignored."""
    token = auth("student", "student-01")["Authorization"].removeprefix("Bearer ")
    url = f"/games/ws/activity/solo:memory-meadow?token={token}&student_id=student-02"
    with client.websocket_connect(url) as ws:
        snapshot = ws.receive_json()
        seated = [p["id"] for p in snapshot["participants"]]
        assert seated == ["student-01"]


def test_a_teacher_token_cannot_join_a_learner_activity():
    token = auth("teacher", "teacher-01")["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(
        f"/games/ws/activity/solo:memory-meadow?token={token}") as ws:
        assert ws.receive_json()["type"] == "error"


# --------------------------------------------------------------------------- issuer hygiene

def test_local_and_cognito_tokens_cannot_be_swapped():
    """The two issuers must not validate each other's tokens. With a pool configured, a
    locally signed HS256 token is not acceptable — that would be an algorithm-confusion
    downgrade straight back to a forgeable token."""
    local = issue_local_token(Principal(role="teacher", user_id="teacher-01"))[0]
    settings = identity.auth_settings
    identity.auth_settings = lambda: identity.AuthSettings(
        region="us-east-1", user_pool_id="us-east-1_test", client_id="testclient")
    try:
        assert identity.auth_settings().configured
        with pytest.raises(InvalidToken):
            principal_from_token(local)
    finally:
        identity.auth_settings = settings
