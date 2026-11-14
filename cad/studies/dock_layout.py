# #19 AC2: a front ROW of MadMax docks. How close can the docks sit, how far behind the row must the active head
# and the empty carriage stay, and how many tools fit in the carriage's X reach? Headless, read-only: never saves.
#   python3 /home/dan/Code/vt350/cad/studies/dock_layout.py [fields.json]
# Side: printer (vt350#122): it reads this printer's heads, docks and MadMax moves. Manual run: plain python3 plus the
# FreeCAD AppImage (`clashlib.FREECADCMD`); laptop, ~1 freecadcmd process, a few GB.
#
# Two stages, both from this file:
#  1. export (freecadcmd, env DOCK_LAYOUT_OUT=<json>): sweep_toolhead.plan() classifies the saved model (the same
#     groups the toolhead sweep uses), then each template slot's solids are sampled on their surfaces and binned into
#     EXTENT FIELDS: 'x' maps each (y, z) cell to the solid's (xmin, xmax) in that row, 'y' maps each (x, z) cell to
#     (ymin, ymax). Three groups per template slot (Left, Right):
#       parked  = head + MadMax plate + the dock's keyslot plate (`Dock Asembly`), at the docked pose;
#       shuttle = the gantry's MadMax carriage + Beacon, moved to the dock's pickup (the sweep's T, Z kept: 0.315 mm
#                 below the dock's carriage copy, as in sweep_toolhead);
#       carried = head + plate at the carried pose (Z -0.315) + the shuttle.
#  2. analysis (plain python3, no numpy, unit-tested in test_dock_layout.py): two parts translated against each other
#     touch along an axis when, in some shared row, one's max meets the other's min. sep() is that offset; it is
#     exact for one part wholly on one side of the other (no interleaving), which is how docked heads sit. A Y/Z
#     shift that isn't a whole cell checks both neighbouring cells (safe side).
#
# The MadMax moves (cad/klipper/toolchanger.cfg, from MadMax's toolchanger.cfg; vt350#52 AC1):
#   pickup:  Y safe_shuttle_y -> X park_x -> Y close_y -> Y attach_y -> X detach_x -> Y safe_toolhead_y
#   dropoff: the same path backwards.
# attach_y is 6 mm in front of the parked pose (the keyslot slide), detach_x 5 mm from park_x, AWAY from the keyslot
# plate. So in a row of identical slots at pitch p the carried head sits 5 mm toward one neighbour while it slides
# back to safe_toolhead_y, and the empty carriage passes behind every parked head at safe_shuttle_y.
# Left out, and said so in the log: bowden tubes (rigid routes, #3), USB cables (not modelled), the dock arms (they
# reach the corner posts; a row needs a crossbar mount instead, #19 AC7), the gantry and belts (the sweep checks them
# at the pickup, which is the same for every slot along X).
import json, math, os, re, subprocess, sys, tempfile, time

WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-30.FCStd")
HERE = os.path.abspath(__file__)
_HERE = os.path.dirname(HERE)
sys.path[:0] = [_HERE] + [p for p in (os.path.join(os.path.dirname(os.path.dirname(_HERE)), d) for d in ("cad/scripts", "platform/freecad")) if os.path.isdir(p)]

CELL = 1.0                 # mm, field cell in the two cross axes
STEP = 0.4                 # mm, surface sample spacing (< CELL, so every row a surface crosses gets points)
DEFLECTION = 0.05          # mm, tessellation
DETACH, SLIDE = 5.0, 6.0   # mm: detach_x - park_x, parked Y - attach_y (toolchanger.cfg)
CFG_PARKED_Y = -62.96      # toolchanger.cfg: parked = attach_y -68.96 + 6.0 (Kalico Y)
CFG_SHUTTLE, CFG_TOOLHEAD = 36.0, 111.0   # toolchanger.cfg safe_shuttle_y / safe_toolhead_y, relative to parked (UNCHECKED there)
CLEARANCES = (0.0, 1.0, 2.0)              # MadMax FAQ: 1-2 mm between docked heads
TOOLHEAD_Y_MAX = 250.0     # mm behind the parked pose: far enough that nothing shares a row any more


