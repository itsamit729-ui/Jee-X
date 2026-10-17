"""Physics (MHT-CET 2024-25): moving charges and magnetism."""

import math

from figlib import Figure, mid_arrow


def ellipse(f, cx, cy, rx, ry, width=3, dash=None):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    f.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" stroke-width="{width}"{extra}/>')


def arc_arrow(f, cx, cy, r, deg, forward=True, size=16):
    """An arrowhead on a circle about (cx, cy) at angle deg (0 = right, 90 = down), pointing along increasing angle when forward."""
    x, y = cx + r * math.cos(math.radians(deg)), cy + r * math.sin(math.radians(deg))
    f.arrowhead(x, y, deg + (90 if forward else -90), size=size)


def wire_quarter_arc_wire():
    """Current I comes down AB, round a quarter circle BC of radius r centred at O, and out along CD."""
    f = Figure(560, 440)
    o, r = (240, 200), 170
    b, c = (o[0] - r, o[1]), (o[0], o[1] + r)
    f.line(70, 40, *b), f.arrowhead(70, 120, 90, size=16)
    f.arc(o[0], o[1], r, 180, 90, width=3), arc_arrow(f, *o, r, 135, forward=False)
    f.line(*c, 520, c[1]), f.arrowhead(400, c[1], 0, size=16)
    f.line(*b, *o, width=2, dash="8 6"), f.line(*o, *c, width=2, dash="8 6")
    f.text(70, 32, "A", size=30), f.text(44, b[1] + 10, "B", size=30), f.text(o[0] + 24, o[1] + 10, "O", size=30)
    f.text(o[0], c[1] + 40, "C", size=30), f.text(520, c[1] + 40, "D", size=30)
    f.text(50, 130, "<i>I</i>", size=30), f.text(155, o[1] - 12, "<i>r</i>", size=30), f.text(o[0] + 20, o[1] + 100, "<i>r</i>", size=30)
    f.text(88, 344, "<i>I</i>", size=30), f.text(400, c[1] + 40, "<i>I</i>", size=30)
    return f


def wire_semicircle_to_centre():
    """A long straight wire from N (right, extending far) to P, a semicircle of radius r about C from P round to Q, then a straight piece from Q in to C."""
    f = Figure(640, 340)
    c, r = (160, 170), 110
    p, q = (c[0], c[1] - r), (c[0], c[1] + r)
    f.line(*p, 500, p[1]), f.line(500, p[1], 630, p[1], width=3, dash="12 8"), f.arrowhead(330, p[1], 180, size=18)
    f.add(f'<path d="M{p[0]},{p[1]} A{r},{r} 0 0 0 {q[0]},{q[1]}" stroke-width="3"/>'), arc_arrow(f, *c, r, 150, forward=True)
    f.line(*q, *c), f.arrowhead(c[0], c[1] + 50, -90, size=16), f.dot(*c, r=6)
    f.text(p[0] - 30, p[1] - 14, "P", size=36), f.text(q[0] - 30, q[1] + 28, "Q", size=36), f.text(c[0] + 28, c[1] + 12, "C", size=36)
    f.text(330, 40, "<i>I</i>", size=36), f.text(500, 40, "N", size=36)
    return f


def three_wires_abc():
    """Three long parallel wires A, B, C: A carries 1 A down, B 2 A down, C 3 A up."""
    f = Figure(520, 420)
    for x, name, label, down in ((90, "A", "1 A", True), (250, "B", "2 A", True), (410, "C", "3 A", False)):
        f.line(x, 60, x, 400), f.arrowhead(x, 240 if down else 220, 90 if down else -90, size=18)
        f.text(x, 40, name, size=34), f.text(x - 14, 244, label, size=32, anchor="end")
    return f


