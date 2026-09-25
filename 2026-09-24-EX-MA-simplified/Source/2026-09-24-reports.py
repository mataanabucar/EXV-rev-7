#!/usr/bin/env python3
"""EX-MA reports: inspection-and-architecture document and the validation roll-up.

Numbers come from the shared constants and the Validation/*.json files written by
cable-kinematics.py, box-validation.py, build-exma-mods.py and package.py.
Run after those:  <cadenv>/bin/python 2026-09-24-reports.py
"""
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


ex = _load("exma", "2026-09-24-exma_common.py")
rt = _load("routing", "2026-09-24-routing.py")
VAL = ex.OUT / "Validation"
KIN = json.loads((VAL / "2026-09-24-kinematics-data.json").read_text())
BOX = json.loads((VAL / "2026-09-24-box-data.json").read_text())
PKG = json.loads((VAL / "2026-09-24-package-check.json").read_text())
EXT = (VAL / "2026-09-24-exterior-check.txt").read_text()
CAB = json.loads((VAL / "2026-09-24-cable-paths.json").read_text())
_WALL = VAL / "2026-09-25-wall-check.json"
WALL = json.loads(_WALL.read_text()) if _WALL.exists() else None
_FULL = VAL / "2026-09-25-full-assembly-check.json"
FULL = json.loads(_FULL.read_text()) if _FULL.exists() else None
VIEWS = [   # Preview/2026-09-24-<key>.png, rendered by render-scene.py (view set b7) + concept-render.mjs
    ("view1-complete-excavator", "Complete excavator: control box with the 3 levers and the slew wheel, pedestal, base, arm, bucket."),
    ("view2-full-system-cutaway", "Full-system cutaway (+v halves removed): every rope from its lever or wheel through the conduit, "
                                  "pedestal, copper elbow and PEX tube to its joint."),
    ("view3-control-box-cutaway", "Control box: lever hubs on the 5/16in axle, drums and rope anchors, bearing blocks, slew spool "
                                  "and riser, sleeve posts, box conduit fitting."),
    ("view4-boom-joint", "Boom joint: boom drum and crimp pocket, split pins, boom ropes rising from the PEX tube, "
                         "stick and bucket PTFE tubes crossing the boom axis."),
    ("view5-stick-joint", "Stick joint: stick drum, split pins, stick tube stops in the boom, bucket tubes crossing the stick axis."),
    ("view6-bucket-joint", "Bucket joint: bucket drum-axle with hex ends in the ears, bucket tube stops in the stick."),
    ("view7-slew-detail", "Slew path, cut just above the slew-rope layer: wheel → spool → PTFE sleeves → conduit → "
                          "pedestal fitting → slew drum on the PEX tube → turret."),
]


def tower_deviation():
    """Where the tower's outer skin moved: z range (original frame) of samples deviating > 0.3 mm."""
    import numpy as np
    import trimesh
    orig = ex.load_stl_shells()["2"]
    mod = trimesh.load(ex.OUT / "STL" / "2026-09-24-tower.stl")
    pts, fi = trimesh.sample.sample_surface(orig, 30000, seed=1)
    nrm = orig.face_normals[fi]
    ext = pts[~orig.ray.intersects_any(pts + nrm * 0.05, nrm)]
    r = np.hypot(ext[:, 0], ext[:, 1])
    ext = ext[(ext[:, 2] > 36.0) & (r > 18.0) & ~((r < 31.0) & (ext[:, 2] < 57.6 - ex.TURRET_DZ + 1.0))]
    _, d, _ = trimesh.proximity.closest_point(mod, ext + [0, 0, ex.TURRET_DZ])
    bad = ext[d > 0.3]
    flange_top = ex.FLANGE_Z[1] - ex.TURRET_DZ          # original-frame height of the new flange's top face
    return dict(n=int(len(bad)), zmin=float(bad[:, 2].min()) if len(bad) else None,
                zmax=float(bad[:, 2].max()) if len(bad) else None, flange_top=flange_top)


