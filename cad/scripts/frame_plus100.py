# GUI pass: vt350-lite-2.FCStd -> vt350-lite-3.FCStd
#  +100 mm between the gantry and the top of the frame (gantry and Z unchanged).
#  - bars crossing the cut plane: rebuilt as Part::Extrusion of their own end face, +100 mm
#  - back panel: spliced (cut, move upper part, fill gap with its cross-section)
#  - everything entirely above the cut plane: moved +100 mm in Z
#  - leadscrew rods: 8 mm diameter
#  Then verifies every object against the pre-change map and writes a cut list.
import FreeCAD, FreeCADGui, Part, sys, os, json, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401  (restores Fasteners objects)
WORK = os.environ.get("VT350_WORK", os.path.expanduser("~/Code/vt350/cad/data"))  # data in, logs out

SCR = WORK
SRC = "/home/dan/Documents/VT350/vt350-lite-2.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-3.FCStd"
ZC, DZ = 534.0, 100.0
STAY_ANYWAY = {"M5x50 Dowel Pin (1)"}           # top hinge pin: belongs to the hinge below the cut
REBUILD_BARS = {"2040", "4040", "4040(Mirror)", "2040(Mirror)", "2040 (1)", "2040 (1)(Mirror)"}
SPLICE = {"Back Panel"}
log_f = open(SCR + "/frame_plus100.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()

def gbox(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
    try: return s.optimalBoundingBox(True, False)
    except Exception: return s.BoundBox

def parent_of(o):
    return next((x for x in o.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))
                 and o in getattr(x, 'Group', [])), None)

def container_global(o):
    """Global placement of the coordinate frame o.Placement is expressed in."""
    p = o
    while True:
        p = parent_of(p)
        if p is None: return FreeCAD.Placement()
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()

def copy_view(src, dst):
    for prop in ('ShapeAppearance', 'ShapeColor', 'DiffuseColor', 'LineColor', 'Transparency', 'Visibility'):
        try: setattr(dst.ViewObject, prop, getattr(src.ViewObject, prop))
        except Exception: pass

