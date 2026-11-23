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
#  - The Mellow MultiHead Zero stays on the bed's front edge, LOWER and to the LEFT (owner, 2026-11-23): Nudge's
#    INSTRUCTIONS.md puts a fixed mount's probe top ~1 mm above the print surface (lite-61's was ~9), and the sheet's
#    tab is at the front centre. Ball at printer (50, -9.5): the left window where both heads reach all four sides of
#    it with 6 mm overtravel (cad/studies/mellow_edge_reach.py), its bushing 0.5 mm in front of the plate. lite-61's
#    bracket and Zero are removed and rebuilt there with lite-61's geometry (bracket on the bed's front 2020).
# Checks (refuses to save on any): every leaf moved exactly -17, unchanged, spliced, removed (rails, lite-61's probe)
# or new (rails, the Zero and its bracket); spliced parts valid with their solid count, their front end -17 and their
# volume + section x 17; tubes and cables cut where the section's perimeter is within 1 % of pi x d; rails 490 long,
# 0.46 mm from each mount, valid; the Zero: each part one valid solid, the bracket on the 2020's face and >= 3 below
# the heater, the ball top 1.0 above the PEI and only the probe above the PEI, the bushing >= 0.5 and ball >= 2 in
# front of the plate and sheet, both heads reach all 4 sides (front_reach_front17.json), over the bed's Z travel it
# hits no fixed part; no leaf left with an attachment that would undo the move on recompute;
# COLLISIONS vs lite-77: every moved, spliced or new part against the rest, no overlap that lite-77 didn't have.
import FreeCAD, Part, os, sys, math, json
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
# the Zero on the bed's front edge (owner, 2026-11-23). Ball centre at printer (50, -9.5): model = printer + (-420, 30.5)
# (cad/klipper/xy_mapping.json, read below)
BALL_PX, BALL_PY = 50.0, -9.5
BALL_ABOVE_PEI = 1.0                                        # its top over the print surface (Nudge INSTRUCTIONS.md)
OVERTRAVEL = 6.0                                            # Nudge's table; ours needs ~5 (mellow_edge_reach.py)
BODY_X, BODY_Y, BODY_H, PROBE_H = 20.0, 17.2, 22.0, 23.0    # lite-61 (Mellow's drawing; the probe estimated)
BUSH_D, BUSH_H, PIN_D, BALL_D = 13.0, 10.0, 5.0, 10.0
BR_T, HEATER_GAP = 4.0, 3.0                                 # lite-61's bracket: wall, and its gap under the heater pad
BED2020 = "2020 (1)"                                        # the bed's front 2020 (lite-61: X -480..-10, Y 60.8, Z 240)
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


