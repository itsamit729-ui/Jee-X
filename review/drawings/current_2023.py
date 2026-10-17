"""Physics (MHT-CET 2020-23): current electricity - networks, bridges and junctions."""

import math

from figlib import Figure, mid_arrow, slant_resistor


def wire(f, *points):
    f.polyline(list(points))


def arrow_label(f, x1, y1, x2, y2, label, lx, ly, at=0.6, size=32, anchor="middle"):
    mid_arrow(f, x1, y1, x2, y2, at=at, size=16)
    f.text(lx, ly, label, size=size, anchor=anchor)


def coil_on_battery():
    """A circular coil: the minor arc PQ (a quarter of the circle) is 10 ohm and the rest 30 ohm; P and Q are joined to a 16 V cell; current I flows up into P and down out of Q."""
    f = Figure(460, 440)
    c, r = (180, 160), 140
    p = (c[0] + r * math.cos(math.radians(70)), c[1] + r * math.sin(math.radians(70)))
    q = (c[0] + r * math.cos(math.radians(-20)), c[1] + r * math.sin(math.radians(-20)))
    f.circle(*c, r)
    f.dot(*p, r=5), f.dot(*q, r=5)
    wire(f, p, (p[0], 380), (p[0] + 50, 380)), f.cell(p[0] + 60, 380, gap=16, long=22, short=12)
    wire(f, (p[0] + 68, 380), (q[0] + 30, 380), (q[0] + 30, q[1]), q)
    f.arrowhead(p[0], 340, -90, size=14), f.arrowhead(q[0] + 30, 260, 90, size=14)
    f.text(120, 70, "30 Ω", size=28), f.text(250, 220, "10 Ω", size=26)
    f.text(p[0] - 14, p[1] + 34, "P", size=28), f.text(q[0] + 44, q[1] + 10, "Q", size=28)
    f.text(p[0] - 22, 350, "<i>I</i>", size=28), f.text(q[0] + 54, 270, "<i>I</i>", size=28)
    f.text(p[0] + 60, 430, "16 V", size=28), f.text(p[0] + 46, 356, "+", size=22), f.text(p[0] + 76, 356, "−", size=22)
    return f


def network_abcdef():
    """A-B 28 ohm and B-C 54 ohm on top; a 6 V cell from B down to E (current I downward); F-E 8 V cell and E-D 12 V cell on the bottom wire."""
    f = Figure(760, 440)
    l, r, m, t, b = 40, 720, 380, 70, 360
    f.line(l, t, 150, t), f.resistor(150, 270, t, peaks=5, height=18), f.line(270, t, 490, t)
    f.resistor(490, 610, t, peaks=5, height=18), f.line(610, t, r, t)
    f.line(l, t, l, b), f.line(r, t, r, b)
    f.line(m, t, m, 146), f.vcell(m, 156, gap=20, long=30, short=16), f.line(m, 166, m, b), f.arrowhead(m, 280, 90, size=18)
    f.line(l, b, 170, b), f.cell(181, b, gap=22, long=30, short=16), f.line(192, b, 570, b)
    f.cell(581, b, gap=22, long=30, short=16), f.line(592, b, r, b)
    f.dot(m, t), f.dot(m, b)
    for x, y, lab in ((l - 20, t + 10, "A"), (m, t - 26, "B"), (r + 22, t + 10, "C"), (r + 22, b + 10, "D"), (m, b + 44, "E"), (l - 20, b + 10, "F")):
        f.text(x, y, lab, size=30)
    f.text(210, 36, "28 Ω", size=30), f.text(550, 36, "54 Ω", size=30), f.text(410, 166, "6 V", size=30, anchor="start")
    f.text(400, 300, "<i>I</i>", size=30, anchor="start"), f.text(181, 420, "8 V", size=30), f.text(581, 420, "12 V", size=30)
    return f


