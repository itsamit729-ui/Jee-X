"""Mathematics: area under curves, linear programming, switching circuits."""

import math

from figlib import Figure


def lever(f, x, y, width=54, label="", below=True, size=26):
    """An open switch from (x, y) to (x + width, y), with an optional label."""
    f.switch(x, y, width=width)
    if label:
        f.text(x + width / 2, y + (38 if below else -30), label, size=size)


def area_between_sin_and_cos():
    """The region under both y = sin x and y = cos x, above the x-axis, from x = 2 pi to x = 5 pi / 2."""
    f = Figure(660, 470)
    x0, x1, base, height = 138, 528, 332, 218

    def px(t):                              # t = 0 at 2 pi, 1 at 5 pi / 2
        return x0 + (x1 - x0) * t

    sin = [(px(i / 60), base - height * math.sin(math.pi / 2 * i / 60)) for i in range(61)]
    cos = [(px(i / 60), base - height * math.cos(math.pi / 2 * i / 60)) for i in range(61)]
    region = sin[:31] + cos[30:] + [(x1, base), (x0, base)]
    f.clips = getattr(f, "clips", 0) + 1
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in region) + " Z"
    lines = "".join(f'<line x1="{x}" y1="{base - height}" x2="{x}" y2="{base}" stroke-width="1.5"/>' for x in range(x0 + 6, x1, 7))
    f.add(f'<clipPath id="shade"><path d="{d}"/></clipPath><g clip-path="url(#shade)">{lines}</g>')
    f.polyline(sin), f.polyline(cos)
    f.line(40, base, 620, base, arrow=True), f.line(620, base, 40, base, arrow=True)
    for x in (x0, px(0.5), x1):
        f.line(x, 440, x, 40, arrow=True), f.line(x, 40, x, 440, arrow=True)
    f.rect(152, 196, 104, 36, fill="#fff", width=2), f.text(204, 224, "<i>y</i> = sin <i>x</i>", size=26)
    f.rect(366, 82, 108, 36, fill="#fff", width=2), f.text(420, 110, "<i>y</i> = cos <i>x</i>", size=26)
    f.text(104, 366, "(2<i>π</i>, 0)", size=24)
    f.text(236, 372, "(", size=26), f.fraction(258, 360, "9<i>π</i>", "4", size=20), f.text(292, 372, ", 0)", size=24)
    f.text(430, 372, "(", size=26), f.fraction(452, 360, "5<i>π</i>", "2", size=20), f.text(486, 372, ", 0)", size=24)
    return f


def feasible_region_three_lines():
    """Region bounded by L1: x + 2y = 2, L2: 3x + 5y = 15, L3: 2x - 3y + 6 = 0 and the axes."""
    f = Figure(680, 460)
    ox, oy, u = 222, 292, 52

    def p(x, y):
        return ox + u * x, oy - u * y

    region = [p(0, 1), p(2, 0), p(5, 0), p(15 / 19, 48 / 19), p(0, 2)]
    f.hatch(region, spacing=18, width=1.2)
    f.line(22, oy, 632, oy, arrow=True), f.line(632, oy, 22, oy, arrow=True)
    f.line(ox, 420, ox, 36, arrow=True), f.line(ox, 36, ox, 420, arrow=True)
    for a, b in ((p(-2.6, 2.3), p(6.0, -2.0)), (p(-1.2, 3.72), p(7.4, -1.44)), (p(-3.6, -0.4), p(5.2, 5.47))):
        f.line(*a, *b, width=2.5, arrow=True), f.line(*b, *a, width=2.5, arrow=True)
    for pt in (p(0, 1), p(0, 2), p(0, 3), p(2, 0), p(5, 0), p(-3, 0)):
        f.dot(*pt, r=4)
    f.text(ox + 16, p(0, 3)[1] - 10, "(0, 3)", size=22, anchor="start"), f.text(ox - 14, p(0, 2)[1] - 12, "(0, 2)", size=22, anchor="end")
    f.text(ox + 38, p(0, 1)[1] + 2, "(0, 1)", size=22, anchor="start", halo=True)
    f.text(p(-3, 0)[0] - 18, oy - 16, "(−3, 0)", size=22), f.text(p(2, 0)[0], oy + 34, "(2, 0)", size=22)
    f.text(p(5, 0)[0] + 28, oy - 16, "(5, 0)", size=22)
    f.text(ox - 14, oy + 30, "O", size=24), f.text(650, oy + 8, "X", size=24), f.text(ox, 26, "Y", size=24)
    f.text(p(4.2, -1.55)[0], p(4.2, -1.55)[1], "<i>L</i><sub>1</sub>", size=24), f.text(644, 372, "<i>L</i><sub>2</sub>", size=24)
    f.text(p(5.3, 5.0)[0], p(5.3, 5.0)[1], "<i>L</i><sub>3</sub>", size=24)
    return f


