"""EX-MA shared design constants and geometry loaders.

Design frame (mm): u = along the arm from the slew axis, v = lateral (+v is the
operator's left when facing the excavator from the control box), z = up from
the base bottom. All EX-MA source geometry is brought into this frame at design
scale (STL / 3MF preview scale 0.7103 -> x1.408).

Import from other scripts with:
    spec = importlib.util.spec_from_file_location("exma", ".../2026-09-24-exma_common.py")
"""
import math
import re
import zipfile
from pathlib import Path

import numpy as np
import trimesh

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "References"
OUT = ROOT / "2026-09-24-EX-MA-simplified"
STL_PATH = REF / "EX-MA Colored ARM.stl"
TMF_PATH = REF / "EX-MA Colored.3mf"
BUCKET_STEP = REF / "Source_Bucket_Repaired.step"

# ---------------------------------------------------------------- frame
STL_SCALE = 0.710351508
S = 1.0 / STL_SCALE
ARM_ROT = math.atan2(0.518966256, 0.485049781)     # 3MF build rotation about Z
BASE_CX, BASE_CY = 55.72, 50.59                     # slew axis in STL / 3MF plate XY

# ---------------------------------------------------------------- design constants
TURRET_DZ = -13.0                  # turret + arm lowered (green ring removed)
# working ranges (deg from the EX-MA pose, + raises); limited by the lever slots, not the joints.
# Each keeps >= 20 deg of rope wrap on its drum at both ends (crimp anchored at mid-range).
WORKING = dict(boom=(-40.0, 45.0), stick=(-50.0, 70.0), bucket=(-55.0, 85.0), slew=(-90.0, 90.0))
# pivots in the ORIGINAL EX-MA position (u, z); add TURRET_DZ for the built position
P_BOOM0 = (0.0, 102.0)
P_STICK0 = (186.19, 196.86)
P_BUCKET0 = (344.80, 122.90)
P_BOOM = (P_BOOM0[0], P_BOOM0[1] + TURRET_DZ)
P_STICK = (P_STICK0[0], P_STICK0[1] + TURRET_DZ)
P_BUCKET = (P_BUCKET0[0], P_BUCKET0[1] + TURRET_DZ)

ROPE_D = 1.6                       # 1/16" galvanized 7x19
PIN_D = 4.17                       # 8-32 threaded rod major diameter
PIN_BORE = 4.6                     # printed clearance bore for 8-32 rod
M3_CLEAR = 3.4
M3_NUT_AF = 5.5                    # across flats
PTFE_OD, PTFE_ID = 4.0, 2.0
PVC34_OD = 26.7                    # 3/4" sch40 PVC

# joint drums: pitch diameter (to rope centre), drum width
DRUM = dict(boom=dict(pitch=30.0, width=14.0),      # boom root free radius 19.0
            stick=dict(pitch=26.0, width=10.0),     # stick root free radius 17.6
            bucket=dict(pitch=17.0, width=10.0),    # stick nose free radius 11.5 (drum turns vs nose)
            slew=dict(pitch=110.0, width=14.0),
            lever=dict(pitch=60.0, width=14.0))     # lever swing 40-52 deg over the working ranges

# printed slewing ring
FLANGE_R = 59.5                    # circular turret flange radius (inner race)
FLANGE_Z = (17.0, 25.0)
RACE_R = (62.5, 70.0)              # base rim / retaining ring radial span
BASE_TOP_Z = 15.0
BASE_RIM_Z = (15.0, 21.0)
RET_RING_Z = (21.0, 27.0)
BALL_D = 6.0                       # airsoft BB
BALL_CIRCLE_R = 59.0
BALL_Z = 21.0
RACE_CLEAR = 0.15                  # per side, ball to race (tune with shims under the retaining ring)

# pedestal / conduit / rotating tube
TUBE_Z = (-98.0, 75.0 + TURRET_DZ)
COND_Z, COND_R = -110.0, 30.0
Z_SLEW_LAYER, Z_ARM_LAYER = -88.0, -130.0
PED_U, PED_V, PED_Z = (-90.0, 90.0), (-90.0, 90.0), (-190.0, 0.0)
ELBOW_R = 30.0

# control box
BOX_U = (-453.0, -203.0)
BOX_V = (-290.0, 115.0)
BOX_Z = (-160.0, 40.0)
T_WOOD = 12.0
AXLE_U, AXLE_Z = -360.0, -100.0
LEVERS = dict(boom=(70.0, 21.0), stick=(0.0, -17.0), bucket=(-70.0, -37.0))   # (handle v, drum v)
HANDLE_LEN = 225.0
WHEEL_C = (-340.0, -190.0)
WHEEL_Z = 75.0
MOUTH_U = -210.0
MOUTH_V = -8.0
BUCKET_STEP_OFFSET = (5.3, -0.05, -19.4)   # STEP frame -> original design frame (fit: mean 0.15 mm)


