"""Actionable topic sequence. Learning thresholds are explicit, not score predictions."""
from collections import defaultdict
from datetime import timedelta, date
from statistics import median
from sqlalchemy import func
from app import models as m

# Conservative chapter ordering, applied only when BOTH names exist in the catalog.
# This is a small curated dependency map, not a claim of a complete prerequisite graph.
DEPENDENCIES = {
    'applications of derivatives': ['continuity and differentiability'],
    'application of derivatives': ['continuity and differentiability'],
    'differential equations': ['integrals'],
    'moving charges and magnetism': ['current electricity'],
    'chemical bonding and molecular structure': ['structure of atom'],
}
LABELS = {'diagnose': 'Find your starting point', 'repair': 'Rebuild the concept',
          'retention': 'Check what you remember', 'fluency': 'Improve solving speed',
          'apply': 'Practise unfamiliar questions', 'maintain': 'Keep it fresh'}


def build_topic_plan(db, rows, settings, standing, now):
    from app.services.question_catalog import candidate_query
    catalog = candidate_query(db).filter(m.Chapter.in_main.is_(True)).subquery()
    topics = db.query(m.Subtopic.id, m.Subtopic.name, m.Chapter.id.label('chapter_id'),
        m.Chapter.name.label('chapter'), m.Subject.code.label('subject'), func.count(catalog.c.id).label('available')).join(
        m.Chapter, m.Chapter.id == m.Subtopic.chapter_id).join(m.Subject, m.Subject.id == m.Chapter.subject_id).join(
        catalog, catalog.c.subtopic_id == m.Subtopic.id).group_by(m.Subtopic.id, m.Subtopic.name, m.Chapter.id, m.Chapter.name, m.Subject.code).all()
    # One FIRST exposure per question. Repeating an answer after seeing a solution
    # can help learning but does not inflate the progress checks.
    by_topic, seen = defaultdict(list), set()
    for r in rows:
        if r.question_id in seen or r.answered_at < now - timedelta(days=45) or r.answered_at != r.first_answered:
            continue
        seen.add(r.question_id)
        if r.outcome in ('correct', 'wrong'):
            by_topic[r.subtopic_id].append(r)
    result = []
    for t in topics:
        sample = by_topic[t.id]
        n = len(sample)
        accuracy = round(100 * sum(r.outcome == 'correct' for r in sample) / n) if n else None
        days = len({r.answered_at.date() for r in sample})
        first = min((r.answered_at for r in sample), default=None)
        last = max((r.answered_at for r in sample), default=None)
        later = [r for r in sample if first and r.answered_at >= first + timedelta(days=3)]
        foundation = n >= 8 and days >= 2 and accuracy >= 70
        retained = foundation and len(later) >= 4 and sum(r.outcome == 'correct' for r in later) / len(later) >= .75
        timed = [r.time_taken_sec / r.expected_time_sec for r in sample if r.outcome == 'correct' and 0 < r.time_taken_sec <= 1800 and r.expected_time_sec > 0]
        ratio = round(median(timed), 2) if len(timed) >= 6 else None
        if n < 8 or days < 2:
            purpose, reason = 'diagnose', f'{n} fresh answers across {days} study days. We need a broader sample before calling this topic strong or weak.'
        elif accuracy < 70:
            purpose, reason = 'repair', f'{accuracy}% correct across {n} fresh answers. Review the method and work through your mistakes before harder questions.'
        elif (now - last).days >= 7:
            purpose, reason = 'retention', f'Last fresh practice was {(now - last).days} days ago. Check recall before moving on.'
        elif ratio and ratio > 1.3:
            purpose, reason = 'fluency', f'{accuracy}% correct, but the median solving time is {ratio}× the question guide across {len(timed)} correct timed answers.'
        elif not retained:
            purpose, reason = 'apply', 'Foundation checkpoint met. Try unfamiliar applications, then return after at least three days to check retention.'
        else:
            purpose, reason = 'maintain', 'Foundation and retention checkpoints met. Keep this topic in mixed revision and test it in a full paper.'
        steps = ['Review one concept or worked example in your notes · 10 min', 'Solve a fresh topic set without help · 15 min', 'Read explanations and record the cause of each mistake · 5 min']
        if purpose == 'fluency':
            steps[0] = 'Review a shorter solving method and common time traps · 10 min'
        if purpose == 'retention':
            steps[0] = 'Recall the method from memory before opening your notes · 10 min'
        result.append({'topic_id': t.id, 'topic': t.name, 'chapter_id': t.chapter_id, 'chapter': t.chapter,
            'subject': t.subject, 'purpose': purpose, 'action': LABELS[purpose], 'reason': reason,
            'minutes': 30, 'steps': steps, 'accuracy': accuracy, 'fresh_answers': n, 'study_days': days,
            'foundation_met': foundation, 'retention_met': retained, 'timing_ratio': ratio,
            'check': 'Foundation: at least 8 fresh answers on 2 days, with 70% correct. Retention: 4 fresh answers at least 3 days after the first session, with 75% correct.',
            'bank_note': 'Limited fresh question coverage: repeated questions help review but cannot prove this checkpoint.' if t.available < 12 else None,
            'prerequisites': []})
    priority = {'repair': 0, 'retention': 1, 'fluency': 2, 'diagnose': 3, 'apply': 4, 'maintain': 5}
    result.sort(key=lambda t: (priority[t['purpose']], t['accuracy'] if t['accuracy'] is not None else 101, t['subject'], t['chapter_id'], t['topic_id']))
    # Interleave subjects within each priority tier; one subject should not hide all others.
    ranked = []
    for p in range(6):
        groups = {s: [t for t in result if t['subject'] == s and priority[t['purpose']] == p] for s in ('PHY', 'CHEM', 'MATH')}
        while any(groups.values()):
            for group in groups.values():
                if group:
                    ranked.append(group.pop(0))
    chapter_topics = defaultdict(list)
    for t in result:
        chapter_topics[(t['subject'], t['chapter'].strip().lower())].append(t)
    ordered, placed, visiting = [], set(), set()
    def place(t):
        if t['topic_id'] in placed or t['topic_id'] in visiting:
            return
        visiting.add(t['topic_id'])
        for name in DEPENDENCIES.get(t['chapter'].strip().lower(), []):
            prerequisites = chapter_topics.get((t['subject'], name), [])
            for pre in prerequisites:
                if not pre['foundation_met']:
                    t['prerequisites'].append(pre['topic'])
                    place(pre)
        visiting.remove(t['topic_id'])
        placed.add(t['topic_id'])
        ordered.append(t)
    for t in ranked:
        place(t)
    budget = settings['weekly_hours'] * 60
    # Reserve half the available time for revision/checkpoints, not new topic cards.
    slots = max(1, int(budget // 60))
    horizon = date.fromisoformat(settings['planning_until'])
    weeks_available = max(1, ((horizon - now.date()).days + 6) // 7)
    for i, t in enumerate(ordered):
        t['order'] = i + 1
        t['week'] = i // slots + 1
        t['planned_from'] = (now.date() + timedelta(weeks=t['week'] - 1)).isoformat()
        t['within_horizon'] = t['week'] <= weeks_available
    recent = [r for r in standing['recent'] if r['date'][:10] >= (now - timedelta(days=45)).date().isoformat()][:3]
    target = settings.get('target_marks')
    gap = max(0, target - standing['score']) if target is not None and standing['score'] is not None else None
    return {'topics': ordered, 'today': ordered[0] if ordered else None, 'week': ordered[:slots],
        'weekly_hours': settings['weekly_hours'], 'topic_minutes': min(len(ordered), slots) * 30,
        'reserved_minutes': budget - min(len(ordered), slots) * 30,
        'goal': f'{target} / 300 marks' if target is not None else 'Your chosen colleges and branches',
        'score': standing['score'], 'score_range': [min(r['score'] for r in recent), max(r['score'] for r in recent)] if len({r['date'][:10] for r in recent}) >= 3 else None,
        'assessment_count': len(recent), 'gap': gap,
        'goal_explanation': f'Close the observed {gap}-mark gap by repairing topic gaps, validating retention and checking transfer in full assessments.' if gap else 'Maintain your target through repeated full assessments and continued revision.' if gap == 0 else f'Start with the topics below, then take a balanced full assessment to measure the distance to {target} marks.' if target is not None else 'Build reliable topic knowledge and use assessment results to track progress. Compare actual rank evidence with your college benchmarks.',
        'phases': [
            {'title': 'Build and repair named topics', 'when': 'Start now', 'action': 'Follow the ordered topic list. Review concepts, practise independently and correct mistakes.', 'check': 'Meet each topic’s fresh-answer foundation checkpoint.'},
            {'title': 'Retain and combine topics', 'when': 'Alongside topic work, from day 4', 'action': 'Revisit topics after a gap and mix them with earlier chapters.', 'check': 'Pass delayed fresh-question checks; reopen topics where accuracy drops.'},
            {'title': 'Turn learning into exam marks', 'when': 'Every 2 weeks when you can reserve a 3-hour block', 'action': 'Take a balanced full assessment and review errors, omissions and pacing. This replaces study time; it is not extra workload.', 'check': f'Sustain {target}/300 across 3 recent assessments on separate days.' if target else 'Compare actual rank evidence with the correct category and quota benchmarks.'},
            {'title': 'Revise through exam day', 'when': 'Final 2 weeks before the configured exam' if settings['exam_date'] else 'Final revision dates appear when the exam date is configured', 'action': 'Prioritise error-log revision, recall and mixed papers; reduce new-topic load.', 'check': 'Keep checking accuracy and pacing instead of treating finished sessions as guaranteed marks.'}],
        'capacity_note': f'{sum(not t["within_horizon"] for t in ordered)} topic sessions fall outside the current planning horizon. Increase available study time or revisit priorities.' if any(not t['within_horizon'] for t in ordered) else 'This is a first-pass schedule. Difficult topics may need extra sessions; dates adjust with your results.',
        'timeline_note': settings['timeline_note'], 'planning_until': settings['planning_until'],
        'method': 'Recomputed from submitted answers. Checkpoints use first exposures within 45 days in the latest 500 response records; repeat answers do not prove mastery. Thresholds and time guides are planning heuristics, not a validated score model. The prerequisite map covers only explicitly matched chapters. Topic completion never promises extra marks or admission.'}
