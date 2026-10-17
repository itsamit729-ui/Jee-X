"""Physics (MHT-CET 2020-23): electrostatics, electromagnetic induction and magnetic effects of current."""

import math

from figlib import Figure, coil, mid_arrow


def ellipse(f, cx, cy, rx, ry, width=3, dash=None):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    f.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" stroke-width="{width}"{extra}/>')


def ellipse_arrow(f, cx, cy, rx, ry, deg, forward=True, size=18):
    """An arrowhead on an ellipse at parameter angle deg (0 = right, 90 = down), pointing along increasing angle when forward."""
    t = math.radians(deg)
    x, y = cx + rx * math.cos(t), cy + ry * math.sin(t)
    dx, dy = -rx * math.sin(t), ry * math.cos(t)
    ang = math.degrees(math.atan2(dy, dx)) + (0 if forward else 180)
    f.arrowhead(x, y, ang, size=size)


def shell_with_charge():
    """A spherical shell of inner radius r1 and outer radius r2 carrying charge Q, with -q at the centre."""
    f = Figure(440, 440)
    c = (220, 230)
    f.circle(*c, 190, width=4), f.circle(*c, 120, width=4)
    f.line(*c, c[0] + 120 * math.cos(math.radians(-62)), c[1] + 120 * math.sin(math.radians(-62)), width=3)
    f.line(*c, c[0] + 190 * math.cos(math.radians(-28)), c[1] + 190 * math.sin(math.radians(-28)), width=3)
    f.text(c[0], c[1] + 40, "−<i>q</i>", size=32), f.text(c[0] + 12, c[1] - 92, "<i>r</i><sub>1</sub>", size=30)
    f.text(c[0] + 112, c[1] - 92, "<i>r</i><sub>2</sub>", size=30), f.text(c[0] + 40, 26, "<i>Q</i>", size=32)
    return f


def points_in_field():
    """Three field lines of a uniform field E pointing right; point A near the top right, B at the left, C lower down in the middle."""
    f = Figure(640, 340)
    for y in (40, 170, 300):
        f.line(20, y, 500, y, width=4, arrow=True)
    f.line(540, 140, 620, 140, width=3, arrow=True), f.text(580, 200, "<i>E</i>", size=44)
    f.dot(390, 95, r=9), f.text(420, 112, "A", size=44, anchor="start")
    f.dot(40, 115, r=9), f.text(66, 132, "B", size=44, anchor="start")
    f.dot(190, 240, r=9), f.text(216, 257, "C", size=44, anchor="start")
    return f


def pendulum_in_capacitor():
    """A pendulum bob hangs between horizontal capacitor plates: the upper plate is negative (dashes), the lower positive (+); the field E points up."""
    f = Figure(460, 420)
    f.line(20, 30, 350, 30, width=3), f.line(20, 390, 350, 390, width=3)
    for x in range(30, 340, 34):
        f.line(x, 60, x + 18, 60, width=3)
        f.text(x + 9, 368, "+", size=30)
    f.line(170, 30, 170, 230, width=2.5), ellipse(f, 170, 245, 28, 16, width=2.5)
    f.add('<path d="M60,215 Q170,290 280,215" stroke-width="2" stroke-dasharray="10 8"/>')
    f.line(390, 380, 390, 60, width=2.5, arrow=True), f.text(404, 110, "<i>E</i>", size=30, anchor="start")
    f.line(404, 78, 424, 78, width=1.5, arrow=True)
    return f


def right_isosceles_charges():
    """A right isosceles triangle with legs a: +Q at the right angle, +2q at the top and +q at the right."""
    f = Figure(460, 440)
    q, top, right = (90, 360), (90, 60), (390, 360)
    f.path([q, top, right], close=True, width=2.5), f.right_angle(q[0], q[1], 1, -1, size=24)
    f.dim(40, 70, 40, 350), f.dim(100, 410, 380, 410)
    f.text(90, 44, "+2<i>q</i>", size=32), f.text(70, 380, "+<i>Q</i>", size=32, anchor="end"), f.text(410, 380, "+<i>q</i>", size=32, anchor="start")
    f.text(28, 214, "<i>a</i>", size=30, anchor="end"), f.text(240, 400, "<i>a</i>", size=30, halo=True)
    return f


