#!/usr/bin/env python3
"""EX-MA control box, pedestal and sandbox: wood panels, hardware, box-side rope paths, cut list.

Design frame as everywhere else (u toward the arm, v = operator's left, z up; mm). All wood is
12 mm plywood. Panels are axis-aligned boxes with their holes and slots.

Run:  <cadenv>/bin/python 2026-09-24-build-box.py
Writes STEP/2026-09-24-{control-box,pedestal,sandbox}-wood.step and 2026-09-24-cut-list.md.
Other scripts import it for panels(), hardware() and the rope / sleeve paths.
"""
import importlib.util
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


ex = _load("exma", "2026-09-24-exma_common.py")
T = ex.T_WOOD

# ---------------------------------------------------------------- parameters
CONDUIT_HOLE_D = 62.0             # 2" PVC OD 60.3
ROD_HOLE_D = 8.5                  # 5/16" rod
BOLT_HOLE_D = 4.6                 # M3 bolts (with washers) through fitting + panel + sandbox wall
SLOT_W = ex.HANDLE_D + 1.1        # lever slot width (5/16" rod handle)
SPOOL_HOLE_D = 24.4               # top panel = upper bearing of the spool tube (Ø24)
PEX_HOLE_D = ex.TURRET_TUBE_OD + 4.0   # pedestal top: clearance only
BUSHING_HOLE_D = 30.4             # pedestal shelf: slew-tube-bushing body Ø30
BLOCK_U = (ex.AXLE_U - 30.0, ex.AXLE_U + 30.0)
BLOCK_TOP = ex.AXLE_Z + 30.0
SHELF_Z = (-63.0, -51.0)
SHELF_U0 = ex.PED_U[0] + T + ex.FIT_T + 2.0     # shelf and cleats start just past the pedestal fitting
KNOB_R = 18.0
R_LEVER = ex.DRUM["lever"]["pitch"] / 2
R_SLEW = ex.DRUM["slew"]["pitch"] / 2
SLEEVE_BEND_R = 30.0              # minimum bend radius of the slew PTFE sleeves


def lever_deg(j):
    """Full lever swing for joint j (deg): joint drum travel over the Ø60 control drum."""
    lo, hi = ex.WORKING[j]
    return (ex.DRUM[j]["pitch"] / 2) * (hi - lo) / R_LEVER


def slot_length(j):
    """Top-panel slot = the lever's hard stop: the handle rod touches the slot end at the top face."""
    a = math.radians(lever_deg(j) / 2)
    h = ex.BOX_Z[1] - ex.AXLE_Z
    return 2 * (h * math.tan(a) + (ex.HANDLE_D / 2) / math.cos(a))


# ---------------------------------------------------------------- panels
@dataclass
class Panel:
    name: str
    group: str                    # control-box / pedestal / sandbox
    lo: tuple
    hi: tuple
    holes: list = field(default_factory=list)   # (kind, axis, centre (u, v, z), d or (len, w), note)
    note: str = ""

    @property
    def size(self):
        return tuple(round(h - l, 1) for l, h in zip(self.lo, self.hi))

    @property
    def normal(self):
        return "uvz"[int(np.argmin(self.size))]


def fitting_bolts(fit_origin_uvz, local_x_is):
    """4 corner bolt positions of a conduit end fitting (local +-40, +-40)."""
    u, v, z = fit_origin_uvz
    return [(u, v + sx * 40.0 * local_x_is, z + sy * 40.0) for sx in (-1, 1) for sy in (-1, 1)]


