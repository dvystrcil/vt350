# Parts already owned

What's already bought for the VT350, and what each part means for the design.
Links are the West3D listings the parts came from. Facts quoted here come from
those listings or the project READMEs linked from them.

## Motion

| Part | Qty | Design impact |
|---|---|---|
| [Monolith CNC Gantry by LDO](https://west3d.com/products/monolith-cnc-gantry-by-ldo-systems-v2-4-and-trident-compatible-with-2wd-and-awd) | 1 | The kit does both 2WD and AWD and supports 9/10 mm belts. Its X rail faces the front (needed for MadMax). It includes "AWD front extrusion support for toolchangers". The model still has the **printed** Monolith joints (#19). |
| [Carbonara carbon-fibre X beam](https://west3d.com/products/carbonara-carbon-fiber-x-beam-for-voron-3d-printers?variant=46478960656596) | 1 | The 350 size is 430 mm and 84.3 g. Rated 110 °C short-term. CAD: [Monolith MISC/CF_tube_mounting](https://github.com/Monolith3D/MISC/tree/main/CF_tube_mounting). |
| [Gates GT2 closed-loop belt 2.4 m, 9 mm RF](https://west3d.com/products/gates-gt2-closed-loop-belt-2-4m-ll-2gt-6-6mm-wide-rf-reinforced?variant=47586401616084) | 2 | 9 mm belts for the Monolith. Cut open to length. |
| [LDO 42STH48-2504AH (S55) high-temp NEMA 17](https://west3d.com/products/ldo-motors-42sth48-2504ah-s55-super-power-high-temp-nema-17-stepper-motor-high-performance-high-temperature-55mm-shaft) | 2 | XY motors. The 55 mm shaft is over Monolith's 37 mm minimum for 9 mm belts. **Two motors means 2WD.** AWD needs 2 more motors and 2 more drivers. |
| [Trident Backbone by clee, 350](https://west3d.com/products/trident-backbone-by-clee) | 1 | Replaces the three printed Z motor mounts with one steel plate. **"NOT COMPATIBLE WITH TRIDENT R2"**, and it conflicts with an inverted-electronics layout (#5). It was designed for the stock Trident frame and bolts "in the same locations as the printed parts". Fit on this 4040 frame needs checking against its DXF ([clee/TridentBackbone](https://github.com/clee/TridentBackbone)) before the frame order (#7). |

## Bed

| Part | Qty | Design impact |
|---|---|---|
| [Kinematic mount, Voron Trident, aluminium (standard)](https://west3d.com/products/kinematics-mount-voron-trident) | 1 | The model already has a kinematic bed mount. Its geometry needs checking against this one. |
| [LDO 350 aluminium build plate kit](https://west3d.com/products/voron-v2-4-aluminum-build-plate-complete-kit-by-ldo-systems-heater-magnet-and-fuse-pre-applied-to-plate) | 1 | Heater, magnet and fuse come pre-applied. |
| [Berserker Plata textured flex plate, 355×355](https://west3d.com/products/berserker-plata-print-surface-flex-plate-single-sided-texture) | 1 | Together with the plate and kinematic mount, sets the bed stack height and therefore Z travel. |

## Toolhead

| Part | Qty | Design impact |
|---|---|---|
| [Orbitool O2S toolhead PCB](https://west3d.com/products/orbitool-toolhead-pcb-board-for-orbiter-2-o2-and-smart-orbiter-3-so3-by-ldo-motors?variant=45224824832212) | 1 | Mounts on the Orbiter and raises the bowden inlet; not modeled yet (#6). **One set covers one head.** Every extra MadMax tool needs another (#19). |
| [Orbiter Smart Filament Sensor (OSS) kit](https://west3d.com/products/orbiter-filament-sensor-complete-kit-for-orbiter-extruder-v20-by-ldo-motors) | 1 | Same as the O2S: one per head. |

## Electronics

| Part | Qty | Design impact |
|---|---|---|
| [BTT Octopus Pro H723, 60 V](https://west3d.com/products/btt-48v-octopus-pro-controller-board-3d-printer-control-system?variant=45102508474580) | 1 | Main MCU. The model has an Octopus Pro box in the electronics cabinet. |
| [BTT TMC5160T Plus (with case)](https://west3d.com/products/tmc5160t-plus-with-case-high-voltage-stepper-motor-driver-btt) | 2 | High-voltage drivers for the 2 XY motors. |
| [BTT TMC2226](https://west3d.com/products/tmc2226-stepper-motor-driver-drivers-btt) | 3 | Drivers for the 3 Z motors. Extruders run from the toolhead boards. |
| [Omron G3NA-210B UTU DC5-24 SSR](https://west3d.com/search?type=product&q=Omron+G3NA-210B+UTU+DC5+24V+Solid+State+Relay+%28SSR%29) | 1 | Switches the bed heater. |
| Raspberry Pi 5 + NVMe HAT + drive | 1 | Klipper host (#5). |
| [BTT Pad 7](https://west3d.com/products/raspberry-pad-7-touch-screen-display-and-pi-adapter-7-inch-pad7-btt) | 1 | Shared with the Neptune over KlipperScreen's multi-printer config. Needs a quick-release mount (#5). |

## Filament

| Part | Qty | Design impact |
|---|---|---|
| PTFE bowden, measured OD 4.12 mm | — | Modeled as a solid Ø4.12 rod to a top-rear exit (lite-5, #3). |
| [EMU](https://github.com/DW-Tas/EMU) (to be built) | — | Filament source behind the printer; the bowden tubes exit at the top rear. |
