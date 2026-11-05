# GUI pass: vt350-lite-8.FCStd -> vt350-lite-9.FCStd   (headless = dry run, never saves)
# Y rails: the user's owned 2 x Berserker MGN9H 400 mm steel rails, rear-flush against the milled rear mounts, plus a
# FRONT EXTENSION per side filling the rest of the gap to the front mount (73.9 mm). The extension is only ridden while
# docking (no accuracy needed there); it can be printed or cut from a shorter steel rail (open question).
# The rule this layout must keep: with the nozzle anywhere over the build plate, both Y blocks are fully on STEEL.
#  - Rails are cut from lite-8's 450 rails (constant section, so exact); the extension is the same section.
#  - Reach, as lite-8 (travel ends at a rail end or when an XY joint touches a mount), plus the steel-only margin:
#    block front position with the nozzle at the plate's front edge, minus the steel rail's front end (>= 0 = on steel).
# Checks: pieces valid, volumes exact, nothing else changed. Refuses to save otherwise.
import FreeCAD, Part, sys, os, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-8.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-9.FCStd"
DRY = not FreeCAD.GuiUp
L_STEEL = 400.0
RAILS = {"R": "MGN9-450mm Y rail (R)", "L": "MGN9-450mm Y rail (L)"}
BLOCKS = ["_MGN9H", "_MGN9H001"]                      # Y carriage blocks inside the milled XY joints
JOINTS = ["XY right: _XY_right", "XY left: _XY_left"]
FRONT_MOUNTS = ["Front right: _Front_right", "Front left: _Front_left"]
REAR_MOUNTS = ["Rear right: _Rear_right", "Rear left: _Rear_left"]
CARRIAGE = "MadMaxCarriage (1)"                       # toolhead carriage; its front (-Y) face is the mating face
HEADS = {"Left": "A4T Assembly fixed v1", "Right": "A4T Assembly fixed v001"}   # docked heads (mating face = +Y face)
PLATE = "Universal Build Plate 350 v1"
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite9_rails.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
def parent_of(o):
    return next((x for x in o.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))
                 and o in getattr(x, 'Group', [])), None)
def container_global(o):
    p = parent_of(o)
    while p is not None:
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
        p = parent_of(p)
    return FreeCAD.Placement()
def one(doc, label):
    c = doc.getObjectsByLabel(label)
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {label!r}")
    return c[0]
