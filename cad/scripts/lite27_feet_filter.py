# GUI pass: vt350-lite-26.FCStd -> vt350-lite-27.FCStd + vt350-filter.FCStd   (headless = dry run, never saves)
# #83 options 2 + 5 and #74 option A (user, 2026-11-08):
#  - 4 levelling feet (placeholders until a product is picked: aluminium T-slot bracket 40x40x8 under each side 4040,
#    M8 stud, rubber pad 50 x 18) standing on a rigid base board (18 mm), with the frame bottom 50 mm above the board;
#  - the Nevermore StealthMax 300 core (lid, main chamber, flow chamber, carbon basket, HEPA, fan) recessed in the
#    backbone's 350 x 330 cutout, top FILTER_TOP below the backbone's top face, so the bed's 2020 T (which lands on the
#    backbone at the bottom of Z travel, #74) never reaches it. Upstream assembly as is (BPM configuration); the
#    housing/mount remix is still to do (#74 AC3), so nothing holds it up in this model yet.
# The filter lives in its own file (vt350-filter.FCStd, ~140 MB of B-spline STEP geometry), like the ebox (lite-19):
# the printer keeps a transparent "Filter envelope" box; the render merges the file with VT350_EXTRA.
# Checks (refuses to save on any):
#  - the printer's lowest solid is the frame bottom at Z -50 (so the feet, not the Z motors, carry it);
#  - each foot's parts touch nothing in the printer (boolean), and the bracket top sits on the frame bottom;
#  - filter top <= FILTER_TOP; every filter part above the backbone's bottom face fits inside the cutout (>= 5 mm);
#  - filter vs printer solids at the model pose: no overlap (boolean, after a box prefilter);
#  - bed-frame 2020s at the bottom of Z travel (dZ BED_LOWEST_DZ, #74 boolean) stay >= 1 mm above the filter;
#  - the filter clears the base board (>= AIR_GAP).
import FreeCAD, Part, Import, sys, os, time, json, traceback
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", f"{REPO}/cad/data")
MODELS = "/home/dan/Documents/VT350"
SRC, DST, FILT = f"{MODELS}/vt350-lite-26.FCStd", f"{MODELS}/vt350-lite-27.FCStd", f"{MODELS}/vt350-filter.FCStd"
STEP = f"{MODELS}/downloads/upstream/stealthmax-main/StealthMax_300.step"   # nevermore3d/StealthMax @ a3451c5, GPL-3.0
DRY = not FreeCAD.GuiUp
CUT = (-420.0, 70.0, -70.0, 400.0)       # backbone cutout X0 Y0 X1 Y1 (#74 AC1)
BB_TOP, BB_BOT = -2.0, -10.0             # backbone faces
FRAME_BOTTOM = -50.0
BED_LOWEST_DZ = -241.98                  # bed's bottom of travel from the model pose (#74, boolean vs the backbone)
BED_T = ("2020 (1)", "2020 (2)")         # the bed frame's 2020 T
FILTER_TOP = -4.0                        # 2 mm under the backbone top, where the 2020 T lands
PLACE_MARGIN = 0.5                       # place the top this far below FILTER_TOP: optimalBoundingBox is tessellation-
                                         # dependent (GUI vs headless differed by 0.14 on this STEP)
BOARD_T, CLEAR = 18.0, 50.0              # board thickness; frame bottom to board top
AIR_GAP = 15.0
FOOT_XY = [(-500.0, -50.0), (10.0, -50.0), (-500.0, 460.0), (10.0, 460.0)]   # under the side 4040s, near the ends
KEEP = ["M_2.0_Body", "M_1a.0_Body_BPM", "M_2.1_CarbonBasket", "M_2.2a_CarbonBasketLid", "M_3.0_Body", "M_3.1_LidPanelHolder",
        "Acrylic Panel", "HEPA Filter", "SOLID", "M_2.3_HEPACover", "HubSupport", "3.3_LidLatch", "3.3_LidLatch001",
        "3.3_LidLatch002", "3.2_LidFrontHinge", "M_2.5a_LogoCap", "M_2.6a_PicoAccessLatch", "M_2.7_IntakeSensorStackAccessLatch",
        "M_2.8_BowdenTubeAccessLatch", "3mm sponge cord", "1.2_AirExhaustSlider", "M_1a.1_AirExhaustWheel_BPM"]
RENAME = {"SOLID": "fan (Delta BFB0712HF)"}
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite27_feet_filter.log", "w"); t0 = time.time()
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
def overlap(a, b):
    try: return a.common(b).Volume
    except Exception as e: log("  boolean failed:", e); return float("inf")
