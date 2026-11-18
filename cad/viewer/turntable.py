#!/usr/bin/env python3
# Turntables of real renders, start to finish (vt350#220). One settings file per turntable, cad/viewer/turntables/
# <name>.json, holds every choice (what to export, cameras, render look, page text, where it's published); each step
# reads it, so a turntable is made the same way every time. Steps, in order:
#
#   cad/viewer/turntable.py export  <name> [--model N]     FreeCAD export (GUI under xvfb, read-only) + licence check
#   cad/viewer/turntable.py views   <name> [--run DIR]     the turntable cameras into the export's scene.json
#   cad/viewer/turntable.py render  <name> [--run DIR] [--lane [--dry-run]]   Blender here (RUN/out), or the lane
#   cad/viewer/turntable.py collect <name> [--run DIR]     after a lane render: its frames into RUN/out
#   cad/viewer/turntable.py stage   <name> [--run DIR]     preview folder RUN/page (index.html, turntable.json, frames/)
#   cad/viewer/turntable.py publish <name> [--run DIR] [--upload 0]   notes/reference page + release asset (public)
#   cad/viewer/turntable.py all     <name> [--model N]     export, views, render here, stage
#   cad/viewer/turntable.py check   all                    every settings file has what the steps need (CI)
#
# RUN is ~/Documents/VT350/renders/vt350-lite-<N>-<name>-turntable-<UTC>/; later steps take the newest one unless
# --run names another. Each step ends with "<step>: OK". publish refuses unless every part's licence is shareable
# (cad/viewer/licences.json): a whole-printer export has many more parts than the toolhead's rules cover.
# Writes to git only in publish (notes/reference/). Never saves a model.
import glob, json, os, re, shlex, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
APP = os.environ.get("VT350_APP", os.path.expanduser("~/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage"))
DOCS = os.environ.get("VT350_DOCS", os.path.expanduser("~/Documents/VT350"))
SUBMIT = os.environ.get("VT350_BATCH_SUBMIT", os.path.expanduser("~/Code/homelab/bin/gpu-batch-submit.py"))
LANE = os.environ.get("VT350_BATCH_ROOT", "/mnt/nfs/media/gpu-batch")
COLOURS = os.environ.get("VT350_COLOURS", os.path.join(ROOT, "cad", "render", "colours.json"))
LICENCES = os.path.join(HERE, "licences.json")
PLATFORM = os.path.join(ROOT, "platform")


def die(msg): print(f"turntable: {msg}", file=sys.stderr); sys.exit(1)


def say(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def settings(name):
    p = os.path.join(HERE, "turntables", name + ".json")
    if not os.path.isfile(p): die(f"no settings {p} (have: {', '.join(sorted(os.listdir(os.path.dirname(p))))})")
    return json.load(open(p))


def find_run(name, opts):
    if "--run" in opts:
        r = os.path.abspath(os.path.expanduser(opts["--run"]))
        if not os.path.isdir(os.path.join(r, "export")): die(f"{r} has no export/")
        return r
    runs = sorted(glob.glob(os.path.join(DOCS, "renders", f"vt350-lite-*-{name}-turntable-*")), key=os.path.getmtime)
    if not runs: die(f"no run for {name}; start with: cad/viewer/turntable.py export {name}")
    return runs[-1]


def model_name(run):
    m = json.load(open(os.path.join(run, "export", "scene.json"))).get("model") or os.path.basename(run)
    return os.path.splitext(os.path.basename(m))[0] if m.endswith(".FCStd") else re.match(r"(vt350-lite-\d+)", m).group(1)


def sh(cmd, log=None, **kw):
    if log:
        with open(log, "w") as f: return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, **kw).returncode
    return subprocess.run(cmd, **kw).returncode


def licence_check(run, must_pass):
    rc = sh(["python3", os.path.join(PLATFORM, "viewer", "licence_check.py"), os.path.join(run, "export", "scene.json"),
             LICENCES, os.path.join(run, "licences.log")])
    if rc and must_pass: die(f"licence check FAILED: see {run}/licences.log; add rules to {LICENCES} (with sources)")
    if rc: say(f"licence check: not every part is cleared yet (fine for a private preview; publish will refuse). "
               f"{run}/licences.log")
    return rc == 0


