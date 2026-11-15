# GUI pass: vt350-lite-40 -> vt350-lite-41   (headless = dry run, never saves)
# vt350#19. The user (2026-11-14): "present some voron type bottom skirts in ABS white with orange accents".
#
# The frame's bottom extrusions sit at Z -50..-10 on four levelling feet (placeholders: bracket Z -58..-50, stud,
# rubber pad Z -100..-82 on the base board at Z -100). The skirts close the 50 mm band under the frame, Voron style:
#  - 4 WHITE SKIRT PANELS, one per face between the corners: a 3 mm wall flush with that face's outer skin (the
#    painted side panels, the door window, the rear 4040's back face), from under the frame down to Z -95 (5 mm off
#    the board). A 16 mm flange along the top lies under the bottom extrusion (M5 into its bottom slot: BOM).
#    The front one stops 1 mm under the door window (Z -51), so the door swings clear; its flange is under the door
#    frame's fixed bottom 2040.
#  - In each panel a vent window, 60 % of its length, with an ORANGE GRILLE in it (vertical slots, 3 mm wide at an
#    8 mm pitch) and a 4 mm lip behind the wall that holds it in.
#  - 4 ORANGE CORNER pieces, L-shaped, 100 mm along each face, ending at Z -80: the rubber foot pads (D50 placeholders)
#    stand 2 mm proud of the side faces at every corner, so the corners stop above them and the feet show below.
#    The corners have no flange (the foot brackets fill the frame's corners from Z -58): they key onto the panels'
#    ends; that joint is not modelled.
# The outer faces are measured from the model's solids, not assumed. Airflow for the bottom filter (inside, Z to -84):
# the 4 grilles are 29 % open (measured, logged); whether the filter needs more is not checked.
# Checks (refuses to save on any): the faces measured; each part one valid solid; nothing overlaps anything (the
# grilles sit in their windows, touching only); each flange touches its extrusion's bottom face; every part clears
# the foot pads and the base board by >= 1 mm; the skirt's outline is flush with the walls above (the side panels'
# paint, the door window, the rear 4040); roles; solids + 12.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "platform/render")]
import litelib, colours
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-40.FCStd", f"{MODELS}/vt350-lite-41.FCStd"
EXTRAS = "Enclosure extras (lite-16)"
GROUP = "Bottom skirts (lite-41)"
T, FL_T, FL_D = 3.0, 4.0, 16.0                     # wall, flange thickness, flange depth (from the wall's inside)
Z_TOP, Z_FRONT_TOP, Z_BOT, Z_CORNER_BOT = -50.0, -51.0, -95.0, -80.0
CORNER = 100.0
VENT_FRAC, VENT_Z = 0.60, (-85.0, -61.0)
SLOT_W, SLOT_PITCH, SLOT_MARGIN, LIP = 3.0, 8.0, 2.0, 4.0
TOL = 1e-3
LIC = "(printed ABS, vt350, GPL-3.0-or-later)"


