"""A versioned, deterministic social story and live-site journey.

Only packaging changes; all examples, answers and conditions stay authored.
"""
from datetime import date
from urllib.parse import urlencode

VERSION = 4
FORMATS = ('challenge', 'answer_first', 'mistake_check', 'visual_proof')
TIMINGS = {'challenge': (5, 12, 19, 24), 'answer_first': (3, 11, 18, 23),
           'mistake_check': (4, 12, 20, 25), 'visual_proof': (4, 13, 21, 27)}
DEEP_TIMINGS = {'challenge':(6,20,34,41), 'answer_first':(5,20,34,41),
                'mistake_check':(6,21,35,42), 'visual_proof':(6,21,35,42)}

def timing_for_plan(plan):
    return (DEEP_TIMINGS if plan.get('depth')=='advanced_v1' else TIMINGS)[plan['format']]

LABELS = {'challenge': 'MAKE YOUR CALL', 'answer_first': 'ANSWER FIRST. NOW WHY?',
          'mistake_check': 'CHECK THE ASSUMPTION', 'visual_proof': 'WATCH THE IDEA WORK'}
BRIEFS = {
 'challenge': 'Open with a solvable question about the worked example. Give the answer, then the reason.',
 'answer_first': 'The first frame shows the exact answer. Make the hook explain why that result is interesting; the payoff is the reasoning.',
 'mistake_check': 'Challenge the supplied misconception without presenting it as true. Resolve it using the worked example.',
 'visual_proof': 'Connect a concrete question to the concept illustration and the exact worked solution. Do not invent visual elements.',
}
# Each opening concerns the actual worked example, not an unrelated transfer question.
HOOKS = {
'Parallel resistance': 'Two paths. Less resistance?',
'Kinetic energy scaling': 'Triple the speed. What happens to energy?',
'Spring combination': 'Two springs. A softer combination?',
'Projectile range': 'Which other angle lands just as far?',
'Vertical throw': 'When does this ball stop rising?',
'Capacitor combination': 'Two capacitors. Why less capacitance?',
'Uniform circular motion': 'Double speed. Double acceleration?',
'Wave speed': 'This answer changes if you miss the units.',
'Impulse': 'The rebound sign changes everything.',
'Electrical power': 'Check what stays fixed before choosing a formula.',
'Mole conversion': 'Multiply or divide by molar mass?',
'Dilution': 'Added water or final volume?',
'Mole fraction': 'Count the moles, not the masses.',
'Ideal gas ratios': 'Half the pressure. What happens to volume?',
'Reaction quotient': 'Which way will this reaction move?',
'First-order half-life': 'Three halvings. What is actually left?',
'Oxidation numbers': 'The ion has a charge. Your sum must too.',
'Limiting reagent': 'Fewer moles does not decide the limiter.',
'Mass percentage': 'Which mass belongs in the denominator?',
'Gas stoichiometry': 'The coefficients already tell you the ratio.',
'Quadratic roots': 'Find the sum. Skip finding the roots.',
'Difference of squares': 'Two big squares. One small multiplication.',
'Arithmetic progression': 'Pair the ends. Skip the long addition.',
'Complementary probability': 'At least one? Start with none.',
'Logarithm laws': 'Those powers can disappear in one step.',
'Odd-function integral': 'Can symmetry erase this entire calculation?',
'Even-function integral': 'Same shape on both sides. Add or cancel?',
'Derivative at a point': 'Substitute first and you lose the answer.',
'Repeated percentage change': 'Up then down. Back to the start?',
'Vector orthogonality': 'One dot product decides the angle.',
'Stopping distance': 'Double the speed. Double the stopping distance?',
'Photoelectric threshold': 'More light. Still no electrons?',
'SHM turning point': 'Stopped at the edge. Still accelerating?',
'Magnetic work': 'A force that cannot speed this charge up.',
'YDSE fringe width': 'Three units. One fringe-width calculation.',
'Escape speed': 'Twice the mass. Twice the escape speed?',
'Capacitor energy': 'Disconnect the battery. The rule changes.',
'Lens displacement': 'Two sharp images reveal one focal length.',
'Rolling energy': 'Rolling energy is not split equally.',
'Satellite energy': 'A higher orbit changes both energies.',
'Weak acid dilution': 'Weak acid. Can you use minus log C?',
'Buffer ratio': 'Dilute ten times. Does pH move?',
'Nernst shift': 'Ten times Q. How far does voltage move?',
'Solubility common ion': 'Extra chloride. Less dissolved silver?',
'Thermodynamic signs': 'These units hide the temperature threshold.',
'Arrhenius slope': 'A negative slope. Positive activation energy?',
'Colligative dissociation': 'Eighty percent split. How many particles?',
'SN1 rate law': 'Triple the nucleophile. Does the rate care?',
'Peroxide effect': 'Peroxide changes where the bromine goes.',
'Coordination oxidation': 'Six ligands. Is iron really plus six?',
'Telescoping sum': 'Ten fractions. Almost everything cancels.',
'Conditional probability': 'At least one head. Is the answer half?',
'Binomial coefficients': 'The hidden factor is inside the brackets.',
'Complex modulus': 'Find the modulus without expanding anything.',
'Determinant row operation': 'The row changes. Does the determinant?',
'Limit rationalisation': 'Zero over zero is not the final answer.',
'Integral reflection': 'Reflect the integral. The fraction disappears.',
'AM-GM minimum': 'You can minimise this without a derivative.',
'Inverse function derivative': 'The inverse slope uses a different input.',
'Independent events': 'Independent does not mean mutually exclusive.',
}
JOURNEYS = {
 'warmup': {'heading': 'Try the next question.', 'detail': '10 mixed-subject questions. Explanations included.',
            'label': 'Free warm-up · no signup', 'path': '/free-test', 'cta': 'Try the free question warm-up'},
 'cet': {'heading': 'Take it into a paper.', 'detail': 'Pick an MHT-CET year and shift. Preview before signing in.',
         'label': 'Public previews · sign in for mocks', 'path': '/mhtcet/papers', 'cta': 'Browse MHT-CET year and shift papers'},
 'practice': {'heading': 'Work on your next gap.', 'detail': 'Choose a subject and chapter. Review your attempt.',
              'label': 'Chapter practice · sign in required', 'path': '/subject-test', 'cta': 'Choose your next chapter practice'},
}

