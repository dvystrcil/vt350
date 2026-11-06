# GUI pass: vt350-lite-25.FCStd -> vt350-lite-26.FCStd   (headless = dry run, never saves)   #61 AC3
# The gantry's MadMax carriage has sat on the X RAIL's front face, not on the MGN12H block, since the original
# assembly (vt350-good -> vt350-lite: same position in every lite-N). The carriage has a ~3 mm recess on its back for
# the block (upstream MadMax_Core_MGN12H_DB_AH_v11.step @ 6bf670d: floor 3.0 / 3.2 mm in from the back face), and in
# the model that floor is at the rail's front face (Y 265.6 vs 265.5). The block's top is ~4.8 mm further forward. So
# the clips at the carriage's ends reach 2.4 mm into the rail, and the block overlaps the carriage.
# Fix: translate everything under the gantry's "Carriage (1)" (carriage, its SpeedClips, the Beacon) by dY so that the
# recess floor lands on the block top. Nothing else moves:
#  - the rail sits on the beam's front face (273.5) and the block on the rail: both correct;
#  - the docks' carriage copies are the carriage at pickup, positioned by the docked tool (lite-14/23): they stay. The
#    pickup gantry pose (copy - gantry carriage) changes by -dY;
#  - the belts are drawn from the XY joints' idlers (lite-7): they stay. They now run in the carriage's belt-entry
#    channel instead of 1.5-3 mm behind its front face.
# Checks (refuses to save on any):
#  - dY measured, not assumed: block top and recess floor by ray probes over the block footprint; |dY| in 4..5.5;
#  - after: carriage floor on the block top within 0.01; carriage x rail and clips x rail = 0; carriage x block ~0;
#  - belts x carriage / clips no worse than before;
#  - moved solids moved by exactly (0, dY, 0) with unchanged volume; every other solid unchanged;
#  - Beacon offset from the carried nozzle unchanged (it rides on the carriage).
# Reports the pickup gantry dY + margin to the front stop, and the carried nozzle's Y reach.
# The carriage's shape is unchanged (pure translation), so cad/derived/ and parts/printed/ don't change.
import FreeCAD, Part, sys, os, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", f"{REPO}/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-25.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-26.FCStd"
DRY = not FreeCAD.GuiUp
CARRIAGE_GROUP, CARRIAGE = "Carriage (1)", "COMPOUND"
BLOCK, RAIL = "MGN_12_H_CARRAGE v1", "MGN12-400mm v002"
CLIP = "SpeedClip 4mm Gap 9mm"
BEACON = "Beacon RevH"
COPIES = {"Left": ("Left Dock", "COMPOUND003", "Left Toolhead"), "Right": ("Right Dock", "COMPOUND004", "Right Toolhead")}
BELTS = ("GT2 9mm belt, lower (Monolith 2WD)", "GT2 9mm belt, upper (Monolith 2WD)")
NOZZLE = "E3D v6 HotEnd - Nozzle"
Y_TRAVEL = (-277.19, 145.43)           # gantry dY limits (lite9_rails.log), as sweep_toolhead.py
SLIDE = 6.0                            # keyslot slide to the large opening (#52), as sweep_toolhead.py
PRINT_Y = (30.5, 380.5)                # print square Y, as sweep_toolhead.py
DY_RANGE = (-5.5, -4.0)
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite26_carriage_on_block.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
_BOX = {}
def gbox(o):
    k = (o.Name, tuple(o.getGlobalPlacement().toMatrix().A))
    if k not in _BOX:
        s = gshape(o)
        try: _BOX[k] = s.optimalBoundingBox(True, False)
        except Exception: _BOX[k] = s.BoundBox
    return _BOX[k]
def parent_of(o):
    return next((x for x in o.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))
                 and o in getattr(x, 'Group', [])), None)
def ancestors(o):
    r = []; p = parent_of(o)
    while p is not None: r.append(p); p = parent_of(p)
    return r
def container_global(o):
    for p in ancestors(o):
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
    return FreeCAD.Placement()
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def bxt(b): return (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)
def close(a, b, tol=1e-3): return all(abs(x - y) <= tol for x, y in zip(bxt(a), bxt(b)))
def com(s):
    vs = [(x.Volume, x.CenterOfMass) for x in s.Solids]; tv = sum(v for v, _ in vs)
    return sum((c * (v / tv) for v, c in vs), V(0, 0, 0))
