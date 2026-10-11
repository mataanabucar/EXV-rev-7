#!/usr/bin/env python3
"""EX-MA MINIMAL design (no PVC conduit) — assembly manual page builder.

Built for the materials on hand: 3 x 7/16in OSB 2 x 4 ft panels, 1 x 5/8in particle board 2 x 2 ft (the
sandbox floor, uncut), no shim, and the printed parts as already printed (old lever hubs, old slew spool).

Reuses the first manual's builder (../../2026-10-10-assembly-manual/source/2026-10-10-build-manual.py) for the
page helpers and for the pages that do not change, patching their text where the minimal design differs
(every patch asserts that the text it replaces exists). Pages that change are written here. All numbers
for the minimal design come from the minimal Source tree (made by 2026-10-11-make-minimal-source.py):
panels() for the wood, cable-paths for the ropes and tubes.

Usage: MINIMAL_SRC=<minimal Source dir> <cadenv>/bin/python 2026-10-11-build-minimal-manual.py
then:  node ../../2026-10-10-assembly-manual/source/2026-10-10-manual-print.mjs 2026-10-11-minimal-manual.html \
            ../2026-10-11-ex-ma-minimal-manual.pdf
"""
import copy
import re
import importlib.util
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MAN = HERE.parent
PROJ = MAN.parent
ASRC = PROJ / "2026-10-10-assembly-manual" / "source"
MSRC = Path(os.environ["MINIMAL_SRC"])
IN = 25.4


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


A = _load("manualA", ASRC / "2026-10-10-build-manual.py")      # first manual: helpers + unchanged pages
wc = _load("wc", ASRC / "2026-10-10-wood-cutlist.py")           # cut-list helpers (nesting, drawings)
bx = _load("bxM", MSRC / "2026-09-24-build-box.py")             # minimal geometry
ex = bx.ex
cp = _load("cpM", MSRC / "2026-09-24-cable-paths.py")
sv, esc = A.sv, A.esc


def ii(mm):
    """Inches to the nearest 1/16: 8-1/16″."""
    return _inch(mm).replace(" ", "-")


_inch = wc.inch
wc.inch = ii                                    # board drawings and cut steps use the same format


def iim(mm):
    return f'{ii(mm)} <span class="mm">({mm:.0f} mm)</span>'


# ================================================================ minimal-design data
T = ex.T_WOOD                                   # 7/16in OSB
OSB_SHEET = (48 * IN, 24 * IN)
PB = 24 * IN                                    # particle board 2 x 2 ft, used whole


def panels():
    P = bx.panels()
    for p in P:
        if p.name == "sandbox floor":
            p.lo = (p.lo[0], p.lo[1], ex.GROUND)
            p.hi = (p.lo[0] + PB, p.lo[1] + PB, ex.GROUND + ex.SB_FLOOR_T)
            p.note = "the 5/8″ particle board, used whole"
        if p.name.startswith("axle bearing block") or p.name == "pedestal shelf":
            ax = {"v": 1, "z": 2}[p.normal]                 # these were 12 mm in build-box: now 7/16in OSB
            lo, hi = list(p.lo), list(p.hi)
            hi[ax] = lo[ax] + T
            p.lo, p.hi = tuple(lo), tuple(hi)
        p.holes = [(k, a, c, d, n.replace("2in conduit (seal with silicone)", "tube passage")
                    .replace("2in conduit", "tube passage")
                    .replace("fitting bolt (M3 × 35 through the sandbox wall)", "8-32 through-rod")
                    .replace("fitting bolt (M3 × 25)", "8-32 through-rod")
                    .replace("box-to-sandbox bolt (M3 × 30)", "M3 × 30 corner bolt")
                    .replace("bolt from the control box", "8-32 through-rod" if abs(c[2] - ex.COND_Z) < 45 else "M3 × 30 corner bolt")
                    .replace("slew spool axle (nut + washer in a Ø22 x 7 counterbore from below)",
                             "spool axle; 7/8″ counterbore 9/32″ deep from below")
                    .replace("slew-tube-bushing", "PEX bushing P15"))
                   for k, a, c, d, n in p.holes]
    w = next(p for p in P if p.name.startswith("pedestal wall -u"))
    for k in (1, 2):                                       # spacer frames: pedestal wall -u outline, 100 mm window
        sp = copy.deepcopy(w)
        sp.name, sp.group = f"spacer frame {k}", "spacer"
        u0 = w.lo[0] - k * T
        sp.lo, sp.hi = (u0, w.lo[1], w.lo[2]), (u0 + T, w.hi[1], w.hi[2])
        sp.holes = [("rect", "u", (u0, ex.PED_FIT_V, ex.COND_Z), (wc.WINDOW, wc.WINDOW),
                     "window (3/8″ hole in each corner, then jigsaw)")]
        sp.note = "glued to the pedestal wall −u"
        P.append(sp)
    return P


PANELS = panels()
WID = {p.name: f"W{i + 1:02d}" for i, p in enumerate(PANELS[:21])}
WID.update({"spacer frame 1": "W22", "spacer frame 2": "W23"})
PD = {p.name: p for p in PANELS}

# ropes and PTFE tubes (cable-paths on the minimal tree)
_paths = cp.all_paths()
_rope = {}
_tube = {}
for _n, _e in _paths.items():
    _poly = cp.polyline(_e)
    _rope[_e["circuit"]] = _rope.get(_e["circuit"], 0.0) + float(np.sum(np.linalg.norm(np.diff(_poly, axis=0), axis=1)))
    for _s in _e["ptfe"]:
        _tube[_n] = float(np.sum(np.linalg.norm(np.diff(np.asarray(_s), axis=0), axis=1)))
# first manual: cut length and modelled tube path (2026-09-24 BOM / cable-paths on Source/). The cut keeps the same
# allowance over the modelled path (10 mm trim + the spare length stored as a bow between the fittings).
A_TUBE = {"stick upper tail": (647, 625.9), "stick lower tail": (658, 636.6), "bucket upper tail": (813, 792.2),
          "bucket lower tail": (822, 801.1), "slew rope A": (339, 316.5), "slew rope B": (407, 385.0)}
TUBE = {n: c - (m - _tube[n]) for n, (c, m) in A_TUBE.items()}
ROPE = {c: _rope[c] + 120.0 for c in ("boom", "stick", "bucket")}          # + 2 x 60 mm crimp loops
SLEW = {lane: float(np.sum(np.linalg.norm(np.diff(cp.polyline(_paths[f"slew rope {lane}"]), axis=0), axis=1))) + 60.0
        for lane in ("A", "B")}                                              # + 1 loop
CHAMBER = cp.rt.CONDUIT_RUN                                                  # fitting floor to fitting floor
BOW_R = cp.rt.conduit_helix(10.5)[1]                                         # spare tube bow radius
STACK = 5 * T
ROD_832 = 6 + STACK + 6 + 2 * (3.2 + 2.0)                                     # flanges + stack + nut and thread each end
R205, R274, R145 = 205.0, 274.0, ex.HANDLE_LEN + 5.0

ROPE_CUTS = [("Boom circuit", ROPE["boom"], "boom", "single crimp at the midpoint ({}), loop at each end"),
             ("Stick circuit", ROPE["stick"], "stick", "single crimp at the midpoint ({}), loop at each end"),
             ("Bucket circuit", ROPE["bucket"], "bucket", "single crimp at the midpoint ({}), loop at each end"),
             ("Slew rope A", SLEW["A"], "slew", "single crimp at one end (pedestal drum), loop at the other (spool)"),
             ("Slew rope B", SLEW["B"], "slew", "single crimp at one end (pedestal drum), loop at the other (spool)")]
PTFE_CUTS = [("stick_hi", TUBE["stick upper tail"], "box fitting → stop in the boom tip"),
             ("stick_lo", TUBE["stick lower tail"], "box fitting → stop in the boom tip"),
             ("bucket_hi", TUBE["bucket upper tail"], "box fitting → stop in the stick nose"),
             ("bucket_lo", TUBE["bucket lower tail"], "box fitting → stop in the stick nose"),
             ("slew sleeve A", TUBE["slew rope A"], "post A → pedestal fitting"),
             ("slew sleeve B", TUBE["slew rope B"], "post B → pedestal fitting")]
ROD_CUTS = [("5/16″ rod", R205, 1, "lever axle", "H14"), ("5/16″ rod", R274, 1, "slew spool axle", "H15"),
            ("5/16″ rod", R145, 3, "lever handles", "H16"), ("8-32 threaded rod", ROD_832, 4, "through-rods (box fitting → pedestal fitting)", "H06"),
            ("8-32 threaded rod", 42.0, 2, "boom split pins", "H10"), ("8-32 threaded rod", 22.0, 2, "stick split pins", "H11"),
            ("8-32 threaded rod", 65.0, 1, "bucket pin", "H12"), ("3/4″ PEX-B tube", 120.0, 1, "turret tube", "S06"),
            ("1/2″ copper pipe", 2 * IN, 1, "on the elbow (if your elbow has no leg)", "S07")]

HW = [
    ("H01", "M3 × 10 button head", 8, "rope-tail anchors on the 3 lever hubs (2 each) and the slew spool (2)"),
    ("H02", "M3 × 12 socket head cap", 16, "boom + stick drum key screws (8), retaining ring (8)"),
    ("H03", "M3 × 20 socket head cap", 17, "joining lugs (8), drag clamps (3), handle clamps (3), slew wheel (3)"),
    ("H04", "M3 × 25 socket head cap", 2, "PEX pinch clamps: turret hub (1), slew drum (1)"),
    ("H05", "M3 × 30 socket head cap", 2, "box front to sandbox wall, lower corners"),
    ("H06", f"8-32 threaded rod, {ii(ROD_832)}", 4, "through-rods: box fitting → pedestal fitting (replace the 8 M3 fitting bolts)"),
    ("H07", "M3 hex nut", 37, "with the M3 screws above"),
    ("H08", "M3 flat washer", 20, "corner bolts (4), rope anchors (16)"),
    ("H09", "M3 split-lock washer", 27, "under nuts/heads on moving or clamping joints"),
    ("H10", "8-32 rod, 1-5/8″ (42 mm)", 2, "boom split pins"),
    ("H11", "8-32 rod, 7/8″ (22 mm)", 2, "stick split pins"),
    ("H12", "8-32 rod, 2-9/16″ (65 mm)", 1, "bucket pin"),
    ("H13", "8-32 hex nut", 20, "jam pairs on the pins (12), through-rods (8)"),
    ("H14", f"5/16″ rod, {ii(R205)}", 1, "lever axle"),
    ("H15", f"5/16″ rod, {ii(R274)}", 1, "slew spool axle"),
    ("H16", f"5/16″ rod, {ii(R145)}", 3, "lever handles"),
    ("H17", "5/16″ nut + SAE washer", 4, "2 on the lever axle, 2 on the spool axle"),
    ("H18", "#8 × 1″ flat-head wood screw", 4, "base to the pedestal top"),
    ("H19", "#6 × 3/4″ flat-head wood screw", 14, "bearing blocks (4), riser (3), posts (4), PEX bushing (3)"),
    ("H20", "#6 × 1-1/4″ flat-head wood screw", 121, "panel joints, 4 per edge, with wood glue (120); elbow support (1)"),
]
STOCK = [
    ("S01", "1/16″ galvanized 7×19 wire rope", "5 pieces", " / ".join(ii(x) for x in (ROPE["boom"], ROPE["stick"], ROPE["bucket"], SLEW["A"], SLEW["B"]))),
    ("S02", "1/16″ single crimp sleeve", 5, "3 joint-drum midpoints + 2 slew rope ends"),
    ("S03", "1/16″ double crimp sleeve", 8, "6 arm tail loops + 2 slew loops"),
    ("S04", "PTFE tube 4 mm OD × 2 mm ID", "6 pieces", " / ".join(ii(L) for _, L, _ in PTFE_CUTS)),
    ("S05", "6 mm airsoft BB (or 1/4″ steel ball)", 57, "slewing ring (+ about 5 spare)"),
    ("S06", "3/4″ PEX-B tube", "4-3/4″", "turret tube (turns with the turret)"),
    ("S07", "1/2″ copper 90° sweep elbow + 2″ of pipe", 1, "fixed elbow in the pedestal; deburr both ends"),
    ("S08", "7/16″ OSB, 2 × 4 ft panel", "3 (2 used)", "all panels except the sandbox floor (Stage 2)"),
    ("S09", "5/8″ particle board, 2 × 2 ft", 1, "sandbox floor W17, used whole"),
    ("S10", "Wood glue; CA or epoxy; silicone; cable tie", "—", "panel joints + spacers; ears, knobs, elbow post; spacer seal; elbow"),
]
A.HW, A.STOCK, A.PANELS, A.WID, A.ex = HW, STOCK, PANELS, WID, ex
A.FIGDIR, A.PFX = MAN / "figures", "2026-10-11-"
page, figk, fignum, need, pid, steps, table, tag, box, stagehead = (A.page, A.figk, A.fignum, A.need, A.pid, A.steps,
                                                                       A.table, A.tag, A.box, A.stagehead)
