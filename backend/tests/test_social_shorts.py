import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
from datetime import datetime,timedelta
import json
import pytest
from app.models.social_job import SocialShort,SocialSlot,SocialAsset,SocialCache,SocialUsage
from app.services import social_shorts as shorts,social_pipeline as pipeline
from app.routers import social_slots as social
from test_social_slots import setup,AUTH


def enable(factory,starts=None,channel='tube'):
    with factory() as db:
        pipeline.write(db,shorts.CONFIG,{'enabled':True,'channel_id':channel,'starts_at':pipeline.stamp(starts or datetime.utcnow()-timedelta(seconds=1)),'updated_at':None},3650*86400);db.commit()


def source(setup,monkeypatch,enabled=True):
    client,factory,clock,instagram=setup
    if enabled:enable(factory)
    monkeypatch.setattr(social.worker,'find_youtube_channel',lambda channel:{'id':channel,'organization_id':'org','name':'Jee Edge'})
    clock[0]=clock[0].replace(hour=9,minute=40)
    # These unit tests inspect a prepared checkpoint before submission. The
    # integration test below exercises the complete same-trigger handoff.
    with monkeypatch.context() as preparation:
        preparation.setattr(shorts,'tick',lambda:None)
        assert client.post('/api/social/trigger',headers=AUTH).status_code==202
    return client,factory,instagram


def uploader(monkeypatch,factory,response=None,error=None):
    original=social.worker.buffer;calls=[]
    def buffer(query,variables):
        if 'createPost' not in query:return {'post':{'id':variables['id'],'status':'sent','schedulingType':'automatic'}}
        payload=variables['input']
        if payload['channelId']!='tube':return original(query,variables)
        with factory() as db:assert db.get(SocialShort,'2026-10-06:s02').state=='submitting'
        calls.append(payload)
        if error:raise error
        return {'createPost':{'post':response or {'id':'yt1','status':'scheduled'}}}
    monkeypatch.setattr(social.worker,'buffer',buffer)
    return calls


def test_disabled_default_has_no_youtube_posts_or_configuration_probes(setup,monkeypatch):
    client,factory,instagram=source(setup,monkeypatch,enabled=False)
    shorts.tick()
    with factory() as db:assert db.query(SocialShort).count()==0
    assert len(instagram)==1
    data=client.get('/api/social/status',headers=AUTH).json()['youtube']
    assert data['settings']['enabled'] is False and data['jobs']==[]


def test_reuses_exact_video_and_metadata_once_without_affecting_instagram(setup,monkeypatch):
    client,factory,instagram=source(setup,monkeypatch)
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');asset=row.asset_id
        assert row.state=='ready'
    calls=uploader(monkeypatch,factory)
    monkeypatch.setattr(social.reel,'render',lambda *a,**k:pytest.fail('Shorts must never render another video'))
    shorts.tick();shorts.tick()
    assert len(calls)==1 and len(instagram)==1
    assert calls[0]['assets']==[{'video':{'url':social.media_origin()+f'/api/social/assets/{asset}.mp4'}}]
    meta=calls[0]['metadata']['youtube']
    assert meta['categoryId']=='27' and meta['privacy']=='public' and meta['madeForKids'] is False
    assert len(meta['title'])<=100 and '#Shorts' in meta['title']
    assert 'utm_source=youtube' in calls[0]['text'] and 'JeeEdge Shorts 2026-10-06 / s02' in calls[0]['text']
    assert calls[0]['schedulingType']=='automatic' and 'instagram' not in calls[0]['metadata']
    with factory() as db:
        assert db.get(SocialShort,'2026-10-06:s02').state=='scheduled'
        assert db.get(SocialSlot,'2026-10-06:s02').state=='scheduled'


