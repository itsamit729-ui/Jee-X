import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.deps import get_current_db_user
from app.routers.subject_tests import router as builder
from app.routers.subject_test_attempts import router as grader
from app.routers.test_attempts import router as attempts

NOW = datetime(2026, 10, 1)


@pytest.fixture
def env():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        for uid in (1, 2):
            db.add(models.User(id=uid, auth0_sub=str(uid), username=f'u{uid}', name='Student'))
            db.add(models.StudentProfile(user_id=uid, dob=date(2006, 1, 1), class_12_year=2027,
                                         target_year=2027, target_exam='jee_main'))
        qid = 0
        for sid, code in enumerate(('PHY', 'CHEM', 'MATH'), 1):
            db.add(models.Subject(id=sid, code=code, name=code))
            for chapter in (1, 2):
                cid = sid * 10 + chapter
                db.add(models.Chapter(id=cid, subject_id=sid, name=f'{code} chapter {chapter}', slug=f'c{cid}', class_level='11'))
                db.add(models.Subtopic(id=cid, chapter_id=cid, name='Topic', slug=f't{cid}'))
            db.flush()
            # 22 single-correct and 6 numerical per subject: enough for one fresh mock, not two.
            for i in range(28):
                qid += 1
                numerical = i >= 22
                db.add(models.Question(id=qid, ref=f'Q{qid}', subtopic_id=sid * 10 + 1 + i % 2,
                                       type='numerical' if numerical else 'single_correct', stem='Stem',
                                       answer_min=2.0 if numerical else None, answer_max=2.0 if numerical else None,
                                       solution=f'Solution {qid}', difficulty=1 + i % 9, expected_time_sec=120,
                                       source_type='original', status='published', content_hash=f'h{qid}'))
                db.add(models.QuestionRevision(question_id=qid, version=1, content={}))
                if not numerical:
                    for j in range(4):
                        db.add(models.QuestionOption(question_id=qid, label='ABCD'[j], content=f'Option {j}',
                                                     is_correct=j == 0, position=j + 1))
        legacy = models.Test(title='Full mock', kind='mock', pattern='jee_main', duration_sec=10800)
        db.add(legacy)
        db.flush()
        db.add(models.TestAttempt(id=500, user_id=1, test_id=legacy.id, submitted_at=NOW, score=40,
                                  total_questions=75, accuracy=50.0, avg_time_seconds=60,
                                  subject_breakdown={'Physics': {'correct': 10, 'total': 25}}))
        db.commit()

    def database():
        with factory() as db:
            yield db
    active = [1]
    app = FastAPI()
    for r in (builder, grader, attempts):
        app.include_router(r)
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_db_user] = lambda: models.User(id=active[0])
    with TestClient(app) as client:
        yield client, factory, active
    engine.dispose()


def answer_all(paper):
    answers = []
    for i, q in enumerate(paper['questions']):
        if i % 3 == 2:
            continue  # skipped
        if q['type'] == 'numerical':
            answers.append({'question_id': q['question_id'], 'numeric_answer': 2.0, 'time_taken_sec': 30})
        else:  # alternate right (option A) and wrong (option B)
            answers.append({'question_id': q['question_id'], 'option_ids': [q['options'][i % 2]['id']], 'time_taken_sec': 90})
    return answers


def test_full_mock_is_server_built_and_reuses_seen_questions(env):
    client, factory, _ = env
    first = client.post('/api/subject-tests', json={'full_mock': True})
    assert first.status_code == 201, first.text
    paper = first.json()
    assert paper['is_mock'] and paper['title'] == 'JEE Main full mock' and paper['duration_sec'] == 10800
    assert len(paper['questions']) == 75
    assert {q['subject_code'] for q in paper['questions']} == {'PHY', 'CHEM', 'MATH'}
    assert all('solution' not in q for q in paper['questions'])
    client.post(f"/api/subject-tests/attempts/{paper['attempt_id']}/submit", json={'answers': answer_all(paper)})
    # Too few fresh questions remain: the mock reuses seen ones, the baseline refuses.
    assert client.post('/api/subject-tests', json={'full_mock': True}).status_code == 201
    assert client.post('/api/subject-tests', json={'assessment': True}).status_code == 409
    assert client.post('/api/subject-tests', json={'full_mock': True, 'assessment': True}).status_code == 422
    assert client.post('/api/subject-tests', json={'full_mock': True, 'subject_code': 'PHY'}).status_code == 422
    with factory() as db:
        assert not db.query(models.Test).filter_by(title='Roadmap baseline assessment').count()


