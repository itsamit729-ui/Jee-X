import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
import json
import pytest
from app.models.social_job import SocialShort
from app.services import social_shorts as shorts, social_pipeline as pipeline
from social import advanced, editorial, worker
from test_social_shorts import setup, source, uploader


def test_same_equilibrium_lesson_cannot_send_forbidden_description_characters():
    lesson=next(c for c in advanced.BANK if c['topic']=='Gas equilibrium dissociation')
    caption=editorial.authored({**lesson,'story_format':'mistake_check'})['caption']
    assert '<=>' in caption  # Reproduce the actual authored source of this lesson.
    original={'text':caption,'metadata':{'youtube':{'title':'What if x < 2?'}}}
    fixed=shorts.validated_payload(original)
    assert '<' not in fixed['text'] and '>' not in fixed['text']
    assert 'A(g) ⇌ 2B(g)' in fixed['text']
    assert 'x ＜ 2' in fixed['metadata']['youtube']['title']
    assert '<=>' in original['text']  # Instagram and authored lesson remain unchanged.
    assert fixed==shorts.validated_payload(fixed)


def test_youtube_description_limit_is_utf8_bytes_and_math_operators_keep_their_meaning():
    assert shorts.youtube_text('a <= b; c >= d; x < 2; x > 0; A -> B')=='a ≤ b; c ≥ d; x ＜ 2; x ＞ 0; A → B'
    assert shorts.youtube_text('A &lt;=&gt; B\x00')=='A ⇌ B'
    payload={'text':'a'*5000,'metadata':{'youtube':{'title':'Question'}}}
    assert len(shorts.validated_payload(payload)['text'].encode('utf-8'))==5000
    payload['text']='≤'*1667  # 1,667 characters, but 5,001 UTF-8 bytes.
    with pytest.raises(worker.ServiceError,match='5,000 UTF-8 bytes'):shorts.validated_payload(payload)


def test_previously_prepared_checkpoints_are_sanitized_before_first_submission(setup,monkeypatch):
    _,factory,_=source(setup,monkeypatch)
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');payload=json.loads(row.payload)
        payload['text']='A <=> B\n\n'+shorts.marker(row.day);row.payload=json.dumps(payload);db.commit()
    calls=uploader(monkeypatch,factory)
    shorts.tick()
    assert len(calls)==1 and 'A ⇌ B' in calls[0]['text'] and '<' not in calls[0]['text']


def test_oversized_utf8_caption_stops_before_any_post_submission(setup,monkeypatch):
    _,factory,_=source(setup,monkeypatch)
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');payload=json.loads(row.payload)
        payload['text']='≤'*1667;row.payload=json.dumps(payload);db.commit()
    calls=uploader(monkeypatch,factory)
    shorts.tick()
    assert calls==[]
    with factory() as db:
        row=db.get(SocialShort,'2026-10-06:s02');assert row.state=='failed' and not row.post_id
        assert '5,000 UTF-8 bytes' in row.error


def failed_post(setup,monkeypatch):
    client,factory,instagram=source(setup,monkeypatch)
    day='2026-10-06:s02'
    text='For A(g) <=> 2B(g), find the dissociation fraction.\n\n'+shorts.marker(day)
    with factory() as db:
        row=db.get(SocialShort,day);row.state='delivery_failed';row.post_id='yt-failed'
        payload=json.loads(row.payload);payload['text']=text;row.payload=json.dumps(payload);db.commit()
        updated=pipeline.stamp(row.updated_at)
        assert shorts.report(db)['jobs'][0]['caption_repairable'] is True
    from app.routers import social_slots as social
    client.app.include_router(social.admin_router)
    url=f'/api/admin/social/youtube/jobs/{day}/repair-caption'
    assert client.post(url,json={'expected_updated_at':updated}).status_code!=202
    client.app.dependency_overrides[social._require_admin]=lambda:'verified-admin'
    return client,factory,instagram,day,text,updated,url


@pytest.mark.parametrize('legacy_rejection',[False,True])
def test_admin_repairs_and_reschedules_the_same_failed_post_without_creating_a_duplicate(setup,monkeypatch,legacy_rejection):
    c,factory,instagram,day,text,updated,url=failed_post(setup,monkeypatch)
    monkeypatch.setattr(worker,'post',lambda identity:{'id':identity,'status':'error','text':text})
    if legacy_rejection:
        with factory() as db:
            row=db.get(SocialShort,day);row.state='needs_review'
            row.error='Buffer did not confirm the caption repair. Check the existing post. Invalid post: YouTube posts require a video., YouTube posts require a title., YouTube posts require a category.'
            db.commit()
    edits=[]
    def edit(query,variables):
        assert 'editPost' in query and 'createPost' not in query
        data=variables['input'];edits.append(data)
        assert data['id']=='yt-failed' and data['mode']=='customScheduled'
        assert len(data['assets'])==1 and data['assets'][0]['video']['url'].endswith('.mp4')
        youtube=data['metadata']['youtube']
        assert youtube['title'] and youtube['categoryId']=='27'
        assert youtube['privacy']=='public' and youtube['madeForKids'] is False
        assert '⇌' in data['text'] and '<' not in data['text'] and '>' not in data['text']
        return {'editPost':{'post':{'id':data['id'],'text':data['text'],'status':'scheduled'}}}
    monkeypatch.setattr(worker,'buffer',edit)
    r=c.post(url,json={'expected_updated_at':updated})
    assert r.status_code==202,r.text
    assert r.json()['creates_new_post'] is False
    with factory() as db:
        row=db.get(SocialShort,day);assert row.state=='scheduled' and row.post_id=='yt-failed'
        assert '⇌' in json.loads(row.payload)['text']
    assert len(edits)==1 and len(instagram)==1
    assert c.post(url,json={'expected_updated_at':updated}).status_code==409
    assert len(edits)==1


