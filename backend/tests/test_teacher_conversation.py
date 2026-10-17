"""Golden conversations exercise the same structured protocol as the teacher UI."""
import uuid
import pytest
from test_teacher_short_requests import offline_studio, ai_studio, studio, classroom, setup
from app import models as m
from app.services import teacher_ai as ai
from app.services.teacher_paper_conversation import PaperConversation, advance
from app.services.teacher_paper_language import mappings, chapter_aliases


def send(c, text, state=None):
    response = c.post('/api/teacher/papers/ai-create', json={
        'prompt':text, 'conversation':state or {}, 'strict_details':True, 'request_key':str(uuid.uuid4())})
    assert response.status_code == 200, response.text
    return response.json()


def topic(factory, name='Electrostatics', slug='electrostatics'):
    with factory() as db:
        chapter = db.get(m.Chapter, 1)
        chapter.name, chapter.slug = name, slug
        db.commit()


def test_short_replies_use_fields_without_resending_history(offline_studio):
    c, *_ = offline_studio
    result = send(c, '2 questions')
    for reply in ['JEE Mains', 'phy', '10']:
        assert result['state'] == 'needs_details'
        result = send(c, reply, result['conversation'])
    assert result['state'] == 'ready', result
    assert len(result['paper']['questions']) == 2
    assert result['paper']['settings']['duration_minutes'] == 10
    assert c.get(result['downloads'][0]['omr']).content.startswith(b'%PDF')


def test_typo_is_not_guessed_and_can_be_corrected_without_old_text(offline_studio):
    c, factory, *_ = offline_studio
    topic(factory)
    result = send(c, 'Make two JEE Mains phy questions on electrostatcs, 1 mark, no negative marking, two sets.')
    assert 'Did you mean Electrostatics' in result['question']
    assert not c.get('/api/teacher/papers').json()['papers']
    result = send(c, 'Electrostatics', result['conversation'])
    assert 'duration' in result['question']
    result = send(c, 'Actually make it three questions', result['conversation'])
    result = send(c, '10min', result['conversation'])
    assert result['state'] == 'ready', result
    assert len(result['paper']['questions']) == 3
    assert result['paper']['settings']['marks_correct'] == 1
    assert result['paper']['settings']['marks_wrong'] == 0
    assert len(result['downloads']) == 2


@pytest.mark.parametrize('alias,slug,name',[
    ('NLM','laws-of-motion','Laws of Motion'),
    ('SHM','oscillations','Oscillations'),
    ('electric charges and fields','electrostatics','Electrostatics'),
    ('units and measurements','units-dimensions','Units and Dimensions'),
])
def test_mapping_resolves_to_live_ids_not_hardcoded_ids(offline_studio,alias,slug,name):
    c, factory, *_ = offline_studio
    topic(factory,name,slug)
    result = send(c,f'Give 2 JEE Main Physics questions on {alias}, 10 minutes.')
    assert result['state'] == 'ready', result
    with factory() as db:
        assert {db.get(m.Question,q['question_id']).subtopic.chapter_id for q in result['paper']['questions']} == {1}


def test_unknown_topic_does_not_get_dropped_after_known_one(offline_studio):
    c, factory, *_ = offline_studio
    topic(factory)
    result = send(c,'2 JEE Main Physics questions on Electrostatics and unicorn dynamics, 10 minutes')
    assert result['state'] == 'needs_details' and 'unicorn dynamics' in result['question']
    assert not c.get('/api/teacher/papers').json()['papers']
    result = send(c,'Electrostatics',result['conversation'])
    assert result['state'] == 'ready', result


def test_same_chapter_name_across_subjects_requires_disambiguation(offline_studio):
    c, factory, *_ = offline_studio
    topic(factory,'Thermodynamics','thermodynamics')
    with factory() as db:
        chapter=db.get(m.Chapter,2);chapter.name='Thermodynamics';chapter.slug='thermodynamics';db.commit()
    result=send(c,'2 JEE Main questions on Thermodynamics, 10 minutes')
    assert result['state']=='needs_details' and 'Which chapter' in result['question']
    result=send(c,'Physics',result['conversation'])
    assert result['state']=='ready', result
    assert {q['subject'] for q in result['paper']['questions']}=={'PHY'}


def test_invalid_values_are_replaceable_not_permanent(offline_studio):
    c, *_ = offline_studio
    result=send(c,'2 JEE Main Physics questions for 10 minutes, 9 sets')
    assert 'one paper or two' in result['question']
    result=send(c,'single set',result['conversation'])
    assert result['state']=='ready' and result['paper']['sets_enabled'] is False


