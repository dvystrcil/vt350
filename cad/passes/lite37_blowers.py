# GUI pass: vt350-lite-36 -> vt350-lite-37   (headless = dry run, never saves)
# vt350#19: the part-cooling blowers. The A4Tv2 heads have a 4010 duct on each side and no blower in it; the user's
# blowers are the Vindr Berserker 4010B-24V-P, 2 per head (A4Tv2, M2x10 self-tappers into the duct's pilot holes).
# No vendor CAD: the solid is built from the user's measurements (#19, issuecomment-6888948594):
#   body 39.7 x 39.7, 9.8 thick; corner tabs on all four corners, 6.5 thick; holes 2.34 on a 34.5 square; outlet on
#   the RIGHT side (label towards you, text upright), 6.0 to 33.8 below the top edge, opening 8.56 (across the
#   thickness) x 27.84; intake 27.4 on the back. Scroll diameter not measured: the body is a box with rounded corners
#   (r 3, not measured: a square corner clips the duct pocket's corner fillets, 6.15 mm3 per blower), its corners
#   down to tab thickness (where the duct's corner bosses are), the outlet a 3 mm pocket, the intake a 1 mm recess.
#   Wires (out the bottom, label side) are not modelled.
# Where (measured from each duct's solid, never from stored properties, #174):
#  - the 4 pilot holes (r 0.75 cylinders) on a 35.0 square give the hole axes; the 4 corner seat faces (planar, ~18 mm2,
#    normal along the holes) give the seat plane. n is taken so the seats face -n: the duct's material is on +n, the
#    blower on -n (its tabs sit on the seats; tabs 6.5 deep below the seat plane, flush with the label face).
#  - between the seats the duct is pocketed 6 mm deep (to n = +6, with the intake hole in its floor): the body stands
#    3.3 proud of the tabs into it, so the intake (back) faces +n, the label -n, and the body spans n -6.5..+3.3.
#    The duct's wire notch is on that label side (n -5.6..+0.9, at the blower's bottom edge), as the user's wires are.
#  - rotation in the plane: the one of 4 whose outlet lands on the duct's inlet opening. It is not assumed. "Open" alone
#    is not enough: the pocket's -u side is open air, and an outlet pointing there is 100% open. So the 3 mm in front of
#    the outlet must be mostly void (>= 0.5) AND the 2 mm ring around that must be mostly duct (>= 0.5, the inlet's
#    walls); exactly one rotation may pass. (lite-36 probe: down 0.59 / 0.67; air side 1.00 / 0.002; up 0.40 / 0.68.)
#    The outlet's position across the thickness is not measured (centred here: n -5.9..+2.7); the inlet spans
#    n -3.2..+5.3, so ~40% of the outlet faces the inlet's lip. Reported, not failed.
#  - centred on the duct's pilot square: the blower's 34.5 holes sit 0.25 mm in from the 35.0 pilots per side
#    (0.354 radially), reported, not failed; the M2 self-tappers take it.
# Checks (refuses to save on any): per duct 4 pilots on a 35.0 square, 4 seats in one plane; every blower one valid
# solid; its 4 holes parallel to the pilots and 0.354 off them (from the placed solid); the outlet pocket is there in
# the placed solid and its rectangle lands on the inlet (open fraction; the other 3 rotations blocked); the tabs touch
# the seats without overlapping the duct; inside its head nothing overlaps it but the named as-designed allowance;
# outside its head nothing does; the carried head's blowers at lite-32's dock poses clear everything that stays put by
# >= 2 mm (nearest box gap reported); role black_plastic (a fan, like the 2510); solids + 10.
import FreeCAD, Part, os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))
import litelib
from litelib import is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-36.FCStd", f"{MODELS}/vt350-lite-37.FCStd"
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path.insert(0, f"{REPO}/platform/render")
import colours
V = FreeCAD.Vector

