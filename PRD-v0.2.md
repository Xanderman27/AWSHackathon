# Product Requirements Document: Adaptive Learning Platform

**Working title:** To be determined (candidates in §25)
**Version:** 0.2
**Date:** September 15, 2026
**Status:** Hackathon MVP definition
**Team:** Four people with mixed technical experience (Tyler, Holden, Matt, Alex)
**Product vision:** K–12 support across Math, Science, English Language Arts, and Reading for students with IEPs and 504 plans, and for the teachers and families who support them
**Hackathon focus:** Elementary-school learners, synthetic data, and a five-minute demonstration

---

## What changed from v0.1

v0.1 was a solid adaptive-assessment PRD, but it had drifted away from the original problem: **families of students with IEPs and 504 plans cannot see progress between meetings, and the loop between teacher, student, and parent never closes.** v0.2 re-anchors the product on that problem and closes requirement and technology gaps:

| Area | Change |
|---|---|
| Problem statement | Rewritten around IEP/504 progress visibility and IDEA's periodic progress-reporting requirement, not generic "assessments are stressful." |
| Positioning | New §3.1 explains why this is not another IXL/Khan-style adaptive tool and names the wedge: evidence that feeds IEP progress reports and parent understanding. |
| Goal links | New concept (§9.4): a teacher can link a curriculum skill to a plain-language goal label they own. Parents see progress on "the goals we agreed on." The IEP document itself never enters the system. |
| Original idea items restored | Hints during assessment (pre-authored, logged), AAC/switch-access considerations, adaptive at-home practice, "which activities worked" outcome capture as the seed for the future ML loop, inclusion cohorts (students with and without disabilities). |
| Parent side | Added conference agenda, plain-language rights and resources library (P1), and family-language translation (P1). |
| Teacher side | Added quest assignment (was implied, never specified), activity-outcome capture, and observation evidence. |
| Learner model | Bayesian Knowledge Tracing chosen with concrete parameters, thresholds, and confidence rules. |
| Cohorts | Deterministic algorithm specified for both modes. |
| Standards | Concrete standard IDs for the demo (CCSS 4.NF.A.1 and RI.4.2) and a `standard_framework` metadata field so state frameworks can be added later. |
| Technology | Streamlit flagged as a conflict with the accessibility promise; recommended split is a React front end plus a Python FastAPI service. Knowledge Base provisioning fallback, Polly pre-generation, structured output via tool use, and model selection added. |
| Delivery | Added a cut line (what to drop first if time runs out) and day-by-day build order. |
| Data model | Added ParentStudentLink, ClassAssignment, GoalLink, ConferenceSlot, ActivityOutcome, AccessibilityPreference, ItemHint. |
| Users | Removed the administrator role. Roster and corpus setup are operational tasks done with scripts in the MVP. |
| Corpus and activities | Knowledge base restricted to tiered trusted sources (standards, district guidelines, federally funded guidance, teacher-reviewed templates) with provenance metadata and an ingestion gate. Activity generation is template-first: retrieve an approved template, fill it from retrieved ideas, verify every field is grounded. |

---

## 1. Executive summary

The product is an accessible learning platform for elementary students who receive special-education services under an IEP or a Section 504 plan. It uses short, playful assessments to estimate a learner's current understanding, adapts after every response, and turns the results into teacher-reviewable learning activities, classroom cohort suggestions, and plain-language progress summaries that parents can actually understand.

The core promise is **closing the loop**. Today a parent may meet a teacher once or twice a year; report cards do not show progress on the specific skills an IEP targets; and the information that would help a family advocate for their child is scattered across federal statutes, district PDFs, and Reddit threads. This product gives the teacher a continuous, low-effort evidence stream, gives the parent a private window into that evidence, and gives the student an experience that responds to them.

The system is a formative support tool. It must not diagnose a disability, determine eligibility or placement, write or modify an IEP, assign grades, or make disciplinary decisions. Recommendations and cohorts do not reach students until a teacher reviews and approves them. The teacher is always the authority.

## 2. Product vision and positioning

### Vision

Make every short learning check-in feel safe and playful, give teachers a clear, evidence-backed next step for each learner, and let families see progress between meetings instead of waiting for the next one.

### Product promise

> A child gets a learning experience that responds to them. An educator stays in control of what happens next. A family sees the progress, not just the grade.

### Product principles

1. **Strengths before deficits.** Describe what a learner understands and what to practice next; never label a child as low, behind, or incapable.
2. **Teacher authority.** AI proposes; educators approve, edit, or reject. The teacher spends the most time with the student and understands them best.
3. **Explainability.** Every recommendation, cohort, and parent summary identifies the assessment evidence and learning objective behind it.
4. **Accessible by default.** Read-aloud, high contrast, adjustable type, keyboard and switch access, large targets, and plain language are core functionality, not settings.
5. **Privacy by design.** Collect the least data needed, isolate records by role, keep IEP documents and diagnoses out of the system, and use only synthetic student data in the hackathon.
6. **No permanent tracks.** Cohorts are temporary, activity-specific, revisable, and hidden from parents and other students.
7. **Continuity.** The parent relationship persists across the whole K–12 span even as teachers change, so a family never starts from zero.

## 3. Problem statement

Students with IEPs and 504 plans are served by a process that is legally rigorous but practically opaque to families:

- **Progress is invisible between meetings.** IDEA requires the IEP to state how progress toward annual goals will be measured and when periodic reports will be provided (34 CFR §300.320(a)(3)), but in practice those reports are often a checkbox on a quarterly form. Grade reports do not show skill-level growth.
- **Information is unevenly distributed.** Whether a family understands their rights under IDEA, Section 504, and FERPA depends heavily on income, language, education, and geography. Families with the resources to hire advocates get different outcomes.
- **Generalized disability guidance is insufficient.** Curriculum and interventions are often designed for a disability category rather than for the individual student, even though two students with the same label may need very different support.
- **The teacher is overloaded.** Teachers already hold the most accurate picture of the student, but turning that picture into individualized activities, defensible progress evidence, and family communication is manual, repetitive work.
- **Assessments are stressful or inaccessible.** Many formative checks are timed, text-heavy, and visually noisy, so they measure anxiety and access barriers as much as understanding.

The platform should close the gap between assessment, teacher action, and family understanding without automating any high-stakes educational decision.

### 3.1 Positioning and differentiation

There are three adjacent categories, and the product deliberately sits between them:

| Category | Examples | What they do well | Gap this product fills |
|---|---|---|---|
| Adaptive practice platforms | IXL, Khan Academy, i-Ready | Large item banks, adaptive difficulty | Not designed around IEP goals, no teacher-approval loop for AI content, weak family transparency, accessibility is often bolted on |
| IEP management and progress-monitoring tools | Frontline IEP, SpedTrack, Goalbook | Compliance paperwork, goal banks | Teacher enters data by hand; nothing generates the evidence; parents rarely get a usable view |
| Parent communication apps | ClassDojo, TalkingPoints, Remind | Messaging, translation | No connection to learning evidence; "how is my child doing" is still a free-text question |

