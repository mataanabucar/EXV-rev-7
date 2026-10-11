#!/usr/bin/env python3
"""EX-MA wood cut list (PDF source): every plywood piece, sheet layouts and drilling, for

  A  the design in the assembly manual (Source/2026-09-24-build-box.py panels(), as modelled)
  B  a minimal version without the 2in PVC conduit:
       - control box per 2026-09-28-compact-control-box-spec.md (214 x 362 x 156)
       - pedestal +u side 12 mm shorter (drum to wall 9.3 mm, as on the +-v sides)
       - pedestal pushed 57 mm toward the box; a 24 mm plywood spacer frame (2 layers, 100 x 100
         window) between the sandbox -u wall and the pedestal -u wall replaces the conduit: the
         84 mm chamber between the two fittings stores the PTFE tubes' spare length
       - 4 x 8-32 rods through fitting / box front / sandbox wall / spacers / pedestal wall / fitting
     The sandbox keeps its size; only the bolt holes in its -u wall change.

Panels for both versions come from build-box.py panels() (B with the compact constants patched in),
so sizes and hole positions follow the same code as the CAD.

Usage: <cadenv>/bin/python 2026-10-10-wood-cutlist.py   -> source/2026-10-10-wood-cutlist.html
then:  node 2026-10-10-manual-print.mjs 2026-10-10-wood-cutlist.html ../2026-10-10-ex-ma-wood-cut-list.pdf
"""
import copy
import html
import importlib.util
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "Source"

KERF = 3.2                                   # 1/8in saw kerf between pieces
SHEET_4x8 = (2438.4, 1219.2)
IN = 25.4


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


sv = _load("msvg", HERE / "2026-10-10-manual-svg.py")
esc = html.escape

# ================================================================ panels
def panels_A():
    bx = _load("bxA", SRC / "2026-09-24-build-box.py")
    return bx.panels(), bx


SPACER_T = 24.0                              # two 12 mm layers
PED_SHIFT = 81.0 - SPACER_T                  # pedestal moves this far toward the box
PED_U_MIN = (-110.0, 78.0)                   # +u wall inner face at 66: drum (r 56.7) clearance 9.3
WINDOW = 100.0                               # spacer window (fitting bolts at +-40 sit inside it)


def panels_B():
    bx = _load("bxB", SRC / "2026-09-24-build-box.py")
    ex = bx.ex
    # compact control box (2026-09-28-compact-control-box-spec.md, "New layout values")
    ex.BOX_U, ex.BOX_V, ex.BOX_Z = (-417.0, -203.0), (-257.0, 105.0), (-202.0, -46.0)
    ex.LEVERS = dict(boom=(60.0, 19.0), stick=(0.0, -17.0), bucket=(-60.0, -32.0))
    ex.LEVER_HUB_V = dict(boom=(10.25, 70.0), stick=(-24.75, 9.75), bucket=(-70.0, -25.25))
    ex.AXLE_BLOCK_V = (70.5, 82.5)
    ex.HANDLE_LEN = 140.0
    ex.WHEEL_C = (-340.0, -180.0)
    # minimal pedestal (sandbox panels are relative to their own corners, so the 57 mm shift of the
    # pedestal inside the sandbox does not change any panel)
    ex.PED_U = PED_U_MIN
    bx.BLOCK_U = (ex.AXLE_U - 30.0, ex.AXLE_U + 30.0)
    bx.BLOCK_TOP = ex.AXLE_Z + 30.0
    bx.SHELF_U0 = ex.PED_U[0] + bx.T + ex.FIT_T + 2.0
    P = bx.panels()
    for p in P:                                # fitting holes now carry the 8-32 through-rods
        p.holes = [(k, a, c, d, n.replace("fitting bolt (M3 × 35 through the sandbox wall)", "8-32 through-rod")
                    .replace("fitting bolt (M3 × 25)", "8-32 through-rod")
                    .replace("bolt from the control box", "8-32 through-rod" if abs(c[2] - ex.COND_Z) < 45 else "bolt from the control box"))
                   for k, a, c, d, n in p.holes]
    # spacer frames: same outline as the pedestal -u wall, 100 x 100 window on the conduit axis
    w = next(p for p in P if p.name.startswith("pedestal wall -u"))
    for k in (1, 2):
        sp = copy.deepcopy(w)
        sp.name = f"spacer frame {k}"
        sp.group = "spacer"
        u0 = w.lo[0] - SPACER_T + (k - 1) * 12.0
        sp.lo, sp.hi = (u0, w.lo[1], w.lo[2]), (u0 + 12.0, w.hi[1], w.hi[2])
        sp.holes = [("rect", "u", (u0, ex.PED_FIT_V, ex.COND_Z), (WINDOW, WINDOW), "window (drill 3/8″ in each corner, then jigsaw)")]
        sp.note = "glued to the pedestal wall −u; silicone against the sandbox wall"
        P.append(sp)
    return P, bx


