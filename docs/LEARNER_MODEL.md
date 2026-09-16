# Learner model architecture

Companion to PRD §9. The learner model is five layers. Each layer uses the smallest technique that solves its problem, and each one is explainable to a teacher. Layers that need data are fitted offline on a synthetic response log produced by a simulator; layers that run during a quiz are in-process and answer in milliseconds.

```
                 offline (fit on response log)          online (per answer, in FastAPI)
                 ─────────────────────────────          ───────────────────────────────
Layer 0  Item calibration      IRT 2PL (girth / scipy)   → item difficulty a, b
Layer 1  Knowledge state       BKT params via pyBKT EM   → BKT update per skill   ──┐
Layer 2  Item selection        —                          → CAT: max information   ◄─┘
Layer 3  Pattern recognition   scikit-learn classifier    → observed_pattern + prob
Layer 4  Outcome learning      —                          → Thompson-sampling bandit over templates
Simulator                      IRT learners + learning rate → synthetic log for Layers 0, 1, 3
```

Artifacts from the offline layers are JSON files in S3 (`models/item_params.json`, `models/bkt_params.json`, `models/pattern_clf.joblib`, `models/bandit_state.json`). The API loads them at startup and falls back to defaults if any is missing, so the quiz never depends on a fit having run.

## Layer 0: Item calibration (Item Response Theory)

**Problem.** Author-assigned difficulty (1–5) is a guess. Two "difficulty 3" items can behave very differently.

**Method.** Two-parameter logistic IRT. Each item gets a difficulty `b` and a discrimination `a`. The probability a learner of ability `θ` answers correctly is `P(θ) = 1 / (1 + exp(-a(θ - b)))`. Fitted by marginal maximum likelihood with the `girth` library (pure NumPy), or SciPy if `girth` is unavailable.

**Cold start.** Before any log exists, `b` is mapped from the author's 1–5 rating to the range −2 to +2 and `a` is 1.0. After a fit, the calibrated values replace them and the teacher-facing item view shows both.

**Why it is worth it.** Calibrated difficulty makes Layer 2 meaningfully adaptive and is how every serious adaptive assessment works.

## Layer 1: Knowledge state (Bayesian Knowledge Tracing)

**Problem.** Estimate, per student and skill, the probability the student currently knows the skill.

**Method.** BKT with four parameters per skill (`p_init`, `p_learn`, `p_guess`, `p_slip`). The update is closed form: weigh the evidence of the answer against guess and slip, then add credit for learning. Full walkthrough with a worked example in the appendix.

**Item-aware variant.** Instead of one `p_guess` and `p_slip` per skill, the online update derives them per item from Layer 0: an easy, high-discrimination item has a lower slip and a harder one a higher guess. This is the KT-IDEM variant of BKT. It costs nothing at runtime and stops the model over-penalizing a miss on the hardest item in the bank.

**Fitting.** Skill parameters are fitted by expectation-maximization with `pyBKT` on the response log. A NumPy EM implementation is kept as a fallback in case `pyBKT` fails to install on a team machine. The "how this works" panel shows default and fitted values side by side.

**Hints.** A correct answer after a hint uses a raised guess probability for that single update, so it moves the estimate less. Hint use is also a feature for Layer 3.

## Layer 2: Item selection (computerized adaptive testing)

**Problem.** Pick the next question that tells us the most, without discouraging the student.

**Method.** Map the BKT estimate to an ability `θ` on the IRT scale, then choose the unseen approved item in the assigned objective with the highest Fisher information `I(θ) = a² P(θ)(1 − P(θ))`, subject to a floor on expected success (default 0.60) so the student is not fed only hard items. Exposure control: an item is not shown twice in one attempt and its recent use across the class is penalized slightly so the same three items do not dominate.

**Routing rules stay explicit.** Two misses below the easy band route to the prerequisite skill and record the reason. Estimate above 0.80 with medium or higher confidence unlocks an extension item. These are teacher-readable rules, not learned behavior.

## Layer 3: Pattern recognition (supervised classifier)

**Problem.** The RAG query needs an `observed_pattern` such as "recognizes visual equivalence but struggles with symbolic notation." In v0.1 that was hand-coded. Hand-coded rules do not scale past two skills.

**Method.** A scikit-learn logistic regression (gradient boosting if it clearly wins on the validation split) over a small feature vector per attempt: correctness by difficulty band, which distractor was chosen on each miss (each distractor is tagged with the misconception it represents), hint count, prerequisite-route flag, and the BKT trajectory shape. Labels come from a fixed, teacher-reviewed taxonomy per skill, for example for equivalent fractions: `visual_only`, `symbolic_notation_gap`, `prerequisite_gap`, `consistent`, `insufficient_evidence`.

**Training data.** The simulator generates learners with a known pattern, so labels are exact. The model is validated on a held-out simulated split and the confusion matrix is committed with the artifact.

