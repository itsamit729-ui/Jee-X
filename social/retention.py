"""Authored visual story briefs. Original examples; no scraped scripts or invented exam claims."""
ENGINE = 'visual_v1'
BEATS = (8, 22, 36, 40)
CUTS = (0, 3, 8, 15, 22, 30, 36, 40)

# Hook, visual setup, diagram, exact diagram data, three spoken worked steps.
BRIEFS = {
'Moving wedge constraint': (
 'The ramp moves. Is your block formula still valid?', 'Equal masses. Smooth 45-degree wedge. Find its recoil.', 'wedge', (),
 ('Horizontal momentum couples the wedge and block accelerations.', 'Along the moving incline, gravity and wedge recoil both enter the equation.', 'Combine the two equations at forty five degrees. The wedge acceleration is g divided by three.')),
'Rolling energy and height': (
 'Friction acts. So why is no energy lost?', 'Solid sphere. Pure rolling up a fixed incline.', 'rolling', (('Translation',.5),('Rotation',.2),('Total',.7)),
 ('Start with both translational and rotational kinetic energy.', 'For a solid sphere, rotation adds one fifth of m v squared. Total energy is seven tenths of m v squared.', 'At the highest point, all that energy becomes gravitational potential energy.')),
'Falling rod hinge reaction': (
 'At the bottom, does the hinge carry only mg?', 'Uniform rod, released horizontally. Frictionless fixed hinge.', 'rod', (),
 ('The centre of mass drops half the rod length. Use energy to find the angular speed.', 'At the bottom, the centre of mass still accelerates upward at three g divided by two.', 'The hinge must support weight and provide that acceleration. Its upward force is five m g divided by two.')),
'Opposed capacitor charge sharing': (
 'Zero final voltage. Did the energy vanish?', 'Join C at V and 2C at V/2 with opposite polarities.', 'capacitors', (('Initial energy',.75),('Final energy',0),('Dissipated',.75)),
 ('Keep the signs. The two initial node charges are equal and opposite.', 'They cancel, so the final voltage and stored energy are zero.', 'The original energy, three quarters of C V squared, is dissipated in the connection resistance.')),
'Coupled oscillator normal mode': (
 'Three springs. Why is the answer not root k over m?', 'Equal masses. Three equal springs. Opposite-phase motion.', 'springs', (),
 ('The left mass feels the wall spring and the coupling spring.', 'In opposite phase, the other displacement is negative. The restoring force becomes minus three k x.', 'Compare with simple harmonic motion. The angular frequency is the square root of three k over m.')),
'Rotating hoop equilibrium': (
 'Can the lowest point become unstable?', 'Rotating hoop: omega squared times R equals 2g.', 'hoop', (),
 ('Balance the tangential components in the rotating frame.', 'For the displaced equilibrium, cosine theta equals g divided by omega squared R.', 'That ratio is one half, so the stable positions are sixty degrees from the bottom, on either side.')),
'Crossed fields from rest': (
 'E over B is not this particle’s maximum speed.', 'Positive charge starts at rest. E is perpendicular to B.', 'speed', (),
 ('Define u as E over B and omega as q B over m.', 'The two velocity components are u times one minus cosine, and u times sine.', 'Their squared sum reaches four u squared. Maximum speed is twice E over B.')),
'Gravity tunnel quarter period': (
 'Falling through Earth is not constant-g motion.', 'Uniform spherical Earth. Drop from the surface to its centre.', 'tunnel', (),
 ('Only the enclosed mass contributes, and it scales with the cube of distance.', 'The inward acceleration is proportional to displacement. This is simple harmonic motion.', 'Surface to centre is one quarter of the period, not one half.')),
'Gas equilibrium dissociation': (
 'At equilibrium, the total mole count has changed.', 'A becomes 2B. Kp = 4 bar. Total pressure = 3 bar.', 'bars', (('A / mol',.5),('B / mol',1),('Total / mol',1.5)),
 ('Start with one mole. At equilibrium, A is one minus alpha, and B is twice alpha.', 'Use the changed total, one plus alpha, to calculate both partial pressures.', 'Substitution gives alpha squared equal to one quarter. The dissociation fraction is one half.')),
'Squared common ion effect': (
 'This silver concentration must be squared.', 'Ag2CrO4: Ksp = 4 x 10^-12. Ag+ starts at 0.10 M.', 'algebra', ('Ksp = [Ag+]² s','s = Ksp / (0.10)²','s = 4 x 10^-10 M'),
 ('The solubility product contains the silver concentration squared.', 'Dissolving s adds twice s of silver, but the initial silver is much larger.', 'Use zero point one squared in the denominator. Solubility is four times ten to the minus ten molar.')),
'Buffer after neutralisation': (
 'Adding acid? Don’t use the old buffer ratio.', '20 mmol HA, 10 mmol A-. Add 5 mmol HCl. pKa = 5.', 'bars', (('HA after / mmol',25),('A- after / mmol',5)),
 ('First do the reaction. Acid consumes five millimoles of the conjugate base.', 'Five millimoles of base remain, while the acid increases to twenty five.', 'Only now use Henderson Hasselbalch. Five plus log of one fifth gives about four point three.')),
'Concentration cell polarity': (
 'Same metal. Can this cell still produce voltage?', 'Zn2+: 0.010 M on one side, 1.0 M on the other.', 'algebra', ('Higher [Zn²+] → higher reduction potential','1.0 M side = cathode','E = (0.05916/2) log(100)'),
 ('The standard potentials cancel because both electrodes are zinc.', 'The higher zinc ion concentration has the higher reduction potential, so it is the cathode.', 'The Nernst concentration ratio is one hundred. The ideal cell voltage is zero point zero five nine one six volts.')),
'Reverse and scale equilibrium': (
 'Double the reaction. Do you double K?', 'A to B: K=100. C to B: K=1000. Find K for 2A to 2C.', 'algebra', ('Reverse: 1/1000','Combine: 100/1000 = 0.1','Double: (0.1)² = 0.01'),
 ('Reverse the second reaction, so its equilibrium constant becomes one over one thousand.', 'Add the reactions. Multiply the constants to obtain zero point one.', 'Doubling a reaction squares its constant. The final answer is zero point zero one.')),
'Parallel first order pathways': (
 'Half gone does not mean half became B.', 'A forms B at rate constant 2k, and C at k.', 'bars', (('A remaining / A0',.5),('B formed / A0',1/3),('C formed / A0',1/6)),
 ('Both pathways consume A, so its total first order rate constant is three k.', 'At half consumption, the elapsed time is natural log two divided by three k.', 'B receives two thirds of the consumed half. That is one third of the original amount.')),
'Base buffer after acid': (
 'This base buffer needs a reaction before a formula.', '60 mmol B + 20 mmol HCl. pKb=5, pKw=14.', 'bars', (('B left / mmol',40),('BH+ formed / mmol',20)),
 ('Hydrochloric acid converts twenty millimoles of base into its conjugate acid.', 'Forty millimoles of base remain. The conjugate acid is twenty.', 'Calculate p O H using that new ratio, then subtract from fourteen. The p H is about nine point three.')),
'Association apparent molar mass': (
 'Heavier particles. What fraction actually paired up?', 'Monomer: 100 g/mol. Apparent molar mass: 150 g/mol.', 'bars', (('Initial particles',1),('Final particles',2/3)),
 ('The particle factor is the true molar mass over the apparent value, giving two thirds.', 'Pairing alpha of the original monomer units leaves one minus alpha over two particles.', 'Equate that to two thirds. Two thirds of the monomer units associate.')),
'Root interval contradiction': (
 'Two roots between 0 and 1. Is that even possible?', 'Both roots of x² - 2ax + a must lie strictly in (0,1).', 'discriminant', (),
 ('For an upward parabola with both roots inside, its values at zero and one must be positive.', 'Those endpoint tests force a to lie strictly between zero and one.', 'But then the discriminant is negative. There are no real roots, so no real value of a works.')),
'Reciprocal improper integral': (
 'An infinite-range integral cancels itself.', 'Integrate ln(x)/(1+x²) from zero to infinity.', 'algebra', ('x = 1/t','ln(x) becomes -ln(t)','I = -I → I = 0'),
 ('First check convergence at both endpoints. The integral exists.', 'Now substitute x equal to one over t. The logarithm changes sign.', 'After reversing the limits, the transformed integral is minus the original. Its value is zero.')),
'Functional reciprocal system': (
 'The second equation is hiding inside the first.', 'For x>0: f(x) + 2f(1/x) = 3x. Integrate from 1 to 2.', 'algebra', ('f(x) + 2f(1/x) = 3x','2f(x) + f(1/x) = 3/x','f(x) = 2/x - x'),
 ('Replace x with one over x to obtain a second linear equation.', 'Eliminate f of one over x. This gives f of x equal to two over x minus x.', 'Integrate that expression from one to two. The result is twice natural log two minus three halves.')),
'Biased coin Bayes update': (
 'Three heads. Is the coin probably double-headed?', 'Pick once: two fair coins, one double-headed. Observe HHH.', 'bars', (('Double-headed weight',1/3),('Fair-coin weight',1/12)),
 ('Three heads has probability one for the double headed coin, and one eighth for a fair coin.', 'Include the prior choices. The weighted likelihoods are one third and one twelfth.', 'Normalize those weights. The chance of the double headed coin is four fifths.')),
'Complex distance circle': (
 'A ratio of distances hides a circle.', 'Find the locus: |z-1| = 2|z+1|.', 'circle', (),
 ('Write z as x plus i y, then square the two nonnegative distances.', 'Collect terms to obtain three x squared plus ten x plus three y squared plus three equal to zero.', 'Complete the square. The centre is minus five thirds, zero, and the radius is four thirds.')),
'Alternating binomial square sum': (
 'Five squared coefficients. One coefficient beats them.', 'Sum (-1)^k C(4,k)² for k=0 through 4.', 'bars', (('k=0',1),('k=1',-16),('k=2',36),('k=3',-16),('k=4',1)),
 ('Read the sum as the coefficient of x to the fourth in a product.', 'The fourth powers of one minus x and one plus x combine into the fourth power of one minus x squared.', 'Its x to the fourth coefficient is four choose two. The sum is six.')),
'Onto function inclusion exclusion': (
 '243 functions. How many actually hit every target?', 'Five labelled inputs. Three labelled targets. Count onto functions.', 'bars', (('All',243),('Subtract',-96),('Restore',3),('Onto',150)),
 ('There are three to the fifth, or two hundred forty three, unrestricted functions.', 'Subtract the functions missing a target: three times two to the fifth, or ninety six.', 'Functions missing two targets were subtracted twice. Restore three to get one hundred fifty onto functions.')),
'Inverse function second derivative': (
 'The inverse second derivative is not a reciprocal.', 'f(x)=x³+x, g=f inverse. Find g double-prime at 2.', 'algebra', ('f(1)=2 → g(2)=1',"g'' = -f''(g)/(f'(g))³",'-6 / 4³ = -3/32'),
 ('First locate the inverse input. Since f of one is two, evaluate the original derivatives at one.', 'Differentiate the inverse identity twice. A minus sign and a cube of the first derivative appear.', 'The original derivatives are four and six. The inverse second derivative is minus three over thirty two.')),
}


def active(content):
    return content.get('story_engine') == ENGINE and content.get('topic') in BRIEFS


def brief(content):
    hook,setup,visual,data,voice = BRIEFS[content['topic']]
    initial={'Buffer after neutralisation':(('HA initially / mmol',20),('A- initially / mmol',10)),
             'Base buffer after acid':(('B initially / mmol',60),('BH+ initially / mmol',0))}
    units={'Rolling energy and height':'Energy / (m v²)', 'Opposed capacitor charge sharing':'Energy / (C V²)',
           'Association apparent molar mass':'Particle count / initial monomer count'}
    return dict(hook=hook,setup=setup,visual=visual,data=data,voice=voice,initial=initial.get(content['topic']),units=units.get(content['topic'],'Exact values · common linear scale'))


def scenes(content,plan):
    b=brief(content)
    # Every mathematical deduction is spoken, rather than only a generic rule.
    return [(0.1,7.5,(plan.get('hook') or b['hook'])+' '+b['setup']),
            (8.1,6.5,b['voice'][0]),(15.1,6.5,b['voice'][1]),(22.1,7.5,b['voice'][2]),
            (30.1,5.5,content['transfer_question'])]
