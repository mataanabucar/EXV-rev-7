"""Watertight CAD-tessellated mesh (STL) -> exact B-rep solid: planes, cylinders, cones, spheres.

Used for the EX-MA parts that only exist as meshes (tower, base, bucket, ears, and the original arm
halves that 2026-09-28-arm-halves-cad.py rebuilds with CAD booleans). The result is one solid whose
faces are real surfaces (a hole is a cylinder with an editable diameter), not triangles.

 1. mesh clean-up: zero-length edges collapsed, knife-thin 'cap' triangles flipped away (the
    surface moves by less than 2 um)
 2. triangles grouped into coplanar facets; strips of facets that fit one cylinder / cone / sphere
    (vertices within 0.02 mm, mesh-edge midpoints within 0.08 mm) grow into one curved region
 3. every region gets its exact surface; region borders are cut into chains at corners and each
    chain becomes a line, arc, circle or spline; between a curved and another surface the chain
    follows the two surfaces' intersection instead of the mesh chords
 4. faces are built on the surfaces (2D curves computed exactly on cylinders / cones / spheres),
    sewn into a shell and closed into a solid; faces that come out wrong are split, then rebuilt
    flat, and the solid is healed and its same-surface faces merged

Command line:  python 2026-09-28-mesh-to-brep.py part.stl|part.npz part.step [--brep part.brep]
               (environment REBREP_REFINE=0 keeps mesh chords as edges instead of surface intersections)
"""
import math
import os
from collections import defaultdict

import numpy as np
import trimesh

import cadquery as cq
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax3, gp_Ax2, gp_Vec
from OCP.Geom import Geom_Plane, Geom_CylindricalSurface, Geom_ConicalSurface, Geom_SphericalSurface, Geom_Circle
from OCP.GC import GC_MakeArcOfCircle
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire,
                                BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid)
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
from OCP.ShapeFix import ShapeFix_Face, ShapeFix_Shell, ShapeFix_Solid, ShapeFix_Shape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SHELL, TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool


# ================================================================= helpers
class UF:
    def __init__(self, n):
        self.p = np.arange(n)

    def find(self, a):
        p = self.p
        r = a
        while p[r] != r:
            r = p[r]
        while p[a] != r:
            p[a], a = r, p[a]
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)

    def labels(self):
        return np.array([self.find(i) for i in range(len(self.p))])


def P(x):
    return gp_Pnt(float(x[0]), float(x[1]), float(x[2]))


def D(x):
    return gp_Dir(float(x[0]), float(x[1]), float(x[2]))


def perp(a):
    a = np.asarray(a, float)
    t = np.eye(3)[np.argmin(np.abs(a))]
    x = np.cross(a, t)
    return x / np.linalg.norm(x)


def circle2d(Q):
    A = np.column_stack((2 * Q[:, 0], 2 * Q[:, 1], np.ones(len(Q))))
    b = (Q ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:2]
    r = math.sqrt(max(sol[2] + c @ c, 1e-18))
    for _ in range(4):
        d = Q - c
        L = np.maximum(np.linalg.norm(d, axis=1), 1e-12)
        J = np.column_stack((-d[:, 0] / L, -d[:, 1] / L, -np.ones(len(Q))))
        st, *_ = np.linalg.lstsq(J, -(L - r), rcond=None)
        c = c + st[:2]; r += st[2]
    return c, r, float(np.abs(np.linalg.norm(Q - c, axis=1) - r).max())


# ================================================================= surface fitting
def _normal_ok(dev, w, tight=2e-3, loose=2e-2):
    """Normal-direction test that tolerates noise from tiny sliver facets: facets carrying 1 % or
    more of the area must pass the tight limit, the rest the loose one."""
    big = w >= 0.01 * w.sum()
    return (np.abs(dev[big]).max(initial=0.0) <= tight) and (np.abs(dev).max(initial=0.0) <= loose)


def fit_cylinder(pts, cen, nrm, w, tol):
    M = (nrm * w[:, None]).T @ nrm
    ev, evec = np.linalg.eigh(M)
    a = evec[:, 0]
    if len(nrm) < 2 or not _normal_ok(nrm @ a, w):
        return None
    X = perp(a); Y = np.cross(a, X)
    Q = np.column_stack((pts @ X, pts @ Y))
    c2, r, res = circle2d(Q)
    if res > tol or r > 5e3:
        return None
    c = c2[0] * X + c2[1] * Y
    # every facet of a tessellated cylinder faces straight away from (or toward) the axis
    rad = (cen - c) - ((cen - c) @ a)[:, None] * a
    rad /= np.maximum(np.linalg.norm(rad, axis=1), 1e-12)[:, None]
    if not _normal_ok(np.abs((rad * nrm).sum(1)) - 1, w, 5e-4, 1e-2):
        return None
    return ("cylinder", dict(axis=a, c=c, r=r), res)


def _axis_point(cen, nrm, a):
    X = perp(a); Y = np.cross(a, X)
    A, b = [], []
    for p, n in zip(cen, nrm):
        n2 = np.array([n @ X, n @ Y])
        L = np.linalg.norm(n2)
        if L < 1e-9:
            continue
        n2 /= L
        p2 = np.array([p @ X, p @ Y])
        A.append([-n2[1], n2[0]]); b.append(-n2[1] * p2[0] + n2[0] * p2[1])
    if len(A) < 2:
        return None, X, Y
    c2, *_ = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)
    return c2, X, Y


def fit_cone(pts, cen, nrm, w, tol):
    if len(nrm) < 3:
        return None
    Nc = nrm - np.average(nrm, axis=0, weights=w)
    C = (Nc * w[:, None]).T @ Nc
    ev, evec = np.linalg.eigh(C)
    a = evec[:, 0]
    dots = nrm @ a
    mean = np.average(dots, weights=w)
    # half-angle between 2 and 75 deg: flatter is a plane, steeper is a cylinder
    if not _normal_ok(dots - mean, w) or abs(mean) < math.sin(math.radians(2.0)) or abs(mean) > math.cos(math.radians(15.0)):
        return None
    c2, X, Y = _axis_point(cen, nrm, a)
    if c2 is None:
        return None
    rho = np.hypot(pts @ X - c2[0], pts @ Y - c2[1])
    t = pts @ a
    k, r0 = np.polyfit(t, rho, 1)
    res = float(np.abs(rho - (k * t + r0)).max() / math.sqrt(1 + k * k))
    if res > tol or not (math.radians(2.0) < abs(math.atan(k)) < math.radians(75.0)):
        return None
    c = c2[0] * X + c2[1] * Y
    # facet normals must match the cone's normal at the facet centre
    d = cen - c
    rad = d - (d @ a)[:, None] * a
    rad /= np.maximum(np.linalg.norm(rad, axis=1), 1e-12)[:, None]
    nm = rad - k * a[None, :]
    nm /= np.linalg.norm(nm, axis=1)[:, None]
    if not _normal_ok(np.abs((nm * nrm).sum(1)) - 1, w, 5e-4, 1e-2):
        return None
    return ("cone", dict(axis=a, c=c, k=k, r0=r0), res)