def charge_moves_on_arc_30():
    """+Q at the origin; A at distance r on the horizontal; B at distance r, 30 degrees above it; q moves from A to B along the arc."""
    f = Figure(460, 420)
    o, r = (60, 330), 330
    a = (o[0] + r, o[1])
    b = (o[0] + r * math.cos(math.radians(-50)), o[1] + r * math.sin(math.radians(-50)))
    f.line(*o, *a, width=2.5), f.line(*o, *b, width=2, dash="8 6")
    f.arc(o[0], o[1], r, 12, -58, width=2.5), f.arrowhead(o[0] + r * math.cos(math.radians(-25)), o[1] + r * math.sin(math.radians(-25)), -115, size=16)
    f.arc(o[0], o[1], 70, 0, -50, width=1.5)
    f.dot(*o, r=7), f.dot(*a, r=7), f.dot(*b, r=7)
    f.text(o[0] - 10, o[1] + 10, "+<i>Q</i>", size=30, anchor="end"), f.text(a[0] + 14, a[1] + 10, "A", size=30, anchor="start")
    f.text(b[0] + 14, b[1], "B", size=30, anchor="start"), f.text(140, 310, "30°", size=28)
    f.text(220, 370, "<i>r</i>", size=28), f.text(190, 210, "<i>r</i>", size=28)
    return f


def sliding_arm_loop():
    """A rectangular loop NPQM in a magnetic field into the page (crosses); arm PQ slides to the right with velocity v."""
    f = Figure(640, 420)
    for y in (30, 100, 170, 240, 310, 380):
        for x in range(30, 620, 90):
            f.text(x, y + 10, "×", size=28)
    n, p, q, m = (90, 70), (440, 70), (440, 340), (90, 340)
    f.line(*m, *n, width=3), f.line(*n, 580, 70, width=3), f.line(*m, 580, 340, width=3), f.line(*p, *q, width=4)
    f.line(440, 200, 600, 200, width=3, arrow=True), f.text(610, 210, "<i>v</i>", size=30, anchor="start")
    f.text(70, 56, "N", size=30), f.text(460, 56, "P", size=30), f.text(70, 380, "M", size=30), f.text(460, 380, "Q", size=30)
    return f


def flux_lines(labels, ylabel, origin):
    f = Figure(520, 420)
    ox, oy = 70, 370
    f.axes(ox, oy, 420, 340, xlabel="<i>I</i>", ylabel=ylabel, origin=origin, size=34)
    for name, k in zip(labels, (2.4, 1.3, 0.85, 0.5)):
        dx = 330 / (1 + k * k) ** 0.5
        f.line(ox, oy, ox + dx, oy - dx * k), f.text(ox + dx + 18, oy - dx * k, name, size=34)
    return f


def flux_current_abcd_o():
    """Flux against current: lines from O for inductors A (steepest), B, C and D (least steep)."""
    return flux_lines("ABCD", "<i>φ</i>", "O")


def flux_current_abcd_0():
    """Flux against current: lines from the origin for inductors A (steepest), B, C and D (least steep)."""
    return flux_lines("ABCD", "<i>φ</i>", "0")