**The wedge:** the student's accessible check-ins produce evidence automatically; the teacher approves what to do with it; the family sees it in plain language, tied to the goals they agreed on. No one in the adjacent categories does all three, and the non-profit structure lets the product go to under-resourced districts first rather than to the districts that can already afford advocates.

## 4. Goals and non-goals

### Goals

- Assess skill understanding through short, playful, accessible interactions.
- Update a learner's estimated mastery after each response and select an appropriate next question.
- Show teachers class-level patterns and evidence for each student's progress, including evidence on teacher-linked goals.
- Recommend teacher-approved activities grounded in curriculum objectives and a curated activity structure.
- Suggest either similar-need or complementary-strength activity cohorts based on the teacher's selected mode, including inclusion cohorts that mix students with and without IEPs.
- Give parents a simple, private, plain-language view of their child's progress, a conference-request workflow, and trustworthy information about their rights.
- Capture whether an approved activity worked, so the product can learn over time under proper governance.
- Demonstrate meaningful use of Amazon Web Services, an explainable learner model, generative AI, retrieval, guardrails, and human approval.

### Non-goals

- Diagnosing a disability or medical, behavioral, or psychological condition.
- Determining special-education eligibility, placement, services, accommodations, or IEP content.
- Storing or parsing the IEP or 504 document itself.
- Replacing standardized, diagnostic, or teacher-administered assessments.
- Automatically assigning grades, discipline, interventions, coursework, or permanent ability groups.
- Comparing a child publicly with classmates.
- Providing legal advice to families (the rights library links to official sources and is informational).
- Training a production-grade predictive model on real student records during the hackathon.
- Supporting every K–12 grade and subject with production-ready content in the MVP.

## 5. Scope

### Long-term product scope

- Grades K–12, with a parent relationship that persists across grade and teacher changes.
- Math, Science, English Language Arts, and Reading.
- District-approved standards and curricula, with state framework support (for example CCSS, TEKS, Virginia SOL) as metadata.
- Student, teacher, and parent/guardian roles; students may belong to multiple classes (for example a general-education class and a resource room). Roster and corpus setup are operational tasks, not a user role (§6).
- Longitudinal progress, teacher-created content, school-system integrations, and multilingual family communication.
- An outcome feedback loop that learns which activities help which learners, under district governance.

### Hackathon MVP

The architecture and data model should support the long-term scope, but the demo will use:

- Elementary visual design, optimized for Grade 4.
- Two representative skill paths:
  - Math: equivalent fractions (CCSS.MATH.CONTENT.4.NF.A.1) with prerequisite "fractions as parts of a whole" (3.NF.A.1).
  - Reading: main idea and supporting details in informational text (CCSS.ELA-LITERACY.RI.4.2).
- A synthetic classroom of 12 students, of whom roughly 5 have goal links (representing IEP/504 students in an inclusion classroom).
- One short adaptive quiz containing 5–8 questions, multiple choice with optional image support.
- A pre-approved question bank (about 20 items per skill path) tagged by subject, standard, skill, prerequisite, difficulty, and one pre-authored hint.
- One curated activity template per demonstrated skill, with Bedrock generating age-appropriate details.
- Teacher, parent, and student views.
- In-app conference requests rather than full calendar integration.

## 6. Users and permissions

| User | Primary need | Allowed access |
|---|---|---|
| Student | Complete an accessible, encouraging learning activity | Own current quiz, hints, feedback, and teacher-approved activities |
| Teacher | Understand needs and choose the next instructional action | Assigned classes, class summaries, individual evidence, goal links, recommendations, cohorts, conference requests, audit history |
| Parent/guardian | Understand their child's progress, know their rights, and communicate with the teacher | Only linked children, family-facing progress summaries, goal progress in plain language, approved at-home suggestions, conference requests, rights library |

There is no administrator user. Rosters, parent–student links, the standards framework, and the approved corpus are loaded by the team with setup scripts during the hackathon. In a district deployment those tasks would be done by school staff through a configuration tool or an SIS integration (§27); that is an operational concern, not a product user.

### Permission rules

- A parent account must never retrieve another child's record, even through a copied or modified URL or API call. Enforcement is in the data-access layer.
- Students do not see mastery percentages, rankings, peer scores, cohort rationales, goal-link labels, or disability-related data.
- Parents do not see classmates, cohorts, peer comparisons, or teacher-only notes.
- Teachers can view only assigned classes and students.
- Goal-link labels are teacher-authored, visible to the teacher and the linked parent, never sent to a model, and never shown to students.
- All recommendation, cohort, and goal-link changes are recorded with actor, timestamp, original proposal, and edits.

## 7. Core user journeys

### 7.1 Student completes an adaptive quiz

1. The student opens a teacher-assigned learning quest.
2. Accessibility preferences (read-aloud, high contrast, larger type, reduced motion) are already applied from the stored profile and can be changed at any time.
3. The system presents one question at a time with large, clear controls and no timer.
4. The student may ask for a hint. The hint is pre-authored and teacher-reviewed; hint use is logged as evidence.
5. After each response, the mastery model updates the student's skill estimate.
6. The next item becomes easier, harder, or targets a prerequisite skill based on the evidence.
7. The student receives brief, encouraging feedback without any ability label.
8. If the student leaves, the quest resumes where they stopped.
9. At completion, the student sees a celebration and a teacher-safe summary such as "You practiced finding fractions that are the same amount."

### 7.2 Teacher assigns a quest, reviews evidence, and approves an activity

1. The teacher assigns a skill quest to the class or to selected students.
2. The teacher opens the class dashboard showing completion, strengths, and skills needing support.
3. The teacher opens a student record and sees item-level evidence, hint use, mastery estimates, confidence, trend, and progress on any linked goal.
4. The platform proposes an activity based on the target skill and a curated activity structure, with retrieved-source cards.
5. The activity includes a rationale, curriculum source, estimated duration, materials, and accessibility notes.
6. The teacher edits, approves, or rejects it. Only an approved activity becomes visible to the student or parent.
7. After the activity runs, the teacher records a one-tap outcome (helped, partly helped, did not help, not tried). This becomes evidence and seeds the future outcome-learning loop.

### 7.3 Teacher creates activity cohorts

1. The teacher selects a learning objective, cohort size, and mode (similar need or complementary strengths).
2. The platform proposes cohorts based on recent, relevant learning evidence and rotation history. Students with and without goal links are eligible on equal terms; goal links are never an input.
3. Each proposal states why the students were grouped and displays confidence or insufficient-data warnings.
4. The teacher can drag students between cohorts, regenerate, approve, or dismiss.
5. Students see only a team name and instructions, never the rationale.
6. The cohort expires after the activity or a teacher-defined period.

### 7.4 Teacher links a skill to a goal

1. The teacher opens a student with an IEP or 504 plan and adds a goal link: a short plain-language label they write themselves (for example "Goal 2: identify equivalent fractions with models") attached to one or more curriculum skills.
2. The teacher chooses whether the parent can see the goal label.
3. From then on, the student's evidence on those skills is summarized under that goal for the teacher and, if enabled, the parent.
4. When writing the periodic IEP progress report required by IDEA, the teacher can export the evidence summary. The product does not write the report and does not touch the IEP.

### 7.5 Parent reviews progress and requests a conference

