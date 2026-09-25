# EX-MA manual excavator — print and assembly checklist

Tick the boxes as you go. Quantities, lengths and plates come from the build scripts (the same data as `2026-09-24-bill-of-materials.md`), so this list matches the files in `STL/`, `3MF/` and the cut list. Directions: u = along the arm, v = sideways (+v = operator's left), z = up.

## 1. Before you start

**Tools**

- [ ] 2.5 mm hex key (M3 socket cap) and 2 mm hex key (M3 button head)
- [ ] 5.5 mm wrench or nut driver (M3 nuts), 11/32in wrench (8-32 nuts), 1/2in wrench (5/16in nuts)
- [ ] crimp tool for 1/16in sleeves, wire-rope cutter
- [ ] PTFE tube cutter (or a new razor blade: cut square), pipe cutter or hacksaw (PVC, copper), deburring tool
- [ ] drill with 3.5 mm and 2 mm bits (M3 clearance, wood-screw pilots), screwdriver
- [ ] wood glue, CA or epoxy (bucket ears), silicone (conduit seal), a few cable ties
- [ ] fine marker and masking tape to label rope and tube pieces

**Sort the hardware** (one small bag per step below)

- [ ] 45 × M3 nut — for the M3 screws in the steps below
- [ ] 36 × M3 flat washer — for the M3 screws in the steps below
- [ ] 27 × M3 split-lock washer — for the M3 screws in the steps below; split-lock washers under the nuts that hold moving or clamping parts
- [ ] #4-40 and #6-32 machine screws — not needed (spares)

## 2. Print (0.6 mm nozzle)

Settings for every part: PLA or PETG, 0.6 mm nozzle, 0.2 mm layers, at least 4 walls, 40 % infill for drums, hubs, clamps and anything carrying a pin (20 % elsewhere). The plates in `3MF/` already have each part in its print orientation; every wall was checked for the 0.6 mm nozzle (`Validation/2026-09-25-wall-check.json`).

Print the plates in this order; it follows the build order, so each step's parts are ready when you get there. After each plate, do its fit test before printing the next.

- [ ] **`3MF/2026-09-24-plate-07.3mf`** — conduit-end-fitting-pedestal (supports: yes (28 cm²))
  - [ ] fit test: copper elbow pushes into the round socket; a PTFE tube slides freely through the rounded window
- [ ] **`3MF/2026-09-24-plate-03.3mf`** — slewing-ring-retaining-ring (supports: none); lever-knob-3 (supports: light (1.5 cm²)); boom-drum (supports: light (1.4 cm²)); stick-drum (supports: light (1.3 cm²)); elbow-support (supports: light (0.6 cm²))
  - [ ] fit test: each drum sits flat; (after plate 02) a BB rolls freely in the race between the base rim and the retaining ring
- [ ] **`3MF/2026-09-24-plate-01.3mf`** — slew-wheel (supports: yes (11 cm²)); bucket (supports: yes (27 cm²)); spool-riser (supports: none); slew-tube-bushing (supports: none); bucket-ear-left (supports: light (1.2 cm²)); bucket-ear-right (supports: light (1.2 cm²)); slew-tube-post-1 (supports: none); slew-tube-post-2 (supports: none)
  - [ ] fit test: PEX tube turns freely in the bushing; the spool riser sits flat
- [ ] **`3MF/2026-09-24-plate-06.3mf`** — tower (supports: yes (53 cm²)); stick-half-right (supports: light (6.9 cm²)); conduit-end-fitting-box (supports: yes (28 cm²))
  - [ ] fit test: 4 PTFE tubes seat together in the box fitting's rounded window and stop on its floor
- [ ] **`3MF/2026-09-24-plate-02.3mf`** — base (supports: yes (28 cm²)); lever-hub-stick (supports: yes (33 cm²)); lever-hub-boom (supports: yes (35 cm²)); lever-hub-bucket (supports: yes (26 cm²)); lever-knob-1 (supports: light (1.5 cm²)); lever-knob-2 (supports: light (1.5 cm²)); bucket-drum-axle (supports: light (0.7 cm²))
  - [ ] fit test: the 5/16in rod slides through all three lever hubs and into their handle sockets, and into a knob's bore
- [ ] **`3MF/2026-09-24-plate-04.3mf`** — boom-half-left (supports: yes (11 cm²)); slew-drum (supports: yes (14 cm²)); slew-spool (supports: yes (21 cm²))
  - [ ] fit test: the slew drum slides onto the PEX tube (clamp open); the spool turns on the 5/16in rod
- [ ] **`3MF/2026-09-24-plate-05.3mf`** — boom-half-right (supports: yes (14 cm²)); stick-half-left (supports: light (5.8 cm²))
  - [ ] fit test: (with plate 06) the bucket drum-axle journals turn freely in both stick-half nose holes

## 3. Cut the stock

- [ ] Wood: every panel in `2026-09-24-cut-list.md` (12 mm plywood), holes and slots as listed there
- [ ] 2 × 8-32 rod, boom split pin (tower cheek → boom wall) (42 mm) — a jam pair (2 nuts) on the outer end
- [ ] 2 × 8-32 rod, stick split pin (boom tip → stick wall) (22 mm) — a jam pair (2 nuts) on the outer end
- [ ] 1 × 8-32 rod, bucket pin (ears + drum-axle) (65 mm) — a jam pair at each end
- [ ] 8-32 rod used (203 of 914 mm) — the rest is spare
- [ ] 2 × 5/16in rod (have) (205 mm, 274 mm) — lever axle; slew spool axle
- [ ] 1 × 3/4in PEX-B tube (have) (120 mm) — turning turret tube
- [ ] 1 × 2in sch 40 PVC (141 mm) — conduit between the box and the pedestal (seal with silicone at the sandbox wall)
- [ ] 3 × 5/16in rod (have) (230 mm) — lever handles (printed knobs glued on top)

Rope and PTFE: cut each piece and label it with tape (each is listed again in the step that uses it).

- [ ] 1384 mm — boom circuit
- [ ] 1821 mm — stick circuit
- [ ] 2173 mm — bucket circuit
- [ ] 829 mm — slew rope A
- [ ] 900 mm — slew rope B
- [ ] 647 mm — stick_hi
- [ ] 658 mm — stick_lo
- [ ] 813 mm — bucket_hi
- [ ] 822 mm — bucket_lo
- [ ] 339 mm — slew sleeve A
- [ ] 407 mm — slew sleeve B

## 4. Sandbox and pedestal

- [ ] Build the sandbox (floor + 4 walls) and the pedestal walls on the sandbox floor; leave the pedestal's +u wall off for access.
- [ ] Fit the pedestal conduit fitting to the -u pedestal wall.
- [ ] Push the copper elbow into the fitting's socket; screw the elbow support to the floor under it and cable-tie the elbow down.
- [ ] Fit the shelf on its cleats and screw the PEX bushing to it.

Hardware:

- [ ] 4 × M3 × 25 socket cap — pedestal conduit fitting to the pedestal wall (fitting 6 + wall 12 mm)
- [ ] 1 × 1/2in copper (have) (90° sweep elbow (R ≈ 30) + 50 mm pipe) — fixed elbow in the pedestal (deburr both ends)
- [ ] 16 × #6 × 3/4in wood screw — bearing blocks (from below), spool riser, sleeve posts, PEX bushing, elbow support
- [ ] 120 × #6 × 1-1/4in wood screw — panel joints, ~4 per edge (box 12 edges, pedestal 10, sandbox 8), with wood glue
- [ ] 12 mm plywood (see cut list) — control box, pedestal, sandbox (2026-09-24-cut-list.md)

**Check:** the elbow's top opening is centred under the bushing; the copper does not move when pulled.

## 5. Control box

- [ ] Build the box (floor, rear, sides, front) with the top left off.
- [ ] Screw the two bearing blocks, the spool riser and the two sleeve posts to the floor (from below).
- [ ] Slide the three lever hubs onto the lever axle rod (order boom, stick, bucket from +v) and set the rod in the bearing blocks with a nut and washer outside each block.
- [ ] Put the slew spool on its axle rod over the riser (washer between).
- [ ] Fit the box conduit fitting inside the box front; bolt through the fitting, the box front and the sandbox wall; bolt the lower corners of the box front to the sandbox wall.
- [ ] Cut the conduit to length, fit it between the two fittings and seal it at the sandbox wall.

Hardware:

- [ ] 4 × M3 × 35 socket cap — box conduit fitting through the box front and the sandbox wall (6 + 12 + 12 mm)
- [ ] 2 × M3 × 30 socket cap — box front to the sandbox wall, lower corners (12 + 12 mm)
- [ ] 4 × 5/16in nut + washer (5/16in) — 2 on the lever axle (outside the bearing blocks), 2 on the spool axle
- [ ] 1 × 2in sch 40 PVC (141 mm) — conduit between the box and the pedestal (seal with silicone at the sandbox wall)

**Check:** each lever hub turns freely on the axle; the spool turns freely.

## 6. Slewing ring and turret

- [ ] Screw the base to the pedestal top.
- [ ] Clamp the turret hub on the PEX tube; feed the tube down through the base, the pedestal top, the bushing and into the slew drum (clamp still loose).
- [ ] Drop the BBs into the base race, lower the turret onto them, and bolt the retaining ring on (nuts slide into the slots in the base rim).
- [ ] Clamp the slew drum on the PEX tube at the slew-rope layer (level with the pedestal fitting's upper holes).

Hardware:

- [ ] 4 × #8 × 1in wood screw — base to the pedestal top
- [ ] 8 × M3 × 12 socket cap — slewing-ring retaining ring: holds the turret down on the BBs (nuts slide into the slots in the base rim)
- [ ] 57 × 6 mm airsoft BBs (or 1/4in steel balls) (Ø6) — slewing ring (+ ~5 spares)
- [ ] 2 × M3 × 25 socket cap — pinch clamps on the PEX turret tube (turret hub, pedestal slew drum)

**Check:** the turret turns by hand with no rocking and no lift; if it rocks, shim under the retaining ring.

## 7. PTFE tubes

- [ ] Seat each arm tube in the box fitting's window (conduit side), then feed it through the conduit, the pedestal window, the copper elbow and up the PEX tube into the tower.
- [ ] Lay each tube along its channels in the boom (and, for the bucket tubes, the stick) to its stop bulkhead; trim the 10 mm extra so it seats on the stop.

Hardware:

- [ ] 1 × PTFE tube 4 mm OD × 2 mm ID (647 mm) — stick_hi (box fitting -> arm stop) (+10 mm to trim)
- [ ] 1 × PTFE tube 4 mm OD × 2 mm ID (658 mm) — stick_lo (box fitting -> arm stop) (+10 mm to trim)
- [ ] 1 × PTFE tube 4 mm OD × 2 mm ID (813 mm) — bucket_hi (box fitting -> arm stop) (+10 mm to trim)
- [ ] 1 × PTFE tube 4 mm OD × 2 mm ID (822 mm) — bucket_lo (box fitting -> arm stop) (+10 mm to trim)

**Check:** each tube slides a few mm in the arm when pushed; the spare length coils loosely in the conduit.

## 8. Arm

- [ ] Boom: set the boom drum between the boom halves with its 4 key screws (heads in the wall pockets); fit the two boom split pins through the tower cheeks into the boom walls; close the halves with the lug screws.
- [ ] Stick: the same with the stick drum and the stick split pins through the boom tip.
- [ ] Bucket: glue the ears onto the bucket lugs; put the bucket drum-axle into the stick nose (hex ends into the ears) and fit the bucket pin through ears and drum-axle.

Hardware:

- [ ] 8 × M3 × 12 socket cap — joint-drum key screws: lock the boom and stick drums to their arm members (4 per drum, 2 through each side wall; the heads sit in pockets in the wall)
- [ ] 8 × M3 × 20 socket cap — joining lugs: clamp the two halves of the boom (4) and the stick (4) together
- [ ] 2 × 8-32 rod, boom split pin (tower cheek → boom wall) (42 mm) — a jam pair (2 nuts) on the outer end
- [ ] 2 × 8-32 rod, stick split pin (boom tip → stick wall) (22 mm) — a jam pair (2 nuts) on the outer end
- [ ] 1 × 8-32 rod, bucket pin (ears + drum-axle) (65 mm) — a jam pair at each end
- [ ] 12 × 8-32 hex nuts (12 of 22) — jam nuts on the pins (two nuts tightened against each other)
- [ ] glue (wood glue; epoxy or CA) — panel joints; bucket ears to the bucket lugs (as in the original EX-MA); printed knobs on the handle rods

**Check:** each joint swings through its full range without rubbing (boom −40…+45°, stick −45…+50°, bucket −55…+85°).

## 9. Arm ropes (boom, stick, bucket)

- [ ] Set the joint to the middle of its working range and the lever vertical.
- [ ] Seat the rope's midpoint single crimp in the joint drum's pocket; wrap one tail each way in the groove.
- [ ] Feed both tails back: boom ropes straight down the PEX tube; stick and bucket ropes inside their PTFE tubes; then through the conduit and the box fitting to the lever drum.
- [ ] Pass each tail through its rim hole on the lever drum, crimp a loop (double crimp) and hook it between two washers on its slotted anchor.
- [ ] Tension: slide the anchors outward until the rope is taut with the lever vertical, then tighten.
- [ ] Direction check: pushing a lever forward should give boom down / stick out / bucket dump. If one is reversed, reverse that rope's wrap on its joint drum.

Hardware:

- [ ] 1 × 1/16in galvanized 7x19 rope (have) (1384 mm) — boom circuit: one length, single crimp at the midpoint on the joint drum, double-crimp loops on the lever anchors (+60 mm per loop included)
- [ ] 1 × 1/16in galvanized 7x19 rope (have) (1821 mm) — stick circuit: one length, single crimp at the midpoint on the joint drum, double-crimp loops on the lever anchors (+60 mm per loop included)
- [ ] 1 × 1/16in galvanized 7x19 rope (have) (2173 mm) — bucket circuit: one length, single crimp at the midpoint on the joint drum, double-crimp loops on the lever anchors (+60 mm per loop included)
- [ ] 5 × single crimp sleeve (have) (1/16in) — 3 joint-drum midpoints + 2 slew rope ends (+ spares)
- [ ] 8 × double crimp sleeve (have) (1/16in) — 6 arm tail loops + 2 slew loops (+ spares)
- [ ] 8 × M3 × 10 button head — slotted rope-tail anchors = tension adjusters (2 per lever, 2 on the spool); the rope loop sits between two washers

**Check:** moving one lever moves only its own joint (hold the others and watch their ropes).

## 10. Slew ropes

- [ ] Feed each slew PTFE sleeve from its post beside the spool through the box fitting and the conduit into its angled counterbore in the pedestal fitting.
- [ ] Crimp the slew rope's end (single crimp) into its lane pocket on the pedestal slew drum; run the rope through its sleeve to the spool.
- [ ] With the arm pointing straight out and the wheel centred, loop the rope (double crimp) onto the spool anchor and tension it.

Hardware:

- [ ] 1 × 1/16in galvanized 7x19 rope (have) (829 mm) — slew rope A: single crimp in the pedestal drum pocket, double-crimp loop on the spool anchor
- [ ] 1 × 1/16in galvanized 7x19 rope (have) (900 mm) — slew rope B: single crimp in the pedestal drum pocket, double-crimp loop on the spool anchor
- [ ] 1 × PTFE tube 4 mm OD × 2 mm ID (339 mm) — slew sleeve A (post -> pedestal fitting) (+10 mm to trim)
- [ ] 1 × PTFE tube 4 mm OD × 2 mm ID (407 mm) — slew sleeve B (post -> pedestal fitting) (+10 mm to trim)

**Check:** wheel left turns the arm left; the wheel reaches ±90° with rope still wrapped on both drums.

## 11. Top panel, handles and wheel

- [ ] Screw the top panel on; push the 5/16in rod handles through the slots into the hub sockets and tighten each handle's pinch clamp.
- [ ] Glue a printed knob onto each handle (CA or epoxy); bolt the slew wheel to the spool flange.
- [ ] Set each lever's drag clamp so the lever holds its position with the arm loaded (boom needs the most).

Hardware:

- [ ] 3 × M3 × 20 socket cap — handle pinch clamps: hold each 5/16in rod handle in its lever hub
- [ ] 3 × M3 × 20 socket cap — slew wheel to the spool flange
- [ ] 3 × M3 × 20 socket cap — lever drag clamps: squeeze the 5/16in rod to set each lever's holding friction

**Check:** each lever stops at both ends of its slot (the slot is the hard stop); nothing rubs the top panel.

## 12. Final function test

- [ ] Each lever end to end: its joint moves through its whole working range and stops at the slot ends.
- [ ] Wheel ±90°: the arm follows 1:1 and no rope jumps its groove.
- [ ] No coupling: move the boom and the stick through their ranges while watching the bucket (it must not move).
- [ ] Ropes stay in their grooves at every end stop; no PTFE tube is pinched at the joints.
- [ ] Re-tension every circuit after the first hour of use (rope stretch and crimp seating).

**Service:** the box top and the pedestal +u wall come off; any drum or rope can be replaced by opening one arm half (lug screws).