def three_wires_dcb():
    """Parallel wires D (15 A up), C (5 A down) and B (10 A up); D to B is 15 cm, D to C is x and C to B is 15 - x."""
    f = Figure(560, 420)
    d, c, b = 110, 270, 450
    for x, name, label, down in ((d, "D", "15 A", False), (c, "C", "5 A", True), (b, "B", "10 A", False)):
        f.line(x, 50, x, 320), f.arrowhead(x, 110, 90 if down else -90, size=16)
        f.text(x, 36, name, size=30), f.text(x + (16 if x != d else -16), 116, label, size=30, anchor="start" if x != d else "end")
    f.dim(d, 220, c, 220), f.dim(c, 260, b, 260), f.dim(d, 350, b, 350)
    f.text((d + c) / 2, 206, "<i>x</i>", size=30), f.text((c + b) / 2, 300, "15 − <i>x</i>", size=30), f.text(280, 396, "15 cm", size=30)
    return f


def loop_in_field_with_mass():
    """A square loop with a cell V hangs a mass; its upper side lies in a shaded magnetic field region."""
    f = Figure(640, 460)
    f.add('<rect x="80" y="30" width="330" height="170" fill="#e5e7eb" stroke="#1f2937" stroke-width="2"/>')
    for y in range(44, 200, 12):
        f.line(84, y, 406, y, width=1, dash="10 6")
    f.rect(190, 110, 140, 200), f.add('<rect x="180" y="210" width="160" height="0" />')
    f.line(330, 230, 330, 244), f.vcell(330, 254, gap=14, long=22, short=12), f.line(330, 264, 330, 310)
    f.line(260, 310, 260, 360), f.path([(260, 360), (210, 420), (310, 420)], close=True)
    f.line(420, 120, 460, 120, arrow=False), f.arrowhead(412, 120, 180, size=14), f.text(466, 112, "Magnetic", size=30, anchor="start")
    f.text(466, 148, "field", size=30, anchor="start")
    f.line(150, 250, 184, 250), f.arrowhead(188, 250, 0, size=14), f.text(30, 244, "Square", size=30, anchor="start"), f.text(30, 280, "loop", size=30, anchor="start")
    f.text(354, 266, "<i>V</i>", size=30, anchor="start")
    return f


def wire_semicircle_dip():
    """A straight wire (i) carrying I, a semicircle (ii) of radius R below the line with centre O on the line, then a straight wire (iii)."""
    f = Figure(640, 300)
    o, r, y = (330, 80), 150, 80
    f.line(20, y, o[0] - r, y), f.arrowhead(90, y, 0, size=16)
    f.add(f'<path d="M{o[0] - r},{y} A{r},{r} 0 0 0 {o[0] + r},{y}" stroke-width="3"/>'), arc_arrow(f, o[0], o[1], r, 90, forward=False)
    f.line(o[0] + r, y, 620, y), f.arrowhead(560, y, 0, size=16)
    f.dot(*o, r=6), f.line(*o, o[0] - r * math.cos(math.radians(30)), o[1] + r * math.sin(math.radians(30)), arrow=True)
    f.text(90, 56, "<i>I</i>", size=28), f.text(90, 120, "(i)", size=28), f.text(330, 270, "(ii)", size=28)
    f.text(560, 56, "(iii)", size=28), f.text(560, 120, "<i>I</i>", size=28), f.text(o[0] + 14, o[1] - 14, "O", size=28)
    f.text(272, 150, "<i>R</i>", size=28)
    return f


def three_quarter_loop_pqrst():
    """Current from P leftwards to Q, round three quarters of a circle of radius r (through R) about O to S, then rightwards to T; OQ and OS at 90 degrees."""
    f = Figure(640, 320)
    o, r = (170, 110), 90
    q, s = (o[0] + r, o[1]), (o[0], o[1] + r)
    f.line(600, o[1], *q), f.arrowhead(420, o[1], 180, size=16)
    f.add(f'<path d="M{q[0]},{q[1]} A{r},{r} 0 1 0 {s[0]},{s[1]}" stroke-width="3"/>')
    f.line(*s, 600, s[1]), f.arrowhead(420, s[1], 0, size=16)
    f.line(*o, *s, width=2, dash="8 6", arrow=True)
    rx, ry = o[0] - r * math.cos(math.radians(30)), o[1] + r * math.sin(math.radians(30))
    f.line(*o, rx, ry, width=2, dash="6 6"), f.right_angle(o[0], o[1], 1, 1, size=18), f.dot(*o, r=5)
    f.text(o[0] - 4, o[1] - 14, "O", size=28), f.text(q[0] + 18, q[1] - 12, "Q", size=28), f.text(610, o[1] + 10, "P", size=28, anchor="start")
    f.text(rx - 22, ry + 14, "R", size=28), f.text(s[0], s[1] + 40, "S", size=28), f.text(610, s[1] + 10, "T", size=28, anchor="start")
    f.text(o[0] - 52, o[1] + 20, "<i>r</i>", size=28), f.text(o[0] + 58, o[1] + 48, "90°", size=28)
    return f