PFX = A.PFX
FIG_KW = {"controls": dict(max_h_in=2.75)}       # figures taller here than in the first manual
_fig_a = A.fig


def _fig(fid, width_in, caption=None, gutter=(1.25, 1.25, 0.2, 0.2), **kw):
    kw.update(FIG_KW.get(fid, {}))
    return _fig_a(fid, width_in, caption, gutter, **kw)


A.fig = fig = _fig


def dims(p):
    return wc.dims(p)


def sz(name):
    a, b = dims(PD[name])
    return f"{ii(a)} × {ii(b)}"


# key positions (design frame -> distances a builder can measure)
BOX_W, BOX_D, BOX_H = ex.BOX_V[1] - ex.BOX_V[0], ex.BOX_U[1] - ex.BOX_U[0], ex.BOX_Z[1] - ex.BOX_Z[0]
SB_H = 40.0 - ex.GROUND
PED_H = 0.0 - ex.PED_Z[0]
FLOOR_TOP = ex.BOX_Z[0] + T                     # box floor top
KNOB_TOP = ex.AXLE_Z + ex.HANDLE_LEN + 16.0
WHEEL_Z = (49.0, 61.0)
POSTS = {"A": (-329.0 + (ex.AXLE_U + 360.0), -120.0), "B": (-274.0 + (ex.AXLE_U + 360.0), -216.0)}
ELBOW_U = -50.0


INCH_RE = re.compile(r">([^<]*)<")              # text between tags: 5/16in -> 5/16″ (the first manual's style)


def reuse(fn, subs=(), remap=True):
    """Run a page function of the first manual, then patch its text. Every old string must be found."""
    n0 = len(A.PAGES)
    fn()
    new = A.PAGES[n0:]
    for old, rep in subs:
        hit = False
        for p in new:
            if old in p["body"]:
                p["body"] = p["body"].replace(old, rep)
                hit = True
        assert hit, f"{fn.__name__}: text not found: {old[:70]}"
    if remap:                                  # appendix letters: C -> B (rope reference), D -> C (open items)
        for p in new:
            p["body"] = p["body"].replace("Appendix C", "Appendix @B").replace("Appendix D", "Appendix C").replace("Appendix @B", "Appendix B")
            p["body"] = p["body"].replace("Open item 6", "Open item @8").replace("Open item 7", "Open item 6").replace("Open item @8", "Open item 8")


# ================================================================ COVER
def cover():
    band = "".join(f'<span style="background:{c}"></span>' for c in (sv.CIRC["boom"], sv.CIRC["stick"], sv.CIRC["bucket"], sv.CIRC["slew"]))
    body = f'''
<div class="band">{band}</div>
<div class="brand">
  <div class="kicker">Assembly &amp; configuration manual · minimal build</div>
  <div class="title">EX-MA <em>cable</em><br>excavator</div>
  <div class="subtitle">Minimal design · no PVC conduit · 7/16″ OSB + 5/8″ particle board</div>
  <div class="pills"><span style="background:{sv.CIRC["boom"]}">Boom</span><span style="background:{sv.CIRC["stick"]}">Stick</span>
  <span style="background:{sv.CIRC["bucket"]}">Bucket</span><span style="background:{sv.CIRC["slew"]}">Slew</span></div>
</div>
<div class="hero"><img src="../figures/{PFX}cover.png" style="width:100%"></div>
<div class="meta">
  <div class="blk"><b>Edition</b> 2026-10-11 · minimal design, for the project files in <span class="mono">2026-09-24-EX-MA-simplified/</span><br>
  <b>Cut sizes in inches</b> for 3 × 7/16″ OSB 2 × 4 ft + 1 × 5/8″ particle board 2 × 2 ft · illustrations rendered from the minimal CAD</div>
  <div class="blk" style="text-align:right"><b>26 printed part types · 29 prints</b><br>23 wood pieces · 4 rope circuits · no electronics</div>
</div>'''
    page(body, cls="cover bleed")


def contents_placeholder():
    page("@@TOC@@", tab="Contents", right="EX-MA minimal build", toc=[])


# ================================================================ INTRODUCTION
def about():
    body = f'''
<div class="kicker">Before you begin</div><h1>About this manual</h1>
<p class="lead">This manual builds the <b>minimal</b> EX-MA: the same arm, turret, levers and rope circuits as the full design, but with no 2″ PVC
conduit. The pedestal stands right against the sandbox wall on two OSB spacer frames, and four 8-32 rods clamp the box, the wall, the spacers and the
pedestal together. Everything is sized for the boards you have. Work through the stages in order.</p>
<div class="row">
 <div class="col">
  <h3>How the pages work</h3>
  <ul class="tight">
   <li><b>Stage header</b>: the stage number and what it achieves.</li>
   <li><b>You need</b>: every part and fastener for that stage, with its ID ({pid("P05")} printed, {pid("W01")} wood,
   {pid("H03")} hardware, {pid("S04")} stock) and quantity. Lay them out first.</li>
   <li><b>Numbered steps</b>: do them in order; each step is one action.</li>
   <li><b>Figures</b>: numbered balloons <span class="ball">1</span> match the list under the figure.
   <span style="color:var(--accent);font-weight:700">Orange arrows</span> show where a part moves to.</li>
   <li><b>Check</b> boxes: stop and verify before going on.</li>
  </ul>
  <h3>Units</h3>
  <p><b>Everything you cut or drill is given in inches</b>, to the nearest 1/16″: wood, rods, rope, PTFE tube, PEX and copper, and every hole
  position. Small grey millimetres follow where the CAD value helps. Printed-part details (M3 screws, Ø60 drums, “3 mm below”) stay metric, as
  in the project files.</p>
  <h3>Directions used everywhere</h3>
  <ul class="tight"><li><b>+u</b> points away from you at the control box, toward the sandbox (“forward”).</li>
  <li><b>+v</b> points to your left; <b>−v</b> to your right. <b>z</b> points up.</li></ul>
 </div>
 <div class="col">{sv.conventions_svg()}
 <h3>Verified, derived or assumed?</h3>
 <table class="t compact"><tr><th style="width:0.9in">Tag</th><th>Meaning</th></tr>
 <tr><td>{tag("v")}</td><td>Read from the minimal CAD model, its build scripts or the project reports.</td></tr>
 <tr><td>{tag("d")}</td><td>Worked out from the model geometry for this manual; the reasoning is given next to it.</td></tr>
 <tr><td>{tag("a")}</td><td>Not in the project files: general practice or a choice you can change.</td></tr>
 <tr><td>{tag("o")}</td><td>A conflict or gap in the design files. Appendix C lists them with options.</td></tr></table>
 </div>
</div>
<h3>Symbols</h3>
<div class="row">
 <div class="col">
  {box("warn", "Warning", "Risk of injury. Read before doing the step.")}
  {box("caut", "Caution", "Risk of damaging a part or having to take things apart again.")}
  {box("mistake", "Common mistake", "Something that is easy to get wrong at this point.")}
 </div>
 <div class="col">
  {box("check", "Check", "A verification point. Do not continue until it passes.")}
  {box("tip", "Tip", "Practical advice. Helpful, but not taken from the CAD model.")}
  {box("open", "Open item", "A question found in the design files that you must decide on.")}
 </div>
</div>
<p class="small">Colours in the illustrations code the part type: <span class="swatch" style="background:#f2a65a"></span>printed
PLA+ <span class="swatch" style="background:#f2cf5b"></span>arm shell (PETG) <span class="swatch" style="background:#5b8fd1"></span>bucket ears
<span class="swatch" style="background:#4a5562"></span>original EX-MA dark parts <span class="swatch" style="background:#d9b783"></span>OSB
<span class="swatch" style="background:#e2a96b"></span>spacer frames <span class="swatch" style="background:#cbb894"></span>particle board
<span class="swatch" style="background:#b4bcc4"></span>metal. Ropes: <span class="swatch" style="background:var(--boom)"></span>boom
<span class="swatch" style="background:var(--stick)"></span>stick <span class="swatch" style="background:var(--bucket)"></span>bucket
<span class="swatch" style="background:var(--slew)"></span>slew. Parts fitted in earlier steps are light grey.</p>
'''
    page(body, tab="Introduction", right="About this manual", toc=[(1, "Introduction"), (2, "About this manual")])


def safety():
    body = f'''
<div class="kicker">Read first</div><h1>Safety and good practice</h1>
<p class="lead">The EX-MA is hand-powered: no motors, springs or electrics. The hazards are the tools you build it with, cut wire rope, small
parts, and pinch points between moving printed parts.</p>
<div class="row"><div class="col">
{box("warn", "Cut wire rope is sharp.", " Each cut end of 7×19 rope splays into fine, stiff wires that puncture skin. Wrap tape round the rope "
     "before cutting and cut through the tape; wear gloves and eye protection.")}
{box("warn", "Small parts.", " The 6 mm BBs, M3 and 8-32 nuts and crimp sleeves are choking hazards. Keep the build area and the finished model "
     "away from small children.")}
{box("warn", "Pinch points.", " The slewing ring, the lever hubs and every joint drum can trap fingers while ropes are tensioned. Keep fingers "
     "out of the box and the pedestal while someone moves a lever or the wheel.")}
{box("warn", "Saws, jigsaws and drills.", " Clamp OSB and particle board before cutting or drilling; support both sides of a cut so the "
     "blade does not bind. OSB and particle-board dust is fine wood dust with resin: cut outdoors or with dust extraction, and wear a dust mask.")}
</div><div class="col">
{box("caut", "Adhesives.", " CA glue bonds skin in seconds. Use it with ventilation. Follow the maker’s cure times for wood glue, CA, epoxy and "
     "silicone; the spacer seal needs its silicone cured before Stage 7.")}
{box("caut", "Heat.", " Printed PLA+ softens well below the temperature of a car interior in summer. Do not leave the model in direct sun or "
     "in a hot vehicle. " + tag("a"))}
{box("caut", "Do not force a joint.", " Every lever has a hard stop at the end of its slot in the box top. If a lever or the wheel resists before "
     "reaching a stop, find the cause (page “Troubleshooting”) instead of pushing harder.")}
{box("caut", "Sand and particle board.", " Particle board swells and crumbles if it gets wet. Seal the floor (Stage 3), keep the sand dry and "
     "keep it below the pedestal top. " + tag("a"))}
</div></div>
<h3>Workspace</h3>
<ul class="tight"><li>A flat table about 4 × 2-1/2 ft; good light (rope holes are Ø2.4 mm).</li>
<li>Saw horses or a bench for breaking down the 2 × 4 ft OSB panels; a straight edge or a fence for the rip cuts.</li>
<li>Small trays or bags for hardware: one per stage. Masking tape and a fine marker for labelling every piece.</li></ul>
<h3>Before you start</h3>
<table class="t compact">
<tr><td style="width:18px">☐</td><td>Read the whole manual once, including Appendix C (open items). Decide items 1–5 before the stage they affect.</td></tr>
<tr><td>☐</td><td>Check your 5/16″ rod: threaded or smooth (Open item 4), and that you have about 3-1/8 ft of it (Stage 2).</td></tr>
<tr><td>☐</td><td>Check the hardware against Appendix A and the actual-size drawings in “Parts identification”.</td></tr>
<tr><td>☐</td><td>Have at least 25 ft of rope, a 5 m (16 ft) roll of PTFE tube, 57 BBs plus spares, the crimp sleeves and 22 8-32 nuts.</td></tr>
<tr><td>☐</td><td>Your printed parts are used as printed: old lever hubs, old slew spool, elbow support (its base plate is sawn off in Stage 4).</td></tr></table>
'''
    page(body, tab="Introduction", right="Safety", toc=[(2, "Safety and good practice")])


