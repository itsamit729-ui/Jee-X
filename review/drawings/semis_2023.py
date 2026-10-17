"""Physics (MHT-CET 2020-23): semiconductors - diode circuits, logic gates and characteristics."""

from figlib import Figure


def wire(f, *points):
    f.polyline(list(points))


def right_cell(f, x, y, **kw):
    """A cell on a horizontal wire with its positive (long) plate on the right."""
    with f.rotated(180, x, y):
        f.cell(x, y, **kw)


def vdiode(f, x, y, pointing="down", size=22):
    with f.rotated(90 if pointing == "down" else -90, x, y):
        f.diode(x, y, "right", size=size)


def light_arrows(f, x, y, inward):
    """Two short parallel arrows above a diode at (x, y): pointing at it (photodiode) or away from it (LED)."""
    for dx in (-10, 12):
        a, b = (x + dx + 16, y - 52), (x + dx, y - 30)
        f.line(*(a if inward else b), *(b if inward else a), width=2, arrow=True)


def diode_5v_to_3v():
    """+5 V terminal, diode (pointing right), 200 ohm, +3 V terminal."""
    f = Figure(720, 190)
    y = 80
    f.dot(50, y, r=10), f.line(50, y, 380, y), f.diode(402, y, "right", size=24), f.line(426, y, 480, y)
    f.resistor(480, 600, y, peaks=4, height=16), f.line(600, y, 660, y), f.dot(660, y, r=10)
    f.text(60, 44, "+5 V", size=40), f.text(660, 44, "+3 V", size=40), f.text(540, 44, "200 Ω", size=36)
    return f


def nand_or_from_nands():
    """A and B each go to a NAND gate with its inputs tied (giving y1, y2); y1 and y2 feed a third NAND gate giving y."""
    f = Figure(720, 330)
    def tied(x, y):
        p, o = f.gate("NAND", x, y, w=96, h=84)
        wire(f, (x - 36, p[0][1]), (x - 36, p[1][1])), f.line(x - 36, p[0][1], *p[0]), f.line(x - 36, p[1][1], *p[1])
        return (x - 36, y), o
    i1, o1 = tied(170, 80)
    i2, o2 = tied(170, 250)
    for (x, y), name in ((i1, "A"), (i2, "B")):
        f.dot(30, y, r=6), f.line(30, y, x, y), f.text(18, y - 16, name, size=30)
    p3, o3 = f.gate("NAND", 480, 165, w=96, h=84)
    wire(f, o1, (380, 80), (380, p3[0][1]), p3[0]), wire(f, o2, (380, 250), (380, p3[1][1]), p3[1])
    f.line(*o3, 680, 165)
    f.text(420, 124, "y<sub>1</sub>", size=28), f.text(420, 236, "y<sub>2</sub>", size=28), f.text(640, 200, "y", size=30)
    return f


def diode_p_to_q():
    """P at +3 V, diode (pointing right), 2 kilo-ohm, Q at -5 V."""
    f = Figure(720, 180)
    y = 80
    f.dot(50, y, r=10), f.line(50, y, 400, y), f.diode(422, y, "right", size=24), f.line(446, y, 520, y)
    f.resistor(520, 620, y, peaks=5, height=14), f.line(620, y, 680, y), f.dot(680, y, r=10)
    f.text(56, 40, "P", size=40), f.text(680, 40, "Q", size=40), f.text(570, 46, "2 kΩ", size=36)
    f.text(60, 148, "+3 V", size=38), f.text(670, 148, "−5 V", size=38)
    return f


def four_gates_inputs():
    """(I) NAND with inputs 1, 1; (II) NOR with 0, 0; (III) AND with 0, 1; (IV) XOR with 1, 0."""
    f = Figure(640, 420)
    for (kind, ins, name), (x, y) in zip((("NAND", "11", "I"), ("NOR", "00", "II"), ("AND", "01", "III"), ("XOR", "10", "IV")),
                                         ((100, 90), (420, 90), (100, 290), (420, 290))):
        p, o = f.gate(kind, x, y, w=80, h=64)
        for (px, py), v in zip(p, ins):
            f.dot(x - 50, py, r=5), f.line(x - 50, py, px, py), f.text(x - 66, py + 9, v, size=26)
        f.line(*o, o[0] + 40, o[1]), f.dot(o[0] + 40, o[1], r=6)
        f.text(x + 40, y + 84, f"({name})", size=28)
    return f


