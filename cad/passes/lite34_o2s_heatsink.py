# GUI pass: vt350-lite-33 -> vt350-lite-34   (headless = dry run, never saves)
# vt350#19 (user, 2026-11-14): "The Dragon heatsink is orange/red aluminium. The heatsink I wanted you to color blue is
# on the O2S board." lite-30 added each Orbitool O2S as ONE object built from the upstream STEP's `Orbitool USB O2S
# v3.3` subtree, so the board's heat sink (the STEP's `Orbitool O2&3 2.5 HeatSink 13 fins`, 2113.1 mm3, 30.4 x 23.4 x
# 12.0) is a solid inside the board object and can't take its own colour. This pass moves that solid out of each of the
# 5 boards into its own object, `Orbitool O2S heat sink <side> (Orbiter-Toolboards 52a5a33, CC0-1.0)[suffix]`, in the
# same head group, with an aluminium ShapeMaterial, so colours.json's `o2s_heatsink` rule (blue) paints it. Nothing
# moves: the board keeps every other solid where it was.
# Checks (refuses to save on any): 5 boards; in each, exactly one solid is the heat sink (volume 2113.1 +- 0.5, sorted
# box 12.0/23.4/30.4 +- 0.1); after writing, the board + its heat sink have the board's old volume and box (global);
# the heat sink takes role `o2s_heatsink` and the board keeps `black_plastic` (cad/render/colours.json); solids +5.
import FreeCAD, Part, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))
import litelib
from litelib import is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-33.FCStd", f"{MODELS}/vt350-lite-34.FCStd"
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path.insert(0, f"{REPO}/platform/render")
import colours

BOARD = "Orbitool O2S v3.3 toolboard "
HS_VOL, HS_DIMS = 2113.1, (12.0, 23.4, 30.4)
HS_LABEL = "Orbitool O2S heat sink {side} (Orbiter-Toolboards 52a5a33, CC0-1.0){suffix}"
AL_SRC = "Crossbow - Main Body"                   # an Aluminum-Generic part in each head, for the ShapeMaterial


def is_heatsink(s):
    d = sorted((s.BoundBox.XLength, s.BoundBox.YLength, s.BoundBox.ZLength))
    return abs(s.Volume - HS_VOL) < 0.5 and all(abs(a - b) < 0.1 for a, b in zip(d, HS_DIMS))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    cmap = colours.load(f"{REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    boards = [o for o in pr.leaves if o.Label.startswith(BOARD)]
    p.check(len(boards) == 5, f"{len(boards)} O2S boards (one per head): {[o.Label[-12:] for o in boards]}")
    al = next(o for o in pr.leaves if o.Label == AL_SRC)
    before = {o.Name: (pr.shapes[o.Name].Volume, pr.shapes[o.Name].BoundBox) for o in boards}
    made = []
    for o in boards:
        sol = o.Shape.Solids                       # in the board's parent frame (each carries o.Placement)
        hs = [s for s in sol if is_heatsink(s)]
        p.check(len(hs) == 1, f"{o.Label}: {len(sol)} solids, {len(hs)} is the 13-fin heat sink "
                f"({[round(s.Volume, 1) for s in hs]})")
        if len(hs) != 1: continue
        rest = [s for s in sol if not s.isSame(hs[0])]
        g = o.getParentGeoFeatureGroup()
        side = "Left" if " Left " in o.Label else "Right"
        suffix = o.Label[o.Label.rindex(")") + 1:]
        o.Shape = Part.makeCompound(rest)
        n = doc.addObject('Part::Feature', 'O2S_heatsink'); n.Shape = Part.makeCompound(hs)
        if g is not None: g.addObject(n)
        n.Label = HS_LABEL.format(side=side, suffix=suffix); n.ShapeMaterial = al.ShapeMaterial
        if FreeCAD.GuiUp:
            try: n.ViewObject.ShapeAppearance = al.ViewObject.ShapeAppearance
            except Exception: n.ViewObject.ShapeColor = al.ViewObject.ShapeColor
        made.append((o, n))
    doc.recompute(); pr.refresh()
    def gpath(o):
        r, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r))
    mat = lambda o: getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default'
    for o, n in made:
        v0, b0 = before[o.Name]
        bs, hs = pr.shapes[o.Name], pr.shapes[n.Name]
        both = FreeCAD.BoundBox(bs.BoundBox); both.add(hs.BoundBox)
        dv = abs(bs.Volume + hs.Volume - v0)
        db = max(abs(a - b) for a, b in zip((both.XMin, both.YMin, both.ZMin, both.XMax, both.YMax, both.ZMax),
                                             (b0.XMin, b0.YMin, b0.ZMin, b0.XMax, b0.YMax, b0.ZMax)))
        p.check(dv < 0.01 and db < 0.01, f"{n.Label}: board + heat sink = the old board (volume diff {dv:.4f}, box diff {db:.4f}); "
                f"heat sink at {hs.BoundBox}")
        p.check(colours.role_of(cmap, n.Label, gpath(n), mat(n)) == "o2s_heatsink",
                f"{n.Label}: material {mat(n)} -> role {colours.role_of(cmap, n.Label, gpath(n), mat(n))}")
        p.check(colours.role_of(cmap, o.Label, gpath(o), mat(o)) == "black_plastic",
                f"{o.Label}: role {colours.role_of(cmap, o.Label, gpath(o), mat(o))}")
    p.check(len(pr.leaves) == n_before + len(made), f"solids: {n_before} + {len(made)} = {len(pr.leaves)}")
    p.dump({"heat_sinks": [dict(label=n.Label, board=o.Label, head=gpath(n),
                                box=[round(v, 2) for v in (pr.shapes[n.Name].BoundBox.XMin, pr.shapes[n.Name].BoundBox.YMin,
                                                           pr.shapes[n.Name].BoundBox.ZMin, pr.shapes[n.Name].BoundBox.XMax,
                                                           pr.shapes[n.Name].BoundBox.YMax, pr.shapes[n.Name].BoundBox.ZMax)])
                           for o, n in made]})
    p.finish([(doc, DST)])


litelib.Pass("lite34_o2s_heatsink").run(main)
