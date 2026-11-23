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
#  - PART B, not written yet: the five Bowden tubes and O2S cables are re-routed from the moved heads
#    (emu_bowden.py, o2s_route.py). Until then a check fails on purpose, so this pass never saves.
# Checks (refuses to save on any): every leaf moved exactly -17, unchanged, spliced, or a removed rail; spliced parts
# valid with their solid count, their front end -17 and their volume + section x 17; rails 490 long, 1.5 mm from each
# mount, valid; no leaf left with an attachment that would undo the move on recompute.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
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
TOL = 1e-3


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


def main(p):
    m = p.open(SRC); doc = m.doc
    par = linkgeo.group_parents(doc.Objects)
    top = {o.Name: (linkgeo.group_path(o, par) + ["", ""])[1] for o in m.leaves}
    box = {o.Name: m.shapes[o.Name].BoundBox for o in m.leaves}
    lab = {o.Name: o.Label for o in m.leaves}
    stay = {n for n, l in lab.items() if l.startswith(STAY) or l in STAY_EXACT}
    rails_old = {n for n, l in lab.items() if l.startswith(RAILS_OLD)}
    front = {n for n in lab if n not in stay and n not in rails_old
             and (box[n].YMax <= FRONT_Y or any(k in top[n] for k in FRONT_GROUPS))}
    belts = {n for n, l in lab.items() if l.startswith(BELTS)}
    cross = {n for n in lab if n not in front | stay | rails_old | belts and box[n].YMin < FRONT_Y}
    tubes = {n for n, l in lab.items() if l.startswith(TUBES)}
    cables = {n for n, l in lab.items() if l.startswith(CABLES)}
    p.log(f"{len(m.leaves)} leaves: {len(front)} move -{DY:g}, {len(cross)} spliced, {len(belts)} belts, "
          f"{len(rails_old)} rail pieces replaced, {len(stay)} stay by name ({sorted(lab[n] for n in stay)})")
    for n in sorted(cross, key=lambda n: lab[n]): p.log(f"   splice: {lab[n]} [{top[n]}] Y {box[n].YMin:.1f}..{box[n].YMax:.1f}")
    p.check(len(rails_old) == 4, f"four old Y rail pieces ({sorted(lab[n] for n in rails_old)})")
    p.check(len(belts) == 2, f"two belts ({len(belts)})")
    att = [lab[n] for n in front | cross | belts
           if getattr(doc.getObject(n), "MapMode", "Deactivated") not in ("Deactivated", None)]
    p.check(not att, f"no moved or spliced leaf is attached (an attachment would undo the move): {att[:5]}")
    # A spliced part that is an App::Link (dupes.py shares one shape between copies) gets its own Part::Feature.
    # A spliced Part::Feature must not be the target of a link that isn't spliced too (its shape would change with it).
    links = [o for o in m.leaves if o.TypeId == "App::Link"]
    tgt_of = {o.Name: linkgeo.link_target(o).Name for o in links}
    # links that share a spliced part's shape but don't change (e.g. the back felt liners, copies of the roof liners)
    # get their own Part::Feature with their current geometry first
    keep = sorted(l for l, t in tgt_of.items() if t in cross | belts and l not in cross | belts)
    p.log(f"   {len(keep)} unchanged links share a spliced shape, so they get their own copy first: "
          f"{sorted(lab[l] for l in keep)}")
    p.log(f"   {sum(1 for n in cross | belts if n in tgt_of)} spliced parts are links: each becomes its own Part::Feature")
    if p.errs: return p.finish([])
    mounts = {k: [o for o in m.leaves if o.Label.startswith(k)] for k in (FRONT_MOUNT, REAR_MOUNT)}
    vols0 = {n: m.shapes[n].Volume for n in cross | belts}
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
    doc.recompute()
    m.refresh()
    # ---- after
    now = {o.Name: m.shapes[o.Name].BoundBox for o in m.leaves}
    for old, new in renamed.items(): now[old] = now[new]; m.shapes[old] = m.shapes[new]
    def same(a, b, dy=0.0):
        return all(abs(x - y) <= TOL for x, y in zip((a.XMin, a.YMin + dy, a.ZMin, a.XMax, a.YMax + dy, a.ZMax),
                                                      (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
    bad_move = [lab[n] for n in front if n not in now or not same(box[n], now[n], -DY)]
    bad_stay = [lab[n] for n in lab if n not in front | cross | belts | rails_old and (n not in now or not same(box[n], now[n]))]
    p.check(not bad_move, f"{len(front)} front leaves moved exactly -{DY:g} ({len(bad_move)} not: {bad_move[:5]})")
    p.check(not bad_stay, f"every other leaf unchanged ({len(bad_stay)} changed: {bad_stay[:5]})")
    for n, (ys, area, nsol) in spliced.items():
        s = m.shapes[n]; b = s.BoundBox; want = vols0[n] + area * DY
        ok = (s.isValid() and len(s.Solids) == nsol and abs(b.YMin - (box[n].YMin - DY)) < TOL
              and abs(b.YMax - box[n].YMax) < TOL and abs(s.Volume - want) <= max(1.0, 1e-5 * want))
        p.check(ok, f"spliced {lab[n]} at Y {ys:g}: Y {b.YMin:.2f}..{b.YMax:.2f} (was {box[n].YMin:.2f}..{box[n].YMax:.2f}), "
                    f"solids {len(s.Solids)}/{nsol}, valid {s.isValid()}, vol {s.Volume:.0f} (want {want:.0f})")
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
    p.log(f"left for part B: {len(tubes)} Bowden tubes ({sorted(lab[n] for n in tubes)}) moved with their heads, "
          f"{len(cables)} O2S cables unchanged: both need re-routing to the moved heads")
    p.check(False, "PART B: Bowden tubes and O2S cables re-routed (not written yet; this pass must not save)")
    p.dump(dict(dy=DY, front=len(front), spliced={lab[n]: v[0] for n, v in spliced.items()}, rail_y0=y0,
                mount_gap=[gap0, gap0 + DY]))
    return p.finish([(doc, DST)])


if not os.environ.get("LITE78_AS_LIB"): litelib.Pass("lite78_front17").run(main)
