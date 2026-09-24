#!/usr/bin/env python3
"""EX-MA concept scene generator (pre-CAD).

Reads the frozen EX-MA exterior mesh, converts it to design scale in the arm
frame, drops the internal mechanism shells that the simplified design removes,
and adds placeholder geometry for the proposed mechanism, control box, conduit
and cable paths. Writes a data.js consumed by 2026-09-24-concept-viewer.html.

Frames
  design frame (mm): u = along arm from slew axis, v = lateral (+v = operator's
  left when facing the excavator from the control box), z = up from base bottom.
  three.js frame: (x, y, z) = (u, z, -v).

Usage: python3 2026-09-24-concept-scene.py <path/to/EX-MA Colored ARM.stl> <out/data.js>
No CAD/STL/STEP files are written.
"""
import base64
import json
import math
import struct
import sys
from array import array

# ---------------------------------------------------------------- parameters
STL_SCALE = 0.710351508            # 3MF preview scale -> design = STL / this
S = 1.0 / STL_SCALE
ARM_ROT = math.atan2(0.518966256, 0.485049781)   # 3MF build rotation about Z
BASE_CX, BASE_CY = 55.72, 50.59                   # slew axis in STL XY

CABLE_R = 1.6                      # drawn radius (2x the real 0.8 mm) for visibility
PTFE_R = 2.0                       # 4 mm OD PTFE
COL = dict(boom="#1fa84a", stick="#1f5fe0", bucket="#e02424", slew="#8a2be2",
           printed="#f08a24", steel="#9aa3ab", wood="#c9a06a", ply="#b98b55",
           pvc="#eeeeee", copper="#b87333", black="#2b2b2b", yellow="#F4EE2A",
           lime="#B6FF43", blue="#2323F7", sand="#e3d09c", ptfe="#f7f7f7")

# pivots (design frame, measured from the STL pin centres)
P_BOOM = (0.0, 102.0)              # (u, z)
P_STICK = (186.19, 196.86)
P_BUCKET = (344.80, 122.90)
R_BOOM, R_STICK, R_BUCKET, R_SLEW = 16.0, 13.0, 9.0, 55.0
R_LEVER = 24.0

# control box (design frame)
BOX_U = (-453.0, -203.0)
BOX_V = (-290.0, 115.0)
BOX_Z = (-160.0, 40.0)
T_WOOD = 12.0
AXLE_U, AXLE_Z = -360.0, -100.0
LEVERS = dict(boom=(70.0, 25.0), stick=(0.0, 0.0), bucket=(-70.0, -25.0))  # (handle v, drum v)
HANDLE_LEN = 225.0
WHEEL_C = (-340.0, -190.0)
WHEEL_Z = 75.0
MOUTH_U = -210.0

# conduit / pedestal
COND_Z, COND_R = -110.0, 30.0      # 2" PVC
Z_SLEW_LAYER, Z_ARM_LAYER = -88.0, -130.0
PED_U, PED_V, PED_Z = (-90.0, 90.0), (-90.0, 90.0), (-190.0, 0.0)
ELBOW_R = 30.0
TUBE_R = 13.35                     # 3/4" PVC OD 26.7
TUBE_Z = (-98.0, 75.0)

# printed slewing ring (turret <-> base); turret + arm lowered by TURRET_DZ
TURRET_DZ = -13.0                  # closes the gap left by the removed green ring
LOWER_ABOVE_Z = 18.0               # anything on the turret side above this height moves down
FLANGE_R, FLANGE_Z = 59.5, (17.0, 25.0)    # circular turret flange = inner race
RACE_R = (62.5, 70.0)              # base lower race rim / retaining ring radial span
BASE_RIM_Z, RET_RING_Z = (15.0, 21.0), (21.0, 27.0)
BALL_R, BALL_CIRCLE_R, BALL_Z, N_BALLS = 3.0, 61.0, 21.0, 56

# sandbox (24" x 24")
SB_U, SB_V, SB_Z = (-203.0, 407.0), (-305.0, 305.0), (-190.0, 40.0)
SAND_Z = -10.0


def t3(p):
    """design (u, v, z) -> three.js (x, y, z)"""
    return [round(p[0], 3), round(p[2], 3), round(-p[1], 3)]


# ---------------------------------------------------------------- EX-MA mesh
def load_exma(path):
    d = open(path, "rb").read()
    n = struct.unpack("<I", d[80:84])[0]
    vid, verts, tris = {}, [], []

    def V(p):
        k = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
        i = vid.get(k)
        if i is None:
            i = len(verts)
            vid[k] = i
            verts.append(k)
        return i

    for t in range(n):
        o = 84 + 50 * t
        f = struct.unpack("<12f", d[o:o + 48])
        tris.append((V(f[3:6]), V(f[6:9]), V(f[9:12])))
    par = list(range(len(verts)))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for a, b, c in tris:
        ra = find(a)
        par[find(b)] = ra
        par[find(c)] = ra
    ca, sa = math.cos(-ARM_ROT), math.sin(-ARM_ROT)
    L = []
    for x, y, z in verts:
        x, y = x - BASE_CX, y - BASE_CY
        L.append(((x * ca - y * sa) * S, (x * sa + y * ca) * S, z * S))
    comps = {}
    for t in tris:
        comps.setdefault(find(t[0]), []).append(t)
    # label shells by ascending min-u, matching the inspection report labels
    order = sorted(comps, key=lambda r: min(L[i][0] for t in comps[r] for i in t))
    labels = "0123456789ABCDEFGHIJKLMNOPQRS"
    return {labels[k]: (comps[r], L) for k, r in enumerate(order)}


