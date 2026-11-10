# cad/klipper: the firmware config, checked against the CAD in Kalico batch mode

The firmware is [Kalico](https://github.com/KalicoCrew/kalico) (user, 2026-11-09). `printer.cfg` holds the values the CAD model decides, plus the minimum Kalico needs to load it. Kalico's **batch mode** runs the config and G-code on the host with no hardware (`klippy -i in.gcode -o out.serial -d <dict>`; Kalico `docs/Debugging.md`). The tests here use it to check that the config allows exactly the CAD envelope and refuses anything past it ([#116](https://github.com/dvystrcil/vt350/issues/116)).

| File | What it is |
|---|---|
| `printer.cfg` | The Kalico config: corexy, steppers, three Z, limits, the Octopus Pro and both O2S toolboards. `PLACEHOLDER` marks values nobody has decided yet |
| `xy_mapping.json` | Model → printer XY: origin and axis directions. **Proposed** in [#116](https://github.com/dvystrcil/vt350/issues/116), not confirmed |
| `frontend.cfg` | The web front end: **Fluidd** (owner, 2026-11-10). One include of a vendored client config in `platform/klipper/frontends/`; `python3 platform/klipper/frontend.py --config cad/klipper/frontend.cfg --use mainsail` switches it |
| `toolchanger.cfg` | The tool changer: includes MadMax's macros (`madmax/`, unchanged) and sets the VT350's dock positions and two `[tool]`s. Included by `printer.cfg` |
| `madmax/` | MadMax's `toolchanger.cfg` and `toolchanger_macros.cfg`, vendored unchanged from `zruncho3d/madmax@277a63c` (GPL-3.0) |
| `dock_params.py` | VT350-specific. Derives every `params_*` in `toolchanger.cfg` from the CAD dock poses and checks the file against them |
| `toolchange.gcode` | Picks up and docks each head: `T0`, `T1`, `UNSELECT_TOOL` |
| `toolchange_timeline.jsonl` | Generated. Every move Kalico planned for `toolchange.gcode`, one JSON line each (the input for #116 AC5) |
| `test_dock_params.py` | `toolchanger.cfg` against the CAD, and the vendored macros against upstream's git blobs. Plain python3 |
| `limits.py` | VT350-specific. Derives each limit from the committed CAD logs, checks `printer.cfg` against them, and writes `envelope.gcode` |
| `envelope.gcode` | Generated. Walks the envelope: the four corners at Z 0 and at the Z floor, then the negative Z `position_min`, then one step past each limit |
| `kalisim/` | The generic core. Runs Kalico batch mode and returns a timeline of planned moves. No FreeCAD, no VT350 knowledge. GPL-3.0 |
| `test_limits.py` | `printer.cfg` against the logs, plus the envelope generator. Plain python3 |
| `test_kalico_batch.py` | Real Kalico, in the container: the pinned commit, one dictionary per MCU, the envelope walk, and the tool changes |

## Where each limit comes from

`printer.cfg` names the source above every limit, and `test_limits.py` recomputes each one from that log:

| Axis | min | max | Source (in `cad/data/logs/`) |
|---|---|---|---|
| X | 4.00 | 346.00 | `sweep_toolhead.log`: "first nozzle X with no new overlap" −416.0 / −74.0, both heads |
| Y | −82.43 | 340.19 | `sweep_toolhead.log`: "nozzle Y reach −51.93 .. 370.69", both heads |
| Z | −15 | 330.33 | min: not a CAD limit (see below); max: `z_sweep.log` `klipper_position_max_configured_mm` |

X and Y are mapped by the proposed `xy_mapping.json`: origin at the print square's front-left corner, model (−420.0, 30.5); X+ = model +X, Y+ = model +Y. With that mapping the CAD gives a 342 × 422.6 mm XY box, so it is **not** the 350 mm square. The nozzle stops 4 mm short of each X edge of the print square and 9.81 mm short of its rear edge (Y 340.19 of 350), while Y below 0 reaches the docks.

**Z `position_min` is the one limit not taken from a CAD log.** Z0 comes from the Beacon nozzle tap (`z_sweep.log`: the nozzle on the magnet sheet) and shifts by fractions of a mm per nozzle. `position_min` only sets how far below Z0 Kalico accepts a command, so per-tool Z offsets and calibration moves aren't refused. −15 matches the AC4 macro source, MadMax `r2pdx_config-v2-Kalico-Beacon` at `zruncho3d/madmax@277a63c` ([vt350#116](https://github.com/dvystrcil/vt350/issues/116)). `limits.py` only requires it to be at or below the CAD floor of 0.

When a CAD log changes, run `python3 cad/klipper/limits.py --check`. If it fails, update `printer.cfg` and regenerate the G-code with `python3 cad/klipper/limits.py --gcode > cad/klipper/envelope.gcode`.

## The web front end

**Fluidd** (owner, 2026-11-10). Mainsail is the other supported choice. Both are Moonraker clients, and each ships a client config with the same sections (`[virtual_sdcard]` with path `~/printer_data/gcodes`, `[pause_resume]`, `[display_status]`, `[respond]`) and the same `PAUSE` / `RESUME` / `CANCEL_PRINT` macros. Both are vendored unchanged in `platform/klipper/frontends/<name>/client.cfg`, pinned by commit and checked by git blob id. `frontend.cfg` includes exactly one of them. To switch, run:

```sh
python3 platform/klipper/frontend.py --config cad/klipper/frontend.cfg --use mainsail   # or --use fluidd
```

`test_kalico_batch.py` runs the tool changes under each front end and checks that they give the same timeline. On the Pi, the usual install (`ln -sf ~/fluidd-config/fluidd.cfg ~/printer_data/config/fluidd.cfg`, then `[include fluidd.cfg]`) gives the same file. How this repo's config reaches the Pi isn't decided yet.

## The tool changes (#116 AC4)

The macros are MadMax's `r2pdx_config-v2-Kalico-Beacon-2025-07-05` at `zruncho3d/madmax@277a63c` (owner's choice, #116), on `viesturz/klipper-toolchanger@94756df`. Both are GPL-3.0. The kalisim image copies klipper-toolchanger's `toolchanger`, `tool`, `tool_probe` and `tool_probe_endstop` modules into Kalico's `klippy/extras/`. Its `tools_calibrate.py` is left out, so Kalico keeps its own.

MadMax's dock path, with the VT350's values (printer coordinates, PROPOSED mapping):

| Param | VT350 | From |
|---|---|---|
| `[tool T0] params_park_x` / `params_detach_x` | 21.00 / 26.00 | `sweep_toolhead.log` "Left: docked nozzle tip (−399.00, …)"; detach 5 mm (MadMax) away from the keyslot plate, which is on the left head's −X side |
| `[tool T1] params_park_x` / `params_detach_x` | 328.00 / 323.00 | "Right: docked nozzle tip (−92.00, …)"; the mirror image, so detach goes −X |
| `params_attach_y` | −68.96 | docked nozzle Y −32.46, minus the 6.0 mm keyslot slide to the large opening (`sweep_toolhead.log`) |
| `params_close_y` | −46.96 | MadMax's distance from its parked Y (+16), kept |
| `params_safe_shuttle_y` | −26.96 | MadMax's distance (+36). **Unchecked:** set for MadMax's heads; #116 AC5 clash-checks it |
| `params_safe_toolhead_y` | 48.04 | MadMax's distance (+111). **Unchecked**, as above |

Pickup runs `safe_shuttle_y` (at the current X) → `park_x` → `close_y` → `attach_y` (path speed) → `detach_x` (path speed) → `safe_toolhead_y` → back to where the change started. Dropoff runs `detach_x, safe_toolhead_y` → `attach_y` → `park_x` (path speed) → `close_y` (path speed) → `safe_shuttle_y`.

What batch mode shows about the macros on this config:
- **Two unknown commands**, which Kalico reports and skips: `SET_INPUT_SHAPER` (MadMax's `after_change_gcode`; needs an `[input_shaper]`) and `STOP_TOOL_PROBE_CRASH_DETECTION` (MadMax's `dropoff_gcode`; only `[tool_probe_endstop]` registers it, and MadMax's own Beacon config leaves that out too). The test fails if another one appears.
- **The empty carriage goes below Y 0 away from the docks.** It travels at `safe_shuttle_y` (−26.96) along X, and after `UNSELECT_TOOL` it returns diagonally from the dock. Every other move below Y 0 is at a dock's park or detach X.
- **The timeline's `tool` is the active extruder, not what's on the carriage.** klipper-toolchanger switches the extruder before the pickup moves, so the empty carriage's approach to a dock is already labelled with the new tool.
- **No tool detection yet.** MadMax starts by reading a `[gcode_button tool<n>_detect]` per tool. The O2S inputs for that aren't decided, so `toolchanger.cfg` starts with no tool on the carriage, as in the model.

When a dock pose in the CAD changes, run `python3 cad/klipper/dock_params.py --check`. It names every `params_*` that no longer matches. After any change to the config or the macros, regenerate the timeline in the image:

```sh
docker build -q --build-context kconfig=cad/klipper/kconfig -t vt350-kalisim platform/kalisim
docker run --rm -v "$PWD:/repo:ro" vt350-kalisim sh -c 'cd /repo/platform && $KALISIM_PYTHON -m kalisim run \
    --config /repo/cad/klipper/printer.cfg --gcode /repo/cad/klipper/toolchange.gcode \
    -d /opt/dicts/octopus-pro-h723.dict -d o2s_left=/opt/dicts/o2s-left.dict -d o2s_right=/opt/dicts/o2s-right.dict' \
    > cad/klipper/toolchange_timeline.jsonl
```

## Running it

```sh
python3 cad/klipper/test_limits.py                 # no Docker: printer.cfg vs the CAD logs
python3 cad/klipper/test_dock_params.py            # no Docker: toolchanger.cfg vs the CAD dock poses
python3 platform/klipper/test_frontend.py          # no Docker: the front-end switch and the vendored client configs
bash cad/klipper/test_in_container.sh      # Docker: builds the image, runs the Kalico tests; "kalico-batch: OK"
```

The `kalico-batch` workflow runs both on every change to `cad/klipper/` or to the Z sweep log.

To run your own G-code through the config:

```sh
docker build -t vt350-kalisim platform/kalisim
docker run --rm -v "$PWD:/repo:ro" vt350-kalisim sh -c 'cd /repo/cad/klipper && $KALISIM_PYTHON -m kalisim run \
    --config printer.cfg --gcode envelope.gcode -d /opt/dicts/octopus-pro-h723.dict \
    -d o2s_left=/opt/dicts/o2s-left.dict -d o2s_right=/opt/dicts/o2s-right.dict'
```

This prints one JSON line per planned move (`plugins/move_timeline.py`). A move Kalico refuses ends the run.

## The image (`kalisim/Dockerfile`)

- **Runtime:** Kalico's published container, `ghcr.io/kalicocrew/kalico`, pinned by digest. Its `klippy/.version` is `v2026.11.00-30-g991e1823`.
- **Dictionaries:** the published image ships klippy only, so a first stage builds the firmware from Kalico's source at `KALICO_SHA` = `991e1823e983a31d26b9264d2b6305fd64e3a09a`, one build per `kconfig/*.config`:
  - `octopus-pro-h723`: STM32H723, 128 KiB bootloader, 25 MHz crystal, USB PA11/PA12 (Kalico's Octopus Pro v1.1 sample config).
  - `o2s-left`, `o2s-right`: STM32F072, no bootloader, 12 MHz crystal, USB PA11/PA12 (O2S User Manual v1.5 §4). USB serials are `Orbitool_O2S_L` and `Orbitool_O2S_R`. Upstream gives every board `Orbitool_O2S`, so two boards would collide in `/dev/serial/by-id`.
- **klipper-toolchanger:** the first stage fetches `viesturz/klipper-toolchanger` at `TOOLCHANGER_SHA` = `94756dfde9b729fd69f9b8780067821c5c99a528` into `/opt/toolchanger`. The runtime stage copies four of its modules into `klippy/extras/`, and fails if Kalico already has a file of that name. They go in `extras/`, not `plugins/`, because they import Kalico's `probe` relatively (`from . import probe`), which only resolves there.
- **Checks:** `build_dicts.sh` fails if Kconfig dropped any requested setting. `test_kalico_batch.py` checks that both stages are the same commit, that the installed toolchanger modules are the pinned ones, and that Kalico's own `tools_calibrate.py` is kept.
- **Flashing the real boards:** the same `kconfig/*.config` files are the `make menuconfig` answers. Batch mode can't see USB names, so check `ls /dev/serial/by-id/` once both toolboards are plugged in.

## Licence

`kalisim/` is **GPL-3.0-or-later**. `plugins/move_timeline.py` runs inside Kalico (GPL-3.0), and the core is meant to become a GPL-3.0 FreeCAD add-on (#116, "Design direction"). Every other file in this folder is GPL-3.0-or-later too, like the rest of the repo's own work. Kalico itself isn't vendored: the image fetches it.
