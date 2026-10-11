"""Physics: alternating current, atoms, capacitance (part 1)."""

import math

from figlib import Figure, coil

I_C, E_C = "<i>I</i><sub>c</sub>", "<i>e</i><sub>c</sub>"


def lcr_series_1h():
    """Series loop: 1 H, 20 uF and 300 ohm on top; source 50 V, 50/pi Hz below."""
    f = Figure(640, 360)
    left, right, top, bottom = 45, 600, 65, 300
    f.line(left, top, 110, top), f.line(190, top, 313, top), f.line(327, top, 440, top), f.line(540, top, right, top)
    coil(f, 110, 190, top, turns=3, radius=17), f.capacitor(320, top), f.resistor(440, 540, top)
    f.text(150, 118, "1 H"), f.text(320, 128, "20 μF"), f.text(490, 118, "300 Ω")
    f.line(left, top, left, bottom), f.line(right, top, right, bottom)
    f.line(left, bottom, 352, bottom), f.line(408, bottom, right, bottom)
    f.ac_source(380, bottom, r=28)
    f.text(232, 268, "50 V,"), f.fraction(288, 258, "50", "<i>π</i>", size=24), f.text(332, 268, "Hz")
    return f


def phasor_options_capacitor():
    """Four options (A)-(D) for the phase relation between current Ic and emf ec."""
    f = Figure(1000, 300)
    f.vector(30, 110, 120, 110), f.vector(120, 110, 215, 110)                       # (A) in phase
    f.text(52, 92, I_C, size=26), f.text(205, 92, E_C, size=26)
    f.vector(330, 160, 330, 55), f.vector(330, 160, 445, 160)                       # (B) current leads by 90
    f.text(312, 62, I_C, size=26), f.text(452, 196, E_C, size=26)
    f.vector(565, 85, 680, 85), f.vector(565, 85, 565, 195)                         # (C) current lags by 90
    f.text(672, 66, E_C, size=26), f.text(545, 190, I_C, size=26)
    f.dot(850, 110), f.vector(850, 110, 765, 110), f.vector(850, 110, 935, 110)     # (D) opposite
    f.text(788, 92, I_C, size=26), f.text(922, 92, E_C, size=26)
    for x, name in ((120, "A"), (385, "B"), (620, "C"), (850, "D")):
        f.text(x, 268, f"({name})", size=28)
    return f


def two_ac_circuits():
    """Circuit (A): 30 ohm alone. Circuit (B): 30 ohm, 40 mH and 0.4 uF in series. Both on 210 V, 50 Hz."""
    f = Figure(1000, 330)
    top, bottom = 80, 215
    # (A)
    f.line(110, top, 185, top), f.resistor(185, 265, top), f.line(265, top, 340, top)
    f.line(110, top, 110, bottom), f.line(340, top, 340, bottom)
    f.line(110, bottom, 199, bottom), f.line(251, bottom, 340, bottom), f.ac_source(225, bottom)
    f.text(225, 52, "30 Ω", size=26), f.text(225, 285, "210 V, 50 Hz", size=26)
    f.circle(48, 148, 26), f.text(48, 159, "A", size=30)
    # (B)
    f.line(470, top, 520, top), f.resistor(520, 600, top), f.line(600, top, 640, top)
    coil(f, 640, 720, top, turns=4, radius=14), f.line(720, top, 783, top), f.capacitor(790, top, height=26)
    f.line(797, top, 880, top)
    f.line(470, top, 470, bottom), f.line(880, top, 880, bottom)
    f.line(470, bottom, 649, bottom), f.line(701, bottom, 880, bottom), f.ac_source(675, bottom)
    f.text(560, 132, "30 Ω", size=26), f.text(680, 132, "40 mH", size=26), f.text(800, 142, "0.4 μF", size=26)
    f.text(675, 285, "210 V, 50 Hz", size=26)
    f.circle(948, 148, 26), f.text(948, 159, "B", size=30)
    return f


def reactance_graph_options():
    """Four options (A)-(D) for inductive reactance XL against angular frequency omega."""
    f = Figure(1000, 290)
    for k, name in enumerate("ABCD"):
        ox, oy = 70 + k * 245, 190
        f.axes(ox, oy, 150, 150, xlabel="<i>ω</i>", ylabel="", size=24)
        f.text(ox - 26, oy - 138, "<i>X</i><sub>L</sub>", size=24)
        if name == "A":
            f.line(ox, oy - 80, ox + 125, oy - 80)
        elif name == "B":
            f.line(ox, oy, ox + 120, oy - 120)
        elif name == "C":
            f.line(ox + 70, oy, ox + 70, oy - 125)
        else:
            f.line(ox, oy - 120, ox + 120, oy)
        f.text(ox + 70, 262, f"({name})", size=26)
    return f


