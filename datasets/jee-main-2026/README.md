# JEE Main 2026 — question dataset

1364 published questions from all 19 shifts of JEE Main 2026, exactly as they are in the Jee Edge database
(478 physics, 428 chemistry, 458 mathematics;
1085 single-correct, 279 numerical; 161 with a figure).
46 have a verified solution. Rebuild this folder with `python solution-pipeline/pipeline/export_dataset.py --year 2026`.

| File | Contents |
|---|---|
| `questions.jsonl` | One question per line: `ref`, `shift`, `subject`, `chapter`, `type`, `stem` (LaTeX in `$...$`), `options` with `is_correct`, `answer`, `figure` (URL on the site, file in `frontend/public`), `solution` (only when verified) |
| `pipeline-pack.jsonl` | The 1318 questions still without a verified solution, in the solution pipeline's format |
| `pending.jsonl` | 46 scraped questions not imported yet: options drawn as images, several figures, or a missing key at the source (with `pending_reasons` and the source figure URLs) |
| `summary.json` | Counts by subject, chapter, shift and type |

## Solving them on another laptop

```
copy datasets\jee-main-2026\pipeline-pack.jsonl solution-pipeline\data\questions.jsonl
cd solution-pipeline
python pipeline/run_batch.py --shard 2/2
```
Send back `solution-pipeline/data/results/*.json`; they are published from the machine with database access.

## Notes
- Source: questions and keys transcribed by ExamsNet from the official papers; figures carry the ExamsNet watermark until replaced.
- A small share of source keys are wrong and some texts are incomplete; the solution pipeline flags them (`key_mismatch`). Known: `PYQ-MATH-c040a14493cf` (key 11, correct answer 6), `PYQ-CHEM-69229726df9c` (question text cut off at the source).
- Contains answer keys: keep the repository private before sharing it widely.
