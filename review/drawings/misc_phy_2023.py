"""Physics (MHT-CET 2020-23): photoelectric graphs, oscillations, thermodynamics, atoms, circular motion,
centre of mass, optics and force-time graphs."""

import math

from figlib import Figure, coil


def ceiling(f, x1, x2, y):
    f.line(x1, y, x2, y, width=3)
    for x in range(int(x1) + 6, int(x2), 16):
        f.line(x, y, x + 12, y - 14, width=2)


def vspring(f, x, y1, y2, turns=6, radius=12):
    """A spring hanging at x from y1 down to y2."""
    f.line(x, y1, x, y1 + 12), f.line(x, y2 - 12, x, y2)
    with f.rotated(90, x, (y1 + y2) / 2):
        coil(f, x - (y2 - y1) / 2 + 12, x + (y2 - y1) / 2 - 12, (y1 + y2) / 2, turns=turns, radius=radius)


def energy_levels():
    """Levels at 0, -2 eV, -4.5 eV and -10 eV; transitions A (0 to -2), B (0 to -4.5), C (-2 to -4.5), D (-2 to -10)."""
    f = Figure(640, 300)
    ys = {0: 40, -2: 100, -4.5: 170, -10: 260}
    for e, y in ys.items():
        f.line(20, y, 470, y, width=3)
        f.text(490, y + 12, "0" if e == 0 else f"− {abs(e):g} eV", size=36, anchor="start")
    for x, a, b, name in ((70, 0, -2, "A"), (180, 0, -4.5, "B"), (270, -2, -4.5, "C"), (380, -2, -10, "D")):
        f.line(x, ys[a], x, ys[b] - 4, width=3, arrow=True)
        f.text(x - 12, ys[a] + 34, name, size=32, anchor="end")
    return f


def ke_frequency_line():
    """Kinetic energy against frequency: a line crossing the frequency axis, extended (dashed) back to -phi0 on the KE axis."""
    f = Figure(480, 400)
    ox, oy = 80, 250
    f.line(ox, 380, ox, 30, arrow=True), f.line(30, oy, 440, oy, arrow=True)
    f.line(140, oy, 400, 60), f.line(ox, oy + 44, 140, oy, width=2, dash="8 6")
    f.text(40, 130, "KE", size=30), f.text(40, 310, "<i>φ</i><sub>0</sub>", size=30)
    f.text(300, 300, "Frequency <i>ν</i> →", size=30)
    return f


def stopping_potential_p_q():
    """Stopping potential Vs against frequency: parallel lines P (threshold v0) and Q (threshold v0')."""
    f = Figure(440, 420)
    ox, oy = 70, 330
    f.line(ox, oy, ox, 30), f.line(ox, oy, 420, oy)
    f.line(160, oy, 290, 60), f.line(240, oy, 370, 60)
    f.text(298, 52, "P", size=32, anchor="start"), f.text(378, 52, "Q", size=32, anchor="start")
    f.text(ox - 10, oy + 36, "O", size=30, anchor="end"), f.text(160, oy + 36, "<i>ν</i>", size=30), f.text(244, oy + 36, "<i>ν</i>′<sub>0</sub>", size=30)
    f.text(30, 190, "<i>V</i><sub>s</sub>", size=30), f.line(36, 130, 36, 80, arrow=True)
    f.text(220, 404, "<i>ν</i>", size=30), f.line(250, 396, 330, 396, arrow=True)
    return f


def potential_step():
    """Potential energy U against x: U = E for 0 <= x <= 1, zero beyond x = 1."""
    f = Figure(440, 380)
    ox, oy = 70, 320
    f.axes(ox, oy, 340, 280, size=30)
    f.polyline([(ox, 130), (260, 130), (260, oy)])
    f.text(30, 60, "<i>U</i>", size=32), f.text(40, 142, "<i>E</i>", size=32), f.text(50, 360, "0", size=30)
    f.text(260, 362, "1", size=30), f.text(400, 362, "<i>x</i>", size=30)
    return f


