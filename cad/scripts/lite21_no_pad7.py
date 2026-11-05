# GUI pass: vt350-lite-20.FCStd -> vt350-lite-21.FCStd   (headless = dry run, never saves)
# Removes the BTT Pad 7 screen (user, 2026-11-05: it will be mounted somewhere else, place not decided).
# It is one solid, "case display 7 hdmi BTT v1.2 v1", directly in the frame group, with nothing else within 3 mm
# of it (no separate mount to remove). Refuses to save unless exactly that one solid is gone and every other solid
# keeps its global bounding box.
import FreeCAD, os, time, traceback
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-20.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-21.FCStd"
DRY = not FreeCAD.GuiUp
LABEL = "case display 7 hdmi BTT v1.2 v1"
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite21_no_pad7.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def bkey(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); b = s.BoundBox
    return tuple(round(x, 4) for x in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))
try:
    errs = []
    def check(ok, msg):
        log(("  ok   " if ok else "  FAIL ") + msg)
        if not ok: errs.append(msg)
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    before = {o.Name: bkey(o) for o in doc.Objects if is_leaf(o)}
    c = doc.getObjectsByLabel(LABEL)
    check(len(c) == 1, f"exactly one {LABEL!r} ({len(c)})")
    o = c[0]; name = o.Name
    users = [x.Label for x in o.InList if not (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))]
    check(not users, f"nothing but its group references it ({users})")
    log("removing", name, LABEL, before[name])
    doc.removeObject(name); doc.recompute()
    after = {x.Name: bkey(x) for x in doc.Objects if is_leaf(x)}
    check(set(before) - set(after) == {name} and not set(after) - set(before), f"only the screen is gone ({len(before)} -> {len(after)})")
    moved = [n for n in after if after[n] != before[n]]
    check(not moved, f"no other solid moved ({moved[:5]})")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
