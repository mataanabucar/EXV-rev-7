#!/usr/bin/env python3
"""EX-MA simplified mechanism - new printed parts (CadQuery).

Every part is modelled in its own print frame (axis = +Z, flat face on the bed).
Run:  <cadenv>/bin/python 2026-09-24-build-parts.py
Writes STEP/ and STL/ files named 2026-09-24-<part>.{step,stl} and prints a
per-part check table (solid count, volume, bounding box, watertight STL).
"""
import importlib.util
import math
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("exma", HERE / "2026-09-24-exma_common.py")
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)

# ---------------------------------------------------------------- parameters
ROPE = ex.ROPE_D                 # 1.6 mm (1/16") 7x19 wire rope
BORE = ex.PIN_BORE               # 4.6 printed clearance for 8-32 rod
M3 = ex.M3_CLEAR                 # 3.4
M3_HEAD_D, M3_HEAD_H = 6.5, 3.0
M3_NUT_AF, M3_NUT_H = 5.8, 2.6   # printed clearance for an M3 hex nut
CRIMP_LEN, CRIMP_W = 9.0, 4.8    # pocket for a 1/16" single stop sleeve (about 4.3 x 6.4)
GROOVE_FLANGE_T = 1.5            # flange thickness at the rim
ROPE_HOLE = 2.4                  # rope pass-through holes
PTFE_BORE = 4.15                 # counterbore for 4 mm OD PTFE tube (tube end stop)

# drum keying: an M3 screw threads into each drum face; its head sits in a socket in the
# member's inner wall (the drum turns with its own member). Angle in the drum print frame.
BOOM_DRIVE_R, BOOM_DRIVE_ANG = 9.0, -60.0
STICK_DRIVE_R, STICK_DRIVE_ANG = 7.2, -90.0
M3_TAP = 2.6                     # pilot hole for an M3 screw in plastic
CLAMP_SLIT = 1.5

AXLE_JOURNAL_D = 12.2            # turns in the existing Ø12.7 hole in the stick nose (no change to the stick)
AXLE_HEX_AF = 12.0               # hex ends keyed into bucket ears G/H
AXLE_Z = dict(drum=5.0, cone=9.5, journal=18.9, hex=24.5)   # half-lengths along the axle

SLEW_HUB_R, SLEW_BORE = 17.0, 27.0   # 3/4" PVC OD 26.7
LEVER_SOCKET_D, LEVER_SOCKET_DEPTH = 16.2, 25.0   # 5/8" hardwood dowel handle
SPOOL_TUBE_R, SPOOL_LEN = 12.0, 145.0
WHEEL_R_OUT, WHEEL_R_IN, WHEEL_T = 92.0, 78.0, 12.0
BOLT_CIRCLE_SPOOL = 16.0

CONDUIT_OD = 60.3                # 2" sch40 PVC
COPPER_OD = 15.9                 # 1/2" copper
FIT_T = 26.0

RET_BOLT_R = 66.8                # retaining ring bolt circle
N_RET_BOLTS = 8


# ---------------------------------------------------------------- helpers
def revolve(pts):
    """Revolve an (r, z) profile about global Z."""
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))


def groove_profile(pitch, width, r_in, flange_t=GROOVE_FLANGE_T, lip=None):
    """(r, z) profile of a single-groove drum rim centred on z = 0.

    Rope centre sits on the pitch radius; groove walls are 45 deg (printable)."""
    rc = pitch / 2 - ROPE / 2                     # groove floor radius
    lip = lip if lip is not None else 3.3
    rf = rc + lip                                 # flange radius
    w2 = width / 2
    return [(r_in, -w2), (rf, -w2), (rf, -w2 + flange_t), (rc, -w2 + flange_t + lip),
            (rc, w2 - flange_t - lip), (rf, w2 - flange_t), (rf, w2), (r_in, w2)], rc, rf


def crimp_pocket(rc, floor_r, angle_deg=90.0, rf=None):
    """Radial pocket that seats the midpoint single crimp at the anchor angle."""
    top = (rf or rc) + 2.0
    box = cq.Workplane("XY").box(CRIMP_LEN, top - floor_r, CRIMP_W).translate((0, (top + floor_r) / 2, 0))
    return box.rotate((0, 0, 0), (0, 0, 1), angle_deg - 90.0)


def z_cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((x, y, z0))


def x_hole(d, length, y, z):
    return cq.Workplane("YZ").circle(d / 2).extrude(length).translate((-length / 2, y, z))


