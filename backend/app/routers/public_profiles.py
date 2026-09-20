"""Allowlisted public responses. Never serialize private user/profile models."""
from collections import OrderedDict, deque
from datetime import datetime, timedelta
from threading import Lock
from time import monotonic
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_db_user
from app.models.public_profile import PublicProfile
from app.models.ranking import JeeXRating, RatedContest, ContestEntry
from app.services.ranking import summary

router = APIRouter(prefix='/api', tags=['public-profiles'])
# Bounded per-process limiter. Uses ASGI peer, never arbitrary forwarded headers.
# Configure trusted proxy handling at the server; use a shared limiter when scaling.
_buckets = OrderedDict()
_bucket_lock = Lock()


def public_read(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    key = request.client.host if request.client else 'unknown'
    now = monotonic()
    with _bucket_lock:
        bucket = _buckets.setdefault(key, deque())
        _buckets.move_to_end(key)
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= 60:
            raise HTTPException(429, 'Too many profile requests. Try again shortly.', headers={'Retry-After': '60', 'Cache-Control': 'no-store'})
        bucket.append(now)
        while len(_buckets) > 4096:
            _buckets.popitem(last=False)


class SettingsIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    enabled: bool
    show_activity: bool
    display_name: str = Field(default='', max_length=80)
    bio: str = Field(default='', max_length=280)


def active_student(user):
    if user.status != 'active' or user.role != 'student' or not user.student_profile:
        raise HTTPException(403, 'An active student profile is required.')


def settings_out(row):
    return dict(enabled=bool(row and row.enabled), show_activity=bool(row and row.show_activity),
                display_name=row.display_name if row else '', bio=row.bio if row else '')


@router.get('/profile/public-settings')
def get_settings(response: Response, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    active_student(user)
    response.headers['Cache-Control'] = 'no-store'
    return settings_out(db.get(PublicProfile, user.id))


@router.patch('/profile/public-settings')
def save_settings(body: SettingsIn, response: Response, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    active_student(user)
    db.query(models.User).filter_by(id=user.id).with_for_update().one()
    row = db.query(PublicProfile).filter_by(user_id=user.id).with_for_update().first()
    if row is None:
        row = PublicProfile(user_id=user.id)
        db.add(row)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    response.headers['Cache-Control'] = 'no-store'
    return settings_out(row)


def resolve(db, username):
    username = username.strip().lower()
    if not re.fullmatch(r'[a-z0-9_]{3,20}', username):
        raise HTTPException(404, 'Profile unavailable.', headers={'Cache-Control': 'no-store'})
    found = db.query(models.User, PublicProfile).join(PublicProfile, PublicProfile.user_id == models.User.id).filter(
        models.User.username == username, models.User.status == 'active', models.User.role == 'student',
        PublicProfile.enabled.is_(True)).first()
    if not found or not found[0].student_profile:
        raise HTTPException(404, 'Profile unavailable.', headers={'Cache-Control': 'no-store'})
    return found


def events_for(db, user):
    p = user.student_profile
    return db.query(ContestEntry, RatedContest).join(RatedContest, RatedContest.id == ContestEntry.contest_id).filter(
        ContestEntry.user_id == user.id, RatedContest.exam == p.target_exam,
        RatedContest.target_year == p.target_year, RatedContest.finalized.is_(True),
        RatedContest.closes_at <= datetime.utcnow(), ContestEntry.rating_after.isnot(None))


def event_out(entry, contest):
    return dict(contest=contest.title, date=contest.closes_at.isoformat() + 'Z',
                before=entry.rating_before, after=entry.rating_after,
                delta=entry.rating_after-entry.rating_before, rank=entry.rank, score=entry.score)


@router.get('/public-profiles/{username}', dependencies=[Depends(public_read)])
def get_public_profile(username: str, db: Session = Depends(get_db)):
    user, public = resolve(db, username)
    p = user.student_profile
    account = db.get(JeeXRating, (user.id, p.target_exam, p.target_year))
    rating = summary(account)
    rank = None
    if rating['rating'] is not None and rating['active'] and p.leaderboard_visibility == 'username':
        rank = 1 + db.query(JeeXRating).join(models.User, models.User.id == JeeXRating.user_id).join(
            models.StudentProfile, models.StudentProfile.user_id == models.User.id).filter(
            JeeXRating.exam == p.target_exam, JeeXRating.target_year == p.target_year,
            models.StudentProfile.target_exam == p.target_exam, models.StudentProfile.target_year == p.target_year,
            models.User.status == 'active', models.User.role == 'student',
            models.StudentProfile.leaderboard_visibility == 'username', JeeXRating.contests >= 3,
            JeeXRating.last_rated_at >= datetime.utcnow()-timedelta(days=30), JeeXRating.rating > account.rating).count()
    recent = events_for(db, user).order_by(RatedContest.closes_at.desc(), RatedContest.id.desc()).limit(100).all()
    activity = None
    if public.show_activity:
        from app.services.rewards import today_ist
        since = today_ist()-timedelta(days=181)
        dates = db.query(models.DailyQuestionAssignment.assigned_date).join(
            models.TestAttempt, models.TestAttempt.test_id == models.DailyQuestionAssignment.test_id).filter(
            models.DailyQuestionAssignment.user_id == user.id, models.TestAttempt.user_id == user.id,
            models.DailyQuestionAssignment.assigned_date >= since,
            models.TestAttempt.submitted_at.isnot(None)).distinct().order_by(models.DailyQuestionAssignment.assigned_date).all()
        current = p.current_streak or 0
        if not p.last_streak_date or p.last_streak_date < today_ist()-timedelta(days=1):
            current = 0
        activity = dict(current_streak=current, longest_streak=p.longest_streak or 0,
                        dates=[d[0].isoformat() for d in dates])
    return dict(username=user.username, display_name=public.display_name, bio=public.bio,
                exam=p.target_exam, target_year=p.target_year, rating=rating, rank=rank,
                history=[event_out(e,c) for e,c in reversed(recent)], activity=activity)


@router.get('/public-profiles/{username}/contests', dependencies=[Depends(public_read)])
def public_contests(username: str, page: int = Query(default=1, ge=1, le=10000), db: Session = Depends(get_db)):
    user, _ = resolve(db, username)
    query = events_for(db, user)
    total = query.count()
    rows = query.order_by(RatedContest.closes_at.desc(), RatedContest.id.desc()).offset((page-1)*20).limit(20).all()
    return dict(entries=[event_out(e,c) for e,c in rows], page=page, total=total)
