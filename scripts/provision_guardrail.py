#!/usr/bin/env python3
"""Create (or update) the Bedrock guardrail the recommendation pipeline runs behind.

    services/api/.venv/bin/python scripts/provision_guardrail.py

The prompt already forbids these things. A guardrail is the version of that which does not
depend on the model choosing to comply, and it is enforced on the way in as well as the way
out — so a prompt-injection attempt in a corpus document is filtered too.

What it denies is taken from the PRD's product boundaries (§16): this is a formative support
tool, so diagnosis, eligibility, placement and medication are out of scope by design, not by
politeness. It prints the id and version to export.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
NAME = "dori-guardrail"

# Each topic is something the product must never do (PRD §4 non-goals, §16 boundaries).
DENIED_TOPICS = [
    {
        "name": "Diagnosis",
        "definition": "Identifying, suggesting, confirming or ruling out a disability, "
                      "disorder, medical or psychological condition in a child.",
        "examples": [
            "Does this mean my child has dyslexia?",
            "These results suggest ADHD.",
            "This learner shows signs of a processing disorder.",
        ],
        "type": "DENY",
    },
    {
        "name": "Eligibility and placement",
        "definition": "Deciding or recommending special-education eligibility, placement, "
                      "services, accommodations, retention, or the content of an IEP or 504 plan.",
        "examples": [
            "This child should be moved to a smaller class.",
            "They qualify for special education services.",
            "Add extra time to the IEP.",
        ],
        "type": "DENY",
    },
    {
        "name": "Medication and clinical advice",
        "definition": "Any mention of medication, dosage, therapy, clinical treatment or "
                      "referral for a child.",
        "examples": [
            "Talk to your doctor about medication.",
            "You should see an occupational therapist.",
        ],
        "type": "DENY",
    },
    {
        "name": "Ranking children",
        "definition": "Comparing a child with classmates, ranking learners, or describing a "
                      "child as behind, low, slow, or incapable.",
        "examples": [
            "Your child is behind the rest of the class.",
            "She is one of the weakest readers in the group.",
        ],
        "type": "DENY",
    },
]

CONTENT_FILTERS = [
    {"type": t, "inputStrength": "HIGH", "outputStrength": "HIGH"}
    for t in ("SEXUAL", "VIOLENCE", "HATE", "INSULTS", "MISCONDUCT")
] + [
    # Prompt attacks are only assessed on input.
    {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"},
]

# A family activity never needs a real person's contact details. NAME is left alone: the
# drafts say "your child", and blocking names would trip on ordinary words.
PII_ENTITIES = [
    {"type": t, "action": "BLOCK"}
    for t in ("EMAIL", "PHONE", "US_SOCIAL_SECURITY_NUMBER", "CREDIT_DEBIT_CARD_NUMBER",
              "US_BANK_ACCOUNT_NUMBER", "PASSWORD", "AWS_SECRET_KEY")
] + [
    {"type": "ADDRESS", "action": "ANONYMIZE"},
]

BLOCKED_IN = ("That is outside what this tool does. It suggests short learning activities; "
              "it does not diagnose, decide services, or give clinical advice.")
BLOCKED_OUT = ("That draft was withheld because it strayed outside what this tool may say "
               "about a child. Try drafting again, or write the activity yourself.")


def find(client) -> dict | None:
    for item in client.list_guardrails().get("guardrails", []):
        if item["name"] == NAME:
            return item
    return None


def main() -> int:
    client = boto3.client("bedrock", region_name=REGION)
    config = dict(
        name=NAME,
        description="Dori: keeps generated family activities inside the product's boundaries.",
        topicPolicyConfig={"topicsConfig": DENIED_TOPICS},
        contentPolicyConfig={"filtersConfig": CONTENT_FILTERS},
        sensitiveInformationPolicyConfig={"piiEntitiesConfig": PII_ENTITIES},
        blockedInputMessaging=BLOCKED_IN,
        blockedOutputsMessaging=BLOCKED_OUT,
    )

    existing = find(client)
    try:
        if existing:
            client.update_guardrail(guardrailIdentifier=existing["id"], **config)
            guardrail_id = existing["id"]
            print(f"[updated] guardrail {NAME} ({guardrail_id})")
        else:
            made = client.create_guardrail(**config)
            guardrail_id = made["guardrailId"]
            print(f"[ made  ] guardrail {NAME} ({guardrail_id})")

        version = client.create_guardrail_version(
            guardrailIdentifier=guardrail_id,
            description="Provisioned by scripts/provision_guardrail.py",
        )["version"]
        print(f"[  ok   ] version {version}")
    except ClientError as problem:
        print(f"[ FAIL  ] {problem.response['Error']['Code']}: {problem.response['Error']['Message'][:220]}")
        return 1

    print(f"""
  {len(DENIED_TOPICS)} denied topics · {len(CONTENT_FILTERS)} content filters · {len(PII_ENTITIES)} PII rules

  export BEDROCK_GUARDRAIL_ID={guardrail_id}
  export BEDROCK_GUARDRAIL_VERSION={version}
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
