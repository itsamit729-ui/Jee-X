"""Classroom authorization, snapshot grading, schedules and account onboarding."""
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
import pytest
from test_roadmap import setup
from app import models as m
from app.auth import get_auth_account, utcnow
from app.routers import teaching, admin_dashboard, users


@pytest.fixture
def classroom(setup):
    client, factory, active = setup
    factory.configure(autoflush=False)  # Match production session behavior.
    for router in (teaching.router, admin_dashboard.router, users.router):
        client.app.include_router(router)
    with factory() as db:
        for uid in (3, 4):
            db.add(m.User(id=uid, auth0_sub=str(uid), username=f'teacher{uid}', name=f'Teacher {uid}'))
        db.flush()
        for uid in (1, 2, 3, 4):
            db.add(m.AuthAccount(id=f'account-{uid}', email=f'person{uid}@example.com', password_hash='unused', user_id=uid, created_at=utcnow()))
        db.add(m.AuthAccount(id='new-teacher', email='new.teacher@example.com', password_hash='unused', created_at=utcnow()))
        db.commit()
    client.app.dependency_overrides[get_auth_account] = lambda: SimpleNamespace(user_id=active[0], id=f'account-{active[0]}')
    admin_dashboard._sessions['teacher-test-admin'] = time.time() + 3600
    yield client, factory, active
    admin_dashboard._sessions.pop('teacher-test-admin', None)


ADMIN = {'Authorization': 'Bearer teacher-test-admin'}


def grant(client, uid=3, enabled=True):
    response = client.put(f'/api/admin/teachers/account-{uid}', headers=ADMIN, json={'active': enabled})
    assert response.status_code == 200, response.text


def prepare(env):
    client, factory, active = env
    grant(client)
    active[0] = 3
    response = client.post('/api/teacher/classes', json={'name': 'JEE Main · Batch A'})
    assert response.status_code == 201, response.text
    room = response.json()
    active[0] = 1
    response = client.post('/api/classrooms/join', json={'code': room['join_code']})
    assert response.status_code == 200, response.text
    return room


def payload(room, **updates):
    now = utcnow()
    return {**{'title': 'Physics checkpoint', 'classroom_ids': [room['id']], 'question_ids': [100, 120],
        'opens_at': (now - timedelta(minutes=1)).isoformat() + 'Z', 'due_at': (now + timedelta(hours=2)).isoformat() + 'Z',
        'solutions_at': (now + timedelta(hours=2)).isoformat() + 'Z', 'duration_minutes': 30,
        'request_key': 'publish-request-00001'}, **updates}


def publish(env, room, **updates):
    client, _, active = env
    active[0] = 3
    response = client.post('/api/teacher/assignments', json=payload(room, **updates))
    assert response.status_code == 201, response.text
    active[0] = 1
    return response.json()['id']


def start(client, aid):
    response = client.post(f'/api/assignments/{aid}/start')
    assert response.status_code == 200, response.text
    return response.json()


def correct_answers(factory):
    with factory() as db:
        option = db.query(m.QuestionOption).filter_by(question_id=100, is_correct=True).one().id
    return [{'question_id': 100, 'option_ids': [option], 'time_taken_sec': 15}, {'question_id': 120, 'numeric_answer': 2, 'time_taken_sec': 20}]


def test_admin_only_grants_existing_accounts_and_audits(classroom):
    client, factory, active = classroom
    assert client.get('/api/admin/teachers').status_code == 401
    assert client.put('/api/admin/teachers/account-1', json={'active': True}).status_code == 401
    assert client.get('/api/teacher/classes').status_code == 403
    grant(client, 3)
    grant(client, 3)  # idempotent
    result = client.get('/api/admin/teachers?q=person3', headers=ADMIN).json()['accounts']
    assert len(result) == 1 and result[0]['active']
    assert client.get('/api/admin/teachers?q=%', headers=ADMIN).json()['accounts'] == []
    with factory() as db:
        audit = db.query(m.AuditLog).filter_by(entity_id=3).all()
        assert len(audit) == 1 and audit[0].actor_id is None
        assert 'teacher-test-admin' not in audit[0].reason
        assert db.get(m.User, 3).role == 'student'
    active[0] = 3
    assert client.get('/api/classrooms/access').json()['teacher']
    grant(client, 3, False)
    assert client.get('/api/teacher/questions').status_code == 403
    assert not client.get('/api/classrooms/access').json()['teacher']


