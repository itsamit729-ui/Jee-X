# MHT CET PYQs

Merged from feature/ai_pipeline into feature/version-1. Includes 4,003 MHT CET 2026
questions (Physics 1,345; Chemistry 1,321; Mathematics 1,337), figures, JEE 2026 datasets
and the verified solution pipeline.

The PYQ page has separate MHT CET and BITSAT catalogs. MHT CET accepts published
single-correct questions with valid answer keys even while worked solutions are pending.
Physics/Chemistry award 1 mark, Mathematics 2 marks, with no negative marking.
Other JEE practice pools continue to exclude both exams.

## Existing database

The Docker startup runs the idempotent `scripts/add_mht_cet.py --apply` migration
before starting the app. It retains BITSAT and expands question and test constraints.
For non-Docker deployments run it from backend before starting the new backend.

Import from a repository checkout with the target DATABASE_URL and DB_SSL_CA:

```sh
cd backend
python scripts/add_mht_cet.py --apply
python scripts/import_scraped_pyqs.py ../generated/scraped-mht-cet --apply --status published
```

In the deployed Docker container the MHT bank is bundled; run:

```sh
QUESTION_REPO_ROOT=/app QUESTION_PUBLIC_ROOT=/app/static python scripts/import_scraped_pyqs.py /app/generated/scraped-mht-cet --apply --status published
```

Re-imports use stable refs and revision history. The source files remain drafts in git.
The catalog only shows questions after database import. Source keys are reconstructed,
not official; the UI states this and does not claim worked solutions are available.
The 47 pending source records are excluded from the chapter bank.

JEE source updates are also merged; use the existing scraped importer for
`../generated/scraped` to synchronize the JEE bank with the target database.
