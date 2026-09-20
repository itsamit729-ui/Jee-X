"""Service 6: a personalized daily question that feeds the Edge Coins streak.

One question per student per IST calendar day, targeting their weakest attempted subtopic
(student_subtopic_stats.mastery ascending) so it's a light, adaptive nudge rather than a random
pick. Grading reuses the existing subject-test grader unchanged
(POST /api/subject-tests/attempts/{attempt_id}/submit) — a daily question is built as the exact
same Test(kind='daily')/TestQuestion/TestAttempt shape create_subject_test() below builds for a
one-question test, so that handler grades it generically. subject_test_attempts.py calls
rewards.update_streak_and_award() when test.kind == 'daily' after grading."""

import random
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.deps import get_current_db_user
from app.services import rewards

router = APIRouter(prefix="/api/daily-question", tags=["daily-question"])

DAILY_DURATION_SEC = 180
CALENDAR_DAYS = 182


def _previously_assigned_question_ids(db: Session, user_id: int) -> set[int]:
    return {
        row[0]
        for row in db.query(models.DailyQuestionAssignment.question_id).filter(
            models.DailyQuestionAssignment.user_id == user_id
        )
    }


def _pick_question(db: Session, user: models.User) -> models.Question | None:
    seen = _previously_assigned_question_ids(db, user.id)

    weak_subtopic_ids = [
        row[0]
        for row in db.query(models.StudentSubtopicStats.subtopic_id)
        .filter(models.StudentSubtopicStats.user_id == user.id, models.StudentSubtopicStats.attempted > 0)
        .order_by(models.StudentSubtopicStats.mastery.asc())
        .all()
    ]
    for subtopic_id in weak_subtopic_ids:
        query = db.query(models.Question).filter(
            models.Question.subtopic_id == subtopic_id, models.Question.status == "published"
        )
        if seen:
            query = query.filter(models.Question.id.notin_(seen))
        candidate = query.first()
        if candidate:
            return candidate

    # No stats yet, or every question in every weak subtopic has already been assigned —
    # fall back to any unseen published question.
    fallback = db.query(models.Question).filter(models.Question.status == "published")
    if seen:
        fallback = fallback.filter(models.Question.id.notin_(seen))
    return fallback.first()


def _create_assignment(db: Session, user: models.User, today) -> models.DailyQuestionAssignment:
    question = _pick_question(db, user)
    if question is None:
        raise HTTPException(status_code=404, detail="No more daily questions available right now.")

    test = models.Test(
        title="Daily question",
        kind="daily",
        pattern="jee_main",
        duration_sec=DAILY_DURATION_SEC,
        ranked=False,
        generated_for_user_id=user.id,
    )
    db.add(test)
    db.flush()
    db.add(
        models.TestQuestion(
            test_id=test.id,
            question_id=question.id,
            position=1,
            marks_correct=4,
            marks_wrong=0 if question.type == "numerical" else 1,
            partial_marking=False,
        )
    )
    attempt = models.TestAttempt(user_id=user.id, test_id=test.id, attempt_number=1, counts_for_rank=False)
    db.add(attempt)

    assignment = models.DailyQuestionAssignment(
        user_id=user.id, question_id=question.id, assigned_date=today, test_id=test.id
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("", response_model=schemas.DailyQuestionOut)
def get_today(user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    rewards.lock_wallet(db, user.id)
    today = rewards.today_ist()
    assignment = (
        db.query(models.DailyQuestionAssignment)
        .filter(models.DailyQuestionAssignment.user_id == user.id, models.DailyQuestionAssignment.assigned_date == today)
        .with_for_update().populate_existing()
        .first()
    )
    if assignment is None:
        assignment = _create_assignment(db, user, today)

    question = (
        db.query(models.Question)
        .options(joinedload(models.Question.options))
        .filter(models.Question.id == assignment.question_id)
        .first()
    )
    attempt = (
        db.query(models.TestAttempt)
        .filter(models.TestAttempt.test_id == assignment.test_id, models.TestAttempt.user_id == user.id)
        .with_for_update().populate_existing()
        .first()
    )

    profile = user.student_profile

    return schemas.DailyQuestionOut(
        attempt_id=attempt.id,
        already_answered=attempt.submitted_at is not None,
        question=schemas.TestQuestionOut(
            question_id=question.id,
            ref=question.ref,
            type=question.type,
            stem=question.stem,
            passage=question.passage.content if question.passage else None,
            options=[schemas.TestOptionOut(id=o.id, label=o.label, content=o.content) for o in question.options],
            marks_correct=4,
            marks_wrong=0 if question.type == "numerical" else 1,
        ),
        current_streak=profile.current_streak or 0,
        longest_streak=profile.longest_streak or 0,
    )


@router.get("/calendar", response_model=schemas.StreakCalendarOut)
def get_calendar(user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    since = rewards.today_ist() - timedelta(days=CALENDAR_DAYS - 1)
    rows = (
        db.query(models.DailyQuestionAssignment.assigned_date)
        .join(models.TestAttempt, models.TestAttempt.test_id == models.DailyQuestionAssignment.test_id)
        .filter(
            models.DailyQuestionAssignment.user_id == user.id,
            models.DailyQuestionAssignment.assigned_date >= since,
            models.TestAttempt.submitted_at.isnot(None),
        )
        .all()
    )
    profile = user.student_profile
    return schemas.StreakCalendarOut(
        activity_dates=sorted(r[0].isoformat() for r in rows),
        current_streak=profile.current_streak or 0,
        longest_streak=profile.longest_streak or 0,
    )
