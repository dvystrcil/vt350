# Extrusion cut list (draft)

Measured from the model `vt350-lite-4.FCStd` on 2026-11-04 by
`cad/scripts/frame_plus100.py` (see `cad/data/logs/frame_plus100.log`).
Lengths are the bar's long axis in mm, **after** the +100 mm change.

| Profile | Length | Qty | Where in the model |
|---|---|---|---|
| 4040 | 740 | 2 | Frame verticals |
| 4040 | 470 | 6 | Frame horizontals (top + bottom) |
| 2040 | 740 | 2 | Frame verticals |
| 2040 | 740 | 2 | Door frame verticals |
| 2040 | 470 | 2 | Gantry |
| 2040 | 470 | 2 | Frame horizontals |
| 2040 | 470 | 2 | Door frame rails (top + bottom) |
| 2040 | 470 | 1 | Electronics cabinet |
| 2020 | 470 | 1 | Bed frame |
| 2020 | 380 | 1 | Rear vertical (below the gantry) |
| 2020 | 340 | 1 | Gantry |
| 2020 | 332 | 1 | Bed frame |

**Totals:** 4040: 2 × 740 + 6 × 470. 2040: 4 × 740 + 7 × 470. 2020: 470, 380, 340, 332.

## Before ordering (stage issue #7)

- [ ] Joint style chosen (full blind joints vs hybrid countersunk). It decides
      which ends are tapped and where access holes go.
- [ ] Machining list per bar added here.
- [ ] Re-measured from the model after any further frame change. Re-run
      `frame_plus100.py`'s cut-list section, or measure in FreeCAD.
- [ ] The electronics cabinet bar may change with the side/top pack decision (#5).
