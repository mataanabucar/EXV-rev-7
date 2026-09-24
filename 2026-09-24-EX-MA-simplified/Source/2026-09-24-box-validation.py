#!/usr/bin/env python3
"""EX-MA B5 validation: control box, pedestal and sandbox.

Writes Validation/2026-09-24-box-report.md (+ -box-data.json) and prints the report.
"""
import importlib.util
import itertools
import json
import math
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
ex, rt = asm.ex, asm.rt
CONTACT_MM3 = 1.0
ROPE_R = ex.ROPE_D / 2
SLEEVE_R = ex.PTFE_OD / 2
MU_PTFE = 0.15                     # steel rope in PTFE, conservative


def M(mesh):
    return ex.to_manifold(mesh)


def moved(mesh, T):
    m = mesh.copy()
    m.apply_transform(T)
    return m


def panel_meshes():
    out = {}
    for p in bx.panels():
        out[p.name] = (ex.shape_to_mesh(bx.panel_solid(p).val(), tol=0.1), p.group)
    return out


BOX_PRINTED = ["lever-hub-boom", "lever-hub-stick", "lever-hub-bucket", "slew-spool", "slew-wheel", "spool-riser",
               "slew-tube-post@A", "slew-tube-post@B", "conduit-end-fitting-box"]
PED_PRINTED = ["slew-drum", "conduit-end-fitting-pedestal", "slew-tube-bushing", "elbow-support"]
# designed contacts (face-to-face or shaft-in-bore): excluded from the overlap test
CONTACTS = {
    frozenset(p) for p in [
        ("conduit-end-fitting-box", "box front"), ("conduit-end-fitting-box", "2in PVC conduit"),
        ("conduit-end-fitting-pedestal", "pedestal wall -u (conduit)"),
        ("conduit-end-fitting-pedestal", "2in PVC conduit"), ("conduit-end-fitting-pedestal", "1/2in copper elbow"),
        ("slew-tube-bushing", "pedestal shelf"), ("slew-tube-bushing", "3/4in PEX turret tube"),
        ("slew-drum", "3/4in PEX turret tube"), ("elbow-support", "1/2in copper elbow"),
        ("spool-riser", "box floor"), ("spool-riser", "slew spool axle (5/16in rod)"),
        ("slew-spool", "slew spool axle (5/16in rod)"), ("slew-wheel", "slew spool axle (5/16in rod)"),
        ("slew-spool", "slew-wheel"), ("slew-spool", "box top (removable)"),
        ("slew spool axle (5/16in rod)", "box floor"), ("slew spool axle (5/16in rod)", "box top (removable)"),
        ("lever axle (5/16in rod)", "axle bearing block left"), ("lever axle (5/16in rod)", "axle bearing block right"),
        ("lever axle (5/16in rod)", "lever-hub-boom"), ("lever axle (5/16in rod)", "lever-hub-stick"),
        ("lever axle (5/16in rod)", "lever-hub-bucket"),
        ("2in PVC conduit", "box front"), ("2in PVC conduit", "sandbox wall -u (box side)"),
        ("2in PVC conduit", "pedestal wall -u (conduit)"),
        ("pedestal shelf", "pedestal shelf cleat -v"), ("pedestal shelf", "pedestal shelf cleat +v"),
        ("3/4in PEX turret tube", "pedestal top"), ("3/4in PEX turret tube", "pedestal shelf"),
        ("1/2in copper elbow", "3/4in PEX turret tube"),
        ("slew-tube-post@A", "box floor"), ("slew-tube-post@B", "box floor"),
        ("elbow-support", "sandbox floor"),
    ]
}
for j in ("boom", "stick", "bucket"):
    CONTACTS.add(frozenset((f"{j} handle", f"lever-hub-{j}")))