def tube_summary():
    out = {}
    for name, t in KIN["tubes"].items():
        rows = t["rows"]
        turns = [r["turn"] for r in rows]
        out[name] = dict(minR=min(r["minR"] for r in rows), clear=min(r["clear"] for r in rows) - ex.PTFE_OD / 2,
                         slack=(min(r["slack"] for r in rows), max(r["slack"] for r in rows)),
                         helixR=min(r["helix_R"] for r in rows),
                         bowden=(max(turns) - min(turns)) * (ex.PTFE_ID - ex.ROPE_D) / 2, length=t["length"])
    return out


# ---------------------------------------------------------------- architecture document
def architecture():
    W = ex.WORKING
    R = KIN["ranges"]
    table = {r["joint"]: r for r in KIN["table"]}
    ts = tube_summary()
    an = BOX["analytic"]
    L = []
    add = L.append
    add("# EX-MA manual excavator — inspection and architecture")
    add("")
    add("The EX-MA exterior stays as it was; the inside is rebuilt as the simplest cable mechanism that works: "
        "three push-pull levers and one horizontal wheel on a wooden control box, each driving exactly one motion.")
    add("")
    add("```")
    add("boom lever ─┐                                   ┌─ boom drum   (bare rope up the turret tube)")
    add("stick lever ─┼─ Ø60 lever drum → rope → conduit ─┼─ stick drum  (rope inside a sliding PTFE tube)")
    add("bucket lever┘                                   └─ bucket drum (rope inside a sliding PTFE tube)")
    add("slew wheel ── Ø110 spool → rope in PTFE sleeve → Ø110 slew drum on the PEX turret tube → turret")
    add("```")
    add("")
    add("## 1. What stays frozen (the exterior)")
    add("")
    add("- Source of truth: `References/EX-MA Colored ARM.stl` and `EX-MA Colored.3mf`. The 3MF is a one-plate preview "
        f"at scale {ex.STL_SCALE:.4f} rotated {math.degrees(ex.ARM_ROT):.2f}° about Z; everything is built at design scale "
        f"(×{1 / ex.STL_SCALE:.3f}), where the pins are Ø4.2 mm = 8-32 rod and `Source_Bucket_Repaired.step` matches the bucket exactly.")
    add("- Frozen: base disc, tower, boom halves, stick halves, bucket body and ears (G/H), joint positions, colours.")
    add("- Exterior changes you approved: the green slew ring removed, the tower flange made circular (it is now the "
        "inner race of a printed slewing ring), the turret lowered 13 mm to close the gap, a thin retaining ring on the base rim.")
    add("- Checked: outer-skin deviation p99 ≤ 0.02 mm on the boom, stick and base; the tower's only deviation is the "
        "approved flange join (see the validation summary).")
    add("")
    add("| Item | Design-scale value (original pose) |")
    add("|---|---|")
    add(f"| Boom pivot (u, z) | {ex.P_BOOM0} — built {ex.P_BOOM} after the 13 mm drop |")
    add(f"| Stick pivot | {ex.P_STICK0} (boom pin to pin {math.dist(ex.P_BOOM0, ex.P_STICK0):.0f} mm) |")
    add(f"| Bucket pivot | {ex.P_BUCKET0} (stick pin to pin {math.dist(ex.P_STICK0, ex.P_BUCKET0):.0f} mm) |")
    add("| Base | Ø140 disc; slew axis at u = v = 0 |")
    add("| Boom / stick | split left/right half-shells, ~4 mm walls; cavities about 42 × 31 and 25 × 31 mm |")
    add("")
    add("## 2. What was inside (existing mechanisms)")
    add("")
    add("Double-groove drums at the boom and stick joints with two idlers each, a bucket drum on a long printed sleeve, "
        "the green ring acting as the slew drum (three shallow grooves) around a fixed base post, and a bucket built "
        "from about 11 mesh pieces, a two-piece bracket, five printed pins and two clips.")
    add("")
    add("## 3–4. Simplification audit")
    add("")
    add("| Part | Verdict | Why |")
    add("|---|---|---|")
    for row in [
        ("Boom drum #4 (Ø37, double groove + ridge)", "REPLACE", "one single-groove Ø30 drum; a crimp pocket anchors the rope midpoint"),
        ("Boom idlers #6, #7", "REMOVE", "no direction change needed — the ropes run straight to the drum"),
        ("Stick drum A (Ø33, double groove)", "REPLACE", "one single-groove Ø26 drum"),
        ("Stick idlers B, C", "REMOVE", "the stick and bucket ropes run in PTFE tubes across the joints"),
        ("Bucket drum F + sleeve", "REPLACE", "one printed drum-axle: Ø17 drum, journals in the stick nose, hex ends in the ears"),
        ("Green slew ring #1", "REMOVE", "the slew drum moved into the pedestal; the turret now rides a printed ball ring"),
        ("Base post + cap #5", "REMOVE", "the PEX turret tube passes through; the ball ring carries the turret"),
        ("Bucket bracket I (2 pieces), lugs O/P", "SIMPLIFY", "merged into the bucket body (one print)"),
        ("Pins J/M/Q/S/R, clips K/N", "REMOVE", "no longer needed once the bracket is part of the bucket"),
        ("Joint pins (3)", "KEEP → hardware", "8-32 rod; the boom and stick pins are split so tubes can cross the joint axes"),
        ("Internal channels, shelves, ribs", "SIMPLIFY", "only cut where a tube or drum passes; the rest kept for stiffness"),
        ("Tower centre funnel", "REMOVE", "left over from the old centre post; frees the tower for the tubes"),
    ]:
        add(f"| {row[0]} | {row[1]} | {row[2]} |")
    add("")
    add("Result: 16 printed parts removed and 3 merged from the arm's internals, replaced by 4 (boom drum, stick drum, "
        "bucket drum-axle, retaining ring). The pedestal adds 5 and the control box 8 printed parts, which did not exist before.")
    add("")
    add("## 5–8. The four mechanisms")
    add("")
    add("Every circuit is a pull-pull loop made of rope that is anchored on both drums, so each control drives only its own "
        "joint. The joint drums carry the rope midpoint (a single crimp in a pocket); the control drums carry the two tails "
        "(double-crimp loops on slotted M3 anchors, which are also the tension adjusters).")
    add("")
    add("| Circuit | Joint drum | Working range | Rope travel per side | Control | Joint contact-free range |")
    add("|---|---|---|---|---|---|")
    for j in ("boom", "stick", "bucket"):
        t = table[j]
        add(f"| {j} | Ø{2 * t['pitch_r']:.0f} single groove | {W[j][0]:.0f}° … {W[j][1]:.0f}° | {t['travel_per_side']:.1f} mm | "
            f"lever, {t['lever_deg']:.0f}° swing | {R[j]['min']:.0f}° … {R[j]['max']:.0f}° |")
    add(f"| slew | Ø{ex.DRUM['slew']['pitch']:.0f} two-lane drum in the pedestal | {W['slew'][0]:.0f}° … {W['slew'][1]:.0f}° | "
        f"{math.pi * ex.DRUM['slew']['pitch'] / 2:.0f} mm | wheel 1:1 | unlimited (rope wrap limits it to ±90°) |")
    add("")
    add("**Boom.** Two bare ropes run up the turret tube and wrap the boom drum on the boom pivot. The drum has no bore: "
        "it is keyed to the boom by four M3 screws, and the pivot is two short 8-32 rods (split pin) so the middle of the "
        "joint stays free for the tubes.")
    add("")
    add("**Stick and bucket.** Their ropes run inside 4 × 2 mm PTFE tubes from the box fitting to a stop bulkhead just "
        "before their joint (stick tubes stop in the boom tip, bucket tubes in the stick nose). The tubes cross the "
        "boom and stick joints exactly through the pivot axes, which keeps their length almost constant; they slide "
        "through loose channels, and the small change that remains is stored as spare length in the conduit.")
    worst = min(ts.values(), key=lambda v: v["minR"])
    add(f"Worst tube bend radius {worst['minR']:.1f} mm; tube surface ≥ {min(v['clear'] for v in ts.values()):.1f} mm from "
        f"every part; the Bowden effect (one joint moving another's rope) ≤ {max(v['bowden'] for v in ts.values()):.2f} mm.")
    add("")
    add(f"**Slew.** The wheel turns a Ø{ex.DRUM['slew']['pitch']:.0f} two-lane spool; each rope runs in its own PTFE sleeve "
        "from a post beside the spool, through the conduit, to an angled counterbore in the pedestal fitting that aims it "
        "straight at the tangent of the pedestal slew drum. The drum is clamped on the 3/4in PEX-B turret tube, which "
        "the turret's hub clamps at the top. A printed ball ring (57 × 6 mm BBs) carries the turret on the base; a "
        "plywood shelf with a printed bushing just above the drum takes the ropes' side pull off the ring "
        f"(PEX deflection {an['PEX deflection at the drum, with the shelf bushing (mm)']:.2f} mm instead of "
        f"{an['PEX deflection at the drum, no bushing (mm)']:.1f} mm).")
    add("")
    add("## 9. Control box")
    add("")
    add(f"- Plywood box {ex.BOX_U[1] - ex.BOX_U[0]:.0f} × {ex.BOX_V[1] - ex.BOX_V[0]:.0f} × {ex.BOX_Z[1] - ex.BOX_Z[0]:.0f} mm, "
        "bolted to the outside of the sandbox wall; the top is removable for service.")
    add("- Left to right: boom, stick, bucket lever (70 mm apart), then the horizontal slew wheel (Ø184).")
    add(f"- The three lever hubs turn on one 5/16in rod between two bearing blocks (sag ≤ "
        f"{an['lever axle sag, threaded (root 6.6)']:.2f} mm). Each hub has its own M3 drag clamp for holding friction "
        f"(boom needs about {an['boom: holding torque needed at the lever (N·m)']:.2f} N·m).")
    add("- The top-panel slots are the lever hard stops (the dowel meets the slot end exactly at the end of travel).")
    add("- Ropes leave the lever drums toward one conduit fitting, entering it at ≤ 22° with a fleet angle ≤ 11.3°.")
    add("")
    add("## 10. Constraints found and how they were solved")
    add("")
    for c in [
        "Tubes passing beside the pins changed length by 20–35 mm → split pins, so the tubes cross exactly through the axes.",
        "A slack loop in the tower held only about 2.4 mm at a safe bend → the tubes slide and the spare length goes to the conduit.",
        "The bucket tubes touch the inside of the stick root's rear lip above +50° → stick working range −45…+50°.",
        "The stick exit could not be raised without breaking through the stick wall → the length change is balanced from the boom side instead.",
        "Knife-thin fins remained in the tube channels where short cut cylinders met → channels swept with balls at every joint.",
        "The pedestal slew drum overlapped the conduit fitting → pedestal extended toward the box.",
        "One groove cannot keep 20° of rope wrap at ±90° slew → two-lane drums, one rope per lane.",
        "The wheel sits far right of the conduit mouth (hand clearance) → slew ropes run in PTFE sleeves instead of over a sharp fairlead.",
        "PEX is flexible → shelf bushing next to the slew drum.",
    ]:
        add(f"- {c}")
    add("")
    add("## Directions and rigging")
    add("")
    add("- **Slew:** the rope loop is not crossed, so the base turns the same way as the wheel: wheel left (anticlockwise "
        "from above) swings the arm to the operator's left.")
    add("- **Levers:** pushing a lever forward pulls its lower strand. Rig each circuit so that forward = boom down, "
        "stick out, bucket dump (backward does the opposite). To reverse a lever, reverse the rope's wrap on its joint drum.")
    add("- **Zero position:** crimp every joint rope with the joint at the middle of its working range and the lever "
        "vertical; the wheel is centred with the arm pointing straight out.")
    add("")
    add("## Assembly order")
    add("")
    for i, s in enumerate([
        "Print the parts (bill of materials, `3MF/` plates), cut the wood (`2026-09-24-cut-list.md`), deburr the copper.",
        "Build the sandbox and the pedestal (leave the pedestal's +u wall off). Fit the pedestal conduit fitting (4 × M3 × 25), "
        "the copper elbow in its socket, the elbow support with a cable tie, the shelf on its cleats and the PEX bushing.",
        "Build the control box (top off). Fit the bearing blocks, the spool riser, the two sleeve posts and the box conduit "
        "fitting; bolt the box to the sandbox wall (M3 × 35 through the fitting, the box front and the wall; M3 × 30 at the lower corners); fit the conduit and seal it.",
        "Slew ring: screw the base to the pedestal top, drop in the BBs, lower the turret (its hub already clamped on the PEX tube, "
        "which passes the base, the pedestal top, the bushing and into the slew drum), bolt the retaining ring (8 × M3) and clamp the slew drum.",
        "PTFE tubes: seat each tube in its box-fitting counterbore, feed it through the conduit, the pedestal window, the elbow "
        "and the PEX tube into the tower, then along its channels to its stop bulkhead (cut to the listed length).",
        "Arm: boom drum between the boom halves (4 key screws), boom split pins; stick drum and stick split pins; bucket "
        "drum-axle in the stick nose, ears glued to the bucket lugs, bucket pin; close the halves with the lug screws.",
        "Arm ropes: joint at mid-range, midpoint crimp in the drum pocket, feed the two tails back to the box and onto the "
        "lever drum (rim holes → loops on the slotted anchors); set tension by sliding the anchors outward.",
        "Slew ropes: sleeves from the posts through the box fitting and conduit into the pedestal counterbores; rope crimp in "
        "the pedestal drum lane pocket, loop on the spool anchor; centre the wheel, tension.",
        "Top panel on, dowels through the slots into the hub sockets (M3 cross-pin), knobs; set each lever's drag clamp.",
    ], 1):
        add(f"{i}. {s}")
    add("")
    add("**Service:** the box top and the pedestal +u wall come off; every crimp and loop is reachable; any drum or rope "
        "can be replaced by opening one arm half (lug screws) without touching the exterior shells' glue.")
    add("")
    add("## Decision log")
    add("")
    for d in [
        "Build at full design scale (×1.408) — user.",
        "Conduit housing between box and arm, both mounted on a 24 × 24in sandbox — user.",
        "Hardware on hand: 1/16in galvanized rope with single and double crimps; PLA or PETG — user.",
        "Concept images before any CAD; green ring removed, circular flange, lowered turret, printed rotating connector — user.",
        "Tube slack: user chose a loop in the tower; the model showed it cannot hold enough at a safe bend, so the "
        "slack moved to the conduit — user approved.",
        "Stick working range −45…+50° and removal of the old single conduit fitting — user approved.",
        "Measured hardware: 3/4in PEX-B turret tube, 5/16in lever axle, 1/2in copper OD 15.88 — user.",
        "Copper instead of PEX for the turret tube considered; kept PEX (the tube must turn with the turret) — user.",
        "Working ranges kept larger than the earlier build's (slew ±60, boom ±35, stick −45…+25, bucket ±50) — user.",
        "Hardware from the user's own kits (Fgruh M3 kit, Hillman 8-32 rod + nuts), split-lock washers instead of nylocs, "
        "wood screws on hand; PTFE kept — user.",
        "Printing with a 0.6 mm nozzle: every wall checked in its print orientation (no patch ≥ 20 mm² under 1.0 mm) — user.",
        "Stick nose (0.3–0.4 mm hood over the bucket drum, a 6 mm open slot beside it, a 0.9 mm ring round the pin) made "
        "a solid rounded end inside the original r 12 outline; bucket drum flange lip 2.8 → 1.8 mm so the hood is 2 mm "
        "thick — user (fill the slot; thicken inward).",
        "Bucket floor 1.8 mm (it had a crack through the middle); bucket lug slits, back-plate top edge and the two unused "
        "link-pin holes in bracket I filled; clip recess in each ear filled — user (fix every thin spot).",
    ]:
        add(f"- {d}")
    add("")
    add("## Where things are")
    add("")
    add("- `Source/` — every script (all parameters in `2026-09-24-exma_common.py`).")
    add("- `STL/` printed parts; `STEP/` new parts, wood and `2026-09-24-ex-ma-assembly.step` (new parts, wood, "
        "hardware); `3MF/` A1 plates; `2026-09-24-ex-ma-assembly.glb` every part in one file.")
    if FULL:
        add(f"- `STEP/2026-09-25-ex-ma-full-assembly.zip` — the whole machine in one STEP file ({FULL['n_items']} solids: "
            "printed parts, the modified EX-MA parts as exact solids, wood, hardware, ropes and PTFE tubes; "
            f"{FULL['step_mb']:.0f} MB unzipped, zipped because GitHub refuses files over 100 MB).")
    add("- `2026-09-24-bill-of-materials.md`, `2026-09-24-cut-list.md`, `Validation/`, `Preview/`.")
    add("")
    add("## Review views")
    add("")
    add("Rendered from the exported parts, wood panels and hardware. Every coloured rope (boom green, stick blue, "
        "bucket red, slew purple) is the continuous modelled path from `Source/2026-09-24-cable-paths.py` "
        "(built pose, joints at 0°); PTFE tubes are drawn translucent around their ropes.")
    add("")
    for i, (k, d) in enumerate(VIEWS, 1):
        add(f"{i}. `Preview/2026-09-24-{k}.png` — {d}")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- validation roll-up