def panels():
    P = []
    u0, u1 = ex.BOX_U
    v0, v1 = ex.BOX_V
    z0, z1 = ex.BOX_Z
    fit_box = (u1 - T, ex.MOUTH_V, ex.COND_Z)
    box_extra = [(u1 - T / 2, v0 + 25.0, z0 + T + 25.0), (u1 - T / 2, v1 - 25.0, z0 + T + 25.0)]
    # control box
    P.append(Panel("box floor", "control-box", (u0, v0, z0), (u1, v1, z0 + T),
                   [("hole", "z", (ex.WHEEL_C[0], ex.WHEEL_C[1], z0), ROD_HOLE_D, "slew spool axle (nut + washer in a Ø22 x 7 counterbore from below)")]))
    front = Panel("box front", "control-box", (u1 - T, v0, z0 + T), (u1, v1, z1 - T),
                  [("hole", "u", (u1, ex.MOUTH_V, ex.COND_Z), CONDUIT_HOLE_D, "2in conduit")])
    for p in fitting_bolts(fit_box, -1):
        front.holes.append(("hole", "u", p, BOLT_HOLE_D, "fitting bolt (M3 × 35 through the sandbox wall)"))
    for p in box_extra:
        front.holes.append(("hole", "u", p, BOLT_HOLE_D, "box-to-sandbox bolt (M3 × 30)"))
    P.append(front)
    P.append(Panel("box rear", "control-box", (u0, v0, z0 + T), (u0 + T, v1, z1 - T)))
    P.append(Panel("box right side", "control-box", (u0 + T, v0, z0 + T), (u1 - T, v0 + T, z1 - T)))
    P.append(Panel("box left side", "control-box", (u0 + T, v1 - T, z0 + T), (u1 - T, v1, z1 - T)))
    top = Panel("box top (removable)", "control-box", (u0, v0, z1 - T), (u1, v1, z1),
                [("hole", "z", (ex.WHEEL_C[0], ex.WHEEL_C[1], z1), SPOOL_HOLE_D, "spool tube bearing")],
                note="screwed to the sides, front and rear; lift off for service")
    for j, (vh, vd) in ex.LEVERS.items():
        top.holes.append(("slot", "z", (ex.AXLE_U, vh, z1), (slot_length(j), SLOT_W),
                          f"{j} lever slot = hard stop ({lever_deg(j):.0f} deg swing)"))
    P.append(top)
    for sgn, nm in ((1, "left"), (-1, "right")):
        va, vb = sorted((sgn * ex.AXLE_BLOCK_V[0], sgn * ex.AXLE_BLOCK_V[1]))
        P.append(Panel(f"axle bearing block {nm}", "control-box", (BLOCK_U[0], va, z0 + T), (BLOCK_U[1], vb, BLOCK_TOP),
                       [("hole", "v", (ex.AXLE_U, 0.0, ex.AXLE_Z), ROD_HOLE_D, "5/16in lever axle")],
                       note="screwed to the floor from below (2 x #6)"))
    # pedestal
    pu0, pu1 = ex.PED_U
    pv0, pv1 = ex.PED_V
    pz0, pz1 = ex.PED_Z
    fit_ped = (pu0 + T, ex.PED_FIT_V, ex.COND_Z)
    ptop = Panel("pedestal top", "pedestal", (pu0, pv0, pz1 - T), (pu1, pv1, pz1),
                 [("hole", "z", (0.0, 0.0, pz1), PEX_HOLE_D, "PEX turret tube clearance")])
    for k in range(4):
        a = math.radians(45 + 90 * k)
        ptop.holes.append(("hole", "z", (38.0 * math.cos(a), 38.0 * math.sin(a), pz1), 3.0, "pilot, #8 screw from the base"))
    P.append(ptop)
    wall = Panel("pedestal wall -u (conduit)", "pedestal", (pu0, pv0, pz0), (pu0 + T, pv1, pz1 - T),
                 [("hole", "u", (pu0, ex.PED_FIT_V, ex.COND_Z), CONDUIT_HOLE_D, "2in conduit")])
    for p in fitting_bolts(fit_ped, 1):
        wall.holes.append(("hole", "u", p, BOLT_HOLE_D, "fitting bolt (M3 × 25)"))
    P.append(wall)
    P.append(Panel("pedestal wall +u (removable access)", "pedestal", (pu1 - T, pv0, pz0), (pu1, pv1, pz1 - T),
                   note="screwed on; remove to reach the slew drum clamp and the elbow"))
    P.append(Panel("pedestal wall -v", "pedestal", (pu0 + T, pv0, pz0), (pu1 - T, pv0 + T, pz1 - T)))
    P.append(Panel("pedestal wall +v", "pedestal", (pu0 + T, pv1 - T, pz0), (pu1 - T, pv1, pz1 - T)))
    P.append(Panel("pedestal shelf", "pedestal", (SHELF_U0, pv0 + T, SHELF_Z[0]), (pu1 - T, pv1 - T, SHELF_Z[1]),
                   [("hole", "z", (0.0, 0.0, SHELF_Z[1]), BUSHING_HOLE_D, "slew-tube-bushing")],
                   note="rests on the two cleats; carries the PEX bushing just above the slew drum"))
    for sgn in (-1, 1):
        va, vb = (pv0 + T, pv0 + 2 * T) if sgn < 0 else (pv1 - 2 * T, pv1 - T)
        P.append(Panel(f"pedestal shelf cleat {'-v' if sgn < 0 else '+v'}", "pedestal",
                       (SHELF_U0, va, SHELF_Z[0] - T), (pu1 - T, vb, SHELF_Z[0])))
    # sandbox
    su0, su1 = ex.SB_U
    sv0, sv1 = ex.SB_V
    sz0, sz1 = ex.SB_Z
    P.append(Panel("sandbox floor", "sandbox", (su0, sv0, sz0 - T), (su1, sv1, sz0),
                   note="the pedestal and the elbow support screw to it"))
    sw = Panel("sandbox wall -u (box side)", "sandbox", (su0, sv0, sz0), (su0 + T, sv1, sz1),
               [("hole", "u", (su0, ex.MOUTH_V, ex.COND_Z), CONDUIT_HOLE_D, "2in conduit (seal with silicone)")])
    for p in fitting_bolts(fit_box, -1) + box_extra:
        sw.holes.append(("hole", "u", (su0, p[1], p[2]), BOLT_HOLE_D, "bolt from the control box"))
    P.append(sw)
    P.append(Panel("sandbox wall +u", "sandbox", (su1 - T, sv0, sz0), (su1, sv1, sz1)))
    P.append(Panel("sandbox wall -v", "sandbox", (su0 + T, sv0, sz0), (su1 - T, sv0 + T, sz1)))
    P.append(Panel("sandbox wall +v", "sandbox", (su0 + T, sv1 - T, sz0), (su1 - T, sv1, sz1)))
    return P


