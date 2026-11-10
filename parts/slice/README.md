# Slicer check: `platform/parts/slice-check.py` (#70)

Headless PrusaSlicer slice of print-oriented STLs. It reports support, time, filament and the slicer's warnings,
fails if support lands in a keep-out box, and plots each part's G-code.

```bash
python3 platform/parts/slice-check.py parts/printed/vt350/a4tv2-duct-4010-madmax-dock/*.stl        # report + previews
python3 platform/parts/slice-check.py <stl…> --keepout parts/slice/keepout.json --out <dir>         # explicit
```

- **Output:** `~/Documents/VT350/slice/<UTC>/`, holding `report.md` (one row per part), `<part>.png` (top, front and side views; support **red**, keep-out boxes **blue**), the `.gcode` and the slicer log. The last line is `slice-check: OK`, or `slice-check: FAILED …` with exit 1. ~1 s to slice a small part; the largest A4Tv2 body takes ~1 min with its plot.
- **Profile:** `petg-0.4-0.2.ini` is pinned: PETG, 0.4 nozzle, 0.2 layers, automatic supports for overhangs flatter than 45°. It's loaded over PrusaSlicer's defaults with an empty `--datadir`, so your GUI presets never leak in.
- **Keep-out boxes:** `keepout.json`, in each STL's own coordinates. Support inside a box fails the check (e.g. a duct's air channel).
- **Needs:** the PrusaSlicer flatpak (`com.prusa3d.PrusaSlicer`) and `rsvg-convert`. The flatpak can't see `/tmp`, so output stays under `$HOME`.

## Reading the support number

The number is what PrusaSlicer's **automatic** supports would add. Parts designed to print without supports (Voron,
Clicky-Clack) still show some, e.g. in nut traps and slots that their designers bridge over:

| Part (upstream, print-oriented) | Support cm³ |
|---|---|
| Voron `z_carriage_left` | 1.04 |
| Clicky-Clack `Latch` | 2.02 |
| LDO cable clip S | 0.12 |
| MadMax SpeedClip 9 mm | 0.28 |
| A4Tv2 `[t]_LED_diffuser` | 0.01 |
| A4Tv2 main body | 11.75 |

The red areas in the preview show where the support goes. So **compare a remix against its upstream original** with the
same profile; don't read the absolute number as pass or fail. E.g. for #59, slice the remixed duct next to DW-Tas's
`A4Tv2_4010_Ducts.stl`.

## Cross-checking in the GUI

To see the same slice in PrusaSlicer's GUI, use the same profile and an empty preset folder, then press Slice:

```bash
flatpak run com.prusa3d.PrusaSlicer --datadir ~/Documents/VT350/slice/gui-datadir --load "$PWD/parts/slice/petg-0.4-0.2.ini" "$PWD/<part>.stl"
```
