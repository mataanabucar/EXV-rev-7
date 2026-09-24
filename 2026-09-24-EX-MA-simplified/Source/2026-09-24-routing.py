"""PTFE tube routing for the arm, v3: tubes cross the joints THROUGH the pivot axes.

Coordinates: design frame, ORIGINAL EX-MA pose (turret not yet lowered); callers add
exma.TURRET_DZ to z for the built position. Joint angles are deltas from the EX-MA pose
(radians, + raises the member, u toward +z).

The boom and stick pins are split into two short rods each, so the middle of each joint
is free and a tube can pass exactly through the pivot axis. A tube passing through the axis
barely changes length when the joint turns.

Tubes are anchored only at their two ends: the conduit fitting in the CONTROL BOX and the
stop boss in the arm. Everywhere else they slide (pedestal fitting, copper elbow, PEX turret tube,
rib channels); the small remaining length change is taken up as spare length in the 2"
conduit, where it forms a gentle helix (see conduit_helix). A bow in the tower was tried
first and rejected: the tower below the boom root is only ~44 mm tall, which holds ~2.4 mm
of slack at R >= 15, and the boom root's rear shell closes over the bow at boom +45 deg.

Each tube moves out to its crossing v in the lower half of the tower and then stays in its
own plane, 4.3-4.5 mm from its neighbour.

Zones along each tube:
  'turret'     fixed on the turret (inside the PEX turret tube)
  'free_boom'  free: tube top -> boom clamp
  'boom'       guided by the boom (straight / fixed bends)
  'free_stick' free: boom bulkhead -> stick clamp (bucket tubes only)
  'stick'      guided by the stick
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
DB = np.array([math.cos(BOOM_ANG), math.sin(BOOM_ANG)])
NB = np.array([-DB[1], DB[0]])
DS = np.array([math.cos(STICK_ANG), math.sin(STICK_ANG)])
NS = np.array([-DS[1], DS[0]])
BOOM_LEN = float(np.linalg.norm(PS - PB))

TUBE_TOP_Z = 35.0                  # top of the rotating PEX turret tube (original frame; 22 built, 3 mm inside the flange bore)
TUBE_BOTTOM_Z = -85.0
BEND_R = 20.0                     # fixed bends inside the members

# boom joint: tube rises vertically through the boom axis; on the boom side it leaves the
# axis at BOOM_EXIT_REL above the boom line and is guided from BOOM_CLAMP_B onwards
BOOM_EXIT_REL = math.radians(55.0)
BOOM_CLAMP_B = 15.0
BOOM_RUN_OFF = 0.0                # offset from the boom line along the boom (bucket tubes)
BOOM_BULKHEAD_S = BOOM_LEN - 27.0 # stick-tube stops and bucket-tube clamp, 27 mm before the stick pin
# stick joint: bucket tubes reach the stick axis along a line STICK_APPROACH from the pin
# (direction from the pin back toward the tube, boom frame at the EX-MA pose)
STICK_APPROACH = math.radians(220.0)
STICK_EXIT_REL = math.radians(25.0)   # stick side: leaves the axis 25 deg above the stick line
STICK_CLAMP_B = 18.0
STICK_STOP_S = 131.1

TUBES = {
    # name: (circuit, slot in the turret tube (u, v), v across the boom joint, stop offset)
    # slots at the top of the 3/4" PEX-B turret tube (ID 17.3; tube surfaces within r 6.9):
    # circuits side by side in u (bucket, stick, boom ropes at (+4, +-2)), each pair split in v.
    # This is the conduit bundle (circuits side by side in v, pairs split by row) turned 90 deg,
    # so the bundle twists 90 deg + slew along the turret tube (<= 180 deg over ~120 mm).
    "stick_hi": ("stick", (0.0, +2.3), +10.0, +7.0),
    "stick_lo": ("stick", (0.0, -2.3), -10.0, -7.0),
    "bucket_hi": ("bucket", (-4.3, +2.3), +14.3, +6.0),     # 0.7 mm from the split-pin ends (|v| 17)
    "bucket_lo": ("bucket", (-4.3, -2.3), -14.3, -6.0),
}
V_RAMP_T = 0.45                   # tower zone: the tube reaches its crossing v by this fraction
BUCKET_V_STICK = 8.5              # bucket tubes pass the stick joint beside the stick drum


def smooth(t):
    t = min(1.0, max(0.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ramp(x, x0, x1, y0, y1):
    return y0 + (y1 - y0) * smooth((x - x0) / (x1 - x0)) if x1 != x0 else y1


def _dir(a):
    return np.array([math.cos(a), math.sin(a)])


def _fillet(p_corner, d_in, d_out, r, n=10):
    """Arc of radius r joining a line arriving along d_in at p_corner to a line leaving along d_out."""
    d_in, d_out = d_in / np.linalg.norm(d_in), d_out / np.linalg.norm(d_out)
    ang = math.atan2(d_in[0] * d_out[1] - d_in[1] * d_out[0], d_in @ d_out)
    if abs(ang) < 1e-6:
        return [p_corner]
    t = r * math.tan(abs(ang) / 2)
    a0 = p_corner - d_in * t
    nrm = np.array([-d_in[1], d_in[0]]) * (1 if ang > 0 else -1)
    c = a0 + nrm * r
    start = math.atan2(*(a0 - c)[::-1])
    return [c + r * _dir(start + ang * k / n) for k in range(n + 1)]


# ---------------------------------------------------------------- centreline
def _member_path(origin, d, n, s0, off0, rel0, s_end, off_end, rel_end=0.0, ramp_len=90.0, step=3.0):
    """Guided path along a member in (s, off) coordinates, C1-smooth:
    starts at (s0, off0) heading rel0 (radians relative to the member line), bends back to the
    member line with radius BEND_R, cosine-ramps to off_end, and (optionally) finishes with an
    arc that leaves at heading rel_end exactly at (s_end, off_end). Returns 2D points."""
    pts = []
    # initial fillet: from heading rel0 back to 0
    ds1, doff1 = BEND_R * abs(math.sin(rel0)), BEND_R * (1 - math.cos(rel0)) * (1 if rel0 > 0 else -1)
    for t in np.linspace(0, 1, 8):
        a = rel0 * (1 - t)
        sgn = 1 if rel0 > 0 else -1
        s_ = s0 + BEND_R * abs(math.sin(rel0) - math.sin(a)) if rel0 != 0 else s0
        o_ = off0 + sgn * BEND_R * (math.cos(a) - math.cos(rel0)) if rel0 != 0 else off0
        pts.append((s_, o_))
    s1, o1 = pts[-1]
    # final arc (reversed construction): ends at (s_end, off_end) heading rel_end
    ds2 = BEND_R * abs(math.sin(rel_end))
    doff2 = BEND_R * (1 - math.cos(rel_end)) * (1 if rel_end > 0 else -1)
    s2, o2 = s_end - ds2, off_end - doff2
    # middle: cosine ramp from o1 to o2 between s1 and s2
    mid_start = s1 + 0.5 * max(0.0, (s2 - s1) - ramp_len)
    for s_ in np.arange(s1 + step, s2, step):
        pts.append((s_, ramp(s_, mid_start, mid_start + min(ramp_len, s2 - s1), o1, o2)))
    pts.append((s2, o2))
    if rel_end != 0:
        sgn = 1 if rel_end > 0 else -1
        for t in np.linspace(0, 1, 8)[1:]:
            a = rel_end * t
            pts.append((s2 + BEND_R * abs(math.sin(a)), o2 + sgn * BEND_R * (1 - math.cos(a))))
    return [origin + s_ * d + o_ * n for s_, o_ in pts]


def centreline(name):
    """[(member, np.array([u, v, z]), zone)] for one tube, original pose."""
    circuit, (pu, pv), v_pin, off_stop = TUBES[name]
    out = []
    # 1. inside the turret tube
    for z in np.linspace(TUBE_BOTTOM_Z, TUBE_TOP_Z, 14):
        out.append(("turret", np.array([pu, pv, z]), "turret"))
    # 2. free zone: tube top -> through the boom axis -> boom clamp (shape re-solved per pose)
    h_boom = BOOM_ANG + BOOM_EXIT_REL
    for t in np.linspace(0, 1, 16)[1:]:
        if t < 0.8:
            u, z = pu * (1 - t / 0.8), TUBE_TOP_Z + (PB[1] - TUBE_TOP_Z) * (t / 0.8)
        else:
            u, z = PB + BOOM_CLAMP_B * _dir(h_boom) * ((t - 0.8) / 0.2)
        out.append(("boom" if t >= 0.8 else "turret", np.array([u, ramp(t, 0.0, V_RAMP_T, pv, v_pin), z]), "free_boom"))
    s_c = BOOM_CLAMP_B * math.cos(BOOM_EXIT_REL)
    off_c = BOOM_CLAMP_B * math.sin(BOOM_EXIT_REL)
    if circuit == "stick":
        path = _member_path(PB, DB, NB, s_c, off_c, BOOM_EXIT_REL, BOOM_BULKHEAD_S, off_stop)
        for p in path:
            s = float((p - PB) @ DB)
            out.append(("boom", np.array([p[0], ramp(s, 60.0, BOOM_BULKHEAD_S - 8.0, v_pin, 0.0), p[1]]), "boom"))
        return out
    side = BUCKET_V_STICK * (1 if v_pin > 0 else -1)
    app_pt = PS + (BOOM_LEN - BOOM_BULKHEAD_S) * _dir(STICK_APPROACH)      # bulkhead clamp on the approach line
    rel_app = math.remainder((STICK_APPROACH + math.pi) - BOOM_ANG, 2 * math.pi)   # approach heading rel. to the boom
    s_app, off_app = float((app_pt - PB) @ DB), float((app_pt - PB) @ NB)
    path = _member_path(PB, DB, NB, s_c, off_c, BOOM_EXIT_REL, s_app, off_app, rel_end=rel_app)
    for p in path:
        s = float((p - PB) @ DB)
        out.append(("boom", np.array([p[0], ramp(s, 90.0, BOOM_BULKHEAD_S - 20.0, v_pin, side), p[1]]), "boom"))
    # 3. free zone across the stick joint: bulkhead clamp -> through the stick axis -> stick clamp
    h_stick = STICK_ANG + STICK_EXIT_REL
    sclamp = PS + STICK_CLAMP_B * _dir(h_stick)
    for t in np.linspace(0, 1, 14)[1:]:
        if t < 0.45:
            q, m = app_pt + (PS - app_pt) * (t / 0.45), "boom"
        else:
            q, m = PS + (sclamp - PS) * ((t - 0.45) / 0.55), "stick"
        out.append((m, np.array([q[0], side, q[1]]), "free_stick"))
    # 4. stick side: guided from the stick clamp to the stop
    s_sc = STICK_CLAMP_B * math.cos(STICK_EXIT_REL)
    off_sc = STICK_CLAMP_B * math.sin(STICK_EXIT_REL)
    path = _member_path(PS, DS, NS, s_sc, off_sc, STICK_EXIT_REL, STICK_STOP_S, off_stop, ramp_len=70.0)
    for p in path:
        s = float((p - PS) @ DS)
        out.append(("stick", np.array([p[0], ramp(s, 40.0, STICK_STOP_S - 10.0, side, 0.0), p[1]]), "stick"))
    return out


# ---------------------------------------------------------------- posing
def _rot_uz(p3, c, a):
    d = np.array([p3[0] - c[0], p3[2] - c[1]])
    ca, sa = math.cos(a), math.sin(a)
    return np.array([c[0] + d[0] * ca - d[1] * sa, p3[1], c[1] + d[0] * sa + d[1] * ca])


def place(member, p3, boom=0.0, stick=0.0, bucket=0.0):
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
    """Cubic Hermite; scale = one tangent scale or (start, end) scales (x chord length)."""
    s0, s1 = scale if isinstance(scale, tuple) else (scale, scale)
    L = np.linalg.norm(p1 - p0)
    t0, t1 = t0 / np.linalg.norm(t0) * L * s0, t1 / np.linalg.norm(t1) * L * s1
    out = []
    for t in np.linspace(0, 1, n):
        h00, h10, h01, h11 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2, t**3 - t**2
        out.append(h00 * p0 + h10 * t0 + h01 * p1 + h11 * t1)
    return out


def tube_polyline(name, boom=0.0, stick=0.0, bucket=0.0, dz=0.0, scale_stick=(1.0, 1.0), n_free=48,
                  with_zones=False):
    """Posed centreline (N x 3). Guided samples ride on their member; each free zone is a
    cubic Hermite tangent to the guided tube at both ends. Tower zone: v moves to the crossing
    v in the first V_RAMP_T of the zone. Stick zone: (start, end) tangent scales.
    with_zones=True also returns the zone name of every sample."""
    cl = centreline(name)
    posed = [(place(m, p, boom, stick, bucket), zone) for m, p, zone in cl]
    out, zones, i = [], [], 0
    while i < len(posed):
        p, zone = posed[i]
        if not zone.startswith("free"):
            out.append(p)
            zones.append(zone)
            i += 1
            continue
        j = i
        while j < len(posed) and posed[j][1] == zone:
            j += 1
        a, b = posed[i - 1][0], posed[min(j, len(posed) - 1)][0]
        ta = a - posed[i - 2][0]
        tb = posed[min(j + 1, len(posed) - 1)][0] - b
        if zone == "free_boom":
            seg = np.array(_hermite(a, ta, b, tb, n_free, 1.0))
            t = np.linspace(0, 1, n_free)
            seg[:, 1] = a[1] + (b[1] - a[1]) * np.array([smooth(min(x / V_RAMP_T, 1.0)) for x in t])
            seg = list(seg[1:-1])
        else:
            seg = _hermite(a, ta, b, tb, n_free, scale_stick)[1:-1]
        out.extend(seg)
        zones.extend([zone] * len(seg))
        i = j
    arr = np.array(out)
    arr[:, 2] += dz
    return (arr, zones) if with_zones else arr


def path_length(poly):
    return float(np.sum(np.linalg.norm(np.diff(poly, axis=0), axis=1)))


def stick_zone_scale(name, boom=0.0, stick=0.0, bucket=0.0):
    """Natural shape across the stick joint: the (start, end) tangent scales with the gentlest
    worst bend (a stand-in for the tube's minimum bending energy; the tube slides through the
    boom guides)."""
    if TUBES[name][0] != "bucket":
        return (1.0, 1.0)
    best = (-1.0, (1.0, 1.0))
    grid = np.linspace(0.5, 2.0, 7)
    for s0 in grid:
        for s1 in grid:
            r = _stick_zone_min_r(name, boom, stick, bucket, (s0, s1))
            if r > best[0]:
                best = (r, (s0, s1))
    # refine around the best
    c0, c1 = best[1]
    for s0 in np.linspace(c0 - 0.2, c0 + 0.2, 5):
        for s1 in np.linspace(c1 - 0.2, c1 + 0.2, 5):
            if min(s0, s1) <= 0.2:
                continue
            r = _stick_zone_min_r(name, boom, stick, bucket, (s0, s1))
            if r > best[0]:
                best = (r, (float(s0), float(s1)))
    return best[1]


def _stick_zone_min_r(name, boom, stick, bucket, sc):
    poly, zones = tube_polyline(name, boom, stick, bucket, 0.0, sc, with_zones=True)
    idx = [i for i, z in enumerate(zones) if z == "free_stick"]
    lo, hi = max(idx[0] - 3, 0), min(idx[-1] + 4, len(poly))
    return min_bend_radius(poly[lo:hi])


def natural(name, boom=0.0, stick=0.0, bucket=0.0, dz=0.0):
    """Natural shape of the arm part of a tube (tube top -> stop): stick zone at its gentlest shape.
    The tube keeps this shape at every pose; length changes slide down to the conduit."""
    return tube_polyline(name, boom, stick, bucket, dz, stick_zone_scale(name, boom, stick, bucket))


def natural_with_zones(name, boom=0.0, stick=0.0, bucket=0.0, dz=0.0):
    return tube_polyline(name, boom, stick, bucket, dz, stick_zone_scale(name, boom, stick, bucket), with_zones=True)


# ---------------------------------------------------------------- conduit slack
# straight conduit run between the control-box fitting (tube anchor) and the pedestal fitting
# (socket floor to socket floor)
CONDUIT_RUN = (ex.PED_U[0] + ex.T_WOOD + ex.CONDUIT_SOCKET) - (ex.BOX_U[1] - ex.T_WOOD - ex.CONDUIT_SOCKET)
CONDUIT_ID = ex.CONDUIT_ID        # 2" sch 40 PVC
CONDUIT_HELIX_R_MAX = CONDUIT_ID / 2 - ex.PTFE_OD / 2 - 4.0   # leave room for the other cables


def conduit_helix(slack, n=120):
    """Spare tube length stored in the conduit run as one helix turn (a tube pushed into a
    straight conduit coils like this). Returns (helix radius, bend radius, turning angle rad,
    polyline in the run frame: x along the conduit)."""
    ell = CONDUIT_RUN
    r_h = math.sqrt(max((ell + slack) ** 2 - ell ** 2, 0.0)) / (2 * math.pi)
    c = ell / (2 * math.pi)
    R = (r_h ** 2 + c ** 2) / r_h if r_h > 1e-9 else float("inf")
    turn = (ell + slack) / R
    t = np.linspace(0, 1, n)
    poly = np.column_stack((ell * t, r_h * (1 - np.cos(2 * math.pi * t)), r_h * np.sin(2 * math.pi * t)))
    return r_h, R, turn, poly


def min_bend_radius(poly):
    r = []
    for a, b, c in zip(poly[:-2], poly[1:-1], poly[2:]):
        ab, bc, ca = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
        cross = np.linalg.norm(np.cross(b - a, c - a))
        if cross < 1e-9 or min(ab, bc) < 1e-6:
            continue
        r.append(ab * bc * ca / (2 * cross))
    return min(r) if r else float("inf")


def tube_stop(name):
    """(member, point, direction) of the tube's anchored end at its stop boss, original pose."""
    cl = centreline(name)
    m, p, _ = cl[-1]
    d = p - cl[-2][1]
    return m, p, d / np.linalg.norm(d)


def bulkhead_clamp_points():
    """Bucket-tube clamp points in the boom bulkhead (original pose): [(point3, dir3)]."""
    out = []
    for name in ("bucket_hi", "bucket_lo"):
        cl = centreline(name)
        idx = max(i for i, (m, p, z) in enumerate(cl) if z == "boom")
        p, q = cl[idx][1], cl[idx - 1][1]
        d = p - q
        out.append((p, d / np.linalg.norm(d)))
    return out