def bridge_pqrs_21a():
    """Bridge: P-Q 5 ohm, Q-R 1 ohm, P-S 12.5 ohm, S-R 2.5 ohm; galvanometer G between Q and S; 2.1 A enters at P and leaves at R."""
    f = Figure(640, 460)
    p, q, r, s = (160, 230), (320, 50), (480, 230), (320, 410)
    for a, b in ((p, q), (q, r), (p, s), (s, r)):
        slant_resistor(f, a, b, length=110)
    f.line(*q, 320, 200), f.meter(320, 230, "G", r=28), f.line(320, 258, *s)
    f.line(20, 230, *p), f.arrowhead(90, 230, 0, size=18), f.line(*r, 620, 230, arrow=True)
    for pt in (p, q, r, s):
        f.dot(*pt, r=7)
    f.text(30, 210, "2.1 A", size=28, anchor="start"), f.text(610, 270, "2.1 A", size=28, anchor="end")
    f.text(p[0] - 10, p[1] - 18, "P", size=30), f.text(q[0], q[1] - 16, "Q", size=30), f.text(r[0] + 10, r[1] - 18, "R", size=30)
    f.text(s[0], s[1] + 40, "S", size=30)
    f.text(200, 120, "5 Ω", size=28), f.text(440, 120, "1 Ω", size=28), f.text(180, 360, "12.5 Ω", size=28), f.text(460, 360, "2.5 Ω", size=28)
    return f


def metre_bridge_4_y():
    """Metre bridge: 4 ohm and Y in the gaps; galvanometer G from the junction to the wire, which it divides into 40 cm and 60 cm; a 6 V cell below."""
    f = Figure(640, 370)
    l, r, m, t, w, b = 20, 620, 290, 60, 220, 300
    f.line(l, t, 80, t), f.resistor(80, 190, t, peaks=5, height=16), f.line(190, t, 390, t)
    f.resistor(390, 500, t, peaks=5, height=16), f.line(500, t, r, t)
    f.line(l, t, l, b), f.line(r, t, r, b), f.line(l, w, r, w, width=5)
    f.line(m, t, m, 116), f.meter(m, 142, "G", r=26), f.line(m, 168, m, w)
    f.line(l, b, 289, b), f.cell(300, b, gap=22, long=26, short=14), f.line(311, b, r, b)
    f.text(135, 30, "4 Ω", size=30), f.text(445, 30, "<i>Y</i>", size=30)
    f.text(155, 206, "40 cm", size=30), f.text(455, 206, "60 cm", size=30), f.text(300, 356, "6 V", size=28)
    return f


def parallel_8_3_then_5():
    """Current I splits into I1 (1.5 A) through 8 ohm and I2 through 3 ohm; it recombines and passes 5 ohm; a cell V (+ on the left) and key k close the loop."""
    f = Figure(640, 420)
    l, a, b, r, t1, t2, mid, bot = 20, 110, 400, 600, 60, 200, 130, 370
    f.line(a, t1, a, t2), f.line(b, t1, b, t2)
    f.line(a, t1, 220, t1), f.resistor(220, 320, t1, peaks=5, height=14), f.line(320, t1, b, t1)
    f.line(a, t2, 220, t2), f.resistor(220, 320, t2, peaks=5, height=14), f.line(320, t2, b, t2)
    f.line(l, mid, a, mid), f.arrowhead(70, mid, 0, size=16)
    f.line(b, mid, 470, mid), f.arrowhead(440, mid, 0, size=16), f.resistor(470, 560, mid, peaks=5, height=14), f.line(560, mid, r, mid)
    f.line(l, mid, l, bot), f.line(r, mid, r, bot)
    f.line(l, bot, 150, bot), f.cell(161, bot, gap=18, long=24, short=14), f.line(172, bot, 430, bot)
    f.circle(460, bot, 22), f.dot(460, bot, r=5), f.line(482, bot, r, bot)
    f.text(130, 40, "1.5 A", size=26), f.text(270, 34, "8 Ω", size=26), f.text(150, 94, "<i>I</i><sub>1</sub>", size=26)
    f.text(150, 180, "<i>I</i><sub>2</sub>", size=26), f.text(270, 174, "3 Ω", size=26)
    f.text(50, 110, "<i>I</i>", size=26), f.text(440, 110, "<i>I</i>", size=26), f.text(515, 104, "5 Ω", size=26)
    f.text(161, 342, "<i>V</i>", size=26), f.text(140, 410, "+", size=22), f.text(182, 410, "−", size=22), f.text(460, 352, "k", size=26)
    return f