def static_parts():
    parts = {}
    for n in BOX_PRINTED + PED_PRINTED:
        parts[n] = asm.part(n)
    for n, (m, g) in panel_meshes().items():
        parts[n] = m
    for n, (m, c) in bx.hardware().items():
        parts[n] = m
    return parts


def overlaps(parts):
    """Pairwise solid overlap (mm3) of every part pair, excluding designed contacts. Meshes that are
    not closed volumes (swept pipes) are tested by vertex distance instead."""
    mans, loose = {}, {}
    for n, m in parts.items():
        try:
            mans[n] = M(m)
        except Exception:
            loose[n] = m
    bad = []
    names = list(mans)
    boxes = {n: parts[n].bounds for n in parts}
    for a, b in itertools.combinations(names, 2):
        if frozenset((a, b)) in CONTACTS:
            continue
        A, B = boxes[a], boxes[b]
        if np.any(A[1] < B[0] - 0.1) or np.any(B[1] < A[0] - 0.1):
            continue
        v = (mans[a] ^ mans[b]).volume()
        if v > CONTACT_MM3:
            bad.append((a, b, round(v, 1)))
    for a, m in loose.items():
        pts = m.vertices[::3]
        for b in names:
            if frozenset((a, b)) in CONTACTS:
                continue
            A, B = m.bounds, boxes[b]
            if np.any(A[1] < B[0] - 0.1) or np.any(B[1] < A[0] - 0.1):
                continue
            inside = parts[b].contains(pts) if parts[b].is_watertight else np.zeros(len(pts), bool)
            if inside.sum() > 3:
                bad.append((a, b, f"{int(inside.sum())} pts inside"))
    return bad, list(loose)


# ---------------------------------------------------------------- lever sweep
def lever_sweep(parts):
    rows = []
    others = {n: M(m) for n, m in parts.items()
              if not n.startswith("lever-hub") and "handle" not in n and n != "lever axle (5/16in rod)"
              and n not in ("2in PVC conduit",)}
    hubs = {j: asm.part(f"lever-hub-{j}") for j in ex.LEVERS}
    top = M(parts["box top (removable)"])
    for j in ex.LEVERS:
        half = bx.lever_deg(j) / 2
        worst = (0.0, "")
        angles = list(np.arange(-half, half + 1e-6, 2.0)) + [half]
        for d in angles:
            T = bx.lever_pose_T(j, d)
            hub = M(moved(hubs[j], T))
            handle = M(bx.lever_handle_mesh(j, 0.0)).transform(T[:3, :4].tolist())
            for n, o in others.items():
                for nm, body in ((f"lever-hub-{j}", hub), (f"{j} handle", handle)):
                    if frozenset((nm, n)) in CONTACTS:
                        continue
                    v = (body ^ o).volume()
                    if v > worst[0]:
                        worst = (v, f"{nm} vs {n} at {d:+.1f} deg")
            # other hubs at both of their extremes
            for k in ex.LEVERS:
                if k == j:
                    continue
                for dk in (-bx.lever_deg(k) / 2, bx.lever_deg(k) / 2):
                    ok = M(moved(hubs[k], bx.lever_pose_T(k, dk)))
                    v = (hub ^ ok).volume()
                    if v > worst[0]:
                        worst = (v, f"hub {j} {d:+.1f} vs hub {k} {dk:+.1f}")
        # hard stop: the dowel touches the slot end at +-half; 1.5 deg further it cuts into the top
        stop = []
        for sgn in (1, -1):
            h_at = (M(bx.lever_handle_mesh(j, sgn * half)) ^ top).volume()
            h_past = (M(bx.lever_handle_mesh(j, sgn * (half + 1.5))) ^ top).volume()
            stop.append((h_at, h_past))
        rows.append(dict(lever=j, swing=2 * half, worst=worst, stop=stop, slot=bx.slot_length(j)))
    return rows


_TREES = {}


