# Compact control box: smallest size with no change to the arm

Specification only: no models were changed. All numbers are in mm, in the design frame of
`Source/2026-09-24-exma_common.py`:
- u runs toward the sandbox;
- v is left (+) / right (−) as seen by the operator;
- z is up.

## Result

| | Current | Compact | Change |
|---|---|---|---|
| Box outside (u × v × z) | 250 × 405 × 242 | **214 × 362 × 156** | −36 / −43 / −86 |
| Box volume | 24.5 L | 12.1 L | −51 % |
| Lever handle length (axle → knob base) | 225 | **140** | −85 |
| Handle rod cut length | 230 | **145** | −85 |
| Handle spacing | 70 | **60** | −10 |
| Knob above the lid (knob underside) | 61 | 61 | same |
| Knob to slew-wheel clearance (worst point of the swing) | 24 | 24 | same |

The joint ranges, lever swings, slew range (±90°) and reach don't change. Everything that sets
them stays exactly where it is:
- the arm, turret, pedestal, conduit and sandbox;
- the conduit fitting;
- the lever axle position (u −360, z −120);
- all drums and all rope paths from the drums to the conduit.

## What sets each dimension

**Height (242 → 156).** The floor stays on the ground (z −202). The highest part inside the box is
the conduit fitting's 100 × 100 flange: it is centred on the conduit (z −110), so its top edge is at
z −60. The lid goes 2 mm above it:
- lid underside: z −58;
- lid top: z −46.

Everything else inside is lower:
- lever hub tops: z −86;
- bearing-block tops: z −90;
- sleeve posts: z −80;
- spool drum top: z −80.

The lever axle can't come up, because its height matches the conduit's rope holes (rope entry
angles ≤ 21°).

**Handle length (225 → 140).** The lid is now 74 mm above the axle instead of 160. The handle
shortens by the same 86 mm, which keeps the knob's clearance above the lid at 61 mm, as now.

**Depth (250 → 214).** The front wall is fixed (it bolts to the sandbox wall). The axle stays at
u −360: moving it closer to the conduit would steepen the boom rope's fleet angle past the current
11.3°. The rear wall comes in to 8 mm behind the rearmost parts:
- slew spool back edge: u −396.7;
- lever drum back edge: u −392.5.

**Width (405 → 362).** The handles move from ±70 to ±60, which leaves a 24 mm gap between the Ø36
knobs (was 34 mm). The following move inward by 10 mm on each side:
- the hub sleeves;
- the bearing blocks and the axle ends;
- the wall on the left;
- the spool, the wheel and the sleeve posts on the right.

The drums stay where they are, so the rope angles don't change. The right wall sits 8 mm outside
the spool. The Ø184 wheel is unchanged and overhangs the right wall by 15 mm (on top of the lid). If
you want the wheel inside the footprint, move the right wall 27 mm further out
(v −284, box width 389).

## New layout values

These are the values to change in `Source/2026-09-24-exma_common.py` and the build scripts:

| Constant | Current | Compact |
|---|---|---|
| `BOX_U` | (−453, −203) | **(−417, −203)** |
| `BOX_V` | (−290, 115) | **(−257, 105)** |
| `BOX_Z` | (−202, 40) | **(−202, −46)** |
| `LEVERS` (handle v, drum v) | boom (70, 19), stick (0, −17), bucket (−70, −32) | **boom (60, 19), stick (0, −17), bucket (−60, −32)** |
| `LEVER_HUB_V` | boom (10.25, 80), stick (−24.75, 9.75), bucket (−80, −25.25) | **boom (10.25, 70), stick unchanged, bucket (−70, −25.25)** |
| `AXLE_BLOCK_V` | (80.5, 92.5) | **(70.5, 82.5)** |
| `HANDLE_LEN` | 225 | **140** |
| `WHEEL_C` (spool / wheel centre, u v) | (−340, −190) | **(−340, −180)** |
| `SPOOL_LEN` (build-parts) | 145 | **59** (spool top stays 9 mm above the lid top) |
| `AXLE_U`, `AXLE_Z`, drums, fitting, conduit | — | unchanged |

## Checks on the compact layout

These use the repo's own rope functions (`build-box.py`).

**Lever ropes: identical to now, because the axle and drums don't move.**

| Strand | Length | Fleet angle | Entry bend | Wrap over the swing |
|---|---|---|---|---|
| boom upper / lower | 118 / 118 | 11.3° / 11.2° | 21.4° / 14.2° | 62–105° / 52–95° |
| stick upper / lower | 116 / 116 | 4.5° / 4.4° | 18.8° / 9.7° | 63–104° / 53–94° |
| bucket upper / lower | 117 / 118 | 9.8° / 9.8° | 20.7° / 13.1° | 64–103° / 54–94° |

**Slew sleeves (spool moved 10 mm toward the levers).**

| Sleeve | Length | Total bends | Friction factor (µ 0.15) |
|---|---|---|---|
| A | 317 → **308** | 144° → 138° | 1.46 → **1.44** |
| B | 385 → **375** | 196° → 198° | 1.67 → **1.68** |

