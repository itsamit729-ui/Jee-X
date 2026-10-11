"""Physics: electromagnetic induction (last), electrostatics, fluid mechanics."""

import math

from figlib import Figure, coil, mid_arrow


def charge(f, x, y, sign, r=18):
    """A point charge drawn as a circle with its sign."""
    f.circle(x, y, r, fill="#fff")
    f.line(x - 9, y, x + 9, y)
    if sign == "+":
        f.line(x, y - 9, x, y + 9)


def two_inductors_parallel():
    """Current I divides into I1 through L1 and I2 through L2, which are in parallel."""
    f = Figure(640, 340)
    left, right, top, mid, bottom = 148, 486, 86, 175, 262
    mid_arrow(f, 30, mid, left, mid, at=0.6), mid_arrow(f, right, mid, 612, mid, at=0.65)
    f.line(left, top, left, bottom), f.line(right, top, right, bottom)
    for y in (top, bottom):
        f.line(left, y, 270, y), coil(f, 270, 378, y, turns=5, radius=16), f.line(378, y, right, y)
        f.arrowhead(222, y, 0)
    f.text(76, 152, "<i>I</i>", size=28), f.text(552, 152, "<i>I</i>", size=28)
    f.text(190, 124, "<i>I</i><sub>1</sub>", size=28), f.text(190, 240, "<i>I</i><sub>2</sub>", size=28)
    f.text(324, 52, "<i>L</i><sub>1</sub>", size=28), f.text(324, 312, "<i>L</i><sub>2</sub>", size=28)
    return f


def hexagon_charges():
    """Regular hexagon ABCDEF with centre O: +q at A, -q at B, -q at C, +q at D, Q at E and -q at F."""
    f = Figure(470, 470)
    cx, cy, r = 228, 238, 120
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in (-90, -30, 30, 90, 150, 210)]
    f.path(pts, close=True)
    for i in range(3):
        f.line(*pts[i], *pts[i + 3], width=2, dash="9 8")
    labels = (("A", 0, -18, "+<i>q</i>", 46, -34), ("F", 26, 2, "−<i>q</i>", 64, -18), ("E", 26, 26, "<i>Q</i>", 52, 46),
              ("D", 0, 40, "+<i>q</i>", 30, 74), ("C", -26, 22, "−<i>q</i>", -56, 42), ("B", -26, 2, "−<i>q</i>", -52, -30))
    for (x, y), (name, dx, dy, q, qx, qy) in zip(pts, labels):
        f.text(x + dx, y + dy, name, size=28), f.text(x + qx, y + qy, q, size=28)
    f.text(cx + 20, cy + 42, "O", size=26, halo=True)
    return f


def two_charges_on_axis():
    """q1 (positive) at the origin and q2 (negative) at x = L on the x-axis."""
    f = Figure(640, 380)
    f.line(208, 345, 208, 42), f.line(22, 214, 596, 214)
    charge(f, 208, 214, "+"), charge(f, 520, 214, "-")
    f.dim(208, 284, 520, 284), f.rect(340, 266, 48, 36, fill="#fff", width=0), f.text(364, 294, "<i>L</i>", size=30)
    f.text(165, 184, "<i>q</i><sub>1</sub>", size=28), f.text(522, 180, "<i>q</i><sub>2</sub>", size=28)
    f.text(612, 224, "<i>x</i>", size=28), f.text(208, 34, "<i>y</i>", size=28)
    return f


def field_distance_graph_options():
    """Four options (A)-(D) for electric field E against distance d."""
    f = Figure(1000, 260)
    for k, name in enumerate("ABCD"):
        ox, oy = 60 + k * 248, 168
        f.axes(ox, oy, 165, 140, xlabel="<i>d</i>", ylabel="<i>E</i>", origin="<i>O</i>", size=24)
        if name == "A":
            f.line(ox, oy, ox + 125, oy - 112)
        elif name == "B":
            f.line(ox, oy - 112, ox + 112, oy)
        elif name == "C":
            f.line(ox, oy - 92, ox + 135, oy - 92)
        else:
            f.line(ox + 88, oy, ox + 88, oy - 122)
        f.text(ox + 75, 240, f"({name})", size=26)
    return f


