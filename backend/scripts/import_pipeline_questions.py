"""Validate locally, preview against DB, or import in bounded transactions.

python backend/scripts/import_pipeline_questions.py --validate-only
python backend/scripts/import_pipeline_questions.py --year 2024
python backend/scripts/import_pipeline_questions.py --year 2024 --apply
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services import pipeline_dataset as source


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year',type=int,choices=source.YEARS)
    parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    years=(args.year,) if args.year else source.YEARS
    datasets=[source.dataset(year) for year in years]
    if args.validate_only:
        print(json.dumps([source.summary(data) for data in datasets],indent=2));return
    from app.database import SessionLocal
    from app.services import pipeline_question_import as importer
    with SessionLocal() as db:
        for data in datasets:
            print(json.dumps({**source.summary(data),'database':importer.plan(db,data)},indent=2))
            db.rollback()
            if args.apply:
                for offset in range(0,len(data['questions']),25):
                    print(json.dumps(importer.publish_batch(db,data,offset)))
            else:print('Read-only preview. Add --apply to publish eligible questions.')

if __name__=='__main__':main()
