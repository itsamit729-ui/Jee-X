"""Physics (MHT-CET 2020-23): alternating current circuits and rotational motion."""

import math

from figlib import Figure, coil


def wire(f, *points):
    f.polyline(list(points))


def hcoil(f, x1, x2, y, turns=6, radius=13):
    """An inductor drawn as humps on a horizontal wire."""
    step = (x2 - x1) / turns
    f.add(" ".join(f'<path d="M{x1 + step * i:.1f},{y} a{step / 2:.1f},{radius} 0 1 1 {step:.1f},0" stroke-width="3"/>' for i in range(turns)))


def three_inductors_pq():
    """P to Q: three inductors L in a row; a wire over the top joins the node after the first L to Q;
    a wire underneath joins P to the node after the second L."""
    f = Figure(760, 220)
    y, p, n1, n2, q = 110, 30, 270, 480, 720
    f.dot(p, y, r=7), f.text(14, y + 10, "P", size=28), f.dot(q, y, r=7), f.text(736, y + 10, "Q", size=28, anchor="start")
    f.line(p, y, 100, y), hcoil(f, 100, 220, y), f.line(220, y, n1, y)
    f.line(n1, y, 310, y), hcoil(f, 310, 430, y), f.line(430, y, n2, y)
    f.line(n2, y, 520, y), hcoil(f, 520, 640, y), f.line(640, y, q, y)
    wire(f, (n1, y), (n1, 30), (690, 30), (690, y))
    wire(f, (75, y), (75, 190), (n2, 190), (n2, y))
    for x in (160, 370, 580):
        f.text(x, 76, "<i>L</i>", size=28)
    return f


def source_r_c_l_parallel():
    """An a.c. source e = e0 sin t with R, C and L each connected across it in parallel."""
    f = Figure(600, 380)
    t, b, xs = 40, 320, 60
    f.line(xs, t, 520, t), f.line(xs, b, 520, b)
    f.line(xs, t, xs, 142), f.ac_source(xs, 170, r=28), f.line(xs, 198, xs, b)
    f.vresistor(180, 100, 260), f.line(180, t, 180, 100), f.line(180, 260, 180, b)
    f.line(330, t, 330, 173), f.vcapacitor(330, 180, gap=14, half=32), f.line(330, 187, 330, b)
    f.line(520, t, 520, 110), f.line(520, 250, 520, b)
    with f.rotated(90, 520, 180):
        coil(f, 450, 590, 180, turns=6, radius=16)
    f.text(84, 130, "<i>e</i>", size=30), f.text(206, 190, "<i>R</i>", size=30, anchor="start")
    f.text(360, 150, "<i>C</i>", size=30, anchor="start"), f.text(548, 190, "<i>L</i>", size=30, anchor="start")
    f.text(20, 368, "<i>e</i> = <i>e</i><sub>0</sub> sin <i>t</i>", size=30, anchor="start")
    return f


def ac_r_l_c():
    """An a.c. source; R = 10 ohm on the top wire; an inductor L (5 mH, 5 ohm) and a capacitor C (50 uF) on the bottom wire."""
    f = Figure(600, 360)
    l, r, t, b = 130, 560, 60, 290
    f.line(l, t, 260, t), f.resistor(260, 370, t, peaks=5, height=14), f.line(370, t, r, t)
    f.line(l, t, l, 150), f.ac_source(l, 178, r=28), f.line(l, 206, l, b), f.line(r, t, r, b)
    f.line(l, b, 220, b), hcoil(f, 220, 340, b), f.line(340, b, 443, b), f.capacitor(450, b, gap=14, height=26), f.line(457, b, r, b)
    f.text(315, 36, "10 Ω", size=28), f.text(315, 106, "<i>R</i>", size=28)
    f.text(280, 252, "5 mH, 5 Ω", size=28), f.text(280, 340, "<i>L</i>", size=28)
    f.text(450, 248, "<i>C</i>", size=28), f.text(490, 340, "50 μF", size=28)
    f.text(52, 172, "a.c.", size=26), f.text(52, 204, "Source", size=26)
    return f


