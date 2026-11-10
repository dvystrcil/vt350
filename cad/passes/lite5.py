# GUI pass: vt350-lite-4.FCStd -> vt350-lite-5.FCStd   (headless = dry run, never saves)
#  1) the six verticals get their drilled side holes back: lite-3 rebuilt them as plain extrusions of
#     their end face (losing every side hole). Here the ORIGINAL drilled bars from lite-2 are spliced
#     at Z=534 (+100 mm of their own cross-section) and swapped in.
#  2) INDX parts removed (INDX DUMMY, NOZZLE TOOL).
#  3) one bowden tube per head: solid rod, OD 4.12 mm (measured), cubic Bezier from the Orbiter
#     inlet (+Z) to a top-rear exit (Y 460, Z 690, tilted 45 deg to the rear), +30 mm beyond.
#  Verifies everything else is untouched; refuses to save on any mismatch.
import FreeCAD, Part, sys, os, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
SCR = "/tmp/claude-1000/-home-dan-Code/b279da99-5634-4c88-a9ae-89fd7f47818b/scratchpad"
OLD = "/home/dan/Documents/VT350/vt350-lite-2.FCStd"   # drilled bars
SRC = "/home/dan/Documents/VT350/vt350-lite-4.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-5.FCStd"
DRY = not FreeCAD.GuiUp
ZC, DZ = 534.0, 100.0
BARS = ["2040", "4040", "4040(Mirror)", "2040(Mirror)", "2040 (1)", "2040 (1)(Mirror)"]
INDX = {"Part__Feature2883": "INDX DUMMY", "Part__Feature2884": "NOZZLE TOOL"}
# (screw, washer) SourceNames in vt350-good: M5x16 in the un-drilled row at each rear 4040 joint
NO_HOLE = [(f"Part__Feature{a:03d}", f"Part__Feature{a+1:03d}") for a in
           (26, 58, 60, 64, 66, 74, 136, 106, 108, 112, 114, 122, 124, 140, 144)]
OD = 4.12
EXIT_Y, EXIT_Z, EXIT_DIR, HANDLES, BEYOND = 460.0, 690.0, V(0, 1, 1).normalize(), (240.0, 160.0), 30.0
INLETS = {"Left": "4mm Bowden Coupler v1 (1)", "Right": "4mm Bowden Coupler v1 (1) (1)"}
log_f = open(SCR + "/lite5.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()

def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
def gbox(o):
    s = gshape(o)
    try: return s.optimalBoundingBox(True, False)
    except Exception: return s.BoundBox
def parent_of(o):
    return next((x for x in o.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))
                 and o in getattr(x, 'Group', [])), None)
def container_global(o):
    p = o
    while True:
        p = parent_of(p)
        if p is None: return FreeCAD.Placement()
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
def side_holes(s):
    """cylindrical faces whose axis is horizontal (global shape of a vertical bar)"""
    n = 0
    for f in s.Faces:
        if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Axis.z) < 1e-6: n += 1
    return n
def copy_view(src, dst):
    if src.ViewObject is None or dst.ViewObject is None: return
    for prop in ('ShapeAppearance', 'ShapeColor', 'DiffuseColor', 'LineColor', 'Transparency', 'Visibility'):
        try: setattr(dst.ViewObject, prop, getattr(src.ViewObject, prop))
        except Exception: pass
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax),
                                                    (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))

