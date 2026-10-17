"""Physics (MHT-CET 2024-25): electric charges, fields and potential."""

import math

from figlib import INK, Figure


def ellipse(f, cx, cy, rx, ry, width=3, dash=None):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    f.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" stroke-width="{width}"{extra}/>')


def cylinder(f, x1, x2, cy, ry, rx=26):
    """A horizontal cylinder with both end faces drawn as ellipses."""
    f.line(x1, cy - ry, x2, cy - ry), f.line(x1, cy + ry, x2, cy + ry)
    ellipse(f, x1, cy, rx, ry), ellipse(f, x2, cy, rx, ry)


def hexagon_charges(right_label="+<i>Q</i>"):
    """Regular hexagon ABCDEF (A top left, going anticlockwise) with centre O: +q at A, -q at B, -q at C, +q at D, +Q at E, -q at F; dashed diagonals, r marked."""
    f = Figure(560, 440)
    cx, cy, r = 280, 220, 160
    names = ("A", "B", "C", "D", "E", "F")
    angles = (240, 180, 120, 60, 0, 300)  # degrees, 0 = right, 90 = down
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in angles]
    f.path(pts, close=True)
    for p in pts:
        f.line(cx, cy, *p, width=2, dash="8 6")
    f.dot(cx, cy, r=6)
    charges = ("+<i>q</i>", "−<i>q</i>", "−<i>q</i>", "+<i>q</i>", right_label, "−<i>q</i>")
    offsets = ((-20, -44, -50, -8), (-50, 0, -40, 40), (-34, 36, 14, 52), (40, 30, -20, 52), (44, 0, 54, 44), (20, -44, 54, -8))
    for (x, y), name, q, (dx, dy, qx, qy) in zip(pts, names, charges, offsets):
        f.text(x + dx, y + dy + 10, name, size=34), f.text(x + qx, y + qy + 10, q, size=32)
    f.text(cx - 80, cy - 14, "<i>r</i>", size=32), f.text(cx + 80, cy - 14, "<i>r</i>", size=32), f.text(cx, cy + 40, "O", size=30)
    return f


def charge_moves_on_arc():
    """+Q at the centre; A and B lie on an arc of radius r about it, 30 degrees apart; the charge moves from A to B along the arc."""
    f = Figure(640, 440)
    o, r = (100, 330), 460
    a = (o[0] + r, o[1])
    b = (o[0] + r * math.cos(math.radians(-30)), o[1] + r * math.sin(math.radians(-30)))
    f.line(*o, *a, width=2, dash="8 6"), f.line(*o, *b, width=2, dash="8 6")
    f.arc(o[0], o[1], r, 18, -40, width=3)
    f.arrowhead(o[0] + r * math.cos(math.radians(-16)), o[1] + r * math.sin(math.radians(-16)), -106, size=18)
    f.arc(o[0], o[1], 110, 0, -30, width=2)
    f.dot(*a, r=6), f.dot(*b, r=6)
    f.text(60, 344, "+<i>Q</i>", size=38), f.text(a[0] + 40, a[1] + 12, "A", size=38), f.text(b[0] + 40, b[1] - 6, "B", size=38)
    f.text(250, 300, "30°", size=34), f.text(310, 390, "<i>r</i>", size=34), f.text(310, 220, "<i>r</i>", size=34)
    return f


def two_charges_one_metre():
    """2 uC at A and -3 uC at B, 1 m apart."""
    f = Figure(640, 160)
    f.line(60, 80, 580, 80), f.dot(60, 80, r=12), f.dot(580, 80, r=12)
    f.text(60, 40, "2 μC", size=32), f.text(580, 40, "−3 μC", size=32), f.text(320, 60, "1 m", size=32)
    f.text(60, 134, "A", size=32), f.text(580, 134, "B", size=32)
    return f


def cylinder_c_b_a():
    """A closed cylinder: plane face C on the left, curved surface B, plane face A on the right."""
    f = Figure(700, 240)
    cylinder(f, 60, 640, 120, 90, rx=36)
    f.dot(350, 110, r=5), f.text(380, 124, "B", size=40, anchor="start")
    f.text(60, 134, "C", size=40), f.text(640, 134, "A", size=40)
    return f


