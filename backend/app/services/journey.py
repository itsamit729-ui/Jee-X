"""Shared milestone evidence, persisted revisions, and next-action selection.

Thresholds are transparent product heuristics, not a calibrated JEE score model.
Only first exposures within 45 days qualify for skill milestones.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
from app import models

SUBJECTS = ('PHY', 'CHEM', 'MATH')


def naive(value):
    return value.replace(tzinfo=None)


def summarize(rows, now):
    fresh, seen = [], set()
    for r in rows:
        if r.question_id in seen or naive(r.answered_at) < now - timedelta(days=45):
            continue
        # A repeat, including a correction after seeing a solution, cannot earn mastery.
        if naive(r.answered_at) != naive(r.first_answered):
            continue
        seen.add(r.question_id)
        if r.outcome in ('correct', 'wrong'):
            fresh.append(r)
    chapters = defaultdict(list)
    for r in fresh:
        chapters[r.chapter_id].append(r)
    skills = []
    for cid, items in chapters.items():
        correct = [r for r in items if r.outcome == 'correct']
        days = {naive(r.answered_at).date() for r in items}
        timed = [r for r in correct if 0 < r.time_taken_sec <= 1800 and r.expected_time_sec > 0]
        start = min(naive(r.answered_at) for r in items)
        later = [r for r in items if naive(r.answered_at) >= start + timedelta(days=3)]
        accuracy = round(100 * len(correct) / len(items))
        established = len(items) >= 8 and len(days) >= 2
        retained = established and accuracy >= 70 and len(later) >= 4 and sum(r.outcome == 'correct' for r in later) / len(later) >= .75
        ratio = median([r.time_taken_sec / r.expected_time_sec for r in timed]) if len(timed) >= 6 else None
        last = max(naive(r.answered_at) for r in items)
        reason = 'Build a clearer picture with fresh questions.'
        mode = 'build_evidence'
        if established and accuracy < 70:
            mode, reason = 'revisit_weak_concept', f'{accuracy}% accuracy across {len(items)} fresh answers: strengthen the concepts before increasing difficulty.'
        elif (now - last).days >= 7:
            mode, reason = 'spaced_revision', 'Revisit this chapter after a gap to check what you retain.'
        elif established and ratio and ratio > 1.3:
            mode, reason = 'build_fluency', 'Correct answers are taking longer than the question time guides. Practise an efficient approach.'
        elif established and accuracy >= 70:
            mode, reason = 'stretch', 'Your foundation evidence is stronger. Try unfamiliar applications and mixed practice.'
        skills.append({'chapter_id': cid, 'title': items[0].chapter, 'subject': items[0].subject,
                       'answered': len(items), 'accuracy': accuracy, 'days': len(days),
                       'established': established, 'foundation': established and accuracy >= 70,
                       'retained': retained, 'reason_code': mode, 'reason': reason,
                       'last_practised': last.isoformat()})
    priority = {'revisit_weak_concept': 0, 'spaced_revision': 1, 'build_fluency': 2, 'build_evidence': 3, 'stretch': 4}
    skills.sort(key=lambda s: (priority[s['reason_code']], s['accuracy'], s['chapter_id']))
    medium = [r for r in fresh if r.difficulty >= 4]
    timed = [r for r in fresh if r.outcome == 'correct' and 0 < r.time_taken_sec <= 1800 and r.expected_time_sec > 0]
    return fresh, skills, medium, timed


def evaluate(rows, settings, standing, now):
    fresh, skills, medium, timed = summarize(rows, now)
    recent = [s for s in standing['recent'] if naive(datetime.fromisoformat(s['date'])) >= now - timedelta(days=45)][:3]
    assessment_days = len({s['date'][:10] for s in recent})
    foundations = [s for s in skills if s['foundation']]
    retained = [s for s in skills if s['retained']]
    application = (len(medium) >= 12 and len({r.chapter_id for r in medium}) >= 3
                   and len({naive(r.answered_at).date() for r in medium}) >= 2
                   and sum(r.outcome == 'correct' for r in medium) / len(medium) >= .7)
    fluency = (len(timed) >= 12 and len({r.chapter_id for r in timed}) >= 3
               and len({naive(r.answered_at).date() for r in timed}) >= 2
               and median([r.time_taken_sec / r.expected_time_sec for r in timed]) <= 1.3)
    consistent = len(recent) >= 3 and assessment_days >= 3
    marks_goal = settings['goal_type'] == 'marks'
    target = settings.get('target_marks')
    target_met = marks_goal and consistent and all(s['score'] >= target for s in recent)
    specs = [
        ('baseline', 'Find your starting point', standing['count'] >= 1, f"{standing['count']} / 1 balanced assessments", 'Complete a fresh, balanced three-subject assessment.', 'Establish a score baseline before estimating the distance to your goal.'),
        ('foundation', 'Build reliable foundations', len(foundations) >= 3 and len({s['subject'] for s in foundations}) == 3,
         f'{len(foundations)} chapters with foundation evidence', 'At least one chapter in each subject: 8 fresh answers, 70% accuracy, on at least 2 days.', 'Secure a starting set of reliable concepts; continue expanding syllabus coverage.'),
        ('application', 'Apply concepts independently', application, f'{len(medium)} / 12 fresh application answers', '12 fresh questions at difficulty 4 or above, 70% accuracy, across 3 chapters and 2 days.', 'Move from familiar methods to unfamiliar applications.'),
        ('fluency', 'Make correct answers faster', fluency, f'{len(timed)} / 12 timed correct answers', '12 correct answers across 3 chapters and 2 days; median active time within 1.3× the question guide.', 'Improve pacing while retaining accuracy; active practice time is a guide, not an exam simulation.'),
        ('retention', 'Keep what you have learned', len(retained) >= 3 and len({s['subject'] for s in retained}) == 3,
         f'{len(retained)} chapters with retention evidence', 'One chapter per subject: foundation sample plus 4 fresh answers at least 3 days later, with 75% accuracy.', 'Check that understanding survives beyond the original practice session.'),
        ('mocks', 'Build full-test consistency', consistent, f'{len(recent)} / 3 recent assessments · {assessment_days} distinct days', 'Complete 3 balanced assessments on separate days within 45 days.', 'Observe your score range, pacing and question selection across complete tests.'),
        ('goal', 'Sustain your target score' if marks_goal else 'Review your admission benchmarks', target_met,
         f"{sum(s['score'] >= target for s in recent)} / 3 assessments at target" if marks_goal else 'College and branch benchmarks in your outlook',
         f'At least {target} / 300 in each of 3 recent balanced assessments on separate days.' if marks_goal else 'Compare your corresponding rank list and eligibility against each choice’s historical cutoff.',
         'Demonstrate your goal repeatedly, then maintain revision through exam day.' if marks_goal else 'Mock scores cannot establish a reserved-category rank or guarantee admission.'),
    ]
    active = next((s[0] for s in specs if not s[2]), 'goal')
    milestones = []
    for index, (key, title, met, progress, requirement, purpose) in enumerate(specs):
        milestones.append({'id': key, 'number': index + 1, 'title': title, 'met': bool(met),
                           'status': 'met' if met else 'current' if key == active else 'upcoming',
                           'progress': progress, 'requirement': requirement, 'purpose': purpose})
    goal_label = f'{target} / 300 marks' if marks_goal else 'Your college & branch choices'
    enough = len(fresh) >= 30 and all(sum(r.subject == s for r in fresh) >= 8 for s in SUBJECTS) and len(skills) >= 6
    return {'version': 2, 'goal_label': goal_label, 'active_id': active, 'milestones': milestones,
            'destinations': settings.get('choices', []),
            'assessment_history': list(reversed(standing['recent'])),
            'foundation_chapters': [s['chapter_id'] for s in foundations],
            'focus': skills[:3], 'evidence': {'fresh_answers': len(fresh), 'chapters': len(skills),
                'subjects': len({r.subject for r in fresh}), 'assessments': len(recent),
                'level': 'Broader practice evidence' if enough else 'Building your practice evidence'},
            'standing': {'score': standing['score'], 'target': target,
                        'gap': max(0, target - standing['score']) if marks_goal and standing['score'] is not None else None,
                        'range': [min(s['score'] for s in recent), max(s['score'] for s in recent)] if consistent else None,
                        'label': 'Target demonstrated in recent assessments' if target_met else 'More assessment evidence needed' if not consistent else 'Working toward your target' if marks_goal else 'Compare historical admission benchmarks'},
            'exam_date': settings.get('exam_date'), 'target_year': settings.get('target_year'),
            'timeline_note': 'Next 7 days are actionable. Later milestones adapt to your results; their completion dates are not promises.',
            'evidence_note': 'Milestones use first-exposure answers from the last 45 days and transparent starting thresholds. The recent response window is capped at 500 records. They do not certify syllabus mastery or predict a future score. Full assessments are subject-balanced, not calibrated official papers.',
            'updated_at': now.isoformat()}


def load_journey(db, user_id, now=None, context=None):
    """Reconcile on read, including results from every submission route, without
    adding work to grading. Student lock keeps simultaneous tabs idempotent.
    Existing plan JSON holds the snapshot; no schema migration is needed.
    """
    from app.services import roadmap
    now = now or datetime.utcnow()
    db.query(models.User).filter_by(id=user_id).with_for_update().first()
    record = db.query(models.StudentRoadmap).filter_by(user_id=user_id).with_for_update().populate_existing().first()
    rows = roadmap.evidence(db, user_id)
    settings = roadmap.resolve_settings(db, user_id, record.settings if record else roadmap.DEFAULTS.copy(), rows, now)
    standing = roadmap.baseline(db, user_id, now)
    if context is not None:
        context.update(rows=rows, settings=settings, standing=standing)
    result = evaluate(rows, settings, standing, now)
    from app.services.topic_plan import build_topic_plan
    result["topic_plan"] = build_topic_plan(db, rows, settings, standing, now)
    latest = db.query(models.TestAttempt).filter(models.TestAttempt.user_id == user_id,
              models.TestAttempt.submitted_at.isnot(None)).order_by(models.TestAttempt.submitted_at.desc(), models.TestAttempt.id.desc()).first()
    result['saved'] = record is not None
    old = record.plan.get('journey', {}) if record else {}
    achievements = dict(old.get('achievements', {}))
    if old.get('goal_label') != result['goal_label']:
        achievements.pop('goal', None)
    for m in result['milestones']:
        if m['met']:
            achievements.setdefault(m['id'], now.isoformat())
        m['first_met_at'] = achievements.get(m['id'])
        if m['first_met_at'] and not m['met']:
            m['status'] = 'recheck'
    result['achievements'] = achievements
    # Compare observed snapshots, never extrapolate future scores from practice.
    result['starting_snapshot'] = old.get('starting_snapshot') or {
        'date': now.isoformat(), 'milestones_met': sum(m['met'] for m in result['milestones']),
        'foundation_chapters': result['foundation_chapters']}
    current_foundations = set(result['foundation_chapters'])
    result['new_foundation_chapters'] = len(current_foundations - set(result['starting_snapshot']['foundation_chapters']))
    result['last_attempt_id'] = latest.id if latest else None
    new_attempt = result['last_attempt_id'] != old.get('last_attempt_id')
    messages = []
    if new_attempt:
        previous_count = old.get('evidence', {}).get('fresh_answers', 0)
        added = result['evidence']['fresh_answers'] - previous_count
        messages.append(f'{added} additional fresh answers now inform your milestones.' if added > 0 and old else f"Your plan now uses {result['evidence']['fresh_answers']} fresh answers." if added > 0 else 'Your latest test is saved. Repeated answers and summary-only scores do not add fresh milestone evidence.')
        if old.get('active_id') and old['active_id'] != result['active_id']:
            messages.append('Your next milestone has changed based on the updated evidence.')
        else:
            messages.append('Your main milestone stays steady while more evidence accumulates.')
        previous_score = old.get('standing', {}).get('score')
        if result['standing']['score'] is not None and result['standing']['score'] != previous_score:
            messages.append(f"Your assessed baseline is now {result['standing']['score']} / 300.")
        previous_met = {m['id'] for m in old.get('milestones', []) if m['met']}
        newly_met = [m['title'] for m in result['milestones'] if m['met'] and m['id'] not in previous_met]
        if newly_met:
            messages.append('New evidence requirements met: ' + ', '.join(newly_met) + '.')
    elif old.get('changes'):
        messages = list(old['changes'])
    else:
        messages = ['Your first plan will adapt as you complete fresh practice and balanced assessments.']
    if old.get('goal_label') and old['goal_label'] != result['goal_label']:
        messages.append('Your goal has changed. Skill achievements are retained; target readiness is checked against the new goal.')
    if not new_attempt and any(m['status'] == 'recheck' and next((p['met'] for p in old.get('milestones', []) if p['id'] == m['id']), False) for m in result['milestones']):
        messages = ['Some earlier evidence has aged beyond the recent window. Recheck these milestones to confirm you are still ready.']
    result['changes'] = messages
    # Persist meaningful revisions, not a different timestamp on every GET.
    comparable = lambda x: {k: v for k, v in x.items() if k not in ('updated_at', 'history', 'next_review', 'saved')}
    weekly_due = bool(record and now - datetime.fromisoformat(record.plan.get('adapted_at', record.plan['created_at'])) >= timedelta(days=7))
    changed = comparable(result) != comparable(old) or weekly_due
    history = list(old.get('history', []))
    if changed and record:
        history.append({'date': now.isoformat(), 'attempt_id': result['last_attempt_id'], 'messages': messages})
        result['history'] = history[-8:]
        plan = dict(record.plan)
        # Three new submitted sessions or a weekly review can change the weekly
        # focus. A single small test updates evidence but doesn't thrash the plan.
        pivot = datetime.fromisoformat(plan.get('adapted_at', plan['created_at']))
        sessions = db.query(models.TestAttempt).filter(models.TestAttempt.user_id == user_id,
            models.TestAttempt.submitted_at > pivot, models.TestAttempt.responses.any()).count()
        if sessions >= 3 or now - pivot >= timedelta(days=7):
            checkpoint = {'date': now.isoformat(), 'tasks': [
                {'title': t['title'], **roadmap.task_progress(t, rows, datetime.fromisoformat(plan['created_at']))} for t in plan['tasks']]}
            record.checkpoints = (list(record.checkpoints) + [checkpoint])[-12:]
            plan = roadmap.make_plan(rows, settings, now)
            plan['adapted_at'] = now.isoformat()
            result['changes'] = [*messages, 'Your seven-day practice focus has been refreshed from your latest evidence.']
            result['history'][-1]['messages'] = result['changes']
        plan['journey'] = result
        record.plan = plan
        record.updated_at = now
        db.commit()
    else:
        result['history'] = history
        result['updated_at'] = old.get('updated_at', result['updated_at'])
        db.commit()  # release read/reconciliation lock
    return result
