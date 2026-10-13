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

Create sheets for enrolled students, choose set A/B, print A4 at 100%, and keep all four corner markers and the opaque QR visible in photographs. Answer sheets accept single-correct, multiple-correct and numerical questions. Compact four-option single-correct papers retain the original one-page layout; mixed papers use versioned multi-page layouts. Upload JPEG/PNG photos (8 MB, 25 MP limit) or scanned PDFs (8 MB, up to 60 pages per upload). Processing aligns the sheet, resolves its paper/student from the QR, and highlights uncertain/multiple markings. Every scan requires teacher review; no score is released solely on a machine guess. Blank answers must be explicitly reviewed as blank; multiple/invalid marks can be confirmed as wrong without inventing an option selection. Duplicate scans cannot create a second score, and a student who started online cannot also receive an offline score for that assignment.

Assign a paper online **before reviewing its OMR scans** if the same test should appear in student history. Reviewed scans then use the existing classroom grader and solution-release rules. Standalone offline papers remain in teacher student reports and CSV exports. An offline paper with reviewed results cannot subsequently be attached to a new online assignment; duplicate it instead. Teachers see only their own class results, not other teachers' records or unrelated private practice.

From **Answer key / PDF → Correct an answer key & regrade**, correct an MCQ option and supply a reason. The transaction updates the saved key, affected online attempts, offline scores and the original attempts' mastery contributions. The original submission time is retained, paper order does not change, and an audit row records old/new keys and affected counts. Corrections apply to this paper, not the shared question bank.

## Deployment and operational limits

This extension adds `teacher_papers`, `teacher_omr_sheets` and `teacher_omr_scans`; the existing startup table creation handles them without dropping or rewriting old tables. Deploy both frontend/backend and install the updated Python requirements (ReportLab, OpenCV, NumPy and PDFium). No paid AI or OCR API is used.

OMR runs as bounded in-process background work, serialised within each process; a teacher may have three active pages, with an admission check for eight globally. These global counts are best-effort under concurrent teachers. It is a small-deployment queue, not a durable distributed worker. Scans/overlays use `TEACHER_SCAN_DIR` (default temporary disk); images are not stored in MySQL. Original uploads are removed after processing. Overlay cleanup runs after scans and removes files older than 24 hours; restart/ephemeral hosting can remove them earlier. Reviewed answers/scores/audit metadata remain in the database. Interrupted jobs are marked for re-upload after ten minutes; expired previews must be re-uploaded before review. Use a persistent directory only on a single instance; multi-instance deployments need shared object storage and a proper worker before scaling OMR.

Validation includes isolated database lifecycle/permissions, snapshot consistency, duplicate prevention, PDF ingestion, key correction/mastery reconciliation, generated OMR detection (blank, filled, multiple and 180-degree rotation), frontend build and A4 visual inspection. Phone photos, live MySQL deployment and browser print layouts still require a deployment pilot; synthetic detection is not an accuracy guarantee.

### Reusable blank OMR copies

In **Papers & OMR → OMR & scans**, choose Set A/B and **Download reusable blank OMR**. One PDF can be printed repeatedly for that finalised paper and set. Students write their name, write their 10-digit OMR ID in the boxes and shade one digit per column, including leading zeros. The ID is shown in the student’s My classroom page and the teacher’s roster and student list. Personalised PDFs remain available as an alternative. Reusable sheets can be printed before enrolling students, but students must join a teacher's class before their scores can be saved.

The reusable QR identifies the paper/set only. It never guesses student identity from handwriting. New reusable sheets include a digit bubble grid. A clear shaded ID automatically selects the matching active student from this teacher’s roster; no manual matching is needed. Blank, multiple, weak or unknown IDs remain unassigned for explicit correction during review. The detector reads shaded bubbles, not handwriting. Earlier reusable sheets retain manual identity review, while personalised QR sheets continue to identify the student directly. The QR distinguishes layouts so older printed copies remain readable. All scores still require answer review. A missing or unauthorised student is rejected; the usual one-result-per-student and online-attempt safeguards still apply. Key corrections do not invalidate printed copies. No database migration is needed.

## Teacher account and navigation

Teacher accounts use `/teacher/profile` for their name, private photo, institution, subjects and teaching bio, and `/teacher/account` for access information and support. Updating a name also updates the teacher name shown with classes. Email and the account username remain read-only. Password changes and Google linking stay at `/account/security` with teacher navigation and a teacher-profile return link. No student profile, date of birth, exam goal, rating or study plan is needed to edit a teacher profile.

The application resolves teacher routes before mounting pages: `/profile` opens the teacher profile, `/pricing` opens teacher account information, and student-only/public practice destinations return to Teacher Studio without calling student APIs. Teacher loading text and the inbox are audience-specific; student fact prompts are suppressed. Teacher inboxes exclude historical student assignment links. Existing mixed accounts retain their student records but are excluded from public student-profile lookup, including the public avatar endpoint.