GROUP_COL = {"control-box": "#d9b783", "pedestal": "#e8d3a8", "sandbox": "#f3e6c8", "spacer": "#f2a65a"}
GROUP_NAME = {"control-box": "Control box", "pedestal": "Pedestal", "sandbox": "Sandbox", "spacer": "Spacer (B)"}


def ids(P_A, P_B):
    """Same W numbers as the manual for the same panels; spacers are W22 / W23."""
    WA = {p.name: f"W{i + 1:02d}" for i, p in enumerate(P_A)}
    WB = {}
    for p in P_B:
        WB[p.name] = WA.get(p.name) or ("W22" if p.name.endswith("1") else "W23")
    return WA, WB


def dims(p):
    d = sorted(p.size, reverse=True)
    return d[0], d[1]


# ================================================================ inches
def inch(mm):
    n = round(mm / IN * 16)
    w, f = divmod(n, 16)
    if f == 0:
        return f"{w}″"
    g = math.gcd(f, 16)
    fr = f"{f // g}/{16 // g}"
    return f"{w} {fr}″" if w else f"{fr}″"


BITS = {62.0: "2-7/16″ hole saw", 30.4: "1-1/4″ spade / Forstner", 26.2: "1″ spade / Forstner", 24.4: "1″ spade / Forstner",
        22.0: "7/8″ Forstner", 8.5: "11/32″", 4.6: "3/16″", 3.0: "1/8″", 9.0: "23/64″ (or 3/8″)"}


def bit(d):
    return BITS.get(round(d, 1), inch(d))


def mm(x):
    return f'<span class="mm">{x:.0f} mm</span>'


# ================================================================ guillotine strip nesting
def nest(pieces, sheet=SHEET_4x8, kerf=KERF):
    """pieces: list of (id, L, W). Rip strips along the sheet length, crosscut each strip into
    columns, stack narrow pieces side by side across a column. Returns strips:
    [dict(width, cols=[dict(length, items=[(id, L, W, rotated)])])]."""
    SL, SW = sheet
    todo = sorted(pieces, key=lambda p: (-min(p[1], p[2]), -max(p[1], p[2])))
    strips = []
    used_w = 0.0
    while todo:
        first = todo[0]
        w = min(first[1], first[2])
        if used_w + w > SW + 0.01:
            break
        strip = dict(width=w, cols=[])
        rest_l = SL
        changed = True
        while changed:
            changed = False
            for p in list(todo):
                a, b = max(p[1], p[2]), min(p[1], p[2])
                # orientation: long side along the strip if the short side fits across
                for L, W in ((a, b), (b, a)):
                    if W <= w + 0.01 and L + (kerf if strip["cols"] else 0) <= rest_l + 0.01:
                        col = dict(length=L, items=[(p[0], L, W)], used=W)
                        # stack more pieces across the column if they fit
                        for q in list(todo):
                            if q is p:
                                continue
                            qa, qb = max(q[1], q[2]), min(q[1], q[2])
                            for qL, qW in ((qa, qb), (qb, qa)):
                                if qL <= L + 0.01 and col["used"] + kerf + qW <= w + 0.01:
                                    col["items"].append((q[0], qL, qW))
                                    col["used"] += kerf + qW
                                    todo.remove(q)
                                    break
                        strip["cols"].append(col)
                        rest_l -= L + (kerf if len(strip["cols"]) > 1 else 0)
                        todo.remove(p)
                        changed = True
                        break
                if changed:
                    break
        strips.append(strip)
        used_w += w + kerf
    return strips, todo


def pack_sheets(pieces, sheet=SHEET_4x8):
    sheets, todo = [], list(pieces)
    while todo:
        strips, todo = nest(todo, sheet)
        sheets.append(strips)
    return sheets


# ================================================================ drawings
SKIPPED = []


