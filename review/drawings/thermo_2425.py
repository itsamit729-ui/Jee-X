"""Physics (MHT-CET 2024-25): thermodynamics and black-body radiation."""

import math

from figlib import Figure, mid_arrow


def path_arrow(f, d, at, angle, size=14):
    """Draw an SVG path and an arrowhead at point `at` pointing along `angle`."""
    f.add(f'<path d="{d}" stroke-width="3"/>')
    f.arrowhead(*at, angle, size=size)


def pv_isochoric_options():
    """P-V graphs (A) a rising line, (B) a vertical line, (C) a rise then gentle fall, (D) a horizontal line."""
    f = Figure(760, 230)
    for name, ox in zip("ABCD", (40, 230, 420, 610)):
        f.axes(ox, 150, 140, 120, xlabel="<i>V</i>", ylabel="<i>P</i>", size=26)
        f.text(ox + 60, 212, f"({name})", size=28)
    f.line(46, 140, 140, 50)
    f.line(300, 40, 300, 150)
    f.add('<path d="M424,140 C440,60 470,60 500,64 C520,68 540,80 552,86" stroke-width="3"/>')
    f.line(610, 60, 740, 60)
    return f


def cycle_pv_and_pt_options():
    """A p-V cycle: A-B isothermal (curving down to the right), B-C at constant pressure back to the left, C-A adiabatic up.
    Options (E)-(H) are p-T cycles."""
    f = Figure(700, 800)
    # p-V
    ox, oy = 270, 180
    f.axes(ox, oy, 200, 160, xlabel="<i>V</i>", ylabel="<i>P</i>", size=26)
    path_arrow(f, f"M{ox + 40},{oy - 130} C{ox + 70},{oy - 80} {ox + 110},{oy - 50} {ox + 140},{oy - 30}", (ox + 92, oy - 72), 48)
    f.line(ox + 140, oy - 30, ox + 50, oy - 30), f.arrowhead(ox + 95, oy - 30, 180, size=14)
    path_arrow(f, f"M{ox + 50},{oy - 30} C{ox + 30},{oy - 40} {ox + 32},{oy - 90} {ox + 40},{oy - 130}", (ox + 36, oy - 100), -90)
    f.text(ox + 48, oy - 140, "A", size=26), f.text(ox + 156, oy - 14, "B", size=26), f.text(ox + 34, oy - 6, "C", size=26)

    def panel(ox, oy, name):
        f.axes(ox, oy, 200, 170, xlabel="<i>T</i>", ylabel="<i>P</i>", size=26)
        f.text(ox + 100, oy + 70, f"({name})", size=28)
    # (E)
    ox, oy = 60, 450
    panel(ox, oy, "E")
    path_arrow(f, f"M{ox + 40},{oy - 140} C{ox + 70},{oy - 90} {ox + 110},{oy - 60} {ox + 140},{oy - 30}", (ox + 92, oy - 82), 48)
    f.line(ox + 140, oy - 30, ox + 40, oy - 30), f.arrowhead(ox + 90, oy - 30, 180, size=14)
    path_arrow(f, f"M{ox + 40},{oy - 30} C{ox + 24},{oy - 50} {ox + 26},{oy - 110} {ox + 40},{oy - 140}", (ox + 30, oy - 100), -90)
    f.text(ox + 50, oy - 150, "A", size=26), f.text(ox + 36, oy - 6, "B", size=26), f.text(ox + 156, oy - 14, "C", size=26)
    # (F)
    ox, oy = 400, 450
    panel(ox, oy, "F")
    path_arrow(f, f"M{ox + 40},{oy - 140} C{ox + 80},{oy - 100} {ox + 120},{oy - 60} {ox + 170},{oy - 30}", (ox + 100, oy - 84), 42)
    path_arrow(f, f"M{ox + 170},{oy - 30} C{ox + 100},{oy - 30} {ox + 40},{oy - 50} {ox + 40},{oy - 140}", (ox + 110, oy - 34), 180)
    f.arrowhead(ox + 41, oy - 100, -90, size=14)
    f.text(ox + 50, oy - 150, "A", size=26), f.text(ox + 186, oy - 10, "B", size=26), f.text(ox + 40, oy - 6, "C", size=26)
    # (G)
    ox, oy = 60, 700
    panel(ox, oy, "G")
    a, b, c = (ox + 40, oy - 150), (ox + 160, oy - 40), (ox + 40, oy - 40)
    mid_arrow(f, *a, *b, at=0.4, size=14), mid_arrow(f, *b, *c, at=0.45, size=14), mid_arrow(f, *a, *c, at=0.45, size=14)
    f.text(ox + 50, oy - 160, "A", size=26), f.text(ox + 178, oy - 30, "B", size=26), f.text(ox + 30, oy - 12, "C", size=26)
    # (H)
    ox, oy = 400, 700
    panel(ox, oy, "H")
    a, b, c = (ox + 40, oy - 150), (ox + 40, oy - 40), (ox + 160, oy - 40)
    mid_arrow(f, *a, *b, at=0.45, size=14), mid_arrow(f, *b, *c, at=0.5, size=14), mid_arrow(f, *c, *a, at=0.5, size=14)
    f.text(ox + 50, oy - 160, "A", size=26), f.text(ox + 30, oy - 12, "B", size=26), f.text(ox + 178, oy - 30, "C", size=26)
    return f


