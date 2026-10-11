"""Exam-specific memory-based practice using the existing paper and grading contracts."""
from typing import Literal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from app import models, schemas
from app.database import get_db
from app.deps import get_current_db_user
from app.services.question_catalog import candidate_query

router = APIRouter(prefix='/api/pyqs', tags=['pyqs'])
YEARS = (2026, 2025, 2024, 2023, 2022)
SUBJECTS = {'PHY': 'Physics', 'CHEM': 'Chemistry', 'MATH': 'Mathematics',
            'ENG': 'English Proficiency', 'LR': 'Logical Reasoning'}


def eligible(db, exam='bitsat'):
    return candidate_query(db, exam=exam, require_solution=exam != 'mht_cet').filter(
        models.Question.source_type == 'pyq', models.Question.year.isnot(None),
        models.Question.type == 'single_correct')


@router.get('/{exam}')
def catalog(exam: Literal['bitsat', 'mht_cet'] = 'bitsat', db: Session = Depends(get_db)):
    rows = (eligible(db, exam).join(models.Subject, models.Subject.id == models.Chapter.subject_id)
            .with_entities(models.Question.year, models.Subject.code, func.count(models.Question.id))
            .group_by(models.Question.year, models.Subject.code).all())
    counts = {(year, code): count for year, code, count in rows}
    paper_rows = (eligible(db, exam).join(models.Subject, models.Subject.id == models.Chapter.subject_id)
                  .filter(models.Question.shift.isnot(None), func.trim(models.Question.shift) != '',
                          models.Subject.code.in_(list(SUBJECTS) if exam == 'bitsat' else ['PHY', 'CHEM', 'MATH']))
                  .with_entities(models.Question.year, models.Question.shift, models.Subject.code,
                                 func.count(models.Question.id))
                  .group_by(models.Question.year, models.Question.shift, models.Subject.code).all())
    papers = {}
    for year, shift, code, count in paper_rows:
        paper = papers.setdefault((year, shift), {'shift': shift, 'available': 0, 'subjects': []})
        paper['available'] += count
        paper['subjects'].append({'code': code, 'name': SUBJECTS[code], 'available': count})
    def paper_order(item):
        try:
            return (datetime.strptime(item['shift'].split(',')[0].strip(), '%d %b %Y'), item['shift'])
        except ValueError:
            return (datetime.max, item['shift'])
    years = sorted(set(YEARS) | {year for year, _, _ in rows}, reverse=True)
    return {'exam': exam, 'label': 'BITSAT' if exam == 'bitsat' else 'MHT CET', 'source_label': 'Memory-based questions',
            'years': [{'year': year, 'papers': sorted([p for (y, _), p in papers.items() if y == year], key=paper_order), 'subjects': [
                {'code': code, 'name': name, 'available': counts.get((year, code), 0)}
                for code, name in SUBJECTS.items() if exam == 'bitsat' or code in ('PHY', 'CHEM', 'MATH')]} for year in years]}


class Start(BaseModel):
    year: int = Field(ge=1900, le=2100)
    subject_code: Literal['PHY', 'CHEM', 'MATH', 'ENG', 'LR']
    count: int = Field(default=10, ge=1, le=30)


