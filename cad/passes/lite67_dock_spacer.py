# GUI pass: vt350-lite-66 -> vt350-lite-67   (headless = dry run, never saves)   vt350#59
# The dock-screw bosses (lite-23) are cut off the 4010 duct on the duct's print face, and the cut-off pieces become a
# separate printed spacer (owner, 2026-11-17: "cut each of the bosses on the same plane as the side of the cowl (the
# side that's down on the print plate); the remaining piece is essentially a spacer"). So the duct prints as DW-Tas
# intends, flat on that face, with no supports, and so does the spacer. Design recorded on vt350#59.
#
# Per remixed duct (the Left head's left duct, the Right head's right duct; the docked heads link to them):
#  1. The print face: the duct's largest planar face, 10 deg off the screw axes. Everything is on its inner side
#     except the three bosses.
#  2. Duct = the duct on the inner side of that plane. What stays of each boss is a stub flush with the print face.
#     Under a boss the duct's outside angles away from the plane (the rear-bottom boss worst, owner 2026-11-17), so
#     each gap between the plane and the duct, inside the boss's footprint column, is filled: only gap pieces that open
#     onto the cut plane and end on duct material within FILL_DEPTH (a piece that runs to the depth limit runs past the
#     duct's edge, and is left out; a piece that doesn't open onto the plane is the air channel, and is left out).
#  3. Heat-set inserts move into the duct behind the cut for the two top bosses: a Voron M3 pocket (dia 4.8 x 4.4)
#     from the cut plane along the screw axis, with >= FLOOR mm of duct beyond it at every sample point. The dock
#     screw goes through the spacer into it, so the dock screw clamps the spacer. The rear-bottom boss has too little
#     duct behind it (5.2 mm), so its insert stays in the spacer at the dock face, as in lite-23, and the spacer (one
#     piece, held by the two top screws) carries it.
#  4. Spacer = each boss between the plane and its dock face (a wedge: square to the screw at the dock end, 10 deg at
#     the duct end), joined by a WEB mm web on the plane (the convex hull of the three boss circles), so the wedges
#     can't turn and the piece prints flat on that face. M3 clearance holes for the top screws; the rear-bottom wedge
#     keeps lite-23's insert pocket + screw tail. Same material card and colour as the duct.
#  5. The docked heads' copies: one App::Link to the spacer beside each link to the duct, with the duct link's
#     placement.
# Checks (refuses to save on any):
#  - two remixed ducts, three boss axes each, the print face found; duct and spacer each one valid solid;
#  - every pocket in material (but the 0.6 mm lead-in above the cut plane), floor >= FLOOR at every sample point;
#  - the fill is open to the plane and ends on duct material (never at FILL_DEPTH);
#  - every spacer copy sits where its duct copy says (box agreement), one per duct copy;
#  - no new overlap between any duct or spacer copy and any other part (against lite-66's overlaps of the duct);
#  - every other solid's box unchanged; solid count +5 (the five spacers);
#  - AC7: each carried head's centre of mass moves <= COM_LIMIT mm in X (owner's limit pending; 0.5 proposed).
import FreeCAD, Part, math, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo, matlib
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-66.FCStd", f"{MODELS}/vt350-lite-67.FCStd"
CARDS = os.path.join(_REPO, "cad/materials")
DUCTS = {"Left": "[a]_Duct-4010-left MadMax dock bosses (remix, CC BY-NC-SA 4.0)",
         "Right": "[a]_Duct-4010-right MadMax dock bosses (remix, CC BY-NC-SA 4.0)"}
HEADS = {"Left": "Left Toolhead", "Right": "Right Toolhead"}
PLATES = {"Left": ("Left Dock", ("Plate", "Plate Back")), "Right": ("Right Dock", ("Plate(Mirror)", "Plate Back(Mirror)"))}
TUBES = ("Bowden Left", "Bowden Right")
SPACER = "[a]_Dock spacer {side} (cut from the duct's dock bosses, CC BY-NC-SA 4.0)"
BOSS_R, POCKET, TAIL = 4.0, (2.4, 4.4), 1.45     # lite-23's boss and Voron M3 insert pocket; the screw tail radius
CLEAR_R = 1.7                                     # M3 clearance
LEAD = 0.6                                        # pocket lead-in above the cut plane (the plane is 10 deg to the axis)
FLOOR = 1.0                                       # mm of duct beyond a pocket
FILL_DEPTH = 7.0                                  # the deepest the duct falls away under a boss (6.8 measured, #59)
WEB = 2.0                                         # spacer web thickness
INTAKE_CLEAR, RING = 1.0, 4.0                     # the web keeps this far off the 4010 intake; the ring round it
COM_LIMIT = 0.5                                   # mm, AC7 (proposed)
DEFAULT_RHO = 1.27e-3                             # g/mm3: Default parts as PETG, as toolhead_com's lower bound


