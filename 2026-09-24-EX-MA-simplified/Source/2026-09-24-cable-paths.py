#!/usr/bin/env python3
"""Continuous cable paths for the review views (built pose, every joint at 0 deg, wheel centred).

Each rope is assembled from the modelled pieces used by the validation:
  arm circuits : lever-drum wrap (tail anchor -> tangent) -> box fitting hole (build-box.lever_strands)
                 -> conduit (straight; the stick/bucket PTFE tubes coil as routing.conduit_helix)
                 -> pedestal fitting -> 1/2in copper elbow (R30) -> up the PEX turret tube
                 -> arm: routing.natural() tube centreline to its stop (stick, bucket) or straight up (boom)
                 -> joint-drum tangent -> wrap to the midpoint crimp pocket
  slew ropes   : spool wrap (anchor -> tangent) -> sleeve post -> PTFE sleeve (build-box.slew_sleeve)
                 -> pedestal fitting counterbore -> exit -> pedestal-drum tangent -> wrap to the crimp pocket

Run it to check continuity and lengths:  <cadenv>/bin/python 2026-09-24-cable-paths.py
Writes Validation/2026-09-24-cable-paths.json.
"""
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


asm = _load("asm", "2026-09-24-assembly.py")
bx = _load("bx", "2026-09-24-build-box.py")
ex, rt = asm.ex, asm.rt
T = ex.T_WOOD
DZ = ex.TURRET_DZ
TUBE_TOP = rt.TUBE_TOP_Z + DZ
# which lever strand runs in which PTFE tube / reaches which boom-drum side (rigging choice)
ROW_TO_TUBE = {("stick", 0): "stick_hi", ("stick", 1): "stick_lo", ("bucket", 0): "bucket_hi", ("bucket", 1): "bucket_lo"}
BOOM_SLOT = {0: (4.0, 2.0), 1: (4.0, -2.0)}          # boom ropes at the top of the turret tube (u, v)
PED_COL = {"boom": 4.0, "stick": 0.0, "bucket": -4.0}  # strand v at the pedestal fitting, relative to the copper axis