# shell label -> (name, colour, group, clip-in-cutaway) ; missing labels are removed
KEEP = {
    "0": ("base", COL["black"], "exterior", True),
    "2": ("tower", COL["black"], "exterior", True),
    "3": ("boom", COL["yellow"], "exterior", True),
    "8": ("boom pin 8-32", COL["steel"], "exterior", False),
    "9": ("stick", COL["yellow"], "exterior", True),
    "D": ("stick pin 8-32", COL["steel"], "exterior", False),
    "E": ("bucket", COL["black"], "exterior", False),
    "G": ("bucket ear", COL["blue"], "exterior", False),
    "H": ("bucket ear", COL["blue"], "exterior", False),
    "I": ("bucket bracket", COL["black"], "exterior", False),
    "L": ("bucket pin 8-32", COL["steel"], "exterior", False),
    "O": ("bucket lug", COL["black"], "exterior", False),
    "P": ("bucket lug", COL["black"], "exterior", False),
}
REMOVED = {"4": "boom double-groove drum", "6": "boom idler", "7": "boom idler",
           "A": "stick double-groove drum", "B": "stick idler", "C": "stick idler",
           "F": "bucket drum + sleeve", "J": "cross pin", "K": "clip", "M": "cross pin",
           "N": "clip", "Q": "vertical pin", "R": "cross pin", "S": "vertical pin",
           "1": "green slew ring (old slew drum; drum now in pedestal)", "5": "base post cap"}

# internal features cut away from kept shells: label -> (max centroid radius, min centroid z)
BORE = {"0": (16.0, 15.2),   # base centre post removed -> floor bearing hole for 3/4in PVC
        "2": (15.0, 25.0)}   # tower centre boss bored to 26.7 for the PVC tube
FLANGE_CUT = {"2": 35.5}     # old square tower flange removed (replaced by circular flange proxy)


def mesh_records(shells):
    out = []
    for lab, (name, color, group, clip) in KEEP.items():
        tris, L = shells[lab]
        arr = array("f")
        rmax, zmin = BORE.get(lab, (-1.0, 0.0))
        for t in tris:
            cu, cv, cz = (sum(L[i][k] for i in t) / 3 for k in range(3))
            if math.hypot(cu, cv) < rmax and cz > zmin:
                continue
            if cz < FLANGE_CUT.get(lab, -1e9):
                continue
            dz = 0.0 if lab == "0" else TURRET_DZ     # base stays; turret and arm drop
            for i in t:
                arr.extend(t3((L[i][0], L[i][1], L[i][2] + dz)))
        out.append(dict(name=name, label=lab, color=color, group=group, clip=clip,
                        b64=base64.b64encode(arr.tobytes()).decode()))
    return out


# ---------------------------------------------------------------- 2D helpers
def tangent_wrap(C, r, P, anchor_deg, sense, n=24):
    """Cable leaving a drum toward external point P.

    C, P are 2D points in the drum plane. The cable is anchored on the drum at
    anchor_deg, wraps in `sense` (+1 CCW, -1 CW) and leaves tangentially toward P.
    Returns the 2D polyline from the anchor to P."""
    dx, dy = P[0] - C[0], P[1] - C[1]
    d = math.hypot(dx, dy)
    phi = math.atan2(dy, dx)
    al = math.acos(min(1.0, r / d))
    best = None
    for th in (phi + al, phi - al):
        tdir = (-math.sin(th) * sense, math.cos(th) * sense)
        T = (C[0] + r * math.cos(th), C[1] + r * math.sin(th))
        if tdir[0] * (P[0] - T[0]) + tdir[1] * (P[1] - T[1]) > 0:
            best = th
    a0 = math.radians(anchor_deg)
    sweep = (best - a0) * sense % (2 * math.pi)
    pts = [(C[0] + r * math.cos(a0 + sense * sweep * k / n), C[1] + r * math.sin(a0 + sense * sweep * k / n))
           for k in range(n + 1)]
    return pts + [tuple(P)], math.degrees(sweep)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def boom_pt(s, off, v):
    ang = math.atan2(P_STICK[1] - P_BOOM[1], P_STICK[0] - P_BOOM[0])
    return (P_BOOM[0] + s * math.cos(ang) - off * math.sin(ang), v,
            P_BOOM[1] + s * math.sin(ang) + off * math.cos(ang))