def parent_group(o):
    return next(x for x in o.InList if o in (getattr(x, "Group", None) or []))


def to_local(shape, pl):
    """A container-frame shape -> the same shape stored under placement pl (so the object keeps pl). copy=True bakes
    the transform into the geometry; copy=False only sets the shape's location, which the placement then replaces
    (LESSONS.md)."""
    s = shape.copy(); s.transformShape(pl.inverse().toMatrix(), True, False); s.Placement = pl
    return s


def hull2d(pts):
    P = sorted(set(pts))
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def rho(o):
    sm = getattr(linkgeo.link_target(o), "ShapeMaterial", None)
    if sm is None or sm.Name == "Default": return DEFAULT_RHO
    return float(sm.PhysicalProperties["Density"].split()[0]) * 1000    # kg/mm^3 -> g/mm3


def group_paths(doc):
    """{Name: labels of its Group parents}: membership as cad/studies/toolhead_com.py counts it (InListRecursive
    would also count a part in every head whose links point at it)."""
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, "Group", None) or []): par.setdefault(k.Name, o)
    def path(o):
        r, q = [], par.get(o.Name)
        while q is not None: r.append(q.Label); q = par.get(q.Name)
        return r
    return {o.Name: path(o) for o in doc.Objects}


def head_com_x(pr, side):
    """(mass g, CoM X) of a carried tool as toolhead_com.py's AC2 line: the head without its bowden tube, plus its
    Plate, Plate Back and their magnets; Default parts as PETG. Only X differences are used (the head isn't moved)."""
    G = group_paths(pr.doc); dock, plates = PLATES[side]
    m = mx = 0.0
    for o in pr.leaves:
        g = G.get(o.Name, [])
        if getattr(o, "StandInFor", ""): continue
        mine = (HEADS[side] in g and o.Label not in TUBES) or (dock in g and (o.Label in plates or any(
            o.Label.startswith(f"MadMax magnet 6x3 N52 (plate {l}) ") for l in plates)))
        if not mine: continue
        for s in pr.shapes[o.Name].Solids:
            w = s.Volume * rho(o); m += w; mx += w * s.CenterOfMass.x
    return m, mx / m


