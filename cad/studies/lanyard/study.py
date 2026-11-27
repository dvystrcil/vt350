"""vt350#218 lanyard + ceiling study (also #3, #243). Read-only: no model is opened or changed.
Route: lite-70's (each bundle clamped in its 45 deg roof clamp, Y 460 on the roof) under lite-69's ceiling (Z 679).
Sweep: head height (gantry as now / raised 10.3 mm, #243) x EI x lanyard case; each slot's head walks out of its dock
and over the whole reach in a serpentine, each solve starting from the last shape.
  1. free length, take-up T = 0.2 N, no lanyard: the tube length each position needs; the cut length of a slot's tube
     is the longest of these (as the flap study's "fixed" case).
  2. fixed (cut) length, with each lanyard case. Every head has its own lanyard, so the docked shapes of a case are
     the docked bundles the active one and its cord meet.
Needs numpy + scipy:  python study.py [out_dir]    (default cad/data/logs; writes lanyard_summary.json, and
lanyard_raw.json with the shapes, ~MBs, not committed)."""
import sys, os, json
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_v, "1")
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lrod
from multiprocessing import Pool

STEP = 34.0
RAISE = {"now": 0.0, "+10.3": 10.3}                     # #243: the gantry raise keeping 10 mm of overtravel
EIS = [700.0, 2000.0, 7000.0]                          # bracket: not measured yet (#3 asks for a cantilever test)
REEL_Y, REEL_Z = -62.0, 665.0                          # cord out of a reel on the front top 2040's inner face (Y -70)
CASES = {"none": (0.0, None), "0.5 N at 1/3": (0.5, 1 / 3), "1 N at 1/3": (1.0, 1 / 3), "2 N at 1/3": (2.0, 1 / 3),
         "1 N at 1/4": (1.0, 1 / 4), "1 N at 1/2": (1.0, 1 / 2)}   # pull, attach point as a fraction from the head
BUNDLE_W = 9.2                                         # PTFE 4 + cable 5.1 side by side
CORD_R = 0.5


def path(slot, dz):
    xs = np.arange(lrod.REACH_X[0], lrod.REACH_X[1] + 1e-6, STEP)
    ys = np.arange(lrod.REACH_Y[0], lrod.REACH_Y[1] + 1e-6, STEP)
    dx = lrod.DOCK_X[slot]
    P = [(dx, lrod.DOCK_Y)] + [(dx, y) for y in np.linspace(lrod.DOCK_Y, ys[0], 3)[1:]]
    xs_order = xs if abs(xs[0] - dx) < abs(xs[-1] - dx) else xs[::-1]
    P += [(x, ys[0]) for x in np.arange(dx, xs_order[0], -np.sign(dx - xs_order[0]) * STEP)[1:]]
    for j, y in enumerate(ys):
        for x in (xs_order if j % 2 == 0 else xs_order[::-1]):
            P.append((x, y))
    return [np.array([x, y, lrod.HEAD_Z + dz]) for x, y in P]


def make_rod(slot, EI, case):
    F, frac = CASES[case]
    if not F: return lrod.Rod(EI)
    n = lrod.N
    return lrod.Rod(EI, reel=[lrod.DOCK_X[slot], REEL_Y, REEL_Z], k=n - int(round(frac * n)), F=F)


def walk(args):
    h, EI, case, slot, Lfix = args
    R = make_rod(slot, EI, case)
    a = lrod.exit_point(slot)
    T = 0.2 if Lfix is None else 0.0
    out, v, prev_ok = [], None, False
    for b in path(slot, RAISE[h]):
        tries = ([v] if v is not None and prev_ok else []) + [R.initial(a, b, Lfix)]
        if v is not None and not prev_ok: tries.append(v)
        best = None
        for x0 in tries:
            x, ok, r = R.solve(a, b, x0, Lfix, T)
            if ok: best = (x, ok, r); break
            if best is None or r.fun < best[2].fun: best = (x, ok, r)
        x, ok, r = best
        v, prev_ok = x, ok
        X, LL = R.unpack(x, a, b, Lfix)
        m = lrod.metrics(R, X)
        f = R.head_force(x, a, b, Lfix, T) if ok else np.full(3, np.nan)
        m.update(ok=bool(ok), L=float(LL), head=b[:2].tolist(), f=f.round(4).tolist(), X=X.round(2).tolist())
        out.append(m)
    return (h, EI, case, slot), out