# ------------------------------------------------------------------------------------------- stage 2: analysis
def _shifts(d, h):
    k = d / h
    return sorted({math.floor(k + 1e-9), math.ceil(k - 1e-9)})


def argsep(A, B, du=0.0, dw=0.0, h=CELL):
    """Smallest offset s along the field's axis such that B, moved by (s, du, dw), is wholly on A's + side: the max of
    A.hi - B.lo over shared rows. Returns (s, A cell, B cell), or None when no row is shared."""
    best = None
    for ku in _shifts(du, h):
        for kw in _shifts(dw, h):
            for (iu, iw), va in A.items():
                vb = B.get((iu - ku, iw - kw))
                if vb is None: continue
                s = va[1] - vb[0]
                if best is None or s > best[0]: best = (s, (iu, iw), (iu - ku, iw - kw))
    return best


def sep(A, B, du=0.0, dw=0.0, h=CELL):
    r = argsep(A, B, du, dw, h)
    return None if r is None else r[0]


def flip(F):
    """Mirror a field along its axis: (lo, hi) -> (-hi, -lo), extra entries (part labels) swap with them."""
    return {k: (-v[1], -v[0]) + tuple(v[2:][::-1]) for k, v in F.items()}


def _ys(lo, hi, h):
    n = int(round((hi - lo) / h))
    return [lo + i * h for i in range(n + 1)]


def pitch(parked, carried, shuttle, detach, attach, toolhead_y, shuttle_y, clearance, h=CELL):
    """Smallest dock pitch for a row of identical slots (X fields). The carried head sits `detach` mm in X (sign: the
    side away from the keyslot plate) while it moves from attach_y to toolhead_y (Y relative to the parked pose); the
    empty carriage (shuttle) moves at park_x between shuttle_y and attach_y. Each phase is checked against the
    neighbours on both sides; the pitch is the largest requirement."""
    if detach < 0: parked, carried, shuttle, detach = flip(parked), flip(carried), flip(shuttle), -detach
    fp, fc, fs = flip(parked), flip(carried), flip(shuttle)
    out, why = {}, {}

    def need(name, r, add, info, a, b):
        if r is None: return
        val = r[0] + add
        if name not in out or val > out[name]: out[name], why[name] = val, (info, a[r[1]], b[r[2]])
    need("parked", argsep(parked, parked, h=h), clearance, "parked next to parked", parked, parked)
    for dy in _ys(attach, toolhead_y, h):                 # carried, at detach_x: toward the + neighbour
        need("detach side", argsep(carried, parked, du=-dy, h=h), detach + clearance, f"carried at detach_x, Y {dy:+.1f}", carried, parked)
        need("far side", argsep(fc, fp, du=-dy, h=h), clearance - detach, f"carried at detach_x, Y {dy:+.1f}", fc, fp)
    for dy in _ys(attach, 0.0, h):                         # carried at park_x, the keyslot slide
        for a, b in ((carried, parked), (fc, fp)):
            need("slide", argsep(a, b, du=-dy, h=h), clearance, f"carried at park_x, Y {dy:+.1f}", a, b)
    for dy in _ys(attach, shuttle_y, h):                   # the empty carriage, at park_x
        for a, b in ((shuttle, parked), (fs, fp)):
            need("shuttle", argsep(a, b, du=-dy, h=h), clearance, f"empty carriage at park_x, Y {dy:+.1f}", a, b)
    out["pitch"] = max(out.values())
    out["why"] = why
    return out