def surface_tree(name, mesh, spacing=0.5):
    """KD-tree of dense surface samples (distance error < ~spacing/2); cached per part."""
    from scipy.spatial import cKDTree
    if name not in _TREES:
        n = int(min(400000, max(2000, mesh.area / spacing ** 2)))
        pts, _ = trimesh.sample.sample_surface(mesh, n, seed=3)
        _TREES[name] = cKDTree(np.vstack((pts, mesh.vertices)))
    return _TREES[name]


def dist_to(name, mesh, pts):
    """Unsigned distance of pts to the part's surface; negative where a point is inside the part."""
    d, _ = surface_tree(name, mesh).query(pts)
    if mesh.is_watertight:
        inside = mesh.contains(pts)
        d = np.where(inside, -d, d)
    return d


def wheel_clearance(parts):
    out = {}
    for j in ex.LEVERS:
        dmin = 1e9
        for d in (-bx.lever_deg(j) / 2, 0.0, bx.lever_deg(j) / 2):
            h = bx.lever_handle_mesh(j, d)
            pts, _ = trimesh.sample.sample_surface(h, 6000, seed=1)
            dmin = min(dmin, float(dist_to("slew-wheel", parts["slew-wheel"], pts).min()))
        out[j] = dmin
    return out


# ---------------------------------------------------------------- ropes and sleeves
def seg_pts(a, b, step=2.0):
    n = max(2, int(np.linalg.norm(b - a) / step) + 1)
    return np.linspace(a, b, n)


FAR = 15.0                         # beyond this the clearance is reported as "> 15 mm"


def clearance(pts, parts, skip):
    best = (FAR, "nothing within 15 mm")
    for n, m in parts.items():
        if n in skip:
            continue
        lo, hi = m.bounds
        near = np.all((pts > lo - 15) & (pts < hi + 15), axis=1)
        if not near.any():
            continue
        d = dist_to(n, m, pts[near])
        if d.min() < best[0]:
            best = (float(d.min()), n)
    return best


def seg_dist(p1, q1, p2, q2):
    """Minimum distance between two 3D segments (sampled)."""
    a, b = seg_pts(p1, q1, 1.0), seg_pts(p2, q2, 1.0)
    return float(np.min(np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)))


def rope_checks(parts):
    rows = []
    lines = []
    for j in ex.LEVERS:
        half = bx.lever_deg(j) / 2
        at = {d: bx.lever_strands(j, d) for d in (-half, 0.0, half)}
        for k in range(2):
            s0 = at[0.0][k]
            skip = {f"lever-hub-{j}", "conduit-end-fitting-box", "2in PVC conduit"}
            c, who = clearance(seg_pts(s0["tangent"], s0["hole"])[1:-2], parts, skip)
            rows.append(dict(name=s0["name"], fleet=s0["fleet_deg"], entry=s0["entry_deg"],
                             wrap=(min(at[d][k]["wrap_deg"] for d in at), max(at[d][k]["wrap_deg"] for d in at)),
                             clear=c - ROPE_R, clear_to=who, length=float(np.linalg.norm(s0["hole"] - s0["tangent"]))))
            lines.append((s0["name"], s0["tangent"], s0["hole"]))
    sleeves = {lane: bx.slew_sleeve(lane) for lane in "AB"}
    srows = []
    for lane, sl in sleeves.items():
        poly = sl["poly"]
        box_part = poly[poly[:, 0] < ex.BOX_U[1] - ex.T_WOOD - ex.FIT_T]
        skip = {f"slew-tube-post@{lane}", "conduit-end-fitting-box", "2in PVC conduit", "box front",
                "sandbox wall -u (box side)", "pedestal wall -u (conduit)", "conduit-end-fitting-pedestal"}
        c, who = clearance(box_part[1:], parts, skip)
        free_box, free_ped = bx.slew_rope_free(lane)
        cb, whob = clearance(seg_pts(*free_box)[1:-1], parts, {"slew-spool", f"slew-tube-post@{lane}"})
        cp, whop = clearance(seg_pts(*free_ped)[1:-1], parts, {"slew-drum", "conduit-end-fitting-pedestal"})
        srows.append(dict(lane=lane, length=sl["length"], turning=math.degrees(sl["turning"]),
                          friction=math.exp(MU_PTFE * sl["turning"]), clear=c - SLEEVE_R, clear_to=who,
                          rope_box_clear=cb - ROPE_R, rope_box_to=whob, rope_ped_clear=cp - ROPE_R, rope_ped_to=whop))
        for a, b in zip(box_part[:-1], box_part[1:]):
            lines.append((f"slew sleeve {lane}", a, b))
    # rope-rope / rope-sleeve distances (centreline minus radii)
    pair = (1e9, "")
    for (na, a1, a2), (nb, b1, b2) in itertools.combinations(lines, 2):
        if na == nb:
            continue
        ra = SLEEVE_R if "sleeve" in na else ROPE_R
        rb = SLEEVE_R if "sleeve" in nb else ROPE_R
        lo = np.minimum(np.minimum(a1, a2), np.minimum(b1, b2))
        d = seg_dist(a1, a2, b1, b2) - ra - rb
        # ignore where both converge into the fitting (last 6 mm before the fitting face)
        if min(a1[0], a2[0]) > ex.BOX_U[1] - ex.T_WOOD - ex.FIT_T - 6 and "sleeve" not in na + nb:
            continue
        if d < pair[0]:
            pair = (d, f"{na} / {nb}")
    return rows, srows, pair, sleeves