def junction_chain_i():
    """1 A, 2 A and 3 A flow into a node; the current goes on to a second node where 1.2 A leaves; further along 0.8 A joins,
    0.5 A and 1.7 A leave, and the remainder I continues."""
    f = Figure(640, 420)
    n1, n2 = (170, 160), (360, 160)
    arrow_label(f, 20, 40, *n1, "1 A", 30, 30, at=0.55, size=28)
    arrow_label(f, 30, 330, *n1, "2 A", 30, 380, at=0.55, size=28)
    arrow_label(f, 170, 330, *n1, "3 A", 186, 380, at=0.5, size=28)
    mid_arrow(f, *n1, *n2, at=0.55, size=16)
    arrow_label(f, *n2, 410, 110, "1.2 A", 420, 100, at=0.9, size=28, anchor="start")
    end = (620, 330)
    f.line(*n2, *end), f.arrowhead(*end, math.degrees(math.atan2(end[1] - n2[1], end[0] - n2[0])), size=18)
    along = lambda t: (n2[0] + (end[0] - n2[0]) * t, n2[1] + (end[1] - n2[1]) * t)  # noqa: E731
    p1, p2, p3 = along(0.3), along(0.55), along(0.75)
    arrow_label(f, p1[0] - 30, p1[1] + 40, *p1, "0.8 A", p1[0] - 30, p1[1] + 80, at=0.8, size=28)
    arrow_label(f, *p2, p2[0] + 40, p2[1] - 50, "0.5 A", p2[0] + 50, p2[1] - 60, at=0.9, size=28, anchor="start")
    arrow_label(f, *p3, p3[0] - 30, p3[1] + 50, "1.7 A", p3[0] - 10, p3[1] + 90, at=0.9, size=28)
    f.text(end[0] - 10, end[1] + 40, "<i>I</i>", size=30)
    return f


def network_3_5_2_2_3_6v():
    """Left rail to node A through 3 ohm; A to node B through 5 ohm; B to the right rail through 2 ohm; another 2 ohm from A over the top
    to the right rail; a second 3 ohm from the left rail to B underneath; a 6 V cell joins the rails at the bottom."""
    f = Figure(700, 420)
    l, r, a, b = 20, 680, 230, 450
    top, mid, low, bot = 50, 150, 270, 380
    f.line(l, mid, l, bot), f.line(r, top, r, bot)
    f.line(l, mid, 80, mid), f.resistor(80, 170, mid, peaks=5, height=16), f.line(170, mid, a, mid)
    f.line(a, mid, 290, mid), f.resistor(290, 380, mid, peaks=5, height=16), f.line(380, mid, b, mid)
    f.line(b, mid, 520, mid), f.resistor(520, 610, mid, peaks=5, height=16), f.line(610, mid, r, mid)
    wire(f, (a, mid), (a, top), (410, top)), f.resistor(410, 500, top, peaks=5, height=16), f.line(500, top, r, top)
    wire(f, (l, low), (190, low)), f.resistor(190, 280, low, peaks=5, height=16), wire(f, (280, low), (b, low), (b, mid))
    f.line(l, bot, 339, bot), f.cell(350, bot, gap=20, long=28, short=14), f.line(361, bot, r, bot)
    f.dot(a, mid), f.dot(b, mid), f.dot(l, low)
    f.text(125, 200, "3 Ω", size=28), f.text(335, 200, "5 Ω", size=28), f.text(565, 200, "2 Ω", size=28)
    f.text(455, 26, "2 Ω", size=28), f.text(235, 238, "3 Ω", size=28), f.text(390, 370, "6 V", size=28)
    return f


