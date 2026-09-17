"""The calls this API makes to Amazon Cognito on a caller's behalf (PRD FR-26).

The browser never talks to Cognito. It posts a username and password to our own sign-in
route over TLS, exactly as it did before, and this module exchanges those for tokens with
`AdminInitiateAuth`. That keeps the designed sign-up dialog and adds no AWS SDK to a frontend
that carries only React and the router.

The admin flow is the right one here precisely because it is not usable from a browser: it is
authorised by the instance's IAM role, so the app client needs no client secret that a
frontend would have to hold. Passwords pass through this process and are never stored by it —
the account record we keep has no password column at all any more.
"""

from __future__ import annotations

import os
from functools import lru_cache

from .identity import auth_settings


class CognitoError(Exception):
    """A call to Cognito failed in a way the caller should hear about."""


class BadCredentials(CognitoError):
    pass


class UserExists(CognitoError):
    pass


@lru_cache(maxsize=1)
def _client():
    import boto3

    return boto3.client("cognito-idp", region_name=os.getenv("AWS_REGION", "us-east-1"))


def configured() -> bool:
    return auth_settings().configured


def authenticate(username: str, password: str) -> dict:
    """Exchange a username and password for tokens. Raises BadCredentials on refusal."""
    conf = auth_settings()
    client = _client()
    try:
        result = client.admin_initiate_auth(
            UserPoolId=conf.user_pool_id,
            ClientId=conf.client_id,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
    except client.exceptions.NotAuthorizedException as exc:
        raise BadCredentials() from exc
    except client.exceptions.UserNotFoundException as exc:
        # Same answer as a wrong password: whether an account exists is not something an
        # unauthenticated caller gets to enumerate.
        raise BadCredentials() from exc
    except Exception as exc:  # noqa: BLE001
        raise CognitoError(str(exc)) from exc

    auth = result.get("AuthenticationResult")
    if not auth:
        # A challenge (new password required, MFA). No demo account should ever be in this
        # state, and answering challenges is not something this route does.
        raise CognitoError("this account needs attention in Cognito before it can sign in")
    return {
        "id_token": auth["IdToken"],
        "refresh_token": auth.get("RefreshToken"),
        "expires_in": auth.get("ExpiresIn", 3600),
    }


def refresh(refresh_token: str) -> dict:
    conf = auth_settings()
    client = _client()
    try:
        result = client.admin_initiate_auth(
            UserPoolId=conf.user_pool_id,
            ClientId=conf.client_id,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh_token},
        )
    except Exception as exc:  # noqa: BLE001
        raise BadCredentials() from exc
    auth = result.get("AuthenticationResult") or {}
    if "IdToken" not in auth:
        raise BadCredentials()
    return {"id_token": auth["IdToken"], "expires_in": auth.get("ExpiresIn", 3600)}


def create_user(*, username: str, password: str, role: str, user_id: str, name: str) -> None:
    """Create a confirmed user carrying the role group and our internal id.

    `custom:user_id` is what the rest of the data is keyed by. It is set here, by the server,
    and is not writable by the user — the pool's schema marks it read-only for the app client,
    so nobody can sign up and nominate themselves somebody else's learner id.
    """
    conf = auth_settings()
    client = _client()
    try:
        client.admin_create_user(
            UserPoolId=conf.user_pool_id,
            Username=username,
            MessageAction="SUPPRESS",  # no invitation mail; we sign them straight in
            UserAttributes=[
                {"Name": "email", "Value": username},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "name", "Value": name},
                {"Name": "custom:user_id", "Value": user_id},
            ],
        )
    except client.exceptions.UsernameExistsException as exc:
        raise UserExists() from exc
    except Exception as exc:  # noqa: BLE001
        raise CognitoError(str(exc)) from exc

    # Permanent, so the account is usable immediately rather than landing in FORCE_CHANGE.
    client.admin_set_user_password(
        UserPoolId=conf.user_pool_id, Username=username, Password=password, Permanent=True,
    )
    client.admin_add_user_to_group(
        UserPoolId=conf.user_pool_id, Username=username, GroupName=role,
    )
