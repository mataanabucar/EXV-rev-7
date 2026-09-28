"""EX-MA hardware as real solids, placed where the build puts them (design frame, built pose).

Every item is (group, name, shape, colour key). Fasteners are modelled with plain shanks at the
nominal major diameter (no helical threads); heads, sockets, hex flats, 30 deg nut chamfers,
washers, the split in lock washers and the Phillips recess of wood screws are modelled.

    m3_items()        M3 screws, nuts, flat and split-lock washers
    pin_items(meshes) 8-32 threaded-rod pins and their jam nuts
    rod516_items()    5/16in lever axle, spool axle and lever handles with nuts / washers
    wood_items()      #6 / #8 flat-head wood screws (panel joints, printed parts to wood)
    stock_items()     6 mm BBs, PEX / copper / PVC, ropes, PTFE tubes, crimp sleeves

Used by 2026-09-28-solid-assembly.py.
"""
import importlib.util
import math
from pathlib import Path

import numpy as np
import trimesh
import cadquery as cq

SRC = Path(__file__).resolve().parent


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, SRC / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


V = cq.Vector
IN = 25.4

ex = _load("exma", "2026-09-24-exma_common.py")
asm = _load("asm", "2026-09-24-assembly.py")
bp = _load("parts", "2026-09-24-build-parts.py")
bx = _load("bx", "2026-09-24-build-box.py")
rt = asm.rt
DZ = ex.TURRET_DZ
T = ex.T_WOOD

# ---------------------------------------------------------------- catalogue dimensions (mm)
M3 = dict(d=3.0, head_d=5.5, head_h=3.0, key=2.5, key_depth=1.3,            # ISO 4762 socket head cap
          bh_d=5.7, bh_h=1.65, bh_key=2.0,                                   # ISO 7380 button head
          nut_af=5.5, nut_m=2.4,                                            # ISO 4032 hex nut
          washer=(3.2, 7.0, 0.5),                                           # ISO 7089 flat washer
          lock=(3.1, 6.2, 0.8))                                             # DIN 127 split lock washer
N832 = dict(d=4.17, nut_af=11 / 32 * IN, nut_m=1 / 8 * IN)                  # #8-32 rod + hex nut
R516 = dict(d=5 / 16 * IN, nut_af=1 / 2 * IN, nut_m=17 / 64 * IN, jam_m=3 / 16 * IN,
            washer=(11 / 32 * IN, 11 / 16 * IN, 0.065 * IN))                # 5/16 rod, nut, jam nut, SAE washer
WOOD6 = dict(d=0.138 * IN, head_d=0.262 * IN)                               # #6 flat-head wood screw
WOOD8 = dict(d=0.164 * IN, head_d=0.315 * IN)                               # #8 flat-head wood screw


# ---------------------------------------------------------------- local fastener solids
# Convention: axis +Z; the seat (bearing face of the head, or face of a washer/nut against the
# part) is the plane z = 0; the shank runs into the material toward -Z; heads sit at z >= 0.
def _cyl(r, z0, z1):
    return cq.Solid.makeCylinder(r, z1 - z0, V(0, 0, z0), V(0, 0, 1))


def _hex_prism(af, z0, z1):
    return cq.Workplane("XY").polygon(6, af / math.cos(math.pi / 6)).extrude(z1 - z0).translate((0, 0, z0)).val()


def socket_cap(L, s=M3):
    head = _cyl(s["head_d"] / 2, 0.0, s["head_h"])
    head = cq.Workplane().add(head).faces(">Z").edges().chamfer(0.3).val()
    sock = _hex_prism(s["key"], s["head_h"] - s["key_depth"], s["head_h"] + 1.0)
    shank = _cyl(s["d"] / 2, -L, 0.0)
    shank = cq.Workplane().add(shank).faces("<Z").edges().chamfer(0.3).val()
    return head.fuse(shank).cut(sock).clean()


def button_head(L, s=M3):
    a, k = s["bh_d"] / 2, s["bh_h"]
    R = (a * a + k * k) / (2 * k)
    dome = cq.Solid.makeSphere(R, V(0, 0, k - R), angleDegrees1=-90, angleDegrees2=90)
    dome = dome.intersect(_cyl(a, 0.0, k))
    sock = _hex_prism(s["bh_key"], k - 1.0, k + 1.0)
    shank = _cyl(s["d"] / 2, -L, 0.0)
    shank = cq.Workplane().add(shank).faces("<Z").edges().chamfer(0.3).val()
    return dome.fuse(shank).cut(sock).clean()


