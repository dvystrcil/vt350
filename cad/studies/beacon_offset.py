#!/usr/bin/env python3
"""How close to the nozzle can the Beacon sit? The Beacon body moved forward against each carried head (vt350#291).

    python3 cad/studies/beacon_offset.py [n_workers]       # read-only, never saves; log + JSON in $VT350_WORK

Owner, 2026-11-22: shrink the Beacon's y_offset (now 27.4: coil centre behind the nozzle) to about 14, with the dock
row moved forward, so the coil reaches the plate's front edge. This checks the first half of that: with a head on the
carriage (the head placed by the plan stage's pickup translation T, as sweep_toolhead.py and front_reach.py do), the
Beacon body is slid forward (model -Y) to each candidate offset and checked against every part of the carried head.
The carriage's own pocket is left out: it gets re-cut for whatever offset is chosen. The keep-out cone and docking are
separate checks.

Plain python3 driving freecadcmd workers through clashlib; the plan stage (sweep_toolhead.py, FreeCAD) gives the groups.
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE] + [p for p in (os.path.join(os.path.dirname(os.path.dirname(HERE)), d)
                                     for d in ("cad/scripts", "platform/freecad")) if os.path.isdir(p)]
import sweep_toolhead as st  # noqa: E402

BEACON = "Beacon"                                        # the Beacon body's object Name (lite24_beacon.py)
NOW = 27.4                                               # today's y_offset (beacon.cfg)
OFFSETS = (27.4, 22.0, 20.0, 18.0, 17.0, 16.0, 15.0, 14.0, 13.5, 13.0, 12.0, 10.0)
TOL = 0.01                                               # mm3
DOCK_OFFSET = 15.0                                       # the docking check's offset: the smallest that clears the head
SHUTTLE_Y = -26.96          # printer Y: MadMax's params_safe_shuttle_y (cad/klipper/toolchanger.cfg)
SHUTTLE_X, SHUTTLE_N = (4.0, 346.0), 18                  # printer X along the dock row
MODEL_FROM_PRINTER = (-420.0, 30.5)                      # cad/klipper/xy_mapping.json
DOCK_ZONE_Y = 120.0                                      # model Y: parts whose box starts in front of this are checked
STEP = os.path.expanduser("~/Documents/VT350/downloads/beacon/Beacon_RevH_Assm_Normal.STEP")  # Beacon's CAD (MIT)


def poses(T, offsets=OFFSETS):
    """{name: {group: translation}}: the head carried (at -T from its docked place, the carriage where the model has
    it) and the Beacon slid forward by NOW - offset."""
    tx, ty, tz = T
    return {f"{dy:.1f}": {"head": (-tx, -ty, -tz), "beacon": (0.0, -(NOW - dy), 0.0)} for dy in offsets}


def first_clear(found, offsets=OFFSETS):
    """The smallest offset with no contact, scanning down from today's; contacts below it don't count."""
    best = None
    for dy in sorted(offsets, reverse=True):
        if found.get(f"{dy:.1f}"): break
        best = dy
    return best


def main():
    import clashlib
    n = int(sys.argv[1]) if len(sys.argv) > 1 else clashlib.default_n()
    work = os.environ.get("VT350_WORK", os.path.join(os.path.dirname(HERE), "data"))
    os.makedirs(os.path.join(work, "logs"), exist_ok=True)
    log_f = open(os.path.join(work, "logs", "beacon_offset.log"), "w"); t0 = time.time()
    def log(*a):
        s = f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a); print(s, flush=True); log_f.write(s + "\n"); log_f.flush()
    os.environ["SWEEP_BOXES"] = "1"            # every leaf's box (front_reach.py does the same), for the dock zone
    plan = st.plan_stage(clashlib.FREECADCMD)
    log(f"model {st.MODEL} (read-only); Beacon offsets tried: {', '.join(f'{d:g}' for d in OFFSETS)} (today {NOW})")
    out = dict(model=os.path.basename(st.MODEL), now=NOW, heads={})
    for h, c in plan["carried"].items():
        head = [p for p in plan["heads"][h] if p != plan["tubes"][h]]
        res = clashlib.run(st.MODEL, groups={"head": head, "beacon": [BEACON]}, poses=poses(c["T"]), fixed=[], n=n,
                           tol=TOL, log=log)
        found = {}
        for r in res["results"]: found.setdefault(r["pose"], []).append((r["volume"], r["la"], r["lb"]))
        for e in res["errors"]: found.setdefault(e["pose"], []).append((-1.0, e["la"], e["lb"] + " [common() error]"))
        log(f"-- {h} head carried: the Beacon body against {len(head)} head parts")
        rows = []
        for dy in OFFSETS:
            hit = sorted(found.get(f"{dy:.1f}", []), reverse=True)
            rows.append(dict(offset=dy, contacts=[[round(v, 2), a, b] for v, a, b in hit[:5]]))
            log(f"   y_offset {dy:5.1f}: " + ("clear" if not hit else
                "; ".join(f"{a} x {b} {v:.1f} mm3" for v, a, b in hit[:3]) + (f" (+{len(hit) - 3} more)" if len(hit) > 3 else "")))
        fc = first_clear(found)
        log(f"   {h}: smallest clear offset tried: {fc}")
        out["heads"][h] = dict(rows=rows, smallest_clear=fc)
    cone(plan, out, log)
    out["docking"] = docking(plan, n, log)
    json.dump(out, open(os.path.join(work, "beacon_offset.json"), "w"), indent=1)
    log("done (read-only, nothing saved)")


def dock_poses(plan, dy=DOCK_OFFSET):
    """{pose: {group: translation}} with the Beacon at offset dy: each head's own dock pickup poses (sweep_toolhead's,
    the head on the carriage), and the bare carriage along the dock row at MadMax's shuttle Y (both heads docked)."""
    shift = (0.0, -(NOW - dy), 0.0)
    plus = lambda t: tuple(a + b for a, b in zip(t, shift))
    out = {}
    for h in plan["carried"]:
        for pid, tr in plan["poses"][h].items():
            if pid.startswith("dock pickup"):
                out[f"{h}: {pid}"] = {"head_" + h: tr["head"], "beacon": plus(tr["carriage"])}
    c = plan["carried"]["Left"]
    (nx, ny, _), (tx, ty, _) = c["nozzle"], c["T"]
    for i in range(SHUTTLE_N):
        x = SHUTTLE_X[0] + (SHUTTLE_X[1] - SHUTTLE_X[0]) * i / (SHUTTLE_N - 1)
        xm, ym = x + MODEL_FROM_PRINTER[0], SHUTTLE_Y + MODEL_FROM_PRINTER[1]
        out[f"bare carriage, shuttle X {x:.0f}"] = {"beacon": plus((xm - nx + tx, ym - ny + ty, 0.0))}
    return out


