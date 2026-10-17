"""Chemistry (MHT-CET 2020-23): skeletal structures, Lewis structures and reaction schemes."""

from figlib import Figure
from drawings.chemistry_2425 import (arrow, benzene_with, bromo_methyl_hexene, methoxy_dimethyl_cyclobutane_13,
                                     ring_group)


def text_line(content, width=760, height=120, size=34):
    f = Figure(width, height)
    f.text(width / 2, height / 2 + size * 0.35, content, size=size)
    return f


def lone_pair(f, x, y, vertical=False, r=4, gap=9):
    if vertical:
        f.dot(x, y - gap, r=r), f.dot(x, y + gap, r=r)
    else:
        f.dot(x - gap, y, r=r), f.dot(x + gap, y, r=r)


def carbonyl_group():
    """The carbonyl group: a carbon with two bonds to the left, double-bonded to O."""
    f = Figure(460, 240)
    f.line(20, 20, 130, 110, width=5), f.line(20, 220, 130, 130, width=5)
    f.atom(170, 120, "C", size=110), f.line(240, 104, 320, 104, width=6), f.line(240, 136, 320, 136, width=6)
    f.atom(380, 120, "O", size=110)
    return f


def hydrogen_peroxide():
    """H-O-O-H."""
    return text_line("H − O − O − H", height=140, size=90)


def propanol_to_propan2ol():
    """Propan-1-ol --Al2O3, 623 K--> A --(i) conc. H2SO4, (ii) conc. H2O, heat--> B."""
    f = Figure(760, 140)
    y = 70
    f.text(90, y + 12, "Propan-1-ol", size=30), arrow(f, 180, 290, y, above="Al<sub>2</sub>O<sub>3</sub>", below="623 K", size=24)
    f.text(306, y + 12, "A", size=30), arrow(f, 326, 700, y, above="(i) conc. H<sub>2</sub>SO<sub>4</sub>", below="(ii) conc. H<sub>2</sub>O, Δ", size=24)
    f.text(724, y + 12, "B", size=30)
    return f


def ester_to_aldehyde():
    """Methyl 4-nitrobenzoate is reduced to 4-nitrobenzaldehyde."""
    f = Figure(760, 280)
    for cx, end in ((150, "OCH<sub>3</sub>"), (600, "H")):
        pts = f.ring(cx, 160, r=60, start=-30)
        ring_group(f, pts, 3, "O<sub>2</sub>N", size=24, length=40)
        c = pts[0]
        top = (c[0] + 30, c[1] - 52)
        f.line(*c, *top, width=3)
        f.line(top[0] - 5, top[1], top[0] - 5, top[1] - 40, width=3), f.line(top[0] + 5, top[1], top[0] + 5, top[1] - 40, width=3)
        f.atom(top[0], top[1] - 58, "O", size=26)
        f.line(*top, top[0] + 40, top[1] + 30, width=3), f.atom(top[0] + 56 + (14 if end != "H" else 0), top[1] + 40, end, size=24)
    arrow(f, 300, 480, 120)
    return f


def thiocyanate_scn_triple():
    """Lewis structure :S≡C-N: with three lone pairs on N."""
    f = Figure(760, 180)
    y = 90
    f.atom(150, y, "S", size=110), f.atom(380, y, "C", size=110), f.atom(620, y, "N", size=110)
    for dy in (-12, 0, 12):
        f.line(210, y + dy, 320, y + dy, width=5)
    f.line(440, y, 560, y, width=5)
    lone_pair(f, 82, y, vertical=True, r=7, gap=16), lone_pair(f, 620, y - 76, r=7, gap=16), lone_pair(f, 620, y + 76, r=7, gap=16)
    lone_pair(f, 688, y, vertical=True, r=7, gap=16)
    return f


def thiocyanate_ion():
    """[ :S(three lone pairs)-C≡N: ] with a negative charge."""
    f = Figure(760, 170)
    y = 90
    f.text(30, y + 30, "[", size=110), f.text(730, y + 30, "]", size=110), f.text(752, 46, "−", size=40)
    f.atom(150, y, "S", size=100), f.atom(410, y, "C", size=100), f.atom(620, y, "N", size=100)
    f.line(210, y, 330, y, width=5)
    for dy in (-12, 0, 12):
        f.line(470, y + dy, 560, y + dy, width=5)
    lone_pair(f, 90, y, vertical=True, r=6, gap=14), lone_pair(f, 150, y - 66, r=6, gap=14), lone_pair(f, 150, y + 66, r=6, gap=14)
    lone_pair(f, 680, y, vertical=True, r=6, gap=14)
    return f


