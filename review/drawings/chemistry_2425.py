"""Chemistry (MHT-CET 2024-25): skeletal structures, reactions and one adsorption graph."""

import math

from figlib import Figure


def stub(f, p, dx, dy, label="", size=30, anchor="middle", lx=0, ly=0):
    """A bond from p to p + (dx, dy), optionally ending in a group label."""
    end = (p[0] + dx, p[1] + dy)
    if label:
        f.line(*p, end[0] - dx * 0.25, end[1] - dy * 0.25)
        f.atom(end[0] + lx, end[1] + ly, label, size=size, anchor=anchor)
    else:
        f.line(*p, *end)
    return end


def ring_group(f, pts, i, label, size=30, length=56, anchor="middle"):
    """A substituent on ring corner i, pointing away from the ring centre."""
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    x, y = pts[i]
    d = math.hypot(x - cx, y - cy)
    ux, uy = (x - cx) / d, (y - cy) / d
    if label:
        f.line(x, y, x + ux * length * 0.7, y + uy * length * 0.7)
        f.atom(x + ux * (length + size * 0.4), y + uy * (length + size * 0.4), label, size=size, anchor=anchor)
    else:
        f.line(x, y, x + ux * length, y + uy * length)


def but_2_ene():
    """But-2-ene as a skeletal zig-zag with the middle bond double."""
    f = Figure(600, 260)
    f.bonds([(20, 220), (190, 40), (380, 220), (570, 40)], double=(1,), width=5, offset=12)
    return f


def benzene_with(groups, size=34, r=70, width=520, height=380, centre=(250, 190)):
    f = Figure(width, height)
    pts = f.ring(*centre, r=r)
    for i, label in groups.items():
        ring_group(f, pts, i, label, size=size)
    return f


def hydroxy_methyl_benzoic_acid():
    """Benzene ring: COOH at the top, OH on the lower right (meta to COOH), CH3 at the bottom (para to COOH)."""
    return benzene_with({0: "COOH", 2: "OH", 3: "CH<sub>3</sub>"})


def ethyl_hydroxy_benzoic_acid():
    """Benzene ring: OH at the top, COOH on the lower right, C2H5 on the lower left."""
    return benzene_with({0: "OH", 2: "COOH", 4: "H<sub>5</sub>C<sub>2</sub>"})


def dimethyl_cyclopentanol():
    """Cyclopentane with OH on the top carbon and a methyl on each of the two neighbouring carbons."""
    f = Figure(420, 360)
    pts = f.ring(210, 200, r=110, sides=5, aromatic=False)
    ring_group(f, pts, 0, "OH", size=34)
    for i, dx in ((1, 80), (4, -80)):
        f.line(*pts[i], pts[i][0] + dx, pts[i][1])
    return f


def alkene_halide(halogen, mirror=False):
    """C1 - C2 = C3(-CH3) - C4(-CH3)(-X): the 4-halo-3-methylpent-2-ene skeleton."""
    f = Figure(560, 300)
    pts = [(20, 200), (130, 80), (250, 200), (370, 80)]
    if mirror:
        pts = [(540 - x, y) for x, y in pts]
    f.bonds(pts, double=(1,), width=4, offset=10)
    f.line(*pts[2], pts[2][0], 280, width=4), f.line(*pts[3], pts[3][0], 10, width=4)
    end = (pts[3][0] + (110 if not mirror else -110), 200)
    f.line(*pts[3], end[0] - (24 if not mirror else -24), end[1] - 24, width=4)
    f.atom(end[0] + (14 if not mirror else -14), end[1] + 10, halogen, size=46)
    return f


def bromo_methyl_pentene():
    """4-Bromo-3-methylpent-2-ene drawn skeletally: CH3-CH=C(CH3)-CH(CH3)-Br."""
    return alkene_halide("Br")


def chloro_methyl_pentene():
    """4-Chloro-3-methylpent-2-ene drawn skeletally (mirror image layout): Cl-CH(CH3)-C(CH3)=CH-CH3."""
    return alkene_halide("Cl", mirror=True)


