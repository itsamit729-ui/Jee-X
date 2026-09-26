"""Isolated SQLite integration tests; production continues to require MySQL."""
import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import datetime, timedelta, date
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base, get_db
from app.deps import get_current_db_user
from app.models.ranking import JeeXRating, RatedContest, ContestEntry
from app.routers.ranking import router
from app.services.ranking import calculate_updates, grade, tier, summary, finalize

QUESTIONS = [dict(id=1, stem='Two plus two?', type='single_correct', passage=None, assets=[],
                  options=[dict(id=11,label='A',content='4'),dict(id=12,label='B',content='5')], correct_option_ids=[11], answer_min=None, answer_max=None, solution='4'),
             dict(id=2, stem='A numerical answer', type='numerical', passage=None, assets=[], options=[], correct_option_ids=[], answer_min=2.4, answer_max=2.6, solution='2.5')]

@pytest.fixture
def setup():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    tables=[models.User.__table__,models.StudentProfile.__table__,JeeXRating.__table__,RatedContest.__table__,ContestEntry.__table__]
    Base.metadata.create_all(engine,tables=tables)
    db=sessionmaker(bind=engine,expire_on_commit=False)()
    for uid in (1,2,3):
        db.add(models.User(id=uid,auth0_sub=f'u{uid}',username=f'student{uid}',name='Student',role='student',status='active'))
        db.flush()
        db.add(models.StudentProfile(user_id=uid,dob=date(2008,1,1),class_12_year=2027,target_year=2027,target_exam='jee_main',leaderboard_visibility='username'))
    db.commit()
    app=FastAPI();app.include_router(router)
    active=[1]
    def current():return db.get(models.User,active[0])
    def session():yield db
    app.dependency_overrides[get_db]=session
    app.dependency_overrides[get_current_db_user]=current
    client=TestClient(app)
    yield db,client,active
    db.close();engine.dispose()


def contest(db, **kw):
    values=dict(title='Weekly contest',exam='jee_main',target_year=2027,opens_at=datetime.utcnow()-timedelta(minutes=1),closes_at=datetime.utcnow()+timedelta(hours=1),duration_sec=600,questions=QUESTIONS)
    values.update(kw); c=RatedContest(**values);db.add(c);db.commit();return c


def test_tier_boundaries():
    assert tier(1)['title']=='Aspirant'
    assert tier(499)['title']=='Aspirant'
    assert tier(500)['title']=='Explorer'
    assert tier(4499)['title']=='Ranker'
    assert tier(4500)['title']==tier(5000)['title']=='Legend'


def test_rating_expectations_ties_bounds_and_singleton():
    assert calculate_updates([(1,10,1500,0),(2,0,1500,0)])=={1:1700,2:1300}
    assert calculate_updates([(1,10,1500,3),(2,10,1500,3)])=={1:1500,2:1500}
    assert calculate_updates([(1,10,1500,0)])=={1:1500}
    upset=calculate_updates([(1,10,1000,3),(2,0,2000,3)])
    assert upset[1]-1000>80
    assert all(1<=v<=5000 for v in calculate_updates([(1,10,5000,0),(2,0,1,0)]).values())


def test_grading():
    assert grade(QUESTIONS,{'1':{'option_ids':[11]},'2':{'numeric_answer':2.5}})==8
    assert grade(QUESTIONS,{'1':{'option_ids':[12]}})==-1
    assert grade(QUESTIONS,{})==0


def test_start_resume_secrecy_and_ownership(setup):
    db,c,active=setup;event=contest(db)
    first=c.post(f'/api/ranking/contests/{event.id}/start').json()
    again=c.post(f'/api/ranking/contests/{event.id}/start').json()
    assert first['id']==again['id'] and first['deadline']==again['deadline']
    assert 'correct_option_ids' not in first['questions'][0] and 'solution' not in first['questions'][0]
    assert 'answer_min' not in first['questions'][1]
    active[0]=2
    assert c.put(f"/api/ranking/entries/{first['id']}",json={'answers':[]}).status_code==404