def test_unrelated_detour_retains_request_without_creating(offline_studio):
    c, *_ = offline_studio
    result=send(c,'2 JEE Main Physics questions')
    state=result['conversation']
    result=send(c,'Tell me a joke',state)
    assert result['question']==ai.UNRELATED_MESSAGE
    assert result['conversation']['slots']==state['slots']
    result=send(c,'10 minutes',result['conversation'])
    assert result['state']=='ready',result


def test_changing_one_score_preserves_other_score_and_unresolved_constraints():
    chapters=[{'id':7,'subject':'PHY','name':'Electrostatics','slug':'electrostatics'}]
    state, _=advance(PaperConversation(),'2 JEE Main Physics questions, +4/-1, custom blueprint',chapters)
    state, prompt=advance(state,'2 marks',chapters)
    assert '2 marks' in prompt and 'deduct 1 for incorrect answers' in prompt
    assert 'custom blueprint' in ' '.join(state.constraints)
    assert '+4' not in prompt


@pytest.mark.parametrize('constraint',['no numerical questions','not hard','without numerical questions'])
def test_negations_survive_structured_updates(constraint):
    state,prompt=advance(PaperConversation(),f'2 JEE Main Physics questions for 10 minutes, {constraint}',[])
    assert constraint.split(' questions')[0] in prompt
    from app.services.teacher_direct_request import direct_request
    assert direct_request(prompt,'jee_main',{'chapters':[]}) is None


def test_client_state_cannot_supply_ids_and_mapping_file_is_auditable(offline_studio):
    c, *_=offline_studio
    response=c.post('/api/teacher/papers/ai-create',json={'prompt':'10 minutes','conversation':{'slots':{'chapter_ids':'123'}},'request_key':str(uuid.uuid4())})
    assert response.status_code==422
    config=mappings()
    assert config['version']==1
    for entry in config['chapters']:
        assert set(entry)=={'subject','slugs','aliases'}
        assert len(entry['slugs'])>=1
        aliases=chapter_aliases([{'id':987,'subject':entry['subject'],'name':'Example','slug':entry['slugs'][0]}])
        for alias in entry['aliases']:
            from app.services.teacher_paper_language import phrase
            assert aliases[phrase(alias)][0]['id']==987


def test_corrected_subject_count_and_scores_are_used_in_the_actual_paper(offline_studio):
    c,*_=offline_studio
    result=send(c,'2 JEE Main Physics questions, hard difficulty, +4/-1, two sets')
    result=send(c,'Chemistry, 3 questions, balanced, 2 marks, single set',result['conversation'])
    result=send(c,'10 minutes',result['conversation'])
    assert result['state']=='ready',result
    paper=result['paper']
    assert len(paper['questions'])==3
    assert {q['subject'] for q in paper['questions']}=={'CHEM'}
    assert paper['settings']['marks_correct']==2 and paper['settings']['marks_wrong']==1
    assert len(result['downloads'])==1


@pytest.mark.parametrize('source',['PYQs','previous year questions'])
def test_year_and_pyq_requests_need_no_provider(offline_studio,source):
    c,factory,*_=offline_studio
    with factory() as db:
        db.get(m.Question,100).year=2025;db.commit()
    result=send(c,f'Create 2 JEE Main {source} from 2024 for 10 minutes')
    assert result['state']=='ready',result
    with factory() as db:
        assert all(db.get(m.Question,q['question_id']).year==2024 for q in result['paper']['questions'])


def test_reference_updates_do_not_reintroduce_old_duration():
    state,_=advance(PaperConversation(),'2 JEE Main Physics questions from 2024 for 10 minutes',[])
    state,prompt=advance(state,'20 minutes',[])
    assert '20 minutes' in prompt and '10 minutes' not in prompt


def test_unsupported_exam_can_be_corrected(offline_studio):
    c,*_=offline_studio
    result=send(c,'2 NEET Physics questions for 10 minutes')
    assert result['state']=='needs_details' and 'This bank supports' in result['question']
    result=send(c,'JEE Main',result['conversation'])
    assert result['state']=='ready',result


def test_term_normalization_is_idempotent():
    from app.services.teacher_direct_request import normalize
    text='BITSAT LR questions, maths and medium difficulty'
    assert normalize(normalize(text))==normalize(text)


def test_long_unrecognized_requirement_gets_followup_not_server_error(offline_studio):
    c,*_=offline_studio
    result=send(c,'Create 2 JEE Main Physics questions for 10 minutes, '+('unfamiliar ' * 200))
    assert result['state']=='needs_details' and 'too long' in result['question']
    assert not c.get('/api/teacher/papers').json()['papers']
