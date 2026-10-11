"""Physics: capacitance (part 2), centre of mass, current electricity (part 1)."""

import math

from figlib import Figure


def mid_arrow(f, x1, y1, x2, y2, at=0.55, size=15):
    """A wire from (x1, y1) to (x2, y2) with an arrowhead part-way along it, pointing towards the end."""
    f.line(x1, y1, x2, y2)
    f.arrowhead(x1 + (x2 - x1) * at, y1 + (y2 - y1) * at, math.degrees(math.atan2(y2 - y1, x2 - x1)), size=size)


def triangle_capacitors():
    """Triangle: 4 uF on each slant side, 2 uF across the middle, and a 2 V cell in the base."""
    f = Figure(440, 470)
    apex, left, right = (220, 40), (25, 380), (415, 380)
    f.line(*left, *apex), f.line(*apex, *right)
    for (px, py), angle in (((137, 185), -60.2), ((303, 185), 60.2)):
        with f.rotated(angle, px, py):
            f.rect(px - 7, py - 6, 14, 12, fill="#fff", width=0), f.capacitor(px, py, height=26)
    f.line(88, 270, 213, 270), f.line(227, 270, 352, 270), f.capacitor(220, 270, height=24)
    f.line(left[0], 380, 211, 380), f.line(229, 380, right[0], 380), f.cell(220, 380, gap=18, long=30, short=16)
    f.text(62, 168, "4 μF", size=28), f.text(380, 168, "4 μF", size=28)
    f.text(220, 330, "2 μF", size=28), f.text(220, 445, "2 V", size=28)
    return f


def two_dielectric_slabs():
    """Capacitor of plate separation d filled with two slabs of equal thickness: K1 = 5 and K2 = 3."""
    f = Figure(640, 450)
    x1, xm, x2, top, bottom = 115, 297, 480, 80, 405
    f.hatch([(x1, top), (xm, top), (xm, bottom), (x1, bottom)], spacing=20)
    for y in range(top + 14, bottom, 14):
        f.line(xm, y, x2, y, width=1.5)
    f.rect(x1, top, x2 - x1, bottom - top), f.line(xm, top, xm, bottom)
    f.line(x1, top, x1, bottom, width=5), f.line(x2, top, x2, bottom, width=5)
    f.line(56, 242, x1, 242), f.line(x2, 242, 540, 242), f.terminal(50, 242), f.terminal(546, 242)
    f.rect(148, 222, 116, 44, fill="#fff", width=0), f.rect(330, 222, 116, 44, fill="#fff", width=0)
    f.text(206, 252, "<i>K</i><sub>1</sub> = 5", size=30, halo=True)
    f.text(388, 252, "<i>K</i><sub>2</sub> = 3", size=30, halo=True)
    f.dim(x1, 56, x2, 56), f.text(297, 46, "<i>d</i>", size=30, halo=True)
    return f


def five_capacitor_network():
    """Five capacitors (3C, 3C, 1C, 2C, 2C) on a supply V."""
    f = Figure(640, 470)
    left, right, top, mid, bottom = 38, 550, 74, 280, 408
    f.line(left, top, 94, top), f.line(108, top, right, top), f.capacitor(101, top, height=28)
    f.line(left, top, left, bottom), f.line(right, mid, right, bottom)
    f.line(right, top, right, 131), f.line(right, 145, right, mid), f.vcapacitor(right, 138, half=30)
    f.line(197, top, 197, 179), f.line(197, 193, 197, mid), f.vcapacitor(197, 186, half=30)
    f.line(378, top, 378, 175), f.line(378, 189, 378, mid), f.vcapacitor(378, 182, half=30)
    f.line(left, mid, 268, mid), f.line(282, mid, right, mid), f.capacitor(275, mid, height=28)
    f.line(left, bottom, 261, bottom), f.line(279, bottom, right, bottom), f.cell(270, bottom, gap=18, long=30, short=16)
    for x, y in ((197, top), (378, top), (left, mid), (197, mid), (378, mid), (right, mid)):
        f.dot(x, y, r=6)
    f.text(150, 50, "3<i>C</i>", size=28), f.text(160, 232, "3<i>C</i>", size=28), f.text(418, 150, "1<i>C</i>", size=28)
    f.text(592, 106, "2<i>C</i>", size=28), f.text(292, 238, "2<i>C</i>", size=28), f.text(312, 388, "<i>V</i>", size=28)
    return f


