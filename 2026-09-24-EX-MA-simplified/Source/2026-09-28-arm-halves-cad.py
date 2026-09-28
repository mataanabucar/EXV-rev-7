"""Boom / stick halves as CAD solids.

The printed halves are the original EX-MA halves plus the modifications of
2026-09-24-build-exma-mods.py (rope channels, stop bulkhead, joining and guide lugs, lug holes,
drum-key counterbores, stick root fill and solid nose, sliver trims). That script works on meshes;
here the original halves are converted to exact B-reps (2026-09-28-mesh-to-brep.py) and every
modification is redone as a CAD boolean with the parameters the mesh pipeline computed (captured by
running it with recording wrappers).

    python 2026-09-28-arm-halves-cad.py boom|stick WORKDIR
        -> WORKDIR/parts/<member>-half-right.step, <member>-half-left.step (printed pose)

Deliberate approximations (all inside the part or within 0.15 mm): the stick nose is one r 11.9
cylinder (print: 12-sided hood filled to r 11.75 - 12.02) and the stop bulkhead is clipped to one
convex hull of the inner section (print: 2 mm hull pieces).
"""
import importlib.util
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh
import cadquery as cq

SRC = Path(__file__).resolve().parent
V = cq.Vector


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, SRC / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


RB = _load("mesh_to_brep", "2026-09-28-mesh-to-brep.py")
ex = _load("exma", "2026-09-24-exma_common.py")


def placed(shape, T):
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    t = gp_Trsf()
    t.SetValues(*[float(v) for v in np.asarray(T)[:3, :4].ravel()])
    return cq.Shape.cast(BRepBuilderAPI_Transform(shape.wrapped, t, True).Shape())


# ---------------------------------------------------------------- CAD primitives
def cyl(p0, p1, r):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    return cq.Solid.makeCylinder(float(r), L, V(*p0), V(*(d / L)))


def sph(p, r):
    return cq.Solid.makeSphere(float(r), V(*map(float, p)), angleDegrees1=-90, angleDegrees2=90)


def box(center, size, R=None):
    sx, sy, sz = map(float, size)
    b = cq.Solid.makeBox(sx, sy, sz, V(-sx / 2, -sy / 2, -sz / 2))
    T = np.eye(4)
    if R is not None:
        T[:3, :3] = R
    T[:3, 3] = center
    return placed(b, T)


def man_to_cad(man):
    """A (simple) manifold solid -> exact B-rep through the mesh converter."""
    m = man.to_mesh()
    mesh = trimesh.Trimesh(np.asarray(m.vert_properties, dtype=np.float64)[:, :3], np.asarray(m.tri_verts), process=False)
    s, rep = RB.rebrep(mesh)
    return s, rep