def stick_pt(s, off, v):
    ang = math.atan2(P_BUCKET[1] - P_STICK[1], P_BUCKET[0] - P_STICK[0])
    return (P_STICK[0] + s * math.cos(ang) - off * math.sin(ang), v,
            P_STICK[1] + s * math.sin(ang) + off * math.cos(ang))


BOOM_ANG = math.degrees(math.atan2(P_STICK[1] - P_BOOM[1], P_STICK[0] - P_BOOM[0]))
STICK_ANG = math.degrees(math.atan2(P_BUCKET[1] - P_STICK[1], P_BUCKET[0] - P_STICK[0]))


# ---------------------------------------------------------------- proxies
prox = []


def cyl(a, b, r, color, group, name="", opacity=1.0, seg=40):
    prox.append(dict(type="cyl", a=t3(a), b=t3(b), r=r, color=color, group=group, name=name,
                     opacity=opacity, seg=seg))


def box(mn, mx, color, group, name="", opacity=1.0):
    prox.append(dict(type="box", min=t3((mn[0], mx[1], mn[2])), max=t3((mx[0], mn[1], mx[2])),
                     color=color, group=group, name=name, opacity=opacity))


def sph(c, r, color, group, name=""):
    prox.append(dict(type="sph", c=t3(c), r=r, color=color, group=group, name=name))


def ring(r_in, r_out, z0, z1, color, group, name=""):
    """Annulus about the slew axis (vertical), in final coordinates (never lowered)."""
    prox.append(dict(type="ring", r_in=r_in, r_out=r_out, y0=z0, y1=z1, color=color, group=group,
                     name=name, nolower=True))


def path(pts, r, color, group, name="", opacity=1.0):
    prox.append(dict(type="path", pts=[t3(p) for p in pts], r=r, color=color, group=group,
                     name=name, opacity=opacity))


def drum_v(C_uz, v0, r_pitch, width, group, name, flange=4.0):
    """Single-groove drum on an axis parallel to v."""
    u, z = C_uz
    cyl((u, v0 - width / 2, z), (u, v0 - width / 2 + 2.5, z), r_pitch + flange, COL["printed"], group, name)
    cyl((u, v0 + width / 2 - 2.5, z), (u, v0 + width / 2, z), r_pitch + flange, COL["printed"], group, name)
    cyl((u, v0 - width / 2, z), (u, v0 + width / 2, z), r_pitch - 0.6, COL["printed"], group, name)


def drum_z(C_uv, z0, r_pitch, width, group, name, flange=5.0):
    """Single-groove drum on a vertical axis."""
    u, v = C_uv
    cyl((u, v, z0 - width / 2), (u, v, z0 - width / 2 + 3), r_pitch + flange, COL["printed"], group, name, seg=64)
    cyl((u, v, z0 + width / 2 - 3), (u, v, z0 + width / 2), r_pitch + flange, COL["printed"], group, name, seg=64)
    cyl((u, v, z0 - width / 2), (u, v, z0 + width / 2), r_pitch - 0.6, COL["printed"], group, name, seg=64)


# --- arm mechanism -------------------------------------------------------
drum_v(P_BOOM, 0.0, R_BOOM, 14, "arm_mech", "boom drum")
cyl((-7, -24.5, 110), (-7, 24.5, 110), 1.6, COL["steel"], "arm_mech", "M3 drive bolt")
drum_v(P_STICK, 0.0, R_STICK, 10, "arm_mech", "stick drum")
cyl((P_STICK[0] - 6, -17, P_STICK[1] + 6), (P_STICK[0] - 6, 17, P_STICK[1] + 6), 1.6, COL["steel"], "arm_mech", "M3 drive bolt")
drum_v(P_BUCKET, 0.0, R_BUCKET, 8, "arm_mech", "bucket drum-axle")
cyl((P_BUCKET[0], -17.5, P_BUCKET[1]), (P_BUCKET[0], 17.5, P_BUCKET[1]), 6.0, COL["printed"], "arm_mech",
    "bucket drum-axle hex ends")
for pu, pz in ((343.3, 102.9), (346.3, 97.9)):
    cyl((pu, -17, pz), (pu, 17, pz), 1.6, COL["steel"], "arm_mech", "M3 bolt")
# PTFE stop bosses
for s_off in (-9.0, 9.0):
    p = boom_pt(150.0 / math.cos(math.radians(BOOM_ANG)), s_off, 0)
    box((p[0] - 6, -8, p[2] - 5), (p[0] + 6, 8, p[2] + 5), COL["printed"], "arm_mech", "PTFE stop boss (boom)")
for s_off in (-7.0, 7.0):
    p = stick_pt(131.1, s_off, 0)
    box((p[0] - 5, -7, p[2] - 4), (p[0] + 5, 7, p[2] + 4), COL["printed"], "arm_mech", "PTFE stop boss (stick)")

# rotating tube (3/4" PVC) + slew drum in pedestal
cyl((0, 0, TUBE_Z[0]), (0, 0, TUBE_Z[1]), TUBE_R, COL["pvc"], "tube", "3/4in PVC rotating tube", opacity=1.0)
cyl((0, -24, 50), (0, 24, 50), 1.6, COL["steel"], "arm_mech", "M3 cross-bolt tower-to-tube")