# ---------------------------------------------------------------- analytic
def analytic():
    out = {}
    # lever axle: simply supported between the bearing blocks, 100 N at mid-span
    span = 2 * (ex.AXLE_BLOCK_V[0] + ex.AXLE_BLOCK_V[1]) / 2
    P, E = 100.0, 200000.0
    for tag, d in (("plain 7.94", ex.LEVER_AXLE_D), ("threaded (root 6.6)", 6.6)):
        I = math.pi * d ** 4 / 64
        out[f"lever axle sag, {tag}"] = P * span ** 3 / (48 * E * I)
    # PEX turret tube under the slew ropes' side pull
    E_pex = 700.0
    I = math.pi * (ex.TURRET_TUBE_OD ** 4 - ex.TURRET_TUBE_ID ** 4) / 64
    T_rope = 30.0
    dirs = []
    for sign in (1, -1):
        L = ex.pedestal_slew_line(sign)
        v = L["exit"] - L["tangent"]
        dirs.append(v / np.linalg.norm(v))
    F = float(np.linalg.norm(T_rope * (dirs[0] + dirs[1])))
    z_drum, z_bush, z_ring = ex.Z_SLEW_LAYER, (asm.PED_SHELF_Z[0] + asm.PED_SHELF_Z[1]) / 2, ex.BALL_Z
    a, Lb = z_bush - z_drum, z_ring - z_bush
    out["slew side pull on the drum (N, 30 N per rope)"] = F
    out["PEX deflection at the drum, no bushing (mm)"] = F * (z_ring - z_drum) ** 3 / (3 * E_pex * I)
    out["PEX deflection at the drum, with the shelf bushing (mm)"] = F * a ** 2 * (Lb + a) / (3 * E_pex * I)
    out["radial load left on the slewing ring (N)"] = F * a / Lb
    out["moment on the slewing ring without the bushing (N·m)"] = F * (z_ring - z_drum) / 1000
    # lever holding torque: arm gravity about each joint at its worst pose
    rho = 1.24e-3 * 0.55            # g/mm3 x effective fill (4 walls + 40 % infill)
    g = 9.81e-3                     # N per g
    mem = {k: asm.member_mesh(k) for k in ("boom", "stick", "bucket")}
    mass = {k: m.volume * rho for k, m in mem.items()}
    com = {k: m.center_mass for k, m in mem.items()}
    piv = {"boom": np.array(ex.P_BOOM), "stick": np.array(ex.P_STICK), "bucket": np.array(ex.P_BUCKET)}
    chain = {"boom": ("boom", "stick", "bucket"), "stick": ("stick", "bucket"), "bucket": ("bucket",)}
    for j, members in chain.items():
        # worst case: every member's centre of mass horizontal from the joint (upper bound)
        tau = sum(mass[k] * g * np.linalg.norm(np.array([com[k][0], com[k][2]]) - piv[j]) for k in members) / 1000
        lever = tau * (ex.DRUM["lever"]["pitch"] / ex.DRUM[j]["pitch"])
        F_bolt = lever / (0.3 * math.pi * (ex.LEVER_AXLE_D / 2) / 1000)
        out[f"{j}: arm gravity torque at the joint, upper bound (N·m)"] = tau
        out[f"{j}: holding torque needed at the lever (N·m)"] = lever
        out[f"{j}: drag-clamp M3 bolt force for it (N, mu 0.3)"] = F_bolt
    out["arm masses (g, printed at ~55 % fill)"] = {k: round(float(v), 0) for k, v in mass.items()}
    return out