def edge_zero(x0, by, ball_top, fb, heater_zmin):
    """lite-61's Zero and bracket at ball centre (x0, by) with the ball's top at ball_top (model coordinates): the body
    under the probe, the bracket's back plate on the bed 2020's front face fb (a BoundBox), an arm forward under the
    plate, a front plate the body bolts to; nothing of it within HEATER_GAP of the heater pad. {key: (label, shape)}."""
    bx = lambda x0_, x1, y0, y1, za, zb: Part.makeBox(x1 - x0_, y1 - y0, zb - za, V(x0_, y0, za))
    bz = ball_top - BALL_D / 2
    body_top = ball_top - PROBE_H; body_bot = body_top - BODY_H
    body = bx(x0 - BODY_X / 2, x0 + BODY_X / 2, by - BODY_Y / 2, by + BODY_Y / 2, body_bot, body_top)
    probe = Part.makeCylinder(BUSH_D / 2, BUSH_H, V(x0, by, body_top)).fuse(
        [Part.makeCylinder(PIN_D / 2, bz - (body_top + BUSH_H), V(x0, by, body_top + BUSH_H)),
         Part.makeSphere(BALL_D / 2, V(x0, by, bz))]).removeSplitter()
    switch = bx(x0 - 4, x0 + 4, by - BODY_Y / 2 - 6, by - BODY_Y / 2, body_bot, body_bot + 6)
    yb = by + BODY_Y / 2                                      # the body's rear (mounting) face
    zc_top = heater_zmin - HEATER_GAP
    back = bx(x0 - 15, x0 + 15, fb.YMin - BR_T, fb.YMin, fb.ZMin, min(fb.ZMax, zc_top))
    front = bx(x0 - 12, x0 + 12, yb, yb + BR_T, min(body_bot - 4, fb.ZMin), min(zc_top, body_top))
    arm = bx(x0 - 8, x0 + 8, yb, fb.YMin - BR_T, fb.ZMin + 6, fb.ZMin + 16)
    rib = bx(x0 - 2, x0 + 2, yb + BR_T, fb.YMin - BR_T, fb.ZMin + 16, min(zc_top, fb.ZMax))
    holes = [Part.makeCylinder(1.7, BR_T + 2, V(x0 + dx, fb.YMin - BR_T - 1, (fb.ZMin + fb.ZMax) / 2), V(0, 1, 0))
             for dx in (-10, 10)]
    zc = (body_bot + body_top) / 2
    holes += [Part.makeCylinder(1.7, BR_T + 2, V(x0 + dx, yb - 1, zc + dz), V(0, 1, 0)) for dx, dz in ((-5, 5), (5, -5))]
    bracket = back.fuse([front, arm, rib]).removeSplitter().cut(Part.makeCompound(holes)).removeSplitter()
    bracket, info = printchamfer.chamfer(bracket, V(0, -1, 0), **CHAMFER)     # printed on its back plate
    return {"body": ("Mellow MultiHead Zero body (aluminium, 20 x 17.2 x 22, from Mellow's drawing)", body),
            "probe": ("Mellow MultiHead Zero probe (bushing, pin, D 10 ball; estimated from the photo)", probe),
            "switch": ("Mellow MultiHead Zero switch + XH2.54 plug (in the body's slot, stand-in)", switch),
            "bracket": (f"Nozzle offset probe bracket (low, lite-78) {LIC}", bracket)}, info


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
    # ---- 4. lite-61's probe off the bed, rebuilt lower and to the left on the bed's front edge (owner, 2026-11-23)
    grp_old = next((g for g in doc.Objects if g.TypeId == "App::Part" and g.Label.startswith(OLD_PROBE)), None)
    for n in old_probe: doc.removeObject(n)
    if grp_old is not None: doc.removeObject(grp_old.Name)
    one = lambda pre: [n for n, l in lab.items() if l.startswith(pre)]
    pei, plate, heater = one("PEI spring-steel"), one("LDO 350 build plate"), one("Heater pad LDO")
    fr = [n for n, l in lab.items() if l == BED2020 and box[n].ZMin > 200 and box[n].YMax < 100]
    p.check(len(pei) == len(plate) == len(heater) == len(fr) == 1,
            f"PEI sheet {len(pei)}, plate {len(plate)}, heater {len(heater)}, bed front 2020 {len(fr)}")
    if p.errs: return p.finish([])
    mp = json.load(open(os.path.join(_REPO, "cad/klipper/xy_mapping.json")))
    (ox, oy), (gx, gy) = mp["origin_model_xy"], mp["sign_xy"]
    zx, zy = ox + gx * BALL_PX, oy + gy * BALL_PY                  # the ball centre, model XY
    pei_top = box[pei[0]].ZMax
    parts, binfo = edge_zero(zx, zy, pei_top + BALL_ABOVE_PEI, box[fr[0]], box[heater[0]].ZMin)
    root = m.root("4040-350x350x250 Voron Trident")
    grp = doc.addObject("App::Part", "OffsetProbe78"); grp.Label = "Nozzle offset probe, low on the bed edge (lite-78, #291)"
    root.addObject(grp)
    made = {}
    for k, (label, sh) in parts.items():
        o = doc.addObject("Part::Feature", "MHZ78_" + k); grp.addObject(o)
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
    # the Zero on the bed edge
    sh = {k: m.shapes[o.Name] for k, o in made.items()}
    for k, o in made.items():
        p.check(sh[k].isValid() and len(sh[k].Solids) == 1, f"{o.Label[:44]}: one valid solid, {sh[k].Volume:.0f} mm3")
    p.check(not binfo.get("failed"), f"bracket chamfered: {binfo['bottom']} bottom + {binfo['top']} top edges, "
                                    f"{len(binfo['reduced'])} reduced, failed {binfo.get('failed')}")
    fb, hb, pb, sb = box[fr[0]], box[heater[0]], box[plate[0]], box[pei[0]]
    d = sh["bracket"].distToShape(m.shapes[fr[0]])[0]
    p.check(d < TOL, f"the bracket's back plate sits on the bed 2020's face (gap {d:.4f})")
    p.check(hb.ZMin - sh["bracket"].BoundBox.ZMax >= HEATER_GAP - TOL,
            f"bracket top Z {sh['bracket'].BoundBox.ZMax:.2f}: {hb.ZMin - sh['bracket'].BoundBox.ZMax:.2f} under the heater pad")
    pr_b = sh["probe"].BoundBox
    p.check(abs(pr_b.ZMax - pei_top - BALL_ABOVE_PEI) < TOL, f"ball top Z {pr_b.ZMax:.2f}: {pr_b.ZMax - pei_top:.2f} above the PEI "
                                                           f"(Z {pei_top:.2f}; want {BALL_ABOVE_PEI})")
    high = [k for k in ("body", "switch", "bracket") if sh[k].BoundBox.ZMax > pei_top - TOL]
    p.check(not high, f"only the probe stands above the PEI ({high})")
    edge = min(pb.YMin, sb.YMin)
    gap_b, gap_ball = edge - (zy + BUSH_D / 2), edge - (zy + BALL_D / 2)
    p.check(gap_b >= 0.5 - TOL and gap_ball >= 2 - TOL,
            f"in front of the plate and sheet (Y {edge:.2f}): bushing {gap_b:.2f} (>= 0.5), ball {gap_ball:.2f} (>= 2)")
    sys.path.insert(0, os.path.join(_REPO, "cad/studies"))
    import mellow_edge_reach as mer
    limit = mer.both_heads(json.load(open(mer.DATA)))
    rmg = mer.margin(limit, BALL_PX, BALL_PY, OVERTRAVEL)
    p.check(rmg >= 0, f"both heads reach all 4 sides of the ball at printer ({BALL_PX:g}, {BALL_PY:g}) with {OVERTRAVEL:g} "
                      f"overtravel: margin {rmg:.2f} (front_reach_front17.json)")
    # over the bed's Z travel (BED_LOWEST_DZ .. +5, the plate past the nozzle) the new parts hit nothing fixed
    allb = FreeCAD.BoundBox()
    for s_ in sh.values(): allb.add(s_.BoundBox)
    sweep = Part.makeBox(allb.XLength, allb.YLength, allb.ZLength - BED_LOWEST_DZ + 5.0,
                         V(allb.XMin, allb.YMin, allb.ZMin + BED_LOWEST_DZ))
    bedside = lambda b: BED_Z[0] <= b.ZMin <= BED_Z[1] and b.ZMax <= BED_Z[1]
    mine0 = {o.Name for o in made.values()}
    zhits = [o.Label[:40] for o in m.leaves if o.Name not in mine0 and "envelope" not in o.Label
             and not bedside(m.boxes[o.Name]) and m.boxes[o.Name].intersect(sweep.BoundBox)
             and sweep.common(m.shapes[o.Name]).Volume > TOL]
    p.check(not zhits, f"over the bed's Z travel (dZ {BED_LOWEST_DZ:g} .. +5) the Zero's swept box "
                       f"X {allb.XMin:.0f}..{allb.XMax:.0f} Y {allb.YMin:.0f}..{allb.YMax:.0f} hits no fixed part: {zhits[:8]}")
    p.check(all(bedside(s_.BoundBox) for s_ in sh.values()), "every new part is bed-side by the motion code's Z band")
    cmap = colours.load(f"{_REPO}/cad/render/colours.json")
    roles = {k: colours.role_of(cmap, o.Label, grp.Label, "Default") for k, o in made.items()}
    p.check(roles == dict(body="brushed_aluminium", probe="brushed_steel", switch="black_plastic", bracket="printed"),
            f"roles {roles}")
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
                                            f"the Zero: {zero_hits[:4]})")
    pv = os.environ.get("LITE78_PREVIEW")
    if pv:
        role = lambda o: colours.role_of(cmap, o.Label, "", "Default")
        near = lambda bb, zone: bb.intersect(zone)
        # 1. the Zero on the bed edge with what's round it (the bed at the model pose)
        z1 = FreeCAD.BoundBox(allb.XMin - 120, allb.YMin - 60, allb.ZMin - 30, allb.XMax + 120, allb.YMax + 90, allb.ZMax + 60)
        sc1 = [(o.Label, m.shapes[o.Name], role(o)) for o in m.leaves if o.Name not in mine and near(m.boxes[o.Name], z1)
               and "envelope" not in o.Label]
        sc1 += [(o.Label, sh[k], role(o)) for k, o in made.items()]
        # 1b. side-on (owner, 2026-11-23): the bed raised to the calibration pose (the docked heads' nozzle tips at the
        # ball's top less lower_z 0.2; the tip Z from sweep_toolhead.log), every part in an X slab round the Zero
        import re as _re
        tips = [float(z) for z in _re.findall(r"carried: nozzle tip Z ([0-9.]+)",
                                              open(os.path.join(_REPO, "cad/data/logs/sweep_toolhead.log")).read())]
        bed_dz = min(tips) - (sh["probe"].BoundBox.ZMax - 0.2)
        zs = FreeCAD.BoundBox(allb.XMin - 60, -260, allb.ZMin - 40, allb.XMax + 60, allb.YMax + 60, allb.ZMax + bed_dz + 220)
        sc1s = []
        for o in m.leaves:
            b = m.boxes[o.Name]
            if "envelope" in o.Label: continue
            up = o.Name in mine or (BED_Z[0] <= b.ZMin <= BED_Z[1] and b.ZMax <= BED_Z[1])
            t = m.shapes[o.Name]
            if up: t = t.copy(); t.translate(V(0, 0, bed_dz))
            if near(t.BoundBox, zs): sc1s.append((o.Label, t, role(o)))
        p.log(f"preview: side scene, bed +{bed_dz:.2f} (nozzle tips {min(tips):.2f}), {len(sc1s)} parts")
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
        preview(pv, {"zero_edge": sc1, "zero_side": sc1s, "tubes_cables": sc2, "front_before": sc3a, "front_after": sc3b})
        p.log(f"preview STLs in {pv}: {len(sc1)}, {len(sc2)}, {len(sc3a)}, {len(sc3b)} parts")
    p.dump(dict(dy=DY, front=len(front), spliced={lab[n]: v[0] for n, v in spliced.items()}, rail_y0=y0,
                mount_gap=[gap0, gap0 + DY], mellow=dict(ball_printer=[BALL_PX, BALL_PY], ball_model=[zx, zy], ball_top_above_pei=BALL_ABOVE_PEI, reach_margin=rmg),
                collisions=dict(now=len(r1.hits), lite77=len(base_hits), new=new_hits, gone=gone_hits),
                hardware="2 x M3x8 + T-nut (bracket to bed 2020), 2 x M3x25 + nut (Zero to bracket)"))
    return p.finish([(doc, DST)])


if not os.environ.get("LITE78_AS_LIB"): litelib.Pass("lite78_front17").run(main)
