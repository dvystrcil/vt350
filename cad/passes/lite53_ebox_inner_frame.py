# GUI pass: vt350-lite-52 -> vt350-lite-53   (headless = dry run, never saves)
# vt350#5. The e-box gets an inner 2020 frame that the DIN rails mount on, so nothing is drilled through the printer's
# side panel (user, 2026-11-16: "I would rather not drill. if I add the 2020s then I have room to add and move things
# about later"; on the first render: no middle upright, and the cross members 20 mm in from the top and bottom "this
# will allow us to put panels in uniformly with the rest of the printer").
#  - Inner frame, all 2020 at X IN0..IN1 (1 mm clear of the right wall felt's outer liner at X 44):
#    bottom and top cross members along Y, butted between the front and rear long rails, Z -30..-10 and 650..670
#    (flush with the long rails' inner top and bottom faces); front and rear uprights between them, Z -10..650.
#    The front upright is at Y -58..-38, not on the front long rail: the printer door's hinges and latch handle wrap
#    round the front-right corner to X 51, Y -61.6, Z 405..525.
#  - Depth: a DIN rail on the inner frame's face (X IN1) has its face at IN1 + 7.5; + printed PSU clip ~10 (assumed,
#    as lite-46) + the BOSYTRO's 50 + 5 clear = X 137.5, so the e-box's outer members move from X 125 to E_IN = 140.
#    The four long rails get a 15 mm piece of their own end face extruded onto the end (X 125..140); the outer
#    uprights, the outer side rails and lite-47's 16 joint fasteners move +15 in X.
#  - Links (lite-52): the top front rail, the top side rail and 7 of 8 joint screws and washers are App::Links to a
#    real part. Only real parts are changed; a link to a changed part follows it. Every final position is checked.
# NOT in this pass: the inner frame's joints (blind joints or corner brackets) and the DIN rails and parts on it
#    (the e-box layout, vt350-ebox-2.FCStd, next).
# Checks (refuses to save on any): every member found once; the long rails X -520..140; the outer members and
# fasteners 15 further out; each new member where specified and 20 x 20 in section; no overlap pair that lite-52
# didn't already have (the e-box envelope excluded: it's re-laid out next); solids = lite-52 + 4.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-52.FCStd", f"{MODELS}/vt350-lite-53.FCStd"
X_L, E_IN_OLD, E_IN = -520.0, 125.0, 140.0
DX = E_IN - E_IN_OLD
E_OUT = E_IN + 20.0
IN0, IN1 = 45.0, 65.0                      # inner frame, X
Y_F, Y_R = -70.0, 480.0                    # the long rails' inner faces (front 2040 Y -90..-70, rear 4040 Y 480..520)
Z_BOT, Z_TOP = -50.0, 690.0
UPRIGHTS = {"front": -58.0, "rear": 460.0}     # Y of each inner upright's low face (no middle one: owner, 2026-11-16)
CROSS_Z = {"bottom": (-30.0, -10.0), "top": (650.0, 670.0)}
BL, BT, BRACKET_RGB = 25.0, 5.0, (0.95, 0.95, 0.94)   # printed bracket stand-in: leg, plate thickness (assumed), white


