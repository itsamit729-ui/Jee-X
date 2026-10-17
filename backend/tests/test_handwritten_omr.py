import base64
from datetime import timedelta
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw
from test_teacher_papers import studio,classroom,setup,finish,encode,shade_id
from test_mixed_omr import question,images,mark
from app import models as m
from app.auth import utcnow
from app.services import mixed_omr,teacher_omr,numeric_ocr

SAMPLES=np.load(Path(__file__).parent/'fixtures/mnist-test-first100.npz')


def write_number(image,item,text):
    for char,(x,y,w,h) in zip(text,mixed_omr.written_cells(item)):
        draw=ImageDraw.Draw(image)
        if char=='-':draw.line(((x+6)*2,(y+14)*2,(x+15)*2,(y+14)*2),fill='black',width=3)
        elif char=='.':draw.ellipse(((x+9)*2,(y+21)*2,(x+11)*2,(y+23)*2),fill='black')
        else:
            index=next(i for i,label in enumerate(SAMPLES['labels']) if str(label)==char)
            glyph=Image.fromarray(255-SAMPLES['images'][index]).convert('RGB')
            image.paste(glyph,(round((x+(w-14)/2)*2),round((y+(h-14)/2)*2)))
    return image


def paper(c,numbers=1,auto=True):
    qs=[question(c,'numerical',answer_min=-2,answer_max=-2) for _ in range(numbers)]
    qs+=[question(c,'multi_correct',options=['First','Second','Third','Fourth'],correct_options=['A','C']),question(c,'single_correct',options=['First','Second'],correct='B')]
    r=c.post('/api/teacher/papers',json={'title':'Simple handwritten answers','question_ids':[q['question_id'] for q in qs],
        'sets_enabled':False,'auto_score_scans':auto})
    assert r.status_code==201,r.text
    return finish(c,r.json())


def fill(image,items):
    for item in items:
        if item['type']=='numerical':write_number(image,item,'-2.0')
        else:
            for label,point in zip(item['labels'],mixed_omr.choices(item)):
                if label in ('AC' if item['type']=='multi_correct' else 'B'):mark(image,point,r=6)
    return shade_id(image,'0000000001')


def upload(c,pid,image):
    r=c.post(f'/api/teacher/papers/{pid}/scans',json={'image_base64':base64.b64encode(encode(image)).decode()})
    assert r.status_code==202,r.text
    return next(row for row in c.get(f'/api/teacher/papers/{pid}/scans').json()['scans'] if row['id']==r.json()['id'])


def test_real_handwritten_digits_signed_decimal_zero_and_unclear_rejection():
    accepted=0
    for glyph,label in zip(SAMPLES['images'],SAMPLES['labels']):
        predicted,confidence=numeric_ocr.digit(glyph)
        if predicted is not None:
            accepted+=1;assert int(predicted)==int(label)
            assert confidence>=numeric_ocr.MIN_CONFIDENCE
    assert accepted>=50
    item={'x':42,'y':332}
    for text,expected in [('-2.0','-2.0'),('0','0'),('22','22')]:
        image=write_number(Image.new('RGB',(1190,1684),'white'),item,text)
        result=numeric_ocr.read_number(cv2.cvtColor(np.array(image),cv2.COLOR_RGB2GRAY),mixed_omr.written_cells(item))
        assert result['answer']==expected,result
    image=write_number(Image.new('RGB',(1190,1684),'white'),item,'1')
    result=numeric_ocr.read_number(cv2.cvtColor(np.array(image),cv2.COLOR_RGB2GRAY),mixed_omr.written_cells(item))
    assert result['status']=='uncertain' and result['answer'] is None


def test_new_pdf_has_simple_boxes_and_actual_upload_scores_without_review(studio,tmp_path):
    c,factory,*_=studio
    p=paper(c);pid=p['id']
    assert p['omr']['numerical_response']=='handwritten' and p['omr']['page_count']==1
    pdf=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf').content
    (tmp_path/'handwritten-omr.pdf').write_bytes(pdf)
    items=mixed_omr.pages_for(p['questions'],[q['question_id'] for q in p['questions']],4)[0]
    image=fill(images(pdf)[0],items)
    token,aligned=teacher_omr.detect(encode(image.rotate(180)))
    assert token.startswith('v4:')
    found,_=mixed_omr.scan(aligned,items)
    assert [d['answer'] for d in found]==['-2.0','AC','B'],found
    row=upload(c,pid,image)
    assert row['state']=='reviewed',row
    assert row['result']['auto_scored'] and row['result']['score']==12
    assert len(c.get('/api/teacher/students').json()['students'][0]['tests'])==1
    duplicate=upload(c,pid,image)
    assert duplicate['state']=='duplicate'
    with factory() as db:assert db.query(m.TeacherScan).filter_by(paper_id=pid,state='reviewed').count()==1


