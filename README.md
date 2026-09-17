# Dori

Accessible check-ins for K-12 students with IEPs and 504 plans, teacher-approved next steps, and plain-language progress for families. Capy the capybara guides the learner.

- Product requirements: [docs/PRD.md](docs/PRD.md)
- Tech stack: [docs/TECH_STACK.md](docs/TECH_STACK.md)
- Learner model: [docs/LEARNER_MODEL.md](docs/LEARNER_MODEL.md)
- Going live on AWS: [docs/AWS.md](docs/AWS.md)
- Guidelines (learning, disability, collaboration, grouping, UI standards): [docs/GUIDELINES.md](docs/GUIDELINES.md)

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

The three student logins sit together in a **Demo Table** group for every game, so two or
three people can sign in on separate devices, open the same game, and land in the same room.

Open http://localhost:5173. The API runs on port 8010. Sign in with a demo account (synthetic data, demo-only plaintext credentials; Cognito is the production plan):

| Role | Username | Password |
|---|---|---|
| Student (Sam) | `sam` | `otter123` |
| Student (Mia) | `mia` | `otter123` |
| Student (Ava) | `ava` | `otter123` |
| Teacher (Ms. Rivera) | `rivera` | `teach123` |
| Parent (Jordan, linked to Sam) | `jordan` | `family123` |

- `python scripts/build_items.py` regenerates the item bank from the authored list.
- `POST http://localhost:8010/demo/reset` restores the seeded state.
- Tests: `cd services/api && .venv/bin/python -m pytest` (Windows: `.venv/Scripts/python`).

## What works today

- Landing page: a Duolingo-style hero with Capy. "Get started" opens a family sign-up (name,
  email, password, class code) — the code decides which classroom they join, and a second step
  asks which child is theirs. "I already have an account" is the login. Students use the login
  their teacher set. Seeded demo logins stay plaintext so judges can read them off the screen;
  anything a real person types at sign-up is salted and hashed with PBKDF2.
- Class code: the teacher's Activities tab shows the code (seeded `BRIGHT4`), copies it, and can
  issue a new one, which stops the old code working. Codes skip characters people confuse
  (no O/0, I/1/L) and are matched ignoring case, spaces, and dashes.
- Student portal: a Duolingo-style practice path (3D step nodes per skill, earned from the same mastery estimate the teacher sees, never shown as a number), plus Quests (assigned adaptive assessments) and Games (collaborative activities and free play) tabs.
- Student quest: adaptive item selection, prerequisite routing, resume, reading passages that are not read aloud so the item still measures reading.
- One play/pause button per question that highlights each word as it is spoken, and light confetti on a correct answer.
- Dori appears beside the question and delivers the hint in a speech bubble.
- Accessibility bar: read-aloud (browser speech engine as a stand-in for Polly), high contrast, three text sizes, reduced motion, keyboard focus.
- Teacher dashboard, four tabs:
  - **Learners** — class summary tiles, then a grid of learner cards (face, name, the skill they
    are furthest from). Clicking one opens that learner's own page: totals, a card per skill with
    band, mastery, confidence and a trend line, who they work with, and every answer they have
    given, newest first.
  - **Activities** — class code, quest assignment, and the collaborative-activity group builder.
  - **Family updates** — the class blog (below).
  - **Class statistics** — aggregate only, per-subject proficiency buckets.
- Parent view: the classroom photo feed, "Who <child> works with" showing each team activity's
  teammates by name and face, and a Duolingo-profile-style page for the linked child — statistics, calculated achievements, group activities, mastery gauge and outcomes, teacher-approved next steps, and a rights library in a popup.
- Class blog: the teacher writes an update — photo, headline, a sentence, a date — and it appears
  on the dashboard of every family in that class. Image bytes go through an authorised route, not
  a public folder.
  Who sees what, and what a district would need before this ships, is in
  [docs/PRIVACY_POSTURE.md](docs/PRIVACY_POSTURE.md).
- Grounded activity recommendations: on a learner's page the teacher drafts an at-home activity
  built only from an approved corpus (`corpus/manifest.json` — standards, misconception guidance,
  accessibility notes, reviewed templates, each with tier, citation and reviewer). The draft
  arrives with its sources and the path the pipeline took, and nothing reaches the family until
  the teacher approves it. Runs on cached drafts with no AWS; `DEMO_OFFLINE=0` plus credentials
  makes it a live Bedrock Converse call with tool-use for structured output and an optional
  guardrail. See [docs/AWS.md](docs/AWS.md).
- Messages: a corner panel on the parent and teacher views. A parent can only reach their child's teacher; a teacher can only reach families in their own class. The server decides the pairing, not the client.
- Faces: each seeded learner has a portrait (`apps/web/public/faces/`, credits and a caveat in
  `CREDITS.md` there) with an illustrated fallback in `components/Avatar.tsx` for anyone without
  one. A team activity leads with its teammates' faces, and the ring around a face is the same
  colour as the squares that person edited on the shared board.
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
data/seed         Skills, items, students, links, seeded mastery; uploads/ holds seeded photos
data/state        Runtime state (gitignored; reset copies seed over it, uploads included)
scripts           build_items.py; fit_*.py and simulate.py to come
docs              PRD, tech stack, learner model, privacy posture, guidelines
```

## Next

Simulator and offline fits (IRT, BKT, pattern classifier), knowledge-base corpus and LangGraph recommendation graph on Bedrock, goal links, cohorts, conference scheduling, Polly audio.
