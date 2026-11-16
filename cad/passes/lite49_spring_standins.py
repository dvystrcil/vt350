# GUI pass: vt350-lite-48 -> vt350-lite-49   (headless = dry run, never saves)
# vt350#195 AC3 (user, 2026-11-16: "go with stand-ins for the springs next"): the 5 extruder tensioner springs
# ("Spring v1", one in each toolhead's Orbiter) cost 19 s of the GUI's 131 s of tessellation, though they are 0.1 MB
# each: one helical B-spline surface (94 x 11 poles), ~144k triangles apiece. Each gets a stand-in: a plain tube that
# holds the coil (its axis, inner and outer radius and length fitted from points on the spring, platform/freecad/
# standins.py), in the same App::Part, at the same placement, in the same colour and material, with a StandInFor
# property naming the real spring. The real spring stays, hidden: the GUI does not tessellate a hidden object when it
# opens a file (measured 2026-11-16, 5 springs: open 14.4 s visible, 0.2 s hidden; a visible spring under a hidden
# App::Part still costs 15 s, so hiding a parent saves nothing). The render export draws the real spring and leaves out
# the stand-in (colours.standin_skip; RENDER_STANDINS=1 swaps them for a quick preview).
# Checks (refuses to save on any): exactly 5 springs, each a plain Part::Feature (one B-spline face and two end planes)
# that nothing is built from, directly in an App::Part; the fit is a coil (the radial spread is the wire's diameter);
# each stand-in one valid solid that holds every sampled point of its spring and whose box holds the spring's box,
# at most 0.3 mm bigger a side; in the document, each stand-in where it was built and its spring hidden and unmoved;
# 5 more solids than lite-48 and nothing else changed.
import FreeCAD, Part, os, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
import standins
from litelib import MODELS, gshape, obb
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-48.FCStd", f"{MODELS}/vt350-lite-49.FCStd"
N_SPRINGS = 5
LABEL = "Spring v1"
BOX_SLACK = 0.3                                    # the tube's box may exceed the spring's by this much a side


def sample(s, nu=24, nv=480):
    """Points on a spring in its own frame: a grid on its B-spline face (untrimmed, so the grid is all on the wire)
    and points along every edge (the cut wire ends). Not a grid on the end planes: a plane's parameter range is the
    rectangle round its trimmed face, and points off the wire would widen the fit."""
    pts = [q for e in s.Edges for q in e.discretize(48)]
    for f in s.Faces:
        if f.Surface.__class__.__name__ != "BSplineSurface": continue
        u0, u1, v0, v1 = f.ParameterRange
        for i in range(nu + 1):
            for j in range(nv + 1):
                pts.append(f.valueAt(u0 + (u1 - u0) * i / nu, v0 + (v1 - v0) * j / nv))
    return pts


def tube(fit):
    ax = fit["axis"]; o = [k for k in range(3) if k != ax]
    base = [0.0, 0.0, 0.0]; base[ax] = fit["lo"]; base[o[0]], base[o[1]] = fit["centre"]
    d = [0.0, 0.0, 0.0]; d[ax] = 1.0
    h = fit["hi"] - fit["lo"]
    return Part.makeCylinder(fit["rmax"], h, V(*base), V(*d)).cut(Part.makeCylinder(fit["rmin"], h, V(*base), V(*d)))


def holds(outer, inner, tol=1e-3):
    return all(getattr(outer, a + "Min") <= getattr(inner, a + "Min") + tol and getattr(outer, a + "Max") >= getattr(inner, a + "Max") - tol
               for a in "XYZ")


