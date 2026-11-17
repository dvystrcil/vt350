# GUI pass: vt350-lite-55 -> vt350-lite-56   (headless = dry run, never saves)
# vt350#5. The e-box gets a door on its outer face (owner, 2026-11-16: "also the ebox door"; hinged on its REAR edge,
# clear "like the front door").
#  - Built from the printer's front door ("Door (1) (1)": a 2040 frame, three pin hinges on its left edge, the latch,
#    handle and magnets on its right, a 3 mm clear sheet on an EPDM gasket), mirrored across the plane x + y = 0:
#    (x, y, z) -> (-y, -x, z), then +70 in X. The mirror both turns the door onto the e-box's outer face (the front
#    door's outside, -Y, becomes +X) and puts its hinges on the rear edge (the front door's hinges at X -520 land at
#    Y 520); a turn alone would put them at the front. Frame X 163..183, 3 mm off the outer members' face (X 160), as
#    the front door's frame stands 3 mm off the printer's.
#  - The e-box face is 610 wide (Y -90..520) where the front door is 550 (X -520..30): the latch side (its vertical,
#    latch, handle, magnets and corner screws) moves 60 further to the front, and the two horizontal 2040s are
#    lengthened by 60 (an extrusion of their end face, as lite-53). The clear sheet and the gasket are made at the
#    new size (sheet X 185..188 over the whole face; gasket inset 10, as the front door's).
#  - Every part is a plain solid in the global frame (a mirror can't be a link; the Fasteners screws become plain
#    solids). Colours and transparency are copied from the front door's parts (GUI).
# Checks (refuses to save on any): the front door has the parts this pass expects; every new part lies at X >= 130
# and inside the e-box's Y and Z (the latch handle wraps the front corner, as the front door's does); no new part
# overlaps a lite-55 part (the envelopes excepted); lite-56 = lite-55 + the door's parts.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-55.FCStd", f"{MODELS}/vt350-lite-56.FCStd"
DOOR = "Door (1) (1)"
DX, WIDEN = 70.0, 60.0                         # after the mirror: out to the e-box face; the latch side forward
LATCH_SIDE_X = -30.0                            # front-door parts whose global XMin is above this are the latch side
FACE_Y, FACE_Z = (-90.0, 520.0), (-50.0, 690.0)
SHEET_X, GASKET_X, GASKET_IN = (185.0, 188.0), (183.0, 185.0), 10.0
WINDOW, GASKET = "Door window (3 mm", "Door window gasket"


def mirror(s):
    """(x, y, z) -> (-y, -x, z) + (DX, 0, 0): global shape s onto the e-box's face."""
    m = s.mirror(V(0, 0, 0), V(1, 1, 0)); m.translate(V(DX, 0, 0)); return m


def normal_along(f, axis):
    u0, u1, v0, v1 = f.ParameterRange
    n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    return abs(abs((n.x, n.y, n.z)[axis]) - 1) < 1e-6


def end_faces(shape, axis, at):
    out = [f.copy() for f in shape.Faces if normal_along(f, axis) and abs(f.CenterOfMass[axis] - at) < 0.05]
    if not out: raise RuntimeError(f"no end face across axis {axis} at {at}")
    return Part.Compound(out)


