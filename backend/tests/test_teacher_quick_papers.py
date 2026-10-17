import random
import uuid
from types import SimpleNamespace
import pytest
from test_roadmap import setup
from test_teaching import classroom,grant
from test_teacher_papers import studio
from app import models as m
from app.routers import teacher_papers as p


@pytest.fixture
def quick_studio(studio,monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    c,factory,*_=studio
    with factory() as db:
        for q in db.query(m.Question):
            q.exam='jee_main';q.year=2024;q.shift='2024-01-27-shift-1';q.source_type='pyq'
        db.commit()
    return studio


def create(c,**changes):
    return c.post('/api/teacher/papers/quick-create',json={
        'request_key':str(uuid.uuid4()),'exam':'jee_main','count':2,'subjects':['PHY'],
        'duration_minutes':10,**changes})


def test_one_step_creation_returns_final_paper_and_both_omrs_without_provider(quick_studio):
    c,factory,*_=quick_studio
    with factory() as db: before=db.query(m.AuthRateLimit).count()
    response=create(c,sets_enabled=True)
    assert response.status_code==200,response.text
    result=response.json();paper=result['paper']
    assert result['state']=='ready' and paper['finalized']
    assert len(paper['questions'])==2 and {q['subject'] for q in paper['questions']}=={'PHY'}
    assert paper['settings']['duration_minutes']==10
    assert (paper['settings']['marks_correct'],paper['settings']['marks_wrong'])==(4,1)
    assert paper['variant_b']!=[q['question_id'] for q in paper['questions']]
    assert [d['variant'] for d in result['downloads']]==['A','B']
    for download in result['downloads']:
        response=c.get(download['omr']);assert response.status_code==200 and response.content.startswith(b'%PDF')
    with factory() as db:
        assert db.query(m.TeacherPaper).count()==1
        assert db.query(m.TeachingAssignment).count()==0
        assert db.query(m.AuthRateLimit).count()==before


def test_catalog_is_exam_scoped_published_metadata_and_validates_chapters(quick_studio):
    c,factory,*_=quick_studio
    with factory() as db:
        db.get(m.Question,100).status='draft';db.get(m.Question,100).created_by=3
        for q in db.query(m.Question).filter(m.Question.id>=200,m.Question.id<300):q.exam='bitsat'
        db.commit()
    result=c.get('/api/teacher/papers/catalog?exam=jee_main')
    assert result.status_code==200,result.text
    chapters=result.json()['chapters']
    assert {row['subject'] for row in chapters}=={'PHY','MATH'}
    assert sum(row['count'] for row in chapters)==49
    assert all(set(row)=={'id','name','subject','count'} for row in chapters)
    assert create(c,chapter_ids=[2]).status_code==422
    assert create(c,chapter_ids=[9999]).status_code==422
    result=create(c,chapter_ids=[1]).json()
    assert all(q['question_id']!=100 for q in result['paper']['questions'])


def test_retry_is_teacher_scoped_and_duplicate_has_no_request_identity(quick_studio,monkeypatch):
    c,factory,active,_=quick_studio
    key=str(uuid.uuid4())
    first=create(c,request_key=key).json()['paper']
    generate=p.generate
    monkeypatch.setattr(p,'generate',lambda *a:pytest.fail('A replay must not generate again'))
    assert create(c,request_key=key).json()['paper']['id']==first['id']
    copied=c.post(f"/api/teacher/papers/{first['id']}/duplicate").json()
    assert 'creation_request_key' not in copied['settings'] and copied['finalized'] is False
    grant(c,4);active[0]=4
    assert c.get(f"/api/teacher/papers/{first['id']}").status_code==404
    assert c.get(f"/api/teacher/papers/{first['id']}/blank-omr.pdf").status_code==404
    monkeypatch.setattr(p,'generate',generate)
    own=create(c,request_key=key)
    assert own.status_code==200 and own.json()['paper']['id']!=first['id']
    active[0]=1
    assert create(c).status_code==403
    assert c.get('/api/teacher/papers/catalog').status_code==403


@pytest.mark.parametrize('changes',[
    {'count':0},{'count':201},{'duration_minutes':0},{'duration_minutes':241},
    {'request_key':'invalid'},{'marks_correct':0},{'marks_wrong':-1},{'subjects':['ENG']},
    {'subjects':[]},{'chapter_ids':[2]},{'year':2024},
    {'selection':'from_paper','year':2024,'shift':'missing-shift'},
    {'selection':'exact','year':2024,'shift':'2024-01-27-shift-1'},
    {'title':'  '},
])
def test_invalid_parameters_do_not_create_partial_papers(quick_studio,changes):
    c,*_=quick_studio
    response=create(c,**changes)
    assert response.status_code==422,response.text
    assert not c.get('/api/teacher/papers').json()['papers']


def test_reference_subset_and_full_paper_keep_exact_year_shift_and_formats(quick_studio):
    c,factory,*_=quick_studio
    with factory() as db:
        for q in db.query(m.Question).filter(m.Question.id>=110,m.Question.id<125):
            q.year=2025;q.shift='2025-01-22-shift-2'
        db.commit()
    body={'selection':'from_paper','year':2024,'shift':'2024-01-27-shift-1'}
    result=create(c,**body);assert result.status_code==200,result.text
    with factory() as db:
        assert all(db.get(m.Question,q['question_id']).year==2024 for q in result.json()['paper']['questions'])
    result=create(c,**{**body,'selection':'exact'},subjects=None)
    assert result.status_code==200,result.text
    assert len(result.json()['paper']['questions'])==60
    assert {q['type'] for q in result.json()['paper']['questions']}=={'single_correct','numerical'}


def test_null_shift_is_a_real_reference_not_a_wildcard(quick_studio):
    c,factory,*_=quick_studio
    with factory() as db:
        for q in db.query(m.Question).filter(m.Question.id<110):q.shift=None
        db.commit()
    result=create(c,selection='from_paper',year=2024,shift=None)
    assert result.status_code==200,result.text
    with factory() as db:
        assert all(db.get(m.Question,q['question_id']).shift is None for q in result.json()['paper']['questions'])


@pytest.mark.parametrize('exam,subject,correct,wrong',[
    ('mht_cet','PHY',1,0),('mht_cet','MATH',2,0),('bitsat','PHY',3,1),
])
def test_marking_defaults_follow_exam_and_subject(quick_studio,exam,subject,correct,wrong):
    c,factory,*_=quick_studio
    with factory() as db:
        for q in db.query(m.Question):q.exam=exam
        db.commit()
    result=create(c,exam=exam,subjects=[subject])
    assert result.status_code==200,result.text
    settings=result.json()['paper']['settings']
    assert (settings['marks_correct'],settings['marks_wrong'])==(correct,wrong)


def test_mixed_cet_requires_explicit_uniform_marking_and_can_be_completed(quick_studio):
    c,factory,*_=quick_studio
    with factory() as db:
        for q in db.query(m.Question):q.exam='mht_cet'
        db.commit()
    result=create(c,exam='mht_cet',count=6,subjects=None)
    assert result.status_code==422 and 'More options' in result.json()['detail']
    assert not c.get('/api/teacher/papers').json()['papers']
    result=create(c,exam='mht_cet',count=6,subjects=None,marks_correct=2,marks_wrong=0)
    assert result.status_code==200,result.text


def test_shortfall_or_unavailable_diagrams_never_save_a_partial_paper(quick_studio,monkeypatch):
    from app.services import teacher_paper_assets
    c,factory,*_=quick_studio
    with factory() as db:
        db.add(m.Asset(question_id=100,url='/question-images/pyq/missing.png',alt_text='Required diagram'))
        db.commit()
    monkeypatch.setattr(teacher_paper_assets,'diagram_file',lambda _:None)
    result=create(c,count=25)
    assert result.status_code==422 and 'shortfall' in result.json()['detail']
    assert not c.get('/api/teacher/papers').json()['papers']
    result=create(c)
    assert result.status_code==200,result.text
    assert all(q['question_id']!=100 for q in result.json()['paper']['questions'])


def test_retired_ai_routes_no_longer_create_anything(quick_studio):
    c,*_=quick_studio
    for path in ['ai-create','ai-draft']:
        response=c.post('/api/teacher/papers/'+path,json={'prompt':'Create a paper'})
        assert response.status_code==410 and 'removed' in response.json()['detail']
    assert not c.get('/api/teacher/papers').json()['papers']


def test_existing_printed_orders_remain_stable():
    for pid in range(1,10):
        legacy=SimpleNamespace(id=pid,questions=[{'question_id':1},{'question_id':2}],settings={})
        expected=[1,2];random.Random(f'paper-{pid}').shuffle(expected)
        assert p.order_for(legacy,'B')==expected
        for flag in ['ai_distinct_sets','distinct_sets']:
            current=SimpleNamespace(**{**vars(legacy),'settings':{flag:True}})
            assert p.order_for(current,'B')==[2,1]


def test_default_one_click_request_needs_no_title_marking_or_scope(quick_studio):
    c,*_=quick_studio
    result=c.post('/api/teacher/papers/quick-create',json={'request_key':str(uuid.uuid4())})
    assert result.status_code==200,result.text
    data=result.json();paper=data['paper']
    assert len({q['question_id'] for q in paper['questions']})==30
    assert {subject:sum(q['subject']==subject for q in paper['questions']) for subject in ['PHY','CHEM','MATH']}=={'PHY':10,'CHEM':10,'MATH':10}
    assert paper['settings']['duration_minutes']==60
    assert '30 questions' in paper['title'] and len(data['downloads'])==1


def test_selected_chapters_narrow_a_subject_group_and_source_is_respected(quick_studio):
    c,factory,*_=quick_studio
    with factory() as db:
        for q in db.query(m.Question).filter(m.Question.id.in_([100,101,102])):q.source_type='original'
        db.commit()
    result=create(c,subjects=['PHY','CHEM'],chapter_ids=[1],source='original',title='Friday quiz',marks_correct=2,marks_wrong=0)
    assert result.status_code==200,result.text
    paper=result.json()['paper']
    assert {q['question_id'] for q in paper['questions']}<={100,101,102}
    assert paper['title']=='Friday quiz' and paper['settings']['marks_wrong']==0
