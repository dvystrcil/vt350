# Extrusion cut list (draft)

Measured from the model `vt350-lite-4.FCStd` on 2026-11-04 by
`cad/scripts/frame_plus100.py` (see `cad/data/logs/frame_plus100.log`), then
updated for **lite-6** (+80 mm of Y at the front, `cad/scripts/lite6.py`).
Lengths are the bar's long axis in mm.

| Profile | Length | Qty | Where in the model | lite-6 change |
|---|---|---|---|---|
| 4040 | 740 | 2 | Frame verticals (rear) | |
| 4040 | **550** | 4 | Frame horizontals, sides (top + bottom) | was 470 |
| 4040 | 470 | 2 | Frame horizontals, rear (top + bottom) | |
| 2040 | 740 | 2 | Frame verticals (front) | moved 80 mm forward |
| 2040 | **380** | 2 | **Z posts** (the old front verticals' position; carry the front Z rails) | **new** |
| 2040 | 740 | 2 | Door frame verticals | |
| 2040 | **550** | 2 | Gantry (sides) | was 470 |
| 2040 | 470 | **3** | Frame horizontals, front: top, bottom (new front), bottom (stays under the Backbone's front holes) | **+1** |
| 2040 | 470 | **1** | **Dock crossbar** (placeholder: height/position follow the dock design) | **new** |
| 2040 | 470 | 2 | Door frame rails (top + bottom) | |
| 2040 | **550** | 1 | Electronics cabinet | was 470 |
| 2020 | 470 | 1 | Bed frame | |
| 2020 | 380 | 1 | Rear vertical (below the gantry) | |
| 2020 | 340 | 1 | Gantry (rear) | |
| 2020 | 332 | 1 | Bed frame | |

Not extrusions, but part of the same order:
- **Y rails: 2 × MGN9, 470 mm** (were MGN12 × 400).
- **X beam: Carbonara 350, 430 mm** CF tube (replaces the 2020).

**Totals:** 4040: 2 × 740 + 4 × 550 + 2 × 470. 2040: 4 × 740 + 3 × 550 + 6 × 470 + 2 × 380. 2020: 470, 380, 340, 332.

## Before ordering (stage issue #7)

- [ ] Joint style chosen (full blind joints vs hybrid countersunk). It decides
      which ends are tapped and where access holes go.
- [ ] Machining list per bar added here.
- [ ] Z post joints and dock crossbar height decided (lite-6 placeholders).
- [ ] Re-measured from the model after any further frame change. Re-run
      `frame_plus100.py`'s cut-list section, or measure in FreeCAD.
- [ ] The electronics cabinet bar may change with the side/top pack decision (#5).