def ethyl_methyl_cycloheptanol():
    """Cycloheptane with OH on the top carbon, CH3 on one ring carbon to the left and C2H5 on one to the right."""
    f = Figure(640, 380)
    pts = [(100, 160), (230, 90), (320, 150), (420, 90), (500, 160), (430, 290), (180, 290)]
    f.path(pts, close=True, width=4)
    f.line(320, 150, 320, 80, width=4), f.atom(320, 50, "OH", size=50)
    f.line(100, 160, 30, 120, width=4)
    f.bonds([(500, 160), (560, 100), (630, 140)], width=4)
    return f


def formyl_methyl_benzoic_acid():
    """Benzene ring: CHO at the top, COOH on the lower right, CH3 at the bottom."""
    return benzene_with({0: "CHO", 2: "COOH", 3: "CH<sub>3</sub>"})


def chloro_methyl_pentene():
    """4-Chloro-3-methylpent-2-ene: CH3-CH=C(CH3)-CH(CH3)-Cl, with the methyl of C4 pointing up and Cl down to the right."""
    f = Figure(520, 360)
    pts = [(20, 210), (130, 150), (250, 210), (370, 150)]
    f.bonds(pts, double=(1,), width=4, offset=10)
    f.line(250, 210, 250, 330, width=4), f.line(370, 150, 370, 30, width=4)
    f.line(370, 150, 460, 200, width=4), f.atom(490, 222, "Cl", size=46)
    return f


def chloro_methyl_hexene():
    """3-Chloro-4-methylhex-3-ene: a six-carbon zig-zag with the C3=C4 bond double, Cl on C3 (up) and CH3 on C4 (down)."""
    f = Figure(560, 320)
    pts = [(20, 210), (110, 140), (200, 210), (290, 140), (380, 210), (470, 140)]
    f.bonds(pts, double=(2,), width=4, offset=10)
    f.line(200, 210, 200, 300, width=4), f.line(290, 140, 290, 80, width=4), f.atom(290, 50, "Cl", size=44)
    return f


def alkene_plus_hi():
    """A skeletal 3-methylhexene: zig-zag with a methyl down from C3 and the C3=C4 bond double; HI and peroxide over the arrow."""
    f = Figure(760, 240)
    pts = [(20, 150), (90, 50), (160, 150), (240, 50), (320, 150), (390, 50)]
    f.bonds(pts, double=(2,), width=4, offset=10)
    f.line(160, 150, 160, 220, width=4)
    arrow(f, 440, 740, 110, above="HI", below="Peroxide", size=40)
    return f


def grignard_with_a():
    """C2H5MgBr --A--> C2H6 + Mg(Br)(NH2)."""
    f = Figure(760, 180)
    y = 90
    f.text(110, y + 12, "C<sub>2</sub>H<sub>5</sub>MgBr", size=36), arrow(f, 230, 340, y, above="A", size=30)
    f.text(480, y + 12, "C<sub>2</sub>H<sub>6</sub> + Mg", size=36)
    f.line(570, y - 10, 620, y - 50), f.line(570, y + 10, 620, y + 50)
    f.text(640, y - 50, "Br", size=34, anchor="start"), f.text(630, y + 76, "NH<sub>2</sub>", size=34, anchor="start")
    return f


def isobutane_bromination():
    """CH3-CH(CH3)-CH3 --R--> CH3-CH(CH3)-CH2Br."""
    f = Figure(760, 160)
    y = 110
    f.text(160, y, "CH<sub>3</sub> − CH − CH<sub>3</sub>", size=32), f.line(166, y - 34, 166, y - 60, width=2.5), f.text(166, y - 70, "CH<sub>3</sub>", size=32)
    arrow(f, 300, 400, y - 10, above="R", size=30)
    f.text(570, y, "CH<sub>3</sub> − CH − CH<sub>2</sub>Br", size=32), f.line(546, y - 34, 546, y - 60, width=2.5), f.text(546, y - 70, "CH<sub>3</sub>", size=32)
    return f


