"""Versioned weekly plans. Practice evidence is never converted to a national rank."""
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
import random
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app import models
from app.services import predictor
from app.services.practice import choose_questions

DEFAULTS = {'weekly_hours': 5, 'target_marks': 150, 'exam_date': None, 'target_college': '', 'current_crl': None, 'target_crl': None}


def assessment_questions(candidates, subject_ids, seen):
    """Fresh, chapter-diverse assessment, independent of adaptive weakness weights."""
    chosen = []
    rng = random.SystemRandom()
    for code in ('PHY', 'CHEM', 'MATH'):
        for kind, count in (('single_correct', 20), ('numerical', 5)):
            pool = [q for q in candidates if q.subject_id == subject_ids.get(code)
                    and q.type == kind and q.id not in seen]
            if len(pool) < count:
                raise HTTPException(409, 'Not enough fresh, complete questions for a balanced baseline yet. Continue topic practice; your roadmap remains available.')
            rng.shuffle(pool)
            chapters = defaultdict(int)
            difficulties = defaultdict(int)
            for _ in range(count):
                q = min(pool, key=lambda q: (chapters[q.chapter_id], difficulties[(q.difficulty - 1) // 3]))
                chosen.append((q.id, None))
                pool.remove(q)
                chapters[q.chapter_id] += 1
                difficulties[(q.difficulty - 1) // 3] += 1
    return chosen


def evidence(db, user_id):
    first = (db.query(models.QuestionResponse.question_id,
                     func.min(models.QuestionResponse.answered_at).label('first_answered'))
             .join(models.TestAttempt, models.TestAttempt.id == models.QuestionResponse.attempt_id)
             .filter(models.QuestionResponse.user_id == user_id, models.TestAttempt.user_id == user_id,
                     models.TestAttempt.submitted_at.isnot(None))
             .group_by(models.QuestionResponse.question_id).subquery())
    return (db.query(models.QuestionResponse.question_id, models.QuestionResponse.outcome,
                     models.QuestionResponse.time_taken_sec, models.QuestionResponse.answered_at,
                     models.Question.subtopic_id, models.Question.difficulty, models.Question.expected_time_sec,
                     models.Subtopic.name.label('topic'), models.Chapter.id.label('chapter_id'),
                     models.Chapter.name.label('chapter'), models.Subject.code.label('subject'), first.c.first_answered)
            .join(models.Question, models.Question.id == models.QuestionResponse.question_id)
            .join(models.Subtopic, models.Subtopic.id == models.Question.subtopic_id)
            .join(models.Chapter, models.Chapter.id == models.Subtopic.chapter_id)
            .join(models.Subject, models.Subject.id == models.Chapter.subject_id)
            .join(models.TestAttempt, models.TestAttempt.id == models.QuestionResponse.attempt_id)
            .join(first, first.c.question_id == models.QuestionResponse.question_id)
            .filter(models.QuestionResponse.user_id == user_id, models.TestAttempt.user_id == user_id,
                    models.TestAttempt.submitted_at.isnot(None), models.Chapter.in_main.is_(True))
            .order_by(models.QuestionResponse.answered_at.desc(), models.QuestionResponse.id.desc()).limit(500).all())


def make_plan(rows, settings, now):
    from types import SimpleNamespace
    topics = {r.subtopic_id: r for r in reversed(rows)}
    candidates = [SimpleNamespace(id=-r.subtopic_id, subtopic_id=r.subtopic_id, topic=r.topic,
                    difficulty=r.difficulty) for r in topics.values()]
    ranked = choose_questions(candidates, rows, len(candidates), now=now)
    tasks, used = [], set()
    max_tasks = min(3, settings['weekly_hours'])
    for qid, reason in ranked:
        r = topics[-qid]
        if r.chapter_id in used:
            continue
        used.add(r.chapter_id)
        tasks.append({'chapter_id': r.chapter_id, 'subject': r.subject, 'title': r.chapter,
                      'reason': reason['reason'], 'goal': reason['learning_goal'], 'topic': r.topic})
        if len(tasks) == max_tasks:
            break
    if not tasks:
        tasks = [{'chapter_id': None, 'subject': code, 'title': name,
                  'reason': 'We need your own answers before choosing a weak chapter.',
                  'goal': 'Try a short session, then review the explanations.', 'topic': None}
                 for code, name in [('PHY', 'Explore Physics'), ('CHEM', 'Explore Chemistry'), ('MATH', 'Explore Mathematics')]]
    # Short repeatable blocks; leave the remaining weekly time for review/self study.
    tasks = tasks[:max_tasks]
    budget = settings['weekly_hours'] * 60
    per_task = min(90, (budget // len(tasks) // 15) * 15)
    for task in tasks:
        task['minutes'] = per_task
        task['practice_minutes'] = 15
        task['review_minutes'] = max(0, per_task - 30)
        task['checkpoint'] = 'Answer 5 fresh questions with at least 4 correct. This is a checkpoint, not proof of mastery.'
    return {'created_at': now.isoformat(), 'review_at': (now + timedelta(days=7)).isoformat(), 'tasks': tasks}


def task_progress(task, rows, since):
    unique = {}
    for row in rows:
        if row.subject != task['subject'] or (task['chapter_id'] and row.chapter_id != task['chapter_id']):
            continue
        if row.first_answered < since or row.outcome not in ('correct', 'wrong'):
            continue
        unique.setdefault(row.question_id, row)
    samples = list(unique.values())[:5]
    correct = sum(r.outcome == 'correct' for r in samples)
    return {'answered': len(samples), 'correct': correct, 'met': len(samples) == 5 and correct >= 4}


def baseline(db, user_id, now):
    attempts = (db.query(models.TestAttempt).join(models.Test)
        .options(selectinload(models.TestAttempt.responses),
                 selectinload(models.TestAttempt.test).selectinload(models.Test.test_questions))
        .filter(models.TestAttempt.user_id == user_id, models.Test.generated_for_user_id == user_id,
                models.Test.title == 'Roadmap baseline assessment', models.Test.kind == 'mock',
                models.TestAttempt.submitted_at.isnot(None))
        .order_by(models.TestAttempt.submitted_at.desc()).limit(6).all())
    scores = []
    for a in attempts:
        questions = a.test.test_questions
        if len(questions) != 75 or len(a.responses) != 75 or any(q.marks_correct != 4 or q.marks_wrong != 1 for q in questions):
            continue
        if (a.submitted_at.replace(tzinfo=None) - a.started_at.replace(tzinfo=None)).total_seconds() > 10860:
            continue
        scores.append({'attempt_id': a.id, 'score': sum(r.marks_awarded for r in a.responses), 'date': a.submitted_at.isoformat()})
    recent = [x for x in scores if datetime.fromisoformat(x['date']).replace(tzinfo=None) >= now - timedelta(days=45)][:3]
    return {'score': median([x['score'] for x in recent]) if recent else None, 'count': len(recent),
            'recent': scores, 'label': 'Median of recent balanced assessments' if recent else 'Build your baseline',
            'note': 'Server-scored, fresh questions; syllabus-balanced by subject, not a calibrated official paper. Assessments older than 45 days are excluded.'}


def scenario(db, marks=None, crl=None):
    result = {'marks': marks, 'rank_low': crl, 'rank_high': crl, 'percentile_low': None,
              'percentile_high': None, 'reference_year': None, 'colleges': [],
              'basis': 'entered_crl' if crl else 'insufficient_data'}
    if crl is None and marks is not None:
        year = predictor._latest_year(db, models.PredictorMainMarksEstimate)
        rank_year = predictor._latest_year(db, models.PredictorMainPercentileAnchor, rank_list='CRL')
        if year and rank_year:
            p = predictor.estimate_percentile(db, marks, year)
            # Do not flatten above-range values into a seemingly exact forecast.
            if p['basis'] == 'interpolated':
                r = predictor.estimate_rank(db, p['percentile_low'], p['percentile_high'], rank_year)
                if r['basis'] == 'interpolated':
                    result.update(p, **{'rank_low': r['rank_low'], 'rank_high': r['rank_high'],
                                      'reference_year': year, 'rank_reference_year': rank_year})
    if result['rank_low'] is not None:
        # Institute-state mapping and category ranks are unavailable: do not guess HS/OS eligibility.
        result['colleges'] = predictor.match_colleges(db, result['rank_low'], result['rank_high'], quotas=('AI',))[:6]
    return result


def build_view(db, user_id, record=None, now=None):
    now = now or datetime.utcnow()
    settings = record.settings if record else DEFAULTS.copy()
    rows = evidence(db, user_id)
    plan = record.plan if record else make_plan(rows, settings, now)
    since = datetime.fromisoformat(plan['created_at'])
    tasks = [{**task, 'progress': task_progress(task, rows, since)} for task in plan['tasks']]
    standing = baseline(db, user_id, now)
    by_subject = defaultdict(dict)
    for r in rows:
        if r.outcome in ('correct', 'wrong'):
            by_subject[r.subject].setdefault(r.question_id, r.outcome)
    subjects = [{'code': code, 'answered': len(items), 'accuracy': round(100 * sum(v == 'correct' for v in items.values()) / len(items))}
                for code, items in by_subject.items() if items]
    return {'saved': record is not None, 'settings': settings, 'plan': {**plan, 'tasks': tasks},
            'baseline': standing, 'subjects': subjects, 'checkpoints': record.checkpoints if record else [],
            'current': scenario(db, standing['score'], settings.get('current_crl')),
            'target': scenario(db, settings['target_marks'], settings.get('target_crl')),
            'college_note': 'Historical JEE Main OPEN / CRL, All India, Gender-Neutral seats only. Home-state, other-state and category-specific pools are not included. Eligibility is not verified; these are comparisons, not admission offers.',
            'updated_at': now.isoformat()}
