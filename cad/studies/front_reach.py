#!/usr/bin/env python3
"""How far forward can each carried head's nozzle go, at each X, before it hits the docked heads? (vt350#291)

    python3 cad/studies/front_reach.py [n_workers]         # read-only, never saves; log + JSON in $VT350_WORK

sweep_toolhead.py's Y reach is only the gantry's hard stops, and its X reach is measured at the bed's Y centre. With
five docks along the front, the nozzle's real front limit depends on X. This finds it per X by bisection in Y:

  - the carried head (+ its MadMax plate), the carriage (Beacon on it) and the bed at the top (its front parts: the
    nozzle-offset probe) move; every other head stays docked. The gantry and belts are left out (they only move in Y,
    and their fits with the carriage are the same at every pose).
  - Only the fixed parts whose box the head + carriage can sweep into are checked (a box filter, so it's exact: a part
    outside the swept box can't overlap).
  - Per X: nozzle Y from Y_LO (the print square's front edge less the Beacon's Y offset: where the nozzle must be for
    the coil to scan the edge) to Y_HI; bisection to RES. It assumes one boundary per X (blocked in front, clear
    behind); the log names any X where the coarse points contradict that.

Plain python3 driving freecadcmd workers through clashlib; the plan stage (sweep_toolhead.py, FreeCAD) gives the groups.
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE] + [p for p in (os.path.join(os.path.dirname(os.path.dirname(HERE)), d)
                                     for d in ("cad/scripts", "platform/freecad")) if os.path.isdir(p)]
import sweep_toolhead as st  # noqa: E402

BEACON_DY = 27.4          # Beacon coil centre - nozzle, Y (Klipper [beacon] y_offset; lite24_beacon.py, lite-26)
X_RANGE = (-416.0, -74.0)  # the nozzle's X reach (sweep_toolhead.log, tightest head per side)
X_N = 35                  # X positions across it (~10 mm apart)
Y_HI = (80.0, 140.0)      # clear-side bracket; the second is tried only where the first is blocked
RES = 2.0                 # bisection stops when blocked..clear is this close (mm)
TOL = 0.01                # mm3


def swept_box(boxes, names, dx, dy0, dy1, dz=0.0):
    """The box the named solids cover when translated by (dx in dx-range, dy in dy0..dy1, dz)."""
    bs = [boxes[n] for n in names if n in boxes]
    return (min(b[0] for b in bs) + dx[0], min(b[1] for b in bs) + dy0, min(b[2] for b in bs) + dz,
            max(b[3] for b in bs) + dx[1], max(b[4] for b in bs) + dy1, max(b[5] for b in bs) + dz)


def hits(b, s, margin=0.5):
    return all(b[i] <= s[i + 3] + margin and b[i + 3] >= s[i] - margin for i in range(3))


def next_round(state, res=RES):
    """state {x: [blocked_y, clear_y]} -> {x: y to try next} (midpoints of brackets wider than res)."""
    return {x: (b + c) / 2 for x, (b, c) in state.items() if b is not None and c is not None and c - b > res}


def classify(res, tries, base):
    """clashlib result -> {x: [(volume, label_a, label_b)]} of contacts not in the baseline. A pair whose common()
    failed counts as a contact (volume -1): an error can't prove the pose clear, so it never makes one clear."""
    got = {x: [] for x in tries}
    for r in res["results"]:
        x = float(r["pose"].split()[0])
        if (r["a"], r["b"]) not in base: got[x].append((r["volume"], r["la"], r["lb"]))
    for e in res["errors"]:
        x = float(e["pose"].split()[0])
        if (e["a"], e["b"]) not in base: got[x].append((-1.0, e["la"], e["lb"] + " [common() error]"))
    return got


def update(state, tried, blocked):
    """Record one round: tried {x: y}, blocked {x: bool}."""
    for x, y in tried.items():
        if blocked[x]: state[x][0] = y
        else: state[x][1] = y


