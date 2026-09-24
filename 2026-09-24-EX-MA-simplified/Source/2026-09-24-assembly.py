"""EX-MA assembly: places every part in the built position (design frame, mm).

part(name) -> trimesh in the assembly frame. Printed parts come from STL/ (new parts are
stored in their print frame and placed here; modified EX-MA parts are already stored in
the assembly frame). Hardware (rod, bolts, BBs, PVC, copper, PTFE, rope) is generated
as simple solids for checks and renders only.

MEMBERS groups the rigid bodies that move together for the joint sweeps.
"""
import importlib.util
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


ex = _load("exma", "2026-09-24-exma_common.py")
rt = _load("routing", "2026-09-24-routing.py")
STL = ex.OUT / "STL"
DZ = ex.TURRET_DZ


def _frame(X, Y, Z, origin):
    X, Y, Z = (np.asarray(a, float) / np.linalg.norm(a) for a in (X, Y, Z))
    if np.linalg.det(np.column_stack((X, Y, Z))) < 0:
        X = -X
    A = np.eye(4)
    A[:3, :3] = np.column_stack((X, Y, Z))
    A[:3, 3] = origin
    return A


def drum_on_v(center_uz, anchor_deg):
    """Print frame (axis +Z, crimp pocket +Y) -> design: axis +v, pocket toward anchor_deg in u-z."""
    a = math.radians(anchor_deg)
    Y = (math.cos(a), 0.0, math.sin(a))
    Z = (0.0, 1.0, 0.0)
    X = np.cross(Y, Z)
    return _frame(X, Y, Z, (center_uz[0], 0.0, center_uz[1]))


# placements of new printed parts: name -> 4x4 (print frame -> built design frame)
def placements():
    P = {}
    P["boom-drum"] = drum_on_v(ex.P_BOOM, 90.0)
    P["stick-drum"] = drum_on_v(ex.P_STICK, math.degrees(rt.BOOM_ANG))
    P["bucket-drum-axle"] = drum_on_v(ex.P_BUCKET, math.degrees(rt.STICK_ANG))
    P["slew-drum"] = _frame((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, ex.Z_SLEW_LAYER))
    P["slewing-ring-retaining-ring"] = _frame((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, ex.RET_RING_Z[0]))
    # conduit fittings: local -Z faces the conduit, local +Y = up, local +X = lateral
    P["conduit-end-fitting@box"] = _frame((0, -1, 0), (0, 0, 1), (-1, 0, 0), (ex.BOX_U[1] - ex.T_WOOD, ex.MOUTH_V, ex.COND_Z))
    P["conduit-end-fitting@pedestal"] = _frame((0, 1, 0), (0, 0, 1), (1, 0, 0), (ex.PED_U[0] + ex.T_WOOD, 0.0, ex.COND_Z))
    for name, (vh, vd) in ex.LEVERS.items():
        P[f"lever-hub-{name}"] = _frame((-1, 0, 0), (0, 0, 1), (0, 1, 0), (ex.AXLE_U, vd, ex.AXLE_Z))
    P["slew-spool"] = _frame((1, 0, 0), (0, 1, 0), (0, 0, 1),
                             (ex.WHEEL_C[0], ex.WHEEL_C[1], ex.Z_SLEW_LAYER - ex.DRUM["slew"]["width"] / 2))
    spool_top = ex.Z_SLEW_LAYER - ex.DRUM["slew"]["width"] / 2 + 145.0
    P["slew-wheel"] = _frame((1, 0, 0), (0, 1, 0), (0, 0, 1), (ex.WHEEL_C[0], ex.WHEEL_C[1], spool_top))
    return P


MODIFIED = ["tower", "base", "boom-half-left", "boom-half-right", "stick-half-left", "stick-half-right",
            "bucket-ear-left", "bucket-ear-right", "bucket"]

MEMBERS = {
    "fixed": ["base", "slewing-ring-retaining-ring"],
    "turret": ["tower"],
    "boom": ["boom-half-left", "boom-half-right", "boom-drum"],
    "stick": ["stick-half-left", "stick-half-right", "stick-drum"],
    "bucket": ["bucket", "bucket-ear-left", "bucket-ear-right", "bucket-drum-axle"],
}


def part(name):
    if name in MODIFIED:
        return trimesh.load(STL / f"2026-09-24-{name}.stl", force="mesh")
    base = name.split("@")[0]
    m = trimesh.load(STL / f"2026-09-24-{base}.stl", force="mesh")
    m.apply_transform(placements()[name])
    return m


def member_mesh(member):
    return trimesh.util.concatenate([part(n) for n in MEMBERS[member]])


def pose_transform(member, boom=0.0, stick=0.0, bucket=0.0, slew=0.0):
    """4x4 moving a member from the built pose to a posed configuration (radians)."""
    def rot_v(center_uz, a):
        c, s = math.cos(a), math.sin(a)
        R = np.eye(4)
        # rotation about +v through (u, z): u' = u c - z s ; z' = u s + z c  (CCW seen from +v)
        R[0, 0], R[0, 2], R[2, 0], R[2, 2] = c, -s, s, c
        T1, T2 = np.eye(4), np.eye(4)
        T1[0, 3], T1[2, 3] = -center_uz[0], -center_uz[1]
        T2[0, 3], T2[2, 3] = center_uz[0], center_uz[1]
        return T2 @ R @ T1
    Tb = rot_v(ex.P_BOOM, boom)
    Ts = Tb @ rot_v(ex.P_STICK, stick)
    Tk = Ts @ rot_v(ex.P_BUCKET, bucket)
    Tz = trimesh.transformations.rotation_matrix(slew, (0, 0, 1))
    chain = {"fixed": np.eye(4), "turret": np.eye(4), "boom": Tb, "stick": Ts, "bucket": Tk}[member]
    return (Tz @ chain) if member != "fixed" else chain
