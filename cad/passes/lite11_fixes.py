# GUI pass: vt350-lite-10.FCStd -> vt350-lite-11.FCStd   (headless = dry run, never saves)
# Fixes the user found looking at lite-10:
#  1) Bowden tubes floated 35.5 mm above the couplers: lite10_ztravel.py placed the tube solid in the coordinate frame
#     of its parent's parent instead of its parent (an App::Part). Rebuilt from the stored route (Inlet, ExitPoint,
#     handles) in the right frame; the tube must now start at the coupler top.
#  2) Four orphan M3x8 screws (Door (1) (1) / Fasteners (1)): in lite-5-dan they held the printed front motorless mounts
#     (lite-6 replaced those with the milled ones); filed under the Door group, they rode along with the door and have
#     floated since lite-6. Deleted.
#  3) Clicky-Clack latch: Hinge_Bottom sat 10.2 mm below the handle (Hinge_Top is flush on top; already so in
#     lite-5-dan). Moved up to the handle's bottom face, with its fasteners; the shift is measured, not typed.
# Checks: tubes valid and touching nothing but their couplers; Hinge_Bottom flush, no new overlaps; everything else
# unchanged. Refuses to save otherwise.
import FreeCAD, Part, sys, os, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-10.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-11.FCStd"
DRY = not FreeCAD.GuiUp
INLETS = {"Left": "4mm Bowden Coupler v1 (1)", "Right": "4mm Bowden Coupler v1 (1) (1)"}
ORPHANS = ("Fasteners (1)", "Door (1) (1)")            # group label, required ancestor
HINGE_BOTTOM, HANDLE = "Hinge_Bottom (1)", "Handle (1)"
HW = ('T-nut', 'SHCS', 'BHCS', 'Screw', 'Washer', 'washer', 'shim', 'Nut', 'Insert', 'pin', 'Dowel', 'magnet')
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite11_fixes.log", "w"); t0 = time.time()
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
    """global placement of the coordinate frame a child of `par` lives in"""
    if par is None: return FreeCAD.Placement()
    if par.isDerivedFrom('App::Part'): return par.getGlobalPlacement()
    for p in ancestors(par):
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
    return FreeCAD.Placement()