def pair_gap(i, j, attach, toolhead_y, shuttle_y, clearance, h=CELL):
    """Smallest nozzle-X distance from slot i to its right-hand neighbour j, for slots of any two templates. Each slot:
    dict(x=docked nozzle X, detach=signed detach_x - park_x, parked/carried/shuttle=X fields at its own docked pose).
    Only one head moves at a time: i's carried head and empty carriage against parked j, and j's against parked i."""
    dn = j["x"] - i["x"]; out, why = {}, {}

    def need(name, r, add, info):
        if r is not None and (name not in out or r[0] + add > out[name]): out[name], why[name] = r[0] + add, info
    need("parked", argsep(i["parked"], j["parked"], h=h), clearance + dn, "parked next to parked")
    for dy in _ys(attach, toolhead_y, h):
        need("left carried", argsep(i["carried"], j["parked"], du=-dy, h=h), i["detach"] + clearance + dn, f"Y {dy:+.1f}")
        need("right carried", argsep(i["parked"], j["carried"], du=dy, h=h), -j["detach"] + clearance + dn, f"Y {dy:+.1f}")
    for dy in _ys(attach, 0.0, h):
        need("slide", argsep(i["carried"], j["parked"], du=-dy, h=h), clearance + dn, f"left, Y {dy:+.1f}")
        need("slide", argsep(i["parked"], j["carried"], du=dy, h=h), clearance + dn, f"right, Y {dy:+.1f}")
    for dy in _ys(attach, shuttle_y, h):
        need("shuttle", argsep(i["shuttle"], j["parked"], du=-dy, h=h), clearance + dn, f"left, Y {dy:+.1f}")
        need("shuttle", argsep(i["parked"], j["shuttle"], du=dy, h=h), clearance + dn, f"right, Y {dy:+.1f}")
    out["gap"] = max(out.values()); out["why"] = why
    return out


def layouts(gaps, detach, reach, n_max):
    """Best row of 1..n_max docks from slot types (gaps[(left type, right type)] = nozzle distance; detach[type] =
    signed detach). Every slot's park_x and detach_x must lie in the nozzle-X reach. Returns {n: None or
    dict(pattern, span=sum of gaps, needed=span + the outer slots' outward detach, slack)}."""
    import itertools
    width, out = reach[1] - reach[0], {}
    for n in range(1, n_max + 1):
        best = None
        for pat in itertools.product(sorted(detach), repeat=n):
            span = sum(gaps[(a, b)] for a, b in zip(pat, pat[1:]))
            needed = span + max(0.0, -detach[pat[0]]) + max(0.0, detach[pat[-1]])
            if needed <= width + 1e-9 and (best is None or needed < best["needed"] - 1e-9):
                best = dict(pattern="".join(pat), span=span, needed=needed, slack=width - needed)
        out[n] = best
    return out


def behind(parked, moving, dx_range, clearance, h=CELL):
    """How far behind the parked pose (Y, + = toward the rear) a moving group must be to pass a ROW of parked heads at
    any X offset in dx_range (Y fields). Returns dy (None: never shares a row), the worst dx, and the cells."""
    best = None
    for dx in _ys(dx_range[0], dx_range[1], h):
        r = argsep(parked, moving, du=dx, h=h)
        if r is not None and (best is None or r[0] > best[0]): best = (r[0], dx, r[1], r[2])
    if best is None: return {"dy": None, "at_dx": None}
    return {"dy": best[0] + clearance, "at_dx": best[1], "parked_cell": best[2], "moving_cell": best[3]}


def tool_count(reach, pitch, detach):
    """Docks in a row whose slot centres (nozzle X at the pickup) all lie in the carriage's nozzle-X reach, leaving
    the outer slot room for its detach move."""
    span = reach[1] - reach[0] - abs(detach)
    return int(math.floor(span / pitch + 1e-9)) + 1


def dump_field(F):
    return {f"{k[0]},{k[1]}": list(v) for k, v in F.items()}


def load_field(D):
    return {tuple(int(x) for x in k.split(",")): tuple(v) for k, v in D.items()}


