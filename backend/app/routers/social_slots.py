"""Authenticated, quick-return cron trigger; state survives Render restarts."""
import io
import time
import functools
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
from social import worker, reel, lessons, editorial, storyboard, narration
from app.services import social_budget as budget
from app.services import instagram_comments as comments
from app.services import social_speech
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


def daily_target():
    try:
        return max(1, min(30, int(os.getenv('SOCIAL_DAILY_TARGET', '30'))))
    except ValueError:
        return 30


def reel_target():
    try:
        return max(0, min(daily_target(), int(os.getenv('SOCIAL_REELS_PER_DAY', '10'))))
    except ValueError:
        return min(10, daily_target())


def current_slot():
    now = local_now()
    minute = now.hour * 60 + now.minute
    if not 7*60 <= minute < 23*60:
        return None
    return f's{min(daily_target()-1, (minute-7*60)*daily_target()//960):02d}'


def is_reel(slot):
    index = int(slot[1:])
    return (index+1)*reel_target()//daily_target() > index*reel_target()//daily_target()


def slot_problem(key):
    day, slot = key.split(':')
    index=int(slot[1:])
    if is_reel(slot):
        ordinal=(index+1)*reel_target()//daily_target()-1
        return lessons.visual_lesson(day,ordinal)
    return lessons.lesson(day,index)


