"""Conservative, idempotent publication of validated pipeline exports."""
import re
from copy import deepcopy
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app import models
from app.importer import _content_hash, _upsert_options, _upsert_question_assets


def norm(text):return re.sub(r'\s+',' ',text or '').strip()


def classify(row,data):
    if row is None:return 'add',None
    if row.status=='retired':return 'skip','Retired questions stay retired'
    if row.status not in ('draft','reviewed','published'):return 'conflict','Unknown stored question status'
    if (row.type,row.exam,row.year,row.shift,norm(row.stem))!=(data['type'],data['exam'],data['year'],data['shift'],norm(data['stem'])):
        return 'conflict','Stored question text or paper metadata differs; existing content preserved'
    if row.subtopic.chapter.subject.code!=data['subject']:return 'conflict','Stored subject differs; existing taxonomy preserved'
    if len(row.assets)>1:return 'conflict','Stored multi-figure question needs review'
    if row.passage_id:return 'conflict','Stored passage must be reviewed before replacing question data'
    actual=sorted(row.options,key=lambda o:o.position)
    if row.type=='single_correct':
        if [(o.label,norm(o.content)) for o in actual]!=[(o['label'],norm(o['content'])) for o in data['options']]:
            return 'conflict','Stored options differ; existing content preserved'
        current=[o.label for o in actual if o.is_correct]
        incoming=[o['label'] for o in data['options'] if o['is_correct']]
        if current and current!=incoming:return 'conflict','Stored answer key disagrees; not overwritten'
        key_missing=not current
    else:
        if actual:return 'conflict','Stored numerical question has unexpected options'
        if row.answer_min is not None and (row.answer_min,row.answer_max)!=(data['answer']['min'],data['answer']['max']):
            return 'conflict','Stored numerical answer disagrees; not overwritten'
        key_missing=row.answer_min is None or row.answer_max is None
    needs_update=(row.status!='published' or key_missing or (not row.solution and data['solution'])
                  or (not row.assets and data['image']))
    return ('update' if needs_update else 'unchanged'),None


def rows_for(db,questions,lock=False):
    refs=[q['ref'] for q in questions]
    query=db.query(models.Question).filter(models.Question.ref.in_(refs)).options(
        selectinload(models.Question.options),selectinload(models.Question.assets),
        selectinload(models.Question.subtopic).selectinload(models.Subtopic.chapter).selectinload(models.Chapter.subject))
    if lock:query=query.with_for_update()
    return {q.ref:q for q in query}


def other_stems(db,questions):
    if not questions:return {}
    # A possible duplicate under another reference is held, never auto-inserted.
    refs=[q['ref'] for q in questions];stems=[q['stem'] for q in questions]
    rows=db.query(models.Question.ref,models.Question.stem,models.Question.shift).filter(
        models.Question.exam=='jee_main',models.Question.year==questions[0]['year'],
        models.Question.stem.in_(stems),~models.Question.ref.in_(refs)).all()
    return {(norm(stem),shift):ref for ref,stem,shift in rows}


def inspect_batch(db,questions,lock=False):
    existing=rows_for(db,questions,lock);duplicates=other_stems(db,questions);decisions=[]
    for data in questions:
        row=existing.get(data['ref']);action,reason=classify(row,data)
        if row is None and (norm(data['stem']),data['shift']) in duplicates:
            action,reason='conflict','Possible duplicate under reference '+duplicates[(norm(data['stem']),data['shift'])]
        decisions.append((data,row,action,reason))
    return decisions


def plan(db,data):
    counts={key:0 for key in ('add','update','unchanged','skip','conflict')};issues=[]
    questions=data['questions']
    for offset in range(0,len(questions),100):
        for q,_,action,reason in inspect_batch(db,questions[offset:offset+100]):
            counts[action]+=1
            if reason:issues.append({'ref':q['ref'],'reason':reason})
    return {'counts':counts,'issues':issues}


