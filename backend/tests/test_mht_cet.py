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


def test_year_shift_papers_include_all_subjects_and_questions_without_leaking_keys():
    from app.deps import get_current_db_user
    from app.routers.pyqs import router as pyq_router
    from app.routers.subject_test_attempts import router as grader
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(models.User(id=1, auth0_sub='paper', username='paper', name='Paper'))
        db.add(models.StudentProfile(user_id=1, dob=date(2006, 1, 1), class_12_year=2027,
                                     target_year=2027, target_exam='jee_main'))
        for sid, code in enumerate(['PHY', 'CHEM', 'MATH'], 1):
            db.add(models.Subject(id=sid, code=code, name=code))
            db.add(models.Chapter(id=sid, subject_id=sid, name=code, slug=code, class_level='12'))
            db.add(models.Subtopic(id=sid, chapter_id=sid, name=code, slug=code))
        db.flush()
        for i in range(1, 41):
            q = models.Question(id=i, ref=f'PAPER-{i:03}', subtopic_id=(i % 3)+1,
                type='single_correct', stem=f'Fixture {i}', solution='', difficulty=3, expected_time_sec=90,
                source_type='pyq', exam='mht_cet' if i != 40 else 'jee_main', year=2026 if i != 39 else 2025,
                shift='11 Apr 2026, Shift 1' if i != 38 else '12 Apr 2026, Shift 2',
                status='draft' if i == 37 else 'published', version=1, content_hash=str(i))
            db.add(q)
            db.flush()
            db.add(models.QuestionRevision(question_id=i, version=1, content={}))
            for j in range(4):
                db.add(models.QuestionOption(question_id=i, label='ABCD'[j], content=str(j),
                                              is_correct=j == 0, position=j+1))
        db.commit()
    def database():
        with factory() as db:
            yield db
    app = FastAPI()
    app.include_router(pyq_router)
    app.include_router(grader)
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_db_user] = lambda: models.User(id=1)
    client = TestClient(app)
    catalog = client.get('/api/pyqs/mht_cet').json()
    year = next(y for y in catalog['years'] if y['year'] == 2026)
    assert [(p['shift'], p['available']) for p in year['papers']] == [
        ('11 Apr 2026, Shift 1', 36), ('12 Apr 2026, Shift 2', 1)]
    assert len(year['papers'][0]['subjects']) == 3
    response = client.post('/api/pyqs/mht_cet/papers', json={'year': 2026, 'shift': '11 Apr 2026, Shift 1'})
    assert response.status_code == 201, response.text
    paper = response.json()
    assert paper['is_mock'] is True
    with factory() as db:
        assert db.get(models.Test, paper['test_id']).kind == 'mock'
    assert {q['subject_code'] for q in paper['questions']} == {'PHY', 'CHEM', 'MATH'}
    assert len(paper['questions']) == 36  # must not truncate at the subject-practice limit
    assert paper['subject_code'] == 'PCM' and paper['duration_sec'] == 10800
    assert sum(q['marks_correct'] for q in paper['questions']) == 48
    assert all(q['marks_wrong'] == 0 and 'solution' not in q for q in paper['questions'])
    assert all('is_correct' not in o for q in paper['questions'] for o in q['options'])
    answers = [{'question_id': q['question_id'], 'option_ids': [q['options'][0]['id']]} for q in paper['questions']]
    result = client.post(f"/api/subject-tests/attempts/{paper['attempt_id']}/submit", json={'answers': answers})
    assert result.status_code == 200, result.text
    assert result.json()['score'] == 48
    assert client.post('/api/pyqs/mht_cet/papers', json={'year': 2024, 'shift': '11 Apr 2026, Shift 1'}).status_code == 404
