"""Isolated auth integration tests; no production database or real email."""
import os
from datetime import timedelta
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/test')
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base, get_db
from app.auth import COOKIE_NAME, digest, utcnow
from app.routers import authentication, users, google_login
from app.services import authentication as service

PASSWORD = 'a long unique passphrase'
EMAIL = 'student@example.com'
HEADERS = {'Origin': 'https://school.example', 'X-Jee-Request': '1'}

@pytest.fixture
def env(monkeypatch):
    monkeypatch.delenv('REQUIRE_EMAIL_VERIFICATION', raising=False)
    monkeypatch.setenv('PUBLIC_APP_URL', 'https://school.example')
    monkeypatch.setenv('CORS_ORIGINS', 'https://school.example')
    monkeypatch.setenv('AUTH_COOKIE_SECURE', 'true')
    monkeypatch.setenv('AUTH_COOKIE_SAMESITE', 'lax')
    monkeypatch.setenv('AUTH_EMAIL_PROVIDER', 'brevo')
    monkeypatch.setenv('BREVO_API_KEY', 'test-key')
    monkeypatch.setenv('AUTH_EMAIL_FROM', 'hello@example.com')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    tables = [models.User.__table__, models.StudentProfile.__table__, models.ProfileAvatar.__table__,
              models.AuthAccount.__table__, models.AuthSession.__table__, models.AuthEmailToken.__table__, models.AuthRateLimit.__table__, models.GoogleIdentity.__table__]
    Base.metadata.create_all(engine, tables=tables)
    sessions = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(authentication.router)
    app.include_router(google_login.router)
    app.include_router(users.router)
    def database():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    sent = []
    monkeypatch.setattr(service, 'send_account_email', lambda email, purpose, token: sent.append((email, purpose, token)))
    with TestClient(app, base_url='https://school.example', headers=HEADERS) as client:
        yield client, sessions, sent, app
    engine.dispose()


def post(client, path, **body):
    return client.post('/api/auth/' + path, json=body)


def signup(env):
    client, sessions, sent, _ = env
    assert post(client, 'register', email=EMAIL, password=PASSWORD).status_code == 202
    return sent[-1][2]


def login(env):
    client, _, _, _ = env
    token = signup(env)
    assert post(client, 'verify-email', token=token).status_code == 200
    response = post(client, 'login', email=EMAIL, password=PASSWORD)
    assert response.status_code == 200, response.text
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    return response


def test_verified_login_hashed_secrets_and_cookie(env):
    client, sessions, sent, _ = env
    token = signup(env)
    assert post(client, 'login', email=EMAIL, password=PASSWORD).status_code == 403
    with sessions() as db:
        account = db.query(models.AuthAccount).one()
        assert account.password_hash.startswith('$argon2id$') and PASSWORD not in account.password_hash
        assert db.query(models.AuthEmailToken).one().token_hash == digest(token)
    assert post(client, 'verify-email', token=token).status_code == 200
    assert post(client, 'verify-email', token=token).status_code == 400
    response = post(client, 'login', email=EMAIL.upper(), password=PASSWORD)
    assert response.status_code == 200
    cookie = response.headers['set-cookie']
    assert all(flag in cookie for flag in ('HttpOnly', 'Secure', 'SameSite=lax', 'Path=/'))
    with sessions() as db:
        assert db.query(models.AuthSession).one().token_hash == digest(client.cookies.get(COOKIE_NAME))
    assert client.get('/api/auth/session').json()['authenticated'] is True
    assert client.get('/api/me').json()['onboarded'] is False


