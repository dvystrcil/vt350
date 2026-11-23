# GUI pass: vt350-lite-77 -> vt350-lite-78   (headless = dry run, never saves)   vt350#291
# The front of the machine 17 mm forward, and one-piece 490 mm Y rails (owner, 2026-11-22).
#  - Why: the Beacon moves to y_offset 15 (its body clears both hot ends down to 15, cad/studies/beacon_offset.py), and
#    the coil then reaches the mesh front only if the docked heads stop the nozzle >= 14.6 mm further forward. The
#    carriage's front stop is the gantry joint on the Y rails' front mounts, so the mounts, docks and front frame move
#    together: 17 mm (2.4 mm of margin). The owner sources rails in 20 mm steps (Motion Constrained, Hiwin MGN9HZ0C):
#    the rails butt against the Monolith mounts (473.93 today, lite-9), so 490.93 takes a 490 with 0.46 at each end.
#  - "The plate has to follow the backbone" (owner): the backbone, bed, plate and all of Z stay. So do the front Z posts
#    (they carry the front Z rails), the old bottom front 2040 (the backbone bolts to it) and the EMU on the roof.
#  - FRONT set, moved -17 in Y: every leaf whose box ends in front of Y -5, and every leaf of a head or dock group.
#  - SPLICED +17 (lite6.py's splice: the front part moves, the gap is filled with the part's own cross-section, so end
#    taps and holes survive): every other leaf that reaches in front of Y -5 (side bars, e-box rails, panels, felt,
#    LED channels, base board, the e-box envelope). Belts: a copy of their own 18 mm stretch (GT2 pitch 2), 1 mm overlap.
#  - Y rails: the 400 + 73.9 front extension (lite-9) replaced by a 490 built from the 400's own section, holes on
#    Hiwin's pattern (pitch 20, 5 mm from each end) when the 400 has holes; lite-77's is a plain bar, so the 490 is too.
#  - The five Bowden tubes and five O2S cables run from each docked head back along Y to the roof-exit clamps, which
#    stay: each is spliced like the frame, at the Y in 100..300 where its section is most nearly a circle of its own
#    diameter (the run is straight along Y there), so the head end moves -17 with its head and the run is 17 longer.
#  - The Mellow MultiHead Zero leaves the bed (owner, 2026-11-22): lite-61's bracket and Zero are removed. The Zero
#    parks on the backbone (steel) on a printed carrier with 4 magnets, centred in X on the strip in front of the bed
#    (the bed comes down to ~20 mm over the backbone everywhere behind Y 28). It goes on the plate centre only to
#    calibrate, by hand (tc_offsets.cfg MELLOW_CALIBRATE_START/RUN): not modelled there, or every sweep would see it.
# Checks (refuses to save on any): every leaf moved exactly -17, unchanged, spliced, removed (rails, lite-61's probe)
# or new (rails, carrier); spliced parts valid with their solid count, their front end -17 and their volume +
# section x 17; tubes and cables cut where the section's perimeter is within 1 % of pi x d; rails 490 long, 0.46 mm
# from each mount, valid; the carrier one valid chamfered solid on the backbone's top, the Zero on the carrier, all
# clear of the bed at its lowest (>= 3 mm); no leaf left with an attachment that would undo the move on recompute;
# COLLISIONS vs lite-77: every moved, spliced or new part against the rest, no overlap that lite-77 didn't have.
import FreeCAD, Part, os, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "platform/render")]
import litelib, linkgeo, printchamfer, colours
from litelib import MODELS, BED_LOWEST_DZ, BED_Z
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-77.FCStd", f"{MODELS}/vt350-lite-78.FCStd"
DY = 17.0
FRONT_Y = -5.0
FRONT_GROUPS = ("Toolhead", "Dock")
STAY = ("2040 Z post (R)", "2040(Mirror) Z post (L)", "backbone-350", "EMU envelope")
STAY_EXACT = ("2040 (2)",)                             # the old bottom front 2040: the backbone's front holes bolt to it
RAILS_OLD = ("MGN9-400mm Y rail (", "MGN9 Y rail front extension (")
RAIL_400 = {"R": "MGN9-400mm Y rail (R)", "L": "MGN9-400mm Y rail (L)"}
RAIL_L, RAIL_PITCH, RAIL_END = 490.0, 20.0, 5.0
FRONT_MOUNT, REAR_MOUNT = "VT9-FI", "VT9-R"            # the Monolith front idler and rear motor mounts (label prefixes)
BELTS = ("GT2 9mm belt, lower", "GT2 9mm belt, upper")
BELT_COPY = 18.0                                       # a whole number of 2 mm GT2 teeth; placed with 1 mm overlap
SPLICE_Y = tuple(float(y) for y in range(30, 400, 5))  # first clean section wins
BELT_Y = tuple(float(y) for y in range(100, 170))
TUBES = ("Bowden ",)
CABLES = ("O2S USB cable slot ",)
TUBE_D, CABLE_D = 4.12, 5.1                            # lite-36 / lite-40: the PTFE tube and the O2S cable
TUBE_Y = tuple(float(y) for y in range(100, 301))      # where to look for each one's splice (the free run along Y)
RUN_GROUP = "O2S cables + channel"                     # lite-40: the zip ties along each tube + cable run
OLD_PROBE = "Nozzle offset probe (lite-61"             # lite-61's group: bracket + Zero, removed
TOL = 1e-3
# the parked Zero (model coordinates): the backbone's front strip, centred on the plate in X
X0 = -245.0
BODY_X, BODY_Y, BODY_H, PROBE_H = 20.0, 17.2, 22.0, 23.0    # lite-61 (Mellow's drawing; the probe estimated)
BUSH_D, BUSH_H, PIN_D, BALL_D = 13.0, 10.0, 5.0, 10.0
SW_Y = 6.0                                                  # the switch + plug stand out of the body's front
BASE_T, BACK_T, BASE_MARGIN = 4.0, 4.0, 1.0
MAG_D, MAG_H, MAG_CLR = 10.0, 3.0, 0.1                      # 4 x D10 x 3 N52 discs, flush with the base's underside
BED_CLEAR = 3.0
CHAMFER = printchamfer.profile(os.path.join(_REPO, "cad/data/print-profile.json"))
LIC = "(printed ABS, vt350, GPL-3.0-or-later)"