# ---------------------------------------------------------------- recording run of the mesh pipeline
def record(member):
    """Run the original halves pipeline for one member with recording wrappers; returns the
    primitive parameters it used, per half."""
    mods = _load("mods", "2026-09-24-build-exma-mods.py")
    reg = {}
    orig_box, orig_cyl = mods.box, mods.cylinder
    flakes = []
    state = dict(in_flake=False)

    def rbox(center, size, R=None):
        m = orig_box(center, size, R)
        reg[id(m)] = ("box", np.array(center, float), np.array(size, float), None if R is None else np.array(R, float))
        if state["in_flake"]:
            flakes[-1].append((np.array(center, float), np.array(size, float)))
        return m

    def rcyl(p0, p1, r, n=48):
        m = orig_cyl(p0, p1, r, n)
        reg[id(m)] = ("cyl", np.array(p0, float), np.array(p1, float), float(r))
        return m
    mods.box, mods.cylinder = rbox, rcyl
    orig_trim = mods.trim_flakes

    def rtrim(man, full):
        flakes.append([])
        state["in_flake"] = True
        try:
            return orig_trim(man, full)
        finally:
            state["in_flake"] = False
    mods.trim_flakes = rtrim
    captured = {}
    orig_jl, orig_gl, orig_sb = mods.joining_lugs, mods.guide_lugs, mods.stop_bulkhead

    def rjl(*a, **k):
        lugs, holes = orig_jl(*a, **k)
        captured["lugs"] = [reg[id(x)] for x in lugs]
        captured["lug_holes"] = [reg[id(x)] for x in holes]
        return lugs, holes

    def rgl(*a, **k):
        lugs, bores = orig_gl(*a, **k)
        captured["glugs"] = [(reg[id(x)], s) for x, s in lugs]
        captured["gbores"] = [reg[id(x)] for x in bores]
        return lugs, bores

    def rsb(*a, **k):
        plate = orig_sb(*a, **k)
        captured["bulk"] = plate
        return plate
    mods.joining_lugs, mods.guide_lugs, mods.stop_bulkhead = rjl, rgl, rsb
    if member == "stick":
        orig_nose, orig_root = mods.nose_fill, mods.root_fill
        captured["nose"], captured["root"] = [], []

        def rnose(v_out):
            n = orig_nose(v_out)
            captured["nose"].append((v_out, n))
            return n

        def rroot(half, sgn, mem):
            r = orig_root(half, sgn, mem)
            captured["root"].append((sgn, r))
            return r
        mods.nose_fill, mods.root_fill = rnose, rroot
        out = mods.stick_halves()
    else:
        out = mods.boom_halves()
    captured["flakes"] = flakes           # per half, in processing order (-v first, then +v)
    captured["result"] = out
    captured["mods"] = mods
    return captured


# ---------------------------------------------------------------- CAD replay
def channels_cad(mods, polys):
    """Rope-tube channels (PTFE clearance) as rope paths (polylines); cut_channel() cuts them one
    at a time, since a single fused tool for all paths is too heavy for the boolean."""
    return [[p for i, p in enumerate(poly) if i == 0 or np.linalg.norm(p - poly[i - 1]) > 1e-3] for poly in polys]


def channel_tool(poly, end_spheres=(False, False)):
    """Swept channel along a polyline: cylinders on the segments, spheres on the inner joints (and
    on the ends when asked)."""
    r = ex.PTFE_OD / 2 + 0.6
    parts = [cyl(a, b, r) for a, b in zip(poly[:-1], poly[1:])] + [sph(p, r) for p in poly[1:-1]]
    parts += [sph(p, r) for p, on in zip((poly[0], poly[-1]), end_spheres) if on]
    return safe_clean(parts[0].fuse(*parts[1:])) if len(parts) > 1 else parts[0]


def cut_channel(m, poly, end_spheres=(False, False)):
    """Cut one rope path; when the whole path will not cut cleanly, cut its two halves (split at a
    joint, the first half carrying that joint's sphere), down to single segments. The material
    removed is the same: cutting A u B = cutting A, then B."""
    short = len(poly) == 2 and np.linalg.norm(np.asarray(poly[1]) - np.asarray(poly[0])) < 1.0
    try:
        return bop(m, "cut", channel_tool(poly, end_spheres), repair=short)
    except RuntimeError:
        if short:
            raise
    if len(poly) == 2:
        # a straight segment in two (the sphere at the midpoint lies inside the two cylinders)
        a, b = np.asarray(poly[0], float), np.asarray(poly[1], float)
        poly = [a, (a + b) / 2, b]
    k = len(poly) // 2
    m = cut_channel(m, poly[:k + 1], (end_spheres[0], True))
    return cut_channel(m, poly[k:], (False, end_spheres[1]))


def prim(rec):
    if rec[0] == "box":
        return box(rec[1], rec[2], rec[3])
    return cyl(rec[1], rec[2], rec[3])


NOSE_R_CAD = 11.9        # the printed nose is the old 12-sided hood (r 11.57-12.02) filled to r 11.75;
                         # the CAD nose is one cylinder between the two (within 0.15 mm of the print)
