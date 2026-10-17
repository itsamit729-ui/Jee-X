"""Reopenable analysis of a submitted, server-graded attempt.

Rebuilt from stored question_responses, so a result can be reviewed after the
submit response is gone. Classroom assignments keep their own release rules
and are never served here."""
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app import models

SUBJECT_NAMES = {'PHY': 'Physics', 'CHEM': 'Chemistry', 'MATH': 'Mathematics',
                 'ENG': 'English Proficiency', 'LR': 'Logical Reasoning'}


def _own_attempts(db: Session, user_id: int):
    """Submitted attempts of this user, excluding classroom assignments (they keep their own release rules)."""
    return (db.query(models.TestAttempt, models.Test)
            .join(models.Test, models.Test.id == models.TestAttempt.test_id)
            .filter(models.TestAttempt.user_id == user_id, models.TestAttempt.submitted_at.isnot(None),
                    models.TestAttempt.test_id.notin_(select(models.TeachingAssignment.test_id))))


def history(db: Session, user_id: int, limit: int = 20, before: int | None = None) -> list[dict]:
    """Submitted attempts, newest first; `before` is the last attempt id already shown."""
    query = _own_attempts(db, user_id)
    if before:
        query = query.filter(models.TestAttempt.id < before)
    rows = query.order_by(models.TestAttempt.id.desc()).limit(max(1, min(limit, 50))).all()
    # Only the listed attempts are checked for stored per-question detail.
    ids = [attempt.id for attempt, _ in rows]
    detailed = {a for (a,) in db.query(models.QuestionResponse.attempt_id)
                .filter(models.QuestionResponse.attempt_id.in_(ids)).distinct()} if ids else set()
    return [{
        'id': attempt.id, 'title': test.title, 'kind': test.kind, 'pattern': test.pattern,
        'is_mock': test.kind == 'mock', 'score': attempt.score, 'total_questions': attempt.total_questions,
        'accuracy': attempt.accuracy, 'submitted_at': attempt.submitted_at, 'detail_available': attempt.id in detailed,
    } for attempt, test in rows]


def _previous(db: Session, attempt: models.TestAttempt, test: models.Test):
    """The student's latest earlier attempt of the same kind of paper, for a change-since-last comparison."""
    row = (_own_attempts(db, attempt.user_id)
           .filter(models.TestAttempt.id < attempt.id, models.Test.kind == test.kind,
                   models.Test.pattern == test.pattern, models.Test.title == test.title)
           .order_by(models.TestAttempt.id.desc()).first())
    if not row:
        return None
    previous, _ = row
    return {'attempt_id': previous.id, 'score': previous.score, 'accuracy': previous.accuracy,
            'submitted_at': previous.submitted_at}


def _bucket():
    return {'correct': 0, 'wrong': 0, 'skipped': 0, 'total': 0, 'marks': 0, 'max_marks': 0, 'time_sec': 0}


def _add(bucket, outcome, marks, max_marks, seconds):
    bucket[outcome if outcome in ('correct', 'wrong') else 'skipped'] += 1
    bucket['total'] += 1
    bucket['marks'] += marks
    bucket['max_marks'] += max_marks
    bucket['time_sec'] += seconds


def _accuracy(bucket):
    attempted = bucket['correct'] + bucket['wrong']
    return round(bucket['correct'] / attempted * 100, 1) if attempted else 0.0


