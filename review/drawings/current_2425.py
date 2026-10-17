"""Physics (MHT-CET 2024-25): current electricity - circuits, junctions and bridges."""

import math

from figlib import Figure, mid_arrow, slant_resistor


def wire(f, *points):
    f.polyline(list(points))


def right_cell(f, x, y, **kw):
    """A cell on a horizontal wire with its positive (long) plate on the right."""
    with f.rotated(180, x, y):
        f.cell(x, y, **kw)


def vzener(f, x, y1, y2):
    """A Zener diode on a vertical wire from y1 (top) to y2, pointing up."""
    mid = (y1 + y2) / 2
    bar, base = mid - 22, mid + 22
    f.line(x, y1, x, bar), f.line(x, base, x, y2)
    f.path([(x - 24, base), (x + 24, base), (x, bar)], close=True, fill="#fff")
    wire(f, (x - 32, bar + 9), (x - 24, bar), (x + 24, bar), (x + 32, bar - 9))


def labelled_arrow(f, x1, y1, x2, y2, label, dx=0, dy=-14, at=0.6, size=30, anchor="middle"):
    mid_arrow(f, x1, y1, x2, y2, at=at, size=16)
    f.text(x2 + dx, y2 + dy, label, size=size, anchor=anchor)


def two_cells_19_ohm():
    """A loop with a 5 V cell on the top wire and a 100 V cell and 19 ohm on the bottom wire."""
    f = Figure(640, 470)
    l, r, top, bottom = 40, 600, 110, 370
    f.line(l, top, 120, top), f.cell(131, top, gap=22, long=40, short=22), f.line(142, top, r, top)
    f.line(l, top, l, bottom), f.line(r, top, r, bottom)
    f.line(l, bottom, 120, bottom), f.cell(131, bottom, gap=22, long=40, short=22), f.line(142, bottom, 280, bottom)
    f.resistor(280, 480, bottom, peaks=6, height=30), f.line(480, bottom, r, bottom)
    f.text(190, 60, "5 V", size=44), f.text(160, 452, "100 V", size=44), f.text(380, 452, "19 Ω", size=44)
    return f


def a_to_b_2ohm_3v_1ohm():
    """A, 2 ohm (I = 2 A towards B), a 3 V cell (+ on the left), 1 ohm, B."""
    f = Figure(760, 130)
    y = 56
    f.terminal(20, y), f.line(26, y, 150, y), f.arrowhead(90, y, 0, size=16), f.resistor(150, 250, y, peaks=5, height=14)
    f.line(250, y, 362, y), f.cell(373, y, gap=20, long=26, short=14), f.line(384, y, 520, y), f.arrowhead(470, y, 0, size=16)
    f.resistor(520, 620, y, peaks=5, height=14), f.line(620, y, 734, y), f.terminal(740, y)
    f.text(20, 106, "A", size=28), f.text(740, 106, "B", size=28)
    f.text(200, 30, "2 Ω", size=26), f.text(200, 106, "<i>I</i> = 2 A", size=26)
    f.text(356, 28, "+", size=24), f.text(394, 28, "−", size=24), f.text(373, 112, "3 V", size=26)
    f.text(570, 30, "1 Ω", size=26)
    return f


def junction_2a_4a_1a_2a_i():
    """2 A and 4 A meet at a junction; the current goes on to a second junction where 1 A leaves upward, then to a third where 2 A leaves and I leaves downward."""
    f = Figure(760, 380)
    j1, j2, j3 = (180, 230), (430, 150), (560, 120)
    labelled_arrow(f, 10, 140, *j1, "", at=0.55), f.text(40, 130, "2 A", size=36)
    labelled_arrow(f, 30, 360, *j1, "", at=0.55), f.text(150, 350, "4 A", size=36)
    mid_arrow(f, *j1, *j2, at=0.45, size=16), mid_arrow(f, *j2, *j3, at=0.5, size=16)
    labelled_arrow(f, *j2, 470, 30, "1 A", dx=40, dy=10, at=0.95, size=36)
    labelled_arrow(f, *j3, 700, 100, "2 A", dx=30, dy=12, at=0.95, size=36)
    labelled_arrow(f, *j3, 670, 230, "<i>I</i>", dx=20, dy=40, at=0.95, size=36)
    return f


