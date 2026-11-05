# GUI pass: vt350-lite-18.FCStd -> vt350-lite-19.FCStd + vt350-ebox.FCStd   (headless = dry run, never saves)
# The electronics box moves to its own document so the printer model loads faster (user, 2026-11-05).
#  - "Electronics" (Octopus, Pi 5, PSU brackets, ...) and "Electronics Cabinet" are copied, with their hierarchy,
#    into vt350-ebox.FCStd. Each copied top-level Part is given its original GLOBAL placement, so the ebox document
#    shares the printer's coordinate frame and can be overlaid on it.
#  - The printer keeps one transparent "Ebox envelope" box (the union bounding box of both), so clash checks and
#    renders still see the space. Deliberately not an App::Link: a link would make FreeCAD load the ebox file anyway.
#  - Colours/appearance are copied view-provider by view-provider (GUI only).
# Refuses to save if: anything outside the ebox references an ebox object, or any copied solid differs from its
#  original in global placement/bounding box/volume, or the solid count doesn't add up.
import FreeCAD, Part, os, time, traceback
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-18.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-19.FCStd"
EBOX = "/home/dan/Documents/VT350/vt350-ebox.FCStd"
DRY = not FreeCAD.GuiUp
TOPS = ["Electronics", "Electronics Cabinet"]
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite19_ebox.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def is_grp(o): return o.isDerivedFrom('App::Part') or o.isDerivedFrom('App::DocumentObjectGroup')
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def parent_of(o): return next((x for x in o.InList if is_grp(x) and o in getattr(x, 'Group', [])), None)
def descendants(g):
    out = []
    for c in getattr(g, 'Group', []): out.append(c); out += descendants(c)
    return out
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
def same_box(a, b, tol=1e-6):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax), (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
VIEW_PROPS = ("ShapeAppearance", "ShapeColor", "DiffuseColor", "LineColor", "PointColor", "Transparency", "Visibility", "DisplayMode")
try:
    errs = []
    def check(ok, msg):
        log(("  ok   " if ok else "  FAIL ") + msg)
        if not ok: errs.append(msg)
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    tops = []
    for lab in TOPS:
        c = [o for o in doc.getObjectsByLabel(lab) if o.isDerivedFrom('App::Part')]
        if len(c) != 1: raise RuntimeError(f"{len(c)} App::Part labelled {lab!r}")
        tops.append(c[0])
    root = parent_of(tops[0]); check(root is not None and parent_of(tops[1]) is root, f"both under {root.Label if root else None}")
    members = []
    for t in tops: members += [t] + descendants(t)
    for o in list(members):   # an App::Part's Origin (and its axes/planes) is not in Group but belongs to it
        org = getattr(o, 'Origin', None) if o.isDerivedFrom('App::Part') else None
        if org is not None: members += [org] + list(getattr(org, 'OriginFeatures', []))
    members = list({o.Name: o for o in members}.values()); mset = {o.Name for o in members}
    leaves = [o for o in members if is_leaf(o)]
    solids_before = sum(1 for o in doc.Objects if is_leaf(o))
    log(f"ebox: {len(members)} objects, {len(leaves)} solids (printer total {solids_before})")
    # anything outside the ebox that points INTO it (other than the root Part's Group)?
    ext_in = [(o.Label, x.Label) for x in members for o in x.InList if o.Name not in mset and not (o is root and x in tops)]
    check(not ext_in, f"no outside references into the ebox {ext_in[:5]}")
    # and does the ebox depend on anything outside it?
    ext_out = [(x.Label, o.Label) for x in members for o in x.OutList if o.Name not in mset]
    check(not ext_out, f"the ebox depends on nothing outside it {ext_out[:5]}")
    before = {o.Name: (gshape(o).BoundBox, o.Shape.Volume, len(o.Shape.Solids), o.getGlobalPlacement()) for o in leaves}
    env = None
    for o in leaves:
        b = gshape(o).BoundBox
        if env is None: env = FreeCAD.BoundBox(b)
        else: env.add(b)
    log(f"envelope X {env.XMin:.1f}..{env.XMax:.1f}  Y {env.YMin:.1f}..{env.YMax:.1f}  Z {env.ZMin:.1f}..{env.ZMax:.1f}")
    # ---- copy into a new document
    eb = FreeCAD.newDocument("vt350_ebox")
    eb.copyObject(tops, True)
    eb.recompute()
    cp = {o.Name: eb.getObject(o.Name) for o in members}
    missing = [o.Label for o in members if cp[o.Name] is None]
    check(not missing, f"every ebox object copied under its own name ({len(members)}) {missing[:5]}")
    extra = [o.Label for o in eb.Objects if o.Name not in mset]
    check(not extra, f"nothing else came along {extra[:5]}")
    for t in tops: cp[t.Name].Placement = t.getGlobalPlacement()
    eb.recompute()
    if FreeCAD.GuiUp:
        import FreeCADGui
        nview = 0
        for o in members:
            vs, vd = o.ViewObject, cp[o.Name].ViewObject
            if vs is None or vd is None: continue
            for p in VIEW_PROPS:
                if hasattr(vs, p) and hasattr(vd, p):
                    try: setattr(vd, p, getattr(vs, p)); nview += 1
                    except Exception: pass
        log(f"view properties copied: {nview}")
    bad = []
    for o in leaves:
        c = cp[o.Name]; b0, v0, n0, p0 = before[o.Name]
        if not (same_box(gshape(c).BoundBox, b0) and abs(c.Shape.Volume - v0) < 1e-6 * max(1, v0) and len(c.Shape.Solids) == n0
                and (c.getGlobalPlacement().Base - p0.Base).Length < 1e-9 and c.getGlobalPlacement().Rotation.isSame(p0.Rotation, 1e-12)):
            bad.append(o.Label)
    check(not bad, f"all {len(leaves)} copied solids match their originals (global placement, bounding box, volume) {bad[:5]}")
    check(sum(1 for o in eb.Objects if is_leaf(o)) == len(leaves), "ebox document solid count")
    # ---- printer: remove the ebox, add the envelope
    names = [o.Name for t in tops for o in reversed(descendants(t))] + [t.Name for t in tops] + [o.Name for o in members]
    for nm in names:
        if doc.getObject(nm) is not None: doc.removeObject(nm)
    doc.recompute()
    box = Part.makeBox(env.XLength, env.YLength, env.ZLength, V(env.XMin, env.YMin, env.ZMin))
    n = doc.addObject('Part::Feature', 'EboxEnvelope'); root.addObject(n)
    loc = box.copy(); loc.Placement = root.getGlobalPlacement().inverse().multiply(loc.Placement); n.Shape = loc
    n.Label = "Ebox envelope (contents in vt350-ebox.FCStd)"
    if FreeCAD.GuiUp: n.ViewObject.ShapeColor = (0.3, 0.5, 0.8); n.ViewObject.Transparency = 80
    doc.recompute()
    check(same_box(gshape(n).BoundBox, env, 1e-6), "envelope lands at the ebox's global position")
    solids_after = sum(1 for o in doc.Objects if is_leaf(o))
    check(solids_after == solids_before - len(leaves) + 1, f"printer solids {solids_before} -> {solids_after} (-{len(leaves)} +1 envelope)")
    check(not any(o.Name in mset for o in doc.Objects), "no ebox object left in the printer")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else:
        eb.saveAs(EBOX); log("SAVED", EBOX, os.path.getsize(EBOX))
        doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
