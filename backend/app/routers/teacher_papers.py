"""Teacher-owned editable papers, blueprint selection, exports and offline review."""
import base64
import csv
import hashlib
import io
import math
import random
import secrets
import re
from collections import Counter
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import or_, func, case
from app import models as m
from app.database import get_db, SessionLocal
from app.auth import utcnow
from app.routers import teaching as t
from app.services import mixed_omr, paper_answers
from app.services.teacher_question_content import presentation

router = APIRouter(prefix='/api/teacher', tags=['teacher papers'])
EXAMS = Literal['jee_main', 'jee_advanced', 'mht_cet', 'bitsat']

def owned(db, pid, user):
    p = db.query(m.TeacherPaper).filter_by(id=pid, teacher_id=user.id).with_for_update().first()
    if not p:
        raise HTTPException(404, 'Paper not found.')
    return p

def bank(db, uid):
    return t.question_query(db, uid)

def roster(db, uid, classroom_ids=None):
    query = db.query(m.ClassroomMember.user_id).join(m.Classroom).filter(m.Classroom.teacher_id == uid, m.ClassroomMember.active.is_(True))
    if classroom_ids:
        for cid in classroom_ids:
            t.owned_class(db, cid, type('Owner', (), {'id': uid})())
        query = query.filter(m.Classroom.id.in_(classroom_ids))
    return {x[0] for x in query.all()}

def payload(p):
    return dict(id=p.id, title=p.title, settings=p.settings, questions=p.questions, version=p.version,
                finalized=p.finalized, assignment_id=p.assignment_id, sets_enabled=sets_enabled(p), variants=['A','B'] if sets_enabled(p) else ['A'], variant_b=order_for(p,'B') if sets_enabled(p) else None, omr=omr_report(p.questions), updated_at=t.stamp(p.updated_at))

class Section(BaseModel):
    subject: Literal['PHY','CHEM','MATH','ENG','LR']
    count: int = Field(ge=1, le=200)
    chapter_ids: list[int] = Field(default_factory=list, max_length=100)
    difficulty_min: int = Field(1, ge=1, le=10)
    difficulty_max: int = Field(10, ge=1, le=10)
    type: Literal['single_correct','multi_correct','numerical'] | None = 'single_correct'

class Generate(BaseModel):
    exam: EXAMS = 'jee_main'
    mode: Literal['quick','blueprint','similar','exact','remedial'] = 'quick'
    count: int = Field(30, ge=1, le=200)
    level: Literal['easy','balanced','hard'] = 'balanced'
    year: int | None = Field(None, ge=2000, le=2100)
    shift: str | None = Field(None, max_length=50)
    classroom_ids: list[int] = Field(default_factory=list, max_length=20)
    chapter_ids: list[int] = Field(default_factory=list, max_length=100)
    sections: list[Section] = Field(default_factory=list, max_length=20)
    locked_ids: list[int] = Field(default_factory=list, max_length=200)
    exclude_ids: list[int] = Field(default_factory=list, max_length=400)
    reference_without_shift: bool = False
    omr_only: bool = False
    taught_only: bool = False
    exclude_assigned: bool = True
    source: Literal['all','pyq','original'] = 'all'
    restrict_to_reference: bool = False
    strict_exam: bool = False
    published_only: bool = False

