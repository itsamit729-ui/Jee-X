"""Chemistry: structures and reaction schemes."""

from figlib import Figure


def bond(f, x1, y1, x2, y2, double=False, gap=5, width=3):
    """A bond; `double` draws two parallel lines."""
    if not double:
        f.line(x1, y1, x2, y2, width=width)
        return
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    nx, ny = -(y2 - y1) / length * gap, (x2 - x1) / length * gap
    f.line(x1 + nx, y1 + ny, x2 + nx, y2 + ny, width=width), f.line(x1 - nx, y1 - ny, x2 - nx, y2 - ny, width=width)


def reaction_arrow(f, x1, x2, y, above="", below="", below2="", size=26):
    f.line(x1, y, x2, y, arrow=True)
    if above:
        f.text((x1 + x2) / 2, y - 16, above, size=size)
    if below:
        f.text((x1 + x2) / 2, y + 34, below, size=size)
    if below2:
        f.text((x1 + x2) / 2, y + 68, below2, size=size)


def phenol_to_quinone():
    """Phenol, under condition A, gives p-benzoquinone."""
    f = Figure(660, 370)
    p = f.ring(138, 208, r=64)
    bond(f, *p[0], 138, 98), f.text(152, 84, "OH", size=34)
    reaction_arrow(f, 244, 432, 208, above="A", size=34)
    q = f.ring(526, 208, r=64, double=(1, 4))
    bond(f, *q[0], 526, 88, double=True), bond(f, *q[3], 526, 328, double=True)
    f.text(526, 76, "O", size=34), f.text(526, 362, "O", size=34)
    return f


def four_benzene_derivatives():
    """(I) phenol, (II) benzyl alcohol, (III) benzyl alcohol with an ethyl group on the ring, (IV) phenol with an ethyl group on the ring."""
    f = Figure(1000, 330)
    spec = ((92, "OH", False, "I"), (306, "CH<sub>2</sub>OH", False, "II"),
            (540, "CH<sub>2</sub>OH", True, "III"), (800, "OH", True, "IV"))
    for cx, group, ethyl, name in spec:
        p = f.ring(cx, 182, r=54, aromatic=False)
        f.circle(cx, 182, 32, width=2.5)
        bond(f, *p[0], cx, 88), f.text(cx + (0 if group == "OH" else 30), 70, group, size=28)
        if ethyl:
            bond(f, *p[2], p[2][0] + 34, p[2][1] + 20)
            f.text(p[2][0] + 42, p[2][1] + 42, "C<sub>2</sub>H<sub>5</sub>", size=28, anchor="start")
        f.text(cx, 304, f"({name})", size=28)
    return f


def methylbenzoic_acid():
    """A benzene ring carrying COOH and, on the next carbon, CH3."""
    f = Figure(660, 410)
    p = f.ring(250, 208, r=118)
    bond(f, *p[1], p[1][0] + 78, p[1][1] - 62), bond(f, *p[2], p[2][0] + 66, p[2][1] + 52)
    f.text(p[1][0] + 88, p[1][1] - 54, "COOH", size=46, anchor="start")
    f.text(p[2][0] + 70, p[2][1] + 88, "CH<sub>3</sub>", size=46, anchor="start")
    return f


def benzene_to_benzaldehyde():
    """Benzene with CO and HCl, anhydrous AlCl3, high pressure, gives benzaldehyde."""
    f = Figure(1000, 300)
    f.ring(98, 122, r=64)
    reaction_arrow(f, 262, 580, 122, above="CO, HCl", below="Anhyd. AlCl<sub>3</sub>", below2="high pressure", size=30)
    p = f.ring(768, 122, r=64)
    bond(f, *p[1], p[1][0] + 40, p[1][1] - 30), f.text(p[1][0] + 46, p[1][1] - 30, "CHO", size=32, anchor="start")
    f.text(98, 264, "(Benzene)", size=30), f.text(790, 264, "(Benzaldehyde)", size=30)
    return f


def aniline_diazotisation():
    """Aniline with nitrous acid (NaNO2/HCl, 273 K) gives A; A with water on heating gives phenol and N2."""
    f = Figure(1000, 300)
    p = f.ring(72, 158, r=46)
    bond(f, *p[1], p[1][0] + 30, p[1][1] - 22), f.text(p[1][0] + 34, p[1][1] - 24, "NH<sub>2</sub>", size=26, anchor="start")
    f.text(232, 168, "+  HO–NO<sub>2</sub>", size=28), f.text(252, 202, "conc.", size=24)
    reaction_arrow(f, 340, 528, 158, above="NaNO<sub>2</sub>/HCl", below="273 K")
    f.text(556, 168, "A", size=30)
    reaction_arrow(f, 590, 748, 158, above="H<sub>2</sub>O", below="Δ")
    q = f.ring(818, 158, r=46)
    bond(f, *q[1], q[1][0] + 30, q[1][1] - 22), f.text(q[1][0] + 34, q[1][1] - 24, "OH", size=26, anchor="start")
    f.text(940, 168, "+  N<sub>2</sub>", size=28)
    return f


