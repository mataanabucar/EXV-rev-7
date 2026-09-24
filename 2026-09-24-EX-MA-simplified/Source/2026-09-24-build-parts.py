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
PTFE_SLIDE = 4.6                 # loose bore: the PTFE tube slides through

# drum keying: an M3 screw threads into each drum face; its head sits in a socket in the
# member's inner wall (the drum turns with its own member). Angle in the drum print frame.
# two key positions per drum (180 deg apart): with split pins nothing passes through the drum
BOOM_DRIVE_R, BOOM_DRIVE_ANGS = 9.0, (-60.0, 120.0)
STICK_DRIVE_R, STICK_DRIVE_ANGS = 7.2, (-30.0, 150.0)
M3_TAP = 2.6                     # pilot hole for an M3 screw in plastic
CLAMP_SLIT = 1.5

AXLE_JOURNAL_D = 12.2            # turns in the existing Ø12.7 hole in the stick nose (no change to the stick)
AXLE_HEX_AF = 12.0               # hex ends keyed into bucket ears G/H
AXLE_Z = dict(drum=5.0, cone=9.5, journal=18.9, hex=24.5)   # half-lengths along the axle

SLEW_HUB_R, SLEW_BORE = 15.0, ex.TURRET_TUBE_OD + 0.3   # 3/4" PEX-B OD 22.23
LEVER_SOCKET_D, LEVER_SOCKET_DEPTH = 16.2, 25.0   # 5/8" hardwood dowel handle
SPOOL_TUBE_R, SPOOL_LEN = 12.0, 145.0
WHEEL_R_OUT, WHEEL_R_IN, WHEEL_T = 92.0, 78.0, 12.0
BOLT_CIRCLE_SPOOL = 16.0
AXLE_BORE = ex.LEVER_AXLE_D + 0.36   # 8.3 for the 5/16" rod (lever axle, slew spool axle)
HUB_CORE_R = 10.0
TURRET_TUBE_BORE = ex.TURRET_TUBE_OD + 0.4   # loose (bushing, pedestal top)

CONDUIT_OD = 60.3                # 2" sch40 PVC
COPPER_OD = ex.COPPER_OD         # 1/2" copper
FIT_T = ex.FIT_T

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


def two_lane_profile(pitch, width, r_in, lip=2.5, flange_t=1.0, ridge=0.4):
    """(r, z) profile of a two-lane drum rim centred on z = 0: one rope per lane, lanes at
    +-(ridge/2 + lip + floor/2); 45 deg walls. Returns (profile, rc, rf, lane_z)."""
    rc = pitch / 2 - ROPE / 2
    rf = rc + lip
    w2 = width / 2
    floor = w2 - flange_t - 2 * lip - ridge / 2
    zA = ridge / 2 + lip + floor / 2
    pts = [(r_in, -w2), (rf, -w2), (rf, -w2 + flange_t), (rc, -w2 + flange_t + lip), (rc, -ridge / 2 - lip),
           (rf, -ridge / 2), (rf, ridge / 2), (rc, ridge / 2 + lip), (rc, w2 - flange_t - lip),
           (rf, w2 - flange_t), (rf, w2), (r_in, w2)]
    return pts, rc, rf, zA


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
def joint_drum(pitch, width, lip, drive_r, drive_angs):
    """Boom / stick drum: single groove, crimp pocket, two M3 key-screw pilots, no pin bore.

    The joint pin is split into two short rods (the PTFE tubes cross the joint axis), so the
    drum is carried by 4 M3 screws - two per face - whose heads sit in sockets in the member's
    inner walls. The drum turns with its own member."""
    prof, rc, rf = groove_profile(pitch, width, 0.0, lip=lip)
    d = revolve(prof)
    d = d.cut(crimp_pocket(rc, rc - 4.5, 90.0, rf))
    for ang in drive_angs:
        a = math.radians(ang)
        d = d.cut(z_cyl(M3_TAP / 2, -width, width, drive_r * math.cos(a), drive_r * math.sin(a)))
    return d


