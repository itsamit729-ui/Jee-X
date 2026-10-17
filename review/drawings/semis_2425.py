"""Physics (MHT-CET 2024-25): semiconductors - diode circuits and logic gates."""

from figlib import Figure


def wire(f, *points):
    f.polyline(list(points))


def vzener(f, x, y1, y2, pointing="up"):
    """A Zener diode on a vertical wire from y1 (top) to y2, its arrow pointing `pointing`."""
    mid = (y1 + y2) / 2
    if pointing == "up":
        bar, base = mid - 22, mid + 22
    else:
        bar, base = mid + 22, mid - 22
    f.line(x, y1, x, min(bar, base)), f.line(x, max(bar, base), x, y2)
    f.path([(x - 24, base), (x + 24, base), (x, bar)], close=True, fill="#fff")
    wire(f, (x - 32, bar + 9), (x - 24, bar), (x + 24, bar), (x + 32, bar - 9))


def two_diodes_branches():
    """D1 (forward, left to right) with 20 ohm on top; D2 (pointing left) with 40 ohm below; 10 V cell at the bottom."""
    f = Figure(640, 520)
    left, right, top, mid, bottom = 40, 600, 120, 270, 440
    f.diode(170, top, "right"), f.line(left, top, 150, top), f.line(190, top, 300, top)
    f.resistor(300, 520, top, peaks=6, height=22), f.line(520, top, right, top)
    f.diode(170, mid, "left"), f.line(left, mid, 150, mid), f.line(190, mid, 300, mid)
    f.resistor(300, 520, mid, peaks=6, height=22), f.line(520, mid, right, mid)
    f.line(left, top, left, bottom), f.line(right, top, right, bottom)
    f.line(left, bottom, 309, bottom), f.line(331, bottom, right, bottom), f.cell(320, bottom)
    f.text(170, 76, "D<sub>1</sub>", size=34), f.text(170, 228, "D<sub>2</sub>", size=34)
    f.text(410, 76, "20 Ω", size=34), f.text(410, 226, "40 Ω", size=34), f.text(320, 506, "10 V", size=34)
    return f


def and_then_nand_with_c():
    """A AND B, together with C, feed a NAND gate giving Y."""
    f = Figure(680, 300)
    p1, o1 = f.gate("AND", 200, 70, w=86, h=74)
    p2, o2 = f.gate("NAND", 470, 156, w=86, h=74)
    for (x, y), name in ((p1[0], "A"), (p1[1], "B")):
        f.terminal(84, y), f.line(90, y, x, y), f.text(46, y + 12, name, size=34)
    wire(f, o1, (420, 70), (420, p2[0][1]), p2[0])
    f.terminal(84, 252), wire(f, (90, 252), (420, 252), (420, p2[1][1]), p2[1]), f.text(46, 264, "C", size=34)
    f.line(*o2, 620, 156), f.text(646, 168, "Y", size=34)
    return f


def nand_or_and():
    """NAND of A, B and OR of A, B feed an AND gate giving Y."""
    f = Figure(680, 300)
    p1, o1 = f.gate("NAND", 170, 70, w=86, h=80)
    p2, o2 = f.gate("OR", 170, 226, w=96, h=80)
    for (x, y), name in ((p1[0], "A"), (p1[1], "B"), (p2[0], "A"), (p2[1], "B")):
        f.line(70, y, x, y), f.text(44, y + 12, name, size=34)
    p3, o3 = f.gate("AND", 450, 148, w=90, h=80)
    wire(f, o1, (370, 70), (370, p3[0][1]), p3[0]), wire(f, o2, (370, 226), (370, p3[1][1]), p3[1])
    f.line(*o3, 620, 148), f.text(646, 160, "Y", size=34)
    return f


def zener_with_series_r():
    """10 V supply (+ on top) through R to a Zener diode across the output."""
    f = Figure(640, 300)
    top, bottom, zx = 60, 270, 470
    f.line(20, top, 230, top), f.resistor(230, 360, top, peaks=4, height=18), f.line(360, top, 620, top)
    f.line(20, bottom, 620, bottom)
    vzener(f, zx, top, bottom, pointing="up")
    f.text(295, 36, "<i>R</i>", size=30)
    f.text(30, 100, "+", size=30), f.text(30, 238, "−", size=30), f.text(20, 176, "10 V", size=30, anchor="start")
    return f


def truth_table(f, x, y, rows, head=("A", "B", "Y"), cw=56, rh=40, size=26, caption=""):
    """A ruled truth table with its top-left corner at (x, y)."""
    cols, n = len(head), len(rows) + 1
    f.rect(x, y, cw * cols, rh * n, width=2)
    for i in range(1, cols):
        f.line(x + cw * i, y, x + cw * i, y + rh * n, width=2)
    for j in range(1, n):
        f.line(x, y + rh * j, x + cw * cols, y + rh * j, width=2)
    for j, row in enumerate([head, *rows]):
        for i, v in enumerate(row):
            f.text(x + cw * (i + 0.5), y + rh * (j + 0.5) + size * 0.35, str(v), size=size)
    if caption:
        f.text(x + cw * cols / 2, y + rh * n + size + 6, caption, size=size)


