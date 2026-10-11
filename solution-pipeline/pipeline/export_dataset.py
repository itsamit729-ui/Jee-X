"""Export a clean question dataset for one exam year from the database (read-only).

Writes datasets/<exam>-<year>/ in the repository:
  questions.jsonl      every published question of that year: text, options, key, figure, chapter,
                       and the solution only when it has been verified (publish.py)
  pipeline-pack.jsonl  the questions still without a verified solution, in the solution pipeline's
                       pack format: copy it to solution-pipeline/data/questions.jsonl to solve them
  pending.jsonl        scraped questions not imported yet (image options, several figures, missing key)
  summary.json         counts by subject, chapter, shift and type
  README.md            what is here and how to use it

Usage (database machine):
  python pipeline/export_dataset.py --year 2026
  python pipeline/export_dataset.py --year 2026 --exam jee_main
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sqlalchemy import text  # noqa: E402

from common import HOME  # noqa: E402
from db import VERIFIED_NOTE, engine  # noqa: E402

SUBJECT = {"PHY": "Physics", "CHEM": "Chemistry", "MATH": "Mathematics"}
SUBJECT_DIR = {"PHY": "physics", "CHEM": "chemistry", "MATH": "mathematics"}
EXAM_NAME = {"jee_main": "JEE Main", "jee_advanced": "JEE Advanced"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--exam", default="jee_main", choices=sorted(EXAM_NAME))
    args = parser.parse_args()
    repo = HOME.parent
    out = repo / "datasets" / f"{args.exam.replace('_', '-')}-{args.year}"
    out.mkdir(parents=True, exist_ok=True)

    with engine().connect() as db:
        rows = db.execute(text("""
            SELECT q.id, q.ref, q.type, q.stem, q.answer_min, q.answer_max, q.solution, q.difficulty,
                   q.expected_time_sec, q.exam, q.year, q.shift, q.status, q.content_hash, q.version,
                   s.code AS subject, c.name AS chapter, c.slug AS chapter_slug, c.class_level,
                   st.name AS subtopic,
                   EXISTS (SELECT 1 FROM question_revisions r WHERE r.question_id = q.id
                           AND r.change_note LIKE :note) AS verified
            FROM questions q
            JOIN subtopics st ON st.id = q.subtopic_id
            JOIN chapters c ON c.id = st.chapter_id
            JOIN subjects s ON s.id = c.subject_id
            WHERE q.year = :year AND q.exam = :exam AND q.status = 'published'
            ORDER BY s.code, c.position, c.slug, q.shift, q.ref"""),
            {"note": f"{VERIFIED_NOTE}%", "year": args.year, "exam": args.exam}).mappings().all()
        ids = ",".join(str(r["id"]) for r in rows) or "0"
        options, images = defaultdict(list), {}
        for o in db.execute(text(f"SELECT question_id, label, content, is_correct FROM question_options "
                                 f"WHERE question_id IN ({ids}) ORDER BY question_id, position")).mappings():
            options[o["question_id"]].append(o)
        for a in db.execute(text(f"SELECT question_id, url, alt_text FROM assets WHERE question_id IN ({ids}) "
                                 f"AND url IS NOT NULL ORDER BY id")).mappings():
            images.setdefault(a["question_id"], a)

    full, pack = [], []
    for r in rows:
        opts = options[r["id"]]
        image = images.get(r["id"])
        answer = r["answer_min"] if r["answer_min"] == r["answer_max"] else f"{r['answer_min']} to {r['answer_max']}"
        item = {
            "ref": r["ref"], "exam": r["exam"], "year": r["year"], "shift": r["shift"],
            "subject": SUBJECT[r["subject"]], "chapter": r["chapter"], "chapter_slug": r["chapter_slug"],
            "class_level": r["class_level"], "subtopic": r["subtopic"], "type": r["type"],
            "stem": r["stem"],
            "options": [{"label": o["label"], "content": o["content"], "is_correct": bool(o["is_correct"])} for o in opts],
            "answer": answer if r["type"] == "numerical" else ",".join(o["label"] for o in opts if o["is_correct"]),
            "figure": {"url": image["url"], "alt": image["alt_text"]} if image else None,
            "solution": r["solution"] if r["verified"] else None,
            "solution_verified": bool(r["verified"]),
            "difficulty": r["difficulty"], "expected_time_sec": r["expected_time_sec"],
        }
        full.append(item)
        if not r["verified"]:
            pack.append({
                "ref": r["ref"], "subject": SUBJECT[r["subject"]], "chapter": r["chapter"], "type": r["type"],
                "exam": r["exam"], "year": r["year"], "shift": r["shift"], "stem": r["stem"],
                "options": [{"label": o["label"], "content": o["content"]} for o in opts],
                "correct": [o["label"] for o in opts if o["is_correct"]],
                "answer_min": r["answer_min"], "answer_max": r["answer_max"], "answer": answer,
                "image_url": image["url"] if image else None, "had_solution": bool(r["solution"]),
                "content_hash": r["content_hash"], "version": r["version"],
            })

    pending = []
    for f in sorted((repo / "generated" / "scraped" / ".pending").glob("*/*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for q in data.get("questions", []):
            if q.get("year") == args.year and q.get("exam") == args.exam:
                pending.append({**q, "subject": SUBJECT[data["subject"]], "chapter": data["chapter"]["name"],
                                "chapter_slug": data["chapter"]["slug"]})

    def write_jsonl(name, items):
        (out / name).write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8")

    write_jsonl("questions.jsonl", full)
    write_jsonl("pipeline-pack.jsonl", pack)
    write_jsonl("pending.jsonl", pending)

    by_chapter = defaultdict(Counter)
    for q in full:
        by_chapter[q["subject"]][q["chapter"]] += 1
    summary = {
        "exam": EXAM_NAME[args.exam], "year": args.year, "questions": len(full),
        "verified_solutions": sum(q["solution_verified"] for q in full), "pending_not_imported": len(pending),
        "by_subject": dict(Counter(q["subject"] for q in full)),
        "by_type": dict(Counter(q["type"] for q in full)),
        "with_figure": sum(1 for q in full if q["figure"]),
        "by_shift": dict(sorted(Counter(q["shift"] for q in full).items())),
        "by_chapter": {s: dict(sorted(c.items())) for s, c in sorted(by_chapter.items())},
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme = f"""# {EXAM_NAME[args.exam]} {args.year} — question dataset

