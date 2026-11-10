> Copy of [`cad/derived/madmax-andrewmcgr-carriage-beacon/README.md`](../../../../cad/derived/madmax-andrewmcgr-carriage-beacon/README.md). Only the **current** printable file is in this folder; see `../README.md`.

# MadMax carriage with a deeper Beacon RevH pocket (derived from MadMax / andrewmcgr)

**Print `MadMaxCarriage Beacon RevH pocket 9mm belts.stl`.** This build runs 9 mm belts (#58). The older file without
"9mm belts" in its name has andrewmcgr's stock **6 mm**-belt clip pockets, and it's kept only as the lite-24 record.

| 9 mm-belt version | |
|---|---|
| Made | 2026-11-06, by Daniel Vystrcil (with Claude Code), `cad/scripts/lite25_carriage_9mm.py` |
| Change | Same as below, plus: **both belt-clip pockets replaced with upstream's 9 mm ones**, taken from [`STL/Carriage_MGN12H_9mm.stl`](https://github.com/zruncho3d/madmax/blob/6bf670de9adcc5924e2fb552978161d7a9c7b1c8/STL/Carriage_MGN12H_9mm.stl) @ `6bf670d` (GPL-3.0). The pockets are 26 mm tall instead of 20, on the same centre line, with the same depth. Swap boxes (STL frame, from the bounding-box minimum): X −1…12.5 and 41.9…55.4, height 1.5…31 from the top, full depth. They hold every 6-vs-9 mm difference and none of andrewmcgr's changes (checked by vertex sets). 18 150.9 → 16 885.0 mm³ |
| Clips | upstream `STL/SpeedClip_4mm_Gap_9mm.stl`, unmodified (not in this folder) |
| Frame | the original `MadMaxCarriage.stl`'s frame (same print orientation) |

## 6 mm-belt version (lite-24)

**This folder is licensed GPL-3.0 (see `LICENSE` here), the licence of the part it was made from (the rest of this repo is GPL-3.0-or-later).**
It's a modified version of a GPL-3.0 part.

| | |
|---|---|
| Original | `MadMaxCarriage` from andrewmcgr's [XOL-A4T-Cartographer](https://github.com/zruncho3d/madmax/tree/main/User%20Mods/andrewmcgr/XOL-A4T-Cartographer) mod in [zruncho3d/madmax](https://github.com/zruncho3d/madmax) |
| Original licence | GPL-3.0 (the madmax repository's `LICENSE`; the mod folder has no separate licence) |
| Original files | [`STL/MadMaxCarriage.stl`](https://github.com/zruncho3d/madmax/blob/6bf670de9adcc5924e2fb552978161d7a9c7b1c8/User%20Mods/andrewmcgr/XOL-A4T-Cartographer/STL/MadMaxCarriage.stl) at commit [`6bf670d`](https://github.com/zruncho3d/madmax/commit/6bf670de9adcc5924e2fb552978161d7a9c7b1c8) |
| Modified | 2026-11-06, by Daniel Vystrcil (with Claude Code) |
| Change | **Probe pocket ceiling raised 2.145 mm** over the Beacon RevH board's footprint (+0.5 mm clearance), so the board top sits 2.145 mm higher. Nothing else changes; the two M3 pilot holes at ±15.8 mm keep 5.36 mm of depth above the new ceiling. 274.8 mm³ removed (18 425.7 → 18 150.9 mm³) |
| Why | With the board against the original ceiling, Beacon's coil face would be only **0.46 mm** above the nozzle tip. Beacon's docs give "nominally 2.6mm recessed from the nozzle in Z" ([quickstart](https://docs.beacon3d.com/quickstart/)) and "only around 3mm higher than the nozzle tip" ([Contact](https://docs.beacon3d.com/contact/)). With the change it's **2.60 mm**. Based on this printer's A4Tv2 heads (nozzle tip 1.67 mm below the carriage underside when carried); a different hotend stack changes the number. See `cad/scripts/lite24_beacon.py` and issue #54 |
| How it was made | `cad/scripts/lite24_beacon.py` cuts the pocket on the carriage as placed in the printer model; `cad/scripts/derive_stls.py` puts it back in the original STL's frame (registered to the original, max vertex error 0.0155 mm) |

**Mounting:** Beacon RevH **Normal** (vertical connector), connector to the **rear** (toward the X beam, away from the bowdens), on two M3 screws through its mounting slots. In this model that gives Klipper `[beacon]` `x_offset: 0`, `y_offset: 27.4` for both heads (a check, not a calibration: measure on the printer).

**Source:** the original STL linked above plus the pocket cut in `lite24_beacon.py` (a box over the board footprint from the old ceiling up by `DZ`).