def sheet_svg(strips, sheet, idcol, width_in=7.3):
    SL, SW = sheet
    sc = width_in * 96 / SL                     # px per mm
    W, H = SL * sc, SW * sc
    s = [f'<svg viewBox="-28 -22 {W + 40:.1f} {H + 44:.1f}" width="{width_in + 40 / 96:.2f}in" font-family="Inter">']
    s.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="#eceff2" stroke="#1d232b" stroke-width="1.2"/>')
    s.append(f'<path d="M0,0 L{W:.1f},{H:.1f} M0,{H:.1f} L{W:.1f},0" stroke="#d5dae0" stroke-width="0.6"/>')
    y = 0.0
    for si, st in enumerate(strips):
        x = 0.0
        for col in st["cols"]:
            yy = y
            for pid, L, Wd in col["items"]:
                c = idcol[pid]
                s.append(f'<rect x="{x * sc:.1f}" y="{yy * sc:.1f}" width="{L * sc:.1f}" height="{Wd * sc:.1f}" fill="{c}" stroke="#1d232b" stroke-width="0.8"/>')
                cx, cy = (x + L / 2) * sc, (yy + Wd / 2) * sc
                if Wd * sc > 15 and L * sc > 34:
                    s.append(f'<text x="{cx:.1f}" y="{cy - (2 if Wd * sc > 26 else -3):.1f}" text-anchor="middle" font-size="9" font-weight="800" font-family="Barlow">{pid}</text>')
                    if Wd * sc > 26:
                        s.append(f'<text x="{cx:.1f}" y="{cy + 9:.1f}" text-anchor="middle" font-size="7" fill="#4a5562">{inch(L)} × {inch(Wd)}</text>')
                elif Wd * sc >= 8 and L * sc >= 16:
                    s.append(f'<text x="{cx:.1f}" y="{yy * sc + Wd * sc / 2 + 2.5:.1f}" text-anchor="middle" font-size="6.5" font-weight="800" font-family="Barlow">{pid}</text>')
                else:
                    SKIPPED.append(pid)
                yy += Wd + KERF
            x += col["length"] + KERF
        # rip line + label
        y2 = y + st["width"]
        s.append(f'<text x="-4" y="{(y + y2) / 2 * sc + 3:.1f}" text-anchor="end" font-size="8" font-weight="700" fill="#e8590c" font-family="Barlow">R{si + 1}</text>')
        if y2 + KERF < SW:
            s.append(f'<line x1="-6" y1="{(y2 + KERF / 2) * sc:.1f}" x2="{W + 6:.1f}" y2="{(y2 + KERF / 2) * sc:.1f}" stroke="#e8590c" stroke-width="0.9" stroke-dasharray="4,3"/>')
        y = y2 + KERF
    s.append(f'<text x="{W / 2:.1f}" y="-8" text-anchor="middle" font-size="9" font-weight="700" fill="#4a5562">{inch(SL)}</text>')
    s.append(f'<text x="{W + 8:.1f}" y="{H / 2:.1f}" font-size="9" font-weight="700" fill="#4a5562" transform="rotate(90 {W + 8:.1f} {H / 2:.1f})" text-anchor="middle">{inch(SW)}</text>')
    s.append("</svg>")
    return "".join(s)


def cut_steps(strips):
    out = []
    for si, st in enumerate(strips):
        cols = []
        for col in st["cols"]:
            items = " + ".join(f"<b>{p}</b>" for p, _, _ in col["items"])
            extra = ""
            if len(col["items"]) > 1:
                extra = " (rip that piece into " + " / ".join(inch(w_) for _, _, w_ in col["items"]) + ")"
            cols.append(f"{inch(col['length'])} → {items}{extra}")
        out.append(f'<li><b>R{si + 1}</b>: rip a strip <b>{inch(st["width"])}</b> wide; crosscut: {"; ".join(cols)}.</li>')
    return '<ol class="cuts">' + "".join(out) + "</ol>"


SEEN = {"u": "seen from the +u side", "v": "seen from the −v side", "z": "seen from above"}
EDGE = {"u": "the −u edge", "v": "the −v (right) edge", "z": "the bottom edge"}


