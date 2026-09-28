"""EX-MA full assembly as real solid bodies (STEP AP214), zipped.

    python 2026-09-28-solid-assembly.py [--work DIR]

 1. EX-MA parts that only exist as meshes become exact B-rep solids:
      tower, base, bucket, bucket ears   STL -> 2026-09-28-mesh-to-brep.py
      boom / stick halves                original halves converted, then every build modification
                                         redone as CAD booleans (2026-09-28-arm-halves-cad.py)
    each conversion runs in its own process (an OpenCascade crash cannot take the build down)
 2. printed parts from their STEP files at their assembly placements, plywood panels as boxes,
    and every hardware item as a solid (2026-09-28-solid-hardware.py)
 3. one component per part, one solid body each, grouped and coloured; the whole assembly is moved
    so the floor bottom sits on Z = 0 and the footprint is centred on X / Y = 0 (Z up)
 4. the STEP is read back and checked (one valid solid per component, no triangle soup), and
    STEP/2026-09-28-ex-ma-solid-assembly.zip is written with the assembly, the converted EX-MA
    parts on their own, and a README with the checks
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import trimesh
import cadquery as cq

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
STL_DIR = ROOT / "STL"
STEP_DIR = ROOT / "STEP"
ZIP_PATH = STEP_DIR / "2026-09-28-ex-ma-solid-assembly.zip"
ASSEMBLY_NAME = "2026-09-28-ex-ma-solid-assembly.step"


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, SRC / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


H = _load("solid_hardware", "2026-09-28-solid-hardware.py")
ex, asm, bx = H.ex, H.asm, H.bx

# footprint centred on X / Y = 0, floor bottom (box / sandbox floor underside) on Z = 0
SHIFT = np.array([-(ex.BOX_U[0] + ex.SB_U[1]) / 2,
                  -(min(ex.BOX_V[0], ex.SB_V[0]) + max(ex.BOX_V[1], ex.SB_V[1])) / 2,
                  -ex.BOX_Z[0]])

HEX = lambda h: tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
COLOURS = dict(
    petg=(0.95, 0.76, 0.10), pla=(0.94, 0.54, 0.14), exma_dark=(0.18, 0.20, 0.23), exma_base=(0.17, 0.18, 0.21),
    ear=HEX("#2f6db5"), wood=(0.78, 0.60, 0.36), ply=(0.86, 0.75, 0.56), steel=(0.62, 0.65, 0.68),
    zinc=(0.78, 0.78, 0.72), bb=(0.93, 0.93, 0.88), copper=(0.72, 0.45, 0.20), pvc=(0.91, 0.92, 0.93),
    pex=(0.96, 0.96, 0.96), ptfe=(0.97, 0.97, 0.97), crimp=(0.80, 0.80, 0.83),
    boom=HEX("#2e9e44"), stick=HEX("#2a6fdb"), bucket=HEX("#d93a2b"), slew=HEX("#8e44ad"))

MESH_PARTS = ["tower", "base", "bucket", "bucket-ear-left", "bucket-ear-right"]
HALF_PARTS = ["boom-half-left", "boom-half-right", "stick-half-left", "stick-half-right"]
EXMA = {  # part: (group, colour)
    "boom-half-left": ("Arm", "petg"), "boom-half-right": ("Arm", "petg"),
    "stick-half-left": ("Arm", "petg"), "stick-half-right": ("Arm", "petg"),
    "bucket": ("Arm", "exma_base"), "bucket-ear-left": ("Arm", "ear"), "bucket-ear-right": ("Arm", "ear"),
    "tower": ("Turret and slewing ring", "exma_dark"), "base": ("Turret and slewing ring", "exma_base"),
}
PRINTED_GROUP = {
    "boom-drum": "Arm", "stick-drum": "Arm", "bucket-drum-axle": "Arm",
    "slewing-ring-retaining-ring": "Turret and slewing ring",
    "slew-drum": "Pedestal", "slew-tube-bushing": "Pedestal", "elbow-support": "Pedestal",
    "conduit-end-fitting-pedestal": "Pedestal",
    "conduit-end-fitting-box": "Control box", "lever-hub-boom": "Control box", "lever-hub-stick": "Control box",
    "lever-hub-bucket": "Control box", "slew-spool": "Control box", "slew-wheel": "Control box",
    "spool-riser": "Control box", "slew-tube-post": "Control box",
}
WOOD_GROUP = {"control-box": "Control box", "pedestal": "Pedestal", "sandbox": "Sandbox"}


# ---------------------------------------------------------------- 1. EX-MA parts as B-rep
def convert_parts(work):
    """Every EX-MA part to work/parts/<name>.step, each conversion in its own process."""
    parts = work / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    for name in MESH_PARTS:
        out = parts / f"{name}.step"
        if out.exists():
            continue
        print(f"  {name}: mesh -> B-rep", flush=True)
        r = subprocess.run([py, str(SRC / "2026-09-28-mesh-to-brep.py"), str(STL_DIR / f"2026-09-24-{name}.stl"),
                            str(out)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"{name}: conversion failed\n{r.stderr[-2000:]}")
    for member in ("boom", "stick"):
        if all((parts / f"{member}-half-{s}.step").exists() for s in ("left", "right")):
            continue
        print(f"  {member} halves: original halves -> B-rep, modifications as CAD booleans", flush=True)
        r = subprocess.run([py, str(SRC / "2026-09-28-arm-halves-cad.py"), member, str(work)],
                           capture_output=True, text=True)
        print(r.stdout[-3000:], flush=True)
        if r.returncode != 0:
            raise RuntimeError(f"{member} halves failed\n{r.stderr[-3000:]}")
    return parts


# ---------------------------------------------------------------- 2. items
def exma_items(parts):
    out = []
    for name, (grp, col) in EXMA.items():
        sol = cq.importers.importStep(str(parts / f"{name}.step")).solids().vals()
        assert len(sol) == 1, (name, len(sol))
        out.append((grp, name, sol[0], col))
    return out


def printed_items():
    out = []
    P = asm.placements()
    cache = {}
    for key, Tm in P.items():
        base = key.split("@")[0]
        if base not in cache:
            cache[base] = cq.importers.importStep(str(STEP_DIR / f"2026-09-24-{base}.step")).val()
        name = base if "@" not in key else f"{base}-{key.split('@')[1]}"
        out.append((PRINTED_GROUP[base], name, H.placed(cache[base], Tm), "pla"))
    knob = cq.importers.importStep(str(STEP_DIR / "2026-09-24-lever-knob.step")).val()
    for j, (vh, vd) in ex.LEVERS.items():
        Tm = H.frame((ex.AXLE_U, vh, ex.AXLE_Z + ex.HANDLE_LEN), (0, 0, 1), (1, 0, 0))
        out.append(("Control box", f"lever-knob-{j}", H.placed(knob, Tm), "pla"))
    return out


def wood_items():
    return [(WOOD_GROUP[p.group], "plywood " + p.name, bx.panel_solid(p).val(),
             "wood" if p.group == "control-box" else "ply") for p in bx.panels()]


def hardware_items():
    meshes = {n: trimesh.load(STL_DIR / f"2026-09-24-{n}.stl") for n in
              ("tower", "boom-half-left", "boom-half-right", "bucket-ear-left", "bucket-ear-right")}
    return H.all_items(meshes)


# ---------------------------------------------------------------- 3. assembly
def safe(name):
    return name.replace("/", "-").replace("(", "").replace(")", "").replace("  ", " ").strip()


def build(items):
    """items: (group path 'A/B', name, shape, colour) -> nested cq.Assembly, one component per part."""
    root = cq.Assembly(name="EX-MA manual excavator")
    groups = {}
    used = defaultdict(set)

    def group(path):
        parent, cur = root, ""
        for part in path.split("/"):
            cur = f"{cur}/{part}" if cur else part
            if cur not in groups:
                groups[cur] = cq.Assembly(name=safe(part))
                parent.add(groups[cur], name=safe(part))
            parent = groups[cur]
        return groups[path]

    for grp, name, shp, col in items:
        g = group(grp)
        nm, base, k = safe(name), safe(name), 2
        while nm in used[grp]:
            nm = f"{base} {k}"
            k += 1
        used[grp].add(nm)
        g.add(shp.translate(cq.Vector(*SHIFT)), name=nm, color=cq.Color(*COLOURS[col]))
    return root


# ---------------------------------------------------------------- 4. checks
def triangle_faces(shape):
    """Three-sided flat faces: count and share of the surface area (the original meshes' facets
    where the EX-MA model itself is faceted)."""
    fs = shape.Faces()
    tri = [f for f in fs if f.geomType() == "PLANE" and len(f.Edges()) == 3]
    return len(tri), 100.0 * sum(f.Area() for f in tri) / sum(f.Area() for f in fs)


def check_parts(parts):
    rep = {}
    for name in EXMA:
        s = cq.importers.importStep(str(parts / f"{name}.step")).solids().vals()
        m = trimesh.load(STL_DIR / f"2026-09-24-{name}.stl", force="mesh")
        # surface distance, printed STL <-> solid, both ways
        vs, ts = s[0].tessellate(0.05, 0.2)
        rm = trimesh.Trimesh(np.array([(p.x, p.y, p.z) for p in vs]), np.array(ts))
        a, _ = trimesh.sample.sample_surface(rm, 20000, seed=1)
        b, _ = trimesh.sample.sample_surface(m, 20000, seed=2)
        d = np.r_[trimesh.proximity.closest_point(m, a)[1], trimesh.proximity.closest_point(rm, b)[1]]
        n_tri, share = triangle_faces(s[0])
        rep[name] = dict(solids=len(s), valid=bool(s[0].isValid()), faces=dict(Counter(f.geomType() for f in s[0].Faces())),
                         triangle_faces=n_tri, triangle_area_percent=round(share, 1), volume=round(s[0].Volume(), 1),
                         stl_volume=round(float(m.volume), 1), dev_p50=round(float(np.percentile(d, 50)), 3),
                         dev_p99=round(float(np.percentile(d, 99)), 3), dev_max=round(float(d.max()), 3))
        print(f"  {name}: {rep[name]}", flush=True)
    return rep


def check_assembly(step, n_items):
    shp = cq.importers.importStep(str(step)).val()
    sols = shp.Solids()
    bb = shp.BoundingBox()
    return dict(components=n_items, solids=len(sols), invalid=sum(1 for s in sols if not s.isValid()),
                bbox=[round(v, 2) for v in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)])


README = """EX-MA manual excavator - full assembly as solid bodies
=====================================================

