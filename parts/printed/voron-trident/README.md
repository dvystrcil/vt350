# Voron Trident R1 (stock parts)

Copied **unchanged** from [VoronDesign/Voron-Trident](https://github.com/VoronDesign/Voron-Trident) at commit [`86eae85`](https://github.com/VoronDesign/Voron-Trident/tree/86eae85057df4e3d1a07fe7eae44d6126724fe00). By the Voron Design team.

**Licence:** **GPL-3.0** (the upstream repository's `LICENSE`, copied here unchanged). Redistribution is allowed, including of modified versions, under the same licence. It requires: the licence text alongside, the copyright and licence notices kept, and the corresponding source available. For a printed part the source is the upstream CAD, which stays at the pinned commit linked below.

Pinned to tag `VTr1` (R1). `main` upstream is R2, which the Trident Backbone doesn't fit (see `bom/printed-parts.md`). In the file names, `_xN` is the quantity to print and `[a]` is an accent-colour part.

| File here | Upstream path at the pinned commit | Qty | Our changes |
|---|---|---|---|
| `z_carriage_left.stl` | [`STLs/Z_Assembly/z_carriage_left.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Z_Assembly/z_carriage_left.stl) | 1 | none |
| `z_carriage_right.stl` | [`STLs/Z_Assembly/z_carriage_right.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Z_Assembly/z_carriage_right.stl) | 1 | none |
| `[a]_z_carriage_left.stl` | [`STLs/Z_Assembly/[a]_z_carriage_left.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Z_Assembly/%5Ba%5D_z_carriage_left.stl) | 1 | none |
| `[a]_z_carriage_right.stl` | [`STLs/Z_Assembly/[a]_z_carriage_right.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Z_Assembly/%5Ba%5D_z_carriage_right.stl) | 1 | none |
| `z_carriage_rear_2hole.stl` | [`STLs/Z_Assembly/z_carriage_rear_2hole.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Z_Assembly/z_carriage_rear_2hole.stl) | 1 | none |
| `z_carriage_rear_3hole.stl` | [`STLs/Z_Assembly/z_carriage_rear_3hole.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Z_Assembly/z_carriage_rear_3hole.stl) | 1 | none |
| `[a]_z_rail_stop_x3.stl` | [`STLs/Z_Assembly/[a]_z_rail_stop_x3.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Z_Assembly/%5Ba%5D_z_rail_stop_x3.stl) | 3 | none |
| `z_rear_extrusionbracket_left.stl` | [`STLs/Z_Assembly/z_rear_extrusionbracket_left.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Z_Assembly/z_rear_extrusionbracket_left.stl) | 1 | none |
| `z_rear_extrusionbracket_right.stl` | [`STLs/Z_Assembly/z_rear_extrusionbracket_right.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Z_Assembly/z_rear_extrusionbracket_right.stl) | 1 | none |
| `10mm_extrusion_drill_guide.stl` | [`STLs/Tools/10mm_extrusion_drill_guide.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Tools/10mm_extrusion_drill_guide.stl) | 1 | none |
| `140mm_extrusion_drill_guide.stl` | [`STLs/Tools/140mm_extrusion_drill_guide.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Tools/140mm_extrusion_drill_guide.stl) | 1 | none |
| `MGN9_rail_guide_x2.stl` | [`STLs/Tools/MGN9_rail_guide_x2.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Tools/MGN9_rail_guide_x2.stl) | 2 | none |
| `MGN12_rail_guide_x2.stl` | [`STLs/Tools/MGN12_rail_guide_x2.stl`](https://github.com/VoronDesign/Voron-Trident/blob/86eae85057df4e3d1a07fe7eae44d6126724fe00/STLs/Tools/MGN12_rail_guide_x2.stl) | 2 | none |

Each file's sha256 is in `../manifest.csv`; `platform/parts/check-printed.py --upstream` re-downloads every file at its commit and compares.