def triangle_q_q_q():
    """Equilateral triangle of side a: Q at the top, +q at the two lower corners."""
    f = Figure(500, 480)
    top, bl, br = (250, 60), (80, 400), (420, 400)
    f.path([top, bl, br], close=True)
    for p in (top, bl, br):
        f.dot(*p, r=8)
    f.dim(40, 380, 150, 140)
    f.text(250, 36, "<i>Q</i>", size=36), f.text(80, 456, "+<i>q</i>", size=36), f.text(420, 456, "+<i>q</i>", size=36)
    f.text(70, 266, "<i>a</i>", size=36)
    return f


def square_q_q_diagonals():
    """A square with +Q at the top-left and bottom-right corners and -q at the other two."""
    f = Figure(560, 520)
    f.rect(100, 70, 360, 380), f.dot(280, 260, r=8)
    f.text(56, 58, "+<i>Q</i>", size=38), f.text(510, 58, "−<i>q</i>", size=38)
    f.text(56, 492, "−<i>q</i>", size=38), f.text(510, 492, "+<i>Q</i>", size=38)
    return f


def half_rings_r1_r2():
    """Two concentric charged half rings (radii R1 and R2) about the centre O, + charges along them."""
    f = Figure(640, 420)
    o = (320, 370)
    f.arc(o[0], o[1], 230, 180, 360, width=3), f.arc(o[0], o[1], 310, 180, 360, width=3)
    for rr in (230, 310):
        for ang in range(200, 360, 22):
            x, y = o[0] + (rr - 24) * math.cos(math.radians(ang)), o[1] + (rr - 24) * math.sin(math.radians(ang))
            f.text(x, y + 10, "+", size=28)
    f.line(*o, o[0] + 225 * math.cos(math.radians(-20)), o[1] + 225 * math.sin(math.radians(-20)), arrow=True)
    f.line(*o, o[0] + 305 * math.cos(math.radians(-55)), o[1] + 305 * math.sin(math.radians(-55)), arrow=True)
    f.text(o[0] - 6, o[1] + 42, "0", size=34), f.text(440, 352, "<i>R</i><sub>1</sub>", size=34), f.text(380, 220, "<i>R</i><sub>2</sub>", size=34)
    return f


def square_abcd_centre_charge():
    """Square ABCD with 10 uC at the centre; 2 uC at corner A."""
    f = Figure(560, 480)
    f.rect(180, 70, 300, 340), f.dot(330, 220, r=6)
    f.text(150, 54, "A", size=36), f.text(510, 54, "B", size=36), f.text(150, 456, "D", size=36), f.text(510, 456, "C", size=36)
    f.text(80, 150, "2 μC", size=36), f.text(330, 290, "10 μC", size=36)
    return f


def surfaces_a_b():
    """Surface A (horizontal ellipse) encloses +2q and -q; surface B (vertical ellipse) encloses -q and +3q."""
    f = Figure(640, 520)
    ellipse(f, 240, 300, 210, 90), ellipse(f, 470, 280, 120, 240)
    f.text(140, 316, "+2<i>q</i>", size=36), f.text(400, 316, "−<i>q</i>", size=36), f.text(470, 120, "+3<i>q</i>", size=36)
    f.text(130, 180, "A", size=36), f.text(620, 180, "B", size=36)
    return f


def q1_origin_q2_x_axis():
    """q1 at the origin, q2 on the x-axis a distance L away."""
    f = Figure(640, 440)
    o = (120, 340)
    f.line(20, o[1], 600, o[1], arrow=True), f.line(o[0], 420, o[0], 30, arrow=True)
    f.dot(*o, r=10), f.dot(360, o[1], r=10), f.dim(o[0] + 10, 380, 350, 380)
    f.text(76, 46, "Y", size=40), f.text(616, 352, "X", size=40)
    f.text(60, 394, "<i>q</i><sub>1</sub>", size=36), f.text(360, 300, "<i>q</i><sub>2</sub>", size=36), f.text(240, 426, "<i>L</i>", size=36)
    return f