def hex_nut(af, m, d, chamfer=True):
    """Hex nut, z 0..-m (seat face at z = 0, toward +Z); 30 deg chamfer on both faces."""
    nut = _hex_prism(af, -m, 0.0)
    if chamfer:
        # 30 deg chamfer starting on the across-flats circle of each face
        rc = af / 2
        prof = cq.Workplane("XZ").polyline([(0, -m), (rc, -m), (rc + (m / 2) * math.tan(math.radians(60)), -m / 2),
                                            (rc, 0.0), (0, 0.0)]).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()
        nut = nut.intersect(prof)
    return nut.cut(_cyl(d / 2, -m - 1, 1.0)).clean()


def washer(di, do, t):
    """Flat washer, z 0..-t (seat face at z = 0)."""
    return _cyl(do / 2, -t, 0.0).cut(_cyl(di / 2, -t - 1, 1.0))


def lock_washer(di, do, t):
    """Split lock washer (flat model with the radial split), z 0..-t."""
    w = washer(di, do, t)
    gap = cq.Solid.makeBox(do, 0.8, t + 2, V(0.0, -0.4, -t - 1))
    return w.cut(gap).clean()


def rod(d, L):
    """Plain rod / threaded rod (major diameter), z 0..-L, 0.3 mm end chamfers."""
    r = _cyl(d / 2, -L, 0.0)
    return cq.Workplane().add(r).edges().chamfer(0.3).val()


def wood_screw(L, s):
    """Flat-head (82 deg countersunk) wood screw: head top at z = 0 (flush), point at z = -L,
    Phillips recess in the head."""
    D, d = s["head_d"], s["d"]
    h = (D - d) / 2 / math.tan(math.radians(41.0))
    tip = 1.5 * d
    prof = [(0, 0), (D / 2, 0), (d / 2, -h), (d / 2, -(L - tip)), (0, -L)]
    body = cq.Workplane("XZ").polyline(prof).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()
    w = 0.18 * D
    for ang in (0, 90):
        slot = cq.Solid.makeBox(0.62 * D, w, 2.0, V(-0.31 * D, -w / 2, -min(0.55 * h, 1.6)))
        slot = slot.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        body = body.cut(slot)
    return body.clean()


def sphere(r):
    return cq.Solid.makeSphere(r, V(0, 0, 0), angleDegrees1=-90, angleDegrees2=90)


# ---------------------------------------------------------------- placement
def frame(origin, z, x=None):
    z = np.asarray(z, float); z /= np.linalg.norm(z)
    if x is None:
        x = np.cross(z, np.eye(3)[np.argmin(np.abs(z))])
    x = np.asarray(x, float); x = x - (x @ z) * z; x /= np.linalg.norm(x)
    y = np.cross(z, x)
    Tm = np.eye(4)
    Tm[:3, 0], Tm[:3, 1], Tm[:3, 2], Tm[:3, 3] = x, y, z, origin
    return Tm


def placed(shape, Tm):
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    t = gp_Trsf()
    t.SetValues(*[float(v) for v in Tm[:3, :4].ravel()])
    return cq.Shape.cast(BRepBuilderAPI_Transform(shape.wrapped, t, True).Shape())


def apply(Tm, p):
    return (np.asarray(Tm) @ np.r_[np.asarray(p, float), 1.0])[:3]


def apply_dir(Tm, d):
    return np.asarray(Tm)[:3, :3] @ np.asarray(d, float)