def extrude(faces, vec):
    sol = [f.extrude(vec) for f in faces.Faces]
    return (sol[0].multiFuse(sol[1:]) if len(sol) > 1 else sol[0]).removeSplitter()


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    door = next(o for o in doc.Objects if o.TypeId == "App::Part" and o.Label == DOOR)
    def subtree(o):
        out = []
        for c in getattr(o, "Group", []) or []: out += [c] + subtree(c)
        return out
    leaves = list({o.Name: o for o in subtree(door) if linkgeo.is_leaf(o)}.values())
    horiz = [o for o in leaves if o.Label.startswith("2040 (2) (1)")]
    window = [o for o in leaves if o.Label.startswith(WINDOW)]
    gasket = [o for o in leaves if o.Label.startswith(GASKET)]
    p.check(len(leaves) >= 30 and len(horiz) == 2 and len(window) == 1 and len(gasket) == 1,
            f"front door: {len(leaves)} parts, {len(horiz)} horizontal 2040s, {len(window)} sheet, {len(gasket)} gasket")
    root = pr.root("4040-350x350x250 Voron Trident")
    grp = doc.addObject("App::Part", "EboxDoor"); grp.Label = "E-box door (lite-56, mirrored from Door (1) (1))"
    root.addObject(grp)
    made = []
    def add(label, s, src):
        n = doc.addObject("Part::Feature", "EboxDoorPart"); grp.addObject(n)
        loc = s.copy(); loc.Placement = linkgeo.gplace(grp).inverse().multiply(loc.Placement)
        n.Shape = loc; n.Label = label
        if FreeCAD.GuiUp and src is not None:
            dvo = linkgeo.drawn_vo(src) or src.ViewObject
            try: n.ViewObject.ShapeAppearance = dvo.ShapeAppearance
            except Exception: pass
            n.ViewObject.Visibility = src.ViewObject.Visibility
        made.append(n)
    n_latch = 0
    for o in leaves:
        if o in window or o in gasket: continue
        s = pr.shapes[o.Name]
        g = mirror(s.copy() if o.TypeId != "App::Link" else Part.makeCompound(s.Solids))
        latch = pr.boxes[o.Name].XMin > LATCH_SIDE_X
        if latch: g.translate(V(0, -WIDEN, 0)); n_latch += 1
        if o in horiz:                       # mapped Y 10..480: lengthen at its front end (Y 10) to Y -50
            b = g.BoundBox
            g = Part.makeCompound(list(g.Solids) + list(extrude(end_faces(g, 1, b.YMin), V(0, -WIDEN, 0)).Solids))
        add(f"E-box door: {o.Label[:60]}", g, o)
    p.log(f"latch side moved {WIDEN} to the front: {n_latch} parts")
    y0, y1 = FACE_Y; z0, z1 = FACE_Z
    add(f"E-box door window (3 mm clear sheet, as the front door's), {y1 - y0:.0f} x {z1 - z0:.0f}",
        box(*SHEET_X, y0, y1, z0, z1), window[0] if window else None)
    add("E-box door window gasket (EPDM foam, black)",
        box(*GASKET_X, y0 + GASKET_IN, y1 - GASKET_IN, z0 + GASKET_IN, z1 - GASKET_IN), gasket[0] if gasket else None)
    n0 = len(pr.leaves)
    doc.recompute(); pr.refresh()
    for n in made:
        b = pr.boxes[n.Name]
        ok = b.XMin >= 130 and b.YMin >= y0 - 45 and b.YMax <= y1 + 15 and b.ZMin >= z0 - 15 and b.ZMax <= z1 + 15
        p.check(ok, f"{n.Label[:58]}: X {b.XMin:.1f}..{b.XMax:.1f} Y {b.YMin:.1f}..{b.YMax:.1f} Z {b.ZMin:.1f}..{b.ZMax:.1f}")
    fr = [n for n in made if "2040" in n.Label]
    if fr:
        fb = FreeCAD.BoundBox()
        for n in fr: fb.add(pr.boxes[n.Name])
        p.check(abs(fb.XMin - 163) < 0.3 and abs(fb.XMax - 183) < 0.3 and abs(fb.YMin - y0) < 0.3 and abs(fb.YMax - y1) < 0.3
                and abs(fb.ZMin - z0) < 0.3 and abs(fb.ZMax - z1) < 0.3,
                f"door frame X {fb.XMin:.1f}..{fb.XMax:.1f} Y {fb.YMin:.1f}..{fb.YMax:.1f} Z {fb.ZMin:.1f}..{fb.ZMax:.1f}")
    env = {o.Name for o in pr.leaves if "envelope" in o.Label}
    mine = {n.Name for n in made}
    items = [(n.Label, pr.shapes[n.Name]) for n in made]
    p.no_overlap(items, pr, lambda r: f"no door part overlaps a lite-55 part: {len(r.hits)} {r.hits[:12]}", exclude=env | mine)
    p.check(len(pr.leaves) == n0 + len(made), f"lite-56 solids: {len(pr.leaves)} (lite-55 {n0} + {len(made)} door parts)")
    p.dump({"parts": len(made), "latch_side": n_latch, "widen": WIDEN, "dx": DX})
    return p.finish([(doc, DST)])


litelib.Pass("lite56_ebox_door").run(main)
