"""Export the question pack (data/questions.jsonl) from the database. Read-only.

Includes every published question that does not yet have a verified solution (a question_revisions
row whose change_note starts with "verified-solution", written by publish.py). Questions with an
empty solution come first. Each line carries the answer key; the pipeline keeps the key away from
the solver and only uses it to compare answers and to brief the checker.

Copy data/questions.jsonl to your friend's laptop; they need no database access.

Usage:
  python pipeline/export_questions.py
  python pipeline/export_questions.py --year 2026 --exam jee_main
  python pipeline/export_questions.py --only-missing        # skip questions that already have some solution
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sqlalchemy import text  # noqa: E402

from common import path  # noqa: E402
from db import VERIFIED_NOTE, engine  # noqa: E402

SUBJECT = {"PHY": "Physics", "CHEM": "Chemistry", "MATH": "Mathematics"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int)
    parser.add_argument("--exam", choices=["jee_main", "jee_advanced"])
    parser.add_argument("--subject", choices=sorted(SUBJECT))
    parser.add_argument("--only-missing", action="store_true", help="only questions whose solution is empty")
    args = parser.parse_args()

    where = ["q.status = 'published'",
             "NOT EXISTS (SELECT 1 FROM question_revisions r WHERE r.question_id = q.id AND r.change_note LIKE :note)"]
    params = {"note": f"{VERIFIED_NOTE}%"}
    if args.year:
        where.append("q.year = :year")
        params["year"] = args.year
    if args.exam:
        where.append("q.exam = :exam")
        params["exam"] = args.exam
    if args.subject:
        where.append("s.code = :subject")
        params["subject"] = args.subject
    if args.only_missing:
        where.append("(q.solution IS NULL OR q.solution = '')")

    sql = f"""
        SELECT q.id, q.ref, q.type, q.stem, q.answer_min, q.answer_max, q.solution, q.exam, q.year, q.shift,
               q.content_hash, q.version, s.code AS subject, c.name AS chapter
        FROM questions q
        JOIN subtopics st ON st.id = q.subtopic_id
        JOIN chapters c ON c.id = st.chapter_id
        JOIN subjects s ON s.id = c.subject_id
        WHERE {' AND '.join(where)}
        ORDER BY (q.solution IS NULL OR q.solution = '') DESC, q.year DESC, q.id
    """
    with engine().connect() as db:
        rows = db.execute(text(sql), params).mappings().all()
        ids = [r["id"] for r in rows]
        options, images = {}, {}
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            marks = ",".join(str(x) for x in chunk)
            for o in db.execute(text(f"SELECT question_id, label, content, is_correct FROM question_options "
                                     f"WHERE question_id IN ({marks}) ORDER BY question_id, position")).mappings():
                options.setdefault(o["question_id"], []).append(o)
            for a in db.execute(text(f"SELECT question_id, url FROM assets WHERE question_id IN ({marks}) "
                                     f"AND url IS NOT NULL ORDER BY id")).mappings():
                images.setdefault(a["question_id"], a["url"])

    out = path("questions_file")
    written = 0
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            opts = options.get(r["id"], [])
            item = {
                "ref": r["ref"], "subject": SUBJECT.get(r["subject"], r["subject"]), "chapter": r["chapter"],
                "type": r["type"], "exam": r["exam"], "year": r["year"], "shift": r["shift"], "stem": r["stem"],
                "options": [{"label": o["label"], "content": o["content"]} for o in opts],
                "correct": [o["label"] for o in opts if o["is_correct"]],
                "answer_min": r["answer_min"], "answer_max": r["answer_max"],
                "answer": r["answer_min"] if r["answer_min"] == r["answer_max"] else f"{r['answer_min']} to {r['answer_max']}",
                "image_url": images.get(r["id"]), "had_solution": bool(r["solution"]),
                "content_hash": r["content_hash"], "version": r["version"],
            }
            if item["type"] != "numerical" and not item["correct"]:
                continue  # no key to verify against
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            written += 1
    missing = sum(1 for r in rows if not r["solution"])
    print(f"Wrote {written} questions to {out} ({missing} with no solution yet, "
          f"{sum(1 for r in rows if images.get(r['id']))} with figures)")


if __name__ == "__main__":
    main()