def rectangle_abcd_paths():
    """A rectangular cycle: a (bottom left) up to b, across to c (top right); a across to d (bottom right), up to c."""
    f = Figure(640, 380)
    a, b, c, d = (90, 320), (90, 70), (550, 70), (550, 320)
    mid_arrow(f, *a, *b, at=0.55, size=18), mid_arrow(f, *b, *c, at=0.5, size=18)
    mid_arrow(f, *a, *d, at=0.5, size=18), mid_arrow(f, *d, *c, at=0.55, size=18)
    f.text(60, 360, "a", size=40), f.text(60, 54, "b", size=40), f.text(586, 54, "c", size=40), f.text(586, 360, "d", size=40)
    return f


def wien_frequency_options():
    """Peak frequency against temperature: curve D (bending up steeply), line B through the origin, curve C (bending down), and a falling line A."""
    f = Figure(640, 520)
    ox, oy = 100, 440
    f.axes(ox, oy, 460, 400, xlabel="X", ylabel="Y", size=34)
    f.add(f'<path d="M{ox},{oy} C{ox + 30},{oy - 120} {ox + 60},{oy - 240} {ox + 110},{oy - 320}" stroke-width="3"/>')
    f.line(ox, oy, ox + 300, oy - 380)
    f.add(f'<path d="M{ox},{oy} C{ox + 120},{oy - 70} {ox + 220},{oy - 150} {ox + 340},{oy - 270}" stroke-width="3"/>')
    f.line(ox + 30, oy - 330, ox + 320, oy - 70)
    f.text(ox + 80, oy - 320, "D", size=34), f.text(ox + 160, oy - 280, "A", size=34)
    f.text(ox + 230, oy - 220, "B", size=34), f.text(ox + 300, oy - 140, "C", size=34)
    f.text(50, 250, "<i>ν</i><sub>m</sub>", size=32), f.line(56, 330, 56, 280, arrow=True)
    f.text(270, 505, "<i>T</i>", size=32), f.line(296, 494, 346, 494, arrow=True)
    return f


def pv_cycle_abcd_curved():
    """A P-V cycle A (top left), B (top right), C (right), D (bottom): A-B nearly flat, B-C and A-D curving down (adiabatic), C-D curving."""
    f = Figure(560, 480)
    ox, oy = 60, 430
    f.axes(ox, oy, 460, 400, xlabel="<i>V</i>", ylabel="<i>P</i>", size=40)
    a, b, c, d = (190, 170), (380, 150), (420, 270), (240, 300)
    f.add(f'<path d="M{a[0]},{a[1]} Q{285},{168} {b[0]},{b[1]}" stroke-width="3"/>')
    f.add(f'<path d="M{b[0]},{b[1]} Q{392},{240} {c[0]},{c[1]}" stroke-width="3"/>')
    f.add(f'<path d="M{c[0]},{c[1]} Q{330},{290} {d[0]},{d[1]}" stroke-width="3"/>')
    f.add(f'<path d="M{a[0]},{a[1]} Q{200},{260} {d[0]},{d[1]}" stroke-width="3"/>')
    f.text(160, 140, "A", size=40), f.text(390, 120, "B", size=40), f.text(456, 290, "C", size=40), f.text(240, 350, "D", size=40)
    return f