def drill_card(p, wid):
    ax = [i for i in range(3) if "uvz"[i] != p.normal]
    A, B = p.size[ax[0]], p.size[ax[1]]
    width_mm, max_h = 84.0, 30.0
    sc = min((width_mm - 26) / A, (max_h - 10) / B)
    w, h = A * sc, B * sc
    ox, oy = 15, 3
    s = [f'<svg viewBox="0 0 {width_mm} {h + 8:.1f}" width="100%">', sv.rect(ox, oy, w, h, "#ead6ad", sv.INK, 0.3)]
    rows = []
    for k, (kind, axis, ctr, d, note) in enumerate(p.holes):
        a, b = ctr[ax[0]] - p.lo[ax[0]], ctr[ax[1]] - p.lo[ax[1]]
        x, y = ox + a * sc, oy + h - b * sc
        L = chr(65 + k)
        if kind == "hole":
            s.append(sv.circ(x, y, max(d / 2 * sc, 0.55), "#fff", sv.INK, 0.25))
            size = f"<b>{bit(d)}</b> <span class=mm>Ø{d:.1f} mm</span>"
            pos = f"{a:.0f} / {b:.0f}", f"{inch(a)} / {inch(b)}"
            r_ = d / 2 * sc
        elif kind == "slot":
            ln, wd = d
            s.append(sv.rect(x - ln / 2 * sc, y - wd / 2 * sc, ln * sc, wd * sc, "#fff", sv.INK, 0.25, wd / 2 * sc))
            e = (ln - wd) / 2
            size = (f"<b>slot {inch(ln)}</b>: {bit(wd).split(' ')[0]} holes at a {inch(a - e)} &amp; {inch(a + e)}, saw between "
                    f"<span class=mm>{ln:.1f} mm</span>")
            pos = f"{a:.0f} / {b:.0f}", f"{inch(a)} / {inch(b)}"
            r_ = 0.8
        else:
            ww, hh = d
            s.append(sv.rect(x - ww / 2 * sc, y - hh / 2 * sc, ww * sc, hh * sc, "#fff", sv.INK, 0.25))
            size = (f"<b>window {inch(ww)} square</b>: corners at a {inch(a - ww / 2)} – {inch(a + ww / 2)}, "
                    f"b {inch(b - hh / 2)} – {inch(b + hh / 2)} <span class=mm>{ww:.0f} mm</span>")
            pos = f"{a:.0f} / {b:.0f}", f"{inch(a)} / {inch(b)}"
            r_ = 0.8
        s.append(sv.t(x + r_ + 0.6, y - 0.6, L, 2.6, "start", 800, sv.ACC, "Barlow"))
        rows.append(f"<tr><td><b style='color:var(--accent)'>{L}</b></td><td>{size}</td><td class=n><b>{pos[1]}</b></td><td class=n><span class=mm>{pos[0]}</span></td><td>{esc(note)}</td></tr>")
    na, nb = "uvz"[ax[0]], "uvz"[ax[1]]
    s.append(sv.t(ox + w / 2, oy + h + 5, f"a →  {inch(A)}", 2.8, "middle", 700))
    s.append(sv.t(ox - 2, oy + h, "b ↑", 2.6, "end", 600) + sv.t(ox + w + 1.2, oy + h / 2, inch(B), 2.8, "start", 700))
    s.append("</svg>")
    s.append(f'<div class="small">a from {EDGE[na]}, b from {EDGE[nb]} — {SEEN[p.normal]}</div>')
    return (f'<div class="dcard"><div class="dh"><span class="pid w">{wid}</span> {esc(p.name)}</div>{"".join(s)}'
            f'<table class="t compact"><tr><th></th><th>Hole / bit</th><th class=n>a / b (in)</th><th class=n>mm</th><th>For</th></tr>{"".join(rows)}</table></div>')


# ================================================================ page assembly
PAGES = []


def page(body, tab, right):
    PAGES.append((body, tab, right))


def cut_table(P, W):
    rows = []
    for p in P:
        L, Wd = dims(p)
        rows.append(f'<tr><td class="cb">☐</td><td><span class="pid w" style="background:{GROUP_COL[p.group]}">{W[p.name]}</span></td>'
                    f'<td>{esc(p.name)}</td><td class="n big">{inch(L)} × {inch(Wd)}</td><td class="n mm">{L:.0f} × {Wd:.0f}</td>'
                    f'<td class="n">{len(p.holes) or "—"}</td><td class="n">{L * Wd / 645.16:.0f}</td></tr>')
    return ('<table class="t ct"><tr><th></th><th>ID</th><th>Piece</th><th class=n>Cut size (in)</th><th class=n>mm</th>'
            '<th class=n>Holes</th><th class=n>sq in</th></tr>' + "".join(rows) + "</table>")


def totals(P):
    t = {}
    for p in P:
        L, Wd = dims(p)
        t[p.group] = t.get(p.group, 0.0) + L * Wd / 645.16
    return t


