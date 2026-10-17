"""Physics (MHT-CET 2024-25): electromagnetic induction."""

from figlib import Figure, coil


def wire(f, *points):
    f.polyline(list(points))


def ellipse(f, cx, cy, rx, ry, width=3, dash=None, fill="none"):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    f.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" stroke-width="{width}" fill="{fill}"{extra}/>')


def lines_from_origin(labels, ylabel, origin="", slopes=(2.6, 1.3, 0.8, 0.45)):
    """Straight lines from the origin with the given slopes (steepest first), labelled at their ends."""
    f = Figure(560, 440)
    ox, oy = 70, 380
    f.axes(ox, oy, 440, 340, xlabel="<i>I</i>", ylabel=ylabel, origin=origin, size=36)
    for name, k in zip(labels, slopes):
        length = 360
        dx = length / (1 + k * k) ** 0.5
        x2, y2 = ox + dx, oy - dx * k
        f.line(ox, oy, x2, y2)
        f.text(x2 + 22, y2 + 4, name, size=36)
    return f


def flux_current_pqrs():
    """Flux against current: straight lines from the origin for inductors P (steepest), Q, R and S (least steep)."""
    return lines_from_origin("PQRS", "<i>φ</i>")


def flux_current_abcd():
    """Flux against current: straight lines from the origin for inductors A (steepest), B, C and D (least steep)."""
    return lines_from_origin("ABCD", "<i>Φ</i>", origin="0")


def flux_current_pqrs_origin():
    """Flux against current: straight lines from O for inductors P (steepest), Q, R and S (least steep)."""
    return lines_from_origin("PQRS", "<i>φ</i>", origin="O", slopes=(3.2, 1.4, 0.75, 0.33))


def flux_current_l1_l2():
    """Flux against current: two straight lines from the origin, L1 steeper than L2."""
    return lines_from_origin(("<i>L</i><sub>1</sub>", "<i>L</i><sub>2</sub>"), "<i>φ</i>", origin="0", slopes=(1.7, 0.75))


def coil_and_magnet():
    """A coil (seen edge-on as an ellipse) with the label Coil and an arrow pointing to it; a bar magnet N-S to its right."""
    f = Figure(640, 220)
    ellipse(f, 200, 110, 36, 96)
    f.line(30, 112, 162, 112, arrow=True), f.text(60, 92, "Coil", size=34)
    f.rect(350, 70, 270, 80), f.text(380, 124, "N", size=34), f.text(590, 124, "S", size=34)
    return f


def rlc_two_switches():
    """V cell and R charge capacitor C when S1 is closed; with S1 open and S2 closed, C discharges through inductor L."""
    f = Figure(520, 560)
    l, r, top, mid, bottom = 60, 400, 50, 330, 500
    f.line(l, top, 186, top), f.cell(197, top, gap=22, long=28, short=16), f.line(208, top, r, top)
    f.line(l, top, l, 150), f.vresistor(l, 150, 260), f.line(l, 260, l, bottom)
    f.line(l, mid, 186, mid), f.capacitor(193, mid, gap=14, height=28), f.line(200, mid, r, mid)
    f.line(r, top, r, 170), f.line(r, 170, 432, 240), f.dot(r, 250), f.line(r, 250, r, mid)
    f.line(r, mid, r, 380), f.line(r, 380, 432, 450), f.dot(r, 460), f.line(r, 460, r, bottom)
    f.line(l, bottom, 150, bottom), coil(f, 150, 290, bottom, turns=5, radius=16), f.line(290, bottom, r, bottom)
    f.text(197, 22, "<i>V</i>", size=30), f.text(176, 92, "−", size=28), f.text(222, 92, "+", size=28)
    f.text(28, 214, "<i>R</i>", size=30), f.text(193, 290, "<i>C</i>", size=30), f.text(220, 466, "<i>L</i>", size=30)
    f.text(444, 260, "S<sub>1</sub>", size=30, anchor="start"), f.text(444, 470, "S<sub>2</sub>", size=30, anchor="start")
    return f


