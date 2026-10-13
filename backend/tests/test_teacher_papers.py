import base64
import io
from types import SimpleNamespace
import pytest
from PIL import Image,ImageDraw
import pypdfium2 as pdfium
from test_roadmap import setup
from test_teaching import classroom,prepare,grant
from app import models as m
from app.auth import utcnow
from app.routers import teacher_papers as p
from app.services import teacher_omr as omr

@pytest.fixture
def studio(classroom,monkeypatch,tmp_path):
    client,factory,active=classroom
    client.app.include_router(p.router)
    monkeypatch.setattr(p,'SessionLocal',factory)
    monkeypatch.setattr(omr,'WORK',tmp_path)
    room=prepare(classroom);active[0]=3
    return client,factory,active,room

def create(client,ids=[100,101]):
    r=client.post('/api/teacher/papers',json={'title':'Class paper','question_ids':ids})
    assert r.status_code==201,r.text
    return r.json()

def own_question(client):
    r=client.post('/api/teacher/questions/private',json={'subtopic_id':1,'stem':'What is 2 + 2?','options':['4','3','2','1'],'correct':'A'})
    assert r.status_code==201,r.text
    return r.json()['question_id']

def finish(client,paper):
    r=client.post(f"/api/teacher/papers/{paper['id']}/finalize",json={'version':paper['version']})
    assert r.status_code==200,r.text
    return r.json()

def test_draft_versions_ownership_and_private_bank(studio):
    c,db,active,room=studio
    qid=own_question(c);paper=create(c,[qid,100]);pid=paper['id']
    assert qid in [q['question_id'] for q in c.get('/api/teacher/questions?q=2%20%2B%202').json()['questions']]
    body={'title':'Edited','question_ids':[100,qid],'version':1}
    assert c.put(f'/api/teacher/papers/{pid}',json=body).status_code==200
    assert c.put(f'/api/teacher/papers/{pid}',json=body).status_code==409
    paper=c.get(f'/api/teacher/papers/{pid}').json();finish(c,paper)
    assert c.put(f'/api/teacher/papers/{pid}',json={**body,'version':2}).status_code==409
    assert c.post(f'/api/teacher/papers/{pid}/duplicate').json()['finalized'] is False
    grant(c,4);active[0]=4
    assert c.get(f'/api/teacher/papers/{pid}').status_code==404
    assert qid not in [q['question_id'] for q in c.get('/api/teacher/questions?q=2%20%2B%202').json()['questions']]
    active[0]=1
    assert c.get('/api/teacher/papers').status_code==403

def test_blueprint_locks_and_shortfall(studio):
    c,db,active,room=studio
    body={'mode':'blueprint','sections':[{'subject':'PHY','count':3,'type':'single_correct'}],'locked_ids':[100]}
    r=c.post('/api/teacher/papers/generate',json=body)
    assert r.status_code==200,r.text
    qs=r.json()['questions'];assert len(qs)==3 and qs[0]['question_id']==100 and all(q['subject']=='PHY' for q in qs)
    body['sections'][0]['count']=100
    assert 'shortfall' in c.post('/api/teacher/papers/generate',json=body).json()['detail']
    assert not c.get('/api/teacher/papers').json()['papers']
    body['sections'][0]['count']=3;body['classroom_ids']=[999]
    assert c.post('/api/teacher/papers/generate',json=body).status_code==404

def test_assignment_uses_finalized_snapshot(studio):
    from datetime import timedelta
    c,factory,active,room=studio
    paper=finish(c,create(c));pid=paper['id']
    with factory() as db:
        db.get(m.Question,100).stem='Bank changed later';db.commit()
    now=utcnow();body={'classroom_ids':[room['id']],'opens_at':now.isoformat()+'Z','due_at':(now+timedelta(hours=1)).isoformat()+'Z','solutions_at':(now+timedelta(hours=1)).isoformat()+'Z'}
    r=c.post(f'/api/teacher/papers/{pid}/assign',json=body);assert r.status_code==200,r.text
    assert c.post(f'/api/teacher/papers/{pid}/assign',json=body).json()['id']==r.json()['id']
    with factory() as db:
        a=db.get(m.TeachingAssignment,r.json()['id']);assert a.questions[0]['stem']=='Question'

