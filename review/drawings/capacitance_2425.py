"""Physics (MHT-CET 2024-25): capacitance."""

import math

from figlib import Figure


def wire(f, *points):
    f.polyline(list(points))


def slant_capacitor(f, p1, p2, gap=14, height=26, at=0.5):
    """A wire from p1 to p2 in any direction with a capacitor on it."""
    (x1, y1), (x2, y2) = p1, p2
    total = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / total, (y2 - y1) / total
    mx, my = x1 + (x2 - x1) * at, y1 + (y2 - y1) * at
    f.line(x1, y1, mx - ux * gap / 2, my - uy * gap / 2), f.line(mx + ux * gap / 2, my + uy * gap / 2, x2, y2)
    with f.rotated(round(math.degrees(math.atan2(uy, ux)), 2), round(mx, 1), round(my, 1)):
        f.capacitor(mx, my, gap=gap, height=height)
    return mx, my


def hatch_rect(f, x, y, w, h, kind="diagonal", spacing=12):
    """A rectangle filled with diagonal or horizontal or vertical lines (a dielectric)."""
    f.rect(x, y, w, h, width=2)
    f.add(f'<clipPath id="c{x}_{y}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>')
    lines = []
    if kind == "horizontal":
        lines = [(x, y + i, x + w, y + i) for i in range(spacing, int(h), spacing)]
    elif kind == "vertical":
        lines = [(x + i, y, x + i, y + h) for i in range(spacing, int(w), spacing)]
    else:
        lines = [(x + i, y + h, x + i + h, y) for i in range(-int(h), int(w), spacing)]
    body = "".join(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" stroke-width="1.5"/>' for a, b, c, d in lines)
    f.add(f'<g clip-path="url(#c{x}_{y})">{body}</g>')


def tag(f, x, y, content, size=32, w=None):
    """A label on a white patch, for text that sits on hatching (y is the text baseline)."""
    w = w or size * 3.2
    f.add(f'<rect x="{x - w / 2:.1f}" y="{y - size * 0.95:.1f}" width="{w:.1f}" height="{size * 1.3:.1f}" fill="#fff" stroke="none"/>')
    f.text(x, y, content, size=size)


def loop_two_cells_two_caps():
    """A loop: 20 V cell on the top wire, 4 V cell on the bottom wire, 3 uF on the left side and 5 uF on the right side."""
    f = Figure(640, 370)
    l, r, top, bottom = 120, 520, 50, 290
    f.line(l, top, 309, top), f.cell(320, top, gap=20, long=26, short=14), f.line(331, top, r, top)
    f.line(l, bottom, 309, bottom), f.cell(320, bottom, gap=20, long=26, short=14), f.line(331, bottom, r, bottom)
    for x in (l, r):
        f.line(x, top, x, 163), f.vcapacitor(x, 170, gap=14, half=26), f.line(x, 177, x, bottom)
    f.text(320, 110, "20 V", size=30), f.text(320, 352, "4 V", size=30)
    f.text(84, 180, "3 μF", size=30, anchor="end"), f.text(556, 180, "5 μF", size=30, anchor="start")
    return f


def two_dielectrics_side_by_side():
    """Parallel plates d apart, the gap filled with K1 (left half) and K2 (right half) side by side, with terminals."""
    f = Figure(640, 400)
    l, r, t, b = 160, 480, 70, 370
    hatch_rect(f, l, t, 160, b - t, "diagonal"), hatch_rect(f, 320, t, 160, b - t, "horizontal")
    f.line(l, t, l, b, width=5), f.line(r, t, r, b, width=5)
    f.line(30, 220, l, 220), f.terminal(24, 220), f.line(r, 220, 610, 220), f.terminal(616, 220)
    f.dim(l, 34, r, 34), tag(f, 320, 30, "<i>d</i>", size=30)
    tag(f, 240, 232, "<i>K</i><sub>1</sub>", size=32), tag(f, 400, 232, "<i>K</i><sub>2</sub>", size=32)
    return f


def vq_graph_a_b():
    """Voltage against charge for capacitors A and B: straight lines from the origin, B steeper; at the same charge Q, VB is above VA."""
    f = Figure(560, 440)
    ox, oy = 80, 380
    f.axes(ox, oy, 420, 340, xlabel="<i>Q</i>", ylabel="<i>V</i>", origin="0", size=32)
    f.line(ox, oy, 330, 90), f.line(ox, oy, 420, 150)
    qx = 230
    yb, ya = oy - (qx - ox) * (290 / 250), oy - (qx - ox) * (230 / 340)
    f.line(ox, yb, qx, yb, width=2, dash="8 6"), f.line(ox, ya, qx, ya, width=2, dash="8 6")
    f.line(qx, yb, qx, oy, width=2, dash="8 6"), f.dot(qx, yb, r=6), f.dot(qx, ya, r=6)
    f.text(346, 86, "B", size=32), f.text(436, 150, "A", size=32), f.text(qx, oy + 34, "<i>Q</i>", size=30)
    f.text(64, yb + 10, "<i>V</i><sub>B</sub>", size=30, anchor="end"), f.text(64, ya + 10, "<i>V</i><sub>A</sub>", size=30, anchor="end")
    return f


def resistor_ladder_with_capacitor():
    """A 6 V cell (current I) on the top wire; 1, 2 and 3 ohm between the two side wires; 0.5 uF and 4 ohm on the bottom wire."""
    f = Figure(600, 520)
    l, r = 40, 560
    rows = (60, 160, 260, 360, 460)
    f.line(l, rows[0], l, rows[-1]), f.line(r, rows[0], r, rows[-1])
    f.line(l, rows[0], 140, rows[0]), f.cell(151, rows[0], gap=20, long=24, short=14), f.line(162, rows[0], r, rows[0])
    f.arrowhead(420, rows[0], 0, size=16)
    for y, ohms in zip(rows[1:4], ("1 Ω", "2 Ω", "3 Ω")):
        f.line(l, y, 240, y), f.resistor(240, 340, y, peaks=4, height=14), f.line(340, y, r, y)
        f.text(380, y - 18, ohms, size=28)
    y = rows[4]
    f.line(l, y, 143, y), f.capacitor(150, y, gap=14, height=22), f.line(157, y, 360, y)
    f.resistor(360, 460, y, peaks=4, height=14), f.line(460, y, r, y)
    f.text(151, 30, "6 V", size=28), f.text(440, 42, "<i>I</i>", size=28), f.text(150, 510, "0.5 μF", size=28), f.text(470, y - 22, "4 Ω", size=28)
    return f


def dielectrics_layered():
    """Parallel plates (left and right) d apart; the upper half of the gap holds K1 = 4, the lower half K2 = 2; terminals on both plates."""
    f = Figure(640, 440)
    l, r, t, m, b = 180, 460, 30, 190, 350
    hatch_rect(f, l, t, r - l, m - t, "horizontal"), hatch_rect(f, l, m, r - l, b - m, "diagonal")
    f.line(l, t, l, b, width=5), f.line(r, t, r, b, width=5)
    f.line(30, m, l, m), f.terminal(24, m), f.line(r, m, 610, m), f.terminal(616, m)
    f.dim(l, 400, r, 400), f.text(320, 430, "<i>d</i>", size=30)
    tag(f, 320, 122, "<i>K</i><sub>1</sub> = 4", size=34), tag(f, 320, 284, "<i>K</i><sub>2</sub> = 2", size=34)
    return f


def three_dielectrics_ab():
    """Plates A (top) and B (bottom) d apart: the left half (area A/2) holds K1 = 4; the right half holds K2 = 3 (upper d/2) over K3 = 6 (lower d/2)."""
    f = Figure(640, 460)
    l, m, r, t, h, b = 40, 320, 560, 80, 220, 360
    hatch_rect(f, l, t, m - l, b - t, "vertical", spacing=10)
    hatch_rect(f, m, t, r - m, h - t, "horizontal", spacing=10), hatch_rect(f, m, h, r - m, b - h, "diagonal")
    f.line(l, t, r, t, width=5), f.line(l, b, r, b, width=5)
    f.line(m, t, m, 30), f.terminal(m, 24), f.line(m, b, m, 410), f.terminal(m, 416)
    f.text(m + 20, 32, "A", size=30, anchor="start"), f.text(m + 20, 440, "B", size=30, anchor="start")
    tag(f, 180, 232, "<i>K</i><sub>1</sub> = 4", size=34)
    tag(f, 440, 162, "<i>K</i><sub>2</sub> = 3", size=32), tag(f, 440, 302, "<i>K</i><sub>3</sub> = 6", size=32)
    f.dim(l, 396, m - 10, 396), f.dim(m + 10, 396, r, 396)
    f.text(180, 430, "<i>A</i>/2", size=28), f.text(440, 430, "<i>A</i>/2", size=28)
    f.dim(596, t, 596, h - 4), f.dim(596, h + 4, 596, b)
    f.text(606, 160, "<i>d</i>/2", size=26, anchor="start"), f.text(606, 300, "<i>d</i>/2", size=26, anchor="start")
    return f


def five_capacitors_ab():
    """Between A and B: three capacitors C in parallel on an upper branch, and two capacitors C in series on a lower branch."""
    f = Figure(640, 440)
    l, r, mid = 120, 520, 220
    f.terminal(40, mid), f.line(46, mid, l, mid), f.line(r, mid, 594, mid), f.terminal(600, mid)
    f.line(l, 110, l, 330), f.line(r, 110, r, 330)
    f.line(l, 110, 200, 110), f.line(400, 110, r, 110)
    f.line(200, 50, 200, 170), f.line(400, 50, 400, 170)
    for y in (50, 110, 170):
        f.line(200, y, 293, y), f.capacitor(300, y, gap=14, height=22), f.line(307, y, 400, y)
        f.text(330, y - 18, "<i>C</i>", size=28, anchor="start")
    f.line(l, 330, 233, 330), f.capacitor(240, 330, gap=14, height=22), f.line(247, 330, 393, 330)
    f.capacitor(400, 330, gap=14, height=22), f.line(407, 330, r, 330)
    f.text(240, 380, "<i>C</i>", size=28), f.text(400, 380, "<i>C</i>", size=28)
    f.text(30, 200, "A", size=30), f.text(612, 200, "B", size=30)
    return f


def half_filled_with_k():
    """Parallel plates (top and bottom) with leads from their centres; the middle half of the gap holds a slab of dielectric constant K, air on both sides."""
    f = Figure(640, 360)
    t, b = 110, 250
    f.line(20, t, 620, t, width=4), f.line(20, b, 620, b, width=4)
    hatch_rect(f, 170, t, 300, b - t, "diagonal", spacing=16)
    f.line(320, 20, 320, t), f.line(320, b, 320, 340)
    tag(f, 320, 192, "<i>K</i>", size=36), f.text(90, 192, "air", size=34), f.text(550, 192, "air", size=34)
    return f


def triangle_three_capacitors():
    """A triangle: C1 = 1C on the left side, C2 = 2C on the right side, C3 = 3C on the base; a cell joins the two base corners underneath."""
    f = Figure(640, 480)
    top, bl, br = (320, 40), (110, 330), (530, 330)
    slant_capacitor(f, top, bl), slant_capacitor(f, top, br)
    f.line(*bl, 313, 330), f.capacitor(320, 330, gap=14, height=26), f.line(327, 330, *br)
    wire(f, bl, (110, 430), (309, 430)), f.cell(320, 430, gap=22, long=28, short=16), wire(f, (331, 430), (530, 430), br)
    f.text(130, 170, "<i>C</i><sub>1</sub> = 1<i>C</i>", size=32), f.text(520, 170, "<i>C</i><sub>2</sub> = 2<i>C</i>", size=32)
    f.text(320, 390, "<i>C</i><sub>3</sub> = 3<i>C</i>", size=32)
    return f


def pentagon_capacitors():
    """A pentagon P (top), T, S, R, Q with a capacitor C on each of its five sides."""
    f = Figure(560, 500)
    cx, cy, r = 280, 260, 190
    names = ("P", "T", "S", "R", "Q")
    pts = [(cx + r * math.cos(math.radians(-90 + 72 * i)), cy + r * math.sin(math.radians(-90 + 72 * i))) for i in range(5)]
    for i in range(5):
        mx, my = slant_capacitor(f, pts[i], pts[(i + 1) % 5])
        ox, oy = (mx - cx) * 0.28, (my - cy) * 0.28
        f.text(mx + ox, my + oy + 10, "<i>C</i>", size=30)
    for (x, y), name in zip(pts, names):
        ox, oy = (x - cx) * 0.14, (y - cy) * 0.14
        f.text(x + ox, y + oy + 10, name, size=30)
    return f


def series_parallel_9v():
    """4 uF in series with (2 uF in parallel with 4 uF), across a 9 V cell."""
    f = Figure(640, 440)
    l, r, top, bottom = 30, 600, 140, 380
    f.line(l, top, 133, top), f.capacitor(140, top, gap=14, height=24), f.line(147, top, 260, top)
    f.line(260, 60, 260, 220), f.line(470, 60, 470, top), f.line(470, top, r, top), f.line(470, top, 470, 220)
    for y in (60, 220):
        f.line(260, y, 358, y), f.capacitor(365, y, gap=14, height=24), f.line(372, y, 470, y)
    f.line(l, top, l, bottom), f.line(r, top, r, bottom)
    f.line(l, bottom, 179, bottom), f.cell(190, bottom, gap=20, long=24, short=14), f.line(201, bottom, r, bottom)
    f.text(140, 200, "4 μF", size=30), f.text(365, 32, "2 μF", size=30), f.text(365, 280, "4 μF", size=30), f.text(190, 428, "9 V", size=30)
    return f


FIGURES = {
    "PYQ-PHY-d71a5e4f2ac7": loop_two_cells_two_caps,
    "PYQ-PHY-8cff163d45b4": two_dielectrics_side_by_side,
    "PYQ-PHY-a964c29c4fc2": vq_graph_a_b,
    "PYQ-PHY-de1cf0e7c04a": resistor_ladder_with_capacitor,
    "PYQ-PHY-cf1dba57e8b9": dielectrics_layered,
    "PYQ-PHY-f4d5937d885b": three_dielectrics_ab,
    "PYQ-PHY-a2627ddbf3f5": vq_graph_a_b,
    "PYQ-PHY-e5850b5e84b2": five_capacitors_ab,
    "PYQ-PHY-1c515d51e569": half_filled_with_k,
    "PYQ-PHY-8506d1fabf0f": triangle_three_capacitors,
    "PYQ-PHY-7f0748d7b162": pentagon_capacitors,
    "PYQ-PHY-de5ade3f4c03": series_parallel_9v,
}
