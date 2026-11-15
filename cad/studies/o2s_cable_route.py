# #3 AC2 (+ #19): the O2S USB cable's route, from each head's wire restraint (lite-35) to the roof, bundled with that
# head's bowden tube. Headless, read-only, never saves:
#   VT350_MODEL=/home/dan/Documents/VT350/vt350-lite-35.FCStd $APP freecadcmd cad/studies/o2s_cable_route.py
# Log: $VT350_WORK/logs/o2s_cable_route.log (+ .json).
#
# The cable leaves the restraint's lock straight up (the lock's Ø5.4 channel, axis +Z; upstream's USB stub is a
# Ø5.0 cable under a Ø9.8 plug). The plan is the usual toolchanger umbilical: the cable is tied along its own head's
# bowden tube, which lite-30 routed to the roof's top-rear exit (#3) with a bend radius >= 100 mm. So per head:
#  1. the tube's curve, from its stored route (Inlet, ExitPoint, ExitDir, HandleInlet, HandleExit; bezier.py). lite-31
#     made the middle heads as copies translated in X, whose stored Inlet/ExitPoint are still the source's: the X
#     offset comes from each copy's geometry vs its source (checked: Y, Z and size unchanged);
#  2. the JOIN: for each point along the tube, the cable's lead-in is a Bezier from the lock top (tangent +Z) to a
#     point beside the tube (tube radius + cable radius + GAP, on the restraint's side), arriving along the tube's
#     tangent. Handles are searched for the largest smallest bend radius (bezier.ranked_handles' method) at each join;
#     the join taken is the LOWEST whose lead-in still bends no tighter than MIN_R, so the cable is tied to the tube
#     as close to the head as it can be (a join near the roof leaves the cable swinging on its own);
#  3. from the join the cable runs beside the tube to the roof's underside; its bend radius there is >= the tube's
#     minus the offset (a lower bound);
#  4. clearance: the cable's centreline sampled every ~4 mm (lead-in + bundle up to the roof), each point's distance
#     to every solid outside its own head's O2S, restraint and tube, minus the cable radius (distToShape raised to
#     the box gap, as in sweep_toolhead); and cable vs cable for neighbouring heads.
# Docked pose only. With the cable tied to the tube, the moving bundle behaves like the tube, whose fixed-length
# behaviour over the travel is #3's open question (the 2026-11-04 study); this adds the cable's length to that.
# The cable's minimum bend radius is not known (no datasheet for the O2S cable): MIN_R is a stated assumption, 10 x
# the Ø5.0 cable, the usual rule for a cable that flexes.
import FreeCAD, Part, os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))
import litelib, bezier
from litelib import is_leaf, MODELS
V = FreeCAD.Vector
MODEL = os.environ.get("VT350_MODEL", f"{MODELS}/vt350-lite-35.FCStd")
R_TUBE, R_CABLE, GAP = 4.12 / 2, 5.0 / 2, 0.5         # PTFE OD 4.12 (measured, #3); cable Ø5.0 (upstream stub)
MIN_R = 50.0                                           # assumption: 10 x OD for a flexing cable
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