# ================================================================ OVERVIEW
def overview():
    legend = [(1, "Boom lever"), (2, "Stick lever"), (3, "Bucket lever"), (4, "Slew wheel"), (5, "Control box (OSB)"),
              (6, "Removable box top: the lever slots are the end stops"), (7, "Pedestal, against the sandbox wall on two spacer frames"),
              (8, "Base with the printed slewing ring (57 BBs)"), (9, "Tower (turret)"), (10, "Boom"), (11, "Stick"), (12, "Bucket"),
              (13, "Sandbox, 24″ × 24″")]
    lg = "".join(f'<tr><td style="width:22px"><span class="ball">{n}</span></td><td>{t_}</td></tr>' for n, t_ in legend)
    body = f'''
<div class="kicker">System overview</div><h1>What you are building</h1>
<p class="lead">Three levers and a wheel on a wooden control box drive the EX-MA arm through wire ropes. Each control moves exactly one
motion: <b style="color:var(--boom)">boom</b>, <b style="color:var(--stick)">stick</b>, <b style="color:var(--bucket)">bucket</b> or
<b style="color:var(--slew)">slew</b>. The ropes leave the box through a printed fitting, cross a short chamber inside the sandbox wall and two
spacer frames, enter the pedestal and run up the turret’s centre tube and along the arm.</p>
{fig("overview", 7.3, "The complete minimal machine as modelled (joints at their modelled pose, the near sandbox wall see-through).",
     gutter=(0.3, 0.3, 0.3, 0.2), legend=True, max_h_in=4.6, key_cols=0)}
<div class="row"><div class="col"><table class="t compact">{lg}</table></div>
<div class="col">
<h3 class="mt0">Main dimensions {tag("v")}</h3>
<table class="t compact">
<tr><td>Sandbox (outside, floor included)</td><td class="n">24″ × 24″ × {ii(SB_H)}</td></tr>
<tr><td>Control box (outside, deep × wide × high)</td><td class="n">{ii(BOX_D)} × {ii(BOX_W)} × {ii(BOX_H)}</td></tr>
<tr><td>Pedestal (outside)</td><td class="n">{ii(ex.PED_U[1] - ex.PED_U[0])} × {ii(ex.PED_V[1] - ex.PED_V[0])} × {ii(PED_H)}</td></tr>
<tr><td>Overall length, box rear to sandbox far wall</td><td class="n">{ii(ex.SB_U[1] - ex.BOX_U[0])}</td></tr>
<tr><td>Knob tops / slew wheel top above the table</td><td class="n">{ii(KNOB_TOP - ex.GROUND)} / {ii(WHEEL_Z[1] - ex.GROUND)}</td></tr>
<tr><td>Base / slewing ring; boom / stick pin to pin</td><td class="n">Ø140 mm; 209 / 175 mm</td></tr>
</table>
<p class="small">Box and sandbox both stand on the table; no shim. The box is {ii(BOX_W)} wide because the lever hubs and slew spool are kept as
printed (Appendix D).</p>
</div></div>'''
    page(body, tab="Overview", right="System overview", toc=[(1, "System overview"), (2, "What you are building")])


def how_it_works():
    lengths = dict(boom=f"rope {ii(ROPE['boom'])}, bare (no tube)", stick=f"rope {ii(ROPE['stick'])} in 2 PTFE tubes",
                   bucket=f"rope {ii(ROPE['bucket'])} in 2 PTFE tubes", slew=f"{ii(SLEW['A'])} + {ii(SLEW['B'])}")
    circ = sv.circuits_svg(lengths).replace(">2IN CONDUIT<", ">CHAMBER<")
    assert ">CHAMBER<" in circ
    body = f'''
<div class="kicker">System overview</div><h1>How it works</h1>
<p class="lead">Every circuit is a <b>pull-pull loop</b>: one rope, anchored on two drums. Turning the control drum pulls one strand and lets out
the other by the same amount, so the joint drum, and the joint, turns. Nothing else is connected to that rope, so each control moves only
its own joint.</p>
<div class="figframe" style="padding:4px 8px;width:5.6in;margin:0 auto">{circ}</div>
<div class="cap" style="margin-bottom:8px"><b>Fig. {fignum()}</b><span>Rope circuits (the “wiring diagram” of this machine). Each lever drives a Ø60
drum on the common lever axle; the slew wheel drives a Ø110 two-lane spool. Lengths are the cut lengths for the minimal build.</span></div>
{fig("system-cutaway", 7.3, "Every rope as modelled, from its control to its joint (cut through the middle; built pose).",
     gutter=(1.05, 1.0, 0.15, 0.3), max_h_in=1.85)}
<div class="row"><div class="col">
<h4>The spacer chamber replaces the conduit</h4>
<p>Between the box fitting and the pedestal fitting the ropes and tubes cross a {ii(CHAMBER)} chamber: the holes in the box front, the sandbox wall and
the pedestal wall, and the windows in the two spacer frames, sealed on all sides. The stick and bucket tubes keep their spare length there as a
gentle bow (radius about {ii(BOW_R)}, more than the 5/8″ minimum). {tag("d")}</p>
</div><div class="col">
<h4>Why the stick and bucket ropes run in PTFE tubes</h4>
<p>Their ropes cross the boom joint (the bucket ropes the stick joint too). Inside a tube anchored at the box fitting and at a stop in the arm,
the rope length does not change when another joint moves. The tubes cross each joint through the pivot axis (the pins are split in two for
this). The slew drum sits in the pedestal on the 3/4″ PEX turret tube. {tag("v")}</p>
</div></div>'''
    page(body, tab="Overview", right="How it works", toc=[(2, "How it works")])


def at_a_glance():
    st = [(1, "Print & check", "29 prints on 7 plates (already printed: check them)"),
          (2, "Cut, drill & label", "OSB boards, rods, rope, PTFE; label every piece"),
          (3, "Sandbox", "particle-board floor + 4 OSB walls"), (4, "Pedestal", "walls, spacers, fitting + rods, elbow, shelf"),
          (5, "Slewing ring & turret", "base, PEX tube, BBs, turret, ring, slew drum"),
          (6, "Control box", "carcass, lever axle + hubs, spool, posts"),
          (7, "Tubes & box mounting", "4 PTFE tubes, box onto the rods"),
          (8, "Arm", "drums, ropes at the joint end, halves, pins, bucket"),
          (9, "Arm ropes at the levers", "zero pose, loops on anchors, tension"),
          (10, "Slew ropes", "sleeves, drum pockets, spool anchors"),
          (11, "Top, handles, wheel", "top panel, handles, knobs, wheel"),
          (12, "Test & configure", "ranges, coupling, tension, friction")]
    cards = "".join(f'<div class="st"><div class="n">{n:02d}</div><div class="nm">{a}</div><div class="d">{b}</div><div class="pg">@@P:stage{n}@@</div></div>'
                    for n, a, b in st)
    body = f'''
<div class="kicker">Planning</div><h1>Build at a glance</h1>
<p class="lead">Twelve stages. Stages 1 and 2 are preparation; 3–8 build the machine; 9–12 rig, adjust and test it.</p>
<div class="flow">{cards}</div>
<h3>What is different in the minimal build {tag("d")}</h3>
<ul class="tight">
<li><b>No conduit.</b> The pedestal stands against the sandbox wall on two glued-on OSB spacer frames (W22, W23). Four 8-32 rods run from the box
fitting (P18) to the pedestal fitting (P17) and clamp the whole stack; they replace the 8 M3 fitting bolts.</li>
<li><b>Your boards.</b> 7/16″ OSB for every panel except the sandbox floor, which is the 5/8″ particle board used whole. With no shim, the sandbox and
pedestal walls are cut 5/32″ shorter so the turret and fittings stay at their design heights, and the elbow support loses its base plate.</li>
<li><b>Compact box with your prints.</b> {ii(BOX_D)} deep, {ii(BOX_H)} high, {ii(BOX_W)} wide (old hubs at 2-3/4″ spacing, old spool);
handles {ii(R145)}; the slew wheel sits {ii(WHEEL_Z[0] - ex.BOX_Z[1])} above the lid.</li>
<li><b>Order.</b> The rods go into the pedestal in Stage 4; the tubes are seated in P18 and the box goes onto the rods in Stage 7. The lever axle goes in
before the left box side; the joint end of each arm rope is rigged while its arm half is open.</li></ul>
<h3>Open items to decide before you start {tag("o")}</h3>
<table class="t compact"><tr><th>#</th><th>Item</th><th>Affects</th></tr>
<tr><td>1</td><td>Stick-drum key screws: two M3 × 12 enter each through-hole from opposite sides and their tips overlap by 1.6 mm.</td><td>Stage 8</td></tr>
<tr><td>2</td><td>Stick joining lugs 1 and 2 at the stick root are 2.9 mm apart: their holes merge, so only one screw fits there.</td><td>Stage 8</td></tr>
<tr><td>3</td><td>Joining-lug screws cannot be reached once a boom or stick is closed.</td><td>Stage 8</td></tr>
<tr><td>4</td><td>5/16″ nuts on the axles need threaded rod ends; one design note calls the rod “smooth”.</td><td>Stages 2, 6, 11</td></tr>
<tr><td>5</td><td>Pedestal-to-floor screws are not counted in the bill of materials.</td><td>Stage 4</td></tr>
<tr><td>6</td><td>Rope tension: the checklist says slide the anchors “outward”; the geometry says inward.</td><td>Stages 9, 10</td></tr>
<tr><td>7</td><td>Bucket knob to slew-wheel rim clearance is only 5/8″ with the kept spool.</td><td>Stage 11</td></tr></table>'''
    page(body, tab="Planning", right="Build at a glance", toc=[(2, "Build at a glance")])


def tools():
    body = f'''
<div class="kicker">Planning</div><h1>Tools and supplies</h1>
<p class="lead">From the project checklist {tag("v")}, with the wood tools for your boards. Everything else is in the bill of materials (Appendix A).</p>
<div class="row"><div class="col">
<h3>Hand tools</h3>
<table class="t compact">
<tr><td>2.5 mm hex key</td><td>M3 socket head cap screws</td></tr>
<tr><td>2 mm hex key</td><td>M3 button head screws (rope anchors)</td></tr>
<tr><td>5.5 mm wrench or nut driver</td><td>M3 nuts</td></tr>
<tr><td>11/32″ wrench (×2)</td><td>8-32 nuts: jam pairs and through-rods</td></tr>
<tr><td>1/2″ wrench</td><td>5/16″ nuts on the axles</td></tr>
<tr><td>Screwdriver (Phillips)</td><td>#6 and #8 wood screws</td></tr>
<tr><td>Crimp tool for 1/16″ sleeves</td><td>single and double crimp sleeves</td></tr>
<tr><td>Wire-rope cutter</td><td>1/16″ 7×19 rope</td></tr>
<tr><td>PTFE tube cutter or new razor blade</td><td>cut square</td></tr>
<tr><td>Hacksaw + metal file</td><td>5/16″ rod, 8-32 rod, copper; deburr every end</td></tr>
<tr><td>Tape measure, square, straight edge</td><td>marking out the boards (1/16″ marks)</td></tr>
</table></div><div class="col">
<h3>Power tools and consumables</h3>
<table class="t compact">
<tr><td>Circular saw (or table saw) + fence</td><td>rip and crosscut the OSB; 1/8″ kerf assumed</td></tr>
<tr><td>Jigsaw</td><td>the two spacer windows; slot ends</td></tr>
<tr><td>Drill + bits</td><td>2-7/16″ hole saw; 1-1/4″ and 1″ spade or Forstner; 7/8″ Forstner; 3/8″, 11/32″, 3/16″, 1/8″, 3/32″</td></tr>
<tr><td>Wood glue</td><td>every panel joint; spacers to the pedestal wall</td></tr>
<tr><td>CA or epoxy</td><td>bucket ears; knobs; elbow-support post</td></tr>
<tr><td>Silicone</td><td>spacer seal against the sandbox wall</td></tr>
<tr><td>Sealer (paint, poly or thinned glue)</td><td>particle-board floor, all faces and edges {tag("a")}</td></tr>
<tr><td>Cable tie (1)</td><td>copper elbow to its support</td></tr>
<tr><td>Masking tape + fine marker</td><td>label every piece</td></tr>
</table></div></div>
<h3>Hardware bags by stage {tag("v")}</h3>
{table(["Stage", "Fasteners and stock to bag"], [
    ("3 Sandbox", "32 × #6 × 1-1/4″"),
    ("4 Pedestal", f"41 × #6 × 1-1/4″; 3 × #6 × 3/4″; 4 × 8-32 rod {ii(ROD_832)} + 8 × 8-32 nut; copper elbow; cable tie; glue; silicone"),
    ("5 Slewing ring", "4 × #8 × 1″; 8 × M3 × 12; 2 × M3 × 25; 10 split-lock washers; 10 M3 nuts; 57 BBs; PEX tube"),
    ("6 Control box", f"32 × #6 × 1-1/4″; 11 × #6 × 3/4″; 5/16″ rods {ii(R205)} + {ii(R274)}; 3 × 5/16″ nut + washer"),
    ("7 Tubes + box", "4 arm PTFE tubes; 2 × M3 × 30; 4 flat washers; 2 M3 nuts (the rod nuts are in the Stage 4 bag)"),
    ("8 Arm", "8 × M3 × 12 (or M3 × 8, Open item 1); 8 × M3 × 20 + 8 nuts; 8-32 rods 2 × 1-5/8″, 2 × 7/8″, 1 × 2-9/16″; 12 × 8-32 nuts; 3 single crimps"),
    ("9 Arm ropes", "6 × M3 × 10 button head; 12 flat washers; 6 split-lock washers; 6 nuts; 6 double crimps"),
    ("10 Slew ropes", "2 × M3 × 10 button head; 4 flat washers; 2 split-lock washers; 2 nuts; 2 single + 2 double crimps; 2 sleeves"),
    ("11 Top", f"16 × #6 × 1-1/4″; 9 × M3 × 20; 9 split-lock washers; 9 nuts; 3 handle rods {ii(R145)}; 1 × 5/16″ nut + washer")], cls="t compact")}'''
    page(body, tab="Planning", right="Tools and supplies", toc=[(2, "Tools and supplies")])