# --- printed slewing ring (final coordinates; not lowered) ----------------
ring(TUBE_R + 0.5, FLANGE_R, FLANGE_Z[0], 19.5, COL["black"], "exterior", "circular turret flange")
ring(TUBE_R + 0.5, FLANGE_R - 2.2, 19.5, 22.5, COL["black"], "exterior", "turret flange race groove")
ring(TUBE_R + 0.5, FLANGE_R, 22.5, FLANGE_Z[1], COL["black"], "exterior", "circular turret flange")
ring(RACE_R[0], RACE_R[1], BASE_RIM_Z[0], BASE_RIM_Z[1], COL["black"], "exterior", "base lower race rim")
ring(RACE_R[0], RACE_R[1], RET_RING_Z[0], RET_RING_Z[1], COL["printed"], "exterior", "slewing-ring retaining ring")
for k in range(8):
    a = math.radians(45 * k)
    c = (66.25 * math.cos(a), 66.25 * math.sin(a))
    prox.append(dict(type="cyl", a=t3((c[0], c[1], RET_RING_Z[1])), b=t3((c[0], c[1], RET_RING_Z[1] + 2.5)), r=2.75,
                     color=COL["steel"], group="exterior", name="M3x20 retaining bolt", opacity=1.0, seg=24,
                     nolower=True))
for k in range(N_BALLS):
    a = 2 * math.pi * (k + 0.5) / N_BALLS
    prox.append(dict(type="sph", c=t3((BALL_CIRCLE_R * math.cos(a), BALL_CIRCLE_R * math.sin(a), BALL_Z)), r=BALL_R,
                     color="#f4f4f4", group="bearing_balls", name="6 mm BB", nolower=True))
drum_z((0.0, 0.0), Z_SLEW_LAYER, R_SLEW, 14, "arm_mech", "slew drum (in pedestal)")

# --- pedestal -------------------------------------------------------------
t = T_WOOD
box((PED_U[0], PED_V[0], PED_Z[1] - t), (PED_U[1], PED_V[1], PED_Z[1]), COL["ply"], "pedestal", "pedestal top")
box((PED_U[0], PED_V[0], PED_Z[0]), (PED_U[0] + t, PED_V[1], PED_Z[1] - t), COL["ply"], "pedestal", "pedestal wall")
box((PED_U[1] - t, PED_V[0], PED_Z[0]), (PED_U[1], PED_V[1], PED_Z[1] - t), COL["ply"], "pedestal", "pedestal wall")
box((PED_U[0] + t, PED_V[0], PED_Z[0]), (PED_U[1] - t, PED_V[0] + t, PED_Z[1] - t), COL["ply"], "pedestal", "pedestal wall")
box((PED_U[0] + t, PED_V[1] - t, PED_Z[0]), (PED_U[1] - t, PED_V[1], PED_Z[1] - t), COL["ply"], "pedestal_near", "pedestal wall")
box((PED_U[0] - 4, -24, COND_Z - 24), (PED_U[0] + t + 6, 24, COND_Z + 30), COL["printed"], "arm_mech", "pedestal fairlead plate")

# conduit + copper elbow
cyl((MOUTH_U - 5, 0, COND_Z), (PED_U[0], 0, COND_Z), COND_R, COL["pvc"], "conduit", "2in PVC conduit")
elbow = [(PED_U[0] + t, 0, Z_ARM_LAYER), (-ELBOW_R, 0, Z_ARM_LAYER)]
for k in range(1, 13):
    th = math.radians(90 - 90 * k / 12)
    elbow.append((-ELBOW_R + ELBOW_R * math.cos(th), 0, Z_ARM_LAYER + ELBOW_R - ELBOW_R * math.sin(th)))
path(elbow, 8.0, COL["copper"], "conduit", "1/2in copper sweep elbow")

# --- sandbox --------------------------------------------------------------
tw = 18.0
box((SB_U[0], SB_V[0], SB_Z[0] - tw), (SB_U[1], SB_V[1], SB_Z[0]), COL["ply"], "sandbox", "sandbox floor")
box((SB_U[0], SB_V[0], SB_Z[0]), (SB_U[0] + tw, SB_V[1], SB_Z[1]), COL["ply"], "sandbox", "sandbox wall (box side)")
box((SB_U[1] - tw, SB_V[0], SB_Z[0]), (SB_U[1], SB_V[1], SB_Z[1]), COL["ply"], "sandbox", "sandbox wall")
box((SB_U[0] + tw, SB_V[0], SB_Z[0]), (SB_U[1] - tw, SB_V[0] + tw, SB_Z[1]), COL["ply"], "sandbox", "sandbox wall")
box((SB_U[0] + tw, SB_V[1] - tw, SB_Z[0]), (SB_U[1] - tw, SB_V[1], SB_Z[1]), COL["ply"], "sandbox_near", "sandbox wall")
box((SB_U[0] + tw, SB_V[0] + tw, SB_Z[0]), (SB_U[1] - tw, SB_V[1] - tw, SAND_Z), COL["sand"], "sand", "sand",
    opacity=0.55)

