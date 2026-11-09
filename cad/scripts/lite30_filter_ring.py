# GUI pass: vt350-lite-29 + vt350-filter-3 -> vt350-lite-30 + vt350-filter-4   (headless = dry run, never saves)
# #74 AC3 (user, 2026-11-09): the filter holder goes around the WHOLE circumference, and the gap between it and the
# backbone cutout is sealed so air can't blow out under the backbone. The seal is TPU, printed on the VT350 itself
# (no filtration needed for basic filaments), as TWO U-SHAPED HALVES that follow the cutout.
# Built on litelib (#93). Replaces lite-29's two cradle halves with one ring:
#   collar : a 4 mm wall all round, SEAL_GAP inside the cutout edge, from COLLAR_Z0 up to COLLAR_TOP (1 mm under the
#            backbone top, so the bed's 2020 T, which lands on the backbone's front edge and along the spine at the
#            bottom of Z travel, stays clear); a GROOVE-deep channel round its outer face at the backbone's mid-height;
#   sides  : lite-29's left/right cradle (10 mm lip on the backbone top, wall down the cutout, ledge under the filter's
#            bottom tray, ridge), on the collar's left/right walls;
#   seal   : a CORD x CORD TPU cord in the channel, 2 mm proud, pressed against the cutout's inner edge face (the
#            wall-to-edge gap is SEAL_GAP, so the cord is squeezed CORD - GROOVE - SEAL_GAP = 0.5 mm); modelled
#            squeezed (flush with the edge) in the assembly, printed CORD x CORD. Two U halves, LEFT and RIGHT, with a
#            half-height lap joint at SPLIT_X (split across X: a front/rear split leaves each half the full 351 mm
#            wide, more than the VT350's 342 mm printable width).
# Not in this pass yet: the front/rear ledges and the duct between the filter's flow chamber and the chamber. The
# section cuts (#74) put the filter's outlet on its rear edge (X -260.7..-229.7, Z -77..-66), below the backbone, so
# once the cutout is sealed the airflow path has to be designed with it.
# Checks (refuses to save on any): ring is one solid; lips over backbone material, off the 2020 T's landing; nothing of
# the ring or seal above COLLAR_TOP outside the lips; bed at the bottom of travel clears everything by >= 1 mm (lips
# >= 5); each seal half one solid, the halves add up to the loop with no overlap, each fits the print area (2 mm spare);
# the seal touches the cutout edge on all four sides; ring >= 0.5 mm off every filter part but the tray it carries;
# lift-out path clear; no overlap with the printer.
import FreeCAD, Part, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals()
                else os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "cad/scripts"))
import litelib
from litelib import box, obb, is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-29.FCStd", f"{MODELS}/vt350-lite-30.FCStd"
FSRC, FDST = f"{MODELS}/vt350-filter-3.FCStd", f"{MODELS}/vt350-filter-4.FCStd"
CUT = (-420.0, 70.0, -70.0, 400.0)
CUT_R = 10.0                                    # cutout corner radius (measured on lite-29: R 10 at Z -2.5/-6/-9.5)
BB_TOP, BB_BOT = -2.0, -10.0
FRONT_BAR_Y, SPINE_X = 81.0, (-255.0, -235.0)
LIP_W, LIP_T, WALL_T, LEDGE_T, LEDGE_IN, RIDGE_W, RIDGE_H, RIDGE_GAP = 10.0, 4.0, 4.0, 4.0, 15.0, 3.0, 5.0, 1.5
SEAL_GAP, GROOVE, CORD = 1.5, 1.0, 3.0          # wall-to-edge gap; channel depth; printed cord section
SEAL_Z = (BB_TOP + BB_BOT) / 2                   # cord centred on the backbone's mid-height
COLLAR_TOP, COLLAR_Z0 = BB_TOP - 1.0, BB_BOT - 6.0
SPLIT_X, LAP = -245.0, 10.0                     # the halves meet on the cutout's centre line
Y0, Y1 = 90.0, 390.0                            # lips (lite-28/29)
BOARD_TOP = -100.0
TRAY = "StealthMax M_1a.0_Body_BPM"


def rrect(inset, z0, z1):
    """The cutout's outline (350 x 330, R CUT_R corners) offset `inset` inwards (negative: outwards), as a prism."""
    b = box(CUT[0] + inset, CUT[2] - inset, CUT[1] + inset, CUT[3] - inset, z0, z1)
    r = CUT_R - inset
    if r > 0.01:
        vert = [e for e in b.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[-1].Point.z) > 1e-6]
        b = b.makeFillet(r, vert)
    return b


def rect_frame(inset_out, inset_in, z0, z1):
    """Frame following the cutout (concentric corners): outer edge `inset_out` inside it, inner edge `inset_in`."""
    return rrect(inset_out, z0, z1).cut(rrect(inset_in, z0 - 1, z1 + 1))


