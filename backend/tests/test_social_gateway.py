import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
import subprocess
import sys
import json
from pathlib import Path
import pytest
import requests
from requests.structures import CaseInsensitiveDict
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.services import social_gateway as gateway
from app.routers.admin_dashboard import _require_admin
from test_social_slots import setup as slots_setup


class Upstream:
    def __init__(self,body=b'{"state":"accepted"}',status=202,headers=None):
        self.body=body;self.status_code=status;self.closed=False
        self.headers=CaseInsensitiveDict(headers or {'Content-Type':'application/json'})
    def iter_content(self,chunk_size):
        for i in range(0,len(self.body),chunk_size):yield self.body[i:i+chunk_size]
    def close(self):self.closed=True


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv('SOCIAL_EXECUTION_MODE','external')
    monkeypatch.setenv('SOCIAL_WORKER_URL','https://publisher.example')
    monkeypatch.setenv('SOCIAL_RELAY_SECRET','relay-'+'x'*32)
    app=FastAPI();gateway.install_social_routes(app)
    calls=[]
    def send(method,url,**kwargs):
        response=Upstream();calls.append((method,url,kwargs,response));return response
    monkeypatch.setattr(gateway.requests,'request',send)
    return TestClient(app),app,calls


def test_external_gateway_imports_no_renderer_in_a_fresh_web_process():
    code="""from fastapi import FastAPI
from app.services.social_gateway import install_social_routes
import sys
app=FastAPI();install_social_routes(app)
assert app.state.social_execution_mode=='external'
assert 'app.routers.social_slots' not in sys.modules
assert 'social.reel' not in sys.modules
assert 'social.local_speech' not in sys.modules
"""
    env={**os.environ,'SOCIAL_EXECUTION_MODE':'external','SOCIAL_WORKER_URL':'https://publisher.example','SOCIAL_RELAY_SECRET':'x'*40}
    result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_admin_authentication_happens_before_relay_and_browser_credentials_never_leave_web(setup):
    client,app,calls=setup
    assert client.post('/api/admin/social/youtube/trigger',headers={'X-Social-Relay':'relay-'+'x'*32}).status_code==401
    assert calls==[]
    app.dependency_overrides[_require_admin]=lambda:'verified-web-admin'
    response=client.post('/api/admin/social/youtube/jobs/2026-10-15:s08/repair-caption',
        json={'expected_updated_at':'version'},headers={'Authorization':'Bearer browser-admin-secret','Cookie':'jee_session=private','X-Social-Relay':'caller-value'})
    assert response.status_code==202
    method,url,kwargs,upstream=calls[0]
    assert method=='POST' and url.endswith('/2026-10-15:s08/repair-caption')
    assert json.loads(kwargs['data'])=={'expected_updated_at':'version'}
    assert kwargs['headers']['X-Social-Relay']=='relay-'+'x'*32
    assert not any(key.lower() in ('authorization','cookie') for key in kwargs['headers'])
    assert kwargs['allow_redirects'] is False and upstream.closed


def test_old_cron_url_forwards_once_and_keeps_trigger_authorization(setup):
    client,_,calls=setup
    response=client.post('/api/social/test-reel?require_voice=true',headers={'Authorization':'Bearer cron-secret'})
    assert response.status_code==202 and len(calls)==1
    assert calls[0][1]=='https://publisher.example/api/social/test-reel?require_voice=true'
    assert calls[0][2]['headers']['Authorization']=='Bearer cron-secret'


def test_meta_signature_and_body_are_preserved(setup):
    client,_,calls=setup
    body=b'{"entry": []}'
    client.post('/api/social/comments/webhook',content=body,headers={'X-Hub-Signature-256':'sha256=signed','Content-Type':'application/json'})
    assert calls[0][2]['data']==body
    assert calls[0][2]['headers']['x-hub-signature-256']=='sha256=signed'


def test_media_stream_keeps_byte_ranges_and_does_not_buffer_a_whole_video(setup,monkeypatch):
    client,_,calls=setup
    upstream=Upstream(b'abc',206,{'Content-Type':'video/mp4','Content-Range':'bytes 1-3/20','Content-Length':'3','Accept-Ranges':'bytes','Cache-Control':'public, max-age=86400'})
    captured=[]
    def send(*args,**kwargs):captured.append(kwargs);return upstream
    monkeypatch.setattr(gateway.requests,'request',send)
    response=client.get('/api/social/assets/'+'a'*32+'.mp4',headers={'Range':'bytes=1-3'})
    assert response.status_code==206 and response.content==b'abc'
    assert response.headers['content-range']=='bytes 1-3/20'
    assert response.headers['cache-control']=='public, max-age=86400'
    assert captured[0]['headers']['range']=='bytes=1-3'
    assert captured[0]['stream'] is True and upstream.closed


def test_ambiguous_remote_failure_is_not_retried_or_run_locally(setup,monkeypatch):
    client,_,calls=setup
    attempts=[]
    def fail(*args,**kwargs):attempts.append(1);raise requests.Timeout('secret backend URL')
    monkeypatch.setattr(gateway.requests,'request',fail)
    response=client.post('/api/social/trigger')
    assert response.status_code==502 and attempts==[1]
    assert 'secret backend URL' not in response.text and 'before retrying' in response.text


def test_oversize_requests_are_rejected_before_forwarding(setup):
    client,_,calls=setup
    assert client.post('/api/social/comments/webhook',content=b'x'*(gateway.MAX_REQUEST_BYTES+1)).status_code==413
    assert calls==[]


