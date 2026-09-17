# Learning, disability, and the design rules that follow

Reference document for Dori. It collects the legal requirements, instructional research, and interface standards that the product has to satisfy, and turns each one into a rule we can build against. It is the background document for the PRD, not a replacement for it: where the PRD says *what* to build, this says *why that and not something else*.

**Status.** Written for the hackathon build. Citations are given so each claim can be checked; verify quotes, effect sizes, and current URLs against the primary source before any of this is shown to a district. Nothing here is legal advice.

**Scope note.** Two audiences run through the whole document: the child using the student portal, and the adults (teacher, family) using the other two. Rules that apply to one and not the other are marked.

---

## 0. How to use this document

For a person: read §4 and §5 before touching collaboration or the cohort algorithm, §1 for the legal boundaries, §6 before touching the student UI.

For a prompt: the compressed version of the hard rules is below. It is safe to paste as context on its own.

> Dori is a formative check-in tool for K-12 students with IEPs and 504 plans. It never diagnoses, determines eligibility, recommends placement, or writes IEP content. The learner model uses evidence from answers only: never disability category, IEP or 504 status, goal links, demographics, behavior history, or another student's performance. Collaboration is a core, evidence-backed feature: structured peer work raises achievement and belonging for students with disabilities, but only when the task cannot be done alone, every member has a role, an individual step closes the activity, and roles rotate so nobody is the permanent helper or the permanent helped. Groups are temporary "activity cohorts," teacher-approved, expiring, never shown to students or families, and never formed from disability status. Student-facing text is at or below a Grade 3 reading level with no scores, numbers, timers, streaks, leaderboards, or failure states. The student interface targets WCAG 2.2 Level AA, 44 px minimum targets, keyboard and switch operability, read-aloud on everything except reading-comprehension passages, and reduced motion honored automatically. Every model output a family sees was approved by a teacher first.

---

## 1. The legal frame

### 1.1 IDEA

The Individuals with Disabilities Education Act (20 U.S.C. §1400 et seq., regulations at 34 CFR Part 300) governs special education for eligible children. Four parts of it shape this product directly.

**Measurable goals and progress reporting.** 34 CFR §300.320(a)(2)–(3) requires each IEP to state measurable annual goals, *how* progress toward them will be measured, and *when* periodic reports will be provided. This is the exact hole the product fills: teachers are required to produce progress evidence on a schedule and usually assemble it by hand. Dori supplies evidence for that reporting. It does not author the goal and does not decide whether the goal was met.

**Least restrictive environment.** 34 CFR §300.114 requires that, to the maximum extent appropriate, children with disabilities are educated with children who are not disabled, and that removal happens only when the nature or severity of the disability means education in regular classes with supplementary aids and services cannot be achieved satisfactorily. The cohort feature's "complementary strengths" mode exists because of this clause: a teacher needs a defensible way to build mixed groups for shared work. A feature that sorted students with IEPs into their own group would push against the statute's central principle, which is why §5.2 prohibits it outright.

**Supplementary aids and services.** 34 CFR §300.42 defines the aids, services, and supports provided in regular classes that enable participation. Read-aloud, extra time, and simplified directions typically live here. The product implements these as *accessibility preferences*, available to any student, so using one is not a disclosure.

**Confidentiality.** 34 CFR §§300.610–300.626 apply FERPA-level protection to personally identifiable information under IDEA, with additional requirements on access records and destruction. Practical consequence: disability status is need-to-know even inside the school, so it does not appear on a dashboard that a substitute teacher or a specials teacher can open.

### 1.2 Section 504 and the ADA

Section 504 of the Rehabilitation Act of 1973 (29 U.S.C. §794, regulations at 34 CFR Part 104) prohibits disability discrimination by recipients of federal funds. §104.33 requires a free appropriate public education. A 504 plan covers students who have a disability that substantially limits a major life activity but who do not require specially designed instruction, so the population is broader than IDEA's thirteen categories and the plans are usually about access, not curriculum.

Title II of the ADA covers public schools regardless of federal funding. The Department of Justice's 2024 web accessibility rule (28 CFR Part 35, Subpart H) sets **WCAG 2.1 Level AA** as the technical standard for web content and mobile apps of public entities, with compliance dates of April 24, 2026 for public entities serving populations of 50,000 or more and April 26, 2027 for smaller entities and special district governments. The first of those dates has passed.

Consequence for us: WCAG conformance is a legal floor for any district customer, not a nice-to-have. We target WCAG 2.2 AA, which in practice covers the 2.1 AA requirement (2.2 adds success criteria and retires only 4.1.1 Parsing) and gives us the newer criteria that matter most for children: target size, dragging alternatives, and focus appearance.

### 1.3 Endrew F. and the standard of progress

*Endrew F. v. Douglas County School District RE-1*, 580 U.S. 386 (2017), held that a school must offer an IEP "reasonably calculated to enable a child to make progress appropriate in light of the child's circumstances," and rejected a merely *de minimis* standard. The Court emphasized that the IEP team's judgment must be supported by a cogent and responsive explanation.

Consequence for us: "a cogent and responsive explanation" is a design requirement, not a slogan. Every number the product shows a teacher carries its evidence and its reason code, because that teacher may have to defend a decision that cited it. This is the reason the learner model is BKT and logistic regression rather than a neural network: a teacher can explain the former in a meeting.

### 1.4 Privacy

| Law | Applies to | What it forces |
|---|---|---|
| FERPA (20 U.S.C. §1232g, 34 CFR Part 99) | Education records | Vendor access typically runs under the school-official exception, §99.31(a)(1), which requires direct control by the district and use limited to the authorized purpose |
| IDEA confidentiality (34 CFR §§300.610–626) | PII under IDEA | Access records, destruction on request, consent for most disclosures |
| COPPA (16 CFR Part 312) | Under-13 personal information | School consent is workable only for educational use; commercial use of the data is not |
| PPRA (20 U.S.C. §1232h) | Surveys on protected topics | Do not ask children about family, beliefs, or behavior |
| State student privacy laws | Varies | Many states add data-sale prohibitions and deletion timelines beyond FERPA |

Consequence for us: the Bedrock prompt carries a pseudonymous mastery summary and nothing else (PRD §10). No names, no goal text, no notes. During the hackathon everything is synthetic, and the demo says so out loud.

### 1.5 Hard rules that follow

1. No diagnosis, eligibility determination, placement recommendation, or IEP text generation. These are denied topics in the Guardrail, not just an instruction in the prompt.
2. Never ingest the IEP or 504 document. Goal links are short teacher-authored labels.
3. Disability category and IEP/504 status are not inputs to any model, any ranking, or any grouping.
4. Every model output that reaches a family passed a teacher's explicit approval, and the approval is logged.
5. Accessibility features are available to every student, always, without a flag being set.
6. A persistent statement of what the tool does not decide appears on the teacher and parent dashboards.

---

## 2. Instructional frameworks we align to

### 2.1 Universal Design for Learning

CAST's UDL Guidelines 3.0 organize design around three principles: multiple means of **engagement** (the why of learning), **representation** (the what), and **action and expression** (the how). The premise is that variability is normal and predictable, so flexibility should be designed in rather than retrofitted per student.

