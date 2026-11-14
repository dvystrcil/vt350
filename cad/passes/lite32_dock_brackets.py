# GUI pass: vt350-lite-31 -> vt350-lite-32   (headless = dry run, never saves)
# vt350#19 AC7 (user, 2026-11-14): what holds the five keyslot plates on lite-31's 2020 dock bar, and the bar on the frame.
#  - Keyslot plate -> bar (user: "printed L-bracket, M5 T-nuts", on the plate's EXISTING holes). Each keyslot plate
#    (`Dock Asembly`, andrewmcgr's XOL-A4T dock) has two rows of 2 x M3 heat-set holes on its OUTER face (the face away
#    from its head, where the corner dock arm used to screw on). The bracket is a 6 mm web on that face (the upper 4
#    holes, M3 SHCS counterbored 3.2 mm) running forward to an upright on the bar's FRONT face: one M5 into a T-nut in
#    the bar's front slot, tightened from the front, so a dock slides along the bar in X when loosened.
#  - Slots 3 (R) and 4 (L) sit BACK TO BACK (R|L, the row study's 92.00): their outer faces are 2.00 mm apart, so a
#    web can't go between them, and their holes face each other. User's rule for a clash (2026-11-14): "redesign the
#    bracket, keep the row; the bar may move". So that pair is printed as ONE part: both keyslot plates joined by a
#    2 mm filler (the gap, full height), with 2 x M3 heat-sets in the filler's front edge; a front hanger screws to
#    those and to the bar's front slot (2 x M5 + T-nuts). The filler's insert holes are cut in the filler only; they
#    run 1 mm into each plate, which the printed pair has (the plates aren't re-cut in the model).
#  - Bar -> 2040 front verticals (user: inside corner brackets, "if I ever start using a remixed head I need to be able
#    to adjust the overall height of the docking bar"): a printed corner bracket on top of each bar end, one M5 into a
#    T-nut in the vertical's inner slot (slides in Z when loosened) and one into the bar's top slot. No machining of
#    the bar or the verticals (notes/cut-list.md, #7 AC3).
#  - The bar keeps its geometry and place. It takes `2020 (1)`'s ShapeMaterial and a label the frame colour rule
#    matches (vt350#149, comment 6881476971: lite-31's bar rendered unpainted).
# Checks (refuses to save on any): the plates' upper heat-set holes are where the brackets put their screws (all three
# plates that get one); slots 3/4 are 2.00 mm apart outer face to outer face; each new part is a valid solid, overlaps
# nothing in the printer and no other new part, and sits on what it is screwed to (distance 0); the carried head of
# every slot (head + MadMax plate + tube + the empty carriage at the pickup) clears every new part by >= 2 mm at
# every dock move (park_x, Y attach..parked; detach_x, Y attach..+60); the bar's label/material give role `frame`
# and the printed parts `printed` in cad/render/colours.json; solids 1265 + 7.
import FreeCAD, Part, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))      # litelib, which puts the other code folders on the path
import litelib
from litelib import is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-31.FCStd", f"{MODELS}/vt350-lite-32.FCStd"
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path.insert(0, f"{REPO}/platform/render")
import colours
V = FreeCAD.Vector
PAT = "LLRLR"
SLOTS = [("Left Toolhead", "Left Dock"), ("Toolhead slot 2 (L)", "Dock slot 2 (L)"), ("Toolhead slot 3 (R)", "Dock slot 3 (R)"),
         ("Toolhead slot 4 (L)", "Dock slot 4 (L)"), ("Right Toolhead", "Right Dock")]
BAR_PREFIX, BAR_SRC = "Dock bar 2020", "2020 (1)"
BAR_LABEL = "2020 dock bar (front; holds the 5 keyslot plates, #19)"
VERTS = ("2040(Mirror)", "2040")                  # the front verticals the bar ends on (left, right)
SLIDE, CARRIED_DZ, DETACH = 6.0, -0.315, 5.0      # toolchanger.cfg keyslot slide / detach; carried vs docked (sweep_toolhead)
CLEAR = 2.0                                       # carried head vs a new part
DY_DETACH = range(-6, 61, 2)                      # carried at detach_x: Y attach .. +60 (past the brackets' rear)
DY_PARK = (-6, -4, -2, 0)                         # carried at park_x: the keyslot slide
WEB_T, UP_W, TF, ZB = 6.0, 14.0, 5.0, 453.3       # keyslot bracket: web thickness, upright reach outboard, front plate, bottom Z
PAIR_ZB, PAIR_W, PAIR_INS, PAIR_IN = 450.3, 10.0, (456.3, 463.3), 2.0   # PAIR_IN: lower block inset from the plates' outer faces
END_T, END_H, END_L = 5.0, 20.0, 22.0


