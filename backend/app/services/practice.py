"""Evidence-based, fixed practice sessions. No generated claims or answer leakage."""
from collections import defaultdict
from datetime import datetime
from statistics import median


def choose_questions(candidates, history, count, mode='recommended', now=None):
    now = now or datetime.utcnow()
    recent = defaultdict(list)
    seen = set()
    for row in history:  # newest first, one observation per distinct question
        if row.question_id in seen:
            continue
        seen.add(row.question_id)
        if row.outcome in ('correct', 'wrong') and len(recent[row.subtopic_id]) < 5:
            recent[row.subtopic_id].append(row)
    ranked = []
    for q in candidates:
        rows = recent[q.subtopic_id]
        wrong = sum(r.outcome == 'wrong' for r in rows)
        timed = [r for r in rows if r.outcome == 'correct' and 0 < r.time_taken_sec <= 1800 and r.expected_time_sec > 0]
        days = max(0, (now - rows[0].answered_at.replace(tzinfo=None)).days) if rows else None
        base = round(median([r.difficulty for r in rows])) if rows else 3
        evidence = {'distinct_questions': len(rows), 'incorrect': wrong}
        if mode == 'revision' and rows and days >= 7:
            code, text, goal, target = 'spaced_revision', f'Your last recorded answer on {q.topic} was {days} days ago.', 'Check what you remember without looking at a solution.', base
            evidence['days_since_practice'] = days
        elif len(rows) >= 3 and wrong >= 2:
            code, text, goal, target = 'revisit_weak_concept', f'You missed {wrong} of your {len(rows)} most recent distinct questions on {q.topic}.', 'Rebuild accuracy with another application of this concept.', max(1, base - 1)
        elif rows and days >= 7:
            code, text, goal, target = 'spaced_revision', f'Your last recorded answer on {q.topic} was {days} days ago.', 'Check what you remember without looking at a solution.', base
            evidence['days_since_practice'] = days
        elif len(timed) >= 3 and median([r.time_taken_sec / r.expected_time_sec for r in timed]) > 1.3:
            code, text, goal, target = 'build_fluency', f'Your recent correct answers on {q.topic} took longer than their expected times.', 'Look for an efficient approach while keeping your accuracy.', base
            evidence['timed_correct_questions'] = len(timed)
        elif len(rows) >= 4 and all(r.outcome == 'correct' for r in rows[:4]):
            code, text, goal, target = 'stretch', f'You answered your last 4 distinct questions on {q.topic} correctly.', 'Test your understanding with another application.', min(10, base + 1)
        elif not rows:
            code, text, goal, target = 'diagnostic', f'There is not enough recent question-level evidence on {q.topic} yet.', 'Help us find your starting point.', 3
        else:
            code, text, goal, target = 'build_evidence', f'You have {len(rows)} recent distinct answered {"question" if len(rows) == 1 else "questions"} on {q.topic}.', 'Build a clearer picture before drawing conclusions about this topic.', base
        if code == 'stretch' and q.difficulty > base:
            goal = 'Try a harder application of this concept.'
        repeated = q.id in seen
        if repeated:
            text += ' You have seen this question before; this is a revision attempt.'
        reason = {'reason_code': code, 'reason': text, 'learning_goal': goal, 'evidence': evidence, 'repeated': repeated}
        ranked.append((q, reason, abs(q.difficulty - target), repeated))
    # Aim for 60% support, 20% revision and 20% exploration, using available evidence.
    pattern = ['support', 'support', 'revision', 'support', 'explore']
    groups = {'revisit_weak_concept': 'support', 'build_fluency': 'support', 'spaced_revision': 'revision'}
    used = defaultdict(int)
    chosen = []
    while ranked and len(chosen) < count:
        desired = 'revision' if mode == 'revision' else pattern[len(chosen) % len(pattern)]
        best = min(ranked, key=lambda item: (
            item[3], groups.get(item[1]['reason_code'], 'explore') != desired,
            used[item[0].subtopic_id], item[2], item[0].id))
        ranked.remove(best)
        q, reason, _, _ = best
        used[q.subtopic_id] += 1
        chosen.append((q.id, reason))
    return chosen
