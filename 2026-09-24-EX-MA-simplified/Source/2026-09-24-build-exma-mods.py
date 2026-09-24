#!/usr/bin/env python3
"""EX-MA modified parts (mesh booleans with manifold3d).

Edits are internal, or user-approved exterior changes (circular turret flange,
turret lowered 13 mm, base race rim + retaining ring). Output: STL/ (assembly
frame, built position) plus Validation/2026-09-24-exterior-check.txt.

  tower         : square flange removed, circular flange + inner race + tube clamp hub,
                  centre bored for the 3/4" PVC tube, lowered TURRET_DZ
  base          : centre post removed (Ø46 hole + closing sleeve), lower race rim with
                  side-entry M3 nut slots, 4 screw holes to the pedestal
  boom halves   : interior cleared between the joints (walls kept >= WALL), PTFE stop
                  bulkhead for the stick tubes (+ bucket pass holes), drum key-screw head
                  sockets, M3 joining lugs; lowered
  stick halves  : interior cleared, PTFE stop bulkhead for the bucket tubes, drum key-screw
                  sockets, joining lugs; lowered
  bucket ears   : hex sockets for the bucket drum-axle; lowered
  bucket        : repaired STEP body + bracket I + lugs O/P as one part; lowered
"""
import importlib.util
import math
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


ex = _load("exma", "2026-09-24-exma_common.py")
rt = _load("routing", "2026-09-24-routing.py")
bp = _load("parts", "2026-09-24-build-parts.py")

DZ = ex.TURRET_DZ
WALL = 3.2                       # minimum wall kept when clearing boom / stick interiors
BOOM_CLEAR_S = (22.0, 188.0)     # clear between the joint bosses (arc length from the pin)
STICK_CLEAR_S = (19.0, 122.0)
BULKHEAD_T = 8.0
KEY_HEAD_D, KEY_HEAD_DEPTH = 6.8, 3.5
LUG = dict(size=(10.0, 8.0, 7.0))        # (along member, across v, radial) M3 joining lug


# ---------------------------------------------------------------- manifold helpers
DROPPED = []


def M(mesh):
    return ex.to_manifold(mesh)


def keep_main(man, name):
    """Keep the main body; drop floating rib fragments left by channel cuts (logged)."""
    parts = sorted(man.decompose(), key=lambda p: -p.volume())
    for p in parts[1:]:
        if abs(p.volume()) >= 0.05:                  # zero-volume slivers are not worth listing
            DROPPED.append((name, round(p.volume(), 1)))
    return parts[0]


def T(man):
    return ex.from_manifold(man)


def cq_to_man(wp, tol=0.03):
    return M(ex.shape_to_mesh(wp.val(), tol=tol))


def cylinder(p0, p1, r, n=48):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    # turned half a segment so no polygon vertex lands exactly on the v = 0 split plane
    c = mf.Manifold.cylinder(L, r, r, n).rotate([0, 0, 180.0 / n])
    # align +Z to d
    z = np.array([0, 0, 1.0])
    v = np.cross(z, d / L)
    s, cth = np.linalg.norm(v), float(z @ (d / L))
    if s < 1e-9:
        R = np.eye(3) if cth > 0 else np.diag([1, -1, -1.0])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        R = np.eye(3) + vx + vx @ vx * ((1 - cth) / s**2)
    A = np.column_stack((R, p0))
    return c.transform(A[:3, :4].tolist())


def box(center, size, R=None):
    b = mf.Manifold.cube(list(size), True)
    A = np.eye(4)
    if R is not None:
        A[:3, :3] = R
    A[:3, 3] = center
    return b.transform(A[:3, :4].tolist())


def member_frame(axis_ang):
    """Rotation: local x = along member (u-z plane), y = v, z = member normal."""
    d = np.array([math.cos(axis_ang), 0, math.sin(axis_ang)])
    n = np.array([-math.sin(axis_ang), 0, math.cos(axis_ang)])
    return np.column_stack((d, [0, 1, 0], n))