def a_l_r_b():
    """A, an inductor L, a resistor R, B."""
    f = Figure(720, 140)
    y = 80
    f.dot(40, y, r=9), f.text(20, y + 12, "A", size=34), f.line(40, y, 140, y), hcoil(f, 140, 300, y, turns=6)
    f.line(300, y, 380, y), f.resistor(380, 600, y, peaks=7, height=18), f.line(600, y, 680, y), f.dot(680, y, r=9)
    f.text(704, y + 12, "B", size=34, anchor="start"), f.text(220, 40, "<i>L</i>", size=34), f.text(490, 40, "<i>R</i>", size=34)
    return f


def current_frequency_options():
    """r.m.s. current I against frequency f: (P) a flat-bottomed dip, (Q) a smooth dip, (R) a flat-topped peak, (S) a smooth peak."""
    f = Figure(760, 220)
    for name, ox in zip("PQRS", (20, 210, 400, 590)):
        f.line(ox, 160, ox, 30), f.line(ox, 160, ox + 160, 160, arrow=False)
        f.line(ox + 110, 178, ox + 150, 178, arrow=True), f.text(ox + 160, 186, "<i>f</i>", size=22, anchor="start")
        f.line(ox - 12, 60, ox - 12, 30, arrow=True), f.text(ox - 12, 80, "<i>I</i>", size=22)
        f.text(ox + 70, 212, f"({name})", size=24)
    f.polyline([(30, 50), (60, 140), (100, 140), (140, 50)])
    f.add('<path d="M220,50 C270,50 270,140 300,140 C330,140 330,50 370,50" stroke-width="3"/>')
    f.polyline([(410, 150), (440, 70), (460, 70), (470, 50), (480, 70), (500, 70), (530, 150)])
    f.add('<path d="M600,150 C660,150 660,40 690,40 C720,40 720,150 750,150" stroke-width="3"/>')
    return f


def lcr_230v():
    """230 V a.c. source; 10 ohm on the top wire, 27 uF on the right side, 3 H on the bottom wire."""
    f = Figure(680, 340)
    l, r, t, b = 110, 540, 60, 280
    f.line(l, t, 280, t), f.resistor(280, 380, t, peaks=5, height=16), f.line(380, t, r, t)
    f.line(l, t, l, 142), f.ac_source(l, 170, r=28), f.line(l, 198, l, b)
    f.line(r, t, r, 163), f.vcapacitor(r, 170, gap=14, half=28), f.line(r, 177, r, b)
    f.line(l, b, 260, b), hcoil(f, 260, 400, b, turns=6), f.line(400, b, r, b)
    f.text(330, 36, "10 Ω", size=32), f.text(74, 182, "230 V", size=30, anchor="end")
    f.text(582, 182, "27 μF", size=32, anchor="start"), f.text(330, 330, "3 H", size=32)
    return f


def l_and_c_parallel_source():
    """L on the top wire and C on a middle wire, in parallel, driven by an a.c. source E on the bottom wire."""
    f = Figure(560, 340)
    l, r, t, m, b = 20, 540, 60, 160, 270
    f.line(l, t, l, b), f.line(r, t, r, b)
    f.line(l, t, 210, t), hcoil(f, 210, 330, t), f.line(330, t, r, t)
    f.line(l, m, 273, m), f.capacitor(280, m, gap=14, height=24), f.line(287, m, r, m)
    f.line(l, b, 252, b), f.ac_source(280, b, r=26), f.line(306, b, r, b)
    f.text(270, 30, "<i>L</i>", size=32), f.text(310, 210, "<i>C</i>", size=32), f.text(310, 326, "<i>E</i>", size=32)
    return f


def inductor_resistor_cell():
    """A, 12 ohm, then 6 H (current 2 A flowing from A towards the coil) on the top wire; a 12 V cell on the bottom wire to B."""
    f = Figure(640, 300)
    t, b, l = 50, 240, 30
    f.dot(560, t, r=9), f.text(580, t + 10, "A", size=32, anchor="start"), f.line(560, t, 480, t)
    f.resistor(380, 480, t, peaks=5, height=14), f.line(380, t, 260, t), f.arrowhead(300, t, 180, size=18)
    hcoil(f, 110, 250, t, turns=7), f.line(110, t, l, t), f.line(250, t, 260, t)
    f.line(l, t, l, b), f.line(l, b, 140, b), f.cell(151, b, gap=22, long=30, short=16), f.line(162, b, 560, b)
    f.dot(560, b, r=9), f.text(580, b + 10, "B", size=32, anchor="start")
    f.text(180, 100, "6 H", size=30), f.text(300, 100, "2 A", size=30), f.text(430, 100, "12 Ω", size=30), f.text(200, 290, "12 V", size=30)
    return f


