# GUI pass: vt350-lite-54 + vt350-emu.FCStd -> vt350-lite-55 + vt350-emu-2.FCStd   (headless = dry run, never saves)
# vt350#187. The EMU (DW-Tas, CC BY-NC-SA 4.0; 5 lanes: a left end, three extenders and a right end, as its CAD
# builds them) goes on the printer's roof (owner, 2026-11-16: "when can we see an EMU up top? and then link 4 more to
# it"; "doors facing front is fine, go ahead").
#  - vt350-emu-2.FCStd (from vt350-emu.FCStd, which stays as it is): the whole EMU moved, not turned (its lids,
#    latches and buttons are already at its -Y end, the printer's front; its PTFE exits at the rear, toward the roof's
#    bowden exits at Y 444..498). Centred on the roof in X, its front 5 mm in from the roof's front edge, its feet on
#    the roof felt's top.
#  - Copies linked as lite-52 linked the printer's (platform/freecad/dupes.py): lane 1 stays real, every part the
#    other lanes repeat becomes an App::Link to it. The end lanes are not copies of the extenders (their bases and
#    end walls differ), so the parts they share link and the rest stay real.
#  - lite-55: an "EMU envelope (contents in vt350-emu-2.FCStd)" box, as for the e-box (renders skip it when the EMU
#    file is merged in).
# Checks (refuses to save on any): every EMU part moved by exactly the translation asked; enough links; every link
# within 1e-6 mm of its copy; (GUI) colour, transparency and visibility kept; part and mesh counts unchanged; no EMU
# part overlaps a lite-54 part; lite-55 = lite-54 + 1 solid.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, dupes, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-54.FCStd", f"{MODELS}/vt350-lite-55.FCStd"
EMU, EMU2 = f"{MODELS}/vt350-emu.FCStd", f"{MODELS}/vt350-emu-2.FCStd"
ROOT = "EMU 5-lane (DW-Tas)"
ROOF = "Roof panel (3 mm) paint, outside"     # X -520..30, Y -90..520
FELT = "Roof felt liner, outer"               # top of the roof felt, Z 704
FRONT_IN = 5.0                                # the EMU's front, in from the roof's front edge
LAND_TOL, MIN_LINKS = 1e-6, 500
BOXES = ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")


def look(o):
    vo = getattr(o, "ViewObject", None)
    if vo is None or not hasattr(vo, "ShapeAppearance"): return None
    return tuple(tuple(round(c, 3) for c in m.DiffuseColor[:3]) + (round(m.Transparency, 3),) for m in vo.ShapeAppearance)


def shown(o):
    vo = getattr(o, "ViewObject", None)
    return vo.Visibility if vo is not None else o.Visibility


def union(model, objs):
    bb = FreeCAD.BoundBox()
    for o in objs: bb.add(model.shapes[o.Name].BoundBox)
    return bb


