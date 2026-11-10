# GUI pass: vt350-lite-23.FCStd -> vt350-lite-24.FCStd   (headless = dry run, never saves)   #54 AC2
# Beacon RevH (user: Beacon RevH Contact) under the MadMax carriage, at Beacon's documented height above the nozzle.
#  - Beacon's own CAD: beacon3d/docs mcad/beacon/Beacon_RevH_Assm_{Normal,LowProfile}.STEP (MIT; the Molex connector
#    sub-assembly is under Molex's terms), read from $VT350_DL (default ~/Documents/VT350/downloads/beacon). Not in git. The CAD's 20 mm tall cylinder above
#    the coil is a keep-out volume, not a part: it's left out of the model, and what sits inside it is reported.
#  - Mount: andrewmcgr's MadMax carriage has two upward M3 pilot holes (dia 2.52) at +-15.8 mm from its centre, rising
#    from a pocket ceiling 3.0 mm above its underside; RevH's two mounting slots are at +-15.8. Board top on the ceiling.
#  - Height: Beacon's quickstart "nominally 2.6mm recessed from the nozzle in Z"; Contact page "only around 3mm higher
#    than the nozzle tip". On lite-23 the coil face would sit only ~0.46 mm above the carried nozzle tip, so the
#    pocket ceiling is raised by DZ (the carriage is remixed: GPL-3.0, andrewmcgr) on the gantry carriage AND on the
#    two docks' carriage copies, so all three stay the same part (sweep_toolhead.py checks that).
#  - Variant (Normal: vertical connector; LowProfile: sideways connector) and orientation (connector to the front or
#    the rear) are chosen by test: each candidate is checked against the carriage, and against each head + plate at
#    its carried pose (the dock's carriage copy is the carriage at pickup, so the Beacon is checked there, docked).
#    The plug's way in (PLUG beyond the connector) must be clear too. Among the candidates that fit, connector to the
#    REAR wins (the cable leaves away from the bowdens, toward the X cable chain of #54 AC3), then least carriage
#    material removed; all are logged.
import FreeCAD, Part, Import, MeshPart, sys, os, time, traceback, math
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
DL = os.environ.get("VT350_DL", "/home/dan/Documents/VT350/downloads/beacon")
SRC = "/home/dan/Documents/VT350/vt350-lite-23.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-24.FCStd"
DRY = not FreeCAD.GuiUp
H = 2.6                      # coil face above the carried nozzle tip (Beacon quickstart nominal)
CLEAR = 0.5                  # pocket clearance around the board and connector (mm)
PLUG = 15.0                  # ASSUMED room the mating cable plug + its first bend needs beyond the connector, in its
                             # mating direction (Normal: up; LowProfile: out along -Y of the board). Not from a datasheet.
CARRIAGE = ("Carriage (1)", "COMPOUND")
COPIES = {"Left": ("Left Dock", "COMPOUND003"), "Right": ("Right Dock", "COMPOUND004")}
HEADS = {"Left": "Left Toolhead", "Right": "Right Toolhead"}
RIDE = {"Left": ("Left Dock", ["Plate", "Plate Back"]), "Right": ("Right Dock", ["Plate(Mirror)", "Plate Back(Mirror)"])}
NOZZLE = "E3D v6 HotEnd - Nozzle"
VARIANTS = {"Normal": "Beacon_RevH_Assm_Normal.STEP", "LowProfile": "Beacon_RevH_Assm_LowProfile.STEP"}
os.makedirs(WORK + "/logs", exist_ok=True); os.makedirs(WORK + "/stl", exist_ok=True)
log_f = open(WORK + "/logs/lite24_beacon.log", "w"); t0 = time.time()
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
def frame_of_parent(par):
    if par is None: return FreeCAD.Placement()
    if par.isDerivedFrom('App::Part'): return par.getGlobalPlacement()
    for p in ancestors(par):
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
    return FreeCAD.Placement()