def render_sheet(pdf):
    doc=pdfium.PdfDocument(pdf);return doc[0].render(scale=2).to_pil().convert('RGB')

def encode(image):
    buf=io.BytesIO();image.save(buf,format='PNG');return buf.getvalue()

def test_printed_template_blank_marks_multiple_and_rotation(tmp_path):
    sheet=SimpleNamespace(id='a'*32,variant='A',question_order=list(range(200)))
    paper=SimpleNamespace(id=1,title='Sample paper',version=1)
    image=render_sheet(omr.sheet_pdf(paper,sheet,'Sample Student'))
    sid,aligned=omr.detect(encode(image));assert sid==sheet.id
    found,_=omr.bubbles(aligned,200);assert all(r['status']=='blank' for r in found)
    draw=ImageDraw.Draw(image)
    for i,k in [(0,0),(1,1),(2,0),(2,2),(199,3)]:
        x,y=omr.cells(i)[k];draw.ellipse((x*2-7,y*2-7,x*2+7,y*2+7),fill='black')
    sid,aligned=omr.detect(encode(image));found,preview=omr.bubbles(aligned,200)
    assert found[0]['answer']=='A' and found[1]['answer']=='B' and found[2]['status']=='multiple' and found[199]['answer']=='D'
    sid,aligned=omr.detect(encode(image.rotate(180)));again,_=omr.bubbles(aligned,200)
    assert again[0]['answer']=='A' and again[199]['answer']=='D'
    root=tmp_path/'preview';root.mkdir(exist_ok=True)
    (root/'omr.pdf').write_bytes(omr.sheet_pdf(paper,sheet,'Sample Student'))
    image.save(root/'omr.png');(root/'marked.jpg').write_bytes(preview)

def test_scan_review_duplicate_fence_and_wrong_paper(studio):
    c,factory,active,room=studio
    qid=own_question(c);paper=finish(c,create(c,[qid]));pid=paper['id']
    r=c.post(f'/api/teacher/papers/{pid}/sheets',json={'student_ids':[1],'variant':'B'});assert r.status_code==200,r.text
    sid=r.json()['sheets'][0]['id'];pdf=c.get(f'/api/teacher/sheets/{sid}.pdf');assert pdf.status_code==200
    image=render_sheet(pdf.content);draw=ImageDraw.Draw(image);x,y=omr.cells(0)[0];draw.ellipse((x*2-7,y*2-7,x*2+7,y*2+7),fill='black')
    body={'image_base64':base64.b64encode(encode(image)).decode()}
    r=c.post(f'/api/teacher/papers/{pid}/scans',json=body);assert r.status_code==202,r.text
    scan=c.get(f'/api/teacher/papers/{pid}/scans').json()['scans'][0];assert scan['state']=='review',scan
    assert scan['detection'][0]['answer']=='A'
    assert c.post(f"/api/teacher/scans/{scan['id']}/review",json={'version':1,'answers':['A']}).json()['result']['score']==4
    c.post(f'/api/teacher/papers/{pid}/scans',json=body);duplicate=c.get(f'/api/teacher/papers/{pid}/scans').json()['scans'][0]
    assert c.post(f"/api/teacher/scans/{duplicate['id']}/review",json={'version':1,'answers':['A']}).status_code==409
    assert len(c.get('/api/teacher/students').json()['students'][0]['tests'])==1
    other=finish(c,create(c,[qid]));c.post(f"/api/teacher/papers/{other['id']}/scans",json=body)
    assert c.get(f"/api/teacher/papers/{other['id']}/scans").json()['scans'][0]['state']=='failed'
    grant(c,4);active[0]=4
    assert c.get(f'/api/teacher/sheets/{sid}.pdf').status_code==404
    assert c.get(f"/api/teacher/scans/{scan['id']}/preview").status_code==404

def test_teacher_account_cannot_use_student_api(monkeypatch):
    from starlette.requests import Request
    from app import auth
    request=Request({'type':'http','method':'GET','path':'/api/subject-tests','headers':[],'query_string':b''})
    user=SimpleNamespace(status='active',teacher_access=SimpleNamespace(active=True))
    account=SimpleNamespace(disabled=False,verified_at=utcnow(),terms=None)
    session=SimpleNamespace(csrf_token='x')
    def found(*args):request.state.auth_context=(session,account,user);return session
    monkeypatch.setattr(auth,'find_session',found)
    with pytest.raises(Exception) as error:auth.get_auth_account(request,None)
    assert error.value.status_code==403

