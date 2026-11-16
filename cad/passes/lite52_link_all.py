# GUI pass: vt350-lite-51 -> vt350-lite-52   (headless = dry run, never saves)
# vt350#195, owner 2026-11-16: "the goal is to refine the CAD file so that working on it goes faster"; plan approved
# the same day. lite-51 linked the 22 biggest copies (file 125 -> 68.7 MB) but the GUI open barely moved: those parts
# were hidden or cheap. This pass links EVERY copy platform/freecad/dupes.py can fit, so the GUI tessellates each shape
# once for all its links. Measured on a scratch copy built the same way (2026-11-16, 3 alternating GUI opens):
# lite-51 median 69.3 s -> 45.9 s, file 65 -> 32 MiB.
# Left real: copies coloured unlike every other copy of their shape (groups split by colour: a link shows its
# master's colour; lite-51 has 32 such copies, which link within their colour), copies a fit would move by more than
# 1e-6 mm (dupes.landing: lite-51's zip ties, up to 3 um off), Fasteners-workbench screws (they rebuild themselves) and
# parts another feature uses (dupes.candidate).
# Each link keeps its copy's Name, Label, parent, Visibility and StandInFor, so the motion groups (built from Names),
# clash lists and the render export find it as before (all walk parts through platform/freecad/linkgeo.py).
# Checks (refuses to save on any): enough links to be the pass it claims (>= MIN_LINKS); every link within 1e-6 mm of
# its copy; (GUI) the same colour, transparency and visibility as its copy; every part keeps its global box; parts
# and meshes the same in number.
import FreeCAD, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, dupes, linkgeo
from litelib import MODELS
SRC, DST = f"{MODELS}/vt350-lite-51.FCStd", f"{MODELS}/vt350-lite-52.FCStd"
LAND_TOL = 1e-6                                     # mm: a link's global box vs its copy's
MIN_LINKS = 900                                     # the scratch build made 1,016 (before splitting by colour)
BOXES = ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")


def look(o):
    """What the GUI shows of o: its colours and transparency per face (or None headless / without them)."""
    vo = getattr(o, "ViewObject", None)
    if vo is None or not hasattr(vo, "ShapeAppearance"): return None
    return tuple(tuple(round(c, 3) for c in m.DiffuseColor[:3]) + (round(m.Transparency, 3),) for m in vo.ShapeAppearance)


def shown(o):
    vo = getattr(o, "ViewObject", None)
    return vo.Visibility if vo is not None else o.Visibility


def main(p):
    pr = p.open(SRC); doc = pr.doc
    sizes = dupes.object_bytes(SRC)
    groups = dupes.find(doc, sizes, split=look if FreeCAD.GuiUp else None)
    near = []
    for g in groups:
        off = [(n, d) for n, d in dupes.landing(g) if d > LAND_TOL]
        near += [(n, round(d, 5), g.master.Label[:40]) for n, d in off]
        g.drop([n for n, _ in off])
    groups = [g for g in groups if g.copies]
    n_copies = sum(len(g.copies) for g in groups)
    p.log(f"{len(groups)} groups, {n_copies} copies to link, saving {sum(g.saving for g in groups) / 1e6:.1f} MB; "
          f"kept real (a fit would move them): {len(near)} {sorted(near, reverse=True)[:12]}")
    if not p.check(n_copies >= MIN_LINKS, f"{n_copies} copies to link (>= {MIN_LINKS})"): return p.finish([])

    before = {o.Name: pr.shapes[o.Name].BoundBox for o in pr.leaves}
    n_leaves = len(pr.leaves)
    n_mesh = len([o for o in doc.Objects if linkgeo.is_mesh(o)])
    was = {o.Name: (look(o), shown(o)) for g in groups for o, _ in g.copies}
    rows, worst, n_links = [], 0.0, 0
    for g in groups:
        res = dupes.link_copies(doc, g)
        w = max(d for _, d in res); worst = max(worst, w); n_links += len(res)
        rows.append(dict(master=g.master.Name, label=g.master.Label, links=[n for n, _ in res],
                         saves_bytes=g.saving, worst_mm=w))
    p.check(worst < LAND_TOL, f"{n_links} links, every one within {LAND_TOL} mm of its copy (worst {worst:.2e})")
    doc.recompute(); pr.refresh()

    if FreeCAD.GuiUp:
        def seen(o):
            # A link's own ShapeAppearance is a default the GUI doesn't draw: it draws its target's unless the link
            # overrides (OverrideMaterial / OverrideMaterialList). The first GUI run read the link's and failed all 1,001.
            dvo = linkgeo.drawn_vo(o)
            if o.TypeId == "App::Link" and dvo is o.ViewObject: return ("overridden",)
            return look(dvo.Object if dvo is not None else o)
        bad_look = [n for n, (lk, _) in was.items() if seen(doc.getObject(n)) != lk]
        bad_vis = [n for n, (_, vis) in was.items() if shown(doc.getObject(n)) != vis]
        p.check(not bad_look, f"every link shows its copy's colour and transparency ({len(bad_look)} differ: {bad_look[:5]})")
        p.check(not bad_vis, f"every link shown or hidden as its copy was ({len(bad_vis)} differ: {bad_vis[:5]})")
    moved = [n for n, b in before.items() if n in pr.shapes and
             max(abs(getattr(b, k) - getattr(pr.shapes[n].BoundBox, k)) for k in BOXES) > LAND_TOL]
    lost = sorted(set(before) - set(pr.shapes))
    p.check(not moved and not lost, f"every part keeps its global box ({len(before)} parts; moved {moved[:5]}, missing {lost[:5]})")
    p.check(len(pr.leaves) == n_leaves, f"parts {n_leaves} -> {len(pr.leaves)} (unchanged: links count as parts)")
    n_mesh2 = len([o for o in doc.Objects if linkgeo.is_mesh(o)])
    p.check(n_mesh2 == n_mesh, f"meshes (and links to meshes) {n_mesh} -> {n_mesh2} (unchanged)")
    p.log(f"{n_links} links in {len(groups)} groups; "
          f"{len([o for o in doc.Objects if o.TypeId == 'App::Link'])} links in the document")
    p.dump({"groups": rows, "kept_real_near": near, "parts": [n_leaves, len(pr.leaves)], "meshes": [n_mesh, n_mesh2]})
    return p.finish([(doc, DST)])


litelib.Pass("lite52_link_all").run(main)
