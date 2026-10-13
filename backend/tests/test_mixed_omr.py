import base64
import io
from pathlib import Path
from types import SimpleNamespace
from datetime import timedelta
from PIL import ImageDraw
import pypdfium2 as pdfium
from test_teacher_papers import studio, classroom, setup, finish, encode, shade_id
from app import models as m
from app.auth import utcnow
from app.services import mixed_omr, teacher_omr


def question(c,kind,**extra):
    body={'subtopic_id':1,'stem':'Mixed answer test question','type':kind,'solution':'Worked solution',**extra}
    r=c.post('/api/teacher/questions/private',json=body);assert r.status_code==201,r.text
    return r.json()


def create_mixed(c,numbers=7,sets=False):
    questions=[question(c,'numerical',answer_min=-12.5,answer_max=-12.5) for _ in range(numbers)]
    questions+=[question(c,'multi_correct',options=['First','Second','Third','Fourth'],correct_options=['A','C']),question(c,'single_correct',options=['First','Second'],correct='B')]
    r=c.post('/api/teacher/papers',json={'title':'Mixed format test','question_ids':[q['question_id'] for q in questions],'sets_enabled':sets,'marks_correct':4,'marks_wrong':1})
    assert r.status_code==201,r.text
    return finish(c,r.json())


def mark(image,point,r=4):
    x,y=point;ImageDraw.Draw(image).ellipse((x*2-r,y*2-r,x*2+r,y*2+r),fill='black')


def fill_page(image,items):
    for item in items:
        if item['type']=='numerical':
            cells=mixed_omr.number_cells(item)
            mark(image,cells['sign'][1]);mark(image,cells['decimal'][1])
            for column,digit in zip(cells['digits'],'00000125'):mark(image,column[int(digit)])
        else:
            for label,point in zip(item['labels'],mixed_omr.choices(item)):
                if label in ('AC' if item['type']=='multi_correct' else 'B'):mark(image,point,r=6)
    return image


def images(pdf):
    with pdfium.PdfDocument(pdf) as doc:return [page.render(scale=2).to_pil().convert('RGB') for page in doc]


def upload(c,pid,image):
    r=c.post(f'/api/teacher/papers/{pid}/scans',json={'image_base64':base64.b64encode(encode(image)).decode()});assert r.status_code==202,r.text
    row=next(s for s in c.get(f'/api/teacher/papers/{pid}/scans').json()['scans'] if s['id']==r.json()['id'])
    assert row['state']=='review',row.get('error')
    return row


def test_mixed_detection_pdf_order_sign_decimal_multiple_and_blank(studio,tmp_path):
    c,f,active,room=studio
    paper=create_mixed(c);pid=paper['id']
    assert paper['omr']['eligible'] and paper['omr']['layout']=='mixed' and paper['omr']['page_count']==2
    pdf=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf').content
    (tmp_path/'mixed.pdf').write_bytes(pdf)
    pages=mixed_omr.pages_for(paper['questions'],[q['question_id'] for q in paper['questions']])
    for index,(im,items) in enumerate(zip(images(pdf),pages)):
        im.save(tmp_path/f'mixed-page-{index+1}.png')
        token,aligned=teacher_omr.detect(encode(im));assert token.endswith(f':{index}')
        found,_=mixed_omr.scan(aligned,items);assert all(d['status']=='blank' for d in found),str(found)
        im=shade_id(fill_page(im,items),'0000000001')
        for rendered in (im,im.rotate(180)):
            token,aligned=teacher_omr.detect(encode(rendered));found,_=mixed_omr.scan(aligned,items)
            assert teacher_omr.read_student_id(aligned)['digits']=='0000000001'
            assert all(d['status']=='marked' for d in found),str(found)
            assert [d['answer'] for d in found]==['-12.5' if d['type']=='numerical' else 'AC' if d['type']=='multi_correct' else 'B' for d in found]


def test_pages_complete_once_with_online_grading_parity_and_key_corrections(studio):
    c,f,active,room=studio
    paper=create_mixed(c);pid=paper['id'];now=utcnow()
    schedule={'classroom_ids':[room['id']],'opens_at':now.isoformat()+'Z','due_at':(now+timedelta(days=1)).isoformat()+'Z','solutions_at':(now+timedelta(days=1)).isoformat()+'Z'}
    assignment=c.post(f'/api/teacher/papers/{pid}/assign',json=schedule).json()['id']
    pdf=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf').content
    pages=mixed_omr.pages_for(paper['questions'],[q['question_id'] for q in paper['questions']]);rows=[]
    for im,items in zip(images(pdf),pages):rows.append(upload(c,pid,shade_id(fill_page(im,items),'0000000001')))
    # Out-of-order uploads/reviews must still produce the full original order.
    first=rows[1];answers=[d['answer'] for d in first['detection']]
    r=c.post(f"/api/teacher/scans/{first['id']}/review",json={'version':first['version'],'student_id':1,'answers':answers});assert r.status_code==200,r.text
    assert r.json()['complete'] is False and r.json()['missing_pages']==[1]
    with f() as db:assert db.get(m.AssignmentRecipient,(assignment,1)).attempt_id is None
    # Partial confirmation is editable until the full paper is scored.
    reopened=c.post(f"/api/teacher/scans/{first['id']}/reopen-page",json={'version':first['version']+1});assert reopened.status_code==200,reopened.text
    assert c.post(f"/api/teacher/scans/{first['id']}/review",json={'version':reopened.json()['version'],'student_id':1,'answers':answers}).json()['complete'] is False
    second=rows[0]
    r=c.post(f"/api/teacher/scans/{second['id']}/review",json={'version':second['version'],'student_id':1,'answers':[d['answer'] for d in second['detection']]});assert r.status_code==200,r.text
    assert r.json()['complete'] and r.json()['result']['score']==36
    with f() as db:
        recipient=db.get(m.AssignmentRecipient,(assignment,1));assert recipient.result['score']==36
        assert db.query(m.TestAttempt).filter_by(test_id=db.get(m.TeachingAssignment,assignment).test_id,user_id=1).count()==1
        assert [v['numeric_answer'] for v in recipient.draft if v['numeric_answer'] is not None]==[-12.5]*7
    assert c.post(f"/api/teacher/scans/{second['id']}/review",json={'version':second['version'],'answers':['']*6}).status_code==409
    changes=[{'question_id':paper['questions'][0]['question_id'],'answer_min':0,'answer_max':0},{'question_id':paper['questions'][-2]['question_id'],'correct_options':['B','D']}]
    r=c.post(f'/api/teacher/papers/{pid}/correct-key',json={'version':paper['version'],'reason':'Correct the numeric and multiple-choice keys','corrections':changes})
    assert r.status_code==200,r.text
    with f() as db:
        assert db.get(m.AssignmentRecipient,(assignment,1)).result['score']==26
        scored=db.query(m.TeacherScan).filter_by(paper_id=pid,state='reviewed').one()
        assert scored.result['score']==26 and len(scored.answers)==9 and scored.result['page_count']==2