def fit_sphere(pts, cen, nrm, w, tol):
    if len(pts) < 8:
        return None
    A = np.column_stack((2 * pts, np.ones(len(pts))))
    b = (pts ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    r = math.sqrt(max(sol[3] + c @ c, 1e-18))
    res = float(np.abs(np.linalg.norm(pts - c, axis=1) - r).max())
    if res > tol or r > 1e3:
        return None
    rad = (cen - c) / np.linalg.norm(cen - c, axis=1)[:, None]
    if not _normal_ok(np.abs((rad * nrm).sum(1)) - 1, w, 5e-3, 2e-2):
        return None
    return ("sphere", dict(c=c, r=r), res)


FITTERS = dict(cylinder=fit_cylinder, cone=fit_cone, sphere=fit_sphere)


# ================================================================= segmentation
def segment(mesh, plane_ang=1e-4, curve_ang_deg=30.0, tol=0.02, rel_tol=2e-4, min_facets=3, min_curved_area=0.3,
            plane_dist=2e-4, mid_tol=None):
    F = mesh.faces
    Vt = mesh.vertices
    adj = mesh.face_adjacency
    uf = UF(len(F))
    # planar facets: grown from the largest triangles, accepting a neighbour when all its vertices lie
    # within plane_dist of the seed plane (float32 noise tilts tiny triangles by more than plane_ang)
    fadj_ = defaultdict(list)
    for a, b in adj:
        fadj_[a].append(b); fadj_[b].append(a)
    fn_ = np.nan_to_num(mesh.face_normals)
    assigned = np.zeros(len(F), bool)
    for seed in np.argsort(-mesh.area_faces):
        if assigned[seed]:
            continue
        n0 = fn_[seed]
        if np.linalg.norm(n0) < 0.5:
            continue
        d0 = n0 @ Vt[F[seed][0]]
        assigned[seed] = True
        stack = [seed]
        while stack:
            f = stack.pop()
            for g in fadj_[f]:
                if assigned[g]:
                    continue
                dist = np.abs(Vt[F[g]] @ n0 - d0).max()
                if dist > plane_dist:
                    continue
                # a big neighbour must also face the same way (a sliver may lie edge-on)
                if mesh.area_faces[g] > 1e-3 and fn_[g] @ n0 < 1 - 1e-6:
                    continue
                assigned[g] = True
                uf.union(seed, g)
                stack.append(g)
    # slivers (height under 2 um: collinear or knife-thin triangles from mesh booleans) carry no
    # surface of their own: attach each to the neighbour across its longest edge
    tri = mesh.triangles
    elen = np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2)       # edge k = (v[k-1], v[k])
    Lmax = elen.max(axis=1)
    alt = 2 * mesh.area_faces / np.maximum(Lmax, 1e-12)
    deg = (mesh.area_faces < 1e-9) | (alt < 2e-3)
    if deg.any():
        good_nb = {}
        emap = {}
        for f, (a, b, c) in enumerate(F):
            for e in ((a, b), (b, c), (c, a)):
                emap.setdefault((min(e), max(e)), []).append(f)
        for f in np.nonzero(deg)[0]:
            a, b, c = F[f]
            k = int(np.argmax(elen[f]))                                  # longest edge (v[k-1], v[k])
            vv = [a, b, c]
            e = (vv[k - 1], vv[k])
            for g in emap.get((min(e), max(e)), []):
                if g != f and not deg[g]:
                    good_nb[f] = g
                    break
        for a, b in adj:
            if deg[a] and a not in good_nb and not deg[b]:
                good_nb[a] = b
            if deg[b] and b not in good_nb and not deg[a]:
                good_nb[b] = a
        for f in np.nonzero(deg)[0]:
            if f in good_nb:
                uf.union(f, good_nb[f])
        # slivers only touching slivers: chain them to any attached neighbour
        for _ in range(3):
            for a, b in adj:
                if deg[a] and a not in good_nb and (b in good_nb or not deg[b]):
                    uf.union(a, b); good_nb[a] = b
                if deg[b] and b not in good_nb and (a in good_nb or not deg[a]):
                    uf.union(a, b); good_nb[b] = a
    lab = uf.labels()
    ids, facet_of = np.unique(lab, return_inverse=True)
    nf = len(ids)
    area = np.bincount(facet_of, weights=mesh.area_faces, minlength=nf)
    fn = np.nan_to_num(mesh.face_normals)
    nrm = np.zeros((nf, 3))
    np.add.at(nrm, facet_of, fn * mesh.area_faces[:, None])
    L = np.linalg.norm(nrm, axis=1)
    nrm = np.where(L[:, None] > 0, nrm / np.maximum(L, 1e-300)[:, None], np.array([0.0, 0.0, 1.0]))
    cen = np.zeros((nf, 3))
    np.add.at(cen, facet_of, mesh.triangles_center * mesh.area_faces[:, None])
    cnt = np.bincount(facet_of, minlength=nf)
    ctr = np.zeros((nf, 3))
    np.add.at(ctr, facet_of, mesh.triangles_center)
    cen = np.where(area[:, None] > 0, cen / np.maximum(area, 1e-300)[:, None], ctr / cnt[:, None])
    fverts = defaultdict(set)
    for f, fc in enumerate(facet_of):
        fverts[fc].update(F[f])
    # facet adjacency with dihedral angles
    fa = facet_of[adj]
    m = fa[:, 0] != fa[:, 1]
    nbr = defaultdict(dict)
    for (x, y) in fa[m]:
        a_ = math.degrees(math.acos(np.clip(nrm[x] @ nrm[y], -1, 1)))
        nbr[x][y] = a_
        nbr[y][x] = a_
    if mid_tol is None:
        mid_tol = MID_TOL
    region = -np.ones(nf, int)
    kinds = []
    order = np.argsort(area)
    # mesh edges of each facet: a fitted surface must also pass near their midpoints (a coarse
    # polygon with its vertices on a circle is not that cylinder)
    fed = defaultdict(set)
    for f, fc in enumerate(facet_of):
        a_, b_, c_ = F[f]
        for u_, v_ in ((a_, b_), (b_, c_), (c_, a_)):
            fed[fc].add((min(u_, v_), max(u_, v_)))

    def mid_ok(model, trial):
        E = np.array(sorted(set().union(*[fed[x] for x in trial])))
        if not len(E):
            return True
        mid = (Vt[E[:, 0]] + Vt[E[:, 1]]) / 2
        return float(np.abs(surf_dist(model[0], model[1], mid)[0]).max()) <= mid_tol

    def grow(seed, kind):
        fit = FITTERS[kind]
        members = [seed]
        mset = {seed}
        pts = set(fverts[seed])
        frontier = [y for y, a_ in nbr[seed].items() if a_ <= curve_ang_deg and region[y] < 0]
        model, rejected = None, set()
        kmin = dict(cylinder=2, cone=3, sphere=4)[kind]
        while frontier:
            # smallest dihedral first keeps the growth on one surface
            frontier.sort(key=lambda z: -min(nbr[z].get(m_, 999.0) for m_ in mset if m_ in nbr[z]) if any(m_ in nbr[z] for m_ in mset) else 0.0)
            y = frontier.pop()
            if y in mset or region[y] >= 0 or y in rejected:
                continue
            trial = members + [y]
            P3 = Vt[np.array(sorted(pts | fverts[y]))]
            scale = np.ptp(P3, axis=0).max()
            if len(trial) < kmin:
                mdl = ("pending",)
            else:
                mdl = fit(P3, cen[trial], nrm[trial], area[trial], max(tol, rel_tol * scale))
                if mdl is not None and not mid_ok(mdl, trial):
                    mdl = None
            if mdl is None:
                if len(trial) == kmin:
                    return None
                rejected.add(y)
                continue
            members = trial; mset.add(y)
            pts |= fverts[y]
            model = mdl
            for z, a_ in nbr[y].items():
                if a_ <= curve_ang_deg and region[z] < 0 and z not in mset and z not in rejected:
                    frontier.append(z)
        if model is None or model[0] == "pending":
            return None
        span = math.degrees(math.acos(np.clip(np.min(nrm[members] @ nrm[members].T), -1, 1)))
        need = dict(cylinder=(3, 8.0), cone=(4, 8.0), sphere=(6, 15.0))[kind]
        if len(members) < need[0] or span < need[1] or area[members].sum() < min_curved_area * (5 if kind == "cone" else 1):
            return None
        if kind == "sphere":
            evs = np.linalg.eigvalsh(nrm[members].T @ nrm[members])
            if evs[1] < 0.02 * evs[2]:
                return None
        return members, model

    for seed in order:
        if region[seed] >= 0:
            continue
        if not any(a_ <= curve_ang_deg and region[y] < 0 for y, a_ in nbr[seed].items()):
            continue
        best = None
        for kind in ("cylinder", "cone", "sphere"):
            g = grow(seed, kind)
            if g is None:
                continue
            cover = area[g[0]].sum()
            # a more complex surface must cover clearly more than a simpler one that fits
            if best is None or cover > best[0] * 1.3:
                best = (cover, g)
        if best is not None:
            members, model = best[1]
            if model[0] == "sphere":
                # a band with vertices only on its rims is also inscribed in a sphere: prefer the
                # cylinder / cone through the same points
                P3 = Vt[np.array(sorted(set().union(*[fverts[x] for x in members])))]
                sc = max(tol, rel_tol * np.ptp(P3, axis=0).max())
                alt = fit_cylinder(P3, cen[members], nrm[members], area[members], sc) or \
                    fit_cone(P3, cen[members], nrm[members], area[members], sc)
                if alt is not None and mid_ok(alt, members):
                    model = alt
            rid = len(kinds)
            kinds.append(model)
            region[members] = rid
    # remaining facets are planes
    for f in range(nf):
        if region[f] < 0:
            rid = len(kinds)
            region[f] = rid
            kinds.append(("plane", dict(n=nrm[f], p=cen[f]), 0.0))
    face_region = region[facet_of]
    # regions that wrap all the way round their axis are split into two halves along mesh rulings,
    # so no face needs a seam; the halves are merged again after sewing
    tc = mesh.triangles_center
    fadj = defaultdict(list)
    for x, y in adj:
        fadj[x].append(y); fadj[y].append(x)

    def components(fs):
        fs = set(fs.tolist())
        comps, seen = [], set()
        for f in fs:
            if f in seen:
                continue
            stack, comp = [f], []
            seen.add(f)
            while stack:
                g = stack.pop(); comp.append(g)
                for h in fadj[g]:
                    if h in fs and h not in seen:
                        seen.add(h); stack.append(h)
            comps.append(comp)
        return sorted(comps, key=len, reverse=True)

    for rid in range(len(kinds)):
        kind, prm, _ = kinds[rid]
        if kind not in ("cylinder", "cone"):
            continue
        fs = np.nonzero(face_region == rid)[0]
        a = prm["axis"]; X = perp(a); Y = np.cross(a, X)
        dv = Vt[np.unique(F[fs])] - prm["c"]
        thv = np.sort(np.arctan2(dv @ Y, dv @ X))
        gaps = np.diff(np.r_[thv, thv[0] + 2 * np.pi])
        if gaps.max() > math.radians(120):
            continue
        g0 = thv[(int(np.argmax(gaps)) + 1) % len(thv)]          # a ruling (vertex angle)
        relv = (thv - g0) % (2 * np.pi)
        cut = relv[int(np.argmin(np.abs(relv - np.pi)))]          # the ruling nearest half a turn on
        d = tc[fs] - prm["c"]
        rel = (np.arctan2(d @ Y, d @ X) - g0) % (2 * np.pi)
        half = fs[rel >= cut]
        rest = fs[rel < cut]
        if len(half) == 0 or len(rest) == 0:
            continue
        # keep each half connected: strays go to the other half
        ch, cr = components(half), components(rest)
        half = set(ch[0]) | set(sum(cr[1:], []))
        half -= set(sum(ch[1:], [])) if len(ch) > 1 else set()
        half = np.array(sorted(half), int)
        new_id = len(kinds)
        kinds.append((kind, prm, 0.0))
        face_region[half] = new_id
    return face_region, kinds


