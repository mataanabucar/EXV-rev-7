#!/usr/bin/env python3
"""EX-MA full assembly: every part in one STEP file (built pose), shipped zipped.

Run:  <cadenv>/bin/python 2026-09-25-full-assembly.py [work_dir]
Contents:
  - new printed parts (their STEP B-reps, placed), wood panels, hardware        (as in the B6 assembly STEP)
  - the nine modified EX-MA parts as exact B-rep solids made from their STLs: coplanar triangles
    are merged into planar faces, the rest stay triangles, so the solids match the meshes exactly
  - the 8 ropes (Ø1.6) and 6 PTFE tubes (Ø4/Ø2) along the modelled paths (2026-09-24-cable-paths.py),
    built from mitred straight pieces within 0.05 mm of the path
Writes:
  STEP/2026-09-25-ex-ma-full-assembly.zip        (holds 2026-09-25-ex-ma-full-assembly.step, ~340 MB unzipped, ~64 MB zipped)
  Validation/2026-09-25-full-assembly-check.json
The unzipped STEP is written to work_dir (default: a temporary folder), never into the repo:
GitHub refuses files over 100 MB.
"""
import importlib.util
import json
import math
import sys
import tempfile
import time
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


pk = _load("pk", "2026-09-24-package.py")
cp = _load("cp", "2026-09-24-cable-paths.py")
asm, bx, ex = pk.asm, pk.bx, pk.ex
OUT = ex.OUT
NAME = "2026-09-25-ex-ma-full-assembly"

ROPE_D = 1.6                       # 1/16in 7x19
PTFE_OD, PTFE_ID = ex.PTFE_OD, 2.0
PATH_TOL = 0.05                    # mm: max deviation when thinning the path points for the ropes/tubes
PLANE_TOL = 1e-3                   # max vertex distance from a merged face's plane (else keep triangles)

HEX = lambda h: tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
COLORS = dict(pk.COLORS, exma_base=HEX("#2b2f35"), ear=HEX("#2f6db5"), ptfe=(0.97, 0.97, 0.97),
              boom=HEX("#2e9e44"), stick=HEX("#2a6fdb"), bucket=HEX("#d93a2b"), slew=HEX("#8e44ad"))
MESH_COLOR = {"tower": "exma_dark", "base": "exma_base", "bucket": "exma_base",
              "bucket-ear-left": "ear", "bucket-ear-right": "ear"}          # boom/stick halves: yellow


# ---------------------------------------------------------------- mesh -> exact B-rep
def _loops(edges):
    """Closed vertex loops from a facet's boundary edges; None if any vertex is not simple."""
    adj = defaultdict(list)
    for a, b in edges:
        adj[int(a)].append(int(b))
        adj[int(b)].append(int(a))
    if any(len(v) != 2 or v[0] == v[1] for v in adj.values()):
        return None
    seen, loops = set(), []
    for s in adj:
        if s in seen:
            continue
        loop, prev, cur = [s], None, s
        seen.add(s)
        while True:
            a, b = adj[cur]
            nxt = a if a != prev else b
            if nxt == s:
                break
            loop.append(nxt)
            seen.add(nxt)
            prev, cur = cur, nxt
        loops.append(loop)
    return loops


def mesh_to_brep(mesh):
    """Watertight trimesh -> OCC solid. Returns (solid, stats)."""
    from OCP.gp import gp_Pnt, gp_Pln, gp_Dir
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace,
                                    BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid)
    from OCP.ShapeFix import ShapeFix_Face, ShapeFix_Solid, ShapeFix_Shape
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopoDS import TopoDS
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    V = mesh.vertices
    P = [gp_Pnt(*map(float, v)) for v in V]

    def wire(loop):
        mp = BRepBuilderAPI_MakePolygon()
        for i in loop:
            mp.Add(P[i])
        mp.Close()
        return mp.Wire()

    faces, used = [], np.zeros(len(mesh.faces), bool)
    n_merged = 0
    for fi, (grp, bnd) in enumerate(zip(mesh.facets, mesh.facets_boundary)):
        n, o = mesh.facets_normal[fi], mesh.facets_origin[fi]
        verts = np.unique(mesh.faces[grp])
        if np.abs((V[verts] - o) @ n).max() > PLANE_TOL:
            continue
        loops = _loops(bnd)
        if not loops:
            continue
        # outer loop = largest area in the facet plane
        ax = np.eye(3)[np.argmin(np.abs(n))]
        e1 = np.cross(n, ax); e1 /= np.linalg.norm(e1)
        e2 = np.cross(n, e1)

        def area(lp):
            q = (V[lp] - o) @ np.column_stack((e1, e2))
            return abs(0.5 * np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1]))
        loops.sort(key=area, reverse=True)
        mf = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(*map(float, o)), gp_Dir(*map(float, n))), wire(loops[0]), True)
        for h in loops[1:]:
            mf.Add(wire(h))
        if not mf.IsDone():
            continue
        sf = ShapeFix_Face(mf.Face())
        sf.Perform()
        face = sf.Face()
        # keep the merged face only if it is valid and covers exactly its triangles; else keep triangles
        g = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, g)
        if not BRepCheck_Analyzer(face).IsValid() or abs(g.Mass() - mesh.area_faces[grp].sum()) > 1e-6 * max(g.Mass(), 1.0):
            continue
        faces.append(face)
        used[grp] = True
        n_merged += 1
    for f in np.nonzero(~used)[0]:
        a, b, c = mesh.faces[f]
        faces.append(BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakePolygon(P[a], P[b], P[c], True).Wire(), True).Face())
    sew = BRepBuilderAPI_Sewing(PLANE_TOL)
    for f in faces:
        sew.Add(f)
    sew.Perform()
    exp = TopExp_Explorer(sew.SewedShape(), TopAbs_SHELL)
    mk = BRepBuilderAPI_MakeSolid()
    n_shell = 0
    while exp.More():
        mk.Add(TopoDS.Shell_s(exp.Current()))
        n_shell += 1
        exp.Next()
    fix = ShapeFix_Solid(mk.Solid())
    fix.Perform()
    fix = ShapeFix_Shape(fix.Solid())          # removes zero-area sliver triangles left in some meshes
    fix.Perform()
    return fix.Shape(), dict(triangles=len(mesh.faces), faces=len(faces), merged_planar_faces=n_merged, shells=n_shell)


