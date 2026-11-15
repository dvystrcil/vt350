# #3 AC2: each head's O2S USB cable route inside the chamber, from its wire restraint's lock to the roof, bundled with
# that head's bowden tube. Shared by cad/studies/o2s_cable_route.py (the study, read-only) and the model passes that
# build the cables (lite-40). Moved here unchanged from the study (2026-11-14) so both use one route.
#
# The cable leaves the restraint's lock straight up (the lock's Ø5.4 channel, axis +Z). The tube's curve is rebuilt
# from its stored route (bezier.py) with X taken from the solid (the stored X is stale on most tubes, #174). The JOIN
# is the LOWEST point on the tube whose lead-in (a Bezier from the lock top, tangent +Z, to a point beside the tube,
# arriving along the tube's tangent) bends no tighter than MIN_R; from there the cable runs beside the tube to the
# roof's underside.
import FreeCAD, Part, math
import bezier
from litelib import is_leaf
V = FreeCAD.Vector
R_TUBE, R_CABLE, GAP = 4.12 / 2, 5.1 / 2, 0.5         # PTFE OD 4.12 (measured, #3); cable OD 5.1 (measured by the user,
                                                       # 2026-11-14; upstream's stub models it as 5.0)
MIN_R = 10 * 2 * R_CABLE                               # assumption: 10 x OD for a flexing cable (no datasheet)
                                                       # The user (2026-11-14): "fairly flexible", rubber jacket, not
                                                       # PVC. So 10 x OD is a cautious rule for it, kept on purpose.
HANDLES = [10.0 * i for i in range(1, 21)]             # 10..200 mm
JOINS = [i / 40 for i in range(1, 36)]                 # along the tube, u 0.025..0.875
ROOF_Z = 690.0                                         # roof panel underside (lite-35)
HEADS = [("Left Toolhead", "Bowden Left", "Bowden Left"), ("Toolhead slot 2 (L)", "Bowden slot 2", "Bowden Left"),
         ("Toolhead slot 3 (R)", "Bowden slot 3", "Bowden Right"), ("Toolhead slot 4 (L)", "Bowden slot 4", "Bowden Left"),
         ("Right Toolhead", "Bowden Right", "Bowden Right")]
OWN = ("Orbitool O2S", "Orbiter Smart Sensor", "Orbitool O2S wire restraint")


def tree(o):
    out = [o]
    for k in (getattr(o, 'Group', []) or []): out += tree(k)
    return out


def bez(poles, u):
    p0, p1, p2, p3 = poles; v = 1 - u
    return V(*[v ** 3 * p0[i] + 3 * v * v * u * p1[i] + 3 * v * u * u * p2[i] + u ** 3 * p3[i] for i in range(3)])


def tangent(poles, u):
    d1, _ = bezier._d(poles, u); t = V(*d1); t.normalize(); return t


def length(poles, u0=0.0, u1=1.0, n=400):
    pts = [bez(poles, u0 + (u1 - u0) * i / n) for i in range(n + 1)]
    return sum((pts[i + 1] - pts[i]).Length for i in range(n)), pts


def u_at_z(poles, z):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if bez(poles, m).z < z: lo = m
        else: hi = m
    return (lo + hi) / 2


def gen_poles(P0, T0, P1, T1, a, b):
    return [tuple(P0), tuple(P0 + T0 * a), tuple(P1 - T1 * b), tuple(P1)]


def box_gap(p, b):
    d = [max(0.0, b.XMin - p.x, p.x - b.XMax), max(0.0, b.YMin - p.y, p.y - b.YMax), max(0.0, b.ZMin - p.z, p.z - b.ZMax)]
    return math.sqrt(sum(x * x for x in d))


