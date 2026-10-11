"""Physics: current electricity (part 2), dual nature (part 1)."""

import math

from figlib import Figure, along, coil, mid_arrow, slant_resistor


def bridge_with_parallel_arms():
    """Bridge A-B-C-D: AB is 6 ohm parallel 3 ohm, BC is x parallel 1 ohm, AD is 1 ohm + 2 ohm, DC is x."""
    f = Figure(470, 480)
    a, b, c, d = (28, 228), (228, 58), (432, 228), (228, 418)
    for p, q, outer, inner in ((a, b, "6 Ω", "3 Ω"), (b, c, "<i>x</i> Ω", "1 Ω")):
        p1, q1 = along(p, q, 0.16), along(p, q, 0.84)
        f.line(*p, *p1), f.line(*q1, *q)
        for off in (26, -26):
            s, e = along(p, q, 0.16, off), along(p, q, 0.84, off)
            f.line(*p1, *s), f.line(*q1, *e)
            slant_resistor(f, s, e, length=56, peaks=3, height=9)
        ox, oy = along(p, q, 0.5, 56)
        ix, iy = along(p, q, 0.5, -64)
        f.text(ox, oy, outer, size=24), f.text(ix, iy + 8, inner, size=24)
    slant_resistor(f, a, along(a, d, 0.5), length=52, peaks=3, height=9)
    slant_resistor(f, along(a, d, 0.5), d, length=52, peaks=3, height=9)
    slant_resistor(f, d, c, length=60, peaks=3, height=9)
    f.text(60, 302, "1 Ω", size=24), f.text(142, 388, "2 Ω", size=24), f.text(368, 340, "<i>x</i> Ω", size=24)
    for p in (a, b, c, d):
        f.dot(*p, r=7)
    f.text(228, 38, "B", size=28), f.text(228, 462, "D", size=28)
    return f


def bridge_15_3_20_4():
    """Bridge with 15, 3, 20 and 4 ohm arms; 6 ohm and a galvanometer between B and D; 2.1 A enters at A."""
    f = Figure(640, 470)
    a, b, c, d = (165, 235), (295, 62), (428, 235), (295, 408)
    for p, q in ((a, b), (b, c), (a, d), (d, c)):
        slant_resistor(f, p, q, length=62, peaks=3, height=10)
    f.line(295, 62, 295, 100), f.vresistor(295, 100, 160, peaks=3, height=10), f.line(295, 160, 295, 408)
    f.meter(295, 240, "G", r=42)
    mid_arrow(f, 42, 235, *a, at=0.6), f.vector(*c, 548, 235)
    f.text(160, 152, "15 Ω"), f.text(430, 148, "3 Ω"), f.text(170, 348, "20 Ω"), f.text(428, 336, "4 Ω")
    f.text(256, 192, "6 Ω", size=24)
    f.text(140, 216, "A"), f.text(295, 42, "B"), f.text(452, 216, "C"), f.text(295, 448, "D")
    f.text(70, 284, "2.1 A")
    return f


def three_cells_2_ohm():
    """Three cells in series driving a 2 ohm resistor; the current circulates clockwise."""
    f = Figure(640, 430)
    left, right, top, bottom = 65, 548, 100, 340
    f.line(left, top, 245, top), f.resistor(245, 365, top, height=15), f.line(365, top, right, top)
    f.line(left, top, left, bottom), f.line(right, top, right, bottom)
    f.arrowhead(left, 205, 270, size=20), f.arrowhead(right, 235, 90, size=20)
    xs = (190, 285, 380)
    f.line(left, bottom, xs[0] - 10, bottom), f.line(xs[2] + 10, bottom, right, bottom)
    for a, b in zip(xs, xs[1:]):
        f.line(a + 10, bottom, b - 10, bottom)
    for x in xs:
        f.cell(x, bottom, gap=20, long=34, short=18)
    f.text(305, 68, "2 Ω")
    return f