NOSE_CUT_R = 12.6        # replaced region reaches past the hood's corners


def nose_region_cad(mods, v_out, r, disc_r):
    """The region the solid nose occupies (drum sector |v| < drum half-width, side sectors out to
    the plate, journal bosses), without the drum-axle clearance."""
    bp = mods.bp
    cu, cz = ex.P_BUCKET0
    zd, zc = bp.AXLE_Z["drum"], bp.AXLE_Z["cone"]

    def pie(rr, a0, a1, v):
        a1 = a1 + 360.0 if a1 <= a0 else a1
        P = lambda a: V(cu + rr * math.cos(math.radians(a)), v, cz + rr * math.sin(math.radians(a)))
        c = V(cu, v, cz)
        am = 0.5 * (a0 + a1)
        e = [cq.Edge.makeLine(c, P(a0)), cq.Edge.makeThreePointArc(P(a0), P(am), P(a1)), cq.Edge.makeLine(P(a1), c)]
        return cq.Wire.assembleEdges(e)

    def sector(rr, a0, a1, v0, v1):
        f = cq.Face.makeFromWires(pie(rr, a0, a1, v0))
        return cq.Solid.extrudeLinear(f, V(0, v1 - v0, 0))
    pieces = [sector(r, *mods.NOSE_DRUM_SECTOR, -zd, zd)]
    for sgn in (1, -1):
        lo, hi = sorted((sgn * zd, sgn * v_out))
        pieces.append(sector(r, *mods.NOSE_SIDE_SECTOR, lo, hi))
        lo, hi = sorted((sgn * zc, sgn * v_out))
        pieces.append(cyl([cu, lo, cz], [cu, hi, cz], disc_r))
    return safe_clean(pieces[0].fuse(*pieces[1:]))


def nose_fill_cad(mods, v_out, R=None):
    """mods.nose_fill as exact CAD: pie-slice prisms about the bucket pin axis (+v), the outer 0.8 mm
    chamfer as a ruled taper, the journal bosses, minus the drum-axle clearance (revolved)."""
    bp = mods.bp
    NR = mods.NOSE_R if R is None else R
    cu, cz = ex.P_BUCKET0
    zd, zc = bp.AXLE_Z["drum"], bp.AXLE_Z["cone"]
    rf = ex.DRUM["bucket"]["pitch"] / 2 - bp.ROPE / 2 + bp.BUCKET_LIP
    rj = bp.AXLE_JOURNAL_D / 2
    hole = 12.7 / 2

    def pie(r, a0, a1, v):
        a1 = a1 + 360.0 if a1 <= a0 else a1
        P = lambda a: V(cu + r * math.cos(math.radians(a)), v, cz + r * math.sin(math.radians(a)))
        c = V(cu, v, cz)
        am = 0.5 * (a0 + a1)
        e = [cq.Edge.makeLine(c, P(a0)), cq.Edge.makeThreePointArc(P(a0), P(am), P(a1)), cq.Edge.makeLine(P(a1), c)]
        return cq.Wire.assembleEdges(e)

    def sector(r, a0, a1, v0, v1, r_at_v1=None):
        if r_at_v1 is None:
            f = cq.Face.makeFromWires(pie(r, a0, a1, v0))
            return cq.Solid.extrudeLinear(f, V(0, v1 - v0, 0))
        return cq.Solid.makeLoft([pie(r, a0, a1, v0), pie(r_at_v1, a0, a1, v1)], True)

    def chamfered(r, a0, a1, v_in, v_o):
        s = 1.0 if v_o > 0 else -1.0
        v_c = v_o - s * 0.8
        lo, hi = sorted((v_in, v_c))
        return sector(r, a0, a1, lo, hi).fuse(sector(r, a0, a1, v_c, v_o, r_at_v1=r - 0.8))

    pieces = [sector(NR, *mods.NOSE_DRUM_SECTOR, -zd, zd)]
    for sgn in (1, -1):
        pieces.append(chamfered(NR, *mods.NOSE_SIDE_SECTOR, sgn * zd, sgn * v_out))
        lo, hi = sorted((sgn * zc, sgn * v_out))
        pieces.append(cyl([cu, lo, cz], [cu, hi, cz], mods.NOSE_BOSS_R))
    fill = safe_clean(pieces[0].fuse(*pieces[1:]))
    prof = [(0.0, -30.0), (hole, -30.0), (hole, -zc), (rj + mods.NOSE_CLEAR, -zc), (rf + mods.NOSE_CLEAR, -zd),
            (rf + mods.NOSE_CLEAR, zd), (rj + mods.NOSE_CLEAR, zc), (hole, zc), (hole, 30.0), (0.0, 30.0)]
    # profile in the u-v plane (radius along +u, axial along v), revolved about the pin axis (+v)
    rev = (cq.Workplane("XY").polyline([(cu + r, v) for r, v in prof]).close()
           .revolve(360, (cu, 0, 0), (cu, 1, 0)).val().translate(V(0, 0, cz)))
    return safe_clean(fill.cut(rev))


