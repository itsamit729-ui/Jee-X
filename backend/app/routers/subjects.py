"""Service 1: subject/chapter catalog — what a student can pick before starting
a subject-wise test. Read-only, needs no auth (mirrors the syllabus tables
being public per docs/database-schema.md section 2)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, and_, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/subjects", tags=["subjects"])

_published_count = func.count(case((and_(models.Question.status == "published", or_(models.Question.exam.is_(None), models.Question.exam.in_(["jee_main", "jee_advanced"]))), models.Question.id)))


@router.get("", response_model=list[schemas.SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.Subject.code,
            models.Subject.name,
            func.count(func.distinct(models.Chapter.id)).label("chapter_count"),
            _published_count.label("question_count"),
        )
        .outerjoin(models.Chapter, models.Chapter.subject_id == models.Subject.id)
        .outerjoin(models.Subtopic, models.Subtopic.chapter_id == models.Chapter.id)
        .outerjoin(models.Question, models.Question.subtopic_id == models.Subtopic.id)
        .filter(models.Subject.code.in_(["PHY", "CHEM", "MATH"]))
        .group_by(models.Subject.id, models.Subject.code, models.Subject.name)
        .order_by(models.Subject.code)
        .all()
    )
    return [
        schemas.SubjectOut(code=r.code, name=r.name, chapter_count=r.chapter_count, published_question_count=r.question_count)
        for r in rows
    ]


@router.get("/{code}/chapters", response_model=list[schemas.ChapterOut])
def list_chapters(code: str, db: Session = Depends(get_db)):
    subject = db.query(models.Subject).filter(models.Subject.code == code.upper()).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Unknown subject.")

    rows = (
        db.query(
            models.Chapter.id,
            models.Chapter.name,
            models.Chapter.slug,
            models.Chapter.class_level,
            models.Chapter.position,
            _published_count.label("question_count"),
        )
        .filter(models.Chapter.subject_id == subject.id)
        .outerjoin(models.Subtopic, models.Subtopic.chapter_id == models.Chapter.id)
        .outerjoin(models.Question, models.Question.subtopic_id == models.Subtopic.id)
        .group_by(models.Chapter.id, models.Chapter.name, models.Chapter.slug, models.Chapter.class_level, models.Chapter.position)
        .order_by(models.Chapter.position, models.Chapter.name)
        .all()
    )
    return [
        schemas.ChapterOut(
            id=r.id, name=r.name, slug=r.slug, class_level=r.class_level, position=r.position,
            published_question_count=r.question_count,
        )
        for r in rows
    ]
