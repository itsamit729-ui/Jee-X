"""Physics: semiconductors (part 1) - diode circuits and logic gates."""

from figlib import Figure


def wire(f, *points):
    f.polyline(list(points))


def zener_circuit():
    """18 V battery, R1 = 800 ohm in series, then R2 = 1800 ohm in parallel with a 9 V Zener diode."""
    f = Figure(640, 460)
    left, mid, right, top, node, bottom = 114, 300, 482, 56, 224, 416
    wire(f, (left, 226), (left, top), (mid, top)), f.arrowhead(232, top, 0, size=18), f.text(206, 36, "<i>I</i>", size=28)
    f.vcell(left, 236, gap=18, long=30, short=16), f.line(left, 245, left, 262), f.vcell(left, 272, gap=18, long=30, short=16)
    wire(f, (left, 282), (left, bottom), (right, bottom))
    f.line(mid, top, mid, 96), f.vresistor(mid, 96, 182), f.line(mid, 182, mid, 268), f.vresistor(mid, 268, 356)
    f.line(mid, 356, mid, bottom), f.dot(mid, node)
    wire(f, (mid, node), (right, node), (right, 300)), f.line(right, 336, right, bottom)
    f.path([(right - 21, 336), (right + 21, 336), (right, 300)], close=True, fill="#fff")
    wire(f, (right - 28, 308), (right - 22, 300), (right + 22, 300), (right + 28, 292))
    f.text(86, 192, "+", size=26), f.text(86, 312, "−", size=26), f.text(68, 252, "18 V", size=26, anchor="end")
    f.text(258, 148, "<i>R</i><sub>1</sub>", size=26), f.text(326, 150, "800 Ω", size=26, anchor="start")
    f.text(258, 320, "<i>R</i><sub>2</sub>", size=26), f.text(326, 322, "1800 Ω", size=26, anchor="start")
    f.text(520, 326, "<i>V</i><sub>z</sub> = 9 V", size=26, anchor="start")
    return f


def or_then_and():
    """Inputs A and B feed an OR gate; its output and input C feed an AND gate giving Y."""
    f = Figure(680, 230)
    pins, out = f.gate("OR", 200, 90, w=100, h=92)
    f.line(66, 67, pins[0][0], 67), f.line(66, 113, pins[1][0], 113)
    pins2, out2 = f.gate("AND", 410, 120, w=104, h=92)
    wire(f, out, (355, 90), (355, pins2[0][1]), pins2[0]), f.line(66, pins2[1][1], *pins2[1])
    f.line(*out2, 590, 120)
    for y, name in ((67, "A"), (113, "B"), (pins2[1][1], "C")):
        f.dot(66, y, r=5), f.text(38, y + 10, name, size=28)
    f.dot(590, 120, r=5), f.text(616, 130, "Y", size=28)
    return f


def diode_resistor_parallel():
    """Between A and B: 30 ohm in series with an ideal diode D, in parallel with another 30 ohm."""
    f = Figure(660, 330)
    left, right, top, mid, bottom = 100, 452, 92, 174, 264
    f.line(28, mid, left, mid), f.line(right, mid, 528, mid), f.terminal(22, mid), f.terminal(534, mid)
    f.line(left, top, left, bottom), f.line(right, top, right, bottom)
    f.line(left, top, 150, top), f.resistor(150, 270, top, height=15), f.line(270, top, 328, top)
    f.diode(348, top, "right", size=20), f.line(368, top, right, top)
    f.line(left, bottom, 150, bottom), f.resistor(150, 300, bottom, height=15, peaks=6), f.line(300, bottom, right, bottom)
    f.text(22, 214, "A", size=30), f.text(536, 214, "B", size=30)
    f.text(210, 152, "30 Ω", size=30), f.text(226, 318, "30 Ω", size=30)
    f.text(368, 148, "D", size=28), f.text(470, 62, "ideal diode", size=28)
    return f