def network_6_4_10_4_6_12v():
    """12 V cell between the left and right rails; 6 ohm from the left rail to node X; 4 ohm from X over the top to the right rail;
    10 ohm from X to node Y; 4 ohm from Y to the right rail; 6 ohm from Y back to the left rail."""
    f = Figure(760, 480)
    l, r, ytop, ymid, ylow, ybot = 20, 740, 60, 170, 280, 400
    x, y = 240, 490
    f.line(l, ymid, l, ybot), f.line(r, ytop, r, ybot)
    f.line(l, ymid, 50, ymid), f.resistor(50, 180, ymid, peaks=6, height=16), f.line(180, ymid, x, ymid)
    wire(f, (x, ymid), (x, ytop), (430, ytop)), f.resistor(430, 560, ytop, peaks=6, height=16), f.line(560, ytop, r, ytop)
    f.line(x, ymid, 300, ymid), f.resistor(300, 430, ymid, peaks=6, height=16), f.line(430, ymid, y, ymid)
    f.line(y, ymid, 560, ymid), f.resistor(560, 690, ymid, peaks=6, height=16), f.line(690, ymid, r, ymid)
    wire(f, (y, ymid), (y, ylow), (330, ylow)), f.resistor(200, 330, ylow, peaks=6, height=16), wire(f, (200, ylow), (l, ylow))
    f.line(l, ybot, 409, ybot), f.cell(420, ybot, gap=22, long=28, short=16), f.line(431, ybot, r, ybot)
    f.dot(x, ymid), f.dot(y, ymid), f.dot(l, ylow), f.dot(r, ymid)
    f.text(115, 136, "6 Ω", size=30), f.text(495, 30, "4 Ω", size=30), f.text(365, 216, "10 Ω", size=30)
    f.text(625, 216, "4 Ω", size=30), f.text(265, 244, "6 Ω", size=30), f.text(420, 468, "12 V", size=30)
    return f


def junction_1a_4a_05a_1a_i():
    """1 A and 4 A enter a junction; 0.5 A leaves upward at a second junction; at a third, 1 A leaves downward and I leaves to the right."""
    f = Figure(760, 380)
    j1, j2, j3 = (150, 175), (360, 155), (570, 180)
    labelled_arrow(f, 30, 60, *j1, "", at=0.55), f.text(130, 110, "1 A", size=36)
    labelled_arrow(f, 20, 290, *j1, "", at=0.55), f.text(90, 286, "4 A", size=36)
    f.line(*j1, *j2), f.line(*j2, *j3)
    labelled_arrow(f, *j2, 440, 50, "0.5 A", dx=-90, dy=24, at=0.95, size=36)
    labelled_arrow(f, *j3, 710, 160, "<i>I</i>", dx=24, dy=14, at=0.95, size=36)
    labelled_arrow(f, *j3, 570, 310, "1 A", dx=0, dy=56, at=0.95, size=36)
    return f


def a_to_b_4ohm_5v_2ohm():
    """A, 4 ohm (I = 3 A towards B), a 5 V cell (+ on the left), 2 ohm, B."""
    f = Figure(760, 130)
    y = 56
    f.dot(40, y, r=7), f.line(40, y, 240, y), f.arrowhead(130, y, 0, size=16), f.resistor(240, 340, y, peaks=5, height=14)
    f.line(340, y, 432, y), f.cell(443, y, gap=20, long=26, short=14), f.line(454, y, 540, y)
    f.resistor(540, 640, y, peaks=5, height=14), f.line(640, y, 720, y), f.dot(720, y, r=7)
    f.text(18, 66, "A", size=28), f.text(744, 66, "B", size=28)
    f.text(290, 30, "4 Ω", size=26), f.text(160, 106, "<i>I</i> = 3 A", size=26)
    f.text(426, 28, "+", size=24), f.text(464, 28, "−", size=24), f.text(443, 112, "5 V", size=26)
    f.text(590, 30, "2 Ω", size=26)
    return f