`teacher_profiles` is a new additive table containing private teaching details and an optimistic version. Photos use the existing image store and sanitisation, with authenticated teacher-only read/upload/delete endpoints. The existing startup table creation creates the new table; deploy frontend and backend together. Teacher account access remains governed by existing teacher permissions; this update does not invent a paid subscription or checkout.

## Paper readiness and optional sets

New papers created in Teacher Studio default to **Single paper — no sets**. Teachers may explicitly choose A/B classroom orders before finalising. Legacy saved papers and older API clients retain their existing A/B behaviour; their QR identities and deterministic order remain unchanged. Single papers internally use the original order and show **Standard paper — no sets** on OMR sheets. Set B requests for these papers are rejected. Duplicating preserves the choice; finalised papers cannot change it.

Readiness checks show the exact question numbers that cannot be scanned: unsupported formats, missing choice labels, or incomplete answer keys. Those papers remain printable and assignable online. The OMR tab offers these alternatives and a duplicate-to-repair action. **Generate only OMR-compatible questions** filters the bank before selection; manually added questions still receive readiness warnings. Exact/similar past-paper modes retain original formats and cannot silently filter out non-OMR questions. Papers with a year but no shift/set label are explicitly selectable as unlabelled references.

PDF and CSV downloads use authenticated requests and show failures in the studio rather than opening raw JSON. Drafts warn before closing/replacing unsaved work; saved-paper reload recovers version conflicts. Opening/new-paper actions reset scan/set state. Teacher Studio offers paper search/status filters, question-key review before finalising, schedule checks, class-filtered personalised sheets, scan state filters and expired-preview explanations. Upload batches validate file size/type before submitting; partial failures identify which files were already accepted. Polling stops once processing finishes.

A reusable sheet’s detected student ID may be corrected by the teacher before scoring, within their active roster; the correction is retained in the result. Personalised QR sheets remain bound to their student. Removed students must be restored before scoring, and existing duplicate-result/online-attempt protections remain. Changes use the existing paper settings JSON; no schema migration is required. Deploy frontend and backend together.


## Mixed-format answer sheets

All supported question types work in teacher-created questions, printed papers, reusable/personalised answer sheets, reviewed scoring and answer-key corrections. Multiple-correct responses are graded by exact option-set match, identical to online classroom grading; no partial-credit scheme is introduced. Numerical responses use the same inclusive answer range as online tests.

Mixed sheets print a page-specific QR, question numbers/types, and a student ID grid on every page. Numerical grids encode sign, eight digits including leading zeros, and 0–8 decimal places. For example, -12.5 uses minus, 00000125 and 1 decimal place. Students also write the value in the answer box. Longer/scientific-notation values and unclear handwriting are entered by the teacher during review; handwriting is not automatically OCR-scored. Ambiguous marks, multiple single-choice marks and writing without a usable numeric grid require explicit review. Zero, negative values, decimals, blanks and invalid responses are distinct.

Every page must be uploaded and confirmed for the same paper, order/set and student before a single final score is created or imported to the classroom assignment. Page order does not matter. Duplicate pages, mixed students/sets, and incomplete papers cannot silently produce a partial final score. Confirmed pages can be reopened before final scoring; if their preview expired, reopening clears that page confirmation and requires a new upload. Completed results retain the original duplicate-score fence. Key corrections regrade completed results, while incomplete papers use the latest key at completion.

Scanned PDFs may contain up to 60 pages within 8 MB; image limits remain 8 MB and 25 megapixels. Up to 60 pending pages per teacher and 120 globally are queued with serial detector execution. The UI tracks page confirmation and shows missing pages after each confirmation. The existing scan JSON records hold versioned page metadata and answers; no schema migration or paid OCR service is needed. Legacy QR sheets and their original geometry remain supported.


## Teacher workspace experience

Teacher accounts open on an overview with real class, student, test and draft counts, upcoming assignments and links to the next setup task. A shared sidebar covers classes, papers, students, reports, syllabus, student questions and account settings. On smaller screens the same navigation is available from the header menu. Existing report links and the legacy `tab=build` link still work; invalid section names return to Overview.

Paper creation has three steps: Set up, Add questions, and Review & finalise. Teachers can generate questions, browse the bank or write private questions in separate panels. Drafts remain editable; finalised papers have separate question paper, answer key, answer sheet and online assignment views. Answer sheets separate printing, uploads and review/results. The current scan review requirement is shown accurately; this UI change does not enable automatic scoring or handwriting OCR.

Student and test lists include search, results exports and clear empty states. Syllabus coverage and personal follow-up are separate views. Student doubts can be filtered by reply status. Profile edits show saved/unsaved status and warn before leaving with changes. Print styles exclude workspace navigation and controls. The existing palette is retained, and transitions respect reduced-motion preferences.


Teacher bank previews and printed papers render complete labelled choice rows, mathematical content and numerical-format hints. Source choices embedded as `(A)`–`(D)` lines are recovered into snapshots without changing option IDs or the answer key. Genuine empty option content is excluded from new teacher papers even when a stem diagram exists; a reactant diagram is not a substitute for missing product options. Label-only choices backed by an image refer to the source diagram. Existing incomplete paper snapshots show an availability warning and require replacement in a duplicate draft.