def hofmann_elimination():
    """Heating propyl triethylammonium hydroxide (losing water) gives A and N,N-diethylpropan-1-amine."""
    f = Figure(760, 340)
    y, nx = 110, 300
    f.text(20, y + 40, "[", size=130, anchor="start")
    f.text(nx - 14, y + 10, "CH<sub>3</sub>CH<sub>2</sub>CH<sub>2</sub> −", size=28, anchor="end")
    f.text(nx, y + 10, "N", size=28), f.text(nx + 14, y + 10, "− CH<sub>2</sub> − CH<sub>3</sub>", size=28, anchor="start")
    f.text(nx - 16, y - 22, "+", size=20)
    f.line(nx, y - 16, nx, y - 40, width=2), f.text(nx, y - 50, "CH<sub>2</sub> − CH<sub>3</sub>", size=28, anchor="start")
    f.line(nx, y + 20, nx, y + 44, width=2), f.text(nx, y + 74, "CH<sub>2</sub> − CH<sub>3</sub>", size=28, anchor="start")
    f.text(500, y + 40, "]", size=130, anchor="start")
    f.text(550, y + 10, "OH", size=28, anchor="start"), f.text(566, y - 22, "−", size=22)
    arrow(f, 620, 740, y, above="Δ", below="−H<sub>2</sub>O", size=24)
    y2, nx2 = 260, 400
    f.text(nx2 - 14, y2, "A + CH<sub>3</sub> − CH<sub>2</sub> − CH<sub>2</sub> −", size=28, anchor="end")
    f.text(nx2, y2, "N", size=28), f.text(nx2 + 14, y2, "− CH<sub>2</sub> − CH<sub>3</sub>", size=28, anchor="start")
    lone_pair(f, nx2, y2 - 30, r=3, gap=6)
    f.line(nx2, y2 + 10, nx2, y2 + 36, width=2), f.text(nx2, y2 + 66, "CH<sub>2</sub> − CH<sub>3</sub>", size=28, anchor="start")
    return f


def cannizzaro():
    """Methanal + Benzene carbaldehyde --(i) conc. NaOH, (ii) H3O+-->."""
    f = Figure(760, 120)
    f.text(220, 70, "Methanal + Benzene carbaldehyde", size=30), arrow(f, 470, 740, 56, above="i. conc. NaOH", below="ii. H<sub>3</sub>O<sup>+</sup>", size=24)
    return f


def rosenmund():
    """C6H5-C(=O)-Cl --R--> C6H5-C(=O)-H + HCl."""
    f = Figure(760, 170)
    y = 60
    f.text(110, y + 10, "C<sub>6</sub>H<sub>5</sub> − C − Cl", size=34), arrow(f, 230, 330, y, above="R", size=30)
    f.text(560, y + 10, "C<sub>6</sub>H<sub>5</sub> − C − H + HCl", size=34)
    for x in (154, 488):
        f.line(x - 5, y + 24, x - 5, y + 74, width=2.5), f.line(x + 5, y + 24, x + 5, y + 74, width=2.5), f.text(x, y + 110, "O", size=34)
    return f


def sulphanilic_acid():
    """Benzene ring with NH2 at the top and SO3H at the bottom (para)."""
    return benzene_with({0: "NH<sub>2</sub>", 3: "SO<sub>3</sub>H"}, width=420, height=400, centre=(210, 200))


def aniline_to_phenol():
    """Aniline --NaNO2 + HCl, 273 K--> A --H2O, heat--> B + N2."""
    f = Figure(760, 130)
    y = 66
    f.text(70, y + 12, "Aniline", size=32), arrow(f, 140, 370, y, above="NaNO<sub>2</sub> + HCl", below="273 K", size=26)
    f.text(390, y + 12, "A", size=32), arrow(f, 410, 560, y, above="H<sub>2</sub>O", below="Δ", size=26)
    f.text(650, y + 12, "B + N<sub>2</sub>↑", size=32)
    return f


def sulphuric_acid_lewis():
    """Lewis structure of H2SO4: H-O-S-O-H with S double-bonded to two O atoms; lone pairs on each O."""
    f = Figure(560, 400)
    y, sx = 200, 280
    xs = (60, 160, sx, 400, 500)
    for x, lab in zip(xs, ("H", "O", "S", "O", "H")):
        f.atom(x, y, lab, size=70)
    for a, b in zip(xs, xs[1:]):
        f.line(a + 34, y, b - 34, y, width=4)
    for sgn in (-1, 1):
        f.line(sx - 8, y + sgn * 40, sx - 8, y + sgn * 110, width=4), f.line(sx + 8, y + sgn * 40, sx + 8, y + sgn * 110, width=4)
        f.atom(sx, y + sgn * 150, "O", size=70)
        lone_pair(f, sx - 44, y + sgn * 150, vertical=True, r=6, gap=12), lone_pair(f, sx + 44, y + sgn * 150, vertical=True, r=6, gap=12)
    for x in (160, 400):
        lone_pair(f, x, y - 50, r=6, gap=12), lone_pair(f, x, y + 50, r=6, gap=12)
    return f