def taxonomy(db,data):
    subject=db.query(models.Subject).filter_by(code=data['subject']).first()
    if not subject:
        names={'PHY':'Physics','CHEM':'Chemistry','MATH':'Mathematics'}
        subject=models.Subject(code=data['subject'],name=names[data['subject']]);db.add(subject);db.flush()
    chapter=db.query(models.Chapter).filter_by(subject_id=subject.id,slug=data['chapter_slug']).first()
    if not chapter:
        position=db.query(func.max(models.Chapter.position)).filter_by(subject_id=subject.id).scalar() or 0
        chapter=models.Chapter(subject_id=subject.id,slug=data['chapter_slug'],name=data['chapter_name'],
            class_level=data['class_level'],in_main=True,in_advanced=True,position=position+1)
        db.add(chapter);db.flush()
    subtopic=db.query(models.Subtopic).filter_by(chapter_id=chapter.id,slug='general').first()
    if not subtopic:
        position=db.query(func.max(models.Subtopic.position)).filter_by(chapter_id=chapter.id).scalar() or 0
        subtopic=models.Subtopic(chapter_id=chapter.id,slug='general',name='General',position=position+1)
        db.add(subtopic);db.flush()
    return subtopic


def publish_batch(db,data,offset=0,limit=25):
    questions=data['questions'][offset:offset+limit]
    decisions=inspect_batch(db,questions,lock=True)
    counts={key:0 for key in ('added','updated','unchanged','skipped','conflicts')};issues=[]
    run=None
    try:
        for source,row,action,reason in decisions:
            if action not in ('add','update'):
                counts[{'unchanged':'unchanged','skip':'skipped','conflict':'conflicts'}[action]]+=1
                if reason:issues.append({'ref':source['ref'],'reason':reason})
                continue
            if run is None:
                run=models.ImportRun(file_path=f'datasets/jee-main-{data["year"]}/questions.jsonl',file_hash=data['digest'])
                db.add(run);db.flush()
            prepared=deepcopy(source)
            if row is None:
                subtopic=taxonomy(db,prepared)
                row=models.Question(ref=prepared['ref'],subtopic_id=subtopic.id,type=prepared['type'],stem=prepared['stem'],
                    solution='',difficulty=prepared['difficulty'],expected_time_sec=prepared['expected_time_sec'],
                    source_type='pyq',exam='jee_main',year=prepared['year'],shift=prepared['shift'],status='draft',version=0)
                db.add(row)
            if action=='update':
                prepared.update(subtopic=row.subtopic.slug,chapter_slug=row.subtopic.chapter.slug,
                    chapter_name=row.subtopic.chapter.name,class_level=row.subtopic.chapter.class_level,
                    difficulty=row.difficulty,expected_time_sec=row.expected_time_sec)
            # Keep existing editorial work, taxonomy, difficulty and replacements.
            if row.solution:prepared['solution']=row.solution
            if row.assets:
                asset=row.assets[0];prepared['image']={'url':asset.url,'alt':asset.alt_text or ''}
            row.solution=prepared['solution'];row.status='published'
            row.version=(row.version or 0)+1
            if prepared['answer']:
                row.answer_min=prepared['answer']['min'];row.answer_max=prepared['answer']['max']
            row.content_hash=_content_hash(prepared)
            db.flush()
            _upsert_options(db,row,prepared['options'])
            _upsert_question_assets(db,row,prepared['image'])
            db.flush()
            db.add(models.QuestionRevision(question_id=row.id,version=row.version,content=prepared,import_run_id=run.id,
                change_note='pipeline-question-import: checked key; '+('source solution checked' if source['solution_verified'] else 'answer key only')))
            counts['added' if action=='add' else 'updated']+=1
        if run:
            run.added=counts['added'];run.updated=counts['updated'];run.errors=issues or None
        db.commit()
    except Exception:
        db.rollback();raise
    next_offset=offset+len(questions)
    return {**counts,'issues':issues,'next_offset':next_offset,'total':len(data['questions']),'finished':next_offset>=len(data['questions'])}