def azo_coupling():
    """Benzenediazonium chloride and phenol, in base, couple to give p-hydroxyazobenzene and HCl."""
    f = Figure(1000, 150)
    y, r = 74, 34
    f.ring(48, y, r=r, start=0), bond(f, 82, y, 104, y)
    f.text(108, y + 10, "N<sup>⊕</sup>≡N Cl<sup>⊖</sup>", size=26, anchor="start")
    f.text(272, y + 10, "+", size=28)
    f.ring(338, y, r=r, start=0), bond(f, 372, y, 394, y), f.text(398, y + 10, "OH", size=26, anchor="start")
    reaction_arrow(f, 458, 546, y, above="OH<sup>−</sup>", size=24)
    f.ring(596, y, r=r, start=0), bond(f, 630, y, 648, y), f.text(652, y + 10, "N=N", size=26, anchor="start")
    bond(f, 712, y, 728, y), f.ring(762, y, r=r, start=0), bond(f, 796, y, 816, y)
    f.text(820, y + 10, "OH", size=26, anchor="start"), f.text(928, y + 10, "+  HCl", size=26)
    return f


def diethyl_methoxycyclohexane():
    """Cyclohexane with a methoxy group on one carbon and two ethyl groups on the carbon opposite."""
    f = Figure(660, 380)
    p = f.ring(300, 190, r=98, aromatic=False, start=0)
    bond(f, 178, 190, *p[3]), f.text(170, 206, "CH<sub>3</sub>–O", size=44, anchor="end")
    for dy in (-92, 92):
        f.polyline([p[0], (p[0][0] + 58, 190 + dy), (p[0][0] + 170, 190 + dy)])
    return f


def ethyl_methyl_cycloheptanol():
    """A seven-membered ring with OH on one carbon, an ethyl group two carbons along one way and a methyl group two carbons along the other way."""
    f = Figure(660, 400)
    ring = [(98, 204), (188, 108), (276, 204), (364, 108), (454, 204), (408, 360), (140, 360)]
    f.path(ring, close=True, width=4)
    bond(f, 276, 204, 276, 86, width=4), f.text(296, 62, "OH", size=46)
    bond(f, 98, 204, 14, 128, width=4), f.polyline([(454, 204), (540, 114), (626, 208)], width=4)
    return f


def keto_enol():
    """A keto form, with a hydrogen on the alpha carbon, in equilibrium with its enol form."""
    f = Figure(1000, 220)
    y = 82
    f.text(112, y + 12, "C", size=34), f.text(222, y + 12, "C", size=34)
    bond(f, 36, y, 88, y), bond(f, 136, y, 198, y), bond(f, 246, y, 298, y)
    bond(f, 112, 26, 112, 54), bond(f, 112, 100, 112, 140), f.text(112, 176, "H", size=34)
    bond(f, 222, 102, 222, 140, double=True), f.text(222, 178, "O", size=34), f.text(146, 50, "α", size=28)
    f.line(372, y - 7, 600, y - 7, arrow=True), f.line(600, y + 7, 372, y + 7, arrow=True)
    f.text(712, y + 12, "C", size=34), f.text(832, y + 12, "C", size=34)
    bond(f, 636, y, 688, y), bond(f, 738, y, 808, y, double=True), bond(f, 856, y, 908, y)
    bond(f, 712, 26, 712, 54), bond(f, 832, 100, 832, 138), f.text(832, 176, "O", size=34)
    bond(f, 852, 164, 892, 164), f.text(912, 176, "H", size=34)
    return f


def pentenamine():
    """Skeletal formula: a five-carbon chain with a double bond between carbons 3 and 4 and NH2 on carbon 2."""
    f = Figure(680, 300)
    f.bonds([(22, 196), (148, 102), (262, 234), (392, 102)], double=(1,), width=4)
    bond(f, 392, 102, 392, 36, width=4), bond(f, 392, 102, 486, 196, width=4)
    f.text(498, 246, "NH<sub>2</sub>", size=50, anchor="start")
    return f


