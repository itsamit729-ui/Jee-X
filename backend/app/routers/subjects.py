"""Service 1: subject/chapter catalog — what a student can pick before starting
a subject-wise test. Read-only, needs no auth (mirrors the syllabus tables
being public per docs/database-schema.md section 2)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.question_catalog import candidate_query

router = APIRouter(prefix="/api/subjects", tags=["subjects"])

# What a JEE student can practise: other exams' questions and chapters are not counted or listed.
def _published_count(db):
    eligible = candidate_query(db).with_entities(models.Question.id)
    return func.count(case((models.Question.id.in_(eligible), models.Question.id)))


_jee_chapter = or_(models.Chapter.in_main.is_(True), models.Chapter.in_advanced.is_(True))


@router.get("", response_model=list[schemas.SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.Subject.code,
            models.Subject.name,
            func.count(func.distinct(models.Chapter.id)).label("chapter_count"),
            _published_count(db).label("question_count"),
        )
        .outerjoin(models.Chapter, and_(models.Chapter.subject_id == models.Subject.id, _jee_chapter))
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
            _published_count(db).label("question_count"),
        )
        .filter(models.Chapter.subject_id == subject.id, _jee_chapter)
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
