"""Student mistake notebook and spaced retrieval practice without answer leakage."""
from datetime import timedelta
from types import SimpleNamespace
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import func
from app import models as m,schemas
from app.database import get_db
from app.deps import get_current_db_user
from app.auth import utcnow
from app.routers import teaching as t
from app.services.grading import _grade_one

router=APIRouter(prefix='/api/learning',tags=['learning'])

def available_card(db,card,uid):
    if card.user_id!=uid: return False
    if card.assignment_id:
        try:
            a,r=t.student_assignment(db,card.assignment_id,uid)
            return bool(r.result and utcnow()>=a.solutions_at and any(q==card.question for q in a.questions))
        except HTTPException: return False
    q=t.question_query(db).filter(m.Question.id==card.question_id).first()
    try: return bool(q and t.freeze(q,q.version)==card.question)
    except HTTPException: return False

def sync_cards(db,uid):
    latest=db.query(m.QuestionResponse.id.label('rid'),func.row_number().over(partition_by=m.QuestionResponse.question_id,order_by=(m.TestAttempt.submitted_at.desc(),m.QuestionResponse.id.desc())).label('position')).join(m.TestAttempt,m.TestAttempt.id==m.QuestionResponse.attempt_id).filter(m.QuestionResponse.user_id==uid,m.TestAttempt.user_id==uid,m.TestAttempt.submitted_at.isnot(None)).subquery()
    rows=db.query(m.QuestionResponse,m.TestAttempt).join(latest,(m.QuestionResponse.id==latest.c.rid)&(latest.c.position==1)).join(m.TestAttempt,m.TestAttempt.id==m.QuestionResponse.attempt_id).order_by(m.TestAttempt.submitted_at.desc(),m.QuestionResponse.id.desc()).limit(500).all()
    existing={c.question_id:c for c in db.query(m.RevisionCard).filter_by(user_id=uid)}
    assignments={a.test_id:a for a in db.query(m.TeachingAssignment).filter(m.TeachingAssignment.test_id.in_([attempt.test_id for _,attempt in rows]))}
    bank_ids=[r.question_id for r,a in rows if a.test_id not in assignments and r.outcome!='correct']
    bank={q.id:q for q in t.question_query(db).filter(m.Question.id.in_(bank_ids))}
    released={}
    for response,attempt in rows:
        old=existing.get(response.question_id)
        if response.outcome=='correct':
            if old: db.delete(old)
            continue
        a=assignments.get(attempt.test_id)
        if a:
            if a.id not in released:
                try:
                    _,r=t.student_assignment(db,a.id,uid)
                    released[a.id]=bool(r.result and utcnow()>=a.solutions_at)
                except HTTPException: released[a.id]=False
            if not released[a.id]: continue
            q=next((q for q in a.questions if q['question_id']==response.question_id),None)
        else:
            row=bank.get(response.question_id)
            try: q=t.freeze(row,row.version) if row else None
            except HTTPException: continue
        if not q: continue
        if old and old.source_response_id==response.id and old.question==q: continue
        if old is None:
            old=m.RevisionCard(user_id=uid,question_id=response.question_id);db.add(old)
        old.source_response_id=response.id;old.assignment_id=a.id if a else None;old.question=q
        old.stage=0;old.due_at=utcnow();old.last_result=response.outcome
    db.flush()

def filter_available(db,cards,uid):
    # Bulk-load bank content; class eligibility is checked once per assignment.
    bank={q.id:q for q in t.question_query(db).filter(m.Question.id.in_([c.question_id for c in cards if not c.assignment_id]))}
    classes={};result=[]
    for c in cards:
        if c.user_id!=uid: continue
        if c.assignment_id:
            if c.assignment_id not in classes:
                try:
                    a,r=t.student_assignment(db,c.assignment_id,uid)
                    classes[c.assignment_id]=a.questions if r.result and utcnow()>=a.solutions_at else []
                except HTTPException: classes[c.assignment_id]=[]
            allowed=c.question in classes[c.assignment_id]
        else:
            q=bank.get(c.question_id)
            try: allowed=bool(q and t.freeze(q,q.version)==c.question)
            except HTTPException: allowed=False
        if allowed:result.append(c)
    return result

def card_out(c):
    return {'id':c.id,'question':t.safe_question(c.question),'stage':c.stage,'due_at':t.stamp(c.due_at),'last_result':c.last_result,'assignment_id':c.assignment_id}

@router.get('/notebook')
def notebook(user=Depends(get_current_db_user),db=Depends(get_db)):
    t.lock_user(db,user.id);sync_cards(db,user.id)
    cards=filter_available(db,list(db.query(m.RevisionCard).filter_by(user_id=user.id).order_by(m.RevisionCard.due_at).limit(500)),user.id)
    result={'cards':[card_out(c) for c in cards],'due_count':sum(c.due_at<=utcnow() for c in cards),'scope':'Mistakes from your latest responses to up to 500 recent questions. Class questions appear after solutions are released.'}
    db.commit();return result

