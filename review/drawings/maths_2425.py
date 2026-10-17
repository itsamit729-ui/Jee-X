"""Mathematics (MHT-CET 2024-25): linear programming graphs and a triangle with cevians.
The graphs are plotted from the questions' own equations; feasible regions are computed by clipping."""

from figlib import Figure

_hatch_id = [0]


class Plot:
    """Data coordinates -> drawing coordinates for one graph panel."""

    def __init__(self, f, left, top, width, height, xr, yr):
        self.f, self.xr, self.yr = f, xr, yr
        self.left, self.top, self.width, self.height = left, top, width, height

    def p(self, x, y):
        (x0, x1), (y0, y1) = self.xr, self.yr
        return (self.left + (x - x0) / (x1 - x0) * self.width, self.top + (y1 - y) / (y1 - y0) * self.height)

    def axes(self, xticks=(), yticks=(), size=24, names=("X", "Y"), primes=False, origin="O"):
        f, (x0, x1), (y0, y1) = self.f, self.xr, self.yr
        f.line(*self.p(x0, 0), *self.p(x1, 0), width=2.5, arrow=True)
        f.line(*self.p(0, y0), *self.p(0, y1), width=2.5, arrow=True)
        if primes:
            f.line(*self.p(0, 0), *self.p(x0, 0), width=2.5, arrow=True), f.line(*self.p(0, 0), *self.p(0, y0), width=2.5, arrow=True)
            f.text(*self._off(self.p(x0, 0), -6, -10), names[0] + "′", size=size, anchor="end")
            f.text(*self._off(self.p(0, y0), 20, 0), names[1] + "′", size=size, anchor="start")
        f.text(*self._off(self.p(x1, 0), 10, 8), names[0], size=size, anchor="start")
        f.text(*self._off(self.p(0, y1), 14, 6), names[1], size=size, anchor="start")
        if origin:
            f.text(*self._off(self.p(0, 0), -8, size), origin, size=size * 0.9, anchor="end")
        for t in xticks:
            x, y = self.p(t, 0)
            f.line(x, y - 5, x, y + 5, width=2), f.text(x, y + size + 4, str(t), size=size * 0.85)
        for t in yticks:
            x, y = self.p(0, t)
            f.line(x - 5, y, x + 5, y, width=2), f.text(x - 10, y + size * 0.3, str(t), size=size * 0.85, anchor="end")

    @staticmethod
    def _off(pt, dx, dy):
        return pt[0] + dx, pt[1] + dy

    def line(self, a, b, c, label="", at=None, size=24, arrows=True, width=2.5):
        """The line ax + by = c across the panel."""
        (x0, x1), (y0, y1) = self.xr, self.yr
        pts = []
        if b:
            for x in (x0, x1):
                pts.append((x, (c - a * x) / b))
        if a:
            for y in (y0, y1):
                pts.append(((c - b * y) / a, y))
        inside = sorted({(round(x, 6), round(y, 6)) for x, y in pts if x0 - 1e-9 <= x <= x1 + 1e-9 and y0 - 1e-9 <= y <= y1 + 1e-9})
        if len(inside) < 2:
            return
        (ax_, ay_), (bx_, by_) = inside[0], inside[-1]
        p1, p2 = self.p(ax_, ay_), self.p(bx_, by_)
        self.f.line(*p1, *p2, width=width, arrow=arrows)
        if arrows:
            self.f.line(*p2, *p1, width=width, arrow=True)
        if label:
            x, y = self.p(*at)
            self.f.text(x, y, label, size=size, halo=True)

    def region(self, constraints, box=None, spacing=10):
        """Hatch the set where every a*x + b*y <= c holds, for constraints given as (a, b, c)."""
        (x0, x1), (y0, y1) = box or (self.xr, self.yr)
        poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for a, b, c in constraints:
            poly = clip(poly, a, b, c)
            if not poly:
                return
        pts = [self.p(x, y) for x, y in poly]
        _hatch_id[0] += 1
        cid = f"r{_hatch_id[0]}"
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
        xs, ys = [x for x, _ in pts], [y for _, y in pts]
        lo, hi, h = min(xs), max(xs), max(ys) - min(ys)
        body = "".join(f'<line x1="{x:.1f}" y1="{max(ys):.1f}" x2="{x + h:.1f}" y2="{min(ys):.1f}" stroke-width="1.5"/>'
                       for x in range(int(lo - h), int(hi) + 1, spacing))
        self.f.add(f'<clipPath id="{cid}"><path d="{d}"/></clipPath><g clip-path="url(#{cid})">{body}</g>')
        self.f.add(f'<path d="{d}" stroke-width="2"/>')


