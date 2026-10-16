"""Conservative, idempotent publication of validated pipeline exports."""
import re
from copy import deepcopy
from sqlalchemy import func, insert
from sqlalchemy.orm import selectinload, joinedload
from app import models
from app.importer import _content_hash


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
        joinedload(models.Question.subtopic).joinedload(models.Subtopic.chapter).joinedload(models.Chapter.subject))
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
    existing=rows_for(db,questions,lock)
    duplicates=other_stems(db,[q for q in questions if q['ref'] not in existing]);decisions=[]
    for data in questions:
        row=existing.get(data['ref']);action,reason=classify(row,data)
        if row is None and (norm(data['stem']),data['shift']) in duplicates:
            action,reason='conflict','Possible duplicate under reference '+duplicates[(norm(data['stem']),data['shift'])]
        decisions.append((data,row,action,reason))
    return decisions


def plan(db,data):
    counts={key:0 for key in ('add','update','unchanged','skip','conflict')};issues=[]
    questions=data['questions']
    for q,_,action,reason in inspect_batch(db,questions):
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


def taxonomy_for(db,questions):
    """Resolve each chapter once per batch, not once per question."""
    by_key={}
    for q in questions:
        key=(q['subject'],q['chapter_slug'])
        if key not in by_key:by_key[key]=taxonomy(db,q)
    return by_key


def publish_batch(db,data,offset=0,limit=25,commit=True):
    questions=data['questions'][offset:offset+limit]
    counts={key:0 for key in ('added','updated','unchanged','skipped','conflicts')};issues=[]
    try:
        decisions=inspect_batch(db,questions,lock=True)
        changed=[decision for decision in decisions if decision[2] in ('add','update')]
        for source,row,action,reason in decisions:
            if action in ('add','update'):continue
            counts[{'unchanged':'unchanged','skip':'skipped','conflict':'conflicts'}[action]]+=1
            if reason:issues.append({'ref':source['ref'],'reason':reason})
        if changed:
            run=models.ImportRun(file_path=f'datasets/jee-main-{data["year"]}/questions.jsonl',file_hash=data['digest'])
            db.add(run);db.flush()
            additions=[q for q,row,action,reason in changed if action=='add']
            topics=taxonomy_for(db,additions)
            new_rows=[];prepared_rows=[]
            for source,row,action,reason in changed:
                prepared=deepcopy(source)
                if action=='update':
                    prepared.update(subtopic=row.subtopic.slug,chapter_slug=row.subtopic.chapter.slug,
                        chapter_name=row.subtopic.chapter.name,class_level=row.subtopic.chapter.class_level,
                        difficulty=row.difficulty,expected_time_sec=row.expected_time_sec)
                    if row.solution:prepared['solution']=row.solution
                    if row.assets:
                        asset=row.assets[0];prepared['image']={'url':asset.url,'alt':asset.alt_text or ''}
                    row.solution=prepared['solution'];row.status='published';row.version+=1
                    if prepared['answer']:
                        row.answer_min=prepared['answer']['min'];row.answer_max=prepared['answer']['max']
                    row.content_hash=_content_hash(prepared)
                    # Only missing keys/images need writes; keep existing option IDs.
                    if row.type=='single_correct':
                        correct={o['label'] for o in prepared['options'] if o['is_correct']}
                        for option in row.options:option.is_correct=option.label in correct
                    if not row.assets and prepared['image']:
                        db.add(models.Asset(question_id=row.id,url=prepared['image']['url'],alt_text=prepared['image'].get('alt','')))
                    counts['updated']+=1
                else:
                    answer=prepared['answer'] or {}
                    new_rows.append(dict(ref=prepared['ref'],subtopic_id=topics[(prepared['subject'],prepared['chapter_slug'])].id,
                        type=prepared['type'],stem=prepared['stem'],solution=prepared['solution'],difficulty=prepared['difficulty'],
                        expected_time_sec=prepared['expected_time_sec'],source_type='pyq',exam='jee_main',year=prepared['year'],
                        shift=prepared['shift'],status='published',version=1,content_hash=_content_hash(prepared),
                        answer_min=answer.get('min'),answer_max=answer.get('max')))
                    counts['added']+=1
                prepared_rows.append((prepared,row))
            db.flush()
            if new_rows:db.execute(insert(models.Question.__table__),new_rows)
            ids=dict(db.query(models.Question.ref,models.Question.id).filter(models.Question.ref.in_([q['ref'] for q in new_rows])).all()) if new_rows else {}
            options=[];assets=[];revisions=[]
            for prepared,row in prepared_rows:
                identity=row.id if row is not None else ids[prepared['ref']]
                version=row.version if row is not None else 1
                if row is None:
                    options.extend(dict(question_id=identity,label=o['label'],content=o['content'],is_correct=o['is_correct'],position=i)
                                   for i,o in enumerate(prepared['options'],1))
                    if prepared['image']:
                        assets.append(dict(question_id=identity,url=prepared['image']['url'],alt_text=prepared['image'].get('alt','')))
                revisions.append(dict(question_id=identity,version=version,content=prepared,import_run_id=run.id,
                    change_note='pipeline-question-import: checked key; '+('source solution checked' if prepared['solution_verified'] else 'answer key only')))
            if options:db.execute(insert(models.QuestionOption.__table__),options)
            if assets:db.execute(insert(models.Asset.__table__),assets)
            db.execute(insert(models.QuestionRevision.__table__),revisions)
            run.added=counts['added'];run.updated=counts['updated'];run.errors=issues or None
        db.flush()
        if commit:db.commit()
    except Exception:
        db.rollback();raise
    next_offset=offset+len(questions)
    return {**counts,'issues':issues,'next_offset':next_offset,'total':len(data['questions']),'finished':next_offset>=len(data['questions'])}


COUNTERS=('added','updated','unchanged','skipped','conflicts')


def progress(db,data):
    row=db.get(models.QuestionImportProgress,data['digest'])
    total=len(data['questions'])
    return {'digest':data['digest'],'year':data['year'],'offset':row.offset if row else 0,'total':total,
        'finished':bool(row and row.offset>=total),
        **{key:getattr(row,key) if row else 0 for key in COUNTERS}}


def publish_next(db,data,offset=0,limit=25):
    """Cursor and question writes commit together. Replayed requests are read-only."""
    try:
        row=db.query(models.QuestionImportProgress).filter_by(digest=data['digest']).with_for_update().first()
        if row is None:
            if offset!=0:raise ValueError('No saved cursor. Read progress and start at offset zero.')
            row=models.QuestionImportProgress(digest=data['digest'],year=data['year'],offset=0,total=len(data['questions']),
                **{key:0 for key in COUNTERS})
            db.add(row);db.flush()
        if offset>row.offset:raise ValueError('Import cursor changed. Read progress before continuing.')
        if offset<row.offset or row.offset>=row.total:
            state=progress(db,data);db.rollback()
            return {**{key:0 for key in COUNTERS},'issues':[],'next_offset':state['offset'],
                'total':state['total'],'finished':state['finished'],'already_processed':True,'progress':state}
        result=publish_batch(db,data,offset,limit,commit=False)
        row.offset=result['next_offset']
        for key in COUNTERS:setattr(row,key,getattr(row,key)+result[key])
        db.flush();state=progress(db,data);db.commit()
        return {**result,'progress':state,'already_processed':False}
    except Exception:
        db.rollback();raise