def two_wires_point_p():
    """Two long parallel wires 2r apart each carry I upward; P is a distance r to the right of the right-hand wire."""
    f = Figure(520, 340)
    for x in (100, 340):
        f.line(x, 20, x, 320), f.arrowhead(x, 130, -90, size=18), f.text(x - 26, 150, "<i>I</i>", size=32)
    f.dim(104, 260, 336, 260), f.text(220, 250, "2<i>r</i>", size=32, halo=True)
    f.line(340, 200, 450, 200, arrow=True), f.dot(456, 200, r=6)
    f.text(395, 240, "<i>r</i>", size=30), f.text(474, 194, "P", size=32, anchor="start")
    return f


def two_semicircles_loop():
    """Loop PQRS: an outer semicircle of radius R1 from Q to R and an inner one of radius R2 from S to P, both about O, joined by straight pieces."""
    f = Figure(600, 380)
    o, r1, r2, y = (300, 300), 240, 120, 300
    f.add(f'<path d="M{o[0] - r1},{y} A{r1},{r1} 0 0 1 {o[0] + r1},{y}" stroke-width="4"/>')
    f.add(f'<path d="M{o[0] - r2},{y} A{r2},{r2} 0 0 1 {o[0] + r2},{y}" stroke-width="4"/>')
    f.line(o[0] - r1, y, o[0] - r2, y, width=4), f.line(o[0] + r2, y, o[0] + r1, y, width=4)
    arc_arrow(f, *o, r1, -80, forward=True, size=18), arc_arrow(f, *o, r2, -120, forward=False, size=18)
    f.arrowhead(o[0] - r1 + 30, y, 180, size=18), f.arrowhead(o[0] + r2 + 50, y, 180, size=18)
    f.line(*o, o[0] + r1 * math.cos(math.radians(-135)), o[1] + r1 * math.sin(math.radians(-135)), arrow=True)
    f.line(*o, o[0] + r2 * math.cos(math.radians(-45)), o[1] + r2 * math.sin(math.radians(-45)), arrow=True)
    f.text(o[0] - r1, y + 40, "Q", size=32), f.text(o[0] - r2, y + 40, "P", size=32), f.text(o[0], y + 40, "O", size=32)
    f.text(o[0] + r2, y + 40, "S", size=32), f.text(o[0] + r1, y + 40, "R", size=32)
    f.text(180, 140, "<i>R</i><sub>1</sub>", size=30), f.text(446, 250, "<i>R</i><sub>2</sub>", size=30), f.text(320, 46, "<i>I</i>", size=30)
    return f


def two_perpendicular_coils():
    """Two identical coils with a common centre in perpendicular planes (coil 1 vertical, coil 2 horizontal), each carrying I."""
    f = Figure(560, 400)
    ellipse(f, 300, 190, 60, 170, dash="14 10"), ellipse(f, 300, 190, 200, 50, dash="14 10")
    f.line(240, 230, 330, 230, width=2)
    f.arrowhead(160, 226, 10, size=18), f.arrowhead(250, 300, 100, size=18)
    f.text(20, 140, "coil 2", size=32, anchor="start"), f.text(330, 370, "coil 1", size=32, anchor="start")
    f.text(150, 262, "<i>I</i>", size=30), f.text(222, 330, "<i>I</i>", size=30)
    return f