def lcr_reactances():
    """Series loop with XL = 200 ohm, XC = 100 ohm, R = 100 ohm on a source of Vrms = 200 root 2 V."""
    f = Figure(660, 470)
    left, right, top, bottom = 40, 630, 55, 325
    f.line(left, top, 150, top), coil(f, 150, 250, top, turns=4, radius=17), f.line(250, top, 318, top)
    f.capacitor(325, top), f.line(332, top, 430, top), f.resistor(430, 530, top), f.line(530, top, right, top)
    f.line(left, top, left, bottom), f.line(right, top, right, bottom)
    f.line(left, bottom, 307, bottom), f.line(363, bottom, right, bottom), f.ac_source(335, bottom, r=28)
    f.text(335, 130, "<i>X</i><sub>L</sub> = 200 Ω,  <i>X</i><sub>C</sub> = 100 Ω,  <i>R</i> = 100 Ω", size=30)
    f.text(335, 410, "<i>V</i><sub>rms</sub> = 200√2 V", size=32)
    return f


def lcr_loop_symbols():
    """Loop with R on top, source E on the left, capacitor C on the right and inductor L at the bottom."""
    f = Figure(640, 460)
    left, right, top, bottom = 70, 570, 60, 410
    f.line(left, top, 260, top), f.resistor(260, 380, top, height=16), f.line(380, top, right, top)
    f.line(left, top, left, 203), f.line(left, 267, left, bottom), f.ac_source(left, 235, r=32)
    f.line(right, top, right, 228), f.line(right, 242, right, bottom), f.vcapacitor(right, 235)
    f.line(left, bottom, 255, bottom), coil(f, 255, 385, bottom, turns=5, radius=17), f.line(385, bottom, right, bottom)
    f.text(320, 118, "<i>R</i>"), f.text(22, 246, "<i>E</i>"), f.text(618, 246, "<i>C</i>"), f.text(320, 372, "<i>L</i>")
    return f


def resonance_graph_options():
    """Four options (P)-(S) for r.m.s. current i against frequency f in a series resonant circuit."""
    f = Figure(1000, 300)
    shapes = {
        "P": lambda t: math.exp(-((t - 0.5) / 0.17) ** 2),                                   # single peak
        "Q": lambda t: 1 - math.exp(-((t - 0.5) / 0.2) ** 2),                                # single dip
        "R": lambda t: 0.72 * math.exp(-((t - 0.5) / 0.26) ** 2) + 0.28 * max(0, 1 - abs(t - 0.5) / 0.06),
        "S": lambda t: 1 - 0.8 * math.exp(-((t - 0.5) / 0.26) ** 2) + 0.14 * max(0, 1 - abs(t - 0.5) / 0.06) - 0.1,
    }
    for k, (name, shape) in enumerate(shapes.items()):
        ox, oy = 65 + k * 245, 200
        f.axes(ox, oy, 165, 165, xlabel="<i>f</i>", ylabel="<i>i</i>", size=26)
        f.polyline([(ox + 15 + 135 * i / 80, oy - 12 - 125 * shape(i / 80)) for i in range(81)])
        f.text(ox + 80, 272, f"({name})", size=26)
    return f


def phasor_options_numbered():
    """Four options (1)-(4) for the phasors of current i and emf e."""
    f = Figure(1000, 320)
    f.vector(45, 215, 45, 70), f.vector(45, 215, 190, 215), f.right_angle(45, 215, 1, -1)          # (1)
    f.text(42, 56, "<i>e</i>", size=28), f.text(206, 224, "<i>i</i>", size=28)
    f.vector(275, 55, 430, 55), f.vector(275, 55, 275, 205), f.right_angle(275, 55, 1, 1)          # (2)
    f.text(446, 64, "<i>i</i>", size=28), f.text(275, 240, "<i>e</i>", size=28)
    f.vector(495, 78, 655, 78), f.vector(495, 150, 655, 150)                                        # (3)
    f.text(672, 87, "<i>i</i>", size=28), f.text(672, 159, "<i>e</i>", size=28)
    f.vector(738, 70, 930, 70), f.vector(738, 70, 912, 228), f.arc(738, 70, 38, 0, 42)             # (4)
    f.text(946, 79, "<i>i</i>", size=28), f.text(932, 246, "<i>e</i>", size=28)
    for x, n in ((110, 1), (348, 2), (592, 3), (842, 4)):
        f.text(x, 298, f"({n})", size=28)
    return f