# ---------------------------------------------------------------- joint drums
def joint_drum(pitch, width, lip, drive_r, drive_ang):
    """Boom / stick drum: single groove, 8-32 pivot bore, crimp pocket, M3 key-screw pilot.

    An M3 screw in each face keys the drum to its own member (head in a wall socket),
    so the drum turns with that member."""
    prof, rc, rf = groove_profile(pitch, width, BORE / 2, lip=lip)
    d = revolve(prof)
    d = d.cut(crimp_pocket(rc, rc - 4.5, 90.0, rf))
    a = math.radians(drive_ang)
    d = d.cut(z_cyl(M3_TAP / 2, -width, width, drive_r * math.cos(a), drive_r * math.sin(a)))
    return d


def boom_drum():
    return joint_drum(ex.DRUM["boom"]["pitch"], ex.DRUM["boom"]["width"], 3.3, BOOM_DRIVE_R, BOOM_DRIVE_ANG)


def stick_drum():
    return joint_drum(ex.DRUM["stick"]["pitch"], ex.DRUM["stick"]["width"], 2.9, STICK_DRIVE_R, STICK_DRIVE_ANG)


def pinch_clamp(part, r_bore, r_out, z0, z1, bolt_z, boss=True):
    """Split-clamp a tube bore: radial slit + tangential M3 pinch bolt that stays outside the bore."""
    y_bolt = (r_bore + r_out) / 2 + (1.5 if boss else 0.0)
    if boss:
        part = part.union(cq.Workplane("XY").box(18, 8, z1 - z0).translate((0, r_out + 1.0, (z0 + z1) / 2)))
    part = part.cut(cq.Workplane("XY").box(CLAMP_SLIT, r_out + 8, z1 - z0 + 2)
                    .translate((0, (r_out + 8) / 2 + r_bore - 1, (z0 + z1) / 2)))
    part = part.cut(x_hole(M3, 60, y_bolt, bolt_z))
    part = part.cut(cq.Workplane("YZ").circle(M3_HEAD_D / 2).extrude(20).translate((6.0, y_bolt, bolt_z)))
    part = part.cut(cq.Workplane("YZ").polygon(6, M3_NUT_AF / math.cos(math.pi / 6)).extrude(20)
                    .translate((-26.0, y_bolt, bolt_z)))
    return part


def bucket_drum_axle():
    """Bucket drum + journals + hex ends in one part. Journals turn in the stick nose,
    hex ends key into ears G/H, an 8-32 rod through the bore clamps the ears to the shoulders."""
    pitch, width = ex.DRUM["bucket"]["pitch"], ex.DRUM["bucket"]["width"]
    rc = pitch / 2 - ROPE / 2
    lip, ft = 2.8, 1.2
    rf = rc + lip
    rj = AXLE_JOURNAL_D / 2
    zd, zc, zj = AXLE_Z["drum"], AXLE_Z["cone"], AXLE_Z["journal"]
    half = [(BORE / 2, 0), (rc, 0), (rc, width / 2 - ft - lip), (rf, width / 2 - ft), (rf, zd),
            (rj, zc), (rj, zj), (BORE / 2, zj)]
    full = [(r, -z) for r, z in reversed(half)] + half[1:]
    body = revolve(full)
    hexes = (cq.Workplane("XY").polygon(6, AXLE_HEX_AF / math.cos(math.pi / 6)).extrude(AXLE_Z["hex"] - zj)
             .translate((0, 0, zj)))
    body = body.union(hexes).union(hexes.mirror("XY"))
    body = body.cut(z_cyl(BORE / 2, -30, 30))
    body = body.cut(crimp_pocket(rc, 4.0, 90.0, rf))
    return body


# ---------------------------------------------------------------- slew drum (pedestal)
def slew_drum():
    """Ø110 pitch drum clamped on the rotating 3/4" PVC tube by an M3x30 cross-bolt."""
    pitch, width = ex.DRUM["slew"]["pitch"], ex.DRUM["slew"]["width"]
    prof, rc, rf = groove_profile(pitch, width, 49.0)
    rim = revolve(prof)
    web = z_cyl(49.5, -width / 2, -width / 2 + 6.0)
    hub = z_cyl(SLEW_HUB_R, -width / 2, 23.0)
    d = rim.union(web).union(hub)
    d = d.cut(z_cyl(SLEW_BORE / 2, -20, 30))
    d = d.cut(crimp_pocket(rc, rc - 4.5, 90.0, rf))
    # split clamp on the PVC tube (pinch bolt outside the tube bore - cables run inside the tube)
    d = pinch_clamp(d, SLEW_BORE / 2, SLEW_HUB_R, -width / 2 + 6.0, 23.0, 14.0)
    return d


