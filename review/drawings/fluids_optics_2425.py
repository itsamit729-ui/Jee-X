"""Physics (MHT-CET 2024-25): fluids, optics, circular motion, atoms, centre of mass and waves."""

import math

from figlib import INK, Figure


def ellipse(f, cx, cy, rx, ry, width=3, dash=None):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    f.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" stroke-width="{width}"{extra}/>')


def water_lines(f, x1, x2, y1, y2, step=22, dash=None):
    for y in range(int(y1) + step // 2, int(y2), step):
        f.line(x1, y, x2, y, width=1.5, dash=dash)


def cylinder_three_orifices():
    """A cylinder of water of height H with orifices O1, O2, O3 at increasing depth on its side; jets v1, v2, v3."""
    f = Figure(620, 380)
    l, r, t, b = 80, 380, 20, 350
    f.line(l, t, l, b), f.line(r, t, r, 90), f.line(r, 110, r, 180), f.line(r, 200, r, 270), f.line(r, 290, r, b), f.line(l, b, r, b)
    water_lines(f, l, r, t, b, step=24)
    f.dim(40, t, 40, b), f.text(30, 200, "<i>H</i>", size=36, halo=True)
    for i, y in enumerate((100, 190, 280)):
        f.line(r, y, 470, y, arrow=True)
        f.text(400, y - 14, f"O<sub>{i + 1}</sub>", size=30, anchor="start"), f.text(484, y + 10, f"(<i>v</i><sub>{i + 1}</sub>)", size=30, anchor="start")
    return f


def capillary_options():
    """Capillary rise h against radius r: (A) constant, (B) falling hyperbola, (C) a vertical line, (D) a falling straight line."""
    f = Figure(640, 480)
    for name, (ox, oy) in zip("ABCD", ((60, 180), (360, 180), (60, 420), (360, 420))):
        f.axes(ox, oy, 210, 150, xlabel="<i>r</i>", ylabel="<i>h</i>", size=28)
        f.text(ox + 80, oy + 46, f"({name})", size=28)
    f.line(60, 70, 220, 70)
    f.curve(lambda x: 170 - 2600 / (x - 352), 372, 560)
    f.line(170, 300, 170, 420)
    f.line(400, 300, 540, 380)
    return f


def conical_tube():
    """A conical tube: wide end A1 (pressure P1, velocity v1) on the left, narrow end A2 (P2, v2) on the right."""
    f = Figure(680, 360)
    ellipse(f, 110, 190, 60, 140), ellipse(f, 520, 110, 30, 50)
    f.line(110, 50, 520, 60), f.line(110, 330, 520, 160)
    f.line(110, 210, 200, 190, arrow=True), f.line(540, 100, 620, 80, arrow=True)
    f.text(40, 50, "A<sub>1</sub>", size=30), f.text(520, 40, "A<sub>2</sub>", size=30)
    f.text(220, 196, "<i>v</i><sub>1</sub>", size=30, anchor="start"), f.text(630, 80, "<i>v</i><sub>2</sub>", size=30, anchor="start")
    f.text(70, 356, "P<sub>1</sub>", size=30), f.text(520, 196, "P<sub>2</sub>", size=30)
    return f


def tank_two_holes():
    """A tank of liquid with two small holes on opposite sides, the left one higher by h; liquid jets out of both."""
    f = Figure(620, 420)
    l, r, t, b = 140, 480, 20, 400
    f.line(l, t, l, 100), f.line(l, 140, l, b), f.line(r, t, r, 290), f.line(r, 330, r, b), f.line(l, b, r, b)
    water_lines(f, l + 20, r - 20, 30, b, step=28, dash="60 18")
    f.circle(l, 120, 20, fill="#fff"), f.circle(r, 310, 20, fill="#fff")
    f.line(l - 20, 120, 30, 120, width=5, arrow=True), f.line(r + 20, 310, 600, 310, width=5, arrow=True)
    f.dim(300, 120, 300, 310), f.text(320, 226, "<i>h</i>", size=36, anchor="start", halo=True)
    return f


def cylinder_at_interface():
    """A solid cylinder of density d floats upright across the interface between a liquid of density rho (above) and one of density 3 rho (below)."""
    f = Figure(640, 340)
    l, r, t, m, b = 30, 610, 30, 170, 310
    f.rect(l, t, r - l, b - t, width=4)
    water_lines(f, l + 10, r - 10, t, m, step=26, dash="40 14")
    f.line(l, m, r, m, width=3)
    f.add(f'<clipPath id="lower"><rect x="{l}" y="{m}" width="{r - l}" height="{b - m}"/></clipPath>')
    body = "".join(f'<line x1="{x}" y1="{b}" x2="{x + (b - m)}" y2="{m}" stroke-width="2"/>' for x in range(l - (b - m), r, 22))
    f.add(f'<g clip-path="url(#lower)">{body}</g>')
    f.rect(200, 90, 36, 120, fill="#fff", width=3), f.text(218, 160, "<i>d</i>", size=30)
    f.text(420, 120, "<i>ρ</i>", size=32, halo=True), f.text(480, 270, "3<i>ρ</i>", size=32, halo=True)
    return f


def three_polaroids_axes():
    """Light from S passes polaroids P1 (pass axis vertical), P2 (axis at 60 degrees to it) and P3 (axis at 90 degrees, drawn in perspective) to O; x, y, z axes for reference."""
    f = Figure(640, 520)
    def plate(x, y):
        f.line(x, y - 110, x, y + 110, width=3)
    f.line(30, 120, 220, 120), f.text(20, 130, "S", size=30)
    f.line(130, 0, 130, 240, width=2, dash="8 6"), f.text(150, 260, "P<sub>1</sub>", size=28)
    f.line(330, 120, 520, 120)
    plate(420, 120), f.line(420 - 70, 120 + 120, 420 + 70, 120 - 120, width=2, dash="8 6"), f.text(440, 260, "P<sub>2</sub>", size=28)
    f.arc(420, 120, 70, -90, -60, width=2), f.text(452, 30, "60°", size=24)
    f.line(30, 400, 240, 400), plate(120, 400), f.line(40, 470, 200, 330, width=2, dash="8 6")
    f.text(256, 410, "O", size=28, anchor="start"), f.text(130, 506, "P<sub>3</sub>", size=28)
    o = (420, 400)
    f.line(*o, 600, 400, arrow=True), f.line(*o, 420, 290, arrow=True), f.line(*o, 350, 470, arrow=True)
    f.text(610, 420, "<i>x</i>", size=28, anchor="start"), f.text(404, 296, "<i>y</i>", size=28), f.text(366, 492, "<i>z</i>", size=28)
    return f


def slab_reflections():
    """A ray enters a parallel glass slab at A: AB is reflected at A; the refracted ray reflects at C on the lower face (part also leaves through it),
    returns to A' on the upper face and leaves as A'B'. Dashed normals at A, A' and C."""
    f = Figure(640, 460)
    top, bottom = 160, 380
    f.line(30, top, 610, top, width=4), f.line(30, bottom, 610, bottom, width=4)
    a, c, a2 = (220, top), (300, bottom), (380, top)
    f.line(110, 70, *a, width=4), f.arrowhead(160, 112, 40, size=18)
    f.line(*a, 300, 60, width=4), f.arrowhead(280, 86, -52, size=18)
    f.line(*a, *c, width=4), f.line(*c, *a2, width=4), f.arrowhead(350, 244, -70, size=18)
    f.line(*a2, 480, 60, width=4)
    f.line(*c, 380, 450, width=4), f.arrowhead(370, 440, 50, size=18)
    for x, y in (a, a2, c):
        f.line(x, y - 60, x, y - 20, width=3, dash="10 8"), f.line(x, y + 20, x, y + 60, width=3, dash="10 8")
    f.text(180, 210, "A", size=32), f.text(310, 46, "B", size=32), f.text(410, 210, "A′", size=32), f.text(500, 46, "B′", size=32)
    f.text(250, 430, "C", size=32)
    return f


def three_circular_polaroids():
    """Unpolarised light I0 passes three polaroids 1, 2, 3 on a common axis; pass axis of 2 at 30 degrees and of 3 at 90 degrees to that of 1."""
    f = Figure(700, 250)
    y = 120
    f.line(20, y, 680, y, width=2, dash="10 6"), f.line(30, 106, 80, 106, arrow=True), f.text(30, 98, "<i>I</i><sub>0</sub>", size=26, anchor="start")
    for i, (x, ang) in enumerate(((160, 0), (360, 30), (560, 90))):
        f.circle(x, y, 56, width=3), f.line(x, y - 100, x, y + 100, width=2, dash="8 6")
        f.text(x + 18, y + 104, str(i + 1), size=28, anchor="start")
        if ang:
            tilt = 30 if ang == 30 else 45  # 90 degrees is drawn in perspective, as in the source
            dx, dy = 100 * math.sin(math.radians(tilt)), 100 * math.cos(math.radians(tilt))
            f.line(x - dx, y + dy, x + dx, y - dy, width=2, dash="8 6")
            f.arc(x, y, 76, -90, -90 + tilt, width=2), f.text(x + 30, y - 84, f"{ang}°", size=26, anchor="start")
    return f


def fringe_width_graph():
    """Fringe width X against screen distance D: a straight line through the origin."""
    f = Figure(560, 400)
    ox, oy = 110, 310
    f.axes(ox, oy, 420, 280, size=34)
    f.line(ox, oy, 440, 50)
    f.text(40, 170, "X", size=38), f.line(60, 130, 60, 60, width=5, arrow=True)
    f.line(340, 370, 420, 370, width=5, arrow=True), f.text(450, 382, "D", size=38)
    return f


def mirror_under_liquid():
    """A tank of liquid with a plane mirror on its base; object P at height h above the mirror; observer O vertically above, outside the liquid."""
    f = Figure(400, 520)
    l, r, surf, mirror, b = 40, 340, 220, 450, 490
    f.line(l, 30, l, b), f.line(r, 30, r, b), f.line(l, b, r, b), f.line(l, surf, r, surf)
    f.line(l, mirror, r, mirror, width=3)
    f.line(170, 50, 170, surf), f.dot(170, 40, r=10), f.text(190, 50, "O", size=30, anchor="start")
    f.dot(170, 270, r=10), f.line(170, 280, 170, mirror, width=2, dash="8 6")
    f.dim(220, 274, 220, mirror - 4), f.text(140, 380, "P", size=30), f.text(240, 380, "<i>h</i>", size=30, anchor="start")
    return f


def white_light_critical():
    """White light in glass meets the glass-air interface; green is just totally internally reflected, grazing along the surface."""
    f = Figure(640, 480)
    p = (360, 180)
    f.line(20, p[1], 620, p[1]), f.line(p[0], 20, p[0], 380)
    f.line(110, 420, *p), f.arrowhead(240, 296, -45, size=16)
    f.line(*p, 600, p[1], width=2), f.arrowhead(590, p[1], 0, size=14)
    f.text(30, 160, "air", size=28, anchor="start"), f.text(30, 214, "glass", size=28, anchor="start")
    f.text(620, 164, "green", size=28, anchor="end"), f.text(40, 460, "white light", size=28, anchor="start")
    return f


def glass_sphere_image():
    """A point object P on the axis of a glass sphere (centre C, left surface at O) forms its image at Q; a ray refracts at the surface towards Q."""
    f = Figure(700, 360)
    c, r = (420, 190), 150
    o = (c[0] - r, c[1])
    f.circle(*c, r, width=2), f.line(20, c[1], 690, c[1], width=2)
    s = (c[0] - r * math.cos(math.radians(55)), c[1] - r * math.sin(math.radians(55)))
    p, q = (80, c[1]), (520, c[1])
    f.line(*p, *s), f.arrowhead((p[0] + s[0]) / 2 + 40, (p[1] + s[1]) / 2 - 8, -17, size=14)
    f.line(*s, *q), f.arrowhead(s[0] + (q[0] - s[0]) * 0.55, s[1] + (q[1] - s[1]) * 0.55, 34, size=14)
    f.line(s[0] - 80, s[1] - 70, *c, width=1.5, dash="8 6")
    f.text(80, c[1] + 40, "P", size=28), f.text(o[0] - 18, c[1] + 40, "O", size=28)
    f.text(c[0] - 14, c[1] + 40, "C", size=28), f.text(q[0] + 18, c[1] + 40, "Q", size=28)
    return f


def mass_round_hole():
    """Mass m moves in a horizontal circle of radius L about a hole O in a table; the string passes through O to a hanging mass M."""
    f = Figure(560, 440)
    ellipse(f, 280, 150, 240, 120, dash="22 14", width=4)
    f.dot(240, 150, r=8), f.line(240, 150, 400, 150, width=4), f.dot(400, 150, r=9)
    f.line(240, 150, 240, 320, width=4)
    f.rect(190, 320, 110, 80, width=4)
    for x in range(196, 270, 24):
        f.line(x, 398, x + 30, 322, width=3)
    f.text(210, 164, "O", size=34, anchor="end"), f.text(320, 130, "<i>L</i>", size=34), f.text(420, 164, "<i>m</i>", size=34, anchor="start")
    f.text(320, 372, "<i>M</i>", size=34, anchor="start")
    return f


def particle_in_cone():
    """A particle moves in a horizontal circle (dashed) on the smooth inner surface of an inverted cone, at height h = 10 cm above the vertex; theta is the half-angle at the base."""
    f = Figure(640, 420)
    v, h_top = (250, 380), 40
    f.line(20, v[1], 620, v[1], width=4)
    f.line(*v, 70, h_top, width=4), f.line(*v, 430, h_top, width=4), f.line(70, h_top, 430, h_top, width=4)
    f.line(v[0], h_top, v[0], v[1], width=3)
    ellipse(f, 250, 140, 128, 26, width=3, dash="16 10")
    f.dot(122, 140, r=7), f.dot(378, 140, r=7)
    f.dim(400, 146, 400, v[1] - 4), f.text(420, 270, "<i>h</i> = 10 cm", size=34, anchor="start")
    f.arc(v[0], v[1], 46, 180, 180 + 62, width=2), f.text(190, 370, "<i>θ</i>", size=30)
    return f


def vertical_circle_abcd():
    """A vertical circle about O: A at the top (string OA), B at the bottom, C on the left and D on the right; the mass moves C to B to D to A."""
    f = Figure(460, 480)
    o, r = (230, 240), 190
    f.circle(*o, r, width=5), f.line(*o, o[0], o[1] - r, width=5)
    for p in ((o[0], o[1] - r), (o[0], o[1] + r), (o[0] - r, o[1]), (o[0] + r, o[1]), o):
        f.dot(*p, r=14)
    f.arrowhead(o[0] - r * math.cos(math.radians(40)), o[1] + r * math.sin(math.radians(40)), 50, size=24)
    f.arrowhead(o[0] + r * math.cos(math.radians(40)), o[1] - r * math.sin(math.radians(40)), -130, size=24)
    f.text(o[0] - 34, o[1] - 70, "A", size=44), f.text(o[0] + 20, o[1] + 140, "B", size=44)
    f.text(o[0] - r + 50, o[1] + 16, "C", size=44), f.text(o[0] + r - 50, o[1] + 16, "D", size=44), f.text(o[0] + 40, o[1] - 20, "O", size=44)
    return f


def hydrogen_levels_transitions():
    """Energy levels n = 1 (ground state), n = 2 and n = 3 (excited states); transition 1 from n = 3 to n = 1, transition 2 from n = 2 to n = 1."""
    f = Figure(700, 280)
    ys = {3: 40, 2: 130, 1: 230}
    for n, y in ys.items():
        f.line(140, y, 440, y, width=2), f.text(20, y + 12, f"<i>n</i> = {n}", size=34, anchor="start")
    f.line(360, 40, 360, 226, width=2, arrow=True), f.line(250, 130, 250, 226, width=2, arrow=True)
    f.text(380, 180, "1", size=30, anchor="start"), f.text(270, 190, "2", size=30, anchor="start")
    f.text(460, 140, "Excited state", size=34, anchor="start"), f.text(460, 242, "Ground state", size=34, anchor="start")
    return f


def three_rods_triangle():
    """Three rods form a right triangle with corners (0, a), (0, 0) and (2a, 0)."""
    f = Figure(640, 340)
    a, o, b = (130, 40), (130, 280), (560, 280)
    f.path([a, o, b], close=True, width=5)
    f.text(50, 56, "(0, <i>a</i>)", size=32), f.text(60, 320, "(0, 0)", size=32), f.text(560, 324, "(2<i>a</i>, 0)", size=32)
    return f


def wave_points():
    """A progressive sine wave along x with points A to F marked on it; B and E are a whole number of wavelengths apart."""
    f = Figure(760, 260)
    ox, oy, lam, amp = 60, 130, 150, 90
    f.line(30, oy, 730, oy, arrow=True), f.line(ox, 240, ox, 20, arrow=True)
    f.curve(lambda x: oy - amp * math.sin(2 * math.pi * (x - ox) / lam), ox, ox + 4 * lam, steps=400)
    pts = {"A": 12, "B": 40, "C": 440, "D": 215, "E": 760, "F": 915}
    for name, deg in pts.items():
        x = ox + lam * deg / 360
        y = oy - amp * math.sin(math.radians(deg))
        f.dot(x, y, r=5)
        dy = 30 if name in ("D", "F") else -16
        f.text(x + 16, y + dy, name, size=26, anchor="start")
    f.text(40, 30, "Y", size=28, anchor="end"), f.text(744, oy + 8, "<i>x</i>", size=28, anchor="start"), f.text(40, oy + 10, "O", size=26, anchor="end")
    return f


FIGURES = {
    "PYQ-PHY-ff08febc1560": cylinder_three_orifices,
    "PYQ-PHY-69a34d04f030": capillary_options,
    "PYQ-PHY-027d20ebc89c": conical_tube,
    "PYQ-PHY-d11cfa5c4268": tank_two_holes,
    "PYQ-PHY-6b49557f03ac": cylinder_at_interface,
    "PYQ-PHY-7a3b714addbb": three_polaroids_axes,
    "PYQ-PHY-e293da8e65ac": slab_reflections,
    "PYQ-PHY-c06f0169ce3b": three_circular_polaroids,
    "PYQ-PHY-83170c0f932f": fringe_width_graph,
    "PYQ-PHY-4efc11cddf60": mirror_under_liquid,
    "PYQ-PHY-eb062b0b854b": white_light_critical,
    "PYQ-PHY-5e8409c0099a": glass_sphere_image,
    "PYQ-PHY-190f78f96d74": mass_round_hole,
    "PYQ-PHY-6638cf60607c": particle_in_cone,
    "PYQ-PHY-66c9a5bfe77a": vertical_circle_abcd,
    "PYQ-PHY-86108b01b8ac": hydrogen_levels_transitions,
    "PYQ-PHY-f4c7c503511a": three_rods_triangle,
    "PYQ-PHY-5edfefb08021": wave_points,
}
