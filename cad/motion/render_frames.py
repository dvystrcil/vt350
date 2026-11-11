#!/usr/bin/env python3
"""Real-renderer (Blender) frames and a video of the VT350's tool-change timeline (vt350#135 AC4).

    python3 cad/motion/render_frames.py prepare            # groups + ONE mesh export + frames.json (FreeCAD GUI, xvfb)
    python3 cad/motion/render_frames.py submit [--dry-run] # the frames go to the batch lane (Blender, GPU)
    python3 cad/motion/render_frames.py encode <frames dir> [--out notes/reference/....mp4]
    python3 cad/motion/render_frames.py stills --at 21,-68.96 # AC5: full-size stills of the frames at a printer XY

How:
  1. Groups: cad/motion/play.py's groups file (sweep_toolhead.py's plan stage, cached): bed, gantry, belt, carriage,
     Left, Right, each belt's clip box and the docks' carriage copies to hide (the player's two fixes: without them
     the belt loop shoots out of the frame and a ghost carriage stays in each dock).
  2. Export: platform/render/export_meshes.py ONCE, at the model pose, with VT350_GROUPS: each group's parts in
     buckets of their own. Cached in $VT350_WORK/motion/render-<model>-<key>/export, keyed by the groups file, the
     exporter and the colour map. Nothing is re-exported per frame.
  3. frames.json: platform/freecad/timeline.py's frames through rig.json (platform/render/motion.py). The export's
     scene.json gets the "docks" camera, computed from the rig; colours.py, colours.json and motion.py are copied in,
     so the export dir is a complete batch-lane input (the lane stages only the script).
  4. Blender (platform/render/render.py --frames) moves each group's objects per frame: frame-NNNNN.png.
  5. ffmpeg: the frames -> an H.264 MP4 for notes/reference.

Everything goes to $VT350_WORK (default cad/data, git-ignored), never /tmp: lite-30 is 184 MB and /tmp has a quota.
Never writes a model. VT350-specific; plain python3, standard library only.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RENDER = os.path.join(ROOT, "platform", "render")
sys.path[:0] = [HERE, RENDER, os.path.join(ROOT, "platform", "freecad")]
import motion  # noqa: E402
import play  # noqa: E402
import timeline  # noqa: E402

RIG, TIMELINE, WORK = play.RIG, play.TIMELINE, play.WORK
COLOURS = os.path.join(ROOT, "cad", "render", "colours.json")
HOMELAB = os.environ.get("HOMELAB", os.path.join(os.path.dirname(ROOT), "homelab"))
EXPORT_CODE = [os.path.join(RENDER, f) for f in ("export_meshes.py", "colours.py", "logos.py", "motion.py")] + [COLOURS]
VIDEO = os.path.join(ROOT, "notes", "reference", "toolchange-docks", "toolchange-docks.mp4")
NOTIFY = "dvystrcil/vt350#135"


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def export_key(groups, code):
    """The export's cache key: the groups file (it holds the model's sha256) and everything that shapes the meshes."""
    h = hashlib.sha256(_sha(groups).encode())
    for p in code:
        h.update(_sha(p).encode())
    return h.hexdigest()[:16]


def export_problem(d):
    """None if export_meshes.py finished in d, else what's wrong (render_full.sh's judgement)."""
    log = os.path.join(d, "export.log")
    if not os.path.exists(log):
        return f"no export.log in {d}"
    with open(log) as f:
        lines = f.read().splitlines()
    bad = [l for l in lines if "FAILED" in l and "] index: " not in l]
    if bad:
        return f"export FAILED: {bad[0]} (see {log})"
    if not any("] done: " in l for l in lines):
        return f"export never finished (no 'done:' in {log})"
    return None


def dock_view(rig, distance=1120.0, rise=270.0, lens_mm=50.0):
    """A camera on both docks: aimed at the middle of the docked nozzles, from `distance` mm out on the side the
    carriage pushes INTO the docks ("into", in model coordinates: the VT350's front) and `rise` mm above them. From
    the other side the back panel hides everything (seen on lite-30, 2026-11-10)."""
    hs = list(rig["heads"].values())
    xs = [h["nozzle"][0] for h in hs]
    look = [(min(xs) + max(xs)) / 2, sum(h["nozzle"][1] for h in hs) / len(hs), hs[0]["nozzle"][2]]
    ix, iy = hs[0]["into"]
    sx, sy = rig["xy"]["sign_xy"]
    pos = [look[0] + ix * sx * distance, look[1] + iy * sy * distance, look[2] + rise]
    return {"name": "docks", "pos": pos, "look": look, "lens_mm": lens_mm, "ev": -0.5}


def make_frames(rig, timeline_path, fps, every, carried=None):
    """fps None: one frame per move end (timeline.py --moves), for stills at exact points."""
    with open(timeline_path) as f:
        records = [json.loads(line) for line in f if line.strip()]
    return motion.frames_file(timeline.frames(rig, records, fps, carried), fps or 1, every)


def frames_at(ff, x, y, tol=0.01):
    """The frames whose printer XY is (x, y)."""
    at = [f for f in ff["frames"] if abs(f["pos"][0] - x) <= tol and abs(f["pos"][1] - y) <= tol]
    if not at:
        raise ValueError(f"no frame at printer X {x} Y {y}")
    return at


def submit_cmd(export, samples, size, n, notify, deadline, view="docks", frames="frames.json"):
    return ["python3", os.path.join(HOMELAB, "bin", "gpu-batch-submit.py"), "blender",
            "--input", export, "--script", os.path.join(RENDER, "render.py"), "--name", "vt350-motion",
            "--expect", "out/frame-*.png", "--min-outputs", str(n), "--deadline", str(deadline), "--notify", notify,
            "--", str(samples), "--frames", frames, "--view", view, "--size", size]


def freecad_gui():
    return play.freecad_gui()


def prepare(a, rig):
    model = a.model or play.default_model(play.SWEEP_LOG, play.MODELS)
    groups = play.groups_file(model, rig, WORK, play.run_plan)
    run = os.path.join(WORK, "motion", f"render-{os.path.splitext(os.path.basename(model))[0]}-"
                                       f"{export_key(groups, EXPORT_CODE)}")
    exp = os.path.join(run, "export")
    if export_problem(exp):
        os.makedirs(exp, exist_ok=True)
        env = dict(os.environ, VT350_MODEL=model, VT350_RENDER_OUT=exp, VT350_GROUPS=groups, VT350_COLOURS=COLOURS,
                   VT350_EXTRA="")
        cmd = ["xvfb-run", "-a", *freecad_gui(), os.path.join(RENDER, "export_meshes.py")]
        print(f"export: {os.path.basename(model)} -> {exp} (FreeCAD GUI under xvfb, minutes)", flush=True)
        with open(os.path.join(run, "freecad.out"), "w") as out:
            subprocess.run(cmd, env=env, stdout=out, stderr=subprocess.STDOUT)   # os._exit: its rc means nothing
        p = export_problem(exp)
        if p:
            raise SystemExit(f"render_frames: {p}")
    else:
        print(f"export: reusing {exp}")
    with open(os.path.join(exp, "scene.json")) as f:
        scene = json.load(f)
    scene["views"] = [dock_view(rig)]
    ff = make_frames(rig, a.timeline, a.fps, a.every)
    motion.check_scene(ff, scene)
    for name, obj in (("scene.json", scene), ("frames.json", ff)):
        with open(os.path.join(exp, name), "w") as f:
            json.dump(obj, f, indent=1)
    for p in (os.path.join(RENDER, "colours.py"), os.path.join(RENDER, "motion.py"), COLOURS):
        shutil.copy2(p, exp)
    moving = {k: b["group"] for k, b in scene["buckets"].items() if b.get("group")}
    print(f"prepared {exp}: {len(scene['buckets'])} buckets ({len(moving)} moving: "
          f"{', '.join(sorted(set(moving.values())))}), {len(ff['frames'])} frames at {ff['fps']:g} fps")
    return exp, ff


def main(argv):
    ap = argparse.ArgumentParser(prog="render_frames", description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("what", choices=("prepare", "submit", "encode", "stills"))
    ap.add_argument("frames_dir", nargs="?", help="encode: the rendered frames")
    ap.add_argument("--model", help="the .FCStd (default: the one sweep_toolhead.log ran on)")
    ap.add_argument("--timeline", default=TIMELINE)
    ap.add_argument("--rig", default=RIG)
    ap.add_argument("--fps", type=float, default=30.0, help="timeline frames per second (default 30)")
    ap.add_argument("--every", type=int, default=2, help="render every Nth of them (default 2: 15 fps)")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--deadline", type=int, default=4 * 3600)
    ap.add_argument("--notify", default=NOTIFY)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=VIDEO, help="encode: the MP4 (default notes/reference/toolchange-docks/toolchange-docks.mp4)")
    ap.add_argument("--at", help="stills: printer X,Y")
    a = ap.parse_args(argv)
    with open(a.rig) as f:
        rig = json.load(f)
    if a.what == "encode":
        if not a.frames_dir:
            ap.error("encode needs the frames dir")
        exp, ff = prepare(a, rig)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        motion.encode(a.frames_dir, ff, a.out)
        print(f"wrote {a.out} ({os.path.getsize(a.out) / 1e6:.1f} MB, {len(ff['frames'])} frames)")
        return 0
    exp, ff = prepare(a, rig)
    if a.what == "stills":
        if not a.at:
            ap.error("stills needs --at X,Y")
        x, y = (float(v) for v in a.at.split(","))
        at = frames_at(make_frames(rig, a.timeline, None, 1), x, y)
        sub = {"fps": ff["fps"], "frames": at}
        name = f"stills-{x:g}_{y:g}.json"
        with open(os.path.join(exp, name), "w") as f:
            json.dump(sub, f, indent=1)
        for k, f in enumerate(at):
            f["i"] = 90000 + k                         # move-end frames: their own numbers, beside the video's
        print(f"{len(at)} move ends at X {x:g} Y {y:g}: " + ", ".join(
            f"frame-{f['i']} seq {f['seq']} carried {f['carried']}" for f in at))
        cmd = submit_cmd(exp, 128, "1920x1080", len(at), a.notify, 3600, frames=name)
    else:
        cmd = submit_cmd(exp, a.samples, a.size, len(ff["frames"]), a.notify, a.deadline)
    if a.what == "prepare":
        print("next: python3 cad/motion/render_frames.py submit   (the batch lane)")
        return 0
    if a.dry_run:
        cmd.insert(3, "--dry-run")
    print(" ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=HOMELAB).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