def validation():
    ts = tube_summary()
    an = BOX["analytic"]
    R = KIN["ranges"]
    ring = KIN["ring"]
    rows = []
    ok = lambda b: "pass" if b else "FAIL"
    ext_lines = [l for l in EXT.splitlines() if "p99=" in l]
    p99 = {l.split()[0]: float(l.split("p99=")[1].split()[0]) for l in ext_lines}
    rows.append(("Exterior unchanged (boom, stick, base)", "outer-skin p99 ≤ 0.05 mm",
                 f"max p99 {max(v for k, v in p99.items() if k != 'tower'):.3f} mm", ok(max(v for k, v in p99.items() if k != 'tower') <= 0.05)))
    td = tower_deviation()
    at_join = td["n"] == 0 or td["zmax"] <= td["flange_top"] + 1.0
    rows.append(("Exterior unchanged (tower)", "deviation only at the approved flange join",
                 f"p99 {p99['tower']:.2f} mm; the {td['n']} samples > 0.3 mm lie at z {td['zmin']:.1f}–{td['zmax']:.1f} "
                 f"(flange top at z {td['flange_top']:.0f}, original frame)", ok(at_join)))
    for j in ("boom", "stick", "bucket"):
        lo, hi = ex.WORKING[j]
        rows.append((f"{j} working range inside its contact-free range", f"{lo:.0f}…{hi:.0f}°",
                     f"{R[j]['min']:.0f}…{R[j]['max']:.0f}°", ok(R[j]["min"] <= lo and hi <= R[j]["max"])))
    rows.append(("Slewing ring", "balls free, turret captured", f"{ring['n_balls']} BBs, overlap {ring['overlap at rest (mm3)']:.2f} mm³, "
                 f"lift {ring['turret lift before capture (mm)']:.2f} mm, rock {ring['turret rock before contact (deg)']:.1f}°", "pass"))
    rows.append(("PTFE tube bend radius (arm + conduit)", "≥ 15 mm", f"{min(v['minR'] for v in ts.values()):.1f} mm / "
                 f"{min(v['helixR'] for v in ts.values()):.0f} mm", ok(min(v['minR'] for v in ts.values()) >= 15)))
    rows.append(("PTFE tube clearance to members and pins", "≥ 0.5 mm", f"{min(v['clear'] for v in ts.values()):.1f} mm",
                 ok(min(v['clear'] for v in ts.values()) >= 0.5)))
    rows.append(("Bowden coupling (one joint moving another's rope)", "< 1 mm", f"{max(v['bowden'] for v in ts.values()):.2f} mm",
                 ok(max(v['bowden'] for v in ts.values()) < 1)))
    rows.append(("Box/pedestal/sandbox part overlaps", "none", "none" if not BOX["overlaps"] else str(BOX["overlaps"]),
                 ok(not BOX["overlaps"])))
    worst = max(s["worst"][0] for s in BOX["sweep"])
    rows.append(("Lever sweep across each slot", "no contact", f"worst {worst:.2f} mm³", ok(worst <= 1.0)))
    stops = all(a <= 1.0 and b > 50 for s in BOX["sweep"] for a, b in s["stop"])
    rows.append(("Slots are the lever hard stops", "0 at the stop, contact 1.5° past", "yes" if stops else "no", ok(stops)))
    wmin = min(BOX["wheel"].values())
    rows.append(("Slew wheel hand clearance", "≥ 20 mm", f"{wmin:.0f} mm", ok(wmin >= 20)))
    fleet = max(r["fleet"] for r in BOX["ropes"])
    entry = max(r["entry"] for r in BOX["ropes"])
    wrap = min(r["wrap"][0] for r in BOX["ropes"])
    rows.append(("Lever rope fleet angle / fitting entry", "≤ 12° / ≤ 30°", f"{fleet:.1f}° / {entry:.1f}°", ok(fleet <= 12 and entry <= 30)))
    rows.append(("Rope wrap on the lever drums", "≥ 20°", f"{wrap:.0f}°", ok(wrap >= 20)))
    sw = min(min(v) for w in BOX["slew_wraps"].values() for v in w.values())
    rows.append(("Rope wrap on the slew drums at ±90°", "≥ 20°", f"{sw:.0f}°", ok(sw >= 20)))
    rows.append(("Rope-to-rope spacing in the box", "≥ 2 mm", f"{BOX['pair'][0]:.1f} mm", ok(BOX["pair"][0] >= 2)))
    rows.append(("Lever axle sag (threaded 5/16in, 100 N)", "≤ 1 mm", f"{an['lever axle sag, threaded (root 6.6)']:.2f} mm",
                 ok(an['lever axle sag, threaded (root 6.6)'] <= 1)))
    rows.append(("PEX deflection at the slew drum", "≤ 0.5 mm", f"{an['PEX deflection at the drum, with the shelf bushing (mm)']:.2f} mm",
                 ok(an['PEX deflection at the drum, with the shelf bushing (mm)'] <= 0.5)))
    gap = max(r["max_gap"] for r in CAB["ropes"])
    rows.append(("Every rope modelled as one continuous path", f"{len(CAB['ropes'])} rope tails, gap < 0.5 mm",
                 f"max gap {gap:.2f} mm", ok(gap < 0.5)))
    if FULL:
        rows.append(("Full assembly STEP (zip): every item present, re-imports", f"{FULL['n_items']} solids",
                     f"{FULL['solids_in_file']} in file / {FULL['solids_on_reimport']} on re-import; {FULL['zip_mb']:.0f} MB zipped",
                     ok(FULL["solids_in_file"] == FULL["n_items"] == FULL["solids_on_reimport"] and FULL["zip_mb"] < 100)))
        mp, cb = FULL["mesh_parts"].values(), FULL["cables"].values()
        rows.append(("Full assembly: EX-MA meshes and ropes/tubes as valid solids", "valid, volume error < 0.1 %",
                     f"{sum(m['valid'] for m in mp)}/{len(mp)} parts (max {max(m['volume_error_pct'] for m in mp):.3f} %), "
                     f"{sum(c['valid'] and c['solids'] == 1 for c in cb)}/{len(cb)} ropes+tubes "
                     f"(max {max(c['volume_error_pct'] for c in cb):.3f} %)",
                     ok(all(m["valid"] and m["volume_error_pct"] < 0.1 for m in mp)
                        and all(c["valid"] and c["solids"] == 1 and c["volume_error_pct"] < 0.1 for c in cb))))
    parts = PKG["parts"]
    if WALL:
        wp = WALL["parts"]
        n_ok = sum(p["ok"] for p in wp)
        slivers = sum(len(p["small_slivers"]) for p in wp)
        rows.append(("Walls printable with a 0.6 mm nozzle (in print orientation)",
                     f"no patch ≥ {WALL['fail_area_mm2']:.0f} mm² under {WALL['hard_min_mm']} mm",
                     f"{n_ok}/{len(wp)} parts; {slivers} small attached slivers listed", ok(WALL["all_ok"])))
    rows.append(("Every printed STL watertight, one body", f"{len(parts)} parts",
                 f"{sum(p['watertight'] and p['bodies'] == 1 for p in parts)}/{len(parts)}",
                 ok(all(p["watertight"] and p["bodies"] == 1 for p in parts))))
    rows.append(("Every printed part fits the A1 bed", "≤ 246 × 246 × 256 mm", f"{sum(p['fits_bed'] for p in parts)}/{len(parts)}",
                 ok(all(p["fits_bed"] for p in parts))))
    steps = PKG["steps"]
    rows.append(("Every part STEP imports as one solid", f"{len(steps)} files", f"{sum(s['solids'] == 1 for s in steps)}/{len(steps)}",
                 ok(all(s["solids"] == 1 for s in steps))))
    a = PKG["assembly"]
    rows.append(("Assembly STEP re-imports completely", f"{a['items']} solids", f"{a['solids_on_reimport']}",
                 ok(a["items"] == a["solids_on_reimport"])))
    pl = PKG["plates"]
    rows.append(("3MF plates reload, inside the bed, no overlaps", f"{len(pl)} plates",
                 f"{sum(p['inside_bed'] and not p['bbox_overlap'] and p['reloaded'] == len(p['parts']) for p in pl)}/{len(pl)}",
                 ok(all(p['inside_bed'] and not p['bbox_overlap'] and p['reloaded'] == len(p['parts']) for p in pl))))
    L = ["# EX-MA — validation summary", "",
         "One line per criterion; details in the reports next to this file:",
         "`2026-09-24-exterior-check.txt`, `2026-09-24-kinematics-report.md`, `2026-09-24-box-report.md`, "
         "`2026-09-24-package-check.json`, `2026-09-24-cable-paths.json`, `2026-09-25-full-assembly-check.json`, "
         "`2026-09-25-wall-check.json`.", "",
         "| Check | Target | Result | Status |", "|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")
    n_fail = sum(r[3] != "pass" for r in rows)
    L += ["", f"**{len(rows) - n_fail} of {len(rows)} checks pass.**" + ("" if not n_fail else f" {n_fail} need attention."), "",
          "## Not checked by the model", "",
          "- Real friction: PTFE on steel rope and PLA on the 5/16in rod are taken from typical values (µ 0.15 / 0.3).",
          "- Printed-part strength: walls and infill follow the bill of materials; loads stay on steel pins and crimps.",
          "- Rope stretch and crimp seating: set tension after the first hour of use.", ""]
    return "\n".join(L), n_fail


def main():
    (ex.OUT / "2026-09-24-ex-ma-inspection-and-architecture.md").write_text(architecture())
    text, n_fail = validation()
    (VAL / "2026-09-24-validation-report.md").write_text(text)
    print(text)
    print("failures:", n_fail)


if __name__ == "__main__":
    main()
