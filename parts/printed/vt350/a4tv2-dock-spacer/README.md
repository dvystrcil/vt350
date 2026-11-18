# A4Tv2 dock spacers (derived from DW-Tas's A4Tv2)

**This folder is licensed CC BY-NC-SA 4.0 (see `LICENSE` here), not GPL-3.0 like the rest of this repo.** The spacers
are cut from our remix of a CC BY-NC-SA 4.0 part (the A4Tv2 4010 ducts, `../a4tv2-duct-4010-madmax-dock/`):
attribution required, **non-commercial only**, and derivatives under the same licence.

| | |
|---|---|
| Original | `A4Tv2_4010_Ducts` from DW-Tas's [A4Tv2](https://github.com/DW-Tas/A4Tv2) at commit [`888755a`](https://github.com/DW-Tas/A4Tv2/tree/888755a97da9e1bd3062c35c914538342ef7d6f2), CC BY-NC-SA 4.0 |
| Modified | 2026-11-17, by Daniel Vystrcil (with Claude Code) |
| What | The three MadMax dock-screw bosses that lite-23 added to each duct, **cut off on the duct's print face** (owner's design, vt350#59), joined into one piece by a 2 mm flange on that face. The flange rings the 4010 blower's intake (Ø30.2) with 1 mm clearance, so the intake stays open. Each boss becomes a wedge: square to its screw at the dock end, 10° at the duct end. Top two wedges: M3 clearance holes. Rear-bottom wedge: the Voron M3 insert pocket (Ø4.8 × 4.4) at the dock face, as lite-23 had it |
| Why | The ducts with bosses couldn't print in DW-Tas's orientation (the bosses went 9.36 mm below the bed). Cut on the print face, the duct prints exactly as DW-Tas intends, and so does this spacer, flat on its flange face |
| How it was made | `cad/passes/lite67_dock_spacer.py` (lite-66 → lite-67); `cad/scripts/derive_stls.py` lays each spacer flat on its largest planar face (the flange face, which sits on the duct) |

**Fitting:** each top dock screw passes through its wedge into a Voron M3 insert in the duct behind the cut (the duct
has ≥ 1 mm of material beyond each pocket), so the two top screws clamp the spacer to the duct. The rear-bottom screw
goes into the insert in the spacer. Longer screws than lite-23's: the wedges are 11.0 mm (front-top) and 7.5 mm
(rear-top, rear-bottom) long along the screw. Screw lengths and the BOM rows are vt350#59 AC6. The screws must be
**magnetic steel**, not stainless: the dock holds the parked screw heads with magnets.

**Print:** flange face down, no supports. One left and one right per pair of heads (the right is the left's mirror image).
