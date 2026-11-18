# Ambrosia filament (West3D): datasheet values in one place

The build prints with Ambrosia filament from West3D (owner, 2026-11-17), so this collects every grade's technical data
from its West3D product page, saving a page-by-page lookup. Values are copied as published, **read 2026-11-17**. Ambrosia
says they're for reference and that suitability is the user's to decide. Re-check a product page before relying on a
number for a design limit. Silk, Sparkle, Dolos, PLA, PHA and Foaming TPU are left out (not candidates for this printer).

**Decided (owner, 2026-11-17):** toolhead parts are **PET-GF** (the heads' printed parts, the MadMax tool plates and the carriage); every other printed part is **ASA** (the owner can't print ABS); clear parts are **PETG**. lite-63 assigns these cards in the model. The CoM study (#60) uses its density, **1.405 g/cm³** (the
middle of 1.40–1.41).

Every grade and in-stock colour is also a FreeCAD material card: `cad/materials/` (how to use them is in its README).

## Mechanical and thermal (ISO test methods as listed)

| Grade | Density g/cm³ (ISO 1183) | Tensile MPa (ISO 527) | Elongation % | Flexural modulus MPa | Flexural strength MPa (ISO 178) | Impact kJ/m² (ISO 180) | HDT °C @ 0.455 MPa (ISO 75) |
|---|---|---|---|---|---|---|---|
| [PET-GF](https://west3d.com/products/ambrosia-pet-gf-glass-filled-pet-filament-of-the-gods-1kg-spool) | 1.40–1.41 | 75 | 4–5 | 4500 | 140 | 40 | **205** |
| [PPS-CF](https://west3d.com/products/ambrosia-pps-cf-filament-of-the-gods-1kg-bambu-ams-friendly-high-temperature-polycarbonate-spools-premium-3d-printing-filament) | 1.30–1.31 | 100–110 | 1–3 | 5500–6000 | 170–180 | 25–30 | **245** |
| [PC-CF](https://west3d.com/products/ambrosia-pc-cf-filament-of-the-gods-1kg-bambu-ams-friendly-cardboard-spools-premium-3d-printing-filament-house-polycarbonate-cf-pccf) | 1.21 | 40 | 7.5–8.5 | 2400 | 85 | 5.5 | 120 |
| [PC-ABS](https://west3d.com/products/ambrosia-pc-abs-filament-of-the-gods-1kg-bambu-ams-friendly-cardboard-spools-premium-3d-printing-filament-house-polycarbonate-abs) | 1.14–1.15 | 43.5–45.5 | 24–26 | 800–950 | 71.5–74.5 | 43.5–44.5 | 123 |
| [ASA](https://west3d.com/products/ambrosia-asa-filament-of-the-gods-1kg-bambu-friendly-cardboard-spools-premium-3d-printing-filament) | 1.08–1.09 | 42–45 | 9–12 | 1200–1400 | 75–79 | 19–20 | 88 |
| [ASA-CF](https://west3d.com/products/ambrosia-asa-cf-filament-of-the-gods-1kg-bambu-ams-friendly-cardboard-spools-premium-3d-printing-filament) | 1.09–1.10 | 39–42 | 15.5–17.5 | 850–900 | 80–82.5 | 10.5–12 | 88 |
| [ASA-GF](https://west3d.com/products/ambrosia-asa-gf-glass-filled-asa-filament-of-the-gods-1kg-bambu-ams-friendly-cardboard-spools-premium-3d-printing-filament) | 1.12–1.13 | 36 | 1–2 | 4000 | 65 | 6.7 | 88+ (TBD) |
| [Uber ABS (ABS+)](https://west3d.com/products/ambrosia-uber-abs-filament-of-the-gods-1kg-bambu-friendly-cardboard-spools-premium-3d-printing-filament-abs) | 1.08–1.10 | 33–37 | 9–15 | 1500–1650 | 65–67 | 12–13.5 | 85 |
| [ABS Matte](https://west3d.com/products/ambrosia-abs-matte-filament-of-the-gods-1kg-bambu-ams-friendly-cardboard-spools-premium-3d-printing-filament) | 1.03 | 39 | 45 | 1800 | 58 | 29 | 88 **@ 1.8 MPa** (a harder test than the others' 0.455 MPa: not comparable) |
| [PETG](https://west3d.com/products/ambrosia-petg-filament-of-the-gods-1kg-bambu-ams-friendly-cardboard-spools-premium-3d-printing-filament) | 1.27–1.28 | 41–45 | 10–12 | 1400–1500 | 64–66 | 5–6 | 68 |
| [PCTG](https://west3d.com/products/ambrosia-pctg-filament-of-the-gods-1kg-spool) | TBD | TBD | TBD | TBD | TBD | TBD | TBD (the page lists every value as TBD) |
| [TPU 95A](https://west3d.com/products/ambrosia-tpu-95-filament-of-the-gods-1kg-bambu-ams-friendly-cardboard-spools-premium-3d-printing-filament-tpu95) | 1.22–1.25 | 27–28 | 800–1000 | 6–7 | 7–9 | no break | 95 |

## Print settings (Ambrosia's ranges, [their recommended value])

| Grade | Nozzle °C | Bed °C | Chamber ("environmental") °C | Notes |
|---|---|---|---|---|
| PET-GF | 270–290 [280] | 80–105 [100] | 40–60 [55] | abrasive: hardened or tungsten-carbide nozzle; dry before printing |
| PPS-CF | 300–350 [340] | 90–110 [100] | 40–120 [70] | abrasive; check the hotend's maximum temperature before planning on it |
| PC-CF | 250–290 [270] | 100–115 [110] | 40–120 [60] | abrasive; contains ~10% PETG; absorbs moisture |
| PC-ABS | 250–280 [270] | 100–115 [110] | 40–120 [60] | |
| ASA | 230–260 [250] | 100–115 [110] | 40–120 [45] | |
| ASA-CF | 250–280 [270] | 100–120 [110] | 40–120 [45] | abrasive |
| ASA-GF | 250–280 [270] | 100–120 [110] | 40–120 [45] | abrasive |
| Uber ABS | 225–250 [235] | 75–110 [100] | 30–100 [40] | |
| ABS Matte | 230–265 [245] | 75–115 [110] | 30–100 [40] | |
| PETG | 225–260 [250] | 65–80 [80] | 15–50 [30] | |
| PCTG | 240–270 [255] | 70–90 [80] | 15–50 [30] | |
| TPU 95A | 190–220 [210] | 50–65 [60] | 40–80 [35] | |

**PET-GF fibre content:** the US product page's description says chopped glass fibre **15%**, and a regional West3D page
says **30%**. The density and mechanical values above are the same on both.

## Door hinges (Clicky-Clack, 3 per door): material

Owner, 2026-11-17: printed door hinges tend to sag over time, so they need a creep-resistant material. On Ambrosia's
own numbers:
- **PET-GF** has the highest stiffness and HDT that this printer can surely print (4500 MPa, 205 °C), and Ambrosia
  markets it as creep-resistant.
- **PPS-CF** is stiffer still (5500–6000 MPa, HDT 245 °C) but needs a 300–350 °C nozzle.
- **PC-CF** (2400 MPa, 120 °C) and the ASA grades are less stiff.

A datasheet doesn't measure creep directly: stiffness and HDT are the closest proxies listed. The hinge's own design
(how its pin carries the door's weight) matters as much as the material.

**Decided (owner, 2026-11-17): PET-GF.** PPS-CF is out: its 300–350 °C nozzle range is beyond what the owner prints.