# ---------------------------------------------------------------- transforms
def plate_to_design(pts):
    """STL / 3MF plate coordinates -> design frame (numpy Nx3)."""
    pts = np.asarray(pts, dtype=float)
    ca, sa = math.cos(-ARM_ROT), math.sin(-ARM_ROT)
    x, y = pts[:, 0] - BASE_CX, pts[:, 1] - BASE_CY
    return np.column_stack(((x * ca - y * sa) * S, (x * sa + y * ca) * S, pts[:, 2] * S))


def to_design_mesh(mesh):
    m = mesh.copy()
    m.vertices = plate_to_design(m.vertices)
    return m


# ---------------------------------------------------------------- STL shells
def load_stl_shells():
    """Split the arm STL into connected shells in the design frame.

    Labels follow the inspection report: shells ordered by min-u -> '0'..'S'.
    Returns dict label -> trimesh.Trimesh."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    m = trimesh.load(STL_PATH, force="mesh", process=True)
    m.merge_vertices(digits_vertex=4)
    # vertex connectivity (face adjacency breaks on the non-manifold boom/stick shells)
    e = m.edges_unique
    n = len(m.vertices)
    g = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
    _, vlab = connected_components(g, directed=False)
    flab = vlab[m.faces[:, 0]]
    parts = [to_design_mesh(m.submesh([np.where(flab == k)[0]], append=True)) for k in np.unique(flab)]
    parts.sort(key=lambda p: p.bounds[0][0])
    labels = "0123456789ABCDEFGHIJKLMNOPQRS"
    return {labels[i]: p for i, p in enumerate(parts)}


# ---------------------------------------------------------------- 3MF objects
def _mat(s):
    a = list(map(float, s.split()))
    M = np.eye(4)
    M[:3, :3] = np.array(a[:9]).reshape(3, 3).T      # 3MF: p' = p * M (row vectors)
    M[:3, 3] = a[9:12]
    return M


def load_3mf_object(item_oid, comp_oid):
    """Return one watertight 3MF component as a design-frame trimesh.

    item_oid: build item object id (e.g. '71'); comp_oid: component object id
    (e.g. '69')."""
    z = zipfile.ZipFile(TMF_PATH)
    main = z.read("3D/3dmodel.model").decode()
    item_T = _mat(re.search(r'<item objectid="%s"[^>]*transform="([^"]+)"' % item_oid, main).group(1))
    comps = re.search(r'<object id="%s"[^>]*>\s*<components>(.*?)</components>' % item_oid, main, re.S).group(1)
    for path, oid, T in re.findall(r'p:path="([^"]+)" objectid="(\d+)"[^>]*transform="([^"]+)"', comps):
        if oid != comp_oid:
            continue
        s = z.read(path.lstrip("/")).decode()
        body = re.search(r'<object id="%s"[^>]*>(.*?)</object>' % oid, s, re.S).group(1)
        V = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', body), dtype=float)
        F = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', body), dtype=int)
        M = item_T @ _mat(T)
        Vh = np.column_stack((V, np.ones(len(V))))
        Vp = (M @ Vh.T).T[:, :3]
        mesh = trimesh.Trimesh(plate_to_design(Vp), F, process=True)
        mesh.merge_vertices(digits_vertex=4)
        return mesh
    raise KeyError((item_oid, comp_oid))


# 3MF sources for the watertight boom / stick halves
BOOM_HALVES = (("71", "69"), ("71", "70"))
STICK_HALVES = (("12", "11"), ("14", "13"))


# ---------------------------------------------------------------- STEP
def load_step_mesh(path, tol=0.05):
    import cadquery as cq
    shape = cq.importers.importStep(str(path)).val()
    verts, tris = shape.tessellate(tol)
    V = np.array([(p.x, p.y, p.z) for p in verts])
    return trimesh.Trimesh(V, np.array(tris), process=True)


def shape_to_mesh(shape, tol=0.05, ang=0.2):
    verts, tris = shape.tessellate(tol, ang)
    V = np.array([(p.x, p.y, p.z) for p in verts])
    return trimesh.Trimesh(V, np.array(tris), process=True)


# ---------------------------------------------------------------- manifold bridge
def to_manifold(mesh):
    import manifold3d as mf
    m = mf.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                tri_verts=np.asarray(mesh.faces, dtype=np.uint32))
    out = mf.Manifold(m)
    if out.status() != mf.Error.NoError:
        raise ValueError(f"not a manifold: {out.status()}")
    return out


def from_manifold(man):
    """Manifold -> trimesh without re-processing (processing deletes slivers and opens holes)."""
    m = man.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=False)


def shift_z(mesh, dz):
    m = mesh.copy()
    m.apply_translation((0, 0, dz))
    return m
