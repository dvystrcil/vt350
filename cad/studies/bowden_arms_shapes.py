"""Every solved bundle shape of the bowden-arm study (vt350#312), for the reference page notes/reference/bowden-arms.html.
Plain python3 + numpy + scipy; read-only, opens no model. About 2 minutes on 10 workers.

    python3 cad/studies/bowden_arms_shapes.py     # writes notes/reference/bowden-arms/shapes.js

It reruns bowden_arms_reach.walk for the chosen design (cad/data/bowden_arms_design.json), gantry at today's height:
  - sliding loop: all 5 tools at EI 700 / 2000 / 7000;
  - sliding loop, cam stalled with the arm up: tools 1, 3, 5 at EI 2000;
  - tied loop: tools 1, 3, 5 at EI 2000, at the cut length its free-length stage finds (as run_modes does);
and the loop-spacing comparison (owner's question, 2026-11-25): the same design with the loops bunched around the
bed's centre X (pitch 60 and 30 mm) instead of each over its own roof exit, the roof exits unchanged.
Each shape is the roof span + head span as one polyline (X, Y, Z, 0.1 mm), with the bend radius at each node as the
study measures it (the clamps' ghost joints folded into the end nodes; the loop node = the turn through the loop)."""
import json, math, os, subprocess, sys
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import bowden_arms_reach as ba
lrod = ba.lrod

REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "notes", "reference", "bowden-arms", "shapes.js")
DESIGN = json.load(open(ba.DESIGN))["design"]
STEP = 34.0
CX = -245.0                                       # the bed's centre X at the lock, roughly (lock reach -416 .. -74)
SPACING = {"over each exit": None, "pitch 60": 60.0, "pitch 30": 30.0}


def loop_x(slot, pitch):
    return lrod.EXIT_X[slot] if pitch is None else CX + (slot - 3) * pitch


# --- the spacing variant: bowden_arms_reach.roof_span / walk (slide), with the loop at its own X --------------------
def roof_span_at(slot, EI, lx):
    a = lrod.exit_point(slot)
    out = []
    for P in (np.array([lx, *DESIGN["loop_up"]]), np.array([lx, *DESIGN["loop_down"]])):
        R = ba.Span(EI, ba.N_ROOF, g0=-lrod.EXIT_DIR)
        s = ba.solve_span(R, a, P, None, ba.TAKEUP, tb=(P - a) / np.linalg.norm(P - a))
        if s is None: return None
        X, LL = R.unpack(s[0], a, P, None)
        out.append((X, LL, ba.shape(R, X)))
    (Xu, Lu, su), (Xd, Ld, sd) = out
    return dict(L_up=Lu, L_down=Ld, minR=min(su["minR"], sd["minR"]), up=dict(X=Xu, **su), down=dict(X=Xd, **sd))


def walk_spaced(args):
    slot, EI, name = args
    lx = loop_x(slot, SPACING[name])
    P_down, P_up = np.array([lx, *DESIGN["loop_down"]]), np.array([lx, *DESIGN["loop_up"]])
    roof = roof_span_at(slot, EI, lx)
    key = (slot, name, EI, "now", "slide")
    pts = ba.path(slot, STEP)
    if roof is None: return key, dict(roof=None, walk=[dict(ok=False)] * len(pts), parked=dict(ok=False))
    R = ba.Span(EI, ba.N_HEAD, g1=ba.DOWN)
    def rec(P, b, prev, t1):
        s = ba.solve_span(R, P, b, None, ba.TAKEUP, prev, ta=t1)
        if s is None: return None, None
        X, LL = R.unpack(s[0], P, b, None); m = ba.shape(R, X, ba.LOCK_ZONE)
        return s[0], dict(ok=True, L=float(LL), minR_body=m["minR_body"], minR_lock=m["minR_zone"], lowest=m["lowest"],
                          ceiling_mm=m["ceiling_mm"], turn=ba.turn_deg(t1, m["t0"]), X=X.round(2).tolist())
    out, prev = [], None
    for b in pts:
        prev, r = rec(P_down, b, prev, roof["down"]["t1"])
        out.append(r or dict(ok=False))
    parked = rec(P_up, pts[0], None, roof["up"]["t1"])[1] or dict(ok=False)
    rs = dict(L_up=roof["L_up"], L_down=roof["L_down"], minR=roof["minR"], up=roof["up"]["X"].round(2).tolist(),
              down=roof["down"]["X"].round(2).tolist(), lowest=min(roof["up"]["lowest"], roof["down"]["lowest"]))
    return key, dict(roof=rs, walk=out, parked=parked)


# --- packing ---------------------------------------------------------------------------------------------------------
def radii(X, g0, g1):
    D = np.diff(X, axis=0); ds = np.linalg.norm(D, axis=1).mean()
    t = D / np.linalg.norm(D, axis=1)[:, None]
    ang = lambda u, v: max(math.acos(float(np.clip(u @ v, -1, 1))), 1e-9)
    R = np.full(len(X), np.inf)
    for i in range(1, len(X) - 1): R[i] = ds / ang(t[i - 1], t[i])
    if g0 is not None: R[0] = ds / ang(g0, t[0])
    if g1 is not None: R[-1] = ds / ang(t[-1], g1)
    return R