def test_uncertain_youtube_upload_is_not_resent_and_instagram_is_unchanged(setup,monkeypatch):
    _,factory,_=source(setup,monkeypatch)
    calls=uploader(monkeypatch,factory,error=social.worker.ServiceError('Upload response timed out'))
    shorts.tick();shorts.tick()
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');assert row.state=='needs_review' and not row.post_id
        assert db.get(SocialSlot,row.day).state=='scheduled'
    assert len(calls)==1
    monkeypatch.setattr(social.worker,'posts',lambda *a:[{'id':'yt-recovered','status':'sent','schedulingType':'automatic','text':calls[0]['text']}])
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');row.updated_at=datetime.utcnow()-timedelta(minutes=20)
        cache=db.get(SocialCache,'youtube-delivery-check')
        if cache:db.delete(cache)
        db.commit()
    shorts.check(True)
    with factory() as db:assert db.get(SocialShort,'2026-10-06:s02').state=='published'
    assert len(calls)==1


def test_channel_or_preparation_failure_does_not_poison_instagram(setup,monkeypatch):
    client,factory,clock,instagram=setup;enable(factory)
    monkeypatch.setattr(shorts,'prepare',lambda day:(_ for _ in ()).throw(RuntimeError('checkpoint failed')))
    clock[0]=clock[0].replace(hour=9,minute=40)
    client.post('/api/social/trigger',headers=AUTH)
    with factory() as db:assert db.get(SocialSlot,'2026-10-06:s02').state=='scheduled'
    assert len(instagram)==1


def test_carousels_and_manual_test_reels_do_not_become_shorts(setup):
    client,factory,_,_=setup;enable(factory)
    client.post('/api/social/trigger',headers=AUTH)
    client.post('/api/social/test-reel',headers=AUTH)
    shorts.prepare_recent()
    with factory() as db:assert db.query(SocialShort).count()==0


def test_enabling_does_not_backfill_existing_prepared_reels(setup,monkeypatch):
    _,factory,_=source(setup,monkeypatch,enabled=False)
    enable(factory,starts=datetime.utcnow()+timedelta(seconds=1))
    shorts.prepare_recent()
    with factory() as db:assert db.query(SocialShort).count()==0


def test_read_only_delivery_check_cannot_submit_ready_short(setup,monkeypatch):
    client,factory,_=source(setup,monkeypatch)
    calls=uploader(monkeypatch,factory)
    response=client.post('/api/social/reconcile',headers=AUTH)
    assert response.json()['publishes_new_work'] is False
    assert calls==[]
    with factory() as db:assert db.get(SocialShort,'2026-10-06:s02').state=='ready'


def test_instagram_hold_does_not_stop_an_already_prepared_short(setup,monkeypatch):
    client,factory,_=source(setup,monkeypatch)
    calls=uploader(monkeypatch,factory)
    social.budget.cache('publishing-hold',{'reason':'Explicit Instagram hold'},3600)
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='delivery_hold'
    assert len(calls)==1


def test_notification_and_published_states_are_not_confused(setup,monkeypatch):
    _,factory,_=source(setup,monkeypatch)
    uploader(monkeypatch,factory,response={'id':'yt1','status':'sent','schedulingType':'notification'})
    shorts.tick()
    with factory() as db:assert db.get(SocialShort,'2026-10-06:s02').state=='needs_review'
    shorts.record('2026-10-06:s02',{'id':'yt1','status':'sent','schedulingType':'automatic'})
    shorts.record('2026-10-06:s02',{'id':'yt1','status':'error'})
    with factory() as db:assert db.get(SocialShort,'2026-10-06:s02').state=='published'


def test_disable_during_preflight_stops_before_submission_fence(setup,monkeypatch):
    _,factory,_=source(setup,monkeypatch)
    calls=uploader(monkeypatch,factory);original=social.worker.request
    def fetch(*args,**kwargs):
        body=original(*args,**kwargs)
        with factory() as db:
            config=shorts.settings(db);config['enabled']=False;pipeline.write(db,shorts.CONFIG,config);db.commit()
        return body
    monkeypatch.setattr(social.worker,'request',fetch)
    shorts.tick()
    assert calls==[]
    with factory() as db:assert db.get(SocialShort,'2026-10-06:s02').state=='failed'