def emf_rate_options():
    """Induced emf e against dI/dt: (A)-(C) drawn with e increasing downward - (A) a horizontal line, (B) a line falling from the origin,
    (C) a curve bending away; (D) e upward, a line rising from the origin."""
    f = Figure(640, 560)
    for name, (ox, oy) in zip("ABC", ((60, 50), (380, 50), (60, 320))):
        f.line(ox, oy, ox + 210, oy, arrow=True), f.line(ox, oy, ox, oy + 170, arrow=True)
        f.text(ox - 20, oy + 8, "0", size=26), f.text(ox + 150, oy - 14, "d<i>I</i>/d<i>t</i>", size=26)
        f.text(ox - 18, oy + 80, "<i>e</i>", size=26), f.text(ox + 110, oy + 224, f"({name})", size=28)
    f.line(60, 120, 250, 120)
    f.line(380, 50, 570, 200)
    f.add('<path d="M60,330 Q170,330 200,420" stroke-width="3"/>')
    ox, oy = 380, 480
    f.axes(ox, oy, 210, 170, size=26), f.line(ox, oy, 560, 330)
    f.text(ox - 20, oy + 8, "0", size=26), f.text(ox - 18, oy - 90, "<i>e</i>", size=26), f.text(ox + 110, oy + 34, "d<i>I</i>/d<i>t</i>", size=26)
    f.text(ox + 110, oy + 72, "(D)", size=28)
    return f


def three_inductors_ab():
    """0.7 H and 0.7 H in parallel, in series with 0.85 H, between A and B."""
    f = Figure(700, 240)
    y, l, r = 120, 150, 440
    f.line(30, y, l, y), f.line(l, 50, l, 190), f.line(r, 50, r, 190)
    for yy in (50, 190):
        f.line(l, yy, 240, yy), coil(f, 240, 350, yy, turns=5, radius=13), f.line(350, yy, r, yy)
    f.line(r, y, 500, y), coil(f, 500, 610, y, turns=5, radius=13), f.line(610, y, 680, y)
    f.text(20, 108, "A", size=30), f.text(690, 108, "B", size=30, anchor="end")
    f.text(295, 26, "0.7 H", size=28), f.text(295, 232, "0.7 H", size=28), f.text(555, 168, "0.85 H", size=28)
    return f


def ring_falling_to_wire():
    """A conducting ring falls (arrow downward) towards a long straight wire below it carrying current I to the right."""
    f = Figure(640, 480)
    f.circle(340, 170, 140, width=5)
    f.line(90, 120, 90, 250, width=4, arrow=True)
    f.line(40, 380, 620, 380, width=6), f.arrowhead(220, 380, 0, size=24)
    f.text(200, 450, "<i>I</i>", size=40)
    return f


def magnet_leaving_loop_with_capacitor():
    """A thick conducting loop with a capacitor (plates a and b) in its lower side; the N pole of a bar magnet moves away to the right along the loop's axis."""
    f = Figure(700, 420)
    ellipse(f, 200, 200, 110, 160, width=3), ellipse(f, 200, 200, 96, 146, width=3)
    f.add('<rect x="170" y="330" width="60" height="50" fill="#fff" stroke="none"/>')
    for x in (184, 216):
        f.line(x, 340, x, 400, width=4)
    wire(f, (184, 346), (178, 346)), wire(f, (216, 346), (222, 346))
    f.line(20, 200, 520, 200, width=2, dash="12 8")
    f.rect(520, 176, 160, 48), f.rect(520, 176, 80, 48, fill="#1f2937")
    f.text(540, 160, "N", size=30), f.text(668, 160, "S", size=30)
    f.line(560, 260, 640, 260, arrow=True)
    f.text(184, 412, "a", size=28, anchor="end"), f.text(222, 412, "b", size=28, anchor="start")
    f.add('<path d="M380,50 Q330,50 300,80" stroke-width="3"/>'), f.arrowhead(298, 84, 130, size=16)
    f.text(390, 60, "Loop", size=32, anchor="start")
    return f


