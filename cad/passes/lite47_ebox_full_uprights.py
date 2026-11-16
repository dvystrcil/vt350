# GUI pass: vt350-lite-46 -> vt350-lite-47   (headless = dry run, never saves)
# vt350#5. The e-box's outer uprights run the full height of the printer, so the front reads as one even frame with
# the door closed (user, 2026-11-16: "the verticals for the ebox, should be the full height of the printer ... then
# add the counter bores"; "lets do it only for the ebox verticals so that looking at the printer straight on it is
# uniform"). Only the e-box corners change; the printer's own corners stay as lite-46 has them.
#  - The four long rails (front 2040, rear 4040, top and bottom) stop at the e-box uprights' inner face, X E_IN
#    (lite-46: X E_OUT). Each rail's piece past X E_IN is cut off, or, where the boolean fails (this model's 2040s),
#    re-extruded from its own low end face to X E_IN.
#  - The front e-box upright: 2020, Y -90..-70, Z -50..690 (lite-46: Z -10..650).
#  - The rear e-box upright becomes a 2040 turned 40 along Y, Y 480..520, Z -50..690, so it covers the whole end of
#    the 4040 rear rail and the frame's back face is flush (user chose it from a plan sketch, 2026-11-16).
#  - The joints: each long rail's end is held by 2 x M5 DIN 912 socket-head screws along X through the upright into
#    the rail end's bores, at the same bores the stock joints used at the printer's corners (read from lite-45: front
#    2040s Y -80 at both bores, Z -40/-20 and 660/680; rear 4040s Y 490 and 510 in the outer row, Z -40 and 680).
#    The upright gets a D 5.5 clearance hole and a D 10.5 x 6 counterbore in its outer face (X E_OUT) for the washer
#    (1) and head (5), as the stock joints had. Screw length: through the upright's 14 mm below the counterbore plus
#    15 mm into the rail, as the stock joints' M5x50 had through a 40 mm upright: M5x30.
# NOT in this pass: the joints of the e-box side rails into these uprights. Screws along Y through the upright into
#    the side rails' end bores would cross the joint screws above in the upright (same Z): those joints are corner
#    brackets, a follow-up.
# Checks (refuses to save on any): the 4 long rails and 2 e-box uprights found once; rails X -520..E_IN; uprights at
# X E_IN..E_OUT, the Y given, Z -50..690; the rear upright 20 x 40; every joint hole cut into its upright (volume
# down by the hole); no overlap pair that lite-46 didn't already have, except each screw with the rail it's threaded
# into (logged); solids = lite-46 + 16.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-46.FCStd", f"{MODELS}/vt350-lite-47.FCStd"
X_L, E_IN, E_OUT = -520.0, 125.0, 145.0
Z_BOT, Z_TOP = -50.0, 690.0
FRONT, REAR = (-90.0, -70.0), (480.0, 520.0)
RAILS = {   # lite-46 label prefix -> joint screw (Y, Z) positions at its e-box end
    "2040 (2) (new front)": [(-80.0, -40.0), (-80.0, -20.0)],
    "2040 (2)001": [(-80.0, 660.0), (-80.0, 680.0)],
    "4040 (2)": [(490.0, -40.0), (510.0, -40.0)],
    "4040 (1)004": [(490.0, 680.0), (510.0, 680.0)]}
HOLE_D, CB_D, CB_DEPTH = 5.5, 10.5, 6.0
HEAD_D, HEAD_H, M5 = 8.5, 5.0, 5.0            # DIN 912 M5
WASH_ID, WASH_OD, WASH_T = 5.3, 10.0, 1.0     # DIN 125 M5, as the stock joints
ENGAGE = 15.0                                  # into the rail end, as the stock joints
SCREW_L = (E_OUT - CB_DEPTH + WASH_T) - (E_IN - ENGAGE)   # under the head to the tip: washer + upright + engage = 30
STEEL = (0.65, 0.67, 0.69)
SRC_2020, SRC_2040_X = "2020 (3)", "2040 (2)"


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def axial(f, axis):
    u0, u1, v0, v1 = f.ParameterRange
    n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    return abs(abs((n.x, n.y, n.z)[axis]) - 1) < 1e-6


