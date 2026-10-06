"""Signed-webhook inbox and bounded Instagram public replies, independent of Buffer."""
import json
import os
import re
import uuid
from datetime import datetime, timedelta
import urllib.request
import urllib.error
from urllib.parse import urlencode
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.social_comment import SocialComment, SocialCommentDispatch, SocialLesson
from app.services import social_budget as budget
from social import worker, comment_copy

IDENTITY = re.compile(r'^[0-9]{1,64}$')
MARKER = re.compile(r'JeeEdge daily (\d{4}-\d{2}-\d{2}) / (s\d{2})')
# Deliberately local operating budgets, not claims about Meta account quotas.
LIMITS = {'instagram':[(3600,100,0),(86400,500,0)],
          'comment_reply':[(3600,6,0),(86400,30,0)]}
budget.LIMITS.update(LIMITS)


def enabled():
    return (os.getenv('SOCIAL_COMMENTS_ENABLED','').lower()=='true'
            and os.getenv('SOCIAL_PAUSED','').lower()!='true')


def missing_config():
    return [k for k in ('IG_ACCESS_TOKEN','IG_ACCOUNT_ID','IG_APP_SECRET',
                       'IG_WEBHOOK_VERIFY_TOKEN','IG_GRAPH_VERSION','GROQ_API_KEY') if not os.getenv(k)]


def graph(path, fields=None, message=None):
    if not re.fullmatch(r'[0-9]{1,64}(?:/replies)?',path):
        raise worker.ServiceError('Invalid Instagram resource.')
    version=os.getenv('IG_GRAPH_VERSION','')
    if not re.fullmatch(r'v\d{2}\.0',version):
        raise worker.ServiceError('Configure IG_GRAPH_VERSION from your Meta app dashboard.')
    budget.reserve('instagram')
    url=f'https://graph.instagram.com/{version}/{path}'
    headers={'Authorization':'Bearer '+os.environ['IG_ACCESS_TOKEN']}
    if fields:
        url += '?' + urlencode(fields)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    headers['Content-Type']='application/json'
    request=urllib.request.Request(url,headers=headers,method='POST' if message is not None else 'GET',
        data=json.dumps({'message':message}).encode() if message is not None else None)
    try:
        # No redirects or automatic retries, especially after an uncertain POST.
        with urllib.request.build_opener(NoRedirect).open(request,timeout=20) as response:
            raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:
                raise worker.ServiceError('Instagram response exceeded the size limit.')
            result=json.loads(raw)
        if not isinstance(result,dict) or result.get('error'):
            raise worker.ServiceError('Instagram returned an API error; inspect app permissions and quotas.')
        return result
    except urllib.error.HTTPError as exc:
        if exc.code==429:
            retry=exc.headers.get('Retry-After','3600')
            budget.cache('cooldown:instagram',True,min(86400,max(60,int(retry) if retry.isdigit() else 3600)))
        raise worker.ServiceError(f'Instagram HTTP {exc.code}; check token, permissions or quota.') from None
    except (urllib.error.URLError,TimeoutError,ValueError):
        raise worker.ServiceError('Instagram request failed; response details withheld.') from None


def save_lesson(db, slot, content):
    # Called in the publication transaction, before Buffer submission.
    old=db.get(SocialLesson,slot)
    encoded=json.dumps(content,ensure_ascii=False)
    if old is None:
        db.add(SocialLesson(slot=slot,content=encoded))
    elif old.content != encoded:
        raise worker.ServiceError('Saved lesson differs from generated lesson; review before publication.')


def ingest(payload):
    if payload.get('object')!='instagram':
        return 0
    count=0; now=datetime.utcnow(); account=os.getenv('IG_ACCOUNT_ID','')
    for entry in payload.get('entry',[]):
        if str(entry.get('id',''))!=account:
            continue
        for change in entry.get('changes',[]):
            if change.get('field')!='comments':
                continue
            value=change.get('value',{})
            cid=str(value.get('id',''));mid=str((value.get('media') or {}).get('id',''))
            author=str((value.get('from') or {}).get('id',''))
            parent=str(value.get('parent_id','')) or None
            if not all(IDENTITY.fullmatch(v) for v in (cid,mid,author)) or author==account:
                continue
            text=value.get('text','')
            if not isinstance(text,str) or not text.strip():
                continue
            if parent and not IDENTITY.fullmatch(parent):
                continue
            with SessionLocal() as db:
                if db.get(SocialComment,cid):
                    continue
                row=SocialComment(id=cid,media_id=mid,author_id=author,parent_id=parent,
                    text=text[:2000],state='pending',attempts=0,created_at=now,updated_at=now,next_attempt=now)
                if len(text)>1500:
                    row.state='review';row.reason='Long comment requires review.'
                db.add(row)
                try:
                    db.commit();count+=1
                except IntegrityError:
                    db.rollback() # duplicate delivery raced with another worker
    return count