def potentiometer_5v():
    """Potentiometer AB driven by a 5 V battery through 45 ohm and key k; a 0.4 V cell and galvanometer to jockey P."""
    f = Figure(680, 380)
    left, right, top, wire, low = 70, 632, 34, 220, 300
    f.line(left, top, 150, top), f.cell(160, top, gap=20, long=28, short=15), f.line(170, top, 186, top)
    f.cell(196, top, gap=20, long=28, short=15), f.line(206, top, 320, top), f.resistor(320, 400, top)
    f.line(400, top, 478, top), f.line(522, top, right, top)
    f.add('<path d="M486,16 A22,22 0 0 0 486,52 M514,16 A22,22 0 0 1 514,52" stroke-width="3"/>'), f.dot(500, 34, r=3)
    f.line(left, top, left, low), f.line(right, top, right, wire), f.line(left, wire, right, wire, width=5)
    f.line(left, low, 155, low), f.cell(165, low, gap=20, long=28, short=15), f.line(175, low, 250, low)
    f.circle(272, low, 22), f.vector(260, low, 286, low, width=2)
    f.add('<path d="M294,296 C330,290 348,270 348,232" stroke-width="3"/>'), f.arrowhead(348, 222, 270, size=16)
    f.text(178, 88, "5 V", size=26), f.text(360, 82, "45 Ω", size=26), f.text(500, 86, "k", size=26)
    f.text(42, 230, "A", size=28), f.text(660, 228, "B", size=28), f.text(348, 204, "P", size=26)
    f.text(190, 352, "0.4 V", size=26), f.text(318, 330, "C", size=26)
    return f


def meter_bridge_3_x():
    """Meter bridge: 3 ohm and x in the gaps, galvanometer to the jockey at P, AP = 30 cm, 10 V battery."""
    f = Figure(660, 440)
    left, right, top, wire, bottom, mid = 85, 562, 62, 230, 335, 322
    f.line(left, top, 165, top), f.resistor(165, 250, top), f.line(250, top, 395, top), f.resistor(395, 480, top)
    f.line(480, top, right, top), f.line(left, top, left, bottom), f.line(right, top, right, bottom)
    f.line(left, wire, right, wire, width=5)
    f.line(mid, top, mid, 106), f.meter(mid, 130, "G", r=24)
    f.add(f'<path d="M{mid},154 C{mid},196 258,172 258,214" stroke-width="3"/>'), f.arrowhead(258, 226, 90, size=16)
    f.line(left, bottom, mid - 10, bottom), f.line(mid + 10, bottom, right, bottom), f.cell(mid, bottom, gap=20, long=30, short=16)
    f.text(207, 112, "3 Ω"), f.text(437, 112, "<i>x</i>"), f.text(165, 212, "30 cm", size=28)
    f.text(58, 240, "A"), f.text(590, 240, "B"), f.text(258, 264, "P", size=26), f.text(mid, 392, "10 V")
    return f


def bridge_10_10_30_30():
    """Balanced bridge with 10, 10, 30 and 30 ohm arms and a galvanometer B-D, on a 3 V battery."""
    f = Figure(480, 470)
    a, b, c, d = (88, 205), (242, 48), (396, 205), (242, 362)
    for p, q in ((a, b), (b, c), (a, d), (d, c)):
        slant_resistor(f, p, q, length=96, peaks=4, height=13)
    f.line(*b, *d), f.meter(242, 205, "G", r=18)
    f.polyline([c, (446, 205), (446, 418), (152, 418)]), f.polyline([(132, 418), (38, 418), (38, 205), a])
    f.cell(142, 418, gap=20, long=30, short=16)
    f.arrowhead(72, 205, 0), f.arrowhead(436, 205, 0), f.arrowhead(38, 318, 270)
    f.text(128, 110, "10 Ω", size=24), f.text(356, 110, "10 Ω", size=24)
    f.text(130, 312, "30 Ω", size=24), f.text(356, 312, "30 Ω", size=24)
    f.text(76, 190, "A", size=24), f.text(242, 34, "B", size=24), f.text(404, 190, "C", size=24), f.text(242, 396, "D", size=24)
    f.text(18, 326, "<i>I</i>", size=26), f.text(192, 452, "3 V", size=24)
    return f