def test_teacher_account_can_skip_student_profile_and_complete_it_later(classroom):
    client, factory, active = classroom
    result = client.put('/api/admin/teachers/new-teacher', json={'active': True}, headers=ADMIN)
    assert result.status_code == 200, result.text
    uid = result.json()['user_id']
    active[0] = uid
    client.app.dependency_overrides[get_auth_account] = lambda: SimpleNamespace(user_id=uid, id='new-teacher')
    assert client.get('/api/teacher/classes').status_code == 200
    assert client.get('/api/classrooms/access').json() == {'teacher': True, 'student_profile': False, 'has_profile': True}
    with factory() as db:
        account = db.get(m.AuthAccount, 'new-teacher')
        assert account.user_id == uid and db.get(m.User, uid).student_profile is None
    response = client.post('/api/onboarding', json={'username': 'actual_teacher', 'name': 'Actual Teacher', 'dob': '2000-01-01', 'class_level': 'dropper'})
    assert response.status_code == 201, response.text
    assert client.get('/api/classrooms/access').json()['student_profile']
    assert client.get('/api/classrooms/access').json()['teacher']


def test_class_ownership_membership_and_revocation(classroom):
    client, factory, active = classroom
    room = prepare(classroom)
    assert client.post('/api/classrooms/join', json={'code': room['join_code'].lower()}).status_code == 200
    with factory() as db:
        assert db.query(m.ClassroomMember).count() == 1
    grant(client, 4)
    active[0] = 4
    assert client.delete(f"/api/teacher/classes/{room['id']}/members/1").status_code == 404
    assert client.post('/api/teacher/assignments', json=payload(room)).status_code == 404
    active[0] = 3
    assert client.post('/api/classrooms/join', json={'code': room['join_code']}).status_code == 400
    client.delete(f"/api/teacher/classes/{room['id']}/members/1")
    active[0] = 1
    assert client.post('/api/classrooms/join', json={'code': room['join_code']}).status_code == 403
    active[0] = 3
    assert client.post(f"/api/teacher/classes/{room['id']}/members/1/restore").status_code == 200
    grant(client, 3, False)
    active[0] = 2
    assert client.post('/api/classrooms/join', json={'code': room['join_code']}).status_code == 404
    with factory() as db:
        assert db.get(m.Classroom, room['id']) is not None


def test_frozen_paper_grading_solution_release_and_learning_evidence(classroom, monkeypatch):
    client, factory, active = classroom
    room = prepare(classroom)
    aid = publish(classroom, room)
    paper = start(client, aid)
    assert start(client, aid)['attempt_id'] == paper['attempt_id']
    assert 'solution' not in str(paper['questions']) and 'is_correct' not in str(paper['questions'])
    assert all('answer_min' not in q for q in paper['questions'])
    answers = correct_answers(factory)
    with factory() as db:
        db.get(m.Question, 120).answer_min = 5
        db.get(m.Question, 120).answer_max = 5
        db.get(m.Question, 120).stem = 'Changed after publication'
        db.query(m.QuestionOption).filter_by(question_id=100).update({'is_correct': False})
        db.commit()
    generic = client.post(f"/api/subject-tests/attempts/{paper['attempt_id']}/submit", json={'answers': answers})
    assert generic.status_code == 403, generic.text
    saved = client.put(f'/api/assignments/{aid}/draft', json={'version': 0, 'answers': answers})
    assert saved.status_code == 200, saved.text
    assert saved.json()['draft_version'] == 1
    assert 'questions' not in saved.json()  # Autosave does not re-download the paper.
    resumed = client.get(f'/api/assignments/{aid}').json()
    assert resumed['answers'][1]['numeric_answer'] == 2
    assert resumed['questions'][1]['stem'] == 'Question'
    assert client.put(f'/api/assignments/{aid}/draft', json={'version': 0, 'answers': []}).status_code == 409
    response = client.post(f'/api/assignments/{aid}/submit', json={'version': 1, 'answers': answers})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['result']['score'] == 8 and not data['solutions_released']
    assert 'questions' not in data['result'] and 'correct_option_ids' not in str(data)
    assert client.post(f'/api/assignments/{aid}/submit', json={'version': 0, 'answers': []}).json()['result']['score'] == 8
    with factory() as db:
        assert db.query(m.QuestionResponse).filter_by(attempt_id=paper['attempt_id']).count() == 2
        stats = db.get(m.StudentSubtopicStats, (1, 1))
        assert stats.attempted == stats.correct == 2
        assert db.get(m.TestAttempt, paper['attempt_id']).test.kind == 'chapter'
        db.get(m.TeachingAssignment, aid).solutions_at = utcnow() - timedelta(seconds=1)
        db.commit()
    released = client.get(f'/api/assignments/{aid}').json()
    assert released['solutions_released'] and released['result']['questions'][1]['answer_min'] == 2
    active[0] = 2
    assert client.get(f'/api/assignments/{aid}').status_code == 404
    grant(client, 4)
    active[0] = 4
    assert client.get(f'/api/teacher/assignments/{aid}/report').status_code == 404
    active[0] = 3
    report = client.get(f'/api/teacher/assignments/{aid}/report')
    assert report.status_code == 200, report.text
    assert report.json()['students'][0]['score'] == 8
    assert report.json()['topics'][0]['accuracy'] == 100


