"""Admin directories stay private, bounded and accurate with mixed account types."""
import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import datetime
import pytest
from app import models as m
from app.routers.admin_dashboard import router, _require_admin, IST
from test_public_papers import setup as base_setup

@pytest.fixture
def setup(base_setup):
    client, app, factory = base_setup
    app.include_router(router)
    app.dependency_overrides[_require_admin] = lambda: 'admin-test'
    now = datetime.utcnow()
    with factory() as db:
        db.add(m.User(id=2, auth0_sub='teacher-test', username='mentor', name='Teacher', email='mentor@example.com'))
        db.add(m.TeacherAccess(user_id=2, active=True, granted_at=now))
        db.add(m.AuthAccount(id='pending', email='pending@example.com', password_hash='PRIVATE_HASH', created_at=now))
        db.add(m.Classroom(id=1, teacher_id=2, name='PCM batch', join_code='PRIVATE_CODE', created_at=now))
        db.add(m.Classroom(id=2, teacher_id=2, name='Empty batch', join_code='PRIVATE_CODE_2', created_at=now))
        db.add(m.ClassroomMember(classroom_id=1, user_id=1, joined_at=now, active=True))
        db.add(m.ClassroomMember(classroom_id=2, user_id=1, joined_at=now, active=False))
        db.add(m.QuestionReport(question_id=1, user_id=1, reason='Wrong sign in the answer', status='open'))
        db.add(m.ImportRun(file_path='/private/secret-path', file_hash='a'*64, added=3, updated=2, errors={'private':'secret'}))
        db.commit()
    return client, app, factory

@pytest.mark.parametrize('path', ['dashboard','users','questions','paper-coverage','classrooms','operations','registrations'])
def test_all_console_data_requires_admin(setup, path):
    client, app, _ = setup
    app.dependency_overrides.pop(_require_admin)
    assert client.get('/api/admin/'+path).status_code == 401


def test_profiles_have_distinct_teacher_filter_and_stable_omr_search(setup):
    client, _, _ = setup
    response = client.get('/api/admin/users?role=teacher')
    assert response.headers['cache-control'] == 'no-store'
    teacher = response.json()['items'][0]
    assert teacher['role'] == 'teacher' and teacher['username'] == 'mentor'
    assert client.get('/api/admin/users?role=student').json()['total'] == 1
    result = client.get('/api/admin/users?q=0000000001').json()
    assert result['total'] == 1 and result['items'][0]['omr_id'] == '0000000001'
    assert client.get('/api/admin/users?q=²').status_code == 200
    assert client.get('/api/admin/users?q=%25').json()['total'] == 0  # Literal %, not a wildcard.
    assert client.get('/api/admin/users?q=mentor%40example.com').json()['total'] == 1
    for endpoint in ('users','questions','paper-coverage','classrooms','operations','registrations'):
        assert client.get('/api/admin/'+endpoint+'?limit=101').status_code == 422
        assert client.get('/api/admin/'+endpoint+'?offset=-1').status_code == 422
    assert client.get('/api/admin/users?role=owner').status_code == 422
    assert 'PRIVATE_HASH' not in response.text and 'auth0_sub' not in response.text


def test_inventory_filters_and_paper_coverage_count_drafts_separately(setup):
    client, _, _ = setup
    first = client.get('/api/admin/questions?exam=mht_cet&status=published&kind=single_correct&limit=2').json()
    second = client.get('/api/admin/questions?exam=mht_cet&status=published&kind=single_correct&limit=2&offset=2').json()
    assert first['total'] == 4 and len(first['items']) == 2
    assert not {r['id'] for r in first['items']} & {r['id'] for r in second['items']}
    assert client.get('/api/admin/questions?q=PUBLIC-5').json()['items'][0]['status'] == 'draft'
    assert client.get('/api/admin/questions?status=delete').status_code == 422
    assert client.get('/api/admin/questions?kind=essay').status_code == 422
    rows = client.get('/api/admin/paper-coverage?exam=mht_cet').json()
    assert rows['total'] == 1
    assert rows['items'][0]['total'] == 5 and rows['items'][0]['published'] == 4
    assert 'solution' not in str(first) and 'is_correct' not in str(first)


def test_classes_include_zero_enrolments_and_queues_hide_internal_data(setup):
    client, _, _ = setup
    classes = client.get('/api/admin/classrooms?q=mentor').json()
    assert classes['total'] == 2
    assert {r['name']:r['members'] for r in classes['items']} == {'PCM batch':1,'Empty batch':0}
    assert 'PRIVATE_CODE' not in str(classes)
    reports = client.get('/api/admin/operations?queue=reports').json()
    assert reports['total'] == 1 and reports['items'][0]['reference'] == 'PUBLIC-1'
    imports = client.get('/api/admin/operations?queue=imports')
    assert imports.json()['items'][0]['status'] == 'has_errors'
    assert 'secret' not in imports.text and '/private/' not in imports.text
    assert client.get('/api/admin/operations?queue=scans').json()['items'] == []
    assert client.get('/api/admin/operations?queue=arbitrary').status_code == 422


def test_overview_handles_empty_activity_and_daily_completion_ownership(setup):
    client, _, factory = setup
    response = client.get('/api/admin/dashboard')
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['overview']['student_users'] == 1
    assert data['overview']['teacher_users'] == 1 and data['overview']['pending_profiles'] == 1
    assert data['teaching']['students'] == 1 and data['teaching']['memberships'] == 1
    assert len(data['growth']) == 14 and data['overview']['average_accuracy'] == 0
    now = datetime.utcnow()
    with factory() as db:
        db.add(m.Test(id=100, title='Daily', kind='daily', pattern='jee_main', duration_sec=60))
        db.flush()
        db.add(m.DailyQuestionAssignment(user_id=1, question_id=1, assigned_date=datetime.now(IST).date(), test_id=100))
        db.add(m.TestAttempt(user_id=2, test_id=100, attempt_number=1, started_at=now, submitted_at=now))
        db.commit()
    assert client.get('/api/admin/dashboard').json()['daily']['completed_today'] == 0
    with factory() as db:
        for number in (1,2):
            db.add(m.TestAttempt(user_id=1, test_id=100, attempt_number=number, started_at=now, submitted_at=now))
        db.commit()
    daily = client.get('/api/admin/dashboard').json()['daily']
    assert daily == {'assigned_today':1,'completed_today':1,'completion_rate':100.0}


def test_signup_directory_includes_unfinished_accounts_without_secrets(setup):
    client, _, _ = setup
    response = client.get('/api/admin/registrations?state=pending&q=pending')
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 1 and data['items'][0]['profile_id'] is None
    assert data['items'][0]['status'] == 'pending' and data['items'][0]['verified'] is False
    assert 'PRIVATE_HASH' not in response.text and 'password_hash' not in response.text
    assert client.get('/api/admin/registrations?state=complete').json()['total'] == 0
    assert client.get('/api/admin/registrations?state=invalid').status_code == 422
