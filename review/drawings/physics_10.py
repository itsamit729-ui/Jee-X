"""Physics: thermodynamics (part 2), wave optics, work-energy-power."""

import math

from figlib import Figure, along, mid_arrow


def dotted(f, x1, y1, x2, y2):
    f.line(x1, y1, x2, y2, width=1.5, dash="3 6")


def cycle_abcd_with_isotherm():
    """P-V cycle: A (3V, 3p) to B (1V, 3p), B to C (1V, 1p), C to D (9V, 1p), and a curve from D back to A."""
    f = Figure(660, 460)
    ox, oy = 74, 404
    f.vector(ox, oy, ox, 40), f.vector(ox, oy, 500, oy)
    xv, yp = {1: 154, 3: 250, 9: 424}, {1: 314, 3: 140}
    a, b, c, d = (xv[3], yp[3]), (xv[1], yp[3]), (xv[1], yp[1]), (xv[9], yp[1])
    for x in xv.values():
        dotted(f, x, 50, x, oy)
    for y in yp.values():
        dotted(f, ox, y, 470, y)
    mid_arrow(f, *a, *b, at=0.6), mid_arrow(f, *b, *c, at=0.55), mid_arrow(f, *c, *d, at=0.5)
    curve = [(424 - 174 * t, 314 - 174 * t ** 1.9) for t in [i / 60 for i in range(61)]]
    f.polyline(curve)
    (x1, y1), (x2, y2) = curve[30], curve[33]
    f.arrowhead(x2, y2, math.degrees(math.atan2(y2 - y1, x2 - x1)), size=15)
    for pt in (a, b, c, d):
        f.dot(*pt, r=6)
    f.text(52, 38, "<i>p</i>", size=28), f.text(516, 414, "<i>V</i>", size=28), f.text(60, 432, "0", size=26)
    f.text(44, 150, "3<i>p</i>", size=26), f.text(44, 324, "1<i>p</i>", size=26)
    for v, x in xv.items():
        f.text(x, 436, f"{v}<i>V</i>", size=26)
    f.text(266, 124, "<i>A</i>", size=28), f.text(134, 124, "<i>B</i>", size=28)
    f.text(170, 346, "<i>C</i>", size=28), f.text(442, 346, "<i>D</i>", size=28)
    return f


def rectangle_cycle_p0_v0():
    """P-V rectangle A (V0, P0), B (3V0, P0), C (3V0, 2P0), D (V0, 2P0), with the arrows as given in the paper."""
    f = Figure(640, 480)
    ox, oy = 170, 374
    f.vector(ox, 438, ox, 96), f.vector(96, oy, 512, oy)
    xs, ys = (257, 343, 428), (292, 206)
    for x in xs:
        f.line(x, oy - 10, x, oy + 10, width=2.5)
    for y in ys:
        f.line(ox - 10, y, ox + 10, y, width=2.5)
    a, b, c, d = (257, 292), (428, 292), (428, 206), (257, 206)
    mid_arrow(f, *d, *c, at=0.6, size=18), mid_arrow(f, *b, *c, at=0.6, size=18)
    mid_arrow(f, *b, *a, at=0.6, size=18), mid_arrow(f, *d, *a, at=0.6, size=18)
    f.text(170, 78, "P", size=36), f.text(540, 386, "V", size=36), f.text(142, 414, "O", size=36)
    f.text(148, 220, "2P<sub>0</sub>", size=32, anchor="end"), f.text(148, 306, "P<sub>0</sub>", size=32, anchor="end")
    f.text(257, 426, "V<sub>0</sub>", size=32), f.text(428, 426, "3V<sub>0</sub>", size=32)
    f.text(240, 332, "A", size=34), f.text(452, 332, "B", size=34), f.text(442, 190, "C", size=34), f.text(252, 190, "D", size=34)
    return f


def straight_path_a_to_b():
    """P (kPa) against V (m3): a straight path from A (4, 5) to B (6, 2)."""
    f = Figure(660, 470)
    ox, oy = 98, 402
    f.vector(ox, oy, ox, 34), f.vector(ox, oy, 548, oy)
    a, b = (264, 154), (432, 292)
    dotted(f, ox, a[1], *a), dotted(f, a[0], a[1], a[0], oy), dotted(f, ox, b[1], *b), dotted(f, b[0], b[1], b[0], oy)
    mid_arrow(f, *a, *b, at=0.55), f.dot(*a, r=7), f.dot(*b, r=7)
    f.text(50, 44, "<i>P</i>", size=32), f.text(50, 82, "(kPa)", size=28), f.text(568, 444, "<i>V</i> (m<sup>3</sup>)", size=28)
    f.text(74, 164, "5", size=28), f.text(74, 302, "2", size=28), f.text(84, 438, "0", size=28)
    f.text(264, 438, "4", size=28), f.text(432, 438, "6", size=28)
    f.text(266, 132, "A", size=30), f.text(452, 272, "B", size=30)
    return f