@router.post('/papers/generate')
def generate(b: Generate, user=Depends(t.require_teacher), db=Depends(get_db)):
    if b.restrict_to_reference and (not b.year or b.mode in ('exact', 'similar')):
        raise HTTPException(422, 'Choose a year for questions from a paper; use reference matching separately.')
    if b.omr_only and b.mode in ('exact','similar'): raise HTTPException(422, 'Past-paper matching preserves the original question formats. Use Quick mock or Custom blueprint to build an OMR-only paper.')
    student_ids=roster(db, user.id, b.classroom_ids)
    query = bank(db, user.id).join(m.Subtopic).join(m.Chapter).join(m.Subject)
    query = query.filter(or_(m.Question.exam == b.exam, m.Question.exam.is_(None)))
    if b.strict_exam: query = query.filter(m.Question.exam == b.exam)
    if b.published_only: query = query.filter(m.Question.status == 'published')
    if b.restrict_to_reference:
        query = query.filter(m.Question.exam == b.exam, m.Question.source_type == 'pyq', m.Question.year == b.year)
        if b.shift is not None or b.reference_without_shift:
            query = query.filter(m.Question.shift == b.shift)
    if b.omr_only:
        options=db.query(m.QuestionOption.question_id).group_by(m.QuestionOption.question_id).having(func.count(m.QuestionOption.id)==4,func.count(func.distinct(m.QuestionOption.label))==4,func.sum(case((m.QuestionOption.label.in_(['A','B','C','D']),1),else_=0))==4,func.sum(case((m.QuestionOption.is_correct.is_(True),1),else_=0))==1)
        query=query.filter(m.Question.type=='single_correct',m.Question.id.in_(options))
    if b.source != 'all': query = query.filter(m.Question.source_type == b.source)
    if b.chapter_ids: query = query.filter(m.Chapter.id.in_(b.chapter_ids))
    if b.taught_only:
        if not b.classroom_ids: raise HTTPException(422, 'Select classes to use their taught syllabus.')
        sets=[{x.chapter_id for x in db.query(m.TaughtChapter).filter_by(classroom_id=cid)} for cid in set(b.classroom_ids)]
        taught=set.intersection(*sets)
        if not taught: raise HTTPException(422, 'No chapters are marked taught in every selected class.')
        query=query.filter(m.Chapter.id.in_(taught))
    # Metadata-only selection is bounded. Content/diagrams load only for selected IDs.
    meta = query.with_entities(m.Question.id, m.Question.difficulty, m.Question.type, m.Question.year,
        m.Question.shift, m.Question.source_type, m.Question.exam, m.Question.subtopic_id,
        m.Chapter.id.label('chapter_id'), m.Subject.code.label('subject')).order_by(m.Question.id).limit(30000).all()
    rows = [dict(r._mapping) for r in meta]
    if len(rows) == 30000: raise HTTPException(422, 'Narrow the syllabus; this selection exceeds 30,000 candidates.')
    locked = list(dict.fromkeys(b.locked_ids))
    lookup = {r['id']: r for r in rows}
    if any(q not in lookup for q in locked): raise HTTPException(422, 'A locked question is outside these filters or unavailable.')
    excluded = set(b.exclude_ids)
    if b.exclude_assigned and b.classroom_ids:
        assigned = db.query(m.TeachingAssignment.questions).join(m.AssignmentClassroom).filter(
            m.TeachingAssignment.teacher_id == user.id, m.AssignmentClassroom.classroom_id.in_(b.classroom_ids)).all()
        excluded.update(q['question_id'] for (questions,) in assigned for q in questions)
    if set(locked) & excluded: raise HTTPException(422, 'A locked question conflicts with the exclusions. Unlock it or change the filters.')
    reference = []
    if b.mode in ('exact','similar'):
        if not b.year or (b.shift is None and not b.reference_without_shift): raise HTTPException(422, 'Choose a year and the exact paper label from the bank.')
        reference = [r for r in rows if r['exam'] == b.exam and r['year'] == b.year and r['shift'] == b.shift and r['source_type'] == 'pyq']
        if not reference: raise HTTPException(422, 'This paper is not available in the bank.')
    rng = random.SystemRandom()
    rng.shuffle(rows)
    selected = locked[:]
    requirements = []
    warning = 'Difficulty is based on reviewed tags, not a calibrated exam score.'
    if b.mode == 'exact':
        if locked or excluded.intersection(r['id'] for r in reference):
            raise HTTPException(422, 'Exact-paper mode cannot honour locks or excluded questions. Disable exclusions or choose Similar.')
        # Original ordering is not inferable from IDs. Preserve source reference order.
        selected = [r['id'] for r in reference]
        warning = 'Available bank questions for this paper; completeness and original question order are not certified.'
    else:
        pool = [r for r in rows if r['id'] not in excluded and r['id'] not in selected]
        if b.mode == 'similar':
            excluded_ref = {r['id'] for r in reference}
            pool = [r for r in pool if r['id'] not in excluded_ref]
            if set(locked) & excluded_ref: raise HTTPException(422, 'Similar papers must not lock original reference questions.')
            weights = Counter((r['subject'], r['chapter_id'], r['type'], r['difficulty']) for r in reference)
            for key, n in weights.items(): requirements.extend([key] * n)
            rng.shuffle(requirements)
            requirements = [requirements[i * len(requirements)//b.count] for i in range(b.count)]
        elif b.mode == 'blueprint':
            if not b.sections: raise HTTPException(422, 'Add at least one blueprint section.')
            if sum(s.count for s in b.sections) > 200: raise HTTPException(422, 'Maximum 200 questions.')
            for s in b.sections:
                if s.difficulty_min > s.difficulty_max: raise HTTPException(422, 'Invalid difficulty range.')
                requirements.extend([s] * s.count)
        elif b.mode == 'quick':
            subjects=sorted({r['subject'] for r in rows if r['subject'] in ({'PHY','CHEM','MATH','ENG','LR'} if b.exam=='bitsat' else {'PHY','CHEM','MATH'})})
            if not subjects: raise HTTPException(422,'No questions match this exam and syllabus.')
            requirements=[('subject',subjects[i % len(subjects)]) for i in range(b.count)]
        else:
            requirements = [None] * b.count
        # Locks consume matching requirements, rather than silently increasing the paper size.
        def matches(r, req):
            if isinstance(req, Section): return r['subject'] == req.subject and (not req.chapter_ids or r['chapter_id'] in req.chapter_ids) and (req.type is None or r['type'] == req.type) and req.difficulty_min <= r['difficulty'] <= req.difficulty_max
            if isinstance(req, tuple) and len(req)==2: return r['subject']==req[1]
            if isinstance(req, tuple): return (r['subject'], r['chapter_id'], r['type'], r['difficulty']) == req
            return True
        for qid in locked:
            index = next((i for i, req in enumerate(requirements) if matches(lookup[qid], req)), None)
            if index is None: raise HTTPException(422, 'Locked questions do not fit this blueprint/count.')
            requirements.pop(index)
        weak = Counter()
        if b.mode == 'remedial':
            if not b.classroom_ids: raise HTTPException(422, 'Select a class for remedial practice.')
            for (qs, result) in db.query(m.TeachingAssignment.questions, m.AssignmentRecipient.result).join(m.AssignmentRecipient).join(m.AssignmentClassroom).filter(m.TeachingAssignment.teacher_id == user.id, m.AssignmentClassroom.classroom_id.in_(b.classroom_ids), m.AssignmentRecipient.result.isnot(None)).all():
                topics = {q['question_id']: q['subtopic_id'] for q in qs}
                for ans in result.get('questions', []):
                    if ans['outcome'] != 'correct': weak[topics[ans['question_id']]] += 1
            for qs,result in db.query(m.TeacherPaper.questions,m.TeacherScan.result).join(m.TeacherScan,m.TeacherScan.paper_id==m.TeacherPaper.id).join(m.TeacherSheet,m.TeacherSheet.id==m.TeacherScan.sheet_id).filter(m.TeacherPaper.teacher_id==user.id,m.TeacherPaper.assignment_id.is_(None),m.TeacherScan.state=='reviewed',m.TeacherSheet.student_id.in_(student_ids)).all():
                topics={q['question_id']:q['subtopic_id'] for q in qs}
                for ans in result.get('questions',[]):
                    if ans['outcome']!='correct': weak[topics[ans['question_id']]]+=1
            if not weak: raise HTTPException(422, 'No submitted class evidence yet. Use Quick mock first.')
        target = {'easy':3,'balanced':5,'hard':8}[b.level]
        pool.sort(key=lambda r: (-weak[r['subtopic_id']], abs(r['difficulty']-target)))
        shortfalls = []
        for req in requirements:
            index = next((i for i,r in enumerate(pool) if matches(r,req)), None)
            if index is None: shortfalls.append(str(req) if req else 'requested level/syllabus')
            else: selected.append(pool.pop(index)['id'])
        if shortfalls: raise HTTPException(422, f'Bank shortfall: {len(shortfalls)} questions unavailable. Broaden chapters, difficulty or exclusions; no partial paper was saved.')
    if not selected or len(selected)>200: raise HTTPException(422, 'Paper must contain 1–200 questions.')
    qs={q.id:q for q in bank(db,user.id).filter(m.Question.id.in_(selected)).all()}
    if b.mode == 'exact': selected.sort(key=lambda i: qs[i].ref)
    return {'questions':[t.freeze(qs[i],qs[i].version) for i in selected], 'warning':warning}

class AIRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=6000)
    defaults: dict = Field(default_factory=dict)
    exam: EXAMS = 'jee_main'


@router.post('/papers/ai-draft')
def ai_draft(b: AIRequest, user=Depends(t.require_teacher), db=Depends(get_db)):
    from app.services import teacher_ai
    from app.services.authentication import throttle
    import os
    if not os.getenv('GROQ_API_KEY', '').strip() or os.getenv('TEACHER_AI_ENABLED', 'true').lower() != 'true':
        raise HTTPException(503, 'AI paper creation is unavailable. Use Generate questions or Choose from bank.')
    if len(b.prompt.strip()) < 10:
        raise HTTPException(422, 'Describe the paper in at least 10 characters.')
    throttle(db, 'teacher_ai:minute', str(user.id), 3, 60)
    throttle(db, 'teacher_ai:day', str(user.id), 30, 86400)
    throttle(db, 'teacher_ai:global', 'all', 100, 86400)
    # Only metadata from the visible, published bank is shared, never question content or student data.
    query = bank(db, user.id).filter(m.Question.status == 'published', m.Question.exam == b.exam)
    years = {int(y) for y in re.findall(r'\b20\d{2}\b', b.prompt)}
    refs = query.filter(m.Question.source_type == 'pyq', m.Question.year.isnot(None))
    if years: refs = refs.filter(m.Question.year.in_(years))
    papers = [dict(index=i, year=y, shift=s, count=n) for i, (y,s,n) in enumerate(
        refs.with_entities(m.Question.year, m.Question.shift, func.count(m.Question.id))
        .group_by(m.Question.year, m.Question.shift).order_by(m.Question.year, m.Question.shift).all())]
    chapters = [dict(id=cid, subject=sub, name=name) for cid,sub,name in query.join(m.Subtopic).join(m.Chapter).join(m.Subject)
                .with_entities(m.Chapter.id, m.Subject.code, m.Chapter.name).distinct().order_by(m.Chapter.id).all()]
    if not chapters:
        raise HTTPException(422, 'No published questions are available for this exam yet. Choose another exam or use the manual bank.')
    # Return the connection to the pool while waiting on the external provider.
    db.rollback()
    plan = teacher_ai.interpret(b.prompt.strip(), b.exam, {'papers': papers, 'chapters': chapters, 'paper_defaults': b.defaults})
    if plan.clarification:
        raise HTTPException(422, plan.clarification)
    available = {c['id']: c for c in chapters}
    ids = plan.chapter_ids + [cid for section in plan.sections for cid in section.chapter_ids]
    if any(cid not in available for cid in ids):
        raise HTTPException(422, 'The requested chapters are unavailable. Please specify chapters from the bank.')
    subjects = {'PHY', 'CHEM', 'MATH', 'ENG', 'LR'} if b.exam == 'bitsat' else {'PHY', 'CHEM', 'MATH'}
    for section in plan.sections:
        if section.subject not in subjects or section.difficulty_min > section.difficulty_max or any(available[cid]['subject'] != section.subject for cid in section.chapter_ids):
            raise HTTPException(422, 'The requested subject/chapter mix is invalid. Please rephrase it.')
    if plan.count is None:
        if plan.sections: plan.count = sum(s.count for s in plan.sections)
        elif plan.selection != 'exact': raise HTTPException(422, 'How many questions should the paper contain?')
    if plan.count is not None and not 1 <= plan.count <= 200:
        raise HTTPException(422, 'Choose between 1 and 200 questions.')
    if plan.sections and sum(s.count for s in plan.sections) != plan.count:
        raise HTTPException(422, 'Subject counts do not add up to the requested total. Please specify the counts again.')
    if plan.paper_index is not None and plan.paper_index >= len(papers):
        raise HTTPException(422, 'The requested paper is unavailable. Specify its year, date and shift.')
    ref = papers[plan.paper_index] if plan.paper_index is not None else None
    if ref and plan.year is not None and plan.year != ref['year']:
        raise HTTPException(422, 'The year and shift do not match. Please specify them again.')
    if plan.selection in ('similar', 'exact') and not ref:
        raise HTTPException(422, 'Specify one available year, date and shift to match.')
    year = ref['year'] if ref else plan.year
    if plan.selection == 'bank' and (year or ref):
        raise HTTPException(422, 'Please clarify whether to use questions from that paper or create a similar paper.')
    if plan.selection == 'from_paper' and (not year or plan.source == 'original'):
        raise HTTPException(422, 'Specify an available PYQ year or shift.')
    if plan.selection in ('similar', 'exact') and (plan.sections or plan.chapter_ids or plan.source == 'original'):
        raise HTTPException(422, 'Paper matching uses the original mix. Request a subset from the paper to add chapter or subject filters.')
    config = Generate(exam=b.exam, strict_exam=True, published_only=True, count=plan.count or 30, level=plan.level,
                      mode=plan.selection if plan.selection in ('exact', 'similar') else 'blueprint' if plan.sections else 'quick',
                      year=year, shift=ref['shift'] if ref else None, reference_without_shift=bool(ref and ref['shift'] is None),
                      restrict_to_reference=plan.selection == 'from_paper', chapter_ids=plan.chapter_ids,
                      sections=[Section(**s.model_dump()) for s in plan.sections], source=plan.source,
                      exclude_assigned=False)
    result = generate(config, user, db)
    # No database writes to papers/assignments: this response is only a reviewable candidate.
    counts = Counter(q['subject'] for q in result['questions'])
    return {**result, 'configuration': config.model_dump(),
            'settings': {k:v for k,v in {'title':plan.title, 'duration_minutes':plan.duration_minutes, 'marks_correct':plan.marks_correct, 'marks_wrong':plan.marks_wrong, 'sets_enabled':plan.sets_enabled, 'exam':b.exam}.items() if v is not None},
            'summary': {'count': len(result['questions']), 'subjects': dict(counts), 'selection': plan.selection,
                        'year':year, 'shift':ref['shift'] if ref else None,
                        'chapters':[available[cid]['name'] for cid in dict.fromkeys(ids)], 'level':plan.level}}


class PaperIn(BaseModel):
    title: str = Field(min_length=3,max_length=150)
    question_ids: list[int] = Field(min_length=1,max_length=200)
    duration_minutes: int = Field(60,ge=1,le=240)
    marks_correct: int = Field(4,ge=1,le=10)
    marks_wrong: int = Field(1,ge=0,le=10)
    instructions: str = Field('',max_length=2000)
    exam: EXAMS = 'jee_main'
    version: int = Field(1,ge=1)
    sets_enabled: bool = True  # Legacy API clients retain A/B; new UI explicitly opts out.

class AIPaperDefaults(BaseModel):
    duration_minutes: int = Field(60,ge=1,le=240)
    marks_correct: int = Field(4,ge=1,le=10)
    marks_wrong: int = Field(1,ge=0,le=10)
    sets_enabled: bool = False
    instructions: str = Field('',max_length=2000)


class AICompleteRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=6000)
    exam: EXAMS = 'jee_main'
    request_key: str = Field(min_length=36, max_length=36, pattern=r'^[a-fA-F0-9-]{36}$')
    defaults: AIPaperDefaults = Field(default_factory=AIPaperDefaults)