def container_global(o): return frame_of_parent(parent_of(o))
def descendants(g):
    out = []
    for c in getattr(g, 'Group', []):
        out.append(c); out += descendants(c)
    return out
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def is_hw(lab): return any(k in lab for k in HW)
def shifted(b, v): return FreeCAD.BoundBox(b.XMin + v.x, b.YMin + v.y, b.ZMin + v.z, b.XMax + v.x, b.YMax + v.y, b.ZMax + v.z)
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax), (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
def translate_global(o, T):
    par_g = container_global(o); g = o.getGlobalPlacement()
    o.Placement = par_g.inverse().multiply(FreeCAD.Placement(T, FreeCAD.Rotation())).multiply(g)
def one(label, cond=lambda o: True):
    c = [o for o in doc.getObjectsByLabel(label) if cond(o)]
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {label!r}")
    return c[0]
def overlaps(objs_a, objs_all, skip=lambda a, b: False):
    out = {}
    for a in objs_a:
        sa = None
        for b in objs_all:
            if a.Name == b.Name or skip(a, b) or not gbox(a).intersect(gbox(b)): continue
            try:
                sa = sa or gshape(a); v = sa.common(gshape(b)).Volume
            except Exception: continue
            if v > 1.0: out[(a.Name, b.Name)] = v
    return out

try:
    errs = []
    doc = FreeCAD.openDocument(SRC)
    log("opened", SRC, len(doc.Objects))
    leaves0 = [o for o in doc.Objects if is_leaf(o)]
    before = {o.Name: gbox(o) for o in leaves0}; label0 = {o.Name: o.Label for o in leaves0}
    tubes0 = [o for o in leaves0 if o.Label.startswith('Bowden ')]
    # ---- 2) orphan screws
    g = one(ORPHANS[0], lambda o: any(a.Label == ORPHANS[1] for a in ancestors(o)))
    orph = list({x.Name: x for x in descendants(g) if is_leaf(x)}.values())
    allsolid = [o for o in leaves0 if o not in orph and not is_hw(o.Label)]
    for x in orph:
        xb = gbox(x); e = FreeCAD.BoundBox(xb.XMin - 0.3, xb.YMin - 0.3, xb.ZMin - 0.3, xb.XMax + 0.3, xb.YMax + 0.3, xb.ZMax + 0.3)
        t = [o.Label for o in allsolid if e.intersect(gbox(o)) and gshape(x).distToShape(gshape(o))[0] < 0.3]
        log(f"orphan {x.Label}: Z {xb.ZMin:.1f}..{xb.ZMax:.1f}, touches {t or 'nothing'}")
    removed = {x.Name for x in orph}
    for x in reversed([g] + descendants(g)):
        try: doc.removeObject(x.Name)
        except Exception: pass
    log(f"removed {len(orph)} orphan screws and their group")
    if len(orph) != 4: errs.append(f"expected 4 orphan screws, found {len(orph)}")
    # ---- 3) Clicky-Clack Hinge_Bottom
    hb_g = one(HINGE_BOTTOM); hd_g = one(HANDLE)
    hb_l = list({x.Name: x for x in descendants(hb_g) if is_leaf(x)}.values()); hd_body = [x for x in descendants(hd_g) if is_leaf(x) and not is_hw(x.Label)]
    hb_body = [x for x in hb_l if not is_hw(x.Label)]
    if len(hb_body) != 1 or len(hd_body) != 1: raise RuntimeError(f"latch bodies: {len(hb_body)} / {len(hd_body)}")
    dz = gbox(hd_body[0]).ZMin - gbox(hb_body[0]).ZMax
    log(f"Hinge_Bottom top Z {gbox(hb_body[0]).ZMax:.2f}, handle bottom Z {gbox(hd_body[0]).ZMin:.2f}: moving Hinge_Bottom up {dz:+.2f}")
    if not (0 < dz < 20): errs.append(f"unexpected latch gap {dz:.2f}")
    b0 = {x.Name: gbox(x) for x in hb_l}; T = V(0, 0, dz)
    for x in hb_l:
        if not is_hw(x.Label): translate_global(x, T)
    doc.recompute(); _BOX.clear()
    for x in hb_l:
        if is_hw(x.Label) and not close(gbox(x), shifted(b0[x.Name], T)): translate_global(x, T)
    _BOX.clear()
    moved = {x.Name: T for x in hb_l}
    mg = [x for x in descendants(hb_g) if 'magnet' in x.Label] ; hm = [x for x in descendants(hd_g) if 'magnet' in x.Label and gbox(x).YMax < -110]
    if mg and hm:
        gap = min(gbox(h).ZMin for h in hm) - max(gbox(m).ZMax for m in mg)
        log(f"latch magnets: bottom pair gap {gap:.2f} mm (top pair, Hinge_Top vs handle: for comparison)")
    # ---- 1) bowden tubes
    made = []; tube_names = [t.Name for t in tubes0]
    for t in tubes0:
        side = t.Label.split()[1]
        P0 = V(t.Inlet); P1 = V(t.ExitPoint); ED = V(t.ExitDir); a = t.HandleInlet.Value; b = t.HandleExit.Value; BY = t.Beyond.Value; OD = t.OD.Value
        cb = gbox(one(INLETS[side]))
        if abs(P0.z - cb.ZMax) > 0.05: errs.append(f"tube {side}: stored inlet Z {P0.z:.2f} != coupler top {cb.ZMax:.2f}")
        log(f"tube {side}: was Z {gbox(t).ZMin:.1f}..{gbox(t).ZMax:.1f}; inlet {P0.z:.1f} (coupler top {cb.ZMax:.1f}); off by {gbox(t).ZMin - P0.z:+.1f}")
        c = Part.BezierCurve(); c.setPoles([P0, P0 + V(0, 0, a), P1 - ED * b, P1])
        path = Part.Wire([c.toShape(), Part.LineSegment(P1, P1 + ED * BY).toShape()])
        tube = path.makePipeShell([Part.Wire(Part.makeCircle(OD / 2, P0, V(0, 0, 1)))], True, True)
        rmin = min(1 / max(c.curvature(i / 400), 1e-12) for i in range(401))
        par = parent_of(t); Cg = frame_of_parent(par)
        props = {p: getattr(t, p) for p in ('OD', 'Inlet', 'ExitPoint', 'ExitDir', 'HandleInlet', 'HandleExit', 'Beyond', 'MinBendRadius', 'PathLength')}
        view = None
        try: view = t.ViewObject.ShapeAppearance if t.ViewObject is not None else None
        except Exception: pass
        doc.removeObject(t.Name)
        loc = tube.copy(); loc.Placement = Cg.inverse().multiply(loc.Placement)
        n = doc.addObject('Part::Feature', 'BowdenTube'); n.Shape = loc
        if par is not None: par.addObject(n)
        n.Label = f"Bowden {side}"
        for p, v in props.items():
            typ = 'App::PropertyVector' if p in ('Inlet', 'ExitPoint', 'ExitDir') else 'App::PropertyLength'
            n.addProperty(typ, p, 'Bowden', 'route parameters (global mm); regenerate by script for other poses'); setattr(n, p, v)
        if view is not None and n.ViewObject is not None:
            try: n.ViewObject.ShapeAppearance = view
            except Exception: pass
        nb = gshape(n).BoundBox
        log(f"   rebuilt: Z {nb.ZMin:.2f}..{nb.ZMax:.2f} (starts {nb.ZMin - P0.z:+.2f} from the inlet), min bend R {rmin:.1f}, valid {tube.isValid()}")
        if abs(nb.ZMin - P0.z) > 0.05 or not tube.isValid(): errs.append(f"tube {side}: not at its inlet after rebuild")
        made.append(n)
    doc.recompute(); _BOX.clear()
    allnow = [o for o in doc.Objects if is_leaf(o)]
    tov = overlaps(made, allnow, skip=lambda a, b: b in made or b.Label in INLETS.values())
    log(f"tubes: {len(tov)} overlaps > 1 mm3 with other parts")
    for (a, b), v in sorted(tov.items(), key=lambda kv: -kv[1]):
        A, B = doc.getObject(a), doc.getObject(b); p = parent_of(B)
        log(f"     {v:8.1f} mm3  {A.Label} x {B.Label} [{p.Label if p else ''}]")
        errs.append(f"{A.Label} overlaps {B.Label} ({v:.1f} mm3)")
    # Hinge_Bottom: new overlaps (vs the same check before the move)
    now = {o.Name: o for o in doc.Objects}
    hb_now = [now[n] for n in moved]
    ov = overlaps(hb_now, allnow, skip=lambda a, b: b.Name in moved)
    log(f"Hinge_Bottom after the move: {len(ov)} overlaps > 1 mm3")
    for (a, b), v in sorted(ov.items(), key=lambda kv: -kv[1]):
        A, B = now[a], now[b]; p = parent_of(B)
        kind = "hardware" if is_hw(A.Label) or is_hw(B.Label) else "PART"
        log(f"     {kind:8} {v:8.1f} mm3  {A.Label} x {B.Label} [{p.Label if p else ''}]")
        if kind == "PART": errs.append(f"Hinge_Bottom: {A.Label} overlaps {B.Label} ({v:.1f} mm3)")
    # ---- verify
    tn = set(tube_names)
    for nm, b in before.items():
        if nm in removed or nm in tn: continue
        if nm not in now: errs.append(f"lost {label0[nm]}"); continue
        exp = shifted(b, moved[nm]) if nm in moved else b
        if not close(gbox(now[nm]), exp): errs.append(f"{'moved wrongly' if nm in moved else 'changed'}: {now[nm].Label}")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
