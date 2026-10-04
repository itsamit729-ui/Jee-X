"""Public launch pricing and authenticated interest capture; no billing yet."""
from typing import Literal
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from app import models
from app.auth import get_auth_account, utcnow
from app.database import get_db
from app.routers.admin_dashboard import _require_admin

router = APIRouter(prefix='/api', tags=['plans'])
# The server owns price snapshots; the browser cannot submit a price or entitlement.
PLANS = {
    'plus_monthly': {'price_inr': 249, 'period_months': 1},
    'plus_quarterly': {'price_inr': 599, 'period_months': 3},
    'teacher': {'price_inr': 999, 'period_months': 1},
}

class InterestIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    plan: Literal['plus_monthly', 'plus_quarterly', 'teacher']


def serialize(row):
    return None if row is None else {
        'plan': row.plan, 'price_inr': row.price_inr,
        'period_months': row.period_months,
        'created_at': row.created_at.isoformat() + 'Z',
        'updated_at': row.updated_at.isoformat() + 'Z',
    }

@router.get('/plans')
def catalog():
    return {'checkout_available': False, 'plans': PLANS}

@router.get('/plans/interest')
def interest(account=Depends(get_auth_account), db: Session = Depends(get_db)):
    return {'interest': serialize(db.get(models.PlanInterest, account.id))}

@router.put('/plans/interest')
def save_interest(body: InterestIn, account=Depends(get_auth_account), db: Session = Depends(get_db)):
    # Serialize requests on the account to make retries and simultaneous tabs safe.
    db.query(models.AuthAccount).filter_by(id=account.id).with_for_update().populate_existing().one()
    row = db.query(models.PlanInterest).filter_by(account_id=account.id).with_for_update().populate_existing().first()
    if row is None:
        row = models.PlanInterest(account_id=account.id, created_at=utcnow())
        db.add(row)
    row.plan = body.plan
    row.price_inr = PLANS[body.plan]['price_inr']
    row.period_months = PLANS[body.plan]['period_months']
    row.updated_at = utcnow()
    result = serialize(row)
    db.commit()
    return {'interest': result}

@router.delete('/plans/interest', status_code=204)
def withdraw_interest(account=Depends(get_auth_account), db: Session = Depends(get_db)):
    db.query(models.AuthAccount).filter_by(id=account.id).with_for_update().one()
    db.query(models.PlanInterest).filter_by(account_id=account.id).delete(synchronize_session=False)
    db.commit()
    return Response(status_code=204)

@router.get('/admin/plan-interests')
def admin_interests(offset: int = 0, token=Depends(_require_admin), db: Session = Depends(get_db)):
    from fastapi import HTTPException
    if offset < 0:
        raise HTTPException(422, 'Offset must be non-negative.')
    query = db.query(models.PlanInterest, models.AuthAccount.email).join(
        models.AuthAccount, models.AuthAccount.id == models.PlanInterest.account_id)
    total = query.count()
    rows = query.order_by(models.PlanInterest.updated_at.desc(), models.PlanInterest.account_id).offset(offset).limit(50).all()
    return {'total': total, 'items': [dict(serialize(row), email=email) for row, email in rows]}
