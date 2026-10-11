"""Physics: semiconductors (part 2), thermodynamics (part 1)."""

import math

from drawings.physics_08 import wire
from figlib import Figure, mid_arrow


def nor_nand_not_chain():
    """A NOR gate, then a NAND gate with its inputs joined, then a NOT gate."""
    f = Figure(680, 230)
    p1, o1 = f.gate("NOR", 110, 122, w=82, h=78)
    f.line(40, p1[0][1], *p1[0]), f.line(40, p1[1][1], *p1[1])
    p2, o2 = f.gate("NAND", 300, 122, w=84, h=78)
    wire(f, o1, (266, 122)), wire(f, p2[0], (266, p2[0][1]), (266, p2[1][1]), p2[1])
    pn, on = f.gate("NOT", 470, 122, w=74, h=66)
    f.line(*o2, *pn[0]), f.line(*on, 600, 122)
    f.text(20, p1[0][1] + 10, "A", size=28), f.text(20, p1[1][1] + 10, "B", size=28), f.text(622, 132, "Y", size=28)
    f.text(152, 62, "NOR", size=26), f.text(346, 62, "NAND", size=26), f.text(504, 62, "NOT", size=26)
    return f


def not_not_nor_not():
    """A and B are each inverted (G1, G2), fed to a NOR gate G3, whose output is inverted by G4."""
    f = Figure(680, 310)
    for y, name, tag in ((78, "A", "1"), (242, "B", "2")):
        pn, on = f.gate("NOT", 142, y, w=92, h=80)
        f.line(54, y, *pn[0]), f.text(32, y + 10, name, size=30)
        f.text(166, y + 10, f"G<sub>{tag}</sub>", size=26)
        if tag == "1":
            top_out = on
        else:
            bottom_out = on
    p3, o3 = f.gate("NOR", 348, 160, w=84, h=80)
    wire(f, top_out, (316, 78), (316, p3[0][1]), p3[0]), wire(f, bottom_out, (316, 242), (316, p3[1][1]), p3[1])
    f.text(394, 170, "G<sub>3</sub>", size=26)
    p4, o4 = f.gate("NOT", 492, 160, w=92, h=80)
    f.line(*o3, *p4[0]), f.text(516, 170, "G<sub>4</sub>", size=26), f.line(*o4, 628, 160)
    f.text(606, 140, "Y", size=30)
    return f


def nor_nand_and():
    """The NOR of A and B and the NAND of B and A feed an AND gate giving Y."""
    f = Figure(680, 340)
    p1, o1 = f.gate("NOR", 168, 96, w=84, h=86)
    p2, o2 = f.gate("NAND", 186, 252, w=78, h=80)
    f.line(84, p1[0][1], *p1[0]), f.line(84, p2[1][1], *p2[1])
    wire(f, (84, 176), (124, 176), (124, p1[1][1]), p1[1]), wire(f, (124, 176), (124, p2[0][1]), p2[0])
    f.dot(124, 176, r=4)
    p3, o3 = f.gate("AND", 414, 174, w=80, h=80)
    wire(f, o1, (346, 96), (346, p3[0][1]), p3[0]), wire(f, o2, (346, 252), (346, p3[1][1]), p3[1])
    f.line(*o3, 568, 174), f.terminal(574, 174)
    for y, name in ((p1[0][1], "A"), (176, "B"), (p2[1][1], "A")):
        f.terminal(78, y), f.text(46, y + 10, f"<i>{name}</i>", size=30)
    f.text(606, 184, "<i>Y</i>", size=30)
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
    f.text(50, 84, "A", size=34), f.text(50, p2[0][1] + 12, "B", size=34), f.text(50, p2[1][1] + 12, "C", size=34)
    f.text(616, 172, "Y", size=34)
    return f


