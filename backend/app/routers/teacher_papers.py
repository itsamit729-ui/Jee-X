"""Teacher-owned editable papers, blueprint selection, exports and offline review."""
import base64
import csv
import hashlib
import io
import random
import secrets
from collections import Counter
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, func
from app import models as m
from app.database import get_db, SessionLocal
from app.auth import utcnow
from app.routers import teaching as t

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
                finalized=p.finalized, assignment_id=p.assignment_id, variant_b=order_for(p,'B'), updated_at=t.stamp(p.updated_at))

class Section(BaseModel):
    subject: Literal['PHY','CHEM','MATH','ENG','LR']
    count: int = Field(ge=1, le=200)
    chapter_ids: list[int] = Field(default_factory=list, max_length=100)
    difficulty_min: int = Field(1, ge=1, le=10)
    difficulty_max: int = Field(10, ge=1, le=10)
    type: Literal['single_correct','multi_correct','numerical'] = 'single_correct'

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
    exclude_assigned: bool = True
    source: Literal['all','pyq','original'] = 'all'

@router.post('/papers/generate')
def generate(b: Generate, user=Depends(t.require_teacher), db=Depends(get_db)):
    student_ids=roster(db, user.id, b.classroom_ids)
    query = bank(db, user.id).join(m.Subtopic).join(m.Chapter).join(m.Subject)
    query = query.filter(or_(m.Question.exam == b.exam, m.Question.exam.is_(None)))
    if b.source != 'all': query = query.filter(m.Question.source_type == b.source)
    if b.chapter_ids: query = query.filter(m.Chapter.id.in_(b.chapter_ids))
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
        if not b.year or not b.shift: raise HTTPException(422, 'Choose a year and the exact paper label from the bank.')
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
            if isinstance(req, Section): return r['subject'] == req.subject and (not req.chapter_ids or r['chapter_id'] in req.chapter_ids) and r['type'] == req.type and req.difficulty_min <= r['difficulty'] <= req.difficulty_max
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

class PaperIn(BaseModel):
    title: str = Field(min_length=3,max_length=150)
    question_ids: list[int] = Field(min_length=1,max_length=200)
    duration_minutes: int = Field(60,ge=1,le=240)
    marks_correct: int = Field(4,ge=1,le=10)
    marks_wrong: int = Field(1,ge=0,le=10)
    instructions: str = Field('',max_length=2000)
    exam: EXAMS = 'jee_main'
    version: int = Field(1,ge=1)

def save_data(b, db, uid):
    if len(set(b.question_ids)) != len(b.question_ids): raise HTTPException(422,'Remove duplicate questions.')
    rows={q.id:q for q in bank(db,uid).filter(m.Question.id.in_(b.question_ids)).all()}
    if len(rows)!=len(b.question_ids): raise HTTPException(422,'A selected question is unavailable.')
    return [t.freeze(rows[i],rows[i].version) for i in b.question_ids]

@router.get('/papers')
def papers(user=Depends(t.require_teacher),db=Depends(get_db)):
    return {'papers':[dict(id=p.id,title=p.title,version=p.version,finalized=p.finalized,count=len(p.questions),settings=p.settings) for p in db.query(m.TeacherPaper).filter_by(teacher_id=user.id).order_by(m.TeacherPaper.updated_at.desc()).limit(100)]}

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
    p=m.TeacherPaper(teacher_id=user.id,title=(old.title+' (copy)')[:150],settings=old.settings,questions=old.questions,created_at=utcnow(),updated_at=utcnow())
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
    if db.query(m.TeacherScan.id).filter_by(paper_id=pid,state='reviewed').first(): raise HTTPException(409,'Offline results already exist. Duplicate the paper for a new online assignment, or assign online before reviewing scans.')
    data=t.PublishIn(**b.model_dump(),**{k:p.settings[k] for k in ('instructions','duration_minutes','marks_correct','marks_wrong')},title=p.title,question_ids=[q['question_id'] for q in p.questions],request_key=f'paper-assignment-{p.id:016d}')
    # Existing publish handles roster deduplication and notifications. Replace the
    # fresh bank read with the saved snapshot before any student can start.
    result=t.publish_assignment(data,user,db,frozen_questions=p.questions,commit=False)
    p=owned(db,pid,user); a=db.get(m.TeachingAssignment,result['id']); a.questions=p.questions
    p.assignment_id=a.id; db.commit(); return result

@router.get('/references')
def references(user=Depends(t.require_teacher),db=Depends(get_db)):
    rows=db.query(m.Question.exam,m.Question.year,m.Question.shift,func.count(m.Question.id)).filter(m.Question.status=='published',m.Question.source_type=='pyq',m.Question.shift.isnot(None)).group_by(m.Question.exam,m.Question.year,m.Question.shift).all()
    return {'papers':[dict(exam=e,year=y,shift=s,count=n) for e,y,s,n in rows]}

class PrivateQuestion(BaseModel):
    subtopic_id:int
    stem:str=Field(min_length=5,max_length=16000)
    options:list[str]=Field(min_length=4,max_length=4)
    correct:Literal['A','B','C','D']
    solution:str=Field('',max_length=16000)
    difficulty:int=Field(5,ge=1,le=10)