def test_media_retention_waits_for_both_platforms(setup,monkeypatch):
    _,factory,_=source(setup,monkeypatch)
    day='2026-10-06:s02';old=datetime.utcnow()-timedelta(days=3)
    with factory() as db:
        ig=db.get(SocialSlot,day);ig.state='published';ig.updated_at=old
        yt=db.get(SocialShort,day);yt.state='scheduled';yt.updated_at=old;db.commit()
        social.cleanup(db);db.commit();assert db.query(SocialAsset).filter_by(day=day).count()==1
    shorts.record(day,{'id':'yt1','status':'sent'})
    with factory() as db:
        social.cleanup(db);db.commit();assert db.query(SocialAsset).filter_by(day=day).count()==1
        db.get(SocialShort,day).updated_at=old;db.commit()
        social.cleanup(db);db.commit();assert db.query(SocialAsset).filter_by(day=day).count()==0


def test_admin_setup_auth_channel_selection_and_confirmation(setup,monkeypatch):
    client,factory,_,instagram=setup
    client.app.include_router(social.admin_router)
    assert client.get('/api/admin/social/youtube/channels').status_code!=200
    client.app.dependency_overrides[social._require_admin]=lambda:'verified-admin'
    channel={'id':'tube','service':'youtube','organization_id':'org','displayName':'Jee Edge'}
    monkeypatch.setattr(social.worker,'youtube_channels',lambda:[channel])
    assert client.get('/api/admin/social/youtube/channels').json()['channels'][0]['id']=='tube'
    assert client.post('/api/admin/social/youtube/config',json={'enabled':True}).status_code==422
    result=client.post('/api/admin/social/youtube/config',json={'enabled':True,'channel_id':'tube'})
    assert result.status_code==200 and result.json()['publishes_new_work'] is False
    assert client.post('/api/admin/social/youtube/config',json={'enabled':False}).status_code==409
    assert instagram==[]


@pytest.mark.parametrize('url,valid',[
 ('https://www.youtube.com/shorts/AbCdEf123_-',True),('https://youtu.be/AbCdEf123_-',True),
 ('https://www.youtube.com/watch?v=AbCdEf123_-&tracking=x',True),
 ('https://youtube.com.evil.test/shorts/AbCdEf123_-',False),('https://youtube.com/@channel',False),
 ('javascript:alert(1)',False),('https://user@youtube.com/shorts/AbCdEf123_-',False)])
def test_youtube_links_are_restricted_to_real_video_urls(url,valid):
    assert bool(shorts.youtube_link(url)) is valid


def test_admin_safe_retry_and_manual_confirmation_do_not_resend_unknown_posts(setup,monkeypatch):
    client,factory,_=source(setup,monkeypatch)
    calls=uploader(monkeypatch,factory,error=social.worker.ServiceError('no receipt'))
    shorts.tick()
    client.app.include_router(social.admin_router)
    client.app.dependency_overrides[social._require_admin]=lambda:'verified-admin'
    job=client.get('/api/admin/social').json()['youtube']['jobs'][0]
    root='/api/admin/social/youtube/jobs/2026-10-06:s02'
    assert client.post(root+'/retry',json={'expected_updated_at':job['updated_at']}).status_code==409
    body={'expected_updated_at':job['updated_at'],'youtube_url':'https://www.youtube.com/shorts/AbCdEf123_-','confirmed':False}
    assert client.post(root+'/confirm-published',json=body).status_code==422
    body['confirmed']=True
    assert client.post(root+'/confirm-published',json=body).json()['publishes_new_work'] is False
    shorts.record('2026-10-06:s02',{'id':'yt1','status':'error'})
    job=client.get('/api/admin/social').json()['youtube']['jobs'][0]
    assert job['state']=='confirmed_published' and job['published_url']==body['youtube_url']
    assert len(calls)==1
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');row.state='failed';row.post_id=None;row.updated_at=datetime.utcnow();db.commit()
    job=client.get('/api/admin/social').json()['youtube']['jobs'][0]
    assert client.post(root+'/retry',json={'expected_updated_at':job['updated_at']}).json()['will_submit_on_next_trigger'] is True
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');assert row.state=='ready' and row.attempts==0
    assert len(calls)==1


