"""Physics: oscillations (last), ray optics, rotational motion (part 1)."""

import math

from drawings.physics_06 import ceiling
from figlib import INK, Figure, coil, mid_arrow


def spin_arrow(f, x, y, rx=26, ry=8):
    """A small curved arrow round a vertical axis, showing rotation."""
    f.add(f'<path d="M{x + rx},{y} A{rx},{ry} 0 1 1 {x + rx * 0.5},{y - ry * 0.9}" stroke-width="2.5"/>')
    f.arrowhead(x + rx, y + 2, 80, size=12)


def three_masses_on_spring():
    """A spring hung from a support carrying three stacked masses: 100 g, 300 g and 500 g."""
    f = Figure(300, 470)
    ceiling(f, 78, 182, 62)
    f.line(130, 62, 130, 96)
    with f.rotated(90, 130, 96):
        coil(f, 130, 290, 96, turns=5, radius=22)
    f.line(130, 256, 130, 300)
    for k, label in enumerate(("100 g", "300 g", "500 g")):
        f.block(88, 300 + 44 * k, 84, 44, label, size=24)
    return f


def right_angled_prism():
    """Right-angled isosceles prism PQR (right angle at Q): a ray from X enters through PQ, reflects at O on PR and leaves towards Y."""
    f = Figure(640, 470)
    p, q, r, o = (122, 46), (122, 362), (438, 362), (271, 195)
    f.path([p, q, r], close=True)
    mid_arrow(f, 32, 195, *o, at=0.35), f.vector(*o, 271, 420), f.dot(*o, r=4)
    f.right_angle(122, 362, 1, -1, size=20)
    f.arc(*p, 44, 45, 90), f.arc(*r, 44, 180, 225), f.arc(*o, 34, 180, 225), f.arc(*o, 34, 45, 90)
    f.text(152, 112, "45°", size=24), f.text(376, 346, "45°", size=24)
    f.text(218, 184, "45°", size=24), f.text(304, 260, "45°", size=24), f.text(168, 352, "90°", size=24)
    f.text(104, 40, "P", size=28), f.text(100, 380, "Q", size=28), f.text(456, 382, "R", size=28)
    f.text(296, 196, "O", size=28), f.text(18, 205, "X", size=28), f.text(271, 452, "Y", size=28)
    return f


def four_regions():
    """Regions I to IV separated by parallel boundaries; a ray in region I meets the first boundary at angle theta to the normal."""
    f = Figure(1000, 340)
    f.line(20, 208, 985, 208)
    for x in (318, 537, 748):
        f.line(x, 28, x, 208)
    for x, name in ((200, "I"), (428, "II"), (642, "III"), (866, "IV")):
        f.text(x, 52, f"region {name}", size=26)
    mid_arrow(f, 105, 208, 318, 124, at=0.5), f.line(70, 124, 400, 124, width=1.5)
    f.arc(318, 124, 70, 158.5, 180), f.text(226, 162, "<i>θ</i>", size=26), f.text(86, 114, "normal", size=24)
    return f


def split_biconvex_lens():
    """A bi-convex lens made of two plano-convex halves: n = 1.5 on the left and n = 1.2 on the right, each curved surface of R = 14 cm."""
    f = Figure(340, 470)
    f.add('<path d="M168,28 Q110,214 168,400 Q226,214 168,28 Z" stroke-width="3"/>')
    f.line(168, 28, 168, 400, width=2, dash="9 8")
    f.text(60, 48, "<i>n</i> = 1.5", size=28), f.text(278, 48, "<i>n</i> = 1.2", size=28)
    f.vector(84, 64, 138, 116, width=2), f.vector(250, 64, 198, 116, width=2)
    f.vector(100, 412, 142, 340, width=2), f.vector(236, 412, 194, 340, width=2)
    f.text(168, 452, "<i>R</i> = 14 cm", size=28)
    return f


def ring_with_sliding_masses():
    """A ring spinning about the vertical axis through its centre O, with two point masses on radial rods."""
    f = Figure(640, 460)
    cx, cy = 314, 252
    f.add(f'<ellipse cx="{cx}" cy="{cy}" rx="272" ry="118" stroke-width="3"/>')
    f.add(f'<ellipse cx="{cx}" cy="{cy}" rx="246" ry="100" stroke-width="3"/>')
    f.line(cx, 32, cx, cy), f.line(cx, cy, cx, 352, width=2.5, dash="5 7"), f.line(cx, 370, cx, 436)
    spin_arrow(f, cx, 78, rx=34, ry=10), f.text(cx + 30, 48, "<i>ω</i>", size=30)
    left, right = (92, 208), (502, 188)
    f.line(cx, cy, *left), f.line(cx, cy, *right)
    for end, t in ((left, 0.38), (right, 0.28)):
        f.dot(cx + (end[0] - cx) * t, cy + (end[1] - cy) * t, r=9)
    f.arrowhead(cx + (left[0] - cx) * 0.52, cy + (left[1] - cy) * 0.52, math.degrees(math.atan2(left[1] - cy, left[0] - cx)))
    f.dot(cx, cy, r=4), f.text(cx - 30, cy + 28, "<i>O</i>", size=30)
    return f


