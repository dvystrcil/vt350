# GUI pass: vt350-lite-49 -> vt350-lite-50   (headless = dry run, never saves)
# vt350#195 AC3 (user, 2026-11-16: "I good with proceeding with standins and swaping when rendering is needed"): the next
# most expensive parts to tessellate get coarse-mesh stand-ins, as the springs got tubes in lite-49. Measured with 5
# copies of each in a test document, GUI open (platform/freecad/LESSONS.md):
#   bowden tube 13.0-13.5 s -> mesh 0.3-0.6 s, O2S toolboard 12.6-13.1 -> 0.9-1.0, Smart Sensor 8.0-9.4 -> 0.7,
#   heat block 5.4 -> 0.3, bearing (18 parts) 4.2-4.4 -> 0.3.
# A coarse mesh (Mesh::Feature, linear deflection 0.1 mm, angular 0.5 rad) is already triangles, so the GUI has nothing
# to tessellate, and it still looks like the part. Each real part gets its own: in the same App::Part, at the real
# part's placement, in its colour, with a StandInFor property naming it. The real part stays, hidden (a hidden part is
# not tessellated on open). The render export walks the real part and never the stand-in (colours.standin_skip).
# A Mesh::Feature isn't a Part::Feature, so the passes, clash checks and part index, which walk Part::Features, don't
# see the stand-ins at all.
# Checks (refuses to save on any): each family has exactly the expected parts (label and face count), each a plain
# Part::Feature directly in an App::Part that nothing is built from, one colour; each mesh's points lie on its part
# (within the deflection, sampled) and its box matches the part's tight box; in the document, each stand-in where it
# was built, its part hidden and unmoved; the Part::Feature solids unchanged.
import FreeCAD, Part, Mesh, MeshPart, os, sys, random
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
from litelib import MODELS, gshape, obb
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-49.FCStd", f"{MODELS}/vt350-lite-50.FCStd"
LIN, ANG = 0.1, 0.5                                 # mesh deflection: mm, rad
BOX_TOL = 0.15                                      # the mesh's box vs the part's tight box, a side
PT_TOL = LIN + 0.02                                 # a sampled mesh point's distance to its part
N_PTS = 60                                          # mesh points sampled per part
# family: (label prefix, faces per part, expected count)
FAMILIES = {"O2S toolboard": ("Orbitool O2S v3.3 toolboard", 11584, 5),
            "Smart Sensor": ("Orbiter Smart Sensor v4.2", 3146, 5),
            "bowden tube": ("Bowden ", 4, 5),
            "heat block": ("Heat Block", 128, 5),
            "MR bearing part": ("_MR", None, 90)}


