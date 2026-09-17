# Going live on AWS

The grounded recommendation pipeline is built and tested. It runs today with no AWS at all,
returning cached drafts. This is what it takes to make it call Bedrock for real.

## What exists now

```
corpus/manifest.json          11 approved sources, each with tier, citation, reviewer, date
services/api/app/ai/
  config.py                   settings + the DEMO_OFFLINE switch
  retrieval.py                local index with metadata filters + the ingestion gate
  schema.py                   ActivityDraft — the tool definition AND the validator
  generate.py                 summarise → retrieve → fill → validate → verify → present
  cached.py                   frozen pipeline outputs, used offline and as the fallback
app/routers/recommendations.py   draft → teacher decision → the family's next steps
```

`DEMO_OFFLINE` defaults to **on**, and stays on regardless if no credentials are present: a
failed Converse call on stage is worse than an honest cached draft.

## Step 1 — credentials

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...        # Workshop Studio issues short-lived keys
export AWS_REGION=us-east-1
```

## Step 2 — run the pre-flight

```bash
services/api/.venv/bin/python scripts/check_aws.py
```

One command answers all three questions that decide whether the live path works on stage:
are we authenticated, which Claude models this account actually exposes, and whether a real
Converse response parses the way the pipeline expects. No AWS CLI needed — boto3 lists the
models. It never prints a secret, and it names the fix for each failure.

Workshop Studio accounts differ, which is why the model id is configuration and not a
constant. If the pre-flight lists an id other than the default:

```bash
export BEDROCK_MODEL_ID=<the id it listed>     # use the us.… inference profile if there is one
```

## What this Workshop Studio account actually allows (verified 2026-09-16)

`list_foundation_models` shows 13 Anthropic models, but an IAM policy named
`ws-deny-bedrock-models-policy-1` explicitly denies most of them. Probing every id, only two
are invokable, and **only through the cross-region inference profile** (`us.` prefix — the
bare id is denied):

| Model id to use | |
|---|---|
| `us.anthropic.claude-sonnet-4-6` | the default; fast, ample for a constrained tool call |
| `us.anthropic.claude-opus-4-6-v1` | fallback if Sonnet is throttled |

Everything else, including `anthropic.claude-sonnet-5` and `anthropic.claude-opus-5`, is
listed but denied. If a teammate sees `AccessDeniedException` naming that policy, this is why:
they are on a bare model id or a denied model, not missing credentials.

Verified end to end: a live Converse call returns a `submit_activity` tool call, validates
into `ActivityDraft`, and cites only approved sources (~1800 in / ~490 out tokens per draft).

## Step 3 — turn it on

Only once the pre-flight is green:

```bash
export DEMO_OFFLINE=0
```

Draft an activity from any learner's page. The badge flips from *Cached drafts · Bedrock not
connected* to *Live · &lt;model id&gt;*, and the pipeline path on each draft changes from
`cached_draft` to `fill_template → verify_grounding → present`.

If Bedrock throttles, denies, or times out, the pipeline falls back to a cached draft, says
so on screen, and records `bedrock_error` in the path. Nothing on stage breaks.

## Step 4 — Guardrail

```bash
services/api/.venv/bin/python scripts/provision_guardrail.py
```

Creates `dori-guardrail` and prints the id and version to export. It is attached to every
Converse call automatically, shown in the status badge, and the pre-flight proves it both
blocks and permits rather than only checking it is attached.

The prompt already forbids these things; the guardrail is the version that does not depend on
the model choosing to comply, and it runs on the way in as well as the way out — so a prompt
injection hidden in a corpus document is filtered too.

| Denied topic | Why |
|---|---|
| Diagnosis | The product must not identify or suggest a disability (PRD §4 non-goals) |
| Eligibility and placement | Not its decision to make, ever |
| Medication and clinical advice | Out of scope, and dangerous to get wrong |
| Ranking children | "No child is compared publicly with classmates" (PRD §4) |

Plus content filters at HIGH for sexual, violence, hate, insults and misconduct, prompt-attack
detection on input, and PII rules that block contact details and anonymise addresses. `NAME` is
deliberately left alone: the drafts say "your child", and blocking names trips on ordinary words.

Verified behaviour (`apply_guardrail`, INPUT):

```
diagnosis   GUARDRAIL_INTERVENED  ['Eligibility and placement', 'Diagnosis']
placement   GUARDRAIL_INTERVENED  ['Eligibility and placement', 'Diagnosis']
medication  GUARDRAIL_INTERVENED  ['Medication and clinical advice', 'Diagnosis']
ranking     GUARDRAIL_INTERVENED  ['Ranking children', ...]
legitimate  NONE                  []
```

## What we send, and what we never send

The user message is a pseudonymous summary plus the retrieved sources. There is no name, no
id, no grade, no class, no photo, no goal link and no plan in it — not filtered out, simply
never assembled. `test_nothing_identifying_reaches_the_model` asserts this against the real
request payload rather than by reading the code.

## Still not AWS

| Piece | Status |
|---|---|
| Bedrock Converse + tool use | **built**, offline by default |
| Guardrails | **built**, needs an id |
| Knowledge Bases | local index behind the same interface; swap `retrieval.retrieve` |
| Polly read-aloud | not started; browser speech is the stand-in |
| S3 for class photos | local disk today; `store.upload_path` is the seam |
| DynamoDB | local JSON today; `LocalStore` is the seam |
| Cognito | header auth today; would rework the sign-up flow |
| AgentCore | `generate.propose` is the graph, written as functions |