try:
    pre = {r['name']: r for r in json.load(open(SCR + "/frame_map/frame_map.json"))}
    doc = FreeCAD.openDocument(SRC)
    log("opened", len(doc.Objects))
    up = FreeCAD.Vector(0, 0, 1)
    moved, rebuilt, spliced = [], {}, []

    # 1) leadscrew rods -> 8 mm (original solid's thread crest is 8.00 mm; 10.5 was a loose B-spline bbox)
    for o in doc.Objects:
        if o.TypeId == 'Part::Cylinder' and o.Label.startswith('Leadscrew') and o.Label.endswith('(rod)'):
            o.Radius = 4.0; log("rod -> d=8", o.Label)

    # 2) classify by pre-change global Z extents
    todo_move, todo_bar, todo_splice = [], [], []
    for o in list(doc.Objects):
        r = pre.get(o.Name)
        if r is None: continue
        z0, z1 = r['z']
        if o.Label in REBUILD_BARS and z0 < ZC < z1: todo_bar.append(o)
        elif o.Label in SPLICE and z0 < ZC < z1: todo_splice.append(o)
        elif z0 >= ZC and o.Label not in STAY_ANYWAY: todo_move.append(o)
        elif z0 < ZC < z1 and o.Label not in STAY_ANYWAY:
            raise RuntimeError(f"unplanned part crosses the cut plane: {o.Label} {z0:.1f}..{z1:.1f}")

    # 3) move everything above the cut +100 in global Z
    for o in todo_move:
        Cg = container_global(o)
        T = FreeCAD.Placement(up * DZ, FreeCAD.Rotation())
        o.Placement = Cg.inverse().multiply(T).multiply(Cg).multiply(o.Placement)
        moved.append(o.Name)
    log("moved +100:", len(moved))

    # 4) rebuild crossing bars from their bottom end face
    for o in todo_bar:
        par = parent_of(o); Cg = container_global(o)
        upL = Cg.Rotation.inverted().multVec(up)                 # global +Z in container coords
        s = o.Shape                                              # in container coords
        ends = [f for f in s.Faces if isinstance(f.Surface, Part.Plane) and abs(abs(f.normalAt(0, 0).dot(upL)) - 1) < 1e-6]
        bottom = min(ends, key=lambda f: f.CenterOfMass.dot(upL))
        top = max(ends, key=lambda f: f.CenterOfMass.dot(upL))
        L = top.CenterOfMass.dot(upL) - bottom.CenterOfMass.dot(upL)
        prof = doc.addObject('Part::Feature', 'BarProfile'); prof.Label = o.Label + ' profile'
        prof.Shape = bottom.copy()   # the bar's own end face, holes and all
        ext = doc.addObject('Part::Extrusion', 'Bar')
        ext.Base = prof; ext.DirMode = 'Custom'; ext.Dir = upL; ext.LengthFwd = L + DZ; ext.Solid = True
        if par: par.addObject(prof); par.addObject(ext)
        prof.ViewObject.Visibility = False
        copy_view(o, ext)
        old_label = o.Label
        doc.removeObject(o.Name)
        ext.Label = old_label
        rebuilt[ext.Name] = (old_label, L, None)
        log(f"bar {old_label}: {L:.2f} -> {L + DZ:.2f} mm (profile faces {len(bottom.Wires)} wires)")

    # 5) splice the back panel at ZC
    for o in todo_splice:
        Cg = container_global(o); s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()  # global
        bb = s.BoundBox; big = 5000
        lower_box = Part.makeBox(big, big, ZC - bb.ZMin + 1, FreeCAD.Vector(-big / 2, -big / 2, bb.ZMin - 1))
        upper_box = Part.makeBox(big, big, bb.ZMax - ZC + 1, FreeCAD.Vector(-big / 2, -big / 2, ZC))
        lower = s.common(lower_box); upper = s.common(upper_box); upper.translate(up * DZ)
        sec = s.slice(up, ZC)
        face = Part.makeFace(sec, 'Part::FaceMakerBullseye')   # nests holes correctly
        mid = face.extrude(up * DZ)
        new = lower.fuse([upper, mid]).removeSplitter()
        new.Placement = Cg.inverse()        # global geometry -> container coords
        newo = doc.addObject('Part::Feature', 'BackPanel'); newo.Label = o.Label
        newo.Shape = new
        par = parent_of(o)
        if par: par.addObject(newo)
        copy_view(o, newo)
        nb = gbox(newo)
        log(f"spliced {o.Label}: z {bb.ZMin:.1f}..{bb.ZMax:.1f} -> {nb.ZMin:.1f}..{nb.ZMax:.1f}, solids {len(newo.Shape.Solids)}, valid {newo.Shape.isValid()}, volume {s.Volume:.0f} -> {newo.Shape.Volume:.0f}")
        doc.removeObject(o.Name); spliced.append(newo.Name)

    doc.recompute()

    # 6) verify against the pre-change map
    errs = []
    for o in doc.Objects:
        if not o.isDerivedFrom('Part::Feature') or o.Shape.isNull() or o.Name.startswith('BarProfile'): continue
        b = gbox(o); r = pre.get(o.Name)
        if o.Name in rebuilt:
            old_label, L, _ = rebuilt[o.Name]
            if abs(b.ZLength - (L + DZ)) > 1e-3 or abs(b.ZMin - (-50.0)) > 1e-3:
                errs.append(f"rebuilt {old_label}: z {b.ZMin:.3f}..{b.ZMax:.3f} (want -50..{-50 + L + DZ:.1f})")
            continue
        if o.Name in spliced or r is None: continue
        dz = DZ if o.Name in moved else 0.0
        if abs(b.ZMin - (r['z'][0] + dz)) > 1e-3 or abs(b.ZMax - (r['z'][1] + dz)) > 1e-3 \
           or abs(b.XMin - r['x'][0]) > 1e-3 or abs(b.YMin - r['y'][0]) > 1e-3:
            # rods were resized on purpose
            if not o.Label.endswith('(rod)'):
                errs.append(f"{o.Label}: z {b.ZMin:.3f}..{b.ZMax:.3f}, expected {r['z'][0]+dz:.3f}..{r['z'][1]+dz:.3f}")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs[:50]]

    # 7) cut list: every 2020/2040/4040 bar, length along its long axis
    import re, collections
    cut = collections.Counter()
    for o in doc.Objects:
        if o.isDerivedFrom('Part::Feature') and re.match(r'^(2020|2040|4040)\b', o.Label) and not o.Name.startswith('BarProfile'):
            b = gbox(o); dims = sorted([b.XLength, b.YLength, b.ZLength])
            path = []; p = o
            while parent_of(p) is not None: p = parent_of(p); path.append(p.Label)
            cut[(o.Label.split()[0][:4], round(dims[2], 1), ' / '.join(reversed(path[:-1]))[:45])] += 1
    log("CUT LIST (profile, length mm, assembly, qty):")
    for (prof, L, where), q in sorted(cut.items()):
        log(f"  {prof}  {L:7.1f}  x{q}   {where}")
    ov = FreeCAD.BoundBox()
    for o in doc.Objects:
        if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.ViewObject.Visibility: ov.add(gbox(o))
    log(f"overall Z {ov.ZMin:.1f}..{ov.ZMax:.1f}")
    if errs:
        log("NOT SAVED: verification failed")
    else:
        doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