def cylinder_c_b_a_small():
    """A closed cylinder: plane face C on the left, curved surface B, plane face A on the right."""
    f = Figure(700, 200)
    cylinder(f, 60, 640, 100, 66, rx=30)
    f.text(60, 114, "C", size=36), f.text(340, 114, "B", size=36), f.text(640, 114, "A", size=36)
    return f


def cylinder_a_c_b():
    """A closed cylinder: plane face A on the left and B on the right (arrows pointing outward from them), curved surface C."""
    f = Figure(700, 240)
    cylinder(f, 100, 600, 130, 76, rx=30)
    f.add(f'<path d="M100,150 Q60,150 50,96" stroke-width="3"/>'), f.arrowhead(50, 92, -100, size=16)
    f.add(f'<path d="M600,150 Q640,150 650,96" stroke-width="3"/>'), f.arrowhead(650, 92, -80, size=16)
    f.text(40, 70, "A", size=34), f.text(660, 70, "B", size=34), f.text(350, 144, "C", size=34)
    return f


def square_2q_charges_point_a():
    """Square of side 2L: +2q at the two left corners, -2q at the two right corners; A is midway between the +2q charges, with dashed lines to the -2q charges."""
    f = Figure(560, 520)
    l, r, t, b = 110, 480, 60, 440
    a = (l, (t + b) / 2)
    f.rect(l, t, r - l, b - t)
    f.line(*a, r, t, width=2.5, dash="12 8"), f.line(*a, r, b, width=2.5, dash="12 8")
    f.dim(70, t, 70, a[1] - 14), f.dim(70, a[1] + 14, 70, b)
    f.text(56, 40, "+2<i>q</i>", size=32), f.text(56, 498, "+2<i>q</i>", size=32)
    f.text(520, 50, "−2<i>q</i>", size=32), f.text(520, 482, "−2<i>q</i>", size=32)
    f.text(130, a[1] + 12, "A", size=32, anchor="start"), f.text(46, 160, "<i>L</i>", size=32), f.text(46, 360, "<i>L</i>", size=32)
    return f


def square_three_charges():
    """Square of side a: q1 = q at the top-left corner, q2 = q at the top-right, q3 = q at the bottom-right."""
    f = Figure(600, 480)
    l, r, t, b = 120, 420, 70, 410
    f.rect(l, t, r - l, b - t)
    f.dim(l + 4, 130, r - 4, 130), f.dim(500, t + 10, 500, b - 10)
    f.line(r, t, 500, t, width=1.5, dash="4 6"), f.line(r, b, 500, b, width=1.5, dash="4 6")
    f.text(70, 50, "<i>q</i><sub>1</sub> = <i>q</i>", size=32), f.text(500, 50, "<i>q</i><sub>2</sub> = <i>q</i>", size=32)
    f.text(500, 456, "<i>q</i><sub>3</sub> = <i>q</i>", size=32)
    f.text(270, 120, "<i>a</i>", size=32, halo=True), f.text(520, 250, "<i>a</i>", size=32, anchor="start")
    return f


def molecule_models():
    """(a) water: O with two H atoms at an angle; (b) N2: two touching N atoms; (c) CO2: O-C-O in a straight line; (d) H2: two touching H atoms."""
    f = Figure(620, 460)

    def atom(x, y, r, label, size=26):
        f.circle(x, y, r, fill="#fff"), f.text(x, y + size * 0.35, label, size=size)

    # (a)
    f.circle(160, 110, 66, fill="#fff"), f.text(160, 84, "O", size=26)
    atom(110, 175, 26, "H"), atom(210, 175, 26, "H")
    f.line(160, 90, 118, 166, width=2, dash="5 5"), f.line(160, 90, 202, 166, width=2, dash="5 5"), f.line(126, 172, 194, 172, width=2, dash="5 5")
    f.text(40, 44, "(a)", size=28)
    # (b)
    atom(470, 80, 32, "N"), atom(470, 144, 32, "N"), f.line(470, 70, 470, 132, width=2)
    f.text(380, 44, "(b)", size=28)
    # (c)
    f.circle(160, 340, 66, fill="#fff"), f.text(160, 350, "C", size=26)
    atom(108, 286, 26, "O"), atom(214, 396, 26, "O")
    f.line(116, 296, 206, 386, width=2, dash="5 5")
    f.text(40, 270, "(c)", size=28)
    # (d)
    atom(450, 340, 32, "H"), atom(512, 340, 32, "H"), f.line(450, 340, 512, 340, width=2, dash="5 5")
    f.text(380, 270, "(d)", size=28)
    return f


