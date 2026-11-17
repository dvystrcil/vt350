# GUI pass: vt350-lite-61 -> vt350-lite-62   (headless = dry run, never saves)   vt350#114 AC4
# The MadMax carriage's underside sits 1.665 mm above the carried nozzle tip, lower than the Beacon's coil face
# (+2.60): two pads, the bottoms of the Beacon pocket's side walls, are the lowest thing after the nozzle, so a tilted
# plate, a curled edge or a blob meets them first (at ~3 deg). Owner, 2026-11-17: trim them if nothing else on the
# toolhead depends on them. Trim: all carriage material below TRIM above the carried nozzle tip goes (0.4 mm above the
# Beacon face, so the Beacon is the lowest part on the carriage), on the gantry carriage AND both docks' carriage
# copies (the same part at pickup; the same cut moved by T, as lite24_beacon.py does). On lite-61 the Left copy is an
# App::Link to the gantry carriage (lite-51), so it follows the trim; the check confirms its shape.
# Checks (refuses to save on any):
#  - the carriage, both copies, the Beacon and both heads' nozzles where expected; carried tip and Beacon face heights;
#  - the cut takes exactly the two pads (2 pieces, NEAR the expected volume), the same volume from each copy;
#  - each trimmed part valid, same solid count; its lowest point now TRIM above the tip, and the Beacon face below it;
#  - nothing comes within CLEAR_MIN of the removed volume: every part not on a head (Beacon, MGN12 block, screws,
#    belts, gantry), each head carried, each dock's own parts against its copy's cut. So the pads hold nothing,
#    locate nothing, and nothing rests on them; the Beacon's board seat (the pocket ceiling) and its two M3 pilot holes
#    are far above the cut;
#  - every other solid unchanged (box), solid count unchanged;
#  - the printable STL's frame: the untrimmed carriage mapped into the committed STL's frame matches its vertices.
# Writes (GUI run only) the trimmed printable carriage over the committed 9 mm-belt STL, in the same frame.
import FreeCAD, Part, Mesh, MeshPart, os, sys
import numpy as np
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-61.FCStd", f"{MODELS}/vt350-lite-62.FCStd"
STL = f"{_REPO}/cad/derived/madmax-andrewmcgr-carriage-beacon/MadMaxCarriage Beacon RevH pocket 9mm belts.stl"
TRIM = 3.0                   # mm above the carried nozzle tip (Beacon face 2.6; Contact: "only around 3mm higher")
CLEAR_MIN = 1.0              # nothing else within this of the removed volume
TIP_Z, BEACON_DZ = 380.485, 2.60     # carried nozzle tip, Beacon face above it (lite-24, carriage_clearance.log)
CUT_VOL = 105.2              # two pads of 52.6 mm3 (trim check, 2026-11-17)
TOL = 0.05
CARRIAGE = ("COMPOUND", "Carriage (1)")
COPIES = {"Left": ("COMPOUND003", "Left Dock"), "Right": ("COMPOUND004", "Right Dock")}
HEADS = {"Left": ("Left Toolhead", "Left Dock", ["Plate", "Plate Back"]),
         "Right": ("Right Toolhead", "Right Dock", ["Plate(Mirror)", "Plate Back(Mirror)"])}
NOZZLE, BEACON = "E3D v6 HotEnd - Nozzle", "Beacon RevH"


def com(s):
    vs = [(x.Volume, x.CenterOfMass) for x in s.Solids]; tv = sum(v for v, _ in vs)
    return sum((c * (v / tv) for v, c in vs), V(0, 0, 0))


