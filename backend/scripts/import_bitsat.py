"""Validated BITSAT import via the existing chapter importer and revision history.
Usage: python scripts/import_bitsat.py ../generated/bitsat [--apply]
Run migrate_bitsat.py first. Default is a read-only validation and import plan.
"""
import argparse
import sys
import tempfile
import json
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'scripts'))
sys.path.insert(0, str(REPO/'backend'))
from validate_bitsat import validate
from import_scraped_pyqs import load_files, plan
from app.database import SessionLocal
from app.importer import import_chapter_file, _get_or_create_subject
from app import models


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    errors, counts = validate(args.root, REPO/'frontend/public')
    if errors:
        raise SystemExit('\n'.join(errors))
    print({f'{year}/{code}': count for (year, code), count in sorted(counts.items())})
    files = load_files(args.root)
    with SessionLocal() as db:
        missing = {data['subject'] for _, data in files} - {s.code for s in db.query(models.Subject).all()}
        if missing and not args.apply:
            print(f'Subjects to create on apply: {sorted(missing)}. File validation passed; DB plan requires these subjects.')
            return
        for code in sorted(missing):
            _get_or_create_subject(db, code)
        adjusted, problems, notes, summary = plan(db, files, None)
        for note in notes:
            print(note)
        if problems:
            db.rollback()
            raise SystemExit('\n'.join(problems))
        print(f"{summary['new']} new, {summary['already_in_db_changed']} changed, {summary['already_in_db_unchanged']} unchanged")
        if not args.apply:
            print('Dry run passed. Use --apply to import.')
            return
        # The existing importer commits each chapter and retains question revisions.
        with tempfile.TemporaryDirectory() as tmp:
            for index, (path, data) in enumerate(adjusted):
                staged = Path(tmp)/f'{index}.json'
                staged.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
                result = import_chapter_file(db, staged)
                run = db.query(models.ImportRun).order_by(models.ImportRun.id.desc()).first()
                run.file_path = str(path)
                db.commit()
                print(f'{path}: {result}')
                if result['errors']:
                    raise SystemExit('Import stopped. Earlier chapters were committed; resolve errors and rerun.')

if __name__ == '__main__':
    main()
