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
from app.models.social_job import SocialSlot, SocialAsset, SocialDispatch, SocialJob, SocialMedia, SocialUsage, SocialQuotaLock, SocialCache
from app.routers import social_slots as social

REAL_REQUEST = social.worker.request

AUTH = {'Authorization': 'Bearer ' + 'x' * 32}


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[m.__table__ for m in (SocialSlot, SocialAsset, SocialDispatch, SocialJob, SocialMedia, SocialUsage, SocialQuotaLock, SocialCache)])
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(social, 'SessionLocal', factory)
    monkeypatch.setattr(social.budget, 'SessionLocal', factory)
    for key in ('SOCIAL_TRIGGER_SECRET', 'BUFFER_API_KEY', 'GROQ_API_KEY'):
        monkeypatch.setenv(key, 'x'*32)
    clock = [datetime(2026,10,6,7)]
    monkeypatch.setattr(social, 'local_now', lambda: clock[0])
    monkeypatch.setattr(social.worker, 'find_channel', lambda: ('org', {'id':'channel'}))
    monkeypatch.setattr(social.worker, 'posts', lambda *a: [])
    monkeypatch.setattr(social.editorial, 'package', lambda *a: {'hook':'Try this', 'caption':'Solve and swipe.'})
    def render(content, copy, directory):
        paths=[]
        for i in range(6):
            p=Path(directory)/f'{i}.png'
            Image.new('RGB',(1080,1350),'orange').save(p)
            paths.append(p)
        return paths
    monkeypatch.setattr(social.worker, 'render', render)
    def video(content, directory, copy=None):
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


def test_thirty_slots_and_retry_no_duplicates(setup):
    client, factory, clock, submitted=setup
    for index in range(30):
        clock[0]=datetime(2026,10,6,7)+timedelta(minutes=32*index)
        assert client.post('/api/social/trigger',headers=AUTH).status_code==202
        client.post('/api/social/trigger',headers=AUTH)
    assert len(submitted)==30
    assert sum(p['metadata']['instagram']['type']=='reel' for p in submitted)==10
    assert sum(len(p['assets'])==6 for p in submitted)==20
    assert len(set(p['text'].splitlines()[-1] for p in submitted))==30
    assert all('bio' not in p['text'] for p in submitted)
    assert all(j['state']=='published' for j in client.get('/api/social/status',headers=AUTH).json()['jobs'])
    assert len({social.slot_problem(f'2026-10-06:s{i:02d}')['topic'] for i in range(30)})==30


def test_media_head_range_and_format(setup):
    client, factory, clock, submitted=setup
    clock[0]=clock[0].replace(hour=8,minute=10)
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
    clock[0]=clock[0].replace(hour=6)
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='idle'
    monkeypatch.setenv('SOCIAL_PAUSED','true')
    assert client.post('/api/social/trigger',headers=AUTH).status_code==503
    assert not submitted


def test_legacy_record_counts_toward_daily_cap(setup,monkeypatch):
    monkeypatch.setenv("SOCIAL_DAILY_TARGET","1")
    client,factory,clock,submitted=setup
    with factory() as db:
        db.add(SocialJob(day='2026-10-06',owner='old',state='scheduled',updated_at=datetime.utcnow(),attempts=1,post_id='old'))
        db.commit()
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='daily_limit'
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
    clock[0]=clock[0].replace(hour=8,minute=10)
    assert client.post('/api/social/trigger',headers=AUTH).json()['slot']=='s00'
    with factory() as db:
        assert db.query(SocialSlot).count()==1
        job=db.get(SocialSlot,'2026-10-06:s00')
        old_owner=job.owner
        job.updated_at=datetime.utcnow()-timedelta(minutes=16)
        db.commit()
    clock[0]=clock[0].replace(hour=7,minute=0)
    client.post('/api/social/trigger',headers=AUTH)
    assert not social.transition('2026-10-06:s00',old_owner,'running','submitting')


def test_rolling_budgets_and_token_reservations(setup):
    _, factory, _, _ = setup
    b=social.budget
    b.reserve('buffer', units=95)
    with pytest.raises(social.worker.ServiceError):
        b.reserve('buffer')
    with factory() as db:
        db.query(SocialUsage).update({'created_at':datetime.utcnow()-timedelta(days=2)})
        db.commit()
    b.reserve('buffer')  # daily window released; still counts toward monthly
    ticket=b.reserve('groq',tokens=7500)
    with pytest.raises(social.worker.ServiceError):
        b.reserve('groq',tokens=200)
    b.settle(ticket,tokens=100)
    b.reserve('groq',tokens=200)
    assert b.report()['services']['groq'][0]['tokens_used']==300


def test_provider_cooldown_and_existing_media_stays_available(setup):
    client,factory,clock,submitted=setup
    client.post('/api/social/trigger',headers=AUTH)
    url=submitted[0]['assets'][0]['image']['url'].replace(social.MEDIA_ORIGIN,'')
    social.budget.cache('cooldown:buffer',True,3600)
    with pytest.raises(social.worker.ServiceError):
        social.budget.reserve('buffer')
    social.budget.record_egress(1024*1024*1024)
    with pytest.raises(social.worker.ServiceError):
        social.budget.admission()
    assert client.get(url).status_code==200


def test_monthly_budget_blocks_even_if_daily_is_empty(setup):
    _,factory,_,_=setup
    with factory() as db:
        db.add(SocialUsage(id='old',service='buffer',units=2850,tokens=0,
                          created_at=datetime.utcnow()-timedelta(days=2)))
        db.commit()
    with pytest.raises(social.worker.ServiceError):
        social.budget.reserve('buffer')


def test_real_request_hook_reserves_before_network_and_settles_usage(setup,monkeypatch):
    import json
    _,factory,_,_=setup
    from social import worker
    # Undo fixture's public-media stub so the actual HTTP wrapper is exercised.
    monkeypatch.setattr(worker, 'request', REAL_REQUEST)
    observed=[]
    class Reply:
        def __enter__(self):
            with factory() as db:
                assert db.query(SocialUsage).filter_by(service='groq').count()==1
            return self
        def __exit__(self,*a): pass
        def read(self): return json.dumps({'usage':{'total_tokens':42}}).encode()
    monkeypatch.setattr(worker.urllib.request,'urlopen',lambda *a,**kw:Reply())
    with social.budget.tracked():
        worker.request('https://api.groq.com/openai/v1/chat/completions',method='POST',
                       body={'messages':[],'max_completion_tokens':100})
    assert social.budget.report()['services']['groq'][0]['tokens_used']==42
