"""Physics: kinematics, laws of motion, moving charges and magnetism, oscillations (part 1)."""

import math

from figlib import Figure, coil, mid_arrow


def slant_coil(f, p1, p2, turns=8, radius=13, lead=14):
    """A spring between two points in any direction."""
    (x1, y1), (x2, y2) = p1, p2
    length = math.hypot(x2 - x1, y2 - y1)
    with f.rotated(round(math.degrees(math.atan2(y2 - y1, x2 - x1)), 2), x1, y1):
        f.line(x1, y1, x1 + lead, y1), coil(f, x1 + lead, x1 + length - lead, y1, turns=turns, radius=radius)
        f.line(x1 + length - lead, y1, x1 + length, y1)


def ceiling(f, x1, x2, y, step=14):
    f.line(x1, y, x2, y, width=4)
    for x in range(int(x1) + 4, int(x2), step):
        f.line(x, y, x + 12, y - 16, width=2)


def plane(f, x, y, angle):
    """A small aircraft seen from the side, flying along `angle` (degrees above the horizontal)."""
    with f.rotated(-angle, x, y):
        f.path([(x + 8, y - 6), (x - 16, y - 34), (x - 4, y - 6)], close=True, fill="#fff", width=2.5)
        f.path([(x + 8, y + 6), (x - 16, y + 34), (x - 4, y + 6)], close=True, fill="#fff", width=2.5)
        f.path([(x - 30, y - 3), (x - 42, y - 16), (x - 34, y + 3)], close=True, fill="#fff", width=2.5)
        f.add(f'<ellipse cx="{x}" cy="{y}" rx="36" ry="9" stroke-width="3" fill="#fff"/>')


def two_planes():
    """Aircraft A climbs at 30 degrees and aircraft B at 60 degrees to the horizontal, in the same vertical plane."""
    f = Figure(660, 440)
    g = 408
    f.line(10, g, 600, g)
    f.line(10, g, 440, g - 248, width=2, dash="10 8"), f.arrowhead(452, g - 255, -30, size=14)
    f.line(500, g, 556, g - 97, width=2, dash="10 8"), f.arrowhead(562, g - 107, -60, size=14)
    plane(f, 498, 122, 30), plane(f, 590, 262, 60)
    f.arc(10, g, 96, -30, 0), f.arc(500, g, 46, -60, 0)
    f.text(128, g - 14, "30°", size=28), f.text(574, g - 14, "60°", size=28)
    f.text(540, 50, "A", size=30), f.text(628, 218, "B", size=30)
    return f


def velocity_time_steps():
    """Velocity against time: 8 m/s for 0-2 s, -4 for 2-4 s, 4 for 4-8 s and -4 for 8-10 s."""
    f = Figure(660, 450)
    ox, oy, ux, uy = 168, 236, 35, 24.5

    def p(t, v):
        return ox + ux * t, oy - uy * v

    f.line(ox, 30, ox, 432), f.line(ox, oy, 585, oy)
    f.polyline([p(0, 8), p(2, 8), p(2, -4), p(4, -4), p(4, 4), p(8, 4), p(8, -4), p(10, -4), p(10, 0)])
    for v in (8, 6, 4, 2, -2, -4, -6):
        f.line(ox - 8, oy - uy * v, ox, oy - uy * v, width=2)
        f.text(ox - 16, oy - uy * v + 9, str(v).replace("-", "−"), size=24, anchor="end")
    for t in (2, 4, 6, 8, 10):
        f.line(ox + ux * t, oy, ox + ux * t, oy + 8, width=2)
        f.text(ox + ux * t - (12 if t in (2, 4, 8) else -12 if t == 10 else 0), oy + 32, str(t), size=24, halo=True)
    f.text(ox - 16, oy + 9, "0", size=24, anchor="end")
    f.text(72, oy + 9, "<i>v</i> (m s<sup>−1</sup>)", size=24), f.text(430, 392, "time (s)", size=24)
    return f


