"""PTFE tube and rope routing for the arm (single source for build + kinematics).

Coordinates: design frame, ORIGINAL EX-MA pose (turret not yet lowered). Callers add
exma.TURRET_DZ to z for the built position. Joint angles are deltas from the EX-MA
pose (radians, + = counter-clockwise viewed from +v, i.e. boom/stick/bucket "up").

Every PTFE tube follows one (u, z) centreline built from lines and arcs, plus a smooth
lateral (v) schedule. Tube samples are tagged with the member that carries them; the
samples inside a joint's flex window are free and re-shaped per pose.

  stick_hi / stick_lo  : base fitting -> PVC tube -> round the boom pin -> boom stop boss
  bucket_hi / bucket_lo: base fitting -> PVC tube -> boom -> over the stick pin -> stick stop boss
"""
import importlib.util
import math
from pathlib import Path

import numpy as np

_spec = importlib.util.spec_from_file_location("exma", Path(__file__).with_name("2026-09-24-exma_common.py"))
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)

PB, PS, PK = np.array(ex.P_BOOM0), np.array(ex.P_STICK0), np.array(ex.P_BUCKET0)
BOOM_ANG = math.atan2(*(PS - PB)[::-1])
STICK_ANG = math.atan2(*(PK - PS)[::-1])
BOOM_LEN = float(np.linalg.norm(PS - PB))
DB = np.array([math.cos(BOOM_ANG), math.sin(BOOM_ANG)])
NB = np.array([-DB[1], DB[0]])
DS = np.array([math.cos(STICK_ANG), math.sin(STICK_ANG)])
NS = np.array([-DS[1], DS[0]])

PVC_TOP_Z = 45.0                 # top of the rotating PVC tube, original frame (32 built)
PVC_BOTTOM_Z = -85.0             # arm cables enter the PVC tube bottom (after the elbow)
RISE_U = 6.0                     # vertical rise line, just in front of the slew axis
ARC1_R = 25.0                    # turret -> boom turn radius
ARC2_R = 30.0                    # boom -> stick turn radius (bucket tubes, over the stick pin)
ARC2_APEX = 8.0                  # arc apex height above the stick pin
BOOM_STOP_S = 150.0 / math.cos(BOOM_ANG)
STICK_STOP_S = 131.1
# free (unclamped) tube zones: the tube is only held by its end stops and the rib channels
FREE_BOOM_S = 45.0               # boom-joint zone: from the PVC top to the first boom rib channel
FREE_STICK = (160.0, 35.0)       # stick-joint zone: from boom s=160 to stick s=35

# tube: (circuit, PVC slot (u, v), v at the boom pin, stop offset, v schedule)
TUBES = {
    "stick_hi": ("stick", (4.0, +3.0), +10.0, +7.0),
    "stick_lo": ("stick", (4.0, -3.0), -10.0, -7.0),     # -9 left only 0.34 mm of the boom's bottom skin
    "bucket_hi": ("bucket", (-2.5, +3.0), +14.5, +7.0),
    "bucket_lo": ("bucket", (-2.5, -3.0), -14.5, -7.0),
}
BOOM_ROPES = {"boom_a": (-6.0, +2.0), "boom_b": (-6.0, -2.0)}     # bare ropes in the PVC tube