def isotherm_and_tp_options():
    """Top: P-V curve from state 1 to state 2 with P = constant / V. Below: four T-P options (a)-(d)."""
    f = Figure(680, 570)
    ox, oy = 62, 232
    f.axes(ox, oy, 230, 200, xlabel="V", ylabel="P", origin="0", size=26)
    f.polyline([(ox + 46 + 150 * t, oy - 180 / (1 + 4.4 * t)) for t in [i / 50 for i in range(51)]])
    f.text(96, 44, "1", size=24), f.text(276, 204, "2", size=24)
    f.text(360, 104, "P =", size=28), f.fraction(456, 94, "constant", "V", size=26)
    options = (("a", 40), ("b", 205), ("c", 370), ("d", 535))
    for name, x in options:
        y = 500
        f.axes(x, y, 118, 112, xlabel="P", ylabel="T", size=22)
        if name == "a":
            pts, labels = [(x + 26, y - 26), (x + 84, y - 84)], ("1", "2")
        elif name == "b":
            pts, labels = [(x + 56, y - 26), (x + 56, y - 92)], ("1", "2")
        elif name == "c":
            pts, labels = [(x + 28, y - 58), (x + 96, y - 58)], ("2", "1")
        else:
            pts, labels = [(x + 28, y - 58), (x + 96, y - 58)], ("1", "2")
        f.line(*pts[0], *pts[1]), f.dot(*pts[0], r=4), f.dot(*pts[1], r=4)
        for (px, py), label in zip(pts, labels):
            f.text(px + (14 if name in "ab" else 0), py + (8 if name in "ab" else 26), label, size=20)
        f.text(x + 58, 556, f"({name})", size=24)
    return f


def pv_graph_options():
    """Four options (A)-(D) for pressure P against volume V."""
    f = Figure(1000, 320)
    for k, name in enumerate("ABCD"):
        ox, oy = 62 + k * 246, 206
        f.axes(ox, oy, 168, 162, xlabel="V", ylabel="P", size=26)
        if name == "A":
            f.line(ox + 18, oy - 18, ox + 132, oy - 132)
        elif name == "B":
            f.line(ox + 88, oy, ox + 88, oy - 140)
        elif name == "C":
            f.polyline([(ox + 14 + 132 * t, oy - 4 - 112 * (1 - math.exp(-3.6 * t))) for t in [i / 50 for i in range(51)]])
        else:
            f.line(ox + 26, oy - 84, ox + 150, oy - 84)
        f.text(ox + 82, 284, f"({name})", size=28)
    return f


def four_process_diagrams():
    """Four P-V diagrams (a)-(d), each from state A to state B: a curve, a horizontal line, a vertical line and a steeper curve."""
    f = Figure(1000, 270)
    for k, name in enumerate("abcd"):
        ox, oy = 52 + k * 248, 186
        f.axes(ox, oy, 178, 158, xlabel="V", ylabel="P", origin="0", size=22)
        if name == "a":
            pts = [(ox + 22 + 118 * t, oy - 132 + 108 * (1 - (1 - t) ** 2.2)) for t in [i / 40 for i in range(41)]]
        elif name == "b":
            pts = [(ox + 30, oy - 96), (ox + 142, oy - 96)]
        elif name == "c":
            pts = [(ox + 84, oy - 126), (ox + 84, oy - 40)]
        else:
            pts = [(ox + 24 + 118 * t, oy - 132 + 108 * (1 - (1 - t) ** 4.5)) for t in [i / 40 for i in range(41)]]
        f.polyline(pts), f.dot(*pts[0], r=4), f.dot(*pts[-1], r=4)
        f.text(pts[0][0] + (0 if name == "b" else 16), pts[0][1] - (12 if name == "b" else -4), "A", size=20)
        f.text(pts[-1][0] + (0 if name == "b" else 16), pts[-1][1] - (12 if name in "abd" else -6), "B", size=20)
        f.text(ox + 84, 252, f"({name})", size=24)
    return f


