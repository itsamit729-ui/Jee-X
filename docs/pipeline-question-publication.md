# JEE Main 2024 / 2025 pipeline publication

Source: `feature/ai_pipeline` at `eb6190d13b1984fd75b26bd2565202bdeefc2c42`.
The feature branch includes its datasets, chapter files, figures and answer-source
pipeline tools. Existing application/schema changes on `feature/version-1` are
preserved by merging the two new pipeline commits, not replacing the feature tree.

## Readiness audit

| Export | Exported records | Eligible | Held by this import | Source pending |
| --- | ---: | ---: | ---: | ---: |
| JEE Main 2024 | 1,684 | 1,683 | 1 | 98 |
| JEE Main 2025 | 1,297 | 1,295 | 2 | 118 |
| Total | 2,981 | 2,978 | 3 | 216 |

Eligible records include 858 numerical questions, 1,009 source-checked worked
solutions and 301 bundled figures. The database importer maps them onto the
existing Question/QuestionOption/Asset/QuestionRevision schema; no new columns or
question types are required. Answer-only questions have an empty solution string,
not a fabricated worked solution. The current JEE Main PYQ archive supports these.

Three source records have a fifth "None of above" option and are held unchanged:
`PYQ-MATH-b25f43af33c6`, `PYQ-MATH-5e4d39c22d39`, `PYQ-PHY-8991eda79415`.
Do not remove the extra option and assume the original text/key is correct. In
particular the first two mathematics texts also need checking against the paper.
The source pending files are retained for future repair and never auto-published.

Validation checks structure, supported exam/type, date/shift, four nonempty A–D
choices, exactly one MCQ key, a finite numerical key, solution-verification flags,
unique references and the presence/readability of bundled images. It normalizes
unsupported mathematical font characters for MySQL's three-byte utf8 tables.
Exports are pinned by SHA-256; a future edit requires a fresh review and digest
update. The structural audit does not independently prove every answer correct.
See each source README for answer provenance, incomplete-source limitations and
figure attribution. Available shifts are reconstructed/partial, not guaranteed
complete official papers.

## Publish through the deployed Admin page

1. Deploy `feature/version-1` using the existing main website Dockerfile. It now
   bundles the exports under `/app/datasets`; the frontend serves their figures.
   Raw answer-key datasets are not put in `frontend/public` or exposed publicly.
2. Open `/admin`, sign in, and choose **Question bank**.
3. Under **Publish JEE Main questions**, select **Review 2024**. This is read-only
   and reports new rows, safe updates, conflicts and already-current questions.
4. Select **Publish eligible 2024 questions**. Keep the page open while it applies
   25-question transactions and displays progress. Repeat for 2025.
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

The first command is a read-only database preview. Omit `--year` to handle both
reviewed years. Keep this CLI separate from the social publishing worker: question
imports belong to the main website/database, not the Reel/Short renderer.