VERBOSE = False


def bop(a, op, b, repair=True):
    """Boolean with fall-backs: exact first, then fuzzy (1 um, 10 um) when the result is null,
    empty, invalid or loses the body (a result far smaller than a cut can explain). With repair,
    a plausible but invalid result is accepted after ShapeFix as a last resort."""
    last = None
    va = a.Volume()
    vb = b.Volume()
    for tol in (None, 1e-3, 1e-2):
        try:
            f = getattr(a, op)
            r = f(b) if tol is None else f(b, tol=tol)
            if r is not None and not r.wrapped.IsNull() and r.Solids() and r.isValid():
                vr = r.Volume()
                ok = (vr >= va - vb - 1.0) if op == "cut" else (vr >= va - 1.0) if op == "fuse" else True
                if VERBOSE:
                    print(f"      {op:5s} tol={tol} vol {va:.1f} -> {vr:.1f} (tool {vb:.1f}) solids {len(r.Solids())} ok={ok}", flush=True)
                if ok:
                    return r
            last = r
        except Exception as e:
            last = e
    # swapped operands (fuse is symmetric), then the tool nudged by 3 um: a coincidence of the tool
    # with an edge of the converted body is the usual cause of a lost body
    tries = [("swap", None)] if op == "fuse" else []
    tries += [("nudge", d) for d in ((1, 1, 1), (-1, 1, -1), (1, -1, -1), (-1, -1, 1))]
    for kind, d in tries:
        try:
            if kind == "swap":
                r = b.fuse(a)
            else:
                r = getattr(a, op)(b.translate(V(*(0.003 * np.array(d, float) / math.sqrt(3)))))
            if r is not None and not r.wrapped.IsNull() and r.Solids() and r.isValid():
                vr = r.Volume()
                ok = (vr >= va - vb - 1.0) if op == "cut" else (vr >= va - 1.0) if op == "fuse" else True
                if VERBOSE:
                    print(f"      {op:5s} {kind} vol {va:.1f} -> {vr:.1f} (tool {vb:.1f}) solids {len(r.Solids())} ok={ok}", flush=True)
                if ok:
                    return r
        except Exception as e:
            last = e
    if not repair:
        raise RuntimeError(f"boolean {op} failed: {last}")
    # no fully valid result: accept a plausible one (right volume, one body more or less) and repair
    # its tolerances; the finished part is healed and validated at the end
    for tol in (None, 1e-3, 1e-2):
        try:
            f = getattr(a, op)
            r = f(b) if tol is None else f(b, tol=tol)
            if r is None or r.wrapped.IsNull() or not r.Solids():
                continue
            vr = r.Volume()
            ok = (vr >= va - vb - 1.0) if op == "cut" else (vr >= va - 1.0) if op == "fuse" else vr > 0
            if not ok or vr > va + vb + 1.0:
                continue
            from OCP.ShapeFix import ShapeFix_Shape
            fx = ShapeFix_Shape(r.wrapped)
            fx.Perform()
            r2 = cq.Shape.cast(fx.Shape())
            if VERBOSE:
                print(f"      {op:5s} tol={tol} ACCEPTED (repaired, valid={r2.isValid()}) vol {va:.1f} -> {r2.Volume():.1f}", flush=True)
            return r2
        except Exception as e:
            last = e
    raise RuntimeError(f"boolean {op} failed: {last}")