def container_global(o): return frame_of_parent(parent_of(o))
def descendants(g):
    out = []
    for c in getattr(g, 'Group', []) or []:
        out.append(c); out += descendants(c)
    return out
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax), (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
def set_global_shape(o, s):
    loc = s.copy(); loc.Placement = container_global(o).inverse().multiply(loc.Placement); o.Shape = loc
def one(label, under=None):
    c = [o for o in doc.getObjectsByLabel(label) if under is None or under in [a.Label for a in ancestors(o)]]
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {label!r} under {under!r}")
    return c[0]
def look(o):
    vo = getattr(o, 'ViewObject', None)
    return [(a.DiffuseColor, a.Transparency) for a in vo.ShapeAppearance] if vo is not None and hasattr(vo, 'ShapeAppearance') else None
def restore_look(o, ap0):
    if ap0 is None: return
    try:
        ap = o.ViewObject.ShapeAppearance
        if len(ap) != len(ap0): ap = [ap[0]] if ap else ap
        for x in ap: x.DiffuseColor = ap0[0][0]; x.Transparency = ap0[0][1]
        o.ViewObject.ShapeAppearance = ap
    except Exception: pass
def com(s):
    vs = [(x.Volume, x.CenterOfMass) for x in s.Solids]; tv = sum(v for v, _ in vs)
    return sum((c * (v / tv) for v, c in vs), V(0, 0, 0))
def load_beacon(fn):
    """Beacon STEP -> (parts compound without the keep-out cylinder, keep-out solid, connector solid) in Beacon's frame:
    board top at Z 0, coil face at Z -4.21, coil axis on Z, mounting slots at X +-15.8, Y -3.5"""
    d = FreeCAD.newDocument("beacon_tmp"); Import.insert(os.path.join(DL, fn), d.Name)
    sol = []
    for o in d.Objects:
        if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids and not o.InList or \
           (o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids and not any(x.isDerivedFrom('Part::Feature') for x in o.InList)):
            s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); sol += s.Solids
    seen, uniq = set(), []
    for x in sol:
        k = (round(x.Volume, 2),) + tuple(round(v, 2) for v in (x.BoundBox.XMin, x.BoundBox.YMin, x.BoundBox.ZMin))
        if k not in seen: seen.add(k); uniq.append(x)
    FreeCAD.closeDocument(d.Name)
    keep = [x for x in uniq if abs(x.BoundBox.ZMin) < 0.01 and abs(x.BoundBox.ZMax - 20.0) < 0.01]
    if len(keep) != 1: raise RuntimeError(f"{fn}: {len(keep)} keep-out cylinders")
    parts = [x for x in uniq if x is not keep[0]]
    conn = [x for x in parts if x.BoundBox.YMin < -13.0 and x.BoundBox.XLength < 11]
    if len(conn) != 1: raise RuntimeError(f"{fn}: {len(conn)} connectors")
    return Part.makeCompound(parts), keep[0], conn[0]

