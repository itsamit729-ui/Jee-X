"""The first eleven figures, drawn as the review sample."""

import math

from figlib import INK, Figure, coil


def ac_series_circuit():
    """Source and 6 ohm on the top wire; coil (5 mH, 4 ohm) and 50 uF on the bottom wire."""
    f = Figure(620, 330)
    left, right, top, bottom = 30, 590, 55, 285
    f.line(left, top, 152, top), f.line(208, top, 390, top), f.line(490, top, right, top)
    f.circle(180, top, 28)
    f.add('<path d="M163,55 q8.5,-20 17,0 t17,0" stroke-width="3"/>')
    f.resistor(390, 490, top)
    f.text(440, top + 50, "6 Ω")
    f.line(right, top, right, bottom), f.line(left, top, left, bottom)
    f.line(left, bottom, 110, bottom), f.line(240, bottom, 443, bottom), f.line(457, bottom, right, bottom)
    coil(f, 110, 240, bottom, turns=4, radius=18)
    f.text(175, bottom - 38, "5 mH, 4 Ω")
    f.capacitor(450, bottom)
    f.text(450, bottom - 45, "50 μF")
    return f


def capacitor_with_slab():
    """Plates a distance d apart with a dielectric slab of thickness d/2 between them."""
    f = Figure(620, 440)
    left, right, top, bottom, mid = 140, 470, 40, 360, 200
    f.line(left, top, left, bottom, width=4), f.line(right, top, right, bottom, width=4)
    f.line(30, mid, left, mid), f.line(right, mid, 590, mid)
    slab = [(180, 70), (345, 70), (345, 330), (180, 330)]
    f.hatch(slab, spacing=18)
    f.path(slab, close=True)
    f.text(263, 213, "<i>K</i>", size=38, halo=True)
    f.line(184, 52, 341, 52, width=2, arrow=True), f.line(341, 52, 184, 52, width=2, arrow=True)
    f.text(263, 38, "<i>d</i>/2")
    f.line(left + 5, 395, right - 5, 395, width=2, arrow=True), f.line(right - 5, 395, left + 5, 395, width=2, arrow=True)
    f.text(305, 430, "<i>d</i>")
    return f


def two_diode_circuit():
    """3 V cell with 70 ohm in the bottom branch; D1 (reverse) and D2 (forward), each with 30 ohm."""
    f = Figure(620, 450)
    left, right, y1, y2, y3 = 30, 590, 75, 215, 365
    f.line(left, y1, left, y3), f.line(right, y1, right, y3)
    for y, pointing, name in ((y1, "left", "1"), (y2, "right", "2")):
        f.line(left, y, 130, y), f.line(170, y, 420, y), f.line(510, y, right, y)
        f.diode(150, y, pointing)
        f.resistor(420, 510, y)
        f.text(150, y - 34, f"<i>D</i><sub>{name}</sub>", size=34)
        f.text(465, y - 26, "30 Ω")
    f.line(left, y3, 129, y3), f.line(151, y3, 420, y3), f.line(510, y3, right, y3)
    f.cell(140, y3)
    f.resistor(420, 510, y3)
    f.text(140, y3 + 72, "3 V"), f.text(465, y3 - 26, "70 Ω")
    return f


def three_rods():
    """Rods 2K, K, 2K in series between 3T (left) and T (right); junctions at T1 and T2."""
    f = Figure(620, 210)
    left, right, top, bottom = 95, 525, 55, 135
    f.wall(left, 25, 185, "left"), f.wall(right, 25, 185, "right")
    f.line(left, top, right, top), f.line(left, bottom, right, bottom)
    for x, name in ((238, "1"), (382, "2")):
        f.line(x, top, x, bottom + 14)
        f.text(x, bottom + 50, f"<i>T</i><sub>{name}</sub>", size=32)
    for x, label in ((166, "2<i>K</i>"), (310, "<i>K</i>"), (454, "2<i>K</i>")):
        f.text(x, 106, label, size=32)
    f.text(42, 106, "3<i>T</i>", size=32), f.text(578, 106, "<i>T</i>", size=32)
    return f