def zener_divider_20v():
    """20 V battery; R1 = 400 ohm then R2 = 1600 ohm in series; an 8 V Zener across R2. Currents IR1, IR2, Iz marked."""
    f = Figure(760, 420)
    l, x, zx, top, node, bottom = 120, 410, 580, 30, 200, 390
    wire(f, (l, 170), (l, top), (x, top)), f.arrowhead(270, top, 0, size=16)
    f.vcell(l, 180, gap=16, long=28, short=16), f.vcell(l, 210, gap=16, long=28, short=16)
    wire(f, (l, 220), (l, bottom), (zx, bottom))
    f.line(x, top, x, 80), f.arrowhead(x, 60, 90, size=16), f.vresistor(x, 80, 170), f.line(x, 170, x, 260)
    f.arrowhead(x, 225, 90, size=16), f.vresistor(x, 260, 360), f.line(x, 360, x, bottom)
    wire(f, (x, node), (zx, node)), f.arrowhead(500, node, 0, size=16), vzener(f, zx, node, bottom)
    f.text(96, 152, "+", size=26), f.text(96, 250, "−", size=26), f.text(70, 206, "20 V", size=30, anchor="end")
    f.text(430, 54, "<i>I</i><sub>R1</sub>", size=28, anchor="start")
    f.text(380, 130, "<i>R</i><sub>1</sub>", size=28, anchor="end"), f.text(440, 136, "400 Ω", size=28, anchor="start")
    f.text(392, 236, "<i>I</i><sub>R2</sub>", size=28, anchor="end"), f.text(500, 236, "<i>I</i><sub>z</sub>", size=28)
    f.text(380, 318, "<i>R</i><sub>2</sub>", size=28, anchor="end"), f.text(440, 318, "1600 Ω", size=28, anchor="start")
    f.text(620, 312, "<i>V</i><sub>z</sub> = 8 V", size=28, anchor="start")
    return f


def three_cells_i1_i2_i3():
    """Top wire: 28 ohm and 54 ohm meet at a node; a 6 V cell leads down from it (current I3) to the bottom node;
    bottom wire: 8 V cell (I1 towards the node) and 12 V cell (I2 towards the node)."""
    f = Figure(760, 440)
    l, r, m, top, bottom = 30, 730, 390, 50, 360
    f.line(l, top, 160, top), f.resistor(160, 270, top, peaks=5, height=18), f.line(270, top, 510, top)
    f.resistor(510, 620, top, peaks=5, height=18), f.line(620, top, r, top)
    f.line(l, top, l, bottom), f.line(r, top, r, bottom)
    f.line(m, top, m, 186), f.vcell(m, 196, gap=20, long=28, short=14, positive="top"), f.line(m, 206, m, bottom)
    f.arrowhead(m, 280, 90, size=18)
    f.line(l, bottom, 150, bottom), f.cell(161, bottom, gap=22, long=28, short=16), f.line(172, bottom, r, bottom)
    f.cell(550, bottom, gap=22, long=28, short=16), f.arrowhead(300, bottom, 0, size=18), f.arrowhead(480, bottom, 180, size=18)
    f.dot(m, top), f.dot(m, bottom)
    f.text(215, 24, "28 Ω", size=30), f.text(565, 24, "54 Ω", size=30), f.text(420, 206, "6 V", size=30, anchor="start")
    f.text(410, 300, "<i>I</i><sub>3</sub>", size=30, anchor="start"), f.text(161, 426, "8 V", size=30)
    f.text(300, 404, "<i>I</i><sub>1</sub>", size=30), f.text(480, 404, "<i>I</i><sub>2</sub>", size=30), f.text(550, 426, "12 V", size=30)
    return f


def x_and_2ohm_to_b():
    """Current I enters, through x, a junction, then 2 ohm to B; from B 0.5 A, 1 A and 1 A leave."""
    f = Figure(760, 190)
    y, b = 90, (640, 90)
    f.dot(20, y), f.line(20, y, 200, y), f.arrowhead(100, y, 0, size=16), f.resistor(200, 330, y, peaks=7, height=14)
    f.line(330, y, 440, y), f.dot(380, y), f.resistor(440, 570, y, peaks=7, height=14), f.line(570, y, *b)
    f.dot(*b)
    labelled_arrow(f, *b, 720, 10, "0.5 A", dx=-60, dy=6, at=0.6, size=22)
    labelled_arrow(f, *b, 750, 90, "1 A", dx=-20, dy=-10, at=0.6, size=22)
    labelled_arrow(f, *b, 720, 170, "1 A", dx=-60, dy=0, at=0.6, size=22)
    f.text(100, 66, "<i>I</i>", size=26), f.text(265, 56, "<i>x</i>", size=26), f.text(505, 140, "2 Ω", size=24)
    f.text(624, 122, "B", size=24)
    return f