@router.post('/{exam}/practice', response_model=schemas.SubjectTestOut, status_code=201)
def start(body: Start, exam: Literal['bitsat', 'mht_cet'] = 'bitsat', user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    if exam == 'mht_cet' and body.subject_code not in ('PHY', 'CHEM', 'MATH'):
        raise HTTPException(422, 'MHT CET practice supports Physics, Chemistry and Mathematics.')
    ids = [row.id for row in eligible(db, exam)
           .join(models.Subject, models.Subject.id == models.Chapter.subject_id)
           .filter(models.Question.year == body.year, models.Subject.code == body.subject_code)
           .order_by(models.Question.ref).limit(body.count).all()]
    if not ids:
        raise HTTPException(404, 'Questions are not available for this selection yet.')
    title = f'{"BITSAT" if exam == "bitsat" else "MHT CET"} {body.year} · {SUBJECTS[body.subject_code]} · Memory-based practice'
    return create_attempt(db, user, exam, ids, title, body.subject_code, len(ids)*90)


class PaperStart(BaseModel):
    year: int = Field(ge=1900, le=2100)
    shift: str = Field(min_length=1, max_length=50)


@router.post('/{exam}/papers', response_model=schemas.SubjectTestOut, status_code=201)
def start_paper(body: PaperStart, exam: Literal['bitsat', 'mht_cet'],
                user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    rows = (eligible(db, exam).join(models.Subject, models.Subject.id == models.Chapter.subject_id)
            .filter(models.Question.year == body.year, models.Question.shift == body.shift,
                    models.Subject.code.in_(list(SUBJECTS) if exam == 'bitsat' else ['PHY', 'CHEM', 'MATH']))
            .with_entities(models.Question.id, models.Question.ref, models.Subject.code).all())
    order = {code: i for i, code in enumerate(SUBJECTS)}
    ids = [row.id for row in sorted(rows, key=lambda row: (order[row.code], row.ref))]
    if not ids:
        raise HTTPException(404, 'No published questions are available for this paper.')
    title = f'{"BITSAT" if exam == "bitsat" else "MHT CET"} {body.year} · {body.shift} · Shift mock'
    # This is timed practice with available source questions, not a sectional exam simulation.
    return create_attempt(db, user, exam, ids, title, 'PCM' if exam == 'mht_cet' else 'ALL', 10800, is_mock=True)


def create_attempt(db, user, exam, ids, title, subject_code, duration_sec, is_mock=False):
    rows = (db.query(models.Question).filter(models.Question.id.in_(ids))
            .options(selectinload(models.Question.options), selectinload(models.Question.assets),
                     selectinload(models.Question.passage).selectinload(models.Passage.assets)).all())
    codes = dict(db.query(models.Question.id, models.Subject.code)
                 .join(models.Subtopic, models.Question.subtopic_id == models.Subtopic.id)
                 .join(models.Chapter, models.Subtopic.chapter_id == models.Chapter.id)
                 .join(models.Subject, models.Chapter.subject_id == models.Subject.id)
                 .filter(models.Question.id.in_(ids)).all())
    def marks(q):
        return 3 if exam == 'bitsat' else (2 if codes[q.id] == 'MATH' else 1)
    wrong = 1 if exam == 'bitsat' else 0
    by_id = {q.id: q for q in rows}
    questions = [by_id[qid] for qid in ids]
    test = models.Test(title=title, kind='mock' if is_mock else 'chapter', pattern=exam, duration_sec=duration_sec,
                       ranked=False, generated_for_user_id=user.id)
    db.add(test)
    db.flush()
    for position, q in enumerate(questions, 1):
        db.add(models.TestQuestion(test_id=test.id, question_id=q.id, position=position,
                                  marks_correct=marks(q), marks_wrong=wrong, partial_marking=False))
    attempt = models.TestAttempt(user_id=user.id, test_id=test.id, attempt_number=1, counts_for_rank=False)
    db.add(attempt)
    db.flush()
    result = schemas.SubjectTestOut(is_mock=is_mock, attempt_id=attempt.id, test_id=test.id, title=title,
        subject_code=subject_code, duration_sec=test.duration_sec,
        questions=[schemas.TestQuestionOut(subject_code=codes[q.id], question_id=q.id, ref=q.ref, type=q.type, stem=q.stem,
            passage=q.passage.content if q.passage else None,
            assets=[schemas.QuestionAssetOut(url=a.url, alt_text=a.alt_text)
                    for a in list(q.assets)+(list(q.passage.assets) if q.passage else [])],
            options=[schemas.TestOptionOut(id=o.id, label=o.label, content=o.content) for o in q.options],
            marks_correct=marks(q), marks_wrong=wrong) for q in questions])
    db.commit()
    return result