def test_analysis_matches_submission_and_is_owner_only(env):
    client, factory, active = env
    paper = client.post('/api/subject-tests', json={'full_mock': True}).json()
    attempt_id = paper['attempt_id']
    assert client.get(f'/api/test-attempts/{attempt_id}/analysis').status_code == 409
    submitted = client.post(f'/api/subject-tests/attempts/{attempt_id}/submit', json={'answers': answer_all(paper)}).json()

    analysis = client.get(f'/api/test-attempts/{attempt_id}/analysis')
    assert analysis.status_code == 200, analysis.text
    data = analysis.json()
    assert data['detail_available'] and data['meta']['is_mock'] and data['meta']['title'] == 'JEE Main full mock'
    summary = data['summary']
    assert summary['score'] == submitted['score'] and summary['max_score'] == 300
    assert summary['correct'] + summary['wrong'] + summary['skipped'] == 75
    assert summary['accuracy'] == round(submitted['accuracy'], 1)
    assert [q['question_id'] for q in data['questions']] == [q['question_id'] for q in paper['questions']]
    by_id = {q['question_id']: q for q in submitted['questions']}
    for q in data['questions']:
        assert q['outcome'] == by_id[q['question_id']]['outcome']
        assert q['marks_awarded'] == by_id[q['question_id']]['marks_awarded']
        assert q['correct_option_ids'] == by_id[q['question_id']]['correct_option_ids']
        assert q['solution'] == by_id[q['question_id']]['solution']
    picked = next(q for q in data['questions'] if q['type'] == 'single_correct' and q['outcome'] == 'wrong')
    assert picked['selected_option_ids'] and picked['selected_option_ids'] != picked['correct_option_ids']
    assert {s['code'] for s in data['subjects']} == {'PHY', 'CHEM', 'MATH'}
    assert sum(s['total'] for s in data['subjects']) == sum(c['total'] for c in data['chapters']) == 75

    active[0] = 2
    assert client.get(f'/api/test-attempts/{attempt_id}/analysis').status_code == 404
    assert client.get('/api/test-attempts/history').json() == []


def test_history_and_legacy_summary_and_assignments(env):
    client, factory, _ = env
    paper = client.post('/api/subject-tests', json={'full_mock': True}).json()
    client.post(f"/api/subject-tests/attempts/{paper['attempt_id']}/submit", json={'answers': answer_all(paper)})
    unsubmitted = client.post('/api/subject-tests', json={'full_mock': True}).json()

    rows = client.get('/api/test-attempts/history').json()
    assert [r['id'] for r in rows] == [paper['attempt_id'], 500]
    assert rows[0]['detail_available'] and not rows[1]['detail_available']
    assert unsubmitted['attempt_id'] not in [r['id'] for r in rows]
    assert [r['id'] for r in client.get('/api/test-attempts/history', params={'before': paper['attempt_id']}).json()] == [500]

    legacy = client.get('/api/test-attempts/500/analysis').json()
    assert not legacy['detail_available'] and legacy['summary']['score'] == 40 and legacy['questions'] == []

    with factory() as db:
        db.add(models.TeachingAssignment(teacher_id=2, test_id=db.get(models.TestAttempt, paper['attempt_id']).test_id,
                                         title='Class test', opens_at=NOW, due_at=NOW, solutions_at=NOW, duration_sec=60,
                                         marks_correct=4, marks_wrong=1, question_count=75, questions=[], created_at=NOW,
                                         request_key='k'))
        db.commit()
    assert client.get(f"/api/test-attempts/{paper['attempt_id']}/analysis").status_code == 403
    assert [r['id'] for r in client.get('/api/test-attempts/history').json()] == [500]


def test_analysis_compares_with_previous_attempt_of_the_same_paper_and_counts_marks_lost(env):
    client, _, _ = env
    first = client.post('/api/subject-tests', json={'full_mock': True}).json()
    client.post(f"/api/subject-tests/attempts/{first['attempt_id']}/submit", json={'answers': answer_all(first)})
    first_data = client.get(f"/api/test-attempts/{first['attempt_id']}/analysis").json()
    # The only earlier attempt is the legacy 'Full mock', a different paper: nothing to compare with.
    assert first_data['meta']['previous'] is None
    wrong = [q for q in first_data['questions'] if q['marks_awarded'] < 0]
    assert wrong and first_data['summary']['marks_lost'] == -sum(q['marks_awarded'] for q in wrong)

    second = client.post('/api/subject-tests', json={'full_mock': True}).json()
    client.post(f"/api/subject-tests/attempts/{second['attempt_id']}/submit", json={'answers': answer_all(second)})
    previous = client.get(f"/api/test-attempts/{second['attempt_id']}/analysis").json()['meta']['previous']
    assert previous['attempt_id'] == first['attempt_id']
    assert previous['score'] == first_data['summary']['score']


def test_dashboard_totals_include_new_server_scored_practice_and_mocks_only_for_owner(env):
    from app.routers.test_attempts import dashboard_attempts
    client,factory,active=env
    mock=client.post('/api/subject-tests',json={'full_mock':True}).json()
    client.post(f"/api/subject-tests/attempts/{mock['attempt_id']}/submit",json={'answers':answer_all(mock)})
    practice=client.post('/api/subject-tests',json={'subject_code':'PHY','mode':'topic','count':3}).json()
    assert 'attempt_id' in practice,practice
    client.post(f"/api/subject-tests/attempts/{practice['attempt_id']}/submit",json={'answers':answer_all(practice)})
    pending=client.post('/api/subject-tests',json={'full_mock':True}).json()
    with factory() as db:
        rows=dashboard_attempts(1,db)
        assert {r['id'] for r in rows}=={500,mock['attempt_id'],practice['attempt_id']}
        assert pending['attempt_id'] not in {r['id'] for r in rows}
        assert next(r for r in rows if r['id']==practice['attempt_id'])['test_type']=='chapter'
        assert dashboard_attempts(2,db)==[]
