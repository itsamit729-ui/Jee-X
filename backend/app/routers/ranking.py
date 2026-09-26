import concurrent.futures
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, AwareDatetime
from sqlalchemy.orm import Session
from app import models
from app.database import get_db, SessionLocal
from app.deps import get_current_db_user
from app.models.ranking import JeeXRating, RatedContest, ContestEntry
from app.services.ranking import TIERS, tier, summary, finalize

router = APIRouter(prefix='/api/ranking', tags=['ranking'])

# Reused across requests (not recreated per call) — backs the parallel reads
# in dashboard() below, each running on its own DB session/connection from
# the existing pool. One database, multiple simultaneous connections to it.
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix='ranking-db')


def _run_in_new_session(fn, *args):
    db = SessionLocal()
    try:
        return fn(db, *args)
    finally:
        db.close()


def student(user):
    if user.status != 'active' or user.role != 'student' or not user.student_profile:
        raise HTTPException(403, 'An active student profile is required.')
    return user.student_profile


def cohort(db, user):
    p = student(user)
    return db.query(RatedContest).filter_by(exam=p.target_exam, target_year=p.target_year)


def settle(db, user):
    # Always settle in chronological order, including contests the caller missed.
    contests = cohort(db, user).filter(RatedContest.closes_at <= datetime.utcnow(), RatedContest.finalized.is_(False)).order_by(RatedContest.closes_at, RatedContest.id).with_for_update().all()
    for contest in contests:
        finalize(db, contest)
    db.commit()


