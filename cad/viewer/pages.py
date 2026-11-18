#!/usr/bin/env python3
# The public pages of one subject (the toolhead, the printer), rebuilt from a lite-N by one command (vt350#220).
# cad/viewer/pages/<name>.json holds every choice: what to export, the render look, the turntable's cameras and text,
# and (optional) the live 3D viewer's GLB, compare render and text. Steps, in order:
#
#   cad/viewer/pages.py release <name> --model N [--lane]   all of the build below, then stage: the one to run for a
#                                                            new lite-N. With --lane it stops after submitting.
#   cad/viewer/pages.py export  <name> [--model N]   FreeCAD export (GUI under xvfb, read-only) + licence check
#   cad/viewer/pages.py views   <name>               turntable cameras + the viewer's "compare" camera
#   cad/viewer/pages.py glb     <name>               the viewer's GLB (+ the embedded-JSON copy for a private preview)
#   cad/viewer/pages.py render  <name> [--lane [--dry-run]]   every camera: Blender here (RUN/out), or the batch lane
#   cad/viewer/pages.py collect <name>               after a lane render: its frames into RUN/out
#   cad/viewer/pages.py stage   <name>               preview folders RUN/page-turntable, RUN/page-viewer
#   cad/viewer/pages.py publish <name> [--upload 0]  the notes/reference pages + release assets; commit after
#   cad/viewer/pages.py check   all                  every settings file has what the steps need (CI)
#
# Every step but release/export/check takes [--run DIR]; default the newest
# ~/Documents/VT350/renders/vt350-lite-<N>-<name>-pages-<UTC>/. Each step ends with "<step>: OK".
# publish refuses unless every exported part's licence is cleared (cad/viewer/licences.json). The release it uploads
# to is the settings' "release" for the run's lite-N (a new lite-N, a new release; old ones stay for old pages).
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
VIEWER = os.path.join(PLATFORM, "viewer")


def die(msg): print(f"pages: {msg}", file=sys.stderr); sys.exit(1)


def say(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sh(cmd, log=None, **kw):
    if log:
        with open(log, "w") as f: return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, **kw).returncode
    return subprocess.run(cmd, **kw).returncode


def settings(name):
    p = os.path.join(HERE, "pages", name + ".json")
    if not os.path.isfile(p): die(f"no settings {p} (have: {', '.join(sorted(os.listdir(os.path.dirname(p))))})")
    return json.load(open(p))


def find_run(name, opts):
    if "--run" in opts:
        r = os.path.abspath(os.path.expanduser(opts["--run"]))
        if not os.path.isdir(os.path.join(r, "export")): die(f"{r} has no export/")
        return r
    runs = sorted(glob.glob(os.path.join(DOCS, "renders", f"vt350-lite-*-{name}-pages-*")), key=os.path.getmtime)
    if not runs: die(f"no run for {name}; start with: cad/viewer/pages.py release {name} --model N")
    return runs[-1]


def prefix(run):
    """vt350-lite-N: the name render.py gives every image of this export."""
    m = json.load(open(os.path.join(run, "export", "scene.json"))).get("model") or os.path.basename(run)
    return os.path.splitext(os.path.basename(m))[0] if m.endswith(".FCStd") else re.match(r"(vt350-lite-\d+)", m).group(1)


def lite(run): return prefix(run).replace("vt350-", "")                     # lite-N


def n_frames(s): return len(s["turntable"]["elevations"]) * s["turntable"]["azimuths"] if "turntable" in s else 0


def licence_check(run, must_pass):
    rc = sh(["python3", os.path.join(VIEWER, "licence_check.py"), os.path.join(run, "export", "scene.json"), LICENCES,
             os.path.join(run, "licences.log")])
    if rc and must_pass: die(f"licence check FAILED: see {run}/licences.log; add rules to {LICENCES} (with sources)")
    if rc: say(f"licence check: not every part is cleared (fine for a private preview; publish will refuse): "
               f"{run}/licences.log")