def methylhexene_with_hi():
    """3-Methylhex-3-ene (skeletal formula) treated with HI gives the product."""
    f = Figure(1000, 200)
    f.bonds([(36, 98), (108, 52), (180, 98), (252, 52), (324, 98), (396, 52)], double=(2,))
    bond(f, 180, 98, 180, 176)
    reaction_arrow(f, 478, 706, 98, above="HI", size=34), f.text(840, 110, "Product", size=36)
    return f


def bromopropane_sequence():
    """2-Bromopropane with alcoholic KOH on heating gives A; A with HBr (no peroxide) gives B."""
    f = Figure(1000, 250)
    y = 102
    f.text(56, y + 10, "CH<sub>3</sub>", size=28), bond(f, 92, y, 148, y), f.text(178, y + 10, "CH", size=28)
    bond(f, 206, y, 262, y), f.text(300, y + 10, "CH<sub>3</sub>", size=28)
    bond(f, 178, y + 18, 178, y + 78), f.text(178, y + 112, "Br", size=28)
    reaction_arrow(f, 356, 598, y, above="Alc. KOH", below="Δ", size=28), f.text(628, y + 10, "A", size=32)
    reaction_arrow(f, 664, 906, y, above="HBr", below="Peroxide absent", size=28), f.text(938, y + 10, "B", size=32)
    return f


def ester_with_dibal():
    """An ester R-CO-O-R' with DIBAL-H followed by H3O+ gives the product."""
    f = Figure(1000, 200)
    y = 112
    f.text(26, y + 12, "R", size=34), bond(f, 54, y, 96, y), f.text(120, y + 12, "C", size=34)
    bond(f, 146, y, 188, y), f.text(214, y + 12, "O", size=34), bond(f, 242, y, 284, y), f.text(316, y + 12, "R′", size=34)
    bond(f, 120, y - 22, 120, y - 56, double=True), f.text(120, y - 68, "O", size=34)
    reaction_arrow(f, 400, 760, y, above="DIBAL-H", below="H<sub>3</sub>O<sup>+</sup>", size=32)
    f.text(880, y + 12, "Product", size=36)
    return f


def dimethylbutanol_with_acid():
    """3,3-Dimethylbutan-2-ol with H2SO4 gives the major product X."""
    f = Figure(1000, 260)
    y = 132
    f.text(42, y + 10, "CH<sub>3</sub>", size=30), bond(f, 80, y, 136, y), f.text(160, y + 10, "C", size=30)
    bond(f, 184, y, 264, y), f.text(288, y + 10, "C", size=30), bond(f, 312, y, 368, y), f.text(410, y + 10, "CH<sub>3</sub>", size=30)
    bond(f, 160, y - 20, 160, y - 62), bond(f, 160, y + 22, 160, y + 62)
    bond(f, 288, y - 20, 288, y - 62), bond(f, 288, y + 22, 288, y + 62)
    f.text(166, y - 74, "CH<sub>3</sub>", size=30), f.text(166, y + 100, "CH<sub>3</sub>", size=30)
    f.text(288, y - 74, "H", size=30), f.text(298, y + 100, "OH", size=30)
    f.text(488, y + 10, "+", size=30), f.text(574, y + 10, "H<sub>2</sub>SO<sub>4</sub>", size=30)
    reaction_arrow(f, 664, 790, y), f.text(828, y + 10, "X", size=32), f.text(848, y + 78, "(major product)", size=28)
    return f


FIGURES = {
    "PYQ-CHEM-208f867cb369": phenol_to_quinone,
    "PYQ-CHEM-5a03bf5abf31": four_benzene_derivatives,
    "PYQ-CHEM-552e0d36885e": methylbenzoic_acid,
    "PYQ-CHEM-dba8fa24d900": benzene_to_benzaldehyde,
    "PYQ-CHEM-1c496861dcde": aniline_diazotisation,
    "PYQ-CHEM-ea34579fcead": azo_coupling,
    "PYQ-CHEM-2fd540219a99": diethyl_methoxycyclohexane,
    "PYQ-CHEM-4888d55430f0": ethyl_methyl_cycloheptanol,
    "PYQ-CHEM-587ee328d374": keto_enol,
    "PYQ-CHEM-ac918123d4f7": pentenamine,
    "PYQ-CHEM-050fca2dd2c3": methylhexene_with_hi,
    "PYQ-CHEM-881b1c73460a": bromopropane_sequence,
    "PYQ-CHEM-59e6848a7363": ester_with_dibal,
    "PYQ-CHEM-a47472f46475": dimethylbutanol_with_acid,
}