def version_pages(tag, title, P, W, intro):
    sheets = pack_sheets([(W[p.name], *dims(p)) for p in P])
    idcol = {W[p.name]: GROUP_COL[p.group] for p in P}
    t = totals(P)
    tot = sum(t.values())
    sheet_area = SHEET_4x8[0] * SHEET_4x8[1] / 645.16
    groups = " · ".join(f"{GROUP_NAME[g]} {v:.0f}" for g, v in t.items())
    layouts = ""
    for k, st in enumerate(sheets):
        SKIPPED.clear()
        svg_ = sheet_svg(st, SHEET_4x8, idcol)
        small = (f'<p class="small">Thin strips not labelled on the drawing: {", ".join(sorted(set(SKIPPED)))} — see the cut order.</p>'
                 if SKIPPED else "")
        layouts += (f'<div class="sheet"><div class="sh">Sheet {k + 1} of {len(sheets)} — 4 × 8 ft, 1/2″ plywood</div>'
                    f'{svg_}{small}{cut_steps(st)}</div>')
    body = f'''<div class="kicker">Version {tag}</div><h1>{title}</h1>
<p class="lead">{intro}</p>
<div class="kpis"><div><b>{tot:.0f} sq in</b><span>plywood in the pieces ({tot / 144:.1f} sq ft)</span></div>
<div><b>{len(sheets)} × 4×8 ft</b><span>sheet{"s" if len(sheets) > 1 else ""} to buy ({tot / (sheet_area * len(sheets)) * 100:.0f} % used)</span></div>
<div><b>{len(P)} pieces</b><span>{groups} sq in</span></div></div>
{cut_table(P, W)}'''
    page(body, f"Version {tag}", "Cut list")
    page(f'<div class="kicker">Version {tag}</div><h2>Sheet layout and cut order</h2>'
         f'<p>Rip the strips first (orange dashed lines, R1, R2 …), then crosscut each strip. Every piece is drawn to scale with '
         f'1/8″ kerf between pieces; grey is offcut. Mark each piece with its ID as soon as it is cut.</p>{layouts}',
         f"Version {tag}", "Sheet layout")
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
        c = drill_card(p, " + ".join(wids))
        if len(wids) > 1:
            nm = {"axle bearing block left": "axle bearing blocks", "spacer frame 1": "spacer frames"}.get(p.name, p.name)
            c = c.replace(f"</span> {esc(p.name)}</div>", f"</span> {esc(nm)} <span class=mm>(×{len(wids)}, identical)</span></div>", 1)
        est = 1.6 + 0.19 * len(p.holes) + (0.15 * len(p.holes) if any(k != "hole" for k, *_ in p.holes) else 0)
        cards.append((c, est))
    pages_ = [[c for c, _ in cards[i:i + 4]] for i in range(0, len(cards), 4)]   # 4 cards fit any page (checked)
    for k, cs in enumerate(pages_):
        page(f'<div class="kicker">Version {tag}</div><h2>Drilling{" (continued)" if k else ""}</h2>'
             + ("" if k else "<p>Measure <b>a</b> along the bottom edge and <b>b</b> up the side, from the lower-left corner as drawn. "
                "Holes: the bold size is the drill bit to use. Clamp a scrap under the panel when drilling the big holes (2-7/16″ hole saw).</p>")
             + f'<div class="dgrid">{"".join(cs)}</div>', f"Version {tag}", "Drilling")
    return tot, len(sheets)


