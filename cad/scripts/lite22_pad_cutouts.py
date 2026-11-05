# GUI pass: vt350-lite-21.FCStd -> vt350-lite-22.FCStd   (headless = dry run, never saves)
# The heater pad's front notches and side strips, and the fuse/lock-washer screws, measured by the user with
# calipers on 2026-11-05 (plate held heater-side up, front edge nearest; measured from the plate's outer edge):
#  - K341 front-ball holes: 7 from the side edge, 43 from the front: CONFIRMED (no change).
#  - side strips: 12.5 wide (was 11), from 28.5 to 58.5 from the front (was 28-59).
#  - front notches: 87 to 117 from the nearest side edge (was 85-120), 12.5 deep (was 10.3). The F150 holes
#    (6.5 from the front) sit mid-depth, as the rear row (6.55) does in its 12.3 strip.
#  - fuse and lock-washer screws: 55 from the centre each -> 122.5 / 232.5 (photo had 122.1 / 232.8).
#  - fuse side: right of centre seen heater-side up, front nearest (from photo PXL_20261105_212953005) = model.
# Nothing else changes: same holes elsewhere, the balls don't move. R150 (rear pair) stays at 102.5 / 252.5:
#  photo PXL_20261105_233549490 (ruler zeroed on the lock-washer screw) has R150 ~19, centre ~54.6, fuse 110, far R150 ~131.
import FreeCAD, Part, os, time, traceback, math
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-21.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-22.FCStd"
DRY = not FreeCAD.GuiUp
X0, Y0, W, T = -422.5, 28.0, 355.0, 10.0
CB_D, CB_DEPTH, HOLE_D = 6.5, 4.9, 3.4
PAD_T, MAG_T = 1.5, 1.4
RY = 348.5
HOLES = dict(F150_L=(102.5, 6.5), F150_R=(252.5, 6.5), K341_L=(7.0, 43.0), K341_R=(348.0, 43.0), REAR_C=(177.5, RY),
             R150_L=(102.5, RY), R150_R=(252.5, RY), FUSE=(122.5, RY), LOCKW=(232.5, RY))
HOLDDOWNS = [(21.0, 20.5), (334.0, 20.5), (21.0, 334.5), (334.0, 334.5)]
RS = 342.7                                        # rear pad strip front edge (lite-20)
SW, S0, S1 = 12.5, 28.5, 58.5                     # side strips: width, front end, rear end
N0, N1, ND = 87.0, 117.0, 12.5                    # front notches: from the nearest side edge, depth
PAD = [(1, 1), (N0, 1), (N0, ND), (N1, ND), (N1, 1), (W - N1, 1), (W - N1, ND), (W - N0, ND), (W - N0, 1), (354, 1),
       (354, S0), (W - SW, S0), (W - SW, S1), (354, S1), (354, 354), (262.5, 354), (262.5, RS), (92.5, RS), (92.5, 354),
       (1, 354), (1, S1), (SW, S1), (SW, S0), (1, S0)]
def poly_area(p): return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite22_pad_cutouts.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def G(u, v, z=0.0): return V(X0 + u, Y0 + v, z)
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
def gbox(o):
    s = gshape(o)
    try: return s.optimalBoundingBox(True, False)
    except Exception: return s.BoundBox
def parent_of(o):
    return next((x for x in o.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))
                 and o in getattr(x, 'Group', [])), None)
def ancestors(o):
    r = []; p = parent_of(o)
    while p is not None: r.append(p); p = parent_of(p)
    return r
def frame_of_parent(par):
    if par is None: return FreeCAD.Placement()
    if par.isDerivedFrom('App::Part'): return par.getGlobalPlacement()
    for p in ancestors(par):
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
    return FreeCAD.Placement()
def set_global_shape(o, s):
    loc = s.copy(); loc.Placement = frame_of_parent(parent_of(o)).inverse().multiply(loc.Placement); o.Shape = loc
def translate_global(o, Tv):
    par_g = frame_of_parent(parent_of(o)); g = o.getGlobalPlacement()
    o.Placement = par_g.inverse().multiply(FreeCAD.Placement(Tv, FreeCAD.Rotation())).multiply(g)
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def one(prefix):
    c = [o for o in doc.Objects if o.Label.startswith(prefix)]
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {prefix!r}...")
    return c[0]
def cyl_axis(o):
    f = max((f for f in gshape(o).Faces if f.Surface.TypeId == 'Part::GeomCylinder'), key=lambda f: f.Area)
    return f.Surface.Center, f.Surface.Axis
def bkey(o):
    b = gbox(o); return tuple(round(x, 4) for x in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))
