"""Independent Shorts delivery using immutable Reel assets and the existing Buffer budget."""
import json
from copy import deepcopy
from html import unescape
import logging
import os
import re
import uuid
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit,parse_qs
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.social_job import SocialShort,SocialSlot,SocialAsset
from app.models.social_comment import SocialLesson
from app.services import social_budget as budget,social_pipeline as pipeline
from social import worker,creative,editorial,reel

CONFIG='youtube-settings'
PENDING=('scheduled','submitting','needs_review','delivery_failed','blocked','repairing')
LEASE=timedelta(minutes=15)


def settings(db):
    return pipeline.read(db,CONFIG) or {'enabled':False,'channel_id':None,'starts_at':None,'updated_at':None}


def safe_error(error):
    from app.routers.social_slots import safe_error as sanitize
    return sanitize(error)


def origin():
    from app.routers.social_slots import media_origin
    return media_origin()


def youtube_link(value):
    try:
        url=urlsplit(value or '')
        if url.scheme!='https' or url.username or url.password or url.port not in (None,443):return None
        if url.hostname in ('youtube.com','www.youtube.com','m.youtube.com'):
            identity=url.path.rstrip('/').split('/')[-1] if url.path.startswith('/shorts/') else parse_qs(url.query).get('v',[''])[0] if url.path=='/watch' else ''
        elif url.hostname=='youtu.be':identity=url.path.strip('/')
        else:return None
        if re.fullmatch('[A-Za-z0-9_-]{11}',identity):return 'https://www.youtube.com/shorts/'+identity
    except ValueError:pass
    return None


def marker(day):
    date,slot=day.split(':')
    return f'JeeEdge Shorts {date} / {slot}'


def youtube_text(value):
    """YouTube forbids literal ASCII angle brackets, even in maths descriptions."""
    value=unescape(value).replace('\r\n','\n').replace('\r','\n')
    for before,after in (('<=>','⇌'),('<->','↔'),('<=','≤'),('>=','≥'),('->','→'),('<-','←'),
                         ('<','＜'),('>','＞')):
        value=value.replace(before,after)
    return ''.join(c for c in value if ord(c)>=32 or c in '\n\t').strip()


def validated_payload(value):
    payload=deepcopy(value)
    title=' '.join(youtube_text(payload['metadata']['youtube']['title']).split())
    text=youtube_text(payload['text'])
    if not 1<=len(title)<=100:
        raise worker.ServiceError('YouTube title must contain 1–100 characters after math conversion.')
    if len(text.encode('utf-8'))>5000:
        raise worker.ServiceError('YouTube description exceeds 5,000 UTF-8 bytes. Shorten the caption before submission.')
    payload['metadata']['youtube']['title']=title;payload['text']=text
    return payload


def caption_repairable(row):
    if row.state!='delivery_failed' or not row.post_id or row.external_link:return False
    payload=json.loads(row.payload)
    text=youtube_text(payload['text'])
    return any(c in payload['text'] for c in '<>') and len(text.encode('utf-8'))<=5000


