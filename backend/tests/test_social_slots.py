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

from app.models.social_comment import SocialLesson

REAL_REQUEST = social.worker.request

AUTH = {'Authorization': 'Bearer ' + 'x' * 32}


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[m.__table__ for m in (SocialSlot, SocialAsset, SocialDispatch, SocialJob, SocialMedia, SocialUsage, SocialQuotaLock, SocialCache, SocialLesson)])
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(social, 'SessionLocal', factory)
    monkeypatch.setattr(social.social_speech, 'fetch', lambda text: None)
    monkeypatch.setattr(social.budget, 'SessionLocal', factory)
    monkeypatch.delenv('SOCIAL_DAILY_TARGET', raising=False)
    monkeypatch.delenv('SOCIAL_REELS_PER_DAY', raising=False)
    for key in ('SOCIAL_TRIGGER_SECRET', 'BUFFER_API_KEY', 'GROQ_API_KEY'):
        monkeypatch.setenv(key, 'x'*32)
    clock = [datetime(2026,10,6,7)]
    monkeypatch.setattr(social, 'local_now', lambda: clock[0])
    monkeypatch.setattr(social.worker, 'find_channel', lambda: ('org', {'id':'channel'}))
    monkeypatch.setattr(social.worker, 'posts', lambda *a: [])
    monkeypatch.setattr(social.storyboard,'plan',social.storyboard.fallback)
    monkeypatch.setattr(social.editorial, 'package', lambda *a,**kw: social.editorial.authored(a[0]))
    def render(content, copy, directory):
        paths=[]
        for i in range(8):
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
            key=social.today()+':'+payload['text'].splitlines()[-1].split(' / ')[-1]
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


def test_twelve_slots_and_retry_no_duplicates(setup):
    client, factory, clock, submitted=setup
    for index in range(12):
        clock[0]=datetime(2026,10,6,7)+timedelta(minutes=80*index)
        assert client.post('/api/social/trigger',headers=AUTH).status_code==202
        client.post('/api/social/trigger',headers=AUTH)
    assert len(submitted)==12
    assert sum(p['metadata']['instagram']['type']=='reel' for p in submitted)==4
    assert sum(len(p['assets'])==8 for p in submitted)==8
    for post in submitted:
        is_video = post['metadata']['instagram']['type'] == 'reel'
        assert ('Kevin MacLeod' in post['text']) == is_video
        if is_video:
            assert 'https://creativecommons.org/licenses/by/4.0/' in post['text']
    assert len(set(p['text'].splitlines()[-1] for p in submitted))==12
    assert all('bio' not in p['text'] for p in submitted)
    assert all(j['state']=='published' for j in client.get('/api/social/status',headers=AUTH).json()['jobs'])
    reel_topics=[social.slot_problem(f'2026-10-06:s{i:02d}')['topic'] for i in range(12) if social.is_reel(f's{i:02d}')]
    assert len(set(reel_topics))==4
    assert set(reel_topics)<=set(social.storyboard.VISUAL_TOPICS)


def test_media_head_range_and_format(setup):
    client, factory, clock, submitted=setup
    clock[0]=clock[0].replace(hour=9,minute=40)
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
    clock[0]=clock[0].replace(hour=9,minute=40)
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


def test_old_env_cannot_restore_thirty_posts(monkeypatch):
    monkeypatch.setenv('SOCIAL_DAILY_TARGET','30')
    monkeypatch.setenv('SOCIAL_REELS_PER_DAY','10')
    assert social.daily_target()==12 and social.reel_target()==4


def test_reported_delivery_error_holds_new_posts(setup,monkeypatch):
    client,factory,clock,submitted=setup
    monkeypatch.setattr(social.worker,'posts',lambda *a:[{'id':'failed-post','status':'error','text':'Existing post'}])
    client.post('/api/social/trigger',headers=AUTH)
    assert not submitted
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='delivery_hold'
    assert client.get('/api/social/status',headers=AUTH).json()['publishing_hold']['post_id']=='failed-post'


def test_repetition_gate_holds_before_render_and_submit(setup,monkeypatch):
    client,_,clock,submitted=setup
    text=social.editorial.authored(social.slot_problem('2026-10-06:s00'))['caption']
    monkeypatch.setattr(social.worker,'posts',lambda *a:[{'id':'previous','status':'sent','text':text+'\nJeeEdge daily 2026-10-05 / s01'}])
    client.post('/api/social/trigger',headers=AUTH)
    assert not submitted
    assert 'repeats' in client.get('/api/social/status',headers=AUTH).json()['jobs'][0]['error']


