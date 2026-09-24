# EX-MA kinematics and cable validation (B4)

Angles are measured from the EX-MA pose; + raises the member. Contact = overlap > 5.0 mm³ between mesh solids, swept in 2.0° steps.

## Joint ranges (first contact)

| Joint | Checked against | Min | Max | Span | Overlap at 0 |
|---|---|---|---|---|---|
| boom | tower + base + ring | -42° | 80° | 122° | 0.0 mm³ |
| boom_arm | whole arm vs tower/base/pedestal top | -42° | 80° | 122° | 0.0 mm³ |
| stick | boom | -54° | 150° | 204° | 0.0 mm³ |
| bucket | stick | -56° | 170° | 226° | 0.0 mm³ |

## Slewing ring

- BBs (6 mm): 57 fit on the Ø118 ball circle with 0.4 mm gaps.
- Ball-to-race overlap at rest: 0.00 mm³ (0 = free running).
- Turret lift before the balls meet the retaining ring: 0.65 mm.
- Turret rock before the flange meets the rim or ring: 1.1°.
- Ball centre to turret flange (inner race): 3.15–3.20 mm (ball radius 3.00 + clearance 0.15).
- Ball centre to base rim (lower outer race): 3.10–3.15 mm (ball radius 3.00 + clearance 0.15).
- Ball centre to retaining ring (upper outer race): 3.16–3.17 mm (ball radius 3.00 + clearance 0.15).

## Working ranges (set by the lever slots)

| Joint | Working range | Inside the contact-free range? |
|---|---|---|
| boom | -40° … 45° | yes (-42° … 80°) |
| stick | -50° … 70° | yes (-54° … 150°) |
| bucket | -55° … 85° | yes (-56° … 170°) |

## PTFE tubes over the working ranges

Tube length is fixed (longest natural path + 2 mm); at other poses the spare length bows out in the free zones.

| Tube | Cut length | Worst bend R | Worst centreline clearance | Spare length (bows) | Bowden coupling |
|---|---|---|---|---|---|
| stick_hi | 357 mm | 4.4 mm | -2.4 mm | 2.0 … 35.3 mm | ≤ 0.18 mm |
| stick_lo | 358 mm | 4.7 mm | -2.2 mm | 2.0 … 35.3 mm | ≤ 0.23 mm |
| bucket_hi | 534 mm | 0.4 mm | -2.2 mm | 2.0 … 42.5 mm | ≤ 1.06 mm |
| bucket_lo | 536 mm | 0.2 mm | -2.2 mm | 2.0 … 43.0 mm | ≤ 1.00 mm |

Clearance = distance from the tube centreline to the nearest member surface (tube radius 2.0 mm).
Bowden coupling = rope movement caused by the tube bending: turning-angle change × rope play (0.2 mm). This is the only way one joint can move another's rope.

## Travel table

| Circuit | Working range | Span | Joint drum pitch R | Rope travel per side | Lever swing (Ø60 control drum) | Rope wrap left at ends |
|---|---|---|---|---|---|---|
| boom | -40° … 45° | 85° | 15.0 mm | 22.3 mm | 42° | 48° |
| stick | -50° … 70° | 120° | 13.0 mm | 27.2 mm | 52° | 30° |
| bucket | -55° … 85° | 140° | 8.5 mm | 20.8 mm | 40° | 20° |
| slew | -90° … 90° | 180° | 55.0 mm | 172.8 mm | wheel 180° (1:1, Ø110 spool) | n/a (single lane, 250° total) |

Crimp anchors are set at the middle of each joint's range at assembly, so the rope wrap at either end of travel is 90° − span/2.
