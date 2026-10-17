# Feature/version-1 integration — 17 October 2026

Based on `25d6976a77141b6d18887b3d330502766a852a74`, which already includes the
ready-test/fullscreen fix and the reopenable analysis work.

## Access

- Dashboard → recent results → open a result, or See full analysis after a
  practice/mock submission. The protected route is `/results/:attemptId`.
- Admin → Question bank → select MHT-CET in the publishing panel → Review a
  year → Publish eligible questions. Refresh or pause resumes from the saved
  server cursor. JEE Main remains the default, with its existing routes intact.

## MHT-CET content

The 2020–2025 exports contain 8,382 rows. Of these, 8,379 pass the pinned import
validation, including 382 figures. Two non-single-correct entries remain held:
`PYQ-CHEM-1c08a21e4758` and `PYQ-MATH-91cb79f0788c`. One possible same-shift
duplicate, `PYQ-PHY-41cb568a9c48`, is held before batching so the result does not
depend on batch size. Another 160 source rows are
in pending files, which are never published by this importer. None of these new
questions has an independently verified worked solution. Source keys are
reconstructed ExamSIDE keys, not official answer keys.

The Docker image bundles all six question/pending exports. Image paths are
checked against the deployed static files. Existing schema migration already
supports MHT-CET. Publication is explicit, not a startup database write: deploying
this code alone does not increase the live published count.

The same conservative importer preserves existing solutions, answers, question
IDs and chapter metadata, holds conflicts and possible duplicates, and commits
question writes with the exam-specific export cursor. New MHT-only chapters are
not marked as JEE chapters. Repeated requests cannot add the same batch twice.

## Analysis integration fixes

Old mock scores are labelled as marks, not a count of correct answers. The free
diagnostic keeps its correct-answer count. MHT-CET/BITSAT result practice links
stay in their exam's subject PYQ bank; JEE chapter links keep their existing
chapter scope. Buddy displays 0% rather than NaN when nothing was attempted.

Validation uses isolated test databases, never the production database. Coverage
includes all eligible MHT rows, figures, replay safety, source pinning, exam
isolation, taxonomy preservation, analysis access controls and existing JEE
publication. Production publication and native browser/device checks are separate.

The full fixture import confirms 8,379 published rows, 382 assets and 8,379
first revisions in an empty test database; replaying the first batch creates
no new rows or revisions. Existing live conflicts can reduce the actual number
added, which is why the admin preview reports new/current/held counts.

## Publication state and 2026 follow-up

The public MHT-CET catalog was checked on 17 October 2026 and already exposed
questions for every year 2020–2026, including all 443 questions for 2020 and
4,003 for 2026. An empty `add + update` preview does not mean an import failed:
questions can already be published without an admin import cursor. The panel
now says Already published and links to the selected archive year. If records
are held, it explains that state and provides a working Review held questions
action, rather than an unexplained disabled Publish button.

The pinned publisher and Docker bundle now include 2026. Across 2020–2026,
12,382 source entries pass validation, with 531 figures and 207 pending rows
excluded. The three previously held 2023/2025 records stay held. Existing
published content is not deleted to match these export counts.
