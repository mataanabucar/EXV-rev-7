# EX-MA — validation summary

One line per criterion; details in the reports next to this file:
`2026-09-24-exterior-check.txt`, `2026-09-24-kinematics-report.md`, `2026-09-24-box-report.md`, `2026-09-24-package-check.json`, `2026-09-24-cable-paths.json`, `2026-09-25-full-assembly-check.json`.

| Check | Target | Result | Status |
|---|---|---|---|
| Exterior unchanged (boom, stick, base) | outer-skin p99 ≤ 0.05 mm | max p99 0.018 mm | pass |
| Exterior unchanged (tower) | deviation only at the approved flange join | p99 1.48 mm; the 282 samples > 0.3 mm lie at z 36.0–37.7 (flange top at z 38, original frame) | pass |
| boom working range inside its contact-free range | -40…45° | -42…80° | pass |
| stick working range inside its contact-free range | -45…50° | -54…150° | pass |
| bucket working range inside its contact-free range | -55…85° | -56…170° | pass |
| Slewing ring | balls free, turret captured | 57 BBs, overlap 0.00 mm³, lift 0.65 mm, rock 1.1° | pass |
| PTFE tube bend radius (arm + conduit) | ≥ 15 mm | 15.3 mm / 66 mm | pass |
| PTFE tube clearance to members and pins | ≥ 0.5 mm | 0.6 mm | pass |
| Bowden coupling (one joint moving another's rope) | < 1 mm | 0.66 mm | pass |
| Box/pedestal/sandbox part overlaps | none | none | pass |
| Lever sweep across each slot | no contact | worst 0.00 mm³ | pass |
| Slots are the lever hard stops | 0 at the stop, contact 1.5° past | yes | pass |
| Slew wheel hand clearance | ≥ 20 mm | 22 mm | pass |
| Lever rope fleet angle / fitting entry | ≤ 12° / ≤ 30° | 11.3° / 21.4° | pass |
| Rope wrap on the lever drums | ≥ 20° | 52° | pass |
| Rope wrap on the slew drums at ±90° | ≥ 20° | 90° | pass |
| Rope-to-rope spacing in the box | ≥ 2 mm | 2.4 mm | pass |
| Lever axle sag (threaded 5/16in, 100 N) | ≤ 1 mm | 0.58 mm | pass |
| PEX deflection at the slew drum | ≤ 0.5 mm | 0.33 mm | pass |
| Every rope modelled as one continuous path | 8 rope tails, gap < 0.5 mm | max gap 0.00 mm | pass |
| Full assembly STEP (zip): every item present, re-imports | 131 solids | 131 in file / 131 on re-import; 64 MB zipped | pass |
| Full assembly: EX-MA meshes and ropes/tubes as valid solids | valid, volume error < 0.1 % | 9/9 parts (max 0.001 %), 14/14 ropes+tubes (max 0.000 %) | pass |
| Every printed STL watertight, one body | 25 parts | 25/25 | pass |
| Every printed part fits the A1 bed | ≤ 246 × 246 × 256 mm | 25/25 | pass |
| Every part STEP imports as one solid | 16 files | 16/16 | pass |
| Assembly STEP re-imports completely | 108 solids | 108 | pass |
| 3MF plates reload, inside the bed, no overlaps | 7 plates | 7/7 | pass |

**27 of 27 checks pass.**

## Not checked by the model

- Real friction: PTFE on steel rope and PLA on the 5/16in rod are taken from typical values (µ 0.15 / 0.3).
- Printed-part strength: walls and infill follow the bill of materials; loads stay on steel pins and crimps.
- Rope stretch and crimp seating: set tension after the first hour of use.