def ft_10_then_20():
    """Force (N) against time (s): 10 N from 0 to 0.5 s, then 20 N from 0.5 s to 1.0 s, then zero."""
    f = Figure(560, 400)
    ox, oy = 110, 320
    f.axes(ox, oy, 420, 270, size=28)
    f.polyline([(ox, 200), (260, 200), (260, 100), (380, 100), (380, oy)])
    f.line(260, oy, 260, oy - 8, width=2), f.line(ox - 8, 200, ox + 8, 200, width=2), f.line(ox - 8, 100, ox + 8, 100, width=2)
    f.text(ox - 14, 210, "10", size=28, anchor="end"), f.text(ox - 14, 110, "20", size=28, anchor="end")
    f.text(260, oy + 36, "0.5", size=28), f.text(380, oy + 36, "1.0", size=28)
    f.text(60, 40, "Force", size=28), f.text(56, 72, "(N)", size=28), f.text(480, oy + 36, "Time (s)", size=28)
    return f


def springs_series_parallel():
    """Left: two springs K in series holding mass M. Right: two springs K side by side (parallel) holding mass M."""
    f = Figure(560, 420)
    ceiling(f, 30, 200, 30), vspring(f, 110, 30, 160), vspring(f, 110, 160, 300)
    f.rect(80, 300, 60, 46), f.text(110, 334, "<i>M</i>", size=28)
    f.text(132, 100, "<i>K</i>", size=28, anchor="start"), f.text(132, 240, "<i>K</i>", size=28, anchor="start")
    ceiling(f, 280, 520, 30), vspring(f, 320, 30, 220), vspring(f, 480, 30, 220)
    f.line(320, 220, 320, 260), f.line(480, 220, 480, 260), f.line(320, 260, 480, 260), f.line(400, 260, 400, 300)
    f.rect(370, 300, 60, 46), f.text(400, 334, "<i>M</i>", size=28)
    f.text(342, 130, "<i>K</i>", size=28, anchor="start"), f.text(502, 130, "<i>K</i>", size=28, anchor="start")
    return f


def lens_in_liquid():
    """A vessel filled with liquid (dashed lines) with a convex lens immersed in it."""
    f = Figure(640, 340)
    l, r, t, b = 330, 620, 20, 320
    f.line(l, t, l, b, width=3), f.line(r, t, r, b, width=3), f.line(l, b, r, b, width=3)
    for y in range(40, 310, 22):
        f.line(l + 10, y, r - 10, y, width=2, dash="18 10")
    f.add('<path d="M470,90 Q510,140 470,190 Q430,140 470,90 Z" stroke-width="3" fill="#fff"/>')
    f.line(320, 140, 250, 140, arrow=True), f.text(20, 152, "Convex lens", size=36, anchor="start")
    f.line(400, 250, 250, 250, arrow=True), f.text(110, 262, "Liquid", size=36, anchor="start")
    return f


