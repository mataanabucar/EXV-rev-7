"""SVG helpers for the assembly manual: figure overlays (callouts, balloons, arrows) and the
vector diagrams (rope circuits, 1:1 hardware, drilling drawings, top views, flow).

Imported by 2026-10-10-build-manual.py.
"""
import html
import json
import math
from pathlib import Path

INK, INK2, INK3, RULE = "#1d232b", "#4a5562", "#7b8592", "#d5dae0"
ACC = "#e8590c"
CIRC = dict(boom="#2e9e44", stick="#2a6fdb", bucket="#d93a2b", slew="#8e44ad")
PT = 96 / 72                          # CSS px per pt


def esc(s):
    return html.escape(str(s), quote=True)


def text_w(s, size):
    """Rough Inter text width (same units as size)."""
    w = 0.0
    for ch in str(s):
        w += 0.33 if ch in "il.,:;|!'()[]1 " else 0.62 if ch in "mwMW%—" else 0.55 if ch.isupper() or ch in "×Ø±°" else 0.52
    return w * size


# ================================================================== figure overlay
def content_box(png, pts, pad_frac=0.03):
    """Bounding box of the non-white pixels of a render, grown to include the given points."""
    from PIL import Image, ImageChops
    im = Image.open(png).convert("L")
    W, H = im.size
    bb = ImageChops.invert(im).point(lambda v: 255 if v > 12 else 0).getbbox() or (0, 0, W, H)
    x0, y0, x1, y1 = bb
    for x, y in pts:
        x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    pad = pad_frac * max(x1 - x0, y1 - y0)
    return (max(0, int(x0 - pad)), max(0, int(y0 - pad)), min(W, int(x1 + pad)), min(H, int(y1 + pad)))


def figure(fdir, fid, width_in, gutter=(1.3, 1.3, 0.25, 0.25), legend=False, extra=None, caption=None, num=None,
           label_pt=7.0, frame=False, crop="auto", img_href=None, max_h_in=None, key_cols=2):
    """Image + SVG overlay. gutter = (left, right, top, bottom) in inches of label space around the
    image. Callouts come from <fdir>/<fid>.json (written by the renderer). The image is cropped to its
    content (plus callout anchors and arrows) unless crop is None or an explicit box."""
    meta = json.loads((Path(fdir) / f"{fid}.json").read_text())
    W, H = meta["w"], meta["h"]
    pts = [tuple(c["anchor2d"]) for c in meta.get("callouts", [])]
    for a in meta.get("arrows", []):
        pts += [tuple(p) for p in a["pts"]]
    pts += [tuple(v) for v in meta.get("points", {}).values()] if extra else []
    if crop == "auto":
        crop = content_box(Path(fdir) / f"{fid}.png", pts)
    x0, y0, x1, y1 = crop if crop else (0, 0, W, H)
    cw, ch = x1 - x0, y1 - y0
    gl, gr, gt, gb = gutter
    img_w_in = width_in - gl - gr
    if max_h_in and ch / cw * img_w_in > max_h_in:           # too tall: narrow the image, keep it centred
        new_w = max_h_in * cw / ch
        extra_w = img_w_in - new_w
        gl, gr = gl + extra_w / 2, gr + extra_w / 2
        img_w_in = new_w
    s = cw / img_w_in                     # image px per inch
    fs = label_pt / 72 * s                 # font size in image px
    GL, GR, GT, GB = gl * s, gr * s, gt * s, gb * s
    cl = [dict(c) for c in meta.get("callouts", [])]
    if legend:                              # every callout becomes a numbered balloon
        used = {c["n"] for c in cl if c.get("n") is not None}
        k = 1
        for c in cl:
            if c.get("n") is None:
                while k in used:
                    k += 1
                c["n"] = k
                used.add(k)
    # T/B gutters grow to fit their label rows
    need_t, need_b = tb_needed(cl, cw, GL, GR, fs, legend, x0, y0)
    GT, GB = max(GT, need_t), max(GB, need_b)
    VW, VH = cw + GL + GR, ch + GT + GB
    height_in = VH / s
    out = []
    for a in meta.get("arrows", []):
        out.append(arrow_svg(a, fs, x0, y0))
    out.append(layout_callouts(cl, cw, ch, GL, GR, GT, GB, fs, legend, x0, y0))
    if extra:
        out.append(extra(meta, fs, x0, y0))
    href = img_href or f"figures/{fid}.png"
    svg = (f'<svg class="ov" viewBox="{-GL:.1f} {-GT:.1f} {VW:.1f} {VH:.1f}" width="{width_in}in" height="{height_in:.3f}in">'
           + "".join(out) + "</svg>")
    clip = (f'<div style="position:absolute;left:{GL / s:.3f}in;top:{GT / s:.3f}in;width:{cw / s:.3f}in;height:{ch / s:.3f}in;overflow:hidden">'
            f'<img src="{href}" style="position:absolute;left:{-x0 / s:.3f}in;top:{-y0 / s:.3f}in;width:{W / s:.3f}in"></div>')
    cap = ""
    if caption:
        cap = f'<div class="cap" style="width:{width_in}in">{f"<b>Fig. {num}</b>" if num else ""}<span>{caption}</span></div>'
    key = ""
    if legend and key_cols:
        items = sorted(cl, key=lambda c: int(c["n"]))
        key = (f'<div class="key" style="--kc:{key_cols}">' + "".join(
            f'<div><span class="ball">{esc(c["n"])}</span><span>{esc(c["text"])}</span></div>' for c in items) + "</div>")
    return (f'<div class="fig{" figframe" if frame else ""}" style="width:{width_in}in">'
            f'<div style="position:relative;width:{width_in}in;height:{height_in:.3f}in">{clip}{svg}</div>{key}{cap}</div>')