def one(label, under=None, prefix=False):
    c = [o for o in doc.Objects if is_leaf(o) and (o.Label.startswith(label) if prefix else o.Label == label)
         and (under is None or under in [a.Label for a in ancestors(o)])]
    if len(c) != 1: raise RuntimeError(f"{len(c)} solids labelled {label!r} under {under!r}")
    return c[0]
def first_hit(shape, p0, d, n=3000, step=0.005):
    """distance from p0 along d (over n*step) to where the ray first enters shape (None if it doesn't): the ray as an
    edge, common() with the solid, nearest end of the pieces inside"""
    e = Part.makeLine(p0, p0 + d * (n * step))
    c = shape.common(e)
    if c.isNull() or not c.Edges: return None
    return min((v.Point - p0).Length for ed in c.Edges for v in ed.Vertexes)
def ov(a, b):
    if not a.BoundBox.intersect(b.BoundBox): return 0.0
    return a.common(b).Volume

try:
    errs, finds = [], []
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    leaves0 = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: gbox(o) for o in leaves0}; label0 = {o.Name: o.Label for o in leaves0}
    vol0 = {}
    car = one(CARRIAGE, CARRIAGE_GROUP); blk = one(BLOCK); rail = one(RAIL)
    movers = [o for o in leaves0 if CARRIAGE_GROUP in [a.Label for a in ancestors(o)]]
    log(f"under {CARRIAGE_GROUP!r}: {len(movers)} solids: {[o.Label for o in movers]}")
    if any(d in [a.Label for a in ancestors(o)] for o in movers for d, _, _ in COPIES.values()): errs.append("a mover is under a dock")
    beacon = [o for o in movers if o.Label.startswith(BEACON)]; clips = [o for o in movers if o.Label.startswith(CLIP)]
    if len(beacon) != 1 or len(clips) != 2 or car not in movers: errs.append(f"movers: beacon {len(beacon)}, clips {len(clips)}")
    C, B, R = gshape(car), gshape(blk), gshape(rail)
    cb, bb, rb = gbox(car), gbox(blk), gbox(rail)
    log(f"carriage Y {cb.YMin:.3f}..{cb.YMax:.3f}; block Y {bb.YMin:.3f}..{bb.YMax:.3f} X {bb.XMin:.2f}..{bb.XMax:.2f} "
        f"Z {bb.ZMin:.2f}..{bb.ZMax:.2f}; rail Y {rb.YMin:.3f}..{rb.YMax:.3f} Z {rb.ZMin:.2f}..{rb.ZMax:.2f}")
    # --- measure: block top and the carriage's recess floor, over the block footprint (0.8 mm in from its edges)
    grid = [(bb.XMin + 0.8 + i * (bb.XLength - 1.6) / 8, bb.ZMin + 0.8 + j * (bb.ZLength - 1.6) / 6) for i in range(9) for j in range(7)]
    tops, floors, topx = [], [], []
    for x, z in grid:
        d = first_hit(B, V(x, bb.YMin - 0.5, z), V(0, 1, 0), n=400)
        if d is not None: tops.append(bb.YMin - 0.5 + d); topx.append(x)
        d = first_hit(C, V(x, cb.YMax + 0.1, z), V(0, -1, 0), n=1200)
        if d is not None and d < 5.0: floors.append(cb.YMax + 0.1 - d)
    top = min(tops); floor = max(floors)
    log(f"block top: {len(tops)}/{len(grid)} rays, Y {min(tops):.3f}..{max(tops):.3f}")
    log(f"carriage recess floor: {len(floors)}/{len(grid)} rays hit within 5 mm of the back, Y "
        f"{min(floors):.3f}..{max(floors):.3f} ({cb.YMax - max(floors):.3f}..{cb.YMax - min(floors):.3f} in from the back; "
        f"upstream core STEP 3.0 / 3.2)")
    log(f"recess floor vs the rail's front face {rb.YMin:.3f}: {floor - rb.YMin:+.3f}; vs the block top {top:.3f}: {floor - top:+.3f}")
    dY = round(top - floor, 3)
    log(f"dY = {dY:+.3f}")
    if not (DY_RANGE[0] <= dY <= DY_RANGE[1]): raise RuntimeError(f"dY {dY} outside {DY_RANGE}")
    # the block's top has levels: the mounting face (highest plane) and reliefs 0.5 lower, plus the screw holes
    lev = {}
    for t, x in zip(tops, topx): lev.setdefault(round(t, 2), []).append(x)
    for k in sorted(lev): log(f"block top ray hits at Y {k:.2f}: {len(lev[k])}, X {min(lev[k]):.2f}..{max(lev[k]):.2f}")
    body = lev[round(top, 2)]
    log(f"mounting face = highest plane {top:.3f}: {len(body)} rays over X {min(body):.2f}..{max(body):.2f} "
        f"(block X {bb.XMin:.2f}..{bb.XMax:.2f}); HIWIN MGN12H H = 13 would put it at {rb.YMax - 13:.3f} "
        f"(model block {top - (rb.YMax - 13):+.3f})")
    if len(body) < 15 or max(body) - min(body) < 20: errs.append("block mounting face not identified")
    # --- before: overlaps, belts, pickup, Beacon
    belts = [gshape(one(b)) for b in BELTS]
    def state(Cs, clip_s, beacon_s):
        st = dict(car_rail=ov(Cs, R), car_block=ov(Cs, B), clips_rail=sum(ov(s, R) for s in clip_s),
                  belts_car=sum(ov(b, Cs) for b in belts), belts_clips=sum(ov(b, s) for b in belts for s in clip_s))
        cc = com(Cs); st["T"] = {}; st["beacon"] = {}
        bc = beacon_s.BoundBox.Center
        for k, (dock, cp, head) in COPIES.items():
            t = com(gshape(one(cp, dock))) - cc
            nz = gbox([o for o in leaves0 if o.Label.startswith(NOZZLE) and head in [a.Label for a in ancestors(o)]][0])
            nx, ny = (nz.XMin + nz.XMax) / 2 - t.x, (nz.YMin + nz.YMax) / 2 - t.y      # carried nozzle, gantry at model pose
            st["T"][k] = t; st["beacon"][k] = (bc.x - nx, bc.y - ny)
            st[k + "_ny"] = (nz.YMin + nz.YMax) / 2
        return st
    s0 = state(C, [gshape(o) for o in clips], gshape(beacon[0]))
    # --- move
    T = FreeCAD.Placement(V(0, dY, 0), FreeCAD.Rotation())
    new = {}
    for o in movers:
        g = gshape(o); n = g.copy(); n.translate(V(0, dY, 0)); new[o.Name] = n
    s1 = state(new[car.Name], [new[o.Name] for o in clips], new[beacon[0].Name])
    # floor on the block top, after
    C1 = new[car.Name]
    fl1 = [cb.YMax + dY + 0.1 - d for x, z in grid if (d := first_hit(C1, V(x, cb.YMax + dY + 0.1, z), V(0, -1, 0), n=1200)) is not None and d < 5.0]
    gap = top - max(fl1)
    log(f"after: recess floor {max(fl1):.3f}, block top {top:.3f}: gap {gap:+.4f}")
    if abs(gap) > 0.01: errs.append(f"carriage floor {gap:+.4f} off the block top")
    for key, what in (("car_rail", "carriage x rail"), ("clips_rail", "clips x rail"), ("car_block", "carriage x block"),
                      ("belts_car", "belts x carriage"), ("belts_clips", "belts x clips")):
        log(f"{what}: {s0[key]:.2f} -> {s1[key]:.2f} mm3")
    if s1["car_rail"] > 0.01 or s1["clips_rail"] > 0.01: errs.append("carriage or clips still in the rail")
    if s1["car_block"] > 0.5: errs.append(f"carriage x block {s1['car_block']:.2f} mm3")
    if s1["belts_car"] > s0["belts_car"] + 0.05: errs.append(f"belts x carriage {s0['belts_car']:.2f} -> {s1['belts_car']:.2f}")
    if s1["belts_clips"] > s0["belts_clips"] + 0.05: errs.append(f"belts x clips {s0['belts_clips']:.2f} -> {s1['belts_clips']:.2f}")
    finds.append(f"carriage group moved dY {dY:+.3f}: recess floor from the rail face ({floor:.2f}) onto the block top ({top:.2f}); "
                 f"carriage x rail {s0['car_rail']:.2f} -> {s1['car_rail']:.2f}, clips x rail {s0['clips_rail']:.2f} -> {s1['clips_rail']:.2f}, "
                 f"carriage x block {s0['car_block']:.2f} -> {s1['car_block']:.2f} mm3")
    # belt line vs the carriage + clips, a few mm in from each end of the carriage, at each belt's height: material
    # along Y (ray = edge, common() with the solid)
    c1b = C1.BoundBox
    clip1 = [new[o.Name] for o in clips]
    def runs_y(shapes, x, z):
        e = Part.makeLine(V(x, c1b.YMin - 1, z), V(x, c1b.YMax + 1, z)); r = []
        for sh in shapes:
            c = sh.common(e)
            if not c.isNull():
                r += [tuple(sorted((ed.Vertexes[0].Point.y, ed.Vertexes[-1].Point.y))) for ed in c.Edges]
        return sorted(r)
    for side, sgn, x0 in (("left", 1, c1b.XMin), ("right", -1, c1b.XMax)):
        for bn, bs in zip(BELTS, belts):
            slab = Part.makeBox(1.0, 60, 30, V(x0 - sgn * 2.0 - 0.5, c1b.YMin - 20, bs.BoundBox.ZMin - 5))
            bsec = bs.common(slab)
            if bsec.isNull() or bsec.Volume < 1e-6: log(f"   {side} end, {bn}: no belt just outside the carriage"); continue
            sb = bsec.BoundBox; zc = (sb.ZMin + sb.ZMax) / 2
            for dx in (1.0, 3.0, 6.0):
                x = x0 + sgn * dx
                rc = runs_y([C1], x, zc); rk = runs_y(clip1, x, zc)
                log(f"   {side} end +{dx:.0f}, {bn.split(',')[1].strip()} belt Y {sb.YMin:.2f}..{sb.YMax:.2f} (Z {zc:.2f}): carriage Y "
                    + (", ".join(f"{p:.2f}..{q:.2f}" for p, q in rc) or "-") + "; clip Y " + (", ".join(f"{p:.2f}..{q:.2f}" for p, q in rk) or "-"))
    # pickup and reach
    for k in COPIES:
        t0_, t1_ = s0["T"][k].y, s1["T"][k].y
        m0, m1 = (t0_ - SLIDE) - Y_TRAVEL[0], (t1_ - SLIDE) - Y_TRAVEL[0]
        r0, r1 = s0[k + "_ny"] + Y_TRAVEL[1] - t0_, s1[k + "_ny"] + Y_TRAVEL[1] - t1_
        f0, f1 = s0[k + "_ny"] + Y_TRAVEL[0] - t0_, s1[k + "_ny"] + Y_TRAVEL[0] - t1_
        log(f"{k}: pickup gantry dY {t0_:.2f} -> {t1_:.2f}; margin to the front stop at the large opening {m0:+.2f} -> {m1:+.2f}; "
            f"carried nozzle Y reach {f0:.2f}..{r0:.2f} -> {f1:.2f}..{r1:.2f} (print square {PRINT_Y[0]}..{PRINT_Y[1]})")
        finds.append(f"{k}: pickup margin {m0:+.2f} -> {m1:+.2f}; nozzle rear reach {r0:.2f} -> {r1:.2f} (print square rear {PRINT_Y[1]})")
        b0, b1 = s0["beacon"][k], s1["beacon"][k]
        log(f"{k}: Beacon box centre - carried nozzle ({b0[0]:+.3f}, {b0[1]:+.3f}) -> ({b1[0]:+.3f}, {b1[1]:+.3f})")
        if abs(b0[0] - b1[0]) > 1e-3 or abs(b0[1] - b1[1]) > 1e-3: errs.append(f"{k}: Beacon offset changed")
    finds.append("Beacon offset from the carried nozzle unchanged (Klipper x 0, y +27.4 stands)")
    # --- apply
    if not errs:
        for o in movers:
            vol0[o.Name] = o.Shape.Volume
            o.Placement = container_global(o).inverse().multiply(T.multiply(o.getGlobalPlacement()))
        doc.recompute(); _BOX.clear()
        now = {o.Name: o for o in doc.Objects if is_leaf(o)}
        for nm, b in before.items():
            if nm not in now: errs.append(f"lost {label0[nm]}"); continue
            nb = gbox(now[nm])
            if nm in new:
                exp = new[nm].BoundBox; got = gshape(now[nm]).BoundBox
                if not close(exp, got) or abs(now[nm].Shape.Volume - vol0[nm]) > 1e-6: errs.append(f"moved wrong: {label0[nm]}")
            elif not close(nb, b): errs.append(f"changed: {now[nm].Label}")
        log(f"applied: {len(new)} solids moved, {len(before) - len(new)} checked unchanged")
    log("FINDINGS:"); [log("  " + f) for f in finds]
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else:
        doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
        FreeCAD.closeDocument(doc.Name)
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
