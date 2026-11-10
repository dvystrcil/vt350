# Kinematic bed: tanaes's Trident mounts vs the model

Source: [tanaes/whopping_Voron_mods `kinematic_bed`](https://github.com/tanaes/whopping_Voron_mods/tree/main/kinematic_bed)
(GPL-3.0). The user owns West3D's aluminium Trident kinematic kit (`notes/parts-owned.md`).
Checked 2026-11-05 against `vt350-lite-16.FCStd`, using his `DXFs/Trident/*.dxf` (laser-cut outlines),
`trident_kinematic-BOM.txt` (thicknesses) and `README_trident_assembly.md`.

## What the model has now

The `Kinematic bed mount` group carries tanaes's **V2.4** parts, not the Trident set. Their sizes match his v24
design, not the Trident DXFs:

| Model part | Model size (mm) | Trident DXF part | Trident size (mm) |
|---|---|---|---|
| `front_support_top_3` | 25.5 × 55.3 × 2 | C/D left/right top | 55.5 × 31.0 × 2 |
| `front_support_bottom_3` | 25.5 × 40.0 × 3 | E/F left/right bottom | 48.4 × 31.0 × 3 |
| `back_support_3_top` | 43.6 × 50.5 × 2 | H back top | 24.7 × 49.3 × 2 |
| `Leaf_spring` | 25.5 × 39.6 | J spring | 44.3 × 31.0 |

**The two front mounts sit on nothing.** Their balls are at Y ≈ 132, but the Trident bed frame's front extrusion
(`2020 (1)`) runs Y 60.8–80.8, and the only other bed extrusion is the centre spine at X −245. The V2.4 design
expects the V2.4 bed extrusions.

The corner bearings are still on the **printed** Trident holders (`Z_Bed_Left/Right/Rear`, each with a GE5C).

## What the Trident set changes, and how it lines up with the model (verified from the DXFs)

| Trident part | Thickness | Replaces | Fit check against the model |
|---|---|---|---|
| A left / B right bearing plate (+ I bearing retain) | 3 mm (I: 3 mm) | printed `Z_Bed_Left/Right` holders; same GE5C | A/B: GE5C bore Ø14.03, two M5 FHCS holes 24 mm apart and **22.0 mm behind the bore**. Model: front GE5C at Y 48.8, front extrusion slot centreline Y 70.8, **22.0 mm**. A is used rotated 180° and B flipped, so both M5s land on the extrusion (left X −450.6 / −474.6, right X −40.1 / −16.1, extrusion X −480 to −10). |
| G back bottom (+ H back top, I retain, 2 dowels) | G 3 mm, H 2 mm | printed `Z_Bed_Rear` holder and the model's `back_sandwich` | G: GE5C bore Ø14, then three M3 holes **22.3 / 35.7 / 64.9 mm** along its centreline. Model: rear GE5C at (−244.9, 426.1), spine at X −245 ending at Y 412.8, so the M3s land at Y 403.8 / 390.4 / 361.2, **all on the spine**. H registers on G: H's four Ø3.4 holes fall on G's 35.7 hole, its two tapped holes at ±11.37 / 50.3, and its 64.9 hole. |
| C/D top + E/F bottom (+ 2 dowels each) | 2 mm / 3 mm | the model's two floating front sandwiches | C on E checks out: C's clamp holes match E's tapped pair (Δ 14.74 / −20.06), and C's other two holes match E's slot holes, 39.41 mm apart. **Their position along the front extrusion is not in the DXFs.** It is set by where the bed's front mount holes are, and it lives only in his Fusion files (`.f3z`, which FreeCAD can't open). |

Also from the BOM: 3 × 9 mm M3 sphere nuts (the balls), 6 × M5x20 dowel pins, and 28 ga spring-steel leaf springs.
The README says to **lengthen the Z endstop pin by about 8 mm**.

## Front position: resolved (lite-17, 2026-11-05)

The bed is the user's **LDO 350 plate kit** (heater label `LDO-SHPAC-350-120-750`; `notes/parts-owned.md`), not a
Kobra Plus. Its aluminium is about **10 mm** thick (user's measurement; 13.5 mm with the heater and magnet sheet).

Where the front balls go:

- tanaes's README: each ball hangs from one of the bed's own mount points ("front left and right standard V2 mount points,
  rear center mount point"). The bolt carries the leaf spring, a thin nut and the sphere nut.
- The model plate's front holes are at (−415.5, 71) and (−74.5, 71): 7 mm in from each side and 43 mm back from the front
  edge, right over the front extrusion's slot (Y 70.8). Rear hole: (−245, 376), on the spine.
- The user's photo of the underside (ruler along the front) shows the same pair. They are small holes in heater cut-outs on
  the left and right edges, about 6–7.6 mm in and 41–43 mm back (photo scale, ±1–2 mm). They are partly under the ruler, so
  **measure them before drilling or ordering anything**. The plate also has holes in the front-edge cut-outs (±75 from
  centre, 6 mm from the edge) and four corner holes 20.7 mm in. Those are not the Trident mount points.
- With E's end holes on the slot centreline, the pin groove passes through the bed hole at exactly one position along the
  extrusion. That position puts C/E **54.7 mm inboard of A's bore**, the same spacing the A and C DXFs are drawn at. The
  front sources agree to 0.1 mm. The leaf spring checks out too: its oval end lands on C's tapped hole 28.3 mm from the
  ball.

What lite-17 found (`cad/data/logs/lite17_kinematic.log`):

| | |
|---|---|
| Bearing height | GE5C goes in from below with I on top, so the outer ring's top is level with A/B/G's top. The bearing centre is 1 mm above the bed frame, which moves the front Z carriages −2.85 mm and the rear +1.55 mm relative to the bed frame. That's fine with three independent Z motors; z-tilt absorbs it. |
| C/D/H height | Their cut-out ends bear on the pins, so they sit **4.1 mm above** E/F/G rather than flat on them. A BOM M3x8 BHCS then reaches only about 1.9 mm into E's 3 mm tapped hole. **Check the thread engagement when assembling**; M3x10 if it's thin. |
| Grooves | Front 36.3° / 143.7°, rear 90°. The directions to the three-ball centroid are 30.8° / 149.2° / 90°, so the front grooves are about 5.5° off radial. That's tanaes's design and is unchanged here. |
| Plate height | Plate top moves **+17.6 mm** relative to the front Z carriages: 4 mm from the thicker plate, the rest from the kinematic stack and bearing seat. tanaes quotes about 8 mm against a stock Trident. The old model's plate sat only 5 mm above the bed frame, so the difference may be in that baseline. lite-10's max print height (347.8 mm) needs re-checking. |
| Bed bolts | M3 SHCS through the plate: (plate below its counterbore) + 0.38 spring + 1.8 nut + 2–3 mm protruding. The counterbore depth on the real plate isn't known, so measure it before buying the 3 bolts. |

Still to do: the README says to lengthen the Z endstop pin by about 8 mm. Fasteners aren't modelled in lite-17.

## lite-18: the real build plate (measured 2026-11-05)

The model's plate (`Universal Build Plate 350`) was a generic one. It had edge notches and rear corner ears, and a
pair of holes the real plate doesn't have. lite-18 (`cad/passes/lite18_plate.py`) replaces it with the user's
LDO plate. The measurements came from calipers, a depth gauge, and a photo of the underside (scale 7.76 px/mm,
±1 mm). The hole sketch is `~/Documents/VT350/bed-plate-holes-5.FCStd`, which is local and not committed.

| Item | Value | How it was measured |
|---|---|---|
| Plate | 355 × 355 × 10, square, edges chamfered | calipers |
| Holes | all Ø3.4 through, Ø6.5 counterbore on the magnet face, 4.9 deep in the aluminium (6.3 with the magnet on) | calipers: 153.4 outside / 146.6 inside → 150.0 C-C, Ø3.4 |
| Magnet sheet | 1.4 | 11.4 plate + magnet |
| PEI spring-steel print sheet | 1.0 | user; not modelled in lite-18 |
| Heater pad | 1.5 (LDO-SHPAC-350-120-750) | depth gauge |
| Pad hold-downs | 4 pan head + washer, Ø~12, 2.0 tall; 3.8 below the aluminium | 15.2 from the top of the magnet to the head |

Holes are given in plate coordinates: the origin is the front-left corner, viewed from the magnet side, and the rear is the wire exit.

| Hole | From left | From front | Notes |
|---|---|---|---|
| F150 L/R | 102.5 / 252.5 | 6.5 | in 30 × 12.5 pad notches (87–117 from the side edge, lite-22), about 36 mm in front of the front bed extrusion, so tanaes's C/E can't reach them |
| **K341 L/R** | 7 / 348 | 43 (calipers, lite-22) | **the front kinematic balls**, in 12.5-wide pad strips (28.5–58.5 from the front) |
| **Rear centre** | 177.5 | **348.5** (lite-20; lite-18 had 349.5) | **the rear ball**, 0.5 mm back along G's groove from lite-17 |
| R150 L/R | 102.5 / 252.5 | 348.5 | in the rear pad strip (92.5–262.5, **12.3** deep) |
| Fuse / lock washer | 122.5 / 232.5 | 348.5 | screws already fitted: a 15 A fuse and a lock washer, 55 from the centre each (calipers, lite-22) |

**Findings:**
- **The springs fit the pad cut-outs.** Only about a third of each spring is under the plate. The rest hangs
  outboard toward C/D/H. The part under the plate lies inside the cut-out. The overlaps with the pad are slivers
  along the cut-out edges: 0.9 / 5.4 / 1.7 mm², under 0.5 mm into the pad, which is below the photo's ±1 mm. Check
  by eye at assembly, and trim the pad's edge by 1 mm if a spring corner sits on the silicone.
- The front hold-downs are 3.5 mm clear of C/D. The rear ones are about 135 mm from any mount.
- **Bed bolts are M3 SHCS, 10 mm.** This corrects lite-18's log and PR #42, which said 14 mm. tanaes's README
  (Step 1) says to fit the spring with the thin hex nut so that **2–3 mm of thread sticks out past the nut**, then
  to thread the sphere nut on "until it bottoms out on the hex nut". So the sphere nut is only meant to take 2–3 mm
  of thread. Under the head the stack is the 5.1 floor + 0.38 spring + 1.8 nut = 7.28, which makes 9.3–10.3 the
  right length, and 10 mm leaves 2.7 mm sticking out. lite-18's 14 mm assumed the bolt could run deep into the ball.
  The model's sphere nut is a plain solid, so it can't show how deep the real one is threaded.

## lite-20: the rear hole row, re-measured (2026-11-05)

Two ruler photos of the underside (Immich export `immich-20261105_133334.zip`: `PXL_20261105_212953005` with the
ruler along the rear strip, `PXL_20261105_213013523` across it). The cm ticks were located by pixel-column
profiles, not by eye. `cad/passes/lite20_rear_row.py` applies the result to lite-19.

| Measured | Value | lite-18/19 |
|---|---|---|
| Pad edge → rear hole centre | 5.75 | 5.8 |
| Plate's rear edge → pad edge (rear strip depth) | **12.3** | 11.3 |
| Plate's rear edge → rear hole centre | **6.55 → row at 348.5** | 5.5 (349.5) |
| R150 pair, about the centre hole | ±75.0 (raw 148.8 C-C, scaled to 150.0: the ruler sits above the plate) | ±75 |
| Fuse / lock-washer screws, from the centre hole | −55.4 / +54.7 → 122.1 / 232.8 | 121.5 / 233.5 |
| Rear strip length | 169.9, centred on the centre hole within 0.5 | 170 |

The plate's edge has a ~1 mm chamfer (a grey, unbrushed band in the photo). The first photo estimate measured to its
inside edge, so it read about 1 mm short, the same bias as the front row (photo 5.8, ruler 6.5). The rear row now
also sits 6.5 from its edge, so the two rows are symmetric.

The rear ball, thin nut and spring slide 1.0 mm forward along G's groove (it runs front-to-back), to Y 376.5.

## lite-22: the pad cut-outs and the front-ball holes, measured with calipers (2026-11-05)

Measured by the user from the plate's outer edge, heater side up, front edge nearest.
`cad/passes/lite22_pad_cutouts.py` applies them to lite-21.

| Measured | Calipers | Photo estimate (lite-18) |
|---|---|---|
| K341 holes: side edge / front edge | **7 / 43** (confirmed) | 7 / 43 |
| Side strips: width | **12.5** | 11 |
| Side strips: front end / rear end, from the front edge | **28.5 / 58.5** | 28 / 59 |
| Front notches: from the nearest side edge | **87–117** (30 wide, centred on F150) | 85–120 |
| Front notches: depth | **12.5** (F150 at 6.5 sits mid-depth) | 10.3 |
| Fuse / lock-washer screws | **55 from the centre each** | 55.4 / 54.7 |

All the photo estimates of pad edges came out 1.5–2 mm short, like the rear strip in lite-20: the edge chamfer.
The fuse is right of the centre seen heater-side up with the front nearest (photo `PXL_20261105_212953005`), as modelled.

With the measured strips, the front springs overlap the pad by 1.7 / 6.8 mm² (lite-18: 0.9 / 5.4), slivers under
1.6 mm wide at the strips' front ends. The springs are drawn flat, before preload. Check at assembly; trim the
strip's front end by about 2 mm if a corner sits on the silicone.

The rear R150 pair stays at 102.5 / 252.5. A first reading of "112" didn't fit. The user's follow-up photo
`PXL_20261105_233549490` (ruler zeroed on the lock-washer screw) gives: R150 ~19, centre hole ~54.6, fuse screw 110,
far R150 ~131. That is 150 C-C about the centre hole, matching lite-20, and 110 screw-to-screw.

## Fastener stacks through the C/D/H sandwiches (measured in lite-18)

At all three mounts the top plate is 2.0 mm and rests on the dowel pins **4.10 mm above** the 3.0 mm bottom plate.

| Screw (README / BOM) | Path | Thread engaged | What's below | Use |
|---|---|---|---|---|
| M3x8 BHCS clamp, C/E and D/F (2 each) | 2 + 4.1 gap, into E/F's tapped hole | 1.9 mm (about 4 threads) of 3 | The tapped holes sit on the front extrusion's edge (Y 60.77 / 80.83 vs 60.8 / 80.8) | **M3x8** as specified. A 10 would stick out 0.9 onto the extrusion's corner. M3x9, if you can get it, gives 2.9 and stays inside E/F. |
| M3x8 BHCS clamp, H/G (2) | 2 + 4.1, into G's tapped hole | 1.9 of 3 | Nothing: the holes are 11.4 off the spine's centre, outside the 20 mm extrusion | **M3x10**: the full 3 mm of thread, and the 0.9 that sticks out is in air |
| M3x14 BHCS to the channel nuts (C/E and D/F ends, 2 of H/G's holes) | 2 + 4.1 + 3 = 9.1, then the slot | 4.9 below the bottom plate | The slot floor is 6.3 below | **M3x14**, as the README says. The BOM lists M3x12, which leaves little thread in the channel nut |
| M3x6 SHCS preload screw (spring tip) | spring 0.38, into C/D/H's tapped hole | 2 (the plate's full thickness) | Air or slot, more than 4 mm clear | as specified |

Source: `README_trident_assembly.md` steps 1–5 and `DXFs/Trident/trident_kinematic-BOM.txt`, as of 2026-11-05.
- The print surface is **2.4 mm above the aluminium**: 1.4 of magnet plus 1.0 of PEI sheet. lite-18 models the magnet
  only. The max print height re-check has to include both.