# ================================================================= surfaces
def seam_dir(a, c, pts):
    """Unit vector perpendicular to axis a pointing into the middle of the largest angular gap of
    pts around the axis: the periodic surface's seam (u = 0) goes there, away from the patch."""
    X = perp(a); Y = np.cross(a, X)
    d = pts - c
    th = np.sort(np.arctan2(d @ Y, d @ X))
    if len(th) < 2:
        return X
    gaps = np.diff(np.r_[th, th[0] + 2 * np.pi])
    i = int(np.argmax(gaps))
    mid = th[i] + gaps[i] / 2
    return math.cos(mid) * X + math.sin(mid) * Y


def make_surface(kind, prm, outward_hint, pts=None):
    """Geom surface whose normal matches the solid's outward normal (sampled at outward_hint =
    (point, normal)); periodic surfaces get their seam placed away from the patch points pts."""
    p0, n0 = outward_hint
    if kind == "plane":
        n = prm["n"]
        return Geom_Plane(gp_Ax3(P(prm["p"]), D(n), D(perp(n))))
    if kind == "cylinder":
        a, c, r = prm["axis"], prm["c"], prm["r"]
        radial = (p0 - c) - ((p0 - c) @ a) * a
        xd = seam_dir(a, c, pts) if pts is not None else perp(a)
        ax = gp_Ax3(P(c), D(a), D(xd))
        if radial @ n0 < 0:
            ax.YReverse()
        return Geom_CylindricalSurface(ax, float(r))
    if kind == "cone":
        a, c, k, r0 = prm["axis"], prm["c"], prm["k"], prm["r0"]
        # reference circle at the patch's mean axial position (radius there = r0 + k t)
        t_ref = float(np.mean(pts @ a)) if pts is not None else float(p0 @ a)
        rr = r0 + k * t_ref
        if rr <= 1e-6:
            t_ref = float(p0 @ a)
            rr = max(r0 + k * t_ref, 1e-3)
        ang = math.atan(k)
        origin = c + t_ref * a
        xd = seam_dir(a, c, pts) if pts is not None else perp(a)

        def cone(rev):
            ax = gp_Ax3(P(origin), D(a), D(xd))
            if rev:
                ax.YReverse()
            return Geom_ConicalSurface(ax, float(ang), float(rr))
        s = cone(False)
        u = GeomAPI_ProjectPointOnSurf(P(p0), s)
        if u.NbPoints():
            uu, vv = u.LowerDistanceParameters()
            pn = gp_Pnt(); d1u = gp_Vec(); d1v = gp_Vec()
            s.D1(uu, vv, pn, d1u, d1v)
            nn = d1u.Crossed(d1v)
            if np.array([nn.X(), nn.Y(), nn.Z()]) @ n0 < 0:
                s = cone(True)
        return s
    if kind == "sphere":
        c, r = prm["c"], prm["r"]
        # patch around the equator, seam behind it
        dm = (pts.mean(0) - c) if pts is not None else (p0 - c)
        dm /= np.linalg.norm(dm)
        zax = perp(dm)
        ax = gp_Ax3(P(c), D(zax), D(-dm))
        if (p0 - c) @ n0 < 0:
            ax.YReverse()
        return Geom_SphericalSurface(ax, float(r))
    raise ValueError(kind)


