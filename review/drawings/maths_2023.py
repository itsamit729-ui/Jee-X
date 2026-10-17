"""Mathematics (MHT-CET 2020-23): linear programming graphs (plotted from the questions' own equations), a switching
circuit, a probability table and a vector diagram."""

import math

from figlib import Figure
from drawings.maths_2425 import POSITIVE, Plot, S, block, ge, row


def lp_square_wedge():
    """Lines y = x, x = 5 and y = 3; shaded: x - y >= 0, x <= 5, y <= 3, x, y >= 0; corners C(3, 3), B(5, 3), A(5, 0)."""
    f = Figure(630, 460)
    g = Plot(f, 30, 20, 540, 400, (-1.5, 7.5), (-1.5, 6))
    g.axes(primes=True, size=28, origin="0")
    g.line(1, -1, 0), g.line(1, 0, 5), g.line(0, 1, 3)
    g.region([ge(1, -1, 0), (1, 0, 5), (0, 1, 3)] + POSITIVE)
    for name, (x, y), (dx, dy), anchor in (("C(3, 3)", (3, 3), (-10, -14), "end"), ("B(5, 3)", (5, 3), (12, -14), "start"),
                                          ("A(5, 0)", (5, 0), (12, 34), "start")):
        px, py = g.p(x, y)
        f.text(px + dx, py + dy, name, size=26, anchor=anchor, halo=True)
    return f


def lp_four_lines_quad():
    """Lines -7x + 14y = 14, 3x + 4y = 18, x - 6y = 3 and 2x + 3y = 3; shaded: 3x + 4y <= 18, x - 6y <= 3, 2x + 3y >= 3, -7x + 14y <= 14, x, y >= 0."""
    f = Figure(670, 480)
    g = Plot(f, 30, 20, 580, 420, (-2.5, 8), (-1.8, 6.2))
    g.axes(primes=True, size=26, origin="")
    g.line(-7, 14, 14, label="−7<i>x</i> + 14<i>y</i> = 14", at=(3.6, 5.8), size=24)
    g.line(3, 4, 18, label="3<i>x</i> + 4<i>y</i> = 18", at=(5.4, 3.6), size=24)
    g.line(1, -6, 3, label="<i>x</i> − 6<i>y</i> = 3", at=(6.6, 0.75), size=24)
    g.line(2, 3, 3, label="2<i>x</i> + 3<i>y</i> = 3", at=(-0.8, -1.4), size=24)
    g.region([(3, 4, 18), (1, -6, 3), ge(2, 3, 3), (-7, 14, 14)] + POSITIVE)
    return f


def probability_table():
    """X: 0, 1, 2 with P(X): 9/16, 3/8, 1/16."""
    f = Figure(640, 260)
    x0, y0, cw, rh = 20, 20, 150, 110
    f.rect(x0, y0, cw * 4, rh * 2, width=3)
    for i in range(1, 4):
        f.line(x0 + cw * i, y0, x0 + cw * i, y0 + rh * 2, width=3)
    f.line(x0, y0 + rh, x0 + cw * 4, y0 + rh, width=3)
    f.text(x0 + cw / 2, y0 + 70, "X", size=44), f.text(x0 + cw / 2, y0 + rh + 70, "P(X)", size=44)
    for i, v in enumerate(("0", "1", "2")):
        f.text(x0 + cw * (i + 1.5), y0 + 70, v, size=44)
    for i, (a, b) in enumerate((("9", "16"), ("3", "8"), ("1", "16"))):
        f.fraction(x0 + cw * (i + 1.5), y0 + rh + 50, a, b, size=40)
    return f


def lp_min_19_5():
    """Lines x = 4, y = x + 3, y = 3 and 2x + 3y = 12; shaded: y >= 3, y <= x + 3, x <= 4, 2x + 3y >= 12."""
    f = Figure(590, 520)
    g = Plot(f, 20, 20, 520, 460, (-1.5, 8), (-2, 7.5))
    g.axes(xticks=(2, 4, 6), yticks=(2, 4, 6), size=24, origin="0")
    g.line(1, 0, 4, label="<i>x</i> = 4", at=(4.9, 7.0), size=24)
    g.line(-1, 1, 3, label="<i>y</i> = <i>x</i> + 3", at=(1.9, 6.7), size=24)
    g.line(0, 1, 3, label="<i>y</i> = 3", at=(6.6, 3.3), size=24)
    g.line(2, 3, 12, label="2<i>x</i> + 3<i>y</i> = 12", at=(6.6, -1.4), size=24)
    g.region([ge(0, 1, 3), (-1, 1, 3), (1, 0, 4), ge(2, 3, 12)])
    return f


