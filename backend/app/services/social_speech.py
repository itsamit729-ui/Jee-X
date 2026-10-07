"""Durable optional TTS; failures must not block publication."""
import hashlib
import logging
import os
import re
from datetime import datetime, timedelta
from sqlalchemy import func
from app.database import SessionLocal
from app.models.social_job import SocialSpeech
from app.services import social_budget as budget
from social import narration, worker

log = logging.getLogger('uvicorn.error')


def fetch(text):
    if os.getenv('SOCIAL_TTS_ENABLED', 'true').lower() != 'true' or not os.getenv('GROQ_API_KEY'):
        log.info('JeeEdge TTS skipped: disabled or missing Groq key.')
        return None
    if not text or len(text) > 200:
        return None
    identity = hashlib.sha256((narration.MODEL+'|'+narration.VOICE+'|'+text).encode()).hexdigest()
    try:
        with SessionLocal() as db:
            budget.locked(db)
            db.query(SocialSpeech).filter(SocialSpeech.created_at < datetime.utcnow()-timedelta(days=7)).delete()
            saved = db.get(SocialSpeech, identity)
            if saved:
                db.commit()
                log.info('JeeEdge TTS cache=%s clip=%s', 'hit' if saved.audio else 'previous_failure', identity[:12])
                return saved.audio
            size = db.query(func.coalesce(func.sum(func.length(SocialSpeech.audio)), 0)).scalar()
            if size + narration.MAX_BYTES > 32*1024*1024:
                db.commit()
                log.warning('JeeEdge TTS skipped: audio cache storage budget reached.')
                return None
            # Durable attempt marker: timeout/crash/invalid audio is not regenerated on retry.
            db.add(SocialSpeech(id=identity, created_at=datetime.utcnow()))
            db.commit()
        with budget.tracked():
            data = worker.request(narration.URL, method='POST',
                body={'model': narration.MODEL, 'voice': narration.VOICE, 'input': text, 'response_format': 'wav'},
                headers={'Authorization': 'Bearer '+os.environ['GROQ_API_KEY']},
                binary=True, timeout=15, max_bytes=narration.MAX_BYTES)
        narration.duration(data)
        with SessionLocal() as db:
            row = db.get(SocialSpeech, identity)
            if row:
                row.audio = data
                db.commit()
        log.info('JeeEdge TTS generated clip=%s bytes=%d seconds=%.2f', identity[:12], len(data), narration.duration(data))
        return data
    except Exception as error:
        # Log only error type; never credentials, provider bodies or connection strings.
        reason = type(error).__name__
        if isinstance(error, worker.ServiceError):
            message = str(error)
            match = re.search(r'HTTP (\d{3})', message)
            reason = ('provider_http_' + match.group(1) if match else
                      'local_quota' if 'budget reached' in message else
                      'provider_cooldown' if 'cooldown active' in message else
                      'response_too_large' if 'size limit' in message else
                      'network_or_timeout' if 'Network request failed' in message else 'service_error')
        log.warning('JeeEdge TTS fallback clip=%s reason=%s; music continues.', identity[:12], reason)
        return None