This is the intellectual basis for the rule in §1.5 that accessibility features are open to everyone. If read-aloud is available only to students with a documented need, the feature itself becomes a disclosure and children stop using it. If it is available to all, a child who needs it is doing what everybody does.

Mapping to the product:

| UDL principle | In Dori |
|---|---|
| Engagement | Choice of quest order where the objective allows, effort-naming feedback, a guide character, no coercive streaks |
| Representation | Read-aloud with word highlighting, text scaling, high contrast, visual and symbolic forms of the same item, hints that restate rather than repeat |
| Action and expression | Keyboard, switch, pointer, and touch paths to the same answer; no drag-only interaction; no handwriting or typing requirement to demonstrate math knowledge |

### 2.2 Multi-tiered systems of support

MTSS/RTI frames instruction in tiers: universal instruction for all (Tier 1), targeted small-group intervention (Tier 2), intensive individualized intervention (Tier 3), with movement driven by progress data. The National Center on Intensive Intervention's data-based individualization model adds the loop that matters here: validated intervention, frequent progress monitoring, diagnostic data when progress stalls, adaptation, repeat.

Dori sits in the Tier 1 and Tier 2 progress-monitoring slot. The check-in produces the frequent measurement; the recommendation proposes an adaptation; the teacher decides. It is not a Tier 3 intervention and should never be described as one.

### 2.3 Explicit instruction and cognitive load

The IES What Works Clearinghouse practice guides for mathematics and reading intervention converge on a short list: explicit and systematic instruction, worked examples, visual representations of the problem, deliberate practice on foundational facts, and motivational strategies that reference effort. Cognitive load theory explains the mechanism: working memory is narrow, so instruction that splits attention across sources, repeats the same content redundantly in two modalities, or loads the screen with decoration spends capacity that should go to the problem.

Design consequences, all of which are already requirements in PRD §13:

- One task per screen. No sidebar of other questions.
- The prompt, the image it refers to, and the choices are visible together. No scrolling between a passage and its question if it can be avoided; if it cannot, the passage stays reachable without losing the question.
- Decoration is subtracted, not added. The guide character occupies a fixed position and does not animate during reading.
- Hints reduce the problem rather than restating the question louder.

A tension worth naming: the redundancy effect in multimedia research suggests that identical on-screen text plus narration can hurt comprehension for fluent readers, while read-aloud tools show a small positive average effect for students with reading disabilities. Both can be true, which is why read-aloud is user-controlled and never automatic.

### 2.4 Accommodation versus modification

This is the distinction the product most easily gets wrong. An **accommodation** changes how a student accesses a task without changing what the task measures. A **modification** changes the construct itself. CCSSO's Accessibility Manual and Chapter 3 of the *Standards for Educational and Psychological Testing* (AERA/APA/NCME, 2014) both frame this as removing construct-irrelevant variance: the goal is to measure the intended skill, not the student's ability to decode the interface.

Reading a math word problem aloud is an accommodation, because decoding is not what the item measures. Reading a reading-comprehension passage aloud is a modification, because decoding is precisely what it measures. The product already encodes this per item (`read_aloud_allowed`), and the rule is worth restating whenever someone proposes "just turn audio on for everything."

The same logic governs hints, which raise the guess probability in the Layer 1 update (see LEARNER_MODEL.md) rather than being ignored, and time, which is unlimited by default because speed is not the construct.

---

## 3. What "disability" means inside our model

The product never stores or reasons about disability categories. But the team needs shared vocabulary for the learner variation it is designing for, because that variation shows up in the interface even though it never shows up in the data.

The frame is **access needs, not categories**. A category does not tell you what a child needs; two students with the same diagnosis routinely need opposite things, and a student with no diagnosis at all may need the same support.

| Access need | How it shows up in a check-in | What the product does | What it must never do |
|---|---|---|---|
| Decoding and reading fluency | Slow starts, misses on items whose math is easy but whose wording is dense | Read-aloud with word highlighting, short sentences, familiar vocabulary | Read a reading passage aloud; count decoding failure as a math miss |
| Working memory | Correct on single-step, misses on multi-step; loses the question while scrolling | One task per screen, question stays visible, no memory-dependent navigation | Impose a timer or penalize returning to the prompt |
| Attention and executive function | Long response times, high variance, abandoned attempts | Chunking, visible "Question 3 of 6", resume where you left off, calm screens | Use response time in the mastery estimate; treat an abandoned attempt as a wrong answer |
| Language and communication | Understands the math, cannot produce the explanation | Selection-based answers, symbol support, no typed justification required | Require expressive language to earn credit |
| Motor control | Mis-taps, accidental double-activation, drag failures | 44 px targets with spacing, no drag-only interaction, no double-click, keyboard and switch paths | Require precision pointing or a gesture with no alternative |
| Sensory regulation | Withdrawal after an animation or a sound | No auto-play, reduced motion honored, muted by default, predictable layout | Use a buzzer, a flash, or a surprise sound for a wrong answer |
| Vision | Misses items that rely on a small visual distinction | Contrast, scaling to 200 percent without loss, alt text, never color alone | Encode the answer in color or in a graphic with no text equivalent |
| Anxiety and prior failure | Stops at the first hard item; refuses hints | Gentle wrong-answer handling, no scores, hints framed as normal, no visible comparison | Show a score, a rank, a red X, or a failure animation |

**Design principle that follows.** Every one of the right-hand columns is a universal feature. None of them is switched on by a flag that says who a child is. This is UDL and it is also the legal posture in §1.5.

---

## 4. Collaboration: the evidence for students with disabilities

Teachers group children constantly, and for a student with an IEP or a 504 plan the stakes of getting it right are higher than for anyone else in the room. The same arrangement that produces the largest gains can also produce isolation inside a room full of people. This section is the evidence base for making collaboration a first-class feature rather than a tab, the conditions that evidence depends on, and the failure modes that make it backfire. §5 turns it into an algorithm.

### 4.1 The case in one paragraph

Structured peer collaboration is one of the better-evidenced instructional arrangements available to a general-education teacher who has students with disabilities in the room. It raises achievement for those students, it appears to cost their classmates nothing and may help them slightly, it raises academic engaged time, it produces social acceptance that pull-out instruction cannot, and on some outcomes it outperforms one-to-one adult support. The qualifier decides everything: none of this follows from seating children at the same table. It follows from structure — a task that cannot be completed alone, a role each child owns, an individual step at the end, and rotation so nobody becomes the permanent helper or the permanent helped. Unstructured group work is where students with disabilities get quietly sidelined, and the research that looks disappointing is mostly research on unstructured group work.

### 4.2 The academic evidence

