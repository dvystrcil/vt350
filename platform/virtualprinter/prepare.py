#!/usr/bin/env python3
"""Set up a virtual printer's data folder before supervisord starts it (vt350#224).

    prepare.py --source /src --config cad/klipper/printer.cfg --map cad/klipper/pinmap.json \\
               [--home-file REL=SRC ...] --supervisord-out <file>
    prepare.py --check --source . --config cad/klipper/printer.cfg --map cad/klipper/pinmap.json \\
               [--sensors <Kalico's klippy/extras/temperature_sensors.cfg>]     # "virtual-printer: check OK"

Run by entrypoint.sh in the virtual-printer image. --config, --map and each SRC are paths inside --source (the
printer's files, mounted read-only); nothing under --source is written. It writes:

- <data>/config/src/...      the printer's config and every file it includes, each MCU pin moved to its simulated
                             board's pin (platform/klipper/pinmap.py apply), same layout as under --source
- <data>/config/printer.cfg  [include src/<config>], then each [mcu]'s serial pointed at its simulator's pty,
                             homing_retract_dist: 0 for each simulated endstop, each probe's pin inverted so it
                             reads untriggered, and each simulated heater's verify_heater checks stretched for the
                             slow simulated clock (see top_config, verify_heaters)
- <data>/config/moonraker.conf
- <home>/<REL>               a copy of SRC for each --home-file (e.g. a save file seeded from its template)
- <run>/heaters-<mcu>.json   each heater on that board whose sensor is a thermistor on the same board, for its
                             simulator's thermal model (heatsim.py; see heater_specs)
- the supervisord config:    one simulavr per [mcu] (heatsim.py: Kalico's scripts/avrsim.py with heaters that
                             heat), klippy, Moonraker, nginx, and reset_watch.py (restarts a board's simulator when
                             klippy resets it)

Each run replaces what the last one wrote.

--check writes nothing: it fails when the virtual printer no longer covers the config (drift, e.g. printer.cfg gains a
[heater_bed] or a fan): a pin the pin map doesn't cover (or one it has that the config dropped), or a heater the
container wouldn't simulate (heater and sensor on different boards, or a sensor_type that isn't a thermistor in
--sensors or the config's own [thermistor] sections). Such a heater would read a steady idle value, and a target
on it would shut the printer down. CI runs it on the printer's config.

Generic: no printer knowledge. Plain python3, standard library only.
"""
import argparse
import json
import os
import shutil
import sys

import heatsim

# pinmap.py sits next to this file in the image, and in platform/klipper in the repo (prepare.py --check, in CI)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "klipper"))
import pinmap  # noqa: E402