def tree(o):
    out = [o]
    for k in (getattr(o, 'Group', []) or []): out += tree(k)
    return out


def bx(x0, x1, y0, y1, z0, z1):
    x0, x1 = min(x0, x1), max(x0, x1)
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, p, d, h): return Part.makeCylinder(r, h, V(*p), V(*d))


def keyslot_bracket(bar, F, o, holes):
    """F: the plate's outer face X; o: outward sign (L -1, R +1); holes [(y, z)]: its upper heat-sets."""
    yf = bar.YMin - TF
    s = bx(F, F + o * WEB_T, yf, max(y for y, _ in holes) + 5.0, ZB, bar.ZMin)
    s = s.fuse(bx(F - o * 6.0, F + o * UP_W, yf, bar.YMin, ZB, bar.ZMax))
    for y, z in holes:
        s = s.cut(cyl(1.7, (F - o * 0.01, y, z), (o, 0, 0), WEB_T + 1))
        s = s.cut(cyl(3.0, (F + o * (WEB_T - 3.2), y, z), (o, 0, 0), 4))
    xm = (F - o * 6.0 + F + o * UP_W) / 2
    s = s.cut(cyl(2.75, (xm, yf - 1, (bar.ZMin + bar.ZMax) / 2), (0, 1, 0), TF + 2))
    return s.removeSplitter()


def pair_parts(bar, ka, kb, front):
    """ka, kb: the boxes of two back-to-back keyslot plates (R then L); front: the plates' front Y in the hanger's Z
    band (set back from their overall front there). Returns (filler, hanger)."""
    xa, xb = ka.XMax, kb.XMin; xc = (xa + xb) / 2; yf = bar.YMin - TF
    fill = bx(xa, xb, front, ka.YMax, ka.ZMin, ka.ZMax)
    h = bx(ka.XMin + PAIR_IN, kb.XMax - PAIR_IN, yf, front, PAIR_ZB, bar.ZMin).fuse(   # inside the heads' outer faces
        bx(ka.XMin - PAIR_W, kb.XMax + PAIR_W, yf, bar.YMin, PAIR_ZB, bar.ZMax))
    for z in PAIR_INS:
        h = h.cut(cyl(1.7, (xc, yf - 1, z), (0, 1, 0), 20)).cut(cyl(3.0, (xc, yf - 1, z), (0, 1, 0), 1 + 3.2))
        fill = fill.cut(cyl(2.0, (xc, front - 0.01, z), (0, 1, 0), 6.0))
    for x in (ka.XMin - PAIR_W / 2, kb.XMax + PAIR_W / 2):
        h = h.cut(cyl(2.75, (x, yf - 1, (bar.ZMin + bar.ZMax) / 2), (0, 1, 0), TF + 2))
    return fill.removeSplitter(), h.removeSplitter()


def end_bracket(bar, xf, o, vy):
    """xf: the vertical's inner face X; o: into the printer (+1 left end, -1 right end); vy: the vertical's Y range."""
    s = bx(xf, xf + o * END_T, vy[0], vy[1], bar.ZMax, bar.ZMax + END_H)                  # on the vertical's inner face
    s = s.fuse(bx(xf, xf + o * END_L, vy[0], bar.YMax, bar.ZMax, bar.ZMax + END_T))       # on the bar's top
    s = s.fuse(bx(xf, xf + o * END_L, vy[0], vy[0] + END_T, bar.ZMax, bar.ZMax + END_H))  # gusset
    s = s.cut(cyl(2.75, (xf - o, (vy[0] + vy[1]) / 2, bar.ZMax + END_T + (END_H - END_T) / 2), (o, 0, 0), END_T + 2))
    s = s.cut(cyl(2.75, (xf + o * (END_L - 8), (bar.YMin + bar.YMax) / 2, bar.ZMax - 1), (0, 0, 1), END_T + 2))
    return s.removeSplitter()