def test_interrupted_presubmission_lease_reuses_asset_and_disabled_work_expires(setup,monkeypatch):
    _,factory,_=source(setup,monkeypatch)
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');asset=row.asset_id
        row.state='running';row.attempts=1;row.updated_at=datetime.utcnow()-timedelta(minutes=20);db.commit()
    calls=uploader(monkeypatch,factory)
    shorts.tick()
    assert len(calls)==1 and asset in calls[0]['assets'][0]['video']['url']
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');row.state='failed';row.post_id=None;row.created_at=datetime.utcnow()-timedelta(days=3)
        config=shorts.settings(db);config['enabled']=False;pipeline.write(db,shorts.CONFIG,config);db.commit()
    shorts.tick()
    with factory() as db:assert db.get(SocialShort,'2026-10-06:s02').state=='expired'
    assert len(calls)==1


def test_youtube_channel_lookup_requires_exact_id_and_connected_state(monkeypatch):
    channels=[{'id':'one','service':'youtube'},{'id':'two','service':'youtube','isDisconnected':True}]
    monkeypatch.setattr(social.worker,'youtube_channels',lambda:channels)
    assert social.worker.find_youtube_channel('one')['id']=='one'
    with pytest.raises(social.worker.ServiceError,match='not available'):social.worker.find_youtube_channel('missing')
    with pytest.raises(social.worker.ServiceError,match='disconnected'):social.worker.find_youtube_channel('two')


def test_shared_budget_defers_without_exhausting_automatic_retries(setup,monkeypatch):
    _,factory,_=source(setup,monkeypatch)
    calls=uploader(monkeypatch,factory)
    with factory() as db:
        db.add(SocialUsage(id='budget-test',service='buffer',created_at=datetime.utcnow(),units=90,tokens=0));db.commit()
    shorts.tick()
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');assert row.state=='ready' and row.attempts==0
        heartbeat=shorts.report(db)['worker']
        assert heartbeat['state']=='deferred' and 'budget' in heartbeat['reason']
        db.get(SocialUsage,'budget-test').created_at=datetime.utcnow()-timedelta(days=31);db.commit()
    shorts.tick()
    assert len(calls)==1


def test_new_reel_submits_its_short_on_the_same_trigger_without_duplicates(setup,monkeypatch):
    client,factory,clock,instagram=setup
    enable(factory)
    monkeypatch.setattr(social.worker,'find_youtube_channel',lambda channel:{'id':channel,'organization_id':'org'})
    calls=uploader(monkeypatch,factory)
    clock[0]=clock[0].replace(hour=9,minute=40)
    assert client.post('/api/social/trigger',headers=AUTH).status_code==202
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02')
        assert row.state=='scheduled' and row.attempts==1 and row.post_id=='yt1'
        assert shorts.report(db)['worker']['state']=='processed'
    assert len(calls)==1 and len(instagram)==1
    assert client.post('/api/social/trigger',headers=AUTH).status_code==202
    assert len(calls)==1 and len(instagram)==1


def test_admin_can_drain_waiting_short_without_creating_an_instagram_post(setup,monkeypatch):
    client,factory,instagram=source(setup,monkeypatch)
    client.app.include_router(social.admin_router)
    assert client.post('/api/admin/social/youtube/trigger').status_code!=202
    client.app.dependency_overrides[social._require_admin]=lambda:'verified-admin'
    calls=uploader(monkeypatch,factory)
    assert client.post('/api/admin/social/youtube/trigger').json()['instagram_unchanged'] is True
    assert len(calls)==1 and len(instagram)==1
    assert client.post('/api/admin/social/youtube/trigger').status_code==202
    assert len(calls)==1 and len(instagram)==1
    with factory() as db:
        config=shorts.settings(db);config['enabled']=False;pipeline.write(db,shorts.CONFIG,config);db.commit()
    assert client.post('/api/admin/social/youtube/trigger').status_code==409