# ================================================================= edges
def edge_geometry(pts, closed, tol=2e-3):
    """Chain points -> ('line', a, b) | ('arc', a, m, b) | ('circle', c, n, r) | ('bspline', pts)."""
    pts = np.asarray(pts, float)
    if not closed:
        a, b = pts[0], pts[-1]
        d = b - a
        L = np.linalg.norm(d)
        if len(pts) == 2 or (L > 1e-9 and np.abs(np.linalg.norm(np.cross(pts - a, d / L), axis=1)).max() < tol):
            return ("line", a, b)
    # planar circle?
    if len(pts) >= 3:
        c0 = pts.mean(0)
        _, s, vt = np.linalg.svd(pts - c0)
        n = vt[2]
        if np.abs((pts - c0) @ n).max() < tol:
            X = vt[0]; Y = vt[1]
            Q = np.column_stack(((pts - c0) @ X, (pts - c0) @ Y))
            c2, r, res = circle2d(Q)
            if res < tol and r < 1e4:
                c = c0 + c2[0] * X + c2[1] * Y
                if closed:
                    # orient the axis so the circle runs the same way as the chain
                    t0 = np.cross(n, pts[0] - c)
                    if t0 @ (pts[1] - pts[0]) < 0:
                        n = -n
                    return ("circle", c, n, r, pts[0])
                # mid point on the arc between the ends, on the side of the chain
                m = pts[len(pts) // 2]
                return ("arc", pts[0], m, pts[-1], c, r)
    return ("bspline", pts)


def surf_dist(kind, prm, X):
    """Signed distance of points X (n, 3) to a fitted surface and its gradient (unit normal)."""
    X = np.atleast_2d(X)
    if kind == "plane":
        n = prm["n"]
        return (X - prm["p"]) @ n, np.tile(n, (len(X), 1))
    if kind == "sphere":
        d = X - prm["c"]
        L = np.maximum(np.linalg.norm(d, axis=1), 1e-12)
        return L - prm["r"], d / L[:, None]
    a, c = prm["axis"], prm["c"]
    d = X - c
    rad = d - (d @ a)[:, None] * a
    rho = np.maximum(np.linalg.norm(rad, axis=1), 1e-12)
    u = rad / rho[:, None]
    if kind == "cylinder":
        return rho - prm["r"], u
    k, r0 = prm["k"], prm["r0"]
    s = math.sqrt(1 + k * k)
    return (rho - (k * (X @ a) + r0)) / s, (u - k * a[None, :]) / s


def on_both(ka, kb, X, iters=12):
    """Newton projection of points X onto the intersection curve of surfaces ka and kb (the
    nearest point on both). Returns (points, ok mask)."""
    Y = np.array(X, float)
    ok = np.ones(len(Y), bool)
    for _ in range(iters):
        fa, ga = surf_dist(ka[0], ka[1], Y)
        fb, gb = surf_dist(kb[0], kb[1], Y)
        # min-norm step solving ga.d = -fa, gb.d = -fb
        g11 = (ga * ga).sum(1); g22 = (gb * gb).sum(1); g12 = (ga * gb).sum(1)
        det = g11 * g22 - g12 * g12
        ok &= det > math.sin(math.radians(4.0)) ** 2
        det = np.where(ok, det, 1.0)
        l1 = (-fa * g22 + fb * g12) / det
        l2 = (-fb * g11 + fa * g12) / det
        Y = Y + np.where(ok[:, None], l1[:, None] * ga + l2[:, None] * gb, 0.0)
    fa, _ = surf_dist(ka[0], ka[1], Y)
    fb, _ = surf_dist(kb[0], kb[1], Y)
    ok &= (np.abs(fa) < 1e-6) & (np.abs(fb) < 1e-6)
    return Y, ok


def refine_chain(pts, ka, kb, dev_tol=2e-3):
    """A chain of mesh vertices along the border of two fitted surfaces, at least one curved: the
    mesh edges are chords of the true edge (the surfaces' intersection). Returns points on that
    intersection between the chain vertices (vertices kept), or None when the chords already lie
    on both surfaces or the intersection cannot be found."""
    if ka[0] == "plane" and kb[0] == "plane":
        return None
    pts = np.asarray(pts, float)
    A, B = pts[:-1], pts[1:]
    L = np.linalg.norm(B - A, axis=1)
    mid = (A + B) / 2
    dev = np.maximum(np.abs(surf_dist(ka[0], ka[1], mid)[0]), np.abs(surf_dist(kb[0], kb[1], mid)[0]))
    if dev.max() <= dev_tol:
        return None
    out = [pts[0]]
    segs = []
    for i in range(len(A)):
        n_in = 1 if dev[i] <= dev_tol else int(min(9, max(3, L[i] // 1.5)))
        s = np.linspace(0, 1, n_in + 2)[1:-1]
        Q = A[i] + s[:, None] * (B[i] - A[i])
        if dev[i] > dev_tol:
            Y, ok = on_both(ka, kb, Q)
            move = np.linalg.norm(Y - Q, axis=1)
            if not ok.all() or move.max() > 1.5 * dev[i] + 0.03:
                return None
            Q = Y
        seg = [A[i]] + list(Q) + [B[i]]
        segs.append(np.array(seg))
        out += list(Q) + [B[i]]
    return np.array(out), segs


def _interp(pts):
    from OCP.GeomAPI import GeomAPI_Interpolate
    from OCP.TColgp import TColgp_HArray1OfPnt
    arr = TColgp_HArray1OfPnt(1, len(pts))
    for i, p in enumerate(pts):
        arr.SetValue(i + 1, P(p))
    it = GeomAPI_Interpolate(arr, False, 1e-7)
    it.Perform()
    return it.Curve() if it.IsDone() else None


def build_edge(geo, v0, v1, closed):
    try:
        if geo[0] == "line":
            if v0.IsSame(v1):
                return None
            mk = BRepBuilderAPI_MakeEdge(v0, v1)
            return mk.Edge() if mk.IsDone() else None
        if geo[0] == "arc":
            arc = GC_MakeArcOfCircle(P(geo[1]), P(geo[2]), P(geo[3]))
            if arc.IsDone():
                mk = BRepBuilderAPI_MakeEdge(arc.Value(), v0, v1)
                if mk.IsDone():
                    return mk.Edge()
            return None
        if geo[0] == "circle":
            c, n, r, p0 = geo[1], geo[2], geo[3], geo[4]
            xd = p0 - c
            xd = xd - (xd @ n) * n
            xd /= np.linalg.norm(xd)
            circ = Geom_Circle(gp_Ax2(P(c), D(n), D(xd)), float(r))
            mk = BRepBuilderAPI_MakeEdge(circ)          # own exact seam vertex (not a corner)
            return mk.Edge() if mk.IsDone() else None
        pts = np.asarray(geo[1])
        keep = np.r_[True, np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-7]
        pts = pts[keep]
        if len(pts) < 2:
            return None
        if len(pts) == 2:
            mk = BRepBuilderAPI_MakeEdge(v0, v1)
            return mk.Edge() if mk.IsDone() else None
        cv = _interp(pts)
        if cv is None:
            return None
        mk = BRepBuilderAPI_MakeEdge(cv, v0, v1)
        return mk.Edge() if mk.IsDone() else None
    except Exception:
        return None


def build_edge_any(pts, v0, v1, closed):
    """Try the fitted geometry, then a spline through the chain, then a straight line."""
    geo = edge_geometry(pts, closed)
    e = build_edge(geo, v0, v1, closed)
    if e is None and not closed:
        e = build_edge(("bspline", pts), v0, v1, False)
        if e is None:
            e = build_edge(("line", pts[0], pts[-1]), v0, v1, False)
        geo = ("fallback",)
    return e, geo[0]


# ================================================================= main
def face_area(face):
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    g = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, g)
    return g.Mass()


def flip_wires(face):
    """Same surface and boundary, every wire reversed (undoes a wrong orientation fix)."""
    from OCP.TopAbs import TopAbs_WIRE
    surf = BRep_Tool.Surface_s(face)
    ws = []
    ex_ = TopExp_Explorer(face, TopAbs_WIRE)
    while ex_.More():
        ws.append(TopoDS.Wire_s(ex_.Current().Reversed()))
        ex_.Next()
    mf = BRepBuilderAPI_MakeFace(surf, ws[0], False)
    for w in ws[1:]:
        mf.Add(w)
    return mf.Face() if mf.IsDone() else face


DEBUG = []
TRACE = None
FACEINFO = []


def clean_slivers(mesh, h_tol=2e-3, e_tol=2e-3, rounds=6):
    """Remove knife-thin triangles left by mesh booleans without moving the surface by more than
    h_tol: edges shorter than e_tol are collapsed, and a 'cap' (apex on its long edge) has that
    edge flipped. Returns a new watertight mesh, or the input when a step would break it."""
    V = np.asarray(mesh.vertices, float).copy()
    F = np.asarray(mesh.faces, int).copy()
    for _ in range(rounds):
        changed = False
        # --- needles: collapse short edges (keep the endpoint with the lower index)
        E = np.vstack((F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]))
        L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
        short = E[L < e_tol]
        if len(short):
            uf = UF(len(V))
            for a, b in short:
                uf.union(int(a), int(b))
            rep_ = np.array([uf.find(i) for i in range(len(V))])
            F2 = rep_[F]
            keep = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 2] != F2[:, 0])
            F2 = F2[keep]
            # opposite duplicate faces (a collapsed fold) cancel
            key = np.sort(F2, axis=1)
            _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
            F2 = F2[cnt[inv.ravel()] == 1]
            t = trimesh.Trimesh(V, F2, process=False)
            if t.is_watertight and t.is_winding_consistent and abs(t.volume - mesh.volume) < 1e-3 * abs(mesh.volume) + 0.05:
                F = F2
                changed = True
        # --- caps: flip the long edge under a flat apex
        he = {}
        for f, (a, b, c) in enumerate(F):
            he[(a, b)] = f; he[(b, c)] = f; he[(c, a)] = f
        edges = set((min(u, v), max(u, v)) for (u, v) in he)
        tri = V[F]
        el = np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2)        # edge k = (v[k-1], v[k])
        area2 = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        alt = area2 / np.maximum(el.max(1), 1e-12)
        dead = set()
        for f in np.nonzero(alt < h_tol)[0]:
            if f in dead:
                continue
            vv = list(F[f])
            k = int(np.argmax(el[f]))
            A, B = vv[k - 1], vv[k]
            Vx = vv[(k + 1) % 3]
            g = he.get((B, A))
            if g is None or g in dead:
                continue
            W = [x for x in F[g] if x not in (A, B)][0]
            if (min(Vx, W), max(Vx, W)) in edges or Vx == W:
                continue
            # apex must project inside the long edge
            d = V[B] - V[A]
            s = (V[Vx] - V[A]) @ d / max(d @ d, 1e-24)
            if not (0.0 < s < 1.0):
                continue
            n1 = np.cross(V[W] - V[A], V[Vx] - V[A])
            n2 = np.cross(V[B] - V[W], V[Vx] - V[W])
            if np.linalg.norm(n1) < 1e-12 or np.linalg.norm(n2) < 1e-12 or n1 @ n2 <= 0:
                continue
            F[f] = [A, W, Vx]
            F[g] = [W, B, Vx]
            for (u, v) in ((A, B), (B, Vx), (Vx, A), (B, A), (A, W), (W, B)):
                he.pop((u, v), None)
            for ff in (f, g):
                a, b, c = F[ff]
                he[(a, b)] = ff; he[(b, c)] = ff; he[(c, a)] = ff
            edges.discard((min(A, B), max(A, B)))
            edges.add((min(Vx, W), max(Vx, W)))
            dead.update((f, g))
            changed = True
        if not changed:
            break
    used = np.unique(F)
    remap = -np.ones(len(V), int)
    remap[used] = np.arange(len(used))
    t = trimesh.Trimesh(V[used], remap[F], process=False)
    if not (t.is_watertight and t.is_winding_consistent):
        return mesh
    return t


