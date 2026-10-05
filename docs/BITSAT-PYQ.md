# BITSAT PYQ section

Route: `/pyq`. Scope: the latest five completed exam years, 2022–2026.

## Content status

The first internet-sourced batch contains **23 reviewed memory-based questions**:
6 attributed to 2022 and 17 to 2023. See `generated/bitsat/README.md` for attribution,
license, modifications, coverage and limitations. This is not a complete five-year bank.
No 2024–2026, English or Logical Reasoning questions are included yet. The available
licensed dataset stops at 2023; other source banks have not been cleared for bulk reuse.
Questions and options were retained; worked solutions were independently derived.
The original source's year attribution is retained, not verified official-paper provenance.
The UI reads actual published database availability. Database migration/import still
must run in the configured deployment environment.

## Existing contracts retained

- Chapter JSON: `subject`, `chapter`, `subtopics`, `passages`, `questions`.
- Questions: existing `ref`, `subtopic`, `type`, `difficulty`, `expected_time_sec`,
  `source_type`, `exam`, `year`, `shift`, `status`, `stem`, `image`, `options`, `solution` fields.
- `exam: "bitsat"`, `source_type: "pyq"`, `type: "single_correct"`; four A–D options
  with exactly one `is_correct: true`. Stable refs begin `BITSAT-` and are at most 50 characters.
- Subjects: `PHY`, `CHEM`, `MATH`, `ENG`, `LR`. English/LR chapters must explicitly set
  `in_main: false` and `in_advanced: false`. The existing schema still requires class level 11/12.
- Figures live under `frontend/public/question-images/`; JSON uses `/question-images/...` URLs.
- Add `provenance` to each question, containing `kind: "memory_based"`, `source` (file or URL),
  `locator` (page/question), `reuse_basis`, and `answer_verified_by`. These fields are retained
  in the existing revision JSON. They document human review; the validator cannot prove an answer is correct.
- Imports use the existing chapter importer, stable-ref upserts, content hashes, and question revisions.
  Existing chapter metadata is retained through the existing scraped-PYQ import planner.
- Practice uses the existing server grader, MathText, QuestionAssets, option controls and solutions.
  Scoring is +3 / −1 / 0; attempts are unranked. This is a subject practice set, not a full timed BITSAT simulation.
- Questions/answers are not bundled into the frontend. Answer keys and solutions are returned only after submission.
- Existing JEE practice and daily selection exclude BITSAT. BITSAT results do not show the JEE rank predictor.

## Deployment and import

The code push does not execute a database migration or import. `create_all` does not alter
existing CHECK constraints. With the target MySQL environment configured, run:

```sh
cd backend
python scripts/migrate_bitsat.py
python scripts/migrate_bitsat.py --apply
```

This expands named CHECK constraints on subjects, questions and tests. Each ALTER replaces
its constraint atomically. MySQL DDL commits implicitly; the migration can be rerun if interrupted.
Deploy the API and frontend before publishing questions. Put reviewed chapter files under
`generated/bitsat/<subject>/<chapter>.json` and their figures in the existing public image tree.

```sh
python scripts/validate_bitsat.py generated/bitsat
cd backend
python scripts/import_bitsat.py ../generated/bitsat
python scripts/import_bitsat.py ../generated/bitsat --apply
```

The importer does not promote drafts automatically; reviewed files must explicitly set
`status: "published"` to appear in the catalog. Each chapter commits independently, like
existing imports. Reruns leave unchanged questions unchanged and version edited questions.
The dry run performs file validation and a database plan; if subjects are missing it reports
that prerequisite without writing. Import failures stop further files and report the error.

## Validation

`PYTHONPATH=backend python -m pytest backend/tests/test_bitsat.py backend/tests/test_practice.py`

API coverage checks availability, wrong-year/draft/incomplete exclusions, no answer leakage,
+3/−1/0 scoring, attempt ownership, repeat submission, and JEE practice isolation.
The import validator rejects missing review provenance and duplicate refs. Test fixture
questions are synthetic fixtures only and never enter a production question bank.
