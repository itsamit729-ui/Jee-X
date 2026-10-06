import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
import io
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models.social_job import SocialSlot, SocialAsset, SocialDispatch, SocialJob, SocialMedia
from app.routers import social_slots as social

AUTH = {'Authorization': 'Bearer ' + 'x' * 32}


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[m.__table__ for m in (SocialSlot, SocialAsset, SocialDispatch, SocialJob, SocialMedia)])
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(social, 'SessionLocal', factory)
    for key in ('SOCIAL_TRIGGER_SECRET', 'BUFFER_API_KEY', 'GROQ_API_KEY'):
        monkeypatch.setenv(key, 'x'*32)
    clock = [datetime(2026,10,6,9)]
    monkeypatch.setattr(social, 'local_now', lambda: clock[0])
    monkeypatch.setattr(social.worker, 'find_channel', lambda: ('org', {'id':'channel'}))
    monkeypatch.setattr(social.worker, 'posts', lambda *a: [])
    monkeypatch.setattr(social.worker, 'ai_copy', lambda *a: {'hook':'Try this', 'caption':'Solve and swipe.'})
    def render(content, copy, directory):
        paths=[]
        for i in range(4):
            p=Path(directory)/f'{i}.png'
            Image.new('RGB',(1080,1350),'orange').save(p)
            paths.append(p)
        return paths
    monkeypatch.setattr(social.worker, 'render', render)
    def video(content, directory):
        p=Path(directory)/'reel.mp4';p.write_bytes(b'\x00\x00\x00\x18ftypisom' + b'v'*40);return p
    monkeypatch.setattr(social.reel, 'render', video)
    submitted=[]
    def buffer(query, variables):
        if 'createPost' not in query:
            return {'post':{'id':variables['id'], 'status':'sent'}}
        payload=variables['input'];submitted.append(payload)
        with factory() as db:
            key=social.today()+':'+social.current_slot()
            assert db.get(SocialSlot,key).state=='submitting'
        return {'createPost':{'post':{'id':'p'+str(len(submitted)), 'status':'scheduled'}}}
    monkeypatch.setattr(social.worker, 'buffer', buffer)
    app=FastAPI();app.include_router(social.router)
    with TestClient(app) as client:
        def fetch(url, **kwargs):
            result=client.get(url.replace(social.MEDIA_ORIGIN,''))
            assert result.status_code==200
            return result.content
        monkeypatch.setattr(social.worker, 'request', fetch)
        yield client, factory, clock, submitted
    engine.dispose()


def test_three_slots_and_retry_no_duplicates(setup):
    client, factory, clock, submitted=setup
    for hour in (9,14,19):
        clock[0]=clock[0].replace(hour=hour)
        assert client.post('/api/social/trigger',headers=AUTH).status_code==202
        client.post('/api/social/trigger',headers=AUTH)
    assert len(submitted)==3
    assert [p['metadata']['instagram']['type'] for p in submitted]==['post','reel','post']
    assert [len(p['assets']) for p in submitted]==[4,1,4]
    assert len(set(p['text'].splitlines()[-1] for p in submitted))==3
    assert all(j['state']=='published' for j in client.get('/api/social/status',headers=AUTH).json()['jobs'])
    assert len({social.slot_problem('2026-10-06:'+s)['subject'] for s in ('morning','reel','evening')})==3


def test_media_head_range_and_format(setup):
    client, factory, clock, submitted=setup
    clock[0]=clock[0].replace(hour=14)
    client.post('/api/social/trigger',headers=AUTH)
    url=submitted[0]['assets'][0]['video']['url'].replace(social.MEDIA_ORIGIN,'')
    full=client.get(url)
    assert full.headers['content-type']=='video/mp4'
    assert client.head(url).headers['content-length']==str(len(full.content))
    part=client.get(url,headers={'Range':'bytes=4-7'})
    assert part.status_code==206 and part.content==b'ftyp'
    assert client.get(url,headers={'Range':'bytes=-4'}).content==b'vvvv'
    assert client.get(url,headers={'Range':'bytes=9999-'}).status_code==416
    assert client.get(url.replace('.mp4','.jpg')).status_code==404


def test_auth_pause_and_early_window(setup,monkeypatch):
    client,_,clock,submitted=setup
    assert client.post('/api/social/trigger').status_code==401
    clock[0]=clock[0].replace(hour=8)
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='idle'
    monkeypatch.setenv('SOCIAL_PAUSED','true')
    assert client.post('/api/social/trigger',headers=AUTH).status_code==503
    assert not submitted


def test_legacy_daily_record_consumes_morning(setup):
    client,factory,clock,submitted=setup
    with factory() as db:
        db.add(SocialJob(day='2026-10-06',owner='old',state='scheduled',updated_at=datetime.utcnow(),attempts=1,post_id='old'))
        db.commit()
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='legacy_record'
    assert not submitted


def test_timeout_held_and_never_reposted(setup,monkeypatch):
    client,_,_,submitted=setup
    def fail(*a):
        raise TimeoutError()
    monkeypatch.setattr(social.worker,'buffer',fail)
    client.post('/api/social/trigger',headers=AUTH)
    for _ in range(3): client.post('/api/social/trigger',headers=AUTH)
    assert client.get('/api/social/status',headers=AUTH).json()['jobs'][0]['state']=='needs_review'


def test_public_media_failure_stops_before_submission(setup,monkeypatch):
    client,_,_,submitted=setup
    monkeypatch.setattr(social.worker,'request',lambda *a,**kw:b'<html>unavailable</html>')
    client.post('/api/social/trigger',headers=AUTH)
    assert not submitted
    assert client.get('/api/social/status',headers=AUTH).json()['jobs'][0]['state']=='failed'


def test_active_job_blocks_another_slot_and_expired_owner_cannot_submit(setup,monkeypatch):
    client,factory,clock,submitted=setup
    monkeypatch.setattr(social,'run_job',lambda *a:None)
    client.post('/api/social/trigger',headers=AUTH)
    clock[0]=clock[0].replace(hour=14)
    assert client.post('/api/social/trigger',headers=AUTH).json()['slot']=='morning'
    with factory() as db:
        assert db.query(SocialSlot).count()==1
        job=db.get(SocialSlot,'2026-10-06:morning')
        old_owner=job.owner
        job.updated_at=datetime.utcnow()-timedelta(minutes=16)
        db.commit()
    clock[0]=clock[0].replace(hour=9)
    client.post('/api/social/trigger',headers=AUTH)
    assert not social.transition('2026-10-06:morning',old_owner,'running','submitting')