def hydroxy_methyl_benzaldehyde():
    """Benzene ring: OH at the top, CH3 on the lower right, CHO (drawn H-C=O) on the lower left."""
    f = Figure(460, 400)
    pts = f.ring(240, 170, r=70)
    ring_group(f, pts, 0, "OH", size=30), ring_group(f, pts, 2, "CH<sub>3</sub>", size=30)
    x, y = pts[4]
    c = (x - 45, y + 30)
    f.line(x, y, *c), f.atom(*c, "C", size=28)
    f.line(c[0] - 14, c[1] - 8, c[0] - 70, c[1] - 30), f.atom(c[0] - 84, c[1] - 34, "H", size=28)
    f.line(c[0] - 4, c[1] + 16, c[0] - 4, c[1] + 64), f.line(c[0] + 4, c[1] + 16, c[0] + 4, c[1] + 64)
    f.atom(c[0], c[1] + 82, "O", size=28)
    return f


def methoxy_dimethyl_cyclobutane_13():
    """Cyclobutane (drawn as a diamond): OCH3 (O with a methyl line) on the top carbon and two methyls on the opposite carbon."""
    f = Figure(300, 420)
    top, right, bottom, left = (150, 150), (230, 230), (150, 310), (70, 230)
    f.path([top, right, bottom, left], close=True, width=4)
    f.line(*top, 150, 100, width=4), f.atom(150, 80, "O", size=40), f.line(160, 50, 200, 20, width=4)
    f.line(*bottom, 100, 360, width=4), f.line(*bottom, 200, 360, width=4)
    return f


def ethyl_methyl_cyclopentanol():
    """Cyclopentane with OH on the bottom carbon, CH3 on the left carbon and C2H5 on the right carbon."""
    f = Figure(620, 320)
    pts = [(240, 40), (380, 40), (430, 130), (310, 210), (190, 130)]
    f.path(pts, close=True, width=4)
    f.line(190, 130, 120, 130, width=4), f.atom(70, 140, "CH<sub>3</sub>", size=40)
    f.line(430, 130, 500, 130, width=4), f.atom(556, 140, "C<sub>2</sub>H<sub>5</sub>", size=40)
    f.line(310, 210, 310, 260, width=4), f.atom(310, 296, "OH", size=40)
    return f


def bromo_methyl_hexene():
    """3-Bromo-4-methylhex-3-ene: a six-carbon zig-zag with the C3=C4 bond double, Br on C3 (up) and CH3 on C4 (down)."""
    f = Figure(560, 300)
    pts = [(20, 210), (110, 130), (200, 210), (290, 130), (380, 210), (470, 130)]
    f.bonds(pts, double=(2,), width=4, offset=10)
    f.line(200, 210, 200, 290, width=4)
    f.line(290, 130, 290, 70, width=4), f.atom(290, 50, "Br", size=40)
    return f


def methoxy_dimethyl_cyclobutane_12():
    """Cyclobutane (square): OCH3 on one carbon (O with a methyl line), two methyls on the adjacent carbon."""
    f = Figure(460, 380)
    tl, tr, br, bl = (140, 140), (280, 140), (280, 280), (140, 280)
    f.path([tl, tr, br, bl], close=True, width=4)
    f.line(*tl, 140, 80, width=4), f.atom(140, 60, "O", size=40), f.line(160, 46, 220, 20, width=4)
    f.line(*tr, 350, 90, width=4), f.line(*tr, 380, 160, width=4)
    return f


def sodium_benzenesulphonate():
    """Benzene ring with an SO3- Na+ group."""
    f = Figure(520, 300)
    pts = f.ring(150, 160, r=90, start=-90)
    f.line(*pts[1], 290, 82, width=3)
    f.text(300, 100, "SO<sub>3</sub>Na", size=50, anchor="start")
    f.text(318, 46, "−", size=34), f.text(470, 46, "+", size=34)
    return f