# the blower (user's measurements), in its own frame: a, b in the label plane (b = up with the text upright),
# c through the thickness (label at c = C0, intake on the c = C1 face)
H = 39.7 / 2                      # half side
C0, C1, TAB = -6.5, 3.3, 0.0      # body c range; tabs c C0..TAB (the seat plane is c = 0)
K = 15.0                          # corners |a|, |b| >= K are tab only (the duct's bosses start at 15.2)
CORNER_R = 3.0                    # the body's corner radius (not measured; clears the duct pocket's corner fillets)
HOLE_R, HOLE_HALF = 2.34 / 2, 34.5 / 2
OUT_B = (H - 33.8, H - 6.0)       # outlet along its edge: 6.0..33.8 below the top
OUT_W = 8.56                      # outlet across the thickness, centred on the body
OUT_C = ((C0 + C1) / 2 - OUT_W / 2, (C0 + C1) / 2 + OUT_W / 2)
OUT_DEPTH, INTAKE_R, INTAKE_DEPTH = 3.0, 27.4 / 2, 1.0
PILOT_R, PILOT_HALF = 0.75, 35.0 / 2
OFFSET = (PILOT_HALF - HOLE_HALF) * math.sqrt(2)          # 0.354: hole axis to pilot axis
VOID_MIN, WALL_MIN, PROBE, RING = 0.5, 0.5, 3.0, 2.0       # in front of the outlet: void fraction, walls around it
ALLOW = {}                        # in-head overlaps as designed: {(duct side, label prefix): mm3}; none expected
LABEL = "Vindr Berserker 4010B blower {side} {head} (modelled from measurements)"
SLOTS = [("Left Toolhead", "Left Dock", "L"), ("Toolhead slot 2 (L)", "Dock slot 2 (L)", "L"), ("Toolhead slot 3 (R)", "Dock slot 3 (R)", "R"),
         ("Toolhead slot 4 (L)", "Dock slot 4 (L)", "L"), ("Right Toolhead", "Right Dock", "R")]
CARRIED_DZ, DETACH, CLEAR = -0.315, 5.0, 2.0
DY_DETACH, DY_PARK = range(-6, 61, 2), (-6, -4, -2, 0)
TOL = 1e-3


def tree(o):
    out = [o]
    for k in (getattr(o, 'Group', []) or []): out += tree(k)
    return out


def bx(a0, a1, b0, b1, c0, c1):
    return Part.makeBox(a1 - a0, b1 - b0, c1 - c0, V(a0, b0, c0))


def blower():
    """the solid in the blower frame (a, b, c), outlet on -a (the right side seen from the label, c looking +c)"""
    s = bx(-H, H, -H, H, C0, C1)
    s = s.makeFillet(CORNER_R, [e for e in s.Edges if e.BoundBox.XLength < 1e-6 and e.BoundBox.YLength < 1e-6])
    for sa in (-1, 1):
        for sb in (-1, 1):
            a0, a1 = sorted((sa * K, sa * H)); b0, b1 = sorted((sb * K, sb * H))
            s = s.cut(bx(a0 - 0.01 * (sa < 0), a1 + 0.01 * (sa > 0), b0 - 0.01 * (sb < 0), b1 + 0.01 * (sb > 0), TAB, C1 + 0.01))
            s = s.cut(Part.makeCylinder(HOLE_R, C1 - C0 + 2, V(sa * HOLE_HALF, sb * HOLE_HALF, C0 - 1)))
    s = s.cut(bx(-H - 0.01, -H + OUT_DEPTH, OUT_B[0], OUT_B[1], OUT_C[0], OUT_C[1]))
    s = s.cut(Part.makeCylinder(INTAKE_R, INTAKE_DEPTH + 0.01, V(0, 0, C1 - INTAKE_DEPTH)))
    return s.removeSplitter()


def outlet_box(a0, a1, grow=0.0):
    return bx(a0, a1, OUT_B[0] - grow, OUT_B[1] + grow, OUT_C[0] - grow, OUT_C[1] + grow)


def in_front(pl, dsh):
    """(void fraction of the PROBE mm in front of the outlet, duct fraction of the RING mm around it)"""
    void = placed(outlet_box(-H - PROBE, -H), pl)
    ring = placed(outlet_box(-H - PROBE, -H, RING), pl).cut(void)
    return 1.0 - void.common(dsh).Volume / void.Volume, ring.common(dsh).Volume / ring.Volume


