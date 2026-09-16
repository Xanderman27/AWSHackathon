# AWS Hackathon: Adaptive Learning Platform

Accessible check-ins for elementary students with IEPs and 504 plans, teacher-approved next steps, and plain-language progress for families.

- Product requirements: [docs/PRD.md](docs/PRD.md)
- Tech stack: [docs/TECH_STACK.md](docs/TECH_STACK.md)

## Layout (planned)

```
apps/web        React + Vite + TypeScript front end (student, teacher, parent routes)
services/api    FastAPI service: mastery model, cohorts, authorization, Bedrock, storage
corpus/         Curated knowledge-base documents with metadata sidecars and source manifest
data/           Synthetic classroom, item bank, hints, scripted demo paths
scripts/        Setup, ingestion, Polly pre-generation, demo reset
docs/           PRD and design notes
```
