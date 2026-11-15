# GUI pass: vt350-lite-35 -> vt350-lite-36   (headless = dry run, never saves)
# vt350#3 AC4 (+ #19): the roof exit for each head's bowden tube and O2S USB cable. lite-16 noted "the bowden tubes
# pass through the rear roof strip, so the roof needs pass-throughs"; nothing cut them. The user (2026-11-14): "start
# on the roof access, also note the electrical cable for each tool will be cable tied to the bowden", and chose to
# CLAMP the bundle at the roof (a fixed point; not a sliding guide).
#
# Per head (5): the tube leaves the roof's underside at its ExitPoint (Y 460, Z 690) along ExitDir (0, .707, .707)
# (lite-30's route). The axis is MEASURED from the tube solid (sections at Z 690 and 700): the stored ExitPoint/Inlet
# are stale in X (each tube lies in a plane X = const; Bowden Left at -409.70, its props say -399.0). The cable rides
# beside the tube in X at the roof, on its restraint's side (L heads -X, R heads +X), centres 5.11 mm apart (PTFE OD
# 4.12 measured, cable OD 5.1 measured, 0.5 between): tied along ~400 mm of tube it rolls there from where
# o2s_cable_route.py's lead-in put it (below the tube), which would have crossed the felt top past the strip's edge.
#  - CUT: two clearance cylinders (radius + 1.0) along the bundle's axes through the roof panel, the felt strip and
#    its liners; the felt strip is notched out to its rear edge (Y 480) instead of leaving a 1 mm wall.
#  - BASE (printed): a flange on the felt strip (Z 704..708, Y 444..480) that steps down onto the roof panel behind
#    it (Z 693..708, Y 480..498), fused with the lower half of a split clamp along the bundle's 45 deg axis. Held by
#    2 x M5 into the rear 4040 bar's top T-slot (Y 490, through the roof panel) and 2 x M3 through-bolts at the front
#    (flange + felt + roof panel, nut inside).
#  - CAP (printed): the clamp's upper half, 2 x M3 into heat-set inserts in the base. Bores are the tube's and the
#    cable's diameters + 0.1; the halves stand 0.3 mm apart, so tightening squeezes both (0.1 mm radial grip).
# Checks (refuses to save on any): each tube's route rebuilt from its stored data; the roof parts stay one valid solid
# each and lose only the cut; after the cut no tube overlaps the roof/felt; the new parts overlap nothing in the
# printer (tubes included); the M5s land on the bar's slot (Y 490 +- 0.5) on its top face (Z 690); every bore and
# screw hole has >= 1.5 mm wall to the part's outside and to each other; neighbouring clamps >= 10 mm apart; role
# printed; solids +10.
import FreeCAD, Part, os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))
import litelib
from litelib import is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-35.FCStd", f"{MODELS}/vt350-lite-36.FCStd"
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path.insert(0, f"{REPO}/platform/render")
import colours
V = FreeCAD.Vector

R_T, R_C, GAP = 4.12 / 2, 5.1 / 2, 0.5                 # tube, cable radii; gap between them
SEP = R_T + R_C + 1.6                                   # 6.21 centre to centre in the clamp: 1.5 mm of wall between the
                                                        # bores (tied along the tube they touch; the clamp spreads them 1.6)
CLR, BORE, SPLIT = 1.0, 0.05, 0.15                      # roof clearance; bore radial oversize; half-gap at the split
ROOF = ["Roof panel (3 mm)", "Roof felt strip (pad 3)", "Roof felt strip liner, inner", "Roof felt strip liner, outer"]
FELT_TOP, PANEL_TOP, STRIP_END = 704.0, 693.0, 480.0
FL_T, FL_HW, FL_Y0, FL_Y1 = 4.0, 18.0, 444.0, 498.0    # flange: thickness on the felt, half width, front, rear
BAR_SLOT_Y, BAR_TOP = 490.0, 690.0                      # rear 4040 bar: top slot centre, top face
CL_HW, CL_T, CL_S0, CL_S1 = 13.0, 7.0, 12.0, 46.0       # clamp: half width (X), half thickness (normal), along-axis span
M3, M3_INS, M5 = 1.7, 2.0, 2.75                         # clearance radii; heat-set insert hole radius (Ø4.0)
INS_DEPTH = 5.5
HEADS = [("Toolhead slot 1", "Left Toolhead", "Bowden Left", "Bowden Left", -1), ("slot 2", "Toolhead slot 2 (L)", "Bowden slot 2", "Bowden Left", -1),
         ("slot 3", "Toolhead slot 3 (R)", "Bowden slot 3", "Bowden Right", +1), ("slot 4", "Toolhead slot 4 (L)", "Bowden slot 4", "Bowden Left", -1),
         ("slot 5", "Right Toolhead", "Bowden Right", "Bowden Right", +1)]
