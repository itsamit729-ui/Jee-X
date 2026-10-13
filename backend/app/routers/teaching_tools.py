"""Class-scoped syllabus, reusable generation settings and learning follow-up."""
from collections import defaultdict
from datetime import timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from app import models as m
from app.database import get_db
from app.deps import get_current_db_user
from app.auth import utcnow
from app.routers import teaching as t
from app.routers.teacher_papers import Generate

router=APIRouter(prefix='/api',tags=['teaching-tools'])

def chapters(db):
    return [{'id':c.id,'name':c.name,'subject':s.code} for c,s in db.query(m.Chapter,m.Subject).join(m.Subject).order_by(m.Subject.code,m.Chapter.position,m.Chapter.id)]

@router.get('/teacher/classes/{cid}/syllabus')
def syllabus(cid:int,user=Depends(t.require_teacher),db=Depends(get_db)):
    t.owned_class(db,cid,user)
    return {'chapters':chapters(db),'taught_ids':[r.chapter_id for r in db.query(m.TaughtChapter).filter_by(classroom_id=cid)]}

class SyllabusIn(BaseModel):
    chapter_ids:list[int]=Field(default_factory=list,max_length=300)

@router.put('/teacher/classes/{cid}/syllabus')
def save_syllabus(cid:int,b:SyllabusIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    t.owned_class(db,cid,user)
    ids=set(b.chapter_ids)
    if db.query(m.Chapter).filter(m.Chapter.id.in_(ids)).count()!=len(ids): raise HTTPException(422,'Unknown chapter.')
    db.query(m.TaughtChapter).filter_by(classroom_id=cid).delete(synchronize_session=False)
    for id in ids: db.add(m.TaughtChapter(classroom_id=cid,chapter_id=id,updated_at=utcnow()))
    db.commit();return {'taught_ids':sorted(ids)}

@router.get('/learning/syllabus')
def student_syllabus(user=Depends(get_current_db_user),db=Depends(get_db)):
    rooms=db.query(m.Classroom).join(m.ClassroomMember).filter(m.ClassroomMember.user_id==user.id,m.ClassroomMember.active.is_(True)).all()
    catalog={c['id']:c for c in chapters(db)}
    return {'classes':[{'id':r.id,'name':r.name,'chapters':[catalog[x.chapter_id] for x in db.query(m.TaughtChapter).filter_by(classroom_id=r.id) if x.chapter_id in catalog]} for r in rooms]}

class BlueprintIn(BaseModel):
    name:str=Field(min_length=3,max_length=150)
    configuration:Generate

@router.get('/teacher/blueprints')
def blueprints(user=Depends(t.require_teacher),db=Depends(get_db)):
    return {'blueprints':[{'id':r.id,'name':r.name,'configuration':r.configuration} for r in db.query(m.TeacherBlueprint).filter_by(teacher_id=user.id).order_by(m.TeacherBlueprint.id.desc())]}

@router.post('/teacher/blueprints',status_code=201)
def save_blueprint(b:BlueprintIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    if not b.name.strip(): raise HTTPException(422,'Enter a blueprint name.')
    for cid in b.configuration.classroom_ids: t.owned_class(db,cid,user)
    if db.query(m.TeacherBlueprint).filter_by(teacher_id=user.id).count()>=100: raise HTTPException(409,'Remove an old blueprint first (maximum 100).')
    config=b.configuration.model_dump();config['locked_ids']=[];config['exclude_ids']=[]
    row=m.TeacherBlueprint(teacher_id=user.id,name=b.name.strip(),configuration=config,created_at=utcnow());db.add(row);db.commit()
    return {'id':row.id}

@router.delete('/teacher/blueprints/{bid}')
def remove_blueprint(bid:int,user=Depends(t.require_teacher),db=Depends(get_db)):
    row=db.query(m.TeacherBlueprint).filter_by(id=bid,teacher_id=user.id).first()
    if not row: raise HTTPException(404,'Blueprint not found.')
    db.delete(row);db.commit();return {'deleted':True}

def class_evidence(db,cid,user):
    t.owned_class(db,cid,user)
    students=db.query(m.User).join(m.ClassroomMember).filter(m.ClassroomMember.classroom_id==cid,m.ClassroomMember.active.is_(True),m.User.status=='active').all()
    ids=[u.id for u in students]
    rows=db.query(m.AssignmentRecipient,m.TeachingAssignment).join(m.TeachingAssignment).join(m.AssignmentClassroom).filter(m.AssignmentClassroom.classroom_id==cid,m.TeachingAssignment.teacher_id==user.id,m.AssignmentRecipient.user_id.in_(ids)).order_by(m.TeachingAssignment.id).all()
    evidence={u.id:{'id':u.id,'name':u.name,'tests':[],'topics':defaultdict(lambda:{'correct':0,'total':0,'name':''}),'seen':set()} for u in students}
    for r,a in rows:
        if not r.result: continue
        item=evidence[r.user_id];result=r.result
        maximum=result.get('max_score') or a.question_count*a.marks_correct
        item['tests'].append({'title':a.title,'percent':round(100*result.get('score',0)/maximum,1)})
        outcomes={q['question_id']:q['outcome'] for q in result.get('questions',[])}
        for q in a.questions:
            item['seen'].add(q['question_id'])
            if q['question_id'] not in outcomes: continue
            topic=item['topics'][q['subtopic_id']];topic['name']=q['topic'];topic['total']+=1;topic['correct']+=int(outcomes[q['question_id']]=='correct')
    return evidence

@router.get('/teacher/classes/{cid}/insights')
def insights(cid:int,user=Depends(t.require_teacher),db=Depends(get_db)):
    evidence=class_evidence(db,cid,user)
    result=[]
    for item in evidence.values():
        tests=item['tests'];weak=[{'id':id,'name':v['name'],'accuracy':round(100*v['correct']/v['total']),'responses':v['total']} for id,v in item['topics'].items() if v['correct']/v['total']<0.7]
        result.append({'id':item['id'],'name':item['name'],'tests':len(tests),'latest_percent':tests[-1]['percent'] if tests else None,'change':round(tests[-1]['percent']-tests[-2]['percent'],1) if len(tests)>1 else None,'weak_topics':sorted(weak,key=lambda v:v['accuracy'])})
    return {'students':result,'scope':'Assigned class results, including linked reviewed OMR results. Changes compare the last two assigned tests; different papers may have different difficulty.'}

class RemedialIn(BaseModel):
    count:int=Field(8,ge=1,le=20)
    student_ids:list[int]=Field(min_length=1,max_length=50)
    request_key:str=Field(min_length=16,max_length=40)

@router.post('/teacher/classes/{cid}/remedial',status_code=201)
def remedial(cid:int,b:RemedialIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    evidence=class_evidence(db,cid,user)
    if not set(b.student_ids)<=set(evidence): raise HTTPException(422,'Select active students from this class.')
    published=[];skipped=[]
    for uid in sorted(set(b.student_ids)):
        item=evidence[uid];key=f'{b.request_key}:{cid}:{uid}'
        existing=db.query(m.TeachingAssignment).filter_by(teacher_id=user.id,request_key=key).first()
        if existing: published.append({'id':existing.id,'student_id':uid});continue
        weak=[id for id,v in item['topics'].items() if v['correct']/v['total']<0.7]
        if not weak: skipped.append({'student_id':uid,'reason':'No weak-topic evidence yet.'});continue
        candidates=t.question_query(db,user.id).filter(m.Question.subtopic_id.in_(weak),~m.Question.id.in_(item['seen'])).order_by(m.Question.id).limit(300).all()
        selected=[]
        # Round-robin topics prevents the first chapter from filling every test.
        buckets={id:[] for id in weak}
        for q in candidates:
            try: t.freeze(q,q.version)
            except HTTPException: continue
            buckets[q.subtopic_id].append(q.id)
        while len(selected)<b.count and any(buckets.values()):
            for bucket in buckets.values():
                if bucket and len(selected)<b.count: selected.append(bucket.pop(0))
        if len(selected)<b.count: skipped.append({'student_id':uid,'reason':f'Only {len(selected)} fresh eligible questions; {b.count} requested.'});continue
        now=utcnow();due=now+timedelta(days=7)
        body=t.PublishIn(title='Personal revision · '+str(cid),instructions='Practise the topics identified in your class results.',classroom_ids=[cid],question_ids=selected,opens_at=now.replace(tzinfo=timezone.utc),due_at=due.replace(tzinfo=timezone.utc),solutions_at=due.replace(tzinfo=timezone.utc),duration_minutes=max(10,b.count*2),marks_correct=1,marks_wrong=0,request_key=key)
        result=t.publish_assignment(body,user,db,commit=False,recipient_ids=[uid]);published.append({'id':result['id'],'student_id':uid})
    db.commit();return {'published':published,'skipped':skipped}


def released(db,aid,uid,qid):
    a,r=t.student_assignment(db,aid,uid)
    if not r.result or utcnow()<a.solutions_at: raise HTTPException(403,'Ask after submitting and after solutions are released.')
    q=next((q for q in a.questions if q['question_id']==qid),None)
    if not q: raise HTTPException(404,'Question not found.')
    return a,q

def doubt_out(db,row,teacher=False):
    a=db.get(m.TeachingAssignment,row.assignment_id)
    q=next((q for q in a.questions if q['question_id']==row.question_id),None)
    return {'id':row.id,'assignment_id':a.id,'title':a.title,'question':t.safe_question(q),'message':row.message,'answer':row.answer,'allow_share':row.allow_share,'shared':row.shared,'version':row.version,'created_at':t.stamp(row.created_at),**({'student':db.get(m.User,row.student_id).name} if teacher else {})}

class DoubtIn(BaseModel):
    assignment_id:int
    question_id:int
    message:str=Field(min_length=5,max_length=2000)
    allow_share:bool=False
    request_key:str=Field(min_length=8,max_length=64)

@router.post('/learning/doubts',status_code=201)
def ask(b:DoubtIn,user=Depends(get_current_db_user),db=Depends(get_db)):
    t.lock_user(db,user.id)
    a,q=released(db,b.assignment_id,user.id,b.question_id)
    old=db.query(m.QuestionDoubt).filter_by(student_id=user.id,request_key=b.request_key).first()
    if old:return doubt_out(db,old)
    if len(b.message.strip())<5: raise HTTPException(422,'Describe your doubt in at least five characters.')
    if db.query(m.QuestionDoubt).filter(m.QuestionDoubt.student_id==user.id,m.QuestionDoubt.created_at>utcnow()-timedelta(days=1)).count()>=20: raise HTTPException(429,'You can ask up to 20 questions per day.')
    row=m.QuestionDoubt(student_id=user.id,teacher_id=a.teacher_id,assignment_id=a.id,question_id=b.question_id,message=b.message.strip(),allow_share=b.allow_share,request_key=b.request_key,created_at=utcnow());db.add(row);db.flush()
    t.notify(db,a.teacher_id,'New question doubt','A student needs help with a released class question.','/teacher?tab=doubts','doubt',None)
    db.commit();return doubt_out(db,row)

@router.get('/learning/doubts')
def my_doubts(user=Depends(get_current_db_user),db=Depends(get_db)):
    rows=db.query(m.QuestionDoubt).filter(or_(m.QuestionDoubt.student_id==user.id,m.QuestionDoubt.shared.is_(True))).filter(m.QuestionDoubt.assignment_id.in_(t.member_assignment_ids(db,user.id))).order_by(m.QuestionDoubt.id.desc()).limit(100).all()
    visible=[]
    for row in rows:
        try: released(db,row.assignment_id,user.id,row.question_id)
        except HTTPException:continue
        visible.append({**doubt_out(db,row),'mine':row.student_id==user.id})
    return {'doubts':visible}

@router.get('/teacher/doubts')
def teacher_doubts(user=Depends(t.require_teacher),db=Depends(get_db)):
    rows=db.query(m.QuestionDoubt).filter_by(teacher_id=user.id).order_by(m.QuestionDoubt.answer.isnot(None),m.QuestionDoubt.id.desc()).limit(100).all()
    return {'doubts':[doubt_out(db,r,True) for r in rows]}

class ReplyIn(BaseModel):
    answer:str=Field(min_length=5,max_length=5000)
    shared:bool=False
    version:int

@router.put('/teacher/doubts/{did}')
def reply(did:int,b:ReplyIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    row=db.query(m.QuestionDoubt).filter_by(id=did,teacher_id=user.id).with_for_update().first()
    if not row: raise HTTPException(404,'Doubt not found.')
    if row.version!=b.version: raise HTTPException(409,'This reply changed. Reload before editing.')
    if b.shared and not row.allow_share: raise HTTPException(422,'The student did not consent to sharing.')
    if len(b.answer.strip())<5: raise HTTPException(422,'Write a complete reply.')
    row.answer=b.answer.strip();row.shared=b.shared;row.version+=1;row.answered_at=utcnow()
    t.notify(db,row.student_id,'Your teacher replied','Open your question doubt to read the explanation.','/learning?tab=doubts','doubt_reply',None)
    db.commit();return doubt_out(db,row,True)
