#!/usr/bin/env python3
"""EX-MA assembly and configuration manual — page builder.

Writes source/2026-10-10-manual.html from:
  - the rendered figures in ../figures/2026-10-10-<id>.png + .json (2026-10-10-manual-figures.mjs)
  - the project's own data: Source/2026-09-24-exma_common.py (dimensions, ranges), build-box.py
    panels() (wood sizes and holes), and the numbers in the bill of materials, cut list, checklist and
    validation reports (quoted below with their source).
Then 2026-10-10-manual-print.mjs prints it to the PDF.

Usage: <cadenv>/bin/python 2026-10-10-build-manual.py
"""
import importlib.util
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAN = HERE.parent
PROJ = MAN.parent
SRC = PROJ / "Source"
FIGDIR = MAN / "figures"
PFX = "2026-10-10-"


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


sv = _load("msvg", HERE / "2026-10-10-manual-svg.py")
ex = _load("exma", SRC / "2026-09-24-exma_common.py")
bx = _load("bx", SRC / "2026-09-24-build-box.py")

esc = sv.esc
FIG_N = [0]


def fignum():
    FIG_N[0] += 1
    return FIG_N[0]


def fig(fid, width_in, caption=None, gutter=(1.25, 1.25, 0.2, 0.2), **kw):
    FIG_N[0] += 1
    return sv.figure(FIGDIR, PFX + fid, width_in, gutter=gutter, caption=caption, num=FIG_N[0],
                     img_href=f"../figures/{PFX}{fid}.png", **kw)


# ================================================================ reference data (sources noted)
# printed parts: id, file name stem, display name, qty, material, plate, what it does
# (bill of materials 2026-09-24 + the 2026-09-29 rebuilds of the base and the bucket ears)
PARTS = [
    ("P01", "boom-half-left", "2026-09-24-boom-half-left", "Boom half, left (+v)", 1, "PETG", "arm 1"),
    ("P02", "boom-half-right", "2026-09-24-boom-half-right", "Boom half, right (−v)", 1, "PETG", "arm 1"),
    ("P03", "stick-half-left", "2026-09-24-stick-half-left", "Stick half, left (+v)", 1, "PETG", "arm 1"),
    ("P04", "stick-half-right", "2026-09-24-stick-half-right", "Stick half, right (−v)", 1, "PETG", "arm 1"),
    ("P05", "boom-drum", "2026-09-24-boom-drum", "Boom drum (Ø30 pitch)", 1, "PLA+", "other 6"),
    ("P06", "stick-drum", "2026-09-24-stick-drum", "Stick drum (Ø26 pitch)", 1, "PLA+", "other 6"),
    ("P07", "bucket-drum-axle", "2026-09-24-bucket-drum-axle", "Bucket drum-axle (Ø17 pitch)", 1, "PLA+", "other 6"),
    ("P08", "bucket", "2026-09-24-bucket", "Bucket", 1, "PLA+", "other 6"),
    ("P09", "bucket-ear-left", "2026-09-29-bucket-ear-left-cad", "Bucket ear, left (G)", 1, "PLA+", "other 6 *"),
    ("P10", "bucket-ear-right", "2026-09-29-bucket-ear-right-cad", "Bucket ear, right (H)", 1, "PLA+", "other 6 *"),
    ("P11", "tower", "2026-09-24-tower", "Tower (turret)", 1, "PLA+", "other 4"),
    ("P12", "base", "2026-09-29-base", "Base (lower race)", 1, "PLA+", "other 4 *"),
    ("P13", "slewing-ring-retaining-ring", "2026-09-24-slewing-ring-retaining-ring", "Slewing-ring retaining ring", 1, "PLA+", "other 5"),
    ("P14", "slew-drum", "2026-09-24-slew-drum", "Pedestal slew drum (Ø110)", 1, "PLA+", "other 1"),
    ("P15", "slew-tube-bushing", "2026-09-24-slew-tube-bushing", "PEX bushing", 1, "PLA+", "other 1"),
    ("P16", "elbow-support", "2026-09-24-elbow-support", "Elbow support", 1, "PLA+", "other 1"),
    ("P17", "conduit-end-fitting-pedestal", "2026-09-24-conduit-end-fitting-pedestal", "Conduit fitting, pedestal end", 1, "PLA+", "other 1"),
    ("P18", "conduit-end-fitting-box", "2026-09-24-conduit-end-fitting-box", "Conduit fitting, box end", 1, "PLA+", "other 3"),
    ("P19", "lever-hub-boom", "2026-09-24-lever-hub-boom", "Lever hub, boom", 1, "PLA+", "other 2"),
    ("P20", "lever-hub-stick", "2026-09-24-lever-hub-stick", "Lever hub, stick", 1, "PLA+", "other 2"),
    ("P21", "lever-hub-bucket", "2026-09-24-lever-hub-bucket", "Lever hub, bucket", 1, "PLA+", "other 3"),
    ("P22", "lever-knob-boom", "2026-09-24-lever-knob", "Lever knob (Ø36)", 3, "PLA+", "other 2"),
    ("P23", "slew-spool", "2026-09-24-slew-spool", "Slew spool (Ø110)", 1, "PLA+", "other 3"),
    ("P24", "slew-wheel", "2026-09-24-slew-wheel", "Slew wheel (Ø184)", 1, "PLA+", "other 2"),
    ("P25", "spool-riser", "2026-09-24-spool-riser", "Spool riser", 1, "PLA+", "other 2"),
    ("P26", "slew-tube-post-A", "2026-09-24-slew-tube-post", "Slew sleeve post", 2, "PLA+", "other 2"),
]
PID = {p[1].replace("-A", "").replace("-boom", "") if p[1] in ("lever-knob-boom", "slew-tube-post-A") else p[1]: p[0] for p in PARTS}

PANELS = bx.panels()
WID = {p.name: f"W{i + 1:02d}" for i, p in enumerate(PANELS)}

# hardware: id, item, qty, used for (bill of materials 2026-09-24)
HW = [
    ("H01", "M3 × 10 button head", 8, "rope-tail anchors on the 3 lever hubs (2 each) and the slew spool (2)"),
    ("H02", "M3 × 12 socket head cap", 16, "boom + stick drum key screws (8), retaining ring (8)"),
    ("H03", "M3 × 20 socket head cap", 17, "joining lugs (8), drag clamps (3), handle clamps (3), slew wheel (3)"),
    ("H04", "M3 × 25 socket head cap", 6, "PEX pinch clamps (2), pedestal conduit fitting (4)"),
    ("H05", "M3 × 30 socket head cap", 2, "box front to sandbox wall, lower corners"),
    ("H06", "M3 × 35 socket head cap", 4, "box conduit fitting through box front + sandbox wall"),
    ("H07", "M3 hex nut", 45, "with the screws above"),
    ("H08", "M3 flat washer", 36, "fittings, box bolts, rope anchors"),
    ("H09", "M3 split-lock washer", 27, "under nuts/heads on moving or clamping joints"),
    ("H10", "8-32 rod, 42 mm", 2, "boom split pins"),
    ("H11", "8-32 rod, 22 mm", 2, "stick split pins"),
    ("H12", "8-32 rod, 65 mm", 1, "bucket pin"),
    ("H13", "8-32 hex nut", 12, "jam pairs on the pins"),
    ("H14", "5/16in rod, 205 mm", 1, "lever axle"),
    ("H15", "5/16in rod, 274 mm", 1, "slew spool axle"),
    ("H16", "5/16in rod, 230 mm", 3, "lever handles"),
    ("H17", "5/16in nut + SAE washer", 4, "2 on the lever axle, 2 on the spool axle"),
    ("H18", "#8 × 1in flat-head wood screw", 4, "base to the pedestal top"),
    ("H19", "#6 × 3/4in flat-head wood screw", 16, "bearing blocks, riser, posts, bushing, elbow support"),
    ("H20", "#6 × 1-1/4in flat-head wood screw", 120, "panel joints, 4 per edge, with wood glue"),
]
STOCK = [
    ("S01", "1/16in galvanized 7×19 wire rope", "5 pieces", "1384 / 1821 / 2173 / 829 / 900 mm"),
    ("S02", "1/16in single crimp sleeve", 5, "3 joint-drum midpoints + 2 slew rope ends"),
    ("S03", "1/16in double crimp sleeve", 8, "6 arm tail loops + 2 slew loops"),
    ("S04", "PTFE tube 4 mm OD × 2 mm ID", "6 pieces", "647 / 658 / 813 / 822 / 339 / 407 mm"),
    ("S05", "6 mm airsoft BB (or 1/4in steel ball)", 57, "slewing ring (+ about 5 spare)"),
    ("S06", "3/4in PEX-B tube", "120 mm", "turret tube (turns with the turret)"),
    ("S07", "1/2in copper 90° sweep elbow + 50 mm pipe", 1, "fixed elbow in the pedestal; deburr both ends"),
    ("S08", "2in sch 40 PVC pipe", "141 mm", "conduit between box and pedestal"),
    ("S09", "Wood glue; CA or epoxy; silicone; cable tie", "—", "panel joints; ears + knobs; conduit seal; elbow"),
]
ROPE_CUTS = [("Boom circuit", 1384, "boom", "single crimp at the midpoint (692 mm), loop at each end"),
             ("Stick circuit", 1821, "stick", "single crimp at the midpoint (910.5 mm), loop at each end"),
             ("Bucket circuit", 2173, "bucket", "single crimp at the midpoint (1086.5 mm), loop at each end"),
             ("Slew rope A", 829, "slew", "single crimp at one end (pedestal drum), loop at the other (spool)"),
             ("Slew rope B", 900, "slew", "single crimp at one end (pedestal drum), loop at the other (spool)")]
PTFE_CUTS = [("stick_hi", 647, "box fitting → stop in the boom tip"), ("stick_lo", 658, "box fitting → stop in the boom tip"),
             ("bucket_hi", 813, "box fitting → stop in the stick nose"), ("bucket_lo", 822, "box fitting → stop in the stick nose"),
             ("slew sleeve A", 339, "post A → pedestal fitting"), ("slew sleeve B", 407, "post B → pedestal fitting")]

MID = {j: (lo + hi) / 2 for j, (lo, hi) in ex.WORKING.items()}


# ================================================================ html helpers
def tag(kind):
    return {"v": '<span class="tag v">Verified</span>', "a": '<span class="tag a">Assumption</span>',
            "o": '<span class="tag o">Open item</span>', "d": '<span class="tag d">Derived</span>'}[kind]


def box(kind, title, body):
    return f'<div class="box {kind}"><span class="bt">{title}</span>{body}</div>'


def steps(items, start=0):
    lis = "".join(f'<li{" class=chk" if it.startswith("✓") else ""}>{it.lstrip("✓ ")}</li>' for it in items)
    return f'<ol class="steps" style="--start:{start}">{lis}</ol>'


def need(rows, title="You need"):
    tr = "".join(f'<tr><td class="id">{i}</td><td>{n}</td><td class="q">{q}</td></tr>' for i, n, q in rows)
    return f'<div class="need"><h4>{title}</h4><table>{tr}</table></div>'


def pid(i):
    cls = "pid" + (" w" if i.startswith("W") else " h" if i.startswith("H") else " s" if i.startswith("S") else "")
    return f'<span class="{cls}">{i}</span>'