def remix(p, side, t):
    """(new duct, spacer, info) in t's container frame."""
    S = t.Shape.copy()
    F = max((f for f in S.Faces if f.Surface.__class__.__name__ == "Plane"), key=lambda f: f.Area)
    u0, u1, v0, v1 = F.ParameterRange
    n = F.normalAt((u0 + u1) / 2, (v0 + v1) / 2); c = F.CenterOfMass
    axes = sorted({(round(f.Surface.Center.y, 3), round(f.Surface.Center.z, 3)) for f in S.Faces
                   if f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - BOSS_R) < 1e-6
                   and abs(abs(f.Surface.Axis.x) - 1) < 1e-6})
    ang = math.degrees(math.acos(abs(n.x)))
    p.check(len(axes) == 3, f"{side}: three boss axes ({axes})")
    p.check(F.Area > 1000 and 5 < ang < 15, f"{side}: print face {F.Area:.0f} mm2, {ang:.2f} deg off the screw axes")
    if p.errs: return None
    s_out = -1 if n.x < 0 else 1
    d = V(-s_out, 0, 0)                                       # along a screw, into the duct
    xface = S.BoundBox.XMin if s_out < 0 else S.BoundBox.XMax
    u = n.cross(V(0, 0, 1)); u.normalize(); w = n.cross(u); w.normalize()
    plane = Part.makePlane(600, 600, c - u * 300 - w * 300, n, u)
    hin, hout = plane.extrude(n * -200), plane.extrude(n * 200)
    cap = Part.makePlane(600, 600, c - u * 300 - w * 300 - n * FILL_DEPTH, n, u).extrude(n * FILL_DEPTH)
    p.check(hin.isInside(c - n, 1e-6, True) and S.common(hout).Volume < 0.12 * S.Volume,
            f"{side}: only the bosses outside the print face ({S.common(hout).Volume:.1f} of {S.Volume:.1f} mm3)")
    hits = {}
    for a in axes:
        p0 = V(xface, *a); hits[a] = (p0, p0 + d * ((c - p0).dot(n) / d.dot(n)))
    front = max(axes, key=lambda a: (hits[a][1] - hits[a][0]).Length)            # the longest wedge
    names = {a: "front-top" if a == front else ("rear-top" if abs(a[0] - front[0]) < 1e-3 else "rear-bottom") for a in axes}
    p.check(sorted(names.values()) == ["front-top", "rear-bottom", "rear-top"], f"{side}: bosses named {names}")
    duct = S.common(hin)
    fills, info = [], {"bosses": {}}
    for a in axes:
        p0, hit = hits[a]
        col = Part.Face(Part.Wire(Part.makeCircle(BOSS_R, hit, d))).extrude(d * 12.0)
        kept = left_open = 0.0
        for g in col.common(hin).common(cap).cut(S).Solids:
            if g.Volume < 1e-3: continue
            deep = max(abs((v.Point - c).dot(n)) for v in g.Vertexes)
            if g.distToShape(plane)[0] > 1e-4: continue                        # enclosed: the air channel
            if deep > FILL_DEPTH - 0.01: left_open += g.Volume; continue          # runs past the duct's edge
            fills.append(g); kept += g.Volume
        info["bosses"][names[a]] = {"axis": a, "spacer_mm": round((hit - p0).Length, 2), "fill_mm3": round(kept, 1),
                                    "left_open_mm3": round(left_open, 1)}
    duct = duct.fuse(fills).removeSplitter() if fills else duct
    pockets = []
    for a in axes:
        if names[a] == "rear-bottom": continue
        p0, hit = hits[a]
        pk = Part.makeCylinder(POCKET[0], POCKET[1] + LEAD, hit - d * LEAD, d); pockets.append(pk)
        air = pk.cut(duct).Volume; lead = math.pi * POCKET[0] ** 2 * LEAD
        bot = hit + d * (POCKET[1] + FLOOR)
        ring = [bot + (V(0, 1, 0) * math.cos(k * math.pi / 6) + V(0, 0, 1) * math.sin(k * math.pi / 6)) * r
                for k in range(12) for r in (0.0, 1.2, POCKET[0])]
        ok = sum(duct.isInside(q, 1e-6, True) for q in ring)
        p.check(air < lead * 1.1, f"{side} {names[a]}: pocket in material (in air {air:.2f} mm3, lead-in {lead:.2f})")
        p.check(ok == len(ring), f"{side} {names[a]}: >= {FLOOR} mm of duct beyond the pocket at {ok}/{len(ring)} points")
    duct = duct.cut(pockets).removeSplitter()
    wedges = [Part.makeCylinder(BOSS_R, (hits[a][1] - hits[a][0]).Length + 3, hits[a][0], d).common(hout) for a in axes]
    # the blower's intake: the closed circle in the print face (r 15.1); the bosses sit round it, so a web straight
    # between them would cover it. The web is the hull of the three boss circles AND a ring round the intake, minus
    # the intake (+ INTAKE_CLEAR): the ring keeps the three wedges one piece.
    circ = [e for wi in F.Wires for e in wi.Edges if e.Curve.__class__.__name__ == "Circle" and e.isClosed() and e.Curve.Radius > 10]
    p.check(len(circ) == 1, f"{side}: one intake circle in the print face ({[round(e.Curve.Radius, 2) for e in circ]})")
    if len(circ) != 1: return None
    ic, ir = circ[0].Curve.Center, circ[0].Curve.Radius
    pts = []
    def ring_pts(centre, r, k_n=72):
        for k in range(k_n):
            q = centre + (u * math.cos(2 * k * math.pi / k_n) + w * math.sin(2 * k * math.pi / k_n)) * r
            pts.append((round((q - c).dot(u), 6), round((q - c).dot(w), 6)))
    for a in axes:
        hit = hits[a][1]; ring_pts(hit - n * (hit - c).dot(n), BOSS_R)
    ring_pts(ic, ir + INTAKE_CLEAR + RING, 144)
    poly = [c + u * x + w * y for x, y in hull2d(pts)]
    hole = Part.Face(Part.Wire(Part.makeCircle(ir + INTAKE_CLEAR, ic, n)))
    web = Part.Face(Part.makePolygon(poly + [poly[0]])).cut(hole).extrude(n * WEB)
    sp = wedges[0].fuse(wedges[1:] + [web]).removeSplitter()
    holes = []
    for a in axes:
        p0, hit = hits[a]
        if names[a] == "rear-bottom":
            holes += [Part.makeCylinder(POCKET[0], POCKET[1] + 0.01, p0 - d * 0.01, d), Part.makeCylinder(TAIL, 40, p0, d)]
        else:
            holes.append(Part.makeCylinder(CLEAR_R, 40, p0 - d, d))
    sp = sp.cut(holes).removeSplitter()
    tube = Part.makeCylinder(ir + INTAKE_CLEAR - 0.01, 60, ic - n * 30, n)
    p.check(sp.common(tube).Volume < 1e-6, f"{side} spacer: the 4010 intake (r {ir:.2f}) stays open, +{INTAKE_CLEAR} mm")
    for nm, s in (("duct", duct), ("spacer", sp)):
        p.check(s.isValid() and len(s.Solids) == 1, f"{side} {nm}: one valid solid ({len(s.Solids)}, valid {s.isValid()})")
    bed = max((f for f in sp.Faces if f.Surface.__class__.__name__ == "Plane"), key=lambda f: f.Area)
    side_ok = all((v.Point - c).dot(n) > -1e-4 for v in sp.Vertexes)
    p.check(side_ok and abs((bed.CenterOfMass - c).dot(n)) < 1e-4,
            f"{side} spacer: prints flat on the cut plane (bed face {bed.Area:.0f} mm2, nothing behind it)")
    info.update(duct_mm3=(round(S.Volume, 1), round(duct.Volume, 1)), spacer_mm3=round(sp.Volume, 1),
                web_mm2=round(bed.Area, 1), print_face_deg=round(ang, 2))
    return duct, sp, info


