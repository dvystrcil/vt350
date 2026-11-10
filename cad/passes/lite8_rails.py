# GUI pass: vt350-lite-7.FCStd -> vt350-lite-8.FCStd   (headless = dry run, never saves)
# Y rails 470 -> 450 mm (the owned/available MGN9 limit: Berserker MGN9H tops out at 450), and a Y-reach report.
#  - The new rails are the 470 rails cut to 450 (the rail is a constant section, so this is exact), placed
#    RAIL_PLACE = rear (default) / centre / front within the 474.4 mm gap between the milled front and rear mounts.
#  - Reach: the gantry moves in Y as one body. Its travel ends when EITHER a Y carriage block reaches its rail's end,
#    OR an XY joint touches the front/rear mount (both checked from the model's own geometry: block, joint and mount
#    bounding boxes in Y, which is exact here because these parts are axis-aligned blocks).
#    Reported for 470 and each 450 placement:
#      front: how far forward the toolhead carriage's mating face reaches, against the docked heads' mating faces
#             (a head can only be picked up if the carriage reaches it);
#      rear:  how far back the nozzle reaches, against the rear edge of the build plate.
# Checks: rails valid, volume = 450/470 of the old; nothing else changed. Refuses to save otherwise.
import FreeCAD, Part, sys, os, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-7.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-8.FCStd"
DRY = not FreeCAD.GuiUp
# rear: same nozzle reach as 470 (the rear is limited by the XY joint hitting the rear mount, not the rail); the docks
# must move back 26.8 mm. front would keep the docks but lose 25 mm of rear reach (see the log's table).
RAIL_PLACE = os.environ.get("RAIL_PLACE", "rear")
L_NEW = 450.0
RAILS = {"R": "MGN9-470mm Y rail (R)", "L": "MGN9-470mm Y rail (L)"}
BLOCKS = ["_MGN9H", "_MGN9H001"]                      # Y carriage blocks inside the milled XY joints
JOINTS = ["XY right: _XY_right", "XY left: _XY_left"]
FRONT_MOUNTS = ["Front right: _Front_right", "Front left: _Front_left"]
REAR_MOUNTS = ["Rear right: _Rear_right", "Rear left: _Rear_left"]
CARRIAGE = "MadMaxCarriage (1)"                       # toolhead carriage; its front (-Y) face is the mating face
HEADS = {"Left": "A4T Assembly fixed v1", "Right": "A4T Assembly fixed v001"}   # docked heads (mating face = +Y face)
PLATE = "Universal Build Plate 350 v1"
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite8_rails.log", "w"); t0 = time.time()
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
    log("opened", SRC, len(doc.Objects), "RAIL_PLACE =", RAIL_PLACE)
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
    log(f"gap between front and rear mounts: Y {gap0:.2f}..{gap1:.2f} ({gap1 - gap0:.1f} mm); 470 rails at Y {rb['R'].YMin:.2f}..{rb['R'].YMax:.2f}")
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
    def placements():
        yield "470 (lite-7)", rb['R'].YMin, rb['R'].YMax
        for p, y0 in (("450 front", gap0), ("450 centre", (gap0 + gap1 - L_NEW) / 2), ("450 rear", gap1 - L_NEW)):
            yield p, y0, y0 + L_NEW
    chosen = None
    log("rail option     rail Y            front limit (by)       carriage face  pickup margin L / R     rear limit (by)       nozzle rear  vs plate rear")
    for name, r0, r1 in placements():
        # forward travel (negative dY): block front reaches rail front, or joint front reaches the front mounts
        df_rail = r0 - b_f; df_mount = gap0 - j_f
        df = max(df_rail, df_mount); fby = "rail end" if df_rail >= df_mount else "joint/mount"
        dr_rail = r1 - b_r; dr_mount = gap1 - j_r
        dr = min(dr_rail, dr_mount); rby = "rail end" if dr_rail <= dr_mount else "joint/mount"
        face = car.YMin + df
        margins = {k: v[0] - face for k, v in heads.items()}           # >= 0: the carriage reaches the head
        noz_off = {k: v[1] - v[0] for k, v in heads.items()}           # nozzle Y relative to mating face (negative)
        noz_rear = max(car.YMin + dr + noz_off[k] for k in heads)
        log(f"  {name:13} {r0:7.2f}..{r1:7.2f}  {df:+8.2f} ({fby:11})  {face:8.2f}     {margins['Left']:+6.2f} / {margins['Right']:+6.2f}"
            f"      {dr:+8.2f} ({rby:11})  {noz_rear:8.2f}   {noz_rear - plate.YMax:+7.2f}")
        if name == f"450 {RAIL_PLACE}": chosen = (r0, r1)
    if chosen is None: raise RuntimeError(f"RAIL_PLACE {RAIL_PLACE!r} not one of front/centre/rear")
    log("  (pickup margin < 0: the carriage stops short of that docked head by that much; plate rear > 0: nozzle passes the plate's rear edge)")
    # ---- replace the rails
    made = []
    for k, o in rails.items():
        s = gshape(o); v0 = s.Volume; b = s.BoundBox
        box = Part.makeBox(b.XLength + 2, L_NEW, b.ZLength + 2, V(b.XMin - 1, 0, b.ZMin - 1))
        s.translate(V(0, chosen[0] - b.YMin, 0))
        new = s.common(box.translated(V(0, chosen[0], 0))).removeSplitter()
        nb = new.BoundBox
        log(f"Y rail {k}: MGN9 {L_NEW:.0f} at Y {nb.YMin:.2f}..{nb.YMax:.2f}, valid {new.isValid()}, solids {len(new.Solids)}, "
            f"volume {new.Volume:.1f} (want {v0 * L_NEW / 470:.1f})")
        if not new.isValid() or len(new.Solids) != 1 or abs(new.Volume - v0 * L_NEW / 470) > 0.5 or abs(nb.YLength - L_NEW) > 1e-3:
            errs.append(f"rail {k} failed checks")
        Cg = container_global(o); grp = parent_of(o); name = o.Name
        doc.removeObject(o.Name)
        n = doc.addObject('Part::Feature', 'Rail'); new.Placement = Cg.inverse().multiply(new.Placement); n.Shape = new
        if grp is not None: grp.addObject(n)
        n.Label = f"MGN9-450mm Y rail ({k})"
        made.append((name, n))
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
