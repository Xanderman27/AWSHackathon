# Dori

Accessible check-ins for K-12 students with IEPs and 504 plans, teacher-approved next steps, and plain-language progress for families. Capy the capybara guides the learner.

- Product requirements: [docs/PRD.md](docs/PRD.md)
- Tech stack: [docs/TECH_STACK.md](docs/TECH_STACK.md)
- Learner model: [docs/LEARNER_MODEL.md](docs/LEARNER_MODEL.md)

## Run it locally

Requires Node 20+ and Python 3.12+.

```bash
# API (first time: create the venv and install)
cd services/api
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt         # Windows: .venv/Scripts/python
.venv/bin/python -m uvicorn app.main:app --port 8010 --reload
```

```bash
# Web (second terminal)
cd apps/web
npm install
npm run dev
```

Open http://localhost:5173. The API runs on port 8010. Sign in with a demo account (synthetic data, demo-only plaintext credentials; Cognito is the production plan):

| Role | Username | Password |
|---|---|---|
| Student (Sam) | `sam` | `otter123` |
| Teacher (Ms. Rivera) | `rivera` | `teach123` |
| Parent (Jordan, linked to Sam) | `jordan` | `family123` |

- `python scripts/build_items.py` regenerates the item bank from the authored list.
- `POST http://localhost:8010/demo/reset` restores the seeded state.
- Tests: `cd services/api && .venv/bin/python -m pytest` (Windows: `.venv/Scripts/python`).

## What works today

- Landing page: a Duolingo-style hero with Capy waving; both buttons open the login dialog. Students use the login their teacher set; teachers and parents have their own.
- Student portal: a Duolingo-style practice path (3D step nodes per skill, earned from the same mastery estimate the teacher sees, never shown as a number), plus Quests (assigned adaptive assessments) and Games (collaborative activities and free play) tabs.
- Student quest: adaptive item selection, prerequisite routing, resume, reading passages that are not read aloud so the item still measures reading.
- One play/pause button per question that highlights each word as it is spoken, and light confetti on a correct answer.
- Dori appears beside the question and delivers the hint in a speech bubble.
- Accessibility bar: read-aloud (browser speech engine as a stand-in for Polly), high contrast, three text sizes, reduced motion, keyboard focus.
- Teacher dashboard: class counts, classwide statistics with per-subject averages, learner table with band and confidence, per-student item evidence with route reasons.
- Parent view: a Duolingo-profile-style page for the linked child — statistics, calculated achievements, group activities, mastery gauge and outcomes, teacher-approved next steps, and a rights library in a popup.
- Messages: a corner panel on the parent and teacher views. A parent can only reach their child's teacher; a teacher can only reach families in their own class. The server decides the pairing, not the client.
- Collaborative activities: six shared-room games over one WebSocket endpoint. A teacher picks an activity, reviews the suggested groups, moves anyone, and publishes; only then does a learner see it, and never the reason they were grouped. Every board is live for the whole group, and each square is tinted with the colour of the teammate who last touched it.

| Activity | What the group does | Grouped by |
|---|---|---|
| Beat Together | Build one 8-count loop together | equivalent-fractions evidence |
| Fraction Strips Together | Shade a fraction wall to find every row equal to the target | equivalent-fractions evidence |
| Story Detectives | Sort clue cards into big idea, helpful detail, and not in the story | main-idea evidence |
| Memory Meadow | Find matching pairs on one shared board | mixed groups, no evidence used |
| Sort It Out | Invent your own groups, name them, and defend them | mixed groups, no evidence used |
| Shape Shift | Turn and flip pieces to fill a shared outline | mixed groups, no evidence used |

  Games are free play: no score, no timer, and nothing from a room reaches the mastery model, the teacher dashboard, or a parent. The five activities that do not need a group can also be opened alone from the Games tab, in a room private to that learner.

## Layout

```
apps/web          React + Vite + TypeScript (student, teacher, parent routes)
  src/games       Shared room client: one socket, one snapshot, one send()
  src/pages/games One screen per collaborative activity
services/api      FastAPI: mastery model, selection, authorization, local JSON storage
  app/mastery     Layer 1 BKT (item-aware) and Layer 2 adaptive selection
  app/games       Activity registry and one module per game (state + apply)
data/seed         Skills, items, students, links, seeded mastery
data/state        Runtime state (gitignored; reset copies seed over it)
scripts           build_items.py; fit_*.py and simulate.py to come
docs              PRD, tech stack, learner model
```

## Next

Simulator and offline fits (IRT, BKT, pattern classifier), knowledge-base corpus and LangGraph recommendation graph on Bedrock, goal links, cohorts, conference scheduling, Polly audio.
