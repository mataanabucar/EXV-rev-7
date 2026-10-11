#!/usr/bin/env python3
"""Figure specifications for the MINIMAL-design manual (3D renders). Derived from
../../2026-10-10-assembly-manual/source/2026-10-10-manual-figure-specs.py; the control-box cameras are
shifted with the box (DU = AXLE_U + 360), the conduit figures are replaced by the spacer stack, and the
conduit-fitting bolts by the 8-32 through-rods. Constants come from the minimal Source tree
(env MINIMAL_SRC, made by 2026-10-11-make-minimal-source.py).

Original notes:

Every camera, selection, exploded offset and callout anchor below is written in the project's
design frame (mm): u toward the sandbox, v to the operator's left, z up; slew axis at u = v = 0.
Positions come from Source/2026-09-24-exma_common.py (imported) so the figures follow the model.

Usage: <cadenv>/bin/python 2026-10-10-manual-figure-specs.py <figures.json>
Then:  node 2026-10-10-manual-figures.mjs <figures.json> <scene_dir> <out_dir>
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import os
HERE = Path(__file__).resolve().parent
SRC = Path(os.environ["MINIMAL_SRC"])


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, SRC / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


ex = _load("exma", "2026-09-24-exma_common.py")

PB, PS, PK = ex.P_BOOM, ex.P_STICK, ex.P_BUCKET
DU = ex.AXLE_U + 360.0                 # control box shift vs the original design
LID = ex.BOX_Z[1]
T = ex.T_WOOD
FIT_BOX_U = ex.BOX_U[1] - T            # box fitting face on the box front (inside)


def bx_(lo, hi):
    """Camera box in original box coordinates, shifted with the control box."""
    return [[lo[0] + DU, lo[1], lo[2]], [hi[0] + DU, hi[1], hi[2]]]
AU, AZ = ex.AXLE_U, ex.AXLE_Z
KNOB_Z = AZ + ex.HANDLE_LEN + 16.0
WC = ex.WHEEL_C
MID = {j: (lo + hi) / 2 for j, (lo, hi) in ex.WORKING.items()}      # rigging pose (mid-range)

ISO = [-0.9, 0.85, 0.62]            # from behind the operator's left shoulder
ISO_R = [-0.9, -0.85, 0.62]         # from behind the operator's right shoulder
SIDE = [0.0, -1.0, 0.0]             # from the operator's right: +u to the right
SIDE_L = [0.0, 1.0, 0.0]

F = []


def fig(id, show, cam, w=2000, h=1300, **kw):
    d = dict(id=id, w=w, h=h, show=show, cam=cam)
    d.update(kw)
    F.append(d)
    return d


def S(sel, style="focus", **kw):
    d = dict(sel=sel, style=style)
    d.update(kw)
    return d


def lab(text, sel=None, at=None, side=None, n=None, off=None, offset=None):
    a = dict(sel=sel) if sel else dict(at=list(at))
    if offset:
        a["offset"] = offset
    return dict(text=text, anchor=a, side=side, n=n, off=off)


def arrow(frm, to, kind="move", **kw):
    d = dict(kind=kind, **{"from": list(frm), "to": list(to)})
    d.update(kw)
    return d


def rot(center, axis, r, a0, a1, ref=(1, 0, 0), **kw):
    d = dict(kind="rotate", center=list(center), axis=list(axis), r=r, a0=a0, a1=a1, ref=list(ref))
    d.update(kw)
    return d


ALL_ARM = ["member:boom", "member:stick", "member:bucket"]
SANDBOX = "group:sandbox_wood"
PED = "group:pedestal_wood"
BOXW = "group:box_wood"
BOX_PARTS = ["group:box", "group:box_hw"]

# =============================================================== front matter
fig("cover", [S("all"), S("group:sandbox_hw", "hide"), S("name:sandbox wall +v", "ghost", opacity=0.12),
              S("re:wood screw", "hide")],
    dict(dir=[-0.8, 1.0, 0.55], margin=0.04), w=2200, h=1700,
    pose=dict(boom=14, stick=-6, bucket=28, slew=22), line=1.8)

fig("overview", [S("all"), S("group:sandbox_hw", "hide"), S("name:sandbox wall +v", "ghost", opacity=0.10),
                 S("re:wood screw", "hide")],
    dict(dir=ISO, margin=0.06), w=2200, h=1500,
    labels=[lab("Boom lever", "name:lever-knob@boom", n=1, side="L"),
            lab("Stick lever", "name:lever-knob@stick", n=2, side="L"),
            lab("Bucket lever", "name:lever-knob@bucket", n=3, side="L"),
            lab("Slew wheel", "name:slew-wheel", n=4, side="R"),
            lab("Control box", "name:box left side", n=5, side="L"),
            lab("Removable box top", "name:box top (removable)", n=6, side="L", offset=[60, 120, 0]),
            lab("Pedestal (inside the sandbox)", "name:pedestal wall +v", n=7, side="L"),
            lab("Base + printed slewing ring", "name:slewing-ring-retaining-ring", n=8, side="R"),
            lab("Tower (turret)", "name:tower", n=9, side="R"),
            lab("Boom", "name:boom-half-left", n=10, side="T"),
            lab("Stick", "name:stick-half-left", n=11, side="T"),
            lab("Bucket", "name:bucket", n=12, side="R"),
            lab("Sandbox", "name:sandbox floor", n=13, side="R", offset=[250, 0, 0])])

CUT_V = dict(n=[0, -1, 0], d=0.0)       # keep v <= 0
fig("system-cutaway",
    [S("all"), S(["name:sandbox wall +v", "name:box top (removable)", "name:box left side", "name:pedestal wall +v",
                  "name:boom-half-left", "name:stick-half-left", "name:bucket-ear-left", "group:sandbox_hw",
                  "re:wood screw", "re:lever-knob", "re:handle", "name:slew-wheel"], "hide"),
     S(["name:tower", "name:base", "name:slewing-ring-retaining-ring", "name:sandbox floor", "name:sandbox wall -u (box side)",
        "name:sandbox wall +u", "group:pedestal_wood", "name:1/2in copper elbow",
        "name:3/4in PEX turret tube", "name:box floor", "name:box rear", "name:box front", "name:box right side",
        "re:conduit-end-fitting", "name:slew-drum", "re:BBs", "name:slew-tube-bushing"], "focus")],
    dict(dir=[-0.05, 1.0, 0.18], margin=0.04), w=2400, h=1250,
    clip=[CUT_V], clipSel=["name:tower", "name:base", "name:slewing-ring-retaining-ring", "group:pedestal_wood",
                           "name:1/2in copper elbow", "name:3/4in PEX turret tube",
                           "re:conduit-end-fitting", "name:slew-drum", "group:sandbox_wood", "group:box_wood",
                           "name:slew-tube-bushing", "re:BBs"],
    ropes=dict(scale=2.6, ptfe=True, ptfeScale=1.6, ptfeOpacity=0.45), line=1.5,
    fitSel=["group:box", "member:boom", "member:stick", "member:bucket", "group:pedestal", "name:tower"],
    labels=[lab("Lever drums (one per lever)", "name:lever-hub-stick", side="L"),
            lab("Slew spool (two lanes)", "name:slew-spool", side="L"),
            lab("Box conduit fitting", "name:conduit-end-fitting-box", side="B"),
            lab("Spacer frames (no conduit)", "name:spacer frame 1", side="B"),
            lab("Pedestal conduit fitting", "name:conduit-end-fitting-pedestal", side="B"),
            lab("1/2in copper elbow", "name:1/2in copper elbow", side="B"),
            lab("Pedestal slew drum", "name:slew-drum", side="B"),
            lab("3/4in PEX turret tube", "name:3/4in PEX turret tube", side="R"),
            lab("Boom drum", "name:boom-drum", side="T"),
            lab("Stick drum", "name:stick-drum", side="T"),
            lab("Bucket drum-axle", "name:bucket-drum-axle", side="R")])

fig("controls", [S(BOXW), S(BOX_PARTS), S("re:wood screw", "hide"), S(["name:box rear"], "focus")],
    dict(dir=[-1.0, 0.12, 0.95], margin=0.12), w=2000, h=1250,
    fitSel=["name:box top (removable)", "re:lever-knob", "name:slew-wheel"],
    arrows=[arrow((AU - 55, 70, KNOB_Z + 30), (AU + 55, 70, KNOB_Z + 30), kind="double"),
            arrow((AU - 55, 0, KNOB_Z + 30), (AU + 55, 0, KNOB_Z + 30), kind="double"),
            arrow((AU - 55, -70, KNOB_Z + 30), (AU + 55, -70, KNOB_Z + 30), kind="double"),
            rot((WC[0], WC[1], 75), (0, 0, 1), 112, -40, 30, kind="rotate")],
    points=dict(fwd=(AU + 120, 0, KNOB_Z + 30), back=(AU - 120, 0, KNOB_Z + 30)),
    labels=[lab("Boom lever", "name:lever-knob@boom", side="L"), lab("Stick lever", "name:lever-knob@stick", side="L"),
            lab("Bucket lever", "name:lever-knob@bucket", side="R"), lab("Slew wheel", "name:slew-wheel", side="R"),
            lab("Lever slots = end stops", at=(AU - 30, 35, LID), side="L")])

# =============================================================== part renders (identification pages)
PRINTED = ["boom-half-left", "boom-half-right", "stick-half-left", "stick-half-right", "boom-drum", "stick-drum",
           "bucket-drum-axle", "bucket", "bucket-ear-left", "bucket-ear-right", "tower", "base",
           "slewing-ring-retaining-ring", "slew-drum", "slew-tube-bushing", "elbow-support",
           "conduit-end-fitting-pedestal", "conduit-end-fitting-box", "lever-hub-boom", "lever-hub-stick",
           "lever-hub-bucket", "lever-knob@boom", "slew-spool", "slew-wheel", "spool-riser", "slew-tube-post@A"]
PART_DIR = {"boom-half-left": [0.25, 1.0, 0.25], "boom-half-right": [0.25, 1.0, 0.25],
            "stick-half-left": [0.25, 1.0, 0.25], "stick-half-right": [0.25, 1.0, 0.25],
            "conduit-end-fitting-box": [0.9, -0.5, 0.45], "conduit-end-fitting-pedestal": [-0.9, 0.5, 0.45],
            "bucket": [0.8, 0.9, 0.6], "lever-hub-bucket": [-0.8, -0.8, 0.6], "lever-hub-boom": [-0.8, 0.8, 0.6],
            "lever-hub-stick": [-0.8, 0.8, 0.6], "bucket-ear-right": [-0.6, -1.0, 0.4]}
for n in PRINTED:
    fig("part-" + n.replace("@", "-"), [S("name:" + n)], dict(dir=PART_DIR.get(n, [-0.8, 0.7, 0.6]), margin=0.06),
        w=900, h=700, line=2.0)

# =============================================================== stage: sandbox
SB_MOVE = [dict(sel="name:sandbox wall -u (box side)", d=[-160, 0, 110]), dict(sel="name:sandbox wall +u", d=[160, 0, 110]),
           dict(sel="name:sandbox wall -v", d=[0, -160, 110]), dict(sel="name:sandbox wall +v", d=[0, 160, 110])]
fig("sandbox-exploded", [S(SANDBOX)], dict(dir=[-0.85, 0.75, 0.75], margin=0.05), w=2000, h=1250, move=SB_MOVE,
    arrows=[dict(kind="move", sel=m["sel"], d=m["d"], endFrac=0.55) for m in SB_MOVE],
    labels=[lab("Sandbox floor: 24″ × 24″ particle board", "name:sandbox floor", n=1, side="B"),
            lab("Wall −u (box side, drilled)", "name:sandbox wall -u (box side)", n=2, side="L"),
            lab("Wall +u", "name:sandbox wall +u", n=3, side="R"),
            lab("Wall −v", "name:sandbox wall -v", n=4, side="R"),
            lab("Wall +v", "name:sandbox wall +v", n=5, side="L")])
fig("sandbox-corner", [S(SANDBOX, "ghost", opacity=0.18), S("re:wood screw .* - sandbox", "focus")],
    dict(dir=[-0.7, 0.55, 0.55], box=[[ex.SB_U[0] - 2, 215, -205], [ex.SB_U[0] + 83, 307, 45]], margin=0.1), w=1100, h=1100,
    labels=[lab("#6 × 1-1/4in up through the floor", "name:#6 x 1-1/4in wood screw 092 - sandbox floor to sandbox wall -u (box side)", side="R"),
            lab("#6 × 1-1/4in through wall −u into wall +v", "re:sandbox wall -u \\(box side\\) to sandbox wall \\+v", side="R")])

# =============================================================== stage: pedestal
PED_CTX = [S(SANDBOX, "context"), S(["name:sandbox wall +v", "name:sandbox wall +u", "name:sandbox wall -v"], "hide"),
           S("group:sandbox_hw", "hide")]
PW_MOVE = [dict(sel="name:pedestal wall -u (conduit)", d=[-70, 0, 0]),
           dict(sel="name:pedestal wall -v", d=[0, -90, 0]), dict(sel="name:pedestal wall +v", d=[0, 90, 0]),
           dict(sel="name:pedestal top", d=[0, 0, 140]), dict(sel="name:pedestal wall +u (removable access)", d=[110, 0, 0])]
fig("pedestal-exploded", PED_CTX + [S([PED]), S("re:pedestal shelf", "hide")],
    dict(dir=[-0.8, 0.95, 0.7], box=[[-220, -200, -200], [220, 200, 160]], margin=0.04), w=2000, h=1400, move=PW_MOVE,
    arrows=[dict(kind="move", sel=m["sel"], d=m["d"], endFrac=0.6) for m in PW_MOVE],
    points=dict(wall_in=(-191, 120, -190), ped_out=(-110, 120, -190)),
    labels=[lab("Wall −u (conduit wall)", "name:pedestal wall -u (conduit)", n=1, side="L"),
            lab("Wall −v", "name:pedestal wall -v", n=2, side="R"),
            lab("Wall +v", "name:pedestal wall +v", n=3, side="L"),
            lab("Pedestal top", "name:pedestal top", n=4, side="T"),
            lab("Wall +u (removable — screw only)", "name:pedestal wall +u (removable access)", n=5, side="R")])
fig("pedestal-fitting", [S(PED, "context"), S(["name:pedestal wall +v", "name:pedestal top", "name:pedestal wall +u (removable access)",
                                               "re:pedestal shelf"], "hide"),
                         S(["name:spacer frame 1", "name:spacer frame 2"], "context"),
                         S("name:conduit-end-fitting-pedestal"), S("re:through-rod")],
    dict(dir=[0.85, 0.75, 0.45], box=[[-175, -70, -175], [-60, 55, -45]], margin=0.12), w=1600, h=1300,
    move=[dict(sel=["name:conduit-end-fitting-pedestal", "re:through-rod .* pedestal side"], d=[45, 0, 0])],
    arrows=[dict(kind="move", sel="name:conduit-end-fitting-pedestal", d=[45, 0, 0], endFrac=0.5, at=(-40, -65, -110))],
    labels=[lab("Pedestal conduit fitting (P17)", "name:conduit-end-fitting-pedestal", side="R"),
            lab("4 × 8-32 rod 3-1/16″, nut on the fitting", "re:8-32 through-rod .* 4", side="T"),
            lab("Spacer frames W22 + W23 (glued on)", "name:spacer frame 2", side="L"),
            lab("Wall −u", "name:pedestal wall -u (conduit)", side="L"),
            lab("Copper socket (elbow)", at=(-72, 0, -130), side="B")])
fig("pedestal-elbow", [S(SANDBOX, "context"), S(["name:sandbox wall +v", "name:sandbox wall +u", "name:sandbox wall -v",
                                                  "name:sandbox wall -u (box side)"], "hide"),
                       S(PED, "context"), S(["name:pedestal wall +v", "name:pedestal top", "name:pedestal wall +u (removable access)"], "hide"),
                       S("re:pedestal shelf", "ghost", opacity=0.15),
                       S(["name:conduit-end-fitting-pedestal", "re:through-rod"], "context"),
                       S(["name:1/2in copper elbow", "name:elbow-support", "re:elbow support"]),
                       S(["name:slew-tube-bushing", "re:PEX bushing"], "ghost", opacity=0.2)],
    dict(dir=[0.35, 1.0, 0.35], box=[[-115, -60, -200], [40, 60, -40]], margin=0.08), w=1700, h=1300,
    labels=[lab("1/2in copper elbow (pushed into the fitting socket)", "name:1/2in copper elbow", side="T"),
            lab("Elbow support (P16)", "name:elbow-support", side="R"),
            lab("Base plate sawn off; 1 × #6 × 1-1/4″ up through the floor", "re:elbow support \\(from below\\)", side="R"),
            lab("Cable-tie slot", at=(-50, 0, -138), side="L"),
            lab("Pedestal fitting", "name:conduit-end-fitting-pedestal", side="L")])
fig("pedestal-shelf", [S(PED, "context"), S(["name:pedestal wall +v", "name:pedestal top", "name:pedestal wall +u (removable access)"], "hide"),
                       S(["name:pedestal shelf", "re:pedestal shelf cleat", "name:slew-tube-bushing", "re:PEX bushing",
                          "re:wall -v to pedestal shelf cleat", "re:wall \\+v to pedestal shelf cleat"]),
                       S(["name:1/2in copper elbow", "name:elbow-support", "name:conduit-end-fitting-pedestal"], "context")],
    dict(dir=[0.6, 1.0, 0.75], box=[[-110, -95, -200], [95, 95, 0]], margin=0.05), w=1700, h=1400,
    move=[dict(sel=["name:pedestal shelf", "name:slew-tube-bushing", "re:PEX bushing"], d=[0, 0, 70]),
          dict(sel=["name:slew-tube-bushing", "re:PEX bushing"], d=[0, 0, 45])],
    arrows=[dict(kind="move", sel="name:pedestal shelf", d=[0, 0, 70], endFrac=0.7, at=(40, 0, -10)),
            dict(kind="move", sel="name:slew-tube-bushing", d=[0, 0, 45], endFrac=0.8, at=(0, 0, 70))],
    labels=[lab("Shelf (rests on the cleats)", "name:pedestal shelf", n=1, side="L"),
            lab("Shelf cleats (screwed to walls ±v)", "name:pedestal shelf cleat +v", n=2, side="R"),
            lab("PEX bushing (P15), flange up", "name:slew-tube-bushing", n=3, side="L"),
            lab("3 × #6 × 3/4in", "re:#6 x 3/4in wood screw 12 - PEX bushing", n=4, side="R")])

# =============================================================== stage: slewing ring + turret
TOP_CTX = [S(PED, "context"), S(["name:pedestal wall +v", "name:pedestal wall +u (removable access)"], "hide"),
           S("re:pedestal shelf", "hide"), S("group:pedestal_hw", "hide")]
fig("base-to-pedestal", TOP_CTX + [S("name:base"), S("re:base to pedestal top")],
    dict(dir=[-0.7, 0.8, 0.9], box=[[-110, -95, -60], [95, 95, 150]], margin=0.05), w=1700, h=1300,
    move=[dict(sel=["name:base"], d=[0, 0, 60]), dict(sel="re:base to pedestal top", d=[0, 0, 120])],
    arrows=[dict(kind="move", sel="re:#8 x 1in wood screw 1 - base", d=[0, 0, 120], endFrac=0.35, at=(26.9, 26.9, 135))],
    labels=[lab("Base (P12) — current file 2026-09-29-base", "name:base", n=1, side="L"),
            lab("4 × #8 × 1″ wood screw in the counterbores", "re:#8 x 1in wood screw 2 - base", n=2, side="R"),
            lab("Pedestal top (1/8″ pilots)", "name:pedestal top", n=3, side="R"),
            lab("Nut slots in the rim (8)", at=(66.8 * math.cos(math.radians(202.5)) - 5, 66.8 * math.sin(math.radians(202.5)), 77.5), side="L")])
fig("turret-tube", [S("name:tower"), S("name:3/4in PEX turret tube"), S("re:turret hub PEX clamp")],
    dict(dir=[0.9, 0.9, 0.35], margin=0.08), w=1300, h=1500,
    move=[dict(sel="name:3/4in PEX turret tube", d=[0, 0, -60])],
    arrows=[arrow((30, 0, -150), (30, 0, -95))],
    labels=[lab("Tower (P11)", "name:tower", side="R"),
            lab("Turret hub clamp: M3 × 25 + lock washer + nut", "re:M3x25 socket head cap screw - turret hub", side="L"),
            lab("3/4″ PEX-B tube, 4-3/4″", "name:3/4in PEX turret tube", side="L")])
fig("slewing-ring-exploded",
    [S("name:base"), S("re:BBs"), S("name:tower"), S("name:slewing-ring-retaining-ring"), S("re:retaining ring")],
    dict(dir=[-0.75, 0.8, 0.75], margin=0.05), w=2000, h=1500,
    clip=[dict(n=[0, -1, 0], d=0.0)], clipSel=["name:base", "name:tower"],
    move=[dict(sel="name:tower", d=[0, 0, 130]), dict(sel="name:slewing-ring-retaining-ring", d=[0, 0, 70]),
          dict(sel=["re:M3x12 socket head cap screw - retaining ring", "re:split-lock washer \\(head side\\) - retaining ring"], d=[0, 0, 110]),
          dict(sel="re:BBs", d=[0, 0, 30])],
    arrows=[arrow((0, 0, 225), (0, 0, 150)), arrow((-66, -10, 120), (-66, -10, 70))],
    labels=[lab("Turret (tower + PEX tube) lowered last", "name:tower", n=1, side="R"),
            lab("8 × M3 × 12 + split-lock washer", "re:M3x12 socket head cap screw - retaining ring 4", n=2, side="L"),
            lab("Retaining ring (P13)", "name:slewing-ring-retaining-ring", n=3, side="L"),
            lab("57 × 6 mm BBs in the race", "re:BBs", n=4, side="L"),
            lab("8 × M3 nut, slid into the rim slots", "re:M3 hex nut - retaining ring 5", n=5, side="L"),
            lab("Base (P12)", "name:base", n=6, side="R")])
fig("slew-drum", [S(PED, "context"), S(["name:pedestal wall +u (removable access)", "name:pedestal wall +v"], "hide"),
                  S("re:pedestal shelf", "ghost", opacity=0.15), S(["name:slew-tube-bushing", "re:PEX bushing"], "context"),
                  S(["name:slew-drum", "re:slew drum PEX clamp", "name:3/4in PEX turret tube"]),
                  S(["name:1/2in copper elbow", "name:elbow-support", "name:conduit-end-fitting-pedestal"], "context")],
    dict(dir=[1.0, 0.75, 0.4], box=[[-100, -90, -200], [95, 95, 5]], margin=0.05), w=1700, h=1400,
    labels=[lab("Slew drum (P14) on the PEX tube", "name:slew-drum", side="R"),
            lab("Pinch clamp: M3 × 25 + lock washer + nut", "re:M3x25 socket head cap screw - slew drum", side="R"),
            lab("PEX tube end 1/16″ below the drum", at=(0, -10, -98), side="L"),
            lab("Copper elbow end inside the PEX bore", "name:1/2in copper elbow", side="L")])

# =============================================================== stage: control box
BOX_MOVE = [dict(sel="name:box front", d=[120, 0, 0]), dict(sel="name:box rear", d=[-120, 0, 0]),
            dict(sel="name:box right side", d=[0, -130, 0]), dict(sel="name:box left side", d=[0, 130, 0]),
            dict(sel="name:box top (removable)", d=[0, 0, 160])]
fig("box-exploded", [S(BOXW)], dict(dir=[-0.85, 0.7, 0.7], margin=0.05), w=2000, h=1400, move=BOX_MOVE,
    arrows=[dict(kind="move", sel=m["sel"], d=m["d"], endFrac=0.6) for m in BOX_MOVE[:4]],
    labels=[lab("Floor", "name:box floor", n=1, side="B"),
            lab("Front (to the sandbox; drilled)", "name:box front", n=2, side="R"),
            lab("Rear", "name:box rear", n=3, side="L"),
            lab("Right side", "name:box right side", n=4, side="R"),
            lab("Left side (fit after the lever axle)", "name:box left side", n=5, side="L"),
            lab("Top (removable, fitted last)", "name:box top (removable)", n=6, side="T"),
            lab("Bearing blocks", "name:axle bearing block left", n=7, side="L")])
AX = ["re:lever-hub", "re:axle bearing block", "re:lever axle", "re:5/16in rod 205"]
AXLE_MOVE = [dict(sel="name:axle bearing block left", d=[0, 60, 0]), dict(sel="name:axle bearing block right", d=[0, -60, 0]),
             dict(sel=["re:lever axle left"], d=[0, 110, 0]), dict(sel=["re:lever axle right"], d=[0, -110, 0]),
             dict(sel=["name:lever-hub-boom", "re:boom lever"], d=[0, 30, 0]),
             dict(sel=["name:lever-hub-bucket", "re:bucket lever"], d=[0, -30, 0])]
fig("axle-stack", [S("name:box floor", "context"), S(["name:lever-hub-boom", "name:lever-hub-stick", "name:lever-hub-bucket",
                                                      "re:axle bearing block", "re:lever axle", "re:5/16in rod 205",
                                                      "re:bearing block"])],
    dict(dir=[-0.55, 0.5, 0.45], box=bx_([-400, -210, -200], [-320, 210, -80]), margin=0.04), w=2200, h=1100,
    move=AXLE_MOVE,
    arrows=[dict(kind="move", sel="name:axle bearing block left", d=[0, 60, 0], endFrac=0.7),
            dict(kind="move", sel="name:axle bearing block right", d=[0, -60, 0], endFrac=0.7)],
    labels=[lab("5/16″ lever axle, 8-1/16″", "re:5/16in rod 205", n=1, side="T"),
            lab("Boom hub (P19) — operator's left", "name:lever-hub-boom", n=2, side="T"),
            lab("Stick hub (P20) — centre", "name:lever-hub-stick", n=3, side="T"),
            lab("Bucket hub (P21) — right", "name:lever-hub-bucket", n=4, side="T"),
            lab("Bearing block (W07/W08)", "name:axle bearing block left", n=5, side="B"),
            lab("5/16in SAE washer + nut, each end", "re:5/16in hex nut - lever axle left", n=6, side="B"),
            lab("2 × #6 × 3/4in from below, each block", "re:wood screw 01 - axle bearing block left", n=7, side="B")])
SP_MOVE = [dict(sel="name:slew-spool", d=[0, 0, 90]), dict(sel=["re:spool axle top"], d=[0, 0, 150]),
           dict(sel="name:spool-riser", d=[0, 0, 40]), dict(sel=["re:wood screw .* - spool riser"], d=[0, 0, 60]),
           dict(sel=["re:spool axle bottom"], d=[0, 0, -45]), dict(sel="re:5/16in rod 274", d=[0, 0, -15])]
fig("spool-stack", [S("name:box floor", "context"), S(["name:spool-riser", "name:slew-spool", "re:slew spool axle", "re:5/16in rod 274",
                                                       "re:spool axle", "re:wood screw .* - spool riser",
                                                       "re:slew-tube-post", "re:slew sleeve post"])],
    dict(dir=[-0.85, -0.55, 0.45], box=bx_([-420, -300, -260], [-240, -90, 160]), margin=0.04), w=1500, h=1700, move=SP_MOVE,
    arrows=[dict(kind="move", sel="name:slew-spool", d=[0, 0, 90], endFrac=0.5)],
    labels=[lab("Slew spool (P23)", "name:slew-spool", n=1, side="R"),
            lab("Spool riser (P25) + 3 × #6 × 3/4in", "name:spool-riser", n=2, side="R"),
            lab("5/16″ spool axle, 10-13/16″", "re:5/16in rod 274", n=3, side="L"),
            lab("Washer + jam nut in the 7/8″ counterbore under the floor", "re:jam nut - spool axle bottom", n=4, side="L"),
            lab("Washer + nut on top (fitted with the wheel)", "re:hex nut - spool axle top", n=5, side="L"),
            lab("Sleeve posts (P26 ×2) + 2 × #6 × 3/4in each", "name:slew-tube-post@B", n=6, side="R")])
fig("box-internals", [S(BOXW, "context"), S(["name:box top (removable)", "name:box left side", "name:box rear"], "hide"),
                      S(BOX_PARTS), S(["re:lever-knob", "re:handle", "name:slew-wheel", "re:slew wheel", "re:spool axle top"], "hide"),
                      S("re:wood screw .* - (box|bearing)", "hide")],
    dict(dir=[-0.85, 0.6, 0.6], margin=0.05), w=2000, h=1350, fitSel=[BOXW],
    labels=[lab("Lever axle + 3 hubs", "name:lever-hub-stick", n=1, side="L"),
            lab("Bearing blocks", "name:axle bearing block left", n=2, side="L"),
            lab("Spool riser + slew spool", "name:slew-spool", n=3, side="R"),
            lab("Sleeve posts", "name:slew-tube-post@A", n=4, side="R"),
            lab("Box conduit fitting (fitted in Stage 7)", "name:conduit-end-fitting-box", n=5, side="R")])

# =============================================================== stage: conduit, tubes, box mounting
fig("spacer-stack", [S(SANDBOX, "context"), S(["name:sandbox wall +v", "name:sandbox wall +u", "name:sandbox wall -v"], "hide"),
                     S("group:sandbox_hw", "hide"), S(PED, "hide"), S("group:pedestal", "hide"), S("group:pedestal_hw", "hide"),
                     S(["name:pedestal wall -u (conduit)", "name:spacer frame 1", "name:spacer frame 2",
                        "name:conduit-end-fitting-pedestal", "re:through-rod"])],
    dict(dir=[0.75, 0.75, 0.45], box=[[-230, -110, -200], [10, 100, 0]], margin=0.05), w=1800, h=1300,
    move=[dict(sel=["name:pedestal wall -u (conduit)", "name:spacer frame 1", "name:spacer frame 2",
                    "name:conduit-end-fitting-pedestal", "re:through-rod"], d=[80, 0, 0])],
    arrows=[arrow((-20, -100, -100), (-90, -100, -100))],
    labels=[lab("Spacer frames W22 + W23, glued to the pedestal wall", "name:spacer frame 1", side="L"),
            lab("Pedestal wall −u (W10)", "name:pedestal wall -u (conduit)", side="R"),
            lab("8-32 rods, nuts on the pedestal fitting", "re:8-32 hex nut - through-rod 4 pedestal side", side="R"),
            lab("Rods go through the four 3/16″ holes in the sandbox wall", "name:sandbox wall -u (box side)", side="L")])
fig("tube-window", [S("name:conduit-end-fitting-box")], dict(dir=[1.0, -0.25, 0.25], box=[[FIT_BOX_U - 26, -62, -164], [FIT_BOX_U, 46, -56]], margin=0.08),
    w=1500, h=1300, ropes=dict(circuits=["stick", "bucket", "boom", "slew"], scale=1.2, ptfe=True, ptfeOpacity=0.85),
    labels=[lab("4 PTFE tubes seat together in the rounded window", at=(FIT_BOX_U, -6, -130), side="R"),
            lab("Boom rope holes (bare rope)", at=(FIT_BOX_U, -12, -130), side="L"),
            lab("Slew sleeve holes (Ø4.6, pass-through)", at=(FIT_BOX_U, -17, -88), side="L"),
            lab("Conduit socket", at=(FIT_BOX_U, 25, -90), side="R")])
fig("box-mount", [S(SANDBOX, "context"), S(["name:sandbox wall +v", "name:sandbox wall +u", "name:sandbox wall -v"], "hide"),
                  S("group:sandbox_hw", "hide"), S(PED, "hide"), S("group:pedestal", "hide"), S("group:pedestal_hw", "hide"),
                  S(BOXW, "context"), S(["name:box top (removable)", "name:box left side"], "hide"),
                  S(["name:conduit-end-fitting-box", "re:through-rod", "re:box to sandbox"])],
    dict(dir=[-0.6, 0.9, 0.55], box=bx_([-460, -310, -210], [-150, 120, -40]), margin=0.04), w=2000, h=1350,
    labels=[lab("4 × 8-32 rod: nut on the box fitting", "re:8-32 hex nut - through-rod 2 box side", n=1, side="T"),
            lab("2 × M3 × 30 at the lower corners", "re:M3x30 socket head cap screw - box to sandbox left", n=2, side="L"),
            lab("Flat washers both sides; nuts inside the sandbox", "re:M3 hex nut - box to sandbox right", n=3, side="R"),
            lab("Box conduit fitting (P18)", "name:conduit-end-fitting-box", n=4, side="L")])
fig("ptfe-route", [S(SANDBOX, "context"), S(["name:sandbox wall +v", "name:sandbox wall +u"], "hide"), S("group:sandbox_hw", "hide"),
                   S(PED, "context"), S(["name:pedestal wall +v", "name:pedestal wall +u (removable access)", "name:pedestal top"], "hide"),
                   S("group:pedestal_hw", "hide"),
                   S(["name:1/2in copper elbow", "name:3/4in PEX turret tube"], "ghost", opacity=0.25),
                   S(["name:spacer frame 1", "name:spacer frame 2"], "context"),
                   S(["re:conduit-end-fitting", "name:slew-drum", "name:tower", "name:base", "name:slewing-ring-retaining-ring",
                      "name:boom-half-right", "name:stick-half-right", "name:boom-drum", "name:stick-drum", "name:bucket-drum-axle"], "context")],
    dict(dir=[-0.1, 1.0, 0.2], box=[[FIT_BOX_U - 35, -60, -170], [370, 60, 215]], margin=0.03), w=2400, h=1200,
    ropes=dict(circuits=["stick", "bucket"], scale=1.2, ptfe=True, ptfeScale=2.2, ptfeOpacity=0.9),
    clip=[dict(n=[0, -1, 0], d=0.0)], clipSel=["name:tower", "name:base", "name:slewing-ring-retaining-ring", "re:conduit-end-fitting", "name:slew-drum"],
    labels=[lab("Box fitting window (tube stop)", "name:conduit-end-fitting-box", side="B"),
            lab("Spacer chamber: spare tube length bows here", at=(-125, -8, -128), side="B"),
            lab("Pedestal fitting window (tubes slide)", "name:conduit-end-fitting-pedestal", side="B"),
            lab("Up the copper elbow and the PEX tube", at=(0, 0, -40), side="B"),
            lab("Stick tubes stop in the boom tip", at=(160, 0, 172), side="T"),
            lab("Bucket tubes stop in the stick nose", at=(305, 0, 128), side="T")])

# =============================================================== stage: arm
fig("boom-drum-keys", [S("name:boom-drum"), S("re:boom drum key")], dict(dir=[0.9, 0.35, 0.65], margin=0.12), w=1500, h=1100,
    points=dict(face=(0, 7.0, 89 - 20), head=(0, 17.0, 89 - 20)),
    labels=[lab("Boom drum (P05)", "name:boom-drum", side="R"),
            lab("M3 × 12 key screw (4: two per face)", "re:boom drum key left 1", side="L"),
            lab("Crimp pocket (rope midpoint)", at=(0, 0, 89 + 15), side="R")])
fig("boom-half-open", [S("name:boom-half-right"), S(["name:boom-drum", "re:boom drum key right", "re:boom drum key left"]),
                       S("name:tower", "context"), S(["re:boom split pin"], "context")],
    dict(dir=[0.05, 1.0, 0.12], box=[[-30, -30, 60], [200, 30, 200]], margin=0.04), w=2200, h=1300,
    ropes=dict(circuits=["boom", "stick", "bucket"], scale=1.4, ptfe=True, ptfeScale=1.4, ptfeOpacity=0.85),
    labels=[lab("Boom half, right (P02), split face up", "name:boom-half-right", side="T"),
            lab("Boom drum: key-screw heads drop into the wall pockets", "name:boom-drum", side="R"),
            lab("Stick tubes: to their stop in the boom tip", at=(160, 0, 172), side="T"),
            lab("Bucket tubes: on through the boom tip", at=(185, 4, 178), side="R"),
            lab("Boom ropes: straight down into the tower", at=(5, 0, 55), side="B")])
fig("boom-close", [S(["name:boom-half-right", "name:boom-half-left", "name:boom-drum"]), S("re:boom joining lug")],
    dict(dir=[-0.35, 1.0, 0.45], margin=0.05), w=2000, h=1200,
    move=[dict(sel=["name:boom-half-left"], d=[0, 90, 0]), dict(sel=["re:M3x20 socket head cap screw - boom joining lug"], d=[0, 45, 0])],
    arrows=[dict(kind="move", sel="name:boom-half-left", d=[0, 90, 0], endFrac=0.7, at=(90, 115, 160))],
    labels=[lab("Boom half, left (P01)", "name:boom-half-left", n=1, side="T"),
            lab("Boom half, right (P02)", "name:boom-half-right", n=2, side="B"),
            lab("Joining lugs: M3 × 20 + nut (see Open item 3)", "re:M3x20 socket head cap screw - boom joining lug 3", n=3, side="T")])
fig("boom-pins", [S(["member:boom"]), S(["name:tower"]), S(["re:boom split pin"]), S("re:joining lug|drum key", "hide"),
                  S("name:base", "context")],
    dict(dir=[-0.9, 0.55, 0.35], box=[[-60, -70, 20], [60, 70, 140]], margin=0.05), w=1700, h=1300,
    move=[dict(sel="re:boom split pin left", d=[0, 55, 0]), dict(sel="re:boom split pin right", d=[0, -55, 0])],
    arrows=[arrow((0, 115, 89), (0, 75, 89)), arrow((0, -115, 89), (0, -75, 89))],
    labels=[lab("8-32 rod, 1-5/8″ (one per side)", "name:8-32 threaded rod 42 mm - boom split pin left", side="T"),
            lab("Jam pair: 2 × 8-32 nut, outside the tower cheek", "re:jam 2\\) - boom split pin left", side="R"),
            lab("Inner end flush with the boom's inner wall", at=(0, 17, 89), side="B"),
            lab("Tower cheek", "name:tower", side="L")])
fig("stick-half-open", [S("name:stick-half-right"), S(["name:stick-drum", "re:stick drum key", "name:bucket-drum-axle"]),
                        S("name:boom-half-right", "context")],
    dict(dir=[0.05, 1.0, 0.12], box=[[160, -30, 90], [370, 30, 210]], margin=0.04), w=2200, h=1250,
    ropes=dict(circuits=["stick", "bucket"], scale=1.4, ptfe=True, ptfeScale=1.4, ptfeOpacity=0.85),
    labels=[lab("Stick half, right (P04)", "name:stick-half-right", side="B"),
            lab("Stick drum (P06) on its key screws", "name:stick-drum", side="T"),
            lab("Bucket drum-axle (P07): journals in the nose holes", "name:bucket-drum-axle", side="R"),
            lab("Bucket tubes: stop in the stick nose", at=(305, 0, 128), side="T"),
            lab("Stick tube stops (boom tip)", at=(160, 0, 172), side="L")])
fig("stick-drum-keys", [S("name:stick-drum"), S("re:stick drum key")], dict(dir=[0.9, 0.45, 0.6], margin=0.14), w=1400, h=1100,
    move=[dict(sel="re:stick drum key left", d=[0, 14, 0]), dict(sel="re:stick drum key right", d=[0, -14, 0])],
    labels=[lab("Stick drum (P06)", "name:stick-drum", side="R"),
            lab("Key screws enter the same through-pilot from both sides", "re:stick drum key left 1", side="L")])
fig("bucket-assembly", [S(["name:bucket", "name:bucket-ear-left", "name:bucket-ear-right", "name:bucket-drum-axle", "re:bucket pin"]),
                        S(["name:stick-half-right"], "context")],
    dict(dir=[0.8, 0.8, 0.45], box=[[290, -60, 20], [380, 60, 130]], margin=0.05), w=1800, h=1500,
    move=[dict(sel="name:bucket-ear-left", d=[0, 30, 0]), dict(sel="name:bucket-ear-right", d=[0, -30, 0]),
          dict(sel="re:bucket pin left", d=[0, 60, 0]), dict(sel="re:bucket pin right", d=[0, -60, 0]),
          dict(sel="name:8-32 threaded rod 65 mm - bucket pin", d=[0, 95, 0])],
    arrows=[arrow((344.8, 60, 135), (344.8, 30, 135)), arrow((344.8, -60, 135), (344.8, -30, 135))],
    labels=[lab("Ear, left (P09): hex socket on the axle's hex end", "name:bucket-ear-left", n=1, side="L"),
            lab("Ear, right (P10)", "name:bucket-ear-right", n=2, side="R"),
            lab("Bucket drum-axle (P07) in the stick nose", "name:bucket-drum-axle", n=3, side="R"),
            lab("8-32 rod, 2-9/16″: the bucket pin", "name:8-32 threaded rod 65 mm - bucket pin", n=4, side="L"),
            lab("Jam pair each end", "re:jam 2\\) - bucket pin right", n=5, side="R"),
            lab("Bucket (P08): glue faces on the lugs", "name:bucket", n=6, side="R")])
fig("stick-pins", [S(["member:stick", "member:bucket"]), S("name:boom-half-left", "ghost", opacity=0.25),
                   S("name:boom-half-right"), S(["re:stick split pin"]), S("re:joining lug|drum key|bucket pin", "hide")],
    dict(dir=[0.3, 1.0, 0.25], box=[[140, -70, 130], [240, 70, 240]], margin=0.06), w=1600, h=1200,
    move=[dict(sel="re:stick split pin left", d=[0, 45, 0]), dict(sel="re:stick split pin right", d=[0, -45, 0])],
    labels=[lab("8-32 rod, 7/8″ (one per side)", "name:8-32 threaded rod 22 mm - stick split pin left", side="R"),
            lab("Jam pair outside the boom tip", "re:jam 2\\) - stick split pin left", side="T"),
            lab("Boom tip", "name:boom-half-right", side="L")])

# =============================================================== stage: arm ropes at the levers
fig("rigging-pose", [S(["member:boom", "member:stick", "member:bucket", "name:tower", "name:base", "name:slewing-ring-retaining-ring"]),
                     S("re:joining lug|drum key", "hide")],
    dict(dir=SIDE, margin=0.08), w=2200, h=1150, pose=dict(boom=MID["boom"], stick=MID["stick"], bucket=MID["bucket"]),
    points=dict(pb=(PB[0], 0, PB[1]), ps=(PS[0], 0, PS[1]), pk=(PK[0], 0, PK[1])))
fig("lever-hub-detail", [S(["name:lever-hub-boom", "re:boom lever"]), S("re:5/16in rod 205", "context"),
                         S("re:5/16in rod 145 mm - boom", "context")],
    dict(dir=[-0.75, 0.9, 0.4], box=bx_([-395, 5, -158], [-325, 85, -84]), margin=0.06), w=1800, h=1350,
    labels=[lab("Rope anchors: M3 × 10 button head in the slot (tension adjuster)", "re:button head screw - boom lever rope anchor upper", n=1, side="L"),
            lab("Washer — rope loop — washer under the head", "re:over rope loop\\) - boom lever rope anchor lower", n=2, side="L"),
            lab("Rope holes through the rim into the groove", at=(AU - 29.5, 19, -124), n=3, side="L"),
            lab("Handle socket + pinch clamp (M3 × 20)", "re:M3x20 socket head cap screw - boom lever handle clamp", n=4, side="R"),
            lab("Drag clamp (M3 × 20 + lock washer)", "re:M3x20 socket head cap screw - boom lever drag clamp", n=5, side="R"),
            lab("Ø60 drum groove", at=(AU, 19, -90.8), n=6, side="R")])
fig("lever-motion", [S(BOXW, "context"), S(["name:box left side", "name:box top (removable)"], "ghost", opacity=0.12),
                     S(["name:box rear", "name:box front"], "hide"),
                     S(BOX_PARTS), S("re:wood screw", "hide"), S("name:conduit-end-fitting-box", "context"),
                     S(["name:slew-wheel", "name:slew-spool", "name:spool-riser", "re:slew-tube-post", "re:spool axle",
                        "re:slew wheel", "re:slew spool", "re:sleeve post", "re:5/16in rod 274", "re:box conduit fitting",
                        "re:box to sandbox"], "hide")],
    dict(dir=[0.0, -1.0, 0.08], box=bx_([-460, 0, -205], [-195, 0, 75]), margin=0.05), w=1800, h=1350,
    ropes=dict(circuits=["boom"], scale=1.8, ptfe=False, clip=True), fitSel=[BOXW],
    clip=[dict(n=[0, 1, 0], d=-15.0)], clipSel=[BOXW, "group:box", "group:box_hw"],
    arrows=[rot((AU, 70, AZ), (0, -1, 0), 172, 110, 70, ref=(1, 0, 0))],
    labels=[lab("Push = forward (toward the sandbox)", at=(AU + 60, 70, KNOB_Z - 10), side="R"),
            lab("Lever axle (5/16in rod)", at=(AU, 70, AZ), side="L"),
            lab("Boom rope strands to the box fitting", at=(-262 + DU, 19, -122), side="R")])

# =============================================================== stage: slew ropes
fig("slew-path", [S(SANDBOX, "context"), S(["name:sandbox wall +v", "name:sandbox wall +u", "name:sandbox wall -v"], "hide"),
                  S("group:sandbox_hw", "hide"),
                  S(PED, "context"), S(["name:pedestal wall +v", "name:pedestal top", "name:pedestal wall +u (removable access)"], "hide"),
                  S("group:pedestal_hw", "hide"), S("re:pedestal shelf", "hide"),
                  S(BOXW, "context"), S(["name:box top (removable)", "name:box left side", "name:box rear"], "hide"),
                  S(["name:slew-spool", "re:slew-tube-post", "re:conduit-end-fitting", "name:slew-drum", "name:spool-riser",
                     "name:3/4in PEX turret tube"]),
                  S(["re:lever-hub"], "ghost", opacity=0.18),
                  S(["name:1/2in copper elbow", "name:elbow-support"], "context")],
    dict(dir=[-0.25, 0.55, 1.0], box=[[ex.BOX_U[0], -300, -200], [90, 120, 0]], margin=0.03), w=2200, h=1250,
    ropes=dict(circuits=["slew"], scale=2.2, ptfe=True, ptfeScale=1.8, ptfeOpacity=0.7),
    labels=[lab("Slew spool (wheel)", "name:slew-spool", n=1, side="L"),
            lab("Sleeve posts: sleeve ends seat here", "name:slew-tube-post@B", n=2, side="B"),
            lab("PTFE sleeves through the box fitting and the spacer chamber", at=(-125, -10, -88), n=3, side="T"),
            lab("Pedestal fitting: angled counterbores (sleeve stops)", "name:conduit-end-fitting-pedestal", n=4, side="T"),
            lab("Slew drum: crimp pockets", "name:slew-drum", n=5, side="R")])
fig("spool-anchors", [S(["name:slew-spool", "re:slew spool rope anchor"]), S("name:spool-riser", "context")],
    dict(dir=[0.35, 0.25, 1.0], box=bx_([-400, -250, -110], [-280, -130, -60]), margin=0.05), w=1600, h=1300,
    ropes=dict(circuits=["slew"], scale=1.6, ptfe=False),
    labels=[lab("Anchor A: M3 × 10 button head, washers each side of the loop", "re:button head screw - slew spool rope anchor A", side="L"),
            lab("Anchor B", "re:button head screw - slew spool rope anchor B", side="R"),
            lab("Upper lane", at=(WC[0] - 55, WC[1], -84.4), side="L"),
            lab("Lower lane", at=(WC[0] + 55, WC[1], -91.6), side="R")])

# =============================================================== stage: top, handles, wheel
TOP_MOVE = [dict(sel="name:box top (removable)", d=[0, 0, 120]),
            dict(sel=["re:lever-knob", "re:5/16in rod 145"], d=[0, 0, 210]),
            dict(sel=["name:slew-wheel", "re:slew wheel \\d", "re:spool axle top"], d=[0, 0, 170])]
fig("top-exploded", [S(BOXW, "context"), S(BOX_PARTS), S("re:wood screw", "hide"), S("name:box top (removable)")],
    dict(dir=[-0.9, 0.65, 0.75], margin=0.04), w=2000, h=1600, fitSel=[BOXW, "re:lever-knob", "name:slew-wheel"],
    move=TOP_MOVE,
    arrows=[dict(kind="move", sel="name:box top (removable)", d=[0, 0, 120], endFrac=0.6, at=(-330 + DU, 100, 80)),
            dict(kind="move", sel="name:slew-wheel", d=[0, 0, 170], endFrac=0.45, at=(-250 + DU, -190, 225)),
            dict(kind="move", sel="re:5/16in rod 145 mm - bucket", d=[0, 0, 210], endFrac=0.35, at=(AU, -70, 170))],
    labels=[lab("Top panel (W06)", "name:box top (removable)", n=1, side="L"),
            lab("5/16″ rod handle, 5-11/16″ (×3)", "name:5/16in rod 145 mm - stick lever handle", n=2, side="L"),
            lab("Lever knob (P22 ×3), glued", "name:lever-knob@boom", n=3, side="L"),
            lab("Slew wheel (P24): 3 × M3 × 20 + lock washer + nut", "name:slew-wheel", n=4, side="R"),
            lab("5/16in washer + nut on the spool axle", "re:hex nut - spool axle top", n=5, side="R")])

# =============================================================== final: ranges
fig("ranges", [S(["member:boom", "member:stick", "member:bucket", "name:tower", "name:base", "name:slewing-ring-retaining-ring"]),
               S("re:joining lug|drum key", "hide")],
    dict(dir=SIDE, margin=0.30), w=2200, h=1300,
    points=dict(pb=(PB[0], 0, PB[1]), ps=(PS[0], 0, PS[1]), pk=(PK[0], 0, PK[1])))


fig("service-access", [S("all"), S("group:sandbox_hw", "hide"), S("re:wood screw", "hide"),
                       S(["name:sandbox wall +v", "name:sandbox wall +u"], "ghost", opacity=0.10),
                       S(["name:box top (removable)", "name:pedestal wall +u (removable access)"], "focus", color="#f08a24")],
    dict(dir=[-0.55, 1.0, 0.7], margin=0.05), w=1800, h=1400, fitSel=["group:box_wood", "group:pedestal_wood", "member:boom"],
    move=[dict(sel=["name:box top (removable)", "re:lever-knob", "re:5/16in rod 145", "name:slew-wheel", "re:slew wheel \\d",
                    "re:spool axle top"], d=[0, 0, 130]),
          dict(sel="name:pedestal wall +u (removable access)", d=[150, 0, 0])],
    arrows=[dict(kind="move", sel="name:box top (removable)", d=[0, 0, 130], endFrac=0.6, at=(-330 + DU, 100, 100)),
            dict(kind="move", sel="name:pedestal wall +u (removable access)", d=[150, 0, 0], endFrac=0.6, at=(240, 100, -100))],
    labels=[lab("Box top: lift off (screws only)", "name:box top (removable)", n=1),
            lab("Pedestal wall +u: unscrew (move the sand away first)", "name:pedestal wall +u (removable access)", n=2)])


def main():
    out = Path(sys.argv[1])
    out.write_text(json.dumps(F, indent=1))
    print(f"{len(F)} figures -> {out}")


if __name__ == "__main__":
    main()
