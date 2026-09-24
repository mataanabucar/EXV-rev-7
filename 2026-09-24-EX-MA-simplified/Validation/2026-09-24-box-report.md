# EX-MA control box, pedestal and sandbox — validation (B5)

Solid overlap threshold 1.0 mm³. Designed contacts (shafts in bores, parts screwed face to face) are excluded from the overlap test.

## Static overlap check (box, pedestal, sandbox, hardware)

- No unintended overlaps.

## Lever sweep (2° steps across each slot)

| Lever | Swing | Slot length | Worst overlap during the sweep | Dowel vs slot end at the stop / 1.5° past |
|---|---|---|---|---|
| boom | 42.5° | 141.5 × 17.0 mm | none | 0.00 / 402 mm³ ; 0.00 / 402 mm³ |
| stick | 41.2° | 137.2 × 17.0 mm | none | 0.00 / 408 mm³ ; 0.00 / 408 mm³ |
| bucket | 39.7° | 132.3 × 17.0 mm | none | 0.00 / 416 mm³ ; 0.00 / 416 mm³ |

The slot is the hard stop: ~0 overlap at the end of travel and a clear overlap 1.5° further.

## Slew wheel hand clearance

| Lever | Closest approach of dowel/knob to the wheel over the lever swing |
|---|---|
| boom | 161 mm |
| stick | 91 mm |
| bucket | 22 mm |

## Lever ropes in the box (drum tangent → box fitting hole)

| Strand | Length | Fleet angle at the drum | Bend entering the fitting | Wrap left on the drum over the swing | Clearance to other parts |
|---|---|---|---|---|---|
| boom upper | 118 mm | 11.3° | 21.4° | 62–105° | 8.0 mm (lever-hub-stick) |
| boom lower | 118 mm | 11.2° | 14.2° | 52–95° | 13.8 mm (lever-hub-stick) |
| stick upper | 116 mm | 4.5° | 18.8° | 63–104° | 7.6 mm (lever-hub-bucket) |
| stick lower | 116 mm | 4.4° | 9.7° | 53–94° | 7.6 mm (lever-hub-bucket) |
| bucket upper | 117 mm | 9.8° | 20.7° | 63–103° | 4.7 mm (lever-hub-stick) |
| bucket lower | 118 mm | 9.8° | 13.1° | 54–94° | 4.7 mm (lever-hub-stick) |

## Slew circuit

Each slew rope runs in its own PTFE sleeve from a post beside the box spool to an angled counterbore in the pedestal fitting that points along the pedestal drum's tangent; both drums have two lanes.

| Sleeve | Length | Bends (total) | Friction factor e^(µθ), µ 0.15 | Sleeve clearance in the box | Bare rope spool→post | Bare rope pedestal exit→drum |
|---|---|---|---|---|---|---|
| A | 317 mm | 144° | 1.46 | > 13 mm | > 14 mm | > 14 mm |
| B | 385 mm | 196° | 1.67 | > 13 mm | > 14 mm | > 14 mm |

| Slew | Lane A wrap spool / pedestal | Lane B wrap spool / pedestal |
|---|---|---|
| -90° | 90° / 270° | 270° / 90° |
| +0° | 180° / 180° | 180° / 180° |
| +90° | 270° / 90° | 90° / 270° |

Closest rope/sleeve pair in the box: 2.4 mm surface to surface (boom upper / stick upper).

## Analytic checks

- lever axle sag, plain 7.94: 0.28
- lever axle sag, threaded (root 6.6): 0.58
- slew side pull on the drum (N, 30 N per rope): 50.10
- PEX deflection at the drum, no bushing (mm): 4.07
- PEX deflection at the drum, with the shelf bushing (mm): 0.33
- radial load left on the slewing ring (N): 19.91
- moment on the slewing ring without the bushing (N·m): 5.46
- boom: arm gravity torque at the joint, upper bound (N·m): 0.30
- boom: holding torque needed at the lever (N·m): 0.61
- boom: drag-clamp M3 bolt force for it (N, mu 0.3): 162.04
- stick: arm gravity torque at the joint, upper bound (N·m): 0.09
- stick: holding torque needed at the lever (N·m): 0.20
- stick: drag-clamp M3 bolt force for it (N, mu 0.3): 54.37
- bucket: arm gravity torque at the joint, upper bound (N·m): 0.01
- bucket: holding torque needed at the lever (N·m): 0.03
- bucket: drag-clamp M3 bolt force for it (N, mu 0.3): 8.78
- arm masses (g, printed at ~55 % fill): {'boom': 87.0, 'stick': 56.0, 'bucket': 25.0}

## Approximate cut lengths (for the bill of materials)

Without crimp tails: add about 60 mm for each double-crimp loop. Final lengths go in the B6 bill of materials.

| Item | Length |
|---|---|
| boom rope (one length, midpoint crimp) | 1307 mm |
| stick rope (one length, midpoint crimp) | 1963 mm |
| bucket rope (one length, midpoint crimp) | 2324 mm |
| PTFE stick_hi (box fitting -> arm stop) | 749 mm |
| PTFE stick_lo (box fitting -> arm stop) | 753 mm |
| PTFE bucket_hi (box fitting -> arm stop) | 915 mm |
| PTFE bucket_lo (box fitting -> arm stop) | 917 mm |
| PTFE slew sleeve A (post -> pedestal fitting) | 329 mm |
| slew rope A (spool anchor -> pedestal crimp) | 662 mm |
| PTFE slew sleeve B (post -> pedestal fitting) | 397 mm |
| slew rope B (spool anchor -> pedestal crimp) | 735 mm |