def stack_svg():
    """Section through the version B wall stack on the conduit axis, to scale (1 unit = 1 mm).
    x = design u (box side left), y = -z about the conduit axis."""
    s = ['<svg viewBox="-80 -84 220 168" width="100%" font-family="Inter">']
    layers = [("box front", "W02", "#d9b783"), ("sandbox wall −u", "W18", "#f3e6c8"), ("spacer", "W22", "#f2a65a"),
              ("spacer", "W23", "#f2a65a"), ("pedestal wall −u", "W10", "#e8d3a8")]
    for i, (name, wid, c) in enumerate(layers):
        x = 12.0 * i
        hole = 50.0 if name == "spacer" else 31.0
        for y0, y1 in ((-66, -hole), (hole, 66)):
            s.append(sv.rect(x, y0, 12, y1 - y0, c, sv.INK, 0.35))
        s.append(sv.t(x + 6, 73, wid, 4.4, "middle", 800, sv.INK, "Barlow"))
    # fittings: 6 mm flange (100 square) + Ø84 boss to 26 mm, 12 mm deep Ø61 socket on the wall side
    for side, x0, d in (("box fitting P18", 0.0, -1), ("pedestal fitting P17", 60.0, 1)):
        fx = x0 + (0 if d > 0 else 0)
        flange = sv.rect(min(fx, fx + 6 * d), -50, 6, 100, "#fbe3c8", sv.INK, 0.35)
        boss = sv.rect(min(fx, fx + 26 * d), -42, 26, 84, "#fbe3c8", sv.INK, 0.35)
        sock = sv.rect(min(fx, fx + 12 * d), -30.45, 12, 60.9, "#ffffff", sv.INK, 0.3)
        s.append(boss + flange + sock)
        s.append(sv.t(fx + 20 * d, -55, side, 4.4, "middle", 700))
    # rods + nuts at +-40 (flange holes)
    for y in (-40, 40):
        s.append(sv.rect(-11, y - 2.08, 82, 4.17, "#b4bcc4", sv.INK, 0.3))
        for xx in (-9.2, 66.0):
            s.append(sv.rect(xx, y - 4.4, 3.2, 8.8, "#c9d0d6", sv.INK, 0.3))
    # PTFE tubes (rows ~20 mm below the axis): stop on the box window floor (22 mm into P18), slide through P17
    pts = []
    for k in range(61):
        u = -22 + 104 * k / 60
        bump = 0.0
        if -12 <= u <= 72:
            bump = 9.5 * (1 - math.cos(2 * math.pi * (u + 12) / 84))
        pts.append((u, 20 - bump))
    s.append('<polyline points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + '" fill="none" stroke="#2a6fdb" stroke-width="2.6"/>')
    s.append(sv.t(30, 27, "PTFE tubes bow here", 4.4, "middle", 700, "#2a6fdb"))
    s.append(sv.arrowline(-12, -71, 72, -71, sv.ACC, 0.5, 2.2, both=True))
    s.append(sv.t(30, -74, "3-5/16″ chamber", 4.6, "middle", 800, sv.ACC))
    s.append(sv.t(30, 80, "8-32 rod 3-1/4″ ×4 at the flange corners, nut each end", 4.2, "middle", 600))
    s.append(sv.t(-78, -60, "BOX SIDE", 4.6, "start", 800, sv.INK2, "Barlow") + sv.t(138, -60, "PEDESTAL SIDE", 4.6, "end", 800, sv.INK2, "Barlow"))
    s.append("</svg>")
    return "".join(s)


CSS_EXTRA = """
.kpis { display: flex; gap: 8px; margin: 4px 0 8px; }
.kpis div { flex: 1; background: var(--tint); border-radius: 3px; padding: 6px 9px; }
.kpis b { display: block; font-family: Barlow; font-size: 19pt; color: var(--navy); line-height: 1.05; }
.kpis span { font-size: 7.5pt; color: var(--ink2); }
table.ct td { font-size: 8.6pt; padding: 3px 5px; }
table.ct td.big { font-weight: 700; font-size: 9.6pt; }
table.ct td.cb { font-size: 11pt; width: 16px; color: var(--ink3); }
.sheet { margin-bottom: 10px; }
.sheet .sh { font-family: Barlow; font-weight: 700; font-size: 11pt; text-transform: uppercase; color: var(--navy); margin: 4px 0; }
ol.cuts { margin: 4px 0 0; padding-left: 0; list-style: none; font-size: 8pt; }
ol.cuts li { margin-bottom: 3px; }
.dgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.dcard { border: 0.6pt solid var(--rule); border-radius: 3px; padding: 4px 6px; break-inside: avoid; }
.dcard .dh { font-weight: 700; font-size: 9pt; margin-bottom: 2px; }
.dcard table.t { font-size: 7pt; margin: 2px 0 0; }
.mm { color: var(--ink3); font-size: 0.85em; font-weight: 400; }
td.mm { color: var(--ink3); }
"""


def build():
    P_A, bxA = panels_A()
    P_B, bxB = panels_B()
    WA, WB = ids(P_A, P_B)
    tA, tB = totals(P_A), totals(P_B)
    TA, TB = sum(tA.values()), sum(tB.values())
    nA = len(pack_sheets([(WA[p.name], *dims(p)) for p in P_A]))
    nB = len(pack_sheets([(WB[p.name], *dims(p)) for p in P_B]))

    def grow(g):
        return f'<td class="n">{tA.get(g, 0):.0f}</td><td class="n">{tB.get(g, 0):.0f}</td>'
    summary = f'''<div class="band" style="position:absolute;left:0;right:0;top:0;height:0.16in;display:flex">
<span style="flex:1;background:#2e9e44"></span><span style="flex:1;background:#2a6fdb"></span><span style="flex:1;background:#d93a2b"></span><span style="flex:1;background:#8e44ad"></span></div>
<div class="kicker">EX-MA cable excavator</div><h1>Wood cut list</h1>
<p class="lead">Every plywood piece for the sandbox, the pedestal and the control box, with sheet layouts, cut order and drilling — for
<b>A</b>, the design in the assembly manual, and <b>B</b>, a minimal version with a compact control box and no 2in PVC conduit.</p>
<div class="row"><div class="col">
<h3 class="mt0">How much wood</h3>
<table class="t"><tr><th>Group</th><th class=n>A (sq in)</th><th class=n>B (sq in)</th></tr>
<tr><td>Sandbox (5 pieces)</td>{grow("sandbox")}</tr><tr><td>Pedestal</td>{grow("pedestal")}</tr>
<tr><td>Control box</td>{grow("control-box")}</tr><tr><td>Spacer frames</td>{grow("spacer")}</tr>
<tr><td><b>Total</b></td><td class="n"><b>{TA:.0f}</b></td><td class="n"><b>{TB:.0f}</b></td></tr>
<tr><td>Sheets (4 × 8 ft)</td><td class="n">{nA}</td><td class="n">{nB}</td></tr></table>
<h3>What to buy</h3>
<ul class="tight"><li><b>One 4 × 8 ft sheet of 1/2″ plywood</b> (sanded 15/32″ or 12 mm Baltic birch) covers either version; ask the store
to make the first rip (R1) if the sheet will not fit your car.</li>
<li>Project panels work too: the sandbox floor is exactly a <b>2 × 2 ft</b> panel (24″ — the CAD size is 1/64″ more, irrelevant); the
rest of either version fits on <b>two 2 × 4 ft</b> panels plus the offcut of a third.</li>
<li>Sizes assume 12 mm (15/32″) stock. With true 1/2″ the boxes come out up to 1/16″ bigger outside — no change needed.</li></ul>
</div><div class="col">
<h3 class="mt0">Before you cut</h3>
<ul class="tight"><li>All sizes in <b>inches</b>, to the nearest 1/16″. The small grey mm figures are the exact CAD sizes, for metric tapes.</li>
<li>Layouts allow a 1/8″ saw kerf between pieces. Holes are given as standard drill-bit sizes.</li>
<li>IDs <b>W01–W21</b> are the same as in the assembly manual; W22/W23 exist only in version B.</li>
<li>Write the ID on every piece in pencil as soon as it is cut, and mark its <b>bottom</b> edge — hole positions are measured from it.</li>
<li>Drill the box front (W02) and the sandbox wall −u (W18) <b>clamped together</b> so their holes line up.</li></ul>
<h3>Version B in one paragraph</h3>
<p>Control box 8-7/16″ × 14-1/4″ × 6-1/8″ (the 2026-09-28 compact spec). Pedestal 1/2″ shorter on its +u side and pushed 2-1/4″ toward
the box; a two-layer plywood spacer (W22, W23) closes the gap to the sandbox wall instead of the PVC conduit. Page {{BPAGE}} explains it.</p>
</div></div>'''
    page(summary, "Summary", "Wood cut list")
    version_pages("A", "As in the assembly manual", P_A, WA,
                  "The modelled design: control box 9-13/16″ × 15-15/16″ × 9-1/2″, pedestal 7-7/8″ × 7-1/16″, sandbox 24″ × 24″ × 9-1/2″, "
                  "joined by a 5-9/16″ length of 2in PVC conduit. Sizes and holes from <span class=mono>build-box.py</span> (same as manual Appendix B).")
    bstart = len(PAGES) + 1
    # B explanation page
    rows = [("Lever axle (5/16″ rod)", "8-1/16″", "7-5/16″"), ("Slew spool axle (5/16″ rod)", "10-13/16″", "7-3/8″"),
            ("Lever handles (5/16″ rod) ×3", "9-1/16″", "5-11/16″"), ("2in PVC conduit", "5-9/16″", "— (none)"),
            ("Fitting bolts", "4 × M3 × 35 + 4 × M3 × 25", "4 × 8-32 rod, 3-1/4″, nut each end"),
            ("Boom / stick / bucket rope", "54-1/2″ / 71-11/16″ / 85-9/16″", "50″ / 67-3/16″ / 81-1/16″"),
            ("PTFE stick_hi / stick_lo", "25-1/2″ / 25-15/16″", "23-1/4″ / 23-11/16″"),
            ("PTFE bucket_hi / bucket_lo", "32″ / 32-3/8″", "29-3/4″ / 30-1/8″"),
            ("Slew sleeve A / B", "13-3/8″ / 16″", "10-3/4″ / 13-3/8″"), ("Slew rope A / B", "32-5/8″ / 35-7/16″", "30-1/16″ / 32-13/16″"),
            ("Reprints", "—", "slew spool (tube 2-5/16″), lever hubs boom + bucket")]
    tr = "".join(f"<tr><td>{a}</td><td class=n>{b}</td><td class=n><b>{c}</b></td></tr>" for a, b, c in rows)
    bpage = f'''<div class="kicker">Version B</div><h1>Minimal version: what changes</h1>
<div class="figframe" style="padding:4px 8px;width:3.45in;margin:0 auto">{stack_svg()}</div>
<div class="cap"><b>Section</b><span>Version B wall stack on the conduit axis, to scale; each plywood layer 15/32″: W02 box front, W18 sandbox wall, W22 + W23 spacers, W10 pedestal wall. One 8-32 rod clamps
everything. The spacers' 3-15/16″ square window holds the rod nuts' far ends clear and gives the PTFE tubes room to bow.</span></div>
<div class="row mt8"><div class="col">
<h3 class="mt0">Why a spacer, not nothing <span class="tag d">Derived</span></h3>
<p>The four arm PTFE tubes change length by up to about 7/16″ as the boom and stick move; in version A that spare length coils in the
conduit. With the pedestal flat on the sandbox wall there would be only 1-7/8″ between the two fittings, and a tube storing that much there
bends to about 5/16″ radius — below the 5/8″ minimum. With the 15/16″ spacer the chamber is 3-5/16″ long and the bow needs about a 3/4″ radius. The
chamber is closed on all sides, so no sand gets in.</p>
<p class="small">Estimate from a cosine bow: rise h = √(4·L·ΔL)/π, smallest radius = L² / (2π²·h). Not a CAD check — do the dry fit below.</p>
<h3>Build notes</h3>
<ul class="tight"><li>Glue W22 to W23, then glue the pair to the outside of the pedestal wall −u (W10), windows lined up with its Ø62 hole.</li>
<li>Stand the pedestal against the sandbox wall −u, run a bead of silicone round the spacer’s outer edge, and clamp with the four rods.</li>
<li>The arm’s slew axis now sits 2-1/4″ closer to the box: 5-1/4″ from the sandbox wall’s inside face instead of 7-1/2″.</li>
<li><b>Dry fit:</b> before closing the box lid, move the boom and stick through their full ranges and check that each stick and bucket
tube still slides freely at the turret end.</li></ul>
</div></div>
<h3>Other stock that changes <span class="tag d">Derived</span></h3>
<table class="t compact"><tr><th>Item</th><th class=n>A (manual)</th><th class=n>B (minimal)</th></tr>{tr}</table>
<p class="small">Box rods, handles and reprints from the compact-box spec. Ropes and tubes: the conduit run is 2-1/4″ shorter, so each arm rope
(two strands through it) is 4-1/2″ shorter and each tube or sleeve 2-1/4″ shorter; the slew numbers also include the compact box. Cut
ropes 3/4″ long and trim when you crimp.</p>'''
    page(bpage, "Version B", "What changes")
    version_pages("B", "Minimal version (no PVC conduit)", P_B, WB,
                  f"Compact control box 8-7/16″ × 14-1/4″ × 6-1/8″; pedestal 7-3/8″ × 7-1/16″; two spacer frames (W22, W23) in place of the conduit; "
                  f"sandbox unchanged except the bolt holes in W18. Panels generated by <span class=mono>build-box.py</span> with the "
                  f"compact-box constants and the minimal pedestal.")

    css = (HERE / "2026-10-10-manual.css").read_text() + CSS_EXTRA
    out = []
    for i, (body, tab, right) in enumerate(PAGES, start=1):
        body = body.replace("{BPAGE}", str(bstart))
        head = (f'<div class="rhead"><span class="tab{" st" if tab.startswith("Version") else ""}">{esc(tab)}</span><span>{esc(right)}</span></div>'
                if i > 1 else "")
        foot = (f'<div class="rfoot"><span>EX-MA cable excavator · Wood cut list · 2026-10-10</span><span class="pn">{i}</span></div>')
        out.append(f'<section class="page">{head}{body}{foot}</section>')
    (HERE / "2026-10-10-wood-cutlist.html").write_text(
        f'<!doctype html><html><head><meta charset="utf-8"><title>EX-MA Wood Cut List</title><style>{css}</style></head>'
        f'<body>{"".join(out)}</body></html>')
    print(f"{len(PAGES)} pages; A {TA:.0f} sq in on {nA} sheet(s); B {TB:.0f} sq in on {nB} sheet(s)")


if __name__ == "__main__":
    build()