# ---------------------------------------------------------------- slewing ring parts
def race_geometry():
    """Contact geometry of the printed ball race (45 deg four-point contact)."""
    R = ex.BALL_D / 2 + ex.RACE_CLEAR
    c = R * math.cos(math.radians(45))
    rb, zb = ex.BALL_CIRCLE_R, ex.BALL_Z
    return dict(R=R, c=c, rb=rb, zb=zb,
                outer_at_joint=rb + 2 * c,          # outer V apex radius at z = zb
                inner_at_joint=rb - 2 * c)          # inner V apex radius at z = zb


def retaining_ring():
    """Upper outer race: bolts onto the base rim, holds the turret flange down."""
    g = race_geometry()
    z0, z1 = 0.0, ex.RET_RING_Z[1] - ex.RET_RING_Z[0]
    r_face_top = 61.5
    z_face_top = (g["outer_at_joint"] - r_face_top)          # 45 deg face rises as r falls
    pts = [(g["outer_at_joint"], z0), (ex.RACE_R[1], z0), (ex.RACE_R[1], z1), (r_face_top, z1),
           (r_face_top, z_face_top)]
    ring = revolve(pts)
    for k in range(N_RET_BOLTS):
        a = math.radians(22.5 + 45 * k)
        ring = ring.cut(z_cyl(M3 / 2, -1, z1 + 1, RET_BOLT_R * math.cos(a), RET_BOLT_R * math.sin(a)))
    return ring


TURRET_HUB_R, TURRET_HUB_Z = 20.5, (3.0, 17.0)   # clamp hub under the flange, inside the base hole


def turret_flange():
    """Circular turret flange = inner race, plus a split-clamp hub below it that grips the
    rotating PVC tube (tightened before the turret is lowered onto the balls).
    Union onto the lowered tower (B3). Design frame, built position."""
    g = race_geometry()
    z0, z1, zb = ex.FLANGE_Z[0], ex.FLANGE_Z[1], ex.BALL_Z
    r_apex = g["inner_at_joint"]
    rb = ex.PVC34_OD / 2 + 0.15
    pts = [(rb, z0), (r_apex + (zb - z0), z0), (r_apex, zb), (r_apex + (z1 - zb), z1), (rb, z1)]
    fl = revolve(pts)
    hub = z_cyl(TURRET_HUB_R, TURRET_HUB_Z[0], z0 + 0.5).cut(z_cyl(rb, TURRET_HUB_Z[0] - 1, z1 + 1))
    hub = pinch_clamp(hub, rb, TURRET_HUB_R, TURRET_HUB_Z[0], z0 - 0.5, (TURRET_HUB_Z[0] + z0) / 2, boss=False)
    return fl.union(hub)


def base_race_rim():
    """Lower outer race rim. Union onto the base (B3); M3 nuts slide in from the outside."""
    g = race_geometry()
    z0, z1 = ex.BASE_RIM_Z
    apex = g["outer_at_joint"]
    pts = [(apex - (z1 - z0), z0), (ex.RACE_R[1], z0), (ex.RACE_R[1], z1), (apex, z1)]
    rim = revolve(pts)
    for k in range(N_RET_BOLTS):
        a = math.radians(22.5 + 45 * k)
        x, y = RET_BOLT_R * math.cos(a), RET_BOLT_R * math.sin(a)
        rim = rim.cut(z_cyl(M3 / 2, z0 - 1, z1 + 1, x, y))
        slot = (cq.Workplane("XY").box(12.0, M3_NUT_AF, M3_NUT_H)
                .translate((RET_BOLT_R + 3.0, 0, z0 + 2.5))
                .rotate((0, 0, 0), (0, 0, 1), math.degrees(a)))
        rim = rim.cut(slot)
    return rim