def export(name, s, opts):
    n = opts.get("--model") or str(s["model"])
    model = os.path.join(DOCS, f"vt350-lite-{n}.FCStd")
    if not os.path.isfile(model): die(f"no model {model}")
    run = os.path.join(DOCS, "renders", f"vt350-lite-{n}-{name}-turntable-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}")
    exp = os.path.join(run, "export"); os.makedirs(exp)
    env = dict(os.environ, VT350_COLOURS=COLOURS, VT350_MODEL=model, VT350_RENDER_OUT=exp,
               VT350_EXTRA=":".join(os.path.join(DOCS, e) for e in s.get("extra", [])))
    if s.get("selection"): env["RENDER_SELECT"] = os.path.join(ROOT, s["selection"])
    say(f"FreeCAD export: vt350-lite-{n}{' + ' + ', '.join(s['extra']) if s.get('extra') else ''}"
        f"{', selection ' + s['selection'] if s.get('selection') else ', whole model'} -> {exp}")
    sh(["xvfb-run", "-a", "-s", "-screen 0 1280x1024x24", APP, os.path.join(PLATFORM, "render", "export_meshes.py")],
       log=os.path.join(run, "freecad.out"), env=env)
    log = open(os.path.join(exp, "export.log")).read() if os.path.exists(os.path.join(exp, "export.log")) else ""
    if "] done: " not in log or any("FAILED" in l and "] index: " not in l for l in log.splitlines()):
        die(f"export FAILED: see {exp}/export.log and {run}/freecad.out")
    licence_check(run, must_pass=False)
    print(run); print("export: OK")


def views(name, s, opts):
    run = find_run(name, opts); v = s["views"]
    cmd = ["python3", os.path.join(PLATFORM, "viewer", "frame_view.py"), os.path.join(run, "export"),
           "--turntable", f"{v['azimuths']}x{len(v['elevations'])}", "--elevations", ",".join(map(str, v["elevations"])),
           "--fill", str(v["fill"]), "--ev", str(v["ev"])]
    if v.get("hide"): cmd += ["--hide", ",".join(v["hide"])]
    if sh(cmd): die("frame_view failed")
    print("views: OK")


def render_args(s):
    r = s["render"]
    return ["--size", r["size"], "--look", r["look"], "--plastic-specular", str(r["plastic_specular"])]


def render(name, s, opts):
    run = find_run(name, opts); r = s["render"]
    if "--lane" in opts:
        cmd = [SUBMIT, "blender", "--input", os.path.join(run, "export"), "--script",
               os.path.join(PLATFORM, "render", "render.py"), "--with", os.path.join(PLATFORM, "render", "colours.py"),
               "--with", COLOURS, "--name", f"{model_name(run)}-{name}-tt", "--expect", "out/*.jpg",
               "--min-outputs", str(len(s["views"]["elevations"]) * s["views"]["azimuths"]),
               "--deadline", str(r.get("lane_deadline_s", 14400)), "--notify", r["lane_notify"]] + \
              (["--dry-run"] if "--dry-run" in opts else []) + ["--", str(r["lane_samples"])] + render_args(s)
        say("submit: " + shlex.join(cmd))
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(SUBMIT)))
        print(p.stdout.strip() if "--dry-run" in opts else p.stdout.strip()[-1500:])
        if "--dry-run" in opts: print("render: dry run, nothing submitted"); return
        m = re.search(r"submitted (\S+)", p.stdout)
        if p.returncode or not m: die(f"lane submit failed: {p.stderr.strip()[-500:]}")
        open(os.path.join(run, "lane-job"), "w").write(m.group(1) + "\n")
        print(f"lane job {m.group(1)}: the result is a comment on {r['lane_notify']}; then: "
              f"cad/viewer/turntable.py collect {name}")
        print("render: submitted"); return
    say(f"Blender: {len(s['views']['elevations']) * s['views']['azimuths']} frames, {r['local_samples']} samples -> {run}/out")
    rc = sh(["blender", "-b", "-P", os.path.join(PLATFORM, "render", "render.py"), "--", os.path.join(run, "export"),
             os.path.join(run, "out"), str(r["local_samples"])] + render_args(s), log=os.path.join(run, "render.out"))
    if rc: die(f"blender FAILED: see {run}/render.out")
    print("render: OK")


