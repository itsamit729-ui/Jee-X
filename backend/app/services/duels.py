"""Server-clock lifecycle and equal, frozen papers. No client-supplied scores."""
import math
import random
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import joinedload
from app import models
from app.services.question_catalog import candidate_query
from app.services.scenarios import _bank_snapshot, grade

OPEN = ('pending', 'lobby', 'active')
FORMATS = {5: 300, 10: 900, 15: 1500}


def utcnow():
    return datetime.utcnow()


def stamp(value):
    return value.isoformat() + 'Z' if value else None


def student(user):
    if user.status != 'active' or user.role != 'student' or not user.student_profile or user.teacher_access:
        raise HTTPException(403, 'Complete an active student profile to play a duel.')


def choose(db, exam, subject, count, user_ids):
    query = candidate_query(db, exam=exam).join(models.Subject, models.Subject.id == models.Chapter.subject_id)
    query = query.filter(models.Subject.code.in_([subject] if subject else ['PHY', 'CHEM', 'MATH']))
    # Load cheap selection metadata, then hydrate only the selected questions.
    candidates = query.all()
    if len(candidates) < count:
        raise HTTPException(422, f'Only {len(candidates)} complete questions are available for this choice. Choose fewer questions or all subjects.')
    seen = {qid for (qid,) in db.query(models.QuestionResponse.question_id).filter(
        models.QuestionResponse.user_id.in_(user_ids)).distinct().all()}
    rng = random.SystemRandom()
    rng.shuffle(candidates)
    # Prefer questions neither player has practised, distributed across difficulty
    # bands and subjects. Both receive exactly the same order and marking.
    buckets = {}
    for row in candidates:
        buckets.setdefault((row.subject_id, min(2, (row.difficulty-1)//3)), []).append(row)
    for pool in buckets.values():
        pool.sort(key=lambda row: row.id in seen)
    picked = []
    while len(picked) < count:
        keys = list(buckets)
        rng.shuffle(keys)
        for key in keys:
            if buckets[key] and len(picked) < count:
                picked.append(buckets[key].pop(0).id)
    rows = db.query(models.Question).filter(models.Question.id.in_(picked)).options(
        joinedload(models.Question.options), joinedload(models.Question.assets),
        joinedload(models.Question.passage).joinedload(models.Passage.assets),
        joinedload(models.Question.subtopic).joinedload(models.Subtopic.chapter).joinedload(models.Chapter.subject)).all()
    by_id = {q.id: q for q in rows}
    return [_bank_snapshot(by_id[qid], by_id[qid].subtopic.chapter.subject.code) for qid in picked]


def marking(match, question):
    if match.exam == 'mht_cet':
        return (2 if question['subject'] == 'MATH' else 1), 0
    return (3, 1) if match.exam == 'bitsat' else (4, 1)


def score(match, player):
    result = grade(match.questions, player.answers or {})
    for q, row in zip(match.questions, result['questions']):
        correct, wrong = marking(match, q)
        row['marks'] = correct if row['outcome'] == 'correct' else -wrong if row['outcome'] == 'wrong' else 0
        saved = (player.answers or {}).get(q['id'], {})
        row['selected_option_ids'] = saved.get('option_ids', [])
        row['numeric_answer'] = saved.get('numeric_answer')
    result['score'] = sum(row['marks'] for row in result['questions'])
    result['possible_marks'] = sum(marking(match, q)[0] for q in match.questions)
    return result


def settle(match, players, now):
    if match.state in ('pending', 'lobby') and now >= match.expires_at:
        match.state = 'expired'
    if match.state != 'active':
        return
    if now >= match.deadline_at:
        for player in players:
            if not player.submitted_at:
                player.submitted_at = match.deadline_at
                player.result = score(match, player)
    if all(p.submitted_at for p in players):
        match.state = 'completed'
        match.completed_at = now
        available = [p for p in players if not p.forfeited]
        if len(available) == 1:
            match.winner_id = available[0].user_id
        elif len(available) == 2:
            a, b = available
            # Equal marks are a draw; network latency never breaks a tie.
            if a.result['score'] != b.result['score']:
                match.winner_id = max(available, key=lambda p: p.result['score']).user_id


def answer(question, payload):
    options = payload.option_ids
    number = payload.numeric_answer
    if question['type'] == 'numerical':
        invalid = bool(options) or number is not None and not math.isfinite(number)
    else:
        invalid = number is not None or len(options) > 1 or any(o not in {v['id'] for v in question['options']} for o in options)
    if invalid:
        raise HTTPException(422, 'Choose one available option, enter a finite numerical answer, or clear the answer.')
    return dict(option_ids=options, numeric_answer=number)


def serialize(db, match, players, viewer_id, now, paper=False, users=None):
    finished = match.state == 'completed'
    mine = next(p for p in players if p.user_id == viewer_id)
    if users is None:
        users = {u.id: u for u in db.query(models.User).filter(models.User.id.in_([p.user_id for p in players])).all()}
    out = dict(id=match.id, viewer_id=viewer_id, state=match.state, challenger_id=match.challenger_id, exam=match.exam,
        subject=match.subject, question_count=match.question_count, duration_sec=match.duration_sec,
        created_at=stamp(match.created_at), expires_at=stamp(match.expires_at), starts_at=stamp(match.starts_at),
        deadline_at=stamp(match.deadline_at), server_now=stamp(now), winner_id=match.winner_id,
        players=[dict(user_id=p.user_id, username=users[p.user_id].username, ready=bool(p.ready_at),
            submitted=bool(p.submitted_at), forfeited=bool(p.forfeited),
            connected=bool(p.last_seen_at and (now-p.last_seen_at).total_seconds() < 20),
            answered=sum(bool(a.get('option_ids')) or a.get('numeric_answer') is not None for a in (p.answers or {}).values()),
            result=(p.result if paper else {key: p.result[key] for key in
                ('score', 'possible_marks', 'correct', 'wrong', 'skipped')}) if finished else None) for p in players])
    if paper:
        out['answers'] = mine.answers or {}
        # Do not release the paper during ready-up/countdown.
        out['questions'] = [dict(question_id=q['id'], subject_code=q['subject'], type=q['type'], stem=q['stem'],
            passage=q.get('passage'), assets=q['assets'], options=q['options'],
            marks_correct=marking(match, q)[0], marks_wrong=marking(match, q)[1]) for q in match.questions
            ] if finished or match.state == 'active' and now >= match.starts_at else []
    return out
