import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import datetime
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.auth import get_auth_account
from app.database import Base, get_db
from app.routers.plans import router
from app.routers.admin_dashboard import _require_admin

@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as db:
        for key in ('one', 'two'):
            db.add(models.AuthAccount(id=key, email=f'{key}@example.com', password_hash='unused', created_at=datetime.utcnow()))
        db.commit()
    app = FastAPI()
    app.include_router(router)
    active = ['one']
    def database():
        with factory() as db:
            yield db
    def account():
        if active[0] is None:
            raise HTTPException(401, 'Sign in required')
        return models.AuthAccount(id=active[0])
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_auth_account] = account
    with TestClient(app) as client:
        yield client, factory, active, app
    engine.dispose()


def test_public_catalog_and_authentication(setup):
    client, _, active, _ = setup
    active[0] = None
    catalog = client.get('/api/plans').json()
    assert catalog['checkout_available'] is False
    assert catalog['plans']['plus_quarterly']['price_inr'] == 599
    assert client.get('/api/plans/interest').status_code == 401
    assert client.put('/api/plans/interest', json={'plan': 'teacher'}).status_code == 401
    assert client.delete('/api/plans/interest').status_code == 401
    assert client.get('/api/admin/plan-interests').status_code == 401


def test_interest_is_idempotent_owned_and_not_entitlement(setup):
    client, factory, active, app = setup
    for _ in range(2):
        response = client.put('/api/plans/interest', json={'plan': 'plus_monthly'})
        assert response.status_code == 200
        assert response.json()['interest']['price_inr'] == 249
    with factory() as db:
        assert db.query(models.PlanInterest).count() == 1
        assert db.get(models.AuthAccount, 'one').user_id is None
        assert db.query(models.TeacherAccess).count() == 0
    active[0] = 'two'
    assert client.get('/api/plans/interest').json()['interest'] is None
    client.delete('/api/plans/interest')
    active[0] = 'one'
    assert client.get('/api/plans/interest').json()['interest']['plan'] == 'plus_monthly'
    updated = client.put('/api/plans/interest', json={'plan': 'teacher'}).json()['interest']
    assert updated['price_inr'] == 999
    app.dependency_overrides[_require_admin] = lambda: 'admin'
    report = client.get('/api/admin/plan-interests').json()
    assert report['total'] == 1
    assert report['items'][0]['email'] == 'one@example.com'
    assert client.get('/api/admin/plan-interests?offset=50').json()['items'] == []
    assert client.get('/api/admin/plan-interests?offset=-1').status_code == 422
    assert client.delete('/api/plans/interest').status_code == 204
    assert client.get('/api/plans/interest').json()['interest'] is None


@pytest.mark.parametrize('body', [{'plan': 'lifetime'}, {'plan': 'plus_monthly', 'price_inr': 1}, {'plan': 'teacher', 'account_id': 'two'}, {'plan': 'teacher', 'active': True}])
def test_rejects_client_prices_accounts_and_entitlements(setup, body):
    client, factory, _, _ = setup
    assert client.put('/api/plans/interest', json=body).status_code == 422
    with factory() as db:
        assert db.query(models.PlanInterest).count() == 0
