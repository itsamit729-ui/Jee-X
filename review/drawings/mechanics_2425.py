"""Physics (MHT-CET 2024-25): rotational motion, kinematics and laws of motion."""

import math

from figlib import Figure


def ceiling(f, x1, x2, y):
    f.line(x1, y, x2, y, width=3)
    for x in range(int(x1) + 6, int(x2), 16):
        f.line(x, y, x + 12, y - 14, width=2)


def disc_points():
    """A uniform disc with centre A, B on the rim, C above the centre and D to the right of it; dashed diameters."""
    f = Figure(460, 440)
    c, r = (240, 220), 190
    f.circle(*c, r)
    f.line(c[0] - r, c[1], c[0] + r, c[1], width=2, dash="10 6"), f.line(c[0], c[1] - r, c[0], c[1] + r, width=2, dash="10 6")
    for p in ((c[0], c[1]), (c[0] - r, c[1]), (c[0], c[1] - 150), (c[0] + 60, c[1])):
        f.dot(*p, r=10)
    f.text(c[0] - 30, c[1] + 50, "A", size=40), f.text(c[0] - r - 26, c[1] + 14, "B", size=40)
    f.text(c[0] + 40, c[1] - 140, "C", size=40), f.text(c[0] + 64, c[1] + 54, "D", size=40)
    return f


def square_plate_axes():
    """Square plate PQRS with centre O; in-plane axes 1 (diagonal through Q), 2 (diagonal through R), 3 (horizontal) and 4 (vertical)."""
    f = Figure(480, 480)
    o, h = (230, 250), 130
    f.rect(o[0] - h, o[1] - h, 2 * h, 2 * h, width=2.5)
    f.line(o[0] - 210, o[1] + 210, o[0] + 180, o[1] - 180, arrow=True)
    f.line(o[0] - 180, o[1] - 180, o[0] + 180, o[1] + 180, arrow=True)
    f.line(o[0] - 210, o[1], o[0] + 200, o[1], arrow=True), f.line(o[0], o[1] + 220, o[0], o[1] - 220, arrow=True)
    f.text(o[0] - h - 24, o[1] - h + 10, "P", size=32), f.text(o[0] + h + 26, o[1] - h + 24, "Q", size=32)
    f.text(o[0] + h + 24, o[1] + h + 10, "R", size=32), f.text(o[0] - h - 22, o[1] + h + 24, "S", size=32)
    f.text(o[0] - 16, o[1] + 46, "O", size=30), f.text(o[0] + 196, o[1] - 186, "1", size=30)
    f.text(o[0] + 196, o[1] + 214, "2", size=30), f.text(o[0] + 222, o[1] + 10, "3", size=30), f.text(o[0], o[1] - 230, "4", size=30)
    return f


def rod_released_from_vertical():
    """A rod pivoted at its lower end: held vertical (left), then turned through angle theta from the vertical (right), weight mg at its centre."""
    f = Figure(640, 340)
    f.line(20, 300, 220, 300), f.rect(40, 40, 24, 260, width=2.5)
    p, length, th = (360, 300), 300, 40
    f.line(320, 300, 620, 300), f.line(*p, p[0], 40, width=2, dash="8 6")
    end = (p[0] + length * math.sin(math.radians(th)), p[1] - length * math.cos(math.radians(th)))
    f.line(*p, *end, width=8)
    mid = ((p[0] + end[0]) / 2, (p[1] + end[1]) / 2)
    f.dot(*mid, r=6), f.line(*mid, mid[0], mid[1] + 90, arrow=True), f.text(mid[0] - 12, mid[1] + 84, "<i>mg</i>", size=26, anchor="end")
    f.arc(p[0], p[1], 70, -90, -90 + th, width=2), f.text(p[0] + 16, p[1] - 80, "<i>θ</i>", size=28)
    f.text((p[0] + mid[0]) / 2 + 22, (p[1] + mid[1]) / 2 + 20, "<i>L</i>/2", size=26, anchor="start")
    f.text((mid[0] + end[0]) / 2 - 22, (mid[1] + end[1]) / 2 - 6, "<i>L</i>/2", size=26, anchor="end")
    f.dot(*p, r=6)
    return f


