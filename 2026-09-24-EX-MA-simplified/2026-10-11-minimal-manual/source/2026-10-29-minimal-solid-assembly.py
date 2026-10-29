#!/usr/bin/env python3
"""EX-MA MINIMAL design (no PVC conduit) as real solid bodies (STEP AP214), zipped.

    MINIMAL_SRC=<minimal Source dir> python 2026-10-29-minimal-solid-assembly.py <work dir>

The minimal Source dir is made by 2026-10-11-make-minimal-source.py (7/16in OSB, 5/8in particle-board
sandbox floor, no shim, spacer stack, compact box with the kept prints). This script reuses the full
design's solid-assembly pipeline from that tree (Source/2026-09-28-solid-assembly.py and
2026-09-28-solid-hardware.py, run on the minimal constants) and applies the same changes as the
minimal manual (2026-10-11-minimal-scene-export.py), as solids:

  removed  2in PVC conduit; the 8 M3 conduit-fitting bolts with their washers and nuts; the two
           #6 x 3/4in elbow-support screws; the short spool axle of the compact spec
  added    spacer frames W22 + W23 (100 mm window); four 8-32 through-rods (78 mm) with a nut on each
           fitting flange; elbow support with its 4 mm base plate cut off and one #6 x 1-1/4in screw up
           through the floor; the 274 mm spool axle of the kept 145 mm spool
  wood     7/16in OSB everywhere (bearing blocks and shelf too); sandbox floor 24in x 24in x 5/8in

EX-MA parts: tower, bucket and the four arm halves come from <work>/parts (converted from the print
meshes by Source/2026-09-28-mesh-to-brep.py and 2026-09-28-arm-halves-cad.py); base, bucket ears and
retaining ring are the 2026-09-29 CAD solids from STEP/.

Writes <work>/<assembly>.step, reads it back, checks it, and writes
../2026-10-29-ex-ma-minimal-solid-assembly.zip (assembly, EX-MA parts, sawn elbow support, README,
checks.json).
"""
import importlib.util
import json
import os
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import trimesh
import cadquery as cq

HERE = Path(__file__).resolve().parent
MAN = HERE.parent
PROJ = MAN.parent
MSRC = Path(os.environ["MINIMAL_SRC"])
STEP_DIR = PROJ / "STEP"
STL_DIR = PROJ / "STL"
ZIP_PATH = MAN / "2026-10-29-ex-ma-minimal-solid-assembly.zip"
ASSEMBLY_NAME = "2026-10-29-ex-ma-minimal-solid-assembly.step"


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


sa = _load("solid_assembly", MSRC / "2026-09-28-solid-assembly.py")    # full pipeline, minimal constants
H, ex, asm, bx = sa.H, sa.ex, sa.asm, sa.bx
T = ex.T_WOOD
IN = 25.4
V = cq.Vector

sa.COLOURS.update(osb=(0.80, 0.66, 0.44), osb_box=(0.74, 0.58, 0.36), spacer=(0.89, 0.66, 0.42),
                  particle=(0.80, 0.72, 0.58))

# EX-MA parts: (assembly name, source STEP, matching print STL, group, colour)
EXMA = {
    "boom-half-left": ("parts", "2026-09-24-boom-half-left", "Arm", "petg"),
    "boom-half-right": ("parts", "2026-09-24-boom-half-right", "Arm", "petg"),
    "stick-half-left": ("parts", "2026-09-24-stick-half-left", "Arm", "petg"),
    "stick-half-right": ("parts", "2026-09-24-stick-half-right", "Arm", "petg"),
    "bucket": ("parts", "2026-09-24-bucket", "Arm", "exma_base"),
    "tower": ("parts", "2026-09-24-tower", "Turret and slewing ring", "exma_dark"),
    "bucket-ear-left": ("2026-09-29-bucket-ear-left-cad", "2026-09-29-bucket-ear-left-cad", "Arm", "ear"),
    "bucket-ear-right": ("2026-09-29-bucket-ear-right-cad", "2026-09-29-bucket-ear-right-cad", "Arm", "ear"),
    "base": ("2026-09-29-base", "2026-09-29-base", "Turret and slewing ring", "exma_base"),
}


def exma_step(name, work):
    src = EXMA[name][0]
    return work / "parts" / f"{name}.step" if src == "parts" else STEP_DIR / f"{src}.step"