def four_nand_xor():
    """NAND of A, B (N1); NAND of A, N1 and NAND of N1, B; both feed a fourth NAND giving Y."""
    f = Figure(760, 340)
    p1, o1 = f.gate("NAND", 180, 170, w=80, h=76)
    p2, o2 = f.gate("NAND", 380, 66, w=80, h=76)
    p3, o3 = f.gate("NAND", 380, 274, w=80, h=76)
    p4, o4 = f.gate("NAND", 600, 170, w=80, h=76)
    f.terminal(60, p1[0][1]), f.terminal(60, p1[1][1])
    f.text(34, p1[0][1] + 10, "A", size=30), f.text(34, p1[1][1] + 12, "B", size=30)
    f.line(66, p1[0][1], *p1[0]), f.line(66, p1[1][1], *p1[1])
    wire(f, (100, p1[0][1]), (100, p2[0][1]), p2[0]), f.dot(100, p1[0][1], r=4)
    wire(f, (120, p1[1][1]), (120, p3[1][1]), p3[1]), f.dot(120, p1[1][1], r=4)
    wire(f, o1, (330, 170)), wire(f, (330, p2[1][1]), (330, p3[0][1]))
    f.line(330, p2[1][1], *p2[1]), f.line(330, p3[0][1], *p3[0]), f.dot(330, 170, r=4)
    wire(f, o2, (540, 66), (540, p4[0][1]), p4[0]), wire(f, o3, (540, 274), (540, p4[1][1]), p4[1])
    f.line(*o4, 730, 170), f.text(746, 180, "Y", size=30)
    return f


def diode_3v_to_1v():
    """3 V terminal, diode D (pointing right), 100 ohm, 1 V terminal."""
    f = Figure(700, 170)
    y = 66
    f.dot(110, y, r=7), f.line(110, y, 238, y), f.diode(258, y, "right"), f.line(278, y, 370, y)
    f.resistor(370, 500, y, peaks=4, height=24), f.line(500, y, 600, y), f.dot(600, y, r=7)
    f.text(56, y + 14, "3 V", size=38), f.text(650, y + 14, "1 V", size=38)
    f.text(258, 144, "D", size=36), f.text(436, 144, "100 Ω", size=36)
    return f


def not_nand_tables():
    """NOT A and B feed a NAND gate giving Y; four truth tables (P), (Q), (R), (S)."""
    f = Figure(760, 640)
    pn, on = f.gate("NOT", 200, 50, w=56, h=44)
    p2, o2 = f.gate("NAND", 470, 90, w=70, h=60)
    f.dot(70, 50, r=5), f.line(70, 50, *pn[0]), f.text(46, 60, "A", size=28)
    wire(f, on, (420, 50), (420, p2[0][1]), p2[0])
    f.dot(70, 160, r=5), wire(f, (70, 160), (420, 160), (420, p2[1][1]), p2[1]), f.text(46, 170, "B", size=28)
    f.line(*o2, 600, 90), f.arrowhead(612, 90, 0), f.text(640, 100, "Y", size=28)
    tables = {"P": (1, 1, 1, 0), "Q": (0, 1, 0, 0), "R": (1, 0, 1, 1), "S": (0, 1, 1, 1)}
    for (name, ys), (x, y) in zip(tables.items(), ((40, 220), (400, 220), (40, 430), (400, 430))):
        truth_table(f, x, y, [(a, b, v) for (a, b), v in zip(((0, 0), (0, 1), (1, 0), (1, 1)), ys)],
                    cw=70, rh=30, size=22, caption=f"({name})")
    return f


def diode_reverse_minus2_minus5():
    """-2 V terminal, 500 ohm, then a diode with N on the left and P on the right, to a -5 V terminal."""
    f = Figure(720, 190)
    y = 80
    f.dot(40, y, r=8), f.line(40, y, 140, y), f.resistor(140, 300, y, peaks=4, height=22), f.line(300, y, 440, y)
    f.diode(460, y, "left"), f.line(480, y, 680, y), f.dot(680, y, r=8)
    f.text(56, 46, "−2 V", size=34), f.text(660, 46, "−5 V", size=34), f.text(220, 150, "500 Ω", size=34)
    f.text(438, 158, "N", size=30), f.text(484, 158, "P", size=30)
    return f


def gate_g_then_or_table():
    """A goes to an OR gate and to box G; B goes to G; G's output is the OR gate's second input. Truth table Y = 1, 1, 1, 1."""
    f = Figure(760, 280)
    p, o = f.gate("OR", 300, 110, w=90, h=84)
    f.dot(70, 90, r=5), f.text(44, 100, "A", size=30), f.line(70, 90, *p[0])
    f.rect(120, 176, 54, 50), f.text(147, 211, "G", size=30)
    wire(f, (96, 90), (96, 190), (120, 190)), f.dot(96, 90, r=4)
    f.dot(70, 212, r=5), f.text(44, 222, "B", size=30), f.line(70, 212, 120, 212)
    wire(f, (174, 200), (260, 200), (260, p[1][1]), p[1])
    f.line(*o, 470, 110), f.text(490, 120, "Y", size=30)
    truth_table(f, 560, 20, [(0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 1)], cw=60, rh=38, size=26, caption="Truth table")
    return f


def not_a_or_b_and_c():
    """NOT A and (B AND C) feed an OR gate giving Y."""
    f = Figure(680, 330)
    pn, on = f.gate("NOT", 174, 72, w=92, h=80)
    p2, o2 = f.gate("AND", 174, 250, w=100, h=88)
    f.line(76, 72, *pn[0]), f.line(76, p2[0][1], *p2[0]), f.line(76, p2[1][1], *p2[1])
    p3, o3 = f.gate("OR", 400, 160, w=104, h=88)
    wire(f, on, (358, 72), (358, p3[0][1]), p3[0]), wire(f, o2, (358, 250), (358, p3[1][1]), p3[1])
    f.line(*o3, 590, 160)
    for y, name in ((72, "A"), (p2[0][1], "B"), (p2[1][1], "C")):
        f.dot(76, y, r=5), f.text(50, y + 12, name, size=34)
    f.dot(590, 160, r=5), f.text(616, 172, "Y", size=34)
    return f


