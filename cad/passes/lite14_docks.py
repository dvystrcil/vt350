# GUI pass: vt350-lite-13.FCStd -> vt350-lite-14.FCStd   (headless = dry run, never saves)
# Docks back so the carriage can reach the docked heads.
#  The MadMax XOL dock assembly carries a copy of the MadMax carriage at its pickup pose (same part as the gantry's:
#  equal volume, area and size): its front face is at Y -24.00. The gantry carriage reaches Y -21.19 before the XY
#  joints hit the milled front mounts (lite-8/9 reach analysis), so pickup was 2.81 mm out of reach. (The README's
#  earlier "6.8 mm" measured to the A4T's back face instead of the carriage pose.)
#  Fix: docks + docked heads move back DOCK_BACK; the printed dock arms ("Dock Arm v1 Bottom") get DOCK_BACK longer
#  through their straight section, so their mounts on the front verticals don't move. Bowden tubes regenerated from
#  the moved couplers. Checks: reach margin, arm volume, new collisions vs lite-13, everything else unchanged.
#  Exports the lengthened arms as STL for printing.
import FreeCAD, Part, Mesh, MeshPart, sys, os, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-13.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-14.FCStd"
DRY = not FreeCAD.GuiUp
DOCK_BACK = 5.0          # mm (+Y). Needed 2.81; the rest keeps the pickup ~2.2 mm short of the joint/mount hard stop
REACH_Y = -21.19         # gantry carriage front face at the front travel limit (lite9_rails.log, unchanged since)
CUT_Y = -53.61           # arm's straight section (constant 193.2 mm^2 from Y -57.6 to -49.6), global Y
GROUPS = ["Left Dock", "Right Dock", "Left Toolhead", "Right Toolhead"]
ARMS = ["Dock Arm v1 Bottom", "Dock Arm v1 Bottom(Mirror)"]
POSE = "MadMaxCarriage"  # the docked carriage copies live in MadMax 4 XOL ... / Carriage / MadMaxCarriage
INLETS = {"Left": "4mm Bowden Coupler v1 (1)", "Right": "4mm Bowden Coupler v1 (1) (1)"}
os.makedirs(WORK + "/logs", exist_ok=True); os.makedirs(WORK + "/stl", exist_ok=True)
log_f = open(WORK + "/logs/lite14_docks.log", "w"); t0 = time.time()
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

def look(o):
    vo = getattr(o, 'ViewObject', None)
    return [(a.DiffuseColor, a.Transparency) for a in vo.ShapeAppearance] if vo is not None and hasattr(vo, 'ShapeAppearance') else None
def set_global_shape(o, s):
    """replace o's shape with global-coordinate shape s, keeping o in its container"""
    loc = s.copy(); loc.Placement = container_global(o).inverse().multiply(loc.Placement); o.Shape = loc
def lengthen(s, y, d):
    """split solid s at plane Y=y, move the +Y part by d, fill the gap with the section extruded"""
    b = s.BoundBox; big = 1000
    lo = s.common(Part.makeBox(big, y - b.YMin + 1, big, V(b.XMin - 1, b.YMin - 1, b.ZMin - 1).add(V(-big / 2, 0, -big / 2))))
    hi = s.common(Part.makeBox(big, b.YMax - y + 1, big, V(b.XMin - 1, y, b.ZMin - 1).add(V(-big / 2, 0, -big / 2))))
    hi.translate(V(0, d, 0))
    wires = s.slice(V(0, 1, 0), y)
    face = Part.makeFace(wires, "Part::FaceMakerBullseye")
    fill = face.extrude(V(0, d, 0))
    parts = lo.Solids + fill.Solids + hi.Solids      # the arm is a compound of 2 solids; fuse solid by solid
    r = parts[0].multiFuse(parts[1:]).removeSplitter()
    return r, face.Area
