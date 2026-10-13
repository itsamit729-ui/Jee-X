# Teacher studio and classroom tests

## Start teaching

Anyone can choose **Teacher** during email/password or Google signup. Email verification follows the existing server setting. Teacher signup creates the minimal linked user and teacher permission automatically, with no administrator approval or student date of birth/class/exam goal required.

Teacher and student accounts now have separate navigation and server-enforced workspaces. Fresh Google accounts can choose Teacher during signup or before student onboarding. An account with an existing student profile cannot self-convert: use a separate email for teaching. Existing mixed accounts retain their old student records but open only the teacher workspace. Teacher accounts cannot create new student profiles or use student practice APIs. Account security and the in-app inbox remain accessible.

The existing admin panel remains available for managing or restoring teacher access. An explicit revocation or account suspension cannot be reversed by self-enrollment; classes and results remain preserved. Signing up again with an existing email never changes that account's permissions.

This uses the existing `teacher_access` table, not a new `users.role` value. Self-enrollment is recorded in `audit_logs` with the account owner's user ID. Shared-password admin actions retain their session fingerprint audit trail.

## Assign a test

- Create a class in Teacher studio and copy its join link or code.
- Students join through `/classes`. A removed student needs the teacher to restore their membership; the join code cannot bypass removal.
- In **Papers & OMR**, generate a paper or select questions manually; preview math and diagrams. Select up to 200 questions, save a draft and finalise it before assigning.
- Select one or more owned classes, set the opening time, deadline, duration and marking, then choose when to release solutions. Dates are entered in the teacher's device timezone and sent with UTC offsets.
- Publish once. The current class roster is deduplicated across selected classes. Students joining later receive future assignments, not previously published papers. At least one active student must be enrolled.
- The question content, assets, answer key, order and marking are snapshotted. The schedule and question text/order cannot be edited after publication. Single-correct keys can be corrected with an audited regrade from the saved paper. An idempotency key prevents duplicate tests if a publish response is lost.

## Student attempts and reports

- `/classes` groups pending and completed/closed assignments. The dashboard highlights pending class tests.
- Students start one timed attempt. Leaving/reloading does not reset the timer. The effective end is the earlier of the attempt duration and assignment deadline.
- Drafts are autosaved to the account. A visible save status and retry action distinguish saved work from unsaved edits. Version checks prevent another tab silently overwriting a newer draft. Navigation through app links saves pending answers first; refresh warns if edits are still unsaved.
- The backend grades frozen questions. After the deadline, it grades the last saved draft and ignores new late answers. Repeated submission returns the same result. Expired started attempts are finalized on the student's next assignment/classroom request or when the teacher opens the report; no background worker is needed. Students who never started remain closed/unstarted.
- Scores appear immediately. Correct options, numeric keys, outcomes per question and explanations stay out of student API payloads until the release time. The generic practice submission endpoint cannot submit classroom tests.
- Reports show student status, score and accuracy, and question/topic accuracy across submitted papers. Topic accuracy includes unanswered questions; student accuracy uses attempted questions. Removed students remain in historical reports but lose assignment access unless still enrolled in another assigned class.
- Responses enter the normal learning history and mastery statistics, so recommendations and roadmap evidence can use them. Assigned papers are chapter tests and cannot count as a full JEE readiness baseline or rated contest. This release does not award class-test coins.

Question-bank items may also be accessible in normal practice, so this is a classroom learning feature, not a proctored/high-stakes secure exam system.

## Notifications and deployment

The bell/inbox persists notifications for assignment publication, unfinished-test reminders one hour before a deadline (where the schedule allows), released solutions for submitted attempts, and a test-closed report for the teacher. Future messages are stored with `available_at` and become visible when due. Read state belongs to each recipient. Polling runs once per minute while visible, plus refresh on focus. The inbox itself has an explicit refresh action. This release delivers **in-app notifications only**, not email or OS/browser push while the app is closed.

Deployment uses the existing backend startup `Base.metadata.create_all` to create these new tables: `teacher_access`, `classrooms`, `classroom_members`, `teaching_assignments`, `assignment_classrooms`, `assignment_recipients`, `classroom_notifications`. Existing user/test schemas are unchanged. Deploy the backend and frontend together using the existing pipeline. No new service, external credential, migration of existing roles or recurring worker is required.

Validation: backend permission/CSRF and lifecycle tests in `backend/tests/test_teaching.py`; countdown clock test in `frontend/tests/assignmentClock.test.js`; responsive browser checks for teacher publishing/reporting, student autosave/resume/submission, solution gating, admin approval and inbox read state. Automated database tests use isolated SQLite; the production MySQL database and deployed site require the normal deployment smoke check.


## Saved papers and automatic selection

