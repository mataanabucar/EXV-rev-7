# EX-MA manual excavator — bill of materials

Everything needed to build the simplified EX-MA arm, the wooden control box, the pedestal and the sandbox. Counts come from the build scripts (drum keys, lugs, bolts, balls), lengths from the validated rope and tube paths.

Print settings (already in the slicer project files in `3MF/`, see Plates below): Bambu Lab A1, 0.6 mm nozzle, your "A1 0.6 Fast Start" printer preset, process "0.30mm Strength @BBL A1 0.6 nozzle" (0.3 mm layers, 4 walls, 25 % infill), 40 % infill on drums, hubs, clamps and anything carrying a pin, tree supports on the parts marked "yes" below. Arm shell (boom and stick halves) in PETG, everything else in SUNLU PLA+ 2.0. The PLA+ project prints faster: flow cap 28 mm³/s at 230 °C (profile: 22 at 220), inner walls, infill and supports 200 mm/s, acceleration 10000; outer walls, top surfaces and the first layer are unchanged. If infill looks under-extruded on the first plate, set the filament's max volumetric speed to 25. Orientation below is the one with the least support area; every wall was checked in that orientation for the 0.6 mm nozzle (`Validation/2026-09-25-wall-check.json`).

## Printed parts — new

| Part | Qty | What it does | Volume | Est. mass | Print orientation | Print size (x × y × z) | Supports | Project, plate |
|---|---|---|---|---|---|---|---|---|
| boom-drum | 1 | Ø30 pitch single-groove boom drum | 10.6 cm³ | 7 g | top face down | 35 × 35 × 14 | light (1.4 cm²) | other 6 |
| stick-drum | 1 | Ø26 pitch single-groove stick drum | 5.8 cm³ | 4 g | top face down | 30 × 30 × 10 | light (1.3 cm²) | other 6 |
| bucket-drum-axle | 1 | Ø17 pitch bucket drum with journals and hex ends | 6.6 cm³ | 5 g | top face down | 19 × 19 × 49 | light (0.7 cm²) | other 6 |
| slew-drum | 1 | Ø110 pitch two-lane slew drum on the rotating 3/4in PEX turret tube | 78.9 cm³ | 54 g | as modelled (bottom down) | 113 × 113 × 31 | yes (14 cm²) | other 1 |
| slewing-ring-retaining-ring | 1 | upper outer race, 8 x M3x12 | 19.9 cm³ | 14 g | top face down | 140 × 140 × 6 | none | other 5 |
| conduit-end-fitting-box | 1 | box end of the conduit: PTFE tube anchors | 133.8 cm³ | 91 g | as modelled (bottom down) | 100 × 100 × 26 | yes (28 cm²) | other 3 |
| conduit-end-fitting-pedestal | 1 | pedestal end: PTFE tubes slide through into the copper elbow | 132.9 cm³ | 91 g | as modelled (bottom down) | 100 × 100 × 26 | yes (28 cm²) | other 1 |
| lever-hub-boom | 1 | boom lever hub + drag clamp, drum offset toward centre | 54.2 cm³ | 37 g | top face down | 65 × 66 × 70 | yes (35 cm²) | other 2 |
| lever-hub-stick | 1 | stick lever hub + drag clamp | 44.9 cm³ | 31 g | top face down | 65 × 66 × 34 | yes (33 cm²) | other 2 |
| lever-hub-bucket | 1 | bucket lever hub + drag clamp, drum offset toward centre | 49.9 cm³ | 34 g | top face down | 65 × 66 × 55 | yes (26 cm²) | other 3 |
| lever-knob | 3 | Ø36 ball knob, glued on the 5/16in rod handle | 22.8 cm³ | 16 g | as modelled (bottom down) | 36 × 36 × 32 | light (1.5 cm²) | other 2 |
| slew-spool | 1 | wheel spool: Ø110 two-lane drum + tube + wheel flange | 124.2 cm³ | 85 g | as modelled (bottom down) | 113 × 113 × 145 | yes (21 cm²) | other 3 |
| slew-wheel | 1 | Ø184 horizontal hand wheel | 116.1 cm³ | 79 g | as modelled (bottom down) | 184 × 184 × 12 | yes (11 cm²) | other 2 |
| slew-tube-bushing | 1 | PEX turret-tube bushing in the pedestal shelf | 6.9 cm³ | 5 g | as modelled (bottom down) | 44 × 44 × 15 | none | other 1 |
| elbow-support | 1 | post + cable-tie saddle under the copper elbow | 24.4 cm³ | 17 g | as modelled (bottom down) | 44 × 24 × 57 | light (0.6 cm²) | other 1 |
| spool-riser | 1 | column from the box floor up to the slew spool | 58.4 cm³ | 40 g | as modelled (bottom down) | 52 × 52 × 94 | none | other 2 |
| slew-tube-post | 2 | slew PTFE sleeve anchor beside the spool | 30.3 cm³ | 21 g | as modelled (bottom down) | 24 × 36 × 110 | none | other 2 |