def clip(poly, a, b, c):
    """Sutherland-Hodgman: keep the part of the polygon where a*x + b*y <= c."""
    out = []
    for i, cur in enumerate(poly):
        prev = poly[i - 1]
        fc, fp = a * cur[0] + b * cur[1] - c, a * prev[0] + b * prev[1] - c
        if fc <= 1e-9:
            if fp > 1e-9:
                t = fp / (fp - fc)
                out.append((prev[0] + (cur[0] - prev[0]) * t, prev[1] + (cur[1] - prev[1]) * t))
            out.append(cur)
        elif fp <= 1e-9:
            t = fp / (fp - fc)
            out.append((prev[0] + (cur[0] - prev[0]) * t, prev[1] + (cur[1] - prev[1]) * t))
    return out


# a*x + b*y >= c is written as (-a, -b, -c)
def ge(a, b, c):
    return (-a, -b, -c)


POSITIVE = [ge(1, 0, 0), ge(0, 1, 0)]


def lp_three_lines():
    """Lines 3x + 8y = 24, 4x + 5y = 20 and 5x + 3y = 15; shaded: 3x + 8y >= 24, 4x + 5y <= 20, 5x + 3y <= 15, x, y >= 0."""
    f = Figure(640, 560)
    g = Plot(f, 70, 30, 520, 460, (-1.5, 9), (-1.2, 8))
    g.axes(xticks=range(1, 9), yticks=range(1, 8), names=("X", "Y"), primes=True)
    g.line(3, 8, 24), g.line(4, 5, 20), g.line(5, 3, 15)
    g.region([ge(3, 8, 24), (4, 5, 20), (5, 3, 15)] + POSITIVE)
    return f


def lp_four_options():
    """Lines x + y = 1, 7x + 9y = 63, y = 5 and x = 6 in four panels; Fig. 1 shades x + y >= 1, 7x + 9y <= 63, y <= 5, x <= 6, x, y >= 0."""
    f = Figure(760, 620)
    regions = {
        1: [[ge(1, 1, 1), (7, 9, 63), (0, 1, 5), (1, 0, 6)] + POSITIVE],
        2: [[(7, 9, 63), ge(0, 1, 5)] + POSITIVE, [ge(7, 9, 63), (0, 1, 5), (1, 0, 6)] + POSITIVE],
        3: [[ge(7, 9, 63), (1, 0, 6), (0, 1, 7)] + POSITIVE],
        4: [[ge(1, 1, 1), (0, 1, 5), (1, 0, 6)] + POSITIVE, [(7, 9, 63), ge(0, 1, 5)] + POSITIVE],
    }
    for n, (left, top) in zip(range(1, 5), ((20, 10), (400, 10), (20, 320), (400, 320))):
        g = Plot(f, left, top, 340, 250, (-1, 10), (-1, 10.5))
        g.axes(xticks=range(1, 10), yticks=range(1, 11), size=18)
        for a, b, c in ((1, 1, 1), (7, 9, 63), (0, 1, 5), (1, 0, 6)):
            g.line(a, b, c, width=2)
        for cons in regions[n]:
            g.region(cons, spacing=8)
        f.text(left + 170, top + 290, f"Fig. {n}", size=22)
    return f