# ================================================================ PARTS
def hardware_pages():
    W = 184
    s = [f'<svg viewBox="0 0 {W} 128" width="{W}mm" height="128mm">']
    s.append(sv.t(2, 5, "M3 SCREWS — HEAD UP, ACTUAL SIZE", 3.4, "start", 700, sv.INK2, "Barlow"))
    x = 10
    for L, kind, idn, q in ((10, "b", "H01", 8), (12, "s", "H02", 16), (20, "s", "H03", 17), (25, "s", "H04", 2), (30, "s", "H05", 2)):
        s.append(sv.button_head(x, 10, L) if kind == "b" else sv.socket_cap(x, 10, L))
        s.append(sv.t(x, 58, f"M3 × {L}", 3.0, "middle", 700))
        s.append(sv.t(x, 61.8, "button head" if kind == "b" else "socket cap", 2.5, "middle", 500, sv.INK2))
        s.append(sv.t(x, 65.6, f"{idn} · ×{q}", 2.6, "middle", 700, sv.ACC))
        x += 17
    s.append(sv.line(4, 13, 4, 13 + 35, sv.INK3, 0.2))
    s.append(sv.t(3, 50, "length is measured under the head", 2.2, "start", 500, sv.INK3, extra='transform="rotate(-90 3 50)"'))
    x0 = 118
    s.append(sv.t(x0 - 4, 5, "M3 NUT AND WASHERS", 3.4, "start", 700, sv.INK2, "Barlow"))
    for k, (draw, nm, idn, q) in enumerate(((sv.nut(x0 + 4, 16, 5.5, 3.0), "M3 nut", "H07", 37),
                                            (sv.ring(x0 + 22, 16, 7.0, 3.2), "flat washer", "H08", 20),
                                            (sv.ring(x0 + 40, 16, 6.2, 3.1, split=True), "split-lock", "H09", 27))):
        s.append(draw)
        cx = x0 + 4 + 18 * k
        s.append(sv.t(cx, 26, nm, 2.6, "middle", 700) + sv.t(cx, 29.6, f"{idn} · ×{q}", 2.6, "middle", 700, sv.ACC))
    s.append(sv.t(96, 38, "8-32 ROD AND NUT (HILLMAN)", 3.4, "start", 700, sv.INK2, "Barlow"))
    y = 46
    for L, idn, q, what in ((22, "H11", 2, "7/8″ · stick split pin"), (42, "H10", 2, "1-5/8″ · boom split pin"),
                            (65, "H12", 1, "2-9/16″ · bucket pin"), (ROD_832, "H06", 4, f"{ii(ROD_832)} · through-rod")):
        s.append(sv.rod(100, y, L, 4.17))
        s.append(sv.t(100, y - 3.2, f"{what} · {idn} ×{q}", 2.5, "start", 600))
        y += 9
    s.append(sv.nut(158, 47, 11 / 32 * 25.4, 4.2) + sv.t(164, 48, "8-32 nut", 2.6, "start", 700) + sv.t(164, 51.5, "H13 ×20", 2.6, "start", 700, sv.ACC))
    s.append(sv.t(2, 75, "WOOD SCREWS (FLAT HEAD)", 3.4, "start", 700, sv.INK2, "Barlow"))
    xw = 10
    for L, d, hd, nm, idn, q in ((19.05, 3.5, 6.65, "#6 × 3/4″", "H19", 14), (31.75, 3.5, 6.65, "#6 × 1-1/4″", "H20", 121),
                                 (25.4, 4.17, 8.0, "#8 × 1″", "H18", 4)):
        s.append(sv.wood_screw(xw, 80, L, d, hd))
        s.append(sv.t(xw + 6, 90, nm, 2.8, "start", 700) + sv.t(xw + 6, 93.6, f"{idn} · ×{q}", 2.6, "start", 700, sv.ACC))
        xw += 30
    s.append(sv.t(100, 84, "5/16″ NUT AND WASHER", 3.4, "start", 700, sv.INK2, "Barlow"))
    s.append(sv.nut(110, 99, 12.7, 8.0) + sv.ring(132, 99, 17.46, 8.73))
    s.append(sv.t(121, 113, "H17 · ×4 each (axle ends)", 2.6, "middle", 700, sv.ACC))
    s.append(sv.t(150, 84, "STOCK (ACTUAL SIZE)", 3.4, "start", 700, sv.INK2, "Barlow"))
    s.append(sv.circ(154, 93, 3.0, "#f6f2e6", sv.INK, 0.25) + sv.t(159, 94, "6 mm BB", 2.6, "start", 700))
    s.append(sv.ring(154, 103, 4.0, 2.0, "#ffffff") + sv.t(159, 104, "PTFE tube, end", 2.6, "start", 700))
    s.append(sv.circ(154, 111, 0.8, sv.STEEL, sv.INK, 0.2) + sv.t(159, 112, "rope 1/16″", 2.6, "start", 700))
    s.append(sv.rect(151.85, 116, 4.3, 6.4, sv.STEEL, sv.INK, 0.2, 0.6) + sv.t(159, 120, "crimp (nominal)", 2.6, "start", 700))
    s.append(sv.line(2, 125, 2 + 4 * 25.4, 125, sv.INK, 0.35) + "".join(sv.line(2 + 25.4 * k, 123.2, 2 + 25.4 * k, 126.8, sv.INK, 0.3) for k in range(5))
             + "".join(sv.line(2 + 6.35 * k, 124.2, 2 + 6.35 * k, 125.8, sv.INK, 0.2) for k in range(17)))
    s.append(sv.t(106, 126, "4 inches: measure this to check the print is at 100 %", 2.6, "start", 600, sv.INK2))
    s.append("</svg>")
    body = f'''
<div class="kicker">Parts identification</div><h1>Hardware at actual size</h1>
<p class="lead">Print this page at 100 % (no “fit to page”) and lay each screw or rod on its drawing to identify it. The scale bar at the bottom must
measure 4″. {tag("v")}</p>
<div class="hw11">{"".join(s)}</div>
<div class="row mt8"><div class="col">
<img src="../figures/{PFX}photo-m3-kit.jpg" style="width:100%;height:1.75in;object-fit:cover;border-radius:3px"><div class="cap"><b>Photo</b><span>Your M3 kit (Fgruh, 2300 pc):
socket head caps and button heads in 4–35 mm, nuts, flat and split-lock washers.</span></div>
</div><div class="col">
<img src="../figures/{PFX}photo-hillman.jpg" style="width:100%;height:1.75in;object-fit:cover;object-position:50% 30%;border-radius:3px"><div class="cap"><b>Photo</b><span>Your Hillman parts: 3 ft of 8-32
threaded rod and 22 hex nuts. The minimal build uses about 20″ of the rod and 20 nuts.</span></div>
</div><div class="col">
{box("mistake", "M3 × 12 vs M3 × 20.", " They look alike in the bag. Lay them on the drawing above before each step.")}
{box("note", "Wood screws", " are your own stock. Flat-head #6 and #8 are drawn; pan heads will not sit flush in the printed counterbores. " + tag("a"))}
</div></div>'''
    page(body, tab="Parts", right="Hardware at actual size", toc=[(1, "Parts identification"), (2, "Hardware at actual size")])


def wood_page():
    groups = {}
    for p in PANELS:
        groups.setdefault(p.group, []).append(p)
    gname = {"control-box": "Control box", "pedestal": "Pedestal", "sandbox": "Sandbox", "spacer": "Spacer frames"}
    rows = [(gname[g], ", ".join(WID[p.name] for p in ps), str(len(ps)), f"{sum(dims(p)[0] * dims(p)[1] for p in ps) / 645.16:.0f}")
            for g, ps in groups.items()]
    body = f'''
<div class="kicker">Parts identification</div><h1>Boards, wood pieces and stock</h1>
<p class="lead">23 wood pieces from the boards you have. Every size is worked out from the minimal CAD model for 7/16″ OSB and the 5/8″ particle
board {tag("v")}; cut sizes, board layouts and hole positions are all in Stage 2.</p>
<div class="row"><div class="col">
<h3 class="mt0">Your boards</h3>
<table class="t compact"><tr><th>Board</th><th class="n">Qty</th><th>Use</th></tr>
<tr><td><b>7/16″ OSB, 2 × 4 ft</b></td><td class="n">3</td><td>2 boards cut into 22 pieces; the 3rd is spare</td></tr>
<tr><td><b>5/8″ particle board, 2 × 2 ft</b></td><td class="n">1</td><td>sandbox floor W17, used whole (no cuts)</td></tr></table>
</div><div class="col">
<h3 class="mt0">Wood pieces by group</h3>
{table(["Group", "IDs", "Pieces", "sq in"], rows, cls="t compact", num=(2, 3))}
</div></div>
<h3>Stock items</h3>
{table(["ID", "Item", "Qty / length", "Used for"], [(pid(a), b, c, d) for a, b, c, d in STOCK], cls="t compact")}
{box("note", "IDs", " W01–W21 are the same pieces as in the full-design manual; W22 and W23 are the spacer frames that replace the conduit. "
     "Pencil the ID on every piece as you cut it.")}'''
    page(body, tab="Parts", right="Boards and stock", toc=[(2, "Boards, wood pieces and stock")])