## Printed parts — modified EX-MA parts

| Part | Qty | What it does | Volume | Est. mass | Print orientation | Print size (x × y × z) | Supports | Project, plate |
|---|---|---|---|---|---|---|---|---|
| tower | 1 | EX-MA tower: circular flange = inner race, PEX clamp hub, centre funnel removed, lowered 13 mm | 130.2 cm³ | 89 g | on its +x side | 99 × 117 × 117 | yes (53 cm²) | other 4 |
| base | 1 | EX-MA base: centre post removed, lower race rim with nut slots, 4 screw holes to the pedestal | 157.6 cm³ | 107 g | as modelled (bottom down) | 140 × 140 × 21 | yes (28 cm²) | other 4 |
| boom-half-left | 1 | EX-MA boom half (+v): PTFE channels, stick-tube bulkhead, drum key sockets, joining lugs | 60.0 cm³ | 41 g | on its +y side | 218 × 123 × 24 | yes (11 cm²) | arm 1 |
| boom-half-right | 1 | EX-MA boom half (-v): as the left half, mirrored | 55.9 cm³ | 38 g | on its -y side | 218 × 123 × 24 | yes (14 cm²) | arm 1 |
| stick-half-left | 1 | EX-MA stick half (+v): PTFE channels, bucket-tube bulkhead, drum key sockets, joining lugs | 42.8 cm³ | 29 g | on its +y side | 190 × 107 × 18 | light (5.9 cm²) | arm 1 |
| stick-half-right | 1 | EX-MA stick half (-v): as the left half, mirrored | 41.1 cm³ | 28 g | on its -y side | 190 × 107 × 18 | light (6.9 cm²) | arm 1 |
| bucket-ear-left | 1 | EX-MA bucket ear G: hex socket for the bucket drum-axle | 2.3 cm³ | 2 g | on its +y side | 20 × 43 × 15 | light (1.2 cm²) | other 6 |
| bucket-ear-right | 1 | EX-MA bucket ear H: hex socket for the bucket drum-axle | 2.3 cm³ | 2 g | on its -y side | 20 × 43 × 15 | light (1.2 cm²) | other 6 |
| bucket | 1 | EX-MA bucket: repaired STEP body + bracket I + lugs O/P merged into one part | 27.8 cm³ | 19 g | on its +x side | 69 × 54 × 69 | yes (27 cm²) | other 6 |

Printed total: 20 new prints + 9 modified EX-MA prints, about 1.03 kg of filament (estimate at ~55 % effective fill).

## Plates (Bambu A1, 256 × 256 mm)

Two slicer projects, each saved for Bambu Studio 2.8.2.61 and for OrcaSlicer (nightly); open the one for your slicer — each opens with all of its plates, already named. The `bambu-` and `orca-` files hold the same parts in the same places.

| Project | Material | Plate | Parts |
|---|---|---|---|
| `3MF/2026-09-27-{bambu,orca}-arm-shell-petg.3mf` | PETG (Generic PETG @BBL A1) | 1 — Arm shell | boom-half-right, boom-half-left, stick-half-right, stick-half-left |
| `3MF/2026-09-27-{bambu,orca}-other-parts-plaplus.3mf` | PLA+ (SUNLU PLA+ 2.0 @BBL A1) | 1 — Pedestal | conduit-end-fitting-pedestal, slew-drum, slew-tube-bushing, elbow-support |
| `3MF/2026-09-27-{bambu,orca}-other-parts-plaplus.3mf` | PLA+ (SUNLU PLA+ 2.0 @BBL A1) | 2 — Control box (1/2) | slew-wheel, lever-hub-stick, lever-hub-boom, spool-riser, lever-knob-1, lever-knob-2, lever-knob-3, slew-tube-post-1, slew-tube-post-2 |
| `3MF/2026-09-27-{bambu,orca}-other-parts-plaplus.3mf` | PLA+ (SUNLU PLA+ 2.0 @BBL A1) | 3 — Control box (2/2) | conduit-end-fitting-box, slew-spool, lever-hub-bucket |
| `3MF/2026-09-27-{bambu,orca}-other-parts-plaplus.3mf` | PLA+ (SUNLU PLA+ 2.0 @BBL A1) | 4 — Turret + slewing ring (1/2) | base, tower |
| `3MF/2026-09-27-{bambu,orca}-other-parts-plaplus.3mf` | PLA+ (SUNLU PLA+ 2.0 @BBL A1) | 5 — Turret + slewing ring (2/2) | slewing-ring-retaining-ring |
| `3MF/2026-09-27-{bambu,orca}-other-parts-plaplus.3mf` | PLA+ (SUNLU PLA+ 2.0 @BBL A1) | 6 — Arm mechanism + bucket | bucket, boom-drum, stick-drum, bucket-ear-right, bucket-ear-left, bucket-drum-axle |