def three_blocks_pulled():
    """Blocks of 2 kg, 8 kg and 12 kg joined by strings (tensions T2 and T1) and pulled by F on a frictionless surface."""
    f = Figure(680, 230)
    f.line(92, 100, 650, 100)
    for x, w, label in ((135, 72, "2 kg"), (292, 72, "8 kg"), (448, 84, "12 kg")):
        f.block(x, 52, w, 48, label, size=24)
    mid_arrow(f, 207, 76, 292, 76, at=0.62), mid_arrow(f, 364, 76, 448, 76, at=0.62)
    f.vector(532, 76, 612, 76)
    f.text(250, 44, "<i>T</i><sub>2</sub>", size=26), f.text(406, 44, "<i>T</i><sub>1</sub>", size=26)
    f.text(634, 86, "<i>F</i>", size=28)
    f.vector(68, 150, 104, 108, width=2)
    f.text(22, 176, "frictionless", size=24, anchor="start"), f.text(22, 206, "surface", size=24, anchor="start")
    return f


def three_parallel_wires():
    """Parallel wires A (15 A), C (50 A) and B (10 A), all currents upward; C is x from A and 15 - x from B."""
    f = Figure(540, 450)
    for x, name, current in ((92, "A", "15 A"), (252, "C", "50 A"), (436, "B", "10 A")):
        f.line(x, 62, x, 408), f.arrowhead(x, 138, 270, size=18)
        f.text(x, 46, name, size=30)
        f.text(x - 18 if name != "B" else x + 18, 172, current, size=28, anchor="end" if name != "B" else "start")
    f.dim(96, 366, 248, 366), f.dim(256, 366, 432, 366)
    f.text(172, 402, "<i>x</i>", size=28, halo=True), f.text(344, 402, "15 − <i>x</i>", size=28, halo=True)
    return f


def square_loop_near_wire():
    """Wire XY carrying I2 upward; square loop ABCD of side L carrying I1 clockwise, its side AB a distance L/3 from the wire."""
    f = Figure(640, 470)
    f.line(88, 36, 88, 436), f.arrowhead(88, 200, 270, size=18)
    f.text(112, 52, "Y", size=30), f.text(112, 436, "X", size=30), f.text(52, 216, "<i>I</i><sub>2</sub>", size=30)
    b, c, d, a = (190, 98), (452, 98), (452, 350), (190, 350)
    f.path([b, c, d, a], close=True)
    f.arrowhead(330, 98, 0, size=18), f.arrowhead(452, 232, 90, size=18)
    f.arrowhead(312, 350, 180, size=18), f.arrowhead(190, 216, 270, size=18)
    f.vector(190, 138, 138, 138, width=2.5), f.vector(452, 138, 504, 138, width=2.5)
    f.text(176, 82, "B", size=30), f.text(470, 82, "C", size=30), f.text(470, 382, "D", size=30), f.text(172, 382, "A", size=30)
    f.text(330, 70, "<i>I</i><sub>1</sub>", size=30)
    f.dim(92, 318, 186, 318), f.fraction(139, 276, "<i>L</i>", "3", size=26)
    f.dim(520, 102, 520, 346), f.text(548, 234, "<i>L</i>", size=30), f.dim(194, 408, 448, 408), f.text(322, 448, "<i>L</i>", size=30)
    return f


