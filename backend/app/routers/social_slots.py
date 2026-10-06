"""Authenticated, quick-return cron trigger; state survives Render restarts."""
import io
import hashlib
import hmac
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.social_job import SocialSlot as SocialJob, SocialAsset as SocialMedia, SocialDispatch
from app.models.social_job import SocialJob as LegacyJob
from app.routers.social import media as legacy_media
from social import worker, reel
from PIL import Image

router = APIRouter(prefix='/api/social', tags=['social'])
# This is the backend origin, not a caller-controlled Host header or frontend URL.
MEDIA_ORIGIN = 'https://jee-edge.onrender.com'


def authorize(authorization: str = Header(default='')):
    secret = os.getenv('SOCIAL_TRIGGER_SECRET', '')
    if len(secret) < 32:
        raise HTTPException(503, 'SOCIAL_TRIGGER_SECRET must contain at least 32 characters')
    if not hmac.compare_digest(authorization.encode(), ('Bearer ' + secret).encode()):
        raise HTTPException(401, 'Invalid trigger credentials')


def local_now():
    return datetime.now(ZoneInfo('Asia/Kolkata'))


def today():
    return local_now().date().isoformat()


def current_slot():
    hour = local_now().hour
    if hour < 9:
        return None
    return 'morning' if hour < 14 else 'reel' if hour < 19 else 'evening'


def slot_problem(key):
    day, slot = key.split(':')
    offset = {'morning': 0, 'reel': 1, 'evening': 2}[slot]
    return worker.problem(day, variant=offset)


def status_data(job):
    return {'day': job.day[:10], 'slot': job.day.split(':')[-1], 'state': job.state, 'attempts': job.attempts,
            'post_id': job.post_id, 'error': job.error, 'updated_at': job.updated_at.isoformat()}


@router.get('/status', dependencies=[Depends(authorize)])
def status():
    with SessionLocal() as db:
        rows = db.query(SocialJob).order_by(SocialJob.day.desc()).limit(21).all()
        return {'jobs': [status_data(row) for row in rows]}


# Preserve all existing public carousel links.
router.add_api_route('/media/{media_id}.png', legacy_media, methods=['GET', 'HEAD'])


@router.api_route('/assets/{media_id}.{extension}', methods=['GET', 'HEAD'])
def media(media_id: str, extension: str, request: Request):
    if not re.fullmatch('[0-9a-f]{32}', media_id) or extension not in ('jpg', 'mp4'):
        raise HTTPException(404, 'Media not found')
    with SessionLocal() as db:
        row = db.get(SocialMedia, media_id)
        if row is None or row.mime != {'jpg': 'image/jpeg', 'mp4': 'video/mp4'}[extension]:
            raise HTTPException(404, 'Media not found')
        data, mime = row.image, row.mime
    length = len(data)
    headers = {'Cache-Control': 'public, max-age=86400', 'Accept-Ranges': 'bytes',
               'Content-Length': str(length), 'ETag': '"' + hashlib.sha256(data).hexdigest() + '"'}
    if request.method == 'HEAD':
        return Response(b'', media_type=mime, headers=headers)
    requested = request.headers.get('range')
    if requested:
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
        if not match or not any(match.groups()):
            return Response(status_code=416, headers={'Content-Range': f'bytes */{length}'})
        first, last = match.groups()
        start = int(first) if first else max(0, length-int(last))
        end = min(int(last), length-1) if first and last else length-1
        if start >= length or start > end:
            return Response(status_code=416, headers={'Content-Range': f'bytes */{length}'})
        headers.update({'Content-Range': f'bytes {start}-{end}/{length}', 'Content-Length': str(end-start+1)})
        return Response(data[start:end+1], status_code=206, media_type=mime, headers=headers)
    return Response(data, media_type=mime, headers=headers)