## Part count by group

| Group | Parts | Prints |
|---|---|---|
| Arm shell | boom-half-left, boom-half-right, stick-half-left, stick-half-right | 4 |
| Arm mechanism + bucket | boom-drum, stick-drum, bucket-drum-axle, bucket, bucket-ear-left, bucket-ear-right | 6 |
| Turret + slewing ring | tower, base, slewing-ring-retaining-ring | 3 |
| Pedestal | slew-drum, slew-tube-bushing, elbow-support, conduit-end-fitting-pedestal | 4 |
| Control box | lever-hub-boom, lever-hub-stick, lever-hub-bucket, lever-knob ×3, slew-spool, spool-riser, slew-tube-post ×2, slew-wheel, conduit-end-fitting-box | 12 |
| **Total** | 26 different parts (STL files) | **29** |

## From your M3 kit (Fgruh 2300 pc)

Every machine screw is an M3 from the kit; the longest needed is 35 mm. Column 3 shows how many of that size are used out of how many the kit holds.

| Item | Qty | Used / in kit | What it does |
|---|---|---|---|
| M3 × 12 socket cap | 8 | 16 of 32 | joint-drum key screws: lock the boom and stick drums to their arm members (4 per drum, 2 through each side wall; the heads sit in pockets in the wall) |
| M3 × 12 socket cap | 8 | 16 of 32 | slewing-ring retaining ring: holds the turret down on the BBs (nuts slide into the slots in the base rim) |
| M3 × 20 socket cap | 8 | 17 of 30 | joining lugs: clamp the two halves of the boom (4) and the stick (4) together |
| M3 × 20 socket cap | 3 | 17 of 30 | lever drag clamps: squeeze the 5/16in rod to set each lever's holding friction |
| M3 × 20 socket cap | 3 | 17 of 30 | slew wheel to the spool flange |
| M3 × 25 socket cap | 2 | 6 of 30 | pinch clamps on the PEX turret tube (turret hub, pedestal slew drum) |
| M3 × 20 socket cap | 3 | 17 of 30 | handle pinch clamps: hold each 5/16in rod handle in its lever hub |
| M3 × 25 socket cap | 4 | 6 of 30 | pedestal conduit fitting to the pedestal wall (fitting 6 + wall 12 mm) |
| M3 × 35 socket cap | 4 | 4 of 20 | box conduit fitting through the box front and the sandbox wall (6 + 12 + 12 mm) |
| M3 × 30 socket cap | 2 | 2 of 20 | box front to the sandbox wall, lower corners (12 + 12 mm) |
| M3 × 10 button head | 8 | 8 of 42 | slotted rope-tail anchors = tension adjusters (2 per lever, 2 on the spool); the rope loop sits between two washers |
| M3 nut | 45 | 45 of 576 | with the screws above |
| M3 flat washer | 36 | 36 of 576 | with the screws above |
| M3 split-lock washer | 27 | 27 of 576 | with the screws above; split-lock washers under the nuts that hold moving or clamping parts |

## From your Hillman parts

The 8-32 rod is only used for the joint pins; nuts are used in jam pairs instead of lock nuts.

| Item | Qty | Length / used | Notes |
|---|---|---|---|
| 8-32 rod, boom split pin (tower cheek → boom wall) | 2 | 42 mm | a jam pair (2 nuts) on the outer end |
| 8-32 rod, stick split pin (boom tip → stick wall) | 2 | 22 mm | a jam pair (2 nuts) on the outer end |
| 8-32 rod, bucket pin (ears + drum-axle) | 1 | 65 mm | a jam pair at each end |
| 8-32 hex nuts | 12 | 12 of 22 | jam nuts on the pins (two nuts tightened against each other) |
| 8-32 rod used |  | 203 of 914 mm | the rest is spare |
| #4-40 and #6-32 machine screws |  |  | not needed (spares) |

## Your wood screws

| Item | Qty |  | Used for |
|---|---|---|---|
| #8 × 1in wood screw | 4 |  | base to the pedestal top |
| #6 × 3/4in wood screw | 16 |  | bearing blocks (from below), spool riser, sleeve posts, PEX bushing, elbow support |
| #6 × 1-1/4in wood screw | 120 |  | panel joints, ~4 per edge (box 12 edges, pedestal 10, sandbox 8), with wood glue |

