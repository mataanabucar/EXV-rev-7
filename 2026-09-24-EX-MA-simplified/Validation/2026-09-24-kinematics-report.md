# EX-MA kinematics and cable validation (B4b: split pins, sliding tubes, conduit slack)

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
| stick | -45° … 50° | yes (-54° … 150°) |
| bucket | -55° … 85° | yes (-56° … 170°) |

## PTFE tubes over the working ranges

Grid: boom × stick working ranges, 5 × 5 poses. Tubes are anchored in the control-box conduit fitting and at their stop boss in the arm, and slide everywhere between. In the arm each tube keeps its natural shape; the length change slides down the PVC tube and is stored as spare length in the 137 mm conduit run, where it coils as a gentle helix.

| Tube | Cut length (approx.) | Arm path length range | Spare length in the conduit | Worst bend R in the arm | Conduit helix radius / bend R | Worst free-zone clearance | Bowden coupling |
|---|---|---|---|---|---|---|---|
| stick_hi | 737 mm | 379.2 … 380.7 mm | 2.0 … 3.5 mm | 20.0 mm | ≤ 5.0 mm / ≥ 100 mm | 0.6 mm (boom at [9.0, 10.0, 97.0], boom -40°, stick -45°) | ≤ 0.22 mm |
| stick_lo | 741 mm | 383.0 … 384.5 mm | 2.0 … 3.5 mm | 20.0 mm | ≤ 5.0 mm / ≥ 100 mm | 0.6 mm (boom at [9.0, -10.0, 97.0], boom -40°, stick -45°) | ≤ 0.22 mm |
| bucket_hi | 902 mm | 537.1 … 545.4 mm | 2.0 … 10.3 mm | 15.3 mm | ≤ 8.6 mm / ≥ 64 mm | 0.6 mm (boom at [9.0, 14.0, 97.0], boom -40°, stick -45°) | ≤ 0.67 mm |
| bucket_lo | 903 mm | 539.1 … 547.3 mm | 2.0 … 10.3 mm | 15.3 mm | ≤ 8.6 mm / ≥ 64 mm | 0.6 mm (boom at [9.0, -14.0, 97.0], boom -40°, stick -45°) | ≤ 0.67 mm |

- Bend radius ≥ 15 mm everywhere (arm and conduit): yes.
- Tube surface ≥ 0.5 mm from every member and split pin in the free zones: yes.
- Conduit helix fits (radius ≤ 20.2 mm in the Ø52.5 conduit): yes.
- Bowden coupling < 1 mm: yes.
- Closest tube-to-tube centrelines in the free zones: 4.3 mm (stick_hi / bucket_hi, boom 2°, stick -45°; tube OD 4 mm, so ≥ 4.0 = not pressed together).

A slack bow inside the tower was modelled first and rejected: below the boom root the tower is only about 44 mm tall, which holds about 2.4 mm of slack at R ≥ 15, while the bucket tubes need up to 10 mm; the boom root's rear shell also closes over a deeper bow at boom +45°.

Clearance = tube surface to the nearest member surface in the unsupported (free) zones; inside the guides the tube runs in Ø5.2 channels by design. Cut length = arm path + fixed run from the box fitting through the conduit, pedestal, elbow and PVC tube (final lengths go in the bill of materials).
Bowden coupling = rope movement caused by the tube bending: turning-angle change × rope play (0.2 mm). This is the only way one joint can move another's rope.

## Travel table

| Circuit | Working range | Span | Joint drum pitch R | Rope travel per side | Lever swing (Ø60 control drum) | Rope wrap left at ends |
|---|---|---|---|---|---|---|
| boom | -40° … 45° | 85° | 15.0 mm | 22.3 mm | 42° | 48° |
| stick | -45° … 50° | 95° | 13.0 mm | 21.6 mm | 41° | 42° |
| bucket | -55° … 85° | 140° | 8.5 mm | 20.8 mm | 40° | 20° |
| slew | -90° … 90° | 180° | 55.0 mm | 172.8 mm | wheel 180° (1:1, Ø110 spool) | n/a (single lane, 250° total) |

Crimp anchors are set at the middle of each joint's range at assembly, so the rope wrap at either end of travel is 90° − span/2.