def two_spheres_on_rod():
    """Two spheres of mass M and radius R joined by a rod; their centres are 4R apart."""
    f = Figure(640, 260)
    c1, c2, r = (100, 110), (540, 110), 80
    f.circle(*c1, r, width=4), f.circle(*c2, r, width=4)
    f.line(c1[0] + r, c1[1], c2[0] - r, c2[1], width=4)
    f.line(*c1, c1[0], c1[1] - r, width=4), f.line(*c2, c2[0], c2[1] - r, width=4), f.dot(*c1, r=6), f.dot(*c2, r=6)
    f.text(c1[0] - 30, c1[1] + 14, "<i>R</i>", size=30), f.text(c2[0] - 30, c2[1] + 14, "<i>R</i>", size=30)
    f.text(c1[0] + 70, 34, "<i>M</i>", size=30), f.text(c2[0] + 70, 34, "<i>M</i>", size=30)
    f.dim(c1[0], 226, c2[0], 226), f.text(320, 216, "4<i>R</i>", size=30, halo=True)
    return f


def three_spheres_axis():
    """Three equal spheres: sphere 1 on top with the axis YY' through its diameter; spheres 2 and 3 below, each touching the axis."""
    f = Figure(440, 520)
    x, r = 220, 72
    f.line(x, 20, x, 500, width=3)
    f.circle(x, 130, r, width=4), f.circle(x - r, 130 + r * math.sqrt(3), r, width=4), f.circle(x + r, 130 + r * math.sqrt(3), r, width=4)
    f.text(x + 24, 144, "1", size=40), f.text(x - r, 144 + r * math.sqrt(3), "2", size=40), f.text(x + r, 144 + r * math.sqrt(3), "3", size=40)
    f.text(x + 40, 36, "Y", size=34), f.text(x + 40, 496, "Y′", size=34)
    return f


def semicircular_wire():
    """A semicircular ring of mass M above the dashed diameter XX'."""
    f = Figure(600, 300)
    f.add('<path d="M120,260 A180,180 0 0 1 480,260" stroke-width="4"/>')
    f.line(20, 260, 580, 260, width=3, dash="16 10")
    f.text(300, 66, "<i>M</i>", size=30), f.text(20, 296, "X", size=30), f.text(580, 296, "X′", size=30)
    return f


def vt_trapezium():
    """Velocity (m/s) against time (s): A (1, 0) to B (3, 10), level to C (5, 10), down to D (7, 0); F and E are the feet of B and C."""
    f = Figure(560, 460)
    ox, oy, sx, sy = 100, 380, 52, 30
    f.line(ox - 10, oy, 540, oy, arrow=True), f.line(ox, oy + 10, ox, 30, arrow=True)
    pt = lambda t, v: (ox + sx * t, oy - sy * v)  # noqa: E731
    a, b, c, d = pt(1, 0), pt(3, 10), pt(5, 10), pt(7, 0)
    f.polyline([a, b, c, d])
    f.line(b[0], b[1], b[0], oy, width=2, dash="8 6"), f.line(c[0], c[1], c[0], oy, width=2, dash="8 6")
    for t in range(1, 8):
        f.line(ox + sx * t, oy, ox + sx * t, oy - 8, width=2), f.text(ox + sx * t, oy + 30, str(t), size=24)
    for v in (2, 4, 6, 8, 10):
        f.line(ox, oy - sy * v, ox + 8, oy - sy * v, width=2), f.text(ox - 12, oy - sy * v + 8, str(v), size=24, anchor="end")
    f.text(ox - 14, oy + 30, "0", size=24)
    f.text(a[0] - 14, oy - 12, "A", size=26), f.text(b[0], b[1] - 14, "B", size=26), f.text(c[0] + 14, c[1] - 14, "C", size=26)
    f.text(d[0] + 14, oy - 12, "D", size=26), f.text(b[0] - 14, oy - 12, "F", size=26), f.text(c[0] + 14, oy - 12, "E", size=26)
    f.text(320, 444, "time (s) →", size=28)
    with f.rotated(-90, 40, 200):
        f.text(40, 200, "Velocity m/s", size=28)
    return f


