# GUI pass: vt350-lite-45 -> vt350-lite-46   (headless = dry run, never saves)
# vt350#5. The side pack is built INTO the printer's frame (user, 2026-11-16): "extend the frame, top at 690. can we
# keep the top extrusions one peice across?", then the bottom too ("Yes, top and bottom").
#  - The four X rails (front 2040 and rear 4040, top and bottom), 470 mm between the uprights until now, become ONE
#    piece each from the left frame face (X -520) to the e-box's outer face (X E_OUT): their own profile, extruded
#    longer. The uprights stand on the bottom rails and the top rails cap them.
#  - So the four printer uprights (front 2040s, rear 4040s) lose 40 mm at each end: Z -10..650 (740 -> 660).
#  - The e-box gets outer uprights (2020, between the long rails: front at Y -90..-70, rear at Y 480..500) and outer
#    side rails top and bottom (2040, standing 40 tall like the printer's, Y -70..480), all at X E_IN..E_OUT. The
#    e-box door (2040 V-slot frame, plexi in the groove, clicky-clack, handle Z 465) is the next pass.
#  - The right side panel (and its paint) is trimmed to Z -10..650, so it fits between the long rails.
#  - The M5 screws that joined the old X rails' ends to the uprights (along X, 16 + their 16 washers) go: those ends
#    no longer exist. The screws joining the side rails to the corners (along Y) stay: the side rails now butt into
#    the long rails, at the same bores.
# NOT in this pass (said so in the PR): the new rail-to-upright corner joints. Vertical screws through the rails into
#    the upright ends would hit the side-rail joint screws, which use the same bores; the joint (corner brackets, or
#    the centre bore) is a follow-up.
# E-box depth: E_IN, set by the PSU (below); still a parameter.
# New members are copies of existing frame extrusions (so they keep the frame's group, material and colour rule),
# given the new shapes; changed members keep their objects. Each long rail is the stock rail, untouched, with its own
# profile extruded onto both ends (the 2040s don't survive OCC booleans, so theirs are compounds of three butted
# pieces). The side rails' joint screws (M5x50 along Y) used to pass through the uprights' corners; they now pass
# through the long rails, which get a D 5.5 clearance hole and a D 10.5 x 6 counterbore for the washer and head.
# Checks (refuses to save on any): every member found once where expected; each rail's profile the same at two
# places; the long rails X -520..E_OUT; the uprights Z -10..650; the e-box members where specified; 32 fasteners
# removed; no overlap ADDED by the new and changed members (the overlaps lite-45 already has, the back panel and the
# Z-motor mount's screws in the stock rear rails, are logged; so is the e-box envelope, which concept C re-lays
# out); solids = lite-45 - 32 + 4.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
from litelib import MODELS
V = FreeCAD.Vector
SRC = os.environ.get("LITE46_SRC", f"{MODELS}/vt350-lite-45.FCStd")      # override: a dry run against an older lite
DST = f"{MODELS}/vt350-lite-46.FCStd"
X_L = -520.0                    # the left frame face
# E_IN from the BOSYTRO 600 W PSU (user, 2026-11-16: 215 x 113 x 50, "there are printable din mounts for this
# PSU"): lying flat on a printed DIN clip, its 215 x 113 face to the rail. DIN rail face X 57.5 + clip ~10 (assumed,
# not measured) + PSU 50 + 5 clear = X 122.5 -> the outer members' inner face at X 125. Terminals are on a 113 x 50
# end, so the wiring leaves sideways, not outward.
E_IN, E_W = 125.0, 20.0         # e-box outer members: inner face X, width (2020/2040 20 thick)
E_OUT = E_IN + E_W
Z_BOT, Z_TOP = -50.0, 690.0
UP_Z0, UP_Z1 = Z_BOT + 40.0, Z_TOP - 40.0
FRONT, REAR = (-90.0, -70.0), (480.0, 520.0)
RAILS = {   # label -> (Y band, Z band)
    "2040 (2) (new front)": (FRONT, (Z_BOT, UP_Z0)), "2040 (2)001": (FRONT, (UP_Z1, Z_TOP)),
    "4040 (2)": (REAR, (Z_BOT, UP_Z0)), "4040 (1)004": (REAR, (UP_Z1, Z_TOP))}