class Bolted:
    """Collects the stack of one bolted joint: screw (head side seat), washers and nut on the far side."""

    def __init__(self, items, group, tag):
        self.items, self.group, self.tag = items, group, tag

    def add(self, name, shape, Tm, colour="steel"):
        self.items.append((self.group, f"{name} - {self.tag}", placed(shape, Tm), colour))

    def joint(self, head_seat, axis_into, L, head="socket", under_head=(), nut_seat=None, under_nut=(),
              nut=True, size=M3, x_hint=None):
        """head_seat: point on the part where the head (or its washer) bears; axis_into: direction the
        shank goes; under_head / under_nut: list of 'washer' / 'lock' stacked from the part surface;
        nut_seat: point on the far part surface where the nut side stack starts (along axis_into)."""
        a = np.asarray(axis_into, float); a /= np.linalg.norm(a)
        p = np.asarray(head_seat, float)
        up = -a                                            # out of the material on the head side
        for kind in under_head:
            t = size["washer"][2] if kind == "washer" else size["lock"][2]
            shp = washer(*size["washer"]) if kind == "washer" else lock_washer(*size["lock"])
            self.add(f"M3 {'flat' if kind == 'washer' else 'split-lock'} washer (head side)", shp, frame(p + up * t, up, x_hint))
            p = p + up * t
        scr = socket_cap(L) if head == "socket" else button_head(L)
        self.add(f"M3x{L:g} {'socket head cap screw' if head == 'socket' else 'button head screw'}", scr,
                 frame(p, up, x_hint))
        if nut and nut_seat is not None:
            # every stack element occupies [q, q + a t]; the local solids span z 0..-t, so each is
            # placed with its z axis along a at q + a t
            q = np.asarray(nut_seat, float)
            for kind in under_nut:
                t = size["washer"][2] if kind == "washer" else size["lock"][2]
                shp = washer(*size["washer"]) if kind == "washer" else lock_washer(*size["lock"])
                self.add(f"M3 {'flat' if kind == 'washer' else 'split-lock'} washer (nut side)", shp, frame(q + a * t, a, x_hint))
                q = q + a * t
            m = size["nut_m"]
            self.add("M3 hex nut", hex_nut(size["nut_af"], m, size["d"]), frame(q + a * m, a, x_hint))


def _mods():
    return _load("mods", "2026-09-24-build-exma-mods.py")