def panel_solid(p):
    import cadquery as cq
    c = [(l + h) / 2 for l, h in zip(p.lo, p.hi)]
    s = cq.Workplane("XY").box(*[h - l for l, h in zip(p.lo, p.hi)]).translate(c)
    n = p.normal
    for kind, axis, ctr, d, _ in p.holes:
        L = 3 * max(p.size)
        if kind == "hole":
            wp = {"u": "YZ", "v": "XZ", "z": "XY"}[axis]
            cyl = cq.Workplane(wp).circle(d / 2).extrude(L, both=True)
            pos = list(ctr)
            s = s.cut(cyl.translate(pos))
        else:                                                     # slot along u in a z-normal panel
            ln, w = d
            sl = cq.Workplane("XY").slot2D(ln, w).extrude(L, both=True).translate(ctr)
            s = s.cut(sl)
    assert n in "uvz"
    return s


# ---------------------------------------------------------------- hardware (checks + renders)
def lever_pose_T(j, deg):
    """4x4: rotate about the lever axle (axis +v) by deg; + tilts the handle toward +u."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    R = np.eye(4)
    # handle up (+z) tilts toward +u for deg > 0: rotation about +v by -deg in the u-z plane
    R[0, 0], R[0, 2], R[2, 0], R[2, 2] = c, s, -s, c
    T1, T2 = np.eye(4), np.eye(4)
    T1[0, 3], T1[2, 3] = -ex.AXLE_U, -ex.AXLE_Z
    T2[0, 3], T2[2, 3] = ex.AXLE_U, ex.AXLE_Z
    return T2 @ R @ T1


def lever_handle_mesh(j, deg=0.0):
    """5/16" rod (from the hub socket floor into the knob) + printed knob, posed."""
    import trimesh
    vh = ex.LEVERS[j][0]
    a = np.array([ex.AXLE_U, vh, ex.AXLE_Z + 9.0])
    b = np.array([ex.AXLE_U, vh, ex.AXLE_Z + ex.HANDLE_LEN])
    rod = trimesh.creation.cylinder(radius=ex.HANDLE_D / 2, segment=np.array([a, b + [0, 0, ex.KNOB_BORE_DEPTH]]),
                                    sections=32)
    knob = trimesh.creation.icosphere(subdivisions=2, radius=KNOB_R)
    knob.apply_translation(b + [0, 0, KNOB_R - 4.0])
    m = ex.from_manifold(ex.to_manifold(rod) + ex.to_manifold(knob))       # one closed solid
    m.apply_transform(lever_pose_T(j, deg))
    return m