def wheatstone_s1_s2():
    """Wheatstone bridge: P and R on top, Q and S1 below, with S2 in parallel with S1; galvanometer G across; cell E and key K."""
    f = Figure(620, 580)
    top, left, right, bottom = (300, 40), (130, 200), (470, 200), (300, 360)
    slant_resistor(f, left, top, length=90), slant_resistor(f, top, right, length=90)
    slant_resistor(f, left, bottom, length=90), slant_resistor(f, bottom, right, length=90)
    # S2 in parallel with S1, on a branch beside it
    a, b = (365, 295), (405, 135 + 130)
    p1, p2 = (bottom[0] + 40, bottom[1] - 40), (right[0] - 40, right[1] + 40)
    out1, out2 = (p1[0] + 34, p1[1] + 34), (p2[0] + 34, p2[1] + 34)
    f.line(*p1, *out1), f.line(*p2, *out2), slant_resistor(f, out1, out2, length=70)
    f.line(*top, 300, 110), f.meter(300, 140, "G", r=30), f.line(300, 170, *bottom)
    wire(f, left, (30, 200), (30, 500), (200, 500)), f.cell(212, 500, gap=20, long=30, short=16)
    wire(f, (224, 500), (280, 500)), f.circle(310, 500, 28), f.dot(310, 500, r=5), wire(f, (338, 500), (560, 500), (560, 200), right)
    f.text(186, 100, "<i>P</i>", size=32), f.text(410, 100, "<i>R</i>", size=32), f.text(180, 316, "<i>Q</i>", size=32)
    f.text(360, 250, "<i>S</i><sub>1</sub>", size=32), f.text(470, 340, "<i>S</i><sub>2</sub>", size=32)
    f.text(186, 476, "+", size=28), f.text(238, 476, "−", size=28), f.text(212, 566, "E", size=30), f.text(310, 566, "K", size=30)
    return f


def si_diode_200_ohm_ammeter():
    """5 V cell (+ on the left) drives current through a Si diode (pointing right), 200 ohm and an ammeter A."""
    f = Figure(720, 400)
    l, r, top, bottom = 20, 690, 80, 330
    f.line(l, top, 150, top), f.diode(180, top, "right", size=30), f.line(210, top, 450, top)
    f.resistor(450, 560, top, peaks=5, height=18), f.line(560, top, r, top)
    f.line(l, top, l, bottom), f.line(r, top, r, 182), f.meter(r, 210, "A", r=28), f.line(r, 238, r, bottom)
    f.line(l, bottom, 183, bottom), f.cell(194, bottom, gap=22, long=28, short=16), f.line(205, bottom, r, bottom)
    f.text(180, 154, "Si-diode", size=30), f.text(505, 46, "200 Ω", size=30)
    f.text(714, 170, "+", size=26, anchor="end"), f.text(714, 268, "−", size=26, anchor="end")
    f.text(170, 312, "+", size=24), f.text(220, 312, "−", size=24), f.text(194, 392, "5 V", size=30)
    return f


def bridge_abcd_galvanometer():
    """4 A enters at A; 8 ohm A-B, 4 ohm B-C, 10 ohm A-D, 5 ohm D-C; galvanometer G between B and D; current leaves at C."""
    f = Figure(760, 330)
    l, r, top, mid, bottom, m = 130, 640, 50, 160, 270, 380
    f.line(l, top, l, bottom), f.line(r, top, r, bottom)
    f.line(l, top, 200, top), f.resistor(200, 290, top, peaks=4, height=16), f.line(290, top, 480, top)
    f.resistor(480, 570, top, peaks=4, height=16), f.line(570, top, r, top)
    f.line(l, bottom, 200, bottom), f.resistor(200, 290, bottom, peaks=4, height=16), f.line(290, bottom, 480, bottom)
    f.resistor(480, 570, bottom, peaks=4, height=16), f.line(570, bottom, r, bottom)
    f.line(m, top, m, 134), f.meter(m, mid, "G", r=26), f.line(m, 186, m, bottom)
    f.line(20, mid, l, mid, arrow=True), f.line(r, mid, 740, mid, arrow=True)
    f.text(70, 140, "A", size=30), f.text(40, 200, "4 A", size=30), f.text(690, 140, "C", size=30)
    f.text(m, 32, "B", size=30), f.text(m, 316, "D", size=30)
    f.text(245, 98, "8 Ω", size=28), f.text(525, 98, "4 Ω", size=28)
    f.text(245, 316, "10 Ω", size=28), f.text(525, 316, "5 Ω", size=28)
    return f