def box_err(a, b):
    return max(abs(getattr(a, k) - getattr(b, k)) for k in ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax"))


def tight(s):
    """The shape's box, tightest of two: BoundBox follows a B-spline's control polygon (loose on the springs), and
    optimalBoundingBox overshoots on some B-spline faces (1.4 mm on the heat blocks' threaded ends). Both contain the
    shape, so their overlap does too."""
    a, b = s.BoundBox, obb(s)
    return FreeCAD.BoundBox(max(a.XMin, b.XMin), max(a.YMin, b.YMin), max(a.ZMin, b.ZMin),
                            min(a.XMax, b.XMax), min(a.YMax, b.YMax), min(a.ZMax, b.ZMax))


def faces_near(s):
    """[(enlarged box, face)] for a shape, so a point is measured only against faces that could be nearest it."""
    out = []
    for f in s.Faces:
        bb = FreeCAD.BoundBox(f.BoundBox); bb.enlarge(PT_TOL + 0.01); out.append((bb, f))
    return out


def dist(q, near):
    """A point's distance to the shape, within PT_TOL + 0.01; inf if no face is that close."""
    v = Part.Vertex(q)
    return min((f.distToShape(v)[0] for bb, f in near if bb.isInside(q)), default=float("inf"))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n_before = len(pr.leaves)
    n_mesh_before = len([o for o in doc.Objects if o.isDerivedFrom("Mesh::Feature")])
    picked = []
    for fam, (pre, nf, n) in FAMILIES.items():
        os_ = [o for o in pr.leaves if o.Label.startswith(pre) and (nf is None or len(o.Shape.Faces) == nf)]
        if p.check(len(os_) == n, f"{fam}: {n} parts (found {len(os_)})"): picked += [(fam, o) for o in os_]
    if p.errs: return p.finish([])
    rng = random.Random(50)
    rows, made = [], []
    for fam, o in picked:
        parent = o.getParentGeoFeatureGroup()
        users = [x.Name for x in o.InList if x is not parent]
        if not p.check(o.TypeId == "Part::Feature" and parent is not None and parent.TypeId == "App::Part" and not users
                       and not hasattr(o, "StandInFor"),
                       f"{o.Label}: a plain Part::Feature directly in an App::Part, nothing built from it, no stand-in yet "
                       f"({o.TypeId}, parent {parent and parent.TypeId}, users {users})"): continue
        if FreeCAD.GuiUp:
            n_col = len({tuple(round(c, 3) for c in m.DiffuseColor[:3]) for m in o.ViewObject.ShapeAppearance})
            if not p.check(n_col == 1, f"{o.Label}: one colour ({n_col})"): continue
        local = o.Shape.copy(); local.Placement = FreeCAD.Placement()
        near = faces_near(local)
        m = MeshPart.meshFromShape(Shape=local, LinearDeflection=LIN, AngularDeflection=ANG, Relative=False)
        mb = m.BoundBox; tb = tight(local)
        be = box_err(mb, tb)
        ok = p.check(m.CountFacets > 0 and be <= BOX_TOL, f"{o.Label}: mesh {m.CountFacets} facets, box within {be:.3f} <= {BOX_TOL}")
        pts = [V(*q) for q in rng.sample([tuple(x) for x in m.Topology[0]], min(N_PTS, m.CountPoints))]
        worst = max(dist(q, near) for q in pts)
        ok &= p.check(worst <= PT_TOL, f"{o.Label}: {len(pts)} mesh points on the part, worst {worst:.4f} <= {PT_TOL}")
        if not ok: continue
        rows.append(dict(family=fam, part=o.Name, label=o.Label, parent=parent.Label, faces=len(local.Faces),
                         facets=m.CountFacets, box_err=round(be, 4), worst=round(worst, 4)))
        made.append((o, parent, m))
    if len(made) != len(picked): return p.finish([])
    for fam in FAMILIES:
        r = [x for x in rows if x["family"] == fam]
        p.log(f"{fam}: {len(r)} stand-ins, {sum(x['facets'] for x in r)} facets in all, worst point {max(x['worst'] for x in r):.4f}, "
              f"worst box {max(x['box_err'] for x in r):.4f}")

    before = {o.Name: str(o.getGlobalPlacement()) for o, _, _ in made}
    objs = []
    for o, parent, m in made:
        st = doc.addObject("Mesh::Feature", "MeshStandIn")
        st.Mesh = m                                    # in the part's own frame; its placement is the part's
        st.Placement = o.Placement
        parent.addObject(st)
        st.Label = f"{o.Label} stand-in"
        st.addProperty("App::PropertyString", "StandInFor", "StandIn",
                       "Name of the hidden real part this mesh shows in the GUI (vt350#195); the render draws that part")
        st.StandInFor = o.Name
        o.Visibility = False
        if FreeCAD.GuiUp:
            st.ViewObject.ShapeAppearance = o.ViewObject.ShapeAppearance
            o.ViewObject.Visibility = False
        objs.append((st, o, m))
    doc.recompute(); pr.refresh()

    for st, o, m in objs:
        want = m.copy(); want.Placement = FreeCAD.Placement(); want.transform(o.getGlobalPlacement().toMatrix())
        got = st.Mesh.copy(); got.Placement = FreeCAD.Placement(); got.transform(st.getGlobalPlacement().toMatrix())
        p.check(box_err(got.BoundBox, want.BoundBox) < 1e-6 and box_err(got.BoundBox, tight(gshape(o))) <= BOX_TOL,
                f"{st.Label}: in the document where it was built, on its part")
        p.check(str(o.getGlobalPlacement()) == before[o.Name] and not o.Visibility, f"{o.Label}: unmoved and hidden")
        p.check(st.getParentGeoFeatureGroup() is o.getParentGeoFeatureGroup() and st.StandInFor == o.Name,
                f"{st.Label}: beside its part, StandInFor {st.StandInFor}")
    n_mesh = len([o for o in doc.Objects if o.isDerivedFrom("Mesh::Feature")])
    p.check(len(pr.leaves) == n_before and n_mesh == n_mesh_before + len(objs),
            f"Part::Feature solids {n_before} -> {len(pr.leaves)} (unchanged); meshes {n_mesh_before} -> {n_mesh} (+{len(objs)})")
    p.dump({"stand_ins": rows, "deflection": [LIN, ANG], "solids": [n_before, len(pr.leaves)], "meshes": [n_mesh_before, n_mesh]})
    return p.finish([(doc, DST)])


litelib.Pass("lite50_mesh_standins").run(main)
