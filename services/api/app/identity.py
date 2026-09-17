"""Who the caller is, proved rather than asserted (PRD FR-26).

Until now the API believed the X-Role and X-User-Id headers the client sent, which meant
anyone who could type a header was a teacher and could read any learner's IEP. This module
replaces that with a signed token: the caller presents one, we verify the signature, and the
role and user id come out of the verified claims. A caller cannot choose who they are.

Two issuers, one verification path:

  * Amazon Cognito, whenever a user pool is configured. Tokens are RS256, signed by the pool
    and checked against its published JWKS.
  * A local issuer, when no pool is configured — a laptop with no AWS, and the test suite.
    Tokens are HS256 signed with a per-process secret.

The local issuer is not a bypass. It mints and verifies real tokens, so an unauthenticated
request is rejected in every mode and the tests exercise the same code the deployment runs.
The two modes are mutually exclusive by construction: `_verify_cognito` only accepts RS256
and only when a pool is configured, `_verify_local` only accepts HS256 and only when one is
not, so a token from one issuer can never be validated by the other.
"""

from __future__ import annotations

import os
import secrets
import threading
import time
from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient

# How long a locally issued token lasts. Cognito controls its own lifetimes.
LOCAL_TTL_SECONDS = 12 * 60 * 60

ROLES = ("student", "teacher", "parent")

PARAM_PREFIX = "/dori/cognito"


@dataclass(frozen=True)
class Principal:
    """A caller whose identity has been verified."""

    role: str
    user_id: str
    display_name: str = ""


@dataclass(frozen=True)
class AuthSettings:
    region: str
    user_pool_id: str | None
    client_id: str | None

    @property
    def configured(self) -> bool:
        return bool(self.user_pool_id and self.client_id)

    @property
    def issuer(self) -> str:
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _parameters() -> dict[str, str]:
    """Pool and client ids from Parameter Store, matching how the Bedrock ids are resolved.

    Absent or unreadable leaves the explicit environment variables in charge, so a laptop
    with no AWS falls through to the local issuer rather than failing to start.
    """
    try:
        import boto3

        page = boto3.client("ssm", region_name=os.getenv("AWS_REGION", "us-east-1")) \
            .get_parameters_by_path(Path=PARAM_PREFIX)
        return {p["Name"].rsplit("/", 1)[-1]: p["Value"] for p in page.get("Parameters", [])}
    except Exception:
        return {}


def _setting(env_name: str, param_name: str) -> str | None:
    return os.getenv(env_name) or _parameters().get(param_name) or None


@lru_cache(maxsize=1)
def auth_settings() -> AuthSettings:
    return AuthSettings(
        region=os.getenv("AWS_REGION", "us-east-1"),
        user_pool_id=_setting("COGNITO_USER_POOL_ID", "user_pool_id"),
        client_id=_setting("COGNITO_CLIENT_ID", "client_id"),
    )


# ---------------------------------------------------------------------------------------
# Cognito

_jwk_lock = threading.Lock()
_jwk_client: PyJWKClient | None = None


def _jwks() -> PyJWKClient:
    """One JWKS client for the process. It caches keys and refetches when a kid is unknown,
    which is what makes key rotation a non-event."""
    global _jwk_client
    with _jwk_lock:
        if _jwk_client is None:
            _jwk_client = PyJWKClient(auth_settings().jwks_url, cache_keys=True)
        return _jwk_client


def _verify_cognito(token: str) -> dict:
    conf = auth_settings()
    key = _jwks().get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token,
        key,
        # An explicit single algorithm. Without this a token could name its own, which is how
        # "alg: none" and RS256-verified-as-HS256 forgeries get in.
        algorithms=["RS256"],
        issuer=conf.issuer,
        audience=conf.client_id,
        options={"require": ["exp", "iss", "aud", "sub"], "verify_exp": True,
                 "verify_iss": True, "verify_aud": True, "verify_signature": True},
    )
    # An access token carries no audience and must not be accepted where an id token is
    # expected; checking token_use explicitly keeps the two from being interchangeable.
    if claims.get("token_use") != "id":
        raise jwt.InvalidTokenError("not an id token")
    return claims


# ---------------------------------------------------------------------------------------
# Local issuer, for a laptop with no AWS and for the tests

def _local_secret() -> str:
    """A per-process secret unless one is supplied. Random by default so that nothing signed
    by a previous run — or by anyone else — verifies here."""
    existing = os.getenv("DORI_DEV_AUTH_SECRET")
    if existing:
        return existing
    global _generated_secret
    if _generated_secret is None:
        _generated_secret = secrets.token_hex(32)
    return _generated_secret


_generated_secret: str | None = None

LOCAL_ISSUER = "dori-local"


def issue_local_token(principal: Principal) -> tuple[str, int]:
    """Mint a token for a caller the login route has already authenticated."""
    expires_in = LOCAL_TTL_SECONDS
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": LOCAL_ISSUER,
            "sub": principal.user_id,
            "custom:user_id": principal.user_id,
            "cognito:groups": [principal.role],
            "name": principal.display_name,
            "token_use": "id",
            "iat": now,
            "exp": now + expires_in,
        },
        _local_secret(),
        algorithm="HS256",
    )
    return token, expires_in


def _verify_local(token: str) -> dict:
    return jwt.decode(
        token,
        _local_secret(),
        algorithms=["HS256"],
        issuer=LOCAL_ISSUER,
        options={"require": ["exp", "iss", "sub"], "verify_exp": True,
                 "verify_iss": True, "verify_signature": True},
    )


# ---------------------------------------------------------------------------------------

class InvalidToken(Exception):
    """The token was missing, expired, tampered with, or issued by someone else."""


def principal_from_token(token: str) -> Principal:
    """Verify a token and return who it says the caller is. Raises InvalidToken otherwise.

    Every failure path raises the same exception with no detail, because the difference
    between "expired", "wrong signature" and "unknown user" is information a caller probing
    the endpoint would like to have and has no legitimate use for.
    """
    if not token:
        raise InvalidToken()
    try:
        claims = _verify_cognito(token) if auth_settings().configured else _verify_local(token)
    except Exception as exc:  # noqa: BLE001 - every verification failure is the same answer
        raise InvalidToken() from exc

    groups = claims.get("cognito:groups") or []
    role = next((g for g in groups if g in ROLES), None)
    # The internal id is a custom attribute rather than the Cognito sub, so that seeded demo
    # learners keep the ids the rest of the data is keyed by (student-01 and friends).
    user_id = claims.get("custom:user_id") or claims.get("sub")
    if role is None or not user_id:
        # A user with no role group is authenticated but has no place in the product yet.
        raise InvalidToken()
    return Principal(role=role, user_id=str(user_id), display_name=str(claims.get("name") or ""))
