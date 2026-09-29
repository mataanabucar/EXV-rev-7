#!/usr/bin/env python3
"""Reinforced bucket ears (G = left, H = right).

The ears' upper part (hex ring + diagonal web) met the lower block (glued onto the bucket lug) only
at one corner: 0.4 mm of material across the 10 mm width, one or two layers when printed on the
side. Around that corner the merged EX-MA shells also left a small void, a notch and a slit, plus
two unused Ø3.7 holes of the removed link pins J/M (the bucket's matching holes are already filled).

Fix, added to the current ears (design frame, built pose):
  - a block on the outer side under the upper part, down to the lower block:
    u 339.77 .. 349.77 (the ear's full width), |v| 13.3 .. 24.93 (flush with the outer face),
    z 86.0 .. 92.2 - the joint goes from ~40 to ~145 mm2 and every printed layer (the ear prints
    on its side) now runs unbroken from the ring to the lower block;
  - the two old pin holes filled.
The inner diagonal stays: it is the clearance for the stick's lower corners.

Checks (printed): overlap with the bucket unchanged (ears and bucket are one rigid member), gap
from the new block to the bucket, and contact with the stick swept over the bucket's range.

Writes STL/2026-09-29-bucket-ear-{left,right}.stl and STEP/2026-09-29-bucket-ear-{left,right}.step
(the STEP through 2026-09-28-mesh-to-brep.py: exact planes and cylinders).
"""
import importlib.util
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
DATE = "2026-09-29"

FILL_U = (339.77, 349.77)          # ear width along u
FILL_V = (13.3, 24.93)             # |v|: lower block's inner step .. ear outer face
FILL_Z = (86.0, 92.2)              # above the bucket's top (z 83.75) .. into the upper part
OLD_PIN_HOLES = ((343.2, 89.9), (345.9, 84.9))   # (u, z) of the removed pins J/M, axis along v
HOLE_V = (10.43, 15.95)            # |v| span of the lower block
HOLE_PLUG_R = 1.95                 # hole Ø3.7 + margin
SWEEP = (-65.0, 95.0, 2.5)         # bucket angle range for the stick check (working -55 .. 85)


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


asm = _load("asm", "2026-09-24-assembly.py")
ex = asm.ex


def box(lo, hi):
    return mf.Manifold.cube(list(np.subtract(hi, lo))).translate(list(lo))


def cyl_v(u, z, v0, v1, r):
    """Cylinder along +v from v0 to v1 at (u, z)."""
    return mf.Manifold.cylinder(v1 - v0, r, r, 64).rotate([-90, 0, 0]).translate([u, v0, z])


def reinforce(name):
    sgn = 1 if name.endswith("left") else -1
    ear = ex.to_manifold(trimesh.load(OUT / "STL" / f"2026-09-24-{name}.stl"))
    v0, v1 = sorted((sgn * FILL_V[0], sgn * FILL_V[1]))
    add = box((FILL_U[0], v0, FILL_Z[0]), (FILL_U[1], v1, FILL_Z[1]))
    h0, h1 = sorted((sgn * HOLE_V[0], sgn * HOLE_V[1]))
    for u, z in OLD_PIN_HOLES:
        add = add + cyl_v(u, z, h0, h1, HOLE_PLUG_R)
    return ear + add, ear, add


def check(name, new, old, add, bucket, stick):
    rep = {}
    rep["volume"] = (round(old.volume(), 1), round(new.volume(), 1))
    tn = ex.from_manifold(new)
    rep["one watertight body"] = tn.is_watertight and len(tn.split(only_watertight=False)) == 1
    rep["bucket overlap mm3 (old, new)"] = (round((old ^ bucket).volume(), 2), round((new ^ bucket).volume(), 2))
    blk = ex.from_manifold(add)
    _, d, _ = trimesh.proximity.closest_point(ex.from_manifold(bucket), blk.sample(5000, seed=1))
    rep["added material to bucket, min gap mm"] = round(float(d.min()), 2)
    to = ex.from_manifold(old)
    worst = (0.0, None)
    for a in np.arange(*SWEEP):
        T = asm.pose_transform("bucket", bucket=math.radians(a))
        vo = (ex.to_manifold(to.copy().apply_transform(T)) ^ stick).volume()
        vn = (ex.to_manifold(tn.copy().apply_transform(T)) ^ stick).volume()
        if vn - vo > worst[0]:
            worst = (vn - vo, float(a))
    rep["extra stick contact over the sweep mm3 (at deg)"] = (round(worst[0], 3), worst[1])
    # joint cross-section just below the old corner
    for m, key in ((to, "old"), (tn, "new")):
        sec = m.section(plane_origin=[0, 0, 91.5], plane_normal=[0, 0, 1])
        area = sum(abs(trimesh.path.polygons.Polygon(e[:, :2]).area) for e in sec.discrete)
        rep[f"section at z 91.5 mm2 ({key})"] = round(area, 1)
    return rep


def main():
    bucket = ex.to_manifold(trimesh.load(OUT / "STL" / "2026-09-24-bucket.stl"))
    stick = ex.to_manifold(trimesh.util.concatenate([asm.part(n) for n in asm.MEMBERS["stick"]]))
    for name in ("bucket-ear-left", "bucket-ear-right"):
        new, old, add = reinforce(name)
        for k, v in check(name, new, old, add, bucket, stick).items():
            print(f"{name}: {k}: {v}", flush=True)
        stl = OUT / "STL" / f"{DATE}-{name}.stl"
        ex.from_manifold(new).export(stl)
        step = OUT / "STEP" / f"{DATE}-{name}.step"
        r = subprocess.run([sys.executable, str(HERE / "2026-09-28-mesh-to-brep.py"), str(stl), str(step)],
                           capture_output=True, text=True)
        print(f"{name}: wrote {stl.name}, {step.name}: {r.stdout.strip()[-400:] or r.stderr.strip()[-400:]}",
              flush=True)


if __name__ == "__main__":
    main()
