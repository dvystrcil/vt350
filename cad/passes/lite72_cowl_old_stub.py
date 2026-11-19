# GUI pass: vt350-lite-71 -> vt350-lite-72   (headless = dry run, never saves)   vt350#59
# Removes lite-23's old rear-bottom dock boss from both cowls (owner, 2026-11-18: "you did not remove the old lower
# docking standoff"). lite-68 moved the rear-bottom insert 18.5 mm forward and 6.25 mm up into the cowl's solid
# corner, but kept lite-67's cowl, so the old boss stayed on: a dia 8 stub, 138 mm3 proud of DW-Tas's duct, with its
# old dia 2.9 screw tail still in it. Nothing uses it now.
#
# The stub is found as a solid of (cowl - DW-Tas's original duct), the original read from lite-22 (before any dock
# boss; same frame as the cowl, since the head groups move as wholes). Of the three such solids, the two top stubs
# carry the top inserts (a dia 4.8 pocket on their axis) and stay; the third, 54 mm from the rear-top axis on lite-23's
# screw square, is cut off. The old pocket lies wholly in the stub, so the cowl there becomes the original duct again.
# Checks (refuses to save on any):
#  - two cowls, three added solids each, exactly one of them pocket-free and on the 20 x 54 screw square;
#  - after the cut: one valid solid, volume = before - stub; (new - original) = the two top stubs only; (original -
#    new) unchanged (only lite-68's moved rear-bottom spot-face + pocket); no dia 2.9 tail left;
#  - the cut is >= 0.5 mm from lite-68's rear-bottom spot-face;
#  - every other solid's box unchanged; the head copies (links) follow their cowl.
import FreeCAD, Part, math, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC = os.environ.get("VT350_SRC", f"{MODELS}/vt350-lite-71.FCStd")    # dry runs may point at lite-70
DST = f"{MODELS}/vt350-lite-72.FCStd"
ORIG = f"{MODELS}/vt350-lite-22.FCStd"                                 # DW-Tas's ducts, before lite-23's bosses
DUCTS = {"Left": "[a]_Duct-4010-left MadMax dock bosses (remix, CC BY-NC-SA 4.0)",
         "Right": "[a]_Duct-4010-right MadMax dock bosses (remix, CC BY-NC-SA 4.0)"}
ORIG_DUCTS = {"Left": "[a]_Duct-4010-left", "Right": "[a]_Duct-4010-right001"}
POCKET_R, TAIL_R, SPOT_R = 2.4, 1.45, 2.75     # lite-68's insert pocket, lite-23's screw tail, lite-68's spot-face


def axes(S, r):
    """(y, z) of S's cylinder faces of radius r along X (the screw axes, in the duct's frame)."""
    return sorted({(round(f.Surface.Center.y, 3), round(f.Surface.Center.z, 3)) for f in S.Faces
                   if f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - r) < 1e-6
                   and abs(abs(f.Surface.Axis.x) - 1) < 1e-6})


def near(c, a, tol=1.0): return math.hypot(c.y - a[0], c.z - a[1]) < tol


