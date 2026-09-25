# EX-MA manual excavator — inspection and architecture

The EX-MA exterior stays as it was; the inside is rebuilt as the simplest cable mechanism that works: three push-pull levers and one horizontal wheel on a wooden control box, each driving exactly one motion.

```
boom lever ─┐                                   ┌─ boom drum   (bare rope up the turret tube)
stick lever ─┼─ Ø60 lever drum → rope → conduit ─┼─ stick drum  (rope inside a sliding PTFE tube)
bucket lever┘                                   └─ bucket drum (rope inside a sliding PTFE tube)
slew wheel ── Ø110 spool → rope in PTFE sleeve → Ø110 slew drum on the PEX turret tube → turret
```

## 1. What stays frozen (the exterior)

- Source of truth: `References/EX-MA Colored ARM.stl` and `EX-MA Colored.3mf`. The 3MF is a one-plate preview at scale 0.7104 rotated 46.93° about Z; everything is built at design scale (×1.408), where the pins are Ø4.2 mm = 8-32 rod and `Source_Bucket_Repaired.step` matches the bucket exactly.
- Frozen: base disc, tower, boom halves, stick halves, bucket body and ears (G/H), joint positions, colours.
- Exterior changes you approved: the green slew ring removed, the tower flange made circular (it is now the inner race of a printed slewing ring), the turret lowered 13 mm to close the gap, a thin retaining ring on the base rim.
- Checked: outer-skin deviation p99 ≤ 0.02 mm on the boom, stick and base; the tower's only deviation is the approved flange join (see the validation summary).

| Item | Design-scale value (original pose) |
|---|---|
| Boom pivot (u, z) | (0.0, 102.0) — built (0.0, 89.0) after the 13 mm drop |
| Stick pivot | (186.19, 196.86) (boom pin to pin 209 mm) |
| Bucket pivot | (344.8, 122.9) (stick pin to pin 175 mm) |
| Base | Ø140 disc; slew axis at u = v = 0 |
| Boom / stick | split left/right half-shells, ~4 mm walls; cavities about 42 × 31 and 25 × 31 mm |

## 2. What was inside (existing mechanisms)

Double-groove drums at the boom and stick joints with two idlers each, a bucket drum on a long printed sleeve, the green ring acting as the slew drum (three shallow grooves) around a fixed base post, and a bucket built from about 11 mesh pieces, a two-piece bracket, five printed pins and two clips.

## 3–4. Simplification audit

| Part | Verdict | Why |
|---|---|---|
| Boom drum #4 (Ø37, double groove + ridge) | REPLACE | one single-groove Ø30 drum; a crimp pocket anchors the rope midpoint |
| Boom idlers #6, #7 | REMOVE | no direction change needed — the ropes run straight to the drum |
| Stick drum A (Ø33, double groove) | REPLACE | one single-groove Ø26 drum |
| Stick idlers B, C | REMOVE | the stick and bucket ropes run in PTFE tubes across the joints |
| Bucket drum F + sleeve | REPLACE | one printed drum-axle: Ø17 drum, journals in the stick nose, hex ends in the ears |
| Green slew ring #1 | REMOVE | the slew drum moved into the pedestal; the turret now rides a printed ball ring |
| Base post + cap #5 | REMOVE | the PEX turret tube passes through; the ball ring carries the turret |
| Bucket bracket I (2 pieces), lugs O/P | SIMPLIFY | merged into the bucket body (one print) |
| Pins J/M/Q/S/R, clips K/N | REMOVE | no longer needed once the bracket is part of the bucket |
| Joint pins (3) | KEEP → hardware | 8-32 rod; the boom and stick pins are split so tubes can cross the joint axes |
| Internal channels, shelves, ribs | SIMPLIFY | only cut where a tube or drum passes; the rest kept for stiffness |
| Tower centre funnel | REMOVE | left over from the old centre post; frees the tower for the tubes |

Result: 16 printed parts removed and 3 merged from the arm's internals, replaced by 4 (boom drum, stick drum, bucket drum-axle, retaining ring). The pedestal adds 5 and the control box 8 printed parts, which did not exist before.

## 5–8. The four mechanisms

Every circuit is a pull-pull loop made of rope that is anchored on both drums, so each control drives only its own joint. The joint drums carry the rope midpoint (a single crimp in a pocket); the control drums carry the two tails (double-crimp loops on slotted M3 anchors, which are also the tension adjusters).

| Circuit | Joint drum | Working range | Rope travel per side | Control | Joint contact-free range |
|---|---|---|---|---|---|
| boom | Ø30 single groove | -40° … 45° | 22.3 mm | lever, 42° swing | -42° … 80° |
| stick | Ø26 single groove | -45° … 50° | 21.6 mm | lever, 41° swing | -54° … 150° |
| bucket | Ø17 single groove | -55° … 85° | 20.8 mm | lever, 40° swing | -56° … 170° |
| slew | Ø110 two-lane drum in the pedestal | -90° … 90° | 173 mm | wheel 1:1 | unlimited (rope wrap limits it to ±90°) |

