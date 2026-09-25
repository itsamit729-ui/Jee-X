import os
import secrets
from threading import BoundedSemaphore
from datetime import timedelta
from html import escape
from urllib.parse import urlsplit
import requests
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException
from sqlalchemy import update, delete
from sqlalchemy.exc import IntegrityError
from app.auth import digest, utcnow
from app.models.authentication import AuthAccount, AuthEmailToken, AuthRateLimit

# OWASP Argon2id minimum, with bounded memory on small instances.
hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
_hash_slots = BoundedSemaphore(2)

def hash_password(password):
    with _hash_slots:
        return hasher.hash(password)


DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def check_password(encoded, password):
    try:
        with _hash_slots:
            return hasher.verify(encoded or DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        return False


def throttle(db, scope, value, limit, seconds):
    """Atomic shared counters, committed even if the subsequent action fails."""
    now = utcnow()
    bucket = int(now.timestamp()) // seconds
    key = digest(f'{scope}:{value}:{bucket}')
    try:
        with db.begin_nested():
            db.add(AuthRateLimit(key=key, hits=0, expires_at=now + timedelta(seconds=seconds)))
            db.flush()
    except IntegrityError:
        pass
    changed = db.execute(update(AuthRateLimit).where(AuthRateLimit.key == key, AuthRateLimit.hits < limit).values(hits=AuthRateLimit.hits + 1)).rowcount
    db.execute(delete(AuthRateLimit).where(AuthRateLimit.expires_at < now - timedelta(days=1)))
    db.commit()
    if not changed:
        raise HTTPException(429, 'Too many attempts. Please try again later.', headers={'Retry-After': str(seconds)})


def ensure_mail_config():
    base = os.getenv('PUBLIC_APP_URL', '').rstrip('/')
    parsed = urlsplit(base)
    valid_url = parsed.scheme == 'https' or (parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1'})
    provider = os.getenv('AUTH_EMAIL_PROVIDER', 'brevo').lower()
    key = os.getenv('BREVO_API_KEY' if provider == 'brevo' else 'RESEND_API_KEY')
    if provider not in {'brevo', 'resend'} or not key or not os.getenv('AUTH_EMAIL_FROM') or not valid_url or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
        raise HTTPException(503, 'Account email is not configured yet. Please try again later.')
    return base


def send_account_email(email, purpose, raw_token):
    base = ensure_mail_config()
    path = 'verify-email' if purpose == 'verify' else 'reset-password'
    title = 'Verify your Jee Edge email' if purpose == 'verify' else 'Reset your Jee Edge password'
    link = f'{base}/{path}#token={raw_token}'
    html = f'<h1>{title}</h1><p><a href="{escape(link, quote=True)}">Continue to Jee Edge</a></p><p>This link expires in 30 minutes and works once. If you did not request it, ignore this email.</p>'
    try:
        if os.getenv('AUTH_EMAIL_PROVIDER', 'brevo').lower() == 'brevo':
            result = requests.post('https://api.brevo.com/v3/smtp/email', timeout=10,
                headers={'api-key': os.environ['BREVO_API_KEY']},
                json={'sender': {'email': os.environ['AUTH_EMAIL_FROM'], 'name': 'Jee Edge'},
                      'to': [{'email': email}], 'subject': title, 'htmlContent': html})
        else:
            result = requests.post('https://api.resend.com/emails', timeout=10,
                headers={'Authorization': f'Bearer {os.environ["RESEND_API_KEY"]}'},
                json={'from': os.environ['AUTH_EMAIL_FROM'], 'to': [email], 'subject': title, 'html': html})
        result.raise_for_status()
    except requests.RequestException:
        raise HTTPException(503, 'We could not send the email. Please try again later.') from None


def issue_email_token(db, account, purpose):
    raw = secrets.token_urlsafe(32)
    db.execute(delete(AuthEmailToken).where(AuthEmailToken.account_id == account.id, AuthEmailToken.purpose == purpose))
    db.add(AuthEmailToken(token_hash=digest(raw), account_id=account.id, purpose=purpose, expires_at=utcnow() + timedelta(minutes=30)))
    db.flush()
    send_account_email(account.email, purpose, raw)


def consume_email_token(db, raw, purpose):
    # Consistent lock order with resend/reset: account, then email token.
    candidate = db.query(AuthEmailToken.account_id).filter_by(token_hash=digest(raw), purpose=purpose).first()
    if candidate:
        db.query(AuthAccount).filter_by(id=candidate.account_id).with_for_update().populate_existing().first()
    token = db.query(AuthEmailToken).filter_by(token_hash=digest(raw), purpose=purpose).with_for_update().populate_existing().first()
    if not token or token.expires_at <= utcnow():
        raise HTTPException(400, 'This link is invalid or has expired. Request a new one.')
    return token