1. The parent signs in and selects one of their linked children.
2. The parent sees "What we practiced," "Current strengths," "What comes next," and, if enabled, "Progress on goals," all in plain language and, when configured, in the family's language.
3. The parent can open the rights and resources library for plain-language explanations of IEPs, 504 plans, progress reports, FERPA record access, and discipline protections, each linking to the official source.
4. The parent selects an available conference time or proposes alternatives, and adds an optional agenda ("I'd like to talk about reading at home").
5. The request remains pending until the teacher confirms it. Both parties see the status in the application.

## 8. Functional requirements

Priority definitions: **P0** is required for the judged demo; **P1** is valuable if time remains; **P2** is post-hackathon.

| ID | Priority | Requirement |
|---|---:|---|
| FR-01 | P0 | Support distinct student, teacher, and parent experiences using synthetic accounts and role-aware data filtering enforced in the data layer. |
| FR-02 | P0 | Let a teacher assign a skill quest to a class or selected students. |
| FR-03 | P0 | Deliver a 5–8 item quiz from a pre-approved, metadata-tagged item bank, resumable if interrupted. |
| FR-04 | P0 | Recalculate estimated mastery and select the next item after every response. |
| FR-05 | P0 | Offer one pre-authored, teacher-reviewed hint per item; log hint use as evidence. |
| FR-06 | P0 | Provide read-aloud, high-contrast mode, font-size control, and reduced motion throughout the student flow, persisted per student. |
| FR-07 | P0 | Honor per-item accommodation rules (for example, whether the reading passage itself may be read aloud) so read-aloud does not silently change what a reading item measures. |
| FR-08 | P0 | Show encouraging feedback and avoid rankings, deficit labels, countdowns, and public scores. |
| FR-09 | P0 | Show teachers class completion, skill distribution, and individual progress with item-level evidence, hint use, confidence, and trend. |
| FR-10 | P0 | Retrieve approved curriculum, misconception, accessibility, and activity-template sources with metadata filters, then generate activity details from that retrieved context. |
| FR-11 | P0 | Require explicit teacher approval before a generated recommendation is published. |
| FR-12 | P0 | Suggest temporary cohorts in either similar-need or complementary-strength mode using a deterministic, explainable algorithm. |
| FR-13 | P0 | Require explicit teacher approval before a cohort is published and allow manual editing. |
| FR-14 | P0 | Let a teacher create a goal link (plain-language label attached to skills) and choose parent visibility. |
| FR-15 | P0 | Show parents only their linked child's strengths, growth, approved next steps, visible goal progress, and conference requests. |
| FR-16 | P0 | Let a teacher publish available conference slots; let a parent request a slot or propose alternatives with an optional agenda; let the teacher accept, reject, or propose a new time. |
| FR-17 | P0 | Provide a rationale, assessment evidence, and visible retrieved-source citations for every recommendation and cohort suggestion. |
| FR-18 | P0 | Log assessment completion, AI proposal, teacher decision, cohort change, goal-link change, and conference-status change. |
| FR-19 | P0 | Handle insufficient or conflicting evidence by asking for more assessment evidence instead of asserting mastery. |
| FR-20 | P0 | Let a teacher record a one-tap outcome for an approved activity. |
| FR-21 | P0 | Provide a demo-reset action that restores the synthetic dataset to its scripted starting state. |
| FR-22 | P1 | Provide a parent-facing rights and resources library: static, curated, plain-language pages linking to official IDEA, Section 504, and FERPA sources. |
| FR-23 | P1 | Translate parent-facing summaries into a family-selected language (Amazon Translate or Bedrock), with the English source retained. |
| FR-24 | P1 | Let a teacher add an observation evidence note ("observed in class today: used fraction strips correctly") that counts toward confidence but is never sent to a model. |
| FR-25 | P1 | Export a goal-progress evidence summary (PDF or printable page) for teacher use in IEP progress reporting. |
| FR-26 | P1 | Use Amazon Cognito for real authentication and role claims. |
| FR-27 | P1 | Provide an at-home practice mode: a shorter, teacher-approved quest a parent can start with the child. |
| FR-28 | P1 | Let teachers author or import standards-aligned question banks. |
| FR-29 | P1 | Support all four target subjects within the elementary grade band. |
| FR-30 | P2 | Support switch-access scanning and symbol-supported answer choices for students who use AAC. |
| FR-31 | P2 | Integrate with district SIS/LMS, email, and calendar systems after security and legal review. |
| FR-32 | P2 | Outcome-learning loop: use activity outcomes and later evidence to rank activity templates, under district governance and fairness review. |

## 9. Adaptive assessment and learner model

### 9.1 Model choice

Use **Bayesian Knowledge Tracing (BKT)** per skill. It is explainable, needs no training data, updates in constant time, and its parameters read as plain English to a teacher. A language model never scores answers or computes mastery.

Per-skill parameters (initial values for the demo; teacher-visible in the "how this works" panel):

| Parameter | Meaning | Default |
|---|---|---|
| p_init | Probability the student already knows the skill before evidence | 0.30 |
| p_learn | Probability of learning the skill after each opportunity | 0.15 |
| p_guess | Probability of a correct answer without knowing (4-choice items) | 0.20 |
| p_slip | Probability of a wrong answer while knowing | 0.10 |

Modifiers: a correct answer after a hint is treated as weaker evidence (p_guess raised to 0.35 for that update). Response time is logged but never used to adjust mastery in the MVP, because timing penalizes exactly the students the product serves.

### 9.2 Thresholds and confidence

| Mastery estimate | Interpretation shown to teacher | Selection behavior |
|---|---|---|
| below 0.40 | "Building foundations" | Route to prerequisite items if two consecutive misses |
| 0.40–0.80 | "Practicing" | Stay on skill, target items near the estimate |
| above 0.80 | "Ready for extension" | Raise difficulty or offer extension item |

Confidence is a function of evidence count and agreement: fewer than 3 relevant items is **low**; 3–5 is **medium**; 6 or more with consistent results is **high**. Contradictory patterns (alternating correct and incorrect at the same difficulty) cap confidence at medium and trigger one more item.

### 9.3 Item metadata and selection policy

Each item includes grade range, subject, standard framework and standard ID, skill and prerequisite skill, difficulty (1–5), correct answer and scoring rule, permitted accessibility formats (including whether the passage may be read aloud), one pre-authored hint, a teacher-reviewed explanation, and approval status.

Selection policy:

1. Keep the student within the teacher-assigned objective.
2. Choose the unseen approved item whose difficulty is closest to the current estimate mapped onto the 1–5 scale, targeting roughly 70 percent expected success.
3. If two consecutive incorrect responses occur below difficulty 2, route to the prerequisite skill and record the route reason for the teacher.
4. If mastery exceeds 0.80 with medium or high confidence, raise difficulty or move to an extension item.
5. If evidence is sparse or contradictory, present another item and display low confidence.
6. Never use disability category, goal links, race, sex, socioeconomic status, behavior, or discipline data to select difficulty.

Demo determinism: the item bank and seed are fixed, so the scripted learner produces the same path every run.

### 9.4 Goal links