def two_diode_circuits():
    """Circuit X: D1 and D2 both pointing right, each with 4 ohm, in parallel across 8 V. Circuit Y: as X but D2 points left."""
    f = Figure(760, 330)
    for ox, d2, name in ((20, "right", "X"), (400, "left", "Y")):
        l, r, t, m, b = ox, ox + 340, 60, 170, 260
        f.line(l, m, l, b), f.line(r, m, r, b), f.line(l, t, l, m), f.line(r, t, r, m)
        for y, d, lab in ((t, "right", "D<sub>1</sub>"), (m, d2, "D<sub>2</sub>")):
            f.line(l + 40, y, l + 100, y), f.diode(l + 120, y, d, size=18), f.line(l + 138, y, l + 190, y)
            f.resistor(l + 190, l + 270, y, peaks=4, height=12), f.line(l + 270, y, r - 40, y)
            f.text(l + 100, y - 24, lab, size=24), f.text(l + 230, y - 22, "4 Ω", size=24)
        f.line(l, t, l + 40, t), f.line(r - 40, t, r, t), f.line(l, m, l + 40, m), f.line(r - 40, m, r, m)
        f.line(l, b, l + 160, b), f.cell(l + 170, b, gap=16, long=22, short=12), f.line(l + 178, b, r, b)
        f.text(l + 170, b + 40, "8 V", size=26), f.text(l + 170, b + 68, f"(Circuit {name})", size=26)
    return f


def two_nots_into_nor():
    """A and B each pass through a NOT gate (G1, G2) giving C and D, which feed a NOR gate giving Y."""
    f = Figure(720, 300)
    pa, oa = f.gate("NOT", 160, 50, w=70, h=56)
    pb, ob = f.gate("NOT", 160, 230, w=70, h=56)
    for (x, y), name in ((pa[0], "A"), (pb[0], "B")):
        f.dot(40, y, r=6), f.line(40, y, x, y), f.text(20, y + 10, name, size=32)
    p3, o3 = f.gate("NOR", 460, 140, w=100, h=88)
    wire(f, oa, (400, 50), (400, p3[0][1]), p3[0]), wire(f, ob, (400, 230), (400, p3[1][1]), p3[1])
    f.line(*o3, 660, 140), f.dot(660, 140, r=7), f.text(690, 152, "Y", size=32)
    f.text(190, 106, "G<sub>1</sub>", size=28), f.text(190, 286, "G<sub>2</sub>", size=28)
    f.text(410, 40, "C", size=30, anchor="start"), f.text(410, 268, "D", size=30, anchor="start")
    return f


def or_then_not():
    """An OR gate on A and B, then a NOT gate giving Y."""
    f = Figure(720, 180)
    p, o = f.gate("OR", 160, 90, w=180, h=130)
    for (x, y), name in ((p[0], "A"), (p[1], "B")):
        f.dot(60, y, r=10), f.line(60, y, x, y), f.text(30, y + 14, name, size=40)
    pn, on = f.gate("NOT", 480, 90, w=90, h=70)
    f.line(*o, *pn[0]), f.line(*on, 660, 90), f.dot(660, 90, r=10), f.text(696, 104, "Y", size=40)
    return f