**Output.** A pattern label and probability. Below a threshold (default 0.55) the pattern is `insufficient_evidence`, which the recommendation graph turns into "ask for one more short quest" instead of an activity. Logistic regression coefficients are shown in the teacher's evidence panel as "why the system thinks this."

## Layer 4: Outcome learning (Thompson-sampling bandit)

**Problem.** Learn which activity templates help which learners from teacher-reported outcomes, without waiting for thousands of records.

**Method.** For each context (skill, pattern label) and each approved activity template, keep a Beta posterior over "helped" versus "did not help," updated from the teacher's one-tap outcome. When proposing an activity, sample from each posterior and order templates by the sample. This is Thompson sampling: it explores when it knows little and exploits when it knows more, and it is explainable as "this template helped 4 of 5 similar learners."

**Boundaries.** The bandit only orders templates the retrieval step already returned as approved and relevant. The teacher still approves. It never touches mastery, cohorts, or which students get which quest. Posteriors start at Beta(1, 1) and are stored per class so one class's outcomes do not silently move another's until a district chooses to pool them.

## The simulator

An IRT-based learner simulator produces every response log the offline layers fit on. Each simulated learner has a latent ability per skill, a learning rate, a pattern label from the taxonomy that biases which distractors they choose, and a hint propensity. The 12 demo students are drawn from it with fixed seeds so the demo path is reproducible, and a larger population (500 learners, 6 sessions each) provides the fitting data.

The team will state plainly that all fitted parameters come from simulated data. The value being demonstrated is that the pipeline exists and runs end to end; the numbers are placeholders until a district provides real logs under a data agreement.

## Confidence

Confidence combines three signals: the number of relevant answers, agreement of the BKT trajectory (no alternating pattern), and Layer 3's probability. Fewer than three answers or a pattern probability under threshold means low. Six or more consistent answers with a confident pattern means high. Everything else is medium. Low confidence blocks definitive recommendations and cohort placement.

## What the model never uses

Disability category, goal links, IEP or 504 status, demographics, behavior or discipline history, response time (logged for the teacher only), and other students' performance. Layer 3's feature vector is committed to the repository so anyone can verify this.

## Libraries and where they run

| Layer | Library | Runs |
|---|---|---|
| 0 | `girth` (NumPy IRT), SciPy fallback | Offline script |
| 1 fit | `pyBKT`, NumPy EM fallback | Offline script |
| 1 update, 2 select | NumPy only | In-process, per answer |
| 3 fit | `scikit-learn`, `joblib` | Offline script |
| 3 score | `scikit-learn` | In-process, at attempt end |
| 4 | NumPy (Beta sampling) | In-process, at recommendation time |
| Simulator | NumPy | Offline script |

Offline scripts run locally in the hackathon. If time allows, they run as an Amazon SageMaker Processing job reading the log from S3 and writing artifacts back, which is the production shape. Inference never leaves the API process, which is how the two-second next-item requirement is met.

## Roadmap

- **Deep knowledge tracing** (an LSTM or transformer model such as SAKT, in PyTorch) as a second estimator once a district has real longitudinal data. It would run alongside BKT, and the teacher view would show both with BKT as the explanation.
- **Pooled bandits** across classes and schools under district governance.
- **Fairness audit** of Layer 3 and Layer 4 outcomes across populations, with the same governance.

## Appendix: the BKT update, worked

Sam starts a fractions quest at the default estimate 0.30, with `p_learn` 0.15, `p_guess` 0.20, `p_slip` 0.10.

Correct answer:

```
knew    = estimate × (1 − p_slip)
did_not = (1 − estimate) × p_guess
estimate = knew / (knew + did_not)
estimate = estimate + (1 − estimate) × p_learn
```

Wrong answer swaps the likelihoods: `knew = estimate × p_slip`, `did_not = (1 − estimate) × (1 − p_guess)`.

- Question 1, correct: 0.27 / 0.41 = 0.66, then learning brings it to **0.71**.
- Question 2, wrong: 0.071 / 0.303 = 0.23, then **0.35**.
- Question 3, correct after a hint (guess raised to 0.35): 0.315 / 0.543 = 0.58, then **0.64**.

The hinted correct answer moved the estimate less than an unhinted one would have. With Layer 0 in place, the guess and slip values in these formulas come from the specific item's calibrated difficulty rather than the skill defaults.

## What to say to a judge or a teacher

"Every answer updates one number per skill: how likely it is that this student knows it. Items are calibrated so the model knows which questions are actually hard. The next question is the one that tells us the most without being discouraging. At the end, a small classifier names the pattern in the answers, which is what the activity generator uses, and a bandit learns from teachers which activities actually helped. Every layer is explainable, all of it runs on synthetic data today, and none of it diagnoses, grades, or places a student."