| Study or line of work | Population | Finding | What it licenses here |
|---|---|---|---|
| Fuchs, Fuchs, Mathes and Simmons (1997), Peer-Assisted Learning Strategies | Students with learning disabilities, low achievers, and average achievers, across dozens of classrooms | All three learner types made greater reading progress than controls in the same schools. The variable was structured reciprocal pairing, not extra time | Structured peer pairs help the identified student *without* costing classmates. This is the closest thing to a direct answer to "is this fair to the other kids" |
| Classwide Peer Tutoring (Greenwood, Delquadri, and colleagues) | At-risk elementary students, followed longitudinally | Higher achievement and substantially higher academic engaged time than conventional instruction, with effects visible in later grades | Collaboration buys engaged time, which is the scarcest resource for a distractible or avoidant learner |
| McMaster and Fuchs (2002), updating Tateyama-Sniezek (1990) | Students with learning disabilities | Effects on achievement were **inconsistent** across studies. The studies that combined group goals with individual accountability were the ones showing benefit | The conditions in §4.6 are not garnish. They are the difference between an effect and no effect |
| Szumski, Smogorzewska and Karwowski (2017), meta-analysis | Classmates *without* special educational needs in inclusive classrooms | Small positive average effect on the achievement of students without special needs | The presence of students with disabilities is not a drag on the class. Have this ready; a principal will ask |
| Ruijs and Peetsma (2009), research review | Both groups in inclusive settings | Effects on peers without disabilities were neutral to positive | Same |
| IES What Works Clearinghouse practice guides | Struggling elementary readers and mathematicians | Peer-assisted and small-group formats appear as recommended practice *alongside* explicit instruction | Collaboration complements explicit instruction. It does not replace it, and a student who has not been taught the skill cannot collaborate their way to it |

The honest summary, and the one to give a judge who pushes: cooperative learning is not automatically good for students with disabilities. *Structured* cooperative learning is. The 2002 review is the important one precisely because it is the least flattering — it found that when you strip out group goals and individual accountability, the benefit for students with learning disabilities becomes unreliable. That is a finding about design, and it is a finding we can build to.

### 4.3 Social outcomes, belonging, and what a check-in cannot measure

Across studies, students with learning and developmental disabilities report lower peer acceptance, fewer reciprocal friendships, and more loneliness than their classmates, including in inclusive settings where they are physically present all day. Physical inclusion is not social inclusion. IDEA's least-restrictive-environment principle (§1.1) is partly aimed at this, and placement alone does not deliver it.

What collaboration adds:

- **Interpersonal attraction.** Johnson and Johnson's meta-analytic work found cooperative structures produce greater liking and acceptance between students with and without disabilities than competitive or individualistic structures do. The mechanism is shared goals, not proximity.
- **Relatedness.** Self-determination theory treats relatedness as a basic psychological need alongside competence and autonomy. A child who does not believe they belong disengages regardless of how well the instruction is designed. For a student who has accumulated years of being the one who gets pulled out, belonging is the binding constraint, not instruction.
- **Authentic practice for goals that are already on the IEP.** Turn-taking, asking for help, disagreeing, repairing a misunderstanding: for many students these are written into the plan as goal areas, and a structured group task is the only place in the school day they get rehearsed for real.

None of this shows up in a mastery estimate. The product should say so rather than implying that the number is the whole picture.

### 4.4 Why it works: five mechanisms

1. **Explaining is learning.** The learning gain in peer work concentrates in *giving elaborated explanations*, not in receiving help (Webb; Roscoe and Chi on tutor learning). This is the single strongest argument for reciprocal roles: if the student with a disability is always the recipient, they are sitting in the seat where the least learning happens.
2. **Engaged time rises.** A student who would disengage from independent seatwork stays in a task that another child is depending on.
3. **The feedback loop shortens.** A peer catches an error in seconds. A teacher circulating a room of 28 reaches a given child every several minutes.
4. **Representation multiplies for free.** A peer restating a problem in child language is UDL's multiple-means-of-representation principle delivered by a person rather than a feature.
5. **Identity shifts.** Contributing something the group needed is different in kind from being helped, and it changes what a child believes they can do. This is why Cohen's "assigning competence" move (§4.8) is in the teacher script and not optional.

### 4.5 Peer support versus adult proximity

This is the finding most likely to change a real decision, so it gets its own subsection.

Giangreco and colleagues (1997), in work usually cited as "Helping or hovering?", documented that close and continuous paraprofessional proximity carried consistent costs: it interfered with peer interaction, separated the student *within* the general education classroom, reduced the general educator's own engagement with that student, and undermined the student's sense of control. Carter and colleagues' peer support research found that students with severe disabilities, supported by trained classmates with adult facilitation, showed substantially more social interaction and at least equivalent academic engagement compared with one-to-one adult support.

The consequence for how we frame this product: a well-structured collaborative arrangement is not a cheaper substitute for adult support. On the social outcomes that inclusion exists to produce, it can be the better intervention. That is the justification for spending real build time on group activities rather than treating them as a bonus feature.

### 4.6 The conditions that make it work

Johnson and Johnson's cooperative-learning research identifies five conditions that separate productive group work from students sitting near each other. Without them, group work reliably degrades into one child doing the task — and per §4.2, this is exactly where the benefit for students with disabilities disappears.

1. **Positive interdependence.** The task cannot be completed by one member alone.
2. **Individual accountability.** Each member's contribution is visible and assessed.
3. **Promotive interaction.** Members explain, question, and help rather than divide and conquer.
4. **Interpersonal and small-group skills.** Turn-taking, disagreement, and asking for help are taught, not assumed.
5. **Group processing.** The group reflects briefly on how it worked.

Consequence for us: the grouping algorithm is the easy half. The *activity template* attached to a cohort has to build in interdependence and individual accountability, or a well-composed group still produces nothing. Every group activity in `data/seed/group_activities.json` should be checkable against these five.

Related finding from Noreen Webb's work on group discourse: what predicts learning is not receiving help but giving *elaborated* explanations, and receiving help only helps when the receiver then applies it. Groups where one student supplies answers produce learning for that student and little for anyone else.

### 4.7 Composition: what the evidence actually says

Two distinctions matter and are constantly conflated.

**Between-class tracking** (assigning students to different classes by measured ability, for the year) has weak achievement evidence and well-documented costs: lower-track classes get less demanding content, expectations drop, and assignment correlates with race and income in ways that have driven decades of litigation and policy. We are not building this and should say so.

**Within-class grouping** (temporary small groups inside one classroom) is a different intervention with better evidence. Lou and colleagues' 1996 meta-analysis in *Review of Educational Research* found a small positive average effect for within-class small-group learning over whole-class instruction, and, importantly, an interaction with composition: lower-achieving students did better in heterogeneous groups, mid-achieving students did somewhat better in homogeneous groups, and higher-achieving students did about the same in either. Slavin's earlier reviews reached a compatible conclusion for elementary mathematics: flexible, skill-based, temporary grouping paired with instruction actually targeted at that skill is the version that works.

The synthesis the framework uses:

> Composition should follow the task, not the child. Homogeneous for targeted practice on one skill; heterogeneous for application, discussion, and collaborative production. Temporary in both cases.

### 4.8 Status, stigma, and the tutor trap

Elizabeth Cohen and Rachel Lotan's Complex Instruction research documents *status generalization*: in a mixed group, students perceived as higher status talk more, are listened to more, and learn more, regardless of the task. Left alone, a heterogeneous group amplifies the gap it was meant to close. Their countermeasures are specific and we adopt two of them:

- **Multiple-ability orientation.** State out loud that the task needs several different abilities and that no one student has them all.
- **Assigning competence.** The teacher publicly names a specific, real contribution from a low-status student.

The related failure mode is the **tutor trap**: repeatedly placing one student as the designated helper and another as the designated helped. It converts a temporary arrangement into an identity, and it takes learning time from the tutor. Peer-Assisted Learning Strategies (Fuchs and Fuchs) avoids this by making tutoring *reciprocal*, with both partners occupying both roles within a session, and by pairing on a rank split rather than pairing the top student with the bottom one.

