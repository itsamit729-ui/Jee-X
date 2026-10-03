import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import datetime, timedelta
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base, get_db
from app.deps import get_current_db_user
from app.routers.roadmap import router
from app.routers.subject_tests import router as builder
from app.routers.subject_test_attempts import router as grader
from app.services.roadmap import task_progress, make_plan, DEFAULTS, scenario
from app.services.predictor import _raw_score_and_max


@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        for uid in (1, 2):
            db.add(models.User(id=uid, auth0_sub=str(uid), username=f'student{uid}', name='Student'))
        for sid, code in enumerate(('PHY', 'CHEM', 'MATH'), 1):
            db.add(models.Subject(id=sid, code=code, name=code))
            db.add(models.Chapter(id=sid, subject_id=sid, name=f'Chapter {code}', slug=code, class_level='11'))
            db.add(models.Subtopic(id=sid, chapter_id=sid, name=f'Topic {code}', slug=code))
            db.flush()
            for i in range(25):
                qid = sid * 100 + i
                numeric = i >= 20
                db.add(models.Question(id=qid, ref=str(qid), subtopic_id=sid, type='numerical' if numeric else 'single_correct',
                    stem='Question', solution='Solution', difficulty=3, expected_time_sec=90,
                    answer_min=2 if numeric else None, answer_max=2 if numeric else None,
                    source_type='original', status='published', version=1, content_hash=str(qid)))
                db.flush()
                db.add(models.QuestionRevision(question_id=qid, version=1, content={}))
                if not numeric:
                    for k in range(2):
                        db.add(models.QuestionOption(question_id=qid, label='AB'[k], content='Option', is_correct=k == 0, position=k + 1))
        db.commit()
    app = FastAPI()
    for r in (router, builder, grader):
        app.include_router(r)
    active = [1]
    def database():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_db_user] = lambda: models.User(id=active[0])
    with TestClient(app) as client:
        yield client, factory, active
    engine.dispose()


def test_plan_persistence_validation_and_user_isolation(setup):
    client, factory, active = setup
    response = client.get('/api/roadmap')
    assert response.status_code == 200, response.text
    initial = response.json()
    assert not initial['saved'] and initial['baseline']['score'] is None
    assert initial['current']['rank_low'] is None
    assert client.put('/api/roadmap', json={'weekly_hours': 0}).status_code == 422
    saved = client.put('/api/roadmap', json={'goal_type': 'marks', 'target_marks': 160}).json()
    assert saved['saved'] and sum(t['minutes'] for t in saved['plan']['tasks']) <= saved['settings']['weekly_hours'] * 60
    assert client.get('/api/roadmap').json()['plan'] == saved['plan']
    again = client.put('/api/roadmap', json={'goal_type': 'marks', 'target_marks': 180}).json()
    assert len(again['checkpoints']) == 1
    active[0] = 2
    other = client.get('/api/roadmap').json()
    assert not other['saved'] and other['settings']['target_marks'] == 150