def main(p):
    od = FreeCAD.openDocument(ORIG); p.log("opened (read-only)", ORIG)
    orig = {}
    for side, lab in ORIG_DUCTS.items():
        c = [o for o in od.Objects if o.Label == lab and hasattr(o, "Shape") and o.Shape.Volume > 1000]
        p.check(len(c) == 1, f"{side}: one original duct {lab!r} in lite-22 ({len(c)})")
        if c: orig[side] = c[0].Shape.copy()
    if p.errs: return p.finish([])
    pr = p.open(SRC); doc = pr.doc
    targets = {}
    for side, lab in DUCTS.items():
        c = [o for o in doc.getObjectsByLabel(lab) if o.TypeId == "Part::Feature"]
        p.check(len(c) == 1, f"{side}: one cowl {lab!r} ({len(c)})")
        if c: targets[side] = c[0]
    if p.errs: return p.finish([])
    copies = {s: [o for o in pr.leaves if linkgeo.link_target(o).Name == t.Name and o.Name != t.Name] for s, t in targets.items()}
    p.log("cowl copies (links):", {s: [o.Label for o in v] for s, v in copies.items()})
    box0 = {n: s.BoundBox for n, s in pr.shapes.items()}
    mine = {t.Name for t in targets.values()} | {o.Name for v in copies.values() for o in v}
    made, info = {}, {}
    for side, t in targets.items():
        S, O = t.Shape.copy(), orig[side]
        common = S.common(O).Volume
        p.check(common > 0.97 * O.Volume, f"{side}: the cowl overlays the original duct (less pockets and print chamfers, lite-70/71) ({common:.1f} of {O.Volume:.1f} mm3)")
        add = [s for s in S.cut(O).Solids if s.Volume > 1.0]
        rem0 = S.cut(O).Volume, O.cut(S).Volume
        pk = axes(S, POCKET_R)
        p.check(len(add) == 3, f"{side}: three solids proud of the original duct ({[round(s.Volume, 2) for s in add]})")
        p.check(len(pk) == 3, f"{side}: three insert pockets ({pk})")
        if p.errs: return p.finish([])
        keep = [s for s in add if any(near(s.BoundBox.Center, a) for a in pk)]
        stub = [s for s in add if not any(near(s.BoundBox.Center, a) for a in pk)]
        p.check(len(keep) == 2 and len(stub) == 1, f"{side}: two top stubs carry pockets, one stub doesn't ({len(keep)}, {len(stub)})")
        if p.errs: return p.finish([])
        st = stub[0]
        tops = [a for a in pk if any(near(s.BoundBox.Center, a) for s in keep)]
        # the stub's axis is its old screw tail's (its box centre is off-axis: the print face trims it at a slant)
        tail = [a for a in axes(S, TAIL_R) if st.common(Part.makeCylinder(TAIL_R + 0.5, 4000, V(-2000, *a), V(1, 0, 0))).Volume > 1.0]
        p.check(len(tail) == 1, f"{side}: the stub holds lite-23's dia {2 * TAIL_R} screw tail ({axes(S, TAIL_R)})")
        if p.errs: return p.finish([])
        c = V(0, *tail[0])
        d54 = sorted(math.hypot(c.y - a[0], c.z - a[1]) for a in tops)
        p.check(abs(math.dist(*tops) - 20.0) < 0.05 and any(abs(d - 54.0) < 0.1 for d in d54),
                f"{side}: the stub sits on lite-23's 20 x 54 screw square (tops {math.dist(*tops):.3f} apart; stub {[round(d, 3) for d in d54]} from them)")
        rb = [a for a in pk if a not in tops][0]
        gap = math.hypot(c.y - rb[0], c.z - rb[1]) - 4.0 - SPOT_R
        p.check(gap >= 0.5, f"{side}: the stub is {gap:.2f} mm clear of lite-68's rear-bottom spot-face")
        N = S.cut(st).removeSplitter()
        p.check(N.isValid() and len(N.Solids) == 1, f"{side}: one valid solid after the cut ({len(N.Solids)}, valid {N.isValid()})")
        p.check(abs(N.Volume - (S.Volume - st.Volume)) < 0.05, f"{side}: volume {S.Volume:.2f} - stub {st.Volume:.2f} = {N.Volume:.2f}")
        add1 = [s for s in N.cut(O).Solids if s.Volume > 1.0]
        p.check(len(add1) == 2 and abs(N.cut(O).Volume - (rem0[0] - st.Volume)) < 0.05,
                f"{side}: proud of the original now: the two top stubs only ({[round(s.Volume, 2) for s in add1]})")
        p.check(abs(O.cut(N).Volume - rem0[1]) < 0.05, f"{side}: cut into the original unchanged ({O.cut(N).Volume:.2f} vs {rem0[1]:.2f} mm3)")
        p.check(not axes(N, TAIL_R), f"{side}: no screw tail left ({axes(N, TAIL_R)})")
        made[side] = N
        info[side] = {"stub_mm3": round(st.Volume, 2), "stub_axis_yz": [round(c.y, 3), round(c.z, 3)],
                      "clear_of_rb_spot_mm": round(gap, 2), "volume": [round(S.Volume, 2), round(N.Volume, 2)]}
        p.log(f"{side}: {info[side]}")
    FreeCAD.closeDocument(od.Name)
    if p.errs: return p.finish([])
    gui = FreeCAD.GuiUp
    for side, t in targets.items():
        pl = FreeCAD.Placement(t.Placement)
        ap = list(t.ViewObject.ShapeAppearance) if gui and hasattr(t.ViewObject, "ShapeAppearance") else None
        s = made[side].copy(); s.transformShape(pl.inverse().toMatrix(), True, False); s.Placement = pl
        # t.Shape is the container-frame shape: the same placement, local geometry (lite68's to_local)
        t.Shape = s
        if ap is not None: t.ViewObject.ShapeAppearance = ap
        p.check(t.Placement.isSame(pl, 1e-9), f"{side}: the cowl keeps its placement")
    doc.recompute(); pr.refresh()
    for side, t in targets.items():
        p.check(abs(t.Shape.Volume - made[side].Volume) < 0.05 and t.Shape.isValid(), f"{side}: saved shape valid, {t.Shape.Volume:.2f} mm3")
        for o in copies[side]:
            p.check(abs(pr.shapes[o.Name].Volume - made[side].Volume) < 0.05, f"{side}: copy {o.Label} follows ({pr.shapes[o.Name].Volume:.2f})")
    moved = [doc.getObject(k).Label for k, b in box0.items() if k not in mine
             and (k not in pr.shapes or not pr.shapes[k].BoundBox.isInside(b) or not b.isInside(pr.shapes[k].BoundBox))]
    p.check(not moved, f"every other solid's box unchanged ({len(moved)}: {moved[:5]})")
    p.dump({"cowl": info, "src": os.path.basename(SRC)})
    return p.finish([(doc, DST)])


litelib.Pass("lite72_cowl_old_stub").run(main)