def rebrep(mesh, tol=0.02, rel_tol=2e-4, curve_ang_deg=30.0, sew_tol=1e-3, verbose=False, unify=True):
    mesh = mesh.copy()
    mesh.merge_vertices()
    try:
        # collapse near-zero edges (< 0.1 um of shape change) left by mesh booleans
        import manifold3d as mf
        man = mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                                  tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))
        if man.status() == mf.Error.NoError:
            sm = man.simplify(SIMPLIFY_TOL).to_mesh()
            m2 = trimesh.Trimesh(np.asarray(sm.vert_properties)[:, :3], np.asarray(sm.tri_verts), process=False)
            m2.merge_vertices()
            if m2.is_watertight and abs(m2.volume - mesh.volume) < 1e-4 * abs(mesh.volume) + 0.1:
                mesh = m2
    except Exception:
        pass
    if not mesh.is_winding_consistent:
        trimesh.repair.fix_winding(mesh)
    if mesh.volume < 0:
        mesh.invert()
    if CLEAN_SLIVERS:
        mesh = clean_slivers(mesh)
    face_region, kinds = segment(mesh, tol=tol, rel_tol=rel_tol, curve_ang_deg=curve_ang_deg)
    demoted = 0
    for attempt in range(6):
        FACEINFO.clear()
        shp, rep, bad = _build(mesh, face_region, kinds, sew_tol)
        rep["attempt"] = attempt
        # done when no face is wrong: a solid can pass the checker with a face whose boundary
        # encloses the wrong area, and booleans on it fail later
        if not bad and rep["free_edges"] == 0:
            break
        n_split = 0
        if attempt < 2:
            # split failing curved faces into narrower angular sectors
            for r_ in sorted(bad):
                n_split += split_sectors(mesh, face_region, kinds, r_, math.radians(90.0 / (attempt + 1)))
        if n_split == 0:
            # last resort: rebuild the failing patches from their flat facets / triangles
            for r_ in sorted(bad):
                demoted += demote(mesh, face_region, kinds, r_)
    rep["bad_faces"] = len(bad)
    rep["demoted_faces"] = demoted
    if not rep["valid"] and rep["free_edges"] == 0:
        shp2 = heal(shp)
        if shp2 is not None:
            shp = shp2
            rep["valid"] = True
            rep["healed"] = True
    if unify and rep["valid"] and rep["free_edges"] == 0:
        # merge faces that lie on one surface (split halves of holes, coplanar neighbours)
        try:
            from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
            u = ShapeUpgrade_UnifySameDomain(shp.wrapped, True, True, False)
            u.SetLinearTolerance(1e-4)
            u.SetAngularTolerance(1e-4)
            u.Build()
            uni = cq.Shape.cast(u.Shape())
            if uni.isValid():
                shp = uni
                rep["unified"] = True
        except Exception:
            pass
    return shp, rep


def demote(mesh, face_region, kinds, rid):
    """Replace one region by planar faces: its coplanar facets (curved) or its triangles (plane)."""
    fs = np.nonzero(face_region == rid)[0]
    if len(fs) <= 1:
        return 0
    kind = kinds[rid][0]
    groups = []
    if kind != "plane":
        sub_adj = [(a, b) for (a, b), t in zip(mesh.face_adjacency, mesh.face_adjacency_angles)
                   if t < 1e-4 and face_region[a] == rid and face_region[b] == rid]
        uf = UF(len(mesh.faces))
        for a, b in sub_adj:
            uf.union(a, b)
        lab = defaultdict(list)
        for f in fs:
            lab[uf.find(f)].append(f)
        groups = list(lab.values())
    else:
        groups = [[f] for f in fs]
    first = True
    for g in groups:
        n = mesh.face_normals[g[0]]
        p = mesh.triangles_center[g[0]]
        model = ("plane", dict(n=n, p=p), 0.0)
        if first:
            kinds[rid] = model
            face_region[g] = rid
            first = False
        else:
            face_region[g] = len(kinds)
            kinds.append(model)
    return len(groups)


USE_SHAPEFIX_FACE = False
REFINE = os.environ.get("REBREP_REFINE", "1") == "1"
SIMPLIFY_TOL = float(os.environ.get("REBREP_SIMPLIFY", "1e-4"))
CLEAN_SLIVERS = os.environ.get("REBREP_CLEAN", "1") == "1"
MID_TOL = float(os.environ.get("REBREP_MID_TOL", "0.08"))   # "inf" turns the chord check off


PCSTATS = defaultdict(int)


def pcurve_dev(c2, surf, ad, f0, f1, n=25):
    worst = 0.0
    for t in np.linspace(f0, f1, n):
        uv = c2.Value(float(t))
        worst = max(worst, surf.Value(uv.X(), uv.Y()).Distance(ad.Value(float(t))))
    return worst


def analytic_pcurve(e, surf, n=25, u_ref=None):
    """2D curve of edge e on an elementary surface, interpolated through the exact (u, v) of
    points sampled along the 3D curve, with the 3D curve's parameters (same-parameter)."""
    from OCP.Geom2dAPI import Geom2dAPI_Interpolate
    from OCP.TColgp import TColgp_HArray1OfPnt2d
    from OCP.TColStd import TColStd_HArray1OfReal
    from OCP.gp import gp_Pnt2d
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    ad = BRepAdaptor_Curve(e)
    f0, f1 = ad.FirstParameter(), ad.LastParameter()
    ts = np.linspace(f0, f1, n)
    X = np.array([[p.X(), p.Y(), p.Z()] for p in (ad.Value(t) for t in ts)])
    s = surf
    kind = None
    # cones only: near the apex the approximate projection can go the wrong way round; on cylinders
    # and spheres it is reliable
    for cls, k in ((Geom_ConicalSurface, "cone"),):
        try:
            h = cls.DownCast(s) if hasattr(cls, "DownCast") else None
        except Exception:
            h = None
        if h is None and isinstance(s, cls):
            h = s
        if h is not None:
            s, kind = h, k
            break
    if kind is None:
        return None
    ax = s.Position()
    o = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
    xd = np.array([ax.XDirection().X(), ax.XDirection().Y(), ax.XDirection().Z()])
    yd = np.array([ax.YDirection().X(), ax.YDirection().Y(), ax.YDirection().Z()])
    zd = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
    d = X - o
    x, y, z = d @ xd, d @ yd, d @ zd
    u = np.unwrap(np.arctan2(y, x))
    if kind == "cyl":
        v = z
    elif kind == "cone":
        v = z / math.cos(s.SemiAngle())
    else:
        v = np.arcsin(np.clip(z / s.Radius(), -1, 1))
    if u_ref is None:
        u = u - 2 * math.pi * math.floor(u.mean() / (2 * math.pi))
    else:
        # same turn of the angle as the reference (the projected curve's start)
        u = u - 2 * math.pi * round((u[0] - u_ref) / (2 * math.pi))
    pts = TColgp_HArray1OfPnt2d(1, n)
    prm = TColStd_HArray1OfReal(1, n)
    for i in range(n):
        pts.SetValue(i + 1, gp_Pnt2d(float(u[i]), float(v[i])))
        prm.SetValue(i + 1, float(ts[i]))
    it = Geom2dAPI_Interpolate(pts, prm, False, 1e-9)
    it.Perform()
    if not it.IsDone():
        return None
    c2 = it.Curve()
    # accept only when the 2D curve maps back onto the 3D curve
    worst = 0.0
    for t in np.linspace(f0, f1, 2 * n + 1):
        uv = c2.Value(float(t))
        q = s.Value(uv.X(), uv.Y())
        p = ad.Value(float(t))
        worst = max(worst, q.Distance(p))
    return c2, worst