def root_fill_cad(mods, half_mesh, sgn, member="stick"):
    """mods.root_fill as a CAD prism: the side plate's outline (taken 0.1 mm inside the plate, where
    it is largest) cut to the fill radius about the pivot, fitted with lines and arcs, extruded along
    v from the inner wall to the plate. Shrunk 0.02 mm so no face lies flush on the member's skin."""
    from shapely.geometry import Polygon, Point
    from shapely.geometry.polygon import orient
    cu, cz = mods.origin_of(member)
    v_from, (v_lo, v_hi), radius = mods.ROOT_FILL[member]

    def outline_at(v):
        sec = half_mesh.section(plane_origin=[0, sgn * v, 0], plane_normal=[0, 1, 0])
        loops = [Polygon(e[:, [0, 2]]) for e in sec.discrete if len(e) > 3] if sec is not None else []
        return max(loops, key=lambda p: p.area) if loops else None
    vs = np.arange(v_lo, v_hi, 0.05)
    areas = np.array([(lambda o: 0.0 if o is None else o.area)(outline_at(v)) for v in vs])
    v_face = float(vs[np.argmax(areas > 0.97 * areas.max())]) + 0.1
    outline = outline_at(v_face)
    region = Polygon(outline.exterior).intersection(Point(cu, cz).buffer(radius, 256)).buffer(-0.02, join_style=2)
    region = orient(region, 1.0)
    v0, v1 = sorted((sgn * v_from, sgn * v_face))
    # frame: extrusion axis +v; local (a, b) = (u, -z)
    fr = RB.Frame((0, 0, 0), (1, 0, 0), (0, 1, 0))
    pts = np.array(region.exterior.coords)[:-1]
    loc = np.column_stack((pts[:, 0], -pts[:, 1]))
    segs = RB.fit_loop(loc, tol=0.01)
    face = cq.Face.makeFromWires(RB.make_wire(segs, fr, v0))
    return cq.Solid.extrudeLinear(face, V(0, v1 - v0, 0))


def hull_cad(points):
    """Convex hull of points as an exact planar-faced solid."""
    h = trimesh.convex.convex_hull(np.asarray(points, float))
    s, rep = RB.rebrep(h, unify=True)
    return s