@router.post('/trigger', status_code=202, dependencies=[Depends(authorize)])
def trigger(tasks: BackgroundTasks):
    if os.getenv('SOCIAL_PAUSED', '').lower() == 'true':
        raise HTTPException(503, 'Social automation is paused')
    if any(not os.getenv(key) for key in ('GROQ_API_KEY', 'BUFFER_API_KEY')):
        raise HTTPException(503, 'GROQ_API_KEY and BUFFER_API_KEY must be configured')
    slot = current_slot()
    if slot is None:
        return {'state': 'idle', 'next_slot': '09:00 Asia/Kolkata'}
    day, owner, now = today() + ':' + slot, uuid.uuid4().hex, datetime.utcnow()
    # One database mutex serializes dispatch decisions across processes.
    with SessionLocal() as db:
        if db.get(SocialDispatch, 1) is None:
            db.add(SocialDispatch(id=1))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
        db.query(SocialDispatch).filter_by(id=1).with_for_update().one()
        active = db.query(SocialJob).filter(SocialJob.state == 'running',
            SocialJob.updated_at >= now - timedelta(minutes=15)).first()
        if active:
            return status_data(active)
        legacy = db.get(LegacyJob, today())
        # The old once-daily carousel consumes today's morning slot.
        if slot == 'morning' and legacy and legacy.state not in ('failed',):
            return {'day': today(), 'slot': slot, 'state': 'legacy_record',
                    'post_id': legacy.post_id, 'error': 'Existing daily record; check Buffer.'}
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
                if job.state in ('scheduled', 'existing', 'submitting', 'needs_review'):
                    tasks.add_task(refresh_delivery, job.day, job.owner, job.post_id)
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


def refresh_delivery(day, owner, post_id):
    """Read-only Buffer reconciliation; never creates or retries a remote post."""
    try:
        if post_id:
            post = worker.buffer('query($id:PostId!) { post(input:{id:$id}) { id status } }', {'id': post_id})['post']
        else:
            org, channel = worker.find_channel()
            recent = worker.posts(org, channel['id'], (datetime.now(timezone.utc)-timedelta(days=3)).isoformat())
            date, slot = day.split(':')
            marker = f'JeeEdge daily {date} / {slot}'
            post = next((p for p in recent if marker in (p.get('text') or '')), None)
        if not post:
            return
        state = 'published' if post['status'] == 'sent' else 'needs_review' if post['status'] in ('error', 'failed', 'notSent') else 'scheduled'
        with SessionLocal() as db:
            db.query(SocialJob).filter(SocialJob.day == day, SocialJob.owner == owner,
                SocialJob.state.in_(['scheduled', 'existing', 'submitting', 'needs_review'])).update(
                {'state': state, 'post_id': post['id'], 'updated_at': datetime.utcnow(),
                 'error': 'Buffer reports a delivery failure; inspect the existing post.' if state == 'needs_review' else None}, synchronize_session=False)
            db.commit()
    except Exception:
        # A failed status read must never reopen a submission slot.
        pass


