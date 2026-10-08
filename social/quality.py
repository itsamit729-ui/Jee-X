"""Authored reasoning and transfer checks; AI never edits these answers."""
from datetime import date
from social import lessons

# why, transfer question, transfer answer. These extend the foundational example
# with a boundary case or linked calculation, without claiming to be actual PYQs.
DEPTH = {
'Parallel resistance': ('Each parallel branch adds current at the same voltage, so total conductance increases.', 'Two positive resistors in parallel have an equivalent resistance of 3 ohm. One is 6 ohm. Find the other.', '1/3 = 1/6 + 1/R, so 1/R = 1/6 and R = 6 ohm.'),
'Kinetic energy scaling': ('Speed is squared in K = mv^2/2. A speed ratio must be squared before comparing energies.', 'Mass doubles while speed halves. What happens to kinetic energy?', 'Knew/Kold = 2 x (1/2)^2 = 1/2. Energy halves; both changing factors matter.'),
'Spring combination': ('Series springs carry the same force; their extensions add. This makes the combination softer.', 'Two ideal springs of stiffness 100 and 200 N/m are in series. Find the effective stiffness.', '1/k = 1/100 + 1/200 = 3/200. Thus k = 200/3 N/m, below both individual values.'),
'Projectile range': ('For complementary angles, the factors sin(theta) and cos(theta) swap. Their product, and hence range, is unchanged.', 'At equal launch speed, angles 30 and 60 degrees have equal range on level ground. Are their flight times equal?', 'No. T = 2u sin(theta)/g. The 60-degree throw stays airborne sqrt(3) times longer. Equal range does not imply equal time.'),
'Vertical throw': ('Velocity describes current motion; acceleration describes its change. Gravity still changes velocity at the turning point.', 'Take upward as positive. At the highest point of a vertical throw, what are velocity and acceleration? Use g = 10 m/s^2.', 'Velocity = 0; acceleration = -10 m/s^2. Gravity has not switched off.'),
'Capacitor combination': ('Series capacitors carry equal charge while voltage drops add. Equal capacitors split the total voltage equally.', 'Two 6 microfarad capacitors are in series across 12 V. Find the charge on each capacitor.', 'Ceq = 3 microfarad. Q = Ceq V = 36 microcoulomb. Each series capacitor carries that charge.'),
'Uniform circular motion': ('Even at constant speed, velocity changes direction. The acceleration needed to turn it is v^2/r.', 'Both speed and circular-path radius double. By what factor does centripetal acceleration change?', 'anew/aold = 2^2/2 = 2. The fixed-radius shortcut alone would give the wrong answer.'),
'Wave speed': ('One cycle advances the wave by one wavelength. Cycles per second times distance per cycle gives speed.', 'A wave travels at 40 m/s. If its frequency doubles while speed stays fixed, what happens to wavelength?', 'v = f lambda stays fixed, so wavelength halves. This comparison assumes the wave speed is unchanged.'),
'Impulse': ('Momentum is a vector. A rebound changes direction, so the final and initial velocities have opposite signs.', 'A 2 kg ball rebounds from +3 to -3 m/s. Is its impulse zero because the speed is unchanged?', 'No. J = 2(-3-3) = -12 N s. Speed is unchanged, but velocity and momentum are not.'),
'Electrical power': ('Combine P = VI with V = IR. Which quantity is held fixed decides whether resistance raises or lowers power.', 'Resistance doubles. Compare the power change for fixed voltage and fixed current.', 'Fixed voltage: P = V^2/R halves. Fixed current: P = I^2 R doubles. State the constraint before choosing a formula.'),
'Mole conversion': ('Molar mass tells you how many grams correspond to one mole. Dividing mass by it counts moles.', 'How many hydrogen atoms are in 18 g of water? Use molar mass 18 g/mol and Avogadro constant NA.', '18/18 = 1 mol of water molecules. Each molecule has two hydrogen atoms, giving 2 NA hydrogen atoms.'),
'Dilution': ('Adding only solvent changes volume, not the amount of dissolved solute. The product M V therefore stays fixed.', '100 mL of 2 M solution is diluted to a final volume of 250 mL. Is its final molarity 2 x 100/150?', 'No. Use final volume, not the added volume: M2 = 2 x 100/250 = 0.8 M.'),
'Mole fraction': ('Mole fraction compares particle amounts. Mass ratios work only after accounting for different molar masses.', 'A mixture contains 18 g water and 46 g ethanol. Their molar masses are 18 and 46 g/mol. Find the mole fraction of water.', 'Each substance contributes 1 mol. Water mole fraction = 1/(1+1) = 0.5, despite the unequal masses.'),
'Ideal gas ratios': ('PV = nRT fixes the pressure-volume product only when both temperature and amount of gas stay fixed.', 'An ideal gas doubles its absolute temperature and halves its volume, with fixed moles. Pressure factor?', 'P is proportional to T/V, so Pnew/Pold = 2/(1/2) = 4. Boyle\'s fixed-temperature rule alone does not apply.'),
'Reaction quotient': ('Q uses the current composition, while K describes equilibrium at the given temperature. Their comparison predicts net change.', 'A reaction has a large K, but its current Q is even larger. Which net direction is favoured?', 'Reverse. Q > K, so the system shifts toward reactants. A large K alone does not reveal the direction from the current state.'),
'First-order half-life': ('First-order decay removes a fixed fraction in equal times, not a fixed mass. Three halvings leave one eighth.', 'A first-order sample is 75% consumed. How many half-lives have elapsed?', '25% remains: 1/4 = (1/2)^2. Two half-lives have elapsed.'),
'Oxidation numbers': ('The charge balance belongs to the whole species. A charged ion has a nonzero total oxidation-number sum.', 'What is oxygen\'s oxidation number in hydrogen peroxide, H2O2, if hydrogen is +1?', '2(+1) + 2x = 0, so x = -1. Peroxides are an exception to the usual oxygen value of -2.'),
'Limiting reagent': ('Each reaction group consumes reactants in the balanced ratio. Divide available moles by the required coefficient to count groups.', 'For N2 + 3H2 -> 2NH3, start with 2 mol N2 and 3 mol H2. Find NH3 formed and N2 left after complete reaction.', 'H2 permits one reaction group. It consumes 1 mol N2 and produces 2 mol NH3, leaving 1 mol N2.'),
'Mass percentage': ('Solution mass includes both solute and solvent. Leaving out the solute changes the denominator.', '10 g solute is dissolved in 90 g water, then 50 g pure water evaporates with no solute loss. New mass percent?', 'Final solution mass = 50 g; solute mass = 10 g. Mass percent = 100 x 10/50 = 20%.'),
'Gas stoichiometry': ('At equal temperature and pressure, ideal gases have equal volume per mole. Balanced mole ratios then become volume ratios.', 'N2 + 3H2 -> 2NH3. Mix 2 L N2 and 3 L H2 at the same temperature and pressure. Maximum NH3 volume at those conditions?', 'H2 limits the reaction: 3 L H2 reacts with 1 L N2 to form 2 L NH3, leaving 1 L N2. Assume complete conversion and ideal gases.'),
'Quadratic roots': ('Expanding a(x-r1)(x-r2) and matching coefficients gives the root sum and product without solving for either root.', 'Roots alpha and beta satisfy x^2 - 5x + 6 = 0. Find alpha^2 + beta^2 without solving.', 'alpha^2 + beta^2 = (alpha+beta)^2 - 2 alpha beta = 5^2 - 2 x 6 = 13.'),
'Difference of squares': ('Expanding (a-b)(a+b) cancels the two cross terms. Only a^2-b^2 remains.', 'Find 1003 x 997 using symmetry around 1000.', '(1000+3)(1000-3) = 1000^2 - 3^2 = 999991. A product near a square becomes one subtraction.'),
'Arithmetic progression': ('Pairing the first and last terms gives equal pair sums. The factor one half accounts for counting the sequence twice.', 'The first term is 3, the last is 39, and the common difference is 4. Find the sum.', 'There are (39-3)/4 + 1 = 10 terms. Sum = 10(3+39)/2 = 210. Nine gaps do not mean nine terms.'),
'Complementary probability': ('The events "at least one" and "none" are disjoint and cover every outcome. Their probabilities sum to one.', 'Two independent trials each succeed with probability 1/3. Probability of at least one success?', '1 - P(both fail) = 1 - (2/3)^2 = 5/9. Adding 1/3 + 1/3 double-counts the case where both succeed.'),
'Logarithm laws': ('Products inside a logarithm become sums because multiplying powers adds exponents. Addition inside has no such rule.', 'Is log10(100+100) equal to log10(100) + log10(100)?', 'No. The left side is log10(200), between 2 and 3. The right side is 4, which equals log10(100 x 100).'),
'Odd-function integral': ('For an odd function, values at opposite inputs cancel as signed areas over symmetric bounds, if the integral exists.', 'Can you declare the ordinary improper integral of 1/x from -1 to 1 equal to zero by odd symmetry?', 'No. It is singular at zero and the two one-sided integrals diverge. Its Cauchy principal value is zero, but the ordinary improper integral does not exist.'),
'Even-function integral': ('An even function has matching values at opposite inputs. The two halves of a symmetric integral add, not cancel.', 'Integrate x^2 + x^3 from -2 to 2 using symmetry.', 'The odd x^3 term integrates to zero. The even part gives 2 times integral of x^2 from 0 to 2 = 16/3.'),
'Derivative at a point': ('A derivative is the local rate of change. Replacing the function with one value first removes all variation.', 'For f(x)=x^2, find the tangent line at x=2.', 'The slope is f\'(2)=4, and the point is (2,4). Thus y-4 = 4(x-2), or y = 4x-4.'),
'Repeated percentage change': ('Successive changes use successive bases. Multiplying the factors preserves that change of base.', 'A price falls by 20%. What percentage increase restores the original price?', 'After the fall, 80% remains. The restoring factor is 100/80 = 1.25, so a 25% increase is needed.'),
'Vector orthogonality': ('The dot product is |a||b| cos(theta). For two nonzero vectors, a zero result means a right angle.', 'The zero vector has dot product zero with every vector. Does that assign it a 90-degree angle with every vector?', 'No. The zero vector has no defined direction, so its angle is undefined. The nonzero-vector condition matters.'),
}