# ---------------------------------------------------------------- interior clearing
def clearing_volume(member_mesh, origin_uz, ang, s_range, step=4.0, inset=WALL):
    """Hull-inset lofted volume that removes internal ribs but keeps `inset` of the outer skin."""
    from shapely.geometry import MultiPoint
    d3 = np.array([math.cos(ang), 0.0, math.sin(ang)])
    n3 = np.array([-math.sin(ang), 0.0, math.cos(ang)])
    e_v = np.array([0.0, 1.0, 0.0])
    o3 = np.array([origin_uz[0], 0.0, origin_uz[1]])
    rings = []
    for s in np.arange(s_range[0], s_range[1] + 1e-6, step):
        c = o3 + s * d3
        sec = member_mesh.section(plane_origin=c, plane_normal=d3)
        if sec is None:
            continue
        P = sec.vertices - c
        xy = np.column_stack((P @ e_v, P @ n3))
        poly = MultiPoint(xy).convex_hull.buffer(-inset, join_style=2)
        if poly.is_empty or poly.area < 10:
            continue
        ring = np.array(poly.exterior.coords)[:-1]
        rings.append(np.array([c + x * e_v + y * n3 for x, y in ring]))
    pieces = []
    for a, b in zip(rings[:-1], rings[1:]):
        pieces.append(mf.Manifold.hull_points(np.vstack((a, b)).tolist()))
    return mf.Manifold.batch_boolean(pieces, mf.OpType.Add)


# ---------------------------------------------------------------- tower
TOWER_CLEAR_Z = (25.6, 57.6)      # built z span cleared inside the tower (flange top .. below the boom root)


def tower():
    sh = ex.load_stl_shells()
    t = M(sh["2"]).trim_by_plane([0, 0, 1], 35.5)          # remove the square flange
    t = t.translate([0, 0, DZ])
    # remove the internal funnel of the old centre post (r 13.6 -> 27, z 33..57 built): the PTFE
    # slack loop needs the tower interior. Hull-inset clearing keeps the 3.2 mm walls (+0.4 mm).
    t = t - clearing_volume(T(t), (0.0, TOWER_CLEAR_Z[0]), math.pi / 2, (0.0, TOWER_CLEAR_Z[1] - TOWER_CLEAR_Z[0]),
                            step=2.0, inset=3.6)
    t = t + cq_to_man(bp.turret_flange())
    top = rt.PVC_TOP_Z + DZ
    t = t - cylinder([0, 0, -5], [0, 0, 70], ex.PVC34_OD / 2 + 0.3)   # centre bored for the tube + cables
    if top > ex.FLANGE_Z[1]:
        t = t + (cylinder([0, 0, ex.FLANGE_Z[1] - 0.5], [0, 0, top], ex.PVC34_OD / 2 + 3.0)
                 - cylinder([0, 0, 0], [0, 0, top + 1], ex.PVC34_OD / 2 + 0.15))  # tube socket up to the PVC top
    # otherwise the PVC ends inside the flange bore (held by the hub pinch clamp below it)
    return t


# ---------------------------------------------------------------- base
def base():
    sh = ex.load_stl_shells()
    b = M(sh["0"])
    b = b - cylinder([0, 0, -1], [0, 0, 60], 23.0)                     # centre post removed
    b = b + (cylinder([0, 0, 0], [0, 0, ex.BASE_TOP_Z], 25.5) - cylinder([0, 0, -1], [0, 0, 20], 23.0))
    b = b + cq_to_man(bp.base_race_rim())
    for k in range(4):
        a = math.radians(45 + 90 * k)
        x, y = 38.0 * math.cos(a), 38.0 * math.sin(a)
        b = b - cylinder([x, y, -1], [x, y, 20], 2.2)                    # #8 wood screws to the pedestal
        b = b - cylinder([x, y, ex.BASE_TOP_Z - 2.5], [x, y, ex.BASE_TOP_Z + 1], 4.2)
    return b


