# Extrusion cut list (draft)

**Re-measured from the model on 2026-11-18** (`vt350-lite-68.FCStd`, every extrusion's box; lite-69 and lite-70 don't
touch the frame). The list measured at lite-6 was out of date: the **side pack** (#5, owner 2026-11-18: "we are going
side pack") was built into the frame in lite-46 (top and bottom bars one piece across chamber + e-box, uprights
between them), lite-47 (full-height e-box outer uprights) and lite-53 (the e-box's inner 2020 frame).
Lengths are the bar's long axis in mm; the names are the model's labels.

**Frame**

| Profile | Length | Qty | Where in the model |
|---|---|---|---|
| 4040 | 660 | 2 | Rear horizontals, top + bottom, one piece X −520..140 across chamber and e-box (lite-46/53) |
| 4040 | 660 | 2 | Rear uprights, Z −10..650, between the horizontals (lite-46) |
| 4040 | 550 | 4 | Side horizontals, top + bottom |
| 2040 | 660 | 2 | Front horizontals, top + bottom ("new front"), one piece X −520..140 (lite-53) |
| 2040 | 660 | 2 | Front uprights, Z −10..650 (lite-46) |
| 2040 | 470 | 1 | Front bottom bar under the Backbone's front holes |
| 2040 | 550 | 2 | Gantry sides |
| 2040 | 430 | 2 | Z posts (carry the front Z rails); **440 if #243 raises the gantry** |
| 2040 | 550 | 2 | E-box outer side rails, top + bottom (lite-46) |
| 2040 | 740 | 1 | E-box rear outer upright, Z −50..690 (lite-47) |
| 2020 | 740 | 1 | E-box front outer upright, Z −50..690 (lite-47) |
| 2020 | 660 | 2 | E-box inner uprights, front + rear (lite-53) |
| 2020 | 550 | 2 | E-box inner cross members, top + bottom (lite-53) |
| 2020 | 470 | 1 | Dock bar (lite-31/32, #19) |
| 2020 | 430 | 1 | Rear vertical below the gantry; **440 if #243 raises the gantry** |
| 2020 | 340 | 1 | Gantry rear |
| 2020 | 470 | 1 | Bed frame |
| 2020 | 332 | 1 | Bed frame |

**Doors**

| Profile | Length | Qty | Where in the model |
|---|---|---|---|
| 2040 | 740 | 2 | Printer door, verticals |
| 2040 | 470 | 2 | Printer door, rails |
| 2040 | 740 | 2 | E-box door, verticals (lite-56) |
| 2040 | 530 | 2 | E-box door, rails (lite-56) |

**Totals (38 bars: 30 frame, the same 30 lite-48 rebuilt, + 8 door):** 4040: 4 × 660 + 4 × 550.
2040: 5 × 740 + 4 × 660 + 4 × 550 + 3 × 470 + 2 × 530 + 2 × 430. 2020: 740 + 2 × 660 + 2 × 550 + 2 × 470 + 430 + 340 + 332.

Not extrusions, but part of the same order:
- **Y rails: the owned 2 × Berserker MGN9H 400** (rear-flush) **+ 2 × 73.9 mm front extensions** (printed or cut steel; lite-9). They were MGN12 × 400.
- **X beam: Carbonara 350, 430 mm** CF tube (replaces the 2020).
- **Z rails: 3 × MGN9 400; Z motors: 3 × 400 mm integrated lead screw** (lite-10).
- **Machining: the 4 gantry-joint holes in the uprights at the gantry's height** (Z 420–440 since lite-10; Z 430–450 if #243 raises it).

## Before ordering (stage issue #7)

- [ ] Joint style chosen (full blind joints vs hybrid countersunk). It decides
      which ends are tapped and where access holes go.
- [ ] Machining list per bar added here.
- [x] Dock bar: profile, length, height and joints decided (lite-31/32, #19 AC7; see below).
- [ ] Z post joints decided (lite-6 placeholder).
- [ ] Gantry height decided (#243): today Z 420–440, or 10.3 mm higher for ~345.6 mm of print height with 10 mm of
      Z overtravel kept. Changes the Z posts and the rear 2020 vertical (430 → 440) and the gantry-joint holes in the
      verticals (+50 → +60 mm over stock). Owner, 2026-11-18: settle it before the frame is ordered.
- [ ] Re-measured from the model after any further frame change (last: lite-68, 2026-11-18). Re-run
      `frame_plus100.py`'s cut-list section, or measure in FreeCAD.
- [x] Side pack (#5, owner 2026-11-18); its bars are in the tables above (lite-46/47/53/56).

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