def methoxy_dimethyl_cyclobutane_square():
    """Cyclobutane (square) with two methyls on the top-left carbon and OCH3 on the bottom-right carbon."""
    f = Figure(460, 380)
    tl, tr, br, bl = (110, 60), (270, 60), (270, 220), (110, 220)
    f.path([tl, tr, br, bl], close=True, width=4)
    f.line(*tl, 40, 60, width=4), f.line(*tl, 110, 10, width=4)
    f.line(*br, 300, 280, width=4), f.atom(330, 320, "OCH<sub>3</sub>", size=40)
    return f


def fischer_lactic_acid():
    """Fischer projection: COOH at the top, CH3 at the bottom, H on the left and OH on the right."""
    f = Figure(420, 320)
    c = (210, 160)
    f.line(c[0], 70, c[0], 250, width=3), f.line(90, c[1], 330, c[1], width=3)
    f.atom(c[0], 46, "COOH", size=36), f.atom(c[0], 280, "CH<sub>3</sub>", size=36)
    f.atom(60, c[1], "H", size=36), f.atom(370, c[1], "OH", size=36)
    return f


def bromo_methyl_pentene_gem():
    """4-Bromo-4-methylpent-2-ene: CH3-CH=CH-C(CH3)2-Br, with the two methyls drawn as an X on C4."""
    f = Figure(560, 300)
    pts = [(20, 200), (130, 80), (250, 200), (360, 80)]
    f.bonds(pts, double=(1,), width=4, offset=10)
    f.line(360, 80, 310, 20, width=4), f.line(360, 80, 410, 20, width=4)
    f.line(360, 80, 446, 180, width=4), f.atom(470, 220, "Br", size=46)
    return f


def arrow(f, x1, x2, y, above="", below="", size=28):
    f.line(x1, y, x2, y, arrow=True)
    if above:
        f.text((x1 + x2) / 2, y - 14, above, size=size)
    if below:
        f.text((x1 + x2) / 2, y + size + 6, below, size=size)


def ethyl_methyl_cyclobutanol():
    """Cyclobutane (in perspective) with OH on the right carbon, an ethyl group on the top carbon and a methyl on the bottom carbon."""
    f = Figure(640, 320)
    left, top, right, bottom = (60, 170), (240, 80), (380, 150), (240, 250)
    f.path([left, top, right, bottom], close=True, width=4)
    f.bonds([top, (270, 30), (330, 40)], width=4)
    f.line(*bottom, 300, 280, width=4)
    f.line(*right, 440, 120, width=4), f.atom(490, 120, "OH", size=44)
    return f


def formyl_methyl_benzoic_acid():
    """Benzene ring: CHO at the top, COOH on the lower right, CH3 at the bottom."""
    return benzene_with({0: "CHO", 2: "COOH", 3: "CH<sub>3</sub>"})


def styrene():
    """Benzene ring with a vinyl group (CH=CH2) on its upper-right carbon."""
    f = Figure(440, 340)
    pts = f.ring(170, 190, r=110, start=-60)
    a = pts[0]
    f.line(*a, a[0] + 50, a[1] - 60, width=3)
    f.bonds([(a[0] + 50, a[1] - 60), (a[0] + 110, a[1] - 20)], double=(0,), width=3, offset=8)
    return f


def picric_acid_from_s(labelled=False):
    """S, on warming with water, gives 2,4,6-trinitrophenol (OH at the top, NO2 at both ortho positions and the para position)."""
    f = Figure(700, 440 if labelled else 380)
    pts = f.ring(450, 190, r=90)
    ring_group(f, pts, 0, "OH", size=32), ring_group(f, pts, 1, "NO<sub>2</sub>", size=32)
    ring_group(f, pts, 5, "O<sub>2</sub>N", size=32), ring_group(f, pts, 3, "NO<sub>2</sub>", size=32)
    f.text(40, 200, "(S)" if labelled else "S", size=34)
    arrow(f, 90, 300, 190, above="warm" if labelled else "Warm", below="H<sub>2</sub>O")
    if labelled:
        f.text(450, 426, "2,4,6-trinitrophenol", size=28)
    return f


