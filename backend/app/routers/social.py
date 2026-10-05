"""Authenticated, quick-return cron trigger; state survives Render restarts."""
import hmac
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.social_job import SocialJob, SocialMedia
from social import worker

router = APIRouter(prefix='/api/social', tags=['social'])
# This is the backend origin, not a caller-controlled Host header or frontend URL.
MEDIA_ORIGIN = 'https://jee-edge.onrender.com'


def authorize(authorization: str = Header(default='')):
    secret = os.getenv('SOCIAL_TRIGGER_SECRET', '')
    if len(secret) < 32:
        raise HTTPException(503, 'SOCIAL_TRIGGER_SECRET must contain at least 32 characters')
    if not hmac.compare_digest(authorization.encode(), ('Bearer ' + secret).encode()):
        raise HTTPException(401, 'Invalid trigger credentials')


def today():
    return datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()


def status_data(job):
    return {'day': job.day, 'state': job.state, 'attempts': job.attempts,
            'post_id': job.post_id, 'error': job.error, 'updated_at': job.updated_at.isoformat()}


@router.get('/status', dependencies=[Depends(authorize)])
def status():
    with SessionLocal() as db:
        rows = db.query(SocialJob).order_by(SocialJob.day.desc()).limit(7).all()
        return {'jobs': [status_data(row) for row in rows]}


@router.get('/media/{media_id}.png')
def media(media_id: str):
    if not re.fullmatch('[0-9a-f]{32}', media_id):
        raise HTTPException(404, 'Image not found')
    with SessionLocal() as db:
        row = db.get(SocialMedia, media_id)
        if row is None:
            raise HTTPException(404, 'Image not found')
        return Response(row.image, media_type='image/png', headers={'Cache-Control': 'public, max-age=86400'})


@router.post('/trigger', status_code=202, dependencies=[Depends(authorize)])
def trigger(tasks: BackgroundTasks):
    if os.getenv('SOCIAL_PAUSED', '').lower() == 'true':
        raise HTTPException(503, 'Social automation is paused')
    if any(not os.getenv(key) for key in ('GROQ_API_KEY', 'BUFFER_API_KEY')):
        raise HTTPException(503, 'GROQ_API_KEY and BUFFER_API_KEY must be configured')
    day, owner, now = today(), uuid.uuid4().hex, datetime.utcnow()
    with SessionLocal() as db:
        job = db.get(SocialJob, day)
        if job is None:
            job = SocialJob(day=day, owner=owner, state='running', updated_at=now, attempts=1)
            db.add(job)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                return status_data(db.get(SocialJob, day))
        else:
            # Reclaim only pre-submission failures or expired generation leases.
            eligible = job.state == 'failed' or (job.state == 'running' and job.updated_at < now - timedelta(minutes=15))
            if not eligible or job.attempts >= 3:
                return status_data(job)
            count = db.query(SocialJob).filter_by(day=day, owner=job.owner, state=job.state,
                                                 updated_at=job.updated_at).update({
                'owner': owner, 'state': 'running', 'updated_at': now,
                'attempts': job.attempts + 1, 'error': None}, synchronize_session=False)
            db.commit()
            if not count:
                db.expire_all()
                return status_data(db.get(SocialJob, day))
        db.expire_all()
        result = status_data(db.get(SocialJob, day))
    tasks.add_task(run_job, day, owner)
    return result


def transition(day, owner, before, after, **values):
    with SessionLocal() as db:
        count = db.query(SocialJob).filter_by(day=day, owner=owner, state=before).update(
            {'state': after, 'updated_at': datetime.utcnow(), **values}, synchronize_session=False)
        db.commit()
        return count == 1


def safe_error(error):
    # Only controlled ServiceError messages are suitable for the status endpoint.
    message = str(error) if isinstance(error, worker.ServiceError) else 'Internal worker error; check service logs.'
    for value in os.environ.values():
        if len(value) >= 12:
            message = message.replace(value, '[redacted]')
    return re.sub(r'https?://\S+', '[URL]', message)[:500]


def run_job(day, owner):
    submitting = False
    try:
        now = datetime.now(timezone.utc)
        org, channel = worker.find_channel()
        recent = worker.posts(org, channel['id'], (now - timedelta(days=3)).isoformat())
        marker = f'JeeEdge daily {day}'
        found = next((post for post in recent if marker in (post.get('text') or '')), None)
        if found:
            transition(day, owner, 'running', 'existing', post_id=found['id'])
            return
        if sum(p['status'] in ('scheduled', 'sending') for p in recent) >= 9:
            raise worker.ServiceError('Buffer queue near capacity; waiting.')
        content = worker.problem(day)
        copy = worker.ai_copy(content, [])
        with TemporaryDirectory(prefix='jeeedge-social-') as directory:
            paths = worker.render(content, copy, directory)
            with SessionLocal() as db:
                # Lock and verify ownership before replacing this day's media.
                job = db.query(SocialJob).filter_by(day=day).with_for_update().one()
                if job.owner != owner or job.state != 'running':
                    return
                db.query(SocialMedia).filter_by(day=day).delete()
                urls = []
                for path in paths:
                    media_id = uuid.uuid4().hex
                    db.add(SocialMedia(id=media_id, day=day, image=path.read_bytes()))
                    urls.append(f'{MEDIA_ORIGIN}/api/social/media/{media_id}.png')
                db.commit()
        if today() != day:
            raise worker.ServiceError('Generation crossed midnight; wait for the next daily trigger.')
        # Durable fence MUST commit before the non-idempotent Buffer mutation.
        if not transition(day, owner, 'running', 'submitting'):
            return
        submitting = True
        caption = copy['caption'] + '\n\nOriginal practice question. More practice via the link in our bio.\n#JEE #JEEPreparation #JeeEdge\n' + marker
        payload = {'text': caption, 'channelId': channel['id'], 'schedulingType': 'automatic',
                   'mode': 'customScheduled', 'dueAt': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                   'metadata': {'instagram': {'type': 'post', 'shouldShareToFeed': True}},
                   'assets': [{'image': {'url': url}} for url in urls]}
        result = worker.buffer('mutation($input:CreatePostInput!) { createPost(input:$input) '
                               '{ __typename ... on PostActionSuccess { post { id status } } '
                               '... on MutationError { message } } }', {'input': payload})['createPost']
        if not result.get('post'):
            # Even an unfamiliar rejection is held for review, never blindly retried.
            raise worker.ServiceError('Buffer did not confirm a post. Check Buffer before retrying. ' + str(result.get('message', 'Unknown response.')))
        transition(day, owner, 'submitting', 'scheduled', post_id=result['post']['id'], error=None)
        # Retain images for 60 days; never remove media attached to ambiguous jobs.
        with SessionLocal() as db:
            old = db.query(SocialJob.day).filter(SocialJob.day < (now - timedelta(days=60)).date().isoformat(),
                                                 SocialJob.state.in_(['scheduled', 'existing', 'failed']))
            db.query(SocialMedia).filter(SocialMedia.day.in_(old)).delete(synchronize_session=False)
            db.commit()
    except Exception as error:
        message = safe_error(error)
        transition(day, owner, 'submitting' if submitting else 'running',
                   'needs_review' if submitting else 'failed', error=message)
        print(f'JeeEdge social {day}: {message}', flush=True)