def capacitor_coil_resistor_ab():
    """Between A and B in series: a 4 F capacitor carrying charge q, a 0.5 H coil and a 2 ohm resistor."""
    f = Figure(660, 170)
    y = 78
    f.line(40, y, 108, y), f.capacitor(115, y, height=28), f.line(122, y, 250, y)
    coil(f, 250, 345, y, turns=4, radius=17), f.line(345, y, 460, y), f.resistor(460, 560, y), f.line(560, y, 612, y)
    f.dot(40, y, r=6), f.dot(612, y, r=6)
    f.text(18, y + 28, "A"), f.text(636, y + 28, "B")
    f.text(90, y - 18, "+", size=28), f.text(142, y - 18, "−", size=28), f.text(115, 30, "<i>q</i>", size=28)
    f.text(115, 150, "4 F"), f.text(298, 140, "0.5 H"), f.text(510, 138, "2 Ω")
    return f


def parallel_then_6_ohm():
    """4 ohm (carrying I1 = 1.2 A) parallel 3 ohm (I2), in series with 6 ohm, a key and a cell; total current I."""
    f = Figure(680, 400)
    left, right, mid, bottom = 34, 640, 152, 350
    mid_arrow(f, left, mid, 128, mid, at=0.75), f.line(128, 84, 128, 220), f.line(455, 84, 455, 220)
    for y in (84, 220):
        f.line(128, y, 252, y), f.resistor(252, 332, y), f.line(332, y, 455, y)
    f.arrowhead(205, 220, 0)
    mid_arrow(f, 455, mid, 520, mid, at=0.75), f.resistor(520, 600, mid), f.line(600, mid, right, mid)
    f.line(right, mid, right, bottom), f.line(left, mid, left, bottom)
    f.line(right, bottom, 424, bottom), f.circle(404, bottom, 20), f.dot(404, bottom, r=6)
    f.line(384, bottom, 230, bottom), f.cell(220, bottom, gap=20, long=30, short=16), f.line(210, bottom, left, bottom)
    f.text(200, 52, "<i>I</i><sub>1</sub> = 1.2 A", size=26)
    f.text(360, 60, "4 Ω", size=26), f.text(292, 262, "3 Ω", size=26), f.text(205, 258, "<i>I</i><sub>2</sub>", size=26)
    f.text(74, 132, "<i>I</i>", size=26), f.text(488, 132, "<i>I</i>", size=26), f.text(560, 118, "6 Ω", size=26)
    return f


def triangle_pqr_9a():
    """9 A enters at P of triangle PQR (3 ohm per side) and leaves at R; I2 flows P to R, I1 flows P to Q to R."""
    f = Figure(680, 460)
    p, r, q = (250, 250), (535, 105), (535, 395)
    mid_arrow(f, 40, 250, 90, 250, at=0.8), f.resistor(90, 165, 250), f.line(165, 250, *p)
    slant_resistor(f, p, r, length=80, peaks=3, height=13), slant_resistor(f, p, q, length=80, peaks=3, height=13, at=0.6)
    f.line(535, 105, 535, 205), f.vresistor(535, 205, 290, peaks=3, height=13), f.line(535, 290, 535, 395)
    f.arrowhead(*along(p, r, 0.24), math.degrees(math.atan2(r[1] - p[1], r[0] - p[0])), size=17)
    f.arrowhead(*along(p, q, 0.3), math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])), size=17)
    f.arrowhead(535, 328, 270, size=17), f.vector(535, 105, 535, 36)
    for pt in (p, r, q):
        f.dot(*pt, r=7)
    f.text(128, 214, "9 A", size=28), f.text(238, 226, "P", size=28), f.text(568, 108, "R", size=28)
    f.text(568, 418, "Q", size=28), f.text(360, 150, "3 Ω", size=28), f.text(382, 392, "3 Ω", size=28)
    f.text(592, 258, "3 Ω", size=28), f.text(300, 186, "<i>I</i><sub>2</sub>", size=28)
    f.text(296, 330, "<i>I</i><sub>1</sub>", size=28), f.text(572, 340, "<i>I</i><sub>1</sub>", size=28)
    return f