@pytest.mark.parametrize('status',['sent','scheduled','sending'])
def test_repair_rechecks_live_status_and_never_retries_an_already_live_or_queued_post(setup,monkeypatch,status):
    c,factory,_,day,text,updated,url=failed_post(setup,monkeypatch)
    monkeypatch.setattr(worker,'post',lambda identity:{'id':identity,'status':status,'text':text})
    monkeypatch.setattr(worker,'buffer',lambda *args:pytest.fail('Already sent or scheduled posts must never be edited or rescheduled'))
    assert c.post(url,json={'expected_updated_at':updated}).status_code==202
    with factory() as db:assert db.get(SocialShort,day).state==('published' if status=='sent' else 'scheduled')


def test_repair_timeout_is_quarantined_without_automatic_recreation(setup,monkeypatch):
    c,factory,_,day,text,updated,url=failed_post(setup,monkeypatch)
    monkeypatch.setattr(worker,'post',lambda identity:{'id':identity,'status':'error','text':text})
    calls=[]
    def timeout(*args):calls.append(1);raise worker.ServiceError('Network request failed; outcome unknown.')
    monkeypatch.setattr(worker,'buffer',timeout)
    assert c.post(url,json={'expected_updated_at':updated}).status_code==202
    with factory() as db:
        row=db.get(SocialShort,day);assert row.state=='needs_review' and row.post_id=='yt-failed'
        assert not shorts.caption_repairable(row)
        assert '<=>' in json.loads(row.payload)['text']  # No false confirmation after timeout.
    assert c.post(url,json={'expected_updated_at':updated}).status_code==409
    assert calls==[1]


def test_repair_does_not_blame_or_retry_a_caption_already_fixed_in_buffer(setup,monkeypatch):
    c,factory,_,day,text,updated,url=failed_post(setup,monkeypatch)
    monkeypatch.setattr(worker,'post',lambda identity:{'id':identity,'status':'error','text':shorts.youtube_text(text)})
    monkeypatch.setattr(worker,'buffer',lambda *args:pytest.fail('No metadata defect, no retry'))
    assert c.post(url,json={'expected_updated_at':updated}).status_code==202
    with factory() as db:
        report=shorts.report(db)['jobs'][0]
        assert report['state']=='delivery_failed' and report['caption_repairable'] is False
        assert 'different fix' in report['error']


def test_failed_post_with_a_youtube_link_is_not_rescheduled(setup,monkeypatch):
    c,factory,_,day,text,updated,url=failed_post(setup,monkeypatch)
    link='https://www.youtube.com/shorts/AbCdEf123_-'
    monkeypatch.setattr(worker,'post',lambda identity:{'id':identity,'status':'error','text':text,'externalLink':link})
    monkeypatch.setattr(worker,'buffer',lambda *args:pytest.fail('A possibly published video must not be retried'))
    assert c.post(url,json={'expected_updated_at':updated}).status_code==202
    with factory() as db:
        row=db.get(SocialShort,day);assert row.state=='needs_review' and row.external_link==link


def test_explicit_buffer_validation_rejection_remains_repairable(setup,monkeypatch):
    c,factory,_,day,text,updated,url=failed_post(setup,monkeypatch)
    monkeypatch.setattr(worker,'post',lambda identity:{'id':identity,'status':'error','text':text})
    monkeypatch.setattr(worker,'buffer',lambda *args:{'editPost':{'message':'Invalid post: YouTube posts require a video.'}})
    assert c.post(url,json={'expected_updated_at':updated}).status_code==202
    with factory() as db:
        row=db.get(SocialShort,day)
        assert row.state=='delivery_failed' and shorts.caption_repairable(row)
        assert '<=>' in json.loads(row.payload)['text']


def test_legacy_rejected_repair_is_available_but_rechecks_live_post(setup,monkeypatch):
    c,factory,_,day,text,updated,url=failed_post(setup,monkeypatch)
    with factory() as db:
        row=db.get(SocialShort,day);row.state='needs_review'
        row.error='Buffer did not confirm the caption repair. Check the existing post. Invalid post: YouTube posts require a video., YouTube posts require a title., YouTube posts require a category.'
        db.commit()
        assert shorts.caption_repairable(row)
    monkeypatch.setattr(worker,'post',lambda identity:{'id':identity,'status':'sent','text':text})
    monkeypatch.setattr(worker,'buffer',lambda *args:pytest.fail('Already published post must never be edited'))
    assert c.post(url,json={'expected_updated_at':updated}).status_code==202
    with factory() as db:assert db.get(SocialShort,day).state=='published'


def test_unavailable_video_stops_repair_before_mutation(setup,monkeypatch):
    c,factory,_,day,text,updated,url=failed_post(setup,monkeypatch)
    monkeypatch.setattr(worker,'post',lambda identity:{'id':identity,'status':'error','text':text})
    monkeypatch.setattr(worker,'request',lambda *args,**kwargs:b'not a video')
    monkeypatch.setattr(worker,'buffer',lambda *args:pytest.fail('Cannot reschedule a missing video'))
    assert c.post(url,json={'expected_updated_at':updated}).status_code==202
    with factory() as db:
        row=db.get(SocialShort,day)
        assert row.state=='delivery_failed' and 'did not return an MP4' in row.error
