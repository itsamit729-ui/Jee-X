"""Authenticated, quick-return cron trigger; state survives Render restarts."""
import io
import logging
import time
import functools
import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.social_job import SocialSlot as SocialJob, SocialAsset as SocialMedia, SocialDispatch, SocialShort
from app.models.social_job import SocialJob as LegacyJob
from app.routers.social import media as legacy_media
from social import worker, reel, lessons, editorial, storyboard, narration, quality, creative, advanced
from app.services import social_budget as budget
from app.services import instagram_comments as comments
from app.services import social_speech
from app.services import social_pipeline as pipeline
from app.services import social_shorts as shorts
from app.models.social_job import SocialCache
from app.routers.admin_dashboard import _require_admin
from urllib.parse import urlsplit
from PIL import Image

router = APIRouter(prefix='/api/social', tags=['social'])
# This is the backend origin, not a caller-controlled Host header or frontend URL.
MEDIA_ORIGIN = 'https://jee-edge.onrender.com'
LEASE = timedelta(minutes=15)
RETRY_DELAY = timedelta(minutes=10)
MANUAL_REEL_SLOT = 's99'  # Reserved; never selected by the automatic schedule.


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
        return max(1, min(12, int(os.getenv('SOCIAL_DAILY_TARGET', '12'))))
    except ValueError:
        return 12


def reel_target():
    try:
        return max(0, min(5, daily_target(), int(os.getenv('SOCIAL_REELS_PER_DAY', '4'))))
    except ValueError:
        return min(4, daily_target())


def current_slot():
    now = local_now()
    minute = now.hour * 60 + now.minute
    if not 7*60 <= minute < 23*60:
        return None
    return f's{min(daily_target()-1, (minute-7*60)*daily_target()//960):02d}'


def is_reel(slot):
    if slot == MANUAL_REEL_SLOT:
        return True
    index = int(slot[1:])
    return (index+1)*reel_target()//daily_target() > index*reel_target()//daily_target()


def slot_problem(key):
    day, slot = key.split(':')
    index=int(slot[1:])
    return quality.daily_plan(day, daily_target(), reel_target())[index]


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
    budget.cache('buffer-channel', result, 3600)
    budget.cache('channel-health', {'checked_at':pipeline.stamp(datetime.utcnow()),'state':'connected'},3600)
    return result


def media_origin():
    origin=(os.getenv('SOCIAL_MEDIA_ORIGIN') or os.getenv('RENDER_EXTERNAL_URL') or MEDIA_ORIGIN).rstrip('/')
    parsed=urlsplit(origin)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise worker.ServiceError('SOCIAL_MEDIA_ORIGIN must be a public HTTPS origin with no path or credentials.')
    return origin


def cleanup(db):
    # Keep unknown submissions intact. Confirmed delivery/failures have a bounded
    # retention window so a healthy week cannot fill the whole free media budget.
    cutoff=datetime.utcnow()-timedelta(days=2)
    old=db.query(SocialJob.day).filter(~SocialJob.day.in_(db.query(SocialShort.day).filter(or_(SocialShort.state.notin_(['published','confirmed_published','expired']),SocialShort.updated_at>=cutoff))),SocialJob.updated_at<cutoff,or_(SocialJob.state.in_(['published','confirmed_published']),
        (SocialJob.state.in_(['failed','expired'])) & SocialJob.post_id.is_(None)))
    db.query(SocialMedia).filter(SocialMedia.day.in_(old)).delete(synchronize_session=False)
    from app.models.social_job import SocialUsage
    db.query(SocialUsage).filter(SocialUsage.created_at<datetime.utcnow()-timedelta(days=31)).delete()
    db.query(SocialCache).filter(SocialCache.expires_at<datetime.utcnow()-timedelta(days=2)).delete()


def status_data(job):
    return {'day': job.day[:10], 'slot': job.day.split(':')[-1], 'state': job.state, 'attempts': job.attempts,
            'post_id': job.post_id, 'error': job.error, 'updated_at': job.updated_at.isoformat()}


@router.get('/plan', dependencies=[Depends(authorize)])
def plan_preview():
    items=quality.daily_plan(today(),daily_target(),reel_target())
    return {'day':today(), 'preview_only':True, 'items':[
        {'slot':f's{i:02}', 'kind':'reel' if is_reel(f's{i:02}') else 'carousel',
         'topic':c['topic'], 'hook':creative.opening(c), 'story':c['story_format'],
         'level':c.get('level'),'content_tier':c.get('content_tier'),
         'seconds':storyboard.beats(storyboard.plan(c))[-1] if is_reel(f's{i:02}') else None,
         'destination':creative.url(c)} for i,c in enumerate(items)]}


