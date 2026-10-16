"""Physics (MHT-CET 2024-25): alternating current and magnetic materials."""

import math

from figlib import Figure, coil


def wire(f, *points):
    f.polyline(list(points))


def impedance_options():
    """Impedance Z against frequency: (A) rising line, (B) a dip (high, low, high), (C) a bump, (D) a V-shaped dip."""
    f = Figure(640, 500)
    for name, (ox, oy) in zip("ABCD", ((50, 190), (370, 190), (50, 430), (370, 430))):
        f.axes(ox, oy, 230, 160, xlabel="<i>ν</i>", ylabel="<i>Z</i>", origin="0", size=26)
        f.text(ox + 110, oy + 44, f"({name})", size=26)
    f.line(70, 170, 210, 50)
    f.add('<path d="M380,60 C440,60 440,160 470,160 C500,160 500,60 560,60" stroke-width="3"/>')
    f.add('<path d="M70,400 C130,400 120,290 160,290 C200,290 190,400 250,400" stroke-width="3"/>')
    f.line(390, 330, 440, 330), f.line(440, 330, 480, 390), f.line(480, 390, 520, 330), f.line(520, 330, 570, 330)
    return f


def rlc_two_switches_arrow():
    """V cell (current arrow) and R charge capacitor C when S1 is closed; with S1 open and S2 closed, C discharges through inductor L."""
    f = Figure(520, 560)
    l, r, top, mid, bottom = 60, 400, 50, 300, 500
    f.line(l, top, 186, top), f.cell(197, top, gap=22, long=28, short=16), f.line(208, top, r, top), f.arrowhead(300, top, 0, size=16)
    f.line(l, top, l, 110), f.vresistor(l, 110, 230), f.line(l, 230, l, bottom)
    f.line(l, mid, 186, mid), f.capacitor(193, mid, gap=14, height=28), f.line(200, mid, r, mid)
    f.line(r, top, r, 130), f.line(r, 130, 432, 200), f.dot(r, 210), f.line(r, 210, r, mid)
    f.line(r, mid, r, 340), f.line(r, 340, 432, 410), f.dot(r, 420), f.line(r, 420, r, bottom)
    f.line(l, bottom, 150, bottom), coil(f, 150, 290, bottom, turns=5, radius=18), f.line(290, bottom, r, bottom)
    f.text(160, 30, "<i>V</i>", size=30), f.text(28, 180, "<i>R</i>", size=30), f.text(193, 258, "<i>C</i>", size=30)
    f.text(220, 548, "<i>L</i>", size=30)
    f.text(444, 220, "S<sub>1</sub>", size=30, anchor="start"), f.text(444, 430, "S<sub>2</sub>", size=30, anchor="start")
    return f


def inductors_half_half_three_quarter():
    """Two inductors L/2 in parallel, in series with 3L/4."""
    f = Figure(700, 380)
    y, l, r = 170, 120, 380
    f.line(20, y, l, y), f.dot(l, y), f.dot(r, y), f.line(l, 60, l, 280), f.line(r, 60, r, 280)
    for yy in (60, 280):
        f.line(l, yy, 180, yy), coil(f, 180, 320, yy, turns=7, radius=16), f.line(320, yy, r, yy)
    f.line(r, y, 470, y), coil(f, 470, 640, y, turns=8, radius=18), f.line(640, y, 690, y)
    f.fraction(250, 130, "<i>L</i>", "2", size=26), f.fraction(250, 330, "<i>L</i>", "2", size=26)
    f.fraction(555, 96, "3", "4", size=26), f.text(590, 108, "<i>L</i>", size=28)
    return f


def two_ac_circuits_40ohm():
    """(A) 40 ohm across a 220 V, 50 Hz source. (B) 40 ohm, 50 mH and 0.5 uF in series across a 220 V, 50 Hz source."""
    f = Figure(760, 300)
    f.line(20, 70, 70, 70), f.resistor(70, 150, 70, peaks=5, height=12), f.line(150, 70, 220, 70)
    f.line(20, 70, 20, 220), f.line(220, 70, 220, 220), f.line(20, 220, 100, 220), f.ac_source(124, 220, r=22), f.line(146, 220, 220, 220)
    f.text(110, 44, "40 Ω", size=24), f.text(124, 266, "220 V, 50 Hz", size=22), f.text(124, 292, "(A)", size=24)
    t, b, l, r = 100, 240, 290, 740
    f.line(l, t, 340, t), f.resistor(340, 420, t, peaks=5, height=12), f.line(420, t, 500, t)
    coil(f, 500, 590, t, turns=5, radius=13), f.line(590, t, 673, t), f.capacitor(680, t, gap=12, height=20), f.line(686, t, r, t)
    f.line(l, t, l, b), f.line(r, t, r, b), f.line(l, b, 492, b), f.ac_source(514, b, r=22), f.line(536, b, r, b)
    f.text(380, 150, "40 Ω", size=24), f.text(545, 150, "50 mH", size=24), f.text(680, 150, "0.5 μF", size=24)
    f.text(514, 280, "220 V, 50 Hz", size=22, anchor="end"), f.text(560, 292, "(B)", size=24)
    return f


