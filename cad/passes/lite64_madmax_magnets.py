# GUI pass: vt350-lite-63 -> vt350-lite-64   (headless = dry run, never saves)   vt350#60
# MadMax's tool-holding magnets, which the model didn't have (owner, 2026-11-17: "you need to add magnets for the
# weight"). MadMax BOM.md (zruncho3d/madmax@277a63c): carriage "6x 6x3mm N52 (Neodymium) magnets", toolhead plate
# "6x 6x3mm N52 magnets"; "push ... they should press-fit flush" (INSTRUCTIONS.md). Each MadMax carriage copy (the
# gantry's, the docks') and each tool plate copy has exactly six pockets of radius 3.05 about 3 mm deep (2x2 for the
# toolhead + the lower 2); this puts one 6x3 magnet in each, its outer face flush with the pocket's opening, as a new
# Part::Feature next to the part in its group (so it moves with it), with the NdFeB N52 card (cad/materials) and a
# nickel colour. The docks' own 3-4 magnets aren't carried and their pockets aren't identified: not added.
# Checks (refuses to save on any):
#  - every carriage and plate copy found, six pockets each (radius 3.05 +- 0.02, depth 2.9..3.05, all one axis);
#  - each magnet inside its own part's pocket (overlap with that part only where the pocket is shallower than 3 mm,
#    at most PROUD_MM3) and clear of every other solid (no overlap);
#  - every other solid's box unchanged; the new solids are exactly 6 per part, valid, 84.8 mm3 each;
#  - the NdFeB card found; each magnet's material is it.
import FreeCAD, Part, os, sys, re, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo, matlib
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-63.FCStd", f"{MODELS}/vt350-lite-64.FCStd"
CARDS = os.path.join(_REPO, "cad/materials")
NDFEB = "NdFeB N52 magnet"
R, H = 3.0, 3.0                       # 6x3 mm
POCKET_R, POCKET_TOL = 3.05, 0.02
DEPTH = (2.9, 3.25)                   # along the axis: the lower pair are 3.2 (a notch at the floor), the 2x2 3.0
PROUD_MM3 = 2.0                       # a 2.94-deep pocket leaves 0.06 mm of a flush 3 mm magnet in its floor: 1.7 mm3
NICKEL = (0.72, 0.73, 0.75)
CARRIAGE = re.compile(r"^COMPOUND\d*$")
PLATE = re.compile(r"^Plate(\(Mirror\))?\d*$")        # the plate, not "Plate Back"


def pockets(s):
    """[(axis point at the opening, inward unit axis, depth)] of the r~3.05, ~3 mm deep cylindrical pockets of s.
    The floor is the end with a small flat face square to the axis and centred on it (an annulus round the push-out
    hole: MadMax INSTRUCTIONS.md, "Magnet removal ... from the backside"); the opening is the other end."""
    out = []
    for f in s.Faces:
        su = f.Surface
        if not isinstance(su, Part.Cylinder) or abs(su.Radius - POCKET_R) > POCKET_TOL: continue
        a = V(su.Axis); a.normalize()
        ts = [(v.Point - su.Center).dot(a) for v in f.Vertexes] or [0]
        t0, t1 = min(ts), max(ts)
        if not (DEPTH[0] <= t1 - t0 <= DEPTH[1]): continue
        ends = []
        for g in s.Faces:
            if not isinstance(g.Surface, Part.Plane) or g.Area > math.pi * POCKET_R ** 2 + 0.5: continue
            n = g.normalAt(0, 0)
            if abs(n.dot(a)) < 0.999: continue
            c = g.CenterOfMass; t = (c - su.Center).dot(a)
            off = (c - su.Center - a * t).Length
            if off < 1.5 and min(abs(t - t0), abs(t - t1)) < 0.25: ends.append(t)   # a notched floor is off-centre
        at0 = any(abs(t - t0) < 0.25 for t in ends); at1 = any(abs(t - t1) < 0.25 for t in ends)
        if at0 == at1: continue
        floor_t, open_t = (t0, t1) if at0 else (t1, t0)
        inward = a * (1 if floor_t > open_t else -1)
        opening = su.Center + a * open_t
        if not any((opening - q).Length < 0.05 for q, _, _ in out): out.append((opening, inward, abs(t1 - t0)))
    return out


