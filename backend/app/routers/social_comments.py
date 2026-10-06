"""Meta webhook handshake/signature verification; protected operational inbox."""
import hashlib
import hmac
import json
import os
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from app.database import SessionLocal
from app.models.social_comment import SocialComment
from app.services import instagram_comments as comments
from app.routers.social_slots import authorize

router=APIRouter(prefix='/api/social/comments',tags=['social-comments'])


@router.get('/webhook',response_class=PlainTextResponse)
def verify(request: Request):
    token=os.getenv('IG_WEBHOOK_VERIFY_TOKEN','')
    query=request.query_params
    if (len(token)<32 or query.get('hub.mode')!='subscribe' or not hmac.compare_digest(
            query.get('hub.verify_token','').encode(),token.encode())):
        raise HTTPException(403,'Invalid webhook verification')
    return query.get('hub.challenge','')


@router.post('/webhook')
async def receive(request: Request,tasks: BackgroundTasks):
    secret=os.getenv('IG_APP_SECRET','')
    if not secret or not os.getenv('IG_ACCOUNT_ID'):
        raise HTTPException(503,'Instagram webhook is not configured')
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>256*1024:
            raise HTTPException(413,'Webhook body too large')
    expected='sha256='+hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get('X-Hub-Signature-256','').encode(),expected.encode()):
        raise HTTPException(403,'Invalid webhook signature')
    try:
        payload=json.loads(body)
        if not isinstance(payload,dict) or not isinstance(payload.get('entry',[]),list):
            raise ValueError()
        changes=0
        for entry in payload.get('entry',[]):
            if not isinstance(entry,dict) or not isinstance(entry.get('changes',[]),list):raise ValueError()
            for change in entry.get('changes',[]):
                changes+=1
                if not isinstance(change,dict) or not isinstance(change.get('value',{}),dict):raise ValueError()
                value=change.get('value',{})
                if any(not isinstance(value.get(key,{}),dict) for key in ('media','from')):raise ValueError()
        if changes>100:raise ValueError()
    except (ValueError,TypeError):
        raise HTTPException(400,'Invalid webhook payload') from None
    count=comments.ingest(payload)
    tasks.add_task(comments.drain_safe)
    return {'accepted':count}


@router.post('/process',status_code=202,dependencies=[Depends(authorize)])
def process(tasks: BackgroundTasks):
    if not comments.enabled():raise HTTPException(503,'Comment automation is disabled or paused')
    missing=comments.missing_config()
    if missing:raise HTTPException(503,{'missing_configuration':missing})
    tasks.add_task(comments.drain_safe)
    return {'state':'accepted'}


@router.get('/status',dependencies=[Depends(authorize)])
def status():
    with SessionLocal() as db:
        counts=dict(db.query(SocialComment.state,func.count()).group_by(SocialComment.state).all())
        # Separate inbox endpoint provides state filtering and cursor pagination.
        rows=db.query(SocialComment).order_by(SocialComment.updated_at.desc()).limit(100).all()
        return {'enabled':comments.enabled(),'missing_configuration':comments.missing_config(),
                'reply_limits':{'rolling_hour':6,'rolling_day':30,'per_author_day':3,'per_author_post':1},
                'counts':counts,'comments':[serialize(r) for r in rows]}


def serialize(row):
    return {k:getattr(row,k) for k in ('id','media_id','parent_id','state','text','reply','reply_id',
                                     'reason','attempts','created_at','updated_at','sent_at')}


@router.get('/inbox',dependencies=[Depends(authorize)])
def inbox(state: str='review', before: str=''):
    if state not in ('review','needs_review','pending','replied','skipped'):
        raise HTTPException(400,'Invalid inbox state')
    with SessionLocal() as db:
        query=db.query(SocialComment).filter_by(state=state)
        if before:query=query.filter(SocialComment.id<before)
        rows=query.order_by(SocialComment.id.desc()).limit(50).all()
        return {'comments':[serialize(r) for r in rows],'next_before':rows[-1].id if len(rows)==50 else None}


@router.post('/{comment_id}/dismiss',dependencies=[Depends(authorize)])
def dismiss(comment_id: str):
    with SessionLocal() as db:
        row=db.query(SocialComment).filter_by(id=comment_id).with_for_update().first()
        if row is None:raise HTTPException(404,'Comment not found')
        if row.state not in ('review','needs_review','pending'):
            raise HTTPException(409,'Cannot dismiss an active or completed reply')
        row.state='skipped';row.reason='Dismissed by operator.';db.commit()
    return {'state':'skipped'}
