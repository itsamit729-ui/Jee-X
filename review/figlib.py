"""Drawing kit for our own question figures: a small SVG canvas with the parts physics, chemistry
and maths figures are made of (circuit components, springs, hatching, axes, logic gates, rings)."""

import math

INK = "#1f2937"
SERIF = "'Times New Roman', Times, serif"


class Figure:
    def __init__(self, width, height):
        self.width, self.height, self.parts = width, height, []

    def add(self, markup):
        self.parts.append(markup)

    def line(self, x1, y1, x2, y2, width=3, dash=None, arrow=False):
        extra = (f' stroke-dasharray="{dash}"' if dash else "") + (' marker-end="url(#arrow)"' if arrow else "")
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke-width="{width}"{extra}/>')

    def path(self, points, width=3, close=False, fill="none"):
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points) + (" Z" if close else "")
        self.add(f'<path d="{d}" stroke-width="{width}" fill="{fill}"/>')

    def circle(self, x, y, r, fill="none", width=3):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke-width="{width}"/>')

    def rect(self, x, y, w, h, fill="none", width=3):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke-width="{width}"/>')

    def text(self, x, y, content, size=30, anchor="middle", halo=False):
        """`content` may use <i>..</i> for variables and <sub>/<sup> for scripts. `halo` puts a white
        outline behind the text, for labels that sit on hatching or cross a line."""
        content = (content.replace("<i>", '<tspan font-style="italic">').replace("</i>", "</tspan>")
                   .replace("<sub>", '<tspan dy="0.35em" font-size="70%">')
                   .replace("</sub>", '</tspan><tspan dy="-0.245em">&#8203;</tspan>')
                   .replace("<sup>", '<tspan dy="-0.6em" font-size="70%">')
                   .replace("</sup>", '</tspan><tspan dy="0.42em">&#8203;</tspan>'))
        outline = 'stroke="#fff" stroke-width="7" paint-order="stroke"' if halo else 'stroke="none"'
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" {outline} '
                 f'fill="{INK}" font-family="{SERIF}">{content}</text>')

    def arc(self, cx, cy, r, deg1, deg2, width=1.5):
        """An arc about (cx, cy) between two directions (degrees, 0 = right, 90 = down)."""
        steps = max(2, int(abs(deg2 - deg1) / 3))
        self.path([(cx + r * math.cos(math.radians(deg1 + (deg2 - deg1) * i / steps)),
                    cy + r * math.sin(math.radians(deg1 + (deg2 - deg1) * i / steps))) for i in range(steps + 1)],
                  width=width)

    def arrowhead(self, x, y, angle_deg, size=13):
        """A solid arrowhead with its tip at (x, y), pointing along angle_deg (0 = right, 90 = down)."""
        a = math.radians(angle_deg)
        back = (x - size * math.cos(a), y - size * math.sin(a))
        side = (size * 0.5 * math.sin(a), -size * 0.5 * math.cos(a))
        pts = [(x, y), (back[0] + side[0], back[1] + side[1]), (back[0] - side[0], back[1] - side[1])]
        self.path(pts, width=1, close=True, fill=INK)

    # ---- circuit and mechanics parts, all drawn along a horizontal wire at height y

    def resistor(self, x1, x2, y, peaks=5, height=13):
        step = (x2 - x1) / (peaks * 2)
        pts = [(x1, y)] + [(x1 + step * (i + 0.5), y + (height if i % 2 else -height)) for i in range(peaks * 2)] + [(x2, y)]
        self.path(pts)

    def capacitor(self, x, y, gap=14, height=30):
        for px in (x - gap / 2, x + gap / 2):
            self.line(px, y - height, px, y + height)

    def cell(self, x, y, gap=22, long=38, short=20):
        """Long plate (positive) on the left, short plate on the right."""
        self.line(x - gap / 2, y - long, x - gap / 2, y + long, width=3)
        self.line(x + gap / 2, y - short, x + gap / 2, y + short, width=5)

    def diode(self, x, y, pointing="right", size=20):
        s = size if pointing == "right" else -size
        self.path([(x - s, y - size), (x + s, y), (x - s, y + size)], close=True)
        self.line(x + s, y - size, x + s, y + size)

    def switch(self, x, y, width=52):
        self.circle(x, y, 5, fill="white", width=2.5)
        self.circle(x + width, y, 5, fill="white", width=2.5)
        self.line(x + 4, y - 3, x + width - 6, y - 22, width=2.5)

    def wall(self, x, y1, y2, side):
        """A fixed support: a vertical line with hatching on the given side ("left" or "right")."""
        self.line(x, y1, x, y2, width=4)
        d = -18 if side == "left" else 18
        for y in range(int(y1) + 4, int(y2), 16):
            self.line(x, y, x + d, y + 14, width=2)

    def hatch(self, points, spacing=14, width=1.5):
        """Fill a polygon with 45-degree hatching, clipped to it."""
        self.clips = getattr(self, "clips", 0) + 1
        cid = f"clip{self.clips}"
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points) + " Z"
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        lines = "".join(f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x + (y1 - y0):.1f}" y2="{y0:.1f}" stroke-width="{width}"/>'
                        for x in range(int(x0 - (y1 - y0)), int(x1) + 1, spacing))
        self.add(f'<clipPath id="{cid}"><path d="{d}"/></clipPath><g clip-path="url(#{cid})">{lines}</g>')

    # ---- general drawing aids

    def rotated(self, angle, cx, cy):
        """with f.rotated(90, x, y): ... draws the parts inside turned about (cx, cy), e.g. a
        vertical resistor from the horizontal one. Put labels outside the block."""
        fig = self

        class Turn:
            def __enter__(self):
                self.start = len(fig.parts)

            def __exit__(self, *exc):
                inner = "".join(fig.parts[self.start:])
                del fig.parts[self.start:]
                fig.add(f'<g transform="rotate({angle} {cx} {cy})">{inner}</g>')
        return Turn()

    def dot(self, x, y, r=5):
        self.circle(x, y, r, fill=INK, width=1)

    def polyline(self, points, width=3, dash=None):
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" stroke-width="{width}"{extra}/>')

    def curve(self, fn, x1, x2, width=3, steps=80, dash=None):
        """Plot y = fn(x) in drawing coordinates from x1 to x2."""
        self.polyline([(x1 + (x2 - x1) * i / steps, fn(x1 + (x2 - x1) * i / steps)) for i in range(steps + 1)],
                      width=width, dash=dash)

    def axes(self, ox, oy, xlen, ylen, xlabel="", ylabel="", origin="", size=26, xneg=0, yneg=0):
        """Graph axes from the origin (ox, oy): x to the right, y upward."""
        self.line(ox - xneg, oy, ox + xlen, oy, arrow=True)
        self.line(ox, oy + yneg, ox, oy - ylen, arrow=True)
        if xlabel:
            self.text(ox + xlen + 6, oy + 30, xlabel, size=size)
        if ylabel:
            self.text(ox - 24, oy - ylen + 8, ylabel, size=size)
        if origin:
            self.text(ox - 16, oy + 26, origin, size=size)

    def meter(self, x, y, letter, r=24):
        """A circled instrument or lamp: A, V, G, L ..."""
        self.circle(x, y, r, fill="#fff")
        self.text(x, y + 10, letter, size=28)

    def ground(self, x, y):
        self.line(x, y, x, y + 14)
        for i, half in enumerate((18, 12, 6)):
            self.line(x - half, y + 14 + i * 8, x + half, y + 14 + i * 8, width=2.5)

    def ac_source(self, x, y, r=26):
        self.circle(x, y, r, fill="#fff")
        self.add(f'<path d="M{x - 16},{y} q8,-18 16,0 t16,0" stroke-width="3"/>')

    def block(self, x, y, w, h, label="", size=28):
        self.rect(x, y, w, h, fill="#fff")
        if label:
            self.text(x + w / 2, y + h / 2 + size * 0.34, label, size=size)

    def fraction(self, x, y, top, bottom, size=24):
        """A stacked fraction centred on x, with its bar at height y."""
        plain = lambda t: len(t.replace("<i>", "").replace("</i>", ""))  # noqa: E731
        half = max(plain(top), plain(bottom)) * size * 0.3 + 4
        self.text(x, y - 7, top, size=size)
        self.line(x - half, y, x + half, y, width=1.5)
        self.text(x, y + size * 0.95, bottom, size=size)

    def vector(self, x1, y1, x2, y2, width=3):
        self.line(x1, y1, x2, y2, width=width, arrow=True)

    def right_angle(self, x, y, dx, dy, size=14):
        """The square mark of a right angle at (x, y), opening towards (dx, dy) = (+-1, +-1)."""
        self.polyline([(x + dx * size, y), (x + dx * size, y + dy * size), (x, y + dy * size)], width=1.5)

    def vcapacitor(self, x, y, gap=14, half=30):
        """A capacitor in a vertical wire: two horizontal plates."""
        for py in (y - gap / 2, y + gap / 2):
            self.line(x - half, py, x + half, py)

    def vresistor(self, x, y1, y2, peaks=5, height=13):
        step = (y2 - y1) / (peaks * 2)
        self.path([(x, y1)] + [(x + (height if i % 2 else -height), y1 + step * (i + 0.5)) for i in range(peaks * 2)]
                  + [(x, y2)])

    def vcell(self, x, y, gap=22, long=38, short=20, positive="top"):
        """A cell in a vertical wire; the long plate is the positive one."""
        up, down = (y - gap / 2, y + gap / 2) if positive == "top" else (y + gap / 2, y - gap / 2)
        self.line(x - long, up, x + long, up, width=3)
        self.line(x - short, down, x + short, down, width=5)

    def terminal(self, x, y, label="", dx=0, dy=-16, size=28, filled=False):
        self.circle(x, y, 6, fill=INK if filled else "#fff", width=2.5)
        if label:
            self.text(x + dx, y + dy, label, size=size)

    def dim(self, x1, y1, x2, y2, width=2):
        """A dimension line with an arrowhead at both ends."""
        self.line(x1, y1, x2, y2, width=width, arrow=True)
        self.line(x2, y2, x1, y1, width=width, arrow=True)

    # ---- logic gates: drawn with the output to the right; return (input pins, output pin)

    def gate(self, kind, x, y, w=70, h=56):
        """kind: AND, OR, NAND, NOR, NOT, XOR. (x, y) is the middle of the left edge.
        Returns ([input points], output point)."""
        top, bot, bubble = y - h / 2, y + h / 2, kind in ("NAND", "NOR", "NOT")
        if kind == "NOT":
            self.path([(x, top + 6), (x + w * 0.75, y), (x, bot - 6)], close=True, fill="#fff")
            tip, pins = x + w * 0.75, [(x, y)]
        elif kind in ("AND", "NAND"):
            r = h / 2
            self.add(f'<path d="M{x},{top} H{x + w - r} A{r},{r} 0 0 1 {x + w - r},{bot} H{x} Z" stroke-width="3" fill="#fff"/>')
            tip, pins = x + w, [(x, y - h * 0.25), (x, y + h * 0.25)]
        else:
            self.add(f'<path d="M{x},{top} Q{x + w * 0.55},{top} {x + w},{y} Q{x + w * 0.55},{bot} {x},{bot} '
                     f'Q{x + w * 0.28},{y} {x},{top} Z" stroke-width="3" fill="#fff"/>')
            if kind == "XOR":
                self.add(f'<path d="M{x - 10},{top} Q{x + w * 0.28 - 10},{y} {x - 10},{bot}" stroke-width="3"/>')
            tip, pins = x + w, [(x + 9, y - h * 0.25), (x + 9, y + h * 0.25)]
        if bubble:
            self.circle(tip + 7, y, 7, fill="#fff")
            tip += 14
        return pins, (tip, y)

    # ---- skeletal formulae

    def bonds(self, points, double=(), width=3, offset=7):
        """A zig-zag chain through `points`; `double` lists the indices i of bonds i -> i+1 drawn double."""
        self.polyline(points, width=width)
        for i in double:
            (x1, y1), (x2, y2) = points[i], points[i + 1]
            length = math.hypot(x2 - x1, y2 - y1)
            nx, ny = -(y2 - y1) / length * offset, (x2 - x1) / length * offset
            tx, ty = (x2 - x1) * 0.12, (y2 - y1) * 0.12
            self.line(x1 + nx + tx, y1 + ny + ty, x2 + nx - tx, y2 + ny - ty, width=width)

    def ring(self, cx, cy, r=48, sides=6, aromatic=True, start=-90, double=None):
        """A carbon ring; returns its corner points (first at the top, clockwise). `aromatic` draws
        alternating inner double bonds, or pass `double` = the edges (i -> i+1) to double."""
        pts = [(cx + r * math.cos(math.radians(start + 360 / sides * i)),
                cy + r * math.sin(math.radians(start + 360 / sides * i))) for i in range(sides)]
        self.path(pts, close=True)
        edges = double if double is not None else (range(0, sides, 2) if aromatic else ())
        for i in edges:
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % sides]
            f1, f2 = 0.78, 0.78
            self.line(cx + (x1 - cx) * f1 + (x2 - x1) * 0.1, cy + (y1 - cy) * f1 + (y2 - y1) * 0.1,
                      cx + (x2 - cx) * f2 - (x2 - x1) * 0.1, cy + (y2 - cy) * f2 - (y2 - y1) * 0.1, width=2.5)
        return pts

    def atom(self, x, y, label, size=28, anchor="middle"):
        """An atom or group label on a white patch, so bonds stop at it."""
        self.text(x, y + size * 0.35, label, size=size, anchor=anchor, halo=True)

    def svg(self) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" '
                f'width="{self.width}" height="{self.height}" fill="none" stroke="{INK}" '
                f'stroke-linecap="round" stroke-linejoin="round">\n'
                f'<defs><marker id="arrow" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="15" markerHeight="15" '
                f'markerUnits="userSpaceOnUse" '
                f'orient="auto-start-reverse"><path d="M1,1 L11,6 L1,11 Z" fill="{INK}" stroke="none"/></marker></defs>\n'
                f'<rect width="{self.width}" height="{self.height}" fill="#fff" stroke="none"/>\n'
                + "\n".join(self.parts) + "\n</svg>\n")