def main(p):
    mm = matlib.use_dir(CARDS)
    pr = p.open(SRC); doc = pr.doc
    P = {o.Name: [g.Label for g in o.InListRecursive] for o in pr.leaves}
    targets = {}
    for side, lab in DUCTS.items():
        c = [o for o in doc.getObjectsByLabel(lab) if o.TypeId == "Part::Feature"]
        p.check(len(c) == 1, f"{side}: one duct {lab!r} ({len(c)})")
        if len(c) == 1: targets[side] = c[0]
    if p.errs: return p.finish([])
    copies = {side: [o for o in pr.leaves if linkgeo.link_target(o).Name == t.Name] for side, t in targets.items()}
    p.log("duct copies:", {s: [o.Label for o in v] for s, v in copies.items()})
    p.check(sum(len(v) for v in copies.values()) == 5, f"five duct copies ({sum(len(v) for v in copies.values())})")
    mine0 = {o.Name for v in copies.values() for o in v}
    pairs0 = [(o.Name, b.Name) for o in pr.leaves if o.Name in mine0 for b in pr.leaves
              if b.Name not in mine0 and pr.shapes[o.Name].BoundBox.intersect(pr.shapes[b.Name].BoundBox)]
    v0 = dict(zip(pairs0, p.volumes([(pr.shapes[a], pr.shapes[b]) for a, b in pairs0])))
    base = {}
    for (a, b), v in v0.items():
        if v > 1e-3: base[b] = max(base.get(b, 0.0), v)
    p.log("lite-66 overlaps of the duct copies:", {doc.getObject(b).Label: round(v, 2) for b, v in base.items()})
    com0 = {s: head_com_x(pr, s) for s in HEADS}
    box0 = {n: s.BoundBox for n, s in pr.shapes.items()}
    n0 = len(pr.leaves)
    made = {}
    for side, t in targets.items():
        r = remix(p, side, t)
        if r is None: return p.finish([])
        made[side] = r
        p.log(f"{side}: {r[2]}")
    if p.errs: return p.finish([])
    gui = FreeCAD.GuiUp
    new_links = []
    for side, t in targets.items():
        duct, sp, info = made[side]
        pl = FreeCAD.Placement(t.Placement)
        ap = list(t.ViewObject.ShapeAppearance) if gui and hasattr(t.ViewObject, "ShapeAppearance") else None
        t.Shape = to_local(duct, pl)
        p.check(t.Placement.isSame(pl, 1e-9), f"{side}: the duct keeps its placement")
        s = doc.addObject("Part::Feature", "DockSpacer"); s.Shape = to_local(sp, pl)
        parent_group(t).addObject(s); s.Placement = pl
        s.Label = SPACER.format(side=side.lower())
        s.ShapeMaterial = t.ShapeMaterial
        if ap is not None: t.ViewObject.ShapeAppearance = ap; s.ViewObject.ShapeAppearance = ap
        for o in copies[side]:
            if o.Name == t.Name: continue
            k = doc.addObject("App::Link", "DockSpacerLink"); k.setLink(s); k.Placement = o.Placement
            parent_group(o).addObject(k)
            head = next(g for g in P[o.Name] if g.startswith("Toolhead slot"))
            k.Label = SPACER.format(side=side.lower()) + f" {head}"
            new_links.append((o.Name, k.Name, s.Name))
    doc.recompute(); pr.refresh()
    P = {o.Name: [g.Label for g in o.InListRecursive] for o in pr.leaves}
    spacers = [o for o in pr.leaves if linkgeo.link_target(o).Label.startswith("[a]_Dock spacer ")]
    p.check(len(pr.leaves) == n0 + 5 and len(spacers) == 5, f"solids {n0} -> {len(pr.leaves)}, five spacers ({len(spacers)})")
    # each spacer copy where its duct copy says: the link's offset from its target equals the duct link's
    for dn, kn, sn in new_links:
        dl, kl, tg = doc.getObject(dn), doc.getObject(kn), doc.getObject(sn)
        td = linkgeo.link_target(dl)
        exp = linkgeo.gplace(dl).multiply(linkgeo.gplace(td).inverse())
        got = linkgeo.gplace(kl).multiply(linkgeo.gplace(tg).inverse())
        p.check(exp.isSame(got, 1e-6), f"{kl.Label}: placed as its duct copy {dl.Label}")
    # no new overlap
    mine = {o.Name for o in pr.leaves if o.Name in mine0 or o in spacers}
    pairs = [(a.Name, b.Name) for a in pr.leaves if a.Name in mine for b in pr.leaves
             if b.Name not in mine and pr.shapes[a.Name].BoundBox.intersect(pr.shapes[b.Name].BoundBox)]
    vols = dict(zip(pairs, p.volumes([(pr.shapes[a], pr.shapes[b]) for a, b in pairs])))
    worse = sorted(((v, doc.getObject(a).Label, doc.getObject(b).Label) for (a, b), v in vols.items()
                    if v > base.get(b, 0.0) + 0.01), reverse=True)
    p.check(not worse, f"no new overlap of a duct or spacer copy ({len(worse)}: {[(round(v, 2), a, b) for v, a, b in worse[:4]]})")
    moved = [doc.getObject(k).Label for k, b in box0.items() if k not in mine0
             and (k not in pr.shapes or not pr.shapes[k].BoundBox.isInside(b) or not b.isInside(pr.shapes[k].BoundBox))]
    p.check(not moved, f"every other solid's box unchanged ({len(moved)}: {moved[:5]})")
    # AC7
    com = {}
    for s in HEADS:
        m1, x1 = head_com_x(pr, s); m0, x0 = com0[s]
        com[s] = {"mass_g": (round(m0, 2), round(m1, 2)), "com_x": (round(x0, 3), round(x1, 3)), "shift_mm": round(x1 - x0, 3)}
        p.check(abs(x1 - x0) <= COM_LIMIT, f"AC7 {HEADS[s]}: mass {m0:.1f} -> {m1:.1f} g, CoM X {x0:.3f} -> {x1:.3f} "
                                           f"({x1 - x0:+.3f} mm, limit {COM_LIMIT})")
    p.dump({side: made[side][2] for side in made} | {"com": com})
    return p.finish([(doc, DST)])


litelib.Pass("lite67_dock_spacer").run(main)