def a_and_b_or_not_c():
    """(A AND B) and NOT C feed an OR gate giving Y."""
    f = Figure(680, 350)
    p1, o1 = f.gate("AND", 176, 84, w=118, h=100)
    pn, on = f.gate("NOT", 176, 268, w=100, h=86)
    f.line(70, p1[0][1], *p1[0]), f.line(70, p1[1][1], *p1[1]), f.line(70, 268, *pn[0])
    p3, o3 = f.gate("OR", 424, 110, w=112, h=96)
    wire(f, o1, (352, 84), (352, p3[0][1]), p3[0])
    wire(f, on, (352, 268), (352, p3[1][1]), p3[1]), f.line(*o3, 594, 110)
    for y, name in ((p1[0][1], "A"), (p1[1][1], "B"), (268, "C")):
        f.dot(70, y, r=6), f.text(38, y + 12, name, size=34)
    f.dot(594, 110, r=6), f.text(624, 122, "Y", size=34)
    return f


def four_gates_with_inputs():
    """Four gates with their inputs: (A) NAND with 1, 1; (B) NAND with 1, 0; (C) NOR with 0, 1; (D) XOR with 0, 0."""
    f = Figure(1000, 190)
    spec = (("A", "NAND", 92, "1", "1"), ("B", "NAND", 352, "1", "0"), ("C", "NOR", 590, "0", "1"), ("D", "XOR", 862, "0", "0"))
    for name, kind, x, a, b in spec:
        pins, out = f.gate(kind, x, 78, w=70, h=74)
        for (px, py), value in zip(pins, (a, b)):
            f.line(x - 54, py, px, py), f.text(x - 70, py + 9, value, size=26)
        f.line(*out, out[0] + 26, 78), f.text(x + 42, 170, f"({name})", size=26)
    return f


def nor_then_not():
    """A NOR gate (output C) followed by a NOT gate giving Y."""
    f = Figure(680, 190)
    p1, o1 = f.gate("NOR", 196, 92, w=104, h=112)
    f.dot(56, p1[0][1], r=6), f.dot(56, p1[1][1], r=6)
    f.line(56, p1[0][1], *p1[0]), f.line(56, p1[1][1], *p1[1])
    pn, on = f.gate("NOT", 414, 92, w=100, h=88)
    f.line(*o1, *pn[0]), f.line(*on, 592, 92), f.dot(592, 92, r=6)
    f.text(28, p1[0][1] + 12, "A", size=34), f.text(28, p1[1][1] + 12, "B", size=34)
    f.text(316, 62, "C", size=34), f.text(622, 104, "Y", size=34)
    return f


def band_diagrams():
    """Band diagrams (1), (2) and (3): conduction band C, valence band V and the Fermi level EF (dashed)."""
    f = Figure(1000, 300)
    fermi = {1: 146, 2: 178, 3: 114}
    for n, x in ((1, 90), (2, 406), (3, 736)):
        f.line(x, 84, x + 200, 84), f.line(x, 208, x + 200, 208)
        f.line(x, fermi[n], x + 200, fermi[n], width=2, dash="9 7")
        f.text(x - 30, 92, "C", size=26), f.text(x - 30, 218, "V", size=26)
        f.text(x - 36, fermi[n] + 9, "<i>E</i><sub>F</sub>", size=24)
        f.text(x + 100, 270, f"({n})", size=28)
    return f


def diode_bias_figures():
    """Fig. 1: diode D1 and R1 between -5 V (anode side) and -3 V. Fig. 2: diode D2 and R2 between 0 V (anode side) and -4 V."""
    f = Figure(470, 470)
    for y, n, a, b in ((128, 1, "−5 V", "−3 V"), (360, 2, "0 V", "−4 V")):
        f.line(56, y, 106, y), f.diode(136, y, "right", size=30), f.line(166, y, 236, y)
        f.resistor(236, 322, y, peaks=3, height=18), f.line(322, y, 392, y)
        f.terminal(50, y), f.terminal(398, y)
        f.text(50, y + 46, a, size=26), f.text(420, y + 44, b, size=26)
        f.text(132, y - 48, f"D<sub>{n}</sub>", size=26), f.text(280, y - 34, f"R<sub>{n}</sub>", size=26)
        f.text(236, y + 78, f"Fig. {n}", size=28)
    return f


def rod(f, x, y, length, r=17):
    """A cylinder lying on its side."""
    f.add(f'<path d="M{x},{y - r} H{x + length} A7,{r} 0 0 1 {x + length},{y + r} H{x}" stroke-width="3"/>')
    f.add(f'<ellipse cx="{x}" cy="{y}" rx="7" ry="{r}" stroke-width="3" fill="#fff"/>')