def test_origin_csrf_logout_and_legacy_bearer_rejected(env):
    client, _, _, app = env
    login(env)
    assert client.post('/api/auth/logout', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.post('/api/auth/logout', headers={'X-CSRF-Token': 'bad'}).status_code == 403
    with TestClient(app, base_url='https://school.example') as fresh:
        assert fresh.get('/api/me', headers={'Authorization': 'Bearer old-auth0-token'}).status_code == 401
        assert fresh.post('/api/auth/login', json={'email': EMAIL, 'password': PASSWORD}).status_code == 403
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/me').status_code == 401


def test_reset_revokes_all_sessions_and_token_is_single_use(env):
    client, sessions, sent, app = env
    login(env)
    old_cookie = client.cookies.get(COOKIE_NAME)
    assert post(client, 'forgot-password', email=EMAIL).status_code == 200
    token = sent[-1][2]
    new_password = 'my replacement long passphrase'
    assert post(client, 'reset-password', token=token, password=new_password).status_code == 200
    assert post(client, 'reset-password', token=token, password=new_password).status_code == 400
    with TestClient(app, base_url='https://school.example', headers=HEADERS) as other:
        other.cookies.set(COOKIE_NAME, old_cookie)
        assert other.get('/api/me').status_code == 401
    assert post(client, 'login', email=EMAIL, password=PASSWORD).status_code == 401
    assert post(client, 'login', email=EMAIL, password=new_password).status_code == 200
    with sessions() as db:
        assert db.query(models.AuthEmailToken).count() == 0


def test_fresh_profile_never_links_legacy_email(env):
    client, sessions, _, _ = env
    with sessions() as db:
        old = models.User(auth0_sub='auth0|legacy', email=EMAIL, username='oldstudent', name='Old Student')
        db.add(old); db.commit(); old_id = old.id
    login(env)
    response = client.post('/api/onboarding', json={'name': 'New Student', 'username': 'newstudent', 'dob': '2006-01-01', 'class_level': '12'})
    assert response.status_code == 201, response.text
    assert response.json()['id'] != old_id
    with sessions() as db:
        assert db.get(models.User, old_id).auth0_sub == 'auth0|legacy'
        assert db.query(models.AuthAccount).one().user_id == response.json()['id']
        assert db.query(models.User).count() == 2
    assert client.get('/api/me').json()['profile']['username'] == 'newstudent'
    assert client.post('/api/onboarding', json={'name': 'Other', 'username': 'another', 'dob': '2006-01-01', 'class_level': '12'}).status_code == 409


def test_expiry_disabled_and_password_change(env):
    client, sessions, _, _ = env
    login(env)
    old_cookie = client.cookies.get(COOKIE_NAME)
    assert post(client, 'change-password', current_password='incorrect', password='a different passphrase').status_code == 400
    response = post(client, 'change-password', current_password=PASSWORD, password='a different passphrase')
    assert response.status_code == 200
    assert client.cookies.get(COOKIE_NAME) != old_cookie
    with sessions() as db:
        assert db.get(models.AuthSession, digest(old_cookie)) is None
        db.query(models.AuthSession).one().expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get('/api/me').status_code == 401
    assert client.get('/api/auth/session').json()['authenticated'] is False
    assert post(client, 'login', email=EMAIL, password='a different passphrase').status_code == 200
    with sessions() as db:
        db.query(models.AuthAccount).one().disabled = True
        db.commit()
    assert client.get('/api/me').status_code == 401


def test_expired_link_generic_responses_and_shared_rate_limit(env):
    client, sessions, sent, app = env
    token = signup(env)
    with sessions() as db:
        db.query(models.AuthEmailToken).one().expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert post(client, 'verify-email', token=token).status_code == 400
    existing = post(client, 'register', email=EMAIL, password=PASSWORD)
    unknown = post(client, 'register', email='someone@example.com', password=PASSWORD)
    assert existing.json() == unknown.json()
    assert post(client, 'forgot-password', email=EMAIL).json() == post(client, 'forgot-password', email='nobody@example.com').json()
    for _ in range(8):
        assert post(client, 'login', email=EMAIL, password='wrong').status_code == 401
    with TestClient(app, base_url='https://school.example', headers=HEADERS) as other:
        response = post(other, 'login', email=EMAIL, password='wrong')
        assert response.status_code == 429 and 'retry-after' in response.headers


def test_mail_failure_rolls_back_new_account(env, monkeypatch):
    from fastapi import HTTPException
    client, sessions, _, _ = env
    def fail(*args):
        raise HTTPException(503, 'Email temporarily unavailable')
    monkeypatch.setattr(service, 'send_account_email', fail)
    assert post(client, 'register', email=EMAIL, password=PASSWORD).status_code == 503
    with sessions() as db:
        assert db.query(models.AuthAccount).count() == 0
        assert db.query(models.AuthEmailToken).count() == 0


def test_google_signin_uses_subject_and_does_not_take_password_account(env, monkeypatch):
    client, sessions, _, _ = env
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'secret')
    class Reply:
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): pass
        def json(self): return self.payload
    identity = {'sub': 'stable-google-id', 'email': 'google@example.com', 'email_verified': True}
    monkeypatch.setattr(google_login.requests, 'post', lambda *a, **kw: Reply({'access_token': 'fake'}))
    monkeypatch.setattr(google_login.requests, 'get', lambda *a, **kw: Reply(identity))

    def start():
        auth = client.get('/api/auth/google/start', follow_redirects=False)
        assert auth.status_code == 302
        from urllib.parse import parse_qs, urlsplit
        return parse_qs(urlsplit(auth.headers['location']).query)['state'][0]

    assert client.get('/api/auth/google/callback?code=one&state=wrong', follow_redirects=False).status_code == 303
    assert client.get('/api/auth/session').json()['authenticated'] is False
    state = start()
    reply = client.get(f'/api/auth/google/callback?code=one&state={state}', follow_redirects=False)
    assert reply.status_code == 303
    with sessions() as db:
        account = db.query(models.AuthAccount).filter_by(email='google@example.com').one()
        assert db.query(models.GoogleIdentity).one().account_id == account.id
    assert client.get('/api/auth/session').json()['authenticated'] is True

    state = start()
    assert client.get(f'/api/auth/google/callback?code=two&state={state}', follow_redirects=False).status_code == 303
    with sessions() as db:
        assert db.query(models.AuthAccount).filter_by(email='google@example.com').count() == 1

    identity.update(sub='another-sub', email='student@example.com')
    signup(env)
    state = start()
    result = client.get(f'/api/auth/google/callback?code=three&state={state}', follow_redirects=False)
    assert result.headers['location'].endswith('/login?google_error=existing')
    with sessions() as db:
        assert db.query(models.GoogleIdentity).count() == 1


