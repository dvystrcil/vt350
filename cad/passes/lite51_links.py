# GUI pass: vt350-lite-50 -> vt350-lite-51   (headless = dry run, never saves)
# vt350#195 AC1 (file well under 100 MB) and AC3 (no duplicated shape over 1 MB). Owner, 2026-11-16: "targeted version
# first, but the goal is to refine the CAD file so that working on it goes faster".
# Every Part::Feature stores its whole shape, even a copy of another. The biggest copies become App::Links to one of
# them (platform/freecad/dupes.py): a link stores no shape and the GUI tessellates the target once for all its links.
#   SpeedClips      6, an STL turned into a solid (14,712 triangles), 5.2 MB each in the file
#   O2S toolboards  5, 3.5 MB each      Smart Sensors  5, 1.6 MB each
#   their lite-50 mesh stand-ins (5 + 5)
#   the MadMax carriage compound beside the SpeedClips: 2 of its 3 copies (the third is a reflection: it stays real)
# Measured on a scratch copy (2026-11-16): file 124 -> 67.7 MB, save 19.2 -> 9.5 s, headless open 9.7 -> 4.5 s; the
# part index of every one of the 1,395 parts identical (boxes, labels, paths, materials).
# A link keeps the copy's Name, Label, parent, Visibility and StandInFor, so motion groups, clash lists, the part index
# and the render export (all link-aware: platform/freecad/linkgeo.py) find it as before.
# Checks (refuses to save on any): each family has the parts it should and each fits its master by a rigid move (the
# one reflection stays a real part); each copy has its master's material and (GUI) colour, since a link shows its
# target's; each link lands where its copy was; every part in the model keeps its global box; leaves and meshes the
# same in number, the shapes stored fewer.
import FreeCAD, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, dupes, linkgeo
from litelib import MODELS
SRC, DST = f"{MODELS}/vt350-lite-50.FCStd", f"{MODELS}/vt350-lite-51.FCStd"
BOX_TOL = 1e-6                                       # mm: a link's global box vs its copy's
# family: (label prefix, Names (None: by label), parts, copies linked, the parts that stay real (not master, not linked))
FAMILIES = {"SpeedClip": ("SpeedClip 4mm Gap 9mm", None, 6, 5, ()),
            "O2S toolboard": ("Orbitool O2S v3.3 toolboard", None, 5, 4, ()),
            "Smart Sensor": ("Orbiter Smart Sensor v4.2", None, 5, 4, ()),
            # Part__Feature1507, under the mirrored dock, is mirrored and re-meshed (3,312 vertices vs 3,310):
            # nothing fits it, so it stays a real part (1.2 MB, a reflection, not a duplicate)
            "MadMax carriage compound": (None, ("Part__Feature448", "Part__Feature654", "Part__Feature1507"), 3, 1,
                                         ("Part__Feature1507",))}
# lite-50's mesh stand-ins for the boards and sensors: one mesh per real part, one group a family (meshes of one shape
# can differ by a point; dupes groups by volume and area within 1e-4). Every one but each group's master becomes a link.
STANDIN_OF = ("O2S toolboard", "Smart Sensor")


def box6(b):
    return (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)


def colours(o):
    return [tuple(round(c, 3) for c in m.DiffuseColor[:3]) for m in o.ViewObject.ShapeAppearance]


