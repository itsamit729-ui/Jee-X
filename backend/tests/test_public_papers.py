import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base, get_db
from app.deps import get_current_db_user
from app.routers.public_papers import router, paper_slug
from app.routers.pyqs import router as mock_router

@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(models.User(id=1, auth0_sub='public-paper-test', username='tester', name='Tester'))
        db.add(models.Subject(id=1, code='PHY', name='Physics'))
        db.add(models.Chapter(id=1, subject_id=1, name='Waves', slug='waves', class_level='12'))
        db.add(models.Subtopic(id=1, chapter_id=1, name='Waves', slug='waves'))
        db.flush()
        for i in range(1, 7):
            db.add(models.Question(id=i, ref=f'PUBLIC-{i}', subtopic_id=1, type='single_correct',
                stem=f'Preview {i} <script>alert(1)</script>', solution='SECRET_SOLUTION',
                difficulty=3, expected_time_sec=90, source_type='pyq', exam='mht_cet' if i != 6 else 'jee_main',
                year=2025, shift='19 Apr 2025, Shift 1', status='draft' if i == 5 else 'published',
                version=1, content_hash=str(i)))
            db.flush()
            for j in range(4):
                db.add(models.QuestionOption(question_id=i, label='ABCD'[j], content=f'Option {j}', is_correct=j == 0, position=j+1))
        db.commit()
    def database():
        with factory() as db:
            yield db
    app = FastAPI()
    app.include_router(router)
    app.include_router(mock_router)
    app.dependency_overrides[get_db] = database
    return TestClient(app), app, factory

def test_public_html_and_live_sitemap_without_javascript(setup):
    client, _, _ = setup
    slug = paper_slug(2025, '19 Apr 2025, Shift 1')
    path = f'/mhtcet/papers/2025/{slug}'
    index = client.get('/mhtcet/papers')
    assert index.status_code == 200 and path in index.text
    response = client.get(path)
    assert response.status_code == 200
    assert '4 available questions' in response.text
    assert 'SECRET_SOLUTION' not in response.text and 'is_correct' not in response.text
    assert 'Preview 3' in response.text and 'Preview 4 &lt;script&gt;' not in response.text
    assert '<script>alert(1)</script>' not in response.text
    assert '&lt;script&gt;' in response.text
    assert 'year=2025' in response.text and 'shift=19+Apr+2025' in response.text
    assert 'Partial' in response.text or 'PARTIAL' in response.text
    assert f'rel="canonical" href="https://jeeedge.in{path}"' in response.text
    from xml.etree import ElementTree
    sitemap = client.get('/sitemap.xml')
    assert 'application/xml' in sitemap.headers['content-type']
    assert path in sitemap.text
    ElementTree.fromstring(sitemap.text)
    assert client.get('/mhtcet/papers/2025/unknown').status_code == 404

def test_start_requires_auth_and_server_counts_success(setup):
    client, app, factory = setup
    body = {'year':2025, 'shift':'19 Apr 2025, Shift 1', 'acquisition_source':'teacher'}
    assert client.post('/api/pyqs/mht_cet/papers', json=body).status_code == 401
    def user():
        with factory() as db:
            return db.get(models.User, 1)
    app.dependency_overrides[get_current_db_user] = user
    response = client.post('/api/pyqs/mht_cet/papers', json=body)
    assert response.status_code == 201, response.text
    assert len(response.json()['questions']) == 4
    assert 'is_correct' not in response.text and 'SECRET_SOLUTION' not in response.text
    with factory() as db:
        row = db.query(models.AcquisitionCount).one()
        assert (row.event, row.source, row.count) == ('mock_start','teacher',1)

def test_aggregate_events_validate_origin_and_paper(setup):
    client, _, factory = setup
    body = {'paper':'archive','source':'teacher','event':'view'}
    assert client.post('/api/public-papers/events',json=body).status_code == 403
    headers = {'origin':'http://localhost:5173','x-jee-request':'1'}
    for _ in range(2):
        assert client.post('/api/public-papers/events',json=body,headers=headers).status_code == 204
    assert client.post('/api/public-papers/events',json={**body,'paper':'fake'},headers=headers).status_code == 404
    assert client.post('/api/public-papers/events',json={**body,'event':'mock_start'},headers=headers).status_code == 422
    assert client.get('/api/admin/paper-acquisition').status_code == 401
    with factory() as db:
        assert db.query(models.AcquisitionCount).one().count == 2