def hardware():
    """name -> (trimesh, colour key). Rods (axles, handles), conduit, copper elbow, PEX tube."""
    import trimesh
    H = {}
    cyl = lambda a, b, r, n=32: trimesh.creation.cylinder(radius=r, segment=np.array([a, b], float), sections=n)
    H["lever axle (5/16in rod)"] = (cyl((ex.AXLE_U, -ex.AXLE_BLOCK_V[1] - 10, ex.AXLE_Z),
                                        (ex.AXLE_U, ex.AXLE_BLOCK_V[1] + 10, ex.AXLE_Z), ex.LEVER_AXLE_D / 2), "steel")
    H["slew spool axle (5/16in rod)"] = (cyl((*ex.WHEEL_C, ex.BOX_Z[0]), (*ex.WHEEL_C, ex.BOX_Z[1] + 32.0),
                                             ex.LEVER_AXLE_D / 2), "steel")
    for j in ex.LEVERS:
        H[f"{j} handle"] = (lever_handle_mesh(j), "steel")
    u_a = ex.BOX_U[1] - T - ex.CONDUIT_SOCKET
    u_b = ex.PED_U[0] + T + ex.CONDUIT_SOCKET
    c = trimesh.creation.annulus(r_min=ex.CONDUIT_ID / 2, r_max=ex.COND_R, height=u_b - u_a, sections=64)
    c.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0)))
    c.apply_translation(((u_a + u_b) / 2, ex.MOUTH_V, ex.COND_Z))
    H["2in PVC conduit"] = (c, "pvc")
    # copper: straight leg from the pedestal fitting socket to the bend, R30 sweep, up to the PEX end
    rc = ex.COPPER_OD / 2
    u_fit = ex.PED_U[0] + T + ex.FIT_T - 8.0
    zc = ex.Z_ARM_LAYER
    pts = [(u_fit, 0.0, zc), (-ex.ELBOW_R, 0.0, zc)]
    for k in range(1, 13):
        th = math.radians(90 - 90 * k / 12)
        pts.append((-ex.ELBOW_R + ex.ELBOW_R * math.cos(th), 0.0, zc + ex.ELBOW_R - ex.ELBOW_R * math.sin(th)))
    H["1/2in copper elbow"] = (tube_mesh(np.array(pts), rc), "copper")
    H["3/4in PEX turret tube"] = (cyl((0, 0, ex.TUBE_Z[0]), (0, 0, ex.TUBE_Z[1]), ex.TURRET_TUBE_OD / 2, 48), "pex")
    return H