def test_publish_dedup_retry_and_frozen_roster(classroom):
    client, factory, active = classroom
    room = prepare(classroom)
    active[0] = 3
    room2 = client.post('/api/teacher/classes', json={'name': 'Second class'}).json()
    active[0] = 1
    client.post('/api/classrooms/join', json={'code': room2['join_code']})
    aid = publish(classroom, room, classroom_ids=[room['id'], room2['id']])
    active[0] = 3
    retry = client.post('/api/teacher/assignments', json=payload(room))
    assert retry.json()['id'] == aid
    with factory() as db:
        assert db.query(m.AssignmentRecipient).count() == 1
        assert db.query(m.TeachingAssignment).count() == 1
        assert db.query(m.ClassroomNotification).filter_by(kind='assigned').count() == 1
    active[0] = 2
    client.post('/api/classrooms/join', json={'code': room['join_code']})
    assert not client.get('/api/classrooms').json()['assignments']
    assert client.post(f'/api/assignments/{aid}/start').status_code == 404
    active[0] = 3
    client.delete(f"/api/teacher/classes/{room['id']}/members/1")
    active[0] = 1
    assert client.get(f'/api/assignments/{aid}').status_code == 200  # still in second class
    active[0] = 3
    client.delete(f"/api/teacher/classes/{room2['id']}/members/1")
    active[0] = 1
    assert client.get(f'/api/assignments/{aid}').status_code == 404
    assert not client.get('/api/notifications').json()['items']


@pytest.mark.parametrize('changes', [
    {'question_ids': [100, 100]}, {'question_ids': [99999]}, {'title': '   '},
    {'due_at': '2020-01-01T00:00:00Z'}, {'solutions_at': '2020-01-01T00:00:00Z'},
    {'opens_at': '2026-01-01T00:00:00'}, {'duration_minutes': 0},
])
def test_invalid_publication_is_atomic(classroom, changes):
    client, factory, active = classroom
    room = prepare(classroom)
    active[0] = 3
    response = client.post('/api/teacher/assignments', json=payload(room, **changes))
    assert response.status_code in (409, 422), response.text
    with factory() as db:
        assert db.query(m.TeachingAssignment).count() == 0
        assert db.query(m.AssignmentRecipient).count() == 0
        assert db.query(m.Test).count() == 0


@pytest.mark.parametrize('answers', [
    [{'question_id': 999}], [{'question_id': 100, 'option_ids': [999999]}],
    [{'question_id': 100}, {'question_id': 100}], [{'question_id': 100, 'numeric_answer': 1}],
    [{'question_id': 120, 'option_ids': [1]}],
])
def test_invalid_answers_do_not_change_draft(classroom, answers):
    client, factory, active = classroom
    aid = publish(classroom, prepare(classroom))
    start(client, aid)
    response = client.put(f'/api/assignments/{aid}/draft', json={'version': 0, 'answers': answers})
    assert response.status_code == 422, response.text
    assert client.get(f'/api/assignments/{aid}').json()['draft_version'] == 0


def test_deadlines_grade_saved_draft_not_late_payload(classroom):
    client, factory, active = classroom
    aid = publish(classroom, prepare(classroom))
    paper = start(client, aid)
    answers = correct_answers(factory)
    client.put(f'/api/assignments/{aid}/draft', json={'version': 0, 'answers': answers[:1]})
    with factory() as db:
        db.get(m.TestAttempt, paper['attempt_id']).started_at = utcnow() - timedelta(hours=1)
        db.commit()
    submitted = client.post(f'/api/assignments/{aid}/submit', json={'version': 1, 'answers': answers})
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()['result']['score'] == 4
    assert submitted.json()['result']['attempted'] == 1
    assert submitted.json()['answers'][0]['question_id'] == 100


def test_report_finalizes_expired_saved_attempt_and_respects_due_time(classroom):
    client, factory, active = classroom
    room = prepare(classroom)
    aid = publish(classroom, room)
    paper = start(client, aid)
    client.put(f'/api/assignments/{aid}/draft', json={'version': 0, 'answers': correct_answers(factory)})
    with factory() as db:
        assignment = db.get(m.TeachingAssignment, aid)
        assignment.due_at = utcnow() - timedelta(seconds=1)
        db.commit()
    active[0] = 3
    report = client.get(f'/api/teacher/assignments/{aid}/report')
    assert report.status_code == 200, report.text
    assert report.json()['students'][0]['status'] == 'submitted'
    assert report.json()['students'][0]['score'] == 8
    active[0] = 1
    assert client.get('/api/classrooms').json()['assignments'][0]['status'] == 'submitted'