def test_validation_submission_and_deadline(setup):
    db,c,active=setup;event=contest(db)
    eid=c.post(f'/api/ranking/contests/{event.id}/start').json()['id']
    url=f'/api/ranking/entries/{eid}'
    assert c.put(url,json={'answers':[{'question_id':1,'option_ids':[999]}]}).status_code==422
    assert c.put(url,json={'answers':[{'question_id':1},{'question_id':1}]}).status_code==422
    assert c.put(url,json={'answers':[{'question_id':1,'numeric_answer':4}]}).status_code==422
    assert c.put(url,json={'answers':[{'question_id':1,'option_ids':[11]}],'score':5000,'submit':True}).status_code==200
    assert c.put(url,json={'answers':[]}).status_code==409
    assert c.get('/api/ranking/contests').json()[0]['score'] is None
    active[0]=2
    eid2=c.post(f'/api/ranking/contests/{event.id}/start').json()['id']
    db.get(ContestEntry,eid2).deadline=datetime.utcnow()-timedelta(seconds=1);db.commit()
    assert c.put(f'/api/ranking/entries/{eid2}',json={'answers':[]}).status_code==409


def test_three_placements_peak_and_idempotent_settlement(setup):
    db,c,active=setup
    for _ in range(3):
        event=contest(db)
        for uid in (1,2):
            active[0]=uid
            eid=c.post(f'/api/ranking/contests/{event.id}/start').json()['id']
            answers=[{'question_id':1,'option_ids':[11]}] if uid==1 else []
            assert c.put(f'/api/ranking/entries/{eid}',json={'answers':answers,'submit':True}).status_code==200
        event.closes_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
        assert c.post('/api/ranking/settle').status_code==200
        account=db.get(JeeXRating,(1,'jee_main',2027));old=account.rating;count=account.contests
        c.post('/api/ranking/settle');db.refresh(account)
        assert account.rating==old and account.contests==count
    active[0]=1
    result=c.get('/api/ranking/me').json()
    assert result['placements_completed']==3 and result['rating']>1500 and result['badges']
    assert len(result['history'])==3
    account=db.get(JeeXRating,(1,'jee_main',2027));peak=account.peak
    account.rating=500;db.commit()
    assert summary(account)['peak']==peak and summary(account)['title']=='Explorer'
    assert len(summary(account)['badges'])>2


def test_privacy_inactivity_cohort_and_ties(setup):
    db,c,active=setup
    for uid in (1,2,3):
        db.add(JeeXRating(user_id=uid,exam='jee_main',target_year=2027,rating=1800,peak=1800,contests=3,last_rated_at=datetime.utcnow()))
    db.commit()
    board=c.get('/api/ranking/leaderboard').json()
    assert [r['rank'] for r in board['entries']]==[1,1,1]
    assert 'email' not in board['entries'][0]
    c.patch('/api/ranking/visibility',json={'visibility':'hidden'})
    assert c.get('/api/ranking/leaderboard').json()['my_rank'] is None
    db.get(JeeXRating,(2,'jee_main',2027)).last_rated_at=datetime.utcnow()-timedelta(days=31)
    db.get(models.StudentProfile,3).target_year=2028;db.commit()
    assert c.get('/api/ranking/leaderboard').json()['entries']==[]
    assert db.get(JeeXRating,(2,'jee_main',2027)).rating==1800


def test_single_entrant_and_abandoned_saved_answers(setup):
    db,c,active=setup;event=contest(db)
    eid=c.post(f'/api/ranking/contests/{event.id}/start').json()['id']
    c.put(f'/api/ranking/entries/{eid}',json={'answers':[{'question_id':1,'option_ids':[11]}]})
    event.closes_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
    c.post('/api/ranking/settle')
    entry=db.get(ContestEntry,eid)
    assert entry.score==4 and entry.submitted_at and entry.rating_after is None
    assert db.get(JeeXRating,(1,'jee_main',2027)).contests==0


