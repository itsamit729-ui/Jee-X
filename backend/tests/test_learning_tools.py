"""Exercise released-result access, revision grading and teacher/class isolation."""
from datetime import timedelta
import pytest
from test_roadmap import setup
from test_teaching import classroom,prepare,publish,start,grant
from app import models as m
from app.auth import utcnow
from app.routers import learning,teaching_tools,teacher_papers

@pytest.fixture
def learning_env(classroom):
    c,f,active=classroom
    for router in (learning.router,teaching_tools.router,teacher_papers.router):c.app.include_router(router)
    room=prepare(classroom)
    return c,f,active,room

def submitted(env, release=True, key='learning-publish-request-01'):
    c,f,active,room=env
    aid=publish((c,f,active),room,request_key=key)
    start(c,aid)
    result=c.post(f'/api/assignments/{aid}/submit',json={'answers':[],'version':0})
    assert result.status_code==200,result.text
    if release:
        with f() as db:
            a=db.get(m.TeachingAssignment,aid);a.solutions_at=utcnow()-timedelta(seconds=1);db.commit()
    return aid

def test_revision_release_grading_spacing_idempotency_and_isolation(learning_env):
    c,f,active,room=learning_env
    aid=submitted(learning_env,False)
    assert c.get('/api/learning/notebook').json()['cards']==[]
    with f() as db:
        a=db.get(m.TeachingAssignment,aid);a.solutions_at=utcnow()-timedelta(seconds=1);db.commit()
    cards=c.get('/api/learning/notebook').json()['cards'];assert len(cards)==2
    assert all('solution' not in r['question'] for r in cards)
    result=c.post('/api/learning/revision',json={'count':8});assert result.status_code==201,result.text
    session=result.json();sid=session['id']
    assert c.post('/api/learning/revision',json={}).json()['id']==sid
    assert all('is_correct' not in o for q in session['questions'] for o in q['options'])
    active[0]=2
    assert c.get(f'/api/learning/revision/{sid}').status_code==404
    active[0]=1
    assert c.post(f'/api/learning/revision/{sid}/submit',json={'answers':[{'question_id':999}]}).status_code==422
    with f() as db: option=db.query(m.QuestionOption).filter_by(question_id=100,is_correct=True).one().id
    result=c.post(f'/api/learning/revision/{sid}/submit',json={'answers':[{'question_id':100,'option_ids':[option]},{'question_id':120,'numeric_answer':2}]})
    assert result.status_code==200,result.text
    assert result.json()['correct']==2
    assert c.post(f'/api/learning/revision/{sid}/submit',json={}).json()==result.json()
    assert c.get('/api/learning/notebook').json()['due_count']==0
    with f() as db:
        card=db.query(m.RevisionCard).first();assert card.stage==1 and card.due_at>utcnow()+timedelta(days=2)
        assert db.query(m.TestAttempt).count()==1
        member=db.get(m.ClassroomMember,(room['id'],1));member.active=False;db.commit()
    assert c.post(f'/api/learning/revision/{sid}/submit',json={}).status_code==409
    assert c.get('/api/learning/notebook').json()['cards']==[]

def test_stale_session_is_replaced_and_misses_are_due_tomorrow(learning_env):
    c,f,active,room=learning_env
    aid=submitted(learning_env)
    s=c.post('/api/learning/revision',json={}).json()
    with f() as db:
        a=db.get(m.TeachingAssignment,aid)
        a.questions=[{**q,'solution':'Corrected explanation'} for q in a.questions];db.commit()
    assert c.post(f"/api/learning/revision/{s['id']}/submit",json={}).status_code==409
    nxt=c.post('/api/learning/revision',json={}).json();assert nxt['id']!=s['id']
    assert c.post(f"/api/learning/revision/{s['id']}/submit",json={}).status_code==409
    assert c.post(f"/api/learning/revision/{nxt['id']}/submit",json={}).status_code==200
    with f() as db:
        card=db.query(m.RevisionCard).first();assert card.stage==0 and card.due_at>utcnow()+timedelta(hours=23)

