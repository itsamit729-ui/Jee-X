"""Two real participants, frozen questions, server time and private results."""
import os
from datetime import datetime, date, timedelta
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base, get_db
from app.deps import get_current_db_user
from app.routers.duels import router
from app.services import duels


@pytest.fixture
def arena(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        for uid, username in [(1,'alice'), (2,'bobby'), (3,'carol')]:
            db.add(models.User(id=uid, username=username, name=username, auth0_sub=f'duel-{uid}', role='student', status='active'))
            db.flush()
            db.add(models.StudentProfile(user_id=uid, dob=date(2008,1,1), class_12_year=2026, target_year=2026, target_exam='jee_main'))
        for sid, code in enumerate(['PHY','CHEM','MATH'], 1):
            db.add(models.Subject(id=sid, code=code, name=code))
            db.flush()
            db.add(models.Chapter(id=sid, subject_id=sid, name=code, slug=code, class_level='12'))
            db.flush()
            db.add(models.Subtopic(id=sid, chapter_id=sid, name=code, slug=code))
        db.flush()
        qid=0
        for exam in ['jee_main','mht_cet','bitsat']:
            for sid in range(1,4):
                for i in range(6):
                    qid+=1
                    numeric=i==5 and exam=='jee_main'
                    q=models.Question(id=qid, ref=f'DUEL-{qid}', subtopic_id=sid, type='numerical' if numeric else 'single_correct',
                        stem=f'Private question {qid}', solution=f'PRIVATE_SOLUTION_{qid}', difficulty=i+1,
                        expected_time_sec=60, source_type='pyq', exam=exam, year=2025, status='published',
                        version=1, content_hash=f'duel-hash-{qid}', answer_min=2 if numeric else None, answer_max=2 if numeric else None)
                    db.add(q)
                    db.flush()
                    if not numeric:
                        for j, label in enumerate('ABCD'):
                            db.add(models.QuestionOption(question_id=qid, label=label, content=label, is_correct=j==0, position=j+1))
        db.commit()
    identity=[1]
    now=[datetime(2026,10,18,12)]
    monkeypatch.setattr(duels,'utcnow',lambda:now[0])
    def database():
        with factory() as db:
            yield db
    def user():
        with factory() as db:
            row=db.get(models.User,identity[0])
            _=row.student_profile,row.teacher_access
            return row
    app=FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db]=database
    app.dependency_overrides[get_current_db_user]=user
    return TestClient(app), identity, now, factory


def create(arena, **extra):
    client, identity, _, _=arena
    identity[0]=1
    response=client.post('/api/duels',json={'username':'bobby','count':5,**extra})
    assert response.status_code==201,response.text
    return response.json()


def begin(arena, **extra):
    client, identity, now, _=arena
    match=create(arena,**extra)
    path=f'/api/duels/{match["id"]}'
    identity[0]=2
    assert client.post(path+'/accept').json()['state']=='lobby'
    assert client.post(path+'/ready').json()['state']=='lobby'
    identity[0]=1
    countdown=client.post(path+'/ready').json()
    assert countdown['state']=='active' and countdown['questions']==[]
    now[0]+=timedelta(seconds=5)
    return path,client.get(path).json()


def test_full_match_private_until_both_finish_and_idempotent(arena):
    client, identity, _, factory=arena
    path, match=begin(arena)
    assert len(match['questions'])==5
    assert 'PRIVATE_SOLUTION' not in str(match)
    assert 'correct_option_ids' not in str(match) and 'answer_min' not in str(match)
    identity[0]=2
    opponent=client.get(path).json()
    assert opponent['questions']==match['questions'] and opponent['deadline_at']==match['deadline_at']
    assert opponent['answers']=={}
    identity[0]=1
    for q in match['questions']:
        response=client.put(path+'/answers/'+q['question_id'],json={'numeric_answer':2} if q['type']=='numerical' else {'option_ids':['A']})
        assert response.status_code==200,response.text
    assert len(client.get(path).json()['answers'])==5
    submitted=client.post(path+'/submit').json()
    assert submitted['state']=='active' and all(p['result'] is None for p in submitted['players'])
    assert client.post(path+'/surrender').status_code==409, 'A submitted player cannot stop their opponent early'
    identity[0]=2
    hidden=client.get(path).json()
    assert hidden['answers']=={} and hidden['players'][0]['answered']==5
    assert all(p['result'] is None for p in hidden['players'])
    completed=client.post(path+'/submit').json()
    assert completed['state']=='completed' and completed['winner_id']==1
    winner=next(p for p in completed['players'] if p['user_id']==1)
    assert winner['result']['score']==20
    assert 'PRIVATE_SOLUTION' in str(completed)
    assert client.post(path+'/submit').json()['players']==completed['players']
    q=match['questions'][0]
    assert client.put(path+'/answers/'+q['question_id'],json={}).status_code==409
    with factory() as db:
        assert db.query(models.TestAttempt).count()==0
        assert db.query(models.DuelMatch).count()==1


