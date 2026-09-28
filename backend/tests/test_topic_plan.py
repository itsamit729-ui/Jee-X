from datetime import datetime, timedelta
from types import SimpleNamespace
from test_roadmap import setup
from app import models as m
from app.services.topic_plan import build_topic_plan


def settings(hours=5):
    return {'weekly_hours': hours, 'planning_until': '2026-12-31', 'target_marks': 180, 'exam_date': None, 'timeline_note': 'Rolling horizon'}


def history(count=8, wrong=0, later=False, slow=False):
    now = datetime(2026, 9, 29)
    rows = []
    for i in range(count):
        day = now - timedelta(days=4 if i < 4 else 0)
        rows.append(SimpleNamespace(question_id=100+i, subtopic_id=1, answered_at=day, first_answered=day,
            outcome='wrong' if i < wrong else 'correct', time_taken_sec=240 if slow else 60, expected_time_sec=90))
    return sorted(rows, key=lambda r: r.answered_at, reverse=True)


def plan(factory, rows, hours=5):
    with factory() as db:
        return build_topic_plan(db, rows, settings(hours), {'score': None, 'recent': []}, datetime(2026, 9, 29))


def test_cold_start_names_real_topics_and_respects_budget(setup):
    client, factory, active = setup
    result = plan(factory, [], 1)
    assert len(result['topics']) == 3
    assert result['today']['topic'] == 'Topic PHY'
    assert result['today']['accuracy'] is None
    assert result['today']['purpose'] == 'diagnose'
    assert len(result['week']) == 1
    assert result['topic_minutes'] + result['reserved_minutes'] == 60
    assert result['score_range'] is None
    assert all(t['topic_id'] and t['chapter_id'] for t in result['topics'])


def test_repair_priority_and_repeats_do_not_pass_checkpoints(setup):
    _, factory, _ = setup
    rows = history(wrong=4)
    result = plan(factory, rows)
    assert result['today']['purpose'] == 'repair'
    assert not result['today']['foundation_met']
    for row in rows:
        row.answered_at += timedelta(hours=1)
        row.outcome = 'correct'
    repeated = plan(factory, rows)
    assert all(t['fresh_answers'] == 0 for t in repeated['topics'])
    assert all(not t['foundation_met'] for t in repeated['topics'])


def test_retention_and_speed_have_distinct_evidence(setup):
    _, factory, _ = setup
    known = next(t for t in plan(factory, history())['topics'] if t['topic_id'] == 1)
    assert known['foundation_met'] and known['retention_met'] and known['purpose'] == 'maintain'
    slow = next(t for t in plan(factory, history(slow=True))['topics'] if t['topic_id'] == 1)
    assert slow['purpose'] == 'fluency' and slow['timing_ratio'] > 1.3
    few = next(t for t in plan(factory, history(count=2, wrong=2))['topics'] if t['topic_id'] == 1)
    assert few['purpose'] == 'diagnose'  # Two mistakes cannot establish a weakness.


def test_exact_topic_launch_and_invalid_chapter_are_checked(setup):
    client, factory, _ = setup
    with factory() as db:
        db.add(m.Subtopic(id=99, chapter_id=1, name='Another physics topic', slug='another'))
        db.get(m.Question, 124).subtopic_id = 99
        db.commit()
    response = client.post('/api/subject-tests', json={'mode': 'recommended', 'subject_code': 'PHY', 'chapter_id': 1, 'topic_id': 99, 'duration_minutes': 15})
    assert response.status_code == 201, response.text
    assert [q['question_id'] for q in response.json()['questions']] == [124]
    assert response.json()['questions'][0]['recommendation']['reason']
    assert client.post('/api/subject-tests', json={'subject_code': 'CHEM', 'chapter_id': 2, 'topic_id': 99}).status_code == 422
    assert client.post('/api/subject-tests', json={'assessment': True, 'topic_id': 99}).status_code == 422


def test_available_hours_are_saved_and_validated(setup):
    client, _, _ = setup
    response = client.put('/api/roadmap', json={'goal_type': 'marks', 'target_marks': 180, 'available_hours': 2})
    assert response.status_code == 200, response.text
    assert response.json()['settings']['weekly_hours'] == 2
    assert client.get('/api/roadmap/journey').json()['topic_plan']['weekly_hours'] == 2
    assert client.put('/api/roadmap', json={'available_hours': 0}).status_code == 422


def test_known_prerequisites_precede_dependent_topics(setup):
    _, factory, _ = setup
    with factory() as db:
        db.get(m.Chapter, 1).name = 'Applications of Derivatives'
        db.add(m.Chapter(id=99, subject_id=1, name='Continuity and Differentiability', slug='prerequisite', class_level='12'))
        db.add(m.Subtopic(id=99, chapter_id=99, name='Continuity', slug='continuity'))
        db.get(m.Question, 124).subtopic_id = 99
        db.commit()
    result = plan(factory, history(wrong=4))
    ids = [t['topic_id'] for t in result['topics']]
    assert ids.index(99) < ids.index(1)
    assert 'Continuity' in next(t for t in result['topics'] if t['topic_id'] == 1)['prerequisites']