# ================================================================= M3 joints
def m3_items():
    items = []
    P = asm.placements()
    mods = _mods()

    # --- joint-drum key screws (M3x12): head in the wall socket, shank into the drum face
    B = Bolted(items, "Hardware/M3 screws, nuts, washers", "")
    for member, piv0, dr, angs, anchor, v_from in (
            ("boom", ex.P_BOOM0, bp.BOOM_DRIVE_R, bp.BOOM_DRIVE_ANGS, 90.0, 16.5),
            ("stick", ex.P_STICK0, bp.STICK_DRIVE_R, bp.STICK_DRIVE_ANGS, math.degrees(rt.BOOM_ANG), 10.7)):
        for i, a in enumerate(angs):
            du, dz = mods.drum_key_rel(dr, a, anchor)
            for sgn, side in ((1, "left"), (-1, "right")):
                B.tag = f"{member} drum key {side} {i + 1}"
                seat = (piv0[0] + du, sgn * (v_from + mods.KEY_HEAD_DEPTH - M3["head_h"]), piv0[1] + dz + DZ)
                B.joint(seat, (0, -sgn, 0), 12, nut=False)

    # --- slewing-ring retaining ring (M3x12 + split-lock under the head, nut in the rim slot)
    for k in range(bp.N_RET_BOLTS):
        a = math.radians(22.5 + 45 * k)
        x, y = bp.RET_BOLT_R * math.cos(a), bp.RET_BOLT_R * math.sin(a)
        B.tag = f"retaining ring {k + 1}"
        slot_top = ex.BASE_RIM_Z[0] + 2.5 + bp.M3_NUT_H / 2
        B.joint((x, y, ex.RET_RING_Z[1]), (0, 0, -1), 12, under_head=["lock"], nut_seat=(x, y, slot_top),
                x_hint=(math.cos(a), math.sin(a), 0))

    # --- boom / stick joining lugs (M3x20 + nut), lug centres from the build's own lug finder
    for member in ("boom", "stick"):
        if member == "boom":
            halves = [ex.load_3mf_object(*h) for h in ex.BOOM_HALVES]
            names = list(rt.TUBES)
            origin, ang = ex.P_BOOM0, rt.BOOM_ANG
            stations = [(45.0, 1), (45.0, -1), (110.0, 1), (110.0, -1), (160.0, 1), (160.0, -1)]
        else:
            halves = [ex.load_3mf_object(*h) for h in ex.STICK_HALVES]
            names = ["bucket_hi", "bucket_lo"]
            origin, ang = ex.P_STICK0, rt.STICK_ANG
            stations = [(40.0, 1), (40.0, -1), (100.0, 1), (100.0, -1), (150.0, 1), (150.0, -1)]
        full = trimesh.util.concatenate(halves)
        avoid = [rt.natural(n) for n in names]
        cut = mods.channels(mods.guided(names, member))
        lugs, _ = mods.joining_lugs(full, origin, ang, stations, avoid, cut)
        for i, lug in enumerate(lugs):
            bb = lug.bounding_box()
            c = 0.5 * (np.array(bb[:3]) + np.array(bb[3:]))
            c[2] += DZ
            B.tag = f"{member} joining lug {i + 1}"
            h = mods.LUG["size"][1] / 2
            B.joint((c[0], h, c[2]), (0, -1, 0), 20, nut_seat=(c[0], -h, c[2]))

    # --- lever hubs: drag clamp (M3x20, y -10.5) and handle pinch clamp (M3x20), head +x, nut -x
    for name, (vh, vd) in ex.LEVERS.items():
        Th = P[f"lever-hub-{name}"]
        off = vh - vd
        X, Yd = apply_dir(Th, (1, 0, 0)), apply_dir(Th, (0, 1, 0))
        for label, y, z, xh, xn in (("drag clamp", -10.5, off, 7.0, -7.0),
                                     ("handle clamp", 34 - bp.LEVER_SOCKET_DEPTH / 2, off + 7.0, 8.0, -8.0)):
            B.tag = f"{name} lever {label}"
            B.joint(apply(Th, (xh, y, z)), -X, 20, under_nut=["lock"], nut_seat=apply(Th, (xn, y, z)), x_hint=Yd)
        # tail anchors: M3x10 button head in the web slot; washer, rope loop, washer under the head
        r_in = ex.DRUM["lever"]["pitch"] / 2 - bp.ROPE / 2 - 6.0
        mid = (12.0 + r_in - 3.0) / 2
        w2 = ex.DRUM["lever"]["width"] / 2
        Zd = apply_dir(Th, (0, 0, 1))
        for i, a in enumerate((25.0, -25.0)):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            web_top = apply(Th, (mid * ca, mid * sa, -w2 + 4.0))
            web_bot = apply(Th, (mid * ca, mid * sa, -w2))
            B.tag = f"{name} lever rope anchor {'upper' if a > 0 else 'lower'}"
            _anchor(B, web_top, web_bot, Zd)

    # --- slew spool anchors (web z 0..4 in the spool frame)
    Ts = P["slew-spool"]
    dep = ex.spool_departures()
    Zs = apply_dir(Ts, (0, 0, 1))
    for lane in ("A", "B"):
        a = math.radians(dep[lane]["tangent_deg"])
        p2 = (36.0 * math.cos(a), 36.0 * math.sin(a))
        B.tag = f"slew spool rope anchor {lane}"
        _anchor(B, apply(Ts, (*p2, 4.0)), apply(Ts, (*p2, 0.0)), Zs)

    # --- slew wheel to spool flange (M3x20, head in the wheel counterbore, nut under the flange)
    Tw = P["slew-wheel"]
    for k in range(3):
        a = math.radians(90 + 120 * k)
        x, y = bp.BOLT_CIRCLE_SPOOL * math.cos(a), bp.BOLT_CIRCLE_SPOOL * math.sin(a)
        B.tag = f"slew wheel {k + 1}"
        B.joint(apply(Tw, (x, y, bp.WHEEL_T - bp.M3_HEAD_H)), (0, 0, -1), 20, under_nut=["lock"],
                nut_seat=apply(Tw, (x, y, -5.0)))

    # --- PEX pinch clamps (M3x25): turret hub (design frame) and pedestal slew drum
    rb = ex.TURRET_TUBE_OD / 2 + 0.15
    yb = (rb + bp.TURRET_HUB_R) / 2
    zb = (bp.TURRET_HUB_Z[0] + ex.FLANGE_Z[0]) / 2
    B.tag = "turret hub PEX clamp"
    B.joint((6.0, yb, zb), (-1, 0, 0), 25, under_nut=["lock"], nut_seat=(-6.0, yb, zb), x_hint=(0, 1, 0))
    Td = P["slew-drum"]
    yb = (bp.SLEW_BORE / 2 + bp.SLEW_HUB_R) / 2 + 1.5
    B.tag = "slew drum PEX clamp"
    B.joint(apply(Td, (6.0, yb, 14.0)), (-1, 0, 0), 25, under_nut=["lock"], nut_seat=apply(Td, (-6.0, yb, 14.0)),
            x_hint=(0, 1, 0))

    # --- conduit fittings and box-to-sandbox bolts (flat washers both sides)
    fit_ped = (ex.PED_U[0] + T, ex.PED_FIT_V, ex.COND_Z)
    for i, p in enumerate(bx.fitting_bolts(fit_ped, 1)):
        B.tag = f"pedestal conduit fitting {i + 1}"
        B.joint((p[0] + 6.0, p[1], p[2]), (-1, 0, 0), 25, under_head=["washer"],
                under_nut=["washer"], nut_seat=(ex.PED_U[0], p[1], p[2]))
    fit_box = (ex.BOX_U[1] - T, ex.MOUTH_V, ex.COND_Z)
    for i, p in enumerate(bx.fitting_bolts(fit_box, -1)):
        B.tag = f"box conduit fitting {i + 1}"
        B.joint((ex.BOX_U[1] - T - 6.0, p[1], p[2]), (1, 0, 0), 35, under_head=["washer"], under_nut=["washer"],
                nut_seat=(ex.SB_U[0] + T, p[1], p[2]))
    for i, (sv, nm) in enumerate(((ex.BOX_V[0] + 25.0, "right"), (ex.BOX_V[1] - 25.0, "left"))):
        z = ex.BOX_Z[0] + T + 25.0
        B.tag = f"box to sandbox {nm}"
        B.joint((ex.BOX_U[1] - T, sv, z), (1, 0, 0), 30, under_head=["washer"], under_nut=["washer"],
                nut_seat=(ex.SB_U[0] + T, sv, z))
    return items


