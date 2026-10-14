"""Shared, credential-free diagnostics and state rules for the publication ledger."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from app.models.social_job import SocialCache

DELIVERY_STATES = ('scheduled','existing','submitting','needs_review','delivery_failed','blocked')
FAILED_REMOTE = ('error','failed','notSent')
POST_TTL = 7 * 86400


def key(prefix, value):
    return prefix + ':' + hashlib.sha256(value.encode()).hexdigest()[:32]


def read(db, name):
    row=db.get(SocialCache,name)
    return json.loads(row.value) if row and row.expires_at>datetime.utcnow() else None


def write(db, name, value, seconds=POST_TTL):
    encoded=json.dumps(value,ensure_ascii=False)
    if len(encoded)>4000:
        raise ValueError('Social checkpoint exceeds its storage limit.')
    db.merge(SocialCache(name=name,value=encoded,expires_at=datetime.utcnow()+timedelta(seconds=seconds)))


def stamp(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def parse_time(value):
    try:
        return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError,AttributeError,TypeError):
        return None


def remote_state(post):
    status=post.get('status')
    if post.get('schedulingType')=='notification':
        return 'needs_review','Buffer is using a phone notification, not automatic publishing. Check this existing post in Buffer.'
    if status=='sent':return 'published',None
    if status in FAILED_REMOTE:return 'delivery_failed','Buffer reports that this post failed. This post will not be submitted again automatically.'
    if status in ('draft','needs_approval'):return 'blocked','This post is a draft or needs approval in Buffer; it is not scheduled for automatic delivery.'
    if status in ('scheduled','sending'):return 'scheduled',None
    return 'needs_review','Buffer returned an unrecognised delivery state. Inspect the existing post before taking action.'


def safe_external_link(value):
    try:
        parsed=urlsplit(value or '')
        if parsed.scheme=='https' and parsed.hostname in ('instagram.com','www.instagram.com') and not parsed.username:
            return parsed._replace(query='',fragment='').geturl()
    except ValueError:
        pass
    return None


def health(jobs, heartbeat, hold, config, now=None):
    now=now or datetime.utcnow()
    issues=[]
    if config['paused']:issues.append({'code':'paused','message':'New publishing is paused on the server.'})
    if not config['buffer_configured']:issues.append({'code':'buffer_key','message':'The Buffer API key is missing on the server.'})
    if not config['trigger_configured']:issues.append({'code':'trigger_secret','message':'The cron Bearer secret is missing or too short.'})
    received=parse_time((heartbeat or {}).get('at'))
    if not received or now-received>timedelta(minutes=25):
        issues.append({'code':'cron_missing','message':'No publishing trigger was recorded in the last 25 minutes. Cron must POST /api/social/trigger; GET /api/social/status only reads status.'})
    if hold:issues.append({'code':'channel_hold','message':hold.get('reason','Buffer delivery is held.')})
    pending=[j for j in jobs if j['state'] in DELIVERY_STATES]
    stalled=[j for j in pending if (parse_time(j.get('due_at')) or now)<now-timedelta(minutes=30)]
    if stalled:issues.append({'code':'overdue','message':f'{len(stalled)} posts are overdue in Buffer. Check delivery; queued does not mean published.'})
    uncertain=[j for j in jobs if j['state'] in ('needs_review','delivery_failed','blocked')]
    if uncertain:issues.append({'code':'post_attention','message':f'{len(uncertain)} posts need attention. They are never blindly resubmitted.'})
    interrupted=[j for j in jobs if j['state']=='running' and (parse_time(j['updated_at']) or now)<now-timedelta(minutes=15)]
    if interrupted:issues.append({'code':'interrupted','message':f'{len(interrupted)} pre-submission jobs were interrupted; recent jobs can recover on the next trigger.'})
    failures=[j for j in jobs if j['state']=='failed' and (parse_time(j['updated_at']) or now)>now-timedelta(days=1)]
    if failures:issues.append({'code':'preparation_failed','message':f'{len(failures)} recent jobs stopped before submission. The job stage and error explain where to fix them.'})
    return {'state':'attention' if issues else 'ready','issues':issues,'last_trigger':heartbeat,'unresolved_posts':len(uncertain),'overdue_posts':len(stalled),
            'last_published_reel':next((j for j in jobs if j.get('kind')=='reel' and j['state'] in ('published','confirmed_published')),None)}