def nand_not_nor_circuit():
    """Y is the NOR of two signals: the NAND of A and B, and the NOR of (NOT A) and B."""
    f = Figure(680, 380)
    p1, o1 = f.gate("NAND", 148, 70, w=72, h=78)
    f.line(66, p1[0][1], *p1[0]), f.line(66, p1[1][1], *p1[1])
    pn, on = f.gate("NOT", 150, 240, w=84, h=70)
    f.line(66, 240, *pn[0])
    p2, o2 = f.gate("NOR", 332, 262, w=72, h=78)
    wire(f, on, (300, 240), (300, p2[0][1]), p2[0])
    wire(f, (66, 296), (300, 296), (300, p2[1][1]), p2[1])
    p3, o3 = f.gate("NOR", 500, 166, w=76, h=80)
    wire(f, o1, (448, 70), (448, p3[0][1]), p3[0]), wire(f, o2, (448, 262), (448, p3[1][1]), p3[1])
    f.line(*o3, 620, 166)
    f.text(44, p1[0][1] + 10, "A", size=30), f.text(44, p1[1][1] + 12, "B", size=30)
    f.text(44, 250, "A", size=30), f.text(44, 306, "B", size=30), f.text(640, 176, "Y", size=30)
    return f


def three_diodes_battery():
    """Diodes D1 (with 150 ohm), D2 (with 50 ohm) and D3 reversed (with 50 ohm) in parallel, fed by 5 V through 100 ohm."""
    f = Figure(470, 420)
    left, right = 30, 412
    rows = ((66, "D1", "right", "150 Ω"), (150, "D2", "right", "50 Ω"), (234, "D3", "left", "50 Ω"))
    for y, name, pointing, value in rows:
        f.line(left, y, 82, y), f.diode(102, y, pointing, size=20), f.line(122, y, 215, y)
        f.resistor(215, 305, y, peaks=4, height=16), f.line(305, y, right, y)
        f.text(60, y - 22, name, size=26), f.text(356, y - 18, value, size=26)
    y = 318
    f.line(left, y, 86, y), f.cell(96, y, gap=20, long=34, short=18), f.line(106, y, 205, y)
    f.resistor(205, 295, y, peaks=4, height=16), f.line(295, y, right, y)
    f.line(left, 66, left, y), f.line(right, 66, right, y)
    f.text(346, y - 18, "100 Ω", size=26), f.text(96, 388, "5 V", size=26)
    return f


def silicon_diode_milliammeter():
    """A silicon diode, a 200 ohm resistor and a milliammeter in series with a 5 V battery."""
    f = Figure(660, 380)
    left, right, top, bottom = 50, 532, 106, 296
    f.line(left, top, 128, top), f.diode(160, top, "right", size=32), f.line(192, top, 330, top)
    f.resistor(330, 470, top, peaks=6, height=18), f.line(470, top, right, top)
    f.line(left, top, left, bottom), f.line(right, top, right, 172), f.line(right, 236, right, bottom)
    f.circle(right, 204, 32), f.vector(516, 220, 548, 188, width=2.5)
    f.line(left, bottom, 142, bottom), f.cell(152, bottom, gap=18, long=26, short=14), f.line(161, bottom, 170, bottom)
    f.cell(179, bottom, gap=18, long=26, short=14), f.line(188, bottom, right, bottom)
    f.text(400, 62, "200 Ω", size=32), f.text(152, 190, "Si diode", size=32), f.text(590, 262, "mA", size=30)
    f.text(104, 336, "+", size=28), f.text(226, 334, "−", size=28), f.text(165, 372, "5 V", size=30)
    return f


