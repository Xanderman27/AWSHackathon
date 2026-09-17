"""Where the AWS settings come from, and the one switch that decides live or cached.

`DEMO_OFFLINE=1` makes the recommendation pipeline return cached drafts instead of calling
Bedrock. It is the default whenever no credentials are present, so the app runs — and the
demo works — on a laptop with no AWS at all. Setting it to 0 with credentials in place is the
only thing standing between this code and a live Converse call.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    region: str
    # Confirm the exact id your account exposes with `aws bedrock list-foundation-models`;
    # Workshop Studio accounts differ, which is why this is configuration and not a constant.
    model_id: str
    guardrail_id: str | None
    guardrail_version: str
    offline: bool
    max_tokens: int = 1400
    temperature: float = 0.2
    # A second guardrail for teacher-facing analysis. Comparing learners is the point of a
    # grouping explanation and forbidden in family text, so one policy cannot serve both.
    # Optional: with none set, teacher text falls back to the stricter family guardrail.
    teacher_guardrail_id: str | None = None
    teacher_guardrail_version: str = "DRAFT"

    @property
    def guardrail(self) -> dict | None:
        if not self.guardrail_id:
            return None
        return {"guardrailIdentifier": self.guardrail_id, "guardrailVersion": self.guardrail_version}

    @property
    def teacher_guardrail(self) -> dict | None:
        """Falls back to the family guardrail rather than to nothing, so a missing setting
        makes the product stricter, never looser."""
        if self.teacher_guardrail_id:
            return {"guardrailIdentifier": self.teacher_guardrail_id,
                    "guardrailVersion": self.teacher_guardrail_version}
        return self.guardrail


def _credentials_present() -> bool:
    """Ask boto3 rather than guessing.

    Checking for AWS_ACCESS_KEY_ID or ~/.aws misses the case that matters most in production:
    an EC2 instance profile or ECS task role, where credentials arrive over the instance
    metadata service and no key or file exists anywhere. boto3's own resolver covers every
    source, including those.
    """
    try:
        import boto3
        return boto3.Session().get_credentials() is not None
    except Exception:
        return False


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings(
        region=os.getenv("AWS_REGION", "us-east-1"),
        model_id=os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"),
        guardrail_id=os.getenv("BEDROCK_GUARDRAIL_ID") or None,
        guardrail_version=os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
        teacher_guardrail_id=os.getenv("BEDROCK_TEACHER_GUARDRAIL_ID") or None,
        teacher_guardrail_version=os.getenv("BEDROCK_TEACHER_GUARDRAIL_VERSION", "DRAFT"),
        # No credentials means offline, whatever the flag says: a failed Converse call on
        # stage is worse than an honest cached draft.
        offline=_flag("DEMO_OFFLINE", default=True) or not _credentials_present(),
    )


def status() -> dict:
    """What the teacher screen shows about where a draft came from."""
    current = settings()
    return {
        "offline": current.offline,
        "model_id": None if current.offline else current.model_id,
        "region": None if current.offline else current.region,
        "guardrail": bool(current.guardrail) and not current.offline,
        "teacher_guardrail": bool(current.teacher_guardrail) and not current.offline,
    }