def check_solid(shape, volume_ref):
    import cadquery as cq
    s = cq.Shape.cast(shape)
    vol = s.Volume()
    return dict(valid=bool(s.isValid()), volume=round(vol, 1), volume_error_pct=round(100 * abs(vol - volume_ref) / volume_ref, 4))


def mesh_part(name):
    import cadquery as cq
    m = asm.part(name)
    t = time.time()
    shape, st = mesh_to_brep(m)
    st.update(check_solid(shape, m.volume))
    if not (st["valid"] and st["volume_error_pct"] < 0.1 and st["shells"] == 1):
        s2 = pk.stl_to_solid(pk.STL / f"2026-09-24-{name}.stl")        # plain triangle sewing
        st2 = check_solid(s2.wrapped, m.volume)
        st.update(fallback="triangle sewing", **st2, faces=st["triangles"])
        shape = s2.wrapped
    st["seconds"] = round(time.time() - t, 1)
    return cq.Shape.cast(shape), st


# ---------------------------------------------------------------- ropes and PTFE tubes
def _simplify(pts, tol=PATH_TOL):
    """Douglas-Peucker: drop path points that lie within tol of the chord (the paths are dense)."""
    pts = np.asarray(pts, float)
    pts = pts[np.r_[True, np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-6]]

    def dp(a, b):
        if b <= a + 1:
            return [a]
        u = (pts[b] - pts[a]) / np.linalg.norm(pts[b] - pts[a])
        d = pts[a + 1:b] - pts[a]
        dist = np.linalg.norm(d - np.outer(d @ u, u), axis=1)
        i = int(np.argmax(dist))
        if dist[i] > tol:
            return dp(a, a + 1 + i) + dp(a + 1 + i, b)
        return [a]
    return pts[dp(0, len(pts) - 1) + [len(pts) - 1]]