{len(full)} published questions from all {len(summary['by_shift'])} shifts of {EXAM_NAME[args.exam]} {args.year}, exactly as they are in the Jee Edge database
({summary['by_subject'].get('Physics', 0)} physics, {summary['by_subject'].get('Chemistry', 0)} chemistry, {summary['by_subject'].get('Mathematics', 0)} mathematics;
{summary['by_type'].get('single_correct', 0)} single-correct, {summary['by_type'].get('numerical', 0)} numerical; {summary['with_figure']} with a figure).
{summary['verified_solutions']} have a verified solution. Rebuild this folder with `python solution-pipeline/pipeline/export_dataset.py --year {args.year}`.

| File | Contents |
|---|---|
| `questions.jsonl` | One question per line: `ref`, `shift`, `subject`, `chapter`, `type`, `stem` (LaTeX in `$...$`), `options` with `is_correct`, `answer`, `figure` (URL on the site, file in `frontend/public`), `solution` (only when verified) |
| `pipeline-pack.jsonl` | The {len(pack)} questions still without a verified solution, in the solution pipeline's format |
| `pending.jsonl` | {len(pending)} scraped questions not imported yet: options drawn as images, several figures, or a missing key at the source (with `pending_reasons` and the source figure URLs) |
| `summary.json` | Counts by subject, chapter, shift and type |

## Solving them on another laptop

```
copy datasets\\{out.name}\\pipeline-pack.jsonl solution-pipeline\\data\\questions.jsonl
cd solution-pipeline
python pipeline/run_batch.py --shard 2/2
```
Send back `solution-pipeline/data/results/*.json`; they are published from the machine with database access.

## Notes
- Source: questions and keys transcribed by ExamsNet from the official papers; figures carry the ExamsNet watermark until replaced.
- A small share of source keys are wrong and some texts are incomplete; the solution pipeline flags them (`key_mismatch`). Known: `PYQ-MATH-c040a14493cf` (key 11, correct answer 6), `PYQ-CHEM-69229726df9c` (question text cut off at the source).
- Contains answer keys: keep the repository private before sharing it widely.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print(f"Wrote {out}: {len(full)} questions ({summary['verified_solutions']} with verified solutions), "
          f"{len(pack)} in the pipeline pack, {len(pending)} pending")


if __name__ == "__main__":
    main()