def feasible_region_fbpce():
    """Region F B P C E bounded by 2x + y = 12, x + 2y = 12, x + 1.25y = 5 and the axes."""
    f = Figure(520, 520)
    ox, oy, u = 78, 416, 24.5

    def p(x, y):
        return ox + u * x, oy - u * y

    region = [p(0, 4), p(0, 6), p(4, 4), p(6, 0), p(5, 0)]
    f.hatch(region, spacing=8, width=1), f.hatch([(x, 2 * oy - y) for x, y in region], spacing=8, width=0)
    f.clips += 1
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in region) + " Z"
    lines = "".join(f'<line x1="{x}" y1="{oy - 160}" x2="{x - 160}" y2="{oy}" stroke-width="1"/>' for x in range(60, 420, 8))
    f.add(f'<clipPath id="cross"><path d="{d}"/></clipPath><g clip-path="url(#cross)">{lines}</g>')
    f.line(14, oy, 498, oy, arrow=True), f.line(498, oy, 14, oy, arrow=True)
    f.line(ox, 500, ox, 24, arrow=True), f.line(ox, 24, ox, 500, arrow=True)
    for a, b in ((p(-1.4, 14.8), p(7.6, -3.2)), (p(-2.4, 7.2), p(16.6, -2.3)), (p(-2.0, 5.6), p(7.6, -2.08))):
        f.line(*a, *b, width=2.5, arrow=True), f.line(*b, *a, width=2.5, arrow=True)
    for k in range(2, 17, 2):
        f.line(ox + u * k, oy - 5, ox + u * k, oy + 5, width=2)
        if k not in (6, 12):
            f.text(ox + u * k, oy + 28, str(k), size=18, halo=True)
    for k in range(2, 15, 2):
        f.line(ox - 5, oy - u * k, ox + 5, oy - u * k, width=2)
        if k not in (4, 6, 12):
            f.text(ox - 12, oy - u * k + 6, str(k), size=18, anchor="end", halo=True)
    f.text(ox - 16, oy + 24, "O", size=20), f.text(508, oy + 26, "X", size=20), f.text(ox - 18, 30, "Y", size=20)
    labels = (("F", p(0, 4), -16, 4), ("B", p(0, 6), -16, -6), ("P", p(4, 4), 12, -6), ("C", p(6, 0), 10, -10),
              ("E", p(5, 0), -8, 26), ("A", p(12, 0), 6, -12), ("D", p(0, 12), 14, 4))
    for name, (x, y), dx, dy in labels:
        f.text(x + dx, y + dy, name, size=20, halo=True)
    for text_, at, angle in (("2<i>x</i> + <i>y</i> = 12", p(8.3, -2.6), 63), ("<i>x</i> + 2<i>y</i> = 12", p(13.4, -2.3), 27),
                             ("<i>x</i> + 1.25<i>y</i> = 5", p(2.6, 1.3), 39)):
        with f.rotated(angle, round(at[0], 1), round(at[1], 1)):
            f.text(at[0], at[1], text_, size=17, halo=True)
    return f


def circuit_three_branches():
    """Lamp L and a cell in series with three parallel branches: S1; S1' and S2'; S1 and S2."""
    f = Figure(680, 480)
    left, right = 132, 512
    rows = (58, 150, 252)
    for y in rows:
        f.line(left, y, right, y)
    f.line(left, rows[0], left, rows[2]), f.line(right, rows[0], right, rows[2])
    for x, y, label in ((270, 58, "<i>S</i><sub>1</sub>"), (188, 150, "<i>S</i>′<sub>1</sub>"), (376, 150, "<i>S</i>′<sub>2</sub>"),
                        (188, 252, "<i>S</i><sub>1</sub>"), (376, 252, "<i>S</i><sub>2</sub>")):
        f.rect(x - 2, y - 6, 58, 12, fill="#fff", width=0), lever(f, x, y, label=label)
    f.polyline([(left, 150), (36, 150), (36, 274)]), f.polyline([(36, 302), (36, 432), (606, 432), (606, 314)])
    f.vcell(36, 288, gap=22, long=36, short=20)
    f.polyline([(right, 150), (606, 150), (606, 250)]), f.meter(606, 282, "<i>L</i>", r=32)
    return f


def circuit_s1_s2_s3():
    """Lamp L and a cell in series with three parallel branches: S1 and S2; S1' and S2; S3 and S2'."""
    f = Figure(680, 470)
    left, right = 118, 488
    rows = ((92, "<i>S</i><sub>1</sub>", "<i>S</i><sub>2</sub>"), (184, "<i>S</i>′<sub>1</sub>", "<i>S</i><sub>2</sub>"),
            (276, "<i>S</i><sub>3</sub>", "<i>S</i>′<sub>2</sub>"))
    for y, first, second in rows:
        f.line(left, y, right, y)
        for x, label in ((176, first), (336, second)):
            f.rect(x - 2, y - 6, 58, 12, fill="#fff", width=0), lever(f, x, y, label=label, size=28)
    f.line(left, 92, left, 276), f.line(right, 92, right, 276)
    f.polyline([(left, 184), (36, 184), (36, 398), (176, 398)]), f.polyline([(right, 184), (570, 184), (570, 398), (412, 398)])
    f.cell(188, 398, gap=20, long=30, short=16), f.line(198, 398, 210, 398), f.cell(222, 398, gap=20, long=30, short=16)
    f.line(232, 398, 348, 398), f.meter(380, 398, "<i>L</i>", r=32)
    f.arrowhead(84, 184, 0), f.arrowhead(540, 184, 0), f.arrowhead(570, 312, 90), f.arrowhead(470, 398, 180)
    f.arrowhead(104, 398, 180), f.arrowhead(36, 290, 270)
    f.text(166, 372, "+", size=28), f.text(250, 372, "−", size=28)
    return f


FIGURES = {
    "PYQ-MATH-d6b28b497765": area_between_sin_and_cos,
    "PYQ-MATH-ec89321acaa0": feasible_region_three_lines,
    "PYQ-MATH-fb362ad9002e": feasible_region_fbpce,
    "PYQ-MATH-8fbb88f34730": circuit_three_branches,
    "PYQ-MATH-e772316f5bac": circuit_s1_s2_s3,
}
