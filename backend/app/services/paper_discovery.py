import hashlib
import re
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError
from app.models.acquisition import AcquisitionCount

SOURCES = {'direct', 'google', 'youtube', 'instagram', 'whatsapp', 'telegram', 'teacher', 'other'}

def paper_slug(year, shift):
    readable = re.sub(r'[^a-z0-9]+', '-', shift.lower()).strip('-')[:75]
    digest = hashlib.sha256(f'{year}:{shift}'.encode()).hexdigest()[:10]
    return f'{readable}-{digest}'

def count_event(db, paper, source, event):
    source = source if source in SOURCES else 'other'
    bucket = dict(day=datetime.now(timezone(timedelta(hours=5, minutes=30))).date(),
                  paper=paper, source=source, event=event)
    query = db.query(AcquisitionCount).filter_by(**bucket)
    if query.update({AcquisitionCount.count: AcquisitionCount.count + 1}):
        return
    try:
        with db.begin_nested():
            db.add(AcquisitionCount(**bucket, count=1))
            db.flush()
    except IntegrityError:
        query.update({AcquisitionCount.count: AcquisitionCount.count + 1})