def tube_mesh(poly, r, sections=16):
    """Swept circle along a polyline (for ropes, sleeves, pipes)."""
    import trimesh
    parts = []
    for a, b in zip(poly[:-1], poly[1:]):
        if np.linalg.norm(b - a) > 1e-6:
            parts.append(trimesh.creation.cylinder(radius=r, segment=np.array([a, b]), sections=sections))
    for p in poly[1:-1]:
        s = trimesh.creation.icosphere(subdivisions=1, radius=r)
        s.apply_translation(p)
        parts.append(s)
    return trimesh.util.concatenate(parts)


# ---------------------------------------------------------------- box rope paths
def box_fitting_hole(circuit_or_slew, row_or_sign, face="box"):
    """Design position of a hole on the box conduit fitting. face 'box' = box-side face,
    'conduit' = conduit-side (socket floor)."""
    x_local = {"boom": -4.0, "stick": 0.0, "bucket": 4.0}
    u = ex.BOX_U[1] - T - (ex.FIT_T if face == "box" else ex.CONDUIT_SOCKET)
    if circuit_or_slew == "slew":
        return np.array([u, ex.MOUTH_V + row_or_sign * ex.FIT_SLEW_X, ex.COND_Z + ex.FIT_SLEW_Y])
    x = x_local[circuit_or_slew]
    return np.array([u, ex.MOUTH_V - x, ex.COND_Z + ex.FIT_ARM_ROWS[row_or_sign]])


def lever_strands(j, deg=0.0):
    """Both strands of lever j at lever angle deg: straight lines from the drum tangent point to the
    box fitting hole. Returns [dict(name, tangent(3), hole(3), dep_deg, wrap_deg, fleet_deg, entry_deg)].
    Row 0 (upper hole) takes the upper strand; the anchors sit at design 180 -+ 25 deg (drum frame)."""
    vd = ex.LEVERS[j][1]
    C = np.array([ex.AXLE_U, ex.AXLE_Z])
    out = []
    for row, (name, side, anchor0) in enumerate((("upper", +1, 155.0), ("lower", -1, 205.0))):
        H = box_fitting_hole(j, row)
        h2 = np.array([H[0], H[2]])
        d = h2 - C
        dist = np.linalg.norm(d)
        base = math.degrees(math.atan2(d[1], d[0]))
        t_ang = base + side * (90.0 - math.degrees(math.asin(R_LEVER / dist)))
        tp2 = C + R_LEVER * np.array([math.cos(math.radians(t_ang)), math.sin(math.radians(t_ang))])
        tp = np.array([tp2[0], vd, tp2[1]])
        anchor = anchor0 - deg                      # the drum turns with the lever (+deg = clockwise here)
        wrap = (anchor - t_ang) if side > 0 else ((t_ang + 360.0) - anchor)
        seg = H - tp
        fleet = math.degrees(math.asin(abs(seg[1]) / np.linalg.norm(seg)))
        entry = math.degrees(math.acos(abs(seg[0]) / np.linalg.norm(seg)))   # vs the fitting hole axis (u)
        out.append(dict(name=f"{j} {name}", tangent=tp, hole=H, dep_deg=t_ang, wrap_deg=wrap, fleet_deg=fleet,
                        entry_deg=entry, circuit=j))
    return out