def lp_wedge_y_x():
    """Lines y = x and -x + 3y = 3; shaded: x - y >= 0, -x + 3y <= 3, x, y >= 0 (up to x = 5.7)."""
    f = Figure(640, 520)
    g = Plot(f, 40, 30, 560, 420, (-3.8, 6.8), (-1.5, 6))
    g.axes(xticks=(-3, -2, -1, 1, 2, 3, 4, 5, 6), yticks=range(1, 6), primes=True, size=26)
    g.line(1, -1, 0, label="<i>y</i> = <i>x</i>", at=(2.6, 4.6), size=26)
    g.line(-1, 3, 3, label="−<i>x</i> + 3<i>y</i> = 3", at=(5.2, 5.4), size=26)
    g.region([ge(1, -1, 0), (-1, 3, 3), (1, 0, 5.7)] + POSITIVE)
    return f


def lp_two_lines_options():
    """Lines 2x + 3y = 6 and x + 4y = 4 in four panels; Fig. 1 shades 2x + 3y <= 6, x + 4y >= 4, x, y >= 0."""
    f = Figure(760, 560)
    regions = {
        1: [(2, 3, 6), ge(1, 4, 4)] + POSITIVE,
        2: [(2, 3, 6), (1, 4, 4)] + POSITIVE,
        3: [(2, 3, 6)] + POSITIVE,
        4: [ge(2, 3, 6), (1, 4, 4)] + POSITIVE,
    }
    for n, (left, top) in zip(range(1, 5), ((20, 10), (400, 10), (20, 290), (400, 290))):
        g = Plot(f, left, top, 330, 220, (-1, 6), (-1.2, 4.5))
        g.axes(xticks=range(1, 6), yticks=range(1, 5), size=20)
        g.line(2, 3, 6, width=2), g.line(1, 4, 4, width=2)
        g.region(regions[n], spacing=8)
        f.text(left + 165, top + 262, f"Fig. {n}", size=22)
    return f


def lp_max_36():
    """Lines 2x - 3y = -15, x + y = 10 and x = 6; shaded: 2x - 3y >= -15, x + y <= 10, x <= 6, x, y >= 0."""
    f = Figure(700, 520)
    g = Plot(f, 30, 20, 640, 440, (-10.5, 11), (-1.5, 12))
    g.axes(xticks=(-10, -8, -6, -4, -2, 2, 4, 6, 8, 10), yticks=range(1, 12), primes=True, size=22)
    g.line(2, -3, -15), g.line(1, 1, 10), g.line(1, 0, 6)
    g.region([ge(2, -3, -15), (1, 1, 10), (1, 0, 6)] + POSITIVE)
    return f


def lp_four_vertices():
    """Lines x + 2y = 50, 2x + y = 100 and 2x - y = 0; shaded: x + 2y >= 50, 2x + y <= 100, 2x - y <= 0, x, y >= 0; corners (0, 25), (10, 20), (25, 50), (0, 100)."""
    f = Figure(640, 560)
    g = Plot(f, 60, 20, 540, 480, (-12, 66), (-18, 112))
    g.axes(xticks=(20, 40, 60), yticks=(20, 40, 60, 80, 100), size=26, origin="0")
    g.line(1, 2, 50), g.line(2, 1, 100), g.line(2, -1, 0)
    g.region([ge(1, 2, 50), (2, 1, 100), (2, -1, 0)] + POSITIVE)
    for (x, y), dx, dy, anchor in (((0, 100), 16, -6, "start"), ((25, 50), 16, -6, "start"), ((0, 25), -12, 30, "end"),
                                   ((10, 20), 14, 34, "start"), ((50, 0), 10, -16, "start")):
        px, py = g.p(x, y)
        f.circle(px, py, 8, width=2.5), f.text(px + dx, py + dy, f"({x}, {y})", size=24, anchor=anchor, halo=True)
    return f


