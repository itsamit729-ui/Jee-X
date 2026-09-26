"""CLI: import scraped PYQ chapter files (generated/scraped/<subject>/*.json) into the database,
through the same importer as import_questions.py, with checks for a live database.

By default this is a dry run: it connects, checks everything read-only and prints a report.
Nothing is written unless --apply is given.

What it does beyond import_questions.py:
  - existing chapters and subtopics keep the name, class, flags and position they have in the
    database; files only add what is missing (new chapters go after the subject's last chapter)
  - characters MySQL's utf8 (3-byte) tables can't store, e.g. math italic 𝜕, are replaced by their
    standard form (∂) before import
  - refuses to run if a question's content hash is already used by a different question, if a
    subject is missing, or if a figure file referenced by a question doesn't exist
  - --status sets the status of the imported questions (default: keep the files' "draft")
  - --retire marks every question in the files as "retired" (the undo: nothing is deleted, so
    tests and responses that already reference the questions stay intact)

Figures are served by the frontend from frontend/public/question-images/pyq/, so they appear only
after the frontend with those files is deployed.

Usage (from backend/, with DATABASE_URL and DB_SSL_CA for the target database in the environment):
    ./venv/Scripts/python.exe scripts/import_scraped_pyqs.py                         # dry run
    ./venv/Scripts/python.exe scripts/import_scraped_pyqs.py --apply                 # import as draft
    ./venv/Scripts/python.exe scripts/import_scraped_pyqs.py --apply --status published
    ./venv/Scripts/python.exe scripts/import_scraped_pyqs.py --retire --apply        # undo
"""

import argparse
import copy
import hashlib
import json
import re
import sys
import tempfile
import time
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, insert, inspect, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.importer import (  # noqa: E402
    _content_hash, _get_or_create_subject, _upsert_chapter, _upsert_subtopics, import_chapter_file,
)

CONNECTION_RETRIES = 3

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_ROOT = REPO / "generated" / "scraped"
PUBLIC = REPO / "frontend" / "public"
STATUSES = ("draft", "reviewed", "published")
REQUIRED_TABLES = ("subjects", "chapters", "subtopics", "questions", "question_options", "assets",
                   "question_subtopics", "question_revisions", "import_runs")


def narrow(text: str) -> str:
    """Replace characters outside the Basic Multilingual Plane with their NFKC form (𝜕 -> ∂)."""
    out = []
    for ch in text:
        if ord(ch) > 0xFFFF:
            ch = unicodedata.normalize("NFKC", ch)
            if any(ord(c) > 0xFFFF for c in ch):
                raise ValueError(f"character {ch!r} has no 3-byte equivalent")
        out.append(ch)
    return "".join(out)


def narrow_all(value):
    if isinstance(value, str):
        return narrow(value)
    if isinstance(value, list):
        return [narrow_all(v) for v in value]
    if isinstance(value, dict):
        return {k: narrow_all(v) for k, v in value.items()}
    return value


def chapter_name(slug: str) -> str:
    small = {"and", "of", "in", "the", "a"}
    words = slug.split("-")
    return " ".join(w if i and w in small else w.capitalize() for i, w in enumerate(words))


def load_files(root: Path):
    files = []
    for path in sorted(root.glob("*/*.json")):
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        files.append((path, narrow_all(json.loads(path.read_text(encoding="utf-8")))))
    return files