def brackets():
    """[(label, [plate boxes (x0, x1, y0, y1, z0, z1)])]: 8 L-brackets, two butted plates each.
    Upright to cross member: in the inner corner on the upright's side that faces the e-box's middle, X IN0..IN1.
    Cross member to long rail: on the cross member's open X IN1 face (the front upright is only 12 mm from the rail)."""
    out = []
    for name, y0 in UPRIGHTS.items():
        yi, s = (y0 + 20, 1) if name == "front" else (y0, -1)          # the upright's inner face, and which way is in
        ys = lambda a, b: (min(yi + s * a, yi + s * b), max(yi + s * a, yi + s * b))
        for k, (z0, z1) in CROSS_Z.items():
            zf, t = (z1, 1) if k == "bottom" else (z0, -1)              # the cross member's face toward the uprights
            zs = lambda a, b: (min(zf + t * a, zf + t * b), max(zf + t * a, zf + t * b))
            out.append((f"Printed bracket 20x25x25 (stand-in), {name} upright to {k} cross member (lite-53)",
                        [(IN0, IN1, *ys(0, BL), *zs(0, BT)), (IN0, IN1, *ys(0, BT), *zs(BT, BL))]))
    for end, yr, s in (("front", Y_F, 1), ("rear", Y_R, -1)):
        ys = lambda a, b: (min(yr + s * a, yr + s * b), max(yr + s * a, yr + s * b))
        for k, (z0, z1) in CROSS_Z.items():
            out.append((f"Printed bracket 20x25x25 (stand-in), {k} cross member to {end} long rail (lite-53)",
                        [(IN1, IN1 + BL, *ys(0, BT), z0, z1), (IN1, IN1 + BT, *ys(BT, BL), z0, z1)]))
    return out   # 20 in from the frame's faces: panels sit as on the printer
SRC_2020 = "2020 (3)"
RAILS = ["2040 (2) (new front)", "2040 (2)001", "4040 (2)", "4040 (1)004"]
MOVE = ["2020 e-box front outer upright", "2040 e-box rear outer upright", "2040 e-box outer side rail",
        "M5x30-Screw e-box joint", "M5-Washer e-box joint"]
MOVE_N = {"2020 e-box front outer upright": 1, "2040 e-box rear outer upright": 1, "2040 e-box outer side rail": 2,
          "M5x30-Screw e-box joint": 8, "M5-Washer e-box joint": 8}


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def normal_along(f, axis):
    u0, u1, v0, v1 = f.ParameterRange
    n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    return abs(abs((n.x, n.y, n.z)[axis]) - 1) < 1e-6


def end_faces(shape, axis, at):
    """The plane faces of `shape` across `axis` lying on `at` (an extrusion's end face: its profile, bores kept)."""
    out = [f.copy() for f in shape.Faces if normal_along(f, axis) and abs(f.CenterOfMass[axis] - at) < 0.05]
    if not out: raise RuntimeError(f"no end face across axis {axis} at {at}")
    return Part.Compound(out)


def extrude(faces, vec):
    sol = [f.extrude(vec) for f in faces.Faces]
    return (sol[0].multiFuse(sol[1:]) if len(sol) > 1 else sol[0]).removeSplitter()


