"""Demo sign-in and sign-up with synthetic accounts (PRD FR-01).

Seeded demo logins keep their plaintext passwords so judges can read them off the screen.
Anything a real person types at sign-up is salted and hashed with PBKDF2 instead — a password
someone chose is theirs, not demo data. Amazon Cognito replaces the whole file in production
(PRD FR-26); nothing else in the API trusts this endpoint, because authorization still
happens per-request in the data layer.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from .. import classcode
from ..models import now
from ..storage import store

router = APIRouter(prefix="/auth", tags=["auth"])

PBKDF2_ROUNDS = 240_000


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


def _session(account: dict) -> dict:
    return {"role": account["role"], "user_id": account["user_id"],
            "display_name": account["display_name"]}


@router.post("/login")
def login(body: LoginIn):
    username = body.username.strip().lower()
    for acct in store.read("accounts"):
        if acct["username"] == username and check_password(acct["password"], body.password):
            store.append("audit", {"actor": acct["user_id"], "action": "auth.login",
                                   "object_id": acct["username"], "at": now()})
            return _session(acct)
    raise HTTPException(401, "That username or password does not match.")


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
    if any(acct["username"] == username for acct in store.read("accounts")):
        raise HTTPException(409, "There is already an account for that email. Try logging in.")

    parent_id = f"parent-{uuid4().hex[:8]}"
    store.append("parents", {
        "id": parent_id,
        "display_name": body.name.strip(),
        "email": username,
        # Which classroom they joined. It becomes a child link only once they choose one.
        "pending_class_id": klass["id"],
        "created_at": now(),
    })
    store.append("accounts", {
        "username": username,
        "password": hash_password(body.password),
        "role": "parent",
        "user_id": parent_id,
        "display_name": body.name.strip(),
    })
    store.append("audit", {"actor": parent_id, "action": "auth.signup",
                           "object_id": klass["id"], "at": now()})
    return {"role": "parent", "user_id": parent_id, "display_name": body.name.strip(),
            "class_name": klass["name"], "needs_child": True}