def test_unclear_digits_or_missing_identity_do_not_create_automatic_scores(studio):
    c,factory,*_=studio
    p=paper(c);pid=p['id']
    pdf=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf').content
    items=mixed_omr.pages_for(p['questions'],[q['question_id'] for q in p['questions']],4)[0]
    image=images(pdf)[0]
    write_number(image,items[0],'1')
    row=upload(c,pid,shade_id(image,'0000000001'))
    assert row['state']=='review' and row['detection'][0]['answer'] is None
    image=fill(images(pdf)[0],items)
    # Leave the ID area blank while retaining every answer.
    blank=images(pdf)[0];image.paste(blank.crop((70,320,540,620)),(70,320))
    row=upload(c,pid,image)
    assert row['state']=='review' and row['student_id'] is None
    with factory() as db:assert db.query(m.TeacherScan).filter_by(paper_id=pid,state='reviewed').count()==0


def test_multi_page_clear_upload_finishes_once_and_updates_assigned_result(studio):
    c,factory,active,room=studio
    p=paper(c,numbers=15);pid=p['id'];now=utcnow()
    schedule={'classroom_ids':[room['id']],'opens_at':now.isoformat()+'Z','due_at':(now+timedelta(days=1)).isoformat()+'Z','solutions_at':(now+timedelta(days=1)).isoformat()+'Z'}
    assignment=c.post(f'/api/teacher/papers/{pid}/assign',json=schedule).json()['id']
    pdf=c.get(f'/api/teacher/papers/{pid}/blank-omr.pdf').content
    pages=mixed_omr.pages_for(p['questions'],[q['question_id'] for q in p['questions']],4)
    assert len(pages)==2
    rows=[upload(c,pid,fill(image,items)) for image,items in reversed(list(zip(images(pdf),pages)))]
    assert rows[0]['state']=='page_reviewed' and rows[-1]['state']=='reviewed'
    assert rows[-1]['result']['score']==68
    with factory() as db:
        recipient=db.get(m.AssignmentRecipient,(assignment,1))
        assert recipient.result['score']==68
        assert db.query(m.TestAttempt).filter_by(id=recipient.attempt_id).count()==1
        original_attempt=recipient.attempt_id
        previous=db.query(m.StudentSubtopicStats).filter_by(user_id=1,subtopic_id=1).one()
        attempted,correct=previous.attempted,previous.correct
    saved=rows[-1]
    corrected=[*saved['answers']];corrected[0]='0'
    response=c.post(f"/api/teacher/scans/{saved['id']}/correct-answers",json={'version':saved['version'],'answers':corrected})
    assert response.status_code==200,response.text
    assert response.json()['result']['score']==63
    assert c.post(f"/api/teacher/scans/{saved['id']}/correct-answers",json={'version':saved['version'],'answers':corrected}).status_code==409
    with factory() as db:
        recipient=db.get(m.AssignmentRecipient,(assignment,1))
        assert recipient.result['score']==63 and recipient.attempt_id==original_attempt
        assert db.query(m.QuestionResponse).filter_by(attempt_id=original_attempt).count()==17
        stat=db.query(m.StudentSubtopicStats).filter_by(user_id=1,subtopic_id=1).one()
        assert stat.attempted==attempted and stat.correct==correct-1


def test_new_numeric_pagination_is_compact_and_never_loses_a_question():
    qs=[{'question_id':i,'type':'numerical','options':[]} for i in range(200)]
    pages=mixed_omr.pages_for(qs,list(range(200)),4)
    assert len(pages)==15
    assert [q['question_id'] for page in pages for q in page]==list(range(200))
    assert all(q['y']+49<790 for page in pages for q in page)
