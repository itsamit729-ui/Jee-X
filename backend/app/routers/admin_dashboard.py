"""Password-gated, read-only admin analytics for Jee Edge.

The shared password is read from ADMIN_PASSWORD at runtime and is never sent to the
frontend bundle. Successful logins receive an opaque in-memory session token; a backend
restart intentionally invalidates every admin session.
"""

import hmac
import os
import secrets
import time as clock
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from threading import Lock

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session, joinedload

from app import models
from app.database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])

IST = timezone(timedelta(hours=5, minutes=30))
SESSION_TTL_SECONDS = 12 * 60 * 60
LOGIN_WINDOW_SECONDS = 10 * 60
LOGIN_BLOCK_SECONDS = 15 * 60
MAX_LOGIN_FAILURES = 5

_sessions: dict[str, float] = {}
_failed_logins: dict[str, list[float]] = defaultdict(list)
_blocked_until: dict[str, float] = {}
_state_lock = Lock()


class AdminLoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=256)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _prune_state(now: float) -> None:
    expired = [token for token, expires_at in _sessions.items() if expires_at <= now]
    for token in expired:
        _sessions.pop(token, None)

    for key, failures in list(_failed_logins.items()):
        recent = [ts for ts in failures if now - ts <= LOGIN_WINDOW_SECONDS]
        if recent:
            _failed_logins[key] = recent
        else:
            _failed_logins.pop(key, None)

    for key, until in list(_blocked_until.items()):
        if until <= now:
            _blocked_until.pop(key, None)