def _halfspace(p, n):
    """Half-space solid on the side the normal n points to."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    f = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(*map(float, p)), gp_Dir(*map(float, n)))).Face()
    return BRepPrimAPI_MakeHalfSpace(f, gp_Pnt(*map(float, p + n))).Solid()


def swept_tube(pts, r_out, r_in=None):
    """Rope (r_in None) or PTFE tube along a path: one straight cylinder per path segment, mitred on
    the plane bisecting each bend so neighbours meet face to face, then fused into one solid.
    (OCC pipe sweeps along these long winding paths failed or gave wrong volumes.)"""
    import cadquery as cq
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    V = cq.Vector
    q = _simplify(pts)
    U = [(q[i + 1] - q[i]) / np.linalg.norm(q[i + 1] - q[i]) for i in range(len(q) - 1)]
    parts = []
    for i, u in enumerate(U):
        a, b = q[i], q[i + 1]
        n0 = u if i == 0 else (U[i - 1] + u) / np.linalg.norm(U[i - 1] + u)
        n1 = u if i == len(U) - 1 else (u + U[i + 1]) / np.linalg.norm(u + U[i + 1])
        ext = 2 * r_out + 1.0
        c = cq.Solid.makeCylinder(r_out, float(np.linalg.norm(b - a)) + 2 * ext, V(*map(float, a - u * ext)), V(*map(float, u)))
        if r_in:
            c = c.cut(cq.Solid.makeCylinder(r_in, float(np.linalg.norm(b - a)) + 4 * ext, V(*map(float, a - 2 * u * ext)),
                                            V(*map(float, u))))
        piece = BRepAlgoAPI_Common(BRepAlgoAPI_Common(c.wrapped, _halfspace(a, n0)).Shape(), _halfspace(b, -n1)).Shape()
        parts.append(cq.Shape.cast(piece))
    s = parts[0].fuse(*parts[1:]).clean()
    length = float(np.linalg.norm(np.diff(q, axis=0), axis=1).sum())
    area = math.pi * (r_out ** 2 - (r_in or 0) ** 2)
    return s, dict(length=round(length, 1), segments=len(U), valid=bool(s.isValid()), solids=len(s.Solids()),
                   volume_error_pct=round(100 * abs(s.Volume() - area * length) / (area * length), 3))


# ---------------------------------------------------------------- assembly
def build():
    import cadquery as cq
    assy = cq.Assembly(name="EX-MA-full")
    col = lambda k: cq.Color(*COLORS[k])
    items = defaultdict(int)
    for name, T in asm.placements().items():
        base = name.split("@")[0]
        shp = pk.placed(cq.importers.importStep(str(pk.STEP / f"2026-09-24-{base}.step")).val(), T)
        assy.add(shp, name=name.replace("@", "-"), color=col("printed"))
        items["printed parts (new)"] += 1
    mesh_stats = {}
    for name in asm.MODIFIED:
        shp, st = mesh_part(name)
        mesh_stats[name] = st
        print(f"  {name}: {st}", flush=True)
        assy.add(shp, name=f"EX-MA-{name}", color=col(MESH_COLOR.get(name, "exma_yellow")))
        items["modified EX-MA parts"] += 1
    for p in bx.panels():
        assy.add(bx.panel_solid(p).val(), name=p.name.replace(" ", "-").replace("(", "").replace(")", ""),
                 color=col("wood" if p.group == "control-box" else "ply"))
        items["wood panels"] += 1
    for name, (shp, c) in pk.hardware_solids().items():
        assy.add(shp, name=name.replace(" ", "-").replace("/", "_"), color=col(c))
        items["hardware"] += 1
    cable_stats = {}
    for rope, e in cp.all_paths().items():
        shp, st = swept_tube(cp.polyline(e), ROPE_D / 2)
        cable_stats[f"rope {rope}"] = st
        assy.add(shp, name=f"rope-{rope.replace(' ', '-')}", color=col(e["circuit"]))
        items["ropes"] += 1
        for k, seg in enumerate(e["ptfe"]):
            shp, st = swept_tube(seg, PTFE_OD / 2, PTFE_ID / 2)
            cable_stats[f"PTFE {rope} {k + 1}"] = st
            assy.add(shp, name=f"PTFE-{rope.replace(' ', '-')}-{k + 1}", color=col("ptfe"))
            items["PTFE tubes"] += 1
    return assy, dict(items), mesh_stats, cable_stats


def count_solids(path):
    pat, n, tail = b"MANIFOLD_SOLID_BREP(", 0, b""
    with open(path, "rb") as f:
        while chunk := f.read(1 << 24):
            buf = tail + chunk
            n += buf.count(pat)
            tail = buf[-(len(pat) - 1):]     # too short to hold a whole match: nothing counted twice
    return n


def reimport(path):
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SOLID
    r = STEPControl_Reader()
    ok = r.ReadFile(str(path))
    r.TransferRoots()
    exp, n = TopExp_Explorer(r.OneShape(), TopAbs_SOLID), 0
    while exp.More():
        n += 1
        exp.Next()
    return int(ok), n


def main():
    work = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    work.mkdir(parents=True, exist_ok=True)
    step = work / f"{NAME}.step"
    t = time.time()
    assy, items, mesh_stats, cable_stats = build()
    print("items:", items, f"({time.time() - t:.0f} s)", flush=True)
    assy.export(str(step))
    print(f"STEP written: {step.stat().st_size / 1e6:.0f} MB ({time.time() - t:.0f} s)", flush=True)
    n_text = count_solids(step)
    status, n_back = reimport(step)
    print(f"solids in file {n_text}, on re-import {n_back} ({time.time() - t:.0f} s)", flush=True)
    z = pk.STEP / f"{NAME}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(step, arcname=step.name)
    n_items = sum(items.values())
    check = dict(file=f"STEP/{z.name}", contains=step.name, items=items, n_items=n_items,
                 solids_in_file=n_text, solids_on_reimport=n_back, reimport_status=status,
                 step_mb=round(step.stat().st_size / 1e6, 1), zip_mb=round(z.stat().st_size / 1e6, 1),
                 mesh_parts=mesh_stats, cables=cable_stats)
    (OUT / "Validation" / "2026-09-25-full-assembly-check.json").write_text(json.dumps(check, indent=1))
    print(json.dumps({k: v for k, v in check.items() if k not in ("mesh_parts", "cables")}, indent=1))


if __name__ == "__main__":
    main()