def vt_20_40_zero():
    """Velocity (m/s) against time (s): 20 m/s from 0 to 6 s, rising to 40 m/s at 10 s, then falling to zero at 14 s."""
    f = Figure(600, 440)
    ox, oy, sx, sy = 120, 340, 30, 6.5
    f.line(ox, oy, 580, oy, arrow=True), f.line(ox, oy, ox, 20, arrow=True)
    pt = lambda t, v: (ox + sx * t, oy - sy * v)  # noqa: E731
    f.polyline([pt(0, 20), pt(6, 20), pt(10, 40), pt(14, 0)])
    f.line(*pt(6, 20), *pt(6, 0), width=2, dash="8 6"), f.line(*pt(10, 40), *pt(10, 0), width=2, dash="8 6")
    for t in range(2, 15, 2):
        f.text(ox + sx * t, oy + 32, str(t), size=26)
    for v in (10, 20, 30, 40):
        f.text(ox - 12, oy - sy * v + 9, str(v), size=26, anchor="end")
    f.text(40, 230, "<i>v</i>", size=28), f.line(46, 190, 46, 150, arrow=True), f.text(46, 270, "(m/s)", size=26)
    f.text(450, 414, "<i>t</i> (s) →", size=28)
    return f


def xt_options():
    """Displacement against time: (a) constant, (b) rising line from the origin, (c) falling line, (d) a zig-zag."""
    f = Figure(760, 230)
    for name, ox in zip("abcd", (40, 230, 420, 610)):
        f.axes(ox, 150, 140, 120, size=24)
        f.text(ox - 18, 60, "<i>x</i>", size=26), f.text(ox + 110, 180, "<i>t</i> →", size=24)
        f.text(ox + 10, 180, "(0, 0)", size=22), f.text(ox + 60, 214, f"({name})", size=24)
    f.line(40, 70, 170, 70)
    f.line(230, 150, 350, 40)
    f.line(420, 50, 540, 150)
    f.polyline([(610, 110), (640, 60), (670, 100), (700, 60), (740, 100)])
    return f


def at_falling_line():
    """Acceleration (m/s^2) against time (s): falling linearly from 8 at t = 0 to zero at t = 10 s."""
    f = Figure(560, 420)
    ox, oy = 150, 330
    f.axes(ox, oy, 380, 300, size=30)
    f.line(ox, 90, 450, oy)
    f.text(ox - 16, 100, "8", size=34, anchor="end"), f.text(450, oy + 40, "10", size=34)
    f.text(64, 160, "<i>a</i>", size=34), f.line(70, 110, 70, 60, arrow=True), f.text(64, 230, "(m/s<sup>2</sup>)", size=30)
    f.text(390, 400, "<i>t</i> (s)", size=32), f.line(450, 390, 500, 390, arrow=True)
    return f


def two_pulleys_central_block():
    """Two fixed pulleys; a mass M hangs on the outer side of each; the inner strings meet at a central block of mass root 2 M, each making angle theta with the vertical."""
    f = Figure(640, 480)
    ceiling(f, 20, 620, 40)
    p1, p2, r = (110, 150), (530, 150), 36
    for p in (p1, p2):
        f.rect(p[0] - 8, 40, 16, p[1] - 40, width=2.5), f.circle(*p, r, width=3)
    f.line(p1[0] - r, p1[1], p1[0] - r, 400), f.line(p2[0] + r, p2[1], p2[0] + r, 400)
    f.arrowhead(p1[0] - r, 330, -90, size=16), f.arrowhead(p2[0] + r, 330, -90, size=16)
    f.rect(p1[0] - r - 30, 400, 60, 56), f.text(p1[0] - r, 438, "<i>M</i>", size=30)
    f.rect(p2[0] + r - 30, 400, 60, 56), f.text(p2[0] + r, 438, "<i>M</i>", size=30)
    top = (320, 290)
    f.line(p1[0] + r * 0.6, p1[1] - r * 0.8, *top), f.line(p2[0] - r * 0.6, p2[1] - r * 0.8, *top)
    f.line(*top, 320, 60, width=2, dash="10 8")
    f.arc(320, 290, 70, -90, -90 + 47, width=2), f.text(350, 200, "<i>θ</i>", size=28)
    f.rect(250, 290, 140, 70), f.text(320, 336, "√2 <i>M</i>", size=32)
    return f


def atwood_with_rider():
    """A fixed pulley with two equal blocks M on either side; a small mass m sits on the right-hand block."""
    f = Figure(420, 480)
    ceiling(f, 60, 260, 40)
    c, r = (160, 170), 80
    f.rect(152, 40, 16, 110, width=2.5), f.circle(*c, r, width=3), f.circle(*c, 56, width=3)
    f.line(c[0] - r, c[1], c[0] - r, 340), f.line(c[0] + r, c[1], c[0] + r, 390)
    f.rect(c[0] - r - 40, 340, 80, 70), f.text(c[0] - r, 386, "<i>M</i>", size=32)
    f.rect(c[0] + r - 50, 390, 100, 70), f.text(c[0] + r - 6, 436, "<i>M</i>", size=32)
    f.rect(c[0] + r + 20, 362, 28, 28), f.text(c[0] + r + 64, 384, "<i>m</i>", size=30, anchor="start")
    return f