@pytest.mark.parametrize('origin',['http://publisher.example','https://user:secret@publisher.example','https://publisher.example/path','https://publisher.example?secret=1',''])
def test_external_configuration_never_silently_falls_back_to_rendering(setup,monkeypatch,origin):
    monkeypatch.setenv('SOCIAL_WORKER_URL',origin)
    with pytest.raises(RuntimeError):gateway.install_social_routes(FastAPI())


def test_worker_exposes_no_student_or_teacher_endpoints_and_requires_relay_for_admin(monkeypatch):
    from app.social_app import create_app
    monkeypatch.setenv('SOCIAL_RELAY_SECRET','x'*40)
    monkeypatch.setenv('SOCIAL_TRIGGER_SECRET','t'*40)
    app=create_app();client=TestClient(app)
    assert client.get('/health').json()['service']=='publisher'
    for path in ('/api/me','/api/auth/session','/api/admin/login','/teacher','/docs','/openapi.json'):
        assert client.get(path).status_code==404
    assert client.get('/api/admin/social',headers={'Authorization':'Bearer arbitrary-admin-token'}).status_code==401
    assert client.post('/api/social/trigger').status_code==401
    assert client.post('/api/social/comments/webhook',content=b'{}').status_code==503
    monkeypatch.setenv('SOCIAL_RELAY_SECRET','short')
    with pytest.raises(RuntimeError):create_app()


def test_existing_cron_and_media_work_end_to_end_through_separate_worker(slots_setup,monkeypatch):
    from app.social_app import create_app
    from app.routers import social_slots
    from app.models.social_job import SocialSlot
    _,factory,_,published=slots_setup
    monkeypatch.setenv('SOCIAL_RELAY_SECRET','relay-'+'x'*32)
    monkeypatch.setenv('SOCIAL_WORKER_URL','https://publisher.example')
    monkeypatch.setenv('SOCIAL_MEDIA_ORIGIN','https://publisher.example')
    monkeypatch.setenv('SOCIAL_EXECUTION_MODE','external')
    worker=TestClient(create_app())
    main=FastAPI();gateway.install_social_routes(main);web=TestClient(main)
    forwarded=[]
    def transport(method,url,**kwargs):
        forwarded.append(url)
        result=worker.request(method,url.removeprefix('https://publisher.example'),headers=kwargs['headers'],content=kwargs['data'])
        return Upstream(result.content,result.status_code,result.headers)
    monkeypatch.setattr(gateway.requests,'request',transport)
    def fetch(url,**kwargs):
        assert url.startswith('https://publisher.example/api/social/assets/')
        result=worker.get(url.removeprefix('https://publisher.example'))
        assert result.status_code==200
        return result.content
    monkeypatch.setattr(social_slots.worker,'request',fetch)
    headers={'Authorization':'Bearer '+'x'*32}
    response=web.post('/api/social/trigger',headers=headers)
    assert response.status_code==202,response.text
    assert len(published)==1
    with factory() as db:assert db.get(SocialSlot,'2026-10-06:s00').state=='scheduled'
    assert all(a['image']['url'].startswith('https://publisher.example/') for a in published[0]['assets'])
    assert web.post('/api/social/trigger',headers=headers).status_code==202
    assert len(published)==1  # Existing slot checkpoint prevents another publication.
    # Old public URLs continue to serve the same database media during migration.
    url=published[0]['assets'][0]['image']['url'].removeprefix('https://publisher.example')
    assert web.get(url).content==worker.get(url).content
    assert all(url.startswith('https://publisher.example/api/social/') for url in forwarded)


def test_worker_startup_initializes_only_social_tables(monkeypatch):
    from app.social_app import create_app
    from app import database
    monkeypatch.setenv('SOCIAL_RELAY_SECRET','x'*40)
    app=create_app();calls=[]
    monkeypatch.setattr(database.Base.metadata,'create_all',lambda **kwargs:calls.append(kwargs))
    app.router.on_startup[0]()
    names=[table.name for table in calls[0]['tables']]
    assert 'social_shorts' in names and 'social_speech' in names
    assert all(name.startswith('social_') for name in names)


def test_worker_redirects_stay_on_main_origin_for_admin_auth(setup,monkeypatch):
    client,app,_=setup
    app.dependency_overrides[_require_admin]=lambda:'verified-web-admin'
    monkeypatch.setattr(gateway.requests,'request',lambda *a,**kw:Upstream(b'',307,{'Location':'https://publisher.example/api/admin/social'}))
    response=client.get('/api/admin/social/',follow_redirects=False)
    assert response.status_code==307 and response.headers['location']=='/api/admin/social'


def test_publisher_import_needs_no_student_pdf_or_omr_libraries():
    code="""import sys
from importlib.abc import MetaPathFinder
class BlockStudentLibraries(MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('numpy','cv2','reportlab','pypdfium2','argon2','email_validator'):
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0,BlockStudentLibraries())
from app.social_app import create_app
app=create_app()
assert not any(name in sys.modules for name in ('numpy','cv2','reportlab','pypdfium2','argon2','email_validator'))
assert 'app.predictor_bootstrap' not in sys.modules
assert 'app.routers.teacher_papers' not in sys.modules
assert 'app.main' not in sys.modules
"""
    env={**os.environ,'SOCIAL_RELAY_SECRET':'x'*40}
    result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