def docking(plan, n, log):
    """The Beacon at DOCK_OFFSET against everything but the carriage family, at the dock poses."""
    import clashlib
    groups = {"beacon": [BEACON]}
    for h in plan["carried"]:
        groups["head_" + h] = [p for p in plan["heads"][h] if p != plan["tubes"][h]]
    skip = set(plan["carriage"]) | set(plan["gantry"]) | set(plan["belt"]) | set(plan["bed"]) | set(plan["exclude"]) \
        | set(plan["tubes"].values()) | {BEACON}
    near = [o for o, b in plan["boxes"].items() if o not in skip and b[4] < DOCK_ZONE_Y and o not in
            {p for g in groups.values() for p in g}]
    ps = dock_poses(plan)
    res = clashlib.run(st.MODEL, groups=groups, poses=ps, fixed=near, n=n, tol=TOL, log=log,
                       skip_group_pairs=[("head_Left", "head_Right")])
    found = {}
    for r in res["results"]:
        if BEACON in (r["a"], r["b"]): found.setdefault(r["pose"], []).append((r["volume"], r["la"], r["lb"]))
    for e in res["errors"]:
        if BEACON in (e["a"], e["b"]): found.setdefault(e["pose"], []).append((-1.0, e["la"], e["lb"] + " [error]"))
    log(f"-- docking, the Beacon at y_offset {DOCK_OFFSET:g}: {len(ps)} poses against {len(near)} parts in the dock zone"
        " (both heads, the docks, the bed-edge probe)")
    rows = []
    for pid in ps:
        hit = sorted(found.get(pid, []), reverse=True)
        rows.append(dict(pose=pid, contacts=[[round(v, 2), a, b] for v, a, b in hit[:5]]))
        log(f"   {pid}: " + ("clear" if not hit else "; ".join(f"{a} x {b} {v:.1f} mm3" for v, a, b in hit[:3])))
    return rows


def cone(plan, out, log):
    """Beacon's keep-out solid (its STEP) on the coil axis, slid with the body, against each carried head's parts."""
    import clashlib, subprocess, tempfile
    root = os.path.dirname(os.path.dirname(HERE))
    with tempfile.TemporaryDirectory(prefix="beacon-cone-") as d:
        jp, op = os.path.join(d, "job.json"), os.path.join(d, "out.json")
        json.dump(dict(model=st.MODEL, step=STEP, now=NOW, offsets=list(OFFSETS), beacon=BEACON,
                       platform=os.path.join(root, "platform", "freecad"),
                       heads={h: dict(ids=[p for p in plan["heads"][h] if p != plan["tubes"][h]], T=c["T"])
                              for h, c in plan["carried"].items()}), open(jp, "w"))
        subprocess.run(clashlib.FREECADCMD + [os.path.join(HERE, "beacon_cone_fc.py")], cwd="/tmp",
                       env=dict(os.environ, BEACON_CONE_JOB=jp, BEACON_CONE_OUT=op),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(op): raise SystemExit("beacon_cone_fc.py wrote nothing")
        res = json.load(open(op))
    if "fatal" in res: raise SystemExit("beacon_cone_fc.py failed:\n" + res["fatal"])
    for s in res["notes"]: log("keep-out:", s)
    for h, rows in res["heads"].items():
        log(f"-- {h} head carried: parts inside Beacon's keep-out solid (its STEP: no metal there)")
        for r in rows:
            log(f"   y_offset {r['offset']:5.1f}: " + ("nothing inside" if not r["inside"] else
                "; ".join(f"{lab} {v:.1f} mm3" for v, lab in r["inside"][:5])
                + (f" (+{len(r['inside']) - 5} more)" if len(r["inside"]) > 5 else "")))
        out["heads"][h]["keep_out"] = rows


if __name__ == "__main__":
    main()
