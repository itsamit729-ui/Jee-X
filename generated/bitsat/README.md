# BITSAT memory-based questions — initial reviewed batch

This is a **partial collection**, not five complete years or complete shift papers.

| Source-attributed year | Physics | Chemistry | Mathematics | English | Logical Reasoning |
|---|---:|---:|---:|---:|---:|
| 2022 | 4 | 1 | 1 | 0 | 0 |
| 2023 | 12 | 1 | 4 | 0 | 0 |
| 2024 | 0 | 0 | 0 | 0 | 0 |
| 2025 | 0 | 0 | 0 | 0 | 0 |
| 2026 | 0 | 0 | 0 | 0 | 0 |

## Attribution

Question stems and options adapted from **datavorous/entrance-exam-dataset**,
credited to **datavorous and the dataset contributors**, published at
https://huggingface.co/datasets/datavorous/entrance-exam-dataset .
The publisher labels that dataset **Creative Commons Attribution 4.0 International**:
https://creativecommons.org/licenses/by/4.0/ . No endorsement is implied.

Source: `search_BITSAT.db`, SHA-256
`63bdcea44d5cafbe36771f72e4e25a52207505a9866c5234916d5bcb951de1fe`.

Changes: HTML stripped; option LaTeX escaping normalized; existing chapter taxonomy applied;
worked solutions independently derived by Codex instead of copied from the dataset.
The dataset year and question wording are retained. Year attribution has **not** been
independently established from an official question paper. Recalled paper labels are
preserved in provenance; they are not treated as verified dates or shifts.

The dataset contains 297 raw records for 2022–2023, including duplicates and inconsistent
questions. Only the 23 explicitly reviewed IDs in `scripts/bitsat_reviews.json` are exported.
Other records are not included in the published bank. Record 2 is excluded because its
integral limit conflicts with its answer and solution. Records with diagrams require a
separate figure review. No questions are fabricated to fill missing years or subjects.

## Reproduce and validate

```sh
python -m pip install beautifulsoup4
python scripts/collect_bitsat_open_data.py
python scripts/validate_bitsat.py generated/bitsat
```

The collector checks the source checksum, four option labels, source answer consistency,
and the independently reviewed key. It reuses existing chapter metadata and stable refs.
A changed source checksum blocks export until reviewed. Automated structure checks are
not proof of correctness or official provenance.

## Import to the configured database

```sh
cd backend
python scripts/migrate_bitsat.py --apply
python scripts/import_bitsat.py ../generated/bitsat
python scripts/import_bitsat.py ../generated/bitsat --apply
```

Files are marked `published` because the included answers were independently derived and
checked against all options. This status takes effect only after database import; a GitHub
push alone does not import questions. Live migration/import have not been performed here.