def ammeter_diode_options():
    """Four circuits, each a cell (+ on the left) and ammeter A with two diodes: (a) in series, opposite ways; (b) in series, same way;
    (c) in parallel, opposite ways; (d) in parallel, same way."""
    f = Figure(760, 240)
    for i, (ox, name) in enumerate(zip((10, 200, 390, 580), "abcd")):
        l, r, t, b = ox, ox + 160, 50, 160
        f.line(l, t, l, b), f.line(r, t, r, b)
        f.line(l, b, l + 34, b), f.cell(l + 40, b, gap=10, long=16, short=9), f.line(l + 45, b, l + 100, b), f.meter(l + 116, b, "A", r=14)
        f.line(l + 130, b, r, b), f.text(l + 30, b + 26, "+", size=18), f.text(l + 52, b + 26, "−", size=18)
        if i < 2:
            f.line(l, t, l + 30, t), f.diode(l + 46, t, "left" if i == 0 else "right", size=14), f.line(l + 60, t, l + 92, t)
            f.diode(l + 108, t, "right", size=14), f.line(l + 122, t, r, t)
        else:
            for y, d in ((t - 22, "right"), (t + 22, "left" if i == 2 else "right")):
                f.line(l + 20, y, l + 62, y), f.diode(l + 78, y, d, size=14), f.line(l + 92, y, r - 20, y)
            f.line(l + 20, t - 22, l + 20, t + 22), f.line(r - 20, t - 22, r - 20, t + 22)
            f.line(l, t, l + 20, t), f.line(r - 20, t, r, t)
        f.text(l + 80, 220, f"({name})", size=22)
    return f


def two_diodes_10v():
    """10 V cell with R1 = 2 ohm in series; then D1 (pointing down) with R2 = 3 ohm and D2 (pointing up) with R3 = 2 ohm in parallel."""
    f = Figure(640, 440)
    l, x1, x2, t, b = 80, 380, 560, 60, 400
    f.line(l, t, 160, t), f.resistor(160, 260, t, peaks=5, height=16), f.line(260, t, x2, t)
    f.line(l, t, l, 180), f.vcell(l, 190, gap=18, long=30, short=16), f.line(l, 200, l, b), f.line(l, b, x2, b)
    for x, d, rl, rv, dl in ((x1, "down", "R<sub>2</sub>", "3 Ω", "D<sub>1</sub>"), (x2, "up", "R<sub>3</sub>", "2 Ω", "D<sub>2</sub>")):
        f.line(x, t, x, 110), vdiode(f, x, 134, d), f.line(x, 156, x, 250), f.vresistor(x, 250, 340), f.line(x, 340, x, b)
        f.text(x + 30, 146, dl, size=30, anchor="start"), f.text(x - 24, 306, rl, size=30, anchor="end")
        f.text(x + 30, 306, rv, size=30, anchor="start")
    f.text(210, 36, "2 Ω", size=30), f.text(210, 106, "R<sub>1</sub>", size=30), f.text(60, 200, "10 V", size=30, anchor="end")
    return f


def gate_g_or_table(ys):
    """A goes to an OR gate and to box G; B goes to G; G's output is the OR gate's second input. Truth table with the given Y column."""
    f = Figure(760, 280)
    p, o = f.gate("OR", 300, 110, w=90, h=84)
    f.dot(70, 90, r=5), f.text(44, 100, "A", size=30), f.line(70, 90, *p[0])
    f.rect(120, 176, 54, 50), f.text(147, 211, "G", size=30)
    wire(f, (96, 90), (96, 190), (120, 190)), f.dot(96, 90, r=4)
    f.dot(70, 212, r=5), f.text(44, 222, "B", size=30), f.line(70, 212, 120, 212)
    wire(f, (174, 200), (260, 200), (260, p[1][1]), p[1])
    f.line(*o, 470, 110), f.text(490, 120, "Y", size=30)
    x, y, cw, rh = 560, 20, 60, 38
    rows = [("A", "B", "Y")] + [(a, b, v) for (a, b), v in zip(((0, 0), (0, 1), (1, 0), (1, 1)), ys)]
    f.rect(x, y, cw * 3, rh * 5, width=2)
    for i in (1, 2):
        f.line(x + cw * i, y, x + cw * i, y + rh * 5, width=2)
    for j in range(1, 5):
        f.line(x, y + rh * j, x + cw * 3, y + rh * j, width=2)
    for j, row in enumerate(rows):
        for i, v in enumerate(row):
            f.text(x + cw * (i + 0.5), y + rh * (j + 0.5) + 9, str(v), size=26)
    return f