def fmt(b): return f"X {b.XMin:.1f}..{b.XMax:.1f} Y {b.YMin:.1f}..{b.YMax:.1f} Z {b.ZMin:.2f}..{b.ZMax:.2f}"
try:
    doc = FreeCAD.openDocument(SRC); log("opened", SRC)
    root = next(o for o in doc.Objects if o.TypeId == 'App::Part' and o.Label.startswith("4040-350x350x250 Voron Trident"))
    leaves = [o for o in doc.Objects if is_leaf(o)]
    shapes = {o.Name: gshape(o) for o in leaves}
    boxes = {n: obb(s) for n, s in shapes.items()}
    n_before = len(leaves)
    zmin = min(b.ZMin for b in boxes.values())
    low = sorted(((b.ZMin, o.Label) for o in leaves for b in [boxes[o.Name]]))[:4]
    log("lowest solids:", low)
    check(abs(zmin - FRAME_BOTTOM) < 0.05, f"printer's lowest point is the frame bottom: {zmin:.2f}")
    board_top = FRAME_BOTTOM - CLEAR

    # ---- filter: STEP -> core parts, turned 180 deg (upstream lid hinge at +Y = front -> our front is -Y), centred on the cutout
    fd = FreeCAD.newDocument("vt350_filter"); Import.insert(STEP, fd.Name); log("STEP loaded", len(fd.Objects))
    picked = {}
    for o in fd.Objects:
        if is_leaf(o) and o.Label in KEEP and o.Shape.Volume > 2000 and o.Label not in picked:
            if any(p.isDerivedFrom('Part::Feature') and p.TypeId != 'App::Part' for p in o.InList): continue
            picked[o.Label] = gshape(o)
    check(set(picked) == set(KEEP), f"all {len(KEEP)} core parts found (missing {sorted(set(KEEP) - set(picked))})")
    for nm in [o.Name for o in fd.Objects]:
        if fd.getObject(nm) is not None: fd.removeObject(nm)
    main = obb(picked["M_2.0_Body"]); core = obb(Part.makeCompound(list(picked.values())))
    cx, cy = (main.XMin + main.XMax) / 2, (main.YMin + main.YMax) / 2
    mx, my = (CUT[0] + CUT[2]) / 2, (CUT[1] + CUT[3]) / 2
    rot = FreeCAD.Placement(V(0, 0, 0), FreeCAD.Rotation(V(0, 0, 1), 180))
    move = FreeCAD.Placement(V(mx + cx, my + cy, FILTER_TOP - PLACE_MARGIN - core.ZMax), FreeCAD.Rotation()).multiply(rot)
    grp = fd.addObject('App::DocumentObjectGroup', 'StealthMax'); grp.Label = "StealthMax 300 (nevermore3d a3451c5, GPL-3.0), recessed concept"
    placed = {}
    for lab, s in picked.items():
        t = s.copy(); t.Placement = move.multiply(t.Placement)
        n = fd.addObject('Part::Feature', 'SM'); n.Shape = t; grp.addObject(n)
        n.Label = "StealthMax " + RENAME.get(lab, lab)
        if FreeCAD.GuiUp and lab == "Acrylic Panel": n.ViewObject.Transparency = 70
        placed[n.Label] = t
    fd.recompute()
    fb = obb(Part.makeCompound(list(placed.values()))); log("filter placed:", fmt(fb))
    check(fb.ZMax <= FILTER_TOP + 0.05, f"filter top {fb.ZMax:.2f} <= {FILTER_TOP}")
    tight = []
    for lab, t in placed.items():
        b = obb(t)
        if b.ZMax > BB_BOT and not (b.XMin >= CUT[0] + 5 and b.XMax <= CUT[2] - 5 and b.YMin >= CUT[1] + 5 and b.YMax <= CUT[3] - 5):
            tight.append(lab)
    check(not tight, f"filter parts that reach the backbone's level fit the cutout with >= 5 mm {tight}")
    log(f"cutout margins: X {fb.XMin - CUT[0]:.1f} / {CUT[2] - fb.XMax:.1f}, Y {fb.YMin - CUT[1]:.1f} / {CUT[3] - fb.YMax:.1f}")
    hits = []
    for o in leaves:
        b = boxes[o.Name]
        if not b.intersect(fb): continue
        for lab, t in placed.items():
            if obb(t).intersect(b) and overlap(t, shapes[o.Name]) > 1e-3: hits.append((lab, o.Label))
    check(not hits, f"filter x printer at the model pose: {len(hits)} overlaps {hits[:5]}")
    tz = [boxes[o.Name].ZMin + BED_LOWEST_DZ for o in leaves if o.Label in BED_T]
    check(len(tz) == 2 and min(tz) - fb.ZMax >= 1.0, f"bed 2020 T at the bottom of travel: Z {min(tz):.2f}, {min(tz) - fb.ZMax:.2f} above the filter")
    check(fb.ZMin - board_top >= AIR_GAP, f"filter bottom {fb.ZMin:.2f} is {fb.ZMin - board_top:.1f} above the board (>= {AIR_GAP})")

    # ---- feet + board (printer document)
    stand = doc.addObject('App::DocumentObjectGroup', 'Stand'); stand.Label = "Stand: levelling feet + base board (#83, placeholders)"
    loc = root.getGlobalPlacement().inverse()
    def add(shape, label, color):
        n = doc.addObject('Part::Feature', 'Stand'); s = shape.copy(); s.Placement = loc.multiply(s.Placement)
        n.Shape = s; stand.addObject(n); n.Label = label
        if FreeCAD.GuiUp: n.ViewObject.ShapeColor = color
        return n
    new = []
    for i, (x, y) in enumerate(FOOT_XY, 1):
        br = Part.makeBox(40, 40, 8, V(x - 20, y - 20, FRAME_BOTTOM - 8))
        stud = Part.makeCylinder(4, 24, V(x, y, FRAME_BOTTOM - 32))
        pad = Part.makeCylinder(25, 18, V(x, y, board_top))
        new += [add(br, f"Levelling foot {i} T-slot bracket (4040, placeholder)", (0.8, 0.8, 0.82)),
                add(stud, f"Levelling foot {i} M8 stud (placeholder)", (0.75, 0.75, 0.75)),
                add(pad, f"Levelling foot pad {i} (rubber, placeholder D50)", (0.08, 0.08, 0.08))]
    fr = FreeCAD.BoundBox(); [fr.add(boxes[o.Name]) for o in leaves]
    bx0, by0, bx1, by1 = fr.XMin - 20, fr.YMin - 20, fr.XMax + 20, fr.YMax + 20
    new.append(add(Part.makeBox(bx1 - bx0, by1 - by0, BOARD_T, V(bx0, by0, board_top - BOARD_T)),
                   f"Base board ({BOARD_T:.0f} mm, plywood/MDF, placeholder)", (0.7, 0.55, 0.35)))
    env = doc.addObject('Part::Feature', 'FilterEnvelope'); root.addObject(env)
    e = Part.makeBox(fb.XLength, fb.YLength, fb.ZLength, V(fb.XMin, fb.YMin, fb.ZMin)); e.Placement = loc.multiply(e.Placement)
    env.Shape = e; env.Label = "Filter envelope (contents in vt350-filter.FCStd)"
    if FreeCAD.GuiUp: env.ViewObject.ShapeColor = (0.3, 0.8, 0.5); env.ViewObject.Transparency = 80
    doc.recompute()
    for n in new:
        s = gshape(n); bad = []
        for o in leaves:
            if boxes[o.Name].intersect(s.BoundBox) and overlap(s, shapes[o.Name]) > 1e-3: bad.append(o.Label)
        check(not bad, f"{n.Label} touches nothing in the printer {bad[:3]}")
    seat = []
    for x, y in FOOT_XY:
        seat.append(any(o.Label.startswith(("4040", "2040")) and abs(boxes[o.Name].ZMin - FRAME_BOTTOM) < 0.05
                        and boxes[o.Name].XMin <= x - 20 + 0.01 and boxes[o.Name].XMax >= x + 20 - 0.01
                        and boxes[o.Name].YMin <= y - 20 + 0.01 and boxes[o.Name].YMax >= y + 20 - 0.01 for o in leaves))
    check(all(seat), f"each bracket's whole top face sits under a bottom extrusion: {seat}")
    after = sum(1 for o in doc.Objects if is_leaf(o))
    check(after == n_before + len(new) + 1, f"printer solids {n_before} -> {after} (+{len(new)} stand, +1 envelope)")
    json.dump({"filter_bbox": [fb.XMin, fb.YMin, fb.ZMin, fb.XMax, fb.YMax, fb.ZMax], "board_top": board_top,
               "feet": FOOT_XY, "parts": sorted(placed)}, open(WORK + "/logs/lite27_feet_filter.json", "w"), indent=1)
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else:
        fd.saveAs(FILT); log("SAVED", FILT, os.path.getsize(FILT))
        doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
