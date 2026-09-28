"""Teacher approval, classrooms, immutable assignments and a scheduled in-app inbox."""
import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload, defer

from app import models as m, schemas
from app.auth import get_auth_account, utcnow
from app.database import get_db
from app.deps import get_current_db_user
from app.routers.admin_dashboard import _require_admin
from app.services.authentication import throttle
from app.services.grading import _grade_one
from app.services.teacher_enrollment import enable_teacher

router = APIRouter(prefix='/api', tags=['classrooms'])


def stamp(value):
    return naive(value).isoformat() + 'Z' if value else None


def naive(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def lock_user(db, user_id, allow_inactive=False):
    user = db.query(m.User).filter_by(id=user_id).with_for_update().populate_existing().first()
    if not user or (user.status != 'active' and not allow_inactive):
        raise HTTPException(403, 'Account access is unavailable.')
    return user


def require_teacher(user: m.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    user = lock_user(db, user.id)
    access = db.get(m.TeacherAccess, user.id, populate_existing=True)
    if not access or not access.active:
        raise HTTPException(403, 'Open Teacher studio to start teaching.')
    return user


def notify(db, user_id, title, body, href, kind='info', assignment=None, when=None):
    db.add(m.ClassroomNotification(user_id=user_id, title=title, body=body, href=href,
        kind=kind, assignment_id=assignment, available_at=when or utcnow()))


class AccessIn(BaseModel):
    active: bool


@router.get('/admin/teachers')
def admin_accounts(q: str = Query('', max_length=254), token=Depends(_require_admin), db: Session = Depends(get_db)):
    query = db.query(m.AuthAccount, m.User, m.TeacherAccess).outerjoin(m.User, m.AuthAccount.user_id == m.User.id).outerjoin(m.TeacherAccess, m.TeacherAccess.user_id == m.User.id)
    if q.strip():
        term = '%' + q.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        query = query.filter(or_(m.AuthAccount.email.ilike(term, escape='\\'), m.User.username.ilike(term, escape='\\')))
    else:
        query = query.filter(m.TeacherAccess.active.is_(True))
    rows = query.order_by(m.AuthAccount.email).limit(25).all()
    return {'accounts': [{'account_id': a.id, 'user_id': a.user_id, 'email': a.email,
        'name': u.name if u else None, 'username': u.username if u else None,
        'active': bool(t and t.active), 'disabled': a.disabled or bool(u and u.status != 'active'),
        'granted_at': stamp(t.granted_at) if t else None, 'revoked_at': stamp(t.revoked_at) if t else None} for a, u, t in rows]}


@router.put('/admin/teachers/{account_id}')
def set_teacher(account_id: str, body: AccessIn, token=Depends(_require_admin), db: Session = Depends(get_db)):
    account = db.query(m.AuthAccount).filter_by(id=account_id).with_for_update().first()
    if not account:
        raise HTTPException(404, 'Account not found. Ask the teacher to sign up first.')
    if account.disabled and body.active:
        raise HTTPException(409, 'Enable this account before granting teacher access.')
    if not account.user_id:
        if not body.active:
            return {'active': False}
        user = m.User(auth0_sub='local:' + account.id, email=account.email, name=account.email.split('@')[0],
            username='teacher_' + secrets.token_hex(8), role='student', status='active')
        db.add(user)
        db.flush()
        account.user_id = user.id
    user = lock_user(db, account.user_id, allow_inactive=not body.active)
    access = db.get(m.TeacherAccess, user.id)
    before = bool(access and access.active)
    if before == body.active:
        db.commit()
        return {'active': body.active, 'user_id': user.id}
    if not access:
        access = m.TeacherAccess(user_id=user.id, granted_at=utcnow())
        db.add(access)
    access.active = body.active
    if body.active:
        access.granted_at, access.revoked_at = utcnow(), None
    else:
        access.revoked_at = utcnow()
    db.add(m.AuditLog(actor_id=None, action='teacher_access_granted' if body.active else 'teacher_access_revoked',
        entity='user', entity_id=user.id, before={'active': before}, after={'active': body.active},
        reason='Admin session ' + hashlib.sha256(token.encode()).hexdigest()[:12]))
    notify(db, user.id, 'Teacher access enabled' if body.active else 'Teacher access removed',
        'You can now create classes and assign tests.' if body.active else 'Your classes and results have been preserved.',
        '/teacher' if body.active else '/classes')
    db.commit()
    return {'active': body.active, 'user_id': user.id}


@router.post('/teacher/enroll')
def enroll_teacher(account: m.AuthAccount = Depends(get_auth_account), db: Session = Depends(get_db)):
    user = enable_teacher(db, account)
    db.commit()
    return {'teacher': True, 'user_id': user.id}


@router.get('/classrooms/access')
def access_info(account: m.AuthAccount = Depends(get_auth_account), db: Session = Depends(get_db)):
    access = db.get(m.TeacherAccess, account.user_id) if account.user_id else None
    user = db.get(m.User, account.user_id) if account.user_id else None
    return {'teacher': bool(access and access.active and user and user.status == 'active'),
        'restricted': bool(access and not access.active), 'student_profile': bool(user and user.student_profile), 'has_profile': bool(user)}


class ClassIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    @field_validator('name')
    @classmethod
    def trim(cls, value):
        if len(value.strip()) < 2:
            raise ValueError('Enter a class name.')
        return value.strip()


class JoinIn(BaseModel):
    code: str = Field(min_length=6, max_length=16)


def owned_class(db, cid, teacher):
    room = db.query(m.Classroom).filter_by(id=cid, teacher_id=teacher.id).with_for_update().first()
    if not room:
        raise HTTPException(404, 'Class not found.')
    return room


@router.get('/teacher/classes')
def teacher_classes(user=Depends(require_teacher), db: Session = Depends(get_db)):
    rooms = db.query(m.Classroom).filter_by(teacher_id=user.id).order_by(m.Classroom.created_at.desc()).all()
    members = db.query(m.ClassroomMember, m.User).join(m.User, m.User.id == m.ClassroomMember.user_id).filter(
        m.ClassroomMember.classroom_id.in_([r.id for r in rooms])).order_by(m.User.name).all()
    return {'classes': [{'id': r.id, 'name': r.name, 'join_code': r.join_code,
        'members': [{'id': u.id, 'name': u.name, 'username': u.username, 'active': mem.active} for mem, u in members if mem.classroom_id == r.id]} for r in rooms]}


@router.post('/teacher/classes', status_code=201)
def create_class(body: ClassIn, user=Depends(require_teacher), db: Session = Depends(get_db)):
    room = m.Classroom(teacher_id=user.id, name=body.name, join_code=''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10)), created_at=utcnow())
    db.add(room)
    db.commit()
    return {'id': room.id, 'name': room.name, 'join_code': room.join_code}