def pv_process_options():
    """p-V graphs with points pi, pf, vi, vf: (I) a falling curve, (II) a horizontal line A to B, (III) a vertical line A down to B,
    (IV) a curve falling steeply from A, then levelling to B."""
    f = Figure(760, 260)
    for i, ox in enumerate((40, 230, 420, 610)):
        oy = 200
        f.line(ox, oy, ox, 30, arrow=True), f.line(ox, oy, ox + 160, oy, arrow=True)
        f.text(ox - 8, 30, "<i>p</i>", size=22, anchor="end"), f.text(ox + 166, oy + 6, "<i>v</i>", size=22, anchor="start")
        f.text(ox - 8, 56, "<i>p</i><sub>i</sub>", size=20, anchor="end"), f.text(ox - 8, 168, "<i>p</i><sub>f</sub>", size=20, anchor="end")
        f.text(ox + 30, oy + 26, "<i>v</i><sub>i</sub>", size=20), f.text(ox + 130, oy + 26, "<i>v</i><sub>f</sub>", size=20)
        f.text(ox + 80, oy + 56, f"({'I' * (i + 1) if i < 3 else 'IV'})", size=22)
    f.curve(lambda x: 50 + 110 * (1 - math.exp(-(x - 70) / 18)) if x > 70 else 50, 70, 170)
    f.dot(70, 50, r=5), f.dot(170, 160, r=5)
    f.line(260, 50, 360, 50), f.dot(260, 50, r=5), f.dot(360, 50, r=5), f.text(262, 44, "A", size=20), f.text(358, 44, "B", size=20)
    f.line(450, 50, 450, 160), f.dot(450, 50, r=5), f.dot(450, 160, r=5), f.text(462, 56, "A", size=20, anchor="start"), f.text(462, 166, "B", size=20, anchor="start")
    f.curve(lambda x: 160 - 110 * math.exp(-(x - 640) / 14), 640, 740)
    f.dot(640, 50, r=5), f.dot(740, 160, r=5), f.text(652, 56, "A", size=20, anchor="start"), f.text(740, 150, "B", size=20)
    return f


def spring_mass_rotating():
    """A mass m on a spring fixed at O moves in a circle about O with angular speed omega (dashed arc and arrow)."""
    f = Figure(640, 300)
    y = 140
    f.dot(40, y, r=9), f.text(20, y + 12, "O", size=34, anchor="middle")
    f.line(40, y, 120, y), coil(f, 120, 440, y, turns=9, radius=18), f.line(440, y, 520, y)
    f.rect(520, 110, 64, 60), f.text(552, 152, "<i>m</i>", size=32)
    f.add('<path d="M530,20 Q630,140 530,270" stroke-width="2.5" stroke-dasharray="12 8"/>')
    f.arrowhead(560, 228, 120, size=18), f.text(600, 230, "<i>ω</i>", size=32, anchor="start")
    return f


def conical_pendulum():
    """A ball of mass m on a string of length l hangs from a fixed point; the string makes angle theta with the vertical axis,
    tension T along it, and the ball moves in a horizontal circle (dashed ellipse)."""
    f = Figure(440, 420)
    top, ball = (240, 40), (70, 330)
    ceiling(f, 200, 280, 40)
    f.line(*top, *ball, width=2.5), f.line(*top, 240, 330, width=2.5), f.line(*top, 410, 330, width=2, dash="8 6")
    f.add('<ellipse cx="240" cy="330" rx="170" ry="34" stroke-width="2" stroke-dasharray="12 8"/>')
    f.circle(*ball, 14, fill="#fff"), f.circle(240, 330, 12, fill="#fff"), f.line(84, 330, 228, 330, width=2)
    f.arrowhead(140, 210, -59, size=16), f.text(122, 220, "<i>T</i>", size=26, anchor="end")
    f.arc(240, 40, 60, 90, 120, width=2), f.text(222, 112, "<i>θ</i>", size=24), f.text(196, 90, "<i>l</i>", size=26)
    f.text(46, 340, "<i>m</i>", size=26, anchor="end"), f.text(150, 322, "<i>r</i>", size=22)
    return f


def de_broglie_masses():
    """de Broglie wavelength against 1/sqrt(V): lines from the origin for masses m4 (steepest), m3, m2 and m1 (least steep)."""
    f = Figure(500, 400)
    ox, oy = 70, 340
    f.axes(ox, oy, 400, 310, size=28)
    for name, k in (("<i>m</i><sub>4</sub>", 2.4), ("<i>m</i><sub>3</sub>", 1.3), ("<i>m</i><sub>2</sub>", 0.8), ("<i>m</i><sub>1</sub>", 0.5)):
        dx = 320 / (1 + k * k) ** 0.5
        f.line(ox, oy, ox + dx, oy - dx * k), f.text(ox + dx + 14, oy - dx * k, name, size=26, anchor="start")
    f.text(30, 200, "<i>λ</i>", size=30), f.line(36, 150, 36, 110, arrow=True), f.text(ox - 10, oy + 32, "0", size=26)
    f.text(430, 384, "1/√<i>V</i>", size=26)
    return f


