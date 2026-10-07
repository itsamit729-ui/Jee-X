"""Authored visual direction; model budget belongs to the editorial quality gate."""
import hashlib
from social import lessons, hooks

VISUAL_TOPICS = ('Projectile range', 'Vertical throw', 'Uniform circular motion',
    'Wave speed', 'Kinetic energy scaling', 'Dilution', 'First-order half-life',
    'Odd-function integral', 'Even-function integral', 'Derivative at a point',
    'Difference of squares', 'Limiting reagent')
HOOKS = {
 'Projectile range': ('Which launch goes farther?', 'Two angles. One landing point.', 'Higher does not mean farther.'),
 'Vertical throw': ('What becomes zero at the top?', 'Stopped. Still accelerating.', 'Watch the instant it turns.'),
 'Uniform circular motion': ('Constant speed. Accelerating?', 'Which way does acceleration point?', 'The direction is the trick.'),
 'Wave speed': ('Does the blue dot travel?', 'The wave moves. What about the dot?', 'Watch one point, not the wave.'),
 'Kinetic energy scaling': ('Triple the speed. Triple the energy?', 'Speed changes. Energy jumps.', 'Predict the energy multiplier.'),
 'Dilution': ('More water. What stays the same?', 'Watch the particles, not the level.', 'More volume. Less concentration.'),
 'First-order half-life': ('What survives three half-lives?', 'Half of what is LEFT.', 'Why subtraction fails here.'),
 'Odd-function integral': ('A big curve. A zero integral?', 'These areas cancel. Why?', 'Check symmetry before integrating.'),
 'Even-function integral': ('These areas look equal. Now what?', 'Solve half. Double the result.', 'Symmetry saves the calculation.'),
 'Derivative at a point': ('Can you see the derivative?', 'The answer is in the tangent.', 'Watch how the slope changes.'),
 'Difference of squares': ('Can you solve this by moving shapes?', 'Two squares. One rectangle.', 'Stop expanding both squares.'),
 'Limiting reagent': ('Which reactant runs out first?', 'Count reaction groups, not molecules.', 'The smaller amount can fool you.'),
}
DIAGRAM_TOPICS = VISUAL_TOPICS + ('Stopping distance','Photoelectric threshold','Weak acid dilution','Nernst shift','Telescoping sum','Conditional probability')
VISUAL_TOPICS = tuple(dict.fromkeys(c['topic'] for c in (lessons.lesson('2026-10-07',i) for i in range(lessons.TOTAL))))
for _topic in VISUAL_TOPICS:
    if _topic not in HOOKS:
        _c = next(c for c in (lessons.lesson('2026-10-07',i) for i in range(lessons.TOTAL)) if c['topic']==_topic)
        HOOKS[_topic] = (hooks.opening(_c),)*3
FORMATS=('predict','compare','spot_trap')


def fallback(content):
    n=int(hashlib.sha256(content['lesson_id'].encode()).hexdigest()[:8],16)
    return {'format':FORMATS[n%3],'hook_index':n%3,'pace':'steady' if n%2 else 'brisk',
            'accent':'blue' if n%2 else 'cream','ending':'save','source':'authored'}


def validate(value,content):
    if not isinstance(value,dict) or value.get('format') not in FORMATS:return False
    return (type(value.get('hook_index')) is int and value['hook_index'] in range(3)
        and value.get('pace') in ('brisk','steady') and value.get('accent') in ('blue','cream')
        and value.get('ending') in ('save','challenge'))


def plan(content):
    # Spend the model budget on the hook and teacher review, not choosing
    # cosmetic enums. Exact diagrams and scene timing are authored and tested.
    return fallback(content)


def beats(plan):
    return (4,17,23,28)
