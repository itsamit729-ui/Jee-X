"""Fresh first-party accounts; no automatic linking to legacy students."""
import secrets
import hmac
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth import (COOKIE_NAME, clear_session_cookie, cookie_options, digest, find_session,
                      get_auth_account, require_browser_request, utcnow)
from app.database import get_db
from app.models.authentication import AuthAccount, AuthSession, AuthEmailToken
from app.models.identity import User
from app.services.authentication import (check_password, consume_email_token, ensure_mail_config,
                                         hasher, hash_password, issue_email_token, throttle)

router = APIRouter(prefix='/api/auth', tags=['authentication'])
GENERIC_EMAIL = 'If the account is eligible, an email will arrive shortly. Check your spam folder too.'


class EmailBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(min_length=3, max_length=254)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        try:
            return validate_email(value.strip(), check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            raise ValueError('Enter a valid email address.') from None


class LoginBody(EmailBody):
    password: str = Field(min_length=1, max_length=128)


class RegisterBody(EmailBody):
    password: str = Field(min_length=15, max_length=128)


class TokenBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str = Field(min_length=32, max_length=128, pattern=r'^[A-Za-z0-9_-]+$')


class ResetBody(TokenBody):
    password: str = Field(min_length=15, max_length=128)


class ChangeBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    current_password: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=15, max_length=128)


def limit(db, request, scope, email=None):
    ip = request.client.host if request.client else 'unknown'
    throttle(db, scope + ':ip', ip, 20 if scope == 'login' else 10, 900)
    if email:
        throttle(db, scope + ':email', email, 8 if scope == 'login' else 3, 900)


def session_data(account, session, db):
    user = db.get(User, account.user_id) if account.user_id else None
    return {'authenticated': True, 'csrf_token': session.csrf_token,
            'user': {'id': account.id, 'email': account.email, 'name': user.name if user else '',
                     'email_verified': bool(account.verified_at), 'onboarded': bool(account.user_id)}}


def new_session(db, request, response, account):
    now = utcnow()
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    old = request.cookies.get(COOKIE_NAME)
    if old:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == digest(old)))
    raw = secrets.token_urlsafe(32)
    row = AuthSession(token_hash=digest(raw), account_id=account.id,
                      csrf_token=secrets.token_urlsafe(32), expires_at=now + timedelta(days=7))
    db.add(row)
    db.commit()
    response.set_cookie(COOKIE_NAME, raw, max_age=7 * 86400, **cookie_options())
    response.headers['Cache-Control'] = 'no-store'
    return session_data(account, row, db)


