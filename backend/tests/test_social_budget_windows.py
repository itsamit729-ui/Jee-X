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