def gate_g_table_1011():
    """A goes to an OR gate and to box G; B goes to G; G feeds the OR gate. Truth table Y = 1, 0, 1, 1."""
    return gate_g_or_table((1, 0, 1, 1))


def gate_g_table_0011():
    """A goes to an OR gate and to box G; B goes to G; G feeds the OR gate. Truth table Y = 0, 0, 1, 1."""
    return gate_g_or_table((0, 0, 1, 1))


def diode_40_40_ab():
    """A to B through two branches: 40 ohm then diode D (pointing right) on top, 40 ohm below."""
    f = Figure(760, 330)
    top, mid, bottom, l, r = 70, 180, 290, 140, 620
    f.dot(20, mid, r=7), f.line(20, mid, l, mid), f.line(l, top, l, bottom), f.dot(740, mid, r=7), f.line(r, mid, 740, mid)
    f.line(r, top, r, bottom)
    f.line(l, top, 190, top), f.resistor(190, 300, top, peaks=5, height=16), f.line(300, top, 460, top)
    f.diode(482, top, "right", size=20), f.line(502, top, r, top)
    f.line(l, bottom, 190, bottom), f.resistor(190, 300, bottom, peaks=5, height=16), f.line(300, bottom, r, bottom)
    f.text(245, 38, "40 Ω", size=30), f.text(482, 126, "D", size=30), f.text(245, 256, "40 Ω", size=30)
    f.text(20, 160, "A", size=30), f.text(740, 222, "B", size=30)
    return f


def led_photodiode_bias():
    """Four circuits: (A) photodiode with the cell's + on the left, (B) photodiode with + on the right,
    (C) LED with + on the right, (D) LED with + on the left. The diode points right on the top wire."""
    f = Figure(760, 600)
    for (name, inward, plus_left), (ox, oy) in zip((("A", True, True), ("B", True, False), ("C", False, False), ("D", False, True)),
                                                   ((20, 30), (400, 30), (20, 300), (400, 300))):
        l, r, t, b = ox, ox + 320, oy + 60, oy + 190
        f.line(l, t, l, b), f.line(r, t, r, b)
        f.line(l, t, l + 170, t), f.diode(l + 196, t, "right", size=26), f.line(l + 222, t, r, t)
        light_arrows(f, l + 196, t, inward)
        f.line(l, b, l + 120, b), f.line(l + 140, b, r, b)
        (f.cell if plus_left else (lambda x, y, **k: right_cell(f, x, y, **k)))(l + 130, b, gap=14, long=22, short=12)
        f.text(l + 112, b + 34, "+" if plus_left else "−", size=26), f.text(l + 150, b + 34, "−" if plus_left else "+", size=26)
        f.text(l + 140, b + 74, f"({name})", size=28)
    return f


def nand_or_not_c():
    """(A NAND B) and NOT C feed an OR gate giving Y."""
    f = Figure(720, 320)
    p1, o1 = f.gate("NAND", 200, 70, w=96, h=84)
    pn, on = f.gate("NOT", 200, 260, w=90, h=70)
    for (x, y), name in ((p1[0], "A"), (p1[1], "B"), (pn[0], "C")):
        f.terminal(80, y), f.line(86, y, x, y), f.text(40, y + 14, name, size=40)
    p3, o3 = f.gate("OR", 470, 160, w=100, h=84)
    wire(f, o1, (400, 70), (400, p3[0][1]), p3[0]), wire(f, on, (400, 260), (400, p3[1][1]), p3[1])
    f.line(*o3, 640, 160), f.terminal(646, 160), f.text(690, 174, "Y", size=40)
    return f