# --- control box ----------------------------------------------------------
u0, u1 = BOX_U
v0, v1 = BOX_V
z0, z1 = BOX_Z
box((u0, v0, z0), (u1, v1, z0 + t), COL["wood"], "box", "box floor")
box((u1 - t, v0, z0 + t), (u1, v1, z1 - t), COL["wood"], "box", "box front")
box((u0, v0, z0 + t), (u0 + t, v1, z1 - t), COL["wood"], "box_rear", "box rear")
box((u0 + t, v0, z0 + t), (u1 - t, v0 + t, z1 - t), COL["wood"], "box", "box right side")
box((u0 + t, v1 - t, z0 + t), (u1 - t, v1, z1 - t), COL["wood"], "box_left", "box left side")
box((u0, v0, z1 - t), (u1, v1, z1), COL["wood"], "box_top", "box top")
for name, (vh, vd) in LEVERS.items():
    box((AXLE_U - 82, vh - 7, z1 - 0.5), (AXLE_U + 82, vh + 7, z1 + 0.6), "#3a2a18", "box_top_slots", "lever slot")
# bulkheads
for vb in (85.0, 12.5, -12.5, -85.0):
    box((AXLE_U - 40, vb - 4.5, z0 + t), (AXLE_U + 40, vb + 4.5, AXLE_Z + 38), COL["ply"], "box_bulk", "plywood bearing block")
cyl((AXLE_U, -92, AXLE_Z), (AXLE_U, 92, AXLE_Z), 2.1, COL["steel"], "box_mech", "8-32 common lever axle")
for name, (vh, vd) in LEVERS.items():
    drum_v((AXLE_U, AXLE_Z), vd, R_LEVER, 14, "box_mech", f"{name} lever drum", flange=4.0)
    lo, hi = sorted((vd, vh))
    if hi - lo > 1:
        cyl((AXLE_U, lo, AXLE_Z), (AXLE_U, hi, AXLE_Z), 10.0, COL["printed"], "box_mech", f"{name} lever hub")
    box((AXLE_U - 11, vh - 11, AXLE_Z - 11), (AXLE_U + 11, vh + 11, AXLE_Z + 22), COL["printed"], "box_mech",
        f"{name} handle socket")
    cyl((AXLE_U, vh, AXLE_Z + 10), (AXLE_U, vh, AXLE_Z + HANDLE_LEN), 8.0, "#8a5a2b", "box_ctrl", f"{name} handle")
    sph((AXLE_U, vh, AXLE_Z + HANDLE_LEN + 14), 18.0, "#161616", "box_ctrl", f"{name} knob")
# slew spool + wheel
drum_z(WHEEL_C, Z_SLEW_LAYER, R_SLEW, 14, "box_mech", "slew spool drum")
cyl((WHEEL_C[0], WHEEL_C[1], Z_SLEW_LAYER + 7), (WHEEL_C[0], WHEEL_C[1], z1 + 18), 12.0, COL["printed"], "box_mech",
    "slew spool tube")
cyl((WHEEL_C[0], WHEEL_C[1], z0 + t), (WHEEL_C[0], WHEEL_C[1], WHEEL_Z + 10), 2.1, COL["steel"], "box_mech",
    "8-32 slew axle")
prox.append(dict(type="torus", c=t3((WHEEL_C[0], WHEEL_C[1], WHEEL_Z)), R=85.0, r=7.0, color="#161616",
                 group="box_ctrl", name="slew wheel"))
cyl((WHEEL_C[0], WHEEL_C[1], z1 + 18), (WHEEL_C[0], WHEEL_C[1], WHEEL_Z + 6), 20.0, "#161616", "box_ctrl", "wheel hub")
for k in range(3):
    a = math.radians(90 + 120 * k)
    cyl((WHEEL_C[0], WHEEL_C[1], WHEEL_Z), (WHEEL_C[0] + 82 * math.cos(a), WHEEL_C[1] + 82 * math.sin(a), WHEEL_Z),
        4.5, "#161616", "box_ctrl", "wheel spoke")
box((u1 - t - 22, -26, COND_Z - 34), (u1 - t, 26, COND_Z + 40), COL["printed"], "box_mech", "box fairlead block")

# ---------------------------------------------------------------- cable paths
strands = []


def strand(circuit, pts, ptfe_from=None, ptfe_to=None, name=""):
    strands.append(dict(circuit=circuit, color=COL[circuit], pts=[t3(p) for p in pts], name=name))
    if ptfe_from is not None:
        seg = pts[ptfe_from:ptfe_to + 1]
        path(seg, PTFE_R, COL["ptfe"], "ptfe", "PTFE 4x2 tube", opacity=0.45)