def _require_admin(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin session required.")

    token = authorization.removeprefix("Bearer ").strip()
    now = clock.time()
    with _state_lock:
        _prune_state(now)
        expires_at = _sessions.get(token)
        if expires_at is None or expires_at <= now:
            _sessions.pop(token, None)
            raise HTTPException(status_code=401, detail="Admin session expired. Sign in again.")
    return token


def _as_ist(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(IST)


def _iso_ist(value: datetime | None) -> str | None:
    converted = _as_ist(value)
    return converted.isoformat() if converted else None


def _start_of_ist_day_utc_naive(day) -> datetime:
    return datetime.combine(day, time.min, tzinfo=IST).astimezone(timezone.utc).replace(tzinfo=None)


@router.post("/login")
def admin_login(body: AdminLoginIn, request: Request, response: Response):
    configured_password = os.getenv("ADMIN_PASSWORD", "")
    if not configured_password:
        raise HTTPException(status_code=503, detail="Admin dashboard is not configured on the server.")

    key = _client_key(request)
    now = clock.time()
    with _state_lock:
        _prune_state(now)
        if _blocked_until.get(key, 0) > now:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")

    if not hmac.compare_digest(body.password, configured_password):
        with _state_lock:
            recent = [ts for ts in _failed_logins[key] if now - ts <= LOGIN_WINDOW_SECONDS]
            recent.append(now)
            _failed_logins[key] = recent
            if len(recent) >= MAX_LOGIN_FAILURES:
                _blocked_until[key] = now + LOGIN_BLOCK_SECONDS
                _failed_logins.pop(key, None)
        raise HTTPException(status_code=401, detail="Invalid admin password.")

    token = secrets.token_urlsafe(32)
    with _state_lock:
        _failed_logins.pop(key, None)
        _blocked_until.pop(key, None)
        _sessions[token] = now + SESSION_TTL_SECONDS

    response.headers["Cache-Control"] = "no-store"
    return {"token": token, "expires_in": SESSION_TTL_SECONDS}


@router.post("/logout")
def admin_logout(token: str = Depends(_require_admin)):
    with _state_lock:
        _sessions.pop(token, None)
    return {"ok": True}


@router.get("/dashboard")
def admin_dashboard(
    response: Response,
    _: str = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"

    now_ist = datetime.now(IST)
    today = now_ist.date()
    today_start = _start_of_ist_day_utc_naive(today)
    week_start = _start_of_ist_day_utc_naive(today - timedelta(days=6))
    window_start_day = today - timedelta(days=13)
    window_start = _start_of_ist_day_utc_naive(window_start_day)

    total_users = db.query(func.count(models.User.id)).scalar() or 0
    teacher_ids = db.query(models.TeacherAccess.user_id).filter(models.TeacherAccess.active.is_(True))
    student_users = db.query(func.count(models.User.id)).filter(models.User.role == "student", ~models.User.id.in_(teacher_ids)).scalar() or 0
    new_users_today = db.query(func.count(models.User.id)).filter(models.User.created_at >= today_start).scalar() or 0
    new_users_7d = db.query(func.count(models.User.id)).filter(models.User.created_at >= week_start).scalar() or 0
    active_today = (
        db.query(func.count(func.distinct(models.TestAttempt.user_id)))
        .filter(models.TestAttempt.started_at >= today_start)
        .scalar()
        or 0
    )
    active_7d = (
        db.query(func.count(func.distinct(models.TestAttempt.user_id)))
        .filter(models.TestAttempt.started_at >= week_start)
        .scalar()
        or 0
    )

    total_questions = db.query(func.count(models.Question.id)).scalar() or 0
    published_questions = (
        db.query(func.count(models.Question.id)).filter(models.Question.status == "published").scalar() or 0
    )

    submitted_attempts = (
        db.query(func.count(models.TestAttempt.id))
        .filter(models.TestAttempt.submitted_at.isnot(None))
        .scalar()
        or 0
    )
    attempts_today = (
        db.query(func.count(models.TestAttempt.id))
        .filter(models.TestAttempt.started_at >= today_start)
        .scalar()
        or 0
    )
    questions_solved = (
        db.query(func.coalesce(func.sum(models.TestAttempt.total_questions), 0))
        .filter(models.TestAttempt.submitted_at.isnot(None))
        .scalar()
        or 0
    )
    avg_accuracy = (
        db.query(func.avg(models.TestAttempt.accuracy))
        .filter(models.TestAttempt.submitted_at.isnot(None), models.TestAttempt.accuracy.isnot(None))
        .scalar()
        or 0
    )

    daily_assigned_today = (
        db.query(func.count(models.DailyQuestionAssignment.id))
        .filter(models.DailyQuestionAssignment.assigned_date == today)
        .scalar()
        or 0
    )
    daily_completed_today = (
        db.query(func.count(func.distinct(models.DailyQuestionAssignment.id)))
        .join(models.TestAttempt, models.TestAttempt.test_id == models.DailyQuestionAssignment.test_id)
        .filter(
            models.DailyQuestionAssignment.assigned_date == today,
            models.TestAttempt.submitted_at.isnot(None),
            models.TestAttempt.user_id == models.DailyQuestionAssignment.user_id,
        )
        .scalar()
        or 0
    )
    daily_completion_rate = (
        round((daily_completed_today / daily_assigned_today) * 100, 1) if daily_assigned_today else 0.0
    )

    outstanding_coins = db.query(func.coalesce(func.sum(models.StudentProfile.edge_coins), 0)).scalar() or 0
    pending_redemptions = (
        db.query(func.count(models.RewardRedemption.id))
        .filter(models.RewardRedemption.status == "pending")
        .scalar()
        or 0
    )
    open_question_reports = (
        db.query(func.count(models.QuestionReport.id))
        .filter(models.QuestionReport.status == "open")
        .scalar()
        or 0
    )
    rated_users = db.query(func.count(func.distinct(models.JeeXRating.user_id))).scalar() or 0
    rated_contests = db.query(func.count(models.RatedContest.id)).scalar() or 0

    status_counts = {status: count for status, count in db.query(models.Question.status, func.count(models.Question.id)).group_by(models.Question.status).all()}
    for status in ("draft", "reviewed", "published", "retired"):
        status_counts.setdefault(status, 0)

    subject_rows = (
        db.query(
            models.Subject.code,
            models.Subject.name,
            func.count(models.Question.id),
            func.sum(case((models.Question.status == "published", 1), else_=0)),
        )
        .join(models.Chapter, models.Chapter.subject_id == models.Subject.id)
        .join(models.Subtopic, models.Subtopic.chapter_id == models.Chapter.id)
        .join(models.Question, models.Question.subtopic_id == models.Subtopic.id)
        .group_by(models.Subject.code, models.Subject.name)
        .order_by(models.Subject.code)
        .all()
    )
    subjects = [
        {"code": code, "name": name, "total": int(total or 0), "published": int(published or 0)}
        for code, name, total, published in subject_rows
    ]

    attempt_kind_rows = (
        db.query(models.Test.kind, func.count(models.TestAttempt.id))
        .join(models.Test, models.TestAttempt.test_id == models.Test.id)
        .filter(models.TestAttempt.submitted_at.isnot(None))
        .group_by(models.Test.kind)
        .order_by(func.count(models.TestAttempt.id).desc())
        .all()
    )
    attempt_kinds = [{"kind": kind, "count": int(count or 0)} for kind, count in attempt_kind_rows]

    days = [window_start_day + timedelta(days=i) for i in range(14)]
    signup_counts = {day: 0 for day in days}
    active_sets = {day: set() for day in days}
    attempt_counts = {day: 0 for day in days}

    for (created_at,) in db.query(models.User.created_at).filter(models.User.created_at >= window_start).all():
        converted = _as_ist(created_at)
        if converted and converted.date() in signup_counts:
            signup_counts[converted.date()] += 1

    for user_id, started_at in (
        db.query(models.TestAttempt.user_id, models.TestAttempt.started_at)
        .filter(models.TestAttempt.started_at >= window_start)
        .all()
    ):
        converted = _as_ist(started_at)
        if converted and converted.date() in active_sets:
            active_sets[converted.date()].add(user_id)
            attempt_counts[converted.date()] += 1

    growth = [
        {
            "date": day.isoformat(),
            "signups": signup_counts[day],
            "active_users": len(active_sets[day]),
            "attempts": attempt_counts[day],
        }
        for day in days
    ]

    recent_users_rows = db.query(models.User).options(joinedload(models.User.student_profile)).order_by(models.User.created_at.desc(), models.User.id.desc()).limit(10).all()
    recent_users = []
    for user in recent_users_rows:
        profile = user.student_profile
        recent_users.append(
            {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "created_at": _iso_ist(user.created_at),
                "target_exam": profile.target_exam if profile else None,
                "target_year": profile.target_year if profile else None,
                "streak": int(profile.current_streak or 0) if profile else 0,
                "coins": int(profile.edge_coins or 0) if profile else 0,
            }
        )

    recent_attempt_rows = (
        db.query(models.TestAttempt, models.User, models.Test)
        .join(models.User, models.User.id == models.TestAttempt.user_id)
        .join(models.Test, models.Test.id == models.TestAttempt.test_id)
        .filter(models.TestAttempt.submitted_at.isnot(None))
        .order_by(models.TestAttempt.submitted_at.desc())
        .limit(10)
        .all()
    )
    recent_attempts = [
        {
            "id": attempt.id,
            "username": user.username,
            "test_title": test.title,
            "kind": test.kind,
            "score": attempt.score,
            "total_questions": attempt.total_questions,
            "accuracy": round(float(attempt.accuracy or 0), 1),
            "submitted_at": _iso_ist(attempt.submitted_at),
        }
        for attempt, user, test in recent_attempt_rows
    ]

    return {
        "generated_at": now_ist.isoformat(),
        "overview": {
            "total_users": int(total_users),
            "student_users": int(student_users),
            "teacher_users": db.query(models.TeacherAccess).filter_by(active=True).count(),
            "pending_profiles": db.query(models.AuthAccount).filter(models.AuthAccount.user_id.is_(None), models.AuthAccount.disabled.is_(False)).count(),
            "new_users_today": int(new_users_today),
            "new_users_7d": int(new_users_7d),
            "active_users_today": int(active_today),
            "active_users_7d": int(active_7d),
            "total_questions": int(total_questions),
            "published_questions": int(published_questions),
            "submitted_attempts": int(submitted_attempts),
            "attempts_today": int(attempts_today),
            "questions_solved": int(questions_solved),
            "average_accuracy": round(float(avg_accuracy), 1),
        },
        "daily": {
            "assigned_today": int(daily_assigned_today),
            "completed_today": int(daily_completed_today),
            "completion_rate": daily_completion_rate,
        },
        "community": {
            "rated_users": int(rated_users),
            "rated_contests": int(rated_contests),
            "outstanding_coins": int(outstanding_coins),
            "pending_redemptions": int(pending_redemptions),
            "open_question_reports": int(open_question_reports),
        },
        "questions": {"status": status_counts, "subjects": subjects},
        "teaching": {
            "classrooms": db.query(models.Classroom).count(),
            "memberships": db.query(models.ClassroomMember).filter_by(active=True).count(),
            "students": db.query(func.count(func.distinct(models.ClassroomMember.user_id))).filter(models.ClassroomMember.active.is_(True)).scalar() or 0,
            "assignments": db.query(models.TeachingAssignment).count(),
            "papers": db.query(models.TeacherPaper).count(),
            "finalized_papers": db.query(models.TeacherPaper).filter_by(finalized=True).count(),
            "scans": {state: count for state, count in db.query(models.TeacherScan.state, func.count(models.TeacherScan.id)).group_by(models.TeacherScan.state)},
        },
        "attempts": {"by_kind": attempt_kinds},
        "growth": growth,
        "recent_users": recent_users,
        "recent_attempts": recent_attempts,
    }


@router.get('/users', dependencies=[Depends(_require_admin)])
def admin_users(response: Response, q: str = Query('', max_length=150),
                role: str = Query('all', pattern='^(all|student|teacher)$'),
                offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    teacher_ids = db.query(models.TeacherAccess.user_id).filter(models.TeacherAccess.active.is_(True))
    query = db.query(models.User).options(joinedload(models.User.student_profile), joinedload(models.User.teacher_access))
    if q.strip():
        term = q.strip()
        terms = [column.contains(term, autoescape=True) for column in (models.User.name, models.User.username, models.User.email)]
        if term.isascii() and term.isdecimal() and len(term) <= 10:
            terms.append(models.User.id == int(term))
        query = query.filter(or_(*terms))
    if role == 'teacher':
        query = query.filter(models.User.id.in_(teacher_ids))
    elif role == 'student':
        query = query.filter(models.User.role == 'student', ~models.User.id.in_(teacher_ids))
    total = query.count()
    rows = query.order_by(models.User.created_at.desc(), models.User.id.desc()).offset(offset).limit(limit).all()
    return {'total': total, 'offset': offset, 'limit': limit, 'items': [{
        'id': u.id, 'name': u.name, 'username': u.username, 'email': u.email,
        'role': 'teacher' if u.teacher_access and u.teacher_access.active else u.role,
        'status': u.status, 'omr_id': str(u.id).zfill(10),
        'target_exam': u.student_profile.target_exam if u.student_profile else None,
        'target_year': u.student_profile.target_year if u.student_profile else None,
        'created_at': _iso_ist(u.created_at), 'last_active_at': _iso_ist(u.last_active_at),
    } for u in rows]}


@router.get('/questions', dependencies=[Depends(_require_admin)])
def admin_questions(response: Response, q: str = Query('', max_length=150),
                    exam: str = Query('', max_length=30), status: str = Query('', pattern='^(|draft|reviewed|published|retired)$'),
                    kind: str = Query('', pattern='^(|single_correct|multi_correct|numerical)$'),
                    offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                    db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    query = db.query(models.Question, models.Subject.code, models.Chapter.name).join(
        models.Subtopic, models.Question.subtopic_id == models.Subtopic.id).join(
        models.Chapter, models.Subtopic.chapter_id == models.Chapter.id).join(
        models.Subject, models.Chapter.subject_id == models.Subject.id)
    if q.strip():
        term = q.strip()
        query = query.filter(or_(models.Question.ref.contains(term, autoescape=True), models.Question.stem.contains(term, autoescape=True)))
    if exam: query = query.filter(models.Question.exam == exam)
    if status: query = query.filter(models.Question.status == status)
    if kind: query = query.filter(models.Question.type == kind)
    total = query.count()
    rows = query.order_by(models.Question.updated_at.desc(), models.Question.id.desc()).offset(offset).limit(limit).all()
    return {'total': total, 'offset': offset, 'limit': limit, 'items': [{
        'id': question.id, 'ref': question.ref, 'stem': question.stem, 'subject': subject, 'chapter': chapter,
        'exam': question.exam, 'year': question.year, 'shift': question.shift, 'status': question.status,
        'type': question.type, 'difficulty': question.difficulty, 'version': question.version,
    } for question, subject, chapter in rows]}


@router.get('/paper-coverage', dependencies=[Depends(_require_admin)])
def admin_coverage(response: Response, exam: str = Query('', max_length=30),
                   offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    query = db.query(models.Question.exam, models.Question.year, models.Question.shift,
                     func.count(models.Question.id), func.sum(case((models.Question.status == 'published', 1), else_=0))).filter(
        models.Question.source_type == 'pyq').group_by(models.Question.exam, models.Question.year, models.Question.shift)
    if exam: query = query.filter(models.Question.exam == exam)
    total = query.count()
    rows = query.order_by(models.Question.year.desc(), models.Question.exam, models.Question.shift).offset(offset).limit(limit).all()
    return {'total': total, 'offset': offset, 'limit': limit, 'items': [dict(exam=exam, year=year, shift=shift,
        total=count, published=int(published or 0)) for exam, year, shift, count, published in rows]}


@router.get('/classrooms', dependencies=[Depends(_require_admin)])
def admin_classrooms(response: Response, q: str = Query('', max_length=150), offset: int = Query(0, ge=0),
                     limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    members = db.query(models.ClassroomMember.classroom_id.label('class_id'), func.count().label('members')).filter(
        models.ClassroomMember.active.is_(True)).group_by(models.ClassroomMember.classroom_id).subquery()
    query = db.query(models.Classroom, models.User.username, members.c.members).join(
        models.User, models.Classroom.teacher_id == models.User.id).outerjoin(members, members.c.class_id == models.Classroom.id)
    if q.strip():
        query = query.filter(or_(models.Classroom.name.contains(q.strip(), autoescape=True), models.User.username.contains(q.strip(), autoescape=True)))
    total = query.count()
    rows = query.order_by(models.Classroom.created_at.desc(), models.Classroom.id.desc()).offset(offset).limit(limit).all()
    return {'total': total, 'offset': offset, 'limit': limit, 'items': [dict(id=c.id, name=c.name, teacher=username,
        members=int(count or 0), created_at=_iso_ist(c.created_at)) for c, username, count in rows]}


@router.get('/operations', dependencies=[Depends(_require_admin)])
def admin_operations(response: Response, queue: str = Query('reports', pattern='^(reports|rewards|imports|scans)$'),
                     offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    """Bounded operational ledgers. Never expose shipping data, raw scans or import paths."""
    response.headers['Cache-Control'] = 'no-store'
    if queue == 'reports':
        query = db.query(models.QuestionReport, models.Question.ref).join(models.Question, models.Question.id == models.QuestionReport.question_id).filter(models.QuestionReport.status == 'open')
        total = query.count()
        rows = query.order_by(models.QuestionReport.created_at, models.QuestionReport.id).offset(offset).limit(limit).all()
        items = [dict(id=r.id, reference=ref, detail=r.reason[:600], status=r.status, at=_iso_ist(r.created_at)) for r, ref in rows]
    elif queue == 'rewards':
        query = db.query(models.RewardRedemption, models.User.username, models.RewardCatalogItem.name).join(models.User, models.User.id == models.RewardRedemption.user_id).join(models.RewardCatalogItem, models.RewardCatalogItem.id == models.RewardRedemption.catalog_item_id).filter(models.RewardRedemption.status == 'pending')
        total = query.count()
        rows = query.order_by(models.RewardRedemption.requested_at, models.RewardRedemption.id).offset(offset).limit(limit).all()
        items = [dict(id=r.id, reference='@'+username, detail=f'{name} · {r.coins_spent} coins', status=r.status, at=_iso_ist(r.requested_at)) for r, username, name in rows]
    elif queue == 'imports':
        query = db.query(models.ImportRun)
        total = query.count()
        rows = query.order_by(models.ImportRun.created_at.desc(), models.ImportRun.id.desc()).offset(offset).limit(limit).all()
        items = [dict(id=r.id, reference=f'Import #{r.id}', detail=f'{r.added} added · {r.updated} updated', status='has_errors' if r.errors else 'completed', at=_iso_ist(r.created_at)) for r in rows]
    else:
        query = db.query(models.TeacherScan, models.TeacherPaper.title, models.User.username).join(models.TeacherPaper, models.TeacherPaper.id == models.TeacherScan.paper_id).join(models.User, models.User.id == models.TeacherScan.teacher_id)
        total = query.count()
        rows = query.order_by(models.TeacherScan.created_at.desc(), models.TeacherScan.id).offset(offset).limit(limit).all()
        items = [dict(id=r.id, reference=title, detail='Teacher @'+username, status=r.state, at=_iso_ist(r.created_at)) for r, title, username in rows]
    return {'total': total, 'offset': offset, 'limit': limit, 'items': items}


@router.get('/registrations', dependencies=[Depends(_require_admin)])
def admin_registrations(response: Response, q: str = Query('', max_length=150),
                        state: str = Query('all', pattern='^(all|pending|complete|disabled)$'),
                        offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                        db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    query = db.query(models.AuthAccount.id, models.AuthAccount.email, models.AuthAccount.user_id,
                     models.AuthAccount.verified_at, models.AuthAccount.disabled, models.AuthAccount.created_at)
    if q.strip(): query = query.filter(models.AuthAccount.email.contains(q.strip(), autoescape=True))
    if state == 'pending': query = query.filter(models.AuthAccount.user_id.is_(None), models.AuthAccount.disabled.is_(False))
    elif state == 'complete': query = query.filter(models.AuthAccount.user_id.isnot(None), models.AuthAccount.disabled.is_(False))
    elif state == 'disabled': query = query.filter(models.AuthAccount.disabled.is_(True))
    total = query.count()
    rows = query.order_by(models.AuthAccount.created_at.desc(), models.AuthAccount.id).offset(offset).limit(limit).all()
    return {'total': total, 'offset': offset, 'limit': limit, 'items': [dict(id=r.id, email=r.email,
        profile_id=r.user_id, status='disabled' if r.disabled else 'complete' if r.user_id else 'pending',
        verified=bool(r.verified_at), created_at=_iso_ist(r.created_at)) for r in rows]}