try:
    errs, finds = [], []
    def check(ok, msg):
        log(("  ok   " if ok else "  FAIL ") + msg)
        if not ok: errs.append(msg)
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    before = {o.Name: bkey(o) for o in doc.Objects if is_leaf(o)}
    plate = one("LDO 350 build plate"); mag = one("Magnetic sheet"); npd = one("Heater pad LDO-SHPAC-350-120-750")
    pb = gbox(plate); zb, zt = pb.ZMin, pb.ZMax
    check(abs(pb.ZLength - T) < 0.01 and abs(pb.XMin - X0) < 0.01 and abs(pb.YMin - Y0) < 0.01,
          f"lite-21 plate at ({pb.XMin:.2f}, {pb.YMin:.2f}, {zb:.2f}), {pb.ZLength:.2f} thick")
    vol0 = gshape(plate).Volume
    # ---- plate: rebuilt with the new rear row (+ the hold-down shank holes, as lite-18)
    s = Part.makeBox(W, W, T, G(0, 0, zb))
    for n, (u, v) in HOLES.items():
        s = s.cut(Part.makeCylinder(HOLE_D / 2, T + 2, G(u, v, zb - 1)))
        s = s.cut(Part.makeCylinder(CB_D / 2, CB_DEPTH + 1, G(u, v, zb + T - CB_DEPTH)))
    for u, v in HOLDDOWNS: s = s.cut(Part.makeCylinder(1.5, 5.0, G(u, v, zb)))
    s = s.removeSplitter()
    check(s.isValid() and len(s.Solids) == 1, "new plate is one valid solid")
    check(abs(s.Volume - vol0) < 0.5, f"plate volume unchanged by moving holes ({vol0:.1f} -> {s.Volume:.1f})")
    set_global_shape(plate, s)
    m = Part.makeBox(W, W, MAG_T, G(0, 0, zt))
    for n, (u, v) in HOLES.items(): m = m.cut(Part.makeCylinder(CB_D / 2, MAG_T + 2, G(u, v, zt - 1)))
    set_global_shape(mag, m.removeSplitter())
    pw = Part.makePolygon([G(u, v, zb - PAD_T) for u, v in PAD] + [G(*PAD[0], zb - PAD_T)])
    pad = Part.Face(pw).extrude(V(0, 0, PAD_T))
    for u, v in HOLDDOWNS: pad = pad.cut(Part.makeCylinder(1.7, PAD_T + 2, G(u, v, zb - PAD_T - 1)))
    check(pad.isValid() and len(pad.Solids) == 1, "heater pad is one valid solid")
    pv0 = gshape(npd).Volume; set_global_shape(npd, pad)
    npd.Label = f"Heater pad LDO-SHPAC-350-120-750 ({PAD_T} mm, outline measured with calipers)"
    want = (poly_area(PAD) - 4 * math.pi * 1.7 ** 2) * PAD_T
    log(f"heater pad volume {pv0:.1f} -> {pad.Volume:.1f} (polygon says {want:.1f})")
    check(abs(pad.Volume - want) < 0.5, "pad volume matches the measured outline")
    doc.recompute()
    doc.recompute()
    def ball_c(o):
        b = gbox(o); return V((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, b.ZMin + 4.5)
    for name, hn in (("front left", "K341_L"), ("front right", "K341_R"), ("rear", "REAR_C")):
        bc = ball_c(one(f"Trident kinematic 9 mm M3 sphere nut, {name}")); h = G(*HOLES[hn])
        check(math.hypot(bc.x - h.x, bc.y - h.y) < 0.6, f"{name} ball under {hn} ({math.hypot(bc.x - h.x, bc.y - h.y):.2f} off)")
    ball = nut = sp = None
    # ---- nothing else moved
    changed = {o.Name for o in (plate, mag, npd)}
    after = {o.Name: bkey(o) for o in doc.Objects if is_leaf(o)}
    check(set(after) == set(before), f"same solids ({len(before)} -> {len(after)})")
    moved = [doc.getObject(n).Label for n in before if n not in changed and before[n] != after.get(n)]
    check(not moved, f"no other solid moved ({moved[:5]})")
    # ---- clashes of the changed parts against everything
    allnow = [o for o in doc.Objects if is_leaf(o)]
    hd = [o for o in allnow if o.Label.startswith("Heater pad hold-down")]
    by_construction = {plate.Name, mag.Name, npd.Name} | {o.Name for o in hd}
    seen = set()
    for a in (plate, mag, npd):
        sa = gshape(a); ba = sa.BoundBox
        for b in allnow:
            if b.Name == a.Name or frozenset((a.Name, b.Name)) in seen: continue
            seen.add(frozenset((a.Name, b.Name)))
            if {a.Name, b.Name} <= by_construction: continue
            if not ba.intersect(gbox(b)): continue
            try: v = sa.common(gshape(b)).Volume
            except Exception: continue
            if v <= 0.01: continue
            msg = f"{v:8.2f} mm3  {a.Label} x {b.Label}"
            known = {a.Name, b.Name} & {npd.Name} and ("J leaf spring" in a.Label + b.Label)
            if known: finds.append("CLASH " + msg); log("  FIND " + msg)
            else: errs.append(msg); log("  FAIL " + msg)
    spr_t = gbox(one("Trident kinematic J leaf spring, rear")).ZLength
    for name in ("front left", "front right", "rear"):
        s_ = gshape(one(f"Trident kinematic J leaf spring, {name}")); c = gshape(npd).common(s_)
        if c.Volume < 1e-4: log(f"{name}: spring clear of the pad"); finds.append(f"{name}: spring clear of the pad"); continue
        cb = c.BoundBox
        log(f"{name}: spring on the pad {c.Volume / spr_t:.1f} mm2, {cb.XLength:.1f} x {cb.YLength:.1f}, Y {cb.YMin:.1f}..{cb.YMax:.1f}")
        finds.append(f"{name}: spring corner on the pad, {c.Volume / spr_t:.1f} mm2 ({cb.XLength:.1f} x {cb.YLength:.1f})")
    log("FINDINGS:"); [log("  " + f) for f in finds]
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