{step}   STEP AP214, millimetres, Z up.
parts/         the nine EX-MA parts on their own, in the build frame (not moved).
checks.json    the numbers below, machine readable.

Placement: the floor bottom (control box and sandbox floors) lies on Z = 0 and the footprint is
centred on X = 0 / Y = 0.

Structure: one component per part, each holding one solid body, grouped as
{groups}

Every body is a real B-rep solid: holes are cylinders with editable diameters, faces are planes,
cylinders, cones or spheres that can be pushed / pulled, chamfered and filleted. Fasteners have
plain shanks at the nominal major diameter (no modelled threads). Components: {n}.

EX-MA parts (converted from the print meshes; deviation = surface distance to the printed STL):
{parts}

Assembly read back: {asm}

Known differences from the print files (noted, not changed):
- stick nose: one cylinder r 11.9 mm where the print has the old 12-sided hood filled to
  r 11.75 - 12.02 (within 0.15 mm).
- boom / stick stop bulkhead: the plate is clipped to one convex hull of the arm's inner section
  (the print uses 2 mm-spaced hull pieces), up to about 1 mm different inside the arm.
- where the original EX-MA model is itself faceted (coarse arcs, small blends and corners), the
  solid keeps those facets as flat faces, as printed - listed above as three-sided flat faces
  (1 - 7 % of each part's area, mostly under 1 mm2 each).

Build notes found while placing the hardware:
- the M3x12 drum key screws from both sides overlap about 1.6 mm in the drum's through hole.
- nine #6 x 3/4in screws (spool riser 3, slew sleeve posts 4, elbow support 2) are 1.4 mm longer
  than the wood under them and show below the floor.
- the spool axle bottom uses a 5/16in jam nut in the floor counterbore (a full nut would stand
  1.4 mm below the floor).
- the 42 mm boom split-pin rods (bill of materials length) stand about 20 mm past their jam nuts.

Rebuild: python Source/2026-09-28-solid-assembly.py  (CadQuery 2.x, trimesh, manifold3d, shapely)
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(Path(tempfile.gettempdir()) / "ex-ma-solid-assembly"),
                    help="scratch folder for the converted parts and the assembly STEP")
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    t = time.time()
    print("1. EX-MA parts", flush=True)
    parts = convert_parts(work)
    part_rep = check_parts(parts)
    print(f"2. items ({time.time() - t:.0f}s)", flush=True)
    items = exma_items(parts) + printed_items() + wood_items() + hardware_items()
    bad = [n for g, n, s, c in items if not s.isValid() or len(s.Solids()) != 1]
    if bad:
        raise RuntimeError(f"not one valid solid: {bad}")
    print(f"   {len(items)} components", flush=True)
    print(f"3. assembly ({time.time() - t:.0f}s)", flush=True)
    step = work / ASSEMBLY_NAME
    build(items).export(str(step))
    print(f"4. checks ({time.time() - t:.0f}s)", flush=True)
    asm_rep = check_assembly(step, len(items))
    print(f"   {asm_rep}", flush=True)
    counts = Counter(g for g, n, s, c in items)
    checks = dict(assembly=asm_rep, parts=part_rep, groups=dict(counts), shift=SHIFT.round(3).tolist())
    (work / "checks.json").write_text(json.dumps(checks, indent=1))
    groups = "\n".join(f"  {g}: {k}" for g, k in sorted(counts.items()))
    prt = "\n".join(f"  {n}: {r['solids']} solid, valid {r['valid']}, faces {r['faces']}, "
                    f"three-sided flat faces {r['triangle_faces']} ({r['triangle_area_percent']} % of the area), "
                    f"deviation p99 {r['dev_p99']} mm / max {r['dev_max']} mm" for n, r in part_rep.items())
    readme = README.format(step=ASSEMBLY_NAME, groups=groups, n=len(items), parts=prt,
                           asm=f"{asm_rep['solids']} solids for {asm_rep['components']} components, "
                               f"{asm_rep['invalid']} invalid, bounding box {asm_rep['bbox']} mm")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(step, ASSEMBLY_NAME)
        for name in EXMA:
            z.write(parts / f"{name}.step", f"parts/2026-09-28-{name}.step")
        z.writestr("checks.json", json.dumps(checks, indent=1))
        z.writestr("README.txt", readme)
    print(f"written {ZIP_PATH} ({ZIP_PATH.stat().st_size / 1e6:.1f} MB, {time.time() - t:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