def prepare(day):
    """Local checkpoint only; no render, provider request or upload."""
    if day.endswith(':s99'):return
    with SessionLocal() as db:
        config=settings(db)
        if not config['enabled'] or not config.get('channel_id') or db.get(SocialShort,day):return
        manifest=pipeline.read(db,pipeline.key('prepared',day)) or {}
        made=pipeline.parse_time(manifest.get('created_at'));starts=pipeline.parse_time(config.get('starts_at'))
        if manifest.get('kind')!='reel' or not made or not starts or made<starts:return
        lesson=db.get(SocialLesson,day)
        assets=db.query(SocialAsset).filter_by(day=day,mime='video/mp4').all()
        if not lesson or len(assets)!=1:return
        c=json.loads(lesson.content)
        title=' '.join(youtube_text(creative.opening(c)).split())
        if len(title)>80:title=c['topic']
        title=title+' | Jee Edge #Shorts'
        description=(editorial.authored(c)['caption']+'\n\nPractise by chapter: '
            'https://jeeedge.in/start?utm_source=youtube&utm_medium=organic_social&utm_campaign=shorts&to=practice'
            '\nOriginal teaching example, not an official PYQ.\n'+reel.music_credit(c)+'\n\n'+marker(day))
        now=datetime.utcnow()
        payload=validated_payload({'text':description,'metadata':{'youtube':{'title':title,'categoryId':'27','privacy':'public',
            'madeForKids':False,'embeddable':True,'notifySubscribers':False,'isAiGenerated':True}}})
        db.add(SocialShort(day=day,channel_id=config['channel_id'],asset_id=assets[0].id,payload=json.dumps(payload),
            state='ready',owner=uuid.uuid4().hex,attempts=0,created_at=now,updated_at=now))
        try:db.commit()
        except IntegrityError:db.rollback()  # A concurrent worker already checkpointed this slot.


def record(day,post):
    state,error=pipeline.remote_state(post)
    if state!='published' and (post.get('error') or {}).get('message'):
        error=safe_error(worker.ServiceError('YouTube delivery: '+str(post['error']['message'])))
    with SessionLocal() as db:
        row=db.query(SocialShort).filter_by(day=day).with_for_update().first()
        if not row or row.state in ('published','confirmed_published'):return
        row.post_id=post['id'];row.state=state;row.error=error
        row.checked_at=datetime.utcnow();row.updated_at=datetime.utcnow()
        row.due_at=pipeline.parse_time(post.get('dueAt')) or row.due_at
        row.external_link=youtube_link(post.get('externalLink')) or row.external_link
        db.commit()


def _defer(day,error):
    with SessionLocal() as db:
        row=db.get(SocialShort,day)
        if row and row.state in PENDING:
            row.checked_at=datetime.utcnow();row.error=safe_error(error);db.commit()