def route(p, pr, obj, h, tlab, slab, src):
    """One head's cable inside the chamber. p: the litelib Pass (checks + log); pr: the opened model; obj(label);
    src {source tube label: object}. Returns (points from the lock top to the roof underside, info dict); the info
    holds the lead-in poles, the tube poles and the join, so a pass can build the solid and its ties."""
    root = obj(h); mine = [o for o in tree(root) if is_leaf(o)]
    lock = [o for o in mine if o.Label.startswith("Orbitool O2S wire restraint lock")]
    p.check(len(lock) == 1, f"{h}: one restraint lock ({len(lock)})")
    ls = pr.shapes[lock[0].Name]
    ch = [f for f in ls.Faces if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 2.7) < 0.05]
    p.check(bool(ch) and all(abs(abs(f.Surface.Axis.z) - 1) < 1e-6 for f in ch), f"{h}: the lock's Ø5.4 cable channel is vertical")
    c = ch[0].Surface.Center
    P0 = V(c.x, c.y, ls.BoundBox.ZMax)
    t, s = obj(tlab), src[slab]
    tb, sb = pr.shapes[t.Name].BoundBox, pr.shapes[s.Name].BoundBox
    dx = tb.XMin - sb.XMin
    p.check(all(abs(a - b) < 1e-3 for a, b in ((tb.YMin, sb.YMin), (tb.ZMin, sb.ZMin), (tb.XLength, sb.XLength), (tb.ZLength, sb.ZLength))),
            f"{h}: {tlab} is {slab} translated by dX {dx:+.2f} (Y, Z, size unchanged)")
    sec = pr.shapes[t.Name].slice(V(0, 0, 1), 600.0)
    p.check(len(sec) == 1, f"{h}: {tlab} cut by Z 600 in one loop")
    off = V(Part.Face(sec[0]).CenterOfMass.x - s.Inlet.x, 0, 0)
    tp = bezier.tube_poles(tuple(V(s.Inlet) + off), tuple(V(s.ExitPoint) + off), tuple(V(s.ExitDir)),
                           s.HandleInlet.Value, s.HandleExit.Value)
    r_tube = bezier.min_radius(tp)
    p.check(abs(r_tube - s.MinBendRadius.Value) < 0.5, f"{h}: tube curve rebuilt from its stored route, R {r_tube:.2f} "
            f"(stored {s.MinBendRadius.Value:.2f})")
    p.check(abs(bez(tp, 0).z - pr.shapes[t.Name].BoundBox.ZMin) < 0.05, f"{h}: the curve starts at the tube's bottom "
            f"(Z {bez(tp, 0).z:.2f} vs {pr.shapes[t.Name].BoundBox.ZMin:.2f})")
    miss = []
    for z in (530.0, 560.0, 600.0, 650.0, 680.0):
        sc = pr.shapes[t.Name].slice(V(0, 0, 1), z)
        cm = Part.Face(sc[0]).CenterOfMass if len(sc) == 1 else None
        q = bez(tp, u_at_z(tp, z))
        miss.append(round((V(cm.x, cm.y, z) - q).Length, 2) if cm else None)
    p.check(all(m is not None and m < 0.5 for m in miss), f"{h}: the rebuilt curve runs through the tube solid's "
            f"section centres at Z 530/560/600/650/680 (off by {miss} mm); X {bez(tp, 0).x:.2f} (stored {s.Inlet.x + dx:.2f})")
    u_roof = u_at_z(tp, ROOF_Z) if bez(tp, 1).z > ROOF_Z else 1.0
    sgap = R_TUBE + R_CABLE + GAP
    per_u = {}
    for u in JOINS:
        if u >= u_roof: break
        Q, T = bez(tp, u), tangent(tp, u)
        w = P0 - Q; w = w - T * w.dot(T)
        if w.Length < 1e-6: continue
        w.normalize(); Qc = Q + w * sgap
        if Qc.z <= P0.z: continue                                  # the lead-in only goes up from the lock
        for a in HANDLES:
            for b in HANDLES:
                pl = gen_poles(P0, V(0, 0, 1), Qc, T, a, b)
                r = bezier.min_radius(pl, 200)
                if u not in per_u or r > per_u[u][0]: per_u[u] = (r, u, a, b, Qc, T, w)
    ok_u = [per_u[x] for x in sorted(per_u) if per_u[x][0] >= MIN_R]
    p.log(f"{h}: best lead-in bend R by join height: " + ", ".join(f"Z {bez(tp, x).z:.0f}: {per_u[x][0]:.0f}" for x in sorted(per_u)))
    p.check(bool(ok_u), f"{h}: a join on the tube with the lead-in bend R >= {MIN_R:.0f}")
    r_lead, u, a, b, Qc, T, w = ok_u[0]                  # the LOWEST join that bends gently enough: bundled sooner
    lead = gen_poles(P0, V(0, 0, 1), Qc, T, a, b)
    L_lead, pts_lead = length(lead, n=120)
    L_bun, pts_tube = length(tp, u, u_roof, n=160)
    # the bundle: beside the tube on the side w had at the join, carried along by removing the tangent part
    pts_bun, sides = [], []
    for i, q in enumerate(pts_tube):
        uu = u + (u_roof - u) * i / 160; Ti = tangent(tp, uu); wi = w - Ti * w.dot(Ti); wi.normalize()
        pts_bun.append(q + wi * sgap); sides.append(wi)
    L_bun2 = sum((pts_bun[i + 1] - pts_bun[i]).Length for i in range(len(pts_bun) - 1))
    r_bun = r_tube - sgap
    p.log(f"{h}: lock top {tuple(round(x, 2) for x in P0)}; join at tube u {u:.3f} = Z {bez(tp, u).z:.1f}, "
          f"{(bez(tp, u) - P0).Length:.1f} mm from the lock; lead-in handles {a:.0f}/{b:.0f}, length {L_lead:.1f}; "
          f"bundle to the roof {L_bun2:.1f} (tube {L_bun:.1f})")
    p.check(r_lead >= MIN_R and r_bun >= MIN_R, f"{h}: bend R lead-in {r_lead:.1f}, beside the tube >= {r_bun:.1f} "
            f"(MIN_R {MIN_R:.0f}, assumed 10 x the {2 * R_CABLE:.1f} mm OD)")
    info = dict(P0=P0, lead=lead, tube_poles=tp, u_join=u, u_roof=u_roof, pts_lead=pts_lead, pts_bun=pts_bun,
                pts_tube=pts_tube, sides=sides, L_lead=L_lead, L_bun=L_bun2, r_lead=r_lead, r_bun=r_bun, r_tube=r_tube,
                mine=mine, tube=t, sgap=sgap)
    return pts_lead + pts_bun[1:], info