def mass_between_four_springs():
    """A block M on a frictionless floor between two walls: springs 2K and 2K in series on the left; springs K and 2K in parallel on the right."""
    f = Figure(760, 260)
    f.rect(20, 40, 24, 200), f.rect(716, 40, 24, 200), f.line(44, 230, 716, 230, width=3)
    f.line(44, 190, 70, 190), coil(f, 70, 180, 190, turns=5, radius=12), f.line(180, 190, 200, 190)
    coil(f, 200, 310, 190, turns=5, radius=12), f.line(310, 190, 330, 190)
    f.text(125, 160, "2<i>K</i>", size=28), f.text(255, 160, "2<i>K</i>", size=28)
    f.rect(330, 100, 200, 130)
    for x in range(330, 530, 16):
        f.line(x, 230, min(x + 130, 530), 230 - min(130, 530 - x), width=1.5)
    f.line(530, 140, 560, 140), f.line(530, 200, 560, 200)
    for y, lab in ((140, "<i>K</i>"), (200, "2<i>K</i>")):
        coil(f, 560, 680, y, turns=5, radius=12), f.line(680, y, 716, y), f.text(620, y - 26, lab, size=28)
    f.text(430, 80, "<i>M</i>", size=30)
    return f


def shm_force_graph():
    """Force F against displacement x: a straight line from (-2, +8) through the origin to (+2, -8), with dashed guides."""
    f = Figure(480, 460)
    o, sx, sy = (240, 220), 50, 18
    f.line(30, o[1], 450, o[1], arrow=True), f.line(o[0], o[1], 30, o[1], arrow=True)
    f.line(o[0], 420, o[0], 30, arrow=True)
    p1, p2 = (o[0] - 2 * sx, o[1] - 8 * sy), (o[0] + 2 * sx, o[1] + 8 * sy)
    f.line(*p1, *p2)
    f.line(p1[0], p1[1], o[0], p1[1], width=2, dash="8 6"), f.line(p1[0], p1[1], p1[0], o[1], width=2, dash="8 6")
    f.line(p2[0], p2[1], o[0], p2[1], width=2, dash="8 6"), f.line(p2[0], p2[1], p2[0], o[1], width=2, dash="8 6")
    f.text(o[0] + 12, p1[1] + 8, "+8", size=26, anchor="start"), f.text(o[0] - 12, p2[1] + 8, "−8", size=26, anchor="end")
    f.text(p1[0], o[1] + 34, "−2", size=26), f.text(p2[0], o[1] - 14, "+2", size=26), f.text(o[0] + 40, o[1] - 14, "+1", size=26)
    f.text(o[0] - 40, o[1] + 34, "−1", size=26)
    f.text(o[0] + 20, 40, "<i>F</i>", size=28, anchor="start"), f.text(o[0] - 20, 420, "−<i>F</i>", size=28, anchor="end")
    f.text(456, o[1] + 10, "<i>X</i>", size=28, anchor="start"), f.text(24, o[1] + 10, "−<i>X</i>", size=28, anchor="end")
    return f


def disc_on_two_springs():
    """A disc (drawn as an ellipse, labelled Disc) rests on two identical vertical springs standing on the floor."""
    f = Figure(440, 420)
    f.add('<ellipse cx="220" cy="70" rx="180" ry="50" stroke-width="3"/>'), f.text(220, 84, "Disc", size=40)
    for x in (110, 330):
        f.line(x, 120, x, 150), f.line(x, 330, x, 380)
        with f.rotated(90, x, 240):
            coil(f, x - 90, x + 90, 240, turns=8, radius=16)
    f.line(20, 380, 420, 380, width=3)
    return f