def three_rods_junction():
    """Three identical rods meeting at a junction; their free ends are at 0 C, 90 C and 90 C."""
    f = Figure(660, 430)
    j = (306, 204)
    for end in ((50, 204), (474, 52), (474, 356)):
        f.line(*j, *end, width=15)
        f.add(f'<line x1="{j[0]}" y1="{j[1]}" x2="{end[0]}" y2="{end[1]}" stroke="#fff" stroke-width="9"/>')
    f.text(62, 174, "0 °C", size=30), f.text(540, 58, "90 °C", size=30), f.text(540, 370, "90 °C", size=30)
    return f


def double_slit_path_difference():
    """Young's experiment: slits S1 and S2, screen with Q, O and P; S2B is perpendicular to S1P."""
    f = Figure(660, 460)
    for y1, y2 in ((126, 206), (232, 312)):
        f.line(36, y1, 36, y2, width=14)
    for y1, y2 in ((72, 128), (152, 288), (312, 402)):
        f.line(130, y1, 130, y2, width=14)
    s1, s2, p = (130, 140), (130, 300), (562, 378)
    f.line(562, 46, 562, 420), f.line(36, 219, 562, 219, width=2, dash="10 8")
    f.line(*s1, *p), f.line(*s2, *p)
    t = ((s2[0] - s1[0]) * (p[0] - s1[0]) + (s2[1] - s1[1]) * (p[1] - s1[1])) / ((p[0] - s1[0]) ** 2 + (p[1] - s1[1]) ** 2)
    b = (s1[0] + (p[0] - s1[0]) * t, s1[1] + (p[1] - s1[1]) * t)
    f.line(*s2, *b)
    ux, uy = (p[0] - s1[0]) / math.hypot(p[0] - s1[0], p[1] - s1[1]), (p[1] - s1[1]) / math.hypot(p[0] - s1[0], p[1] - s1[1])
    q1, q2 = (b[0] + ux * 13, b[1] + uy * 13), (b[0] - uy * 13, b[1] + ux * 13)
    f.polyline([q1, (q1[0] - uy * 13, q1[1] + ux * 13), q2], width=1.5)
    f.dot(*p, r=4)
    f.text(104, 138, "S<sub>1</sub>", size=26, anchor="end"), f.text(104, 306, "S<sub>2</sub>", size=26, anchor="end")
    f.text(b[0] - 6, b[1] - 12, "B", size=26), f.text(36, 344, "Slit", size=26)
    f.text(542, 78, "Q", size=26), f.text(582, 228, "O", size=26), f.text(548, 404, "P", size=26)
    return f


def slits_a1_a2_and_p():
    """Slits A1 and A2 a distance a apart; P is on the screen, a distance D away, directly opposite A1."""
    f = Figure(660, 460)
    f.line(72, 30, 72, 432), f.line(552, 30, 552, 432)
    a1, a2, p = (72, 130), (72, 278), (552, 130)
    f.line(*a1, *p, width=2.5, dash="10 8"), f.line(*a2, *p, width=2.5, dash="10 8")
    for pt in (a1, a2, p):
        f.dot(*pt, r=6)
    f.add('<path d="M56,140 Q44,140 44,154 V190 Q44,204 32,204 Q44,204 44,218 V254 Q44,268 56,268" stroke-width="2.5"/>')
    f.dim(76, 402, 548, 402), f.rect(290, 384, 44, 36, fill="#fff", width=0), f.text(312, 414, "D", size=30)
    f.text(40, 128, "A<sub>1</sub>", size=28), f.text(40, 296, "A<sub>2</sub>", size=28)
    f.text(14, 214, "a", size=28), f.text(580, 140, "P", size=30)
    return f