def lp_three_lines_x8():
    """Lines x - y = 1, 2x + y = 2 and x + 2y = 8; shaded: 2x + y >= 2, x - y <= 1, x + 2y <= 8, x, y >= 0."""
    f = Figure(650, 460)
    g = Plot(f, 30, 20, 560, 400, (-1.5, 10), (-1.5, 5))
    g.axes(primes=True, size=28, origin="O")
    g.line(1, -1, 1, label="<i>x</i> − <i>y</i> = 1", at=(6.2, 4.4), size=26)
    g.line(2, 1, 2, label="2<i>x</i> + <i>y</i> = 2", at=(3.2, -0.9), size=26)
    g.line(1, 2, 8, label="<i>x</i> + 2<i>y</i> = 8", at=(8.2, -0.9), size=26)
    g.region([ge(2, 1, 2), (1, -1, 1), (1, 2, 8)] + POSITIVE)
    return f


def lp_ocdb():
    """Lines x + 2y = 50, x = 10 and y = x; shaded OCDBO: x <= 10, y >= x, x + 2y <= 50, x >= 0; B(0, 25), C(10, 10), D(10, 20), A(50, 0)."""
    f = Figure(650, 460)
    g = Plot(f, 30, 20, 560, 400, (-4, 56), (-4, 32))
    g.axes(xticks=range(5, 55, 5), yticks=range(5, 35, 5), size=20, origin="O")
    g.line(1, 2, 50), g.line(1, 0, 10), g.line(1, -1, 0)
    g.region([(1, 0, 10), ge(-1, 1, 0), (1, 2, 50)] + POSITIVE)
    for name, (x, y), dx in (("B", (0, 25), 14), ("C", (10, 10), 14), ("D", (10, 20), 14), ("A", (50, 0), 0)):
        px, py = g.p(x, y)
        f.text(px + dx, py - 10, name, size=24, anchor="start", halo=True)
    return f


def lp_y_ge_1():
    """Lines 3x + 4y = 12, 4x + 7y = 28 and y = 1; shaded: 3x + 4y >= 12, 4x + 7y <= 28, y >= 1, x, y >= 0."""
    f = Figure(630, 460)
    g = Plot(f, 20, 20, 560, 400, (-0.8, 8.5), (-1.5, 5.6))
    g.axes(xticks=range(1, 8), yticks=range(1, 6), size=24, origin="0")
    g.line(3, 4, 12), g.line(4, 7, 28), g.line(0, 1, 1)
    g.region([ge(3, 4, 12), (4, 7, 28), ge(0, 1, 1)] + POSITIVE)
    return f


def lp_max_95():
    """Lines x + y = 5, x = 3 and y = 3; shaded: x <= 3, y <= 3, x + y <= 5, x, y >= 0."""
    f = Figure(590, 440)
    g = Plot(f, 20, 20, 520, 380, (-0.5, 7), (-0.8, 5.8))
    g.axes(xticks=range(1, 7), yticks=range(1, 6), size=26, origin="0")
    g.line(1, 1, 5), g.line(1, 0, 3), g.line(0, 1, 3)
    g.region([(1, 0, 3), (0, 1, 3), (1, 1, 5)] + POSITIVE, spacing=8)
    return f


def lp_regions_s1_s4_x3():
    """Lines 4x + 3y = 60, y = 2x and x = 3 split the first quadrant into S1-S4; S2 is the region x >= 3, y >= 2x, 4x + 3y <= 60.
    Points: B(0, 20), F(3, 16), E(6, 12), D(3, 6), C(3, 0), A(15, 0)."""
    f = Figure(550, 520)
    g = Plot(f, 20, 20, 480, 460, (-3, 19), (-4, 24))
    g.axes(size=26, origin="O")
    g.line(4, 3, 60, label="4<i>x</i> + 3<i>y</i> = 60", at=(13.5, -3.2), size=22)
    g.line(-2, 1, 0, label="<i>y</i> ≥ 2<i>x</i>", at=(-1.6, -3.2), size=22)
    g.line(1, 0, 3, label="<i>x</i> = 3", at=(4.6, -3.2), size=22)
    for name, (x, y), dx, dy in (("B", (0, 20), -12, 6), ("F", (3, 16), 10, -6), ("E", (6, 12), 14, 8), ("D", (3, 6), 10, 6),
                                 ("C", (3, 0), 12, 26), ("A", (15, 0), -6, 30)):
        px, py = g.p(x, y)
        f.dot(px, py, r=4), f.text(px + dx, py + dy, name, size=22, anchor="start" if dx > 0 else "end", halo=True)
    for name, (x, y) in (("1", (8, 6)), ("2", (4.4, 13)), ("3", (1.5, 13)), ("4", (1.6, 2))):
        f.text(*g.p(x, y), f"S<sub>{name}</sub>", size=24, halo=True)
    return f


def lp_four_lines_band():
    """Lines 2x + 3y = 6, 3x + 6y = 18, x - 3y = 3 and -x + 2y = 2; shaded: 2x + 3y >= 6, 3x + 6y <= 18, x - 3y <= 3, -x + 2y <= 2, x, y >= 0."""
    f = Figure(650, 460)
    g = Plot(f, 30, 20, 560, 400, (-3, 8), (-2.2, 5.6))
    g.axes(xticks=range(1, 7), yticks=range(1, 6), size=24, origin="O")
    g.line(2, 3, 6), g.line(3, 6, 18), g.line(1, -3, 3), g.line(-1, 2, 2)
    g.region([ge(2, 3, 6), (3, 6, 18), (1, -3, 3), (-1, 2, 2)] + POSITIVE)
    return f