def nand_nor_or_circuit():
    """The NAND of A and B and the NOR of B and C feed an OR gate giving Y."""
    f = Figure(680, 350)
    p1, o1 = f.gate("NAND", 238, 106, w=86, h=92)
    p2, o2 = f.gate("NOR", 238, 266, w=86, h=92)
    f.line(76, p1[0][1], *p1[0]), f.line(76, p1[1][1], *p1[1]), f.line(76, p2[1][1], *p2[1])
    wire(f, (168, p1[1][1]), (168, p2[0][1]), p2[0]), f.dot(168, p1[1][1], r=4)
    p3, o3 = f.gate("OR", 462, 196, w=92, h=84)
    wire(f, o1, (400, 106), (400, p3[0][1]), p3[0]), wire(f, o2, (400, 266), (400, p3[1][1]), p3[1])
    f.line(*o3, 584, 196), f.terminal(590, 196)
    for y, name in ((p1[0][1], "A"), (p1[1][1], "B"), (p2[1][1], "C")):
        f.terminal(70, y), f.text(42, y + 10, name, size=30)
    f.text(616, 206, "Y", size=30)
    return f


def gate_g_with_truth_table():
    """Y = A OR G(A, B), where G is an unknown two-input gate, with the truth table the circuit must give."""
    f = Figure(1000, 250)
    pins, out = f.gate("OR", 380, 104, w=108, h=110)
    f.line(52, pins[0][1], *pins[0]), f.dot(52, pins[0][1], r=6), f.dot(52, 196, r=6)
    f.block(190, 168, 56, 56, "G", size=30)
    wire(f, (130, pins[0][1]), (130, 182), (190, 182)), f.dot(130, pins[0][1], r=4), f.line(52, 196, 62, 196)
    f.line(62, 196, 100, 196), wire(f, (100, 196), (150, 196), (150, 210), (190, 210))
    wire(f, (246, 196), (330, 196), (330, pins[1][1]), pins[1])
    f.line(*out, 548, 104), f.dot(548, 104, r=6)
    f.text(28, pins[0][1] + 10, "A", size=30), f.text(28, 206, "B", size=30), f.text(574, 114, "Y", size=30)
    x0, y0, cw, ch = 690, 26, 72, 40
    rows = (("A", "B", "Y"), ("0", "0", "0"), ("0", "1", "0"), ("1", "0", "1"), ("1", "1", "1"))
    f.rect(x0, y0, cw * 3, ch * 5)
    for i in range(1, 5):
        f.line(x0, y0 + ch * i, x0 + cw * 3, y0 + ch * i, width=2)
    for j in (1, 2):
        f.line(x0 + cw * j, y0, x0 + cw * j, y0 + ch * 5, width=2)
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            f.text(x0 + cw * (j + 0.5), y0 + ch * i + 29, cell, size=26)
    return f


def and_and_or_with_inverter():
    """C = A AND B, D = (NOT A) AND B, and E = C OR D."""
    f = Figure(680, 270)
    p1, o1 = f.gate("AND", 280, 62, w=66, h=56)
    p2, o2 = f.gate("AND", 280, 192, w=66, h=56)
    f.dot(50, p1[0][1], r=5), f.line(50, p1[0][1], *p1[0]), f.dot(50, p2[1][1], r=5), f.line(50, p2[1][1], *p2[1])
    f.dot(110, p1[0][1], r=4), f.line(110, p1[0][1], 110, 92)
    f.path([(96, 92), (124, 92), (110, 118)], close=True, fill="#fff"), f.circle(110, 124, 6, fill="#fff")
    wire(f, (110, 130), (110, p2[0][1]), (206, p2[0][1]))
    f.add(f'<path d="M206,{p2[0][1]} a10,10 0 0 1 20,0" stroke-width="3"/>'), f.line(226, p2[0][1], *p2[0])
    wire(f, (216, p2[1][1]), (216, p1[1][1]), p1[1]), f.dot(216, p2[1][1], r=4)
    p3, o3 = f.gate("OR", 492, 127, w=80, h=60)
    wire(f, o1, (410, 62), (410, p3[0][1]), p3[0]), wire(f, o2, (410, 192), (410, p3[1][1]), p3[1])
    f.line(*o3, 632, 127), f.dot(632, 127, r=5)
    f.text(28, p1[0][1] + 8, "A", size=26), f.text(28, p2[1][1] + 8, "B", size=26)
    f.text(388, 44, "C", size=26), f.text(388, 226, "D", size=26), f.text(632, 108, "E", size=26)
    return f