def main(p):
    pr = p.open(SRC); doc = pr.doc
    lab = lambda l: next(o for o in pr.leaves if o.Label == l)
    box = lambda l: pr.shapes[lab(l).Name].BoundBox
    cmap = colours.load(f"{_REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    # ---- the outline, from the solids
    xl = box("Left side panel (3 mm) paint, outside").XMin
    xr = box("Right side panel (3 mm) paint, outside").XMax
    yf = next(pr.shapes[o.Name].BoundBox for o in pr.leaves if o.Label.startswith("Door window (3 mm")).YMin
    rear = [o for o in pr.leaves if o.Label == "4040 (2)" and o.getParentGeoFeatureGroup() and o.getParentGeoFeatureGroup().Label == "Horizontals"]
    p.check(len(rear) == 1, f"the rear bottom 4040: {len(rear)}")
    rb = pr.shapes[rear[0].Name].BoundBox; yr = rb.YMax
    p.check(abs(xl + 523) < 0.2 and abs(xr - 33) < 0.2 and abs(yf + 118) < 0.2 and abs(yr - 520) < 0.2 and abs(rb.ZMin - Z_TOP) < 0.1,
            f"outline measured: X {xl:.1f}..{xr:.1f}, Y {yf:.1f}..{yr:.1f}; the bottom extrusions' underside Z {rb.ZMin:.1f}")
    Y0, Y1 = yf, yr + T                                        # the rear wall stands outside the 4040's back face
    pads = [o for o in pr.leaves if o.Label.startswith("Levelling foot pad")]
    board = lab("Base board (18 mm, plywood/MDF, placeholder)")
    p.check(len(pads) == 4, f"4 foot pads ({len(pads)})")
    # ---- faces: name, wall box (x0, x1, y0, y1), along-axis, flange box builder, top Z
    faces = {
        "front": dict(wall=(xl, xr, Y0, Y0 + T), ax="x", top=Z_FRONT_TOP, inward=V(0, 1, 0)),
        "rear":  dict(wall=(xl, xr, Y1 - T, Y1), ax="x", top=Z_TOP, inward=V(0, -1, 0)),
        "left":  dict(wall=(xl, xl + T, Y0, Y1), ax="y", top=Z_TOP, inward=V(1, 0, 0)),
        "right": dict(wall=(xr - T, xr, Y0, Y1), ax="y", top=Z_TOP, inward=V(-1, 0, 0)),
    }
    grp = doc.addObject("App::DocumentObjectGroup", "Bottom_skirts"); grp.Label = GROUP
    next(o for o in doc.Objects if o.Label == EXTRAS).addObject(grp)
    made = []
    def add(name, label, shape):
        p.check(shape.isValid() and len(shape.Solids) == 1, f"{label[:40]}: one valid solid ({len(shape.Solids)}), {shape.Volume:.0f} mm3")
        o = doc.addObject("Part::Feature", name); o.Shape = shape; o.Label = label; grp.addObject(o); made.append(o); return o
    def bx(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
    flanges = {}
    for f, d in faces.items():
        x0, x1, y0, y1 = d["wall"]
        # the panel runs between the corner pieces
        if d["ax"] == "x": a0, a1 = x0 + CORNER, x1 - CORNER; wall = bx(a0, a1, y0, y1, Z_BOT, d["top"])
        else:              a0, a1 = y0 + CORNER, y1 - CORNER; wall = bx(x0, x1, a0, a1, Z_BOT, d["top"])
        # flange under the extrusion, from the wall's inner face inward
        n = d["inward"]
        if d["ax"] == "x":
            yi = y1 if n.y > 0 else y0
            fl = bx(a0, a1, min(yi, yi + n.y * FL_D), max(yi, yi + n.y * FL_D), Z_TOP - FL_T, Z_TOP)
        else:
            xi = x1 if n.x > 0 else x0
            fl = bx(min(xi, xi + n.x * FL_D), max(xi, xi + n.x * FL_D), a0, a1, Z_TOP - FL_T, Z_TOP)
        L = a1 - a0; v0, v1 = a0 + L * (1 - VENT_FRAC) / 2, a1 - L * (1 - VENT_FRAC) / 2
        if d["ax"] == "x":
            win = bx(v0, v1, y0, y1, *VENT_Z)
            lip = bx(v0 - LIP, v1 + LIP, *( (y1, y1 + 2.0) if n.y > 0 else (y0 - 2.0, y0) ), VENT_Z[0] - LIP, VENT_Z[1] + LIP)
        else:
            win = bx(x0, x1, v0, v1, *VENT_Z)
            lip = bx(*( (x1, x1 + 2.0) if n.x > 0 else (x0 - 2.0, x0) ), v0 - LIP, v1 + LIP, VENT_Z[0] - LIP, VENT_Z[1] + LIP)
        panel = wall.fuse(fl).cut(win).removeSplitter()
        grille = win.fuse(lip)
        k, s = 0, v0 + SLOT_PITCH / 2
        while s + SLOT_W / 2 < v1 - 4.0:
            if s - SLOT_W / 2 > v0 + 4.0:
                z0, z1 = VENT_Z[0] + SLOT_MARGIN, VENT_Z[1] - SLOT_MARGIN
                lo, hi = (y0 - 2.5, y1 + 2.5) if d["ax"] == "x" else (x0 - 2.5, x1 + 2.5)
                sl = bx(s - SLOT_W / 2, s + SLOT_W / 2, lo, hi, z0, z1) if d["ax"] == "x" else bx(lo, hi, s - SLOT_W / 2, s + SLOT_W / 2, z0, z1)
                grille = grille.cut(sl); k += 1
            s += SLOT_PITCH
        grille = grille.removeSplitter()
        open_frac = k * SLOT_W * (VENT_Z[1] - VENT_Z[0] - 2 * SLOT_MARGIN) / ((v1 - v0) * (VENT_Z[1] - VENT_Z[0]))
        p.log(f"{f}: panel {L:.0f} long, vent {v1 - v0:.0f} x {VENT_Z[1] - VENT_Z[0]:.0f} with {k} slots ({open_frac:.0%} open)")
        flanges[f] = add("Skirt_panel", f"Skirt panel {f} {LIC}", panel)
        add("Skirt_grille", f"Skirt grille {f} {LIC}", grille)
    # corners: L pieces, 100 along each face, Z -80 .. top
    for nm, xo, yo in (("front-left", xl, Y0), ("front-right", xr, Y0), ("rear-left", xl, Y1), ("rear-right", xr, Y1)):
        sx = 1 if xo == xl else -1; sy = 1 if yo == Y0 else -1
        top = Z_FRONT_TOP if yo == Y0 else Z_TOP
        leg_x = bx(min(xo, xo + sx * CORNER), max(xo, xo + sx * CORNER), min(yo, yo + sy * T), max(yo, yo + sy * T), Z_CORNER_BOT, top)
        leg_y = bx(min(xo, xo + sx * T), max(xo, xo + sx * T), min(yo + sy * T, yo + sy * CORNER), max(yo + sy * T, yo + sy * CORNER), Z_CORNER_BOT, Z_TOP)
        add("Skirt_corner", f"Skirt corner {nm} {LIC}", leg_x.fuse(leg_y).removeSplitter())
    doc.recompute(); pr.refresh()
    mine = {o.Name for o in made}
    # ---- checks
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in made], pr, lambda r: f"the skirts vs the printer: {r.hits[:6]}", exclude=mine)
    for i, a in enumerate(made):
        for b in made[i + 1:]:
            if not pr.boxes[a.Name].intersect(pr.boxes[b.Name]): continue
            v = pr.shapes[a.Name].common(pr.shapes[b.Name]).Volume
            p.check(v < TOL, f"{a.Label[:24]} vs {b.Label[:24]}: {v:.4f} mm3")
    under = {"front": "2040 (2) (1)001", "rear": "4040 (2)", "left": "4040 (1)001", "right": "4040 (1)"}
    for f, o in flanges.items():
        ex = [x for x in pr.leaves if x.Label == under[f] and pr.boxes[x.Name].ZMin < -49]
        d = min(pr.shapes[o.Name].distToShape(pr.shapes[x.Name])[0] for x in ex)
        p.check(d < 0.01, f"skirt panel {f}: its flange touches the underside of {under[f]} (gap {d:.3f})")
    for o in made:
        d = min(pr.shapes[o.Name].distToShape(pr.shapes[x.Name])[0] for x in pads + [board])
        p.check(d >= 1.0, f"{o.Label[:28]}: clears the foot pads and the board by {d:.1f} mm")
    allb = pr.shapes[made[0].Name].BoundBox
    for o in made[1:]: allb.add(pr.boxes[o.Name])
    p.check(abs(allb.XMin - xl) < TOL and abs(allb.XMax - xr) < TOL and abs(allb.YMin - yf) < TOL and abs(allb.YMax - Y1) < TOL,
            f"the skirts' outline X {allb.XMin:.1f}..{allb.XMax:.1f}, Y {allb.YMin:.1f}..{allb.YMax:.1f}: flush with the walls above "
            f"(the rear wall sits on the rear 4040's back face, {T:.0f} mm proud; the side skirts run {T:.0f} mm past the side panels' rear edge to meet it)")
    def gpath(o):
        r_, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r_.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r_))
    roles = {}
    for o in made: roles.setdefault(o.Label.split()[1], set()).add(colours.role_of(cmap, o.Label, gpath(o), "Default"))
    p.check(roles == {"panel": {"printed"}, "grille": {"accent"}, "corner": {"accent"}}, f"roles {roles}")
    p.check(len(pr.leaves) == n_before + 12, f"solids: {n_before} + 12 = {len(pr.leaves)}")
    p.dump({"outline": [round(xl, 1), round(xr, 1), round(yf, 1), round(Y1, 1)], "z": [Z_BOT, Z_TOP], "corner_bottom_z": Z_CORNER_BOT,
            "volumes_mm3": {o.Label.split(" (")[0]: round(pr.shapes[o.Name].Volume) for o in made}})
    p.finish([(doc, DST)])


litelib.Pass("lite41_skirts").run(main)
