# A4Tv2 4010 ducts with MadMax dock bosses (derived from DW-Tas's A4Tv2)

**This folder is licensed CC BY-NC-SA 4.0 (see `LICENSE` here), not GPL-3.0 like the rest of this repo.** It's a modified
version of a CC BY-NC-SA 4.0 part: attribution required, **non-commercial only**, and derivatives under the same licence.

| | |
|---|---|
| Original | `A4Tv2_4010_Ducts` (left and right 4010 part-cooling ducts) from DW-Tas's [A4Tv2](https://github.com/DW-Tas/A4Tv2) |
| Original licence | CC BY-NC-SA 4.0 (the A4Tv2 repository's `LICENSE`) |
| Original files | [`STL/ducts/A4Tv2_4010_Ducts.stl`](https://github.com/DW-Tas/A4Tv2/blob/888755a97da9e1bd3062c35c914538342ef7d6f2/STL/ducts/A4Tv2_4010_Ducts.stl) and the ducts in `A4Tv2_assembly.step`, at commit [`888755a`](https://github.com/DW-Tas/A4Tv2/commit/888755a97da9e1bd3062c35c914538342ef7d6f2) |
| Modified | 2026-11-05, by Daniel Vystrcil (with Claude Code) |
| Change | **Three cylindrical bosses (Ø8) on each duct's outer face** carry the three MadMax dock screws (rear-top, rear-bottom, front-top), replacing the separate dock brackets. Each has a pocket for a Voron M3 heat-set insert (Ø4.8 × 4.4 deep, then a Ø2.9 × 4.2 tail for the screw), copied from andrewmcgr's MadMax Dock Bracket. Each boss ends 0.2 mm inside the duct wall's solid section, so nothing enters the air channel, and keeps ≥ 0.4 mm clear of the fan screws and the duct's body-screw counterbores. Volume: left 10 242.7 → 11 568.7 mm³, right 10 270.1 → 11 589.1 mm³ |
| Why | On this printer (a Voron Trident 350 with MadMax and A4Tv2 heads), the dock brackets collided with the Crossbow lever and limited X reach. The idea of carrying the dock screws on the cowl comes from the MadMax community (an A4T v1 remix posted on Discord, no CAD published; see also zruncho3d/madmax PR #34). See `cad/README.md`, `lite23_cowl_docks.py`, and issue #53 |
| How it was made | `cad/passes/lite23_cowl_docks.py` adds the bosses to the ducts as placed in the printer model; `cad/scripts/derive_stls.py` moves each into the upstream STL's frame (registered to the original duct, max vertex error 0.0064 mm) |

**Print-oriented since lite-67 (2026-11-17, vt350#59).** lite-67 (`cad/passes/lite67_dock_spacer.py`) cut the bosses
off on the duct's print face. What stays of each boss is a stub flush with that face, filled down to the duct where its
outside angles away, so these STLs sit flat in DW-Tas's own print orientation (48.95 × 63.32 × 23.66 mm, as the
upstream duct) and print without supports. The cut-off pieces are the separate spacer in `../a4tv2-dock-spacer/`. The
two top inserts moved into the duct behind the cut (≥ 1 mm of duct beyond each pocket); the rear-bottom insert stays in
the spacer, since the duct behind that boss is only 5.2 mm deep. lite-23's version, with the bosses, is in git history.

**Hardware:** 3 × Voron M3 heat-set inserts (2 in the duct, 1 in the spacer) and 3 × M3 FHCS per duct. The screws must be **magnetic steel**, not stainless:
the dock holds the parked screw heads with magnets.

**Source:** the original STEP/STL linked above plus `lite23_cowl_docks.py` (the boss geometry is fully parametric there:
`SCREWS`, `BOSS_R`, `POCKET`, `TAIL`, `FACE_X`).