def two_cells_abc():
    """Cell E1 between A and B and cell E2 between B and C, connected in opposition."""
    f = Figure(660, 180)
    y = 62
    f.line(20, y, 210, y), f.line(232, y, 430, y), f.line(452, y, 640, y)
    f.cell(221, y, gap=22, long=40, short=22)
    f.line(430, y - 22, 430, y + 22, width=5), f.line(452, y - 40, 452, y + 40, width=3)
    for x, name in ((115, "A"), (330, "B"), (548, "C")):
        f.terminal(x, y), f.text(x, y + 62, name, size=30)
    f.text(221, 150, "<i>E</i><sub>1</sub>", size=30), f.text(441, 150, "<i>E</i><sub>2</sub>", size=30)
    return f


def photoelectric_graph_options():
    """Four options (A)-(D) for the kinetic energy E of photoelectrons against frequency nu."""
    f = Figure(1000, 290)
    for k, name in enumerate("ABCD"):
        ox, oy = 62 + k * 248, 190
        f.axes(ox, oy, 165, 155, xlabel="<i>ν</i>", ylabel="<i>E</i>", origin="0", size=24)
        if name == "A":
            f.line(ox, oy, ox + 125, oy - 125)
        elif name == "B":
            f.line(ox, oy - 55, ox + 110, oy - 135)
        elif name == "C":
            f.line(ox + 45, oy, ox + 150, oy - 120)
        else:
            f.line(ox, oy - 135, ox + 110, oy)
        f.text(ox + 78, 266, f"({name})", size=26)
    return f


def kinetic_energy_intensity_lines():
    """Lines P, Q, R and S on axes of maximum kinetic energy E against intensity I."""
    f = Figure(470, 470)
    ox, oy = 92, 388
    f.line(ox, oy, ox, 60), f.line(40, oy, 390, oy)
    f.line(ox, 312, 372, 312), f.line(ox, 312, 372, 72), f.line(ox, oy, 372, 152), f.line(182, oy, 372, 222)
    f.text(398, 80, "Q"), f.text(398, 162, "R"), f.text(398, 230, "S"), f.text(398, 322, "P")
    f.text(66, 130, "<i>E</i>", size=34), f.text(410, 400, "<i>I</i>", size=34), f.text(66, 425, "<i>O</i>", size=32)
    return f


FIGURES = {
    "PYQ-PHY-60b4a44e51b0": bridge_with_parallel_arms,
    "PYQ-PHY-6408550bd4a0": bridge_15_3_20_4,
    "PYQ-PHY-68544ad2882b": three_cells_2_ohm,
    "PYQ-PHY-7c1df5208232": potentiometer_5v,
    "PYQ-PHY-8e50feb7581a": meter_bridge_3_x,
    "PYQ-PHY-a236c70a32b8": bridge_10_10_30_30,
    "PYQ-PHY-a2a2c1ce1531": capacitor_coil_resistor_ab,
    "PYQ-PHY-baa4b0e075af": parallel_then_6_ohm,
    "PYQ-PHY-c01bb3a1626e": triangle_pqr_9a,
    "PYQ-PHY-e4be5bb7c266": two_cells_abc,
    "PYQ-PHY-499cc044b90b": photoelectric_graph_options,
    "PYQ-PHY-538127d58bf2": kinetic_energy_intensity_lines,
}