def nand_nor_tied_not():
    """NAND of A and B feeds both inputs of a NOR gate, then a NOT gate gives Y."""
    f = Figure(720, 170)
    p1, o1 = f.gate("NAND", 140, 84, w=96, h=80)
    for (x, y), name in ((p1[0], "A"), (p1[1], "B")):
        f.dot(60, y, r=6), f.line(60, y, x, y), f.text(34, y + 12, name, size=32)
    p2, o2 = f.gate("NOR", 340, 84, w=90, h=80)
    f.line(*o1, 300, 84), wire(f, (300, p2[0][1]), (300, p2[1][1]))
    f.line(300, p2[0][1], *p2[0]), f.line(300, p2[1][1], *p2[1])
    pn, on = f.gate("NOT", 500, 84, w=58, h=46)
    f.line(*o2, *pn[0]), f.line(*on, 640, 84), f.dot(640, 84, r=6), f.text(674, 96, "Y", size=32)
    return f


def xor_from_and_or_not():
    """A feeds AND 1 and a NOT gate; B feeds AND 2 and a NOT gate; NOT A goes to AND 2, NOT B to AND 1; an OR gate gives Y."""
    f = Figure(760, 330)
    a1, o1 = f.gate("AND", 400, 70, w=90, h=80)
    a2, o2 = f.gate("AND", 400, 260, w=90, h=80)
    na, ona = f.gate("NOT", 170, 130, w=56, h=44)
    nb, onb = f.gate("NOT", 170, 200, w=56, h=44)
    f.dot(50, a1[0][1], r=5), f.text(28, a1[0][1] + 10, "A", size=30), f.line(50, a1[0][1], *a1[0])
    f.dot(50, a2[1][1], r=5), f.text(28, a2[1][1] + 10, "B", size=30), f.line(50, a2[1][1], *a2[1])
    wire(f, (120, a1[0][1]), (120, 130), na[0]), f.dot(120, a1[0][1], r=4)
    wire(f, (120, a2[1][1]), (120, 200), nb[0]), f.dot(120, a2[1][1], r=4)
    wire(f, ona, (300, 130), (340, a2[0][1]), a2[0])
    wire(f, onb, (300, 200), (340, a1[1][1]), a1[1])
    p3, o3 = f.gate("OR", 580, 165, w=90, h=80)
    wire(f, o1, (540, 70), (540, p3[0][1]), p3[0]), wire(f, o2, (540, 260), (540, p3[1][1]), p3[1])
    f.line(*o3, 700, 165), f.dot(700, 165, r=5), f.text(690, 210, "Y output", size=26)
    return f


def npn_as_two_diodes():
    """(a)-(d): E and C terminals, base lead B from the middle, with the two diodes in the four possible directions."""
    f = Figure(1000, 520)
    # (left diode, right diode) directions
    layouts = {"a": ("right", "right"), "b": ("left", "right"), "c": ("right", "left"), "d": ("left", "left")}
    for (name, (d1, d2)), (ox, oy) in zip(layouts.items(), ((0, 0), (500, 0), (0, 260), (500, 260))):
        y = oy + 60
        f.dot(ox + 50, y, r=5), f.line(ox + 50, y, ox + 120, y), f.diode(ox + 140, y, d1, size=24)
        f.line(ox + 164, y, ox + 300, y), f.diode(ox + 320, y, d2, size=24), f.line(ox + 344, y, ox + 420, y)
        f.dot(ox + 420, y, r=5), f.line(ox + 232, y, ox + 232, y + 80), f.dot(ox + 232, y + 80, r=5)
        f.text(ox + 26, y + 10, "E", size=28), f.text(ox + 446, y + 10, "C", size=28)
        f.text(ox + 232, y + 116, "B", size=28), f.text(ox + 232, y + 170, f"({name})", size=28)
    return f


def two_cells_diode_3ohm():
    """A, a -4 V cell (+ on the left), a diode pointing right, 3 ohm, a -1 V cell (+ on the right), B."""
    f = Figure(760, 170)
    y = 66
    f.dot(40, y, r=8), f.line(40, y, 110, y), f.cell(122, y, gap=18, long=30, short=16), f.line(131, y, 220, y)
    f.diode(242, y, "right", size=24), f.line(266, y, 330, y), f.resistor(330, 480, y, peaks=6, height=26)
    f.line(480, y, 593, y), f.line(611, y, 700, y), f.dot(700, y, r=8)
    with f.rotated(180, 602, y):  # positive plate on the right
        f.cell(602, y, gap=18, long=30, short=16)
    f.text(18, y + 12, "A", size=34, anchor="middle"), f.text(732, y + 12, "B", size=34)
    f.text(110, 24, "+", size=26), f.text(140, 24, "−", size=26), f.text(122, 146, "−4 V", size=32)
    f.text(590, 24, "−", size=26), f.text(620, 24, "+", size=26), f.text(602, 146, "−1 V", size=32)
    f.text(405, 146, "3 Ω", size=32)
    return f