def one_solid(path):
    sol = cq.importers.importStep(str(path)).solids().vals()
    assert len(sol) == 1, (path, len(sol))
    return sol[0]


# ---------------------------------------------------------------- items
def exma_items(work):
    return [(g, name, one_solid(exma_step(name, work)), col) for name, (_, _, g, col) in EXMA.items()]


def elbow_support_sawn():
    """Printed elbow support with its 4 mm base plate cut off (print frame: plate z 0..4)."""
    s = cq.importers.importStep(str(STEP_DIR / "2026-09-24-elbow-support.step")).val()
    bb = s.BoundingBox()
    keep = cq.Solid.makeBox(bb.xlen + 10, bb.ylen + 10, bb.zmax - 4.0 + 5,
                            cq.Vector(bb.xmin - 5, bb.ymin - 5, 4.0))
    out = s.intersect(keep)
    sol = out.Solids()
    assert len(sol) == 1 and sol[0].isValid()
    return sol[0]


def printed_items():
    out = []
    P = asm.placements()
    files = {"slewing-ring-retaining-ring": "2026-09-29-slewing-ring-retaining-ring"}
    cache = {"elbow-support": elbow_support_sawn()}
    for key, Tm in P.items():
        base = key.split("@")[0]
        if base not in cache:
            cache[base] = cq.importers.importStep(str(STEP_DIR / f"{files.get(base, '2026-09-24-' + base)}.step")).val()
        name = base if "@" not in key else f"{base}-{key.split('@')[1]}"
        if base == "elbow-support":
            name = "elbow-support (base plate cut off)"
        out.append((sa.PRINTED_GROUP[base], name, H.placed(cache[base], Tm), "pla"))
    knob = cq.importers.importStep(str(STEP_DIR / "2026-09-24-lever-knob.step")).val()
    for j, (vh, vd) in ex.LEVERS.items():
        Tm = H.frame((ex.AXLE_U, vh, ex.AXLE_Z + ex.HANDLE_LEN), (0, 0, 1), (1, 0, 0))
        out.append(("Control box", f"lever-knob-{j}", H.placed(knob, Tm), "pla"))
    return out


def panels():
    import copy
    P = bx.panels()
    for p in P:
        if p.name == "sandbox floor":                       # the 2 x 2 ft particle board, uncut
            p.hi = (p.lo[0] + 24 * IN, p.lo[1] + 24 * IN, p.hi[2])
        if p.name.startswith("axle bearing block") or p.name == "pedestal shelf":
            ax = {"v": 1, "z": 2}[p.normal]                 # 12 mm in build-box: 7/16in OSB here
            lo, hi = list(p.lo), list(p.hi)
            if p.name == "axle bearing block left":
                lo[ax] = hi[ax] - T                         # keep the outer faces where they are
            else:
                hi[ax] = lo[ax] + T
            p.lo, p.hi = tuple(lo), tuple(hi)
    w = next(p for p in P if p.name.startswith("pedestal wall -u"))
    for k in (1, 2):
        sp = copy.deepcopy(w)
        sp.name, sp.group, sp.holes = f"spacer frame {k}", "spacer", []
        u0 = w.lo[0] - k * T
        sp.lo, sp.hi = (u0, w.lo[1], w.lo[2]), (u0 + T, w.hi[1], w.hi[2])
        P.append(sp)
    return P


WID = {}


def wood_items():
    out = []
    P = panels()
    for i, p in enumerate(P):
        wid = f"W{i + 1:02d}" if i < 21 else ("W22" if p.name.endswith("1") else "W23")
        if p.group == "spacer":
            c = [(l + h) / 2 for l, h in zip(p.lo, p.hi)]
            sz = [h - l for l, h in zip(p.lo, p.hi)]
            shp = (cq.Workplane("XY").box(*sz).translate(c)
                   .cut(cq.Workplane("XY").box(sz[0] * 3, 100.0, 100.0).translate((c[0], ex.PED_FIT_V, ex.COND_Z)))).val()
            out.append(("Pedestal", f"{wid} OSB {p.name}", shp, "spacer"))
            continue
        mat = "particle board" if p.name == "sandbox floor" else "OSB"
        col = "particle" if p.name == "sandbox floor" else ("osb_box" if p.group == "control-box" else "osb")
        out.append((sa.WOOD_GROUP[p.group], f"{wid} {mat} {p.name}", bx.panel_solid(p).val(), col))
    return out