def curved_face(surf, wires, tol=1e-4):
    """Face on a curved surface from its wires, with each edge's 2D curve projected directly
    (no ShapeFix: its projection crashes on some small patches)."""
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Face
    from OCP.GeomProjLib import GeomProjLib
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepLib import BRepLib
    bb = BRep_Builder()
    face = TopoDS_Face()
    bb.MakeFace(face, surf, 1e-7)
    for w in wires:
        bb.Add(face, w)
    ex_ = TopExp_Explorer(face, TopAbs_EDGE)
    while ex_.More():
        e = TopoDS.Edge_s(ex_.Current())
        ex_.Next()
        try:
            c3 = BRep_Tool.Curve_s(e, 0.0, 0.0)
            ad = BRepAdaptor_Curve(e)
            f0, f1 = ad.FirstParameter(), ad.LastParameter()
            c2 = GeomProjLib.Curve2d_s(c3, f0, f1, surf)
            dev = pcurve_dev(c2, surf, ad, f0, f1) if c2 is not None else 1e9
            if dev > 1e-3:
                an = analytic_pcurve(e, surf, u_ref=c2.Value(f0).X() if c2 is not None else None)
                if an is not None and an[1] < dev:
                    c2 = an[0]
                    PCSTATS["analytic"] += 1
            if c2 is None:
                return None
            bb.UpdateEdge(e, c2, face, tol)
        except Exception:
            return None
    try:
        BRepLib.SameParameter_s(face, tol)
    except Exception:
        pass
    return face


def heal(shp):
    """Tolerance / pcurve repair; falls back to a STEP write-read round trip (the reader heals)."""
    try:
        fx = ShapeFix_Shape(shp.wrapped)
        fx.Perform()
        s2 = cq.Shape.cast(fx.Shape())
        if s2.isValid() and len(s2.Solids()) == 1:
            return s2.Solids()[0]
    except Exception:
        pass
    try:
        import os
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".step")
        os.close(fd)
        shp.exportStep(path)
        s3 = cq.importers.importStep(path).val()
        os.remove(path)
        if s3.isValid() and len(s3.Solids()) == 1:
            return s3.Solids()[0]
    except Exception:
        pass
    return None


def split_sectors(mesh, face_region, kinds, rid, max_ang):
    """Split a cylinder / cone region into angular sectors no wider than max_ang."""
    kind, prm, _ = kinds[rid]
    if kind not in ("cylinder", "cone"):
        return 0
    fs = np.nonzero(face_region == rid)[0]
    a = prm["axis"]; X = perp(a); Y = np.cross(a, X)
    d = mesh.triangles_center[fs] - prm["c"]
    th = np.arctan2(d @ Y, d @ X)
    ths = np.sort(th)
    gaps = np.diff(np.r_[ths, ths[0] + 2 * np.pi])
    g0 = ths[(int(np.argmax(gaps)) + 1) % len(ths)] - 1e-9
    rel = (th - g0) % (2 * np.pi)
    span = rel.max()
    n = max(2, int(math.ceil(span / max_ang)))
    bins = np.minimum((rel / (span / n + 1e-12)).astype(int), n - 1)
    made = 0
    for k in range(1, n):
        sel = fs[bins == k]
        if len(sel) == 0:
            continue
        face_region[sel] = len(kinds)
        kinds.append((kind, prm, 0.0))
        made += 1
    return made


