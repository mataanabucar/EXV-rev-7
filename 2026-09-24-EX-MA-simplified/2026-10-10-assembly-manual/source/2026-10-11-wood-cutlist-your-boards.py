#!/usr/bin/env python3
"""EX-MA version B (minimal, no PVC conduit) cut plan for the boards on hand:
    3 x OSB 7/16in, 2 x 4 ft
    1 x particle board 5/8in, 2 x 2 ft  -> the sandbox floor, used uncut

Everything is regenerated with the real thicknesses (build-box.py panels(), version B constants from
2026-10-10-wood-cutlist.py), with no shim under the control box: box and sandbox both stand on the
ground, so the 5/8in floor puts the sandbox floor top 5/32in higher than the design. The pedestal and
sandbox walls are cut that much shorter, which keeps the pedestal top, the turret and both conduit
fittings at their design heights. The printed elbow support (stands on the sandbox floor) loses its
4 mm base plate to match.

Usage: <cadenv>/bin/python 2026-10-11-wood-cutlist-your-boards.py
then:  node 2026-10-10-manual-print.mjs 2026-10-11-wood-cutlist-your-boards.html ../2026-10-11-ex-ma-cut-plan-your-boards.pdf
"""
import copy
import html
import importlib.util
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


wc = _load("wc", HERE / "2026-10-10-wood-cutlist.py")
sv, inch, dims = wc.sv, wc.inch, wc.dims
esc = html.escape
IN = 25.4

T_OSB = 7 / 16 * IN                 # 11.11 mm
T_FLOOR = 5 / 8 * IN                # 15.88 mm particle board
GROUND = -202.0                     # box floor bottom and sandbox floor bottom (no shim)
OSB_SHEET = (48 * IN, 24 * IN)
PB_SHEET = (24 * IN, 24 * IN)
RAISE = T_FLOOR - 12.0              # sandbox floor top vs the design (3.88 mm = 5/32in)


def panels():
    bx = _load("bxY", wc.SRC / "2026-09-24-build-box.py")
    ex = bx.ex
    ex.BOX_U, ex.BOX_V, ex.BOX_Z = (-417.0, -203.0), (-257.0, 105.0), (-202.0, -46.0)
    ex.LEVERS = dict(boom=(60.0, 19.0), stick=(0.0, -17.0), bucket=(-60.0, -32.0))
    ex.LEVER_HUB_V = dict(boom=(10.25, 70.0), stick=(-24.75, 9.75), bucket=(-70.0, -25.25))
    ex.AXLE_BLOCK_V = (70.5, 82.5)
    ex.HANDLE_LEN = 140.0
    ex.WHEEL_C = (-340.0, -180.0)
    ex.PED_U = wc.PED_U_MIN
    ex.T_WOOD = bx.T = T_OSB
    floor_top = GROUND + T_FLOOR
    ex.PED_Z = (floor_top, 0.0)                  # pedestal top stays at z 0
    ex.SB_Z = (floor_top, 40.0)                  # sandbox rim stays at z 40
    bx.BLOCK_U = (ex.AXLE_U - 30.0, ex.AXLE_U + 30.0)
    bx.BLOCK_TOP = ex.AXLE_Z + 30.0
    bx.SHELF_U0 = ex.PED_U[0] + T_OSB + ex.FIT_T + 2.0
    P = bx.panels()
    for p in P:
        if p.name == "sandbox floor":            # the particle-board panel, uncut
            p.lo = (p.lo[0], p.lo[1], GROUND)
            p.hi = (p.lo[0] + PB_SHEET[0], p.lo[1] + PB_SHEET[1], floor_top)
            p.note = "the 5/8in particle board, uncut"
        p.holes = [(k, a, c, d, n.replace("fitting bolt (M3 × 35 through the sandbox wall)", "8-32 through-rod")
                    .replace("fitting bolt (M3 × 25)", "8-32 through-rod")
                    .replace("bolt from the control box", "8-32 through-rod" if abs(c[2] - ex.COND_Z) < 45 else "bolt from the control box"))
                   for k, a, c, d, n in p.holes]
    w = next(p for p in P if p.name.startswith("pedestal wall -u"))
    for k in (1, 2):
        sp = copy.deepcopy(w)
        sp.name, sp.group = f"spacer frame {k}", "spacer"
        u0 = w.lo[0] - k * T_OSB
        sp.lo, sp.hi = (u0, w.lo[1], w.lo[2]), (u0 + T_OSB, w.hi[1], w.hi[2])
        sp.holes = [("rect", "u", (u0, ex.PED_FIT_V, ex.COND_Z), (wc.WINDOW, wc.WINDOW), "window (drill 3/8″ in each corner, then jigsaw)")]
        P.append(sp)
    return P, ex