def matrix(rows, t):
    M = FreeCAD.Matrix()
    (M.A11, M.A12, M.A13), (M.A21, M.A22, M.A23), (M.A31, M.A32, M.A33) = rows
    M.A14, M.A24, M.A34 = t
    return M


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n0 = len(pr.leaves)
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, "Group", []) or []): par.setdefault(k.Name, o)
    def path(o):
        r, q = set(), par.get(o.Name)
        while q is not None: r.add(q.Label); q = par.get(q.Name)
        return r
    P = {o.Name: path(o) for o in pr.leaves}
    def one(label, under):
        c = [o for o in pr.leaves if o.Label == label and under in P[o.Name]]
        p.check(len(c) == 1, f"{label!r} under {under!r}: {len(c)}")
        return c[0]
    car = one(*CARRIAGE); C = pr.shapes[car.Name]; cb = C.BoundBox
    copies = {k: one(*v) for k, v in COPIES.items()}
    p.check(car.TypeId == "Part::Feature", f"the gantry carriage is a Part::Feature ({car.TypeId})")
    links = {o.Name for o in copies.values() if o.TypeId == "App::Link"}      # lite-51: a copy may link to the carriage
    for o in copies.values():
        p.check(o.TypeId == "Part::Feature" or linkgeo.link_target(o) is car,
                f"{o.Label} ({o.Name}): {o.TypeId}" + (f" -> {linkgeo.link_target(o).Name}" if o.Name in links else ""))
    T = {k: com(pr.shapes[c.Name]) - com(C) for k, c in copies.items()}
    for k, t in T.items(): p.log(f"{k} dock copy = gantry carriage + ({t.x:.3f}, {t.y:.3f}, {t.z:.3f})")
    bea = [o for o in pr.leaves if o.Label.startswith(BEACON)]
    p.check(len(bea) == 1, f"Beacon: {len(bea)}")
    bz = pr.shapes[bea[0].Name].BoundBox.ZMin
    tips = {}
    for h, (g, dk, pl) in HEADS.items():
        nz = [o for o in pr.leaves if o.Label.startswith(NOZZLE) and g in P[o.Name]]
        p.check(len(nz) == 1, f"{h} nozzle: {len(nz)}")
        tips[h] = pr.shapes[nz[0].Name].BoundBox.ZMin - T[h].z
    p.check(all(abs(t - TIP_Z) < 0.01 for t in tips.values()), f"carried tips Z {tips} (expected {TIP_Z})")
    p.check(abs(bz - TIP_Z - BEACON_DZ) < 0.01, f"Beacon face {bz - TIP_Z:.3f} above the tip (expected {BEACON_DZ})")
    p.check(abs(cb.ZMin - TIP_Z - 1.665) < 0.01, f"carriage underside {cb.ZMin - TIP_Z:.3f} above the tip (expected 1.665)")
    zt = TIP_Z + TRIM
    knife = litelib.box(cb.XMin - 5, cb.XMax + 5, cb.YMin - 5, cb.YMax + 5, cb.ZMin - 1, zt)
    cut = C.common(knife)
    p.log(f"trim plane Z {zt:.3f}: {cut.Volume:.2f} mm3 in {len(cut.Solids)} piece(s)")
    for s in cut.Solids:
        b = s.BoundBox
        p.log(f"   {s.Volume:6.2f} mm3  X {b.XMin:.2f}..{b.XMax:.2f}  Y {b.YMin:.2f}..{b.YMax:.2f}  Z {b.ZMin:.3f}..{b.ZMax:.3f}")
    p.check(len(cut.Solids) == 2 and abs(cut.Volume - CUT_VOL) < 0.5, f"the cut is the two pads: {len(cut.Solids)} pieces, "
            f"{cut.Volume:.2f} mm3 (expected 2, {CUT_VOL})")
    new = {}
    def trimmed(o, t):
        s = pr.shapes[o.Name]; k = knife.copy(); k.translate(t)
        n = s.cut(k)
        rem = s.Volume - n.Volume
        p.check(n.isValid() and len(n.Solids) == len(s.Solids) and abs(rem - cut.Volume) < TOL,
                f"{o.Label} ({o.Name}): removed {rem:.2f} mm3 (gantry {cut.Volume:.2f}), valid {n.isValid()}, "
                f"solids {len(n.Solids)} (was {len(s.Solids)})")
        nb = n.BoundBox
        p.check(nb.ZMin - t.z - TIP_Z >= TRIM - 1e-4, f"{o.Label} ({o.Name}): underside now {nb.ZMin - t.z - TIP_Z:.3f} above the carried tip")
        new[o.Name] = n
    trimmed(car, V(0, 0, 0))
    for k, c in copies.items(): trimmed(c, T[k])
    p.check(bz < new[car.Name].BoundBox.ZMin - 0.3, f"the Beacon face ({bz - TIP_Z:.3f}) is now the carriage's lowest part "
            f"({new[car.Name].BoundBox.ZMin - bz:.3f} below the carriage)")
    # nothing near the removed volume
    heads = set()
    for h, (g, dk, pl) in HEADS.items():
        heads |= {o.Name for o in pr.leaves if g in P[o.Name] or (o.Label in pl and dk in P[o.Name])}
    mine = {car.Name} | {c.Name for c in copies.values()}
    def near(cs, items, what):
        cbx = cs.BoundBox; cbx.enlarge(CLEAR_MIN + 0.01); rows = []
        for lab, s in items:
            if not s.BoundBox.intersect(cbx): continue
            d = cs.distToShape(s)[0]
            if d < CLEAR_MIN: rows.append(f"{lab[:50]} {d:.3f}")
        p.check(not rows, f"{what}: nothing within {CLEAR_MIN} mm of the removed volume: {rows}")
    near(cut, [(o.Label, pr.shapes[o.Name]) for o in pr.leaves if o.Name not in mine | heads], "gantry carriage, parts not on a head")
    for h, (g, dk, pl) in HEADS.items():
        items = []
        for o in pr.leaves:
            if o.Name in heads and (g in P[o.Name] or dk in P[o.Name]):
                s = pr.shapes[o.Name].copy(); s.translate(-T[h]); items.append((o.Label, s))
        near(cut, items, f"{h} head carried")
        cc = cut.copy(); cc.translate(T[h])
        near(cc, [(o.Label, pr.shapes[o.Name]) for o in pr.leaves if dk in P[o.Name] and o.Name not in mine | heads],
             f"{h} dock, its copy's cut")
    # the printable STL's frame (lite25_carriage_9mm.py): STL (bbox min at 0) -> model is
    # rows ((1,0,0),(0,0,1),(0,-1,0)), t = (XMin, YMin, ZMax) of the UNTRIMMED carriage's optimal box
    msh = Mesh.Mesh(STL); bA = msh.BoundBox
    ob = C.optimalBoundingBox(True, False)                                   # lite-25 framed it on the optimal box
    M = matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)), (ob.XMin, ob.YMin, ob.ZMax))
    def to_stl(s):
        r = s.copy(); r.transformShape(M.inverse(), True); r.translate(V(bA.XMin, bA.YMin, bA.ZMin)); return r
    back0 = to_stl(C)
    pts = [V(q.x, q.y, q.z) for q in msh.Points][::max(1, msh.CountPoints // 1500)]
    d = np.array([back0.distToShape(Part.Vertex(q))[0] for q in pts])
    p.check(d.max() <= TOL, f"the committed STL's frame: {len(pts)} of its vertices on the untrimmed carriage, max {d.max():.4f} "
            f"median {np.median(d):.4f} mm")
    # apply
    for o in [car] + [c for c in copies.values() if c.Name not in links]:   # a link follows its target
        vo = getattr(o, "ViewObject", None)
        ap = [(a.DiffuseColor, a.Transparency) for a in vo.ShapeAppearance] if vo is not None and hasattr(vo, "ShapeAppearance") else None
        # keep the object's own Placement: an App::Link to it (the Left copy) re-applies its own placement to the
        # target's local geometry, so a changed target Placement moves the link (a first try moved it 4.78 mm in Y)
        P0 = FreeCAD.Placement(o.Placement)
        cg = linkgeo.gplace(o).multiply(P0.inverse())                  # the containers' global placement
        X = cg.multiply(P0).inverse()                                  # global -> the object's own frame
        sols = []
        for so in new[o.Name].Solids:                                  # each solid as a global shape (composed location)
            so = so.copy(); so.Placement = X.multiply(so.Placement); sols.append(so)
        loc = Part.makeCompound(sols); loc.Placement = P0; o.Shape = loc
        p.check(o.Placement.isSame(P0, 1e-9), f"{o.Label} ({o.Name}): its Placement unchanged")
        if ap:
            try:
                a2 = o.ViewObject.ShapeAppearance
                for x in a2: x.DiffuseColor = ap[0][0]; x.Transparency = ap[0][1]
                o.ViewObject.ShapeAppearance = a2
            except Exception: pass
    doc.recompute()
    before = {n: s.BoundBox for n, s in pr.shapes.items()}
    pr.refresh()
    for o in [car] + list(copies.values()):
        a, b = pr.shapes[o.Name], new[o.Name]
        dc = (com(a) - com(b)).Length; ba, bb_ = a.BoundBox, b.BoundBox
        db = max(abs(x - y) for x, y in zip((ba.XMin, ba.YMin, ba.ZMin, ba.XMax, ba.YMax, ba.ZMax),
                                            (bb_.XMin, bb_.YMin, bb_.ZMin, bb_.XMax, bb_.YMax, bb_.ZMax)))
        p.check(abs(a.Volume - b.Volume) < 1e-3 and dc < 1e-4 and db < 1e-3,
                f"{o.Label} ({o.Name}) holds the trimmed shape where it was: volume diff {abs(a.Volume - b.Volume):.5f}, "
                f"centroid {dc:.6f} mm, box {db:.6f} mm")
    moved = [pr.shapes[n] for n in pr.shapes if n not in mine and
             max(abs(a - b) for a, b in zip((before[n].XMin, before[n].YMin, before[n].ZMin, before[n].XMax, before[n].YMax, before[n].ZMax),
                                             (pr.shapes[n].BoundBox.XMin, pr.shapes[n].BoundBox.YMin, pr.shapes[n].BoundBox.ZMin,
                                              pr.shapes[n].BoundBox.XMax, pr.shapes[n].BoundBox.YMax, pr.shapes[n].BoundBox.ZMax))) > 1e-6]
    p.check(not moved and len(pr.leaves) == n0, f"every other solid unchanged ({len(moved)} moved); solids {len(pr.leaves)} (was {n0})")
    back = to_stl(new[car.Name])
    out = MeshPart.meshFromShape(Shape=back, LinearDeflection=0.01, AngularDeflection=0.1)
    bb = back.BoundBox
    p.log(f"printable carriage: {out.CountFacets} facets, {bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f}, "
          f"volume {back.Volume:.1f} (was {back0.Volume:.1f})")
    p.dump({"trim_above_tip": TRIM, "removed_mm3": round(cut.Volume, 2),
            "pads": [[round(x, 2) for x in (s.BoundBox.XMin, s.BoundBox.XMax, s.BoundBox.YMin, s.BoundBox.YMax)] for s in cut.Solids],
            "carriage_mm3": [round(C.Volume, 1), round(new[car.Name].Volume, 1)]})
    if not p.errs:
        if p.dry: p.log(f"DRY RUN: would write {os.path.relpath(STL, _REPO)}")
        else: out.write(STL); p.log(f"wrote {os.path.relpath(STL, _REPO)}")
    return p.finish([(doc, DST)])


litelib.Pass("lite62_trim_beacon_pads").run(main)
