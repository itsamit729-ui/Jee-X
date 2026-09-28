# Teacher studio and classroom tests

## Start teaching

Anyone can choose **Teacher** during email/password or Google signup. Email verification follows the existing server setting. Teacher signup creates the minimal linked user and teacher permission automatically, with no administrator approval or student date of birth/class/exam goal required.

Existing accounts can open **Explore → Teacher studio → Start teaching**. Fresh Google accounts can also choose the teacher workspace from student onboarding. Enrollment is idempotent and retains any existing student profile. Teachers can optionally add a student profile at `/onboarding?student=1`.

The existing admin panel remains available for managing or restoring teacher access. An explicit revocation or account suspension cannot be reversed by self-enrollment; classes and results remain preserved. Signing up again with an existing email never changes that account's permissions.

This uses the existing `teacher_access` table, not a new `users.role` value. Self-enrollment is recorded in `audit_logs` with the account owner's user ID. Shared-password admin actions retain their session fingerprint audit trail.

## Assign a test

- Create a class in Teacher studio and copy its join link or code.
- Students join through `/classes`. A removed student needs the teacher to restore their membership; the join code cannot bypass removal.
- In **Create a test**, search/filter published questions by subject, chapter and difficulty; preview math, diagrams, options and solutions. Select up to 100 questions.
- Select one or more owned classes, set the opening time, deadline, duration and marking, then choose when to release solutions. Dates are entered in the teacher's device timezone and sent with UTC offsets.
- Publish once. The current class roster is deduplicated across selected classes. Students joining later receive future assignments, not previously published papers. At least one active student must be enrolled.
- The question content, assets, answer key, order and marking are snapshotted. The schedule and paper cannot be edited after publication in this release. An idempotency key prevents duplicate tests if a publish response is lost.

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