UPRIGHTS = {"2040": FRONT, "2040(Mirror)": FRONT, "4040": REAR, "4040(Mirror)": REAR}
CB_DEPTH = 6.0                  # joint-screw counterbore in the long rails: washer 1 + head 5
SRC_2020, SRC_2040_X = "2020 (3)", "2040 (2)"     # profile sources: a vertical 2020, a 2040 rail along X


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def profile(shape, axis, at):
    """An extrusion's cross-section at `at` along `axis` (0 X, 1 Y, 2 Z), holes kept: the faces of a 1 mm slab of it
    that lie on the plane `at`. (Slicing gave open wires on these profiles, and the end faces include end features;
    a boolean slab's faces are closed.) Returns (compound of faces, area)."""
    b = shape.BoundBox; lo = [b.XMin - 1, b.YMin - 1, b.ZMin - 1]; hi = [b.XMax + 1, b.YMax + 1, b.ZMax + 1]
    lo[axis], hi[axis] = at, at + 1.0
    cut = box(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
    slab = shape.common(cut)
    if not slab.Faces: slab = shape.common([cut], 1e-4)      # OCC returned nothing (seen on the front 2040): fuzzy
    def across(f):      # a plane face perpendicular to the axis, on `at` (BoundBoxes here carry a loose tolerance)
        u0, u1, v0, v1 = f.ParameterRange
        n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        return abs(abs((n.x, n.y, n.z)[axis]) - 1) < 1e-6 and abs(f.CenterOfMass[axis] - at) < 0.05
    out = [f.copy() for f in slab.Faces if across(f)]
    if not out:
        # every boolean on this model's 2040s comes back empty (fuzzy too): use the member's own low end face, found
        # by its normal, moved to `at` (the 2040's bores run through, so its end face is its profile)
        ob = shape.optimalBoundingBox(); end = round((ob.XMin, ob.YMin, ob.ZMin)[axis])
        def at_end(f):
            u0, u1, v0, v1 = f.ParameterRange
            n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
            return abs(abs((n.x, n.y, n.z)[axis]) - 1) < 1e-6 and abs(f.CenterOfMass[axis] - end) < 0.05
        out = [f.copy() for f in shape.Faces if at_end(f)]
        d = [0, 0, 0]; d[axis] = at - end
        for f in out: f.translate(V(*d))
    if not out: raise RuntimeError(f"no section along axis {axis} at {at}")
    c = Part.Compound(out)
    return c, c.Area


def extrude(faces, vec):
    sol = [f.extrude(vec) for f in faces.Faces]
    return (sol[0].multiFuse(sol[1:]) if len(sol) > 1 else sol[0]).removeSplitter()


def container(o):
    """The group that holds o: a DocumentObjectGroup, else its App::Part, else whatever lists it in Group."""
    g = o.getParentGroup() or o.getParentGeoFeatureGroup()
    if g is None:
        g = next((x for x in o.InList if o in getattr(x, "Group", [])), None)
    return g


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n_before = len(pr.leaves)
    by_label = {}
    for o in pr.leaves: by_label.setdefault(o.Label, []).append(o)

    def one(label, yband, zband=None):
        c = [o for o in by_label.get(label, []) if abs(pr.boxes[o.Name].YMin - yband[0]) < 0.1 and abs(pr.boxes[o.Name].YMax - yband[1]) < 0.1
             and (zband is None or (abs(pr.boxes[o.Name].ZMin - zband[0]) < 0.1 and abs(pr.boxes[o.Name].ZMax - zband[1]) < 0.1))]
        p.check(len(c) == 1, f"{label} found once at Y {yband} Z {zband}: {len(c)}")
        return c[0] if c else None

    def put(o, s):
        par = o.getGlobalPlacement().multiply(o.Placement.inverse())
        s = s.copy(); s.Placement = par.inverse().multiply(s.Placement)
        o.Shape = s; o.Placement = FreeCAD.Placement()

    changed = []
    old = {o.Name: pr.shapes[o.Name] for o in pr.leaves}      # lite-45's shapes: overlap baseline
    # 1. the long rails: the stock rail kept as it is (every feature already modelled in it stays), extended at
    #    both ends with its own profile, taken from a slab 40 mm in from its left end (and compared with one 80 mm in)
    ext_axis_screws = [o for o in pr.leaves if o.Label.startswith("M5x") and pr.boxes[o.Name].YLength >= 15
                       and pr.boxes[o.Name].XLength < 11 and pr.boxes[o.Name].ZLength < 11]   # screws along Y
    holes, compounds = [], []
    for label, (yb, zb) in RAILS.items():
        o = one(label, yb, zb)
        if o is None: continue
        s0 = pr.shapes[o.Name]; b = s0.BoundBox
        x0 = round(b.XMin); secs = []
        for d in (40.0, 80.0, 60.0, 100.0, 120.0, 150.0):
            try: secs.append((d,) + profile(s0, 0, x0 + d))
            except RuntimeError as e: p.log(f"{label}: no section {d:.0f} mm in ({e})")
            if len(secs) == 2: break
        p.check(len(secs) == 2 and abs(secs[0][2] - secs[1][2]) < 0.005 * secs[0][2],
                f"{label}: the profile is the same at two places ({[(d, round(a, 1)) for d, _, a in secs]} mm in, mm2)")
        if len(secs) < 2: continue
        _, f, area0 = secs[0]; fx = x0 + secs[0][0]
        x1 = round(b.XMax)
        lpiece = extrude(f.translated(V(X_L - fx, 0, 0)), V(x0 - X_L, 0, 0)) if x0 - X_L > 0.01 else None
        rpiece = extrude(f.translated(V(x1 - fx, 0, 0)), V(E_OUT - x1, 0, 0))
        pieces = [x for x in (lpiece, rpiece) if x is not None]
        long = s0.fuse(pieces).removeSplitter()
        want = s0.Volume + sum(x.Volume for x in pieces)
        if len(long.Solids) != 1 or abs(long.Volume - want) > 0.01 * want:
            # the 2040s don't survive booleans: one part made of the stock rail and its extensions, butted end to end
            p.log(f"{label}: the fuse failed ({len(long.Solids)} solids, {long.Volume:.0f} of {want:.0f} mm3); "
                  f"kept as a compound of the stock rail and {len(pieces)} extensions")
            long = Part.Compound([s0] + pieces); compounds.append(label)
        # the side rails' joint screws (along Y, into the side rails' end bores) now pass through this rail where
        # the upright used to be: in the build, a drilled clearance hole (D 5.5) for each
        lb = long.BoundBox
        for sc in ext_axis_screws:
            sb = pr.boxes[sc.Name]
            if sb.XMin > lb.XMin and sb.XMax < lb.XMax and sb.ZMin > lb.ZMin and sb.ZMax < lb.ZMax and \
               sb.YMin < lb.YMax and sb.YMax > lb.YMin:
                cx, cz = (sb.XMin + sb.XMax) / 2, (sb.ZMin + sb.ZMax) / 2
                if long.common(pr.shapes[sc.Name]).Volume > 1e-3:
                    long = long.cut(Part.makeCylinder(5.5 / 2, lb.YLength + 2, V(cx, lb.YMin - 1, cz), V(0, 1, 0)))
                    # the head and its washer (6 mm: 1 + 5) sit at the rail's outer face: counterbore D 10.5
                    if sb.YMax > lb.YMax - 0.5:
                        cb = Part.makeCylinder(10.5 / 2, CB_DEPTH + 1, V(cx, lb.YMax - CB_DEPTH, cz), V(0, 1, 0))
                    else:
                        cb = Part.makeCylinder(10.5 / 2, CB_DEPTH + 1, V(cx, lb.YMin - 1, cz), V(0, 1, 0))
                    long = long.cut(cb)
                    holes.append((label, sc.Label, round(cx, 1), round(cz, 1)))
        put(o, long); o.Label = f"{label} one piece X {X_L:.0f}..{E_OUT:.0f} (lite-46)"
        changed.append((o, area0))
    p.log(f"clearance holes (D 5.5, along Y) drilled in the long rails for the side rails' joint screws: {len(holes)} {holes}")
    # 2. the printer uprights: Z UP_Z0..UP_Z1
    for label, yb in UPRIGHTS.items():
        for o in [o for o in by_label.get(label, []) if abs(pr.boxes[o.Name].YMin - yb[0]) < 0.1 and abs(pr.boxes[o.Name].ZMax - Z_TOP) < 0.1]:
            s = pr.shapes[o.Name]; b = s.BoundBox
            put(o, s.common(box(b.XMin - 1, b.XMax + 1, b.YMin - 1, b.YMax + 1, UP_Z0, UP_Z1)))
            o.Label = f"{label} upright Z {UP_Z0:.0f}..{UP_Z1:.0f} (lite-46)"
            changed.append((o, None))
    p.check(sum(1 for o, a in changed if a is None) == 4, f"4 printer uprights shortened: {sum(1 for o, a in changed if a is None)}")
    # 3. the e-box members, copies of frame extrusions with new shapes
    src20 = next(o for o in pr.leaves if o.Label == SRC_2020)
    src40 = next(o for o in pr.leaves if o.Label == SRC_2040_X and abs(pr.boxes[o.Name].YMin + 10) < 0.1)
    s20 = pr.shapes[src20.Name]; f20, _ = profile(s20, 2, round(s20.BoundBox.ZMin) + 100.0)
    s40 = pr.shapes[src40.Name]; f40, _ = profile(s40, 0, round(s40.BoundBox.XMin) + 40.0)
    f40.rotate(V(f40.optimalBoundingBox().XMin, 0, 0), V(0, 0, 1), 90)          # the 20 x 40 profile now faces along Y
    newspec = []
    for name, y0 in (("front", FRONT[0]), ("rear", REAR[0])):
        f = f20.copy(); fb = f.optimalBoundingBox()
        f.translate(V(E_IN - fb.XMin, y0 - fb.YMin, UP_Z0 - fb.ZMin))
        newspec.append((src20, f"2020 e-box {name} outer upright, Z {UP_Z0:.0f}..{UP_Z1:.0f} (lite-46)", extrude(f, V(0, 0, UP_Z1 - UP_Z0))))
    for name, z0 in (("bottom", Z_BOT), ("top", UP_Z1)):
        f = f40.copy(); fb = f.optimalBoundingBox()
        f.translate(V(E_IN - fb.XMin, FRONT[1] - fb.YMin, z0 - fb.ZMin))
        newspec.append((src40, f"2040 e-box outer side rail, {name} (lite-46)", extrude(f, V(0, REAR[0] - FRONT[1], 0))))
    new = []
    for srco, label, s in newspec:
        c = doc.copyObject(srco, False); container(srco).addObject(c)
        put(c, s); c.Label = label; new.append(c)
    # 4. the right side panel and its paint: Z UP_Z0..UP_Z1
    for o in [o for o in pr.leaves if o.Label.startswith("Right side panel (3 mm)")]:
        s = pr.shapes[o.Name]; b = s.BoundBox
        put(o, s.common(box(b.XMin - 1, b.XMax + 1, b.YMin - 1, b.YMax + 1, UP_Z0, UP_Z1)))
        changed.append((o, None))
    # 5. the old X rails' end joints: M5x50 screws along X and their washers, in the corner bands
    def in_bands(b):
        return any(b.YMin >= yb[0] - 0.5 and b.YMax <= yb[1] + 0.5 for yb in (FRONT, REAR)) and \
               (b.ZMax <= UP_Z0 + 0.5 or b.ZMin >= UP_Z1 - 0.5)
    gone = [o for o in pr.leaves if "Fasteners001" in (container(o).Label if container(o) else "")
            and in_bands(pr.boxes[o.Name])
            and ((o.Label.startswith("M5x50-Screw") and pr.boxes[o.Name].XLength >= 50)
                 or (o.Label.startswith("M5-Washer") and pr.boxes[o.Name].XLength <= 1.5))]
    p.check(len(gone) == 32, f"old rail-end joints removed: {len(gone)} (16 M5x50 along X + 16 washers)")
    for o in gone: doc.removeObject(o.Name)
    doc.recompute(); pr.refresh()
    # checks
    for o, area0 in changed:
        b = pr.boxes[o.Name]
        if area0 is not None:
            nsol = len(pr.shapes[o.Name].Solids)
            p.check(abs(b.XMin - X_L) < 0.3 and abs(b.XMax - E_OUT) < 0.3 and (nsol == 1 or o.Label.split(" one piece")[0] in compounds),
                    f"{o.Label}: X {b.XMin:.2f}..{b.XMax:.2f}, {nsol} solid(s), profile {area0:.1f} mm2")
        elif o.Label.startswith(("2040 up", "2040(Mirror) up", "4040 up", "4040(Mirror) up")):
            p.check(abs(b.ZMin - UP_Z0) < 0.05 and abs(b.ZMax - UP_Z1) < 0.05, f"{o.Label}: Z {b.ZMin:.2f}..{b.ZMax:.2f}")
    for o in new:
        b = pr.boxes[o.Name]
        p.check(abs(b.XMin - E_IN) < 0.05 and abs(b.XMax - E_OUT) < 0.05, f"{o.Label}: X {b.XMin:.2f}..{b.XMax:.2f}, "
                f"Y {b.YMin:.2f}..{b.YMax:.2f}, Z {b.ZMin:.2f}..{b.ZMax:.2f}")
    members = [o for o, a in changed] + new
    env = {o.Name for o in pr.leaves if o.Label.startswith("Ebox envelope")}
    member_names = {o.Name for o in members}
    # overlap the NEW geometry adds: lite-45 already has some (the back panel and the Z-motor mount's screws reach into
    # the stock rear rails), so each pair's volume is compared with the same pair in lite-45
    cand = [(m, o) for m in members for o in pr.leaves if o.Name not in member_names and o.Name not in env
            and pr.boxes[o.Name].intersect(pr.shapes[m.Name].BoundBox)]
    vnew = p.volumes([(pr.shapes[m.Name], pr.shapes[o.Name]) for m, o in cand])
    vold = p.volumes([(old[m.Name], old[o.Name]) if m.Name in old and o.Name in old else (Part.Shape(), Part.Shape())
                      for m, o in cand])
    added = [(m.Label[:40], o.Label[:30], round(a - (b if b != float("inf") else 0), 1)) for (m, o), a, b in zip(cand, vnew, vold)
             if a - (b if b != float("inf") else 0) > 1e-2]
    kept = [(m.Label[:40], o.Label[:30], round(b, 1)) for (m, o), a, b in zip(cand, vnew, vold) if b > 1e-2 and b != float("inf")]
    p.log(f"info overlaps already in lite-45 (not a failure): {len(kept)} {kept}")
    # a pair that already overlapped in lite-45 may grow (the back panel, modelled into the stock rear rails, runs on
    # into their new end pieces where the uprights were): logged. A pair that didn't overlap before fails.
    before = {(m[:40], o[:30]) for m, o, _ in kept}
    grown = [h for h in added if (h[0], h[1]) in before]
    fresh = [h for h in added if (h[0], h[1]) not in before]
    p.log(f"info existing overlaps that grew with the longer members (not a failure): {grown}")
    p.check(not fresh, f"new overlaps (pairs that didn't overlap in lite-45): {len(fresh)} {fresh[:12]}")
    envp = [(m, e) for m in members for e in env if pr.boxes[e].intersect(pr.shapes[m.Name].BoundBox)]
    envh = [(m.Label[:40], round(v, 1)) for (m, e), v in zip(envp, p.volumes([(pr.shapes[m.Name], pr.shapes[e]) for m, e in envp])) if v > 1e-3]
    p.log(f"info e-box envelope overlapping the members (not a failure; concept C re-lays it out): {envh}")
    p.check(len(pr.leaves) == n_before - 32 + 4, f"solids: {len(pr.leaves)} (lite-45 - 32 joint parts + 4 e-box members = {n_before - 28})")
    p.dump({"holes": holes, "compound_rails": compounds, "x_left": X_L, "e_in": E_IN, "e_out": E_OUT, "uprights_z": [UP_Z0, UP_Z1], "rail_length": E_OUT - X_L,
            "removed": len(gone), "new": [o.Label for o in new]})
    return p.finish([(doc, DST)])


litelib.Pass("lite46_frame_extension").run(main)