# ---------------------------------------------------------------- tube stop bulkheads
def stop_bulkhead(member_mesh_full, tubes, pass_tubes, member):
    """Plate across the member interior at the tube stops: PTFE counterbores end in rope holes;
    pass-through holes for tubes that continue."""
    m0, p_stop, dvec = rt.tube_stop(tubes[0])
    ang = math.atan2(dvec[2], dvec[0])
    R = member_frame(ang)
    c = np.array(p_stop, float) - dvec * (BULKHEAD_T / 2)
    plate = box(c, (BULKHEAD_T, 60, 60), R)
    s_c = float((np.array([c[0], c[2]]) - np.array(origin_of(member))) @ np.array([math.cos(axis_of(member)), math.sin(axis_of(member))]))
    inner = clearing_volume(member_mesh_full, origin_of(member), axis_of(member), (s_c - 8, s_c + 8), 2.0, inset=2.0)
    plate = plate ^ inner
    for name in tubes:
        # the tube bore is the member's own channel (cut again after the plate is added); it ends
        # at p, so the tube seats on the channel end face and only the rope continues
        _, p, d = rt.tube_stop(name)
        plate = plate - cylinder(p - d * 20, p + d * 20, bp.ROPE_HOLE / 2)
    for p, d in (rt.bulkhead_clamp_points() if pass_tubes else []):
        # loose guide, kept well clear of the Ø5.2 channel surface (near-coincident cuts pinch the mesh)
        plate = plate - cylinder(p - d * 12, p + d * 12, ex.PTFE_OD / 2 + 1.2)
    return plate


def origin_of(member):
    return ex.P_BOOM0 if member == "boom" else ex.P_STICK0


def axis_of(member):
    return rt.BOOM_ANG if member == "boom" else rt.STICK_ANG


def joining_lugs(member_mesh_full, origin_uz, ang, stations, avoid):
    """M3 lugs at the top and bottom walls across the split plane (v = 0)."""
    R = member_frame(ang)
    d3, n3 = R[:, 0], R[:, 2]
    o3 = np.array([origin_uz[0], 0, origin_uz[1]])
    lugs, holes = [], []
    for s, side in stations:
        c0 = o3 + s * d3
        # find the inner wall along +/- normal at v = 0
        loc, _, _ = member_mesh_full.ray.intersects_location([c0], [side * n3], multiple_hits=True)
        if len(loc) == 0:
            continue
        dist = sorted(np.linalg.norm(loc - c0, axis=1))
        wall_in = dist[0]
        c = c0 + side * n3 * (wall_in - LUG["size"][2] / 2 + 1.0)
        if any(np.linalg.norm(poly - c, axis=1).min() < 5.0 for poly in avoid):
            continue
        lugs.append(box(c, LUG["size"], R))          # sits 1 mm into the wall, never reaches the skin
        holes.append(cylinder(c - np.array([0, 6, 0]), c + np.array([0, 6, 0]), ex.M3_CLEAR / 2))
    return lugs, holes


# ---------------------------------------------------------------- boom / stick halves
WALL_IN = dict(boom=17.0, stick=11.7)       # |v| of the inner side walls at the joint roots


def key_socket(pivot_uz, drive_uz_rel, v_from, v_to):
    p = np.array([pivot_uz[0] + drive_uz_rel[0], 0, pivot_uz[1] + drive_uz_rel[1]])
    return cylinder(p + [0, v_from, 0], p + [0, v_to, 0], KEY_HEAD_D / 2)


def drum_key_rel(drive_r, drive_ang_local, anchor_dir_deg):
    """Drum print frame (local +Y = crimp pocket) -> (u, z) offset of the key screw."""
    a = math.radians(anchor_dir_deg - 90.0 + drive_ang_local)
    return (drive_r * math.cos(a), drive_r * math.sin(a))


def guided(names, member):
    """Guided centreline pieces of the tubes on one member (original pose)."""
    out = []
    for n in names:
        pts = [p for m, p, z in rt.centreline(n) if m == member and z == member]
        if len(pts) > 1:
            out.append(np.array(pts))
    return out


def channels(polys):
    """Swept Ø5.2 channel along each polyline: a cylinder per segment plus a ball at every inner
    joint (without the balls, the wedge between two cylinder end caps leaves a knife-thin fin of
    rib material through the tube centreline on the outside of each bend). Ends stay flat."""
    r = ex.PTFE_OD / 2 + 0.6
    cuts = []
    for poly in polys:
        poly = [p for i, p in enumerate(poly) if i == 0 or np.linalg.norm(p - poly[i - 1]) > 1e-3]
        cuts += [cylinder(a, b, r) for a, b in zip(poly[:-1], poly[1:])]
        cuts += [mf.Manifold.sphere(r, 48).translate(list(p)) for p in poly[1:-1]]
    return mf.Manifold.batch_boolean(cuts, mf.OpType.Add)


