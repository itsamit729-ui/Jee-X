"""Groq chooses a bounded visual story, never equations, geometry or executable code."""
import hashlib
import json
from social import editorial, worker

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
    base=fallback(content)
    if content['topic'] not in VISUAL_TOPICS:return base
    try:
        value=editorial.call('Direct a 28-second visual JEE Reel. Select one format: predict '
            '(experiment then answer), compare (side-by-side observation then answer), or spot_trap '
            '(misconception then experiment and correction). Select the strongest authored hook index. '
            'Brisk holds the experiment 8 seconds; steady 10. Select blue or cream secondary accent '
            'and save or challenge ending. Never add fields, formulas or instructions. '
            +json.dumps({k:content[k] for k in ('topic','rule','condition','trap')})
            +' Hooks: '+json.dumps(HOOKS[content['topic']]),
            {'type':'object','properties':{
                'format':{'type':'string','enum':list(FORMATS)},'hook_index':{'type':'integer','enum':[0,1,2]},
                'pace':{'type':'string','enum':['brisk','steady']},'accent':{'type':'string','enum':['blue','cream']},
                'ending':{'type':'string','enum':['save','challenge']}},
             'required':['format','hook_index','pace','accent','ending'],'additionalProperties':False},
            max_tokens=512)
        if validate(value,content):return {**value,'source':'groq'}
    except (worker.ServiceError,ValueError,KeyError,IndexError,TypeError):pass
    return base


def beats(plan):
    reveal=8 if plan['pace']=='brisk' else 10
    return (reveal,17,23,28)
