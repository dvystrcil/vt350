#!/usr/bin/env python3
"""After a model change: re-derive the remixed STLs, refresh parts/printed, re-sweep, redraw the print area (#69).

  python3 cad/scripts/refresh.py <lite-N> [--notify OWNER/REPO#N] [--dry-run]   # lane: submit, then the repo writes
  python3 cad/scripts/refresh.py <lite-N> --collect [CHAIN-ID]                   # after the chain's comment
  python3 cad/scripts/refresh.py <lite-N> --local [--from STEP] [--dry-run]      # every step on this machine

By default (homelab#2257) the model-reading steps run on the cluster's batch lane: the homelab chain vt350-refresh
(homelab bin/gpu-batch-submit.py, VT350_GPU_BATCH_SUBMIT) runs part_index, sweep, z_sweep and print_area on max-01,
read-only, and posts ONE comment on --notify when it ends. This machine submits it first, then runs only the steps whose
output is committed while the chain runs: derive_stls (the lane's STLs are never committed: max-01 tessellates them
differently, homelab#1961), sync_printed, check_printed and orca_projects. After the comment, --collect copies the chain's logs, the
part index and print-area.svg into the repo (refusing a failed or unfinished chain, another model's, or a log without
its completion marker, before writing anything) and runs test_print_area. On lite-32 the local run took 4790 s, z_sweep
alone 3219 s. --local runs every step here, as before (the lane down, or no NFS share).

Steps of --local, in order. It stops at the first failure and names the step and its log:
  part_index       platform/freecad/part_index.py (FreeCAD, headless, read-only, #90): the per-part box index beside
                   vt350-lite-<N>.FCStd AND each companion the same pass saved (any other .FCStd in the folder saved
                   within COMPANION_S of it, never another lite-N: lite-28 wrote vt350-filter-2 in the same minute).
                   Skips a model whose <model>.parts.json is fresh
  derive_stls      cad/scripts/derive_stls.py (FreeCAD, headless, read-only): remixes -> cad/derived/
  sync_printed     every parts/printed row copied from this repo (repo = dvystrcil/vt350, upstream_path set) whose
                   source changed is re-copied, and ONLY its sha256 cell in manifest.csv is rewritten (text edit: the
                   rest of the file, quoting and row order stay byte-identical)
  check_printed    platform/parts/check-printed.py (must print "check-printed: OK")
  orca_projects    platform/parts/orca_projects.py parts/slice/sets.json (#217, needs the Orca flatpak): regenerates
                   the OrcaSlicer projects (parts/slice/projects/) whose STLs, quantities or presets changed, so a
                   PR that changes a part carries its plate ("orca-projects: OK")
  sweep            cad/studies/sweep_toolhead.py on vt350-lite-<N>.FCStd (VT350_MODEL), ~11 min
  z_sweep          cad/studies/z_sweep.py (FreeCAD, headless, read-only, #82): the bed's Z travel, both ends, by
                   boolean contact, with the documents the model's envelopes name (envelope_docs) -> cad/data/logs/z_sweep.log
  print_area       cad/studies/print_area.py -> cad/data/print-area.svg
  test_print_area  cad/studies/test_print_area.py

It never writes a model file (every step is read-only on the .FCStd) and never commits. Committing and the PR stay with
the caller. The summary (STLs changed, reach vs the committed sweep log, Z travel vs the committed z_sweep log, print area) goes to stdout and to
cad/data/logs/refresh.log. Every step is checked for a completion marker as well as its exit code, because a step can
crash and still exit 0, and a marker read from a separate log only counts if this run rewrote that log.

Plain python3 (stdlib). FreeCAD comes from VT350_APP (default: the 26.3rc2 AppImage).
"""
import argparse
import csv
import glob
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
APP = os.environ.get("VT350_APP", "/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage")
MODELS_DIR = "/home/dan/Documents/VT350"
MODELS = MODELS_DIR + "/vt350-lite-{}.FCStd"
COMPANION_S = 600             # a pass saves its documents seconds apart (finish()); 10 min still excludes the next pass
THIS_REPO = "dvystrcil/vt350"
# Where each step's tool lives (vt350#122: generic tools under platform/, the VT350's own studies under cad/studies/).
TOOLS = {"part_index": "platform/freecad/part_index.py", "derive_stls": "cad/scripts/derive_stls.py",
         "check_printed": "platform/parts/check-printed.py", "orca_projects": "platform/parts/orca_projects.py", "sweep": "cad/studies/sweep_toolhead.py",
         "z_sweep": "cad/studies/z_sweep.py", "print_area": "cad/studies/print_area.py",
         "test_print_area": "cad/studies/test_print_area.py"}
