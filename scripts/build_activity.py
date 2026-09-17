"""Generate data/seed/attempts.json and data/seed/benchmarks.json for the demo class.

Without these two files every activity counter on the teacher dashboard is zero: stars,
questions answered, quests finished and hints all derive from the attempt log, and the log
was never seeded. An empty classroom is a bad first impression of a product whose whole
argument is "look at the evidence".

The log is *derived from the seeded mastery*, not invented independently. For each
(learner, skill) row in mastery.json this walks the recorded history, answering items with a
probability that tracks the estimate at that point, so the dashboard's totals, the subject
bars and each learner's evidence panel all tell the same story. A hand-written log would
drift from the mastery numbers the moment anyone edited either file.

Everything is seeded from a fixed RNG, so the demo is identical on every machine and a
re-run does not reshuffle the class. Run: python scripts/build_activity.py
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"

# The demo's "today" is the day the file is generated, so the dashboard's 14-day activity
# chart always has something in its most recent columns. Re-run this script when the demo
# starts looking stale; the RNG seed is fixed, so the shape of the class does not change.
TODAY = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
RNG = random.Random(4207)
NL = chr(10)

MAX_ITEMS = 6
WINDOW_DAYS = 14         # matches the teacher dashboard's activity chart
HINT_BASE = 0.14          # chance a learner opens a hint on any item
HINT_STRUGGLE = 0.34      # ... and when the skill is still building


def load(name: str):
    return json.loads((SEED / f"{name}.json").read_text(encoding="utf-8"))


def stamp(day_offset: float) -> str:
    """An ISO timestamp day_offset days before TODAY, landed inside the school day."""
    when = TODAY - timedelta(days=day_offset)
    when = when.replace(hour=9 + RNG.randrange(6), minute=RNG.randrange(60), second=0, microsecond=0)
    return when.isoformat()


def pick_choice(item: dict, correct: bool) -> str:
    """The right answer, or a distractor — preferring one tagged with a misconception,
    because the Layer 3 pattern classifier reads distractor tags, not just wrongness."""
    if correct:
        return item["answer"]
    wrong = [c for c in item["choices"] if c["id"] != item["answer"]]
    tagged = [c for c in wrong if c.get("misconception")]
    return RNG.choice(tagged or wrong)["id"]


def build_attempts(students, mastery, items, skills):
    """One attempt per six answers, replaying each learner's recorded mastery history."""
    by_skill: dict[str, list[dict]] = {}
    for it in items:
        if it.get("approved", True):
            by_skill.setdefault(it["skill_id"], []).append(it)

    student_ids = {s["id"] for s in students}
    attempts: list[dict] = []
    counter = 0

    for row in sorted(mastery, key=lambda r: (r["student_id"], r["skill_id"])):
        if row["student_id"] not in student_ids:
            continue
        pool = by_skill.get(row["skill_id"], [])
        if not pool:
            continue

        history = row.get("history") or [row["estimate"]]
        total = max(row.get("evidence_count", len(history)), 1)
        unseen = pool[:]
        RNG.shuffle(unseen)

        # Split the evidence into attempt-sized chunks, then give each chunk its own day.
        #
        # Two earlier versions of this got the shape wrong in opposite directions. Walking
        # each learner from an old endpoint to a recent one left the last days of the chart
        # empty, because only a row whose final chunk happened to land on its endpoint
        # reached them. Pinning every final chunk to the recent end instead put a third of
        # the fortnight's answers on one day. Drawing a day per attempt from a distribution
        # that leans recent, then sorting oldest-first so a learner's own evidence stays in
        # order, gives a classroom rhythm rather than a ramp or a spike.
        sizes: list[int] = []
        remaining = total
        while remaining > 0:
            sizes.append(min(MAX_ITEMS, remaining))
            remaining -= sizes[-1]
        days = sorted((RNG.triangular(0.2, WINDOW_DAYS - 0.6, 2.5) for _ in sizes), reverse=True)

        answered = 0
        for size, started in zip(sizes, days):
            # A trailing stub of one or two answers reads as an attempt still in progress.
            completed = size >= 4
            if not unseen:
                unseen = pool[:]
                RNG.shuffle(unseen)

            counter += 1
            responses = []
            for step in range(size):
                item = unseen.pop() if unseen else RNG.choice(pool)
                # The estimate at this point in the learner's history drives correctness.
                at_point = history[min(answered + step, len(history) - 1)]
                p_correct = min(0.93, max(0.12, at_point))
                # A harder item is less likely to land; difficulty runs 1..5.
                p_correct -= (item.get("difficulty", 3) - 3) * 0.08
                correct = RNG.random() < max(0.08, min(0.95, p_correct))
                hint_chance = HINT_STRUGGLE if at_point < 0.45 else HINT_BASE
                responses.append({
                    "item_id": item["id"],
                    "choice_id": pick_choice(item, correct),
                    "correct": correct,
                    "hint_used": RNG.random() < hint_chance,
                    "route_reason": None,
                    "at": stamp(started - step * 0.01),
                })

            attempts.append({
                "id": f"att-seed{counter:04d}",
                "student_id": row["student_id"],
                "skill_id": row["skill_id"],
                "current_skill_id": row["skill_id"],
                "responses": responses,
                "max_items": MAX_ITEMS,
                "completed": completed,
                "started_at": stamp(started),
            })
            answered += size

    return attempts


