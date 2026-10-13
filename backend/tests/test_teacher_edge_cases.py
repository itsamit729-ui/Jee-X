"""Paper format readiness, no-set sheets and teacher recovery paths."""
from pathlib import Path
from datetime import timedelta
from test_teacher_papers import studio, classroom, setup, own_question, finish, render_sheet, shade_id, encode
from app import models as m
from app.auth import utcnow


def standard(c, ids):
    r=c.post('/api/teacher/papers',json={'title':'Standard classroom paper','question_ids':ids,'sets_enabled':False})
    assert r.status_code==201,r.text
    return r.json()


def test_no_set_paper_pdf_and_invalid_variant(studio,tmp_path):
    c,f,active,room=studio
    qid=own_question(c);paper=finish(c,standard(c,[qid]));pid=paper['id']
    assert paper['sets_enabled'] is False and paper['variant_b'] is None and paper['variants']==['A']
    assert paper['omr']['eligible']
    assert c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf?variant=B').status_code==422
    assert c.post(f'/api/teacher/papers/{pid}/sheets',json={'student_ids':[1],'variant':'B'}).status_code==422
    pdf=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf');assert pdf.status_code==200,pdf.text
    import pypdfium2 as pdfium
    with pdfium.PdfDocument(pdf.content) as doc:
        text=doc[0].get_textpage().get_text_range()
        assert 'Standard paper - no sets' in text and 'Set A' not in text
    (tmp_path/'standard-omr.pdf').write_bytes(pdf.content)
    render_sheet(pdf.content).save(tmp_path/'standard-omr.png')
    copy=c.post(f'/api/teacher/papers/{pid}/duplicate').json();assert copy['sets_enabled'] is False
    assert c.get('/api/teacher/papers').json()['papers'][0]['omr']['eligible']


def test_mixed_formats_remain_printable_scannable_and_assignable(studio):
    c,f,active,room=studio
    qid=own_question(c)
    paper=finish(c,standard(c,[100,120,qid]));pid=paper['id']
    assert paper['omr']['eligible'] and paper['omr']['layout']=='mixed'
    assert paper['omr']['eligible_count']==3 and paper['omr']['issues']==[]
    r=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf');assert r.status_code==200 and r.headers['content-type']=='application/pdf'
    # Same mixed paper is still assignable online.
    now=utcnow();schedule={'classroom_ids':[room['id']],'opens_at':now.isoformat()+'Z','due_at':(now+timedelta(days=1)).isoformat()+'Z','solutions_at':(now+timedelta(days=1)).isoformat()+'Z'}
    assert c.post(f'/api/teacher/papers/{pid}/assign',json=schedule).status_code==200


def test_omr_generation_filters_types_labels_and_bad_keys(studio):
    c,f,active,room=studio
    good=own_question(c);bad=own_question(c)
    with f() as db:
        option=db.query(m.QuestionOption).filter_by(question_id=bad,label='D').one();option.is_correct=True;db.commit()
    body={'omr_only':True,'count':1,'exclude_assigned':False}
    r=c.post('/api/teacher/papers/generate',json=body);assert r.status_code==200,r.text
    assert [q['question_id'] for q in r.json()['questions']]==[good]
    assert c.post('/api/teacher/papers/generate',json={**body,'count':2}).status_code==422
    assert c.post('/api/teacher/papers/generate',json={**body,'locked_ids':[bad]}).status_code==422
    assert c.post('/api/teacher/papers/generate',json={**body,'mode':'exact','year':2025,'shift':'test'}).status_code==422
    paper=standard(c,[bad]);assert not paper['omr']['eligible']


def test_unlabelled_past_paper_is_selectable_without_mixing_shifts(studio):
    c,f,active,room=studio
    with f() as db:
        for qid,shift in [(100,None),(101,'Morning')]:
            q=db.get(m.Question,qid);q.exam='jee_main';q.year=2025;q.shift=shift;q.source_type='pyq'
        db.commit()
    refs=c.get('/api/teacher/references').json()['papers'];assert any(r['shift'] is None for r in refs)
    body={'mode':'exact','exam':'jee_main','year':2025,'reference_without_shift':True,'exclude_assigned':False}
    result=c.post('/api/teacher/papers/generate',json=body);assert result.status_code==200,result.text
    assert [q['question_id'] for q in result.json()['questions']]==[100]
    assert c.post('/api/teacher/papers/generate',json={**body,'reference_without_shift':False}).status_code==422


