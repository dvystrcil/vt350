#!/usr/bin/env python3
"""After a model change: re-derive the remixed STLs, refresh parts/printed, re-sweep, redraw the print area (#69).

  python3 cad/scripts/refresh.py <lite-N number> [--from STEP] [--dry-run]

Steps, in order. It stops at the first failure and names the step and its log:
  derive_stls      cad/scripts/derive_stls.py (FreeCAD, headless, read-only): remixes -> cad/derived/
  sync_printed     every parts/printed row copied from this repo (repo = dvystrcil/vt350, upstream_path set) whose
                   source changed is re-copied, and ONLY its sha256 cell in manifest.csv is rewritten (text edit: the
                   rest of the file, quoting and row order stay byte-identical)
  check_printed    parts/check-printed.py (must print "check-printed: OK")
  sweep            cad/scripts/sweep_toolhead.py on vt350-lite-<N>.FCStd (VT350_MODEL), ~11 min
  print_area       cad/scripts/print_area.py -> cad/data/print-area.svg
  test_print_area  cad/scripts/test_print_area.py

It never writes a model file (every step is read-only on the .FCStd) and never commits. Committing and the PR stay with
the caller. The summary (STLs changed, reach vs the committed sweep log, print area) goes to stdout and to
cad/data/logs/refresh.log. Every step is checked for a completion marker as well as its exit code, because a step can
crash and still exit 0.

Plain python3 (stdlib). FreeCAD comes from VT350_APP (default: the 26.3rc2 AppImage).
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
APP = os.environ.get("VT350_APP", "/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage")
MODELS = "/home/dan/Documents/VT350/vt350-lite-{}.FCStd"
THIS_REPO = "dvystrcil/vt350"
MANIFEST = "parts/printed/manifest.csv"
PRINTED = "parts/printed"
SWEEP_LOG = "cad/data/logs/sweep_toolhead.log"
ORDER = ["derive_stls", "sync_printed", "check_printed", "sweep", "print_area", "test_print_area"]


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


def plan(n, root=REPO, app=APP, start=None):
    if start is not None and start not in ORDER:
        raise ValueError(f"unknown step {start!r}; steps are {ORDER}")
    logs = os.path.join(root, "cad", "data", "logs")
    fc = app.split() + ["freecadcmd"]
    steps = [
        Step("derive_stls", cmd=fc + [os.path.join(root, "cad/scripts/derive_stls.py")], env=dict(VT350_REPO=root),
             log=os.path.join(logs, "refresh_derive_stls.out"),
             marker=r"done: (\d+) of \1 written", marker_in=os.path.join(logs, "derive_stls.log")),
        Step("sync_printed", fn=sync_printed),
        Step("check_printed", cmd=[sys.executable, os.path.join(root, "parts/check-printed.py"), "--root", root],
             log=os.path.join(logs, "refresh_check_printed.out"), marker=r"(?m)^check-printed: OK$"),
        Step("sweep", cmd=[sys.executable, os.path.join(root, "cad/scripts/sweep_toolhead.py")],
             env=dict(VT350_MODEL=MODELS.format(n), FREECADCMD=" ".join(fc), VT350_WORK=os.path.join(root, "cad/data")),
             log=os.path.join(logs, "refresh_sweep.out"),
             marker=r"(?m)done \(read-only, nothing saved\)$", marker_in=os.path.join(root, SWEEP_LOG)),
        Step("print_area", cmd=[sys.executable, os.path.join(root, "cad/scripts/print_area.py")],
             log=os.path.join(logs, "refresh_print_area.out"), marker=r"printable [\d.]+ x [\d.]+ mm"),
        Step("test_print_area", cmd=[sys.executable, os.path.join(root, "cad/scripts/test_print_area.py")],
             log=os.path.join(logs, "refresh_test_print_area.out"), marker=r"(?m)^Ran [1-9]\d* tests? in [\d.]+s\n\nOK$"),
    ]
    return steps[ORDER.index(start):] if start else steps


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
        with open(log, "w") as lf:
            rc = subprocess.call(s.cmd, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT, env=dict(os.environ, **s.env))
        if rc != 0:
            raise StepError(f"step {s.name} failed: exit {rc}; see {log}")
        if s.marker:
            mi = s.marker_in or log
            mi = mi if os.path.isabs(mi) else os.path.join(cwd, mi)
            body = open(mi, encoding="utf-8", errors="replace").read() if os.path.isfile(mi) else ""
            if not re.search(s.marker, body):
                raise StepError(f"step {s.name} failed: completion marker /{s.marker}/ not in {mi} (exit was 0); see {log}")


def _print_area():
    spec = importlib.util.spec_from_file_location("print_area", os.path.join(HERE, "print_area.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def summary(changed, sweep_log, prev_sweep_log, area_line=None):
    out = [f"{len(changed)} STL{'' if len(changed) == 1 else 's'} changed"]
    for c in changed:
        out.append(f"  {c['path']}: {c['old'][:12]} -> {c['new'][:12]}")
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
    if area_line:
        out.append("print area: " + area_line)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lite", type=int, help="model number N of vt350-lite-N.FCStd for the sweep")
    ap.add_argument("--from", dest="start", choices=ORDER, help="start at this step")
    ap.add_argument("--dry-run", action="store_true", help="print the steps and what sync_printed would change")
    a = ap.parse_args()
    steps = plan(a.lite, start=a.start)
    if a.dry_run:
        for s in steps:
            print(f"{s.name:16s} {' '.join(s.cmd) if s.cmd else 'sync_printed()'}  {s.env or ''}")
        for c in sync_printed(REPO, write=False):
            print(f"would re-copy {c['path']} ({c['old'][:12]} -> {c['new'][:12]})")
        return 0
    if any(s.name == "sweep" for s in steps) and not os.path.isfile(MODELS.format(a.lite)):
        print(f"refresh: FAILED: no model {MODELS.format(a.lite)}"); return 1
    prev = subprocess.run(["git", "-C", REPO, "show", f"HEAD:{SWEEP_LOG}"], capture_output=True, text=True).stdout
    t0 = time.time()
    try:
        run(steps, on_step=lambda s: print(f"[{time.time() - t0:6.0f}s] {s.name}", flush=True))
    except StepError as e:
        print(f"refresh: FAILED: {e}"); return 1
    by = {s.name: s for s in steps}
    changed = by["sync_printed"].result if "sync_printed" in by else []
    sweep = open(os.path.join(REPO, SWEEP_LOG), encoding="utf-8").read() if "sweep" in by else None
    area = None
    if "print_area" in by:
        area = open(by["print_area"].log, encoding="utf-8").read().strip().splitlines()[-1]
    s = summary(changed or [], sweep, prev, area)
    with open(os.path.join(REPO, "cad/data/logs/refresh.log"), "w", encoding="utf-8") as f:
        f.write(s + f"\nsteps: {', '.join(by)}; {time.time() - t0:.0f} s\nrefresh: OK\n")
    print(s); print("refresh: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
