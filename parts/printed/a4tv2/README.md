# A4Tv2 toolhead

Copied **unchanged** from [DW-Tas/A4Tv2](https://github.com/DW-Tas/A4Tv2) at commit [`888755a`](https://github.com/DW-Tas/A4Tv2/tree/888755a97da9e1bd3062c35c914538342ef7d6f2). By DW-Tas.

**Licence:** **CC BY-NC-SA 4.0** (the upstream repository's `LICENSE`, copied here unchanged). Redistribution is allowed with attribution (creator, licence link, and whether it was changed), **non-commercial only**, and adaptations must use the same licence. This repo is non-commercial.

Variant for this build (lite-15): Dragon Rapido UHF body, Orbiter (`o2`), XOL carriage mount, Crossbow adapter, UHF hotend-fan duct with a 2510 fan, low LED. The 4010 part-cooling ducts are **not** here: this build prints the remix with dock bosses (`../vt350/a4tv2-duct-4010-madmax-dock/`). The upstream README adds: "The non-commercial aspect of this license is for cases where A4Tv2 is the product, not the use of A4Tv2 to create products."

| File here | Upstream path at the pinned commit | Qty | Our changes |
|---|---|---|---|
| `main-body_dragon-rapido-UHF_o2_xol.stl` | [`STL/main_bodies/main-body_dragon-rapido-UHF_o2_xol.stl`](https://github.com/DW-Tas/A4Tv2/blob/888755a97da9e1bd3062c35c914538342ef7d6f2/STL/main_bodies/main-body_dragon-rapido-UHF_o2_xol.stl) | 2 | none |
| `[a]_orbiter-crossbow-adapter_o2_xol.stl` | [`STL/extruder_adapters/[a]_orbiter-crossbow-adapter_o2_xol.stl`](https://github.com/DW-Tas/A4Tv2/blob/888755a97da9e1bd3062c35c914538342ef7d6f2/STL/extruder_adapters/%5Ba%5D_orbiter-crossbow-adapter_o2_xol.stl) | 2 | none |
| `Duct-HEF-Dragon-UHF.stl` | [`STL/ducts/Duct-HEF-Dragon-UHF.stl`](https://github.com/DW-Tas/A4Tv2/blob/888755a97da9e1bd3062c35c914538342ef7d6f2/STL/ducts/Duct-HEF-Dragon-UHF.stl) | 2 | none |
| `LED_Carrier.stl` | [`STL/led_carrier/LED_Carrier.stl`](https://github.com/DW-Tas/A4Tv2/blob/888755a97da9e1bd3062c35c914538342ef7d6f2/STL/led_carrier/LED_Carrier.stl) | 2 | none |
| `[t]_LED_diffuser.stl` | [`STL/led_carrier/[t]_LED_diffuser.stl`](https://github.com/DW-Tas/A4Tv2/blob/888755a97da9e1bd3062c35c914538342ef7d6f2/STL/led_carrier/%5Bt%5D_LED_diffuser.stl) | 2 | none |

Each file's sha256 is in `../manifest.csv`; `parts/check-printed.py --upstream` re-downloads every file at its commit and compares.