def boom_drum():
    return joint_drum(ex.DRUM["boom"]["pitch"], ex.DRUM["boom"]["width"], 3.3, BOOM_DRIVE_R, BOOM_DRIVE_ANGS)


def stick_drum():
    return joint_drum(ex.DRUM["stick"]["pitch"], ex.DRUM["stick"]["width"], 2.9, STICK_DRIVE_R, STICK_DRIVE_ANGS)


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
    """Ø110 pitch two-lane drum clamped on the rotating 3/4" PEX tube by an M3 pinch bolt.

    One rope per lane, each ending in a single crimp seated in a pocket half a turn from where
    it leaves the drum, so each rope keeps 90-270 deg of wrap over the +-90 deg slew range."""
    pitch, width = ex.DRUM["slew"]["pitch"], ex.DRUM["slew"]["width"]
    prof, rc, rf, zl = two_lane_profile(pitch, width, 49.0)
    assert abs(zl - ex.SLEW_LANE_OFF) < 0.05
    rim = revolve(prof)
    web = z_cyl(49.5, -width / 2, -width / 2 + 5.0)
    hub = z_cyl(SLEW_HUB_R, -width / 2, 23.0)
    d = rim.union(web).union(hub)
    d = d.cut(z_cyl(SLEW_BORE / 2, -20, 30))
    for sign, z in ((1, zl), (-1, -zl)):                  # lane A (+v strand) upper, lane B lower
        a = ex.pedestal_slew_line(sign)["tangent_deg"] - sign * 180.0
        d = d.cut(crimp_pocket(rc, rc - 4.5, a, rf).translate((0, 0, z)))
    # split clamp on the PEX tube (pinch bolt outside the tube bore - cables run inside the tube)
    d = pinch_clamp(d, SLEW_BORE / 2, SLEW_HUB_R, -width / 2 + 6.0, 23.0, 14.0)
    return d


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
    rotating PEX tube (tightened before the turret is lowered onto the balls).
    Union onto the lowered tower (B3). Design frame, built position."""
    g = race_geometry()
    z0, z1, zb = ex.FLANGE_Z[0], ex.FLANGE_Z[1], ex.BALL_Z
    r_apex = g["inner_at_joint"]
    rb = ex.TURRET_TUBE_OD / 2 + 0.15
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
def conduit_fitting(end):
    """Conduit end fitting; end = 'box' or 'pedestal'. Local X = design v, local Y = design z above
    the conduit centre. Conduit socket on the -Z face; slew holes high, 6 arm holes low.

    Slew: each slew rope runs in its own PTFE sleeve from a post beside the box spool to the
    pedestal fitting. Box end: loose Ø4.6 pass-through. Pedestal end: angled counterbore (sleeve
    anchor) aimed along the pedestal drum's tangent, so the rope leaves the fitting unbent.

    Hole columns follow design v on both ends (the two fittings face opposite ways, so local x
    is mirrored): boom +v, stick centre, bucket -v, matching the lever drums' order so no ropes
    cross in the box. Each circuit's two strands use the two rows (y -17.8 / -22.2).

    The PTFE tubes run the whole way from the box fitting to their stop bosses in the arm:
      box:      the 4 tubes come out of the conduit and seat in 10 mm counterbores on the conduit
                side (tube anchor); only the ropes continue into the box.
      pedestal: the 4 tubes slide through loose Ø4.6 bores into the 1/2" copper elbow socket on
                the +Z face (the tubes' length change is stored as spare length in the conduit)."""
    body = cq.Workplane("XY").rect(100, 100).extrude(6).union(z_cyl(42, 0, FIT_T))
    for sx in (-1, 1):
        for sy in (-1, 1):
            body = body.cut(z_cyl(2.3, -1, 7, sx * 40, sy * 40))
    body = body.cut(z_cyl(CONDUIT_OD / 2 + 0.3, -1, 12))
    # pedestal fitting sits on the conduit line (v = PED_FIT_V); its copper socket and arm holes
    # are offset so the elbow rises on the slew axis (v = 0)
    x0 = -ex.PED_FIT_V if end == "pedestal" else 0.0
    if end == "pedestal":
        body = body.cut(z_cyl(COPPER_OD / 2 + 0.2, FIT_T - 8, FIT_T + 1, x0, -20))
    xs = -1.0 if end == "box" else 1.0             # local x of design +v (box: local X = -v)
    col = dict(boom=x0 + 4.0 * xs, stick=x0, bucket=x0 - 4.0 * xs)
    tubes = [(col[c], y) for c in ("stick", "bucket") for y in ex.FIT_ARM_ROWS]
    ropes_only = [(col["boom"], y) for y in ex.FIT_ARM_ROWS]
    body = slew_sleeve_holes(body, end)
    for x, y in ropes_only + (tubes if end == "box" else []):
        body = body.cut(z_cyl(ROPE_HOLE / 2, 0, FIT_T + 1, x, y))
    bell = lambda x, y, z: body.cut(cq.Workplane("XY").circle(3.5).workplane(offset=2.2).circle(ROPE_HOLE / 2)
                                    .loft().translate((x, y, z)))
    for x, y in ropes_only:
        body = bell(x, y, 11.9)                           # bell mouth on the conduit side
    if end == "box":
        for x, y in ropes_only + tubes:                   # and on the box side: ropes fan out to the drums
            body = body.cut(cq.Workplane("XY").circle(ROPE_HOLE / 2).workplane(offset=2.2).circle(3.5)
                            .loft().translate((x, y, FIT_T - 2.2 + 0.01)))
    if end == "box":
        for x, y in tubes:
            body = body.cut(z_cyl(PTFE_BORE / 2, 11, 22, x, y))          # tube end stop, from the conduit side
    else:
        # the four tubes touch each other, so they slide through one rounded window (separate
        # Ø4.6 bores 4 mm apart would merge around a loose pillar)
        xc = (col["stick"] + col["bucket"]) / 2
        w, h = abs(col["stick"] - col["bucket"]) + PTFE_SLIDE, 4.4 + PTFE_SLIDE
        win = cq.Workplane("XY").rect(w, h).extrude(FIT_T + 2).edges("|Z").fillet(PTFE_SLIDE / 2 - 0.05)
        body = body.cut(win.translate((xc, -20.0, -1)))
    return body


def slew_sleeve_holes(body, end):
    y = ex.FIT_SLEW_Y
    for sign in (1, -1):                                  # design +v / -v strand
        if end == "box":
            x = -sign * ex.FIT_SLEW_X
            body = body.cut(z_cyl(PTFE_SLIDE / 2, -1, FIT_T + 1, x, y))
            for z0, r0, r1 in ((ex.CONDUIT_SOCKET - 0.01, 3.8, PTFE_SLIDE / 2), (FIT_T - 2.0 + 0.01, PTFE_SLIDE / 2, 3.8)):
                body = body.cut(cq.Workplane("XY").circle(r0).workplane(offset=2.0).circle(r1).loft()
                                .translate((x, y, z0)))
        else:
            g = math.degrees(ex.pedestal_slew_line(sign)["gamma"])
            x, z0 = sign * ex.FIT_SLEW_X, ex.CONDUIT_SOCKET
            cb = z_cyl(PTFE_BORE / 2, -2.0, 11.0).union(z_cyl(ROPE_HOLE / 2, -2.0, 30.0))
            body = body.cut(cb.rotate((0, 0, 0), (0, 1, 0), sign * g).translate((x, y, z0)))
    return body


# ---------------------------------------------------------------- control drums
def control_drum_rim(pitch, width, r_in):
    prof, rc, rf = groove_profile(pitch, width, r_in)
    return revolve(prof), rc, rf


def slot_anchor(part, rc, angle_deg, hole_dir, r0, r1, z_slot, z_hole):
    """Slotted M3 tail anchor (tension adjuster): a radial slot through the web at angle_deg, and a
    rope hole from the slot's outer end through the rim into the groove, 8 deg along hole_dir."""
    mid = (r0 + r1) / 2
    slot = (cq.Workplane("XY").slot2D(r1 - r0 + M3, M3).extrude(z_slot[1] - z_slot[0])
            .translate((mid, 0, z_slot[0])).rotate((0, 0, 0), (0, 0, 1), angle_deg))
    part = part.cut(slot)
    hole = (cq.Workplane("YZ").circle(ROPE_HOLE / 2).extrude(rc + 3.0 - (r1 - 2.0)).translate((r1 - 2.0, 0, z_hole))
            .rotate((0, 0, 0), (0, 0, 1), angle_deg + hole_dir * 8.0))
    return part.cut(hole)


def lever_hub(name):
    """Printed lever hub: Ø60 single-groove drum + sleeve + dowel socket, turns on the common
    5/16" rod. Local Z = design v - drum v; the handle points local +Y (up); local +X = design -u.

    - Sleeves run to LEVER_HUB_V so the three hubs and the two bearing blocks stack 0.5 mm apart.
    - Drag clamp: a slit on the -Y side of the handle block and an M3 across it squeeze the rod;
      it sets each lever's own holding friction.
    - Tail anchors sit at the back of the drum (design 180 +- 25 deg): the strands leave toward
      the conduit mouth in front and below, so each wraps 45-110 deg over the lever swing."""
    handle_v, drum_v = ex.LEVERS[name]
    off = handle_v - drum_v
    z0, z1 = (v - drum_v for v in ex.LEVER_HUB_V[name])
    pitch, width = ex.DRUM["lever"]["pitch"], ex.DRUM["lever"]["width"]
    r_in = pitch / 2 - ROPE / 2 - 6.0                 # 6 mm rim under the groove
    rim, rc, rf = control_drum_rim(pitch, width, r_in)
    web = z_cyl(r_in + 0.5, -width / 2, -width / 2 + 4.0)
    hub = rim.union(web).union(z_cyl(HUB_CORE_R, z0, z1))
    blk_h = 20.0
    hub = hub.union(cq.Workplane("XY").box(22, 50, blk_h).translate((0, 9.0, off)))
    hub = hub.intersect(cq.Workplane("XY").box(200, 200, z1 - z0).translate((0, 0, (z0 + z1) / 2)))
    hub = hub.cut(cq.Workplane("XZ").circle(LEVER_SOCKET_D / 2).extrude(-LEVER_SOCKET_DEPTH)
                  .translate((0, 34 - LEVER_SOCKET_DEPTH, off)))
    hub = hub.cut(x_hole(M3, 30, 24.0, off))                       # dowel cross-pin
    hub = hub.cut(z_cyl(AXLE_BORE / 2, -200, 200))
    # drag clamp
    slit_y0, slit_y1 = -AXLE_BORE / 2 + 0.5, -17.0
    hub = hub.cut(cq.Workplane("XY").box(CLAMP_SLIT, slit_y0 - slit_y1, blk_h + 1)
                  .translate((0, (slit_y0 + slit_y1) / 2, off)))
    yb = -10.5
    hub = hub.cut(x_hole(M3, 30, yb, off))
    hub = hub.cut(cq.Workplane("YZ").circle(M3_HEAD_D / 2).extrude(12).translate((7.0, yb, off)))
    hub = hub.cut(cq.Workplane("YZ").polygon(6, M3_NUT_AF / math.cos(math.pi / 6)).extrude(12)
                  .translate((-19.0, yb, off)))
    # tail anchors: local angle 0 = design rear; upper strand at +25, lower strand at -25
    zs = (-width / 2 - 1.0, -width / 2 + 5.0)
    for a, hd in ((25.0, 1), (-25.0, -1)):
        hub = slot_anchor(hub, rc, a, hd, 12.0, r_in - 3.0, zs, 0.0)
    return hub


def slew_spool():
    """Box slew spool: Ø110 two-lane drum + tube + wheel flange in one part, turning on a fixed
    5/16" rod. Each lane's rope ends in a double-crimp loop on a slotted M3 anchor (tension
    adjuster) half a turn from where it leaves the spool."""
    pitch, width = ex.DRUM["slew"]["pitch"], ex.DRUM["slew"]["width"]
    prof, rc, rf, zl = two_lane_profile(pitch, width, 49.0)
    rim = revolve(prof).translate((0, 0, width / 2))
    web = z_cyl(49.5, 0, 4.0)
    tube = z_cyl(SPOOL_TUBE_R, 0, SPOOL_LEN)
    flange = z_cyl(22.0, SPOOL_LEN - 5.0, SPOOL_LEN)
    s = rim.union(web).union(tube).union(flange)
    s = s.cut(z_cyl(AXLE_BORE / 2, -1, SPOOL_LEN + 1))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        s = s.cut(z_cyl(M3 / 2, SPOOL_LEN - 20, SPOOL_LEN + 1, BOLT_CIRCLE_SPOOL * math.cos(a),
                        BOLT_CIRCLE_SPOOL * math.sin(a)))
    dep = ex.spool_departures()
    # lane A rope leaves at dep A heading +SPOOL_DEPART (clockwise sense) and lies on the far arc;
    # its anchor sits at lane B's departure point, and vice versa
    s = slot_anchor(s, rc, dep["B"]["tangent_deg"], -1, 30.0, 42.0, (-1.0, 5.0), width / 2 + zl)
    s = slot_anchor(s, rc, dep["A"]["tangent_deg"], +1, 30.0, 42.0, (-1.0, 5.0), width / 2 - zl)
    return s


def slew_wheel():
    rim = z_cyl(WHEEL_R_OUT, 0, WHEEL_T).cut(z_cyl(WHEEL_R_IN, -1, WHEEL_T + 1))
    rim = rim.edges("not |Z").fillet(3.0)
    w = rim.union(z_cyl(22.0, 0, WHEEL_T))
    for k in range(3):
        a = 90 + 120 * k
        spoke = cq.Workplane("XY").box(WHEEL_R_IN - 18, 10, 8).translate(((WHEEL_R_IN + 18) / 2, 0, 4)) \
            .rotate((0, 0, 0), (0, 0, 1), a)
        w = w.union(spoke)
    w = w.cut(z_cyl(AXLE_BORE / 2, -1, WHEEL_T + 1))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        x, y = BOLT_CIRCLE_SPOOL * math.cos(a), BOLT_CIRCLE_SPOOL * math.sin(a)
        w = w.cut(z_cyl(M3 / 2, -1, WHEEL_T + 1, x, y)).cut(z_cyl(M3_HEAD_D / 2, WHEEL_T - M3_HEAD_H, WHEEL_T + 1, x, y))
    return w


# ---------------------------------------------------------------- box / pedestal supports
SCREW6_CLEAR = 3.8                # #6 wood screw clearance


def slew_tube_bushing():
    """Flanged plain bushing for the PEX turret tube in the pedestal shelf (just above the slew
    drum): takes the slew ropes' side pull off the slewing ring. Flange down on the bed."""
    b = z_cyl(22.0, 0, 3.0).union(z_cyl(15.0, 0, 3.0 + ex.T_WOOD))
    b = b.cut(z_cyl(TURRET_TUBE_BORE / 2, -1, 20))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        b = b.cut(z_cyl(SCREW6_CLEAR / 2, -1, 4, 18.5 * math.cos(a), 18.5 * math.sin(a)))
    return b


ELBOW_SUPPORT_H = ex.Z_ARM_LAYER - COPPER_OD / 2 - ex.PED_Z[0]   # sandbox floor -> copper underside


def elbow_support():
    """Post under the horizontal leg of the 1/2" copper elbow; a cable tie through the saddle holds
    the elbow down against the ropes' pull at the 90 deg turn."""
    h = ELBOW_SUPPORT_H
    p = cq.Workplane("XY").box(44, 24, 4).translate((0, 0, 2))
    p = p.union(cq.Workplane("XY").box(20, 16, h + 5).translate((0, 0, (h + 5) / 2)))
    p = p.cut(cq.Workplane("YZ").circle(COPPER_OD / 2 + 0.2).extrude(30).translate((-15, 0, h + COPPER_OD / 2)))
    p = p.cut(cq.Workplane("XY").box(20 + 2, 3.0, 5.0).translate((0, 0, h - 5.0)))        # cable-tie slot
    for sx in (-1, 1):
        p = p.cut(z_cyl(SCREW6_CLEAR / 2, -1, 5, sx * 16.0, 0))
    return p


SPOOL_RISER_H = (ex.Z_SLEW_LAYER - ex.DRUM["slew"]["width"] / 2 - 0.5) - (ex.BOX_Z[0] + ex.T_WOOD)


def spool_riser():
    """Fixed column from the box floor to just under the slew spool; the 5/16" spool axle passes
    through it (a washer between riser and spool)."""
    r = z_cyl(26.0, 0, 4.0).union(z_cyl(14.0, 0, SPOOL_RISER_H))
    r = r.cut(z_cyl(AXLE_BORE / 2, -1, SPOOL_RISER_H + 1))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        r = r.cut(z_cyl(SCREW6_CLEAR / 2, -1, 5, 21.0 * math.cos(a), 21.0 * math.sin(a)))
    return r


SLEEVE_POST_H = ex.Z_SLEW_LAYER - (ex.BOX_Z[0] + ex.T_WOOD)     # box floor -> slew mid-plane


def slew_tube_post():
    """Post beside the box spool holding the end of one slew PTFE sleeve on the spool tangent
    (x2). Local +X = toward the spool; the sleeve seats in a counterbore from -X."""
    h = SLEEVE_POST_H
    p = cq.Workplane("XY").box(24, 36, 4).translate((0, 0, 2))
    p = p.union(cq.Workplane("XY").box(16, 16, h + 8).translate((0, 0, (h + 8) / 2)))
    p = p.cut(cq.Workplane("YZ").circle(PTFE_BORE / 2).extrude(12).translate((-8.5, 0, h)))
    p = p.cut(cq.Workplane("YZ").circle(ROPE_HOLE / 2).extrude(20).translate((-10, 0, h)))
    p = p.cut(cq.Workplane("YZ").circle(ROPE_HOLE / 2).workplane(offset=2.0).circle(3.2).loft()
              .translate((8.0 - 2.0 + 0.01, 0, h)))                                # bell toward the spool
    for sy in (-1, 1):
        p = p.cut(z_cyl(SCREW6_CLEAR / 2, -1, 5, 0, sy * 13.0))
    return p


# ---------------------------------------------------------------- registry
PARTS = {
    # name: (builder, prints, description)
    "boom-drum": (boom_drum, 1, "Ø30 pitch single-groove boom drum"),
    "stick-drum": (stick_drum, 1, "Ø26 pitch single-groove stick drum"),
    "bucket-drum-axle": (bucket_drum_axle, 1, "Ø17 pitch bucket drum with journals and hex ends"),
    "slew-drum": (slew_drum, 1, "Ø110 pitch two-lane slew drum on the rotating 3/4in PEX turret tube"),
    "slewing-ring-retaining-ring": (retaining_ring, 1, "upper outer race, 8 x M3x12"),
    "conduit-end-fitting-box": (lambda: conduit_fitting("box"), 1, "box end of the conduit: PTFE tube anchors"),
    "conduit-end-fitting-pedestal": (lambda: conduit_fitting("pedestal"), 1,
                                     "pedestal end: PTFE tubes slide through into the copper elbow"),
    "lever-hub-boom": (lambda: lever_hub("boom"), 1, "boom lever hub + drag clamp, drum offset toward centre"),
    "lever-hub-stick": (lambda: lever_hub("stick"), 1, "stick lever hub + drag clamp"),
    "lever-hub-bucket": (lambda: lever_hub("bucket"), 1, "bucket lever hub + drag clamp, drum offset toward centre"),
    "slew-spool": (slew_spool, 1, "wheel spool: Ø110 two-lane drum + tube + wheel flange"),
    "slew-wheel": (slew_wheel, 1, "Ø184 horizontal hand wheel"),
    "slew-tube-bushing": (slew_tube_bushing, 1, "PEX turret-tube bushing in the pedestal shelf"),
    "elbow-support": (elbow_support, 1, "post + cable-tie saddle under the copper elbow"),
    "spool-riser": (spool_riser, 1, "column from the box floor up to the slew spool"),
    "slew-tube-post": (slew_tube_post, 2, "slew PTFE sleeve anchor beside the spool"),
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
