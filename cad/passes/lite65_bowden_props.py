# GUI pass: vt350-lite-64 -> vt350-lite-65   (headless = dry run, never saves)   vt350#174
# The bowden tubes' stored route was 10.70 mm off in X. Since vt350#195 the five tubes are one Part::Feature,
# "Bowden Left", holding the route (Inlet, ExitPoint, ExitDir, HandleInlet, HandleExit) and four App::Links to it, so
# one fix covers all five. lite-31 made the slot copies by translating Bowden Left and kept its props, which were
# already stale: Inlet.x and ExitPoint.x say -399.00, while the solid lies in the plane X -409.70 (lite36_roof_exit.py
# and o2s_route.py measured around it). This sets both X values to the solid's section centre at Z 600. No geometry.
# The material cards are registered before the model opens (else every part reopens as Default; LESSONS.md).
# Checks (refuses to save on any):
#  - five tubes, one target, which has the route props; the solid is in one plane X = const (sections at five Z);
#  - afterwards, each tube's route (the target's props moved by the link's placement) runs within TOL of its
#    solid's section centre at Z 530/560/600/650/680 (cad/studies/test_bowden_props_fc.py, the same check);
#  - only X changed: Y, Z, ExitDir and the handles as before;
#  - every solid's box, the solid count and every part's material unchanged.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo, matlib, bezier
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-64.FCStd", f"{MODELS}/vt350-lite-65.FCStd"
CARDS = os.path.join(_REPO, "cad/materials")
ZS = (530.0, 560.0, 600.0, 650.0, 680.0)
TOL = 0.1
PROPS = ("Inlet", "ExitPoint", "ExitDir", "HandleInlet", "HandleExit")


def route(o):
    """o's stored route as a global Part.BezierCurve: its link target's props, moved as o is moved relative to it."""
    t = linkgeo.link_target(o)
    poles = bezier.tube_poles(tuple(V(t.Inlet)), tuple(V(t.ExitPoint)), tuple(V(t.ExitDir)),
                              t.HandleInlet.Value, t.HandleExit.Value)
    rel = linkgeo.gplace(o).multiply(linkgeo.gplace(t).inverse())
    c = Part.BezierCurve(); c.setPoles([rel.multVec(V(*q)) for q in poles])
    return c


def worst(tubes):
    """The largest distance from a tube's route to its section centre, over every tube and height."""
    w = (0.0, "")
    for o in tubes:
        s, c = linkgeo.gshape(o), route(o).toShape()
        for z in ZS:
            sec = s.slice(V(0, 0, 1), z)
            if len(sec) != 1: return (float("inf"), f"{o.Label} at Z {z}: {len(sec)} loops")
            d = c.distToShape(Part.Vertex(Part.Face(sec[0]).CenterOfMass))[0]
            if d > w[0]: w = (d, f"{o.Label} at Z {z}")
    return w


def main(p):
    matlib.use_dir(CARDS)
    pr = p.open(SRC); doc = pr.doc
    tubes = [o for o in pr.leaves if o.Label.startswith("Bowden ")]
    targets = {linkgeo.link_target(o).Name for o in tubes}
    p.check(len(tubes) == 5 and len(targets) == 1, f"five tubes, one target ({len(tubes)}, {sorted(targets)})")
    if p.errs: return p.finish([])
    t = doc.getObject(targets.pop())
    p.check(t.TypeId == "Part::Feature" and all(hasattr(t, k) for k in PROPS), f"{t.Label} holds the route props")
    s = linkgeo.gshape(t)
    xs = [Part.Face(s.slice(V(0, 0, 1), z)[0]).CenterOfMass.x for z in ZS]
    p.check(max(xs) - min(xs) < 0.01, f"{t.Label} lies in one plane X = const: {min(xs):.3f}..{max(xs):.3f}")
    if p.errs: return p.finish([])
    x = xs[ZS.index(600.0)]
    w0 = worst(tubes)
    p.log(f"before: {t.Label} Inlet.x {t.Inlet.x:.2f}, ExitPoint.x {t.ExitPoint.x:.2f}; solid X {x:.3f}; "
          f"worst route-to-centre {w0[0]:.2f} mm ({w0[1]})")
    before = {k: getattr(t, k) for k in PROPS}
    box0 = {n: sh.BoundBox for n, sh in pr.shapes.items()}
    mat0 = {o.Name: getattr(getattr(linkgeo.link_target(o), "ShapeMaterial", None), "Name", "") for o in pr.leaves}
    n0 = len(pr.leaves)
    t.Inlet = V(x, t.Inlet.y, t.Inlet.z)
    t.ExitPoint = V(x, t.ExitPoint.y, t.ExitPoint.z)
    doc.recompute(); pr.refresh()
    w1 = worst(tubes)
    p.check(w1[0] < TOL, f"after: each tube's route within {TOL} mm of its section centres (worst {w1[0]:.3f} mm, {w1[1]})")
    same = (abs(t.Inlet.y - before["Inlet"].y) < 1e-9 and abs(t.Inlet.z - before["Inlet"].z) < 1e-9
            and abs(t.ExitPoint.y - before["ExitPoint"].y) < 1e-9 and abs(t.ExitPoint.z - before["ExitPoint"].z) < 1e-9
            and (V(t.ExitDir) - V(before["ExitDir"])).Length < 1e-12
            and t.HandleInlet.Value == before["HandleInlet"].Value and t.HandleExit.Value == before["HandleExit"].Value)
    p.check(same, "only X changed (Inlet/ExitPoint Y and Z, ExitDir, the handles as before)")
    moved = [doc.getObject(n).Label for n, b in box0.items()
             if n not in pr.shapes or not pr.shapes[n].BoundBox.isInside(b) or not b.isInside(pr.shapes[n].BoundBox)]
    p.check(not moved and len(pr.leaves) == n0, f"every solid's box and the count unchanged ({len(moved)}: {moved[:5]})")
    mat1 = {o.Name: getattr(getattr(linkgeo.link_target(o), "ShapeMaterial", None), "Name", "") for o in pr.leaves}
    changed = [doc.getObject(n).Label for n in mat0 if mat0[n] != mat1.get(n)]
    p.check(not changed, f"every part's material unchanged ({len(changed)}: {changed[:5]})")
    p.dump({"target": t.Label, "x_was": round(before["Inlet"].x, 3), "x_now": round(x, 3),
            "worst_before_mm": round(w0[0], 3), "worst_after_mm": round(w1[0], 3)})
    return p.finish([(doc, DST)])


litelib.Pass("lite65_bowden_props").run(main)