# ---------------------------------------------------------------- conduit end fitting (x2)
def conduit_fitting():
    """Same part at both conduit ends. Local X = design v, local Y = design z above conduit centre.

    Conduit socket on the -Z face; slew holes high, 6 arm holes low; PTFE counterbores
    (tube end stops) and a 1/2" copper elbow socket on the +Z face (used at the pedestal end)."""
    body = cq.Workplane("XY").rect(100, 100).extrude(6).union(z_cyl(42, 0, FIT_T))
    for sx in (-1, 1):
        for sy in (-1, 1):
            body = body.cut(z_cyl(2.3, -1, 7, sx * 40, sy * 40))
    body = body.cut(z_cyl(CONDUIT_OD / 2 + 0.3, -1, 12))
    body = body.cut(z_cyl(COPPER_OD / 2 + 0.2, FIT_T - 8, FIT_T + 1, 0, -20))
    slew = [(-5, 22.0), (5, 22.0)]
    arm = [(x, y) for x in (-4.0, 0.0, 4.0) for y in (-17.8, -22.2)]
    for x, y in slew + arm:
        body = body.cut(z_cyl(ROPE_HOLE / 2, 0, FIT_T + 1, x, y))
        body = body.cut(cq.Workplane("XY").circle(3.5).workplane(offset=2.2).circle(ROPE_HOLE / 2)
                        .loft().translate((x, y, 11.9)))         # bell mouth on the conduit side
    for x, y in [(-4.0, -17.8), (-4.0, -22.2), (4.0, -17.8), (4.0, -22.2)]:
        body = body.cut(z_cyl(PTFE_BORE / 2, FIT_T - 14, FIT_T + 1, x, y))
    return body


# ---------------------------------------------------------------- control drums
def control_drum_rim(pitch, width, r_in):
    prof, rc, rf = groove_profile(pitch, width, r_in)
    return revolve(prof), rc, rf


def tail_anchors(part, rc, r_slot0, r_slot1, z_web_top, width, spread=25.0):
    """Two radial M3 slots (slotted tail anchors = tension adjusters) + rope entry holes."""
    for sgn in (1, -1):
        a = math.radians(90 + sgn * spread)
        mid = (r_slot0 + r_slot1) / 2
        slot = (cq.Workplane("XY").slot2D(r_slot1 - r_slot0 + M3, M3).extrude(40)
                .translate((mid, 0, -20)).rotate((0, 0, 0), (0, 0, 1), math.degrees(a)))
        part = part.cut(slot)
        ae = math.radians(90 + sgn * 8)
        hole = (cq.Workplane("YZ").circle(ROPE_HOLE / 2).extrude(rc + 2).translate((r_slot1 - 2, 0, 0))
                .rotate((0, 0, 0), (0, 0, 1), math.degrees(ae)))
        part = part.cut(hole)
    return part


def lever_hub(name):
    """Printed lever hub: Ø48 drum + sleeve + dowel socket, turns on the common 8-32 axle.

    Local Z = design v. The socket sits at z = handle_v - drum_v; handle points +Y."""
    handle_v, drum_v = ex.LEVERS[name]
    off = handle_v - drum_v
    pitch, width = ex.DRUM["lever"]["pitch"], ex.DRUM["lever"]["width"]
    rim, rc, rf = control_drum_rim(pitch, width, 17.0)
    web = z_cyl(17.5, -width / 2, -width / 2 + 4.0)
    hub = rim.union(web).union(z_cyl(10.0, -width / 2, width / 2))
    blk_h = 20.0
    zc = off
    if abs(off) > width / 2 + blk_h / 2:
        z0, z1 = (width / 2, zc - blk_h / 2) if off > 0 else (zc + blk_h / 2, -width / 2)
        hub = hub.union(z_cyl(10.0, z0, z1))
    block = cq.Workplane("XY").box(22, 45, blk_h).translate((0, 11.5, zc))
    hub = hub.union(block)
    hub = hub.cut(cq.Workplane("XZ").circle(LEVER_SOCKET_D / 2).extrude(-LEVER_SOCKET_DEPTH)
                  .translate((0, 34 - LEVER_SOCKET_DEPTH, zc)))
    hub = hub.cut(x_hole(M3, 30, 24.0, zc))
    hub = hub.cut(z_cyl(BORE / 2, -200, 200))
    hub = tail_anchors(hub, rc, 11.5, 16.0, -width / 2 + 4.0, width)
    return hub


def slew_spool():
    """Wheel spool: Ø110 drum + tube + wheel flange in one part, turns on a fixed 8-32 axle."""
    pitch, width = ex.DRUM["slew"]["pitch"], ex.DRUM["slew"]["width"]
    rim, rc, rf = control_drum_rim(pitch, width, 49.0)
    rim = rim.translate((0, 0, width / 2))
    web = z_cyl(49.5, 0, 5.0)
    tube = z_cyl(SPOOL_TUBE_R, 0, SPOOL_LEN)
    flange = z_cyl(22.0, SPOOL_LEN - 5.0, SPOOL_LEN)
    s = rim.union(web).union(tube).union(flange)
    s = s.cut(z_cyl(BORE / 2, -1, SPOOL_LEN + 1))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        s = s.cut(z_cyl(M3 / 2, SPOOL_LEN - 20, SPOOL_LEN + 1, BOLT_CIRCLE_SPOOL * math.cos(a),
                        BOLT_CIRCLE_SPOOL * math.sin(a)))
    s = s.translate((0, 0, -width / 2))
    s = tail_anchors(s, rc, 30.0, 42.0, 5.0 - width / 2, width, spread=20.0)
    return s.translate((0, 0, width / 2))