## Rope, tube and other stock

PTFE tube = the white 4 mm OD / 2 mm ID filament (Bowden) tube used on 3D printers. The stick and bucket ropes run inside it through the arm, and the slew ropes through the conduit; it is what lets each lever move only its own joint.

| Item | Qty | Size / length | Used for |
|---|---|---|---|
| 1/16in galvanized 7x19 rope (have) | 1 | 1384 mm | boom circuit: one length, single crimp at the midpoint on the joint drum, double-crimp loops on the lever anchors (+60 mm per loop included) |
| 1/16in galvanized 7x19 rope (have) | 1 | 1821 mm | stick circuit: one length, single crimp at the midpoint on the joint drum, double-crimp loops on the lever anchors (+60 mm per loop included) |
| 1/16in galvanized 7x19 rope (have) | 1 | 2173 mm | bucket circuit: one length, single crimp at the midpoint on the joint drum, double-crimp loops on the lever anchors (+60 mm per loop included) |
| 1/16in galvanized 7x19 rope (have) | 1 | 829 mm | slew rope A: single crimp in the pedestal drum pocket, double-crimp loop on the spool anchor |
| 1/16in galvanized 7x19 rope (have) | 1 | 900 mm | slew rope B: single crimp in the pedestal drum pocket, double-crimp loop on the spool anchor |
| single crimp sleeve (have) | 5 | 1/16in | 3 joint-drum midpoints + 2 slew rope ends (+ spares) |
| double crimp sleeve (have) | 8 | 1/16in | 6 arm tail loops + 2 slew loops (+ spares) |
| PTFE tube 4 mm OD × 2 mm ID | 1 | 647 mm | stick_hi (box fitting -> arm stop) (+10 mm to trim) |
| PTFE tube 4 mm OD × 2 mm ID | 1 | 658 mm | stick_lo (box fitting -> arm stop) (+10 mm to trim) |
| PTFE tube 4 mm OD × 2 mm ID | 1 | 813 mm | bucket_hi (box fitting -> arm stop) (+10 mm to trim) |
| PTFE tube 4 mm OD × 2 mm ID | 1 | 822 mm | bucket_lo (box fitting -> arm stop) (+10 mm to trim) |
| PTFE tube 4 mm OD × 2 mm ID | 1 | 339 mm | slew sleeve A (post -> pedestal fitting) (+10 mm to trim) |
| PTFE tube 4 mm OD × 2 mm ID | 1 | 407 mm | slew sleeve B (post -> pedestal fitting) (+10 mm to trim) |
| 5/16in rod (have) | 2 | 205 mm, 274 mm | lever axle; slew spool axle |
| 5/16in rod (have) | 3 | 230 mm | lever handles (printed knobs glued on top) |
| 5/16in nut + washer | 4 | 5/16in | 2 on the lever axle (outside the bearing blocks), 2 on the spool axle |
| 6 mm airsoft BBs (or 1/4in steel balls) | 57 | Ø6 | slewing ring (+ ~5 spares) |
| 3/4in PEX-B tube (have) | 1 | 120 mm | turning turret tube |
| 1/2in copper (have) | 1 | 90° sweep elbow (R ≈ 30) + 50 mm pipe | fixed elbow in the pedestal (deburr both ends) |
| 2in sch 40 PVC | 1 | 141 mm | conduit between the box and the pedestal (seal with silicone at the sandbox wall) |
| 12 mm plywood | see cut list |  | control box, pedestal, sandbox (2026-09-24-cut-list.md) |
| glue |  | wood glue; epoxy or CA | panel joints; bucket ears to the bucket lugs (as in the original EX-MA); printed knobs on the handle rods |

Rope total: 7.1 m (have at least 9 m, which includes 20 % spare). PTFE tube total: 3.7 m — buy one 5 m roll.

M3 sizes all fit inside the kit's counts.

## Wood

All wood parts, sizes and hole positions: `2026-09-24-cut-list.md` (STEP: `STEP/2026-09-24-control-box-wood.step`, `-pedestal-wood.step`, `-sandbox-wood.step`).

## Part count

- Removed from the original arm mechanism: 16 printed parts (2 double-groove drums, 4 idlers, the bucket drum + sleeve, 5 pins, 2 clips, the green slew ring, the base post cap).
- Merged: bucket bracket I (2 pieces) and lugs O/P into the bucket body.
- New arm-side mechanism parts: boom drum, stick drum, bucket drum-axle, slewing-ring retaining ring (4).
- New pedestal and conduit parts: slew drum, PEX bushing, elbow support, 2 conduit fittings (5).
- New control-box parts: 3 lever hubs, slew spool, slew wheel, spool riser, 2 sleeve posts (8).