def lever_box_segment(circuit, sign, v_mouth, z_off):
    """Control drum anchor -> tangent -> box fairlead mouth point (design coords)."""
    vh, vd = LEVERS[circuit]
    M = (MOUTH_U, v_mouth, Z_ARM_LAYER + z_off)
    pts2, wrap = tangent_wrap((AXLE_U, AXLE_Z), R_LEVER, (M[0], M[2]), 180.0, sign)
    pts = [(p[0], vd, p[1]) for p in pts2[:-1]] + [M]
    return pts


def arm_common(v_i, o_i, z_off):
    """Box mouth -> conduit -> pedestal fairlead -> copper elbow -> up the rotating tube."""
    pts = [(MOUTH_U, v_i, Z_ARM_LAYER + z_off), (PED_U[0] + T_WOOD, v_i, Z_ARM_LAYER + z_off),
           (-ELBOW_R, v_i, Z_ARM_LAYER - o_i)]
    R = ELBOW_R + o_i
    for k in range(1, 13):
        th = math.radians(90 - 90 * k / 12)
        pts.append((-ELBOW_R + R * math.cos(th), v_i, Z_ARM_LAYER + ELBOW_R - R * math.sin(th)))
    pts.append((o_i, v_i, TUBE_Z[1]))
    return pts


# boom (green): bare cable, both strands up the tube to the boom drum
for sign, o in ((+1, -3.0), (-1, 3.0)):
    box_pts = lever_box_segment("boom", sign, 0.0, -o)
    common = arm_common(0.0, o, -o)
    top = common[-1]
    arm2, wrap = tangent_wrap(P_BOOM, R_BOOM, (top[0], top[2]), 90.0, -sign)
    arm = [(p[0], 0.0, p[1]) for p in reversed(arm2[:-1])]
    strand("boom", box_pts + common[1:] + arm, name=f"boom strand {sign}")

# stick (blue): PTFE from pedestal fairlead to boom stop boss, bare to stick drum
stop_s = 150.0 / math.cos(math.radians(BOOM_ANG))
for sign, o, vpath in ((+1, -2.0, (6, 11, 11, 11, 10, 5)), (-1, 2.0, (6, 15, 15, 15, 14, 6))):
    off_end = 9.0 * sign
    box_pts = lever_box_segment("stick", sign, 6.0, -o)
    common = arm_common(6.0, o, -o)
    k_ptfe0 = len(box_pts)                       # pedestal fairlead index (after mouth)
    up = [(-6.0, vpath[1], 90.0), (-10.0, vpath[2], 104.0), (-2.0, vpath[3], 116.0),
          boom_pt(40, off_end * 0.9, vpath[4]), boom_pt(100, off_end, vpath[5]), boom_pt(stop_s, off_end, 0.0)]
    stop = up[-1]
    arm2, wrap = tangent_wrap(P_STICK, R_STICK, (stop[0], stop[2]), BOOM_ANG, -sign)
    arm = [(p[0], 0.0, p[1]) for p in reversed(arm2[:-1])]
    pts = box_pts + common[1:] + up + arm
    strand("stick", pts, ptfe_from=k_ptfe0, ptfe_to=len(box_pts) + len(common) - 1 + len(up) - 1, name="stick")

# bucket (red): PTFE from pedestal fairlead through the boom, across the stick joint, to stick stop boss
for sign, o, vs in ((+1, -2.0, (-11, -11, -11, -10, -9, -8, -4)), (-1, 2.0, (-15, -15, -14, -13, -13, -12, -6))):
    off_end = 7.0 * sign
    box_pts = lever_box_segment("bucket", sign, -6.0, -o)
    common = arm_common(-6.0, o, -o)
    k_ptfe0 = len(box_pts)
    up = [(-6.0, vs[0], 90.0), (-10.0, vs[1], 104.0), (-2.0, vs[2], 116.0),
          boom_pt(40, 4.0 if sign > 0 else -2.0, vs[3]), boom_pt(165, 5.0 if sign > 0 else 0.0, vs[4]),
          (P_STICK[0] - 3, vs[5], P_STICK[1] + (13.0 if sign > 0 else 9.0)),
          stick_pt(25, 5.0 if sign > 0 else -1.0, vs[6] - 4), stick_pt(80, off_end * 0.8, vs[6]),
          stick_pt(131.1, off_end, 0.0)]
    stop = up[-1]
    arm2, wrap = tangent_wrap(P_BUCKET, R_BUCKET, (stop[0], stop[2]), STICK_ANG, -sign)
    arm = [(p[0], 0.0, p[1]) for p in reversed(arm2[:-1])]
    pts = box_pts + common[1:] + up + arm
    strand("bucket", pts, ptfe_from=k_ptfe0, ptfe_to=len(box_pts) + len(common) - 1 + len(up) - 1, name="bucket")

