# Personalised practice

The top navigation and dashboard link to `/recommendations`, which opens Recommended for you. `/subject-test` opens Choose a topic. Both offer Recommended for you, Choose a topic and Quick revision. Students choose a 5/15/30-minute guide (up to 3/8/16 questions). Subject/chapter bank totals are not shown in this screen; session progress remains visible. Time is an estimate, not an exam countdown.

## Selection and evidence

`POST /api/subject-tests` accepts `mode`, optional `subject_code`/`chapter_id`, and `duration_minutes`. Existing subject/count requests continue to work. Topic mode requires a subject. A chapter must belong to that subject.

Selection uses at most the current student's latest 500 question responses from submitted attempts, retaining the newest observation per distinct question and up to five answered questions per subtopic. Subject-only legacy mock summaries cannot establish topic weaknesses and are not used as evidence. Skips do not count as wrong answers. Repeated attempts at the same question do not inflate the evidence count.

- At least three distinct answers and two errors: practise the concept, targeting an easier difficulty.
- Last recorded answer at least seven days ago: revision.
- At least three correct answers with usable timing, median time/expected-time ratio above 1.3: fluency practice. Historical zero timings are ignored.
- Last four distinct answers correct: target a higher difficulty; only describe the selected question as harder if its difficulty exceeds the historical median.
- No answered evidence: diagnostic. Limited evidence: gather more evidence, without claiming a weakness.

Selection prefers unseen questions within the bounded history. The default slot pattern aims for three support, one revision and one exploration question per five, falling back according to available evidence/content. Revision mode prioritizes revision candidates. Candidate difficulty and subtopic diversity break ties. Repeated questions are explicitly identified in their explanations. This is a rules-based starting policy, not a validated mastery assessment.

Each question returns `recommendation: {reason_code, reason, learning_goal, evidence, repeated}`. A new additive `practice_recommendations` table stores the exact explanation under `(test_id, question_id)` in the same transaction as session creation. The application's existing `Base.metadata.create_all` startup initializes this table; no existing column is altered. Explanations contain no answers, solutions, or other students' data.

Candidates must be published, have nonempty stems/solutions, and be supported single-answer or numerical questions with valid answer metadata. Assets explicitly recorded with missing/unsupported URLs, including passage assets, exclude the question. Selection does not fetch remote image URLs or prove their availability, nor detect unrecorded missing diagrams. Content review remains necessary.

## Timing and deployment

The browser accumulates time per question across revisits, excluding hidden/unfocused intervals and submission time. The backend bounds submitted times; client timing is advisory, not an anti-cheat measure. Existing grading persists these times with question responses.

Deploy backend and frontend from the same revision. No new service, AI key or scheduler is needed. Fixed question sets are chosen at session start; this does not introduce question-by-question adaptation or page-reload recovery for in-progress subject practice.

## Checks

Run `PYTHONPATH=backend python -m pytest backend/tests` and `npm test --prefix frontend`, then `npm run build --prefix frontend`.
Regression checks cover reason evidence, distinct-question counting, difficulty choice, revision, zero timings, repeats, question eligibility, account isolation, answer-key exclusion, snapshot persistence after grading, and active-time accumulation.