@router.post('/settle')
def settle_closed(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    settle(db, user)
    return {'ok': True}


def _build_me(db, user_id, exam, target_year, visibility):
    account = db.get(JeeXRating, (user_id, exam, target_year))
    events = db.query(ContestEntry, RatedContest).join(RatedContest, RatedContest.id == ContestEntry.contest_id).filter(
        ContestEntry.user_id == user_id, RatedContest.exam == exam,
        RatedContest.target_year == target_year, ContestEntry.rating_after.isnot(None)
    ).order_by(RatedContest.closes_at.desc()).limit(50).all()
    return {**summary(account), 'exam': exam, 'target_year': target_year,
            'visibility': visibility, 'tiers': TIERS,
            'history': [dict(contest=c.title, date=c.closes_at, before=e.rating_before,
                             after=e.rating_after, delta=e.rating_after-e.rating_before, rank=e.rank, score=e.score) for e,c in events]}


def _build_leaderboard(db, user_id, exam, target_year, page):
    if page < 1:
        raise HTTPException(422, 'Page must be positive.')
    query = db.query(JeeXRating, models.User).join(models.User, models.User.id == JeeXRating.user_id).join(models.StudentProfile, models.StudentProfile.user_id == models.User.id).filter(
        JeeXRating.exam == exam, JeeXRating.target_year == target_year,
        models.StudentProfile.target_exam == exam, models.StudentProfile.target_year == target_year,
        JeeXRating.contests >= 3, JeeXRating.last_rated_at >= datetime.utcnow()-timedelta(days=30),
        models.StudentProfile.leaderboard_visibility == 'username', models.User.status == 'active', models.User.role == 'student')
    ordered = query.order_by(JeeXRating.rating.desc(), JeeXRating.user_id).all()
    rows = []
    rank = 0
    previous = None
    my_rank = None
    for index, (r, u) in enumerate(ordered):
        if r.rating != previous:
            rank = index + 1
        previous = r.rating
        if u.id == user_id:
            my_rank = rank
        if (page-1)*50 <= index < page*50:
            rows.append(dict(rank=rank, username=u.username, rating=r.rating, title=tier(r.rating)['title'], is_me=u.id==user_id))
    return dict(entries=rows, total=len(ordered), page=page, my_rank=my_rank)


def _build_contests(db, user_id, exam, target_year):
    rows = db.query(RatedContest).filter_by(exam=exam, target_year=target_year).order_by(RatedContest.opens_at.desc()).limit(30).all()
    entries = {entry.contest_id: entry for entry in db.query(ContestEntry).filter(
        ContestEntry.user_id == user_id, ContestEntry.contest_id.in_([c.id for c in rows])
    ).all()} if rows else {}
    result = []
    now = datetime.utcnow()
    for c in rows:
        entry = entries.get(c.id)
        result.append(dict(id=c.id, title=c.title, opens_at=c.opens_at.isoformat()+'Z', closes_at=c.closes_at.isoformat()+'Z',
                           duration_sec=c.duration_sec, question_count=len(c.questions), finalized=c.finalized,
                           status='upcoming' if now<c.opens_at else 'closed' if now>=c.closes_at else 'live',
                           entry_id=entry.id if entry else None, submitted=bool(entry and entry.submitted_at),
                           score=entry.score if entry and c.finalized else None,
                           rank=entry.rank if entry and c.finalized else None,
                           rated=bool(entry and entry.rating_after is not None)))
    return result


@router.get('/dashboard')
def dashboard(user=Depends(get_current_db_user), db: Session = Depends(get_db), page: int = 1):
    """Everything the Ranking page needs in as little wall-clock time as
    possible: settle any closed contests first (sequential — it can change
    what the three reads below see), then me + leaderboard + contests in
    parallel, each on its own DB session/connection from the pool. Same one
    database throughout — just multiple simultaneous connections to it
    instead of one connection used four times in a row. Individual endpoints
    below are kept for other callers, but the page itself should use this."""
    p = student(user)
    user_id, exam, target_year, visibility = user.id, p.target_exam, p.target_year, p.leaderboard_visibility
    settle(db, user)
    me_future = _pool.submit(_run_in_new_session, _build_me, user_id, exam, target_year, visibility)
    board_future = _pool.submit(_run_in_new_session, _build_leaderboard, user_id, exam, target_year, page)
    contests_future = _pool.submit(_run_in_new_session, _build_contests, user_id, exam, target_year)

    return dict(me=me_future.result(), leaderboard=board_future.result(), contests=contests_future.result())


@router.get('/me')
def me(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    p = student(user)
    return _build_me(db, user.id, p.target_exam, p.target_year, p.leaderboard_visibility)


@router.get('/leaderboard')
def leaderboard(user=Depends(get_current_db_user), db: Session = Depends(get_db), page: int = 1):
    p = student(user)
    return _build_leaderboard(db, user.id, p.target_exam, p.target_year, page)


class VisibilityIn(BaseModel):
    visibility: Literal['username', 'hidden']


@router.patch('/visibility')
def visibility(body: VisibilityIn, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    student(user).leaderboard_visibility = body.visibility
    db.commit()
    return {'visibility': body.visibility}


@router.get('/contests')
def contests(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    p = student(user)
    return _build_contests(db, user.id, p.target_exam, p.target_year)


@router.post('/contests/{contest_id}/start')
def start(contest_id: int, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    p = student(user)
    c = cohort(db, user).filter(RatedContest.id == contest_id).with_for_update().first()
    now = datetime.utcnow()
    if not c or not c.opens_at <= now < c.closes_at:
        raise HTTPException(409, 'This contest is not open.')
    entry = db.query(ContestEntry).filter_by(contest_id=c.id, user_id=user.id).with_for_update().first()
    if not entry:
        # Serialize account creation even for simultaneous starts.
        db.query(models.User).filter_by(id=user.id).with_for_update().one()
        if not db.query(JeeXRating).filter_by(user_id=user.id, exam=p.target_exam, target_year=p.target_year).with_for_update().first():
            db.add(JeeXRating(user_id=user.id, exam=p.target_exam, target_year=p.target_year))
        entry = ContestEntry(contest_id=c.id, user_id=user.id, started_at=now,
                             deadline=min(c.closes_at, now+timedelta(seconds=c.duration_sec)), answers={})
        db.add(entry)
        db.flush()
    if entry.submitted_at or now >= entry.deadline:
        raise HTTPException(409, 'Your attempt has ended. Saved answers will be graded when the contest closes.')
    out = dict(id=entry.id, title=c.title, deadline=entry.deadline.isoformat()+'Z', server_time=now.isoformat()+'Z', answers=entry.answers,
               questions=[{k:v for k,v in q.items() if k not in ('correct_option_ids','answer_min','answer_max','solution')} for q in c.questions])
    db.commit()
    return out


class Answer(BaseModel):
    question_id: int
    option_ids: list[int] = Field(default_factory=list, max_length=4)
    numeric_answer: float | None = Field(default=None, allow_inf_nan=False)


class SaveIn(BaseModel):
    answers: list[Answer] = Field(max_length=100)
    submit: bool = False


@router.put('/entries/{entry_id}')
def save(entry_id: int, body: SaveIn, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    student(user)
    # Same lock order as start/finalize: contest, then entry.
    initial = db.query(ContestEntry).filter_by(id=entry_id, user_id=user.id).first()
    if not initial:
        raise HTTPException(404, 'Attempt not found.')
    c = db.query(RatedContest).filter_by(id=initial.contest_id).with_for_update().one()
    e = db.query(ContestEntry).filter_by(id=entry_id).with_for_update().populate_existing().one()
    now = datetime.utcnow()
    if c.finalized or e.submitted_at or now >= e.deadline:
        raise HTTPException(409, 'Your attempt has ended. Previously saved answers are retained.')
    questions = {q['id']:q for q in c.questions}
    if len({a.question_id for a in body.answers}) != len(body.answers):
        raise HTTPException(422, 'Duplicate question answers.')
    answers = {}
    for a in body.answers:
        q = questions.get(a.question_id)
        if not q or not set(a.option_ids) <= {o['id'] for o in q['options']}:
            raise HTTPException(422, 'Invalid question or option.')
        if (q['type']=='single_correct' and len(a.option_ids)>1) or (q['type']=='numerical' and a.option_ids) or (q['type']!='numerical' and a.numeric_answer is not None):
            raise HTTPException(422, 'Answer does not match the question type.')
        answers[str(a.question_id)] = a.model_dump()
    e.answers = answers
    if body.submit:
        e.submitted_at = now
    db.commit()
    return dict(saved=True, submitted=body.submit)


class ContestIn(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    exam: Literal['jee_main','jee_advanced']
    target_year: int = Field(ge=2026, le=2100)
    opens_at: AwareDatetime
    closes_at: AwareDatetime
    duration_sec: int = Field(ge=60, le=14400)
    question_ids: list[int] = Field(min_length=1, max_length=100)


@router.post('/contests', status_code=201)
def create(body: ContestIn, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    if user.role != 'admin' or user.status != 'active':
        raise HTTPException(403, 'Administrator access required.')
    opens = body.opens_at.astimezone(timezone.utc).replace(tzinfo=None)
    closes = body.closes_at.astimezone(timezone.utc).replace(tzinfo=None)
    if opens <= datetime.utcnow() or closes-opens < timedelta(seconds=body.duration_sec):
        raise HTTPException(422, 'Use a future opening and a window at least as long as the test.')
    if len(set(body.question_ids)) != len(body.question_ids):
        raise HTTPException(422, 'Question IDs must be unique.')
    # Serialize scheduling across administrators, including an empty contest table.
    db.query(models.User).filter(models.User.role=='admin').order_by(models.User.id).with_for_update().all()
    if db.query(RatedContest).filter(RatedContest.exam==body.exam, RatedContest.target_year==body.target_year,
                                   RatedContest.opens_at<closes, RatedContest.closes_at>opens).with_for_update().first():
        raise HTTPException(409, 'Another contest overlaps this cohort and time window.')
    snapshots = []
    for qid in body.question_ids:
        q = db.get(models.Question, qid)
        if not q or q.status != 'published' or (q.exam and q.exam != body.exam):
            raise HTTPException(422, f'Question {qid} must be published and compatible with the exam.')
        correct = [o.id for o in q.options if o.is_correct]
        if q.type != 'numerical' and (not correct or (q.type=='single_correct' and len(correct)!=1)):
            raise HTTPException(422, f'Question {qid} has an invalid answer key.')
        snapshots.append(dict(id=q.id, stem=q.stem, type=q.type, passage=q.passage.content if q.passage else None,
                              assets=[dict(url=a.url, alt_text=a.alt_text) for a in list(q.assets) + (list(q.passage.assets) if q.passage else [])],
                              options=[dict(id=o.id, label=o.label, content=o.content) for o in q.options],
                              correct_option_ids=correct, answer_min=q.answer_min, answer_max=q.answer_max, solution=q.solution))
    c = RatedContest(title=body.title, exam=body.exam, target_year=body.target_year, opens_at=opens,
                     closes_at=closes, duration_sec=body.duration_sec, questions=snapshots)
    db.add(c)
    db.commit()
    return dict(id=c.id)