def bulkhead_cad(mods, member, full):
    """mods.stop_bulkhead as CAD: an 8 mm plate across the member at the tube stops, clipped to the
    member's inner hull (lofted hull pieces, 2 mm inset), rope holes and loose PTFE pass holes."""
    from shapely.geometry import MultiPoint
    rt, bp = mods.rt, mods.bp
    if member == "boom":
        tubes, pass_tubes = ["stick_hi", "stick_lo"], True
    else:
        tubes, pass_tubes = ["bucket_hi", "bucket_lo"], False
    m0, p_stop, dvec = rt.tube_stop(tubes[0])
    ang = math.atan2(dvec[2], dvec[0])
    R = mods.member_frame(ang)
    c = np.array(p_stop, float) - dvec * (mods.BULKHEAD_T / 2)
    plate = box(c, (mods.BULKHEAD_T, 60, 60), R)
    origin, axis = mods.origin_of(member), mods.axis_of(member)
    s_c = float((np.array([c[0], c[2]]) - np.array(origin)) @ np.array([math.cos(axis), math.sin(axis)]))
    d3 = np.array([math.cos(axis), 0.0, math.sin(axis)])
    n3 = np.array([-math.sin(axis), 0.0, math.cos(axis)])
    e_v = np.array([0.0, 1.0, 0.0])
    o3 = np.array([origin[0], 0.0, origin[1]])
    rings = []
    # the plate spans s_c +- 4, i.e. exactly the hull pieces between the rings at s_c - 4 ... s_c + 4;
    # their union is modelled as the single convex hull of those rings (within 1 % of the piece union;
    # fusing the separate pieces along their shared ring faces is not robust)
    for s in np.arange(s_c - 4, s_c + 4 + 1e-6, 2.0):
        cc = o3 + s * d3
        sec = full.section(plane_origin=cc, plane_normal=d3)
        if sec is None:
            continue
        Pp = sec.vertices - cc
        poly = MultiPoint(np.column_stack((Pp @ e_v, Pp @ n3))).convex_hull.buffer(-2.0, join_style=2)
        if poly.is_empty or poly.area < 10:
            continue
        rings.append(np.array([cc + x * e_v + y * n3 for x, y in np.array(poly.exterior.coords)[:-1]]))
    # one convex slab per ring interval (each exactly the original hull piece, clipped to the plate's
    # thickness, which ends on the outer rings), glued together along their shared ring faces
    slabs = [hull_cad(np.vstack((a, b))) for a, b in zip(rings[:-1], rings[1:])]
    try:
        inner = safe_clean(slabs[0].fuse(*slabs[1:], glue=True))
        if not (inner.isValid() and len(inner.Solids()) == 1):
            raise ValueError("glue")
    except Exception:
        inner = hull_cad(np.vstack(rings))
    plate = bop(plate, "intersect", inner)
    for name in tubes:
        _, p, d = rt.tube_stop(name)
        plate = bop(plate, "cut", cyl(p - d * 20, p + d * 20, bp.ROPE_HOLE / 2))
    if pass_tubes:
        for p, d in rt.bulkhead_clamp_points():
            plate = bop(plate, "cut", cyl(p - d * 12, p + d * 12, ex.PTFE_OD / 2 + 1.2))
    return plate


def cut_flake(m, c, s):
    """Trim one sliver: the flake box only has to contain it, so a box 2 % smaller or larger
    serves as well when the exact one meets a face edge-on; an empty box is skipped."""
    b = box(c, s)
    try:
        inside = m.intersect(b).Volume()
    except Exception:
        inside = None
    if inside is not None and inside < 1e-3:
        return m
    for k in (1.0, 0.98, 1.02, 0.95, 1.05):
        try:
            return bop(m, 'cut', box(c, np.asarray(s) * k))
        except RuntimeError:
            continue
    raise RuntimeError(f"flake cut failed at {np.round(c, 2)}")


def safe_clean(shape):
    """Merge faces on one surface, but only when the result stays a valid solid."""
    try:
        c = shape.clean()
        if c.isValid() and abs(c.Volume() - shape.Volume()) < 1e-3 * abs(shape.Volume()) + 0.01:
            return c
    except Exception:
        pass
    return shape


def largest(shape):
    sols = shape.Solids()
    return max(sols, key=lambda s: s.Volume()) if sols else shape