def test_personalised_mixed_set_b_and_manual_numeric_entry(studio):
    c,f,active,room=studio
    paper=create_mixed(c,numbers=1,sets=True);pid=paper['id']
    sh=c.post(f'/api/teacher/papers/{pid}/sheets',json={'student_ids':[1],'variant':'B'}).json()['sheets'][0]
    pdf=c.get(f"/api/teacher/sheets/{sh['id']}.pdf").content
    pages=mixed_omr.pages_for(paper['questions'],paper['variant_b'])
    row=upload(c,pid,images(pdf)[0]);assert row['student_id']==1 and row['variant']=='B'
    types={q['question_id']:q['type'] for q in paper['questions']}
    answers=['-1.25e1' if types[d['question_id']]=='numerical' else 'CA' if types[d['question_id']]=='multi_correct' else 'B' for d in row['detection']]
    invalid=[*answers];numeric=next(i for i,d in enumerate(row['detection']) if d['type']=='numerical');invalid[numeric]='1e999'
    assert c.post(f"/api/teacher/scans/{row['id']}/review",json={'version':row['version'],'answers':invalid}).status_code==422
    r=c.post(f"/api/teacher/scans/{row['id']}/review",json={'version':row['version'],'answers':answers});assert r.status_code==200,r.text
    assert r.json()['result']['score']==12


def test_numerical_ambiguity_handwriting_and_multiple_choice_exactness(studio):
    c,f,active,room=studio
    paper=create_mixed(c,numbers=1);pid=paper['id']
    pdf=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf').content
    items=mixed_omr.pages_for(paper['questions'],[q['question_id'] for q in paper['questions']])[0]
    im=images(pdf)[0];numeric=items[0];x,y,w,h=mixed_omr.number_cells(numeric)['box']
    ImageDraw.Draw(im).text((x*2+10,y*2+4),'123456789012.34',fill='black')
    _,aligned=teacher_omr.detect(encode(im));found,_=mixed_omr.scan(aligned,items)
    assert found[0]['status']=='written' and found[0]['answer'] is None
    im=fill_page(images(pdf)[0],items);mark(im,mixed_omr.number_cells(numeric)['sign'][0])
    _,aligned=teacher_omr.detect(encode(im));found,_=mixed_omr.scan(aligned,items)
    assert found[0]['status']=='uncertain' and found[0]['answer'] is None
    row=upload(c,pid,shade_id(im,'0000000001'))
    r=c.post(f"/api/teacher/scans/{row['id']}/review",json={'version':row['version'],'student_id':1,'answers':['invalid','A','']})
    assert r.status_code==200,r.text
    assert r.json()['result']['score']==-2 and [q['outcome'] for q in r.json()['result']['questions']]==['wrong','wrong','skipped']


def test_zero_and_eight_decimal_places_are_not_blank(studio):
    c,f,active,room=studio
    paper=create_mixed(c,numbers=1);pid=paper['id']
    pdf=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf').content
    items=mixed_omr.pages_for(paper['questions'],[q['question_id'] for q in paper['questions']])[0]
    pts=mixed_omr.number_cells(items[0])
    for digits,places,expected in [('00000000',0,'0'),('12345678',8,'0.12345678')]:
        im=images(pdf)[0];mark(im,pts['sign'][0]);mark(im,pts['decimal'][places])
        for col,digit in zip(pts['digits'],digits):mark(im,col[int(digit)])
        _,aligned=teacher_omr.detect(encode(im));found,_=mixed_omr.scan(aligned,items)
        assert found[0]['status']=='marked' and found[0]['answer']==expected


def test_maximum_numeric_paper_paginates_without_missing_or_overlapping_items():
    qs=[{'question_id':i,'type':'numerical','options':[]} for i in range(200)]
    pages=mixed_omr.pages_for(qs,list(range(200)))
    assert len(pages)==50
    assert [q['question_id'] for page in pages for q in page]==list(range(200))
    assert all(q['y']+149<790 for page in pages for q in page)