def lc_16mh_10uf():
    """An LC loop: L = 16 mH on the top wire, C = 10 uF on the bottom wire."""
    f = Figure(620, 400)
    l, r, t, b = 40, 580, 100, 320
    f.line(l, t, 230, t), coil(f, 230, 390, t, turns=6, radius=18), f.line(390, t, r, t)
    f.line(l, t, l, b), f.line(r, t, r, b), f.line(l, b, 293, b), f.capacitor(300, b, gap=16, height=34), f.line(308, b, r, b)
    f.text(310, 50, "<i>L</i> = 16 mH", size=36), f.text(440, 384, "<i>C</i> = 10 μF", size=36)
    return f


def l_2l_c_2c_ac_source():
    """L and 2L in series on an upper branch, C on a middle branch and 2C on a lower branch, all in parallel, across an a.c. source."""
    f = Figure(640, 440)
    l, r = 150, 460
    f.line(l, 60, l, 260), f.line(r, 60, r, 260)
    f.line(l, 60, 190, 60), coil(f, 190, 290, 60, turns=5, radius=14), f.line(290, 60, 320, 60)
    coil(f, 320, 400, 60, turns=4, radius=14), f.line(400, 60, r, 60)
    f.line(l, 160, 283, 160), f.capacitor(290, 160, gap=14, height=24), f.line(297, 160, r, 160)
    f.line(l, 260, 333, 260), f.capacitor(340, 260, gap=14, height=24), f.line(347, 260, r, 260)
    wire(f, (l, 180), (30, 180), (30, 370), (282, 370)), f.ac_source(310, 370, r=28), wire(f, (338, 370), (610, 370), (610, 180), (r, 180))
    f.dot(l, 180), f.dot(r, 180)
    f.text(240, 30, "<i>L</i>", size=30), f.text(360, 30, "2<i>L</i>", size=30), f.text(270, 210, "<i>C</i>", size=30)
    f.text(320, 310, "2<i>C</i>", size=30), f.text(350, 420, "a.c. source", size=30, anchor="start")
    return f


def phasor_options_il_el():
    """Current iL and emf eL: (A) opposite directions; (B) iL pointing down, eL pointing right; (C) in phase; (D) iL pointing up, eL right."""
    f = Figure(700, 380)
    def vec(x1, y1, x2, y2):
        f.line(x1, y1, x2, y2, arrow=True)
    f.dot(180, 80), vec(180, 80, 60, 80), vec(180, 80, 300, 80)
    f.text(60, 112, "<i>i</i><sub>L</sub>", size=26), f.text(300, 112, "<i>e</i><sub>L</sub>", size=26), f.text(30, 50, "A", size=30)
    vec(480, 50, 480, 150), vec(480, 50, 640, 50)
    f.text(500, 152, "<i>i</i><sub>L</sub>", size=26, anchor="start"), f.text(640, 84, "<i>e</i><sub>L</sub>", size=26), f.text(420, 50, "B", size=30)
    vec(60, 290, 180, 290), vec(180, 290, 300, 290)
    f.text(70, 324, "<i>i</i><sub>L</sub>", size=26), f.text(300, 324, "<i>e</i><sub>L</sub>", size=26), f.text(30, 240, "C", size=30)
    vec(480, 340, 480, 230), vec(480, 340, 640, 340)
    f.text(500, 252, "<i>i</i><sub>L</sub>", size=26, anchor="start"), f.text(640, 374, "<i>e</i><sub>L</sub>", size=26), f.text(420, 240, "D", size=30)
    return f


def two_l_parallel_two_c_series():
    """Two inductors L in parallel, in series with two capacitors C, across an a.c. source."""
    f = Figure(640, 440)
    l, r, t = 40, 600, 100
    f.line(l, t, 130, t), f.line(130, 40, 130, 160), f.line(290, 40, 290, 160)
    for yy in (40, 160):
        f.line(130, yy, 160, yy), coil(f, 160, 260, yy, turns=5, radius=14), f.line(260, yy, 290, yy)
    f.line(290, t, 393, t), f.capacitor(400, t, gap=14, height=28), f.line(407, t, 493, t), f.capacitor(500, t, gap=14, height=28)
    f.line(507, t, r, t)
    f.line(l, t, l, 360), f.line(r, t, r, 360), f.line(l, 360, 282, 360), f.ac_source(310, 360, r=28), f.line(338, 360, r, 360)
    f.text(210, 112, "<i>L</i>", size=32), f.text(210, 218, "<i>L</i>", size=32)
    f.text(400, 168, "<i>C</i>", size=32), f.text(500, 168, "<i>C</i>", size=32), f.text(310, 420, "a.c.", size=30)
    return f