def rods_parallel_and_series():
    """Two identical rods joined side by side (fig 1) and end to end (fig 2)."""
    f = Figure(1000, 260)
    rod(f, 52, 46, 270), rod(f, 52, 82, 270)
    rod(f, 428, 64, 268), rod(f, 696, 64, 268)
    f.text(176, 180, "(fig 1)", size=30), f.text(680, 180, "(fig 2)", size=30)
    return f


def cyclic_process_abc():
    """P-V diagram: A (400 K) to B (800 K) at constant volume, B to C (600 K) adiabatic, C back to A at constant pressure."""
    f = Figure(660, 480)
    ox, oy = 86, 432
    f.vector(ox, oy, ox, 52), f.vector(ox, oy, 596, oy)
    a, b, c = (176, 320), (176, 122), (470, 320)
    f.line(*a, *b), f.line(*a, *c)
    f.polyline([(176 + 294 * t, 320 - 198 * ((1 - t) ** 2.6)) for t in [i / 60 for i in range(61)]])
    for pt in (a, b, c):
        f.dot(*pt, r=6)
    f.text(86, 38, "P", size=28), f.text(616, 442, "V", size=28), f.text(62, 442, "0", size=28)
    f.text(226, 108, "B (800 K)", size=26), f.text(184, 362, "A (400 K)", size=26), f.text(486, 362, "C (600 K)", size=26)
    return f


def rectangular_cycle():
    """P-V diagram of the cycle A (3V0, 2P0), B (5V0, 2P0), C (5V0, 4P0), D (3V0, 4P0), traversed A-B-C-D-A."""
    f = Figure(660, 480)
    ox, oy = 96, 428
    f.vector(ox, oy, ox, 34), f.vector(ox, oy, 616, oy)
    x3, x5, y2, y4 = 318, 548, 296, 164
    for (x1, y1, x2, y2_) in ((ox, y4, x3, y4), (ox, y2, x3, y2), (x3, y2, x3, oy), (x5, y2, x5, oy)):
        f.line(x1, y1, x2, y2_, width=1.5, dash="12 5 3 5")
    mid_arrow(f, x3, y2, x5, y2, at=0.42, size=18), mid_arrow(f, x5, y2, x5, y4, at=0.42, size=18)
    mid_arrow(f, x5, y4, x3, y4, at=0.62, size=18), mid_arrow(f, x3, y4, x3, y2, at=0.42, size=18)
    f.text(70, 54, "<i>P</i>", size=34), f.text(634, 440, "<i>V</i>", size=34)
    f.text(82, y4 + 12, "4<i>P</i><sub>0</sub>", size=30, anchor="end"), f.text(82, y2 + 12, "2<i>P</i><sub>0</sub>", size=30, anchor="end")
    f.text(x3, 470, "3<i>V</i><sub>0</sub>", size=30), f.text(x5, 470, "5<i>V</i><sub>0</sub>", size=30)
    f.text(x3 - 22, y2 + 34, "<i>A</i>", size=30), f.text(x5 + 22, y2 + 12, "<i>B</i>", size=30)
    f.text(x5 + 20, y4 - 12, "<i>C</i>", size=30), f.text(x3, y4 - 16, "<i>D</i>", size=30)
    return f


FIGURES = {
    "PYQ-PHY-9664bf47af69": nor_nand_not_chain,
    "PYQ-PHY-b47f085dae46": not_not_nor_not,
    "PYQ-PHY-b487d3996611": nor_nand_and,
    "PYQ-PHY-ba4d50dd7be1": not_a_or_b_and_c,
    "PYQ-PHY-c02b14187798": a_and_b_or_not_c,
    "PYQ-PHY-cb7346d5faed": four_gates_with_inputs,
    "PYQ-PHY-dd33546acda1": nor_then_not,
    "PYQ-PHY-f8c8505e3af4": band_diagrams,
    "PYQ-PHY-fddcaeea5c07": diode_bias_figures,
    "PYQ-PHY-1f124098d639": rods_parallel_and_series,
    "PYQ-PHY-21271bbdb27d": cyclic_process_abc,
    "PYQ-PHY-4a7c2fe7af0a": rectangular_cycle,
}