def section_at(s, ys):
    """Planar cut faces of s at Y = ys (lite6.py)."""
    bb = s.BoundBox; big = 5000
    back = s.common(Part.makeBox(big, bb.YMax - ys + 1, big, V(-big / 2, ys, -big / 2)))
    fs = [f for f in back.Faces if isinstance(f.Surface, Part.Plane) and abs(abs(f.normalAt(0, 0).y) - 1) < 1e-6
          and abs(f.CenterOfMass.y - ys) < 1e-6]
    return back, fs


def splice(s, ys_candidates, dy, probe=7.0):
    """Cut s at Y = ys, move the Y < ys part by -dy, fill with the cut section extruded by dy (lite6.py). A section is
    clean when its area equals the one `probe` further on: no hole crosses it."""
    bb = s.BoundBox; big = 5000
    for ys in ys_candidates:
        if not (bb.YMin + probe + 1 < ys < bb.YMax - probe - 1): continue
        back, fs = section_at(s, ys)
        _, fs2 = section_at(s, ys + probe)
        a1, a2 = sum(f.Area for f in fs), sum(f.Area for f in fs2)
        if not fs or abs(a1 - a2) > 1e-3: continue
        front = s.common(Part.makeBox(big, ys - bb.YMin + 1, big, V(-big / 2, bb.YMin - 1, -big / 2)))
        front.translate(V(0, -dy, 0))
        new = back.fuse([front] + [f.extrude(V(0, -dy, 0)) for f in fs]).removeSplitter()
        return new, ys, a1
    return None, None, None


def splice_multi(s, ys_candidates, dy):
    """A part made of several solids (a door frame's bars, a gasket's strips): the first ys clean for every solid that
    crosses it; those are spliced one by one, the ones in front of it move -dy, the ones behind stay."""
    if len(s.Solids) == 1: return splice(s, ys_candidates, dy)
    for ys in ys_candidates:
        out, area, ok = [], 0.0, True
        for so in s.Solids:
            b = so.BoundBox
            if b.YMax <= ys: m = so.copy(); m.translate(V(0, -dy, 0)); out.append(m); continue
            if b.YMin >= ys: out.append(so); continue
            new, y1, a = splice(so, (ys,), dy)
            if new is None: ok = False; break
            out += new.Solids; area += a
        if ok: return Part.makeCompound(out), ys, area
    return None, None, None


def splice_belt(s, ys_candidates, dy, copy):
    """Belts (a compound of strand solids): per solid crossing the cuts, the Y < ys part moves -dy and a copy of the
    solid's own ys..ys+copy stretch fills the gap, placed to end at ys (copy > dy: it overlaps the moved part by
    copy - dy). Solids entirely in front of the cuts move; behind them stay."""
    big = 5000; out, cuts = [], []
    lo, hi = min(ys_candidates), max(ys_candidates)
    for so in s.Solids:
        bb = so.BoundBox
        if bb.YMin >= hi: out.append(so); continue
        if bb.YMax <= lo: m = so.copy(); m.translate(V(0, -dy, 0)); out.append(m); continue
        done = False
        for ys in ys_candidates:
            if not (bb.YMin + 1 < ys and ys + copy < bb.YMax - 1): continue
            back, fs = section_at(so, ys); _, fs2 = section_at(so, ys + copy)
            if not fs or len(fs) != len(fs2) or abs(sum(f.Area for f in fs) - sum(f.Area for f in fs2)) > 1e-3: continue
            seg = so.common(Part.makeBox(big, copy, big, V(-big / 2, ys, -big / 2))); seg.translate(V(0, -copy, 0))
            front = so.common(Part.makeBox(big, ys - bb.YMin + 1, big, V(-big / 2, bb.YMin - 1, -big / 2)))
            front.translate(V(0, -dy, 0))
            parts = back.Solids + front.Solids + seg.Solids
            out += parts[0].fuse(parts[1:]).removeSplitter().Solids; cuts.append(ys); done = True; break
        if not done: return None, None
    return Part.makeCompound(out), cuts