def a_to_b_2ohm_3v_1ohm_va_vb():
    """A (potential VA), current I = 2 A towards B, 2 ohm, a 3 V cell (+ on the left), 1 ohm, B (potential VB)."""
    f = a_to_b_2ohm_3v_1ohm()
    f.text(44, 34, "<i>V</i><sub>A</sub>", size=24), f.text(712, 34, "<i>V</i><sub>B</sub>", size=24)
    return f


def lcr_ammeter_300v():
    """L (VL = 100 V), a capacitor (VC = 100 V) and R = 50 ohm in series on the top wire; an ammeter A on the left; a 300 V, 50 Hz source below."""
    f = Figure(700, 460)
    l, r, top, bottom = 40, 660, 90, 380
    f.line(l, top, 120, top)
    f.add(" ".join(f'<path d="M{120 + 22 * i},{top} a11,11 0 1 1 22,0" stroke-width="3"/>' for i in range(6)))
    f.line(252, top, 345, top), f.capacitor(352, top, gap=14, height=26), f.line(359, top, 470, top)
    f.resistor(470, 560, top, peaks=5, height=16), f.line(560, top, r, top)
    f.line(l, top, l, 264), f.meter(l, 290, "A", r=26), f.line(l, 316, l, bottom), f.line(r, top, r, bottom)
    f.line(l, bottom, 344, bottom), f.ac_source(370, bottom, r=26), f.line(396, bottom, r, bottom)
    f.text(186, 50, "<i>L</i>", size=32), f.text(515, 50, "<i>R</i> = 50 Ω", size=32)
    f.text(186, 156, "<i>V</i><sub>L</sub> = 100 V", size=30), f.text(400, 156, "<i>V</i><sub>C</sub> = 100 V", size=30)
    f.text(520, 440, "300 V, 50 Hz", size=30)
    return f


def square_loop_currents():
    """A square loop: 20 A enters at the top-left corner, 3 A at the top-right; 5 A leaves at the bottom-left, I at the bottom-right.
    Arrows: right along both horizontal sides, down both vertical sides; 15 A down the left side."""
    f = Figure(640, 480)
    tl, tr, bl, br = (200, 110), (480, 110), (200, 370), (480, 370)
    for a, b in ((tl, tr), (bl, br), (tl, bl), (tr, br)):
        mid_arrow(f, *a, *b, at=0.55, size=18)
    mid_arrow(f, 120, 30, *tl, at=0.7, size=18), mid_arrow(f, 560, 30, *tr, at=0.7, size=18)
    mid_arrow(f, *bl, 120, 450, at=0.85, size=18), mid_arrow(f, *br, 560, 450, at=0.85, size=18)
    f.text(90, 120, "20 A", size=34), f.text(600, 80, "3 A", size=34), f.text(140, 250, "15 A", size=34)
    f.text(200, 456, "5 A", size=34), f.text(540, 380, "<i>I</i>", size=34)
    return f


