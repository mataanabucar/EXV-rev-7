#!/usr/bin/env python3
"""Bucket ears (G = left, H = right) rebuilt as native CAD solids, reinforced.

The ears came from the original EX-MA mesh, which is full of hidden defects: a crack at the joint
between the ring part and the lower block, the hollow of a filled clip recess, slits in the lower
block, a 0.14 mm step on its underside and two leftover pin holes. Patching the mesh left some of
them (2026-09-29-reinforce-bucket-ears.py). This builds each ear from its measured design shape,
so there are none:

  - body: one side profile (v, z) extruded across the ear's width, u 339.77 .. 349.77
      lower block      v 10.43 .. 15.93, z 81.89 .. 91.89 (glued onto the bucket lug)
      reinforcement    v 15.93 .. 24.93, z 86.0 .. 91.89 (solid joint, as in the patched version)
      upper block      v 18.93 .. 24.93 up to the ring
      diagonal         (12.93, 91.89) -> (19.93, 97.89) -> (19.6, 99.89) -> v 18.93: the clearance
                       for the stick's lower corners, unchanged
  - ring: Ø19.97 disc on the bucket pin axis, v 18.93 .. 24.93, with the hex socket for the bucket
    drum-axle (AF 12.3 = axle hex 12.0 + 0.3, same phase as before)
  - bottom: Ø6 disc (v 12.93 .. 15.93) and the Ø3.8 pin into the bucket (v 12.93 .. 21.43)
  - the old pin J/M holes and the clip recess are solid.

The right ear is the mirror of the left about the arm's split plane v = -0.07 (as the originals).

Checks: bucket overlap and stick contact over the bucket sweep, against the original ears.
Writes STL/ and STEP/ 2026-09-29-bucket-ear-{left,right}-cad (design frame, built pose).
"""
import importlib.util
import math
from pathlib import Path

import numpy as np
import trimesh
import cadquery as cq

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
DATE = "2026-09-29"
V = cq.Vector


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


asm = _load("asm", "2026-09-24-assembly.py")
ex, rt = asm.ex, asm.rt
bp = _load("parts", "2026-09-24-build-parts.py")

U = (339.77, 349.77)                              # ear width along u
PROFILE = [(10.43, 81.89), (15.93, 81.89), (15.93, 86.0), (24.93, 86.0), (24.93, 109.89),
           (18.93, 109.89), (18.93, 99.89), (19.6, 99.89), (19.93, 97.89), (12.93, 91.89),
           (10.43, 91.89)]                         # left ear, (v, z)
RING_C, RING_R, RING_V = (344.765, 109.89), 9.985, (18.93, 24.93)
HEX_AF = bp.AXLE_HEX_AF + 0.3
DISC_C, DISC_R, DISC_V = (344.77, 79.89), 3.0, (12.931, 15.931)
PIN_R, PIN_V = 1.9, (12.931, 21.431)
MIRROR_V = -0.07                                  # right ear = left mirrored about v = -0.07
SWEEP = (-65.0, 95.0, 2.5)                        # bucket range for the stick check (working -55 .. 85)


def v_cyl(c, r, v0, v1):
    return cq.Solid.makeCylinder(r, v1 - v0, V(c[0], v0, c[1]), V(0, 1, 0))


def left_ear():
    face = cq.Face.makeFromWires(cq.Wire.makePolygon([V(U[0], v, z) for v, z in PROFILE], close=True))
    body = cq.Solid.extrudeLinear(face, V(U[1] - U[0], 0, 0))
    body = body.fuse(v_cyl(RING_C, RING_R, *RING_V))
    body = body.fuse(v_cyl(DISC_C, DISC_R, *DISC_V)).fuse(v_cyl(DISC_C, PIN_R, *PIN_V))
    # hex socket: same orientation as the drum-axle hex (print-frame X at stick angle - 90 deg)
    px, pz = ex.P_BUCKET
    phase = math.radians((math.degrees(rt.STICK_ANG) - 90.0) % 60.0)
    R = HEX_AF / 2 / math.cos(math.pi / 6)
    hexpts = [V(px + R * math.cos(phase + k * math.pi / 3), RING_V[0] - 1, pz + R * math.sin(phase + k * math.pi / 3))
              for k in range(6)]
    hexp = cq.Solid.extrudeLinear(cq.Face.makeFromWires(cq.Wire.makePolygon(hexpts, close=True)),
                                  V(0, RING_V[1] - RING_V[0] + 2, 0))
    return body.cut(hexp).clean()


def right_ear(left):
    return left.mirror("XZ", V(0, MIRROR_V, 0))


def to_mesh(shape):
    vs, ts = shape.tessellate(0.005, 0.05)
    return trimesh.Trimesh(np.array([(p.x, p.y, p.z) for p in vs]), np.array(ts), process=True)


def check(name, new_shape, bucket, stick):
    import manifold3d as mf
    M = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32),
                                      tri_verts=np.asarray(t.faces, np.uint32)))
    tn = to_mesh(new_shape)
    to = trimesh.load(OUT / "STL" / f"2026-09-24-{name}.stl")
    mn, mo = M(tn), M(to)
    rep = {"volume (old, new)": (round(to.volume, 1), round(tn.volume, 1)),
           "bucket overlap mm3 (old, new)": (round((mo ^ bucket).volume(), 2), round((mn ^ bucket).volume(), 2)),
           "removed vs old mm3": round((mo - mn).volume(), 2), "added vs old mm3": round((mn - mo).volume(), 2)}
    worst = (0.0, None)
    for a in np.arange(*SWEEP):
        T = asm.pose_transform("bucket", bucket=math.radians(a))
        vo = (M(to.copy().apply_transform(T)) ^ stick).volume()
        vn = (M(tn.copy().apply_transform(T)) ^ stick).volume()
        if vn - vo > worst[0]:
            worst = (vn - vo, float(a))
    rep["extra stick contact over the sweep mm3 (at deg)"] = (round(worst[0], 3), worst[1])
    sec = tn.section(plane_origin=[0, 0, 91.5], plane_normal=[0, 0, 1])
    rep["joint section at z 91.5 mm2"] = round(sum(abs(trimesh.path.polygons.Polygon(e[:, :2]).area)
                                                 for e in sec.discrete), 1)
    return rep


def main():
    import manifold3d as mf
    M = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32),
                                      tri_verts=np.asarray(t.faces, np.uint32)))
    bucket = M(trimesh.load(OUT / "STL" / "2026-09-24-bucket.stl"))
    stick = M(trimesh.util.concatenate([asm.part(n) for n in asm.MEMBERS["stick"]]))
    left = left_ear()
    for name, s in (("bucket-ear-left", left), ("bucket-ear-right", right_ear(left))):
        faces = {}
        for f in s.Faces():
            faces[f.geomType()] = faces.get(f.geomType(), 0) + 1
        step = OUT / "STEP" / f"{DATE}-{name}-cad.step"
        stl = OUT / "STL" / f"{DATE}-{name}-cad.stl"
        cq.exporters.export(s, str(step))
        cq.exporters.export(s, str(stl), tolerance=0.005, angularTolerance=0.05)
        back = cq.importers.importStep(str(step)).solids().vals()
        m = trimesh.load(stl)
        print(f"{name}: valid {s.isValid()}, faces {faces}; STEP read back {len(back)} solid, valid "
              f"{all(b.isValid() for b in back)}; STL watertight {m.is_watertight}, bodies "
              f"{len(m.split(only_watertight=False))}", flush=True)
        for k, v in check(name, s, bucket, stick).items():
            print(f"   {k}: {v}", flush=True)


if __name__ == "__main__":
    main()
