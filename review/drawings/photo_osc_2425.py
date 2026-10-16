"""Physics (MHT-CET 2024-25): photoelectric effect graphs and oscillations."""

import math

from figlib import Figure, coil


def photocurrent(f, ox, oy, stop, sat, scale_v=1.0, rise=60):
    """A photocurrent curve starting at the retarding potential `stop` (pixels left of the origin) and levelling at `sat` (pixels above)."""
    x0 = ox - stop
    f.add(f'<path d="M{x0},{oy} C{x0 + stop * 0.6},{oy - sat * 0.4} {ox - 10},{oy - sat} {ox + rise},{oy - sat} L{ox + 240},{oy - sat}" stroke-width="3"/>')


def stopping_potential_a_b():
    """Stopping potential against frequency: two parallel lines, A meeting the frequency axis before B."""
    f = Figure(560, 380)
    ox, oy = 120, 330
    f.axes(ox, oy, 420, 300, xlabel="<i>ν</i>", size=34)
    f.line(310, oy, 380, 40), f.line(380, oy, 450, 40)
    f.text(380, 40, "A", size=36, anchor="end"), f.text(470, 40, "B", size=36, anchor="start")
    with f.rotated(-90, 60, 190):
        f.text(60, 190, "Stopping potential", size=32)
    return f


def photocurrent_same_frequency():
    """Photocurrent against anode potential for curves a, b, c, d: all start at the same retarding potential; saturation currents Ia < Ib < Ic < Id."""
    f = Figure(620, 360)
    ox, oy = 240, 260
    f.line(20, oy, 600, oy, arrow=True), f.line(ox, 330, ox, 40, arrow=True)
    for name, sat in (("a", 60), ("b", 100), ("c", 135), ("d", 170)):
        photocurrent(f, ox, oy, 130, sat, rise=10)
        f.text(ox + 270, oy - sat + 10, f"<i>I</i><sub>{name}</sub>", size=28, anchor="start")
    f.text(196, 246, "a", size=24), f.text(176, 222, "b", size=24), f.text(160, 204, "c", size=24), f.text(142, 186, "d", size=24)
    f.text(ox, 30, "Photocurrent (<i>I</i>)", size=28), f.text(ox + 10, oy + 34, "O", size=28, anchor="start")
    f.line(70, 290, 20, 290, arrow=True), f.text(80, 298, "Retarding", size=28, anchor="start"), f.text(80, 334, "Potential", size=28, anchor="start")
    f.line(320, 320, 370, 320, arrow=True), f.text(400, 298, "Accelerating", size=28, anchor="start"), f.text(400, 334, "Potential", size=28, anchor="start")
    return f


def stopping_potential_x_y():
    """Stopping potential Vs against frequency: parallel lines X (threshold v0) and Y (threshold v0')."""
    f = Figure(620, 400)
    ox, oy = 80, 300
    f.line(20, oy, 600, oy), f.line(ox, 360, ox, 20)
    f.line(270, oy, 400, 40), f.line(420, oy, 560, 40)
    f.text(410, 40, "X", size=34, anchor="start"), f.text(568, 40, "Y", size=34, anchor="start")
    f.text(270, 340, "<i>ν</i><sub>0</sub>", size=32), f.text(420, 340, "<i>ν</i>′<sub>0</sub>", size=32)
    f.text(40, 180, "<i>V</i><sub>s</sub>", size=32), f.line(46, 120, 46, 70, arrow=True)
    f.line(150, 386, 500, 386, arrow=True), f.text(320, 378, "Freq (<i>ν</i>)", size=32, halo=True)
    return f


def photocurrent_same_saturation():
    """Photocurrent against anode potential: curves a, b, c, d reach the same saturation current Ia but start at retarding potentials -V0(1) to -V0(4)."""
    f = Figure(640, 380)
    ox, oy = 300, 290
    f.line(20, oy, 620, oy), f.line(ox, oy, ox, 60)
    for name, stop, lx in (("a", 30, 310), ("b", 90, 270), ("c", 150, 236), ("d", 230, 200)):
        photocurrent(f, ox, oy, stop, 170, rise=40)
        f.text(ox - stop, oy + 40, f"−<i>V</i><sub>0</sub><sup>{['a', 'b', 'c', 'd'].index(name) + 1}</sup>", size=24)
    f.text(330, 210, "a", size=26), f.text(260, 200, "b", size=26), f.text(220, 180, "c", size=26), f.text(180, 160, "d", size=26)
    f.text(560, 128, "<i>I</i><sub>a</sub>", size=28, anchor="start"), f.text(470, 200, "Saturation Current", size=26)
    f.text(ox + 12, oy + 36, "0", size=26, anchor="start"), f.text(ox, 40, "Photo Current (<i>I</i>)", size=26)
    f.text(630, 352, "Accelerating potential →", size=26, anchor="end")
    f.line(110, 368, 60, 368, arrow=True), f.text(116, 376, "Retarding Potential", size=26, anchor="start")
    return f


