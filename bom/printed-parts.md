# Printed parts: first pass (#8 AC2)

**The files are in [`parts/printed/`](../parts/printed/)** (#63): every "print" row below, pinned to an upstream commit, with its licence and a sha256. `parts/check-printed.py` fails if a "print" row here has no part or link there.

Source for stock parts: **Voron Trident R1** STLs at tag
[`VTr1`](https://github.com/VoronDesign/Voron-Trident/tree/VTr1/STLs) (last
updated 2026-05-31). `main` in the Voron repo is now **R2** (released
2026-06-13), and the Backbone isn't compatible with R2, so don't download
from `main`. In the file names, `_xN` is the quantity and `[a]` marks an
accent-colour part.

Status key:
- **print**: needed as-is.
- **replaced**: a bought part does this job.
- **decide**: waits on an open decision.
- **custom**: no stock part fits this build, so it needs its own design.
- **skip**: not used.

## Stock Trident R1 parts

| Folder / part | Status | Why |
|---|---|---|
| `Gantry/AB_Drive_Units/*` (a/b drive frames, wire cover, Y endstop) | replaced | Monolith CNC kit (rear motor mounts) |
| `Gantry/Front_Idlers/*` | replaced | Monolith CNC kit (front motorless mounts) |
| `Gantry/X_Axis/XY_Joints/*` (MGN12 joints, cable bridges, endstop pods) | replaced | Monolith milled XY joints. **Note: they use MGN9H Y-carriages**, so the Y rails are MGN9, not the model's MGN12. The endstop approach is still open: see [Toolheads for Monolith](https://github.com/Monolith3D/Toolheads_for_Monolith). |
| `Gantry/X_Axis/X_Carriage/*` | replaced | MadMax shuttle on the front X rail (#19). **Print the 9 mm-belt versions** (#58): carriage = `parts/printed/vt350/madmax-andrewmcgr-carriage-beacon/MadMaxCarriage Beacon RevH pocket 9mm belts.stl` (copied from `cad/derived/`; andrewmcgr's Beacon/Cartographer carriage with upstream's 9 mm belt pockets); belt clips = upstream [`STL/SpeedClip_4mm_Gap_9mm.stl`](https://github.com/zruncho3d/madmax/blob/6bf670de9adcc5924e2fb552978161d7a9c7b1c8/STL/SpeedClip_4mm_Gap_9mm.stl) ×2, unmodified (`parts/printed/madmax/`). The 6 mm-belt carriage and `SpeedClip_4mm_Gap` don't fit the 9 mm belts |
| `Gantry/chain_wire_anchor_*` | decide | Toolchanger cable routing: per-tool umbilicals or chains (#19) |
| `Z_Assembly/z_stepper_left/right/rear` | replaced | Trident Backbone plate |
| `Z_Assembly/z_cable_chain_mount_2hole/3hole` | decide | Collides with the Backbone (#7 comment). Needs a Backbone-compatible anchor. |
| `Z_Assembly/z_carriage_left/right`, `[a]_z_carriage_left/right` | print | |
| `Z_Assembly/z_carriage_rear_2hole` or `_3hole` | print (pick one) | Matches the Z chain choice |
| `Z_Assembly/z_bed_left/right/rear` | decide | The aluminium kinematic mount probably replaces these. Confirm against its kit contents. |
| `Z_Assembly/[a]_z_rail_stop_x3` | print | |
| `Z_Assembly/z_rear_extrusionbracket_left/right` | print | Monolith FAQ: rotate 180° in Full Travel mode, or use plain brackets in No Protrusion mode |
| `Z_Assembly/nozzle_probe.stl` | decide | Probe not chosen yet |
| `Z_Assembly/wago_221-412_mount.stl` | decide | Wiring plan (#13) |
| `ElectronicsBay/Controller_Mounts/Octopus_bracket_set.stl` | decide | Octopus Pro is owned; mount style depends on the pack location (#5) |
| `ElectronicsBay/raspberrypi_bracket.stl` | decide | Pi 5 + NVMe HAT. Check the stack height (#5). |
| `ElectronicsBay/` DIN mounts, PSU brackets, deck supports, cable anchors, WAGO mount | decide | Pack location and PSU model (#5) |
| `Exhaust_Filter/*` | decide | Chamber thermal design (#4) |
| `Panels/Front_Doors/*` (hinges, handles, latch) | replaced | The [Clicky-Clack fridge door](https://github.com/tanaes/whopping_Voron_mods/tree/main/clickyclacky_door) is used instead (see below) |
| `Panels/*panel_clip*` 4 mm / 6 mm | decide | Panel thickness (#4). The 4040's 6 mm slot takes the stock clips. |
| `Panels/bottom_panel_*`, `wire_cover_*` | decide | Pack location (#5) |
| `Skirt/350/*`, skirt corners, fan grills, keystone, power inlet | custom | The 4040 frame is 550 mm outside (stock 350 is 510), so stock skirts don't fit. Feet and skirt need a custom design. |
| `Skirt/mini12864_*`, `[a]_btt_knob_light_shield` | skip | The screen is the Pad 7 |
| `Spool_Management/*` | skip | Replaced by the EMU |
| `Tools/10mm_extrusion_drill_guide`, `140mm_extrusion_drill_guide` | print | For fixing any holes by hand ("a few holes we got wrong") |
| `Tools/MGN9_rail_guide_x2`, `MGN12_rail_guide_x2` | print | MGN9 for the Z and Y rails, MGN12 for the X rail |
| `Tools/110mm_Y_alignment_spacer_x2`, `pulley_jig` | decide | The Monolith has its own alignment helpers |

## Kit and mod printed parts

| Source | Parts | Qty | Status |
|---|---|---|---|
| [LDO Monolith kit STLs](https://github.com/Monolith3D/LDO_Monolith_Gantry_Kits/tree/main/STLs) | `Cable_management_clip_S/M/L` | per the manual | print |
| same | `LDO_9mm_VT_NP_spacer` | — | only if using No Protrusion mode |
| [Toolheads for Monolith](https://github.com/Monolith3D/Toolheads_for_Monolith) | belt clamp / belt alignment helper | 1 | decide: how the MadMax shuttle takes the belts |
| [MadMax](https://github.com/zruncho3d/madmax) | shuttle, docks, dock mounts. This build uses andrewmcgr's XOL-A4T-Cartographer mod: `Plate Assembly` + `Plate Back` (on each head) and `Dock Asembly` (the keyslot plate, per dock); the carriage and the 4 dock arms are our remixes (`parts/printed/vt350/`). The Dock Brackets are replaced by bosses on the A4Tv2 ducts (lite-23, #53) | shuttle ×1, dock **per tool** | print. Dock mount style waits on #19 (2WD, so not the AWD front support). |
| [A4Tv2](https://github.com/DW-Tas/A4Tv2) | toolhead body + Crossbow adapter. The model's heads are A4Tv2 since lite-15 (they replaced the [A4T](https://github.com/Armchair-Heavy-Industries/A4T) v1): Dragon Rapido UHF / Orbiter (`o2`) / XOL main body, `[a]_orbiter-crossbow-adapter_o2_xol`, `Duct-HEF-Dragon-UHF`, LED carrier + diffuser. The 4010 ducts are our remix with dock bosses (`parts/printed/vt350/`). The O2S / OSS have no A4Tv2 printed part | **per tool** | print |
| [EMU](https://github.com/DW-Tas/EMU) | separate unit; its own configurator | per lane | print, tracked separately |
| [Clicky-Clack fridge door](https://github.com/tanaes/whopping_Voron_mods/tree/main/clickyclacky_door) (tanaes) | `Hinge-L-solid`, `Hinge-L-sleeve` (each **×3**, one per hinge; upstream ships ×2), `Handle`, `Handle-Hinge_Top`, `Handle-Hinge_Bottom`, `Latch`, `Panel_Clip` | 3 hinges | print. The model's door already follows this design: `Bottom Hinge`, `Latch Handle`, `Panel_Clip` and M5×50 dowel pins are all in it. Upstream hardware for 2 hinges is 6 M5×7×8 split bushings, 4 M5 dowel pins (40–50 mm), 4 M3×20 SHCS, 12 M3×8 SHCS, 12 6×3 magnets, 1 M3×8 BHCS, 1 M3 heat-set insert, 4 M5×16 BHCS, the HSCPF3H-B-2000 retainer strip and a 3 mm acrylic panel. The third hinge adds 1 dowel pin and 2 bushings. **This build differs from upstream:** the door frame is 2040 at full frame height (in the frame order, #7), not upstream's 2020 at 470 × 500 mm, so the panel size and retainer length must come from the model. |
| vt350 (this repo) | BTT TMC5160T Plus base (`btt5160-base-4-middle-screws`, the user's own design, GPL-3.0-or-later) | 1 | print |
| custom | Pad 7 quick-release mount, skirts and feet, Z chain anchor for the Backbone | — | custom |

## Next steps
1. Confirm what the kinematic mount kit includes (does it replace `z_bed_*`?).
2. Work out how the MadMax shuttle and the Monolith belt clamps fit together, and its endstop or sensorless homing.
3. Door: get the acrylic panel size and retainer strip length from the model's 2040 door frame. Check that a 3 mm acrylic panel suits the 60/70 °C chamber (#4).
4. Get the per-tool A4T and MadMax file list for the chosen variants.