def test_google_link_requires_password_session_and_csrf(env, monkeypatch):
    client, sessions, _, _ = env
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'secret')
    assert client.post('/api/auth/google/link').status_code == 401
    login(env)
    assert client.post('/api/auth/google/link', headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    result = client.post('/api/auth/google/link')
    assert result.status_code == 200
    from urllib.parse import parse_qs, urlsplit
    state = parse_qs(urlsplit(result.json()['url']).query)['state'][0]
    class Reply:
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): pass
        def json(self): return self.payload
    monkeypatch.setattr(google_login.requests, 'post', lambda *a, **kw: Reply({'access_token': 'fake'}))
    monkeypatch.setattr(google_login.requests, 'get', lambda *a, **kw: Reply({
        'sub': 'linked-google-id', 'email': 'other@gmail.com', 'email_verified': True}))
    callback = client.get(f'/api/auth/google/callback?code=one&state={state}', follow_redirects=False)
    assert callback.headers['location'].endswith('/account/security?google_connected=1')
    with sessions() as db:
        account = db.query(models.AuthAccount).filter_by(email=EMAIL).one()
        assert db.query(models.GoogleIdentity).one().account_id == account.id
        assert db.query(models.AuthAccount).count() == 1


def test_session_and_profile_use_one_select_without_avatar_blob(env):
    from sqlalchemy import event
    client, sessions, _, _ = env
    login(env)
    assert client.post('/api/onboarding', json={
        'name': 'Student', 'username': 'speedstudent', 'dob': '2006-01-01', 'class_level': '12'
    }).status_code == 201
    with sessions() as db:
        uid = db.query(models.AuthAccount).one().user_id
        db.add(models.ProfileAvatar(user_id=uid, image=b'large-image-placeholder'))
        db.commit()
    queries = []
    engine = sessions.kw['bind']
    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            queries.append(statement)
    event.listen(engine, 'before_cursor_execute', record)
    try:
        for path in ['/api/auth/session', '/api/me']:
            queries.clear()
            response = client.get(path)
            assert response.status_code == 200
            assert len(queries) == 1, queries
            assert 'profile_avatars_1.image' not in queries[0]
        assert response.json()['profile']['avatar_url'].endswith('/avatar')
    finally:
        event.remove(engine, 'before_cursor_execute', record)
    # The request-local optimization must never hide a subsequent suspension.
    with sessions() as db:
        db.get(models.User, uid).status = 'suspended'
        db.commit()
    assert client.get('/api/me').status_code == 403


def test_combined_dashboard_onboarding_and_account_isolation(env):
    from app.routers import test_attempts
    client, sessions, _, app = env
    app.include_router(test_attempts.router)
    Base.metadata.create_all(sessions.kw['bind'], tables=[
        models.Test.__table__, models.TestAttempt.__table__, models.JeeXRating.__table__,
        models.RatedContest.__table__, models.ContestEntry.__table__,
    ])
    assert client.get('/api/test-attempts/dashboard').status_code == 401
    login(env)
    assert client.get('/api/test-attempts/dashboard').json()['onboarded'] is False
    client.post('/api/onboarding', json={
        'name': 'Student', 'username': 'speedstudent', 'dob': '2006-01-01', 'class_level': '12'
    })
    result = client.get('/api/test-attempts/dashboard')
    assert result.status_code == 200, result.text
    assert result.json()['profile']['username'] == 'speedstudent'
    assert result.json()['attempts'] == []
    assert result.json()['rating']['title'] == 'Unrated'
    # A request without this student's cookie cannot reuse their data.
    with TestClient(app, base_url='https://school.example') as other:
        assert other.get('/api/test-attempts/dashboard').status_code == 401