def test_bad_schedule_and_whitespace_title_are_validation_errors(studio):
    c,f,active,room=studio
    assert c.post('/api/teacher/papers',json={'title':'   ','question_ids':[100]}).status_code==422
    paper=finish(c,standard(c,[100]))
    body={'classroom_ids':[room['id']],'opens_at':'bad-date','due_at':'bad-date','solutions_at':'bad-date'}
    r=c.post(f"/api/teacher/papers/{paper['id']}/assign",json=body);assert r.status_code==422,r.text
    body={**body,'opens_at':'2026-10-14T12:00:00','due_at':'2026-10-15T12:00:00','solutions_at':'2026-10-15T12:00:00'}
    assert c.post(f"/api/teacher/papers/{paper['id']}/assign",json=body).status_code==422


def test_reusable_clear_id_can_be_corrected_before_scoring(studio):
    c,f,active,room=studio
    active[0]=2;c.post('/api/classrooms/join',json={'code':room['join_code']});active[0]=3
    qid=own_question(c);paper=finish(c,standard(c,[qid]));pid=paper['id']
    pdf=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf').content
    import base64
    image=shade_id(render_sheet(pdf),'0000000001')
    r=c.post(f'/api/teacher/papers/{pid}/scans',json={'image_base64':base64.b64encode(encode(image)).decode()});assert r.status_code==202,r.text
    scan=c.get(f'/api/teacher/papers/{pid}/scans').json()['scans'][0]
    assert scan['student_id']==1 and scan['preview_available']
    r=c.post(f"/api/teacher/scans/{scan['id']}/review",json={'version':scan['version'],'student_id':2,'answers':['A']});assert r.status_code==200,r.text
    assert r.json()['result']['identity']['corrected_from_student_id']==1
    with f() as db:
        row=db.get(m.TeacherScan,scan['id']);assert db.get(m.TeacherSheet,row.sheet_id).student_id==2
    corrected=c.post(f'/api/teacher/papers/{pid}/correct-key',json={'version':paper['version'],'reason':'Corrected the reviewed key','corrections':[{'question_id':qid,'correct':'B'}]})
    assert corrected.status_code==200,corrected.text
    saved=c.get(f'/api/teacher/papers/{pid}/scans').json()['scans'][0]
    assert saved['result']['identity']['reviewed_student_id']==2


def test_legacy_settings_keep_sets_and_personalised_sheet_membership_is_checked(studio):
    c,f,active,room=studio
    qid=own_question(c)
    paper=c.post('/api/teacher/papers',json={'title':'Legacy paper','question_ids':[qid]}).json();pid=paper['id']
    with f() as db:
        row=db.get(m.TeacherPaper,pid);row.settings={k:v for k,v in row.settings.items() if k!='sets_enabled'};db.commit()
    paper=finish(c,paper);assert paper['sets_enabled'] and paper['variant_b']==[qid]
    sh=c.post(f'/api/teacher/papers/{pid}/sheets',json={'student_ids':[1],'variant':'B'}).json()['sheets'][0]
    pdf=c.get(f"/api/teacher/sheets/{sh['id']}.pdf").content
    import base64
    c.post(f'/api/teacher/papers/{pid}/scans',json={'image_base64':base64.b64encode(encode(render_sheet(pdf))).decode()})
    scan=c.get(f'/api/teacher/papers/{pid}/scans').json()['scans'][0]
    with f() as db: db.get(m.ClassroomMember,(room['id'],1)).active=False;db.commit()
    r=c.post(f"/api/teacher/scans/{scan['id']}/review",json={'version':scan['version'],'answers':['A']})
    assert r.status_code==404