# Code folders, searched after this file's own folder (where a gpu-batch pod stages everything flat).
CODE_DIRS = ("cad/scripts", "cad/studies", "platform/freecad")
MANIFEST = "parts/printed/manifest.csv"
PRINTED = "parts/printed"
SETS = "parts/slice/sets.json"                                      # the print sets for orca_projects (#217)
SWEEP_LOG = "cad/data/logs/sweep_toolhead.log"
Z_LOG = "cad/data/logs/z_sweep.log"
ORDER = ["part_index", "derive_stls", "sync_printed", "check_printed", "orca_projects", "sweep", "z_sweep", "print_area", "test_print_area"]
# The batch lane (homelab#2257): homelab's submit command and the laptop path of its NFS work share.
SUBMIT = os.environ.get("VT350_GPU_BATCH_SUBMIT", "/home/dan/Code/homelab/bin/gpu-batch-submit.py")
WORK_ROOT = os.environ.get("GPU_BATCH_WORK_ROOT", "/mnt/nfs/media/gpu-batch")
LANE_LOCAL = ["derive_stls", "sync_printed", "check_printed", "orca_projects"]      # what the laptop still runs (their output is committed)
SUBMIT_LOG = "cad/data/logs/refresh_submit.out"
CHAIN_RE = r"(?m)^started chain vt350-refresh (\S+)$"              # its first line (pinned by a homelab test)
# The chain's sweep job runs the sweep, the index and z_sweep under one deadline (lite-32 on the laptop: 1114 s + 3219 s;
# lite-30 on max-01: 23.5 min). homelab caps z_sweep's own step at 1 h within it. 7200 s stopped being enough at lite-50:
# the toolhead sweep alone took 92.3 min (lite-50) and 116.6 min (lite-51) on max-01, leaving z_sweep 1542 s and 50 s
# (vt350#204). 3.5 h = the slower sweep + z_sweep's 1 h cap + the index, with ~30 min to spare.
SWEEP_DEADLINE_S = 12600
SWEEP_DONE = r"(?m)done \(read-only, nothing saved\)$"
Z_DONE = r"(?m)^\[ *\d+\.\ds\] z_sweep: done \(read-only, nothing saved\)$"
INDEX_DONE = r"(?m)part_index: done \(\d+ models\)$"
# What --collect copies: (job, path in the job dir, repo path, a regex its text must match; {n} = the lite number).
PULL = [("sweep", "out/logs/sweep_toolhead.log", SWEEP_LOG, SWEEP_DONE),
        ("sweep", "out/logs/sweep_toolhead.log", SWEEP_LOG, r"(?m)^\[ *[\d.]+s\] model \S*/vt350-lite-{n}\.FCStd "),
        ("sweep", "out/logs/z_sweep.log", Z_LOG, Z_DONE),
        ("sweep", "out/logs/z_sweep.log", Z_LOG, r"(?m)^\[ *[\d.]+s\] model \S*/vt350-lite-{n}\.FCStd "),
        ("sweep", "out/logs/z_sweep.json", "cad/data/logs/z_sweep.json", r"/vt350-lite-{n}\.FCStd\b"),
        ("sweep", "out/logs/part_index.log", "cad/data/logs/part_index.log", INDEX_DONE),
        ("area", "out/print-area.svg", "cad/data/print-area.svg", r"Printable area on vt350-lite-{n}\b")]


class StepError(RuntimeError):
    pass


