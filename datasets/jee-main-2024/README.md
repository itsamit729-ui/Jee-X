# JEE Main 2024 — question dataset

1684 questions from all 20 shifts of JEE Main 2024, from the scraped question files (not imported into the database yet)
(576 physics, 524 chemistry, 584 mathematics;
1103 single-correct, 581 numerical; 157 with a figure).
286 have a verified solution. Rebuild this folder with `python solution-pipeline/pipeline/export_dataset.py --year 2024 --from-files`.

## Where the answers come from (`answer_source`)
- `grafite-jee-mains` (1336): grafite JEE Mains dataset, matched by text within the same shift
- `pipeline-two-solves-checked` (286): solution pipeline key mode: two independent solves agree and the checker accepts the solution
- `examsnet` (62): ExamsNet's own key (scraped before Oct 2026)

Every numerical answer not taken from ExamsNet was checked against NTA's official final key: it must be one of the numerical answers NTA lists for that shift and subject, or it was left out.


| File | Contents |
|---|---|
| `questions.jsonl` | One question per line: `ref`, `shift`, `subject`, `chapter`, `type`, `stem` (LaTeX in `$...$`), `options` with `is_correct`, `answer`, `figure` (URL on the site, file in `frontend/public`), `solution` (only when verified) |
| `pipeline-pack.jsonl` | The 1398 questions still without a verified solution, in the solution pipeline's format |
| `pending.jsonl` | 98 scraped questions not imported yet: options drawn as images, several figures, or a missing key at the source (with `pending_reasons` and the source figure URLs) |
| `summary.json` | Counts by subject, chapter, shift and type |

## Solving them on another laptop

```
copy datasets\jee-main-2024\pipeline-pack.jsonl solution-pipeline\data\questions.jsonl
cd solution-pipeline
python pipeline/run_batch.py --shard 2/2
```
Send back `solution-pipeline/data/results/*.json`; they are published from the machine with database access.

## Notes
- Source: questions and keys transcribed by ExamsNet from the official papers; figures carry the ExamsNet watermark until replaced.
- A small share of source keys are wrong and some texts are incomplete; the solution pipeline flags them (`key_mismatch`).
- Contains answer keys: keep the repository private before sharing it widely.