def plan(db, files, status):
    """Adjust file data to the database and collect problems. Read-only."""
    problems, notes = [], []
    subjects = {s.code: s for s in db.query(models.Subject).all()}
    next_position = {}
    for code, subject in subjects.items():
        top = db.query(func.max(models.Chapter.position)).filter(models.Chapter.subject_id == subject.id).scalar()
        next_position[code] = (top or 0) + 1

    new_chapters, existing_chapters = [], []
    adjusted = []
    for path, data in files:
        data = copy.deepcopy(data)
        code = data["subject"]
        subject = subjects.get(code)
        if not subject:
            problems.append(f"{path.name}: subject {code} is not in the database")
            continue
        slug = data["chapter"]["slug"]
        chapter = (db.query(models.Chapter)
                   .filter(models.Chapter.subject_id == subject.id, models.Chapter.slug == slug).first())
        if chapter:
            existing_chapters.append(f"{code}/{slug}")
            data["chapter"] = {"name": chapter.name, "slug": slug, "class_level": chapter.class_level,
                               "in_main": chapter.in_main, "in_advanced": chapter.in_advanced,
                               "position": chapter.position}
            db_subtopics = {s.slug: s for s in chapter.subtopics}
            data["subtopics"] = [
                {"slug": s["slug"], "name": db_subtopics[s["slug"]].name, "position": db_subtopics[s["slug"]].position}
                if s["slug"] in db_subtopics else s
                for s in data["subtopics"]
            ]
        else:
            if data["chapter"]["name"] == slug.replace("-", " ").title():
                data["chapter"]["name"] = chapter_name(slug)
            data["chapter"]["position"] = next_position[code]
            next_position[code] += 1
            new_chapters.append(f"{code}/{slug} ({data['chapter']['name']}, class {data['chapter']['class_level']})")

        for q in data["questions"]:
            if status:
                q["status"] = status
            if q.get("image"):
                image_file = PUBLIC / q["image"]["url"].lstrip("/")
                if not image_file.is_file():
                    problems.append(f"{q['ref']}: figure file missing: {image_file}")
        adjusted.append((path, data))

    questions = [q for _, data in adjusted for q in data["questions"]]
    refs = [q["ref"] for q in questions]
    if len(refs) != len(set(refs)):
        dupes = [r for r, n in Counter(refs).items() if n > 1]
        problems.append(f"{len(dupes)} refs appear in more than one file, e.g. {dupes[:3]}")

    existing = {}
    for i in range(0, len(refs), 500):
        for q in db.query(models.Question).filter(models.Question.ref.in_(refs[i:i + 500])):
            existing[q.ref] = q
    hashes = {_content_hash(q): q["ref"] for q in questions}
    for i in range(0, len(hashes), 500):
        chunk = list(hashes)[i:i + 500]
        for ref, h in db.query(models.Question.ref, models.Question.content_hash).filter(
                models.Question.content_hash.in_(chunk)):
            if hashes[h] != ref:
                problems.append(f"{hashes[h]}: same content as existing question {ref}")
    unchanged = sum(1 for q in questions if q["ref"] in existing and existing[q["ref"]].content_hash == _content_hash(q))

    # Same exam/year/shift and stem as an existing question under another ref: likely a duplicate.
    def norm(text):
        return re.sub(r"\W+", "", text.lower())
    keys = {(q.get("exam"), q.get("year"), norm(q["stem"])) for q in questions}
    years = {q.get("year") for q in questions}
    others = (db.query(models.Question.ref, models.Question.exam, models.Question.year, models.Question.stem)
              .filter(models.Question.year.in_(years), ~models.Question.ref.in_(refs)).all()) if years else []
    duplicates = [ref for ref, exam, year, stem in others if (exam, year, norm(stem)) in keys]
    if duplicates:
        notes.append(f"{len(duplicates)} existing questions under other refs have the same text and year, "
                     f"e.g. {duplicates[:5]} (not changed)")

    return adjusted, problems, notes, {
        "files": len(adjusted), "questions": len(questions), "new": len(questions) - len(existing),
        "already_in_db_unchanged": unchanged, "already_in_db_changed": len(existing) - unchanged,
        "new_chapters": new_chapters, "existing_chapters": existing_chapters,
        "with_figures": sum(1 for q in questions if q.get("image")),
        "status": Counter(q.get("status", "draft") for q in questions),
    }


