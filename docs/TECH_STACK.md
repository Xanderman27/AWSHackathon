# Tech stack

This document expands §17 of the PRD into concrete choices, versions, and the reason for each. It is the reference for anyone setting up a workstream.

## Summary

| Layer | Choice | Why |
|---|---|---|
| Front end | React 18, Vite, TypeScript, React Router, plain CSS with custom properties | Full control over focus, ARIA, and layout, which the accessibility promise depends on. Vite gives instant reloads for a two-day build. |
| API | Python 3.12, FastAPI, Pydantic v2, Uvicorn | Python keeps all AI work in one language. Pydantic models double as the JSON schemas the front end validates against. |
| Learner model | Pure Python module, no ML library | Bayesian Knowledge Tracing is four parameters and one update formula. Pure functions are testable and explainable to a teacher. |
| Cohorts | Pure Python module | Deterministic sort-and-cut with rotation penalties. Auditable, no clustering library. |
| Generative AI | Amazon Bedrock Converse API via `boto3`, Anthropic Claude model | Converse gives one interface across models, supports tool use for structured output, and integrates Guardrails in the same call. |
| Retrieval | Amazon Bedrock Knowledge Bases over S3, with a local fallback | Managed chunking, embedding, and metadata filtering. The fallback keeps the demo alive if provisioning stalls. |
| Guardrails | Amazon Bedrock Guardrails | PII filter, harmful content, prompt attack, denied topics (diagnosis, eligibility, placement, medication). |
| Read-aloud | Amazon Polly neural voice, pre-generated to S3 | Instant playback in the demo; no live synthesis latency on the student screen. |
| Translation (P1) | Amazon Translate | One API call for parent summaries; Bedrock can substitute. |
| Storage | Repository interface with two adapters: local JSON files for the demo, Amazon DynamoDB for deployment | The demo must reset in one command and run offline. DynamoDB is a swap, not a rewrite. |
| Auth (P1) | Amazon Cognito | Real role claims once the flow works. Until then, a header-based synthetic role switch. |
| Hosting | Local for the judged demo; AWS Amplify Hosting (front end) and AWS App Runner (API) if time allows | Reliability over cloud points. A recorded backup video is required either way. |
| Observability | Amazon CloudWatch via structured JSON logs | Audit events and model latency without extra infrastructure. |
| Delivery and config | Amazon CloudFront over S3; AWS Systems Manager Parameter Store | Instant audio playback; one source of truth for service IDs across four machines. |
| Corpus ingestion | Amazon Textract for district PDFs | Turns Tier 2 teaching guidelines into clean text for the knowledge base. |
| Testing | pytest for the API, Vitest for the front end, Playwright for one keyboard-only smoke test | The keyboard test is the accessibility acceptance criterion in code form. |

## Front end

- **React 18 + Vite + TypeScript.** Three role routes: `/student`, `/teacher`, `/parent`. Each route is a separate page tree so role-specific components never share state accidentally.
- **Styling.** Plain CSS with custom properties on `:root`. High contrast and type scaling are implemented by swapping a `data-theme` and `data-scale` attribute on `<html>`, which changes the variables. No component library, because most of them fight focus management and large targets.
- **Accessibility mechanics.** Native `<button>` and `<fieldset>` elements for answers, `aria-live` regions for feedback, a visible focus ring defined once, `prefers-reduced-motion` respected and also togglable. Audio uses a single `<audio>` element per screen with explicit play, pause, replay, and stop buttons.
- **State.** React Query for server data, `useReducer` for the quiz flow. No global store is needed at this size.
- **Charts (teacher and parent views).** Recharts, with numbers also rendered as text so nothing depends on color or a graphic.
- **Fallback.** If nobody on the team can work in React, the teacher and parent dashboards move to Streamlit and the student quiz becomes a single hand-written HTML/JS page served by FastAPI. The student quiz does not go in Streamlit under any circumstances.

## API service

- **FastAPI** with routers per domain: `assignments`, `attempts`, `mastery`, `recommendations`, `cohorts`, `goals`, `conferences`, `audit`.
- **Authorization** is a dependency on every route. It resolves the caller's role and allowed IDs (linked children for parents, assigned classes for teachers) and every repository query takes those IDs as a filter. Hiding a button is never the security boundary.
- **Pydantic v2** models for every entity in PRD §18. The activity draft model is exported to JSON Schema and committed to `packages/schema/activity.json`, which the front end imports for form validation.
- **Modules with interfaces:** `mastery/`, `cohorts/`, `retrieval/`, `generation/`, `storage/`, `tts/`. Each has a protocol class and at least one implementation, so the demo can swap the local adapters for AWS ones.
- **`DEMO_OFFLINE=1`** makes `retrieval/` read a local index and `generation/` return cached drafts. This is the fallback for a Bedrock outage on stage.