def nand_combinations_i_ii():
    """(I): two NAND gates with tied inputs, each at 0, feed a third NAND. (II): a NAND gate feeds a NAND with tied inputs."""
    f = Figure(760, 470)
    def tied_nand(x, y, w=80, h=70):
        p, o = f.gate("NAND", x, y, w=w, h=h)
        wire(f, (x - 30, p[0][1]), (x - 30, p[1][1])), f.line(x - 30, p[0][1], *p[0]), f.line(x - 30, p[1][1], *p[1])
        return (x - 30, y), o
    i1, o1 = tied_nand(200, 60)
    i2, o2 = tied_nand(200, 200)
    for (x, y) in (i1, i2):
        f.dot(60, y, r=6), f.line(60, y, x, y), f.text(36, y + 11, "0", size=32)
    p3, o3 = f.gate("NAND", 560, 130, w=80, h=70)
    wire(f, o1, (440, 60), (440, p3[0][1]), p3[0]), wire(f, o2, (440, 200), (440, p3[1][1]), p3[1])
    f.line(*o3, 740, 130), f.text(320, 280, "(I)", size=32)
    p4, o4 = f.gate("NAND", 230, 380, w=80, h=70)
    for (x, y) in p4:
        f.dot(150, y, r=6), f.line(150, y, x, y)
    i5, o5 = tied_nand(460, 380)
    f.line(*o4, *i5), f.line(*o5, 640, 380), f.terminal(646, 380)
    f.text(320, 454, "(II)", size=32)
    return f


def zener_15v_with_1k_load():
    """20 V input (+ top, - bottom) through 250 ohm to a 15 V Zener in parallel with a 1 kilo-ohm load."""
    f = Figure(760, 440)
    top, bottom, zx, rx = 60, 400, 380, 620
    f.terminal(60, top), f.terminal(60, bottom)
    f.line(66, top, 170, top), f.resistor(170, 280, top, peaks=4, height=18), f.line(280, top, rx, top)
    f.line(66, bottom, rx, bottom), vzener(f, zx, top, bottom, pointing="up")
    f.line(rx, top, rx, 180), f.vresistor(rx, 180, 300), f.line(rx, 300, rx, bottom)
    f.text(30, top + 10, "+", size=30), f.text(30, bottom + 10, "−", size=30), f.text(40, 240, "20 V", size=30, anchor="start")
    f.text(225, 120, "250 Ω", size=30), f.text(404, 120, "+", size=28), f.text(404, 320, "15 V", size=30, anchor="start")
    f.text(644, 250, "1 kΩ", size=30, anchor="start")
    return f


def zener_24v_rs_rl():
    """24 V battery, Rs = 300 ohm, a 15 V Zener (current Iz) in parallel with RL = 1200 ohm across the output terminals."""
    f = Figure(760, 400)
    left, top, bottom, zx, rx, ox = 40, 70, 370, 330, 480, 640
    f.line(left, top, 180, top), f.resistor(180, 280, top, peaks=4, height=20), f.line(280, top, ox, top)
    f.arrowhead(130, top, 0, size=18)
    f.line(left, top, left, 190), f.vcell(left, 200, gap=14, long=26, short=14), f.vcell(left, 230, gap=14, long=26, short=14)
    f.line(left, 240, left, bottom), f.line(left, bottom, ox, bottom)
    vzener(f, zx, top, bottom, pointing="up"), f.arrowhead(zx, 140, 90, size=18)
    f.line(rx, top, rx, 180), f.vresistor(rx, 180, 290), f.line(rx, 290, rx, bottom), f.arrowhead(rx, 140, 90, size=18)
    f.line(ox, top, ox, 190), f.terminal(ox, 196), f.terminal(ox, 264), f.line(ox, 270, ox, bottom)
    f.text(230, 42, "<i>R</i><sub>S</sub>", size=30), f.text(230, 128, "300 Ω", size=30)
    f.text(18, 194, "+", size=26), f.text(64, 226, "24 V", size=30, anchor="start")
    f.text(352, 150, "<i>I</i><sub>z</sub>", size=30, anchor="start"), f.text(290, 330, "15 V", size=30)
    f.text(510, 250, "<i>R</i><sub>L</sub>", size=30, anchor="start"), f.text(500, 330, "1200 Ω", size=30, anchor="start")
    f.text(662, 220, "output", size=28, anchor="start"), f.text(662, 256, "voltage", size=28, anchor="start")
    return f


def nor_and_nand_tables():
    """NOR of A, B and AND of A, B feed a NAND gate giving Y; four truth tables (P), (Q), (R), (S)."""
    f = Figure(760, 640)
    p1, o1 = f.gate("NOR", 180, 60, w=70, h=56)
    p2, o2 = f.gate("AND", 180, 160, w=70, h=56)
    f.terminal(40, p1[0][1]), f.text(18, p1[0][1] + 10, "A", size=28), f.line(46, p1[0][1], *p1[0])
    f.terminal(40, p2[1][1]), f.text(18, p2[1][1] + 10, "B", size=28), f.line(46, p2[1][1], *p2[1])
    wire(f, (90, p1[0][1]), (90, p2[0][1]), p2[0]), f.dot(90, p1[0][1], r=4)
    # B's branch rises to the NOR gate, hopping over A's branch to the AND gate
    f.line(120, p2[1][1], 120, p2[0][1] + 8), f.arc(120, p2[0][1], 8, 90, 270), f.line(120, p2[0][1] - 8, 120, p1[1][1])
    f.line(120, p1[1][1], *p1[1]), f.dot(120, p2[1][1], r=4)
    p3, o3 = f.gate("NAND", 400, 110, w=70, h=56)
    wire(f, o1, (350, 60), (350, p3[0][1]), p3[0]), wire(f, o2, (350, 160), (350, p3[1][1]), p3[1])
    f.line(*o3, 560, 110), f.text(586, 120, "Y", size=28)
    tables = {"P": (1, 1, 1, 1), "Q": (0, 1, 1, 1), "R": (1, 0, 1, 1), "S": (1, 1, 0, 1)}
    for (name, ys), (x, y) in zip(tables.items(), ((40, 230), (400, 230), (40, 440), (400, 440))):
        truth_table(f, x, y, [(a, b, v) for (a, b), v in zip(((0, 0), (0, 1), (1, 0), (1, 1)), ys)],
                    cw=70, rh=30, size=22, caption=f"({name})")
    return f


