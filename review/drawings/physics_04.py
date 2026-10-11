"""Physics: dual nature (part 2), electromagnetic induction."""

import math

from figlib import INK, Figure, coil


def crosses(f, xs, ys, size=9, skip=()):
    """Field into the page: a cross at every (x, y) except those in `skip`."""
    for y in ys:
        for x in xs:
            if (x, y) not in skip:
                f.line(x - size, y - size, x + size, y + size, width=2.5), f.line(x - size, y + size, x + size, y - size, width=2.5)


def vcoil(f, x, y1, y2, turns=4, radius=15):
    """A coil in a vertical wire from y1 down to y2."""
    with f.rotated(90, x, y1):
        coil(f, x, x + (y2 - y1), y1, turns=turns, radius=radius)


def vec_label(f, x, y, letter, size=30):
    """A letter with a vector arrow over it."""
    f.text(x, y, f"<i>{letter}</i>", size=size)
    f.line(x - 12, y - size * 0.82, x + 12, y - size * 0.82, width=2, arrow=True)


def stopping_potential_line():
    """Stopping potential V0 against frequency: a straight line cutting the x-axis at A and the y-axis at B (below O)."""
    f = Figure(500, 450)
    f.vector(138, 425, 138, 35), f.vector(138, 218, 468, 218)
    f.line(138, 368, 330, 58)
    f.text(108, 52, "Y", size=30), f.text(486, 228, "X", size=30), f.text(116, 232, "O", size=28)
    f.text(214, 202, "A", size=28), f.text(116, 380, "B", size=28)
    f.text(42, 222, "<i>V</i><sub>0</sub>", size=30), f.vector(68, 226, 68, 168, width=2)
    return f


def r_l_between_a_b():
    """A resistor R and an inductor L in series between terminals A and B; current i enters at A."""
    f = Figure(640, 450)
    left, right, top, bottom = 62, 548, 78, 372
    f.line(left, bottom - 6, left, top), f.line(left, top, 140, top), f.resistor(140, 240, top, height=18)
    f.line(240, top, 370, top), coil(f, 370, 470, top, turns=3, radius=20), f.line(470, top, right, top)
    f.line(right, top, right, bottom - 6)
    f.terminal(left, bottom), f.terminal(right, bottom)
    f.arrowhead(left, 215, 270, size=20)
    f.text(190, 150, "<i>R</i>", size=34), f.text(420, 150, "<i>L</i>", size=34), f.text(92, 248, "<i>i</i>", size=34)
    f.text(left, 425, "A", size=32), f.text(right, 425, "B", size=32)
    return f


def two_bulbs_r_l():
    """Bulb B1 in series with R, and bulb B2 in series with L, in parallel; switch S and a battery complete the circuit."""
    f = Figure(660, 440)
    left, node, right, top, mid, bottom = 36, 374, 602, 96, 248, 402
    f.line(left, top, 105, top), f.resistor(105, 190, top), f.line(190, top, 262, top), f.line(322, top, node, top)
    f.circle(292, top, 30, fill=INK), f.circle(292, mid, 30, fill=INK)
    f.line(left, mid, 70, mid), coil(f, 70, 190, mid, turns=7, radius=17), f.line(190, mid, 262, mid)
    f.polyline([(322, mid), (node, mid), (node, top)])
    f.line(node, top, 436, top), f.line(442, top - 4, 514, top - 44), f.line(546, top, right, top)
    f.dot(node, top), f.dot(left, mid), f.dot(436, top, r=6), f.dot(540, top, r=6)
    f.line(left, top, left, bottom), f.line(right, top, right, bottom)
    f.line(left, bottom, 130, bottom), f.cell(140, bottom, gap=18, long=28, short=15)
    f.line(149, bottom, 158, bottom), f.cell(167, bottom, gap=18, long=28, short=15), f.line(176, bottom, right, bottom)
    f.text(147, 152, "<i>R</i>", size=32), f.text(130, 312, "<i>L</i>", size=32), f.text(470, 50, "<i>S</i>", size=32)
    f.text(292, 46, "<i>B</i><sub>1</sub>", size=32), f.text(292, 318, "<i>B</i><sub>2</sub>", size=32)
    return f


def induced_emf_graph_options():
    """Four options A-D for induced e.m.f. e against dI/dt."""
    f = Figure(1000, 280)
    f.vector(35, 172, 35, 12), f.vector(35, 172, 185, 172), f.line(35, 172, 165, 45)                 # A
    f.text(14, 44, "e", size=24), f.text(165, 204, "dI/dt", size=24), f.text(14, 196, "0", size=22)
    for ox, name in ((288, "B"), (555, "C"), (830, "D")):
        f.vector(ox, 25, ox, 192), f.vector(ox, 25, ox + 155, 25)
        f.text(ox - 22, 118, "e", size=24), f.text(ox + 150, 58, "dI/dt", size=24)
        if name == "B":
            f.line(ox, 108, ox + 140, 108)
        elif name == "C":
            f.line(ox, 25, ox + 150, 138)
        else:
            f.polyline([(ox + 128 * t, 25 + 160 * t ** 3.2) for t in [i / 40 for i in range(41)]])
    for x, name in ((88, "A"), (366, "B"), (636, "C"), (905, "D")):
        f.text(x, 262, name, size=28)
    return f