def test_future_open_and_unstarted_expiry(classroom, monkeypatch):
    client, factory, active = classroom
    room = prepare(classroom)
    now = utcnow()
    aid = publish(classroom, room, opens_at=(now + timedelta(minutes=20)).isoformat() + 'Z')
    assert client.get(f'/api/assignments/{aid}').json()['status'] == 'upcoming'
    assert client.post(f'/api/assignments/{aid}/start').status_code == 409
    with factory() as db:
        db.get(m.TeachingAssignment, aid).due_at = now - timedelta(seconds=1)
        db.commit()
    assert client.get(f'/api/assignments/{aid}').json()['status'] == 'expired'
    assert client.post(f'/api/assignments/{aid}/start').status_code == 409


def test_notifications_scheduling_read_ownership_and_reminder_suppression(classroom, monkeypatch):
    client, factory, active = classroom
    aid = publish(classroom, prepare(classroom))
    inbox = client.get('/api/notifications').json()
    assert inbox['unread_count'] == 1 and len(inbox['items']) == 1
    nid = inbox['items'][0]['id']
    active[0] = 2
    assert client.post(f'/api/notifications/{nid}/read').status_code == 404
    active[0] = 1
    assert client.post(f'/api/notifications/{nid}/read').status_code == 200
    assert client.get('/api/notifications').json()['unread_count'] == 0
    with factory() as db:
        db.query(m.ClassroomNotification).filter_by(kind='reminder').update({'available_at': utcnow() - timedelta(seconds=1)})
        db.commit()
    assert client.get('/api/notifications').json()['unread_count'] == 1
    start(client, aid)
    client.post(f'/api/assignments/{aid}/submit', json={'version': 0, 'answers': correct_answers(factory)})
    assert client.get('/api/notifications').json()['unread_count'] == 0
    with factory() as db:
        db.query(m.ClassroomNotification).filter_by(kind='solutions').update({'available_at': utcnow() - timedelta(seconds=1)})
        db.commit()
    assert any('Solutions ready' in n['title'] for n in client.get('/api/notifications').json()['items'])
    active[0] = 3
    assert not any('Test closed' in n['title'] for n in client.get('/api/notifications').json()['items'])
    with factory() as db:
        db.query(m.ClassroomNotification).filter_by(kind='closed').update({'available_at': utcnow() - timedelta(seconds=1)})
        db.commit()
    assert any('Test closed' in n['title'] for n in client.get('/api/notifications').json()['items'])
    grant(client, 3, False)
    assert not any('Test closed' in n['title'] for n in client.get('/api/notifications').json()['items'])


def test_join_rate_limit(classroom):
    client, _, _ = classroom
    for _ in range(15):
        assert client.post('/api/classrooms/join', json={'code': 'BADCODE'}).status_code == 404
    assert client.post('/api/classrooms/join', json={'code': 'BADCODE'}).status_code == 429


def test_teacher_routes_use_native_session_csrf_and_live_revocation(classroom, monkeypatch):
    from app.auth import COOKIE_NAME, digest
    from app.deps import get_current_db_user
    client, factory, active = classroom
    grant(client, 3)
    monkeypatch.setenv('PUBLIC_APP_URL', 'http://testserver')
    monkeypatch.setenv('CORS_ORIGINS', 'http://testserver')
    with factory() as db:
        db.get(m.AuthAccount, 'account-3').verified_at = utcnow()
        db.add(m.AuthSession(token_hash=digest('teacher-cookie'), account_id='account-3', csrf_token='csrf-test', expires_at=utcnow() + timedelta(hours=1)))
        db.commit()
    client.app.dependency_overrides.pop(get_auth_account)
    client.app.dependency_overrides.pop(get_current_db_user)
    assert client.get('/api/teacher/classes').status_code == 401
    client.cookies.set(COOKIE_NAME, 'teacher-cookie')
    assert client.get('/api/teacher/classes').status_code == 200
    assert client.post('/api/teacher/classes', json={'name': 'Unauthorized origin'}).status_code == 403
    headers = {'Origin': 'http://testserver', 'X-Jee-Request': '1', 'X-CSRF-Token': 'wrong'}
    assert client.post('/api/teacher/classes', headers=headers, json={'name': 'Wrong CSRF'}).status_code == 403
    headers['X-CSRF-Token'] = 'csrf-test'
    assert client.post('/api/teacher/classes', headers=headers, json={'name': 'Valid class'}).status_code == 201
    grant(client, 3, False)
    assert client.get('/api/teacher/classes').status_code == 403
    assert client.post('/api/teacher/classes', headers=headers, json={'name': 'After removal'}).status_code == 403