def replay(member, raw_halves_cad, cap):
    """raw_halves_cad: [half -v, half +v] exact B-reps of the original halves (original pose); a half
    given as None is skipped (its slot in the result is None)."""
    mods = cap["mods"]
    rt = mods.rt
    bp = mods.bp
    DZ = ex.TURRET_DZ
    if member == "boom":
        names = list(rt.TUBES)
        cut = channels_cad(mods, mods.guided(names, "boom"))
        keys = [mods.drum_key_rel(bp.BOOM_DRIVE_R, a, 90.0) for a in bp.BOOM_DRIVE_ANGS]
        drum_env = cyl([ex.P_BOOM0[0], -8.0, ex.P_BOOM0[1]], [ex.P_BOOM0[0], 8.0, ex.P_BOOM0[1]], 18.2)
        piv, v_key = ex.P_BOOM0, 16.5
        side_c = [100, None, 150]
    else:
        names = ["bucket_hi", "bucket_lo"]
        cut = channels_cad(mods, mods.guided(names, "stick"))
        keys = [mods.drum_key_rel(bp.STICK_DRIVE_R, a, math.degrees(rt.BOOM_ANG)) for a in bp.STICK_DRIVE_ANGS]
        drum_env = None
        piv, v_key = ex.P_STICK0, 10.7
        side_c = [260, None, 170]
    bulk_cad = bulkhead_cad(mods, member, cap["full"])
    rep_b = dict(valid=bulk_cad.isValid(), faces=len(bulk_cad.Faces()), vol=round(bulk_cad.Volume(), 1))
    if VERBOSE:
        print("    bulkhead", rep_b, flush=True)
    lugs = [prim(r) for r in cap["lugs"]]
    holes = [prim(r) for r in cap["lug_holes"]] + [prim(r) for r in cap["gbores"]]
    out = []
    for i, h in enumerate(raw_halves_cad):
        if h is None:
            out.append(None)
            continue
        sgn = -1 if i == 0 else 1
        # fuses first, cuts after: the channels are cut once at the end, (H - C) u F - C = (H u F) - C,
        # and an early cut would only raise tolerances where the fused pieces land
        m = h
        if drum_env is not None:
            m = bop(m, 'cut', drum_env)
        side = box([side_c[0], sgn * 50 + (-0.35 if sgn < 0 else 0.15), side_c[2]], [400, 100, 400])
        m = bop(m, 'fuse', bulk_cad.intersect(side))
        for lug in lugs:
            m = bop(m, 'fuse', lug.intersect(side))
        for rec, lside in cap["glugs"]:
            if lside == sgn:
                m = bop(m, 'fuse', prim(rec))
        for hole in holes:
            m = bop(m, 'cut', hole)
        if member == "stick":
            rf_cad = root_fill_cad(mods, cap["halves_mesh"][i], sgn)
            m = bop(m, 'fuse', rf_cad)
            m = bop(m, "cut", cyl([ex.P_STICK0[0], sgn * 5.0, ex.P_STICK0[1]], [ex.P_STICK0[0], sgn * 20.0, ex.P_STICK0[1]],
                          ex.PIN_BORE / 2))
        for k in keys:
            p = np.array([piv[0] + k[0], 0, piv[1] + k[1]])
            m = bop(m, 'cut', cyl(p + [0, sgn * v_key, 0], p + [0, sgn * (v_key + mods.KEY_HEAD_DEPTH), 0], mods.KEY_HEAD_D / 2))
        if member == "stick":
            v_out, nose = cap["nose"][i]
            # the old nose is a 0.35 mm faceted hood: booleans cannot cut through it, so the whole
            # nose tip is replaced (cut the region, glue the solid nose into the matching cavity)
            nose_side = box([260, sgn * 50.1, 170], [400, 100, 400])
            region = nose_region_cad(mods, v_out + 1.0, NOSE_CUT_R, mods.NOSE_BOSS_R).intersect(nose_side)
            nose_cad = nose_fill_cad(mods, v_out, R=NOSE_R_CAD).intersect(nose_side)
            m = bop(m, 'cut', region)
            try:
                g = m.fuse(nose_cad, glue=True)
                if not (g.Solids() and g.Volume() > m.Volume() + 0.9 * nose_cad.Volume()):
                    raise ValueError("glue")
                m = g
            except Exception:
                m = bop(m, 'fuse', nose_cad)
        for poly in cut:
            m = cut_channel(m, poly)
        m = largest(safe_clean(m))
        for c, s in cap["flakes"][i]:
            m = cut_flake(m, c, s)
        m = largest(safe_clean(m))
        out.append(m.translate(V(0, 0, DZ)))
    return out, dict(bulk=rep_b)