def bridge_with_switch_s():
    """Bridge: P from A to B, Q from B to C, R from A to D, galvanometer G from D to C; switch S between B and D; cell V between A and C.
    Currents IP, IQ, IR, IG marked."""
    f = Figure(600, 560)
    a, b, c, d = (140, 250), (300, 50), (460, 250), (300, 410)
    slant_resistor(f, a, b, length=110), slant_resistor(f, b, c, length=110), slant_resistor(f, a, d, length=110)
    f.line(*d, 360, 350), f.meter(380, 330, "G", r=28), f.line(400, 310, *c)
    f.line(*b, 300, 190), f.line(300, 190, 340, 290), f.dot(300, 300, r=6), f.line(300, 300, *d)
    for p in (a, b, c, d):
        f.dot(*p, r=5)
    wire(f, a, (60, 300), (60, 500), (288, 500)), f.cell(300, 500, gap=24, long=28, short=16), wire(f, (312, 500), (520, 500), (520, 300), c)
    f.arrowhead(60, 400, -90, size=16), f.arrowhead(520, 400, 90, size=16)
    f.arrowhead(280, 75, -51, size=14), f.arrowhead(324, 80, 51, size=14), f.arrowhead(164, 274, 45, size=14)
    f.arrowhead(352, 354, -45, size=14)
    f.text(300, 36, "B", size=30), f.text(118, 244, "A", size=30), f.text(484, 244, "C", size=30), f.text(300, 450, "D", size=30)
    f.text(176, 128, "<i>P</i>", size=30), f.text(430, 128, "<i>Q</i>", size=30), f.text(170, 370, "<i>R</i>", size=30)
    f.text(252, 84, "<i>I</i><sub>P</sub>", size=26), f.text(352, 84, "<i>I</i><sub>Q</sub>", size=26)
    f.text(150, 300, "<i>I</i><sub>R</sub>", size=26), f.text(360, 410, "<i>I</i><sub>G</sub>", size=26)
    f.text(276, 300, "S", size=28), f.text(300, 552, "<i>V</i>", size=30)
    return f


def six_volt_g_r_4ohm_10v():
    """A 6 V cell in series with a galvanometer G, in parallel with R; then 4 ohm on the top wire to a 10 V cell on the right."""
    f = Figure(700, 340)
    l, m, r, top, bottom = 90, 230, 560, 50, 300
    f.line(l, top, r, top), f.line(l, bottom, r, bottom)
    f.line(l, top, l, 100), f.vcell(l, 110, gap=20, long=34, short=18), f.line(l, 120, l, 196), f.meter(l, 224, "G", r=28)
    f.line(l, 252, l, bottom)
    f.line(m, top, m, 120), f.vresistor(m, 120, 230), f.line(m, 230, m, bottom)
    f.resistor(330, 450, top, peaks=5, height=16)
    f.line(r, top, r, 150), f.vcell(r, 160, gap=20, long=34, short=18), f.line(r, 170, r, bottom)
    f.text(40, 120, "6 V", size=30, anchor="end"), f.text(256, 186, "<i>R</i>", size=30, anchor="start")
    f.text(390, 26, "4 Ω", size=30), f.text(600, 170, "10 V", size=30, anchor="start")
    return f


def loop_10v_200v_38ohm():
    """A loop with a 10 V cell (+ on the left, labelled B) on the top wire, and a 200 V cell (+ on the left) and 38 ohm on the bottom wire."""
    f = Figure(640, 420)
    l, r, top, bottom = 30, 610, 90, 340
    f.line(l, top, 490, top), f.cell(501, top, gap=22, long=30, short=16), f.line(512, top, r, top)
    f.line(l, top, l, bottom), f.line(r, top, r, bottom)
    f.line(l, bottom, 120, bottom), f.cell(131, bottom, gap=22, long=30, short=16), f.line(142, bottom, 470, bottom)
    f.resistor(470, 580, bottom, peaks=5, height=20), f.line(580, bottom, r, bottom)
    f.text(501, 40, "10 V", size=32), f.text(480, 68, "+", size=26), f.text(524, 68, "−", size=26), f.text(501, 148, "B", size=30)
    f.text(110, 316, "+", size=26), f.text(154, 316, "−", size=26), f.text(131, 400, "200 V", size=32), f.text(525, 300, "38 Ω", size=32)
    return f


def two_cells_3ohm_and_6ohm():
    """Two branches, each a 3 V cell and 3 ohm, between two nodes; the nodes are joined round the outside through 6 ohm."""
    f = Figure(620, 440)
    l, r, ol, orr, y1, y2, mid, bottom = 160, 470, 30, 590, 60, 230, 150, 380
    for y in (y1, y2):
        f.line(l, y, 200, y), f.cell(211, y, gap=22, long=30, short=16), f.line(222, y, 300, y)
        f.resistor(300, 410, y, peaks=5, height=18), f.line(410, y, r, y)
        f.text(211, y + 74, "3 V", size=32), f.text(355, y + 66, "3 Ω", size=32)
    f.line(l, y1, l, y2), f.line(r, y1, r, y2)
    wire(f, (l, mid), (ol, mid), (ol, bottom), (240, bottom)), f.resistor(240, 380, bottom, peaks=5, height=20)
    wire(f, (380, bottom), (orr, bottom), (orr, mid), (r, mid))
    f.dot(l, mid), f.dot(r, mid), f.text(310, 432, "6 Ω", size=32)
    return f


