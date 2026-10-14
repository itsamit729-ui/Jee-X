"""Delivery recovery must never create a second copy of an uncertain post."""
from datetime import datetime,timedelta
import pytest
from test_social_slots import setup,AUTH,seed_legacy_hold
from app.models.social_job import SocialSlot,SocialAsset,SocialCache
from app.routers import social_slots as social


def release_retry(factory,key):
    with factory() as db:
        row=db.get(SocialSlot,key);row.updated_at=datetime.utcnow()-timedelta(minutes=16)
        cached=db.get(SocialCache,'delivery-reconciliation')
        if cached:db.delete(cached)
        db.commit()


def test_status_is_read_only_and_explains_missing_cron(setup,monkeypatch):
    client,factory,_,submitted=setup
    monkeypatch.setattr(social.worker,'buffer',lambda *a:pytest.fail('Status must not call a provider'))
    response=client.get('/api/social/status',headers=AUTH)
    data=response.json()
    assert data['read_only'] is True
    assert any(i['code']=='cron_missing' for i in data['health']['issues'])
    assert data['cron']['path']=='/api/social/trigger' and data['cron']['method']=='POST'
    assert not submitted and not data['jobs']
    assert ('x'*32) not in response.text


def test_retry_recovers_previous_window_with_same_marker(setup,monkeypatch):
    client,factory,clock,submitted=setup
    original=social.worker.render
    monkeypatch.setattr(social.worker,'render',lambda *a:(_ for _ in ()).throw(social.worker.ServiceError('Renderer unavailable')))
    client.post('/api/social/trigger',headers=AUTH)
    immediate=client.post('/api/social/trigger',headers=AUTH).json()
    assert immediate['state']=='failed' and immediate['attempts']==1 and immediate['retry_after']
    release_retry(factory,'2026-10-06:s00')
    clock[0]=clock[0].replace(hour=8,minute=20)
    monkeypatch.setattr(social.worker,'render',original)
    response=client.post('/api/social/trigger',headers=AUTH).json()
    assert response['slot']=='s00' and response['attempts']==2
    assert len(submitted)==1 and submitted[0]['text'].endswith('JeeEdge daily 2026-10-06 / s00')


def test_prepared_reel_survives_failed_public_fetch_and_origin_correction(setup,monkeypatch):
    client,factory,clock,submitted=setup
    clock[0]=clock[0].replace(hour=9,minute=40)
    fetch=social.worker.request
    render=social.reel.render
    rendered=[]
    def counted(*args):rendered.append(1);return render(*args)
    monkeypatch.setattr(social.reel,'render',counted)
    monkeypatch.setattr(social.worker,'request',lambda *a,**kw:b'<html>wrong origin</html>')
    client.post('/api/social/trigger',headers=AUTH)
    with factory() as db:
        ids=[a.id for a in db.query(SocialAsset).all()]
    assert client.get('/api/social/status',headers=AUTH).json()['jobs'][0]['prepared'] is True
    assert not submitted
    release_retry(factory,'2026-10-06:s02')
    monkeypatch.setenv('SOCIAL_MEDIA_ORIGIN','https://correct-media.example')
    monkeypatch.setattr(social.worker,'request',fetch)
    clock[0]=clock[0].replace(hour=11,minute=0)
    client.post('/api/social/trigger',headers=AUTH)
    assert len(rendered)==1 and len(submitted)==1
    assert submitted[0]['metadata']['instagram']['type']=='reel'
    assert submitted[0]['assets'][0]['video']['url'].startswith('https://correct-media.example/')
    with factory() as db:assert [a.id for a in db.query(SocialAsset).all()]==ids


def test_delivery_reconciles_older_slots_outside_publish_window(setup):
    client,factory,clock,submitted=setup
    client.post('/api/social/trigger',headers=AUTH)
    clock[0]=clock[0].replace(hour=23,minute=30)
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='idle'
    with factory() as db:assert db.get(SocialSlot,'2026-10-06:s00').state=='published'
    assert len(submitted)==1


def test_manual_test_uses_production_music_fallback_without_groq(setup,monkeypatch):
    client,_,clock,submitted=setup
    monkeypatch.delenv('GROQ_API_KEY')
    monkeypatch.setenv('SOCIAL_TTS_ENABLED','false')
    clock[0]=clock[0].replace(hour=2)
    assert client.post('/api/social/test-reel',headers=AUTH).status_code==202
    assert len(submitted)==1 and submitted[0]['metadata']['instagram']['type']=='reel'


def test_notifications_and_drafts_cannot_be_claimed_as_published(setup):
    client,factory,_,_=setup
    client.post('/api/social/trigger',headers=AUTH)
    social.record_delivery({'id':'p1','status':'sent','schedulingType':'notification'})
    with factory() as db:assert db.get(SocialSlot,'2026-10-06:s00').state=='needs_review'
    social.record_delivery({'id':'p1','status':'needs_approval'})
    with factory() as db:assert db.get(SocialSlot,'2026-10-06:s00').state=='blocked'
    social.record_delivery({'id':'p1','status':'sent','schedulingType':'automatic'})
    social.record_delivery({'id':'p1','status':'error'})
    with factory() as db:assert db.get(SocialSlot,'2026-10-06:s00').state=='published'