def summarise(res):
    rows = []
    for h in RAISE:
        for EI in EIS:
            for case in CASES:
                if not all((h, EI, case, s) in res for s in range(1, 6)): continue
                F, frac = CASES[case]
                docked = {s: np.array(res[(h, EI, case, s)][0]["X"]) for s in range(1, 6)}
                reel = {s: np.array([lrod.DOCK_X[s], REEL_Y, REEL_Z]) for s in range(1, 6)}
                per = {}
                for s in range(1, 6):
                    ps = res[(h, EI, case, s)]; ok = [p for p in ps if p["ok"]]
                    moving = ok[1:]
                    others = [o for o in range(1, 6) if o != s]
                    touch = sum(min(lrod.seg_dist(np.array(p["X"]), docked[o]) for o in others) < BUNDLE_W for p in moving)
                    fs = np.array([p["f"] for p in moving]); fm = np.linalg.norm(fs, axis=1)
                    r = dict(unsolved=len(ps) - len(ok), n=len(ps), L=round(ps[0]["L"]),
                             lowest=round(min(p["lowest"] for p in ok), 1), minR=round(min(p["minR"] for p in ok), 1),
                             ceiling_pct=round(100 * sum(p["ceiling_mm"] > 0 for p in ok) / len(ok)),
                             ceiling_max_mm=round(max(p["ceiling_mm"] for p in ok)),
                             docked_fz=round(ps[0]["f"][2], 3), docked_f=[round(c, 3) for c in ps[0]["f"]],
                             f_p50=round(float(np.percentile(fm, 50)), 2), f_max=round(float(fm.max()), 2),
                             touch_docked_pct=round(100 * touch / max(len(moving), 1)))
                    if F:
                        cross, zs = 0, []
                        for p in moving:
                            X = np.array(p["X"]); k = make_rod(s, EI, case).k
                            cord = np.array([reel[s], X[k]])
                            hit = False
                            for o in others:
                                if lrod.seg_dist(cord, docked[o]) < BUNDLE_W / 2 + CORD_R:
                                    hit = True
                                    D = docked[o]          # where on the docked bundle: its closest node's height
                                    t = np.linspace(0, 1, 50)[:, None]; C = reel[s] + t * (X[k] - reel[s])
                                    i = np.argmin(np.linalg.norm(D[:, None] - C[None], axis=2).min(axis=1)); zs.append(D[i, 2])
                            cross += hit
                        r.update(cord_min=round(min(p["cord"] for p in ok)), cord_max=round(max(p["cord"] for p in ok)),
                                 cord_deg_min=round(min(p["cord_deg"] for p in ok)),
                                 cord_lowest_z=round(min(p["cord_z"] for p in ok), 1),
                                 cord_cross_pct=round(100 * cross / max(len(moving), 1)),
                                 cord_cross_z=[round(min(zs)), round(max(zs))] if zs else None)
                    per[s] = r
                gaps = [round(lrod.seg_dist(docked[s], docked[s + 1]) - BUNDLE_W, 1) for s in range(1, 5)]
                rows.append(dict(raise_=h, EI=EI, case=case, docked_gaps=gaps, slots=per))
    return rows


if __name__ == "__main__":
    here = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/logs")
    res = {}
    with Pool(int(os.environ.get("LANYARD_WORKERS", "10"))) as pool:
        jobs = [(h, e, "none", s, None) for h in RAISE for e in EIS for s in range(1, 6)]
        free = {}
        for k, out in pool.imap_unordered(walk, jobs):
            free[k] = out; print("free", k, sum(not p["ok"] for p in out), "unsolved", flush=True)
        Lcut = {(h, e, s): max(p["L"] for p in free[(h, e, "none", s)] if p["ok"]) for h in RAISE for e in EIS for s in range(1, 6)}
        jobs = [(h, e, c, s, Lcut[(h, e, s)]) for h in RAISE for e in EIS for c in CASES for s in range(1, 6)]
        for k, out in pool.imap_unordered(walk, jobs):
            res[k] = out; print("cut", k, sum(not p["ok"] for p in out), "unsolved", flush=True)
    rows = summarise(res)
    for r in rows:
        for s in r["slots"]: r["slots"][s]["L_free_range"] = [round(min(p["L"] for p in free[(r["raise_"], r["EI"], "none", s)] if p["ok"])),
                                                              round(max(p["L"] for p in free[(r["raise_"], r["EI"], "none", s)] if p["ok"]))]
    json.dump(rows, open(f"{here}/lanyard_summary.json", "w"), indent=1)
    json.dump({"|".join(map(str, k)): v for k, v in res.items()}, open(f"{here}/lanyard_raw.json", "w"))
    for r in rows: print(json.dumps(r))