def box_gap(a, b):
    """Euclidean gap between two boxes (0 when they overlap): a lower bound of the shapes' distance."""
    d = [max(0.0, a.XMin - b.XMax, b.XMin - a.XMax), max(0.0, a.YMin - b.YMax, b.YMin - a.YMax), max(0.0, a.ZMin - b.ZMax, b.ZMin - a.ZMax)]
    return (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5


def vbox(shape):
    """The box of a shape's vertices: exact for these prisms and plates (a GUI-mode optimal box is a tessellation's)."""
    b = FreeCAD.BoundBox()
    for v in shape.Vertexes: b.add(v.Point)
    return b


def upper_holes(shape, face_x, zmin):
    """Centres (y, z) of the M3 heat-set holes (cylinders r 2.2..2.5 along X) at face_x, above zmin."""
    out = set()
    for f in shape.Faces:
        if not isinstance(f.Surface, Part.Cylinder) or not 2.2 < f.Surface.Radius < 2.5: continue
        if abs(abs(f.Surface.Axis.x) - 1) > 1e-6: continue
        b = f.BoundBox
        if min(abs(b.XMin - face_x), abs(b.XMax - face_x)) > 0.3 or b.ZMin < zmin: continue
        out.add((round((b.YMin + b.YMax) / 2, 2), round((b.ZMin + b.ZMax) / 2, 2)))
    return sorted(out)


def main(p):
    pr = p.open(SRC); doc = pr.doc
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    cmap = colours.load(f"{REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    bar_o = next(o for o in pr.leaves if o.Label.startswith(BAR_PREFIX))
    bar = vbox(pr.shapes[bar_o.Name])
    p.log(f"bar {bar_o.Label!r}: {bar}")
    slots = []
    for i, (h, d) in enumerate(SLOTS, 1):
        ks = [o for o in tree(obj(d)) if is_leaf(o) and o.Label.startswith("Dock Asembly")]
        if len(ks) != 1: raise RuntimeError(f"{d}: {len(ks)} keyslot plates")
        k = PAT[i - 1]; kb = vbox(pr.shapes[ks[0].Name])
        F, o = (kb.XMin, -1) if k == "L" else (kb.XMax, +1)
        slots.append(dict(n=i, k=k, head=obj(h), dock=obj(d), ks=ks[0], kb=kb, F=F, o=o))
    # --- the plates' heat-set holes, from the model
    ref = upper_holes(pr.shapes[slots[0]["ks"].Name], slots[0]["F"], 450.0)
    p.log("slot 1 keyslot plate, upper heat-set holes (y, z):", ref)
    p.check(len(ref) == 4, f"slot 1 keyslot plate has 4 upper heat-set holes on its outer face ({len(ref)})")
    side = [s for s in slots if s["n"] in (1, 2, 5)]
    for s in side:
        hs = upper_holes(pr.shapes[s["ks"].Name], s["F"], 450.0)
        p.check(hs == ref, f"slot {s['n']} ({s['k']}): the same 4 holes on the outer face X {s['F']:.2f} ({hs})")
    a, b = slots[2], slots[3]
    gap = b["kb"].XMin - a["kb"].XMax
    p.check(a["k"] == "R" and b["k"] == "L" and abs(gap - 2.0) < 0.01,
            f"slots 3 ({a['k']}) and 4 ({b['k']}): outer faces face each other {gap:.2f} mm apart (no room for a web)")
    # --- the new parts
    new = []                                    # (label, shape, group object)
    for s in side:
        new.append((f"Dock bracket slot {s['n']} ({s['k']}) (keyslot plate to bar)", keyslot_bracket(bar, s["F"], s["o"], ref),
                    s["dock"]))
    band = bx(a["kb"].XMin - 1, b["kb"].XMax + 1, a["kb"].YMin - 1, a["kb"].YMax + 1, PAIR_ZB, bar.ZMin)
    front = min(pr.shapes[s["ks"].Name].common(band).BoundBox.YMin for s in (a, b))
    p.log(f"slots 3/4 plates' front in the hanger band Z {PAIR_ZB}..{bar.ZMin:.2f}: Y {front:.3f} (overall {a['kb'].YMin:.3f})")
    fill, hang = pair_parts(bar, a["kb"], b["kb"], front)
    new.append(("Dock pair filler slots 3+4 (prints with both keyslot plates)", fill, a["dock"]))
    new.append(("Dock pair hanger slots 3+4 (keyslot pair to bar)", hang, a["dock"]))
    vb = {lab: vbox(pr.shapes[obj(lab).Name]) for lab in VERTS}
    p.check(abs(vb[VERTS[0]].XMax - bar.XMin) < 0.01 and abs(vb[VERTS[1]].XMin - bar.XMax) < 0.01,
            f"bar ends on the verticals' inner faces (X {vb[VERTS[0]].XMax:.2f} / {vb[VERTS[1]].XMin:.2f})")
    grp = bar_o.getParentGeoFeatureGroup()
    new.append(("Dock bar end bracket (left)", end_bracket(bar, vb[VERTS[0]].XMax, +1, (vb[VERTS[0]].YMin, vb[VERTS[0]].YMax)), grp))
    new.append(("Dock bar end bracket (right)", end_bracket(bar, vb[VERTS[1]].XMin, -1, (vb[VERTS[1]].YMin, vb[VERTS[1]].YMax)), grp))
    for lab, sh, _ in new:
        p.check(sh.isValid() and len(sh.Solids) == 1, f"{lab}: one valid solid, {sh.Volume:.1f} mm3, {sh.BoundBox}")
    # --- static checks
    p.no_overlap([(lab, sh) for lab, sh, _ in new], pr, lambda r: f"new parts x printer: {r.hits[:6]}")
    pairs = [(i, j) for i in range(len(new)) for j in range(i + 1, len(new)) if new[i][1].BoundBox.intersect(new[j][1].BoundBox)]
    vols = p.volumes([(new[i][1], new[j][1]) for i, j in pairs])
    hit = [(new[i][0], new[j][0], round(v, 3)) for (i, j), v in zip(pairs, vols) if v > 1e-3]
    p.check(not hit, f"new parts x each other: {hit}")
    bar_s = pr.shapes[bar_o.Name]
    seats = [(new[k][0], new[k][1], tgt) for k, s in enumerate(side) for tgt in (("plate", pr.shapes[s["ks"].Name]), ("bar", bar_s))]
    seats += [(new[3][0], new[3][1], ("slot 3 plate", pr.shapes[a["ks"].Name])), (new[3][0], new[3][1], ("slot 4 plate", pr.shapes[b["ks"].Name])),
              (new[4][0], new[4][1], ("bar", bar_s)), (new[4][0], new[4][1], ("slot 3 plate", pr.shapes[a["ks"].Name])),
              (new[4][0], new[4][1], ("slot 4 plate", pr.shapes[b["ks"].Name])), (new[4][0], new[4][1], ("pair filler", new[3][1])),
              (new[5][0], new[5][1], ("bar", bar_s)), (new[5][0], new[5][1], ("left vertical", pr.shapes[obj(VERTS[0]).Name])),
              (new[6][0], new[6][1], ("bar", bar_s)), (new[6][0], new[6][1], ("right vertical", pr.shapes[obj(VERTS[1]).Name]))]
    for lab, sh, (tl, ts) in seats:
        d = sh.distToShape(ts)[0]
        p.check(d < 0.01, f"{lab} sits on the {tl} (distance {d:.3f})")
    # --- every slot's carried head at the dock moves vs the new parts
    # distToShape is wrong for some head solids here: it returns 0.00 for parts whose boxes are > 10 mm apart (found on
    # lite-31's BREPs, 2026-11-14). A true distance is never below the gap between the two boxes, so each pair whose
    # boxes are within CLEAR + 1 mm is measured, the result is raised to the box gap, and every raised pair is logged.
    tubes = {s["n"]: [o for o in tree(s["head"]) if is_leaf(o) and o.Label.startswith("Bowden")] for s in slots}
    tubes[1] = [o for o in tubes[1] if o.Label == "Bowden Left"]
    tubes[5] = [obj("Bowden Right")]
    car = {}
    for s in (slots[0], slots[-1]):
        car[s["k"]] = (s, [o for c in tree(s["dock"]) if c.TypeId == 'App::Part' and c.Label.startswith("Carriage")
                           for o in tree(c) if is_leaf(o)])
    for s in slots:
        rs, cl = car[s["k"]]
        cdx = s["kb"].XMin - rs["kb"].XMin                       # the pickup carriage copy, moved to this slot
        mine = [o for o in tree(s["head"]) + tree(s["dock"]) if is_leaf(o) and not o.Label.startswith(("Bowden", "Dock Asembly"))
                and o.Name not in {c.Name for c in cl}] + tubes[s["n"]]
        group = [(o.Label, pr.shapes[o.Name]) for o in mine] + [(o.Label, pr.shapes[o.Name].translated(V(cdx, 0, 0))) for o in cl]
        det = DETACH if s["k"] == "L" else -DETACH
        poses = [(0.0, dy) for dy in DY_PARK] + [(det, dy) for dy in DY_DETACH]
        tasks, keys = [], []
        for dx, dy in poses:
            for lab, sh in group:
                m = sh.BoundBox; mb = FreeCAD.BoundBox(m.XMin + dx, m.YMin + dy, m.ZMin + CARRIED_DZ, m.XMax + dx, m.YMax + dy, m.ZMax + CARRIED_DZ)
                for plab, psh, _ in new:
                    g = box_gap(mb, psh.BoundBox)
                    if g < CLEAR + 1.0:
                        tasks.append((psh, sh.translated(V(dx, dy, CARRIED_DZ)))); keys.append((f"{lab} @x{dx:+.0f} y{dy:+.0f}", plab, g))
        ds = p.map(litelib._t_dist, tasks)
        res, raised = [], []
        for (k, plab, g), d in zip(keys, ds):
            if isinstance(d, litelib._Err): raise RuntimeError(f"distToShape failed for {k} vs {plab}: {d.msg}")
            if d < g - 1e-6: raised.append((k, plab, round(d, 2), round(g, 2)))
            res.append((max(d, g), k, plab))
        if raised: p.log(f"slot {s['n']}: {len(raised)} distToShape results below their box gap, raised to it: {raised[:4]}")
        dmin = min(res)[0] if res else float("inf")
        near = sorted((round(d, 2), k, plab) for d, k, plab in res if d < CLEAR)
        p.check(not near, f"slot {s['n']} ({s['k']}) carried head + carriage, {len(poses)} dock poses ({len(tasks)} pairs measured): "
                f"min {dmin:.2f} mm to the new parts {near[:3]}")
    # --- write
    abs_src = next((o for o in pr.leaves if 'ABS' in getattr(getattr(o, 'ShapeMaterial', None), 'Name', '')), None)
    p.check(abs_src is not None, f"a printed (ABS) part to take the brackets' material from ({abs_src.Label if abs_src else None})")
    for lab, sh, g in new:
        o = doc.addObject('Part::Feature', 'DockBracket'); o.Shape = sh; g.addObject(o)
        o.Placement = g.getGlobalPlacement().inverse().multiply(o.Placement)
        o.Label = lab; o.ShapeMaterial = abs_src.ShapeMaterial
        if FreeCAD.GuiUp:
            try: o.ViewObject.ShapeAppearance = abs_src.ViewObject.ShapeAppearance
            except Exception: o.ViewObject.ShapeColor = abs_src.ViewObject.ShapeColor
    src = obj(BAR_SRC)
    bar_o.Label = BAR_LABEL; bar_o.ShapeMaterial = src.ShapeMaterial
    doc.recompute(); pr.refresh()
    def gpath(o):
        r, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r))
    mat = lambda o: getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default'
    role = colours.role_of(cmap, bar_o.Label, gpath(bar_o), mat(bar_o))
    p.check(role == "frame", f"bar: label {bar_o.Label!r}, material {mat(bar_o)}, group {gpath(bar_o)!r} -> role {role}")
    for o in [o for o in pr.leaves if o.Label in {lab for lab, _, _ in new}]:
        r_ = colours.role_of(cmap, o.Label, gpath(o), mat(o))
        p.check(r_ == "printed", f"{o.Label}: material {mat(o)} -> role {r_}")
    p.check(len(pr.leaves) == n_before + len(new), f"solids: {n_before} + {len(new)} = {len(pr.leaves)}")
    p.dump({"bar": [bar.XMin, bar.YMin, bar.ZMin, bar.XMax, bar.YMax, bar.ZMax], "bar_label": BAR_LABEL, "heat_sets": ref,
            "parts": [dict(label=lab, volume=round(sh.Volume, 1),
                           box=[round(v, 2) for v in (sh.BoundBox.XMin, sh.BoundBox.YMin, sh.BoundBox.ZMin,
                                                      sh.BoundBox.XMax, sh.BoundBox.YMax, sh.BoundBox.ZMax)]) for lab, sh, _ in new],
            "fasteners": {"M3 SHCS into the plates' heat-sets": 12, "M3 heat-set in the pair filler + M3 SHCS": 2,
                          "M5 + T-nut, bar front slot": 5, "M5 + T-nut, bar top slot": 2, "M5 + T-nut, vertical inner slot": 2}})
    p.finish([(doc, DST)])


litelib.Pass("lite32_dock_brackets").run(main)
