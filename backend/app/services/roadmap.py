"""Versioned weekly plans. Practice evidence is never converted to a national rank."""
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
import random
import os
import json
from datetime import date
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app import models
from app.services import predictor, admissions
from app.services.practice import choose_questions

DEFAULTS = {'goal_type': 'marks', 'weekly_hours': 5, 'target_marks': 150, 'college_choices': []}


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


def resolve_settings(db, user_id, stored, rows, now, validate=False):
    goal_type = stored.get('goal_type', 'marks')
    ids = stored.get('college_choices', []) if goal_type == 'colleges' else []
    programs = (db.query(models.PredictorProgram).options(selectinload(models.PredictorProgram.institute))
                .filter(models.PredictorProgram.id.in_(ids)).all()) if ids else []
    by_id = {p.id: p for p in programs}
    if validate and any(i not in by_id for i in ids):
        raise HTTPException(422, 'A selected college or branch is no longer available. Choose another option.')
    admission = {**admissions.DEFAULT, **stored.get('admission', {})}
    eligible_rows = admissions.cutoff_rows(db, admission) if ids else []
    choices = []
    for pid in ids:
        program = by_id.get(pid)
        if not program:
            continue
        options = [r for r in eligible_rows if r['program_id'] == pid and r['quota_resolved']]
        # Keep each category's own rank list; select the student's category benchmark first.
        preferred_seat = admission['category'] + (' (PwD)' if admission['pwd'] else '')
        options.sort(key=lambda r: (r['seat_type'] != preferred_seat, r['gender_pool'] != 'Gender-Neutral', -r['closing_rank']))
        cutoff = options[0] if options else None
        choices.append({'id': pid, 'institute': program.institute.name, 'program': program.name,
                        'rank': cutoff['closing_rank'] if cutoff else None,
                        'rank_list': cutoff['rank_list'] if cutoff else None,
                        'quota': cutoff['quota'] if cutoff else None,
                        'seat_type': cutoff['seat_type'] if cutoff else None,
                        'gender_pool': cutoff['gender_pool'] if cutoff else None,
                        'year': cutoff['reference_year'] if cutoff else None,
                        'round': cutoff['reference_round'] if cutoff else None})
    profile = db.get(models.StudentProfile, user_id)
    target_year = profile.target_year if profile else now.year + (now.month >= 6)
    # Operator-managed verified dates only. Never manufacture an official examination date.
    try:
        configured = json.loads(os.getenv('JEE_MAIN_EXAM_DATES', '{}')).get(str(target_year))
        exam_date = date.fromisoformat(configured) if configured else None
    except (ValueError, TypeError, AttributeError):
        exam_date = None
    if exam_date and exam_date < now.date():
        exam_date = None
    cutoff_date = now - timedelta(days=28)
    timed = [r for r in rows if r.answered_at >= cutoff_date and 0 < r.time_taken_sec <= 1800]
    # Practice time is only an observed lower bound, not total availability.
    hours = min(15, max(3, round(sum(r.time_taken_sec for r in timed) / 3600 / 4 * 2))) if len(timed) >= 10 else 5
    known_ranks = [c['rank'] for c in choices if c['rank'] is not None and c['rank_list'] == 'CRL']
    return {'admission': admission, 'goal_type': goal_type, 'target_marks': (stored.get('target_marks') or 150) if goal_type == 'marks' else None,
            'college_choices': ids, 'choices': choices, 'weekly_hours': hours,
            'pace_basis': 'Suggested from recent timed practice, including time for review.' if len(timed) >= 10 else 'A starting suggestion of five hours per week; adjusted as practice evidence grows.',
            'target_year': target_year, 'exam_date': exam_date.isoformat() if exam_date else None,
            'timeline_note': f'Exam date managed by JeeX for your {target_year} target year.' if exam_date else f'Official date not configured for {target_year}. We use a rolling 12-week planning horizon, not an assumed exam date.',
            'planning_until': (min(exam_date, now.date() + timedelta(weeks=12)) if exam_date else now.date() + timedelta(weeks=12)).isoformat(),
            'target_crl': min(known_ranks) if known_ranks else None}


def build_view(db, user_id, record=None, now=None):
    now = now or datetime.utcnow()
    rows = evidence(db, user_id)
    settings = resolve_settings(db, user_id, record.settings if record else DEFAULTS.copy(), rows, now)
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
    current = scenario(db, standing['score'])
    target = scenario(db, settings['target_marks'], settings.get('target_crl'))
    admission = settings['admission']
    cutoffs = admissions.cutoff_rows(db, admission)
    ranks = admissions.rank_inputs(admission, current['rank_low'], current['rank_high'])
    current['colleges'] = admissions.matches(cutoffs, ranks)
    if admission.get('crl'):
        current.update(rank_low=admission['crl'], rank_high=admission['crl'], basis='entered_crl')
    current['rank_inputs'] = {key: value[0] for key, value in ranks.items()}
    # Marks predict CRL only. Never reuse today's category rank as a future scenario.
    target['colleges'] = admissions.matches(cutoffs, {'CRL': (target['rank_low'], target['rank_high'])} if target['rank_low'] else {})
    if settings['goal_type'] == 'colleges':
        target['basis'] = 'college_cutoff'
        target['colleges'] = [{'institute': c['institute'], 'program': c['program'],
            'reference_year': c['year'], 'reference_round': c['round'], 'quota': c['quota'],
            'seat_type': c['seat_type'], 'gender_pool': c['gender_pool'], 'rank_list': c['rank_list'],
            'closing_rank': c['rank'], 'meets_conservative_estimate': True} for c in settings['choices'] if c['rank'] is not None]
    return {'saved': record is not None, 'settings': settings, 'plan': {**plan, 'tasks': tasks},
            'baseline': standing, 'subjects': subjects, 'checkpoints': record.checkpoints if record else [],
            'current': current, 'states': admissions.STATES, 'cutoff_preview': admissions.preview(cutoffs, admission),
            'target': target,
            'college_note': 'Historical JoSAA cutoffs, not admission guarantees. OPEN uses CRL; reserved and PwD pools use their respective ranks. Marks-based estimates support CRL only. NIT quotas use your Class XII state code of eligibility, not residence. Unmapped non-NIT state quotas and other admission eligibility checks are excluded.',
            'updated_at': now.isoformat()}
