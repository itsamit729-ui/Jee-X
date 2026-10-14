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
from app.models.social_job import SocialSlot, SocialAsset, SocialDispatch, SocialJob, SocialMedia, SocialUsage, SocialQuotaLock, SocialCache, SocialShort
from app.routers import social_slots as social

from app.models.social_comment import SocialLesson

REAL_REQUEST = social.worker.request

AUTH = {'Authorization': 'Bearer ' + 'x' * 32}


def seed_legacy_hold(post):
    social.budget.cache('publishing-hold',{'post_id':post['id'],'reason':'Legacy Buffer delivery hold'},86400)


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[m.__table__ for m in (SocialSlot, SocialAsset, SocialDispatch, SocialJob, SocialMedia, SocialUsage, SocialQuotaLock, SocialCache, SocialShort, SocialLesson)])
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(social, 'SessionLocal', factory)
    monkeypatch.setattr(social.social_speech, 'fetch', lambda text: None)
    monkeypatch.setattr(social.budget, 'SessionLocal', factory)
    monkeypatch.setattr(social.shorts,'SessionLocal',factory)
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
        assert ('Music: original synthesized rhythm' in post['text']) == is_video
        assert 'jeeedge.in/start' in post['text']
        assert 'Kevin MacLeod' not in post['text']
    assert len(set(p['text'].splitlines()[-1] for p in submitted))==12
    assert all('bio' not in p['text'] for p in submitted)
    with factory() as db:
        pending=[(row.day,row.owner,row.post_id) for row in db.query(SocialSlot).all()]
    for args in pending:social.refresh_delivery(*args)
    assert all(j['state']=='published' for j in client.get('/api/social/status',headers=AUTH).json()['jobs'])
    reel_topics=[social.slot_problem(f'2026-10-06:s{i:02d}')['topic'] for i in range(12) if social.is_reel(f's{i:02d}')]
    assert len(set(reel_topics))==4
    assert set(reel_topics)<=set(social.storyboard.REEL_TOPICS)


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


def test_content_plan_is_private_and_cannot_publish(setup):
    client,factory,_,submitted=setup
    assert client.get('/api/social/plan').status_code==401
    response=client.get('/api/social/plan',headers=AUTH)
    assert response.status_code==200 and response.json()['preview_only'] is True
    items=response.json()['items']
    assert len(items)==12
    videos=[c for c in items if c['kind']=='reel']
    assert len({c['story'] for c in videos})==4
    assert {c['seconds'] for c in videos}=={41,42}
    assert all(c['destination'].startswith('https://jeeedge.in/start?') for c in items)
    assert not submitted
    with factory() as db:
        assert db.query(SocialSlot).count()==db.query(SocialUsage).count()==0


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


def test_unrelated_historical_delivery_error_does_not_block_new_posts(setup,monkeypatch):
    client,factory,clock,submitted=setup
    original=social.worker.buffer
    monkeypatch.setattr(social.worker,'posts',lambda *a:[{'id':'foreign-failure','status':'error','text':'An unrelated old post'}])
    client.post('/api/social/trigger',headers=AUTH)
    assert len(submitted)==1
    assert social.budget.cached('publishing-hold') is None


def test_recovered_hold_marks_exact_post_published_without_reposting(setup):
    client,factory,_,submitted=setup
    with factory() as db:
        db.add(SocialSlot(day='2026-10-06:s00',owner='original',state='needs_review',
                         post_id='recovered',error='Delivery failed',updated_at=datetime.utcnow(),attempts=1))
        db.commit()
    seed_legacy_hold({'id':'recovered'})
    result=client.post('/api/social/trigger',headers=AUTH).json()
    assert result['state']=='delivery_hold' and result['delivery_check']=='requested'
    assert social.budget.cached('publishing-hold') is None
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='published'
    with factory() as db:
        job=db.get(SocialSlot,'2026-10-06:s00')
        assert job.post_id=='recovered' and job.attempts==1 and job.error is None
    assert not submitted


@pytest.mark.parametrize('post', [None,{'id':'held','status':'scheduled'}, {'id':'held','status':'error'}, {'id':'held','status':'draft'}])
def test_legacy_hold_is_replaced_by_post_level_state_without_resubmission(setup,monkeypatch,post):
    client,factory,_,submitted=setup
    with factory() as db:
        db.add(SocialSlot(day='2026-10-05:s02',owner='old',state='needs_review',updated_at=datetime.utcnow(),attempts=1,post_id='held'));db.commit()
    calls=[]
    def read(query,variables):
        assert 'createPost' not in query
        calls.append(variables)
        return {'post':post}
    monkeypatch.setattr(social.worker,'buffer',read)
    seed_legacy_hold({'id':'held'})
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='delivery_hold'
    assert social.budget.cached('publishing-hold') is None
    assert calls==[{'id':'held'}] and not submitted
    with factory() as db:
        row=db.get(SocialSlot,'2026-10-05:s02')
        assert row.state==('needs_review' if post is None else {'scheduled':'scheduled','error':'delivery_failed','draft':'blocked'}[post['status']])


def test_hold_survives_status_read_failure(setup,monkeypatch):
    client,_,_,submitted=setup
    def fail(*args):
        raise social.worker.ServiceError('Buffer local free-tier budget reached')
    monkeypatch.setattr(social.worker,'buffer',fail)
    seed_legacy_hold({'id':'held'})
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='delivery_hold'
    assert social.budget.cached('publishing-hold')['post_id']=='held'
    assert not submitted


def test_recovery_cannot_clear_a_replaced_hold(setup,monkeypatch):
    client,_,_,submitted=setup
    seed_legacy_hold({'id':'held'})
    def read(*args):
        social.budget.cache('publishing-hold',{'post_id':'new-failure','reason':'review'},86400)
        return {'post':{'id':'held','status':'sent'}}
    monkeypatch.setattr(social.worker,'buffer',read)
    client.post('/api/social/trigger',headers=AUTH)
    assert social.budget.cached('publishing-hold')['post_id']=='new-failure'
    assert not submitted


def test_stale_failure_list_cannot_rehold_confirmed_sent_post_or_duplicate_it(setup,monkeypatch):
    client,_,_,submitted=setup
    monkeypatch.setattr(social.worker,'posts',lambda *a:[{'id':'recovered','status':'error',
        'text':'Existing post\nJeeEdge daily 2026-10-06 / s00'}])
    client.post('/api/social/trigger',headers=AUTH)
    assert social.budget.cached('publishing-hold') is None
    assert client.get('/api/social/status',headers=AUTH).json()['jobs'][0]['post_id']=='recovered'
    assert not submitted


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
    result=client.post('/api/social/test-reel?require_voice=true',headers=AUTH)
    assert result.status_code==202 and not submitted
    with factory() as db:
        job=db.get(SocialSlot,'2026-10-06:s99')
        assert job.state=='failed' and 'all narration scenes' in job.error
    retry=client.post('/api/social/test-reel?require_voice=true',headers=AUTH).json()
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
    client.post('/api/social/test-reel?require_voice=true',headers=AUTH)
    assert not submitted


def test_manual_respects_auth_pause_and_delivery_hold(setup,monkeypatch):
    client,_,_,submitted=setup
    assert client.post('/api/social/test-reel').status_code==401
    monkeypatch.setenv('SOCIAL_TTS_ENABLED','false')
    assert client.post('/api/social/test-reel?require_voice=true',headers=AUTH).status_code==503
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
