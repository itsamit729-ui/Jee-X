"""Launch preferences only. These records never grant paid entitlements."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.database import Base


class PlanInterest(Base):
    __tablename__ = 'plan_interests'
    account_id = Column(String(36), ForeignKey('auth_accounts.id', ondelete='CASCADE'), primary_key=True)
    plan = Column(String(32), nullable=False)
    price_inr = Column(Integer, nullable=False)
    period_months = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, index=True)
