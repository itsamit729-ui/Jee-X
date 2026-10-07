"""Durable optional TTS; failures must not block publication."""
import hashlib
import logging
import os
from datetime import datetime, timedelta
from sqlalchemy import func
from app.database import SessionLocal
from app.models.social_job import SocialSpeech
from app.services import social_budget as budget
from social import narration, worker

log = logging.getLogger(__name__)


def fetch(text):
    if os.getenv('SOCIAL_TTS_ENABLED', 'true').lower() != 'true' or not os.getenv('GROQ_API_KEY'):
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
                return saved.audio
            size = db.query(func.coalesce(func.sum(func.length(SocialSpeech.audio)), 0)).scalar()
            if size + narration.MAX_BYTES > 32*1024*1024:
                db.commit()
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
        return data
    except Exception as error:
        # Log only error type; never credentials, provider bodies or connection strings.
        log.info('Optional Reel narration unavailable (%s); using music fallback.', type(error).__name__)
        return None