DROP = ("pedestal conduit fitting", "box conduit fitting", "elbow support", "slew spool axle", "2in PVC conduit")


def hardware_items():
    items = [it for it in sa.hardware_items() if not any(k in it[1] for k in DROP)]
    g = "Hardware/8-32 through-rods"
    nut = H.hex_nut(H.N832["nut_af"], H.N832["nut_m"], H.N832["d"])
    m = H.N832["nut_m"]
    u_box = ex.BOX_U[1] - T - 6.0                           # P18 flange face inside the box
    u_ped = ex.PED_U[0] + T + 6.0                           # P17 flange face inside the pedestal
    L = (u_ped - u_box) + 2 * (m + 2.0)
    for i, p in enumerate(bx.fitting_bolts((ex.BOX_U[1] - T, ex.MOUTH_V, ex.COND_Z), -1)):
        v, z = p[1], p[2]
        items.append((g, f"8-32 through-rod {L:.0f} mm {i + 1}", H.placed(H.rod(H.N832["d"], L), H.frame((u_ped + m + 2.0, v, z), (1, 0, 0))), "steel"))
        items.append((g, f"8-32 hex nut - through-rod {i + 1} box side", H.placed(nut, H.frame((u_box - m, v, z), (-1, 0, 0))), "steel"))
        items.append((g, f"8-32 hex nut - through-rod {i + 1} pedestal side", H.placed(nut, H.frame((u_ped + m, v, z), (1, 0, 0))), "steel"))
    z0, z1 = ex.BOX_Z[0], 72.0                              # kept 145 mm spool: axle from the floor to z 72
    items.append(("Hardware/5-16 rod, nuts, washers", f"5/16in rod {z1 - z0:.0f} mm - slew spool axle",
                  H.placed(H.rod(H.R516["d"], z1 - z0), H.frame((*ex.WHEEL_C, z1), (0, 0, 1))), "steel"))
    items.append(("Hardware/wood screws", "#6 x 1-1/4in wood screw - elbow support (up through the floor)",
                  H.placed(H.wood_screw(1.25 * IN, H.WOOD6), H.frame((asm.ELBOW_SUPPORT_U, 0.0, ex.GROUND), (0, 0, -1))), "zinc"))
    return items


# ---------------------------------------------------------------- checks
def check_parts(work):
    rep = {}
    for name, (_, stl, _, _) in EXMA.items():
        s = one_solid(exma_step(name, work))
        m = trimesh.load(STL_DIR / f"{stl}.stl", force="mesh")
        vs, ts = s.tessellate(0.05, 0.2)
        rm = trimesh.Trimesh(np.array([(p.x, p.y, p.z) for p in vs]), np.array(ts))
        a, _ = trimesh.sample.sample_surface(rm, 20000, seed=1)
        b, _ = trimesh.sample.sample_surface(m, 20000, seed=2)
        d = np.r_[trimesh.proximity.closest_point(m, a)[1], trimesh.proximity.closest_point(rm, b)[1]]
        n_tri, share = sa.triangle_faces(s)
        rep[name] = dict(source=exma_step(name, work).name if EXMA[name][0] != "parts" else "converted from the print STL",
                         valid=bool(s.isValid()), faces=len(s.Faces()), triangle_faces=n_tri,
                         triangle_area_percent=round(share, 1), volume=round(s.Volume(), 1), stl_volume=round(float(m.volume), 1),
                         dev_p99=round(float(np.percentile(d, 99)), 3), dev_max=round(float(d.max()), 3))
        print(f"  {name}: {rep[name]}", flush=True)
    return rep