def splice_tube(s, ys_candidates, dy, d):
    """A swept tube or cable: cut where its Y section is one loop whose length is nearest pi x d (the run is along Y
    there), move the Y < ys part -dy, fill with that section extruded. (new, ys, area, perimeter error)"""
    big = 5000; best = None
    for ys in ys_candidates:
        sec = s.section(Part.makePlane(big, big, V(-big / 2, ys, -big / 2), V(0, 1, 0)))
        loops = Part.sortEdges(sec.Edges) if sec.Edges else []
        if len(loops) != 1: continue
        err = abs(Part.Wire(loops[0]).Length - math.pi * d) / (math.pi * d)
        if best is None or err < best[1]: best = (ys, err)
    if best is None: return None, None, None, None
    ys = best[0]
    back, fs = section_at(s, ys)
    if len(fs) != 1: return None, ys, None, best[1]
    bb = s.BoundBox
    front = s.common(Part.makeBox(big, ys - bb.YMin + 1, big, V(-big / 2, bb.YMin - 1, -big / 2)))
    front.translate(V(0, -dy, 0))
    pieces = back.Volume + front.Volume                   # (a sweep's own Volume can be off: lite-36's tubes by ~4 %)
    new = back.fuse([front, fs[0].extrude(V(0, -dy, 0))]).removeSplitter()
    return new, ys, fs[0].Area, best[1], pieces


def parked_zero(y_front, z0):
    """The Zero on its carrier, the switch's front at y_front, the carrier's underside at z0: {key: (label, shape)}."""
    bx = lambda x0, x1, y0, y1, za, zb: Part.makeBox(x1 - x0, y1 - y0, zb - za, V(x0, y0, za))
    b0 = y_front + SW_Y                                   # the body's front
    b1 = b0 + BODY_Y                                      # its rear (mounting) face
    zb, zt = z0 + BASE_T, z0 + BASE_T + BODY_H
    body = bx(X0 - BODY_X / 2, X0 + BODY_X / 2, b0, b1, zb, zt)
    yc = (b0 + b1) / 2
    bz = zt + PROBE_H - BALL_D / 2
    probe = Part.makeCylinder(BUSH_D / 2, BUSH_H, V(X0, yc, zt)).fuse(
        [Part.makeCylinder(PIN_D / 2, bz - zt - BUSH_H, V(X0, yc, zt + BUSH_H)), Part.makeSphere(BALL_D / 2, V(X0, yc, bz))]).removeSplitter()
    switch = bx(X0 - 4, X0 + 4, y_front, b0, zb, zb + 6)
    # the carrier: a base under the whole Zero, a back plate the body bolts to (lite-61's 2 x M3 holes)
    base = bx(X0 - 15, X0 + 15, y_front - BASE_MARGIN, b1 + BACK_T, z0, zb)
    back = bx(X0 - 12, X0 + 12, b1, b1 + BACK_T, zb, zt)
    zc = (zb + zt) / 2
    holes = [Part.makeCylinder(1.7, BACK_T + 2, V(X0 + dx, b1 - 1, zc + dz), V(0, 1, 0)) for dx, dz in ((-5, 5), (5, -5))]
    yl = (y_front - BASE_MARGIN + b1 + BACK_T) / 2
    mags = [(X0 + dx, yl + dy_) for dx in (-8.5, 8.5) for dy_ in (-7.0, 7.0)]
    pockets = [Part.makeCylinder(MAG_D / 2 + MAG_CLR, MAG_H, V(x, y, z0)) for x, y in mags]
    carrier = base.fuse([back]).removeSplitter().cut(Part.makeCompound(holes + pockets)).removeSplitter()
    carrier, info = printchamfer.chamfer(carrier, V(0, 0, 1), **CHAMFER)
    out = {"body": ("Mellow MultiHead Zero body (aluminium, 20 x 17.2 x 22, from Mellow's drawing), parked", body),
           "probe": ("Mellow MultiHead Zero probe (bushing, pin, D 10 ball; estimated from the photo), parked", probe),
           "switch": ("Mellow MultiHead Zero switch + XH2.54 plug (in the body's slot, stand-in), parked", switch),
           "carrier": (f"Mellow parking carrier (magnetic, on the backbone) {LIC}", carrier)}
    for i, (x, y) in enumerate(mags):
        out[f"mag{i}"] = (f"Mellow carrier magnet {i + 1} (D10 x 3 N52 disc)", Part.makeCylinder(MAG_D / 2, MAG_H, V(x, y, z0)))
    return out, info


def rail_490(r400, y0):
    """A 490 MGN9 rail from Y y0: the 400's section (at a clean Y) extruded, with the 400's hole cut (its first one,
    taken as the difference of its plain extrusion and the rail) repeated on Hiwin's pattern."""
    bb = r400.BoundBox
    for ys in [bb.YMin + 10.0 + 0.5 * i for i in range(40)]:
        _, fs = section_at(r400, ys); _, fs2 = section_at(r400, ys + 3.0)
        if fs and abs(sum(f.Area for f in fs) - sum(f.Area for f in fs2)) < 1e-3: break
    else: raise RuntimeError("no clean section on the 400 rail")
    prof = [f.copy() for f in fs]
    for f in prof: f.translate(V(0, bb.YMin - ys, 0))
    plain400 = Part.makeCompound([f.extrude(V(0, bb.YLength, 0)) for f in prof]).fuse([]).removeSplitter() \
        if len(prof) > 1 else prof[0].extrude(V(0, bb.YLength, 0))
    holes = [h for h in plain400.cut(r400).Solids if h.Volume > 1.0]
    body = prof[0].extrude(V(0, RAIL_L, 0)) if len(prof) == 1 else Part.makeCompound(
        [f.extrude(V(0, RAIL_L, 0)) for f in prof]).fuse([]).removeSplitter()
    body.translate(V(0, y0 - bb.YMin, 0))
    if not holes: return body, 0, 0                     # the model's 400 is a plain bar (no holes): so is the 490
    h0 = min(holes, key=lambda h: h.BoundBox.YMin)
    hc = (h0.BoundBox.YMin + h0.BoundBox.YMax) / 2
    cuts = []
    k = 0
    while RAIL_END + RAIL_PITCH * k <= RAIL_L - RAIL_END + 1e-6:
        h = h0.copy(); h.translate(V(0, y0 + RAIL_END + RAIL_PITCH * k - hc, 0)); cuts.append(h); k += 1
    return body.cut(cuts).removeSplitter(), k, len(holes)


