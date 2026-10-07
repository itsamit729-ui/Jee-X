"""Authored shortcut rules with explicit conditions and calculated examples.

AI may package these lessons, but cannot replace their formulas or worked answers.
"""
from datetime import date
import math
import json
from pathlib import Path

EXTRA = json.loads(Path(__file__).with_name("knowledge.json").read_text())
TOTAL = 30 + len(EXTRA)


def lesson(day, index):
    if index >= 30:
        return dict(EXTRA[(index - 30) % len(EXTRA)])
    serial = date.fromisoformat(day).toordinal()
    k = (serial + index) % 30
    n = 2 + (serial * 7 + index) % 11
    subject = ['PHYSICS', 'CHEMISTRY', 'MATHS'][k // 10]
    entries = [
        ('Parallel resistance', 'For positive resistors in parallel, the equivalent is below the smallest resistor.', 'Ideal positive resistances; components share the same two nodes.', 'Adding parallel resistances directly.', f'{n} ohm and {2*n} ohm are in parallel. Find the equivalent.', f'{2*n/3:.3g} ohm', f'R = R1 R2/(R1+R2) = {n} x {2*n}/{3*n} = {2*n/3:.3g} ohm.'),
        ('Kinetic energy scaling', 'At fixed mass, multiplying speed by a factor multiplies kinetic energy by its square.', 'Non-relativistic motion and unchanged mass.', 'Assuming kinetic energy grows linearly with speed.', f'Speed increases from {n} m/s to {3*n} m/s. By what factor does kinetic energy change?', '9 times', 'K = mv^2/2. The speed ratio is 3, so the energy ratio is 3^2 = 9.'),
        ('Spring combination', 'Identical springs: parallel stiffness adds; series stiffness divides by their count.', 'Ideal massless springs, small extensions, identical stiffness.', 'Using the series rule for a parallel arrangement.', f'Two springs, each {10*n} N/m, are in series. Find the effective stiffness.', f'{5*n} N/m', f'1/k = 1/{10*n} + 1/{10*n}. Therefore k = {5*n} N/m.'),
        ('Projectile range', 'Complementary launch angles give equal ranges at the same launch speed.', 'No air drag, constant gravity, equal launch and landing heights.', 'Applying this rule when landing height differs.', f'At a fixed launch speed, which angle has the same range as {n+20} degrees?', f'{70-n} degrees', f'R = u^2 sin(2 theta)/g. Complementary angles: 90 - {n+20} = {70-n} degrees.'),
        ('Vertical throw', 'At the highest point, vertical velocity is zero but gravitational acceleration is not.', 'Near Earth, no air resistance; take g = 10 m/s^2.', 'Setting acceleration to zero at the top.', f'A ball is thrown vertically upward at {10*n} m/s. Time to the top?', f'{n} s', f'v = u - gt. Set v = 0: t = {10*n}/10 = {n} s.'),
        ('Capacitor combination', 'Identical capacitors in parallel add; two identical capacitors in series give half.', 'Ideal capacitors in the stated series/parallel connection.', 'Copying resistor rules without checking.', f'Two {2*n} microfarad capacitors are in series. Find equivalent capacitance.', f'{n} microfarad', f'1/C = 1/{2*n} + 1/{2*n}, so C = {n} microfarad.'),
        ('Uniform circular motion', 'At fixed radius, centripetal acceleration scales with speed squared.', 'Same radius; acceleration magnitude is v^2/r.', 'Confusing constant speed with zero acceleration.', f'Speed changes from {n} m/s to {2*n} m/s at the same radius. Acceleration factor?', '4 times', 'a = v^2/r. Doubling speed multiplies acceleration by 2^2 = 4.'),
        ('Wave speed', 'Use v = frequency x wavelength; convert wavelength into metres first.', 'Frequency in hertz and wavelength in metres for speed in m/s.', 'Leaving centimetres unconverted.', f'A wave has frequency {100*n} Hz and wavelength 20 cm. Find its speed.', f'{20*n} m/s', f'20 cm = 0.20 m. v = {100*n} x 0.20 = {20*n} m/s.'),
        ('Impulse', 'Impulse is the change in momentum; use signed velocities.', 'Constant mass; choose one positive direction.', 'Ignoring the sign when an object rebounds.', f'A {n} kg ball changes velocity from +3 to -2 m/s. Find its impulse.', f'{-5*n} N s', f'J = m(v-u) = {n}(-2-3) = {-5*n} N s.'),
        ('Electrical power', 'At fixed voltage, resistance increasing makes power decrease: P = V^2/R.', 'Ideal resistor and a constant voltage supply.', 'Using fixed-current intuition for a fixed-voltage problem.', f'A {10*n} ohm resistor is across 10 V. Find its power.', f'{10/n:.3g} W', f'P = V^2/R = 100/{10*n} = {10/n:.3g} W.'),
        ('Mole conversion', 'Divide mass by molar mass; never multiply them to get moles.', 'Mass in grams and molar mass in g/mol.', 'Mixing kilograms with g/mol.', f'How many moles are in {18*n} g of water? Use 18 g/mol.', f'{n} mol', f'n = mass/molar mass = {18*n}/18 = {n} mol.'),
        ('Dilution', 'When only solvent is added, solute moles stay fixed: M1 V1 = M2 V2.', 'No reaction or solute loss; use consistent volume units.', 'Using added solvent volume as final solution volume.', f'{n} M solution: 100 mL is diluted to 500 mL. Final molarity?', f'{n/5:g} M', f'M2 = M1 V1/V2 = {n} x 100/500 = {n/5:g} M.'),
        ('Mole fraction', 'Mole fractions sum to one; count moles, not masses.', 'All components of the mixture included.', 'Putting mass directly into a mole-fraction ratio.', f'A mixture has {n} mol A and {3*n} mol B. Find the mole fraction of A.', '0.25', f'xA = {n}/({n}+{3*n}) = 1/4 = 0.25.'),
        ('Ideal gas ratios', 'At constant temperature and amount of gas, pressure x volume stays fixed.', 'Ideal-gas approximation; temperature in kelvin if it changes.', 'Applying Boyle\'s law while temperature changes.', f'A gas occupies {n} L at 2 atm. Volume at 1 atm, same temperature?', f'{2*n} L', f'P1 V1 = P2 V2, so V2 = 2 x {n}/1 = {2*n} L.'),
        ('Reaction quotient', 'Compare Q with K: Q below K means forward change toward equilibrium.', 'Same reaction, temperature and definition of Q and K.', 'Assuming a large K means the system is already at equilibrium.', f'For a reaction, Q = {n} and K = {10*n}. Which net direction is favoured?', 'Forward', f'{n} < {10*n}, so Q < K. Forward change raises Q toward K.'),
        ('First-order half-life', 'After each half-life, halve what remains; do not subtract a fixed amount.', 'First-order kinetics under unchanged conditions.', 'Subtracting half of the original amount every time.', f'A first-order sample starts at {8*n} g. Amount after three half-lives?', f'{n} g', f'Remaining = {8*n} x (1/2)^3 = {n} g.'),
        ('Oxidation numbers', 'The sum of oxidation numbers equals the overall charge.', 'Apply standard oxygen -2 here; peroxide exceptions are not involved.', 'Setting the sum to zero for a charged ion.', f'In sulfate, SO4^2-, what is sulfur\'s oxidation number? Oxygen is -2.', '+6', 'Let sulfur be x. x + 4(-2) = -2; x = +6.'),
        ('Limiting reagent', 'Divide each reactant amount by its stoichiometric coefficient; the smaller ratio limits.', 'Balanced reaction; quantities expressed in moles.', 'Choosing the smaller number of moles without using coefficients.', f'N2 + 3H2 -> 2NH3. Start with {n} mol N2 and {2*n} mol H2. Limiting reagent?', 'H2', f'N2 ratio = {n}/1; H2 ratio = {2*n}/3 = {2*n/3:.3g}. H2 has the smaller ratio.'),
        ('Mass percentage', 'Mass percent uses mass of the entire solution in the denominator.', 'Solute and solution masses in the same units.', 'Dividing by solvent mass instead of solution mass.', f'{n} g solute is mixed with {9*n} g solvent. Mass percent of solute?', '10%', f'Total mass = {10*n} g. Percent = 100 x {n}/{10*n} = 10%.'),
        ('Gas stoichiometry', 'Ideal-gas volumes at the same temperature and pressure follow mole ratios.', 'All compared gases at the same temperature and pressure.', 'Using volume ratios for solids or liquids.', f'N2 + 3H2 -> 2NH3. How much H2 reacts with {n} L N2, same T and P?', f'{3*n} L', f'The N2:H2 mole ratio is 1:3, so H2 volume = 3 x {n} = {3*n} L.'),
        ('Quadratic roots', 'For ax^2+bx+c=0, root sum is -b/a and root product is c/a.', 'a is nonzero; roots may be real or complex.', 'Forgetting the minus sign in the sum.', f'Without solving: sum of roots of x^2 - {n+3}x + {3*n} = 0?', str(n+3), f'By Vieta, sum = -b/a = -(-{n+3})/1 = {n+3}.'),
        ('Difference of squares', 'a^2-b^2 = (a-b)(a+b). Look for nearby squares.', 'Valid for all real a and b.', 'Replacing the difference of squares by (a-b)^2.', f'Evaluate {100+n}^2 - {100-n}^2 without expanding both squares.', str(400*n), f'Difference = {2*n}; sum = 200. Product = {2*n} x 200 = {400*n}.'),
        ('Arithmetic progression', 'Pair first and last terms: sum = count x (first+last)/2.', 'Equally spaced terms; count all terms correctly.', 'Using the number of gaps as the number of terms.', f'Find 1+2+...+{2*n}.', str(n*(2*n+1)), f'There are {2*n} terms. Sum = {2*n}(1+{2*n})/2 = {n*(2*n+1)}.'),
        ('Complementary probability', 'Probability of at least one = 1 - probability of none.', 'Use independence only when the trials really are independent.', 'Adding overlapping event probabilities directly.', f'A fair coin is tossed {n} times independently. Probability of at least one head?', f'1 - 1/{2**n}', f'No heads means all tails: (1/2)^{n} = 1/{2**n}. Subtract from 1.'),
        ('Logarithm laws', 'log(a b) = log(a) + log(b), but log(a+b) does not split this way.', 'Positive arguments; same valid logarithm base.', 'Splitting the logarithm of a sum.', f'Find log10(10^{n} x 100).', str(n+2), f'log10(10^{n}) + log10(100) = {n} + 2 = {n+2}.'),
        ('Odd-function integral', 'An integrable odd function has zero integral over symmetric bounds.', 'f(-x)=-f(x); interval [-a,a]; the integral must exist.', 'Using symmetry when the bounds are not opposite.', f'Integrate x^3 from -{n} to +{n}.', '0', 'x^3 is odd. Equal positive and negative signed areas cancel over symmetric bounds.'),
        ('Even-function integral', 'For an integrable even function, integrate from zero to a and double.', 'f(-x)=f(x), on the symmetric interval [-a,a].', 'Confusing an even function with zero signed area.', f'Integrate x^2 from -{n} to +{n}.', f'{2*n**3}/3', f'2 times integral from 0 to {n} of x^2 = 2 x {n}^3/3 = {2*n**3}/3.'),
        ('Derivative at a point', 'Differentiate first, substitute the point second.', 'A differentiable function at the point in question.', 'Substituting first and then differentiating a constant.', f'For f(x)=x^2+{n}x, find f\'(2).', str(n+4), f'f\'(x)=2x+{n}. Thus f\'(2)=4+{n}={n+4}.'),
        ('Repeated percentage change', 'Multiply the factors for successive percentage changes.', 'Both changes apply successively to the current value.', 'Assuming equal percentage increases and decreases cancel.', f'A price rises by {n}% and then falls by {n}%. Net percentage change?', f'{n*n/100:g}% decrease', f'(1+{n}/100)(1-{n}/100)=1-{n*n}/10000. Net loss = {n*n/100:g}%.'),
        ('Vector orthogonality', 'Two nonzero vectors are perpendicular exactly when their dot product is zero.', 'Euclidean vectors; both vectors nonzero.', 'Checking component sums instead of the dot product.', f'Are ({n},1) and (1,-{n}) perpendicular?', 'Yes', f'Dot product = {n} x 1 + 1 x (-{n}) = 0. Both vectors are nonzero.'),
    ]
    topic, rule, condition, trap, question, answer, solution = entries[k]
    return {'subject': subject, 'topic': topic, 'rule': rule, 'condition': condition,
            'trap': trap, 'question': question, 'answer': answer, 'solution': solution,
            'lesson_id': f'{k}:{n}'}


def visual_lesson(day, ordinal):
    """Rotate supported visual concepts; no duplicate Reel topic within a 10-Reel day."""
    from social.storyboard import VISUAL_TOPICS
    pool={item['topic']:item for item in (lesson(day,i) for i in range(TOTAL))}
    topic=VISUAL_TOPICS[(date.fromisoformat(day).toordinal()*10+ordinal)%len(VISUAL_TOPICS)]
    return pool[topic]