def picric_acid_labelled():
    """(S), on warming with water, gives 2,4,6-trinitrophenol (OH at the top, NO2 at both ortho positions and the para position)."""
    return picric_acid_from_s(labelled=True)


def chloro_nitro_series(first_plain=False):
    """Three chlorobenzenes I, II, III with increasing nitro substitution."""
    f = Figure(760, 330)
    sets = [{0: "Cl"} if first_plain else {0: "Cl", 3: "NO<sub>2</sub>"},
            {0: "Cl", 3: "NO<sub>2</sub>"} if first_plain else {0: "Cl", 1: "NO<sub>2</sub>", 3: "NO<sub>2</sub>"},
            {0: "Cl", 1: "NO<sub>2</sub>", 5: "O<sub>2</sub>N", 3: "NO<sub>2</sub>"}]
    for (cx, name), groups in zip(((120, "I"), (370, "II"), (620, "III")), sets):
        pts = f.ring(cx, 160, r=56)
        for i, label in groups.items():
            ring_group(f, pts, i, label, size=28, length=40)
        f.text(cx, 320, name, size=30)
    return f


def chloro_nitro_i_ii_iii():
    """I: p-nitrochlorobenzene; II: 2,4-dinitrochlorobenzene; III: 2,4,6-trinitrochlorobenzene."""
    return chloro_nitro_series()


def chloro_i_ii_iii():
    """I: chlorobenzene; II: p-nitrochlorobenzene; III: 2,4,6-trinitrochlorobenzene."""
    return chloro_nitro_series(first_plain=True)


def methylbutene_plus_bromine():
    """2-Methylbut-2-ene (skeletal) + Br2 gives A."""
    f = Figure(760, 280)
    pts = [(30, 240), (170, 100), (260, 240), (400, 90)]
    f.bonds(pts, double=(1,), width=4, offset=10)
    f.line(170, 100, 170, 20, width=4)
    f.text(430, 210, "+ Br<sub>2</sub>", size=44, anchor="start"), arrow(f, 580, 700, 196), f.text(730, 210, "A", size=44)
    return f


def polymer_text(units, n_x, sub=None, size=52, width=760, height=300):
    """A repeating unit written as text between brackets with subscript n; `sub` is (x, label) for a group hung below."""
    f = Figure(width, height)
    y = 90
    f.text(width / 2, y + size * 0.35, units, size=size)
    half = n_x
    for x in (width / 2 - half, width / 2 + half):
        f.line(x, y - 50, x, y + 50, width=4)
    f.line(width / 2 - half - 40, y, width / 2 - half, y, width=4), f.line(width / 2 + half, y, width / 2 + half + 30, y, width=4)
    f.text(width / 2 + half + 24, y + 70, "<i>n</i>", size=size * 0.8)
    if sub:
        x, label = sub
        f.line(x, y + 30, x, y + 120, width=4), f.text(x, y + 170, label, size=size)
    return f


def polyacrylamide():
    """-[CH2-CH(CONH2)]-n."""
    return polymer_text("CH<sub>2</sub> − CH", 160, sub=(440, "CONH<sub>2</sub>"))


def polyisoprene():
    """-[CH2-C(CH3)=CH-CH2]-n ?"""
    f = polymer_text("CH<sub>2</sub> − C = CH − CH<sub>2</sub>", 240, sub=(318, "CH<sub>3</sub>"), size=46)
    f.text(680, 104, "?", size=46)
    return f


def amide_linkage():
    """The amide linkage -C(=O)-NH- followed by the words 'linkage?'."""
    f = Figure(640, 320)
    y = 170
    f.line(20, y, 60, y, width=3), f.atom(90, y, "C", size=50), f.line(120, y, 170, y, width=3), f.atom(200, y, "N", size=50)
    f.line(230, y, 270, y, width=3), f.text(280, y + 18, "linkage ?", size=46, anchor="start")
    f.line(84, y - 34, 84, y - 90, width=3), f.line(96, y - 34, 96, y - 90, width=3), f.atom(90, y - 120, "O", size=50)
    f.line(200, y + 34, 200, y + 80, width=3), f.atom(200, y + 116, "H", size=50)
    return f