def smooth(t):
    t = min(1.0, max(0.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ramp(x, x0, x1, y0, y1):
    return y0 + (y1 - y0) * smooth((x - x0) / (x1 - x0)) if x1 != x0 else y1


# ---------------------------------------------------------------- centreline pieces (u, z)
def _arc(c, r, a0, a1, n):
    return [np.array([c[0] + r * math.cos(a), c[1] + r * math.sin(a)]) for a in np.linspace(a0, a1, n)]


def _boom_line_start():
    """End of the turret->boom arc (heading = boom direction), plus the arc samples."""
    # arc tangent to the vertical line u = RISE_U, turning clockwise into the boom heading
    turn = math.pi / 2 - BOOM_ANG
    # choose the arc start height so the arc ends on the boom-line offset OFF0 (below the line)
    c_u = RISE_U + ARC1_R
    end_rel = np.array([-ARC1_R * math.cos(turn), ARC1_R * math.sin(turn)])   # end minus centre
    off0 = 1.0                   # on the pin line: full-width section, clear of the chamfered lower corners
    # end point e = (c_u + end_rel.u, z0 + end_rel.z); require (e - PB) . NB = off0
    z0 = (off0 - (c_u + end_rel[0] - PB[0]) * NB[0]) / NB[1] + PB[1] - end_rel[1]
    arc = _arc((c_u, z0), ARC1_R, math.pi, math.pi - turn, 16)
    return z0, arc, off0


Z0_ARC1, ARC1_PTS, OFF0 = _boom_line_start()
S_ARC1_END = float((ARC1_PTS[-1] - PB) @ DB)


def _stick_arc():
    """Arc over the stick pin, centre below the pin, tangent to both the boom and stick headings."""
    c = PS + np.array([0.0, ARC2_APEX - ARC2_R])
    # clockwise travel at angle a heads (a - 90 deg): start on the boom heading, end on the stick heading
    a0 = math.pi / 2 + BOOM_ANG
    a1 = math.pi / 2 + STICK_ANG
    pts = _arc(c, ARC2_R, a0, a1, 16)
    return pts


ARC2_PTS = _stick_arc()
OFF_BOOM_END = float((ARC2_PTS[0] - PB) @ NB)
S_BOOM_ARC2 = float((ARC2_PTS[0] - PB) @ DB)
OFF_STICK_START = float((ARC2_PTS[-1] - PS) @ NS)
S_STICK_ARC2 = float((ARC2_PTS[-1] - PS) @ DS)


def centreline(name):
    """Sampled centreline [(member, np.array([u, v, z]), zone)] for one tube, original pose.

    zone: 'fixed' samples ride rigidly on their member; 'flex_boom' / 'flex_stick' are free."""
    circuit, (pu, pv), v_pin, off_stop = TUBES[name]
    out = []
    # 1. inside the PVC tube (turret), vertical, slot position
    for z in np.linspace(PVC_BOTTOM_Z, PVC_TOP_Z, 14):
        out.append(("turret", np.array([pu, pv, z]), "fixed"))
    # 2. fan out above the PVC top to the rise line u = RISE_U and the pin-side v (free zone)
    for z in np.linspace(PVC_TOP_Z, Z0_ARC1, 10)[1:]:
        t = (z - PVC_TOP_Z) / (Z0_ARC1 - PVC_TOP_Z)
        out.append(("turret", np.array([ramp(t, 0, 1, pu, RISE_U), ramp(t, 0, 1, pv, v_pin), z]), "flex_boom"))
    # 3. turret->boom arc (free window centred on it)
    for p in ARC1_PTS[1:]:
        out.append(("boom", np.array([p[0], v_pin, p[1]]), "flex_boom"))
    # 4. along the boom
    if circuit == "stick":
        s_end = BOOM_STOP_S
        for s in np.linspace(S_ARC1_END, s_end, 40)[1:]:
            off = ramp(s, 40.0, s_end - 15.0, OFF0, off_stop)
            v = ramp(s, 60.0, s_end - 10.0, v_pin, 0.0)
            p = PB + s * DB + off * NB
            out.append(("boom", np.array([p[0], v, p[1]]), "flex_boom" if s < FREE_BOOM_S else "fixed"))
        return out
    side = 8.5 * (1 if v_pin > 0 else -1)
    for s in np.linspace(S_ARC1_END, S_BOOM_ARC2, 44)[1:]:
        off = ramp(s, 40.0, S_BOOM_ARC2 - 10.0, OFF0, OFF_BOOM_END)
        v = ramp(s, 100.0, 170.0, v_pin, side)
        p = PB + s * DB + off * NB
        zone = "flex_boom" if s < FREE_BOOM_S else ("flex_stick" if s > FREE_STICK[0] else "fixed")
        out.append(("boom", np.array([p[0], v, p[1]]), zone))
    # 5. over the stick pin
    for i, p in enumerate(ARC2_PTS[1:]):
        out.append(("stick" if i >= len(ARC2_PTS) // 2 else "boom", np.array([p[0], side, p[1]]), "flex_stick"))
    # 6. along the stick to the stop
    for s in np.linspace(S_STICK_ARC2, STICK_STOP_S, 36)[1:]:
        off = ramp(s, S_STICK_ARC2 + 10.0, STICK_STOP_S - 15.0, OFF_STICK_START, off_stop)
        v = ramp(s, 40.0, STICK_STOP_S - 10.0, side, 0.0)
        p = PS + s * DS + off * NS
        out.append(("stick", np.array([p[0], v, p[1]]), "flex_stick" if s < FREE_STICK[1] else "fixed"))
    return out


# ---------------------------------------------------------------- posing
def _rot_uz(p3, c, a):
    d = np.array([p3[0] - c[0], p3[2] - c[1]])
    ca, sa = math.cos(a), math.sin(a)
    return np.array([c[0] + d[0] * ca - d[1] * sa, p3[1], c[1] + d[0] * sa + d[1] * ca])


def place(member, p3, boom=0.0, stick=0.0, bucket=0.0):
    """Move a point rigidly with its member for a pose (joint deltas in radians)."""
    if member == "turret":
        return np.array(p3, float)
    if member == "boom":
        return _rot_uz(p3, PB, boom)
    if member == "stick":
        return _rot_uz(_rot_uz(p3, PS, stick), PB, boom)
    if member == "bucket":
        return _rot_uz(_rot_uz(_rot_uz(p3, PK, bucket), PS, stick), PB, boom)
    raise KeyError(member)


def _hermite(p0, t0, p1, t1, n, scale=1.0):
    L = np.linalg.norm(p1 - p0) * scale
    t0, t1 = t0 / np.linalg.norm(t0) * L, t1 / np.linalg.norm(t1) * L
    out = []
    for t in np.linspace(0, 1, n):
        h00, h10, h01, h11 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2, t**3 - t**2
        out.append(h00 * p0 + h10 * t0 + h01 * p1 + h11 * t1)
    return out


def tube_polyline(name, boom=0.0, stick=0.0, bucket=0.0, dz=0.0, scale=1.0, n_flex=40):
    """Posed PTFE centreline (N x 3). Fixed samples ride on members; each free zone is
    replaced by a cubic Hermite curve tangent to the clamped tube on both sides.
    `scale` stretches the end tangents: a longer (slack) tube bows more."""
    cl = centreline(name)
    posed = [(place(m, p, boom, stick, bucket), zone) for m, p, zone in cl]
    out, i = [], 0
    while i < len(posed):
        p, zone = posed[i]
        if zone == "fixed":
            out.append(p)
            i += 1
            continue
        j = i
        while j < len(posed) and posed[j][1] == zone:
            j += 1
        a, b = posed[i - 1][0], posed[min(j, len(posed) - 1)][0]
        ta = a - posed[i - 2][0]
        tb = posed[min(j + 1, len(posed) - 1)][0] - b
        out.extend(_hermite(a, ta, b, tb, n_flex, scale)[1:-1])
        i = j
    arr = np.array(out)
    arr[:, 2] += dz
    return arr


def fit_length(name, L_target, boom=0.0, stick=0.0, bucket=0.0, dz=0.0):
    """Shape of a fixed-length tube at a pose: pick the tangent scale whose curve length
    matches L_target (the slack bows out). Returns (poly, scale)."""
    lo, hi = 0.3, 3.0
    f = lambda sc: path_length(tube_polyline(name, boom, stick, bucket, dz, sc)) - L_target
    if f(lo) > 0:
        return tube_polyline(name, boom, stick, bucket, dz, lo), lo
    if f(hi) < 0:
        return tube_polyline(name, boom, stick, bucket, dz, hi), hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    sc = 0.5 * (lo + hi)
    return tube_polyline(name, boom, stick, bucket, dz, sc), sc


def path_length(poly):
    return float(np.sum(np.linalg.norm(np.diff(poly, axis=0), axis=1)))


def min_bend_radius(poly, skip_pvc=True):
    """Smallest radius of curvature along the polyline (3-point circumcircles)."""
    r = []
    for a, b, c in zip(poly[:-2], poly[1:-1], poly[2:]):
        ab, bc, ca = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
        cross = np.linalg.norm(np.cross(b - a, c - a))
        if cross < 1e-9 or min(ab, bc) < 1e-6:
            continue
        r.append(ab * bc * ca / (2 * cross))
    return min(r) if r else float("inf")


def tube_stop(name):
    """(member, point, direction) of the tube end at its stop boss, original pose."""
    cl = centreline(name)
    m, p, _ = cl[-1]
    d = p - cl[-2][1]
    return m, p, d / np.linalg.norm(d)
