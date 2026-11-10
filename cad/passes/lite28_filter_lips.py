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
import FreeCAD, Part, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))      # litelib, which puts the other code folders on the path
import litelib
from litelib import box, obb, gshape, is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-27.FCStd", f"{MODELS}/vt350-lite-28.FCStd"
FSRC, FDST = f"{MODELS}/vt350-filter.FCStd", f"{MODELS}/vt350-filter-2.FCStd"
CUT = (-420.0, 70.0, -70.0, 400.0)
BB_TOP = -2.0
FRONT_BAR_Y, SPINE_X = 81.0, (-255.0, -235.0)
LIP_W, LIP_T, DROP_T, WALL_GAP = 10.0, 4.0, 4.0, 0.5
Y0, Y1 = 90.0, 390.0
BODY = "StealthMax M_2.0_Body"


def main(p):
    pr = p.open(SRC); fm = p.open(FSRC)
    backbone, env = pr.leaf("backbone-350"), pr.leaf("Filter envelope")
    grp = next(o for o in fm.doc.Objects if o.TypeId == 'App::DocumentObjectGroup' and o.Label.startswith("StealthMax 300"))
    fparts = fm.by_label()
    fb = obb(Part.makeCompound(list(fparts.values()))); p.log("filter:", fb)
    mainb, lidb = obb(fparts[BODY]), obb(fparts["StealthMax M_3.0_Body"])
    p.log("main chamber:", mainb, "lid frame:", lidb)
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
        p.check(len(lat) == 1, f"{side}: one lid latch on this side ({len(lat)})")
        ly0, ly1 = lat[0].YMin - 3.0, lat[0].YMax + 3.0
        parts = []
        for a, b in [(Y0, ly0), (ly1, Y1)]:
            parts.append(box(*lip, a, b, BB_TOP, BB_TOP + LIP_T))                    # lip resting on the backbone
            parts.append(box(*drop, a, b, TAB_Z0, BB_TOP + LIP_T))                   # drop down the gap
            parts.append(box(*tab, a, b, TAB_Z0, TAB_Z1))                            # tab into the chamber wall
        h = parts[0].fuse(parts[1:]).removeSplitter()
        hangers.append((side, h))
        p.log(f"{side}: hanger {h.BoundBox}; latch Y {lat[0].YMin:.1f}..{lat[0].YMax:.1f} -> gap {ly0:.1f}..{ly1:.1f}")
        p.on_face(h, BB_TOP, f"{side}: lip bottom face on the backbone top Z {BB_TOP}", top=BB_TOP + LIP_T)
        lipfoot = box(lip[0] if side == "left" else CUT[2], CUT[0] if side == "left" else lip[1], Y0, Y1, BB_TOP - 0.5, BB_TOP)
        p.over_material(lipfoot, pr.shapes[backbone.Name],
                        lambda r: f"{side}: lip footprint over backbone material {r.frac:.0%} (slots allowed)")
        hb = h.BoundBox
        p.check(hb.YMin >= FRONT_BAR_Y + 5 and not (hb.XMin < SPINE_X[1] and hb.XMax > SPINE_X[0]),
                f"{side}: clear of the 2020 T's landing (Y >= {FRONT_BAR_Y + 5}, off the spine)")
        onto = p.vol(h, fparts[BODY])
        p.check(onto > 1.0, f"{side}: arm reaches onto the filter body (overlap {onto:.0f} mm3, to be fused in the remix)")
        p.min_distance(h, {lat_k[0]: fparts[lat_k[0]]}, lambda r: f"{side}: hanger keeps {r.d:.2f} mm off the lid latch",
                       min_d=1.0)
        p.min_distance(h, fparts, lambda r: f"{side}: hanger keeps >= 0.5 mm off every other filter part "
                                            f"(lid, latches, access latches) {r.near[:4]}", min_d=0.5, skip=(BODY,))
    bed = p.clear_of_bed_travel(hangers, pr, lambda r: f"bed at the bottom of travel vs hangers: closest {r.gap:.2f} ({r.who})")
    p.no_overlap(hangers, pr, lambda r: f"hangers x printer at the model pose: {r.hits[:5]}", exclude=(env.Name,))
    # ---- write: hangers into the filter doc, envelope grown
    p.add_solids(fm.doc, grp, hangers, 'Hanger', "StealthMax hanger lip, {} (remix concept)")
    nb = FreeCAD.BoundBox(fb); [nb.add(h.BoundBox) for _, h in hangers]
    p.resize_envelope(pr, env, nb, "Filter envelope (contents in vt350-filter-2.FCStd)")
    p.check(sum(1 for o in pr.doc.Objects if is_leaf(o)) == len(pr.leaves), "printer solid count unchanged")
    p.dump({"hangers": {s: [h.BoundBox.XMin, h.BoundBox.YMin, h.BoundBox.ZMin, h.BoundBox.XMax, h.BoundBox.YMax, h.BoundBox.ZMax]
                        for s, h in hangers}, "bed_gap": bed.gap, "envelope": [nb.XMin, nb.YMin, nb.ZMin, nb.XMax, nb.YMax, nb.ZMax]})
    p.finish([(fm.doc, FDST), (pr.doc, DST)])


litelib.Pass("lite28_filter_lips").run(main)
