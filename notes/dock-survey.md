# MadMax dock survey (#19 AC8), 2026-11-04

Goal: 5–6 tools. Head: A4T + Orbiter 2.5 + Crossbow (+ O2S/OSS later, #6).

## How MadMax docks work (from the MadMax docs)
- **Gantry-attached docks** need only XY motion, so they suit a static-gantry Trident. Docks are keyslot plates with magnets. The head carries flat-head screws at a common spacing (**20 mm in Y × 54 mm in Z**) that drop into the keyslots ([GETTING_STARTED](https://github.com/zruncho3d/madmax/blob/main/GETTING_STARTED.md)).
- For the A4T, andrewmcgr's plate carries the dock screws on an L-bracket, so **the A4T itself isn't modified** ([GETTING_STARTED](https://github.com/zruncho3d/madmax/blob/main/GETTING_STARTED.md), A4T/XOL section).
- **X space per docked head = head width + 3 mm screw stick-out + 1–2 mm clearance** ([FAQ](https://github.com/zruncho3d/madmax/blob/main/FAQ.md)).
- The usual 2-head layout is one dock on each front corner post. **More than 2 heads uses a front crossbar.** Builds that do this: Yell's E3dent ("Crossbar for >= 2 heads!"), noobydp's horizontal-rail dock, and the user's 4-head Trident reference photo (3 docked + 1 active, slim docks on a front crossbar).
- MadMax README: "No builds seen beyond two heads, yet." The user's photo shows 4 exist.

## Candidate docks

Sizes are the bounding boxes of the published files. Plate width is the X footprint.

| Dock | Mounts to | Size (mm) | Tested on | Notes |
|---|---|---|---|---|
| [Ambrosia (rbricheno) Stalagmite](https://github.com/rbricheno/stalagmite_dock) | corner verticals (M5) | plate 51.5 × 103.8 × 14.2, spacer 18 × 52 × 28 | Trident 300, DragonBrick | Parametric (Fusion). The 2-part version lets the spacer be reprinted for a different offset. One per side, so 2 heads. |
| [noobydp horizontal-rail dock](https://github.com/zruncho3d/madmax/tree/main/User%20Mods/noobydp) | **a horizontal extrusion** on a Trident | 51.5 × 108.7 × 34 | Trident, DragonBurner + Cartographer | **Crossbar-ready.** Based on the Stalagmite. STEP and F3D available. |
| [andrewmcgr XOL-A4T-Cartographer](https://github.com/zruncho3d/madmax/tree/main/User%20Mods/andrewmcgr/XOL-A4T-Cartographer) | dock arm + bracket | arm 36.5 × 57.7 × 30, bracket 30 × 64 × 16.4, assembly 37 × 98 × 6 | "**extensively tested on a Voron Trident 350**" with A4Ts | **Matches our head and printer size.** Also includes the A4T plate and a Cartographer/Beacon carriage for a front MGN12 rail. [wulfsta](https://github.com/zruncho3d/madmax/tree/main/User%20Mods/wulfsta/XOL-A4T-MGN9) has an MGN9 version of the plate. |
| Vlad's 300 Trident (MadMax build MM.012) | "extended Ambrosia's docks" | — | A4T, Sherpa Mini | No files in the repo |
| The model's current docks | corner verticals | 111.5 wide incl. arm | — | The wide arm reaches the vertical. A crossbar dock doesn't need it. |

**Dock plates are about 52 mm wide, narrower than the head**, so head width sets the spacing, not the dock.

## What sets head width (from the model, `Left Toolhead`)

| Sub-assembly | X width | X range |
|---|---|---|
| A4T assembly (cowling) | **70.0** | −434.0 … −364.0 |
| Crossbow integration | 70.7 | −444.3 … −373.7: **sticks out 10.3 mm** past the A4T on one side |
| Orbiter 2.5 | 59.0 | inside the A4T width |
| **Whole head** | **80.3** | |

So **the Crossbow mount adds ~10 mm** of head width. Not yet modeled: O2S/OSS (#6, AC9).

## A4Tv2 (decided 2026-11-04): head size, with the Orbiter, OSS and O2S (#19 AC9)
The user switched to [A4Tv2](https://github.com/DW-Tas/A4Tv2) (a prerelease) and is keeping the Crossbow.

Head = upstream `CAD/A4Tv2_assembly.step`, taking only our parts by exact name:
- `main-body_dragon-rapido-UHF_o2_xol`, `[a]_orbiter-crossbow-adapter_o2_xol`;
- 4010 part-cooling ducts, UHF hotend fan and duct, part fans, LEDs, Crossbow;
- carriage, Orbiter, duct and Xol hardware.

Then the official Orbiter 2.5 + Smart Sensor + O2S assembly (`Orbiter v2.5_SmartSensor and O2S Toolboard.step`, RobertLorincz/Orbiter-Toolboards) is seated on the adapter. Script: `cad/studies/ac9_head_envelope.py`.

- **Seating:** the Orbiter's two M3 holes land on the adapter's (−19.5 / +17.5 mm) within 0.01 mm, with the filament axes coincident. The hole pattern is asymmetric, so the motor and O2S can only face the rear. The housing touches the adapter after a 1.6 mm drop. No O2S part overlaps any A4Tv2 part.
- **Correction:** the first version of this section measured 73.4 × 67.1 × 112.8 for "our variant". It filtered out `wwbmg`, but the STEP labels that extruder `WW-BMG`, so the WW-BMG extruder and its NEMA14 stood in for the Orbiter. The assembly STEP has no Orbiter at all.
- **Hotend:** the assembly has no Dragon Rapido UHF (or Ace Volcano). Its Dragon Ace stands in, which only affects how far the nozzle hangs below the body (Z), not the depth.
- `Support_Main-body-UHF` is left out: it is a print support (no separate STL; it sits on top of the body).

| | X width | Y depth: overall box | Y depth: worst single height | Z height |
|---|---|---|---|---|
| **A4Tv2 + Orbiter + OSS + O2S** | **73.4** (Crossbow −38.1, ducts +35.4) | 88.1 (Y −34.2 … 53.8) | **68.0** (at Z +23…+37, the O2S band) | 169.6 (nozzle tip to O2S wire restraint) |
| A4T v1 as modeled (with Crossbow) | 80.3 | 80.4 | — | 131.1 |

- **Width is unchanged by the O2S** (it stays within ±30.3 mm), so the spacing is still **78.4 mm** (73.4 + 3 + 2).
- **Depth:** the O2S board sits 32 mm behind the body's rear face, but only above Z +11.7, where the head's front is set back to Y −14 (the body's front is at −34 lower down). Docked heads and the active head are at the same height, so what matters is the deepest single 1 mm slice, not the overall box. That slice is 68.0 mm. A bounding-box version of the same profile read 86 mm at Z 9–11; that was a box artefact, and real slices show 47.8 there.
- **The MadMax plate** (from the model's docked v1 plate) sticks out 3.5 mm behind the body over its height and 13 mm over its top 9 mm. That raises the worst slice to **68.6 mm** at Z 0…1.
- **"Go deep" amount = 6 + 4 + 68.6 ≈ 79 mm → 80 mm** of Y at the front (lite-6).

## Tool count

Spacing p = head width + 3 + 2. *Span* = how far apart the outermost docked heads' centres can be. It's limited by X carriage travel; it was 307 mm between the model's current docks, and must be measured with the real Monolith gantry (#19 AC1). N = floor(span / p) + 1.

| Head width | Spacing | span 307 | span 350 | span 363 (Full Travel +13) | 6 tools needs span ≥ |
|---|---|---|---|---|---|
| 80.3 (A4T + Crossbow as modeled) | 85.3 | 4 | 5 (needs ≥ 341) | 5 | 427 |
| 70.0 (Crossbow inside the A4T width) | 75.0 | **5** (needs ≥ 300) | 5 | 5 | 375 |
| **73.4 (A4Tv2 + Crossbow + O2S, chosen)** | **78.4** | 4 (5 needs ≥ 314) | **5** | **5** | 392 |

- **5 tools looks feasible** with a front crossbar and slim docks. That's either with the Crossbow tucked inside the A4T width (fits even at the current span), or with the X span measured at ≥ 341 mm.
- **6 tools** needs a span of 375 mm (70 mm heads) or 427 mm (80 mm heads). That's beyond a 350's X travel. The options are a wider frame, which means a new X beam (the Carbonara only comes in 250/300/350, and the 350 one is 430 mm), or narrower heads (the DragonBurner is 54 mm per the MadMax docs).

## Measured on lite-30: a row of docks (#19 AC2, `cad/studies/dock_layout.py`, 2026-11-13)
The arithmetic above takes head width + 5. The model says more: it moves the real lite-30 parts (A4Tv2 + Orbiter 2.5 + Smart Sensor + O2S, the MadMax plate, the dock's keyslot plate, the carriage and Beacon) through MadMax's dock moves (`cad/klipper/toolchanger.cfg`: 6 mm keyslot slide; detach 5 mm in X, **away from the keyslot plate**). Read-only; accurate to about ±0.5 mm. Log: `cad/data/logs/dock_layout.log`.

**What sets the spacing is the neighbour's keyslot plate, not the head.** The keyslot plate sits beside its head, so in a row of identical docks it sits between two heads, and the carried head's 5 mm detach moves toward it. Two slot styles exist in the model:
- **L** (the left dock): keyslot plate on −X, detach +X;
- **R** (the right dock, mirrored plate and keyslot plate): keyslot plate on +X, detach −X.

Nozzle distance between neighbours (2 mm clearance; 0 mm is 2 less):

| Left slot \| right slot | Gap | Set by |
|---|---|---|
| L\|L | 85.16 | carried head at detach, at attach_y: its right 4010 duct meets the neighbour's keyslot plate |
| **L\|R** | **76.12** | both heads detach into this gap and no keyslot plate is in it; only one head moves at a time |
| R\|L | 92.00 | the two keyslot plates back to back, parked |
| R\|R | 90.06 | carried head at detach: its Crossbow lever meets the neighbour's keyslot plate |

**Tool count**, in the carriage's nozzle-X reach −416 … −74 (342 mm, `sweep_toolhead.log`), counting the outer slots' outward detach:

| Tools | Best row | Needs | Slack |
|---|---|---|---|
| 4 | LRLR | 244.24 | 97.76 |
| **5** | **LLRLR** | **329.40** | **12.60** |
| 6 | none | | |

All-L docks fit only 4 at 2 mm (5 at 1 mm with 0.4 mm to spare). L and R tools aren't interchangeable: the dock screws sit on bosses on one duct (lite-23), left duct for an L slot, right duct for an R slot.

**Behind the row:**
- The **carried head** clears a row of parked heads at **parked + 67.96 mm** (the parked O2S board vs the carried head's Orbiter hub); `toolchanger.cfg`'s safe_toolhead_y is parked + 111, so it is safe with 41 mm to spare.
- The **empty carriage** clears it at parked − 0.50 (its SpeedClips vs the parked plate); safe_shuttle_y parked + 36 is safe.
- **Printing near docks:** with docks along the whole front, the carried nozzle stays at **Y ≥ 37.50**, 7.0 mm behind the print square's front edge (30.50). This is #121's front-corner clash spread across a full row. The O2S's 18 mm standoffs (#121) would move the board back and make this worse.

**Not checked here:** bowden tubes (rigid routes, #3), USB cables past the stub, the dock arms (corner-post mounts: a row needs a crossbar or hangers, AC7), the gantry and belts (checked by the toolhead sweep at the pickup, which is the same for every slot).

## Y: printable area lost to parked heads
Docked heads hang over the bed's front strip, and their nozzles sit at the same height as the active nozzle. Model: bed plate Y 28.0 … 388.5; docked heads Y −1.9 … 78.5. With docks across the whole front, the strip is lost for every multi-tool print, not just the corners:
- **Loss ≈ 6 mm dock slide + 4 mm screw stick-out + head depth (80 mm) ≈ 90 mm**, versus 360 mm of bed (A4T v1 as modeled; for the A4Tv2 + O2S head it is ≈ 79 mm, see above).
- The MadMax answer is **"going deep"**: lengthen Y by that amount.
- This only touches Y parts: the side extrusions (not ordered yet, #7), the Y rails (MGN9, being bought anyway), belts and side panels. **The X beam and Monolith kit are unaffected.**

## Frame-order impact (#7)
1. **A front dock crossbar** along X at gantry height. That's a new bar, plus holes or joints in the front verticals.
2. **Optionally, going deep**: longer side bars in Y.

Both have to be decided before the shop order.

## Next steps
1. Measure the real X span after the gantry swap (lite-6, #19 AC1).
2. Model the noobydp/Ambrosia crossbar dock and andrew's A4T dock arm at 75 and 85 mm spacing, and check clearance with the O2S on the head (#6).
3. Decide: Crossbow placement, crossbar height and position, and deep (+~90 mm Y) or not.