def or_nand_not_nor_y123():
    """Y1 = A OR B; Y2 = NOT (C NAND D); Y1 and Y2 feed a NOR gate giving Y3."""
    f = Figure(790, 340)
    p1, o1 = f.gate("OR", 150, 70, w=96, h=84)
    p2, o2 = f.gate("NAND", 150, 270, w=86, h=84)
    for (x, y), name in ((p1[0], "A"), (p1[1], "B"), (p2[0], "C"), (p2[1], "D")):
        f.line(60, y, x, y), f.text(40, y + 12, name, size=34)
    pn, on = f.gate("NOT", 300, 270, w=62, h=50)
    f.line(*o2, *pn[0])
    p3, o3 = f.gate("NOR", 520, 170, w=96, h=84)
    wire(f, o1, (440, 70), (440, p3[0][1]), p3[0]), wire(f, on, (440, 270), (440, p3[1][1]), p3[1])
    f.line(*o3, 700, 170)
    f.text(420, 50, "Y<sub>1</sub>", size=32), f.text(350, 326, "Y<sub>2</sub>", size=32), f.text(712, 160, "Y<sub>3</sub>", size=32, anchor="start")
    return f


def diode_40_60_ab():
    """A to B through two branches: 40 ohm then diode D (pointing right) on top, 60 ohm below."""
    f = Figure(760, 330)
    top, mid, bottom, l, r = 70, 180, 290, 140, 620
    f.dot(20, mid, r=7), f.line(20, mid, l, mid), f.line(l, top, l, bottom), f.dot(740, mid, r=7), f.line(r, mid, 740, mid)
    f.line(r, top, r, bottom)
    f.line(l, top, 190, top), f.resistor(190, 300, top, peaks=5, height=16), f.line(300, top, 460, top)
    f.diode(482, top, "right", size=20), f.line(502, top, r, top)
    f.line(l, bottom, 340, bottom), f.resistor(340, 460, bottom, peaks=5, height=16), f.line(460, bottom, r, bottom)
    f.text(245, 38, "40 Ω", size=30), f.text(482, 126, "D", size=30), f.text(400, 256, "60 Ω", size=30)
    f.text(20, 160, "A", size=30), f.text(740, 222, "B", size=30)
    return f


def vdiode(f, x, y, pointing="up", size=22):
    """A diode on a vertical wire, centred at (x, y), pointing up or down."""
    with f.rotated(-90 if pointing == "up" else 90, x, y):
        f.diode(x, y, "right", size=size)


def hop(f, x, y, r=8):
    """A vertical wire at x hopping over a horizontal wire at y (draws the small arc only)."""
    f.arc(x, y, r, 90, 270)


def nor_not():
    """A NOR gate on A and B, then a NOT gate giving Y."""
    f = Figure(720, 150)
    p, o = f.gate("NOR", 160, 74, w=100, h=84)
    for (x, y), name in ((p[0], "A"), (p[1], "B")):
        f.dot(50, y, r=6), f.line(50, y, x, y), f.text(24, y + 12, name, size=32)
    pn, on = f.gate("NOT", 460, 74, w=80, h=64)
    f.line(*o, *pn[0]), f.line(*on, 660, 74), f.dot(660, 74, r=6), f.text(690, 86, "Y", size=32)
    return f


def not_a_nand_bc_or():
    """NOT A and (B NAND C) feed an OR gate giving Y."""
    f = Figure(720, 300)
    pn, on = f.gate("NOT", 200, 60, w=76, h=58)
    p2, o2 = f.gate("NAND", 230, 240, w=96, h=80)
    f.dot(90, 60, r=6), f.line(90, 60, *pn[0]), f.text(56, 72, "A", size=34)
    for (x, y), name in ((p2[0], "B"), (p2[1], "C")):
        f.dot(90, y, r=6), f.line(90, y, x, y), f.text(56, y + 12, name, size=34)
    p3, o3 = f.gate("OR", 500, 150, w=96, h=84)
    wire(f, on, (440, 60), (440, p3[0][1]), p3[0]), wire(f, o2, (440, 240), (440, p3[1][1]), p3[1])
    f.line(*o3, 660, 150), f.dot(660, 150, r=6), f.text(690, 162, "Y", size=34)
    return f


def not_not_nand():
    """NOT A and NOT B feed a NAND gate giving Y."""
    f = Figure(720, 280)
    pa, oa = f.gate("NOT", 200, 60, w=80, h=64)
    pb, ob = f.gate("NOT", 200, 220, w=80, h=64)
    f.line(80, 60, *pa[0]), f.text(56, 72, "A", size=34), f.line(80, 220, *pb[0]), f.text(56, 232, "B", size=34)
    p3, o3 = f.gate("NAND", 470, 140, w=96, h=84)
    wire(f, oa, (360, 60), (360, p3[0][1]), p3[0]), wire(f, ob, (360, 220), (360, p3[1][1]), p3[1])
    f.line(*o3, 680, 140), f.text(690, 116, "Y", size=34)
    return f