# ---- steps ------------------------------------------------------------------------------------------------------

def export(name, s, opts):
    n = opts.get("--model") or str(s["model"])
    model = os.path.join(DOCS, f"vt350-lite-{n}.FCStd")
    if not os.path.isfile(model): die(f"no model {model}")
    run = os.path.join(DOCS, "renders", f"vt350-lite-{n}-{name}-pages-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}")
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
    return run


def views(name, s, opts):
    run = find_run(name, opts); exp = os.path.join(run, "export"); fv = os.path.join(VIEWER, "frame_view.py")
    hide = ["--hide", ",".join(s["hide"])] if s.get("hide") else []
    if "turntable" in s:
        t = s["turntable"]
        if sh(["python3", fv, exp, "--turntable", f"{t['azimuths']}x{len(t['elevations'])}", "--elevations",
               ",".join(map(str, t["elevations"])), "--fill", str(t["fill"]), "--ev", str(t["ev"])] + hide):
            die("frame_view (turntable) failed")
    if "viewer" in s:
        c = s["viewer"]["compare"]
        if sh(["python3", fv, exp, "--name", "compare", "--from", c["from"], "--lens", str(c["lens"]), "--fill",
               str(c["fill"]), "--ev", str(c["ev"]), "--add", "1"] + hide):
            die("frame_view (compare) failed")
    print("views: OK")


def glb(name, s, opts):
    if "viewer" not in s: print(f"{name} has no viewer; nothing to do"); print("glb: OK"); return
    run = find_run(name, opts); out = os.path.join(run, f"{prefix(run)}-{name}.glb")
    say(f"Blender: GLB -> {out}")
    if sh(["blender", "-b", "-P", os.path.join(VIEWER, "glb.py"), "--", os.path.join(run, "export"), out,
           "--decimate", str(s["viewer"]["decimate"]), "--json", "1"], log=os.path.join(run, "glb.out")):
        die(f"blender FAILED: see {run}/glb.out")
    if "glb-export: OK" not in open(os.path.join(run, "glb.out")).read(): die(f"no GLB; see {run}/glb.out")
    print(f"{out} ({os.path.getsize(out) / 1048576:.1f} MB)"); print("glb: OK")


def render_args(s):
    r = s["render"]
    return ["--size", r["size"], "--look", r["look"], "--plastic-specular", str(r["plastic_specular"])]


def render(name, s, opts):
    run = find_run(name, opts); r = s["render"]; n = n_frames(s) + (1 if "viewer" in s else 0)
    if "--lane" in opts:
        cmd = [SUBMIT, "blender", "--input", os.path.join(run, "export"), "--script",
               os.path.join(PLATFORM, "render", "render.py"), "--with", os.path.join(PLATFORM, "render", "colours.py"),
               "--with", COLOURS, "--name", f"{prefix(run)}-{name}", "--expect", "out/*.jpg", "--min-outputs", str(n),
               "--deadline", str(r.get("lane_deadline_s", 14400)), "--notify", r["lane_notify"]] + \
              (["--dry-run"] if "--dry-run" in opts else []) + ["--", str(r["lane_samples"])] + render_args(s)
        say("submit: " + shlex.join(cmd))
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(SUBMIT)))
        if "--dry-run" in opts: print(p.stdout.strip()); print("render: dry run, nothing submitted"); return
        print(p.stdout.strip()[-1500:])
        m = re.search(r"submitted (\S+)", p.stdout)
        if p.returncode or not m: die(f"lane submit failed: {p.stderr.strip()[-500:]}")
        open(os.path.join(run, "lane-job"), "w").write(m.group(1) + "\n")
        print(f"lane job {m.group(1)}: the result is a comment on {r['lane_notify']}; then: "
              f"cad/viewer/pages.py collect {name}, stage {name}")
        print("render: submitted"); return
    say(f"Blender: {n} images, {r['local_samples']} samples -> {run}/out")
    if sh(["blender", "-b", "-P", os.path.join(PLATFORM, "render", "render.py"), "--", os.path.join(run, "export"),
           os.path.join(run, "out"), str(r["local_samples"])] + render_args(s), log=os.path.join(run, "render.out")):
        die(f"blender FAILED: see {run}/render.out")
    print("render: OK")