def dubins(p0, h0, p1, h1, R):
    """Shortest circle-straight-circle path (plan view) from pose (p0, heading h0) to (p1, h1),
    both headings in radians. Returns (length, polyline Nx2, total turning rad)."""
    best = None
    for s0 in (1, -1):              # +1 = left turn
        for s1 in (1, -1):
            c0 = p0 + R * s0 * np.array([-math.sin(h0), math.cos(h0)])
            c1 = p1 + R * s1 * np.array([-math.sin(h1), math.cos(h1)])
            dc = c1 - c0
            D = np.linalg.norm(dc)
            if s0 == s1:
                th = math.atan2(dc[1], dc[0])
                L_s = D
            else:
                if D < 2 * R:
                    continue
                th = math.atan2(dc[1], dc[0]) + s0 * math.asin(2 * R / D)     # inner tangent
                L_s = math.sqrt(D * D - 4 * R * R)
            a0 = (s0 * (th - h0)) % (2 * math.pi)
            a1 = (s1 * (h1 - th)) % (2 * math.pi)
            L = R * (a0 + a1) + L_s
            if best is None or L < best[0]:
                best = (L, s0, s1, th, a0, a1, c0, c1, L_s)
    L, s0, s1, th, a0, a1, c0, c1, L_s = best
    pts = []
    for k in range(int(a0 / math.radians(3)) + 2):
        a = h0 + s0 * min(a0, k * math.radians(3))
        pts.append(c0 + R * s0 * np.array([math.sin(a), -math.cos(a)]))
    q0 = pts[-1]
    q1 = q0 + L_s * np.array([math.cos(th), math.sin(th)])
    pts.append(q1)
    for k in range(1, int(a1 / math.radians(3)) + 2):
        a = th + s1 * min(a1, k * math.radians(3))
        pts.append(c1 + R * s1 * np.array([math.sin(a), -math.cos(a)]))
    pts[-1] = np.array(p1, float)
    return L, np.array(pts), a0 + a1


def slew_sleeve(lane):
    """PTFE sleeve of one slew rope: box post -> box fitting -> conduit -> pedestal fitting counterbore.
    Returns dict(poly (N x 3), length, turning (rad), min_R)."""
    sign = 1 if lane == "A" else -1
    dep = ex.spool_departures()[lane]
    z = ex.Z_SLEW_LAYER
    start = dep["post"] + 8.0 * dep["dir"]                         # sleeve leaves the post's far face
    h_start = math.atan2(dep["dir"][1], dep["dir"][0])
    fb = box_fitting_hole("slew", sign, "box")
    fc = box_fitting_hole("slew", sign, "conduit")
    L1, p1, t1 = dubins(start, h_start, fb[:2], 0.0, SLEEVE_BEND_R)
    ped = ex.pedestal_slew_line(sign)
    L2, p2, t2 = dubins(fc[:2], 0.0, ped["entry"], ped["gamma"] * sign, SLEEVE_BEND_R)
    poly = [np.array([x, y, z]) for x, y in p1] + [np.array([x, y, z]) for x, y in p2]
    # the counterbore holds the sleeve's last 11 mm along the angled hole
    end = np.array([*(ped["entry"] + 11.0 * np.array([math.cos(ped["gamma"]), sign * math.sin(ped["gamma"])])), z])
    poly.append(end)
    poly = np.array(poly)
    L = float(np.sum(np.linalg.norm(np.diff(poly, axis=0), axis=1)))
    return dict(poly=poly, length=L, turning=t1 + t2, lane=lane)


def slew_rope_free(lane):
    """Bare rope segments of one slew rope: spool tangent -> post, pedestal fitting exit -> drum tangent."""
    sign = 1 if lane == "A" else -1
    dep = ex.spool_departures()[lane]
    z = ex.Z_SLEW_LAYER
    zl = z + (ex.SLEW_LANE_OFF if lane == "A" else -ex.SLEW_LANE_OFF)
    ped = ex.pedestal_slew_line(sign)
    box = np.array([[*dep["tangent"], zl], [*dep["post"], z]])
    pedes = np.array([[*ped["exit"], z], [*ped["tangent"], zl]])
    return box, pedes


def slew_wraps(slew_deg):
    """Rope wrap (deg) on the spool and the pedestal drum per lane at slew angle slew_deg (+ = CCW
    seen from above, spool and drum turn together 1:1)."""
    dep = ex.spool_departures()
    out = {}
    for lane, sign in (("A", 1), ("B", -1)):
        # pedestal drum: lane A rope leaves CCW at the +v tangent and lies on smaller angles
        t = ex.pedestal_slew_line(sign)["tangent_deg"]
        anchor = t - sign * 180.0 + slew_deg
        w_ped = sign * (t - anchor)
        # spool: lane A leaves clockwise at dep A and lies on larger angles; anchor at dep B
        a_sp = dep["B" if lane == "A" else "A"]["tangent_deg"] + slew_deg
        w_sp = (a_sp - dep[lane]["tangent_deg"]) % 360.0 if lane == "A" else (dep[lane]["tangent_deg"] - a_sp) % 360.0
        out[lane] = (w_sp, w_ped)
    return out