# ------------------------------------------------------------------------------------------- stage 1: export
def export(out):
    import FreeCAD, numpy as np
    import sweep_toolhead as st
    st.MODEL = MODEL
    with tempfile.TemporaryDirectory(prefix="docklayout-") as d:
        pj = os.path.join(d, "plan.json"); st.plan(pj); plan_ = json.load(open(pj))
    doc = FreeCAD.ActiveDocument
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, 'Group', []) or []): par.setdefault(k.Name, o)
    def path(o):
        r, p = [], par.get(o.Name)
        while p is not None: r.append(p.Label); p = par.get(p.Name)
        return r
    def gshape(name):
        o = doc.getObject(name); s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
    num = r"(-?\d+\.\d+)"
    labels, lix = [], {}
    def li(lab):
        if lab not in lix: lix[lab] = len(labels); labels.append(lab)
        return lix[lab]

    def points(s):
        pts, tris = s.tessellate(DEFLECTION)
        if not tris: return np.zeros((0, 3))
        P = np.array([(p.x, p.y, p.z) for p in pts]); T = np.array(tris)
        a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
        L = np.max(np.stack([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)]), axis=0)
        n = np.maximum(1, np.ceil(L / STEP)).astype(int)
        out_ = [P]
        for k in np.unique(n):
            sel = n == k
            i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1)); m = (i + j) <= k
            u, v = (i[m] / k)[None, :, None], (j[m] / k)[None, :, None]
            A, B, C = a[sel][:, None, :], b[sel][:, None, :], c[sel][:, None, :]
            out_.append((A + u * (B - A) + v * (C - A)).reshape(-1, 3))
        return np.concatenate(out_)

    def fields(members):                       # members: [(object Name, (dx, dy, dz))]
        F = {"x": {}, "y": {}}
        for name, t in members:
            P = points(gshape(name)) + np.array(t)
            if not len(P): continue
            L = li(doc.getObject(name).Label)
            for ax, (a, u, w) in (("x", (0, 1, 2)), ("y", (1, 0, 2))):
                iu = np.floor(P[:, u] / CELL).astype(np.int64); iw = np.floor(P[:, w] / CELL).astype(np.int64)
                key = (iu - iu.min()) * (iw.max() - iw.min() + 1) + (iw - iw.min())
                order = np.argsort(key, kind="stable"); ks = key[order]; vs = P[order, a]
                starts = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
                lo, hi = np.minimum.reduceat(vs, starts), np.maximum.reduceat(vs, starts)
                cu, cw = iu[order][starts], iw[order][starts]
                G = F[ax]
                for k in range(len(starts)):
                    c_ = (int(cu[k]), int(cw[k])); v = G.get(c_)
                    l_, h_ = float(lo[k]), float(hi[k])
                    if v is None: G[c_] = [l_, h_, L, L]
                    else:
                        if l_ < v[0]: v[0], v[2] = l_, L
                        if h_ > v[1]: v[1], v[3] = h_, L
        return {ax: dump_field(F[ax]) for ax in F}

    res = {"model": MODEL, "cell": CELL, "step": STEP, "deflection": DEFLECTION, "notes": plan_["notes"], "templates": {}}
    for h, d in st.HEADS.items():
        T = [float(x) for x in re.search(rf"^{h}: pickup carriage offset \({num}, {num}, {num}\)",
                                         "\n".join(plan_["notes"]), re.M).groups()]
        noz = [float(x) for x in re.search(rf"^{h}: docked nozzle tip \({num}, {num}, {num}\)",
                                           "\n".join(plan_["notes"]), re.M).groups()]
        tool = plan_["tool"][h]
        skip = set(tool["plate"]) | set(plan_["dock_copies"])
        keyslot = [o.Name for o in doc.Objects if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
                   and d["dock"] in path(o) and o.Name not in skip
                   and not any(x.startswith("Dock Arm") for x in path(o) + [o.Label])]
        arms = [o.Label for o in doc.Objects if o.isDerivedFrom('Part::Feature') and d["dock"] in path(o)
                and any(x.startswith("Dock Arm") for x in path(o) + [o.Label])]
        head = tool["head"] + tool["plate"]
        sh = [(n, (T[0], T[1], 0.0)) for n in plan_["carriage"]]
        hb = [gshape(n).BoundBox for n in tool["head"]]; kb = [gshape(n).BoundBox for n in keyslot]
        hx = (min(b.XMin for b in hb) + max(b.XMax for b in hb)) / 2
        kx = (min(b.XMin for b in kb) + max(b.XMax for b in kb)) / 2
        res["templates"][h] = dict(
            pickup_offset=T, docked_nozzle=noz, carried_dz=-T[2],
            detach=DETACH if kx < hx else -DETACH,
            keyslot=[doc.getObject(n).Label for n in keyslot], arms_left_out=arms,
            head_centre_x=hx, keyslot_centre_x=kx,
            fields=dict(parked=fields([(n, (0.0, 0.0, 0.0)) for n in head + keyslot]),
                        shuttle=fields(sh),
                        carried=fields([(n, (0.0, 0.0, -T[2])) for n in head] + sh)))
    res["labels"] = labels
    json.dump(res, open(out, "w"))