def frame_placement(P, u, w, n, theta):
    """blower frame -> global: rotate theta about c, then (a, b, c) -> (u, w, n), origin P (the pilot square's centre
    on the seat plane)"""
    m = FreeCAD.Matrix(u.x, w.x, n.x, P.x, u.y, w.y, n.y, P.y, u.z, w.z, n.z, P.z, 0, 0, 0, 1)
    return FreeCAD.Placement(m).multiply(FreeCAD.Placement(V(), FreeCAD.Rotation(V(0, 0, 1), theta)))


def placed(s, pl):
    c = s.copy(); c.Placement = pl.multiply(c.Placement); return c


def box_gap(a, b):
    d = [max(0.0, a.XMin - b.XMax, b.XMin - a.XMax), max(0.0, a.YMin - b.YMax, b.YMin - a.YMax), max(0.0, a.ZMin - b.ZMax, b.ZMin - a.ZMax)]
    return (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5


def duct_frame(p, tag, sh):
    """pilots, seat plane, n (seats face -n), u = Z x n, P = the pilot square's centre on the seat plane"""
    pil = [f for f in sh.Faces if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - PILOT_R) < 0.01]
    p.check(len(pil) == 4, f"{tag}: {len(pil)} pilot holes r {PILOT_R}")
    n = V(pil[0].Surface.Axis); n.normalize()
    p.check(all(V(f.Surface.Axis).getAngle(n) < 1e-6 or V(f.Surface.Axis).getAngle(-n) < 1e-6 for f in pil),
            f"{tag}: pilot axes parallel")
    seats = []
    for f in sh.Faces:
        if isinstance(f.Surface, Part.Plane) and 10 < f.Area < 25:
            fn = V(f.Surface.Axis) * (-1 if f.Orientation == "Reversed" else 1)
            if abs(abs(fn.dot(n)) - 1) < 1e-6: seats.append((f, fn.dot(n)))
    # the seats: one per pilot, the pilot's axis crossing the face
    def crosses(f, pf):
        c, a = pf.Surface.Center, V(pf.Surface.Axis)
        q = c + a * ((f.Vertexes[0].Point - c).dot(a) / a.dot(a))
        return f.isInside(q, 1e-6, True) or f.distToShape(Part.Vertex(q))[0] < 1.5
    seat = [(f, d) for f, d in seats if any(crosses(f, pf) for pf in pil)]
    p.check(len(seat) == 4 and len({round(d) for _, d in seat}) == 1,
            f"{tag}: 4 corner seats {[round(f.Area, 2) for f, _ in seat]}, all facing the same way")
    if seat[0][1] > 0: n = -n                                   # seats face -n
    q0 = seat[0][0].Vertexes[0].Point
    p.check(all(abs((f.Vertexes[0].Point - q0).dot(n)) < 1e-6 for f, _ in seat), f"{tag}: the 4 seats in one plane")
    pts = []
    for f in pil:
        c, a = f.Surface.Center, V(f.Surface.Axis)
        pts.append(c + a * ((q0 - c).dot(n) / a.dot(n)))
    P = sum(pts, V()) * 0.25
    w = V(0, 0, 1)
    p.check(abs(n.dot(w)) < 1e-6, f"{tag}: seat normal horizontal ({n.x:.5f}, {n.y:.5f}, {n.z:.5f})")
    u = w.cross(n); u.normalize()
    loc = sorted((round((q - P).dot(u), 4), round((q - P).dot(w), 4)) for q in pts)
    p.check(all(abs(abs(x) - PILOT_HALF) < TOL and abs(abs(y) - PILOT_HALF) < TOL for x, y in loc)
            and len({(x > 0, y > 0) for x, y in loc}) == 4, f"{tag}: pilots on a {2 * PILOT_HALF} square {loc}")
    return P, u, w, n, pil


