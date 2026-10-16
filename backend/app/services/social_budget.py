"""Durable local budgets. Provider-wide usage outside this worker is not observable."""
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, case
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.social_job import SocialUsage, SocialQuotaLock, SocialCache
from social import worker

# Headroom below Buffer Free's documented 100/250/3000 rolling limits:
# https://developers.buffer.com/guides/api-limits.html (verified 2026-10-15).
# No paid fallback; the monthly cap still bounds sustained usage.
LIMITS = {
    'buffer': [(900, 95, 0), (86400, 235, 0), (30*86400, 2850, 0)],
    'groq': [(60, 28, 7600), (86400, 950, 190000)],
    'groq_tts': [(60, 8, 1000), (86400, 90, 3200)],
    'render': [(86400, 1800, 0)],
    'egress': [(86400, 64*1024*1024, 0), (30*86400, 1024*1024*1024, 0)],
}


class BudgetExceeded(worker.ServiceError):
    def __init__(self, message, retry_at=None, details=None):
        super().__init__(message)
        self.retry_at = retry_at
        self.details = details


def stamp(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def release_time(db, service, seconds, used, consumed, units, tokens, max_units, max_tokens, now):
    """When enough recorded usage expires for this request, without resetting it."""
    rows = db.query(SocialUsage.created_at, SocialUsage.units, SocialUsage.tokens).filter(
        SocialUsage.service == service, SocialUsage.created_at > now-timedelta(seconds=seconds)
    ).order_by(SocialUsage.created_at).all()
    for created, spent, spent_tokens in rows:
        used -= spent
        consumed -= spent_tokens
        if used+units <= max_units and (not max_tokens or consumed+tokens <= max_tokens):
            return created+timedelta(seconds=seconds+1)
    return None


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
        raise BudgetExceeded(service + ' provider cooldown active; holding work without paid fallback.',
                             stamp(cooldown.expires_at), {'source':'provider_cooldown','service':service})
    blocked=[]
    for seconds, max_units, max_tokens in LIMITS[service]:
        used, consumed = totals(db, service, seconds, now)
        if used+units > max_units or (max_tokens and consumed+tokens > max_tokens):
            retry=release_time(db,service,seconds,used,consumed,units,tokens,max_units,max_tokens,now)
            blocked.append({'window_seconds':seconds,'used':int(used),'budget':max_units,
                            'tokens_used':int(consumed),'token_budget':max_tokens or None,'retry_at':stamp(retry)})
    if blocked:
        # All blocked windows must have headroom, not just the first one.
        retry=max(w['retry_at'] for w in blocked) if all(w['retry_at'] for w in blocked) else None
        labels={900:'15-minute',86400:'24-hour',30*86400:'30-day'}
        windows=', '.join(f"{labels.get(w['window_seconds'],str(w['window_seconds'])+'s')} {w['used']}/{w['budget']}" for w in blocked)
        raise BudgetExceeded(service+f' local free-tier budget reached ({windows}; {units} units needed).',retry,
                             {'source':'local_ledger','service':service,'units_requested':units,'windows':blocked})


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
    if url == 'https://api.groq.com/openai/v1/audio/speech':
        return reserve('groq_tts', tokens=len(body.get('input', '').encode('utf-8')) + 32)
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
    service = ('buffer' if url == 'https://api.buffer.com' else
               'groq_tts' if url.endswith('/audio/speech') else 'groq')
    cache('cooldown:'+service, True, max(60, min(seconds, 86400)))


@contextmanager
def tracked():
    token = worker.REQUEST_HOOKS.set((before, after, limited))
    try:
        yield
    finally:
        worker.REQUEST_HOOKS.reset(token)


def admission(db=None):
    if db is None:
        with SessionLocal() as session:
            return admission(session)
    for service, units in [('buffer', 3), ('render', 180), ('egress', 8*1024*1024)]:
        check(db, service, units=units)


def record_egress(size):
    # Never break already-published URLs when the admission budget is exhausted.
    with SessionLocal() as db:
        db.add(SocialUsage(id=uuid.uuid4().hex, service='egress', created_at=datetime.utcnow(), units=size, tokens=0))
        db.commit()


def report():
    with SessionLocal() as db:
        now=datetime.utcnow()
        windows=sorted({seconds for limits in LIMITS.values() for seconds,_,_ in limits})
        columns=[]
        for seconds in windows:
            current=SocialUsage.created_at>now-timedelta(seconds=seconds)
            columns.extend([func.sum(case((current,SocialUsage.units),else_=0)),func.sum(case((current,SocialUsage.tokens),else_=0))])
        rows=db.query(SocialUsage.service,*columns).filter(SocialUsage.created_at>now-timedelta(seconds=max(windows))).group_by(SocialUsage.service).all()
        usage={row[0]:{seconds:(row[1+i*2] or 0,row[2+i*2] or 0) for i,seconds in enumerate(windows)} for row in rows}
        result={}
        for service,limits in LIMITS.items():
            result[service]=[]
            for seconds,units,tokens in limits:
                used,consumed=usage.get(service,{}).get(seconds,(0,0))
                result[service].append({'window_seconds':seconds,'used':used,'budget':units,'tokens_used':consumed,'token_budget':tokens or None})
        return {'scope':'This automation only; prior and external account usage is not included.','services':result}
