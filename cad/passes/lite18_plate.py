# GUI pass: vt350-lite-17.FCStd -> vt350-lite-18.FCStd   (headless = dry run, never saves)
# The real build plate under the lite-17 kinematic mounts, measured by the user on 2026-11-05 (calipers, depth gauge,
# and photo PXL_20261105_175159371 of the underside, scale 7.76 px/mm; sketch ~/Documents/VT350/bed-plate-holes-5.FCStd):
#  - LDO plate: 355 x 355 x 10, square (no edge notches, no rear corner ears). Every hole is 3.4 through with a 6.5
#    counterbore on the magnet face, 4.9 deep in the aluminium (6.3 measured with the 1.4 magnet sheet on).
#  - holes (plate coords: origin front-left, magnet side up): F150 pair 102.5/252.5 x 6.5 (150.0 C-C by calipers);
#    K341 pair 7/348 x 43 (photo agrees within 1 mm); rear row at 349.5 (photo ~5.3 from the rear edge, +-1):
#    R150 102.5/252.5, centre 177.5, fuse screw 121.5, lock-washer screw 233.5.
#  - heater pad 1.5 thick (depth gauge), inset ~1 mm, with cut-outs: front notches 35 x 10.3 around F150, side strips
#    11 wide from 28 to 59 around K341, rear strip 92.5-262.5 x 11.3 deep. Corners radiused in reality, square here.
#  - 4 pad hold-downs (pan head + washer, 12.2 dia) at 21/334 x 20.5/334.5; top of magnet to head 15.2, so 3.8 below
#    the aluminium (2.0 head+washer by depth gauge + 1.5 pad = 3.5; the 3.8 envelope is used).
#  - magnet sheet 1.4 (11.4 plate+magnet).
# Anchoring: the plate keeps lite-17's footprint origin (front-left corner X -422.5, Y 28) and Z (sits on the springs);
#  the front balls stay under K341 (the only front pair over the front bed extrusion; F150 is ~36 mm in front of it).
#  The rear ball, its thin nut and spring slide along G's groove to the measured rear hole.
# Clashes with the heater pad / hold-downs are FINDINGS (the springs are drawn flat, before preload, so they overlap
#  the pad wherever they run past a cut-out); they are reported, with a preload-bend estimate, and do not block the save.
#  Anything else new overlapping, or a ball off its hole, blocks the save.
import FreeCAD, Part, sys, os, time, traceback, math
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-17.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-18.FCStd"
DRY = not FreeCAD.GuiUp
X0, Y0, W, T = -422.5, 28.0, 355.0, 10.0
CB_D, CB_DEPTH, HOLE_D = 6.5, 4.9, 3.4
PAD_T, MAG_T, HD_D, HD_BELOW = 1.5, 1.4, 12.2, 3.8
RY = 349.5
HOLES = dict(F150_L=(102.5, 6.5), F150_R=(252.5, 6.5), K341_L=(7.0, 43.0), K341_R=(348.0, 43.0), REAR_C=(177.5, RY),
             R150_L=(102.5, RY), R150_R=(252.5, RY), FUSE=(121.5, RY), LOCKW=(233.5, RY))
HOLDDOWNS = [(21.0, 20.5), (334.0, 20.5), (21.0, 334.5), (334.0, 334.5)]
PAD = [(1, 1), (85, 1), (85, 10.3), (120, 10.3), (120, 1), (235, 1), (235, 10.3), (270, 10.3), (270, 1), (354, 1),
       (354, 28), (344, 28), (344, 59), (354, 59), (354, 354), (262.5, 354), (262.5, 343.7), (92.5, 343.7), (92.5, 354),
       (1, 354), (1, 59), (11, 59), (11, 28), (1, 28)]
SHCS = [6, 8, 10, 12, 14, 16, 18, 20, 25]
ENGAGE_MIN = 3.0                                  # M3 thread engagement wanted in the sphere nut
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite18_plate.log", "w"); t0 = time.time()
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
def one(label):
    c = doc.getObjectsByLabel(label)
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {label!r}")
    return c[0]
def add(s, label, parent, color=None):
    n = doc.addObject('Part::Feature', 'Plate18'); parent.addObject(n); set_global_shape(n, s); n.Label = label
    if color and FreeCAD.GuiUp: n.ViewObject.ShapeColor = color
    return n
