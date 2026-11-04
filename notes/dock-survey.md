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

## Tool count

Spacing p = head width + 3 + 2. *Span* = how far apart the outermost docked heads' centres can be. It's limited by X carriage travel; it was 307 mm between the model's current docks, and must be measured with the real Monolith gantry (#19 AC1). N = floor(span / p) + 1.

| Head width | Spacing | span 307 | span 350 | span 363 (Full Travel +13) | 6 tools needs span ≥ |
|---|---|---|---|---|---|
| 80.3 (A4T + Crossbow as modeled) | 85.3 | 4 | 5 (needs ≥ 341) | 5 | 427 |
| 70.0 (Crossbow inside the A4T width) | 75.0 | **5** (needs ≥ 300) | 5 | 5 | 375 |

- **5 tools looks feasible** with a front crossbar and slim docks. That's either with the Crossbow tucked inside the A4T width (fits even at the current span), or with the X span measured at ≥ 341 mm.
- **6 tools** needs a span of 375 mm (70 mm heads) or 427 mm (80 mm heads). That's beyond a 350's X travel. The options are a wider frame, which means a new X beam (the Carbonara only comes in 250/300/350, and the 350 one is 430 mm), or narrower heads (the DragonBurner is 54 mm per the MadMax docs).

## Y: printable area lost to parked heads
Docked heads hang over the bed's front strip, and their nozzles sit at the same height as the active nozzle. Model: bed plate Y 28.0 … 388.5; docked heads Y −1.9 … 78.5. With docks across the whole front, the strip is lost for every multi-tool print, not just the corners:
- **Loss ≈ 6 mm dock slide + 4 mm screw stick-out + head depth (80 mm) ≈ 90 mm**, versus 360 mm of bed.
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
