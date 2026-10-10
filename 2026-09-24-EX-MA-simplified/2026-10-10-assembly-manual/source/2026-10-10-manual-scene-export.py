#!/usr/bin/env python3
"""Scene export for the assembly-manual illustrations.

Every object comes from the project's own geometry, in the built pose (design frame, mm):
  - printed parts: STL/ files placed by Source/2026-09-24-assembly.py (current base and bucket
    ears: STL/2026-09-29-base.stl, STL/2026-09-29-bucket-ear-{left,right}-cad.stl)
  - lever knobs: STL/2026-09-24-lever-knob.stl on top of each handle rod
  - plywood panels: Source/2026-09-24-build-box.py panels() (holes and slots cut)
  - fasteners, pins, rods, nuts, washers, wood screws: Source/2026-09-28-solid-hardware.py
  - PEX, copper, PVC: Source/2026-09-24-build-box.py hardware(); 6 mm BBs on the ball circle
  - ropes and PTFE tubes: Source/2026-09-24-cable-paths.py all_paths() (polylines)

Writes <out>/scene.json (object list with name, group, member, colour key, bbox and byte offsets)
and <out>/scene.bin (float32 vertex positions + uint32 triangle indices per object).

Usage: <cadenv>/bin/python 2026-10-10-manual-scene-export.py <out_dir>
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]                       # 2026-09-24-EX-MA-simplified
SRC = PROJ / "Source"
STL = PROJ / "STL"


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, SRC / fn)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


asm = _load("asm", "2026-09-24-assembly.py")
bx = _load("bx", "2026-09-24-build-box.py")
ex = asm.ex

# current printed files (the 2026-09-29 rebuilds replace the original base and ears)
CURRENT_STL = {
    "base": STL / "2026-09-29-base.stl",
    "bucket-ear-left": STL / "2026-09-29-bucket-ear-left-cad.stl",
    "bucket-ear-right": STL / "2026-09-29-bucket-ear-right-cad.stl",
}

PRINTED = {   # name -> (group, member, colour key)
    "base": ("turret", "fixed", "exma_dark"),
    "slewing-ring-retaining-ring": ("turret", "fixed", "printed"),
    "tower": ("turret", "turret", "exma"),
    "boom-half-left": ("arm", "boom", "petg"), "boom-half-right": ("arm", "boom", "petg"),
    "boom-drum": ("arm", "boom", "printed"),
    "stick-half-left": ("arm", "stick", "petg"), "stick-half-right": ("arm", "stick", "petg"),
    "stick-drum": ("arm", "stick", "printed"),
    "bucket": ("arm", "bucket", "exma_dark"),
    "bucket-ear-left": ("arm", "bucket", "ear"), "bucket-ear-right": ("arm", "bucket", "ear"),
    "bucket-drum-axle": ("arm", "bucket", "printed"),
    "slew-drum": ("pedestal", "turret", "printed"),
    "conduit-end-fitting-pedestal": ("pedestal", "fixed", "printed"),
    "slew-tube-bushing": ("pedestal", "fixed", "printed"),
    "elbow-support": ("pedestal", "fixed", "printed"),
    "conduit-end-fitting-box": ("box", "fixed", "printed"),
    "lever-hub-boom": ("box", "lever-boom", "printed"),
    "lever-hub-stick": ("box", "lever-stick", "printed"),
    "lever-hub-bucket": ("box", "lever-bucket", "printed"),
    "slew-spool": ("box", "wheel", "printed"),
    "slew-wheel": ("box", "wheel", "printed"),
    "spool-riser": ("box", "fixed", "printed"),
    "slew-tube-post@A": ("box", "fixed", "printed"),
    "slew-tube-post@B": ("box", "fixed", "printed"),
}


def printed_mesh(name):
    if name in CURRENT_STL:
        return trimesh.load(CURRENT_STL[name], force="mesh")
    return asm.part(name)


def knob_meshes():
    """Printed lever knob (print frame: bottom on z 0, bore up from the bottom) on each handle:
    the 5/16in rod top is at AXLE_Z + HANDLE_LEN + KNOB_BORE_DEPTH, the knob bottom at
    AXLE_Z + HANDLE_LEN (Source/2026-09-24-build-box.py lever_handle_mesh)."""
    out = {}
    k = trimesh.load(STL / "2026-09-24-lever-knob.stl", force="mesh")
    for j, (vh, _) in ex.LEVERS.items():
        m = k.copy()
        m.apply_translation((ex.AXLE_U, vh, ex.AXLE_Z + ex.HANDLE_LEN))
        out[f"lever-knob@{j}"] = m
    return out


def shape_mesh(shape, tol=0.05, ang=0.3):
    vs, ts = shape.tessellate(tol, ang)
    return trimesh.Trimesh(np.array([(p.x, p.y, p.z) for p in vs]), np.array(ts), process=False)


def hw_member(name):
    """Which moving member a hardware item rides with (for posed / exploded figures)."""
    n = name.lower()
    if "boom drum key" in n or "boom joining lug" in n:
        return "boom"
    if "stick drum key" in n or "stick joining lug" in n or "stick split pin" in n:
        return "boom" if "split pin" in n else "stick"
    if "boom split pin" in n or "turret hub" in n:
        return "turret"
    if "bucket pin" in n:
        return "bucket"
    if "slew drum pex" in n:
        return "turret"
    for j in ("boom", "stick", "bucket"):
        if f"{j} lever" in n:
            return f"lever-{j}"
    if "slew spool" in n or "slew wheel" in n or "spool axle top" in n:
        return "wheel"
    return "fixed"


def hw_group(name):
    n = name.lower()
    if any(k in n for k in ("drum key", "joining lug", "split pin", "bucket pin")):
        return "arm_hw"
    if "retaining ring" in n or "turret hub" in n or "base to pedestal" in n:
        return "turret_hw"
    if any(k in n for k in ("pedestal", "slew drum pex", "pex bushing", "elbow support")):
        return "pedestal_hw"
    if "sandbox" in n and "box" in n and "to sandbox" in n:
        return "box_hw"
    if any(k in n for k in ("sandbox floor", "sandbox wall")):
        return "sandbox_hw"
    return "box_hw"


def hardware():
    """(name, group, member, colour, mesh) for every fastener / rod / nut / washer / wood screw."""
    H = _load("solid_hw", "2026-09-28-solid-hardware.py")
    meshes = {n: printed_mesh(n) for n in ("tower", "boom-half-left", "boom-half-right",
                                           "bucket-ear-left", "bucket-ear-right")}
    items = H.m3_items() + H.pin_items(meshes) + H.rod516_items() + H.wood_items()
    out = []
    for grp, name, shape, col in items:
        n = name.lower()
        g = hw_group(name)
        if "wood screw" in n and ("to box" in n or "box floor" in n or "box top" in n or "box front" in n
                                  or "box rear" in n or "bearing block" in n or "spool riser" in n
                                  or "sleeve post" in n):
            g = "box_hw"
        if "wood screw" in n and "pedestal" in n:
            g = "pedestal_hw"
        if "wood screw" in n and "sandbox" in n:
            g = "sandbox_hw"
        if "pex bushing" in n or "elbow support" in n:
            g = "pedestal_hw"
        if "handle" in n and "5/16in rod" in n:
            g = "box_hw"
        out.append((name, g, hw_member(name), "zinc" if col == "zinc" else "steel", shape_mesh(shape)))
    return out


def stock():
    out = []
    H = bx.hardware()
    for n, (m, c) in H.items():
        if "handle" in n or "rod" in n:
            continue                                   # rods come from the solid hardware list
        g = "pedestal" if ("PEX" in n or "copper" in n) else "conduit"
        member = "turret" if "PEX" in n else "fixed"
        out.append((n, g, member, c, m))
    n_b = int(2 * math.pi * ex.BALL_CIRCLE_R // (ex.BALL_D + 0.4))
    balls = []
    for k in range(n_b):
        t = 2 * math.pi * k / n_b
        s_ = trimesh.creation.icosphere(subdivisions=2, radius=ex.BALL_D / 2)
        s_.apply_translation((ex.BALL_CIRCLE_R * math.cos(t), ex.BALL_CIRCLE_R * math.sin(t), ex.BALL_Z))
        balls.append(s_)
    out.append((f"{n_b} x 6 mm BBs", "turret", "fixed", "bb", trimesh.util.concatenate(balls)))
    return out


def panels():
    out = []
    for p in bx.panels():
        m = shape_mesh(bx.panel_solid(p).val(), tol=0.2, ang=0.3)
        g = {"control-box": "box_wood", "pedestal": "pedestal_wood", "sandbox": "sandbox_wood"}[p.group]
        out.append((p.name, g, "fixed", "ply_box" if p.group == "control-box" else "ply", m))
    return out


def ropes():
    cp = _load("cp", "2026-09-24-cable-paths.py")
    R = []
    for n, e in cp.all_paths().items():
        R.append(dict(name=n, circuit=e["circuit"], pts=np.round(cp.polyline(e), 3).tolist(),
                      ptfe=[np.round(np.asarray(s), 3).tolist() for s in e["ptfe"]]))
    return R


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    objs = []
    for n, (g, mem, col) in PRINTED.items():
        objs.append((n, g, mem, col, printed_mesh(n), "printed"))
    for n, m in knob_meshes().items():
        objs.append((n, "box", f"lever-{n.split('@')[1]}", "knob", m, "printed"))
    for n, g, mem, col, m in panels():
        objs.append((n, g, mem, col, m, "wood"))
    for n, g, mem, col, m in stock():
        objs.append((n, g, mem, col, m, "stock"))
    print(f"{len(objs)} parts / panels / stock; building hardware ...", flush=True)
    for n, g, mem, col, m in hardware():
        objs.append((n, g, mem, col, m, "hardware"))
    meta, off = [], 0
    with open(out / "scene.bin", "wb") as f:
        for n, g, mem, col, m, kind in objs:
            v = np.asarray(m.vertices, np.float32)
            t = np.asarray(m.faces, np.uint32)
            f.write(v.tobytes())
            f.write(t.tobytes())
            meta.append(dict(name=n, group=g, member=mem, color=col, kind=kind,
                             bbox=[np.round(m.bounds[0], 2).tolist(), np.round(m.bounds[1], 2).tolist()],
                             v_off=off, v_n=int(len(v)), t_off=off + v.nbytes, t_n=int(len(t))))
            off += v.nbytes + t.nbytes
    pose = dict(P_BOOM=ex.P_BOOM, P_STICK=ex.P_STICK, P_BUCKET=ex.P_BUCKET, AXLE=(ex.AXLE_U, ex.AXLE_Z),
                WHEEL_C=ex.WHEEL_C)
    (out / "scene.json").write_text(json.dumps(dict(objects=meta, ropes=ropes(), pose=pose,
                                                    rope_d=ex.ROPE_D, ptfe_od=4.0)))
    print(f"wrote {len(meta)} objects, {off / 1e6:.1f} MB -> {out}", flush=True)


if __name__ == "__main__":
    main()