# ---------------------------------------------------------------- cut list
def cut_list(P):
    L = ["# EX-MA control box, pedestal and sandbox — cut list", "",
         "All parts 12 mm plywood (1/2in also works; hole positions are measured from the panel's lower-left "
         "corner as seen from the named side). Sizes in mm, rounded to 0.5.", ""]
    groups = {}
    for p in P:
        groups.setdefault(p.group, []).append(p)
    for g, ps in groups.items():
        L += [f"## {g}", "", "| Part | Qty | Length × width × thick | Notes |", "|---|---|---|---|"]
        for p in ps:
            dims = sorted(p.size, reverse=True)
            L.append(f"| {p.name} | 1 | {dims[0]:.1f} × {dims[1]:.1f} × {dims[2]:.1f} | {p.note} |")
        L.append("")
        for p in ps:
            if not p.holes:
                continue
            L += [f"**{p.name}** — holes / slots", "", "| Feature | Size | Position (a, b) | Purpose |", "|---|---|---|---|"]
            ax = [i for i in range(3) if "uvz"[i] != p.normal]
            for kind, axis, ctr, d, note in p.holes:
                a, b = ctr[ax[0]] - p.lo[ax[0]], ctr[ax[1]] - p.lo[ax[1]]
                size = f"Ø{d:.1f}" if kind == "hole" else f"{d[0]:.1f} × {d[1]:.1f} slot (along {'uvz'[ax[0]]})"
                L.append(f"| {kind} | {size} | ({a:.1f}, {b:.1f}) along ({'uvz'[ax[0]]}, {'uvz'[ax[1]]}) | {note} |")
            L.append("")
    L += ["## Other cut stock", "",
          f"- 2in sch 40 PVC conduit: {ex.PED_U[0] + T + ex.CONDUIT_SOCKET - (ex.BOX_U[1] - T - ex.CONDUIT_SOCKET):.0f} mm "
          "(socket floor to socket floor).",
          f"- 5/16in rod: lever axle {2 * ex.AXLE_BLOCK_V[1] + 20:.0f} mm; slew spool axle "
          f"{ex.BOX_Z[1] + 32.0 - ex.BOX_Z[0]:.0f} mm.",
          f"- 5/16in rod lever handles: 3 × {ex.HANDLE_LEN - 9.0 + ex.KNOB_BORE_DEPTH:.0f} mm.",
          "- 8-32 rod (joint pins only): 2 × 42 mm, 2 × 22 mm, 1 × 65 mm.", ""]
    return "\n".join(L)


def main():
    import cadquery as cq
    P = panels()
    out_step = ex.OUT / "STEP"
    for g in ("control-box", "pedestal", "sandbox"):
        solids = [panel_solid(p).val() for p in P if p.group == g]
        comp = cq.Compound.makeCompound(solids)
        cq.exporters.export(cq.Workplane("XY").newObject([comp]), str(out_step / f"2026-09-24-{g}-wood.step"))
        print(f"{g:12s} {len(solids)} panels -> STEP/2026-09-24-{g}-wood.step")
    (ex.OUT / "2026-09-24-cut-list.md").write_text(cut_list(P))
    print("cut list -> 2026-09-24-cut-list.md")
    for j in ex.LEVERS:
        print(f"{j:6s} lever swing {lever_deg(j):5.1f} deg  slot {slot_length(j):6.1f} x {SLOT_W:.1f}")


if __name__ == "__main__":
    main()
