import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base, get_db
from app.deps import get_current_db_user
from app.routers.pyqs import router
from app.routers.subject_test_attempts import router as grader


@pytest.fixture
def archive():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine)
    with factory() as db:
        for uid in [1,2]:
            db.add(models.User(id=uid,auth0_sub=str(uid),username=f'student{uid}',name='Student'))
            db.add(models.StudentProfile(user_id=uid,dob=date(2006,1,1),class_12_year=2027,target_year=2027))
        for sid,code in enumerate(['PHY','CHEM','MATH'],1):
            db.add(models.Subject(id=sid,code=code,name=code))
            db.add(models.Chapter(id=sid,subject_id=sid,name=code,slug=code,class_level='12'))
            db.add(models.Subtopic(id=sid,chapter_id=sid,name=code,slug=code))
        db.flush()
        for i in range(1,49):
            numeric=i%4==0
            q=models.Question(id=i,ref=f'MAIN-{i:03}',subtopic_id=1 if i<=36 or i>=43 else 2 if i<=40 else 3,
                type='numerical' if numeric else 'single_correct',stem=f'Fixture {i}',solution='',
                answer_min=5 if numeric else None,answer_max=5 if numeric else None,
                difficulty=5,expected_time_sec=120,source_type='original' if i==47 else 'pyq',
                exam='bitsat' if i==46 else 'jee_main',year=2024 if i==44 else 2026,
                shift=None if i==43 else '21 Jan 2026, Shift 1',status='draft' if i==45 else 'published',
                version=1,content_hash=f'hash{i}')
            db.add(q);db.flush();db.add(models.QuestionRevision(question_id=i,version=1,content={}))
            if not numeric:
                for j in range(4):
                    db.add(models.QuestionOption(question_id=i,label='ABCD'[j],content=f'Option {j}',is_correct=j==0,position=j))
            if i==48:q.answer_min=None;q.answer_max=None;q.type='single_correct'  # no valid key
        db.commit()
    def database():
        with factory() as db:yield db
    active=[1]
    app=FastAPI();app.include_router(router);app.include_router(grader)
    app.dependency_overrides[get_db]=database
    app.dependency_overrides[get_current_db_user]=lambda:models.User(id=active[0])
    with TestClient(app) as client:yield client,active
    engine.dispose()


def test_catalog_includes_mcq_numerical_missing_solutions_and_all_years(archive):
    c,_=archive
    response=c.get('/api/pyqs/jee_main');assert response.status_code==200
    data=response.json();assert data['label']=='JEE Main'
    y=next(y for y in data['years'] if y['year']==2026)
    assert sum(s['available'] for s in y['subjects'])==43
    assert y['papers'][0]['available']==42  # question without a shift remains in subject practice
    assert next(y for y in data['years'] if y['year']==2024)['subjects'][0]['available']==1
    assert c.post('/api/pyqs/jee_main/practice',json={'year':2026,'subject_code':'ENG'}).status_code==422


def test_subject_sets_reach_every_question_without_repeating_the_first_thirty(archive):
    c,_=archive
    def start(offset):
        r=c.post('/api/pyqs/jee_main/practice',json={'year':2026,'subject_code':'PHY','count':30,'offset':offset})
        assert r.status_code==201,r.text
        return {q['question_id'] for q in r.json()['questions']}
    first,second=start(0),start(30)
    assert len(first)==30 and len(second)==7 and not first&second
    assert first|second==set(range(1,37))|{43}
    assert c.post('/api/pyqs/jee_main/practice',json={'year':2026,'subject_code':'PHY','offset':60}).status_code==404
    assert c.post('/api/pyqs/jee_main/practice',json={'year':2026,'subject_code':'PHY','offset':-1}).status_code==422


def test_full_shift_scoring_and_numeric_keys_are_only_returned_after_owned_submission(archive):
    c,active=archive
    r=c.post('/api/pyqs/jee_main/papers',json={'year':2026,'shift':'21 Jan 2026, Shift 1'})
    assert r.status_code==201,r.text
    paper=r.json();assert paper['is_mock'] and paper['duration_sec']==10800 and paper['subject_code']=='PCM'
    assert len(paper['questions'])==42
    assert all(q['marks_correct']==4 and q['marks_wrong']==1 for q in paper['questions'])
    assert all('answer_min' not in q and 'answer_max' not in q and 'solution' not in q for q in paper['questions'])
    assert all('is_correct' not in o for q in paper['questions'] for o in q['options'])
    answers=[{'question_id':q['question_id'],'numeric_answer':5} if q['type']=='numerical' else
             {'question_id':q['question_id'],'option_ids':[q['options'][0]['id']]} for q in paper['questions']]
    answers[0]['option_ids']=[paper['questions'][0]['options'][1]['id']]
    url=f"/api/subject-tests/attempts/{paper['attempt_id']}/submit"
    active[0]=2;assert c.post(url,json={'answers':answers}).status_code==404
    active[0]=1;r=c.post(url,json={'answers':answers});assert r.status_code==200,r.text
    result=r.json();assert result['score']==41*4-1
    numeric=next(q for q in result['questions'] if q['question_id']==4)
    assert numeric['answer_min']==5 and numeric['answer_max']==5
    assert c.post(url,json={'answers':answers}).status_code==409


def test_shift_keeps_each_subject_mcqs_before_numericals(archive):
    c,_=archive
    paper=c.post('/api/pyqs/jee_main/papers',json={'year':2026,'shift':'21 Jan 2026, Shift 1'}).json()
    order={'PHY':0,'CHEM':1,'MATH':2}
    keys=[(order[q['subject_code']],int(q['type']=='numerical')) for q in paper['questions']]
    assert keys==sorted(keys)
    assert len({q['question_id'] for q in paper['questions']})==42
