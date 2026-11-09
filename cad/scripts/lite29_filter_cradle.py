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
import FreeCAD, Part, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals()
                else os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "cad/scripts"))
import litelib
from litelib import box, obb, is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-28.FCStd", f"{MODELS}/vt350-lite-29.FCStd"
FSRC, FDST = f"{MODELS}/vt350-filter-2.FCStd", f"{MODELS}/vt350-filter-3.FCStd"
CUT = (-420.0, 70.0, -70.0, 400.0)
BB_TOP = -2.0
FRONT_BAR_Y, SPINE_X = 81.0, (-255.0, -235.0)
LIP_W, LIP_T, WALL_T, WALL_GAP, LEDGE_T, LEDGE_IN, RIDGE_W, RIDGE_H, RIDGE_GAP = 10.0, 4.0, 4.0, 0.5, 4.0, 15.0, 3.0, 5.0, 1.5
BOARD_TOP = -100.0
Y0, Y1 = 90.0, 390.0
# The filter stands on its bottom tray (M_1a.0_Body_BPM, under the main chamber), not on the chamber floor.
# Its plain BoundBox is polluted (Y to -419, Z to -372); the optimal box and a slice under the edges are right.
TRAY = "StealthMax M_1a.0_Body_BPM"


def main(p):
    pr = p.open(SRC); fm = p.open(FSRC)
    backbone, env = pr.leaf("backbone-350"), pr.leaf("Filter envelope")
    grp = next(o for o in fm.doc.Objects if o.TypeId == 'App::DocumentObjectGroup' and o.Label.startswith("StealthMax 300"))
    old = [o.Name for o in fm.doc.Objects if o.Label.startswith("StealthMax hanger lip")]
    p.check(len(old) == 2, f"two lite-28 hangers to replace ({len(old)})")
    for n in old: fm.doc.removeObject(n)
    fm.doc.recompute(); fm.refresh()
    fparts = fm.by_label()
    fboxes = {k: obb(s) for k, s in fparts.items()}
    fb = obb(Part.makeCompound(list(fparts.values()))); p.log("filter:", fb)
    chamber = fparts[TRAY]; mainb = fboxes[TRAY]
    p.log("bottom tray (support):", mainb)
    floors = []
    for x0, x1 in ((mainb.XMin, mainb.XMin + LEDGE_IN), (mainb.XMax - LEDGE_IN, mainb.XMax)):
        sl = chamber.common(box(x0, x1, Y0, Y1, mainb.ZMin - 5, mainb.ZMax)); floors.append(sl.BoundBox.ZMin)
    p.log("tray underside under the ledge strips (left, right):", [round(f, 2) for f in floors])
    p.check(abs(floors[0] - floors[1]) < 0.05, f"tray underside level on both sides {floors}")
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
        p.check(len(c.Solids) == 1, f"{side}: cradle half is one solid ({len(c.Solids)})")
        cradles.append((side, c))
        cb = c.BoundBox; p.log(f"{side}: cradle {cb}")
        lipfoot = box(lip[0] if side == "left" else CUT[2], CUT[0] if side == "left" else lip[1], Y0, Y1, BB_TOP - 0.5, BB_TOP)
        p.over_material(lipfoot, pr.shapes[backbone.Name],
                        lambda r: f"{side}: lip footprint over backbone material {r.frac:.0%} (slots allowed)")
        p.check(cb.YMin >= FRONT_BAR_Y + 5 and not (cb.XMin < SPINE_X[1] and cb.XMax > SPINE_X[0]),
                f"{side}: clear of the 2020 T's landing (Y >= {FRONT_BAR_Y + 5}, off the spine)")
        sup = (ledge[1] - mainb.XMin) if side == "left" else (mainb.XMax - ledge[0])
        p.check(sup >= 10.0, f"{side}: ledge reaches {sup:.1f} mm under the bottom tray (Z {floor:.2f})")
        pen = p.vol(c, chamber)
        p.check(pen <= 1.0, f"{side}: cradle x bottom tray interpenetration {pen:.2f} mm3")
        dch = c.distToShape(chamber)[0]
        p.check(dch <= 0.2, f"{side}: bottom tray rests on the ledge (distance {dch:.2f})")
        p.min_distance(c, fparts, lambda r: f"{side}: >= 0.5 mm off every other filter part {r.near[:4]}",
                       min_d=0.5, skip=(TRAY,))
        p.lift_out_clear(c, fboxes, lambda r: f"{side}: lift-out path clear (cradle in the column above a filter part: "
                                              f"{r.blocked[:4]})", height=200, start_z={TRAY: floor + 0.01})
        p.check(LZ0 - BOARD_TOP >= 15.0, f"{side}: ledge bottom {LZ0:.1f} is {LZ0 - BOARD_TOP:.1f} above the board")
    bed = p.clear_of_bed_travel(cradles, pr, lambda r: f"bed at the bottom of travel vs cradle: closest {r.gap:.2f} ({r.who})")
    p.no_overlap(cradles, pr, lambda r: f"cradle x printer at the model pose: {r.hits[:5]}", exclude=(env.Name,))
    p.add_solids(fm.doc, grp, cradles, 'Cradle', "StealthMax cradle half, {} (remix concept)")
    nb = FreeCAD.BoundBox(fb); [nb.add(c.BoundBox) for _, c in cradles]
    p.resize_envelope(pr, env, nb, "Filter envelope (contents in vt350-filter-3.FCStd)")
    p.check(sum(1 for o in pr.doc.Objects if is_leaf(o)) == len(pr.leaves), "printer solid count unchanged")
    p.dump({"cradles": {s: [c.BoundBox.XMin, c.BoundBox.YMin, c.BoundBox.ZMin, c.BoundBox.XMax, c.BoundBox.YMax, c.BoundBox.ZMax]
                        for s, c in cradles}, "bed_gap": bed.gap, "envelope": [nb.XMin, nb.YMin, nb.ZMin, nb.XMax, nb.YMax, nb.ZMax]})
    p.finish([(fm.doc, FDST), (pr.doc, DST)])


litelib.Pass("lite29_filter_cradle").run(main)
