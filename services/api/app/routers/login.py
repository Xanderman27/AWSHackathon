"""Sign-in and sign-up (PRD FR-01, FR-26).

Both routes end the same way: the caller gets a signed token, and every later request is
authorised by that token rather than by headers the caller writes. Where the token comes from
depends on the deployment — Amazon Cognito when a user pool is configured, the local issuer
on a laptop with no AWS — but the shape of the exchange, and the fact that there is one, does
not change between them.

Passwords are never stored by this service when Cognito is configured; the pool holds them.
The local issuer keeps the seeded demo logins in plaintext so judges can read them off the
screen, and salts and hashes with PBKDF2 anything a real person types, because a password
someone chose is theirs, not demo data.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from .. import classcode, cognito
from ..identity import InvalidToken, Principal, issue_local_token, principal_from_token
from ..models import now
from ..storage import store

router = APIRouter(prefix="/auth", tags=["auth"])

PBKDF2_ROUNDS = 240_000

BAD_LOGIN = "That username or password does not match."


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return f"pbkdf2${PBKDF2_ROUNDS}${salt}${digest.hex()}"


def check_password(stored: str, supplied: str) -> bool:
    if not stored.startswith("pbkdf2$"):
        # A seeded demo account. Constant-time all the same.
        return hmac.compare_digest(stored, supplied)
    _, rounds, salt, expected = stored.split("$", 3)
    digest = hashlib.pbkdf2_hmac("sha256", supplied.encode(), bytes.fromhex(salt), int(rounds))
    return hmac.compare_digest(digest.hex(), expected)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=120)


class SignUpIn(BaseModel):
    """What a family types on the landing page."""

    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    class_code: str = Field(min_length=1, max_length=40)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


def _session(principal: Principal, token: str, expires_in: int,
             refresh_token: str | None = None) -> dict:
    body = {
        "role": principal.role,
        "user_id": principal.user_id,
        "display_name": principal.display_name,
        "token": token,
        "expires_in": expires_in,
    }
    if refresh_token:
        body["refresh_token"] = refresh_token
    return body


def _local_login(username: str, password: str) -> dict:
    for acct in store.read("accounts"):
        if acct["username"] == username and check_password(acct["password"], password):
            principal = Principal(role=acct["role"], user_id=acct["user_id"],
                                  display_name=acct["display_name"])
            token, expires_in = issue_local_token(principal)
            store.append("audit", {"actor": acct["user_id"], "action": "auth.login",
                                   "object_id": acct["username"], "at": now()})
            return _session(principal, token, expires_in)
    raise HTTPException(401, BAD_LOGIN)


@router.post("/login")
def login(body: LoginIn):
    username = body.username.strip().lower()
    if not cognito.configured():
        return _local_login(username, body.password)

    try:
        tokens = cognito.authenticate(username, body.password)
    except cognito.BadCredentials:
        raise HTTPException(401, BAD_LOGIN) from None
    except cognito.CognitoError as exc:
        raise HTTPException(503, f"Sign-in is unavailable right now. {exc}") from None

    try:
        principal = principal_from_token(tokens["id_token"])
    except InvalidToken:
        # We just received this token from Cognito, so failing to verify it means the pool and
        # our configuration disagree. Refusing is the only safe answer.
        raise HTTPException(503, "Sign-in is misconfigured.") from None

    store.append("audit", {"actor": principal.user_id, "action": "auth.login",
                           "object_id": username, "at": now()})
    return _session(principal, tokens["id_token"], tokens["expires_in"],
                    tokens.get("refresh_token"))


@router.post("/refresh")
def refresh(body: RefreshIn):
    """Trade a refresh token for a fresh id token, so a long sitting stays signed in."""
    if not cognito.configured():
        # The local issuer has no refresh concept; its tokens simply last the session.
        raise HTTPException(400, "not available")
    try:
        tokens = cognito.refresh(body.refresh_token)
        principal = principal_from_token(tokens["id_token"])
    except (cognito.BadCredentials, InvalidToken):
        raise HTTPException(401, "Please sign in again.") from None
    return _session(principal, tokens["id_token"], tokens["expires_in"])


@router.post("/signup", status_code=201)
def signup(body: SignUpIn):
    """Create a family account and put it in the class the code belongs to.

    The code is the only thing that decides which class this family joins; a client cannot
    name a class directly. Linking to a particular child is a separate, authorised step
    (see routers/parent.py), because a class code says which classroom, never which child.
    """
    klass = classcode.find_class(body.class_code)
    if klass is None:
        raise HTTPException(404, "We could not find that class code. Check it with your teacher.")

    username = str(body.email).strip().lower()
    taken = any(acct["username"] == username for acct in store.read("accounts")) \
        or any(p.get("email") == username for p in store.read("parents"))
    if taken:
        raise HTTPException(409, "There is already an account for that email. Try logging in.")

    parent_id = f"parent-{uuid4().hex[:8]}"
    display_name = body.name.strip()

    if cognito.configured():
        try:
            cognito.create_user(username=username, password=body.password, role="parent",
                                user_id=parent_id, name=display_name)
        except cognito.UserExists:
            raise HTTPException(409, "There is already an account for that email. "
                                     "Try logging in.") from None
        except cognito.CognitoError as exc:
            raise HTTPException(503, f"We could not create that account. {exc}") from None
    else:
        store.append("accounts", {
            "username": username,
            "password": hash_password(body.password),
            "role": "parent",
            "user_id": parent_id,
            "display_name": display_name,
        })

    store.append("parents", {
        "id": parent_id,
        "display_name": display_name,
        "email": username,
        # Which classroom they joined. It becomes a child link only once they choose one.
        "pending_class_id": klass["id"],
        "created_at": now(),
    })
    store.append("audit", {"actor": parent_id, "action": "auth.signup",
                           "object_id": klass["id"], "at": now()})

    # Sign them straight in, so the flow continues into choosing their child.
    if cognito.configured():
        tokens = cognito.authenticate(username, body.password)
        principal = principal_from_token(tokens["id_token"])
        session = _session(principal, tokens["id_token"], tokens["expires_in"],
                           tokens.get("refresh_token"))
    else:
        principal = Principal(role="parent", user_id=parent_id, display_name=display_name)
        token, expires_in = issue_local_token(principal)
        session = _session(principal, token, expires_in)

    return {**session, "class_name": klass["name"], "needs_child": True}
