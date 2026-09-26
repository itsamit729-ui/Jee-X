import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import datetime, timedelta, date
from types import SimpleNamespace as Row
from app.services.practice import choose_questions

NOW = datetime(2026, 9, 27)
def q(id=100, topic=1, difficulty=3):
    return Row(id=id, subtopic_id=topic, topic='Molecular shape', difficulty=difficulty, expected_time_sec=90)
def h(id, outcome='wrong', topic=1, days=0, seconds=0, difficulty=5):
    return Row(question_id=id, outcome=outcome, subtopic_id=topic, answered_at=NOW-timedelta(days=days), time_taken_sec=seconds, expected_time_sec=90, difficulty=difficulty)

def test_reasons_follow_distinct_evidence_and_difficulty():
    picked = choose_questions([q(100,difficulty=4),q(101,difficulty=8)], [h(1),h(2),h(3,'correct')], 1, now=NOW)
    assert picked[0][0] == 100
    assert picked[0][1]['evidence'] == {'distinct_questions':3,'incorrect':2}
    assert picked[0][1]['reason_code'] == 'revisit_weak_concept'
    assert '2 of your 3' in picked[0][1]['reason']
    # Repeated answers to one question do not manufacture evidence of weakness.
    assert choose_questions([q()], [h(1),h(1),h(1)],1,now=NOW)[0][1]['reason_code'] == 'build_evidence'

def test_cold_start_revision_speed_and_stretch():
    assert choose_questions([q()],[],1,now=NOW)[0][1]['reason_code'] == 'diagnostic'
    assert choose_questions([q()],[h(1,'correct',days=12)],1,now=NOW)[0][1]['evidence']['days_since_practice'] == 12
    assert choose_questions([q()],[h(i,'correct',seconds=150) for i in range(3)],1,now=NOW)[0][1]['reason_code'] == 'build_fluency'
    assert choose_questions([q()],[h(i,'correct',seconds=0) for i in range(3)],1,now=NOW)[0][1]['reason_code'] != 'build_fluency'
    selected = choose_questions([q(100,difficulty=6),q(101,difficulty=2)],[h(i,'correct') for i in range(4)],1,now=NOW)
    assert selected[0][0] == 100 and 'harder' in selected[0][1]['learning_goal']

def test_repeat_fallback_is_explicit_and_no_duplicates():
    rows = choose_questions([q(1),q(2)], [h(1)], 5, now=NOW)
    assert [r[0] for r in rows] == [2,1]
    assert rows[1][1]['repeated'] and 'seen this question' in rows[1][1]['reason']


def test_practice_api_scopes_evidence_snapshots_and_filters_incomplete_content():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app import models
    from app.database import Base,get_db
    from app.deps import get_current_db_user
    from app.routers.subject_tests import router
    from app.routers.subject_test_attempts import router as grader
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine)
    with factory() as db:
        for uid in [1,2]:
            db.add(models.User(id=uid,auth0_sub=str(uid),username=f'u{uid}',name='Student'))
            db.add(models.StudentProfile(user_id=uid,dob=date(2006,1,1),class_12_year=2027,target_year=2027,target_exam='jee_main'))
        db.add(models.Subject(id=1,code='CHEM',name='Chemistry'))
        db.add(models.Subject(id=2,code='PHY',name='Physics'))
        db.add(models.Chapter(id=1,subject_id=1,name='Bonding',slug='bonding',class_level='11'))
        db.add(models.Subtopic(id=1,chapter_id=1,name='Molecular shape',slug='shape'))
        db.flush()
        for i in range(1,8):
            question=models.Question(id=i,ref=f'Q{i}',subtopic_id=1,type='single_correct',stem='Pick a shape',solution='Explanation',difficulty=3,expected_time_sec=90,source_type='original',status='published' if i!=7 else 'draft',version=1,content_hash=str(i))
            db.add(question)
            db.flush()
            db.add(models.QuestionRevision(question_id=i,version=1,content={}))
            for j in range(2):
                db.add(models.QuestionOption(question_id=i,label='AB'[j],content='Option',is_correct=j==0,position=j+1))
        db.add(models.Asset(question_id=6,url=None,alt_text='Missing diagram'))
        old=models.Test(title='Previous',kind='chapter',pattern='jee_main',duration_sec=300)
        db.add(old);db.flush()
        attempt=models.TestAttempt(user_id=2,test_id=old.id,submitted_at=NOW)
        db.add(attempt);db.flush()
        for i in range(1,4):
            db.add(models.QuestionResponse(attempt_id=attempt.id,user_id=2,question_id=i,question_version=1,outcome='wrong',time_taken_sec=0,answered_at=NOW))
        db.commit()
    def database():
        with factory() as db: yield db
    active=[1]
    app=FastAPI();app.include_router(router);app.include_router(grader)
    app.dependency_overrides[get_db]=database
    app.dependency_overrides[get_current_db_user]=lambda: models.User(id=active[0])
    with TestClient(app) as client:
        assert client.post('/api/subject-tests',json={'mode':'topic'}).status_code == 422
        assert client.post('/api/subject-tests',json={'mode':'topic','subject_code':'PHY','chapter_id':1}).status_code == 422
        response=client.post('/api/subject-tests',json={'mode':'recommended','duration_minutes':5})
        assert response.status_code==201,response.text
        session=response.json();questions=session['questions']
        assert len(questions)==3
        assert all(x['question_id'] not in (6,7) for x in questions)
        assert all(x['recommendation']['reason_code']=='diagnostic' for x in questions)
        assert all('solution' not in x and 'answer_min' not in x for x in questions)
        assert all('is_correct' not in o for x in questions for o in x['options'])
        with factory() as db:
            snapshots=db.query(models.PracticeRecommendation).filter_by(test_id=session['test_id']).all()
            assert len(snapshots)==3
            before={s.question_id:s.explanation for s in snapshots}
        active[0]=2
        other=client.post('/api/subject-tests',json={'mode':'recommended','duration_minutes':5}).json()
        assert any(x['recommendation']['reason_code']=='revisit_weak_concept' for x in other['questions'])
        assert client.post(f"/api/subject-tests/attempts/{session['attempt_id']}/submit",json={'answers':[]}).status_code==404
        active[0]=1
        result=client.post(f"/api/subject-tests/attempts/{session['attempt_id']}/submit",json={'answers':[{'question_id':x['question_id'],'option_ids':[x['options'][0]['id']],'time_taken_sec':42} for x in questions]})
        assert result.status_code==201 or result.status_code==200,result.text
        with factory() as db:
            assert all(r.time_taken_sec==42 for r in db.query(models.QuestionResponse).filter_by(user_id=1))
            assert {s.question_id:s.explanation for s in db.query(models.PracticeRecommendation).filter_by(test_id=session['test_id'])}==before
    engine.dispose()