def test_access_control_and_invalid_invites(arena):
    client, identity, _, _=arena
    assert client.post('/api/duels',json={'username':'alice'}).status_code==422
    assert client.post('/api/duels',json={'username':'missing'}).status_code==404
    assert client.post('/api/duels',json={'username':'bobby','count':6}).status_code==422
    match=create(arena)
    path=f'/api/duels/{match["id"]}'
    assert client.post(path+'/accept').status_code==409
    assert client.post('/api/duels',json={'username':'bobby'}).status_code==409
    identity[0]=3
    assert client.get('/api/duels').json()==[]
    for method, endpoint, body in [('get',path,None),('post',path+'/accept',None),('put',path+'/answers/bank:1',{})]:
        response=getattr(client,method)(endpoint,**({'json':body} if body is not None else {}))
        assert response.status_code==404
    identity[0]=2
    assert client.get('/api/duels/invitations/count').json()=={'count':1}
    assert client.post(path+'/decline').json()['state']=='declined'
    assert client.get('/api/duels/invitations/count').json()=={'count':0}


def test_deadline_recovers_after_disconnect_and_rejects_late_answers(arena):
    client, identity, now, factory=arena
    path, match=begin(arena)
    q=match['questions'][0]
    assert client.put(path+'/answers/'+q['question_id'],json={}).status_code==200
    now[0]+=timedelta(seconds=match['duration_sec'])
    assert client.put(path+'/answers/'+q['question_id'],json={}).status_code==409
    finished=client.get(path).json()
    assert finished['state']=='completed' and finished['winner_id'] is None
    assert all(p['submitted'] and p['result']['score']==0 for p in finished['players'])
    with factory() as db:
        assert db.get(models.DuelMatch,match['id']).state=='completed'


def test_countdown_invalid_answers_and_frozen_paper(arena):
    client, identity, now, factory=arena
    match=create(arena,subject='PHY')
    assert match['questions']==[]
    with factory() as db:
        row=db.get(models.DuelMatch,match['id'])
        qid=row.questions[0]['id']
        old_stem=row.questions[0]['stem']
        question=db.get(models.Question,int(qid.split(':')[1]))
        question.stem='EDITED BANK TEXT'
        db.commit()
    path=f'/api/duels/{match["id"]}'
    assert client.put(path+'/answers/'+qid,json={}).status_code==409
    identity[0]=2
    client.post(path+'/accept');client.post(path+'/ready')
    identity[0]=1
    client.post(path+'/ready')
    assert client.put(path+'/answers/'+qid,json={}).status_code==409
    now[0]+=timedelta(seconds=5)
    paper=client.get(path).json()
    assert paper['questions'][0]['stem']==old_stem
    assert all(q['subject_code']=='PHY' for q in paper['questions'])
    assert client.put(path+'/answers/bank:99999',json={}).status_code==404
    mcq=next(q for q in paper['questions'] if q['type']=='single_correct')
    endpoint=path+'/answers/'+mcq['question_id']
    assert client.put(endpoint,json={'option_ids':['Z']}).status_code==422
    assert client.put(endpoint,json={'option_ids':['A','B']}).status_code==422
    assert client.put(endpoint,json={'numeric_answer':2}).status_code==422
    assert client.put(endpoint,json={'score':999}).status_code==422
    assert client.put(endpoint,json={'option_ids':['B']}).status_code==200
    assert client.put(endpoint,json={}).status_code==200
    assert client.get(path+'?paper=false').json().get('questions') is None