def test_already_submitted_twelve_prevents_extra_post_after_rollout(setup):
    client,factory,clock,submitted=setup
    with factory() as db:
        for i in range(12,24):
            db.add(SocialSlot(day=f'2026-10-06:s{i:02d}',owner='old',state='published',updated_at=datetime.utcnow(),attempts=1,post_id=str(i)))
        db.commit()
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='daily_limit'
    assert not submitted


def test_old_failed_slot_cannot_exceed_reduced_daily_cap(setup):
    client,factory,_,submitted=setup
    with factory() as db:
        db.add(SocialSlot(day='2026-10-06:s00',owner='old',state='failed',updated_at=datetime.utcnow(),attempts=1))
        for i in range(12,24):
            db.add(SocialSlot(day=f'2026-10-06:s{i:02d}',owner='old',state='published',updated_at=datetime.utcnow(),attempts=1,post_id=str(i)))
        db.commit()
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='daily_limit'
    assert not submitted



def enable_test_voice(monkeypatch):
    from social.test_narration import wav
    monkeypatch.setattr(social.social_speech,'fetch',lambda text:wav())


def test_manual_narrated_reel_outside_window_and_idempotency(setup,monkeypatch):
    client,factory,clock,submitted=setup
    clock[0]=clock[0].replace(hour=23,minute=10)
    enable_test_voice(monkeypatch)
    result=client.post('/api/social/test-reel',headers=AUTH)
    assert result.status_code==202 and result.json()['slot']=='s99'
    assert len(submitted)==1 and submitted[0]['metadata']['instagram']['type']=='reel'
    for _ in range(3):
        client.post('/api/social/test-reel',headers=AUTH)
    assert len(submitted)==1
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='idle'


def test_manual_requires_all_voice_scenes_and_no_retry_storm(setup,monkeypatch):
    client,factory,clock,submitted=setup
    result=client.post('/api/social/test-reel',headers=AUTH)
    assert result.status_code==202 and not submitted
    with factory() as db:
        job=db.get(SocialSlot,'2026-10-06:s99')
        assert job.state=='failed' and 'all narration scenes' in job.error
    retry=client.post('/api/social/test-reel',headers=AUTH).json()
    assert 'retry_after' in retry and retry['attempts']==1
    with factory() as db:
        job=db.get(SocialSlot,'2026-10-06:s99')
        job.updated_at=datetime.utcnow()-timedelta(minutes=31)
        db.commit()
    from social.test_narration import wav
    calls=[]
    def one_clip(text):
        calls.append(text)
        return wav() if len(calls)==1 else None
    monkeypatch.setattr(social.social_speech,'fetch',one_clip)
    client.post('/api/social/test-reel',headers=AUTH)
    assert not submitted


def test_manual_respects_auth_pause_and_delivery_hold(setup,monkeypatch):
    client,_,_,submitted=setup
    assert client.post('/api/social/test-reel').status_code==401
    monkeypatch.setenv('SOCIAL_TTS_ENABLED','false')
    assert client.post('/api/social/test-reel',headers=AUTH).status_code==503
    monkeypatch.setenv('SOCIAL_TTS_ENABLED','true')
    monkeypatch.setenv('SOCIAL_PAUSED','true')
    assert client.post('/api/social/test-reel',headers=AUTH).status_code==503
    monkeypatch.setenv('SOCIAL_PAUSED','false')
    social.budget.cache('publishing-hold',{'reason':'review'},86400)
    assert client.post('/api/social/test-reel',headers=AUTH).json()['state']=='delivery_hold'
    assert not submitted


def test_only_one_manual_exception_after_twelve_regular_submissions(setup,monkeypatch):
    client,factory,clock,submitted=setup
    enable_test_voice(monkeypatch)
    with factory() as db:
        for i in range(12):
            db.add(SocialSlot(day=f'2026-10-06:s{i:02d}',owner='old',state='published',updated_at=datetime.utcnow(),attempts=1,post_id=str(i)))
        db.commit()
    client.post('/api/social/test-reel',headers=AUTH)
    client.post('/api/social/test-reel',headers=AUTH)
    assert len(submitted)==1
    with factory() as db:
        assert db.query(SocialSlot).count()==13
