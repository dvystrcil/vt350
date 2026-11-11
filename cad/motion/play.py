#!/usr/bin/env python3
"""Watch the VT350's tool-change timeline play on the model in FreeCAD (vt350#135 AC3).

    python3 cad/motion/play.py                     # opens FreeCAD with the player panel (play/pause/step/speed/stop)
    python3 cad/motion/play.py --speed 0.25        # start in slow motion
    python3 cad/motion/play.py --dry-run           # print the FreeCAD command and environment, don't start it
    python3 cad/motion/play.py --autotest out.json # under xvfb: play every frame, stop, check every Placement is back

What it does:
  1. Groups: runs cad/studies/sweep_toolhead.py's plan stage on the model (freecadcmd, ~35 s on lite-30) and names its
     groups the way cad/motion/rig.json does (bed, gantry, belt, carriage, Left, Right; each head's group includes its
     MadMax tool plate). The result is cached in $VT350_WORK/motion/, keyed by the model's bytes, sweep_toolhead.py
     and rig.json, so the next run starts at once.
  2. Starts FreeCAD with platform/freecad/player_gui.FCMacro, which opens a private copy of the model (never the model
     itself, never saved; the copy goes in $VT350_WORK/motion/ and is removed on close) and plays cad/klipper/toolchange_timeline.jsonl through rig.json.

The model defaults to the one the committed sweep_toolhead.log ran on (the rig's numbers come from that log), in
~/Documents/VT350. FreeCAD is $FREECAD if set, else the AppImage clashlib uses ($FREECAD_APPIMAGE).

This file is VT350-specific. Plain python3, standard library only; FreeCAD runs as a separate process.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PLATFORM = os.path.join(ROOT, "platform", "freecad")
SWEEP = os.path.join(ROOT, "cad", "studies", "sweep_toolhead.py")
SWEEP_LOG = os.path.join(ROOT, "cad", "data", "logs", "sweep_toolhead.log")
RIG = os.path.join(HERE, "rig.json")
TIMELINE = os.path.join(ROOT, "cad", "klipper", "toolchange_timeline.jsonl")
MODELS = "/home/dan/Documents/VT350"
FORMAT = "3"                     # the groups file's format, in the cache key: 2 added "clip" (the belts), 3 "hide"
WORK = os.environ.get("VT350_WORK", os.path.join(ROOT, "cad", "data"))


def groups_from_plan(plan, rig):
    """sweep_toolhead's plan -> {rig group: [object Name]}. The plan's keys are the rig's group names, its heads by
    head name."""
    out = {}
    for g in [rig["bed"]["group"], *rig["gantry_groups"], rig["carriage_group"]]:
        if g not in plan:
            raise ValueError(f"the plan has no group {g!r} (the rig moves it)")
        out[g] = list(plan[g])
    for name, h in rig["heads"].items():
        if name not in plan.get("heads", {}):
            raise ValueError(f"the plan has no head {name!r} (the rig has it)")
        out[h["group"]] = list(plan["heads"][name])
    return out


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def groups_file(model, rig, work, run_plan):
    """The player's groups file for this model, from the cache or a fresh plan. -> its path."""
    msha = _sha(model)
    key = hashlib.sha256((FORMAT + msha + _sha(SWEEP) + json.dumps(rig, sort_keys=True)).encode()).hexdigest()[:16]
    d = os.path.join(work, "motion")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"groups-{os.path.splitext(os.path.basename(model))[0]}-{key}.json")
    if os.path.exists(path):
        return path
    plan = run_plan(model)
    groups = groups_from_plan(plan, rig)
    if "dock_copies" not in plan:
        raise ValueError("the plan has no dock_copies (sweep_toolhead.py from before vt350#135's ghost-carriage fix)")
    sys.path.insert(0, os.path.dirname(SWEEP))
    import sweep_toolhead
    # a belt is one loop: its side runs change length with gantry Y, so only the part in the XY joints' Y band moves
    # rigidly with the gantry. Show that part, as the sweep checks it (vt350#135: the whole loop shot out the front)
    clip = {n: list(sweep_toolhead.BELT_CLIP) for n in plan["belt"]}
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".groups-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump({"model": model, "model_sha256": msha, "from": "cad/studies/sweep_toolhead.py plan stage",
                       "groups": groups, "clip": clip,
                       # each dock's carriage copy at its pickup pose: it stayed behind as a ghost once the moving
                       # carriage left (vt350#135)
                       "hide": list(plan["dock_copies"])}, f, indent=1)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
    return path


