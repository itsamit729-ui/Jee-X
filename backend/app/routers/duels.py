"""Two invited students only. All mutations serialize on the match row."""
from datetime import timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.deps import get_current_db_user
from app.services import duels as service

router = APIRouter(prefix='/api/duels', tags=['duels'])


class Challenge(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    username: str = Field(min_length=3, max_length=20, pattern=r'^[a-zA-Z0-9_]+$')
    exam: str = Field(default='jee_main', pattern=r'^(jee_main|mht_cet|bitsat)$')
    subject: str | None = Field(default=None, pattern=r'^(PHY|CHEM|MATH)$')
    count: int = Field(default=5)


class Answer(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    option_ids: list[str] = Field(default_factory=list, max_length=1)
    numeric_answer: float | None = None


def owned(db, user, match_id):
    service.student(user)
    match = db.query(models.DuelMatch).filter(models.DuelMatch.id == match_id,
        or_(models.DuelMatch.challenger_id == user.id, models.DuelMatch.opponent_id == user.id)
        ).with_for_update().populate_existing().first()
    if not match:
        raise HTTPException(404, 'Challenge not found.')
    players = db.query(models.DuelPlayer).filter_by(match_id=match.id).order_by(models.DuelPlayer.user_id).with_for_update().populate_existing().all()
    now = service.utcnow()
    service.settle(match, players, now)
    return match, players, now


def output(db, match, players, user, now):
    data = service.serialize(db, match, players, user.id, now, paper=True)
    db.commit()
    return data


@router.get('')
def inbox(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    service.student(user)
    # Open matches first; bounded history thereafter. Deadline recovery needs no
    # in-process timers, and survives worker restarts.
    rows = db.query(models.DuelMatch).filter(or_(models.DuelMatch.challenger_id == user.id,
        models.DuelMatch.opponent_id == user.id)).order_by(
        models.DuelMatch.state.in_(service.OPEN).desc(), models.DuelMatch.created_at.desc()).limit(40).with_for_update().all()
    now = service.utcnow()
    result = []
    all_players = db.query(models.DuelPlayer).filter(models.DuelPlayer.match_id.in_([m.id for m in rows])).with_for_update().all()
    users = {u.id: u for u in db.query(models.User).filter(models.User.id.in_([p.user_id for p in all_players])).all()}
    by_match = {}
    for player in all_players:
        by_match.setdefault(player.match_id, []).append(player)
    for match in rows:
        players = by_match[match.id]
        service.settle(match, players, now)
        result.append(service.serialize(db, match, players, user.id, now, users=users))
    db.commit()
    return result


@router.post('', status_code=201)
def create(body: Challenge, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    service.student(user)
    if body.count not in service.FORMATS:
        raise HTTPException(422, 'Choose 5, 10 or 15 questions.')
    opponent = db.query(models.User).filter_by(username=body.username.lower(), status='active', role='student').first()
    if not opponent or not opponent.student_profile or opponent.teacher_access:
        raise HTTPException(404, 'Student not found. Check their exact username.')
    if user.id == opponent.id:
        raise HTTPException(422, 'Choose another student to challenge.')
    # Stable user lock order protects quotas and duplicate invitations on MySQL.
    db.query(models.User).filter(models.User.id.in_([user.id, opponent.id])).order_by(models.User.id).with_for_update().all()
    now = service.utcnow()
    for uid in [user.id, opponent.id]:
        open_count = len(db.query(models.DuelMatch).filter(or_(models.DuelMatch.challenger_id == uid,
            models.DuelMatch.opponent_id == uid), models.DuelMatch.state.in_(service.OPEN),
            or_((models.DuelMatch.state == 'active') & (models.DuelMatch.deadline_at > now),
                (models.DuelMatch.state.in_(['pending', 'lobby'])) & (models.DuelMatch.expires_at > now))).with_for_update().all())
        if open_count >= 5:
            raise HTTPException(429, 'One of you already has five open challenges. Finish or close one first.')
    if len(db.query(models.DuelMatch.id).filter(models.DuelMatch.challenger_id == user.id,
        models.DuelMatch.created_at >= now-timedelta(days=1)).with_for_update().all()) >= 20:
        raise HTTPException(429, 'You have reached 20 invitations today. Try again tomorrow.')
    duplicate = db.query(models.DuelMatch).filter(
        or_((models.DuelMatch.challenger_id == user.id) & (models.DuelMatch.opponent_id == opponent.id),
            (models.DuelMatch.challenger_id == opponent.id) & (models.DuelMatch.opponent_id == user.id)),
        models.DuelMatch.state.in_(service.OPEN),
        or_((models.DuelMatch.state == 'active') & (models.DuelMatch.deadline_at > now),
            models.DuelMatch.state.in_(['pending', 'lobby']) & (models.DuelMatch.expires_at > now))).with_for_update().first()
    if duplicate:
        raise HTTPException(409, 'You already have an open challenge with this student. Open it from your lobby.')
    questions = service.choose(db, body.exam, body.subject, body.count, [user.id, opponent.id])
    match = models.DuelMatch(id=uuid4().hex, challenger_id=user.id, opponent_id=opponent.id,
        exam=body.exam, subject=body.subject, question_count=body.count, duration_sec=service.FORMATS[body.count],
        state='pending', questions=questions, created_at=now, expires_at=now+timedelta(minutes=30))
    db.add(match)
    db.flush()
    players = [models.DuelPlayer(match_id=match.id, user_id=uid, answers={}) for uid in [user.id, opponent.id]]
    db.add_all(players)
    return output(db, match, players, user, now)


@router.get('/invitations/count')
def invitation_count(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    service.student(user)
    return {'count': db.query(models.DuelMatch).filter_by(opponent_id=user.id, state='pending').filter(
        models.DuelMatch.expires_at > service.utcnow()).count()}


@router.get('/{match_id}')
def get_match(match_id: str, paper: bool = True, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    match, players, now = owned(db, user, match_id)
    mine = next(p for p in players if p.user_id == user.id)
    mine.last_seen_at = now
    data = service.serialize(db, match, players, user.id, now, paper=paper)
    db.commit()
    return data


@router.post('/{match_id}/{action}')
def action(match_id: str, action: str, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    service.student(user)
    if action not in ('accept', 'decline', 'cancel', 'leave', 'ready', 'submit', 'surrender'):
        raise HTTPException(404, 'Unknown match action.')
    identities = db.query(models.DuelMatch.challenger_id, models.DuelMatch.opponent_id).filter(
        models.DuelMatch.id == match_id, or_(models.DuelMatch.challenger_id == user.id,
        models.DuelMatch.opponent_id == user.id)).first()
    if not identities:
        raise HTTPException(404, 'Challenge not found.')
    # Lock participants before the match, including across different lobbies.
    db.query(models.User).filter(models.User.id.in_(identities)).order_by(models.User.id).with_for_update().all()
    match, players, now = owned(db, user, match_id)
    mine = next(p for p in players if p.user_id == user.id)
    mine.last_seen_at = now
    if action == 'accept' and match.state == 'pending' and user.id == match.opponent_id:
        match.state = 'lobby'
        match.expires_at = now+timedelta(minutes=10)
    elif action == 'decline' and match.state == 'pending' and user.id == match.opponent_id:
        match.state = 'declined'
    elif action == 'cancel' and match.state in ('pending', 'lobby') and user.id == match.challenger_id:
        match.state = 'cancelled'
    elif action == 'leave' and match.state == 'lobby':
        match.state = 'cancelled'
    elif action == 'ready' and match.state == 'lobby':
        # A player cannot be in two live matches at once.
        other = db.query(models.DuelMatch).filter(models.DuelMatch.id != match.id,
            models.DuelMatch.state == 'active', models.DuelMatch.deadline_at > now,
            or_(models.DuelMatch.challenger_id.in_([p.user_id for p in players]),
                models.DuelMatch.opponent_id.in_([p.user_id for p in players]))).with_for_update().first()
        if other:
            raise HTTPException(409, 'One of you is playing another match. Finish it before readying up.')
        mine.ready_at = mine.ready_at or now
        if all(p.ready_at for p in players):
            match.state = 'active'
            match.starts_at = now+timedelta(seconds=5)
            match.deadline_at = match.starts_at+timedelta(seconds=match.duration_sec)
    elif action in ('submit', 'surrender') and match.state == 'active' and now >= match.starts_at:
        if mine.submitted_at and action == 'surrender':
            raise HTTPException(409, 'Your answers are already locked. Wait for your opponent to finish.')
        if not mine.submitted_at:
            mine.submitted_at = now
            mine.forfeited = action == 'surrender'
            mine.result = service.score(match, mine)
        if action == 'surrender':
            for player in players:
                if not player.submitted_at:
                    player.submitted_at = now
                    player.result = service.score(match, player)
        service.settle(match, players, now)
    elif match.state not in ('completed', 'expired', 'declined', 'cancelled'):
        raise HTTPException(409, 'That action is unavailable in the current match state. Refresh the match.')
    return output(db, match, players, user, now)


@router.put('/{match_id}/answers/{question_id}')
def save(match_id: str, question_id: str, body: Answer, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    match, players, now = owned(db, user, match_id)
    mine = next(p for p in players if p.user_id == user.id)
    if match.state != 'active' or now < match.starts_at or mine.submitted_at:
        db.commit()  # persist any deadline settlement
        raise HTTPException(409, 'The match is not accepting answers. Refresh to see its status.')
    question = next((q for q in match.questions if q['id'] == question_id), None)
    if not question:
        raise HTTPException(404, 'Question is not part of this match.')
    mine.answers = {**(mine.answers or {}), question_id: service.answer(question, body)}
    mine.last_seen_at = now
    db.commit()
    return {'saved': True, 'question_id': question_id}