@router.delete('/teacher/classes/{class_id}/members/{student_id}')
def remove_member(class_id: int, student_id: int, user=Depends(require_teacher), db: Session = Depends(get_db)):
    owned_class(db, class_id, user)
    member = db.get(m.ClassroomMember, (class_id, student_id))
    if not member:
        raise HTTPException(404, 'Student not found in this class.')
    member.active = False
    db.commit()
    return {'removed': True}


@router.post('/classrooms/join')
def join_class(body: JoinIn, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    throttle(db, 'classroom_join', str(user.id), 15, 600)
    lock_user(db, user.id)
    room = db.query(m.Classroom).filter_by(join_code=body.code.strip().upper()).with_for_update().first()
    access = db.get(m.TeacherAccess, room.teacher_id) if room else None
    if not room or not access or not access.active:
        raise HTTPException(404, 'That class code is unavailable. Check it with your teacher.')
    if room.teacher_id == user.id:
        raise HTTPException(400, 'You already manage this class.')
    member = db.get(m.ClassroomMember, (room.id, user.id))
    if member and not member.active:
        raise HTTPException(403, 'You were removed from this class. Ask your teacher to restore access.')
    if not member:
        db.add(m.ClassroomMember(classroom_id=room.id, user_id=user.id, joined_at=utcnow(), active=True))
    db.commit()
    return {'id': room.id, 'name': room.name}


@router.post('/teacher/classes/{class_id}/members/{student_id}/restore')
def restore_member(class_id: int, student_id: int, user=Depends(require_teacher), db: Session = Depends(get_db)):
    owned_class(db, class_id, user)
    member = db.get(m.ClassroomMember, (class_id, student_id))
    if not member:
        raise HTTPException(404, 'Membership not found.')
    member.active = True
    db.commit()
    return {'restored': True}


def question_query(db):
    return db.query(m.Question).options(selectinload(m.Question.options), selectinload(m.Question.assets),
        joinedload(m.Question.passage).selectinload(m.Passage.assets),
        joinedload(m.Question.subtopic).joinedload(m.Subtopic.chapter).joinedload(m.Chapter.subject)).filter(
        m.Question.status == 'published', m.Question.type.in_(['single_correct', 'multi_correct', 'numerical']))


def freeze(q, version):
    options = [{'id': o.id, 'label': o.label, 'content': o.content, 'is_correct': o.is_correct} for o in sorted(q.options, key=lambda o: o.position)]
    if not q.stem or (q.type == 'numerical' and (q.answer_min is None or q.answer_max is None or q.answer_min > q.answer_max)) or (q.type != 'numerical' and (len(options) < 2 or not any(o['is_correct'] for o in options))):
        raise HTTPException(409, f'Question {q.ref} has an incomplete answer key. Choose another question.')
    return {'question_id': q.id, 'version': version, 'ref': q.ref, 'type': q.type, 'stem': q.stem,
        'options': options, 'answer_min': float(q.answer_min) if q.answer_min is not None else None,
        'answer_max': float(q.answer_max) if q.answer_max is not None else None, 'solution': q.solution,
        'assets': [{'url': a.url, 'alt_text': a.alt_text} for a in q.assets],
        'passage': {'body': q.passage.content, 'assets': [{'url': a.url, 'alt_text': a.alt_text} for a in q.passage.assets]} if q.passage else None,
        'subject': q.subtopic.chapter.subject.code, 'chapter': q.subtopic.chapter.name,
        'subtopic_id': q.subtopic_id, 'topic': q.subtopic.name, 'difficulty': q.difficulty}


def safe_question(q):
    return {**{k: q[k] for k in ('question_id', 'ref', 'type', 'stem', 'assets', 'passage', 'subject', 'chapter', 'topic', 'difficulty')},
        'options': [{k: o[k] for k in ('id', 'label', 'content')} for o in q['options']]}


@router.get('/teacher/questions')
def question_bank(q: str = Query('', max_length=150), subject: str = Query('', max_length=12), chapter_id: int | None = None,
                  difficulty: int | None = Query(None, ge=1, le=10), offset: int = Query(0, ge=0, le=10000),
                  user=Depends(require_teacher), db: Session = Depends(get_db)):
    query = question_query(db).join(m.Subtopic).join(m.Chapter).join(m.Subject)
    if subject:
        query = query.filter(m.Subject.code == subject)
    if chapter_id:
        query = query.filter(m.Chapter.id == chapter_id)
    if difficulty:
        query = query.filter(m.Question.difficulty == difficulty)
    if q.strip():
        query = query.filter(or_(m.Question.ref.contains(q.strip(), autoescape=True), m.Question.stem.contains(q.strip(), autoescape=True)))
    rows = query.order_by(m.Question.id).offset(offset).limit(21).all()
    questions = []
    for row in rows[:20]:
        try:
            questions.append(freeze(row, row.version))
        except HTTPException:
            continue
    chapters = db.query(m.Chapter.id, m.Chapter.name, m.Subject.code).join(m.Subject).order_by(m.Subject.code, m.Chapter.name).all()
    return {'questions': questions, 'has_more': len(rows) > 20,
        'chapters': [{'id': c.id, 'name': c.name, 'subject': c.code} for c in chapters]}


class PublishIn(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    instructions: str = Field('', max_length=2000)
    classroom_ids: list[int] = Field(min_length=1, max_length=20)
    question_ids: list[int] = Field(min_length=1, max_length=100)
    opens_at: datetime
    due_at: datetime
    solutions_at: datetime
    duration_minutes: int = Field(30, ge=1, le=240)
    marks_correct: int = Field(4, ge=1, le=10)
    marks_wrong: int = Field(1, ge=0, le=10)
    request_key: str = Field(min_length=16, max_length=64)

    @field_validator('opens_at', 'due_at', 'solutions_at')
    @classmethod
    def timezone_required(cls, value):
        if not value.tzinfo:
            raise ValueError('Include a timezone in the date.')
        return naive(value)


@router.post('/teacher/assignments', status_code=201)
def publish(body: PublishIn, user=Depends(require_teacher), db: Session = Depends(get_db)):
    existing = db.query(m.TeachingAssignment).filter_by(teacher_id=user.id, request_key=body.request_key).first()
    if existing:
        return {'id': existing.id, 'title': existing.title}
    now = utcnow()
    if len(body.title.strip()) < 3 or len(set(body.question_ids)) != len(body.question_ids):
        raise HTTPException(422, 'Use a title and distinct questions.')
    if body.due_at <= max(now, body.opens_at) or body.solutions_at < body.due_at:
        raise HTTPException(422, 'The deadline must follow the opening time; release solutions at or after the deadline.')
    if body.due_at > now + timedelta(days=366) or body.solutions_at > body.due_at + timedelta(days=90):
        raise HTTPException(422, 'Schedule within one year and release solutions within 90 days of closing.')
    rooms = [owned_class(db, cid, user) for cid in sorted(set(body.classroom_ids))]
    recipients = sorted({uid for (uid,) in db.query(m.ClassroomMember.user_id).join(m.User, m.User.id == m.ClassroomMember.user_id).filter(
        m.ClassroomMember.classroom_id.in_([r.id for r in rooms]), m.ClassroomMember.active.is_(True), m.User.status == 'active').all()})
    if not recipients:
        raise HTTPException(409, 'Ask students to join a selected class before publishing.')
    questions = {q.id: q for q in question_query(db).filter(m.Question.id.in_(body.question_ids)).all()}
    if len(questions) != len(body.question_ids):
        raise HTTPException(409, 'Some selected questions are no longer published. Refresh the question bank.')
    versions = dict(db.query(m.QuestionRevision.question_id, func.max(m.QuestionRevision.version)).filter(
        m.QuestionRevision.question_id.in_(body.question_ids)).group_by(m.QuestionRevision.question_id).all())
    if len(versions) != len(questions):
        raise HTTPException(409, 'A selected question has no revision record. Choose another question.')
    frozen = [freeze(questions[qid], versions[qid]) for qid in body.question_ids]
    test = m.Test(title='Class test: ' + body.title.strip(), kind='chapter', pattern='jee_main', duration_sec=body.duration_minutes * 60,
        ranked=False, created_by=user.id, opens_at=body.opens_at, closes_at=body.due_at, results_at=body.solutions_at)
    db.add(test)
    db.flush()
    assignment = m.TeachingAssignment(teacher_id=user.id, test_id=test.id, title=body.title.strip(), instructions=body.instructions.strip(),
        opens_at=body.opens_at, due_at=body.due_at, solutions_at=body.solutions_at, duration_sec=test.duration_sec,
        marks_correct=body.marks_correct, marks_wrong=body.marks_wrong, questions=frozen, question_count=len(frozen), created_at=now, request_key=body.request_key)
    db.add(assignment)
    db.flush()
    for index, question in enumerate(frozen):
        db.add(m.TestQuestion(test_id=test.id, question_id=question['question_id'], position=index + 1,
            marks_correct=body.marks_correct, marks_wrong=body.marks_wrong, partial_marking=False))
    for room in rooms:
        db.add(m.AssignmentClassroom(assignment_id=assignment.id, classroom_id=room.id))
    href = f'/assignments/{assignment.id}'
    for uid in recipients:
        db.add(m.AssignmentRecipient(assignment_id=assignment.id, user_id=uid, draft=[]))
        notify(db, uid, 'New test: ' + assignment.title, 'Your teacher has assigned a test. Check the opening time and deadline.', href, 'assigned', assignment.id)
        reminder = assignment.due_at - timedelta(hours=1)
        if reminder > max(now, assignment.opens_at):
            notify(db, uid, 'Due soon: ' + assignment.title, 'One hour left to finish your class test.', href, 'reminder', assignment.id, reminder)
        notify(db, uid, 'Solutions ready: ' + assignment.title, 'Review your answers and work through the explanations.', href, 'solutions', assignment.id, assignment.solutions_at)
    notify(db, user.id, 'Test closed: ' + assignment.title, 'Open your class report to review submissions and topic accuracy.',
        f'/teacher?report={assignment.id}', 'closed', assignment.id, assignment.due_at)
    db.commit()
    return {'id': assignment.id, 'title': assignment.title, 'recipients': len(recipients)}


def assignment_summary(a):
    return {'id': a.id, 'title': a.title, 'instructions': a.instructions, 'opens_at': stamp(a.opens_at), 'due_at': stamp(a.due_at),
        'solutions_at': stamp(a.solutions_at), 'duration_sec': a.duration_sec, 'question_count': a.question_count,
        'max_score': a.question_count * a.marks_correct, 'marks_correct': a.marks_correct, 'marks_wrong': a.marks_wrong}


def member_assignment_ids(db, uid):
    return db.query(m.AssignmentClassroom.assignment_id).join(m.ClassroomMember,
        m.ClassroomMember.classroom_id == m.AssignmentClassroom.classroom_id).filter(m.ClassroomMember.user_id == uid, m.ClassroomMember.active.is_(True))


def student_assignment(db, aid, uid):
    a = db.query(m.TeachingAssignment).filter(m.TeachingAssignment.id == aid, m.TeachingAssignment.id.in_(member_assignment_ids(db, uid))).first()
    r = db.get(m.AssignmentRecipient, (aid, uid)) if a else None
    if not a or not r:
        raise HTTPException(404, 'Assignment not found in your classes.')
    return a, r


def deadline(a, attempt):
    return min(a.due_at, naive(attempt.started_at) + timedelta(seconds=a.duration_sec))


def status_for(a, r, attempt=None):
    if attempt and attempt.submitted_at is not None:
        return 'submitted'
    if utcnow() >= a.due_at or (attempt and utcnow() >= deadline(a, attempt)):
        return 'expired'
    if attempt:
        return 'in_progress'
    return 'upcoming' if utcnow() < a.opens_at else 'not_started'


def student_payload(a, r, attempt=None):
    data = {**assignment_summary(a), 'status': status_for(a, r, attempt), 'server_now': stamp(utcnow()),
        'draft_version': r.draft_version, 'saved_at': stamp(r.saved_at)}
    if attempt:
        data.update({'attempt_id': attempt.id, 'deadline': stamp(deadline(a, attempt)), 'answers': r.draft,
            'questions': [safe_question(q) for q in a.questions]})
    if r.result is not None:
        data['result'] = {k: v for k, v in r.result.items() if k != 'questions'}
        data['solutions_released'] = utcnow() >= a.solutions_at
        if data['solutions_released']:
            data['result']['questions'] = r.result['questions']
    return data


class DraftIn(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    version: int = Field(ge=0)
    answers: list[schemas.SubjectTestAnswerIn] = Field(default_factory=list, max_length=100)


def validated_answers(a, body):
    import math
    questions = {q['question_id']: q for q in a.questions}
    seen = set()
    for ans in body.answers:
        q = questions.get(ans.question_id)
        if not q or ans.question_id in seen:
            raise HTTPException(422, 'Answers must refer to distinct questions in this test.')
        seen.add(ans.question_id)
        if ans.numeric_answer is not None and not math.isfinite(ans.numeric_answer):
            raise HTTPException(422, 'Enter a finite numeric answer.')
        if len(set(ans.option_ids)) != len(ans.option_ids) or not set(ans.option_ids).issubset({o['id'] for o in q['options']}):
            raise HTTPException(422, 'An answer contains invalid options.')
        if (q['type'] == 'numerical' and ans.option_ids) or (q['type'] != 'numerical' and ans.numeric_answer is not None) or (q['type'] == 'single_correct' and len(ans.option_ids) > 1):
            raise HTTPException(422, 'An answer does not match its question type.')
    return [ans.model_dump() for ans in body.answers]


def finalize(db, a, r, attempt):
    """Caller holds the student's user lock. Draft and frozen key are authoritative."""
    if r.result is not None:
        return
    # Practice grading serializes mastery updates through the student profile.
    db.query(m.StudentProfile).filter_by(user_id=r.user_id).with_for_update().populate_existing().first()
    answers = {v['question_id']: schemas.SubjectTestAnswerIn(**v) for v in r.draft}
    results, subjects = [], {}
    correct = attempted = total_marks = total_time = 0
    stats = {s.subtopic_id: s for s in db.query(m.StudentSubtopicStats).filter(m.StudentSubtopicStats.user_id == r.user_id,
        m.StudentSubtopicStats.subtopic_id.in_({q['subtopic_id'] for q in a.questions})).with_for_update().all()}
    for q in a.questions:
        ans = answers.get(q['question_id'], schemas.SubjectTestAnswerIn(question_id=q['question_id']))
        question = SimpleNamespace(type=q['type'], answer_min=q['answer_min'], answer_max=q['answer_max'], options=[SimpleNamespace(**o) for o in q['options']])
        outcome, correct_ids = _grade_one(question, ans)
        marks = a.marks_correct if outcome == 'correct' else -a.marks_wrong if outcome == 'wrong' else 0
        time_taken = min(ans.time_taken_sec, a.duration_sec)
        db.add(m.QuestionResponse(attempt_id=attempt.id, user_id=r.user_id, question_id=q['question_id'], question_version=q['version'],
            numeric_answer=ans.numeric_answer, outcome=outcome, marks_awarded=marks, time_taken_sec=time_taken))
        # Selections live in the immutable result/draft, independent of mutable bank options.
        results.append({'question_id': q['question_id'], 'outcome': outcome, 'marks_awarded': marks,
            'correct_option_ids': sorted(correct_ids), 'answer_min': q['answer_min'], 'answer_max': q['answer_max'], 'solution': q['solution']})
        correct += int(outcome == 'correct')
        attempted += int(outcome != 'skipped')
        total_marks += marks
        total_time += time_taken
        topic = stats.get(q['subtopic_id'])
        if not topic:
            topic = m.StudentSubtopicStats(user_id=r.user_id, subtopic_id=q['subtopic_id'], attempted=0, correct=0)
            db.add(topic)
            stats[q['subtopic_id']] = topic
        if outcome != 'skipped':
            topic.attempted += 1
            topic.correct += int(outcome == 'correct')
            topic.mastery = topic.correct / topic.attempted
            topic.last_attempted_at = utcnow()
        subject = subjects.setdefault(q['subject'], {'total': 0, 'correct': 0})
        subject['total'] += 1
        subject['correct'] += int(outcome == 'correct')
    attempt.submitted_at = utcnow()
    attempt.score, attempt.total_questions = total_marks, len(a.questions)
    attempt.accuracy = round(100 * correct / attempted, 2) if attempted else 0
    attempt.avg_time_seconds = round(total_time / len(a.questions), 2)
    attempt.subject_breakdown = subjects
    r.result = {'score': total_marks, 'max_score': a.marks_correct * len(a.questions), 'correct': correct,
        'attempted': attempted, 'accuracy': attempt.accuracy, 'submitted_at': stamp(attempt.submitted_at), 'questions': results}


def expire_saved(db, a, r):
    attempt = db.get(m.TestAttempt, r.attempt_id) if r.attempt_id else None
    if attempt and r.result is None and utcnow() >= deadline(a, attempt):
        finalize(db, a, r, attempt)
    return attempt


@router.get('/classrooms')
def student_classes(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    lock_user(db, user.id)
    rooms = db.query(m.Classroom, m.User.name).join(m.ClassroomMember, m.ClassroomMember.classroom_id == m.Classroom.id).join(m.User, m.User.id == m.Classroom.teacher_id).filter(
        m.ClassroomMember.user_id == user.id, m.ClassroomMember.active.is_(True)).all()
    rows = db.query(m.TeachingAssignment, m.AssignmentRecipient, m.TestAttempt).options(defer(m.TeachingAssignment.questions), defer(m.AssignmentRecipient.draft), defer(m.AssignmentRecipient.result)).join(m.AssignmentRecipient, m.AssignmentRecipient.assignment_id == m.TeachingAssignment.id).outerjoin(m.TestAttempt, m.TestAttempt.id == m.AssignmentRecipient.attempt_id).filter(
        m.AssignmentRecipient.user_id == user.id, m.TeachingAssignment.id.in_(member_assignment_ids(db, user.id))).order_by(m.TeachingAssignment.due_at.desc()).limit(100).all()
    assignments = []
    for a, r, attempt in rows:
        if attempt and not attempt.submitted_at and utcnow() >= deadline(a, attempt):
            expire_saved(db, a, r)
        assignments.append({**assignment_summary(a), 'status': status_for(a, r, attempt), 'score': attempt.score if attempt and attempt.submitted_at else None})
    db.commit()
    return {'classes': [{'id': r.id, 'name': r.name, 'teacher': name} for r, name in rooms], 'assignments': assignments}


@router.get('/assignments/{assignment_id}')
def get_assignment(assignment_id: int, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    lock_user(db, user.id)
    a, r = student_assignment(db, assignment_id, user.id)
    attempt = expire_saved(db, a, r)
    db.commit()
    return student_payload(a, r, attempt)


@router.post('/assignments/{assignment_id}/start')
def start_assignment(assignment_id: int, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    lock_user(db, user.id)
    a, r = student_assignment(db, assignment_id, user.id)
    attempt = expire_saved(db, a, r)
    if not attempt:
        if not a.opens_at <= utcnow() < a.due_at:
            raise HTTPException(409, 'This test is not open for attempts.')
        attempt = m.TestAttempt(user_id=user.id, test_id=a.test_id, started_at=utcnow(), attempt_number=1, counts_for_rank=False)
        db.add(attempt)
        db.flush()
        r.attempt_id = attempt.id
    db.commit()
    return student_payload(a, r, attempt)


def write_draft(assignment_id, body, user, db, submit):
    lock_user(db, user.id)
    a, r = student_assignment(db, assignment_id, user.id)
    attempt = db.get(m.TestAttempt, r.attempt_id) if r.attempt_id else None
    if not attempt:
        raise HTTPException(409, 'Start the test first.')
    if r.result is not None:
        return student_payload(a, r, attempt)
    if utcnow() >= deadline(a, attempt):
        finalize(db, a, r, attempt)
    else:
        if body.version != r.draft_version:
            raise HTTPException(409, 'This test changed in another tab. Reload the saved attempt before continuing.')
        r.draft = validated_answers(a, body)
        r.draft_version += 1
        r.saved_at = utcnow()
        if submit:
            finalize(db, a, r, attempt)
    db.commit()
    if not submit and r.result is None:
        # Keystroke autosaves acknowledge only state; do not resend the whole paper.
        return {'status': 'in_progress', 'draft_version': r.draft_version,
            'saved_at': stamp(r.saved_at), 'server_now': stamp(utcnow()),
            'deadline': stamp(deadline(a, attempt))}
    return student_payload(a, r, attempt)


@router.put('/assignments/{assignment_id}/draft')
def save_draft(assignment_id: int, body: DraftIn, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    return write_draft(assignment_id, body, user, db, False)


@router.post('/assignments/{assignment_id}/submit')
def submit_assignment(assignment_id: int, body: DraftIn, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    return write_draft(assignment_id, body, user, db, True)


@router.get('/teacher/assignments')
def teacher_assignments(user=Depends(require_teacher), db: Session = Depends(get_db)):
    assignments = db.query(m.TeachingAssignment).options(defer(m.TeachingAssignment.questions)).filter_by(teacher_id=user.id).order_by(m.TeachingAssignment.created_at.desc()).limit(100).all()
    counts = {aid: (count, submitted) for aid, count, submitted in db.query(m.AssignmentRecipient.assignment_id, func.count(),
        func.count(m.TestAttempt.submitted_at)).outerjoin(m.TestAttempt, m.TestAttempt.id == m.AssignmentRecipient.attempt_id).filter(
        m.AssignmentRecipient.assignment_id.in_([a.id for a in assignments])).group_by(m.AssignmentRecipient.assignment_id).all()}
    return {'assignments': [{**assignment_summary(a), 'recipients': counts.get(a.id, (0, 0))[0],
        'submitted': counts.get(a.id, (0, 0))[1]} for a in assignments]}


@router.get('/teacher/assignments/{assignment_id}/report')
def assignment_report(assignment_id: int, user=Depends(require_teacher), db: Session = Depends(get_db)):
    a = db.query(m.TeachingAssignment).filter_by(id=assignment_id, teacher_id=user.id).first()
    if not a:
        raise HTTPException(404, 'Assignment not found.')
    # Finalize timed-out saved drafts individually; each transaction keeps the
    # student lock order used by practice grading. Never accepts late answers.
    aid, teacher_id = a.id, user.id
    db.commit()
    candidates = db.query(m.AssignmentRecipient, m.TestAttempt).join(m.TestAttempt, m.TestAttempt.id == m.AssignmentRecipient.attempt_id).filter(
        m.AssignmentRecipient.assignment_id == aid, m.TestAttempt.submitted_at.is_(None)).order_by(m.AssignmentRecipient.user_id).all()
    ids = [r.user_id for r, attempt in candidates if utcnow() >= deadline(a, attempt)]
    db.commit()
    for uid in ids:
        lock_user(db, uid, allow_inactive=True)
        access = db.get(m.TeacherAccess, teacher_id, populate_existing=True)
        if not access or not access.active:
            raise HTTPException(403, 'Teacher access has been removed.')
        r = db.get(m.AssignmentRecipient, (aid, uid), populate_existing=True)
        a = db.get(m.TeachingAssignment, aid)
        expire_saved(db, a, r)
        db.commit()
    a = db.get(m.TeachingAssignment, aid)
    rows = db.query(m.AssignmentRecipient, m.User, m.TestAttempt).join(m.User, m.User.id == m.AssignmentRecipient.user_id).outerjoin(m.TestAttempt,
        m.TestAttempt.id == m.AssignmentRecipient.attempt_id).filter(m.AssignmentRecipient.assignment_id == aid).order_by(m.User.name).all()
    students, questions, topics = [], {}, {}
    for r, student, attempt in rows:
        students.append({'id': student.id, 'name': student.name, 'username': student.username, 'status': status_for(a, r, attempt),
            'score': r.result['score'] if r.result else None, 'accuracy': r.result['accuracy'] if r.result else None,
            'submitted_at': r.result['submitted_at'] if r.result else None})
        if r.result:
            for result, q in zip(r.result['questions'], a.questions):
                for target, key in ((questions, q['question_id']), (topics, q['subject'] + ' · ' + q['topic'])):
                    item = target.setdefault(key, {'correct': 0, 'responses': 0})
                    item['responses'] += 1
                    item['correct'] += int(result['outcome'] == 'correct')
    return {**assignment_summary(a), 'students': students,
        'questions': [{**q, **questions.get(q['question_id'], {'correct': 0, 'responses': 0})} for q in a.questions],
        'topics': [{'name': key, **value, 'accuracy': round(value['correct'] * 100 / value['responses'])} for key, value in topics.items()]}


def inbox_query(db, uid):
    # Scheduled rows become visible on the next poll; no background worker is required.
    r = m.AssignmentRecipient
    base = db.query(m.ClassroomNotification).outerjoin(r, (r.assignment_id == m.ClassroomNotification.assignment_id) & (r.user_id == uid)).filter(
        m.ClassroomNotification.user_id == uid, m.ClassroomNotification.available_at <= utcnow())
    member_ids = member_assignment_ids(db, uid)
    return base.filter(or_(m.ClassroomNotification.assignment_id.is_(None), m.ClassroomNotification.kind == 'closed',
        m.ClassroomNotification.assignment_id.in_(member_ids))).filter(or_(m.ClassroomNotification.kind != 'reminder',
        (or_(r.attempt_id.is_(None), r.attempt_id.in_(db.query(m.TestAttempt.id).filter(m.TestAttempt.submitted_at.is_(None))))) & (m.ClassroomNotification.assignment_id.in_(db.query(m.TeachingAssignment.id).filter(m.TeachingAssignment.due_at > utcnow()))))).filter(
        or_(m.ClassroomNotification.kind != 'solutions', r.attempt_id.in_(db.query(m.TestAttempt.id).filter(m.TestAttempt.submitted_at.isnot(None)))))


@router.get('/notifications')
def notifications(account: m.AuthAccount = Depends(get_auth_account), db: Session = Depends(get_db)):
    if not account.user_id:
        return {'items': [], 'unread_count': 0, 'teacher': False}
    access = db.get(m.TeacherAccess, account.user_id)
    query = inbox_query(db, account.user_id)
    if not access or not access.active:
        query = query.filter(m.ClassroomNotification.kind != 'closed')
    count = query.filter(m.ClassroomNotification.read_at.is_(None)).count()
    rows = query.order_by(m.ClassroomNotification.available_at.desc(), m.ClassroomNotification.id.desc()).limit(50).all()
    return {'teacher': bool(access and access.active), 'unread_count': count, 'items': [
        {'id': n.id, 'title': n.title, 'body': n.body, 'href': n.href, 'read': n.read_at is not None, 'created_at': stamp(n.available_at)} for n in rows]}


@router.post('/notifications/{notification_id}/read')
def read_notification(notification_id: int, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    row = inbox_query(db, user.id).filter(m.ClassroomNotification.id == notification_id).first()
    if not row:
        raise HTTPException(404, 'Notification not found.')
    row.read_at = row.read_at or utcnow()
    db.commit()
    return {'read': True}