def tree_box(o):
    """bounding box of every solid under a group/part (or the object itself)"""
    b = FreeCAD.BoundBox(); todo = [o]; seen = set()
    while todo:
        x = todo.pop()
        if x.Name in seen: continue
        seen.add(x.Name)
        if x.isDerivedFrom('Part::Feature') and not x.Shape.isNull() and x.Shape.Solids: b.add(gshape(x).BoundBox)
        todo += list(getattr(x, 'Group', []))
    return b
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax),
                                                    (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
def lowest_solid_y(o):
    best = None; todo = [o]
    while todo:
        x = todo.pop()
        if x.isDerivedFrom('Part::Feature') and not x.Shape.isNull() and x.Shape.Solids:
            b = gshape(x).BoundBox
            if best is None or b.ZMin < best[0]: best = (b.ZMin, (b.YMin + b.YMax) / 2, x.Label)
        todo += list(getattr(x, 'Group', []))
    return best

try:
    errs = []
    doc = FreeCAD.openDocument(SRC)
    log("opened", SRC, len(doc.Objects))
    leaves = [o for o in doc.Objects if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids]
    before = {o.Name: gshape(o).BoundBox for o in leaves}
    # ---- geometry the reach depends on
    blk = [gshape(one(doc, l)).BoundBox for l in BLOCKS]
    jnt = [tree_box(one(doc, l)) for l in JOINTS]
    fm = [tree_box(one(doc, l)) for l in FRONT_MOUNTS]
    rm = [tree_box(one(doc, l)) for l in REAR_MOUNTS]
    car = gshape(one(doc, CARRIAGE)).BoundBox
    plate = gshape(one(doc, PLATE)).BoundBox
    rails = {k: one(doc, v) for k, v in RAILS.items()}
    rb = {k: gshape(o).BoundBox for k, o in rails.items()}
    gap0 = max(b.YMax for b in fm); gap1 = min(b.YMin for b in rm)
    log(f"gap between front and rear mounts: Y {gap0:.2f}..{gap1:.2f} ({gap1 - gap0:.1f} mm); lite-8 450 rails at Y {rb['R'].YMin:.2f}..{rb['R'].YMax:.2f}")
    s0, s1 = gap1 - L_STEEL, gap1                                   # steel, rear-flush
    log(f"steel 400 at Y {s0:.2f}..{s1:.2f}; front extension Y {gap0:.2f}..{s0:.2f} ({s0 - gap0:.2f} mm)")
    b_f = min(b.YMin for b in blk); b_r = max(b.YMax for b in blk)
    j_f = min(b.YMin for b in jnt); j_r = max(b.YMax for b in jnt)
    log(f"at the model's gantry pose: Y blocks {b_f:.2f}..{b_r:.2f} ({b_r - b_f:.1f} long); XY joints {j_f:.2f}..{j_r:.2f}; carriage mating face Y {car.YMin:.2f}")
    # heads: mating face and nozzle, in the docked pose
    heads = {}
    for k, l in HEADS.items():
        h = one(doc, l); hb = tree_box(h); z, ny, nl = lowest_solid_y(h)
        heads[k] = (hb.YMax, ny)
        log(f"{k} head docked: mating face Y {hb.YMax:.2f}; nozzle (lowest solid '{nl}', Z {z:.1f}) at Y {ny:.2f} = {hb.YMax - ny:.1f} mm in front of the mating face")
    log(f"build plate Y {plate.YMin:.2f}..{plate.YMax:.2f}")
    # ---- reach for each rail option
    df = max(gap0 - b_f, gap0 - j_f); fby = "joint/mount" if gap0 - j_f >= gap0 - b_f else "rail end"   # steel+extension runs to the mount
    dr = min(s1 - b_r, gap1 - j_r); rby = "rail end" if s1 - b_r <= gap1 - j_r else "joint/mount"
    face = car.YMin + df
    noz_off = {k: v[1] - v[0] for k, v in heads.items()}
    log(f"front limit dY {df:+.2f} ({fby}): carriage face Y {face:.2f}; pickup margin " +
        " / ".join(f"{k} {heads[k][0] - face:+.2f}" for k in heads) + " (< 0: docks must move back by that much)")
    noz_rear = max(car.YMin + dr + noz_off[k] for k in heads)
    log(f"rear limit dY {dr:+.2f} ({rby}): nozzle reaches Y {noz_rear:.2f}; vs plate rear edge {noz_rear - plate.YMax:+.2f}")
    for k in heads:
        d_front = plate.YMin - noz_off[k] - car.YMin                # gantry dY that puts this head's nozzle on the plate's front edge
        m = (b_f + d_front) - s0
        log(f"{k} head: nozzle at the plate's front edge (Y {plate.YMin:.2f}) puts the block front at Y {b_f + d_front:.2f}: "
            f"{m:+.2f} mm {'on steel' if m >= 0 else 'ON THE EXTENSION'}")
        if m < 0: errs.append(f"{k} head: printing at the plate's front edge needs the extension ({m:.2f} mm)")
    # ---- replace the rails
    made = []
    for k, o in rails.items():
        s_ = gshape(o); v0 = s_.Volume; b = s_.BoundBox
        if abs(b.YMin - gap0) > 0.05 and abs(b.YMax - gap1) > 0.05 and abs(b.YLength - 450) > 1e-3: pass
        def piece(y0, y1):
            box = Part.makeBox(b.XLength + 2, y1 - y0, b.ZLength + 2, V(b.XMin - 1, y0, b.ZMin - 1))
            sh = s_.copy()
            if not (b.YMin - 1e-6 <= y0 and y1 <= b.YMax + 1e-6):            # extend: the section is constant in Y
                sec = s_.common(Part.makeBox(b.XLength + 2, 1.0, b.ZLength + 2, V(b.XMin - 1, b.YMin + 100.0, b.ZMin - 1)))
                face = [f for f in sec.Faces if abs(f.normalAt(0, 0).y) > 0.999 and abs(f.CenterOfMass.y - (b.YMin + 100.0)) < 1e-6][0]
                face.translate(V(0, y0 - face.CenterOfMass.y, 0))
                return face.extrude(V(0, y1 - y0, 0)).removeSplitter()
            return sh.common(box).removeSplitter()
        per_mm = v0 / b.YLength
        parts = [("steel", f"MGN9-400mm Y rail ({k}) - owned Berserker, steel", s0, s1),
                 ("ext", f"MGN9 Y rail front extension ({k}) - {s0 - gap0:.1f} mm, printed or cut steel (docking only)", gap0, s0)]
        Cg = container_global(o); grp = parent_of(o); name = o.Name
        shapes = []
        for kind, label, y0, y1 in parts:
            sh = piece(y0, y1); nb = sh.BoundBox
            log(f"{label}: Y {nb.YMin:.2f}..{nb.YMax:.2f}, valid {sh.isValid()}, solids {len(sh.Solids)}, volume {sh.Volume:.1f} (want {per_mm * (y1 - y0):.1f})")
            if not sh.isValid() or len(sh.Solids) != 1 or abs(sh.Volume - per_mm * (y1 - y0)) > 0.5 or abs(nb.YLength - (y1 - y0)) > 1e-3:
                errs.append(f"{label}: failed checks")
            shapes.append((kind, label, sh))
        doc.removeObject(o.Name)
        for kind, label, sh in shapes:
            n = doc.addObject('Part::Feature', 'Rail'); sh.Placement = Cg.inverse().multiply(sh.Placement); n.Shape = sh
            if grp is not None: grp.addObject(n)
            n.Label = label
            if kind == "ext" and n.ViewObject is not None:
                try: n.ViewObject.ShapeAppearance = (FreeCAD.Material(DiffuseColor=(0.9, 0.45, 0.1)),)
                except Exception: pass
        made.append((name, None))
    doc.recompute()
    removed = {nm for nm, _ in made}
    now = {o.Name: o for o in doc.Objects}
    for nm, b in before.items():
        if nm in removed: continue
        if nm not in now: errs.append(f"lost {nm}"); continue
        if not close(gshape(now[nm]).BoundBox, b): errs.append(f"changed: {now[nm].Label}")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
