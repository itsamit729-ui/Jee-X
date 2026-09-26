"""Service 7: Edge Coins wallet + reward redemption. Earning happens in
app/services/rewards.py, hooked into grading (subject_test_attempts.py) and the daily-question
streak (daily_question.py) — this router only reads the wallet and handles redemption requests.
No admin fulfillment UI exists yet; a redemption just creates a 'pending' request row."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.deps import get_current_db_user
from app.services import rewards

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


@router.get("", response_model=schemas.WalletOut)
def get_wallet(user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    profile = user.student_profile
    transactions = (
        db.query(models.EdgeCoinTransaction)
        .filter(models.EdgeCoinTransaction.user_id == user.id)
        .order_by(models.EdgeCoinTransaction.created_at.desc())
        .limit(50)
        .all()
    )
    catalog = (
        db.query(models.RewardCatalogItem)
        .filter(models.RewardCatalogItem.is_active.is_(True))
        .order_by(models.RewardCatalogItem.cost_coins.asc())
        .all()
    )
    redemptions = (
        db.query(models.RewardRedemption)
        .options(joinedload(models.RewardRedemption.catalog_item))
        .filter(models.RewardRedemption.user_id == user.id)
        .order_by(models.RewardRedemption.requested_at.desc())
        .all()
    )

    return schemas.WalletOut(
        balance=profile.edge_coins or 0,
        transactions=[schemas.EdgeCoinTransactionOut.model_validate(t, from_attributes=True) for t in transactions],
        catalog=[schemas.RewardCatalogItemOut.model_validate(c, from_attributes=True) for c in catalog],
        redemptions=[
            schemas.RewardRedemptionOut(
                id=r.id,
                catalog_item_id=r.catalog_item_id,
                catalog_item_name=r.catalog_item.name,
                coins_spent=r.coins_spent,
                status=r.status,
                requested_at=r.requested_at,
            )
            for r in redemptions
        ],
    )


@router.post("/redeem", response_model=schemas.RewardRedemptionOut, status_code=201)
def redeem(body: schemas.RedeemIn, user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    catalog_item = (
        db.query(models.RewardCatalogItem)
        .filter(models.RewardCatalogItem.id == body.catalog_item_id, models.RewardCatalogItem.is_active.is_(True))
        .first()
    )
    if not catalog_item:
        raise HTTPException(status_code=404, detail="Unknown or inactive reward.")

    shipping = {f"shipping_{k}": v for k, v in body.shipping.model_dump().items()}
    try:
        redemption = rewards.redeem(db, user, catalog_item, shipping)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    db.refresh(redemption)

    return schemas.RewardRedemptionOut(
        id=redemption.id,
        catalog_item_id=redemption.catalog_item_id,
        catalog_item_name=catalog_item.name,
        coins_spent=redemption.coins_spent,
        status=redemption.status,
        requested_at=redemption.requested_at,
    )