class Step:
    """cmd (argv) or fn (callable(root) -> anything); stdout+stderr go to log; marker = regex that must appear in
    marker_in (default: the step's own log) for the step to count as finished"""

    def __init__(self, name, cmd=None, fn=None, log=None, marker=None, marker_in=None, env=None):
        self.name, self.cmd, self.fn, self.log, self.marker, self.marker_in = name, cmd, fn, log, marker, marker_in
        self.env = env or {}
        self.result = None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sync_printed(root, write=True):
    """re-copy in-repo parts whose source changed; return [{path, src, old, new}] in manifest order"""
    mpath = os.path.join(root, MANIFEST)
    with open(mpath, newline="", encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines(keepends=True)
    header = next(csv.reader([lines[0]]))
    changed, out = [], [lines[0]]
    for ln in lines[1:]:
        cells = next(csv.reader(io.StringIO(ln)), None)
        if not cells or len(cells) != len(header):
            raise StepError(f"{MANIFEST}: can't split this row into {len(header)} cells (multi-line cell?): {ln[:80]!r}")
        r = dict(zip(header, cells))
        if r["repo"] != THIS_REPO or not r["upstream_path"] or not r["path"]:
            out.append(ln); continue
        src = os.path.join(root, r["upstream_path"]); dst = os.path.join(root, PRINTED, r["path"])
        if not os.path.isfile(src):
            raise StepError(f"{MANIFEST}: {r['path']}: source {r['upstream_path']} is missing")
        new = sha256(src)
        if new == r["sha256"] and os.path.isfile(dst) and sha256(dst) == new:
            out.append(ln); continue
        if ln.count(r["sha256"]) != 1:
            raise StepError(f"{MANIFEST}: {r['path']}: its sha256 doesn't occur exactly once in its row")
        changed.append(dict(path=r["path"], src=r["upstream_path"], old=r["sha256"], new=new))
        out.append(ln.replace(r["sha256"], new, 1))
        if write:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
    if changed and write:
        with open(mpath, "w", newline="", encoding="utf-8") as f:
            f.write("".join(out))
    return changed


def companions(model):
    """The other .FCStd files in model's folder saved within COMPANION_S of it, sorted; never another vt350-lite-N."""
    if not os.path.isfile(model): return []
    d, t = os.path.dirname(model), os.path.getmtime(model)
    out = []
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if not f.endswith(".FCStd") or p == model or re.match(r"vt350-lite-\d", f): continue
        if abs(os.path.getmtime(p) - t) <= COMPANION_S: out.append(p)
    return out


def _code_path():
    """This file's folder, then the checkout's code folders that exist."""
    dirs = [HERE] + [os.path.join(REPO, d) for d in CODE_DIRS]
    return [d for i, d in enumerate(dirs) if os.path.isdir(d) and os.path.realpath(d) not in
            [os.path.realpath(x) for x in dirs[:i]]]


def _module(name):
    path = next(p for p in (os.path.join(d, f"{name}.py") for d in _code_path()) if os.path.isfile(p))
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def envelope_docs(model):
    """The documents model's envelopes name ("Filter envelope (contents in vt350-filter-3.FCStd)"), beside it: what
    z_sweep opens with the model, so what the batch lane must ship (#82). Read from the file, no FreeCAD."""
    sys.path[:0] = _code_path()
    return _module("z_sweep").envelope_paths(model)


def plan(n, root=REPO, app=APP, start=None, models=MODELS_DIR):
    if start is not None and start not in ORDER:
        raise ValueError(f"unknown step {start!r}; steps are {ORDER}")
    logs = os.path.join(root, "cad", "data", "logs")
    fc = app.split() + ["freecadcmd"]
    model = os.path.join(models, f"vt350-lite-{n}.FCStd")
    steps = [
        Step("part_index", cmd=fc + [os.path.join(root, TOOLS["part_index"])],
             env=dict(VT350_INDEX_MODELS=":".join([model] + companions(model)), VT350_WORK=os.path.join(root, "cad/data")),
             log=os.path.join(logs, "refresh_part_index.out"),
             marker=INDEX_DONE, marker_in=os.path.join(logs, "part_index.log")),
        Step("derive_stls", cmd=fc + [os.path.join(root, TOOLS["derive_stls"])], env=dict(VT350_REPO=root),
             log=os.path.join(logs, "refresh_derive_stls.out"),
             marker=r"done: (\d+) of \1 written", marker_in=os.path.join(logs, "derive_stls.log")),
        Step("sync_printed", fn=sync_printed),
        Step("check_printed", cmd=[sys.executable, os.path.join(root, TOOLS["check_printed"]), "--root", root],
             log=os.path.join(logs, "refresh_check_printed.out"), marker=r"(?m)^check-printed: OK$"),
        Step("orca_projects", cmd=[sys.executable, os.path.join(root, TOOLS["orca_projects"]),
                                   os.path.join(root, SETS)],
             log=os.path.join(logs, "refresh_orca_projects.out"), marker=r"(?m)^orca-projects: OK$"),
        Step("sweep", cmd=[sys.executable, os.path.join(root, TOOLS["sweep"])],
             env=dict(VT350_MODEL=model, FREECADCMD=" ".join(fc), VT350_WORK=os.path.join(root, "cad/data")),
             log=os.path.join(logs, "refresh_sweep.out"),
             marker=SWEEP_DONE, marker_in=os.path.join(root, SWEEP_LOG)),
        Step("z_sweep", cmd=fc + [os.path.join(root, TOOLS["z_sweep"])],
             env=dict(VT350_MODEL=model, FREECADCMD=" ".join(fc), VT350_WORK=os.path.join(root, "cad/data")),
             log=os.path.join(logs, "refresh_z_sweep.out"),
             marker=Z_DONE, marker_in=os.path.join(root, Z_LOG)),
        Step("print_area", cmd=[sys.executable, os.path.join(root, TOOLS["print_area"])],
             log=os.path.join(logs, "refresh_print_area.out"), marker=r"printable [\d.]+ x [\d.]+ mm"),
        Step("test_print_area", cmd=[sys.executable, os.path.join(root, TOOLS["test_print_area"])],
             log=os.path.join(logs, "refresh_test_print_area.out"), marker=r"(?m)^Ran [1-9]\d* tests? in [\d.]+s\n\nOK$"),
    ]
    return steps[ORDER.index(start):] if start else steps


def lane_plan(n, root=REPO, app=APP, models=MODELS_DIR, notify=None, submit=SUBMIT, z_change_ok=False, fresh=False):
    """Submit the vt350-refresh chain for vt350-lite-<n>, then the steps whose output is committed (homelab#2257)."""
    model = os.path.join(models, f"vt350-lite-{n}.FCStd")
    cmd = [sys.executable, submit, "chain", "vt350-refresh", "--model", model, "--models-dir", models, "--vt350", root,
           "--sweep-deadline", str(SWEEP_DEADLINE_S)] + (["--notify", notify] if notify else []) \
        + (["--z-change-ok"] if z_change_ok else []) + (["--fresh"] if fresh else [])
    sub = Step("submit", cmd=cmd, log=os.path.join(root, SUBMIT_LOG), marker=CHAIN_RE)
    return [sub] + [s for s in plan(n, root=root, app=app, models=models) if s.name in LANE_LOCAL]


def chain_id(submit_out):
    m = re.search(CHAIN_RE, submit_out)
    if not m:
        raise StepError(f"no 'started chain vt350-refresh <id>' line in the submit output: {submit_out[-300:]!r}")
    return m.group(1)


def last_chain_id(root=REPO):
    p = os.path.join(root, SUBMIT_LOG)
    if not os.path.isfile(p):
        raise StepError(f"no {SUBMIT_LOG}: name the chain (--collect <chain-id>)")
    return chain_id(open(p, encoding="utf-8").read())


def collect(n, cid, root=REPO, work_root=WORK_ROOT):
    """Copy a finished vt350-refresh chain's outputs into the repo, where the local steps write them. Everything is
    checked before anything is written. -> {copied: [repo paths], index: [.parts.json paths], printable: [w, d]}"""
    if not cid.startswith(f"vt350-lite-{n}-"):
        raise StepError(f"chain {cid} is not a chain of vt350-lite-{n}")
    for job in ("derive", "sweep", "area"):
        d = os.path.join(work_root, f"{cid}-{job}")
        try:
            st = json.load(open(os.path.join(d, "status.json"), encoding="utf-8"))
        except FileNotFoundError:
            raise StepError(f"chain {cid} not finished: no status.json in {d} (wait for its comment)") from None
        except (OSError, ValueError) as e:
            raise StepError(f"chain {cid}: can't read {d}/status.json: {e}") from None
        if st.get("state") != "succeeded":
            raise StepError(f"chain {cid}: {d} {st.get('state')}: {st.get('reason')}")
    texts, copies = {}, {}
    for job, rel, dest, pattern in PULL:
        src = os.path.join(work_root, f"{cid}-{job}", rel)
        if src not in texts:
            try:
                texts[src] = open(src, encoding="utf-8").read()
            except OSError as e:
                raise StepError(f"chain {cid}: no {rel} in {cid}-{job}: {e}") from None
        if not re.search(pattern.format(n=n), texts[src]):
            raise StepError(f"chain {cid}: {src} does not match /{pattern.format(n=n)}/")
        copies[dest] = src
    area = os.path.join(work_root, f"{cid}-area", "out/refresh-summary.json")
    try:
        printable = json.load(open(area, encoding="utf-8"))["printable"]
    except (OSError, ValueError, KeyError) as e:
        raise StepError(f"chain {cid}: no printable area in {area}: {e}") from None
    index = sorted(glob.glob(os.path.join(work_root, f"{cid}-sweep", "out/index/*.parts.json")))
    if not index:
        raise StepError(f"chain {cid}: no part index in {cid}-sweep/out/index/")
    for dest, src in copies.items():
        shutil.copyfile(src, os.path.join(root, dest))
    return dict(copied=list(copies), index=index, printable=printable)


def collect_plan(index, root=REPO, models=MODELS_DIR):
    """After collect(): the chain's part index beside the models it describes (only onto the same bytes), and the
    print-area test against the copied log and SVG."""
    logs = os.path.join(root, "cad", "data", "logs")
    adopt = Step("adopt_index", cmd=[sys.executable, os.path.join(root, TOOLS["part_index"]), "--adopt", "--models", models,
                                     *index], log=os.path.join(logs, "refresh_adopt_index.out"))
    return [adopt] + [s for s in plan(0, root=root, models=models) if s.name == "test_print_area"]


def run(steps, cwd=REPO, root=REPO, on_step=None):
    for s in steps:
        if on_step: on_step(s)
        if s.fn is not None:
            try:
                s.result = s.fn(root)
            except StepError as e:
                raise StepError(f"step {s.name} failed: {e}") from None
            continue
        log = s.log if os.path.isabs(s.log) else os.path.join(cwd, s.log)
        os.makedirs(os.path.dirname(log), exist_ok=True)
        t0 = time.time()
        with open(log, "w") as lf:
            rc = subprocess.call(s.cmd, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT, env=dict(os.environ, **s.env))
        if rc != 0:
            raise StepError(f"step {s.name} failed: exit {rc}; see {log}")
        if s.marker:
            mi = s.marker_in or log
            mi = mi if os.path.isabs(mi) else os.path.join(cwd, mi)
            body = open(mi, encoding="utf-8", errors="replace").read() if os.path.isfile(mi) else ""
            if body and mi != log and os.path.getmtime(mi) < t0 - 1:
                raise StepError(f"step {s.name} failed: {mi} was not written by this run (an old log; exit was 0); see {log}")
            if not re.search(s.marker, body):
                raise StepError(f"step {s.name} failed: completion marker /{s.marker}/ not in {mi} (exit was 0); see {log}")


def _print_area():
    return _module("print_area")


def stl_lines(changed):
    return [f"{len(changed)} STL{'' if len(changed) == 1 else 's'} changed"] + \
        [f"  {c['path']}: {c['old'][:12]} -> {c['new'][:12]}" for c in changed]


def summary(changed, sweep_log, prev_sweep_log, area_line=None, index=None, z_log=None, prev_z_log=None):
    out = []
    if index:
        out.append("part index: " + ", ".join(f"{os.path.basename(m)[:-len('.FCStd')]} {st}" for m, st in index))
    if changed is not None:                         # None: a --collect summary (the STLs were the submit run's)
        out += stl_lines(changed)
    if sweep_log is None:
        out.append("sweep not run")
    else:
        pa = _print_area(); r = pa.parse_reach(sweep_log)
        line = f"reach ({r['model']}, tightest head per side): X {r['x_min']} .. {r['x_max']}"
        p = None
        if prev_sweep_log:
            try: p = pa.parse_reach(prev_sweep_log)
            except ValueError: p = None
        if p: line += f" (was {p['x_min']} .. {p['x_max']})"
        line += f", Y {r['y_min']} .. {r['y_max']}"
        if p: line += f" (was {p['y_min']} .. {p['y_max']}, {p['model']})"
        out.append(line)
    if z_log is None:
        out.append("z sweep not run")
    else:
        ct = _module("contact"); z = ct.parse(z_log)
        line = (f"Z travel: plate top {z['z_lower_limit_mm']:.2f} .. {z['z_upper_limit_mm']:.2f}, "
                f"print height {z['print_height_mm']:.2f}, full travel {z['z_travel_mm']:.2f} "
                f"(Klipper Z {z['klipper_position_max_mm']:.2f} .. {z['z_negative_limit_mm']:.2f})")
        try: w = ct.parse(prev_z_log or "", keys=ct.KEYS[:3])     # a log from before #82 AC6 has only these
        except ValueError: w = None
        if w:
            try: t = f", full travel {ct.parse(prev_z_log)['z_travel_mm']:.2f}"
            except ValueError: t = ""
            line += f" (was {w['z_lower_limit_mm']:.2f} .. {w['z_upper_limit_mm']:.2f}, {w['print_height_mm']:.2f}{t})"
        out.append(line)
    if area_line:
        out.append("print area: " + area_line)
    return "\n".join(out)


def load_tool(name):
    """import one of TOOLS as a module, from where TOOLS says it lives"""
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, TOOLS[name]))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lite", type=int, help="model number N of vt350-lite-N.FCStd for the sweep")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--local", action="store_true", help="run every step on this machine (no batch lane)")
    mode.add_argument("--collect", nargs="?", const="", metavar="CHAIN-ID",
                      help="copy a finished chain's outputs into the repo (default: the last one submitted)")
    ap.add_argument("--notify", help="lane: OWNER/REPO#N the chain comments on when it ends")
    ap.add_argument("--z-change-ok", action="store_true",
                    help="lane: print height may move > 5 mm from the committed z_sweep.log (the chain's z-guard "
                         "stops it otherwise, before the 2 h toolhead sweep; homelab gpu-batch-submit)")
    ap.add_argument("--fresh", action="store_true",
                    help="lane: rerun every step; by default a step whose inputs match an earlier chain's is reused")
    ap.add_argument("--from", dest="start", choices=ORDER, help="--local: start at this step")
    ap.add_argument("--dry-run", action="store_true", help="print the steps and what sync_printed would change")
    a = ap.parse_args(argv)
    if a.start and not a.local:
        ap.error("--from needs --local (the lane run is always: submit, derive_stls, sync_printed, check_printed, orca_projects)")
    return a