# ================================================================ STAGE 2: CUT, DRILL, LABEL
def stage_cut():
    rope_rows = [(f'<span class="swatch" style="background:var(--{c})"></span>{n}', f"<b>{ii(L)}</b>", how.format(ii(L / 2)))
                 for n, L, c, how in ROPE_CUTS]
    tube_rows = [(n, f"<b>{ii(L)}</b>", w) for n, L, w in PTFE_CUTS]
    rod_rows = [(s, f"<b>{(str(q) + ' × ') if q > 1 else ''}{ii(L)}</b>", f"{w} ({i})") for s, L, q, w, i in ROD_CUTS]
    rope_tot = sum(L for _, L, _, _ in ROPE_CUTS)
    tube_tot = sum(L for _, L, _ in PTFE_CUTS)
    r516 = R205 + R274 + 3 * R145
    r832 = 4 * ROD_832 + 2 * 42 + 2 * 22 + 65
    body = f'''{stagehead(2, "Cut, drill and label", "Boards, rods, rope and tube, all in inches. Label every piece the moment it is cut.")}
<div class="row"><div class="col">
<h3 class="mt0">Wire rope, 1/16″ 7×19 {tag("d")}</h3>
{table(["Piece", "Cut", "Ends"], rope_rows, num=(1,))}
<p class="small">Each includes 2-3/8″ per crimp loop. Total {ii(rope_tot)} ({rope_tot / 304.8:.1f} ft). Cut 3/4″ long if unsure and trim when you crimp.</p>
<h3>PTFE tube, 4 × 2 mm {tag("d")}</h3>
{table(["Piece", "Cut", "Runs"], tube_rows, num=(1,))}
<p class="small">Each includes 3/8″ to trim at fitting. Total {ii(tube_tot)} ({tube_tot / 304.8:.1f} ft).</p>
</div><div class="col">
<h3 class="mt0">Rods, tube and pipe {tag("v")}</h3>
{table(["Stock", "Cut", "For"], rod_rows, num=(1,))}
<p class="small">5/16″ rod total {ii(r516)} plus 4 saw cuts: a 3 ft rod is about 1/4″ short, so buy 4 ft. 8-32 total {ii(r832)} from your
3 ft Hillman rod.</p>
{steps(["Cut all rope and PTFE pieces. Wrap tape round the rope at the cut mark and cut through the tape.",
        "Write the piece name on a tape flag at <b>both</b> ends of every rope and tube (e.g. “STICK — box end”).",
        "On the three arm ropes, mark the midpoint with a second colour.",
        "Cut the rods square; file a small chamfer on each end. Run a nut on and off each 8-32 piece to clean the thread.",
        "Cut the PEX and copper square and deburr inside and out: a burr will cut a rope."], 0)}
</div></div>
{box("warn", "Rope ends.", " Tape every cut end until it is crimped. Loose wires go through skin easily.")}
{box("open", "Open item 4: axle nuts.", f" The {ii(R205)} lever axle and the {ii(R274)} spool axle carry 5/16″ nuts. If your 5/16″ rod is smooth, "
     "thread about 5/8″ at each end of those two rods with a 5/16-18 die, or use 5/16″ shaft collars.")}'''
    page(body, tab="Stage 2", right="Cut, drill and label (1/7)", toc=[(2, "Stage 2 — Cut, drill and label")], stage=2)

    # cut list
    osb = [p for p in PANELS if p.name != "sandbox floor"]
    osb_area = sum(dims(p)[0] * dims(p)[1] for p in osb) / 645.16
    sheets = wc.pack_sheets([(WID[p.name], *dims(p)) for p in osb], OSB_SHEET)
    idcol = {WID[p.name]: wc.GROUP_COL[p.group] for p in PANELS}
    body = f'''<h2>Stage 2 — continued: cut list</h2>
<div class="kpis"><div><b>Particle board</b><span>sandbox floor W17: the whole 24″ × 24″ panel, no cuts</span></div>
<div><b>{len(sheets)} OSB boards</b><span>22 pieces, {osb_area:.0f} sq in ({osb_area / (len(sheets) * 1152) * 100:.0f} % of the {len(sheets)} boards)</span></div>
<div><b>1 OSB board spare</b><span>keep it for re-cuts</span></div></div>
<p>Sizes for 7/16″ OSB, worked out from the minimal CAD panels {tag("v")}. Tick each piece as you cut it, pencil its ID on it and draw an arrow to
its <b>bottom</b> edge (holes are measured from it).</p>
{wc.cut_table(PANELS, WID).replace("2in conduit", "tube passage")}
<p class="small">Walls of the sandbox and the pedestal are 5/32″ shorter than the full design: the 5/8″ floor stands on the table with no shim,
so the turret and both fittings stay at their design heights. {tag("d")}</p>'''
    page(body, tab="Stage 2", right="Cut list (2/7)")

    lays = []
    for k, st in enumerate(sheets):
        wc.SKIPPED.clear()
        svg_ = wc.sheet_svg(st, OSB_SHEET, idcol, width_in=7.0)
        small = (f'<p class="small">Thin strips not labelled on the drawing: {", ".join(sorted(set(wc.SKIPPED)))}; see the cut order.</p>'
                 if wc.SKIPPED else "")
        lays.append(f'<div class="sheet"><div class="sh">OSB board {k + 1} — 2 × 4 ft, 7/16″</div>{svg_}{small}{wc.cut_steps(st)}</div>')
    pb = (f'<div class="sheet"><div class="sh">Particle board — 2 × 2 ft, 5/8″ · and OSB board {len(sheets) + 1}</div>'
          '<div class="row"><div class="col"><svg viewBox="-6 -10 120 116" width="2.0in" font-family="Inter">'
          '<rect x="0" y="0" width="100" height="100" fill="#cbb894" stroke="#1d232b" stroke-width="0.8"/>'
          '<text x="50" y="48" text-anchor="middle" font-size="11" font-weight="800" font-family="Barlow">W17</text>'
          '<text x="50" y="60" text-anchor="middle" font-size="6.5" fill="#4a5562">sandbox floor, uncut</text>'
          '<text x="50" y="-3" text-anchor="middle" font-size="7" font-weight="700" fill="#4a5562">24″</text>'
          '<text x="104" y="50" font-size="7" font-weight="700" fill="#4a5562" transform="rotate(90 104 50)" text-anchor="middle">24″</text></svg></div>'
          '<div class="col w70"><p><b>W17 sandbox floor:</b> use the whole particle-board panel, no cuts. The design is 1/64″ bigger; that does '
          'not matter. Seal both faces and all edges before you build on it (Stage 3).</p>'
          f'<p><b>OSB board {len(sheets) + 1}:</b> not needed. Keep it for a re-cut.</p></div></div></div>')
    lays[-1] += pb
    for k, lay in enumerate(lays):
        page(f'<h2>Stage 2 — continued: board layouts{" (continued)" if k else ""}</h2>'
             + ('<p>Rip the strips first (orange dashed lines, R1, R2 …), then crosscut each strip. Drawn to scale with a 1/8″ kerf; grey is '
                'offcut. After the crosscut, trim any piece that is narrower than its strip to its cut-list size.</p>'
                + box("tip", "Cleats W15 and W16.", " A 7/16″ × 7/16″ stick is too thin to rip safely on its own. Rip it off the edge of a "
                      "wider offcut with a push stick, or use any square stick at least 7/16″ thick. " + tag("a")) if not k else "") + lay,
             tab="Stage 2", right=f"Board layouts ({3 + k}/7)")

    drilled, seen = [], {}
    for p in PANELS:
        if not p.holes:
            continue
        ax = [i for i in range(3) if "uvz"[i] != p.normal]
        key = (dims(p), tuple((k, d if k == "hole" else tuple(d), round(c[ax[0]] - p.lo[ax[0]], 1), round(c[ax[1]] - p.lo[ax[1]], 1))
                              for k, _, c, d, _ in p.holes))
        if key in seen:
            seen[key][1].append(WID[p.name])
            continue
        seen[key] = (p, [WID[p.name]])
        drilled.append(seen[key])
    cards = []
    for p, wids in drilled:
        c = wc.drill_card(p, " + ".join(wids))
        if len(wids) > 1:
            nm = {"axle bearing block left": "axle bearing blocks", "spacer frame 1": "spacer frames"}.get(p.name, p.name)
            c = c.replace(f"</span> {esc(p.name)}</div>", f"</span> {esc(nm)} <span class=mm>(×{len(wids)}, identical)</span></div>", 1)
        cards.append(c)
    npg = math.ceil(len(cards) / 4)
    for k in range(0, len(cards), 4):
        intro = ("" if k else
                 "<p>Measure <b>a</b> along the bottom edge and <b>b</b> up the side, from the lower-left corner as drawn. The bold size is the "
                 "drill bit. Clamp a scrap under OSB so the holes do not tear out.</p>")
        tail = ""
        grid = cards[k:k + 4]
        if k == 0:
            w02, w18 = PD["box front"], PD["sandbox wall -u (box side)"]
            dv, dz = w02.lo[1] - w18.lo[1], w18.lo[2] - w02.lo[2]
            tail = box("caut", "Drill the box front W02 through the sandbox wall W18.", " Their four rod holes and two corner holes must line up, "
                       f"but the panels are not the same size. Drill W18 from its card. Clamp W02 on it face to face, W02’s −v end {ii(dv)} in from "
                       f"W18’s −v end and W02’s bottom edge {ii(dz)} below W18’s (the two 2-7/16″ holes then line up), and drill the six 3/16″ "
                       "holes through W18’s holes into W02. " + tag("d"))
        if len(grid) < 4:
            grid.append('<div class="dcard"><div class="dh">Drilling tips ' + tag("a") + '</div><ul class="tight" style="font-size:8pt">'
                        "<li><b>Clean holes in OSB:</b> clamp a scrap under the panel, or drill until the point shows and finish from the other side.</li>"
                        "<li><b>2-7/16″ holes:</b> hole saw with its pilot; cut halfway from each face.</li>"
                        "<li><b>Lever slots (W06):</b> drill a 23/64″ hole at each end position given, saw or jigsaw the two sides between them, "
                        "file smooth. The handle must run end to end without catching: the slot ends are the lever stops.</li>"
                        "<li><b>Spacer windows (W22, W23):</b> mark the square, drill a 3/8″ hole inside each corner, jigsaw between them. Slightly "
                        "big is fine; never smaller.</li>"
                        "<li><b>Counterbore under the box floor (W01):</b> 7/8″ Forstner 9/32″ deep first, then the 11/32″ hole through its centre.</li>"
                        "</ul></div>")
        page(f'<h2>Stage 2 — continued: drilling{" (continued)" if k else ""}</h2>{intro}<div class="dgrid">{"".join(grid)}</div>{tail}',
             tab="Stage 2", right=f"Drilling ({3 + len(lays) + k // 4}/{2 + len(lays) + npg})")
    return len(lays) + npg


# ================================================================ STAGE 3 SANDBOX
def stage_sandbox():
    w18 = PD["sandbox wall -u (box side)"]
    hole = next(h for h in w18.holes if h[3] > 50)
    a = hole[2][1] - w18.lo[1]
    b = hole[2][2] - w18.lo[2]
    body = f'''{stagehead(3, "Build the sandbox", "Particle-board floor and four OSB walls, glued and screwed. The −u wall is the drilled one: the control box bolts to its outside.")}
<div class="row"><div class="fc">{figk("sandbox-exploded", 4.45, "Sandbox: four walls on the floor.", max_h_in=4.0)}</div>
<div class="fc">{figk("sandbox-corner", 2.65, "Corner joint, walls see-through.", kc=1, max_h_in=4.0)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("W17"), "Floor, 5/8″ particle board 24″ × 24″", 1), (pid("W18"), f"Wall −u (drilled), {sz('sandbox wall -u (box side)')}", 1),
       (pid("W19"), f"Wall +u, {sz('sandbox wall +u')}", 1), (pid("W20"), f"Wall −v, {sz('sandbox wall -v')}", 1),
       (pid("W21"), f"Wall +v, {sz('sandbox wall +v')}", 1), (pid("H20"), "#6 × 1-1/4″ wood screw", 32), ("", "Wood glue; floor sealer", "")])}
</div><div class="col">
{steps(["Seal the particle board on both faces and all four edges and let it dry. " + tag("a"),
        "Glue and screw the four walls <b>on top of</b> the floor: 4 screws up through the floor into each wall’s bottom edge. Drill a 3/32″ pilot "
        "for every screw into an OSB edge, and keep screws 1/2″ from the corners.",
        "The −v and +v walls fit between the −u and +u walls: 4 screws through each ±u wall into the ends of the ±v walls.",
        f"Put the −u wall’s holes at the bottom: the 2-7/16″ hole centre is {ii(b)} above the wall’s bottom edge and {ii(a)} from its −v end "
        "(operator’s right). " + tag("v"),
        "Check the box is square (equal diagonals) before the glue sets."])}
</div></div>
{box("check", "Check.", f" Walls flush with the floor edges; diagonals equal within 1/16″; walls {ii(SB_H - ex.SB_FLOOR_T)} tall, so the rim is "
     f"{ii(SB_H)} above the table.")}
{box("mistake", "Hole side.", f" Fitting the −u wall upside down puts the big hole near the top. The hole is {ii(b)} from the <b>bottom</b>.")}'''
    page(body, tab="Stage 3", right="Sandbox", toc=[(2, "Stage 3 — Sandbox")], stage=3)