@pytest.mark.parametrize('exam',['jee_main','mht_cet','bitsat'])
def test_correct_exam_marking_and_surrender(arena,exam):
    client, identity, _, _=arena
    path, match=begin(arena,exam=exam)
    for q in match['questions']:
        assert q['marks_correct']==(2 if q['subject_code']=='MATH' else 1) if exam=='mht_cet' else q['marks_correct']==(3 if exam=='bitsat' else 4)
    ended=client.post(path+'/surrender').json()
    assert ended['state']=='completed' and ended['winner_id']==2
    assert next(p for p in ended['players'] if p['user_id']==1)['forfeited']
    assert client.post(path+'/submit').json()['winner_id']==2


def test_expired_invitation_and_ready_lobby(arena):
    client, identity, now, _=arena
    match=create(arena)
    now[0]+=timedelta(minutes=31)
    assert client.get(f'/api/duels/{match["id"]}').json()['state']=='expired'
    second=create(arena)
    path=f'/api/duels/{second["id"]}'
    identity[0]=2
    client.post(path+'/accept')
    now[0]+=timedelta(minutes=11)
    assert client.post(path+'/ready').json()['state']=='expired'


def test_only_active_students_and_available_questions(arena):
    client, identity, _, factory=arena
    with factory() as db:
        db.get(models.User,1).status='suspended'
        db.commit()
    assert client.get('/api/duels').status_code==403
    with factory() as db:
        db.get(models.User,1).status='active'
        db.query(models.Question).filter_by(exam='bitsat').update({'status':'draft'})
        db.commit()
    assert client.post('/api/duels',json={'username':'bobby','exam':'bitsat'}).status_code==422


def test_cannot_ready_for_overlapping_matches(arena):
    client, identity, now, _=arena
    first=create(arena)
    second=create(arena,username='carol')
    p1=f'/api/duels/{first["id"]}';p2=f'/api/duels/{second["id"]}'
    identity[0]=2
    client.post(p1+'/accept');client.post(p1+'/ready')
    identity[0]=1
    client.post(p1+'/ready')
    identity[0]=3
    client.post(p2+'/accept')
    assert client.post(p2+'/ready').status_code==409


def test_numeric_validation_and_wrong_answer_scoring():
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.routers.duels import Answer
    q={'id':'bank:99','ref':'NUM','subject':'PHY','type':'numerical','stem':'2?',
       'options':[],'correct_option_ids':[],'answer_min':1.95,'answer_max':2.05,'solution':'Two'}
    match=SimpleNamespace(questions=[q],exam='jee_main')
    for number,expected in [(2,4),(3,-1),(None,0)]:
        player=SimpleNamespace(answers={'bank:99':duels.answer(q,Answer(numeric_answer=number))})
        assert duels.score(match,player)['score']==expected
    with pytest.raises(HTTPException):
        duels.answer(q,Answer(option_ids=['A']))
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Answer(numeric_answer=float('inf'))


def test_reverse_invitation_is_duplicate_and_ready_leave_can_cancel(arena):
    client, identity, _, _=arena
    match=create(arena)
    identity[0]=2
    assert client.post('/api/duels',json={'username':'alice'}).status_code==409
    path=f'/api/duels/{match["id"]}'
    client.post(path+'/accept')
    assert client.post(path+'/leave').json()['state']=='cancelled'
    identity[0]=1
    assert client.get('/api/duels').json()[0]['state']=='cancelled'


def test_daily_invitation_limit_counts_expired_invites(arena):
    client, identity, now, factory=arena
    for i in range(20):
        create(arena)
        now[0]+=timedelta(minutes=31)
    response=client.post('/api/duels',json={'username':'bobby'})
    assert response.status_code==429 and '20 invitations' in response.text
    now[0]+=timedelta(days=1)
    create(arena)


def test_endpoint_requires_authentication(arena):
    client, _, _, _=arena
    previous=client.app.dependency_overrides.pop(get_current_db_user)
    try:
        assert client.get('/api/duels').status_code==401
        assert client.get('/api/duels/invitations/count').status_code==401
    finally:
        client.app.dependency_overrides[get_current_db_user]=previous