def or_nand_and_xor():
    """A and B feed both an OR gate and a NAND gate; their outputs feed an AND gate giving Y."""
    f = Figure(720, 330)
    p1, o1 = f.gate("OR", 220, 80, w=110, h=96)
    p2, o2 = f.gate("NAND", 220, 250, w=100, h=88)
    f.dot(40, p1[0][1], r=8), f.text(20, p1[0][1] + 12, "A", size=34), f.line(40, p1[0][1], *p1[0])
    f.dot(40, p1[1][1], r=8), f.text(20, p1[1][1] + 12, "B", size=34), f.line(40, p1[1][1], 92, p1[1][1])
    f.arc(100, p1[1][1], 8, 180, 360), f.line(108, p1[1][1], *p1[1])
    wire(f, (100, p1[0][1]), (100, p1[1][1] - 8)), f.line(100, p1[1][1] + 8, 100, p2[0][1]), f.line(100, p2[0][1], *p2[0])
    wire(f, (70, p1[1][1]), (70, p2[1][1]), p2[1])
    f.dot(100, p1[0][1], r=4), f.dot(70, p1[1][1], r=4)
    p3, o3 = f.gate("AND", 500, 165, w=90, h=80)
    wire(f, o1, (440, 80), (440, p3[0][1]), p3[0]), wire(f, o2, (440, 250), (440, p3[1][1]), p3[1])
    f.line(*o3, 660, 165), f.dot(660, 165, r=8), f.text(680, 210, "Y", size=34)
    return f


def nand_then_and():
    """A NAND gate on A and B whose output feeds both inputs of an AND gate giving Y."""
    f = Figure(720, 170)
    p, o = f.gate("NAND", 200, 80, w=180, h=110)
    for (x, y), name in ((p[0], "A"), (p[1], "B")):
        f.dot(60, y, r=8), f.line(60, y, x, y), f.text(30, y + 14, name, size=40)
    p2, o2 = f.gate("AND", 470, 80, w=110, h=100)
    wire(f, o, (440, 80)), wire(f, (440, p2[0][1]), (440, p2[1][1])), f.line(440, p2[0][1], *p2[0]), f.line(440, p2[1][1], *p2[1])
    f.line(*o2, 660, 80), f.dot(660, 80, r=8), f.text(696, 94, "Y", size=40)
    return f


def nand_and_not_nand_into_nor():
    """(A NAND B) and ((NOT A) NAND B) feed a NOR gate giving Y."""
    f = Figure(720, 300)
    p1, o1 = f.gate("NAND", 230, 70, w=100, h=86)
    pn, on = f.gate("NOT", 160, 200, w=60, h=40)
    p2, o2 = f.gate("NAND", 300, 220, w=100, h=86)
    f.text(30, p1[0][1] + 14, "A", size=42), f.line(60, p1[0][1], *p1[0]), f.text(30, p1[1][1] + 14, "B", size=42), f.line(60, p1[1][1], *p1[1])
    f.text(30, 214, "A", size=42), f.line(60, 200, *pn[0]), wire(f, on, (p2[0][0], p2[0][1]))
    f.text(30, p2[1][1] + 14, "B", size=42), f.line(60, p2[1][1], *p2[1])
    p3, o3 = f.gate("NOR", 520, 140, w=100, h=96)
    wire(f, o1, (460, 70), (460, p3[0][1]), p3[0]), wire(f, o2, (460, 220), (460, p3[1][1]), p3[1])
    f.line(*o3, 700, 140), f.text(660, 100, "Y", size=40)
    return f


def led_iv_curve():
    """Current I (mA) against voltage V (volt): a curve rising ever more steeply from the origin."""
    f = Figure(500, 400)
    ox, oy = 120, 320
    f.axes(ox, oy, 330, 290, size=30)
    f.curve(lambda x: oy - 2 - 270 * ((x - ox) / 160) ** 2.6, ox, ox + 160)
    f.text(70, 150, "<i>I</i>", size=36), f.line(70, 110, 70, 70, arrow=True), f.text(56, 200, "(mA)", size=30)
    f.text(ox - 26, oy + 36, "O", size=32), f.text(300, 386, "<i>V</i> → (Volt)", size=32)
    return f


