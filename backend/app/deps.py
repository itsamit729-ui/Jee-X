from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.auth import get_auth_account
from app.database import get_db


def get_current_db_user(
    account: models.AuthAccount = Depends(get_auth_account),
    db: Session = Depends(get_db),
) -> models.User:
    user = db.get(models.User, account.user_id) if account.user_id else None
    if not user:
        raise HTTPException(status_code=404, detail="Complete onboarding before continuing.")
    return user