def lcr_xl_xc_r():
    """X_L = 200 ohm, X_C = 100 ohm and R = 100 ohm in series on the top wire; a.c. source V_rms = 200 root 2 V on the bottom wire."""
    f = Figure(560, 340)
    l, r, t, b = 30, 520, 50, 270
    f.line(l, t, 50, t), hcoil(f, 50, 170, t), f.line(170, t, 233, t), f.capacitor(240, t, gap=14, height=26)
    f.line(247, t, 330, t), f.resistor(330, 430, t, peaks=5, height=14), f.line(430, t, r, t)
    f.line(l, t, l, b), f.line(r, t, r, b), f.line(l, b, 252, b), f.ac_source(280, b, r=26), f.line(306, b, r, b)
    f.text(110, 104, "<i>X</i><sub>L</sub> = 200 Ω", size=28), f.text(400, 104, "<i>R</i> = 100 Ω", size=28)
    f.text(240, 156, "<i>X</i><sub>C</sub> = 100 Ω", size=28), f.text(280, 330, "<i>V</i><sub>rms</sub> = 200√2 V", size=28)
    return f


def three_rings_axis():
    """Three rings of radius R: ring 1 on top with the axis YY' through its centre; rings 2 and 3 below, touching each other at the axis."""
    f = Figure(460, 520)
    x, r = 230, 100
    f.line(x, 20, x, 500, width=2.5, dash="12 8")
    c1, c2, c3 = (x, 150), (x - r, 150 + r * math.sqrt(3)), (x + r, 150 + r * math.sqrt(3))
    for c in (c1, c2, c3):
        f.circle(*c, r, width=4)
    f.line(*c1, c1[0] + r, c1[1], width=2, dash="8 6"), f.line(c2[0], c2[1], c3[0], c3[1], width=2, dash="8 6")
    f.text(c1[0] - 14, c1[1] + 10, "1", size=26, anchor="end"), f.text(c1[0] + 50, c1[1] - 14, "<i>R</i>", size=26)
    f.text(c2[0], c2[1] + 34, "2", size=26), f.text(c3[0], c3[1] + 34, "3", size=26)
    f.text(c2[0] + 50, c2[1] - 14, "<i>R</i>", size=26), f.text(c3[0] - 50, c3[1] - 14, "<i>R</i>", size=26)
    f.text(x - 18, 30, "Y", size=28, anchor="end"), f.text(x - 18, 498, "Y′", size=28, anchor="end")
    return f


def three_spheres_dots():
    """Three equal solid spheres: one on top with the axis YY' through its centre; two below, touching each other at the axis."""
    f = Figure(300, 460)
    x, r = 150, 62
    f.line(x, 20, x, 440, width=3)
    c1, c2, c3 = (x, 130), (x - r, 130 + r * math.sqrt(3)), (x + r, 130 + r * math.sqrt(3))
    for c in (c1, c2, c3):
        f.circle(*c, r, width=3), f.dot(*c, r=5)
    f.text(x - 20, 46, "Y", size=34, anchor="end"), f.text(x - 20, 430, "Y′", size=34, anchor="end")
    return f


def triangle_lamina_axes():
    """A right-angled triangular lamina PQR (right angle at Q); T and S lie on the hypotenuse PR, with lines QT and QS."""
    f = Figure(420, 460)
    p, q, r = (60, 40), (60, 420), (380, 420)
    f.path([p, q, r], close=True, width=3)
    t = (p[0] + (r[0] - p[0]) * 0.28, p[1] + (r[1] - p[1]) * 0.28)
    s = (p[0] + (r[0] - p[0]) * 0.5, p[1] + (r[1] - p[1]) * 0.5)
    f.line(*q, *t, width=3), f.line(*q, *s, width=3)
    f.text(40, 40, "P", size=34), f.text(36, 440, "Q", size=34), f.text(400, 440, "R", size=34)
    f.text(t[0] + 22, t[1] + 4, "T", size=34, anchor="start"), f.text(s[0] + 22, s[1] + 4, "S", size=34, anchor="start")
    return f