Two more cautions worth keeping in view:

- **Matthew effects** (Stanovich, 1986): early gaps compound, because the student who reads less gets less practice and falls further behind. An arrangement that quietly gives a student less demanding work every time accelerates this.
- **Labeling.** Children identify the "low group" within days regardless of what it is called. Group names, colors, and visible ordering all leak. This is why students never see the rationale, never see a band, and why group names are neutral nouns.

### 4.9 What we will not do

- Group by disability category, IEP/504 status, or any proxy for them.
- Persist a group beyond the activity it was built for.
- Show a student their band, their rank, or why they are in a group.
- Show a family any other child's data, or the composition logic.
- Reuse a cohort as evidence in a placement, eligibility, or service conversation.
- Let the model, rather than the teacher, finalize a roster.

### 4.10 What the evidence obliges us to build

Each row is a claim from §4.1–§4.8 turned into something that has to exist in the product. A collaborative feature missing these is not a lighter version of the research; it is the version the research says does not work.

| Evidence | Required feature | Where it lives |
|---|---|---|
| Benefit depends on group goals plus individual accountability (§4.2) | Every group activity has a shared artifact that no single member can produce, and an individual closing step completed alone | Activity template; `data/seed/group_activities.json` |
| The learning is in giving explanations, not receiving help (§4.4) | Roles rotate so every student occupies the explaining role; reciprocal pairing for peer practice | §5.7 roles; rank-split pairing in §5.3 |
| Status generalization sidelines the lower-status member (§4.8) | The 0.40 status guard in the cost function, plus a multiple-ability statement and an assigning-competence prompt in the teacher script | §5.5, §5.7 |
| Arrangements repeated become identities (§4.3, §4.8) | Rotation as a cost term, cohort expiry, neutral group names, drift metrics over an 8-week window | §5.5, §5.9 |
| Mixed groups demotivate when scored on absolute correctness (§4.7) | Collaborative games score improvement over each student's own baseline | Game scoring in `apps/web/src/pages/games` and `services/api/app/games` |
| Peer support can beat adult proximity on social outcomes (§4.5) | Collaboration is a primary surface in the student portal, not a hidden tab, and the teacher view treats "ran a group activity" as a first-class action | Student Games tab; teacher dashboard |
| Social gains do not appear in achievement data (§4.3) | Teacher captures a one-tap outcome on the cohort itself — did this grouping work — separate from any mastery change, feeding Layer 4 | Cohort outcome capture |
| Collaboration complements explicit instruction, never replaces it (§4.2) | A student with no recent evidence on the skill is routed to practice, not into a group, via the eligibility gate | §5.4 |

One rule cuts across all of them: **a collaborative feature must never be the place where a student with a disability is visibly the one being helped.** If a screen, a score, a role assignment, or a rationale string makes that legible to the other children, it has undone the thing it was built for.

---

## 5. The smart grouping framework

This expands PRD §12 into something implementable and auditable. The product term stays **activity cohort**, which signals a temporary instructional arrangement rather than a fixed ability group.

### 5.1 Principles

1. **Evidence, not identity.** Composition is computed from demonstrated performance on the selected skill and nothing else.
2. **The task picks the shape.** Similar-need for targeted practice, complementary for application. The teacher chooses the task; the mode follows.
3. **Access profiles shape the activity, not the roster.** If a cohort contains a student who uses read-aloud, the *activity* is chosen or adapted so it works with read-aloud. Access preferences never move a student into or out of a group, because that path turns a preference into a proxy for disability.
4. **Rotation is a first-class constraint.** Any composition rule applied repeatedly becomes a track. Pairing history is an explicit cost term, not an afterthought.
5. **Determinism.** Same inputs, same seed, same rosters. A teacher who regenerates gets an explainable difference, not a reshuffle.
6. **The teacher is the decision-maker.** The output is a proposal with a rationale, editable in full, and every edit is logged.
7. **Everything expires.** A cohort is scoped to one activity and a short window.

### 5.2 Inputs

**Allowed.**

| Input | Source | Why it is allowed |
|---|---|---|
| Mastery estimate on the target skill | Layer 1 BKT posterior | Direct evidence from this student's answers |
| Confidence | Evidence count, trajectory agreement, pattern probability | Prevents grouping on noise |
| Evidence recency and count | Response log | Stale evidence is not evidence |
| Observed pattern label and probability | Layer 3 classifier | Lets complementary mode pair genuinely different approaches |
| Mastery on a second skill | Layer 1 | Required for complementary mode |
| Pairing history | Prior cohorts, last N activities | Rotation |
| Teacher constraints: keep together, keep apart | Teacher input | The teacher knows things the data does not |
| Requested cohort size | Teacher input | |

**Prohibited**, repeated from PRD §12 because it is the part most likely to erode under time pressure: disability or diagnostic category, goal links, IEP or 504 status, race, ethnicity, sex, religion, socioeconomic status, English-learner status, behavior or disciplinary history, attendance, accessibility preferences, response time, and any single overall ability or risk score.

The prohibition on a **single overall score** matters independently. A composite "ability" number is the mechanism by which flexible skill grouping degenerates into tracking, because it is stable across skills and across weeks while a per-skill estimate is not.

### 5.3 Task type determines composition

| Task type | Mode | Composition rule | Size | Basis |
|---|---|---|---|---|
| Targeted practice on one skill | Similar need | Mastery band within one band; max spread 0.25 on the estimate | 3 | Lou et al.: mid-achieving students gain from homogeneous grouping; instruction can be pitched exactly |
| Reciprocal peer practice | Similar need, paired | Rank-split pairing: rank *i* with rank *i + n/2*; both partners occupy both roles | 2 | PALS; avoids the tutor trap by construction |
| Application, discussion, open task | Complementary strengths | At least two distinct pattern labels or strength skills represented; no member more than 0.40 above every other on the task skill | 3–4 | Lou et al.: lower-achieving students gain from heterogeneous grouping; Cohen: the task must need multiple abilities |
| Review game or collaborative build | Complementary, balanced | Equalize group mean on the target skill across groups; score on improvement over each student's own baseline, not absolute correctness | 3–4 | Slavin's team-scoring approach keeps mixed teams motivating and fair |
| Extension | Similar need | Students above 0.80 with medium or high confidence | 2–3 | Matches the existing routing rule in Layer 2 |

The `no member more than 0.40 above every other` rule is the tutor-trap guard. It prevents the arrangement where one student is obviously the expert and the group defers, which is the status dynamic in §4.8.

### 5.4 Eligibility gates

Before composition runs:

1. Fewer than 3 relevant items in the last 14 days, or confidence `low`: excluded, listed as **needs more evidence**, with a one-tap "assign a short quest" action. Never silently placed.
2. No evidence on the second skill in complementary mode: eligible for filler seats only, not for a strength seat.
3. Absent or teacher-excluded students: removed before composition, not after, so group sizes come out right.

The "needs more evidence" state is a feature, not an error. It is the honest answer and it is what keeps a low-confidence estimate from becoming a group assignment.

### 5.5 Cost function

