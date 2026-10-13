"""Regression cases for source bank choices in teacher papers."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from test_teaching import classroom
from test_roadmap import setup  # Initialise the isolated test database before app imports.
from app.routers.teaching import freeze
from app.services.teacher_question_content import presentation


def test_recover_source_choices_without_changing_ids_or_key():
    choices=[{'id':1,'label':'A','content':'A','is_correct':False},{'id':2,'label':'B','content':'','is_correct':True}]
    stem,options=presentation('Which statement is correct?\n(A) K.E. increases\n(B) K.E. decreases',choices)
    assert stem=='Which statement is correct?'
    assert options==[{**choices[0],'content':'K.E. increases'},{**choices[1],'content':'K.E. decreases'}]
    assert choices[1]['content']==''


def test_incomplete_choice_markers_do_not_remove_question_text():
    original='Consider (A) in the diagram.\n(B) is a point.'
    stem,options=presentation(original,[{'label':'A','content':'1'},{'label':'B','content':'2'}])
    assert stem==original
    assert [o['content'] for o in options]==['1','2']


def test_stem_diagram_does_not_replace_missing_option_drawings():
    q=SimpleNamespace(ref='PYQ-CHEM-missing-products',type='single_correct',stem='The major product formed is:',options=[SimpleNamespace(id=i,label=label,content='',is_correct=label=='C',position=i) for i,label in enumerate('ABCD')],assets=[SimpleNamespace(url='/reactant.png',alt_text='Reactant')])
    with pytest.raises(HTTPException) as error:freeze(q,1)
    assert error.value.status_code==409
    assert 'missing answer option content' in error.value.detail


def test_teacher_bank_skips_missing_choices_and_recovers_embedded_choices(classroom):
    from test_teaching import prepare
    from app import models as m
    client,factory,active=classroom
    prepare(classroom);active[0]=3
    with factory() as db:
        bad=db.get(m.Question,100)
        bad.stem='Choose a product for this reaction.'
        bad.options[0].content=''
        db.add(m.Asset(question_id=bad.id,url='/reactant.png',alt_text='Reactant structure'))
        recovered=db.get(m.Question,101)
        recovered.stem='Which statement is correct?\n(A) The first statement\n(B) The second statement'
        recovered.options[0].content='';recovered.options[1].content='B'
        db.commit()
    response=client.get('/api/teacher/questions')
    assert response.status_code==200
    rows={q['question_id']:q for q in response.json()['questions']}
    assert 100 not in rows
    assert rows[101]['stem']=='Which statement is correct?'
    assert [o['content'] for o in rows[101]['options']]==['The first statement','The second statement']
