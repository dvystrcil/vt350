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
