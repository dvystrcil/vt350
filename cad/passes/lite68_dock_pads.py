# GUI pass: vt350-lite-67 -> vt350-lite-68   (headless = dry run, never saves)   vt350#59
# The dock reaches to the cowl, instead of a spacer on the cowl reaching to the dock (owner, 2026-11-18: "Have we
# considered the opposite approach? that we extend the dock to the cowl?"). lite-67's spacer couldn't be held on: the
# dock screws' heads stand proud as the docking hooks, so they clamp nothing, and a nut against the dock has no
# consistent height or bearing face and takes away the play the dock needs. On the dock, the extension is free: it
# doesn't ride on the head, and its shape costs nothing.
#
# Per side (the Left head at the Left Dock, the Right head at the Right Dock, mirror image):
#  1. The spacers go (two targets, three links). The cowl stays lite-67's: it prints flat as DW-Tas's duct.
#  2. Cowl, each dock screw: a spot-face square to the screw (r SPOT_R, just below the 10 deg print face), so the
#     screw's sleeve seats flat, and a short M3 insert (3 x 5) from it, >= FLOOR mm of cowl beyond and WALL round.
#     The rear-bottom screw moves MOVE_RB (18.5 forward, 6.25 up: the middle of the spot both cowls allow): where it was, the cowl takes only a 2 mm pocket.
#  3. Dock: the rear-bottom keyslot (channel + through-hole) moves by MOVE_RB too: the old one is filled, and the
#     plate grows a wing there (its spine ends short of the new place), as its top wing.
#     Each keyslot (the keyslot plate, MadMax "Dock Asembly", GPL-3.0): a pad on the plate's inner face. Its
#     footprint is the keyslot's head channel (the 2 mm recess the screw head slides in) grown by PAD_WALL; it fills
#     the old channel, and at its own face it carries the same channel, so the screw head sees the keyslot it always
#     did, just nearer the cowl. The plate's through-hole at the parked screw runs on through the pad. Each pad's face
#     is square to the screw (as the plate's was), so the gap doesn't change as the head slides along the keyslot, and
#     it reaches as far as it can while keeping >= CLEAR from every part of the head at every pose of the 6 mm pickup
#     slide (the play the dock needs, owner 2026-11-18), then is cut back so its sleeve is a whole mm. The Left head's
#     Crossbow lever stands 1.75 mm off the plate at the rear-top keyslot, so that pad stays short and its sleeve long.
#  4. The head's screw: through a sleeve (bought, exact length) into the insert; the head clamps the sleeve, so the
#     hook height is the sleeve's, not how far the screw is turned. Sleeve lengths are logged (spot-face to pad face).
# Checks (refuses to save on any):
#  - two remixed ducts, three screw axes, the print face; the spacers found and gone (-5 solids); one valid solid each;
#  - each pocket in material, >= FLOOR beyond it at every sample point; each spot-face below the print face;
#  - each pad: the channel and through-hole found, CLEAR kept at every slide pose, the channel the plate's outline;
#  - no new overlap (any cowl copy or keyslot plate against any other part, against lite-67's);
#  - every other solid's box unchanged; AC7 against lite-66 (before the spacer).
import FreeCAD, Part, math, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo, matlib
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-67.FCStd", f"{MODELS}/vt350-lite-68.FCStd"
CARDS = os.path.join(_REPO, "cad/materials")
DUCTS = {"Left": "[a]_Duct-4010-left MadMax dock bosses (remix, CC BY-NC-SA 4.0)",
         "Right": "[a]_Duct-4010-right MadMax dock bosses (remix, CC BY-NC-SA 4.0)"}
HEADS = {"Left": "Left Toolhead", "Right": "Right Toolhead"}
DOCKS = {"Left": "Left Dock", "Right": "Right Dock"}
PLATES = {"Left": ("Plate", "Plate Back"), "Right": ("Plate(Mirror)", "Plate Back(Mirror)")}
TUBES = ("Bowden Left", "Bowden Right")
SPACER = "[a]_Dock spacer "
KEYS = "Dock Asembly"                    # the keyslot plate (MadMax's spelling)
KEYS_LABEL = "Dock Asembly, standoff pads {side} (MadMax remix, GPL-3.0)"
POCKET = (2.4, 3.4)                      # short M3 insert, 3 long x 5 OD (owner 2026-11-18): pocket r, depth from the spot-face
MOVE_RB = V(0, -18.5, 6.25)              # the rear-bottom screw and keyslot move here (global): the cowl is 11 mm deep
                                         # there, 2 mm where it was (owner 2026-11-18)
