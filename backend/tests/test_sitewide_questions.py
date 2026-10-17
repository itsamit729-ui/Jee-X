"""Imported answer-only questions remain usable outside the PYQ archive."""
from datetime import date
from test_roadmap import setup
from app import models
from app.services.question_catalog import candidate_query
from app.routers.daily_question import _pick_question
from app.routers.subjects import list_subjects
from app.services.scenarios import choose_questions, grade, public_question


def test_answer_only_bank_reaches_practice_baseline_roadmap_and_daily(setup):
    client, factory, _ = setup
    with factory() as db:
        db.add(models.StudentProfile(user_id=1,dob=date(2006,1,1),class_12_year=2027,target_year=2027))
        for q in db.query(models.Question):
            q.solution = ''
            q.source_type = 'pyq'
            q.exam = 'jee_main'
            q.year = 2025
        db.get(models.Question, 100).status = 'draft'
        db.get(models.Question, 101).exam = 'mht_cet'
        for o in db.get(models.Question, 102).options:
            o.is_correct = False
        db.commit()
        assert candidate_query(db).count() == 72
        assert sum(s.published_question_count for s in list_subjects(db)) == 72
        assert _pick_question(db, models.User(id=1)).id not in {100, 101, 102}
    r = client.post('/api/subject-tests', json={'mode':'topic','subject_code':'PHY','count':30})
    assert r.status_code == 201, r.text
    picked = r.json()['questions']
    assert {q['question_id'] for q in picked} == set(range(103,125))
    assert any(q['type'] == 'numerical' for q in picked)
    assert all('solution' not in q and 'answer_min' not in q for q in picked)
    assert all('is_correct' not in o for q in picked for o in q['options'])
    # Restore the three held fixtures: a full baseline requires 20 MCQs
    # and 5 numerical questions per subject, without relaxing that balance.
    with factory() as db:
        db.get(models.Question, 100).status = 'published'
        db.get(models.Question, 101).exam = 'jee_main'
        db.get(models.Question, 102).options[0].is_correct = True
        db.commit()
    baseline = client.post('/api/subject-tests', json={'assessment':True})
    assert baseline.status_code == 201, baseline.text
    assert len(baseline.json()['questions']) == 75
    mock = client.post('/api/subject-tests', json={'full_mock':True})
    assert mock.status_code == 201, mock.text
    paper = mock.json()
    assert paper['is_mock'] and paper['duration_sec'] == 10800
    assert paper['title'] == 'JEE Main full mock'
    assert len(paper['questions']) == 75
    assert all(q['marks_wrong'] == 1 for q in paper['questions'])
    assert {q['subject_code'] for q in paper['questions']} == {'PHY','CHEM','MATH'}
    answers = [{'question_id':q['question_id'],'numeric_answer':2} if q['type']=='numerical' else
               {'question_id':q['question_id'],'option_ids':[q['options'][0]['id']]} for q in paper['questions']]
    graded = client.post(f"/api/subject-tests/attempts/{paper['attempt_id']}/submit", json={'answers':answers})
    assert graded.status_code == 200, graded.text
    assert graded.json()['score'] == 300
    # Taking a mock must not exhaust the feature once every question is seen.
    assert client.post('/api/subject-tests', json={'full_mock':True}).status_code == 201
    # Baselines still require fresh evidence rather than silently reusing answers.
    assert client.post('/api/subject-tests', json={'assessment':True}).status_code == 409
    assert client.post('/api/subject-tests', json={'full_mock':True,'subject_code':'PHY'}).status_code == 422
    assert client.post('/api/subject-tests', json={'full_mock':True,'assessment':True}).status_code == 422
    roadmap = client.get('/api/roadmap')
    assert roadmap.status_code == 200, roadmap.text
    # Roadmap is still actionable when no question has a worked explanation.
    assert roadmap.json()['journey']['topic_plan']['topics']


def test_scenarios_use_answer_only_decimal_questions_and_hide_keys(setup):
    _, factory, _ = setup
    with factory() as db:
        for q in db.query(models.Question):
            q.solution = ''
            q.exam = 'jee_main'
            if q.type == 'numerical':
                q.answer_min = 1.25
                q.answer_max = 1.5
        db.commit()
        questions = choose_questions(db, 30)
    numeric = next(q for q in questions if q['id'].startswith('bank:') and q['type']=='numerical')
    assert 'answer_min' not in public_question(numeric) and 'solution' not in public_question(numeric)
    result = grade([numeric], {numeric['id']:{'numeric_answer':1.4}})['questions'][0]
    assert result['outcome'] == 'correct'
    assert (result['answer_min'],result['answer_max']) == (1.25,1.5)


def test_daily_sampling_can_choose_new_ids_while_excluding_drafts_and_other_exams(setup,monkeypatch):
    from app.routers import daily_question
    _,factory,_=setup
    monkeypatch.setattr(daily_question.random,'choice',lambda ids:max(ids))
    with factory() as db:
        db.query(models.Question).update({'status':'draft'})
        db.get(models.Question,100).status='published'
        for qid,exam,status in [(15000,'jee_main','published'),(15001,'mht_cet','published'),(15002,'jee_main','draft')]:
            db.add(models.Question(id=qid,ref=f'NEW-PUBLICATION-{qid}',subtopic_id=1,type='numerical',
                stem='New publication fixture',solution='',difficulty=3,expected_time_sec=120,
                answer_min=1.5,answer_max=1.5,source_type='pyq',status=status,exam=exam,year=2019,
                version=1,content_hash=str(qid)))
        db.commit()
        assert daily_question._pick_question(db,models.User(id=1)).id==15000
