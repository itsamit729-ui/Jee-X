"""Privacy and cohort integration tests against an isolated database."""
import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import date, datetime, timedelta
from io import BytesIO
import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base, get_db
from app.deps import get_current_db_user
from app.routers.public_profiles import router, _buckets


@pytest.fixture
def setup():
    _buckets.clear()
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    tables = [models.User, models.StudentProfile, models.PublicProfile, models.ProfileAvatar, models.JeeXRating,
              models.RatedContest, models.ContestEntry, models.Test, models.TestAttempt, models.DailyQuestionAssignment]
    Base.metadata.create_all(engine, tables=[m.__table__ for m in tables])
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    for uid in (1, 2, 3):
        db.add(models.User(id=uid, auth0_sub=f'private-sub-{uid}', username=f'student{uid}', name='Private real name', email='private@example.com', role='student', status='active'))
        db.flush()
        db.add(models.StudentProfile(user_id=uid, dob=date(2008,1,1), class_12_year=2027, target_year=2027, target_exam='jee_main', leaderboard_visibility='username'))
    db.commit()
    app = FastAPI(); app.include_router(router)
    active = [1]
    def current(): return db.get(models.User, active[0])
    def session(): yield db
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_current_db_user] = current
    yield db, TestClient(app), active, app
    db.close(); engine.dispose()


def enable(c, **extra):
    return c.patch('/api/profile/public-settings', json=dict(enabled=True, show_activity=False, display_name='', bio='', **extra))


def test_avatar_upload_public_display_replacement_and_removal(setup):
    _, c, active, _ = setup
    image = BytesIO()
    Image.new('RGB', (800, 400), 'orange').save(image, 'PNG')
    path = '/api/public-profiles/student1/avatar'
    assert c.get(path).status_code == 404
    uploaded = c.put('/api/profile/avatar', content=image.getvalue(), headers={'Content-Type': 'image/png'})
    assert uploaded.status_code == 200 and uploaded.json() == {'avatar_url': path}
    assert c.get('/api/public-profiles/student1').json()['avatar_url'] == path
    photo = c.get(path)
    assert photo.status_code == 200 and photo.headers['content-type'] == 'image/jpeg'
    assert photo.headers['cache-control'] == 'no-store'
    with Image.open(BytesIO(photo.content)) as decoded:
        assert decoded.size == (256, 128)
    replacement = BytesIO()
    Image.new('RGB', (300, 300), 'blue').save(replacement, 'JPEG')
    assert c.put('/api/profile/avatar', content=replacement.getvalue(), headers={'Content-Type': 'image/jpeg'}).status_code == 200
    new_photo = c.get(path).content
    assert new_photo != photo.content
    assert c.put('/api/profile/avatar', content=b'not an image', headers={'Content-Type': 'image/png'}).status_code == 422
    assert c.get(path).content == new_photo
    active[0] = 2
    assert c.delete('/api/profile/avatar').status_code == 200
    assert c.get(path).status_code == 200
    active[0] = 1
    assert c.delete('/api/profile/avatar').json() == {'avatar_url': None}
    assert c.get('/api/public-profiles/student1').json()['avatar_url'] is None
    assert c.get(path).status_code == 404


def test_avatar_requires_valid_image_and_active_student(setup):
    db, c, _, _ = setup
    assert c.put('/api/profile/avatar', content=b'bad', headers={'Content-Type': 'image/svg+xml'}).status_code == 415
    assert c.put('/api/profile/avatar', content=b'a' * (4 * 1024 * 1024 + 1), headers={'Content-Type': 'image/png'}).status_code == 413
    db.get(models.User, 1).status = 'suspended'
    db.commit()
    assert c.put('/api/profile/avatar', content=b'bad', headers={'Content-Type': 'image/png'}).status_code == 403
    assert c.get('/api/public-profiles/student1/avatar').status_code == 404


def test_public_without_settings_and_legacy_hidden_records(setup):
    db,c,_,_=setup
    assert c.get('/api/profile/public-settings').json()['enabled'] is True
    res=c.get('/api/public-profiles/STUDENT1')
    assert res.status_code == 200 and res.headers['cache-control']=='no-store'
    data=res.json()
    assert set(data)=={'username','display_name','bio','avatar_url','exam','target_year','rating','rank','history','activity'}
    assert data['activity'] is None and data['rating']['rating'] is None
    assert data['display_name']=='' and data['bio']==''
    assert 'private' not in res.text.lower() and '2008' not in res.text
    assert c.get('/api/public-profiles/student1/contests').status_code==200
    assert c.get('/api/public-profiles/missing').status_code==404
    db.add(models.PublicProfile(user_id=1,enabled=False,show_activity=False,display_name='',bio=''))
    db.commit()
    assert c.get('/api/public-profiles/student1').status_code==200
    result=c.patch('/api/profile/public-settings',json={'enabled':False,'show_activity':False})
    assert result.status_code==200 and result.json()['enabled'] is True
    assert c.get('/api/public-profiles/student1').status_code==200
    assert c.get('/api/public-profiles/student1/contests').status_code==200


