"""Real small-paper conversations must work even with no AI quota or key."""
import uuid
import pytest
from test_teacher_ai import ai_studio
from test_teacher_papers import studio
from test_teaching import classroom
from test_roadmap import setup
from app import models as m
from app.services import teacher_ai as ai


@pytest.fixture
def offline_studio(ai_studio,monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY')
    monkeypatch.setattr(ai,'interpret',lambda *a:pytest.fail('This standard request must not consume provider quota'))
    return ai_studio


def send(c,prompt):
    response=c.post('/api/teacher/papers/ai-create',json={'prompt':prompt,'strict_details':True,'request_key':str(uuid.uuid4())})
    assert response.status_code==200,response.text
    return response.json()


@pytest.mark.parametrize('prompt,minutes',[
    ('Give me two JEE Main Physics questions for ten minutes.',10),
    ('Can you please make a short JEE Main physics test with 2 qs for 10 min?',10),
    ('JEE Main, Physics, 2 questions, 10 minutes',10),
    ('Create a 2-question JEE Main Physics paper for 10 minutes.',10),
    ('Give 2 MCQs in Physics for JEE Main for 10 minutes.',10),
    ('Please create a JEE Main test: 2 Physics questions for 10 minutes.',10),
    ('JEE Main Physics, questions: 2, 10min',10),
    ('Give me two JEE Main Physics questions for half an hour.',30),
    ('Make a JEE Main Physics paper with 2 questions for one hour and fifteen minutes.',75),
    ('Generate 2 JEE Main chem qns, 10 minutes, 2 marks, no negative marking.',10),
    ('Give me a couple of questions for JEE Main Physics within 10 minutes, set A and set B.',10),
])
def test_two_question_phrasing_works_without_api_key(offline_studio,prompt,minutes):
    c,factory,*_=offline_studio
    with factory() as db: before=db.query(m.AuthRateLimit).count()
    data=send(c,'teacher: '+prompt)
    assert data['state']=='ready',data
    paper=data['paper'];assert len(paper['questions'])==2
    assert paper['settings']['duration_minutes']==minutes
    with factory() as db:
        assert db.query(m.AuthRateLimit).count()==before


def test_short_replies_collect_only_missing_fields_then_return_pdfs(offline_studio):
    c,*_=offline_studio
    conversation='teacher: 2 q'
    data=send(c,conversation)
    assert data['state']=='needs_details' and '2 questions' in data['question']
    assert 'number of questions' not in data['question']
    for reply in ['JEE Main','Physics','10min']:
        conversation+='\nassistant: '+data['question']+'\nteacher: '+reply
        data=send(c,conversation)
    assert data['state']=='ready',data
    assert len(data['paper']['questions'])==2
    assert data['paper']['settings']['duration_minutes']==10
    omr=c.get(data['downloads'][0]['omr'])
    assert omr.status_code==200 and omr.content.startswith(b'%PDF')


def test_missing_exam_keeps_a_known_chapter_without_provider(offline_studio):
    c,factory,*_=offline_studio
    with factory() as db:
        chapter=db.get(m.Chapter,1);chapter.name='Electric Charges, Fields and Potential';chapter.slug='electrostatics';db.commit()
    prompt='teacher: Give me two questions on electrostatics for ten minutes.'
    data=send(c,prompt)
    assert data['state']=='needs_details'
    assert 'exam (' in data['question'] and 'subjects, chapters/topics' not in data['question']
    data=send(c,prompt+'\nassistant: '+data['question']+'\nteacher: JEE Main')
    assert data['state']=='ready',data
    assert {q['subject'] for q in data['paper']['questions']}=={'PHY'}


def test_subject_quotas_and_two_sets_are_local(offline_studio):
    c,*_=offline_studio
    data=send(c,'Give me a JEE Main paper with 2 Physics and 1 Chemistry questions for 10 minutes, two sets.')
    assert data['state']=='ready',data
    assert len(data['paper']['questions'])==3
    assert [q['subject'] for q in data['paper']['questions']].count('PHY')==2
    assert [d['variant'] for d in data['downloads']]==['A','B']
    for d in data['downloads']:assert c.get(d['omr']).content.startswith(b'%PDF')


@pytest.mark.parametrize('prompt,part',[
    ('2 JEE Main Physics questions for ten minutes, 10 sets','one paper or two shuffled sets'),
    ('2 JEE Main Physics Chemistry Mathematics questions for ten minutes','cannot include all 3 subjects'),
    ('2.5 JEE Main Physics questions for ten minutes','whole number'),
    ('Give me 0 JEE Main Physics questions for ten minutes','between 1 and 200'),
    ('2 JEE Main Physics questions for ten minutes, 0.5 marks','whole-number marks'),
])
def test_impossible_parameters_get_a_local_followup(offline_studio,prompt,part):
    c,*_=offline_studio
    data=send(c,prompt)
    assert data['state']=='needs_details' and part in data['question']
    assert not c.get('/api/teacher/papers').json()['papers']


@pytest.mark.parametrize('prompt',['Hello','Tell me a joke','What is the weather?','Create a website with two questions','Explain Physics'])
def test_unrelated_input_is_redirected_without_spending_quota(offline_studio,prompt):
    c,*_=offline_studio
    data=send(c,prompt)
    assert data['state']=='needs_details' and data['question']==ai.UNRELATED_MESSAGE
    assert not c.get('/api/teacher/papers').json()['papers']


def test_standard_request_still_works_after_language_limit(offline_studio):
    from app.services.authentication import throttle
    c,factory,*_=offline_studio
    with factory() as db:
        for _ in range(3):throttle(db,'teacher_ai:minute','3',3,60)
    data=send(c,'Give me two JEE Main Physics questions for ten minutes.')
    assert data['state']=='ready',data


def test_complex_request_capacity_error_explains_limit_and_does_not_create(ai_studio,monkeypatch):
    c,*_=ai_studio
    calls=[]
    class Response:
        status_code=429
        def json(self):return {'error':{'code':'rate_limit_exceeded'}}
    def post(url,**kwargs):calls.append(kwargs);return Response()
    monkeypatch.setattr(ai.requests,'post',post)
    response=c.post('/api/teacher/papers/ai-create',json={'prompt':'Give me 2 JEE Main Physics questions for 10 minutes with my custom blueprint.','strict_details':True,'request_key':str(uuid.uuid4())})
    assert response.status_code==429,response.text
    assert 'question count is not the limit' in response.json()['detail']
    assert len(calls)==1
    import json
    sent=json.loads(calls[0]['json']['messages'][1]['content'])['catalog']
    assert sent['papers']==[] and {chapter['subject'] for chapter in sent['chapters']}=={'PHY'}
    assert all('slug' not in chapter for chapter in sent['chapters'])
    assert not c.get('/api/teacher/papers').json()['papers']


def test_latest_marking_and_set_corrections_win(offline_studio):
    c,*_=offline_studio
    data=send(c,'teacher: Give 2 JEE Main Physics questions, 1 mark, no negative marking, two sets.\nassistant: Please specify duration in minutes.\nteacher: 10 minutes, +4/-1, single set')
    assert data['state']=='ready',data
    paper=data['paper']
    assert paper['settings']['marks_correct']==4 and paper['settings']['marks_wrong']==1
    assert paper['sets_enabled'] is False and len(data['downloads'])==1


def test_small_ai_sets_differ_without_changing_legacy_saved_orders():
    from types import SimpleNamespace
    import random
    from app.routers.teacher_papers import order_for
    for pid in range(1,20):
        old=SimpleNamespace(id=pid,questions=[{'question_id':1},{'question_id':2}],settings={})
        expected=[1,2];random.Random(f'paper-{pid}').shuffle(expected)
        assert order_for(old,'B')==expected
        new=SimpleNamespace(**{**vars(old),'settings':{'ai_distinct_sets':True}})
        assert order_for(new,'B')==[2,1]


def test_type_exclusion_is_not_inverted_into_a_numerical_request():
    from app.services.teacher_direct_request import direct_request
    catalog={'chapters':[{'id':1,'name':'Physics','slug':'physics','subject':'PHY'}],'paper_defaults':{'require_details':True}}
    assert direct_request('Give 2 JEE Main Physics questions for 10 minutes, no numerical questions.','jee_main',catalog) is None


def test_greeting_or_unrelated_detour_does_not_poison_the_next_paper_request(offline_studio):
    c,*_=offline_studio
    prompt='teacher: Hello\nassistant: '+ai.UNRELATED_MESSAGE+'\nteacher: Tell me a joke\nassistant: '+ai.UNRELATED_MESSAGE+'\nteacher: Give me two JEE Main Physics questions for ten minutes.'
    assert send(c,prompt)['state']=='ready'