A goal link is a teacher-owned record: `{student_id, label, skill_ids[], parent_visible, created_by, created_at}`. The label is free text written by the teacher. The product never ingests the IEP document, never suggests goal wording, and never sends labels to a model. Goal links exist so evidence can be summarized in the language the family already knows from their IEP meeting.

### 9.5 How the MVP demonstrates ML and AI

- **Learner modeling:** BKT updates after every interaction and drives the adaptive path.
- **Generative AI:** Amazon Bedrock generates activity details and plain-language explanations from grounded, approved source material.
- **Retrieval:** Curriculum standards and activity structures are retrieved from an Amazon Bedrock Knowledge Base with metadata filters.
- **Human-in-the-loop:** Teachers approve all generated recommendations and cohorts and record outcomes.
- **Learning loop (roadmap):** Outcome capture is the training signal for a future model that ranks activities by demonstrated effectiveness.

Describe this as an adaptive learner model plus grounded generative AI, not as a clinically validated diagnostic model.

## 10. Retrieval-augmented generation workflow

### Purpose

RAG grounds personalized content in trusted curriculum and teacher-reviewed instructional resources supplied by the school or district. It is not a generic document chatbot. Its MVP job is to turn a demonstrated learning need into an evidence-backed draft activity that a teacher can inspect, edit, and approve.

### Required end-to-end flow

1. The deterministic mastery service identifies a target skill, evidence confidence, and observed response pattern.
2. The application constructs a retrieval query without a student name, goal-link label, diagnosis, or other identifying information.
3. The application queries an Amazon Bedrock Knowledge Base using metadata filters for grade, subject, skill, document type, audience, language, and approval status.
4. The knowledge base returns a small set of relevant chunks: the curriculum objective, prerequisite, common misconception, approved activity structure, and accessibility strategy.
5. The application passes the retrieved chunks and a minimal pseudonymous mastery summary to the Bedrock Converse API, using a tool definition whose input schema is the activity schema so the model's output is structured.
6. The application validates the returned JSON against the schema.
7. The teacher sees the draft alongside the supporting assessment evidence and source cards for the retrieved documents.
8. The teacher edits, approves, or rejects the draft. Only the approved version can reach a student or parent.

### MVP knowledge-base corpus

Use a small, high-quality corpus of 20–30 focused documents. Include curriculum standards and objectives, skill prerequisite maps, common misconception guides, teacher-approved individual and collaborative activity templates, accessibility and instructional strategies, parent-facing curriculum explanations, and approved at-home activities. Each source covers one concept or reusable pattern.

### Corpus provenance: trusted sources only

The knowledge base is the product's source of truth for what an activity may say. Every document must trace to a trusted origin, and the origin must be visible to the teacher on the source card. Allowed origins, in order of preference:

| Tier | Origin | Examples |
|---|---|---|
| 1 | Published learning standards | Common Core State Standards; a state framework such as TEKS or Virginia SOL |
| 2 | District or school-board curriculum and teaching guidelines | Adopted curriculum scope and sequence, district instructional guides, board-approved intervention menus |
| 3 | Federally funded or nationally recognized instructional guidance | What Works Clearinghouse practice guides (IES), IRIS Center modules (Vanderbilt, OSEP-funded), National Center on Intensive Intervention, CAST Universal Design for Learning guidelines |
| 4 | Educator-authored templates reviewed by a certified teacher | The team's own activity templates, each marked with the reviewer and date |

Not allowed: uncited web pages, forum posts, commercial worksheets of unknown origin, and any AI-generated text that has not been reviewed by an educator and marked `approved: true`.

Each document carries provenance metadata in addition to the retrieval fields below:

```json
{
  "source_org": "IES What Works Clearinghouse",
  "source_title": "Assisting Students Struggling with Mathematics: Intervention in the Elementary Grades",
  "source_url": "https://ies.ed.gov/ncee/wwc/PracticeGuide/26",
  "source_tier": 3,
  "reviewed_by": "certified-teacher-01",
  "reviewed_on": "2026-09-16"
}
```

A source manifest (one CSV or JSON file in the repository) lists every document with these fields. The ingestion script refuses any document missing a tier, URL or citation, reviewer, or `approved: true`. For the hackathon, the team writes the Tier 4 templates and adapts Tier 1–3 material into short, focused documents with citations back to the original.

### Retrieval metadata

```json
{
  "grade": 4,
  "subject": "math",
  "standard_framework": "CCSS",
  "standard_id": "4.NF.A.1",
  "skill_id": "fraction_equivalence",
  "document_type": "activity_template",
  "audience": "teacher",
  "approved": true,
  "language": "en",
  "version": "2026.1"
}
```

Bedrock Knowledge Bases read metadata from a sidecar `<file>.metadata.json` next to each S3 object; the ingestion script must generate these. Required filter behavior: retrieve only approved material; match subject and target skill; respect grade band; separate teacher-, parent-, and student-facing material; prefer the current version and language; return no recommendation when no sufficiently relevant approved source is available.

### Generation input

Student performance remains in the structured application data store, not in the vector knowledge base. The generation request receives only minimal learning evidence:

```json
{
  "learner_ref": "student-07",
  "target_skill": "fraction_equivalence",
  "mastery_estimate": 0.42,
  "confidence": "medium",
  "hints_used": 2,
  "observed_pattern": "Recognizes visual equivalence but struggles with symbolic notation"
}
```

Do not include student names, parent contact information, disability labels, goal-link labels, IEP content, observation notes, or free-form private notes in retrieval queries or model prompts.

### Required generated output

The response must validate against a schema containing target skill and learning objective; activity title, duration, materials, and steps; accessibility options; a check-for-understanding prompt; an evidence-based rationale; retrieved source identifiers and titles; confidence or insufficient-evidence state; and `status: draft` until teacher approval.

### RAG boundaries

RAG may help create activities, feedback explanations, family-friendly summaries, translations, and instructions for an already proposed cohort. It must not score answers, calculate mastery, decide cohort membership, enforce permissions, confirm conferences, diagnose a learner, propose eligibility, placement, or IEP changes, or generate an unreviewed live assessment item or hint for immediate student use.

### Failure and fallback behavior

- If retrieval returns no relevant approved source, display "More source material is needed" and do not generate.
- If generated JSON fails validation, retry once with the same sources, then fall back to the underlying approved template.
- If generated text makes a claim unsupported by a retrieved source, omit the claim and flag the draft for review.
- If Guardrails block a request or response, show the teacher a neutral "content could not be generated" state and fall back to the template.
- If Bedrock is unavailable, preserve assessment results and let the teacher open the retrieved template directly.
- Log the retrieval query, filters, returned source IDs, model ID, guardrail result, generated draft, and teacher decision.

### RAG evaluation

Create a golden test set of 8–10 queries covering both skill paths, including two negative cases (wrong grade, parent audience). For each, define the expected target skill and at least one expected source document. Measure: expected source in top three; every displayed citation supports its claim; grade, subject, audience, and approval filters prevent cross-boundary retrieval; unsupported or no-result cases trigger the fallback; a teacher can understand the rationale.

## 11. Activity recommendation requirements

### Template-first generation

An activity recommendation is never written from scratch. It is always an instance of an approved activity template retrieved from the knowledge base, filled in with details that are themselves grounded in retrieved sources. The model's job is to adapt, not to invent.

