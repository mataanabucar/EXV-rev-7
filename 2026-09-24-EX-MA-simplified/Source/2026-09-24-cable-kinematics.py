#!/usr/bin/env python3
"""EX-MA B4 validation: joint sweeps, slewing ring, PTFE tubes, rope loops, travel table.

Writes Validation/2026-09-24-kinematics-report.md and prints it.
Angles are deltas from the EX-MA pose (deg); + raises the member (u toward +z).
"""
import importlib.util
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
ex, rt = asm.ex, asm.rt
DZ = ex.TURRET_DZ
CONTACT_MM3 = 5.0
STEP = 2.0
MIN_WRAP_DEG = 20.0               # rope wrap kept on every drum at the ends of travel
BOWDEN_E = (ex.PTFE_ID - ex.ROPE_D) / 2   # rope-to-tube radial play


def man(mesh):
    return ex.to_manifold(mesh)


def moved(mesh, T):
    m = mesh.copy()
    m.apply_transform(T)
    return m


# ---------------------------------------------------------------- joint sweeps
def sweep(label, moving_members, fixed_members, joint, lo=-180, hi=180, extra_fixed=None):
    mov = trimesh.util.concatenate([asm.member_mesh(m) for m in moving_members])
    # moving members are rigid relative to each other for this sweep; pose by the joint only
    fixed = trimesh.util.concatenate([asm.member_mesh(m) for m in fixed_members] + (extra_fixed or []))
    F = man(fixed)
    pivot_member = {"boom": "boom", "stick": "stick", "bucket": "bucket"}[joint]

    def hit(deg):
        kw = {joint: math.radians(deg)}
        T = asm.pose_transform(pivot_member, **kw)
        # pose_transform for 'stick' chains through the boom (boom = 0 here) - fine
        return (man(moved(mov, T)) ^ F).volume()

    res = {}
    for sgn, lim in ((1, hi), (-1, lo)):
        a = 0.0
        last_ok = 0.0
        while abs(a) <= abs(lim):
            v = hit(a)
            if v > CONTACT_MM3 and a != 0.0:
                break
            last_ok = a
            a += sgn * STEP
        res["max" if sgn > 0 else "min"] = last_ok
    res["at0"] = hit(0.0)
    return res


def ground_box():
    # pedestal top plate (z < 0) and a margin: the arm must not dig into its own pedestal
    return trimesh.creation.box(extents=(180, 180, 12), transform=trimesh.transformations.translation_matrix((0, 0, -6)))


