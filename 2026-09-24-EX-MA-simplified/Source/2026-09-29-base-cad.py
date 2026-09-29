#!/usr/bin/env python3
"""Base (lower race) and slewing-ring retaining ring as native CAD solids.

The printed base so far was the original EX-MA base mesh with the race rim unioned on, so its STEP
was a converted mesh: the 45 deg ball-race cone came out as a row of flat facets. This rebuilds the
base from its measured dimensions as one CadQuery solid (revolved body, pockets, ribs, holes):
every round wall is a cylinder and the race is one conical face.

Changes against the current base (everything that mates stays where it is):
  - 45 deg support under the race rim: the rim's underside hung 5.4 mm out over the outer pockets
    at z 15; a revolved 45 deg fillet (r 57.455 / z 15 -> r 62.88 / z 9.575) makes it print without
    supports.
  - the 4 unused mounting holes of the original base (Ø5.2 at r 62, 45 deg, with a Ø10 recess cut
    into the outer wall) are filled: solid Ø10 bosses on the 45 deg ribs.
  - the small V groove where the rim met the old base wall (r 68.6 .. 70, z 14.2 .. 15) is gone;
    the outer wall is r 70 all the way up (the old wall was r 69.93 below the rim).

Kept: bore r 23; inner ring wall r 23 .. 25.5; inner pockets r 25.5 .. 37.92 and outer pockets
r 48.86 .. 62.88, floors at z 4; ribs at 0/90/180/270 deg (5.86 wide) and 45 deg (6.0 wide);
middle ring top z 15 with the raised band r 40.95 .. 45.93 to z 16.2; race rim r 57.455 .. 70,
z 15 .. 21 with the 45 deg race cone; 8 x M3 holes on r 66.8 (22.5 + 45 k deg) with side nut slots;
4 x #8 wood-screw holes Ø4.4 at r 38 (45 deg) with Ø8.4 counterbores from z 12.5.

The retaining ring was already a CadQuery solid (2026-09-24-build-parts.py); it is exported again
here with the base, unchanged.

Writes STEP/ and STL/ 2026-09-29-base and 2026-09-29-slewing-ring-retaining-ring (base in the design
frame as before: bottom on z = 0, axis on z; ring in its print frame, bottom face on z = 0).
"""
import importlib.util
import math
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
DATE = "2026-09-29"
V = cq.Vector


def _load(name, fn):
    s = importlib.util.spec_from_file_location(name, HERE / fn)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


bp = _load("parts", "2026-09-24-build-parts.py")
ex = bp.ex

# ---------------------------------------------------------------- dimensions (mm)
R_OUT = ex.RACE_R[1]                 # 70: outer wall and rim
R_BORE = 23.0                        # centre bore (turret clamp hub r 20.5 turns inside)
R_IN_WALL = 25.5                     # inner ring wall
R_MID = (37.92, 48.86)               # middle ring (solid) between the two pocket rings
R_OUT_WALL = 62.88                   # outer pockets end here
Z_FLOOR = 4.0                        # pocket floors
Z_TOP = ex.BASE_TOP_Z                # 15: ring / wall tops, rim underside
BAND_R, BAND_TOP = (40.95, 45.93), 16.2
RIB_AXIS_W, RIB_DIAG_W = 5.86, 6.0   # ribs at 0/90/180/270 and at 45/135/225/315 deg
OUTER_BOSS_R, OUTER_BOSS_AT = 5.0, 62.0     # filled bosses where the old Ø5.2 holes were
SCREW_R, SCREW_HOLE_D, SCREW_CB_D, SCREW_CB_Z = 38.0, 4.4, 8.4, Z_TOP - 2.5
g = bp.race_geometry()
RIM_Z = ex.BASE_RIM_Z                # (15, 21)
CONE_TOP_R = g["outer_at_joint"]     # 63.455 at z 21
CONE_BOT_R = CONE_TOP_R - (RIM_Z[1] - RIM_Z[0])   # 57.455 at z 15 (45 deg)
SUPPORT_Z = Z_TOP - (R_OUT_WALL - CONE_BOT_R)     # 9.575: 45 deg fillet under the rim


def revolve(pts):
    """Closed (r, z) polygon revolved about z."""
    return (cq.Workplane("XZ").polyline(pts).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)).val())


def z_cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Solid.makeCylinder(r, z1 - z0, V(x, y, z0), V(0, 0, 1))


def rib(ang_deg, width, z0, z1):
    """Straight rib through the centre along ang_deg (both directions)."""
    b = cq.Solid.makeBox(2 * (R_OUT + 5), width, z1 - z0, V(-(R_OUT + 5), -width / 2, z0))
    return b.rotate(V(0, 0, 0), V(0, 0, 1), ang_deg)