def hydrogen_transitions():
    """Levels n = 1, 2, 3 of hydrogen: transition 1 is n = 3 to 1, transition 2 is n = 2 to 1."""
    f = Figure(660, 380)
    for n, y in ((3, 48), (2, 182), (1, 330)):
        f.line(85, y, 455, y)
        f.text(72, y + 9, f"<i>n</i> = {n}", size=26, anchor="end")
    f.vector(345, 48, 345, 327), f.vector(198, 182, 198, 327)
    f.text(365, 250, "1", size=26), f.text(218, 250, "2", size=26)
    f.text(470, 118, "Excited states", size=26, anchor="start")
    f.text(470, 322, "Ground", size=26, anchor="start"), f.text(470, 352, "state", size=26, anchor="start")
    return f


def four_capacitors_ab():
    """Four capacitors C in a row; B joins the two outer ends, A joins the nodes after the first and before the last."""
    f = Figure(640, 440)
    row, xs = 180, (120, 223, 326, 430)
    f.polyline([(113, row), (51, row), (51, 74), (489, 74), (489, row), (437, row)])
    for a, b in zip(xs, xs[1:]):
        f.line(a + 7, row, b - 7, row)
    for x in xs:
        f.capacitor(x, row, height=24)
        f.text(x, 138, "<i>C</i>", size=28)
    f.polyline([(489, 127), (587, 127), (587, 181)]), f.dot(587, 181, r=6), f.text(587, 218, "B", size=28)
    f.polyline([(172, row), (172, 304), (378, 304), (378, row)])
    f.line(275, 304, 275, 369), f.dot(275, 369, r=6), f.text(275, 406, "A", size=28)
    return f


def capacitors_6c():
    """2C, 3C and 4C in parallel, in series with C1, between A and B."""
    f = Figure(640, 400)
    left, right, mid = 185, 420, 200
    f.line(left, 50, left, 350), f.line(right, 50, right, 350)
    for y, label in ((50, "2<i>C</i>"), (mid, "3<i>C</i>"), (350, "4<i>C</i>")):
        f.line(left, y, 293, y), f.line(307, y, right, y), f.capacitor(300, y, height=26)
        f.text(336, y - 22, label, size=28)
    f.line(72, mid, left, mid), f.terminal(66, mid), f.text(40, mid + 10, "A", size=30)
    f.dot(right, mid), f.line(right, mid, 503, mid), f.capacitor(510, mid, height=26), f.line(517, mid, 584, mid)
    f.terminal(590, mid), f.text(617, mid + 10, "B", size=30)
    f.text(540, mid - 24, "<i>C</i><sup>1</sup>", size=28)
    return f


def four_capacitors_battery():
    """C3, C2 and C1 in series around the upper loop; C4 across the middle; battery V at the bottom."""
    f = Figure(660, 460)
    left, right, top, mid, bottom, cx = 150, 480, 45, 280, 395, 315
    f.line(left, top, cx - 7, top), f.line(cx + 7, top, right, top), f.capacitor(cx, top, height=24)
    f.line(left, top, left, 153), f.line(left, 167, left, bottom), f.vcapacitor(left, 160, half=24)
    f.line(right, top, right, 153), f.line(right, 167, right, bottom), f.vcapacitor(right, 160, half=24)
    f.line(left, mid, cx - 7, mid), f.line(cx + 7, mid, right, mid), f.capacitor(cx, mid, height=24)
    f.line(left, bottom, cx - 9, bottom), f.line(cx + 9, bottom, right, bottom), f.cell(cx, bottom, gap=18, long=30, short=16)
    f.text(cx, 108, "<i>C</i><sub>2</sub> = 2<i>C</i>", size=28), f.text(cx, 240, "<i>C</i><sub>4</sub> = 4<i>C</i>", size=28)
    f.text(118, 170, "<i>C</i><sub>3</sub> = 3<i>C</i>", size=28, anchor="end")
    f.text(512, 170, "<i>C</i><sub>1</sub> = 1<i>C</i>", size=28, anchor="start")
    f.text(cx, 450, "<i>V</i>", size=28)
    return f


FIGURES = {
    "PYQ-PHY-0894b992a5b4": lcr_series_1h,
    "PYQ-PHY-4a1b26e2b7bc": phasor_options_capacitor,
    "PYQ-PHY-53a50157b51a": two_ac_circuits,
    "PYQ-PHY-7c73dcee250d": reactance_graph_options,
    "PYQ-PHY-84780fb2d1a4": lcr_reactances,
    "PYQ-PHY-8ef3a063fe82": lcr_loop_symbols,
    "PYQ-PHY-bc6941ae8e65": resonance_graph_options,
    "PYQ-PHY-fb8ae36649a1": phasor_options_numbered,
    "PYQ-PHY-ff27622b8334": hydrogen_transitions,
    "PYQ-PHY-003d7241278d": four_capacitors_ab,
    "PYQ-PHY-44ee062e22cd": capacitors_6c,
    "PYQ-PHY-4a0e4aa08e20": four_capacitors_battery,
}