def completed_ai_paper(p):
    return {'state':'ready', 'paper':payload(p), 'downloads':[
        {'variant':v, 'omr':f'/api/teacher/papers/{p.id}/blank-omr.pdf?variant={v}'}
        for v in (['A','B'] if sets_enabled(p) else ['A'])]}


@router.post('/papers/ai-create')
def ai_create(b: AICompleteRequest, user=Depends(t.require_teacher), db=Depends(get_db)):
    def existing(lock=False):
        query=db.query(m.TeacherPaper).filter(m.TeacherPaper.teacher_id==user.id,
            m.TeacherPaper.settings['ai_request_key'].as_string()==b.request_key)
        return (query.with_for_update() if lock else query).order_by(m.TeacherPaper.id).first()
    previous=existing()
    if previous: return completed_ai_paper(previous)
    from app.services.teacher_ai import resolve_request
    requested_exam, question = resolve_request(b.prompt, b.exam)
    if question: return {'state':'needs_details','question':question}
    b.exam = requested_exam
    settings=b.defaults.model_dump()
    # Missing input and ambiguous constraints are returned as a conversational follow-up.
    try:
        draft=ai_draft(AIRequest(prompt=b.prompt,exam=b.exam,defaults=settings),user,db)
    except HTTPException as error:
        if error.status_code==422:
            return {'state':'needs_details','question':error.detail}
        raise
    settings.update(draft['settings'])
    title=settings.pop('title', None) or f"{b.exam.replace('_',' ').upper()} - {len(draft['questions'])} questions"
    settings.pop('exam',None)
    if not omr_report(draft['questions'])['eligible']:
        return {'state':'needs_details','question':'Some matching questions cannot be used on an OMR sheet. Should we use a different topic or paper? Please describe the revised selection.'}
    # Serialize only persistence, not the provider call. Replays return the same saved paper.
    db.query(m.User).filter_by(id=user.id).with_for_update().one()
    previous=existing(lock=True)
    if previous: return completed_ai_paper(previous)
    settings.update(exam=b.exam,ai_request_key=b.request_key)
    p=m.TeacherPaper(teacher_id=user.id,title=title,questions=draft['questions'],settings=settings,
                     finalized=True,version=1,created_at=utcnow(),updated_at=utcnow())
    db.add(p);db.commit()
    return completed_ai_paper(p)


