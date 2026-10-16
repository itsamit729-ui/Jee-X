# JEE Main 2025 — question dataset

1297 questions from all 19 shifts of JEE Main 2025, from the scraped question files (not imported into the database yet)
(440 physics, 394 chemistry, 463 mathematics;
1020 single-correct, 277 numerical; 145 with a figure).
724 have a verified solution. Rebuild this folder with `python solution-pipeline/pipeline/export_dataset.py --year 2025 --from-files`.

## Where the answers come from (`answer_source`)
- `pipeline-two-solves-checked` (716): solution pipeline key mode: two independent solves agree and the checker accepts the solution
- `pw-jee-main-math` (356): PhysicsWallahAI/JEE-Main-2025-Math dataset (NTA-verified), matched by text
- `examsnet` (225): ExamsNet's own key (scraped before Oct 2026)

Every numerical answer not taken from ExamsNet was checked against NTA's official final key: it must be one of the numerical answers NTA lists for that shift and subject, or it was left out.


| File | Contents |
|---|---|
| `questions.jsonl` | One question per line: `ref`, `shift`, `subject`, `chapter`, `type`, `stem` (LaTeX in `$...$`), `options` with `is_correct`, `answer`, `figure` (URL on the site, file in `frontend/public`), `solution` (only when verified) |
| `pipeline-pack.jsonl` | The 573 questions still without a verified solution, in the solution pipeline's format |
| `pending.jsonl` | 118 scraped questions not imported yet: options drawn as images, several figures, or a missing key at the source (with `pending_reasons` and the source figure URLs) |
| `summary.json` | Counts by subject, chapter, shift and type |

## Solving them on another laptop

```
copy datasets\jee-main-2025\pipeline-pack.jsonl solution-pipeline\data\questions.jsonl
cd solution-pipeline
python pipeline/run_batch.py --shard 2/2
```
Send back `solution-pipeline/data/results/*.json`; they are published from the machine with database access.

## Notes
- Source: questions and keys transcribed by ExamsNet from the official papers; figures carry the ExamsNet watermark until replaced.
- A small share of source keys are wrong and some texts are incomplete; the solution pipeline flags them (`key_mismatch`).
- Contains answer keys: keep the repository private before sharing it widely.
