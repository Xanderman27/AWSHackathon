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
    # For the plan-drafting surface: diagnosis and medication stay denied, but proposing a
    # support for the team to consider is allowed - that is the surface's purpose.
    plan_guardrail_id: str | None = None
    plan_guardrail_version: str = "DRAFT"

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

    @property
    def plan_guardrail(self) -> dict | None:
        """No fallback to the other two on purpose: both deny 'recommending accommodations
        or IEP content', which is this surface's entire job. Unset means unguarded drafting
        behind the system rules, citation verification and the human adoption step."""
        if self.plan_guardrail_id:
            return {"guardrailIdentifier": self.plan_guardrail_id,
                    "guardrailVersion": self.plan_guardrail_version}
        return None


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


PARAM_PREFIX = "/dori/bedrock"


@lru_cache(maxsize=1)
def _parameters() -> dict[str, str]:
    """Guardrail ids from Parameter Store, so rotating one needs no config change anywhere.

    Read once at startup. If the parameters are absent or unreadable this returns nothing and
    the explicit environment variables take over, so a laptop with no AWS is unaffected.
    """
    try:
        import boto3
        page = boto3.client("ssm", region_name=os.getenv("AWS_REGION", "us-east-1")) \
            .get_parameters_by_path(Path=PARAM_PREFIX)
        return {p["Name"].rsplit("/", 1)[-1]: p["Value"] for p in page.get("Parameters", [])}
    except Exception:
        return {}


def _setting(env_name: str, param_name: str, default: str | None = None) -> str | None:
    """An explicit environment variable always wins; Parameter Store is the fallback."""
    return os.getenv(env_name) or _parameters().get(param_name) or default


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings(
        region=os.getenv("AWS_REGION", "us-east-1"),
        model_id=os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"),
        guardrail_id=_setting("BEDROCK_GUARDRAIL_ID", "guardrail_id"),
        guardrail_version=_setting("BEDROCK_GUARDRAIL_VERSION", "guardrail_version", "DRAFT"),
        teacher_guardrail_id=_setting("BEDROCK_TEACHER_GUARDRAIL_ID", "teacher_guardrail_id"),
        teacher_guardrail_version=_setting(
            "BEDROCK_TEACHER_GUARDRAIL_VERSION", "teacher_guardrail_version", "DRAFT"),
        plan_guardrail_id=_setting("BEDROCK_PLAN_GUARDRAIL_ID", "plan_guardrail_id"),
        plan_guardrail_version=_setting(
            "BEDROCK_PLAN_GUARDRAIL_VERSION", "plan_guardrail_version", "DRAFT"),
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
        "guardrail_version": current.guardrail_version if current.guardrail else None,
    }