def test_admin_only_and_exam_access(setup):
    db,c,active=setup
    payload=dict(title='Admin contest',exam='jee_main',target_year=2027,opens_at='2030-01-01T10:00:00Z',closes_at='2030-01-01T11:00:00Z',duration_sec=600,question_ids=[1])
    assert c.post('/api/ranking/contests',json=payload).status_code==403
    event=contest(db,exam='jee_advanced')
    assert c.post(f'/api/ranking/contests/{event.id}/start').status_code==409
    assert c.get('/api/ranking/contests').json()==[]


def test_admin_publication_snapshot_and_overlap(setup):
    db,c,active=setup
    Base.metadata.create_all(db.get_bind())
    user=db.get(models.User,1);user.role='admin'
    db.add(models.Subject(id=1,code='PHY',name='Physics'));db.flush()
    db.add(models.Chapter(id=1,subject_id=1,name='Motion',slug='motion',class_level='11'));db.flush()
    db.add(models.Subtopic(id=1,chapter_id=1,name='Velocity',slug='velocity'));db.flush()
    q=models.Question(id=1,ref='test-1',subtopic_id=1,type='single_correct',stem='Original question',solution='Solution',difficulty=3,expected_time_sec=60,source_type='original',status='published',content_hash='a'*64)
    db.add(q);db.flush()
    db.add(models.QuestionOption(question_id=1,label='A',content='Correct',is_correct=True,position=1));db.commit()
    payload=dict(title='Admin contest',exam='jee_main',target_year=2027,opens_at='2030-01-01T10:00:00Z',closes_at='2030-01-01T11:00:00Z',duration_sec=600,question_ids=[1])
    response=c.post('/api/ranking/contests',json=payload)
    assert response.status_code==201, response.text
    event=db.get(RatedContest,response.json()['id'])
    assert event.questions[0]['stem']=='Original question'
    q.stem='Edited question';db.commit()
    assert event.questions[0]['stem']=='Original question'
    assert c.post('/api/ranking/contests',json=payload).status_code==409
    assert c.post('/api/ranking/contests',json={**payload,'question_ids':[1,1]}).status_code==422
    assert c.post('/api/ranking/contests',json={**payload,'opens_at':'2030-01-01T10:00:00'}).status_code==422


def test_finalization_does_not_run_before_close(setup):
    db,c,active=setup;event=contest(db)
    c.post(f'/api/ranking/contests/{event.id}/start')
    assert c.post('/api/ranking/settle').status_code==200
    db.refresh(event)
    assert not event.finalized
    assert db.get(JeeXRating,(1,'jee_main',2027)).contests==0


def test_contest_list_has_constant_query_count(setup):
    from sqlalchemy import event
    from app.routers.ranking import _build_contests
    db, _, _ = setup
    for number in range(30):
        contest(db, title=f'Contest {number}')
    queries = []
    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            queries.append(statement)
    event.listen(db.bind, 'before_cursor_execute', record)
    try:
        results = _build_contests(db, 1, 'jee_main', 2027)
        assert len(results) == 30
        assert len(queries) == 2, queries
    finally:
        event.remove(db.bind, 'before_cursor_execute', record)


def test_settlement_does_not_revisit_finalized_contests(setup, monkeypatch):
    from app.routers import ranking
    db, _, _ = setup
    contest(db, finalized=True, closes_at=datetime.utcnow()-timedelta(minutes=1))
    pending = contest(db, closes_at=datetime.utcnow()-timedelta(minutes=1))
    contest(db)  # Still open.
    visited = []
    monkeypatch.setattr(ranking, 'finalize', lambda session, row: visited.append(row.id))
    ranking.settle(db, db.get(models.User, 1))
    assert visited == [pending.id]