@pytest.mark.parametrize('value,required', [(None, True), ('true', True), ('false', False), (' FALSE ', False), ('', True), ('flase', True), ('0', True)])
def test_verification_setting_defaults_to_required(monkeypatch, value, required):
    from app.auth import email_verification_required
    if value is None:
        monkeypatch.delenv('REQUIRE_EMAIL_VERIFICATION', raising=False)
    else:
        monkeypatch.setenv('REQUIRE_EMAIL_VERIFICATION', value)
    assert email_verification_required() is required


def test_optional_verification_signup_without_email_provider(env, monkeypatch):
    client, sessions, sent, _ = env
    monkeypatch.setenv('REQUIRE_EMAIL_VERIFICATION', 'false')
    monkeypatch.delenv('BREVO_API_KEY')
    response = post(client, 'register', email=EMAIL, password=PASSWORD)
    assert response.status_code == 202, response.text
    assert response.json()['verification_required'] is False
    assert sent == []
    with sessions() as db:
        assert db.query(models.AuthAccount).one().verified_at is None
        assert db.query(models.AuthEmailToken).count() == 0
    duplicate = post(client, 'register', email=EMAIL, password='a different long password')
    assert duplicate.json() == response.json()
    assert post(client, 'login', email=EMAIL, password='a different long password').status_code == 401
    result = post(client, 'login', email=EMAIL, password=PASSWORD)
    assert result.status_code == 200
    assert result.json()['user']['email_verified'] is False
    client.headers['X-CSRF-Token'] = result.json()['csrf_token']
    assert client.get('/api/auth/session').json()['authenticated'] is True
    assert client.get('/api/me').status_code == 200
    payload = {'name': 'Student', 'username': 'ordinaryuser', 'dob': '2006-01-01', 'class_level': '12'}
    assert client.post('/api/onboarding', json=payload, headers={'X-CSRF-Token':'bad'}).status_code == 403
    assert client.post('/api/onboarding', json=payload).status_code == 201
    assert client.get('/api/me').json()['profile']['username'] == 'ordinaryuser'


def test_reenable_verification_blocks_existing_sessions_until_verified(env, monkeypatch):
    client, sessions, sent, _ = env
    monkeypatch.setenv('REQUIRE_EMAIL_VERIFICATION', 'false')
    assert post(client, 'register', email=EMAIL, password=PASSWORD).status_code == 202
    assert post(client, 'login', email=EMAIL, password=PASSWORD).status_code == 200
    monkeypatch.setenv('REQUIRE_EMAIL_VERIFICATION', 'true')
    assert client.get('/api/me').status_code == 403
    assert post(client, 'login', email=EMAIL, password=PASSWORD).status_code == 403
    assert client.get('/api/auth/session').json()['authenticated'] is False
    assert post(client, 'resend-verification', email=EMAIL).status_code == 200
    assert post(client, 'verify-email', token=sent[-1][2]).status_code == 200
    assert post(client, 'login', email=EMAIL, password=PASSWORD).status_code == 200
    assert client.get('/api/me').status_code == 200
    with sessions() as db:
        assert db.query(models.AuthAccount).one().verified_at is not None


def test_optional_verification_preserves_disabled_and_expired_checks(env, monkeypatch):
    client, sessions, _, _ = env
    monkeypatch.setenv('REQUIRE_EMAIL_VERIFICATION', 'false')
    post(client, 'register', email=EMAIL, password=PASSWORD)
    assert post(client, 'login', email=EMAIL, password=PASSWORD).status_code == 200
    with sessions() as db:
        db.query(models.AuthSession).one().expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get('/api/me').status_code == 401
    assert post(client, 'login', email=EMAIL, password=PASSWORD).status_code == 200
    with sessions() as db:
        db.query(models.AuthAccount).one().disabled = True
        db.commit()
    assert client.get('/api/me').status_code == 401
    assert post(client, 'login', email=EMAIL, password=PASSWORD).status_code == 401


def test_optional_verification_password_reset_does_not_verify_account(env, monkeypatch):
    client, sessions, sent, _ = env
    monkeypatch.setenv('REQUIRE_EMAIL_VERIFICATION', 'false')
    post(client, 'register', email=EMAIL, password=PASSWORD)
    assert post(client, 'forgot-password', email=EMAIL).status_code == 200
    assert sent[-1][1] == 'reset'
    assert post(client, 'reset-password', token=sent[-1][2], password='another long passphrase').status_code == 200
    with sessions() as db:
        assert db.query(models.AuthAccount).one().verified_at is None
    assert post(client, 'login', email=EMAIL, password='another long passphrase').status_code == 200
