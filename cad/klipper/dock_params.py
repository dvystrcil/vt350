#!/usr/bin/env python3
"""The VT350's tool-change params: from the CAD dock poses, checked against toolchanger.cfg (vt350#116 AC4).

    python3 cad/klipper/dock_params.py --check     # toolchanger.cfg's params == the ones the CAD gives; "dock-params: OK"

The macros are MadMax's (madmax/toolchanger.cfg, vendored unchanged). They read these params:

  [toolchanger]  params_close_y         Y right before the magnets start to grab
                 params_attach_y        Y at the keyslots' large opening
                 params_safe_shuttle_y  Y where the empty carriage travels in X
                 params_safe_toolhead_y Y where the carriage with a head travels in X
  [tool Tn]      params_park_x          X of the head in its dock
                 params_detach_x        X after the sideways move that takes the screws out of the keyslots

From the CAD (cad/data/logs/sweep_toolhead.log), mapped by xy_mapping.json:
  park_x   "<head>: docked nozzle tip (x, y, z)"                    -> x
  attach_y docked y - the keyslot slide ("slid 6.0 mm forward to the keyslots' large opening")
Not in the CAD, so kept as MadMax's distance from its own parked Y (its attach_y + the same slide):
  close_y, safe_shuttle_y, safe_toolhead_y, and the 5 mm detach move. The safe Ys depend on the heads' depth, which
  differs from MadMax's; AC5 clash-checks them on the model.

This file is VT350-specific. Plain python3, standard library only.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import limits  # noqa: E402

# git blob ids of the vendored files at zruncho3d/madmax@277a63cbb696f937fbf9d883a8d8c46a658cd6d9,
# Configs/r2pdx_config-v2-Kalico-Beacon-2025-07-05/klipper-toolchanger/<name> (GPL-3.0)
UPSTREAM_BLOBS = {"toolchanger.cfg": "06e94bda4a9a87f0694d5baf2c34b7615d05e177",
                  "toolchanger_macros.cfg": "3f4c8abce0493be9daf21a5f4e987b0210056980"}
Y_PARAMS = ("params_attach_y", "params_close_y", "params_safe_shuttle_y", "params_safe_toolhead_y")
# MadMax's detach move: toolboard_0.cfg params_park_x 42 -> params_detach_x 47 (blob be0eeeac), toolboard_1.cfg
# 435 -> 440 (blob 7b8ee98a), same commit. Away from the keyslot plate.
DETACH = 5.0
# Which side of each head its dock's keyslot plate is on, in model X: cad/passes/lite23_cowl_docks.py "Per head
# (left = -X dock side, right = +X, mirror image)". The detach move goes the other way.
HEADS = {"Left": {"tool": "T0", "tool_number": 0, "extruder": "extruder", "plate_side": -1},
         "Right": {"tool": "T1", "tool_number": 1, "extruder": "extruder1", "plate_side": 1}}
DECIMALS = 2


def docked(sweep_log):
    """{"Left": (x, y), ...}: each head's docked nozzle tip, model coordinates."""
    got = {h: (float(x), float(y)) for h, x, y in
           re.findall(r"(\w+): docked nozzle tip \((-?[0-9.]+), (-?[0-9.]+), -?[0-9.]+\)", sweep_log)}
    if set(got) != set(HEADS):
        raise ValueError(f"sweep_toolhead log: need a 'docked nozzle tip' line for each of {sorted(HEADS)}: {got}")
    return got


def slide(sweep_log):
    """The keyslot slide, parked -> large opening, in mm."""
    got = set(re.findall(r"slid (-?[0-9.]+) mm forward to the keyslots' large opening", sweep_log))
    if len(got) != 1:
        raise ValueError(f"sweep_toolhead log: need one 'slid N mm forward to the keyslots' large opening': {got}")
    return float(got.pop())


def madmax_params(path=os.path.join(HERE, "madmax", "toolchanger.cfg")):
    """MadMax's own Y params, from the vendored [toolchanger]."""
    with open(path) as f:
        tc = limits.parse_cfg(f.read())["toolchanger"]
    return {k: float(tc[k]) for k in Y_PARAMS}


def _r(v):
    return round(v, DECIMALS)


def derive(sweep_log, mapping, madmax):
    """{"toolchanger": {param: y}, "tools": {"T0": {...}, ...}} in printer coordinates."""
    poses, s = docked(sweep_log), slide(sweep_log)
    ys = {y for _, y in poses.values()}
    if len(ys) != 1:
        raise ValueError(f"the docks aren't at the same Y ({poses}): [toolchanger] has one close/attach Y for all")
    (oy, sy), (ox, sx) = (mapping["origin_model_xy"][1], mapping["sign_xy"][1]), \
                         (mapping["origin_model_xy"][0], mapping["sign_xy"][0])
    parked_model_y = ys.pop()
    madmax_parked = madmax["params_attach_y"] + s               # the slide is upstream's (#52)
    model_y = {"params_attach_y": parked_model_y - s}
    for k in ("params_close_y", "params_safe_shuttle_y", "params_safe_toolhead_y"):
        model_y[k] = parked_model_y + (madmax[k] - madmax_parked)
    tc = {k: _r(sy * (v - oy)) for k, v in sorted(model_y.items())}
    tools = {}
    for head, (x, _) in poses.items():
        h = HEADS[head]
        detach_model_x = x - h["plate_side"] * DETACH
        tools[h["tool"]] = {"tool_number": h["tool_number"], "extruder": h["extruder"],
                            "params_park_x": _r(sx * (x - ox)), "params_detach_x": _r(sx * (detach_model_x - ox))}
    return {"toolchanger": tc, "tools": dict(sorted(tools.items()))}


def derive_committed():
    with open(os.path.join(limits.LOGS, "sweep_toolhead.log")) as f:
        return derive(f.read(), limits.load_mapping(), madmax_params())


def differences(cfg, want):
    """Every derived param that toolchanger.cfg doesn't set to the same value."""
    out = []
    for sec, params in [("toolchanger", want["toolchanger"])] + [(f"tool {t}", p) for t, p in want["tools"].items()]:
        have = cfg.get(sec, {})
        for k, v in params.items():
            got = have.get(k)
            same = got is not None and (got == v if isinstance(v, str) else
                                        (int(got) == v if isinstance(v, int) else float(got) == v))
            if not same:
                out.append(f"[{sec}] {k}: toolchanger.cfg {got}, CAD {v}")
    return out


def main(argv):
    if argv != ["--check"]:
        raise SystemExit(__doc__)
    want = derive_committed()
    with open(os.path.join(HERE, "toolchanger.cfg")) as f:
        diff = differences(limits.parse_cfg(f.read()), want)
    if diff:
        raise SystemExit("dock-params: FAILED: " + "; ".join(diff))
    return [f"{k}: {v}" for k, v in want["toolchanger"].items()] + \
           [f"{t}: park_x {p['params_park_x']}, detach_x {p['params_detach_x']}" for t, p in want["tools"].items()] + \
           ["dock-params: OK"]


if __name__ == "__main__":
    print("\n".join(main(sys.argv[1:])))
