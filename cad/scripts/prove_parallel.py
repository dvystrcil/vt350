#!/usr/bin/env python3
# prove_parallel: run lite-N passes headless (dry runs, never save) serially (VT350_WORKERS=1) and then in parallel
# (VT350_WORKERS=N), one after the other, and check the two logs are identical line for line apart from the
# "[  t.s]" timestamps, the JSON dumps identical, and the parallel run finished ("DRY RUN" line). Reports both wall
# times (#45).
#
#   python3 cad/scripts/prove_parallel.py --workers 3 lite28_filter_lips lite29_filter_cradle lite30_filter_ring
#
# Exit 0 only when every pass is identical and finished. Output: <out>/<pass>/{serial,parallel}/logs/... and
# <out>/summary.json. The worker count is still capped by free memory (litepool.worker_count): the pin is a ceiling.
# Long (lite-30 serial ~14 min): run it in the background. FREECADCMD overrides the command, like clashlib.
import argparse, difflib, json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get("FREECAD_APPIMAGE", "/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage")
DONE = "DRY RUN (headless): all checks passed, not saved"
TS = re.compile(r"^\[ *[0-9]+\.[0-9]s\] ")


def strip(text):
    return [TS.sub("", l, count=1) for l in text.splitlines()]


def finished(lines):
    return bool(lines) and lines[-1] == DONE


def run_one(name, workers, work, cmd, scripts):
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ, VT350_WORK=work, VT350_WORKERS=str(workers))
    t = time.time()
    with open(os.path.join(work, "stderr.txt"), "w") as err:
        subprocess.run(cmd + [os.path.join(scripts, name + ".py")], env=env, stdout=subprocess.DEVNULL, stderr=err)
    return time.time() - t


def prove(names, workers, out, cmd=None, scripts=HERE, log=print):
    cmd = cmd or os.environ.get("FREECADCMD", f"{APP} freecadcmd").split()
    passes = []
    for name in names:
        p = dict(name=name)
        runs = {}
        for tag, w in (("serial", 1), ("parallel", workers)):
            d = os.path.join(out, name, tag)
            p[f"{tag}_s"] = round(run_one(name, w, d, cmd, scripts), 2)
            lp, jp = os.path.join(d, "logs", name + ".log"), os.path.join(d, "logs", name + ".json")
            runs[tag] = (open(lp).read() if os.path.exists(lp) else None, open(jp).read() if os.path.exists(jp) else None)
            log(f"{name}: {tag} ({w} worker{'s' if w > 1 else ''}) {p[f'{tag}_s']:.1f} s")
        (ls, js), (lp_, jp_) = runs["serial"], runs["parallel"]
        if ls is None or lp_ is None:
            p.update(log_identical=False, json_identical=False, error="no log from the " + ("serial" if ls is None else "parallel") + " run")
        else:
            a, b = strip(ls), strip(lp_)
            p.update(lines=len(a), log_identical=a == b, json_identical=js == jp_,
                     diff=list(difflib.unified_diff(a, b, "serial", "parallel", lineterm=""))[:40])
            if not finished(b): p["error"] = f"parallel run not finished (last line {b[-1] if b else '-'!r})"
        p["ok"] = bool(p.get("log_identical") and p.get("json_identical") and "error" not in p)
        if p.get("parallel_s"): p["speedup"] = round(p["serial_s"] / p["parallel_s"], 2)
        passes.append(p)
    res = dict(ok=all(p["ok"] for p in passes), workers=workers, passes=passes)
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, "summary.json"), "w"), indent=1)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("passes", nargs="+", help="pass script names without .py, e.g. lite30_filter_ring")
    ap.add_argument("--workers", type=int, required=True, help="parallel worker count (a ceiling: memory caps it)")
    ap.add_argument("--out", default=None, help="output dir (default: a new temp dir)")
    ap.add_argument("--scripts", default=HERE)
    a = ap.parse_args()
    out = a.out or tempfile.mkdtemp(prefix="prove-parallel-")
    res = prove(a.passes, a.workers, out, scripts=a.scripts)
    for p in res["passes"]:
        state = "IDENTICAL" if p["ok"] else "DIFFERENT/FAILED: " + p.get("error", "see diff")
        print(f"{p['name']}: {p.get('lines', '?')} lines {state}; serial {p['serial_s']} s, parallel {p['parallel_s']} s"
              f" (x{p.get('speedup', '?')})")
        if not p["ok"]: print("\n".join(p.get("diff", [])))
    print(f"summary: {os.path.join(out, 'summary.json')}")
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
