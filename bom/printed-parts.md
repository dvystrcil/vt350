# Printed parts: first pass (#8 AC2)

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
| `Gantry/X_Axis/X_Carriage/*` | replaced | MadMax shuttle on the front X rail (#19) |
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
| `Panels/Front_Doors/*` (hinges, handles, latch) | decide | The model has its own 2040 door with 3 hinges. Check whether those are these STLs. |
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
| [MadMax](https://github.com/zruncho3d/madmax) | shuttle, docks, dock mounts | shuttle ×1, dock **per tool** | print. Dock mount style waits on #19 (2WD, so not the AWD front support). |
| [A4T](https://github.com/Armchair-Heavy-Industries/A4T) | toolhead body + Orbiter 2.5 / O2S / OSS / Crossbow adapters | **per tool** | print |
| [EMU](https://github.com/DW-Tas/EMU) | separate unit; its own configurator | per lane | print, tracked separately |
| custom | Pad 7 quick-release mount, skirts and feet, Z chain anchor for the Backbone | — | custom |

## Next steps
1. Confirm what the kinematic mount kit includes (does it replace `z_bed_*`?).
2. Work out how the MadMax shuttle and the Monolith belt clamps fit together, and its endstop or sensorless homing.
3. Check whether the model's door hinges and latch are the stock STLs.
4. Get the per-tool A4T and MadMax file list for the chosen variants.
