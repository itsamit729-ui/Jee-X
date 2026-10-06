"""Durable local budgets. Provider-wide usage outside this worker is not observable."""
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.social_job import SocialUsage, SocialQuotaLock, SocialCache
from social import worker

# Headroom below published limits; no paid fallback and no automatic limit increases.
LIMITS = {
    'buffer': [(900, 95, 0), (86400, 95, 0), (30*86400, 2850, 0)],
    'groq': [(60, 28, 7600), (86400, 950, 190000)],
    'render': [(86400, 1800, 0)],
    'egress': [(86400, 64*1024*1024, 0), (30*86400, 1024*1024*1024, 0)],
}


def locked(db):
    if db.get(SocialQuotaLock, 1) is None:
        db.add(SocialQuotaLock(id=1))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    db.query(SocialQuotaLock).filter_by(id=1).with_for_update().one()


def totals(db, service, seconds, now):
    return db.query(func.coalesce(func.sum(SocialUsage.units), 0),
                    func.coalesce(func.sum(SocialUsage.tokens), 0)).filter(
        SocialUsage.service == service, SocialUsage.created_at > now-timedelta(seconds=seconds)).one()


def check(db, service, units=0, tokens=0):
    now = datetime.utcnow()
    cooldown = db.get(SocialCache, 'cooldown:'+service)
    if cooldown and cooldown.expires_at > now:
        raise worker.ServiceError(service + ' provider cooldown active; holding work without paid fallback.')
    for seconds, max_units, max_tokens in LIMITS[service]:
        used, consumed = totals(db, service, seconds, now)
        if used+units > max_units or (max_tokens and consumed+tokens > max_tokens):
            raise worker.ServiceError(service + ' local free-tier budget reached; wait for the rolling window to reset.')


def reserve(service, units=1, tokens=0):
    with SessionLocal() as db:
        locked(db)
        check(db, service, units, tokens)
        identity = uuid.uuid4().hex
        db.add(SocialUsage(id=identity, service=service, created_at=datetime.utcnow(), units=units, tokens=tokens))
        db.commit()
        return identity


def settle(identity, units=None, tokens=None):
    with SessionLocal() as db:
        row = db.get(SocialUsage, identity)
        if row:
            if units is not None:
                row.units = max(1, units)
            if tokens is not None:
                row.tokens = max(0, tokens)
            db.commit()


def cached(name):
    with SessionLocal() as db:
        row = db.get(SocialCache, name)
        return json.loads(row.value) if row and row.expires_at > datetime.utcnow() else None


def cache(name, value, seconds):
    with SessionLocal() as db:
        locked(db)
        db.merge(SocialCache(name=name, value=json.dumps(value), expires_at=datetime.utcnow()+timedelta(seconds=seconds)))
        db.commit()


def before(url, body):
    if url == 'https://api.buffer.com':
        return reserve('buffer')
    if url.startswith('https://api.groq.com/'):
        # UTF-8 bytes conservatively bound text tokenization; reserve output too.
        tokens = len(json.dumps(body, ensure_ascii=False).encode()) + int(body.get('max_completion_tokens', 0)) + 100
        return reserve('groq', tokens=tokens)
    return None


def after(identity, result):
    if identity and isinstance(result, dict) and 'usage' in result:
        actual = result['usage'].get('total_tokens')
        if isinstance(actual, int) and actual >= 0:
            settle(identity, tokens=actual)


def limited(url, seconds):
    service = 'buffer' if url == 'https://api.buffer.com' else 'groq'
    cache('cooldown:'+service, True, max(60, min(seconds, 86400)))


@contextmanager
def tracked():
    token = worker.REQUEST_HOOKS.set((before, after, limited))
    try:
        yield
    finally:
        worker.REQUEST_HOOKS.reset(token)


def admission():
    with SessionLocal() as db:
        for service, units in [('buffer', 3), ('render', 180), ('egress', 8*1024*1024)]:
            check(db, service, units=units)


def record_egress(size):
    # Never break already-published URLs when the admission budget is exhausted.
    with SessionLocal() as db:
        db.add(SocialUsage(id=uuid.uuid4().hex, service='egress', created_at=datetime.utcnow(), units=size, tokens=0))
        db.commit()


def report():
    with SessionLocal() as db:
        now = datetime.utcnow()
        result = {}
        for service, windows in LIMITS.items():
            result[service] = []
            for seconds, units, tokens in windows:
                used, consumed = totals(db, service, seconds, now)
                result[service].append({'window_seconds': seconds, 'used': used, 'budget': units,
                                        'tokens_used': consumed, 'token_budget': tokens or None})
        return {'scope': 'This automation only; prior and external account usage is not included.', 'services': result}