# ================================================================ STAGE 4 PEDESTAL
def stage_pedestal():
    rod_in = 2 + 3.2 + 6 + T                        # rod end -> outer face of the pedestal wall (pedestal side)
    out_sp = ROD_832 - rod_in - 2 * T               # past the spacers' outer face
    out_wall = out_sp - T                           # past the outside of the sandbox wall
    cleat_h = PD["pedestal shelf cleat -v"].lo[2] - ex.PED_Z[0]
    body = f'''{stagehead(4, "Build the pedestal", "An OSB column that stands against the sandbox wall on two spacer frames. It carries the slewing ring on top and the slew drum inside.")}
{figk("pedestal-exploded", 7.3, "Pedestal walls and top. Wall +u is screwed only: it is the service hatch.", kc=3, max_h_in=4.3)}
<div class="row"><div class="col w40">
{need([(pid("W09"), f"Pedestal top, {sz('pedestal top')}", 1), (pid("W10"), f"Wall −u (drilled), {sz('pedestal wall -u (conduit)')}", 1),
       (pid("W11"), f"Wall +u (removable), {sz('pedestal wall +u (removable access)')}", 1), (pid("W12"), f"Wall −v, {sz('pedestal wall -v')}", 1),
       (pid("W13"), f"Wall +v, {sz('pedestal wall +v')}", 1), (pid("H20"), "#6 × 1-1/4″ wood screw", 32)])}
</div><div class="col">
{steps(["Glue and screw walls −v and +v between walls −u and +u (4 screws per joint, through the ±u walls, 3/32″ pilots). Fit wall +u "
        "<b>with screws only, no glue</b>.",
        "Glue and screw the top onto the four walls (4 screws per wall). The top’s 1″ hole is the PEX clearance; its four 1/8″ holes are pilots for "
        "the base screws.",
        "Build the pedestal on the bench, not in the sandbox: the spacers and the rods go on first (next page). The figure shows it in its "
        "final place."])}
{box("check", "Check.", f" The pedestal is {ii(PED_H)} tall and its top is flat and square to the walls. Wall −u has a 2-7/16″ hole and four "
     "3/16″ holes around it.")}
</div></div>'''
    page(body, tab="Stage 4", right="Pedestal (1/3)", toc=[(2, "Stage 4 — Pedestal")], stage=4)

    body = f'''<h2>Stage 4 — continued: spacer frames, pedestal fitting and through-rods</h2>
<div class="row"><div class="fc">{figk("spacer-stack", 3.55, "The stack that replaces the conduit (cut through the middle).", kc=1, max_h_in=3.3)}</div>
<div class="fc">{figk("pedestal-fitting", 3.55, "P17 on wall −u with the four rods, from inside the pedestal.", kc=1, max_h_in=3.3)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("W22"), "Spacer frame 1", 1), (pid("W23"), "Spacer frame 2", 1), ("", "Wood glue", ""), (pid("P17"), "Pedestal conduit fitting", 1),
       (pid("H06"), f"8-32 rod, {ii(ROD_832)}", 4), (pid("H13"), "8-32 nut", 4)], "You need (this page)")}
{box("note", "Why spacers.", f" Two 7/16″ frames fill the gap the conduit used to cross. Their {ii(wc.WINDOW)} windows, with the holes in the "
     f"walls, make a sealed {ii(CHAMBER)} chamber between the two fittings. " + tag("d"))}
</div><div class="col">
{steps(["Glue the two spacer frames to the <b>outside</b> of wall −u, one on the other, edges flush with the wall’s edges, windows lined up. "
        "The four 3/16″ holes and the 2-7/16″ hole must all be clear inside the window. Clamp until set.",
        "From inside the pedestal, hold P17’s square flange flat against wall −u: the big socket faces the wall’s hole; the round boss, with the "
        "small copper socket in its end, points into the pedestal. Line up its four corner holes with the wall’s.",
        f"Push a {ii(ROD_832)} 8-32 rod through each corner: P17’s flange, the wall, then out through the spacer window. Run an 8-32 nut onto the "
        f"inner end until about 1/16″ of thread shows past it, and snug it against the flange. Each rod now sticks out {ii(out_sp)} past the "
        "spacers.",
        "Keep the four 8-32 nuts for the box side in this stage’s bag (Stage 7)."], 3)}
{box("mistake", "Fitting turned round.", " If the big socket faces into the pedestal, the copper socket faces the wall and the tubes cannot reach "
     "the turret.")}
</div></div>'''
    page(body, tab="Stage 4", right="Pedestal (2/3)")

    body = f'''<h2>Stage 4 — continued: into the sandbox, copper elbow, shelf</h2>
<div class="row"><div class="fc">{figk("pedestal-elbow", 3.55, "Copper elbow on the sawn elbow support.", kc=1, max_h_in=2.05)}</div>
<div class="fc">{figk("pedestal-shelf", 3.55, "Cleats, shelf and PEX bushing (shelf and bushing lifted out).", kc=2, max_h_in=2.05)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("S07"), "1/2″ copper elbow + pipe", 1), (pid("P16"), "Elbow support (base plate sawn off)", 1),
       (pid("H20"), "#6 × 1-1/4″ (elbow support)", 1), ("", "Silicone; CA or epoxy; cable tie", ""), (pid("W14"), "Shelf", 1),
       (pid("W15"), "Shelf cleat −v", 1), (pid("W16"), "Shelf cleat +v", 1), (pid("H20"), "#6 × 1-1/4″ (cleats)", 8),
       (pid("P15"), "PEX bushing", 1), (pid("H19"), "#6 × 3/4″ (bushing)", 3)], "You need (this page)")}
</div><div class="col">
{steps(["Run a bead of silicone round the outer face of the outer spacer, just outside its window. Stand the pedestal on the sandbox floor and slide "
        "it against the −u wall so the four rods pass through the wall’s 3/16″ holes. The rods stick out "
        f"{ii(out_wall)} outside the sandbox. Fit a nut finger-tight on each to hold the pedestal while the silicone cures (they come off again in "
        "Stage 7).",
        "Saw the 5/32″ base plate off the elbow support, flush with its post. Push the copper elbow’s horizontal leg into P17’s copper socket; the "
        "other leg points straight up.",
        f"Stand the post under the horizontal leg (about {ii(ELBOW_U - (ex.PED_U[0] + T))} in from the inside of wall −u), mark its centre on the floor, drill a 1/8″ "
        "pilot through the floor there, and fix it with one #6 × 1-1/4″ up from below plus a few drops of CA. Cable-tie the elbow into the saddle.",
        f"Screw the cleats to the inside of walls −v and +v, their tops {ii(cleat_h)} above the sandbox floor. Lay the shelf on them and screw the "
        "PEX bushing into the shelf hole, flange on top."], 6)}
{box("check", "Check.", " The elbow’s top opening is directly under the bushing’s bore (sight down through it). The copper does not move when "
     "pulled. No light shows between the outer spacer and the sandbox wall. " + tag("v"))}
</div></div>
{box("open", "Open item 5: fixing the pedestal down.", " The rods clamp the pedestal to the sandbox wall once the box is on (Stage 7). For a firmer "
     "base, add 4 × #6 × 1-1/4″ up through the floor into the ±v walls, 2 each (not in the bill of materials). " + tag("a"))}'''
    page(body, tab="Stage 4", right="Pedestal (3/3)")


# ================================================================ STAGE 6 CONTROL BOX
def stage_box():
    front = PD["box front"]
    big = next(h for h in front.holes if h[3] > 50)
    a_r = big[2][1] - ex.BOX_V[0]
    a_l = ex.BOX_V[1] - big[2][1]
    b_f = big[2][2] - FLOOR_TOP
    body = f'''{stagehead(6, "Build the control box", "Box carcass, lever axle with its three hubs, the slew spool and the two sleeve posts. The left side and the top go on later.")}
{figk("box-exploded", 7.3, "Control box panels.", kc=4, max_h_in=4.5)}
<div class="row"><div class="col w45">
{need([(pid("W01"), f"Box floor, {sz('box floor')}", 1), (pid("W02"), f"Box front (drilled), {sz('box front')}", 1), (pid("W03"), f"Box rear, {sz('box rear')}", 1),
       (pid("W04"), f"Box right side, {sz('box right side')}", 1), (pid("W05"), "Box left side (later in this stage)", 1),
       (pid("H20"), "#6 × 1-1/4″ wood screw", 32), ("", "Wood glue", "")])}
</div><div class="col">
{steps(["Glue and screw the front, rear and right side onto the floor (4 screws per edge, up through the floor, 3/32″ pilots).",
        "Join the front and rear to the right side (4 screws per joint, through the front and rear).",
        f"The front’s 2-7/16″ hole is low (centre {ii(b_f)} above the floor’s top face) and right of centre: {ii(a_r)} from the box’s right-hand (−v) "
        f"outside face, {ii(a_l)} from its left. " + tag("v"),
        "Leave the left side and the top off for now."])}
{box("caut", "Box size.", f" With the hubs and spool you already printed, the box is {ii(BOX_D)} deep, {ii(BOX_W)} wide and {ii(BOX_H)} high "
     "outside. " + tag("v"))}
</div></div>'''
    page(body, tab="Stage 6", right="Control box (1/3)", toc=[(2, "Stage 6 — Control box")], stage=6)


def _box_pages_2_3():
    """Pages 2 and 3 of the first manual's Stage 6 (its page 1 is replaced above)."""
    n0 = len(A.PAGES)
    A.FIG_N[0] -= 1                             # its page-1 figure reuses the number of ours, then is dropped
    A.stage_box()
    del A.PAGES[n0]                             # drop the first manual's page 1
    p2, p3 = A.PAGES[n0], A.PAGES[n0 + 1]
    blk = PD["axle bearing block left"]
    sub2 = [("5/16in rod, 205 mm", f"5/16″ rod, {ii(R205)}"),
            ("Centre the rod (102.5 mm each side of the middle)", f"Centre the rod ({ii(R205 / 2)} each side of the middle)"),
            ("axle 93 mm from the floor’s rear (−u) edge, left block’s outer face 22.5 mm in from the floor’s left (+v) edge. Screw each block from below: 2 × #6 × 3/4in.",
             f"axle {ii(ex.AXLE_U - ex.BOX_U[0])} from the floor’s rear (−u) edge, left block’s outer face {ii(ex.BOX_V[1] - blk.hi[1])} in from the floor’s "
             "left (+v) edge. Screw each block from below: 2 × #6 × 3/4″ (1/8″ pilots in the block edge)."),
            ("#6 × 3/4in wood screw", "#6 × 3/4″ wood screw")]
    sub3 = [("5/16in rod, 274 mm", f"5/16″ rod, {ii(R274)}"),
            ("Push the 274 mm rod up through the floor’s Ø8.5 hole from below. Fit a washer and a nut on its bottom end inside the Ø22 × 7 counterbore",
             f"Push the {ii(R274)} rod up through the floor’s 11/32″ hole from below. Fit a washer and a nut on its bottom end inside the 7/8″ × 9/32″ counterbore"),
            ("come from the model: post A at u −329, v −120; post B at u −274, v −216 (design frame).",
             f"come from the model. Centres, from the floor’s rear (−u) edge and right (−v) edge: post A {ii(POSTS['A'][0] - ex.BOX_U[0])} / "
             f"{ii(POSTS['A'][1] - ex.BOX_V[0])}, post B {ii(POSTS['B'][0] - ex.BOX_U[0])} / {ii(POSTS['B'][1] - ex.BOX_V[0])}."),
            ("#6 × 3/4in wood screw", "#6 × 3/4″ wood screw"),
            ("it goes in at Stage 7, together with the PTFE tubes", "it goes in at Stage 7, together with the PTFE tubes and the rods")]
    for p, subs in ((p2, sub2), (p3, sub3)):
        for old, new in subs:
            assert old in p["body"], old[:60]
            p["body"] = p["body"].replace(old, new)