def inductor_combinations():
    """Four arrangements (P)-(S) of the coils L1, L2 and L3 between A and B."""
    f = Figure(1000, 980)

    def name(x, y, n):
        f.text(x, y, f"<i>L</i><sub>{n}</sub>", size=24)

    # (P) all three in series
    f.line(55, 52, 105, 52), coil(f, 105, 225, 52, turns=7, radius=17), f.line(225, 52, 265, 52)
    coil(f, 265, 385, 52, turns=7, radius=17), f.line(385, 52, 425, 52), coil(f, 425, 545, 52, turns=7, radius=17)
    f.line(545, 52, 610, 52)
    f.text(40, 62, "A", size=24), f.text(628, 62, "B", size=24), name(152, 106, 1), name(325, 106, 2), name(480, 106, 3)
    f.text(328, 166, "(P)", size=24)
    # (Q) all three in parallel
    for y, n in ((240, 1), (318, 2), (400, 3)):
        f.line(112, y, 150, y), coil(f, 150, 290, y, turns=8, radius=17), f.line(290, y, 320, y)
        name(215, y - 36, n)
    f.line(112, 240, 112, 400), f.line(320, 240, 320, 400), f.line(62, 318, 112, 318), f.line(320, 318, 368, 318)
    f.text(46, 328, "A", size=24), f.text(384, 328, "B", size=24), f.text(226, 496, "(Q)", size=24)
    # (R) L1 and L2 in series (joined at the top), together in parallel with L3
    f.polyline([(160, 716), (160, 658), (375, 658), (375, 716)])
    for x in (160, 375):
        with f.rotated(90, x, 716):
            coil(f, x, x + 112, 716, turns=6, radius=17)
        f.line(x, 828, x, 888)
    f.line(52, 888, 215, 888), coil(f, 215, 320, 888, turns=6, radius=17), f.line(320, 888, 470, 888)
    f.text(36, 898, "A", size=24), f.text(486, 898, "B", size=24)
    name(122, 778, 1), name(412, 786, 2), name(260, 936, 3), f.text(260, 964, "(R)", size=24)
    # (S) L1 between A and B; L2 and L3 in series form the other path
    f.line(648, 688, 722, 688), coil(f, 722, 812, 688, turns=5, radius=16), f.line(812, 688, 928, 688)
    f.line(928, 688, 928, 722)
    with f.rotated(90, 928, 722):
        coil(f, 928, 1024, 722, turns=5, radius=16)
    f.line(928, 818, 928, 850), f.line(928, 850, 818, 850), coil(f, 728, 818, 850, turns=5, radius=16)
    f.line(728, 850, 648, 850), f.line(648, 850, 648, 688)
    f.line(648, 815, 606, 858), f.line(895, 688, 940, 642)
    f.text(588, 880, "A", size=24), f.text(950, 636, "B", size=24)
    name(762, 660, 1), name(766, 892, 2), name(968, 778, 3), f.text(790, 950, "(S)", size=24)
    return f


def loop_falling_in_field():
    """A rectangular loop of width l, partly in a field B into the page, moving down with velocity v."""
    f = Figure(400, 470)
    crosses(f, (32, 112, 192, 272), (48, 106, 158, 208, 258, 312, 382))
    f.rect(58, 72, 186, 276, width=4)
    vec_label(f, 332, 62, "B"), f.vector(300, 200, 300, 272), vec_label(f, 332, 246, "v")
    f.dim(58, 412, 244, 412), f.text(151, 452, "<i>l</i>", size=30)
    return f


def flux_current_lines():
    """Magnetic flux against current for four inductors: lines A, B, C and D from the origin, A steepest."""
    f = Figure(480, 460)
    ox, oy = 58, 405
    f.vector(ox, oy, ox, 22), f.vector(ox, oy, 440, oy)
    for (x, y), name in (((182, 92), "A"), ((252, 135), "B"), ((302, 185), "C"), ((350, 242), "D")):
        f.line(ox, oy, x, y)
        f.text(x + 14, y - 8, name, size=30)
    f.text(22, 100, "<i>ϕ</i>", size=34), f.text(36, 440, "0", size=30), f.text(430, 448, "<i>I</i>", size=32)
    return f


def rotating_rod_in_field():
    """Rod AC of length 4L in a field B into the page, turning about O with AO = L and OC = 3L."""
    f = Figure(660, 290)
    crosses(f, range(78, 560, 66), (76, 118, 176, 214), size=6)
    f.line(58, 147, 580, 147, width=4), f.dot(190, 147, r=6)
    f.text(36, 158, "A", size=28), f.text(604, 158, "C", size=28), f.text(190, 136, "O", size=22)
    f.text(111, 104, "<i>ω</i>", size=26), vec_label(f, 598, 78, "B")
    f.dim(62, 240, 186, 240), f.dim(194, 240, 578, 240)
    f.text(124, 272, "<i>L</i>", size=26), f.text(386, 272, "3<i>L</i>", size=26)
    return f