def main(p):
    mm = matlib.use_dir(CARDS)
    try: card = matlib.card(mm, NDFEB)
    except Exception as e: p.check(False, f"card {NDFEB!r}: {e}"); return p.finish([])
    pr = p.open(SRC); doc = pr.doc
    n0 = len(pr.leaves)
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, "Group", []) or []): par.setdefault(k.Name, o)
    def path(o):
        r, q = [], par.get(o.Name)
        while q is not None: r.append(q.Label); q = par.get(q.Name)
        return r
    hosts = [o for o in pr.leaves if (CARRIAGE.match(o.Label) and any(g.startswith("MadMaxCarriage") for g in path(o)))
             or (PLATE.match(o.Label) and any(g.startswith("Plate Assembly") for g in path(o)))]
    p.log(f"{len(hosts)} carriage/plate copies: " + ", ".join(f"{o.Label} ({o.TypeId.split('::')[1]}) in {path(o)[1] if len(path(o)) > 1 else path(o)[0]}" for o in hosts))
    p.check(sum(1 for o in hosts if CARRIAGE.match(o.Label)) >= 3 and sum(1 for o in hosts if PLATE.match(o.Label)) >= 5,
            f"every carriage (>= 3) and tool plate (>= 5) copy found")
    plan = []
    for o in hosts:
        s = pr.shapes[o.Name]
        pk = pockets(s)
        axes = {tuple(round(x, 3) for x in a) for _, a, _ in pk}
        p.check(len(pk) == 6 and len(axes) == 1, f"{o.Label} ({o.Name}): {len(pk)} pockets (want 6), axes {sorted(axes)}")
        for i, (op, a, d) in enumerate(pk):
            m = Part.makeCylinder(R, H, op, a)          # from the opening, 3 mm in: flush outside
            plan.append((o, i + 1, m, d))
    if p.errs: return p.finish([])
    # fit: inside its own pocket, clear of everything else
    by = {o.Name: s for o, s in ((o, pr.shapes[o.Name]) for o in pr.leaves)}
    for o, i, m, d in plan:
        own = m.common(by[o.Name]).Volume
        p.check(own <= PROUD_MM3 + 1e-6 and (own < 1e-3 or d < H), f"{o.Label} magnet {i}: {own:.3f} mm3 in its own part (pocket {d:.2f} deep)")
    hit = []
    for o, i, m, d in plan:
        mb = m.BoundBox
        for n, s in by.items():
            if n == o.Name or not s.BoundBox.intersect(mb): continue
            v = m.common(s).Volume
            if v > 1e-3: hit.append(f"{o.Label} magnet {i} x {doc.getObject(n).Label} {v:.3f} mm3")
    p.check(not hit, f"every magnet clear of every other solid ({len(hit)}: {hit[:5]})")
    if p.errs: return p.finish([])
    box0 = {n: s.BoundBox for n, s in pr.shapes.items()}
    gui = FreeCAD.GuiUp
    made = []
    for o, i, m, d in plan:
        g = par.get(o.Name)
        kind = "carriage" if CARRIAGE.match(o.Label) else "plate"
        n = doc.addObject("Part::Feature", "MadMaxMagnet")
        n.Label = f"MadMax magnet 6x3 N52 ({kind} {o.Label}) {i}"
        # global -> the containers' frame (the new object sits in o's group)
        cg = linkgeo.gplace(o).multiply(FreeCAD.Placement(o.Placement).inverse()) if o.TypeId != "App::Link" else \
             linkgeo.gplace(o).multiply(FreeCAD.Placement(o.Placement).inverse())
        loc = m.copy(); loc.transformShape(cg.inverse().toMatrix(), True)
        n.Shape = loc
        if g is not None: g.addObject(n)
        n.ShapeMaterial = card
        if gui and hasattr(n.ViewObject, "ShapeAppearance"):
            ap = n.ViewObject.ShapeAppearance
            for x in ap: x.DiffuseColor = NICKEL + (1.0,) if len(x.DiffuseColor) == 4 else NICKEL
            n.ViewObject.ShapeAppearance = ap
        made.append((n, m))
    doc.recompute(); pr.refresh()
    moved = [doc.getObject(n).Label for n, b in box0.items()
             if max(abs(a - c) for a, c in zip((pr.shapes[n].BoundBox.XMin, pr.shapes[n].BoundBox.YMin, pr.shapes[n].BoundBox.ZMin,
                                                pr.shapes[n].BoundBox.XMax, pr.shapes[n].BoundBox.YMax, pr.shapes[n].BoundBox.ZMax),
                                               (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))) > 1e-9]
    p.check(not moved, f"every other solid's box unchanged ({len(moved)}: {moved[:5]})")
    p.check(len(pr.leaves) == n0 + len(plan) == n0 + 6 * len(hosts), f"solids {len(pr.leaves)} = {n0} + {len(plan)}")
    vol = math.pi * R * R * H
    bad = [n.Label for n, m in made if n.Name not in pr.shapes or abs(pr.shapes[n.Name].Volume - vol) > 0.01
           or not pr.shapes[n.Name].isValid() or (pr.shapes[n.Name].BoundBox.Center - m.BoundBox.Center).Length > 1e-6
           or getattr(n.ShapeMaterial, "Name", "") != NDFEB]
    p.check(not bad, f"each magnet valid, {vol:.1f} mm3, where planned, NdFeB ({len(bad)} not: {bad[:5]})")
    rho = 7.6e-3
    p.log(f"magnets: {len(made)} x {vol * rho:.3f} g; carried per tool (carriage 6 + plate 6) {12 * vol * rho:.2f} g")
    p.dump({"hosts": [o.Label for o in hosts], "magnets": len(made), "g_each": round(vol * rho, 3)})
    return p.finish([(doc, DST)])


litelib.Pass("lite64_madmax_magnets").run(main)
