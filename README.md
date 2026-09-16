# Dori

Accessible check-ins for K-12 students with IEPs and 504 plans, teacher-approved next steps, and plain-language progress for families. Dori is the bear who guides the learner.

- Product requirements: [docs/PRD.md](docs/PRD.md)
- Tech stack: [docs/TECH_STACK.md](docs/TECH_STACK.md)
- Learner model: [docs/LEARNER_MODEL.md](docs/LEARNER_MODEL.md)

## Run it locally

Requires Node 20+ and Python 3.12+.

```bash
# API (first time: create the venv and install)
cd services/api
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --port 8010 --reload
```

```bash
# Web (second terminal)
cd apps/web
npm install
npm run dev
```

Open http://localhost:5173. The API runs on port 8010. Pick a role on the home page; the demo uses synthetic accounts (Sam is `student-01`, the teacher owns class 4A, `parent-01` is linked to Sam).

- `python scripts/build_items.py` regenerates the item bank from the authored list.
- `POST http://localhost:8010/demo/reset` restores the seeded state.
- Tests: `cd services/api && .venv/Scripts/python -m pytest`.

## What works today

- Landing page: animated, states who it is for, and links the frameworks the product follows.
- Student portal: Quests (adaptive assessments) and Games (free play, placeholders for now).
- Student quest: adaptive item selection, prerequisite routing, resume, reading passages that are not read aloud so the item still measures reading.
- One play/pause button per question that highlights each word as it is spoken, and light confetti on a correct answer.
- Dori appears beside the question and delivers the hint in a speech bubble.
- Accessibility bar: read-aloud (browser speech engine as a stand-in for Polly), high contrast, three text sizes, reduced motion, keyboard focus.
- Teacher dashboard: class counts in neutral language, learner table with band and confidence, per-student item evidence with route reasons.
- Parent view: linked children only, a child-only mastery gauge, teacher-approved next steps, and a rights library that opens in a popup.
- Messages: a corner panel on the parent and teacher views. A parent can only reach their child's teacher; a teacher can only reach families in their own class. The server decides the pairing, not the client.

## Layout

```
apps/web          React + Vite + TypeScript (student, teacher, parent routes)
services/api      FastAPI: mastery model, selection, authorization, local JSON storage
  app/mastery     Layer 1 BKT (item-aware) and Layer 2 adaptive selection
data/seed         Skills, items, students, links, seeded mastery
data/state        Runtime state (gitignored; reset copies seed over it)
scripts           build_items.py; fit_*.py and simulate.py to come
docs              PRD, tech stack, learner model
```

## Next

Simulator and offline fits (IRT, BKT, pattern classifier), knowledge-base corpus and LangGraph recommendation graph on Bedrock, goal links, cohorts, conference scheduling, Polly audio.
