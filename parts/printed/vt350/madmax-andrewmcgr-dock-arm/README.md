> Copy of [`cad/derived/madmax-andrewmcgr-dock-arm/README.md`](../../../../cad/derived/madmax-andrewmcgr-dock-arm/README.md). Only the **current** printable file is in this folder; see `../README.md`.

# Dock Arm, lengthened 5 mm (derived from MadMax / andrewmcgr)

**This folder is licensed GPL-3.0 (see `LICENSE` here), the licence of the part it was made from (the rest of this repo is GPL-3.0-or-later).**
It's a modified version of a GPL-3.0 part.

| | |
|---|---|
| Original | `Dock Arm` from andrewmcgr's [XOL-A4T-Cartographer](https://github.com/zruncho3d/madmax/tree/main/User%20Mods/andrewmcgr/XOL-A4T-Cartographer) mod in [zruncho3d/madmax](https://github.com/zruncho3d/madmax) |
| Original licence | GPL-3.0 (the madmax repository's `LICENSE`; the mod folder has no separate licence) |
| Original files | [`CAD/Dock Arm.step`](https://github.com/zruncho3d/madmax/blob/main/User%20Mods/andrewmcgr/XOL-A4T-Cartographer/CAD/Dock%20Arm.step), [`STL/Dock Arm.stl`](https://github.com/zruncho3d/madmax/blob/main/User%20Mods/andrewmcgr/XOL-A4T-Cartographer/STL/Dock%20Arm.stl) at commit [`6bf670d`](https://github.com/zruncho3d/madmax/commit/6bf670de9adcc5924e2fb552978161d7a9c7b1c8) |
| Modified | 2026-11-04, by Daniel Vystrcil (with Claude Code) |
| Change | **5 mm longer.** The arm's straight section (constant 193.2 mm², 8 mm long) is cut and the section extruded 5 mm. The mount end and the dock end are otherwise unchanged. Size 36.5 × 62.73 × 30 mm (original 36.5 × 57.73 × 30); volume 12 880 mm³ (original 12 397) |
| Why | On this printer (a Voron Trident 350, 80 mm deeper at the front) the carriage couldn't reach the docked heads by 2.81 mm. The longer arms move each dock 5 mm back. See `cad/README.md`, lite-14 |
| How it was made | `cad/scripts/lite14_docks.py` (function `lengthen`) on the arm as placed in the printer model. This STL is one of those arms, moved to the origin in the original STL's orientation |

**Printing:** 4 needed, a top and a bottom arm for each of the two docks. The right dock uses the same part turned around, not a mirrored one. The orientation is the same as the original STL.

**Source:** under GPL-3.0, the "source" is the preferred form for making modifications. Here that's the original STEP linked above plus the `lengthen` step in `cad/scripts/lite14_docks.py`, a 5 mm extrusion of the section at the cut. The rest of the printer model isn't distributed.

## `Dock Arm -9.06mm.stl` (lite-23, issue #53)

| | |
|---|---|
| Original | the same `Dock Arm` as above (GPL-3.0, commit `6bf670d`) |
| Modified | 2026-11-05, by Daniel Vystrcil (with Claude Code) |
| Change | **9.06 mm shorter than the original** (14.06 mm shorter than `Dock Arm +5mm.stl`). A 14.06 mm slab is removed from the arm's constant-section run (193.2 mm², sections either side of the cut identical to 0.0000 mm²) and the two ends are joined. Size 36.5 × 48.67 × 30 mm (original 36.5 × 57.73 × 30); volume 11 521.8 mm³ |
| Why | lite-23 moves the dock screws onto bosses on the head's duct (see `cad/derived/a4tv2-duct-4010-madmax-dock/`), so each dock's keyslot plate moves 14.06 mm forward and 5.78 mm down, and the parked heads sit 12.5 mm further back. Pickup at the keyslots' large opening now has +8.69 mm before the carriage's hard stop |
| How it was made | `cad/scripts/lite23_cowl_docks.py` (step "Shorten the arms") on the arm as placed in the printer model; `cad/scripts/derive_stls.py` puts it in the original STL's orientation (registered to `Dock Arm +5mm.stl`, max vertex error 0.0001 mm) |

**Printing:** this replaces `Dock Arm +5mm.stl`: **4 needed**, a top and a bottom arm for each dock (both arms of each dock were shortened by the same cut; the right dock uses the same part turned around). Same orientation as the original STL. `Dock Arm +5mm.stl` stays here for lite-14…22 builds.