def lcr_voltages_source_e():
    """L, C and R in series with voltages 20 V, 50 V and 40 V across them, driven by the alternating emf E."""
    f = Figure(700, 420)
    l, r, t, b = 20, 680, 70, 350
    f.line(l, t, 80, t), coil(f, 80, 200, t, turns=6, radius=16), f.line(200, t, 343, t), f.capacitor(350, t, gap=14, height=26)
    f.line(357, t, 500, t), f.resistor(500, 640, t, peaks=6, height=18), f.line(640, t, r, t)
    f.line(l, t, l, b), f.line(r, t, r, b), f.line(l, b, 322, b), f.ac_source(350, b, r=28), f.line(378, b, r, b)
    f.dim(l + 4, 150, 236, 150), f.dim(244, 150, 456, 150), f.dim(464, 150, r - 4, 150)
    f.text(140, 30, "<i>L</i>", size=32), f.text(350, 30, "<i>C</i>", size=32), f.text(570, 30, "<i>R</i>", size=32)
    f.text(130, 196, "20 V", size=32), f.text(350, 196, "50 V", size=32), f.text(570, 196, "40 V", size=32)
    f.text(350, 410, "<i>E</i>", size=32)
    return f


def hysteresis_loop():
    """B-H hysteresis loop: saturation at a, retentivity b on the B axis, coercivity c on the H axis, saturation d, then e and f."""
    f = Figure(640, 520)
    ox, oy = 280, 260
    f.line(60, oy, 470, oy, arrow=True), f.line(ox, 480, ox, 40, arrow=True)
    f.add('<path d="M440,100 C330,100 260,170 240,260 C220,350 170,440 70,460" stroke-width="3"/>')
    f.add('<path d="M70,460 C180,450 280,440 320,260 C340,160 380,110 440,100" stroke-width="3"/>')
    f.add('<path d="M280,260 C320,200 360,120 440,100" stroke-width="2.5" stroke-dasharray="none"/>')
    f.arrowhead(300, 128, 160, size=16), f.arrowhead(160, 448, -10, size=16), f.arrowhead(212, 340, 115, size=16)
    f.text(298, 52, "<i>B</i>", size=30, anchor="start"), f.text(330, 52, "Flux density", size=30, anchor="start")
    f.text(486, 270, "<i>H</i>", size=30, anchor="start"), f.text(470, 340, "Magnetizing", size=30, anchor="start"), f.text(470, 380, "force", size=30, anchor="start")
    f.text(456, 110, "a", size=30, anchor="start"), f.text(262, 196, "b", size=30), f.text(220, 286, "c", size=30)
    f.text(270, 286, "o", size=28), f.text(52, 470, "d", size=30), f.text(312, 380, "e", size=30), f.text(338, 286, "f", size=30)
    return f


def susceptibility_options():
    """Susceptibility against temperature: (A) a constant negative value; (B) a constant positive value; (C) high and flat, then dropping; (D) falling with T."""
    f = Figure(700, 280)
    # A: T axis through the middle, line below it
    f.line(60, 230, 60, 30, arrow=True), f.line(60, 110, 170, 110, arrow=True), f.line(60, 160, 140, 160)
    f.text(44, 40, "<i>χ</i>", size=26), f.text(44, 116, "0", size=24), f.text(170, 146, "<i>T</i>", size=26), f.text(60, 264, "A", size=28)
    # B
    f.line(240, 230, 240, 30, arrow=True), f.line(240, 150, 350, 150, arrow=True), f.line(240, 80, 320, 80)
    f.text(224, 40, "<i>χ</i>", size=26), f.text(350, 186, "<i>T</i>", size=26), f.text(240, 264, "B", size=28)
    # C
    f.line(420, 230, 420, 30, arrow=True), f.line(420, 230, 540, 230, arrow=True)
    f.add('<path d="M420,80 L460,80 C480,80 470,190 500,190 L520,190" stroke-width="3"/>')
    f.text(404, 220, "<i>χ</i>", size=26), f.text(540, 264, "<i>T</i>", size=26), f.text(480, 264, "C", size=28)
    # D
    f.line(580, 230, 580, 30, arrow=True), f.line(580, 230, 690, 230, arrow=True)
    f.add('<path d="M588,60 C600,150 620,200 680,200" stroke-width="3"/>')
    f.text(564, 40, "<i>χ</i>", size=26), f.text(688, 264, "<i>T</i>", size=26), f.text(630, 264, "D", size=28)
    return f


FIGURES = {
    "PYQ-PHY-e954c36fcbca": impedance_options,
    "PYQ-PHY-8155aace6e0a": rlc_two_switches_arrow,
    "PYQ-PHY-994dae3ef50c": inductors_half_half_three_quarter,
    "PYQ-PHY-d37f2af2d0ac": two_ac_circuits_40ohm,
    "PYQ-PHY-dc7dfb8b77d6": lc_16mh_10uf,
    "PYQ-PHY-5b7bbcab3569": l_2l_c_2c_ac_source,
    "PYQ-PHY-87886ef6393b": phasor_options_il_el,
    "PYQ-PHY-134390581dd2": two_l_parallel_two_c_series,
    "PYQ-PHY-7cd5564a0a30": lcr_voltages_source_e,
    "PYQ-PHY-5878732e7654": hysteresis_loop,
    "PYQ-PHY-a8d2ffbc581e": susceptibility_options,
}
