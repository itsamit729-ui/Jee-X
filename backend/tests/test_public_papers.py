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


def test_instagram_landing_has_real_destinations_and_aggregate_tracking(setup):
    client,_,factory=setup
    response=client.get('/start?to=cet&utm_source=instagram')
    assert response.status_code==200
    assert 'rel="canonical" href="https://jeeedge.in/start"' in response.text
    assert 'data-paper="instagram" data-source="instagram"' in response.text
    assert response.text.index('<h2>Choose an MHT-CET paper') < response.text.index('<h2>Try a free warm-up')
    assert '/free-test?source=instagram' in response.text
    assert '/mhtcet/papers?utm_source=instagram' in response.text
    assert '/subject-test?source=instagram' in response.text
    assert 'sign in for a timed mock' in response.text
    assert client.get('/start?to=https://example.com').status_code==422
    assert 'https://jeeedge.in/start' in client.get('/sitemap.xml').text
    headers={'origin':'http://localhost:5173','x-jee-request':'1'}
    for event in ('view','start_click'):
        assert client.post('/api/public-papers/events',json={'paper':'instagram','source':'instagram','event':event},headers=headers).status_code==204
    with factory() as db:
        assert {(r.event,r.source,r.count) for r in db.query(models.AcquisitionCount)}=={('view','instagram',1),('start_click','instagram',1)}


def test_youtube_landing_preserves_source_and_records_aggregate_events(setup):
    client, _, factory = setup
    response = client.get('/start?to=practice&utm_source=youtube&utm_campaign=shorts')
    assert response.status_code == 200
    assert 'data-paper="youtube" data-source="youtube"' in response.text
    assert 'Continue from Jee Edge on YouTube:' in response.text
    assert 'rel="canonical" href="https://jeeedge.in/start"' in response.text
    assert response.text.index('<h2>Work on a chapter') < response.text.index('<h2>Try a free warm-up')
    for path in ('/subject-test?source=youtube', '/free-test?source=youtube', '/mhtcet/papers?utm_source=youtube'):
        assert path in response.text
    headers = {'origin': 'http://localhost:5173', 'x-jee-request': '1'}
    for event in ('view', 'start_click'):
        assert client.post('/api/public-papers/events', json={'paper': 'youtube', 'source': 'youtube', 'event': event}, headers=headers).status_code == 204
    with factory() as db:
        assert {(r.event, r.source, r.count) for r in db.query(models.AcquisitionCount)} == {('view', 'youtube', 1), ('start_click', 'youtube', 1)}
    fallback = client.get('/start?utm_source=%3Cscript%3E')
    assert fallback.status_code == 200
    assert 'data-paper="instagram" data-source="instagram"' in fallback.text
    assert '<script>' not in fallback.text


def test_year_archive_has_distinct_canonical_breadcrumbs_and_live_sitemap_entries(setup):
    import json
    import re
    from xml.etree import ElementTree
    client,_,_=setup
    response=client.get('/mhtcet/papers/2025')
    assert response.status_code==200
    assert '<h1>MHT-CET 2025 question papers by shift</h1>' in response.text
    assert 'rel="canonical" href="https://jeeedge.in/mhtcet/papers/2025"' in response.text
    schema=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',response.text).group(1))
    assert schema[1]['@type']=='BreadcrumbList'
    assert schema[1]['itemListElement'][-1]['item']=='https://jeeedge.in/mhtcet/papers/2025'
    sitemap=ElementTree.fromstring(client.get('/sitemap.xml').text)
    locations=[node.text for node in sitemap.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    assert 'https://jeeedge.in/mhtcet/papers/2025' in locations
    assert len(locations)==len(set(locations))
    assert client.get('/mhtcet/papers/2024').status_code==404
    assert 'SECRET_SOLUTION' not in response.text


def test_structured_metadata_cannot_break_out_of_json_script():
    import json,re
    from app.routers.public_papers import page
    malicious='Question </script><script>alert(1)</script> & test'
    response=page(malicious,malicious,'/example','<h1>Safe body</h1>',breadcrumbs=[(malicious,'/example')])
    html=response.body.decode()
    raw=re.search(r'<script type="application/ld\+json">(.*?)</script>',html).group(1)
    assert json.loads(raw)[0]['name']==malicious
    assert '</script>' not in raw and '<script>alert(1)' not in html