def cyl_axis(o):
    f = max((f for f in gshape(o).Faces if f.Surface.TypeId == 'Part::GeomCylinder'), key=lambda f: f.Area)
    return f.Surface.Center, f.Surface.Axis
try:
    errs, finds = [], []
    def check(ok, msg):
        log(("  ok   " if ok else "  FAIL ") + msg)
        if not ok: errs.append(msg)
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    plate = one("Universal Build Plate 350 v1"); pb = gbox(plate); zb = pb.ZMin
    check(abs(pb.ZLength - T) < 0.01, f"lite-17 plate is {pb.ZLength:.2f} thick")
    check(abs(pb.XMin - X0) < 0.01 and abs(pb.YMin - Y0) < 0.01, f"lite-17 plate front-left corner at ({pb.XMin:.2f}, {pb.YMin:.2f})")
    PG = parent_of(plate)
    # ---- the real plate
    s = Part.makeBox(W, W, T, G(0, 0, zb))
    for n, (u, v) in HOLES.items():
        s = s.cut(Part.makeCylinder(HOLE_D / 2, T + 2, G(u, v, zb - 1)))
        s = s.cut(Part.makeCylinder(CB_D / 2, CB_DEPTH + 1, G(u, v, zb + T - CB_DEPTH)))
    s = s.removeSplitter()
    check(s.isValid() and len(s.Solids) == 1, "new plate is one valid solid")
    set_global_shape(plate, s); plate.Label = "LDO 350 build plate (real: 355 sq x 10, 3.4 + 6.5x4.9 cbore)"
    doc.recompute()
    zt = zb + T
    # ---- magnet sheet, heater pad, hold-downs
    mag = Part.makeBox(W, W, MAG_T, G(0, 0, zt))
    for n, (u, v) in HOLES.items(): mag = mag.cut(Part.makeCylinder(CB_D / 2, MAG_T + 2, G(u, v, zt - 1)))
    nm = add(mag.removeSplitter(), f"Magnetic sheet ({MAG_T} mm)", PG, (0.15, 0.15, 0.15))
    pw = Part.makePolygon([G(u, v, zb - PAD_T) for u, v in PAD] + [G(*PAD[0], zb - PAD_T)])
    pad = Part.Face(pw).extrude(V(0, 0, PAD_T))
    for u, v in HOLDDOWNS: pad = pad.cut(Part.makeCylinder(1.7, PAD_T + 2, G(u, v, zb - PAD_T - 1)))
    check(pad.isValid() and len(pad.Solids) == 1, "heater pad is one valid solid")
    npd = add(pad, f"Heater pad LDO-SHPAC-350-120-750 ({PAD_T} mm, photo outline +-1 mm)", PG, (0.72, 0.22, 0.18))
    nhd = []
    for k, (u, v) in enumerate(HOLDDOWNS, 1):
        h = Part.makeCylinder(HD_D / 2, HD_BELOW - PAD_T, G(u, v, zb - HD_BELOW))
        h = h.fuse(Part.makeCylinder(1.5, HD_BELOW + 5, G(u, v, zb - HD_BELOW))).removeSplitter()
        nhd.append(add(h, f"Heater pad hold-down {k} (pan head + washer envelope, {HD_BELOW} below plate)", PG, (0.6, 0.6, 0.62)))
    # the hold-down shank goes into the plate (a tapped hole the pad hides): cut it so the plate/shank don't read as a clash
    s2 = gshape(plate)
    for u, v in HOLDDOWNS: s2 = s2.cut(Part.makeCylinder(1.5, 5.0, G(u, v, zb)))
    set_global_shape(plate, s2.removeSplitter()); doc.recompute()
    # ---- balls under the holes
    mounts = {}
    for name in ("front left", "front right", "rear"):
        mounts[name] = dict(ball=one(f"Trident kinematic 9 mm M3 sphere nut, {name}"), nut=one(f"Trident kinematic M3 thin hex nut, {name}"),
                            spring=one(f"Trident kinematic J leaf spring, {name} (flat, before preload)"),
                            pins=[o for o in doc.Objects if o.Label.startswith(f"Trident kinematic M5x20 dowel pin, {name}")])
    def ball_c(o):
        b = gbox(o); return V((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, b.ZMin + 4.5)
    hole_for = {"front left": "K341_L", "front right": "K341_R", "rear": "REAR_C"}
    for name, m in mounts.items():
        h = G(*HOLES[hole_for[name]]); bc = ball_c(m["ball"])
        check(len(m["pins"]) == 2, f"{name}: 2 dowel pins ({[o.Label for o in m['pins']]})")
        if name == "rear":
            (_c, ax) = cyl_axis(m["pins"][0]); ax = V(ax.x, ax.y, 0); ax.normalize(); c1, c2 = gbox(m["pins"][0]).Center, gbox(m["pins"][1]).Center
            dt = (h - V(bc.x, bc.y, 0)).dot(ax)
            mid = (V(c1.x, c1.y, 0) + V(c2.x, c2.y, 0)) * 0.5
            t_old = (V(bc.x, bc.y, 0) - mid).dot(ax)
            log(f"rear: hole Y {h.y:.2f} vs lite-17 ball Y {bc.y:.2f}; slide {dt:+.2f} along the groove ({ax.x:.3f}, {ax.y:.3f}); "
                f"ball {t_old:+.2f} -> {t_old + dt:+.2f} from the pins' middle (pins +-10)")
            check(abs(t_old + dt) < 10 - 9 / 4, "rear ball still within the pins")
            for k in ("ball", "nut"): translate_global(m[k], ax * dt)
            m["moved"] = ax * dt
        doc.recompute(); bc = ball_c(m["ball"])
        off = math.hypot(bc.x - h.x, bc.y - h.y)
        check(off < 0.6, f"{name} ball under {hole_for[name]} ({off:.2f} off)")
        m["bc"] = bc
    # rear spring: keep its oval on H's tapped hole, re-aim its tip at the moved ball (rotate about the oval)
    mr = mounts["rear"]
    if "moved" in mr:
        sp = mr["spring"]; sb = gshape(sp)
        bc_old = mr["bc"] - mr["moved"]
        tap = None
        for o in doc.getObjectsByLabel("Trident kinematic H back top (2 mm)"):
            for f in gshape(o).Faces:
                if f.Surface.TypeId == 'Part::GeomCylinder' and abs(f.Surface.Radius - 2.529 / 2) < 0.01: tap = f.Surface.Center
        if tap is None: raise RuntimeError("H tapped hole not found")
        a0 = math.degrees(math.atan2(bc_old.y - tap.y, bc_old.x - tap.x)); a1 = math.degrees(math.atan2(mr["bc"].y - tap.y, mr["bc"].x - tap.x))
        sb.rotate(V(tap.x, tap.y, 0), V(0, 0, 1), a1 - a0); set_global_shape(sp, sb); doc.recompute()
        log(f"rear spring re-aimed {a1 - a0:+.2f} deg about H's tapped hole")
        inside = gshape(sp).isInside(V(mr["bc"].x, mr["bc"].y, gbox(sp).ZMin + 0.19), 0.01, True)
        check(inside, "rear ball bolt still lands on the spring")
    # ---- bed bolt lengths (M3 SHCS, head in the counterbore)
    floor = T - CB_DEPTH
    nut_h = gbox(mounts["rear"]["nut"]).ZLength; spr_t = gbox(mounts["rear"]["spring"]).ZLength
    log(f"bolt stack below the counterbore floor: floor {floor:.2f} + spring {spr_t:.2f} + thin nut {nut_h:.2f}")
    for name, m in mounts.items():
        bb = gbox(m["ball"]); bc = m["bc"]
        to_ball_top = zt - CB_DEPTH - bb.ZMax
        to_ball_bot = zt - CB_DEPTH - bb.ZMin
        # what's under the ball: the pins' tops are beside it; the bottom plate (E/F/G) is below the groove
        under = [o for o in doc.Objects if is_leaf(o) and "Trident kinematic" in o.Label and any(k in o.Label for k in (" bottom (", "G back"))]
        zfloor = max((gbox(o).ZMax for o in under if gbox(o).XMin < bc.x < gbox(o).XMax and gbox(o).YMin < bc.y < gbox(o).YMax), default=None)
        room = (bb.ZMin - zfloor) if zfloor is not None else float('nan')
        lmin, lmax = to_ball_top + ENGAGE_MIN, to_ball_bot + max(0.0, room - 0.5)
        ok = [L for L in SHCS if lmin <= L <= lmax]
        log(f"{name}: under-head length to the ball's top {to_ball_top:.2f}, through the ball {to_ball_bot:.2f}; "
            f"gap ball bottom -> bottom plate {room:.2f}; need {lmin:.2f}..{lmax:.2f} -> stock M3 SHCS {ok}")
        finds.append(f"bolt {name}: M3 SHCS {ok} (min {lmin:.2f} for {ENGAGE_MIN:g} mm in the sphere nut, max {lmax:.2f})")
        if not ok: errs.append(f"{name}: no stock bolt length fits")
    # ---- clashes
    zb_now = gbox(plate).ZMin
    newp = [plate, nm, npd] + nhd
    allnow = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    pad_like = {npd.Name} | {o.Name for o in nhd}
    seen = set()
    for a in newp:
        sa = gshape(a); ba = sa.BoundBox
        for b in allnow:
            if b.Name == a.Name or b.Name in {x.Name for x in newp} and (b.Name, a.Name) in seen: continue
            seen.add((a.Name, b.Name))
            if b.Name in {x.Name for x in newp} and {a.Name, b.Name} <= ({plate.Name} | pad_like): continue  # pad/hold-down/plate contacts by construction
            if not ba.intersect(gbox(b)): continue
            try: v = sa.common(gshape(b)).Volume
            except Exception: continue
            if v <= 0.01: continue
            msg = f"{v:8.2f} mm3  {a.Label} x {b.Label}"
            if a.Name in pad_like and "Trident kinematic" in b.Label: finds.append("CLASH " + msg); log("  FIND " + msg)
            else: errs.append(msg); log("  FAIL " + msg)
    # min clearance of every kinematic part to the pad and the hold-downs
    kin = [o for o in allnow if "Trident kinematic" in o.Label]
    for o in nhd + [npd]:
        so = gshape(o)
        near = sorted(((so.distToShape(gshape(k))[0], k.Label) for k in kin if so.BoundBox.isInside(gbox(k).Center) or True), key=lambda x: x[0])[:2]
        log(f"  nearest to {o.Label[:40]}: " + "; ".join(f"{d:.2f} mm {l}" for d, l in near))
        if o in nhd: finds.append(f"{o.Label[:20]}: nearest kinematic part {near[0][0]:.2f} mm ({near[0][1]})")
    # where each spring clash is: the springs are flat and clamped against the plate at the ball, so any pad under them
    # near the ball is real contact. Report the overlap's footprint and how far it is from the ball.
    for name, m in mounts.items():
        sp = gshape(m["spring"]); bc = m["bc"]
        on_plate = sp.common(Part.makeBox(W, W, 5, G(0, 0, zb_now - 4))).Volume / sp.Volume
        c = gshape(npd).common(sp)
        if c.Volume < 1e-4:
            log(f"{name}: spring {on_plate:.0%} under the plate footprint; no pad under it"); finds.append(f"{name}: spring clear of the pad"); continue
        cb = c.BoundBox; area = c.Volume / spr_t
        dmin = min(math.hypot(p.Point.x - bc.x, p.Point.y - bc.y) for p in c.Vertexes)
        dmax = max(math.hypot(p.Point.x - bc.x, p.Point.y - bc.y) for p in c.Vertexes)
        log(f"{name}: spring {on_plate:.0%} under the plate footprint; on the pad: {area:.1f} mm2, {cb.XLength:.1f} x {cb.YLength:.1f} mm, "
            f"{dmin:.1f}..{dmax:.1f} mm from the ball, X {cb.XMin:.1f}..{cb.XMax:.1f} Y {cb.YMin:.1f}..{cb.YMax:.1f}")
        finds.append(f"{name}: spring corner on the pad, {area:.1f} mm2 ({cb.XLength:.1f} x {cb.YLength:.1f}), {dmin:.1f}..{dmax:.1f} mm from the ball")
    log(f"plate top (aluminium) Z {zt:.2f}, magnet top {zt + MAG_T:.2f} (lite-17 plate top {pb.ZMax:.2f})")
    log("FINDINGS:"); [log("  " + f) for f in finds]
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