try:
    errs = []
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    leaves0 = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: gbox(o) for o in leaves0}; label0 = {o.Name: o.Label for o in leaves0}
    groups = [one(g) for g in GROUPS]
    moved = {x.Name for g in groups for x in descendants(g) if is_leaf(x)}
    arms = [one(a) for a in ARMS]
    tubes0 = [o for o in leaves0 if o.Label.startswith('Bowden ')]
    tube_names = {t.Name for t in tubes0}
    special = {a.Name for a in arms} | tube_names
    poses = [o for o in leaves0 if POSE in getattr(parent_of(o), 'Label', '') and 'Carriage (1)' not in [a.Label for a in ancestors(o)]]
    if len(poses) != 2: raise RuntimeError(f"{len(poses)} docked carriage copies")
    for p in poses: log(f"docked carriage copy {p.Label}: front face Y {gbox(p).YMin:.2f}; reach {REACH_Y:.2f} -> margin {gbox(p).YMin - REACH_Y:+.2f}")
    T = V(0, DOCK_BACK, 0)
    # baseline overlaps of everything that moves (incl. arms) vs everything else, at lite-13
    movers0 = [o for o in leaves0 if o.Name in moved and o.Name not in tube_names]
    skip = lambda a, b: b.Name in moved
    ov0 = overlaps(movers0, leaves0, skip); log(f"lite-13 overlaps of the moving parts with the rest: {len(ov0)}")
    arm0 = {a.Name: gshape(a) for a in arms}
    app0 = {o.Name: look(o) for o in arms}
    # move the groups (App::Parts) and lengthen the arms
    for g in groups: translate_global(g, T)
    doc.recompute(); _BOX.clear()
    for a in arms:
        s0 = arm0[a.Name]
        sec0 = s0.common(Part.makeBox(2000, 0.2, 2000, V(-1000, CUT_Y - 0.1, -1000))).Volume / 0.2
        sec1 = s0.common(Part.makeBox(2000, 0.2, 2000, V(-1000, CUT_Y - 4.1, -1000))).Volume / 0.2
        if abs(sec0 - sec1) > 0.5: errs.append(f"{a.Label}: section not constant around Y {CUT_Y} ({sec0:.1f} vs {sec1:.1f})")
        s1, fa = lengthen(s0, CUT_Y, DOCK_BACK)
        want = s0.Volume + fa * DOCK_BACK
        log(f"{a.Label}: section {fa:.1f} mm2 at Y {CUT_Y}; volume {s0.Volume:.1f} -> {s1.Volume:.1f} (want {want:.1f}); valid {s1.isValid()}, solids {len(s1.Solids)} (was {len(s0.Solids)})")
        if abs(s1.Volume - want) > 0.5 or not s1.isValid() or len(s1.Solids) != len(s0.Solids): errs.append(f"{a.Label}: bad lengthened shape")
        b0, b1 = s0.BoundBox, s1.BoundBox
        if abs(b1.YMin - b0.YMin) > 1e-3 or abs(b1.YMax - b0.YMax - DOCK_BACK) > 1e-3: errs.append(f"{a.Label}: mount end moved or dock end not +{DOCK_BACK}")
        set_global_shape(a, s1)
        a.Label = a.Label.replace("Dock Arm v1 Bottom", f"Dock Arm v1 Bottom +{DOCK_BACK:g}mm")
        if app0[a.Name] is not None:
            ap = a.ViewObject.ShapeAppearance
            if len(ap) != len(app0[a.Name]):
                a.ViewObject.ShapeAppearance = [ap[0]] if ap else ap
            for x in a.ViewObject.ShapeAppearance: x.DiffuseColor = app0[a.Name][0][0]
        Mesh.export([a], f"{WORK}/stl/{a.Label.replace(' ', '_').replace('(', '').replace(')', '').replace('+', 'plus')}.stl") if False else None
        m = MeshPart.meshFromShape(Shape=s1, LinearDeflection=0.02, AngularDeflection=0.2)
        fn = f"{WORK}/stl/dock_arm_v1_bottom_plus{DOCK_BACK:g}mm{'_mirror' if 'Mirror' in a.Label else ''}.stl"
        m.write(fn); log(f"   STL {os.path.relpath(fn, WORK)}: {m.CountFacets} facets")
    doc.recompute(); _BOX.clear()
    for a in arms:
        g = gbox(a); b0 = arm0[a.Name].BoundBox
        if abs(g.YMin - b0.YMin) > 1e-3 or abs(g.YMax - b0.YMax - DOCK_BACK) > 1e-3: errs.append(f"{a.Label}: placed wrong ({g.YMin:.2f}..{g.YMax:.2f})")
    for p in poses:
        log(f"docked carriage copy {p.Label}: front face now Y {gbox(p).YMin:.2f}; margin to the hard stop {gbox(p).YMin - REACH_Y:+.2f}")
        if gbox(p).YMin - REACH_Y < 0.5: errs.append(f"{p.Label}: still out of reach")
    # bowden tubes (inlets moved with the left/right toolheads; exits fixed)
    made = []
    for t in tubes0:
        side = t.Label.split()[1]
        cb = gbox(one(INLETS[side]))
        P0 = V((cb.XMin + cb.XMax) / 2, (cb.YMin + cb.YMax) / 2, cb.ZMax)
        old = V(t.Inlet)
        log(f"tube {side}: coupler top now {P0.x:.2f},{P0.y:.2f},{P0.z:.2f} (was {old.x:.2f},{old.y:.2f},{old.z:.2f})")
        if (P0 - old - T).Length > 0.05: errs.append(f"tube {side}: coupler moved {P0 - old}, expected {T}")
        P1 = V(t.ExitPoint); ED = V(t.ExitDir); a_ = t.HandleInlet.Value; b_ = t.HandleExit.Value; BY = t.Beyond.Value; OD = t.OD.Value
        c = Part.BezierCurve(); c.setPoles([P0, P0 + V(0, 0, a_), P1 - ED * b_, P1])
        path = Part.Wire([c.toShape(), Part.LineSegment(P1, P1 + ED * BY).toShape()])
        tube = path.makePipeShell([Part.Wire(Part.makeCircle(OD / 2, P0, V(0, 0, 1)))], True, True)
        rmin = min(1 / max(c.curvature(i / 400), 1e-12) for i in range(401))
        props = {p: getattr(t, p) for p in ('OD', 'Inlet', 'ExitPoint', 'ExitDir', 'HandleInlet', 'HandleExit', 'Beyond', 'MinBendRadius', 'PathLength')}
        props['Inlet'] = P0; props['MinBendRadius'] = rmin; props['PathLength'] = path.Length
        par = parent_of(t); Cg = frame_of_parent(par); app = look(t)
        doc.removeObject(t.Name)
        loc = tube.copy(); loc.Placement = Cg.inverse().multiply(loc.Placement)
        n = doc.addObject('Part::Feature', 'BowdenTube'); n.Shape = loc
        if par is not None: par.addObject(n)
        n.Label = f"Bowden {side}"
        for p, v in props.items():
            typ = 'App::PropertyVector' if p in ('Inlet', 'ExitPoint', 'ExitDir') else 'App::PropertyLength'
            n.addProperty(typ, p, 'Bowden', 'route parameters (global mm); regenerate by script for other poses'); setattr(n, p, v)
        if app is not None:
            try:
                ap = n.ViewObject.ShapeAppearance
                for x in ap: x.DiffuseColor = app[0][0]; x.Transparency = app[0][1]
                n.ViewObject.ShapeAppearance = ap
            except Exception: pass
        doc.recompute(); _BOX.clear()
        nb = gshape(n).BoundBox
        log(f"   rebuilt: starts {nb.ZMin - P0.z:+.2f} from the coupler top; min bend R {rmin:.1f}; length {path.Length:.1f}; valid {tube.isValid()}")
        if abs(nb.ZMin - P0.z) > 0.05 or not tube.isValid() or rmin < 100: errs.append(f"tube {side}: bad rebuild")
        made.append(n)
    # collisions after
    now = {o.Name: o for o in doc.Objects if is_leaf(o)}
    allnow = list(now.values())
    movers1 = [now[n] for n in moved if n in now and n not in tube_names]
    ov1 = overlaps(movers1, allnow, skip)
    new = {k: v for k, v in ov1.items() if k not in ov0 or v > ov0[k] + 1.0}
    log(f"moving parts vs the rest: {len(ov1)} overlaps ({len(new)} new or larger than in lite-13)")
    for (a_, b_), v in sorted(new.items(), key=lambda kv: -kv[1]):
        A, B = now[a_], now[b_]; p = parent_of(B)
        log(f"     {v:8.1f} mm3  {A.Label} x {B.Label} [{p.Label if p else ''}]  (lite-13: {ov0.get((a_, b_), 0):.1f})")
        errs.append(f"new overlap {A.Label} x {B.Label} ({v:.1f} mm3)")
    tov = overlaps(made, allnow, skip=lambda a, b: b in made or b.Label in INLETS.values())
    log(f"tubes: {len(tov)} overlaps")
    for (a_, b_), v in tov.items(): errs.append(f"{now[a_].Label} overlaps {now[b_].Label} ({v:.1f} mm3)")
    # verify
    for nm, b in before.items():
        if nm in tube_names: continue
        if nm not in now: errs.append(f"lost {label0[nm]}"); continue
        if nm in special: continue
        exp = shifted(b, T) if nm in moved else b
        if not close(gbox(now[nm]), exp): errs.append(f"{'moved wrongly' if nm in moved else 'changed'}: {now[nm].Label}")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
