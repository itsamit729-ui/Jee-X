"""Persist reviewed college details using the configured DATABASE_URL.

Run from repository root: PYTHONPATH=backend python scripts/import_college_insights.py
Normal deployments run the same sync automatically after the reference-data import.
"""
from sqlalchemy.orm import Session
from app.database import engine
from app.models import CollegeInsight
from app.services.college_insights import sync_insights

if __name__ == '__main__':
    CollegeInsight.__table__.create(engine, checkfirst=True)
    with Session(engine) as db:
        print(sync_insights(db))
