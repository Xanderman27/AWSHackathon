"""Authorization headers for the tests.

The API no longer takes the caller's word for who they are, so a test cannot just assert a
role in a header. It mints a real token from the local issuer — the same one a laptop with no
AWS uses — and sends it the same way a browser would. Tests therefore exercise the actual
verification path rather than a bypass around it.
"""

from __future__ import annotations

from app.identity import Principal, issue_local_token


def auth(role: str, user_id: str, name: str = "") -> dict[str, str]:
    token, _ = issue_local_token(Principal(role=role, user_id=user_id, display_name=name))
    return {"Authorization": f"Bearer {token}"}