def status_report():
    with SessionLocal() as db:
        rows=db.query(SocialJob).order_by(SocialJob.day.desc()).limit(90).all()
        days=[row.day for row in rows]
        names=['last-publish-trigger','publishing-hold','delivery-reconciliation']+[pipeline.key(kind,row.day) for row in rows for kind in ('progress','prepared')]+[pipeline.key('delivery',row.post_id or row.day) for row in rows]
        cache={r.name:json.loads(r.value) for r in db.query(SocialCache).filter(SocialCache.name.in_(names),SocialCache.expires_at>datetime.utcnow()).all()}
        kinds={day:('reel' if mime=='video/mp4' else 'carousel') for day,mime in db.query(SocialMedia.day,SocialMedia.mime).filter(SocialMedia.day.in_(days)).distinct().all()}
        jobs=[]
        for row in rows:
            delivery=cache.get(pipeline.key('delivery',row.post_id or row.day))
            progress=cache.get(pipeline.key('progress',row.day)) or {}
            manifest=cache.get(pipeline.key('prepared',row.day)) or {}
            jobs.append({**status_data(row),'updated_at':pipeline.stamp(row.updated_at),'kind':kinds.get(row.day) or manifest.get('kind') or progress.get('kind') or ('reel' if row.day.endswith(':s99') else 'unknown'),
                'stage':progress.get('stage'),'prepared':bool(manifest),'creative':manifest.get('creative'),'due_at':(delivery or {}).get('due_at'),
                'delivery_checked_at':(delivery or {}).get('checked_at'),'operator_confirmed_at':(delivery or {}).get('operator_confirmed_at'),'published_url':(delivery or {}).get('external_link')})
        heartbeat=cache.get('last-publish-trigger')
        hold=cache.get('publishing-hold')
        config={'paused':os.getenv('SOCIAL_PAUSED','').lower()=='true','buffer_configured':bool(os.getenv('BUFFER_API_KEY')),
                'trigger_configured':len(os.getenv('SOCIAL_TRIGGER_SECRET',''))>=32,'editorial_configured':bool(os.getenv('GROQ_API_KEY')),
                'voice_enabled':os.getenv('SOCIAL_TTS_ENABLED','true').lower()=='true'}
        upcoming=[]
        now=local_now()
        for offset in (0,1):
            date=now.date()+timedelta(days=offset)
            for index in range(daily_target()):
                at=datetime.combine(date,datetime.min.time(),tzinfo=ZoneInfo('Asia/Kolkata'))+timedelta(minutes=420+(960*index+daily_target()-1)//daily_target())
                compare=now if now.tzinfo else now.replace(tzinfo=ZoneInfo('Asia/Kolkata'))
                if at>compare:
                    slot=f's{index:02d}'
                    upcoming.append({'slot':slot,'kind':'reel' if is_reel(slot) else 'carousel','at':at.isoformat()})
        return {'read_only':True,'daily_target':daily_target(),'reels_target':reel_target(),'jobs':jobs,'usage':budget.report(),
                'youtube':shorts.report(db),'publishing_hold':hold,'configuration':config,'health':pipeline.health(jobs,heartbeat,hold,config),
                'last_reconciliation':cache.get('delivery-reconciliation'),'next_windows':upcoming[:daily_target()],
                'capacity':{'source_reels_per_day':reel_target(),'source_reels_ceiling':5,
                    'shorts_per_day':reel_target() if shorts.settings(db)['enabled'] else 0,
                    'narration_requests_per_new_reel':5,'new_engine':'visual_v1',
                    'scope':'Configured output and this automation’s ledger only; provider-wide usage, audience retention and remaining account allowances are not observed.'},
                'cron':{'method':'POST','path':'/api/social/trigger','timezone':'Asia/Kolkata','interval_minutes':10,
                        'note':'GET /api/social/status never generates or publishes a post.'}}


@router.get('/status', dependencies=[Depends(authorize)])
def status():
    return status_report()


@router.post('/reconcile',status_code=202,dependencies=[Depends(authorize)])
def reconcile(tasks:BackgroundTasks):
    tasks.add_task(reconcile_pending,True)
    tasks.add_task(shorts.check,True)
    return {'state':'checking_delivery','publishes_new_work':False,'status_path':'/api/social/status'}


admin_router=APIRouter(prefix='/api/admin/social',tags=['admin'],dependencies=[Depends(_require_admin)])


@admin_router.get('')
def admin_status():
    return status_report()


@admin_router.post('/reconcile',status_code=202)
def admin_reconcile(tasks:BackgroundTasks):
    return reconcile(tasks)


class ConfirmPublished(BaseModel):
    expected_updated_at:str=Field(min_length=1,max_length=64)
    instagram_url:str=Field(min_length=10,max_length=2048)
    confirmed:bool=False


@admin_router.post('/jobs/{day}/confirm-published')
def confirm_published(day:str,body:ConfirmPublished):
    link=pipeline.safe_external_link(body.instagram_url)
    if not body.confirmed or not link or not re.fullmatch(r'/(?:p|reel|reels)/[A-Za-z0-9_-]+/?',urlsplit(link).path):
        raise HTTPException(422,'Confirm that you checked the matching existing Instagram post and provide its public post or Reel URL.')
    expected=pipeline.parse_time(body.expected_updated_at)
    with SessionLocal() as db:
        job=db.query(SocialJob).filter_by(day=day).with_for_update().first()
        if not job:raise HTTPException(404,'Job not found.')
        if job.state not in ('delivery_failed','needs_review','blocked') or job.updated_at!=expected:
            raise HTTPException(409,'This job has changed or does not need a delivery confirmation. Refresh its status.')
        before=job.state;job.state='confirmed_published';job.error=None;job.updated_at=datetime.utcnow()
        name=pipeline.key('delivery',job.post_id or job.day)
        metadata=pipeline.read(db,name) or {}
        pipeline.write(db,name,{**metadata,'external_link':link,'operator_confirmed_at':pipeline.stamp(job.updated_at)},30*86400)
        pipeline.write(db,pipeline.key('confirmation',day),{'before':before,'after':job.state,'post_id':job.post_id,'instagram_url':link,'at':pipeline.stamp(job.updated_at)},30*86400)
        db.commit()
    return {'state':'confirmed_published','publishes_new_work':False}


class ShortsSetup(BaseModel):
    enabled:bool
    channel_id:str|None=Field(None,max_length=128)
    expected_updated_at:str|None=Field(None,max_length=64)


@admin_router.get('/youtube/channels')
def youtube_channels():
    try:
        with budget.tracked():rows=worker.youtube_channels()
        return {'channels':[{'id':c['id'],'name':c.get('displayName') or c.get('name') or c['id'],
            'available':not any(c.get(k) for k in ('isDisconnected','isLocked','isQueuePaused')),
            'disconnected':bool(c.get('isDisconnected')),'locked':bool(c.get('isLocked')),'paused':bool(c.get('isQueuePaused'))} for c in rows]}
    except Exception as error:raise HTTPException(503,safe_error(error))


@admin_router.post('/youtube/config')
def youtube_setup(body:ShortsSetup):
    channel=None
    if body.enabled:
        if not body.channel_id:raise HTTPException(422,'Choose the YouTube channel connected to your Buffer account.')
        try:
            with budget.tracked():channel=worker.find_youtube_channel(body.channel_id)
        except Exception as error:raise HTTPException(503,safe_error(error))
    with SessionLocal() as db:
        budget.locked(db);previous=shorts.settings(db)
        if body.expected_updated_at!=previous.get('updated_at'):
            raise HTTPException(409,'Shorts setup changed. Refresh before saving.')
        now=pipeline.stamp(datetime.utcnow())
        starts=previous.get('starts_at') if previous['enabled'] and previous.get('channel_id')==body.channel_id else now
        config={'enabled':body.enabled,'channel_id':body.channel_id or previous.get('channel_id'),
                'channel_name':(channel or {}).get('displayName') or (channel or {}).get('name') or previous.get('channel_name'),
                'starts_at':starts,'updated_at':now}
        pipeline.write(db,shorts.CONFIG,config,3650*86400)
        cached=db.get(SocialCache,pipeline.key('youtube-channel',config['channel_id'] or ''))
        if cached:db.delete(cached)
        db.commit()
    return {'settings':config,'publishes_new_work':False,'note':'Only Reels prepared after enabling this setup are mirrored. Existing queues stay unchanged.'}


class ConfirmShort(BaseModel):
    expected_updated_at:str=Field(min_length=1,max_length=64)
    youtube_url:str=Field(min_length=10,max_length=2048)
    confirmed:bool=False


@admin_router.post('/youtube/jobs/{day}/confirm-published')
def confirm_short(day:str,body:ConfirmShort):
    url=shorts.youtube_link(body.youtube_url)
    if not body.confirmed or not url:raise HTTPException(422,'Check the matching existing YouTube Short and provide its public URL.')
    with SessionLocal() as db:
        row=db.query(SocialShort).filter_by(day=day).with_for_update().first()
        if not row:raise HTTPException(404,'Short not found.')
        if row.state not in ('delivery_failed','needs_review','blocked') or row.updated_at!=pipeline.parse_time(body.expected_updated_at):
            raise HTTPException(409,'This Short changed or does not need confirmation. Refresh its status.')
        before=row.state;row.state='confirmed_published';row.external_link=url;row.error=None;row.updated_at=datetime.utcnow()
        pipeline.write(db,pipeline.key('youtube-confirmation',day),{'before':before,'url':url,'at':pipeline.stamp(row.updated_at)},30*86400)
        db.commit()
    return {'state':'confirmed_published','publishes_new_work':False}


class RetryShort(BaseModel):
    expected_updated_at:str=Field(min_length=1,max_length=64)


@admin_router.post('/youtube/jobs/{day}/retry')
def retry_short(day:str,body:RetryShort):
    with SessionLocal() as db:
        budget.locked(db);config=shorts.settings(db)
        row=db.query(SocialShort).filter_by(day=day).with_for_update().first()
        if not row:raise HTTPException(404,'Short not found.')
        if row.state!='failed' or row.post_id or row.updated_at!=pipeline.parse_time(body.expected_updated_at):
            raise HTTPException(409,'Only a failed pre-submission Short can be retried. Refresh the row; uncertain deliveries are never resent.')
        if not config['enabled'] or config['channel_id']!=row.channel_id or row.created_at<datetime.utcnow()-timedelta(days=2):
            raise HTTPException(409,'Enable the matching channel first. Expired Shorts are not backfilled.')
        if not db.get(SocialMedia,row.asset_id):raise HTTPException(409,'The original prepared video is unavailable.')
        row.state='ready';row.attempts=0;row.error=None;row.updated_at=datetime.utcnow()
        pipeline.write(db,pipeline.key('youtube-retry',day),{'at':pipeline.stamp(row.updated_at),'post_id':None},30*86400)
        db.commit()
    return {'state':'ready','will_submit_on_next_trigger':True}


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
    return dispatch(tasks)


@router.post('/test-reel', status_code=202, dependencies=[Depends(authorize)])
def test_reel(tasks: BackgroundTasks, require_voice:bool=False):
    return dispatch(tasks, manual_reel=True, require_voice=require_voice)


def dispatch(tasks, manual_reel=False, require_voice=False):
    with SessionLocal() as db:
        pipeline.write(db,'last-publish-trigger',{'at':pipeline.stamp(datetime.utcnow()),'mode':'manual_reel' if manual_reel else 'scheduled'})
        db.commit()
    if os.getenv('SOCIAL_PAUSED', '').lower() == 'true':
        raise HTTPException(503, 'Social automation is paused')
    if not os.getenv('BUFFER_API_KEY'):
        raise HTTPException(503, 'BUFFER_API_KEY must be configured; editorial and voice can use the authored fallback.')
    if require_voice and os.getenv('SOCIAL_TTS_ENABLED', 'true').strip().lower() != 'true':
        raise HTTPException(503, 'Enable SOCIAL_TTS_ENABLED before requesting a narrated test Reel')
    tasks.add_task(shorts.tick)
    if not manual_reel and comments.enabled():
        tasks.add_task(comments.drain_safe)
    hold = budget.cached('publishing-hold')
    if hold:
        tasks.add_task(refresh_hold, hold)
        return {'state': 'delivery_hold', **hold, 'delivery_check': 'requested'}
    tasks.add_task(reconcile_pending)
    slot = MANUAL_REEL_SLOT if manual_reel else current_slot()
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
        if not manual_reel:
            current_index=int(slot[1:])
            candidates=db.query(SocialJob).filter(SocialJob.day.startswith(today()+':'),SocialJob.day!=today()+':'+MANUAL_REEL_SLOT,
                SocialJob.attempts<3,or_((SocialJob.state=='failed') & (SocialJob.updated_at<now-RETRY_DELAY),
                                       (SocialJob.state=='running') & (SocialJob.updated_at<now-LEASE))).order_by(SocialJob.day).all()
            for candidate in candidates:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}:s\d{2}',candidate.day):continue
                index=int(candidate.day.split(':s')[-1])
                if 0<=index<daily_target() and 0<=(current_index-index)*960/daily_target()<=120:
                    day=candidate.day;slot=day.split(':')[-1];break
        job = db.get(SocialJob, day)
        if not manual_reel and (job is None or job.state == 'failed'):
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
            if manual_reel and job.state == 'failed' and job.updated_at > now-timedelta(minutes=30):
                return {**status_data(job), 'retry_after': (job.updated_at+timedelta(minutes=30)).isoformat()+'Z'}
            # Reclaim only pre-submission failures or expired generation leases.
            if job.state=='failed' and job.updated_at>now-(timedelta(minutes=30) if manual_reel else RETRY_DELAY):
                return {**status_data(job),'retry_after':pipeline.stamp(job.updated_at+(timedelta(minutes=30) if manual_reel else RETRY_DELAY))}
            eligible = job.state == 'failed' or (job.state == 'running' and job.updated_at < now - LEASE)
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
        if manual_reel:
            pipeline.write(db,pipeline.key('voice-required',day),require_voice);db.commit()
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
    message = str(error) if isinstance(error, worker.ServiceError) else 'Internal worker error ('+type(error).__name__+'); check service logs.'
    for value in os.environ.values():
        if len(value) >= 12:
            message = message.replace(value, '[redacted]')
    return re.sub(r'https?://\S+', '[URL]', message)[:500]


