import json
import pytest
import requests
from test_roadmap import setup
from test_teaching import classroom
from test_teacher_papers import studio
from app import models as m
from app.services import teacher_ai as ai


@pytest.fixture
def ai_studio(studio, monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-key-not-real')
    monkeypatch.setenv('TEACHER_AI_ENABLED', 'true')
    c, factory, active, room = studio
    with factory() as db:
        for q in db.query(m.Question):
            q.exam = 'jee_main'
            q.year = 2024
            q.shift = '2024-01-27-shift-1'
            q.source_type = 'pyq'
        db.commit()
    return studio


def request(c, prompt='Create 6 questions with 2 per subject from the bank.'):
    return c.post('/api/teacher/papers/ai-draft', json={'prompt':prompt,'exam':'jee_main'})


def mock_plan(monkeypatch, **kwargs):
    monkeypatch.setattr(ai, 'interpret', lambda *a: ai.AIPlan(**kwargs))


def test_optional_draft_counts_unique_questions_no_save_and_manual_unchanged(ai_studio, monkeypatch):
    c, factory, active, _ = ai_studio
    mock_plan(monkeypatch, count=6, sections=[{'subject':s,'count':2} for s in ('PHY','CHEM','MATH')])
    r=request(c); assert r.status_code == 200, r.text
    data=r.json(); assert len({q['question_id'] for q in data['questions']}) == 6
    assert data['summary']['subjects'] == {'PHY':2,'CHEM':2,'MATH':2}
    assert data['settings'] == {'exam':'jee_main'}
    assert not c.get('/api/teacher/papers').json()['papers']
    assert c.post('/api/teacher/papers/generate',json={'count':6}).status_code == 200
    active[0]=1
    assert request(c).status_code == 403


def test_from_shift_is_filtered_and_similar_excludes_reference(ai_studio, monkeypatch):
    c,factory,_,_=ai_studio
    with factory() as db:
        for sid in (1,2,3):
            for q in db.query(m.Question).filter(m.Question.id>=sid*100+10,m.Question.id<sid*100+25):
                q.year=2025;q.shift='2025-01-22-shift-2'
        db.commit()
    mock_plan(monkeypatch, selection='from_paper', paper_index=0, count=6)
    r=request(c);assert r.status_code==200,r.text
    with factory() as db:
        assert all(db.get(m.Question,q['question_id']).year==2024 and db.get(m.Question,q['question_id']).shift=='2024-01-27-shift-1' for q in r.json()['questions'])
    mock_plan(monkeypatch, selection='similar', paper_index=0, count=6)
    r=request(c);assert r.status_code==200,r.text
    with factory() as db:
        assert all(db.get(m.Question,q['question_id']).year==2025 for q in r.json()['questions'])
    # Explicit subject and chapter quotas preserve mixed question types.
    mock_plan(monkeypatch, selection='from_paper', year=2025, count=3, sections=[{'subject':'PHY','count':3,'chapter_ids':[1],'type':'numerical'}])
    r=request(c);assert r.status_code==200,r.text
    with factory() as db:
        assert all(db.get(m.Question,q['question_id']).year==2025 and q['subject']=='PHY' and q['type']=='numerical' for q in r.json()['questions'])


@pytest.mark.parametrize('plan', [
    {'count':200},
    {'count':2,'chapter_ids':[9999]},
    {'selection':'from_paper','count':2},
    {'selection':'similar','paper_index':999,'count':2},
    {'selection':'from_paper','paper_index':0,'year':2023,'count':2},
    {'count':3,'sections':[{'subject':'PHY','count':2}]},
    {'count':2,'sections':[{'subject':'PHY','count':2,'chapter_ids':[2]}]},
    {'count':2,'sections':[{'subject':'ENG','count':2}]},
    {'selection':'bank','year':2024,'count':2},
    {'clarification':'Which date and shift do you mean?'}
])
def test_invalid_constraints_do_not_create_partial_papers(ai_studio,monkeypatch,plan):
    c,*_=ai_studio;mock_plan(monkeypatch,**plan)
    assert request(c).status_code==422
    assert not c.get('/api/teacher/papers').json()['papers']


def test_catalog_only_visible_metadata_and_exam_separation(ai_studio,monkeypatch):
    c,factory,_,_=ai_studio
    with factory() as db:
        db.get(m.Question,100).exam='bitsat'
        db.get(m.Question,101).exam='jee_advanced'
        db.get(m.Question,102).status='draft';db.get(m.Question,102).created_by=4
        db.commit()
    def interpret(prompt,exam,catalog):
        assert exam=='jee_main'
        assert 'Question' not in json.dumps(catalog) and 'Solution' not in json.dumps(catalog)
        assert set(catalog)=={'papers','chapters'}
        assert sum(p['count'] for p in catalog['papers']) == 72
        return ai.AIPlan(count=10)
    monkeypatch.setattr(ai,'interpret',interpret)
    r=request(c);assert r.status_code==200,r.text
    assert not {100,101,102}.intersection(q['question_id'] for q in r.json()['questions'])


def test_missing_key_disabled_and_rate_limit_leave_manual_available(ai_studio,monkeypatch):
    c,*_=ai_studio
    monkeypatch.delenv('GROQ_API_KEY');assert request(c).status_code==503
    monkeypatch.setenv('GROQ_API_KEY','test-key-not-real')
    monkeypatch.setenv('TEACHER_AI_ENABLED','false');assert request(c).status_code==503
    monkeypatch.setenv('TEACHER_AI_ENABLED','true');mock_plan(monkeypatch,count=3)
    for _ in range(3):assert request(c).status_code==200
    assert request(c).status_code==429
    assert c.post('/api/teacher/papers/generate',json={'count':3}).status_code==200


def test_provider_bounded_request_and_errors(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','not-a-real-key')
    monkeypatch.setenv('TEACHER_AI_ENABLED','true')
    calls=[]
    class Response:
        status_code=200
        def json(self):return {'choices':[{'finish_reason':'stop','message':{'content':'{"count":6}'}}],'usage':{'prompt_tokens':500,'completion_tokens':100}}
    def post(url,**kw):calls.append((url,kw));return Response()
    monkeypatch.setattr(ai.requests,'post',post)
    assert ai.interpret('Make six questions','jee_main',{'papers':[],'chapters':[]}).count==6
    assert len(calls)==1 and calls[0][1]['json']['max_completion_tokens']==1600
    assert calls[0][1]['timeout']==(4,20)
    for status, expected in [(429,429),(401,503),(500,503)]:
        Response.status_code=status
        with pytest.raises(Exception) as e:ai.interpret('Make six questions','jee_main',{})
        assert e.value.status_code==expected and 'not-a-real-key' not in str(e.value.detail)
    def timeout(*a,**kw):raise requests.Timeout()
    monkeypatch.setattr(ai.requests,'post',timeout)
    with pytest.raises(Exception) as e:ai.interpret('Make six questions','jee_main',{})
    assert e.value.status_code==503


@pytest.mark.parametrize('content,finish', [('not json','stop'), ('{"count":201}','stop'), ('{"question_ids":[100]}','stop'), ('{"count":6}','length')])
def test_malformed_model_responses_rejected(monkeypatch,content,finish):
    monkeypatch.setenv('GROQ_API_KEY','not-a-real-key')
    monkeypatch.setattr(ai.requests,'post',lambda *a,**kw:type('Response',(),{'status_code':200,'json':lambda self:{'choices':[{'finish_reason':finish,'message':{'content':content}}]}})())
    with pytest.raises(Exception) as e:ai.interpret('Make six questions','jee_main',{})
    assert e.value.status_code==502


def test_exact_paper_keeps_every_format_and_existing_saved_draft(ai_studio,monkeypatch):
    c,factory,_,_=ai_studio
    saved=c.post('/api/teacher/papers',json={'title':'Keep this draft','question_ids':[100,101]}).json()
    mock_plan(monkeypatch,selection='exact',paper_index=0,source='pyq',title='Original paper')
    r=request(c);assert r.status_code==200,r.text
    assert len(r.json()['questions'])==75
    assert {q['type'] for q in r.json()['questions']}=={'single_correct','numerical'}
    unchanged=c.get(f"/api/teacher/papers/{saved['id']}").json()
    assert unchanged['title']=='Keep this draft' and len(unchanged['questions'])==2


def test_ai_selection_does_not_include_own_unpublished_questions(ai_studio,monkeypatch):
    c,factory,_,_=ai_studio
    with factory() as db:
        db.get(m.Question,100).status='draft';db.get(m.Question,100).created_by=3;db.commit()
    mock_plan(monkeypatch,selection='exact',paper_index=0)
    r=request(c);assert r.status_code==200,r.text
    assert len(r.json()['questions'])==74
    assert 100 not in [q['question_id'] for q in r.json()['questions']]
