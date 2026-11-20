# Build status: read this first when picking the project back up

Last updated **2026-11-19**.

## What this printer is

See [What this printer will be](../README.md#what-this-printer-will-be) in the README: the goal, the main parts, scope and where it stands. The decisions behind each part are below.

## Decisions made

| Date | Decision | Where |
|---|---|---|
| 2026-11-10 | **Web front end: Fluidd** (Mainsail stays a one-line switch: `platform/klipper/frontend.py --use mainsail`). Firmware is Kalico; tool-change macros are MadMax's `r2pdx_config-v2-Kalico-Beacon` on klipper-toolchanger | `cad/klipper/README.md`, #116 |
| 2026-11-04 | **+100 mm between the gantry and the frame top**, for bowden/USB clearance; gantry height and Z travel unchanged | `cad/README.md` |
| 2026-11-04 | Frame bars crossing the change are **re-extruded from their end profile** (parametric), not cut-and-spliced | `cad/README.md` |
| 2026-11-04 | Door gets **3 identical hinges** | `cad/README.md` |
| 2026-11-04 | Door handle stays where it is until the pack decision | #5 |
| 2026-11-04 | **Chamber target: 60 °C sustained, 70 °C peak** (revised down from 80 °C). Good for ASA/ABS; some nylons may want more, which is an accepted limit | #4 |
| 2026-11-04 | Active chamber heater; PC/PC-CF printed parts; electronics outside the chamber; motor cooling (all decided at 80 °C: **revisit** at 60 °C) | #4 |
| 2026-11-04 | 140 mm Noctua ceiling fans to push hot air down; **separate insulated roof panel** | #5 |
| 2026-11-04 | Toolheads: **Orbitool O2S + OSS**; **Nitehawk-36 not used** | #6 |
| 2026-11-09 | **lite-30**: O2S + Smart Sensor on both heads (Orbiter designer's STEP, CC0); Nitehawk-36 boxes removed; each Orbiter's motor/gear stack corrected −2.0 mm onto its hub | #6, `cad/README.md` |
| 2026-11-04 | **Go deep: +80 mm of Y at the front** (A4Tv2 + O2S head, deepest slice 68.6 mm). Backbone, Z, bed and rear frame stay; the old front verticals become Z posts | #19, `cad/README.md` (lite-6) |
| 2026-11-04 | Gantry: **LDO Monolith milled, 2WD, VT 9 mm, rear NP** (FT hits the rear gantry 2020); **MGN9 × 470 Y rails**; **Carbonara 430 CF X beam** | #11, #19 |
| 2026-11-04 | **Taller Z: gantry +50 mm in the same 740 mm frame; Z rails and lead screws 400** (~348 mm print height). The 400 integrated motor is in stock at West3D | `cad/README.md` (lite-10) |
| 2026-11-04 | **A4Tv2 needs the 3 mm spacer** between the hotend top and the shroud ceiling (confirmed by the A4Tv2's creator). The nozzle sits 3 mm lower; model it when the A4Tv2 replaces the A4T v1 | #19 |
| 2026-11-05 | **Insulation:** the 3 owned carbon-felt pads (10 mm), sealed in aluminium; roof and back outside their panels, right wall between the panel and the electronics. **Test a pad for conductivity first.** | #14 |
| 2026-11-05 | **Camera: Nocturne USB** (Luke's Lab / West3D, 96°, rated to 70 °C, which is the chamber peak with no margin) inside, top front centre; stream MJPEG (ustreamer): a Pi 5 has no H.264 encoder, and current C920s have none either | #14 |
| 2026-11-14 | **Camera moves to the rear-right corner** (lite-39): the parked heads blocked the top-front view (21 of 49 plate points seen at the worst bed height); at X −50, Y 440, Z 620, by the rear-right 4040 upright, it sees 41. Bracket to the upright not modelled yet (26 mm gap) | #19 |
| 2026-11-05 | **Lights: 24 V warm white, 3500–4000 K, CRI ≥ 90**, COB in aluminium channel, switched from an Octopus output; no 5 V lighting | #14 |
| 2026-11-05 | **Kinematic bed: tanaes's Trident set** (owned, West3D). The model still has his V2.4 parts, with the front pair floating; see `notes/kinematic-bed.md` | #10 |
| 2026-11-04 | **Crossbow: the all-metal (aluminium CNC) version from West3D**, DW-Tas's current design. The A4Tv2 assembly already models it. The older Crossbow in lite-14 and earlier is gone from lite-15 | #12 |
| 2026-11-04 | **A4Tv2: its creator says to modify it as needed.** Licences decide where changes go. The A4Tv2 is [CC BY-NC-SA 4.0](https://github.com/DW-Tas/A4Tv2): remixes are allowed with attribution, non-commercially, under the same licence. The MadMax plate and dock parts are GPL-3.0. The two licences don't mix, so keep any fit changes **on the MadMax plate side (GPL-3.0, like `cad/derived/`)**, and keep any A4Tv2 changes in their own CC BY-NC-SA 4.0 folder. **Correction (lite-15):** the first hole check compared the wrong holes (the extruder mounting pattern). The proper check, in lite-15, finds all three XOL carriage-screw pairs of the A4Tv2 on andrewmcgr's plate, so **the plate fits unmodified**. Open: the left head's Crossbow lever hits the left dock brackets, and the length of the upper carriage screws | #19 |

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

## Baseline and the pass in flight

**Baseline: `baseline-lite-72`** (tag on main, 2026-11-19; `baseline-lite-71` before it). The tag's message lists the sha256 of
`vt350-lite-72.FCStd`, `vt350-emu-4.FCStd` and `vt350-ebox-3.FCStd`; check the files in `~/Documents/VT350` with
`sha256sum` before starting a pass.

**One model pass in flight at a time.** Before starting a pass, claim its number here, in the same PR as the pass.
Clear it when that PR merges. Two passes built at the same time each start from the same lite-N and end up as
partial versions that have to be rebuilt in order (lite-67 to lite-71 did this).

| Pass in flight | Branch | Builds on |
|---|---|---|
| **lite-73** (#263): hex DAV main body + Dragon ACE Volcano stand-in, no spacer | `feat/263-lite73-dav` | lite-72 |

## Where things are

| What | Where |
|---|---|
| Model files (not in git) | `~/Documents/VT350/`. Current working copy **`vt350-lite-72.FCStd`**: lite-22 (the heater pad measured with calipers) + the dock screws on bosses on each head's duct (lite-23), Beacon RevH (lite-24), the 9 mm-belt carriage (lite-25) sitting on the MGN12H block (lite-26), levelling feet (lite-27), the filter holder (lite-28, lite-29; the filter itself in `vt350-filter-3.FCStd`, off the printer since lite-31, #115), O2S + Smart Sensor on the heads (lite-30), **five docks in a front `LLRLR` row on a 2020 bar** (lite-31) (the model keeps all 5; the build starts with 2 tools, T0 in slot 1 and T1 in slot 5: owner decision 2026-11-14, `notes/dock-survey.md`) and **the brackets that hold them** (lite-32, #19 AC7), made **saddles clamped to both bar faces** (lite-33); the O2S heat sink as its own part, for its colour (lite-34); the O2S cable's wire restraint (strain relief) on each head (lite-35); the roof exit, a printed clamp per head that holds its bowden tube and O2S cable where they leave through the roof (lite-36, #3 AC4); the part-cooling blowers, a Vindr Berserker 4010B in each 4010 duct, 2 per head, modelled from the user's measurements (lite-37); the R heads' bowden tubes onto their sensors, the left side panel, the panels' spray-painted outsides and the door window on its gasket (lite-38); the camera in the rear-right corner (lite-39); the O2S cables zip-tied to the bowdens and carried in a printed covered channel to the side pack (lite-40); Voron-style bottom skirts, white with orange grilles and corners (lite-41). **lite-42 is two variants of new skirts for the user to choose from** (`vt350-lite-42-band.FCStd`: the 50 mm band as it is; `vt350-lite-42-tall.FCStd`: Voron's 67 mm height with the stand 30 mm lower; `vt350-lite-42-none.FCStd`: no skirt, taller foot bodies with 5 mm of thread showing). **lite-43** (`vt350-lite-43.FCStd`) is lite-42-none with the stale filter envelope removed, the foot pads back to 18 mm and the base board raised 19 mm (5 mm of thread still showing). **lite-44** (`vt350-lite-44.FCStd`) puts real Asmith DK-0808035A levelling feet under the brackets, studs cut to 19.5 mm, 5 mm of thread showing, the board 8.5 mm lower. **lite-45** (`vt350-lite-45.FCStd`) holds each foot bracket to its 4040 with 4 × M5×14 DIN 912 + DIN 127 lock washers into drop-in T-nuts (the 4040's slot is a 20-series slot 6, cavity only 4 mm tall). **lite-46** (`vt350-lite-46.FCStd`) builds the e-box into the printer's frame: one-piece front and rear rails top and bottom, X −520…145, printer uprights cut to Z −10…650, 2020 outer uprights and 2040 outer side rails at X 125–145 (#5; corner joints, e-box feet and door still to come). **lite-47** (`vt350-lite-47.FCStd`) runs the e-box's outer uprights full height (Z −50…690; the rear one a 2040 flush with the 4040 rear rail), the long rails stopping against them at X 125, each rail end held by 2 × M5×30 in counterbores. **lite-48** (`vt350-lite-48.FCStd`, 110 MB, was 214) rebuilds all 30 frame extrusions from clean profiles (#195: frame BRep 238.7 → 6.4 MB, booleans work) and moves the gantry joints' orphaned holes from Z 380 to Z 430, where their screws are. **lite-49** (`vt350-lite-49.FCStd`) gives the 5 extruder springs plain-tube stand-ins and hides the real ones (#195 AC3): a hidden part isn't tessellated when the GUI opens, so the GUI open drops ~14 s (median 125.6 → 111.5 s); renders still draw the real springs. **lite-50** (`vt350-lite-50.FCStd`, 125 MB) adds coarse-mesh stand-ins for the O2S boards, Smart Sensors, bowdens, heat blocks and bearings: GUI open median 120.7 → 83.6 s. **lite-51** (`vt350-lite-51.FCStd`, **68.7 MB**) turns 22 copies (SpeedClips, O2S boards, Smart Sensors, their stand-ins, a carriage compound) into App::Links to one of each, so the file stores each shape once (#195 AC1/AC3; `platform/freecad/dupes.py`). **lite-52** (`vt350-lite-52.FCStd`, **33.8 MB**) links every copy `dupes.py` can fit (1,001 links: screws, bearings, the ×5 toolhead parts): GUI open median 70.4 → 46.9 s. **lite-53** (`vt350-lite-53.FCStd`, 34.0 MB) gives the e-box an inner 2020 frame for the DIN rails, so the side panel isn't drilled (#5), and makes the e-box 15 mm deeper (outer members X 125 → 140). lite-54…58 (#5, #187, #4): the e-box layout on that frame (`vt350-ebox-3.FCStd`: two BOSYTROs flat, real TS35 rails on the owner's Neptune holders), the 5-lane EMU on the roof (`vt350-emu-2.FCStd`, linked, 22 MB), a rear-hinged clear e-box door, and both doors' sheets in the frame slot on a rubber glazing strip; the owner approved the layout (2026-11-16). lite-59 (#5) closes the e-box: painted top and rear panels like the roof's, the bottom left open for air, and a three-piece printed grille on the front in the large skirt's style, notched round both doors' latches. lite-60 fixes the grille to the frame: 18 M3 screws into T-nuts, about every 10 cm, with L-ears on its left edge. lite-61 (#186) puts the nozzle offset probe (Mellow MultiHead Zero) on a printed bracket at the bed's front edge. lite-62 (#114) trims the two pads under the carriage's Beacon pocket walls, so the Beacon face (+2.6) is the lowest part of the carriage; the carriage now sits 3.0 mm above the nozzle tip. lite-63 (#60) gives the parts real materials: PET-GF on the toolheads, plates and carriage, ASA for the other printed parts (no ABS), PETG for clear parts, the bought Orbiter and Beacon at their published masses, NdFeB for magnets; the Beacon is white. lite-64 (#60) adds MadMax's 6×3 N52 magnets in every carriage and tool-plate pocket (48; 7.7 g per carried tool). lite-65 (#174) fixes the bowden tubes' stored route, 10.7 mm off in X. lite-66 (#60) weighs the fans: 15 g per 4010 blower, 6.8 g per 2510 (another maker's figures until weighed). lite-67 and lite-68 fit the docks to the cowl (#59, #233, #240). lite-69 (#4) moves the roof and back insulation inside the panels (the back felt thinner, 3.9 mm, until the compression test) and puts the EMU on the roof. lite-70 (#3) sets the roof-exit clamps flat on the roof, lowers the cable channel (USB cables 83–98 mm shorter) and chamfers the new printed parts; emu-4 lowers the EMU onto the roof with its bowdens re-routed. lite-71 (#3) fixes the cable channel down (posts with a lip on the rear 4040, arms on the rear-right upright, M3s into inserts), cuts it into 5 bed-sized pieces with a snap-on cover, and chamfers the older parts we designed; the probe bracket gets a flat side to print on. lite-72 (#59) fixes the dock parts for printing: the cowls lose lite-23's old rear-bottom stub, the keyslot plates' old keyslot is filled and the pad overhang past the edge goes down to the bed, and the left plate's 0.16 mm rear-top pad (one stray layer) is gone, its keyslot lowered flush. What we learned on the way: `platform/freecad/LESSONS.md`. Each pass is a row in `cad/README.md`; electronics in `vt350-ebox-3.FCStd`, the EMU in `vt350-emu-4.FCStd` (emu-3 added the five bowdens from the roof exits to the EMU lanes, #187; emu-4 sets the EMU on the roof), same global frame; untouched original `vt350-good.FCStd` |
| **Backup of the model files** | restic to the home NAS. Run **`cad/backup-models.sh --verify`** (alias `vt350-backup`) after model changes; old snapshots are pruned automatically (last 10, daily for 30 days, monthly for a year). Target and password are local config (`~/.config/vt350/backup.env`), not in this public repo; keep the restic password in the password manager too. First backup 2026-11-04: 52 files, 4.09 GB, test restore byte-identical |
| How the model files were made + how to redo it | `cad/README.md`, `cad/passes/` |
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
- Wiring documentation for the electronics (stage #13): candidate tool [WireViz](https://github.com/wireviz/WireViz). It turns wiring described in YAML into diagrams and a bill of materials, so the docs can be versioned like the rest of the repo.