def check(force=False):
    """Read-only provider reconciliation. Never submits, queues or retries a post."""
    try:
        with budget.tracked():
            now=datetime.utcnow()
            with SessionLocal() as db:
                budget.locked(db)
                cache=pipeline.read(db,'youtube-delivery-check')
                last=pipeline.parse_time((cache or {}).get('at'))
                if last and now-last<timedelta(minutes=1):return
                quarantine=('needs_review','delivery_failed','blocked')
                elapsed=SocialShort.checked_at<now-timedelta(minutes=1 if force else 30)
                if not force:
                    elapsed=or_(and_(SocialShort.state.notin_(quarantine),elapsed),
                                and_(SocialShort.state.in_(quarantine),SocialShort.checked_at<now-timedelta(hours=4)))
                rows=db.query(SocialShort).filter(SocialShort.state.in_(PENDING),or_(SocialShort.checked_at.is_(None),
                    elapsed)).order_by(SocialShort.checked_at,SocialShort.updated_at).limit(2).all()
                rows=[(r.day,r.post_id,r.organization_id,r.channel_id,r.updated_at,r.due_at) for r in rows]
                if not rows:return
                budget.check(db,'buffer',units=10)  # Leave Instagram headroom; never raise the shared budget.
                pipeline.write(db,'youtube-delivery-check',{'at':pipeline.stamp(now)});db.commit()
            for day,post_id,org,channel,updated,due in rows:
                if not force and due and due>now:continue
                try:
                    if post_id:
                        post=worker.post(post_id)
                        if post and post.get('id')!=post_id:raise worker.ServiceError('YouTube delivery check returned a different post. Nothing resubmitted.')
                    elif org:
                        found=[p for p in worker.posts(org,channel,(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()) if marker(day) in (p.get('text') or '').splitlines()]
                        post=found[0] if len(found)==1 else None
                    else:post=None
                    if post:record(day,post)
                    elif post_id or updated<now-LEASE:
                        with SessionLocal() as db:
                            row=db.get(SocialShort,day)
                            if row and row.state in PENDING:
                                row.state='needs_review';row.error='Existing YouTube submission is missing or unconfirmed. No automatic resubmission.'
                                row.checked_at=now;row.updated_at=now;db.commit()
                except Exception as error:_defer(day,error)
    except Exception as error:
        logging.getLogger('uvicorn.error').warning('Shorts delivery check deferred: %s',safe_error(error))


def _transition(day,owner,before,after,**values):
    with SessionLocal() as db:
        n=db.query(SocialShort).filter_by(day=day,owner=owner,state=before).update(
            {'state':after,'updated_at':datetime.utcnow(),**values},synchronize_session=False)
        db.commit();return n==1


def run(day,owner):
    submitted=False
    try:
        with budget.tracked():
            with SessionLocal() as db:
                row=db.get(SocialShort,day);config=settings(db)
                if not row or row.owner!=owner or row.state!='running':return
                if not config['enabled'] or config.get('channel_id')!=row.channel_id:
                    raise worker.ServiceError('Shorts publishing is disabled or the selected channel changed.')
                budget.check(db,'buffer',units=10)
                channel_id=row.channel_id;asset_id=row.asset_id;payload=validated_payload(json.loads(row.payload))
                row.payload=json.dumps(payload);db.commit()
            cached=budget.cached(pipeline.key('youtube-channel',channel_id))
            channel=cached or worker.find_youtube_channel(channel_id)
            if not cached:budget.cache(pipeline.key('youtube-channel',channel_id),channel,3600)
            org=channel['organization_id']
            recent=worker.posts(org,channel_id,(datetime.now(timezone.utc)-timedelta(days=3)).isoformat())
            found=[p for p in recent if marker(day) in (p.get('text') or '').splitlines()]
            if len(found)>1:
                _transition(day,owner,'running','needs_review',error='Multiple YouTube posts have this exact slot marker. No automatic resubmission.')
                return
            if found:record(day,found[0]);return
            if sum(p.get('status') in ('scheduled','sending') for p in recent)>=9:raise worker.ServiceError('YouTube queue near capacity; waiting without upgrading the plan.')
            with SessionLocal() as db:
                asset=db.get(SocialAsset,asset_id)
                if not asset or asset.day!=day or asset.mime!='video/mp4':raise worker.ServiceError('Prepared Reel asset is unavailable. Nothing sent to YouTube.')
            url=origin()+f'/api/social/assets/{asset_id}.mp4'
            body=worker.request(url,binary=True,max_bytes=8*1024*1024)
            if len(body)<12 or body[4:8]!=b'ftyp':raise worker.ServiceError('Public Shorts asset did not return an MP4.')
            due=datetime.utcnow()+timedelta(minutes=5)
            with SessionLocal() as db:
                budget.locked(db);config=settings(db)
                if not config['enabled'] or config.get('channel_id')!=channel_id:
                    raise worker.ServiceError('Shorts setup changed before submission. Nothing sent.')
                n=db.query(SocialShort).filter_by(day=day,owner=owner,state='running').update(
                    {'state':'submitting','organization_id':org,'due_at':due,'updated_at':datetime.utcnow()},synchronize_session=False)
                db.commit()
                if not n:return
            submitted=True
            payload.update(channelId=channel_id,schedulingType='automatic',mode='customScheduled',
                dueAt=pipeline.stamp(due),assets=[{'video':{'url':url}}])
            response=worker.buffer('mutation($input:CreatePostInput!){createPost(input:$input){... on PostActionSuccess{post{'+worker.POST_FIELDS+'}} ... on MutationError{message}}}',{'input':payload})['createPost']
            post=response.get('post')
            if not post or not post.get('id'):raise worker.ServiceError('Buffer did not confirm the YouTube submission. Inspect the existing queue before taking action. '+str(response.get('message') or 'No confirmation returned.'))
            record(day,{**post,'dueAt':post.get('dueAt') or pipeline.stamp(due),'schedulingType':post.get('schedulingType') or 'automatic'})
    except Exception as error:
        _transition(day,owner,'submitting' if submitted else 'running','needs_review' if submitted else 'failed',error=safe_error(error))
        logging.getLogger('uvicorn.error').warning('Shorts slot=%s: %s',day,safe_error(error))


def repair_caption(day,owner):
    """Explicit admin recovery: edit and reschedule the same failed Buffer ID."""
    submitting=False
    try:
        with budget.tracked():
            with SessionLocal() as db:
                row=db.get(SocialShort,day);config=settings(db)
                if not row or row.owner!=owner or row.state!='repairing':return
                if os.getenv('SOCIAL_PAUSED','').lower()=='true' or not config['enabled'] or config.get('channel_id')!=row.channel_id:
                    raise worker.ServiceError('Shorts setup changed or publishing is paused. Nothing edited.')
                budget.check(db,'buffer',units=3);post_id=row.post_id
            post=worker.post(post_id)
            if not post or post.get('id')!=post_id or marker(day) not in (post.get('text') or '').splitlines():
                raise worker.ServiceError('Existing Buffer post could not be matched to this Short. Nothing edited.')
            if post.get('status') not in pipeline.FAILED_REMOTE:
                record(day,post);return  # Already sent or scheduled; never reschedule it.
            live_link=youtube_link(post.get('externalLink'))
            if live_link:
                _transition(day,owner,'repairing','needs_review',external_link=live_link,
                            error='Buffer returned a YouTube link for this failed post. Check whether it is already live before retrying.')
                return
            current=post.get('text') or ''
            corrected=youtube_text(current)
            if not any(c in current for c in '<>'):
                with SessionLocal() as db:
                    row=db.query(SocialShort).filter_by(day=day,owner=owner,state='repairing').first()
                    if row:
                        payload=json.loads(row.payload);payload['text']=current;row.payload=json.dumps(payload);db.commit()
                raise worker.ServiceError('The existing Buffer caption already meets YouTube text rules. No retry made; the unknown delivery error needs a different fix.')
            if len(corrected.encode('utf-8'))>5000:
                raise worker.ServiceError('Corrected caption exceeds 5,000 UTF-8 bytes. Nothing edited.')
            with SessionLocal() as db:
                row=db.query(SocialShort).filter_by(day=day,owner=owner,state='repairing').with_for_update().first()
                config=settings(db)
                if not row:return
                if not config['enabled'] or config.get('channel_id')!=row.channel_id or os.getenv('SOCIAL_PAUSED','').lower()=='true':
                    raise worker.ServiceError('Shorts setup changed before repair. Nothing edited.')
                row.updated_at=datetime.utcnow();db.commit()
            due=pipeline.stamp(datetime.utcnow()+timedelta(minutes=5))
            submitting=True
            result=worker.buffer('mutation($input:EditPostInput!){editPost(input:$input){... on PostActionSuccess{post{'+worker.POST_FIELDS+'}} ... on MutationError{message}}}',
                {'input':{'id':post_id,'text':corrected,'schedulingType':'automatic','mode':'customScheduled','dueAt':due}})['editPost']
            edited=result.get('post')
            if not edited or edited.get('id')!=post_id:
                raise worker.ServiceError('Buffer did not confirm the caption repair. Check the existing post. '+str(result.get('message') or ''))
            record(day,{**edited,'dueAt':edited.get('dueAt') or due,'schedulingType':edited.get('schedulingType') or 'automatic'})
            with SessionLocal() as db:
                row=db.query(SocialShort).filter_by(day=day,owner=owner,post_id=post_id).with_for_update().first()
                if row:
                    payload=json.loads(row.payload);payload['text']=corrected;row.payload=json.dumps(payload);db.commit()
    except Exception as error:
        _transition(day,owner,'repairing','needs_review' if submitting else 'delivery_failed',error=safe_error(error))
        logging.getLogger('uvicorn.error').warning('Shorts caption repair slot=%s: %s',day,safe_error(error))


def prepare_recent():
    with SessionLocal() as db:
        config=settings(db)
        if not config['enabled']:return
        rows=db.query(SocialSlot.day).join(SocialAsset,SocialSlot.day==SocialAsset.day).filter(
            SocialAsset.mime=='video/mp4',SocialSlot.updated_at>datetime.utcnow()-timedelta(days=2),
            ~SocialSlot.day.in_(db.query(SocialShort.day))).order_by(SocialSlot.day.desc()).limit(12).all()
    for (day,) in rows:
        try:prepare(day)
        except Exception as error:logging.getLogger('uvicorn.error').warning('Shorts checkpoint slot=%s deferred: %s',day,safe_error(error))


def tick():
    """One prepared Short per worker pass, with a pre-submission lease and bounded retries."""
    outcome={'at':pipeline.stamp(datetime.utcnow()),'state':'checking','reason':None}
    try:
        if os.getenv('SOCIAL_PAUSED','').lower()=='true':
            outcome.update(state='paused',reason='Social publishing is paused on the server.');return
        prepare_recent();check()
        now=datetime.utcnow();owner=uuid.uuid4().hex
        with SessionLocal() as db:
            budget.locked(db);config=settings(db)
            db.query(SocialShort).filter(SocialShort.state.in_(('ready','failed','running')),SocialShort.post_id.is_(None),
                SocialShort.created_at<now-timedelta(days=2)).update({'state':'expired','updated_at':now,'error':'Prepared Short expired before submission.'},synchronize_session=False)
            if not config['enabled']:
                outcome.update(state='disabled',reason='YouTube Shorts publishing is disabled.');db.commit();return
            budget.check(db,'buffer',units=10)
            row=db.query(SocialShort).filter(SocialShort.channel_id==config['channel_id'],SocialShort.attempts<3,
                or_(SocialShort.state=='ready',(SocialShort.state=='failed') & (SocialShort.updated_at<now-timedelta(minutes=10)),
                    (SocialShort.state=='running') & (SocialShort.updated_at<now-LEASE))).order_by(SocialShort.created_at).first()
            if not row:
                outcome.update(state='idle',reason='No eligible Short was waiting at this check.');db.commit();return
            day=row.day;row.state='running';row.owner=owner;row.attempts+=1;row.error=None;row.updated_at=now;db.commit()
        run(day,owner)
        outcome.update(state='processed',reason='Checked the prepared Short for submission.',slot=day)
    except Exception as error:
        outcome.update(state='deferred',reason=safe_error(error))
        if isinstance(error,budget.BudgetExceeded):
            outcome.update(retry_at=error.retry_at,budget=error.details)
        logging.getLogger('uvicorn.error').warning('Shorts tick deferred: %s',safe_error(error))
    finally:
        try:
            with SessionLocal() as db:
                pipeline.write(db,'youtube-worker',outcome);db.commit()
        except Exception:
            logging.getLogger('uvicorn.error').warning('Shorts worker heartbeat could not be saved.')


def report(db):
    config=settings(db)
    rows=db.query(SocialShort).order_by(SocialShort.created_at.desc()).limit(30).all()
    jobs=[{'day':r.day[:10],'slot':r.day.split(':')[-1],'state':r.state,'attempts':r.attempts,
        'post_id':r.post_id,'error':r.error,'title':json.loads(r.payload)['metadata']['youtube']['title'],
        'updated_at':pipeline.stamp(r.updated_at),'checked_at':pipeline.stamp(r.checked_at),'due_at':pipeline.stamp(r.due_at),
        'published_url':r.external_link,'channel_id':r.channel_id,'caption_repairable':caption_repairable(r)} for r in rows]
    return {'settings':config,'worker':pipeline.read(db,'youtube-worker'),'jobs':jobs,'needs_attention':sum(r.state in ('failed','needs_review','delivery_failed','blocked') for r in rows),
            'last_published':next((j for j in jobs if j['state'] in ('published','confirmed_published')),None)}