def slew_wheel():
    rim = z_cyl(WHEEL_R_OUT, 0, WHEEL_T).cut(z_cyl(WHEEL_R_IN, -1, WHEEL_T + 1))
    rim = rim.edges("not |Z").fillet(3.0)
    w = rim.union(z_cyl(22.0, 0, WHEEL_T))
    for k in range(3):
        a = 90 + 120 * k
        spoke = cq.Workplane("XY").box(WHEEL_R_IN - 18, 10, 8).translate(((WHEEL_R_IN + 18) / 2, 0, 4)) \
            .rotate((0, 0, 0), (0, 0, 1), a)
        w = w.union(spoke)
    w = w.cut(z_cyl(2.6, -1, WHEEL_T + 1))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        x, y = BOLT_CIRCLE_SPOOL * math.cos(a), BOLT_CIRCLE_SPOOL * math.sin(a)
        w = w.cut(z_cyl(M3 / 2, -1, WHEEL_T + 1, x, y)).cut(z_cyl(M3_HEAD_D / 2, WHEEL_T - M3_HEAD_H, WHEEL_T + 1, x, y))
    return w


# ---------------------------------------------------------------- registry
PARTS = {
    # name: (builder, prints, description)
    "boom-drum": (boom_drum, 1, "Ø30 pitch single-groove boom drum"),
    "stick-drum": (stick_drum, 1, "Ø26 pitch single-groove stick drum"),
    "bucket-drum-axle": (bucket_drum_axle, 1, "Ø17 pitch bucket drum with journals and hex ends"),
    "slew-drum": (slew_drum, 1, "Ø110 pitch slew drum on the rotating 3/4in PVC tube"),
    "slewing-ring-retaining-ring": (retaining_ring, 1, "upper outer race, 8 x M3x12"),
    "conduit-end-fitting": (conduit_fitting, 2, "same part at box and pedestal ends of the conduit"),
    "lever-hub-boom": (lambda: lever_hub("boom"), 1, "boom lever hub, drum offset toward centre"),
    "lever-hub-stick": (lambda: lever_hub("stick"), 1, "stick lever hub"),
    "lever-hub-bucket": (lambda: lever_hub("bucket"), 1, "bucket lever hub, drum offset toward centre"),
    "slew-spool": (slew_spool, 1, "wheel spool: Ø110 drum + tube + wheel flange"),
    "slew-wheel": (slew_wheel, 1, "Ø184 horizontal hand wheel"),
}
HELPERS = {"turret-flange": turret_flange, "base-race-rim": base_race_rim}


def build_all(out_dir=ex.OUT, only=None):
    import trimesh
    step_dir, stl_dir = Path(out_dir) / "STEP", Path(out_dir) / "STL"
    step_dir.mkdir(parents=True, exist_ok=True)
    stl_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (fn, n, desc) in PARTS.items():
        if only and name not in only:
            continue
        wp = fn()
        solids = wp.solids().vals()
        shape = wp.val()
        step = step_dir / f"2026-09-24-{name}.step"
        stl = stl_dir / f"2026-09-24-{name}.stl"
        cq.exporters.export(wp, str(step))
        cq.exporters.export(wp, str(stl), tolerance=0.02, angularTolerance=0.1)
        m = trimesh.load(stl, force="mesh")
        bb = shape.BoundingBox()
        rows.append((name, n, len(solids), round(shape.Volume() / 1000, 2), (round(bb.xlen, 1), round(bb.ylen, 1),
                     round(bb.zlen, 1)), m.is_watertight, desc))
    return rows


if __name__ == "__main__":
    only = sys.argv[1:] or None
    rows = build_all(only=only)
    print(f"{'part':30s} {'qty':>3s} {'solids':>6s} {'cm3':>7s}  {'bbox mm':22s} watertight")
    for r in rows:
        print(f"{r[0]:30s} {r[1]:3d} {r[2]:6d} {r[3]:7.2f}  {str(r[4]):22s} {r[5]}")
