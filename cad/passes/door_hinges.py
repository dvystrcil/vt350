# GUI pass: vt350-lite-3.FCStd -> vt350-lite-4.FCStd
# Three identical door hinges: copy the complete 'Bottom Hinge (1)' to a middle and a top position,
# remove the two loose top-hinge dowel pins. Verifies positions; refuses to save on mismatch.
import FreeCAD, FreeCADGui, Part, sys, os, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
WORK = os.environ.get("VT350_WORK", os.path.expanduser("~/Code/vt350/cad/data"))  # data in, logs out

SCR = WORK
SRC = "/home/dan/Documents/VT350/vt350-lite-3.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-4.FCStd"
log_f = open(SCR + "/door_hinges.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()

def gbox_tree(o):
    bb = FreeCAD.BoundBox()
    objs = [o] + [x for x in o.OutListRecursive]
    for x in objs:
        if x.isDerivedFrom('Part::Feature') and not x.Shape.isNull() and x.TypeId not in ('App::Origin',):
            s = x.Shape.copy(); s.Placement = x.getGlobalPlacement()
            try: bb.add(s.optimalBoundingBox(True, False))
            except Exception: bb.add(s.BoundBox)
    return bb

def parent_part(o):
    return next((x for x in o.InList if x.isDerivedFrom('App::Part') and o in x.Group), None)

try:
    doc = FreeCAD.openDocument(SRC)
    hinge = [o for o in doc.Objects if o.Label == 'Bottom Hinge (1)']
    pins = [o for o in doc.Objects if o.Label in ('M5x50 Dowel Pin (1)', 'M5x50 Dowel Pin (1)001')]
    assert len(hinge) == 1, f"expected 1 'Bottom Hinge (1)', found {len(hinge)}"
    assert len(pins) == 2, f"expected 2 loose top pins, found {len(pins)}"
    h = hinge[0]; door = parent_part(h)
    hb = gbox_tree(h)
    rails = [o for o in doc.Objects if o.Label in ('2040 (2) (1)', '2040 (2) (1)001')]
    top_rail_under = min(gbox_tree(r).ZMin for r in rails if gbox_tree(r).ZMin > 0)
    bottom_gap = hb.ZMin - max(gbox_tree(r).ZMax for r in rails if gbox_tree(r).ZMax < 0)
    top_off = (top_rail_under - bottom_gap) - hb.ZMax           # mirror the bottom hinge's gap at the top
    mid_off = top_off / 2
    log(f"bottom hinge z {hb.ZMin:.2f}..{hb.ZMax:.2f}; bottom gap {bottom_gap:.2f}; top rail underside {top_rail_under:.2f}")
    log(f"offsets: middle +{mid_off:.2f}, top +{top_off:.2f}")
    Cg = door.getGlobalPlacement() if door else FreeCAD.Placement()
    made = {}
    for name, off in (('Middle Hinge', mid_off), ('Top Hinge', top_off)):
        before = set(o.Name for o in doc.Objects)
        c = doc.copyObject(h, True)
        new_objs = [o for o in doc.Objects if o.Name not in before]
        c.Label = name
        if door: door.addObject(c)
        T = FreeCAD.Placement(FreeCAD.Vector(0, 0, off), FreeCAD.Rotation())
        c.Placement = Cg.inverse().multiply(T).multiply(Cg).multiply(h.Placement)
        made[name] = (c, off)
        log(f"{name}: copied {len(new_objs)} objects")
    for p in pins:
        log("removed loose pin", p.Label); doc.removeObject(p.Name)
    doc.recompute()
    errs = []
    hb2 = gbox_tree(h)
    if abs(hb2.ZMin - hb.ZMin) > 1e-3: errs.append("bottom hinge moved")
    for name, (c, off) in made.items():
        b = gbox_tree(c)
        want = (hb.ZMin + off, hb.ZMax + off)
        sol = sum(len(x.Shape.Solids) for x in c.OutListRecursive if x.isDerivedFrom('Part::Feature') and not x.Shape.isNull())
        log(f"{name}: z {b.ZMin:.2f}..{b.ZMax:.2f} (want {want[0]:.2f}..{want[1]:.2f}), x {b.XMin:.2f}..{b.XMax:.2f} (bottom {hb.XMin:.2f}..{hb.XMax:.2f}), solids {sol}")
        if abs(b.ZMin - want[0]) > 1e-3 or abs(b.ZMax - want[1]) > 1e-3 or abs(b.XMin - hb.XMin) > 1e-3 or abs(b.YMin - hb.YMin) > 1e-3:
            errs.append(f"{name} misplaced")
        if b.ZMax > top_rail_under + 1e-6:
            errs.append(f"{name} overlaps the top rail")
    log(f"verify: {len(errs)} problems", errs)
    if errs: log("NOT SAVED")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