def run_job(day, owner):
    submitting = False
    try:
        now = datetime.now(timezone.utc)
        org, channel = worker.find_channel()
        recent = worker.posts(org, channel['id'], (now - timedelta(days=3)).isoformat())
        calendar_day, slot = day.split(':')
        marker = f'JeeEdge daily {calendar_day} / {slot}'
        found = next((post for post in recent if marker in (post.get('text') or '')), None)
        if found:
            transition(day, owner, 'running', 'existing', post_id=found['id'])
            return
        if sum(p['status'] in ('scheduled', 'sending') for p in recent) >= 9:
            raise worker.ServiceError('Buffer queue near capacity; waiting.')
        content = slot_problem(day)
        copy = worker.ai_copy(content, []) if slot != 'reel' else None
        if slot == 'reel':
            copy = {'hook': 'Can you solve it before the reveal?',
                    'caption': 'Pause, solve, then watch the explanation. Save this original practice challenge for revision.'}
        with TemporaryDirectory(prefix='jeeedge-social-') as directory:
            paths = [reel.render(content, directory)] if slot == 'reel' else worker.render(content, copy, directory)
            with SessionLocal() as db:
                # Lock and verify ownership before replacing this day's media.
                job = db.query(SocialJob).filter_by(day=day).with_for_update().one()
                if job.owner != owner or job.state != 'running':
                    return
                db.query(SocialMedia).filter_by(day=day).delete()
                retained = db.query(func.coalesce(func.sum(func.length(SocialMedia.image)), 0)).scalar()
                if retained > 96 * 1024 * 1024:
                    raise worker.ServiceError('Social media storage reached its 96 MiB budget; review old media.')
                urls = []
                for path in paths:
                    media_id = uuid.uuid4().hex
                    if slot == 'reel':
                        data, mime, extension = path.read_bytes(), 'video/mp4', 'mp4'
                    else:
                        stream = io.BytesIO()
                        with Image.open(path) as image:
                            image.convert('RGB').save(stream, format='JPEG', quality=92)
                        data, mime, extension = stream.getvalue(), 'image/jpeg', 'jpg'
                    retained += len(data)
                    if retained > 96 * 1024 * 1024:
                        raise worker.ServiceError('Social media storage would exceed its 96 MiB budget.')
                    db.add(SocialMedia(id=media_id, day=day, image=data, mime=mime))
                    urls.append(f'{MEDIA_ORIGIN}/api/social/assets/{media_id}.{extension}')
                db.commit()
        if today() != calendar_day:
            raise worker.ServiceError('Generation crossed midnight; wait for the next daily trigger.')
        # Verify public fetches before any non-idempotent submission.
        for url in urls:
            body = worker.request(url, binary=True)
            if slot == 'reel':
                if len(body) < 12 or body[4:8] != b'ftyp':
                    raise worker.ServiceError('Public Reel URL did not return an MP4.')
            else:
                with Image.open(io.BytesIO(body)) as image:
                    if image.format != 'JPEG' or image.size != (1080, 1350):
                        raise worker.ServiceError('Public carousel verification failed.')
        # Durable fence MUST commit before the non-idempotent Buffer mutation.
        if not transition(day, owner, 'running', 'submitting'):
            return
        submitting = True
        caption = copy['caption'] + '\n\nOriginal practice question. More practice via the link in our bio.\n#JEE #JEEPreparation #JeeEdge\n' + marker
        payload = {'text': caption, 'channelId': channel['id'], 'schedulingType': 'automatic',
                   'mode': 'customScheduled', 'dueAt': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                   'metadata': {'instagram': {'type': 'reel' if slot == 'reel' else 'post', 'shouldShareToFeed': True}},
                   'assets': [{('video' if slot == 'reel' else 'image'): {'url': url}} for url in urls]}
        result = worker.buffer('mutation($input:CreatePostInput!) { createPost(input:$input) '
                               '{ __typename ... on PostActionSuccess { post { id status } } '
                               '... on MutationError { message } } }', {'input': payload})['createPost']
        if not result.get('post'):
            # Even an unfamiliar rejection is held for review, never blindly retried.
            raise worker.ServiceError('Buffer did not confirm a post. Check Buffer before retrying. ' + str(result.get('message', 'Unknown response.')))
        transition(day, owner, 'submitting', 'scheduled', post_id=result['post']['id'], error=None)
        # Retain media at least 14 days after confirmed publication; uncertain jobs are kept.
        with SessionLocal() as db:
            old = db.query(SocialJob.day).filter(SocialJob.day < (now - timedelta(days=14)).date().isoformat(),
                                                 SocialJob.state.in_(['published', 'failed']))
            db.query(SocialMedia).filter(SocialMedia.day.in_(old)).delete(synchronize_session=False)
            db.commit()
    except Exception as error:
        message = safe_error(error)
        transition(day, owner, 'submitting' if submitting else 'running',
                   'needs_review' if submitting else 'failed', error=message)
        print(f'JeeEdge social {day}: {message}', flush=True)
