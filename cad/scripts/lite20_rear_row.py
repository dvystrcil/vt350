# GUI pass: vt350-lite-19.FCStd -> vt350-lite-20.FCStd   (headless = dry run, never saves)
# The plate's rear hole row and rear heater-pad cut-out, re-measured on 2026-11-05 from two ruler photos
# (Immich export immich-20261105_133334.zip: PXL_20261105_212953005 ruler along the rear strip, ~11.8 px/mm;
#  PXL_20261105_213013523 ruler across it, 19 px/mm). Cm ticks located by pixel-column profiles, not by eye.
#  - depth: pad edge -> hole centre 5.75, plate edge -> pad edge 12.3, so the rear row is 6.55 from the rear edge
#    (lite-18 had 5.5: the photo estimate stopped at the ~1 mm edge chamfer). Same 6.5 as the front row by ruler,
#    so the row is symmetric: RY = 355 - 6.5 = 348.5. Rear pad strip 12.3 deep -> starts at 342.7 (was 343.7).
#  - along the strip, relative to the centre hole, scaled so the R150 pair is 150.0 C-C (raw 148.8: the ruler sits
#    above the plate): R150 +-75.0, fuse screw -55.4 -> 122.1, lock-washer screw +54.7 -> 232.8, strip 169.9 long
#    and centred within 0.5 (kept 92.5-262.5). The centre hole is midway between R150 (+-0.1).
#  NOT re-measured here: K341 front holes, side strips, front notches, the centre hole vs the plate's side edges.
# The rear ball, its thin nut and spring slide along G's groove to the new REAR_C (lite-17 had it at Y 376.0,
#  lite-18 at 377.5, now 376.5). Everything else must keep its exact global bounding box, or the save is refused.
import FreeCAD, Part, os, time, traceback, math
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-19.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-20.FCStd"
DRY = not FreeCAD.GuiUp
X0, Y0, W, T = -422.5, 28.0, 355.0, 10.0
CB_D, CB_DEPTH, HOLE_D = 6.5, 4.9, 3.4
PAD_T, MAG_T = 1.5, 1.4
RY = 348.5
HOLES = dict(F150_L=(102.5, 6.5), F150_R=(252.5, 6.5), K341_L=(7.0, 43.0), K341_R=(348.0, 43.0), REAR_C=(177.5, RY),
             R150_L=(102.5, RY), R150_R=(252.5, RY), FUSE=(122.1, RY), LOCKW=(232.8, RY))
HOLDDOWNS = [(21.0, 20.5), (334.0, 20.5), (21.0, 334.5), (334.0, 334.5)]
RS = 342.7                                        # rear pad strip front edge (was 343.7)
PAD = [(1, 1), (85, 1), (85, 10.3), (120, 10.3), (120, 1), (235, 1), (235, 10.3), (270, 10.3), (270, 1), (354, 1),
       (354, 28), (344, 28), (344, 59), (354, 59), (354, 354), (262.5, 354), (262.5, RS), (92.5, RS), (92.5, 354),
       (1, 354), (1, 59), (11, 59), (11, 28), (1, 28)]
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite20_rear_row.log", "w"); t0 = time.time()
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
          f"lite-19 plate at ({pb.XMin:.2f}, {pb.YMin:.2f}, {zb:.2f}), {pb.ZLength:.2f} thick")
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
    log(f"heater pad volume {pv0:.1f} -> {pad.Volume:.1f} (rear strip 1.0 deeper over 170 x 1.5 = {170 * 1.0 * 1.5:.1f} less)")
    check(abs((pv0 - pad.Volume) - 255.0) < 1.0, "pad lost exactly the extra rear-strip strip")
    doc.recompute()
    # ---- rear ball, nut, spring: slide along G's groove under the new REAR_C
    ball = one("Trident kinematic 9 mm M3 sphere nut, rear"); nut = one("Trident kinematic M3 thin hex nut, rear")
    sp = one("Trident kinematic J leaf spring, rear")
    pins = [o for o in doc.Objects if o.Label.startswith("Trident kinematic M5x20 dowel pin, rear")]
    check(len(pins) == 2, "rear: 2 dowel pins")
    def ball_c(o):
        b = gbox(o); return V((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, b.ZMin + 4.5)
    h = G(*HOLES["REAR_C"]); bc0 = ball_c(ball)
    (_c, ax) = cyl_axis(pins[0]); ax = V(ax.x, ax.y, 0); ax.normalize()
    c1, c2 = gbox(pins[0]).Center, gbox(pins[1]).Center; mid = (V(c1.x, c1.y, 0) + V(c2.x, c2.y, 0)) * 0.5
    dt = (h - V(bc0.x, bc0.y, 0)).dot(ax); t_old = (V(bc0.x, bc0.y, 0) - mid).dot(ax)
    log(f"rear: hole Y {h.y:.2f} vs lite-19 ball Y {bc0.y:.2f}; slide {dt:+.2f} along the groove ({ax.x:.3f}, {ax.y:.3f}); "
        f"ball {t_old:+.2f} -> {t_old + dt:+.2f} from the pins' middle (pins +-10)")
    check(abs(t_old + dt) < 10 - 9 / 4, "rear ball still within the pins")
    for o in (ball, nut): translate_global(o, ax * dt)
    doc.recompute(); bc = ball_c(ball)
    check(math.hypot(bc.x - h.x, bc.y - h.y) < 0.6, f"rear ball under REAR_C ({math.hypot(bc.x - h.x, bc.y - h.y):.2f} off)")
    tap = None
    for o in doc.getObjectsByLabel("Trident kinematic H back top (2 mm)"):
        for f in gshape(o).Faces:
            if f.Surface.TypeId == 'Part::GeomCylinder' and abs(f.Surface.Radius - 2.529 / 2) < 0.01: tap = f.Surface.Center
    if tap is None: raise RuntimeError("H tapped hole not found")
    a0 = math.degrees(math.atan2(bc0.y - tap.y, bc0.x - tap.x)); a1 = math.degrees(math.atan2(bc.y - tap.y, bc.x - tap.x))
    sb = gshape(sp); sb.rotate(V(tap.x, tap.y, 0), V(0, 0, 1), a1 - a0); set_global_shape(sp, sb); doc.recompute()
    log(f"rear spring re-aimed {a1 - a0:+.2f} deg about H's tapped hole")
    check(gshape(sp).isInside(V(bc.x, bc.y, gbox(sp).ZMin + 0.19), 0.01, True), "rear ball bolt still lands on the spring")
    # ---- nothing else moved
    changed = {o.Name for o in (plate, mag, npd, ball, nut, sp)}
    after = {o.Name: bkey(o) for o in doc.Objects if is_leaf(o)}
    check(set(after) == set(before), f"same solids ({len(before)} -> {len(after)})")
    moved = [doc.getObject(n).Label for n in before if n not in changed and before[n] != after.get(n)]
    check(not moved, f"no other solid moved ({moved[:5]})")
    # ---- clashes of the changed parts against everything
    allnow = [o for o in doc.Objects if is_leaf(o)]
    hd = [o for o in allnow if o.Label.startswith("Heater pad hold-down")]
    by_construction = {plate.Name, mag.Name, npd.Name} | {o.Name for o in hd}
    seen = set()
    for a in (plate, mag, npd, ball, nut, sp):
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
            known = known or ({a.Name, b.Name} >= {ball.Name, sp.Name}) or ({a.Name, b.Name} >= {nut.Name, sp.Name})
            if known: finds.append("CLASH " + msg); log("  FIND " + msg)
            else: errs.append(msg); log("  FAIL " + msg)
    spr_t = gbox(sp).ZLength
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