def _wrap(text, fs, maxw):
    words, lines, cur = str(text).split(), [], ""
    for w_ in words:
        t_ = (cur + " " + w_).strip()
        if text_w(t_, fs) > maxw and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = t_
    if cur:
        lines.append(cur)
    return lines


def tb_rows(g, avail, fs, legend):
    """Split the labels of one T/B side into rows that fit the available width."""
    br = fs * 0.95
    for c in g:
        c["_lines"] = [] if (legend and c.get("n") is not None) else _wrap(c["text"], fs, fs * 11)
        c["_w"] = max([text_w(l, fs) for l in c["_lines"]] + [2 * br]) + (2 * br + fs * 0.4 if c.get("n") is not None and c["_lines"] else 0) + fs * 1.2
    total = sum(c["_w"] for c in g)
    nrows = 1 if total <= avail else 2 if total <= 2 * avail else 3
    return [g[i::nrows] for i in range(nrows)]


def tb_needed(cl, W, GL, GR, fs, legend, x0, y0):
    lh = fs * 1.25
    need = {"T": 0.0, "B": 0.0}
    if legend:
        return 0.0, 0.0
    for side in ("T", "B"):
        g = sorted([c for c in cl if c.get("side") == side], key=lambda c: c["anchor2d"][0])
        if not g:
            continue
        rows = tb_rows(g, W + GL + GR - fs, fs, legend)
        h = 0.0
        for r in rows:
            h += max(max(max(len(c["_lines"]) for c in r), 1) * lh, 2 * fs) + fs * 0.6
        need[side] = h + fs * 0.6
    return need["T"], need["B"]


def arrow_head(x, y, dx, dy, size, color):
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    a = (x, y)
    b = (x - ux * size + px * size * 0.45, y - uy * size + py * size * 0.45)
    c = (x - ux * size - px * size * 0.45, y - uy * size - py * size * 0.45)
    return f'<path d="M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f} L{c[0]:.1f},{c[1]:.1f} Z" fill="{color}"/>'