def glass_water_air():
    """A ray from glass into water, then grazing along the water-air surface."""
    f = Figure(620, 450)
    top, low = 90, 275
    f.hatch([(30, low), (590, low), (590, 440), (30, 440)], spacing=22, width=1)
    f.line(30, top, 590, top, width=4), f.line(30, low, 590, low, width=4)
    start, p1, p2 = (485, 400), (420, low), (262, top)
    in_glass = math.degrees(math.atan2(start[1] - p1[1], start[0] - p1[0]))    # direction p1 -> start
    in_water = math.degrees(math.atan2(p1[1] - p2[1], p1[0] - p2[0]))          # direction p2 -> p1
    f.line(*start, *p1), f.line(*p1, *p2), f.line(*p2, 30, top, width=4)
    f.arrowhead(450, 332.7, in_glass + 180, size=16)
    f.arrowhead(150, top, 180, size=16)
    f.line(420, 185, 420, 375, width=1.5), f.line(262, 15, 262, 175, width=1.5)
    f.path([(262, 68), (240, 68), (240, top)], width=1.5)
    f.arc(*p1, 62, in_glass, 90), f.arc(*p1, 46, in_water + 180, 270), f.arc(*p2, 42, in_water, 90)
    f.text(441, 372, "<i>i</i><sub>1</sub>", size=26, halo=True), f.text(397, 218, "<i>r</i>", size=26)
    f.text(284, 158, "<i>i</i><sub>2</sub>", size=26), f.text(226, 58, "90°", size=22)
    f.text(45, 56, "Air", size=26, anchor="start"), f.text(45, 150, "Water", size=26, anchor="start")
    f.text(45, 336, "Glass", size=26, anchor="start", halo=True)
    f.text(505, 172, "<i>μ</i><sub>w</sub> =", size=26)
    f.text(558, 158, "4", size=24), f.line(546, 165, 570, 165, width=1.5), f.text(558, 190, "3", size=24)
    return f


def feasible_region():
    """Region bounded by 2x + y = 2, x - y = 1, x + 2y = 8 and the y-axis: vertices E, A, B, D."""
    f = Figure(640, 470)
    ox, oy, u = 175, 375, 50

    def p(x, y):
        return ox + u * x, oy - u * y

    region = [p(0, 2), p(1, 0), p(10 / 3, 7 / 3), p(0, 4)]
    f.hatch(region, spacing=13)
    f.line(55, oy, 600, oy, arrow=True), f.line(600, oy, 55, oy, arrow=True)
    f.line(ox, 455, ox, 35, arrow=True), f.line(ox, 35, ox, 455, arrow=True)
    for a, b in ((p(-0.75, 4.375), p(9.2, -0.6)),      # x + 2y = 8
                 (p(-0.45, 2.9), p(1.6, -1.2)),        # 2x + y = 2
                 (p(-0.1, -1.1), p(4.6, 3.6))):        # x - y = 1
        f.line(*a, *b, arrow=True), f.line(*b, *a, arrow=True)
    f.text(606, oy - 16, "X", size=28), f.text(ox - 28, 52, "Y", size=28)
    f.text(ox + 16, p(0, 4)[1] - 14, "D (0, 4)", size=24, anchor="start")
    f.text(ox - 12, p(0, 2)[1] + 8, "E (0, 2)", size=24, anchor="end")
    f.text(ox - 12, oy - 12, "O (0, 0)", size=24, anchor="end")
    f.text(p(1, 0)[0] + 16, oy + 32, "A (1, 0)", size=24, anchor="start")
    f.text(p(8, 0)[0] - 16, oy + 32, "C", size=24)
    bx, by = p(10 / 3, 7 / 3)
    f.text(bx + 30, by + 8, "B (", size=24, anchor="start")
    f.text(bx + 74, by - 2, "10", size=19), f.line(bx + 62, by + 3, bx + 86, by + 3, width=1.5), f.text(bx + 74, by + 22, "3", size=19)
    f.text(bx + 92, by + 8, ",", size=24)
    f.text(bx + 110, by - 2, "7", size=19), f.line(bx + 101, by + 3, bx + 119, by + 3, width=1.5), f.text(bx + 110, by + 22, "3", size=19)
    f.text(bx + 124, by + 8, ")", size=24, anchor="start")
    return f


def switching_circuit():
    """Three parallel branches (S1 S2', S1' S2, S1' S2') in series with a lamp L and a cell."""
    f = Figure(620, 490)
    left, right, bottom = 35, 585, 420
    rows = ((75, "<i>S</i><sub>1</sub>", "<i>S</i>′<sub>2</sub>"), (185, "<i>S</i>′<sub>1</sub>", "<i>S</i><sub>2</sub>"),
            (295, "<i>S</i>′<sub>1</sub>", "<i>S</i>′<sub>2</sub>"))
    for y, first, second in rows:
        f.line(left, y, 182, y), f.line(244, y, 426, y), f.line(488, y, right, y)
        f.switch(187, y), f.switch(431, y)
        f.text(228, y - 30, first, size=28), f.text(462, y - 30, second, size=28)
    f.line(left, 75, left, bottom), f.line(right, 75, right, bottom)
    f.line(left, bottom, 149, bottom), f.line(171, bottom, 358, bottom), f.line(422, bottom, right, bottom)
    f.cell(160, bottom, gap=18, long=34, short=18)
    f.circle(390, bottom, 30), f.text(390, bottom + 12, "<i>L</i>", size=34)
    f.arrowhead(108, 75, 0), f.arrowhead(right, 138, 90), f.arrowhead(272, bottom, 180), f.arrowhead(left, 238, 270)
    return f


