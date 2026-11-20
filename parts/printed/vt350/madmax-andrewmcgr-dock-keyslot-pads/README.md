# Dock keyslot plate with standoff pads (derived from MadMax / andrewmcgr)

**This folder is licensed GPL-3.0 (see `LICENSE` here), the licence of the part it was made from (the rest of this repo is GPL-3.0-or-later).**
It's a modified version of a GPL-3.0 part.

| | |
|---|---|
| Original | `Dock Asembly` (the dock's keyslot plate; upstream spelling) from andrewmcgr's [XOL-A4T-Cartographer](https://github.com/zruncho3d/madmax/tree/main/User%20Mods/andrewmcgr/XOL-A4T-Cartographer) mod in [zruncho3d/madmax](https://github.com/zruncho3d/madmax), commit `6bf670d`; the unmodified copy is `parts/printed/madmax/andrewmcgr/Dock Asembly.stl` |
| Original licence | GPL-3.0 (the madmax repository's `LICENSE`) |
| Modified | 2026-11-18, by Daniel Vystrcil (with Claude Code) |
| Change | **The dock reaches to the cowl** (vt350#59, owner's idea): a **pad** on the plate's inner face at each keyslot, carrying the keyslot's 2 mm head channel at its face, so the screw head meets the same keyslot nearer the toolhead. The plate's through-hole at each parked screw runs on through the pad. The **rear-bottom keyslot moves 18.5 mm forward and 6.25 mm up** (the cowl is only 2 mm deep where it was) and the plate grows a wing to carry it; the old keyslot is filled. Each pad face is square to the screw and stops ≥ 1 mm from the toolhead over the whole 6 mm pickup slide (the play the dock needs). |
| Pads (mm) | front-top 7.69, rear-bottom 7.42, rear-top 4.16 (right) / **none (left)**: the left head's Crossbow lever stands 1.75 mm off the plate there, so that keyslot sits flush in the plate face (lite-72 lowered it 0.16 mm: lite-68's 0.16 mm pad sliced as one stray layer) |
| Why | lite-23 put the dock screws on bosses on the 4010 duct, which couldn't print flat. lite-67 cut them off into a separate spacer, which nothing could hold on (the screw heads stand proud as docking hooks, so they clamp nothing). On the dock the extension is free: it doesn't ride on the toolhead |
| How it was made | `cad/passes/lite68_dock_pads.py` (lite-67 → lite-68); `cad/scripts/derive_stls.py` lays each plate on its outer face (pads up) |

**Hardware per head** (the cowl side, `../a4tv2-duct-4010-madmax-dock/`): 3 short M3 heat-set inserts (3 mm long,
5 mm OD) in the cowl; 3 M3 male-female round standoffs (4 mm body, Ø5, **stud ground to 3 mm**) screwed into them;
3 M3×6 flat-head screws (FHCS; ground to 5 mm on the 4 mm standoffs), **alloy steel**, strongly magnetic, not stainless,
in the standoffs' tops (the heads are the hooks).
Every standoff is 4 mm, except the left head's rear-top: **8 mm** (an M3×8+6 standoff, its stud also ground to 3 mm; or two 4 mm stacked).
The screw clamps on the standoff, so the hook height is the standoff's body, not how far a screw is turned.
**Magnets:** the plate's hex hole at each parked screw takes a 6×3 N52. With the pads it's ~11.5 mm long: press the magnet
in **from the pad side**, flush with the channel floor, so it sits right behind the screw head as on the upstream plate.
Step by step: `docs/assembly/stage-12-toolheads.md`.

**Print:** outer face down, pads up, no supports. Left: 3 (Left Dock, slots 2 and 4); right: 2 (Right Dock, slot 3).
The mounting holes and their heat-sets are unchanged.