def _show(steps):
    for s in steps:
        print(f"{s.name:16s} {' '.join(s.cmd) if s.cmd else 'sync_printed()'}  {s.env or ''}")
    for c in sync_printed(REPO, write=False):
        print(f"would re-copy {c['path']} ({c['old'][:12]} -> {c['new'][:12]})")


def _git_head(rel):
    return subprocess.run(["git", "-C", REPO, "show", f"HEAD:{rel}"], capture_output=True, text=True).stdout


def _index_status(models):
    pi = load_tool("part_index")
    return [(m, pi.status(m)) for m in models]


def _finish(s, steps, t0):
    with open(os.path.join(REPO, "cad/data/logs/refresh.log"), "w", encoding="utf-8") as f:
        f.write(s + f"\nsteps: {', '.join(steps)}; {time.time() - t0:.0f} s\nrefresh: OK\n")
    print(s); print("refresh: OK")
    return 0


def main_collect(a):
    t0 = time.time()
    model = MODELS.format(a.lite)
    try:
        cid = a.collect or last_chain_id()
        prev, prev_z = _git_head(SWEEP_LOG), _git_head(Z_LOG)
        got = collect(a.lite, cid)
        print(f"collected chain {cid}: " + ", ".join(got["copied"]), flush=True)
        steps = collect_plan(got["index"])
        run(steps, on_step=lambda s: print(f"[{time.time() - t0:6.0f}s] {s.name}", flush=True))
    except StepError as e:
        print(f"refresh: FAILED: {e}"); return 1
    sweep = open(os.path.join(REPO, SWEEP_LOG), encoding="utf-8").read()
    z_log = open(os.path.join(REPO, Z_LOG), encoding="utf-8").read()
    area = f"vt350-lite-{a.lite}: printable {got['printable'][0]} x {got['printable'][1]} mm (chain {cid})"
    s = summary(None, sweep, prev, area, _index_status([model] + companions(model)), z_log, prev_z)
    return _finish(s, ["collect " + cid] + [x.name for x in steps], t0)


