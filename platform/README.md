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
| `freecad/` | The pass library (`litelib.py`: parts plus named checks, run on workers by `litepool.py`), clash checks (`clashlib.py`), boolean contact (`contact.py`), the per-part box index (`part_index.py`), copies found and turned into App::Links (`dupes.py`) and the link-aware geometry every walker uses (`linkgeo.py`), mesh registration (`reglib.py`, `register.py`), Bézier paths (`bezier.py`), FCStd inspectors (`analyze.py`, `cats.py`, `tree.py`), the motion player's core (`timeline.py`: a kalisim timeline + a rig file → frames of group translations, with the dock handover), and its FreeCAD GUI player (`player.py`, started by `player_gui.FCMacro`: plays the frames on a private copy of the model, play/pause/step/speed, restores every Placement on stop, never saves) | FreeCAD `freecadcmd`; the `test_*.py` files without `import FreeCAD` run in plain `python3` |
| `viewer/` | Part selection and licence rules (`rules.py`), the licence check of an export (`licence_check.py`), Blender export to GLB with the renders' materials (`glb.py`), turntable cameras (`frame_view.py`), the turntable and 3D viewer pages (`turntable_page.py`, `viewer_page.py`, templates `turntable.html`, `viewer.html`; shared release-asset helpers in `pages/sitepub.py`) | python3, then Blender |
| `render/` | FreeCAD mesh export (`export_meshes.py`), Blender render (`render.py`), the colour-map engine (`colours.py`) and logo split (`logos.py`) | FreeCAD, then Blender |
| `kalisim/` | Kalico batch mode with no hardware: run G-code through the real firmware and check the moves. The image includes klipper-toolchanger (pinned), for printers whose config uses it. klippy runs with a sandbox `HOME` holding an empty `printer_data/config/`, for configs that keep a file there (`[save_variables]`); `home_files` / `--home-file REL=SRC` copies a file in first (e.g. a save file seeded from its template) | `docker` (Kalico's published image, pinned by digest) |
| `parts/` | `check-printed.py` (printed parts against their manifest and the BOM) and `slice-check.py` (supports, keep-outs and print estimates, via OrcaSlicer or `--slicer prusa`) and `orca_projects.py` (the parts as OrcaSlicer projects, one 3MF per work unit with a plate per material, from a sets file, with an index of each STL's sha256; `--check` needs no Orca) | `python3`; slice-check also needs the Orca (or PrusaSlicer) flatpak |
| `klipper/` | The web front end's client config, Fluidd or Mainsail, vendored unchanged; `frontend.py` reports which one a printer's config includes and switches it. `pinmap.py`: a config's MCU pins (with its includes) mapped onto simulated boards, one simulavr atmega644p per `[mcu]`, for a live klippy with no hardware (#224); `generate` writes the map, `check` fails when the config uses a pin the map doesn't cover ("pinmap: OK"), `apply` writes a copy of the config tree with the pins swapped | `python3` |
| `virtualprinter/` | A virtual printer (#224): an image FROM the kalisim image that runs klippy live, one simulavr atmega644p per `[mcu]` (Kalico's AVR firmware, `simulavr.config`), Moonraker and Fluidd (behind nginx) under supervisord. At start, `prepare.py` copies the printer's config with its pins moved (`klipper/pinmap.py apply`), points each `[mcu]` at its simulator, seeds `--home-file`s, and writes the Moonraker and supervisord configs; `reset_watch.py` restarts a board's simulator when klippy resets it (simulavr has no watchdog). `virtualprinter.sh build/start/status/stop`; nothing is kept when it stops. `prepare.py --check` fails when the config has a pin the map doesn't cover or a heater it wouldn't simulate. Built from pins only: apt from snapshot.debian.org at exact versions (`apt_snapshot.sh`), pip with hashes (`pip_lock.py`), simulavr by commit and tree sha256 | `docker` |
| `pages/` | `check_index.py`: the guard that runs before the reference pages are published; `fetch_assets.py`: puts the pages' large files (release assets, checked by sha256) in place; `credits.py`: a `CREDITS.md`, one row per upstream project, from `REUSE.toml`, the licence rules and a projects file (`--check` fails when it is stale) | `python3`, `gh` |
| `docs/` | `step_parts.py`: each assembly page's Print and Buy tables (the parts for that stage only), from the printed-parts manifest and the BOM, written between `<!-- step-parts:begin -->` / `<!-- step-parts:end -->` markers; `--check` fails on a stale block or a page with parts but no markers | `python3` |
| `library/` | `check_library.py`: a parts library (`<library>/<category>/<part>/<variant>/source.json` plus the files; the category must be in the schema's list and match the folder): each `source.json` against the library's `schema.json`, each committed file's sha256, no file for a no-file entry, no file without a `source.json`; with `--reuse` / `--projects` / `--manifest`, each file's REUSE label, each entry's credit and each printed part's manifest row agree (#268) | `python3` |
| `webarchive/` | `crawl.py`: offline copies of the web sites a build reads (vendor docs, shops), from a sites file: each site crawled by browsertrix-crawler (headless Chrome in docker, pinned by digest; gets past sites that refuse plain HTTP clients), kept as a WACZ archive (open in replayweb.page) plus one Markdown file of text per page, each page's images (from the WARC, listed in its `.md`) and an `INDEX.md`; refuses an `--out` inside a git checkout; `--text-only` rebuilds the text without crawling | `docker`, `python3` |
| `chain/` | `fingerprint.py`: skip a chain link whose inputs haven't changed (#324). A link declares the files it reads (globs, with basename excludes such as `test_*`) and the part indexes it looks at (each part's label and box by default, so a recolour or hide changes nothing); its fingerprint is their sha256; a JSON record keeps each link's last successful fingerprint; `decide()` says run / reused / forced (`--fresh`, and everything downstream) / always | `python3` |
| `testing/` | `check_test_tmp.sh`: every plain-python test must leave its `TMPDIR` empty | `bash` |

**What to run the tools on, and how long they take** (recommended hardware, measured run times, why memory sets the speed): [`HARDWARE.md`](HARDWARE.md).

**What we've learned about FreeCAD** (what makes a model slow to open, hidden parts, stand-ins, App::Links, and the gotchas that cost us time): [`freecad/LESSONS.md`](freecad/LESSONS.md). Add to it the day something is learned.

## Running them by hand

Every tool runs without Claude and without the cluster. Run these from the repo root:

```bash
APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage

python3 platform/parts/check-printed.py                         # "check-printed: OK"
python3 platform/parts/slice-check.py parts/printed/vt350/<part>/*.stl
python3 platform/parts/orca_projects.py parts/slice/sets.json   # regenerate stale OrcaSlicer projects; --check: "orca-projects: OK"
python3 platform/pages/check_index.py notes/reference           # "check-index: OK"
python3 platform/pages/fetch_assets.py notes/reference/assets.json   # "fetch-assets: OK"; --from-dir DIR to skip the download
python3 platform/pages/credits.py --projects cad/credits.json --reuse REUSE.toml --licences cad/viewer/licences.json --licence-dir LICENSES --out CREDITS.md   # "credits: OK"; --check in CI
python3 platform/library/check_library.py --library cad/library --reuse REUSE.toml --projects cad/credits.json --manifest parts/printed/manifest.csv   # "library-check: OK"
bash platform/testing/check_test_tmp.sh                         # "check-test-tmp: OK"
python3 platform/webarchive/crawl.py cad/data/web-sources.json --out ~/Documents/VT350/web   # offline copies of the sites; --only NAME; "webarchive: OK"
python3 platform/docs/step_parts.py                            # rewrite the Print/Buy tables in docs/assembly/stage-N-*.md; --check in CI ("step-parts: OK")
python3 platform/klipper/pinmap.py check --config cad/klipper/printer.cfg --map cad/klipper/pinmap.json   # "pinmap: OK"
bash cad/klipper/virtual-printer.sh start                      # platform/virtualprinter with the VT350's config; "virtual-printer: ready" (stop: "virtual-printer: stopped")
bash cad/klipper/test_in_container.sh                           # builds platform/kalisim with the VT350's MCU configs; "kalico-batch: OK"
cad/render/render_full.sh 30                                    # FreeCAD export + Blender render of vt350-lite-30
cad/viewer/export_glb.sh 62                                     # a licence-checked GLB of a selection, for the 3D viewer ("glb-export: OK")
python3 platform/viewer/licence_check.py <export>/scene.json <licences.json>   # "licence-check: OK"
python3 platform/viewer/turntable_page.py stage <frames> <page.json> <out>    # a turntable preview folder ("turntable-page: OK")
python3 platform/viewer/viewer_page.py stage <model> <compare.jpg> <page.json> <out>   # a 3D viewer preview ("viewer-page: OK")
cad/viewer/pages.py release <name> --model N                  # the VT350's public pages from a lite-N (notes/scripts.md)
$APP freecadcmd $PWD/platform/freecad/part_index.py             # the per-part box index ($VT350_INDEX_MODELS)
TESS_COST_MODEL=<model> $APP freecadcmd $PWD/platform/freecad/tess_cost.py   # which parts make a model slow to open (freecad/LESSONS.md)
DUPES_MODEL=<model> $APP freecadcmd $PWD/platform/freecad/dupes.py          # which parts are copies, and what linking them saves in the file
```

The full list, with the VT350-side commands, is in [`notes/scripts.md`](../notes/scripts.md).

## Settings: the values file

A script that moved its laptop-specific constant to [`freecad/batchvalues.py`](freecad/batchvalues.py) takes that
setting from, in order: its own environment variable, then the `platform` section of the JSON file named by
`GPU_BATCH_VALUES` (the same file whose `print_guard` section the gpu-batch guard reads), then today's value in the
code. With no values file, nothing changes. A missing or non-JSON file, or an unknown `platform` key, is an error.

| Key | Env var | Default | Used by |
|---|---|---|---|
| `freecad_appimage` | `FREECAD_APPIMAGE` | `/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage` | `freecad/litelib.py`, `freecad/clashlib.py` |

```json
{
  "platform": {
    "freecad_appimage": "/opt/FreeCAD/FreeCAD.AppImage"
  }
}
```

## Where the printer's data comes in

The printer passes its data to these tools by path or environment variable:

| Tool | The printer's data | Default |
|---|---|---|
| `render/colours.py` | the colour map | `$VT350_COLOURS`, else a `colours.json` beside `colours.py`, else `cad/render/colours.json` |
| `freecad/timeline.py` | the rig: XY mapping, bed Z, each head's dock and pickup offset | `--rig` (the VT350's: `cad/motion/rig.json`) |
| `freecad/player.py` | the model, the groups file ({group: [object Name]}), the timeline and the rig | `MOTION_*` environment variables (the VT350's launcher: `cad/motion/play.py`) |
| `klipper/frontend.py` | the config that includes the front end | `--config` (the VT350's: `cad/klipper/frontend.cfg`) |
| `klipper/pinmap.py` | the printer's top config, and its pin map | `--config`, `--map` (the VT350's: `cad/klipper/printer.cfg`, `cad/klipper/pinmap.json`) |
| `kalisim/Dockerfile` | the MCU Kconfig fragments | the `kconfig` build context: `docker build --build-context kconfig=cad/klipper/kconfig platform/kalisim` |
| `virtualprinter/virtualprinter.sh` | the MCU Kconfig fragments, the printer's files, its top config, pin map and seeded home files | `--kconfig`, `--source` (mounted read-only), `--config`, `--map`, `--home-file REL=SRC` (the VT350's launcher: `cad/klipper/virtual-printer.sh`) |
| `docs/step_parts.py` | the manifest, the BOM and the assembly pages | `--root` (default: this checkout), `--manifest` (`parts/printed/manifest.csv`), `--printed` (`parts/printed`), `--bom` (`bom/bom.csv`), `--pages` (`docs/assembly`) |
| `parts/check-printed.py` | the manifest and BOM | `--root` (default: this checkout), reads `parts/printed/manifest.csv` and `bom/printed-parts.md` |
| `parts/slice-check.py` | the slicer presets and keep-out boxes | `parts/slice/orca/orca.json` (the Neptune presets), `parts/slice/petg-0.4-0.2.ini` (`--slicer prusa`), `parts/slice/keepout.json` (`--orca`, `--profile`, `--keepout`) |
| `pages/check_index.py` | the pages folder | its argument (default `notes/reference`) |
| `pages/fetch_assets.py` | the manifest of release assets | its argument; `--repo` or `GITHUB_REPOSITORY` |
| `library/check_library.py` | the library folder (with its `schema.json`), REUSE.toml, the projects file | `--library`, `--schema`, `--reuse`, `--projects`, `--manifest` (the VT350's: `cad/library`, `cad/library/schema.json`, `REUSE.toml`, `cad/credits.json`, `parts/printed/manifest.csv`) |
| `pages/credits.py` | the projects file, REUSE.toml, the licence rules, the licence texts | `--projects`, `--reuse`, `--licences`, `--licence-dir`, `--out` (the VT350's: `cad/credits.json`, `REUSE.toml`, `cad/viewer/licences.json`, `LICENSES`, `CREDITS.md`) |

## Still VT350-specific (phase 3 of #122)

Moving the code here didn't make it generic yet. These VT350 assumptions are still in it:

- `freecad/litelib.py` holds VT350 constants (`BED_LOWEST_DZ`, `BED_FLOOR_DZ`, `BED_Z`), the default model and work
  paths, and `print_area()`, which reads the VT350's `cad/studies/print_area.py` and sweep log.
- `freecad/contact.py` has the VT350's floor margin (`FLOOR_MARGIN`). `freecad/part_index.py` has the VT350's model
  folder (`MODELS_DIR`) and a `vt350-` format name.
- Tools read their inputs from 16 `VT350_*` environment variables: `VT350_BLENDER`, `VT350_COLOURS`, `VT350_DOCS`,
  `VT350_EXTRA`, `VT350_GROUPS`, `VT350_HEAVY_FACES`, `VT350_INDEX_FORCE`, `VT350_INDEX_MODELS`, `VT350_MODEL`,
  `VT350_RENDER_OUT`, `VT350_REPO`, `VT350_RESERVE_MB`, `VT350_WORK`, `VT350_WORKER_DOC_MB`, `VT350_WORKER_MB`,
  `VT350_WORKERS`. **The rule for these (agreed 2026-11-16):** a platform input has a neutral name that says what
  it is (a model path, an output folder, a colour map), and the printer passes its own values in. The printer's
  names stay on the printer's side: its launchers, passes and values. New inputs follow the rule from the start
  (`RENDER_STANDINS`, `FREECAD_APPIMAGE`, `PASS_GUI_NOTICE`); these 16 get renamed with #125 and the values-file moves, not piecemeal.
- **A GUI pass shows its outcome** (`freecad/outcome.py`, vt350#280). When `litelib.Pass` ends a GUI run, it shows
  SAVED (each file and its size) or NOT SAVED (the first 5 failed checks) in a message box and the Report view, with
  the log's path. The box waits for a click. For an unattended GUI run (an agent, a script) set
  `PASS_GUI_NOTICE=report` (Report view only) or `none` (the log only). Headless runs are unchanged. The log's lines
  are the same as before.
- `parts/check-printed.py` names this repository (`THIS_REPO`) and its licence.
- The default paths in the tables above are the VT350's folders.

Phase 3 replaces these with one printer description file that each tool reads.
