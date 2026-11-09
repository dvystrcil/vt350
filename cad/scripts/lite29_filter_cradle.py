# GUI pass: vt350-lite-28 + vt350-filter-2 -> vt350-lite-29 + vt350-filter-3   (headless = dry run, never saves)
# #74 AC3 (user, 2026-11-08): the filter sits in a CRADLE of two halves, left and right, and lifts out from above.
# Replaces lite-28's four hanger pieces (each side was split around the lid latch because its tab went into the wall).
# Each half, one continuous piece Y 90..390 (orange PET-GF concept):
#   lip   : 10 mm over the backbone top, LIP_T thick, bottom face on the backbone (left/right edges only: the bed's
#           2020 T lands on the front and rear edges at the bottom of Z travel, see lite28_filter_lips.py);
#   wall  : WALL_T down the cutout gap against the cutout edge, clear of the lid latch;
#   ledge : LEDGE_T under the filter's bottom tray (M_1a.0_Body_BPM, underside Z -79.9 at the edges), LEDGE_IN under its
#           side edge; the centre of the underside (fan, exhaust slider, three access hatches) stays open;
#   ridge : RIDGE_W x RIDGE_H on the ledge, RIDGE_GAP beside the tray wall, so the filter can't slide sideways.
# The filter does not move (its tray already sits at the ledge height). The printer's Filter envelope is resized.
# Checks (refuses to save on any): lip on the backbone top over >= 90 % material; off the 2020 T's landing; ledge top
# meets the tray underside with >= 10 mm of support; no interpenetration with the tray (<= 1 mm3) and >= 0.5 mm off every
# other filter part; lift-out path clear (nothing of the cradle in the column above any filter part); bed at the bottom
# of travel >= 5 mm above; no overlap with the printer; ledge bottom >= 15 mm above the board.
import FreeCAD, Part, sys, os, time, json, traceback
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", f"{REPO}/cad/data")
MODELS = "/home/dan/Documents/VT350"
SRC, DST = f"{MODELS}/vt350-lite-28.FCStd", f"{MODELS}/vt350-lite-29.FCStd"
FSRC, FDST = f"{MODELS}/vt350-filter-2.FCStd", f"{MODELS}/vt350-filter-3.FCStd"
DRY = not FreeCAD.GuiUp
CUT = (-420.0, 70.0, -70.0, 400.0)
BB_TOP = -2.0
BED_LOWEST_DZ = -241.98
FRONT_BAR_Y, SPINE_X = 81.0, (-255.0, -235.0)
LIP_W, LIP_T, WALL_T, WALL_GAP, LEDGE_T, LEDGE_IN, RIDGE_W, RIDGE_H, RIDGE_GAP = 10.0, 4.0, 4.0, 0.5, 4.0, 15.0, 3.0, 5.0, 1.5
BOARD_TOP = -100.0
Y0, Y1 = 90.0, 390.0
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite29_filter_cradle.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
errs = []
def check(ok, what):
    log(("ok   " if ok else "FAIL ") + what)
    if not ok: errs.append(what)
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
def obb(s):
    try: return s.optimalBoundingBox(True, False)
    except Exception: return s.BoundBox
def is_leaf(o):
    return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and bool(o.Shape.Solids) and o.TypeId != 'App::Part'
def vol(a, b):
    try: return a.common(b).Volume
    except Exception as e: log("  boolean failed:", e); return float("inf")