def carbon_dioxide_lewis():
    """Lewis structure O=C=O with two lone pairs on each oxygen."""
    f = Figure(640, 220)
    y = 110
    f.atom(110, y, "O", size=140), f.atom(320, y, "C", size=140), f.atom(530, y, "O", size=140)
    for x1, x2 in ((180, 250), (390, 460)):
        f.line(x1, y - 14, x2, y - 14, width=6), f.line(x1, y + 14, x2, y + 14, width=6)
    for x in (110, 530):
        lone_pair(f, x, y - 92, r=12, gap=26), lone_pair(f, x, y + 92, r=12, gap=26)
    return f


def lead_chamber_steps():
    """(i) 2SO2(g) + 2NO2(g) -> 2SO3(g) + 2NO; (ii) 2NO(g) + O2(g) -> 2NO2(g); adding: 2SO2(g) + O2(g) -> 2SO3(g)."""
    f = Figure(760, 210)
    f.text(20, 50, "i.", size=32, anchor="start"), f.text(90, 50, "2SO<sub>2(g)</sub> + 2NO<sub>2(g)</sub> → 2SO<sub>3(g)</sub> + 2NO", size=32, anchor="start")
    f.text(20, 110, "ii.", size=32, anchor="start"), f.text(90, 110, "2NO<sub>(g)</sub> + O<sub>2(g)</sub> → 2NO<sub>2(g)</sub>", size=32, anchor="start")
    f.line(80, 140, 740, 140, width=2.5)
    f.text(90, 190, "2SO<sub>2(g)</sub> + O<sub>2(g)</sub> → 2SO<sub>3(g)</sub>", size=32, anchor="start")
    return f


def methyl_octenol():
    """6-Methyloct-4-en-3-ol: a skeletal chain with an ethyl branch at the top left, a double bond in the middle, OH hanging below and an ethyl at the right."""
    f = Figure(580, 360)
    f.bonds([(70, 100), (70, 40), (130, 10)], width=4), f.line(70, 100, 20, 150, width=4)
    f.bonds([(70, 100), (180, 160), (280, 100), (370, 160), (460, 110), (550, 160)], double=(1,), width=4, offset=10)
    f.line(370, 160, 370, 260, width=4), f.atom(370, 300, "OH", size=44)
    return f


def bromophenol():
    """Benzene ring with OH at the top and Br at the bottom (para)."""
    return benzene_with({0: "OH", 3: "Br"}, width=380, height=400, centre=(190, 200))


def halo_dimethyl_heptene(halogen):
    """A skeletal chain: ethyl branch at the top left, a double bond in the middle, a methyl down from the double-bond carbon,
    and the halogen-bearing carbon at the right with a methyl pointing down."""
    f = Figure(560, 360)
    f.bonds([(90, 120), (90, 50), (150, 20)], width=4)
    f.bonds([(20, 170), (90, 120), (180, 190), (270, 120), (360, 170)], double=(2,), width=4, offset=10)
    f.line(180, 190, 180, 290, width=4), f.line(360, 170, 360, 270, width=4)
    f.line(360, 170, 440, 110, width=4), f.atom(480, 94, halogen, size=50)
    return f


def bromo_dimethyl_heptene():
    """2-Bromo-4,5-dimethylhept-3-ene drawn skeletally, Br at the right."""
    return halo_dimethyl_heptene("Br")


def iodo_dimethyl_heptene():
    """2-Iodo-4,5-dimethylhept-3-ene drawn skeletally, I at the right."""
    return halo_dimethyl_heptene("I")


def chloro_methyl_cyclohexanone():
    """Cyclohexanone (C=O on the left) with Cl on the next carbon up and a methyl on the carbon opposite the C=O."""
    f = Figure(520, 300)
    pts = [(160, 60), (290, 60), (350, 150), (290, 240), (160, 240), (100, 150)]
    f.path(pts, close=True, width=4)
    f.line(100, 142, 40, 142, width=4), f.line(100, 158, 40, 158, width=4), f.atom(24, 150, "O", size=44)
    f.line(160, 60, 120, 20, width=4), f.atom(100, 18, "Cl", size=44, anchor="end")
    f.line(350, 150, 450, 150, width=4)
    return f


def hydroxy_pentanone():
    """A skeletal chain with OH on C2 and C=O on C3, ending in a question mark."""
    f = Figure(500, 320)
    pts = [(20, 210), (120, 140), (220, 210), (320, 140), (420, 200)]
    f.polyline(pts, width=4)
    f.line(120, 140, 120, 80, width=4), f.atom(120, 50, "OH", size=50)
    f.line(214, 214, 214, 270, width=4), f.line(226, 214, 226, 270, width=4), f.atom(220, 296, "O", size=50)
    f.text(440, 280, "?", size=50)
    return f