def table(head, rows, cls="t", num=()):
    th = "".join(f'<th{" class=n" if k in num else ""}>{h}</th>' for k, h in enumerate(head))
    tr = "".join("<tr>" + "".join(f'<td{" class=n" if k in num else ""}>{c}</td>' for k, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<table class="{cls}"><tr>{th}</tr>{tr}</table>'


PAGES = []        # dict(tab, right, body, toc=[(level, title)], cls)


def page(body, tab="", right="", toc=(), cls="", stage=False):
    PAGES.append(dict(body=body, tab=tab, right=right, toc=list(toc), cls=cls, stage=stage))


def stagehead(n, title, sub):
    return (f'<div class="stagehead"><div class="num"><div><small>STAGE</small>{n}</div></div>'
            f'<div class="t"><h2>{title}</h2><div class="sub">{sub}</div></div></div>')


# ================================================================ COVER
def cover():
    band = "".join(f'<span style="background:{c}"></span>' for c in (sv.CIRC["boom"], sv.CIRC["stick"], sv.CIRC["bucket"], sv.CIRC["slew"]))
    hero = f'<img src="../figures/{PFX}cover.png" style="width:100%">'
    body = f'''
<div class="band">{band}</div>
<div class="brand">
  <div class="kicker">Assembly &amp; configuration manual</div>
  <div class="title">EX-MA <em>cable</em><br>excavator</div>
  <div class="subtitle">Simplified EX-MA arm · lever control box · pedestal · sandbox</div>
  <div class="pills"><span style="background:{sv.CIRC["boom"]}">Boom</span><span style="background:{sv.CIRC["stick"]}">Stick</span>
  <span style="background:{sv.CIRC["bucket"]}">Bucket</span><span style="background:{sv.CIRC["slew"]}">Slew</span></div>
</div>
<div class="hero">{hero}</div>
<div class="meta">
  <div class="blk"><b>Edition</b> 2026-10-10 · for the project files in <span class="mono">2026-09-24-EX-MA-simplified/</span><br>
  <b>Includes</b> the 2026-09-29 base and bucket-ear rebuilds · all illustrations rendered from the project CAD</div>
  <div class="blk" style="text-align:right"><b>26 printed part types · 29 prints</b><br>21 plywood panels · 4 rope circuits · no electronics</div>
</div>'''
    page(body, cls="cover bleed")


# ================================================================ CONTENTS (filled later)
def contents_placeholder():
    page("@@TOC@@", tab="Contents", right="EX-MA assembly manual", toc=[])


# ================================================================ ABOUT
def about():
    body = f'''
<div class="kicker">Before you begin</div><h1>About this manual</h1>
<p class="lead">This manual takes you from a table of printed parts, plywood and hardware to a working, rigged excavator.
Work through the stages in order: each one assumes the stages before it are complete and checked.</p>
<div class="row">
 <div class="col">
  <h3>How the pages work</h3>
  <ul class="tight">
   <li><b>Stage header</b> — the stage number and what it achieves.</li>
   <li><b>You need</b> — every part and fastener for that stage, with its ID ({pid("P05")} printed, {pid("W01")} wood,
   {pid("H03")} hardware, {pid("S04")} stock) and quantity. Lay them out first.</li>
   <li><b>Numbered steps</b> — do them in order; each step is one action.</li>
   <li><b>Figures</b> — numbered balloons <span class="ball">1</span> match the step text or the list beside the figure.
   <span style="color:var(--accent);font-weight:700">Orange arrows</span> show where a part moves to.</li>
   <li><b>Check</b> boxes — stop and verify before going on.</li>
  </ul>
  <h3>Directions used everywhere</h3>
  <p>The project uses one fixed frame. Picture yourself standing at the control box, facing the sandbox:</p>
  <ul class="tight"><li><b>+u</b> points away from you, toward the sandbox (“forward”).</li>
  <li><b>+v</b> points to your left; <b>−v</b> to your right.</li><li><b>z</b> points up.</li></ul>
  <p>Part names use the same words: the <i>left</i> boom half is the +v half; the sandbox wall “−u” is the wall the box bolts to.</p>
 </div>
 <div class="col">{sv.conventions_svg()}</div>
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
  {box("open", "Open item", "A question this manual found in the design files that you must decide on.")}
 </div>
</div>
<h3>Verified, derived or assumed?</h3>
<p>Every number and connection in this manual comes from the project files. Where a statement needs care, it carries a tag:</p>
<table class="t compact"><tr><th style="width:1in">Tag</th><th>Meaning</th></tr>
<tr><td>{tag("v")}</td><td>Read directly from the CAD model, the build scripts or their validation reports.</td></tr>
<tr><td>{tag("d")}</td><td>Worked out from the model geometry for this manual (for example an assembly order that the geometry forces).
The reasoning is given next to it.</td></tr>
<tr><td>{tag("a")}</td><td>Not in the project files: general practice or a choice you can change. Treat it as a suggestion.</td></tr>
<tr><td>{tag("o")}</td><td>A conflict or gap found in the design files. Appendix D lists all of them with options.</td></tr></table>
<p class="small">Colours in the illustrations code the part type, not the filament colour: <span class="swatch" style="background:#f2a65a"></span>printed
PLA+ part <span class="swatch" style="background:#f2cf5b"></span>arm shell (PETG) <span class="swatch" style="background:#5b8fd1"></span>bucket ears
<span class="swatch" style="background:#4a5562"></span>original EX-MA dark parts <span class="swatch" style="background:#d9b783"></span>plywood
<span class="swatch" style="background:#b4bcc4"></span>metal hardware. Ropes: <span class="swatch" style="background:var(--boom)"></span>boom
<span class="swatch" style="background:var(--stick)"></span>stick <span class="swatch" style="background:var(--bucket)"></span>bucket
<span class="swatch" style="background:var(--slew)"></span>slew. Parts already installed in earlier steps are drawn in light grey.</p>
'''
    page(body, tab="Introduction", right="About this manual", toc=[(1, "Introduction"), (2, "About this manual")])


def safety():
    body = f'''
<div class="kicker">Read first</div><h1>Safety and good practice</h1>
<p class="lead">The EX-MA is a hand-powered model: there are no motors, springs or electrics. The hazards are the tools you build it with,
cut wire rope, small parts and pinch points between moving printed parts.</p>
<div class="row"><div class="col">
{box("warn", "Cut wire rope is sharp.", " Each cut end of 7×19 rope splays into fine, stiff wires that puncture skin. Wrap tape round the rope "
     "before cutting and cut through the tape; wear gloves when handling free ends; wear eye protection when cutting.")}
{box("warn", "Small parts.", " The 6 mm BBs, M3 nuts and crimp sleeves are choking hazards. The M3 kit is labelled “not suitable for children "
     "under 3 years due to small parts”. Keep the build area and the finished model away from small children.")}
{box("warn", "Pinch points.", " The slewing ring, the lever hubs and every joint drum can trap fingers while ropes are tensioned. Keep fingers "
     "out of the box and the pedestal while someone moves a lever or the wheel.")}
{box("warn", "Power tools and blades.", " Clamp plywood before drilling; cut PTFE tube with a tube cutter or a new razor blade on a cutting "
     "board, never toward your hand.")}
</div><div class="col">
{box("caut", "Adhesives.", " CA glue bonds skin in seconds. Use it with ventilation and keep acetone-free remover nearby. Follow the maker’s "
     "instructions and cure times for wood glue, CA, epoxy and silicone.")}
{box("caut", "Heat.", " Printed PLA+ softens well below the temperature of a car interior in summer. Do not leave the model in direct sun or "
     "in a hot vehicle. " + tag("a"))}
{box("caut", "Do not force a joint.", " Every lever has a hard stop at the end of its slot in the box top. If a lever or the wheel resists before "
     "reaching a stop, find the cause (page “Troubleshooting”) instead of pushing harder; a rope can pull out of its crimp or a printed drum can crack.")}
{box("caut", "Sand.", " Sand in the slewing ring, the lever slots or the conduit wears the parts fast. Keep the sand dry and below the pedestal top "
     "(the model’s sand level is 10 mm below it " + tag("v") + ").")}
</div></div>
<h3>Workspace</h3>
<ul class="tight"><li>A flat table about 1.2 × 0.8 m for the box and the sandbox; good light (rope holes are Ø2.4 mm).</li>
<li>Small trays or bags for hardware: one per stage (the “You need” lists match the stages).</li>
<li>Masking tape and a fine marker for labelling ropes and tubes as you cut them.</li></ul>
<h3>Before you start</h3>
<table class="t compact">
<tr><td style="width:18px">☐</td><td>Read the whole manual once, including Appendix D (open items). Decide items 1–5 before the stage they affect.</td></tr>
<tr><td>☐</td><td>Decide the box size: the modelled box (this manual) or the compact box (Appendix E). It changes the panels, three rods and three prints.</td></tr>
<tr><td>☐</td><td>Check your 5/16in rod: threaded or smooth (Open item 4).</td></tr>
<tr><td>☐</td><td>Check the hardware against Appendix A and the actual-size drawings on page 10. The M3 kit holds every screw size used.</td></tr>
<tr><td>☐</td><td>Have at least 9 m of rope, a 5 m roll of PTFE tube, 57 BBs plus spares, and the crimp sleeves.</td></tr>
<tr><td>☐</td><td>Print plates in the Stage 1 order and do each fit test as the plate comes off.</td></tr></table>
'''
    page(body, tab="Introduction", right="Safety", toc=[(2, "Safety and good practice")])


# ================================================================ OVERVIEW
def overview():
    legend = [(1, "Boom lever"), (2, "Stick lever"), (3, "Bucket lever"), (4, "Slew wheel"), (5, "Control box (plywood)"),
              (6, "Removable box top — the lever slots are the end stops"), (7, "Pedestal (inside the sandbox)"),
              (8, "Base with the printed slewing ring (57 BBs)"), (9, "Tower (turret)"), (10, "Boom"), (11, "Stick"), (12, "Bucket"),
              (13, "Sandbox, 610 × 610 mm")]
    lg = "".join(f'<tr><td style="width:22px"><span class="ball">{n}</span></td><td>{t_}</td></tr>' for n, t_ in legend)
    body = f'''
<div class="kicker">System overview</div><h1>What you are building</h1>
<p class="lead">Three levers and a wheel on a wooden control box drive the EX-MA arm through wire ropes. Each control moves exactly one
motion: <b style="color:var(--boom)">boom</b>, <b style="color:var(--stick)">stick</b>, <b style="color:var(--bucket)">bucket</b> or
<b style="color:var(--slew)">slew</b>. The ropes run from the box through a 2in conduit under the sandbox wall into the pedestal, up the
turret’s centre tube and along the arm.</p>
{fig("overview", 7.3, "The complete machine as modelled (joints at their modelled pose, the near sandbox wall see-through).",
     gutter=(0.3, 0.3, 0.3, 0.2), legend=True, max_h_in=4.6, key_cols=0)}
<div class="row"><div class="col"><table class="t compact">{lg}</table></div>
<div class="col">
<h3 class="mt0">Main dimensions {tag("v")}</h3>
<table class="t compact">
<tr><td>Sandbox (outside)</td><td class="n">610 × 610 × 242 mm</td></tr>
<tr><td>Control box (outside, u × v × z)</td><td class="n">250 × 405 × 242 mm</td></tr>
<tr><td>Pedestal (outside)</td><td class="n">200 × 180 × 190 mm</td></tr>
<tr><td>Base / slewing ring</td><td class="n">Ø140 mm</td></tr>
<tr><td>Boom / stick, pin to pin</td><td class="n">209 / 175 mm</td></tr>
<tr><td>Knob tops above the floor</td><td class="n">339 mm</td></tr>
</table>
<p class="small">The control box is the size in the CAD model. A smaller box (214 × 362 × 156) was specified on 2026-09-28 but not
modelled; see Appendix E before you cut the box panels.</p>
</div></div>'''
    page(body, tab="Overview", right="System overview", toc=[(1, "System overview"), (2, "What you are building")])


def how_it_works():
    lengths = dict(boom="rope 1384 mm, bare (no tube)", stick="rope 1821 mm in 2 PTFE tubes", bucket="rope 2173 mm in 2 PTFE tubes",
                   slew="ropes 829 + 900 mm in 2 PTFE sleeves")
    body = f'''
<div class="kicker">System overview</div><h1>How it works</h1>
<p class="lead">Every circuit is a <b>pull-pull loop</b>: one rope, anchored on two drums. Turning the control drum pulls one strand and lets out
the other by the same amount, so the joint drum — and the joint — turns. Nothing else is connected to that rope, so each control moves only
its own joint.</p>
<div class="figframe" style="padding:4px 8px;width:5.6in;margin:0 auto">{sv.circuits_svg(lengths)}</div>
<div class="cap" style="margin-bottom:8px"><b>Fig. {fignum()}</b><span>Rope circuits (the “wiring diagram” of this machine). Each lever drives a Ø60
drum on the common lever axle; the slew wheel drives a Ø110 two-lane spool.</span></div>
{fig("system-cutaway", 7.3, "Every rope as modelled, from its control to its joint (cut through the middle; built pose).",
     gutter=(1.05, 1.0, 0.15, 0.3), max_h_in=1.85)}
<div class="row"><div class="col">
<h4>Why the stick and bucket ropes run in PTFE tubes</h4>
<p>Their ropes cross the boom joint (and the bucket ropes the stick joint). Inside a tube that is anchored at the box fitting and at a stop in the
arm, the rope length does not change when another joint moves. The tubes cross each joint through the pivot axis (the pins are split in two
for this), and the small length change left is taken up as spare tube in the conduit. {tag("v")}</p>
</div><div class="col">
<h4>Why the slew drum is in the pedestal</h4>
<p>The turret turns on a printed ball ring. A 3/4in PEX tube clamped in the turret hub runs down through the base into the pedestal, where the
slew drum is clamped to it; a shelf bushing just above the drum takes the ropes’ side pull. The arm ropes run up the inside of the same tube.
{tag("v")}</p>
</div></div>'''
    page(body, tab="Overview", right="How it works", toc=[(2, "How it works")])


def controls():
    rows = [("Boom lever", "boom", "boom down", "boom up", f"{ex.WORKING['boom'][0]:.0f}° … +{ex.WORKING['boom'][1]:.0f}°", "42.5°"),
            ("Stick lever", "stick", "stick out", "stick in", f"{ex.WORKING['stick'][0]:.0f}° … +{ex.WORKING['stick'][1]:.0f}°", "41.2°"),
            ("Bucket lever", "bucket", "bucket dump", "bucket curl", f"{ex.WORKING['bucket'][0]:.0f}° … +{ex.WORKING['bucket'][1]:.0f}°", "39.7°")]
    tr = "".join(f'<tr><td><span class="swatch" style="background:var(--{c})"></span><b>{n}</b></td><td>{f}</td><td>{b}</td><td class="n">{r}</td>'
                 f'<td class="n">{s}</td></tr>' for n, c, f, b, r, s in rows)
    body = f'''
<div class="kicker">System overview</div><h1>Controls and specifications</h1>
{fig("controls", 7.3, "The operator’s view: three levers in slots, the slew wheel on the right. Orange arrows show the lever travel and the wheel.",
     gutter=(1.05, 1.0, 0.1, 0.1))}
<div class="row"><div class="col w60">
<h3 class="mt0">Lever and wheel directions</h3>
<table class="t"><tr><th>Control</th><th>Push forward</th><th>Pull back</th><th class="n">Joint range</th><th class="n">Lever swing</th></tr>{tr}
<tr><td><span class="swatch" style="background:var(--slew)"></span><b>Slew wheel</b></td><td colspan="2">turn left (anticlockwise from above) →
arm swings to your left; 1 : 1</td><td class="n">−90° … +90°</td><td class="n">180°</td></tr></table>
<p class="small">“Forward” = toward the sandbox (+u). Directions and ranges {tag("v")}: architecture notes and kinematics report. You set the lever
direction when you rig each rope (Stage 9); a reversed lever is fixed by reversing that rope’s wrap on its joint drum.</p>
</div><div class="col">
<h3 class="mt0">Key specifications {tag("v")}</h3>
<table class="t compact">
<tr><td>Rope</td><td>1/16in galvanized 7×19</td></tr>
<tr><td>Joint drums (pitch Ø)</td><td>boom 30 · stick 26 · bucket 17</td></tr>
<tr><td>Control drums</td><td>levers Ø60 · slew spool Ø110</td></tr>
<tr><td>Slew drums</td><td>Ø110, two lanes</td></tr>
<tr><td>Slewing ring</td><td>57 × 6 mm BBs on Ø118</td></tr>
<tr><td>Joint pins</td><td>8-32 threaded rod</td></tr>
<tr><td>Axles / handles</td><td>5/16in rod</td></tr>
<tr><td>Printed parts</td><td>26 types, 29 prints, ≈1.03 kg</td></tr>
<tr><td>Materials</td><td>arm shell PETG, rest PLA+</td></tr>
</table></div></div>
{fig("ranges", 7.3, "What each lever moves: the working ranges set by the slots (detail in Stage 12).", gutter=(0.05, 0.05, 0.05, 0.05),
     extra=range_extra, crop=None, max_h_in=2.9)}'''
    page(body, tab="Overview", right="Controls and specifications", toc=[(2, "Controls and specifications")])


def at_a_glance():
    st = [(1, "Print & check", "29 prints on 7 plates; fit test after each plate", "P"),
          (2, "Cut, drill & label", "plywood, rods, rope, PTFE; label every piece", "C"),
          (3, "Sandbox", "floor + 4 walls", "S"), (4, "Pedestal", "walls, conduit fitting, copper elbow, shelf, bushing", "Pd"),
          (5, "Slewing ring & turret", "base, PEX tube, BBs, turret, retaining ring, slew drum", "T"),
          (6, "Control box", "carcass, lever axle + hubs, spool, posts", "B"),
          (7, "Conduit, tubes, box mounting", "conduit, 4 PTFE tubes, bolt the box on", "Cd"),
          (8, "Arm", "drums, ropes at the joint end, halves, pins, bucket", "A"),
          (9, "Arm ropes at the levers", "zero pose, loops on anchors, tension, direction", "R"),
          (10, "Slew ropes", "sleeves, drum pockets, spool anchors", "Sl"),
          (11, "Top, handles, wheel", "top panel, handles, knobs, wheel, drag clamps", "Tp"),
          (12, "Test & configure", "ranges, coupling, tension, friction", "F")]
    cards = "".join(f'<div class="st"><div class="n">{n:02d}</div><div class="nm">{a}</div><div class="d">{b}</div><div class="pg">@@P:stage{n}@@</div></div>'
                    for n, a, b, _ in st)
    body = f'''
<div class="kicker">Planning</div><h1>Build at a glance</h1>
<p class="lead">Twelve stages. Stages 1 and 2 are preparation; 3–8 build the machine; 9–12 rig, adjust and test it.</p>
<div class="flow">{cards}</div>
<h3>Changes from the 2026-09-25 checklist {tag("d")}</h3>
<p>This manual follows the order in <span class="mono">2026-09-25-print-and-assembly-checklist.md</span> with three changes the geometry forces:</p>
<ul class="tight">
<li><b>The box is bolted on after the turret (Stage 7, not 5).</b> The four PTFE tubes stop in a window on the conduit side of the box fitting;
they can only be seated there while that fitting is still loose. The same bolts hold the fitting, the box front and the sandbox wall together.</li>
<li><b>The lever axle goes in before the left box side.</b> With the side fitted, its nut is 2 mm from the side panel and the 205 mm rod cannot be
threaded through the blocks.</li>
<li><b>The joint end of each arm rope is rigged while its arm half is open (Stage 8).</b> The crimp pockets are inside the closed arm.</li></ul>
<h3>Open items to decide before you start {tag("o")}</h3>
<p>Preparing this manual turned up the following conflicts in the design files. Read Appendix D now; items 1–3 change what you do in Stage 8.</p>
<table class="t compact"><tr><th>#</th><th>Item</th><th>Affects</th></tr>
<tr><td>1</td><td>Stick-drum key screws: two M3 × 12 enter each through-hole from opposite sides and their tips overlap by 1.6 mm.</td><td>Stage 8</td></tr>
<tr><td>2</td><td>Stick joining lugs 1 and 2 at the stick root are 2.9 mm apart: their holes merge, so only one screw fits there.</td><td>Stage 8</td></tr>
<tr><td>3</td><td>Joining-lug screws cannot be reached once a boom or stick is closed: no access hole through the outer wall.</td><td>Stage 8</td></tr>
<tr><td>4</td><td>5/16in nuts on the axles need threaded rod ends; one design note calls the rod “smooth”.</td><td>Stages 6, 11</td></tr>
<tr><td>5</td><td>The cut list says the pedestal screws to the sandbox floor, but no screws are counted for it.</td><td>Stage 4</td></tr>
<tr><td>6</td><td>The 3MF plates still hold the old base and bucket ears; print the 2026-09-29 files instead.</td><td>Stage 1</td></tr>
<tr><td>7</td><td>Rope tension: the checklist says slide the anchors “outward”; the geometry says inward (toward the drum centre).</td><td>Stages 9, 10</td></tr></table>'''
    page(body, tab="Planning", right="Build at a glance", toc=[(2, "Build at a glance")])


def tools():
    body = f'''
<div class="kicker">Planning</div><h1>Tools and supplies</h1>
<p class="lead">From the project checklist {tag("v")}. Everything else is in the bill of materials (Appendix A).</p>
<div class="row"><div class="col">
<h3>Hand tools</h3>
<table class="t compact">
<tr><td>2.5 mm hex key</td><td>M3 socket head cap screws</td></tr>
<tr><td>2 mm hex key</td><td>M3 button head screws (rope anchors)</td></tr>
<tr><td>5.5 mm wrench or nut driver</td><td>M3 nuts</td></tr>
<tr><td>11/32in wrench (×2)</td><td>8-32 jam nuts — one to hold, one to turn</td></tr>
<tr><td>1/2in wrench</td><td>5/16in nuts on the axles</td></tr>
<tr><td>Screwdriver (Phillips)</td><td>#6 and #8 wood screws</td></tr>
<tr><td>Crimp tool for 1/16in sleeves</td><td>single and double crimp sleeves</td></tr>
<tr><td>Wire-rope cutter</td><td>1/16in 7×19 rope</td></tr>
<tr><td>PTFE tube cutter or new razor blade</td><td>cut square</td></tr>
<tr><td>Pipe cutter or hacksaw; deburring tool</td><td>PVC conduit, copper</td></tr>
</table></div><div class="col">
<h3>Power tools and consumables</h3>
<table class="t compact">
<tr><td>Drill + 3.5 mm and 2 mm bits</td><td>M3 clearance; wood-screw pilots</td></tr>
<tr><td>Drill bits for the panel holes</td><td>Ø62 (hole saw), Ø30.4, Ø26.2, Ø24.4, Ø22 counterbore, Ø8.5, Ø4.6, Ø3.0 — sizes from the cut list {tag("v")}</td></tr>
<tr><td>Saw for 12 mm plywood</td><td>21 panels (Appendix B)</td></tr>
<tr><td>Wood glue</td><td>every panel joint</td></tr>
<tr><td>CA or epoxy</td><td>bucket ears to the bucket; knobs on the handles</td></tr>
<tr><td>Silicone</td><td>conduit seal at the sandbox wall</td></tr>
<tr><td>Cable tie (1)</td><td>copper elbow to its support</td></tr>
<tr><td>Masking tape + fine marker</td><td>label every rope and tube</td></tr>
<tr><td>Metal file</td><td>slot-end burrs, rod ends {tag("a")}</td></tr>
</table></div></div>
<h3>3D printing</h3>
<p>The parts were laid out for a Bambu Lab A1 with a 0.6 mm nozzle; slicer projects for Bambu Studio and OrcaSlicer are in <span class="mono">3MF/</span>.
Arm shell in PETG, everything else in PLA+ (SUNLU PLA+ 2.0). Stage 1 lists the settings. {tag("v")}</p>
<h3>Hardware bags by stage {tag("v")}</h3>
{table(["Stage", "Fasteners and stock to bag"], [
    ("3 Sandbox", "32 × #6 × 1-1/4in"),
    ("4 Pedestal", "40 × #6 × 1-1/4in; 5 × #6 × 3/4in; 4 × M3 × 25, 8 flat washers, 4 nuts; copper elbow; cable tie"),
    ("5 Slewing ring", "4 × #8 × 1in; 8 × M3 × 12; 2 × M3 × 25; 10 split-lock washers; 10 nuts; 57 BBs; PEX tube"),
    ("6 Control box", "32 × #6 × 1-1/4in; 11 × #6 × 3/4in; 205 + 274 mm 5/16in rod; 3 × 5/16in nut + washer"),
    ("7 Conduit + box", "4 × M3 × 35; 2 × M3 × 30; 12 flat washers; 6 nuts; PVC conduit; 4 arm PTFE tubes"),
    ("8 Arm", "8 × M3 × 12 (or M3 × 8, Open item 1); 8 × M3 × 20 + 8 nuts; 8-32 rods 2 × 42, 2 × 22, 1 × 65 mm; 12 × 8-32 nuts; 3 single crimps"),
    ("9 Arm ropes", "6 × M3 × 10 button head; 12 flat washers; 6 split-lock washers; 6 nuts; 6 double crimps"),
    ("10 Slew ropes", "2 × M3 × 10 button head; 4 flat washers; 2 split-lock washers; 2 nuts; 2 single + 2 double crimps; 2 sleeves"),
    ("11 Top", "16 × #6 × 1-1/4in; 9 × M3 × 20; 9 split-lock washers; 9 nuts; 3 handle rods; 1 × 5/16in nut + washer")], cls="t compact")}
<p class="small">Counts follow the bill of materials and the hardware model; the M3 split-lock and flat-washer totals (27 / 36) match.</p>'''
    page(body, tab="Planning", right="Tools and supplies", toc=[(2, "Tools and supplies")])


# ================================================================ HARDWARE 1:1
def hardware_pages():
    W = 184
    s = [f'<svg viewBox="0 0 {W} 128" width="{W}mm" height="128mm">']
    s.append(sv.t(2, 5, "M3 SCREWS — HEAD UP, ACTUAL SIZE", 3.4, "start", 700, sv.INK2, "Barlow"))
    x = 10
    for L, kind, idn, q in ((10, "b", "H01", 8), (12, "s", "H02", 16), (20, "s", "H03", 17), (25, "s", "H04", 6),
                            (30, "s", "H05", 2), (35, "s", "H06", 4)):
        s.append(sv.button_head(x, 10, L) if kind == "b" else sv.socket_cap(x, 10, L))
        s.append(sv.t(x, 58, f"M3 × {L}", 3.0, "middle", 700))
        s.append(sv.t(x, 61.8, "button head" if kind == "b" else "socket cap", 2.5, "middle", 500, sv.INK2))
        s.append(sv.t(x, 65.6, f"{idn} · ×{q}", 2.6, "middle", 700, sv.ACC))
        x += 17
    s.append(sv.line(4, 13, 4, 13 + 35, sv.INK3, 0.2))
    s.append(sv.t(3, 50, "length is measured under the head", 2.2, "start", 500, sv.INK3, extra='transform="rotate(-90 3 50)"'))
    # nuts and washers
    x0 = 118
    s.append(sv.t(x0 - 4, 5, "M3 NUT AND WASHERS", 3.4, "start", 700, sv.INK2, "Barlow"))
    for k, (draw, nm, idn, q) in enumerate(((sv.nut(x0 + 4, 16, 5.5, 3.0), "M3 nut", "H07", 45),
                                            (sv.ring(x0 + 22, 16, 7.0, 3.2), "flat washer", "H08", 36),
                                            (sv.ring(x0 + 40, 16, 6.2, 3.1, split=True), "split-lock", "H09", 27))):
        s.append(draw)
        cx = x0 + 4 + 18 * k
        s.append(sv.t(cx, 26, nm, 2.6, "middle", 700) + sv.t(cx, 29.6, f"{idn} · ×{q}", 2.6, "middle", 700, sv.ACC))
    # 8-32
    s.append(sv.t(x0 - 4, 38, "8-32 ROD AND NUT (HILLMAN)", 3.4, "start", 700, sv.INK2, "Barlow"))
    y = 46
    for L, idn, q, what in ((22, "H11", 2, "stick split pin"), (42, "H10", 2, "boom split pin"), (65, "H12", 1, "bucket pin")):
        s.append(sv.rod(x0 - 4, y, L, 4.17))
        s.append(sv.t(x0 - 4, y - 3.2, f"{L} mm · {what} · {idn} ×{q}", 2.5, "start", 600))
        y += 9
    s.append(sv.nut(x0 + 40, 47, 11 / 32 * 25.4, 4.2) + sv.t(x0 + 46, 48, "8-32 nut", 2.6, "start", 700) + sv.t(x0 + 46, 51.5, "H13 ×12", 2.6, "start", 700, sv.ACC))
    # wood screws
    s.append(sv.t(2, 75, "WOOD SCREWS (FLAT HEAD)", 3.4, "start", 700, sv.INK2, "Barlow"))
    xw = 10
    for L, d, hd, nm, idn, q in ((19.05, 3.5, 6.65, "#6 × 3/4in", "H19", 16), (31.75, 3.5, 6.65, "#6 × 1-1/4in", "H20", 120),
                                 (25.4, 4.17, 8.0, "#8 × 1in", "H18", 4)):
        s.append(sv.wood_screw(xw, 80, L, d, hd))
        s.append(sv.t(xw + 6, 90, nm, 2.8, "start", 700) + sv.t(xw + 6, 93.6, f"{idn} · ×{q}", 2.6, "start", 700, sv.ACC))
        xw += 30
    # 5/16
    s.append(sv.t(100, 84, "5/16in NUT AND WASHER", 3.4, "start", 700, sv.INK2, "Barlow"))
    s.append(sv.nut(110, 99, 12.7, 8.0) + sv.ring(132, 99, 17.46, 8.73))
    s.append(sv.t(121, 113, "H17 · ×4 each (axle ends)", 2.6, "middle", 700, sv.ACC))
    # rope, ptfe, crimps, BB
    s.append(sv.t(150, 84, "STOCK (ACTUAL SIZE)", 3.4, "start", 700, sv.INK2, "Barlow"))
    s.append(sv.circ(154, 93, 3.0, "#f6f2e6", sv.INK, 0.25) + sv.t(159, 94, "6 mm BB", 2.6, "start", 700))
    s.append(sv.ring(154, 103, 4.0, 2.0, "#ffffff") + sv.t(159, 104, "PTFE tube, end", 2.6, "start", 700))
    s.append(sv.circ(154, 111, 0.8, sv.STEEL, sv.INK, 0.2) + sv.t(159, 112, "rope Ø1.6", 2.6, "start", 700))
    s.append(sv.rect(151.85, 116, 4.3, 6.4, sv.STEEL, sv.INK, 0.2, 0.6) + sv.t(159, 120, "crimp (nominal)", 2.6, "start", 700))
    s.append(sv.line(2, 125, 102, 125, sv.INK, 0.35) + "".join(sv.line(2 + 10 * k, 123.5, 2 + 10 * k, 126.5, sv.INK, 0.3) for k in range(11)))
    s.append(sv.t(104, 126, "100 mm — measure this to check your print is at 100 %", 2.6, "start", 600, sv.INK2))
    s.append("</svg>")
    body = f'''
<div class="kicker">Parts identification</div><h1>Hardware at actual size</h1>
<p class="lead">Print this page at 100 % (no “fit to page”) and lay each screw on its drawing to identify it. The scale bar at the bottom must
measure 100 mm. Sizes from the screw standards used in the hardware model {tag("v")}.</p>
<div class="hw11">{"".join(s)}</div>
<div class="row mt8"><div class="col">
<img src="../figures/{PFX}photo-m3-kit.jpg" style="width:100%;height:1.75in;object-fit:cover;border-radius:3px"><div class="cap"><b>Photo</b><span>Your M3 kit (Fgruh, 2300 pc):
socket head caps and button heads in 4–35 mm, nuts, flat and split-lock washers.</span></div>
</div><div class="col">
<img src="../figures/{PFX}photo-hillman.jpg" style="width:100%;height:1.75in;object-fit:cover;object-position:50% 30%;border-radius:3px"><div class="cap"><b>Photo</b><span>Your Hillman parts: 3 ft of 8-32
threaded rod and 22 hex nuts (used); the #4-40 and #6-32 machine screws are not needed.</span></div>
</div><div class="col">
{box("mistake", "M3 × 12 vs M3 × 20.", " They look alike in the bag. Lay them on the drawing above before each step.")}
{box("note", "Wood screws", " are your own stock. Flat-head #6 and #8 are drawn; pan heads will not sit flush in the printed counterbores. " + tag("a"))}
</div></div>'''
    page(body, tab="Parts", right="Hardware at actual size", toc=[(1, "Parts identification"), (2, "Hardware at actual size")])


def parts_pages():
    def card(p):
        i, fid, stem, nm, q, mat, plate = p
        star = "*" in plate
        newf = ' · <b style="color:var(--accent)">new file</b>' if star else ""
        pl = plate.replace(" *", "")
        return (f'<div class="card"><span class="pid">{i}</span><span class="qty">×{q}</span>'
                f'<img src="../figures/{PFX}part-{fid}.png"><div class="nm">{nm}</div>'
                f'<div class="mt">{mat} · plate {pl}{newf}</div>'
                f'<div class="fn">STL/{stem}.stl</div></div>')
    halves = [PARTS[:16], PARTS[16:]]
    for k, chunk in enumerate(halves):
        cards = "".join(card(p) for p in chunk)
        intro = (f'<div class="kicker">Parts identification</div><h1>Printed parts</h1><p class="lead">26 part types, 29 prints. Each card shows '
                 f'the part ID used in this manual, the quantity, the material and slicer plate, and the STL file. {tag("v")}</p>') if k == 0 else \
            '<div class="kicker">Parts identification</div><h2>Printed parts (continued)</h2>'
        extra = ""
        if k == 1:
            extra = f'''<div class="mt8">{box("caut", "Use the current files for P09, P10 and P12.", " The base was rebuilt on 2026-09-29 (no supports "
                    "needed under the race rim, the four unused outer holes filled) and both bucket ears were rebuilt as clean CAD solids "
                    "(reinforced joint, no mesh defects). The slicer projects in <span class=mono>3MF/</span> still contain the older versions: "
                    "replace them before printing plates 4 and 6 (Stage 1). Do not use the superseded patched-mesh files "
                    "<span class=mono>STL/2026-09-29-bucket-ear-left.stl</span> / <span class=mono>-right.stl</span>.")}
{box("note", "Arm-shell halves", " are mirror images. The <b>left</b> halves (P01, P03) sit on the +v side, the operator’s left when the arm points "
     "away from the box.")}</div>'''
        page(intro + f'<div class="gal">{cards}</div>' + extra, tab="Parts", right="Printed parts",
             toc=[(2, "Printed parts")] if k == 0 else [])


def wood_page():
    rows = []
    for p in PANELS:
        dims = sorted(p.size, reverse=True)
        grp = {"control-box": "Control box", "pedestal": "Pedestal", "sandbox": "Sandbox"}[p.group]
        nh = len(p.holes)
        rows.append((pid(WID[p.name]), f"<b>{grp}</b> · {esc(p.name)}", f"{dims[0]:.0f} × {dims[1]:.0f}", f"{nh}" if nh else "—", esc(p.note or "")))
    body = f'''
<div class="kicker">Parts identification</div><h1>Wood and stock</h1>
<p class="lead">21 panels, all 12 mm plywood (1/2in also works). Sizes from the cut list generated by <span class="mono">build-box.py</span>
{tag("v")}. Hole positions are drawn in Appendix B.</p>
{table(["ID", "Panel", "Size (mm)", "Holes", "Note"], rows, cls="t compact", num=(2, 3))}
<h3>Stock items</h3>
{table(["ID", "Item", "Qty / length", "Used for"], [(pid(a), b, c, d) for a, b, c, d in STOCK], cls="t compact")}'''
    page(body, tab="Parts", right="Wood and stock", toc=[(2, "Wood and stock")])


# ================================================================ STAGE 1 PRINT
def stage_print():
    plates = [("PETG", "arm 1", "Arm shell", "P02, P01, P04, P03", "bucket drum-axle journals turn freely in both stick-half nose holes"),
              ("PLA+", "other 1", "Pedestal", "P17, P14, P15, P16", "copper elbow pushes into P17’s socket; a PTFE tube slides through its window; "
               "the PEX tube turns in P15; P14 slides onto the PEX tube (clamp open)"),
              ("PLA+", "other 2", "Control box 1/2", "P24, P20, P19, P25, P22 ×3, P26 ×2", "5/16in rod slides through each hub and into its "
               "handle socket; rod enters each knob; riser sits flat"),
              ("PLA+", "other 3", "Control box 2/2", "P18, P23, P21", "rod through the hub; spool turns on the rod; 4 PTFE tubes seat together "
               "in P18’s window and stop on its floor"),
              ("PLA+", "other 4", "Turret + slewing ring 1/2", "P12 (new file), P11", "PEX tube slides into the tower’s centre bore"),
              ("PLA+", "other 5", "Turret + slewing ring 2/2", "P13", "a BB rolls freely in the race between the base rim and the ring"),
              ("PLA+", "other 6", "Arm mechanism + bucket", "P08, P05, P06, P10 + P09 (new files), P07", "each drum sits flat")]
    rows = [(m, pl, n, ps, ft) for m, pl, n, ps, ft in plates]
    settings = [("Printer preset", "A1 0.6 Fast Start (your preset)"), ("Process", "0.30mm Strength @BBL A1 0.6 nozzle — 0.3 mm layers, 4 walls"),
                ("Infill", "25 % (40 % on drums, hubs, clamps and pinned parts)"), ("Supports", "tree, only where the plate marks them"),
                ("PETG filament", "Generic PETG @BBL A1 — arm shell only"), ("PLA+ filament", "SUNLU PLA+ 2.0 @BBL A1 — everything else"),
                ("PLA+ speed (project)", "flow cap 28 mm³/s at 230 °C; inner walls / infill / supports 200 mm/s; accel 10000"),
                ("If infill looks thin", "lower the filament’s max volumetric speed to 25")]
    card = "".join(f'<div style="display:flex;border-bottom:0.5pt solid #e3e7eb;padding:2px 0"><div style="flex:0 0 1.35in;color:var(--ink2)">{a}</div>'
                   f'<div style="font-weight:600">{b}</div></div>' for a, b in settings)
    body = f'''{stagehead(1, "Print and check the parts", "Seven plates in build order; a fit test after each plate catches a bad print before it is buried in the assembly.")}
<div class="row"><div class="col w55">
<h3 class="mt0">Configuration: slicer settings {tag("v")}</h3>
<div class="figframe" style="padding:6px 9px;font-size:7.6pt">
<div style="font-family:Barlow;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--navy);margin-bottom:3px">
Stored in the project files — open, check, print</div>{card}</div>
<div class="cap"><b>Fig. {fignum()}</b><span>Summary of the settings saved in <span class="mono">3MF/2026-09-27-{{bambu,orca}}-*.3mf</span>
(not a screenshot: your slicer shows them under the printer, process and filament presets).</span></div>
</div><div class="col">
{steps(["Open the project for your slicer from <span class=mono>3MF/</span>: <span class=mono>2026-09-27-bambu-…</span> for Bambu Studio "
        "2.8.2.61 or <span class=mono>2026-09-27-orca-…</span> for OrcaSlicer. Each opens with its plates named and the settings in place.",
        "In the PLA+ project, replace the base on plate 4 with <span class=mono>STL/2026-09-29-base.stl</span> and both ears on plate 6 with "
        "<span class=mono>STL/2026-09-29-bucket-ear-{left,right}-cad.stl</span>. Keep their orientation: base flat side down; ears on their "
        "outer side.",
        "Every part is already in its print orientation and every wall was checked for the 0.6 mm nozzle — do not rotate or rescale parts.",
        "Print the plates in the order of the table below. After each plate do its fit test (last column) before printing the next."])}
</div></div>
{table(["Material", "Plate", "Name", "Parts", "Fit test after printing"], rows)}
{box("check", "Check after every plate.", " Remove all support, then do the fit test. A hub that will not slide on the rod, or a drum that rocks on "
     "the table, gets reprinted now — not after it is rigged.")}
<div class="row"><div class="col">{box("note", "New base (P12).", " Only the eight nut-slot roofs need support (about 2 cm²; the race rim has its own 45° "
     "support built in). The bill of materials still lists 28 cm² for the old base. " + tag("v"))}</div>
<div class="col">{box("mistake", "Ears swapped.", " P09 (left) and P10 (right) are mirror images. Mark them L and R as soon as they come off the plate.")}</div></div>'''
    page(body, tab="Stage 1", right="Print and check", toc=[(1, "Assembly"), (2, "Stage 1 — Print and check the parts")], stage=1)


# ================================================================ STAGE 2 CUT
def stage_cut():
    rope_rows = [(f'<span class="swatch" style="background:var(--{c})"></span>{n}', f"{L}", how) for n, L, c, how in ROPE_CUTS]
    tube_rows = [(n, f"{L}", w) for n, L, w in PTFE_CUTS]
    body = f'''{stagehead(2, "Cut, drill and label the stock", "Plywood, rods, rope and PTFE tube. Label every piece the moment it is cut.")}
<div class="row"><div class="col">
<h3 class="mt0">Wire rope (1/16in 7×19) {tag("v")}</h3>
{table(["Piece", "Cut (mm)", "Ends"], rope_rows, num=(1,))}
<p class="small">Lengths include 60 mm for each double-crimp loop. Total 7.1 m — have at least 9 m.</p>
<h3>PTFE tube 4 × 2 mm {tag("v")}</h3>
{table(["Piece", "Cut (mm)", "Runs"], tube_rows, num=(1,))}
<p class="small">Each includes 10 mm to trim at fitting. Total 3.7 m — one 5 m roll.</p>
</div><div class="col">
<h3 class="mt0">Rods and pipe {tag("v")}</h3>
{table(["Stock", "Cut", "For"], [("5/16in rod", "205 mm", "lever axle (H14)"), ("5/16in rod", "274 mm", "slew spool axle (H15)"),
                                ("5/16in rod", "3 × 230 mm", "lever handles (H16)"), ("8-32 threaded rod", "2 × 42 mm", "boom split pins (H10)"),
                                ("8-32 threaded rod", "2 × 22 mm", "stick split pins (H11)"), ("8-32 threaded rod", "1 × 65 mm", "bucket pin (H12)"),
                                ("3/4in PEX-B", "120 mm", "turret tube (S06)"), ("2in sch 40 PVC", "141 mm", "conduit (S08), socket floor to socket floor"),
                                ("1/2in copper", "elbow + 50 mm", "pedestal elbow (S07)")])}
{steps(["Cut all ten rope and PTFE pieces. Wrap tape round the rope at the cut mark and cut through the tape.",
        "Write the piece name on a tape flag at <b>both</b> ends of every rope and tube (e.g. “STICK — box end”).",
        "On the three arm ropes, mark the midpoint with a second colour (692 / 910.5 / 1086.5 mm).",
        "Cut the rods square; chamfer the ends lightly with a file so they slide through printed bores. Run a nut on and off each 8-32 piece to clean "
        "the thread.",
        "Cut the PVC and copper square and deburr inside and out — a burr will cut a rope."], 0)}
</div></div>
{box("warn", "Rope ends.", " Tape every cut end until it is crimped. Loose wires go through skin easily.")}
<h3>Plywood</h3>
<p>Cut the 21 panels to the sizes on page “Wood and stock” and drill the holes in Appendix B. Holes per panel: box floor 1 (+ Ø22 × 7
counterbore from below), box front 7, box top 1 hole + 3 slots, bearing blocks 1 each, pedestal top 5, pedestal wall −u 5, shelf 1, sandbox wall −u 7.
{tag("v")}</p>
{box("caut", "Drill the box front and the sandbox wall −u together.", " Their seven holes must line up (the same M3 bolts pass through both). "
     "Clamp the two panels face to face, box front on top, and drill through both. " + tag("a"))}
{box("open", "Open item 4 — axle nuts.", " The axle and spool rod ends carry 5/16in nuts. If your 5/16in rod is smooth (one design note says so), "
     "thread about 15 mm at each end of the 205 mm and 274 mm rods with a 5/16-18 die, or substitute 5/16in shaft collars. See Appendix D.")}'''
    page(body, tab="Stage 2", right="Cut, drill and label", toc=[(2, "Stage 2 — Cut, drill and label")], stage=2)


# ================================================================ STAGE 3 SANDBOX
def figk(fid, width_in, caption, kc=2, gutter=(0.08, 0.08, 0.08, 0.08), **kw):
    """Figure with numbered balloons next to the parts and a key underneath."""
    return fig(fid, width_in, caption, gutter=gutter, legend=True, key_cols=kc, **kw)


def stage_sandbox():
    body = f'''{stagehead(3, "Build the sandbox", "Floor and four walls, glued and screwed. The −u wall is the drilled one: the control box bolts to its outside.")}
<div class="row"><div class="fc">{figk("sandbox-exploded", 4.45, "Sandbox: four walls on the floor.", max_h_in=4.0)}</div>
<div class="fc">{figk("sandbox-corner", 2.65, "Corner joint, walls see-through.", kc=1, max_h_in=4.0)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("W17"), "Sandbox floor 610 × 610", 1), (pid("W18"), "Wall −u (box side, 7 holes)", 1), (pid("W19"), "Wall +u", 1),
       (pid("W20"), "Wall −v", 1), (pid("W21"), "Wall +v", 1), (pid("H20"), "#6 × 1-1/4in wood screw", 32), ("", "Wood glue", "")])}
</div><div class="col">
{steps(["Glue and screw the four walls <b>on top of</b> the floor: 4 screws up through the floor into each wall’s bottom edge.",
        "The −v and +v walls fit between the −u and +u walls: 4 screws through each ±u wall into the ends of the ±v walls.",
        "Put the −u wall’s holes at the bottom: the Ø62 conduit hole centre is 80 mm above the wall’s bottom edge and 297 mm from its −v end. " + tag("v"),
        "Check the box is square (equal diagonals) before the glue sets."])}
</div></div>
{box("check", "Check.", " Walls flush with the floor edges; diagonals equal within 2 mm; the −u wall’s Ø62 hole is low, near the middle.")}
{box("mistake", "Hole side.", " Fitting the −u wall upside down puts the conduit hole 150 mm too high. The hole is 80 mm from the <b>bottom</b>.")}'''
    page(body, tab="Stage 3", right="Sandbox", toc=[(2, "Stage 3 — Sandbox")], stage=3)


# ================================================================ STAGE 4 PEDESTAL
def stage_pedestal():
    body = f'''{stagehead(4, "Build the pedestal", "A plywood column inside the sandbox that carries the slewing ring on top and the slew drum inside.")}
{figk("pedestal-exploded", 7.3, "Pedestal walls and top on the sandbox floor. Wall +u is screwed only: it is the service hatch.", kc=3, max_h_in=4.6)}
<div class="row"><div class="col w40">
{need([(pid("W09"), "Pedestal top (5 holes)", 1), (pid("W10"), "Wall −u (conduit wall, 5 holes)", 1), (pid("W11"), "Wall +u (removable)", 1),
       (pid("W12"), "Wall −v", 1), (pid("W13"), "Wall +v", 1), (pid("H20"), "#6 × 1-1/4in wood screw", 32)])}
{box("open", "Open item 5 — fixing the pedestal down.", " The cut list says the pedestal screws to the sandbox floor, but the bill of materials "
     "counts no screws for it. Suggested: 4 extra #6 × 1-1/4in up through the sandbox floor into the ±v walls (2 each). " + tag("a"))}
</div><div class="col">
{steps(["Glue and screw walls −v and +v between walls −u and +u (4 screws per joint, through the ±u walls). Fit wall +u <b>with screws only, "
        "no glue</b>.",
        "Glue and screw the pedestal top onto the four walls (4 screws per wall). The top’s Ø26.2 hole is the PEX clearance; its four Ø3 holes "
        "are pilots for the base screws.",
        "Stand the pedestal on the sandbox floor, centred side to side, with wall −u (the drilled one) facing the sandbox’s −u wall.",
        "Set the gap between the inner face of the sandbox −u wall and the outer face of the pedestal’s wall −u to <b>81 mm</b>, so the two "
        "Ø62 conduit holes line up. " + tag("v")])}
{box("check", "Check.", " Sight through the sandbox wall’s Ø62 hole: you see the pedestal wall’s Ø62 hole centred behind it. The pedestal top is level.")}
</div></div>'''
    page(body, tab="Stage 4", right="Pedestal (1/2)", toc=[(2, "Stage 4 — Pedestal")], stage=4)
    body = f'''<h2>Stage 4 — continued: conduit fitting, copper elbow, shelf</h2>
<div class="row"><div class="fc">{figk("pedestal-fitting", 3.55, "P17 on wall −u, seen from inside the pedestal.", kc=1, max_h_in=1.95)}</div>
<div class="fc">{figk("pedestal-elbow", 3.55, "Copper elbow and its support.", kc=1, max_h_in=1.95)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("P17"), "Conduit fitting, pedestal end", 1), (pid("H04"), "M3 × 25 socket cap", 4), (pid("H08"), "M3 flat washer", 8),
       (pid("H07"), "M3 nut", 4), (pid("S07"), "1/2in copper elbow + 50 mm pipe", 1), (pid("P16"), "Elbow support", 1),
       (pid("H19"), "#6 × 3/4in wood screw", 5), ("", "Cable tie", 1), (pid("W14"), "Shelf", 1), (pid("W15"), "Shelf cleats", 2),
       (pid("H20"), "#6 × 1-1/4in wood screw", 8), (pid("P15"), "PEX bushing", 1)], "You need (this page)")}
</div><div class="col">
{steps(["Remove wall +u. Hold P17’s square flange flat against the <b>inside</b> of wall −u: the conduit socket opens toward the wall’s Ø62 "
        "hole; the round boss, with the small copper socket in its end face, points into the pedestal. Line up the 4 corner holes.",
        "Bolt it: M3 × 25 + flat washer from inside (head on the fitting flange), flat washer + nut outside the wall. Tighten evenly.",
        "Push the copper elbow’s horizontal leg into the fitting’s copper socket (8 mm deep); the other leg points straight up.",
        "Set the elbow support under the horizontal leg, screw it to the sandbox floor (2 × #6 × 3/4in) and cable-tie the elbow into its saddle.",
        "Screw the two cleats to the inside of walls −v and +v (#6 × 1-1/4in), lay the shelf on them, and screw the PEX bushing into the shelf "
        "hole, flange on top (3 × #6 × 3/4in)."])}
</div></div>
<div class="row"><div class="fc">{figk("pedestal-shelf", 3.5, "Cleats, shelf and PEX bushing (shelf and bushing lifted out).", kc=2, max_h_in=1.75)}</div>
<div class="col">{box("check", "Check.", " The elbow’s top opening is directly under the bushing’s bore (sight down through the bushing). The copper does "
     "not move when you pull it. " + tag("v"))}
{box("mistake", "Fitting turned round.", " If the big socket faces into the pedestal, the conduit cannot reach it and the copper socket faces the wall.")}</div></div>'''
    page(body, tab="Stage 4", right="Pedestal (2/2)")


# ================================================================ STAGE 5 SLEWING RING
def stage_turret():
    body = f'''{stagehead(5, "Slewing ring and turret", "The base screws to the pedestal; the turret rides on 57 BBs and is held down by the retaining ring.")}
<div class="row"><div class="fc">{figk("base-to-pedestal", 4.2, "Base onto the pedestal top.", kc=1, max_h_in=4.3)}</div>
<div class="fc">{figk("turret-tube", 2.9, "PEX tube into the turret hub.", kc=1, max_h_in=4.3)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("P12"), "Base (2026-09-29 file)", 1), (pid("H18"), "#8 × 1in wood screw", 4), (pid("P11"), "Tower", 1),
       (pid("S06"), "3/4in PEX-B tube, 120 mm", 1), (pid("H04"), "M3 × 25 (hub clamp)", 1), (pid("H09"), "M3 split-lock washer", 1),
       (pid("H07"), "M3 nut", 1)])}
</div><div class="col">
{steps(["Set the base on the pedestal top with its centre bore over the Ø26.2 hole. Turn it until its four counterbored holes (45° positions, "
        "r 38 mm) sit over the four Ø3 pilots.",
        "Screw it down with 4 × #8 × 1in in the counterbores. Do not over-tighten into the plywood.",
        "Push the PEX tube up into the tower’s clamp hub from below until its top is <b>3 mm below the top face of the turret flange</b> "
        "(tube top at z 22, flange top at z 25). " + tag("v"),
        "Tighten the hub’s pinch clamp: M3 × 25 through the hub, split-lock washer and nut on the far side. The tube must not turn in the hub."])}
</div></div>
{box("caut", "Clamp the tube before the turret goes on.", " Once the turret sits on the balls, the hub clamp is inside the base and cannot be reached. " + tag("v"))}'''
    page(body, tab="Stage 5", right="Slewing ring and turret (1/2)", toc=[(2, "Stage 5 — Slewing ring and turret")], stage=5)
    body = f'''<h2>Stage 5 — continued: balls, retaining ring, slew drum</h2>
<div class="row"><div class="fc">{figk("slewing-ring-exploded", 4.0, "Slewing ring, exploded and cut in half to show the race.", kc=1, max_h_in=3.4)}</div>
<div class="col">
{need([(pid("S05"), "6 mm BBs", 57), (pid("P13"), "Retaining ring", 1), (pid("H02"), "M3 × 12 socket cap", 8), (pid("H09"), "M3 split-lock washer", 9),
       (pid("H07"), "M3 nut", 9), (pid("P14"), "Pedestal slew drum", 1), (pid("H04"), "M3 × 25 (drum clamp)", 1)], "You need (this page)")}
{figk("slew-drum", 3.1, "Slew drum on the PEX tube inside the pedestal (wall +u removed).", kc=1, max_h_in=2.2)}
</div></div>
{steps(["Slide an M3 nut into each of the 8 slots in the outside of the base rim, flat side up, until it lines up with the hole above it.",
        "Lay the 57 BBs in the base’s race (the 45° groove round the rim). They fill the circle with about 0.4 mm between balls.",
        "From inside the pedestal (wall +u off), hold the slew drum under the shelf, hub up. Lower the turret: the PEX tube goes down through the "
        "base, the pedestal top, the bushing and into the drum. The turret flange settles on the balls.",
        "Lay the retaining ring on the rim and fit the 8 × M3 × 12, a split-lock washer under each head, into the nuts. Tighten them in a cross "
        "pattern, a little at a time.",
        "Slide the drum up or down the tube until the tube’s end is 2 mm below the drum’s underside, and tighten its pinch clamp (M3 × 25, "
        "lock washer, nut) lightly. Its rotation is set in Stage 10."], 4)}
<div class="row"><div class="col">{box("check", "Check — turret.", " The turret turns by hand with no rocking and no lift. The model allows 0.65 mm lift and "
     "1.1° rock before parts touch. If it rocks, shim under the retaining ring; if it binds, loosen the ring screws evenly a quarter turn. " + tag("v"))}</div>
<div class="col">{box("caut", "Count the balls.", " 57 balls. One missing makes a gap that knocks as the turret turns; one extra jams the ring.")}</div></div>'''
    page(body, tab="Stage 5", right="Slewing ring and turret (2/2)")


# ================================================================ STAGE 6 CONTROL BOX
def stage_box():
    body = f'''{stagehead(6, "Build the control box", "Box carcass, lever axle with its three hubs, the slew spool and the two sleeve posts. The left side and the top go on later.")}
{figk("box-exploded", 7.3, "Control box panels.", kc=4, max_h_in=4.7)}
<div class="row"><div class="col w40">
{need([(pid("W01"), "Box floor", 1), (pid("W02"), "Box front (7 holes)", 1), (pid("W03"), "Box rear", 1), (pid("W04"), "Box right side", 1),
       (pid("W05"), "Box left side (later in this stage)", 1), (pid("H20"), "#6 × 1-1/4in wood screw", 32), ("", "Wood glue", "")])}
</div><div class="col">
{steps(["Glue and screw the front, rear and right side onto the floor (4 screws per edge, up through the floor).",
        "Join the front and rear to the right side (4 screws per joint, through the front and rear).",
        "The front’s Ø62 hole is low (centre 80 mm above the floor’s top face) and right of centre: 282 mm from the box’s right-hand (−v) "
        "side, 123 mm from its left. " + tag("v"),
        "Leave the left side and the top off for now."])}
{box("caut", "Box size.", " These are the modelled box sizes (250 × 405 × 242). If you want the smaller box of Appendix E, its panels, rods "
     "and two reprinted hubs all change — decide before cutting.")}
</div></div>'''
    page(body, tab="Stage 6", right="Control box (1/3)", toc=[(2, "Stage 6 — Control box")], stage=6)
    body = f'''<h2>Stage 6 — continued: lever axle and hubs</h2>
{figk("axle-stack", 7.3, "Lever axle stack, exploded along the axle: blocks, three hubs, washers and nuts.", kc=3, max_h_in=4.6)}
<div class="row"><div class="col w40">
{need([(pid("W07"), "Axle bearing block left", 1), (pid("W08"), "Axle bearing block right", 1), (pid("H14"), "5/16in rod, 205 mm", 1),
       (pid("P19"), "Lever hub, boom", 1), (pid("P20"), "Lever hub, stick", 1), (pid("P21"), "Lever hub, bucket", 1),
       (pid("H17"), "5/16in nut + SAE washer", 2), (pid("H19"), "#6 × 3/4in wood screw", 4)], "You need (this page)")}
</div><div class="col">
{steps(["On the bench, slide onto the rod in this order from the left (+v) end: left block, <b>boom</b> hub, <b>stick</b> hub, <b>bucket</b> "
        "hub, right block. The handle sockets all point the same way (up).",
        "Centre the rod (102.5 mm each side of the middle). Fit a washer and a nut outside each block, finger-tight plus a quarter turn: the "
        "hubs must still turn freely. They are 0.5 mm apart by design. " + tag("v"),
        "Stand the stack on the box floor: axle 93 mm from the floor’s rear (−u) edge, left block’s outer face 22.5 mm in from the floor’s left "
        "(+v) edge. Screw each block from below: 2 × #6 × 3/4in. " + tag("v"),
        "Now fit the left side (glue + 4 screws per edge)."])}
</div></div>
{box("mistake", "Hub order.", " Boom (P19) on the operator’s left, stick (P20) centre, bucket (P21) right. The hubs look alike — check the "
     "label on each before sliding it on. " + tag("v"))}'''
    page(body, tab="Stage 6", right="Control box (2/3)")
    body = f'''<h2>Stage 6 — continued: slew spool, riser and sleeve posts</h2>
<div class="row"><div class="fc">{figk("spool-stack", 3.3, "Spool axle, riser, spool and posts.", kc=1, max_h_in=3.6)}</div>
<div class="fc">{figk("box-internals", 3.8, "Inside the box at the end of Stage 6 (top, rear and left side hidden).", kc=1, max_h_in=3.0)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("P25"), "Spool riser", 1), (pid("P23"), "Slew spool", 1), (pid("H15"), "5/16in rod, 274 mm", 1), (pid("H17"), "5/16in nut + SAE washer", 1),
       (pid("P26"), "Slew sleeve post", 2), (pid("H19"), "#6 × 3/4in wood screw", 7), (pid("P18"), "Box conduit fitting (loose for now)", 1)],
      "You need (this page)")}
{box("note", "Post positions", " come from the model: post A at u −329, v −120; post B at u −274, v −216 (design frame). Each post’s "
     "counterbore lines up with the spool’s drum tangent. " + tag("v"))}
</div><div class="col">
{steps(["Push the 274 mm rod up through the floor’s Ø8.5 hole from below. Fit a washer and a nut on its bottom end inside the Ø22 × 7 "
        "counterbore under the floor (the model uses a thin jam nut there so it stays flush).",
        "Slide the riser down the rod onto the floor and screw it through its flange (3 × #6 × 3/4in).",
        "Slide the spool onto the rod, drum end down, onto the riser. There is no washer between them: the gap is 0.5 mm. " + tag("v"),
        "Screw the two sleeve posts to the floor beside the spool, each with 2 × #6 × 3/4in through its base. Post <b>A</b> is the one nearer "
        "the levers. Each post’s counterbore faces away from the spool.",
        "Put the box conduit fitting (P18) aside — it goes in at Stage 7, together with the PTFE tubes."], 4)}
{box("check", "Check.", " Each hub turns freely on the axle and the spool turns freely on its rod. Nothing in the box rubs the hubs.")}
</div></div>'''
    page(body, tab="Stage 6", right="Control box (3/3)")


# ================================================================ STAGE 7 CONDUIT, TUBES, BOX
def stage_conduit():
    body = f'''{stagehead(7, "Conduit, PTFE tubes and box mounting", "The conduit links box and pedestal; the four arm tubes are seated in the box fitting, threaded through to the turret, then the box is bolted on.")}
<div class="row"><div class="fc">{figk("conduit-insert", 3.9, "Conduit into the pedestal fitting through the sandbox wall.", kc=1, max_h_in=3.7)}</div>
<div class="fc">{figk("tube-window", 3.2, "Box fitting P18 from the conduit side, with the tube and rope paths.", kc=1, max_h_in=3.7)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("S08"), "2in PVC conduit, 141 mm", 1), (pid("P18"), "Box conduit fitting", 1), (pid("S04"), "PTFE: stick_hi, stick_lo, bucket_hi, bucket_lo", 4)])}
{box("note", "Why this order.", " The tubes stop in P18 on the conduit side, and P18 is clamped between the box front and the sandbox wall by the "
     "same bolts. Once those bolts are in, the window cannot be reached. " + tag("d"))}
</div><div class="col">
{steps(["Push the conduit through the sandbox wall’s Ø62 hole from outside, across the gap, through the pedestal wall’s Ø62 hole and into "
        "P17’s socket until it bottoms (12 mm deep). About 24 mm stays outside the sandbox wall. " + tag("v"),
        "Seat the box end of the four arm tubes in P18’s rounded window — from the <b>conduit side</b> (the side with the big socket). They sit "
        "side by side and stop on the window floor.",
        "Feed the four free ends out through the box front’s Ø62 hole from inside the box, into the conduit’s outer end, along the conduit, out "
        "through P17’s window, into the copper elbow and up the PEX tube until they come out at the top of the turret.",
        "Slide the box against the sandbox wall: the conduit end enters the box front’s hole and P18’s socket. P18 sits inside the box front "
        "with its socket on the conduit."])}
</div></div>'''
    page(body, tab="Stage 7", right="Conduit, tubes, box (1/2)", toc=[(2, "Stage 7 — Conduit, PTFE tubes and box mounting")], stage=7)
    body = f'''<h2>Stage 7 — continued: bolt the box on, seal the conduit</h2>
{figk("box-mount", 7.3, "Box against the sandbox wall: four fitting bolts and two corner bolts (box top, left side and sandbox walls hidden).", kc=2, max_h_in=3.5)}
<div class="row"><div class="col">
{need([(pid("H06"), "M3 × 35 socket cap", 4), (pid("H05"), "M3 × 30 socket cap", 2), (pid("H08"), "M3 flat washer", 12), (pid("H07"), "M3 nut", 6),
       ("", "Silicone", "")], "You need (this page)")}
{steps(["Line up P18’s four corner holes with the box front’s and the sandbox wall’s holes. Fit 4 × M3 × 35 from inside the box: flat "
        "washer under the head (on P18’s flange), flat washer and nut on the sandbox side.",
        "Fit the two lower-corner bolts: M3 × 30 through the box front and the sandbox wall, flat washers both sides.",
        "Tighten all six evenly. Seal round the conduit at the outside of the sandbox wall with silicone.",
        "At the turret, pull the four tubes up gently and leave them hanging out of the top for Stage 8. Leave their spare length coiled "
        "loosely in the conduit."], 4)}
</div><div class="col">
{figk("ptfe-route", 3.5, "Where the four arm tubes run when finished.", kc=1, max_h_in=2.4)}
{box("check", "Check.", " Each tube slides a few mm when pushed at the turret end, and does not come out of P18’s window when pulled. The "
     "box stands flat on the same ground as the sandbox.")}
</div></div>'''
    page(body, tab="Stage 7", right="Conduit, tubes, box (2/2)")


# ================================================================ STAGE 8 ARM
def stage_arm():
    body = f'''{stagehead(8, "Assemble the arm", "Boom, stick and bucket, each with its drum, its rope’s joint end and its PTFE tubes laid in before the halves close.")}
{box("open", "Read Appendix D items 1–3 first.", " The CAD shows three fit problems in this stage: the stick-drum key screws collide, two stick "
     "lug holes merge, and the joining-lug screws are enclosed once a member is closed. The steps below say where each one matters.")}
<div class="row"><div class="fc">{figk("boom-drum-keys", 2.85, "Boom drum with its four key screws.", kc=1, max_h_in=3.2)}</div>
<div class="fc">{figk("boom-half-open", 4.25, "Boom right half with drum, PTFE tubes and boom rope.", kc=1, max_h_in=3.5)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("P05"), "Boom drum", 1), (pid("H02"), "M3 × 12 socket cap (key screws)", 4), (pid("S01"), "Boom rope 1384 mm (midpoint marked)", 1),
       (pid("S02"), "Single crimp sleeve", 1), (pid("P02"), "Boom half, right", 1), (pid("P01"), "Boom half, left", 1),
       (pid("H03"), "M3 × 20 socket cap (lugs)", 4), (pid("H07"), "M3 nut", 4)], "You need — boom")}
</div><div class="col">
{steps(["Screw two M3 × 12 into each face of the boom drum (4 screws, into the Ø2.6 pilots) until the underside of each head is <b>10 mm</b> "
        "from the drum face. The heads will sit in pockets in the boom walls. " + tag("v"),
        "Crimp the single sleeve onto the boom rope at its midpoint mark. Seat the sleeve in the drum’s crimp pocket and wrap one tail each way "
        "round the groove.",
        "Lay the drum in the right boom half (P02) so its two right-hand screw heads drop into the wall pockets at the boom root.",
        "Lay the four PTFE tubes from the turret into P02’s channels: the two <b>stick</b> tubes to their stop at the boom tip; the two "
        "<b>bucket</b> tubes on through the boom tip. Trim each stick tube so it seats on its stop."])}
</div></div>'''
    page(body, tab="Stage 8", right="Arm (1/4)", toc=[(2, "Stage 8 — Arm")], stage=8)
    body = f'''<h2>Stage 8 — continued: close the boom and pin it to the tower</h2>
<div class="row"><div class="fc">{figk("boom-close", 3.55, "Closing the boom.", kc=1, max_h_in=3.8)}</div>
<div class="fc">{figk("boom-pins", 3.55, "Boom split pins: one short rod per side.", kc=1, max_h_in=3.8)}</div></div>
<div class="row"><div class="col">
{steps(["Feed both boom rope tails down into the tower and the PEX tube, and push them on down to the box (see the tip).",
        "Close the boom: put the left half (P01) on, the drum’s left screw heads in its pockets.",
        "Joining lugs: 4 × M3 × 20 + nut clamp the halves. Open item 3: in the CAD the lug screws cannot be reached once the halves are "
        "closed — decide how you will hold the halves before this step.",
        "Set the boom root between the tower cheeks. Push a 42 mm 8-32 rod through each cheek into the boom wall until its inner end is flush "
        "with the boom’s inner wall.",
        "Fit two 8-32 nuts on the outer end of each pin and lock them against each other (jam pair) against the cheek."], 4)}
</div><div class="col">
{need([(pid("H10"), "8-32 rod, 42 mm", 2), (pid("H13"), "8-32 nut", 4)], "You need — boom pins")}
{box("tip", "Threading a bare tail down the elbow.", " Both fittings have bell-mouth entries on the conduit side. If a boom tail will not find "
     "its Ø2.4 hole at the bottom of the elbow, thread it up from the box side instead (through P18, the conduit, P17, the elbow and the PEX), "
     "take it over the drum and send the other tail down.")}
{box("mistake", "Pin too long inside.", " A split pin pushed past the boom’s inner wall blocks the PTFE tubes that cross the joint axis. "
     "The inner ends must be flush. " + tag("v"))}
</div></div>'''
    page(body, tab="Stage 8", right="Arm (2/4)")
    body = f'''<h2>Stage 8 — continued: stick</h2>
<div class="row"><div class="fc">{figk("stick-half-open", 4.6, "Stick right half: drum, bucket drum-axle, tubes and ropes.", kc=1, max_h_in=2.4)}</div>
<div class="fc">{figk("stick-drum-keys", 2.5, "Stick-drum key screws.", kc=1, max_h_in=1.85)}</div></div>
<div class="row"><div class="col w40">
{need([(pid("P06"), "Stick drum", 1), (pid("H02"), "Key screws — see Open item 1", 4), (pid("S01"), "Stick rope 1821 mm", 1),
       (pid("S02"), "Single crimp sleeve", 2), (pid("S01"), "Bucket rope 2173 mm", 1), (pid("P07"), "Bucket drum-axle", 1),
       (pid("P04"), "Stick half, right", 1), (pid("P03"), "Stick half, left", 1), (pid("H03"), "M3 × 20 + nut (lugs)", "3–4"),
       (pid("H11"), "8-32 rod, 22 mm", 2), (pid("H13"), "8-32 nut", 4)], "You need — stick")}
{figk("stick-pins", 2.85, "Stick split pins.", kc=1, max_h_in=1.9)}
</div><div class="col">
{steps(["Stick drum key screws: each pilot goes right through the 10 mm drum, and the model puts an M3 × 12 into it from each side with the "
        "heads 6.2 mm from the faces — the tips then overlap by 1.6 mm. Use M3 × 8 (in your kit) or shorten the M3 × 12 by 2 mm. " + tag("o"),
        "Crimp the stick rope’s single sleeve at its midpoint, seat it in the stick drum’s pocket and wrap the tails. Lay the drum in P04 "
        "with its screw heads in the pockets.",
        "Push each stick tail into the end of its stick tube at the boom tip and on down the tube to the box.",
        "Bucket drum-axle: put its journals in the nose holes of P04. Crimp the bucket rope’s sleeve at its midpoint, seat it in the "
        "drum-axle’s pocket, wrap the tails, and push them into the bucket tubes (laid in P04’s channels to their stop in the nose) and on to "
        "the box.",
        "Close with P03. Lugs: the two at the stick root overlap (2.9 mm apart) — only one screw fits there (Open item 2).",
        "Fit the stick to the boom tip with a 22 mm 8-32 rod each side (inner ends flush) and a jam pair outside."])}
</div></div>'''
    page(body, tab="Stage 8", right="Arm (3/4)")
    body = f'''<h2>Stage 8 — continued: bucket</h2>
<div class="row"><div class="fc">{figk("bucket-assembly", 3.9, "Bucket, ears and bucket pin, exploded along the pin.", kc=1, max_h_in=4.6)}</div>
<div class="col">
{need([(pid("P08"), "Bucket", 1), (pid("P09"), "Bucket ear, left (2026-09-29 file)", 1), (pid("P10"), "Bucket ear, right (2026-09-29 file)", 1),
       (pid("H12"), "8-32 rod, 65 mm (bucket pin)", 1), (pid("H13"), "8-32 nut", 4), ("", "CA or epoxy", "")], "You need — bucket")}
{box("caut", "Glue last.", " Glue the ears only with the bucket pin fitted and tightened, so the hex sockets, the pin and the bucket lugs line up.")}
{box("mistake", "Ears swapped.", " The left ear (P09) goes on the +v end of the drum-axle. Swapped ears do not seat on the bucket lugs.")}
</div></div>
<div class="row"><div class="col">
{steps(["Dry fit: slide each ear’s hex socket onto the drum-axle’s hex end (left ear on the +v end). The ears’ lower blocks rest on the "
        "bucket’s lugs and the small pin under each ear goes into the bucket.",
        "Push the 65 mm rod through the left ear, the drum-axle’s bore and the right ear. Centre it.",
        "Fit a jam pair on each end, snug against the ears: the rod clamps the ears to the drum-axle’s shoulders."])}
</div><div class="col">
{steps(["When the bucket hangs straight and swings freely, glue each ear’s lower block to its bucket lug (CA or epoxy), as on the original "
        "EX-MA. Let it cure fully before rigging.",
        "Swing the bucket, stick and boom by hand through their ranges: nothing may rub."], 3)}
</div></div>
{box("check", "Check — joint ranges.", f" Boom {ex.WORKING['boom'][0]:.0f}° … +{ex.WORKING['boom'][1]:.0f}°, stick {ex.WORKING['stick'][0]:.0f}° … "
     f"+{ex.WORKING['stick'][1]:.0f}°, bucket {ex.WORKING['bucket'][0]:.0f}° … +{ex.WORKING['bucket'][1]:.0f}° from the modelled pose, with no rubbing. "
     "The model is contact-free well beyond these (boom −42…+80°, stick −54…+150°, bucket −56…+170°). " + tag("v"))}'''
    page(body, tab="Stage 8", right="Arm (4/4)")


# ================================================================ STAGE 9 RIG ARM ROPES
def rig_extra(meta, fs, x0, y0):
    P = meta["points"]
    out = []
    for k, (lab, key) in enumerate((("boom +2.5°", "pb"), ("stick +2.5°", "ps"), ("bucket +15°", "pk"))):
        x, y = P[key][0] - x0, P[key][1] - y0
        out.append(sv.circ(x, y, fs * 1.0, "none", sv.ACC, fs * 0.15))
        tx, ty = x + fs * 1.6, y - fs * 1.8
        out.append(f'<rect x="{tx - fs * 0.3:.1f}" y="{ty - fs * 1.05:.1f}" width="{sv.text_w(lab, fs * 1.1) + fs * 0.6:.1f}" height="{fs * 1.5:.1f}" '
                   f'rx="{fs * 0.3:.1f}" fill="{sv.ACC}"/>')
        out.append(sv.t(tx, ty, lab, f"{fs * 1.1:.1f}", "start", 700, "#fff"))
    return "".join(out)


def stage_rig():
    body = f'''{stagehead(9, "Rig the arm ropes at the levers", "Set every joint to the middle of its range and every lever upright, then loop each tail onto its anchor and tension it.")}
{fig("rigging-pose", 7.3, "The rigging pose: each joint at the middle of its working range, measured from the modelled pose (+ = raised).",
     gutter=(0.05, 0.05, 0.05, 0.05), extra=rig_extra, max_h_in=3.8)}
<div class="row"><div class="col w45">
<h3 class="mt0">Configuration: zero positions {tag("v")}</h3>
{table(["Joint", "Working range", "Rig at"], [("Boom", "−40° … +45°", "+2.5°"), ("Stick", "−45° … +50°", "+2.5°"), ("Bucket", "−55° … +85°", "+15°"),
                                             ("All levers", "slot end to slot end", "upright"), ("Slew", "−90° … +90°", "arm straight out, wheel centred")], cls="t compact")}
<p class="small">Crimping at mid-range leaves the same rope wrap on the joint drum at both ends of travel. Prop the arm in this pose with a block
while you work. {tag("v")}</p>
{need([(pid("S03"), "Double crimp sleeve", 6), (pid("H01"), "M3 × 10 button head (in the hubs)", 6), (pid("H08"), "M3 flat washer", 12),
       (pid("H09"), "M3 split-lock washer", 6), (pid("H07"), "M3 nut", 6)])}
</div><div class="col">
{steps(["Inside the box each tail comes out of P18’s box face. Take each strand to its own lever drum: boom tails to the boom hub, stick to "
        "the stick hub, bucket to the bucket hub. Strands never cross.",
        "Wrap the tail into the groove and pass it through the rim hole beside its anchor slot (upper strand to the upper anchor, lower to the "
        "lower).",
        "With the anchor screw at the <b>outer</b> end of its slot (nearest the rope hole), pull the rope just taut and crimp a loop with a "
        "double sleeve so that it sits on the screw.",
        "Stack on the screw: flat washer — rope loop — flat washer; the split-lock washer and nut on the other side of the web. Snug only."])}
{box("mistake", "Crimping with the joint off-centre.", " A crimp made with the joint at one end of its range leaves no rope wrap at the other "
     "end, and the lever stops short. Re-check the rigging pose before every crimp.")}
</div></div>'''
    page(body, tab="Stage 9", right="Arm ropes (1/2)", toc=[(2, "Stage 9 — Rig the arm ropes")], stage=9)
    body = f'''<h2>Stage 9 — continued: tension and direction</h2>
<div class="row"><div class="fc">{figk("lever-hub-detail", 3.9, "Lever hub (boom): anchors, rope holes and clamps.", kc=1, max_h_in=4.3)}</div>
<div class="fc">{figk("lever-motion", 3.2, "Boom lever from the side (box cut away): push = forward.", kc=1, max_h_in=4.3)}</div></div>
<div class="row"><div class="col">
{steps(["Tension: slide each anchor screw along its slot <b>toward the drum centre</b> (away from the rope hole) until both strands are "
        "taut with the joint still at mid-range and the lever upright, then tighten the nut. Each slot gives about 8 mm of take-up.",
        "Repeat for the other strand of the same circuit so the lever stays upright when both are taut.",
        "Direction: push the lever forward (toward the sandbox). It must give boom down, stick out, bucket dump. If one is reversed, undo "
        "that rope at the joint drum and wrap it the other way round the drum.",
        "Move each lever slowly end to end and watch its joint: smooth, no slack strand, the rope stays in every groove."], 4)}
</div><div class="col">
{box("open", "Open item 7 — which way to slide.", " The checklist says “slide the anchors outward”. In the CAD the rope enters each slot "
     "at its <b>outer</b> end, so moving the screw inward is what takes up rope. Trust what you see: the strand tightens as the screw moves "
     "away from the rope hole. " + tag("v"))}
{box("check", "Check — no coupling.", " Hold the bucket lever still and move the boom and stick levers through their full travel: the "
     "bucket must not move. The model predicts at most 0.66 mm of rope movement from tube bending (“Bowden coupling”). " + tag("v"))}
</div></div>'''
    page(body, tab="Stage 9", right="Arm ropes (2/2)")


# ================================================================ STAGE 10 SLEW
def stage_slew():
    ped = {"A": (129.09 - 180.0, "lane A pocket (upper)"), "B": (-117.68 + 180.0, "lane B pocket (lower)")}
    spool = {"A": (-60.0, "anchor, upper lane"), "B": (120.0, "anchor, lower lane")}
    body = f'''{stagehead(10, "Rig the slew ropes", "Two ropes in two PTFE sleeves: each one ends in a pocket on the pedestal drum and in a loop on the spool.")}
{figk("slew-path", 7.3, "Slew path from above (box, pedestal and sandbox walls cut away): spool → posts → sleeves → conduit → pedestal fitting → slew drum.",
      kc=3, max_h_in=3.7)}
<div class="row"><div class="col w45">
{need([(pid("S04"), "PTFE slew sleeve A 339 mm, B 407 mm", 2), (pid("S01"), "Slew rope A 829 mm, B 900 mm", 2), (pid("S02"), "Single crimp sleeve", 2),
       (pid("S03"), "Double crimp sleeve", 2), (pid("H01"), "M3 × 10 button head (in the spool)", 2), (pid("H08"), "M3 flat washer", 4),
       (pid("H09"), "M3 split-lock washer", 2), (pid("H07"), "M3 nut", 2)])}
</div><div class="col">
{steps(["Push sleeve A from its post (the one nearer the levers) through P18’s upper slew hole on that side, along the conduit and into "
        "P17’s angled counterbore until it stops. Seat its other end in post A’s counterbore and trim the 10 mm extra. Same for sleeve B.",
        "Crimp a single sleeve on one end of rope A. Thread the other end through the pedestal-fitting exit, sleeve A and post A to the spool.",
        "Seat rope A’s crimp in the <b>upper</b>-lane pocket of the pedestal drum and wrap it half a turn in that lane. Rope B: lower lane."])}
{box("mistake", "Swapped lanes.", " Rope A (the shorter, 829 mm) runs in the <b>upper</b> lane on both drums and in sleeve A (339 mm). If "
     "ropes cross between the drums, the arm turns the wrong way.")}
</div></div>'''
    page(body, tab="Stage 10", right="Slew ropes (1/2)", toc=[(2, "Stage 10 — Rig the slew ropes")], stage=10)
    body = f'''<h2>Stage 10 — continued: drum position, spool loops, tension</h2>
<div class="figframe" style="padding:4px 10px;width:6.4in;margin:0 auto">{sv.slew_topview(ped, spool)}</div>
<div class="cap" style="width:6.4in;margin:0 auto 6px"><b>Fig. {fignum()}</b><span>Zero position seen from above, arm pointing straight out (+u):
pocket and anchor angles from the model. {tag("v")}</span></div>
<div class="row"><div class="col">
{steps(["Point the arm straight out (+u, away from the box). Turn the pedestal drum on the PEX tube until its pockets are at the angles in "
        "the diagram (lane A 51° to the right of the arm, lane B 62° to the left), then tighten its pinch clamp hard. The drum must not slip "
        "on the tube. " + tag("v"),
        "Turn the spool so its two anchors are at the angles in the diagram (wheel centred).",
        "Wrap each rope half a turn round its spool lane, pass it through the rim hole by its anchor, and crimp a loop (double sleeve) onto the "
        "anchor screw with the screw at the outer end of the slot: washer — loop — washer, lock washer and nut below the web.",
        "Tension both ropes by sliding the anchors toward the spool centre, keeping the arm straight out. Each slot gives about 12 mm.",
        "Turn the wheel left: the arm must swing to your left, 1 : 1, up to 90°. Then right to 90°."], 3)}
</div><div class="col">
{figk("spool-anchors", 3.4, "Spool anchors and lanes from above.", kc=1, max_h_in=2.3)}
{box("check", "Check — wrap left at the ends.", " At ±90° each rope must still have at least 90° of wrap on both drums (the model has "
     "90–270°). If a rope runs out early, the drum or the spool was not centred: re-centre and re-crimp. " + tag("v"))}
{box("caut", "Drum clamp.", " A slipping pedestal drum feels like “the wheel turns but the arm doesn’t”. Tighten the M3 × 25 pinch clamp "
     "before tensioning, and re-check it after the first test.")}
</div></div>'''
    page(body, tab="Stage 10", right="Slew ropes (2/2)")


# ================================================================ STAGE 11 TOP
def stage_top():
    body = f'''{stagehead(11, "Top panel, handles, knobs and wheel", "The top panel’s slots are the lever end stops. Fit it, push the handles through, and bolt the wheel on.")}
<div class="row"><div class="fc">{figk("top-exploded", 4.3, "Top panel, handles, knobs and wheel.", kc=1, max_h_in=4.8)}</div>
<div class="col">
{need([(pid("W06"), "Box top (3 slots, 1 hole)", 1), (pid("H20"), "#6 × 1-1/4in wood screw", 16), (pid("H16"), "5/16in rod handle, 230 mm", 3),
       (pid("P22"), "Lever knob", 3), (pid("H03"), "M3 × 20 (handle clamps)", 3), (pid("H03"), "M3 × 20 (drag clamps)", 3),
       (pid("H09"), "M3 split-lock washer", 9), (pid("H07"), "M3 nut", 9), (pid("P24"), "Slew wheel", 1), (pid("H03"), "M3 × 20 (wheel)", 3),
       (pid("H17"), "5/16in nut + washer (spool top)", 1), ("", "CA or epoxy", "")])}
</div></div>
<div class="row"><div class="col">
{steps(["Lower the top onto the box: the spool tube passes through its Ø24.4 hole (the top is the spool’s upper bearing). Screw it to the "
        "front, rear and both sides, 4 screws per edge — screws only, no glue, so it lifts off for service.",
        "Push each handle rod down through its slot into its hub socket (25 mm deep). Tighten the handle pinch clamp (M3 × 20, lock washer "
        "and nut).",
        "Glue a knob on each handle: the rod goes 14 mm into the knob’s bore."])}
</div><div class="col">
{steps(["Bolt the wheel to the spool’s top flange: 3 × M3 × 20, heads in the wheel’s counterbores, lock washer and nut under the flange.",
        "Fit the washer and nut on top of the spool axle. Snug it until the spool has no up-down play but still turns freely. " + tag("a"),
        "Fit the three drag-clamp screws (M3 × 20, lock washer, nut) loosely; they are set in Stage 12."], 3)}
</div></div>
{box("check", "Check.", " Each lever stops on the end of its slot at both ends of travel — the slot is the hard stop. The model has the handle "
     "touch the slot end exactly at the end of travel, with nothing else touching. " + tag("v"))}'''
    page(body, tab="Stage 11", right="Top, handles, wheel", toc=[(2, "Stage 11 — Top, handles, knobs and wheel")], stage=11)


# ================================================================ STAGE 12 TEST
def range_extra(meta, fs, x0, y0):
    P = meta["points"]
    mm = meta["mmPerPx"]
    out = []

    def to2d(key, u, z):
        c = {"pb": ex.P_BOOM, "ps": ex.P_STICK, "pk": ex.P_BUCKET}[key]
        return P[key][0] - x0 + (u - c[0]) / mm, P[key][1] - y0 - (z - c[1]) / mm

    defs = [("pb", ex.P_BOOM, ex.P_STICK, 95, ex.WORKING["boom"], "boom", "BOOM −40° … +45°"),
            ("ps", ex.P_STICK, ex.P_BUCKET, 70, ex.WORKING["stick"], "stick", "STICK −45° … +50°"),
            ("pk", ex.P_BUCKET, (334.0, 58.0), 40, ex.WORKING["bucket"], "bucket", "BUCKET −55° … +85°")]
    for key, c, ref, R, (lo, hi), col, lab in defs:
        a0 = math.degrees(math.atan2(ref[1] - c[1], ref[0] - c[0]))
        pts = [to2d(key, c[0] + R * math.cos(math.radians(a0 + a)), c[1] + R * math.sin(math.radians(a0 + a))) for a in range(int(lo), int(hi) + 1, 3)]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        colr = sv.CIRC[col]
        out.append(f'<path d="{d}" fill="none" stroke="#fff" stroke-width="{fs * 0.6:.1f}"/><path d="{d}" fill="none" stroke="{colr}" '
                   f'stroke-width="{fs * 0.28:.1f}"/>')
        (xa, ya), (xb, yb) = pts[-2], pts[-1]
        out.append(sv.arrow_head(xb, yb, xb - xa, yb - ya, fs * 1.1, colr))
        (xa, ya), (xb, yb) = pts[1], pts[0]
        out.append(sv.arrow_head(xb, yb, xb - xa, yb - ya, fs * 1.1, colr))
        cx, cy = to2d(key, c[0], c[1])
        for (x, y) in (pts[0], pts[-1]):
            out.append(sv.line(cx, cy, x, y, colr, fs * 0.08, dash=f"{fs * 0.4:.1f},{fs * 0.3:.1f}"))
        mx, my = pts[len(pts) // 2]
        out.append(f'<rect x="{mx - sv.text_w(lab, fs) / 2 - fs * 0.4:.1f}" y="{my - fs * 2.6:.1f}" width="{sv.text_w(lab, fs) + fs * 0.8:.1f}" '
                   f'height="{fs * 1.5:.1f}" rx="{fs * 0.3:.1f}" fill="{colr}"/>')
        out.append(sv.t(mx, my - fs * 1.5, lab, f"{fs:.1f}", "middle", 700, "#fff"))
    return "".join(out)


def stage_test():
    body = f'''{stagehead(12, "Final test and configuration", "Run every control through its full range, check for coupling, then set the lever friction.")}
{fig("ranges", 7.3, "Working ranges set by the lever slots, measured from the modelled pose shown (+ = raised).", gutter=(0.05, 0.05, 0.05, 0.05),
     extra=range_extra, crop=None, max_h_in=4.0)}
<div class="row"><div class="col">
<h3 class="mt0">Function test {tag("v")}</h3>
{steps(["Each lever, slowly, end to end: its joint moves through its whole working range and the handle stops on the slot ends.",
        "Wheel to −90° and +90°: the arm follows 1 : 1 and no rope jumps its groove.",
        "No coupling: move the boom and the stick through their ranges while watching the bucket. It must not move.",
        "At every end stop, look at the ropes: each stays in its groove, and no PTFE tube is pinched at a joint.",
        "Turn the turret by the wheel through ±90°: smooth, no knocking from the ball ring."])}
</div><div class="col">
<h3 class="mt0">Configuration: lever holding friction</h3>
{steps(["Drag clamps: with the arm extended, tighten each lever’s drag-clamp screw a little at a time until the lever holds its position when you "
        "let go. The boom needs the most; the bucket almost none.",
        "Re-tension every circuit after the first hour of use (rope stretch and crimp seating), using the slotted anchors."], 5)}
{table(["Lever", "Holding torque (model)", "Clamp force (µ 0.3)"], [("Boom", "0.65 N·m", "172 N"), ("Stick", "0.23 N·m", "60 N"),
                                                                ("Bucket", "0.04 N·m", "10 N")], num=(1, 2))}
<p class="small">From the box validation report {tag("v")}. Use them to compare levers: the boom clamp needs several times the stick’s.</p>
</div></div>
{box("check", "Done.", " When every check on this page passes, the build is complete. Keep the hardware bags: the spares are listed in Appendix A.")}'''
    page(body, tab="Stage 12", right="Test and configure", toc=[(2, "Stage 12 — Final test and configuration")], stage=12)


# ================================================================ OPERATION, MAINTENANCE, TROUBLESHOOTING
def operation():
    body = f'''<div class="kicker">After assembly</div><h1>Operation and maintenance</h1>
<div class="row"><div class="col">
<h3 class="mt0">Operating</h3>
<ul class="tight">
<li>Stand behind the box. Left hand: boom and stick levers. Right hand: bucket lever and slew wheel.</li>
<li>Move one control at a time at first. Push forward = boom down, stick out, bucket dump; wheel left = arm left.</li>
<li>The slot ends are the stops. Do not lever against them or force the wheel past ±90°.</li>
<li>Do not lift or carry the machine by the arm, the levers or the wheel. Carry the sandbox and the box together from below.</li>
<li>Dig in dry sand only. Brush sand off the slewing ring and out of the lever slots after use.</li></ul>
<h3>Service access {tag("v")}</h3>
{figk("service-access", 3.55, "The two service hatches: box top and pedestal wall +u.", kc=1, max_h_in=2.6)}
<ul class="tight">
<li><b>Box top</b> — lift off (screws only): lever hubs, anchors, spool, sleeve posts, box fitting.</li>
<li><b>Pedestal wall +u</b> — unscrew (screws only): slew drum clamp, copper elbow, sleeve ends. Clear the sand from that side first.</li>
<li><b>An arm half</b> — opening one half gives access to its drum, crimp pocket and tubes. See Open item 3 for how the halves are held.</li></ul>
</div><div class="col">
<h3 class="mt0">Maintenance schedule {tag("a")}</h3>
{table(["When", "Do"], [("After the first hour", "Re-tension all four circuits (rope stretch and crimp seating). " + tag("v")),
                         ("Every session", "Brush off sand; check the knobs and the handle clamps are tight."),
                         ("Monthly", "Check the jam nuts on the five joint pins and the 8 retaining-ring screws; check the slew drum clamp."),
                         ("If a lever feels slack", "Re-tension at its anchors (Stage 9)."),
                         ("If the arm drifts", "Tighten that lever’s drag clamp (Stage 12).")])}
<h3>Replacing a rope {tag("d")}</h3>
<ol style="padding-left:14px;margin:2px 0">
<li>Lift the box top; undo the two loops of that circuit at its lever drum.</li>
<li>Open the arm half that holds its joint drum and lift the crimp out of the pocket.</li>
<li>Pull the old rope out from the arm end; use it to measure the new one (cut lengths in Appendix C).</li>
<li>Re-rig as in Stages 8 and 9 (or 10 for slew).</li></ol>
</div></div>'''
    page(body, tab="Reference", right="Operation and maintenance", toc=[(1, "Reference"), (2, "Operation and maintenance")])


def troubleshooting():
    rows = [
        ("A lever moves the wrong joint", "Strands crossed in the box, or ropes swapped at the box fitting", "Each circuit’s two strands go to its own hub; the box fitting columns run boom / stick / bucket in the same order as the hubs (Stage 9)."),
        ("A joint moves the wrong way", "Rope wrapped the wrong way round the joint drum", "Reverse that rope’s wrap on its joint drum (Stage 9, step 7)."),
        ("Moving one lever moves another joint", "PTFE tube not seated at the box fitting or at its arm stop; tube pinched", "Re-seat both tube ends; check the tube is not trapped by a split pin or lug (Stage 8)."),
        ("Lever stops short of the slot end", "Rope crimped with the joint off-centre; rope too tight", "Return to the rigging pose and re-crimp (Stage 9)."),
        ("Lever floppy, joint lags", "Rope slack", "Slide the anchors toward the drum centre (Stage 9, step 5)."),
        ("Arm sags when you let go", "Drag clamp too loose", "Tighten that lever’s drag clamp (Stage 12, step 6)."),
        ("Lever very stiff", "Drag clamp too tight; axle nuts squeezing the hubs; hub rubbing a neighbour", "Ease the drag clamp; back the axle nuts off; hubs need their 0.5 mm gaps."),
        ("Rope jumps out of a groove", "Slack rope at an end stop", "Re-tension; check the joint is not driven past its working range."),
        ("Wheel turns, arm does not (or slips)", "Pedestal slew drum or turret-hub clamp slipping on the PEX tube", "Tighten both M3 × 25 pinch clamps (Stages 5 and 10)."),
        ("Arm turns the opposite way to the wheel", "Slew ropes crossed between lanes", "Rope A upper lane on both drums, rope B lower (Stage 10)."),
        ("Slew range less than ±90°", "Drum or spool not centred when the ropes were crimped", "Re-centre both (Stage 10, steps 4–5) and re-crimp."),
        ("Turret rocks or lifts", "Retaining ring too high", "Shim under the retaining ring (Stage 5 check)."),
        ("Turret binds or knocks", "Missing or extra BB; uneven ring screws; sand in the race", "57 balls; loosen the ring screws evenly; clean the race."),
        ("Bucket wobbles on its pin", "Jam nuts loose; ear glue joint failed", "Re-lock the jam pairs; re-glue the ear with the pin fitted."),
        ("Handle turns in its hub", "Handle pinch clamp loose", "Tighten the M3 × 20 handle clamp (Stage 11)."),
        ("Sand coming out at the box", "Conduit seal missing at the sandbox wall", "Seal round the conduit with silicone outside the wall (Stage 7)."),
        ("Rope frays at a fitting", "Burr on the copper or the PVC end", "Deburr; check the rope runs through the bell-mouth holes."),
    ]
    body = f'''<div class="kicker">After assembly</div><h1>Troubleshooting</h1>
<p class="lead">Find the symptom, check the likely cause, then go to the stage named in the fix. Causes come from how the circuits are built;
where a cause is general practice it is not tagged separately.</p>
{table(["Symptom", "Likely cause", "Fix"], rows)}'''
    page(body, tab="Reference", right="Troubleshooting", toc=[(2, "Troubleshooting")])


# ================================================================ APPENDICES
def app_bom():
    hw = [(pid(i), n, str(q), u) for i, n, q, u in HW]
    pr = [(pid(p[0]), p[3], str(p[4]), p[5], p[6].replace(" *", " (new file)")) for p in PARTS]
    body = f'''<div class="kicker">Appendix A</div><h1>Bill of materials</h1>
<p class="lead">From <span class="mono">2026-09-24-bill-of-materials.md</span> {tag("v")}; base and ear files updated to the 2026-09-29 rebuilds.</p>
<div class="row"><div class="col w50">
<h3 class="mt0">Printed parts</h3>{table(["ID", "Part", "Qty", "Material", "Plate"], pr, cls="t compact", num=(2,))}
</div><div class="col">
<h3 class="mt0">Hardware</h3>{table(["ID", "Item", "Qty", "Used for"], hw, cls="t compact", num=(2,))}
<p class="small">M3 counts all fit in the Fgruh kit. Spares left: 8-32 rod about 711 mm and 10 nuts; #4-40 and #6-32 screws unused.</p>
</div></div>'''
    page(body, tab="Appendix A", right="Bill of materials", toc=[(1, "Appendices"), (2, "A — Bill of materials")])


def panel_svg(p, width_mm=84.0, max_h=38.0):
    ax = [i for i in range(3) if "uvz"[i] != p.normal]
    A, B = p.size[ax[0]], p.size[ax[1]]
    sc = min((width_mm - 24) / A, (max_h - 12) / B)
    w, h = A * sc, B * sc
    ox, oy = 15, 4
    s = [f'<svg viewBox="0 0 {width_mm} {h + 14:.1f}" width="100%">']
    s.append(sv.rect(ox, oy, w, h, "#ead6ad", sv.INK, 0.3))
    letters = []
    for k, (kind, axis, ctr, d, note) in enumerate(p.holes):
        a, b = ctr[ax[0]] - p.lo[ax[0]], ctr[ax[1]] - p.lo[ax[1]]
        x, y = ox + a * sc, oy + h - b * sc
        L = chr(65 + k)
        if kind == "hole":
            s.append(sv.circ(x, y, max(d / 2 * sc, 0.5), "#fff", sv.INK, 0.25))
        else:
            ln, wd = d
            s.append(sv.rect(x - ln / 2 * sc, y - wd / 2 * sc, ln * sc, wd * sc, "#fff", sv.INK, 0.25, wd / 2 * sc))
        s.append(sv.t(x + max(d / 2 * sc if kind == 'hole' else 0, 0.8) + 0.6, y - 0.8, L, 2.6, "start", 800, sv.ACC, "Barlow"))
        size = f"Ø{d:.1f}" if kind == "hole" else f"slot {d[0]:.1f} × {d[1]:.1f}"
        letters.append((L, size, f"{a:.1f}", f"{b:.1f}", esc(note)))
    na, nb = "uvz"[ax[0]], "uvz"[ax[1]]
    s.append(sv.arrowline(ox, oy + h + 4, ox + 12, oy + h + 4, sv.INK2, 0.25, 1.2) + sv.t(ox + 13, oy + h + 5, f"a ({na})", 2.4, "start", 600, sv.INK2))
    s.append(sv.arrowline(ox - 4, oy + h, ox - 4, oy + h - 10, sv.INK2, 0.25, 1.2) + sv.t(ox - 4.8, oy + h - 11, f"b ({nb})", 2.4, "end", 600, sv.INK2))
    s.append(sv.t(ox + w / 2, oy + h + 9.5, f"{A:.0f} mm", 2.6, "middle", 600) + sv.t(ox + w + 1.2, oy + h / 2, f"{B:.0f}", 2.6, "start", 600))
    s.append("</svg>")
    return "".join(s), letters, na, nb


SEEN = {"u": "seen from the +u side", "v": "seen from the −v side", "z": "seen from above"}
EDGE = {"u": "the −u edge", "v": "the −v edge (operator’s right)", "z": "the bottom edge"}


def app_cutlist():
    drilled = [p for p in PANELS if p.holes and p.name != "axle bearing block right"]
    cards = []
    for p in drilled:
        svg, letters, na, nb = panel_svg(p)
        rows = "".join(f"<tr><td><b style='color:var(--accent)'>{L}</b></td><td>{sz}</td><td class=n>{a}</td><td class=n>{b}</td><td>{nt}</td></tr>"
                       for L, sz, a, b, nt in letters)
        cards.append(f'''<div style="break-inside:avoid;border:0.6pt solid var(--rule);border-radius:3px;padding:4px 6px;margin-bottom:6px">
<div style="font-weight:700">{pid(WID[p.name])}{(" + " + pid("W08")) if "block left" in p.name else ""} {esc(p.name.replace("axle bearing block left", "axle bearing blocks (×2, identical)"))} <span class="small">— {SEEN[p.normal]}; a from {EDGE[na]}, b from {EDGE[nb]}</span></div>
{svg}<table class="t compact" style="margin:2px 0 0"><tr><th></th><th>Size</th><th class=n>a</th><th class=n>b</th><th>Purpose</th></tr>{rows}</table></div>''')
    half = 4
    body1 = f'''<div class="kicker">Appendix B</div><h1>Drilling drawings</h1>
<p class="lead">Every drilled panel, drawn to scale from <span class="mono">build-box.py</span> {tag("v")}. Positions in mm from the panel’s lower-left
corner as drawn: <b>a</b> along the horizontal edge, <b>b</b> up the vertical edge. The box floor’s Ø8.5 hole also gets a Ø22 × 7 counterbore
from below.</p><div class="twocol">{"".join(cards[:half])}</div>'''
    page(body1, tab="Appendix B", right="Drilling drawings (1/2)", toc=[(2, "B — Drilling drawings")])
    page(f'<div class="kicker">Appendix B</div><h2>Drilling drawings (continued)</h2><div class="twocol">{"".join(cards[half:])}</div>',
         tab="Appendix B", right="Drilling drawings (2/2)")


def app_cuts():
    body = f'''<div class="kicker">Appendix C</div><h1>Rope, tube and plate reference</h1>
<div class="row"><div class="col">
<h3 class="mt0">Cut lengths {tag("v")}</h3>
{table(["Piece", "Cut (mm)", "Modelled path (mm)"], [("Boom rope", "1384", "1264 + 2 × 60 loops"), ("Stick rope", "1821", "1701 + 2 × 60"),
                                                   ("Bucket rope", "2173", "2053 + 2 × 60"), ("Slew rope A", "829", "769 + 60"), ("Slew rope B", "900", "840 + 60"),
                                                   ("PTFE stick_hi", "647", "637 + 10 trim"), ("PTFE stick_lo", "658", "648 + 10"),
                                                   ("PTFE bucket_hi", "813", "803 + 10"), ("PTFE bucket_lo", "822", "812 + 10"),
                                                   ("Slew sleeve A", "339", "329 + 10"), ("Slew sleeve B", "407", "397 + 10")], num=(1,))}
<p class="small">Modelled lengths from <span class="mono">Validation/2026-09-24-box-report.md</span>; cut lengths from the bill of materials.</p>
<h3>Rope travel per circuit {tag("v")}</h3>
{table(["Circuit", "Range", "Rope travel per side", "Control"], [("Boom", "85°", "22.3 mm", "lever 42°"), ("Stick", "95°", "21.6 mm", "lever 41°"),
                                                               ("Bucket", "140°", "20.8 mm", "lever 40°"), ("Slew", "180°", "172.8 mm", "wheel 180°")])}
</div><div class="col">
<h3 class="mt0">Lever ropes in the box {tag("v")}</h3>
{table(["Strand", "Length", "Fleet", "Wrap over swing"], [("boom upper", "118", "11.3°", "62–105°"), ("boom lower", "118", "11.2°", "52–95°"),
                                                       ("stick upper", "116", "4.5°", "63–104°"), ("stick lower", "116", "4.4°", "53–94°"),
                                                       ("bucket upper", "117", "9.8°", "63–103°"), ("bucket lower", "118", "9.8°", "54–94°")], num=(1,))}
<h3>Slew wrap {tag("v")}</h3>
{table(["Slew", "Rope A spool / pedestal", "Rope B spool / pedestal"], [("−90°", "90° / 270°", "270° / 90°"), ("0°", "180° / 180°", "180° / 180°"),
                                                                     ("+90°", "270° / 90°", "90° / 270°")])}
<h3>Slicer projects</h3>
<p class="small mono">3MF/2026-09-27-bambu-arm-shell-petg.3mf · 3MF/2026-09-27-orca-arm-shell-petg.3mf<br>
3MF/2026-09-27-bambu-other-parts-plaplus.3mf · 3MF/2026-09-27-orca-other-parts-plaplus.3mf</p>
</div></div>'''
    page(body, tab="Appendix C", right="Rope, tube and plates", toc=[(2, "C — Rope, tube and plate reference")])


def app_open():
    items = [
        ("1", "Stick-drum key screws collide",
         "The stick drum is 10 mm thick and each key pilot runs right through it. The hardware model puts one M3 × 12 into each pilot from each side "
         "with its head in a 3.5 mm wall pocket, which places the two tips at v −0.8 and +0.8 mm: they overlap by 1.6 mm (10.5 mm³ in the "
         "interference check). The boom drum (14 mm) does not have this problem: its screws stop 5 mm short of the centre.",
         "Use M3 × 8 socket caps on the stick drum (in your kit; 1.8 mm in the drum), or grind 2 mm off each M3 × 12. Both keep the heads in "
         "their pockets."),
        ("2", "Stick root lugs overlap",
         "Joining lugs 1 and 2 of the stick are 2.9 mm apart, so their Ø3.4 holes merge into one figure-of-eight hole and their screws and nuts "
         "overlap (interference check).",
         "Fit one M3 × 20 in that lug; the stick then has 3 lug screws (1 spare)."),
        ("3", "Joining-lug screws are enclosed",
         "On both members every lug screw head sits inside the closed shell, and the outer walls have no access hole on the screw axis (ray test on "
         "the CAD). As modelled, the lug screws cannot be fitted or tightened once a boom or stick is closed.",
         "Decide before Stage 8. Options: (a) drill a small access hole through the outer wall on each lug axis and fit the nut captive with a drop "
         "of CA — changes the exterior; (b) close the halves without lug screws and hold them with tape or a few dots of CA along the seam — "
         "loses easy opening for service; (c) add access in the CAD and reprint the halves."),
        ("4", "5/16in axle ends",
         "The bill of materials puts 5/16in nuts on both ends of the lever axle and the spool axle. One design note calls the rod “smooth”; the "
         "validation report checks the axle both plain and threaded.",
         "If your rod is threaded rod, nothing changes. If it is smooth, thread the ends with a 5/16-18 die or use 5/16in shaft collars."),
        ("5", "Pedestal not fixed to the floor",
         "The cut list says “the pedestal and the elbow support screw to” the sandbox floor, but no screws for the pedestal are counted in the bill "
         "of materials or placed in the hardware model.",
         "4 extra #6 × 1-1/4in up through the sandbox floor into the ±v walls (Stage 4)."),
        ("6", "Slicer plates hold the old base and ears",
         "Plates 4 and 6 of the PLA+ project were made before the 2026-09-29 rebuilds.",
         "Replace them with STL/2026-09-29-base.stl and STL/2026-09-29-bucket-ear-{left,right}-cad.stl (Stage 1)."),
        ("7", "Tension direction",
         "The checklist says to slide the rope anchors “outward”. In the CAD the rope enters each anchor slot at its outer end, so the strand "
         "tightens as the screw moves inward.",
         "Slide toward the drum centre (Stages 9 and 10)."),
    ]
    rows = [(n, f"<b>{t_}</b><br>{w}", fix) for n, t_, w, fix in items]
    body = f'''<div class="kicker">Appendix D</div><h1>Open items and verification</h1>
<p class="lead">Found while preparing this manual by checking the project’s own CAD and hardware model. None of them is fixed in the project files;
each needs your decision. {tag("o")}</p>
{table(["#", "What the files show", "Options"], rows)}
<h3>What was verified, and how</h3>
<table class="t compact">
<tr><td>Illustrations</td><td>Rendered from the project STL files, the plywood panels and the hardware solids at their modelled positions.
Base and ears use the 2026-09-29 files.</td></tr>
<tr><td>Hardware interference</td><td>Every pair of fasteners checked for overlap (manifold boolean). Found items 1 and 2; the only other overlap is the
copper elbow inside the PEX tube, which the model draws as a solid rod (not a real clash).</td></tr>
<tr><td>Numbers</td><td>Dimensions, ranges and lengths are taken from <span class="mono">exma_common.py</span>, <span class="mono">build-box.py</span>,
<span class="mono">build-parts.py</span>, the bill of materials, the checklist and the validation reports.</td></tr>
<tr><td>Not verified</td><td>Physical fit of real prints, glue strength, rope friction, how hard a person can push. Tips and items tagged
{tag("a")} are general practice.</td></tr></table>'''
    page(body, tab="Appendix D", right="Open items and verification", toc=[(2, "D — Open items and verification")])


def app_compact():
    body = f'''<div class="kicker">Appendix E</div><h1>Option: compact control box</h1>
<p class="lead">On 2026-09-28 a smaller box was specified (<span class="mono">2026-09-28-compact-control-box-spec.md</span>) without changing the arm,
the slew or the reach. It is a specification only — <b>no CAD model was made</b>, so this manual’s figures show the full-size box. {tag("v")}</p>
{table(["", "Modelled box (this manual)", "Compact box (spec)"], [("Outside u × v × z", "250 × 405 × 242", "214 × 362 × 156"),
                                                                 ("Lever handle length / rod", "225 / 230 mm", "140 / 145 mm"),
                                                                 ("Handle spacing", "70 mm", "60 mm"), ("Lever axle rod", "205 mm", "185 mm"),
                                                                 ("Spool axle rod", "274 mm", "188 mm"), ("Slew spool tube", "145 mm", "59 mm (reprint)"),
                                                                 ("Lever hubs", "as printed", "boom + bucket reprinted (sleeve −10 mm)"),
                                                                 ("Lid slots (boom / stick / bucket)", "133 / 129 / 124", "66.1 / 64.1 / 61.8"),
                                                                 ("Slew sleeves A / B", "339 / 407", "330 / 397 (cut)"),
                                                                 ("Knob stroke (boom)", "177 mm", "114 mm"), ("Boom holding force at the knob", "2.7 N", "4.2 N")])}
<div class="row"><div class="col">{box("caut", "If you choose the compact box", " cut its panels from the spec (floor and lid 214 × 362, front and "
     "rear 362 × 132, sides 190 × 132), reprint the slew spool and the boom and bucket hubs, and drill two new box-to-sandbox holes. The "
     "Stage 6 and Stage 11 steps are the same; only the dimensions change.")}</div>
<div class="col">{box("note", "Unchanged", " Arm, turret, pedestal, conduit, fittings, drums, all arm ropes and the four arm PTFE tubes. "
     "The lever axle height and position stay the same, so the rope angles do not change. " + tag("v"))}</div></div>'''
    page(body, tab="Appendix E", right="Compact control box option", toc=[(2, "E — Compact control box option")])


def app_files():
    body = f'''<div class="kicker">Appendix F</div><h1>Files and revision</h1>
<div class="row"><div class="col">
<h3 class="mt0">Project files used</h3>
<table class="t compact">
<tr><td class="mono">STL/</td><td>printed parts (P01–P26), print-ready</td></tr>
<tr><td class="mono">STEP/</td><td>solid models of the new parts, the wood, and the 2026-09-29 base, ring and ears</td></tr>
<tr><td class="mono">3MF/</td><td>slicer projects (Bambu Studio, OrcaSlicer)</td></tr>
<tr><td class="mono">Source/</td><td>build scripts; all parameters in <span class="mono">2026-09-24-exma_common.py</span></td></tr>
<tr><td class="mono">Validation/</td><td>box, kinematics and wall-thickness reports</td></tr>
<tr><td class="mono">2026-09-24-bill-of-materials.md</td><td>quantities, plates, materials</td></tr>
<tr><td class="mono">2026-09-24-cut-list.md</td><td>plywood sizes and holes</td></tr>
<tr><td class="mono">2026-09-25-print-and-assembly-checklist.md</td><td>the checklist this manual expands</td></tr>
<tr><td class="mono">2026-09-28-compact-control-box-spec.md</td><td>Appendix E</td></tr>
<tr><td class="mono">References/IMG_2449, IMG_2454</td><td>photos of the M3 kit and the Hillman parts</td></tr></table>
</div><div class="col">
<h3 class="mt0">This manual’s source</h3>
<table class="t compact">
<tr><td class="mono">source/2026-10-10-manual-scene-export.py</td><td>geometry → scene for the renderer</td></tr>
<tr><td class="mono">source/2026-10-10-manual-figure-specs.py</td><td>cameras, callouts, exploded offsets</td></tr>
<tr><td class="mono">source/2026-10-10-manual-render.html</td><td>three.js illustration renderer</td></tr>
<tr><td class="mono">source/2026-10-10-manual-figures.mjs</td><td>renders all figures</td></tr>
<tr><td class="mono">source/2026-10-10-manual-svg.py</td><td>overlays and vector diagrams</td></tr>
<tr><td class="mono">source/2026-10-10-build-manual.py</td><td>text and page layout</td></tr>
<tr><td class="mono">source/2026-10-10-manual.css</td><td>page styles</td></tr>
<tr><td class="mono">source/2026-10-10-manual-print.mjs</td><td>HTML → PDF</td></tr>
<tr><td class="mono">source/2026-10-10-build-manual.sh</td><td>runs the whole chain</td></tr>
<tr><td class="mono">figures/</td><td>rendered figures + callout data</td></tr></table>
<h3>Revision</h3>
{table(["Date", "Change"], [("2026-10-10", "First edition. Covers the modelled design with the 2026-09-29 base and ears.")])}
</div></div>'''
    page(body, tab="Appendix F", right="Files and revision", toc=[(2, "F — Files and revision")])


# ================================================================ assemble
def build():
    cover()
    contents_placeholder()
    about()
    safety()
    overview()
    how_it_works()
    controls()
    at_a_glance()
    tools()
    hardware_pages()
    parts_pages()
    wood_page()
    stage_print()
    stage_cut()
    stage_sandbox()
    stage_pedestal()
    stage_turret()
    stage_box()
    stage_conduit()
    stage_arm()
    stage_rig()
    stage_slew()
    stage_top()
    stage_test()
    operation()
    troubleshooting()
    app_bom()
    app_cutlist()
    app_cuts()
    app_open()
    app_compact()
    app_files()

    # TOC and stage page refs
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
    n = len(PAGES)
    for i, p in enumerate(PAGES, start=1):
        body = p["body"].replace("@@TOC@@", toc_html)
        for k, v in stage_pg.items():
            body = body.replace(f"@@P:stage{k}@@", f"p. {v}")
        head = foot = ""
        if "cover" not in p["cls"]:
            tabcls = "tab st" if p["stage"] else "tab"
            head = f'<div class="rhead"><span class="{tabcls}">{esc(p["tab"])}</span><span>{esc(p["right"])}</span></div>'
            foot = (f'<div class="rfoot"><span>EX-MA cable excavator · Assembly &amp; configuration manual · 2026-10-10</span>'
                    f'<span class="pn">{i}</span></div>')
        out.append(f'<section class="page {p["cls"]}">{head}{body}{foot}</section>')
    html_ = f'''<!doctype html><html><head><meta charset="utf-8"><title>EX-MA Assembly Manual</title>
<link rel="stylesheet" href="2026-10-10-manual.css"></head><body>{"".join(out)}</body></html>'''
    (HERE / "2026-10-10-manual.html").write_text(html_)
    print(f"{n} pages, {FIG_N[0]} figures -> {HERE / '2026-10-10-manual.html'}")


if __name__ == "__main__":
    build()