def end_profile(shape, axis):
    """The member's own low end face(s) along `axis`, found by normal (booleans fail on this model's 2040s; their
    bores run through, so the end face is the profile)."""
    ob = shape.optimalBoundingBox(); end = (ob.XMin, ob.YMin, ob.ZMin)[axis]
    out = [f.copy() for f in shape.Faces if axial(f, axis) and abs(f.CenterOfMass[axis] - end) < 0.05]
    if not out: raise RuntimeError(f"no end face along axis {axis}")
    return Part.Compound(out), end


def extrude(faces, vec):
    sol = [f.extrude(vec) for f in faces.Faces]
    return (sol[0].multiFuse(sol[1:]) if len(sol) > 1 else sol[0]).removeSplitter()


def container(o):
    g = o.getParentGroup() or o.getParentGeoFeatureGroup()
    if g is None:
        g = next((x for x in o.InList if o in getattr(x, "Group", [])), None)
    return g


def trim_x(p, label, s, x1):
    """s with everything past X x1 removed: per solid, kept, dropped, cut by a box, or (a failed boolean) re-extruded
    from its own low X end face."""
    out = []
    for sol in s.Solids:
        ob = sol.optimalBoundingBox()
        if ob.XMax <= x1 + 0.01: out.append(sol); continue
        if ob.XMin >= x1 - 0.01: continue
        want = sol.Volume * (x1 - ob.XMin) / (ob.XMax - ob.XMin)     # exact for a plain extrusion; holes make it approx
        c = sol.common(box(ob.XMin - 1, x1, ob.YMin - 1, ob.YMax + 1, ob.ZMin - 1, ob.ZMax + 1))
        if c.Solids and abs(c.Volume - want) < 0.05 * want and abs(c.optimalBoundingBox().XMax - x1) < 0.05:
            out += c.Solids
        else:
            f, x0 = end_profile(sol, 0)
            p.log(f"{label}: piece X {ob.XMin:.1f}..{ob.XMax:.1f}: the cut failed ({len(c.Solids)} solids, "
                  f"{c.Volume:.0f} of {want:.0f} mm3); re-extruded from its end face to X {x1:.0f}")
            out.append(extrude(f, V(x1 - x0, 0, 0)))
    return out[0] if len(out) == 1 else Part.Compound(out)


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n_before = len(pr.leaves)
    old = {o.Name: pr.shapes[o.Name] for o in pr.leaves}

    def put(o, s):
        par = o.getGlobalPlacement().multiply(o.Placement.inverse())
        s = s.copy(); s.Placement = par.inverse().multiply(s.Placement)
        o.Shape = s; o.Placement = FreeCAD.Placement()

    def find(pred, what):
        c = [o for o in pr.leaves if pred(o)]
        p.check(len(c) == 1, f"{what} found once: {len(c)}")
        return c[0] if len(c) == 1 else None

    # 1. the long rails stop at X E_IN
    rails = {}
    for label in RAILS:
        o = find(lambda o, l=label: o.Label.startswith(l + " one piece X -520..145 (lite-46)"), label)
        if o is None: continue
        put(o, trim_x(p, label, pr.shapes[o.Name], E_IN))
        o.Label = f"{label} one piece X {X_L:.0f}..{E_IN:.0f} (lite-47)"; rails[label] = o
    # 2. the e-box uprights, full height
    up_f = find(lambda o: o.Label.startswith("2020 e-box front outer upright"), "e-box front upright")
    up_r = find(lambda o: o.Label.startswith("2020 e-box rear outer upright"), "e-box rear upright")
    s20 = pr.shapes[next(o for o in pr.leaves if o.Label == SRC_2020).Name]
    f20, z0 = end_profile(s20, 2)
    f20 = f20.translated(V(0, 0, -z0)); fb = f20.optimalBoundingBox()
    f20.translate(V(E_IN - fb.XMin, FRONT[0] - fb.YMin, Z_BOT))
    front = extrude(f20, V(0, 0, Z_TOP - Z_BOT))
    s40 = pr.shapes[next(o for o in pr.leaves if o.Label == SRC_2040_X and abs(pr.boxes[o.Name].YMin + 10) < 0.1).Name]
    f40, _ = end_profile(s40, 0)                                   # plane X: 20 in Y, 40 in Z
    f40.rotate(V(0, 0, 0), V(0, 1, 0), 90)                          # -> plane Z: 40 in X, 20 in Y
    f40.rotate(V(0, 0, 0), V(0, 0, 1), 90)                          # -> 20 in X, 40 in Y
    fb = f40.optimalBoundingBox()
    p.check(abs(fb.XLength - 20) < 0.3 and abs(fb.YLength - 40) < 0.3 and fb.ZLength < 0.01,
            f"rear upright profile 20 x 40 in plan: {fb.XLength:.2f} x {fb.YLength:.2f} x {fb.ZLength:.3f}")
    f40.translate(V(E_IN - fb.XMin, REAR[0] - fb.YMin, Z_BOT - fb.ZMin))
    rear = extrude(f40, V(0, 0, Z_TOP - Z_BOT))
    # the two 90-degree turns leave the profile 0.001 out of plane, so the extrusion leans a few microns into the side
    # rails it butts against (0.2 mm3 each, first dry run): clipped to its exact box
    rear = rear.common(box(E_IN, E_OUT, REAR[0], REAR[1], Z_BOT, Z_TOP))
    p.check(len(rear.Solids) == 1, f"rear upright clipped to its box: {len(rear.Solids)} solid, {rear.Volume:.0f} mm3")
    # 3. the joints: holes and counterbores in the uprights, screws and washers
    items, holes = [], []
    for label, pts in RAILS.items():
        for y, z in pts:
            hole = Part.makeCylinder(HOLE_D / 2, E_OUT - E_IN + 2, V(E_IN - 1, y, z), V(1, 0, 0)).fuse(
                Part.makeCylinder(CB_D / 2, CB_DEPTH + 1, V(E_OUT - CB_DEPTH, y, z), V(1, 0, 0)))
            x_wash = E_OUT - CB_DEPTH; x_head = x_wash + WASH_T
            screw = Part.makeCylinder(HEAD_D / 2, HEAD_H, V(x_head, y, z), V(1, 0, 0)).fuse(
                Part.makeCylinder(M5 / 2, SCREW_L, V(x_head - SCREW_L, y, z), V(1, 0, 0))).removeSplitter()
            washer = Part.makeCylinder(WASH_OD / 2, WASH_T, V(x_wash, y, z), V(1, 0, 0)).cut(
                Part.makeCylinder(WASH_ID / 2, WASH_T, V(x_wash, y, z), V(1, 0, 0)))
            holes.append((label, y, z, hole))
            items.append((label, f"M5x{SCREW_L:.0f}-Screw e-box joint {label} Y{y:.0f} Z{z:.0f} (DIN 912, lite-47)", screw))
            items.append((label, f"M5-Washer e-box joint {label} Y{y:.0f} Z{z:.0f} (DIN 125, lite-47)", washer))
    cut_log = []
    for name, s, yb in (("front", front, FRONT), ("rear", rear, REAR)):
        mine = [h for _, y, _, h in holes if yb[0] < y < yb[1]]
        v0 = s.Volume
        for h in mine: s = s.cut(h)
        lost = v0 - s.Volume
        p.check(len(s.Solids) == 1 and lost > len(mine) * 0.5 * 3.1416 * (HOLE_D / 2) ** 2 * (E_OUT - E_IN - CB_DEPTH),
                f"{name} upright: {len(mine)} joint holes cut, {lost:.0f} mm3 removed, {len(s.Solids)} solid")
        cut_log.append((name, len(mine), round(lost, 1)))
        if name == "front": front = s
        else: rear = s
    # lite-46's e-box side rails (also a turned 2040 profile) reach Y 480.00226, 2.3 microns into the rear upright's
    # face: a plain box at Y 480 overlaps them by 0.32 mm3 and one 0.001 off by 0 (probe, 2026-11-16). Clipped exact.
    sides = []
    for o in [o for o in pr.leaves if o.Label.startswith("2040 e-box outer side rail")]:
        s = pr.shapes[o.Name]; b = s.optimalBoundingBox()
        c = s.common(box(E_IN, E_OUT, FRONT[1], REAR[0], b.ZMin - 1, b.ZMax + 1))
        p.check(len(c.Solids) == 1 and abs(c.Volume - s.Volume) < 1.0,
                f"{o.Label}: clipped to Y {FRONT[1]:.0f}..{REAR[0]:.0f}, {len(c.Solids)} solid, {s.Volume - c.Volume:.3f} mm3 off")
        put(o, c); sides.append(o)
    p.check(len(sides) == 2, f"2 e-box side rails: {len(sides)}")
    if up_f: put(up_f, front); up_f.Label = f"2020 e-box front outer upright, Z {Z_BOT:.0f}..{Z_TOP:.0f} (lite-47)"
    if up_r: put(up_r, rear); up_r.Label = f"2040 e-box rear outer upright, Y 480..520, Z {Z_BOT:.0f}..{Z_TOP:.0f} (lite-47)"
    grp = container(next(o for o in pr.leaves if o.Label.startswith("M5x50-Screw")))
    new = []
    for _, label, s in items:
        new += p.add_solids(doc, grp, [("", s)], "Fastener", label, STEEL)
    doc.recompute(); pr.refresh()
    # checks
    for label, o in rails.items():
        b = pr.boxes[o.Name]
        p.check(abs(b.XMin - X_L) < 0.3 and abs(b.XMax - E_IN) < 0.3, f"{o.Label}: X {b.XMin:.2f}..{b.XMax:.2f}")
    for o, yb in ((up_f, FRONT), (up_r, REAR)):
        if o is None: continue
        b = pr.boxes[o.Name]
        p.check(abs(b.XMin - E_IN) < 0.3 and abs(b.XMax - E_OUT) < 0.3 and abs(b.YMin - yb[0]) < 0.3 and abs(b.YMax - yb[1]) < 0.3
                and abs(b.ZMin - Z_BOT) < 0.3 and abs(b.ZMax - Z_TOP) < 0.3,
                f"{o.Label}: X {b.XMin:.2f}..{b.XMax:.2f}, Y {b.YMin:.2f}..{b.YMax:.2f}, Z {b.ZMin:.2f}..{b.ZMax:.2f}")
    members = list(rails.values()) + [o for o in (up_f, up_r) if o] + sides + new
    names = {o.Name for o in members}
    env = {o.Name for o in pr.leaves if o.Label.startswith("Ebox envelope")}
    rail_of = {o.Name: rails.get(lab) for o, (lab, _, _) in zip(new, items)}
    threaded = {(o.Name, rail_of[o.Name].Name) for o in new if rail_of.get(o.Name) and "Screw" in o.Label}
    cand = [(m, o) for m in members for o in pr.leaves if o.Name != m.Name and o.Name not in env
            and (o.Name not in names or m.Name < o.Name) and pr.boxes[o.Name].intersect(pr.shapes[m.Name].BoundBox)]
    vnew = p.volumes([(pr.shapes[m.Name], pr.shapes[o.Name]) for m, o in cand])
    vold = p.volumes([(old[m.Name], old[o.Name]) if m.Name in old and o.Name in old else (Part.Shape(), Part.Shape())
                      for m, o in cand])
    fresh, kept, thread = [], [], []
    for (m, o), a, b in zip(cand, vnew, vold):
        b = 0.0 if b == float("inf") and not (m.Name in old and o.Name in old) else b
        pair = (m.Label[:44], o.Label[:36], round(a, 1))
        if (m.Name, o.Name) in threaded or (o.Name, m.Name) in threaded: thread.append(pair); continue
        if b > 1e-2: kept.append(pair); continue
        if a > 1e-2: fresh.append(pair)
    p.log(f"info screw threads in their rail ends (expected): {len(thread)} {thread}")
    p.log(f"info overlaps lite-46 already has (not a failure): {len(kept)} {kept}")
    p.check(not fresh, f"new overlaps (pairs that didn't overlap in lite-46): {len(fresh)} {fresh[:12]}")
    p.check(len(pr.leaves) == n_before + 16, f"solids: {len(pr.leaves)} (lite-46 + 8 screws + 8 washers = {n_before + 16})")
    p.dump({"e_in": E_IN, "e_out": E_OUT, "z": [Z_BOT, Z_TOP], "screw": f"M5x{SCREW_L:.0f} DIN 912", "joints": {k: v for k, v in RAILS.items()},
            "holes_cut": cut_log, "counterbore": [CB_D, CB_DEPTH]})
    return p.finish([(doc, DST)])


litelib.Pass("lite47_ebox_full_uprights").run(main)