def ring_and_tangent():
    """A circular loop of radius R, centre O, with the axis XX' tangent to it at the top."""
    f = Figure(620, 480)
    cx, cy, r = 300, 252, 216
    f.line(50, 36, 550, 36), f.circle(cx, cy, r)
    f.line(cx, 36, cx, cy), f.line(cx - r, cy, cx + r, cy, dash="14 12")
    f.circle(cx, cy, 10, fill=INK)
    f.text(24, 46, "<i>X</i>", size=34), f.text(582, 46, "<i>X</i>′", size=34)
    f.text(326, 160, "<i>R</i>", size=34), f.text(300, 306, "<i>O</i>", size=34)
    return f


def concentric_half_rings():
    """Two concentric half rings of radii R1 and R2 about O, each with linear charge density lambda."""
    f = Figure(620, 350)
    cx, cy = 308, 305
    for r in (170, 264):
        f.add(f'<path d="M{cx - r},{cy} A{r},{r} 0 0 1 {cx + r},{cy}" stroke-width="3"/>')
        for k in range(9):
            a = math.radians(8 + k * 20.5)
            rr = r + (24 if k % 2 == 0 else -24)
            x, y = cx - rr * math.cos(a), cy - rr * math.sin(a)
            f.line(x - 8, y, x + 8, y, width=2), f.line(x, y - 8, x, y + 8, width=2)
    for r, deg, name in ((170, 30, "1"), (264, 62, "2")):
        a = math.radians(deg)
        x, y = cx + r * math.cos(a), cy - r * math.sin(a)
        f.line(cx, cy, x - 3 * math.cos(a), y + 3 * math.sin(a), arrow=True)
        f.text(x - 34, y + 46, f"<i>R</i><sub>{name}</sub>", size=26, halo=True)
    f.text(cx - 12, cy + 32, "<i>O</i>", size=28)
    f.text(196, 62, "<i>λ</i>", size=28), f.text(222, 158, "<i>λ</i>", size=28, halo=True)
    return f


def mass_between_springs():
    """A mass m between two identical springs S1 and S2 fixed to walls A-side and B-side."""
    f = Figure(620, 210)
    y = 105
    for x in (35, 585):
        f.line(x, 62, x, 148, width=4), f.line(x - 12, 148, x + 12, 148, width=4)
    f.line(35, y, 70, y), f.line(250, y, 286, y), f.line(350, y, 386, y), f.line(546, y, 585, y)
    coil(f, 70, 250, y, turns=8, radius=20), coil(f, 386, 546, y, turns=8, radius=20)
    f.rect(286, 70, 64, 70)
    f.text(318, 116, "<i>m</i>", size=30)
    f.text(160, 68, "A", size=28), f.text(466, 68, "B", size=28)
    f.text(160, 165, "<i>S</i><sub>1</sub>", size=28), f.text(466, 165, "<i>S</i><sub>2</sub>", size=28)
    return f


def dimethylnonenol():
    """Skeletal formula of 3,7-dimethylnon-5-en-4-ol (the compound to be named)."""
    f = Figure(620, 350)
    chain = [(193, 28), (93, 80), (93, 180), (193, 230), (293, 180), (393, 230), (493, 180), (493, 80), (393, 28)]
    f.path(chain)
    f.line(205, 212, 281, 174)                    # second line of the C=C bond
    f.line(93, 180, 28, 232), f.line(493, 180, 560, 232)   # methyl branches
    f.line(393, 230, 393, 282)
    f.text(415, 322, "OH", size=40)
    return f


FIGURES = {
    "PYQ-PHY-ed3626d6e366": ac_series_circuit,
    "PYQ-PHY-2f2d65379236": capacitor_with_slab,
    "PYQ-PHY-8f46ff259d46": two_diode_circuit,
    "PYQ-PHY-58fe2a41a3f5": three_rods,
    "PYQ-PHY-45fb2db35584": glass_water_air,
    "PYQ-MATH-eabc842d22ef": feasible_region,
    "PYQ-MATH-bc68e094c80e": switching_circuit,
    "PYQ-PHY-2850756305fd": ring_and_tangent,
    "PYQ-PHY-645f546a7572": concentric_half_rings,
    "PYQ-PHY-7dd5cbd71e56": mass_between_springs,
    "PYQ-CHEM-7e5ec56d198c": dimethylnonenol,
}
