# Build status: read this first when picking the project back up

Last updated **2026-11-04**.

## What this printer is

A Voron Trident 350 derivative on a **4040 frame**: MGN12 rails on X/Y, three
MGN9 rails on Z with integrated-leadscrew NEMA17s (T8, 8 mm), 250 mm Z travel,
**MadMax toolchanger** with two toolheads (A4T + Dragon Rapido UHF, Orbiter 2.5
+ **Orbitool O2S** + **Orbiter Smart Filament Sensor**), kinematic bed (Kobra
Plus heated bed), Octopus Pro + Pi 5, fully enclosed.

## Decisions made

| Date | Decision | Where |
|---|---|---|
| 2026-11-04 | **+100 mm between the gantry and the frame top**, for bowden/USB clearance; gantry height and Z travel unchanged | `cad/README.md` |
| 2026-11-04 | Frame bars crossing the change are **re-extruded from their end profile** (parametric), not cut-and-spliced | `cad/README.md` |
| 2026-11-04 | Door gets **3 identical hinges** | `cad/README.md` |
| 2026-11-04 | Door handle stays where it is until the pack decision | #5 |
| 2026-11-04 | **Chamber target: 60 °C sustained, 70 °C peak** (revised down from 80 °C). Good for ASA/ABS; some nylons may want more, which is an accepted limit | #4 |
| 2026-11-04 | Active chamber heater; PC/PC-CF printed parts; electronics outside the chamber; motor cooling (all decided at 80 °C: **revisit** at 60 °C) | #4 |
| 2026-11-04 | 140 mm Noctua ceiling fans to push hot air down; **separate insulated roof panel** | #5 |
| 2026-11-04 | Toolheads: **Orbitool O2S + OSS**; **Nitehawk-36 not used** | #6 |
| 2026-11-04 | **Go deep: +80 mm of Y at the front** (A4Tv2 + O2S head, deepest slice 68.6 mm). Backbone, Z, bed and rear frame stay; the old front verticals become Z posts | #19, `cad/README.md` (lite-6) |
| 2026-11-04 | Gantry: **LDO Monolith milled, 2WD, VT 9 mm, rear NP** (FT hits the rear gantry 2020); **MGN9 × 470 Y rails**; **Carbonara 430 CF X beam** | #11, #19 |
| 2026-11-04 | **Taller Z: gantry +50 mm in the same 740 mm frame; Z rails and lead screws 400** (~348 mm print height). The 400 integrated motor is in stock at West3D | `cad/README.md` (lite-10) |

## Open decisions (blocking)

| Issue | Question |
|---|---|
| #4 | Panel material (polycarbonate vs aluminium/ACM; acrylic is marginal at the 70 °C peak) |
| #5 | **Side pack vs DOOMCube-style top pack** for the electronics; fan model and how the 70 °C peak is bounded at the ceiling (stock NF-A14 is rated to exactly 70 °C) |
| #3 | Bowden + USB routing through the new headroom, and where they exit |
| #11 | 2WD vs AWD: the model mixes both |

## Build stages (in order)

#7 frame order → #8 printed parts → #9 frame assembly → #10 Z + bed →
#11 gantry → #12 toolchanger + toolheads → #13 electronics → #14 enclosure →
#15 first power-on + calibration.

Each stage issue has an **inventory** acceptance criterion. Tick it as you
confirm which parts you already own.

## Where things are

| What | Where |
|---|---|
| Model files (not in git) | `~/Documents/VT350/`. Current working copy **`vt350-lite-10.FCStd`** (gantry +50 mm, Z 400 rails + screws, ~348 mm print height); untouched original `vt350-good.FCStd` |
| **Backup of the model files** | restic to the home NAS. Run **`cad/backup-models.sh --verify`** (alias `vt350-backup`) after model changes; old snapshots are pruned automatically (last 10, daily for 30 days, monthly for a year). Target and password are local config (`~/.config/vt350/backup.env`), not in this public repo; keep the restic password in the password manager too. First backup 2026-11-04: 52 files, 4.09 GB, test restore byte-identical |
| How the model files were made + how to redo it | `cad/README.md`, `cad/scripts/` |
| Cut list (draft) | `notes/cut-list.md` |
| Parts already owned + design impact | `notes/parts-owned.md` |
| Source STEP files (frame variants, toolheads, boards) | `~/Documents/VT350/` |
| FreeCAD | `~/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage`, launched from `~/Desktop/freecad-26.3rc2.desktop` (on the RTX 2070) |
| Tracking | GitHub project "3D Printer Projects"; label `build-stage` |

## Not in this repo / not done yet

- The model backup is on the home NAS, which is not off-site.
- `~/Documents/3D Files/ebox/ebox.FCStd` is **not** this printer's ebox (most
  likely the Neptune's portable power supply). The VT350 electronics are the
  `Electronics` group inside the model.
- Splitting the model into per-assembly files with `App::Link` (would make it
  lighter still).
- Klipper config (`config/`): starts in stage #15.