def four_inductor_combinations():
    """(P) L1, L2, L3 in series; (Q) L1, L2, L3 in parallel; (R) L1 and L2 on two sides of a triangle with L3 on the base;
    (S) L1 on top, L2 down the right side and L3 along the bottom, in series."""
    f = Figure(760, 510)
    y = 80
    f.line(10, y, 40, y)
    for i, x in enumerate((40, 150, 260)):
        coil(f, x, x + 80, y, turns=4, radius=11), f.line(x + 80, y, x + 110, y)
        f.text(x + 40, y + 40, f"<i>L</i><sub>{i + 1}</sub>", size=22)
    f.text(190, 160, "(P)", size=26)
    l, r = 480, 700
    f.line(l, 30, l, 170), f.line(r, 30, r, 170), f.line(440, 100, l, 100), f.line(r, 100, 740, 100)
    for i, yy in enumerate((30, 100, 170)):
        f.line(l, yy, 550, yy), coil(f, 550, 630, yy, turns=4, radius=11), f.line(630, yy, r, yy)
        f.text(590, yy + 34, f"<i>L</i><sub>{i + 1}</sub>", size=22)
    f.text(590, 236, "(Q)", size=26)
    a, b, c = (60, 400), (200, 260), (340, 400)
    for (p, q) in ((a, b), (b, c)):
        ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        f.line(*p, mx - 45 * math.cos(math.radians(ang)), my - 45 * math.sin(math.radians(ang)))
        f.line(mx + 45 * math.cos(math.radians(ang)), my + 45 * math.sin(math.radians(ang)), *q)
        with f.rotated(round(ang, 1), mx, my):
            coil(f, mx - 45, mx + 45, my, turns=4, radius=11)
    f.line(20, 400, 140, 400), coil(f, 140, 260, 400, turns=5, radius=11), f.line(260, 400, 380, 400)
    f.text(130, 300, "<i>L</i><sub>1</sub>", size=22, anchor="end"), f.text(270, 300, "<i>L</i><sub>2</sub>", size=22, anchor="start")
    f.text(200, 444, "<i>L</i><sub>3</sub>", size=22), f.text(200, 494, "(R)", size=26)
    l, r, t, b = 470, 700, 300, 420
    f.line(440, t, 520, t), coil(f, 520, 620, t, turns=4, radius=11), f.line(620, t, r, t)
    f.line(r, t, r, 330)
    with f.rotated(90, r, 360):
        coil(f, r - 30, r + 30, 360, turns=3, radius=11)
    f.line(r, 390, r, b), f.line(440, b, 520, b), coil(f, 520, 620, b, turns=4, radius=11), f.line(620, b, r, b)
    f.text(570, t + 36, "<i>L</i><sub>1</sub>", size=22), f.text(r + 22, 368, "<i>L</i><sub>2</sub>", size=22, anchor="start")
    f.text(570, b + 36, "<i>L</i><sub>3</sub>", size=22), f.text(570, 494, "(S)", size=26)
    return f


def coil_and_magnet_ns():
    """A coil seen edge-on (an upright ellipse) labelled Coil, and a bar magnet with N facing the coil."""
    f = Figure(640, 280)
    ellipse(f, 150, 130, 50, 120, width=5)
    f.rect(330, 90, 290, 80, width=4), f.text(370, 146, "N", size=46), f.text(590, 146, "S", size=46)
    f.text(20, 270, "Coil", size=46, anchor="start")
    return f


def amperian_loop_three_wires():
    """An Amperian loop (ellipse) encloses a wire carrying 5 A upward and one carrying 2 A downward; a third wire with 3 A upward lies outside."""
    f = Figure(520, 320)
    ellipse(f, 170, 160, 160, 70, width=3)
    for x, up, lab in ((80, True, "5 A"), (250, False, "2 A")):
        f.line(x, 20, x, 105, width=2.5), f.line(x, 215, x, 300, width=2.5), f.line(x, 105, x, 215, width=2.5, dash="8 6")
        f.arrowhead(x, 40 if up else 50, -90 if up else 90, size=16), f.arrowhead(x, 270 if up else 280, -90 if up else 90, size=16)
        f.text(x - 14 if up else x + 14, 50, lab, size=30, anchor="end" if up else "start")
    f.line(420, 300, 420, 20, width=2.5), f.arrowhead(420, 70, -90, size=16), f.text(436, 76, "3 A", size=30, anchor="start")
    return f


def three_parallel_wires():
    """Parallel wires A, B, C, spaced d apart, carrying I (up), I (up) and 2I (down)."""
    f = Figure(420, 400)
    for x, name, lab, up in ((60, "A", "<i>I</i>", True), (200, "B", "<i>I</i>", True), (340, "C", "2<i>I</i>", False)):
        f.line(x, 50, x, 380, width=2.5), f.arrowhead(x, 200, -90 if up else 90, size=16)
        f.text(x, 36, name, size=30), f.text(x - 14, 210, lab, size=28, anchor="end")
    f.dim(64, 350, 196, 350), f.dim(204, 350, 336, 350)
    f.text(130, 340, "<i>d</i>", size=28, halo=True), f.text(270, 340, "<i>d</i>", size=28, halo=True)
    return f