def seven_rings():
    """Seven identical rings of radius R: one in the centre touching six around it."""
    f = Figure(470, 470)
    cx, cy, r = 235, 235, 65
    f.circle(cx, cy, r), f.dot(cx, cy, r=3)
    for k in range(6):
        a = math.radians(90 + 60 * k)
        x, y = cx + 2 * r * math.cos(a), cy - 2 * r * math.sin(a)
        f.circle(x, y, r), f.dot(x, y, r=3)
    f.line(cx, cy, cx, cy - r, width=2.5), f.text(cx - 18, cy - 22, "<i>R</i>", size=28)
    return f


def three_rings_axis():
    """Ring A centred on the axis YY', above rings B and C which touch each other on the axis; each has radius R."""
    f = Figure(340, 470)
    x, r = 170, 58
    f.line(x, 38, x, 428, width=2.5)
    f.circle(x, 185, r), f.circle(x - r, 285, r), f.circle(x + r, 285, r)
    f.line(x - r, 285, x + r, 285, width=2)
    f.text(x, 28, "<i>Y</i>", size=26), f.text(x, 458, "<i>Y</i>′", size=26)
    f.text(244, 158, "<i>A</i>", size=26), f.text(34, 296, "<i>B</i>", size=26), f.text(306, 296, "<i>C</i>", size=26)
    f.text(x - 34, 274, "<i>R</i>", size=24), f.text(x + 34, 274, "<i>R</i>", size=24)
    return f


def five_spheres_axis():
    """Five identical spheres about the axis AA': three centred on the axis and two touching it on either side."""
    f = Figure(340, 470)
    x, r = 170, 44
    for cx, cy in ((x, 132), (x - r, 208), (x + r, 208), (x, 284), (x, 372)):
        f.circle(cx, cy, r)
    f.line(x, 36, x, 438, width=2.5)
    spin_arrow(f, x, 62)
    f.text(x, 28, "A", size=24), f.text(x, 464, "A′", size=24)
    return f


def sphere_and_axis():
    """A solid sphere whose centre is 10 cm from the axis of rotation."""
    f = Figure(470, 460)
    f.line(46, 30, 46, 432, width=5)
    f.circle(382, 216, 40), f.line(46, 216, 382, 216, arrow=True)
    f.text(210, 262, "10 cm", size=32)
    return f


def rod_turning_about_b():
    """A rod pivoted at B, shown upright (BA) and after turning through angle theta with angular velocity omega."""
    f = Figure(340, 470)
    b = (40, 412)
    f.line(*b, 40, 92, width=4, arrow=True), f.line(*b, 266, 186, width=4, arrow=True)
    f.arc(*b, 336, -84, -47, width=4), f.arrowhead(278, 176, 52, size=20)
    f.arc(*b, 72, -90, -45, width=3)
    f.text(18, 98, "<i>A</i>", size=32), f.text(40, 452, "<i>B</i>", size=32)
    f.text(72, 318, "<i>θ</i>", size=32), f.text(128, 52, "<i>ω</i>", size=32)
    return f


def sphere_parallel_axis():
    """A hollow sphere with centre C: the diameter AB and a parallel axis XY at distance h from it."""
    f = Figure(370, 470)
    f.circle(168, 238, 130, width=5)
    f.line(168, 78, 168, 404, width=4), f.line(230, 96, 230, 388, width=4)
    f.dim(172, 238, 226, 238, width=3)
    f.text(148, 74, "A", size=28), f.text(148, 422, "B", size=28), f.text(252, 92, "X", size=28), f.text(252, 410, "Y", size=28)
    f.text(146, 248, "C", size=28), f.text(200, 276, "<i>h</i>", size=28)
    return f


def rod_with_end_masses():
    """Two masses m at the ends A and B of a rod; the axis XX' passes through its centre O, perpendicular to it."""
    f = Figure(560, 460)
    f.line(262, 58, 262, 402, width=2, dash="9 8")
    f.rect(84, 212, 356, 6, fill="#fff", width=2.5), f.dot(84, 215, r=10), f.dot(440, 215, r=10)
    f.text(46, 224, "<i>m</i>", size=28), f.text(480, 224, "<i>m</i>", size=28)
    f.text(84, 256, "A", size=26), f.text(440, 256, "B", size=26), f.text(280, 256, "O", size=26)
    f.text(262, 44, "X", size=28), f.text(264, 436, "X′", size=28)
    return f


FIGURES = {
    "PYQ-PHY-5cae8b8c7b29": three_masses_on_spring,
    "PYQ-PHY-5ada71209ad1": right_angled_prism,
    "PYQ-PHY-9aa31bbeed7f": four_regions,
    "PYQ-PHY-dfd1a9faf63a": split_biconvex_lens,
    "PYQ-PHY-288899f2d585": ring_with_sliding_masses,
    "PYQ-PHY-4393ebafbda8": seven_rings,
    "PYQ-PHY-5163964cacaa": three_rings_axis,
    "PYQ-PHY-5319ffd754f5": five_spheres_axis,
    "PYQ-PHY-5650aa977da9": sphere_and_axis,
    "PYQ-PHY-626088f7966f": rod_turning_about_b,
    "PYQ-PHY-6503b7edad4b": sphere_parallel_axis,
    "PYQ-PHY-c6f4e7db8116": rod_with_end_masses,
}