def collect(name, s, opts):
    run = find_run(name, opts)
    job = open(os.path.join(run, "lane-job")).read().strip()
    rc = subprocess.run([SUBMIT, "status", job], capture_output=True, text=True).returncode
    if rc: die(f"lane job {job} is not done (status exit {rc}: 1 failed, 2 running)")
    os.makedirs(os.path.join(run, "out"), exist_ok=True)
    got = glob.glob(os.path.join(LANE, job, "out", "*.jpg"))
    for f in got: shutil.copy2(f, os.path.join(run, "out"))
    print(f"{len(got)} images from {job} into {run}/out"); print("collect: OK")


def turntable_cfg(name, s, run):
    t = s["turntable"]; pg = dict(t["page"])
    note = pg.pop("model_note", name)
    cfg = dict(pg, prefix=prefix(run), model=f"{lite(run)}, {note}", elevations=t["elevations"], azimuths=t["azimuths"],
               blurb=t["blurb"], issue=s["publish"]["issue"])
    p = os.path.join(run, "turntable-page.json"); json.dump(cfg, open(p, "w"), ensure_ascii=False, indent=1)
    return p


def viewer_cfg(name, s, run):
    scene = json.load(open(os.path.join(run, "export", "scene.json")))
    cam = next((v for v in scene.get("views", []) if v["name"] == "compare"), None)
    if not cam: die(f"no compare view in {run}/export/scene.json: run views {name}")
    v = s["viewer"]
    cfg = dict(v["page"], prefix=prefix(run), model=lite(run), blurb=v["blurb"], issue=s["publish"]["issue"],
               cam={k: cam[k] for k in ("pos", "look", "lens_mm")})
    p = os.path.join(run, "viewer-page.json"); json.dump(cfg, open(p, "w"), ensure_ascii=False, indent=1)
    return p


def viewer_files(name, run):
    glb_ = os.path.join(run, f"{prefix(run)}-{name}.glb"); comp = os.path.join(run, "out", f"{prefix(run)}-compare.jpg")
    for f in (glb_, comp):
        if not os.path.isfile(f): die(f"no {f}: run glb / render {name}")
    return glb_, comp


def stage(name, s, opts):
    run = find_run(name, opts)
    if "turntable" in s:
        out = os.path.join(run, "page-turntable")
        if sh(["python3", os.path.join(VIEWER, "turntable_page.py"), "stage", os.path.join(run, "out"),
               turntable_cfg(name, s, run), out]): die("turntable stage failed")
    if "viewer" in s:
        glb_, comp = viewer_files(name, run); out = os.path.join(run, "page-viewer")
        if sh(["python3", os.path.join(VIEWER, "viewer_page.py"), "stage", glb_[:-4] + ".gltf.json", comp,
               viewer_cfg(name, s, run), out]): die("viewer stage failed")
    print(f"preview: python3 -m http.server -d {run}/page-<turntable|viewer>   (or publish each as a private artifact)")
    print("stage: OK")


def publish(name, s, opts):
    run = find_run(name, opts); p = s["publish"]
    licence_check(run, must_pass=True)
    tag = p["release"].format(model=re.search(r"lite-(\d+)", prefix(run)).group(1))
    pages = os.path.join(ROOT, p["pages"]); up = ["--upload", opts.get("--upload", "1")]
    if "turntable" in s:
        if sh(["python3", os.path.join(VIEWER, "turntable_page.py"), "publish", os.path.join(run, "out"),
               turntable_cfg(name, s, run), pages, s["turntable"]["page_name"], "--release", tag] + up):
            die("turntable publish failed")
    if "viewer" in s:
        glb_, comp = viewer_files(name, run)
        if sh(["python3", os.path.join(VIEWER, "viewer_page.py"), "publish", glb_, comp, viewer_cfg(name, s, run),
               pages, s["viewer"]["page_name"], "--release", tag] + up):
            die("viewer publish failed")
    print(f"next: commit {p['pages']}/ on a branch and open a draft PR; the site updates when it merges")
    print("publish: OK")