# ================================================================ STAGE 7 TUBES AND BOX
def stage_mount():
    body = f'''{stagehead(7, "PTFE tubes and box mounting", "The four arm tubes are seated in the box fitting and threaded through the spacer chamber to the turret; then the box goes onto the rods.")}
<div class="row"><div class="fc">{figk("tube-window", 3.2, "Box fitting P18 from the sandbox side, with the tube and rope paths.", kc=1, max_h_in=3.6)}</div>
<div class="fc">{figk("ptfe-route", 3.9, "Where the four arm tubes run when finished.", kc=1, max_h_in=3.6)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("P18"), "Box conduit fitting", 1), (pid("S04"), "PTFE: stick_hi, stick_lo, bucket_hi, bucket_lo", 4)])}
{box("note", "Why this order.", " The tubes stop in P18 on its sandbox side, and P18 is clamped against the box front by the rod nuts. Once those "
     "nuts are on, the window cannot be reached. " + tag("d"))}
</div><div class="col">
{steps(["Take the four temporary nuts off the rods outside the sandbox wall (the silicone must have cured).",
        "Seat the box end of the four arm tubes in P18’s rounded window from the <b>socket side</b> (the side with the big round recess). They sit "
        "side by side and stop on the window floor.",
        "Stand the box a little way from the sandbox (top off) and hold P18 inside it behind the front. Feed the four free tube ends out through "
        "the box front’s 2-7/16″ hole, through the sandbox wall’s hole, across the spacer chamber, through P17’s window, into the copper elbow "
        "and up the PEX tube until they come out at the top of the turret.",
        "Slide the box up to the sandbox wall: the four rods pass through the box front’s 3/16″ holes. Slip P18 over the rod ends inside the box, "
        "socket toward the box front, and push it flat against the front while you take up the tube slack at the turret."])}
</div></div>'''
    page(body, tab="Stage 7", right="Tubes and box mounting (1/2)", toc=[(2, "Stage 7 — PTFE tubes and box mounting")], stage=7)
    body = f'''<h2>Stage 7 — continued: nuts, corner bolts, seal</h2>
{figk("box-mount", 7.3, "Box against the sandbox wall: four through-rods and two corner bolts (box top, left side and sandbox walls hidden).", kc=2, max_h_in=3.5)}
<div class="row"><div class="col">
{need([(pid("H13"), "8-32 nut (from the Stage 4 bag)", 4), (pid("H05"), "M3 × 30 socket cap", 2), (pid("H08"), "M3 flat washer", 4),
       (pid("H07"), "M3 nut", 2)], "You need (this page)")}
{steps(["Run an 8-32 nut onto each rod end on P18’s flange. Tighten the four in turn, a little at a time, holding the nut on the pedestal side "
        "with the second wrench (reach in through the pedestal’s +u hatch). The stack closes up: P18, box front, sandbox wall, spacers, "
        "pedestal wall, P17.",
        "Fit the two lower-corner bolts: M3 × 30 through the box front and the sandbox wall, flat washers both sides, nut inside the sandbox.",
        "At the turret, pull the four tubes up gently and leave them hanging out of the top for Stage 8. Their spare length bows inside the spacer "
        "chamber."], 4)}
</div><div class="col">
{box("check", "Check.", " Each tube slides a little when pushed at the turret end and does not come out of P18’s window when pulled. The box "
     "stands flat on the same table as the sandbox; the pedestal does not move when pushed. " + tag("v"))}
{box("caut", "Do not over-tighten the rods.", " The nuts bear on printed flanges. Snug plus a quarter turn is enough; crushing the OSB or cracking "
     "a flange breaks the seal. " + tag("a"))}
{box("tip", "Sand seal.", " If you see daylight round the outer spacer from inside the sandbox, run a second bead of silicone into the corner "
     "between the spacer and the wall.")}
</div></div>'''
    page(body, tab="Stage 7", right="Tubes and box mounting (2/2)")


# ================================================================ APPENDICES
def app_cuts():
    rows = [("Boom rope", ROPE["boom"], f"{ROPE['boom'] - 120:.0f} + 2 × 60 loops"), ("Stick rope", ROPE["stick"], f"{ROPE['stick'] - 120:.0f} + 2 × 60"),
            ("Bucket rope", ROPE["bucket"], f"{ROPE['bucket'] - 120:.0f} + 2 × 60"), ("Slew rope A", SLEW["A"], f"{SLEW['A'] - 60:.0f} + 60"),
            ("Slew rope B", SLEW["B"], f"{SLEW['B'] - 60:.0f} + 60")]
    rows += [(f"PTFE {n}", L, f"{_tube[k]:.0f} + {L - _tube[k]:.0f} spare and trim") for (n, L, _), k in
             zip(PTFE_CUTS, ("stick upper tail", "stick lower tail", "bucket upper tail", "bucket lower tail", "slew rope A", "slew rope B"))]
    body = f'''<div class="kicker">Appendix B</div><h1>Rope, tube and rod reference</h1>
<div class="row"><div class="col">
<h3 class="mt0">Cut lengths {tag("d")}</h3>
{table(["Piece", "Cut", "mm", "Modelled path (mm)"], [(a, f"<b>{ii(L)}</b>", f"{L:.0f}", c) for a, L, c in rows], num=(1, 2))}
<p class="small">Paths from <span class="mono">cable-paths.py</span> on the minimal model. Each tube keeps the same allowance over its path as in the
full design: 3/8″ to trim plus the spare length that bows in the chamber.</p>
</div><div class="col">
<h3 class="mt0">The stack, box to pedestal {tag("d")}</h3>
{table(["Layer", "Thickness"], [("P18 flange (box fitting)", "6 mm"), ("Box front W02", "7/16″"), ("Sandbox wall W18", "7/16″"),
                               ("Spacer frames W22 + W23", "7/8″"), ("Pedestal wall W10", "7/16″"), ("P17 flange (pedestal fitting)", "6 mm"),
                               ("Rod: stack + a nut and 1/16″ of thread each end", f"<b>{ii(ROD_832)}</b>")], num=(1,))}
<p class="small">Chamber between the fitting floors: {ii(CHAMBER)}; spare-tube bow radius about {ii(BOW_R)} (5/8″ minimum).</p>
<h3>Rope travel per circuit {tag("v")}</h3>
{table(["Circuit", "Range", "Rope travel per side", "Control"], [("Boom", "85°", "22.3 mm", "lever 42°"), ("Stick", "95°", "21.6 mm", "lever 41°"),
                                                               ("Bucket", "140°", "20.8 mm", "lever 40°"), ("Slew", "180°", "172.8 mm", "wheel 180°")])}
<h3>Slew wrap {tag("v")}</h3>
{table(["Slew", "Rope A spool / pedestal", "Rope B spool / pedestal"], [("−90°", "90° / 270°", "270° / 90°"), ("0°", "180° / 180°", "180° / 180°"),
                                                                     ("+90°", "270° / 90°", "90° / 270°")])}
</div></div>'''
    page(body, tab="Appendix B", right="Rope, tube and rod reference", toc=[(2, "B — Rope, tube and rod reference")])


def app_open():
    items = [
        ("1", "Stick-drum key screws collide",
         "The stick drum is 10 mm thick and each key pilot runs right through it. The hardware model puts an M3 × 12 into each pilot from each side; "
         "the two tips overlap by 1.6 mm.",
         "Use M3 × 8 socket caps on the stick drum (in your kit), or grind 2 mm off each M3 × 12."),
        ("2", "Stick root lugs overlap",
         "Joining lugs 1 and 2 of the stick are 2.9 mm apart, so their holes merge and their screws and nuts overlap.",
         "Fit one M3 × 20 in that lug; the stick then has 3 lug screws (1 spare)."),
        ("3", "Joining-lug screws are enclosed",
         "On both members every lug screw head sits inside the closed shell, and the outer walls have no access hole on the screw axis.",
         "Decide before Stage 8: (a) drill a small access hole on each lug axis; (b) close the halves without lug screws, held with tape or dots of "
         "CA along the seam; (c) add access in the CAD and reprint the halves."),
        ("4", "5/16″ axle ends",
         "Both axles carry 5/16″ nuts. One design note calls the rod “smooth”.",
         "Threaded rod: nothing changes. Smooth rod: thread the ends with a 5/16-18 die or use 5/16″ shaft collars."),
        ("5", "Pedestal not screwed to the floor",
         "The cut list says the pedestal screws to the sandbox floor, but no screws are counted. In the minimal build the four rods clamp it to the "
         "sandbox wall.",
         "Optional: 4 extra #6 × 1-1/4″ up through the floor into the ±v walls (Stage 4)."),
        ("6", "Tension direction",
         "The checklist says to slide the rope anchors “outward”. In the CAD the rope enters each slot at its outer end, so the strand tightens as "
         "the screw moves inward.",
         "Slide toward the drum centre (Stages 9 and 10)."),
        ("7", "Bucket knob near the slew wheel",
         f"With the kept 145 mm spool the wheel sits {ii(WHEEL_Z[0] - ex.BOX_Z[1])} above the lid. At the bucket lever’s end of travel its knob "
         "comes within 15.5 mm (5/8″) of the wheel rim; the full design had 24 mm.",
         "Works as is; mind your knuckles on the bucket lever. A reprinted short spool (compact spec) would lower the wheel."),
        ("8", "Slicer plates hold the old base and ears",
         "Plates 4 and 6 of the PLA+ project were made before the 2026-09-29 rebuilds.",
         "If you have not printed P09, P10 and P12 yet, use the 2026-09-29 STL files (Stage 1)."),
    ]
    rows = [(n, f"<b>{t_}</b><br>{w}", fix) for n, t_, w, fix in items]
    body = f'''<div class="kicker">Appendix C</div><h1>Open items and verification</h1>
<p class="lead">Found by checking the project’s CAD and hardware model. Items 1–6 and 8 are in the project files as they are; item 7 comes from
the minimal build with your prints. Each needs your decision. {tag("o")}</p>
{table(["#", "What the files show", "Options"], rows)}
<h3>What was verified for the minimal build, and how</h3>
<table class="t compact">
<tr><td>Geometry</td><td>A copy of the project sources with the minimal constants (7/16″ OSB, 5/8″ floor, no shim, spacers, compact box with the
kept prints) rebuilt every panel, placement and rope path. Illustrations are rendered from it.</td></tr>
<tr><td>Interference</td><td>Every pair of parts and fasteners checked against the full design. The only new contact is the elbow support on the
floor, which is intended. The left corner bolt was moved 5/16″ left to clear the spacers.</td></tr>
<tr><td>Not verified</td><td>Physical fit of real prints, OSB and particle-board screw holding, glue strength, rope friction. Items tagged
{tag("a")} are general practice.</td></tr></table>'''
    page(body, tab="Appendix C", right="Open items and verification", toc=[(2, "C — Open items and verification")])


def app_diff():
    rows = [("Box to pedestal", "141 mm of 2″ PVC conduit across an 81 mm gap", f"no conduit: 2 OSB spacer frames, {ii(CHAMBER)} chamber"),
            ("Fitting fasteners", "4 × M3 × 35 (box), 4 × M3 × 25 (pedestal)", f"4 × 8-32 rod {ii(ROD_832)}, nut each end"),
            ("Wood", "12 mm plywood, 21 panels", "7/16″ OSB (22 pieces) + 5/8″ particle-board floor"),
            ("Shim under the box", "none needed (12 mm floor)", "none: walls 5/32″ shorter instead"),
            ("Sandbox", "610 × 610 × 242 mm", f"24″ × 24″ × {ii(SB_H)}"),
            ("Pedestal", "200 × 180 × 190 mm", f"{ii(ex.PED_U[1] - ex.PED_U[0])} × {ii(ex.PED_V[1] - ex.PED_V[0])} × {ii(PED_H)}"),
            ("Control box", "250 × 405 × 242 mm", f"{ii(BOX_D)} × {ii(BOX_W)} × {ii(BOX_H)}"),
            ("Lever handles", "230 mm rod", f"{ii(R145)} rod"),
            ("Lever slots", "133 / 129 / 124 mm", "66 / 64 / 62 mm (same swing, shorter lever)"),
            ("Slew wheel", "on the lid", f"{ii(WHEEL_Z[0] - ex.BOX_Z[1])} above the lid (spool kept)"),
            ("Elbow support", "as printed", "base plate sawn off; 1 screw from below"),
            ("Arm ropes", "1384 / 1821 / 2173 mm", " / ".join(ii(ROPE[c]) for c in ("boom", "stick", "bucket"))),
            ("PTFE + sleeves", "3.7 m", f"{ii(sum(L for _, L, _ in PTFE_CUTS))}"),
            ("Hardware IDs", "H06 = M3 × 35", "H06 = 8-32 through-rod; H04 2 pcs; nuts 37; flat washers 20"),
            ("Printed parts", "26 types, 29 prints", "the same files, as printed")]
    body = f'''<div class="kicker">Appendix D</div><h1>Differences from the full design</h1>
<p class="lead">What the minimal build changes, compared with the first manual (2026-10-10). Arm, turret, slewing ring, drums, fittings and every
printed part are the same. {tag("v")}</p>
{table(["", "Full design (2026-10-10 manual)", "Minimal build (this manual)"], rows)}
<div class="row"><div class="col">{box("note", "Same printed parts.", " P17 and P18 are still called “conduit fittings”: their big sockets now open "
     "into the spacer chamber instead of holding the PVC. Nothing is reprinted.")}</div>
<div class="col">{box("caut", "Do not mix the manuals’ cut sizes.", " Every wood size, rope, tube and rod length in this manual is for the minimal "
     "build with your boards. The first manual’s millimetre sizes are for 12 mm plywood and the conduit.")}</div></div>'''
    page(body, tab="Appendix D", right="Differences from the full design", toc=[(2, "D — Differences from the full design")])


