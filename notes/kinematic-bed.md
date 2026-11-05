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

## Open before modelling the front pair

- **Where are the bed's front mount holes?** The bed is a Kobra Plus heater on the
  `Universal Build Plate 350`. If the bed has no holes where the front mounts need them, tanaes ships drill guides
  (`STLs/drill_guide_standard.stl`, `drill_guide_slots.stl`).
- Alternatively, take the front-mount position from his Fusion assembly. Someone with Fusion would need to export a STEP.

The bearing plates (A/B, G/H, I) are anchored by their holes and can go in now. That's the next pass.