def fill_mastery(students, mastery, skills):
    """Top up mastery.json so the class has evidence outside math.

    The seeded rows are hand-curated — Sam's scripted demo path depends on her exact numbers
    — so every existing row is returned untouched and this only *appends* pairs that have no
    row at all. Without it the subject breakdown is one tall math bar and four empty ones.

    Not every learner gets every subject. "Needs more evidence" is a real state the teacher
    dashboard is supposed to surface (docs/GUIDELINES.md §5.4), so a class where everyone has
    full evidence everywhere would be hiding the honest answer.
    """
    # Re-running must not stack another layer of rows on top of the last run, so anything this
    # script produced is dropped first and regenerated. The curated rows carry no marker.
    mastery = [m for m in mastery if not m.get("generated")]
    have = {(m["student_id"], m["skill_id"]) for m in mastery}
    added: list[dict] = []

    for student in students:
        missing = [s["id"] for s in skills if (student["id"], s["id"]) not in have]
        RNG.shuffle(missing)
        # Three to five extra subjects each: enough that a fortnight of the class reads as
        # busy, not so much that the "needs more evidence" count collapses to zero.
        for skill_id in missing[:RNG.randrange(3, 6)]:
            estimate = round(min(0.94, max(0.12, RNG.gauss(0.58, 0.21))), 2)
            evidence = RNG.randrange(4, 12)
            # A history that walks from a cold start up to the estimate, with a wobble.
            history = []
            value = round(max(0.1, estimate - RNG.uniform(0.18, 0.34)), 2)
            for step in range(evidence):
                value = round(min(0.95, max(0.08,
                    value + (estimate - value) * 0.45 + RNG.uniform(-0.06, 0.06))), 2)
                history.append(value)
            history[-1] = estimate
            added.append({
                "student_id": student["id"],
                "skill_id": skill_id,
                "estimate": estimate,
                "evidence_count": evidence,
                "history": history,
                "updated_at": stamp(RNG.uniform(1, 9)),
                "generated": True,
            })

    return mastery + added, added


def build_benchmarks(students, mastery, skills):
    """A subject check-in per learner per subject they have evidence in.

    Stars only count quizzes finished *after* the check-in for that subject, so these are
    dated before the attempt log. A learner with no evidence in a subject has not checked in.
    """
    by_id = {s["id"]: s for s in skills}
    pairs = sorted({(m["student_id"], by_id[m["skill_id"]]["subject"])
                    for m in mastery if m["skill_id"] in by_id})
    ids = {s["id"] for s in students}
    return [{"student_id": sid, "subject": subject, "at": stamp(14.5)}
            for sid, subject in pairs if sid in ids]