def dispatch_lock(db):
    if db.get(SocialCommentDispatch,1) is None:
        db.add(SocialCommentDispatch(id=1))
        try: db.commit()
        except IntegrityError: db.rollback()
    return db.query(SocialCommentDispatch).filter_by(id=1).with_for_update().one()


def finish(cid, owner, state, reason, **values):
    with SessionLocal() as db:
        db.query(SocialComment).filter_by(id=cid,owner=owner).filter(
            SocialComment.state.in_(['processing','submitting'])).update(
                {'state':state,'reason':reason,'updated_at':datetime.utcnow(),**values},synchronize_session=False)
        db.commit()


def claim(owner):
    now=datetime.utcnow()
    with SessionLocal() as db:
        lock=dispatch_lock(db)
        if lock.owner!=owner or lock.expires_at<=now:
            return None
        # A stopped worker may have made a successful POST: never blindly replay it.
        db.query(SocialComment).filter(SocialComment.state=='submitting',
            SocialComment.updated_at<now-timedelta(minutes=10)).update(
                {'state':'needs_review','reason':'Uncertain reply delivery; inspect Instagram before taking action.'},synchronize_session=False)
        db.query(SocialComment).filter(SocialComment.state=='processing',
            SocialComment.attempts>=3,SocialComment.updated_at<now-timedelta(minutes=10)).update(
                {'state':'review','reason':'Repeated interrupted processing; inspect before retrying.'},synchronize_session=False)
        db.query(SocialComment).filter(SocialComment.state=='processing',
            SocialComment.updated_at<now-timedelta(minutes=10)).update(
                {'state':'pending'},synchronize_session=False)
        row=db.query(SocialComment).filter(SocialComment.state=='pending',
            SocialComment.next_attempt<=now,SocialComment.attempts<3).order_by(SocialComment.created_at).first()
        if row is None:
            db.commit();return None
        row.state='processing';row.owner=owner;row.updated_at=now;row.attempts+=1
        result={k:getattr(row,k) for k in ('id','media_id','author_id','parent_id','text','attempts','created_at','reply')}
        db.commit();return result