def test_two_recent_delivery_failures_trip_circuit_without_resending(setup,monkeypatch):
    client,factory,clock,submitted=setup
    client.post('/api/social/trigger',headers=AUTH)
    first=submitted[0]['text']
    monkeypatch.setattr(social.worker,'posts',lambda *a:[{'id':'p1','status':'error','text':first}])
    clock[0]=clock[0].replace(hour=8,minute=20)
    client.post('/api/social/trigger',headers=AUTH)
    assert len(submitted)==2
    second=submitted[1]['text']
    monkeypatch.setattr(social.worker,'posts',lambda *a:[{'id':'p1','status':'error','text':first},{'id':'p2','status':'error','text':second}])
    clock[0]=clock[0].replace(hour=9,minute=40)
    client.post('/api/social/trigger',headers=AUTH)
    assert len(submitted)==2
    with factory() as db:
        assert 'Two recent' in db.get(SocialSlot,'2026-10-06:s02').error
    release_retry(factory,'2026-10-06:s02')
    monkeypatch.setattr(social.worker,'posts',lambda *a:[{'id':'p1','status':'sent','text':first},{'id':'p2','status':'error','text':second}])
    client.post('/api/social/trigger',headers=AUTH)
    assert len(submitted)==3
    assert len({p['text'].splitlines()[-1] for p in submitted})==3


def test_admin_can_check_delivery_but_cannot_publish_from_panel(setup):
    client,factory,_,submitted=setup
    client.app.include_router(social.admin_router)
    assert client.get('/api/admin/social').status_code==401
    assert client.post('/api/admin/social/reconcile').status_code==401
    client.app.dependency_overrides[social._require_admin]=lambda:'verified-admin'
    assert client.get('/api/admin/social').json()['read_only'] is True
    response=client.post('/api/admin/social/reconcile').json()
    assert response['publishes_new_work'] is False and not submitted


def test_media_cleanup_keeps_uncertain_assets_and_recent_confirmations(setup):
    _,factory,_,_=setup
    with factory() as db:
        for index,state in enumerate(['published','needs_review','scheduled','failed']):
            key=f'2026-10-01:s{index:02}'
            db.add(SocialSlot(day=key,owner='old',state=state,updated_at=datetime.utcnow()-timedelta(days=3),attempts=1,post_id=None if state=='failed' else str(index)))
            db.flush();db.add(SocialAsset(id=str(index)*32,day=key,mime='video/mp4',image=b'video'))
        db.commit();social.cleanup(db);db.commit()
        assert {a.day for a in db.query(SocialAsset).all()}=={'2026-10-01:s01','2026-10-01:s02'}


def test_admin_confirmation_records_existing_post_without_sending_or_retrying(setup):
    client,factory,_,submitted=setup
    client.post('/api/social/trigger',headers=AUTH)
    social.record_delivery({'id':'p1','status':'error'})
    client.app.include_router(social.admin_router)
    client.app.dependency_overrides[social._require_admin]=lambda:'verified-admin'
    row=client.get('/api/admin/social').json()['jobs'][0]
    body={'expected_updated_at':row['updated_at'],'instagram_url':'https://www.instagram.com/reel/verified123/','confirmed':False}
    path='/api/admin/social/jobs/2026-10-06:s00/confirm-published'
    assert client.post(path,json=body).status_code==422
    body['confirmed']=True
    assert client.post(path,json={**body,'instagram_url':'https://evil.example/reel/fake'}).status_code==422
    assert client.post(path,json=body).json()['publishes_new_work'] is False
    assert client.post(path,json=body).status_code==409
    assert len(submitted)==1
    data=client.get('/api/admin/social').json()['jobs'][0]
    assert data['state']=='confirmed_published' and data['published_url']==body['instagram_url']
    social.record_delivery({'id':'p1','status':'error'})
    social.record_delivery({'id':'p1','status':'sent'})
    with factory() as db:assert db.get(SocialSlot,'2026-10-06:s00').state=='confirmed_published'
    refreshed=client.get('/api/admin/social').json()['jobs'][0]
    assert refreshed['published_url']==body['instagram_url'] and refreshed['operator_confirmed_at']


def test_pagination_is_bounded_and_preserves_posts(monkeypatch):
    from social import worker
    pages=[]
    def read(query,variables):
        pages.append(variables['after'])
        return {'posts':{'edges':[{'node':{'id':str(len(pages))}}],'pageInfo':{'hasNextPage':len(pages)==1,'endCursor':'next'}}}
    monkeypatch.setattr(worker,'buffer',read)
    assert [p['id'] for p in worker.posts('org','channel','2026-10-10')]==['1','2']
    assert pages==[None,'next']
    monkeypatch.setattr(worker,'buffer',lambda *a:{'posts':{'edges':[],'pageInfo':{'hasNextPage':True,'endCursor':None}}})
    with pytest.raises(worker.ServiceError,match='did not advance'):worker.posts('org','channel','2026-10-10')