try:
    errs, finds = [], []
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    leaves0 = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: gbox(o) for o in leaves0}; label0 = {o.Name: o.Label for o in leaves0}
    car = one(CARRIAGE[1], CARRIAGE[0]); sc = gshape(car)
    copies = {k: one(c, d) for k, (d, c) in COPIES.items()}
    T = {k: com(gshape(c)) - com(sc) for k, c in copies.items()}
    for k, t in T.items(): log(f"{k}: dock carriage copy = gantry carriage + ({t.x:.3f}, {t.y:.3f}, {t.z:.3f})")
    # mount holes and ceiling
    hz = sorted({(round(f.Surface.Center.x, 3), round(f.Surface.Center.y, 3), round(f.BoundBox.ZMin, 3)) for f in sc.Faces
                 if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 1.26) < 0.01 and abs(f.Surface.Axis.z) > 0.999})
    if len(hz) != 2 or abs(hz[0][1] - hz[1][1]) > 1e-3 or abs(hz[0][2] - hz[1][2]) > 1e-3:
        raise RuntimeError(f"carriage probe holes: {hz}")
    xc = (hz[0][0] + hz[1][0]) / 2; yh = hz[0][1]; z_ceil = hz[0][2]; span = abs(hz[1][0] - hz[0][0])
    log(f"carriage probe holes at X {hz[0][0]:.2f} / {hz[1][0]:.2f} (span {span:.2f}), Y {yh:.2f}; pocket ceiling Z {z_ceil:.2f}; "
        f"carriage underside Z {sc.BoundBox.ZMin:.2f}")
    if abs(span - 31.6) > 0.1: errs.append(f"probe hole span {span:.2f}, Beacon slots are 31.6 apart")
    # carried nozzle tip (relative to the gantry carriage)
    tips = {}
    for k, g in HEADS.items():
        nz = [o for o in descendants(one(g)) if is_leaf(o) and o.Label.startswith(NOZZLE)]
        if len(nz) != 1: raise RuntimeError(f"{k}: {len(nz)} nozzles")
        tips[k] = gbox(nz[0]).ZMin - T[k].z
    tip = max(tips.values())
    log(f"carried nozzle tips Z {tips}; using {tip:.3f}")
    z_face = tip + H; z_top = z_face + 4.21; dz = z_top - z_ceil
    log(f"coil face target Z {z_face:.3f} (tip + {H}); board top {z_top:.3f}; ceiling raise DZ {dz:.3f} "
        f"(as drilled: face {z_ceil - 4.21 - tip:+.3f} above the tip)")
    if dz < 0: raise RuntimeError("the pocket is already deep enough; nothing to cut (re-check before going on)")
    hole_depth = None
    for f in sc.Faces:
        if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 1.26) < 0.01: hole_depth = f.BoundBox.ZMax - z_top
    log(f"M3 pilot holes keep {hole_depth:.2f} mm above the new ceiling")
    if hole_depth < 4.0: errs.append(f"M3 pilot holes only {hole_depth:.2f} deep after the cut")
    # candidates
    others = {}
    for k in HEADS:
        d, labs = RIDE[k]
        others[k] = [o for o in descendants(one(HEADS[k])) if is_leaf(o) and not o.Label.startswith('Bowden ')] + [one(l, d) for l in labs]
    cands = []
    for vname, fn in VARIANTS.items():
        parts, keep, conn = load_beacon(fn)
        for rot in (0, 180):
            pl = FreeCAD.Placement(V(xc, yh + (3.5 if rot == 0 else -3.5), z_top), FreeCAD.Rotation(V(0, 0, 1), rot))
            b = parts.copy(); b.Placement = pl.multiply(b.Placement)
            k_ = keep.copy(); k_.Placement = pl.multiply(k_.Placement)
            cn = conn.copy(); cn.Placement = pl.multiply(cn.Placement)
            bb = b.BoundBox
            # pocket: board footprint (+ connector) from the old ceiling up to the board top, plus the connector's own
            # clearance where it rises above the board
            board = Part.makeBox(bb.XLength + 2 * CLEAR, bb.YLength + 2 * CLEAR, z_top - z_ceil + 0.02,
                                 V(bb.XMin - CLEAR, bb.YMin - CLEAR, z_ceil - 0.01))
            cb = cn.BoundBox
            cut = board
            if cb.ZMax > z_top:
                cut = board.fuse(Part.makeBox(cb.XLength + 2 * CLEAR, cb.YLength + 2 * CLEAR, cb.ZMax - z_top + CLEAR,
                                              V(cb.XMin - CLEAR, cb.YMin - CLEAR, z_top - 0.01)))
            if vname == "Normal":
                plug = Part.makeBox(cb.XLength, cb.YLength, PLUG, V(cb.XMin, cb.YMin, cb.ZMax))
            else:
                y0 = cb.YMin - PLUG if rot == 0 else cb.YMax
                plug = Part.makeBox(cb.XLength, PLUG, cb.ZLength, V(cb.XMin, y0, cb.ZMin))
            removed = sc.common(cut).Volume
            new_c = sc.cut(cut)
            hits = []
            for what, sh in (("Beacon", b), ("plug way-in", plug)):
                for k in HEADS:
                    bt = sh.copy(); bt.translate(T[k])
                    for o in others[k]:
                        if not gbox(o).intersect(bt.BoundBox): continue
                        v = bt.common(gshape(o)).Volume
                        if v > 0.01: hits.append(f"{what}, {k} head carried: {o.Label} {v:.2f} mm3")
                for o in leaves0:     # anything else on the gantry/carriage at the model pose
                    if o.Name == car.Name or not gbox(o).intersect(sh.BoundBox): continue
                    v = sh.common(gshape(o)).Volume
                    if v > 0.01: hits.append(f"{what}, model pose: {o.Label} {v:.2f} mm3")
                v_car = sh.common(new_c).Volume
                if v_car > 0.01: hits.append(f"{what}: carriage after the cut {v_car:.2f} mm3")
            ok = not hits and new_c.isValid() and len(new_c.Solids) == len(sc.Solids)
            log(f"candidate {vname}, connector {'front' if rot == 0 else 'rear'}: carriage material removed {removed:.1f} mm3; "
                f"carriage valid {new_c.isValid()} solids {len(new_c.Solids)}; {len(hits)} overlaps" + ("".join("\n      " + h for h in hits)))
            cands.append(dict(ok=ok, removed=removed, name=vname, rot=rot, b=b, keep=k_, cut=cut, new_c=new_c))
    good = sorted([c for c in cands if c["ok"]], key=lambda c: (c["rot"] != 180, round(c["removed"], 1)))
    if not good: raise RuntimeError("no Beacon variant/orientation fits")
    pick = good[0]
    log(f"chosen: Beacon RevH {pick['name']}, connector to the {'front' if pick['rot'] == 0 else 'rear'} "
        f"(removes {pick['removed']:.1f} mm3 of carriage)")
    finds.append(f"Beacon RevH {pick['name']}, connector {'front' if pick['rot'] == 0 else 'rear'}; coil face {H} mm above the "
                 f"carried nozzle tip; carriage pocket ceiling raised {dz:.2f} mm")
    # apply the cut to the gantry carriage and both copies (same cut, moved by T)
    ap = look(car); set_global_shape(car, pick["new_c"]); restore_look(car, ap)
    for k, c in copies.items():
        s0 = gshape(c); cut = pick["cut"].copy(); cut.translate(T[k]); n = s0.cut(cut)
        dv = abs((s0.Volume - n.Volume) - pick["removed"])
        log(f"{k} copy: removed {s0.Volume - n.Volume:.1f} mm3 (gantry carriage {pick['removed']:.1f}); valid {n.isValid()}")
        if dv > 0.05 or not n.isValid(): errs.append(f"{k} copy: cut differs from the gantry carriage's by {dv:.2f} mm3")
        ap = look(c); set_global_shape(c, n); restore_look(c, ap)
    # place the Beacon under the gantry carriage's group
    par = parent_of(car)
    n = doc.addObject('Part::Feature', 'Beacon'); n.Shape = Part.Shape()
    if par is not None: par.addObject(n)
    set_global_shape(n, pick["b"])
    n.Label = f"Beacon RevH {pick['name']} (Beacon CAD, MIT)"
    try: n.ViewObject.ShapeAppearance[0].DiffuseColor = (0.1, 0.35, 0.8)
    except Exception: pass
    doc.recompute(); _BOX.clear()
    # checks
    gb = gshape(n).BoundBox
    log(f"Beacon: X {gb.XMin:.2f}..{gb.XMax:.2f} Y {gb.YMin:.2f}..{gb.YMax:.2f} Z {gb.ZMin:.2f}..{gb.ZMax:.2f}; coil face "
        f"{gb.ZMin - tip:+.3f} above the carried tip")
    coil_c = V(xc, yh + (3.5 if pick["rot"] == 0 else -3.5), 0)       # coil axis at the board origin (STEP: coil r7.98 at y +0.52)
    for k in HEADS:
        nzb = gbox([o for o in descendants(one(HEADS[k])) if is_leaf(o) and o.Label.startswith(NOZZLE)][0])
        nx, ny = (nzb.XMin + nzb.XMax) / 2 - T[k].x, (nzb.YMin + nzb.YMax) / 2 - T[k].y
        log(f"{k} head carried: Beacon coil centre at x_offset {coil_c.x - nx:+.2f}, y_offset {coil_c.y - ny:+.2f} from the nozzle")
        finds.append(f"{k} head: Beacon x_offset {coil_c.x - nx:+.2f}, y_offset {coil_c.y - ny:+.2f} (Klipper [beacon], +Y = rear)")
    if abs((gb.ZMin - tip) - H) > 0.01: errs.append(f"coil face {gb.ZMin - tip:.3f} above the tip, want {H}")
    metal = []
    for o in doc.Objects:
        if not is_leaf(o) or o.Name == n.Name: continue
        if gbox(o).intersect(pick["keep"].BoundBox) and gshape(o).common(pick["keep"]).Volume > 0.01: metal.append(o.Label)
    log(f"inside Beacon's 20 mm keep-out cylinder over the coil (model pose): {metal or 'nothing'}")
    finds.append(f"inside the keep-out cylinder: {', '.join(metal) if metal else 'nothing'} (printed carriage plastic is fine; metal isn't)")
    now = {o.Name: o for o in doc.Objects if is_leaf(o)}
    changed = {car.Name} | {c.Name for c in copies.values()}
    for nm, b in before.items():
        if nm in changed: continue
        if nm not in now: errs.append(f"lost {label0[nm]}"); continue
        if not close(gbox(now[nm]), b): errs.append(f"changed: {now[nm].Label}")
    m = MeshPart.meshFromShape(Shape=pick["new_c"], LinearDeflection=0.02, AngularDeflection=0.2)
    fn = f"{WORK}/stl/madmax_carriage_beacon_pocket.stl"; m.write(fn); log(f"STL {os.path.relpath(fn, WORK)}: {m.CountFacets} facets")
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
