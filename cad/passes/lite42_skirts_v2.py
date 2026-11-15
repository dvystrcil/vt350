# GUI pass: vt350-lite-41 -> vt350-lite-42-band / vt350-lite-42-tall   (headless = dry run, never saves)
# vt350#19. The user (2026-11-15, on lite-41's render): "we have a lot of work to do on this. It really is about
# aesthetics" (references: ~/Documents/VT350/references/voron-skirts, and look at the official Voron skirts); then, asked
# about the height: "render both, and keep in mind the adjustable feet need a little room to poke out so the printer is
# not resting on the skirts".
#
# VT350_SKIRT picks the variant (two models, so the user can compare renders):
#   band  the 50 mm band under the frame as it is: skirt Z -50 .. -88 (38 tall), feet and board unchanged.
#   tall  Voron proportions: the official Trident skirts are 66.8 mm tall (VoronDesign/Voron-Trident STLs/Skirt/350,
#         measured). The stand drops 30 mm (longer M8 studs on the same placeholder feet), and the skirt is Z -50 .. -118
#         (68 tall).
# Both variants replace lite-41's skirts with the same Voron-style design, drawn here, not copied (Voron's parts are
# for a 2020 frame 470 wide; this 4040 frame is 556 x 641 outside):
#  - WHITE PANELS (3 mm wall flush with each face, a 16 x 4 mm flange under the bottom extrusion, as lite-41), each with
#    hex WINDOWS: a chamfered outline filled with a honeycomb (flat-top hexes, 3 mm webs), clipped by the outline the way
#    Voron's are. The front has two windows either side of a BADGE; the sides and the rear have two each, split by a rib.
#  - An ORANGE MESH plate (2 mm, fine hexes) behind every window: the two-colour look of the references.
#  - An orange BADGE inset flush in the front panel's centre: an elongated hexagon (no logo).
#  - ORANGE CORNER blocks: an L of 3 mm walls, 56 mm along each face, with a chamfered outer edge.
#  - FEET: every skirt part keeps >= 12 mm above the board (the printer stands on its feet, never on the skirt), and has
#    an ARCH round each levelling foot (R 29 over the D50 pad, up to 6 mm above the pad), so the feet poke out.
# Checks (refuses to save on any): the outline measured; each part one valid solid; nothing overlaps the printer or each
# other; each flange touches its extrusion's underside; every part >= 1 mm from the feet's studs and pads and the
# board (the brackets are flush with the frame's faces, like the walls), and its lowest point >= 12 mm above the
# board; the outline flush with the walls above; roles; solid count.
import FreeCAD, Part, os, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "platform/render")]
import litelib, colours
from litelib import MODELS
V = FreeCAD.Vector
VAR = os.environ.get("VT350_SKIRT", "band")
assert VAR in ("band", "tall"), VAR
SRC, DST = f"{MODELS}/vt350-lite-41.FCStd", f"{MODELS}/vt350-lite-42-{VAR}.FCStd"
EXTRAS = "Enclosure extras (lite-16)"
OLD_GROUP = "Bottom skirts (lite-41)"
GROUP = f"Bottom skirts v2 (lite-42 {VAR})"
T, FL_T, FL_D = 3.0, 4.0, 16.0                     # wall, flange thickness, flange depth (as lite-41)
Z_TOP, Z_FRONT_TOP = -50.0, -51.0
DROP = {"band": 0.0, "tall": 30.0}[VAR]           # the stand (pads, board) moves down by this
BOARD_TOP0 = -100.0
FLOOR_GAP = 12.0                                   # skirt bottom above the board (the user: feet poke out)
CORNER, CHAMF = 56.0, 8.0                          # corner leg length along each face; outer vertical edge chamfer
BORDER = {"band": 7.0, "tall": 10.0}[VAR]          # white border round the windows
END_M, RIB = 50.0, 24.0                            # window margin from a panel's ends (clears the foot arches), mid rib
HEX_F, WEB = {"band": 10.0, "tall": 19.0}[VAR], 3.0
MESH_F, MESH_WEB, MESH_T, MESH_M = {"band": 5.0, "tall": 6.0}[VAR], 1.6, 2.0, 3.0
BADGE_W = 100.0
ARCH_R, ARCH_UP = 29.0, 6.0
TOL = 1e-3
LIC = "(printed ABS, vt350, GPL-3.0-or-later)"