def cut_lengths():
    """Rope and PTFE cut lengths (mm) measured along the continuous modelled paths
    (2026-09-24-cable-paths.py), without crimp tails (add 60 mm per double-crimp loop)."""
    cp = _load("cp", "2026-09-24-cable-paths.py")
    P = cp.all_paths()
    L = {n: float(np.sum(np.linalg.norm(np.diff(cp.polyline(e), axis=0), axis=1))) for n, e in P.items()}
    out = {}
    for j in ("boom", "stick", "bucket"):
        out[f"{j} rope (one length, midpoint crimp)"] = L[f"{j} upper tail"] + L[f"{j} lower tail"]
    for n, e in P.items():
        if e.get("tube"):
            seg = e["ptfe"][0]
            out[f"PTFE {e['tube']} (box fitting -> arm stop)"] = float(np.sum(np.linalg.norm(np.diff(seg, axis=0), axis=1))) + 11.0
    for lane in "AB":
        out[f"PTFE slew sleeve {lane} (post -> pedestal fitting)"] = bx.slew_sleeve(lane)["length"] + 12.0
        out[f"slew rope {lane} (spool anchor -> pedestal crimp)"] = L[f"slew rope {lane}"]
    return out


def fmt_clear(v, who):
    return f"> {v:.0f} mm" if who.startswith("nothing") else f"{v:.1f} mm ({who})"


