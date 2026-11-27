# Extrusion cut list (draft)

Measured from the model `vt350-lite-4.FCStd` on 2026-11-04 by
`cad/passes/frame_plus100.py` (see `cad/data/logs/frame_plus100.log`), then
updated for **lite-6** (+80 mm of Y at the front, `cad/passes/lite6.py`).
Lengths are the bar's long axis in mm.

| Profile | Length | Qty | Where in the model | lite-6 change |
|---|---|---|---|---|
| 4040 | 740 | 2 | Frame verticals (rear) | |
| 4040 | **550** | 4 | Frame horizontals, sides (top + bottom) | was 470 |
| 4040 | 470 | 2 | Frame horizontals, rear (top + bottom) | |
| 2040 | 740 | 2 | Frame verticals (front) | moved 80 mm forward |
| 2040 | **430** | 2 | **Z posts** (the old front verticals' position; carry the front Z rails) | **new**; 380 → 430 in lite-10 (gantry +50) |
| 2040 | 740 | 2 | Door frame verticals | |
| 2040 | **550** | 2 | Gantry (sides) | was 470 |
| 2040 | 470 | **3** | Frame horizontals, front: top, bottom (new front), bottom (stays under the Backbone's front holes) | **+1** |
| 2040 | 470 | 2 | Door frame rails (top + bottom) | |
| 2040 | **550** | 1 | Electronics cabinet | was 470 |
| 2020 | 470 | 1 | Bed frame | |
| 2020 | 470 | **1** | **Dock bar** (lite-31/32, #19): front, between the 2040 front verticals, holds the 5 keyslot plates | **new**: replaces lite-6's 2040 dock crossbar placeholder |
| 2020 | **430** | 1 | Rear vertical (below the gantry) | was 380 (lite-10: gantry +50) |
| 2020 | 340 | 1 | Gantry (rear) | |
| 2020 | 332 | 1 | Bed frame | |

Not extrusions, but part of the same order:
- **Y rails: 2 × Hiwin MGN9H 490, one piece** ([Motion Constrained](https://motionconstrained.com/store/hiwin-linear-guides/mgn-series/mgn-linear-guide-sets/hiwin-mgn9hz0c-long-block-linear-guides/); vt350#291, from lite-78). They replace the owned Berserker 400s + 73.9 mm front extensions (lite-9), which go to Z. The frame front moves 17 mm forward for them: the extrusion lengths here change with lite-78.
- **X beam: Carbonara 350, 430 mm** CF tube (replaces the 2020).
- **Z rails: 3 × MGN9 400** (3 owned Berserkers: the third bought 2026-11-25; owner 2026-11-22); **Z motors: 3 × 400 mm integrated lead screw** (lite-10).
- **Machining: re-drill the 4 gantry-joint holes in the verticals 50 mm higher** (lite-10 raises the gantry to Z 420–440).

**Totals:** 4040: 2 × 740 + 4 × 550 + 2 × 470. 2040: 4 × 740 + 3 × 550 + 5 × 470 + 2 × 430. 2020: 2 × 470, 430, 340, 332.

## Before ordering (stage issue #7)

- [ ] Joint style chosen (full blind joints vs hybrid countersunk). It decides
      which ends are tapped and where access holes go.
- [ ] Machining list per bar added here.
- [x] Dock bar: profile, length, height and joints decided (lite-31/32, #19 AC7; see below).
- [ ] Z post joints decided (lite-6 placeholder).
- [ ] Re-measured from the model after any further frame change. Re-run
      `frame_plus100.py`'s cut-list section, or measure in FreeCAD.
- [ ] The electronics cabinet bar may change with the side/top pack decision (#5).

## Machining per bar (#7 AC3)

Only the rows that are decided so far. The rest depends on the joint style (#7 AC1).

| Bar | Machining | Why |
|---|---|---|
| 2020 × 470 dock bar | **none**: no tapped ends, no access holes | Its ends are held by printed inside corner brackets on its top face, not blind joints (user, 2026-11-14): the bar can then be raised or lowered by sliding the brackets in the verticals' slots, if a remixed head ever needs a different dock height. lite-32 |
| 2040 × 740 front verticals | **none for the dock bar** (the lite-10 gantry-joint re-drill above still applies) | Each corner bracket takes one M5 + T-nut in the vertical's inner (20 mm) face slot. |

T-nuts the dock bar needs (lite-32 + lite-33, `cad/data/logs/lite32_dock_brackets.json`, `lite33_dock_saddles.json`):
- **5 × M5 in the bar's front slot**: one per keyslot bracket for slots 1, 2 and 5, and two for the slot 3+4 pair hanger.
- **4 × M3 in the bar's rear slot** (lite-33): one per bracket. Each bracket is a saddle clamped to both faces of the
  bar, so the magnets' rearward tug at pickup and the heads' weight can't rock it (user, 2026-11-14).
- **2 × M5 in the bar's top slot**: one per end bracket.
- **2 × M5 in the verticals' inner slots**: one per end bracket.

Once the bar is between the verticals its slot ends are covered, so use **drop-in (roll-in) T-nuts**, or slide all 11 into
the bar before fitting it. The rear M3s go in from behind with the heads off. Screws: 9 × M5 (front slot: 5, top and
verticals: 4), 4 × M3×10 SHCS (rear slot), 12 × M3 SHCS into the keyslot plates' existing heat-sets, 2 × M3 heat-sets +
SHCS for the pair hanger. Lengths other than the rear M3×10 aren't chosen yet. Still no machining of the bar.
