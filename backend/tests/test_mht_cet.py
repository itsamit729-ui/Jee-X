"""MHT-CET questions are stored under their own exam and stay out of what JEE students practise."""
import json
import os
from datetime import date

os.environ.setdefault("DATABASE_URL", "mysql+pymysql://test:test@localhost/unused")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.importer import import_chapter_file
from app.routers.daily_question import _pick_question
from app.routers.subjects import router


def chapter_file(tmp_path, name, chapter, exam, ref):
    options = [{"label": label, "content": label, "is_correct": label == "B"} for label in "ABCD"]
    question = {"ref": ref, "subtopic": "general", "type": "single_correct", "difficulty": 5, "expected_time_sec": 120,
                "source_type": "pyq", "exam": exam, "year": 2026, "shift": "20 May 2026, Shift 1",
                "status": "published", "stem": f"Question {ref}", "image": None, "options": options, "solution": "Because."}
    path = tmp_path / name
    path.write_text(json.dumps({
        "subject": "PHY", "chapter": chapter, "passages": [], "questions": [question],
        "subtopics": [{"slug": "general", "name": "General", "position": 99}]}), encoding="utf-8")
    return path


def test_mht_cet_questions_are_stored_but_not_served_to_jee_students(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    shared = {"name": "Waves", "slug": "waves", "class_level": "11", "in_main": True, "in_advanced": True, "position": 1}
    mht_only = {"name": "Communication Systems", "slug": "communication-systems", "class_level": "12",
                "in_main": False, "in_advanced": False, "in_mht_cet": True, "position": 2}
    with Session() as db:
        db.add(models.User(id=1, auth0_sub="one", username="one", name="One"))
        for name, chapter, exam, ref in [("mht-waves.json", {**shared, "in_mht_cet": True}, "mht_cet", "PYQ-PHY-mht1"),
                                         ("mht-only.json", mht_only, "mht_cet", "PYQ-PHY-mht2"),
                                         ("jee-waves.json", shared, "jee_main", "PYQ-PHY-jee1")]:
            result = import_chapter_file(db, chapter_file(tmp_path, name, chapter, exam, ref))
            assert not result["errors"], result
        db.commit()

        assert {q.ref: q.exam for q in db.query(models.Question)} == {
            "PYQ-PHY-mht1": "mht_cet", "PYQ-PHY-mht2": "mht_cet", "PYQ-PHY-jee1": "jee_main"}
        # The JEE file was imported last and has no in_mht_cet: the flag set by the MHT-CET file stays.
        waves = db.query(models.Chapter).filter_by(slug="waves").one()
        assert (waves.in_main, waves.in_mht_cet) == (True, True)
        # With the JEE question already assigned, there is nothing left for the daily question.
        user = db.get(models.User, 1)
        assert _pick_question(db, user).ref == "PYQ-PHY-jee1"
        db.add(models.DailyQuestionAssignment(user_id=1, question_id=_pick_question(db, user).id,
                                              assigned_date=date(2026, 10, 11)))
        db.flush()
        assert _pick_question(db, user) is None

    def get_test_db():
        with Session() as db:
            yield db

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = get_test_db
    client = TestClient(app)
    assert client.get("/api/subjects").json() == [
        {"code": "PHY", "name": "Physics", "chapter_count": 1, "published_question_count": 1}]
    chapters = client.get("/api/subjects/PHY/chapters").json()
    assert [(c["slug"], c["published_question_count"]) for c in chapters] == [("waves", 1)]
