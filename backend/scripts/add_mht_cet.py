"""CLI: change an existing database so it can hold MHT-CET questions. The app creates missing
tables at startup but never alters existing ones, so these two changes are made here:

  - chapters.in_mht_cet (new column, default false)
  - ck_questions_exam also allows 'mht_cet'

Run it BEFORE deploying a backend whose models have chapters.in_mht_cet: that backend selects the
column and fails on every chapter query while it is missing.

By default this is a dry run: it prints what it would change. Nothing is written unless --apply
is given. Safe to rerun: changes already made are skipped.

Usage (from backend/, with DATABASE_URL and DB_SSL_CA for the target database in the environment):
    ./venv/Scripts/python.exe scripts/add_mht_cet.py            # dry run
    ./venv/Scripts/python.exe scripts/add_mht_cet.py --apply
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402

from app.database import engine  # noqa: E402
from app.models.content import QUESTION_EXAMS  # noqa: E402

EXAM_CHECK = "exam IS NULL OR exam IN (%s)" % ",".join(f"'{e}'" for e in QUESTION_EXAMS)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write to the database (default: dry run)")
    args = parser.parse_args()

    inspector = inspect(engine)
    statements = []
    if "in_mht_cet" not in {c["name"] for c in inspector.get_columns("chapters")}:
        statements.append("ALTER TABLE chapters ADD COLUMN in_mht_cet BOOLEAN NOT NULL DEFAULT 0")
    checks = {c["name"]: c["sqltext"] for c in inspector.get_check_constraints("questions")}
    current = checks.get("ck_questions_exam")
    if current is None:
        statements.append(f"ALTER TABLE questions ADD CONSTRAINT ck_questions_exam CHECK ({EXAM_CHECK})")
    elif "mht_cet" not in current:
        statements.append(f"ALTER TABLE questions DROP CHECK ck_questions_exam, "
                          f"ADD CONSTRAINT ck_questions_exam CHECK ({EXAM_CHECK})")

    if not statements:
        print("Nothing to do: the database already accepts MHT-CET questions.")
        return
    for s in statements:
        print(s)
    if not args.apply:
        print("Dry run: add --apply to make these changes.")
        return
    with engine.begin() as db:
        for s in statements:
            db.execute(text(s))
    print("Done.")


if __name__ == "__main__":
    main()