def test_balanced_assessment_server_scoring_and_baseline(setup, monkeypatch):
    from app.services import rewards
    # Coins are separately tested; keep this assessment test independent of reward catalog fixtures.
    monkeypatch.setattr(rewards, 'lock_wallet', lambda *a: None)
    monkeypatch.setattr(rewards, 'total_correct_answers', lambda *a: 0)
    monkeypatch.setattr(rewards, 'check_and_award_milestones', lambda *a: 0)
    client, factory, active = setup
    client.put('/api/roadmap', json={})
    response = client.post('/api/subject-tests', json={'assessment': True})
    assert response.status_code == 201, response.text
    paper = response.json()
    assert paper['duration_sec'] == 10800 and len(paper['questions']) == 75
    assert all(q['marks_wrong'] == 1 and q['recommendation'] is None for q in paper['questions'])
    assert all('solution' not in q for q in paper['questions'])
    numeric = [q for q in paper['questions'] if q['type'] == 'numerical']
    assert len(numeric) == 15
    answers = [{'question_id': q['question_id'], 'numeric_answer': 999, 'time_taken_sec': 10} if q['type'] == 'numerical'
               else {'question_id': q['question_id'], 'option_ids': [q['options'][0]['id']], 'time_taken_sec': 30}
               for q in paper['questions']]
    active[0] = 2
    assert client.post(f"/api/subject-tests/attempts/{paper['attempt_id']}/submit", json={'answers': answers}).status_code == 404
    active[0] = 1
    inserts = []
    engine = factory.kw['bind']
    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('INSERT INTO QUESTION_RESPONSES'):
            inserts.append(executemany)
    event.listen(engine, 'before_cursor_execute', capture)
    response = client.post(f"/api/subject-tests/attempts/{paper['attempt_id']}/submit", json={'answers': answers})
    event.remove(engine, 'before_cursor_execute', capture)
    assert inserts == [True], 'A full paper should persist responses in one batch'

    assert response.status_code == 200, response.text
    result = response.json()
    assert result['score'] == 225  # 60*4 - 15; numeric wrong answers also lose one mark.
    assert set(result['subject_breakdown']) == {'PHY', 'CHEM', 'MATH'}
    view = client.get('/api/roadmap').json()
    assert view['baseline']['score'] == 225 and view['baseline']['count'] == 1
    assert client.post('/api/subject-tests', json={'assessment': True}).status_code == 409  # no fresh pool left
    with factory() as db:
        a = db.get(models.TestAttempt, paper['attempt_id'])
        assert _raw_score_and_max(a) == (225, 300)
        assert len(a.responses) == 75
        assert sum(len(r.chosen_options) for r in a.responses) == 60
        a.started_at = datetime.utcnow() - timedelta(hours=4)
        db.commit()
    assert client.get('/api/roadmap').json()['baseline']['score'] is None


def test_repeated_questions_do_not_manufacture_checkpoints():
    now = datetime.utcnow()
    task = {'subject': 'PHY', 'chapter_id': 1}
    def row(qid, fresh=True, outcome='correct'):
        return SimpleNamespace(question_id=qid, subject='PHY', chapter_id=1, outcome=outcome,
            first_answered=now + timedelta(seconds=1) if fresh else now - timedelta(days=1))
    assert task_progress(task, [row(1)] * 5, now)['answered'] == 1
    assert task_progress(task, [row(i, False) for i in range(5)], now)['answered'] == 0
    assert task_progress(task, [row(i) for i in range(5)], now)['met']
    assert not task_progress(task, [row(i, outcome='wrong') for i in range(5)], now)['met']


def test_college_scenarios_exclude_unresolved_state_and_category_pools(setup):
    _, factory, _ = setup
    with factory() as db:
        db.add(models.PredictorInstitute(id=1, name='Institute'))
        db.add(models.PredictorProgram(id=1, institute_id=1, name='Engineering'))
        db.flush()
        for quota, rank_list, seat in [('AI', 'CRL', 'OPEN'), ('OS', 'CRL', 'OPEN'), ('HS', 'CRL', 'OPEN'), ('AI', 'OBC-NCL', 'OBC-NCL')]:
            db.add(models.PredictorJosaaCutoff(year=2025, counselling='JoSAA', round=6,
                institute_id=1, program_id=1, quota=quota, seat_type=seat, gender_pool='Gender-Neutral',
                exam_route='JEE_MAIN_PAPER1', rank_list=rank_list, opening_rank=1, closing_rank=50000))
        db.commit()
        matches = scenario(db, crl=25000)['colleges']
        assert len(matches) == 1 and matches[0]['quota'] == 'AI' and matches[0]['seat_type'] == 'OPEN'
        assert scenario(db, marks=150)['rank_low'] is None