def ke_frequency_options():
    """Kinetic energy E against frequency: (1) a rising line starting on the frequency axis, (2) a horizontal line, (3) a vertical line, (4) a falling line."""
    f = Figure(760, 220)
    for i, ox in enumerate((40, 230, 420, 610)):
        f.axes(ox, 160, 140, 130, xlabel="<i>ν</i>", ylabel="E", size=24)
        f.text(ox + 70, 210, f"({i + 1})", size=26)
    f.line(80, 160, 140, 50)
    f.line(230, 60, 360, 60)
    f.line(510, 50, 510, 160)
    f.line(610, 60, 730, 160)
    return f


def stopping_potential_two_points():
    """Stopping potential against frequency of radiation: a line from v0 through C (v1, V1) and D (v2, V2)."""
    f = Figure(640, 400)
    ox, oy = 150, 300
    f.line(ox, oy, 560, oy), f.line(ox, oy, ox, 40)
    x0 = 260
    pts = {"C": (390, 200), "D": (530, 90)}
    f.line(x0, oy, 600, oy - (600 - x0) * (100 / 130))
    for name, (x, y) in pts.items():
        f.line(ox, y, x, y, width=2, dash="10 6"), f.line(x, y, x, oy, width=2, dash="10 6")
        f.text(x - 6, y - 12, name, size=28, anchor="end")
    f.text(ox + 20, 216, "<i>V</i><sub>1</sub>", size=26, anchor="start"), f.text(ox + 20, 106, "<i>V</i><sub>2</sub>", size=26, anchor="start")
    f.text(x0, oy + 30, "<i>ν</i><sub>0</sub>", size=26), f.text(390, oy + 30, "<i>ν</i><sub>1</sub>", size=26), f.text(530, oy + 30, "<i>ν</i><sub>2</sub>", size=26)
    f.text(70, 180, "Stopping", size=26), f.text(70, 212, "potential", size=26), f.line(70, 140, 70, 100, arrow=True)
    f.line(340, 370, 390, 370, arrow=True), f.text(396, 378, "Frequency of radiation", size=26, anchor="start")
    return f


def photocurrent_abcd_mixed():
    """Photocurrent against potential: a and b level off at different currents and start at different retarding potentials (b further);
    c starts where b does; c and d reach the same saturation current."""
    f = Figure(640, 400)
    ox, oy = 280, 330
    f.line(20, oy, 620, oy, arrow=True), f.line(ox, oy, ox, 50, arrow=True)
    photocurrent(f, ox, oy, 80, 110, rise=60)     # a
    photocurrent(f, ox, oy, 150, 160, rise=60)    # b
    photocurrent(f, ox, oy, 150, 210, rise=80)    # c
    photocurrent(f, ox, oy, 230, 210, rise=80)    # d
    f.text(420, 200, "a", size=28), f.text(420, 150, "b", size=28), f.text(178, 290, "c", size=28), f.text(110, 270, "d", size=28)
    f.text(ox, 36, "photocurrent", size=30)
    f.text(320, 386, "(<i>V</i>) → accelerating potential", size=28)
    return f


def vspring(f, x, y1, y2, turns=6, radius=13):
    """A spring hanging from y1 down to y2 at x."""
    f.line(x, y1, x, y1 + 14), f.line(x, y2 - 14, x, y2)
    with f.rotated(90, x, (y1 + y2) / 2):
        coil(f, x - (y2 - y1) / 2 + 14, x + (y2 - y1) / 2 - 14, (y1 + y2) / 2, turns=turns, radius=radius)


def ceiling(f, x1, x2, y):
    f.line(x1, y, x2, y, width=3)
    for x in range(int(x1) + 6, int(x2), 14):
        f.line(x, y, x + 10, y - 12, width=2)


def springs_abc(label_k=True):
    """Identical springs K with mass m: (a) one spring; (b) two springs in series; (c) two springs side by side (parallel)."""
    f = Figure(700, 420)
    ceiling(f, 40, 200, 30), vspring(f, 120, 30, 160), f.rect(80, 160, 80, 50), f.text(120, 194, "<i>m</i>", size=28)
    f.text(140, 100, "<i>K</i>", size=28, anchor="start"), f.text(120, 400, "fig. (a)", size=28)
    ceiling(f, 260, 420, 30), vspring(f, 340, 30, 160), vspring(f, 340, 160, 300), f.rect(300, 300, 80, 50), f.text(340, 334, "<i>m</i>", size=28)
    f.text(360, 100, "<i>K</i>", size=28, anchor="start"), f.text(360, 240, "<i>K</i>", size=28, anchor="start"), f.text(340, 400, "fig. (b)", size=28)
    ceiling(f, 480, 660, 30), vspring(f, 520, 30, 160), vspring(f, 620, 30, 160), f.rect(500, 160, 140, 50), f.text(570, 194, "<i>m</i>", size=28)
    f.text(498, 100, "<i>K</i>", size=28, anchor="end"), f.text(642, 100, "<i>K</i>", size=28, anchor="start"), f.text(570, 400, "fig. (c)", size=28)
    return f