class SessionIn(BaseModel):
    count:int=Field(8,ge=1,le=20)

@router.post('/revision',status_code=201)
def start(body:SessionIn,user=Depends(get_current_db_user),db=Depends(get_db)):
    t.lock_user(db,user.id);sync_cards(db,user.id)
    existing=db.query(m.RevisionSession).filter_by(user_id=user.id).filter(m.RevisionSession.result.is_(None),m.RevisionSession.created_at>utcnow()-timedelta(days=1)).order_by(m.RevisionSession.id.desc()).first()
    if existing and all(valid_item(db,c,user.id) for c in existing.cards):
        db.commit();return session_out(existing)
    cards=filter_available(db,list(db.query(m.RevisionCard).filter_by(user_id=user.id).filter(m.RevisionCard.due_at<=utcnow()).order_by(m.RevisionCard.due_at).limit(500)),user.id)[:body.count]
    if not cards: raise HTTPException(409,'No revision questions are due. Complete practice or return on the next revision date.')
    row=m.RevisionSession(user_id=user.id,cards=[{'card_id':c.id,'source_response_id':c.source_response_id,'question':c.question} for c in cards],created_at=utcnow())
    db.add(row);db.commit();return session_out(row)

def valid_item(db,item,uid):
    card=db.get(m.RevisionCard,item['card_id'])
    return bool(card and card.source_response_id==item['source_response_id'] and card.question==item['question'] and available_card(db,card,uid))

def session_out(row):
    return {'id':row.id,'questions':[t.safe_question(c['question']) for c in row.cards],'result':row.result}

@router.get('/revision/{sid}')
def read(sid:int,user=Depends(get_current_db_user),db=Depends(get_db)):
    row=db.query(m.RevisionSession).filter_by(id=sid,user_id=user.id).first()
    if not row: raise HTTPException(404,'Revision session not found.')
    for item in row.cards:
        card=db.get(m.RevisionCard,item['card_id'])
        if not valid_item(db,item,user.id): raise HTTPException(409,'A question is no longer available. Start a new revision session.')
    return session_out(row)

class SubmitIn(BaseModel):
    answers:list[schemas.SubjectTestAnswerIn]=Field(default_factory=list,max_length=20)

@router.post('/revision/{sid}/submit')
def submit(sid:int,body:SubmitIn,user=Depends(get_current_db_user),db=Depends(get_db)):
    t.lock_user(db,user.id)
    row=db.query(m.RevisionSession).filter_by(id=sid,user_id=user.id).with_for_update().first()
    if not row: raise HTTPException(404,'Revision session not found.')
    if not all(valid_item(db,c,user.id) for c in row.cards): raise HTTPException(409,'Source evidence changed. Start a new revision session.')
    if row.result:return row.result
    ids={c['question']['question_id'] for c in row.cards};answers={a.question_id:a for a in body.answers}
    if len(answers)!=len(body.answers) or not set(answers)<=ids: raise HTTPException(422,'Answers must belong to this revision session.')
    results=[]
    for item in row.cards:
        card=db.get(m.RevisionCard,item['card_id']);q=item['question']
        if not valid_item(db,item,user.id): raise HTTPException(409,'Source evidence changed. Reload your notebook before retrying.')
        ans=answers.get(q['question_id'],schemas.SubjectTestAnswerIn(question_id=q['question_id']))
        options={o['id'] for o in q['options']}
        if not set(ans.option_ids)<=options or (q['type']=='single_correct' and len(ans.option_ids)>1) or (q['type']=='numerical' and ans.option_ids) or (q['type']!='numerical' and ans.numeric_answer is not None): raise HTTPException(422,'An answer does not match its question.')
        outcome,correct_ids=_grade_one(SimpleNamespace(**{**q,'options':[SimpleNamespace(**o) for o in q['options']]}),ans)
        card.stage=min(card.stage+1,4) if outcome=='correct' else 0
        days=(1,3,7,14,30)[card.stage]
        card.due_at=utcnow()+timedelta(days=days);card.last_result=outcome
        results.append({'question_id':q['question_id'],'outcome':outcome,'correct_option_ids':sorted(correct_ids),'answer_min':q['answer_min'],'answer_max':q['answer_max'],'solution':q['solution'],'next_due':t.stamp(card.due_at)})
    row.result={'correct':sum(q['outcome']=='correct' for q in results),'total':len(results),'questions':results,'submitted_at':t.stamp(utcnow())}
    db.commit();return row.result