def process(row, owner):
    cid=row['id']; account=os.environ['IG_ACCOUNT_ID']; submitting=False
    try:
        if datetime.utcnow()-row['created_at']>timedelta(days=2):
            finish(cid,owner,'review','Comment waited more than two days.');return
        current=graph(cid,{'fields':'id,text,from,media,parent_id,hidden'})
        media_id=str((current.get('media') or {}).get('id',''))
        author_id=str((current.get('from') or {}).get('id',''))
        parent=str(current.get('parent_id','')) or None
        if (str(current.get('id'))!=cid or media_id!=row['media_id'] or
            author_id!=row['author_id'] or author_id==account or current.get('hidden')):
            finish(cid,owner,'skipped','Comment identity changed, is hidden, or belongs to us.');return
        if parent!=row['parent_id']:
            finish(cid,owner,'review','Comment thread identity differs from the webhook.');return
        text=current.get('text','')
        if not isinstance(text,str) or not 1<=len(text.strip())<=1500:
            finish(cid,owner,'review','Comment length requires review.');return
        media=graph(media_id,{'fields':'id,caption,owner'})
        if str((media.get('owner') or {}).get('id',''))!=account:
            finish(cid,owner,'skipped','Media does not belong to the configured account.');return
        match=MARKER.search(media.get('caption',''))
        with SessionLocal() as db:
            snapshot=db.get(SocialLesson,match[1]+':'+match[2]) if match else None
            lesson=json.loads(snapshot.content) if snapshot else None
        if lesson is None:
            finish(cid,owner,'review','No saved lesson for this post; do not guess its content.');return
        root=parent or cid
        thread=[]
        if parent:
            original=graph(parent,{'fields':'text'})
            thread.append({'role':'commenter','text':str(original.get('text',''))[:240]})
        replies=graph(root+'/replies',{'fields':'id,text,from','limit':20})
        if replies.get('paging',{}).get('next'):
            finish(cid,owner,'review','Thread exceeds automatic context limit.');return
        for reply in replies.get('data',[]):
            if str((reply.get('from') or {}).get('id',''))==account:
                finish(cid,owner,'skipped','JeeEdge already replied in this thread.');return
            thread.append({'role':'commenter','text':str(reply.get('text',''))[:240]})
        if len(thread)>10:
            finish(cid,owner,'review','Thread exceeds automatic context limit.');return
        # Obvious instruction attacks/links never enter generation.
        if re.search(r'https?://|www\.|ignore.{0,30}(instructions|prompt)|system prompt|api[_ ]?key',text,re.I):
            finish(cid,owner,'skipped','Link, promotion or instruction request.');return
        def save_draft(answer):
            with SessionLocal() as db:
                db.query(SocialComment).filter_by(id=cid,owner=owner,state='processing').update(
                    {'reply':answer,'text':text},synchronize_session=False)
                db.commit()
        with budget.tracked():
            action,answer,reason=comment_copy.decide(lesson,text,thread,
                candidate=row['reply'] if row['text']==text else None,save_draft=save_draft)
        if action!='reply':
            finish(cid,owner,'review' if action=='review' else 'skipped',reason,reply=answer,text=text);return
        # Re-read before committing a public reply; do not answer edited comments.
        latest=graph(cid,{'fields':'text,hidden'})
        if latest.get('text')!=text or latest.get('hidden'):
            finish(cid,owner,'review','Comment changed during drafting.');return
        # Reserve before acquiring the send fence; includes ambiguous sends.
        budget.reserve('comment_reply')
        with SessionLocal() as db:
            lock=dispatch_lock(db)
            job=db.query(SocialComment).filter_by(id=cid).with_for_update().one()
            now=datetime.utcnow()
            if not enabled() or lock.owner!=owner or lock.expires_at<=now or job.owner!=owner or job.state!='processing':
                return
            recent=db.query(SocialComment).filter(SocialComment.author_id==author_id,
                SocialComment.state.in_(['replied','submitting','needs_review']))
            if recent.filter(SocialComment.media_id==media_id).count() or recent.filter(
                    SocialComment.updated_at>now-timedelta(days=1)).count()>=3:
                job.state='skipped';job.reason='Per-student reply limit reached.';job.updated_at=now;db.commit();return
            job.reply=answer;job.text=text;job.state='submitting';job.updated_at=now
            db.commit() # durable at-most-once fence before POST
        submitting=True
        result=graph(root+'/replies',message=answer)
        rid=str(result.get('id',''))
        if not IDENTITY.fullmatch(rid):
            raise worker.ServiceError('Instagram did not confirm a reply ID.')
        finish(cid,owner,'replied','Reply confirmed by Instagram.',reply_id=rid,sent_at=datetime.utcnow())
    except Exception as exc:
        # No remote response bodies, tokens, user content or model prompts in errors.
        reason=str(exc)[:280] if isinstance(exc,worker.ServiceError) else 'Comment processing failed; inspect configuration or review.'
        state='needs_review' if submitting else ('pending' if row['attempts']<3 else 'review')
        finish(cid,owner,state,reason,next_attempt=datetime.utcnow()+timedelta(minutes=30))


def drain():
    if not enabled() or missing_config():
        return
    owner=uuid.uuid4().hex;now=datetime.utcnow()
    with SessionLocal() as db:
        lock=dispatch_lock(db)
        if lock.owner and lock.expires_at and lock.expires_at>now:
            return
        lock.owner=owner;lock.expires_at=now+timedelta(minutes=10);db.commit()
    try:
        for _ in range(2):
            if not enabled():break
            row=claim(owner)
            if not row:break
            process(row,owner)
        # Keep the deduplication IDs, remove comment/reply bodies after 30 days.
        with SessionLocal() as db:
            db.query(SocialComment).filter(SocialComment.created_at<now-timedelta(days=30)).update(
                {'text':'','reply':None},synchronize_session=False)
            db.commit()
    finally:
        with SessionLocal() as db:
            db.query(SocialCommentDispatch).filter_by(id=1,owner=owner).update(
                {'owner':None,'expires_at':None},synchronize_session=False)
            db.commit()


def drain_safe():
    try:
        drain()
    except Exception:
        # Comment outages must not prevent the existing publication background task.
        print('Comment worker unavailable; durable inbox retained for the next trigger.',flush=True)
