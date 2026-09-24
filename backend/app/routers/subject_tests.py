"""Service 2: build a subject-wise test — pick a subject (and optionally one
chapter), pull a random set of published questions, create the `tests` /
`test_questions` / `test_attempts` rows, and hand the student the question
paper with no answers in it (rule 7 in docs/database-schema.md section 13)."""

import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.deps import get_current_db_user

router = APIRouter(prefix="/api/subject-tests", tags=["subject-tests"])

SECONDS_PER_QUESTION = 90


@router.post("", response_model=schemas.SubjectTestOut, status_code=201)
def create_subject_test(
    body: schemas.SubjectTestCreate,
    user: models.User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
):
    subject = db.query(models.Subject).filter(models.Subject.code == body.subject_code).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Unknown subject.")

    query = (
        db.query(models.Question)
        .join(models.Subtopic, models.Question.subtopic_id == models.Subtopic.id)
        .join(models.Chapter, models.Subtopic.chapter_id == models.Chapter.id)
        .options(joinedload(models.Question.options))
        .filter(models.Chapter.subject_id == subject.id, models.Question.status == "published")
    )
    if body.chapter_id is not None:
        query = query.filter(models.Chapter.id == body.chapter_id)

    pool = query.all()
    if not pool:
        raise HTTPException(
            status_code=404,
            detail="No published questions available for this subject/chapter yet.",
        )

    picked = random.sample(pool, k=min(body.count, len(pool)))

    test = models.Test(
        title=f"{subject.name} practice test",
        kind="chapter",
        pattern="jee_main",
        duration_sec=len(picked) * SECONDS_PER_QUESTION,
        ranked=False,
        generated_for_user_id=user.id,
    )
    db.add(test)
    db.flush()

    for position, question in enumerate(picked, start=1):
        db.add(
            models.TestQuestion(
                test_id=test.id,
                question_id=question.id,
                position=position,
                marks_correct=4,
                marks_wrong=0 if question.type == "numerical" else 1,
                partial_marking=False,
            )
        )

    attempt = models.TestAttempt(
        user_id=user.id,
        test_id=test.id,
        attempt_number=1,
        counts_for_rank=False,
    )
    db.add(attempt)
    db.commit()
    db.refresh(test)
    db.refresh(attempt)

    questions_out = [
        schemas.TestQuestionOut(
            question_id=q.id,
            ref=q.ref,
            type=q.type,
            stem=q.stem,
            assets=[schemas.QuestionAssetOut(url=a.url, alt_text=a.alt_text)
                    for a in list(q.assets) + (list(q.passage.assets) if q.passage else [])],
            passage=q.passage.content if q.passage else None,
            options=[schemas.TestOptionOut(id=o.id, label=o.label, content=o.content) for o in q.options],
            marks_correct=4,
            marks_wrong=0 if q.type == "numerical" else 1,
        )
        for q in picked
    ]

    return schemas.SubjectTestOut(
        attempt_id=attempt.id,
        test_id=test.id,
        title=test.title,
        subject_code=subject.code,
        duration_sec=test.duration_sec,
        questions=questions_out,
    )