# ---------------------------------------------------------------- slewing ring
def slewing_ring_check():
    tower = man(asm.part("tower"))
    base = man(asm.part("base"))
    ring = man(asm.part("slewing-ring-retaining-ring"))
    R = ex.BALL_D / 2
    n_balls = int(2 * math.pi * ex.BALL_CIRCLE_R // (ex.BALL_D + 0.4))
    c = np.array([[ex.BALL_CIRCLE_R * math.cos(a), ex.BALL_CIRCLE_R * math.sin(a), ex.BALL_Z]
                  for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
    out = dict(n_balls=n_balls)
    for name, m in (("turret flange (inner race)", tower), ("base rim (lower outer race)", base),
                    ("retaining ring (upper outer race)", ring)):
        tm = ex.from_manifold(m)
        _, d, _ = trimesh.proximity.closest_point(tm, c)
        out[name] = (float(d.min()), float(d.max()))
    # lift test: move turret up until the ball (fixed radially at the outer race) is trapped
    ball = trimesh.creation.icosphere(subdivisions=2, radius=R)
    balls = trimesh.util.concatenate([moved(ball, trimesh.transformations.translation_matrix(p)) for p in c])
    B = man(balls)
    out["overlap at rest (mm3)"] = float((B ^ tower).volume() + (B ^ base).volume() + (B ^ ring).volume())
    lift = 0.0
    while lift < 5.0:
        lift += 0.05
        Tt = trimesh.transformations.translation_matrix((0, 0, lift))
        # balls ride with the turret flange; they are trapped once they hit the retaining ring
        if ((man(moved(balls, Tt)) ^ ring).volume()) > 0.5:
            break
    out["turret lift before capture (mm)"] = lift
    tilt = 0.0
    while tilt < 5.0:
        tilt += 0.1
        # rock the turret about a horizontal axis through the ball plane; flange edge must meet the ring
        Tr = trimesh.transformations.rotation_matrix(math.radians(tilt), (0, 1, 0), (0, 0, ex.BALL_Z))
        if (man(moved(ex.from_manifold(tower), Tr)) ^ ring).volume() > 0.5 or \
           (man(moved(ex.from_manifold(tower), Tr)) ^ base).volume() > 0.5:
            break
    out["turret rock before contact (deg)"] = tilt
    return out


# ---------------------------------------------------------------- PTFE tubes
TUBE_R = ex.PTFE_OD / 2
MIN_BEND_R = 15.0                  # PTFE 4x2 bends without kinking above ~15 mm
MIN_GAP = 0.5                      # tube surface to any member in the free zones
# fixed tube run below the PVC top: box fitting -> conduit -> pedestal fitting -> elbow -> PVC tube
LOWER_RUN = (rt.CONDUIT_RUN                                          # box fitting -> pedestal fitting
             + (-ex.ELBOW_R - (ex.PED_U[0] + ex.T_WOOD))                # pedestal fitting -> elbow
             + math.pi / 2 * ex.ELBOW_R                                 # R30 elbow
             + (rt.PVC_TOP_Z + DZ) - (ex.Z_ARM_LAYER + ex.ELBOW_R))     # elbow top -> PVC top (built)


def _free_mask(poly, zones):
    """Samples to check for clearance: the free zones (where the tube is unsupported)."""
    return np.array([z.startswith("free") for z in zones])


def tube_checks(work, n=5):
    """PTFE tubes over the working ranges (boom x stick grid, n x n poses). In the arm each tube
    keeps its natural shape (it slides through the guides); it is cut to its longest arm path
    + 2 mm, and the spare length at each pose is stored as a helix in the conduit run."""
    members = {k: asm.member_mesh(k) for k in ("turret", "boom", "stick")}
    members["turret"] = trimesh.util.concatenate([members["turret"], asm.split_pins("boom")])
    members["boom"] = trimesh.util.concatenate([members["boom"], asm.split_pins("stick")])
    poses = [(b, s) for b in np.linspace(*work["boom"], n) for s in np.linspace(*work["stick"], n)]
    rad = lambda g: (math.radians(g[0]), math.radians(g[1]))
    shapes = {name: {g: rt.natural_with_zones(name, *rad(g), dz=DZ) for g in poses} for name in rt.TUBES}
    rep = {}
    for name in rt.TUBES:
        nat = {g: rt.path_length(shapes[name][g][0]) for g in poses}
        L = max(nat.values()) + 2.0
        rep[name] = dict(arm_length=L, natural=(min(nat.values()), max(nat.values())), rows=[])
    pair_min = (99.0, None, None)
    for g in poses:
        Tm = {mem: asm.pose_transform(mem, boom=rad(g)[0], stick=rad(g)[1]) for mem in members}
        posed = {mem: moved(members[mem], Tm[mem]) for mem in members}
        free_pts = {}
        for name in rt.TUBES:
            poly, zones = shapes[name][g]
            free = _free_mask(poly, zones)
            pts = poly[free]
            clear, where = 99.0, ""
            for mem, m in posed.items():
                d = -trimesh.proximity.signed_distance(m, pts)
                k = int(np.argmin(d))
                if d[k] < clear:
                    clear, where = float(d[k]), f"{mem} at {np.round(pts[k], 0).tolist()}"
            free_pts[name] = pts
            slack = rep[name]["arm_length"] - rt.path_length(poly)
            r_h, R_h, turn_h, _ = rt.conduit_helix(slack)
            rep[name]["rows"].append(dict(boom=g[0], stick=g[1], minR=rt.min_bend_radius(poly), clear=clear,
                                          where=where, slack=slack, helix_r=r_h, helix_R=R_h,
                                          turn=total_turn(poly) + turn_h))
        names = list(free_pts)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                A, B = free_pts[names[i]], free_pts[names[j]]
                d = np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2).min()
                if d < pair_min[0]:
                    pair_min = (float(d), f"{names[i]} / {names[j]}", g)
    for name, t in rep.items():
        turns = [r["turn"] for r in t["rows"]]
        t["bowden"] = (max(turns) - min(turns)) * BOWDEN_E
        t["length"] = t["arm_length"] + LOWER_RUN
    return rep, pair_min


def total_turn(poly):
    d = np.diff(poly, axis=0)
    d = d / np.linalg.norm(d, axis=1)[:, None]
    c = np.clip(np.sum(d[1:] * d[:-1], axis=1), -1, 1)
    return float(np.sum(np.arccos(c)))


# ---------------------------------------------------------------- rope loops / travel
def travel_table(ranges):
    rows = []
    r_lever = ex.DRUM["lever"]["pitch"] / 2
    for j in ("boom", "stick", "bucket"):
        r = ex.DRUM[j]["pitch"] / 2
        span = ranges[j]["max"] - ranges[j]["min"]
        mid = (ranges[j]["max"] + ranges[j]["min"]) / 2
        travel = r * math.radians(span)
        lever = math.degrees(travel / r_lever)
        wrap_mid = 90.0
        wrap_end = wrap_mid - span / 2
        rows.append(dict(joint=j, range=(ranges[j]["min"], ranges[j]["max"]), span=span, mid=mid, pitch_r=r,
                         travel_per_side=travel, lever_deg=lever, wrap_end=wrap_end))
    r_s = ex.DRUM["slew"]["pitch"] / 2
    rows.append(dict(joint="slew", range=(-90.0, 90.0), span=180.0, mid=0.0, pitch_r=r_s,
                     travel_per_side=r_s * math.pi, lever_deg=180.0, wrap_end=None))
    return rows


def lever_slot(lever_deg, h_above_pivot=None):
    """Slot length in the top panel for a lever swinging +/- lever_deg/2 about the axle."""
    h = h_above_pivot if h_above_pivot is not None else (ex.BOX_Z[1] - ex.AXLE_Z)
    return 2 * h * math.tan(math.radians(lever_deg / 2))


def main():
    out_val = ex.OUT / "Validation"
    out_val.mkdir(exist_ok=True)
    ranges = {}
    ranges["boom"] = sweep("boom vs turret", ["boom"], ["turret", "fixed"], "boom", -80, 80)
    ranges["boom_arm"] = sweep("arm vs turret/base/pedestal", ["boom", "stick", "bucket"], ["turret", "fixed"], "boom",
                               -80, 80, extra_fixed=[ground_box()])
    ranges["stick"] = sweep("stick vs boom", ["stick"], ["boom"], "stick", -150, 150)
    ranges["bucket"] = sweep("bucket vs stick", ["bucket"], ["stick"], "bucket", -200, 200)
    ring = slewing_ring_check()
    work = {k: tuple(v) for k, v in ex.WORKING.items()}
    tubes, pair = tube_checks(work)
    table = travel_table({k: dict(min=v[0], max=v[1]) for k, v in work.items() if k != "slew"})
    L = ["# EX-MA kinematics and cable validation (B4b: split pins, sliding tubes, conduit slack)", "",
         "Angles are measured from the EX-MA pose; + raises the member. Contact = overlap > "
         f"{CONTACT_MM3} mm³ between mesh solids, swept in {STEP}° steps.", "",
         "## Joint ranges (first contact)", "",
         "| Joint | Checked against | Min | Max | Span | Overlap at 0 |", "|---|---|---|---|---|---|"]
    for key, what in (("boom", "tower + base + ring"), ("boom_arm", "whole arm vs tower/base/pedestal top"),
                      ("stick", "boom"), ("bucket", "stick")):
        r = ranges[key]
        L.append(f"| {key} | {what} | {r['min']:.0f}° | {r['max']:.0f}° | {r['max'] - r['min']:.0f}° | {r['at0']:.1f} mm³ |")
    L += ["", "## Slewing ring", "",
          f"- BBs (6 mm): {ring['n_balls']} fit on the Ø{2 * ex.BALL_CIRCLE_R:.0f} ball circle with 0.4 mm gaps.",
          f"- Ball-to-race overlap at rest: {ring['overlap at rest (mm3)']:.2f} mm³ (0 = free running).",
          f"- Turret lift before the balls meet the retaining ring: {ring['turret lift before capture (mm)']:.2f} mm.",
          f"- Turret rock before the flange meets the rim or ring: {ring['turret rock before contact (deg)']:.1f}°."]
    for k in ("turret flange (inner race)", "base rim (lower outer race)", "retaining ring (upper outer race)"):
        a, b = ring[k]
        L.append(f"- Ball centre to {k}: {a:.2f}–{b:.2f} mm (ball radius {ex.BALL_D / 2:.2f} + clearance {ex.RACE_CLEAR:.2f}).")
    L += ["", "## Working ranges (set by the lever slots)", "",
          "| Joint | Working range | Inside the contact-free range? |", "|---|---|---|"]
    for j in ("boom", "stick", "bucket"):
        lo, hi = ex.WORKING[j]
        ok = ranges[j]["min"] <= lo and hi <= ranges[j]["max"]
        L.append(f"| {j} | {lo:.0f}° … {hi:.0f}° | {'yes' if ok else 'NO'} ({ranges[j]['min']:.0f}° … {ranges[j]['max']:.0f}°) |")
    L += ["", "## PTFE tubes over the working ranges", "",
          f"Grid: boom × stick working ranges, 5 × 5 poses. Tubes are anchored in the control-box conduit fitting "
          "and at their stop boss in the arm, and slide everywhere between. In the arm each tube keeps its natural "
          "shape; the length change slides down the PVC tube and is stored as spare length in the "
          f"{rt.CONDUIT_RUN:.0f} mm conduit run, where it coils as a gentle helix.", "",
          "| Tube | Cut length (approx.) | Arm path length range | Spare length in the conduit | Worst bend R in the arm | "
          "Conduit helix radius / bend R | Worst free-zone clearance | Bowden coupling |",
          "|---|---|---|---|---|---|---|---|"]
    for name, t in tubes.items():
        rows = t["rows"]
        w = min(rows, key=lambda r: r["clear"])
        L.append(f"| {name} | {t['length']:.0f} mm | {t['natural'][0]:.1f} … {t['natural'][1]:.1f} mm | "
                 f"{min(r['slack'] for r in rows):.1f} … {max(r['slack'] for r in rows):.1f} mm | "
                 f"{min(r['minR'] for r in rows):.1f} mm | ≤ {max(r['helix_r'] for r in rows):.1f} mm / ≥ {min(r['helix_R'] for r in rows):.0f} mm | "
                 f"{w['clear'] - TUBE_R:.1f} mm ({w['where']}, boom {w['boom']:.0f}°, stick {w['stick']:.0f}°) | "
                 f"≤ {t['bowden']:.2f} mm |")
    ok_R = all(r["minR"] >= MIN_BEND_R and r["helix_R"] >= MIN_BEND_R for t in tubes.values() for r in t["rows"])
    ok_c = all(r["clear"] - TUBE_R >= MIN_GAP for t in tubes.values() for r in t["rows"])
    ok_h = all(r["helix_r"] <= rt.CONDUIT_HELIX_R_MAX for t in tubes.values() for r in t["rows"])
    ok_b = all(t["bowden"] < 1.0 for t in tubes.values())
    L += ["", f"- Bend radius ≥ {MIN_BEND_R:.0f} mm everywhere (arm and conduit): {'yes' if ok_R else 'NO'}.",
          f"- Tube surface ≥ {MIN_GAP} mm from every member and split pin in the free zones: {'yes' if ok_c else 'NO'}.",
          f"- Conduit helix fits (radius ≤ {rt.CONDUIT_HELIX_R_MAX:.1f} mm in the Ø{rt.CONDUIT_ID} conduit): {'yes' if ok_h else 'NO'}.",
          f"- Bowden coupling < 1 mm: {'yes' if ok_b else 'NO'}.",
          f"- Closest tube-to-tube centrelines in the free zones: {pair[0]:.1f} mm ({pair[1]}, boom {pair[2][0]:.0f}°, "
          f"stick {pair[2][1]:.0f}°; tube OD {ex.PTFE_OD:.0f} mm, so ≥ 4.0 = not pressed together).",
          "", "A slack bow inside the tower was modelled first and rejected: below the boom root the tower is only "
          "about 44 mm tall, which holds about 2.4 mm of slack at R ≥ 15, while the bucket tubes need up to "
          "10 mm; the boom root's rear shell also closes over a deeper bow at boom +45°."]
    L += ["", "Clearance = tube surface to the nearest member surface in the unsupported (free) zones; inside the "
          "guides the tube runs in Ø5.2 channels by design. Cut length = arm path + fixed run from the box "
          "fitting through the conduit, pedestal, elbow and PVC tube (final lengths go in the bill of materials).",
          "Bowden coupling = rope movement caused by the tube bending: turning-angle change × rope play "
          f"({BOWDEN_E:.1f} mm). This is the only way one joint can move another's rope.", "",
          "## Travel table", "",
          "| Circuit | Working range | Span | Joint drum pitch R | Rope travel per side | Lever swing (Ø60 control drum) | Rope wrap left at ends |",
          "|---|---|---|---|---|---|---|"]
    for r in table:
        wrap = f"{r['wrap_end']:.0f}°" if r["wrap_end"] is not None else "n/a (single lane, 250° total)"
        ctrl = f"{r['lever_deg']:.0f}°" if r["joint"] != "slew" else "wheel 180° (1:1, Ø110 spool)"
        L.append(f"| {r['joint']} | {r['range'][0]:.0f}° … {r['range'][1]:.0f}° | {r['span']:.0f}° | {r['pitch_r']:.1f} mm | "
                 f"{r['travel_per_side']:.1f} mm | {ctrl} | {wrap} |")
    L += ["", "Crimp anchors are set at the middle of each joint's range at assembly, so the rope wrap at "
          "either end of travel is 90° − span/2.", ""]
    rep = "\n".join(L)
    (out_val / "2026-09-24-kinematics-report.md").write_text(rep)
    (out_val / "2026-09-24-kinematics-data.json").write_text(json.dumps(
        dict(ranges=ranges, ring=ring, table=table,
             tubes={k: dict(length=v["length"], arm_length=v["arm_length"], rows=v["rows"]) for k, v in tubes.items()}),
        indent=1, default=float))
    print(rep)


if __name__ == "__main__":
    main()