def active(c):
    return c.get('creative_version') == VERSION

def attach(c, day, ordinal):
    serial = date.fromisoformat(day).toordinal()
    # A topic gets another approach on its next rotation, not just new colours.
    seed = serial // 5 + ordinal
    return {**c, 'creative_version': VERSION, 'story_format': FORMATS[(serial + ordinal) % 4],
            'creative_seed': seed, 'journey': 'practice' if c.get('content_tier')=='advanced_v1' else ('warmup', 'cet', 'practice')[(serial + ordinal) % 3]}

def opening(c):
    return HOOKS.get(c['topic'], c.get('hook') or c['question'])

def destination(c):
    return JOURNEYS.get(c.get('journey'), JOURNEYS['warmup'])

def url(c):
    return 'https://jeeedge.in/start?' + urlencode({'utm_source':'instagram', 'utm_medium':'organic_social',
        'utm_campaign':c.get('story_format','lesson'), 'to':c.get('journey','warmup')})

def caption_suffix(c):
    return f"\n\nTry it on Jee Edge: {destination(c)['cta']}.\njeeedge.in/start"

def caption(c):
    kind = c.get('story_format', 'challenge')
    if kind == 'answer_first':
        parts = [f"{c['answer']}. Here is the calculation.", c['question'], c['solution'], c['condition']]
    elif kind == 'mistake_check':
        parts = [f"The mistake: {c['trap']}", c['question'], c['solution'], c['condition']]
    elif kind == 'visual_proof':
        parts = [c.get('why', c['rule']), c['question'], c['solution'], c['condition']]
    else:
        parts = [c['question'], c['solution'], c.get('why', c['rule']), c['condition']]
    return '\n\n'.join(parts)

def plan(c):
    kind = c.get('story_format', 'challenge')
    if kind not in FORMATS:
        kind = 'challenge'
    depth=c.get('content_tier')
    beats=(DEEP_TIMINGS if depth=='advanced_v1' else TIMINGS)[kind]
    return {'version':VERSION, 'format':kind, 'depth':depth, 'beats':beats, 'hook':opening(c),
            'soundtrack':int(c.get('creative_seed',0)) % 4, 'source':'authored', 'subtitles':[]}

def spoken(c, p):
    reveal, worked, close, end = timing_for_plan(p)
    # Keep complete sentences; no arbitrary truncation of formulae or conditions.
    why = c.get('why', c['rule'])
    explanation = why if len(why) <= 200 else c['rule']
    condition = c['condition']
    return [(0.1, reveal - .3, p.get('hook') or opening(c)),
            (reveal+.15, worked-reveal-.3, explanation),
            (worked+.15, close-worked-.3, condition)]
