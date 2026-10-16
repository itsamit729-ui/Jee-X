import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
from datetime import datetime, timedelta

import pytest

from app.models.social_job import SocialCache, SocialUsage
from app.services import social_budget as budget, social_pipeline as pipeline
from test_social_slots import setup


def test_buffer_daily_headroom_matches_free_plan_and_preserves_usage(setup):
    _,factory,_,_=setup
    with factory() as db:
        # Outside the burst window but still inside the daily window.
        made=datetime.utcnow()-timedelta(hours=1)
        db.add(SocialUsage(id='daily',service='buffer',created_at=made,units=200,tokens=0));db.commit()
        budget.check(db,'buffer',units=10)
        budget.check(db,'buffer',units=35)
        with pytest.raises(budget.BudgetExceeded) as caught:
            budget.check(db,'buffer',units=36)
        error=caught.value
        assert error.details['windows'][0]['window_seconds']==86400
        assert '24-hour 200/235' in str(error)
        assert pipeline.parse_time(error.retry_at)==made+timedelta(days=1,seconds=1)
        assert db.get(SocialUsage,'daily').units==200


def test_all_exhausted_windows_must_release_before_retry(setup):
    _,factory,_,_=setup
    with factory() as db:
        now=datetime.utcnow()
        db.add(SocialUsage(id='monthly',service='buffer',created_at=now-timedelta(days=2),units=2760,tokens=0))
        db.add(SocialUsage(id='burst',service='buffer',created_at=now,units=90,tokens=0));db.commit()
        with pytest.raises(budget.BudgetExceeded) as caught:
            budget.check(db,'buffer',units=10)
        error=caught.value
        assert {w['window_seconds'] for w in error.details['windows']}=={900,30*86400}
        # Only 10 units need to expire from the monthly window. The new burst
        # expires later than the old monthly batch, so that batch is sufficient.
        assert pipeline.parse_time(error.retry_at)==now+timedelta(days=28,seconds=1)
        assert db.query(SocialUsage).count()==2


def test_provider_cooldown_is_respected_with_a_visible_retry_time(setup):
    _,factory,_,_=setup
    with factory() as db:
        until=datetime.utcnow()+timedelta(minutes=20)
        db.add(SocialCache(name='cooldown:buffer',value='true',expires_at=until));db.commit()
        with pytest.raises(budget.BudgetExceeded) as caught:
            budget.check(db,'buffer',units=1)
        assert pipeline.parse_time(caught.value.retry_at)==until
        assert caught.value.details['source']=='provider_cooldown'


def test_render_budget_wait_does_not_spend_attempts_and_reports_real_release(setup):
    from app.routers import social_slots as social
    from app.models.social_job import SocialSlot
    from test_social_slots import AUTH
    client,factory,clock,submitted=setup
    made=datetime.utcnow()-timedelta(hours=3)
    with factory() as db:
        db.add(SocialUsage(id='renders',service='render',created_at=made,units=1630,tokens=0))
        db.add(SocialSlot(day='2026-10-06:s00',owner='old',state='failed',attempts=2,
                          updated_at=datetime.utcnow()-timedelta(minutes=20)))
        db.commit()
    for _ in range(4):
        response=client.post('/api/social/trigger',headers=AUTH)
        assert response.status_code==202,response.text
        wait=response.json()
        assert wait['state']=='budget_wait' and wait['attempts']==2
        assert pipeline.parse_time(wait['retry_after'])==made+timedelta(days=1,seconds=1)
        assert wait['budget']['service']=='render'
    with factory() as db:
        assert db.get(SocialSlot,'2026-10-06:s00').attempts==2
        assert db.get(SocialUsage,'renders').units==1630
        # Rolling usage expiring, rather than a ledger reset, releases the slot.
        db.get(SocialUsage,'renders').created_at=datetime.utcnow()-timedelta(days=2)
        db.commit()
    assert client.post('/api/social/trigger',headers=AUTH).json()['state']=='running'
    assert len(submitted)==1


def test_budget_race_in_background_restores_attempt_and_keeps_retry_checkpoint(setup,monkeypatch):
    from app.routers import social_slots as social
    from app.models.social_job import SocialSlot
    from test_social_slots import AUTH
    client,factory,clock,submitted=setup
    real=social.budget.admission
    retry=pipeline.stamp(datetime.utcnow()+timedelta(hours=2))
    def raced(db=None):
        if db is not None:return real(db)
        raise budget.BudgetExceeded('render capacity changed',retry,{'service':'render'})
    monkeypatch.setattr(social.budget,'admission',raced)
    client.post('/api/social/trigger',headers=AUTH)
    assert not submitted
    with factory() as db:
        job=db.get(SocialSlot,'2026-10-06:s00')
        assert job.state=='failed' and job.attempts==0
        progress=pipeline.read(db,pipeline.key('progress',job.day))
        assert progress['stage']=='budget_wait' and progress['retry_after']==retry


def test_prepared_media_can_publish_while_new_rendering_is_waiting(setup,monkeypatch):
    from app.routers import social_slots as social
    from app.models.social_job import SocialSlot
    from test_social_slots import AUTH
    client,factory,clock,submitted=setup
    fetch=social.worker.request
    def unavailable(*args,**kwargs):
        raise social.worker.ServiceError('Temporary media verification failure')
    monkeypatch.setattr(social.worker,'request',unavailable)
    client.post('/api/social/trigger',headers=AUTH)
    assert not submitted
    with factory() as db:
        job=db.get(SocialSlot,'2026-10-06:s00')
        assert pipeline.read(db,pipeline.key('prepared',job.day))
        job.updated_at=datetime.utcnow()-timedelta(minutes=20)
        db.add(SocialUsage(id='render-full',service='render',created_at=datetime.utcnow(),units=1800,tokens=0))
        db.commit()
    monkeypatch.setattr(social.worker,'request',fetch)
    def no_render(*args,**kwargs):
        raise AssertionError('Prepared media must not be rendered twice')
    monkeypatch.setattr(social.worker,'render',no_render)
    client.post('/api/social/trigger',headers=AUTH)
    assert len(submitted)==1