Composition is a search over partitions minimizing a weighted cost. Every term is inspectable, and every term maps to something in §4.

```
cost(G) = Σ_g [ w_fit      · fit_penalty(g, mode)
               + w_repeat   · repeat_penalty(g)
               + w_isolate  · isolation_penalty(g)
               + w_status   · status_penalty(g) ]
        + w_hard · constraint_violations(G)
```

| Term | Similar-need | Complementary | Guards against |
|---|---|---|---|
| `fit_penalty` | Variance of mastery in the group; hard cap at 0.25 spread | Number of missing distinct pattern labels below 2 | A group the activity cannot be pitched to |
| `repeat_penalty` | Jaccard overlap of this group's pairs with pairs from the last N activities (default N = 3), weighted by recency | same | Tracking by accumulation |
| `isolation_penalty` | Charged when a student is the only member from the lowest band present in the class, or shares no prior groupmate with anyone in the group | same | A child repeatedly grouped alone-in-a-crowd |
| `status_penalty` | 0 | Charged proportionally to the gap between the top member and the next, above the 0.40 threshold | The tutor trap and status generalization |
| `constraint_violations` | Hard: keep-apart violated, keep-together broken, size out of range | same | Overriding the teacher |

Default weights: `w_hard` dominant (effectively infinite), then `w_fit` 1.0, `w_repeat` 0.6, `w_status` 0.5, `w_isolate` 0.4. These are starting values, not findings. They are in one config block so a teacher-facing slider ("mix it up more" versus "match the level more closely") can move `w_repeat` against `w_fit` without a code change.

### 5.6 Algorithm

Deterministic, no clustering library, runs in milliseconds for a class of 30.

```
1. Gate       Apply §5.4. Emit the needs-more-evidence list.
2. Seed       Similar need:  sort by (mastery, confidence, student_id) and cut into
                             groups of the requested size; last group absorbs the remainder
                             up to size + 1.
              Complementary: sort by mastery on skill A descending; deal round-robin
                             (snake order) across groups so each group gets one member
                             from each quartile; then fill strength seats from skill B.
3. Improve    Local search: repeatedly evaluate all pairwise swaps between groups, accept
              the swap with the largest cost reduction, stop when no swap improves or after
              200 iterations. Ties broken by student_id so the result is stable.
4. Explain    Emit a rationale from the actual numbers, plus machine-readable reason codes.
5. Expire     Stamp the cohort with the activity id and a TTL.
```

Sorting ties break on `student_id` rather than randomly, so regeneration is reproducible and a teacher who regenerates twice sees the same thing.

Bedrock may rephrase the rationale for readability. It never computes the roster.

### 5.7 Roles and accountability

The roster is half the design. Attached to every cohort activity:

- **Assigned roles** that rotate across activities: reader, checker, recorder, reporter. Roles are assigned by rotation history, not by mastery, so the strongest student is not always the reporter.
- **A shared artifact** that needs every role's contribution, which is the positive-interdependence requirement.
- **An individual step** at the end, completed alone, which is individual accountability. Without it the group's output tells the teacher nothing about any individual.
- **A multiple-ability statement** in the teacher's script: the named abilities this task needs, so the teacher can open by saying no one is good at all of them.
- **A 60-second group processing prompt** at the end: one thing the group did well, one thing to do differently.

### 5.8 Transparency, by audience

| Audience | Sees |
|---|---|
| Teacher | Roster, per-student mastery and confidence, the rationale string, the reason codes, which constraints bound, what changed since last time, an edit and regenerate control |
| Student | The activity, their group's neutral name, their role. Nothing else. No band, no rationale, no ordering |
| Family | Nothing about cohorts. Only the teacher-approved next step for their own child |

Group names are neutral and non-ordinal: `Otter`, `Maple`, `Harbor`. Never `Group 1`, never a color that maps to a level, never a name that persists across activities.

### 5.9 Audit metrics

A grouping feature can satisfy every rule above on any single run and still produce tracking over a term. These metrics run over a rolling 8-week window and are shown to the teacher, not the student.

| Metric | Definition | Flag |
|---|---|---|
| Groupmate diversity | Distinct groupmates ÷ possible groupmates, per student | Bottom decile of the class |
| Partner concentration | Herfindahl index over a student's groupmate distribution | Above threshold: same few partners repeatedly |
| Band persistence | Share of activities where a student was in the lowest-mean group | Above 60 percent |
| Role balance | Distribution of assigned roles per student | Any role never or always held |
| Exclusion rate | Share of activities where a student was "needs more evidence" | Above 30 percent: the check-in cadence is failing that student, not the student failing the check-in |

A separate **disparate-impact review** compares these metrics against disability status and other protected characteristics. This creates a real tension, and it should be stated plainly rather than finessed: auditing for disparate impact requires the protected attribute, but the attribute is prohibited as a model input. The resolution is a separation of duties. The attribute lives with the district, never in the grouping service; the audit runs on the district side over exported metrics; the result is a governance report, never a feature. This is post-hackathon work and should be described as such.

### 5.10 Worked example

Class 4A, skill `fraction_equivalence`, teacher picks a collaborative build task for groups of three.

Eligible: 9 students. Excluded: 3 with fewer than 3 items in 14 days, listed as needs more evidence.

Mastery estimates: 0.91, 0.84, 0.72, 0.68, 0.55, 0.51, 0.44, 0.38, 0.29. Sam (`student-01`) is at 0.55, confidence medium, pattern `visual_only`.

A collaborative build is an application task, so complementary mode. Snake-deal produces `{0.91, 0.51, 0.44}`, `{0.84, 0.55, 0.38}`, `{0.72, 0.68, 0.29}`. The status guard fires on group 3: 0.72 is 0.43 above 0.29, over the 0.40 threshold, but 0.68 is not, so the group passes. Group 1 fails: 0.91 is 0.40 and 0.47 above its members. Local search swaps 0.91 with 0.72, giving `{0.72, 0.51, 0.44}`, `{0.84, 0.55, 0.38}`, `{0.91, 0.68, 0.29}` — which now fails on group 3 by a wider margin, so the swap is rejected and the search instead swaps 0.44 up: `{0.91, 0.68, 0.51}`, `{0.84, 0.55, 0.38}`, `{0.72, 0.44, 0.29}`. All three pass the status guard, pattern coverage is satisfied, and the repeat penalty is checked against the last three activities.

Sam's group rationale, as the teacher sees it:

> Three learners practicing equivalent fractions at difficulty 2–3. Different approaches: one working visually, one working with symbolic notation, one consistent across both. No pair here worked together in the last three activities. Sam has the recorder role this time.

Sam sees: "You're with Harbor today. You're the recorder."

---

## 6. Student portal interface standards

The student portal is the part of the product where the accessibility claim is either true or false. These are requirements with acceptance criteria, not preferences.

### 6.1 The WCAG floor

Target: **WCAG 2.2 Level AA**, plus the AAA criteria listed. The criteria below are the ones that bite hardest for children with disabilities and are the ones to check first.