def inductors_2_3_4_6():
    """A to B: 2 H, then 4 H, then 6 H in a row; a wire above joins the node before 2 H to the node after 4 H, with 3 H from it down to the node between 2 H and 4 H;
    a wire below joins the node between 2 H and 4 H to the node after 6 H."""
    f = Figure(720, 300)
    y, top, bottom = 160, 50, 260
    n1, n2, n3, n4 = 100, 280, 460, 640
    f.terminal(30, y), f.line(36, y, n1, y)
    f.line(n1, y, 140, y), coil(f, 140, 240, y, turns=5, radius=12), f.line(240, y, n2, y)
    f.line(n2, y, 320, y), coil(f, 320, 420, y, turns=5, radius=12), f.line(420, y, n3, y)
    f.line(n3, y, 500, y), coil(f, 500, 600, y, turns=5, radius=12), f.line(600, y, n4, y)
    f.line(n4, y, 684, y), f.terminal(690, y)
    wire(f, (n1, y), (n1, top), (n3, top), (n3, y))
    f.line(n2, top, n2, 70)
    with f.rotated(90, n2, 100):
        coil(f, n2 - 30, n2 + 30, 100, turns=4, radius=11)
    f.line(n2, 130, n2, y)
    wire(f, (n2, y), (n2, bottom), (n4, bottom), (n4, y))
    for x in (n1, n2, n3, n4):
        f.dot(x, y, r=4)
    f.text(20, 148, "A", size=28, anchor="end"), f.text(704, 148, "B", size=28, anchor="start")
    f.text(190, 136, "2 H", size=26), f.text(370, 136, "4 H", size=26), f.text(550, 136, "6 H", size=26)
    f.text(n2 - 20, 110, "3 H", size=26, anchor="end")
    return f


def magnet_through_cut_ring():
    """A bar magnet (S above N) falls along the axis of a horizontal copper ring."""
    f = Figure(560, 420)
    f.rect(220, 20, 70, 120), f.text(255, 70, "S", size=32), f.text(255, 116, "N", size=32)
    f.text(320, 90, "Magnet", size=32, anchor="start")
    f.line(255, 140, 255, 330, arrow=True)
    ellipse(f, 270, 340, 140, 52, width=6)
    f.line(80, 330, 120, 330, arrow=True), f.text(20, 340, "Ring", size=32, anchor="start")
    return f


def loop_falling_in_field():
    """A long rectangular loop of width l partly inside a magnetic field into the page (crosses); it moves down with velocity V."""
    f = Figure(520, 540)
    f.rect(110, 110, 210, 340)
    for x in (100, 180, 260, 340):
        f.text(x, 60, "×", size=44)
    for y in (160, 230, 300, 370):
        for x in (50, 160, 270, 380):
            f.text(x, y + 14, "×", size=44)
    f.dim(120, 490, 310, 490), f.text(215, 530, "<i>l</i>", size=34)
    f.line(450, 160, 450, 280, width=4, arrow=True), f.line(430, 300, 470, 300, width=2), f.text(450, 340, "<i>V</i>", size=34)
    return f


FIGURES = {
    "PYQ-PHY-cb8aedccbcd8": flux_current_pqrs,
    "PYQ-PHY-551534ecc528": coil_and_magnet,
    "PYQ-PHY-1cdd8a03124c": flux_current_abcd,
    "PYQ-PHY-e3bd38039dc7": rlc_two_switches,
    "PYQ-PHY-10b77802f35e": emf_rate_options,
    "PYQ-PHY-f0e0239db2b3": three_inductors_ab,
    "PYQ-PHY-a0d43054db70": ring_falling_to_wire,
    "PYQ-PHY-b6933710dad5": flux_current_pqrs_origin,
    "PYQ-PHY-a70f912937b4": magnet_leaving_loop_with_capacitor,
    "PYQ-PHY-d0c052730cdd": inductors_2_3_4_6,
    "PYQ-PHY-3779057f4cf0": magnet_through_cut_ring,
    "PYQ-PHY-834364b93643": flux_current_l1_l2,
    "PYQ-PHY-c696ad9f3a94": loop_falling_in_field,
}