## Learner model

- BKT per skill with the PRD §9.1 defaults. One function: `update(state, correct, hint_used) -> state`. One selector: `next_item(state, bank, seen) -> item`.
- Confidence is computed from evidence count and agreement, not stored separately.
- Unit tests cover the scripted demo path for "Sam" so the adaptive route is reproducible on every run.

### Why there is no ML library in the inference path

BKT inference is a closed-form Bayes update with four parameters. There is nothing to train at demo time, so scikit-learn, PyTorch, or SageMaker would add a dependency without adding a capability, and a teacher-readable formula is part of the explainability requirement.

ML tooling enters in three places:

1. **Parameter calibration (optional, `scripts/calibrate_bkt.py`).** Uses `pyBKT` to fit `p_learn`, `p_guess`, and `p_slip` per skill from a response log by expectation-maximization. Runs on the synthetic log for the demo so the pipeline exists; the "how this works" panel can show default versus fitted values. On real data this is how the model improves per district.
2. **Embeddings.** Retrieval uses Amazon Titan Text Embeddings through Bedrock. That is a trained model in the loop.
3. **Generation.** Claude through Bedrock.

The outcome-learning loop in PRD §27 (ranking activities by demonstrated effectiveness) is the first place a trained, district-specific model would be justified. See "Roadmap services" below.

## Generative AI on Bedrock

- **Client:** `boto3` `bedrock-runtime` with the Converse API. If the account allows it, the Anthropic Bedrock SDK's Mantle client is an equivalent option; `boto3` is the default because Workshop Studio accounts always have it.
- **Model:** an Anthropic Claude model exposed by the Workshop Studio account, referenced with the `anthropic.` Bedrock model prefix. Prefer Claude Sonnet 5 for draft quality; Claude Haiku 4.5 if quota or latency forces it. Confirm the available IDs on day 1 with `aws bedrock list-foundation-models`.
- **Structured output:** the activity template schema is passed as a tool definition and the model is instructed to call it. The response's tool-use input is validated with Pydantic before anything is shown.
- **Guardrails:** created once with the console or CLI, referenced by ID in every Converse call. The guardrail result is stored with the recommendation.
- **Prompt hygiene:** the request contains the retrieved chunks, the template, and the minimal pseudonymous mastery summary from PRD §10. Nothing else.

## Retrieval

- **Bedrock Knowledge Base** over an S3 bucket. Each document has a `<name>.metadata.json` sidecar with the retrieval and provenance fields from PRD §10. Queries use `retrieve` with a metadata filter on grade, subject, skill, document type, audience, and approval.
- **Vector store:** OpenSearch Serverless if it provisions in under 30 minutes; otherwise the S3 Vectors store option.
- **Local fallback:** a script embeds the corpus with Bedrock Titan Text Embeddings into a NumPy array and applies the same metadata filter in Python. Same interface, same filter semantics, so the golden test set runs against both.
- **Ingestion gate:** `scripts/ingest.py` reads `corpus/manifest.json`, rejects any document without tier, citation, reviewer, and approval, uploads the rest with sidecars, and starts a sync job.

## Read-aloud

- `scripts/pregenerate_audio.py` calls Polly for every item prompt, choice, hint, and feedback string, stores MP3s in S3 (or `data/audio/` locally) keyed by a content hash, and writes the URL into the item record.
- Live synthesis is only used for generated activity text, and only on the teacher view.

## Storage

- `storage/local.py` reads and writes JSON files under `data/state/`. `scripts/reset_demo.py` copies `data/seed/` over it.
- `storage/dynamo.py` implements the same protocol with single-table design. It is built only after the local path works end to end.

## Additional AWS services

The Workshop Studio account exposes most of the AWS catalog. Each service below was judged on one question: does it remove work or add a real capability for this product? Anything that only adds a logo is left out.

### Use in the MVP

