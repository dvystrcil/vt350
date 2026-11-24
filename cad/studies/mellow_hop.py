#!/usr/bin/env python3
"""How high do the toolchange moves and the Beacon scan pass over the Mellow MultiHead Zero? (vt350#291)

    python3 cad/studies/mellow_hop.py            # read-only, never saves; ~10 min (plan stage + one freecadcmd)

lite-78 put the Zero on the bed's front edge, low: ball centre printer (50, -9.5), ball top 1.0 above the PEI (Nudge).
MadMax's toolchange lifts Z only +1 (madmax/toolchanger.cfg dropoff_gcode: `G0 Z{cur_z + 1.0}`), and the pickup runs
at that Z until it restores the position. On the first layer (0.2) the change runs with the nozzle 1.2 above the
print surface. The Beacon's scan flies the nozzle at Z 2 (trigger_distance), and its front turns run past the plate's
front edge. Which part passes over the Zero, and how close?

The moves, all in printer XY (cad/klipper/xy_mapping.json), each with the nozzle Z it runs at:
  - T0's dropoff and pickup: the carried Left head along X detach (15.30) between Y safe_toolhead (31.04) and attach
    (-85.96), and into the dock (X 15.30 -> 10.30) (cad/klipper/toolchanger.cfg);
  - a dropoff that starts at the front of the plate: from (x, 2.5) straight to (15.30, 31.04), x 7..100 every 3 mm,
    and the mirror move, the restore from (x, 31.04) to (x, 2.5);
  - the empty carriage: T0's dock moves (X 10.30, Y -85.96 -> -43.96) and the shuttle at Y -43.96 between the docks;
  - T1 (the Right head) along its X detach (334.70), for completeness;
  - the Beacon scan (cad/motion/beacon_scan.py: Beacon's own path, overscan and all) with T0 carried, at Z 2, for the
    Beacon at today's y_offset 27.4 and at lite-79's 15 (the Beacon slid in the model: a what-if, nothing saved);
  - printing the plate's front edge on the first layer (Z 0.2), as a reference.
The clearance is the gap between the lowest part over the Zero (head, carriage, Beacon) and the Zero's top
(ball, bushing, bracket) as the move passes. Rough parts: the hot end's heat block is a stand-in (lite-73); the
tools' Z offsets (gcode_z_offset) shift the empty carriage by the active tool's offset, not modelled.
Output: $VT350_WORK/mellow_hop.json and logs/mellow_hop.log.
"""
import json, os, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, os.path.join(ROOT, "cad", "scripts"), os.path.join(ROOT, "platform", "freecad"),
                os.path.join(ROOT, "cad", "motion"), os.path.join(ROOT, "platform", "klipper")]
import sweep_toolhead as st  # noqa: E402
import beacon_scan as bs  # noqa: E402
import pinmap  # noqa: E402

BALL = (50.0, -9.5)                  # printer XY of the ball centre (lite-78, mellow_edge_reach.py)
PROBE_PREFIX = "Nozzle offset probe"  # the Zero's group (lite-78; sweep_toolhead.rides_with_bed)
FIRST_LAYER = 0.2
HOP = 1.0                            # madmax/toolchanger.cfg dropoff_gcode
TC_Z = FIRST_LAYER + HOP
SCAN_Z = bs.TRIGGER_Z                # 2.0
FRONT_Y = 2.5                        # the printable front edge, printer Y (print_area.py: Y 2.5 ... 342.69)
OFFSETS = (27.4, 15.0)
BEACON = "Beacon"                    # the Beacon's object Name (lite24_beacon.py)


def cfg():
    c = pinmap.load(os.path.join(ROOT, "cad", "klipper", "toolchanger.cfg")).sections
    m = json.load(open(os.path.join(ROOT, "cad", "klipper", "xy_mapping.json")))
    tc = c["toolchanger"]
    tools = {t: dict(park=float(c[f"tool {t}"]["params_park_x"]), detach=float(c[f"tool {t}"]["params_detach_x"])) for t in ("T0", "T1")}
    return dict(attach=float(tc["params_attach_y"]), close=float(tc["params_close_y"]),
                shuttle=float(tc["params_safe_shuttle_y"]), safe=float(tc["params_safe_toolhead_y"]), tools=tools,
                origin=m["origin_model_xy"], sign=m["sign_xy"])