def guide_lugs(names, member):
    """Loose tube guides where each tube enters its member's guided zone (the clamp point):
    a block from the inner side wall to the tube, with a Ø6 flared entry; the Ø5.2 channel continues through it."""
    lugs, bores = [], []
    for n in names:
        cl = rt.centreline(n)
        k = next(i for i, (m, p, z) in enumerate(cl) if m == member and z == member)
        p, q = cl[k][1], cl[k + 2][1]
        d = (q - p) / np.linalg.norm(q - p)
        ang = math.atan2(d[2], d[0])
        R = member_frame(ang)
        side = 1 if p[1] > 0 else -1
        v_wall = WALL_IN[member] + 1.0
        v_in = p[1] - side * 4.0
        c = np.array([p[0], (v_in + side * v_wall) / 2, p[2]])
        lugs.append((box(c, (6.0, abs(side * v_wall - v_in), 9.0), R), side))
        bores.append(cylinder(p - d * 8, p + d * 0.5, ex.PTFE_OD / 2 + 1.0))   # flared entry; the channel continues
    return lugs, bores


def boom_halves():
    halves = [ex.load_3mf_object(*h) for h in ex.BOOM_HALVES]
    full = trimesh.util.concatenate(halves)
    names = list(rt.TUBES)
    bulk = stop_bulkhead(full, ["stick_hi", "stick_lo"], ["bucket_hi", "bucket_lo"], "boom")
    avoid = [rt.natural(n) for n in names]
    lugs, lug_holes = joining_lugs(full, ex.P_BOOM0, rt.BOOM_ANG,
                                   [(45.0, 1), (45.0, -1), (110.0, 1), (110.0, -1), (160.0, 1), (160.0, -1)], avoid)
    keys = [drum_key_rel(bp.BOOM_DRIVE_R, a, 90.0) for a in bp.BOOM_DRIVE_ANGS]
    cut = channels(guided(names, "boom"))
    glugs, gbores = guide_lugs(names, "boom")
    drum_env = cylinder([ex.P_BOOM0[0], -8.0, ex.P_BOOM0[1]], [ex.P_BOOM0[0], 8.0, ex.P_BOOM0[1]], 18.2)
    out = []
    for i, h in enumerate(halves):
        sgn = -1 if i == 0 else 1                      # half 69 is -v, half 70 is +v
        m = M(h) - cut - drum_env                      # clean PTFE channels through the internal ribs
        side = box([100, sgn * 50 + (-0.35 if sgn < 0 else 0.15), 150], [400, 100, 400])   # 0.5 mm seam gap
        m = m + (bulk ^ side)
        for lug in lugs:
            m = m + (lug ^ side)
        for lug, lside in glugs:
            if lside == sgn:
                m = m + lug
        for hole in lug_holes + gbores:
            m = m - hole
        for key in keys:
            m = m - key_socket(ex.P_BOOM0, key, sgn * 16.5, sgn * (16.5 + KEY_HEAD_DEPTH))
        m = m - cut                                    # final pass: one consistent channel surface
        out.append(keep_main(m, f"boom half {sgn:+d}").translate([0, 0, DZ]))
    return out


def stick_halves():
    halves = [ex.load_3mf_object(*h) for h in ex.STICK_HALVES]
    full = trimesh.util.concatenate(halves)
    names = ["bucket_hi", "bucket_lo"]
    bulk = stop_bulkhead(full, names, [], "stick")
    avoid = [rt.natural(n) for n in names]
    lugs, lug_holes = joining_lugs(full, ex.P_STICK0, rt.STICK_ANG,
                                   [(40.0, 1), (40.0, -1), (100.0, 1), (100.0, -1), (150.0, 1), (150.0, -1)], avoid)
    keys = [drum_key_rel(bp.STICK_DRIVE_R, a, math.degrees(rt.BOOM_ANG)) for a in bp.STICK_DRIVE_ANGS]
    cut = channels(guided(names, "stick"))
    glugs, gbores = guide_lugs(names, "stick")
    out = []
    for i, h in enumerate(halves):
        sgn = -1 if i == 0 else 1
        m = M(h) - cut
        side = box([260, sgn * 50 + (-0.35 if sgn < 0 else 0.15), 170], [400, 100, 400])
        m = m + (bulk ^ side)
        for lug in lugs:
            m = m + (lug ^ side)
        for lug, lside in glugs:
            if lside == sgn:
                m = m + lug
        for hole in lug_holes + gbores:
            m = m - hole
        for key in keys:
            m = m - key_socket(ex.P_STICK0, key, sgn * 10.7, sgn * (10.7 + KEY_HEAD_DEPTH))
        m = m - cut
        out.append(keep_main(m, f"stick half {sgn:+d}").translate([0, 0, DZ]))
    return out