@router.get('/topics')
def topics(user=Depends(t.require_teacher),db=Depends(get_db)):
    return {'topics':[dict(id=s.id,name=s.name,chapter=c.name,subject=sub.code) for s,c,sub in db.query(m.Subtopic,m.Chapter,m.Subject).join(m.Chapter,m.Chapter.id==m.Subtopic.chapter_id).join(m.Subject,m.Subject.id==m.Chapter.subject_id).all()]}

@router.post('/questions/private',status_code=201)
def private(b:PrivateQuestion,user=Depends(t.require_teacher),db=Depends(get_db)):
    if not db.get(m.Subtopic,b.subtopic_id) or any(not x.strip() or len(x)>8000 for x in b.options): raise HTTPException(422,'Choose a valid topic and four non-empty options.')
    ref='T'+str(user.id)+'-'+secrets.token_hex(10)
    q=m.Question(ref=ref,subtopic_id=b.subtopic_id,type='single_correct',stem=b.stem,solution=b.solution,difficulty=b.difficulty,expected_time_sec=120,source_type='original',status='draft',created_by=user.id,version=1,content_hash=hashlib.sha256(ref.encode()).hexdigest())
    db.add(q);db.flush()
    for i,content in enumerate(b.options): db.add(m.QuestionOption(question_id=q.id,label='ABCD'[i],content=content,is_correct='ABCD'[i]==b.correct,position=i+1))
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

def order_for(p,variant):
    ids=[q['question_id'] for q in p.questions]
    if variant=='B': random.Random(f'paper-{p.id}').shuffle(ids)
    return ids