def pack(roof, head):
    roof, head = np.array(roof), np.array(head)
    Rr, Rh = radii(roof, -lrod.EXIT_DIR, None), radii(head, None, ba.DOWN)
    t_in = roof[-1] - roof[-2]; t_out = head[1] - head[0]
    a = max(math.acos(float(np.clip(t_in @ t_out / np.linalg.norm(t_in) / np.linalg.norm(t_out), -1, 1))), 1e-9)
    Rr[-1] = (np.linalg.norm(t_in) + np.linalg.norm(t_out)) / 2 / a
    P = np.vstack([roof, head[1:]]); R = np.concatenate([Rr, Rh[1:]])
    return dict(p=np.round(P, 1).ravel().tolist(), r=[round(float(min(x, 9999)), 1) for x in R])


def case(r, loop):
    walk = []
    for p in r["walk"]:
        if not p.get("ok"): walk.append(None); continue
        d = pack(r["roof"][loop], p["X"])
        d.update(head=p.get("head"), L=round(r["roof"]["L_" + loop] + p["L"], 1), rb=round(p["minR_body"], 1),
                 rl=round(p["minR_lock"], 1), low=round(p["lowest"] - ba.HEAD_Z, 1))
        walk.append(d)
    pk = None
    if r["parked"]["ok"]:
        pk = pack(r["roof"]["up"], r["parked"]["X"])
        pk.update(L=round(r["roof"]["L_up"] + r["parked"]["L"], 1), rb=round(r["parked"]["minR_body"], 1),
                  rl=round(r["parked"]["minR_lock"], 1), low=round(r["parked"]["lowest"] - ba.HEAD_Z, 1))
    return dict(walk=walk, parked=pk)


def main():
    main_jobs = [(s, DESIGN, e, "now", STEP, "slide", None, False) for s in range(1, 6) for e in ba.EIS]
    main_jobs += [(s, DESIGN, 2000.0, "now", STEP, "slide", None, True) for s in (1, 3, 5)]
    main_jobs += [(s, DESIGN, 2000.0, "now", STEP, "tied", None, False) for s in (1, 3, 5)]
    with Pool(int(os.environ.get("ARMS_WORKERS", "10"))) as pool:
        res = dict(pool.imap_unordered(ba.walk, main_jobs))
        tied = []
        for s in (1, 3, 5):
            r = res[(s, DESIGN["name"], 2000.0, "now", "tied")]
            ok = [p for p in r["walk"] if p.get("ok")]
            if ok and len(ok) == len(r["walk"]):
                tied.append((s, DESIGN, 2000.0, "now", STEP, "tied", max(p["L"] for p in ok), False))
        res.update(dict(pool.imap_unordered(ba.walk, tied)))
        spaced = dict(pool.imap_unordered(walk_spaced, [(s, e, n) for n in SPACING for s in range(1, 6) for e in ba.EIS]))

    cases = {}
    for k, r in res.items():
        slot, _, EI, _, mode = k[:5]
        if r["roof"] is None: raise SystemExit(f"no roof span for {k}")
        stuck = len(k) > 5
        cases[f"{mode}|{slot}|{int(EI)}" + ("|stuck" if stuck else "")] = case(r, "up" if stuck else "down")
    spacing = []
    for n, pitch in SPACING.items():
        for e in ba.EIS:
            rows = ba.summarise(spaced, dict(DESIGN, name=n), range(1, 6), "now", e, "slide")
            g = lambda key, f=min: f(r[key] for r in rows.values())
            spacing.append(dict(layout=n, loop_x=[round(loop_x(s, pitch)) for s in range(1, 6)], EI=int(e),
                                ok=ba.passes(rows, DESIGN, "now"), takeup=g("takeup_travel", max),
                                lock_R=g("lock_minR"), body_R=g("body_minR"), roof_R=g("roof_minR"),
                                touch_pct=g("touch_parked_pct", max), to_parked=g("to_parked_min")))
            print(spacing[-1], flush=True)
    sha = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    data = dict(design=DESIGN, ceil=lrod.Z_CEIL, head_z=ba.HEAD_Z, min_r=ba.MIN_R, lock_zone=ba.LOCK_ZONE,
                takeup=ba.TAKEUP, exit_x={s: lrod.EXIT_X[s] for s in range(1, 6)},
                exits={s: np.round(lrod.exit_point(s), 1).tolist() for s in range(1, 6)},
                lock_reach=[ba.lock_xy((ba.REACH_X[0], ba.REACH_Y[0])), ba.lock_xy((ba.REACH_X[1], ba.REACH_Y[1]))],
                cases=cases, spacing=spacing)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(f"// Solved bundle shapes for bowden-arms.html (vt350#312), from cad/studies/bowden_arms_shapes.py at {sha}.\n")
        f.write("window.ARMS_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT} ({os.path.getsize(OUT) / 1e6:.1f} MB, {len(cases)} cases)")


if __name__ == "__main__":
    main()