def spring_points(x1, x2, y, turns, radius):
    """Points of a coil whose turns overlap, like a drawn spring or inductor."""
    pts, steps = [], turns * 48
    pitch = (x2 - x1 - 2 * radius * 0.6) / turns
    for i in range(steps + 1):
        t = 2 * math.pi * i / 48
        pts.append((x1 + radius * 0.6 + pitch * t / (2 * math.pi) - radius * 0.6 * math.cos(t), y - radius * math.sin(t)))
    return pts


def coil(fig, x1, x2, y, turns=5, radius=17):
    fig.path(spring_points(x1, x2, y, turns, radius))


def mid_arrow(fig, x1, y1, x2, y2, at=0.55, size=15, width=3):
    """A wire from (x1, y1) to (x2, y2) with an arrowhead part-way along it, pointing towards the end."""
    fig.line(x1, y1, x2, y2, width=width)
    fig.arrowhead(x1 + (x2 - x1) * at, y1 + (y2 - y1) * at, math.degrees(math.atan2(y2 - y1, x2 - x1)), size=size)


def slant_resistor(fig, p1, p2, length=70, peaks=4, height=10, at=0.5):
    """A wire from p1 to p2 in any direction with a resistor on it (centred `at` of the way along)."""
    (x1, y1), (x2, y2) = p1, p2
    total = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / total, (y2 - y1) / total
    mx, my = x1 + (x2 - x1) * at, y1 + (y2 - y1) * at
    fig.line(x1, y1, mx - ux * length / 2, my - uy * length / 2)
    fig.line(mx + ux * length / 2, my + uy * length / 2, x2, y2)
    with fig.rotated(round(math.degrees(math.atan2(uy, ux)), 2), round(mx, 1), round(my, 1)):
        fig.resistor(mx - length / 2, mx + length / 2, my, peaks=peaks, height=height)
    return mx, my


def along(p1, p2, t, off=0.0):
    """The point a fraction t of the way from p1 to p2, moved `off` to the left of the direction of travel."""
    (x1, y1), (x2, y2) = p1, p2
    total = math.hypot(x2 - x1, y2 - y1)
    return (x1 + (x2 - x1) * t + (y2 - y1) / total * off, y1 + (y2 - y1) * t - (x2 - x1) / total * off)