def motions(c):
    """{name: dict(under=..., z=..., points=[printer xy...])}."""
    t0, t1 = c["tools"]["T0"], c["tools"]["T1"]
    M = {}
    def add(name, under, z, pts): M[name] = dict(under=under, z=z, points=[list(p) for p in pts])
    add("T0 dropoff/pickup: carried along X detach, Y safe_toolhead <-> attach", "Left 27.4", TC_Z,
        [(t0["detach"], c["safe"]), (t0["detach"], c["attach"])])
    add("T0 into/out of its dock: X detach <-> park at Y attach", "Left 27.4", TC_Z, [(t0["detach"], c["attach"]), (t0["park"], c["attach"])])
    for x in range(7, 101, 3):
        add(f"T0 dropoff from the front edge x {x}", "Left 27.4", TC_Z, [(x, FRONT_Y), (t0["detach"], c["safe"])])
        add(f"restore to the front edge x {x}", "Left 27.4", TC_Z, [(x, c["safe"]), (x, FRONT_Y)])
    add("empty carriage: T0's dock moves, Y attach -> close -> safe_shuttle", "empty 27.4", TC_Z,
        [(t0["park"], c["attach"]), (t0["park"], c["shuttle"])])
    add("empty carriage: shuttle between the docks at Y safe_shuttle", "empty 27.4", TC_Z, [(t0["park"], c["shuttle"]), (t1["park"], c["shuttle"])])
    add("empty carriage, Beacon at 15: shuttle between the docks", "empty 15", TC_Z, [(t0["park"], c["shuttle"]), (t1["park"], c["shuttle"])])
    add("T1 dropoff/pickup: carried along X detach", "Right 27.4", TC_Z, [(t1["detach"], c["safe"]), (t1["detach"], c["attach"])])
    s = bs.settings()
    for off in OFFSETS:
        o = (s["offset"][0], off)
        over = bs.overscan(s["mesh_min"], s["mesh_max"], s["probe_count"], o, s["axis_min"], s["axis_max"], s["direction"])
        path = bs.scan_path(s["mesh_min"], s["mesh_max"], s["probe_count"], o, over, s["direction"])
        add(f"Beacon scan, y_offset {off:g} (overscan {over:.2f})", f"Left {off:g}", SCAN_Z, path)
    for off in OFFSETS:
        add(f"printing the front edge, first layer (Beacon {off:g})", f"Left {off:g}", FIRST_LAYER, [(6.5, FRONT_Y), (120, FRONT_Y)])
    return M


def main():
    import clashlib
    work = os.environ.get("VT350_WORK", os.path.join(ROOT, "cad", "data"))
    os.makedirs(os.path.join(work, "logs"), exist_ok=True)
    logf = open(os.path.join(work, "logs", "mellow_hop.log"), "w"); t0 = time.time()
    def log(*a):
        s_ = f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a); print(s_, flush=True); logf.write(s_ + "\n"); logf.flush()
    c = cfg()
    ox, oy = c["origin"]; sx, sy = c["sign"]
    to_model = lambda p: (ox + sx * p[0], oy + sy * p[1])
    plan = st.plan_stage(clashlib.FREECADCMD)
    log(f"model {st.MODEL} (read-only); toolchange Z {TC_Z} (first layer {FIRST_LAYER} + MadMax's hop {HOP}), scan Z {SCAN_Z}")
    unders = {}
    for h, cr in plan["carried"].items():
        (nx, ny, nz), T = cr["nozzle"], cr["T"]
        tip = (nx - T[0], ny - T[1], nz - T[2])
        head = [p for p in plan["heads"][h] if p != plan["tubes"][h]]
        for off in OFFSETS:
            unders[f"{h} {off:g}"] = dict(nozzle=tip, T=T, parts=head + plan["carriage"], head=head, beacon=BEACON,
                                          beacon_dy=-(27.4 - off))
            if h == "Left":
                unders[f"empty {off:g}"] = dict(nozzle=tip, T=T, parts=list(plan["carriage"]), head=[], beacon=BEACON,
                                               beacon_dy=-(27.4 - off))
    M = motions(c)
    for m in M.values(): m["points"] = [list(to_model(p)) for p in m["points"]]
    job = dict(model=st.MODEL, platform=os.path.join(ROOT, "platform", "freecad"), step=0.25, sample=0.5,
               probe_prefix=PROBE_PREFIX, ball_model_xy=list(to_model(BALL)), probe_half=14.0, probe_depth=8.0,
               under_window=[(-65.0, 65.0), (-60.0, 95.0)], under_depth=12.0, unders=unders, motions=M)
    with tempfile.TemporaryDirectory(prefix="mellow-hop-") as d:
        jp, op = os.path.join(d, "job.json"), os.path.join(d, "out.json")
        json.dump(job, open(jp, "w"))
        subprocess.run(clashlib.FREECADCMD + [os.path.join(HERE, "mellow_hop_fc.py")], cwd="/tmp",
                       env=dict(os.environ, MELLOW_HOP_JOB=jp, MELLOW_HOP_OUT=op), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(op + ".log"):
            for line in open(op + ".log"): log("fc:", line.rstrip())
        if not os.path.exists(op): raise SystemExit("mellow_hop_fc.py wrote nothing")
        res = json.load(open(op))
    if "fatal" in res: raise SystemExit("mellow_hop_fc.py failed:\n" + res["fatal"])
    # summary: the worst of each family
    fam = {}
    for name, r in res["motions"].items():
        key = name.split(" x ")[0] if " x " in name else name
        if r.get("clearance") is None: fam.setdefault(key, None); continue
        if fam.get(key) is None or r["clearance"] < fam[key][1]["clearance"]: fam[key] = (name, r)
    log("-- the closest pass of each move over the Zero (probe top "
        f"{res['probe_top']:.2f} above the print surface):")
    summary = {}
    for key, v in fam.items():
        if v is None: log(f"   {key}: never over the Zero"); summary[key] = None; continue
        name, r = v
        log(f"   {key}: Z {r['z']}: {r['clearance']:+.2f} mm ({r['part']}){'' if name == key else f' at {name}'}; "
            f"{r['clearance'] - r['z']:+.2f} at Z 0")
        summary[key] = dict(worst=name, z=r["z"], clearance=r["clearance"], part=r["part"], at_z0=round(r["clearance"] - r["z"], 3))
    res["summary"] = summary
    json.dump(res, open(os.path.join(work, "mellow_hop.json"), "w"), indent=1)
    log("done (read-only, nothing saved)")


if __name__ == "__main__":
    main()
