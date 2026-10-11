#!/usr/bin/env python3
"""Build the source tree for the EX-MA *minimal* design (no PVC conduit), as built from:
    3 x 7/16in OSB 2x4 ft panels, 1 x 5/8in particle board 2x2 ft (sandbox floor), no shim,
    the printed parts as already printed (old lever hubs, old 145 mm slew spool).

It copies Source/*.py into <work>/root/2026-09-24-EX-MA-simplified/Source, links STL/, STEP/, 3MF/,
Validation/ and References/ (read only), and appends the overrides below to the copied
2026-09-24-exma_common.py, so every build script (panels, placements, hardware, rope paths) runs
unchanged on the minimal geometry. Three small patches:
  - build-box.py: the sandbox floor gets its own thickness (5/8in particle board)
  - assembly.py: the elbow support sits 4 mm lower (its 4 mm base plate is sawn off)
  - build-box.py + solid-hardware.py: the left box-to-sandbox bolt moves 8 mm left (clears the spacers)

Usage: <cadenv>/bin/python 2026-10-11-make-minimal-source.py <work_dir>
Prints the path of the minimal Source directory.
"""
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]                       # 2026-09-24-EX-MA-simplified
ROOT = PROJ.parent

OVERRIDES = '''

# ===================================================================== MINIMAL DESIGN OVERRIDES
# (appended by 2026-10-11-make-minimal-source.py)
T_WOOD = 7 / 16 * 25.4                 # 7/16in OSB
SB_FLOOR_T = 5 / 8 * 25.4              # 5/8in particle board sandbox floor
GROUND = -202.0                        # box floor bottom = sandbox floor bottom (no shim)
SPACER_N = 2                           # two OSB spacer frames replace the 2in PVC conduit
PED_U = (-110.0, 78.0)                 # pedestal +u side 12 mm shorter (drum to wall 9.3 mm)
PED_Z = (GROUND + SB_FLOOR_T, 0.0)     # pedestal top stays at z 0 (walls 5/32in shorter)
SB_Z = (GROUND + SB_FLOOR_T, 40.0)     # sandbox rim stays at z 40
SB_U = (PED_U[0] - (SPACER_N + 1) * T_WOOD, PED_U[0] - (SPACER_N + 1) * T_WOOD + 610.0)
# compact control box depth / height (2026-09-28 spec), kept prints: old hubs (handles +-70),
# old axle blocks and the old 145 mm spool at its old place -> box 15in wide
BOX_U = (SB_U[0] - 214.0, SB_U[0])
BOX_V = (-266.0, 115.0)
BOX_Z = (GROUND, -46.0)
AXLE_U = BOX_U[1] - 157.0              # same distance behind the box front as in the design
WHEEL_C = (BOX_U[1] - 137.0, -190.0)
MOUTH_U = BOX_U[1] - 7.0
HANDLE_LEN = 140.0                     # knob stays 61 mm above the (lower) lid
'''


def main():
    work = Path(sys.argv[1]).resolve()
    root = work / "root"
    proj = root / PROJ.name
    src = proj / "Source"
    if src.exists():
        shutil.rmtree(src)
    src.mkdir(parents=True)
    for name in ("STL", "STEP", "3MF", "Validation"):
        link = proj / name
        if not link.exists():
            os.symlink(PROJ / name, link)
    if not (root / "References").exists():
        os.symlink(ROOT / "References", root / "References")
    for f in (PROJ / "Source").glob("*.py"):
        shutil.copy(f, src / f.name)
    ec = src / "2026-09-24-exma_common.py"
    ec.write_text(ec.read_text() + OVERRIDES)
    bb = src / "2026-09-24-build-box.py"
    s = bb.read_text()
    a = 'P.append(Panel("sandbox floor", "sandbox", (su0, sv0, sz0 - T), (su1, sv1, sz0),'
    assert a in s
    bb.write_text(s.replace(a, 'P.append(Panel("sandbox floor", "sandbox", (su0, sv0, sz0 - ex.SB_FLOOR_T), (su1, sv1, sz0),'))
    # left box-to-sandbox bolt 8 mm further left: at v 90 its nut would land on the spacer frames' edge
    a = "(u1 - T / 2, v1 - 25.0, z0 + T + 25.0)"
    s = bb.read_text()
    assert a in s
    bb.write_text(s.replace(a, "(u1 - T / 2, v1 - 17.0, z0 + T + 25.0)"))
    hw = src / "2026-09-28-solid-hardware.py"
    s = hw.read_text()
    a = '(ex.BOX_V[1] - 25.0, "left")'
    assert a in s
    hw.write_text(s.replace(a, '(ex.BOX_V[1] - 17.0, "left")'))
    asm = src / "2026-09-24-assembly.py"
    s = asm.read_text()
    a = '(ELBOW_SUPPORT_U, 0.0, ex.PED_Z[0])'
    assert a in s
    asm.write_text(s.replace(a, '(ELBOW_SUPPORT_U, 0.0, ex.PED_Z[0] - 4.0)'))
    print(src)


if __name__ == "__main__":
    main()
