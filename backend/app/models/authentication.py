"""Native accounts are independent of legacy Auth0 identities."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from app.database import Base


class AuthAccount(Base):
    __tablename__ = 'auth_accounts'
    id = Column(String(36), primary_key=True)
    email = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    disabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)


class GoogleIdentity(Base):
    __tablename__ = 'auth_google_identities'
    google_sub = Column(String(255), primary_key=True)
    account_id = Column(String(36), ForeignKey('auth_accounts.id', ondelete='CASCADE'), unique=True, nullable=False)


class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    token_hash = Column(String(64), primary_key=True)
    account_id = Column(String(36), ForeignKey('auth_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    csrf_token = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


class AuthEmailToken(Base):
    __tablename__ = 'auth_email_tokens'
    token_hash = Column(String(64), primary_key=True)
    account_id = Column(String(36), ForeignKey('auth_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    purpose = Column(String(16), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


class AuthRateLimit(Base):
    __tablename__ = 'auth_rate_limits'
    key = Column(String(64), primary_key=True)
    hits = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=False, index=True)