def and_then_nand():
    """Two inputs feed an AND gate; its output and the third input feed a NAND gate giving Y."""
    f = Figure(680, 300)
    p1, o1 = f.gate("AND", 132, 108, w=120, h=104)
    p2, o2 = f.gate("NAND", 388, 152, w=124, h=112)
    for y in (p1[0][1], p1[1][1], p2[1][1]):
        f.dot(46, y, r=8)
    f.line(46, p1[0][1], *p1[0]), f.line(46, p1[1][1], *p1[1]), f.line(46, p2[1][1], *p2[1])
    wire(f, o1, (330, 108), (330, p2[0][1]), p2[0]), f.line(*o2, 580, 152)
    f.text(604, 162, "Y", size=30)
    return f


def four_input_three_outputs():
    """Y1 = NOT(NOR(A, B)), Y2 = C AND D, and Y3 = NOR(Y1, Y2)."""
    f = Figure(680, 300)
    p1, o1 = f.gate("NOR", 122, 76, w=76, h=66)
    pn, on = f.gate("NOT", 292, 76, w=60, h=52)
    p2, o2 = f.gate("AND", 162, 206, w=64, h=66)
    p3, o3 = f.gate("NOR", 448, 136, w=80, h=68)
    f.line(48, p1[0][1], *p1[0]), f.line(48, p1[1][1], *p1[1]), f.line(48, p2[0][1], *p2[0]), f.line(48, p2[1][1], *p2[1])
    f.line(*o1, *pn[0]), wire(f, on, (392, 76), (392, p3[0][1]), p3[0])
    wire(f, o2, (392, 206), (392, p3[1][1]), p3[1]), f.line(*o3, 606, 136)
    for y, name in ((p1[0][1], "A"), (p1[1][1], "B"), (p2[0][1], "C"), (p2[1][1], "D")):
        f.text(26, y + 10, name, size=28)
    f.text(374, 52, "<i>Y</i><sub>1</sub>", size=28), f.text(374, 250, "<i>Y</i><sub>2</sub>", size=28)
    f.text(606, 112, "<i>Y</i><sub>3</sub>", size=28)
    return f


def xy_junction_battery():
    """Semiconductors X and Y joined end to end; the battery's positive terminal is connected to X."""
    f = Figure(640, 440)
    f.rect(188, 70, 180, 86), f.line(278, 70, 278, 156)
    f.text(233, 128, "X", size=40), f.text(323, 128, "Y", size=40)
    wire(f, (188, 113), (52, 113), (52, 352), (258, 352)), wire(f, (282, 352), (522, 352), (522, 113), (368, 113))
    f.cell(270, 352, gap=24, long=44, short=26)
    return f


FIGURES = {
    "PYQ-PHY-13b13f6e8da6": zener_circuit,
    "PYQ-PHY-20af162cf897": or_then_and,
    "PYQ-PHY-246c537173b6": diode_resistor_parallel,
    "PYQ-PHY-25b040f182ff": nand_not_nor_circuit,
    "PYQ-PHY-29e3414a8015": three_diodes_battery,
    "PYQ-PHY-446100bad5a0": silicon_diode_milliammeter,
    "PYQ-PHY-469daad471b6": nand_nor_or_circuit,
    "PYQ-PHY-53e7866c94e3": gate_g_with_truth_table,
    "PYQ-PHY-67f1b976742c": and_and_or_with_inverter,
    "PYQ-PHY-6b04168fad60": and_then_nand,
    "PYQ-PHY-87bee246971d": four_input_three_outputs,
    "PYQ-PHY-8caf23fbe7e9": xy_junction_battery,
}