def lp_x1_y3():
    """Lines x = 1, y = 3, x - 2y = 2 and 6x + 7y = 42; shaded: x >= 1, y <= 3, x - 2y <= 2, 6x + 7y <= 42, x, y >= 0."""
    f = Figure(640, 520)
    g = Plot(f, 40, 20, 560, 440, (-2.5, 8.5), (-2.5, 8))
    g.axes(xticks=range(1, 8), yticks=range(1, 8), primes=True, size=26)
    g.line(1, 0, 1), g.line(0, 1, 3), g.line(1, -2, 2), g.line(6, 7, 42)
    g.region([ge(1, 0, 1), (0, 1, 3), (1, -2, 2), (6, 7, 42)] + POSITIVE)
    return f


def lp_unbounded_box():
    """Lines x + 2y = 6, 5x + 3y = 15, x = 7 and y = 6; shaded: x + 2y >= 6, 5x + 3y >= 15, x <= 7, y <= 6, x, y >= 0."""
    f = Figure(640, 520)
    g = Plot(f, 40, 20, 560, 440, (-1, 9), (-1, 7.8))
    g.axes(xticks=range(1, 9), yticks=range(1, 8), size=26, origin="0")
    g.line(1, 2, 6), g.line(5, 3, 15), g.line(1, 0, 7), g.line(0, 1, 6)
    g.region([ge(1, 2, 6), ge(5, 3, 15), (1, 0, 7), (0, 1, 6)] + POSITIVE)
    return f


def lp_regions_s1_s4():
    """Lines -x + y = 3, 2x + 3y = 12, x = 4 and y = 3 divide the plane; S1 marks the region 2x + 3y >= 12, -x + y <= 3, x <= 4, y >= 3."""
    f = Figure(700, 560)
    g = Plot(f, 30, 20, 640, 480, (-5, 8), (-3.5, 8.5))
    g.axes(xticks=(-4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7), yticks=range(1, 8), primes=True, size=24, origin="")
    g.line(-1, 1, 3, label="−<i>x</i> + <i>y</i> = 3", at=(-3.4, -3), size=26)
    g.line(2, 3, 12, label="2<i>x</i> + 3<i>y</i> = 12", at=(6.6, -2.8), size=26)
    g.line(1, 0, 4, label="<i>x</i> = 4", at=(4.2, -3.1), size=26)
    g.line(0, 1, 3, label="<i>y</i> = 3", at=(7.4, 3.3), size=26)
    for name, (x, y) in {"1": (2.0, 4.6), "2": (0.8, 1.8), "3": (2.8, 2.4), "4": (-1.0, 3.5)}.items():
        f.text(*g.p(x, y), f"S<sub>{name}</sub>", size=26, halo=True)
    return f


def lp_wedge_both():
    """Lines x - y = 0 and x + y = 0 through O; shaded: x - y >= 0, x + y >= 0 (the wedge to the right, up to x = 3)."""
    f = Figure(640, 420)
    g = Plot(f, 30, 20, 580, 380, (-5, 5), (-3.3, 3.3))
    g.axes(size=30, origin="0")
    g.line(1, -1, 0, label="<i>x</i> − <i>y</i> = 0", at=(4.3, 2.4), size=28)
    g.line(1, 1, 0, label="<i>x</i> + <i>y</i> = 0", at=(4.0, -2.6), size=28)
    g.region([ge(1, -1, 0), ge(1, 1, 0), (1, 0, 3)], spacing=8)
    return f


