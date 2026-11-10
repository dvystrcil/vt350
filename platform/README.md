# platform/: the generic tools

These are the tools the VT350 uses that would work unchanged for another printer, given that printer's data. They
check the CAD, render it, simulate the firmware, and check the parts and pages. The VT350's own data, config, passes
and studies stay in `cad/`, `parts/` and `notes/`. The split, and the rule for placing a new file, are in
[#122](https://github.com/dvystrcil/vt350/issues/122).

A file belongs here if it would work unchanged for another printer. A file that holds this printer's data, config
or document content stays outside `platform/`. Code here may read the printer's data, but it never imports printer
code. The printer side imports from here, not the other way round.

## What's here

| Folder | What it does | Runs with |
|---|---|---|
| `freecad/` | The pass library (`litelib.py`: parts plus named checks, run on workers by `litepool.py`), clash checks (`clashlib.py`), boolean contact (`contact.py`), the per-part box index (`part_index.py`), mesh registration (`reglib.py`, `register.py`), Bézier paths (`bezier.py`), FCStd inspectors (`analyze.py`, `cats.py`, `tree.py`), and the motion player's core (`timeline.py`: a kalisim timeline + a rig file → frames of group translations, with the dock handover) | FreeCAD `freecadcmd`; the `test_*.py` files without `import FreeCAD` run in plain `python3` |
| `render/` | FreeCAD mesh export (`export_meshes.py`), Blender render (`render.py`), the colour-map engine (`colours.py`) and logo split (`logos.py`) | FreeCAD, then Blender |
| `kalisim/` | Kalico batch mode with no hardware: run G-code through the real firmware and check the moves. The image includes klipper-toolchanger (pinned), for printers whose config uses it | `docker` (Kalico's published image, pinned by digest) |
| `parts/` | `check-printed.py` (printed parts against their manifest and the BOM) and `slice-check.py` (supports and keep-outs, via PrusaSlicer) | `python3`; slice-check also needs PrusaSlicer |
| `klipper/` | The web front end's client config, Fluidd or Mainsail, vendored unchanged; `frontend.py` reports which one a printer's config includes and switches it | `python3` |
| `pages/` | `check_index.py`: the guard that runs before the reference pages are published | `python3` |
| `testing/` | `check_test_tmp.sh`: every plain-python test must leave its `TMPDIR` empty | `bash` |

## Running them by hand

Every tool runs without Claude and without the cluster. Run these from the repo root:

```bash
APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage

python3 platform/parts/check-printed.py                         # "check-printed: OK"
python3 platform/parts/slice-check.py parts/printed/vt350/<part>/*.stl
python3 platform/pages/check_index.py notes/reference           # "check-index: OK"
bash platform/testing/check_test_tmp.sh                         # "check-test-tmp: OK"
bash cad/klipper/test_in_container.sh                           # builds platform/kalisim with the VT350's MCU configs; "kalico-batch: OK"
cad/render/render_full.sh 30                                    # FreeCAD export + Blender render of vt350-lite-30
$APP freecadcmd $PWD/platform/freecad/part_index.py             # the per-part box index ($VT350_INDEX_MODELS)
```

The full list, with the VT350-side commands, is in [`notes/scripts.md`](../notes/scripts.md).

## Where the printer's data comes in

The printer passes its data to these tools by path or environment variable:

| Tool | The printer's data | Default |
|---|---|---|
| `render/colours.py` | the colour map | `$VT350_COLOURS`, else a `colours.json` beside `colours.py`, else `cad/render/colours.json` |
| `freecad/timeline.py` | the rig: XY mapping, bed Z, each head's dock and pickup offset | `--rig` (the VT350's: `cad/motion/rig.json`) |
| `klipper/frontend.py` | the config that includes the front end | `--config` (the VT350's: `cad/klipper/frontend.cfg`) |
| `kalisim/Dockerfile` | the MCU Kconfig fragments | the `kconfig` build context: `docker build --build-context kconfig=cad/klipper/kconfig platform/kalisim` |
| `parts/check-printed.py` | the manifest and BOM | `--root` (default: this checkout), reads `parts/printed/manifest.csv` and `bom/printed-parts.md` |
| `parts/slice-check.py` | the slicer profile and keep-out boxes | `parts/slice/petg-0.4-0.2.ini`, `parts/slice/keepout.json` (`--profile`, `--keepout`) |
| `pages/check_index.py` | the pages folder | its argument (default `notes/reference`) |

## Still VT350-specific (phase 3 of #122)

Moving the code here didn't make it generic yet. These VT350 assumptions are still in it:

- `freecad/litelib.py` holds VT350 constants (`BED_LOWEST_DZ`, `BED_FLOOR_DZ`, `BED_Z`), the default model and work
  paths, and `print_area()`, which reads the VT350's `cad/studies/print_area.py` and sweep log.
- `freecad/contact.py` has the VT350's floor margin (`FLOOR_MARGIN`). `freecad/part_index.py` has the VT350's model
  folder (`MODELS_DIR`) and a `vt350-` format name, and every tool reads `VT350_*` environment variables.
- `parts/check-printed.py` names this repository (`THIS_REPO`) and its licence.
- The default paths in the tables above are the VT350's folders.

Phase 3 replaces these with one printer description file that each tool reads.