def run_plan(model):
    """sweep_toolhead.py's plan stage (freecadcmd) on the model."""
    sys.path[:0] = [os.path.dirname(SWEEP), PLATFORM]
    os.environ["VT350_MODEL"] = model                  # the plan stage's freecadcmd reads it
    import clashlib
    import sweep_toolhead
    return sweep_toolhead.plan_stage(clashlib.FREECADCMD)


def default_model(sweep_log, models):
    """The model sweep_toolhead.log ran on, in the models folder."""
    with open(sweep_log) as f:
        for line in f:
            m = re.search(r"\] model (\S+\.FCStd) \(read-only\)", line)
            if m:
                return os.path.join(models, os.path.basename(m.group(1)))
    raise ValueError(f"{sweep_log}: no 'model ... (read-only)' line")


def command(cfg, freecad):
    """-> (argv, the MOTION_* environment) that starts the player."""
    argv = list(freecad) + [os.path.join(PLATFORM, "player_gui.FCMacro")]
    if cfg["autotest"]:
        argv = ["xvfb-run", "-a"] + argv
    env = {"MOTION_MODEL": cfg["model"], "MOTION_GROUPS": cfg["groups"], "MOTION_TIMELINE": cfg["timeline"],
           "MOTION_RIG": cfg["rig"], "MOTION_FPS": str(cfg["fps"]), "MOTION_SPEED": str(cfg["speed"]),
           "MOTION_COPY_DIR": cfg["copy_dir"]}
    if cfg["carried"]:
        env["MOTION_CARRIED"] = cfg["carried"]
    if cfg["autotest"]:
        env["MOTION_AUTOTEST"] = cfg["autotest"]
    return argv, env


def freecad_gui():
    if os.environ.get("FREECAD"):
        return os.environ["FREECAD"].split()
    sys.path.insert(0, PLATFORM)
    import clashlib
    return [clashlib.APP]


def main(argv):
    ap = argparse.ArgumentParser(prog="play", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--model", help="the .FCStd (default: the one sweep_toolhead.log ran on, in ~/Documents/VT350)")
    ap.add_argument("--timeline", default=TIMELINE)
    ap.add_argument("--rig", default=RIG)
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--speed", type=float, default=1.0, help="starting speed factor (the panel can change it)")
    ap.add_argument("--carried", help="the head on the carriage at the start (default none)")
    ap.add_argument("--dry-run", action="store_true", help="print the command and environment, don't start FreeCAD")
    ap.add_argument("--autotest", metavar="OUT", help="play every frame under xvfb, stop, check, write OUT (JSON)")
    a = ap.parse_args(argv)
    model = a.model or default_model(SWEEP_LOG, MODELS)
    with open(a.rig) as f:
        rig = json.load(f)
    cfg = {"model": model, "groups": groups_file(model, rig, WORK, run_plan), "timeline": a.timeline, "rig": a.rig,
           "fps": a.fps, "speed": a.speed, "carried": a.carried, "autotest": a.autotest and os.path.abspath(a.autotest),
           "copy_dir": os.path.join(WORK, "motion")}        # the model's private copy: /tmp's quota can't take 180 MB
    cmd, env = command(cfg, freecad_gui())
    if a.dry_run:
        print(" ".join(f"{k}={v}" for k, v in env.items()) + " " + " ".join(cmd))
        return 0
    import subprocess
    rc = subprocess.run(cmd, env=dict(os.environ, **env)).returncode
    if a.autotest:
        with open(a.autotest) as f:
            res = json.load(f)
        print(json.dumps(res, indent=1))
        ok = "fatal" not in res and not res["not_restored"] and res["model_unchanged"] and res["copy_removed"]
        print("play autotest: " + ("OK" if ok else "FAILED"))
        return 0 if ok else 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