def app_files():
    body = f'''<div class="kicker">Appendix E</div><h1>Files and revision</h1>
<div class="row"><div class="col">
<h3 class="mt0">Project files used</h3>
<table class="t compact">
<tr><td class="mono">STL/</td><td>printed parts (P01–P26), print-ready</td></tr>
<tr><td class="mono">Source/</td><td>build scripts; parameters in <span class="mono">2026-09-24-exma_common.py</span></td></tr>
<tr><td class="mono">Validation/</td><td>box, kinematics and wall-thickness reports</td></tr>
<tr><td class="mono">2026-09-24-bill-of-materials.md</td><td>quantities, plates, materials</td></tr>
<tr><td class="mono">2026-09-28-compact-control-box-spec.md</td><td>compact box depth and height</td></tr>
<tr><td class="mono">2026-10-10-assembly-manual/</td><td>first manual: renderer, page helpers, styles</td></tr>
<tr><td class="mono">2026-10-11-ex-ma-cut-plan-your-boards.pdf</td><td>earlier cut plan (compact 14-1/4″ box): superseded by Stage 2 here</td></tr></table>
<h3>Revision</h3>
{table(["Date", "Change"], [("2026-10-11", "First edition of the minimal-build manual.")])}
</div><div class="col">
<h3 class="mt0">This manual’s source (2026-10-11-minimal-manual/)</h3>
<table class="t compact">
<tr><td class="mono">source/2026-10-11-make-minimal-source.py</td><td>minimal copy of Source/ (constants + 3 patches)</td></tr>
<tr><td class="mono">source/2026-10-11-minimal-scene-export.py</td><td>geometry → scene for the renderer</td></tr>
<tr><td class="mono">source/2026-10-11-minimal-figure-specs.py</td><td>cameras, callouts, exploded offsets</td></tr>
<tr><td class="mono">source/2026-10-11-build-minimal-manual.py</td><td>text, cut plan and page layout</td></tr>
<tr><td class="mono">source/2026-10-11-build-minimal-manual.sh</td><td>runs the whole chain</td></tr>
<tr><td class="mono">figures/</td><td>rendered figures + callout data</td></tr></table>
<p class="small">The renderer, figure runner, overlay helpers, styles and PDF printer are shared with the first manual
(<span class="mono">2026-10-10-assembly-manual/source/</span>).</p>
</div></div>'''
    page(body, tab="Appendix E", right="Files and revision", toc=[(2, "E — Files and revision")])


# ================================================================ assemble
def build():
    cover()
    contents_placeholder()
    about()
    safety()
    overview()
    how_it_works()
    reuse(A.controls, [("Stage 12).", "Stage 12).")])
    at_a_glance()
    tools()
    hardware_pages()
    reuse(A.parts_pages, [
        ("replace them before printing plates 4 and 6 (Stage 1).", "replace them before printing plates 4 and 6 (Stage 1). Already printed? Use what you have."),
        ("Elbow support", "Elbow support (base plate sawn off, Stage 4)")])
    wood_page()
    reuse(A.stage_print, [
        ("Seven plates in build order; a fit test after each plate catches a bad print before it is buried in the assembly.",
         "Your parts are already printed: do each plate’s fit test now, before a bad print is buried in the assembly."),
        ("Print the plates in the order of the table below. After each plate do its fit test (last column) before printing the next.",
         "Print the plates in the order of the table below and do each fit test (last column). Parts you already have: do the fit test now. "
         "The minimal build uses every part as printed; only the elbow support (P16) gets its base plate sawn off in Stage 4.")])
    stage_cut()
    stage_sandbox()
    stage_pedestal()
    reuse(A.stage_turret, [("3/4in PEX-B tube, 120 mm", "3/4″ PEX-B tube, 4-3/4″"),
                           ("Set the base on the pedestal top with its centre bore over the Ø26.2 hole. Turn it until its four counterbored holes (45° positions, r 38 mm) sit over the four Ø3 pilots.",
                            "Set the base on the pedestal top with its centre bore over the 1″ hole. Turn it until its four counterbored holes sit over the four 1/8″ pilots."),
                           ("Do not over-tighten into the plywood.", "Do not over-tighten into the OSB."),
                           ("From inside the pedestal (wall +u off)", "From inside the pedestal (wall +u off; move it aside)")])
    stage_box()
    _box_pages_2_3()
    stage_mount()
    reuse(A.stage_arm, [("Boom rope 1384 mm (midpoint marked)", f"Boom rope {ii(ROPE['boom'])} (midpoint marked)"),
                        ("Stick rope 1821 mm", f"Stick rope {ii(ROPE['stick'])}"), ("Bucket rope 2173 mm", f"Bucket rope {ii(ROPE['bucket'])}"),
                        ("8-32 rod, 42 mm", "8-32 rod, 1-5/8″"), ("8-32 rod, 22 mm", "8-32 rod, 7/8″"),
                        ("8-32 rod, 65 mm (bucket pin)", "8-32 rod, 2-9/16″ (bucket pin)"),
                        ("Push a 42 mm 8-32 rod", "Push a 1-5/8″ 8-32 rod"), ("with a 22 mm 8-32 rod each side", "with a 7/8″ 8-32 rod each side"),
                        ("Push the 65 mm rod", "Push the 2-9/16″ rod"),
                        ("thread it up from the box side instead (through P18, the conduit, P17, the elbow and the PEX)",
                         "thread it up from the box side instead (through P18, the spacer chamber, P17, the elbow and the PEX)"),
                        ("Both fittings have bell-mouth entries on the conduit side.", "Both fittings have bell-mouth entries on the chamber side.")])
    reuse(A.stage_rig)
    reuse(A.stage_slew, [("PTFE slew sleeve A 339 mm, B 407 mm", f"PTFE slew sleeve A {ii(TUBE['slew rope A'])}, B {ii(TUBE['slew rope B'])}"),
                         ("Slew rope A 829 mm, B 900 mm", f"Slew rope A {ii(SLEW['A'])}, B {ii(SLEW['B'])}"),
                         ("along the conduit and into", "across the spacer chamber and into"),
                         ("Rope A (the shorter, 829 mm)", f"Rope A (the shorter, {ii(SLEW['A'])})"),
                         ("sleeve A (339 mm)", f"sleeve A ({ii(TUBE['slew rope A'])})"),
                         ("and trim the 10 mm extra", "and trim the 3/8″ extra"),
                         ("spool → posts → sleeves → conduit → pedestal fitting", "spool → posts → sleeves → spacer chamber → pedestal fitting")])
    reuse(A.stage_top, [("5/16in rod handle, 230 mm", f"5/16″ rod handle, {ii(R145)}"),
                        ("The top panel’s slots are the lever end stops. Fit it, push the handles through, and bolt the wheel on.",
                         f"The top panel’s slots are the lever end stops. Fit it, push the handles through, and bolt the wheel on, {ii(WHEEL_Z[0] - ex.BOX_Z[1])} above the lid."),
                        ("its Ø24.4 hole", "its 1″ hole"),
                        ("with nothing else touching. ", "with nothing else touching. The bucket knob passes 5/8″ from the wheel rim at its end of travel (Open item 7). ")])
    reuse(A.stage_test)
    reuse(A.operation, [("<li><b>Pedestal wall +u</b> — unscrew (screws only): slew drum clamp, copper elbow, sleeve ends.",
                         "<li><b>Pedestal wall +u</b> — unscrew (screws only): slew drum clamp, copper elbow, sleeve ends, the through-rod nuts.")])
    reuse(A.troubleshooting, [("Conduit seal missing at the sandbox wall", "Spacer seal leaking at the sandbox wall"),
                              ("Seal round the conduit with silicone outside the wall (Stage 7).",
                               "Run silicone into the corner between the outer spacer and the wall from inside the sandbox (Stage 7 tip)."),
                              ("Burr on the copper or the PVC end", "Burr on the copper end or a fitting hole")])
    reuse(A.app_bom, [("base and ear files updated to the 2026-09-29 rebuilds.", "updated for the minimal build (no conduit, 8-32 through-rods, kept prints)."),
                      ("Spares left: 8-32 rod about 711 mm and 10 nuts;", "Spares left: about 15″ of 8-32 rod and 2 nuts;")])
    app_cuts()
    app_open()
    app_diff()
    app_files()

    PAGES = A.PAGES
    toc, stage_pg = [], {}
    for i, p in enumerate(PAGES, start=1):
        for lv, title in p["toc"]:
            toc.append((lv, title, i))
        if p["stage"] and p["stage"] not in stage_pg:
            stage_pg[p["stage"]] = i
    ents = "".join(f'<div class="ent lv{lv}"><span>{esc(t_)}</span><span class="dots"></span><span class="pg">{pg}</span></div>' for lv, t_, pg in toc)
    toc_html = f'''<div class="kicker">Contents</div><h1>Contents</h1><div class="toc">{ents}</div>
<div class="rule"></div><p class="small">Page numbers count the cover as page 1. Figures are numbered in order through the manual.</p>'''
    out = []
    for i, p in enumerate(PAGES, start=1):
        body = INCH_RE.sub(lambda m: ">" + re.sub(r"(?<=\d)in\b", "″", m.group(1)) + "<", p["body"])
        body = body.replace("@@TOC@@", toc_html)
        for k, v in stage_pg.items():
            body = body.replace(f"@@P:stage{k}@@", f"p. {v}")
        head = foot = ""
        if "cover" not in p["cls"]:
            tabcls = "tab st" if p["stage"] else "tab"
            head = f'<div class="rhead"><span class="{tabcls}">{esc(p["tab"])}</span><span>{esc(p["right"])}</span></div>'
            foot = (f'<div class="rfoot"><span>EX-MA cable excavator · Minimal build manual · 2026-10-11</span>'
                    f'<span class="pn">{i}</span></div>')
        out.append(f'<section class="page {p["cls"]}">{head}{body}{foot}</section>')
    css_href = os.path.relpath(ASRC / "2026-10-10-manual.css", HERE)
    html_ = f'''<!doctype html><html><head><meta charset="utf-8"><title>EX-MA Minimal Build Manual</title>
<link rel="stylesheet" href="{css_href}"><style>{wc.CSS_EXTRA}</style></head><body>{"".join(out)}</body></html>'''
    (HERE / "2026-10-11-minimal-manual.html").write_text(html_)
    print(f"{len(PAGES)} pages, {A.FIG_N[0]} figures -> {HERE / '2026-10-11-minimal-manual.html'}")
    print("ropes", {k: round(v) for k, v in ROPE.items()}, "slew", {k: round(v) for k, v in SLEW.items()},
          "tubes", {n: round(L) for n, L, _ in PTFE_CUTS}, "rod832", round(ROD_832, 1), "chamber", round(CHAMBER, 1), "bow", round(BOW_R, 1))


if __name__ == "__main__":
    build()