WALL = 1.0                               # cowl round each pocket
LEAD = 0.6
FLOOR = 1.0
SPOT_R = 2.75                            # spot-face radius: a dia 5 sleeve + 0.25
SPOT_EXTRA = 0.2                         # below the print face's lowest point round the spot-face
CHANNEL = 2.0                            # the keyslot plate's head channel depth (its inner face to its step)
PAD_WALL = 2.5
CLEAR = 1.0                              # mm from the pad to any head part, over the whole slide
WING = 1.0                               # the moved keyslot's wing: its pad footprint + this, through the plate
SLEEVE_STEP = 1.0                        # sleeves come in whole mm: each pad is cut back so its sleeve is one
SLIDE = 6.0                              # pickup: the parked head goes 6.0 mm forward (-Y) along the keyslots (lite-23)
POSES = [-SLIDE * k / 12 for k in range(13)]
COM_LIMIT = 0.5                          # mm, AC7 (owner accepted 2026-11-18)
DEFAULT_RHO = 1.27e-3
COM66 = os.path.join(os.environ.get("VT350_WORK", os.path.join(_REPO, "cad/data")), "logs", "lite67_dock_spacer.json")


def to_local(shape, pl):
    """A container-frame shape -> the same shape stored under placement pl (copy=True: LESSONS.md)."""
    s = shape.copy(); s.transformShape(pl.inverse().toMatrix(), True, False); s.Placement = pl
    return s


def container(o):
    """The placement of o's container: global = container * o.Placement."""
    return linkgeo.gplace(o).multiply(o.Placement.inverse())


def rho(o):
    sm = getattr(linkgeo.link_target(o), "ShapeMaterial", None)
    if sm is None or sm.Name == "Default": return DEFAULT_RHO
    return float(sm.PhysicalProperties["Density"].split()[0]) * 1000


def group_paths(doc):
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, "Group", None) or []): par.setdefault(k.Name, o)
    def path(o):
        r, q = [], par.get(o.Name)
        while q is not None: r.append(q.Label); q = par.get(q.Name)
        return r
    return {o.Name: path(o) for o in doc.Objects}


def head_com_x(pr, side):
    """(mass g, CoM X) of a carried tool, as toolhead_com.py's AC2 line (lite67_dock_spacer.py)."""
    G = group_paths(pr.doc); dock, plates = DOCKS[side], PLATES[side]
    m = mx = 0.0
    for o in pr.leaves:
        g = G.get(o.Name, [])
        if getattr(o, "StandInFor", ""): continue
        mine = (HEADS[side] in g and o.Label not in TUBES) or (dock in g and (o.Label in plates or any(
            o.Label.startswith(f"MadMax magnet 6x3 N52 (plate {l}) ") for l in plates)))
        if not mine: continue
        for s in pr.shapes[o.Name].Solids:
            w = s.Volume * rho(o); m += w; mx += w * s.CenterOfMass.x
    return m, mx / m


