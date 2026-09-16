# The learner model, explained

This is the plain-language companion to PRD §9. It exists so every team member, and later every teacher, can explain what the number on the screen means.

## What the model estimates

For each student and each skill, the model keeps one number: the probability that the student currently knows the skill. It starts at a default and moves after every answer. It is never shown to students. Teachers see it as a band ("Building foundations," "Practicing," "Ready for extension") together with a confidence level.

## The four parameters

The model is called Bayesian Knowledge Tracing. It has four parameters per skill, each a probability:

| Name | Plain meaning | Default |
|---|---|---|
| p_init | Chance the student already knows the skill before we have seen any answers | 0.30 |
| p_learn | Chance the student learns the skill during any one question, regardless of whether they got it right | 0.15 |
| p_guess | Chance of a correct answer when the student does not know the skill (four choices, so a bit above one in four) | 0.20 |
| p_slip | Chance of a wrong answer when the student does know the skill (misread, misclick, distraction) | 0.10 |

The last two are what make the model forgiving. One wrong answer does not mean the student does not know; one right answer does not mean they do.

## How one answer changes the estimate

Two steps happen after every answer.

**Step 1: weigh the evidence.** Ask "how likely was this answer if the student knows, versus if they do not?" and update the estimate accordingly.

If the answer was correct:

```
knew = estimate × (1 − p_slip)
did_not = (1 − estimate) × p_guess
estimate = knew / (knew + did_not)
```

If the answer was wrong:

```
knew = estimate × p_slip
did_not = (1 − estimate) × (1 − p_guess)
estimate = knew / (knew + did_not)
```

**Step 2: allow for learning.** The question itself was a chance to learn, so:

```
estimate = estimate + (1 − estimate) × p_learn
```

That is the whole model.

## A worked example

Sam starts a fractions quest. Estimate = 0.30.

**Question 1, correct.**
knew = 0.30 × 0.90 = 0.27. did_not = 0.70 × 0.20 = 0.14.
estimate = 0.27 / 0.41 = 0.66. After learning: 0.66 + 0.34 × 0.15 = **0.71**.

**Question 2, wrong** (starting from 0.71).
knew = 0.71 × 0.10 = 0.071. did_not = 0.29 × 0.80 = 0.232.
estimate = 0.071 / 0.303 = 0.23. After learning: 0.23 + 0.77 × 0.15 = **0.35**.

**Question 3, correct after using a hint.** A hint makes a lucky right answer more likely, so p_guess is raised to 0.35 for this one update.
knew = 0.35 × 0.90 = 0.315. did_not = 0.65 × 0.35 = 0.228.
estimate = 0.315 / 0.543 = 0.58. After learning: 0.58 + 0.42 × 0.15 = **0.64**.

Notice that the hinted correct answer moved the estimate less than the unhinted one in question 1 would have. That is the point of logging hints.

## What the model deliberately ignores

- **Response time.** Logged for the teacher, never used in the update. Slow answers are often accommodation, not confusion.
- **Anything about the student other than their answers.** No disability category, goal links, demographics, behavior, or prior grades.
- **Other students.** Each estimate is independent. There is no ranking.

## Confidence

The estimate alone can mislead when there is little evidence. Confidence is reported separately:

| Relevant answers | Confidence |
|---|---|
| fewer than 3 | Low |
| 3 to 5 | Medium |
| 6 or more, consistent | High |

If answers alternate right and wrong at the same difficulty, confidence is capped at medium and one more question is asked. A low-confidence estimate never produces a definitive recommendation or a cohort placement.

## How the estimate chooses the next question

1. Stay inside the skill the teacher assigned.
2. Pick the unseen question whose difficulty best matches the estimate, aiming for about a 70 percent chance of success. Too easy teaches nothing; too hard is discouraging.
3. If the student misses two easy questions in a row, switch to the prerequisite skill and record why, so the teacher sees "routed to fractions-as-parts-of-a-whole after two misses."
4. If the estimate passes 0.80 with at least medium confidence, offer a harder or extension question.

## Where machine learning fits

The four parameters above are defaults. With real response logs, they can be fitted per skill using expectation-maximization (the `pyBKT` library does this), which is how the model becomes more accurate for a particular district's students. The hackathon includes an optional calibration script that runs this on the synthetic log so the pipeline exists. There is no training step in the live quiz.

## What to say to a judge or a teacher

"After every answer we update one number: how likely it is that this student knows this skill. The update accounts for lucky guesses and careless slips, and it gives credit for learning during the quiz. We show it as a band with a confidence level, and it only drives which question comes next and what evidence the teacher sees. It never diagnoses, grades, or places a student."