def base():
    # body of revolution: floor + walls + rings to z 15, race rim with its 45 deg cone, raised band
    body = revolve([(R_BORE, 0.0), (R_OUT, 0.0), (R_OUT, RIM_Z[1]), (CONE_TOP_R, RIM_Z[1]),
                    (CONE_BOT_R, RIM_Z[0]), (R_BORE, Z_TOP)])
    body = body.fuse(revolve([(BAND_R[0], Z_TOP - 0.5), (BAND_R[1], Z_TOP - 0.5), (BAND_R[1], BAND_TOP),
                              (BAND_R[0], BAND_TOP)]))
    # pockets: two annuli from the floor up to z 15, minus the ribs, the outer bosses and the
    # 45 deg support under the rim
    pockets = (z_cyl(R_MID[0], Z_FLOOR, Z_TOP).cut(z_cyl(R_IN_WALL, Z_FLOOR - 1, Z_TOP + 1))
               .fuse(z_cyl(R_OUT_WALL, Z_FLOOR, Z_TOP).cut(z_cyl(R_MID[1], Z_FLOOR - 1, Z_TOP + 1))))
    for k in range(4):
        pockets = pockets.cut(rib(90.0 * k, RIB_AXIS_W, Z_FLOOR - 1, Z_TOP + 1))
        pockets = pockets.cut(rib(45.0 + 90.0 * k, RIB_DIAG_W, Z_FLOOR - 1, Z_TOP + 1))
        a = math.radians(45.0 + 90.0 * k)
        pockets = pockets.cut(z_cyl(OUTER_BOSS_R, Z_FLOOR - 1, Z_TOP + 1,
                                    OUTER_BOSS_AT * math.cos(a), OUTER_BOSS_AT * math.sin(a)))
    pockets = pockets.cut(revolve([(CONE_BOT_R, Z_TOP + 1), (R_OUT_WALL + 1, Z_TOP + 1),
                                   (R_OUT_WALL + 1, SUPPORT_Z - 1), (CONE_BOT_R, Z_TOP)]))
    body = body.cut(pockets)
    # #8 wood screws to the pedestal top: Ø4.4 through, Ø8.4 counterbore from z 12.5
    for k in range(4):
        a = math.radians(45.0 + 90.0 * k)
        x, y = SCREW_R * math.cos(a), SCREW_R * math.sin(a)
        body = body.cut(z_cyl(SCREW_HOLE_D / 2, -1.0, BAND_TOP + 1, x, y))
        body = body.cut(z_cyl(SCREW_CB_D / 2, SCREW_CB_Z, BAND_TOP + 1, x, y))
    # retaining-ring bolts: M3 through the rim, nut slot from the outside
    for k in range(bp.N_RET_BOLTS):
        a = 22.5 + 45.0 * k
        x, y = bp.RET_BOLT_R * math.cos(math.radians(a)), bp.RET_BOLT_R * math.sin(math.radians(a))
        body = body.cut(z_cyl(bp.M3 / 2, RIM_Z[0] - 1, RIM_Z[1] + 1, x, y))
        slot = cq.Solid.makeBox(12.0, bp.M3_NUT_AF, bp.M3_NUT_H,
                                V(bp.RET_BOLT_R + 3.0 - 6.0, -bp.M3_NUT_AF / 2, RIM_Z[0] + 2.5 - bp.M3_NUT_H / 2))
        body = body.cut(slot.rotate(V(0, 0, 0), V(0, 0, 1), a))
    return body.clean()


def export(shape, name):
    step = OUT / "STEP" / f"{DATE}-{name}.step"
    stl = OUT / "STL" / f"{DATE}-{name}.stl"
    cq.exporters.export(shape, str(step))
    cq.exporters.export(shape, str(stl), tolerance=0.01, angularTolerance=0.05)
    return step, stl


def main():
    b = base()
    ring = bp.retaining_ring()
    ring = ring.val() if isinstance(ring, cq.Workplane) else ring
    for name, s in (("base", b), ("slewing-ring-retaining-ring", ring)):
        faces = {}
        for f in s.Faces():
            faces[f.geomType()] = faces.get(f.geomType(), 0) + 1
        step, stl = export(s, name)
        back = cq.importers.importStep(str(step)).solids().vals()
        print(f"{name}: valid {s.isValid()}, solids {len(s.Solids())}, volume {s.Volume():.1f} mm3, faces {faces}; "
              f"STEP read back: {len(back)} solid(s), valid {all(x.isValid() for x in back)} -> {step.name}, {stl.name}")


if __name__ == "__main__":
    main()