def test_college_goal_choices_and_automatic_settings(setup, monkeypatch):
    client, factory, _ = setup
    with factory() as db:
        db.add(models.PredictorInstitute(id=1, name='Test Institute'))
        db.flush()
        for i in range(1, 5):
            db.add(models.PredictorProgram(id=i, institute_id=1, name=f'Branch {i}'))
        db.flush()
        db.add(models.PredictorJosaaCutoff(year=2025, counselling='JoSAA', round=6,
            institute_id=1, program_id=1, quota='AI', seat_type='OPEN', gender_pool='Gender-Neutral',
            exam_route='JEE_MAIN_PAPER1', rank_list='CRL', opening_rank=1, closing_rank=12000))
        db.commit()
    options = client.get('/api/roadmap/colleges?q=Test').json()
    assert len(options) == 4 and options[0]['institute'] == 'Test Institute'
    assert client.get('/api/roadmap/colleges?q=%25').json() == []
    payload = {'goal_type': 'colleges', 'target_marks': None, 'college_choices': [1, 2, 3]}
    response = client.put('/api/roadmap', json=payload)
    assert response.status_code == 200, response.text
    view = response.json()
    assert view['settings']['target_marks'] is None
    assert len(view['settings']['choices']) == 3 and view['settings']['target_crl'] == 12000
    assert view['settings']['choices'][1]['rank'] is None
    assert view['target']['basis'] == 'college_cutoff'
    assert view['target']['colleges'][0]['program'] == 'Branch 1'
    for choices in ([], [1, 1], [1, 2, 3, 4], [999]):
        assert client.put('/api/roadmap', json={**payload, 'college_choices': choices}).status_code == 422
    assert client.put('/api/roadmap', json={**payload, 'target_marks': 200}).status_code == 422
    assert client.put('/api/roadmap', json={'exam_date': '2028-01-01'}).status_code == 422
    year = view['settings']['target_year']
    monkeypatch.setenv('JEE_MAIN_EXAM_DATES', '{"%s":"%s-12-31"}' % (year, year))
    assert client.get('/api/roadmap').json()['settings']['exam_date'] == f'{year}-12-31'
    monkeypatch.setenv('JEE_MAIN_EXAM_DATES', 'not json')
    assert client.get('/api/roadmap').json()['settings']['exam_date'] is None
    assert client.get('/api/roadmap').json()['settings']['college_choices'] == [1, 2, 3]


def test_start_practice_does_not_rebuild_or_write_the_full_plan(setup, monkeypatch):
    from app.services import topic_plan
    client, factory, _ = setup
    client.put('/api/roadmap', json={})
    with factory() as db:
        before = db.get(models.StudentRoadmap, 1).plan
    def forbidden(*args, **kwargs):
        raise AssertionError('Starting practice must not build a full topic plan')
    monkeypatch.setattr(topic_plan, 'build_topic_plan', forbidden)
    response = client.post('/api/subject-tests', json={'subject_code':'PHY','mode':'recommended','duration_minutes':5})
    assert response.status_code == 201, response.text
    assert len(response.json()['questions']) == 3
    assert response.json()['questions'][0]['recommendation']['milestone_id']
    with factory() as db:
        assert db.get(models.StudentRoadmap, 1).plan == before


@pytest.mark.parametrize('correct', [True, False])
def test_single_daily_submit_query_budget_and_durable_result(setup, correct):
    from datetime import date
    client, factory, _ = setup
    with factory() as db:
        db.add(models.StudentProfile(user_id=1, dob=date(2008, 1, 1),
            class_12_year=2027, target_year=2027, target_exam='jee_main'))
        test = models.Test(title='Daily', kind='daily', pattern='jee_main', duration_sec=120)
        db.add(test)
        db.flush()
        db.add(models.TestQuestion(test_id=test.id, question_id=100, position=1,
                                   marks_correct=4, marks_wrong=1))
        attempt = models.TestAttempt(test_id=test.id, user_id=1)
        db.add(attempt)
        db.flush()
        attempt_id = attempt.id
        option_id = db.query(models.QuestionOption.id).filter_by(question_id=100, is_correct=correct).scalar()
        db.commit()
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement)
    engine = factory.kw['bind']
    event.listen(engine, 'before_cursor_execute', capture)
    try:
        response = client.post(f'/api/subject-tests/attempts/{attempt_id}/submit', json={
            'answers': [{'question_id': 100, 'option_ids': [option_id], 'time_taken_sec': 10}]})
    finally:
        event.remove(engine, 'before_cursor_execute', capture)
    assert response.status_code == 200, response.text
    assert len(statements) <= (8 if correct else 7), statements
    result = response.json()
    assert result['score'] == (4 if correct else -1)
    assert result['questions'][0]['outcome'] == ('correct' if correct else 'wrong')
    assert result['coins_earned'] == 1 and result['current_streak'] == 1
    with factory() as db:
        assert db.get(models.TestAttempt, attempt_id).submitted_at is not None
        saved = db.query(models.QuestionResponse).filter_by(attempt_id=attempt_id).one()
        assert saved.chosen_options[0].option_id == option_id
        assert db.get(models.StudentProfile, 1).edge_coins == 1
    assert client.post(f'/api/subject-tests/attempts/{attempt_id}/submit', json={'answers': []}).status_code == 409