**Boom.** Two bare ropes run up the turret tube and wrap the boom drum on the boom pivot. The drum has no bore: it is keyed to the boom by four M3 screws, and the pivot is two short 8-32 rods (split pin) so the middle of the joint stays free for the tubes.

**Stick and bucket.** Their ropes run inside 4 × 2 mm PTFE tubes from the box fitting to a stop bulkhead just before their joint (stick tubes stop in the boom tip, bucket tubes in the stick nose). The tubes cross the boom and stick joints exactly through the pivot axes, which keeps their length almost constant; they slide through loose channels, and the small change that remains is stored as spare length in the conduit.
Worst tube bend radius 15.3 mm; tube surface ≥ 0.6 mm from every part; the Bowden effect (one joint moving another's rope) ≤ 0.66 mm.

**Slew.** The wheel turns a Ø110 two-lane spool; each rope runs in its own PTFE sleeve from a post beside the spool, through the conduit, to an angled counterbore in the pedestal fitting that aims it straight at the tangent of the pedestal slew drum. The drum is clamped on the 3/4in PEX-B turret tube, which the turret's hub clamps at the top. A printed ball ring (57 × 6 mm BBs) carries the turret on the base; a plywood shelf with a printed bushing just above the drum takes the ropes' side pull off the ring (PEX deflection 0.33 mm instead of 4.1 mm).

## 9. Control box

- Plywood box 250 × 405 × 242 mm, bolted to the outside of the sandbox wall; the top is removable for service.
- Left to right: boom, stick, bucket lever (70 mm apart), then the horizontal slew wheel (Ø184).
- The three lever hubs turn on one 5/16in rod between two bearing blocks (sag ≤ 0.58 mm). Each hub has its own M3 drag clamp for holding friction (boom needs about 0.65 N·m).
- The top-panel slots are the lever hard stops (the handle rod meets the slot end exactly at the end of travel).
- Ropes leave the lever drums toward one conduit fitting, entering it at ≤ 22° with a fleet angle ≤ 11.3°.

## 10. Constraints found and how they were solved

- Tubes passing beside the pins changed length by 20–35 mm → split pins, so the tubes cross exactly through the axes.
- A slack loop in the tower held only about 2.4 mm at a safe bend → the tubes slide and the spare length goes to the conduit.
- The bucket tubes touch the inside of the stick root's rear lip above +50° → stick working range −45…+50°.
- The stick exit could not be raised without breaking through the stick wall → the length change is balanced from the boom side instead.
- Knife-thin fins remained in the tube channels where short cut cylinders met → channels swept with balls at every joint.
- The pedestal slew drum overlapped the conduit fitting → pedestal extended toward the box.
- One groove cannot keep 20° of rope wrap at ±90° slew → two-lane drums, one rope per lane.
- The wheel sits far right of the conduit mouth (hand clearance) → slew ropes run in PTFE sleeves instead of over a sharp fairlead.
- PEX is flexible → shelf bushing next to the slew drum.

## Directions and rigging

- **Slew:** the rope loop is not crossed, so the base turns the same way as the wheel: wheel left (anticlockwise from above) swings the arm to the operator's left.
- **Levers:** pushing a lever forward pulls its lower strand. Rig each circuit so that forward = boom down, stick out, bucket dump (backward does the opposite). To reverse a lever, reverse the rope's wrap on its joint drum.
- **Zero position:** crimp every joint rope with the joint at the middle of its working range and the lever vertical; the wheel is centred with the arm pointing straight out.

## Assembly order

1. Print the parts (bill of materials, `3MF/` plates), cut the wood (`2026-09-24-cut-list.md`), deburr the copper.
2. Build the sandbox and the pedestal (leave the pedestal's +u wall off). Fit the pedestal conduit fitting (4 × M3 × 25), the copper elbow in its socket, the elbow support with a cable tie, the shelf on its cleats and the PEX bushing.
3. Build the control box (top off). Fit the bearing blocks, the spool riser, the two sleeve posts and the box conduit fitting; bolt the box to the sandbox wall (M3 × 35 through the fitting, the box front and the wall; M3 × 30 at the lower corners); fit the conduit and seal it.
4. Slew ring: screw the base to the pedestal top, drop in the BBs, lower the turret (its hub already clamped on the PEX tube, which passes the base, the pedestal top, the bushing and into the slew drum), bolt the retaining ring (8 × M3) and clamp the slew drum.
5. PTFE tubes: seat each tube in its box-fitting counterbore, feed it through the conduit, the pedestal window, the elbow and the PEX tube into the tower, then along its channels to its stop bulkhead (cut to the listed length).
6. Arm: boom drum between the boom halves (4 key screws), boom split pins; stick drum and stick split pins; bucket drum-axle in the stick nose, ears glued to the bucket lugs, bucket pin; close the halves with the lug screws.
7. Arm ropes: joint at mid-range, midpoint crimp in the drum pocket, feed the two tails back to the box and onto the lever drum (rim holes → loops on the slotted anchors); set tension by sliding the anchors outward.
8. Slew ropes: sleeves from the posts through the box fitting and conduit into the pedestal counterbores; rope crimp in the pedestal drum lane pocket, loop on the spool anchor; centre the wheel, tension.
9. Top panel on, 5/16in rod handles through the slots into the hub sockets (M3 pinch clamp), printed knobs glued on; set each lever's drag clamp.

**Service:** the box top and the pedestal +u wall come off; every crimp and loop is reachable; any drum or rope can be replaced by opening one arm half (lug screws) without touching the exterior shells' glue.

## Decision log

- Build at full design scale (×1.408) — user.
- Conduit housing between box and arm, both mounted on a 24 × 24in sandbox — user.
- Hardware on hand: 1/16in galvanized rope with single and double crimps; PLA or PETG — user.
- Concept images before any CAD; green ring removed, circular flange, lowered turret, printed rotating connector — user.
- Tube slack: user chose a loop in the tower; the model showed it cannot hold enough at a safe bend, so the slack moved to the conduit — user approved.
- Stick working range −45…+50° and removal of the old single conduit fitting — user approved.
- Measured hardware: 3/4in PEX-B turret tube, 5/16in lever axle, 1/2in copper OD 15.88 — user.
- Copper instead of PEX for the turret tube considered; kept PEX (the tube must turn with the turret) — user.
- Working ranges kept larger than the earlier build's (slew ±60, boom ±35, stick −45…+25, bucket ±50) — user.
- Hardware from the user's own kits (Fgruh M3 kit, Hillman 8-32 rod + nuts), split-lock washers instead of nylocs, wood screws on hand; PTFE kept — user.
- Printing with a 0.6 mm nozzle: every wall checked in its print orientation (no patch ≥ 20 mm² under 1.0 mm) — user.
- Stick nose (0.3–0.4 mm hood over the bucket drum, a 6 mm open slot beside it, a 0.9 mm ring round the pin) made a solid rounded end inside the original r 12 outline; bucket drum flange lip 2.8 → 1.8 mm so the hood is 2 mm thick — user (fill the slot; thicken inward).
- Bucket floor 1.8 mm (it had a crack through the middle); bucket lug slits, back-plate top edge and the two unused link-pin holes in bracket I filled; clip recess in each ear filled — user (fix every thin spot).

## Where things are

- `Source/` — every script (all parameters in `2026-09-24-exma_common.py`).
- `STL/` printed parts; `STEP/` new parts, wood and `2026-09-24-ex-ma-assembly.step` (new parts, wood, hardware); `3MF/` A1 plates; `2026-09-24-ex-ma-assembly.glb` every part in one file.
- `STEP/2026-09-25-ex-ma-full-assembly.zip` — the whole machine in one STEP file (131 solids: printed parts, the modified EX-MA parts as exact solids, wood, hardware, ropes and PTFE tubes; 334 MB unzipped, zipped because GitHub refuses files over 100 MB).
- `2026-09-24-bill-of-materials.md`, `2026-09-24-cut-list.md`, `Validation/`, `Preview/`.
- `2026-09-25-print-and-assembly-checklist.md` — print order with fit tests, cut list for rope and tube, and the build, rigging and test steps with the hardware for each.

## Review views

Rendered from the exported parts, wood panels and hardware. Every coloured rope (boom green, stick blue, bucket red, slew purple) is the continuous modelled path from `Source/2026-09-24-cable-paths.py` (built pose, joints at 0°); PTFE tubes are drawn translucent around their ropes.

1. `Preview/2026-09-24-view1-complete-excavator.png` — Complete excavator: control box with the 3 levers and the slew wheel, pedestal, base, arm, bucket.
2. `Preview/2026-09-24-view2-full-system-cutaway.png` — Full-system cutaway (+v halves removed): every rope from its lever or wheel through the conduit, pedestal, copper elbow and PEX tube to its joint.
3. `Preview/2026-09-24-view3-control-box-cutaway.png` — Control box: lever hubs on the 5/16in axle, drums and rope anchors, bearing blocks, slew spool and riser, sleeve posts, box conduit fitting.
4. `Preview/2026-09-24-view4-boom-joint.png` — Boom joint: boom drum and crimp pocket, split pins, boom ropes rising from the PEX tube, stick and bucket PTFE tubes crossing the boom axis.
5. `Preview/2026-09-24-view5-stick-joint.png` — Stick joint: stick drum, split pins, stick tube stops in the boom, bucket tubes crossing the stick axis.
6. `Preview/2026-09-24-view6-bucket-joint.png` — Bucket joint: bucket drum-axle with hex ends in the ears, bucket tube stops in the stick.
7. `Preview/2026-09-24-view7-slew-detail.png` — Slew path, cut just above the slew-rope layer: wheel → spool → PTFE sleeves → conduit → pedestal fitting → slew drum on the PEX tube → turret.
