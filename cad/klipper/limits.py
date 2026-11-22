#!/usr/bin/env python3
"""The VT350's axis limits: from the committed CAD logs, in the config, and the G-code that walks them (vt350#116).

    python3 cad/klipper/limits.py --check     # the config's limits == the ones the CAD logs give; "limits: OK"
    python3 cad/klipper/limits.py --cfg       # print cad_values.cfg (committed as cad/klipper/cad_values.cfg, #294)
    python3 cad/klipper/limits.py --gcode     # print the envelope G-code (committed as cad/klipper/envelope.gcode)

The config is printer.cfg with everything it includes (platform/klipper/pinmap.py's loader: later files win, as in
Kalico). The limits themselves live in the generated cad_values.cfg.

The CAD limits:
  X  sweep_toolhead.log "<head> head, left/right side: first nozzle X with no new overlap <x>", both heads (tighter)
  Y  sweep_toolhead.log "<head> carried: ... nozzle Y reach <min> .. <max>", both heads (tighter)
  Z  min 0 (Z0 = the nozzle on the magnet sheet, z_sweep.log); max = the last klipper_position_max_configured_mm
     in z_sweep.log
mapped from model to printer XY by xy_mapping.json: printer = sign * (model - origin).

This file is VT350-specific. The generic batch-mode runner is platform/kalisim/ (no FreeCAD, no VT350 knowledge).
Plain python3, standard library only.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "platform", "klipper"))
import pinmap  # noqa: E402  (the generic include-following config loader)
LOGS = os.path.join(ROOT, "cad", "data", "logs")
AXES = ("x", "y", "z")
DECIMALS = 4  # G-code coordinates in the envelope file


def parse_cfg(text):
    """A Klipper/Kalico config as {section: {option: value}}: comments dropped, indented lines (multi-line values
    such as a macro's gcode) skipped."""
    out, sec = {}, None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip()[0] in "#;":
            continue
        if raw[0] in " \t":
            continue
        line = re.split(r"\s[#;]", raw, maxsplit=1)[0].strip()
        m = re.fullmatch(r"\[([^\]]+)\]", line)
        if m:
            sec = m.group(1).strip()
            out.setdefault(sec, {})
            continue
        if sec is None:
            raise ValueError(f"option outside a section: {raw!r}")
        key, value = re.split(r"\s*[:=]\s*", line, maxsplit=1)
        out[sec][key.strip()] = value.strip()
    return out


def load_cfg(path=os.path.join(HERE, "printer.cfg")):
    """printer.cfg and everything it includes, as {section: {option: value}} (later files win, as in Kalico)."""
    return pinmap.load(path).sections


def cfg_limits(cfg):
    """{"x": (position_min, position_max), ...} from [stepper_x/y/z]; position_min defaults to 0 as in Kalico."""
    return {a: (float(cfg[f"stepper_{a}"].get("position_min", 0)), float(cfg[f"stepper_{a}"]["position_max"]))
            for a in AXES}


def step_distance(cfg, axis):
    """One full-resolution step of the axis's stepper, in mm."""
    s = cfg[f"stepper_{axis}"]
    return float(s["rotation_distance"]) / (int(s.get("full_steps_per_rotation", 200)) * int(s["microsteps"]))


def load_mapping(path=os.path.join(HERE, "xy_mapping.json")):
    with open(path) as f:
        return json.load(f)


def _to_printer(lo, hi, i, mapping):
    o, s = mapping["origin_model_xy"][i], mapping["sign_xy"][i]
    a, b = (round(s * (v - o), 6) for v in (lo, hi))
    return (min(a, b), max(a, b))


def _intersect(ranges):
    return (max(r[0] for r in ranges), min(r[1] for r in ranges))


def cad_limits(sweep_log, z_log, mapping):
    """The limits the CAD logs give, in printer coordinates."""
    xs = {}
    for head, side, v in re.findall(r"(\w+) head, (left|right) side: first nozzle X with no new overlap (-?[0-9.]+)",
                                    sweep_log):
        xs.setdefault(head, {})[side] = float(v)
    if not xs or any(set(d) != {"left", "right"} for d in xs.values()):
        raise ValueError(f"sweep_toolhead log: X scan lines missing (need left and right side per head): {xs}")
    ys = re.findall(r"(\w+) carried: .*?nozzle Y reach (-?[0-9.]+) \.\. (-?[0-9.]+)", sweep_log)
    if not ys:
        raise ValueError("sweep_toolhead log: no 'nozzle Y reach' line")
    zmax = re.findall(r"klipper_position_max_configured_mm=([0-9.]+)", z_log)
    if not zmax:
        raise ValueError("z_sweep log: no klipper_position_max_configured_mm line")
    return {"x": _intersect([_to_printer(d["left"], d["right"], 0, mapping) for d in xs.values()]),
            "y": _intersect([_to_printer(float(lo), float(hi), 1, mapping) for _, lo, hi in ys]),
            "z": (0.0, float(zmax[-1]))}


def _sources(sweep_log):
    """Per head: the X scan's left/right values and the Y reach, for the comments in cad_values.cfg."""
    xs, ys = {}, {}
    for head, side, v in re.findall(r"(\w+) head, (left|right) side: first nozzle X with no new overlap (-?[0-9.]+)",
                                    sweep_log):
        xs.setdefault(head, {})[side] = v
    for head, lo, hi in re.findall(r"(\w+) carried: .*?nozzle Y reach (-?[0-9.]+) \.\. (-?[0-9.]+)", sweep_log):
        ys[head] = (lo, hi)
    return xs, ys


def cad_values_cfg(sweep_log, z_log, mapping):
    """cad_values.cfg: the stepper limits the CAD logs give, with each one's source (vt350#294). Kalico merges these
    options into the [stepper_*] sections of steppers.cfg."""
    cad = cad_limits(sweep_log, z_log, mapping)
    xs, ys = _sources(sweep_log)
    (ox, oy), (sx, sy) = mapping["origin_model_xy"], mapping["sign_xy"]
    f = lambda v: f"{v:.2f}"
    sign = lambda s, o: f"{'' if s > 0 else '-'}(model {'-' if o >= 0 else '+'} {abs(o)})"
    x = "; ".join(f"{h} {d['left']} .. {d['right']}" for h, d in xs.items())
    y = "; ".join(f"{h} {lo} .. {hi}" for h, (lo, hi) in ys.items())
    (x0, x1), (y0, y1), (_, z1) = cad["x"], cad["y"], cad["z"]
    return "\n".join([
        "# GENERATED by `python3 cad/klipper/limits.py --cfg > cad/klipper/cad_values.cfg` from the committed CAD logs;",
        "# don't edit by hand: cad/klipper/test_limits.py fails when this file isn't what the logs give (vt350#294).",
        "# Kalico merges these options into the sections of the same name in steppers.cfg. Printer XY from model XY:",
        f"#   X = {sign(sx, ox)}, Y = {sign(sy, oy)} (cad/klipper/xy_mapping.json); each axis takes the tighter head.",
        "",
        "[stepper_x]",
        "# source: cad/data/logs/sweep_toolhead.log \"<head> head, left/right side: first nozzle X with no new overlap\"",
        f"#         (model X: {x})",
        f"position_min: {f(x0)}",
        f"position_max: {f(x1)}",
        "# PLACEHOLDER: X homes at its max (where X homes with two O2S heads is not decided, stage #15)",
        f"position_endstop: {f(x1)}",
        "",
        "[stepper_y]",
        "# source: cad/data/logs/sweep_toolhead.log \"<head> carried: ... nozzle Y reach <min> .. <max>\"",
        f"#         (model Y: {y})",
        "# Y below 0 is the dock zone in front of the plate: the box limit lets the nozzle reach it anywhere along X,",
        "# so only the tool-change macros keep it to the dock positions (#116 AC4).",
        f"position_min: {f(y0)}",
        f"position_max: {f(y1)}",
        "# PLACEHOLDER: Y homes at its max (stage #15)",
        f"position_endstop: {f(y1)}",
        "",
        "[stepper_z]",
        "# source: cad/data/logs/z_sweep.log klipper_position_max_configured_mm (Z position_min is not a CAD limit:",
        "#         it is in steppers.cfg)",
        f"position_max: {f(z1)}",
        ""])


def differences(cfg_lim, cad_lim):
    """Every limit must equal the CAD's, except Z position_min, which may sit below the CAD floor: Z0 comes from the
    Beacon nozzle tap and shifts per nozzle, so a negative min is a software allowance for tool offsets (vt350#116)."""
    out = []
    for a in AXES:
        for i, key in enumerate(("position_min", "position_max")):
            if (a, i) == ("z", 0) and cfg_lim[a][i] <= cad_lim[a][i]:
                continue
            if cfg_lim[a][i] != cad_lim[a][i]:
                out.append(f"{a} {key}: config {cfg_lim[a][i]}, CAD {cad_lim[a][i]}")
    return out


def _fmt(v):
    return f"{v:.{DECIMALS}f}"


def envelope_gcode(cfg):
    """G-code that walks the envelope: kalisim runs @setup + @in-range in one go (every move must be accepted), and
    @setup + each @past block on its own (the move must be refused)."""
    lim = cfg_limits(cfg)
    (x0, x1), (y0, y1), (z0, z1) = lim["x"], lim["y"], lim["z"]
    lines = ["; VT350 envelope walk (vt350#116 AC3). Generated by cad/klipper/limits.py --gcode from printer.cfg;",
             "; don't edit. Run by cad/klipper/test_kalico_batch.py: @setup + @in-range once, every move accepted;",
             "; @setup + each @past block alone, its move refused with \"Move out of range\".",
             "; @setup", "G28", "G90", "G1 F6000",
             "; @in-range", "; the four corners at each Z end"]
    for z in (max(z0, 0.0), z1):                         # corners on the plate (Z0), not at a negative allowance
        for x, y in ((x0, y0), (x0, y1), (x1, y1), (x1, y0)):
            lines.append(f"G1 X{_fmt(x)} Y{_fmt(y)} Z{_fmt(z)}")  # front-left, rear-left, rear-right, front-right
    if z0 < 0:
        lines += ["; Z position_min: the allowance below the plate for tool offsets", f"G1 Z{_fmt(z0)}"]
    for a in AXES:
        step = step_distance(cfg, a)
        for end, sign in (("min", -1), ("max", 1)):
            limit = lim[a][0 if end == "min" else 1]
            past = _fmt(limit + sign * step)
            if not (float(past) - limit) * sign > 0:
                raise ValueError(f"{a}: one step ({step} mm) past {limit} rounds back onto the limit at "
                                 f"{DECIMALS} decimals")
            lines += [f"; @past {a}_{end}", f"G1 {a.upper()}{past}"]
    return "\n".join(lines) + "\n"


def _logs():
    with open(os.path.join(LOGS, "sweep_toolhead.log")) as f, open(os.path.join(LOGS, "z_sweep.log")) as g:
        return f.read(), g.read()


def main(argv, cfg=None):
    """cfg: the parsed config (default: printer.cfg and its includes)."""
    if argv == ["--cfg"]:
        return [cad_values_cfg(*_logs(), load_mapping()).rstrip("\n")]
    cfg = load_cfg() if cfg is None else cfg
    if argv == ["--gcode"]:
        return [envelope_gcode(cfg).rstrip("\n")]
    if argv == ["--check"]:
        cad = cad_limits(*_logs(), load_mapping())
        diff = differences(cfg_limits(cfg), cad)
        if diff:
            raise SystemExit("limits: FAILED: " + "; ".join(diff))
        return [f"{a}: {lo} .. {hi}" for a, (lo, hi) in cad.items()] + ["limits: OK"]
    raise SystemExit(__doc__)


if __name__ == "__main__":
    print("\n".join(main(sys.argv[1:])))