def ids(P):
    PA, _ = wc.panels_A()
    WA = {p.name: f"W{i + 1:02d}" for i, p in enumerate(PA)}
    return {p.name: WA.get(p.name) or ("W22" if p.name.endswith("1") else "W23") for p in P}


# ---------------------------------------------------------------- derived numbers for the stack
STACK = 5 * T_OSB                                # box front, sandbox wall, 2 spacers, pedestal wall
CHAMBER = 24.0 + STACK                           # + the two 12 mm fitting sockets
ROD = 6 + STACK + 6 + 2 * (3.2 + 2.0)            # flanges + stack + nut and thread each end
CONDUIT_A = 141.0
SHORTER = CONDUIT_A - CHAMBER                    # every rope strand / tube through the conduit


def bow_radius(L, dl=10.5):
    h = math.sqrt(4 * L * dl) / math.pi
    return L * L / (2 * math.pi ** 2 * h)


def elbow_svg():
    """Elbow support side view (print frame, to scale): base plate 44 x 4, post 20 wide to h + 5."""
    h = 57.1
    s = ['<svg viewBox="-62 -14 150 92" width="100%" font-family="Inter">']
    y0 = 70
    s.append(sv.rect(-22, y0 - 4, 44, 4, "#f2a65a", sv.INK, 0.4))
    s.append(sv.rect(-10, y0 - h - 5, 20, h + 1, "#f2a65a", sv.INK, 0.4))
    s.append(f'<circle cx="0" cy="{y0 - h - 7.94:.1f}" r="8.14" fill="#fff" stroke="{sv.INK}" stroke-width="0.4"/>')
    s.append(f'<circle cx="0" cy="{y0 - h - 7.94:.1f}" r="7.94" fill="#c98a55" stroke="{sv.INK}" stroke-width="0.3"/>')
    for x in (-16, 16):
        s.append(sv.rect(x - 1.9, y0 - 4, 3.8, 4, "#fff", sv.INK, 0.25))
    s.append(sv.line(-34, y0 - 4, 40, y0 - 4, sv.ACC, 0.7, dash="2.5,1.5"))
    s.append(sv.t(41, y0 - 3, "saw here", 3.6, "start", 800, sv.ACC))
    s.append(sv.t(41, y0 + 2, "(remove the 5/32″ base plate)", 3.0, "start", 500, sv.INK2))
    s.append(sv.line(-34, y0, 40, y0, sv.INK3, 0.3) + sv.t(-36, y0 + 1, "old floor line", 2.8, "end", 500, sv.INK2))
    s.append(sv.t(0, y0 - h - 18, "1/2″ copper", 3.2, "middle", 600))
    s.append(sv.t(0, y0 + 8, "Elbow support P16, side view, to scale", 3.2, "middle", 600, sv.INK2))
    s.append("</svg>")
    return "".join(s)