def four_inductors_ab():
    """Inductors 1 H, 2 H, 3 H and 4 H wired so that each one joins A to B."""
    f = Figure(680, 380)
    y, top, bottom = 188, 56, 320
    f.line(56, y, 110, y), coil(f, 110, 178, y, turns=3, radius=17), f.line(178, y, 300, y)
    coil(f, 300, 368, y, turns=3, radius=17), f.line(368, y, 475, y), coil(f, 475, 543, y, turns=3, radius=17)
    f.line(543, y, 616, y)
    f.polyline([(56, y), (56, top), (430, top), (430, y)])
    f.line(245, top, 245, 86), vcoil(f, 245, 86, 150, turns=3, radius=17), f.line(245, 150, 245, bottom)
    f.polyline([(245, bottom), (616, bottom), (616, y)])
    f.dot(56, y, r=6), f.dot(616, y, r=6), f.dot(245, y), f.dot(430, y), f.dot(245, top)
    f.text(30, 198, "A", size=28), f.text(642, 198, "B", size=28)
    f.text(144, 146, "1 H", size=26), f.text(298, 126, "2 H", size=26), f.text(334, 238, "3 H", size=26)
    f.text(509, 238, "4 H", size=26)
    return f


def loop_with_resistor_in_field():
    """A loop in a field into the page: resistor on the left side, sliding rod of length L on the right moving with velocity V."""
    f = Figure(660, 400)
    crosses(f, (40, 148, 255, 360, 468), (50, 160, 250, 362), size=12)
    left, right, top, bottom = 76, 412, 112, 322
    f.rect(left - 14, 182, 28, 80, fill="#fff", width=0)
    f.line(left, top, right, top), f.line(left, bottom, right, bottom), f.line(right, top, right, bottom, width=5)
    f.line(left, top, left, 182), f.vresistor(left, 182, 262, peaks=4), f.line(left, 262, left, bottom)
    f.line(right, 217, 572, 217, width=4, arrow=True)
    f.rect(366, 196, 34, 40, fill="#fff", width=0), f.text(384, 228, "<i>L</i>", size=32)
    vec_label(f, 612, 228, "V")
    return f


def rod_leaving_field_region():
    """A loop with resistor R inside a region of magnetic field; its rod of length L is pulled out with velocity V."""
    f = Figure(660, 400)
    f.rect(30, 44, 425, 332)
    left, right, top, bottom = 132, 388, 106, 282
    f.line(left, top, right, top), f.line(left, bottom, right, bottom), f.line(right, top, right, bottom, width=5)
    f.line(left, top, left, 150), f.vresistor(left, 150, 240, peaks=4), f.line(left, 240, left, bottom)
    f.rect(right - 6, top - 6, 12, 12, fill=INK), f.rect(right - 6, bottom - 6, 12, 12, fill=INK)
    f.line(right, 194, 582, 194, arrow=True)
    f.text(92, 206, "<i>R</i>", size=32), f.text(358, 206, "<i>L</i>", size=32), f.text(606, 204, "<i>V</i>", size=30)
    f.text(52, 352, "mag. field", size=28, anchor="start")
    return f


def inductor_resistor_cell_ab():
    """From A: 6 ohm, then a 3 H inductor carrying 2 A away from A, then a 6 V cell to B."""
    f = Figure(680, 340)
    left, top, bottom = 36, 64, 282
    f.line(left, top, 120, top), coil(f, 120, 270, top, turns=6, radius=17), f.line(270, top, 430, top)
    f.resistor(430, 545, top), f.line(545, top, 622, top), f.arrowhead(330, top, 180, size=18)
    f.line(left, top, left, bottom), f.line(left, bottom, 215, bottom), f.cell(225, bottom, gap=20, long=32, short=17)
    f.line(235, bottom, 622, bottom), f.dot(622, top, r=7), f.dot(622, bottom, r=7)
    f.text(195, 120, "3 H", size=28), f.text(352, 40, "2 A", size=28), f.text(488, 122, "6 Ω", size=28)
    f.text(272, 326, "6 V", size=28), f.text(652, 74, "A", size=28), f.text(652, 292, "B", size=28)
    return f


FIGURES = {
    "PYQ-PHY-e562133303d1": stopping_potential_line,
    "PYQ-PHY-30a3fb56f725": r_l_between_a_b,
    "PYQ-PHY-40a287ad9f0f": two_bulbs_r_l,
    "PYQ-PHY-4de0d1f75f69": induced_emf_graph_options,
    "PYQ-PHY-583415e316c2": inductor_combinations,
    "PYQ-PHY-64d6a0fada4b": loop_falling_in_field,
    "PYQ-PHY-73eeb4888f85": flux_current_lines,
    "PYQ-PHY-85f8dc22d590": rotating_rod_in_field,
    "PYQ-PHY-89aa9e229841": four_inductors_ab,
    "PYQ-PHY-b4500bce0d11": loop_with_resistor_in_field,
    "PYQ-PHY-d4bc46508975": rod_leaving_field_region,
    "PYQ-PHY-e3c306ed5088": inductor_resistor_cell_ab,
}