def build_analysis(db: Session, user_id: int, attempt_id: int) -> dict:
    attempt = (db.query(models.TestAttempt).options(joinedload(models.TestAttempt.test))
               .filter(models.TestAttempt.id == attempt_id, models.TestAttempt.user_id == user_id).first())
    if not attempt:
        raise HTTPException(404, 'Attempt not found.')
    if attempt.submitted_at is None:
        raise HTTPException(409, 'Submit this test to see its analysis.')
    if db.query(models.TeachingAssignment.id).filter_by(test_id=attempt.test_id).first():
        raise HTTPException(403, 'Open this result from the class assignment.')
    test = attempt.test
    meta = {'attempt_id': attempt.id, 'title': test.title, 'kind': test.kind, 'pattern': test.pattern,
            'is_mock': test.kind == 'mock', 'duration_sec': test.duration_sec, 'submitted_at': attempt.submitted_at,
            'previous': _previous(db, attempt, test)}

    responses = {r.question_id: r for r in db.query(models.QuestionResponse).filter_by(attempt_id=attempt.id)}
    if not responses:
        # Legacy client-scored attempt: only the stored summary exists.
        return {'meta': meta, 'detail_available': False, 'summary': {
            'score': attempt.score, 'total_questions': attempt.total_questions, 'accuracy': attempt.accuracy,
            'avg_time_seconds': attempt.avg_time_seconds}, 'subject_breakdown': attempt.subject_breakdown or {},
            'subjects': [], 'chapters': [], 'questions': []}

    selected = defaultdict(list)
    for response_id, option_id in (db.query(models.ResponseOption.response_id, models.ResponseOption.option_id)
                                   .filter(models.ResponseOption.response_id.in_([r.id for r in responses.values()]))):
        selected[response_id].append(option_id)
    paper = (db.query(models.TestQuestion, models.Question, models.Chapter, models.Subject)
             .join(models.Question, models.Question.id == models.TestQuestion.question_id)
             .join(models.Subtopic, models.Subtopic.id == models.Question.subtopic_id)
             .join(models.Chapter, models.Chapter.id == models.Subtopic.chapter_id)
             .join(models.Subject, models.Subject.id == models.Chapter.subject_id)
             .options(selectinload(models.Question.options), selectinload(models.Question.assets),
                      selectinload(models.Question.passage).selectinload(models.Passage.assets))
             .filter(models.TestQuestion.test_id == test.id)
             .order_by(models.TestQuestion.position).all())

    summary, subjects, chapters, questions = _bucket(), {}, {}, []
    for tq, question, chapter, subject in paper:
        response = responses.get(question.id)
        outcome = response.outcome if response else 'skipped'
        marks = response.marks_awarded if response else 0
        seconds = response.time_taken_sec if response else 0
        for bucket in (summary, subjects.setdefault(subject.code, _bucket()),
                       chapters.setdefault(chapter.id, _bucket())):
            _add(bucket, outcome, marks, tq.marks_correct, seconds)
        chapters[chapter.id].update(chapter_id=chapter.id, name=chapter.name, subject_code=subject.code)
        assets = list(question.assets) + (list(question.passage.assets) if question.passage else [])
        questions.append({
            'position': tq.position, 'question_id': question.id, 'ref': question.ref, 'type': question.type,
            'subject_code': subject.code, 'chapter': chapter.name, 'stem': question.stem,
            'passage': question.passage.content if question.passage else None,
            'assets': [{'url': a.url, 'alt_text': a.alt_text} for a in assets],
            'options': [{'id': o.id, 'label': o.label, 'content': o.content}
                        for o in sorted(question.options, key=lambda o: o.position)],
            'selected_option_ids': sorted(selected.get(response.id, [])) if response else [],
            'numeric_answer': response.numeric_answer if response else None,
            'correct_option_ids': sorted(o.id for o in question.options if o.is_correct),
            'answer_min': question.answer_min if question.type == 'numerical' else None,
            'answer_max': question.answer_max if question.type == 'numerical' else None,
            'outcome': outcome, 'marks_awarded': marks, 'marks_correct': tq.marks_correct,
            'time_taken_sec': seconds, 'expected_time_sec': question.expected_time_sec,
            'solution': question.solution,
        })

    return {
        'meta': meta, 'detail_available': True,
        'summary': {'score': summary['marks'], 'max_score': summary['max_marks'],
                    'total_questions': summary['total'], 'correct': summary['correct'], 'wrong': summary['wrong'],
                    'skipped': summary['skipped'], 'accuracy': _accuracy(summary), 'time_sec': summary['time_sec'],
                    'marks_lost': -sum(q['marks_awarded'] for q in questions if q['marks_awarded'] < 0)},
        'subject_breakdown': attempt.subject_breakdown or {},
        'subjects': [{'code': code, 'name': SUBJECT_NAMES.get(code, code), **b, 'accuracy': _accuracy(b)}
                     for code, b in subjects.items()],
        'chapters': sorted(({**b, 'accuracy': _accuracy(b)} for b in chapters.values()),
                           key=lambda c: (c['subject_code'], c['name'])),
        'questions': questions,
    }