def build():
    P, ex = panels()
    W = ids(P)
    osb = [p for p in P if p.name != "sandbox floor"]
    sheets = wc.pack_sheets([(W[p.name], *dims(p)) for p in osb], OSB_SHEET)
    idcol = {W[p.name]: wc.GROUP_COL[p.group] for p in P}
    osb_area = sum(dims(p)[0] * dims(p)[1] for p in osb) / 645.16
    pages = []

    def page(body, tab, right):
        pages.append((body, tab, right))

    R = bow_radius(CHAMBER)
    shift = (81.0 + (12.0 - T_OSB)) - 2 * T_OSB   # pedestal gap in A (with OSB sandbox wall) minus the spacers
    rows = [("8-32 through-rods (4)", inch(ROD)), ("Boom / stick / bucket rope", " / ".join(inch(x - 2 * SHORTER) for x in (1384, 1821, 2173))),
            ("PTFE stick_hi / stick_lo", " / ".join(inch(x - SHORTER) for x in (647, 658))),
            ("PTFE bucket_hi / bucket_lo", " / ".join(inch(x - SHORTER) for x in (813, 822))),
            ("Slew sleeve A / B", " / ".join(inch(x - SHORTER) for x in (330, 397))),
            ("Slew rope A / B", " / ".join(inch(x - SHORTER) for x in (820, 890))),
            ("Lever axle / spool axle / 3 handles (5/16″ rod)", "7-5/16″ / 7-3/8″ / 5-11/16″ each")]
    tr = "".join(f"<tr><td>{a}</td><td class=n><b>{b}</b></td></tr>" for a, b in rows)
    body = f'''<div style="position:absolute;left:0;right:0;top:0;height:0.16in;display:flex">
<span style="flex:1;background:#2e9e44"></span><span style="flex:1;background:#2a6fdb"></span><span style="flex:1;background:#d93a2b"></span><span style="flex:1;background:#8e44ad"></span></div>
<div class="kicker">EX-MA cable excavator · version B (minimal, no PVC conduit)</div><h1>Cut plan for your boards</h1>
<p class="lead">Three 7/16″ OSB panels (2 × 4 ft) and one 5/8″ particle-board panel (2 × 2 ft). Every size below is worked out for
those thicknesses; the box and the sandbox both stand straight on the ground (no shim).</p>
<div class="kpis"><div><b>Particle board</b><span>sandbox floor W17 — use it whole, no cuts</span></div>
<div><b>{len(sheets)} OSB panels</b><span>everything else: {osb_area:.0f} sq in ({osb_area / (len(sheets) * 1152) * 100:.0f} % of the {len(sheets)} panels)</span></div>
<div><b>1 OSB panel spare</b><span>keep it for re-cuts or a lid</span></div></div>
<div class="row"><div class="col">
<h3 class="mt0">What changes because of your boards</h3>
<ul class="tight">
<li><b>7/16″ OSB instead of 12 mm (1/32″ thinner).</b> Outside sizes and every hole position stay as designed; pieces that fit between
others come out up to 1/16″ longer. All sizes in this plan already include that.</li>
<li><b>5/8″ floor, no shim.</b> The sandbox floor top sits 5/32″ higher than the design. The <b>pedestal walls and sandbox walls are
5/32″ shorter</b> to match, so the pedestal top, the turret and both conduit fittings stay at their design heights and still line up
with the control box. Hole heights in those walls are already corrected.</li>
<li><b>Elbow support (printed P16):</b> it stands on the sandbox floor, so it is now 5/32″ too tall. Saw off its 5/32″ base plate flush
with the post (drawing on the right) and fix the post with one #6 × 1-1/4″ screw up through the floor into its centre (1/8″ pilot)
plus a few drops of CA or epoxy. Nothing else printed is affected.</li>
<li><b>Spacer stack</b> is now 5 × 7/16″: the chamber between the fittings is {inch(CHAMBER)} long — the PTFE tubes’ bow needs about
{inch(R)} radius, still above the 5/8″ minimum <span class="tag d">Derived</span>. The arm’s slew axis moves {inch(shift)} toward the box.</li>
</ul></div><div class="col w35">
<div class="figframe" style="padding:4px">{elbow_svg()}</div>
<h3>Lengths for this build <span class="tag d">Derived</span></h3>
<table class="t compact">{tr}</table>
<p class="small">Ropes and tubes are shorter than the manual by the {inch(SHORTER)} the conduit run lost (arm ropes twice). Cut ropes 3/4″
long and trim when you crimp.</p>
</div></div>
<h3>Working with these materials <span class="tag a">Assumption</span></h3>
<div class="row"><div class="col">{wc_box("caut", "Particle board and sand.", " Particle board swells and crumbles if it gets damp. Seal both faces "
     "and all four edges of the floor (paint, poly or a coat of wood glue thinned with water) before assembly, and keep the sand dry.")}</div>
<div class="col">{wc_box("note", "OSB edges.", " Screws hold less well in OSB edges than in plywood. Drill a 3/32″ pilot for every #6 screw, keep "
     "screws 1/2″ from corners, and glue every joint.")}</div></div>'''
    page(body, "Your boards", "Cut plan")

    page('<div class="kicker">Version B · your boards</div><h1>Cut list</h1><p>Sizes for 7/16″ OSB and the 5/8″ particle-board floor. '
         'Tick each piece as you cut it and pencil its ID on it, with an arrow to its <b>bottom</b> edge.</p>'
         + wc.cut_table(P, W), "Your boards", "Cut list")

    lays = []
    for k, st in enumerate(sheets):
        wc.SKIPPED.clear()
        svg_ = wc.sheet_svg(st, OSB_SHEET, idcol, width_in=7.0)
        small = (f'<p class="small">Thin strips not labelled on the drawing: {", ".join(sorted(set(wc.SKIPPED)))} — see the cut order.</p>'
                 if wc.SKIPPED else "")
        lays.append(f'<div class="sheet"><div class="sh">OSB panel {k + 1} — 2 × 4 ft, 7/16″</div>{svg_}{small}{wc.cut_steps(st)}</div>')
    lays[-1] += ('<div class="sheet"><div class="sh">OSB panel 3 — spare</div><p>Not needed. Keep it for a re-cut.</p></div>'
            '<div class="sheet"><div class="sh">Particle board — 2 × 2 ft, 5/8″</div><p><b>W17 sandbox floor:</b> use the whole panel, '
            'no cuts (24″ × 24″; the design is 1/64″ bigger, which does not matter). Seal it before building on it.</p></div>')
    for k, lay in enumerate(lays):
        page('<div class="kicker">Version B · your boards</div><h2>Board layouts and cut order' + (" (continued)" if k else "") + '</h2>'
             + ('<p>Rip the strips first (orange dashed lines, R1, R2 …), then crosscut each strip. Drawn to scale with a 1/8″ kerf; grey is '
                'offcut.</p>' if not k else "") + lay, "Your boards", "Layouts")

    drilled, seen = [], {}
    for p in P:
        if not p.holes:
            continue
        ax = [i for i in range(3) if "uvz"[i] != p.normal]
        key = (dims(p), tuple((k, d if k == "hole" else tuple(d), round(c[ax[0]] - p.lo[ax[0]], 1), round(c[ax[1]] - p.lo[ax[1]], 1))
                              for k, _, c, d, _ in p.holes))
        if key in seen:
            seen[key][1].append(W[p.name])
            continue
        seen[key] = (p, [W[p.name]])
        drilled.append(seen[key])
    cards = []
    for p, wids in drilled:
        c = wc.drill_card(p, " + ".join(wids))
        if len(wids) > 1:
            nm = {"axle bearing block left": "axle bearing blocks", "spacer frame 1": "spacer frames"}.get(p.name, p.name)
            c = c.replace(f"</span> {esc(p.name)}</div>", f"</span> {esc(nm)} <span class=mm>(×{len(wids)}, identical)</span></div>", 1)
        cards.append(c)
    if len(cards) % 4 == 1:                      # a lone last card goes on the last layout page (it has room)
        pages[-1] = (pages[-1][0] + '<h3>Drilling — spacer frames W22 + W23</h3><div class="dgrid">' + cards.pop() + "</div>",
                     *pages[-1][1:])
    for k in range(0, len(cards), 4):
        page(f'<div class="kicker">Version B · your boards</div><h2>Drilling{" (continued)" if k else ""}</h2>'
             + ("" if k else "<p>Measure <b>a</b> along the bottom edge and <b>b</b> up the side, from the lower-left corner as drawn. The bold size "
                "is the drill bit. In OSB, clamp a scrap under the panel so the holes do not tear out.</p>")
             + f'<div class="dgrid">{"".join(cards[k:k + 4])}</div>', "Your boards", "Drilling")

    css = (HERE / "2026-10-10-manual.css").read_text() + wc.CSS_EXTRA
    out = []
    for i, (body, tab, right) in enumerate(pages, start=1):
        head = f'<div class="rhead"><span class="tab st">{esc(tab)}</span><span>{esc(right)}</span></div>' if i > 1 else ""
        foot = f'<div class="rfoot"><span>EX-MA cable excavator · Cut plan for your boards · 2026-10-11</span><span class="pn">{i}</span></div>'
        out.append(f'<section class="page">{head}{body}{foot}</section>')
    (HERE / "2026-10-11-wood-cutlist-your-boards.html").write_text(
        f'<!doctype html><html><head><meta charset="utf-8"><title>EX-MA Cut Plan — Your Boards</title><style>{css}</style></head>'
        f'<body>{"".join(out)}</body></html>')
    print(f"{len(pages)} pages; {len(sheets)} OSB panels; OSB {osb_area:.0f} sq in; chamber {CHAMBER:.1f} mm, R {R:.1f} mm, rod {ROD:.1f} mm, "
          f"shorter by {SHORTER:.1f} mm, shift {shift:.1f} mm")


def wc_box(kind, title, body):
    return f'<div class="box {kind}"><span class="bt">{title}</span>{body}</div>'


if __name__ == "__main__":
    build()
