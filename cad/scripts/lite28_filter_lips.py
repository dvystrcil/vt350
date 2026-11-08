# GUI pass: vt350-lite-27 + vt350-filter -> vt350-lite-28 + vt350-filter-2   (headless = dry run, never saves)
# #74 AC3 (user, 2026-11-08): the StealthMax hangs in the backbone cutout by a lip that extends 10 mm over the
# backbone's top face, and is lifted out from above. A lip all round is not possible: at the bottom of Z travel the
# bed frame's 2020 T rests on the backbone's top face, its front bar over the cutout's front edge (Y 61..81) and its
# centre spine across the rear edge (X -255..-235). So the lips are on the LEFT and RIGHT edges only, where the nearest
# bed parts at the bottom of travel are >= 18 mm up.
# Each side: a hanger (concept for the remixed housing, orange PET-GF) = a lip on the backbone (10 mm over it, LIP_T thick,
# bottom face ON the backbone top) + a drop down the cutout gap + a tab into the main chamber wall under the lid frame (the lid
# still lifts off). Split
# around the lid latch on that side so the lid still opens once the filter is lifted out.
# The printer's "Filter envelope" grows to include the hangers and points at vt350-filter-2.FCStd.
# Checks (refuses to save on any):
#  - lip bottoms lie on the backbone top face (Z -2) and over backbone material for their whole footprint (10 mm wide);
#  - lips stay clear of the front bar strip (Y <= 81 + 5) and the spine (X -255..-235);
#  - hangers vs bed parts moved to the bottom of travel (dZ BED_LOWEST_DZ): vertical gap >= 5 mm (box test, exact for
#    the box-shaped hangers, conservative for the bed);
#  - hangers vs printer solids at the model pose: no overlap (boolean);
#  - each arm reaches onto the filter body (overlap with M_2.0_Body or M_3.0_Body > 0: it is meant to fuse into it);
#  - hangers keep >= 1 mm off each lid latch.
import FreeCAD, Part, sys, os, time, json, traceback
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", f"{REPO}/cad/data")
MODELS = "/home/dan/Documents/VT350"
SRC, DST = f"{MODELS}/vt350-lite-27.FCStd", f"{MODELS}/vt350-lite-28.FCStd"
FSRC, FDST = f"{MODELS}/vt350-filter.FCStd", f"{MODELS}/vt350-filter-2.FCStd"
DRY = not FreeCAD.GuiUp
CUT = (-420.0, 70.0, -70.0, 400.0)
BB_TOP = -2.0
BED_LOWEST_DZ = -241.98
FRONT_BAR_Y, SPINE_X = 81.0, (-255.0, -235.0)
LIP_W, LIP_T, DROP_T, WALL_GAP = 10.0, 4.0, 4.0, 0.5
Y0, Y1 = 90.0, 390.0
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite28_filter_lips.log", "w"); t0 = time.time()
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
    fparts = {o.Label: gshape(o) for o in fd.Objects if is_leaf(o)}
    fb = obb(Part.makeCompound(list(fparts.values()))); log("filter:", fb)
    mainb, lidb = obb(fparts["StealthMax M_2.0_Body"]), obb(fparts["StealthMax M_3.0_Body"])
    log("main chamber:", mainb, "lid frame:", lidb)
    body = [fparts["StealthMax M_2.0_Body"]]
    latches = {k: obb(s) for k, s in fparts.items() if "LidLatch" in k}
    TAB_Z1 = lidb.ZMin - 1.0; TAB_Z0 = TAB_Z1 - 7.0          # into the main chamber wall, under the lid frame
    hangers = []
    # per side: lip X range (on the backbone), drop X range (in the gap, outside the main chamber), tab X range (into its wall)
    for side, (lip, drop, tab) in {
            "left": ((CUT[0] - LIP_W, CUT[0] + WALL_GAP), (CUT[0] + WALL_GAP, CUT[0] + WALL_GAP + DROP_T),
                     (CUT[0] + WALL_GAP, mainb.XMin + 3.0)),
            "right": ((CUT[2] - WALL_GAP, CUT[2] + LIP_W), (CUT[2] - WALL_GAP - DROP_T, CUT[2] - WALL_GAP),
                      (mainb.XMax - 3.0, CUT[2] - WALL_GAP))}.items():
        lat_k = [k for k, b in latches.items() if (b.XMin < fb.XMin + 20 if side == "left" else b.XMax > fb.XMax - 20)]
        lat = [latches[k] for k in lat_k]
        check(len(lat) == 1, f"{side}: one lid latch on this side ({len(lat)})")
        ly0, ly1 = lat[0].YMin - 3.0, lat[0].YMax + 3.0
        segs = [(Y0, ly0), (ly1, Y1)]
        parts = []
        for a, b in segs:
            parts.append(box(*lip, a, b, BB_TOP, BB_TOP + LIP_T))                    # lip resting on the backbone
            parts.append(box(*drop, a, b, TAB_Z0, BB_TOP + LIP_T))                   # drop down the gap
            parts.append(box(*tab, a, b, TAB_Z0, TAB_Z1))                            # tab into the chamber wall
        h = parts[0].fuse(parts[1:]).removeSplitter()
        hangers.append((side, h, None, segs))
        lipfoot = box(lip[0] if side == "left" else CUT[2], CUT[0] if side == "left" else lip[1], Y0, Y1, BB_TOP - 0.5, BB_TOP)
        under = vol(lipfoot, shapes[backbone.Name])
        log(f"{side}: hanger {h.BoundBox}; latch Y {lat[0].YMin:.1f}..{lat[0].YMax:.1f} -> gap {ly0:.1f}..{ly1:.1f}")
        check(abs(h.BoundBox.ZMax - (BB_TOP + LIP_T)) < 1e-6 and abs(min(f.BoundBox.ZMin for f in h.Faces if abs(f.BoundBox.ZMax - BB_TOP) < 1e-6 and abs(f.BoundBox.ZMin - BB_TOP) < 1e-6 and f.Area > 100) - BB_TOP) < 1e-6,
              f"{side}: lip bottom face on the backbone top Z {BB_TOP}")
        solid_frac = under / (LIP_W * (Y1 - Y0) * 0.5)
        check(solid_frac > 0.9, f"{side}: lip footprint over backbone material {solid_frac:.0%} (slots allowed)")
        hb = h.BoundBox
        check(hb.YMin >= FRONT_BAR_Y + 5 and not (hb.XMin < SPINE_X[1] and hb.XMax > SPINE_X[0]),
              f"{side}: clear of the 2020 T's landing (Y >= {FRONT_BAR_Y + 5}, off the spine)")
        onto = max(vol(h, b) for b in body)
        check(onto > 1.0, f"{side}: arm reaches onto the filter body (overlap {onto:.0f} mm3, to be fused in the remix)")
        dl = h.distToShape(fparts[lat_k[0]])[0]
        check(dl >= 1.0, f"{side}: hanger keeps {dl:.2f} mm off the lid latch")
        near = [(k, round(h.distToShape(t)[0], 2)) for k, t in fparts.items()
                if k != "StealthMax M_2.0_Body" and obb(t).intersect(h.BoundBox) or (k != "StealthMax M_2.0_Body" and h.distToShape(t)[0] < 0.5)]
        near = [(k, d) for k, d in near if d < 0.5]
        check(not near, f"{side}: hanger keeps >= 0.5 mm off every other filter part (lid, latches, access latches) {near[:4]}")
    # bed at the bottom of travel vs hangers: every bed-side solid (ZMin 230..300 at the model pose, over the backbone)
    bed = [o for o in leaves if 230 <= boxes[o.Name].ZMin <= 300 and boxes[o.Name].ZMax <= 300]
    worst = (999, "")
    for side, h, _, _ in hangers:
        hb = h.BoundBox
        for o in bed:
            b = boxes[o.Name]
            if b.XMin < hb.XMax and b.XMax > hb.XMin and b.YMin < hb.YMax and b.YMax > hb.YMin:
                gap = b.ZMin + BED_LOWEST_DZ - hb.ZMax
                if gap < worst[0]: worst = (gap, f"{side} vs {o.Label}")
    check(worst[0] >= 5.0, f"bed at the bottom of travel vs hangers: closest {worst[0]:.2f} ({worst[1]})")
    hits = []
    for side, h, _, _ in hangers:
        for o in leaves:
            if o.Name == env.Name: continue
            if boxes[o.Name].intersect(h.BoundBox) and vol(h, shapes[o.Name]) > 1e-3: hits.append((side, o.Label))
    check(not hits, f"hangers x printer at the model pose: {hits[:5]}")
    # ---- write: hangers into the filter doc, envelope grown
    for side, h, _, _ in hangers:
        n = fd.addObject('Part::Feature', 'Hanger'); n.Shape = h; grp.addObject(n)
        n.Label = f"StealthMax hanger lip, {side} (remix concept)"
        if FreeCAD.GuiUp: n.ViewObject.ShapeColor = (0.89, 0.4, 0.16)
    fd.recompute()
    nb = FreeCAD.BoundBox(fb); [nb.add(h.BoundBox) for _, h, _, _ in hangers]
    e = box(nb.XMin, nb.XMax, nb.YMin, nb.YMax, nb.ZMin, nb.ZMax); e.Placement = root.getGlobalPlacement().inverse().multiply(e.Placement)
    env.Shape = e; env.Label = "Filter envelope (contents in vt350-filter-2.FCStd)"
    doc.recompute()
    log("envelope:", gshape(env).BoundBox)
    check(sum(1 for o in doc.Objects if is_leaf(o)) == len(leaves), "printer solid count unchanged")
    json.dump({"hangers": {s: [h.BoundBox.XMin, h.BoundBox.YMin, h.BoundBox.ZMin, h.BoundBox.XMax, h.BoundBox.YMax, h.BoundBox.ZMax]
                           for s, h, _, _ in hangers}, "bed_gap": worst[0], "envelope": [nb.XMin, nb.YMin, nb.ZMin, nb.XMax, nb.YMax, nb.ZMax]},
              open(WORK + "/logs/lite28_filter_lips.json", "w"), indent=1)
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