LABEL = "Roof exit clamp {part} slot {n} (vt350, GPL-3.0-or-later)"
GROUP = "Enclosure extras (lite-16)"


def frame(Dv):
    X = V(1, 0, 0); N = X.cross(Dv); N.normalize()
    return X, Dv, N


def lbox(o, X, Dv, N, u0, u1, s0, s1, n0, n1):
    """a box in the local frame (u along X, s along D, n along N), corners u0..u1 etc., from origin o"""
    b = Part.makeBox(u1 - u0, s1 - s0, n1 - n0)
    m = FreeCAD.Matrix(X.x, Dv.x, N.x, 0, X.y, Dv.y, N.y, 0, X.z, Dv.z, N.z, 0, 0, 0, 0, 1)
    b.Placement = FreeCAD.Placement(m).multiply(FreeCAD.Placement(V(u0, s0, n0), FreeCAD.Rotation()))
    b.translate(o); return b


def cyl(p, d, r, s0, s1):
    return Part.makeCylinder(r, s1 - s0, p + d * s0, d)


def above(z): return Part.makeBox(4000, 4000, 2000, V(-2000, -2000, z))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    cmap = colours.load(f"{REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    abs_src = next(o for o in pr.leaves if 'ABS' in getattr(getattr(o, 'ShapeMaterial', None), 'Name', ''))
    src = {k: obj(k) for k in ("Bowden Left", "Bowden Right")}
    roof = {lab: obj(lab) for lab in ROOF}
    p.check(all(o.TypeId == "Part::Feature" and o.Placement.isIdentity() and o.getGlobalPlacement().isIdentity()
                for o in roof.values()), "roof parts are plain Part::Features in the global frame")
    bar = obj("4040 (1)004"); bb = pr.shapes[bar.Name].BoundBox
    p.check(abs(bb.ZMax - BAR_TOP) < 1e-3 and bb.YMin <= BAR_SLOT_Y - 10 + 1e-3 and bb.YMax >= BAR_SLOT_Y + 10 - 1e-3,
            f"the rear top bar: top Z {bb.ZMax:.2f}, Y {bb.YMin:.1f}..{bb.YMax:.1f} (slot at {BAR_SLOT_Y})")
    cutters, made, report = [], [], []
    for name, h, tlab, slab, sgn in HEADS:
        t, s = obj(tlab), src[slab]
        tb, sb = pr.shapes[t.Name].BoundBox, pr.shapes[s.Name].BoundBox
        dx = tb.XMin - sb.XMin
        p.check(all(abs(a - b) < 1e-3 for a, b in ((tb.YMin, sb.YMin), (tb.ZMin, sb.ZMin), (tb.XLength, sb.XLength))),
                f"{name}: {tlab} is {slab} translated by dX {dx:+.2f}")
        # the axis from the tube's own geometry: its stored ExitPoint is stale in X (Bowden Left: -399.0 stored, the
        # solid crosses Z 690 at X -409.70), so section the solid at the roof's underside and 10 mm higher
        def centre(z):
            sec = pr.shapes[t.Name].slice(V(0, 0, 1), z)
            p.check(len(sec) == 1, f"{name}: {tlab} cut by Z {z} in one loop ({len(sec)})")
            return Part.Face(sec[0]).CenterOfMass
        E, E2 = centre(690.0), centre(700.0); Dv = E2 - E; Dv.normalize()
        sd = V(s.ExitDir); sd.normalize()
        p.check(Dv.getAngle(sd) < math.radians(0.5) and abs(Dv.x) < 1e-3,
                f"{name}: exit measured at {tuple(round(x, 2) for x in E)} along {tuple(round(x, 3) for x in Dv)} "
                f"(stored ExitPoint X {s.ExitPoint.x + dx:.2f}, ExitDir agrees to {math.degrees(Dv.getAngle(sd)):.2f} deg)")
        Dv = V(0, Dv.y, Dv.z); Dv.normalize()
        X, Dv, N = frame(Dv)
        Ec = E + X * (sgn * SEP)                          # the cable's axis, beside the tube
        mid = E + X * (sgn * SEP / 2)
        # the cut through the roof layers: clearance cylinders + the felt notch out to the strip's rear edge
        cut = cyl(E, Dv, R_T + CLR, -15, 40).fuse(cyl(Ec, Dv, R_C + CLR, -15, 40))
        xs = sorted((E.x, Ec.x)); nx0, nx1 = xs[0] - R_C - CLR, xs[1] + R_C + CLR
        notch = Part.makeBox(nx1 - nx0, STRIP_END + 1 - 455, FELT_TOP + 1 - PANEL_TOP, V(nx0, 455, PANEL_TOP))
        cutters.append((name, cut, notch))
        # the base: flange (on the felt, stepping down to the roof panel behind the strip) + the clamp's lower half
        fl = Part.makeBox(2 * FL_HW, STRIP_END - FL_Y0, FL_T, V(mid.x - FL_HW, FL_Y0, FELT_TOP))
        step = Part.makeBox(2 * FL_HW, FL_Y1 - STRIP_END, FELT_TOP + FL_T - PANEL_TOP, V(mid.x - FL_HW, STRIP_END, PANEL_TOP))
        lower = lbox(mid, X, Dv, N, -CL_HW, CL_HW, CL_S0, CL_S1, -CL_T, -SPLIT).common(above(FELT_TOP))
        base = fl.fuse(step).fuse(lower)
        cap = lbox(mid, X, Dv, N, -CL_HW, CL_HW, CL_S0, CL_S1, SPLIT, CL_T).common(above(FELT_TOP + FL_T + 0.5))
        # passages: clearance through the flange, bores in the clamp
        base = base.cut(cyl(E, Dv, R_T + CLR, -15, CL_S0 + 2)).cut(cyl(Ec, Dv, R_C + CLR, -15, CL_S0 + 2))
        bores = cyl(E, Dv, R_T + BORE, -15, CL_S1 + 15).fuse(cyl(Ec, Dv, R_C + BORE, -15, CL_S1 + 15))
        base, cap = base.cut(bores), cap.cut(bores)
        # fasteners: 2 x M5 into the bar's slot, 2 x M3 through-bolts at the front, 2 x M3 cap screws into inserts
        m5 = [V(mid.x + sx * 11.0, BAR_SLOT_Y, PANEL_TOP - 3) for sx in (-1, 1)]
        m3f = [V(mid.x + sx * 13.0, 451.0, PANEL_TOP - 10) for sx in (-1, 1)]
        sm = (CL_S0 + CL_S1) / 2 + 4
        capc = [mid + X * (sx * 9.5) + Dv * sm for sx in (-1, 1)]
        for q in m5: base = base.cut(Part.makeCylinder(M5, 40, q))
        for q in m3f: base = base.cut(Part.makeCylinder(M3, 40, q))
        for q in capc:
            cap = cap.cut(Part.makeCylinder(M3, 20, q - N * 1, N))
            base = base.cut(Part.makeCylinder(M3_INS, INS_DEPTH + SPLIT, q - N * (SPLIT + INS_DEPTH), N))
        base, cap = base.removeSplitter(), cap.removeSplitter()
        p.check(base.isValid() and len(base.Solids) == 1 and cap.isValid() and len(cap.Solids) == 1,
                f"{name}: base {base.Volume:.0f} mm3, cap {cap.Volume:.0f} mm3, one valid solid each; base Z "
                f"{base.BoundBox.ZMin:.1f}..{base.BoundBox.ZMax:.1f}, Y {base.BoundBox.YMin:.1f}..{base.BoundBox.YMax:.1f}")
        # walls: each bore / hole to the outside and to each other (distance between the holes' surfaces)
        def wall(sh, a_r, a_p, a_d, b_r, b_p, b_d):
            la, lb = Part.makeLine(a_p - a_d * 200, a_p + a_d * 200), Part.makeLine(b_p - b_d * 200, b_p + b_d * 200)
            return la.distToShape(lb)[0] - a_r - b_r
        walls = {"tube-cable bores": wall(None, R_T + BORE, E, Dv, R_C + BORE, Ec, Dv)}
        for i, q in enumerate(capc):
            for nm, pp, rr in (("tube", E, R_T + BORE), ("cable", Ec, R_C + BORE)):
                walls[f"cap screw {i} - {nm} bore"] = wall(None, M3_INS, q, N, rr, pp, Dv)
        p.check(min(walls.values()) >= 1.5 - 1e-6, f"{name}: walls between holes >= 1.5 mm: { {k: round(v, 2) for k, v in walls.items()} }")
        edge = min(CL_HW - abs((q - mid).dot(X)) - M3_INS for q in capc)
        p.check(edge >= 1.5, f"{name}: cap screws {edge:.2f} mm from the clamp's side faces")
        for q in m5:
            p.check(abs(q.y - BAR_SLOT_Y) < 0.5 and bb.XMin < q.x < bb.XMax, f"{name}: M5 at X {q.x:.1f} over the bar's slot (Y {q.y})")
        made.append((name, h, sgn, base, cap, m5, m3f, capc, mid))
        report.append(dict(slot=name, tube_exit=[round(x, 2) for x in E], cable_side="-X" if sgn < 0 else "+X",
                           base_mm3=round(base.Volume, 1), cap_mm3=round(cap.Volume, 1)))
    # neighbours
    for (a, *_ , ba, ca, _, _, _, ma), (b, *__, bb2, cb, _, _, _, mb) in zip(made, made[1:]):
        g = (bb2.BoundBox.XMin - ba.BoundBox.XMax)
        p.check(g >= 10.0, f"clamps {a} | {b}: {g:.1f} mm apart")
    # cut the roof layers
    for lab, o in roof.items():
        old = pr.shapes[o.Name]; new = old
        for name, cut, notch in cutters:
            new = new.cut(cut)
            if lab != "Roof panel (3 mm)": new = new.cut(notch)
        # the M5 and front M3 holes go through the roof panel (and the front M3s through the felt strip too)
        for name, h, sgn, base, cap, m5, m3f, capc, mid in made:
            for q in m5 + m3f: new = new.cut(Part.makeCylinder(M5 if q in m5 else M3, 40, q))
        new = new.removeSplitter()
        p.check(new.isValid() and len(new.Solids) == 1 and 0 < old.Volume - new.Volume < 0.2 * old.Volume,
                f"{lab}: cut {old.Volume - new.Volume:.1f} of {old.Volume:.1f} mm3 ({len(cutters)} exits); valid {new.isValid()}, "
                f"solids {len(new.Solids)}")
        o.Shape = new
    grp = obj(GROUP)
    for name, h, sgn, base, cap, *_ in made:
        n = name.split()[-1]
        for part, sh in (("base", base), ("cap", cap)):
            ob = doc.addObject("Part::Feature", "RoofExit_" + part); ob.Shape = sh; grp.addObject(ob)
            ob.Label = LABEL.format(part=part, n=n); ob.ShapeMaterial = abs_src.ShapeMaterial
            if FreeCAD.GuiUp:
                try: ob.ViewObject.ShapeAppearance = abs_src.ViewObject.ShapeAppearance
                except Exception: ob.ViewObject.ShapeColor = abs_src.ViewObject.ShapeColor
    doc.recompute(); pr.refresh()
    new_objs = [o for o in pr.leaves if o.Label.startswith("Roof exit clamp")]
    p.check(len(new_objs) == 10, f"{len(new_objs)} new clamp parts")
    # tubes no longer cross the roof layers
    tubes = [obj(t) for _, _, t, _, _ in HEADS]
    left = [(t.Label, r.Label, round(pr.shapes[t.Name].common(pr.shapes[r.Name]).Volume, 3)) for t in tubes for r in roof.values()
            if pr.shapes[t.Name].BoundBox.intersect(pr.shapes[r.Name].BoundBox)]
    p.check(all(v < 1e-3 for _, _, v in left), f"tubes vs the cut roof layers: {[x for x in left if x[2] >= 1e-3] or 'clear'}")
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in new_objs], pr,
                 lambda r: f"new clamp parts vs everything (tubes included): {r.hits[:6]}", exclude={o.Name for o in new_objs})
    def gpath(o):
        r, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r))
    mat = lambda o: getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default'
    for o in new_objs:
        r_ = colours.role_of(cmap, o.Label, gpath(o), mat(o))
        p.check(r_ == "printed", f"{o.Label}: material {mat(o)} -> role {r_}")
    p.check(len(pr.leaves) == n_before + 10, f"solids: {n_before} + 10 = {len(pr.leaves)}")
    p.dump({"exits": report,
            "fasteners_added_per_exit": {"M5x25 SHCS + M5 T-nut (rear 4040 top slot)": 2,
                                         "M3x20 SHCS + washer + nyloc nut (front, through felt + roof)": 2,
                                         "M3x12 SHCS + M3 heat-set insert (cap to base)": 2},
            "exits_total": len(made)})
    p.finish([(doc, DST)])


litelib.Pass("lite36_roof_exit").run(main)
