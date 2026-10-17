# Learning follow-up

Students can open **Explore → Mistakes & revision** (`/learning`). Wrong and skipped answers from the latest responses to up to 500 recent questions become revision cards. Class questions require active membership, an assigned submitted result and released solutions. A correct subsequent normal attempt retires the card. Eight-question untimed sessions grade on the server, reveal explanations only on submission and schedule successful retrieval at 3, 7, 14 then 30 days; misses return after one day. Revision does not create ranked attempts, mastery records or coins. Sessions resume for one day; unsaved choices live only on the current screen. Changed keys/source evidence invalidate stale sessions.

Teachers use **Syllabus & improvement** to mark covered chapters and inspect their own class results. Students see those covered chapters in their learning notebook. **Only taught chapters** in the paper builder uses the intersection across selected classes and rejects empty coverage. Generation blueprints save exam, chapter, section, level, class and reference-paper settings; locks and temporary question exclusions are not persisted. Up to 100 blueprints per teacher.

Class improvement compares marks percentages on the last two assigned tests, including linked reviewed OMR results. Different tests can differ in difficulty, so this is not a calibrated ability measure. Below-70%-accuracy topics feed personal remedial assignments. Teachers explicitly select up to 50 students, a question count and publish. Each student receives only their own fresh questions, a two-minute-per-question timer (minimum ten minutes), seven-day deadline and solution release at that deadline. Insufficient-bank or insufficient-evidence students are reported as skipped. Repeating a publish request does not duplicate previously published assignments. Standalone offline scan results are not included in this class-assignment report.

**Ask teacher** on released assignment questions opens a private question doubt. Teachers reply in **Question doubts**. Students can consent to class sharing; sharing is off by default. Shared threads omit the account name and are readable only by active assigned classmates who have submitted and reached solution release. The UI asks students to leave personal details out of shareable text. This release supports text/LaTeX questions and replies, not photo uploads or paid AI answers. In-app notifications link to new doubts and replies. At most 20 new doubts per student per day; lists show up to 100 threads.

Deploy frontend and backend together. Five new tables (`revision_cards`, `revision_sessions`, `teacher_taught_chapters`, `teacher_blueprints`, `question_doubts`) are created by existing startup metadata creation. Existing tables and attempt history are unchanged. Revision evidence IDs deliberately have no foreign-key constraint because key corrections rebuild response rows. No additional service, scheduled worker or paid API is needed.

### Quick manual paper creation

Create a paper opens a compact manual builder. Choose an exam and optionally a
subject, searchable chapters, or a past-paper year/shift; count and time have
editable defaults and size presets. One action saves the final paper and shows
paper and OMR downloads. Titles and exam/subject marking are automatic unless
overridden. Difficulty, question format, source and instructions are optional.
The detailed editor remains available through **Choose questions myself**.

`GET /api/teacher/papers/catalog?exam=...` supplies published chapter metadata.
`POST /api/teacher/papers/quick-create` accepts explicit structured fields, never
natural-language instructions. Selection uses only the authenticated teacher's
visible published bank, verifies the exam, scope and reference, and rejects
missing diagrams, bank shortfalls or incomplete OMR data without saving a partial
paper. A full reference paper retains its formats and original mix; a subset
supports filters. Null shift labels match only that unlabeled reference.

The client supplies a UUID preserved across retries of unchanged input. The
teacher-scoped `creation_request_key` and a user row lock prevent duplicate saves.
Copies omit that identity. New A/B papers ensure distinct orders when there is
more than one question. Previously saved papers retain their printed orders,
including papers created by the former AI flow. Paper PDFs prepare in the
background and reuse the existing per-tab render cache; OMR download is independent.

AI interpretation, mapping files, chat UI and provider calls have been removed.
Old AI endpoints return HTTP 410 with a refresh instruction. No Groq key, AI model
configuration, database migration or new service is needed for paper creation.
Deploy frontend and backend together.