def three_diodes_parallel():
    """6 V cell with 100 ohm in one branch; D1 (pointing up) with 50 ohm, D2 (down) with 60 ohm, D3 (down) with 160 ohm in the others."""
    f = Figure(760, 330)
    top, bottom = 40, 300
    xs = (150, 330, 480, 620)
    f.line(xs[0], top, xs[-1], top), f.line(xs[0], bottom, xs[-1], bottom)
    f.line(xs[0], top, xs[0], 82), f.vcell(xs[0], 92, gap=20, long=34, short=18), f.line(xs[0], 102, xs[0], 170)
    f.vresistor(xs[0], 170, 260), f.line(xs[0], 260, xs[0], bottom)
    for x, pointing, ohms, name in ((xs[1], "up", "50", "1"), (xs[2], "down", "60", "2"), (xs[3], "down", "160", "3")):
        f.line(x, top, x, 92), vdiode(f, x, 114, pointing), f.line(x, 136, x, 170)
        f.vresistor(x, 170, 260), f.line(x, 260, x, bottom)
        f.text(x + 28, 90, f"D<sub>{name}</sub>", size=30, anchor="start")
        f.text(x + 28, 228, f"{ohms} Ω", size=30, anchor="start")
    f.text(104, 106, "6 V", size=30, anchor="end"), f.text(124, 228, "100 Ω", size=30, anchor="end")
    return f


def rho_t_options():
    """Resistivity against temperature, options A (rising, curving up), B (rising line), C (falling steeply, then flat), D (falling line)."""
    f = Figure(760, 560)
    for name, (ox, oy) in zip("ABCD", ((70, 220), (450, 220), (70, 500), (450, 500))):
        f.axes(ox, oy, 210, 180, xlabel="<i>T</i>", ylabel="<i>ρ</i>", origin="O", size=26)
        f.text(ox + 110, oy + 52, name, size=28)
        if name == "A":
            f.curve(lambda x, ox=ox, oy=oy: oy - 18 - 140 * ((x - ox - 20) / 160) ** 2.2, ox + 20, ox + 180)
        elif name == "B":
            f.line(ox + 30, oy - 30, ox + 170, oy - 150)
        elif name == "C":
            f.curve(lambda x, ox=ox, oy=oy: oy - 12 - 1400 / (x - ox + 2) ** 1.2 * 1.0, ox + 12, ox + 190)
        else:
            f.line(ox + 30, oy - 150, ox + 170, oy - 20)
    return f


def nand_ab_or_not_a_and_b():
    """(A NAND B) and ((NOT A) AND B) feed an OR gate giving Y."""
    f = Figure(760, 330)
    p1, o1 = f.gate("AND", 300, 80, w=86, h=74)
    ya, yb = p1[0][1], p1[1][1]
    pn, on = f.gate("NOT", 410, 80, w=50, h=38)
    f.dot(80, ya, r=7), f.text(46, ya + 10, "A", size=30), f.dot(80, yb, r=7), f.text(46, yb + 12, "B", size=30)
    f.line(80, ya, 300, ya), f.line(80, yb, 300, yb)
    f.line(*o1, *pn[0])
    pn2, on2 = f.gate("NOT", 210, 250, w=56, h=42)
    p2, o2 = f.gate("AND", 330, 270, w=86, h=74)
    f.line(180, ya, 180, yb - 8), hop(f, 180, yb), f.line(180, yb + 8, 180, 250), f.line(180, 250, *pn2[0])
    f.dot(180, ya, r=4), f.line(*on2, *p2[0])
    wire(f, (140, yb), (140, p2[1][1]), p2[1]), f.dot(140, yb, r=4)
    p3, o3 = f.gate("OR", 560, 170, w=96, h=84)
    wire(f, on, (520, 80), (520, p3[0][1]), p3[0]), wire(f, o2, (520, 270), (520, p3[1][1]), p3[1])
    f.line(*o3, 720, 170), f.text(740, 180, "Y", size=30)
    return f


def two_diodes_three_branches():
    """Top: 30 ohm and D2 (pointing left). Middle: D1 (pointing right) and 30 ohm. Bottom: 20 ohm and a 5 V cell (+ on the left)."""
    f = Figure(720, 400)
    l, r, top, mid, bottom = 60, 680, 50, 190, 320
    f.line(l, top, l, bottom), f.line(r, top, r, bottom)
    f.line(l, top, 160, top), f.resistor(160, 270, top, peaks=4, height=18), f.line(270, top, 500, top)
    f.diode(522, top, "left", size=22), f.line(544, top, r, top)
    f.line(l, mid, 160, mid), f.diode(182, mid, "right", size=22), f.line(204, mid, 450, mid)
    f.resistor(450, 560, mid, peaks=4, height=18), f.line(560, mid, r, mid)
    f.line(l, bottom, 180, bottom), f.resistor(180, 290, bottom, peaks=4, height=18), f.line(290, bottom, 541, bottom)
    f.cell(552, bottom, gap=18, long=30, short=16), f.line(561, bottom, r, bottom)
    f.text(215, 104, "30 Ω", size=32), f.text(560, 104, "D<sub>2</sub>", size=32)
    f.text(220, 154, "D<sub>1</sub>", size=32), f.text(505, 244, "30 Ω", size=32)
    f.text(235, 374, "20 Ω", size=32), f.text(524, 364, "+", size=28), f.text(580, 364, "−", size=28)
    f.text(552, 392, "5 V", size=30)
    return f