def c1_c2_parallel_c3_series():
    """C1 and C2 in parallel, in series with C3 and the source V."""
    f = Figure(470, 460)
    left, right, top, mid, bottom = 62, 400, 70, 178, 392
    for y, name in ((top, "1"), (mid, "2")):
        f.line(left, y, 213, y), f.line(227, y, right, y), f.capacitor(220, y, height=30)
        f.text(262, y - 16, f"<i>C</i><sub>{name}</sub>", size=30)
    f.line(left, top, left, bottom), f.line(right, top, right, bottom)
    f.line(left, bottom, 138, bottom), f.line(152, bottom, 281, bottom), f.line(305, bottom, right, bottom)
    f.capacitor(145, bottom, height=30), f.cell(293, bottom, gap=22, long=44, short=24)
    f.text(186, bottom - 16, "<i>C</i><sub>3</sub>", size=30), f.text(330, bottom - 22, "<i>V</i>", size=30)
    return f


def three_blocks():
    """Blocks A, B and C on a horizontal surface; A moves towards B."""
    f = Figure(640, 160)
    f.line(40, 118, 600, 118)
    for x, name in ((95, "A"), (290, "B"), (458, "C")):
        f.add(f'<rect x="{x}" y="46" width="86" height="72" rx="8" stroke-width="3" fill="#fff"/>')
        f.text(x + 43, 94, name, size=32)
    f.vector(196, 82, 266, 82)
    return f


def three_spheres_on_axis():
    """Three identical touching spheres with centres A, B and C on the x-axis; A is at the origin."""
    f = Figure(640, 340)
    ox, oy, r = 215, 200, 41
    f.vector(ox, 320, ox, 28), f.vector(70, oy, 540, oy)
    for k, name in enumerate("ABC"):
        f.circle(ox + 2 * r * k, oy, r), f.dot(ox + 2 * r * k, oy, r=3)
        f.text(ox + 2 * r * k - 12, oy + 26, name, size=22)
    f.text(238, 40, "Y", size=24), f.text(540, 232, "X", size=24)
    return f


def l_shaped_rods():
    """Two uniform rods from the origin: one of length 2L along y and one of length L along x."""
    f = Figure(400, 460)
    ox, oy = 90, 318
    f.vector(ox, oy, ox, 38), f.vector(ox, oy, 330, oy)
    f.line(22, oy, ox, oy, width=2, dash="8 8"), f.line(ox, oy, ox, 400, width=2, dash="8 8")
    f.rect(ox - 6, 96, 12, oy - 96 + 6, fill="#fff"), f.rect(ox - 6, oy - 6, 176, 12, fill="#fff")
    f.text(48, 205, "2<i>L</i>", size=32), f.text(180, 362, "<i>L</i>", size=32), f.text(62, 356, "<i>O</i>", size=30)
    f.text(346, 328, "<i>x</i>", size=30), f.text(112, 50, "<i>y</i>", size=30)
    return f


def ladder_9v():
    """9 V cell feeding a ladder: 3, 2, 2 ohm on top; 8, 8, 4 ohm across; 2, 2, 2 ohm below."""
    f = Figure(680, 300)
    xs, top, bottom = (80, 250, 455, 620), 62, 238
    for (a, b), upper in zip(zip(xs, xs[1:]), ("3 Ω", "2 Ω", "2 Ω")):
        m = (a + b) / 2
        for y in (top, bottom):
            f.line(a, y, m - 38, y), f.resistor(m - 38, m + 38, y, peaks=4, height=11), f.line(m + 38, y, b, y)
        f.text(m, top - 20, upper, size=24), f.text(m, bottom + 38, "2 Ω", size=24)
    for x, label in zip(xs[1:], ("8 Ω", "8 Ω", "4 Ω")):
        f.line(x, top, x, 112), f.vresistor(x, 112, 188, peaks=4, height=11), f.line(x, 188, x, bottom)
        f.text(x + 24, 159, label, size=24, anchor="start")
    f.line(xs[0], top, xs[0], 141), f.line(xs[0], 159, xs[0], bottom), f.vcell(xs[0], 150, gap=18, long=26, short=14)
    f.text(44, 138, "9 V", size=24, anchor="end")
    for x in xs[1:3]:
        f.dot(x, top), f.dot(x, bottom)
    return f


def junction_currents_i():
    """Three junctions in a line: currents 4.5, 1.7 A in and 2.3 A out; 3.2, 4.9 A in and 2.6 A out; 1.9 A and I out."""
    f = Figure(1000, 450)
    j1, j2, j3 = (260, 243), (518, 218), (875, 270)
    f.line(*j1, *j2), f.line(*j2, *j3)
    mid_arrow(f, 170, 125, *j1, at=0.7), mid_arrow(f, 75, 322, *j1, at=0.45), mid_arrow(f, *j1, 195, 435, at=0.65)
    f.vector(*j2, 380, 10), mid_arrow(f, 685, 33, *j2, at=0.65), mid_arrow(f, 430, 438, *j2, at=0.7)
    f.vector(*j3, 992, 182), f.vector(*j3, 975, 365)
    for x, y, label in ((128, 172, "4.5 A"), (52, 300, "1.7 A"), (272, 395, "2.3 A"), (332, 76, "2.6 A"),
                        (580, 78, "3.2 A"), (522, 388, "4.9 A"), (868, 352, "1.9 A")):
        f.text(x, y, label, size=32)
    f.text(952, 170, "<i>I</i>", size=34)
    return f