def main(p):
    pr = p.open(SRC); doc = pr.doc
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    cmap = colours.load(f"{REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    body = blower()
    p.check(body.isValid() and len(body.Solids) == 1, f"the blower solid: valid, one solid, {body.Volume:.1f} mm3, "
            f"box {body.BoundBox.XLength:.2f} x {body.BoundBox.YLength:.2f} x {body.BoundBox.ZLength:.2f}")
    made, report = [], []
    for h, d, k in SLOTS:
        root = obj(h); mine = [o for o in tree(root) if is_leaf(o)]
        fan = [o for o in mine if o.Label.startswith("2510 Fan")]
        p.check(len(fan) == 1, f"{h}: one 2510 fan ({len(fan)})")
        items = []
        for side in ("left", "right"):
            ds = [o for o in mine if o.Label.startswith(f"[a]_Duct-4010-{side}")]
            p.check(len(ds) == 1, f"{h}: one {side} 4010 duct ({[o.Label for o in ds]})")
            duct = ds[0]; dsh = pr.shapes[duct.Name]
            tag = f"{h} / {duct.Label}"
            P, u, w, n, pil = duct_frame(p, tag, dsh)
            # rotation: the outlet must land on the duct's inlet
            opens = [in_front(frame_placement(P, u, w, n, 90.0 * q), dsh) for q in range(4)]
            fits = [q for q in range(4) if opens[q][0] >= VOID_MIN and opens[q][1] >= WALL_MIN]
            p.check(len(fits) == 1, f"{tag}: outlet (void, walls) by rotation 0/90/180/270 "
                    f"{[(round(a, 3), round(b, 3)) for a, b in opens]}: on the inlet at {[90 * q for q in fits]} deg "
                    f"(void >= {VOID_MIN} and walls >= {WALL_MIN}, exactly one)")
            best = fits[0] if fits else 0
            pl = frame_placement(P, u, w, n, 90.0 * best)
            out_dir = pl.Rotation.multVec(V(-1, 0, 0))
            g = placed(body, pl)
            nm = doc.addObject("Part::Feature", "Blower_4010")
            par = duct.getParentGeoFeatureGroup()
            loc = g.copy(); loc.Placement = par.getGlobalPlacement().inverse().multiply(g.Placement)
            nm.Shape = loc; par.addObject(nm)
            nm.Label = LABEL.format(side=side[0].upper(), head=h)
            nm.ShapeMaterial = fan[0].ShapeMaterial
            if FreeCAD.GuiUp:
                try: nm.ViewObject.ShapeAppearance = fan[0].ViewObject.ShapeAppearance
                except Exception: nm.ViewObject.ShapeColor = fan[0].ViewObject.ShapeColor
            items.append(dict(side=side, duct=duct, obj=nm, g=g, P=P, n=n, pil=pil, pl=pl, opens=opens, rot=90 * best,
                              out_dir=out_dir))
        made.append((h, d, k, root, fan[0], items))
    doc.recompute(); pr.refresh()
    allnew = []
    for h, d, k, root, fan, items in made:
        head_leaves = [o for o in tree(root) if is_leaf(o)]
        for it in items:
            nm, duct = it["obj"], it["duct"]; sh = pr.shapes[nm.Name]; dsh = pr.shapes[duct.Name]
            tag = nm.Label
            p.check(sh.isValid() and len(sh.Solids) == 1 and abs(sh.Volume - body.Volume) < TOL
                    and abs(sh.BoundBox.DiagonalLength - it["g"].BoundBox.DiagonalLength) < TOL
                    and (sh.BoundBox.Center - it["g"].BoundBox.Center).Length < 1e-6,
                    f"{tag}: one valid solid, {sh.Volume:.1f} mm3, where placed")
            # the holes, from the placed solid: parallel to the pilots, OFFSET off each
            holes = [f for f in sh.Faces if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - HOLE_R) < 1e-6]
            nn = it["n"]
            def off(c1, c2):
                dv = c1 - c2; return (dv - nn * dv.dot(nn)).Length
            axes = []
            for f in holes:
                c = f.Surface.Center
                if not any(off(c, a) < 1e-6 for a in axes): axes.append(c)
            par = all(V(f.Surface.Axis).getAngle(nn) < 1e-6 or V(f.Surface.Axis).getAngle(-nn) < 1e-6 for f in holes)
            pair = [min(off(a, pf.Surface.Center) for pf in it["pil"]) for a in axes]
            used = {min(range(4), key=lambda i: off(a, it["pil"][i].Surface.Center)) for a in axes}
            p.check(len(axes) == 4 and par and len(used) == 4 and all(abs(x - OFFSET) < TOL for x in pair),
                    f"{tag}: 4 holes parallel to the duct's pilots, one per pilot, each {[round(x, 3) for x in pair]} mm "
                    f"off its pilot (34.5 vs 35.0 square: {OFFSET:.3f} expected)")
            # the outlet, from the placed solid: the pocket is there, its rectangle lands on the inlet
            inside = placed(outlet_box(-H, -H + 1.0), it["pl"])
            in_mat = inside.common(sh).Volume
            vf, wf = in_front(it["pl"], dsh)
            od = it["out_dir"]
            p.check(in_mat < TOL and vf >= VOID_MIN and wf >= WALL_MIN and od.z < -1 + 1e-6,
                    f"{tag}: outlet pocket in the solid ({in_mat:.4f} mm3 of material in it); facing "
                    f"({od.x:+.3f}, {od.y:+.3f}, {od.z:+.3f}), rotation {it['rot']} deg; in front of it {100 * vf:.1f}% "
                    f"void inside {100 * wf:.1f}% duct walls (the inlet)")
            # tabs on the seats: touching, not overlapping
            ov = sh.common(dsh).Volume; dd = sh.distToShape(dsh)[0]
            p.check(ov < TOL and dd < TOL, f"{tag}: on its duct's seats: overlap {ov:.4f} mm3, distance {dd:.4f}")
            # inside the head: only the named allowance
            got = {}
            for o in head_leaves:
                if o.Name in (nm.Name, duct.Name) or not pr.boxes[o.Name].intersect(sh.BoundBox): continue
                v = sh.common(pr.shapes[o.Name]).Volume
                if v > TOL: got[o.Label] = round(v, 3)
            fan_v = sh.common(pr.shapes[fan.Name]).Volume
            p.log(f"{tag}: vs the 2510 fan {fan_v:.3f} mm3; box gap {box_gap(sh.BoundBox, pr.shapes[fan.Name].BoundBox):.2f}, "
                  f"distance {sh.distToShape(pr.shapes[fan.Name])[0]:.3f} mm")
            want = {key: v for (s_, key), v in ALLOW.items() if s_ == it["side"]}
            bad = {lab: v for lab, v in got.items()
                   if not any(lab.startswith(key) and abs(v - want[key]) < 0.05 for key in want)}
            p.check(not bad and len(got) == len(want), f"{tag}: inside {h}, overlaps {got or 'none'} (as designed: {want or 'none'})")
            allnew.append((h, nm, sh, it))
        excl = {o.Name for o in head_leaves}
        p.no_overlap([(it["obj"].Label, pr.shapes[it["obj"].Name]) for it in items], pr,
                     lambda r, h=h: f"{h}: blowers vs every solid outside its head: {r.hits[:6]}", exclude=excl)
    # --- the carried head's blowers at lite-32's dock poses vs everything that stays put (lite-35's block: the head,
    # its dock's moving parts, its tube, both dock carriage copies; distToShape raised to the box gap)
    car = [o for dname in ("Left Dock", "Right Dock") for c in tree(obj(dname))
           if c.TypeId == 'App::Part' and c.Label.startswith("Carriage") for o in tree(c) if is_leaf(o)]
    for h, d, k, root, fan, items in made:
        own = {o.Name for o in tree(obj(h)) + tree(obj(d)) if is_leaf(o)
               and not o.Label.startswith(("Dock Asembly", "Dock bracket", "Dock pair"))}
        obst = [o for o in pr.leaves if o.Name not in own and o.Name not in {c.Name for c in car}
                and not o.Label.startswith("Bowden")]
        det = DETACH if k == "L" else -DETACH
        poses = [(0.0, dy) for dy in DY_PARK] + [(det, dy) for dy in DY_DETACH]
        tasks, keys, gmin = [], [], (float("inf"), "")
        for dx, dy in poses:
            for it in items:
                sh = pr.shapes[it["obj"].Name]; m = sh.BoundBox; key = it["side"]
                mb = FreeCAD.BoundBox(m.XMin + dx, m.YMin + dy, m.ZMin + CARRIED_DZ, m.XMax + dx, m.YMax + dy, m.ZMax + CARRIED_DZ)
                for o in obst:
                    g = box_gap(mb, pr.boxes[o.Name])
                    gmin = min(gmin, (g, f"{key} @x{dx:+.0f} y{dy:+.0f} vs {o.Label}"))
                    if g < CLEAR + 1.0:
                        tasks.append((pr.shapes[o.Name], sh.translated(V(dx, dy, CARRIED_DZ)))); keys.append((f"{key} @x{dx:+.0f} y{dy:+.0f}", o.Label, g))
        ds = p.map(litelib._t_dist, tasks)
        res, raised = [], []
        for (kk, ol, g), dd in zip(keys, ds):
            if isinstance(dd, litelib._Err): raise RuntimeError(f"distToShape failed for {kk} vs {ol}: {dd.msg}")
            if dd < g - 1e-6: raised.append((kk, ol, round(dd, 2), round(g, 2)))
            res.append((max(dd, g), kk, ol))
        if raised: p.log(f"{h}: {len(raised)} distToShape results below their box gap, raised to it: {raised[:4]}")
        near = sorted((round(a, 2), b, c) for a, b, c in res if a < CLEAR)
        p.log(f"{h}: nearest {sorted((round(a, 2), b, c) for a, b, c in res)[:3]}")
        p.check(not near and gmin[0] < float("inf"), f"{h}: its blowers at {len(poses)} dock poses ({len(tasks)} pairs "
                f"within {CLEAR + 1.0:.0f} mm by box, measured; nearest box gap {gmin[0]:.2f}: {gmin[1]}): "
                f"min {min(res)[0] if res else float('inf'):.2f} mm to anything that stays put {near[:3]}")
    def gpath(o):
        r, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r))
    mat = lambda o: getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default'
    for h, nm, sh, it in allnew:
        r_ = colours.role_of(cmap, nm.Label, gpath(nm), mat(nm))
        p.check(r_ == "black_plastic", f"{nm.Label}: material {mat(nm)} -> role {r_}")
    p.check(len(pr.leaves) == n_before + 10 and len(allnew) == 10, f"solids: {n_before} + {len(allnew)} = {len(pr.leaves)}")
    p.dump({"blower": dict(volume=round(body.Volume, 1), body_c=[C0, C1], tabs_c=[C0, TAB], outlet_b=list(OUT_B),
                           outlet_c=[round(x, 2) for x in OUT_C], hole_offset_mm=round(OFFSET, 3)),
            "blowers": [dict(label=nm.Label, head=h, duct=it["duct"].Label, rotation_deg=it["rot"],
                             outlet_void_walls_by_rotation=[[round(a, 3), round(b, 3)] for a, b in it["opens"]],
                             outlet_dir=[round(x, 4) for x in it["out_dir"]],
                             seat_centre=[round(x, 3) for x in it["P"]], seat_normal=[round(x, 5) for x in it["n"]],
                             box=[round(v, 2) for v in (sh.BoundBox.XMin, sh.BoundBox.YMin, sh.BoundBox.ZMin,
                                                        sh.BoundBox.XMax, sh.BoundBox.YMax, sh.BoundBox.ZMax)])
                        for h, nm, sh, it in allnew],
            "fasteners_added_per_blower": {"M2x10 self-tapping screw (into the duct's pilot)": 4}})
    p.finish([(doc, DST)])


litelib.Pass("lite37_blowers").run(main)
