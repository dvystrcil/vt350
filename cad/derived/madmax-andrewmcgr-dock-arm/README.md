# Dock Arm, lengthened 5 mm (derived from MadMax / andrewmcgr)

**This folder is licensed GPL-3.0 (see `LICENSE` here), not MIT like the rest of this repo.**
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