def to_local(o, g):
    """A global shape in o's own frame (lite77's helper)."""
    g = g.copy(); pl = g.Placement; g.Placement = FreeCAD.Placement(); g.transformShape(pl.toMatrix(), True, False)
    g.transformShape(linkgeo.gplace(o).inverse().toMatrix(), True, False)
    g.Placement = o.Placement
    return g


def unlink(doc, o, shape_global):
    """Replace the App::Link o by a Part::Feature with shape_global, in o's container, with o's label and colour."""
    holder = o.getParentGeoFeatureGroup()
    vo = linkgeo.drawn_vo(o)
    f = doc.addObject("Part::Feature", o.Name + "_own")
    if holder is not None: holder.addObject(f)
    f.Placement = FreeCAD.Placement(); f.Shape = to_local(f, shape_global)
    label = o.Label; doc.removeObject(o.Name); f.Label = label
    if vo is not None and getattr(f, "ViewObject", None) is not None:
        try: f.ViewObject.ShapeAppearance = vo.ShapeAppearance; f.ViewObject.Transparency = vo.Transparency
        except Exception: pass
    return f


def move_global(o, dy):
    par = o.getParentGeoFeatureGroup()
    pg = linkgeo.gplace(par) if par is not None else FreeCAD.Placement()
    o.Placement = pg.inverse().multiply(FreeCAD.Placement(V(0, dy, 0), FreeCAD.Rotation())).multiply(pg).multiply(o.Placement)


def overlaps(p, m, items, skip_of):
    """{(tag, leaf Label)} with common() volume > TOL: items [(tag, shape, Name)] against every leaf whose box meets the
    item's, but those in skip_of(Name) (a set of Names)."""
    cand = [(tag, s, o) for tag, s, n in items for o in m.leaves
            if o.Name not in skip_of(n) and m.boxes[o.Name].intersect(s.BoundBox)]
    vols = p.volumes([(s, m.shapes[o.Name]) for _, s, o in cand])
    return {(tag, o.Label) for (tag, _, o), v in zip(cand, vols) if v > TOL}, len(cand)


def preview(path, sets):
    """LITE78_PREVIEW=<dir>: STLs of a few regions for review images (platform/render/render_parts.py), never the model.
    sets {scene: [(file stem, shape, role)]} -> <dir>/<scene>/<stem>.stl + parts.json."""
    import MeshPart, json, re
    for sc, items in sets.items():
        d = os.path.join(path, sc); os.makedirs(d, exist_ok=True); idx = []
        for i, (stem, s, role) in enumerate(items):
            fn = f"{i:04d}-" + re.sub(r"[^A-Za-z0-9]+", "_", stem)[:50] + ".stl"
            MeshPart.meshFromShape(Shape=s, LinearDeflection=0.1, AngularDeflection=0.3).write(os.path.join(d, fn))
            idx.append(dict(file=fn, label=stem, role=role))
        json.dump(idx, open(os.path.join(d, "parts.json"), "w"), indent=0)


