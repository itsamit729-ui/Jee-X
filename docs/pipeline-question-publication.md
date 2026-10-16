# JEE Main 2019–2025 pipeline publication

All four remote branches were checked on 2026-10-16: `main`,
`feature/version-1`, `feature/ai_pipeline` and `jeeedge-social-media`.
New question data is on `feature/ai_pipeline` at
`3c7ec3ec7a0a70e0b62cefdace7ac41d7f3b4a04`: the 2019–2023 exports and
their figures, keyed chapter files and answer-source matching update. The other
branches contain no additional question data missing from the feature branch.
The 2024/2025 exports retain their original pinned revision
`eb6190d13b1984fd75b26bd2565202bdeefc2c42` and unchanged import digests.

## Readiness audit

| Export | Exported records | Eligible | Held by this import | Source pending |
| --- | ---: | ---: | ---: | ---: |
| JEE Main 2019 | 653 | 650 | 3 | 638 |
| JEE Main 2020 | 642 | 642 | 0 | 473 |
| JEE Main 2021 | 1,373 | 1,373 | 0 | 744 |
| JEE Main 2022 | 1,401 | 1,401 | 0 | 457 |
| JEE Main 2023 | 1,477 | 1,475 | 2 | 472 |
| JEE Main 2024 | 1,684 | 1,683 | 1 | 98 |
| JEE Main 2025 | 1,297 | 1,295 | 2 | 118 |
| Total | 8,527 | 8,519 | 8 | 3,000 |

The five new exports contribute 5,541 eligible questions and 88 figures.
All seven exports together include 2,863 numerical questions, 1,009 source-checked
worked solutions and 389 bundled figures. New 2019–2023 records have checked
source keys and no worked solutions; none are invented. They map onto the existing
Question/QuestionOption/Asset/QuestionRevision schema without new columns or types.

Eight records with extra source choices are held unchanged; their references and
reasons are in `datasets/jee-main-publication-review.json`. Do not remove extra
choices or assume the remaining key is valid. Pending source records stay out.
The existing JEE Main 2026 and MHT-CET 2026 files are not newly reviewed by this
extension and retain their existing publication paths and status.

Validation checks structure, supported exam/type, date/shift, four nonempty A–D
choices, exactly one MCQ key, a finite numerical key, solution-verification flags,
unique references and presence/readability of bundled images. It normalizes
unsupported mathematical font characters for MySQL's three-byte utf8 tables.
Exports are pinned by SHA-256; a future edit requires fresh review and digest
updates. Structural validation does not independently prove every answer correct.
See each source README for provenance, incomplete-source limitations and figure
attribution. Available shifts are reconstructed/partial, not guaranteed complete
official papers; historical formats and original ordering can differ.

## Publish through the deployed Admin page

1. Deploy `feature/version-1` using the existing main website Dockerfile. It now
   bundles the exports under `/app/datasets`; the frontend serves their figures.
   Raw answer-key datasets are not put in `frontend/public` or exposed publicly.
2. Open `/admin`, sign in, and choose **Question bank**.
3. Under **Publish JEE Main questions**, select a year such as **Review 2019**. This is read-only
   and reports new rows, safe updates, conflicts and already-current questions.
4. Select **Publish eligible 2019 questions**. Keep the page open while it applies
   25-question transactions and displays progress. Repeat for the other years you want to publish (2019–2025). Existing 2024/2025 checkpoints remain valid.
5. Check the PYQ page's JEE Main section and Admin year/shift coverage. The imported
   years and shifts appear from the live database; no frontend year list is needed.

Do not run the generic scraped importer with a global published override for this
review: it also includes draft questions from other years and pending source issues.
Publication is never done at startup, so cold starts do not repeatedly bulk-import
questions or add an extra reference-data import to the student web service.

## Database safeguards

- Preview and publishing endpoints require the existing Admin session.
- Each batch requires the exact digest that was previewed and accepts at most 50
  questions; the Admin UI uses 25. A failed batch rolls back as a unit.
- Existing IDs/attempt references remain intact. Retired questions stay retired.
- Stored text/options/key disagreements and possible other-reference duplicates
  are held rather than overwritten. A database may therefore accept fewer records
  than the offline eligible count; its preview explains the difference.
- Existing nonempty solutions, replacement images, taxonomy names/positions and
  difficulty/time settings are preserved. Verified source solutions fill gaps.
- Changes create a new question revision and an import-run record. Repeating a
  completed batch creates no duplicate question or revision.
- If a request times out, review and restart safely. Completed batches remain
  committed; repeated records are detected. Never assume a timeout meant rollback.

## CLI alternative

No database is needed to validate files:

```sh
python backend/scripts/import_pipeline_questions.py --validate-only
```

With the production database environment configured on your own machine:

```sh
python backend/scripts/import_pipeline_questions.py --year 2024
python backend/scripts/import_pipeline_questions.py --year 2024 --apply
python backend/scripts/import_pipeline_questions.py --year 2025 --apply
```

The first command is a read-only database preview. Omit `--year` to handle all seven
reviewed years. Keep this CLI separate from the social publishing worker: question
imports belong to the main website/database, not the Reel/Short renderer.

## Resumable imports and fewer database round trips

The main app initializes a `question_import_progress` table on deployment. Each
export digest has one saved cursor and cumulative counts. The cursor, revisions
and question changes commit together. Replaying an older batch returns the saved
cursor without scanning or writing that batch again; an offset ahead of the
saved cursor is rejected. `/api/admin/pipeline-questions/{year}/progress` is an
Admin-only lightweight read used after refreshes and lost responses.

The Admin control resumes from this server cursor and checks it before retrying
an interrupted POST. It retries transient failures up to three times; expired
Admin sessions and changed exports require signing in/reviewing again. Use **Pause import** to stop after the current batch is confirmed. Progress
survives browser refreshes and service restarts. An import completed using the
older code has no cursor yet; its existing questions are safely detected during
the first pass, without duplication.

New questions, options, assets and revisions use bulk inserts. Taxonomy is
resolved once per chapter per batch, and preview avoids per-chunk relationship
queries and duplicate checks for already-known references. In the local SQL
statement test, a fresh 25-question batch went from 283 statements to 24. This is
a query-count measurement, not a claim about production wall-clock speed.

### Site-wide use after publication

Published JEE Main questions from the reviewed datasets join topic practice, recommended
practice, revision, roadmap topic planning, balanced baseline assessments, full mocks from `/test`, daily
questions, scenario practice and the teacher bank/paper builder automatically.
Worked solutions are optional; an answer key and supported content remain required.
Practice subject/chapter counts use the same eligibility rules as session creation.
Other exams retain their own pools, and pending, held and unpublished records do
not enter the student pool. Existing attempts and teacher paper snapshots stay fixed.
Numerical scenario questions support decimals and answer ranges; the range is
shown only after the scenario ends. Complete the required year imports in Admin before
expecting all 8,519 reviewed questions to be available in production.

The main full mock uses 20 MCQs and 5 numerical questions per subject, 180 minutes
and +4/−1 scoring, with server-side grading. Unseen questions are preferred,
with repeats allowed when a subject/format pool runs out. Baseline assessments
continue to require fresh questions. The free warm-up remains a fixed demo.
