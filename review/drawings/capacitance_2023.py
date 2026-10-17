"""Physics (MHT-CET 2020-23): capacitance - networks and dielectric-filled capacitors."""

from figlib import Figure


def wire(f, *points):
    f.polyline(list(points))


_clip = [0]


def hatch_rect(f, x, y, w, h, kind="diagonal", spacing=12, dash=None):
    """A rectangle filled with diagonal, horizontal or vertical lines (a dielectric)."""
    _clip[0] += 1
    cid = f"cap23_{_clip[0]}"
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    if kind == "horizontal":
        lines = [(x, y + i, x + w, y + i) for i in range(spacing, int(h), spacing)]
    elif kind == "vertical":
        lines = [(x + i, y, x + i, y + h) for i in range(spacing, int(w), spacing)]
    else:
        lines = [(x + i, y + h, x + i + h, y) for i in range(-int(h), int(w), spacing)]
    body = "".join(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" stroke-width="1.5"{extra}/>' for a, b, c, d in lines)
    f.add(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath><g clip-path="url(#{cid})">{body}</g>')


def tag(f, x, y, content, size=32, w=None):
    """A label on a white patch, for text that sits on hatching (y is the baseline)."""
    w = w or size * 3.2
    f.add(f'<rect x="{x - w / 2:.1f}" y="{y - size * 0.95:.1f}" width="{w:.1f}" height="{size * 1.3:.1f}" fill="#fff" stroke="none"/>')
    f.text(x, y, content, size=size)


def hcap(f, x1, x2, y, label="", dy=-30, size=28, height=22):
    """A wire from x1 to x2 with a capacitor in the middle."""
    m = (x1 + x2) / 2
    f.line(x1, y, m - 7, y), f.capacitor(m, y, gap=14, height=height), f.line(m + 7, y, x2, y)
    if label:
        f.text(m, y + dy, label, size=size)


def vcap(f, x, y1, y2, label="", dx=34, size=28, half=26, anchor="start"):
    """A vertical wire from y1 to y2 with a capacitor in the middle."""
    m = (y1 + y2) / 2
    f.line(x, y1, x, m - 7), f.vcapacitor(x, m, gap=14, half=half), f.line(x, m + 7, x, y2)
    if label:
        f.text(x + dx, m + 10, label, size=size, anchor=anchor)


def five_in_series_meander():
    """Five capacitors C in series between A and B, wound in a loop: down the left side, along the bottom, up and across a middle step,
    down and along the bottom again, and up the right side to B."""
    f = Figure(660, 320)
    t, b, l, r = 50, 250, 50, 590
    f.dot(260, t, r=7), f.dot(380, t, r=7), f.text(260, 30, "A", size=32), f.text(380, 30, "B", size=32)
    f.text(260, 86, "+", size=26), f.text(380, 86, "−", size=26)
    wire(f, (260, t), (l, t)), vcap(f, l, t, b, "<i>C</i>", dx=-34, anchor="end")
    hcap(f, l, 240, b, "<i>C</i>", dy=52), wire(f, (240, b), (240, 150))
    hcap(f, 240, 400, 150, "<i>C</i>", dy=52), wire(f, (400, 150), (400, b))
    hcap(f, 400, r, b, "<i>C</i>", dy=52), vcap(f, r, b, t, "<i>C</i>", dx=34), wire(f, (r, t), (380, t))
    return f


def four_caps_ab():
    """A and B on the top wire; C1 from B's side down to the middle wire; C2 and C3 on the middle wire, C4 on the bottom wire, between the two side rails."""
    f = Figure(640, 340)
    l, r, t, m, b = 20, 620, 30, 160, 290
    f.dot(150, t, r=8), f.dot(195, t, r=8), f.text(150, 72, "A", size=30), f.text(195, 72, "B", size=30)
    wire(f, (150, t), (l, t), (l, b)), wire(f, (195, t), (r, t), (r, b))
    vcap(f, 330, t, m, "C<sub>1</sub>")
    hcap(f, l, 330, m, "C<sub>2</sub>", dy=60), hcap(f, 330, r, m, "C<sub>3</sub>", dy=60)
    hcap(f, l, r, b, "C<sub>4</sub>", dy=-40)
    return f


def ladder_2c_c():
    """Between rails A (top) and B (bottom): 2C from A to B on the left; on the right, 2C, 2C and C in series down to B,
    with C from the first junction to B and C from the second junction to B."""
    f = Figure(640, 340)
    l, rx, t, b = 60, 560, 30, 310
    f.circle(40, t, 7, fill="#fff"), f.circle(40, b, 7, fill="#fff"), f.text(20, t + 10, "A", size=30), f.text(20, b + 10, "B", size=30)
    f.line(47, t, rx, t), f.line(47, b, rx, b)
    vcap(f, 175, t, b, "2<i>C</i>", dx=-34, anchor="end")
    n1, n2 = 130, 210
    vcap(f, rx, t, n1, "2<i>C</i>"), vcap(f, rx, n1, n2, "2<i>C</i>"), vcap(f, rx, n2, b, "<i>C</i>")
    wire(f, (rx, n1), (305, n1)), vcap(f, 305, n1, b, "<i>C</i>", dx=-34, anchor="end")
    wire(f, (rx, n2), (410, n2)), vcap(f, 410, n2, b, "<i>C</i>", dx=-34, anchor="end")
    return f


def caps_6_8_4_ground():
    """A at 900 V, C1 = 6 uF to P, then C2 = 8 uF in parallel with C3 = 4 uF to B, which is earthed."""
    f = Figure(680, 300)
    y = 130
    f.circle(30, y, 9, fill="#fff"), hcap(f, 39, 290, y, "6 μF", dy=-40, height=30), f.text(165, y + 64, "C<sub>1</sub>", size=28)
    f.dot(290, y, r=9), f.text(290, y + 44, "P", size=30)
    f.line(290, y, 400, y), f.line(400, 60, 400, 200), f.line(590, 60, 590, 200)
    hcap(f, 400, 590, 60, "8 μF", dy=-30), hcap(f, 400, 590, 200, "", dy=0)
    f.text(495, 110, "C<sub>2</sub>", size=26), f.text(495, 170, "C<sub>3</sub>", size=26), f.text(495, 260, "4 μF", size=28)
    f.line(590, y, 640, y), f.dot(640, y, r=9), f.text(660, y - 12, "B", size=30, anchor="start")
    f.line(640, y, 640, 220), f.ground(640, 220)
    f.text(30, y - 22, "A", size=30), f.text(40, y + 50, "900 V", size=28)
    return f


def three_slabs_series():
    """Parallel plates joined to X and Y; the gap holds three slabs side by side across it: k1 (thickness t1), k2 (t2), k3 (t3)."""
    f = Figure(520, 420)
    xs = (110, 210, 310, 430)
    for x in xs:
        f.line(x, 70, x, 400, width=2.5)
    f.line(30, 220, xs[0], 220), f.line(xs[-1], 220, 500, 220)
    f.text(20, 232, "X", size=34), f.text(504, 232, "Y", size=34, anchor="start")
    for i, (a, b) in enumerate(zip(xs, xs[1:])):
        f.dim(a + 2, 40, b - 2, 40)
        f.text((a + b) / 2, 30, f"<i>t</i><sub>{i + 1}</sub>", size=30, halo=True)
        f.text((a + b) / 2, 250, f"<i>k</i><sub>{i + 1}</sub>", size=34)
    return f


def two_pairs_15v():
    """A to B: two 5 uF capacitors in parallel; B to the far side: two more 5 uF in parallel, joined back to A over the top; a 15 V cell joins A and B underneath."""
    f = Figure(640, 370)
    a, bx, r = 50, 300, 600
    t, y1, mid, y2, bot = 30, 90, 150, 210, 300
    f.line(a, t, a, bot), f.line(a, t, r, t), f.line(r, t, r, mid)
    f.line(100, y1, 100, y2), f.line(a, mid, 100, mid), f.line(240, y1, 240, y2), f.line(240, mid, 330, mid)
    hcap(f, 100, 240, y1, "5 μF", dy=-36), hcap(f, 100, 240, y2, "5 μF", dy=48)
    f.line(330, y1, 330, y2), f.line(530, y1, 530, y2), f.line(530, mid, r, mid)
    hcap(f, 330, 530, y1, "5 μF", dy=-36), hcap(f, 330, 530, y2, "5 μF", dy=48)
    f.line(a, bot, 250, bot), f.cell(261, bot, gap=18, long=24, short=14), f.line(272, bot, bx, bot), f.line(bx, mid, bx, bot)
    f.dot(bx, mid, r=6)
    f.text(30, mid + 10, "A", size=32), f.text(bx + 4, mid - 12, "B", size=32, halo=True), f.text(261, 350, "15 V", size=30)
    return f


def two_layer_dielectric():
    """Plates A (top) and B (bottom) a distance d apart: the upper layer, thickness d/4, holds dielectric K1 (vertical lines);
    the lower layer, thickness 3d/4, holds K2 (dashed horizontal lines)."""
    f = Figure(480, 460)
    l, r, t, m, b = 120, 440, 60, 140, 380
    f.line(l, t, r, t, width=4), f.line(l, b, r, b, width=4)
    f.line(280, 20, 280, t, width=3), f.line(280, b, 280, 430, width=3)
    hatch_rect(f, l, t, r - l, m - t, "vertical", spacing=14, dash="8 6"), f.line(l, m, r, m, width=2)
    hatch_rect(f, l, m, r - l, b - m, "horizontal", spacing=26, dash="18 8")
    f.dim(70, t + 2, 70, m - 2), f.dim(70, m + 2, 70, b - 2)
    f.fraction(40, 92, "<i>d</i>", "4", size=26), f.fraction(40, 250, "3<i>d</i>", "4", size=26)
    f.text(300, 30, "A", size=30, anchor="start"), f.text(300, 450, "B", size=30, anchor="start")
    return f


def six_caps_c1_c6():
    """A - C1 (8 uF) - node; from the node C2 (8 uF) on to a pair C5 (4 uF) and C6 (4 uF) in parallel, which return to B;
    from the node C3 (8 uF) and C4 (8 uF) in series down to B."""
    f = Figure(700, 420)
    a, n, y = 40, 180, 70
    f.dot(a, y, r=8), f.text(20, y + 10, "A", size=30), hcap(f, a, n, y, "C<sub>1</sub> = 8 μF", dy=-30, size=26)
    f.dot(n, y, r=7), hcap(f, n, 400, y, "C<sub>2</sub> = 8 μF", dy=-30, size=26)
    f.line(400, y, 520, y), vcap(f, 400, y, 210, "C<sub>5</sub> = 4 μF", dx=-36, size=26, anchor="end")
    vcap(f, 520, y, 210, "C<sub>6</sub> = 4 μF", dx=36, size=26), f.line(400, 210, 520, 210)
    vcap(f, n, y, 220, "C<sub>3</sub> = 8 μF", dx=-36, size=26, anchor="end"), vcap(f, n, 220, 370, "C<sub>4</sub> = 8 μF", dx=-36, size=26, anchor="end")
    wire(f, (520, 210), (520, 370)), f.line(n, 370, 650, 370), f.dot(650, 370, r=8), f.text(650, 408, "B", size=30)
    return f


def four_c_loop():
    """From A, three capacitors C in series to a node joined to B; a wire from A also loops over the top and returns through a fourth C to that node."""
    f = Figure(700, 280)
    y, top, bot = 140, 40, 230
    f.dot(30, y, r=9), f.text(20, y - 20, "A", size=32)
    f.line(30, y, 90, y), wire(f, (90, y), (90, top), (660, top), (660, y))
    hcap(f, 90, 230, y, "<i>C</i>", dy=-40), hcap(f, 230, 370, y, "<i>C</i>", dy=-40), hcap(f, 370, 520, y, "<i>C</i>", dy=-40)
    hcap(f, 520, 660, y, "<i>C</i>", dy=-40), f.dot(520, y, r=8)
    f.dot(30, bot, r=9), f.text(20, bot - 20, "B", size=32), wire(f, (30, bot), (520, bot), (520, y))
    return f


def crossed_box_and_ladder():
    """A box of three capacitors C (top edge, bottom edge, and one on the diagonal) between A and the next node;
    then C from that node to N2; C from N2 to N3 and C from N3 to B, with N1 tied to N3 over the top and N2 tied to B underneath."""
    f = Figure(800, 320)
    y, bt, bb, bl, br = 160, 70, 250, 120, 280
    f.circle(56, y, 8, fill="#fff"), f.text(20, y + 10, "A", size=32), f.line(64, y, bl, y)
    f.line(bl, bt, bl, bb), f.line(br, bt, br, bb)
    hcap(f, bl, br, bt, "<i>C</i>", dy=-32), hcap(f, bl, br, bb, "<i>C</i>", dy=44)
    f.line(bl, bt, 194, y - 6), f.line(206, y + 6, br, bb)
    with f.rotated(45, 200, y):
        f.capacitor(200, y, gap=14, height=22)
    f.text(236, y - 12, "<i>C</i>", size=28)
    n1, n2, n3, b = 330, 460, 600, 720
    f.line(br, y, n1, y), hcap(f, n1, n2, y, "<i>C</i>", dy=-30), hcap(f, n2, n3, y, "<i>C</i>", dy=48), hcap(f, n3, b, y, "<i>C</i>", dy=48)
    wire(f, (n1, y), (n1, 90), (n3, 90), (n3, y)), wire(f, (n2, y), (n2, 240), (690, 240), (690, y))
    f.line(b, y, 742, y), f.circle(750, y, 8, fill="#fff"), f.text(764, y + 10, "B", size=32, anchor="start")
    return f


def two_caps_and_battery():
    """Between a top and a bottom rail: a capacitor C/2, a capacitor C and a battery V, side by side."""
    f = Figure(680, 360)
    t, b = 30, 320
    f.line(120, t, 600, t, width=3), f.line(120, b, 600, b, width=3)
    vcap(f, 120, t, b, "", half=40), vcap(f, 360, t, b, "", half=40)
    f.line(600, t, 600, 165), f.vcell(600, 175, gap=20, long=40, short=22), f.line(600, 185, 600, b)
    f.fraction(40, 160, "<i>C</i>", "2", size=40), f.text(310, 150, "<i>C</i>", size=44), f.text(620, 120, "<i>V</i>", size=44, anchor="start")
    return f


def two_halves_k1_k2():
    """A capacitor's plate area split into two equal halves (dashed line), filled with K1 and K2."""
    f = Figure(640, 300)
    f.rect(20, 60, 600, 190, width=4)
    f.line(320, 10, 320, 290, width=3, dash="16 10")
    f.text(170, 172, "<i>K</i><sub>1</sub>", size=50), f.text(470, 172, "<i>K</i><sub>2</sub>", size=50)
    return f


def half_filled_medium():
    """Two horizontal plates with a lead through the middle; the left half of the gap is air, the right half a dielectric medium."""
    f = Figure(600, 360)
    t, b = 110, 230
    f.line(20, t, 580, t, width=3), f.line(20, b, 580, b, width=3)
    f.line(290, 20, 290, 340, width=3)
    hatch_rect(f, 290, t, 290, b - t, "diagonal", spacing=16)
    f.text(140, 184, "Air", size=40), tag(f, 440, 184, "Medium", size=40, w=170)
    return f


FIGURES = {
    "PYQ-PHY-d5775a2d9359": five_in_series_meander,
    "PYQ-PHY-cd0cb17dc6d5": four_caps_ab,
    "PYQ-PHY-eab688ab96b1": ladder_2c_c,
    "PYQ-PHY-264da6554b1a": caps_6_8_4_ground,
    "PYQ-PHY-6d6d73112c9d": three_slabs_series,
    "PYQ-PHY-9f7d2aa16aa2": two_pairs_15v,
    "PYQ-PHY-e1d3c23bf744": two_layer_dielectric,
    "PYQ-PHY-ced12b318da3": six_caps_c1_c6,
    "PYQ-PHY-e399012b82a2": four_c_loop,
    "PYQ-PHY-8c0c75a43189": crossed_box_and_ladder,
    "PYQ-PHY-3023b0bd61e1": two_caps_and_battery,
    "PYQ-PHY-3afa7448573a": two_halves_k1_k2,
    "PYQ-PHY-ae1257b17658": half_filled_medium,
}
