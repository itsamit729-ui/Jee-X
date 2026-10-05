"""Expand existing MySQL CHECK constraints before importing BITSAT content.
Run from backend: python scripts/migrate_bitsat.py [--apply]
MySQL DDL commits implicitly; rerunning safely resumes completed tables.
"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect, text
from app.database import engine

CHANGES = (
    ('subjects', 'ck_subjects_code', "code IN ('PHY','CHEM','MATH','ENG','LR')", 'ENG'),
    ('questions', 'ck_questions_exam', "exam IS NULL OR exam IN ('jee_main','jee_advanced','bitsat')", 'bitsat'),
    ('tests', 'ck_tests_pattern', "pattern IN ('jee_main','jee_advanced','bitsat')", 'bitsat'),
)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if engine.dialect.name != 'mysql':
        raise SystemExit('This migration targets MySQL only.')
    for table, name, expression, marker in CHANGES:
        checks = {c['name']: c['sqltext'] for c in inspect(engine).get_check_constraints(table)}
        if marker.lower() in checks.get(name, '').lower():
            print(f'{table}: already updated')
            continue
        # Replace in one ALTER statement; never leave the table unconstrained.
        drop = f'DROP CHECK `{name}`, ' if name in checks else ''
        statement = f'ALTER TABLE `{table}` {drop}ADD CONSTRAINT `{name}` CHECK ({expression})'
        print(statement)
        if args.apply:
            with engine.begin() as conn:
                conn.execute(text(statement))
    print('Migration complete.' if args.apply else 'Dry run. Use --apply to execute.')

if __name__ == '__main__':
    main()