def main(p):
    pr = p.open(MODEL); doc = pr.doc
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    src = {k: obj(k) for k in ("Bowden Left", "Bowden Right")}
    res, cables = {}, {}
    for h, tlab, slab in HEADS:
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
        off = V(dx, 0, 0)
        tp = bezier.tube_poles(tuple(V(s.Inlet) + off), tuple(V(s.ExitPoint) + off), tuple(V(s.ExitDir)),
                               s.HandleInlet.Value, s.HandleExit.Value)
        r_tube = bezier.min_radius(tp)
        p.check(abs(r_tube - s.MinBendRadius.Value) < 0.5, f"{h}: tube curve rebuilt from its stored route, R {r_tube:.2f} "
                f"(stored {s.MinBendRadius.Value:.2f})")
        p.check(abs(bez(tp, 0).z - pr.shapes[t.Name].BoundBox.ZMin) < 0.05, f"{h}: the curve starts at the tube's bottom "
                f"(Z {bez(tp, 0).z:.2f} vs {pr.shapes[t.Name].BoundBox.ZMin:.2f})")
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
        pts_bun = []
        for i, q in enumerate(pts_tube):
            uu = u + (u_roof - u) * i / 160; Ti = tangent(tp, uu); wi = w - Ti * w.dot(Ti); wi.normalize()
            pts_bun.append(q + wi * sgap)
        L_bun2 = sum((pts_bun[i + 1] - pts_bun[i]).Length for i in range(len(pts_bun) - 1))
        r_bun = r_tube - sgap
        cables[h] = pts_lead + pts_bun[1:]
        p.log(f"{h}: lock top {tuple(round(x, 2) for x in P0)}; join at tube u {u:.3f} = Z {bez(tp, u).z:.1f}, "
              f"{(bez(tp, u) - P0).Length:.1f} mm from the lock; lead-in handles {a:.0f}/{b:.0f}, length {L_lead:.1f}; "
              f"bundle to the roof {L_bun2:.1f} (tube {L_bun:.1f})")
        p.check(r_lead >= MIN_R and r_bun >= MIN_R, f"{h}: bend R lead-in {r_lead:.1f}, beside the tube >= {r_bun:.1f} "
                f"(MIN_R {MIN_R:.0f}, assumed 10 x Ø5.0)")
        # clearance vs everything outside this head's O2S/restraint/sensor parts and its own tube
        excl = {o.Name for o in mine if o.Label.startswith(OWN)} | {t.Name}
        if h == "Left Toolhead": excl |= {obj("Bowden Right").Name}                 # filed under the left head
        obst = [o for o in pr.leaves if o.Name not in excl]
        near = []
        for k, q in enumerate(cables[h]):
            for o in obst:
                g = box_gap(q, pr.boxes[o.Name])
                if g < R_CABLE + 3.0:
                    d = Part.Vertex(q).distToShape(pr.shapes[o.Name])[0]
                    near.append((max(d, g) - R_CABLE, o.Label, k < len(pts_lead), round(q.z, 1)))
        near.sort()
        hits = [x for x in near if x[0] < 0.0]
        p.log(f"{h}: nearest to the cable (clearance, part, in lead-in, Z): {[(round(x[0], 2), x[1][:40], x[2], x[3]) for x in near[:4]]}")
        p.check(not hits, f"{h}: the cable clears everything outside its own O2S/restraint/tube "
                f"({len(near)} close samples; min {near[0][0] if near else float('inf'):.2f} mm) {[(round(x[0], 2), x[1][:40]) for x in hits[:3]]}")
        res[h] = dict(lock_top=[round(x, 2) for x in P0], join_u=round(u, 3), join_z=round(bez(tp, u).z, 1),
                      lead_in_mm=round(L_lead, 1), bundle_mm=round(L_bun2, 1), total_to_roof_mm=round(L_lead + L_bun2, 1),
                      r_lead_in=round(r_lead, 1), r_bundle_min=round(r_bun, 1), tube_r=round(r_tube, 2),
                      nearest=[(round(x[0], 2), x[1], x[2], x[3]) for x in near[:3]])
    # cable vs cable, neighbours
    hs = [h for h, _, _ in HEADS]
    for i in range(len(hs) - 1):
        A, B = cables[hs[i]], cables[hs[i + 1]]
        dmin = min((a - b).Length for a in A for b in B) - 2 * R_CABLE
        p.check(dmin > 0, f"cable {hs[i]} vs {hs[i + 1]}: {dmin:.1f} mm apart")
        res[f"{hs[i]} | {hs[i + 1]}"] = round(dmin, 1)
    p.dump({"model": os.path.basename(MODEL), "cable_od_mm": 2 * R_CABLE, "min_r_assumed_mm": MIN_R, "heads": res})
    p.log("o2s_cable_route: done (read-only, nothing saved)")


litelib.Pass("o2s_cable_route").run(main)