def main(p):
    pr = p.open(SRC); doc = pr.doc
    sizes = dupes.object_bytes(SRC)
    picked = {}
    for fam, (pre, names, n, _, _) in FAMILIES.items():
        os_ = ([doc.getObject(x) for x in names] if names else
               [o for o in pr.leaves if o.Label.startswith(pre) and o.TypeId == "Part::Feature"])
        if p.check(len(os_) == n and None not in os_, f"{fam}: {n} parts (found {len(os_)})"): picked[fam] = os_
    real = {o.Name for f in STANDIN_OF for o in picked.get(f, [])}
    standins = [o for o in doc.Objects if getattr(o, "StandInFor", "") in real and o.TypeId == "Mesh::Feature"]
    p.check(len(standins) == len(real), f"mesh stand-ins: one per board and sensor ({len(standins)} for {len(real)})")
    if p.errs: return p.finish([])

    groups = {}
    for fam, (_, _, n, n_link, stay) in FAMILIES.items():
        gs = [g for g in dupes.find(doc, sizes, {o.Name for o in picked[fam]}) if g.copies]
        copies = sum(len(g.copies) for g in gs)
        linked = {o.Name for g in gs for o, _ in g.copies} | {g.master.Name for g in gs}
        real = sorted({o.Name for o in picked[fam]} - linked)
        if p.check(len(gs) == 1 and copies == n_link and tuple(real) == stay,
                   f"{fam}: one group, {copies} copies fit by a rigid move (want {n_link}), staying real {real} "
                   f"(want {list(stay)})"):
            groups[fam] = gs[0]
    sg = [g for g in dupes.find(doc, sizes, {o.Name for o in standins}) if g.copies]
    p.check(len(sg) == len(STANDIN_OF) and sum(len(g.copies) for g in sg) == len(standins) - len(STANDIN_OF),
            f"stand-ins: {len(sg)} groups (one a family), {sum(len(g.copies) for g in sg)} copies of {len(standins)}")
    for i, g in enumerate(sg): groups[f"stand-ins {i + 1}"] = g
    if p.errs: return p.finish([])

    for fam, g in groups.items():
        m = g.master
        for o, _ in g.copies:
            mat = lambda x: getattr(getattr(x, "ShapeMaterial", None), "Name", "")
            p.check(mat(o) == mat(m), f"{o.Label}: material {mat(o)!r} = its master's {mat(m)!r}")
            if FreeCAD.GuiUp:
                p.check(colours(o) == colours(m), f"{o.Label}: colour = its master's (a link shows its target's)")
    if p.errs: return p.finish([])

    before = {o.Name: box6(pr.shapes[o.Name].BoundBox) for o in pr.leaves}
    n_leaves = len(pr.leaves)
    n_mesh = len([o for o in doc.Objects if linkgeo.is_mesh(o)])
    rows = []
    for fam, g in groups.items():
        res = dupes.link_copies(doc, g)
        for name, d in res:
            p.check(d < BOX_TOL, f"{fam}: {name} -> link to {g.master.Name}, lands {d:.2e} mm from the copy")
        rows.append(dict(family=fam, master=g.master.Name, links=[n for n, _ in res], saves_bytes=g.saving,
                         worst_mm=max(d for _, d in res)))
        p.log(f"{fam}: {len(res)} links to {g.master.Label} [{g.master.Name}], saves {g.saving / 1e6:.2f} MB")
    doc.recompute(); pr.refresh()

    moved = [n for n in before if n in pr.shapes and max(abs(a - b) for a, b in zip(before[n], box6(pr.shapes[n].BoundBox))) > BOX_TOL]
    lost = sorted(set(before) - set(pr.shapes))
    p.check(not moved and not lost, f"every part keeps its global box ({len(before)} parts; moved {moved[:5]}, missing {lost[:5]})")
    p.check(len(pr.leaves) == n_leaves, f"parts {n_leaves} -> {len(pr.leaves)} (unchanged: links count as parts)")
    n_mesh2 = len([o for o in doc.Objects if linkgeo.is_mesh(o)])
    p.check(n_mesh2 == n_mesh, f"meshes (and links to meshes) {n_mesh} -> {n_mesh2} (unchanged)")
    n_links = len([o for o in doc.Objects if o.TypeId == "App::Link"])
    total = sum(len(r["links"]) for r in rows)
    p.log(f"{total} links ({n_links} in the document); the copies stored {sum(r['saves_bytes'] for r in rows) / 1e6:.1f} MB")
    p.dump({"links": rows, "parts": [n_leaves, len(pr.leaves)], "meshes": [n_mesh, n_mesh2]})
    return p.finish([(doc, DST)])


litelib.Pass("lite51_links").run(main)