def enrich(content):
    if content.get('why'):
        return dict(content)
    why, question, answer = DEPTH[content['topic']]
    return {**content, 'why': why, 'transfer_question': question, 'transfer_answer': answer}


def daily_plan(day, count, reels):
    """Twenty distinct topics per subject; four per day, a five-day rotation.

    Saved job snapshots remain immutable. All topics have an authored visual
    proof board; physical diagrams are used only for supported simulations.
    """
    serial = date.fromisoformat(day).toordinal()
    pool = {int(c['lesson_id'].split(':')[0]): c for c in (lessons.lesson(day,i) for i in range(lessons.TOTAL))}
    rings = [tuple(x for pair in zip(range(s*10,s*10+10),range(30+s*10,40+s*10)) for x in pair) for s in range(3)]
    groups = [[pool[ring[(serial*4+j)%20]] for j in range(4)] for ring in rings]
    candidates = [groups[s][j] for j in range(4) for s in range(3)]
    from social.storyboard import DIAGRAM_TOPICS
    visual = sorted(candidates, key=lambda c: c['topic'] not in DIAGRAM_TOPICS)
    # Interleaved subjects keep the Reel subset varied too.
    video_choices = visual[:reels]
    video_indices = [i for i in range(count) if (i+1)*reels//count > i*reels//count]
    video = dict(zip(video_indices, video_choices))
    counts = {s: sum(c['subject']==s for c in video.values()) for s in ('PHYSICS','CHEMISTRY','MATHS')}
    used = {c['topic'] for c in video.values()}
    result = []
    from social import art_direction
    ordinals = {True:0,False:0}
    for index in range(count):
        if index in video:
            choice = video[index]
        else:
            available = [c for c in candidates if c['topic'] not in used]
            choice = min(available, key=lambda c: counts[c['subject']])
            counts[choice['subject']] += 1
            used.add(choice['topic'])
        kind = index in video
        result.append(art_direction.attach(enrich(choice), serial, ordinals[kind]))
        ordinals[kind] += 1
    return result
