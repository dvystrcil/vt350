# #3 AC2 (+ #19): the O2S USB cable's route, from each head's wire restraint (lite-35) to the roof, bundled with that
# head's bowden tube. Headless, read-only, never saves:
#   VT350_MODEL=/home/dan/Documents/VT350/vt350-lite-35.FCStd $APP freecadcmd cad/studies/o2s_cable_route.py
# Log: $VT350_WORK/logs/o2s_cable_route.log (+ .json).
#
# The cable leaves the restraint's lock straight up (the lock's Ø5.4 channel, axis +Z; upstream's USB stub is a
# Ø5.0 cable under a Ø9.8 plug; the user measured the real cable at 5.1 mm). The plan is the usual toolchanger umbilical: the cable is tied along its own head's
# bowden tube, which lite-30 routed to the roof's top-rear exit (#3) with a bend radius >= 100 mm. So per head:
#  1. the tube's curve, from its stored route (Inlet, ExitPoint, ExitDir, HandleInlet, HandleExit; bezier.py). lite-31
#     made the middle heads as copies translated in X. The stored Inlet/ExitPoint X is STALE on every tube (each
#     tube lies in a plane X = const; Bowden Left's solid is at X -409.70, its props say -399.0; found 2026-11-14 by
#     lite36_roof_exit.py, after #169/#171 had used the stored X). So X is taken from the solid (its section at Z 600)
#     and the rebuilt curve is checked against the solid's section centres at several heights;
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
# the cable's OD (5.1 mm, measured), the usual rule for a cable that flexes.
import FreeCAD, Part, os, sys, math
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) if "__file__" in globals() \
    else os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "cad/scripts")]
import litelib, bezier
from litelib import is_leaf, MODELS
from o2s_route import R_CABLE, MIN_R, HEADS, OWN, bez, box_gap, route       # the route itself (moved there 2026-11-14)
V = FreeCAD.Vector
MODEL = os.environ.get("VT350_MODEL", f"{MODELS}/vt350-lite-35.FCStd")


def main(p):
    pr = p.open(MODEL); doc = pr.doc
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    src = {k: obj(k) for k in ("Bowden Left", "Bowden Right")}
    res, cables = {}, {}
    for h, tlab, slab in HEADS:
        cables[h], I = route(p, pr, obj, h, tlab, slab, src)
        mine, t, pts_lead = I["mine"], I["tube"], I["pts_lead"]
        P0, u, L_lead, L_bun2, r_lead, r_bun, r_tube = I["P0"], I["u_join"], I["L_lead"], I["L_bun"], I["r_lead"], I["r_bun"], I["r_tube"]
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
        res[h] = dict(lock_top=[round(x, 2) for x in P0], join_u=round(u, 3), join_z=round(bez(I['tube_poles'], u).z, 1),
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