def seven_discs():
    """Seven identical discs of radius R: one at the centre and six around it, each touching its neighbours; R marked on the centre disc."""
    f = Figure(460, 460)
    c, r = (230, 230), 74
    centres = [c] + [(c[0] + 2 * r * math.cos(math.radians(90 + 60 * i)), c[1] - 2 * r * math.sin(math.radians(90 + 60 * i))) for i in range(6)]
    for x, y in centres:
        f.circle(x, y, r, width=3), f.dot(x, y, r=6)
    f.dim(c[0] + 4, c[1], c[0] + r - 2, c[1]), f.text(c[0] + 36, c[1] + 40, "<i>R</i>", size=30)
    return f


def disc_parallel_axis():
    """A disc of radius R with axis CM through its centre (perpendicular to the plane, drawn as a line) and a parallel axis AB a distance 2R/3 from it."""
    f = Figure(360, 460)
    c, r = (180, 220), 150
    f.circle(*c, r, width=3)
    f.line(c[0], 30, c[0], 420, width=2.5), f.line(c[0] + 30, 30, c[0] + 30, 420, width=2.5)
    f.dot(*c, r=5), f.dot(c[0] + 30, c[1], r=5), f.line(c[0] - r, c[1], c[0], c[1], width=2.5)
    f.dim(c[0] + 2, 400, c[0] + 28, 400)
    f.text(c[0] - 10, 40, "C", size=28, anchor="end"), f.text(c[0] + 40, 40, "A", size=28, anchor="start")
    f.text(c[0] - 10, 450, "M", size=28, anchor="end"), f.text(c[0] + 40, 450, "B", size=28, anchor="start")
    f.text(c[0] - 80, c[1] + 34, "<i>R</i>", size=28), f.text(c[0] + 40, 410, "2<i>R</i>/3", size=26, anchor="start")
    return f


def four_spheres_row(top_r=False):
    """Four identical spheres touching in a row with centres A, B, C, D; dashed axes through each centre and a dashed line through the centres."""
    f = Figure(760, 340)
    r, y, x0 = 92, 170, 100
    xs = [x0 + 2 * r * i for i in range(4)]
    for x in xs:
        f.circle(x, y, r, width=4 if top_r else 2.5)
        f.line(x, 20, x, 320, width=2.5, dash="12 8")
    f.line(xs[0], y, xs[-1], y, width=2.5, dash="12 8")
    for x, name in zip(xs, "ABCD"):
        f.dot(x, y, r=7 if not top_r else 0.1)
        f.text(x + 16, y + 42, name, size=32, anchor="start")
    if top_r:
        f.dim(xs[0] + 4, 40, xs[0] + r - 4, 40), f.text(xs[0] + r / 2, 30, "<i>R</i>", size=32, halo=True)
        f.text(14, y - 10, "M", size=32, anchor="start")
    else:
        f.dim(xs[0] + 4, 280, xs[0] + r - 4, 280), f.text(xs[0] + r / 2, 316, "<i>R</i>", size=32)
    return f


def four_spheres_dots():
    """Four identical spheres touching in a row with centres A, B, C, D (marked by dots); dashed axes and centre line; R marked below the first."""
    return four_spheres_row()


def four_spheres_bold():
    """Four identical spheres (mass M) touching in a row with centres A, B, C, D; dashed axes and centre line; R marked above the first."""
    return four_spheres_row(top_r=True)


FIGURES = {
    "PYQ-PHY-794a29bb42f4": three_inductors_pq,
    "PYQ-PHY-21adf19a271b": source_r_c_l_parallel,
    "PYQ-PHY-446d0c007e5e": ac_r_l_c,
    "PYQ-PHY-88bb16277a2d": a_l_r_b,
    "PYQ-PHY-8cce677fd204": current_frequency_options,
    "PYQ-PHY-d6edbfcf1d06": lcr_230v,
    "PYQ-PHY-370a06a8a318": l_and_c_parallel_source,
    "PYQ-PHY-6a0bb0253b49": inductor_resistor_cell,
    "PYQ-PHY-b76874967008": lcr_xl_xc_r,
    "PYQ-PHY-8b3afc1597c1": three_rings_axis,
    "PYQ-PHY-180f80b2623d": three_spheres_dots,
    "PYQ-PHY-d2a425551070": triangle_lamina_axes,
    "PYQ-PHY-a2481d6ae9fa": seven_discs,
    "PYQ-PHY-061690ec45e7": disc_parallel_axis,
    "PYQ-PHY-10570c113970": four_spheres_dots,
    "PYQ-PHY-50bcd78e3fcd": four_spheres_bold,
}