def container(o):
    g = o.getParentGroup() or o.getParentGeoFeatureGroup()
    if g is None:
        g = next((x for x in o.InList if o in getattr(x, "Group", [])), None)
    return g


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n_before = len(pr.leaves)
    old = {o.Name: pr.shapes[o.Name] for o in pr.leaves}
    oldbox = {o.Name: pr.boxes[o.Name] for o in pr.leaves}

    def put(o, s):
        """o (a new Part::Feature, no links to it) gets the GLOBAL shape s."""
        par = o.getGlobalPlacement().multiply(o.Placement.inverse())
        s = s.copy(); s.Placement = par.inverse().multiply(s.Placement)
        o.Shape = s; o.Placement = s.Placement

    def parent_turns(o):
        """o's parents' placement turns (a move by Placement along global X is then a move along X)."""
        par = linkgeo.gplace(o).multiply(o.Placement.inverse())
        return not par.Rotation.isSame(FreeCAD.Rotation(), 1e-9)

    def find(pred, what, n=1):
        c = [o for o in pr.leaves if pred(o)]
        p.check(len(c) == n, f"{what} found {n}x: {len(c)}")
        return c

    # 1. the long rails: their own end face extruded X 125..140, added to the rail's LOCAL shape so that a link to the
    #    rail (which shows its target's local shape at the link's own placement) gets the extension too.
    rails = []
    for label in RAILS:
        c = find(lambda o, l=label: o.Label.startswith(l + " one piece X -520..125 (lite-47)"), label)
        if not c: continue
        o = c[0]; rails.append(o)
        if o.TypeId == "App::Link": continue
        s = pr.shapes[o.Name]
        ends = end_faces(s, 0, E_IN_OLD); area = sum(f.Area for f in ends.Faces)
        piece = extrude(ends, V(DX, 0, 0))
        p.check(abs(piece.Volume - area * DX) < 0.01 * area * DX, f"{label}: extension {piece.Volume:.0f} mm3 = end face {area:.0f} mm2 x {DX:.0f}")
        gp, keep = linkgeo.gplace(o), o.Placement
        loc = o.Shape.copy(); loc.Placement = FreeCAD.Placement()
        pl = piece.copy(); pl.Placement = gp.inverse().multiply(pl.Placement)
        o.Shape = Part.Compound(list(loc.Solids) + list(pl.Solids)); o.Placement = keep
    # 2. the outer members and lite-47's joint fasteners: +DX, by Placement only, links and real parts alike (a link
    #    ignores its target's Placement, so each moves by its own).
    moved = []
    for prefix in MOVE:
        moved += find(lambda o, pf=prefix: o.Label.startswith(pf), prefix, MOVE_N[prefix])
    for o in moved:
        p.check(not parent_turns(o), f"{o.Label[:50]}: parents don't turn")
        if o.TypeId == "App::Link":
            p.check(not getattr(o, "LinkTransform", False), f"{o.Label[:50]}: LinkTransform off")
        o.Placement = FreeCAD.Placement(V(DX, 0, 0), FreeCAD.Rotation()).multiply(o.Placement)
    # 3. the inner frame: copies of a stock 2020 (its group, material and colour), given new shapes
    srco = next(o for o in pr.leaves if o.Label == SRC_2020)
    p.check(srco.TypeId == "Part::Feature", f"{SRC_2020} is a Part::Feature: {srco.TypeId}")
    s20 = pr.shapes[srco.Name]; ob = s20.optimalBoundingBox()
    p.check(ob.ZLength > ob.XLength and ob.ZLength > ob.YLength, f"{SRC_2020} runs along Z: {ob.XLength:.1f} x {ob.YLength:.1f} x {ob.ZLength:.1f}")
    f20 = end_faces(s20, 2, ob.ZMin).translated(V(0, 0, -ob.ZMin))         # plane Z = 0
    fb = f20.optimalBoundingBox()
    p.check(abs(fb.XLength - 20) < 0.3 and abs(fb.YLength - 20) < 0.3, f"2020 profile {fb.XLength:.2f} x {fb.YLength:.2f}")

    def upright(y0, z0, z1):
        f = f20.translated(V(IN0 - fb.XMin, y0 - fb.YMin, z0)); return extrude(f, V(0, 0, z1 - z0))

    def cross(z0):                                    # along Y: the profile turned into plane Y
        f = f20.copy(); f.rotate(V(0, 0, 0), V(1, 0, 0), -90); b = f.optimalBoundingBox()
        f.translate(V(IN0 - b.XMin, Y_F - b.YMin, z0 - b.ZMin)); return extrude(f, V(0, Y_R - Y_F, 0))

    spec = [(f"2020 e-box inner cross member, {k}, Z {z0:.0f}..{z1:.0f} (lite-53)", cross(z0), (IN0, IN1, Y_F, Y_R, z0, z1))
            for k, (z0, z1) in CROSS_Z.items()]
    U0, U1 = CROSS_Z["bottom"][1], CROSS_Z["top"][0]
    for name, y0 in UPRIGHTS.items():
        spec.append((f"2020 e-box inner upright, {name}, Y {y0:.0f}..{y0 + 20:.0f} (lite-53)",
                     upright(y0, U0, U1), (IN0, IN1, y0, y0 + 20, U0, U1)))
    new = []
    for label, s, want in spec:
        c = doc.copyObject(srco, False); container(srco).addObject(c)
        put(c, s); c.Label = label; new.append((c, want))
    # printed 20x25x25 angle brackets, one per joint: stand-ins (two butted plates, legs 25, 20 wide, BT thick
    # assumed). The owner prints a downloaded design whose licence forbids sharing: no file of it goes in the repo
    # or the models, only its outside size.
    for label, b in brackets():
        sh = Part.makeCompound([box(*q) for q in b])
        o = p.add_solids(doc, container(srco), [("", sh)], "Bracket", label, BRACKET_RGB)[0]; put(o, sh)   # global
        bb = FreeCAD.BoundBox()
        for q in b: bb.add(FreeCAD.BoundBox(q[0], q[2], q[4], q[1], q[3], q[5]))
        new.append((o, (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)))
    doc.recompute(); pr.refresh()
    # checks: positions
    for o in rails:
        b = pr.boxes[o.Name]
        p.check(abs(b.XMin - X_L) < 0.3 and abs(b.XMax - E_IN) < 0.3, f"{o.Label}: X {b.XMin:.2f}..{b.XMax:.2f}")
        o.Label = o.Label.replace("X -520..125 (lite-47)", f"X -520..{E_IN:.0f} (lite-53)")
    for o in moved:
        a, b = oldbox[o.Name], pr.boxes[o.Name]
        p.check(abs(b.XMin - a.XMin - DX) < 0.05 and abs(b.XMax - a.XMax - DX) < 0.05 and abs(b.YMin - a.YMin) < 0.05
                and abs(b.ZMin - a.ZMin) < 0.05 and abs(b.ZMax - a.ZMax) < 0.05,
                f"{o.Label[:50]}: X {a.XMin:.1f}..{a.XMax:.1f} -> {b.XMin:.1f}..{b.XMax:.1f}")
    for o, want in new:
        b = pr.boxes[o.Name]; got = (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax)
        p.check(all(abs(g - w) < 0.3 for g, w in zip(got, want)), f"{o.Label}: {' '.join(f'{g:.1f}' for g in got)}")
    # checks: overlaps
    members = rails + moved + [o for o, _ in new]
    names = {o.Name for o in members}
    env = {o.Name for o in pr.leaves if o.Label.startswith("Ebox envelope")}
    cand = [(m, o) for m in members for o in pr.leaves if o.Name != m.Name and o.Name not in env
            and (o.Name not in names or m.Name < o.Name) and pr.boxes[o.Name].intersect(pr.shapes[m.Name].BoundBox)]
    vnew = p.volumes([(pr.shapes[m.Name], pr.shapes[o.Name]) for m, o in cand])
    vold = p.volumes([(old[m.Name], old[o.Name]) if m.Name in old and o.Name in old else (Part.Shape(), Part.Shape())
                      for m, o in cand])
    fresh, kept = [], []
    for (m, o), a, b in zip(cand, vnew, vold):
        b = 0.0 if b == float("inf") and not (m.Name in old and o.Name in old) else b
        pair = (m.Label[:44], o.Label[:36], round(a, 1))
        if b > 1e-2: kept.append(pair); continue
        if a > 1e-2: fresh.append(pair)
    p.log(f"info overlaps lite-52 already has (not a failure): {len(kept)} {kept}")
    p.check(not fresh, f"new overlaps (pairs that didn't overlap in lite-52): {len(fresh)} {fresh[:12]}")
    p.check(len(pr.leaves) == n_before + 4 + len(brackets()), f"solids: {len(pr.leaves)} (lite-52 + 4 members + {len(brackets())} brackets = {n_before + 4 + len(brackets())})")
    p.dump({"e_in": [E_IN_OLD, E_IN], "inner_frame_x": [IN0, IN1], "uprights_y": UPRIGHTS,
            "cross_z": CROSS_Z, "moved": len(moved), "rails": [o.Label for o in rails]})
    return p.finish([(doc, DST)])


litelib.Pass("lite53_ebox_inner_frame").run(main)
