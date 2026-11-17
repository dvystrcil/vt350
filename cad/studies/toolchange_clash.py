#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Clash-check the moves Kalico plans for a tool change on the CAD model (vt350#116 AC5). Read-only.

    python3 cad/studies/toolchange_clash.py [N_WORKERS [HEAD ...]]   # VT350_MODEL=<lite-N.FCStd>; HEAD: Left, Right

Input: cad/klipper/toolchange_timeline.jsonl (every move Kalico planned for cad/klipper/toolchange.gcode) and
cad/klipper/xy_mapping.json (printer = sign * (model - origin)). sweep_toolhead.py's plan stage gives the groups (bed,
gantry, belts, carriage, each head) and each head's carried offset.

Each move becomes poses: its end, and points along it at most STEP mm apart. A pose places
  - the carriage so the active tool's nozzle is at the move's X/Y (the offset nozzle -> carriage is the same for both
    heads, to 0.01 mm), the gantry and belts with it;
  - the bed at the move's Z (Klipper Z0 = magnet sheet at the nozzle tip, as sweep_toolhead's "top");
  - the head: carried (moves with the carriage) or not (stays where it was last let go; at the start, docked).
What is carried follows the macros as cad/klipper/dock_params.py reads them: the empty carriage grabs a head on
arriving at that head's (params_park_x, params_attach_y); it carries it through the detach move; on a drop-off it
lets go when it leaves (params_park_x, params_attach_y) in Y. The timeline's `tool` is the active extruder, not what
is on the carriage (cad/klipper/README.md), so it is not used for that.