def _anchor(B, web_top, web_bot, up):
    """Slotted rope anchor: washer, rope-loop gap, washer, M3x10 button head on top; lock + nut under."""
    up = np.asarray(up, float) / np.linalg.norm(up)
    w = M3["washer"][2]
    B.add("M3 flat washer (under rope loop)", washer(*M3["washer"]), frame(web_top + up * w, up))
    top = web_top + up * (w + ex.ROPE_D)
    B.add("M3 flat washer (over rope loop)", washer(*M3["washer"]), frame(top + up * w, up))
    B.joint(top + up * w, -up, 10, head="button", under_nut=["lock"], nut_seat=web_bot)


# ================================================================= 8-32 pins
def pin_items(meshes):
    """meshes: dict name -> trimesh of the (placed) EX-MA parts, for the outer faces the nuts bear on."""
    items = []
    g = "Hardware/8-32 pins and jam nuts"
    nut = hex_nut(N832["nut_af"], N832["nut_m"], N832["d"])

    def outer_face(mesh, p, d, radii=(3.5, 5.0, 6.5, 7.5)):
        """Outermost face along d, probed on rings around the axis (the axis itself runs in the bore)."""
        d = np.asarray(d, float)
        e1 = np.cross(d, (1.0, 0, 0) if abs(d[0]) < 0.9 else (0, 0, 1.0)); e1 /= np.linalg.norm(e1)
        e2 = np.cross(d, e1)
        best = None
        for r in radii:
            origins = [np.asarray(p, float) + r * (math.cos(t) * e1 + math.sin(t) * e2)
                       for t in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
            loc, idx, _ = mesh.ray.intersects_location(origins, [d] * len(origins), multiple_hits=True)
            if len(loc):
                v = float(max((np.asarray(loc) - np.asarray(p)) @ d)) + float(np.asarray(p) @ d)
                best = v if best is None else max(best, v)
        return None if best is None else abs(best)

    def pin(name, axis_pt, sgn, v_in, L, mesh_names):
        a = np.array([0.0, sgn, 0.0])
        p_in = np.array([axis_pt[0], sgn * v_in, axis_pt[1]])
        items.append((g, f"8-32 threaded rod {L:g} mm - {name}", placed(rod(N832["d"], L), frame(p_in, -a)), "steel"))
        # jam pair against the outermost face the rod passes through
        faces = [outer_face(meshes[m], p_in, a) for m in mesh_names if m in meshes]
        faces = [f for f in faces if f is not None]
        s = max(faces) if faces else v_in + L - 2 * N832["nut_m"]
        for k in range(2):
            q = a * (s + k * N832["nut_m"])
            q = np.array([axis_pt[0], q[1], axis_pt[1]])
            items.append((g, f"8-32 hex nut (jam {k + 1}) - {name}", placed(nut, frame(q + a * N832["nut_m"], a)), "steel"))

    for sgn, side in ((1, "left"), (-1, "right")):
        pin(f"boom split pin {side}", ex.P_BOOM, sgn, asm.SPLIT_PIN_V["boom"][0], 42.0, ["tower"])
        pin(f"stick split pin {side}", ex.P_STICK, sgn, asm.SPLIT_PIN_V["stick"][0], 22.0,
            [f"boom-half-{side}"])
    # bucket pin through both ears: 65 mm centred, jam pair at each end
    L = 65.0
    a = np.array([0.0, 1.0, 0.0])
    p0 = np.array([ex.P_BUCKET[0], -L / 2, ex.P_BUCKET[1]])
    items.append((g, "8-32 threaded rod 65 mm - bucket pin", placed(rod(N832["d"], L), frame(p0 + a * L, a)), "steel"))
    for sgn, side, ear in ((1, "left", "bucket-ear-left"), (-1, "right", "bucket-ear-right")):
        d = a * sgn
        s = outer_face(meshes[ear], np.array([ex.P_BUCKET[0], 0.0, ex.P_BUCKET[1]]), d) if ear in meshes else 25.0
        for k in range(2):
            q = np.array([ex.P_BUCKET[0], sgn * (s + k * N832["nut_m"]), ex.P_BUCKET[1]])
            items.append((g, f"8-32 hex nut (jam {k + 1}) - bucket pin {side}",
                          placed(nut, frame(q + d * N832["nut_m"], d)), "steel"))
    return items


# ================================================================= 5/16 rod
def rod516_items():
    items = []
    g = "Hardware/5-16 rod, nuts, washers"
    d = R516["d"]
    y = ex.AXLE_BLOCK_V[1] + 10
    items.append((g, f"5/16in rod {2 * y:.0f} mm - lever axle",
                  placed(rod(d, 2 * y), frame((ex.AXLE_U, y, ex.AXLE_Z), (0, 1, 0))), "steel"))
    wsh = washer(*R516["washer"])
    nut = hex_nut(R516["nut_af"], R516["nut_m"], d)
    jam = hex_nut(R516["nut_af"], R516["jam_m"], d)
    wt = R516["washer"][2]
    for sgn, side in ((1, "left"), (-1, "right")):
        a = np.array([0, sgn, 0.0])
        s = np.array([ex.AXLE_U, sgn * ex.AXLE_BLOCK_V[1], ex.AXLE_Z])
        items.append((g, f"5/16in SAE washer - lever axle {side}", placed(wsh, frame(s + a * wt, a)), "steel"))
        items.append((g, f"5/16in hex nut - lever axle {side}", placed(nut, frame(s + a * (wt + R516['nut_m']), a)), "steel"))
    z0, z1 = ex.BOX_Z[0], ex.BOX_Z[1] + 32.0
    c = ex.WHEEL_C
    items.append((g, f"5/16in rod {z1 - z0:.0f} mm - slew spool axle", placed(rod(d, z1 - z0), frame((*c, z1), (0, 0, 1))), "steel"))
    # bottom: washer + jam nut inside the 22 mm x 7 mm counterbore under the box floor (a full nut
    # would stand 1.4 mm below the floor)
    s = np.array([*c, ex.BOX_Z[0] + 7.0])
    dn = np.array([0, 0, -1.0])
    items.append((g, "5/16in SAE washer - spool axle bottom", placed(wsh, frame(s + dn * wt, dn)), "steel"))
    items.append((g, "5/16in jam nut - spool axle bottom", placed(jam, frame(s + dn * (wt + R516['jam_m']), dn)), "steel"))
    spool_top = ex.Z_SLEW_LAYER - ex.DRUM["slew"]["width"] / 2 + bp.SPOOL_LEN
    s = np.array([*c, spool_top + bp.WHEEL_T])
    up = np.array([0, 0, 1.0])
    items.append((g, "5/16in SAE washer - spool axle top", placed(wsh, frame(s + up * wt, up)), "steel"))
    items.append((g, "5/16in hex nut - spool axle top", placed(nut, frame(s + up * (wt + R516['nut_m']), up)), "steel"))
    # lever handles: rod from the hub socket floor into the knob
    for j, (vh, vd) in ex.LEVERS.items():
        L = ex.HANDLE_LEN - 9.0 + ex.KNOB_BORE_DEPTH
        top = (ex.AXLE_U, vh, ex.AXLE_Z + ex.HANDLE_LEN + ex.KNOB_BORE_DEPTH)
        items.append((g, f"5/16in rod {L:.0f} mm - {j} lever handle", placed(rod(d, L), frame(top, (0, 0, 1))), "steel"))
    return items


# ================================================================= wood screws
PANEL_JOINTS = [
    # (face panel, edge panel): the screw goes through the face panel into the edge of the other
    ("box floor", "box front"), ("box floor", "box rear"), ("box floor", "box left side"), ("box floor", "box right side"),
    ("box top (removable)", "box front"), ("box top (removable)", "box rear"),
    ("box top (removable)", "box left side"), ("box top (removable)", "box right side"),
    ("box front", "box left side"), ("box front", "box right side"), ("box rear", "box left side"), ("box rear", "box right side"),
    ("pedestal top", "pedestal wall -u (conduit)"), ("pedestal top", "pedestal wall +u (removable access)"),
    ("pedestal top", "pedestal wall -v"), ("pedestal top", "pedestal wall +v"),
    ("pedestal wall -u (conduit)", "pedestal wall -v"), ("pedestal wall -u (conduit)", "pedestal wall +v"),
    ("pedestal wall +u (removable access)", "pedestal wall -v"), ("pedestal wall +u (removable access)", "pedestal wall +v"),
    ("pedestal wall -v", "pedestal shelf cleat -v"), ("pedestal wall +v", "pedestal shelf cleat +v"),
    ("sandbox floor", "sandbox wall -u (box side)"), ("sandbox floor", "sandbox wall +u"),
    ("sandbox floor", "sandbox wall -v"), ("sandbox floor", "sandbox wall +v"),
    ("sandbox wall -u (box side)", "sandbox wall -v"), ("sandbox wall -u (box side)", "sandbox wall +v"),
    ("sandbox wall +u", "sandbox wall -v"), ("sandbox wall +u", "sandbox wall +v"),
]


def wood_items():
    items = []
    g = "Hardware/wood screws"
    panels = {p.name: p for p in bx.panels()}
    s6_long = wood_screw(1.25 * IN, WOOD6)
    s6 = wood_screw(0.75 * IN, WOOD6)
    s8 = wood_screw(1.0 * IN, WOOD8)
    n = 0
    for fa, eb in PANEL_JOINTS:
        A, Bp = panels[fa], panels[eb]
        lo_a, hi_a, lo_b, hi_b = map(np.array, (A.lo, A.hi, Bp.lo, Bp.hi))
        k = next(i for i in range(3) if abs(hi_a[i] - lo_b[i]) < 1e-6 or abs(lo_a[i] - hi_b[i]) < 1e-6)
        if abs(hi_a[k] - lo_b[k]) < 1e-6:
            head, d = lo_a[k], 1.0
        else:
            head, d = hi_a[k], -1.0
        others = [i for i in range(3) if i != k]
        ov = {i: (max(lo_a[i], lo_b[i]), min(hi_a[i], hi_b[i])) for i in others}
        j = max(others, key=lambda i: ov[i][1] - ov[i][0])
        m = [i for i in others if i != j][0]
        for t in (0.125, 0.375, 0.625, 0.875):
            p = np.zeros(3)
            p[k] = head
            p[j] = ov[j][0] + t * (ov[j][1] - ov[j][0])
            p[m] = 0.5 * (ov[m][0] + ov[m][1])
            ax = np.zeros(3); ax[k] = -d                  # local +Z points out of the face panel
            n += 1
            items.append((g, f"#6 x 1-1/4in wood screw {n:03d} - {fa} to {eb}", placed(s6_long, frame(p, ax)), "zinc"))
    # printed parts to wood (#6 x 3/4in); the head's cone rests on the 3.8 mm clearance hole edge
    P = asm.placements()
    h_seat = (WOOD6["head_d"] - 3.8) / 2 / math.tan(math.radians(41.0))
    k = 0

    def s6_at(p_top, up, what):
        nonlocal k
        k += 1
        items.append((g, f"#6 x 3/4in wood screw {k:02d} - {what}",
                      placed(s6, frame(np.asarray(p_top) + np.asarray(up) * h_seat, up)), "zinc"))
    for sgn, side in ((1, "left"), (-1, "right")):
        for du in (-15.0, 15.0):
            # from below through the box floor into the bearing block (head flush with the floor bottom)
            k += 1
            items.append((g, f"#6 x 3/4in wood screw {k:02d} - axle bearing block {side}",
                          placed(s6, frame((ex.AXLE_U + du, sgn * sum(ex.AXLE_BLOCK_V) / 2, ex.BOX_Z[0]), (0, 0, -1))), "zinc"))
    for i in range(3):
        a = math.radians(90 + 120 * i)
        s6_at(apply(P["spool-riser"], (21.0 * math.cos(a), 21.0 * math.sin(a), 4.0)), (0, 0, 1), "spool riser")
    for lane in ("A", "B"):
        for sy in (-1, 1):
            s6_at(apply(P[f"slew-tube-post@{lane}"], (0.0, sy * 13.0, 4.0)), (0, 0, 1), f"slew sleeve post {lane}")
    for i in range(3):
        a = math.radians(90 + 120 * i)
        s6_at(apply(P["slew-tube-bushing"], (18.5 * math.cos(a), 18.5 * math.sin(a), 0.0)), (0, 0, 1), "PEX bushing")
    for sx in (-1, 1):
        s6_at(apply(P["elbow-support"], (sx * 16.0, 0.0, 4.0)), (0, 0, 1), "elbow support")
    # base to the pedestal top (#8 x 1in) in the 8.4 mm counterbores
    h8 = (WOOD8["head_d"] - 4.4) / 2 / math.tan(math.radians(41.0))
    for i in range(4):
        a = math.radians(45 + 90 * i)
        p = (38.0 * math.cos(a), 38.0 * math.sin(a), ex.BASE_TOP_Z - 2.5 + h8)
        items.append((g, f"#8 x 1in wood screw {i + 1} - base to pedestal top", placed(s8, frame(p, (0, 0, 1))), "zinc"))
    return items


# ================================================================= stock: balls, tubes, rope, crimps
def stock_items():
    items = []
    fa = _load("fa", "2026-09-25-full-assembly.py")
    cp = fa.cp
    pk = fa.pk
    g_bb = "Slewing ring balls"
    n_b = int(2 * math.pi * ex.BALL_CIRCLE_R // (ex.BALL_D + 0.4))
    ball = sphere(ex.BALL_D / 2)
    for k in range(n_b):
        a = 2 * math.pi * k / n_b
        items.append((g_bb, f"6 mm BB {k + 1:02d}", placed(ball, frame((ex.BALL_CIRCLE_R * math.cos(a),
                                                                            ex.BALL_CIRCLE_R * math.sin(a), ex.BALL_Z), (0, 0, 1))), "bb"))
    hs = pk.hardware_solids()
    items.append(("Pedestal", "3/4in PEX-B turret tube", hs["3/4in PEX-B turret tube"][0], "pex"))
    items.append(("Pedestal", "1/2in copper elbow + pipe", hs["1/2in copper elbow + pipe"][0], "copper"))
    items.append(("Sandbox", "2in PVC conduit", hs["2in PVC conduit"][0], "pvc"))
    g_r = "Ropes, PTFE tubes, crimps"
    paths = cp.all_paths()
    for name, e in paths.items():
        poly = cp.polyline(e)
        shp, st = fa.swept_tube(poly, fa.ROPE_D / 2)
        items.append((g_r, f"1/16in rope - {name}", shp, e["circuit"]))
        for i, seg in enumerate(e["ptfe"]):
            shp, st = fa.swept_tube(seg, fa.PTFE_OD / 2, fa.PTFE_ID / 2)
            items.append((g_r, f"PTFE tube 4x2 - {name}{'' if len(e['ptfe']) == 1 else f' {i + 1}'}", shp, "ptfe"))
    # crimps: single stop sleeves where the ropes end in the drum pockets, double sleeves at the
    # tail loops on the lever / spool anchors
    single = cq.Solid.makeCylinder(2.15, 6.4, V(0, 0, -3.2), V(0, 0, 1)).cut(
        cq.Solid.makeCylinder(0.9, 8.0, V(0, 0, -4.0), V(0, 0, 1)))
    dbl = (cq.Workplane("XY").slot2D(6.0, 3.2).extrude(8.0).translate((0, 0, -4.0)).val()
           .cut(cq.Solid.makeCylinder(0.9, 10, V(-1.4, 0, -5), V(0, 0, 1)))
           .cut(cq.Solid.makeCylinder(0.9, 10, V(1.4, 0, -5), V(0, 0, 1))))
    done_single = set()
    for name, e in paths.items():
        poly = cp.polyline(e)
        end, prev = poly[-1], poly[-2]
        d = (end - prev) / np.linalg.norm(end - prev)
        key = tuple(np.round(end, 1))
        if key not in done_single:
            done_single.add(key)
            items.append((g_r, f"single crimp sleeve - {e['circuit'] + ' drum midpoint' if e['circuit'] != 'slew' else name}",
                          placed(single, frame(end - d * 3.2, d)), "crimp"))
        st, nx = poly[0], poly[1]
        d0 = (nx - st) / np.linalg.norm(nx - st)
        items.append((g_r, f"double crimp sleeve - {name} loop", placed(dbl, frame(st + d0 * 6.0, d0)), "crimp"))
    return items


def all_items(meshes):
    return m3_items() + pin_items(meshes) + rod516_items() + wood_items() + stock_items()