def fast_import_file(db, rel_path: str, data: dict):
    """Same rows as app.importer.import_chapter_file, written in a few batched statements.

    The importer makes ~10 round trips per question, which is minutes per file against a remote
    database. Chapter/subtopic upserts reuse the importer's own helpers; new questions and their
    options, figure, extra subtopics and first revision are inserted in bulk, in one transaction per
    file. Returns None (caller falls back to the importer) if a question already in the database has
    changed, since updating needs the importer's versioning.
    """
    if data.get("passages"):
        return None
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    subject = _get_or_create_subject(db, data["subject"])
    chapter = _upsert_chapter(db, subject, data["chapter"])
    subtopics = _upsert_subtopics(db, chapter, data.get("subtopics", []))

    questions = data.get("questions", [])
    refs = [q["ref"] for q in questions]
    existing = dict(db.query(models.Question.ref, models.Question.content_hash)
                    .filter(models.Question.ref.in_(refs)).all()) if refs else {}
    new, errors = [], []
    for q in questions:
        if q["subtopic"] not in subtopics:
            errors.append(f"{q['ref']}: unknown subtopic slug {q['subtopic']!r}")
            continue
        content_hash = _content_hash(q)
        if q["ref"] in existing:
            if existing[q["ref"]] != content_hash:
                db.rollback()
                return None
            continue
        new.append((q, content_hash))

    run = models.ImportRun(file_path=rel_path, file_hash=hashlib.sha256(payload).hexdigest(), run_by=None)
    db.add(run)
    db.flush()
    if new:
        db.execute(insert(models.Question), [{
            "ref": q["ref"], "subtopic_id": subtopics[q["subtopic"]].id, "passage_id": None,
            "type": q["type"], "stem": q["stem"],
            "answer_min": (q.get("answer") or {}).get("min"), "answer_max": (q.get("answer") or {}).get("max"),
            "solution": q["solution"], "difficulty": q["difficulty"], "expected_time_sec": q["expected_time_sec"],
            "source_type": q["source_type"], "exam": q.get("exam"), "year": q.get("year"), "shift": q.get("shift"),
            "status": q.get("status", "draft"), "content_hash": content_hash, "version": 1,
        } for q, content_hash in new])
        ids = dict(db.query(models.Question.ref, models.Question.id)
                   .filter(models.Question.ref.in_([q["ref"] for q, _ in new])).all())
        options = [{"question_id": ids[q["ref"]], "label": o["label"], "content": o["content"],
                    "is_correct": o["is_correct"], "position": i}
                   for q, _ in new for i, o in enumerate(q.get("options", []), start=1)]
        assets = [{"question_id": ids[q["ref"]], "passage_id": None, "url": q["image"].get("url"),
                   "alt_text": q["image"].get("alt", "")} for q, _ in new if q.get("image")]
        also = [{"question_id": ids[q["ref"]], "subtopic_id": subtopics[slug].id}
                for q, _ in new for slug in set(q.get("also_subtopics", [])) if slug in subtopics]
        revisions = [{"question_id": ids[q["ref"]], "version": 1, "content": q, "import_run_id": run.id}
                     for q, _ in new]
        for model, rows in ((models.QuestionOption, options), (models.Asset, assets),
                            (models.QuestionSubtopic, also), (models.QuestionRevision, revisions)):
            if rows:
                db.execute(insert(model), rows)
    run.added, run.updated, run.errors = len(new), 0, errors or None
    db.commit()
    return {"added": len(new), "updated": 0, "errors": errors}