def test_syllabus_intersection_blueprint_owner_and_student_view(learning_env):
    c,f,active,room=learning_env;cid=room['id'];active[0]=3
    assert c.put(f'/api/teacher/classes/{cid}/syllabus',json={'chapter_ids':[999]}).status_code==422
    assert c.put(f'/api/teacher/classes/{cid}/syllabus',json={'chapter_ids':[1]}).status_code==200
    b={'count':3,'classroom_ids':[cid],'taught_only':True,'exclude_assigned':False}
    generated=c.post('/api/teacher/papers/generate',json=b);assert generated.status_code==200,generated.text
    assert all(q['subject']=='PHY' for q in generated.json()['questions'])
    second=c.post('/api/teacher/classes',json={'name':'Second class'}).json()['id']
    assert c.post('/api/teacher/papers/generate',json={**b,'classroom_ids':[cid,second]}).status_code==422
    saved=c.post('/api/teacher/blueprints',json={'name':'Physics only','configuration':{**b,'locked_ids':[100]}})
    assert saved.status_code==201,saved.text
    bid=saved.json()['id'];assert c.get('/api/teacher/blueprints').json()['blueprints'][0]['configuration']['locked_ids']==[]
    grant(c,4);active[0]=4
    assert c.delete(f'/api/teacher/blueprints/{bid}').status_code==404
    assert c.put(f'/api/teacher/classes/{cid}/syllabus',json={'chapter_ids':[]}).status_code==404
    active[0]=1
    assert c.get('/api/learning/syllabus').json()['classes'][0]['chapters'][0]['id']==1
    active[0]=2;assert c.get('/api/learning/syllabus').json()['classes']==[]

def test_remedial_is_personal_fresh_repeatable_and_class_scoped(learning_env):
    c,f,active,room=learning_env;aid=submitted(learning_env)
    active[0]=2;c.post('/api/classrooms/join',json={'code':room['join_code']})
    active[0]=3
    report=c.get(f"/api/teacher/classes/{room['id']}/insights");assert report.status_code==200,report.text
    assert report.json()['students'][0]['weak_topics']
    body={'student_ids':[1,2],'count':3,'request_key':'personal-request-key-01'}
    endpoint=f"/api/teacher/classes/{room['id']}/remedial"
    r=c.post(endpoint,json=body);assert r.status_code==201,r.text
    data=r.json();assert len(data['published'])==1 and len(data['skipped'])==1
    pid=data['published'][0]['id']
    assert c.post(endpoint,json=body).json()['published'][0]['id']==pid
    with f() as db:
        a=db.get(m.TeachingAssignment,pid)
        assert len(a.questions)==3 and not {100,120}&{q['question_id'] for q in a.questions}
        assert [r.user_id for r in db.query(m.AssignmentRecipient).filter_by(assignment_id=pid)]==[1]
    active[0]=2;assert c.get(f'/api/assignments/{pid}').status_code==404
    active[0]=1;assert c.get(f'/api/assignments/{pid}').status_code==200
    grant(c,4);active[0]=4;assert c.post(endpoint,json=body).status_code==404