def butadiene_and_acrylonitrile():
    """Buta-1,3-diene (skeletal, both ends double) 'and' acrylonitrile (CH2=CH-CN) ?"""
    f = Figure(760, 220)
    f.bonds([(20, 190), (110, 60), (200, 190), (290, 60)], double=(0, 2), width=4, offset=10)
    f.text(360, 180, "and", size=44)
    f.bonds([(430, 190), (520, 60), (610, 160)], double=(0,), width=4, offset=10)
    f.text(620, 190, "CN ?", size=44, anchor="start")
    return f


def phenol_with_cro3():
    """Phenol, with CrO3, gives the product."""
    f = Figure(760, 220)
    pts = f.ring(110, 110, r=90, start=0)
    f.line(*pts[0], 250, 110, width=3), f.text(290, 126, "OH", size=44)
    arrow(f, 350, 520, 110, above="CrO<sub>3</sub>", size=36), f.text(640, 126, "product", size=44)
    return f


def benzoyl_chloride_to_acid():
    """Benzoyl chloride, with reagent R, gives benzoic acid."""
    f = Figure(760, 320)
    for cx, end in ((110, "Cl"), (520, "OH")):
        pts = f.ring(cx, 210, r=80, start=-30)
        c = pts[0]
        top = (c[0], c[1] - 70)
        f.line(*c, *top, width=3)
        f.line(top[0] - 6, top[1], top[0] - 6, top[1] - 50, width=3), f.line(top[0] + 6, top[1], top[0] + 6, top[1] - 50, width=3)
        f.atom(top[0], top[1] - 72, "O", size=40)
        f.line(*top, top[0] + 50, top[1] + 50, width=3), f.atom(top[0] + 74, top[1] + 74, end, size=40)
    arrow(f, 290, 400, 230, above="R", size=30)
    return f


def alkyne_to_alkene():
    """-C≡C- to C=C (with the four substituent bonds of the alkene drawn)."""
    f = Figure(760, 200)
    y = 100
    f.text(160, y + 20, "− C ≡ C −", size=56), f.text(360, y + 20, "to", size=56)
    f.text(560, y + 20, "C = C", size=56)
    for x, sx in ((480, -1), (640, 1)):
        f.line(x, y, x + sx * 80, y - 70, width=3), f.line(x, y, x + sx * 80, y + 70, width=3)
    return f


def two_isopropyl_branches():
    """2,3-Dimethylbutane drawn skeletally: a central bond with a forked (Y-shaped) carbon at each end."""
    f = Figure(760, 280)
    a, b = (190, 140), (570, 140)
    f.line(*a, *b, width=8)
    f.line(*a, 20, 40, width=8), f.line(*a, 20, 240, width=8)
    f.line(*b, 740, 40, width=8), f.line(*b, 740, 240, width=8)
    return f


def ethanol_to_ethane():
    """Ethanol --SOCl2, heat--> X --Mg, dry ether--> Y --NH3--> Z + Mg(Cl)(NH2)."""
    f = Figure(760, 170)
    y = 90
    f.text(70, y + 10, "Ethanol", size=28), arrow(f, 130, 230, y, above="SOCl<sub>2</sub>", below="Δ", size=22)
    f.text(248, y + 10, "X", size=28), arrow(f, 268, 410, y, above="Mg", below="Dry ether", size=22)
    f.text(428, y + 10, "Y", size=28), arrow(f, 448, 540, y, above="NH<sub>3</sub>", size=22)
    f.text(590, y + 10, "Z + Mg", size=28)
    f.line(636, y - 6, 680, y - 46), f.line(636, y + 6, 680, y + 46)
    f.text(704, y - 46, "Cl", size=28), f.text(714, y + 62, "NH<sub>2</sub>", size=28)
    return f