def pv_process_options_abc():
    """P-V graphs: (a) a falling hyperbola, (b) a vertical line with a downward arrow, (c) a horizontal line with an arrow to the right."""
    f = Figure(760, 240)
    for name, ox in zip("abc", (40, 290, 540)):
        f.axes(ox, 160, 170, 140, size=26)
        f.text(ox - 22, 90, "<i>P</i>", size=28), f.text(ox + 100, 196, "<i>V</i>", size=28), f.text(ox + 90, 230, f"({name})", size=28)
    f.curve(lambda x: 150 - 1500 / (x - 30), 52, 200)
    f.line(350, 40, 350, 140, arrow=True)
    f.line(570, 70, 690, 70, arrow=True)
    return f


def cycle_abc_p_v():
    """Cycle A (P, V) to B (P, 3V) at constant pressure, B up to C (4P, 3V), then straight back to A."""
    f = Figure(560, 480)
    ox, oy = 100, 380
    f.line(30, oy, 520, oy, arrow=True), f.line(ox, 450, ox, 30, arrow=True)
    a, b, c = (220, 290), (380, 290), (380, 90)
    mid_arrow(f, *a, *b, at=0.5, size=18), mid_arrow(f, *b, *c, at=0.5, size=18), mid_arrow(f, *c, *a, at=0.45, size=18)
    f.line(ox, 290, a[0], 290, width=2, dash="4 6"), f.line(a[0], 290, a[0], oy, width=2, dash="4 6")
    f.line(ox, 90, c[0], 90, width=3, dash="16 10")
    f.text(84, 300, "<i>P</i>", size=30, anchor="end"), f.text(84, 100, "4<i>P</i>", size=30, anchor="end")
    f.text(220, 414, "<i>V</i>", size=30), f.text(380, 414, "3<i>V</i>", size=30)
    f.text(210, 330, "A", size=30), f.text(404, 300, "B", size=30, anchor="start"), f.text(398, 90, "C", size=30, anchor="start")
    f.text(40, 250, "<i>P</i>", size=30), f.line(46, 200, 46, 130, arrow=True)
    f.text(280, 466, "<i>V</i>", size=30), f.line(304, 456, 360, 456, arrow=True)
    return f


def black_body_curves():
    """Black-body radiant power against wavelength (nm) at 3000 K, 4000 K, 5000 K and 5500 K; peaks move to shorter wavelength and grow with temperature."""
    f = Figure(760, 420)
    ox, oy = 90, 330
    f.line(30, oy, 740, oy, arrow=True), f.line(ox, 380, ox, 20, arrow=True)
    scale = 0.2  # pixels per nm
    for t, peak in ((3000, 40), (4000, 70), (5000, 160), (5500, 250)):
        lam_peak = 2.9e6 / t
        def curve(x, peak=peak, lp=lam_peak):
            u = max((x - ox) / scale, 30) / lp  # wavelength in units of the peak wavelength
            return oy - peak * (u ** -5 / (math.exp(4.965 / u) - 1)) * (math.exp(4.965) - 1)
        f.curve(curve, ox + 18, 700, steps=200)
    for i, n in enumerate(range(500, 3001, 500)):
        x = ox + n * scale
        f.line(x, oy, x, oy + 8, width=2), f.text(x, oy + 34, str(n), size=22)
    f.text(560, 390, "wavelength (nm)", size=24)
    f.text(118, 44, "<i>λ</i><sub>m</sub>", size=24), f.line(150, 40, 200, 40, arrow=True), f.text(208, 48, "5500 K", size=24, anchor="start")
    f.line(230, 150, 280, 150, arrow=True), f.text(288, 158, "5000 K", size=24, anchor="start", halo=True)
    f.text(150, 252, "4000 K", size=24, anchor="start", halo=True), f.text(150, 302, "3000 K", size=24, anchor="start", halo=True)
    return f


