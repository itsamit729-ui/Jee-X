"""Reward idempotency and stale-session regressions; no production DB writes."""
import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import date, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import models
from app.database import Base
from app.services import rewards


@pytest.fixture
def sessions(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "rewards.db"}')
    tables = [models.User, models.StudentProfile, models.EdgeCoinTransaction,
              models.RewardCatalogItem, models.RewardRedemption]
    Base.metadata.create_all(engine, tables=[m.__table__ for m in tables])
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    with factory() as db:
        db.add(models.User(id=1,auth0_sub='student',username='student',name='Student',role='student',status='active'))
        db.flush()
        db.add(models.StudentProfile(user_id=1,dob=date(2008,1,1),class_12_year=2027,target_year=2027,target_exam='jee_main',edge_coins=0,current_streak=0,longest_streak=0))
        db.commit()
    yield factory
    engine.dispose()


def test_same_day_retries_and_next_ist_day(sessions):
    with sessions() as db:
        user=db.get(models.User,1)
        day=date(2026,9,20)
        assert rewards.update_streak_and_award(db,user,day)==1
        assert rewards.update_streak_and_award(db,user,day)==0
        db.commit()
        assert rewards.update_streak_and_award(db,user,day)==0
        assert rewards.update_streak_and_award(db,user,day+timedelta(days=1))==1
        db.commit()
        assert user.student_profile.edge_coins==2
        assert user.student_profile.current_streak==2
        assert [t.note for t in db.query(models.EdgeCoinTransaction).order_by(models.EdgeCoinTransaction.id)]==['2026-09-20','2026-09-21']


def test_stale_session_does_not_award_twice(sessions):
    with sessions() as first, sessions() as stale:
        user=stale.get(models.User,1)
        assert user.student_profile.last_streak_date is None
        rewards.update_streak_and_award(first,first.get(models.User,1),date(2026,9,20)); first.commit()
        assert rewards.update_streak_and_award(stale,user,date(2026,9,20))==0
        stale.commit()
        assert user.student_profile.edge_coins==1
        assert stale.query(models.EdgeCoinTransaction).count()==1


def test_ledger_protects_against_reset_streak(sessions):
    with sessions() as db:
        user=db.get(models.User,1)
        rewards.update_streak_and_award(db,user,date(2026,9,20));db.commit()
        user.student_profile.last_streak_date=None;db.commit()
        assert rewards.update_streak_and_award(db,user,date(2026,9,20))==0
        assert db.query(models.EdgeCoinTransaction).count()==1


def test_streak_bonus_and_wallet_are_preserved(sessions):
    with sessions() as db:
        user=db.get(models.User,1)
        for n in range(7):
            amount=rewards.update_streak_and_award(db,user,date(2026,9,1)+timedelta(days=n))
            assert amount==(6 if n==6 else 1)
            db.commit()
        assert user.student_profile.current_streak==7
        assert user.student_profile.edge_coins==12
        assert rewards.update_streak_and_award(db,user,date(2026,9,7))==0
        # A broken streak rebuilt to seven does not re-award its lifetime bonus.
        for n in range(7):
            assert rewards.update_streak_and_award(db,user,date(2026,9,10)+timedelta(days=n))==1
            db.commit()
        assert db.query(models.EdgeCoinTransaction).filter_by(reason='streak_bonus').count()==1


def test_rollback_keeps_day_eligible(sessions):
    with sessions() as db:
        user=db.get(models.User,1)
        rewards.update_streak_and_award(db,user,date(2026,9,20));db.rollback()
        assert rewards.update_streak_and_award(db,user,date(2026,9,20))==1
        db.commit()
        assert db.query(models.EdgeCoinTransaction).count()==1


def test_stale_redemption_cannot_spend_previous_balance(sessions):
    shipping=dict(shipping_name='Student',shipping_line1='Line 1',shipping_city='City',shipping_state='State',shipping_pincode='123456',shipping_phone='1234567890')
    with sessions() as seed:
        seed.get(models.StudentProfile,1).edge_coins=10
        seed.add(models.RewardCatalogItem(id=1,name='Reward',cost_coins=10,is_active=True));seed.commit()
    with sessions() as first, sessions() as stale:
        user=stale.get(models.User,1);assert user.student_profile.edge_coins==10
        rewards.redeem(first,first.get(models.User,1),first.get(models.RewardCatalogItem,1),shipping);first.commit()
        with pytest.raises(ValueError,match='Insufficient'):
            rewards.redeem(stale,user,stale.get(models.RewardCatalogItem,1),shipping)
        stale.rollback()
        assert stale.query(models.RewardRedemption).count()==1
        assert stale.get(models.StudentProfile,1).edge_coins==0