# slew (purple): wheel spool -> mouth -> conduit (upper layer) -> pedestal fairlead -> slew drum
for sign, vm in ((+1, 5.0), (-1, -5.0)):
    M = (MOUTH_U, vm, Z_SLEW_LAYER)
    anchor_box = math.degrees(math.atan2(M[1] - WHEEL_C[1], M[0] - WHEEL_C[0])) + 180
    b2, wb = tangent_wrap(WHEEL_C, R_SLEW, (M[0], M[1]), anchor_box, -sign)
    F = (PED_U[0] + T_WOOD, vm, Z_SLEW_LAYER)
    a2, wa = tangent_wrap((0.0, 0.0), R_SLEW, (F[0], F[1]), 0.0, sign)
    pts = [(p[0], p[1], Z_SLEW_LAYER) for p in b2[:-1]] + [M, F] + \
          [(p[0], p[1], Z_SLEW_LAYER) for p in reversed(a2[:-1])]
    strand("slew", pts, name="slew strand")

# ---------------------------------------------------------------- labels / views
def L3(p):
    return t3(p)


VIEWS = {
    "01-full-assembly": dict(
        title="View 1 — Complete excavator: control box, conduit, pedestal, arm (sandbox 24″ × 24″)",
        cam=dict(pos=t3((-1050, 820, 620)), target=t3((-40, -20, 20)), fov=32),
        hide=["box_rear_x"], cut=[], ghost={"sand": 0.72},
        labels=[("Boom lever", (AXLE_U, 70, 140), -60, 110), ("Stick lever", (AXLE_U, 0, 140), -20, -80),
                ("Bucket lever", (AXLE_U, -70, 140), 40, -80), ("Slew wheel (horizontal)", (WHEEL_C[0], WHEEL_C[1] - 60, 80), 60, -40),
                ("Wooden control box on sandbox wall", (-330, 115, -60), -170, 60),
                ("2″ PVC conduit under sand (all 8 cables)", (-150, 0, COND_Z), -60, 120),
                ("Pedestal (slew drum inside)", (0, 90, -60), 60, 80),
                ("EX-MA exterior (turret now on printed slewing ring)", (100, 0, 177), 40, -70)]),
    "02-control-box": dict(
        title="View 2 — Control box: 3 push-pull levers + horizontal slew wheel on top",
        cam=dict(pos=t3((-1080, 430, 560)), target=t3((-330, -90, 0)), fov=34),
        only=["box", "box_rear", "box_left", "box_top", "box_top_slots", "box_ctrl", "sandbox", "sandbox_near",
              "sand", "conduit"], ghost={"sand": 0.8},
        labels=[("BOOM", (AXLE_U, 70, 150), -60, -60), ("STICK", (AXLE_U, 0, 150), -30, -70),
                ("BUCKET", (AXLE_U, -70, 150), 10, -80), ("SLEW WHEEL", (WHEEL_C[0], WHEEL_C[1] - 85, 80), 40, -90),
                ("Slot length = lever hard stop", (AXLE_U - 80, 70, 40), -200, 40),
                ("Top panel screwed on (service access)", (-250, -120, 40), 80, 90)]),
    "03-control-box-cutaway": dict(
        title="View 3 — Control box cutaway: common lever axle, 3 lever drums, slew spool, fairlead, conduit exit",
        cam=dict(pos=t3((-900, 560, 330)), target=t3((-320, -70, -80)), fov=30),
        only=["box", "box_mech", "box_bulk", "box_ctrl", "cables", "conduit", "box_top"],
        ghost={"box_top": 0.15, "conduit": 0.25, "box_bulk": 0.3},
        clipx=-150.0,
        labels=[("8-32 common axle", (AXLE_U, 92, AXLE_Z), -170, 40),
                ("Boom drum Ø48 (hub offset to handle)", (AXLE_U, 25, AXLE_Z - 28), -210, 90),
                ("Stick drum", (AXLE_U, 0, AXLE_Z - 28), -60, 130),
                ("Bucket drum", (AXLE_U, -25, AXLE_Z - 28), 30, 120),
                ("Plywood bearing blocks (axle supports)", (AXLE_U - 40, 85, AXLE_Z + 30), -200, -40),
                ("Slew spool (Ø110 drum + tube, 1 part)", (WHEEL_C[0], WHEEL_C[1] - 60, Z_SLEW_LAYER), 70, 60),
                ("Fairlead block → conduit", (MOUTH_U, 0, COND_Z + 40), 80, -50),
                ("Double-crimp loops + tension screw on drum", (AXLE_U - 24, 25, AXLE_Z), -230, -10)]),
    "04-arm": dict(
        title="View 4 — Arm and base on pedestal: circular turret flange, printed slewing ring, turret lowered 13 mm",
        cam=dict(pos=t3((200, -820, 330)), target=t3((150, 0, 60)), fov=34),
        only=["exterior", "pedestal", "pedestal_near", "tube"],
        labels=[("Boom", (95, 0, 175), -40, -80), ("Stick", (270, 0, 180), 30, -80), ("Bucket", (330, 0, 60), 60, 40),
                ("Circular turret flange, turret lowered 13 mm", (-35, -40, 25), -90, -170, "fixed"),
                ("Bolted retaining ring (upper race)", (40, -58, 27), 260, 40, "fixed"), ("Wooden pedestal", (0, 90, -100), -220, 40)]),
    "05-arm-cutaway": dict(
        title="View 5 — Arm cutaway: joint drums, PTFE-sleeved cables, rotating tube, slew drum in pedestal",
        cam=dict(pos=t3((140, -900, 40)), target=t3((135, 0, 35)), fov=36),
        only=["exterior", "arm_mech", "pedestal", "pedestal_near", "tube", "cables", "ptfe", "conduit",
              "bearing_balls"],
        cut=["exterior", "pedestal", "tube", "bearing_balls"], ghost={"conduit": 0.25, "tube": 0.35},
        labels=[("Boom drum Ø32, keyed by M3 bolt", (0, 0, 118), -250, -90),
                ("Stick drum Ø26", (P_STICK[0], 0, P_STICK[1] + 15), -40, -90),
                ("Bucket drum-axle Ø18", (P_BUCKET[0], 0, P_BUCKET[1] - 10), 50, 40),
                ("PTFE stop boss (stick cables)", (150, 0, 186), -260, -60),
                ("PTFE stop boss (bucket cables)", (305, 0, 150), 30, -80),
                ("PTFE sleeves cross the joints", (60, -10, 140), -120, -120),
                ("3/4″ PVC tube turns with turret (M3 cross-bolt)", (0, 0, 50), -270, -20),
                ("Printed slewing ring: 6 mm BBs between flange and base", (61, 0, 21), 300, 30, "fixed"),
                ("Slew drum Ø110 (in pedestal)", (40, 0, Z_SLEW_LAYER), 60, 20),
                ("Copper elbow: arm cables up the axis", (-20, 0, -125), 150, 90),
                ("Conduit from control box", (-150, 0, COND_Z + 30), -40, -120)]),
    "06-slew-bearing-detail": dict(
        title="View 6 — Printed slewing ring: circular turret flange (inner race), 6 mm BBs, bolted retaining ring",
        cam=dict(pos=t3((70, -300, 110)), target=t3((10, 0, 22)), fov=30),
        only=["exterior", "arm_mech", "tube", "bearing_balls", "pedestal", "pedestal_near", "cables", "ptfe"],
        cut=["exterior", "pedestal", "tube", "bearing_balls"], ghost={"tube": 0.35},
        labels=[("Turret flange Ø119 = inner race (printed with tower)", (-40, 0, 23), -60, -260),
                ("6 mm BBs (≈56, no cage)", (-61, 0, 21), -120, 110),
                ("Retaining ring = upper outer race (new printed part)", (66, 0, 25), 60, -150),
                ("Base rim = lower outer race", (66, 0, 17), 90, 90),
                ("8 × M3×20 into nuts captured in base", (66.25, 0, 28.5), 150, -70),
                ("3/4″ PVC tube: cables + slew torque only", (-13, 0, 60), -330, -120),
                ("Base (fixed, screwed to pedestal)", (-45, 0, 8), -250, 60)]),
}