def benzonitrile_grignard():
    """Benzonitrile --C6H5MgBr, dry ether--> A --H3O+--> B + NH3 + Mg(Br)(OH)."""
    f = Figure(760, 220)
    f.text(110, 66, "Benzonitrile", size=32), arrow(f, 220, 410, 56, above="C<sub>6</sub>H<sub>5</sub>MgBr", below="Dry ether", size=24)
    f.text(430, 66, "A", size=32), arrow(f, 460, 600, 56, above="H<sub>3</sub>O<sup>+</sup>", size=24)
    f.text(520, 160, "B + NH<sub>3</sub> + Mg", size=32)
    f.line(640, 140, 680, 100), f.line(640, 160, 680, 200)
    f.text(704, 100, "Br", size=32), f.text(712, 212, "OH", size=32)
    return f


def ethylbenzene_oxidation():
    """C6H5-CH2-CH3 --(i) alk. KMnO4, (ii) H3O+--> product."""
    f = Figure(760, 120)
    f.text(160, 70, "C<sub>6</sub>H<sub>5</sub> − CH<sub>2</sub> − CH<sub>3</sub>", size=34)
    arrow(f, 320, 560, 56, above="(i) alk. KMnO<sub>4</sub>", below="(ii) H<sub>3</sub>O<sup>+</sup>", size=24)
    f.text(660, 70, "product", size=36)
    return f


def aniline_to_diazonium():
    """Aniline, with reagent A, gives benzenediazonium chloride."""
    f = Figure(760, 350)
    for cx, label in ((120, "NH<sub>2</sub>"), (580, "N<sub>2</sub>Cl")):
        pts = f.ring(cx, 230, r=90)
        ring_group(f, pts, 0, label, size=36)
    f.text(556, 46, "+", size=26), f.text(618, 46, "−", size=26)
    arrow(f, 260, 430, 230, above="A", size=32)
    return f


def tetrathionate():
    """Tetrathionate ion: -O-S(=O)2-S-S-S(=O)2-O-, with the four S atoms numbered 1 to 4."""
    f = Figure(640, 300)
    y = 150
    xs = [50, 150, 250, 350, 450, 550]
    labels = ["O", "S", "S", "S", "S", "O"]
    for x, lab in zip(xs, labels):
        f.atom(x, y, lab, size=46)
    for x1, x2 in zip(xs, xs[1:]):
        f.line(x1 + 26, y, x2 - 26, y, width=3)
    f.text(16, y - 10, "−", size=30), f.text(588, y - 10, "−", size=30)
    for i, x in enumerate(xs[1:5]):
        f.text(x + 24, y - 34, str(i + 1), size=28)
    for x in (150, 450):
        for sgn in (-1, 1):
            f.line(x - 6, y + sgn * 30, x - 6, y + sgn * 92, width=3), f.line(x + 6, y + sgn * 30, x + 6, y + sgn * 92, width=3)
            f.atom(x, y + sgn * 118, "O", size=46)
    return f


def ethanol_skeletal():
    """Ethanol drawn skeletally: two bonds in an inverted V ending in OH."""
    f = Figure(640, 300)
    f.line(20, 200, 240, 30, width=8), f.line(240, 30, 450, 190, width=8)
    f.atom(540, 240, "OH", size=90)
    return f


def adsorption_isobars():
    """Extent of adsorption x/m against pressure at 195 K (highest curve), 210 K, 244 K and 273 K (lowest)."""
    f = Figure(560, 360)
    ox, oy = 70, 330
    f.axes(ox, oy, 380, 300, size=28)
    for i, (t, top) in enumerate(((195, 50), (210, 90), (244, 140), (273, 190))):
        sat = oy - top
        f.curve(lambda x, s=sat: oy - s * (1 - math.exp(-(x - ox) / (30 + 12 * i))) * (1 + (x - ox) / 2000), ox, 340)
        f.text(352, oy - (oy - top) * 1.135 + 10, f"{t} K", size=30, anchor="start")
    f.text(34, 160, "<i>x</i>", size=30), f.line(18, 172, 50, 172, width=2), f.text(34, 204, "<i>m</i>", size=30)
    return f