def save_data(b, db, uid):
    if len(b.title.strip())<3: raise HTTPException(422,'Enter a paper title of at least three characters.')
    if len(set(b.question_ids)) != len(b.question_ids): raise HTTPException(422,'Remove duplicate questions.')
    rows={q.id:q for q in bank(db,uid).filter(m.Question.id.in_(b.question_ids)).all()}
    if len(rows)!=len(b.question_ids): raise HTTPException(422,'A selected question is unavailable.')
    return [t.freeze(rows[i],rows[i].version) for i in b.question_ids]

@router.get('/papers')
def papers(user=Depends(t.require_teacher),db=Depends(get_db)):
    return {'papers':[dict(id=p.id,title=p.title,version=p.version,finalized=p.finalized,count=len(p.questions),assignment_id=p.assignment_id,settings=p.settings,sets_enabled=sets_enabled(p),omr=omr_report(p.questions)) for p in db.query(m.TeacherPaper).filter_by(teacher_id=user.id).order_by(m.TeacherPaper.updated_at.desc()).limit(100)]}

@router.post('/papers',status_code=201)
def create(b:PaperIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    p=m.TeacherPaper(teacher_id=user.id,title=b.title.strip(),questions=save_data(b,db,user.id),settings=b.model_dump(exclude={'title','question_ids','version'}),created_at=utcnow(),updated_at=utcnow())
    db.add(p); db.commit(); return payload(p)

@router.get('/papers/{pid}')
def read(pid:int,user=Depends(t.require_teacher),db=Depends(get_db)): return payload(owned(db,pid,user))

@router.put('/papers/{pid}')
def update(pid:int,b:PaperIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    p=owned(db,pid,user)
    if p.finalized: raise HTTPException(409,'Finalised papers cannot be changed. Duplicate this paper first.')
    if p.version!=b.version: raise HTTPException(409,'Draft changed in another window. Reload before saving.')
    p.questions=save_data(b,db,user.id); p.title=b.title.strip(); p.settings=b.model_dump(exclude={'title','question_ids','version'}); p.version+=1; p.updated_at=utcnow()
    db.commit(); return payload(p)

@router.post('/papers/{pid}/duplicate',status_code=201)
def duplicate(pid:int,user=Depends(t.require_teacher),db=Depends(get_db)):
    old=owned(db,pid,user)
    p=m.TeacherPaper(teacher_id=user.id,title=(old.title+' (copy)')[:150],settings={k:v for k,v in old.settings.items() if k!='ai_request_key'},questions=old.questions,created_at=utcnow(),updated_at=utcnow())
    db.add(p); db.commit(); return payload(p)

class VersionIn(BaseModel):
    version:int=Field(ge=1)

@router.post('/papers/{pid}/finalize')
def finalize(pid:int,b:VersionIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    p=owned(db,pid,user)
    if b.version!=p.version: raise HTTPException(409,'Reload the latest paper before finalising.')
    p.finalized=True; db.commit(); return payload(p)

class Schedule(BaseModel):
    classroom_ids:list[int]=Field(min_length=1,max_length=20)
    opens_at:str
    due_at:str
    solutions_at:str

@router.post('/papers/{pid}/assign')
def assign(pid:int,b:Schedule,user=Depends(t.require_teacher),db=Depends(get_db)):
    p=owned(db,pid,user)
    if not p.finalized: raise HTTPException(409,'Finalise the paper first.')
    if p.assignment_id: return {'id':p.assignment_id,'title':p.title}
    if any(q['type']!='numerical' and any(not o['content'] for o in presentation(q['stem'],q['options'])[1]) for q in p.questions):raise HTTPException(409,'This saved paper has missing answer choices. Duplicate it and replace the incomplete questions before assigning it.')
    if db.query(m.TeacherScan.id).filter_by(paper_id=pid,state='reviewed').first(): raise HTTPException(409,'Offline results already exist. Duplicate the paper for a new online assignment, or assign online before reviewing scans.')
    try:
        data=t.PublishIn(**b.model_dump(),**{k:p.settings[k] for k in ('instructions','duration_minutes','marks_correct','marks_wrong')},title=p.title,question_ids=[q['question_id'] for q in p.questions],request_key=f'paper-assignment-{p.id:016d}')
    except ValidationError: raise HTTPException(422,'Choose valid opening, deadline and solution-release dates, including your timezone.')
    # Existing publish handles roster deduplication and notifications. Replace the
    # fresh bank read with the saved snapshot before any student can start.
    result=t.publish_assignment(data,user,db,frozen_questions=p.questions,commit=False)
    p=owned(db,pid,user); a=db.get(m.TeachingAssignment,result['id']); a.questions=p.questions
    p.assignment_id=a.id; db.commit(); return result

@router.get('/references')
def references(user=Depends(t.require_teacher),db=Depends(get_db)):
    rows=db.query(m.Question.exam,m.Question.year,m.Question.shift,func.count(m.Question.id)).filter(m.Question.status=='published',m.Question.source_type=='pyq',m.Question.year.isnot(None),m.Question.exam.in_(['jee_main','jee_advanced','mht_cet','bitsat'])).group_by(m.Question.exam,m.Question.year,m.Question.shift).all()
    return {'papers':[dict(exam=e,year=y,shift=s,count=n) for e,y,s,n in rows]}

class PrivateQuestion(BaseModel):
    subtopic_id:int
    stem:str=Field(min_length=5,max_length=16000)
    type:Literal['single_correct','multi_correct','numerical']='single_correct'
    options:list[str]=Field(default_factory=list,max_length=4)
    correct:Literal['A','B','C','D']|None=None
    correct_options:list[Literal['A','B','C','D']]=Field(default_factory=list,max_length=4)
    answer_min:float|None=None
    answer_max:float|None=None
    solution:str=Field('',max_length=16000)
    difficulty:int=Field(5,ge=1,le=10)

@router.get('/topics')
def topics(user=Depends(t.require_teacher),db=Depends(get_db)):
    return {'topics':[dict(id=s.id,name=s.name,chapter=c.name,subject=sub.code) for s,c,sub in db.query(m.Subtopic,m.Chapter,m.Subject).join(m.Chapter,m.Chapter.id==m.Subtopic.chapter_id).join(m.Subject,m.Subject.id==m.Chapter.subject_id).all()]}

@router.post('/questions/private',status_code=201)
def private(b:PrivateQuestion,user=Depends(t.require_teacher),db=Depends(get_db)):
    if not db.get(m.Subtopic,b.subtopic_id):raise HTTPException(422,'Choose a valid topic.')
    correct=set(b.correct_options or ([b.correct] if b.correct else []))
    if b.type=='numerical':
        if b.answer_min is None or b.answer_max is None or not all(math.isfinite(v) and abs(v)<=3.4e38 for v in (b.answer_min,b.answer_max)) or b.answer_min>b.answer_max:raise HTTPException(422,'Enter a finite numerical answer range, minimum first (magnitude at most 3.4 × 10^38).')
        if b.options or correct:raise HTTPException(422,'Numerical questions use an answer range, not choices.')
    elif not 2<=len(b.options)<=4 or any(not x.strip() or len(x)>8000 for x in b.options) or not correct or not correct<=set('ABCD'[:len(b.options)]) or (b.type=='single_correct' and len(correct)!=1):raise HTTPException(422,'Choose two to four non-empty options and a valid answer key.')
    ref='T'+str(user.id)+'-'+secrets.token_hex(10)
    q=m.Question(ref=ref,subtopic_id=b.subtopic_id,type=b.type,answer_min=b.answer_min if b.type=='numerical' else None,answer_max=b.answer_max if b.type=='numerical' else None,stem=b.stem,solution=b.solution,difficulty=b.difficulty,expected_time_sec=120,source_type='original',status='draft',created_by=user.id,version=1,content_hash=hashlib.sha256(ref.encode()).hexdigest())
    db.add(q);db.flush()
    for i,content in enumerate(b.options): db.add(m.QuestionOption(question_id=q.id,label='ABCD'[i],content=content,is_correct='ABCD'[i] in correct,position=i+1))
    db.flush();db.expire(q,['options']);frozen=t.freeze(q,1)
    db.add(m.QuestionRevision(question_id=q.id,version=1,content=frozen));db.commit()
    return frozen

@router.get('/students')
def students(user=Depends(t.require_teacher),db=Depends(get_db)):
    ids=roster(db,user.id)
    users=db.query(m.User).filter(m.User.id.in_(ids)).all()
    results=db.query(m.TeachingAssignment,m.AssignmentRecipient).join(m.AssignmentRecipient).filter(m.TeachingAssignment.teacher_id==user.id,m.AssignmentRecipient.user_id.in_(ids)).all()
    offline=db.query(m.TeacherScan,m.TeacherSheet,m.TeacherPaper).join(m.TeacherSheet,m.TeacherScan.sheet_id==m.TeacherSheet.id).join(m.TeacherPaper,m.TeacherPaper.id==m.TeacherScan.paper_id).filter(m.TeacherScan.teacher_id==user.id,m.TeacherScan.state=='reviewed',m.TeacherSheet.student_id.in_(ids)).all()
    return {'students':[dict(id=u.id,name=u.name,username=u.username,tests=[dict(title=a.title,assignment_id=a.id,mode='offline' if any(sh.student_id==u.id and p.assignment_id==a.id for s,sh,p in offline) else 'online',result={k:v for k,v in (r.result or {}).items() if k!='questions'}) for a,r in results if r.user_id==u.id]+[dict(title=p.title,paper_id=p.id,mode='offline',result=s.result) for s,sh,p in offline if sh.student_id==u.id and not any(a.id==p.assignment_id and r.user_id==u.id for a,r in results)]) for u in users]}

@router.get('/students.csv')
def students_csv(user=Depends(t.require_teacher),db=Depends(get_db)):
    out=io.StringIO();w=csv.writer(out);w.writerow(['Student ID','Name','Test','Mode','Score','Maximum','Accuracy'])
    def safe(v):
        s=str(v if v is not None else '')
        return "'"+s if s.startswith(('=','+','-','@','\t','\r')) else s
    for s in students(user,db)['students']:
        for test in s['tests']:
            r=test['result'];w.writerow([safe(x) for x in [s['id'],s['name'],test['title'],test['mode'],r.get('score'),r.get('max_score'),r.get('accuracy')]])
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="class-results.csv"'})

class SheetIn(BaseModel):
    student_ids:list[int]=Field(min_length=1,max_length=50)
    variant:Literal['A','B']='A'

def sets_enabled(p):
    return (getattr(p,'settings',None) or {}).get('sets_enabled',True)

def check_variant(p,variant):
    if variant=='B' and not sets_enabled(p): raise HTTPException(422,'This paper uses one question order without sets. Choose the standard paper.')

def omr_report(questions):
    issues=[]
    for index,q in enumerate(questions):
        _,options=presentation(q.get('stem',''),q.get('options',[]));reason=None
        if q.get('type')=='numerical':
            if q.get('answer_min') is None or q.get('answer_max') is None or not all(math.isfinite(float(q[k])) for k in ('answer_min','answer_max')) or q['answer_min']>q['answer_max']: reason='Needs a valid numerical answer range'
        elif q.get('type') in ('single_correct','multi_correct'):
            labels=[o.get('label') for o in options];correct=sum(bool(o.get('is_correct')) for o in options)
            if any(not o.get('content') for o in options):reason='Missing answer option content'
            elif not 2<=len(options)<=4 or len(set(labels))!=len(labels) or not set(labels)<={'A','B','C','D'}:reason='Needs two to four distinct A-D options'
            elif not correct or (q['type']=='single_correct' and correct!=1):reason='Needs a valid answer key'
        else:reason='Unsupported question format'
        if reason:issues.append({'number':index+1,'question_id':q['question_id'],'reason':reason})
    mixed=mixed_omr.needs_mixed(questions)
    return {'eligible':bool(questions) and len(questions)<=200 and not issues,'issues':issues,'eligible_count':len(questions)-len(issues),'total':len(questions),'layout':'mixed' if mixed else 'compact',
        'page_count':len(mixed_omr.pages_for(questions,[q['question_id'] for q in questions])) if mixed and not issues else 1}


def order_for(p,variant):
    ids=[q['question_id'] for q in p.questions]
    if variant=='B': random.Random(f'paper-{p.id}').shuffle(ids)
    return ids

def generic_sheet_id(p,variant,layout=2):
    suffix=':mixed-v3' if layout==3 else ':idgrid-v2' if layout==2 else ''
    return hashlib.sha256(f'jeeedge-reusable-omr:{p.id}:{variant}{suffix}'.encode()).hexdigest()[:32]


def check_omr(p):
    if not p.finalized: raise HTTPException(409,'Finalise the paper before creating OMR sheets.')
    report=omr_report(p.questions)
    if not report['eligible']:
        numbers=', '.join(str(i['number']) for i in report['issues'][:12])
        raise HTTPException(422,f'OMR is unavailable for this paper. Check questions {numbers or "and paper length"} in the paper readiness panel. Print or assign online, or duplicate and replace incompatible questions.')


@router.get('/papers/{pid}/blank-omr.pdf')
def blank_sheet_download(pid:int,variant:Literal['A','B']='A',user=Depends(t.require_teacher),db=Depends(get_db)):
    from types import SimpleNamespace
    from app.services.teacher_omr import sheet_pdf
    p=owned(db,pid,user);check_omr(p);check_variant(p,variant)
    sheet=SimpleNamespace(id=generic_sheet_id(p,variant,3 if mixed_omr.needs_mixed(p.questions) else 2),variant=variant,question_order=order_for(p,variant))
    return Response(sheet_pdf(p,sheet,None),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="omr-{p.id}-{variant}-print-multiple-copies.pdf"'})

@router.post('/papers/{pid}/sheets')
def sheets(pid:int,b:SheetIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    p=owned(db,pid,user)
    check_omr(p);check_variant(p,b.variant)
    if not set(b.student_ids)<=roster(db,user.id): raise HTTPException(404,'Student is not active in your classes.')
    result=[]
    for uid in sorted(set(b.student_ids)):
        s=db.query(m.TeacherSheet).filter_by(paper_id=pid,student_id=uid,variant=b.variant).first()
        if not s:
            s=m.TeacherSheet(id=secrets.token_hex(16),paper_id=pid,student_id=uid,variant=b.variant,question_order=order_for(p,b.variant),created_at=utcnow());db.add(s)
        result.append({'id':s.id,'student_id':uid,'variant':b.variant})
    db.commit();return {'sheets':result}

@router.get('/sheets/{sid}.pdf')
def sheet_download(sid:str,user=Depends(t.require_teacher),db=Depends(get_db)):
    from app.services.teacher_omr import sheet_pdf
    sh=db.get(m.TeacherSheet,sid)
    if not sh: raise HTTPException(404,'Sheet not found.')
    p=owned(db,sh.paper_id,user);student=db.get(m.User,sh.student_id)
    return Response(sheet_pdf(p,sh,student.name),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="omr-{p.id}-{sh.student_id}-{sh.variant}.pdf"'})

class ScanIn(BaseModel):
    image_base64:str=Field(min_length=50,max_length=12_000_000)

@router.post('/papers/{pid}/scans',status_code=202)
def scan(pid:int,b:ScanIn,tasks:BackgroundTasks,user=Depends(t.require_teacher),db=Depends(get_db)):
    from app.services import teacher_omr as omr
    p=owned(db,pid,user)
    check_omr(p)
    active=db.query(m.TeacherScan).filter(m.TeacherScan.teacher_id==user.id,m.TeacherScan.state.in_(['queued','processing']),m.TeacherScan.created_at>utcnow()-timedelta(minutes=10)).count()
    global_active=db.query(m.TeacherScan).filter(m.TeacherScan.state.in_(['queued','processing']),m.TeacherScan.created_at>utcnow()-timedelta(minutes=10)).count()
    if global_active>=120: raise HTTPException(429,'The scan queue is busy. Retry after current scans finish.')
    if active>=60: raise HTTPException(429,'Sixty pages are processing. Wait for them before uploading more.')
    try:
        data=base64.b64decode(b.image_base64,validate=True)
        if len(data)>8_000_000: raise ValueError('Maximum upload size is 8 MB.')
        if data.startswith(b'%PDF-'):
            import pypdfium2 as pdfium
            with pdfium.PdfDocument(data) as document:
                if not 1<=len(document)<=60: raise ValueError('Upload PDF batches of one to sixty pages.')
                images=[]
                for page in document:
                    width,height=page.get_size()
                    if min(width,height)<=0: raise ValueError('Invalid PDF page dimensions.')
                    bitmap=page.render(scale=min(2,2200/max(width,height)))
                    image=bitmap.to_pil();output=io.BytesIO();image.save(output,format='PNG');images.append(output.getvalue())
                    image.close();bitmap.close();page.close()
        else:
            omr.decode_image(data);images=[data]
    except ValueError as e: raise HTTPException(422,str(e)[:200])
    except Exception: raise HTTPException(422,'Upload a valid JPEG, PNG or PDF below 8 MB. PDFs may contain up to sixty pages.')
    if active+len(images)>60 or global_active+len(images)>120: raise HTTPException(429,'Wait for current scans to finish before uploading this batch.')
    identities=[]
    for image in images:
        identity=secrets.token_hex(16);omr.path(identity,'input').write_bytes(image)
        db.add(m.TeacherScan(id=identity,teacher_id=user.id,paper_id=pid,state='queued',created_at=utcnow()))
        identities.append(identity)
    db.commit()
    for identity in identities: tasks.add_task(process_scan,identity)
    return {'id':identities[0],'ids':identities,'state':'queued'}

def process_scan(identity):
    from app.services import teacher_omr as omr
    with omr.GATE:
        try:
            with SessionLocal() as db:
                scan=db.get(m.TeacherScan,identity)
                if not scan or scan.state!='queued': return
                scan.state='processing';db.commit()
                sid,aligned=omr.detect(omr.path(identity,'input').read_bytes())
                mixed_page=None
                if sid.startswith('v3:'):
                    _,sid,page_text=sid.split(':');mixed_page=int(page_text)
                sh=db.get(m.TeacherSheet,sid);p=db.get(m.TeacherPaper,scan.paper_id)
                if not p or p.teacher_id!=scan.teacher_id: raise ValueError('Paper is unavailable.')
                if mixed_omr.needs_mixed(p.questions)!=(mixed_page is not None): raise ValueError('This answer-sheet layout does not match the paper. Download its current sheet.')
                template=next(((v,layout) for layout in ((3,) if mixed_page is not None else (2,1)) for v in (('A','B') if sets_enabled(p) else ('A',)) if sid==generic_sheet_id(p,v,layout)),None)
                template_variant,layout=template if template else (None,0)
                if template_variant:
                    count=len(p.questions);scan.result={'template_variant':template_variant}
                    if layout in (2,3):
                        identity_result=omr.read_student_id(aligned)
                        if identity_result['status']=='clear':
                            uid=int(identity_result['digits'])
                            t.lock_user(db,scan.teacher_id)
                            if uid in roster(db,scan.teacher_id):
                                matched=db.query(m.TeacherSheet).filter_by(paper_id=p.id,student_id=uid,variant=template_variant).first()
                                if not matched:
                                    matched=m.TeacherSheet(id=secrets.token_hex(16),paper_id=p.id,student_id=uid,variant=template_variant,question_order=order_for(p,template_variant),created_at=utcnow())
                                    db.add(matched);db.flush()
                                scan.sheet_id=matched.id;identity_result['status']='matched'
                            else: identity_result['status']='not_in_roster'
                        scan.result={**scan.result,'identity':identity_result}
                elif sh and sh.paper_id==scan.paper_id:
                    count=len(sh.question_order);scan.sheet_id=sid
                else: raise ValueError('This QR code belongs to another paper. Select the matching paper.')
                if mixed_page is not None:
                    variant=template_variant or sh.variant
                    pages=mixed_omr.pages_for(p.questions,order_for(p,variant))
                    if mixed_page>=len(pages): raise ValueError('Invalid page number for this paper.')
                    items=pages[mixed_page]
                    scan.result={**(scan.result or {}),'layout':3,'page_index':mixed_page,'page_count':len(pages),'question_order':[i['question_id'] for i in items]}
                    found,preview=mixed_omr.scan(aligned,items)
                else:
                    found,preview=omr.bubbles(aligned,count,id_grid=layout==2)
                    question_ids=order_for(p,template_variant) if template_variant else sh.question_order
                    lookup={q['question_id']:q for q in p.questions}
                    found=[{**d,'question_id':qid,'type':lookup[qid]['type'],'labels':[o['label'] for o in lookup[qid]['options']]} for d,qid in zip(found,question_ids)]
                omr.path(identity,'jpg').write_bytes(preview)
                scan.detection=found;scan.state='review';db.commit()
        except Exception as e:
            with SessionLocal() as db:
                scan=db.get(m.TeacherScan,identity)
                if scan:
                    scan.state='failed';scan.error=str(e)[:300] if isinstance(e,ValueError) else 'Scan processing failed. Upload a sharper image and retry.';db.commit()
        finally:
            omr.path(identity,'input').unlink(missing_ok=True)
            # Original photos are transient. Review overlays expire after 24 hours.
            import time
            for f in omr.WORK.glob('*.jpg'):
                if f.stat().st_mtime<time.time()-86400: f.unlink(missing_ok=True)

def own_scan(db,sid,user):
    s=db.query(m.TeacherScan).filter_by(id=sid,teacher_id=user.id).with_for_update().first()
    if not s: raise HTTPException(404,'Scan not found.')
    return s

@router.get('/papers/{pid}/scans')
def scans(pid:int,user=Depends(t.require_teacher),db=Depends(get_db)):
    from app.services import teacher_omr as omr
    owned(db,pid,user)
    rows=db.query(m.TeacherScan).filter_by(paper_id=pid,teacher_id=user.id).order_by(m.TeacherScan.created_at.desc()).limit(100).all()
    output=[]
    for s in rows:
        if s.state in ('queued','processing') and s.created_at<utcnow()-timedelta(minutes=10): s.state='failed';s.error='Processing was interrupted. Upload the image again.'
        sh=db.get(m.TeacherSheet,s.sheet_id) if s.sheet_id else None
        student=db.get(m.User,sh.student_id) if sh else None
        can_reopen=s.state=='page_reviewed' and sh and not db.query(m.TeacherScan.id).join(m.TeacherSheet,m.TeacherSheet.id==m.TeacherScan.sheet_id).filter(m.TeacherScan.paper_id==pid,m.TeacherScan.state=='reviewed',m.TeacherSheet.student_id==sh.student_id).first()
        output.append(dict(can_reopen=bool(can_reopen),preview_available=omr.path(s.id,'jpg').is_file(),id=s.id,state=s.state,error=s.error,version=s.version,detection=s.detection,answers=s.answers,result=s.result,student=student.name if student else None,student_id=sh.student_id if sh else None,variant=sh.variant if sh else (s.result or {}).get('template_variant')))
    db.commit();return {'scans':output}

@router.post('/scans/{sid}/reopen-page')
def reopen_page(sid:str,b:VersionIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    from app.services import teacher_omr as omr
    row=own_scan(db,sid,user);owned(db,row.paper_id,user)
    if row.state!='page_reviewed' or row.version!=b.version:raise HTTPException(409,'Reload this page before editing it.')
    sheet=db.get(m.TeacherSheet,row.sheet_id)
    if db.query(m.TeacherScan.id).join(m.TeacherSheet,m.TeacherSheet.id==m.TeacherScan.sheet_id).filter(m.TeacherScan.paper_id==row.paper_id,m.TeacherScan.state=='reviewed',m.TeacherSheet.student_id==sheet.student_id).first():raise HTTPException(409,'The full paper has already been scored.')
    row.state='review' if omr.path(sid,'jpg').is_file() else 'superseded'
    row.version+=1
    db.add(m.AuditLog(actor_id=user.id,action='omr_page_reopened',entity='teacher_paper',entity_id=row.paper_id,after={'scan_id':row.id,'student_id':sheet.student_id,'state':row.state},reason='Teacher reopened a confirmed page before final scoring.'))
    db.commit();return {'state':row.state,'version':row.version}

@router.get('/scans/{sid}/preview')
def preview(sid:str,user=Depends(t.require_teacher),db=Depends(get_db)):
    from app.services import teacher_omr as omr
    own_scan(db,sid,user);p=omr.path(sid,'jpg')
    if not p.is_file(): raise HTTPException(410,'Preview expired or the server restarted. Upload again if visual review is needed.')
    return FileResponse(p,media_type='image/jpeg')

class ReviewIn(BaseModel):
    version:int=Field(ge=1)
    student_id:int|None=Field(None,ge=1)
    answers:list[str]=Field(min_length=1,max_length=200)

@router.post('/scans/{sid}/review')
def review(sid:str,b:ReviewIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    s=own_scan(db,sid,user);p=owned(db,s.paper_id,user)
    if s.version!=b.version or s.state!='review': raise HTTPException(409,'This scan is already reviewed or changed. Reload it.')
    from app.services import teacher_omr as omr
    if not omr.path(sid,'jpg').is_file(): raise HTTPException(410,'Preview expired. Upload the sheet again before reviewing.')
    sh=db.get(m.TeacherSheet,s.sheet_id) if s.sheet_id else None
    # A reusable sheet can contain a clearly shaded but mistaken student ID.
    # Personalised QR sheets remain bound to their original student.
    if sh and (s.result or {}).get('template_variant') and b.student_id and b.student_id!=sh.student_id:
        s.result={**s.result,'identity':{**s.result.get('identity',{}),'corrected_from_student_id':sh.student_id,'reviewed_student_id':b.student_id}}
        sh=None
    if not sh:
        variant=(s.result or {}).get('template_variant')
        if variant not in ('A','B'): raise HTTPException(409,'Sheet identity is unavailable. Upload again.')
        if not b.student_id: raise HTTPException(422,'Select the student whose name and ID are written on this sheet.')
        if b.student_id not in roster(db,user.id): raise HTTPException(404,'Student is not active in your classes.')
        sh=db.query(m.TeacherSheet).filter_by(paper_id=p.id,student_id=b.student_id,variant=variant).first()
        if not sh:
            sh=m.TeacherSheet(id=secrets.token_hex(16),paper_id=p.id,student_id=b.student_id,variant=variant,question_order=order_for(p,variant),created_at=utcnow())
            db.add(sh);db.flush()
        s.sheet_id=sh.id
    elif b.student_id is not None and b.student_id!=sh.student_id:
        raise HTTPException(422,'A personalised sheet cannot be assigned to a different student.')
    if sh.student_id not in roster(db,user.id): raise HTTPException(404,'Student is no longer active in your classes. Restore membership before saving a score.')
    page_meta=s.result or {}
    page_order=page_meta.get('question_order',sh.question_order)
    if len(b.answers)!=len(page_order) or any(len(a)>100 for a in b.answers): raise HTTPException(422,'Review every answer on this page, including blanks.')
    qmap={q['question_id']:q for q in p.questions}
    page_answers=[paper_answers.normalize(qmap[qid],answer) for qid,answer in zip(page_order,b.answers)]
    other=db.query(m.TeacherScan).join(m.TeacherSheet,m.TeacherSheet.id==m.TeacherScan.sheet_id).filter(m.TeacherScan.paper_id==p.id,m.TeacherScan.state=='reviewed',m.TeacherSheet.student_id==sh.student_id).first()
    if other: raise HTTPException(409,'This student already has a reviewed offline result for this paper. Duplicate scans cannot add another score.')
    if p.assignment_id:
        t.lock_user(db,sh.student_id)
        recipient=db.query(m.AssignmentRecipient).filter_by(assignment_id=p.assignment_id,user_id=sh.student_id).with_for_update().populate_existing().first()
        if recipient and recipient.attempt_id: raise HTTPException(409,'This student has already started online. Finish or review that attempt instead of adding an offline score.')
    identity_result=page_meta.get('identity')
    full_answers=page_answers
    if page_meta.get('layout')==3:
        pages=mixed_omr.pages_for(p.questions,sh.question_order)
        previous=db.query(m.TeacherScan).filter_by(paper_id=p.id,sheet_id=sh.id,state='page_reviewed').with_for_update().all()
        confirmed={r.result['page_index']:r for r in previous}
        page_index=page_meta['page_index']
        if page_index in confirmed:raise HTTPException(409,'This page is already confirmed for this student. Duplicate pages cannot change saved answers.')
        s.answers=page_answers;s.result={**page_meta,'student_id':sh.student_id};s.state='page_reviewed';s.reviewed_at=utcnow();s.version+=1
        confirmed[page_index]=s
        if len(confirmed)<len(pages):
            db.commit();return {'complete':False,'confirmed_pages':len(confirmed),'page_count':len(pages),'missing_pages':[i+1 for i in range(len(pages)) if i not in confirmed]}
        collected={}
        for index,row in confirmed.items():
            expected=[i['question_id'] for i in pages[index]]
            if row.result.get('question_order')!=expected or len(row.answers)!=len(expected):raise HTTPException(409,'Page contents changed. Re-upload the matching answer sheet.')
            collected.update(zip(expected,row.answers))
        if set(collected)!=set(sh.question_order):raise HTTPException(409,'Some answers are missing. Review every page.')
        full_answers=[collected[qid] for qid in sh.question_order]
        # Keep page membership so a corrected key can regrade the full paper later.
        page_meta={**page_meta,'confirmed_scan_ids':[r.id for r in confirmed.values()]}
    s.answers=full_answers;s.result=offline_score(p,sh,full_answers)
    if identity_result:s.result={**s.result,'identity':identity_result}
    if page_meta.get('layout')==3:s.result={**s.result,**{k:page_meta[k] for k in ('layout','page_index','page_count','confirmed_scan_ids')}}
    s.state='reviewed';s.reviewed_at=utcnow();s.version+=1
    db.add(m.AuditLog(actor_id=user.id,action='omr_reviewed',entity='teacher_paper',entity_id=p.id,after={'scan_id':s.id,'student_id':sh.student_id,'variant':sh.variant,'score':s.result['score'],'identity':identity_result},reason='Teacher confirmed all pages and detected answers.'))
    if p.assignment_id:
        assignment=db.get(m.TeachingAssignment,p.assignment_id)
        if recipient:
            attempt=m.TestAttempt(user_id=sh.student_id,test_id=assignment.test_id,started_at=utcnow(),attempt_number=1,counts_for_rank=False)
            db.add(attempt);db.flush();recipient.attempt_id=attempt.id
            recipient.draft=[paper_answers.draft(qmap[qid],answer) for qid,answer in zip(sh.question_order,full_answers)]
            t.finalize(db,assignment,recipient,attempt)
    db.commit();return {'complete':True,'result':s.result}


def offline_score(p,sh,answers):
    qmap={q['question_id']:q for q in p.questions};details=[]
    for qid,answer in zip(sh.question_order,answers):
        q=qmap[qid];outcome=paper_answers.outcome(q,answer)
        details.append(dict(question_id=qid,answer=answer,outcome=outcome,marks=p.settings['marks_correct'] if outcome=='correct' else -p.settings['marks_wrong'] if outcome=='wrong' else 0,topic=q['topic']))
    correct=sum(d['outcome']=='correct' for d in details);attempted=sum(d['outcome']!='skipped' for d in details)
    return dict(score=sum(d['marks'] for d in details),max_score=len(details)*p.settings['marks_correct'],correct=correct,attempted=attempted,accuracy=round(correct*100/attempted,2) if attempted else 0,questions=details)

class KeyCorrection(BaseModel):
    question_id:int
    correct:Literal['A','B','C','D']|None=None
    correct_options:list[Literal['A','B','C','D']]=Field(default_factory=list,max_length=4)
    answer_min:float|None=None
    answer_max:float|None=None

class CorrectKeyIn(BaseModel):
    version:int=Field(ge=1)
    reason:str=Field(min_length=5,max_length=1000)
    corrections:list[KeyCorrection]=Field(min_length=1,max_length=200)

@router.post('/papers/{pid}/correct-key')
def correct_key(pid:int,b:CorrectKeyIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    """Correct a frozen MCQ key and regrade every affected result atomically."""
    import copy
    p=owned(db,pid,user)
    if not p.finalized or b.version!=p.version: raise HTTPException(409,'Reload the finalised paper before correcting its key.')
    questions=copy.deepcopy(p.questions);qmap={q['question_id']:q for q in questions}
    before=[]
    if len({c.question_id for c in b.corrections})!=len(b.corrections): raise HTTPException(422,'Each question may be corrected once.')
    for change in b.corrections:
        q=qmap.get(change.question_id)
        if not q:raise HTTPException(422,'Choose a question from this saved paper.')
        before.append({'question_id':q['question_id'],'correct':[o['label'] for o in q['options'] if o['is_correct']],'answer_min':q['answer_min'],'answer_max':q['answer_max']})
        correct=set(change.correct_options or ([change.correct] if change.correct else []))
        if q['type']=='numerical':
            if correct or change.answer_min is None or change.answer_max is None or not all(math.isfinite(v) and abs(v)<=3.4e38 for v in (change.answer_min,change.answer_max)) or change.answer_min>change.answer_max:raise HTTPException(422,'Enter a finite, ordered numerical answer range within ±3.4e38.')
            q['answer_min']=change.answer_min;q['answer_max']=change.answer_max
        else:
            if not correct or not correct<={o['label'] for o in q['options']} or (q['type']=='single_correct' and len(correct)!=1):raise HTTPException(422,'Choose the correct option or options for this question.')
            for o in q['options']:o['is_correct']=o['label'] in correct
    p.questions=questions;p.version+=1;p.updated_at=utcnow()
    online=offline=0
    if p.assignment_id:
        assignment=db.get(m.TeachingAssignment,p.assignment_id)
        assignment.questions=questions
        # Match normal grading's lock order. Re-read recipients after acquiring
        # the student lock so an in-flight submission cannot be counted twice.
        ids=[x[0] for x in db.query(m.AssignmentRecipient.user_id).filter_by(assignment_id=assignment.id).order_by(m.AssignmentRecipient.user_id)]
        for uid in ids:
            t.lock_user(db,uid,allow_inactive=True)
            r=db.query(m.AssignmentRecipient).filter_by(assignment_id=assignment.id,user_id=uid).with_for_update().populate_existing().first()
            if not r.result: continue
            attempt=db.get(m.TestAttempt,r.attempt_id)
            submitted=attempt.submitted_at
            # Undo only this attempt's mastery contribution, then use the same
            # authoritative grader. Other practice history is retained.
            db.query(m.StudentProfile).filter_by(user_id=uid).with_for_update().first()
            previous_dates={}
            for old in r.result['questions']:
                if old['outcome']=='skipped': continue
                stat=db.query(m.StudentSubtopicStats).filter_by(user_id=uid,subtopic_id=qmap[old['question_id']]['subtopic_id']).with_for_update().first()
                if stat:
                    previous_dates.setdefault(stat.subtopic_id,stat.last_attempted_at)
                    stat.attempted=max(0,stat.attempted-1);stat.correct=max(0,stat.correct-int(old['outcome']=='correct'))
                    stat.mastery=stat.correct/stat.attempted if stat.attempted else 0
            db.query(m.QuestionResponse).filter_by(attempt_id=attempt.id).delete(synchronize_session=False)
            r.result=None;db.flush();t.finalize(db,assignment,r,attempt)
            for topic_id,last_date in previous_dates.items():
                db.query(m.StudentSubtopicStats).filter_by(user_id=uid,subtopic_id=topic_id).one().last_attempted_at=last_date
            attempt.submitted_at=submitted;r.result={**r.result,'submitted_at':t.stamp(submitted)}
            online+=1
    for scan,sh in db.query(m.TeacherScan,m.TeacherSheet).join(m.TeacherSheet,m.TeacherSheet.id==m.TeacherScan.sheet_id).filter(m.TeacherScan.paper_id==p.id,m.TeacherScan.state=='reviewed').all():
        metadata={k:v for k,v in (scan.result or {}).items() if k in ('identity','layout','page_index','page_count','confirmed_scan_ids')}
        scan.result={**offline_score(p,sh,scan.answers),**metadata};scan.version+=1;offline+=1
    db.add(m.AuditLog(actor_id=user.id,action='teacher_key_corrected',entity='teacher_paper',entity_id=p.id,
        before={'keys':before,'version':b.version},after={'keys':[c.model_dump() for c in b.corrections],'version':p.version,'online_results':online,'offline_results':offline},reason=b.reason.strip()))
    db.commit();return {'paper':payload(p),'online_results':online,'offline_results':offline}