def right_triangle_q_2q():
    """Isosceles right triangle with legs l: Q at the right angle, -2q at the other two corners."""
    f = Figure(500, 440)
    q, top, right = (80, 380), (80, 60), (400, 380)
    f.path([q, top, right], close=True), f.right_angle(q[0], q[1], 1, -1, size=22)
    f.text(80, 40, "−2<i>q</i>", size=34), f.text(440, 392, "−2<i>q</i>", size=34, anchor="start")
    f.text(56, 392, "<i>Q</i>", size=34, anchor="end"), f.text(56, 228, "<i>l</i>", size=34), f.text(240, 426, "<i>l</i>", size=34)
    return f


def flux_surfaces():
    """Four closed surfaces of different shapes (a)-(d), each enclosing the same charge +q."""
    f = Figure(640, 520)
    shapes = {
        "a": "M100,60 C140,40 160,70 150,110 C190,140 190,200 150,210 C110,220 90,180 100,140 C70,130 60,80 100,60 Z",
        "b": "M440,60 C510,40 560,90 540,150 C530,210 460,220 430,190 C390,160 390,80 440,60 Z",
        "c": "M110,300 C150,290 160,320 150,380 C145,430 110,450 100,420 C90,380 90,320 110,300 Z",
        "d": "M430,300 C470,320 490,280 520,300 C560,320 530,350 560,370 C590,400 540,420 520,400 C500,430 470,420 470,400 "
             "C450,430 420,420 430,390 C400,380 400,340 430,330 C410,320 410,300 430,300 Z",
    }
    centres = {"a": (130, 170), "b": (470, 140), "c": (125, 380), "d": (480, 370)}
    labels = {"a": (130, 260), "b": (470, 260), "c": (125, 490), "d": (480, 490)}
    for k, d in shapes.items():
        f.add(f'<path d="{d}" stroke-width="3"/>')
        f.dot(*centres[k], r=4), f.text(centres[k][0] + 8, centres[k][1] + 10, "+<i>q</i>", size=26, anchor="start")
        f.text(*labels[k], f"({k})", size=28)
    return f


FIGURES = {
    "PYQ-PHY-9371dc25b3a2": hexagon_charges,
    "PYQ-PHY-3c278146bb29": charge_moves_on_arc,
    "PYQ-PHY-689887524a8c": two_charges_one_metre,
    "PYQ-PHY-75d9d1fdf721": cylinder_c_b_a,
    "PYQ-PHY-abf655379669": triangle_q_q_q,
    "PYQ-PHY-2239c8c3c3c4": square_q_q_diagonals,
    "PYQ-PHY-e5106e91639c": half_rings_r1_r2,
    "PYQ-PHY-4dbad3fe4b34": square_abcd_centre_charge,
    "PYQ-PHY-54c1fd3b4129": surfaces_a_b,
    "PYQ-PHY-1b8ae73364ca": q1_origin_q2_x_axis,
    "PYQ-PHY-35d8b3ddb2c7": cylinder_c_b_a_small,
    "PYQ-PHY-b09127992c36": cylinder_a_c_b,
    "PYQ-PHY-6a6cf1875a95": square_2q_charges_point_a,
    "PYQ-PHY-73996032ba58": square_three_charges,
    "PYQ-PHY-7ab1cbc0fd9c": molecule_models,
    "PYQ-PHY-48f11f708341": right_triangle_q_2q,
    "PYQ-PHY-b30e10f1c0bf": hexagon_charges,
    "PYQ-PHY-5e624436d922": flux_surfaces,
}