Reported per pose: the overlaps that are not already in the saved model (the docked fits), and whether one of
sweep_toolhead's own poses (corners, centre, the dock pickups) is the same pose (AC5: "Any position the
model-derived dock poses didn't cover gets reported"). Also any pose whose gantry Y is outside the travel.
Log: cad/data/logs/toolchange_clash.log, ends "toolchange_clash: done".
"""
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.setdefault("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-61.FCStd")
sys.path[:0] = [HERE, os.path.join(ROOT, "platform/freecad"), os.path.join(ROOT, "cad/scripts")]
WORK = os.environ.get("VT350_WORK", os.path.join(ROOT, "cad/data"))
TIMELINE = os.path.join(ROOT, "cad/klipper/toolchange_timeline.jsonl")
MAPPING = os.path.join(ROOT, "cad/klipper/xy_mapping.json")
TOOLCHANGER = os.path.join(ROOT, "cad/klipper/toolchanger.cfg")
STEP, STEP_FAR = 25.0, 100.0   # mm between poses along a move: near the docks (an end at printer Y < NEAR_Y), elsewhere
NEAR_Y = 50.0                   # just past params_safe_toolhead_y 48.04; the print area is sweep_toolhead's (corners, X scans)
# a block on its own rail: a sliding fit, whose volume changes with the rail's holes under it (sweep_toolhead's X scan
# leaves out MGN12-400mm the same way)
SLIDING = (("MGN12-400mm", "MGN_12_H_CARRAGE"), ("_MGN9H", "MGN9-400mm Y rail"), ("_MGN9H", "MGN9 Y rail front extension"))
SAME = 0.5             # mm: a Kalico pose is "covered" by a model pose with the carriage and head this close (bed Z apart)


def read_params(text):
    """toolchanger.cfg -> (attach_y, {extruder name: park_x}) (the [tool Tn] sections' extruder and params_park_x)."""
    attach, park, sec, ext = None, {}, None, {}
    for line in text.splitlines():
        s = line.split("#")[0].strip()
        if s.startswith("["): sec = s.strip("[]"); continue
        if ":" not in s: continue
        k, v = (x.strip() for x in s.split(":", 1))
        if k == "params_attach_y": attach = float(v)
        if sec and sec.startswith("tool ") and k == "extruder": ext[sec] = v
        if sec and sec.startswith("tool ") and k == "params_park_x": park[sec] = float(v)
    if attach is None or not park: raise ValueError("toolchanger.cfg: no params_attach_y or params_park_x")
    return attach, {ext[s]: x for s, x in park.items()}


def carried_states(moves, attach_y, park_x, tol=0.01):
    """moves: [(x, y, z)] in printer coordinates, in order (the first is where the carriage starts).
    park_x: {head: park X}. -> for each move i >= 1: (interior, end), each (carried head or None, {head: released
    pose as a printer (x, y) of the carriage when let go, or None = docked})."""
    def at_dock(p):
        for h, x in park_x.items():
            if abs(p[0] - x) < tol and abs(p[1] - attach_y) < tol: return h
        return None
    carried, rel = None, {h: None for h in park_x}
    out = []
    for a, b in zip(moves, moves[1:]):
        ha, hb = at_dock(a), at_dock(b)
        if carried is not None and ha == carried and abs(b[1] - a[1]) > tol and abs(b[0] - a[0]) < tol:
            rel[carried] = (a[0], a[1]); carried = None          # let go: leaving the dock in Y
            out.append(((None, dict(rel)), (None, dict(rel)))); continue
        interior = (carried, dict(rel))
        if carried is None and hb is not None:
            carried = hb; rel[hb] = None                         # grab on arrival
        out.append((interior, (carried, dict(rel))))
    return out


def samples(a, b, step=STEP):
    """Points from a (excluded) to b (included), at most step apart."""
    d = math.dist(a[:2], b[:2]) if len(a) > 2 else math.dist(a, b)
    n = max(1, math.ceil(max(d, abs(a[2] - b[2]) if len(a) > 2 else 0) / step))
    return [tuple(a[k] + (b[k] - a[k]) * i / n for k in range(len(a))) for i in range(1, n + 1)]


def main():
    import clashlib
    import sweep_toolhead as st
    n = int(sys.argv[1]) if len(sys.argv) > 1 else clashlib.default_n()
    os.makedirs(WORK + "/logs", exist_ok=True)
    lf = open(WORK + "/logs/toolchange_clash.log", "w"); t0 = time.time()
    def log(*a):
        s = f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a); print(s, flush=True); lf.write(s + "\n"); lf.flush()
    mp = json.load(open(MAPPING))
    (ox, oy), (sx, sy) = mp["origin_model_xy"], mp["sign_xy"]
    attach_y, park_by_ext = read_params(open(TOOLCHANGER).read())
    ext_head = {"extruder": "Left", "extruder1": "Right"}
    park_x = {ext_head[e]: x for e, x in park_by_ext.items()}
    tl = [json.loads(l) for l in open(TIMELINE)]
    moves = [tuple(r["pos"][:3]) for r in tl if r["kind"] == "move"]
    tools = [r["tool"] for r in tl if r["kind"] == "move"]
    log(f"model {st.MODEL} (read-only); timeline {len(tl)} lines, {len(moves)} moves; attach_y {attach_y}, park_x {park_x}; "
        f"mapping origin ({ox}, {oy}), sign ({sx}, {sy}) [{mp.get('status', '')[:60]}]")
    plan = st.plan_stage(clashlib.FREECADCMD)
    meta = plan["meta"]
    pick = {h: meta[f"{h}:dock pickup, top"] for h in st.HEADS}
    tz = {}
    for h in st.HEADS:
        m_ = [re.match(rf"{h}: pickup carriage offset \((\S+), (\S+), (\S+)\)", x) for x in plan["notes"]]
        m_ = [x for x in m_ if x]
        if len(m_) != 1: raise SystemExit(f"{h}: no 'pickup carriage offset' note in the plan")
        tz[h] = float(m_[0].group(3))
    T = {h: (pick[h]["carriage"][0], pick[h]["carriage"][1], tz[h]) for h in st.HEADS}
    off = {h: (pick[h]["nozzle"][0] - pick[h]["carriage"][0], pick[h]["nozzle"][1] - pick[h]["carriage"][1]) for h in st.HEADS}
    dz_top = pick["Left"]["bed_dz"]
    log(f"nozzle -> carriage offset: " + "; ".join(f"{h} ({o[0]:.3f}, {o[1]:.3f})" for h, o in off.items())
        + f"; bed top dZ {dz_top:+.3f}")
    if math.dist(off["Left"], off["Right"]) > 0.05: raise SystemExit("the heads' nozzle -> carriage offsets differ")
    o = off["Left"]
    def model_xy(p): return (p[0] / sx + ox, p[1] / sy + oy)
    def tc_of(p):
        mx, my = model_xy(p); return (mx - o[0], my - o[1], 0.0)
    states = carried_states(moves, attach_y, park_x)
    poses = {h: {} for h in st.HEADS}; info = {h: {} for h in st.HEADS}
    for i, ((s_in, s_end), a, b) in enumerate(zip(states, moves, moves[1:]), start=1):
        pts = samples(a, b, STEP if min(a[1], b[1]) < NEAR_Y else STEP_FAR)
        for j, p in enumerate(pts):
            carried, rel = s_end if j == len(pts) - 1 else s_in
            tc = tc_of(p)
            # one clash run per head: its own solids are the moving "head" group, the other head stays fixed (docked).
            # A pose goes to the run of the head that is carried, or else of a head let go off its dock pose.
            owner = carried or next((h for h in st.HEADS if rel[h] is not None), None) or ext_head[tools[i]]
            r_ = rel[owner]
            if carried == owner: th = (tc[0] - T[owner][0], tc[1] - T[owner][1], -tz[owner])
            elif r_ is None: th = (0.0, 0.0, 0.0)
            else:
                rr = tc_of(r_); th = (rr[0] - T[owner][0], rr[1] - T[owner][1], -tz[owner])
            others_moved = [h for h in st.HEADS if h != owner and rel[h] is not None]
            dz = dz_top - p[2]
            pid = f"move {i:02d}{'' if j == len(pts) - 1 else f' @{(j + 1) / len(pts):.2f}'}"
            poses[owner][pid] = {"bed": (0, 0, dz), "gantry": (0, tc[1], 0), "belt": (0, tc[1], 0), "carriage": tc, "head": th}
            info[owner][pid] = dict(p=p, carried=carried, moved_other=others_moved,
                                    in_travel=st.Y_TRAVEL[0] - 1e-6 <= tc[1] <= st.Y_TRAVEL[1] + 1e-6)
    log("excluded as in sweep_toolhead: the docks' carriage copies, the Z drag chain, the head's own bowden tube; belts "
        "clipped to the XY joints' band")
    clip = {bb: st.BELT_CLIP for bb in plan["belt"]}
    skip = [("belt", "gantry"), ("belt", "carriage")]
    uncovered_total, new_total = 0, 0
    only = sys.argv[2:] or list(st.HEADS)
    for h in only:
        mine = poses[h]
        if not mine: continue
        ref = plan["poses"][h]
        ps = dict(mine); ps["model"] = {}
        groups = dict(bed=plan["bed"], gantry=plan["gantry"], belt=plan["belt"], carriage=plan["carriage"], head=plan["heads"][h])
        res = clashlib.run(st.MODEL, groups=groups, poses=ps, exclude=plan["exclude"] + [plan["tubes"][h]], n=n, tol=0.01,
                           log=log, clip=clip, skip_group_pairs=skip)
        base = {(r["a"], r["b"]): r["volume"] for r in res["results"] if r["pose"] == "model"}
        log(f"=== {h} head: {len(mine)} poses; {len(res['errors'])} common() errors")
        for e in res["errors"]: log(f"   ERROR {e['pose']}: {e['la']} x {e['lb']}: {e['error']}")
        for pid, d in mine.items():
            m = info[h][pid]
            cov = [rp for rp, rd in ref.items() if all(math.dist(rd.get(g, (0, 0, 0)), d.get(g, (0, 0, 0))) < SAME
                                                      for g in ("carriage", "head"))]
            allr = [r for r in res["results"] if r["pose"] == pid and abs(base.get((r["a"], r["b"]), -1) - r["volume"]) >= 0.01]
            def sliding(r): return any((r["la"].startswith(x) and r["lb"].startswith(y)) or (r["lb"].startswith(x) and r["la"].startswith(y))
                                       for x, y in SLIDING)
            rows = [r for r in allr if not sliding(r)]; nslide = len(allr) - len(rows)
            new_total += len(rows); uncovered_total += not cov
            p = m["p"]
            state = f"carrying {m['carried']}" if m["carried"] else "empty"
            log(f"-- {pid}: printer ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}), {state}"
                + ("" if m["in_travel"] else ", GANTRY Y OUT OF TRAVEL")
                + (f", {', '.join(m['moved_other'])} head left off its dock" if m["moved_other"] else "")
                + f"; {'covered by the model pose ' + repr(cov[0]) if cov else 'NOT covered by a model pose'}; "
                + (f" (bed Z {d['bed'][2] - ref[cov[0]]['bed'][2]:+.2f} from it)" if cov else "")
                + f"; {len(rows)} overlaps not in the saved model" + (f" (+{nslide} blocks sliding on their rails)" if nslide else ""))
            for r in rows:
                log(f"   {r['volume']:10.2f} mm3  {r['ga']}: {r['la']}  x  {r['gb'] or 'fixed'}: {r['lb']}")
    log(f"summary: {sum(len(v) for v in poses.values())} poses, {uncovered_total} not covered by a model-derived pose, "
        f"{new_total} overlaps not in the saved model")
    log("toolchange_clash: done (read-only, nothing saved)")


if __name__ == "__main__":
    main()