def export_stage(freecadcmd, out):
    subprocess.run(freecadcmd + [HERE], env=dict(os.environ, DOCK_LAYOUT_OUT=out, VT350_MODEL=MODEL),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd="/tmp")
    if not os.path.exists(out): raise SystemExit("export stage wrote nothing")
    r = json.load(open(out))
    if "fatal" in r: raise SystemExit("export stage failed:\n" + r["fatal"])
    return r


# ------------------------------------------------------------------------------------------- report
def main():
    os.makedirs(WORK + "/logs", exist_ok=True)
    log_f = open(WORK + "/logs/dock_layout.log", "w"); t0 = time.time()
    def log(*a):
        s = f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a); print(s, flush=True); log_f.write(s + "\n"); log_f.flush()
    if len(sys.argv) > 1:
        ex = json.load(open(sys.argv[1]))
    else:
        import clashlib
        keep = os.environ.get("DOCK_LAYOUT_KEEP")          # keep the fields: re-run the analysis with `dock_layout.py <it>`
        fd, fj = tempfile.mkstemp(prefix="dock-layout-", suffix=".json"); os.close(fd)
        try:
            ex = export_stage(clashlib.FREECADCMD, fj)
            if keep: os.replace(fj, keep)
        finally: os.path.exists(fj) and os.remove(fj)
    import print_area
    reach = print_area.parse_reach(open(os.path.join(WORK, "logs", "sweep_toolhead.log")).read())
    rx = (reach["x_min"], reach["x_max"])
    lab = ex["labels"]
    def nm(v, i): return lab[int(v[i])] if len(v) > i else "?"
    log(f"model {ex['model']} (read-only); cells {ex['cell']} mm, surface samples every {ex['step']} mm, "
        f"tessellation {ex['deflection']} mm: distances are good to about +-0.5 mm")
    log(f"carriage nozzle-X reach {rx[0]} .. {rx[1]} (sweep_toolhead.log, {reach['model']})")
    log("left out: bowden tubes (#3), USB cables (not modelled), dock arms (corner-post mounts; a row needs a crossbar, "
        "AC7), gantry and belts (checked by the sweep at the pickup, the same for every slot)")
    summary = {}
    for h, t in ex["templates"].items():
        F = {g: {ax: load_field(t["fields"][g][ax]) for ax in ("x", "y")} for g in t["fields"]}
        log(f"=== template slot: {h} (keyslot {', '.join(t['keyslot'])}; left out: {', '.join(t['arms_left_out']) or '-'})")
        log(f"   keyslot plate centre X {t['keyslot_centre_x']:.2f} vs head centre {t['head_centre_x']:.2f}: "
            f"detach {t['detach']:+.1f} mm in X (away from the plate); pickup carriage offset {t['pickup_offset']}; "
            f"carried head dZ {t['carried_dz']:+.3f}")
        summary[h] = {}
        for c in CLEARANCES:
            p = pitch(F["parked"]["x"], F["carried"]["x"], F["shuttle"]["x"], t["detach"], -SLIDE, TOOLHEAD_Y_MAX, CFG_SHUTTLE, c)
            n = tool_count(rx, p["pitch"], t["detach"])
            log(f"-- clearance {c:.1f} mm: pitch {p['pitch']:.2f} mm -> {n} tools in the reach")
            for k in ("parked", "slide", "detach side", "far side", "shuttle"):
                if k in p:
                    info, va, vb = p["why"][k]
                    log(f"   {k:12} {p[k]:7.2f}  ({info}: moving {nm(va, 3)} meets neighbour {nm(vb, 2)})")
            summary[h][f"clearance {c:.1f}"] = dict(pitch=round(p["pitch"], 2), tools=n, parts={k: round(p[k], 2) for k in p if k not in ("pitch", "why")})
        # behind the row: true safe Y values, and the print square's front edge
        span = (rx[0] - rx[1] - 100.0, rx[1] - rx[0] + 100.0)
        for g, cfg in (("shuttle", CFG_SHUTTLE), ("carried", CFG_TOOLHEAD)):
            b = behind(F["parked"]["y"], F[g]["y"], span, 0.0)
            if b["dy"] is None: log(f"-- {g} behind the row: never shares a row"); continue
            pv, mv = F["parked"]["y"][tuple(b["parked_cell"])], F[g]["y"][tuple(b["moving_cell"])]
            log(f"-- {g} passing behind a row of parked heads: needs Y >= parked {b['dy']:+.2f} mm (+ clearance), worst at "
                f"dX {b['at_dx']:+.1f}: parked {nm(pv, 3)} (rear Y {pv[1]:.2f}) vs {g} {nm(mv, 2)} (front Y {mv[0]:.2f}); "
                f"toolchanger.cfg uses parked {cfg:+.1f} (Kalico {CFG_PARKED_Y + cfg:.2f}); with 2 mm: Kalico >= "
                f"{CFG_PARKED_Y + b['dy'] + 2.0:.2f}")
            summary[h][g + "_behind"] = round(b["dy"], 2)
            if g == "carried":
                ny = t["docked_nozzle"][1] + b["dy"] + 2.0
                log(f"   front edge: with docks along the whole front, the carried nozzle must stay at Y >= {ny:.2f} "
                    f"(docked nozzle Y {t['docked_nozzle'][1]:.2f} + {b['dy']:.2f} + 2.0); print square front edge 30.50")
                summary[h]["front_nozzle_y"] = round(ny, 2)
    # mixed rows: each slot Left-style (keyslot plate on -X, detach +X) or Right-style (mirrored: plate on +X, detach -X)
    slots = {h[0]: dict(x=t["docked_nozzle"][0], detach=t["detach"],
                        **{g: load_field(t["fields"][g]["x"]) for g in ("parked", "carried", "shuttle")})
             for h, t in ex["templates"].items()}
    log("=== rows of docks, any mix of Left-style (L: keyslot plate on -X, detach +X) and Right-style (R: mirrored) slots; "
        "gap = nozzle X distance between neighbours")
    summary["rows"] = {}
    for c in CLEARANCES:
        gaps = {}
        for a_ in slots:
            for b_ in slots:
                g = pair_gap(slots[a_], slots[b_], -SLIDE, TOOLHEAD_Y_MAX, CFG_SHUTTLE, c)
                gaps[(a_, b_)] = g["gap"]
                k = max((k for k in g if k not in ("gap", "why")), key=lambda k: g[k])
                log(f"-- clearance {c:.1f}: {a_}|{b_} gap {g['gap']:.2f} (set by: {k}, {g['why'][k]})")
        rows = layouts(gaps, {k: v["detach"] for k, v in slots.items()}, rx, 7)
        for n, r in rows.items():
            log(f"   {n} tools: " + ("does not fit" if r is None else
                f"{r['pattern']}, span {r['span']:.2f} + outward detach = {r['needed']:.2f} of {rx[1] - rx[0]:.2f} (slack {r['slack']:.2f})"))
        summary["rows"][f"clearance {c:.1f}"] = dict(gaps={f"{a_}|{b_}": round(v, 2) for (a_, b_), v in gaps.items()},
                                                    rows={str(n): r for n, r in rows.items()})
    json.dump(summary, open(WORK + "/logs/dock_layout.json", "w"), indent=1, sort_keys=True)
    log("done (read-only, nothing saved)")


if os.environ.get("DOCK_LAYOUT_OUT"):
    try:
        export(os.environ["DOCK_LAYOUT_OUT"])
    except Exception:
        import traceback; json.dump(dict(fatal=traceback.format_exc()), open(os.environ["DOCK_LAYOUT_OUT"], "w"))
    finally:
        os._exit(0)
elif __name__ == "__main__":
    main()