def lp_small_triangle():
    """Lines 3x + 4y = 12, y = x and y = 3; shaded: 3x + 4y >= 12, y - x >= 0, y <= 3, x, y >= 0."""
    f = Figure(590, 460)
    g = Plot(f, 20, 20, 520, 400, (-1, 8), (-1.2, 7))
    g.axes(xticks=range(1, 8), yticks=range(1, 7), size=24, origin="0")
    g.line(3, 4, 12), g.line(-1, 1, 0), g.line(0, 1, 3)
    g.region([ge(3, 4, 12), ge(-1, 1, 0), (0, 1, 3)] + POSITIVE, spacing=8)
    return f


def lp_four_options_x2y():
    """Lines x - 2y = 2, 5x + 2y = 10 and 4x + 5y = 20 in four panels; Fig. 3 shades x - 2y <= 2, 5x + 2y >= 10, 4x + 5y <= 20, x, y >= 0."""
    f = Figure(760, 600)
    regions = {
        1: [ge(5, 2, 10), (4, 5, 20)] + POSITIVE,
        2: [(5, 2, 10), (4, 5, 20)] + POSITIVE,
        3: [(1, -2, 2), ge(5, 2, 10), (4, 5, 20)] + POSITIVE,
        4: [ge(1, -2, 2), (4, 5, 20)] + POSITIVE,
    }
    for n, (left, top) in zip(range(1, 5), ((20, 10), (400, 10), (20, 310), (400, 310))):
        g = Plot(f, left, top, 340, 240, (-1, 6.5), (-1.6, 6))
        g.axes(xticks=range(1, 6), yticks=range(1, 6), size=18, origin="0")
        for a, b, c in ((1, -2, 2), (5, 2, 10), (4, 5, 20)):
            g.line(a, b, c, width=2)
        g.region(regions[n], spacing=8)
        f.text(left + 170, top + 280, f"Fig. {n}", size=22)
    return f


def circuit_three_branches():
    """Three branches in parallel: S1 on the top, S2 in the middle, S1' and S2' in series on the bottom; a cell and lamp L in the outer loop."""
    f = Figure(700, 420)
    l, r = 130, 560
    for y, labels in ((50, [S(1)]), (150, [S(2)]), (250, [S(1, "′"), S(2, "′")])):
        row(f, l, r, y, labels, size=28, dot=True, w=70)
    f.line(l, 50, l, 250, width=2.5), f.line(r, 50, r, 250, width=2.5)
    f.line(40, 150, l, 150, width=2.5), f.line(r, 150, 660, 150, width=2.5)
    f.line(40, 150, 40, 370, width=2.5), f.line(660, 150, 660, 370, width=2.5)
    f.line(40, 370, 190, 370, width=2.5), f.cell(201, 370, gap=16, long=26, short=14), f.line(209, 370, 500, 370, width=2.5)
    f.meter(530, 370, "L", r=28), f.line(558, 370, 660, 370, width=2.5)
    f.arrowhead(40, 260, -90, size=16), f.arrowhead(660, 260, 90, size=16), f.arrowhead(100, 150, 0, size=16), f.arrowhead(620, 150, 0, size=16)
    return f


def vectors_150():
    """Vector u (|u| = 8) drawn up to the right and vector v (|v| = 12) drawn to the right from its tip; the angle between them is 150 degrees."""
    f = Figure(640, 340)
    tip = (300, 110)
    f.line(160, 330, *tip, width=4, arrow=True), f.line(*tip, 620, tip[1], width=4, arrow=True)
    f.arc(tip[0], tip[1], 60, 0, 180 - 60, width=2.5)
    f.text(420, 70, "|<i>v</i>| = 12", size=44), f.text(30, 250, "|<i>u</i>| = 8", size=44, anchor="start")
    f.text(380, 230, "150°", size=44)
    return f


FIGURES = {
    "PYQ-MATH-b528475f43f0": lp_square_wedge,
    "PYQ-MATH-d477ac12e1ae": lp_four_lines_quad,
    "PYQ-MATH-9d60868c462f": probability_table,
    "PYQ-MATH-27ac06107011": lp_min_19_5,
    "PYQ-MATH-2525b2242dbd": lp_three_lines_x8,
    "PYQ-MATH-49a851142586": lp_ocdb,
    "PYQ-MATH-87a3b1da68ac": lp_y_ge_1,
    "PYQ-MATH-d0ee1fde7c9f": lp_max_95,
    "PYQ-MATH-ab4a6f7e1d2b": lp_regions_s1_s4_x3,
    "PYQ-MATH-c0680d1436fc": lp_four_lines_band,
    "PYQ-MATH-88cc7b68ad4c": lp_small_triangle,
    "PYQ-MATH-5e4c8d880590": lp_four_options_x2y,
    "PYQ-MATH-0008872b92c9": circuit_three_branches,
    "PYQ-MATH-729eb8f6ec8b": vectors_150,
}