def arrow_svg(a, fs, x0=0, y0=0, color=ACC):
    pts = [(p[0] - x0, p[1] - y0) for p in a["pts"]]
    w = fs * 0.28
    hs = fs * 1.25
    if a.get("kind") == "rotate":
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts[:-1])
        (xa, ya), (xb, yb) = pts[-3], pts[-1]
        return (f'<path d="{d}" fill="none" stroke="#fff" stroke-width="{w * 3:.1f}" stroke-linecap="round"/>'
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w:.1f}" stroke-linecap="round"/>'
                + arrow_head(xb, yb, xb - xa, yb - ya, hs, color))
    (xa, ya), (xb, yb) = pts
    L = math.hypot(xb - xa, yb - ya)
    if L < 1:
        return ""
    ux, uy = (xb - xa) / L, (yb - ya) / L
    sx, sy = xa, ya
    if a.get("kind") == "double":
        sx, sy = xa + ux * hs * 0.8, ya + uy * hs * 0.8
    ex_, ey_ = xb - ux * hs * 0.8, yb - uy * hs * 0.8
    s = (f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex_:.1f}" y2="{ey_:.1f}" stroke="#fff" stroke-width="{w * 3:.1f}" stroke-linecap="round"/>'
         f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex_:.1f}" y2="{ey_:.1f}" stroke="{color}" stroke-width="{w:.1f}" stroke-linecap="round"/>'
         + arrow_head(xb, yb, ux, uy, hs, color))
    if a.get("kind") == "double":
        s += arrow_head(xa, ya, -ux, -uy, hs, color)
    return s


def balloon(x, y, n, fs):
    r = fs * 0.95
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#fff" stroke="{ACC}" stroke-width="{fs * 0.13:.1f}"/>'
            f'<text x="{x:.1f}" y="{y + fs * 0.36:.1f}" text-anchor="middle" font-family="Barlow" font-weight="800" '
            f'font-size="{fs * 1.05:.1f}" fill="{ACC}">{esc(n)}</text>')