def pv_isochoric_options_abcd():
    """P-V graphs: (A) a rising line through the origin, (B) a horizontal line, (C) a vertical line, (D) a rising curve that levels off."""
    f = Figure(760, 230)
    for name, ox in zip("ABCD", (40, 230, 420, 610)):
        f.axes(ox, 160, 140, 130, xlabel="<i>V</i>", ylabel="<i>P</i>", size=24)
        f.text(ox + 70, 214, f"({name})", size=26)
    f.line(40, 160, 140, 50)
    f.line(240, 60, 360, 60)
    f.line(470, 50, 470, 150)
    f.add('<path d="M612,155 C630,80 680,40 740,50" stroke-width="3"/>')
    return f


def vt_options_pqrs():
    """Volume against temperature: (P) a falling line, (Q) a rising line, (R) an L-shape near the origin, (S) a horizontal line."""
    f = Figure(640, 400)
    for name, (ox, oy) in zip("PQRS", ((80, 160), (400, 160), (80, 360), (400, 360))):
        f.line(ox - 40, oy, ox + 180, oy), f.line(ox, oy + 20, ox, oy - 140)
        f.text(ox - 46, oy - 140, f"({name})", size=26, anchor="end"), f.text(ox - 10, oy - 110, "<i>V</i>", size=24, anchor="end")
        f.text(ox - 10, oy + 30, "O", size=22, anchor="end"), f.text(ox + 170, oy + 34, "<i>T</i>", size=24)
    f.line(110, 60, 190, 130)
    f.line(430, 130, 510, 60)
    f.polyline([(110, 280), (110, 330), (180, 330)])
    f.line(410, 240, 520, 240)
    return f


def ft_falling_line():
    """Force F (N) against time t (s): falling linearly from 0.6 N at t = 0 to zero at t = 4.0 s."""
    f = Figure(500, 340)
    ox, oy = 140, 260
    f.line(40, oy, 460, oy, width=3, arrow=True), f.line(ox, 300, ox, 30, width=3, arrow=True)
    f.line(ox, 110, 300, oy, width=3)
    f.text(60, 70, "(0.6)", size=34), f.text(170, 70, "<i>F</i> (N)", size=34, anchor="start")
    f.text(ox - 16, oy + 40, "O", size=34, anchor="end"), f.text(300, oy + 50, "4.0", size=34), f.text(430, oy + 50, "<i>t</i> (s)", size=34)
    return f


FIGURES = {
    "PYQ-PHY-8786436a9fea": energy_levels,
    "PYQ-PHY-f996790068ab": ke_frequency_line,
    "PYQ-PHY-2cfefb4ca42d": stopping_potential_p_q,
    "PYQ-PHY-c2d2683dd213": potential_step,
    "PYQ-PHY-aa7cd33f031c": ft_10_then_20,
    "PYQ-PHY-d7c53b428f1b": springs_series_parallel,
    "PYQ-PHY-b74f87edccf3": lens_in_liquid,
    "PYQ-PHY-d08742d75d02": pv_process_options,
    "PYQ-PHY-e60a84272ba3": spring_mass_rotating,
    "PYQ-PHY-30ef694040c2": conical_pendulum,
    "PYQ-PHY-92576004ade7": de_broglie_masses,
    "PYQ-PHY-22f4b59eef85": mass_between_four_springs,
    "PYQ-PHY-2b2ed872ab81": shm_force_graph,
    "PYQ-PHY-a8c17a44dfc6": disc_on_two_springs,
    "PYQ-PHY-0ecbc00b112a": pv_isochoric_options_abcd,
    "PYQ-PHY-b3adc1563727": vt_options_pqrs,
    "PYQ-PHY-c612592554d7": ft_falling_line,
}
