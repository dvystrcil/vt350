# Slicer check: `platform/parts/slice-check.py` (#70)

Headless slice of print-oriented STLs. It reports support, time, filament, grams and cost, and the slicer's
warnings. It fails if support lands in a keep-out box, and it plots each part's G-code.

```bash
python3 platform/parts/slice-check.py parts/printed/vt350/a4tv2-duct-4010-madmax-dock/*.stl        # report + previews
python3 platform/parts/slice-check.py <stl…> --keepout parts/slice/keepout.json --out <dir>         # explicit
python3 platform/parts/slice-check.py --slicer prusa <stl…>                                         # the PrusaSlicer check
```

- **Slicer:** OrcaSlicer by default (gpu-batch-docker#13), with the Neptune presets the prints actually use, so time,
  grams and cost are real estimates. `--slicer prusa` is the original PrusaSlicer check; see "Orca or PrusaSlicer"
  below for why Orca is the default.
- **Output:** `~/Documents/VT350/slice/<UTC>/`, holding:
  - `report.md`: one row per part, plus per-feature time, grams and speeds for Orca;
  - `<part>.png`: top, front and side views, with support **red** and keep-out boxes **blue**;
  - the `.gcode` and the slicer log;
  - for Orca, also `<part>.statistics.json` and `<part>.layers.csv` (time per layer).

  The last line is `slice-check: OK`, or `slice-check: FAILED …` with exit 1. A small part takes about 1 s to slice;
  the largest A4Tv2 body takes about 1 min with its plot.
- **Orca presets:** `orca/`, the three the user prints with (picked 2026-11-07), exported from the GUI with
  `print_host` blanked:

  | Type | Preset |
  |---|---|
  | Machine | `Elegoo Neptune 4 Pro (0.4 nozzle) -  MMU` (two spaces before `MMU`) |
  | Process | `0.20mm Standard @Elegoo Neptune4Pro (0.4 nozzle) - MMU` |
  | Filament | `E RPETG Red - MMU - cht-mze + bimetal` |

  `orca/orca.json` names them, and a change to one is a reviewed diff. They hold only overrides. Their `inherits`
  parents come from the running Orca's own Elegoo system profiles, which slice-check installs into a fresh datadir
  under the output dir, so your GUI config never leaks in.
  
  The process gets `support_check` from `orca.json`: supports on, everywhere, for overhangs flatter than 45°, as in
  the Prusa profile. Your preset leaves supports off and turns them on per plate.
- **Prusa profile:** `petg-0.4-0.2.ini` is pinned: PETG, 0.4 nozzle, 0.2 layers, automatic supports for overhangs
  flatter than 45°. It's loaded over PrusaSlicer's defaults with an empty `--datadir`. It has no machine limits,
  speeds or filament density, so its time is rough and its grams and cost are 0.
- **Keep-out boxes:** `keepout.json`, in each STL's own coordinates. Support inside a box fails the check, e.g. a
  duct's air channel.
- **Needs:** the Orca flatpak (`com.orcaslicer.OrcaSlicer`, or `ORCA_SLICER`) or the PrusaSlicer one, plus
  `rsvg-convert`. Flatpaks can't see `/tmp`, so output stays under `$HOME`. In the cluster:
  `harbor.sirddail.net/ai/gpu-batch-orcaslicer`, the same Flathub build, byte-identical G-code
  (gpu-batch-docker#13 AC5).

## Reading the support number

The number is what the slicer's **automatic** supports would add. Parts designed to print without supports (Voron,
Clicky-Clack) still show some, e.g. in nut traps and slots that their designers bridge over:

| Part (upstream, print-oriented) | Orca support cm³ | PrusaSlicer support cm³ |
|---|---|---|
| Voron `z_carriage_left` | 0.37 | 1.04 |
| Clicky-Clack `Latch` | 0.70 | 2.02 |
| LDO cable clip S | 0.02 | 0.12 |
| MadMax SpeedClip 9 mm | 0.05 | 0.28 |
| A4Tv2 `[t]_LED_diffuser` | 0.01 | 0.01 |
| A4Tv2 main body | 6.26 | 11.75 |

The two slicers support the same overhangs. Orca's numbers are smaller because its `snug` support hugs each overhang,
while PrusaSlicer's grid spreads out around it, and on the A4Tv2 body it also fills the round bore.

The red areas in the preview show where the support goes. So **compare a remix against its upstream original** with the
same profile and slicer; don't read the absolute number as pass or fail. E.g. for #59, slice the remixed duct next
to DW-Tas's `A4Tv2_4010_Ducts.stl`.

## Orca or PrusaSlicer (gpu-batch-docker#13 AC4)

Both slicers ran in their gpu-batch images on the same STLs. The slice times are the slicer process alone, without
the plot.

| Part | Time, Orca | Time, Prusa | Grams, Orca | Slice wall, Orca | Slice wall, Prusa | Peak RSS, Orca | Peak RSS, Prusa |
|---|---|---|---|---|---|---|---|
| A4Tv2 main body | 1h 18m 34s | 4h 51m 3s | 34.24 | 4.8 s | 10.6 s | 526 MB | 653 MB |
| Voron `z_carriage_left` | 32m 28s | 1h 44m 26s | 16.74 | 1.3 s | 1.1 s | 316 MB | 184 MB |
| Clicky-Clack `Latch` | 42m 37s | 1h 10m 31s | 8.05 | 0.9 s | 0.6 s | 252 MB | 107 MB |
| A4Tv2 `[t]_LED_diffuser` | 3m 54s | 4m 15s | 0.33 | 0.4 s | — | 234 MB | — |

Orca replaces PrusaSlicer as the default, for these reasons:
- Its time, grams and cost come from the presets the Neptune actually prints with. The Prusa profile has no machine
  limits or speeds, so its time is roughly 1.5–4× Orca's here, and its grams are 0.
- Its support is the support you would print.
- It slices the big part twice as fast, though it uses about 250 MB more on small ones.

PrusaSlicer stays available as `--slicer prusa`, e.g. to compare against older reports. Neither slicer reported a
warning on these parts.

Orca's estimates match its GUI. The user's `chamber-heater-chamber-heater-body` plate 1 sliced headless, in the image
and on the laptop, gives 56.26 m, 146.15 g and cost 3.36, the same as the GUI. Time is 2h 42m 10s against the GUI's
2h 48m; that GUI number was read on 2026-11-07, the day Flathub moved from 2.4.2 to 2.5.0. Checking an estimate
against a real print's time is still to do.

## Cross-checking in the GUI

Orca: open `<part>.gcode` from the output dir in Orca (File → Import → G-code), or slice the STL there with the three
presets above and supports on.

To see the same slice in PrusaSlicer's GUI, use the same profile and an empty preset folder, then press Slice:

```bash
flatpak run com.prusa3d.PrusaSlicer --datadir ~/Documents/VT350/slice/gui-datadir --load "$PWD/parts/slice/petg-0.4-0.2.ini" "$PWD/<part>.stl"
```