The recommendation service works in this order:

1. **Retrieve the template.** Query the knowledge base for `document_type: activity_template` matching the target skill, grade, and audience. If none is returned, stop and show the no-source fallback.
2. **Retrieve supporting ideas.** Query for the matching curriculum objective, prerequisite map, misconception guide, and accessibility strategy. These are the "ideas" the model may draw on.
3. **Fill the template.** Pass the template, the supporting chunks, and the minimal mastery summary to Bedrock with the template's field structure as the tool schema. The model fills the fields: title, theme, worked example, step wording, materials list, accessibility notes, check-for-understanding prompt.
4. **Verify grounding.** Each filled field must map to at least one retrieved chunk ID. Fields that cite nothing are replaced with the template's default text and the draft is flagged for teacher attention.
5. **Present.** The teacher sees the filled activity, the template it came from, and a source card for every retrieved document with its origin, tier, and link.

### Template structure

Every activity template in the corpus has: title pattern, target grade band and skill, learning objective (quoted from the standard), estimated duration, materials, step-by-step instructions with placeholders the model may fill, accessibility options, check-for-understanding prompt, source standard reference, source provenance (§10), and a list of which fields are teacher-editable and which are locked.

### Generation rules

- Bedrock may vary wording, theme, examples, and difficulty of examples within the template's placeholders. It may not add steps, remove the check for understanding, change the learning objective, or alter locked fields.
- Retrieved sources must be in the model context, and the output must cite them by chunk ID.
- Output must validate against the template's schema before display.
- The system must not invent a standard, accommodation, diagnosis, or IEP requirement.
- A recommendation must show which answers and target skills contributed to it.
- Low-confidence results recommend additional observation or another short quest, not a definitive intervention.
- Generated content is draft until teacher approval, and the teacher's edits are stored alongside the original.

### MVP template set

Four templates, two per skill path, all Tier 4 (educator-authored, teacher-reviewed) and each citing Tier 1–3 sources:

| Skill | Individual template | Collaborative template |
|---|---|---|
| Equivalent fractions (4.NF.A.1) | Fraction strips and number line matching | Fraction equivalence card sort in a cohort of three |
| Main idea and details (RI.4.2) | Passage annotation with a "main idea, three details" organizer | Shared read and "headline the paragraph" cohort activity |

## 12. Activity cohort requirements

"Activity cohort" is the product term. It signals a temporary instructional arrangement rather than a fixed ability group.

### Modes

**Similar need:** students currently practicing the same skill at a compatible difficulty level.

**Complementary strengths:** students with different demonstrated strengths relevant to a collaborative task, without making one child responsible for teaching another. This is also the **inclusion mode**: it is how a general-education teacher builds mixed cohorts of students with and without IEPs for shared activities, supporting the least-restrictive-environment principle in IDEA without any student being identified.

### Deterministic algorithm (MVP)

Inputs: per-student mastery and confidence on the selected skill (and a second skill for complementary mode), evidence recency, teacher-selected cohort size, prior cohort pairings, and teacher-entered constraints (keep apart, keep together).

1. Exclude students with fewer than 3 relevant items in the last 14 days; list them as "needs more evidence."
2. Similar need: sort eligible students by mastery estimate and cut into cohorts of the requested size, then apply a rotation penalty that swaps adjacent members if the pair was together in the last two cohorts, respecting teacher constraints.
3. Complementary strengths: for each cohort, pick one student with high confidence and mastery above 0.7 on skill A, one with the same on skill B, and fill remaining seats with students in the practicing range on either skill, again applying rotation and constraints.
4. Emit a rationale string per cohort from the actual numbers ("all three are practicing equivalent fractions at difficulty 2–3; none were grouped together last week").

Bedrock may rephrase the rationale for readability but the calculation is deterministic and auditable.

### Prohibited inputs

Disability or diagnostic category, goal links, IEP or 504 status, race, ethnicity, sex, religion, socioeconomic status, behavior or disciplinary history, and any single overall ability or risk score.

### Safeguards

Minimum evidence threshold; "insufficient evidence" state; teacher-facing explanation for every cohort; manual edit, regeneration, and dismissal; rationale and peer performance hidden from students and parents; expiry after one activity or a short period; never reused as a placement recommendation.

## 13. Dashboards

### Teacher dashboard

- Class completion and participation.
- Skill distribution by curriculum objective.
- Class strengths and areas for additional practice, in neutral language ("4 learners need more evidence," "6 learners are ready for extension").
- Student list with trend, confidence indicators, and a goal-link marker visible only to the teacher.
- Individual item-response history including hint use and route reasons.
- Goal-link editor and goal-progress summary.
- Draft, approved, and rejected recommendations, with outcome capture on approved ones.
- Cohort builder with mode selector and editable cohorts.
- Conference slot publisher and pending requests with parent agendas.
- Audit history.
- A "how this works" panel explaining the learner model and its limits in plain language.

### Parent dashboard

- Child selector limited to linked children.
- "What we practiced," "Current strengths," "What comes next."
- "Progress on goals" when the teacher has enabled a visible goal link.
- Progress over time without class rank or peer comparison.
- Only teacher-approved learning activities or at-home suggestions.
- Conference-request form with agenda and current status.
- Rights and resources library (P1).
- Language selector (P1).
- A persistent statement that the tool supports learning and does not make eligibility, placement, or IEP decisions.

### Student experience

- Playful quest framing with a guide character; one task per screen.
- Visible read-aloud, contrast, type-size, and reduced-motion controls.
- Hint button with a friendly, non-judgmental label.
- Large response targets and clear focus states.
- Calm, specific encouragement.
- No streak penalty, leaderboard, timer, or failure animation.

## 14. Accessibility requirements

Production target is WCAG 2.2 Level AA. The hackathon demo must visibly include:

- Amazon Polly text-to-speech for questions, answer choices, hints, and feedback, with play, pause, replay, and stop controls, pre-generated for the item bank and cached in S3 so playback is instant.
- Per-item accommodation rules so a reading-comprehension passage is read aloud only when the item permits it.
- High-contrast mode that does not rely on color alone.
- Font-size controls that do not break layout.
- Keyboard navigation with visible focus, and a single-key "next" flow that is compatible with switch-access devices.
- Screen-reader labels for all interactive elements.
- Large touch targets and generous spacing.
- Plain language and short instructions; images with alt text.
- Reduced-motion behavior when motion is not essential.
- No auto-playing audio.

Roadmap: symbol-supported answer choices and switch scanning for AAC users (FR-30). Accessibility preferences follow the user across sessions but are never used to infer a disability or change academic expectations.

## 15. Parent–teacher conference scheduling

1. Teacher publishes available slots.
2. Parent selects a slot or proposes alternatives, with an optional agenda.
3. The system creates a pending request.
4. Teacher accepts, rejects, or proposes a new time.
5. The application records the final status and shows it to both parties.

Optional agentic demonstration: a Bedrock tool-use flow can translate "find a time after 4 p.m. next week" into calls to `list_available_slots` and `create_conference_request`. The interface must show the chosen time and obtain explicit parent confirmation before creating the request; teacher confirmation is still required. This is the first item on the cut line (§23.4).