def wire_with_quarter_arc():
    """Current I comes down the straight wire AB, round a quarter circle BC of radius r centred at O, and out along CD."""
    f = Figure(500, 470)
    o, r = (232, 232), 152
    f.line(80, 44, 80, 232, width=4), f.add(f'<path d="M80,232 A{r},{r} 0 0 0 232,384" stroke-width="4"/>')
    f.line(232, 384, 430, 384, width=4)
    f.line(80, 232, *o, width=2.5), f.line(*o, 232, 384, width=2.5), f.line(*o, 232 - 107.5, 232 + 107.5, width=2.5)
    f.arrowhead(80, 130, 90, size=20), f.arrowhead(232 - 112, 232 + 104, 44, size=20), f.arrowhead(340, 384, 0, size=20)
    f.text(56, 52, "A", size=32), f.text(54, 242, "B", size=32), f.text(256, 226, "O", size=32)
    f.text(232, 428, "C", size=32), f.text(448, 418, "D", size=32)
    f.text(48, 138, "<i>I</i>", size=32), f.text(84, 356, "<i>I</i>", size=32), f.text(340, 432, "<i>I</i>", size=32)
    f.text(152, 214, "<i>r</i>", size=30), f.text(256, 320, "<i>r</i>", size=30), f.text(176, 268, "<i>r</i>", size=30)
    return f


def amperian_loop_three_wires():
    """Loop P encloses a 3 A wire (current up) and a 1.5 A wire (current down); a 1 A wire (down) lies outside."""
    f = Figure(470, 460)
    f.add('<ellipse cx="184" cy="222" rx="108" ry="74" stroke-width="3"/>')
    for x, up, label, side in ((148, True, "3 A", "end"), (220, False, "1.5 A", "start"), (348, False, "1 A", "start")):
        f.line(x, 46, x, 418), f.arrowhead(x, 96 if up else 112, 270 if up else 90, size=18)
        f.text(x - 18 if side == "end" else x + 18, 112, label, size=28, anchor=side)
    f.text(46, 232, "P", size=28)
    return f


def two_bent_wires():
    """Wire A-B-C turns down at B and wire D-E-T turns up at E; O is midway between B and E, which are a apart."""
    f = Figure(640, 470)
    b, e = (218, 212), (368, 212)
    f.line(22, 212, 76, 212, width=2, dash="3 6"), mid_arrow(f, 76, 212, *b, at=0.55)
    mid_arrow(f, *b, 218, 372, at=0.7), f.line(218, 372, 218, 440, width=2, dash="3 6")
    f.line(572, 212, 508, 212, width=2, dash="3 6"), mid_arrow(f, 508, 212, *e, at=0.6)
    mid_arrow(f, *e, 368, 62, at=0.6), f.line(368, 62, 368, 20, width=2, dash="3 6")
    f.dot(293, 212, r=4)
    f.dim(222, 144, 364, 144), f.dim(222, 308, 364, 308)
    f.text(293, 134, "<i>a</i>", size=26, halo=True), f.text(293, 298, "<i>a</i>", size=26, halo=True)
    f.text(84, 196, "A", size=26), f.text(222, 194, "B", size=26), f.text(196, 396, "C", size=26)
    f.text(368, 244, "E", size=26), f.text(506, 244, "D", size=26), f.text(346, 70, "T", size=26)
    f.text(293, 246, "O", size=26)
    f.text(142, 186, "<i>I</i>", size=26), f.text(196, 306, "<i>I</i>", size=26), f.text(432, 244, "<i>I</i>", size=26)
    f.text(386, 142, "<i>I</i>", size=26)
    return f


def two_wires_cd_ab():
    """Wire CD (current to the right) held a distance r above wire AB (current to the left)."""
    f = Figure(680, 220)
    f.line(78, 62, 505, 62, width=4), f.arrowhead(300, 62, 0, size=22)
    f.line(78, 154, 505, 154, width=4), f.arrowhead(270, 154, 180, size=22)
    f.text(46, 74, "C", size=34), f.text(532, 74, "D", size=34), f.text(46, 166, "A", size=34), f.text(532, 166, "B", size=34)
    f.dim(578, 66, 578, 150), f.text(612, 120, "<i>r</i>", size=34)
    return f