def bridge_pqrs_4_4_1_3():
    """Bridge: P-Q 4 ohm, Q-R 4 ohm, P-S 1 ohm, S-R 3 ohm; galvanometer G between Q and S; a cell V joins P and R."""
    f = Figure(520, 420)
    p, q, r, s = (90, 140), (260, 30), (430, 140), (260, 250)
    for a, b in ((p, q), (q, r), (p, s), (s, r)):
        slant_resistor(f, a, b, length=90, height=10)
    f.line(*q, 260, 114), f.meter(260, 140, "G", r=26), f.line(260, 166, *s)
    wire(f, p, (20, 140), (20, 340), (249, 340)), f.cell(260, 340, gap=20, long=26, short=14), wire(f, (271, 340), (500, 340), (500, 140), r)
    f.text(p[0] - 10, p[1] - 14, "P", size=28, anchor="end"), f.text(q[0], q[1] - 6, "Q", size=28, halo=True)
    f.text(r[0] + 10, r[1] - 14, "R", size=28, anchor="start"), f.text(s[0], s[1] + 36, "S", size=28)
    f.text(150, 60, "4 Ω", size=26), f.text(370, 60, "4 Ω", size=26), f.text(140, 230, "1 Ω", size=26), f.text(380, 230, "3 Ω", size=26)
    f.text(260, 390, "<i>V</i>", size=28)
    return f


def bridge_pqrs_rect():
    """P to R: 6 ohm then 3 ohm along the top (through Q), 8 ohm then 4 ohm along the bottom (through S); galvanometer G from Q to S; 5 A enters at P."""
    f = Figure(700, 300)
    l, r, m, t, b, y = 130, 560, 345, 50, 250, 150
    f.line(l, t, l, b), f.line(r, t, r, b)
    for yy, (r1, r2) in ((t, ("6 Ω", "3 Ω")), (b, ("8 Ω", "4 Ω"))):
        f.line(l, yy, 180, yy), f.resistor(180, 270, yy, peaks=5, height=14), f.line(270, yy, 450, yy)
        f.resistor(450, 540, yy, peaks=5, height=14), f.line(540, yy, r, yy)
        dy = 46 if yy == t else -26
        f.text(225, yy + dy, r1, size=28), f.text(495, yy + dy, r2, size=28)
    f.line(m, t, m, 124), f.meter(m, y, "G", r=26), f.line(m, 176, m, b)
    f.line(20, y, l, y), f.arrowhead(80, y, 0, size=16), f.line(r, y, 680, y, arrow=True)
    f.dot(l, y, r=6), f.dot(r, y, r=6)
    f.text(l - 14, y - 12, "P", size=28, anchor="end"), f.text(m, t - 14, "Q", size=28), f.text(r + 14, y - 12, "R", size=28, anchor="start")
    f.text(m, b + 40, "S", size=28), f.text(60, y + 40, "5 A", size=28)
    return f


def voltmeter_two_cells():
    """A voltmeter V on the top wire; 2 ohm and a 12 V cell on the middle wire; 1 ohm and a 6 V cell on the bottom wire; the three wires in parallel."""
    f = Figure(640, 360)
    l, r, t, m, b = 20, 620, 50, 170, 300
    f.line(l, t, l, b), f.line(r, t, r, b)
    f.line(l, t, 290, t), f.meter(320, t, "V", r=30), f.line(350, t, r, t)
    for y, ohm, volt in ((m, "2 Ω", "12 V"), (b, "1 Ω", "6 V")):
        f.line(l, y, 120, y), f.resistor(120, 240, y, peaks=5, height=16), f.line(240, y, 389, y)
        f.cell(400, y, gap=22, long=30, short=16), f.line(411, y, r, y)
        f.text(180, y - 30, ohm, size=34), f.text(470, y - 30 if y == m else y + 50, volt, size=34)
    return f


