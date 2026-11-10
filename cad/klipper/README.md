# cad/klipper: the firmware config, checked against the CAD in Kalico batch mode

The firmware is [Kalico](https://github.com/KalicoCrew/kalico) (user, 2026-11-09). `printer.cfg` holds the values the CAD model decides, plus the minimum Kalico needs to load it. Kalico's **batch mode** runs the config and G-code on the host with no hardware (`klippy -i in.gcode -o out.serial -d <dict>`; Kalico `docs/Debugging.md`). The tests here use it to check that the config allows exactly the CAD envelope and refuses anything past it ([#116](https://github.com/dvystrcil/vt350/issues/116)).

| File | What it is |
|---|---|
| `printer.cfg` | The Kalico config: corexy, steppers, three Z, limits, the Octopus Pro and both O2S toolboards. `PLACEHOLDER` marks values nobody has decided yet |
| `xy_mapping.json` | Model → printer XY: origin and axis directions. **Proposed** in [#116](https://github.com/dvystrcil/vt350/issues/116), not confirmed |
| `limits.py` | VT350-specific. Derives each limit from the committed CAD logs, checks `printer.cfg` against them, and writes `envelope.gcode` |
| `envelope.gcode` | Generated. Walks the envelope: the four corners at Z 0 and at the Z floor, then the negative Z `position_min`, then one step past each limit |
| `kalisim/` | The generic core. Runs Kalico batch mode and returns a timeline of planned moves. No FreeCAD, no VT350 knowledge. GPL-3.0 |
| `test_limits.py` | `printer.cfg` against the logs, plus the envelope generator. Plain python3 |
| `test_kalico_batch.py` | Real Kalico, in the container: the pinned commit, one dictionary per MCU, and the envelope walk |

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

## Running it

```sh
python3 cad/klipper/test_limits.py                 # no Docker: printer.cfg vs the CAD logs
bash cad/klipper/kalisim/test_in_container.sh      # Docker: builds the image, runs the Kalico tests; "kalico-batch: OK"
```

The `kalico-batch` workflow runs both on every change to `cad/klipper/` or to the Z sweep log.

To run your own G-code through the config:

```sh
docker build -t vt350-kalisim cad/klipper/kalisim
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
- **Checks:** `build_dicts.sh` fails if Kconfig dropped any requested setting. `test_kalico_batch.py` checks that both stages are the same commit.
- **Flashing the real boards:** the same `kconfig/*.config` files are the `make menuconfig` answers. Batch mode can't see USB names, so check `ls /dev/serial/by-id/` once both toolboards are plugged in.

## Licence

`kalisim/` is **GPL-3.0-or-later**. `plugins/move_timeline.py` runs inside Kalico (GPL-3.0), and the core is meant to become a GPL-3.0 FreeCAD add-on (#116, "Design direction"). Every other file in this folder is MIT, like the rest of the repo. Kalico itself isn't vendored: the image fetches it.