def wavefront_refraction():
    """A plane wavefront meeting an air-water surface at A and B: incident width x, refracted width y, and the distances z (in air) and w (in water)."""
    f = Figure(640, 480)
    s = 0.64
    a, b = (320 * s, 400 * s), (755 * s, 400 * s)
    d1 = (math.sqrt(0.5), math.sqrt(0.5))
    n = math.hypot(110, 268)
    d2 = (110 / n, 268 / n)
    span = b[0] - a[0]
    foot1 = (b[0] - d1[0] * span * d1[0], b[1] - d1[1] * span * d1[0])            # on the second incident ray
    foot2 = (a[0] + d2[0] * span * d2[0], a[1] + d2[1] * span * d2[0])            # on the first refracted ray
    for y in range(int(a[1]) + 22, 440, 21):
        f.line(105, y, 615, y, width=1.2, dash="16 14")
    f.line(120, a[1], 615, a[1])
    mid_arrow(f, a[0] - 260 * s, a[1] - 260 * s, *a, at=0.4), mid_arrow(f, b[0] - 365 * s, b[1] - 365 * s, *b, at=0.14)
    mid_arrow(f, *a, a[0] + d2[0] * 185, a[1] + d2[1] * 185, at=0.92), mid_arrow(f, *b, b[0] + d2[0] * 130, b[1] + d2[1] * 130, at=0.62)
    f.dim(*a, *foot1, width=2.5), f.dim(*b, *foot2, width=2.5)
    za, zb = along(foot1, b, 0.04, 14), along(foot1, b, 0.96, 14)
    wa, wb = along(a, foot2, 0.06, -14), along(a, foot2, 0.94, -14)
    f.dim(*za, *zb), f.dim(*wa, *wb)
    f.arc(*a, 30, -43, 0), f.arc(*b, 58, 180, 201)
    for foot, u, v in ((foot1, (-d1[0], -d1[1]), (-d1[1], d1[0])), (foot2, (-d2[0], -d2[1]), (d2[1], -d2[0]))):
        p1 = (foot[0] + u[0] * 12, foot[1] + u[1] * 12)
        f.polyline([p1, (p1[0] + v[0] * 12, p1[1] + v[1] * 12), (foot[0] + v[0] * 12, foot[1] + v[1] * 12)], width=1.5)

    def tag(x, y, label, w=26):
        f.rect(x - w / 2, y - 18, w, 26, fill="#fff", width=0), f.text(x, y + 2, label, size=24)

    tag(*along(a, foot1, 0.45, 22), "<i>x</i>"), tag(*along(foot1, b, 0.5, 36), "<i>z</i>")
    tag(*along(a, foot2, 0.5, -40), "<i>w</i>"), tag(*along(b, foot2, 0.45, 24), "<i>y</i>")
    f.text(a[0] - 26, a[1] - 6, "A", size=22), tag(b[0] + 26, b[1] + 26, "B")
    f.text(a[0] + 44, a[1] - 8, "<i>i</i>", size=22), tag(b[0] - 78, b[1] + 24, "<i>r</i>", w=20)
    f.text(520, 172, "air", size=24), tag(566, 322, "water", w=74)
    return f


def pendulum_p_to_q():
    """A pendulum held horizontal at P and released; Q is its lowest point, a height h = 2 m below."""
    f = Figure(580, 470)
    pivot, r = (120, 70), 324
    f.line(*pivot, pivot[0] + r, pivot[1]), f.line(*pivot, pivot[0], pivot[1] + r, width=2.5, dash="10 9")
    f.add(f'<path d="M{pivot[0] + r},{pivot[1]} A{r},{r} 0 0 1 {pivot[0]},{pivot[1] + r}" stroke-width="2.5" stroke-dasharray="10 9"/>')
    f.dot(pivot[0] + r, pivot[1], r=13), f.dot(pivot[0], pivot[1] + r, r=13)
    f.text(pivot[0] + r + 40, pivot[1] + 8, "P", size=32), f.text(pivot[0] - 40, pivot[1] + r + 12, "Q", size=32)
    f.text(60, 240, "h = 2 m", size=28)
    return f


FIGURES = {
    "PYQ-PHY-83df44bc8bf8": cycle_abcd_with_isotherm,
    "PYQ-PHY-83f4162f1545": rectangle_cycle_p0_v0,
    "PYQ-PHY-87fe8f2b3580": straight_path_a_to_b,
    "PYQ-PHY-8e761920e372": isotherm_and_tp_options,
    "PYQ-PHY-c0ada5b032f7": pv_graph_options,
    "PYQ-PHY-cdfbeb260b44": four_process_diagrams,
    "PYQ-PHY-d44961c87c41": three_rods_junction,
    "PYQ-PHY-5496cf810f48": double_slit_path_difference,
    "PYQ-PHY-ce6ded181b3e": slits_a1_a2_and_p,
    "PYQ-PHY-fa2d60f024f6": wavefront_refraction,
    "PYQ-PHY-09c41e7c9d64": pendulum_p_to_q,
}