def release(name, s, opts):
    run = export(name, s, opts); opts = dict(opts, **{"--run": run})
    views(name, s, opts); glb(name, s, opts); render(name, s, opts)
    if "--lane" in opts: return
    stage(name, s, opts)
    print(f"look at the previews, then: cad/viewer/pages.py publish {name}"); print("release: OK")


# ---- settings check (CI) -----------------------------------------------------------------------------------------

PAGE = {"title": str, "title_accent": str, "page_title": str, "credits": str, "links": list}
NEED = {"model": int, "extra": list, "hide": list,
        "render": {"size": str, "look": str, "plastic_specular": float, "local_samples": int, "lane_samples": int,
                   "lane_notify": str},
        "publish": {"pages": str, "release": str, "issue": str}}
NEED_TT = {"page_name": str, "blurb": str, "azimuths": int, "elevations": list, "fill": float, "ev": float,
           "page": dict(PAGE, foot=str)}
NEED_VW = {"page_name": str, "blurb": str, "decimate": float,
           "compare": {"from": str, "lens": float, "fill": float, "ev": float},
           "page": dict(PAGE, caption=str, about=str, compare_alt=str)}


def problems(name, s, need, where=""):
    out = []
    for k, t in need.items():
        if k not in s: out.append(f"{name}: no {where}{k}")
        elif isinstance(t, dict): out += problems(name, s[k], t, where + k + ".")
        elif not isinstance(s[k], t) and not (t is float and isinstance(s[k], int)):
            out.append(f"{name}: {where}{k} should be {t.__name__}")
    return out


def check_one(name, s):
    out = problems(name, s, NEED)
    if "turntable" not in s and "viewer" not in s: out.append(f"{name}: neither turntable nor viewer")
    if "turntable" in s: out += problems(name, s["turntable"], NEED_TT, "turntable.")
    if "viewer" in s: out += problems(name, s["viewer"], NEED_VW, "viewer.")
    if s.get("selection") and not os.path.isfile(os.path.join(ROOT, s["selection"])):
        out.append(f"{name}: selection {s['selection']} doesn't exist")
    if not os.path.isdir(os.path.join(ROOT, s.get("publish", {}).get("pages", "-"))):
        out.append(f"{name}: publish.pages isn't a folder")
    if "{model}" not in s.get("publish", {}).get("release", "{model}"):
        out.append(f"{name}: publish.release should contain {{model}} (one release per lite-N)")
    return out


def check():
    found, files = [], sorted(glob.glob(os.path.join(HERE, "pages", "*.json")))
    if not files: print(f"no settings in {HERE}/pages"); return 1
    for p in files:
        n = os.path.basename(p)[:-5]; found += check_one(n, json.load(open(p))); print(f"{n}: checked")
    for f in found: print(f)
    if found: return 1
    print("check: OK"); return 0


STEPS = {"export": export, "views": views, "glb": glb, "render": render, "collect": collect, "stage": stage,
         "publish": publish, "release": release}


def main(argv):
    if len(argv) < 2 or argv[0] not in list(STEPS) + ["check"]:
        print("usage: cad/viewer/pages.py {release|export|views|glb|render|collect|stage|publish|check} <name> "
              "[--model N] [--run DIR] [--lane [--dry-run]] [--upload 0]\n  settings: cad/viewer/pages/<name>.json; "
              "steps: see the top of this file"); return 2
    step, name = argv[0], argv[1]
    if step == "check": return check()
    rest = argv[2:]; opts = {}
    while rest:
        k = rest.pop(0); opts[k] = rest.pop(0) if rest and not rest[0].startswith("--") else "1"
    STEPS[step](name, settings(name), opts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