def main(p):
    m = p.open(SRC); doc = m.doc
    par = linkgeo.group_parents(doc.Objects)
    top = {o.Name: (linkgeo.group_path(o, par) + ["", ""])[1] for o in m.leaves}
    gp = {o.Name: " / ".join(linkgeo.group_path(o, par)) for o in m.leaves}     # before anything is removed or replaced
    box = {o.Name: m.shapes[o.Name].BoundBox for o in m.leaves}
    lab = {o.Name: o.Label for o in m.leaves}
    stay = {n for n, l in lab.items() if l.startswith(STAY) or l in STAY_EXACT}
    rails_old = {n for n, l in lab.items() if l.startswith(RAILS_OLD)}
    tubes = {n for n, l in lab.items() if l.startswith(TUBES)}
    cables = {n for n, l in lab.items() if l.startswith(CABLES)}
    old_probe = {n for n in lab if top[n].startswith(OLD_PROBE)}
    special = tubes | cables | old_probe
    front = {n for n in lab if n not in stay and n not in rails_old and n not in special
             and (box[n].YMax <= FRONT_Y or any(k in top[n] for k in FRONT_GROUPS))}
    belts = {n for n, l in lab.items() if l.startswith(BELTS)}
    cross = {n for n in lab if n not in front | stay | rails_old | belts | special and box[n].YMin < FRONT_Y}
    p.log(f"{len(m.leaves)} leaves: {len(front)} move -{DY:g}, {len(cross)} spliced, {len(belts)} belts, "
          f"{len(rails_old)} rail pieces replaced, {len(stay)} stay by name ({sorted(lab[n] for n in stay)})")
    for n in sorted(cross, key=lambda n: lab[n]): p.log(f"   splice: {lab[n]} [{top[n]}] Y {box[n].YMin:.1f}..{box[n].YMax:.1f}")
    p.check(len(rails_old) == 4, f"four old Y rail pieces ({sorted(lab[n] for n in rails_old)})")
    p.check(len(belts) == 2, f"two belts ({len(belts)})")
    p.check(len(tubes) == 5 and len(cables) == 5, f"five Bowden tubes and five O2S cables ({len(tubes)}, {len(cables)})")
    p.check(len(old_probe) == 4, f"lite-61's probe: 4 parts to remove ({sorted(lab[n] for n in old_probe)})")
    att = [lab[n] for n in front | cross | belts | tubes | cables
           if getattr(doc.getObject(n), "MapMode", "Deactivated") not in ("Deactivated", None)]
    p.check(not att, f"no moved or spliced leaf is attached (an attachment would undo the move): {att[:5]}")
    # A spliced part that is an App::Link (dupes.py shares one shape between copies) gets its own Part::Feature.
    # A spliced Part::Feature must not be the target of a link that isn't spliced too (its shape would change with it).
    links = [o for o in m.leaves if o.TypeId == "App::Link"]
    tgt_of = {o.Name: linkgeo.link_target(o).Name for o in links}
    # links that share a spliced part's shape but don't change (e.g. the back felt liners, copies of the roof liners)
    # get their own Part::Feature with their current geometry first
    spl = cross | belts | tubes | cables
    keep = sorted(l for l, t in tgt_of.items() if t in spl and l not in spl)
    p.log(f"   {len(keep)} unchanged links share a spliced shape, so they get their own copy first: "
          f"{sorted(lab[l] for l in keep)}")
    p.log(f"   {sum(1 for n in spl if n in tgt_of)} spliced parts are links: each becomes its own Part::Feature")
    shared_probe = sorted(lab[l] for l, t in tgt_of.items() if t in old_probe and l not in old_probe)
    p.check(not shared_probe, f"nothing else links to lite-61's probe parts: {shared_probe}")
    if p.errs: return p.finish([])
    # ---- 0. the baseline for the collision check: every part this pass moves, splices or replaces, against the rest
    env = {n for n, l in lab.items() if "envelope" in l}
    tag = lambda n: ("Y rail " + lab[n].split("(")[1][0]) if n in rails_old else lab[n]
    watched = (front | spl | rails_old) - env
    p.log(f"collision baseline: {len(watched)} parts vs the rest (lite-77) ...")
    # pairs inside the front set move together and can't change: a front part is checked against the rest only
    front_skip = front | env | old_probe
    all_skip = env | old_probe
    skip0 = lambda n: front_skip | {n} if n in front else all_skip | {n}
    base_hits, nc = overlaps(p, m, [(tag(n), m.shapes[n], n) for n in watched], skip0)
    p.log(f"collision baseline (lite-77): {nc} pairs, {len(base_hits)} overlaps")
    old_shapes = {n: m.shapes[n].copy() for n in lab} if os.environ.get("LITE78_PREVIEW") else {}
    mounts = {k: [o for o in m.leaves if o.Label.startswith(k)] for k in (FRONT_MOUNT, REAR_MOUNT)}
    vols0 = {n: m.shapes[n].Volume for n in spl}
    renamed = {}
    for l in keep: renamed[l] = unlink(doc, doc.getObject(l), m.shapes[l]).Name
    # ---- 1. the front set
    for n in front: move_global(doc.getObject(n), -DY)
    # ---- 2. splices
    spliced = {}
    for n in sorted(cross, key=lambda n: lab[n]):
        o = doc.getObject(n); s = m.shapes[n]
        new, ys, area = splice_multi(s, SPLICE_Y, DY)
        if new is None: p.check(False, f"splice {lab[n]}: no clean section in {SPLICE_Y[0]:g}..{SPLICE_Y[-1]:g}"); continue
        spliced[n] = (ys, area, len(s.Solids))
        if o.TypeId == "App::Link": renamed[n] = unlink(doc, o, new).Name
        else: o.Shape = to_local(o, new)
    for n in sorted(belts, key=lambda n: lab[n]):
        o = doc.getObject(n); s = m.shapes[n]
        new, cuts = splice_belt(s, BELT_Y, DY, BELT_COPY)
        if new is None: p.check(False, f"belt {lab[n]}: no clean cut"); continue
        p.log(f"   belt {lab[n]}: {len(cuts)} strand(s) spliced at Y {cuts}")
        if o.TypeId == "App::Link": renamed[n] = unlink(doc, o, new).Name
        else: o.Shape = to_local(o, new)
    tube_cut = {}
    for n in sorted(tubes | cables, key=lambda n: lab[n]):
        o = doc.getObject(n); s = m.shapes[n]
        new, ys, area, err, pieces = splice_tube(s, TUBE_Y, DY, TUBE_D if n in tubes else CABLE_D)
        if new is not None: vols0[n] = pieces
        if new is None: p.check(False, f"splice {lab[n]}: no single round section in {TUBE_Y[0]:g}..{TUBE_Y[-1]:g}"); continue
        spliced[n] = (ys, area, len(s.Solids)); tube_cut[n] = err
        if o.TypeId == "App::Link": renamed[n] = unlink(doc, o, new).Name
        else: o.Shape = to_local(o, new)
    # the zip ties on each run in front of its cut move with the run's front end
    cut_lo = min(spliced[n][0] for n in tube_cut) if tube_cut else 0.0
    ties = {n for n in lab if RUN_GROUP in gp[n] and n not in spl
            and box[n].YMax <= cut_lo}
    p.log(f"   {len(ties)} parts on the tube + cable runs in front of Y {cut_lo:g} move with them: {sorted({lab[n].split(' slot')[0] for n in ties})}")
    for n in ties: move_global(doc.getObject(n), -DY)
    # ---- 3. rails
    fm = {s: min(m.shapes[o.Name].BoundBox.YMax for o in mounts[FRONT_MOUNT]) for s in "RL"}
    rm = min(m.shapes[o.Name].BoundBox.YMin for o in mounts[REAR_MOUNT])
    gap0 = rm - fm["R"]
    y0 = fm["R"] - DY + (gap0 + DY - RAIL_L) / 2
    new_rails = {}
    for side, l400 in RAIL_400.items():
        o400 = next(doc.getObject(n) for n in rails_old if lab[n].startswith(l400))
        r, nh, nh400 = rail_490(m.shapes[o400.Name], y0)
        p.log(f"   rail {side}: 490 from Y {y0:.2f}; {nh} holes (the 400 had {nh400})")
        holder = o400.getParentGeoFeatureGroup()
        f = doc.addObject("Part::Feature", f"YRail490_{side}")
        if holder is not None: holder.addObject(f)
        f.Label = f"MGN9 Y rail ({side}) - Hiwin MGNR9 490 mm, one piece (Motion Constrained; vt350#291)"
        f.Placement = FreeCAD.Placement(); f.Shape = to_local(f, r)
        new_rails[side] = f
    for n in rails_old: doc.removeObject(n)
    # ---- 4. lite-61's probe off the bed; the Zero parked on the backbone
    grp_old = next((g for g in doc.Objects if g.TypeId == "App::Part" and g.Label.startswith(OLD_PROBE)), None)
    for n in old_probe: doc.removeObject(n)
    if grp_old is not None: doc.removeObject(grp_old.Name)
    bb_ = m.shapes[next(n for n, l in lab.items() if l.startswith("backbone-350"))].BoundBox
    bed_front = min(box[n].YMin for n in lab if lab[n].startswith(("PEI spring-steel", "Magnetic sheet")))
    strip = (bb_.YMin, bed_front)
    depth = BASE_MARGIN + SW_Y + BODY_Y + BACK_T                  # the carrier's Y depth
    y_front = (strip[0] + strip[1] - depth) / 2 + BASE_MARGIN     # centred on the strip
    parts, cinfo = parked_zero(y_front, bb_.ZMax)
    root = m.root("4040-350x350x250 Voron Trident")
    grp = doc.addObject("App::Part", "OffsetProbeParked"); grp.Label = "Nozzle offset probe, parked on the backbone (lite-78, #291)"
    root.addObject(grp)
    made = {}
    for k, (label, sh) in parts.items():
        o = doc.addObject("Part::Feature", "MHZP_" + k); grp.addObject(o)
        o.Placement = FreeCAD.Placement(); o.Shape = to_local(o, sh); o.Label = label; made[k] = o
    doc.recompute()
    m.refresh()
    # ---- after
    now = {o.Name: m.shapes[o.Name].BoundBox for o in m.leaves}
    for old, new in renamed.items(): now[old] = now[new]; m.shapes[old] = m.shapes[new]
    def same(a, b, dy=0.0):
        return all(abs(x - y) <= TOL for x, y in zip((a.XMin, a.YMin + dy, a.ZMin, a.XMax, a.YMax + dy, a.ZMax),
                                                      (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
    bad_move = [lab[n] for n in front if n not in now or not same(box[n], now[n], -DY)]
    bad_ties = [lab[n] for n in ties if not same(box[n], now[n], -DY)]
    p.check(not bad_ties, f"{len(ties)} zip ties moved -{DY:g} with their runs ({bad_ties[:3]})")
    bad_stay = [lab[n] for n in lab if n not in front | spl | rails_old | old_probe | ties and (n not in now or not same(box[n], now[n]))]
    gone = [lab[n] for n in old_probe if doc.getObject(n) is not None]
    p.check(not gone, f"lite-61's bracket and Zero removed ({gone})")
    p.check(not bad_move, f"{len(front)} front leaves moved exactly -{DY:g} ({len(bad_move)} not: {bad_move[:5]})")
    p.check(not bad_stay, f"every other leaf unchanged ({len(bad_stay)} changed: {bad_stay[:5]})")
    for n, (ys, area, nsol) in spliced.items():
        s = m.shapes[n]; b = s.BoundBox; want = vols0[n] + area * DY
        vtol = 0.005 * want if n in tube_cut else max(1.0, 1e-5 * want)     # B-spline sweeps: volumes to ~0.3 %
        ok = (s.isValid() and len(s.Solids) == nsol and abs(b.YMin - (box[n].YMin - DY)) < TOL
              and abs(b.YMax - box[n].YMax) < TOL and abs(s.Volume - want) <= vtol)
        p.check(ok, f"spliced {lab[n]} at Y {ys:g}: Y {b.YMin:.2f}..{b.YMax:.2f} (was {box[n].YMin:.2f}..{box[n].YMax:.2f}), "
                    f"solids {len(s.Solids)}/{nsol}, valid {s.isValid()}, vol {s.Volume:.0f} (want {want:.0f})")
    for n, err in sorted(tube_cut.items(), key=lambda kv: lab[kv[0]]):
        p.check(err < 0.01, f"{lab[n][:30]}: cut at Y {spliced[n][0]:g}, section perimeter {100 * err:.2f} % off pi x d")
    for n in belts:
        s = m.shapes[n]
        p.check(s.isValid() and abs(s.BoundBox.YMin - (box[n].YMin - DY)) < TOL,
                f"belt {lab[n]}: valid {s.isValid()}, Y {s.BoundBox.YMin:.2f}..{s.BoundBox.YMax:.2f} "
                f"(was {box[n].YMin:.2f}..{box[n].YMax:.2f}), vol {vols0[n]:.0f} -> {s.Volume:.0f}")
    fm2 = min(m.shapes[o.Name].BoundBox.YMax for o in mounts[FRONT_MOUNT])
    for side, f in new_rails.items():
        b = m.shapes[f.Name].BoundBox
        p.check(m.shapes[f.Name].isValid() and abs(b.YLength - RAIL_L) < TOL
                and abs(b.YMin - fm2 - (gap0 + DY - RAIL_L) / 2) < TOL and abs(rm - b.YMax - (gap0 + DY - RAIL_L) / 2) < TOL,
                f"rail {side}: Y {b.YMin:.2f}..{b.YMax:.2f} ({b.YLength:.2f} long), {b.YMin - fm2:.2f} from the front "
                f"mount and {rm - b.YMax:.2f} from the rear one (gap {gap0:.2f} -> {gap0 + DY:.2f})")
    # the parked Zero
    sh = {k: m.shapes[o.Name] for k, o in made.items()}
    for k, o in made.items():
        p.check(sh[k].isValid() and len(sh[k].Solids) == 1, f"{o.Label[:44]}: one valid solid, {sh[k].Volume:.0f} mm3")
    cb = sh["carrier"].BoundBox
    p.check(abs(cb.ZMin - bb_.ZMax) < TOL and bb_.YMin <= cb.YMin and cb.YMax <= strip[1] - BED_CLEAR,
            f"the carrier on the backbone's top (Z {cb.ZMin:.2f} = {bb_.ZMax:.2f}), Y {cb.YMin:.1f}..{cb.YMax:.1f} inside the "
            f"strip {strip[0]:.1f}..{strip[1]:.1f} with {strip[1] - cb.YMax:.1f} to the bed's front edge")
    p.check(abs(sh["body"].BoundBox.ZMin - cb.ZMin - BASE_T) < TOL, "the Zero's body stands on the carrier's base")
    p.check(not cinfo.get("failed"), f"carrier chamfered: {cinfo['bottom']} bottom + {cinfo['top']} top edges, "
                                    f"{len(cinfo['reduced'])} reduced, failed {cinfo.get('failed')}")
    for i in range(4):
        mb = sh[f"mag{i}"]
        p.check(mb.common(sh["carrier"]).Volume < TOL and abs(mb.BoundBox.ZMin - bb_.ZMax) < TOL,
                f"magnet {i + 1} in its pocket, on the backbone")
    # the bed at its lowest (BED_LOWEST_DZ): every bed-side leaf within 40 mm, moved down, >= BED_CLEAR off the Zero
    allb = FreeCAD.BoundBox()
    for s_ in sh.values(): allb.add(s_.BoundBox)
    zone = FreeCAD.BoundBox(allb.XMin - 40, allb.YMin - 40, allb.ZMin - 40 - BED_LOWEST_DZ, allb.XMax + 40, allb.YMax + 40,
                            allb.ZMax + 40 - BED_LOWEST_DZ)
    bedside = [o for o in m.leaves if BED_Z[0] <= m.boxes[o.Name].ZMin <= BED_Z[1] and m.boxes[o.Name].ZMax <= BED_Z[1]
               and m.boxes[o.Name].intersect(zone)]
    dmin, who = 999.0, ""
    zero = Part.makeCompound(list(sh.values()))
    for o in bedside:
        b = m.shapes[o.Name].copy(); b.translate(V(0, 0, BED_LOWEST_DZ))
        d = zero.distToShape(b)[0]
        if d < dmin: dmin, who = d, o.Label
    p.check(dmin >= BED_CLEAR, f"the bed at its lowest (dZ {BED_LOWEST_DZ:g}) keeps {dmin:.1f} mm off the parked Zero "
                               f"(>= {BED_CLEAR:g}; nearest {who[:40]}, {len(bedside)} bed parts near)")
    cmap = colours.load(f"{_REPO}/cad/render/colours.json")
    roles = {k: colours.role_of(cmap, o.Label, grp.Label, "Default") for k, o in made.items()}
    p.check(roles["body"] == "brushed_aluminium" and roles["probe"] == "brushed_steel" and roles["switch"] == "black_plastic"
            and roles["carrier"] == "printed" and all(roles[f"mag{i}"] == "brushed_steel" for i in range(4)), f"roles {roles}")
    # COLLISIONS vs lite-77
    watched_now = {(renamed.get(n, n)) for n in watched if n not in rails_old} | {f.Name for f in new_rails.values()}
    rtag = {f.Name: f"Y rail {s}" for s, f in new_rails.items()}
    mine = {o.Name for o in made.values()}
    front_now = {renamed.get(n, n) for n in front}
    skip1 = lambda n: (front_now | env | mine | {n}) if n in front_now else (env | mine | {n})
    names = [n for n in watched_now if n in m.shapes] + list(mine)
    tags = {**{n: rtag.get(n, lab.get(n) or doc.getObject(n).Label) for n in watched_now}, **{o.Name: o.Label for o in made.values()}}
    hits1, nc1 = overlaps(p, m, [(tags[n], m.shapes[n], n) for n in names], skip1)
    new_hits = sorted(hits1 - base_hits - {(b, a) for a, b in base_hits})
    gone_hits = sorted(base_hits - hits1)
    p.log(f"collision check: {nc1} pairs, {len(hits1)} overlaps now, {len(base_hits)} in lite-77; {len(gone_hits)} gone: {gone_hits[:6]}")
    zero_hits = [h for h in hits1 if h[0] in {o.Label for o in made.values()}]
    r1 = type("R", (), {"hits": hits1})
    p.check(not new_hits and not zero_hits, f"COLLISIONS: no overlap lite-77 didn't have ({len(new_hits)} new: {new_hits[:8]}; "
                                            f"parked Zero: {zero_hits[:4]})")
    pv = os.environ.get("LITE78_PREVIEW")
    if pv:
        role = lambda o: colours.role_of(cmap, o.Label, "", "Default")
        near = lambda bb, zone: bb.intersect(zone)
        # 1. the parked Zero with what's round it, the bed at its lowest
        z1 = FreeCAD.BoundBox(allb.XMin - 120, allb.YMin - 60, allb.ZMin - 30, allb.XMax + 120, allb.YMax + 90, allb.ZMax + 60)
        sc1 = [(o.Label, m.shapes[o.Name], role(o)) for o in m.leaves if o.Name not in mine and near(m.boxes[o.Name], z1)
               and not (BED_Z[0] <= m.boxes[o.Name].ZMin <= BED_Z[1] and m.boxes[o.Name].ZMax <= BED_Z[1])]
        z1b = FreeCAD.BoundBox(z1.XMin, z1.YMin, z1.ZMin - BED_LOWEST_DZ, z1.XMax, z1.YMax, z1.ZMax - BED_LOWEST_DZ)
        for o in m.leaves:
            b = m.boxes[o.Name]
            if BED_Z[0] <= b.ZMin <= BED_Z[1] and b.ZMax <= BED_Z[1] and near(b, z1b):
                t = m.shapes[o.Name].copy(); t.translate(V(0, 0, BED_LOWEST_DZ)); sc1.append((o.Label + " (bed at its lowest)", t, role(o)))
        sc1 += [(o.Label, sh[k], role(o)) for k, o in made.items()]
        # 2. tubes and cables, before (lite-77) and after, with the docked heads after
        sc2 = [(lab[n] + " BEFORE", old_shapes[n], "before") for n in tubes | cables]
        sc2 += [(lab[n], m.shapes[renamed.get(n, n)], "after") for n in tubes | cables]
        sc2 += [(lab[n], m.shapes[renamed.get(n, n)], role(doc.getObject(renamed.get(n, n)))) for n in front
                if any(k in top[n] for k in ("Toolhead",)) and m.boxes[renamed.get(n, n)].ZMax > 380]
        # 3. the front corner, before and after: the frame, rails, docks
        z3 = FreeCAD.BoundBox(-520, -140, -20, -330, 120, 720)
        sc3a = [(lab[n], old_shapes[n], role(doc.getObject(renamed.get(n, n))) if doc.getObject(renamed.get(n, n)) else "Default")
                for n in old_shapes if n in lab and near(old_shapes[n].BoundBox, z3) and n not in env]
        sc3b = [(o.Label, m.shapes[o.Name], role(o)) for o in m.leaves if near(m.boxes[o.Name], z3) and o.Name not in env]
        preview(pv, {"zero_parked": sc1, "tubes_cables": sc2, "front_before": sc3a, "front_after": sc3b})
        p.log(f"preview STLs in {pv}: {len(sc1)}, {len(sc2)}, {len(sc3a)}, {len(sc3b)} parts")
    p.dump(dict(dy=DY, front=len(front), spliced={lab[n]: v[0] for n, v in spliced.items()}, rail_y0=y0,
                mount_gap=[gap0, gap0 + DY], parked_zero=dict(y_front=y_front, strip=list(strip), bed_gap=dmin),
                collisions=dict(now=len(r1.hits), lite77=len(base_hits), new=new_hits, gone=gone_hits),
                hardware="carrier: 2 x M3x25 + nut (Zero to carrier), 4 x D10 x 3 N52 discs (glued in)"))
    return p.finish([(doc, DST)])


if not os.environ.get("LITE78_AS_LIB"): litelib.Pass("lite78_front17").run(main)