def bridge_10_15_20_30_5():
    """Bridge A-B 10 ohm, B-C 15 ohm, A-D 20 ohm, D-C 30 ohm, B-D 5 ohm; cell B (+ on the left) and key k between A and C; current I."""
    f = Figure(640, 500)
    a, b, c, d = (140, 210), (320, 40), (500, 210), (320, 380)
    slant_resistor(f, a, b, length=100), slant_resistor(f, b, c, length=100)
    slant_resistor(f, a, d, length=100), slant_resistor(f, d, c, length=100)
    f.line(*b, 320, 160), f.vresistor(320, 160, 260), f.line(320, 260, *d)
    wire(f, a, (60, 210), (60, 440), (150, 440)), f.cell(162, 440, gap=22, long=28, short=16)
    wire(f, (174, 440), (420, 440)), f.circle(450, 440, 26), f.dot(450, 440, r=5), wire(f, (476, 440), (580, 440), (580, 210), c)
    f.arrowhead(60, 320, -90, size=18), f.arrowhead(580, 320, 90, size=18)
    for p in (a, b, c, d):
        f.dot(*p, r=6)
    f.text(320, 26, "B", size=30), f.text(114, 196, "A", size=30), f.text(526, 196, "C", size=30), f.text(320, 424, "D", size=30)
    f.text(160, 90, "10 Ω", size=30), f.text(480, 90, "15 Ω", size=30), f.text(370, 222, "5 Ω", size=30)
    f.text(160, 340, "20 Ω", size=30), f.text(480, 340, "30 Ω", size=30), f.text(36, 330, "<i>I</i>", size=30)
    f.text(140, 416, "+", size=26), f.text(186, 416, "−", size=26), f.text(162, 492, "B", size=30), f.text(470, 494, "k", size=30)
    return f


def network_abcd_5v():
    """5 ohm A-B, 10 ohm B-C, 20 ohm C-D; 10 ohm from A over the top to C; 10 ohm from B underneath to D; a 5 V cell (+ on the left) between A and D."""
    f = Figure(640, 420)
    a, b, c, d = 90, 230, 400, 560
    y, ytop, ylow, ybot = 150, 50, 240, 370
    f.line(20, y, a, y), f.resistor(110, 200, y, peaks=5, height=14), f.line(a, y, 110, y), f.line(200, y, b, y)
    f.line(b, y, 270, y), f.resistor(270, 360, y, peaks=5, height=14), f.line(360, y, c, y)
    f.line(c, y, 440, y), f.resistor(440, 530, y, peaks=5, height=14), f.line(530, y, 620, y)
    wire(f, (a, y), (a, ytop), (200, ytop)), f.resistor(200, 290, ytop, peaks=5, height=14), wire(f, (290, ytop), (c, ytop), (c, y))
    wire(f, (b, y), (b, ylow), (330, ylow)), f.resistor(330, 420, ylow, peaks=5, height=14), wire(f, (420, ylow), (d, ylow), (d, y))
    wire(f, (20, y), (20, ybot), (309, ybot)), f.cell(320, ybot, gap=22, long=28, short=16), wire(f, (331, ybot), (620, ybot), (620, y))
    for x in (a, b, c, d):
        f.dot(x, y, r=5)
    f.text(20, 128, "A", size=30), f.text(240, 128, "B", size=30), f.text(420, 128, "C", size=30), f.text(600, 128, "D", size=30)
    f.text(155, 196, "5 Ω", size=28), f.text(315, 196, "10 Ω", size=28), f.text(485, 196, "20 Ω", size=28)
    f.text(245, 26, "10 Ω", size=28), f.text(375, 286, "10 Ω", size=28)
    f.text(298, 346, "+", size=26), f.text(342, 346, "−", size=26), f.text(320, 414, "5 V", size=30)
    return f