| Criterion | Level | What it means here |
|---|---|---|
| 1.1.1 Non-text Content | A | Every image, icon, and Capy has a text alternative; decorative art is `aria-hidden` |
| 1.3.1 Info and Relationships | A | Real `<fieldset>`/`<legend>` for a question and its choices, real headings, no div soup |
| 1.4.1 Use of Color | A | Correct/incorrect never signaled by color alone; icon plus text always |
| 1.4.3 Contrast (Minimum) | AA | 4.5:1 body text, 3:1 large text. Check the pastel chips; pastels fail this constantly |
| 1.4.4 Resize Text | AA | Three type sizes, up to 200 percent, no loss of content or function |
| 1.4.10 Reflow | AA | Usable at 320 CSS px wide with no two-dimensional scrolling |
| 1.4.11 Non-text Contrast | AA | 3:1 for the focus ring, buttons, and the step nodes on the path |
| 1.4.12 Text Spacing | AA | Layout survives increased line height, paragraph, letter, and word spacing |
| 2.1.1 Keyboard / 2.1.2 No Trap | A | Everything reachable and escapable by keyboard; this is also the switch-access path |
| 2.2.1 Timing Adjustable | A | No time limits on items. Speed is not the construct |
| 2.2.2 Pause, Stop, Hide | A | Any motion over 5 seconds can be stopped, including the landing animation |
| 2.3.1 Three Flashes | A | Nothing flashes. Confetti is slow, soft, and short |
| 2.3.3 Animation from Interactions | AAA | `prefers-reduced-motion` honored automatically and togglable in the app |
| 2.4.3 Focus Order | A | Focus order follows reading order, including after a dialog closes |
| 2.4.7 Focus Visible | AA | One focus ring, defined once, visible on every control including custom ones |
| 2.4.11 Focus Not Obscured | AA | Capy, the audio bar, and the accessibility bar never cover the focused element |
| 2.5.5 Target Size (Enhanced) | AAA | We hold 44×44 CSS px minimum, 48 for primary answer targets, with spacing |
| 2.5.7 Dragging Movements | AA | Every drag has a single-pointer alternative. The beat game needs this checked explicitly |
| 2.5.8 Target Size (Minimum) | AA | 24×24 absolute floor; we exceed it everywhere |
| 3.1.5 Reading Level | AAA | Student text at or below Grade 3 |
| 3.2.3 / 3.2.4 Consistent Navigation and Identification | AA | The accessibility bar is in the same place on every screen, with the same labels |
| 3.2.6 Consistent Help | A | The hint control is always in the same place |
| 3.3.1 / 3.3.3 Error Identification and Suggestion | A/AA | A wrong answer is described in words and offers a next step |
| 3.3.7 Redundant Entry | A | Never ask a child to re-enter anything |
| 3.3.8 Accessible Authentication | AA | No puzzle, no CAPTCHA, no memorized string as the only path |
| 4.1.2 Name, Role, Value | A | Custom controls expose state; use native elements first |
| 4.1.3 Status Messages | AA | Feedback appears in an `aria-live="polite"` region without stealing focus |

Beyond WCAG, the W3C's *Making Content Usable for People with Cognitive and Learning Disabilities* is the better reference for this population, because WCAG's cognitive coverage is thin. Its objectives map closely to what the PRD already requires: help users understand what things are, find what they need, use clear language, avoid the need to remember, and support focus.

### 6.2 Typography and reading

Drawn from the British Dyslexia Association's Dyslexia Style Guide and standard legibility research. These are defaults, and all of them are overridable by the type-size control.

- **Sans-serif**, generous x-height, unambiguous letterforms. The `l`/`I`/`1` and `b`/`d` distinctions matter more than brand character.
- **Body text at 18 px minimum** for students, larger for the question prompt. Print guidance of 12–14 pt maps to roughly 16–19 px; a child reading at grade level on a classroom device needs the top of that.
- **Line height 1.5**, paragraph spacing at least 2× the font size.
- **Left-aligned, never justified.** Justification creates rivers of white space that break tracking for dyslexic readers.
- **Line length 60–70 characters.** Wider lines lose the return sweep.
- **Off-white background, near-black text.** Pure `#FFFFFF` behind pure `#000000` maximizes contrast but causes visual stress for some readers. The warm off-white canvas the app already uses is the right call. High-contrast mode is a separate, user-chosen theme.
- **No italics for emphasis**; bold instead. No all-caps, no underline except for links.
- **Never rely on red/green** to distinguish anything, including in charts on the teacher side.

### 6.3 Language and tone

- Grade 3 or below for students, checked with a readability measure on the actual strings, not estimated by eye.
- Short sentences, one clause. Active voice. Second person.
- Consistent vocabulary: the same action is always called the same word. "Try" is always "try," never sometimes "submit," "check," or "go."
- No idioms, no sarcasm, no rhetorical questions. Literal language is not only an autism accommodation; it is better for every early reader and every English learner.
- No adult framing on the student screens. The child sees quest, try, practice, next. Never assessment, mastery, score, level, or data.
- Instructions describe the action, not the interface: "Pick the picture that shows the same amount," not "Click the correct radio button below."

### 6.4 Flow and cognitive load

- One task per screen, one primary action per screen.
- Position is stable: the prompt, the choices, the audio control, the hint, and the next action are in the same place on every item.
- Progress is visible and non-threatening: "Question 3 of 6." No countdown, no progress bar that implies speed.
- Pause and resume from anywhere, including after closing the tab. A child who walks away and comes back finds the same question.
- Nothing is destroyed by navigation. Back is safe.
- No infinite scroll, no carousel, no content that moves on its own.

### 6.5 Audio and read-aloud

- Nothing auto-plays. Ever. (WCAG 1.4.2, and a sensory-regulation requirement.)
- One audio control per screen with explicit play, pause, replay, and stop. The same control in the same place.
- **Word-level highlighting synchronized with speech.** The highlight is a background tint with sufficient contrast, not a color change on the text, so it survives high-contrast mode.
- Speech rate is adjustable and the setting persists.
- Read-aloud covers the prompt, every choice, the hint, and the feedback — **except** where `read_aloud_allowed` is false on the item, which is how a reading-comprehension passage is protected (§2.4). The UI states why in child-friendly words: "This one is for your reading eyes."
- Browser speech synthesis is the hackathon stand-in; Polly audio is pre-generated and cached so playback is instant in the demo.
- Audio is never the only channel. Every spoken string is on screen.

### 6.6 Feedback and errors

- **Correct**: specific and effort-naming. "You looked at both pictures carefully." Not "Great job!" repeated forty times, which children discount by the third instance.
- **Wrong**: neutral, informative, immediately actionable. No red X, no buzzer, no failure animation, no sad face. "Not this time. Look at how many pieces are shaded." Then a route: hint, try again, or move on.
- Feedback lands in an `aria-live="polite"` region and does not move focus, so a screen-reader user hears it without losing their place.
- The child never sees a number. Not a score, not a percentage, not a mastery estimate, not a comparison. The practice path shows progress as position, earned from the same estimate the teacher sees, rendered as steps rather than a value.
- No streaks, no leaderboards, no loss-framed mechanics. A streak is a punishment for an absence, and absences correlate with the exact conditions we are trying to support.

### 6.7 Motion, sound, and predictability

- `prefers-reduced-motion: reduce` is honored automatically, and there is also an in-app toggle, because school devices often have the OS setting locked.
- With reduced motion on, transitions become instant. Confetti becomes a static badge. Nothing is lost, only stilled.
- Default animation is slow and small. Nothing bounces, spins, or scales more than slightly.
- The layout never reorders between items. Capy stays in one place.
- No modal appears without the child causing it.