LEGEND = [("Boom circuit", COL["boom"]), ("Stick circuit", COL["stick"]), ("Bucket circuit", COL["bucket"]),
          ("Slew circuit", COL["slew"]), ("New printed parts", COL["printed"]), ("PTFE 4×2 sleeve", "#d9d9d9")]


LOWER_GROUPS = {"arm_mech", "tube", "ptfe"}
LOWER_LABEL_VIEWS = {"04-arm", "05-arm-cutaway"}


def _low(p3):
    """three.js point [x, y(=z design), z]: drop turret-side points by TURRET_DZ."""
    return [p3[0], round(p3[1] + TURRET_DZ, 3), p3[2]] if p3[1] > LOWER_ABOVE_Z else p3


def lower_proxies_and_strands():
    for P in prox:
        if P.get("nolower") or P["group"] not in LOWER_GROUPS:
            continue
        for key in ("a", "b", "c", "min", "max"):
            if key in P:
                P[key] = _low(P[key])
        if "pts" in P:
            P["pts"] = [_low(q) for q in P["pts"]]
    for S_ in strands:
        S_["pts"] = [_low(q) for q in S_["pts"]]


def main():
    stl, out = sys.argv[1], sys.argv[2]
    shells = load_exma(stl)
    meshes = mesh_records(shells)
    lower_proxies_and_strands()
    views = {}
    for k, v in VIEWS.items():
        v = dict(v)
        low = k in LOWER_LABEL_VIEWS
        labs = []
        for lab in v["labels"]:
            a, b, c, d = lab[:4]
            fixed = len(lab) > 4 and lab[4] == "fixed"     # slewing-ring parts sit on the fixed base
            labs.append(dict(text=a, at=(_low(L3(b)) if low and not fixed else L3(b)), dx=c, dy=d))
        v["labels"] = labs
        views[k] = v
    scene = dict(proxies=prox, strands=strands, cable_r=CABLE_R, views=views, legend=LEGEND,
                 removed=REMOVED)
    with open(out, "w") as f:
        f.write("window.MESHES=" + json.dumps(meshes) + ";\n")
        f.write("window.SCENE=" + json.dumps(scene) + ";\n")
    print(f"meshes={len(meshes)} proxies={len(prox)} strands={len(strands)} -> {out}")


if __name__ == "__main__":
    main()