def cowl(p, side, t):
    """(new duct in t's container frame, {name: (global axis point on the print face, global into-duct dir, spot
    bottom offset)}, info)."""
    S = t.Shape.copy()
    F = max((f for f in S.Faces if f.Surface.__class__.__name__ == "Plane"), key=lambda f: f.Area)
    u0, u1, v0, v1 = F.ParameterRange
    n = F.normalAt((u0 + u1) / 2, (v0 + v1) / 2); c = F.CenterOfMass
    ang = math.degrees(math.acos(abs(n.x)))
    p.check(F.Area > 1000 and 5 < ang < 15, f"{side}: print face {F.Area:.0f} mm2, {ang:.2f} deg off the screw axes")
    d = V(1 if n.x < 0 else -1, 0, 0)                         # along a screw, into the duct
    tops = sorted({(round(f.Surface.Center.y, 3), round(f.Surface.Center.z, 3)) for f in S.Faces
                   if f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - POCKET[0]) < 1e-6
                   and abs(abs(f.Surface.Axis.x) - 1) < 1e-6})
    p.check(len(tops) == 2 and abs(math.dist(*tops) - 20.0) < 0.05, f"{side}: lite-67's two top pockets ({tops})")
    if p.errs: return None
    # the rear-bottom screw: same Y as the rear-top (the shorter of the two top wedges), 54 mm down (lite-23 SCREWS)
    def hit(a):
        p0 = V(0, *a); return p0 + d * ((c - p0).dot(n) / d.dot(n))
    # rear-top: the top axis whose print-face hit is nearer the dock (lite-67's shorter wedge)
    rear = max(tops, key=lambda a: hit(a).dot(-d))
    front = [a for a in tops if a != rear][0]
    # rear-bottom: lite-67's stub there (a cylinder face r 4.0) is coaxial with neither top axis
    stubs = sorted({(round(f.Surface.Center.y, 3), round(f.Surface.Center.z, 3)) for f in S.Faces
                    if f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - 4.0) < 1e-6
                    and abs(abs(f.Surface.Axis.x) - 1) < 1e-6})
    rb = [a for a in stubs if all(abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1 for b in tops)]
    p.check(len(rb) == 1, f"{side}: the rear-bottom stub's axis ({stubs})")
    if p.errs: return None
    p.check(abs(math.dist(rear, rb[0]) - 54.0) < 0.05 and abs(math.dist(rear, front) - 20.0) < 0.05,
            f"{side}: lite-23's screw square, 20 x 54 ({math.dist(rear, front):.3f} x {math.dist(rear, rb[0]):.3f})")
    C = container(t)
    mv = C.Rotation.inverted().multVec(MOVE_RB)
    p.check(abs(mv.x) < 1e-6, f"{side}: the move is across the screw axes ({mv})")
    nb = (round(rb[0][0] + mv.y, 6), round(rb[0][1] + mv.z, 6))
    axes = {"front-top": front, "rear-top": rear, "rear-bottom": nb}
    duct = S
    tanv = math.tan(math.radians(ang))
    spot_off = SPOT_R * tanv + SPOT_EXTRA                      # spot bottom, past the print-face hit, along d
    cuts, info = [], {}
    for nm, a in axes.items():
        h = hit(a); sb = h + d * spot_off
        cuts.append(Part.makeCylinder(SPOT_R, 10.0, sb, -d))
        dep = POCKET[1]
        pk = Part.makeCylinder(POCKET[0], dep + 0.01, sb - d * 0.01, d); cuts.append(pk)
        bot = sb + d * (dep + FLOOR)
        ring = [bot + (V(0, 1, 0) * math.cos(k * math.pi / 6) + V(0, 0, 1) * math.sin(k * math.pi / 6)) * r
                for k in range(12) for r in (0.0, 1.2, POCKET[0])]
        ok = sum(S.isInside(q, 1e-6, True) for q in ring)
        def avail(dd):
            bb = sb + d * (dd + FLOOR)
            return all(S.isInside(bb + (V(0, 1, 0) * math.cos(k * math.pi / 6) + V(0, 0, 1) * math.sin(k * math.pi / 6)) * r, 1e-6, True)
                       for k in range(12) for r in (0.0, 1.2, POCKET[0]))
        best = max([x / 10 for x in range(10, 80) if avail(x / 10)] or [0.0])
        p.log(f"{side} {nm}: deepest pocket from the spot-face with {FLOOR} mm floor all round: {best:.1f} mm (contiguous? {all(avail(x / 10) for x in range(10, int(best * 10) + 1))})")
        p.check(ok == len(ring), f"{side} {nm}: >= {FLOOR} mm of cowl beyond the {dep} mm pocket at {ok}/{len(ring)} points")
        wl = [sb + d * (dep * f) + (V(0, 1, 0) * math.cos(k * math.pi / 6) + V(0, 0, 1) * math.sin(k * math.pi / 6)) * (POCKET[0] + WALL)
              for k in range(12) for f in (0.25, 0.5, 0.9)]
        okw = sum(S.isInside(q, 1e-6, True) for q in wl)
        p.check(okw == len(wl), f"{side} {nm}: {WALL} mm of cowl round the pocket at {okw}/{len(wl)} points")
        # spot-face: its rim all below the print face (so the sleeve seats on the flat, not on the slope)
        rim = [sb + (V(0, 1, 0) * math.cos(k * math.pi / 18) + V(0, 0, 1) * math.sin(k * math.pi / 18)) * SPOT_R
               for k in range(36)]
        below = min((q - c).dot(-n) for q in rim)
        p.check(below > 0.05, f"{side} {nm}: spot-face rim {below:.2f} mm below the print face")
        sleeve_floor = (sum(S.isInside(sb + d * 0.3 + (V(0, 1, 0) * math.cos(k * math.pi / 6) + V(0, 0, 1) * math.sin(k * math.pi / 6)) * r, 1e-6, True)
                            for k in range(12) for r in (POCKET[0] + 0.15,)))
        p.check(sleeve_floor == 12, f"{side} {nm}: the sleeve seats on cowl all round the insert ({sleeve_floor}/12)")
        info[nm] = dict(axis=a, pocket_mm=dep, spot_mm=round(spot_off, 3))
    duct = S.cut(cuts).removeSplitter()
    p.check(duct.isValid() and len(duct.Solids) == 1, f"{side} cowl: one valid solid ({len(duct.Solids)}, valid {duct.isValid()})")
    g = {nm: (C.multVec(hit(a) + d * spot_off), C.Rotation.multVec(d)) for nm, a in axes.items()}
    info["print_face_deg"] = round(ang, 2)
    return duct, g, info