@router.post('/papers/{pid}/sheets')
def sheets(pid:int,b:SheetIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    p=owned(db,pid,user)
    if not p.finalized: raise HTTPException(409,'Finalise the paper before creating OMR sheets.')
    if any(q['type']!='single_correct' or len(q['options'])!=4 or sum(o['is_correct'] for o in q['options'])!=1 for q in p.questions): raise HTTPException(422,'OMR supports single-correct A–D questions with four options. Numerical/multi-correct papers remain available online and for printing.')
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
    if not p.finalized: raise HTTPException(409,'Finalise the paper before uploading scans.')
    active=db.query(m.TeacherScan).filter(m.TeacherScan.teacher_id==user.id,m.TeacherScan.state.in_(['queued','processing']),m.TeacherScan.created_at>utcnow()-timedelta(minutes=10)).count()
    global_active=db.query(m.TeacherScan).filter(m.TeacherScan.state.in_(['queued','processing']),m.TeacherScan.created_at>utcnow()-timedelta(minutes=10)).count()
    if global_active>=8: raise HTTPException(429,'The scan queue is busy. Retry after current scans finish.')
    if active>=3: raise HTTPException(429,'Three scans are processing. Wait for them before uploading more.')
    try:
        data=base64.b64decode(b.image_base64,validate=True)
        if len(data)>8_000_000: raise ValueError('Maximum upload size is 8 MB.')
        if data.startswith(b'%PDF-'):
            import pypdfium2 as pdfium
            with pdfium.PdfDocument(data) as document:
                if not 1<=len(document)<=3: raise ValueError('Upload PDF batches of one to three pages.')
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
    except Exception: raise HTTPException(422,'Upload a valid JPEG, PNG or PDF below 8 MB. PDFs may contain up to three pages.')
    if active+len(images)>3 or global_active+len(images)>8: raise HTTPException(429,'Wait for current scans to finish before uploading this batch.')
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
                sh=db.get(m.TeacherSheet,sid);p=db.get(m.TeacherPaper,scan.paper_id)
                if not sh or sh.paper_id!=scan.paper_id or p.teacher_id!=scan.teacher_id: raise ValueError('This QR code belongs to another paper. Select the matching paper.')
                found,preview=omr.bubbles(aligned,len(sh.question_order))
                omr.path(identity,'jpg').write_bytes(preview)
                scan.sheet_id=sid;scan.detection=found;scan.state='review';db.commit()
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
    owned(db,pid,user)
    rows=db.query(m.TeacherScan).filter_by(paper_id=pid,teacher_id=user.id).order_by(m.TeacherScan.created_at.desc()).limit(100).all()
    output=[]
    for s in rows:
        if s.state in ('queued','processing') and s.created_at<utcnow()-timedelta(minutes=10): s.state='failed';s.error='Processing was interrupted. Upload the image again.'
        sh=db.get(m.TeacherSheet,s.sheet_id) if s.sheet_id else None
        student=db.get(m.User,sh.student_id) if sh else None
        output.append(dict(id=s.id,state=s.state,error=s.error,version=s.version,detection=s.detection,answers=s.answers,result=s.result,student=student.name if student else None,student_id=sh.student_id if sh else None,variant=sh.variant if sh else None))
    db.commit();return {'scans':output}

@router.get('/scans/{sid}/preview')
def preview(sid:str,user=Depends(t.require_teacher),db=Depends(get_db)):
    from app.services import teacher_omr as omr
    own_scan(db,sid,user);p=omr.path(sid,'jpg')
    if not p.is_file(): raise HTTPException(410,'Preview expired or the server restarted. Upload again if visual review is needed.')
    return FileResponse(p,media_type='image/jpeg')

class ReviewIn(BaseModel):
    version:int=Field(ge=1)
    answers:list[Literal['','A','B','C','D','invalid']]=Field(min_length=1,max_length=200)

@router.post('/scans/{sid}/review')
def review(sid:str,b:ReviewIn,user=Depends(t.require_teacher),db=Depends(get_db)):
    s=own_scan(db,sid,user);p=owned(db,s.paper_id,user)
    if s.version!=b.version or s.state!='review': raise HTTPException(409,'This scan is already reviewed or changed. Reload it.')
    from app.services import teacher_omr as omr
    if not omr.path(sid,'jpg').is_file(): raise HTTPException(410,'Preview expired. Upload the sheet again before reviewing.')
    sh=db.get(m.TeacherSheet,s.sheet_id)
    if len(b.answers)!=len(sh.question_order): raise HTTPException(422,'Review every answer, including blanks.')
    other=db.query(m.TeacherScan).join(m.TeacherSheet,m.TeacherSheet.id==m.TeacherScan.sheet_id).filter(m.TeacherScan.paper_id==p.id,m.TeacherScan.state=='reviewed',m.TeacherSheet.student_id==sh.student_id).first()
    if other: raise HTTPException(409,'This student already has a reviewed offline result for this paper. Duplicate scans cannot add another score.')
    if p.assignment_id:
        t.lock_user(db,sh.student_id)
        recipient=db.query(m.AssignmentRecipient).filter_by(assignment_id=p.assignment_id,user_id=sh.student_id).with_for_update().populate_existing().first()
        if recipient and recipient.attempt_id: raise HTTPException(409,'This student has already started online. Finish or review that attempt instead of adding an offline score.')
    qmap={q['question_id']:q for q in p.questions}
    s.answers=b.answers;s.result=offline_score(p,sh,b.answers)
    s.state='reviewed';s.reviewed_at=utcnow();s.version+=1
    db.add(m.AuditLog(actor_id=user.id,action='omr_reviewed',entity='teacher_paper',entity_id=p.id,after={'scan_id':s.id,'score':s.result['score']},reason='Teacher confirmed all detected answers.'))
    if p.assignment_id:
        assignment=db.get(m.TeachingAssignment,p.assignment_id)
        if recipient:
            attempt=m.TestAttempt(user_id=sh.student_id,test_id=assignment.test_id,started_at=utcnow(),attempt_number=1,counts_for_rank=False)
            db.add(attempt);db.flush();recipient.attempt_id=attempt.id
            recipient.draft=[{'question_id':qid,'option_ids':[o['id'] for o in qmap[qid]['options'] if o['label']==answer],'numeric_answer':None,'time_taken_sec':0,'invalid':answer=='invalid'} for qid,answer in zip(sh.question_order,b.answers)]
            t.finalize(db,assignment,recipient,attempt)
    db.commit();return {'result':s.result}


def offline_score(p,sh,answers):
    qmap={q['question_id']:q for q in p.questions};details=[]
    for qid,answer in zip(sh.question_order,answers):
        q=qmap[qid];key=next(o['label'] for o in q['options'] if o['is_correct']);outcome='skipped' if not answer else 'correct' if answer==key else 'wrong'
        details.append(dict(question_id=qid,answer=answer,outcome=outcome,marks=p.settings['marks_correct'] if outcome=='correct' else -p.settings['marks_wrong'] if outcome=='wrong' else 0,topic=q['topic']))
    correct=sum(d['outcome']=='correct' for d in details);attempted=sum(d['outcome']!='skipped' for d in details)
    return dict(score=sum(d['marks'] for d in details),max_score=len(details)*p.settings['marks_correct'],correct=correct,attempted=attempted,accuracy=round(correct*100/attempted,2) if attempted else 0,questions=details)

class KeyCorrection(BaseModel):
    question_id:int
    correct:Literal['A','B','C','D']

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
        if not q or q['type']!='single_correct' or change.correct not in [o['label'] for o in q['options']]: raise HTTPException(422,'Choose an existing single-correct question and option.')
        before.append({'question_id':q['question_id'],'correct':[o['label'] for o in q['options'] if o['is_correct']]})
        for o in q['options']: o['is_correct']=o['label']==change.correct
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
        scan.result=offline_score(p,sh,scan.answers);scan.version+=1;offline+=1
    db.add(m.AuditLog(actor_id=user.id,action='teacher_key_corrected',entity='teacher_paper',entity_id=p.id,
        before={'keys':before,'version':b.version},after={'keys':[c.model_dump() for c in b.corrections],'version':p.version,'online_results':online,'offline_results':offline},reason=b.reason.strip()))
    db.commit();return {'paper':payload(p),'online_results':online,'offline_results':offline}