def two_perpendicular_loops():
    """Two equal loops with a common centre O in perpendicular planes: the vertical one carries I, the horizontal one 2I."""
    f = Figure(460, 440)
    c = (230, 220)
    ellipse(f, *c, 80, 190, width=3), ellipse(f, *c, 210, 80, width=3)
    for deg, fwd in ((235, False), (300, True), (125, True), (60, False)):
        ellipse_arrow(f, *c, 80, 190, deg, fwd)
    for deg, fwd in ((150, True), (210, True), (330, False), (30, False)):
        ellipse_arrow(f, *c, 210, 80, deg, fwd)
    f.dot(c[0] + 26, c[1], r=8), f.text(c[0] - 6, c[1] + 12, "O", size=34, anchor="end")
    f.text(320, 60, "<i>I</i>", size=34), f.text(40, 350, "2<i>I</i>", size=34)
    return f


def semicircle_with_dip():
    """Current I flows round a large semicircle of radius R1 above O and a small semicircle of radius R2 below O, joined by straight pieces."""
    f = Figure(560, 380)
    o, r1, r2, y = (280, 260), 240, 90, 260
    f.add(f'<path d="M{o[0] - r1},{y} A{r1},{r1} 0 0 1 {o[0] + r1},{y}" stroke-width="3"/>')
    f.line(o[0] + r1, y, o[0] + r2, y), f.line(o[0] - r2, y, o[0] - r1, y)
    f.add(f'<path d="M{o[0] + r2},{y} A{r2},{r2} 0 0 1 {o[0] - r2},{y}" stroke-width="3"/>')
    f.arrowhead(o[0] - 70, o[1] - r1 + 10, 10, size=18)
    f.arrowhead(o[0] + 200, y, 0, size=18), f.arrowhead(o[0] - 180, y, 180, size=18)
    f.arrowhead(o[0] - r2 * math.cos(math.radians(40)), y + r2 * math.sin(math.radians(40)), 220, size=16)
    f.line(*o, o[0] + r1 * math.cos(math.radians(-62)), o[1] + r1 * math.sin(math.radians(-62)), width=2, dash="8 6", arrow=True)
    f.line(*o, o[0] + 10, y + r2 - 2, width=2, dash="8 6", arrow=True)
    f.text(o[0] - 10, y - 6, "O", size=32, anchor="end"), f.text(380, 140, "<i>R</i><sub>1</sub>", size=32, anchor="start")
    f.text(o[0] + 18, y + 40, "<i>R</i><sub>2</sub>", size=30, anchor="start")
    f.text(o[0] - 70, 50, "<i>I</i>", size=30), f.text(o[0] - 200, y + 40, "<i>I</i>", size=30), f.text(o[0] + 200, y + 40, "<i>I</i>", size=30)
    return f


def wire_above_long_wire():
    """Wire PQ carries I to the right a height h above a long wire on the table carrying I to the left."""
    f = Figure(640, 340)
    f.line(60, 60, 580, 60, width=3), f.arrowhead(430, 60, 0, size=20)
    f.line(40, 250, 600, 250, width=3), f.arrowhead(520, 250, 180, size=20)
    f.dim(200, 66, 200, 244), f.add('<rect x="186" y="130" width="28" height="50" fill="#fff" stroke="none"/>')
    f.text(200, 166, "<i>h</i>", size=34)
    f.text(30, 72, "P", size=40), f.text(610, 72, "Q", size=40, anchor="start")
    f.text(470, 40, "<i>I</i>", size=36), f.text(520, 230, "<i>I</i>", size=36), f.text(320, 306, "Long wire", size=40)
    return f


FIGURES = {
    "PYQ-PHY-21fcae785856": shell_with_charge,
    "PYQ-PHY-0edaece0567f": points_in_field,
    "PYQ-PHY-bad5f1a7983b": pendulum_in_capacitor,
    "PYQ-PHY-eb01983f5549": right_isosceles_charges,
    "PYQ-PHY-c965408e2829": charge_moves_on_arc_30,
    "PYQ-PHY-bf5cd0119716": sliding_arm_loop,
    "PYQ-PHY-4b765b092171": flux_current_abcd_o,
    "PYQ-PHY-16bb69aa2635": flux_current_abcd_0,
    "PYQ-PHY-92648409cd61": four_inductor_combinations,
    "PYQ-PHY-bcbcac7792a0": coil_and_magnet_ns,
    "PYQ-PHY-09af0a61989e": amperian_loop_three_wires,
    "PYQ-PHY-0b6db60fefef": three_parallel_wires,
    "PYQ-PHY-44efdda81610": two_perpendicular_loops,
    "PYQ-PHY-849b8141f294": semicircle_with_dip,
    "PYQ-PHY-50ce8e051303": wire_above_long_wire,
}
