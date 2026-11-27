# Parts already owned

What's already bought for the VT350, and what each part means for the design.
Links are the West3D listings the parts came from. Facts quoted here come from
those listings or the project READMEs linked from them.

## Motion

| Part | Qty | Design impact |
|---|---|---|
| [Monolith CNC Gantry by LDO](https://west3d.com/products/monolith-cnc-gantry-by-ldo-systems-v2-4-and-trident-compatible-with-2wd-and-awd) | 1 | The kit does both 2WD and AWD and supports 9/10 mm belts. Its X rail faces the front (needed for MadMax). It includes "AWD front extrusion support for toolchangers", but this build runs **2WD**, so the MadMax docks need another mount (#19 AC7). The model still has the **printed** Monolith joints (#19). |
| [Carbonara carbon-fibre X beam](https://west3d.com/products/carbonara-carbon-fiber-x-beam-for-voron-3d-printers?variant=46478960656596) | 1 | The 350 size is 430 mm and 84.3 g. Rated 110 °C short-term. CAD: [Monolith MISC/CF_tube_mounting](https://github.com/Monolith3D/MISC/tree/main/CF_tube_mounting). |
| [Gates GT2 closed-loop belt 2.4 m, 9 mm RF](https://west3d.com/products/gates-gt2-closed-loop-belt-2-4m-ll-2gt-6-6mm-wide-rf-reinforced?variant=47586401616084) | 2 | 9 mm belts for the Monolith. Cut open to length. |
| [Berserker MGN9H-1R 400 mm, with carriages](https://west3d.com/products/berserker-mgn9h-1r-150-300-350-400-linear-rails-viking-skis-with-carriages) | 3 | **Z rails** (owner, 2026-11-22; the third Berserker 400, bought 2026-11-25, makes all three match). They were the Y rails (lite-9: rear-flush plus a 73.9 mm front extension); from lite-78 the Y rails are one-piece Hiwin MGN9H 490s (vt350#291, `bom/bom.csv`). |
| [Berserker MGN12H-1R 400 mm, with carriage](https://west3d.com/products/berserker-mgn12h-1r-300-350-400-linear-rails-viking-skis-with-carriages) | 1 | **X rail** on the Carbonara beam. It matches the model's MGN12 × 400. |
| [LDO 42STH48-2504AH (S55) high-temp NEMA 17](https://west3d.com/products/ldo-motors-42sth48-2504ah-s55-super-power-high-temp-nema-17-stepper-motor-high-performance-high-temperature-55mm-shaft) | 2 | XY motors. The 55 mm shaft is over Monolith's 37 mm minimum for 9 mm belts. **Decision (2026-11-04): 2WD.** AWD isn't planned; it would need 2 more motors and 2 more drivers. |
| [Trident Backbone by clee, 350](https://west3d.com/products/trident-backbone-by-clee) | 1 | Replaces the three printed Z motor mounts with one steel plate. **"NOT COMPATIBLE WITH TRIDENT R2"**, and it conflicts with an inverted-electronics layout (#5). It was designed for the stock Trident frame and bolts "in the same locations as the printed parts". **Decision: Trident R1.** **Checked in lite-5:** the model already has it (`backbone-350 v2`). All 13 holes match the [DXF](https://github.com/clee/TridentBackbone) within 0.1 mm. Every M5 hole lands on a 4040/2040 slot centre, so it needs no frame machining. The stock Z cable anchors collide with it and need replacing (#7). |

## Bed

| Part | Qty | Design impact |
|---|---|---|
| [Kinematic mount, Voron Trident, aluminium (standard)](https://west3d.com/products/kinematics-mount-voron-trident) | 1 | The model already has a kinematic bed mount. Its geometry needs checking against this one. |
| [LDO 350 aluminium build plate kit](https://west3d.com/products/voron-v2-4-aluminum-build-plate-complete-kit-by-ldo-systems-heater-magnet-and-fuse-pre-applied-to-plate) | 1 | Heater, magnet and fuse come pre-applied. The fuse is the bed's thermal fuse: no separate one to buy (owner, 2026-11-27). |
| [Berserker Plata textured flex plate, 355×355](https://west3d.com/products/berserker-plata-print-surface-flex-plate-single-sided-texture) | 1 | Together with the plate and kinematic mount, sets the bed stack height and therefore Z travel. |

## Toolhead

| Part | Qty | Design impact |
|---|---|---|
| [Orbitool O2S toolhead PCB](https://west3d.com/products/orbitool-toolhead-pcb-board-for-orbiter-2-o2-and-smart-orbiter-3-so3-by-ldo-motors?variant=45224824832212) | 1 | Owner owns one head's worth (2026-11-19). **2 needed** (one per head; both heads have it in the model since lite-30, #6). Mounts on the Orbiter; with the Smart Sensor the bowden inlet is 18.25 mm higher (the sensor's collet top). The Nitehawk-36 it replaces is **not used** (2 removed from the model in lite-30). Every extra MadMax tool needs another (#19). |
| [Orbiter Smart Filament Sensor (OSS) kit](https://west3d.com/products/orbiter-filament-sensor-complete-kit-for-orbiter-extruder-v20-by-ldo-motors) | 1 | Owner owns one head's worth (2026-11-19). **2 needed**, one per head (in the model since lite-30, #6). Plugs into the O2S. |
| Vindr Berserker 4010B-24V-P blower (part cooling) | 2 (one head's pair; owner, 2026-11-19) | **Check the pair is Berserker's newer 4010 design** (the A4T README marks older Vindr 4010s incompatible). **4 needed for the 2-tool build**, 2 per head, one in each A4Tv2 4010 duct (10 in the model since lite-37, #19; the 3 middle heads' 6 come when those tools are built, `notes/dock-survey.md`). Modelled from the user's measurements (no vendor CAD). Each is held by **4 × M2 × 10 self-tapping screws** into the duct's pilot holes (16 for the 2-tool build); its 34.5 mm hole square sits 0.25 mm per side inside the duct's 35.0, which the self-tappers take. |
| [Beacon RevH, Normal](https://west3d.com/products/beacon-probe-eddy-current-surface-scanner-for-3d-printers?variant=46106145882324) | 1 | **Owned (owner, 2026-11-25).** Normal, from West3D (chosen 2026-11-17): style "Beacon H Normal", SKU WES2566NOR, $81.49 on 2026-11-17, with a USB cable of 6 ft 7 in (2.01 m; the owner measured it 2026-11-27, the listing says 6 ft). Check the cable reaches the Pi 5 through #54's X and Y chains before relying on it (Filastruder also lists a 10.5 ft option). Connector to the rear, under the MadMax carriage (lite-24, #54): coil face 2.60 mm above the nozzle tip, Klipper offsets x 0, y +27.4. 3.5 g (beacon3d.com). Low Profile-rear also fits (lite-24 log), front doesn't. Reference images: `~/Documents/VT350/references/toolhead/beacon-h/` (`RevH-N.png` is the Normal). |
| [Mellow MultiHead Zero (black)](https://west3d.com/products/mellow-multiohead-zero-precision-xyz-nozzle-offset-calibration-tool-black) | 1 | **Owned (owner, 2026-11-25).** The nozzle offset probe (#186): in the model since lite-61, on the bed frame's front 2020. |
| A4Tv2 kit | 1 | **Owned (owner, 2026-11-25).** Which kit (West3D's A4T fastener kit V2, or another) and its contents are still to record; then the A4Tv2 screw rows in `bom/bom.csv` can be marked. |
| 6×3 mm N52 magnets | 15 | **Owned (owner, 2026-11-25).** The MadMax carriage's 6 + one head's 9 (tool plate 6, dock keyslot plate 3); 9 more for the second head (`bom/bom.csv`). |
| Dock hardware: M3 heat-set inserts (M3x3x5, 150-pack), M3 standoffs (4 mm body 10-pack; 8 mm body 12-pack), M3x6 FHCS (magnetic steel) | — | **Owned (owner, 2026-11-25).** The #59 dock hooks and the 4010 duct inserts (`bom/bom.csv`). |
| [BERSERKER VINDR 2510A-24V-A axial fan](https://west3d.com/products/berserker-vindr-ultra-performance-2510-axial-fan-24v-2510a-24v-a-25x10mm) (hotend cooling) | not yet recorded | **Chosen as the hotend fan (owner, 2026-11-17)**; whether one is already owned is still to confirm. Out of stock on West3D 2026-11-17: owner set the restock notification. The O2S hot-end fan output takes 12 or 24 V fans with tach only (O2S manual v1.5 §3.7: `max_power: 1.0` for 24 V, `cycle_time: 0.0001`), so stay with this 24 V fan. 24 V, 25x10 mm, dual ball bearing, 20000 RPM, 5.86 CFM, with a tachometer line (the O2S's hotend-fan output reads RPM). One per head; the model has a generic 2510. West3D lists a 28 g shipping weight, which isn't the fan's own mass (#60). |
| [LDO Orbiter V2.5](https://west3d.com/products/ldo-orbiter-extruder-v2-5-orbiter-v2-5-and-v2-0-to-v2-5-upgrade-kit) | 1 | **1 owned (owner, 2026-11-19): one head's worth.** The extruder the O2S and OSS mount on. One per head. **Motor: LDO 36STH20** (user checked the owned part, 2026-11-10). The model has the v2.0 mockup's 36STH17, and the O2S manual (v1.5 §3.12) calls for **18 mm** board standoffs with the 36STH20 + Smart Sensor (model: 14 mm). Fix the model before the parked-head clash (https://github.com/dvystrcil/vt350/issues/121). **Mass ~135 g** (orbiterprojects.com, Orbiter v2.0 page, read 2026-11-17: "Weight reduced to ~135 grams"; v2.5 uses the v2.0 body; the motor isn't named), used for the model's mass in `cad/materials/bought.json` (#60) until the owner weighs one. |
| Phaetus Dragon ACE Volcano hotend | 1 | **Owned (owner, 2026-11-19): one head's worth.** One per head. Since lite-73 (#263) it sits on the hex DAV A4Tv2 main body, no spacer, its box includes the 4 M2.5 mounting screws and the MZE (owner, 2026-11-21); the owner also owns a 0.6 TC Undertaker nozzle (measured 2026-11-20). |
| [Crossbow CNC filament cutter (DW-Tas, aluminium)](https://west3d.com/products/crossbow-cnc-filament-cutter-for-a4t-sherpa-mini-orbiter-v2-5-and-other-flat-top-extruders-by-dw-tas) | 1 | **Owned (owner, 2026-11-27): one head's worth.** One per head; the second head needs another (`bom/bom.csv`). Also needs a printed Monolith depressor. |
| [A4T - Another 4010 Toolhead Fastener Kit (BDF)](https://west3d.com/products/a4t-another-4010-toolhead-fastener-kit-bdf), SKU WES3620V6, **V1** | 1 | **V1, bought before V2; covers part of one A4Tv2 head** (owner, 2026-11-19). V1 contents (vendor page, read 2026-11-19): M3 square nut 5, M3x8 SHCS 4, M3x6 BHCS 3, M3x50 SHCS 3, M3x16 SHCS 3, M3x12 SHCS 3, M3x20 SHCS 3, M3x5x4 heat-set 3, 22.5 x 4 OD x 3.1 ID tube 2. The V2 option (same SKU) is the complete A4Tv2 set. |
| LDO Nitehawk-36 toolboard | 1 | Found in stock 2026-11-10; board version not recorded. **Not in the design**: the O2S was chosen (#6 AC1) and re-examined 2026-11-10 in [notes/reference/toolboard-o2s-vs-nitehawk36.html](reference/toolboard-o2s-vs-nitehawk36.html) (recommendation: keep the O2S; the Nitehawk is rated 65 °C with no fan-cooled figure and has no Smart Sensor port). The final choice is still open in https://github.com/dvystrcil/vt350/issues/6. |

## Electronics

| Part | Qty | Design impact |
|---|---|---|
| [BTT Octopus Pro H723, 60 V](https://west3d.com/products/btt-48v-octopus-pro-controller-board-3d-printer-control-system?variant=45102508474580) | 1 | Main MCU. The model has an Octopus Pro box in the electronics cabinet. |
| LDO LCP300-24D5 PSU | 1 | Owned (user, 2026-11-10); role not decided. A candidate for the 24 V supply that is otherwise still to buy (https://github.com/dvystrcil/vt350/issues/22). Its datasheet (outputs, current, 5 V rail) has not been checked yet. |
| [BTT TMC5160T Plus (with case)](https://west3d.com/products/tmc5160t-plus-with-case-high-voltage-stepper-motor-driver-btt) | 2 | High-voltage drivers for the 2 XY motors. |
| [BTT TMC2226](https://west3d.com/products/tmc2226-stepper-motor-driver-drivers-btt) | 3 | Drivers for the 3 Z motors. Extruders run from the toolhead boards. |
| [Omron G3NA-210B UTU DC5-24 SSR](https://west3d.com/search?type=product&q=Omron+G3NA-210B+UTU+DC5+24V+Solid+State+Relay+%28SSR%29) | 1 | Switches the bed heater. |
| Raspberry Pi 5 + NVMe HAT + drive | 1 | Klipper host (#5). |
| [BTT Pad 7](https://west3d.com/products/raspberry-pad-7-touch-screen-display-and-pi-adapter-7-inch-pad7-btt) | 1 | Shared with the Neptune over KlipperScreen's multi-printer config. Needs a quick-release mount (#5). **Removed from the model in lite-21**: the user has other ideas for where to mount it; not placed yet. |
| BOSYTRO 600 W adjustable PSU, 0–60 V, 0–10 A (Amazon, bought 2025-11-21) | 1 | Motor supply for X and Y only: the two TMC5160T Plus drivers (user, 2026-11-16). Not the Octopus: its motor input feeds the TMC2226 Z drivers, which are rated to 29 V, so it stays on the 24 V supply. The user may hang a heater on it later; at 48 V its 10 A limit gives about 480 W, shared with the motors. **Set it to 48 V with a meter before connecting anything, then lock or cover the knobs.** Its 60 V maximum is above the driver's rated input: the [BTT TMC5160T Plus wiki](https://global.bttwiki.com/TMC5160TPlus.html) spec table gives HVIN **8–56 V**, even though its feature list says "maximum 60 V". 48 V leaves headroom for the voltage the motors push back when they decelerate. The same page also says: (1) switch the driver (motor) power on **before** the logic power / mainboard; (2) the voltage from the mainboard to the driver must never exceed 24 V; (3) active cooling is required above 3 A. The 24 V supply is the same brand's 600 W 0–24 V unit (owned since 2026-11-16, next row). |
| BOSYTRO 600 W adjustable PSU, 0–24 V, 0–25 A ([listing](https://www.amazon.com/dp/B0CFQFTWVD)) | 1 | **Owned (user, 2026-11-16).** The 24 V supply (#22): Octopus Pro logic and its motor input, toolhead boards, fans, lights. The Octopus's own drivers run Z (user, 2026-11-16) and the TMC5160T Plus pair runs X and Y off the 60 V supply (the BOSYTRO 0–60 V unit above). The Octopus motor input must stay at 24 V: its TMC2226s are rated to 29 V. Set it to 24.0 V with a meter before connecting anything. The TBT7-C1 relay (next row) delays it so it comes on after the motor supply. The user's Neptune runs on the same unit. Size 215 × 113 × 50 mm (user's measurement, 2026-11-16, on #5); all its terminals are on one 113 × 50 end (user, 2026-11-16); it mounts lying flat on a printable DIN clip. The e-box depth in lite-46 (outer members at X 125) comes from those dimensions. The LDO LCP300-24D5 (above) was the fallback for this role, so its role is open again. |
| Time relay TBT7-C1 (0.1 s – 10 days) | 1 | Bought to power the drivers before the mainboard (TMC5160T Plus sequencing, row above). Intended wiring: the 60 V motor supply switches on with the printer, and the relay delays the mainboard's 24 V supply by a second or two. Before wiring it, confirm from the relay's own manual its function mode (it must be set to **on-delay**), its coil voltage and its contact rating. |
| [Nitehawk Hexa 6+1 USB adapter](https://west3d.com/search?type=product&q=Nitehawk+Hexa) | 1 | USB hub for toolhead boards (link is a search, not the product page). |
| DIN fuse holders, 5×20 mm glass | 7+ | **Owned (owner, 2026-11-27).** The e-box's F1, F2, F4–F8 (lite-54 layout); the fuses must be 5×20 mm glass, ratings still to choose (`bom/bom.csv`). |
| DIN circuit breaker, 15 A | 1 | **Owned (owner, 2026-11-27).** Q1 on the mains rail (lite-54). The layout wants **2-pole** (live and neutral); confirm this one is before wiring it. |
| Buck converter, 24 V to 5 V, 10 A, 50 W | 1 | **Owned (owner, 2026-11-27).** Feeds the Pi 5 from F8; 10 A covers the Pi 5's 5 A. |
| Wago lever connectors | — | Owned. |
| SSR DIN clamp with heatsink | 1 | For the Omron SSR above. |
| DIN holders | — | **To print** for any part that needs one. |

## Enclosure

| Part | Qty | Design impact |
|---|---|---|
| [Nocturne USB camera (Luke's Laboratory, 96°)](https://west3d.com/products/nocturne-usb-camera-for-3d-printers-by-lukes-laboratory) | 1 | **Owned (owner, 2026-11-27).** The chamber camera (#14), rated to 70 °C. |
| Carbon-felt insulation pad, 10 mm | 3 | Owned (`notes/status.md`, 2026-11-05). Sealed in aluminium; in the model the roof and back pads sit inside their panels (lite-69; the back one 3.9 mm until the compression test) and the right-wall pad between the panel and the electronics. **Test a pad for conductivity first** (#14). Vendor and size not recorded. |

## Filament

| Part | Qty | Design impact |
|---|---|---|
| PTFE bowden, measured OD 4.12 mm | — | Modeled as a solid Ø4.12 rod to a top-rear exit (lite-5, #3). |
| [EMU](https://github.com/DW-Tas/EMU) (to be built) | — | Filament source behind the printer; the bowden tubes exit at the top rear. |