def right_triangle_charges():
    """Right-angled isosceles triangle with legs root 2 a: Q at the right angle, 2q at the top and q at the right."""
    f = Figure(470, 470)
    q, top, right = (112, 390), (112, 82), (420, 390)
    f.path([q, top, right], close=True), f.right_angle(112, 390, 1, -1, size=34)
    f.text(112, 62, "2<i>q</i>", size=30), f.text(82, 412, "<i>Q</i>", size=30), f.text(444, 402, "<i>q</i>", size=30)
    f.text(64, 248, "√2 <i>a</i>", size=28), f.text(266, 432, "√2 <i>a</i>", size=28)
    return f


def square_with_centre_charge():
    """Square ABCD with 10 uC at its centre; a 2 uC charge is at corner A."""
    f = Figure(470, 460)
    f.rect(128, 100, 246, 246), f.dot(251, 226, r=5)
    f.text(112, 92, "A", size=28), f.text(392, 92, "B", size=28), f.text(392, 372, "C", size=28), f.text(112, 372, "D", size=28)
    f.text(64, 152, "2 μC", size=28), f.text(251, 206, "10 μC", size=28)
    return f


def potential_regions():
    """Potential V along x: constant from A to B, rising to C, constant to D, then falling to E; regions 1 to 4."""
    f = Figure(540, 460)
    ox, oy = 54, 416
    f.vector(ox, oy, ox, 58), f.vector(ox, oy, 492, oy)
    a, b, c, d, e = (54, 252), (124, 252), (194, 150), (330, 150), (394, 416)
    f.polyline([a, b, c, d, e])
    for (x, y) in (b, c, d):
        f.line(x, y, x, oy + 10, width=2, dash="9 8")
    for pt in (a, b, c, d, e):
        f.dot(*pt, r=6)
    f.line(262, oy - 7, 262, oy + 7, width=2)
    for x, n in ((90, 1), (159, 2), (228, 3), (358, 4)):
        f.text(x, 398, str(n), size=28)
    f.text(30, 262, "A", size=28), f.text(108, 236, "B", size=28), f.text(182, 134, "C", size=28)
    f.text(332, 134, "D", size=28), f.text(412, 404, "E", size=28)
    f.text(54, 44, "<i>V</i>", size=30), f.text(508, 426, "<i>x</i>", size=30)
    return f


def charge_moved_on_arc():
    """q1 at A and q2 at B, 30 cm apart; q3 moves from C, 40 cm above A, along a circle of centre A to D on line AB."""
    f = Figure(560, 460)
    a, b, d, c = (120, 388), (380, 388), (467, 388), (120, 41)
    f.line(*c, *a), f.line(*a, *d)
    f.add(f'<path d="M{c[0]},{c[1]} A347,347 0 0 1 {d[0]},{d[1]}" stroke-width="2" stroke-dasharray="9 8"/>')
    for pt in (a, b, d, c):
        f.dot(*pt, r=8)
    f.text(92, 50, "C", size=30), f.text(120, 432, "A", size=30), f.text(380, 432, "B", size=30), f.text(467, 432, "D", size=30)
    f.text(152, 78, "<i>q</i><sub>3</sub>", size=28), f.text(150, 364, "<i>q</i><sub>1</sub>", size=28)
    f.text(380, 364, "<i>q</i><sub>2</sub>", size=28)
    f.text(58, 222, "40 cm", size=28), f.text(250, 438, "30 cm", size=28)
    return f


def hemispheres_pressed():
    """A spherical shell made of two hemispheres held together by forces F from each side."""
    f = Figure(640, 340)
    f.circle(320, 170, 136, width=5), f.line(320, 34, 320, 306, width=4, dash="22 14")
    f.line(40, 170, 180, 170, width=5, arrow=True), f.line(600, 170, 460, 170, width=5, arrow=True)
    f.text(92, 130, "<i>F</i>", size=38), f.text(548, 130, "<i>F</i>", size=38)
    return f


