#!/usr/bin/env python3
"""EX-MA B6 package: assembly STEP, Bambu A1 plates (3MF), bill of materials, validation roll-up.

Run:  <cadenv>/bin/python 2026-09-24-package.py [--skip-step]
Writes:
  STEP/2026-09-24-ex-ma-assembly.step   (exact B-rep: new printed parts, wood, hardware; built pose)
  2026-09-24-ex-ma-assembly.glb         (every part incl. the modified EX-MA meshes, ropes and sleeves)
  3MF/2026-09-27-{bambu,orca}-{arm-shell-petg,other-parts-plaplus}.3mf  (via 2026-09-27-slicer-projects.py)
  2026-09-24-bill-of-materials.md
  Validation/2026-09-24-package-check.json (read by the validation roll-up)
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


asm = _load("asm", "2026-09-24-assembly.py")
bx = _load("bx", "2026-09-24-build-box.py")
bp = _load("bp", "2026-09-24-build-parts.py")
sp = _load("sp", "2026-09-27-slicer-projects.py")
ex, rt = asm.ex, asm.rt
OUT = ex.OUT
STL, STEP, TMF, VAL = OUT / "STL", OUT / "STEP", OUT / "3MF", OUT / "Validation"

BED, BED_MARGIN, BED_Z = 256.0, 5.0, 256.0
DENSITY = 1.24e-3                   # g/mm3 (PLA; PETG 1.27)
FILL = 0.55                         # effective solid fraction at 4 walls + 40 % infill
OVERHANG_NZ = -math.sin(math.radians(45.0))   # faces pointing further down than 45 deg need support

MOD_DESC = {
    "tower": "EX-MA tower: circular flange = inner race, PEX clamp hub, centre funnel removed, lowered 13 mm",
    "base": "EX-MA base: centre post removed, lower race rim with nut slots, 4 screw holes to the pedestal",
    "boom-half-left": "EX-MA boom half (+v): PTFE channels, stick-tube bulkhead, drum key sockets, joining lugs",
    "boom-half-right": "EX-MA boom half (-v): as the left half, mirrored",
    "stick-half-left": "EX-MA stick half (+v): PTFE channels, bucket-tube bulkhead, drum key sockets, joining lugs",
    "stick-half-right": "EX-MA stick half (-v): as the left half, mirrored",
    "bucket-ear-left": "EX-MA bucket ear G: hex socket for the bucket drum-axle",
    "bucket-ear-right": "EX-MA bucket ear H: hex socket for the bucket drum-axle",
    "bucket": "EX-MA bucket: repaired STEP body + bracket I + lugs O/P merged into one part",
}
COLORS = dict(printed=(0.94, 0.54, 0.14), exma_dark=(0.18, 0.20, 0.23), exma_yellow=(0.95, 0.76, 0.10),
              wood=(0.78, 0.60, 0.36), ply=(0.86, 0.75, 0.56), steel=(0.60, 0.64, 0.67), copper=(0.72, 0.45, 0.20),
              pvc=(0.91, 0.92, 0.93), pex=(0.96, 0.96, 0.96), dowel=(0.66, 0.45, 0.25))


# ---------------------------------------------------------------- printed parts
def printed_parts():
    rows = []
    for n, (fn, q, desc) in bp.PARTS.items():
        rows.append(dict(name=n, qty=q, desc=desc, kind="new", mesh=trimesh.load(STL / f"2026-09-24-{n}.stl")))
    for n in asm.MODIFIED:
        rows.append(dict(name=n, qty=1, desc=MOD_DESC[n], kind="modified",
                         mesh=trimesh.load(STL / f"2026-09-24-{n}.stl")))
    return rows


def _down_rotations():
    """Rotations that put each of the 6 axis directions facing the bed (-z)."""
    out = []
    for axis in np.eye(3):
        for s in (1, -1):
            d = s * axis
            target = np.array([0, 0, -1.0])
            v = np.cross(d, target)
            c = float(d @ target)
            if np.linalg.norm(v) < 1e-9:
                R = np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
            else:
                vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
                R = np.eye(3) + vx + vx @ vx * (1 / (1 + c))
            label = ("+" if s > 0 else "-") + "xyz"[int(np.argmax(np.abs(axis)))]
            out.append((label, R))
    return out


# round / grooved parts print with their axis vertical (rope grooves and bores stay round and
# strong); only which end faces the bed is chosen
AXIS_VERTICAL = {"boom-drum", "stick-drum", "bucket-drum-axle", "slew-drum", "slewing-ring-retaining-ring",
                 "lever-hub-boom", "lever-hub-stick", "lever-hub-bucket", "slew-spool", "slew-wheel",
                 "slew-tube-bushing", "spool-riser", "conduit-end-fitting-box", "conduit-end-fitting-pedestal", "base"}
ORIENT_TEXT = {"+z": "top face down", "-z": "as modelled (bottom down)", "+x": "on its +x side", "-x": "on its -x side",
               "+y": "on its +y side", "-y": "on its -y side"}


def orient(mesh, name=""):
    """Axis-aligned print orientation with the least support area (ties: largest bed contact).
    Returns (oriented mesh on z = 0, label, support area mm2, bed contact mm2)."""
    best = None
    for label, R in _down_rotations():
        if name in AXIS_VERTICAL and not label.endswith("z"):
            continue
        m = mesh.copy()
        A = np.eye(4)
        A[:3, :3] = R
        m.apply_transform(A)
        m.apply_translation(-m.bounds[0])
        nz = m.face_normals[:, 2]
        zc = m.triangles_center[:, 2]
        on_bed = zc < 0.3
        support = float(m.area_faces[(nz < OVERHANG_NZ) & ~on_bed].sum())
        contact = float(m.area_faces[(nz < -0.99) & on_bed].sum())
        score = support - 0.02 * contact
        if best is None or score < best[0]:
            best = (score, m, label, support, contact)
    return best[1], best[2], best[3], best[4]


# ---------------------------------------------------------------- assembly STEP
def stl_to_solid(path):
    from OCP.StlAPI import StlAPI_Reader
    from OCP.TopoDS import TopoDS_Shape, TopoDS
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    import cadquery as cq
    shape = TopoDS_Shape()
    StlAPI_Reader().Read(shape, str(path))
    sew = BRepBuilderAPI_Sewing(1e-4)
    sew.Add(shape)
    sew.Perform()
    exp = TopExp_Explorer(sew.SewedShape(), TopAbs_SHELL)
    mk = BRepBuilderAPI_MakeSolid()
    while exp.More():
        mk.Add(TopoDS.Shell_s(exp.Current()))
        exp.Next()
    return cq.Solid(mk.Solid()).fix()


def hardware_solids():
    """Hardware as B-rep solids (built pose)."""
    import cadquery as cq
    V = cq.Vector
    out = {}
    cyl = lambda r, a, b: cq.Solid.makeCylinder(r, float(np.linalg.norm(np.subtract(b, a))), V(*a),
                                                V(*(np.subtract(b, a) / np.linalg.norm(np.subtract(b, a)))))
    y = ex.AXLE_BLOCK_V[1] + 10
    out["lever axle 5/16in rod"] = (cyl(ex.LEVER_AXLE_D / 2, (ex.AXLE_U, -y, ex.AXLE_Z), (ex.AXLE_U, y, ex.AXLE_Z)), "steel")
    out["slew spool axle 5/16in rod"] = (cyl(ex.LEVER_AXLE_D / 2, (*ex.WHEEL_C, ex.BOX_Z[0]), (*ex.WHEEL_C, ex.BOX_Z[1] + 32.0)), "steel")
    for j, (vh, vd) in ex.LEVERS.items():
        a, b = (ex.AXLE_U, vh, ex.AXLE_Z + 9.0), (ex.AXLE_U, vh, ex.AXLE_Z + ex.HANDLE_LEN + ex.KNOB_BORE_DEPTH)
        knob = cq.Solid.makeSphere(bx.KNOB_R, V(b[0], b[1], b[2] - ex.KNOB_BORE_DEPTH + bx.KNOB_R - 4.0),
                                   angleDegrees1=-90, angleDegrees2=90)
        out[f"{j} handle (5/16in rod + printed knob)"] = (cyl(ex.HANDLE_D / 2, a, b).fuse(knob).clean(), "steel")
    u_a, u_b = ex.BOX_U[1] - ex.T_WOOD - ex.CONDUIT_SOCKET, ex.PED_U[0] + ex.T_WOOD + ex.CONDUIT_SOCKET
    pipe = cyl(ex.COND_R, (u_a, ex.MOUTH_V, ex.COND_Z), (u_b, ex.MOUTH_V, ex.COND_Z)).cut(
        cyl(ex.CONDUIT_ID / 2, (u_a - 1, ex.MOUTH_V, ex.COND_Z), (u_b + 1, ex.MOUTH_V, ex.COND_Z)))
    out["2in PVC conduit"] = (pipe, "pvc")
    pex = cyl(ex.TURRET_TUBE_OD / 2, (0, 0, ex.TUBE_Z[0]), (0, 0, ex.TUBE_Z[1])).cut(
        cyl(ex.TURRET_TUBE_ID / 2, (0, 0, ex.TUBE_Z[0] - 1), (0, 0, ex.TUBE_Z[1] + 1)))
    out["3/4in PEX-B turret tube"] = (pex, "pex")
    # copper: straight leg + R30 sweep, swept as one solid
    u_fit = ex.PED_U[0] + ex.T_WOOD + ex.FIT_T - 8.0
    zc = ex.Z_ARM_LAYER
    R = ex.ELBOW_R
    mid = (-R + R * math.cos(math.radians(-45)), zc + R + R * math.sin(math.radians(-45)))
    path = cq.Workplane("XZ").moveTo(u_fit, zc).lineTo(-R, zc).threePointArc(mid, (0.0, zc + R))
    prof = cq.Workplane("YZ", origin=(u_fit, 0, zc)).circle(ex.COPPER_OD / 2).circle(ex.COPPER_OD / 2 - 1.0)
    out["1/2in copper elbow + pipe"] = (prof.sweep(path).val(), "copper")
    for j in ("boom", "stick"):
        c = ex.P_BOOM if j == "boom" else ex.P_STICK
        v0, v1 = asm.SPLIT_PIN_V[j]
        for s, nm in ((1, "left"), (-1, "right")):
            out[f"{j} split pin {nm} (8-32 rod)"] = (cyl(ex.PIN_D / 2, (c[0], s * v0, c[1]), (c[0], s * v1, c[1])), "steel")
    out["bucket pin (8-32 rod)"] = (cyl(ex.PIN_D / 2, (ex.P_BUCKET[0], -32, ex.P_BUCKET[1]), (ex.P_BUCKET[0], 32, ex.P_BUCKET[1])), "steel")
    balls = None
    n_b = int(2 * math.pi * ex.BALL_CIRCLE_R // (ex.BALL_D + 0.4))
    for k in range(n_b):
        a = 2 * math.pi * k / n_b
        s = cq.Solid.makeSphere(ex.BALL_D / 2, V(ex.BALL_CIRCLE_R * math.cos(a), ex.BALL_CIRCLE_R * math.sin(a), ex.BALL_Z),
                                angleDegrees1=-90, angleDegrees2=90)
        out[f"BB {k + 1:02d}"] = (s, "pex")
    return out


def placed(shape, T):
    """Rigid 4x4 placement of a CadQuery shape (built directly as a gp_Trsf)."""
    import cadquery as cq
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    t = gp_Trsf()
    t.SetValues(*[float(x) for x in T[:3, :4].ravel()])
    return cq.Shape.cast(BRepBuilderAPI_Transform(shape.wrapped, t, True).Shape())


def assembly_step(path):
    import cadquery as cq
    assy = cq.Assembly(name="EX-MA")
    col = lambda k: cq.Color(*COLORS[k])
    count = 0
    P = asm.placements()
    for name, T in P.items():
        base = name.split("@")[0]
        shp = cq.importers.importStep(str(STEP / f"2026-09-24-{base}.step")).val()
        shp = placed(shp, T)
        assy.add(shp, name=name.replace("@", "-"), color=col("printed"))
        count += 1
    # The modified EX-MA parts are meshes: sewn into STEP they become one face per triangle
    # (~420 MB for the nine parts), so they stay as STLs already placed in this frame and are
    # included in the GLB. stl_to_solid() converts any one of them on demand.
    for p in bx.panels():
        assy.add(bx.panel_solid(p).val(), name=p.name.replace(" ", "-").replace("(", "").replace(")", ""),
                 color=col("wood" if p.group == "control-box" else "ply"))
        count += 1
    for name, (shp, c) in hardware_solids().items():
        assy.add(shp, name=name.replace(" ", "-").replace("/", "_"), color=col(c))
        count += 1
    try:
        assy.export(str(path))
    except AttributeError:
        assy.save(str(path))
    back = cq.importers.importStep(str(path))
    n_back = len(back.solids().vals())
    return dict(items=count, solids_on_reimport=n_back)


# ---------------------------------------------------------------- hardware counts (from the models)
# The user's kits (References/IMG_2449.jpeg, IMG_2454.jpeg)
M3_KIT = {  # (head, length): pieces in the Fgruh 2300-pc kit
    **{("socket cap", L): n for L, n in ((4, 40), (6, 42), (8, 42), (12, 32), (16, 30), (20, 30), (25, 30), (30, 20), (35, 20))},
    **{("button head", L): n for L, n in ((6, 40), (8, 42), (10, 42), (12, 32), (16, 30), (20, 30), (25, 30), (30, 20), (35, 20))},
    "nut": 576, "flat washer": 576, "split-lock washer": 576,
}
ROD_832_MM, NUTS_832 = 914.0, 22   # Hillman 8-32 threaded rod 3 ft + 22 hex nuts


def hardware_table():
    """BOM hardware in four groups: the user's M3 kit, the user's Hillman parts, the user's wood
    screws, and stock still to buy. Counts come from the part features, lengths from the paths."""
    feat = json.loads((VAL / "2026-09-24-mods-features.json").read_text())
    box = json.loads((VAL / "2026-09-24-box-data.json").read_text())
    cl = box["cut_lengths"]
    n_keys = 2 * len(bp.BOOM_DRIVE_ANGS) + 2 * len(bp.STICK_DRIVE_ANGS)
    n_lugs_b, n_lugs_s = feat["boom joining lugs (M3 + nut)"], feat["stick joining lugs (M3 + nut)"]
    n_ret = bp.N_RET_BOLTS
    n_lev = len(ex.LEVERS)
    n_wheel = 3
    n_anchor = 2 * n_lev + 2
    n_balls = int(2 * math.pi * ex.BALL_CIRCLE_R // (ex.BALL_D + 0.4))
    # M3 uses: (head, length, qty, nuts, flat washers, split-lock washers, what for)
    uses = [
        ("socket cap", 12, n_keys, 0, 0, 0, "joint-drum key screws: lock the boom and stick drums to their arm members "
         "(4 per drum, 2 through each side wall; the heads sit in pockets in the wall)"),
        ("socket cap", 12, n_ret, n_ret, 0, n_ret, "slewing-ring retaining ring: holds the turret down on the BBs "
         "(nuts slide into the slots in the base rim)"),
        ("socket cap", 20, n_lugs_b + n_lugs_s, n_lugs_b + n_lugs_s, 0, 0,
         f"joining lugs: clamp the two halves of the boom ({n_lugs_b}) and the stick ({n_lugs_s}) together"),
        ("socket cap", 20, n_lev, n_lev, 0, n_lev, "lever drag clamps: squeeze the 5/16in rod to set each lever's holding friction"),
        ("socket cap", 20, n_wheel, n_wheel, 0, n_wheel, "slew wheel to the spool flange"),
        ("socket cap", 25, 2, 2, 0, 2, "pinch clamps on the PEX turret tube (turret hub, pedestal slew drum)"),
        ("socket cap", 20, n_lev, n_lev, 0, n_lev, "handle pinch clamps: hold each 5/16in rod handle in its lever hub"),
        ("socket cap", 25, 4, 4, 8, 0, "pedestal conduit fitting to the pedestal wall (fitting 6 + wall 12 mm)"),
        ("socket cap", 35, 4, 4, 8, 0, "box conduit fitting through the box front and the sandbox wall (6 + 12 + 12 mm)"),
        ("socket cap", 30, 2, 2, 4, 0, "box front to the sandbox wall, lower corners (12 + 12 mm)"),
        ("button head", 10, n_anchor, n_anchor, 2 * n_anchor, n_anchor,
         "slotted rope-tail anchors = tension adjusters (2 per lever, 2 on the spool); the rope loop sits between two washers"),
    ]
    need = {}
    for head, L, q, nuts, fw, lw, _ in uses:
        need[(head, L)] = need.get((head, L), 0) + q
        need["nut"] = need.get("nut", 0) + nuts
        need["flat washer"] = need.get("flat washer", 0) + fw
        need["split-lock washer"] = need.get("split-lock washer", 0) + lw
    m3 = [(f"M3 × {L} {head}", q, f"{need[(head, L)]} of {M3_KIT[(head, L)]}", use) for head, L, q, *_, use in uses]
    for k in ("nut", "flat washer", "split-lock washer"):
        m3.append((f"M3 {k}", need[k], f"{need[k]} of {M3_KIT[k]}", "with the screws above; split-lock washers under the "
                   "nuts that hold moving or clamping parts" if k == "split-lock washer" else "with the screws above"))
    over = [k for k, v in need.items() if v > M3_KIT[k]]
    # 8-32 rod: pins only; jam nuts (two nuts locked against each other)
    pins = [("boom split pin (tower cheek → boom wall)", 2, 42.0, 2), ("stick split pin (boom tip → stick wall)", 2, 22.0, 2),
            ("bucket pin (ears + drum-axle)", 1, 65.0, 4)]
    rod_used = sum(n * L + n * 2.0 for _, n, L, _ in pins)
    nuts_used = sum(n * k for _, n, _, k in pins)
    hill = [(f"8-32 rod, {nm}", n, f"{L:.0f} mm", "a jam pair (2 nuts) on the outer end" if k == 2 else "a jam pair at each end")
            for nm, n, L, k in pins]
    hill.append(("8-32 hex nuts", nuts_used, f"{nuts_used} of {NUTS_832}", "jam nuts on the pins (two nuts tightened against each other)"))
    hill.append(("8-32 rod used", "", f"{rod_used:.0f} of {ROD_832_MM:.0f} mm", "the rest is spare"))
    hill.append(("#4-40 and #6-32 machine screws", "", "", "not needed (spares)"))
    wood = [("#8 × 1in wood screw", 4, "", "base to the pedestal top"),
            ("#6 × 3/4in wood screw", 4 + 3 + 4 + 3 + 2, "", "bearing blocks (from below), spool riser, sleeve posts, PEX bushing, elbow support"),
            ("#6 × 1-1/4in wood screw", 4 * (12 + 10 + 8), "", "panel joints, ~4 per edge (box 12 edges, pedestal 10, sandbox 8), with wood glue")]
    buy = []
    rope_total = 0.0
    for j in ("boom", "stick", "bucket"):
        L = cl[f"{j} rope (one length, midpoint crimp)"] + 120.0
        rope_total += L
        buy.append(("1/16in galvanized 7x19 rope (have)", 1, f"{L:.0f} mm", f"{j} circuit: one length, single crimp at the "
                    "midpoint on the joint drum, double-crimp loops on the lever anchors (+60 mm per loop included)"))
    for lane in "AB":
        L = cl[f"slew rope {lane} (spool anchor -> pedestal crimp)"] + 60.0
        rope_total += L
        buy.append(("1/16in galvanized 7x19 rope (have)", 1, f"{L:.0f} mm", f"slew rope {lane}: single crimp in the pedestal "
                    "drum pocket, double-crimp loop on the spool anchor"))
    buy.append(("single crimp sleeve (have)", 5, "1/16in", "3 joint-drum midpoints + 2 slew rope ends (+ spares)"))
    buy.append(("double crimp sleeve (have)", 8, "1/16in", "6 arm tail loops + 2 slew loops (+ spares)"))
    ptfe_total = 0.0
    for k, v in cl.items():
        if k.startswith("PTFE"):
            ptfe_total += v + 10.0
            buy.append(("PTFE tube 4 mm OD × 2 mm ID", 1, f"{v + 10:.0f} mm", k.replace("PTFE ", "") + " (+10 mm to trim)"))
    buy += [
        ("5/16in rod (have)", 2, f"{2 * ex.AXLE_BLOCK_V[1] + 20:.0f} mm, {ex.BOX_Z[1] + 32.0 - ex.BOX_Z[0]:.0f} mm", "lever axle; slew spool axle"),
        ("5/16in rod (have)", 3, f"{ex.HANDLE_LEN - 9.0 + ex.KNOB_BORE_DEPTH:.0f} mm", "lever handles (printed knobs glued on top)"),
        ("5/16in nut + washer", 4, "5/16in", "2 on the lever axle (outside the bearing blocks), 2 on the spool axle"),
        ("6 mm airsoft BBs (or 1/4in steel balls)", n_balls, "Ø6", "slewing ring (+ ~5 spares)"),
        ("3/4in PEX-B tube (have)", 1, f"{ex.TUBE_Z[1] - ex.TUBE_Z[0]:.0f} mm", "turning turret tube"),
        ("1/2in copper (have)", 1, "90° sweep elbow (R ≈ 30) + 50 mm pipe", "fixed elbow in the pedestal (deburr both ends)"),
        ("2in sch 40 PVC", 1, f"{rt.CONDUIT_RUN:.0f} mm", "conduit between the box and the pedestal (seal with silicone at the sandbox wall)"),
        ("12 mm plywood", "see cut list", "", "control box, pedestal, sandbox (2026-09-24-cut-list.md)"),
        ("glue", "", "wood glue; epoxy or CA", "panel joints; bucket ears to the bucket lugs (as in the original EX-MA); printed knobs on the handle rods"),
    ]
    sections = [
        ("From your M3 kit (Fgruh 2300 pc)", "Every machine screw is an M3 from the kit; the longest needed is 35 mm. "
         "Column 3 shows how many of that size are used out of how many the kit holds.", ("Item", "Qty", "Used / in kit", "What it does"), m3),
        ("From your Hillman parts", "The 8-32 rod is only used for the joint pins; nuts are used in jam pairs instead of lock nuts.",
         ("Item", "Qty", "Length / used", "Notes"), hill),
        ("Your wood screws", "", ("Item", "Qty", "", "Used for"), wood),
        ("Rope, tube and other stock", "PTFE tube = the white 4 mm OD / 2 mm ID filament (Bowden) tube used on 3D printers. "
         "The stick and bucket ropes run inside it through the arm, and the slew ropes through the conduit; "
         "it is what lets each lever move only its own joint.", ("Item", "Qty", "Size / length", "Used for"), buy),
    ]
    return sections, dict(rope_total=rope_total, ptfe_total=ptfe_total, n_balls=n_balls, keys=n_keys,
                          lugs=n_lugs_b + n_lugs_s, m3_over_kit=over, rod_832_used=rod_used, nuts_832_used=nuts_used)


# ---------------------------------------------------------------- BOM
def bom_md(rows, plates, H, totals):
    L = ["# EX-MA manual excavator — bill of materials", "",
         "Everything needed to build the simplified EX-MA arm, the wooden control box, the pedestal and the "
         "sandbox. Counts come from the build scripts (drum keys, lugs, bolts, balls), lengths from the "
         "validated rope and tube paths.", "",
         "Print settings (already in the slicer project files in `3MF/`, see Plates below): Bambu Lab A1, 0.6 mm "
         "nozzle, your \"A1 0.6 Fast Start\" printer preset, process \"0.30mm Strength @BBL A1 0.6 nozzle\" (0.3 mm "
         "layers, 4 walls, 25 % infill), 40 % infill on drums, hubs, clamps and anything carrying a pin, tree "
         "supports on the parts marked \"yes\" below. Arm shell (boom and stick halves) in PETG, everything else "
         "in SUNLU PLA+ 2.0. Orientation below is the one with the least support area; every wall was checked in "
         "that orientation for the 0.6 mm nozzle (`Validation/2026-09-25-wall-check.json`).", ""]
    for kind, title in (("new", "Printed parts — new"), ("modified", "Printed parts — modified EX-MA parts")):
        L += [f"## {title}", "", "| Part | Qty | What it does | Volume | Est. mass | Print orientation | Print size (x × y × z) | Supports | Project, plate |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            if r["kind"] != kind:
                continue
            e = r["oriented"].extents
            sup = "none" if r["support"] < 50 else (f"light ({r['support'] / 100:.1f} cm²)" if r["support"] < 800
                                                    else f"yes ({r['support'] / 100:.0f} cm²)")
            L.append(f"| {r['name']} | {r['qty']} | {r['desc']} | {r['mesh'].volume / 1000:.1f} cm³ | "
                     f"{r['mesh'].volume * DENSITY * FILL:.0f} g | {ORIENT_TEXT[r['orient']]} | {e[0]:.0f} × {e[1]:.0f} × {e[2]:.0f} | {sup} | "
                     f"{', '.join(sorted(r.get('plates', [])))} |")
        L.append("")
    n_new = sum(r["qty"] for r in rows if r["kind"] == "new")
    n_mod = sum(r["qty"] for r in rows if r["kind"] == "modified")
    mass = sum(r["qty"] * r["mesh"].volume for r in rows) * DENSITY * FILL
    L += [f"Printed total: {n_new} new prints + {n_mod} modified EX-MA prints, about {mass / 1000:.2f} kg of filament "
          "(estimate at ~55 % effective fill).", "",
          "## Plates (Bambu A1, 256 × 256 mm)", "",
          "Two slicer projects, each saved for Bambu Studio 2.8.2.61 and for OrcaSlicer (nightly); open the one "
          "for your slicer — each opens with all of its plates, already named. The `bambu-` and `orca-` files hold "
          "the same parts in the same places.", "",
          "| Project | Material | Plate | Parts |", "|---|---|---|---|"]
    for c in plates:
        if c["slicer"] != "bambu":
            continue
        f = c["file"].replace("bambu-", "{bambu,orca}-")
        for p in c["plates"]:
            L.append(f"| `3MF/{f}` | {c['material']} ({c['filament']}) | {p['plate']} — {p['name']} | {', '.join(p['parts'])} |")
    L += ["", "## Part count by group", "", "| Group | Parts | Prints |", "|---|---|---|"]
    by = {r["name"]: r for r in rows}
    for g, names in sp.GROUPS.items():
        L.append(f"| {g} | " + ", ".join(n + (f" ×{by[n]['qty']}" if by[n]["qty"] > 1 else "") for n in names)
                 + f" | {sum(by[n]['qty'] for n in names)} |")
    L.append(f"| **Total** | {len(rows)} different parts (STL files) | **{sum(r['qty'] for r in rows)}** |")
    for title, intro, hdr, items in H:
        L += ["", f"## {title}", ""] + ([intro, ""] if intro else [])
        L += ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
        for row in items:
            L.append("| " + " | ".join(str(x) for x in row) + " |")
    L += ["", f"Rope total: {totals['rope_total'] / 1000:.1f} m (have at least {math.ceil(totals['rope_total'] / 1000 * 1.2)} m, which includes 20 % spare). "
          f"PTFE tube total: {totals['ptfe_total'] / 1000:.1f} m — buy one 5 m roll.", "",
          "M3 sizes all fit inside the kit's counts." if not totals["m3_over_kit"] else
          f"More needed than the kit holds: {totals['m3_over_kit']}.", "",
          "## Wood", "", "All wood parts, sizes and hole positions: `2026-09-24-cut-list.md` "
          "(STEP: `STEP/2026-09-24-control-box-wood.step`, `-pedestal-wood.step`, `-sandbox-wood.step`).", "",
          "## Part count", "",
          "- Removed from the original arm mechanism: 16 printed parts (2 double-groove drums, 4 idlers, the bucket "
          "drum + sleeve, 5 pins, 2 clips, the green slew ring, the base post cap).",
          "- Merged: bucket bracket I (2 pieces) and lugs O/P into the bucket body.",
          "- New arm-side mechanism parts: boom drum, stick drum, bucket drum-axle, slewing-ring retaining ring (4).",
          f"- New pedestal and conduit parts: slew drum, PEX bushing, elbow support, 2 conduit fittings (5).",
          f"- New control-box parts: 3 lever hubs, slew spool, slew wheel, spool riser, 2 sleeve posts (8).", ""]
    return "\n".join(L) + "\n"


def assembly_glb(path):
    """Every part as a mesh in the built pose (+ modelled ropes and sleeves) for quick viewing."""
    scene = trimesh.Scene()
    rgba = lambda k: (np.array(COLORS[k] + (1.0,)) * 255).astype(np.uint8)
    def add(mesh, name, key):
        m = mesh.copy()
        m.visual = trimesh.visual.ColorVisuals(m, face_colors=rgba(key))
        scene.add_geometry(m, node_name=name, geom_name=name)
    for name in asm.placements():
        add(asm.part(name), name, "printed")
    for name in asm.MODIFIED:
        add(asm.part(name), name, "exma_yellow" if name.startswith(("boom", "stick")) else "exma_dark")
    for p in bx.panels():
        add(ex.shape_to_mesh(bx.panel_solid(p).val(), tol=0.2), p.name, "wood" if p.group == "control-box" else "ply")
    for name, (m, c) in bx.hardware().items():
        add(m, name, {"steel": "steel", "dowel": "dowel", "pvc": "pvc", "copper": "copper", "pex": "pex"}[c])
    rope_col = dict(boom=(0.18, 0.62, 0.27), stick=(0.16, 0.44, 0.86), bucket=(0.85, 0.23, 0.17), slew=(0.56, 0.27, 0.68))
    for k, v in rope_col.items():
        COLORS[f"rope_{k}"] = v
    for j in ex.LEVERS:
        for st in bx.lever_strands(j, 0.0):
            add(bx.tube_mesh(np.array([st["tangent"], st["hole"]]), ex.ROPE_D / 2, 8), f"rope {st['name']} (box)", f"rope_{j}")
    for lane in "AB":
        sl = bx.slew_sleeve(lane)
        add(bx.tube_mesh(sl["poly"], ex.PTFE_OD / 2, 10), f"slew PTFE sleeve {lane}", "pex")
        for seg, nm in zip(bx.slew_rope_free(lane), ("box", "pedestal")):
            add(bx.tube_mesh(seg, ex.ROPE_D / 2, 8), f"slew rope {lane} ({nm})", "rope_slew")
    for name in rt.TUBES:
        add(bx.tube_mesh(rt.natural(name, dz=ex.TURRET_DZ), ex.PTFE_OD / 2, 10), f"PTFE {name} (arm)", "pex")
    scene.export(str(path))
    back = trimesh.load(str(path))
    return dict(nodes=len(back.geometry), size_mb=round(path.stat().st_size / 1e6, 1))


def main():
    skip_step = "--skip-step" in sys.argv
    rows = printed_parts()
    for r in rows:
        r["oriented"], r["orient"], r["support"], r["contact"] = orient(r["mesh"], r["name"])
    plate_checks = sp.write_projects(rows)
    for c in plate_checks:
        if c["slicer"] == "bambu":
            for p in c["plates"]:
                for inst in p["parts"]:
                    base = inst if inst in {r["name"] for r in rows} else inst.rsplit("-", 1)[0]
                    next(r for r in rows if r["name"] == base).setdefault("plates", set()).add(
                        f"{c['project'].split('-')[0]} {p['plate']}")
    H, totals = hardware_table()
    (OUT / "2026-09-24-bill-of-materials.md").write_text(bom_md(rows, plate_checks, H, totals))
    part_checks = []
    for r in rows:
        m = r["mesh"]
        e = r["oriented"].extents
        part_checks.append(dict(part=r["name"], watertight=bool(m.is_watertight),
                                bodies=len(m.split(only_watertight=False)), fits_bed=bool(max(e[0], e[1]) <= BED - 2 * BED_MARGIN
                                                                                            and e[2] <= BED_Z),
                                print_size=[round(float(x), 1) for x in e], orientation=r["orient"],
                                support_mm2=round(r["support"], 0)))
    import cadquery as cq
    step_checks = []
    for f in sorted(STEP.glob("2026-09-24-*.step")):
        if "assembly" in f.name or "wood" in f.name:
            continue
        step_checks.append(dict(step=f.name, solids=len(cq.importers.importStep(str(f)).solids().vals())))
    asm_check = None
    if not skip_step:
        print("assembly STEP (sewing the modified EX-MA meshes takes a few minutes)", flush=True)
        asm_check = assembly_step(STEP / "2026-09-24-ex-ma-assembly.step")
        asm_check["step_size_mb"] = round((STEP / "2026-09-24-ex-ma-assembly.step").stat().st_size / 1e6, 1)
        asm_check["glb"] = assembly_glb(OUT / "2026-09-24-ex-ma-assembly.glb")
    else:
        old = VAL / "2026-09-24-package-check.json"
        if old.exists():
            asm_check = json.loads(old.read_text()).get("assembly")
    (VAL / "2026-09-24-package-check.json").write_text(json.dumps(dict(
        parts=part_checks, steps=step_checks, plates=plate_checks, assembly=asm_check, totals=totals), indent=1))
    print(f"projects: {len(plate_checks)}  parts: {len(rows)}  assembly: {asm_check}")
    for c in part_checks:
        print(f"  {c['part']:30s} wt={c['watertight']} bodies={c['bodies']} bed={c['fits_bed']} "
              f"{c['orientation']} support={c['support_mm2']:.0f} mm2 size={c['print_size']}")
    for c in plate_checks:
        print(f"  {c['file']:45s} plates={len(c['plates'])} objects={c['objects']} inside={c['inside_own_plate']} "
              f"overlap={c['footprint_overlap']} max_h={c['max_height_mm']}")


if __name__ == "__main__":
    main()
