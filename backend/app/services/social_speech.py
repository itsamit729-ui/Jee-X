"""Durable optional TTS; bounded retries and explicit safe diagnostics."""
import hashlib
import logging
import os
import re
from datetime import datetime, timedelta
from sqlalchemy import func
from app.database import SessionLocal
from app.models.social_job import SocialSpeech
from app.services import social_budget as budget
from social import narration, speech_audio, worker

log = logging.getLogger('uvicorn.error')
FAILURE_BACKOFF = timedelta(minutes=30)


def fetch(text):
    if os.getenv('SOCIAL_TTS_ENABLED', 'true').strip().lower() != 'true' or not os.getenv('GROQ_API_KEY'):
        log.info('JeeEdge TTS skipped: disabled or missing Groq key.')
        return None
    if not text or len(text) > 200:
        log.warning('JeeEdge TTS skipped: text length outside 1..200 characters.')
        return None
    identity = hashlib.sha256((narration.MODEL+'|'+narration.VOICE+'|'+text).encode()).hexdigest()
    stage = 'cache_lookup'
    try:
        # Seconds match the precision of the existing MySQL datetime column.
        attempted_at = datetime.utcnow().replace(microsecond=0)
        with SessionLocal() as db:
            budget.locked(db)
            db.query(SocialSpeech).filter(SocialSpeech.created_at < attempted_at-timedelta(days=7)).delete()
            saved = db.get(SocialSpeech, identity)
            if saved and saved.audio:
                db.commit()
                log.info('JeeEdge TTS cache=hit clip=%s', identity[:12])
                return saved.audio
            if saved and attempted_at-saved.created_at < FAILURE_BACKOFF:
                retry_at = saved.created_at+FAILURE_BACKOFF
                db.commit()
                log.info('JeeEdge TTS cache=retry_backoff clip=%s retry_after=%sZ', identity[:12], retry_at.isoformat())
                return None
            size = db.query(func.coalesce(func.sum(func.length(SocialSpeech.audio)), 0)).scalar()
            if size + narration.MAX_BYTES > 32*1024*1024:
                db.commit()
                log.warning('JeeEdge TTS skipped: audio cache storage budget reached.')
                return None
            # Claim while holding the existing cross-process database mutex.
            # Old failed records automatically become eligible after 30 minutes;
            # no schema migration, key rotation, or same-call retry loop.
            if saved:
                saved.created_at = attempted_at
            else:
                db.add(SocialSpeech(id=identity, created_at=attempted_at))
            db.commit()
        stage = 'provider_request'
        with budget.tracked():
            data = worker.request(narration.URL, method='POST',
                body={'model': narration.MODEL, 'voice': narration.VOICE, 'input': text, 'response_format': 'wav'},
                headers={'Authorization': 'Bearer '+os.environ['GROQ_API_KEY']},
                binary=True, timeout=15, max_bytes=narration.MAX_BYTES)
        stage = 'audio_validation'
        data, metrics = speech_audio.normalize(data)
        log.info('JeeEdge TTS validated clip=%s metrics=%s', identity[:12], metrics)
        stage = 'cache_write'
        with SessionLocal() as db:
            # A very late response cannot overwrite another attempt's cache claim.
            db.query(SocialSpeech).filter_by(id=identity, created_at=attempted_at, audio=None).update(
                {'audio':data}, synchronize_session=False)
            db.commit()
        log.info('JeeEdge TTS generated clip=%s bytes=%d seconds=%.2f', identity[:12], len(data), metrics['seconds'])
        return data
    except Exception as error:
        # Use only controlled codes/numeric metadata. No keys, URLs, response bodies,
        # prompts, DB connection strings or arbitrary exception text in logs.
        reason = type(error).__name__
        metrics = {}
        if isinstance(error, speech_audio.AudioValidationError):
            reason, metrics = error.code, error.metrics
        elif isinstance(error, worker.ServiceError):
            message = str(error)
            match = re.search(r'HTTP (\d{3})', message)
            reason = ('provider_http_' + match.group(1) if match else
                      'local_quota' if 'budget reached' in message else
                      'provider_cooldown' if 'cooldown active' in message else
                      'response_too_large' if 'size limit' in message else
                      'network_or_timeout' if 'Network request failed' in message else 'service_error')
        log.warning('JeeEdge TTS fallback clip=%s stage=%s reason=%s metrics=%s; music continues.',
                    identity[:12], stage, reason, metrics)
        return None
