# GUI pass: vt350-lite-78 -> vt350-lite-79   (headless = dry run, never saves)   colour only
# The camera housing and the Mellow MultiHead Zero's bracket go from the printed white to the accent orange (owner,
# 2026-11-24: "the holder of the camera and the mellow are white and I want them orange"). The accent is the one the
# skirt grilles, corners and cable channel cover use: PET-GF orange, #E2662A (cad/render/colours.json "accent").
#  - Camera housing: `Camera housing (front|back)` (lite-16, moved by lite-39). The camera's frame bracket isn't
#    modelled, so the housing is what holds it.
#  - Mellow: `Nozzle offset probe bracket (low, lite-78)`. The Zero itself stays aluminium, steel and black.
# Renders take their colour from cad/render/colours.json by label, changed in the same branch; this pass makes the
# FreeCAD file match.
# Checks (refuses to save on any): exactly the expected parts, each a real Part::Feature (not a link, which would
# show its target's colour); no geometry, placement or leaf count changes; in a GUI run, every face of each part is the
# accent afterwards. Headless runs (no ViewObject) check everything but the colour.
import FreeCAD, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
from litelib import MODELS
SRC, DST = f"{MODELS}/vt350-lite-78.FCStd", f"{MODELS}/vt350-lite-79.FCStd"
ACCENT_HEX = "#E2662A"
ACCENT = tuple(int(ACCENT_HEX[i:i + 2], 16) / 255 for i in (1, 3, 5))
TARGETS = (("Camera housing front", 1), ("Camera housing back", 1), ("Nozzle offset probe bracket ", 1))
TOL = 1e-3


def faces_colours(o):
    """The diffuse colours a part's view shows, one per ShapeAppearance entry (GUI only)."""
    return [tuple(round(c, 3) for c in m.DiffuseColor[:3]) for m in o.ViewObject.ShapeAppearance]


def set_colour(o):
    """Every face of o in the accent: one material for the whole shape (lite-77's ShapeAppearance route)."""
    vo = o.ViewObject
    mats = list(vo.ShapeAppearance)
    m0 = mats[0]
    m0.DiffuseColor = ACCENT + (0.0,) if len(m0.DiffuseColor) == 4 else ACCENT
    vo.ShapeAppearance = (m0,)


def main(p):
    m = p.open(SRC); doc = m.doc
    parts = []
    for prefix, n in TARGETS:
        found = [o for o in m.leaves if o.Label.startswith(prefix)]
        p.check(len(found) == n, f"{n} part(s) labelled '{prefix}...' ({[o.Label for o in found]})")
        parts += found
    for o in parts:
        p.check(o.TypeId == "Part::Feature", f"{o.Label} is a Part::Feature, not a link ({o.TypeId})")
    if p.errs: return p.finish([])
    for o in parts:
        p.log(f"part: {o.Label} ({o.Name}), {len(m.shapes[o.Name].Faces)} faces")
    boxes0 = {n: s.BoundBox for n, s in m.shapes.items()}
    vols0 = {o.Name: m.shapes[o.Name].Volume for o in parts}
    place0 = {o.Name: o.Placement.copy() for o in parts}
    n0 = len(m.leaves)
    # ---- write
    if FreeCAD.GuiUp:
        for o in parts:
            before = sorted(set(faces_colours(o)))
            set_colour(o)
            p.log(f"  {o.Label}: {before[:3]} -> {sorted(set(faces_colours(o)))}")
    else:
        p.log("headless: no ViewObject, colours not set (dry run checks the parts and the model only)")
    doc.recompute()
    m.refresh()
    # ---- after
    moved = [doc.getObject(n).Label for n, b in boxes0.items()
             if n not in m.shapes or not (m.shapes[n].BoundBox.isInside(b) and b.isInside(m.shapes[n].BoundBox))]
    p.check(not moved, f"every solid's box unchanged ({len(moved)}: {moved[:5]})")
    p.check(len(m.leaves) == n0, f"leaves {n0} -> {len(m.leaves)} (unchanged)")
    for o in parts:
        p.check(abs(m.shapes[o.Name].Volume - vols0[o.Name]) < TOL and o.Placement.isSame(place0[o.Name], TOL),
                f"{o.Label}: same volume and placement")
        if FreeCAD.GuiUp:
            cols = set(faces_colours(o))
            want = tuple(round(c, 3) for c in ACCENT)
            p.check(cols == {want}, f"{o.Label}: every face the accent {ACCENT_HEX} ({sorted(cols)[:3]})")
    p.dump({"accent": ACCENT_HEX, "parts": [o.Label for o in parts]})
    return p.finish([(doc, DST)])


if not os.environ.get("LITE79_AS_LIB"): litelib.Pass("lite79_orange").run(main)