def arc_pts(c, r, a0, a1, lift, step=4.0):
    """Points on a circle (centre c = (x, y), radius r) from angle a0 to a1 (deg, either direction);
    lift(x, y) -> 3D point."""
    n = max(2, int(abs(a1 - a0) / step) + 1)
    return [lift(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
            for a in np.linspace(a0, a1, n)]


def tangent_from(P, c, r, side):
    """Tangent point on circle (c, r) seen from P (2D); side +1 / -1 picks the left / right tangent
    looking from P toward c. Returns (point, angle deg)."""
    d = np.array(c) - np.array(P)
    D = np.linalg.norm(d)
    base = math.atan2(-d[1], -d[0])                       # from the centre back toward P
    a = base + side * math.acos(r / D)
    return np.array(c) + r * np.array([math.cos(a), math.sin(a)]), math.degrees(a)


def unwrap_to(a_from, a_to, direction):
    """Return a_to shifted by 360s so it lies from a_from in `direction` (+1 increasing, -1 decreasing)."""
    while direction > 0 and a_to < a_from:
        a_to += 360.0
    while direction < 0 and a_to > a_from:
        a_to -= 360.0
    return a_to


def elbow_pts(a, b, u_start):
    """Strand through the pedestal fitting and the R30 copper elbow: a = offset toward the bend
    centre (up at the start), b = lateral offset (v). Returns points up to the elbow top."""
    R = ex.ELBOW_R
    pts = [np.array([u_start, b, ex.Z_ARM_LAYER + a]), np.array([-R, b, ex.Z_ARM_LAYER + a])]
    for phi in np.linspace(0, math.pi / 2, 16)[1:]:
        C = np.array([-R + R * math.sin(phi), (ex.Z_ARM_LAYER + R) - R * math.cos(phi)])
        n = np.array([-math.sin(phi), math.cos(phi)])
        q = C + a * n
        pts.append(np.array([q[0], b, q[1]]))
    return pts


def arm_rope(j, row):
    """One tail of an arm circuit, from its lever-drum anchor to the joint-drum crimp pocket."""
    pieces = []
    st = bx.lever_strands(j, 0.0)[row]
    vd = ex.LEVERS[j][1]
    anchor = 155.0 if row == 0 else 205.0
    lift_lever = lambda x, z: np.array([x, vd, z])
    # upper tail lies on the drum from its anchor (155) down to the departure; lower from 205 up to it
    dep = unwrap_to(anchor, st["dep_deg"], -1 if row == 0 else 1)
    pieces.append(("lever drum wrap", arc_pts((ex.AXLE_U, ex.AXLE_Z), bx.R_LEVER, anchor, dep, lift_lever)))
    hole_c = bx.box_fitting_hole(j, row, "conduit")
    pieces.append(("box: drum to fitting", [st["tangent"], st["hole"], hole_c]))
    # conduit: box socket floor -> pedestal socket floor
    u_p = ex.PED_U[0] + T + ex.CONDUIT_SOCKET
    z_row = ex.COND_Z + ex.FIT_ARM_ROWS[row]
    E = np.array([u_p, PED_COL[j], z_row])
    S = hole_c
    tube = ROW_TO_TUBE.get((j, row))
    if tube:
        kin = json.loads((ex.OUT / "Validation" / "2026-09-24-kinematics-data.json").read_text())
        slack = kin["tubes"][tube]["arm_length"] - rt.path_length(rt.natural(tube, dz=DZ))
        r_h, R_h, turn, hp = rt.conduit_helix(slack, n=60)
        d = (E - S) / np.linalg.norm(E - S)
        e1 = np.array([0, 1.0, 0]) - d * d[1]
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(d, e1)
        L = np.linalg.norm(E - S)
        pieces.append(("conduit (PTFE coil)", [S + (x / hp[-1, 0]) * (E - S) + y * e1 + z * e2 for x, y, z in hp]))
    else:
        pieces.append(("conduit", [S, E]))
    a = ex.FIT_ARM_ROWS[row] - (-20.0)                          # row offset from the copper axis (up = toward the bend centre)
    b = PED_COL[j]
    pieces.append(("pedestal fitting + copper elbow", [E] + elbow_pts(a, b, u_p)[1:]))
    bottom = pieces[-1][1][-1]
    if tube:
        top_uv = rt.TUBES[tube][1]
    else:
        top_uv = BOOM_SLOT[row]
    top = np.array([top_uv[0], top_uv[1], TUBE_TOP])
    pieces.append(("up the PEX turret tube", [bottom, top]))
    if tube:
        poly, zones = rt.natural_with_zones(tube, dz=DZ)
        arm = [p for p, zn in zip(poly, zones) if zn != "turret"]
        pieces.append(("arm: PTFE tube to its stop", [top] + arm))
        stop = arm[-1]
        c = ex.P_STICK if j == "stick" else ex.P_BUCKET
        r = ex.DRUM[j]["pitch"] / 2
        pocket = math.degrees(rt.BOOM_ANG if j == "stick" else rt.STICK_ANG)
        side = 1 if row == 0 else -1
        tp, ta = tangent_from((stop[0], stop[2]), c, r, -side)
        direction = -1 if row == 0 else 1
        pieces.append(("stop to joint drum", [stop, np.array([tp[0], 0.0, tp[1]])]))
        pieces.append(("joint drum wrap to crimp", arc_pts(c, r, ta, unwrap_to(ta, pocket, direction),
                                                          lambda x, z: np.array([x, 0.0, z]))))
    else:
        c, r = ex.P_BOOM, ex.DRUM["boom"]["pitch"] / 2
        side = 1 if row == 0 else -1
        tp, ta = tangent_from((top[0], top[2]), c, r, side)
        pieces.append(("up to the boom drum", [top, np.array([tp[0], 0.0, tp[1]])]))
        pieces.append(("boom drum wrap to crimp", arc_pts(c, r, ta, unwrap_to(ta, 90.0, 1 if row == 0 else -1),
                                                         lambda x, z: np.array([x, 0.0, z]))))
    return pieces, tube


def slew_rope(lane):
    sign = 1 if lane == "A" else -1
    dep = ex.spool_departures()
    zl = ex.Z_SLEW_LAYER + sign * ex.SLEW_LANE_OFF
    pieces = []
    a_dep = dep[lane]["tangent_deg"]
    a_anchor = dep["B" if lane == "A" else "A"]["tangent_deg"]
    if lane == "A":
        a0 = unwrap_to(a_dep, a_anchor, 1)                      # rope lies on the larger angles
    else:
        a0 = unwrap_to(a_dep, a_anchor, -1)
    pieces.append(("spool wrap", arc_pts(ex.WHEEL_C, bx.R_SLEW, a0, a_dep, lambda x, y: np.array([x, y, zl]))))
    fb, fp = bx.slew_rope_free(lane)
    pieces.append(("spool to sleeve post", [fb[0], fb[1]]))
    sl = bx.slew_sleeve(lane)
    pieces.append(("PTFE sleeve", [fb[1]] + list(sl["poly"])))
    ped = ex.pedestal_slew_line(sign)
    pieces.append(("through the pedestal fitting", [sl["poly"][-1], np.array([*ped["exit"], ex.Z_SLEW_LAYER])]))
    pieces.append(("fitting to pedestal drum", [fp[0], fp[1]]))
    t = ped["tangent_deg"]
    end = t - 180.0 if sign > 0 else t + 180.0
    pieces.append(("pedestal drum wrap to crimp", arc_pts((0.0, 0.0), bx.R_SLEW, t, end, lambda x, y: np.array([x, y, zl]))))
    return pieces, sl


def all_paths():
    """{rope name: dict(circuit, pieces [(label, Nx3)], ptfe [Nx3 ...])}"""
    out = {}
    for j in ("boom", "stick", "bucket"):
        for row in (0, 1):
            pieces, tube = arm_rope(j, row)
            ptfe = []
            if tube:
                labels = ("conduit (PTFE coil)", "pedestal fitting + copper elbow", "up the PEX turret tube", "arm: PTFE tube to its stop")
                seg = []
                for lab, pts in pieces:
                    if lab in labels:
                        seg += [np.asarray(p) for p in pts]
                ptfe.append(np.array(seg))
            out[f"{j} {'upper' if row == 0 else 'lower'} tail"] = dict(circuit=j, tube=tube, ptfe=ptfe,
                                                                      pieces=[(l, np.array(p)) for l, p in pieces])
    for lane in "AB":
        pieces, sl = slew_rope(lane)
        out[f"slew rope {lane}"] = dict(circuit="slew", pieces=[(l, np.array(p)) for l, p in pieces], ptfe=[sl["poly"]])
    return out


def polyline(entry):
    pts = []
    for _, p in entry["pieces"]:
        for q in p:
            if not pts or np.linalg.norm(q - pts[-1]) > 1e-6:
                pts.append(q)
    return np.array(pts)


def main():
    P = all_paths()
    box = json.loads((ex.OUT / "Validation" / "2026-09-24-box-data.json").read_text())["cut_lengths"]
    rows = []
    for name, e in P.items():
        gaps = [float(np.linalg.norm(e["pieces"][k][1][0] - e["pieces"][k - 1][1][-1])) for k in range(1, len(e["pieces"]))]
        poly = polyline(e)
        L = float(np.sum(np.linalg.norm(np.diff(poly, axis=0), axis=1)))
        rows.append(dict(rope=name, pieces=[l for l, _ in e["pieces"]], max_gap=max(gaps), length=L))
    # compare with the cut-list lengths (arm ropes = both tails)
    comp = {}
    for j in ("boom", "stick", "bucket"):
        L = sum(r["length"] for r in rows if r["rope"].startswith(j + " "))
        comp[j] = (L, box[f"{j} rope (one length, midpoint crimp)"])
    for lane in "AB":
        L = next(r["length"] for r in rows if r["rope"] == f"slew rope {lane}")
        comp[f"slew {lane}"] = (L, box[f"slew rope {lane} (spool anchor -> pedestal crimp)"])
    ptfe = {}
    for name, e in P.items():
        for k, seg in enumerate(e["ptfe"]):
            key = e.get("tube") or f"slew sleeve {name[-1]}"
            # arm tubes also sit 11 mm deep in the box-fitting counterbore; the sleeve polyline already includes its ends
            ptfe[key] = float(np.sum(np.linalg.norm(np.diff(seg, axis=0), axis=1))) + (11.0 if e.get("tube") else 12.0)
    out = dict(ropes=rows, ptfe_lengths=ptfe,
               lengths={k: dict(path=v[0], cut_list=v[1], diff_pct=100 * (v[0] - v[1]) / v[1]) for k, v in comp.items()},
               paths={n: polyline(e).round(2).tolist() for n, e in P.items()})
    (ex.OUT / "Validation" / "2026-09-24-cable-paths.json").write_text(json.dumps(out, indent=1))
    for r in rows:
        print(f"{r['rope']:20s} pieces {len(r['pieces']):2d}  max gap {r['max_gap']:.3f} mm  length {r['length']:.0f} mm")
    for k, v in ptfe.items():
        print(f"PTFE {k:14s} {v:.0f} mm")
    for k, v in out["lengths"].items():
        print(f"{k:8s} path {v['path']:.0f} mm  cut list {v['cut_list']:.0f} mm  ({v['diff_pct']:+.1f} %)")


if __name__ == "__main__":
    main()