def collect(name, s, opts):
    run = find_run(name, opts)
    job = open(os.path.join(run, "lane-job")).read().strip()
    rc = subprocess.run([SUBMIT, "status", job], capture_output=True, text=True).returncode
    if rc: die(f"lane job {job} is not done (status exit {rc}: 1 failed, 2 running)")
    os.makedirs(os.path.join(run, "out"), exist_ok=True)
    got = glob.glob(os.path.join(LANE, job, "out", "*.jpg"))
    for f in got: shutil.copy2(f, os.path.join(run, "out"))
    print(f"{len(got)} frames from {job} into {run}/out"); print("collect: OK")


def page_cfg(name, s, run):
    m = model_name(run)
    cfg = dict(s["page"], prefix=m, model=f"{m.replace('vt350-', '')}, {s['page'].get('model_note', name)}",
               elevations=s["views"]["elevations"], azimuths=s["views"]["azimuths"])
    cfg.pop("model_note", None)
    cfg.update({k: s["publish"][k] for k in ("blurb", "issue") if k in s["publish"]})
    p = os.path.join(run, "page.json"); json.dump(cfg, open(p, "w"), ensure_ascii=False, indent=1)
    return p


def stage(name, s, opts):
    run = find_run(name, opts); out = opts.get("--out") or os.path.join(run, "page")
    if sh(["python3", os.path.join(PLATFORM, "viewer", "turntable_page.py"), "stage", os.path.join(run, "out"),
           page_cfg(name, s, run), out]): die("stage failed")
    print(f"preview: python3 -m http.server -d {out}   (or publish the folder as a private artifact)")
    print("stage: OK")


def publish(name, s, opts):
    run = find_run(name, opts); p = s["publish"]
    licence_check(run, must_pass=True)
    if sh(["python3", os.path.join(PLATFORM, "viewer", "turntable_page.py"), "publish", os.path.join(run, "out"),
           page_cfg(name, s, run), os.path.join(ROOT, p["pages"]), p["page_name"], "--release", p["release"],
           "--upload", opts.get("--upload", "1")]): die("publish failed")
    print(f"next: commit {p['pages']}/ ({p['page_name']}.html, {p['page_name']}/turntable.json, assets.json, index.html) "
          f"on a branch; the site updates when it merges")
    print("publish: OK")


NEED = {"model": int, "extra": list, "views": {"azimuths": int, "elevations": list, "fill": float, "ev": float, "hide": list},
        "render": {"size": str, "look": str, "plastic_specular": float, "local_samples": int, "lane_samples": int,
                   "lane_notify": str},
        "page": {"title": str, "title_accent": str, "page_title": str, "foot": str, "credits": str, "links": list},
        "publish": {"pages": str, "page_name": str, "release": str, "issue": str, "blurb": str}}


def problems(name, s, need=NEED, where=""):
    out = []
    for k, t in need.items():
        if k not in s: out.append(f"{name}: no {where}{k}")
        elif isinstance(t, dict): out += problems(name, s[k], t, where + k + ".")
        elif not isinstance(s[k], t) and not (t is float and isinstance(s[k], int)):
            out.append(f"{name}: {where}{k} should be {t.__name__}")
    if not where:
        if s.get("selection") and not os.path.isfile(os.path.join(ROOT, s["selection"])):
            out.append(f"{name}: selection {s['selection']} doesn't exist")
        if not os.path.isdir(os.path.join(ROOT, s.get("publish", {}).get("pages", "-"))):
            out.append(f"{name}: publish.pages isn't a folder")
    return out


def check():
    found = []
    for p in sorted(glob.glob(os.path.join(HERE, "turntables", "*.json"))):
        n = os.path.basename(p)[:-5]; found += problems(n, json.load(open(p))); print(f"{n}: checked")
    for f in found: print(f)
    if found: return 1
    print("check: OK"); return 0


STEPS = {"export": export, "views": views, "render": render, "collect": collect, "stage": stage, "publish": publish}


def main(argv):
    if len(argv) < 2 or argv[0] not in list(STEPS) + ["all", "check"]:
        print("usage: cad/viewer/turntable.py {export|views|render|collect|stage|publish|all} <name> [--run DIR] "
              "[--model N] [--lane] [--upload 0]\n  settings: cad/viewer/turntables/<name>.json; steps: see the top of "
              "this file"); return 2
    step, name = argv[0], argv[1]
    if step == "check": return check()
    rest = argv[2:]; opts = {}
    while rest:
        k = rest.pop(0); opts[k] = rest.pop(0) if rest and not rest[0].startswith("--") else "1"
    s = settings(name)
    for st in (["export", "views", "render", "stage"] if step == "all" else [step]): STEPS[st](name, s, opts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
