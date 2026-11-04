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
| Model files (not in git) | `~/Documents/VT350/`. Current working copy **`vt350-lite-4.FCStd`**; untouched original `vt350-good.FCStd` |
| How the model files were made + how to redo it | `cad/README.md`, `cad/scripts/` |
| Cut list (draft) | `notes/cut-list.md` |
| Source STEP files (frame variants, toolheads, boards) | `~/Documents/VT350/` |
| FreeCAD | `~/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage`, launched from `~/Desktop/freecad-26.3rc2.desktop` (on the RTX 2070) |
| Tracking | GitHub project "3D Printer Projects"; label `build-stage` |

## Not in this repo / not done yet

- **The model files are only on the laptop.** Back up `~/Documents/VT350/`.
- `~/Documents/3D Files/ebox/ebox.FCStd` is **not** this printer's ebox (most
  likely the Neptune's portable power supply). The VT350 electronics are the
  `Electronics` group inside the model.
- Splitting the model into per-assembly files with `App::Link` (would make it
  lighter still).
- Klipper config (`config/`): starts in stage #15.
