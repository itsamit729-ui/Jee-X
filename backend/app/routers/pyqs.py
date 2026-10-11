"""Exam-specific memory-based practice using the existing paper and grading contracts."""
from typing import Literal
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
        models.Question.source_type == 'pyq', models.Question.year.in_(YEARS),
        models.Question.type == 'single_correct')


@router.get('/{exam}')
def catalog(exam: Literal['bitsat', 'mht_cet'] = 'bitsat', db: Session = Depends(get_db)):
    rows = (eligible(db, exam).join(models.Subject, models.Subject.id == models.Chapter.subject_id)
            .with_entities(models.Question.year, models.Subject.code, func.count(models.Question.id))
            .group_by(models.Question.year, models.Subject.code).all())
    counts = {(year, code): count for year, code, count in rows}
    return {'exam': exam, 'label': 'BITSAT' if exam == 'bitsat' else 'MHT CET', 'source_label': 'Memory-based questions',
            'years': [{'year': year, 'subjects': [
                {'code': code, 'name': name, 'available': counts.get((year, code), 0)}
                for code, name in SUBJECTS.items() if exam == 'bitsat' or code in ('PHY', 'CHEM', 'MATH')]} for year in YEARS]}


class Start(BaseModel):
    year: Literal[2022, 2023, 2024, 2025, 2026]
    subject_code: Literal['PHY', 'CHEM', 'MATH', 'ENG', 'LR']
    count: int = Field(default=10, ge=1, le=30)


@router.post('/{exam}/practice', response_model=schemas.SubjectTestOut, status_code=201)
def start(body: Start, exam: Literal['bitsat', 'mht_cet'] = 'bitsat', user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    if exam == 'mht_cet' and body.subject_code not in ('PHY', 'CHEM', 'MATH'):
        raise HTTPException(422, 'MHT CET practice supports Physics, Chemistry and Mathematics.')
    correct = 3 if exam == 'bitsat' else (2 if body.subject_code == 'MATH' else 1)
    wrong = 1 if exam == 'bitsat' else 0
    ids = [row.id for row in eligible(db, exam)
           .join(models.Subject, models.Subject.id == models.Chapter.subject_id)
           .filter(models.Question.year == body.year, models.Subject.code == body.subject_code)
           .order_by(models.Question.ref).limit(body.count).all()]
    if not ids:
        raise HTTPException(404, 'Questions are not available for this selection yet.')
    rows = (db.query(models.Question).filter(models.Question.id.in_(ids))
            .options(selectinload(models.Question.options), selectinload(models.Question.assets),
                     selectinload(models.Question.passage).selectinload(models.Passage.assets)).all())
    by_id = {q.id: q for q in rows}
    questions = [by_id[qid] for qid in ids]
    title = f'{"BITSAT" if exam == "bitsat" else "MHT CET"} {body.year} · {SUBJECTS[body.subject_code]} · Memory-based practice'
    test = models.Test(title=title, kind='chapter', pattern=exam, duration_sec=len(ids)*90,
                       ranked=False, generated_for_user_id=user.id)
    db.add(test)
    db.flush()
    for position, q in enumerate(questions, 1):
        db.add(models.TestQuestion(test_id=test.id, question_id=q.id, position=position,
                                  marks_correct=correct, marks_wrong=wrong, partial_marking=False))
    attempt = models.TestAttempt(user_id=user.id, test_id=test.id, attempt_number=1, counts_for_rank=False)
    db.add(attempt)
    db.flush()
    result = schemas.SubjectTestOut(attempt_id=attempt.id, test_id=test.id, title=title,
        subject_code=body.subject_code, duration_sec=test.duration_sec,
        questions=[schemas.TestQuestionOut(question_id=q.id, ref=q.ref, type=q.type, stem=q.stem,
            passage=q.passage.content if q.passage else None,
            assets=[schemas.QuestionAssetOut(url=a.url, alt_text=a.alt_text)
                    for a in list(q.assets)+(list(q.passage.assets) if q.passage else [])],
            options=[schemas.TestOptionOut(id=o.id, label=o.label, content=o.content) for o in q.options],
            marks_correct=correct, marks_wrong=wrong) for q in questions])
    db.commit()
    return result