README = """EX-MA manual excavator - MINIMAL design (no PVC conduit), assembly as solid bodies
==================================================================================

{step}
    STEP AP214, millimetres, Z up. Floor bottom (control box and sandbox) on Z = 0, footprint
    centred on X = 0 / Y = 0. X runs from the box rear toward the sandbox, Y to the operator's left.
parts/        the nine EX-MA parts on their own in the build frame, and the elbow support with its
              base plate cut off (print frame).
checks.json   the numbers below, machine readable.

This is the build in 2026-10-11-ex-ma-minimal-manual.pdf: 7/16in OSB, 5/8in particle-board sandbox
floor (24 x 24in, uncut), no shim, two OSB spacer frames and four 8-32 through-rods instead of the
2in PVC conduit, compact control box ({box}) with the lever hubs and 145 mm slew spool as already
printed. Wood pieces carry the manual's W numbers.

Structure: one component per part, each one solid body, grouped as
{groups}
Components: {n}.

Every body is a B-rep solid (holes are cylinders, faces are planes / cylinders / cones / spheres).
Fasteners have plain shanks at the nominal diameter (no modelled threads). Ropes and PTFE tubes
are swept along their modelled paths at the built pose.

EX-MA parts (deviation = surface distance to the print STL):
{parts}

Assembly read back: {asm}

Notes:
- the elbow support's post sits on the sandbox floor; its single #6 x 1-1/4in screw comes up
  through the floor (manual Stage 4).
- the 7/16in OSB shelf rests on its cleats about 0.9 mm lower than the 12 mm shelf of the design,
  so the PEX bushing sits that much lower (it still guides the tube; nothing else moves).
- the drum key screws of the stick drum overlap as in the design (manual Open item 1).

Rebuild: MINIMAL_SRC=$(python 2026-10-11-make-minimal-source.py WORK) \\
         python 2026-10-11-minimal-manual/source/2026-10-29-minimal-solid-assembly.py WORK
         (after converting the parts into WORK/parts with Source/2026-09-28-mesh-to-brep.py and
         2026-09-28-arm-halves-cad.py; CadQuery 2.x, trimesh, manifold3d, shapely)
"""


def main():
    work = Path(sys.argv[1])
    t = time.time()
    print("1. EX-MA parts", flush=True)
    part_rep = check_parts(work)
    print(f"2. items ({time.time() - t:.0f}s)", flush=True)
    items = exma_items(work) + printed_items() + wood_items() + hardware_items()
    bad = [n for g, n, s, c in items if not s.isValid() or len(s.Solids()) != 1]
    if bad:
        raise RuntimeError(f"not one valid solid: {bad}")
    gone = [n for g, n, s, c in items if any(k in n for k in ("PVC", "conduit fitting "))]
    assert not gone, gone
    print(f"   {len(items)} components", flush=True)
    print(f"3. assembly ({time.time() - t:.0f}s)", flush=True)
    step = work / ASSEMBLY_NAME
    sa.build(items).export(str(step))
    print(f"4. checks ({time.time() - t:.0f}s)", flush=True)
    asm_rep = sa.check_assembly(step, len(items))
    print(f"   {asm_rep}", flush=True)
    counts = Counter(g for g, n, s, c in items)
    checks = dict(assembly=asm_rep, parts=part_rep, groups=dict(counts), shift=sa.SHIFT.round(3).tolist(),
                  components=sorted(f"{g}/{n}" for g, n, s, c in items))
    (work / "checks.json").write_text(json.dumps(checks, indent=1))
    groups = "\n".join(f"  {g}: {k}" for g, k in sorted(counts.items()))
    prt = "\n".join(f"  {n}: {r['source']}; valid {r['valid']}, {r['faces']} faces, deviation p99 {r['dev_p99']} mm / "
                    f"max {r['dev_max']} mm" for n, r in part_rep.items())
    bb = asm_rep["bbox"]
    readme = README.format(step=ASSEMBLY_NAME, groups=groups, n=len(items), parts=prt,
                           box="8-7/16 x 15 x 6-1/8in",
                           asm=f"{asm_rep['solids']} solids for {asm_rep['components']} components, {asm_rep['invalid']} invalid, "
                               f"size {bb[3] - bb[0]:.1f} x {bb[4] - bb[1]:.1f} x {bb[5] - bb[2]:.1f} mm "
                               f"({(bb[3] - bb[0]) / IN:.2f} x {(bb[4] - bb[1]) / IN:.2f} x {(bb[5] - bb[2]) / IN:.2f} in)")
    elbow = work / "elbow-support-base-plate-cut-off.step"
    cq.exporters.export(cq.Workplane().add(elbow_support_sawn()), str(elbow))
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(step, ASSEMBLY_NAME)
        for name in EXMA:
            z.write(exma_step(name, work), f"parts/{name}.step")
        z.write(elbow, "parts/elbow-support-base-plate-cut-off.step")
        z.writestr("checks.json", json.dumps(checks, indent=1))
        z.writestr("README.txt", readme)
    print(f"written {ZIP_PATH} ({ZIP_PATH.stat().st_size / 1e6:.1f} MB, {time.time() - t:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