def check_database(db):
    problems, notes = [], []
    tables = set(inspect(engine).get_table_names())
    missing = [t for t in REQUIRED_TABLES if t not in tables]
    if missing:
        problems.append(f"missing tables: {missing}")
    if engine.dialect.name == "mysql":
        schema = db.execute(text("SELECT DATABASE()")).scalar()
        collations = dict(db.execute(text(
            "SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA = :schema "
            "AND TABLE_NAME IN ('questions','question_options','assets','chapters','subtopics')"),
            {"schema": schema}).all())
        notes.append(f"database {schema}, table collations {collations}")
    total = db.query(func.count(models.Question.id)).scalar()
    by_status = dict(db.query(models.Question.status, func.count()).group_by(models.Question.status).all())
    by_year = dict(db.query(models.Question.year, func.count()).group_by(models.Question.year).all())
    notes.append(f"existing questions: {total}, by status {by_status}, by year {by_year}")
    return problems, notes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", nargs="?", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--apply", action="store_true", help="write to the database (default: dry run)")
    parser.add_argument("--status", choices=STATUSES, help="status for the imported questions (default: as in files)")
    parser.add_argument("--retire", action="store_true", help="undo: mark every question in the files retired")
    parser.add_argument("--slow", action="store_true", help="use the row-by-row importer for every file")
    args = parser.parse_args()
    root = args.root.resolve()

    files = load_files(root)
    if not files:
        sys.exit(f"No chapter files under {root}")
    print(f"Target database: {engine.url.render_as_string(hide_password=True)}")

    db = SessionLocal()
    try:
        if args.retire:
            refs = [q["ref"] for _, data in files for q in data["questions"]]
            query = db.query(models.Question).filter(models.Question.ref.in_(refs))
            print(f"{query.count()} of {len(refs)} questions from the files are in the database.")
            if args.apply:
                changed = query.update({models.Question.status: "retired"}, synchronize_session=False)
                db.commit()
                print(f"Retired {changed} questions.")
            else:
                print("Dry run: add --apply to retire them.")
            return

        db_problems, db_notes = check_database(db)
        adjusted, problems, notes, summary = plan(db, files, args.status)
        problems = db_problems + problems
        for note in db_notes + notes:
            print(f"note: {note}")
        print(json.dumps({k: (dict(v) if isinstance(v, Counter) else v) for k, v in summary.items()}, indent=2))
        if problems:
            print(f"\n{len(problems)} problem(s); nothing written:")
            for p in problems[:50]:
                print(f"  - {p}")
            sys.exit(1)
        if not args.apply:
            print("\nDry run OK. Add --apply to import.")
            return
        db.rollback()  # end the read-only transaction before importing

        totals = {"added": 0, "updated": 0, "errors": []}
        with tempfile.TemporaryDirectory() as tmp:
            for path, data in adjusted:
                rel_path = str(path.relative_to(REPO)).replace("\\", "/")
                for attempt in range(1, CONNECTION_RETRIES + 1):
                    try:
                        result = None if args.slow else fast_import_file(db, rel_path, data)
                        if result is None:  # --slow, or questions changed since an earlier import
                            temp_file = Path(tmp) / path.name
                            temp_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                            result = import_chapter_file(db, temp_file)
                            run = db.query(models.ImportRun).order_by(models.ImportRun.id.desc()).first()
                            run.file_path = rel_path
                            db.commit()
                        break
                    except OperationalError as e:
                        # Dropped connection: the file's transaction didn't commit, so retry it whole.
                        db.rollback()
                        db.close()
                        engine.dispose()
                        db = SessionLocal()
                        if attempt == CONNECTION_RETRIES:
                            print(f"FAILED on {rel_path} after {attempt} tries; earlier files are imported, this one is not.")
                            raise
                        print(f"  connection lost on {rel_path} ({e.orig}); retrying")
                        time.sleep(5 * attempt)
                    except Exception:
                        db.rollback()
                        print(f"FAILED on {rel_path}; earlier files are imported, this one is not.")
                        raise
                totals["added"] += result["added"]
                totals["updated"] += result["updated"]
                totals["errors"] += [f"{path.name}: {e}" for e in result["errors"]]
                print(f"  {path.relative_to(root)}: +{result['added']} ~{result['updated']}"
                      f"{' errors: ' + str(result['errors']) if result['errors'] else ''}")

        refs = [q["ref"] for _, data in adjusted for q in data["questions"]]
        stored = db.query(models.Question).filter(models.Question.ref.in_(refs))
        by_status = dict(stored.with_entities(models.Question.status, func.count()).group_by(models.Question.status).all())
        options = (db.query(func.count(models.QuestionOption.id)).join(models.Question)
                   .filter(models.Question.ref.in_(refs)).scalar())
        assets = (db.query(func.count(models.Asset.id)).join(models.Question, models.Asset.question_id == models.Question.id)
                  .filter(models.Question.ref.in_(refs)).scalar())
        print(f"\nImported: added {totals['added']}, updated {totals['updated']}, errors {len(totals['errors'])}")
        for e in totals["errors"]:
            print(f"  - {e}")
        print(f"In database now: {stored.count()} of {len(refs)} questions, by status {by_status}, "
              f"{options} options, {assets} figures")
    finally:
        db.close()


if __name__ == "__main__":
    main()
