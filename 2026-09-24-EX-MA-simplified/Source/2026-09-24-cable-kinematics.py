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
def tube_checks(work):
    """PTFE tubes over the working ranges. Tube length = longest natural path over the grid
    (+2 mm); at every other pose that fixed length is re-shaped (slack bows out)."""
    members = {k: asm.member_mesh(k) for k in ("turret", "boom", "stick")}
    rep = {}
    for name in rt.TUBES:
        circuit = rt.TUBES[name][0]
        bs = np.linspace(*work["boom"], 5)
        ss = np.linspace(*work["stick"], 5) if circuit == "bucket" else [0.0]
        grid = [(b, s) for b in bs for s in ss]
        nat = {g: rt.path_length(rt.tube_polyline(name, math.radians(g[0]), math.radians(g[1]), dz=DZ)) for g in grid}
        L_tube = max(nat.values()) + 2.0
        turn_ref = None
        rows = []
        for jb, js in grid:
            poly, sc = rt.fit_length(name, L_tube, math.radians(jb), math.radians(js), dz=DZ)
            clear = 99.0
            for mem in ("turret", "boom", "stick"):
                T = asm.pose_transform(mem, boom=math.radians(jb), stick=math.radians(js))
                sd = trimesh.proximity.signed_distance(moved(members[mem], T), poly[::2])
                clear = min(clear, float(-sd.max()))
            turn = total_turn(poly)
            turn_ref = turn if turn_ref is None else turn_ref
            rows.append(dict(boom=float(jb), stick=float(js), minR=rt.min_bend_radius(poly), slack=L_tube - nat[(jb, js)],
                             clear=clear, turn=turn, scale=sc))
        tmin, tmax = min(r["turn"] for r in rows), max(r["turn"] for r in rows)
        rep[name] = dict(length=L_tube, rows=rows, bowden=(tmax - tmin) * BOWDEN_E)
    return rep


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
    tubes = tube_checks(work)
    table = travel_table({k: dict(min=v[0], max=v[1]) for k, v in work.items() if k != "slew"})
    L = ["# EX-MA kinematics and cable validation (B4)", "",
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
          "Tube length is fixed (longest natural path + 2 mm); at other poses the spare length bows out in the free zones.", "",
          "| Tube | Cut length | Worst bend R | Worst centreline clearance | Spare length (bows) | Bowden coupling |",
          "|---|---|---|---|---|---|"]
    for name, t in tubes.items():
        rows = t["rows"]
        L.append(f"| {name} | {t['length']:.0f} mm | {min(r['minR'] for r in rows):.1f} mm | "
                 f"{min(r['clear'] for r in rows):.1f} mm | {min(r['slack'] for r in rows):.1f} … {max(r['slack'] for r in rows):.1f} mm | "
                 f"≤ {t['bowden']:.2f} mm |")
    L += ["", "Clearance = distance from the tube centreline to the nearest member surface (tube radius 2.0 mm).",
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
             tubes={k: dict(length=v["length"], rows=v["rows"]) for k, v in tubes.items()}), indent=1, default=float))
    print(rep)


if __name__ == "__main__":
    main()