def zener_iv_regions():
    """Zener I-V curve: forward branch c-b-a rising steeply at the top right; reverse branch c-d-e falling at the bottom left."""
    f = Figure(760, 470)
    ox, oy = 360, 230
    f.line(150, oy, 590, oy, arrow=True), f.line(ox, oy, 150, oy, arrow=True)
    f.line(ox, oy, ox, 20, arrow=True), f.line(ox, oy, ox, 450, arrow=True)
    f.curve(lambda x: oy - 6 - 200 * ((x - ox) / 180) ** 3.2, ox, ox + 172)
    f.curve(lambda x: oy + 6 + 200 * ((ox - x) / 170) ** 3.2, ox - 162, ox)
    f.text(408, 50, "<i>I</i> (mA)", size=28), f.text(538, 40, "a", size=28), f.text(440, 186, "b", size=28)
    f.text(338, 268, "c", size=28), f.text(214, 278, "d", size=28), f.text(170, 420, "e", size=28)
    f.text(640, 120, "Forward", size=30), f.text(660, 156, "bias", size=30)
    f.text(70, 290, "Reverse", size=30), f.text(84, 326, "bias", size=30)
    f.line(200, 180, 130, 180, arrow=True), f.text(212, 190, "<i>V</i> (volt)", size=28, anchor="start")
    f.line(420, 300, 490, 300, arrow=True), f.text(500, 310, "<i>V</i> (volt)", size=28, anchor="start")
    f.text(470, 420, "<i>I</i> (mA)", size=28)
    return f


def a_and_nor_bc():
    """A and (B NOR C) feed an AND gate giving Y."""
    f = Figure(720, 220)
    p1, o1 = f.gate("NOR", 160, 150, w=90, h=80)
    p2, o2 = f.gate("AND", 480, 110, w=100, h=86)
    f.dot(80, 40, r=7), f.text(46, 52, "A", size=32), wire(f, (80, 40), (400, 40), (400, p2[0][1]), p2[0])
    for (x, y), name in ((p1[0], "B"), (p1[1], "C")):
        f.dot(80, y, r=7), f.line(80, y, x, y), f.text(46, y + 12, name, size=32)
    wire(f, o1, (440, 150), (440, p2[1][1]), p2[1])
    f.line(*o2, 670, 110), f.dot(670, 110, r=7), f.text(698, 122, "Y", size=32)
    return f


def iv_options_led():
    """Four I-V graphs: (a) through the origin, steep both ways; (b) rising steeply in the first quadrant; (c) a dip below the V axis in the fourth quadrant; (d) rising quickly then levelling."""
    f = Figure(760, 560)
    # (a)
    ox, oy = 200, 140
    f.line(80, oy, 330, oy, arrow=True), f.line(ox, 250, ox, 20, arrow=True)
    f.curve(lambda x: oy - 100 * ((x - ox) / 70) ** 3 if x > ox else oy + 100 * ((ox - x) / 70) ** 3, ox - 62, ox + 62)
    f.text(30, 40, "(a)", size=28), f.text(222, 40, "<i>I</i>", size=26), f.text(320, 176, "<i>V</i>", size=26), f.text(214, 168, "0", size=24)
    # (b)
    ox, oy = 460, 230
    f.axes(ox, oy, 250, 200, xlabel="<i>V</i>", ylabel="<i>I</i>", origin="0", size=26)
    f.curve(lambda x: oy - 4 - 190 * ((x - ox) / 200) ** 4, ox, ox + 200)
    f.text(390, 40, "(b)", size=28)
    # (c)
    ox, oy = 200, 420
    f.line(80, oy, 330, oy, arrow=True), f.line(ox, 540, ox, 300, arrow=True)
    f.add(f'<path d="M{ox},{oy + 70} Q{ox + 90},{oy + 80} {ox + 96},{oy}" stroke-width="3"/>')
    f.text(30, 320, "(c)", size=28), f.text(184, 312, "<i>I</i>", size=26), f.text(322, 456, "<i>V</i>", size=26), f.text(184, 446, "0", size=24)
    # (d)
    ox, oy = 460, 520
    f.axes(ox, oy, 250, 200, xlabel="<i>V</i>", ylabel="<i>I</i>", origin="0", size=26)
    f.curve(lambda x: oy - 40 - 30 * ((x - ox) / 200) - 30 * (1 - 2.718 ** (-(x - ox) / 6)), ox + 2, ox + 210)
    f.text(390, 320, "(d)", size=28)
    return f


def photodiode_iv_intensities():
    """Photodiode reverse-bias curves I1 (smallest current) to I4 (largest) below the voltage axis; current axis in uA pointing down."""
    f = Figure(700, 440)
    ox, oy = 380, 100
    f.line(40, oy, 660, oy, arrow=True), f.line(ox, 20, ox, 420, arrow=True)
    f.text(60, 80, "Reverse bias", size=30, anchor="start"), f.text(400, 80, "Forward bias", size=30, anchor="start")
    f.text(392, 418, "μA", size=30, anchor="start")
    for i, level in enumerate((150, 190, 240, 290)):
        f.add(f'<path d="M{ox},{oy} Q{ox - 10},{level} {ox - 80},{level} L110,{level}" stroke-width="3"/>')
        f.text(90, level + 10, f"<i>I</i><sub>{i + 1}</sub>", size=28, anchor="end")
    return f