def seal_halves(loop):
    """Split the loop across X at SPLIT_X with a half-height lap LAP long: the left half keeps the lap's lower layer."""
    zm = SEAL_Z; big = 1000.0
    lo = box(-big, SPLIT_X, -big, big, -big, big).fuse(box(SPLIT_X, SPLIT_X + LAP, -big, big, -big, zm))
    hi = box(SPLIT_X + LAP, big, -big, big, -big, big).fuse(box(SPLIT_X, SPLIT_X + LAP, -big, big, zm, big))
    return loop.common(lo).removeSplitter(), loop.common(hi).removeSplitter()


def main(p):
    pr = p.open(SRC); fm = p.open(FSRC)
    backbone, env = pr.leaf("backbone-350"), pr.leaf("Filter envelope")
    grp = next(o for o in fm.doc.Objects if o.TypeId == 'App::DocumentObjectGroup' and o.Label.startswith("StealthMax 300"))
    old = [o.Name for o in fm.doc.Objects if o.Label.startswith("StealthMax cradle half")]
    p.check(len(old) == 2, f"two lite-29 cradle halves to replace ({len(old)})")
    for n in old: fm.doc.removeObject(n)
    fm.doc.recompute(); fm.refresh()
    fparts = fm.by_label(); fboxes = {k: obb(s) for k, s in fparts.items()}
    fb = obb(Part.makeCompound(list(fparts.values()))); p.log("filter:", fb)
    chamber = fparts[TRAY]; mainb = fboxes[TRAY]
    floors = []
    for x0, x1 in ((mainb.XMin, mainb.XMin + LEDGE_IN), (mainb.XMax - LEDGE_IN, mainb.XMax)):
        floors.append(chamber.common(box(x0, x1, Y0, Y1, mainb.ZMin - 5, mainb.ZMax)).BoundBox.ZMin)
    p.log("tray underside under the side ledges (left, right):", [round(f, 2) for f in floors])
    floor = min(floors); LZ0 = floor - LEDGE_T

    # ---- ring: collar + left/right cradles, channel for the cord
    wall_in = SEAL_GAP + WALL_T
    collar = rect_frame(SEAL_GAP, wall_in, COLLAR_Z0, COLLAR_TOP)
    parts = [collar]
    for side in ("left", "right"):
        if side == "left":
            lip = (CUT[0] - LIP_W, CUT[0] + SEAL_GAP); wall = (CUT[0] + SEAL_GAP, CUT[0] + wall_in)
            ledge = (wall[0], mainb.XMin + LEDGE_IN); ridge = (mainb.XMin - RIDGE_GAP - RIDGE_W, mainb.XMin - RIDGE_GAP)
        else:
            lip = (CUT[2] - SEAL_GAP, CUT[2] + LIP_W); wall = (CUT[2] - wall_in, CUT[2] - SEAL_GAP)
            ledge = (mainb.XMax - LEDGE_IN, wall[1]); ridge = (mainb.XMax + RIDGE_GAP, mainb.XMax + RIDGE_GAP + RIDGE_W)
        parts += [box(*lip, Y0, Y1, BB_TOP, BB_TOP + LIP_T), box(*wall, Y0, Y1, LZ0, BB_TOP + LIP_T),
                  box(*ledge, Y0, Y1, LZ0, floor), box(*ridge, Y0, Y1, floor, floor + RIDGE_H)]
    channel = rect_frame(SEAL_GAP - 0.01, SEAL_GAP + GROOVE, SEAL_Z - CORD / 2, SEAL_Z + CORD / 2)
    ring = parts[0].fuse(parts[1:]).removeSplitter().cut(channel).removeSplitter()
    p.check(len(ring.Solids) == 1, f"ring is one solid ({len(ring.Solids)})")
    p.log("ring:", ring.BoundBox)

    # ---- seal: squeezed in the assembly (flush with the edge), printed CORD x CORD
    zc = (SEAL_Z - CORD / 2, SEAL_Z + CORD / 2)
    loop = rect_frame(0.01, SEAL_GAP + GROOVE, *zc)
    printed = rect_frame(SEAL_GAP + GROOVE - CORD, SEAL_GAP + GROOVE, *zc)
    halves = seal_halves(loop); phalves = seal_halves(printed)
    for tag, h, ph in (("left", halves[0], phalves[0]), ("right", halves[1], phalves[1])):
        p.check(len(h.Solids) == 1, f"seal {tag} half is one solid ({len(h.Solids)})")
        p.fits_print_area(ph, lambda r: f"seal {tag} half prints in one piece: {r.size[0]:.1f} x {r.size[1]:.1f} on "
                                        f"{r.area[0]} x {r.area[1]} (2 mm spare{', turned' if r.rotated else ''})", margin=2.0)
    v = [h.Volume for h in halves]
    p.check(abs(sum(v) - loop.Volume) < 1e-3 and p.vol(*halves) < 1e-3,
            f"seal halves add up to the loop ({v[0]:.1f} + {v[1]:.1f} = {loop.Volume:.1f} mm3), no overlap")
    seal = halves[0].fuse(halves[1])
    p.log(f"seal squeeze: printed {CORD} -> {SEAL_GAP + GROOVE - 0.01:.2f} wide ({CORD - SEAL_GAP - GROOVE:.1f} mm, "
          f"{(CORD - SEAL_GAP - GROOVE) / CORD:.0%})")
    bbs = pr.shapes[backbone.Name]
    for name, band in (("left", box(CUT[0] - 1, CUT[0] + 1, 150, 320, -20, 5)), ("right", box(CUT[2] - 1, CUT[2] + 1, 150, 320, -20, 5)),
                       ("front", box(-380, -110, CUT[1] - 1, CUT[1] + 1, -20, 5)), ("rear", box(-380, -110, CUT[3] - 1, CUT[3] + 1, -20, 5))):
        d = seal.common(band).distToShape(bbs)[0]
        p.check(d <= 0.05, f"seal touches the cutout edge, {name} side (gap {d:.2f})")

    # ---- the ring and seal vs everything
    p.over_material(box(CUT[0] - LIP_W, CUT[0], Y0, Y1, BB_TOP - 0.5, BB_TOP), bbs,
                    lambda r: f"left: lip footprint over backbone material {r.frac:.0%} (slots allowed)")
    p.over_material(box(CUT[2], CUT[2] + LIP_W, Y0, Y1, BB_TOP - 0.5, BB_TOP), bbs,
                    lambda r: f"right: lip footprint over backbone material {r.frac:.0%} (slots allowed)")
    up = ring.common(box(-1000, 1000, -1000, 1000, COLLAR_TOP + 1e-6, 1000))
    ub = up.BoundBox
    p.check(not up.Solids or (ub.YMin >= FRONT_BAR_Y + 5 and all(not (s.BoundBox.XMin < SPINE_X[1] and s.BoundBox.XMax > SPINE_X[0])
                                                                 for s in up.Solids)),
            f"above Z {COLLAR_TOP}: only the lips (Y >= {FRONT_BAR_Y + 5}, off the spine)")
    # the ring is a hollow frame: one bounding box would cover the whole cutout at the lips' height, so the box
    # test runs on its pieces (each lip/wall top above COLLAR_TOP, the collar below it) and the seal
    low = ring.common(box(-1000, 1000, -1000, 1000, -1000, COLLAR_TOP))
    pieces = [(f"lip {'left' if s.BoundBox.XMin < -245 else 'right'}", s) for s in up.Solids] + [("collar", low), ("seal", seal)]
    p.clear_of_bed_travel(pieces, pr,
                          lambda r: f"bed at the bottom of travel vs ring + seal: closest {r.gap:.2f} ({r.who})", min_gap=1.0)
    p.min_distance(ring, fparts, lambda r: f"ring >= 0.5 mm off every filter part but the tray {r.near[:4]}",
                   min_d=0.5, skip=(TRAY,))
    pen = p.vol(ring, chamber)
    p.check(pen <= 1.0, f"ring x bottom tray interpenetration {pen:.2f} mm3")
    p.lift_out_clear(ring, fboxes, lambda r: f"lift-out path clear (ring in the column above a filter part: {r.blocked[:4]})",
                     start_z={TRAY: floor + 0.01})
    p.check(LZ0 - BOARD_TOP >= 15.0, f"ledge bottom {LZ0:.1f} is {LZ0 - BOARD_TOP:.1f} above the board")
    p.no_overlap([("ring", ring), ("seal", seal)], pr, lambda r: f"ring + seal x printer at the model pose: {r.hits[:5]}",
                 exclude=(env.Name,))

    # ---- write
    p.add_solids(fm.doc, grp, [("ring", ring)], 'Ring', "StealthMax cradle {} (remix concept, PET-GF)")
    p.add_solids(fm.doc, grp, [("left", halves[0]), ("right", halves[1])], 'Seal',
                 "StealthMax cutout seal, {} half (TPU)", color=(0.15, 0.15, 0.15))
    nb = FreeCAD.BoundBox(fb); nb.add(ring.BoundBox); nb.add(seal.BoundBox)
    p.resize_envelope(pr, env, nb, "Filter envelope (contents in vt350-filter-4.FCStd)")
    p.check(sum(1 for o in pr.doc.Objects if is_leaf(o)) == len(pr.leaves), "printer solid count unchanged")
    p.dump({"ring": [ring.BoundBox.XMin, ring.BoundBox.YMin, ring.BoundBox.ZMin, ring.BoundBox.XMax, ring.BoundBox.YMax,
                     ring.BoundBox.ZMax], "seal_printed_halves": [list(obb(h).XLength for h in phalves), list(obb(h).YLength for h in phalves)],
            "envelope": [nb.XMin, nb.YMin, nb.ZMin, nb.XMax, nb.YMax, nb.ZMax]})
    p.finish([(fm.doc, FDST), (pr.doc, DST)])


litelib.Pass("lite30_filter_ring").run(main)