def pentenamine():
    """Pent-3-en-2-amine drawn skeletally: H2N at the lower left, a methyl up from C2, double bond C3=C4."""
    f = Figure(640, 320)
    f.line(100, 270, 220, 140, width=4), f.atom(60, 286, "H<sub>2</sub>N", size=44)
    f.line(220, 140, 220, 30, width=4)
    f.bonds([(220, 140), (380, 290), (500, 160), (620, 290)], double=(1,), width=4, offset=10)
    return f


def friedel_crafts_methylation():
    """A + Chloromethane --anhydrous AlCl3--> 2-Chlorotoluene + 4-Chlorotoluene."""
    f = Figure(760, 110)
    f.text(110, 66, "A + Chloromethane", size=24), arrow(f, 225, 345, 56, above="Anhydrous", below="AlCl<sub>3</sub>", size=18)
    f.text(552, 66, "2-Chlorotoluene + 4-Chlorotoluene", size=24)
    return f


def butadiene_and_acrylonitrile():
    """Buta-1,3-diene (skeletal, both ends double) 'and' acrylonitrile (CH2=CH-CN)."""
    f = Figure(760, 220)
    f.bonds([(20, 190), (110, 60), (200, 190), (290, 60)], double=(0, 2), width=4, offset=10)
    f.text(390, 180, "and", size=44)
    f.bonds([(470, 190), (560, 60), (650, 160)], double=(0,), width=4, offset=10)
    f.text(660, 200, "CN", size=44, anchor="start")
    return f


FIGURES = {
    "PYQ-CHEM-ac50e0697ef5": carbonyl_group,
    "PYQ-CHEM-4a834564b7dd": hydrogen_peroxide,
    "PYQ-CHEM-1df8b6024111": propanol_to_propan2ol,
    "PYQ-CHEM-d2b8b3eefa2f": ester_to_aldehyde,
    "PYQ-CHEM-c751a8df5731": thiocyanate_scn_triple,
    "PYQ-CHEM-8d6583813312": thiocyanate_ion,
    "PYQ-CHEM-8340cdc6e6d1": ethyl_methyl_cycloheptanol,
    "PYQ-CHEM-ef9fe28a4a6f": formyl_methyl_benzoic_acid,
    "PYQ-CHEM-09e972648095": chloro_methyl_pentene,
    "PYQ-CHEM-35ff263e2b60": chloro_methyl_hexene,
    "PYQ-CHEM-e6cda7619c03": alkene_plus_hi,
    "PYQ-CHEM-7faf4c6bce78": grignard_with_a,
    "PYQ-CHEM-2bb80e7775b6": isobutane_bromination,
    "PYQ-CHEM-942c98b87231": hofmann_elimination,
    "PYQ-CHEM-f34e3bce735a": cannizzaro,
    "PYQ-CHEM-26bdc84aea99": rosenmund,
    "PYQ-CHEM-5d08ee8fcf81": sulphanilic_acid,
    "PYQ-CHEM-7d9e7ac3c98b": aniline_to_phenol,
    "PYQ-CHEM-be114120a30e": sulphuric_acid_lewis,
    "PYQ-CHEM-8a8a9cdd71da": carbon_dioxide_lewis,
    "PYQ-CHEM-33926bdd56cb": lead_chamber_steps,
    "PYQ-CHEM-0b177a8e1044": methyl_octenol,
    "PYQ-CHEM-2b885b6dc307": bromophenol,
    "PYQ-CHEM-a94e8811c72d": bromo_dimethyl_heptene,
    "PYQ-CHEM-f36c67db868f": chloro_methyl_cyclohexanone,
    "PYQ-CHEM-7910e6afb180": hydroxy_pentanone,
    "PYQ-CHEM-ce96530c3e72": iodo_dimethyl_heptene,
    "PYQ-CHEM-7060498fd7d5": pentenamine,
    "PYQ-CHEM-da323ff428c0": friedel_crafts_methylation,
    "PYQ-CHEM-41bf3752a943": butadiene_and_acrylonitrile,
    # the same structures as already-drawn 2024 questions
    "PYQ-CHEM-d40995e324bf": bromo_methyl_hexene,
    "PYQ-CHEM-21f14a12bcf0": methoxy_dimethyl_cyclobutane_13,
}