def _build(mesh, face_region, kinds, sew_tol):
    F = mesh.faces
    Vt = mesh.vertices
    nreg = len(kinds)
    # half-edge map: directed edge (u, v) -> face
    he = {}
    for f, (a, b, c) in enumerate(F):
        he[(a, b)] = f; he[(b, c)] = f; he[(c, a)] = f
    # vertex -> regions, boundary degree
    vreg = defaultdict(set)
    for f, (a, b, c) in enumerate(F):
        r = face_region[f]
        vreg[a].add(r); vreg[b].add(r); vreg[c].add(r)
    bdeg = defaultdict(int)
    for (u, v), f in he.items():
        if u < v:
            g = he.get((v, u))
            if g is not None and face_region[f] != face_region[g]:
                bdeg[u] += 1; bdeg[v] += 1
    corner = {v for v in bdeg if len(vreg[v]) >= 3 or bdeg[v] != 2}

    def is_bnd(u, v):
        f = he[(u, v)]
        g = he.get((v, u))
        return g is None or face_region[f] != face_region[g]

    def next_bnd(u, v):
        """Next boundary half-edge after (u -> v) within v's fan of the same region."""
        f = he[(u, v)]
        for _guard in range(10000):
            a, b, c = F[f]
            nxt = {(a, b): (b, c), (b, c): (c, a), (c, a): (a, b)}[(u, v)]
            if is_bnd(*nxt):
                return nxt
            # cross to the twin face and continue around v
            x, y = nxt
            f = he[(y, x)]
            u, v = y, x          # now traversing (y -> x) in face f, i.e. arriving at x == v
            # we need the edge in face f that ENDS at v: (y, x) ends at x == v
    # region boundary loops
    loops = defaultdict(list)
    used = set()
    for (u, v), f in he.items():
        if (u, v) in used or not is_bnd(u, v):
            continue
        r = face_region[f]
        loop = [u]
        e = (u, v)
        guard = 0
        ok = True
        while True:
            used.add(e)
            loop.append(e[1])
            e = next_bnd(*e)
            guard += 1
            if e is None or (e != (u, v) and e in used) or guard > 10 ** 6:
                ok = False
                DEBUG.append(("loop", int(r)))
                break
            if e == (u, v):
                break
        if ok:
            loops[r].append(loop[:-1])    # vertex cycle (first vertex not repeated)
    # pre-pass: loops with fewer than two corners get extra corners so every chain has two distinct
    # ends (a full circle keeps no corner: it becomes one closed circular edge)
    for r, lps in loops.items():
        for lp in lps:
            cs = [i for i, v in enumerate(lp) if v in corner]
            if len(cs) >= 2:
                continue
            if not cs:
                k = int(np.argmin(lp))
                seq = lp[k:] + lp[:k]
                if len(seq) >= 4 and edge_geometry(Vt[seq + [seq[0]]], True)[0] == "circle":
                    continue
                corner.add(seq[0]); corner.add(seq[len(seq) // 2])
            else:
                i = cs[0]
                corner.add(lp[(i + len(lp) // 2) % len(lp)])

    vtx = {}

    def vert(i):
        if i not in vtx:
            vtx[i] = BRepBuilderAPI_MakeVertex(P(Vt[i])).Vertex()
        return vtx[i]

    stats = defaultdict(int)
    failed_edges = 0

    def chain_edges(vids, closed=False, r_a=None, r_b=None):
        """Chain of mesh vertices -> list of edges in chain direction (one exact curve when the
        points define it, else one straight edge per mesh edge). Between two fitted surfaces, at
        least one curved, the curve follows their intersection rather than the mesh chords."""
        nonlocal failed_edges
        pts = Vt[vids + [vids[0]]] if closed else Vt[vids]
        segs = None
        if REFINE and r_a is not None and r_b is not None and r_a != r_b:
            rf = refine_chain(pts, kinds[r_a], kinds[r_b])
            if rf is not None:
                pts, segs = rf
                stats["refined"] += 1
        geo = edge_geometry(pts, closed)
        k = geo[0]
        n_pts = len(pts) - 1 if closed else len(pts)
        e = None
        if closed and k == "circle" and n_pts >= 4:
            e = build_edge(geo, None, None, True)
        elif not closed and k == "line":
            e = build_edge(geo, vert(vids[0]), vert(vids[-1]), False)
        elif not closed and k == "arc" and n_pts >= 4:
            e = build_edge(geo, vert(vids[0]), vert(vids[-1]), False)
        elif not closed and k == "bspline" and n_pts >= 5:
            e = build_edge(geo, vert(vids[0]), vert(vids[-1]), False)
        if e is not None and k in ("arc", "bspline"):
            # the curve must follow the chain: same length within 0.5 %
            L_chain = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
            L_edge = cq.Edge(e).Length()
            if abs(L_edge - L_chain) > 0.005 * L_chain + 0.01:
                e = None
        if e is not None:
            stats[k] += 1
            return [e]
        # polyline fallback: straight edges between consecutive mesh vertices
        seq = vids + [vids[0]] if closed else vids
        out = []
        for i_, (a_, b_) in enumerate(zip(seq[:-1], seq[1:])):
            ee = None
            if segs is not None and len(segs[i_]) > 2:
                ee = build_edge(("bspline", segs[i_]), vert(a_), vert(b_), False)
            if ee is None:
                ee = build_edge(("line",), vert(a_), vert(b_), False)
            if ee is None:
                failed_edges += 1
                DEBUG.append(("seg", a_, b_))
                continue
            out.append(ee)
        stats["polyline"] += 1
        return out

    def other(u, v):
        """Region across the mesh edge (u, v) from the face that owns (u -> v)."""
        g = he.get((v, u))
        return None if g is None else int(face_region[g])

    chains = {}           # (first, second vertex) -> (edges, start, end)
    closed_chains = {}    # frozenset(vertices) -> (edges, seam, seq)
    face_wires = defaultdict(list)
    for r, lps in loops.items():
        for lp in lps:
            cidx = [i for i, v in enumerate(lp) if v in corner]
            wire_edges = []
            if not cidx:
                k = int(np.argmin(lp))
                seq = lp[k:] + lp[:k]
                key = frozenset(seq)
                if key in closed_chains:
                    es, s0, dirseq = closed_chains[key]
                    fwd = (seq[1] == dirseq[1])
                    wire_edges += [(e, True) for e in es] if fwd else [(e, False) for e in reversed(es)]
                else:
                    es = chain_edges(seq, True, r, other(seq[0], seq[1]))
                    closed_chains[key] = (es, seq[0], tuple(seq))
                    wire_edges += [(e, True) for e in es]
                face_wires[r].append(wire_edges)
                continue
            k0 = cidx[0]
            seq = lp[k0:] + lp[:k0] + [lp[k0]]
            idx = [i for i, v in enumerate(seq) if v in corner]
            for i0, i1 in zip(idx[:-1], idx[1:]):
                part = seq[i0:i1 + 1]
                key_f = (part[0], part[1])
                key_r = (part[-1], part[-2])
                if key_r in chains and chains[key_r][2] == part[0]:
                    wire_edges += [(e, False) for e in reversed(chains[key_r][0])]
                    continue
                if key_f in chains:
                    wire_edges += [(e, True) for e in chains[key_f][0]]
                    continue
                es = chain_edges(part, False, r, other(part[0], part[1]))
                chains[key_f] = (es, part[0], part[-1])
                wire_edges += [(e, True) for e in es]
            face_wires[r].append(wire_edges)
    # faces
    faces = []
    failed_faces = []
    reg_faces = defaultdict(list)
    for f, r in enumerate(face_region):
        reg_faces[r].append(f)
    for r in range(nreg):
        kind, prm, _ = kinds[r]
        fs = reg_faces[r]
        if not fs:
            continue
        f0 = max(fs, key=lambda f: mesh.area_faces[f])
        hint = (mesh.triangles_center[f0], mesh.face_normals[f0])
        try:
            surf = make_surface(kind, prm, hint, Vt[np.unique(F[fs])])
        except Exception:
            failed_faces.append(r)
            continue
        wires = []
        for we in face_wires.get(r, []):
            mw = BRepBuilderAPI_MakeWire()
            for e, fwd in we:
                mw.Add(e if fwd else TopoDS.Edge_s(e.Reversed()))
            if not mw.IsDone():
                mw = None
            if mw is not None:
                wires.append(mw.Wire())
        if not wires:
            failed_faces.append(r)
            continue
        # outer wire first (planes: largest enclosed area)
        if kind == "plane" and len(wires) > 1:
            def warea(w):
                from OCP.GProp import GProp_GProps
                from OCP.BRepGProp import BRepGProp
                fc = BRepBuilderAPI_MakeFace(Geom_Plane(gp_Ax3(P(prm["p"]), D(prm["n"]), D(perp(prm["n"])))), w, True)
                if not fc.IsDone():
                    return 0.0
                g = GProp_GProps(); BRepGProp.SurfaceProperties_s(fc.Face(), g)
                return abs(g.Mass())
            wires.sort(key=warea, reverse=True)
        if kind != "plane" and not USE_SHAPEFIX_FACE:
            face = curved_face(surf, wires)
            if face is None:
                failed_faces.append(r)
                continue
            if face_area(face) < 0:
                face = curved_face(surf, [TopoDS.Wire_s(w.Reversed()) for w in wires])
                if face is None:
                    failed_faces.append(r)
                    continue
            faces.append((r, face))
            FACEINFO.append((r, kind, face, float(mesh.area_faces[fs].sum()), len(wires)))
            continue
        mf = BRepBuilderAPI_MakeFace(surf, wires[0], True)
        if not mf.IsDone():
            failed_faces.append(r)
            continue
        for w in wires[1:]:
            mf.Add(w)
        face = mf.Face()
        if kind != "plane":
            # pcurves / seams on curved surfaces; planes need none (and the fixer may drop a tiny
            # wire and leave an unbounded plane)
            if TRACE is not None:
                TRACE.write(f"{r} {kind} wires={len(wires)} edges={sum(len(w) for w in face_wires.get(r, []))} "
                            f"mesh_area={float(mesh.area_faces[fs].sum()):.4f} prm={ {k: np.round(v, 4).tolist() if hasattr(v, '__len__') else round(float(v), 4) for k, v in prm.items()} }\n")
                TRACE.flush()
                from OCP.BRepTools import BRepTools
                BRepTools.Write_s(face, "last_face.brep")
                np.save("last_face_pts.npy", mesh.vertices[np.unique(mesh.faces[fs])])
            sf = ShapeFix_Face(face)
            sf.SetPrecision(1e-5)
            sf.SetMaxTolerance(sew_tol)
            sf.Perform()
            fixed = sf.Face()
            ex_e = TopExp_Explorer(fixed, TopAbs_EDGE)
            if ex_e.More() and abs(face_area(fixed)) < 1e6:
                face = fixed
        if face_area(face) < 0:
            face = flip_wires(face)
        faces.append((r, face))
        FACEINFO.append((r, kind, face, float(mesh.area_faces[fs].sum()), len(wires)))
    sew = BRepBuilderAPI_Sewing(sew_tol)
    for _, fc in faces:
        sew.Add(fc)
    sew.Perform()
    sewn = sew.SewedShape()
    exp = TopExp_Explorer(sewn, TopAbs_SHELL)
    mk = BRepBuilderAPI_MakeSolid()
    nsh = 0
    while exp.More():
        sh = TopoDS.Shell_s(exp.Current())
        fx = ShapeFix_Shell(sh); fx.Perform()
        mk.Add(TopoDS.Shell_s(fx.Shell()))
        nsh += 1
        exp.Next()
    solid = mk.Solid()
    fs = ShapeFix_Solid(solid)
    fs.Perform()
    shp = cq.Shape.cast(fs.Solid())
    bad = set(failed_faces)
    for r_, kind_, face_, am_, nw_ in FACEINFO:
        # area mismatch = wrong boundary; tolerance-only defects are left to the final heal
        if abs(face_area(face_) - am_) > 0.02 * am_ + 0.05:
            bad.add(r_)
    if not shp.isValid():
        # curved faces that fail the checker after sewing go the same way (split, then flatten)
        from OCP.BRepCheck import BRepCheck_Analyzer
        for r_, kind_, face_, am_, nw_ in FACEINFO:
            if kind_ == "plane":
                continue
            f2 = sew.Modified(face_) if sew.IsModified(face_) else face_
            if not BRepCheck_Analyzer(f2).IsValid():
                bad.add(r_)
    rep = dict(regions=nreg, kinds=dict(_count([k[0] for k in kinds])), edges=dict(stats), faces_built=len(faces),
               failed_faces=len(failed_faces), failed_edges=failed_edges, shells=nsh,
               free_edges=sew.NbFreeEdges(), valid=bool(shp.isValid()))
    return shp, rep, bad


def _count(xs):
    d = defaultdict(int)
    for x in xs:
        d[x] += 1
    return d


# ================================================================= 2D loop fitting (used by the arm-half CAD replay)
V = cq.Vector


class Frame:
    """Local (a, b, w) -> world = O + a X + b Y + w Z; Z is the extrusion axis."""

    def __init__(self, origin, X, Z):
        Z = np.asarray(Z, float); Z = Z / np.linalg.norm(Z)
        X = np.asarray(X, float); X = X - (X @ Z) * Z; X = X / np.linalg.norm(X)
        self.O, self.X, self.Z = np.asarray(origin, float), X, Z
        self.Y = np.cross(Z, X)

    def to_local(self, P):
        D = np.asarray(P, float) - self.O
        return np.column_stack((D @ self.X, D @ self.Y, D @ self.Z))

    def to_world(self, a, b, w):
        return self.O + a * self.X + b * self.Y + w * self.Z

    def vec(self, a, b, w):
        return V(*map(float, self.to_world(a, b, w)))



def circle_fit(P):
    A = np.column_stack((2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))))
    b = (P ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:2]
    r = math.sqrt(max(sol[2] + c @ c, 1e-12))
    for _ in range(6):
        d = P - c
        L = np.maximum(np.linalg.norm(d, axis=1), 1e-12)
        J = np.column_stack((-d[:, 0] / L, -d[:, 1] / L, -np.ones(len(P))))
        step, *_ = np.linalg.lstsq(J, -(L - r), rcond=None)
        c = c + step[:2]; r = r + step[2]
    res = np.abs(np.linalg.norm(P - c, axis=1) - r)
    return c, float(r), float(res.max())


def simplify_collinear(P, tol):
    P = [np.asarray(p) for p in P]
    changed = True
    while changed and len(P) > 3:
        changed = False
        i = 0
        while i < len(P) and len(P) > 3:
            a, b, c = P[i - 1], P[i], P[(i + 1) % len(P)]
            ac = c - a
            L = np.linalg.norm(ac)
            if L < 1e-9 or np.linalg.norm(b - a) < 1e-7:
                P.pop(i); changed = True; continue
            dist = abs(ac[0] * (b - a)[1] - ac[1] * (b - a)[0]) / L
            if dist < tol and (b - a) @ ac > 0 and (c - b) @ ac > 0:
                P.pop(i); changed = True
            else:
                i += 1
    return np.array(P)


def seg_end(s):
    return s["p1"]


def fit_loop(P, tol=0.03, max_turn_deg=24.0, min_arc_deg=15.0):
    """Closed polyline -> list of segment dicts:
    {'k': 'line', 'p0', 'p1'} | {'k': 'arc', 'p0', 'p1', 'c', 'r', 'ccw'} | {'k': 'circle', 'c', 'r'}"""
    P = np.asarray(P, float)
    if len(P) > 1 and np.linalg.norm(P[0] - P[-1]) < 1e-9:
        P = P[:-1]
    P = simplify_collinear(P, min(tol * 0.2, 0.005))
    n = len(P)
    if n >= 8:
        c, r, res = circle_fit(P)
        if res < max(tol, 0.003 * r):
            return [dict(k="circle", c=c, r=r)]
    E = np.roll(P, -1, axis=0) - P
    Lseg = np.linalg.norm(E, axis=1)
    ang = np.arctan2(E[:, 1], E[:, 0])
    turn = np.degrees((np.roll(ang, -1) - ang + np.pi) % (2 * np.pi) - np.pi)
    hard = np.nonzero(np.abs(turn) > max_turn_deg)[0]
    start = (hard[0] + 1) % n if len(hard) else int(np.argmax(Lseg))
    order = np.r_[start:n, 0:start]
    P, Lseg, turn = P[order], Lseg[order], turn[order]
    per = Lseg.sum()
    segs = []
    i = 0
    while i < n:
        j = i
        sign = 0
        while j + 1 < n:
            t = turn[j]
            if abs(t) > max_turn_deg or abs(t) < 0.02:
                break
            s = np.sign(t)
            if sign and s != sign:
                break
            if Lseg[j + 1] > 0.35 * per:
                break
            sign = s
            j += 1
        best = None
        while j >= i + 2:
            idx = np.arange(i, j + 2) % n
            pts = P[idx]
            c, r, res = circle_fit(pts)
            angs = np.unwrap(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))
            tot = abs(np.degrees(angs[-1] - angs[0]))
            if res < max(tol, 0.003 * r) and tot >= min_arc_deg and r < 5e3:
                best = (idx, c, r, angs[-1] > angs[0])
                break
            j -= 1
        if best is not None:
            idx, c, r, ccw = best
            segs.append(dict(k="arc", p0=P[idx[0]].copy(), p1=P[idx[-1]].copy(), c=c, r=r, ccw=bool(ccw)))
            i = n if idx[-1] == 0 else idx[-1]
        else:
            segs.append(dict(k="line", p0=P[i].copy(), p1=P[(i + 1) % n].copy()))
            i += 1
    out = []
    for s in segs:
        if out and s["k"] == "line" and out[-1]["k"] == "line":
            a, b, c2 = out[-1]["p0"], out[-1]["p1"], s["p1"]
            ac = c2 - a
            L = np.linalg.norm(ac)
            if L > 1e-9 and abs(ac[0] * (b - a)[1] - ac[1] * (b - a)[0]) / L < min(tol * 0.2, 0.005):
                out[-1]["p1"] = c2
                continue
        out.append(s)
    # close exactly
    for k in range(len(out)):
        out[k]["p1"] = out[(k + 1) % len(out)]["p0"] if out[k]["k"] != "circle" else None
    return out


def arc_mid(s):
    c, r = s["c"], s["r"]
    a0 = math.atan2(s["p0"][1] - c[1], s["p0"][0] - c[0])
    a1 = math.atan2(s["p1"][1] - c[1], s["p1"][0] - c[0])
    if s["ccw"]:
        d = (a1 - a0) % (2 * math.pi)
    else:
        d = -((a0 - a1) % (2 * math.pi))
    am = a0 + d / 2
    return c + r * np.array([math.cos(am), math.sin(am)])


def edges3d(segs, frame, w):
    E = []
    for s in segs:
        if s["k"] == "line":
            if np.linalg.norm(s["p1"] - s["p0"]) < 1e-6:
                continue
            E.append(cq.Edge.makeLine(frame.vec(*s["p0"], w), frame.vec(*s["p1"], w)))
        elif s["k"] == "arc":
            E.append(cq.Edge.makeThreePointArc(frame.vec(*s["p0"], w), frame.vec(*arc_mid(s), w), frame.vec(*s["p1"], w)))
        else:
            E.append(cq.Edge.makeCircle(float(s["r"]), frame.vec(s["c"][0], s["c"][1], w), V(*map(float, frame.Z))))
    return E


def make_wire(segs, frame, w):
    return cq.Wire.assembleEdges(edges3d(segs, frame, w))


# ================================================================= checks
def shape_mesh(shape, tol=0.05, ang=0.2):
    vs, ts = shape.tessellate(tol, ang)
    return trimesh.Trimesh(np.array([(p.x, p.y, p.z) for p in vs]), np.array(ts), process=True)


def deviation(shape, mesh, n=20000):
    rm = shape_mesh(shape)
    a, _ = trimesh.sample.sample_surface(rm, n, seed=1)
    b, _ = trimesh.sample.sample_surface(mesh, n, seed=2)
    _, d1, _ = trimesh.proximity.closest_point(mesh, a)
    _, d2, _ = trimesh.proximity.closest_point(rm, b)
    d = np.r_[d1, d2]
    return dict(p50=round(float(np.percentile(d, 50)), 3), p99=round(float(np.percentile(d, 99)), 3),
                max=round(float(d.max()), 3), vol=round(shape.Volume(), 1), vol_mesh=round(float(mesh.volume), 1))


def face_stats(shape):
    from collections import Counter
    return dict(Counter(f.geomType() for f in shape.Faces())), len(shape.Faces())


def edge_tolerance(shape):
    """Largest edge tolerance of a shape (mm): what a boolean has to bridge."""
    ex_ = TopExp_Explorer(shape.wrapped, TopAbs_EDGE)
    t = 0.0
    while ex_.More():
        t = max(t, BRep_Tool.Tolerance_s(TopoDS.Edge_s(ex_.Current())))
        ex_.Next()
    return t


def main():
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Convert a watertight STL to an exact B-rep STEP solid.")
    ap.add_argument("mesh", help=".stl, or .npz with float64 arrays V (vertices) and F (faces)")
    ap.add_argument("step")
    ap.add_argument("--brep", help="also write an OpenCascade .brep file")
    a = ap.parse_args()
    if a.mesh.endswith(".npz"):
        d = np.load(a.mesh)
        mesh = trimesh.Trimesh(d["V"], d["F"], process=False)
    else:
        mesh = trimesh.load(a.mesh, force="mesh")
    shp, rep = rebrep(mesh)
    shp.exportStep(a.step)
    if a.brep:
        from OCP.BRepTools import BRepTools
        BRepTools.Write_s(shp.wrapped, a.brep)
    back = cq.importers.importStep(a.step).solids().vals()
    rep.update(faces=face_stats(shp)[0], max_edge_tol=round(edge_tolerance(shp), 4),
               step_solids=len(back), step_valid=bool(back and back[0].isValid()),
               deviation=deviation(shp, mesh))
    print(json.dumps(rep, default=str))


if __name__ == "__main__":
    main()