def main(p):
    pr = p.open(SRC); doc = pr.doc
    roof, felt = pr.leaf(ROOF), pr.leaf(FELT)
    rb, fz = pr.shapes[roof.Name].BoundBox, pr.shapes[felt.Name].BoundBox.ZMax
    em = p.open(EMU); ed = em.doc
    root = em.root(ROOT)
    bb0 = union(em, em.leaves)
    d = V((rb.XMin + rb.XMax) / 2 - (bb0.XMin + bb0.XMax) / 2, rb.YMin + FRONT_IN - bb0.YMin, fz - bb0.ZMin)
    p.log(f"EMU {bb0.XLength:.1f} x {bb0.YLength:.1f} x {bb0.ZLength:.1f}; roof X {rb.XMin:.1f}..{rb.XMax:.1f} "
          f"Y {rb.YMin:.1f}..{rb.YMax:.1f}, felt top Z {fz:.2f}; move {d}")
    before = {o.Name: em.shapes[o.Name].BoundBox for o in em.leaves}
    root.Placement = FreeCAD.Placement(d, FreeCAD.Rotation()).multiply(root.Placement)
    ed.recompute(); em.refresh()
    off = [n for n, b in before.items() if max(abs(getattr(em.shapes[n].BoundBox, k) - getattr(b, k) -
                                                   (d.x if k[0] == "X" else d.y if k[0] == "Y" else d.z)) for k in BOXES) > 1e-6]
    p.check(not off and len(em.leaves) == len(before), f"every EMU part ({len(before)}) moved by {d} ({len(off)} off: {off[:5]})")
    # links (as lite-52)
    groups = dupes.find(ed, dupes.object_bytes(EMU), split=look if FreeCAD.GuiUp else None)
    near = []
    for g in groups:
        o_ = [(n, dd) for n, dd in dupes.landing(g) if dd > LAND_TOL]
        near += [(n, round(dd, 5)) for n, dd in o_]; g.drop([n for n, _ in o_])
    groups = [g for g in groups if g.copies]
    n_copies = sum(len(g.copies) for g in groups)
    p.log(f"{len(groups)} groups, {n_copies} copies to link, saving {sum(g.saving for g in groups) / 1e6:.1f} MB; "
          f"kept real (a fit would move them): {len(near)}")
    p.check(n_copies >= MIN_LINKS, f"{n_copies} copies to link (>= {MIN_LINKS})")
    moved_box = {o.Name: em.shapes[o.Name].BoundBox for o in em.leaves}
    n_leaves, n_mesh = len(em.leaves), len([o for o in ed.Objects if linkgeo.is_mesh(o)])
    was = {o.Name: (look(o), shown(o)) for g in groups for o, _ in g.copies}
    worst, n_links = 0.0, 0
    for g in groups:
        res = dupes.link_copies(ed, g)
        worst = max([worst] + [x for _, x in res]); n_links += len(res)
    p.check(worst < LAND_TOL, f"{n_links} links, every one within {LAND_TOL} mm of its copy (worst {worst:.2e})")
    ed.recompute(); em.refresh()
    if FreeCAD.GuiUp:
        def seen(o):
            dvo = linkgeo.drawn_vo(o)
            if o.TypeId == "App::Link" and dvo is o.ViewObject: return ("overridden",)
            return look(dvo.Object if dvo is not None else o)
        bad_look = [n for n, (lk, _) in was.items() if seen(ed.getObject(n)) != lk]
        bad_vis = [n for n, (_, vis) in was.items() if shown(ed.getObject(n)) != vis]
        p.check(not bad_look, f"every link shows its copy's colour and transparency ({len(bad_look)} differ: {bad_look[:5]})")
        p.check(not bad_vis, f"every link shown or hidden as its copy was ({len(bad_vis)} differ: {bad_vis[:5]})")
    moved = [n for n, b in moved_box.items() if n in em.shapes and
             max(abs(getattr(b, k) - getattr(em.shapes[n].BoundBox, k)) for k in BOXES) > LAND_TOL]
    p.check(not moved and len(em.leaves) == n_leaves, f"links keep every part's box ({n_leaves} -> {len(em.leaves)} parts; moved {moved[:5]})")
    p.check(len([o for o in ed.Objects if linkgeo.is_mesh(o)]) == n_mesh, f"meshes {n_mesh} (unchanged)")
    # the printer: clash check, envelope
    bb = union(em, em.leaves)
    items = [(o.Label, em.shapes[o.Name]) for o in em.leaves]
    p.no_overlap(items, pr, lambda r: f"no EMU part overlaps a lite-54 part: {len(r.hits)} {r.hits[:10]}")
    n0 = len(pr.leaves)
    proot = pr.root("4040-350x350x250 Voron Trident")
    box = Part.makeBox(bb.XLength, bb.YLength, bb.ZLength, V(bb.XMin, bb.YMin, bb.ZMin))
    n = doc.addObject("Part::Feature", "EmuEnvelope"); proot.addObject(n)
    loc = box.copy(); loc.Placement = linkgeo.gplace(proot).inverse().multiply(loc.Placement); n.Shape = loc
    n.Label = "EMU envelope (contents in vt350-emu-2.FCStd)"
    if FreeCAD.GuiUp: n.ViewObject.ShapeColor = (0.3, 0.5, 0.8); n.ViewObject.Transparency = 80
    doc.recompute(); pr.refresh()
    eb = pr.shapes[n.Name].BoundBox
    p.check(max(abs(getattr(eb, k) - getattr(bb, k)) for k in BOXES) < 1e-6,
            f"envelope X {eb.XMin:.1f}..{eb.XMax:.1f} Y {eb.YMin:.1f}..{eb.YMax:.1f} Z {eb.ZMin:.1f}..{eb.ZMax:.1f}")
    p.check(len(pr.leaves) == n0 + 1, f"lite-55 solids: {len(pr.leaves)} (lite-54 + 1 = {n0 + 1})")
    p.dump({"move": [d.x, d.y, d.z], "emu_parts": n_leaves, "links": n_links, "kept_real_near": near,
            "envelope": [bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax]})
    return p.finish([(ed, EMU2), (doc, DST)])


litelib.Pass("lite55_emu_roof").run(main)
