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
| [Berserker MGN9H-1R 400 mm, with carriages](https://west3d.com/products/berserker-mgn9h-1r-150-300-350-400-linear-rails-viking-skis-with-carriages) | 2 | **Y rails.** lite-9 uses them rear-flush (Y 40…440) plus a 73.9 mm front extension per side, which the blocks only ride while docking. Printed or cut steel is still open. 450 is the longest MGN9 West3D sells, and 500 won't fit in the 473.9 mm gap between the milled mounts. |
| [Berserker MGN12H-1R 400 mm, with carriage](https://west3d.com/products/berserker-mgn12h-1r-300-350-400-linear-rails-viking-skis-with-carriages) | 1 | **X rail** on the Carbonara beam. It matches the model's MGN12 × 400. |
| [LDO 42STH48-2504AH (S55) high-temp NEMA 17](https://west3d.com/products/ldo-motors-42sth48-2504ah-s55-super-power-high-temp-nema-17-stepper-motor-high-performance-high-temperature-55mm-shaft) | 2 | XY motors. The 55 mm shaft is over Monolith's 37 mm minimum for 9 mm belts. **Decision (2026-11-04): 2WD.** AWD isn't planned; it would need 2 more motors and 2 more drivers. |
| [Trident Backbone by clee, 350](https://west3d.com/products/trident-backbone-by-clee) | 1 | Replaces the three printed Z motor mounts with one steel plate. **"NOT COMPATIBLE WITH TRIDENT R2"**, and it conflicts with an inverted-electronics layout (#5). It was designed for the stock Trident frame and bolts "in the same locations as the printed parts". **Decision: Trident R1.** **Checked in lite-5:** the model already has it (`backbone-350 v2`). All 13 holes match the [DXF](https://github.com/clee/TridentBackbone) within 0.1 mm. Every M5 hole lands on a 4040/2040 slot centre, so it needs no frame machining. The stock Z cable anchors collide with it and need replacing (#7). |

## Bed

| Part | Qty | Design impact |
|---|---|---|
| [Kinematic mount, Voron Trident, aluminium (standard)](https://west3d.com/products/kinematics-mount-voron-trident) | 1 | The model already has a kinematic bed mount. Its geometry needs checking against this one. |
| [LDO 350 aluminium build plate kit](https://west3d.com/products/voron-v2-4-aluminum-build-plate-complete-kit-by-ldo-systems-heater-magnet-and-fuse-pre-applied-to-plate) | 1 | Heater, magnet and fuse come pre-applied. |
| [Berserker Plata textured flex plate, 355×355](https://west3d.com/products/berserker-plata-print-surface-flex-plate-single-sided-texture) | 1 | Together with the plate and kinematic mount, sets the bed stack height and therefore Z travel. |

## Toolhead

| Part | Qty | Design impact |
|---|---|---|
| [Orbitool O2S toolhead PCB](https://west3d.com/products/orbitool-toolhead-pcb-board-for-orbiter-2-o2-and-smart-orbiter-3-so3-by-ldo-motors?variant=45224824832212) | 1 | **2 needed** (one per head; both heads have it in the model since lite-30, #6). Mounts on the Orbiter; with the Smart Sensor the bowden inlet is 18.25 mm higher (the sensor's collet top). The Nitehawk-36 it replaces is **not used** (2 removed from the model in lite-30). Every extra MadMax tool needs another (#19). |
| [Orbiter Smart Filament Sensor (OSS) kit](https://west3d.com/products/orbiter-filament-sensor-complete-kit-for-orbiter-extruder-v20-by-ldo-motors) | 1 | **2 needed**, one per head (in the model since lite-30, #6). Plugs into the O2S. |
| [LDO Orbiter V2.5](https://west3d.com/products/ldo-orbiter-extruder-v2-5-orbiter-v2-5-and-v2-0-to-v2-5-upgrade-kit) | not yet recorded | The extruder the O2S and OSS mount on. One per head. |

## Electronics

| Part | Qty | Design impact |
|---|---|---|
| [BTT Octopus Pro H723, 60 V](https://west3d.com/products/btt-48v-octopus-pro-controller-board-3d-printer-control-system?variant=45102508474580) | 1 | Main MCU. The model has an Octopus Pro box in the electronics cabinet. |
| [BTT TMC5160T Plus (with case)](https://west3d.com/products/tmc5160t-plus-with-case-high-voltage-stepper-motor-driver-btt) | 2 | High-voltage drivers for the 2 XY motors. |
| [BTT TMC2226](https://west3d.com/products/tmc2226-stepper-motor-driver-drivers-btt) | 3 | Drivers for the 3 Z motors. Extruders run from the toolhead boards. |
| [Omron G3NA-210B UTU DC5-24 SSR](https://west3d.com/search?type=product&q=Omron+G3NA-210B+UTU+DC5+24V+Solid+State+Relay+%28SSR%29) | 1 | Switches the bed heater. |
| Raspberry Pi 5 + NVMe HAT + drive | 1 | Klipper host (#5). |
| [BTT Pad 7](https://west3d.com/products/raspberry-pad-7-touch-screen-display-and-pi-adapter-7-inch-pad7-btt) | 1 | Shared with the Neptune over KlipperScreen's multi-printer config. Needs a quick-release mount (#5). **Removed from the model in lite-21**: the user has other ideas for where to mount it; not placed yet. |
| BOSYTRO 600 W adjustable PSU, 0–60 V, 0–10 A (Amazon, bought 2025-11-21) | 1 | Motor supply (Octopus Pro H723 60 V, TMC5160T Plus). **Set it to 48 V with a meter before connecting anything, then lock or cover the knobs.** Its 60 V maximum is above the driver's rated input: the [BTT TMC5160T Plus wiki](https://global.bttwiki.com/TMC5160TPlus.html) spec table gives HVIN **8–56 V**, even though its feature list says "maximum 60 V". 48 V leaves headroom for the voltage the motors push back when they decelerate. The same page also says: (1) switch the driver (motor) power on **before** the logic power / mainboard; (2) the voltage from the mainboard to the driver must never exceed 24 V; (3) active cooling is required above 3 A. Check the Octopus Pro H723 60 V's own motor-input rating as well. The 24 V supply will be the same brand's 600 W 0–24 V unit (to buy, #22). |
| Time relay TBT7-C1 (0.1 s – 10 days) | 1 | Bought to power the drivers before the mainboard (TMC5160T Plus sequencing, row above). Intended wiring: the 60 V motor supply switches on with the printer, and the relay delays the mainboard's 24 V supply by a second or two. Before wiring it, confirm from the relay's own manual its function mode (it must be set to **on-delay**), its coil voltage and its contact rating. |
| [Nitehawk Hexa 6+1 USB adapter](https://west3d.com/search?type=product&q=Nitehawk+Hexa) | 1 | USB hub for toolhead boards (link is a search, not the product page). |
| Wago lever connectors | — | Owned. |
| SSR DIN clamp with heatsink | 1 | For the Omron SSR above. |
| DIN holders | — | **To print** for any part that needs one. |

## Filament

| Part | Qty | Design impact |
|---|---|---|
| PTFE bowden, measured OD 4.12 mm | — | Modeled as a solid Ø4.12 rod to a top-rear exit (lite-5, #3). |
| [EMU](https://github.com/DW-Tas/EMU) (to be built) | — | Filament source behind the printer; the bowden tubes exit at the top rear. |
