import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models.social_job import SocialJob, SocialMedia
from app.routers import social


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[SocialJob.__table__, SocialMedia.__table__])
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(social, 'SessionLocal', factory)
    for key in ('SOCIAL_TRIGGER_SECRET', 'GROQ_API_KEY', 'BUFFER_API_KEY'):
        monkeypatch.setenv(key, 'x' * 32)
    app = FastAPI()
    app.include_router(social.router)
    with TestClient(app) as client:
        yield client, factory
    engine.dispose()


AUTH = {'Authorization': 'Bearer ' + 'x' * 32}


def test_auth_and_durable_claim(setup, monkeypatch):
    client, factory = setup
    called = []
    monkeypatch.setattr(social, 'run_job', lambda *args: called.append(args))
    assert client.post('/api/social/trigger').status_code == 401
    assert client.get('/api/social/status').status_code == 401
    assert client.post('/api/social/trigger', headers=AUTH).status_code == 202
    client.post('/api/social/trigger', headers=AUTH)
    assert len(called) == 1
    with factory() as db:
        job = db.get(SocialJob, social.today())
        job.updated_at = datetime.utcnow() - timedelta(minutes=16)
        db.commit()
    client.post('/api/social/trigger', headers=AUTH)
    assert len(called) == 2
    assert not social.transition(called[0][0], called[0][1], 'running', 'submitting')
    with factory() as db:
        job = db.get(SocialJob, social.today())
        job.state = 'submitting'
        job.updated_at = datetime.utcnow() - timedelta(days=1)
        db.commit()
    client.post('/api/social/trigger', headers=AUTH)
    assert len(called) == 2


def mock_generation(monkeypatch):
    monkeypatch.setattr(social.worker, 'find_channel', lambda: ('org', {'id': 'channel'}))
    monkeypatch.setattr(social.worker, 'posts', lambda *args: [])
    monkeypatch.setattr(social.worker, 'ai_copy', lambda *args: {'hook': 'Try this', 'caption': 'Swipe to solve'})
    def render(content, copy, directory):
        path = Path(directory) / '1.png'
        path.write_bytes(b'fake-png')
        return [path]
    monkeypatch.setattr(social.worker, 'render', render)


def test_submission_fenced_and_media_public(setup, monkeypatch):
    client, factory = setup
    mock_generation(monkeypatch)
    def submit(query, variables):
        with factory() as db:
            assert db.get(SocialJob, social.today()).state == 'submitting'
            media = db.query(SocialMedia).one()
            url = '/api/social/media/' + media.id + '.png'
            assert client.get(url).content == b'fake-png'
            head = client.head(url)
            assert head.status_code == 200
            assert head.content == b''
            assert head.headers['content-type'] == 'image/png'
            assert head.headers['content-length'] == str(len(b'fake-png'))
        return {'createPost': {'post': {'id': 'post123', 'status': 'scheduled'}}}
    monkeypatch.setattr(social.worker, 'buffer', submit)
    client.post('/api/social/trigger', headers=AUTH)
    data = client.get('/api/social/status', headers=AUTH).json()['jobs'][0]
    assert data['state'] == 'scheduled'
    assert data['post_id'] == 'post123'
    client.post('/api/social/trigger', headers=AUTH)
    assert client.get('/api/social/status', headers=AUTH).json()['jobs'][0]['attempts'] == 1


def test_ambiguous_submission_is_held(setup, monkeypatch):
    client, _ = setup
    mock_generation(monkeypatch)
    calls = []
    def submit(*args):
        calls.append(1)
        raise TimeoutError('secret remote response')
    monkeypatch.setattr(social.worker, 'buffer', submit)
    client.post('/api/social/trigger', headers=AUTH)
    client.post('/api/social/trigger', headers=AUTH)
    data = client.get('/api/social/status', headers=AUTH).json()['jobs'][0]
    assert data['state'] == 'needs_review'
    assert 'secret remote' not in data['error']
    assert len(calls) == 1


def test_existing_buffer_post_skips_generation(setup, monkeypatch):
    client, _ = setup
    mock_generation(monkeypatch)
    monkeypatch.setattr(social.worker, 'posts', lambda *args: [{'id': 'old', 'text': 'JeeEdge daily ' + social.today(), 'status': 'scheduled'}])
    monkeypatch.setattr(social.worker, 'ai_copy', lambda *args: pytest.fail('Must not generate again'))
    client.post('/api/social/trigger', headers=AUTH)
    assert client.get('/api/social/status', headers=AUTH).json()['jobs'][0]['state'] == 'existing'


def test_generation_failures_are_bounded(setup, monkeypatch):
    client, _ = setup
    def fail():
        raise social.worker.ServiceError('Buffer unavailable')
    monkeypatch.setattr(social.worker, 'find_channel', fail)
    for _ in range(5):
        client.post('/api/social/trigger', headers=AUTH)
    data = client.get('/api/social/status', headers=AUTH).json()['jobs'][0]
    assert data['state'] == 'failed'
    assert data['attempts'] == 3