def pads(p, side, K, head_shapes, screws):
    """(new keyslot plate, global; info). screws: {name: (global spot bottom, global into-duct dir)}."""
    S = linkgeo.gshape(K)
    toward = screws["rear-top"][1]                               # from the dock toward the head: the screw's way into the cowl
    toward = V(round(toward.x), 0, 0)
    x_in = S.BoundBox.XMax if toward.x > 0 else S.BoundBox.XMin   # the plate's inner face
    out, info = [], {}
    body = S
    thick = S.BoundBox.XLength
    for nm, (sb, d) in screws.items():
        y, z = sb.y, sb.z
        mv = MOVE_RB if nm == "rear-bottom" else V(0, 0, 0)
        sy, sz = y - mv.y, z - mv.z                                 # where the plate's keyslot is now
        def wire_at(depth):
            ws = [w for w in S.slice(V(1, 0, 0), x_in - toward.x * depth)
                  if w.BoundBox.YMin < sy < w.BoundBox.YMax and w.BoundBox.ZMin < sz < w.BoundBox.ZMax]
            ws = [w for w in ws if w.BoundBox.YLength < 25 and w.BoundBox.ZLength < 25]   # not the plate's outline
            return min(ws, key=lambda w: w.BoundBox.YLength * w.BoundBox.ZLength) if len(ws) == 1 else None
        ch, hole = wire_at(CHANNEL / 2), wire_at(CHANNEL + 1.5)
        p.check(ch is not None and hole is not None, f"{side} {nm}: the keyslot's channel and through-hole at the screw")
        if ch is None or hole is None: return None
        chf, hof = Part.Face(ch), Part.Face(hole)
        if mv.Length > 0:
            # fill the old keyslot through the plate; the plate's spine ends short of the new place, so it grows a
            # wing there (the keyslot's footprint + WING, through the plate), like its top wing
            fo = chf.makeOffset2D(0.3, 0, False, False, False).toNurbs()
            fo.translate(V(x_in - toward.x * thick - fo.BoundBox.Center.x, 0, 0))
            body = body.fuse(fo.extrude(toward * thick))
            wg = chf.makeOffset2D(PAD_WALL + WING, 0, False, False, False).toNurbs(); wg.translate(mv)
            wg.translate(V(x_in - toward.x * thick - wg.BoundBox.Center.x, 0, 0))
            body = body.fuse(wg.extrude(toward * thick))
            chf.translate(mv); hof.translate(mv)
        p.check(abs(chf.Area - hof.Area) > 1 and chf.Area > hof.Area, f"{side} {nm}: channel {chf.Area:.1f} mm2 > through-hole {hof.Area:.1f}")
        foot = chf.makeOffset2D(PAD_WALL, 0, False, False, False).toNurbs()   # offset curves go invalid when
                                                                              # transformed (LESSONS.md)
        def pad(L):
            f0 = foot.copy(); f0.translate(V(x_in - toward.x * CHANNEL - f0.BoundBox.Center.x, 0, 0))
            return f0.extrude(toward * (L + CHANNEL))
        def clearance(L):
            pd = pad(L)
            bb = FreeCAD.BoundBox(pd.BoundBox); bb.enlarge(SLIDE + 3)
            near = [h for h in head_shapes if h.BoundBox.intersect(bb)]
            if not near: return 99.0
            comp = Part.makeCompound(near); best = 99.0
            for dy in POSES:
                q = pd.copy(); q.translate(V(0, -dy, 0))             # the head moves dy; the pad, relative to it, -dy
                best = min(best, q.distToShape(comp)[0])
            return best
        lo, hi = 0.0, 20.0
        p.check(clearance(lo) >= CLEAR, f"{side} {nm}: the plate itself keeps {CLEAR} mm ({clearance(lo):.2f})")
        for _ in range(14):
            mid = (lo + hi) / 2
            if clearance(mid) >= CLEAR: lo = mid
            else: hi = mid
        L = math.floor(lo * 20) / 20                                 # 0.05 mm steps, rounded down
        s_max = (V(x_in + toward.x * L, y, z) - sb).Length            # the sleeve if the pad went that far
        s_len = math.ceil(s_max / SLEEVE_STEP - 1e-6) * SLEEVE_STEP
        L = round(L - (s_len - s_max), 4)
        p.check(L >= 0, f"{side} {nm}: room for a pad ({L:.2f} mm) with a {s_len:.1f} mm sleeve")
        cl = clearance(L)
        p.check(L < 19.0, f"{side} {nm}: the pad is stopped by the head, not by the search's 20 mm limit ({L:.2f})")
        p.check(cl >= CLEAR, f"{side} {nm}: pad {L:.2f} mm keeps {cl:.2f} mm from the head over the slide (>= {CLEAR})")
        face_x = x_in + toward.x * L
        chn = chf.copy(); chn.translate(V(face_x - chn.BoundBox.Center.x, 0, 0)); chn = chn.extrude(-toward * CHANNEL)
        thr = hof.copy(); thr.translate(V(x_in - toward.x * 10 - thr.BoundBox.Center.x, 0, 0)); thr = thr.extrude(toward * (10 + L - CHANNEL + 0.01))
        body = body.fuse(pad(L)).cut([chn, thr])
        sleeve = (V(face_x, y, z) - sb).Length
        info[nm] = dict(moved=tuple(round(x, 2) for x in mv), pad_mm=L, clearance_mm=round(cl, 3), sleeve_mm=round(sleeve, 2), face_x=round(face_x, 3))
    body = body.removeSplitter()
    p.check(body.isValid() and len(body.Solids) == 1, f"{side} keyslot plate: one valid solid ({len(body.Solids)}, valid {body.isValid()})")
    big = max((f for f in body.Faces if f.Surface.__class__.__name__ == "Plane"), key=lambda f: f.Area)
    p.check(abs(big.normalAt(0, 0).x) > 0.999 and abs(big.CenterOfMass.x - (x_in - toward.x * 6.0)) < 0.05,
            f"{side} keyslot plate: still prints on its outer face (x {big.CenterOfMass.x:.2f}, {big.Area:.0f} mm2)")
    return body, info


