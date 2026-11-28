# Dancer axle wear test (by hand)

vt350#312, lite-81 (#327). The dancer's axle is a hardened 5 × 12 mm dowel pressed into the sheave's 625. Its ends
slide up and down in 1.7 mm deep grooves in the printed plates as the dancer takes up the bundle. The owner's worry
(2026-11-27): the dowel slides rather than rolls, so it may wear flat spots, and the printed grooves may wear too. An
idea with balls on rails was set aside until this test shows whether the simple axle wears at all.

The test is by hand (owner: "I don't have a way to rig it to a printer").

## The rig

`cad/studies/dancer_wear_rig_fc.py` builds it from the lite-81 pass's own parts, so the dowel slides on the surfaces
it slides on in the printer:

- **Rig** (`rig.stl`, one piece, printed standing on its base like the real stack sections): the middle of T0/T1's
  stack, Z 155–360. It has the same three plates, 1.7 mm grooves and 5.4 mm slots, plus a base flange with four
  Ø5.5 holes. The grooves run out of the top, as they do in the real middle section, so the wheel drops in from
  above.
- **Wheel**: the real two halves (`half1.stl`, `half2.stl`, printed plate face down), a 625-2RS, the dowel and
  3 × M2 × 5 cap screws into 3 × M2 heat-set inserts. It weighs about 41 g, the dancer study's 0.4 N, so it needs no
  extra weight.
- **Anchor pin**: an M4 × 25 screw and nut, or any 4 mm pin, through the hole near the top. The cord's fixed end ties
  to it. With the pin in, the wheel can't ride out of the open grooves.
- **Cord**: about 600 mm of any 5 mm cord, or a spare length of the bundle.

The STLs are written to `~/Documents/VT350/prints/dancer-wear-rig/` (not in git). The numbers are in
`cad/data/dancer_wear_rig.json`.

**Print project:** `~/Documents/VT350/prints/dancer-wear-rig/dancer-wear-rig.3mf` (OrcaSlicer, the Neptune presets
from `parts/slice/orca/`). Plate 1 is the rig, standing; plate 2 is both halves, plate face down.

**Material: PETG** (owner 2026-11-27: "I will print with petg for this"), with the Neptune's PETG preset. The real
stack and sheaves are PET-GF. Glass fibre is abrasive, so a clean result in PETG doesn't yet clear PET-GF for the
dowel. Wear on the plastic should be similar or worse in PETG. If PETG passes, one more set in PET-GF settles it.

**Slice (Orca 2.5.2, slice-check):**
- Each half: about 17 min and 15 g, with no support worth the name.
- The rig: about 4 h 32 min and 177 g. Its crossbars are the stack's 45° chevrons (owner 2026-11-27: "The crossbars
  need support ... can you make them angled at 45"), and its pin hole is a teardrop, so it prints standing with
  supports off, as the project does.
- Orca's support check, which flags overhangs at 45° and flatter, still marks the slopes: 25 g, since they sit
  exactly on its line. At 44° it leaves only one 4 mm strip (2.5 g).

## Before

1. **Measure the dowel.** Measure its diameter with a micrometer, or calipers if that's what you have, at both ends,
   in two directions 90° apart. Write the four numbers in the log.
2. **Mark the dowel.** Draw a paint-pen line along one end, facing straight up once it's assembled. Afterwards it
   shows whether the dowel turns or always slides on the same line, which is where a flat would form.
3. **Photograph the grooves** at a low angle with a light across them, so you can compare the same view afterwards.

## Assembly

1. Heat-set the three inserts into half 2 from its join face.
2. Press the dowel into the 625 so it sticks out 3.5 mm each side. It's an m6 press fit: use a vice with soft jaws.
3. Seat the 625 in half 2's pocket, close half 1 over it, and drive the three M2 screws. The lips clamp the bearing's
   outer ring.
4. Screw or clamp the rig's base to the bench. Take the pin out.
5. Lower the wheel into the first channel (the one beside the outer plate), with the dowel ends in the grooves.
6. Put the pin back. Tie the cord to it between the plates. Run the cord down, under the wheel in its groove, and up
   the far side.

## Cycling

Pull the free end straight up until the wheel nearly reaches the pin (68 mm of axle travel), then let it down
slowly. Don't let it drop. That's one cycle. A comfortable pace is about one per second.

Do it in **sets of 500**. After each set, check the dowel's mark and feel both grooves with a fingernail. After 1000,
2000 and 5000 cycles, measure the dowel at the same four places and photograph the grooves.

**Stop early if:**
- a dowel diameter drops by **0.02 mm** or more;
- the grooves show a polished track you can catch with a fingernail;
- the wheel starts to bind, or rocks in the channel.

## Log

| Date | Cycles total | Dowel Ø, end A (0° / 90°) | Dowel Ø, end B (0° / 90°) | Mark turned? | Grooves | Notes |
|---|---|---|---|---|---|---|
|  | 0 |  |  | — |  | before |
|  | 500 |  |  |  |  |  |
|  | 1000 |  |  |  |  |  |
|  | 2000 |  |  |  |  |  |
|  | 5000 |  |  |  |  |  |

## What the result decides

- **No measurable wear and smooth grooves after 5000 cycles:** keep the dowel axle.
- **Wear on the plastic grooves only:** a harder groove surface, such as a steel strip or a liner insert, or a
  different filament for the stacks.
- **Flats on the dowel:** go back to a rolling idea. The balls-on-rails sketch, with its rocking and skidding problems
  noted in vt350#327's thread, is one starting point; small bearings rolling on the axle ends in the grooves is
  another.