| Service | Use | Why it earns its place |
|---|---|---|
| Amazon CloudFront | Serve pre-generated Polly audio and, if deployed, the static front end from S3 | Audio playback on the student screen must be instant; CloudFront in front of S3 makes cached MP3s load from an edge in milliseconds and avoids exposing the bucket. |
| AWS Systems Manager Parameter Store | Hold the Bedrock model ID, Guardrail ID, Knowledge Base ID, bucket names | Four people will each have their own environment. One parameter path per setting means no hard-coded IDs and no `.env` files passed around in chat. |
| Amazon Textract | Convert Tier 2 district curriculum PDFs to text during corpus ingestion | District teaching guidelines usually arrive as scanned or layout-heavy PDFs. Textract turns them into clean text for chunking, which is the difference between a trusted corpus and a demo corpus. |
| AWS IAM | Least-privilege role for the API: Bedrock invoke, KB retrieve, Polly synthesize, S3 read/write on one bucket, DynamoDB on one table | Required anyway; documenting it up front avoids a wildcard policy on demo day. |

### Use if time allows (P1)

| Service | Use | Why |
|---|---|---|
| Amazon Cognito | Authentication and role claims | Already P1 in the PRD. Amplify wires it in with little code. |
| Amazon Translate | Parent-facing summaries in the family's language | Already P1. One API call per summary, English source retained. |
| Amazon Bedrock Agents | Run the conference-scheduling assistant as a managed agent with `list_available_slots` and `create_conference_request` as action-group tools | Replaces a hand-written tool-use loop with a managed one and gives judges a native AWS agent to look at. Only worth it if the manual scheduling flow is already done. |
| Amazon Comprehend | PII detection on free-text fields parents and teachers type (conference agenda, observation notes) before storage | Guardrails covers model calls; Comprehend covers text that never reaches a model but still lands in the database. |

### Roadmap services (post-hackathon)

| Service | Use | Why later |
|---|---|---|
| Amazon SageMaker | Train and host the outcome-ranking model for the learning loop; run BKT calibration at district scale | Needs real outcome data and governance first. |
| Amazon Personalize | Alternative to a custom model for ranking activity templates per learner evidence pattern | Managed recommender; makes sense once there are thousands of outcomes. |
| Amazon Transcribe | Spoken answers for students who cannot use a pointer or keyboard | Real accessibility value, pairs with AAC support in PRD FR-30. Needs careful design so speech recognition errors do not become mastery errors. |
| Amazon SES and Amazon EventBridge | Conference status notifications by email, scheduled progress digests to families | PRD keeps external email out of scope until a district privacy review. |
| AWS Step Functions | Orchestrate ingestion (Textract, chunk, embed, sync) and the recommendation pipeline with retries | Useful once ingestion runs on real district content; in-process is fine for 30 documents. |
| Amazon CloudTrail | Audit AWS API activity alongside the application audit log | Part of a district security review, not the demo. |

### Considered and rejected

| Service | Reason |
|---|---|
| Amazon QuickSight | Embedded dashboards are slow to set up and would replace the accessible React views with iframes. |
| Amazon Kendra | Overlaps with Bedrock Knowledge Bases and costs more; metadata filtering in KB is sufficient. |
| Amazon Lex | The student experience is not a chatbot, and the scheduling assistant is better served by Converse tool use or Bedrock Agents. |
| AWS Lambda + API Gateway for the API | Works (FastAPI runs under Mangum), but App Runner runs the same container with no cold starts and less wiring. Keep as an alternative if App Runner is unavailable. |
| Amazon Chime SDK | Virtual conference rooms are out of scope; scheduling is the problem, not the meeting. |

## Repository layout

```
apps/web/               React app
services/api/           FastAPI service
packages/schema/        Shared JSON schemas exported from Pydantic
corpus/                 Knowledge-base documents, sidecars, manifest
data/seed/              Synthetic classroom, item bank, hints, scripted paths
data/state/             Runtime state for the local adapter (gitignored)
scripts/                ingest.py, pregenerate_audio.py, reset_demo.py, seed.py
docs/                   PRD.md, TECH_STACK.md
```

## Local development

- Node 20 and Python 3.12.
- `pnpm` for the front end, `uv` for Python dependencies.
- One `make dev` (or a `justfile`) starts both servers. The API runs on port 8000, the front end on 5173 with a proxy to the API.
- AWS credentials come from the Workshop Studio environment variables. Nothing is committed.

## Day-1 setup checklist

1. Confirm Bedrock model access and note the exact model IDs.
2. Start Knowledge Base provisioning immediately; build the local index in parallel.
3. Create the Guardrail and record its ID.
4. Create the S3 bucket for corpus and audio, put a CloudFront distribution in front of the audio prefix, and store all IDs in Parameter Store under `/hackathon/`.
5. Run `scripts/seed.py`, `scripts/pregenerate_audio.py`, and `scripts/reset_demo.py` once each to prove the offline path.
