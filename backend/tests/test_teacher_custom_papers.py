from collections import Counter
import pytest
from test_teacher_quick_papers import quick_studio,studio,classroom,setup,create
from app import models as m


def test_exact_type_mix_can_cross_subjects_without_changing_counts(quick_studio):
    c,factory,*_=quick_studio
    with factory() as db:
        for qid in [101,102]:
            q=db.get(m.Question,qid);q.type='multi_correct'
            for option in q.options:option.is_correct=option.label in ['A','C']
        db.commit()
    mix=[{'type':'single_correct','count':6},{'type':'multi_correct','count':2},{'type':'numerical','count':2}]
    response=create(c,count=10,question_mix=mix)
    assert response.status_code==200,response.text
    paper=response.json()['paper']
    assert Counter(q['type'] for q in paper['questions'])=={'single_correct':6,'multi_correct':2,'numerical':2}
    assert len({q['question_id'] for q in paper['questions']})==10
    assert paper['settings']['numerical_response']=='handwritten'
    assert paper['settings']['auto_score_scans'] is True


def test_specific_sections_are_reserved_before_any_subject_sections(quick_studio):
    c,factory,*_=quick_studio
    with factory() as db:
        keep={101,102,201,202,203,204}
        for q in db.query(m.Question):
            if q.id not in keep:q.status='draft'
            else:q.type='single_correct'
        db.commit()
    mix=[{'type':'single_correct','count':4},{'subject':'PHY','type':'single_correct','count':2,'chapter_ids':[1]}]
    response=create(c,count=6,subjects=None,question_mix=mix)
    assert response.status_code==200,response.text
    assert {q['question_id'] for q in response.json()['paper']['questions']}==keep


@pytest.mark.parametrize('mix,extra',[
    ([{'type':'numerical','count':1}],{}),
    ([{'type':'numerical','count':2}],{'question_type':'single_correct'}),
    ([{'subject':'CHEM','type':'single_correct','count':2}],{}),
    ([{'subject':'PHY','type':'single_correct','count':2,'chapter_ids':[2]}],{}),
    ([{'type':'numerical','count':0}],{}),
    ([{'type':'numerical','count':2}],{'selection':'exact','subjects':None,'year':2024,'shift':'2024-01-27-shift-1'}),
])
def test_invalid_mix_never_saves_partial_paper(quick_studio,mix,extra):
    c,*_=quick_studio
    response=create(c,question_mix=mix,**extra)
    assert response.status_code==422,response.text
    assert not c.get('/api/teacher/papers').json()['papers']


def test_format_shortfall_names_the_missing_section(quick_studio):
    c,*_=quick_studio
    response=create(c,question_mix=[{'type':'multi_correct','count':2}])
    assert response.status_code==422 and 'Multiple correct' in response.json()['detail']
    assert not c.get('/api/teacher/papers').json()['papers']