### 6.8 Input: keyboard, switch, touch, AAC

- Full keyboard operability with a visible focus ring, plus a **single-key next flow** so the whole quest can be completed with one action repeated. This is what makes the app usable with a single-switch device.
- No time limits anywhere, which is also a switch-scanning requirement: scanning is slow by nature.
- No drag-only interaction. The beat game and any ordering task need a click-to-select, click-to-place alternative (WCAG 2.5.7).
- No double-click, no long-press, no multi-touch gesture as the only path.
- 44×44 px minimum targets, 48 for answer choices, with at least 8 px of spacing so a tremor does not activate a neighbor.
- Roadmap (PRD FR-30): symbol-supported choices and switch scanning for AAC users. Until then, the keyboard path is the compatibility story and it must actually work.

### 6.9 Collaborative screens

Group activities are where the accessibility work and the collaboration work meet, and where both are easiest to lose. A collaborative game that a child cannot operate excludes them from the exact arrangement §4 says they benefit from most.

- **Every role is operable by every input.** If the recorder role needs typing, or the builder role needs dragging, that role is closed to some children and role rotation quietly stops rotating. Each role needs a keyboard, switch, and pointer path.
- **Turn-taking is explicit and has no clock.** Whose turn it is must be visible, announced to a screen reader through `aria-live`, and never expire. Timed turn-taking excludes switch scanning and slow processing outright.
- **Shared state changes are announced, not just animated.** When another member adds to the shared artifact, a child who cannot see the animation still needs to know it happened.
- **Audio in a shared game is per-student and never forced.** Pre-generated audio plays on the child's own device under their own control. A game that depends on hearing a beat needs a visual and a haptic channel for the same information.
- **No voice requirement.** Nothing in a collaborative task may require speech, since expressive language is a goal area for many of these students, not a prerequisite.
- **Participation is visible to the teacher, never to the group.** The teacher can see who contributed what, because that is the individual-accountability requirement. Children see the shared result, because ranking contributions inside a group rebuilds the status dynamic §4.8 exists to prevent.
- **A child can leave and rejoin.** Dysregulation, a bathroom trip, and a pull-out service all happen mid-activity. Departure must not break the group's task or mark the child.

### 6.10 Testing

Automated checks catch roughly a third of real accessibility problems. They are necessary and not close to sufficient.

1. **Automated**: axe or Lighthouse in CI on every route, zero violations as a merge gate.
2. **Keyboard-only smoke test**: one Playwright test completing a full quest without a mouse, asserting focus visibility at each step. This is already the planned acceptance criterion in code form.
3. **Screen reader**: manual pass with NVDA and VoiceOver on the student quest and the path.
4. **Zoom and spacing**: 200 percent zoom, 320 px viewport, and the text-spacing bookmarklet, with no loss of function.
5. **Contrast**: automated on tokens, manual on the pastel chips and the step nodes.
6. **Reduced motion**: every screen with the OS setting on.
7. **Cold read**: a person who has never seen the app completes a quest with no explanation.

The one that cannot be skipped in a real deployment is testing with actual students with disabilities, and with the assistive technology they actually use. We cannot do that during the hackathon, and the honest framing is that our conformance claim is a conformance claim, not a usability finding.

---

## 7. Teacher portal principles

- **Evidence, then interpretation, then action, in that order.** Never an interpretation without the evidence one click away.
- **Neutral language.** "4 learners need more evidence," "6 learners are ready for extension." Never "struggling," "low," "weak," "behind," "at risk." Deficit language in a UI migrates into how a teacher talks about a child in a meeting.
- **Confidence is always displayed next to an estimate.** A number without its confidence invites a decision it cannot support.
- **Reason codes on every route.** "Moved to prerequisite after two misses below the easy band." This is the *Endrew F.* explanation requirement in interface form.
- **The teacher can always disagree**, and disagreement is a first-class recorded action, not an override buried in a menu. Rejected recommendations are stored with the reason and feed Layer 4.
- **Need-to-know for sensitive fields.** Goal-link markers are visible to the assigned teacher only. Disability status is not in the product at all.
- **A "how this works" panel** in plain language, including the limits, reachable from the dashboard. A teacher who cannot explain the tool cannot defend a decision that cites it.
- **Authorization is server-side and scoped.** A teacher reaches their own classes only. Hiding a control is never the security boundary.

## 8. Family portal principles

- **Plain language, and a lower reading level than feels necessary.** Health and civic communication guidance generally targets grade 6–8 for the general public; IDEA separately requires that prior written notice and procedural safeguards be written so the general public can understand them, and provided in the parent's native language where feasible (34 CFR §300.503(c), §300.504(d)). Our summaries should meet the same bar even though they are not legal notices.
- **Translation is an access requirement, not a feature.** English text is retained alongside the translation so a bilingual family can check it.
- **A jargon glossary.** Every term of art that survives into a family-facing string links to a one-sentence definition. IEP, 504, accommodation, benchmark, present levels.
- **Their child only.** Server-enforced. No class distribution, no rank, no percentile, no other child's anything.
- **Nothing reaches a family that a teacher did not approve.** This is the single most important boundary in the product, because an unreviewed model output landing in a family's hands is the failure mode that ends a district pilot.
- **Denied topics, enforced by Guardrails, not by prompt text:** diagnosis, eligibility, placement, services, medication, prognosis, and comparison to other children.
- **A standing statement**: this tool supports learning and does not make eligibility, placement, or IEP decisions.
- **A rights library** pointing to authoritative sources (IDEA, OCR, the state parent center) rather than our own paraphrase of the law.
- **Family-to-teacher messaging is pairing-enforced server-side.** A parent reaches their own child's teacher and no one else.

## 9. Language guide

| Do not write | Write | Why |
|---|---|---|
| Low group, high group | Activity cohort, group name | Ordinal labels become identities |
| Struggling student, at-risk student | Learner practicing this skill | Deficit framing |
| Special-needs student | Student with a disability, or nothing at all | Person-first is the default in US education; honor stated preference for identity-first |
| Wheelchair-bound, suffers from | Uses a wheelchair, has | Neutral description |
| Failed the quiz | Has not shown this yet | Formative, not terminal |
| The model says the student has a gap in X | The answers show X; the model's pattern label is Y with probability Z | Separates evidence from inference |
| Score, grade, level | Progress, next step | Student-facing rule |
| Normal students, regular kids | Students without IEPs, general education students | |
| Mastered | Consistently showing | "Mastered" overstates what six items can support |

## 10. Open questions for district validation

Listed because a judge or a district reviewer will ask, and the honest answer is better than an improvised one.