def slack(outer, inner):
    return max(max(getattr(inner, a + "Min") - getattr(outer, a + "Min"), getattr(outer, a + "Max") - getattr(inner, a + "Max"))
               for a in "XYZ")


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n_before = len(pr.leaves)
    springs = [o for o in pr.leaves if o.Label.startswith(LABEL)]
    if not p.check(len(springs) == N_SPRINGS, f"{N_SPRINGS} '{LABEL}' parts (found {len(springs)})"): return p.finish([])
    rows, made = [], []
    for o in springs:
        s = o.Shape
        kinds = sorted(f.Surface.__class__.__name__ for f in s.Faces)
        parent = o.getParentGeoFeatureGroup()
        users = [x.Name for x in o.InList if x is not parent]
        ok = p.check(o.TypeId == "Part::Feature" and kinds == ["BSplineSurface", "Plane", "Plane"] and len(s.Solids) == 1,
                     f"{o.Label}: a plain Part::Feature, one B-spline face and two end planes ({o.TypeId}, {kinds})")
        ok &= p.check(parent is not None and parent.TypeId == "App::Part" and not users,
                      f"{o.Label}: directly in an App::Part, nothing built from it (parent {parent and parent.Label}, users {users})")
        if not ok: continue
        local = s.copy(); local.Placement = FreeCAD.Placement()
        pts = sample(local)
        fit = standins.fit_coil([(q.x, q.y, q.z) for q in pts])
        wire = 4 * local.Volume / local.Area                     # a round wire: V / A = d / 4
        ok = p.check(abs(fit["spread"] - wire) < 0.15 * wire,
                     f"{o.Label}: a coil (radial spread {fit['spread']:.3f} vs wire {wire:.3f})")
        t = tube(fit)
        ok &= p.check(t.isValid() and len(t.Solids) == 1, f"{o.Label}: the stand-in is one valid solid")
        if not ok: continue
        out = [q for q in pts[::7] if not t.isInside(q, 1e-3, True)]
        ok &= p.check(not out, f"{o.Label}: the stand-in holds every sampled point ({len(pts[::7])}, outside {len(out)})")
        tight = obb(local)                               # BoundBox is loose on a B-spline (its control polygon)
        sl = slack(t.BoundBox, tight)
        ok &= p.check(holds(t.BoundBox, tight) and sl <= BOX_SLACK,
                      f"{o.Label}: the stand-in's box holds the spring's, slack {sl:.3f} <= {BOX_SLACK}")
        if not ok: continue
        p.log(f"{o.Label} ({o.Name}) in {parent.Label}: axis {'XYZ'[fit['axis']]}, OD {2 * fit['rmax']:.3f} ID {2 * fit['rmin']:.3f} "
              f"length {fit['hi'] - fit['lo']:.3f}, wire {wire:.3f}; stand-in {len(t.Faces)} faces, slack {sl:.3f}")
        rows.append(dict(spring=o.Name, label=o.Label, parent=parent.Label, axis="XYZ"[fit["axis"]],
                         od=round(2 * fit["rmax"], 3), id=round(2 * fit["rmin"], 3), length=round(fit["hi"] - fit["lo"], 3),
                         wire=round(wire, 3), slack=round(sl, 3), points=len(pts)))
        made.append((o, parent, t))
    if len(made) != N_SPRINGS: return p.finish([])

    before = {o.Name: (str(o.getGlobalPlacement()), pr.shapes[o.Name].BoundBox) for o in springs}
    objs = []
    for o, parent, t in made:
        st = doc.addObject("Part::Feature", "SpringStandIn")
        st.Shape = t                                   # in the spring's own frame; its placement is the spring's
        st.Placement = o.Placement
        parent.addObject(st)
        st.Label = f"{o.Label} stand-in"
        st.addProperty("App::PropertyString", "StandInFor", "StandIn",
                       "Name of the hidden real part this shape shows in the GUI (vt350#195); the render draws that part")
        st.StandInFor = o.Name
        if hasattr(o, "ShapeMaterial") and hasattr(st, "ShapeMaterial"): st.ShapeMaterial = o.ShapeMaterial
        o.Visibility = False
        if FreeCAD.GuiUp:
            st.ViewObject.ShapeAppearance = o.ViewObject.ShapeAppearance
            o.ViewObject.Visibility = False
        objs.append((st, o, t))
    doc.recompute(); pr.refresh()

    for st, o, t in objs:
        want = t.copy(); want.Placement = o.getGlobalPlacement()
        got = gshape(st).BoundBox; real = obb(gshape(o))
        p.check(max(abs(getattr(got, a) - getattr(want.BoundBox, a)) for a in ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")) < 1e-6,
                f"{st.Label}: in the document where it was built")
        p.check(holds(got, real) and slack(got, real) <= BOX_SLACK, f"{st.Label}: holds its spring in the document")
        p.check(str(o.getGlobalPlacement()) == before[o.Name][0] and not o.Visibility, f"{o.Label}: unmoved and hidden")
        p.check(st.getParentGeoFeatureGroup() is o.getParentGeoFeatureGroup() and st.StandInFor == o.Name,
                f"{st.Label}: beside its spring, StandInFor {st.StandInFor}")
    p.check(len(pr.leaves) == n_before + N_SPRINGS, f"solids {n_before} -> {len(pr.leaves)} (+{N_SPRINGS})")
    p.dump({"springs": rows, "solids": [n_before, len(pr.leaves)]})
    return p.finish([(doc, DST)])


litelib.Pass("lite49_spring_standins").run(main)
