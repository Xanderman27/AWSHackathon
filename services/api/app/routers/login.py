"""Demo sign-in with synthetic accounts (PRD FR-01).

Students use the login their teacher set for them; teachers and parents have their own.
This is a hackathon stand-in: plaintext demo credentials in seed data, no tokens. Amazon
Cognito replaces it in production (PRD FR-26), and nothing else in the API trusts this
endpoint — authorization still happens per-request in the data layer.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models import now
from ..storage import store

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=120)


@router.post("/login")
def login(body: LoginIn):
    username = body.username.strip().lower()
    for acct in store.read("accounts"):
        if acct["username"] == username and acct["password"] == body.password:
            store.append("audit", {"actor": acct["user_id"], "action": "auth.login",
                                   "object_id": acct["username"], "at": now()})
            return {"role": acct["role"], "user_id": acct["user_id"], "display_name": acct["display_name"]}
    raise HTTPException(401, "That username or password does not match.")