def box(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
try:
    doc = FreeCAD.openDocument(SRC); log("opened", SRC)
    fd = FreeCAD.openDocument(FSRC); log("opened", FSRC)
    root = next(o for o in doc.Objects if o.TypeId == 'App::Part' and o.Label.startswith("4040-350x350x250 Voron Trident"))
    leaves = [o for o in doc.Objects if is_leaf(o)]
    shapes = {o.Name: gshape(o) for o in leaves}; boxes = {n: obb(s) for n, s in shapes.items()}
    backbone = next(o for o in leaves if o.Label.startswith("backbone-350"))
    env = next(o for o in leaves if o.Label.startswith("Filter envelope"))
    grp = next(o for o in fd.Objects if o.TypeId == 'App::DocumentObjectGroup' and o.Label.startswith("StealthMax 300"))
    old = [o.Name for o in fd.Objects if o.Label.startswith("StealthMax hanger lip")]
    check(len(old) == 2, f"two lite-28 hangers to replace ({len(old)})")
    for n in old: fd.removeObject(n)
    fd.recompute()
    fparts = {o.Label: gshape(o) for o in fd.Objects if is_leaf(o)}
    fboxes = {k: obb(s) for k, s in fparts.items()}
    fb = obb(Part.makeCompound(list(fparts.values()))); log("filter:", fb)
    # The filter stands on its bottom tray (M_1a.0_Body_BPM, under the main chamber), not on the chamber floor.
    # Its plain BoundBox is polluted (Y to -419, Z to -372); the optimal box and a slice under the edges are right.
    TRAY = "StealthMax M_1a.0_Body_BPM"
    chamber = fparts[TRAY]; mainb = fboxes[TRAY]
    log("bottom tray (support):", mainb)
    floors = []
    for x0, x1 in ((mainb.XMin, mainb.XMin + LEDGE_IN), (mainb.XMax - LEDGE_IN, mainb.XMax)):
        sl = chamber.common(box(x0, x1, Y0, Y1, mainb.ZMin - 5, mainb.ZMax)); floors.append(sl.BoundBox.ZMin)
    log("tray underside under the ledge strips (left, right):", [round(f, 2) for f in floors])
    check(abs(floors[0] - floors[1]) < 0.05, f"tray underside level on both sides {floors}")
    floor = min(floors); LZ0 = floor - LEDGE_T
    cradles = []
    for side in ("left", "right"):
        if side == "left":
            lip = (CUT[0] - LIP_W, CUT[0] + WALL_GAP); wall = (CUT[0] + WALL_GAP, CUT[0] + WALL_GAP + WALL_T)
            ledge = (wall[0], mainb.XMin + LEDGE_IN); ridge = (mainb.XMin - RIDGE_GAP - RIDGE_W, mainb.XMin - RIDGE_GAP)
        else:
            lip = (CUT[2] - WALL_GAP, CUT[2] + LIP_W); wall = (CUT[2] - WALL_GAP - WALL_T, CUT[2] - WALL_GAP)
            ledge = (mainb.XMax - LEDGE_IN, wall[1]); ridge = (mainb.XMax + RIDGE_GAP, mainb.XMax + RIDGE_GAP + RIDGE_W)
        parts = [box(*lip, Y0, Y1, BB_TOP, BB_TOP + LIP_T), box(*wall, Y0, Y1, LZ0, BB_TOP + LIP_T),
                 box(*ledge, Y0, Y1, LZ0, floor), box(*ridge, Y0, Y1, floor, floor + RIDGE_H)]
        c = parts[0].fuse(parts[1:]).removeSplitter()
        check(len(c.Solids) == 1, f"{side}: cradle half is one solid ({len(c.Solids)})")
        cradles.append((side, c))
        cb = c.BoundBox; log(f"{side}: cradle {cb}")
        lipfoot = box(lip[0] if side == "left" else CUT[2], CUT[0] if side == "left" else lip[1], Y0, Y1, BB_TOP - 0.5, BB_TOP)
        frac = vol(lipfoot, shapes[backbone.Name]) / (LIP_W * (Y1 - Y0) * 0.5)
        check(frac > 0.9, f"{side}: lip footprint over backbone material {frac:.0%} (slots allowed)")
        check(cb.YMin >= FRONT_BAR_Y + 5 and not (cb.XMin < SPINE_X[1] and cb.XMax > SPINE_X[0]),
              f"{side}: clear of the 2020 T's landing (Y >= {FRONT_BAR_Y + 5}, off the spine)")
        sup = (ledge[1] - mainb.XMin) if side == "left" else (mainb.XMax - ledge[0])
        check(sup >= 10.0, f"{side}: ledge reaches {sup:.1f} mm under the bottom tray (Z {floor:.2f})")
        pen = vol(c, chamber)
        check(pen <= 1.0, f"{side}: cradle x bottom tray interpenetration {pen:.2f} mm3")
        dch = c.distToShape(chamber)[0]
        check(dch <= 0.2, f"{side}: bottom tray rests on the ledge (distance {dch:.2f})")
        near = []
        for k, s in fparts.items():
            if k == TRAY: continue
            d = c.distToShape(s)[0]
            if d < 0.5: near.append((k, round(d, 2)))
        check(not near, f"{side}: >= 0.5 mm off every other filter part {near[:4]}")
        blocked = []
        for k, b in fboxes.items():
            col = box(b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMin + 200)
            if k == TRAY: col = box(b.XMin, b.XMax, b.YMin, b.YMax, floor + 0.01, b.ZMin + 200)
            v = vol(c, col)
            if v > 1e-3: blocked.append((k, round(v, 1)))
        check(not blocked, f"{side}: lift-out path clear (cradle in the column above a filter part: {blocked[:4]})")
        check(LZ0 - BOARD_TOP >= 15.0, f"{side}: ledge bottom {LZ0:.1f} is {LZ0 - BOARD_TOP:.1f} above the board")
    bed = [o for o in leaves if 230 <= boxes[o.Name].ZMin <= 300 and boxes[o.Name].ZMax <= 300]
    worst = (999, "")
    for side, c in cradles:
        hb = c.BoundBox
        for o in bed:
            b = boxes[o.Name]
            if b.XMin < hb.XMax and b.XMax > hb.XMin and b.YMin < hb.YMax and b.YMax > hb.YMin:
                gap = b.ZMin + BED_LOWEST_DZ - hb.ZMax
                if gap < worst[0]: worst = (gap, f"{side} vs {o.Label}")
    check(worst[0] >= 5.0, f"bed at the bottom of travel vs cradle: closest {worst[0]:.2f} ({worst[1]})")
    hits = []
    for side, c in cradles:
        for o in leaves:
            if o.Name == env.Name: continue
            if boxes[o.Name].intersect(c.BoundBox) and vol(c, shapes[o.Name]) > 1e-3: hits.append((side, o.Label))
    check(not hits, f"cradle x printer at the model pose: {hits[:5]}")
    for side, c in cradles:
        n = fd.addObject('Part::Feature', 'Cradle'); n.Shape = c; grp.addObject(n)
        n.Label = f"StealthMax cradle half, {side} (remix concept)"
        if FreeCAD.GuiUp: n.ViewObject.ShapeColor = (0.89, 0.4, 0.16)
    fd.recompute()
    nb = FreeCAD.BoundBox(fb); [nb.add(c.BoundBox) for _, c in cradles]
    e = box(nb.XMin, nb.XMax, nb.YMin, nb.YMax, nb.ZMin, nb.ZMax); e.Placement = root.getGlobalPlacement().inverse().multiply(e.Placement)
    env.Shape = e; env.Label = "Filter envelope (contents in vt350-filter-3.FCStd)"
    doc.recompute()
    log("envelope:", gshape(env).BoundBox)
    check(sum(1 for o in doc.Objects if is_leaf(o)) == len(leaves), "printer solid count unchanged")
    json.dump({"cradles": {s: [c.BoundBox.XMin, c.BoundBox.YMin, c.BoundBox.ZMin, c.BoundBox.XMax, c.BoundBox.YMax, c.BoundBox.ZMax]
                           for s, c in cradles}, "bed_gap": worst[0], "envelope": [nb.XMin, nb.YMin, nb.ZMin, nb.XMax, nb.YMax, nb.ZMax]},
              open(WORK + "/logs/lite29_filter_cradle.json", "w"), indent=1)
    log(f"verify: {len(errs)} problems"); [log("  " + x) for x in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else:
        fd.saveAs(FDST); log("SAVED", FDST, os.path.getsize(FDST))
        doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
