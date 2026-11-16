"""vt350#3 flap + guide study. Sweep: layouts x EI x slack mode; each slot's head walks a serpentine over the reach,
out of its dock first. Needs numpy + scipy (a venv: uv venv && uv pip install numpy scipy).
  python study.py [out_dir]     # default: cad/data/logs; writes flap_guide_summary.json (+ flap_guide_raw.json,
                                # the shapes, ~MBs: not committed)
About 10 min on 10 workers (laptop, 2026-11-16)."""
import sys, os, json
# one BLAS thread per worker: numpy's default (one per core, in every worker) took the first run to load 107 on 12 cores
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_v, "1")
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rod
from multiprocessing import Pool

GZ = 685.0
X_IN = {"L": -380.0, "R": -110.0}            # flap inner edges: 100 mm flaps off the inner wall faces (-480, -10)
SIDE = {1: "L", 2: "L", 3: "R", 4: "R", 5: "R"}   # the loop study's split, 1-2 / 3-5
LAYOUTS = {
    "A one station": {1: 187.5, 2: 212.5, 3: 175.0, 4: 200.0, 5: 225.0},
    "B two stations": {1: 110.0, 2: 290.0, 3: 110.0, 4: 200.0, 5: 290.0},
}
EIS = [700.0, 2000.0, 7000.0, 11000.0]
BUNDLE_W = 9.2                                # PTFE 4 + cable 5.1 side by side
STEP = 34.0


def path(slot):
    xs = np.arange(rod.REACH_X[0], rod.REACH_X[1] + 1e-6, STEP)
    ys = np.arange(rod.REACH_Y[0], rod.REACH_Y[1] + 1e-6, STEP)
    dx = rod.DOCK_X[slot]
    P = [(dx, rod.DOCK_Y)]
    # out of the dock: forward to the first row, then along it to the serpentine start (nearest column)
    P += [(dx, y) for y in np.linspace(rod.DOCK_Y, ys[0], 3)[1:]]
    xs_order = xs if abs(xs[0] - dx) < abs(xs[-1] - dx) else xs[::-1]
    P += [(x, ys[0]) for x in np.arange(dx, xs_order[0], -np.sign(dx - xs_order[0]) * STEP)[1:]]
    for j, y in enumerate(ys):
        for x in (xs_order if j % 2 == 0 else xs_order[::-1]):
            P.append((x, y))
    return [np.array([x, y, rod.HEAD_Z]) for x, y in P]


def guide(layout, slot):
    return np.array([X_IN[SIDE[slot]], LAYOUTS[layout][slot], GZ])


def walk(args):
    layout, EI, mode, slot, Lfix = args
    R = rod.Rod(EI)
    a = guide(layout, slot)
    L = Lfix if mode == "fixed" else None
    T = 0.0 if mode == "fixed" else float(mode[2:])
    out, v, prev_ok = [], None, False
    for b in path(slot):
        tries = ([v] if v is not None and prev_ok else []) + [R.initial(a, b, L)]
        if v is not None and not prev_ok: tries.append(v)
        best = None
        for x0 in tries:
            x, ok, r = R.solve(a, b, x0, L, T)
            if ok: best = (x, ok, r); break
            if best is None or r.fun < best[2].fun: best = (x, ok, r)
        x, ok, r = best
        v, prev_ok = x, ok
        X, LL = R.unpack(x, a, b, L)
        m = rod.metrics(X); m.update(ok=bool(ok), L=float(LL), head=b[:2].tolist(), X=X.round(2).tolist())
        out.append(m)
    return (layout, EI, mode, slot), out


def summarise(res):
    rows = []
    for layout in LAYOUTS:
        for EI in EIS:
            for mode in MODES:
                if not all((layout, EI, mode, s) in res for s in range(1, 6)): continue
                docked = {s: np.array(res[(layout, EI, mode, s)][0]["X"]) for s in range(1, 6)}
                allp = [p for s in range(1, 6) for p in res[(layout, EI, mode, s)]]
                okp = [p for p in allp if p["ok"]]
                cross, mincl = [], []
                for s in range(1, 6):
                    ps = [p for p in res[(layout, EI, mode, s)][1:] if p["ok"]]
                    n = 0; mc = 1e9
                    for p in ps:
                        X = np.array(p["X"])
                        d = min(rod.seg_dist(X, docked[o]) for o in range(1, 6) if o != s)
                        mc = min(mc, d); n += d < BUNDLE_W
                    cross.append(round(100 * n / max(len(ps), 1))); mincl.append(round(mc - BUNDLE_W, 1))
                gaps = [round(rod.seg_dist(docked[s], docked[s + 1]) - BUNDLE_W, 1) for s in range(1, 5)]
                Ls = [p["L"] for p in okp]; lows = [p["lowest"] for p in okp]
                rows.append(dict(layout=layout, EI=EI, mode=mode, unsolved=len(allp) - len(okp), n=len(allp),
                                 L_min=round(min(Ls)), L_max=round(max(Ls)), lowest=round(min(lows), 1),
                                 lowest_p5=round(float(np.percentile(lows, 5)), 1),
                                 docked_lowest=round(min(float(docked[s][:, 2].min()) for s in docked), 1),
                                 minR=round(min(p["minR"] for p in okp), 1),
                                 guide_max_deg=round(max(p["guide_deg_from_down"] for p in okp)),
                                 docked_gaps=gaps, cross_pct=cross, min_clear_to_docked=mincl))
    return rows


MODES = ["T=0.2", "T=0.5", "fixed"]

if __name__ == "__main__":
    here = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/logs")
    res = {}
    with Pool(int(os.environ.get("FLAP_WORKERS", "10"))) as pool:
        jobs = [(l, e, m, s, None) for l in LAYOUTS for e in EIS for m in MODES[:2] for s in range(1, 6)]
        for k, out in pool.imap_unordered(walk, jobs):
            res[k] = out; print("done", k, sum(not p["ok"] for p in out), "unsolved", flush=True)
        # fixed: nothing pulls slack back -> the span keeps the longest length the T=0.2 walk pulled out
        jobs = [(l, e, "fixed", s, max(p["L"] for p in res[(l, e, "T=0.2", s)] if p["ok"]))
                for l in LAYOUTS for e in EIS for s in range(1, 6)]
        for k, out in pool.imap_unordered(walk, jobs):
            res[k] = out; print("done", k, sum(not p["ok"] for p in out), "unsolved", flush=True)
    rows = summarise(res)
    json.dump(rows, open(f"{here}/flap_guide_summary.json", "w"), indent=1)
    json.dump({"|".join(map(str, k)): v for k, v in res.items()}, open(f"{here}/flap_guide_raw.json", "w"))
    for r in rows: print(json.dumps(r))