def main(p):
    matlib.use_dir(CARDS)
    pr = p.open(SRC); doc = pr.doc
    G = group_paths(doc)
    targets, keys = {}, {}
    for side, lab in DUCTS.items():
        c = [o for o in doc.getObjectsByLabel(lab) if o.TypeId == "Part::Feature"]
        p.check(len(c) == 1, f"{side}: one duct {lab!r} ({len(c)})")
        if c: targets[side] = c[0]
        k = [o for o in pr.leaves if o.Label.startswith(KEYS) and DOCKS[side] in G.get(o.Name, [])]
        p.check(len(k) == 1 and k[0].TypeId == "Part::Feature", f"{side}: one keyslot plate in {DOCKS[side]} ({[o.Label for o in k]})")
        if k: keys[side] = k[0]
    # the slot docks: their keyslot plates are copies of the Left one (Part::Features) or links to the Right one;
    # each must take the remixed plate, and sit to its head's cowl as the Left / Right plate does to its own
    slot_keys = {side: [o for o in pr.leaves if linkgeo.link_target(o).Label.startswith(KEYS) and o.Name != keys[side].Name
                        and any(g.startswith("Dock slot") for g in G.get(o.Name, []))
                        and (linkgeo.link_target(o).Name == keys[side].Name or (o.TypeId == "Part::Feature" and side == "Left"))]
                 for side in keys}
    p.log("slot dock plates:", {s: [(o.Label, o.TypeId) for o in v] for s, v in slot_keys.items()})
    p.check(sum(len(v) for v in slot_keys.values()) == 3, f"three slot dock plates ({sum(len(v) for v in slot_keys.values())})")
    spacers = [o for o in doc.Objects if o.Label.startswith(SPACER)]
    p.check(len(spacers) == 5, f"lite-67's five spacers ({len(spacers)})")
    if p.errs: return p.finish([])
    copies = {s: [o for o in pr.leaves if linkgeo.link_target(o).Name == t.Name] for s, t in targets.items()}
    mine0 = {o.Name for v in copies.values() for o in v} | {k.Name for k in keys.values()} | {
        o.Name for v in slot_keys.values() for o in v}
    # each slot plate's cowl: the duct copy nearest it; the plate-to-cowl placement must equal the side's own
    def rel(plate, duct): return linkgeo.gplace(duct).inverse().multiply(linkgeo.gplace(plate))   # the plate in the cowl's frame
    pair = {}
    for side, v in slot_keys.items():
        own = min(copies[side], key=lambda d: pr.shapes[d.Name].distToShape(pr.shapes[keys[side].Name])[0])
        p.check(own.Name == targets[side].Name, f"{side}: its own plate faces its own cowl ({own.Label})")
        r0 = rel(keys[side], targets[side])
        for k in v:
            d = min(copies[side], key=lambda d: pr.shapes[d.Name].distToShape(pr.shapes[k.Name])[0])
            ok = rel(k, d).isSame(r0, 1e-6)
            p.check(ok, f"{side} {k.Label} ({G.get(k.Name, ['?'])[1] if len(G.get(k.Name, [])) > 1 else '?'}): sits to its cowl {d.Label} as {keys[side].Label} does")
            pair[k.Name] = side
    sp0 = {o.Name for o in spacers}
    pairs0 = [(a.Name, b.Name) for a in pr.leaves if a.Name in mine0 for b in pr.leaves
              if b.Name not in mine0 | sp0 and pr.shapes[a.Name].BoundBox.intersect(pr.shapes[b.Name].BoundBox)]
    base = {}
    for (a, b), v in zip(pairs0, p.volumes([(pr.shapes[a], pr.shapes[b]) for a, b in pairs0])):
        if v > 1e-3: base[(a, b)] = v
    p.log("lite-67 overlaps of the cowl copies and keyslot plates:", {(doc.getObject(a).Label, doc.getObject(b).Label): round(v, 2) for (a, b), v in base.items()})
    box0 = {n: s.BoundBox for n, s in pr.shapes.items()}
    n0 = len(pr.leaves)
    # the cowls
    made, screws = {}, {}
    for side, t in targets.items():
        r = cowl(p, side, t)
        if r is None: return p.finish([])
        made[side] = r; screws[side] = r[1]
        p.log(f"{side} cowl: {r[2]}")
    if p.errs: return p.finish([])
    gui = FreeCAD.GuiUp
    for o in [o for o in spacers if o.TypeId == "App::Link"] + [o for o in spacers if o.TypeId != "App::Link"]:
        doc.removeObject(o.Name)
    for side, t in targets.items():
        pl = FreeCAD.Placement(t.Placement)
        ap = list(t.ViewObject.ShapeAppearance) if gui and hasattr(t.ViewObject, "ShapeAppearance") else None
        t.Shape = to_local(made[side][0], pl)
        if ap is not None: t.ViewObject.ShapeAppearance = ap
        p.check(t.Placement.isSame(pl, 1e-9), f"{side}: the cowl keeps its placement")
    doc.recompute(); pr.refresh()
    # the pads, against the head parked at each dock (after the cowl change)
    G = group_paths(doc)
    info = {}
    for side, K in keys.items():
        hs = [pr.shapes[o.Name] for o in pr.leaves if HEADS[side] in G.get(o.Name, []) and o.Label not in TUBES]
        r = pads(p, side, K, hs, screws[side])
        if r is None: return p.finish([])
        body, inf = r; info[side] = inf
        p.log(f"{side} pads: {inf}")
        pl = FreeCAD.Placement(K.Placement)
        ap = list(K.ViewObject.ShapeAppearance) if gui and hasattr(K.ViewObject, "ShapeAppearance") else None
        cpl = container(K)
        loc = body.copy(); loc.transformShape(cpl.inverse().toMatrix(), True, False)
        K.Shape = to_local(loc, pl)
        if ap is not None: K.ViewObject.ShapeAppearance = ap
        K.Label = KEYS_LABEL.format(side=side.lower())
        p.check(K.Placement.isSame(pl, 1e-9), f"{side}: the keyslot plate keeps its placement")
    if p.errs: return p.finish([])
    for v in slot_keys.values():
        for k in v:
            if k.TypeId != "Part::Feature": continue                 # links follow their target
            src = keys[pair[k.Name]]
            p.check(k.Placement.isSame(src.Placement, 1e-9), f"{k.Label}: the same placement as {src.Label}")
            ap = list(k.ViewObject.ShapeAppearance) if gui and hasattr(k.ViewObject, "ShapeAppearance") else None
            k.Shape = src.Shape.copy()
            if ap is not None: k.ViewObject.ShapeAppearance = ap
            k.Label = src.Label.replace(" (MadMax", f" {G.get(k.Name, ['', '?'])[1]} (MadMax") if len(G.get(k.Name, [])) > 1 else k.Label
    doc.recompute(); pr.refresh()
    for side, K in keys.items():
        b = pr.shapes[K.Name].BoundBox
        p.check(K.Shape.isValid(), f"{side} keyslot plate valid after the save path; box X {b.XMin:.2f}..{b.XMax:.2f}")
    for v in slot_keys.values():
        for k in v:
            src = keys[pair[k.Name]]
            a, b = pr.shapes[k.Name], pr.shapes[src.Name]
            p.check(k.Shape.isValid() or k.TypeId == "App::Link", f"{k.Label}: valid")
            p.check(abs(a.Volume - b.Volume) < 1e-3, f"{k.Label}: the remixed plate ({a.Volume:.1f} vs {b.Volume:.1f} mm3)")
    p.check(len(pr.leaves) == n0 - 5, f"solids {n0} -> {len(pr.leaves)} (the five spacers gone)")
    mine = mine0
    pairs = [(a.Name, b.Name) for a in pr.leaves if a.Name in mine for b in pr.leaves
             if b.Name not in mine and pr.shapes[a.Name].BoundBox.intersect(pr.shapes[b.Name].BoundBox)]
    vols = dict(zip(pairs, p.volumes([(pr.shapes[a], pr.shapes[b]) for a, b in pairs])))
    worse = sorted(((v, doc.getObject(a).Label, doc.getObject(b).Label) for (a, b), v in vols.items()
                    if v > base.get((a, b), 0.0) + 0.01), reverse=True)
    p.check(not worse, f"no new overlap of a cowl copy or keyslot plate ({len(worse)}: {[(round(v, 2), a, b) for v, a, b in worse[:4]]})")
    moved = [doc.getObject(k).Label for k, b in box0.items() if k not in mine0 and k not in sp0
             and (k not in pr.shapes or not pr.shapes[k].BoundBox.isInside(b) or not b.isInside(pr.shapes[k].BoundBox))]
    p.check(not moved, f"every other solid's box unchanged ({len(moved)}: {moved[:5]})")
    import json
    c66 = json.load(open(COM66))["com"]                          # lite-66 (before the spacer): lite-67's baseline
    com = {}
    for s in HEADS:
        m1, x1 = head_com_x(pr, s); m0, x0 = c66[s]["mass_g"][0], c66[s]["com_x"][0]
        com[s] = {"mass_g": (m0, round(m1, 2)), "com_x": (x0, round(x1, 3)), "shift_mm": round(x1 - x0, 3)}
        p.check(abs(x1 - x0) <= COM_LIMIT, f"AC7 {HEADS[s]}: against lite-66, mass {m0:.1f} -> {m1:.1f} g, CoM X "
                                           f"{x0:.3f} -> {x1:.3f} ({x1 - x0:+.3f} mm, limit {COM_LIMIT})")
    p.dump({"cowl": {s: made[s][2] for s in made}, "pads": info, "com": com})
    return p.finish([(doc, DST)])


litelib.Pass("lite68_dock_pads").run(main)