@router.get('/session')
def session_status(request: Request, response: Response, db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    session = find_session(request, db)
    if session:
        try:
            account = get_auth_account(request, db)
            return session_data(account, session, db)
        except HTTPException:
            pass
    clear_session_cookie(response)
    return {'authenticated': False, 'user': None, 'csrf_token': None}


@router.post('/register', status_code=202, dependencies=[Depends(require_browser_request)])
def register(body: RegisterBody, request: Request, db: Session = Depends(get_db)):
    limit(db, request, 'register', body.email)
    ensure_mail_config()
    encoded = hash_password(body.password)
    if db.query(AuthAccount).filter_by(email=body.email).first():
        return {'message': GENERIC_EMAIL}
    account = AuthAccount(id=str(uuid.uuid4()), email=body.email, password_hash=encoded, created_at=utcnow())
    try:
        db.add(account)
        db.flush()
        issue_email_token(db, account, 'verify')
        db.commit()
    except IntegrityError:
        db.rollback()
    return {'message': GENERIC_EMAIL}


@router.post('/login', dependencies=[Depends(require_browser_request)])
def login(body: LoginBody, request: Request, response: Response, db: Session = Depends(get_db)):
    limit(db, request, 'login', body.email)
    account = db.query(AuthAccount).filter_by(email=body.email).with_for_update().first()
    valid = check_password(account.password_hash if account else None, body.password)
    if not account or not valid or account.disabled:
        raise HTTPException(401, 'Email or password is incorrect.')
    if not account.verified_at:
        raise HTTPException(403, 'Verify your email first. You can request a new verification link below.')
    user = db.get(User, account.user_id) if account.user_id else None
    if user and user.status != 'active':
        raise HTTPException(403, 'This account is suspended.')
    if hasher.check_needs_rehash(account.password_hash):
        account.password_hash = hash_password(body.password)
    return new_session(db, request, response, account)


@router.post('/logout', dependencies=[Depends(require_browser_request)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session = find_session(request, db)
    if session:
        if not hmac.compare_digest(session.csrf_token, request.headers.get('x-csrf-token', '')):
            raise HTTPException(403, 'Your security token is invalid. Reload the page and try again.')
        db.delete(session)
        db.commit()
    clear_session_cookie(response)
    return {'message': 'Signed out.'}


@router.post('/resend-verification', dependencies=[Depends(require_browser_request)])
def resend(body: EmailBody, request: Request, db: Session = Depends(get_db)):
    limit(db, request, 'verify-email', body.email)
    ensure_mail_config()
    account = db.query(AuthAccount).filter_by(email=body.email).with_for_update().first()
    if account and not account.verified_at and not account.disabled:
        issue_email_token(db, account, 'verify')
        db.commit()
    return {'message': GENERIC_EMAIL}


@router.post('/verify-email', dependencies=[Depends(require_browser_request)])
def verify_email(body: TokenBody, request: Request, db: Session = Depends(get_db)):
    limit(db, request, 'consume-verify')
    token = consume_email_token(db, body.token, 'verify')
    account = db.query(AuthAccount).filter_by(id=token.account_id).with_for_update().first()
    if not account or account.disabled:
        raise HTTPException(400, 'This link is invalid or has expired.')
    account.verified_at = utcnow()
    db.delete(token)
    db.commit()
    return {'message': 'Email verified. You can now sign in.'}


@router.post('/forgot-password', dependencies=[Depends(require_browser_request)])
def forgot(body: EmailBody, request: Request, db: Session = Depends(get_db)):
    limit(db, request, 'reset-email', body.email)
    ensure_mail_config()
    account = db.query(AuthAccount).filter_by(email=body.email).with_for_update().first()
    if account and account.verified_at and not account.disabled:
        issue_email_token(db, account, 'reset')
        db.commit()
    return {'message': GENERIC_EMAIL}


@router.post('/reset-password', dependencies=[Depends(require_browser_request)])
def reset(body: ResetBody, request: Request, response: Response, db: Session = Depends(get_db)):
    limit(db, request, 'consume-reset')
    token = consume_email_token(db, body.token, 'reset')
    account = db.query(AuthAccount).filter_by(id=token.account_id).with_for_update().first()
    if not account or account.disabled:
        raise HTTPException(400, 'This link is invalid or has expired.')
    account.password_hash = hash_password(body.password)
    db.execute(delete(AuthSession).where(AuthSession.account_id == account.id))
    db.execute(delete(AuthEmailToken).where(AuthEmailToken.account_id == account.id))
    db.commit()
    clear_session_cookie(response)
    return {'message': 'Password updated. Sign in with your new password.'}


@router.post('/change-password')
def change_password(body: ChangeBody, request: Request, response: Response,
                    account: AuthAccount = Depends(get_auth_account), db: Session = Depends(get_db)):
    limit(db, request, 'change-password', account.id)
    account = db.query(AuthAccount).filter_by(id=account.id).with_for_update().populate_existing().one()
    get_auth_account(request, db)  # Recheck after the rate-limit transaction committed.
    if not check_password(account.password_hash, body.current_password):
        raise HTTPException(400, 'Your current password is incorrect.')
    account.password_hash = hash_password(body.password)
    db.execute(delete(AuthSession).where(AuthSession.account_id == account.id))
    db.execute(delete(AuthEmailToken).where(AuthEmailToken.account_id == account.id))
    return new_session(db, request, response, account)