def wire_semicircle_point_p():
    """A long wire comes down (1) to the top of a semicircle of radius r about P, the current goes round the left (2) to the bottom, then out along a long horizontal wire (3)."""
    f = Figure(520, 420)
    p, r = (200, 220), 110
    f.line(p[0], 20, p[0], p[1] - r), f.arrowhead(p[0], 60, 90, size=16)
    f.add(f'<path d="M{p[0]},{p[1] - r} A{r},{r} 0 0 0 {p[0]},{p[1] + r}" stroke-width="3"/>')
    arc_arrow(f, *p, r, 225, forward=False), arc_arrow(f, *p, r, 140, forward=False)
    f.line(p[0], p[1] + r, 470, p[1] + r), f.arrowhead(380, p[1] + r, 0, size=16)
    f.line(p[0] - r, p[1], *p, width=2, dash="8 6"), f.line(p[0], p[1] - r, p[0], p[1] + r, width=2, dash="8 6"), f.dot(*p, r=5)
    f.text(p[0] + 22, p[1] + 10, "P", size=30, anchor="start"), f.text(p[0] - 55, p[1] - 12, "<i>r</i>", size=28)
    f.text(p[0] + 22, p[1] + 70, "<i>r</i>", size=28, anchor="start"), f.text(p[0] + 22, 60, "1", size=28, anchor="start")
    f.text(p[0] - r - 26, p[1] + 10, "2", size=28), f.text(380, p[1] + r + 40, "3", size=28), f.text(p[0] - r - 6, p[1] + 90, "<i>I</i>", size=28)
    return f


def omega_loop():
    """A long straight wire carrying I comes in from the left, goes round a nearly complete circle of radius r about O, and leaves to the right."""
    f = Figure(600, 400)
    o, r = (300, 180), 120
    a1, a2 = 115, 65  # degrees where the loop leaves the straight line (90 = straight down)
    p1 = (o[0] + r * math.cos(math.radians(a1)), o[1] + r * math.sin(math.radians(a1)))
    p2 = (o[0] + r * math.cos(math.radians(a2)), o[1] + r * math.sin(math.radians(a2)))
    y = p1[1]
    f.line(20, y, *p1), f.arrowhead(100, y, 0, size=16)
    f.add(f'<path d="M{p1[0]:.1f},{p1[1]:.1f} A{r},{r} 0 1 1 {p2[0]:.1f},{p2[1]:.1f}" stroke-width="3"/>')
    f.line(*p2, 580, y), f.arrowhead(500, y, 0, size=16), arc_arrow(f, *o, r, -90, forward=True)
    f.dot(*o, r=6), f.line(*o, o[0] + r * math.cos(math.radians(-40)), o[1] + r * math.sin(math.radians(-40)), width=2, dash="6 6")
    f.text(o[0], o[1] + 36, "O", size=30), f.text(o[0] + 60, o[1] - 30, "<i>r</i>", size=30), f.text(o[0], o[1] - r - 20, "<i>I</i>", size=30)
    f.text(100, y + 40, "<i>I</i>", size=30), f.text(500, y + 40, "<i>I</i>", size=30)
    return f


FIGURES = {
    "PYQ-PHY-36551d9e1346": wire_quarter_arc_wire,
    "PYQ-PHY-94c5b76cd4ea": wire_semicircle_to_centre,
    "PYQ-PHY-e6ebd587f542": three_wires_abc,
    "PYQ-PHY-301859d72313": three_wires_dcb,
    "PYQ-PHY-b94cb42ea969": loop_in_field_with_mass,
    "PYQ-PHY-40e1e4773c1a": wire_semicircle_dip,
    "PYQ-PHY-91402f48388d": three_quarter_loop_pqrst,
    "PYQ-PHY-539dd6a4c93d": two_wires_point_p,
    "PYQ-PHY-694aaa6346c0": two_semicircles_loop,
    "PYQ-PHY-d8a278c78413": two_perpendicular_coils,
    "PYQ-PHY-6b12816562af": wire_semicircle_point_p,
    "PYQ-PHY-20be53c65ccf": omega_loop,
}
