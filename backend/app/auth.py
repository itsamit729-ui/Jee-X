"""Cookie sessions and CSRF validation for first-party authentication."""
import hashlib
import hmac
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.authentication import AuthAccount, AuthSession
from app.models.identity import User

COOKIE_NAME = 'jee_session'


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def trusted_origins():
    raw = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
    raw.append(os.getenv('PUBLIC_APP_URL', 'http://localhost:5173'))
    return {f'{p.scheme}://{p.netloc}' for v in raw if (p := urlsplit(v.strip())).scheme in {'http', 'https'} and p.netloc}


def require_browser_request(request: Request):
    if request.headers.get('origin', '').rstrip('/') not in trusted_origins() or request.headers.get('x-jee-request') != '1':
        raise HTTPException(403, 'This request did not come from an allowed website.')


def cookie_options():
    secure = os.getenv('AUTH_COOKIE_SECURE', 'true').lower() == 'true'
    same_site = os.getenv('AUTH_COOKIE_SAMESITE', 'lax').lower()
    if same_site not in {'lax', 'strict', 'none'} or (same_site == 'none' and not secure):
        raise RuntimeError('Invalid authentication cookie configuration.')
    return dict(httponly=True, secure=secure, samesite=same_site, path='/')


def clear_session_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME, **cookie_options())


def find_session(request: Request, db: Session):
    raw = request.cookies.get(COOKIE_NAME, '')
    if not raw or len(raw) > 128:
        return None
    session = db.get(AuthSession, digest(raw))
    if not session or session.expires_at <= utcnow():
        return None
    return session


def get_auth_account(request: Request, db: Session = Depends(get_db)) -> AuthAccount:
    session = find_session(request, db)
    if not session:
        raise HTTPException(401, 'Your session has expired. Please sign in again.')
    account = db.get(AuthAccount, session.account_id)
    if not account or account.disabled:
        raise HTTPException(401, 'Please sign in again.')
    if not account.verified_at:
        raise HTTPException(403, 'Verify your email before continuing.')
    user = db.get(User, account.user_id) if account.user_id else None
    if user and user.status != 'active':
        raise HTTPException(403, 'This account is suspended.')
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        require_browser_request(request)
        if not hmac.compare_digest(session.csrf_token, request.headers.get('x-csrf-token', '')):
            raise HTTPException(403, 'Your security token is invalid. Reload the page and try again.')
    return account