def main_lane(a):
    steps = lane_plan(a.lite, notify=a.notify, z_change_ok=a.z_change_ok, fresh=a.fresh)
    if a.dry_run:
        _show(steps); return 0
    if not os.path.isfile(MODELS.format(a.lite)):
        print(f"refresh: FAILED: no model {MODELS.format(a.lite)}"); return 1
    if not a.notify:
        print("refresh: no --notify: the chain posts no comment; read its status.json files once, later")
    t0 = time.time()
    try:
        run(steps, on_step=lambda s: print(f"[{time.time() - t0:6.0f}s] {s.name}", flush=True))
    except StepError as e:
        print(f"refresh: FAILED: {e}"); return 1
    cid = last_chain_id()
    by = {s.name: s for s in steps}
    s = "\n".join(stl_lines(by["sync_printed"].result or []) + [
        f"part_index, sweep, z_sweep, print_area: on chain {cid}",
        f"after its comment: python3 cad/scripts/refresh.py {a.lite} --collect {cid}"])
    return _finish(s, list(by), t0)


def main(argv=None):
    a = parse_args(argv)
    if a.collect is not None:
        return main_collect(a)
    if not a.local:
        return main_lane(a)
    steps = plan(a.lite, start=a.start)
    if a.dry_run:
        _show(steps); return 0
    if any(s.name in ("part_index", "sweep", "z_sweep") for s in steps) and not os.path.isfile(MODELS.format(a.lite)):
        print(f"refresh: FAILED: no model {MODELS.format(a.lite)}"); return 1
    prev, prev_z = _git_head(SWEEP_LOG), _git_head(Z_LOG)
    t0 = time.time()
    try:
        run(steps, on_step=lambda s: print(f"[{time.time() - t0:6.0f}s] {s.name}", flush=True))
    except StepError as e:
        print(f"refresh: FAILED: {e}"); return 1
    by = {s.name: s for s in steps}
    changed = by["sync_printed"].result if "sync_printed" in by else []
    sweep = open(os.path.join(REPO, SWEEP_LOG), encoding="utf-8").read() if "sweep" in by else None
    z_log = open(os.path.join(REPO, Z_LOG), encoding="utf-8").read() if "z_sweep" in by else None
    area = None
    if "print_area" in by:
        area = open(by["print_area"].log, encoding="utf-8").read().strip().splitlines()[-1]
    index = _index_status(by["part_index"].env["VT350_INDEX_MODELS"].split(":")) if "part_index" in by else None
    s = summary(changed or [], sweep, prev, area, index, z_log, prev_z)
    return _finish(s, list(by), t0)


if __name__ == "__main__":
    sys.exit(main())