def bridge_with_rheostat():
    """Bridge: A-B 5 ohm, B-C 10 ohm, A-D 20 ohm, D-C 40 ohm; galvanometer G (100 ohm) from B to D; currents I1, I2 leave A;
    a 3 V cell, key and rheostat complete the circuit, current I."""
    f = Figure(680, 560)
    a, b, c, d = (120, 230), (330, 30), (540, 230), (330, 430)
    for p, q in ((a, b), (b, c), (a, d), (d, c)):
        slant_resistor(f, p, q, length=130, peaks=6, height=10)
    f.line(*b, 330, 204), f.meter(330, 230, "G", r=26), f.line(330, 256, *d)
    wire(f, a, (40, a[1]), (40, 490), (120, 490)), f.cell(130, 490, gap=16, long=22, short=12)
    f.line(138, 490, 230, 490), f.text(256, 500, "(·)", size=28), f.line(282, 490, 360, 490)
    f.resistor(360, 660, 490, peaks=12, height=14)
    wire(f, c, (620, c[1])), f.line(620, c[1], 620, 474, arrow=True)
    f.arrowhead(40, 380, -90, size=16), f.arrowhead(620, 330, 90, size=16)
    f.text(a[0] + 4, a[1] + 44, "A", size=28), f.text(b[0], b[1] - 8, "B", size=28, halo=True), f.text(c[0] + 10, c[1] - 14, "C", size=28)
    f.text(d[0], d[1] + 40, "D", size=28)
    f.text(180, 100, "5 Ω", size=26), f.text(470, 100, "10 Ω", size=26), f.text(170, 370, "20 Ω", size=26), f.text(480, 370, "40 Ω", size=26)
    f.text(200, 238, "100 Ω", size=26), f.text(80, 214, "<i>I</i><sub>1</sub>", size=24), f.text(80, 268, "<i>I</i><sub>2</sub>", size=24)
    f.text(20, 390, "<i>I</i>", size=26), f.text(646, 340, "<i>I</i>", size=26), f.text(130, 540, "3 V", size=24)
    f.text(116, 470, "+", size=20), f.text(146, 470, "−", size=20), f.text(560, 540, "Rheostat", size=24)
    return f


def five_conductors_p():
    """At P: 4 A flows in from above, 5 A in from the left, 3 A out to the right, 5 A out downward, and a fifth conductor runs to Q (down and to the right)."""
    f = Figure(420, 420)
    p = (200, 200)
    arrow_label(f, 200, 20, *p, "4 A", 230, 50, at=0.55, size=28, anchor="start")
    arrow_label(f, 20, 200, *p, "5 A", 40, 180, at=0.4, size=28, anchor="start")
    arrow_label(f, *p, 400, 200, "3 A", 330, 180, at=0.7, size=28)
    arrow_label(f, *p, 200, 400, "5 A", 160, 370, at=0.7, size=28, anchor="end")
    f.line(*p, 330, 330), f.text(346, 356, "Q", size=30), f.text(176, 236, "P", size=30)
    return f


def five_conductors_o():
    """At O: 10 A flows in from the upper left, 2.5 A in from the lower left and 5 A in from the lower right; 6 A flows out to the upper right; conductor OP runs straight down to P."""
    f = Figure(420, 440)
    o = (210, 180)
    arrow_label(f, 40, 20, *o, "10 A", 20, 130, at=0.6, size=34, anchor="start")
    arrow_label(f, 30, 360, *o, "2.5 A", 70, 400, at=0.5, size=34, anchor="start")
    arrow_label(f, 390, 360, *o, "5 A", 330, 260, at=0.55, size=34, anchor="start")
    arrow_label(f, *o, 380, 20, "6 A", 320, 130, at=0.6, size=34, anchor="start")
    f.dot(*o, r=10), f.line(*o, 210, 380), f.dot(210, 380, r=10)
    f.text(210, 160, "O", size=34, halo=True), f.text(210, 428, "P", size=34)
    return f


FIGURES = {
    "PYQ-PHY-ea2129a88cee": coil_on_battery,
    "PYQ-PHY-47b7cdbb7f3b": network_abcdef,
    "PYQ-PHY-ddd0bfbeaa3f": bridge_pqrs_21a,
    "PYQ-PHY-688362e02fdc": metre_bridge_4_y,
    "PYQ-PHY-63ba04d4aef8": parallel_8_3_then_5,
    "PYQ-PHY-2a43d72effb9": junction_chain_i,
    "PYQ-PHY-fedc75c67c54": network_3_5_2_2_3_6v,
    "PYQ-PHY-6e20d16d1bd4": bridge_pqrs_4_4_1_3,
    "PYQ-PHY-f0e09df7e029": bridge_pqrs_rect,
    "PYQ-PHY-322cd20a5b7f": bridge_pqrs_rect,
    "PYQ-PHY-96724fa0c295": voltmeter_two_cells,
    "PYQ-PHY-25b3611b4ce7": bridge_with_rheostat,
    "PYQ-PHY-814d4311fe76": five_conductors_p,
    "PYQ-PHY-42eae79c1c23": five_conductors_o,
}