def widening_tube():
    """A tube that widens from end P (area AP) to end Q (area AQ); the fluid flows from P to Q."""
    f = Figure(600, 450)
    f.add('<path d="M76,324 C200,250 300,100 468,95" stroke-width="3"/>')
    f.add('<path d="M78,396 C240,300 320,246 468,236" stroke-width="3"/>')
    f.add('<ellipse cx="76" cy="360" rx="9" ry="36" stroke-width="3"/>')
    f.add('<ellipse cx="468" cy="165" rx="20" ry="70" stroke-width="3" fill="#fff"/>')
    f.vector(470, 165, 534, 165)
    f.text(558, 176, "Q", size=30), f.text(46, 420, "P", size=30)
    f.text(498, 78, "<i>A</i><sub>Q</sub>", size=30), f.text(42, 310, "<i>A</i><sub>P</sub>", size=30)
    return f


def sphere_in_oil_and_mercury():
    """A sphere floating half in oil (above) and half in mercury (below) in a vessel."""
    f = Figure(640, 460)
    f.add('<ellipse cx="240" cy="46" rx="208" ry="15" stroke-width="3"/>')
    f.add('<path d="M40,58 C58,70 58,80 58,96 L58,366 Q58,392 86,392 L394,392 Q422,392 422,366 L422,96 '
          'C422,80 422,70 440,58" stroke-width="3"/>')
    f.line(58, 132, 422, 132)
    for y in range(146, 232, 15):
        f.line(66, y, 414, y, width=1.5, dash="16 9")
    f.line(58, 238, 422, 238, width=2)
    for y in range(250, 384, 11):
        f.line(66, y, 414, y, width=1.5, dash="7 5")
    f.circle(240, 238, 76, fill="#fff")
    f.line(414, 178, 468, 142, width=2), f.text(480, 144, "Oil", size=30, anchor="start")
    f.line(390, 350, 452, 408, width=2), f.text(462, 424, "Mercury", size=30, anchor="start")
    return f


def velocity_time_graph_options():
    """Four options (a)-(d) for velocity v against time t."""
    f = Figure(640, 410)
    panels = (("a", 130, 150), ("b", 400, 150), ("c", 130, 318), ("d", 400, 318))
    for name, ox, oy in panels:
        f.axes(ox, oy, 128, 108, xlabel="<i>t</i>", ylabel="<i>v</i>", origin="0", size=22)
        if name == "a":
            f.line(ox, oy - 66, ox + 105, oy - 66)
        elif name == "b":
            f.line(ox, oy - 32, ox + 92, oy - 96)
        elif name == "c":
            f.polyline([(ox + 6 + 100 * i / 50, oy - 6 - 90 * math.exp(-5 * i / 50)) for i in range(51)])
        else:
            f.polyline([(ox + 100 * i / 50, oy - 62 * (1 - math.exp(-4 * i / 50))) for i in range(51)])
        f.text(ox + 52, oy + 44, f"({name})", size=22)
    return f


FIGURES = {
    "PYQ-PHY-e6b17fa0158d": two_inductors_parallel,
    "PYQ-PHY-01080c60d7d7": hexagon_charges,
    "PYQ-PHY-14c20716a041": two_charges_on_axis,
    "PYQ-PHY-4bf0558fb045": field_distance_graph_options,
    "PYQ-PHY-4eb071ffc0de": right_triangle_charges,
    "PYQ-PHY-7b2888169c04": square_with_centre_charge,
    "PYQ-PHY-93879d43a542": potential_regions,
    "PYQ-PHY-942d95c0ffd2": charge_moved_on_arc,
    "PYQ-PHY-c5ff64bf943d": hemispheres_pressed,
    "PYQ-PHY-68041bd8ad9e": widening_tube,
    "PYQ-PHY-737d7a05d55f": sphere_in_oil_and_mercury,
    "PYQ-PHY-ccbc6f9df034": velocity_time_graph_options,
}