def lp_scholarship():
    """Lines x + y = 15, x + y = 10, x = 5 and y = 4; shaded ABCD with A (5, 5), B (5, 10), C (11, 4), D (6, 4)."""
    f = Figure(640, 480)
    g = Plot(f, 30, 20, 580, 420, (-3, 18), (-3, 18))
    g.axes(size=28, origin="O")
    g.line(1, 1, 15, label="<i>x</i> + <i>y</i> = 15", at=(9.5, 8.5), size=26)
    g.line(1, 1, 10, label="<i>x</i> + <i>y</i> = 10", at=(10.6, 1.8), size=26)
    g.line(1, 0, 5, label="<i>x</i> = 5", at=(6.6, -1.8), size=26)
    g.line(0, 1, 4, label="<i>y</i> = 4", at=(16.5, 5.2), size=26)
    g.region([(1, 1, 15), ge(1, 1, 10), ge(1, 0, 5), ge(0, 1, 4)])
    for name, (x, y), (dx, dy) in (("A", (5, 5), (-22, 10)), ("B", (5, 10), (-22, 0)), ("C", (11, 4), (16, -12)), ("D", (6, 4), (-6, 34))):
        px, py = g.p(x, y)
        f.text(px + dx, py + dy, name, size=28, halo=True)
    return f


def lp_three_lines_l123():
    """Lines L1: y - x = 1, L2: 2x + 5y = 10 and L3: x + y = 1, with unit ticks on both axes."""
    f = Figure(640, 480)
    g = Plot(f, 30, 20, 580, 420, (-2.8, 6.6), (-1.5, 6))
    g.axes(xticks=(-2, -1, 1, 2, 3, 4, 5, 6), yticks=range(1, 6), size=26, origin="0")
    g.line(-1, 1, 1, label="L<sub>1</sub>", at=(4.0, 5.0), size=26)
    g.line(2, 5, 10, label="L<sub>2</sub>", at=(6.3, -0.9), size=26)
    g.line(1, 1, 1, label="L<sub>3</sub>", at=(2.6, -1.3), size=26)
    for t in range(1, 6):
        f.dot(*g.p(0, t), r=5)
    return f