def main():
    import clashlib
    n = int(sys.argv[1]) if len(sys.argv) > 1 else clashlib.default_n()
    work = os.environ.get("VT350_WORK", os.path.join(os.path.dirname(HERE), "data"))
    os.makedirs(os.path.join(work, "logs"), exist_ok=True)
    log_f = open(os.path.join(work, "logs", "front_reach.log"), "a"); t0 = time.time()
    cache_p = os.path.join(work, "front_reach_cache.json")   # every pose checked so far: a re-run skips them
    cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
    def log(*a):
        s = f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a); print(s, flush=True); log_f.write(s + "\n"); log_f.flush()
    os.environ["SWEEP_BOXES"] = "1"
    plan = st.plan_stage(clashlib.FREECADCMD)
    log(f"model {st.MODEL} (read-only)")
    boxes, lab = plan["boxes"], plan["labels"]
    out = dict(model=os.path.basename(st.MODEL), beacon_dy=BEACON_DY, res=RES, heads={})
    for h, c in plan["carried"].items():
        (nx, ny, nz), (tx, ty, tz), dz_top = c["nozzle"], c["T"], c["dz_top"]
        x_lo, y_lo, x_hi, y_hi = c["square"]
        y_lo_scan = y_lo - BEACON_DY
        other = [o for o in plan["carried"] if o != h][0]
        head, car = plan["heads"][h], plan["carriage"]
        moving = set(head) | set(car)
        # head + carriage cover this box over the whole scan (carried: head moves tc - T, carriage tc)
        dxr = (X_RANGE[0] - nx, X_RANGE[1] - nx)                   # nozzle X shift from the docked nozzle
        sw = swept_box(boxes, head, dxr, y_lo_scan - ny, Y_HI[1] - ny, -tz)
        swc = swept_box(boxes, car, (X_RANGE[0] - nx + tx, X_RANGE[1] - nx + tx), y_lo_scan - ny + ty, Y_HI[1] - ny + ty)
        sweep = tuple(min(a, b) for a, b in zip(sw[:3], swc[:3])) + tuple(max(a, b) for a, b in zip(sw[3:], swc[3:]))
        skip = set(plan["gantry"]) | set(plan["belt"]) | moving | {plan["tubes"][h]} | set(plan["exclude"])
        bed = [b for b in plan["bed"] if hits([v + (dz_top if i in (2, 5) else 0) for i, v in enumerate(boxes[b])], sweep)]
        fixed = [o for o in boxes if o not in skip and o not in set(plan["bed"]) and hits(boxes[o], sweep)]
        log(f"{h} carried ({other} and the slot heads docked): swept box X {sweep[0]:.1f}..{sweep[3]:.1f} "
            f"Y {sweep[1]:.1f}..{sweep[4]:.1f} Z {sweep[2]:.1f}..{sweep[5]:.1f}; checked against {len(fixed)} fixed "
            f"and {len(bed)} bed solids (of {len(boxes)})")
        groups = dict(bed=bed, carriage=car, head=head)

        def pose(x, y):
            tc = (x - nx + tx, y - ny + ty, 0.0)
            if not (st.Y_TRAVEL[0] - 1e-6 <= tc[1] <= st.Y_TRAVEL[1] + 1e-6): raise RuntimeError(f"Y {y:.2f} out of travel")
            return {"bed": (0, 0, dz_top), "carriage": tc, "head": (tc[0] - tx, tc[1] - ty, tc[2] - tz)}

        def check(tries, tag):
            """tries {x: y} -> {x: [(volume, a, b)]} of overlaps not in the baseline."""
            key = lambda x, y: f"{h} {x:.2f} {y:.2f}"
            todo = {x: y for x, y in tries.items() if key(x, y) not in cache}
            if todo:
                poses = {f"{x:.2f} {y:.2f}": pose(x, y) for x, y in todo.items()}
                res = clashlib.run(st.MODEL, groups=groups, poses=poses, fixed=fixed, n=n, tol=TOL, log=log,
                                   skip_group_pairs=[("carriage", "head")])
                for e in res["errors"]: log(f"   ERROR (counted as a contact) {e['pose']}: {e['la']} x {e['lb']}: {e['error']}")
                for x, v in classify(res, todo, base).items(): cache[key(x, todo[x])] = v
                json.dump(cache, open(cache_p, "w"))
            log(f"   {h} {tag}: {len(tries)} poses ({len(tries) - len(todo)} from the cache)")
            return {x: [tuple(c) for c in cache[key(x, y)]] for x, y in tries.items()}

        base = set()
        cx, cy = (x_lo + x_hi) / 2, (y_lo + y_hi) / 2
        b0 = clashlib.run(st.MODEL, groups=groups, poses={"centre": pose(cx, cy)}, fixed=fixed, n=n, tol=TOL, log=log,
                          skip_group_pairs=[("carriage", "head")])
        base = {(r["a"], r["b"]) for r in b0["results"]}
        log(f"{h} baseline (nozzle at the centre {cx:.1f}, {cy:.1f}): {len(base)} overlapping pairs, ignored after: "
            + ("; ".join(sorted(f"{lab.get(a, a)} x {lab.get(b, b)}" for a, b in base)) or "none"))
        xs = [round(X_RANGE[0] + (X_RANGE[1] - X_RANGE[0]) * i / (X_N - 1), 2) for i in range(X_N)]
        state = {x: [None, None] for x in xs}
        what = {}
        lo = check({x: y_lo_scan for x in xs}, "Y_LO")
        hi = check({x: Y_HI[0] for x in xs}, "Y_HI")
        for x in xs:
            what[x] = lo[x]
            state[x] = [y_lo_scan if lo[x] else None, None if hi[x] else Y_HI[0]]
            if not lo[x]: state[x] = [None, y_lo_scan]
            if not lo[x] and hi[x]: log(f"   {h} X {x}: NOT ONE BOUNDARY: clear at Y {y_lo_scan:.2f}, blocked at {Y_HI[0]}")
        far = [x for x in xs if state[x][1] is None]
        if far:
            hi2 = check({x: Y_HI[1] for x in far}, "Y_HI2")
            for x in far:
                if not hi2[x]: state[x] = [Y_HI[0], Y_HI[1]]
                else: log(f"   {h} X {x}: still blocked at Y {Y_HI[1]}: " + "; ".join(f"{a} x {b}" for _, a, b in hi2[x][:4]))
        rnd = 0
        while True:
            tries = next_round(state)
            if not tries: break
            rnd += 1
            got = check(tries, f"round {rnd}")
            update(state, tries, {x: bool(v) for x, v in got.items()})
            for x, v in got.items():
                if v: what[x] = v
            log(f"   {h} round {rnd}: {len(tries)} poses, {sum(1 for v in got.values() if v)} blocked")
        rows = []
        log(f"-- {h}: nozzle front limit per X (model coordinates; blocked .. clear, the first hit at the blocked Y)")
        for x in xs:
            b, c = state[x]
            first = sorted(what.get(x, []), reverse=True)[:3]
            rows.append(dict(x=x, blocked=b, clear=c))
            log(f"   {h} X {x:8.2f}: front limit Y {('%.2f' % c) if c is not None else 'none'}"
                + (f" (blocked at {b:.2f}: " + "; ".join(f"{a} x {bb} {v:.1f} mm3" for v, a, bb in first) + ")" if b is not None else " (clear at the scan's front end)"))
        out["heads"][h] = rows
    json.dump(out, open(os.path.join(work, "front_reach.json"), "w"), indent=1)
    log("done (read-only, nothing saved)")


if __name__ == "__main__":
    main()