def tp_cycle_grid():
    """T against P on a grid: 1 to 2 straight up, 2 to 3 along a line through the origin, 3 to 4 straight down, 4 to 1 along a line through the origin."""
    f = Figure(560, 480)
    ox, oy, cw, rh = 100, 400, 80, 70
    f.line(ox - 20, oy, 520, oy, arrow=True), f.line(ox, 440, ox, 30, arrow=True)
    for i in range(1, 5):
        f.line(ox + cw * i, oy, ox + cw * i, oy - rh * 4, width=2)
        f.line(ox, oy - rh * i, ox + cw * 4, oy - rh * i, width=2)
    pt = lambda p, t: (ox + cw * p, oy - rh * t)  # noqa: E731
    p1, p2, p3, p4 = pt(1, 2 / 3), pt(1, 4 / 3), pt(3, 4), pt(3, 2)
    mid_arrow(f, *p1, *p2, at=0.6, size=16), mid_arrow(f, *p2, *p3, at=0.4, size=16)
    mid_arrow(f, *p3, *p4, at=0.5, size=16), mid_arrow(f, *p4, *p1, at=0.4, size=16)
    f.text(p1[0] + 18, p1[1] + 22, "1", size=28), f.text(p2[0] - 16, p2[1] + 8, "2", size=28, anchor="end")
    f.text(p3[0] + 8, p3[1] - 10, "3", size=28), f.text(p4[0] + 16, p4[1] + 30, "4", size=28, anchor="start")
    f.text(ox - 22, oy + 30, "0", size=28), f.text(60, 60, "<i>T</i>", size=32), f.line(66, 140, 66, 80, arrow=True)
    f.text(470, 446, "<i>P</i>", size=32), f.line(380, 436, 440, 436, arrow=True)
    return f


def cycle_abca_v_p():
    """V (m^3) against P (N m^-2): A at (10, 1.5), B at (10, 2), C at (5, 2); A to B up, B to C left, C to A along a straight line."""
    f = Figure(560, 500)
    ox, oy = 120, 400
    px, vy = 34, 150  # pixels per N m^-2 and per m^3
    f.line(ox, oy, 520, oy), f.line(ox, oy, ox, 40)
    for i in range(1, 11):
        f.line(ox + px * i, oy, ox + px * i, oy - 10, width=2)
    pt = lambda p, v: (ox + px * p, oy - vy * v)  # noqa: E731
    a, b, c = pt(10, 1.5), pt(10, 2), pt(5, 2)
    mid_arrow(f, *a, *b, at=0.6, size=16), mid_arrow(f, *b, *c, at=0.5, size=16), mid_arrow(f, *c, *a, at=0.55, size=16)
    f.line(ox, c[1], c[0], c[1], width=2, dash="4 6"), f.line(c[0], c[1], c[0], oy, width=2, dash="4 6")
    f.line(a[0], a[1], a[0], oy, width=2, dash="4 6"), f.dot(ox, oy - vy, r=5)
    f.text(ox - 14, c[1] + 10, "2", size=28, anchor="end"), f.text(ox - 14, oy - vy + 10, "1", size=28, anchor="end")
    f.text(ox, oy + 34, "0", size=28), f.text(c[0], oy + 34, "5", size=28), f.text(a[0], oy + 34, "10", size=28)
    f.text(c[0] - 40, c[1] - 14, "C", size=30), f.text(b[0] + 14, b[1] - 6, "B", size=30, anchor="start"), f.text(a[0] + 14, a[1] + 10, "A", size=30, anchor="start")
    f.text(56, 240, "<i>V</i>", size=32), f.line(62, 190, 62, 140, arrow=True), f.text(56, 290, "(m<sup>3</sup>)", size=28)
    f.text(320, 484, "<i>P</i> (N m<sup>−2</sup>)", size=32)
    return f


FIGURES = {
    "PYQ-PHY-395500c8724d": pv_isochoric_options,
    "PYQ-PHY-a77d8056daac": cycle_pv_and_pt_options,
    "PYQ-PHY-df1b662bc59f": rectangle_abcd_paths,
    "PYQ-PHY-8c7a9de38dc4": wien_frequency_options,
    "PYQ-PHY-a187bd014014": pv_cycle_abcd_curved,
    "PYQ-PHY-7c4304d6f4dd": pv_process_options_abc,
    "PYQ-PHY-01035150109a": cycle_abc_p_v,
    "PYQ-PHY-6172464a7ac8": black_body_curves,
    "PYQ-PHY-ddc69a4bc64a": tp_cycle_grid,
    "PYQ-PHY-89a2c86ba215": cycle_abca_v_p,
}