def opposing_cells_p_q():
    """P to Q: r1 = 1 ohm, a 4 V cell (+ on the left), an 8 V cell (+ on the right), r2 = 2 ohm; R = 9 ohm joins P and Q underneath."""
    f = Figure(760, 260)
    l, r, top, bottom = 30, 730, 60, 200
    f.line(l, top, 60, top), f.resistor(60, 200, top, peaks=6, height=14), f.line(200, top, 329, top)
    f.cell(340, top, gap=22, long=30, short=16), f.line(351, top, 429, top), right_cell(f, 440, top, gap=22, long=30, short=16)
    f.line(451, top, 520, top), f.resistor(520, 660, top, peaks=6, height=14), f.line(660, top, r, top)
    f.line(l, top, l, bottom), f.line(r, top, r, bottom)
    f.line(l, bottom, 150, bottom), f.resistor(150, 380, bottom, peaks=10, height=14), f.line(380, bottom, r, bottom)
    f.text(l, 34, "P", size=30), f.text(r, 34, "Q", size=30)
    f.text(130, 118, "<i>r</i><sub>1</sub> = 1 Ω", size=28), f.text(340, 122, "4 V", size=28), f.text(440, 122, "8 V", size=28)
    f.text(590, 118, "<i>r</i><sub>2</sub> = 2 Ω", size=28), f.text(265, 248, "<i>R</i> = 9 Ω", size=28)
    return f


def five_r_bridge_16v():
    """Five equal resistors R: A-C, C-B, A-D, D-B and C-D; a 16 V cell between A and B underneath."""
    f = Figure(520, 560)
    a, b, c, d = (90, 230), (430, 230), (260, 50), (260, 400)
    for p, q in ((a, c), (c, b), (a, d), (d, b)):
        slant_resistor(f, p, q, length=100)
    f.line(*c, 260, 170), f.vresistor(260, 170, 280), f.line(260, 280, *d)
    wire(f, a, (90, 500), (249, 500)), f.cell(260, 500, gap=22, long=28, short=16), wire(f, (271, 500), (430, 500), b)
    for p in (a, b, c, d):
        f.dot(*p, r=6)
    f.text(260, 34, "C", size=30), f.text(62, 222, "A", size=30), f.text(462, 222, "B", size=30), f.text(260, 446, "D", size=30)
    f.text(130, 110, "<i>R</i>", size=30), f.text(390, 110, "<i>R</i>", size=30), f.text(300, 236, "<i>R</i>", size=30)
    f.text(130, 360, "<i>R</i>", size=30), f.text(390, 360, "<i>R</i>", size=30), f.text(260, 552, "16 V", size=30)
    return f


FIGURES = {
    "PYQ-PHY-f6f8dd52f145": a_to_b_2ohm_3v_1ohm_va_vb,
    "PYQ-PHY-aa4d8311d8ba": lcr_ammeter_300v,
    "PYQ-PHY-893f181fc916": square_loop_currents,
    "PYQ-PHY-02646ebf4154": bridge_with_switch_s,
    "PYQ-PHY-b98d59723336": six_volt_g_r_4ohm_10v,
    "PYQ-PHY-d2e0d0593146": loop_10v_200v_38ohm,
    "PYQ-PHY-06d93a8b57f9": two_cells_3ohm_and_6ohm,
    "PYQ-PHY-db8afb37ee66": bridge_10_15_20_30_5,
    "PYQ-PHY-feaf4a1d12b1": network_abcd_5v,
    "PYQ-PHY-d14eb0757676": opposing_cells_p_q,
    "PYQ-PHY-82fc4338443e": five_r_bridge_16v,
    "PYQ-PHY-59997197a671": two_cells_19_ohm,
    "PYQ-PHY-44a9000771b4": a_to_b_2ohm_3v_1ohm,
    "PYQ-PHY-202579950eef": junction_2a_4a_1a_2a_i,
    "PYQ-PHY-94db2e000079": network_6_4_10_4_6_12v,
    "PYQ-PHY-62057bc1edf3": junction_1a_4a_05a_1a_i,
    "PYQ-PHY-af935db9aa73": a_to_b_4ohm_5v_2ohm,
    "PYQ-PHY-2beac5c04a79": zener_divider_20v,
    "PYQ-PHY-9d11678a0623": three_cells_i1_i2_i3,
    "PYQ-PHY-f3fa36e41bcd": x_and_2ohm_to_b,
    "PYQ-PHY-3dbc47dafdb2": wheatstone_s1_s2,
    "PYQ-PHY-4ec5f3a0e177": si_diode_200_ohm_ammeter,
    "PYQ-PHY-d3055d1bdee4": bridge_abcd_galvanometer,
}