**Clearances.**
- Sleeve post A to the right-hand axle washer / nut: 2.5 / 4.1 mm (in u). This is the tightest spot
  in the compact box: fit the washer and nut before the post.
- Knob or rod to wheel rim over the full swing: 24 mm (unchanged).
- Fitting flange to lid: 2 mm.
- Hub handle sockets to lid: 28 mm.

**Lid slots (they are the lever end stops).** They get shorter because the lid is closer to the
axle:

| Lever | Swing | Slot now | Slot compact |
|---|---|---|---|
| boom | 42.5° | 133.0 × 9.0 | **66.1 × 9.0** |
| stick | 41.2° | 128.7 × 9.0 | **64.1 × 9.0** |
| bucket | 39.7° | 123.9 × 9.0 | **61.8 × 9.0** |

## Lever feel: the one real trade-off

With the Ø60 lever drums kept, the shorter handle means a shorter stroke and a heavier push. Joint
travel per lever angle is unchanged.

| | Current (225, Ø60) | Compact (140, Ø60) | Compact + Ø48 lever drums |
|---|---|---|---|
| Knob stroke, end to end (boom) | 177 | 114 | 143 |
| Force to hold the boom at the knob | 2.7 N | 4.2 N | 3.4 N |
| Knob drop at the stops | 16 | 10 | 16 |
| Lever swing (boom / stick / bucket) | 42.5 / 41.2 / 39.7° | same | 53.1 / 51.5 / 49.6° |
| Lid slots (boom / stick / bucket) | 133 / 129 / 124 | 66 / 64 / 62 | 83 / 80 / 77 |
| Rope wrap left on the lever drum | ≥ 52° | ≥ 52° | ≥ 44° |

- **Recommended: keep the Ø60 hubs.** They reuse the printed lever hubs as they are (only the handle
  block moves with the handle, see below). The forces stay small: at most 4.2 N to hold the boom,
  and about double that to raise it against the drag clamp. Control gets quicker: 0.75° of boom per
  mm of knob movement instead of 0.48°.
- **Optional, to keep today's feel:** Ø48 lever drums. The stroke comes back to 143 mm and the force
  is +24 % instead of +55 %. All rope angles stay within the current limits, as the calculation
  shows:

  | Strand (Ø48) | Fleet | Entry | Wrap |
  |---|---|---|---|
  | boom | 11.1° | ≤ 18.9° | 44–107° |
  | stick | 4.4° | ≤ 16.0° | 45–106° |
  | bucket | 9.7° | ≤ 18.1° | 46–105° |

  This needs a redesigned hub: the rope anchors inside the smaller drum have to be re-laid.
- A Ø40 drum would match today's force almost exactly (+4 %) but leaves only 37° of rope wrap and no
  room for the anchors, so it isn't recommended.

## Parts that change

**Plywood (12 mm), control box only.** The pedestal and sandbox are unchanged.

| Panel | Current | Compact |
|---|---|---|
| Floor | 250 × 405 | **214 × 362** |
| Removable top (lid) | 250 × 405 | **214 × 362** (slots as above, at v +60 / 0 / −60, u −360; spool bearing hole at u −340, v −180) |
| Front | 405 × 218 | **362 × 132** (conduit hole unchanged at v −8, z −110) |
| Rear | 405 × 218 | **362 × 132** |
| Left / right sides | 226 × 218 | **190 × 132** |
| Axle bearing blocks (2) | 60 × 12 × 100 | same size, at \|v\| 70.5–82.5 |

**Rod stock (5/16in).**

| Rod | Current | Compact |
|---|---|---|
| Lever axle | 205 | **185** |
| Slew spool axle (floor → 32 mm above the lid) | 274 | **188** |
| Handles (3) | 230 | **145** |

**Printed parts.**
- `slew-spool`: tube length 145 → 59 (drum, lanes and anchors unchanged). Reprint.
- `lever-hub-boom` and `lever-hub-bucket`: sleeve 10 mm shorter, and the handle block (socket, pinch
  clamp and drag clamp) moves 10 mm toward the centre, to v +60 / −60. Reprint.
- `lever-hub-stick`: unchanged.
- Unchanged:
  - `slew-wheel`, `spool-riser`, `slew-tube-post` (both), `lever-knob`;
  - `conduit-end-fitting-box`: same place and size;
  - every arm, turret and pedestal part.

**Ropes and tubes.**
- Arm ropes and the four PTFE tubes: unchanged.
- Slew sleeves: A 329 → **320**, B 397 → **387**.
- Slew ropes: about 9–10 mm shorter each; still crimped at assembly, so no change to the procedure.

**Box to sandbox.**
- The two lower box-to-sandbox bolts move to v −232 and v +80 (25 mm in from the new side walls,
  z −165 as before), so drill two new holes in the sandbox −u wall.
- The four fitting bolts are unchanged.

## What else changes for the user

- The knobs sit 85 mm lower above the ground: tops at 254 mm, was 339. Their height above the lid
  is unchanged.
- The lid is 86 mm below the sandbox rim instead of flush with it.
- Service is unchanged: the lid lifts off, and every crimp, loop and clamp is reachable from above.