GAMES = [
    ("beat-together", "Beat Together", "Blue Note Crew"),
    ("globe-trotters", "Globe Trotters", "Compass Club"),
    ("checkers", "Checkers Corner", "Otter Table"),
    ("memory-meadow", "Memory Meadow", "Maple Group"),
    ("sort-it-out", "Sort It Out", "Harbour Crew"),
    ("story-detectives", "Story Detectives", "Lantern Group"),
    ("shape-shift", "Shape Shift", "Kite Table"),
]


def build_group_activities(students, existing):
    """A fortnight of small-group work, rotating so no pair repeats.

    The teacher dashboard reports the drift metrics from docs/GUIDELINES.md §5.9 —
    groupmate diversity, repeat pairings, learners never grouped — and with a single seeded
    activity they are all degenerate. Rotation here is deliberate: members are dealt from a
    list that shifts by a different stride each round, which is the cheap version of the
    rotation penalty in §5.5 and keeps repeat pairs near zero.
    """
    ids = [s["id"] for s in students]
    rows = [r for r in existing if not r.get("generated")]
    seen = {r["id"] for r in rows}

    for round_no, (game_id, title, group_name) in enumerate(GAMES):
        # A different stride per round means the trios reshuffle rather than rotate rigidly.
        stride = 1 + round_no * 5
        order = [ids[(i * stride + round_no) % len(ids)] for i in range(len(ids))]
        # Deal trios; a trailing pair is fine, a trailing single is folded back in.
        trios = [order[i:i + 3] for i in range(0, len(order), 3)]
        if len(trios[-1]) == 1:
            trios[-2] += trios.pop()

        for seat, members in enumerate(trios):
            row_id = f"group-activity-{game_id}-{round_no}{seat}"
            if row_id in seen:
                continue
            rows.append({
                "id": row_id,
                "class_id": students[0]["class_id"],
                "game_id": game_id,
                "title": title,
                "group_name": f"{group_name}" if seat == 0 else f"{group_name} {seat + 1}",
                "member_ids": members,
                "rationale": "Recent evidence on the same classroom objective, and no pair here "
                             "worked together in the last three activities.",
                "status": "published",
                "created_by": "teacher-01",
                "published_at": stamp(12 - round_no * 1.7),
                "generated": True,
            })
    return rows


def main() -> None:
    students, mastery = load("students"), load("mastery")
    items, skills = load("items"), load("skills")

    mastery, added = fill_mastery(students, mastery, skills)
    attempts = build_attempts(students, mastery, items, skills)
    benchmarks = build_benchmarks(students, mastery, skills)
    groups = build_group_activities(students, load("group_activities"))

    if added:
        (SEED / "mastery.json").write_text(json.dumps(mastery, indent=2) + "\n", encoding="utf-8")
    (SEED / "attempts.json").write_text(json.dumps(attempts, indent=2) + "\n", encoding="utf-8")
    (SEED / "benchmarks.json").write_text(json.dumps(benchmarks, indent=2) + "\n", encoding="utf-8")
    (SEED / "group_activities.json").write_text(json.dumps(groups, indent=2) + NL, encoding="utf-8")

    answers = sum(len(a["responses"]) for a in attempts)
    correct = sum(1 for a in attempts for r in a["responses"] if r["correct"])
    print(f"mastery      {len(mastery)} rows ({len(added)} appended)")
    print(f"attempts     {len(attempts)}")
    print(f"answers      {answers}  ({correct} correct, {round(100 * correct / answers)}%)")
    print(f"finished     {sum(1 for a in attempts if a['completed'])}")
    print(f"hints        {sum(1 for a in attempts for r in a['responses'] if r['hint_used'])}")
    print(f"benchmarks   {len(benchmarks)}")
    print(f"group work   {len(groups)} activities")


if __name__ == "__main__":
    main()