def layout_callouts(cl, W, H, GL, GR, GT, GB, fs, legend, x0=0, y0=0):
    """Place labels in gutters (L/R columns, T/B rows), sorted to avoid crossing; draw leaders."""
    if not cl:
        return ""
    if legend:
        return near_balloons(cl, W, H, GL, GR, GT, GB, fs, x0, y0)
    groups = {"L": [], "R": [], "T": [], "B": []}
    for c in cl:
        ax, ay = c["anchor2d"][0] - x0, c["anchor2d"][1] - y0
        side = c.get("side") or ("L" if ax < W / 2 else "R")
        c["_a"] = (ax, ay)
        groups[side].append(c)
    out = []
    lh = fs * 1.25
    pad = fs * 0.6
    br = fs * 0.95

    def label_lines(c, maxw):
        if legend and c.get("n") is not None:
            return []
        words, lines, cur = str(c["text"]).split(), [], ""
        for w_ in words:
            t = (cur + " " + w_).strip()
            if text_w(t, fs) > maxw and cur:
                lines.append(cur)
                cur = w_
            else:
                cur = t
        if cur:
            lines.append(cur)
        return lines

    for side in ("L", "R"):
        g = sorted(groups[side], key=lambda c: c["_a"][1])
        if not g:
            continue
        colw = (GL if side == "L" else GR) - pad * 2 - (2 * br + fs * 0.4)
        for c in g:
            c["_lines"] = label_lines(c, max(colw, fs * 4))
            c["_h"] = max(len(c["_lines"]) * lh, 2 * br) + fs * 0.45
        # vertical placement: start at anchor y, push down to avoid overlap, then pull up if past the bottom
        ys = [c["_a"][1] for c in g]
        pos = []
        top = -GT + fs
        for c, y in zip(g, ys):
            yy = max(y - c["_h"] / 2, top)
            pos.append(yy)
            top = yy + c["_h"]
        bottom = H + GB - fs * 0.2
        over = top - bottom
        if over > 0:
            for i in range(len(pos) - 1, -1, -1):
                lim = bottom - sum(c["_h"] for c in g[i:])
                pos[i] = min(pos[i], lim)
        for c, yy in zip(g, pos):
            ax, ay = c["_a"]
            cy = yy + c["_h"] / 2
            n = c.get("n")
            if side == "L":
                bx = -GL + pad + br
                tx = bx + br + fs * 0.35 if n is not None else -GL + pad
                anchor = "start"
                lend = (tx + (max(text_w(l, fs) for l in c["_lines"]) if c["_lines"] else 0) + fs * 0.3) if (n is None or c["_lines"]) else bx + br
                if n is not None and not c["_lines"]:
                    lend = bx + br
                lx = max(lend, bx + br) if n is not None else lend
            else:
                bx = W + GR - pad - br
                tx = bx - br - fs * 0.35 if n is not None else W + GR - pad
                anchor = "end"
                lend = (tx - (max(text_w(l, fs) for l in c["_lines"]) if c["_lines"] else 0) - fs * 0.3)
                if n is not None and not c["_lines"]:
                    lend = bx - br
                lx = lend
            # leader: horizontal stub then straight to the anchor
            stub = lx + (fs * 0.8 if side == "L" else -fs * 0.8)
            out.append(f'<polyline points="{lx:.1f},{cy:.1f} {stub:.1f},{cy:.1f} {ax:.1f},{ay:.1f}" fill="none" '
                       f'stroke="#fff" stroke-width="{fs * 0.32:.1f}" stroke-linejoin="round"/>'
                       f'<polyline points="{lx:.1f},{cy:.1f} {stub:.1f},{cy:.1f} {ax:.1f},{ay:.1f}" fill="none" '
                       f'stroke="{INK}" stroke-width="{fs * 0.09:.1f}" stroke-linejoin="round"/>'
                       f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="{fs * 0.22:.1f}" fill="{INK}" stroke="#fff" stroke-width="{fs * 0.08:.1f}"/>')
            if n is not None:
                out.append(balloon(bx, cy, n, fs))
            ty = cy - (len(c["_lines"]) - 1) * lh / 2 + fs * 0.35
            for i, l in enumerate(c["_lines"]):
                out.append(f'<text x="{tx:.1f}" y="{ty + i * lh:.1f}" text-anchor="{anchor}" font-family="Inter" '
                           f'font-weight="500" font-size="{fs:.1f}" fill="{INK}">{esc(l)}</text>')
    for side in ("T", "B"):
        g = sorted(groups[side], key=lambda c: c["_a"][0])
        if not g:
            continue
        rows = tb_rows(g, W + GL + GR - fs, fs, legend)
        ycur = -GT + fs * 0.6 if side == "T" else H + GB - fs * 0.6
        for row in rows:
            block_h = max(max(max(len(c["_lines"]) for c in row), 1) * lh, 2 * br)
            if side == "B":
                ycur -= block_h + fs * 0.6
            xs, left = [], -GL + fs * 0.3
            for c in row:
                xx = max(c["_a"][0] - c["_w"] / 2, left)
                xs.append(xx)
                left = xx + c["_w"]
            right = W + GR - fs * 0.3
            if left > right:
                for k in range(len(xs) - 1, -1, -1):
                    xs[k] = min(xs[k], right - sum(c["_w"] for c in row[k:]))
            for c, xx in zip(row, xs):
                ax, ay = c["_a"]
                cx = xx + c["_w"] / 2
                top = ycur
                ly = top + block_h + fs * 0.15 if side == "T" else top - fs * 0.15
                n = c.get("n")
                out.append(f'<polyline points="{cx:.1f},{ly:.1f} {ax:.1f},{ay:.1f}" fill="none" stroke="#fff" stroke-width="{fs * 0.32:.1f}"/>'
                           f'<polyline points="{cx:.1f},{ly:.1f} {ax:.1f},{ay:.1f}" fill="none" stroke="{INK}" stroke-width="{fs * 0.09:.1f}"/>'
                           f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="{fs * 0.22:.1f}" fill="{INK}" stroke="#fff" stroke-width="{fs * 0.08:.1f}"/>')
                tx, anchor = cx, "middle"
                if n is not None:
                    if c["_lines"]:
                        bx = xx + fs * 0.6 + br
                        out.append(balloon(bx, top + br, n, fs))
                        tx, anchor = bx + br + fs * 0.3, "start"
                    else:
                        out.append(balloon(cx, top + br, n, fs))
                for k, l in enumerate(c["_lines"]):
                    out.append(f'<rect x="{(tx if anchor == "start" else tx - text_w(l, fs) / 2) - fs * 0.15:.1f}" y="{top + k * lh - fs * 0.05:.1f}" '
                               f'width="{text_w(l, fs) + fs * 0.3:.1f}" height="{lh:.1f}" fill="#fff" opacity="0.85"/>')
                    out.append(f'<text x="{tx:.1f}" y="{top + k * lh + fs * 0.95:.1f}" text-anchor="{anchor}" font-family="Inter" '
                               f'font-weight="500" font-size="{fs:.1f}" fill="{INK}">{esc(l)}</text>')
            if side == "T":
                ycur += block_h + fs * 0.6
    return "".join(out)


def near_balloons(cl, W, H, GL, GR, GT, GB, fs, x0=0, y0=0):
    """Numbered balloons placed just outside the part, pushed apart; straight leaders."""
    br = fs * 0.95
    A = [(c["anchor2d"][0] - x0, c["anchor2d"][1] - y0) for c in cl]
    cx = sum(a[0] for a in A) / len(A)
    cy = sum(a[1] for a in A) / len(A)
    D = max(W, H) * 0.09
    P = []
    for (ax, ay), c in zip(A, cl):
        dx, dy = ax - cx, ay - cy
        side = None
        if side == "L":
            dx, dy = -1.0, 0.15 * (dy / (abs(dy) + 1))
        elif side == "R":
            dx, dy = 1.0, 0.15 * (dy / (abs(dy) + 1))
        elif side == "T":
            dx, dy = 0.15 * (dx / (abs(dx) + 1)), -1.0
        elif side == "B":
            dx, dy = 0.15 * (dx / (abs(dx) + 1)), 1.0
        L = math.hypot(dx, dy) or 1
        P.append([ax + dx / L * D, ay + dy / L * D])
    lo_x, hi_x, lo_y, hi_y = -GL + br * 1.3, W + GR - br * 1.3, -GT + br * 1.3, H + GB - br * 1.3
    for _ in range(300):
        moved = False
        for i in range(len(P)):
            for j in range(len(P)):
                if i == j:
                    continue
                # balloon-balloon and balloon-anchor spacing
                for (qx, qy), mind in (((P[j][0], P[j][1]), br * 2.5), ((A[j][0], A[j][1]), br * 1.6)):
                    dx, dy = P[i][0] - qx, P[i][1] - qy
                    d = math.hypot(dx, dy)
                    if d < mind:
                        if d < 1e-6:
                            dx, dy, d = 1.0, 0.3, 1.04
                        k = (mind - d) / d * 0.5
                        P[i][0] += dx * k
                        P[i][1] += dy * k
                        moved = True
            P[i][0] = min(max(P[i][0], lo_x), hi_x)
            P[i][1] = min(max(P[i][1], lo_y), hi_y)
        if not moved:
            break
    out = []
    for (px, py), (ax, ay), c in zip(P, A, cl):
        dx, dy = ax - px, ay - py
        d = math.hypot(dx, dy) or 1
        sx, sy = px + dx / d * br, py + dy / d * br
        out.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="#fff" stroke-width="{fs * 0.32:.1f}"/>'
                   f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="{INK}" stroke-width="{fs * 0.1:.1f}"/>'
                   f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="{fs * 0.22:.1f}" fill="{INK}" stroke="#fff" stroke-width="{fs * 0.08:.1f}"/>')
    for (px, py), c in zip(P, cl):
        out.append(balloon(px, py, c["n"], fs))
    return "".join(out)


# ================================================================== simple primitives (user units)
def t(x, y, s, size=3.2, anchor="start", weight=500, color=INK, family="Inter", extra=""):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{color}" {extra}>{esc(s)}</text>')


def line(x1, y1, x2, y2, c=INK, w=0.3, dash=None, cap="round"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{c}" stroke-width="{w}" stroke-linecap="{cap}"{d}/>'


def rect(x, y, w, h, fill="none", stroke=INK, sw=0.3, rx=0, extra=""):
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def circ(x, y, r, fill="none", stroke=INK, sw=0.3):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def hexagon(x, y, af, fill="#c9d0d6", stroke=INK, sw=0.25, rot=0.0):
    R = af / 2 / math.cos(math.pi / 6)
    pts = " ".join(f"{x + R * math.cos(math.radians(rot + 30 + 60 * k)):.2f},{y + R * math.sin(math.radians(rot + 30 + 60 * k)):.2f}" for k in range(6))
    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def arrowline(x1, y1, x2, y2, c=INK, w=0.35, hs=1.6, both=False):
    s = line(x1, y1, x2, y2, c, w)
    s += arrow_head(x2, y2, x2 - x1, y2 - y1, hs, c)
    if both:
        s += arrow_head(x1, y1, x1 - x2, y1 - y2, hs, c)
    return s


# ================================================================== hardware at 1:1 (1 unit = 1 mm)
STEEL, ZINC, BLACK = "#c9d0d6", "#dde2e7", "#3a414b"


def threads(x, y0, y1, d, pitch):
    s = ""
    y = y0 + pitch
    while y < y1 - 0.2:
        s += line(x - d / 2, y, x + d / 2, y - pitch * 0.4, "#8a939c", 0.12)
        y += pitch
    return s


def socket_cap(x, y, L, head_d=5.5, head_h=3.0, d=3.0, fill=BLACK):
    s = rect(x - head_d / 2, y, head_d, head_h, fill, INK, 0.2, 0.4)
    s += rect(x - d / 2, y + head_h, d, L, "#59626d", INK, 0.2)
    s += threads(x, y + head_h, y + head_h + L, d, 0.5)
    return s


def button_head(x, y, L, head_d=5.7, head_h=1.65, d=3.0, fill=BLACK):
    s = f'<path d="M{x - head_d / 2:.2f},{y + head_h:.2f} Q{x - head_d / 2:.2f},{y:.2f} {x:.2f},{y:.2f} Q{x + head_d / 2:.2f},{y:.2f} {x + head_d / 2:.2f},{y + head_h:.2f} Z" fill="{fill}" stroke="{INK}" stroke-width="0.2"/>'
    s += rect(x - d / 2, y + head_h, d, L, "#59626d", INK, 0.2)
    s += threads(x, y + head_h, y + head_h + L, d, 0.5)
    return s


def wood_screw(x, y, L, d, head_d, fill=ZINC):
    hh = (head_d - d) / 2 / math.tan(math.radians(41))
    tip = d * 1.6
    pts = [(x - head_d / 2, y), (x + head_d / 2, y), (x + d / 2, y + hh), (x + d / 2, y + L - tip), (x, y + L),
           (x - d / 2, y + L - tip), (x - d / 2, y + hh)]
    s = '<polygon points="' + " ".join(f"{a:.2f},{b:.2f}" for a, b in pts) + f'" fill="{fill}" stroke="{INK}" stroke-width="0.2"/>'
    yy = y + hh + 0.8
    while yy < y + L - tip:
        s += line(x - d / 2, yy, x + d / 2, yy - 0.5, "#8a939c", 0.15)
        yy += 1.3
    return s


def rod(x, y, L, d, fill=STEEL, threaded=True, pitch=0.79):
    s = rect(x, y - d / 2, L, d, fill, INK, 0.2)
    if threaded:
        xx = x + pitch
        while xx < x + L - 0.2:
            s += line(xx, y - d / 2, xx - pitch * 0.4, y + d / 2, "#8a939c", 0.12)
            xx += pitch
    return s


def ring(x, y, od, id_, fill=STEEL, split=False):
    s = (f'<path d="M{x - od / 2:.2f},{y:.2f} a{od / 2},{od / 2} 0 1,0 {od:.2f},0 a{od / 2},{od / 2} 0 1,0 {-od:.2f},0 Z '
         f'M{x - id_ / 2:.2f},{y:.2f} a{id_ / 2},{id_ / 2} 0 1,1 {id_:.2f},0 a{id_ / 2},{id_ / 2} 0 1,1 {-id_:.2f},0 Z" '
         f'fill="{fill}" fill-rule="evenodd" stroke="{INK}" stroke-width="0.2"/>')
    if split:
        s += rect(x + id_ / 2 - 0.2, y - 0.35, (od - id_) / 2 + 0.4, 0.7, "#fff", "none", 0)
    return s


def nut(x, y, af, hole, fill=STEEL):
    return hexagon(x, y, af, fill) + circ(x, y, hole / 2, "#fff", INK, 0.2)


# ================================================================== top-view slew diagram
def slew_topview(ped, spool):
    """ped / spool: dict lane -> (pocket or anchor angle deg, rope exit tangent deg). Design frame top view:
    +u to the right, +v up."""
    W, H = 180, 96
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%">']

    def drum(cx, cy, r, title, marks, arm=False):
        g = [circ(cx, cy, r, "#fbe3c8", INK, 0.35), circ(cx, cy, r - 3.5, "#fff", INK3, 0.2), circ(cx, cy, 4, "#e9ecef", INK, 0.25)]
        g.append(t(cx, cy + r + 12, title, 3.4, "middle", 700))
        if arm:
            g.append(arrowline(cx + 5, cy, cx + r + 16, cy, INK, 0.6, 2.4))
            g.append(t(cx + r + 4, cy - 2.2, "arm points +u", 2.6, "start", 600, INK2))
        for lane, (ang, lab_) in marks.items():
            a = math.radians(ang)
            px, py = cx + (r - 1.8) * math.cos(a), cy - (r - 1.8) * math.sin(a)
            col = CIRC["slew"]
            g.append(f'<rect x="{px - 2.4:.2f}" y="{py - 1.4:.2f}" width="4.8" height="2.8" rx="0.6" fill="{col}" '
                     f'transform="rotate({-ang + 90:.1f} {px:.2f} {py:.2f})"/>')
            lx, ly = cx + (r + 7) * math.cos(a), cy - (r + 7) * math.sin(a)
            g.append(line(px, py, lx, ly, INK, 0.2))
            g.append(t(lx, ly - 1.2 if math.sin(a) > 0 else ly + 3.2, lab_, 2.7, "middle", 600))
        return "".join(g)
    s.append(drum(48, 46, 27, "Pedestal slew drum (P14)", ped, arm=True))
    s.append(drum(132, 46, 27, "Slew spool (P23)", spool))
    # axes
    s.append(arrowline(4, 92, 16, 92, INK, 0.35, 1.6) + t(17.5, 93, "+u", 2.8, "start", 700))
    s.append(arrowline(4, 92, 4, 80, INK, 0.35, 1.6) + t(5.5, 79.5, "+v (your left)", 2.8, "start", 700))
    s.append("</svg>")
    return "".join(s)


# ================================================================== rope circuit diagram ("wiring diagram")
def circuits_svg(lengths):
    W, H = 186, 120
    cols = [("Control", 10), ("Box fitting", 45), ("2in conduit", 66), ("Pedestal fitting", 88), ("Elbow + PEX tube", 112),
            ("Arm", 142), ("Joint drum", 172)]
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" font-family="Inter">']
    for name, x in cols:
        s.append(t(x, 7, name.upper(), 2.7, "middle", 700, INK2, "Barlow", 'letter-spacing="0.2"'))
    for x in (45, 88):
        s.append(rect(x - 2.2, 10, 4.4, 92, "#fbe3c8", INK, 0.25, 0.6))
    s.append(rect(50, 12, 32, 88, "#f1f3f5", INK3, 0.25, 2))
    rows = [("boom", 22, "Boom lever", "Boom drum Ø30", False), ("stick", 44, "Stick lever", "Stick drum Ø26", True),
            ("bucket", 66, "Bucket lever", "Bucket drum Ø17", True), ("slew", 88, "Slew wheel", "Slew drum Ø110", None)]
    for c, y, ctrl, jd, ptfe in rows:
        col = CIRC[c]
        # control drum
        s.append(circ(14, y, 6.5, "#fbe3c8", INK, 0.3) + circ(14, y, 1.4, "#e9ecef", INK, 0.2))
        s.append(t(14, y + 11, ctrl, 2.6, "middle", 700))
        for dy, lab in ((-2.2, "upper"), (2.2, "lower")):
            yy = y + dy
            if ptfe is True:
                s.append(f'<path d="M45,{yy:.1f} L142,{yy:.1f}" stroke="#c4cad1" stroke-width="2.4" fill="none"/>')
                s.append(f'<path d="M45,{yy:.1f} L142,{yy:.1f}" stroke="#ffffff" stroke-width="1.6" fill="none"/>')
            if ptfe is None:
                s.append(f'<path d="M30,{yy:.1f} L88,{yy:.1f}" stroke="#c4cad1" stroke-width="2.4" fill="none"/>')
                s.append(f'<path d="M30,{yy:.1f} L88,{yy:.1f}" stroke="#ffffff" stroke-width="1.6" fill="none"/>')
            s.append(line(20, y + (dy * 2.4), 30, yy, col, 0.7))
            end = 166 if c != "slew" else 112
            s.append(line(30, yy, end, yy, col, 0.7))
            # loop + anchor at the control end
            s.append(circ(20, y + dy * 2.4, 0.9, "#fff", col, 0.45))
        # joint drum
        jx = 172 if c != "slew" else 118
        s.append(circ(jx, y, 6.5, "#fbe3c8", INK, 0.3))
        s.append(f'<path d="M{jx - 6:.1f},{y - 2.2:.1f} A6.2,6.2 0 0,1 {jx + 6:.1f},{y - 2.2:.1f}" stroke="{col}" stroke-width="0.7" fill="none"/>')
        s.append(rect(jx - 1.2, y - 7.6, 2.4, 2.0, INK, "none", 0, 0.4))
        s.append(t(jx, y + 11, jd, 2.6, "middle", 700))
        lx = 127 if c != "slew" else 66
        s.append(rect(lx - text_w(lengths[c], 2.4) / 2 - 0.8, y - 8.6, text_w(lengths[c], 2.4) + 1.6, 3.6, "#ffffff", "none", 0, 0.6))
        s.append(t(lx, y - 5.9, lengths[c], 2.4, "middle", 600, INK2))
        if c == "slew":
            s.append(t(118 + 9, y + 1, "on the PEX turret tube", 2.4, "start", 500, INK2))
            s.append(t(118 + 9, y + 4.2, "(turns the turret)", 2.4, "start", 500, INK2))
    # legend
    ly = 112
    s.append(rect(10, ly - 2.8, 9, 3.6, "#ffffff", "#c4cad1", 0.6, 1) + t(21, ly, "PTFE tube / sleeve (rope slides inside)", 2.5))
    s.append(circ(72, ly - 1, 1, "#fff", INK, 0.45) + t(75, ly, "loop on a slotted anchor (tension adjuster)", 2.5))
    s.append(rect(133, ly - 2.4, 2.4, 2.0, INK, "none", 0, 0.4) + t(137, ly, "single crimp in a drum pocket", 2.5))
    s.append("</svg>")
    return "".join(s)


# ================================================================== conventions diagram
def conventions_svg():
    W, H = 120, 84
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%">']
    s.append(t(60, 4, "TOP VIEW — z points up, out of the page", 2.8, "middle", 700, INK2, "Barlow"))
    s.append(rect(50, 9, 62, 62, "#f3e6c8", INK, 0.35) + t(81, 14, "SANDBOX", 2.8, "middle", 700, INK2, "Barlow"))
    s.append(rect(61, 31, 20, 18, "#e8d3a8", INK, 0.3) + circ(71, 40, 7, "none", INK3, 0.25) + t(71, 54, "pedestal", 2.4, "middle", 600))
    s.append(rect(24.5, 28, 25, 40.5, "#d9b783", INK, 0.35) + t(37, 73.5, "CONTROL BOX", 2.6, "middle", 700, INK2, "Barlow"))
    for vy in (32, 39, 46):
        s.append(circ(32, vy, 1.6, "#3a414b", "none", 0))
    s.append(circ(39.5, 59, 6.5, "none", "#f08a24", 0.8))
    s.append(line(49.5, 41, 61, 41, "#aab2bb", 2.0))
    s.append(circ(11, 41, 3.2, "#fff", INK, 0.4) + t(11, 48, "you", 2.6, "middle", 700))
    s.append(f'<path d="M14.6,38.5 L17.6,41 L14.6,43.5" fill="none" stroke="{INK}" stroke-width="0.45"/>')
    s.append(arrowline(6, 80, 26, 80, ACC, 0.6, 2.2) + t(27.5, 81, "+u toward the sandbox", 2.7, "start", 700, ACC))
    s.append(arrowline(6, 80, 6, 62, ACC, 0.6, 2.2) + t(7.5, 61, "+v your left", 2.7, "start", 700, ACC))
    s.append(circ(6, 80, 1.2, "#fff", ACC, 0.5) + circ(6, 80, 0.35, ACC, ACC, 0))
    s.append(t(79, 81, "−v is your right; z up", 2.6, "start", 600, INK2))
    s.append("</svg>")
    return "".join(s)