KALICO = "/opt/klipper"
KLIPPY_PYTHON = "/opt/venv/bin/python"
MOONRAKER = "/opt/moonraker/moonraker/moonraker.py"
MOONRAKER_PYTHON = "/opt/moonraker-env/bin/python"
PYSIMULAVR = "/opt/virtualprinter/pysimulavr"
NGINX_CONF = "/opt/virtualprinter/nginx.conf"
RESET_WATCH = "/opt/virtualprinter/reset_watch.py"
HEATSIM = "/opt/virtualprinter/heatsim.py"
# Kalico's built-in thermistors ([thermistor <sensor_type>] sections), for the heater model's sensor curves
SENSORS_CFG = KALICO + "/klippy/extras/temperature_sensors.cfg"
FIRMWARE = "/opt/virtualprinter/firmware/klipper.elf"
# the firmware's board: simulavr.config (atmega644p at 20 MHz, 250000 baud on UART0)
MACHINE, SPEED, BAUD = "atmega644p", 20000000, 250000
MOONRAKER_PORT = 7125
# Moonraker sees requests from nginx, with the viewer's address in X-Real-IP: the host through Docker's bridge
# Sections whose option is a probe's input: a simulated input reads its pull-up (high), so each is inverted to read
# untriggered (top_config). Matched on the section name's first word ([tool_probe T0] too).
# verify_heater counts wall-clock time, and a simulated heater heats in simulated time, which simulavr runs 10 to 25
# times slower (heatsim.py). Its checks on each simulated heater are stretched by this much (see verify_heaters).
VERIFY_STRETCH = 30
PROBE_PINS = {"probe": "pin", "tools_calibrate": "pin", "tool_probe": "pin"}
TRUSTED = ["127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "FE80::/10", "::1/128"]


def _inside(root, rel, what):
    path = os.path.normpath(os.path.join(root, rel))
    if os.path.isabs(rel) or not (path == root or path.startswith(root.rstrip(os.sep) + os.sep)):
        raise ValueError(f"{what} {rel!r}: must be relative and stay inside {root}")
    return path


def section(mcu):
    return "mcu" if mcu == "mcu" else f"mcu {mcu}"


def endstop_sections(cfg, mcus):
    """Sections whose endstop_pin is an input on a simulated MCU (not a probe's virtual endstop)."""
    out = []
    for name, opts in cfg.sections.items():
        if opts.get("endstop_pin") and pinmap.split_pin(opts["endstop_pin"])[1] in mcus:
            out.append(name)
    return sorted(out)


def invert_pin(desc):
    """'^PC2' -> '^!PC2' and back: the pull-up kept, the inversion flipped (Klipper reads ^/~ before !)."""
    mods, chip, pin = pinmap.split_pin(desc)
    pull = "".join(c for c in mods if c in "^~")
    bang = "" if mods.count("!") % 2 else "!"
    return f"{pull}{bang}{chip + ':' if chip != 'mcu' or ':' in desc else ''}{pin}"


def probe_pins(cfg, mcus):
    """[(section, option, inverted value)] for each probe input on a simulated MCU, from the pin-mapped config."""
    out = []
    for name, opts in cfg.sections.items():
        option = PROBE_PINS.get(name.split()[0].lower())
        value = opts.get(option) if option else None
        if value and pinmap.split_pin(value)[1] in mcus:
            out.append((name, option, invert_pin(value)))
    return sorted(out)


def _sim_pin(pin):
    """'PC3' -> 'C3': simulavr names a pin by port letter and bit."""
    return pin[1:] if pin.upper().startswith("P") else pin


def thermistors(*cfgs):
    """{sensor_type: Kalico's Thermistor parameters} from each config's [thermistor <name>] sections; later win."""
    out = {}
    for cfg in cfgs:
        for name, opts in cfg.sections.items():
            kind, _, sensor = name.partition(" ")
            if kind.lower() != "thermistor" or not sensor.strip():
                continue
            try:
                p = {"t1": float(opts["temperature1"]), "r1": float(opts["resistance1"])}
                if "beta" in opts:
                    p["beta"] = float(opts["beta"])
                else:
                    for i in ("2", "3"):
                        p["t" + i] = float(opts["temperature" + i])
                        p["r" + i] = float(opts["resistance" + i])
            except (KeyError, ValueError):
                continue
            out[sensor.strip()] = p
    return out


def heater_specs(cfg, mcus, sensors):
    """({mcu: [heater spec for heatsim.py]}, [skipped heaters and why]) from the pin-mapped config.

    A heater is simulated when its heater_pin and sensor_pin are on the same simulated board and its sensor_type is
    a thermistor (in `sensors`, from thermistors()). Any other heater keeps the idle reading."""
    out, skipped = {}, []
    for name, opts in sorted(cfg.sections.items()):
        if not (opts.get("heater_pin") and opts.get("sensor_pin")):
            continue
        hmods, hchip, hpin = pinmap.split_pin(opts["heater_pin"])
        _, schip, spin = pinmap.split_pin(opts["sensor_pin"])
        sensor = opts.get("sensor_type", "").strip()
        if hchip not in mcus or schip != hchip:
            skipped.append(f"[{name}]: heater and sensor not on one simulated board")
            continue
        if sensor not in sensors:
            skipped.append(f"[{name}]: sensor_type {sensor!r} is not a thermistor")
            continue
        try:
            pullup = float(opts.get("pullup_resistor", 4700.0))
            inline = float(opts.get("inline_resistor", 0.0))
        except ValueError:
            skipped.append(f"[{name}]: pullup_resistor or inline_resistor is not a number")
            continue
        spec = {"name": name, "heater_pin": _sim_pin(hpin), "inverted": hmods.count("!") % 2 == 1,
                "sensor_pin": _sim_pin(spin), "pullup": pullup, "inline": inline, "thermistor": sensors[sensor]}
        spec.update(heatsim.KINDS[heatsim.kind_of(name)])
        out.setdefault(hchip, []).append(spec)
    return out, skipped


def check(source, config, pin_map, sensors_cfg=SENSORS_CFG):
    """(problems, simulated heaters) for the config: problems is [] when the pin map covers every MCU pin, exactly,
    and every heater would be simulated (see heater_specs). Writes nothing."""
    source = os.path.abspath(source)
    loaded = pinmap.load(_inside(source, config, "--config"))
    problems = [f"pin map: {p}" for p in pinmap.check(pinmap.pin_uses(loaded), load_map(_inside(source, pin_map, "--map")))]
    if not os.path.exists(sensors_cfg):
        raise ValueError(f"no thermistor list at {sensors_cfg} (Kalico's klippy/extras/temperature_sensors.cfg; "
                         "pass --sensors)")
    specs, skipped = heater_specs(loaded, pinmap.mcu_names(loaded), thermistors(pinmap.load(sensors_cfg), loaded))
    problems += [f"heater not simulated: {why}" for why in skipped]
    return problems, sorted(h["name"] for v in specs.values() for h in v)


def verify_heaters(cfg, names):
    """[(heater, check_gain_time, max_error)]: each simulated heater's verify_heater checks, from the printer's
    [verify_heater <heater>] or Kalico's defaults (20 s for an extruder, else 60 s; 120), times VERIFY_STRETCH."""
    out = []
    for name in sorted(names):
        opts = cfg.sections.get(f"verify_heater {name}", {})
        gain = float(opts.get("check_gain_time", 20.0 if name.startswith("extruder") else 60.0))
        error = float(opts.get("max_error", 120.0))
        out.append((name, gain * VERIFY_STRETCH, error * VERIFY_STRETCH))
    return out


def top_config(include, mcus, run, endstops=(), probes=(), verify=()):
    lines = ["# Generated by platform/virtualprinter/prepare.py at container start; each run replaces it.",
             "# The printer's own config, its MCU pins moved to the simulated boards' (platform/klipper/pinmap.py):",
             f"[include {include}]", "",
             "# Each MCU is a simulavr board: its serial is that simulator's pty. A pty has no DTR line to reset a",
             "# board with, so each is reset by command, and reset_watch.py then restarts its simulator (simulavr has",
             "# no watchdog to reboot it).", ""]
    for mcu in sorted(mcus):
        lines += [f"[{section(mcu)}]", f"serial: {os.path.join(run, mcu + '.tty')}", f"baud: {BAUD}",
                  "restart_method: command", ""]
    if endstops:
        lines += ["# A simulated endstop input reads its pull-up, so it is triggered from the start and a homing retract",
                  "# never clears it (\"Endstop x still triggered after retract\"). With no retract, homing ends at once,",
                  "# at position_endstop (as mainsail-crew/virtual-klipper-printer's configs do).", ""]
        for name in endstops:
            lines += [f"[{name}]", "homing_retract_dist: 0", ""]
    if probes:
        lines += ["# A simulated probe input reads its pull-up too, so a probe would read triggered from the start",
                  "# (\"Probe triggered prior to movement\"). Inverted, it reads untriggered: each probing move runs its",
                  "# full distance, as in batch mode (platform/kalisim). The printer's own config is unchanged.", ""]
        for name, option, value in probes:
            lines += [f"[{name}]", f"{option}: {value}", ""]
    if verify:
        lines += ["# A simulated heater heats in simulated time (heatsim.py), 10 to 25 times slower than the wall clock",
                  f"# verify_heater counts in, so its checks are {VERIFY_STRETCH} times longer here. It still shuts down a",
                  "# heater that doesn't heat, only later.", ""]
        for name, gain, error in verify:
            lines += [f"[verify_heater {name}]", f"check_gain_time: {gain:g}", f"max_error: {error:g}", ""]
    return "\n".join(lines)


def moonraker_conf(data, run):
    trusted = "\n".join("  " + t for t in TRUSTED)
    return f"""# Generated by platform/virtualprinter/prepare.py at container start.
[server]
host: 127.0.0.1
port: {MOONRAKER_PORT}
klippy_uds_address: {os.path.join(data, "comms", "klippy.sock")}

[authorization]
trusted_clients:
{trusted}
cors_domains:
  *://localhost
  *://localhost:*
  *://127.0.0.1
  *://127.0.0.1:*

[machine]
provider: supervisord_cli
supervisord_config_path: {os.path.join(run, "supervisord.conf")}
validate_service: False
validate_config: False

[file_manager]
enable_object_processing: False

[history]
"""


def supervisord_conf(mcus, data, run, firmware):
    def program(name, command, env=None):
        out = [f"[program:{name}]", f"command={command}", "autostart=true", "autorestart=true",
               "startsecs=2", "redirect_stderr=true", "stdout_logfile=/dev/stdout", "stdout_logfile_maxbytes=0"]
        if env:
            out.append("environment=" + ",".join(f'{k}="{v}"' for k, v in env.items()))
        return out + [""]

    cfg = os.path.join(data, "config", "printer.cfg")
    lines = ["; Generated by platform/virtualprinter/prepare.py at container start.",
             "[supervisord]", "nodaemon=true", "logfile=/dev/null", "logfile_maxbytes=0",
             f"pidfile={os.path.join(run, 'supervisord.pid')}", "",
             "[unix_http_server]", f"file={os.path.join(run, 'supervisor.sock')}", "",
             "[rpcinterface:supervisor]",
             "supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface", "",
             "[supervisorctl]", f"serverurl=unix://{os.path.join(run, 'supervisor.sock')}", ""]
    for mcu in sorted(mcus):
        lines += program(
            f"simulavr-{mcu}",
            f"{KLIPPY_PYTHON} {HEATSIM} --heaters {os.path.join(run, 'heaters-' + mcu + '.json')} "
            f"-m {MACHINE} -s {SPEED} -b {BAUD} -p {os.path.join(run, mcu + '.tty')} {firmware}",
            {"PYTHONPATH": PYSIMULAVR})
    lines += program("klippy", f"{KLIPPY_PYTHON} {KALICO}/klippy/klippy.py {cfg} "
                     f"-l {os.path.join(data, 'logs', 'klippy.log')} -a {os.path.join(data, 'comms', 'klippy.sock')}")
    lines += program("moonraker", f"{MOONRAKER_PYTHON} {MOONRAKER} -d {data} "
                     f"-c {os.path.join(data, 'config', 'moonraker.conf')} "
                     f"-l {os.path.join(data, 'logs', 'moonraker.log')}")
    lines += program("reset-watch", f"python3 {RESET_WATCH} {os.path.join(data, 'logs', 'klippy.log')} "
                     f"{os.path.join(run, 'supervisord.conf')}")
    lines += program("nginx", f"nginx -e stderr -c {NGINX_CONF} -g 'daemon off;'")
    return "\n".join(lines)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def prepare(source, config, pin_map, data, run, home, home_files, firmware=FIRMWARE, sensors_cfg=SENSORS_CFG):
    """Write the virtual printer's configs; returns {"config": top config, "supervisord": its config}."""
    source = os.path.abspath(source)
    config_src = _inside(source, config, "--config")
    map_src = _inside(source, pin_map, "--map")
    seeds = {_inside(home, rel, "--home-file"): _inside(source, src, "--home-file source")
             for rel, src in home_files.items()}
    cfg = load_map(map_src)
    problems = pinmap.check(pinmap.pin_uses(pinmap.load(config_src)), cfg)
    if problems:
        raise ValueError("the pin map doesn't match the config: " + "; ".join(problems))
    loaded = pinmap.load(config_src)
    mcus = pinmap.mcu_names(loaded)

    for d in ("config", "logs", "gcodes", "comms", "database"):
        os.makedirs(os.path.join(data, d), exist_ok=True)
    os.makedirs(run, exist_ok=True)
    tree = os.path.join(data, "config", "src")
    shutil.rmtree(tree, ignore_errors=True)
    top, _ = pinmap.apply(config_src, cfg, tree)
    mapped = pinmap.load(top)
    builtin = [pinmap.load(sensors_cfg)] if os.path.exists(sensors_cfg) else []
    specs, skipped = heater_specs(mapped, mcus, thermistors(*builtin, mapped))
    simulated = [h["name"] for v in specs.values() for h in v]
    top_cfg = os.path.join(data, "config", "printer.cfg")
    _write(top_cfg, top_config(os.path.relpath(top, os.path.dirname(top_cfg)), mcus, run,
                                endstop_sections(loaded, mcus), probe_pins(mapped, mcus),
                                verify_heaters(mapped, simulated)))
    _write(os.path.join(data, "config", "moonraker.conf"), moonraker_conf(data, run))
    for mcu in sorted(mcus):
        _write(os.path.join(run, f"heaters-{mcu}.json"), json.dumps(specs.get(mcu, []), indent=1) + "\n")
    for dst, src in seeds.items():
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    sup = os.path.join(run, "supervisord.conf")
    _write(sup, supervisord_conf(mcus, data, run, firmware))
    return {"config": top_cfg, "supervisord": sup, "heaters": sorted(simulated),
            "unheated": skipped}


def load_map(path):
    with open(path) as f:
        return json.load(f)


def main(argv):
    ap = argparse.ArgumentParser(prog="prepare", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--source", required=True, help="the printer's files (read-only)")
    ap.add_argument("--config", required=True, help="the top config, relative to --source")
    ap.add_argument("--map", required=True, help="the pin map, relative to --source")
    ap.add_argument("--home-file", action="append", default=[], metavar="REL=SRC",
                    help="copy SRC (relative to --source) to REL in the home folder, e.g.\n"
                         "printer_data/config/offset_save_file.cfg=cad/klipper/madmax/offset_save_file.cfg")
    ap.add_argument("--data", default=os.environ.get("VP_DATA", "/opt/printer_data"))
    ap.add_argument("--run", default=os.environ.get("VP_RUN", "/tmp/virtualprinter"))
    ap.add_argument("--home", default=os.path.expanduser("~"))
    ap.add_argument("--check", action="store_true", help="write nothing; fail if the virtual printer doesn't cover "
                    "the config (pins, heaters)")
    ap.add_argument("--sensors", default=SENSORS_CFG, help="--check: Kalico's temperature_sensors.cfg")
    a = ap.parse_args(argv)
    if a.check:
        problems, heaters = check(a.source, a.config, a.map, a.sensors)
        for p in problems:
            print(f"virtual-printer: {p}")
        if problems:
            print(f"virtual-printer: fix the config, or regenerate the map: python3 platform/klipper/pinmap.py "
                  f"generate --config {a.config} --map {a.map}")
            print("virtual-printer: check FAILED")
            return 1
        print(f"virtual-printer: simulated heaters: {', '.join(heaters) or 'none'}")
        print("virtual-printer: check OK")
        return 0
    home_files = {}
    for h in a.home_file:
        rel, sep, src = h.partition("=")
        if not sep:
            ap.error(f"--home-file {h!r}: expected REL=SRC")
        home_files[rel] = src
    out = prepare(a.source, a.config, a.map, a.data, a.run, a.home, home_files)
    print(f"virtual-printer: config {out['config']}")
    print(f"virtual-printer: simulated heaters: {', '.join(out['heaters']) or 'none'}")
    for why in out["unheated"]:
        print(f"virtual-printer: not simulated (reads a steady idle value): {why}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ValueError as e:
        print(f"virtual-printer: {e}")
        sys.exit(1)
