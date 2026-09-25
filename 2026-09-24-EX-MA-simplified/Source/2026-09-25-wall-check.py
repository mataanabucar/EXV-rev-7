#!/usr/bin/env python3
"""Wall-thickness check of every printed STL for a 0.6 mm nozzle, in its print orientation.

Run:  <cadenv>/bin/python 2026-09-25-wall-check.py [--dir STL_DIR] [part ...]
Method: turn the part into the print orientation chosen by 2026-09-24-package.py, sample the
surface evenly, cast a ray inward along each sample's normal and keep the first hit when it lands
on an opposing face (normals within ~37 deg of anti-parallel): that distance is the wall
thickness. What the nozzle has to lay down is the width of that wall inside one layer, i.e. the
thickness divided by the horizontal part of the normal; near-horizontal faces (|n_z| > 0.9) are
tops and bottoms of layers, not walls, and are skipped. Thin samples within 2 mm of each other
form a region.
Pass rule (0.6 mm nozzle):
  - no patch of >= MIN_AREA mm2 thinner than HARD_MIN (1.0 mm: two lines; thinner walls do not print)
  - smaller thin slivers (seam alignment sockets, wedge tips where cuts meet ribs) are listed only:
    they are attached to solid material, so the slicer drops them or prints one line
  - patches between HARD_MIN and TARGET (1.8 mm = 3 lines) are listed for information
Writes Validation/2026-09-25-wall-check.json (all parts only).
"""
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import trimesh
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

OUT = Path(__file__).resolve().parent.parent
STL = OUT / "STL"
HARD_MIN, TARGET, MIN_AREA, LIST_AREA = 1.0, 1.8, 20.0, 3.0
MAX_SAMPLES, BATCH = 60000, 4000


def thickness(mesh, in_layer=False):
    n = min(MAX_SAMPLES, int(mesh.area * 1.5) + 1000)
    pts, fi = trimesh.sample.sample_surface_even(mesh, n, seed=1)
    nrm = mesh.face_normals[fi]
    org = pts - nrm * 1e-3
    th = np.full(len(pts), np.inf)
    for k in range(0, len(org), BATCH):
        loc, ri, ti = mesh.ray.intersects_location(org[k:k + BATCH], -nrm[k:k + BATCH], multiple_hits=False)
        opp = (mesh.face_normals[ti] * nrm[k + ri]).sum(1) < -0.8
        th[k + ri[opp]] = np.linalg.norm(loc[opp] - org[k + ri[opp]], axis=1)
    if in_layer:
        horiz = np.sqrt(np.clip(1.0 - nrm[:, 2] ** 2, 0.0, 1.0))
        th = np.where(np.abs(nrm[:, 2]) > 0.9, np.inf, th / np.maximum(horiz, 1e-6))
    return pts, th, mesh.area / len(pts)


def regions(pts, th, per, limit, min_area=LIST_AREA):
    idx = np.nonzero(th < limit)[0]
    if not len(idx):
        return []
    pairs = cKDTree(pts[idx]).query_pairs(2.0, output_type="ndarray")
    A = sp.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(idx), len(idx)))
    _, lab = connected_components(A, directed=False)
    out = []
    for c in np.unique(lab):
        g = idx[lab == c]
        if len(g) * per < min_area:
            continue
        out.append(dict(area_mm2=round(float(len(g) * per), 1), min_t=round(float(th[g].min()), 2),
                        median_t=round(float(np.median(th[g])), 2), center=pts[g].mean(0).round(1).tolist(),
                        lo=pts[g].min(0).round(1).tolist(), hi=pts[g].max(0).round(1).tolist()))
    return sorted(out, key=lambda r: -r["area_mm2"])


def _package():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pk", Path(__file__).resolve().parent / "2026-09-24-package.py")
    pk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pk)
    return pk


PK = None


def check(name, stl_dir=STL):
    global PK
    PK = PK or _package()
    m = trimesh.load(stl_dir / f"2026-09-24-{name}.stl", force="mesh")
    m, orient_label, _, _ = PK.orient(m, name)
    pts, th, per = thickness(m, in_layer=True)
    thin = regions(pts, th, per, HARD_MIN)
    hard = [r for r in thin if r["area_mm2"] >= MIN_AREA]
    slivers = [r for r in thin if r["area_mm2"] < MIN_AREA]
    soft = [r for r in regions(pts, th, per, TARGET) if r["min_t"] >= HARD_MIN]
    fin = th[np.isfinite(th)]
    return dict(part=name, print_orientation=PK.ORIENT_TEXT.get(orient_label, orient_label),
                samples=len(pts), p1_mm=round(float(np.percentile(fin, 1)), 2),
                thin_patches=hard, small_slivers=slivers, between_1_0_and_1_8=soft, ok=not hard)


def main():
    args = sys.argv[1:]
    stl_dir = STL
    if args[:1] == ["--dir"]:
        stl_dir, args = Path(args[1]), args[2:]
    names = args or sorted(p.stem.replace("2026-09-24-", "") for p in stl_dir.glob("2026-09-24-*.stl"))
    res = []
    for n in names:
        r = check(n, stl_dir)
        res.append(r)
        print(f"{n:32s} {'ok  ' if r['ok'] else 'FAIL'} thin patches: {len(r['thin_patches'])}; "
              f"small slivers: {len(r['small_slivers'])} ({sum(x['area_mm2'] for x in r['small_slivers']):.0f} mm2); "
              f"1.0-1.8 mm: {len(r['between_1_0_and_1_8'])}", flush=True)
        for h in r["thin_patches"]:
            print("      ", h, flush=True)
    if not sys.argv[1:]:                  # full run on STL/: record it
        (OUT / "Validation" / "2026-09-25-wall-check.json").write_text(json.dumps(dict(
            nozzle_mm=0.6, hard_min_mm=HARD_MIN, target_mm=TARGET, fail_area_mm2=MIN_AREA, list_area_mm2=LIST_AREA,
            parts=res, all_ok=all(r["ok"] for r in res)), indent=1))
    print("all ok:", all(r["ok"] for r in res))


if __name__ == "__main__":
    main()