# ---------------------------------------------------------------- command line
HALVES = {"boom": (ex.BOOM_HALVES, ["boom-half-right", "boom-half-left"]),
          "stick": (ex.STICK_HALVES, ["stick-half-right", "stick-half-left"])}
# converter settings tried in turn until every boolean of the replay succeeds
SETTINGS = [{}, {"REBREP_MID_TOL": "inf"}, {"REBREP_MID_TOL": "inf", "REBREP_REFINE": "0"}]


def read_brep(path):
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shape
    sh = TopoDS_Shape()
    BRepTools.Read_s(sh, str(path), BRep_Builder())
    s = cq.Shape.cast(sh)
    return s.Solids()[0] if s.Solids() else s


def export_checked(shape, path):
    """Write the solid to STEP and read it back; when the STEP reader rebuilds a face differently,
    try the face-merged and the repaired shape. Returns the solid that reads back valid, or None."""
    from OCP.ShapeFix import ShapeFix_Shape

    def fixed(s):
        fx = ShapeFix_Shape(s.wrapped)
        fx.Perform()
        return cq.Shape.cast(fx.Shape())
    for cand in (lambda: shape, lambda: safe_clean(shape), lambda: fixed(shape), lambda: fixed(safe_clean(shape))):
        try:
            s = cand()
            if not (s.isValid() and len(s.Solids()) == 1):
                continue
            s.exportStep(str(path))
            back = cq.importers.importStep(str(path)).solids().vals()
            if len(back) == 1 and back[0].isValid() and abs(back[0].Volume() - s.Volume()) < 1.0:
                return back[0]
        except Exception:
            continue
    return None


def main():
    global VERBOSE
    member, work = sys.argv[1], Path(sys.argv[2])
    raw_dir, parts = work / "raw", work / "parts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    parts.mkdir(parents=True, exist_ok=True)
    VERBOSE = "-v" in sys.argv
    srcs, names = HALVES[member]
    meshes = [ex.load_3mf_object(*h) for h in srcs]          # original halves, [-v, +v]
    for i, m in enumerate(meshes):
        np.savez(raw_dir / f"{member}-{i}.npz", V=np.asarray(m.vertices, float), F=np.asarray(m.faces))
    print(f"{member}: recording the mesh pipeline", flush=True)
    cap = record(member)
    cap["full"] = trimesh.util.concatenate(meshes)
    cap["halves_mesh"] = meshes
    last = None
    todo = [0, 1]
    for k, env in enumerate(SETTINGS):
        # each half is tried with the next converter settings until it replays and reads back valid
        raw = [None, None]
        for i in todo:
            brep = raw_dir / f"{member}-{i}-{k}.brep"
            r = subprocess.run([sys.executable, str(SRC / "2026-09-28-mesh-to-brep.py"), str(raw_dir / f"{member}-{i}.npz"),
                                str(raw_dir / f"{member}-{i}-{k}.step"), "--brep", str(brep)],
                               capture_output=True, text=True, env={**os.environ, **env})
            if r.returncode != 0:
                raise RuntimeError(r.stderr[-2000:])
            raw[i] = read_brep(brep)
        for i in list(todo):
            one = [raw[j] if j == i else None for j in range(2)]
            try:
                halves, info = replay(member, one, cap)
            except RuntimeError as e:
                print(f"  {names[i]}, converter settings {env or 'default'}: {e}; next settings", flush=True)
                last = e
                continue
            out = export_checked(halves[i], parts / f"{names[i]}.step")
            if out is None:
                last = RuntimeError(f"{names[i]}: STEP does not read back as one valid solid")
                print(f"  {names[i]}, converter settings {env or 'default'}: {last}; next settings", flush=True)
                continue
            todo.remove(i)
            print(f"  {names[i]}: {len(out.Faces())} faces, volume {out.Volume():.1f} mm3 (settings {env or 'default'})",
                  flush=True)
        if not todo:
            return
    raise RuntimeError(f"{member}: no converter settings gave a complete replay: {last}")


if __name__ == "__main__":
    main()