def spring_with_three_masses():
    """A spring hangs from a ceiling with masses 100 g, 300 g and 500 g stacked below it (500 g at the bottom)."""
    f = Figure(400, 520)
    ceiling(f, 60, 220, 30), vspring(f, 140, 30, 220, turns=8, radius=20)
    for i, label in enumerate(("100 g", "300 g", "500 g")):
        f.rect(60, 220 + i * 90, 200, 90), f.text(160, 276 + i * 90, label, size=30)
    return f


def mass_on_two_strings():
    """Mass m hangs at R from two strings of length L tied to fixed points P and Q, 2d apart."""
    f = Figure(560, 480)
    p, q, r = (40, 40), (520, 40), (280, 380)
    f.line(*p, *q, width=2, dash="10 6"), f.line(*p, *r, width=2.5), f.line(*q, *r, width=2.5)
    f.rect(250, 380, 60, 80)
    for y in (396, 412, 428, 444):
        f.line(250, y, 310, y, width=2)
    f.text(28, 30, "P", size=30), f.text(536, 30, "Q", size=30), f.text(280, 26, "2<i>d</i>", size=30)
    f.text(140, 210, "<i>L</i>", size=30), f.text(420, 210, "<i>L</i>", size=30), f.text(304, 370, "R", size=30, anchor="start")
    f.text(320, 470, "<i>m</i>", size=30, anchor="start")
    return f


def ball_on_curved_surface():
    """A small ball rolling on a frictionless concave curved surface."""
    f = Figure(640, 440)
    f.add('<path d="M30,180 Q330,420 600,170" stroke-width="4"/>')
    f.circle(430, 200, 46, width=4), f.dot(430, 200, r=10)
    f.line(430, 60, 430, 140, arrow=True), f.text(430, 46, "Ball", size=32)
    f.line(520, 340, 470, 278, arrow=True), f.text(630, 380, "Frictionless", size=32, anchor="end"), f.text(630, 420, "Curved surface", size=32, anchor="end")
    return f


def mass_between_two_springs():
    """Mass m between two identical springs S1 and S2 (constant K each), fixed to walls on both sides."""
    f = Figure(760, 200)
    y = 100
    f.line(30, 20, 30, 180, width=4), f.line(730, 20, 730, 180, width=4)
    for yy in range(28, 180, 18):
        f.line(30, yy, 14, yy + 14, width=2), f.line(730, yy, 746, yy + 14, width=2)
    f.line(30, y, 100, y), coil(f, 100, 230, y, turns=7, radius=13), f.line(230, y, 330, y)
    f.rect(330, 70, 90, 60), f.text(375, 110, "<i>m</i>", size=30)
    f.line(420, y, 540, y), coil(f, 540, 670, y, turns=7, radius=13), f.line(670, y, 730, y)
    f.text(165, 56, "S<sub>1</sub>", size=28), f.text(605, 56, "S<sub>2</sub>", size=28)
    f.text(165, 160, "<i>K</i>", size=28), f.text(605, 160, "<i>K</i>", size=28)
    return f


FIGURES = {
    "PYQ-PHY-98ff62869ab8": stopping_potential_a_b,
    "PYQ-PHY-ebb71146b357": photocurrent_same_frequency,
    "PYQ-PHY-8593e3565034": stopping_potential_x_y,
    "PYQ-PHY-4fbf56afea24": photocurrent_same_saturation,
    "PYQ-PHY-fb2ba73a1e1e": ke_frequency_options,
    "PYQ-PHY-3cb01e06dc67": stopping_potential_two_points,
    "PYQ-PHY-1c6368b92484": photocurrent_abcd_mixed,
    "PYQ-PHY-8268be47bb55": springs_abc,
    "PYQ-PHY-8c9aff3f5d8b": spring_with_three_masses,
    "PYQ-PHY-ce40aea40a97": mass_on_two_strings,
    "PYQ-PHY-65b0a60697b3": ball_on_curved_surface,
    "PYQ-PHY-823af9d2aa18": mass_between_two_springs,
    "PYQ-PHY-787350dfe567": springs_abc,
}
