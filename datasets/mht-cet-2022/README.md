# MHT CET 2022 — question dataset

146 questions from 1 shifts of MHT CET 2022, scraped from ExamSIDE's chapter-wise pages
(49 physics, 47 chemistry, 50 mathematics; 4 with a figure).
None has a solution yet. Rebuild this folder with `python scripts/scrape_mhtcet.py --dataset 2022`.

| File | Contents |
|---|---|
| `questions.jsonl` | One question per line: `ref`, `shift`, `subject`, `chapter`, `type`, `stem` (LaTeX in `$...$`), `options` with `is_correct`, `answer`, `figure` (file in `frontend/public`), `solution` (empty) |
| `pipeline-pack.jsonl` | The same 146 questions in the solution pipeline's format (figures point at the source site) |
| `pending.jsonl` | 4 questions not usable as they are: options drawn as images, several figures, a table, or a formula that could not be rebuilt (with `pending_reasons` and the source figure URLs) |
| `summary.json` | Counts by subject, chapter, shift and type |

## Solving them

```
copy datasets\mht-cet-2022\pipeline-pack.jsonl solution-pipeline\data\questions.jsonl
cd solution-pipeline
python pipeline/run_batch.py --limit 3
```

## Notes
- Source: questions and keys as transcribed by ExamSIDE; MHT-CET is computer based and its papers are not published, so these are the source's reconstruction and its keys are not official. The solution pipeline flags disagreements (`key_mismatch`).
- Formulas were rebuilt from the site's rendered MathJax, not copied as LaTeX. `generated/scraped-mht-cet/.reports/` lists the questions whose rebuilt text differs from the site's raw excerpt.
- These questions are not in the database: `exam` is `mht_cet`, which the backend does not accept yet.
- Contains answer keys: keep the repository private before sharing it widely.
