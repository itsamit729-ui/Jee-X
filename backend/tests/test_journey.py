import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from app import models
from app.services.journey import evaluate, load_journey
from app.services.practice import choose_questions
from test_roadmap import setup

NOW = datetime(2026, 9, 28, 10)
SETTINGS = {'goal_type': 'marks', 'target_marks': 180, 'target_year': 2027}
EMPTY = {'recent': [], 'count': 0, 'score': None}


def rows(correct=True, repeated=False, old=False):
    result = []
    for sid, subject in enumerate(('PHY', 'CHEM', 'MATH'), 1):
        for i in range(8):
            at = NOW - timedelta(days=40 if old else (4 if i < 4 else 0))
            result.append(SimpleNamespace(question_id=sid*100+i, chapter_id=sid, chapter=f'Chapter {subject}',
                subtopic_id=sid, topic=f'Topic {subject}', subject=subject, answered_at=at,
                first_answered=at-timedelta(days=60) if repeated else at, outcome='correct' if correct else 'wrong',
                time_taken_sec=60, expected_time_sec=90, difficulty=5))
    return sorted(result, key=lambda r:r.answered_at, reverse=True)


def test_fresh_independent_evidence_and_expiry():
    initial = evaluate([], SETTINGS, EMPTY, NOW)
    assert initial['active_id'] == 'baseline' and initial['standing']['range'] is None
    repeated = evaluate(rows(repeated=True), SETTINGS, EMPTY, NOW)
    assert repeated['evidence']['fresh_answers'] == 0
    result = evaluate(rows(), SETTINGS, EMPTY, NOW)
    met = {m['id'] for m in result['milestones'] if m['met']}
    assert met == {'foundation', 'application', 'fluency', 'retention'}
    assert result['active_id'] == 'baseline'  # practice never manufactures an exam score
    assert result['standing']['score'] is None
    stale = evaluate(rows(), SETTINGS, EMPTY, NOW+timedelta(days=50))
    assert stale['evidence']['fresh_answers'] == 0
    mixed = rows()
    for row in mixed:
        if row.answered_at < NOW:
            row.outcome = 'wrong'
    assert not next(m for m in evaluate(mixed, SETTINGS, EMPTY, NOW)['milestones'] if m['id'] == 'retention')['met']
    same_day = rows(old=True)
    assert not next(m for m in evaluate(same_day, SETTINGS, EMPTY, NOW)['milestones'] if m['id'] == 'foundation')['met']


def test_goal_requires_consistency_and_college_ranks_are_not_guessed():
    recent = [{'score': score, 'date': (NOW-timedelta(days=i*2)).isoformat()} for i, score in enumerate([181, 190, 185])]
    standing = {'recent': recent, 'count': 3, 'score': 185}
    result = evaluate(rows(), SETTINGS, standing, NOW)
    assert result['standing']['range'] == [181, 190]
    assert result['milestones'][-1]['met']
    recent[0]['score'] = 150
    assert not evaluate(rows(), SETTINGS, standing, NOW)['milestones'][-1]['met']
    for item in recent: item['date'] = NOW.isoformat()
    assert evaluate(rows(), SETTINGS, standing, NOW)['standing']['range'] is None
    college = evaluate(rows(), {**SETTINGS, 'goal_type':'colleges', 'target_marks':None}, standing, NOW)
    assert college['standing']['gap'] is None and not college['milestones'][-1]['met']


def test_latest_misses_adjust_focus_without_one_answer_claiming_mastery():
    result = evaluate(rows(correct=False), SETTINGS, EMPTY, NOW)
    assert all(s['reason_code'] == 'revisit_weak_concept' for s in result['focus'])
    assert all(not m['met'] for m in result['milestones'])
    single = evaluate(rows()[:1], SETTINGS, EMPTY, NOW)
    assert single['focus'][0]['reason_code'] == 'build_evidence'


def test_recommendations_link_to_plan_and_keep_exploration():
    pool = [SimpleNamespace(id=i, chapter_id=1 if i<=8 else 2, subtopic_id=i, topic=f'Topic {i}', difficulty=3) for i in range(1,17)]
    selected = choose_questions(pool, [], 8, focus_chapters={2}, milestone={'id':'foundation','title':'Foundations'}, now=NOW)
    assert selected[0][0] > 8
    assert any(qid <= 8 for qid, _ in selected)
    assert all(reason['milestone_id'] == 'foundation' for _, reason in selected)


def test_snapshot_isolation_idempotency_and_summary_scores_excluded(setup):
    client, factory, active = setup
    saved = client.put('/api/roadmap', json={'target_marks':180}).json()
    first = client.get('/api/roadmap/journey').json()
    assert first == client.get('/api/roadmap/journey').json()
    with factory() as db:
        record = db.get(models.StudentRoadmap, 1)
        assert record.plan['journey']['goal_label'] == '180 / 300 marks'
        db.add(models.Test(id=800, title='Client summary', kind='mock', pattern='jee_main', duration_sec=10800))
        db.flush()
        db.add(models.TestAttempt(user_id=1, test_id=800, submitted_at=datetime.utcnow(), score=280))
        db.commit()
    updated = client.get('/api/roadmap/journey').json()
    assert updated['standing']['score'] is None
    assert any('summary-only' in s for s in updated['changes'])
    assert len(updated['history']) == len(first['history'])+1
    assert updated == client.get('/api/roadmap/journey').json()
    active[0] = 2
    other = client.get('/api/roadmap/journey').json()
    assert not other['saved'] and other['history'] == []
    assert other['last_attempt_id'] is None


def test_weekly_refresh_and_goal_change_keep_skill_achievements(setup):
    client, factory, _ = setup
    client.put('/api/roadmap', json={'target_marks':180})
    with factory() as db:
        record = db.get(models.StudentRoadmap, 1)
        plan = dict(record.plan)
        plan['created_at'] = (datetime.utcnow()-timedelta(days=8)).isoformat()
        plan['journey']['achievements'] = {'foundation': NOW.isoformat(), 'goal': NOW.isoformat()}
        record.plan = plan
        db.commit()
    value = client.get('/api/roadmap/journey').json()
    assert any('refreshed' in s for s in value['changes'])
    assert next(m for m in value['milestones'] if m['id']=='foundation')['status'] == 'recheck'
    changed = client.put('/api/roadmap', json={'target_marks':200}).json()['journey']
    assert changed['achievements'].get('foundation')
    assert 'goal' not in changed['achievements']


def test_three_fresh_sessions_refresh_weekly_plan(setup):
    client, factory, _ = setup
    client.put('/api/roadmap', json={})
    initial = client.get('/api/roadmap').json()['plan']['created_at']
    with factory() as db:
        db.add(models.Test(id=900, title='Practice', kind='chapter', pattern='jee_main', duration_sec=900))
        db.flush()
        for i in range(3):
            attempt = models.TestAttempt(user_id=1, test_id=900, attempt_number=i+1, submitted_at=datetime.utcnow()+timedelta(seconds=1))
            db.add(attempt); db.flush()
            db.add(models.QuestionResponse(attempt_id=attempt.id, user_id=1, question_id=100+i, question_version=1,
                outcome='wrong', time_taken_sec=60, marks_awarded=-1))
        db.commit()
    value = client.get('/api/roadmap').json()
    assert value['plan']['created_at'] != initial
    assert any('refreshed' in s for s in value['journey']['changes'])
    assert len(value['checkpoints']) == 1
    assert value['journey']['evidence']['fresh_answers'] == 3