try:
    errs = []
    # ---- 1a) splice the drilled bars from lite-2 (global coordinates) ----
    od = FreeCAD.openDocument(OLD)
    spliced = {}
    up = V(0, 0, 1)
    for lab in BARS:
        cand = od.getObjectsByLabel(lab)
        if len(cand) != 1: raise RuntimeError(f"lite-2: {len(cand)} objects labelled {lab!r}")
        s = gshape(cand[0]); bb = s.BoundBox; big = 5000
        ends = [f for f in s.Faces if isinstance(f.Surface, Part.Plane) and abs(abs(f.normalAt(0, 0).z) - 1) < 1e-6]
        end_area = min(ends, key=lambda f: f.CenterOfMass.z).Area
        sec = Part.makeFace(s.slice(up, ZC), 'Part::FaceMakerBullseye')
        if abs(sec.Area - end_area) > 1e-3:
            raise RuntimeError(f"{lab}: section at Z={ZC} ({sec.Area:.2f}) != end face ({end_area:.2f}) -> a hole crosses the cut")
        lower = s.common(Part.makeBox(big, big, ZC - bb.ZMin + 1, V(-big/2, -big/2, bb.ZMin - 1)))
        upper = s.common(Part.makeBox(big, big, bb.ZMax - ZC + 1, V(-big/2, -big/2, ZC))); upper.translate(up * DZ)
        new = lower.fuse([upper, sec.extrude(up * DZ)]).removeSplitter()
        h0, h1 = side_holes(s), side_holes(new)
        want_vol = s.Volume + sec.Area * DZ
        log(f"splice {lab}: z {bb.ZMin:.1f}..{bb.ZMax:.1f} -> {new.BoundBox.ZMin:.1f}..{new.BoundBox.ZMax:.1f}, "
            f"side-hole faces {h0} -> {h1}, solids {len(new.Solids)}, valid {new.isValid()}, vol {new.Volume:.0f} (want {want_vol:.0f})")
        if h1 != h0 or len(new.Solids) != 1 or not new.isValid() or abs(new.Volume - want_vol) > 1e-3 * want_vol:
            errs.append(f"splice {lab} failed checks")
        spliced[lab] = (new, h0)
    FreeCAD.closeDocument(od.Name)

    # ---- open lite-4, snapshot everything ----
    doc = FreeCAD.openDocument(SRC)
    log("opened lite-4", len(doc.Objects))
    before = {o.Name: gbox(o) for o in doc.Objects if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull()}
    touched = set()

    # ---- 1b) swap the extrusions for the drilled bars ----
    for lab in BARS:
        cand = [o for o in doc.getObjectsByLabel(lab) if o.TypeId == 'Part::Extrusion']
        if len(cand) != 1: raise RuntimeError(f"lite-4: {len(cand)} extrusions labelled {lab!r}")
        ext = cand[0]; prof = ext.Base; par = parent_of(ext); Cg = container_global(ext)
        new, h0 = spliced[lab]
        if not close(gbox(ext), new.BoundBox):     # same envelope, only holes differ
            eb = gbox(ext); errs.append(f"{lab}: extrusion box {eb} != spliced box {new.BoundBox}")
        loc = new.copy(); loc.Placement = Cg.inverse().multiply(loc.Placement)
        o = doc.addObject('Part::Feature', 'Bar'); o.Shape = loc
        if par: par.addObject(o)
        copy_view(ext, o)
        touched |= {ext.Name, prof.Name}
        doc.removeObject(ext.Name); doc.removeObject(prof.Name)
        o.Label = lab
        touched.add(o.Name)
        log(f"swapped {lab}: now {o.Name} in {par.Label if par else '(root)'}")

    # ---- 2) INDX ----
    for name, lab in INDX.items():
        o = doc.getObject(name)
        if o is None or o.Label != lab: raise RuntimeError(f"INDX: {name} is {o and o.Label!r}, expected {lab!r}")
        par = parent_of(o); doc.removeObject(name); touched.add(name); log("removed", lab)
        if par is not None and par.isDerivedFrom('App::Part') and not [x for x in par.Group if x.TypeId != 'App::Origin']:
            log("removed empty container", par.Label)
            for x in list(par.Group): doc.removeObject(x.Name)
            doc.removeObject(par.Name)

    # ---- 2b) rear 4040 corners: keep only the 2 staggered M5x50 through-bolts per bar that have
    #          drilled holes; remove the M5x16 BHCS (+ washer) in the other row (no access hole) ----
    by_src = {}
    for o in doc.Objects:
        if 'SourceName' in o.PropertiesList: by_src.setdefault(o.SourceName, []).append(o)
    for scr, wsh in NO_HOLE:
        for src, want in ((scr, ('ISO7380-1', 'M5', 16.0)), (wsh, ('ISO7089', 'M5', None))):
            got = by_src.get(src, [])
            def ident(o):
                L = None
                if 'Length' in o.PropertiesList:
                    L = float(o.LengthCustom) if str(o.Length) == 'Custom' else float(str(o.Length).replace('mm', ''))
                return (str(getattr(o, 'Type', '')), str(getattr(o, 'Diameter', '')), L)
            if len(got) != 1 or ident(got[0]) != want:
                raise RuntimeError(f"no-hole fastener {src}: found {[(g.Label, ident(g)) for g in got]}, expected one {want}")
            touched.add(got[0].Name); doc.removeObject(got[0].Name)
    log(f"removed {len(NO_HOLE)} M5x16 BHCS + washers with no drilled hole (rear 4040 corners)")

    # ---- 3) bowden tubes ----
    root = next(o for o in doc.Objects if o.TypeId == 'App::Part' and not [p for p in o.InList if p.isDerivedFrom('App::Part')])
    grp = doc.addObject('App::DocumentObjectGroup', 'Bowden'); grp.Label = 'Bowden'; root.addObject(grp)
    Rinv = root.getGlobalPlacement().inverse()
    frame = [o for o in doc.Objects if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull()
             and (o.Label in BARS or o.Label.startswith(('2040', '4040', '2020')) or o.Label == 'Back Panel')]
    for side, cl in INLETS.items():
        cpl = doc.getObjectsByLabel(cl)
        if len(cpl) != 1: raise RuntimeError(f"{len(cpl)} objects labelled {cl!r}")
        cb = gbox(cpl[0])
        P0 = V((cb.XMin + cb.XMax) / 2, (cb.YMin + cb.YMax) / 2, cb.ZMax)
        P1 = V(P0.x, EXIT_Y, EXIT_Z)
        a, b = HANDLES
        curve = Part.BezierCurve(); curve.setPoles([P0, P0 + V(0, 0, a), P1 - EXIT_DIR * b, P1])
        path = Part.Wire([curve.toShape(), Part.LineSegment(P1, P1 + EXIT_DIR * BEYOND).toShape()])
        circ = Part.Wire(Part.makeCircle(OD / 2, P0, V(0, 0, 1)))
        tube = path.makePipeShell([circ], True, True)
        # tightest bend along the curve
        n = 400; rmin = min(1 / max(curve.curvature(i / n), 1e-12) for i in range(n + 1))
        L = curve.length() + BEYOND
        hits = []
        tb = tube.BoundBox
        # every solid part whose box overlaps the tube (frame, gantry, chains, heads...), except the
        # coupler stack the tube plugs into
        near = [f for f in doc.Objects if f.isDerivedFrom('Part::Feature') and not f.Shape.isNull()
                and f.Name not in touched and f.Shape.Solids and gbox(f).intersect(tb)
                and not any(k in f.Label for k in ('Bowden Coupler', 'Bowden Clip', 'BrassCouplerRing'))]
        for f in near:
            try: c = tube.common(gshape(f))
            except Exception as e: hits.append(f"{f.Label}: common failed {e}"); continue
            if c.Volume > 1e-3: hits.append(f"{f.Label} {c.Volume:.1f} mm3")
        log(f"tube {side}: checked against {len(near)} nearby parts")
        t = doc.addObject('Part::Feature', 'BowdenTube'); t.Label = f"Bowden {side}"
        sh = tube.copy(); sh.Placement = Rinv.multiply(sh.Placement); t.Shape = sh
        for prop, typ, val in (('OD', 'App::PropertyLength', OD), ('Inlet', 'App::PropertyVector', P0),
                               ('ExitPoint', 'App::PropertyVector', P1), ('ExitDir', 'App::PropertyVector', EXIT_DIR),
                               ('HandleInlet', 'App::PropertyLength', a), ('HandleExit', 'App::PropertyLength', b),
                               ('Beyond', 'App::PropertyLength', BEYOND), ('MinBendRadius', 'App::PropertyLength', rmin),
                               ('PathLength', 'App::PropertyLength', L)):
            t.addProperty(typ, prop, 'Bowden', 'route parameters (global mm); regenerate by script for other poses')
            setattr(t, prop, val)
        if t.ViewObject is not None:
            try: t.ViewObject.ShapeAppearance = (FreeCAD.Material(DiffuseColor=(0.95, 0.95, 0.95), Transparency=0.4),)
            except Exception: pass
        grp.addObject(t); touched.add(t.Name)
        log(f"tube {side}: inlet {P0.x:.1f},{P0.y:.1f},{P0.z:.1f} -> exit {P1.x:.1f},{P1.y:.1f},{P1.z:.1f}; "
            f"length {L:.0f} mm, min bend R {rmin:.1f} mm, solid valid {tube.isValid()}, frame hits {hits or 'none'}")
        if not tube.isValid() or hits or rmin < 50: errs.append(f"tube {side}: valid={tube.isValid()} hits={hits} R={rmin:.1f}")

    doc.recompute()
    # ---- verify: every other object unchanged; new bars carry their holes ----
    for o in doc.Objects:
        if o.Name in touched or o.Name not in before: continue
        if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and not close(gbox(o), before[o.Name]):
            errs.append(f"moved: {o.Label}")
    for lab in BARS:
        o = [x for x in doc.getObjectsByLabel(lab) if x.TypeId == 'Part::Feature']
        if len(o) != 1 or side_holes(gshape(o[0])) != spliced[lab][1]: errs.append(f"{lab}: holes not present after swap")
        else: log(f"check {lab}: {side_holes(gshape(o[0]))} side-hole faces, z {gbox(o[0]).ZMin:.1f}..{gbox(o[0]).ZMax:.1f}")
    left = [n for n in INDX if doc.getObject(n) is not None]
    if left: errs.append(f"INDX still present: {left}")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
