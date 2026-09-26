"""Google OpenID Connect for first-party browser sessions."""
import os
import secrets
import uuid
from urllib.parse import urlencode, urlsplit

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import cookie_options, get_auth_account, utcnow
from app.database import get_db
from app.models.authentication import AuthAccount, GoogleIdentity
from app.models.identity import User
from app.routers.authentication import new_session
from app.services.authentication import hash_password, throttle

router = APIRouter(prefix='/api/auth/google', tags=['authentication'])
STATE_COOKIE = 'jee_google_state'


def config():
    base = os.getenv('PUBLIC_APP_URL', '').rstrip('/')
    parts = urlsplit(base)
    client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
    if not client_id or not client_secret or parts.scheme != 'https' or not parts.netloc or parts.path or parts.query or parts.fragment:
        raise HTTPException(503, 'Google sign-in is not configured.')
    return base, client_id, client_secret


def login_error(base, reason):
    return RedirectResponse(f'{base}/login?google_error={reason}', status_code=303)


@router.get('/enabled')
def enabled():
    try:
        config()
        return {'enabled': True}
    except HTTPException:
        return {'enabled': False}


def authorization_response(base, client_id, state):
    redirect_uri = f'{base}/api/auth/google/callback'
    params = {'client_id': client_id, 'redirect_uri': redirect_uri, 'response_type': 'code',
              'scope': 'openid email', 'state': state, 'prompt': 'select_account'}
    return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params)


@router.get('/start')
def start():
    base, client_id, _ = config()
    state = secrets.token_urlsafe(32)
    response = RedirectResponse(authorization_response(base, client_id, state), status_code=302)
    response.set_cookie(STATE_COOKIE, state, max_age=600, path='/api/auth/google', **{k: v for k, v in cookie_options().items() if k != 'path'})
    response.headers['Cache-Control'] = 'no-store'
    return response


@router.post('/link')
def link(account: AuthAccount = Depends(get_auth_account), db: Session = Depends(get_db)):
    base, client_id, _ = config()
    if db.query(GoogleIdentity).filter_by(account_id=account.id).first():
        raise HTTPException(409, 'A Google account is already connected.')
    state = 'link.' + secrets.token_urlsafe(32)
    from fastapi.responses import JSONResponse
    response = JSONResponse({'url': authorization_response(base, client_id, state)})
    response.set_cookie(STATE_COOKIE, state, max_age=600, path='/api/auth/google', **{k: v for k, v in cookie_options().items() if k != 'path'})
    return response


@router.get('/callback')
def callback(request: Request, code: str = '', state: str = '', db: Session = Depends(get_db)):
    base, client_id, client_secret = config()
    response = login_error(base, 'failed')
    expected = request.cookies.get(STATE_COOKIE, '')
    response.delete_cookie(STATE_COOKIE, path='/api/auth/google', secure=True, samesite='lax', httponly=True)
    if not code or not state or not expected or not secrets.compare_digest(state, expected):
        return response
    ip = request.client.host if request.client else 'unknown'
    throttle(db, 'google:ip', ip, 20, 900)
    try:
        token_response = requests.post('https://oauth2.googleapis.com/token', timeout=10,
            data={'code': code, 'client_id': client_id, 'client_secret': client_secret,
                  'redirect_uri': f'{base}/api/auth/google/callback', 'grant_type': 'authorization_code'})
        token_response.raise_for_status()
        # The code is exchanged by this confidential client; retrieve identity directly
        # from Google's TLS-protected OpenID Connect userinfo endpoint.
        user_response = requests.get('https://openidconnect.googleapis.com/v1/userinfo', timeout=10,
            headers={'Authorization': f'Bearer {token_response.json()["access_token"]}'})
        user_response.raise_for_status()
        payload = user_response.json()
    except (requests.RequestException, ValueError, KeyError):
        return response
    sub = payload.get('sub')
    email = payload.get('email', '').strip().lower()
    if not sub or not email or not payload.get('email_verified'):
        return response

    identity = db.get(GoogleIdentity, sub)
    if state.startswith('link.'):
        try:
            account = get_auth_account(request, db)
        except HTTPException:
            return response
        if identity and identity.account_id != account.id:
            return response
        if not identity:
            if db.query(GoogleIdentity).filter_by(account_id=account.id).first():
                return response
            db.add(GoogleIdentity(google_sub=sub, account_id=account.id))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                return response
    elif identity:
        account = db.get(AuthAccount, identity.account_id)
    else:
        # A matching address must never silently grant access to a password account.
        if db.query(AuthAccount).filter_by(email=email).first():
            return login_error(base, 'existing')
        account = AuthAccount(id=str(uuid.uuid4()), email=email,
                              password_hash=hash_password(secrets.token_urlsafe(48)),
                              verified_at=utcnow(), created_at=utcnow())
        db.add(account)
        db.add(GoogleIdentity(google_sub=sub, account_id=account.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return login_error(base, 'failed')
    if not account or account.disabled:
        return response
    user = db.get(User, account.user_id) if account.user_id else None
    if user and user.status != 'active':
        return response
    result = RedirectResponse(f'{base}/account/security?google_connected=1' if state.startswith('link.') else f'{base}/dashboard', status_code=303)
    new_session(db, request, result, account)
    result.delete_cookie(STATE_COOKIE, path='/api/auth/google', secure=True, samesite='lax', httponly=True)
    return result