def tracked(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        with budget.tracked():
            return function(*args, **kwargs)
    return wrapper


def find_channel():
    cached = budget.cached('buffer-channel')
    if cached:
        return cached[0], cached[1]
    result = worker.find_channel()
    budget.cache('buffer-channel', result, 86400)
    return result


def cleanup(db):
    cutoff = (datetime.utcnow()-timedelta(days=7)).date().isoformat()
    old = db.query(SocialJob.day).filter(SocialJob.day < cutoff, SocialJob.state.in_(['published','failed']))
    db.query(SocialMedia).filter(SocialMedia.day.in_(old)).delete(synchronize_session=False)
    from app.models.social_job import SocialUsage, SocialCache
    db.query(SocialUsage).filter(SocialUsage.created_at < datetime.utcnow()-timedelta(days=31)).delete()
    db.query(SocialCache).filter(SocialCache.expires_at < datetime.utcnow()-timedelta(days=2)).delete()


def status_data(job):
    return {'day': job.day[:10], 'slot': job.day.split(':')[-1], 'state': job.state, 'attempts': job.attempts,
            'post_id': job.post_id, 'error': job.error, 'updated_at': job.updated_at.isoformat()}


@router.get('/status', dependencies=[Depends(authorize)])
def status():
    with SessionLocal() as db:
        rows = db.query(SocialJob).order_by(SocialJob.day.desc()).limit(90).all()
        return {'daily_target': daily_target(), 'reels_target': reel_target(),
                'jobs': [status_data(row) for row in rows], 'usage': budget.report()}


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
        budget.record_egress(end-start+1)
        return Response(data[start:end+1], status_code=206, media_type=mime, headers=headers)
    budget.record_egress(length)
    return Response(data, media_type=mime, headers=headers)


@router.post('/trigger', status_code=202, dependencies=[Depends(authorize)])
def trigger(tasks: BackgroundTasks):
    if os.getenv('SOCIAL_PAUSED', '').lower() == 'true':
        raise HTTPException(503, 'Social automation is paused')
    if any(not os.getenv(key) for key in ('GROQ_API_KEY', 'BUFFER_API_KEY')):
        raise HTTPException(503, 'GROQ_API_KEY and BUFFER_API_KEY must be configured')
    if comments.enabled():
        tasks.add_task(comments.drain_safe)
    slot = current_slot()
    if slot is None:
        return {'state': 'idle', 'next_slot': '07:00 Asia/Kolkata'}
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
        job = db.get(SocialJob, day)
        if job is None:
            # Existing same-day submissions count toward the new target during migration.
            used = db.query(SocialJob).filter(SocialJob.day.startswith(today()+':'),
                SocialJob.state != 'failed').count()
            if legacy and legacy.state != 'failed':
                used += 1
            if used >= daily_target():
                return {'state': 'daily_limit', 'day': today(), 'limit': daily_target()}
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


@tracked
def refresh_delivery(day, owner, post_id):
    """Read-only Buffer reconciliation; never creates or retries a remote post."""
    try:
        if post_id:
            post = worker.buffer('query($id:PostId!) { post(input:{id:$id}) { id status } }', {'id': post_id})['post']
        else:
            org, channel = find_channel()
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


@tracked
def run_job(day, owner):
    submitting = False
    try:
        budget.admission()
        now = datetime.now(timezone.utc)
        org, channel = find_channel()
        recent = worker.posts(org, channel['id'], (now - timedelta(days=3)).isoformat())
        # Reconcile all recently observed delivery states without extra API calls.
        with SessionLocal() as db:
            for post in recent:
                if post['status'] == 'sent':
                    db.query(SocialJob).filter(SocialJob.post_id == post['id']).update({'state':'published'}, synchronize_session=False)
            cleanup(db)
            db.commit()
        calendar_day, slot = day.split(':')
        marker = f'JeeEdge daily {calendar_day} / {slot}'
        found = next((post for post in recent if marker in (post.get('text') or '')), None)
        if found:
            transition(day, owner, 'running', 'existing', post_id=found['id'])
            return
        if sum(p['status'] in ('scheduled', 'sending') for p in recent) >= 9:
            raise worker.ServiceError('Buffer queue near capacity; waiting.')
        # Preserve any existing generation snapshot across a renderer rollout.
        from app.models.social_comment import SocialLesson
        import json
        with SessionLocal() as db:
            saved=db.get(SocialLesson,day)
            content=json.loads(saved.content) if saved else slot_problem(day)
        video = is_reel(slot)
        copy = editorial.package(content, 'reel' if video else 'carousel')
        if video:
            copy['storyboard']=storyboard.plan(content)
        with TemporaryDirectory(prefix='jeeedge-social-') as directory:
            if video:
                copy['voice_clips'] = narration.prepare(content, copy['storyboard'], directory, social_speech.fetch)
            ticket = budget.reserve('render', units=180)
            started = time.monotonic()
            paths = [reel.render(content, directory, copy)] if video else worker.render(content, copy, directory)
            budget.settle(ticket, units=int(time.monotonic()-started)+1)
            with SessionLocal() as db:
                # Lock and verify ownership before replacing this day's media.
                job = db.query(SocialJob).filter_by(day=day).with_for_update().one()
                if job.owner != owner or job.state != 'running':
                    return
                comments.save_lesson(db, day, content)
                db.query(SocialMedia).filter_by(day=day).delete()
                retained = db.query(func.coalesce(func.sum(func.length(SocialMedia.image)), 0)).scalar()
                if retained > 96 * 1024 * 1024:
                    raise worker.ServiceError('Social media storage reached its 96 MiB budget; review old media.')
                urls = []
                for path in paths:
                    media_id = uuid.uuid4().hex
                    if video:
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
            if video:
                if len(body) < 12 or body[4:8] != b'ftyp':
                    raise worker.ServiceError('Public Reel URL did not return an MP4.')
            else:
                with Image.open(io.BytesIO(body)) as image:
                    if image.format != 'JPEG' or image.size != (1080, 1350):
                        raise worker.ServiceError('Public carousel verification failed.')
        credit = ('\n\n' + reel.music_credit()) if video else ''
        # Durable fence MUST commit before the non-idempotent Buffer mutation.
        if not transition(day, owner, 'running', 'submitting'):
            return
        submitting = True
        caption = copy['caption'] + credit + '\n\nOriginal practice question. Save the rule and its conditions for revision.\n#JEE #JEEPreparation #JeeEdge\n' + marker
        payload = {'text': caption, 'channelId': channel['id'], 'schedulingType': 'automatic',
                   'mode': 'customScheduled', 'dueAt': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                   'metadata': {'instagram': {'type': 'reel' if video else 'post', 'shouldShareToFeed': True}},
                   'assets': [{('video' if video else 'image'): {'url': url}} for url in urls]}
        result = worker.buffer('mutation($input:CreatePostInput!) { createPost(input:$input) '
                               '{ __typename ... on PostActionSuccess { post { id status } } '
                               '... on MutationError { message } } }', {'input': payload})['createPost']
        if not result.get('post'):
            # Even an unfamiliar rejection is held for review, never blindly retried.
            raise worker.ServiceError('Buffer did not confirm a post. Check Buffer before retrying. ' + str(result.get('message', 'Unknown response.')))
        transition(day, owner, 'submitting', 'scheduled', post_id=result['post']['id'], error=None)
        # Retain media at least 7 days after confirmed publication; uncertain jobs are kept.
        with SessionLocal() as db:
            old = db.query(SocialJob.day).filter(SocialJob.day < (now - timedelta(days=7)).date().isoformat(),
                                                 SocialJob.state.in_(['published', 'failed']))
            db.query(SocialMedia).filter(SocialMedia.day.in_(old)).delete(synchronize_session=False)
            db.commit()
    except Exception as error:
        message = safe_error(error)
        transition(day, owner, 'submitting' if submitting else 'running',
                   'needs_review' if submitting else 'failed', error=message)
        print(f'JeeEdge social {day}: {message}', flush=True)
