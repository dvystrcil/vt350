# GUI pass: vt350-lite-76 -> vt350-lite-77   (headless = dry run, never saves)   vt350#291
# The print surface: the owner's PEI spring-steel sheet on the magnet sheet (owner, 2026-11-22, vt350#291: "We should
# add the plate now to our CAD"). Until now the model stopped at the magnet sheet, and every study took Z0 as the
# nozzle on the magnet sheet, "with a steel sheet, subtract its thickness".
#  - Thickness 1.0 mm: the owner's measurement (notes/kinematic-bed.md, the lite-18 stack table: "PEI spring-steel
#    print sheet | 1.0 | user; not modelled in lite-18").
#  - Footprint: ASSUMED the magnet sheet's outer square (355 x 355), without its holes (a spring-steel sheet has none).
#    The real sheet's size and any tab aren't measured yet.
#  - One plain box, `PEI spring-steel sheet (1.0 mm)`, in the magnet sheet's group, so it rides with the bed;
#    cad/studies/sweep_toolhead.py and z_sweep.py take its top as Z0 from this pass on.
# Checks (refuses to save on any): one magnet sheet and no sheet yet; the new sheet's bottom face on the magnet sheet's
# top, its top 1.0 above; its footprint the magnet sheet's; no overlap with any solid at the model pose; every other
# solid's box unchanged; one new leaf. Reported: the Mellow MultiHead Zero ball's height above the new surface.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-76.FCStd", f"{MODELS}/vt350-lite-77.FCStd"
MAGNET, SHEET = "Magnetic sheet", "PEI spring-steel sheet"
T = 1.0                                   # owner's measurement
LABEL = f"{SHEET} ({T:.1f} mm)"
BALL = "Mellow MultiHead Zero probe"


def to_local(o, g):
    """A global shape in o's own frame (o's container placements and o.Placement taken off); lite76's helper."""
    g = g.copy(); pl = g.Placement; g.Placement = FreeCAD.Placement(); g.transformShape(pl.toMatrix(), True, False)
    g.transformShape(linkgeo.gplace(o).inverse().toMatrix(), True, False)
    g.Placement = o.Placement
    return g


def main(p):
    m = p.open(SRC); doc = m.doc
    mags = [o for o in m.leaves if o.Label.startswith(MAGNET)]
    old = [o for o in m.leaves if o.Label.startswith(SHEET)]
    p.check(len(mags) == 1 and not old, f"one magnet sheet ({[o.Label for o in mags]}), no PEI sheet yet ({len(old)})")
    if p.errs: return p.finish([])
    mag = mags[0]; mb = m.shapes[mag.Name].BoundBox
    p.log(f"magnet sheet {mag.Label}: X {mb.XMin:.3f}..{mb.XMax:.3f} Y {mb.YMin:.3f}..{mb.YMax:.3f} top Z {mb.ZMax:.3f}")
    sheet = Part.makeBox(mb.XLength, mb.YLength, T, V(mb.XMin, mb.YMin, mb.ZMax))
    boxes0 = {n: s.BoundBox for n, s in m.shapes.items()}
    n0 = len(m.leaves)
    p.on_face(sheet, mb.ZMax, f"the sheet's bottom on the magnet sheet's top (Z {mb.ZMax:.3f}), its top {T} above",
              top=mb.ZMax + T)
    p.no_overlap([("sheet", sheet)], m, lambda r: f"the sheet overlaps nothing at the model pose ({r.hits[:5]})")
    # ---- write
    par = mag.getParentGeoFeatureGroup()
    f = doc.addObject("Part::Feature", "PEI_sheet")
    if par is not None: par.addObject(f)
    f.Label = LABEL
    f.Placement = FreeCAD.Placement()
    f.Shape = to_local(f, sheet)
    doc.recompute()
    if FreeCAD.GuiUp:
        try: f.ViewObject.ShapeAppearance[0].DiffuseColor = (0.72, 0.55, 0.25)   # textured PEI, gold-brown
        except Exception as e: p.log(f"  colour not set: {e}")
    m.refresh()
    # ---- after
    new = [o for o in m.leaves if o.Label == LABEL]
    p.check(len(new) == 1, f"one {LABEL} leaf ({len(new)})")
    if new:
        nb = m.shapes[new[0].Name].BoundBox
        d = max(abs(getattr(nb, k) - getattr(sheet.BoundBox, k)) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"))
        p.check(d < 1e-6 and abs(nb.XLength - mb.XLength) < 1e-6 and abs(nb.YLength - mb.YLength) < 1e-6,
                f"in place: the magnet sheet's footprint {nb.XLength:.2f} x {nb.YLength:.2f}, Z {nb.ZMin:.3f}..{nb.ZMax:.3f} "
                f"(off by {d:.2e})")
        p.check(par is None or new[0] in par.Group, f"in the magnet sheet's group ({par.Label if par else 'root'})")
    moved = [m.doc.getObject(n).Label for n, b in boxes0.items()
             if n not in m.shapes or not (m.shapes[n].BoundBox.isInside(b) and b.isInside(m.shapes[n].BoundBox))]
    p.check(not moved, f"every other solid's box unchanged ({len(moved)}: {moved[:5]})")
    p.check(len(m.leaves) == n0 + 1, f"leaves {n0} -> {len(m.leaves)} (+1)")
    ball = [o for o in m.leaves if o.Label.startswith(BALL)]
    out = {"sheet": {"label": LABEL, "thickness": T, "x": [mb.XMin, mb.XMax], "y": [mb.YMin, mb.YMax],
                     "z": [mb.ZMax, mb.ZMax + T]}}
    if ball:
        bb = m.shapes[ball[0].Name].BoundBox
        p.log(f"FINDING: the Mellow MultiHead Zero ball top Z {bb.ZMax:.2f} is {bb.ZMax - (mb.ZMax + T):.2f} above the new "
              f"print surface (was {bb.ZMax - mb.ZMax:.2f} above the magnet sheet)")
        out["mellow_ball_top_above_surface"] = round(bb.ZMax - (mb.ZMax + T), 3)
    p.dump(out)
    return p.finish([(doc, DST)])


if not os.environ.get("LITE77_AS_LIB"): litelib.Pass("lite77_pei_sheet").run(main)