@pytest.mark.parametrize('answer',['A','invalid'])
def test_offline_assignment_and_key_correction_regrades_once(studio,answer):
    from datetime import timedelta
    c,factory,active,room=studio
    qid=own_question(c);paper=finish(c,create(c,[qid]));pid=paper['id']
    now=utcnow();schedule={'classroom_ids':[room['id']],'opens_at':now.isoformat()+'Z','due_at':(now+timedelta(hours=1)).isoformat()+'Z','solutions_at':(now+timedelta(hours=1)).isoformat()+'Z'}
    assignment=c.post(f'/api/teacher/papers/{pid}/assign',json=schedule).json()['id']
    sheet=c.post(f'/api/teacher/papers/{pid}/sheets',json={'student_ids':[1],'variant':'B'}).json()['sheets'][0]
    pdf=c.get(f"/api/teacher/sheets/{sheet['id']}.pdf").content
    upload=c.post(f'/api/teacher/papers/{pid}/scans',json={'image_base64':base64.b64encode(pdf).decode()});assert upload.status_code==202,upload.text
    sid=upload.json()['id']
    review=c.post(f'/api/teacher/scans/{sid}/review',json={'version':1,'answers':[answer]});assert review.status_code==200,review.text
    with factory() as db:
        r=db.get(m.AssignmentRecipient,(assignment,1));assert r.result['score']==(4 if answer=='A' else -1)
        assert db.query(m.QuestionResponse).filter_by(attempt_id=r.attempt_id).count()==1
        stats=db.query(m.StudentSubtopicStats).filter_by(user_id=1,subtopic_id=1).one();before=(stats.attempted,stats.correct)
    body={'version':paper['version'],'reason':'Answer key was incorrect','corrections':[{'question_id':qid,'correct':'B'}]}
    fixed=c.post(f'/api/teacher/papers/{pid}/correct-key',json=body);assert fixed.status_code==200,fixed.text
    assert fixed.json()['paper']['variant_b']==paper['variant_b']
    assert c.post(f'/api/teacher/papers/{pid}/correct-key',json=body).status_code==409
    with factory() as db:
        r=db.get(m.AssignmentRecipient,(assignment,1));assert r.result['score']==-1
        assert db.get(m.TestAttempt,r.attempt_id).score==-1
        assert db.query(m.QuestionResponse).filter_by(attempt_id=r.attempt_id).count()==1
        stats=db.query(m.StudentSubtopicStats).filter_by(user_id=1,subtopic_id=1).one();assert (stats.attempted,stats.correct)==(before[0],before[1]-int(answer=='A'))
        assert db.get(m.TeacherScan,sid).result['score']==-1
        assert db.query(m.AuditLog).filter_by(action='teacher_key_corrected').count()==1
    student=c.get('/api/teacher/students').json()['students'][0]
    assert len(student['tests'])==1 and student['tests'][0]['mode']=='offline'
    assert student['tests'][0]['result']['score']==-1

def test_reference_generation_and_remedial_need_real_evidence(studio):
    c,factory,active,room=studio
    with factory() as db:
        for qid in (100,101,102,103):
            q=db.get(m.Question,qid);q.difficulty=5;q.exam='jee_main';q.type='single_correct';q.subtopic_id=1
            if qid in (100,101):q.year=2025;q.shift='Test morning';q.source_type='pyq'
        db.commit()
    original=c.post('/api/teacher/papers/generate',json={'mode':'exact','year':2025,'shift':'Test morning'})
    assert original.status_code==200,original.text
    assert {q['question_id'] for q in original.json()['questions']}=={100,101}
    similar=c.post('/api/teacher/papers/generate',json={'mode':'similar','year':2025,'shift':'Test morning','count':2})
    assert similar.status_code==200,similar.text
    assert not {100,101}&{q['question_id'] for q in similar.json()['questions']}
    assert all(q['subtopic_id']==1 and q['difficulty']==5 for q in similar.json()['questions'])
    assert c.post('/api/teacher/papers/generate',json={'mode':'remedial','classroom_ids':[room['id']]}).status_code==422