def test_doubts_release_ownership_sharing_consent_and_versions(learning_env):
    c,f,active,room=learning_env;aid=submitted(learning_env,False)
    body={'assignment_id':aid,'question_id':100,'message':'Why does this step work?','request_key':'doubt-request-key-01'}
    assert c.post('/api/learning/doubts',json=body).status_code==403
    with f() as db:
        a=db.get(m.TeachingAssignment,aid);a.solutions_at=utcnow()-timedelta(seconds=1);db.commit()
    asked=c.post('/api/learning/doubts',json=body);assert asked.status_code==201,asked.text
    did=asked.json()['id'];assert c.post('/api/learning/doubts',json=body).json()['id']==did
    active[0]=3
    assert c.get('/api/teacher/doubts').json()['doubts'][0]['id']==did
    reply={'answer':'Use conservation of energy here.','version':1,'shared':True}
    assert c.put(f'/api/teacher/doubts/{did}',json=reply).status_code==422
    reply['shared']=False
    assert c.put(f'/api/teacher/doubts/{did}',json=reply).status_code==200
    assert c.put(f'/api/teacher/doubts/{did}',json=reply).status_code==409
    grant(c,4);active[0]=4;assert c.put(f'/api/teacher/doubts/{did}',json=reply).status_code==404
    active[0]=2;assert c.get('/api/learning/doubts').json()['doubts']==[]
    active[0]=1;assert c.get('/api/learning/doubts').json()['doubts'][0]['answer']==reply['answer']

def test_shared_doubts_require_recipient_submission_and_active_membership(learning_env):
    c,f,active,room=learning_env
    active[0]=2;c.post('/api/classrooms/join',json={'code':room['join_code']})
    aid=submitted(learning_env)
    body={'assignment_id':aid,'question_id':100,'message':'Please explain the first step.','allow_share':True,'request_key':'shared-doubt-request-01'}
    did=c.post('/api/learning/doubts',json=body).json()['id']
    active[0]=3
    assert c.put(f'/api/teacher/doubts/{did}',json={'answer':'Start with Newton’s second law.','shared':True,'version':1}).status_code==200
    active[0]=2
    assert c.get('/api/learning/doubts').json()['doubts']==[]
    start(c,aid)
    assert c.post(f'/api/assignments/{aid}/submit',json={'answers':[],'version':0}).status_code==200
    shared=c.get('/api/learning/doubts').json()['doubts'];assert len(shared)==1
    assert shared[0]['mine'] is False and 'student' not in shared[0]
    assert 'solution' not in shared[0]['question']
    with f() as db:
        db.get(m.ClassroomMember,(room['id'],2)).active=False;db.commit()
    assert c.get('/api/learning/doubts').json()['doubts']==[]


def test_recent_normal_practice_mistakes_and_correct_response_retirement(learning_env):
    c,f,active,room=learning_env
    active[0]=1
    with f() as db:
        test=m.Test(title='Practice',kind='chapter',pattern='jee_main',duration_sec=60,ranked=False);db.add(test);db.flush();tid=test.id
        attempt=m.TestAttempt(test_id=test.id,user_id=1,attempt_number=1,counts_for_rank=False,submitted_at=utcnow());db.add(attempt);db.flush()
        db.add(m.QuestionResponse(user_id=1,attempt_id=attempt.id,question_id=100,question_version=1,outcome='wrong',marks_awarded=0,time_taken_sec=10));db.commit()
    cards=c.get('/api/learning/notebook');assert cards.status_code==200,cards.text
    assert len(cards.json()['cards'])==1 and cards.json()['cards'][0]['assignment_id'] is None
    with f() as db:
        attempt=m.TestAttempt(test_id=tid,user_id=1,attempt_number=2,counts_for_rank=False,submitted_at=utcnow());db.add(attempt);db.flush()
        db.add(m.QuestionResponse(user_id=1,attempt_id=attempt.id,question_id=100,question_version=1,outcome='correct',marks_awarded=4,time_taken_sec=10));db.commit()
    assert c.get('/api/learning/notebook').json()['cards']==[]

    # Regrading an older attempt creates newer response IDs, not newer evidence.
    with f() as db:
        old=db.query(m.TestAttempt).filter_by(test_id=tid,user_id=1,attempt_number=1).one()
        db.query(m.QuestionResponse).filter_by(attempt_id=old.id).delete();db.flush()
        db.add(m.QuestionResponse(user_id=1,attempt_id=old.id,question_id=100,question_version=1,outcome='wrong',marks_awarded=0,time_taken_sec=10));db.commit()
    assert c.get('/api/learning/notebook').json()['cards']==[]
