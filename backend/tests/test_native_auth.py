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
from app.routers import authentication, users
from app.services import authentication as service

PASSWORD = 'a long unique passphrase'
EMAIL = 'student@example.com'
HEADERS = {'Origin': 'https://school.example', 'X-Jee-Request': '1'}

@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv('PUBLIC_APP_URL', 'https://school.example')
    monkeypatch.setenv('CORS_ORIGINS', 'https://school.example')
    monkeypatch.setenv('AUTH_COOKIE_SECURE', 'true')
    monkeypatch.setenv('AUTH_COOKIE_SAMESITE', 'lax')
    monkeypatch.setenv('AUTH_EMAIL_PROVIDER', 'brevo')
    monkeypatch.setenv('BREVO_API_KEY', 'test-key')
    monkeypatch.setenv('AUTH_EMAIL_FROM', 'hello@example.com')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    tables = [models.User.__table__, models.StudentProfile.__table__, models.ProfileAvatar.__table__,
              models.AuthAccount.__table__, models.AuthSession.__table__, models.AuthEmailToken.__table__, models.AuthRateLimit.__table__]
    Base.metadata.create_all(engine, tables=tables)
    sessions = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(authentication.router)
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