FIGURES = {
    "PYQ-CHEM-2bc21a986696": ethyl_methyl_cyclobutanol,
    "PYQ-CHEM-7bcc101724dc": bromo_methyl_hexene,
    "PYQ-CHEM-9f80e236c9c0": formyl_methyl_benzoic_acid,
    "PYQ-CHEM-c90656807d53": methoxy_dimethyl_cyclobutane_12,
    "PYQ-CHEM-7acdabcbada2": styrene,
    "PYQ-CHEM-2b4a89acd904": picric_acid_from_s,
    "PYQ-CHEM-92d24bd3217d": chloro_nitro_i_ii_iii,
    "PYQ-CHEM-b3b5f5db0da3": picric_acid_labelled,
    "PYQ-CHEM-e1f0f578aab4": chloro_i_ii_iii,
    "PYQ-CHEM-451990449c26": methylbutene_plus_bromine,
    "PYQ-CHEM-888ec5114af7": polyacrylamide,
    "PYQ-CHEM-50ae26cc108b": amide_linkage,
    "PYQ-CHEM-fa3c458eda6e": butadiene_and_acrylonitrile,
    "PYQ-CHEM-f1e2408ad6c3": polyisoprene,
    "PYQ-CHEM-d897a70de306": phenol_with_cro3,
    "PYQ-CHEM-f1db6312e7dd": phenol_with_cro3,
    "PYQ-CHEM-d91ca3571b76": benzoyl_chloride_to_acid,
    "PYQ-CHEM-b256fe1297d9": alkyne_to_alkene,
    "PYQ-CHEM-9371d0e2e4b0": two_isopropyl_branches,
    "PYQ-CHEM-4ed0886a59f2": ethanol_to_ethane,
    "PYQ-CHEM-d682fb1abc8e": benzonitrile_grignard,
    "PYQ-CHEM-fc7fdd61431b": ethylbenzene_oxidation,
    "PYQ-CHEM-0b12db959229": aniline_to_diazonium,
    "PYQ-CHEM-f880883eacec": tetrathionate,
    "PYQ-CHEM-c6e825ff9599": ethanol_skeletal,
    "PYQ-CHEM-4bf3c1709864": adsorption_isobars,
    "PYQ-CHEM-262f84d16cae": but_2_ene,
    "PYQ-CHEM-d962aeb838ba": hydroxy_methyl_benzoic_acid,
    "PYQ-CHEM-73279a7baecd": ethyl_hydroxy_benzoic_acid,
    "PYQ-CHEM-8f2a91151611": dimethyl_cyclopentanol,
    "PYQ-CHEM-170323fabf44": bromo_methyl_pentene,
    "PYQ-CHEM-4abe6ea9f441": hydroxy_methyl_benzaldehyde,
    "PYQ-CHEM-864818ea1a73": methoxy_dimethyl_cyclobutane_13,
    "PYQ-CHEM-53970f74adfe": ethyl_methyl_cyclopentanol,
    "PYQ-CHEM-76cb7ede7996": bromo_methyl_hexene,
    "PYQ-CHEM-d6f993cfb7ca": methoxy_dimethyl_cyclobutane_12,
    "PYQ-CHEM-63714c5fcbbd": chloro_methyl_pentene,
    "PYQ-CHEM-5635838c7fd1": sodium_benzenesulphonate,
    "PYQ-CHEM-eeeef984ca9d": methoxy_dimethyl_cyclobutane_square,
    "PYQ-CHEM-b0bcc046ea5f": methoxy_dimethyl_cyclobutane_13,
    "PYQ-CHEM-b476c8ed19f9": fischer_lactic_acid,
    "PYQ-CHEM-b83c5f7c20f7": bromo_methyl_pentene_gem,
    "PYQ-CHEM-b85f21c2adb7": dimethyl_cyclopentanol,
}