## 16. Responsible AI, safety, and privacy

### Required product boundaries

- Display a clear statement that the system supports formative learning and does not make diagnostic, eligibility, placement, or IEP decisions.
- Never ingest the IEP or 504 document. Goal links are teacher-authored labels only.
- Do not send names, contact details, goal labels, observation notes, or free-form teacher notes to the model.
- Use synthetic records only during the hackathon.
- Require teacher approval of recommendations and cohorts.
- Store the prompt context, retrieved source identifiers, generated output, model ID, guardrail result, and teacher decision for auditability.
- Apply Bedrock Guardrails with PII filtering, harmful-content controls, prompt-attack protection, and denied topics covering diagnosis, eligibility, placement, and medication.
- Reject student or parent prompts that attempt to retrieve another learner's data.
- Define retention: the demo store is wiped on reset; production retention would follow district policy.

### Legal and policy posture

Do not claim the prototype is "FERPA compliant," "COPPA compliant," or suitable for IEP decision-making. A production deployment would require district legal, privacy, security, accessibility, and special-education review, and would typically operate under FERPA's school-official exception with a district data agreement. IDEA makes IEP goals, progress measurement, services, and placement part of the formal IEP process; this product supplies supporting evidence for teachers and families and does not replace that process.

Official references:

- [IDEA statute and regulations](https://sites.ed.gov/idea/statuteregulations)
- [IDEA: Individualized Education Programs, 34 CFR §300.320](https://sites.ed.gov/idea/regs/b/d/300.320)
- [IDEA discipline provisions guidance](https://sites.ed.gov/idea/idea-files/dcl-implementation-of-idea-discipline-provisions)
- [FERPA](https://www2.ed.gov/policy/gen/guid/fpco/ferpa/index.html)
- [U.S. Department of Education Student Privacy resources](https://studentprivacy.ed.gov/)
- [FTC Children's Privacy resources](https://www.ftc.gov/business-guidance/privacy-security/childrens-privacy)
- [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/)

## 17. Proposed AWS architecture

### 17.1 Front-end decision (changed from v0.1)

v0.1 proposed Streamlit for all three experiences. That conflicts with the product's central promise. Streamlit re-renders the whole page on every interaction, gives no control over focus management or ARIA labeling, makes custom audio controls and one-task-per-screen layouts awkward, and cannot reliably meet the keyboard-only and visible-focus acceptance criteria in §21. Accessibility is the demo, so the front end must be able to deliver it.

**Recommended default:** a single React front end (Vite, TypeScript, plain CSS variables for contrast and type scaling) with three role routes, talking to a Python FastAPI service that owns the mastery model, cohort algorithm, Bedrock calls, and data access. Python stays for everything AI-related so the Bedrock workstream is unaffected.

**Fallback if no team member is comfortable with React:** Streamlit for the teacher and parent dashboards (data tables and forms are where it is strong) and a small hand-written HTML/JavaScript student quiz page served by FastAPI. Do not build the student experience in Streamlit.

### 17.2 Diagram

```text
Student / Teacher / Parent
           |
   React web app (Vite + TypeScript), role routes
           |  HTTPS / JSON
   FastAPI service (Python)
   |------------------------------------------------|
   | mastery model (BKT)  | cohort algorithm        |
   | authorization layer  | audit log               |
   | recommendation svc   | scheduling svc          |
   |------------------------------------------------|
        |                |                  |
   Bedrock            Bedrock KB         Amazon Polly
   Converse API       (S3 corpus +       (pre-generated
   + Guardrails       metadata           audio in S3)
                      filters)
        |
   DynamoDB (demo: local JSON/SQLite adapter behind the same repository interface)
```

### 17.3 Service responsibilities

| Service | Responsibility |
|---|---|
| Amazon Bedrock Converse API | Activity generation, family-friendly explanations, translation, optional tool-use scheduling assistant. Use an Anthropic Claude model available in the account via the `anthropic.` Bedrock model prefix (Claude Sonnet 5 for quality; Claude Haiku 4.5 if latency or quota requires). Force structured output by defining the activity schema as a tool. |
| Amazon Bedrock Knowledge Bases | Retrieve curriculum standards and approved activity structures with metadata filters. Default vector store is OpenSearch Serverless; if the Workshop Studio account cannot provision it or it takes too long, use the S3 Vectors store option, or fall back to a local index built with Bedrock Titan Text Embeddings and NumPy behind the same retrieval interface and filter logic. |
| Amazon Bedrock Guardrails | PII filtering, harmful-content controls, prompt-attack protection, denied topics. |
| Amazon Polly | Neural voice read-aloud, pre-generated per item and cached in S3; live synthesis only for generated content. |
| Amazon Translate | Parent-facing translation (P1); Bedrock can substitute. |
| Amazon DynamoDB | Synthetic profiles, attempts, mastery state, goal links, approvals, cohorts, outcomes, conference requests. |
| Amazon S3 | Curated corpus with metadata sidecars, cached audio. |
| Amazon Cognito | Authentication and role claims (P1). |
| Amazon CloudWatch | Application errors, latency, and audit events. |
| Hosting | Run locally for the judged demo; optional AWS Amplify Hosting for the front end and App Runner for FastAPI if time allows. Keep a recorded backup video. |

Direct `boto3` calls from the FastAPI service are acceptable. Separate the service functions (mastery, retrieval, generation, authorization, storage) into modules with interfaces so each can be swapped or hosted separately later.

## 18. Core data model

| Entity | Important fields |
|---|---|
| User | Pseudonymous user ID, role, display name |
| ParentStudentLink | Parent ID, student ID, relationship, active flag |
| Class | Class ID, teacher ID, grade, name |
| ClassMembership | Class ID, student ID (a student may be in several classes) |
| StudentProfile | Student ID, grade band; no diagnosis, no IEP status |
| AccessibilityPreference | Student ID, read-aloud, contrast, type size, reduced motion, language |
| CurriculumSkill | Skill ID, subject, grade range, standard framework, standard ID, prerequisites |
| AssessmentItem | Item ID, skill, difficulty, prompt, choices, image and alt text, answer rule, accommodation rules, approved status |
| ItemHint | Item ID, hint text, reviewed-by |
| ClassAssignment | Assignment ID, class or student IDs, skill, assigned by, due window |
| Attempt | Attempt ID, student ID, assignment ID, timestamps, completion state, resume pointer |
| ItemResponse | Attempt ID, item ID, response, correctness, hint used, response time, route reason |
| MasteryState | Student ID, skill ID, estimate, confidence, evidence count, last updated |
| GoalLink | Goal ID, student ID, label, skill IDs, parent visible, created by |
| ObservationEvidence | Student ID, skill ID, teacher note, date (never sent to a model) |
| ActivityTemplate | Template ID, skill, structure, materials, accessibility options, source |
| Recommendation | Student ID, target skill, evidence IDs, retrieved source IDs, generated draft, status, teacher edits, model ID, guardrail result |
| ActivityOutcome | Recommendation ID, outcome (helped, partly, did not, not tried), recorded by, date |
| CohortProposal | Class ID, objective, mode, members, rationale, confidence, expiry, status |
| ConferenceSlot | Teacher ID, start, end, status |
| ConferenceRequest | Parent ID, teacher ID, student ID, slot or proposed times, agenda, status |
| AuditEvent | Actor, action, object ID, before/after state, timestamp, model metadata |

## 19. Non-functional requirements

- **Performance:** next quiz item within two seconds from the item bank; AI-generated activity drafts under eight seconds; read-aloud playback under one second from cache.
- **Reliability:** if Bedrock or the knowledge base is unavailable, students can finish the quiz and teachers see deterministic results and the approved template.
- **Security:** authorization enforced in the data-access layer on every query, keyed by role and link tables, not by hiding interface components.
- **Explainability:** no recommendation or cohort can be approved without a visible evidence-based rationale.
- **Accessibility:** core student tasks work with keyboard input, text scaling, and read-aloud enabled.
- **Teacher effort:** reviewing evidence and approving an activity for one student should take under two minutes; this is the constraint that keeps the loop closed.
- **Observability:** log errors, model latency, retrieval sources, guardrail interventions, and approval outcomes without logging sensitive content.
- **Resettability:** one command restores the scripted synthetic state for repeated demos.

## 20. Success metrics

### Hackathon validation metrics

- 100 percent of scripted quiz paths adapt after a change in demonstrated mastery.
- 100 percent of generated recommendations cite a known skill and approved template.
- At least one expected approved source appears in the top three retrieval results for every golden-path query.
- Zero unapproved, wrong-audience, or wrong-grade documents appear after metadata filtering in scripted tests.
- 100 percent of recommendations and cohorts require teacher approval before publication.
- 100 percent of parent test accounts are blocked from non-linked student records, tested by direct API call.
- All four accessibility controls work during the live demo, and one reading item demonstrates the passage-read-aloud rule.
- All proposed cohorts provide an understandable rationale and expiry.
- Fallback paths work when evidence is insufficient, retrieval is empty, or Bedrock output fails validation.
- Teacher path from opening a student to an approved activity completes in under two minutes.
- The end-to-end demonstration completes in under five minutes.

### Future outcome measures

Student completion and voluntary re-engagement; teacher time from assessment to approved next step; teacher acceptance, edit, and rejection rates; activity outcome rates by template; parent comprehension of strengths, next steps, and goal progress; parent-initiated conference rate; accessibility task-completion across assistive technologies; fairness review of recommendation and cohort outcomes across relevant populations, performed only with appropriate governance and consent. These evaluate usability and decision support; they do not establish clinical or educational efficacy.

## 21. Acceptance criteria

### Adaptive quiz

- Given a student answers two appropriately difficult items correctly, when the next item is selected, then it targets the same skill at greater complexity or an extension skill.
- Given a student misses two consecutive low-difficulty items, when the model updates, then the next item targets the prerequisite and the teacher view shows the route reason.
- Given a student uses a hint and then answers correctly, when mastery updates, then the update is smaller than for an unaided correct answer and the hint is visible in the teacher's evidence.
- Given evidence is contradictory or sparse, when the assessment ends, then confidence is labeled low and no definitive recommendation is made.
- Given a student closes the quiz mid-way, when they return, then they resume at the same item.

### Accessibility

- Given read-aloud is enabled, when a new item loads, then the student can play, pause, and replay the question and choices.
- Given a reading item whose passage is marked not-read-aloud, when read-aloud is enabled, then the question and choices are read but the passage is not, and the interface says why in plain language.
- Given high-contrast mode or a larger font is selected, when the student continues the quiz, then the preference persists and the layout remains usable.
- Given a keyboard-only user, when they navigate the quiz, then every interactive control has a visible focus state and can be activated without a pointer.

### Teacher approval and goal links

- Given an AI-generated activity exists, when the teacher has not approved it, then it is absent from student and parent views.
- Given the teacher edits and approves an activity, when the student opens approved activities, then the edited version appears and an audit event records the decision.
- Given the teacher records an outcome for an approved activity, when the teacher views the student, then the outcome appears with the activity in the evidence timeline.
- Given a teacher creates a parent-visible goal link on two skills, when the parent views the child, then a "Progress on goals" section shows the label and plain-language progress on those skills only.
- Given a goal link exists, when a recommendation is generated, then the request payload sent to Bedrock contains no goal label.

### Retrieval-augmented generation

- Given a Grade 4 fraction-equivalence need, when the recommendation service queries the knowledge base, then results are filtered to approved Grade 4 math sources for the target skill and audience.
- Given relevant sources are retrieved, when Bedrock generates the draft, then the output includes valid source identifiers, conforms to the schema, and remains in draft status.
- Given no sufficiently relevant approved source is retrieved, when a recommendation is requested, then the system shows the no-source fallback and does not call the model.
- Given a filled activity draft, when it is displayed, then every field that differs from the template default cites at least one retrieved chunk, and every source card shows the document's origin, tier, and link.
- Given a document in the corpus lacks a source tier, citation, reviewer, or approval flag, when ingestion runs, then the document is rejected and named in the ingestion log.
- Given a parent-facing explanation is requested, when retrieval runs, then teacher-only documents and information about other students are excluded.

### Cohorts

- Given similar-need mode, when cohorts are proposed, then each cohort is tied to a shared current objective and shows its evidence rationale.
- Given complementary-strength mode, when cohorts are proposed, then the rationale identifies task-relevant complementary strengths without assigning peer-teacher roles.
- Given a student has fewer than three relevant items, when cohorts are proposed, then that student appears under "needs more evidence" rather than in a cohort.
- Given the teacher changes a cohort, when it is approved, then students see only the team and activity and the edit is logged.

### Parent access and scheduling

- Given a parent is linked to one child, when they request another student ID through the API, then the request is denied with no data returned.
- Given a parent requests an available slot with an agenda, when the teacher accepts it, then both dashboards show the confirmed status and the teacher sees the agenda.

## 22. Five-minute judging demonstration

| Time | Demonstration |
|---:|---|
| 0:00–0:25 | State the problem and promise: families of students with IEPs cannot see progress between meetings; accessible check-ins become teacher-controlled next steps and plain-language family updates. |
| 0:25–1:25 | Student takes several quiz items; turn on read-aloud, high contrast, and larger type; use a hint once; show the path routing to a prerequisite and then recovering. |
| 1:25–2:15 | Teacher dashboard: class summary, one student's evidence with hint use and route reason, mastery trend, confidence, and the goal link the teacher created. |
| 2:15–3:05 | Trigger the RAG workflow; show retrieved curriculum, misconception, and activity-template source cards; generate the grounded draft, edit one detail, approve it, and record an outcome from a "previous" activity. |
| 3:05–3:50 | Toggle between similar-need and complementary-strength cohorts; show rationale, "needs more evidence," move one student, and approve. |
| 3:50–4:30 | Parent view: only the linked child; "Progress on goals" in plain language; open the rights library briefly; submit a conference request with an agenda. |
| 4:30–5:00 | Close with safeguards, AWS architecture, and the path from Grade 4 to K–12, four subjects, and the outcome-learning loop. |

### Demo story

One synthetic learner, "Sam," is a Grade 4 student with a goal link on equivalent fractions. Sam's first responses reveal the gap, Sam uses a hint on a visual item and then improves. The teacher sees the evidence, approves a hands-on fraction-strip activity, and places Sam in a temporary inclusion cohort. Sam's parent, who missed the last conference because of a work schedule, sees the goal progress in plain language and books a time with an agenda. One story, start to finish.

## 23. Delivery plan for four team members

### 23.1 Workstreams

**Workstream A: Student experience and accessibility**
Build the React visual system and quiz flow; implement read-aloud (Polly cache), contrast, type scaling, reduced motion, hints, resume, and keyboard behavior; connect the adaptive item-selection endpoint.

**Workstream B: Learner model and synthetic data**
Define skills, prerequisites, item metadata, hints, and 12 synthetic learner profiles including Sam's scripted path; implement BKT, confidence, routing, and the deterministic cohort algorithm; write the golden test scenarios and fallback behavior; own demo reset.

**Workstream C: Bedrock and grounded generation**
Build the 20–30 document corpus with metadata sidecars; provision the Knowledge Base with the local-index fallback; implement Converse calls with tool-based structured output, validation, citations, and Guardrails; implement recommendation generation, parent-summary generation, and optional conference tool use; run the RAG golden test set.

**Workstream D: Teacher and parent views, integration, and story**
Build FastAPI routes with the authorization layer and audit log; build teacher and parent dashboards, goal links, approval workflow, outcome capture, cohort editor, and conference scheduling; own integration, the one-pager (Tyler's problem-section graphs feed this), presentation, and backup video.

### 23.2 Build order

1. **Day 1 morning:** repository skeleton, data model, synthetic data, one deterministic end-to-end path (assign quest, take quiz, see evidence) with the local store.
2. **Day 1 afternoon:** accessibility controls in the student flow; teacher evidence view; goal links; corpus and Knowledge Base ingestion in parallel.
3. **Day 1 evening:** Bedrock-generated activity draft with validation, citations, approval, and fallback.
4. **Day 2 morning:** cohorts with both modes and editing; parent view; conference scheduling; authorization tests.
5. **Day 2 afternoon:** outcome capture, demo reset, rights library if time, polish, rehearsal with a timer, backup video.

### 23.3 Integration rules

- One shared JSON schema file for the activity draft, used by both the FastAPI validator and the React form.
- The mastery service and cohort algorithm are pure functions with unit tests so Workstream A and D can integrate against fixtures before Workstream B is finished.
- Every Bedrock call goes through one module with a `DEMO_OFFLINE` flag that returns cached drafts.

### 23.4 Cut line

If by midday on day 2 the core path is not reliable, drop in this order:

1. Agentic conference assistant (keep manual slot selection).
2. Rights library and translation.
3. Complementary-strengths mode (keep similar-need).
4. Live Bedrock generation in the demo (use cached, previously generated drafts and say so).
5. Cognito (already P1).

Never cut: accessibility controls, teacher approval gate, parent isolation test, goal links, demo reset.

## 24. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scope is too broad | Keep K–12 and four subjects as the architecture vision; demonstrate two Grade 4 skill paths; enforce the cut line. |
| Product reads as "another adaptive quiz app" | Lead the demo with the family problem and the goal link; show the parent view, not just the teacher view. |
| Goal links look like IEP data in the system | Labels are teacher-authored, optional, never modeled, never shown to students, and clearly documented as not the IEP. |
| Cohorts stigmatize students | Temporary cohorts, neutral names, hidden rationale, rotation, expiry, teacher control, goal links excluded as inputs. |
| Generated content is inaccurate | Ground in approved sources, validate structured output, show citations, require teacher approval. |
| Assessment appears diagnostic | Formative language, visible uncertainty, explicit prohibitions, "how this works" panel. |
| Child data is exposed | Synthetic data only, minimal model context, data-layer authorization, direct-object access tests. |
| Accessibility is cosmetic | React front end with real focus management; controls in the primary demo path; test keyboard, scaling, contrast, and audio before visual polish. |
| Read-aloud invalidates reading items | Per-item accommodation rules; demo one item that shows the rule working. |
| Knowledge Base provisioning stalls | Local embedding index behind the same interface; start provisioning first thing on day 1. |
| Bedrock latency or failure breaks the demo | Preloaded item bank, deterministic scoring, cached drafts under `DEMO_OFFLINE`, transparent fallback. |
| Five-minute demo becomes a feature tour | One learner story from quiz through teacher action and parent follow-up; rehearse with a timer. |

## 25. Decisions still needed

| Decision | Recommended default |
|---|---|
| Product name | Keep a working title until the core flow works. Candidates that fit the loop-closing promise: **Bridge**, **Loop**, **Stepping Stones**, **Compass**. Check trademarks before printing anything. |
| Front end | React (Vite, TypeScript) unless no one can build it; then Streamlit for dashboards and hand-written HTML for the student quiz. Decide on day 1 within the first hour. |
| Demo grade and topics | Grade 4; equivalent fractions (4.NF.A.1); main idea and details (RI.4.2). |
| Visual theme | Warm "learning quest" with animal or nature guides; no babyish language. |
| Cohort size | Three students. |
| Mastery model | BKT with the §9.1 defaults. |
| Bedrock model | Claude Sonnet 5 via Converse; Haiku 4.5 as latency fallback; whichever the Workshop Studio account exposes. |
| Vector store | OpenSearch Serverless if it provisions in under 30 minutes; otherwise S3 Vectors or the local fallback. |
| Authentication | Synthetic role accounts first; Cognito only after the full flow works. |
| Scheduling | In-app request and teacher confirmation; no external calendar. |
| Rights library content | Four pages: what an IEP is, what a 504 plan is, progress reports and your right to records (FERPA), discipline protections. Each links to the official source and states it is informational, not legal advice. |

## 26. Definition of done for the hackathon

The MVP is done when one synthetic student can complete an accessible adaptive quiz with a hint; the results update an explainable mastery state; the teacher can create a goal link, inspect evidence and citations, approve a grounded activity, record an outcome, and edit and approve a cohort; a linked parent can view only that child, see goal progress in plain language, and request a conference with an agenda; a parent account is provably blocked from other students at the API; and the entire story can be demonstrated reliably in five minutes with an offline-safe fallback.

## 27. Roadmap beyond the hackathon

1. **Outcome-learning loop.** With enough activity outcomes and follow-up evidence, rank activity templates by demonstrated effectiveness per skill and evidence pattern. Requires district governance, consent, and fairness review before any model is trained on real records.
2. **Continuity across years.** Parent relationship and goal-progress history persist as the student changes teachers and schools within a district.
3. **Teacher-authored content.** Item banks, hints, and activity templates authored or imported by teachers, with the same approval metadata.
4. **AAC support.** Symbol-supported choices, switch scanning, and integration with common AAC vocabularies.
5. **State standards and district setup.** Metadata-driven support for TEKS, Virginia SOL, and other frameworks, plus a configuration tool or SIS integration so district staff can manage rosters, links, and the approved corpus without engineering help.
6. **Integrations.** SIS roster sync, LMS, email, and calendar after security and legal review.
7. **Student companion.** A constrained, teacher-configured helper that offers hints and encouragement during practice (not assessment), built only after the pre-authored hint model proves out.