# ---------------------------------------------------------------- bucket + ears
def ears():
    sh = ex.load_stl_shells()
    af = bp.AXLE_HEX_AF + 0.3
    hexp = mf.Manifold.cylinder(80, af / 2 / math.cos(math.pi / 6), af / 2 / math.cos(math.pi / 6), 6, True)
    # match the drum-axle's hex: its print-frame X maps to (stick angle - 90 deg) in the u-z plane
    phase = (math.degrees(rt.STICK_ANG) - 90.0) % 60.0
    hexp = hexp.rotate([0, 0, phase])
    hexp = hexp.transform([[1, 0, 0, ex.P_BUCKET0[0]], [0, 0, -1, 0], [0, 1, 0, ex.P_BUCKET0[1]]])
    out = []
    for lab in ("G", "H"):
        m = M(sh[lab]) - hexp
        out.append(m.translate([0, 0, DZ]))
    return out


def bucket():
    sh = ex.load_stl_shells()
    body = ex.load_step_mesh(ex.BUCKET_STEP)
    body.apply_translation(ex.BUCKET_STEP_OFFSET)
    m = M(body)
    for lab in ("O", "P"):
        m = m + M(sh[lab])
    # bracket I is 4 touching sub-bodies (8 edges shared by 4 faces): union them one by one
    merged_I = True
    for piece in sh["I"].split(only_watertight=False):
        piece.merge_vertices()
        trimesh.repair.fix_normals(piece)
        try:
            m = m + M(piece)
        except ValueError:
            merged_I = False
    return keep_main(m, "bucket").translate([0, 0, DZ]), merged_I


# ---------------------------------------------------------------- robust STL export
def unzip_coincident(V, F, step=0.02, rounds=6):
    """STL stores no connectivity, so vertices that the manifold kernel keeps distinct but at the
    same float32 position (where two internal surfaces touch) merge on reload into 4-face edges.
    Move each such copy `step` mm toward the centroid of its own face fan until all are unique."""
    V = V.astype(np.float32).astype(np.float64)
    for _ in range(rounds):
        _, inv, cnt = np.unique(V.astype(np.float32), axis=0, return_inverse=True, return_counts=True)
        dup = np.where(cnt[inv.ravel()] > 1)[0]
        if len(dup) == 0:
            break
        UNZIPPED.append(len(dup))
        cen = V[F].mean(axis=1)
        acc, n = np.zeros_like(V), np.zeros(len(V))
        for k in range(3):
            np.add.at(acc, F[:, k], cen)
            np.add.at(n, F[:, k], 1)
        d = acc[dup] / n[dup, None] - V[dup]
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
        V[dup] = (V[dup] + step * d).astype(np.float32).astype(np.float64)
    return V


def export_checked(mesh, path, name):
    """Export the manifold mesh as STL and verify the reloaded file is watertight; coincident
    vertex copies are unzipped first; sliver cleanup (simplify) only if that is not enough."""
    clean = mesh
    for tol in (None, 0.02, 0.05):
        m = mesh if tol is None else T(keep_main(M(mesh).simplify(tol), name + " (after cleanup)"))
        clean = trimesh.Trimesh(unzip_coincident(m.vertices, m.faces), m.faces, process=False)
        clean.export(path)
        if trimesh.load(path, force="mesh").is_watertight:
            return clean
    print(f"WARNING {name}: not watertight after STL round trip")
    return clean


UNZIPPED = []