def four_crossed_springs():
    """A block m hung from the ceiling by four identical springs k meeting at a common joint."""
    f = Figure(470, 470)
    ceiling(f, 10, 448, 46)
    joint = (230, 216)
    for p in ((52, 50), (398, 50)):
        slant_coil(f, p, joint, turns=9, radius=13)
    for p in ((62, 384), (398, 384)):
        slant_coil(f, joint, p, turns=9, radius=13)
    f.hatch([(24, 386), (440, 386), (440, 448), (24, 448)], spacing=11, width=1.2)
    f.rect(24, 386, 416, 62), f.rect(206, 398, 48, 40, fill="#fff", width=0), f.text(230, 430, "<i>m</i>", size=32)
    for x, y in ((52, 50), (398, 50), joint, (62, 384), (398, 384)):
        f.circle(x, y, 6, fill="#fff", width=2.5)
    f.text(188, 108, "<i>k</i>", size=32), f.text(378, 150, "<i>k</i>", size=32)
    f.text(98, 280, "<i>k</i>", size=32), f.text(366, 280, "<i>k</i>", size=32)
    return f


def mass_between_2k_and_k():
    """A mass m on a floor between two walls, held by a spring 2k on the left and a spring k on the right."""
    f = Figure(660, 230)
    f.wall(48, 28, 178, "left"), f.wall(598, 28, 178, "right"), f.line(48, 178, 598, 178)
    f.line(48, 118, 92, 118), coil(f, 92, 232, 118, turns=6, radius=20), f.line(232, 118, 274, 118)
    f.block(274, 56, 118, 122, "<i>m</i>", size=40)
    f.line(392, 118, 432, 118), coil(f, 432, 556, 118, turns=5, radius=20), f.line(556, 118, 598, 118)
    f.text(160, 58, "2<i>k</i>", size=34), f.text(494, 62, "<i>k</i>", size=34)
    return f


def three_spring_systems():
    """Mass m hung from (a) one spring, (b) two springs in series, (c) two springs in parallel."""
    f = Figure(480, 470)

    def vspring(x, y1, y2, turns):
        with f.rotated(90, x, y1):
            coil(f, x, x + (y2 - y1), y1, turns=turns, radius=12)

    for x in (80, 228, 376):
        ceiling(f, x - 42, x + 42, 112, step=10)
    f.line(80, 112, 80, 168), vspring(80, 168, 256, 6), f.line(80, 256, 80, 330)                    # (a)
    f.line(228, 112, 228, 136), vspring(228, 136, 222, 6), f.line(228, 222, 228, 238)               # (b)
    vspring(228, 238, 318, 6), f.line(228, 318, 228, 330)
    for x in (352, 400):                                                                            # (c)
        f.line(x, 112, x, 168), vspring(x, 168, 256, 6), f.line(x, 256, x, 330)
    for x, name in ((80, "a"), (228, "b"), (376, "c")):
        f.block(x - 32, 330, 64, 42, "<i>m</i>", size=26)
        f.text(x, 428, f"Fig. ({name})", size=26)
    return f


FIGURES = {
    "PYQ-PHY-85ba68fa95b4": two_planes,
    "PYQ-PHY-bc6fddb86dc4": velocity_time_steps,
    "PYQ-PHY-e2582d5a3160": three_blocks_pulled,
    "PYQ-PHY-0aa00bd01250": three_parallel_wires,
    "PYQ-PHY-1550b231663d": square_loop_near_wire,
    "PYQ-PHY-5c3c165e8bbd": wire_with_quarter_arc,
    "PYQ-PHY-833e7143bf34": amperian_loop_three_wires,
    "PYQ-PHY-c253be58a7c9": two_bent_wires,
    "PYQ-PHY-c83448f2d65f": two_wires_cd_ab,
    "PYQ-PHY-1b09905ffeb6": four_crossed_springs,
    "PYQ-PHY-48aa68cb48d0": mass_between_2k_and_k,
    "PYQ-PHY-56394f0c105d": three_spring_systems,
}