def bx(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    lab = lambda l: next(o for o in pr.leaves if o.Label == l)
    box = lambda l: pr.shapes[lab(l).Name].BoundBox
    cmap = colours.load(f"{_REPO}/cad/render/colours.json")
    # ---- remove lite-41's skirts
    old = next(o for o in doc.Objects if o.Label == OLD_GROUP)
    gone = [o for o in old.Group]
    p.check(len(gone) == 12, f"lite-41's skirts: 12 parts ({len(gone)})")
    for o in gone: doc.removeObject(o.Name)
    doc.removeObject(old.Name)
    doc.recompute(); pr.refresh()
    n_before = len(pr.leaves)
    # ---- the stand: tall drops the pads and the board by DROP, the studs grow to reach
    pads = sorted([o for o in pr.leaves if o.Label.startswith("Levelling foot pad")], key=lambda o: o.Label)
    studs = sorted([o for o in pr.leaves if o.Label.startswith("Levelling foot") and "M8 stud" in o.Label], key=lambda o: o.Label)
    brackets = [o for o in pr.leaves if o.Label.startswith("Levelling foot") and "bracket" in o.Label]
    board = lab("Base board (18 mm, plywood/MDF, placeholder)")
    p.check(len(pads) == 4 and len(studs) == 4 and len(brackets) == 4, f"4 feet ({len(pads)} pads, {len(studs)} studs, {len(brackets)} brackets)")
    if DROP:
        def move_global(o, dz):
            par = o.getGlobalPlacement().multiply(o.Placement.inverse())
            pl = o.Placement.copy(); pl.Base = pl.Base + par.Rotation.inverted().multVec(V(0, 0, dz)); o.Placement = pl
        for o in pads + [board]: move_global(o, -DROP)
        for o in studs:
            b = pr.shapes[o.Name].BoundBox
            cx, cy = (b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2
            g = Part.makeCylinder(4, b.ZLength + DROP, V(cx, cy, b.ZMin - DROP))
            par = o.getGlobalPlacement().multiply(o.Placement.inverse())
            g.Placement = par.inverse().multiply(g.Placement)
            o.Shape = g; o.Placement = FreeCAD.Placement()
            o.Label = o.Label.replace("(placeholder)", f"(placeholder, {b.ZLength + DROP:.0f} long)")
        doc.recompute(); pr.refresh()
    board_top = pr.shapes[board.Name].BoundBox.ZMax
    p.check(abs(board_top - (BOARD_TOP0 - DROP)) < 0.01, f"board top Z {board_top:.2f} (expected {BOARD_TOP0 - DROP:.2f})")
    Z_BOT = board_top + FLOOR_GAP
    feet = []
    for o in pads:
        b = pr.shapes[o.Name].BoundBox; feet.append(((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, b.ZMax))
    p.log(f"variant {VAR}: board top {board_top:.1f}, skirt Z {Z_BOT:.1f} .. {Z_TOP:.1f} ({Z_TOP - Z_BOT:.0f} tall), feet {[(round(x), round(y)) for x, y, _ in feet]}")
    # ---- the outline, from the solids (as lite-41)
    xl = box("Left side panel (3 mm) paint, outside").XMin
    xr = box("Right side panel (3 mm) paint, outside").XMax
    yf = next(pr.shapes[o.Name].BoundBox for o in pr.leaves if o.Label.startswith("Door window (3 mm")).YMin
    rear = [o for o in pr.leaves if o.Label == "4040 (2)" and o.getParentGeoFeatureGroup() and o.getParentGeoFeatureGroup().Label == "Horizontals"]
    p.check(len(rear) == 1, f"the rear bottom 4040: {len(rear)}")
    rb = pr.shapes[rear[0].Name].BoundBox; yr = rb.YMax
    p.check(abs(xl + 523) < 0.2 and abs(xr - 33) < 0.2 and abs(yf + 118) < 0.2 and abs(yr - 520) < 0.2 and abs(rb.ZMin - Z_TOP) < 0.1,
            f"outline measured: X {xl:.1f}..{xr:.1f}, Y {yf:.1f}..{yr:.1f}; the bottom extrusions' underside Z {rb.ZMin:.1f}")
    Y0, Y1 = yf, yr + T
    faces = {
        "front": dict(wall=(xl, xr, Y0, Y0 + T), ax="x", top=Z_FRONT_TOP, inward=V(0, 1, 0)),
        "rear":  dict(wall=(xl, xr, Y1 - T, Y1), ax="x", top=Z_TOP, inward=V(0, -1, 0)),
        "left":  dict(wall=(xl, xl + T, Y0, Y1), ax="y", top=Z_TOP, inward=V(1, 0, 0)),
        "right": dict(wall=(xr - T, xr, Y0, Y1), ax="y", top=Z_TOP, inward=V(-1, 0, 0)),
    }
    # ---- keep-outs: the arches round the feet, the bracket/stud zones for the flanges
    arches = Part.makeCompound([Part.makeCylinder(ARCH_R, (z + ARCH_UP) - (board_top - 1), V(x, y, board_top - 1)) for x, y, z in feet])
    keep = Part.makeCompound([bx(pr.boxes[o.Name].XMin - 1, pr.boxes[o.Name].XMax + 1, pr.boxes[o.Name].YMin - 1,
                                 pr.boxes[o.Name].YMax + 1, -200, 0) for o in brackets + studs])
    grp = doc.addObject("App::DocumentObjectGroup", "Bottom_skirts_v2"); grp.Label = GROUP
    next(o for o in doc.Objects if o.Label == EXTRAS).addObject(grp)
    made = []
    def add(name, label, shape):
        shape = shape.removeSplitter() if shape.Solids else shape
        if len(shape.Solids) > 1:   # keep the largest only if the rest are crumbs; else refuse
            big = max(shape.Solids, key=lambda s: s.Volume)
            crumbs = [s.Volume for s in shape.Solids if s is not big]
            p.check(sum(crumbs) < 1.0, f"{label[:40]}: crumbs {crumbs[:5]} mm3")
            shape = big
        p.check(shape.isValid() and len(shape.Solids) == 1, f"{label[:40]}: one valid solid ({len(shape.Solids)}), {shape.Volume:.0f} mm3")
        o = doc.addObject("Part::Feature", name); o.Shape = shape; o.Label = label; grp.addObject(o); made.append(o); return o
    # face-local 2D -> 3D: u along the face, v = Z, w across the wall (from w0 to w1, absolute X or Y)
    def prism(face, pts_uv, w0, w1):
        if face["ax"] == "x": P = [V(u, w0, v) for u, v in pts_uv]; d = V(0, w1 - w0, 0)
        else:                 P = [V(w0, u, v) for u, v in pts_uv]; d = V(w1 - w0, 0, 0)
        return Part.Face(Part.makePolygon(P + [P[0]])).extrude(d)
    def chamfered(u0, u1, v0, v1, c):
        return [(u0 + c, v0), (u1 - c, v0), (u1, v0 + c), (u1, v1 - c), (u1 - c, v1), (u0 + c, v1), (u0, v1 - c), (u0, v0 + c)]
    def hexes(u0, u1, v0, v1, F, web):
        a = F / math.sqrt(3); du = (F + web) * math.cos(math.radians(30)); dv = F + web
        out, i, u = [], 0, u0 - du
        while u < u1 + du:
            v = v0 - dv + (dv / 2 if i % 2 else 0)
            while v < v1 + dv:
                out.append([(u + a * math.cos(math.radians(60 * k)), v + a * math.sin(math.radians(60 * k))) for k in range(6)])
                v += dv
            u += du; i += 1
        return out
    stats = {}
    for f, d in faces.items():
        x0, x1, y0, y1 = d["wall"]; n = d["inward"]; top = d["top"]
        if d["ax"] == "x": a0, a1 = x0 + CORNER, x1 - CORNER; wall = bx(a0, a1, y0, y1, Z_BOT, top); wo, wi = (y0, y1) if n.y > 0 else (y1, y0)
        else:              a0, a1 = y0 + CORNER, y1 - CORNER; wall = bx(x0, x1, a0, a1, Z_BOT, top); wo, wi = (x0, x1) if n.x > 0 else (x1, x0)
        sgn = 1 if wi > wo else -1                                 # +1: inward is +w
        if d["ax"] == "x":
            fl = bx(a0, a1, min(wi, wi + sgn * FL_D), max(wi, wi + sgn * FL_D), Z_TOP - FL_T, Z_TOP)
        else:
            fl = bx(min(wi, wi + sgn * FL_D), max(wi, wi + sgn * FL_D), a0, a1, Z_TOP - FL_T, Z_TOP)
        fl = fl.cut(keep)
        v0, v1 = Z_BOT + BORDER, top - BORDER
        c = min(8.0, (v1 - v0) / 3)
        mid = (a0 + a1) / 2
        if f == "front":
            spans = [(a0 + END_M, mid - BADGE_W / 2 - RIB / 2), (mid + BADGE_W / 2 + RIB / 2, a1 - END_M)]
        else:
            spans = [(a0 + END_M, mid - RIB / 2), (mid + RIB / 2, a1 - END_M)]
        panel = wall.fuse(fl)
        holes, meshes = [], []
        for i, (u0, u1) in enumerate(spans, 1):
            win = prism(d, chamfered(u0, u1, v0, v1, c), wo - sgn * 1, wi + sgn * 1)
            hx = Part.makeCompound([prism(d, h, wo - sgn * 1, wi + sgn * 1) for h in hexes(u0, u1, v0, v1, HEX_F, WEB)])
            holes.append(win.common(hx))
            # the mesh behind: the window outline + MESH_M, fine hexes inside it (less a 2 mm rim)
            mo = chamfered(u0 - MESH_M, u1 + MESH_M, v0 - MESH_M, v1 + MESH_M, c + MESH_M * 0.4)
            plate = prism(d, mo, wi, wi + sgn * MESH_T)
            inner = prism(d, chamfered(u0 - MESH_M + 2, u1 + MESH_M - 2, v0 - MESH_M + 2, v1 + MESH_M - 2, c), wi - sgn, wi + sgn * (MESH_T + 1))
            mh = Part.makeCompound([prism(d, h, wi - sgn, wi + sgn * (MESH_T + 1)) for h in hexes(u0 - MESH_M, u1 + MESH_M, v0 - MESH_M, v1 + MESH_M, MESH_F, MESH_WEB)])
            meshes.append((i, plate.cut(inner.common(mh))))
        panel = panel.cut(Part.makeCompound(holes)).cut(arches)
        if f == "front":
            bw, bh = BADGE_W, (v1 - v0)
            badge_uv = [(mid - bw / 2, (v0 + v1) / 2), (mid - bw / 2 + bh / 2, v0), (mid + bw / 2 - bh / 2, v0),
                        (mid + bw / 2, (v0 + v1) / 2), (mid + bw / 2 - bh / 2, v1), (mid - bw / 2 + bh / 2, v1)]
            badge = prism(d, badge_uv, wo, wo + sgn * 1.5)
            panel = panel.cut(badge)
        add("Skirt_panel", f"Skirt panel {f} {LIC}", panel)
        for i, m in meshes: add("Skirt_mesh", f"Skirt mesh {f} {i} {LIC}", m.cut(arches))
        if f == "front": add("Skirt_badge", f"Skirt badge front {LIC}", badge)
        stats[f] = dict(length=round(a1 - a0), windows=[round(u1 - u0) for u0, u1 in spans], window_h=round(v1 - v0, 1))
    # corners: an L of 3 mm walls, CORNER along each face, the outer vertical edge chamfered, the feet's arches cut out
    for nm, xo, yo in (("front-left", xl, Y0), ("front-right", xr, Y0), ("rear-left", xl, Y1), ("rear-right", xr, Y1)):
        sx = 1 if xo == xl else -1; sy = 1 if yo == Y0 else -1
        top = Z_FRONT_TOP if yo == Y0 else Z_TOP
        leg_x = bx(min(xo, xo + sx * CORNER), max(xo, xo + sx * CORNER), min(yo, yo + sy * T), max(yo, yo + sy * T), Z_BOT, top)
        leg_y = bx(min(xo, xo + sx * T), max(xo, xo + sx * T), min(yo + sy * T, yo + sy * CORNER), max(yo + sy * T, yo + sy * CORNER), Z_BOT, top)
        # the chamfer: fill the inside of the corner with a 45-degree web CHAMF across, then cut the outer edge off
        corner = leg_x.fuse(leg_y)
        tri = Part.Face(Part.makePolygon([V(xo, yo + sy * CHAMF, Z_BOT - 1), V(xo + sx * CHAMF, yo, Z_BOT - 1), V(xo, yo, Z_BOT - 1),
                                          V(xo, yo + sy * CHAMF, Z_BOT - 1)])).extrude(V(0, 0, top - Z_BOT + 2))
        web = Part.Face(Part.makePolygon([V(xo, yo + sy * (CHAMF + T * 1.414), Z_BOT), V(xo + sx * (CHAMF + T * 1.414), yo, Z_BOT),
                                          V(xo, yo, Z_BOT), V(xo, yo + sy * (CHAMF + T * 1.414), Z_BOT)])).extrude(V(0, 0, top - Z_BOT))
        corner = corner.fuse(web).cut(tri).cut(arches)
        add("Skirt_corner", f"Skirt corner {nm} {LIC}", corner)
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
    for o in made:
        if not o.Label.startswith("Skirt panel"): continue
        f = o.Label.split()[2]
        ex = [x for x in pr.leaves if x.Label == under[f] and pr.boxes[x.Name].ZMin < -49]
        dd = min(pr.shapes[o.Name].distToShape(pr.shapes[x.Name])[0] for x in ex)
        p.check(dd < 0.01, f"skirt panel {f}: its flange touches the underside of {under[f]} (gap {dd:.3f})")
    # the brackets sit flush with the 4040s' outer faces, so a wall on that face touches them as it touches the frame
    # (no_overlap above covers them); the parts that move with adjustment, the studs and pads, and the board need air
    stand = pads + studs + [board]
    for o in made:
        dd = min(pr.shapes[o.Name].distToShape(pr.shapes[x.Name])[0] for x in stand)
        zlow = pr.boxes[o.Name].ZMin
        p.check(dd >= 1.0, f"{o.Label[:28]}: clears the studs, pads and board by {dd:.1f} mm")
        p.check(zlow >= board_top + FLOOR_GAP - TOL, f"{o.Label[:28]}: lowest Z {zlow:.1f}, {zlow - board_top:.1f} above the board (>= {FLOOR_GAP:.0f})")
    allb = pr.shapes[made[0].Name].BoundBox
    for o in made[1:]: allb.add(pr.boxes[o.Name])
    p.check(abs(allb.XMin - xl) < TOL and abs(allb.XMax - xr) < TOL and abs(allb.YMin - yf) < TOL and abs(allb.YMax - Y1) < TOL,
            f"the skirts' outline X {allb.XMin:.1f}..{allb.XMax:.1f}, Y {allb.YMin:.1f}..{allb.YMax:.1f}: flush with the walls above")
    def gpath(o):
        r_, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r_.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r_))
    roles = {}
    for o in made: roles.setdefault(o.Label.split()[1], set()).add(colours.role_of(cmap, o.Label, gpath(o), "Default"))
    p.check(roles == {"panel": {"printed"}, "mesh": {"accent"}, "badge": {"accent"}, "corner": {"accent"}}, f"roles {roles}")
    p.check(len(pr.leaves) == n_before + len(made) and len(made) == 4 + 8 + 1 + 4, f"solids: {n_before} + {len(made)} = {len(pr.leaves)} (17 parts)")
    p.dump({"variant": VAR, "drop": DROP, "board_top": board_top, "z": [Z_BOT, Z_TOP], "faces": stats,
            "outline": [round(xl, 1), round(xr, 1), round(yf, 1), round(Y1, 1)],
            "volumes_mm3": {o.Label.split(" (")[0]: round(pr.shapes[o.Name].Volume) for o in made}})
    p.finish([(doc, DST)])


litelib.Pass(f"lite42_skirts_{VAR}").run(main)