# ---------------------------------------------------------------- exterior check
def exterior_deviation(original, modified, dz=0.0, n=30000, band=None, context=None):
    """Sample the original surface; keep points whose outward normal ray escapes the whole
    assembled member (`context`, e.g. both halves) = true exterior skin; report their distance
    to the modified part's surface."""
    ctx = context if context is not None else original
    pts, fi = trimesh.sample.sample_surface(original, n, seed=1)
    nrm = original.face_normals[fi]
    escapes = ~ctx.ray.intersects_any(pts + nrm * 0.05, nrm)
    ext = pts[escapes]
    if band is not None:
        ext = ext[band(ext)]
    ext = ext + np.array([0, 0, dz])
    _, dist, _ = trimesh.proximity.closest_point(modified, ext)
    return len(ext), float(np.percentile(dist, 99)), float(dist.max())


def main():
    out_stl = ex.OUT / "STL"
    out_val = ex.OUT / "Validation"
    out_stl.mkdir(exist_ok=True)
    out_val.mkdir(exist_ok=True)
    sh = ex.load_stl_shells()
    results = {}
    tw = T(tower()); results["tower"] = tw
    bs = T(base()); results["base"] = bs
    bl, br = [T(m) for m in boom_halves()]
    results["boom-half-right"], results["boom-half-left"] = bl, br      # 3MF half 69 is -v (operator's right)
    sl, sr = [T(m) for m in stick_halves()]
    results["stick-half-right"], results["stick-half-left"] = sl, sr
    el, er = [T(m) for m in ears()]
    results["bucket-ear-left"], results["bucket-ear-right"] = el, er    # ear G is +v (operator's left)
    bk, merged_I = bucket()
    results["bucket"] = T(bk)
    lines = ["EX-MA modified parts - exterior deviation check (design mm)",
             "samples on the original outer skin; distance to the modified part's surface",
             f"bucket bracket I merged into bucket: {merged_I}", ""]
    for name, mesh in results.items():
        results[name] = export_checked(mesh, out_stl / f"2026-09-24-{name}.stl", name)
    checks = [
        ("boom-half-right", ex.load_3mf_object(*ex.BOOM_HALVES[0]), DZ),
        ("boom-half-left", ex.load_3mf_object(*ex.BOOM_HALVES[1]), DZ),
        ("stick-half-right", ex.load_3mf_object(*ex.STICK_HALVES[0]), DZ),
        ("stick-half-left", ex.load_3mf_object(*ex.STICK_HALVES[1]), DZ),
        ("tower", sh["2"], DZ),
        ("base", sh["0"], 0.0),
    ]
    boom_full = trimesh.util.concatenate([ex.load_3mf_object(*h) for h in ex.BOOM_HALVES])
    stick_full = trimesh.util.concatenate([ex.load_3mf_object(*h) for h in ex.STICK_HALVES])
    for name, orig, dz in checks:
        band = None
        ctx = boom_full if name.startswith("boom") else stick_full if name.startswith("stick") else None
        if name == "tower":
            band = lambda p: (p[:, 2] > 36.0) & (np.hypot(p[:, 0], p[:, 1]) > 18.0) & \
                ~((np.hypot(p[:, 0], p[:, 1]) < 31.0) & (p[:, 2] < TOWER_CLEAR_Z[1] - DZ + 1.0))   # flange, bore, funnel
        if name == "base":
            band = lambda p: (p[:, 2] < 14.0) & (np.hypot(p[:, 0], p[:, 1]) > 26.0)   # rim + centre hole approved
        n, p99, mx = exterior_deviation(orig, results[name], dz, band=band, context=ctx)
        lines.append(f"{name:18s} samples={n:6d}  p99={p99:6.3f}  max={mx:6.3f}")
    lines.append("")
    lines.append("floating fragments dropped (name, volume mm3): " + (", ".join(f"{a} {b}" for a, b in DROPPED) or "none"))
    lines.append(f"coincident vertex copies unzipped by 0.02 mm (all parts): {sum(UNZIPPED)}")
    lines.append("")
    for name, mesh in results.items():
        lines.append(f"{name:18s} watertight={mesh.is_watertight}  bodies={len(mesh.split(only_watertight=False))}"
                     f"  volume={mesh.volume / 1000:7.2f} cm3  bbox={np.round(mesh.extents, 1).tolist()}")
    (out_val / "2026-09-24-exterior-check.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