def record_delivery(post, day=None, owner=None):
    state,error=pipeline.remote_state(post)
    if state!='published' and (post.get('error') or {}).get('message'):
        error=safe_error(worker.ServiceError('Buffer delivery: '+str(post['error']['message'])))
    with SessionLocal() as db:
        confirmed=db.query(SocialJob.state).filter(SocialJob.post_id==post['id'],SocialJob.state.in_(['published','confirmed_published'])).first()
        if confirmed and (confirmed[0]=='confirmed_published' or state!='published'):return
        query=db.query(SocialJob).filter(SocialJob.state.in_(pipeline.DELIVERY_STATES))
        if day:query=query.filter_by(day=day,owner=owner)
        else:query=query.filter_by(post_id=post['id'])
        query.update({'state':state,'post_id':post['id'],'error':error,'updated_at':datetime.utcnow()},synchronize_session=False)
        pipeline.write(db,pipeline.key('delivery',post['id']),{'status':post.get('status'),'due_at':post.get('dueAt'),
            'sent_at':post.get('sentAt'),'checked_at':pipeline.stamp(datetime.utcnow()),
            'scheduling_type':post.get('schedulingType'),'external_link':pipeline.safe_external_link(post.get('externalLink'))})
        db.commit()


@tracked
def refresh_delivery(day, owner, post_id):
    try:
        if post_id:post=worker.post(post_id)
        else:
            org,channel=find_channel()
            date,slot=day.split(':')
            marker=f'JeeEdge daily {date} / {slot}'
            found=[p for p in worker.posts(org,channel['id'],(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()) if marker in (p.get('text') or '').splitlines()]
            post=found[0] if len(found)==1 else None
        if post:record_delivery(post,day,owner)
    except Exception as error:
        logging.getLogger('uvicorn.error').warning('JeeEdge delivery check deferred: %s',safe_error(error))


@tracked
def reconcile_pending(force=False):
    """Reconcile every slot, including past windows, without publishing anything."""
    now=datetime.utcnow()
    try:
        with SessionLocal() as db:
            budget.locked(db)
            previous=pipeline.read(db,'delivery-reconciliation')
            checked=pipeline.parse_time((previous or {}).get('at'))
            if checked and now-checked<(timedelta(minutes=1) if force else timedelta(minutes=30)):
                return
            pending=db.query(SocialJob).filter(SocialJob.state.in_(pipeline.DELIVERY_STATES)).order_by(SocialJob.updated_at).limit(60).all()
            rows=[(j.day,j.owner,j.post_id) for j in pending]
            if not rows and not force:return
            budget.check(db,'buffer',units=6)
            pipeline.write(db,'delivery-reconciliation',{'at':pipeline.stamp(now),'state':'checking','posts':len(rows)})
            if force:
                cached=db.get(SocialCache,'buffer-channel')
                if cached:db.delete(cached)
            db.commit()
        with budget.tracked():
            org,channel=find_channel()
            recent=worker.posts(org,channel['id'],(datetime.now(timezone.utc)-timedelta(days=3)).isoformat())
            by_id={p['id']:p for p in recent}
            exact_left=6 if force else 1
            for day,owner,post_id in rows:
                date,slot=day.split(':')
                marker=f'JeeEdge daily {date} / {slot}'
                matches=[p for p in recent if marker in (p.get('text') or '').splitlines()]
                post=by_id.get(post_id) if post_id else matches[0] if len(matches)==1 else None
                exact_attempted=False
                if not post and post_id and exact_left:
                    post=worker.post(post_id);exact_left-=1;exact_attempted=True
                if post:record_delivery(post,day,owner)
                elif exact_attempted or not post_id:
                    with SessionLocal() as db:
                        query=db.query(SocialJob).filter_by(day=day,owner=owner).filter(SocialJob.state.in_(pipeline.DELIVERY_STATES))
                        if exact_attempted or len(matches)>1:
                            query.update({'state':'needs_review','error':'The existing post is missing or its slot marker is ambiguous. No automatic resubmission.','updated_at':now},synchronize_session=False)
                        else:
                            query.filter(SocialJob.state=='submitting',SocialJob.updated_at<now-LEASE).update({'state':'needs_review','error':'Submission outcome is unconfirmed after an interrupted request. Inspect Buffer before taking action.','updated_at':now},synchronize_session=False)
                        db.commit()
        hold=budget.cached('publishing-hold')
        if hold:refresh_hold(hold)
        with SessionLocal() as db:
            # Only expired pre-submission work is eligible for abandonment.
            db.query(SocialJob).filter(SocialJob.day<today()+':',SocialJob.state=='running',SocialJob.updated_at<now-LEASE,SocialJob.post_id.is_(None)).update(
                {'state':'expired','error':'Interrupted before submission; the original day has ended.','updated_at':now},synchronize_session=False)
            pipeline.write(db,'delivery-reconciliation',{'at':pipeline.stamp(now),'state':'checked','posts':len(rows)})
            cleanup(db);db.commit()
    except Exception as error:
        message=safe_error(error)
        with SessionLocal() as db:
            pipeline.write(db,'delivery-reconciliation',{'at':pipeline.stamp(now),'state':'deferred','error':message})
            db.commit()
        logging.getLogger('uvicorn.error').warning('JeeEdge reconciliation deferred: %s',message)


@tracked
def refresh_hold(expected):
    """Migrate an old blanket hold to post-level quarantine, never resubmission."""
    post_id=expected.get('post_id')
    if not post_id:return
    try:
        with SessionLocal() as db:
            budget.locked(db)
            current=pipeline.read(db,'publishing-hold')
            if current!=expected:return
            check=db.get(SocialCache,'hold-delivery-check')
            if check and check.value==post_id and check.expires_at>datetime.utcnow():return
            db.merge(SocialCache(name='hold-delivery-check',value=post_id,expires_at=datetime.utcnow()+timedelta(minutes=30)))
            db.commit()
        post=worker.post(post_id)
        if post and post.get('id')!=post_id:return
        if post:record_delivery(post)
        with SessionLocal() as db:
            budget.locked(db)
            current=db.get(SocialCache,'publishing-hold')
            if not current or json.loads(current.value)!=expected:return
            if not post:
                db.query(SocialJob).filter(SocialJob.post_id==post_id,SocialJob.state.in_(pipeline.DELIVERY_STATES)).update(
                    {'state':'needs_review','error':'The existing Buffer post is no longer visible. It will not be recreated automatically.','updated_at':datetime.utcnow()},synchronize_session=False)
            pipeline.write(db,'last-hold-resolution',{'at':pipeline.stamp(datetime.utcnow()),'post_id':post_id,
                'result':'published' if post and pipeline.remote_state(post)[0]=='published' else 'quarantined_without_retry'})
            db.delete(current);db.commit()
    except Exception:
        # A failed read cannot resolve the old hold or prove that a post is gone.
        pass


def hold_delivery(post):
    # Keep the compatibility entry point; a delivery error now quarantines only
    # that post. A channel circuit below detects repeated, recent failures.
    record_delivery(post)


def stage(day,owner,name):
    with SessionLocal() as db:
        job=db.query(SocialJob).filter_by(day=day,owner=owner).with_for_update().first()
        if not job or job.state not in ('running','submitting'):return False
        job.updated_at=datetime.utcnow()
        pipeline.write(db,pipeline.key('progress',day),{'stage':name,'kind':'reel' if is_reel(day.split(':')[-1]) else 'carousel','at':pipeline.stamp(job.updated_at)})
        db.commit();return True


def check_failure_circuit():
    with SessionLocal() as db:
        recent=db.query(SocialJob).filter(or_(SocialJob.post_id.isnot(None),SocialJob.state=='confirmed_published'),SocialJob.state.in_(['published','confirmed_published','delivery_failed']),
            SocialJob.updated_at>datetime.utcnow()-timedelta(days=1),SocialJob.day>=(local_now().date()-timedelta(days=1)).isoformat()+':').order_by(SocialJob.day.desc()).limit(2).all()
        if len(recent)==2 and all(j.state=='delivery_failed' for j in recent):
            raise worker.ServiceError('Two recent automation posts failed delivery. Check the Instagram connection in Buffer and reconcile delivery before scheduling more.')


@tracked
def run_job(day, owner):
    submitting=False
    phase='preflight'
    try:
        if not stage(day,owner,phase):return
        media_origin()
        org,channel=find_channel()
        recent=worker.posts(org,channel['id'],(datetime.now(timezone.utc)-timedelta(days=3)).isoformat())
        # Historical failures belonging to other posts never freeze this slot.
        with SessionLocal() as db:
            known={pid for (pid,) in db.query(SocialJob.post_id).filter(SocialJob.post_id.isnot(None),SocialJob.state.in_(pipeline.DELIVERY_STATES)).all()}
        for post in recent:
            if post['id'] in known:record_delivery(post)
        check_failure_circuit()
        calendar_day,slot=day.split(':')
        marker=f'JeeEdge daily {calendar_day} / {slot}'
        found=[p for p in recent if marker in (p.get('text') or '').splitlines()]
        if found:
            if len(found)!=1:
                raise worker.ServiceError('Multiple Buffer posts have this exact slot marker. Inspect them before continuing.')
            if transition(day,owner,'running','existing',post_id=found[0]['id']):record_delivery(found[0],day,owner)
            return
        if sum(p['status'] in ('scheduled','sending') for p in recent)>=9:
            raise worker.ServiceError('Buffer queue near capacity; waiting.')
        with SessionLocal() as db:
            manifest=pipeline.read(db,pipeline.key('prepared',day))
            strict_voice=bool(pipeline.read(db,pipeline.key('voice-required',day)))
        if manifest:
            # Media and the exact caption survive a verification failure/restart.
            urls=manifest['urls'];video=manifest['kind']=='reel';caption=manifest['caption']
            urls=[media_origin()+urlsplit(url).path for url in urls]
            with SessionLocal() as db:
                assets=db.query(SocialMedia.id,SocialMedia.mime).filter_by(day=day).all()
                available={f'{media_origin()}/api/social/assets/{identity}.{'mp4' if mime=='video/mp4' else 'jpg'}' for identity,mime in assets}
            if not urls or len(set(urls))!=len(urls) or not set(urls)<=available:raise worker.ServiceError('Prepared media no longer matches the stored assets. Inspect this slot before continuing.')
        else:
            budget.admission()
            phase='prepare_lesson';stage(day,owner,phase)
            from app.models.social_comment import SocialLesson
            with SessionLocal() as db:
                saved=db.get(SocialLesson,day)
                if saved:content=json.loads(saved.content)
                elif slot==MANUAL_REEL_SLOT:
                    used={json.loads(row.content).get('topic') for row in db.query(SocialLesson).filter(SocialLesson.slot.startswith(calendar_day+':')).all()}
                    candidates=[advanced.manual(calendar_day,i) for i in range(len(advanced.BANK))]
                    candidate=next((c for c in candidates if c['topic'] not in used),None)
                    if candidate is None:raise worker.ServiceError('All visual topics already used today; hold the test to avoid a repeated lesson.')
                    content=creative.attach(quality.enrich(candidate),calendar_day,len(used))
                else:content=slot_problem(day)
                job=db.query(SocialJob).filter_by(day=day,owner=owner,state='running').with_for_update().first()
                if not job:return
                comments.save_lesson(db,day,content);db.commit()
            video=is_reel(slot)
            yesterday=(local_now().date()-timedelta(days=1)).isoformat()
            recent_captions=[p.get('text') or '' for p in recent if any(f'JeeEdge daily {d} / ' in (p.get('text') or '') for d in (calendar_day,yesterday))]
            copy=editorial.package(content,'reel' if video else 'carousel',recent=recent_captions)
            if editorial.repeated(copy['caption'],recent_captions):raise worker.ServiceError('Caption repeats a recent lesson; holding this slot for content review.')
            if video:
                copy['storyboard']=storyboard.plan(content);copy['storyboard']['hook']=copy['hook']
                if slot==MANUAL_REEL_SLOT:copy['storyboard']['pace']='brisk'
            credit=('\n\n'+reel.music_credit(content)) if video else ''
            caption=copy['caption']+(creative.caption_suffix(content) if creative.active(content) else '')+credit+'\n\n'+marker
            if len(caption)>2200:raise worker.ServiceError('Prepared Instagram caption exceeds 2200 characters; nothing submitted.')
            with TemporaryDirectory(prefix='jeeedge-social-') as directory:
                phase='narration';stage(day,owner,phase)
                if video:copy['voice_clips']=narration.prepare(content,copy['storyboard'],directory,social_speech.fetch)
                if strict_voice and len(copy.get('voice_clips',[]))!=len(narration.scenes(content,copy['storyboard'])):
                    raise worker.ServiceError('Narrated test held: all narration scenes must be valid. Nothing sent to Buffer; retry later or use the production music fallback.')
                phase='render';stage(day,owner,phase)
                ticket=budget.reserve('render',units=180);started=time.monotonic()
                try:paths=[reel.render(content,directory,copy)] if video else worker.render(content,copy,directory)
                finally:
                    render_seconds=int(time.monotonic()-started)+1
                    budget.settle(ticket,units=render_seconds)
                with SessionLocal() as db:
                    job=db.query(SocialJob).filter_by(day=day,owner=owner,state='running').with_for_update().first()
                    if not job:return
                    cleanup(db)
                    db.query(SocialMedia).filter_by(day=day).delete()
                    retained=db.query(func.coalesce(func.sum(func.length(SocialMedia.image)),0)).scalar()
                    urls=[]
                    for path in paths:
                        media_id=uuid.uuid4().hex
                        if video:data,mime,extension=path.read_bytes(),'video/mp4','mp4'
                        else:
                            stream=io.BytesIO()
                            with Image.open(path) as image:image.convert('RGB').save(stream,format='JPEG',quality=92)
                            data,mime,extension=stream.getvalue(),'image/jpeg','jpg'
                        retained+=len(data)
                        if retained>96*1024*1024:raise worker.ServiceError('Social media storage reached 96 MiB. Reconcile older queued posts; their media is retained until delivery is known.')
                        db.add(SocialMedia(id=media_id,day=day,image=data,mime=mime))
                        urls.append(f'{media_origin()}/api/social/assets/{media_id}.{extension}')
                    manifest={'urls':urls,'kind':'reel' if video else 'carousel','caption':caption,'created_at':pipeline.stamp(datetime.utcnow()),
                              'creative':{'engine':content.get('story_engine') or ('creative_v4' if creative.active(content) else 'legacy'),
                                  'topic':content['topic'],'story':content.get('story_format'),
                                  'seconds':storyboard.beats(copy['storyboard'])[-1] if video else None,
                                  'voice_expected':len(narration.scenes(content,copy['storyboard'])) if video else 0,
                                  'voice_ready':len(copy.get('voice_clips',[])), 'editorial':copy.get('editorial_source','unknown'),
                                  'render_seconds':render_seconds,'media_bytes':sum(len(p.read_bytes()) for p in paths)}}
                    pipeline.write(db,pipeline.key('prepared',day),manifest)
                    db.commit()
        if video:
            try:shorts.prepare(day)
            except Exception as error:logging.getLogger('uvicorn.error').warning('Shorts checkpoint deferred: %s',safe_error(error))
        if today()!=calendar_day:raise worker.ServiceError('Generation crossed midnight; wait for the next daily trigger.')
        phase='verify_public_media';stage(day,owner,phase)
        for url in urls:
            body=worker.request(url,binary=True,max_bytes=8*1024*1024)
            if video:
                if len(body)<12 or body[4:8]!=b'ftyp':raise worker.ServiceError('Public Reel URL did not return an MP4. Check the configured public media origin.')
            else:
                with Image.open(io.BytesIO(body)) as image:
                    if image.format!='JPEG' or image.size!=(1080,1350):raise worker.ServiceError('Public carousel verification failed.')
        # Existing ambiguous/delivered jobs can never cross this fence twice.
        if not transition(day,owner,'running','submitting'):return
        submitting=True;phase='submit';stage(day,owner,phase)
        payload={'text':caption,'channelId':channel['id'],'schedulingType':'automatic','mode':'customScheduled',
            'dueAt':(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(),
            'metadata':{'instagram':{'type':'reel' if video else 'post','shouldShareToFeed':True}},
            'assets':[{('video' if video else 'image'):{'url':url}} for url in urls]}
        result=worker.buffer('mutation($input:CreatePostInput!) { createPost(input:$input) { __typename ... on PostActionSuccess { post { '+worker.POST_FIELDS+' } } ... on MutationError { message } } }',{'input':payload})['createPost']
        post=result.get('post')
        if not post or not post.get('id'):raise worker.ServiceError('Buffer did not confirm a post. Inspect Buffer before retrying. '+str(result.get('message','Unknown response.')))
        if transition(day,owner,'submitting','scheduled',post_id=post['id'],error=None):
            record_delivery({**post,'dueAt':post.get('dueAt') or payload['dueAt'],'schedulingType':post.get('schedulingType') or 'automatic'},day,owner)
        with SessionLocal() as db:
            pipeline.write(db,pipeline.key('progress',day),{'stage':'accepted_by_buffer','at':pipeline.stamp(datetime.utcnow())});db.commit()
    except Exception as error:
        message=safe_error(error)
        transition(day,owner,'submitting' if submitting else 'running','needs_review' if submitting else 'failed',error=message)
        with SessionLocal() as db:
            pipeline.write(db,pipeline.key('progress',day),{'stage':phase,'kind':'reel' if is_reel(day.split(':')[-1]) else 'carousel','error':message,'at':pipeline.stamp(datetime.utcnow())});db.commit()
        logging.getLogger('uvicorn.error').warning('JeeEdge social slot=%s stage=%s: %s',day,phase,message)
