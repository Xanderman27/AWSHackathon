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

## Step 4 — Guardrails (optional, ~10 minutes)

Create a guardrail with denied topics for diagnosis, eligibility, placement and medication,
plus the PII filter, then:

```bash
export BEDROCK_GUARDRAIL_ID=...
export BEDROCK_GUARDRAIL_VERSION=1
```

It is attached to every Converse call automatically and shown in the status badge.

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