1. **Grouping weights are unvalidated.** The defaults in §5.5 are reasoned, not fitted. They need a term of real use and teacher feedback.
2. **The 0.40 status threshold is a guess.** It should be calibrated against observed group discourse, which requires classroom observation we have not done.
3. **Disparate-impact auditing needs a governance home.** §5.9 describes the separation of duties; no district has agreed to it.
4. **Grade 3 reading level is asserted, not measured.** Run a readability pass over the actual strings, and recognize that readability formulas are weak instruments for very short text.
5. **The pattern taxonomy is teacher-reviewed but small.** Five labels for one skill does not generalize.
6. **All fitted parameters come from simulated data.** Stated plainly everywhere, including in the demo.
7. **We have not tested with students with disabilities or with real assistive technology.** Our accessibility claim is conformance against a standard, not evidence of usability.
8. **Read-aloud of generated text** is not covered by the pre-generated Polly cache and needs a latency and quality plan.
9. **Our collaborative activities have not been checked against the five conditions in §4.6.** The evidence in §4.2 is conditional on them, so an activity that fails the check is not supported by the research we are citing. This audit is cheap and should happen before the demo.
10. **We have no measure of whether a grouping worked.** §4.10 proposes a one-tap cohort outcome; until it exists, the drift metrics in §5.9 measure fairness of composition but not benefit.

## 11. References

**Law and regulation**

- IDEA statute and regulations — https://sites.ed.gov/idea/statuteregulations
- 34 CFR §300.320, Definition of individualized education program — https://sites.ed.gov/idea/regs/b/d/300.320
- 34 CFR §300.114, LRE requirements — https://sites.ed.gov/idea/regs/b/b/300.114
- 34 CFR §§300.610–300.626, Confidentiality of information
- Section 504 of the Rehabilitation Act, 29 U.S.C. §794; 34 CFR Part 104
- *Endrew F. v. Douglas County School District RE-1*, 580 U.S. 386 (2017) — https://www.supremecourt.gov/opinions/16pdf/15-827_0pm1.pdf
- DOJ ADA Title II web and mobile accessibility rule (2024), 28 CFR Part 35 Subpart H — https://www.ada.gov/resources/2024-03-08-web-rule/
- FERPA — https://studentprivacy.ed.gov/
- COPPA, FTC children's privacy guidance — https://www.ftc.gov/business-guidance/privacy-security/childrens-privacy

**Standards and frameworks**

- W3C, Web Content Accessibility Guidelines 2.2 — https://www.w3.org/TR/WCAG22/
- W3C, Making Content Usable for People with Cognitive and Learning Disabilities — https://www.w3.org/TR/coga-usable/
- CAST, UDL Guidelines 3.0 — https://udlguidelines.cast.org/
- AERA, APA, and NCME, *Standards for Educational and Psychological Testing* (2014), Ch. 3 on fairness and accessibility
- CCSSO, *Accessibility Manual* — accommodation versus modification, and read-aloud policy
- British Dyslexia Association, Dyslexia Style Guide

**Instructional evidence**

- IES What Works Clearinghouse practice guides, mathematics and reading intervention in the elementary grades — https://ies.ed.gov/ncee/wwc/practiceguides
- National Center on Intensive Intervention, data-based individualization — https://intensiveintervention.org/
- IRIS Center, Vanderbilt (OSEP-funded modules) — https://iris.peabody.vanderbilt.edu/

**Collaboration and inclusion for students with disabilities**

- Fuchs, D., Fuchs, L. S., Mathes, P. G., and Simmons, D. C. (1997). Peer-assisted learning strategies: making classrooms more responsive to diversity. *American Educational Research Journal*, 34(1), 174–206.
- McMaster, K. N., and Fuchs, D. (2002). Effects of cooperative learning on the academic achievement of students with learning disabilities: an update of Tateyama-Sniezek's review. *Learning Disabilities Research and Practice*, 17(2), 107–117.
- Tateyama-Sniezek, K. M. (1990). Cooperative learning: does it improve the academic achievement of students with handicaps? *Exceptional Children*, 56(5), 426–437.
- Greenwood, C. R., Delquadri, J. C., and Hall, R. V. (1989). Longitudinal effects of classwide peer tutoring. *Journal of Educational Psychology*, 81(3), 371–383.
- Giangreco, M. F., Edelman, S. W., Luiselli, T. E., and MacFarland, S. Z. C. (1997). Helping or hovering? Effects of instructional assistant proximity on students with disabilities. *Exceptional Children*, 64(1), 7–18.
- Carter, E. W., Cushing, L. S., Clark, N. M., and Kennedy, C. H. (2005). Effects of peer support interventions on students' access to the general curriculum and social interactions. *Research and Practice for Persons with Severe Disabilities*, 30(1), 15–25.
- Szumski, G., Smogorzewska, J., and Karwowski, M. (2017). Academic achievement of students without special educational needs in inclusive classrooms: a meta-analysis. *Educational Research Review*, 21, 33–54.
- Ruijs, N. M., and Peetsma, T. T. D. (2009). Effects of inclusion on students with and without special educational needs reviewed. *Educational Research Review*, 4(2), 67–79.
- Roscoe, R. D., and Chi, M. T. H. (2007). Understanding tutor learning: knowledge-building and knowledge-telling in peer tutors' explanations and questions. *Review of Educational Research*, 77(4), 534–574.
- Deci, E. L., and Ryan, R. M. (2000). The "what" and "why" of goal pursuits: human needs and the self-determination of behavior. *Psychological Inquiry*, 11(4), 227–268. (Relatedness as a basic need.)

**Grouping and group dynamics**

- Johnson, D. W., and Johnson, R. T. Cooperative learning: the five essential elements. Cooperative Learning Institute.
- Lou, Y., Abrami, P. C., Spence, J. C., Poulsen, C., Chambers, B., and d'Apollonia, S. (1996). Within-class grouping: a meta-analysis. *Review of Educational Research*, 66(4), 423–458.
- Slavin, R. E. (1987). Ability grouping and student achievement in elementary schools: a best-evidence synthesis. *Review of Educational Research*, 57(3), 293–336.
- Cohen, E. G., and Lotan, R. A. (2014). *Designing Groupwork: Strategies for the Heterogeneous Classroom* (3rd ed.). Teachers College Press.
- Fuchs, D., and Fuchs, L. S. (2005). Peer-Assisted Learning Strategies: promoting word recognition, fluency, and reading comprehension in young children. *The Journal of Special Education*, 39(1), 34–44.
- Webb, N. M. (2009). The teacher's role in promoting collaborative dialogue in the classroom. *British Journal of Educational Psychology*, 79(1), 1–28.
- Vygotsky, L. S. (1978). *Mind in Society*. Harvard University Press. (Zone of proximal development.)
- Stanovich, K. E. (1986). Matthew effects in reading. *Reading Research Quarterly*, 21(4), 360–407.

**Cognition and multimedia**

- Sweller, J., Ayres, P., and Kalyuga, S. (2011). *Cognitive Load Theory*. Springer.
- Mayer, R. E. (2021). *Multimedia Learning* (3rd ed.). Cambridge University Press.
- Wood, S. G., Moxley, J. H., Tighe, E. L., and Wagner, R. K. (2018). Does use of text-to-speech and related read-aloud tools improve reading comprehension for students with reading disabilities? A meta-analysis. *Journal of Learning Disabilities*, 51(1), 73–84.

**Related documents in this repository**

- [PRD.md](PRD.md) — product requirements, especially §12 cohorts, §13 dashboards, §14 accessibility, §16 responsible AI
- [LEARNER_MODEL.md](LEARNER_MODEL.md) — the five-layer model and what it never uses
- [TECH_STACK.md](TECH_STACK.md) — implementation choices
