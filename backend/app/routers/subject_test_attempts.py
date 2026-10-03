"""Service 3: grade a subject-wise test attempt. The browser sends the
choices the student made; this is the only code that decides correctness
(the "Grader" component in docs/database-schema.md section 1). Writes
question_responses / response_options, the attempt's cached summary, and
bumps each answered subtopic's mastery in the learning profile."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.deps import get_current_db_user
from app.services import rewards

router = APIRouter(prefix="/api/subject-tests", tags=["subject-tests"])


from app.services.grading import _grade_one


@router.post("/attempts/{attempt_id}/submit", response_model=schemas.SubjectTestResultOut)
def submit_subject_test(
    attempt_id: int,
    body: schemas.SubjectTestSubmitIn,
    user: models.User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
):
    if db.query(models.TeachingAssignment.id).join(models.TestAttempt, models.TestAttempt.test_id == models.TeachingAssignment.test_id).filter(
        models.TestAttempt.id == attempt_id, models.TestAttempt.user_id == user.id).first():
        raise HTTPException(403, "Use the classroom assignment to submit this test.")
    wallet = rewards.lock_wallet(db, user.id)
    attempt = (
        db.query(models.TestAttempt)
        .filter(models.TestAttempt.id == attempt_id, models.TestAttempt.user_id == user.id)
        .with_for_update().populate_existing()
        .first()
    )
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if db.query(models.TeachingAssignment.id).filter_by(test_id=attempt.test_id).first():
        raise HTTPException(403, "Use the classroom assignment to submit this test.")
    if attempt.submitted_at is not None:
        raise HTTPException(status_code=409, detail="This attempt was already submitted.")

    # Fetch the paper, answer keys, revision and subject in one round trip.
    latest_revision = (select(func.max(models.QuestionRevision.version))
        .where(models.QuestionRevision.question_id == models.Question.id)
        .correlate(models.Question).scalar_subquery())
    paper = (db.query(models.TestQuestion, models.Question, models.Subject.code,
                      latest_revision, models.Test.kind)
        .join(models.Question, models.Question.id == models.TestQuestion.question_id)
        .join(models.Subtopic, models.Subtopic.id == models.Question.subtopic_id)
        .join(models.Chapter, models.Chapter.id == models.Subtopic.chapter_id)
        .join(models.Subject, models.Subject.id == models.Chapter.subject_id)
        .join(models.Test, models.Test.id == models.TestQuestion.test_id)
        .options(joinedload(models.Question.options))
        .filter(models.TestQuestion.test_id == attempt.test_id).all())
    if not paper:
        raise HTTPException(status_code=400, detail="This test has no questions.")
    test_questions = {tq.question_id: tq for tq, _, _, _, _ in paper}
    questions = {q.id: q for _, q, _, _, _ in paper}
    revisions = {q.id: revision for _, q, _, revision, _ in paper}
    question_subjects = {q.id: code for _, q, code, _, _ in paper}
    test_kind = paper[0][4]
    answers_by_question = {a.question_id: a for a in body.answers}

    results: list[schemas.QuestionResultOut] = []
    total_marks = 0
    correct_count = 0
    total_time = 0
    subtopic_touch: dict[int, bool] = {}
    response_rows = []
    selected_options = {}

    stats_by_topic = {s.subtopic_id: s for s in db.query(models.StudentSubtopicStats)
        .filter(models.StudentSubtopicStats.user_id == user.id,
                models.StudentSubtopicStats.subtopic_id.in_({q.subtopic_id for q in questions.values()}))
        .with_for_update().populate_existing().all()}
    for question_id, tq in test_questions.items():
        question = questions[question_id]
        answer = answers_by_question.get(question_id, schemas.SubjectTestAnswerIn(question_id=question_id))

        outcome, correct_option_ids = _grade_one(question, answer)
        marks_awarded = tq.marks_correct if outcome == "correct" else (-tq.marks_wrong if outcome == "wrong" else 0)

        question_version = revisions.get(question.id) or question.version

        response_rows.append(dict(
            attempt_id=attempt.id,
            user_id=user.id,
            question_id=question.id,
            question_version=question_version,
            numeric_answer=answer.numeric_answer,
            outcome=outcome,
            marks_awarded=marks_awarded,
            time_taken_sec=answer.time_taken_sec,
        ))

        if question.type != "numerical":
            valid_options = {o.id for o in question.options}
            if not set(answer.option_ids) <= valid_options:
                raise HTTPException(422, "An answer contains an option from another question.")
            selected_options[question.id] = set(answer.option_ids)

        total_marks += marks_awarded
        total_time += answer.time_taken_sec
        if outcome == "correct":
            correct_count += 1

        stats = stats_by_topic.get(question.subtopic_id)
        if not stats:
            stats = models.StudentSubtopicStats(user_id=user.id, subtopic_id=question.subtopic_id, attempted=0, correct=0)
            db.add(stats)
            stats_by_topic[question.subtopic_id] = stats
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

    # Core executemany avoids one INSERT/lastrowid round trip per question on MySQL.
    # Remain inside the same transaction and wallet/attempt locks as the summary.
    # Incorrect/skipped submissions cannot cross a correct-answer milestone.
    previously_correct_count = rewards.total_correct_answers(db, user.id) if correct_count else 0
    saved = db.execute(insert(models.QuestionResponse.__table__),
                       response_rows[0] if len(response_rows) == 1 else response_rows)
    if any(selected_options.values()):
        if len(response_rows) == 1:
            response_ids = {response_rows[0]["question_id"]: saved.inserted_primary_key[0]}
        else:
            response_ids = dict(db.query(models.QuestionResponse.question_id, models.QuestionResponse.id)
                                .filter_by(attempt_id=attempt.id).all())
        db.execute(insert(models.ResponseOption.__table__), [
            {"response_id": response_ids[qid], "option_id": oid}
            for qid, option_ids in selected_options.items() for oid in option_ids
        ])

    total_questions = len(test_questions)
    attempted = sum(1 for r in results if r.outcome != "skipped")
    subject_breakdown = {}
    for result in results:
        code = question_subjects[result.question_id]
        item = subject_breakdown.setdefault(code, {"correct": 0, "total": 0})
        item["total"] += 1
        item["correct"] += int(result.outcome == "correct")

    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.score = total_marks
    attempt.total_questions = total_questions
    attempt.accuracy = round((correct_count / attempted) * 100, 2) if attempted else 0.0
    attempt.avg_time_seconds = round(total_time / total_questions, 2) if total_questions else 0.0
    attempt.subject_breakdown = subject_breakdown

    coins_earned = rewards.check_and_award_milestones(
        db, user, previously_correct_count, previously_correct_count + correct_count, wallet
    )
    current_streak = None
    if test_kind == "daily":
        coins_earned += rewards.update_streak_and_award(db, user, locked_profile=wallet)
        current_streak = wallet.current_streak

    # Build before commit expires ORM attributes; return only after durable commit.
    result = schemas.SubjectTestResultOut(
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
    db.commit()
    return result
