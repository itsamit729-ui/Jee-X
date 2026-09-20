"""Service 3: grade a subject-wise test attempt. The browser sends the
choices the student made; this is the only code that decides correctness
(the "Grader" component in docs/database-schema.md section 1). Writes
question_responses / response_options, the attempt's cached summary, and
bumps each answered subtopic's mastery in the learning profile."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.deps import get_current_db_user
from app.services import rewards

router = APIRouter(prefix="/api/subject-tests", tags=["subject-tests"])


def _grade_one(question: models.Question, answer: schemas.SubjectTestAnswerIn) -> tuple[str, set[int]]:
    """Returns (outcome, correct_option_ids)."""
    correct_option_ids = {o.id for o in question.options if o.is_correct}

    if question.type == "numerical":
        if answer.numeric_answer is None:
            return "skipped", correct_option_ids
        in_range = (question.answer_min or 0) <= answer.numeric_answer <= (question.answer_max or 0)
        return ("correct" if in_range else "wrong"), correct_option_ids

    chosen = set(answer.option_ids)
    if not chosen:
        return "skipped", correct_option_ids
    return ("correct" if chosen == correct_option_ids else "wrong"), correct_option_ids


@router.post("/attempts/{attempt_id}/submit", response_model=schemas.SubjectTestResultOut)
def submit_subject_test(
    attempt_id: int,
    body: schemas.SubjectTestSubmitIn,
    user: models.User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
):
    rewards.lock_wallet(db, user.id)
    attempt = (
        db.query(models.TestAttempt)
        .filter(models.TestAttempt.id == attempt_id, models.TestAttempt.user_id == user.id)
        .with_for_update().populate_existing()
        .first()
    )
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if attempt.submitted_at is not None:
        raise HTTPException(status_code=409, detail="This attempt was already submitted.")

    test_questions = {
        tq.question_id: tq
        for tq in db.query(models.TestQuestion).filter(models.TestQuestion.test_id == attempt.test_id).all()
    }
    if not test_questions:
        raise HTTPException(status_code=400, detail="This test has no questions.")

    answers_by_question = {a.question_id: a for a in body.answers}
    previously_correct_count = rewards.total_correct_answers(db, user.id)

    results: list[schemas.QuestionResultOut] = []
    total_marks = 0
    correct_count = 0
    total_time = 0
    subtopic_touch: dict[int, bool] = {}

    for question_id, tq in test_questions.items():
        question = (
            db.query(models.Question)
            .options(joinedload(models.Question.options))
            .filter(models.Question.id == question_id)
            .first()
        )
        answer = answers_by_question.get(question_id, schemas.SubjectTestAnswerIn(question_id=question_id))

        outcome, correct_option_ids = _grade_one(question, answer)
        marks_awarded = tq.marks_correct if outcome == "correct" else (-tq.marks_wrong if outcome == "wrong" else 0)

        latest_revision = (
            db.query(models.QuestionRevision)
            .filter(models.QuestionRevision.question_id == question.id)
            .order_by(models.QuestionRevision.version.desc())
            .first()
        )
        question_version = latest_revision.version if latest_revision else question.version

        response = models.QuestionResponse(
            attempt_id=attempt.id,
            user_id=user.id,
            question_id=question.id,
            question_version=question_version,
            numeric_answer=answer.numeric_answer,
            outcome=outcome,
            marks_awarded=marks_awarded,
            time_taken_sec=answer.time_taken_sec,
        )
        db.add(response)
        db.flush()

        if question.type != "numerical":
            for option_id in answer.option_ids:
                db.add(models.ResponseOption(response_id=response.id, option_id=option_id))

        total_marks += marks_awarded
        total_time += answer.time_taken_sec
        if outcome == "correct":
            correct_count += 1

        stats = (
            db.query(models.StudentSubtopicStats)
            .filter(
                models.StudentSubtopicStats.user_id == user.id,
                models.StudentSubtopicStats.subtopic_id == question.subtopic_id,
            )
            .with_for_update().populate_existing()
            .first()
        )
        if not stats:
            stats = models.StudentSubtopicStats(user_id=user.id, subtopic_id=question.subtopic_id, attempted=0, correct=0)
            db.add(stats)
        if question.subtopic_id not in subtopic_touch:
            stats.attempted += 1
            if outcome == "correct":
                stats.correct += 1
            stats.mastery = stats.correct / stats.attempted if stats.attempted else 0.5
            stats.last_attempted_at = datetime.now(timezone.utc)
            subtopic_touch[question.subtopic_id] = True

        results.append(
            schemas.QuestionResultOut(
                question_id=question.id,
                ref=question.ref,
                outcome=outcome,
                marks_awarded=marks_awarded,
                correct_option_ids=sorted(correct_option_ids),
                solution=question.solution,
            )
        )

    total_questions = len(test_questions)
    attempted = sum(1 for r in results if r.outcome != "skipped")
    subject_code = (
        db.query(models.Subject.code)
        .join(models.Chapter, models.Chapter.subject_id == models.Subject.id)
        .join(models.Subtopic, models.Subtopic.chapter_id == models.Chapter.id)
        .join(models.Question, models.Question.subtopic_id == models.Subtopic.id)
        .filter(models.Question.id == next(iter(test_questions)))
        .scalar()
    )
    subject_breakdown = {subject_code: {"correct": correct_count, "total": total_questions}}

    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.score = total_marks
    attempt.total_questions = total_questions
    attempt.accuracy = round((correct_count / attempted) * 100, 2) if attempted else 0.0
    attempt.avg_time_seconds = round(total_time / total_questions, 2) if total_questions else 0.0
    attempt.subject_breakdown = subject_breakdown

    coins_earned = rewards.check_and_award_milestones(
        db, user, previously_correct_count, previously_correct_count + correct_count
    )
    current_streak = None
    if attempt.test.kind == "daily":
        coins_earned += rewards.update_streak_and_award(db, user)
        current_streak = user.student_profile.current_streak

    db.commit()

    return schemas.SubjectTestResultOut(
        attempt_id=attempt.id,
        score=attempt.score,
        total_questions=attempt.total_questions,
        accuracy=attempt.accuracy,
        avg_time_seconds=attempt.avg_time_seconds,
        subject_breakdown=attempt.subject_breakdown,
        questions=results,
        coins_earned=coins_earned,
        current_streak=current_streak,
    )