The builder offers quick subject-balanced selection, explicit subject/type/difficulty blueprints, a similar-paper mode matching the available reference distribution, the available original PYQ paper, and class remedial selection from submitted online or reviewed offline work. Select taught chapters and exclude questions previously assigned online to selected classes. Locks consume blueprint slots; shortfalls reject the generation instead of saving an incomplete paper. You can replace, reorder or manually choose every question. Private single-correct questions support LaTeX and remain draft items visible only to their owner and assigned students. Saved papers can be duplicated as reusable starting points.

Difficulty uses question-bank tags, not calibrated exam statistics. Reference matching depends on year/shift/chapter/type metadata, and cannot certify complete coverage or original question order. Quick selection distributes questions across available subjects; use a blueprint for exact counts. Marks are uniform per paper: choose the marking explicitly, especially for exams with subject-specific marks. This is a custom classroom test, not a claim to reproduce every official exam rule.

Draft updates check a version to prevent overwriting another tab. Finalised snapshots remain independent of later bank edits. Sets A/B have stable question order; options retain their original labels. Print the question paper and the separate key/solutions using **Print / Save as PDF** with A4 selected. Personalised OMR sheets are direct PDF downloads. Printed source images must already be available in the bank; the feature does not remove source watermarks.

## OMR review and corrections

Create sheets for enrolled students, choose set A/B, print A4 at 100%, and keep all four corner markers and the opaque QR visible in photographs. OMR accepts only single-correct A–D questions with exactly four options. Upload JPEG/PNG photos (8 MB, 25 MP limit) or scanned PDFs (8 MB, up to three pages per upload). Processing aligns the sheet, resolves its paper/student from the QR, and highlights uncertain/multiple markings. Every scan requires teacher review; no score is released solely on a machine guess. Blank answers must be explicitly reviewed as blank; multiple/invalid marks can be confirmed as wrong without inventing an option selection. Duplicate scans cannot create a second score, and a student who started online cannot also receive an offline score for that assignment.

Assign a paper online **before reviewing its OMR scans** if the same test should appear in student history. Reviewed scans then use the existing classroom grader and solution-release rules. Standalone offline papers remain in teacher student reports and CSV exports. An offline paper with reviewed results cannot subsequently be attached to a new online assignment; duplicate it instead. Teachers see only their own class results, not other teachers' records or unrelated private practice.

From **Answer key / PDF → Correct an answer key & regrade**, correct an MCQ option and supply a reason. The transaction updates the saved key, affected online attempts, offline scores and the original attempts' mastery contributions. The original submission time is retained, paper order does not change, and an audit row records old/new keys and affected counts. Corrections apply to this paper, not the shared question bank.

## Deployment and operational limits

This extension adds `teacher_papers`, `teacher_omr_sheets` and `teacher_omr_scans`; the existing startup table creation handles them without dropping or rewriting old tables. Deploy both frontend/backend and install the updated Python requirements (ReportLab, OpenCV, NumPy and PDFium). No paid AI or OCR API is used.

OMR runs as bounded in-process background work, serialised within each process; a teacher may have three active pages, with an admission check for eight globally. These global counts are best-effort under concurrent teachers. It is a small-deployment queue, not a durable distributed worker. Scans/overlays use `TEACHER_SCAN_DIR` (default temporary disk); images are not stored in MySQL. Original uploads are removed after processing. Overlay cleanup runs after scans and removes files older than 24 hours; restart/ephemeral hosting can remove them earlier. Reviewed answers/scores/audit metadata remain in the database. Interrupted jobs are marked for re-upload after ten minutes; expired previews must be re-uploaded before review. Use a persistent directory only on a single instance; multi-instance deployments need shared object storage and a proper worker before scaling OMR.

Validation includes isolated database lifecycle/permissions, snapshot consistency, duplicate prevention, PDF ingestion, key correction/mastery reconciliation, generated OMR detection (blank, filled, multiple and 180-degree rotation), frontend build and A4 visual inspection. Phone photos, live MySQL deployment and browser print layouts still require a deployment pilot; synthetic detection is not an accuracy guarantee.

### Reusable blank OMR copies

In **Papers & OMR → OMR & scans**, choose Set A/B and **Download reusable blank OMR**. One PDF can be printed repeatedly for that finalised paper and set. Students write their name and student ID in the header. Personalised PDFs remain available as an alternative. Reusable sheets can be printed before enrolling students, but students must join a teacher's class before their scores can be saved.

The reusable QR identifies the paper/set only. It never guesses student identity from handwriting. On upload, select the enrolled student after comparing the handwritten name/ID with the annotated preview, then review answers. A missing or unauthorised student is rejected; the usual one-result-per-student and online-attempt safeguards still apply. Key corrections do not invalidate printed copies. No database migration is needed.