def two_blocks_in_contact():
    """A 6 kg block and a shorter 4 kg block in contact on a smooth floor; a 5 N force pushes the 6 kg block from the left."""
    f = Figure(640, 220)
    f.line(20, 190, 620, 190)
    f.rect(190, 30, 180, 160), f.rect(370, 80, 200, 110)
    f.line(30, 110, 180, 110, arrow=True)
    f.text(90, 90, "5 N", size=32), f.text(280, 120, "6 kg", size=34), f.text(470, 150, "4 kg", size=34)
    return f


def ft_step_graph():
    """Force (N) against time (s): 8 N from 0 to 0.5 s, then 4 N from 0.5 s to 1.0 s."""
    f = Figure(600, 380)
    ox, oy = 250, 290
    f.line(ox, oy, 580, oy, arrow=True), f.line(ox, oy, ox, 30, arrow=True)
    f.polyline([(ox, 100), (380, 100), (380, oy)]), f.polyline([(380, 190), (480, 190), (480, oy)])
    f.line(ox, 190, 380, 190, width=2, dash="10 6"), f.line(380, 190, 380, oy, width=2, dash="10 6")
    f.text(ox - 20, 112, "8", size=30, anchor="end"), f.text(ox - 20, 202, "4", size=30, anchor="end"), f.text(ox - 20, oy + 10, "0", size=30, anchor="end")
    f.text(380, oy + 40, "0.5", size=30), f.text(480, oy + 40, "1.0", size=30)
    f.text(110, 80, "Force (<i>F</i>)", size=30), f.text(140, 120, "N", size=30), f.text(470, 360, "time (<i>t</i>) s", size=30)
    return f


def rope_pulled_aside():
    """Mass M hangs from a rope fixed at P; the rope PQ makes angle theta with the vertical because a horizontal force F pulls at Q; tension T along PQ."""
    f = Figure(520, 480)
    ceiling(f, 40, 300, 60)
    p, q = (150, 60), (280, 280)
    f.line(*p, p[0], 460, width=2, dash="12 8")
    f.line(*p, *q, width=4), f.arrowhead(214, 168, -120, size=20), f.text(250, 178, "<i>T</i>", size=32, anchor="start")
    f.dot(*q, r=8), f.line(*q, 460, q[1], width=4), f.text(476, q[1] + 10, "<i>F</i>", size=32, anchor="start")
    f.line(*q, q[0], 400, width=4), f.rect(q[0] - 34, 400, 68, 64, width=4), f.text(q[0], 444, "<i>M</i>", size=32)
    f.arc(p[0], p[1], 60, 90, 90 - 30, width=2), f.text(p[0] + 18, p[1] + 98, "<i>θ</i>", size=28)
    f.text(p[0] + 40, p[1] - 14, "P", size=32), f.text(q[0] + 10, q[1] - 22, "Q", size=32, anchor="start")
    return f


FIGURES = {
    "PYQ-PHY-a80be998bc0e": disc_points,
    "PYQ-PHY-7a8e83fc71d4": square_plate_axes,
    "PYQ-PHY-cec0abd73614": rod_released_from_vertical,
    "PYQ-PHY-fe6db6207711": two_spheres_on_rod,
    "PYQ-PHY-c8381b57c77e": three_spheres_axis,
    "PYQ-PHY-9c6cddbe3e5d": semicircular_wire,
    "PYQ-PHY-3e2dbd851e37": vt_trapezium,
    "PYQ-PHY-28f92a646550": vt_20_40_zero,
    "PYQ-PHY-b3991c78e04a": xt_options,
    "PYQ-PHY-441393e884fa": at_falling_line,
    "PYQ-PHY-eb8109f0fbf0": two_pulleys_central_block,
    "PYQ-PHY-5acad6651ee1": atwood_with_rider,
    "PYQ-PHY-af0b02f08147": two_blocks_in_contact,
    "PYQ-PHY-3b516e4a1879": ft_step_graph,
    "PYQ-PHY-9dcaef0f5be2": rope_pulled_aside,
}