def main():
    parts = static_parts()
    bad, loose = overlaps(parts)
    sweep = lever_sweep(parts)
    wheel = wheel_clearance(parts)
    ropes, sleeves, pair, sleeve_geo = rope_checks(parts)
    an = analytic()
    wr = {sd: bx.slew_wraps(sd) for sd in (-90, 0, 90)}
    L = ["# EX-MA control box, pedestal and sandbox — validation (B5)", "",
         f"Solid overlap threshold {CONTACT_MM3} mm³. Designed contacts (shafts in bores, parts screwed face to "
         "face) are excluded from the overlap test.", "",
         "## Static overlap check (box, pedestal, sandbox, hardware)", ""]
    L.append("- No unintended overlaps." if not bad else "- Overlaps:\n" + "\n".join(f"  - {a} / {b}: {v}" for a, b, v in bad))
    if loose:
        L.append(f"- Swept meshes tested by vertex containment: {', '.join(loose)}.")
    L += ["", "## Lever sweep (2° steps across each slot)", "",
          "| Lever | Swing | Slot length | Worst overlap during the sweep | Dowel vs slot end at the stop / 1.5° past |",
          "|---|---|---|---|---|"]
    for r in sweep:
        w = f"{r['worst'][0]:.2f} mm³ ({r['worst'][1]})" if r["worst"][0] > 0 else "none"
        st = " ; ".join(f"{a:.2f} / {b:.0f} mm³" for a, b in r["stop"])
        L.append(f"| {r['lever']} | {r['swing']:.1f}° | {r['slot']:.1f} × {bx.SLOT_W:.1f} mm | {w} | {st} |")
    L += ["", "The slot is the hard stop: ~0 overlap at the end of travel and a clear overlap 1.5° further.", "",
          "## Slew wheel hand clearance", "",
          "| Lever | Closest approach of dowel/knob to the wheel over the lever swing |", "|---|---|"]
    for j, d in wheel.items():
        L.append(f"| {j} | {d:.0f} mm |")
    L += ["", "## Lever ropes in the box (drum tangent → box fitting hole)", "",
          "| Strand | Length | Fleet angle at the drum | Bend entering the fitting | Wrap left on the drum over the swing | Clearance to other parts |",
          "|---|---|---|---|---|---|"]
    for r in ropes:
        L.append(f"| {r['name']} | {r['length']:.0f} mm | {r['fleet']:.1f}° | {r['entry']:.1f}° | "
                 f"{r['wrap'][0]:.0f}–{r['wrap'][1]:.0f}° | {r['clear']:.1f} mm ({r['clear_to']}) |")
    L += ["", "## Slew circuit", "",
          "Each slew rope runs in its own PTFE sleeve from a post beside the box spool to an angled counterbore "
          "in the pedestal fitting that points along the pedestal drum's tangent; both drums have two lanes.", "",
          "| Sleeve | Length | Bends (total) | Friction factor e^(µθ), µ 0.15 | Sleeve clearance in the box | "
          "Bare rope spool→post | Bare rope pedestal exit→drum |", "|---|---|---|---|---|---|---|"]
    for r in sleeves:
        L.append(f"| {r['lane']} | {r['length']:.0f} mm | {r['turning']:.0f}° | {r['friction']:.2f} | "
                 f"{fmt_clear(r['clear'], r['clear_to'])} | {fmt_clear(r['rope_box_clear'], r['rope_box_to'])} | "
                 f"{fmt_clear(r['rope_ped_clear'], r['rope_ped_to'])} |")
    L += ["", "| Slew | Lane A wrap spool / pedestal | Lane B wrap spool / pedestal |", "|---|---|---|"]
    for sd, w in wr.items():
        L.append(f"| {sd:+d}° | {w['A'][0]:.0f}° / {w['A'][1]:.0f}° | {w['B'][0]:.0f}° / {w['B'][1]:.0f}° |")
    L += ["", f"Closest rope/sleeve pair in the box: {pair[0]:.1f} mm surface to surface ({pair[1]}).", "",
          "## Analytic checks", ""]
    for k, v in an.items():
        L.append(f"- {k}: {v:.2f}" if isinstance(v, float) else f"- {k}: {v}")
    cl = cut_lengths()
    L += ["", "## Cut lengths (measured along the modelled cable paths)", "",
          "Measured along the continuous paths in 2026-09-24-cable-paths.py, without crimp tails (the bill of materials adds 60 mm per double-crimp loop).", "",
          "| Item | Length |", "|---|---|"]
    for k, v in cl.items():
        L.append(f"| {k} | {v:.0f} mm |")
    rep = "\n".join(L) + "\n"
    out = ex.OUT / "Validation"
    (out / "2026-09-24-box-report.md").write_text(rep)
    (out / "2026-09-24-box-data.json").write_text(json.dumps(dict(
        overlaps=bad, sweep=sweep, wheel=wheel, ropes=ropes, sleeves=sleeves, pair=pair, analytic=an, cut_lengths=cl,
        slew_wraps={str(k): v for k, v in wr.items()},
        sleeve_paths={k: v["poly"].round(2).tolist() for k, v in sleeve_geo.items()}), indent=1, default=float))
    print(rep)


if __name__ == "__main__":
    main()