def resistivity_graph_options():
    """Four options (A)-(D) for resistivity rho against temperature T."""
    f = Figure(1000, 280)
    for k, name in enumerate("ABCD"):
        ox, oy = 62 + k * 248, 180
        f.axes(ox, oy, 160, 150, xlabel="<i>T</i>", ylabel="<i>ρ</i>", origin="<i>O</i>", size=24)
        if name == "A":
            f.line(ox + 12, oy - 12, ox + 125, oy - 125)
        elif name == "B":
            f.polyline([(ox + 14 + 125 * i / 60, oy - 8 - 122 * math.exp(-4 * i / 60)) for i in range(61)])
        elif name == "C":
            f.line(ox + 12, oy - 125, ox + 125, oy - 12)
        else:
            f.polyline([(ox + 14 + 125 * i / 60, oy - 8 - 122 * math.exp(-4 * (1 - i / 60))) for i in range(61)])
        f.text(ox + 75, 256, f"({name})", size=26)
    return f


def junction_currents_small_i():
    """2 A and 3 A enter; 1 A, 0.6 A, 1.3 A and i A leave at the following junctions."""
    f = Figure(660, 300)
    j1, j2, j3 = (118, 122), (340, 122), (452, 154)
    mid_arrow(f, 30, 70, *j1, at=0.6), mid_arrow(f, 50, 190, *j1, at=0.6), mid_arrow(f, *j1, *j2, at=0.55)
    f.line(*j2, *j3)
    f.vector(*j2, 404, 60), f.vector(*j3, 524, 104), f.vector(*j3, 558, 186), f.vector(*j3, 452, 244)
    f.text(62, 62, "2 A", size=26), f.text(92, 204, "3 A", size=26), f.text(360, 62, "1 A", size=26)
    f.text(560, 104, "0.6 A", size=26), f.text(598, 196, "1.3 A", size=26), f.text(478, 256, "<i>i</i> A", size=26)
    return f


def network_six_currents():
    """Rectangle with a diagonal and a semicircular arm, carrying currents I1 to I6."""
    f = Figure(640, 470)
    left, right, top, bottom, r = 60, 410, 125, 365, 120
    f.rect(left, top, right - left, bottom - top), f.line(right, top, left, bottom)
    f.add(f'<path d="M{right},{top} A{r},{r} 0 0 1 {right},{bottom}" stroke-width="3"/>')
    f.arrowhead(250, top, 0, size=20), f.arrowhead(220, bottom, 180, size=20), f.arrowhead(left, 230, 270, size=20)
    f.arrowhead(right, 258, 90, size=20), f.arrowhead(right + r, 258, 90, size=20)
    f.arrowhead(222, 254, math.degrees(math.atan2(bottom - top, left - right)), size=20)
    f.text(238, 92, "<i>I</i><sub>6</sub>", size=34), f.text(215, 420, "<i>I</i><sub>4</sub>", size=34)
    f.text(26, 258, "<i>I</i><sub>5</sub>", size=34), f.text(196, 212, "<i>I</i><sub>3</sub>", size=34)
    f.text(440, 262, "<i>I</i><sub>2</sub>", size=34), f.text(566, 262, "<i>I</i><sub>1</sub>", size=34)
    return f


FIGURES = {
    "PYQ-PHY-4f9116d98335": triangle_capacitors,
    "PYQ-PHY-90379a1d0e02": two_dielectric_slabs,
    "PYQ-PHY-adebaebd0973": five_capacitor_network,
    "PYQ-PHY-e4580a65e954": c1_c2_parallel_c3_series,
    "PYQ-PHY-a7bb0f926fc9": three_blocks,
    "PYQ-PHY-b077f2a4b965": three_spheres_on_axis,
    "PYQ-PHY-ea3b9d8d1a1a": l_shaped_rods,
    "PYQ-PHY-10f4d5a22f51": ladder_9v,
    "PYQ-PHY-3c96093d61ac": junction_currents_i,
    "PYQ-PHY-415ec8bb67c9": resistivity_graph_options,
    "PYQ-PHY-5211f2f9cd22": junction_currents_small_i,
    "PYQ-PHY-5f905bfbdce7": network_six_currents,
}
