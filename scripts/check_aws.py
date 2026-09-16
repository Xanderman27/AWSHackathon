#!/usr/bin/env python3
"""Pre-flight for the Bedrock path. Run it the moment credentials land.

    services/api/.venv/bin/python scripts/check_aws.py

It answers the three questions that decide whether the live path works on stage: are we
authenticated, which Claude model will this account actually let us call, and does a real
Converse response parse the way the pipeline expects. It never prints a secret.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

OK, BAD, MEH = "  ok  ", " FAIL ", " ---- "


def line(mark: str, text: str) -> None:
    print(f"[{mark}] {text}")


def main() -> int:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        line(BAD, "boto3 is not installed. pip install -r services/api/requirements.txt")
        return 1

    from app.ai import generate
    from app.ai.config import settings
    from app.ai.schema import TOOL_NAME

    region = os.getenv("AWS_REGION", "us-east-1")
    print(f"\nRegion: {region}\n")

    # 1. Authenticated?
    try:
        who = boto3.client("sts", region_name=region).get_caller_identity()
        line(OK, f"Authenticated as …{who['Arn'][-40:]}")
    except (ClientError, BotoCoreError) as problem:
        line(BAD, f"No usable credentials: {type(problem).__name__}")
        print("\n  export AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN / AWS_REGION")
        return 1

    # 2. Which Anthropic models does this account expose? (No AWS CLI needed.)
    ids: list[str] = []
    try:
        listed = boto3.client("bedrock", region_name=region).list_foundation_models()
        ids = [m["modelId"] for m in listed["modelSummaries"] if "anthropic" in m["modelId"]]
        if ids:
            line(OK, f"{len(ids)} Anthropic model(s) visible")
            for model_id in ids[:12]:
                print(f"         {model_id}")
        else:
            line(BAD, "No Anthropic models visible. Request model access in the Bedrock console.")
    except (ClientError, BotoCoreError) as problem:
        line(MEH, f"Could not list models ({type(problem).__name__}); the account may still allow invoke.")

    configured = settings().model_id
    if ids and configured not in ids:
        line(MEH, f"BEDROCK_MODEL_ID={configured} is not in that list.")
        print("         If invoke fails below, export one of the ids above (or its us. inference profile).")
    else:
        line(OK, f"BEDROCK_MODEL_ID={configured}")

    if settings().offline:
        line(MEH, "DEMO_OFFLINE is on, so the app is still serving cached drafts.")
        print("         export DEMO_OFFLINE=0 to go live.")

    # 3. Does a real call come back in the shape the pipeline parses?
    print()
    sources = generate.gather("fraction_equivalence", "Equivalent fractions", "building")
    summary = generate.summarise("building", 5, 0.2, "Equivalent fractions")
    try:
        response = generate._call_bedrock(summary, sources)
    except Exception as problem:  # noqa: BLE001 - we want the reason on screen
        line(BAD, f"Converse failed: {type(problem).__name__}: {problem}")
        print("\n  AccessDenied  -> model access not granted for this id")
        print("  Validation    -> wrong model id, or try the us. inference profile")
        print("  Throttling    -> quota; retry, or use a smaller model")
        print("\n  The app keeps working: it falls back to cached drafts and says so on screen.")
        return 1

    payload = generate._tool_input(response)
    if payload is None:
        line(BAD, f"The response carried no {TOOL_NAME} tool call.")
        print(f"         Top-level keys: {sorted(response.keys())}")
        return 1
    line(OK, f"Converse returned a {TOOL_NAME} tool call")

    from app.ai.schema import ActivityDraft
    try:
        draft = ActivityDraft.model_validate(payload)
    except Exception as problem:  # noqa: BLE001
        line(BAD, f"The draft did not match ActivityDraft: {problem}")
        return 1
    line(OK, f"Validated: {draft.title!r} ({draft.minutes} min, cites {draft.citations})")

    allowed = {s.id for s in sources}
    invented = [c for c in draft.citations if c not in allowed]
    line(OK if not invented else MEH,
         "All citations are real approved sources" if not invented else f"Invented ids (stripped at runtime): {invented}")

    usage = response.get("usage", {})
    if usage:
        line(OK, f"Tokens in/out: {usage.get('inputTokens')}/{usage.get('outputTokens')}")
    if settings().guardrail:
        line(OK, f"Guardrail attached: {settings().guardrail['guardrailIdentifier']}")
    else:
        line(MEH, "No guardrail configured (export BEDROCK_GUARDRAIL_ID to attach one).")

    print("\nLive path verified. Set DEMO_OFFLINE=0 and drafts will come from Bedrock.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