def nor_ab_and_c():
    """(A NOR B) and C feed an AND gate giving Y."""
    f = Figure(720, 220)
    p1, o1 = f.gate("NOR", 160, 60, w=96, h=80)
    p2, o2 = f.gate("AND", 470, 120, w=100, h=86)
    for (x, y), name in ((p1[0], "A"), (p1[1], "B")):
        f.dot(60, y, r=7), f.line(60, y, x, y), f.text(32, y + 12, name, size=32)
    wire(f, o1, (410, 60), (410, p2[0][1]), p2[0])
    f.dot(60, 180, r=7), wire(f, (60, 180), (430, 180), (430, p2[1][1]), p2[1]), f.text(32, 192, "C", size=32)
    f.line(*o2, 670, 120), f.dot(670, 120, r=7), f.text(698, 132, "Y", size=32)
    return f


def a_and_or_bc():
    """A and (B OR C) feed an AND gate giving Y."""
    f = Figure(720, 260)
    p1, o1 = f.gate("OR", 180, 170, w=110, h=96)
    p2, o2 = f.gate("AND", 450, 80, w=100, h=86)
    f.dot(80, p2[0][1], r=7), f.text(46, p2[0][1] + 12, "A", size=32), f.line(80, p2[0][1], *p2[0])
    for (x, y), name in ((p1[0], "B"), (p1[1], "C")):
        f.dot(80, y, r=7), f.line(80, y, x, y), f.text(46, y + 12, name, size=32)
    wire(f, o1, (400, 170), (400, p2[1][1]), p2[1])
    f.line(*o2, 650, 80), f.dot(650, 80, r=7), f.text(680, 92, "Y", size=32)
    return f


def four_biased_diodes():
    """Diode D then resistor R, with end potentials (A) 0 V and -4 V, (B) -4 V and -3 V, (C) -2 V and +2 V, (D) 3 V and 5 V."""
    f = Figure(760, 330)
    ends = {"A": ("0 V", "−4 V"), "B": ("−4 V", "−3 V"), "C": ("−2 V", "+2 V"), "D": ("3 V", "5 V")}
    for (name, (v1, v2)), (ox, oy) in zip(ends.items(), ((20, 70), (400, 70), (20, 230), (400, 230))):
        f.line(ox, oy, ox + 90, oy), f.diode(ox + 108, oy, "right", size=18), f.line(ox + 126, oy, ox + 150, oy)
        f.resistor(ox + 150, ox + 260, oy, peaks=6, height=10), f.line(ox + 260, oy, ox + 330, oy)
        f.text(ox + 4, oy - 22, v1, size=26, anchor="start"), f.text(ox + 330, oy - 22, v2, size=26, anchor="end")
        f.text(ox + 108, oy - 26, "D", size=26), f.text(ox + 205, oy - 26, "R", size=26)
        f.text(ox + 160, oy + 54, f"({name})", size=26)
    return f


FIGURES = {
    "PYQ-PHY-7879789defe0": nor_not,
    "PYQ-PHY-f115cf9b3ca7": not_a_nand_bc_or,
    "PYQ-PHY-862470339b35": not_not_nand,
    "PYQ-PHY-99a278a42453": three_diodes_parallel,
    "PYQ-PHY-d03979e7fa93": rho_t_options,
    "PYQ-PHY-5f276c6ddd1c": nand_ab_or_not_a_and_b,
    "PYQ-PHY-61f712a758dd": two_diodes_three_branches,
    "PYQ-PHY-a97747837d80": zener_iv_regions,
    "PYQ-PHY-c829d981ec94": a_and_nor_bc,
    "PYQ-PHY-43a0e85791b1": iv_options_led,
    "PYQ-PHY-4b730aab90d6": photodiode_iv_intensities,
    "PYQ-PHY-891dfe0586c6": nor_ab_and_c,
    "PYQ-PHY-6ce51fb72afe": a_and_or_bc,
    "PYQ-PHY-71df20bba0e4": four_biased_diodes,
    "PYQ-PHY-1195ff61af65": npn_as_two_diodes,
    "PYQ-PHY-390222f47cfc": two_cells_diode_3ohm,
    "PYQ-PHY-03678937d2d8": nand_combinations_i_ii,
    "PYQ-PHY-a3995f7f8993": zener_15v_with_1k_load,
    "PYQ-PHY-ae346dda8389": zener_24v_rs_rl,
    "PYQ-PHY-df1dd64bc1ea": nor_and_nand_tables,
    "PYQ-PHY-5fb89b6b42da": or_nand_not_nor_y123,
    "PYQ-PHY-e1c5993bc4c3": diode_40_60_ab,
    "PYQ-PHY-ec171a51ce6a": four_nand_xor,
    "PYQ-PHY-1dabac0d4e77": diode_3v_to_1v,
    "PYQ-PHY-80a4ea47d0bc": not_nand_tables,
    "PYQ-PHY-c063b83ed274": diode_reverse_minus2_minus5,
    "PYQ-PHY-a516a86e0bea": gate_g_then_or_table,
    "PYQ-PHY-b4ea6669f46b": not_a_or_b_and_c,
    "PYQ-PHY-165c623f374d": nand_nor_tied_not,
    "PYQ-PHY-9e3aadc0270e": xor_from_and_or_not,
    "PYQ-PHY-b580a06ff0ea": two_diodes_branches,
    "PYQ-PHY-b9579030c795": and_then_nand_with_c,
    "PYQ-PHY-4581a9fcd5ff": nand_or_and,
    "PYQ-PHY-bfa3824e11da": zener_with_series_r,
}