def triangle_cevians():
    """Triangle ABC: P on AC, Q on BC; BP and AQ meet at M."""
    f = Figure(640, 470)
    a, b, c = (210, 40), (40, 400), (600, 390)
    f.path([a, b, c], close=True, width=4)
    p = (a[0] + (c[0] - a[0]) * 3 / 7, a[1] + (c[1] - a[1]) * 3 / 7)
    q = (b[0] + (c[0] - b[0]) * 4 / 7, b[1] + (c[1] - b[1]) * 4 / 7)
    f.line(*b, *p, width=4), f.line(*a, *q, width=4)
    # M: intersection of BP and AQ
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = b, p, a, q
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    m = (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    f.text(a[0] + 18, a[1] + 4, "A", size=34, anchor="start"), f.text(b[0] - 8, b[1] + 40, "B", size=34)
    f.text(c[0] + 10, c[1] + 40, "C", size=34), f.text(p[0] + 18, p[1] - 6, "P", size=34, anchor="start")
    f.text(q[0], q[1] + 44, "Q", size=34), f.text(m[0] - 18, m[1] - 10, "M", size=34, anchor="end")
    return f


# ---- switching circuits

def switch(f, x, y, label, w=56, size=22, dot=False):
    """An open switch on a horizontal wire, from x to x + w, labelled below."""
    f.line(x, y, x + w - 4, y - 22, width=2.5)
    if dot:
        f.dot(x + w, y, r=5)
    f.text(x + w / 2, y + size + 6, label, size=size)


def row(f, x1, x2, y, labels, size=22, dot=False, w=56):
    """A wire from x1 to x2 with the labelled switches spread along it."""
    n = len(labels)
    gap = (x2 - x1 - n * w) / (n + 1)
    x = x1
    for label in labels:
        f.line(x, y, x + gap, y, width=2.5)
        switch(f, x + gap, y, label, w=w, size=size, dot=dot)
        x += gap + w
    f.line(x, y, x2, y, width=2.5)


def block(f, x1, x2, y1, y2, top, bottom, size=22, dot=False, w=56):
    """Two rows of switches in parallel between x1 and x2."""
    f.line(x1, y1, x1, y2, width=2.5), f.line(x2, y1, x2, y2, width=2.5)
    row(f, x1, x2, y1, top, size=size, dot=dot, w=w), row(f, x1, x2, y2, bottom, size=size, dot=dot, w=w)


def supply(f, x1, x2, y_top, y, size=22):
    """Side wires down from y_top and a bottom wire with a cell and a lamp L."""
    f.line(x1, y_top, x1, y, width=2.5), f.line(x2, y_top, x2, y, width=2.5)
    mid = (x1 + x2) / 2
    f.line(x1, y, mid - 50, y, width=2.5), f.cell(mid - 40, y, gap=14, long=16, short=9)
    f.line(mid - 33, y, mid + 20, y, width=2.5), f.meter(mid + 40, y, "L", r=18), f.line(mid + 58, y, x2, y, width=2.5)


S = lambda n, p="": f"S<sub>{n}</sub>{p}"  # noqa: E731


def five_or_six_circuits(names):
    """Circuits: two branches (S1, S2) | (S1, S3); S1 | (S2, S3); S1 then (S2 parallel S3); S1, S2, S3 in series; (S1, S2) | S3."""
    f = Figure(760, 60 + 180 * ((len(names) + 1) // 2))
    for i, name in enumerate(names):
        col, line_ = i % 2, i // 2
        x1, x2, top = 70 + col * 370, 330 + col * 370, 40 + line_ * 180
        f.text(x1 - 24, top + 40, name, size=26, anchor="end")
        kind = i
        if kind == 0:
            block(f, x1, x2, top, top + 64, [S(1), S(2)], [S(1), S(3)]), supply(f, x1, x2, top + 64, top + 140)
        elif kind == 1:
            block(f, x1, x2, top, top + 64, [S(1)], [S(2), S(3)]), supply(f, x1, x2, top + 64, top + 140)
        elif kind == 2:
            row(f, x1, x1 + 100, top + 30, [S(1)]), block(f, x1 + 100, x2 - 20, top, top + 64, [S(2)], [S(3)])
            f.line(x2 - 20, top + 30, x2, top + 30, width=2.5), supply(f, x1, x2, top + 30, top + 140)
        elif kind == 3:
            row(f, x1, x2, top + 30, [S(1), S(2), S(3)]), supply(f, x1, x2, top + 30, top + 140)
        else:
            block(f, x1, x2, top, top + 64, [S(1), S(2)], [S(3)]), supply(f, x1, x2, top + 64, top + 140)
    return f


def circuits_i_to_v():
    """Circuits i-v: (S1, S2) | (S1, S3); S1 | (S2, S3); S1 then (S2 | S3); S1, S2, S3 in series; (S1, S2) | S3."""
    return five_or_six_circuits(["i.", "ii.", "iii.", "iv.", "v."])


def circuits_a_to_e():
    """Circuits (A)-(E): (S1, S2) | (S1, S3); S1 | (S2, S3); S1 then (S2 | S3); S1, S2, S3 in series; (S1, S2) | S3."""
    return five_or_six_circuits(["(A)", "(B)", "(C)", "(D)", "(E)"])


def two_branch_circuit(top_first, top_block, bottom, terminals=False):
    """Upper branch: a switch then two switches in parallel; lower branch: switches in series. Both between the same two nodes."""
    f = Figure(760, 440 if not terminals else 300)
    l, r, yt, yb = 140, 640, 110, 250
    f.line(l, yt, l, yb, width=2.5), f.line(r, yt, r, yb, width=2.5)
    row(f, l, l + 170, yt, [top_first], size=28, dot=True, w=70)
    block(f, l + 170, r - 40, 50, 170, top_block[:1], top_block[1:], size=28, dot=True, w=70)
    f.line(r - 40, yt, r, yt, width=2.5)
    row(f, l, r, yb, bottom, size=28, dot=True, w=70)
    mid = (yt + yb) / 2
    if terminals:
        f.line(30, mid, l, mid, width=2.5), f.dot(30, mid, r=6), f.line(r, mid, 730, mid, width=2.5), f.dot(730, mid, r=6)
        f.arrowhead(70, mid, 180, size=14), f.arrowhead(690, mid, 0, size=14)
    else:
        f.line(40, mid, l, mid, width=2.5), f.line(r, mid, 720, mid, width=2.5)
        f.line(40, mid, 40, 400, width=2.5), f.line(720, mid, 720, 400, width=2.5)
        f.line(40, 400, 300, 400, width=2.5), f.cell(312, 400, gap=16, long=26, short=14), f.line(320, 400, 460, 400, width=2.5)
        f.meter(490, 400, "L", r=28), f.line(518, 400, 720, 400, width=2.5)
        f.arrowhead(40, 260, -90, size=16), f.arrowhead(720, 260, 90, size=16)
    return f


def circuit_p_and_q_or_r():
    """Upper branch: S1 then S2 parallel S3; lower branch: S1, S2, S1 in series; cell and lamp L."""
    return two_branch_circuit(S(1), [S(2), S(3)], [S(1), S(2), S(1)])


def circuit_primed_switches():
    """Upper branch: S1 then S2' parallel S3'; lower branch: S2, S3, S1 in series; cell and lamp L."""
    return two_branch_circuit(S(1), [S(2, "′"), S(3, "′")], [S(2), S(3), S(1)])


def circuit_terminals_primed():
    """Between two terminals: upper branch S1 then S2 parallel S3; lower branch S3', S2', S1 in series."""
    return two_branch_circuit(S(1), [S(2), S(3)], [S(3, "′"), S(2, "′"), S(1)], terminals=True)


def circuit_s1_block_s2():
    """S1, then S1' parallel S2', then S2, in series with a cell and a lamp L."""
    f = Figure(760, 380)
    y = 110
    row(f, 40, 240, y, [S(1)], size=30, w=70)
    block(f, 240, 500, 50, 170, [S(1, "′")], [S(2, "′")], size=30, w=70)
    row(f, 500, 720, y, [S(2)], size=30, w=70)
    f.line(40, y, 40, 330, width=2.5), f.line(720, y, 720, 330, width=2.5)
    f.line(40, 330, 300, 330, width=2.5), f.cell(312, 330, gap=16, long=26, short=14), f.line(320, 330, 460, 330, width=2.5)
    f.meter(490, 330, "L", r=28), f.line(518, 330, 720, 330, width=2.5)
    f.text(292, 366, "+", size=26), f.text(334, 366, "−", size=26)
    return f


FIGURES = {
    "PYQ-MATH-5e0505add6aa": circuits_i_to_v,
    "PYQ-MATH-c69308ccdbc0": circuits_a_to_e,
    "PYQ-MATH-36859b87586e": circuit_p_and_q_or_r,
    "PYQ-MATH-a12f21f99b7c": circuit_primed_switches,
    "PYQ-MATH-d00e0afb706a": circuit_terminals_primed,
    "PYQ-MATH-b9b4947e1a54": circuit_s1_block_s2,
    "PYQ-MATH-584ae9f5f497": lp_three_lines,
    "PYQ-MATH-9a239db954c6": lp_four_options,
    "PYQ-MATH-93c3b9b83351": lp_wedge_y_x,
    "PYQ-MATH-e19afa038229": lp_two_lines_options,
    "PYQ-MATH-53479ed4d3bf": lp_max_36,
    "PYQ-MATH-8efc50184bef": lp_four_vertices,
    "PYQ-MATH-a0af7132b4a2": lp_x1_y3,
    "PYQ-MATH-c12ccfdd8fb7": lp_unbounded_box,
    "PYQ-MATH-228502c1cb23": lp_regions_s1_s4,
    "PYQ-MATH-4a5d2e413ecc": lp_wedge_both,
    "PYQ-MATH-acd6f9c8db29": lp_scholarship,
    "PYQ-MATH-5eb03fc627d4": lp_three_lines_l123,
    "PYQ-MATH-258989f30856": triangle_cevians,
}