def xor_from_nots_ands_or():
    """NOT A with B feeds AND 1; A with NOT B feeds AND 2; both AND outputs feed an OR gate giving Y."""
    f = Figure(720, 320)
    a1, o1 = f.gate("AND", 360, 70, w=90, h=80)
    a2, o2 = f.gate("AND", 360, 250, w=90, h=80)
    na, ona = f.gate("NOT", 190, a1[0][1], w=56, h=44)
    nb, onb = f.gate("NOT", 190, a2[1][1], w=56, h=44)
    f.text(24, a1[0][1] + 12, "A", size=36), f.line(50, a1[0][1], *na[0]), f.line(*ona, *a1[0])
    f.text(24, a2[1][1] + 12, "B", size=36), f.line(50, a2[1][1], *nb[0]), f.line(*onb, *a2[1])
    wire(f, (90, a1[0][1]), (90, a2[0][1]), a2[0]), f.dot(90, a1[0][1], r=4)
    wire(f, (130, a2[1][1]), (130, a1[1][1]), a1[1]), f.dot(130, a2[1][1], r=4)
    p3, o3 = f.gate("OR", 540, 160, w=90, h=80)
    wire(f, o1, (500, 70), (500, p3[0][1]), p3[0]), wire(f, o2, (500, 250), (500, p3[1][1]), p3[1])
    f.line(*o3, 700, 160), f.text(690, 140, "Y", size=36)
    return f


def two_nors_into_or():
    """A and B feed two NOR gates (A to the top input of the upper one and the lower one's first input; B to the others); their outputs feed an OR gate giving Y."""
    f = Figure(720, 330)
    p1, o1 = f.gate("NOR", 260, 80, w=120, h=100)
    p2, o2 = f.gate("NOR", 260, 250, w=120, h=100)
    f.text(20, p1[0][1] + 10, "A", size=30), f.line(40, p1[0][1], *p1[0])
    f.text(20, p2[1][1] + 10, "B", size=30), f.line(40, p2[1][1], *p2[1])
    wire(f, (100, p1[0][1]), (100, p2[0][1]), p2[0])
    f.dot(100, p1[0][1], r=4)
    wire(f, (140, p2[1][1]), (140, p1[1][1]), p1[1]), f.dot(140, p2[1][1], r=4)
    p3, o3 = f.gate("OR", 520, 165, w=100, h=80)
    wire(f, o1, (460, 80), (460, p3[0][1]), p3[0]), wire(f, o2, (460, 250), (460, p3[1][1]), p3[1])
    f.line(*o3, 690, 165), f.dot(690, 165, r=6), f.text(690, 205, "Y", size=30)
    return f


FIGURES = {
    "PYQ-PHY-4d85578d3267": diode_5v_to_3v,
    "PYQ-PHY-36777b1812ef": nand_or_from_nands,
    "PYQ-PHY-8a9ed7d6eaea": diode_p_to_q,
    "PYQ-PHY-3b0a13ef9735": four_gates_inputs,
    "PYQ-PHY-00e2a5c82ac7": two_diode_circuits,
    "PYQ-PHY-8ca9770b87b1": two_nots_into_nor,
    "PYQ-PHY-54f8beb53fa1": or_then_not,
    "PYQ-PHY-fe61b698f047": ammeter_diode_options,
    "PYQ-PHY-fd7c44df3cf6": two_diodes_10v,
    "PYQ-PHY-375ca3d7b543": gate_g_table_1011,
    "PYQ-PHY-972a68ea26a6": diode_40_40_ab,
    "PYQ-PHY-047bd0ef275b": led_photodiode_bias,
    "PYQ-PHY-eecb9c7f9dc7": nand_or_not_c,
    "PYQ-PHY-4b947d081a2c": or_nand_and_xor,
    "PYQ-PHY-9558866028ed": nand_then_and,
    "PYQ-PHY-b78c01e5ef47": nand_and_not_nand_into_nor,
    "PYQ-PHY-765bc7cf9b3b": led_iv_curve,
    "PYQ-PHY-8b397a063de8": xor_from_nots_ands_or,
    "PYQ-PHY-ff3607302410": two_nors_into_or,
    "PYQ-PHY-2c9cbbe930a6": gate_g_table_0011,
}