def test_settings_cannot_edit_other_user_or_rating(setup):
    db,c,active,app=setup
    assert c.patch('/api/profile/public-settings',json={'enabled':True,'show_activity':False,'user_id':2}).status_code==422
    enable(c); active[0]=2
    assert c.get('/api/profile/public-settings').json()['enabled'] is True
    assert c.patch('/api/profile/public-settings',json={'enabled':True,'show_activity':False,'bio':'x'*281}).status_code==422
    app.dependency_overrides.pop(get_current_db_user)
    assert c.get('/api/profile/public-settings').status_code in (401,403)
    assert c.patch('/api/profile/public-settings',json={'enabled':True,'show_activity':False}).status_code in (401,403)
    assert c.get('/api/public-profiles/student1').status_code==200


def test_suspended_and_nonstudent_are_hidden(setup):
    db,c,_,_=setup;enable(c)
    user=db.get(models.User,1); user.status='suspended';db.commit()
    assert c.get('/api/public-profiles/student1').status_code==404
    assert c.get('/api/public-profiles/student1/contests').status_code==404
    assert c.get('/api/profile/public-settings').status_code==403
    assert enable(c).status_code==403
    user.status='active';user.role='admin';db.commit()
    assert c.get('/api/public-profiles/student1').status_code==404


def test_cohort_rank_ties_visibility_and_inactivity(setup):
    db,c,_,_=setup;enable(c)
    for uid,score in [(1,2800),(2,3000),(3,2800)]:
        db.add(models.JeeXRating(user_id=uid,exam='jee_main',target_year=2027,rating=score,peak=score,contests=3,last_rated_at=datetime.utcnow()))
    db.commit()
    assert c.get('/api/public-profiles/student1').json()['rank']==2
    db.get(models.StudentProfile,2).target_year=2028;db.commit()
    assert c.get('/api/public-profiles/student1').json()['rank']==1
    db.get(models.StudentProfile,1).leaderboard_visibility='hidden';db.commit()
    assert c.get('/api/public-profiles/student1').json()['rank'] is None
    db.get(models.StudentProfile,1).leaderboard_visibility='username'
    db.get(models.JeeXRating,(1,'jee_main',2027)).last_rated_at=datetime.utcnow()-timedelta(days=31);db.commit()
    assert c.get('/api/public-profiles/student1').json()['rank'] is None


def test_history_finalization_cohort_and_pagination(setup):
    db,c,_,_=setup;enable(c)
    for i in range(24):
        event=models.RatedContest(title=f'Contest {i}',exam='jee_main',target_year=2028 if i==23 else 2027,opens_at=datetime.utcnow()-timedelta(days=30),closes_at=datetime.utcnow()-timedelta(days=25-i),duration_sec=600,questions=[{'solution':'PRIVATE ANSWER'}],finalized=i!=22)
        db.add(event);db.flush()
        db.add(models.ContestEntry(contest_id=event.id,user_id=1,started_at=event.opens_at,deadline=event.closes_at,answers={'secret':'answer'},score=12,rank=1,rating_before=1500+i,rating_after=1501+i))
    db.commit()
    result=c.get('/api/public-profiles/student1').json()
    assert len(result['history'])==22
    assert result['history'][0]['contest']=='Contest 0'
    assert 'solution' not in str(result) and 'secret' not in str(result)
    history=c.get('/api/public-profiles/student1/contests').json()
    assert history['total']==22 and len(history['entries'])==20
    assert len(c.get('/api/public-profiles/student1/contests?page=2').json()['entries'])==2
    assert c.get('/api/public-profiles/student1/contests?page=0').status_code==422


def test_activity_opt_in_and_stale_streak(setup):
    db,c,_,_=setup;enable(c)
    p=db.get(models.StudentProfile,1);p.current_streak=7;p.longest_streak=12;p.last_streak_date=date.today()-timedelta(days=10);db.commit()
    assert c.get('/api/public-profiles/student1').json()['activity'] is None
    c.patch('/api/profile/public-settings',json={'enabled':True,'show_activity':True})
    assert c.get('/api/public-profiles/student1').json()['activity']=={'current_streak':0,'longest_streak':12,'dates':[]}


def test_public_rate_limit(setup):
    _,c,_,_=setup
    for _ in range(60): assert c.get('/api/public-profiles/missing').status_code==404
    result=c.get('/api/public-profiles/missing')
    assert result.status_code==429 and result.headers['retry-after']=='60'
