# GUI pass: vt350-lite-9.FCStd -> vt350-lite-10.FCStd   (headless = dry run, never saves)
# Taller Z inside the same 740 mm frame. lite-9's bed could rise only 14.8 mm (Z blocks hit the 300 mm rail ends), so
# at the top of travel the plate was still 45 mm under the nozzle. Fix:
#  1) Raise the gantry and everything on it by DZ = 50: gantry bars, Monolith stations + beam + Y rails, X rail and
#     carriage, MadMax carriage, belts, X endstop, docks, docked heads, dock crossbar. The frame itself is unchanged.
#     The printed X endstop (from the printed gantry, like lite-7's Y endstop) is REMOVED: raised 50 mm it sweeps into the
#     left Z rail, its stop and the Z post. The user is printing new endstops.
#  2) Z posts (old front verticals) and the rear 2020 vertical under the gantry: +50 at the top (they end at the gantry).
#  3) Z rails 300 -> 400 (+100 at the top, section between holes). Rail stops moved onto the new rail tops.
#  4) Z lead screws 300 -> 400 (rods +100 at the top): the 400 integrated-leadscrew motors, uncut.
#  5) Bowden tubes regenerated from the raised inlets: lite-5's route (exit Y 460 / Z 690, 45 deg to the rear) with
#     its handles, and the handle pair that gives the largest bend radius while staying inside the frame top.
# Reports: Z travel (both ends, each limit named), max print height, the 300 mm lead screw option, the gantry swept
# over its whole Y travel against lead screw tops / rail stops / Z posts, tube clearance, and new collisions vs lite-9.
# Checks: extended parts valid with exact volumes, moved parts moved exactly, everything else unchanged.
import FreeCAD, Part, sys, os, time, math, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-9.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-10.FCStd"
DRY = not FreeCAD.GuiUp
DZ = 50.0
T_UP = V(0, 0, DZ)
RAIL_EXT, SCREW_EXT = 100.0, 100.0
REMOVE_GROUPS = ["_1_X_endstop v1"]
MOVE_GROUPS = ["Monolith gantry (LDO milled, 2WD VT 9mm)", "Gantry assembly", "Carriage (1)", "_11_9mm_2WD_belts_FT_FT v1",
               "Left Dock", "Right Dock", "Left Toolhead", "Right Toolhead"]
FRAME_GANTRY = "Gantry"                               # frame sub-group: the 2 side 2040s + rear 2020 of the gantry
MOVE_LEAVES = ["MGN_12_H_CARRAGE v1", "Dock crossbar (placeholder, 2040)"]
MOVE_PREFIXES = ["MGN9-400mm Y rail", "MGN9 Y rail front extension"]   # lite-9 put these at the root, not in the Monolith group
FIXED_LEAVES = ["case display 7 hdmi BTT v1.2 v1"]       # BTT Pad 7 on the side of the frame: not on the gantry
CHAIN = "10x11 Chain Z"                                # its carriage end moves with the bed; links aren't posed: left out
FIXED_GROUPS = ["Verticals", "Horizontals", "Door (1) (1)", "Electronics", "Z Assembly (1)", "Bed frame"]
Z_RAILS = {"Left": "SOLID029", "Rear": "SOLID034", "Right": "SOLID037"}
RAIL_STOPS = {"Left": "rail_stop (1)", "Rear": "rail_stop", "Right": "rail_stop (2)"}
RODS = {"Left": "Leadscrew (rod)", "Right": "Leadscrew001 (rod)", "Rear": "Leadscrew002 (rod)"}
NUTS = {"Left": "Leadscrew Nut", "Right": "Leadscrew Nut002", "Rear": "Leadscrew Nut001"}
BLOCK_GROUPS = {"Left": "MGN9H (2)", "Right": "MGN9H (4)", "Rear": "MGN9H (3)"}
BED_GROUPS = ["Z_Bed_Left", "Z_Bed_Right", "Z_Bed_Rear", "Z_Carriage_Left", "Z_Carriage_Right",
              "Z_Carriage_Rear_2-hole (IGUS)", "Z_Carriage_Rear_3-Hole (Generic)", "MGN9H (2)", "MGN9H (4)",
              "Bed frame", "kinematic bed mount v1"]
PLATE = "Universal Build Plate 350 v1"
NOZZLES = ["E3D v6 HotEnd - Nozzle", "E3D v6 HotEnd - Nozzle001"]
SWEEP_GROUPS = ["XY right: _XY_right", "XY left: _XY_left", "Gantry assembly", "Carriage (1)"]
SWEEP_LEAVES = ["MGN_12_H_CARRAGE v1", "Carbonara CF X beam 20x20 430"]
Y_TRAVEL = (-277.19, 145.43)                           # gantry dY limits from lite9_rails.log (unchanged by a Z shift)
OD = 4.12
EXIT_Y, EXIT_Z, EXIT_DIR, HANDLES, BEYOND = 460.0, 690.0, V(0, 1, 1).normalize(), (240.0, 160.0), 30.0
INLETS = {"Left": "4mm Bowden Coupler v1 (1)", "Right": "4mm Bowden Coupler v1 (1) (1)"}
FRAME_TOP_Z = 650.0                                   # underside of the top frame bars

os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite10_ztravel.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
_BOX = {}
def gbox(o):
    """tight global bounding box, cached per object and placement (cache cleared after every move)"""
    k = (o.Name, tuple(o.getGlobalPlacement().toMatrix().A))
    if k not in _BOX:
        s = gshape(o)
        try: _BOX[k] = s.optimalBoundingBox(True, False)
        except Exception: _BOX[k] = s.BoundBox
    return _BOX[k]
def parent_of(o):
    return next((x for x in o.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))
                 and o in getattr(x, 'Group', [])), None)
def ancestors(o):
    r = []; p = parent_of(o)
    while p is not None: r.append(p); p = parent_of(p)
    return r
def container_global(o):
    for p in ancestors(o):
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
    return FreeCAD.Placement()
def descendants(g):
    out = []
    for c in getattr(g, 'Group', []):
        out.append(c); out += descendants(c)
    return out
def is_leaf(o):
    return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids and o.TypeId != 'App::Origin'
def shifted(b, v):
    return FreeCAD.BoundBox(b.XMin + v.x, b.YMin + v.y, b.ZMin + v.z, b.XMax + v.x, b.YMax + v.y, b.ZMax + v.z)
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax),
                                                    (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
def translate_global(o, T):
    par_g = container_global(o)
    g = o.getGlobalPlacement()
    o.Placement = par_g.inverse().multiply(FreeCAD.Placement(T, FreeCAD.Rotation())).multiply(g)
def copy_view(src, dst):
    if src.ViewObject is None or dst.ViewObject is None: return
    for prop in ('ShapeAppearance', 'ShapeColor', 'DiffuseColor', 'LineColor', 'Transparency', 'Visibility'):
        try: setattr(dst.ViewObject, prop, getattr(src.ViewObject, prop))
        except Exception: pass
def replace_shape(o, new_global, label=None):
    """new Part::Feature in o's place (same parent, view), o removed; returns the new object"""
    par = parent_of(o); Cg = container_global(o)
    loc = new_global.copy(); loc.Placement = Cg.inverse().multiply(loc.Placement)
    n = doc.addObject('Part::Feature', 'Feature'); n.Shape = loc
    if par is not None: par.addObject(n)
    copy_view(o, n); lab = label or o.Label
    doc.removeObject(o.Name); n.Label = lab
    return n
def zsection(s, z):
    big = 5000
    above = s.common(Part.makeBox(big, big, s.BoundBox.ZMax - z + 1, V(-big/2, -big/2, z)))
    fs = [f for f in above.Faces if isinstance(f.Surface, Part.Plane) and abs(abs(f.normalAt(0, 0).z) - 1) < 1e-6
          and abs(f.CenterOfMass.z - z) < 1e-6]
    return above, fs
def extend_top(s, dz, start_below=3.0, probe=7.0, step=1.0, span=200.0):
    """lengthen a Z-running part by dz just below its top end: cut at the first clean section (equal area at z and
    z - probe, so no hole crosses), lift the top piece by dz, fill with the section extruded. Returns (shape, z)."""
    b = s.BoundBox; z = b.ZMax - start_below
    while z > b.ZMax - span:
        _, f1 = zsection(s, z); _, f2 = zsection(s, z - probe)
        a1 = sum(f.Area for f in f1); a2 = sum(f.Area for f in f2)
        if f1 and a1 > 0 and abs(a1 - a2) < 1e-6 * max(a1, 1):
            big = 5000
            lower = s.common(Part.makeBox(big, big, z - b.ZMin + 1, V(-big/2, -big/2, b.ZMin - 1)))
            upper, _ = zsection(s, z); upper = upper.translated(V(0, 0, dz))
            fill = Part.makeCompound([f.extrude(V(0, 0, dz)) for f in f1])
            out = lower.fuse([fill, upper]).removeSplitter()
            if len(out.Solids) == 1: out = out.Solids[0]
            return out, z, a1
        z -= step
    raise RuntimeError("no clean section found")
def one(label):
    c = doc.getObjectsByLabel(label)
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {label!r}")
    return c[0]
def leaves_under(o):
    return [x for x in ([o] + descendants(o)) if is_leaf(x)]
def boxes_of(objs):
    b = FreeCAD.BoundBox()
    for o in objs: b.add(gbox(o))
    return b
HW = ('T-nut', 'SHCS', 'BHCS', 'Screw', 'Washer', 'washer', 'shim', 'Nut', 'Insert', 'pin', 'Dowel')
def is_hw(lab): return any(k in lab for k in HW)
def overlaps(objs_a, objs_all, skip=lambda a, b: False, shift=None):
    """{(a.Name, b.Name): mm3} for overlaps > 1 mm3; shift: {name: V} applied to those objects' shapes"""
    shift = shift or {}
    def sh(o):
        s = gshape(o)
        if o.Name in shift: s.translate(shift[o.Name])
        return s
    boxes = {o.Name: shifted(gbox(o), shift.get(o.Name, V())) for o in list(objs_a) + list(objs_all)}
    cache = {}; out = {}
    for a in objs_a:
        for b in objs_all:
            if a.Name == b.Name or skip(a, b) or (b.Name, a.Name) in out or (a.Name, b.Name) in out: continue
            if not boxes[a.Name].intersect(boxes[b.Name]): continue
            try:
                sa = cache.setdefault(a.Name, sh(a)); sb = cache.setdefault(b.Name, sh(b))
                v = sa.common(sb).Volume
            except Exception: continue
            if v > 1.0: out[(a.Name, b.Name)] = v
    return out

try:
    errs, notes = [], []
    doc = FreeCAD.openDocument(SRC)
    log("opened", SRC, len(doc.Objects))
    leaves0 = [o for o in doc.Objects if is_leaf(o)]
    before = {o.Name: gbox(o) for o in leaves0}
    label0 = {o.Name: o.Label for o in leaves0}
    # ---------- classify what moves up ----------
    move = {}
    for gl in MOVE_GROUPS:
        for x in leaves_under(one(gl)): move[x.Name] = x
    fg = [g for g in doc.getObjectsByLabel(FRAME_GANTRY) if parent_of(g) is not None and 'Frame' in parent_of(g).Label]
    if len(fg) != 1: raise RuntimeError(f"frame gantry group: {len(fg)}")
    for x in leaves_under(fg[0]): move[x.Name] = x
    for l in MOVE_LEAVES: x = one(l); move[x.Name] = x
    for o in leaves0:
        if any(o.Label.startswith(p) for p in MOVE_PREFIXES): move[o.Name] = o
    removed = {}
    for gl in REMOVE_GROUPS:
        g = one(gl); ls = leaves_under(g)
        for x in ls: removed[x.Name] = x.Label; move.pop(x.Name, None)
        log(f"removing {gl} ({len(ls)} solids): {sorted({x.Label for x in ls})}")
    tubes0 = [o for o in leaves0 if o.Label.startswith('Bowden ')]
    for t in tubes0: move.pop(t.Name, None)
    fixed_names = set()
    for gl in FIXED_GROUPS:
        for g in doc.getObjectsByLabel(gl):
            for x in leaves_under(g): fixed_names.add(x.Name)
    for nm in move: fixed_names.discard(nm)
    tube_names = {t.Name for t in tubes0}
    unclassified = [o for o in leaves0 if before[o.Name].ZMin >= 325 and o.Name not in move and o.Name not in fixed_names
                    and o.Name not in tube_names and o.Name not in removed]
    # loose frame hardware: bolts/washers touching a gantry bar go up with it; ones at the top frame bars stay
    gbars = [gbox(x) for x in leaves_under(fg[0])]
    def touches_gantry_bar(o):
        b = gbox(o); e = FreeCAD.BoundBox(b.XMin - 0.5, b.YMin - 0.5, b.ZMin - 0.5, b.XMax + 0.5, b.YMax + 0.5, b.ZMax + 0.5)
        return any(e.intersect(g) for g in gbars)
    up_hw = [o for o in unclassified if is_hw(o.Label) and touches_gantry_bar(o)]
    top_hw = [o for o in unclassified if o not in up_hw and before[o.Name].ZMin >= 600]
    for o in up_hw: move[o.Name] = o
    for o in top_hw: fixed_names.add(o.Name)
    for l in FIXED_LEAVES: fixed_names.add(one(l).Name)
    rest = [o for o in unclassified if o not in up_hw and o not in top_hw and o.Name not in fixed_names]
    grew = True
    while grew:                                       # washers etc. touching a bolt that moves, move with it
        grew = False
        mv_hw = [gbox(m) for m in move.values() if is_hw(m.Label)]
        for o in list(rest):
            b = gbox(o); e = FreeCAD.BoundBox(b.XMin - 0.3, b.YMin - 0.3, b.ZMin - 0.3, b.XMax + 0.3, b.YMax + 0.3, b.ZMax + 0.3)
            if is_hw(o.Label) and any(e.intersect(m) for m in mv_hw): move[o.Name] = o; up_hw.append(o); rest.remove(o); grew = True
    log(f"loose frame hardware at gantry level: {len(up_hw)} touch a gantry bar (moved up with it), {len(top_hw)} at the top frame bars (fixed)")
    unclassified = [o for o in unclassified if o not in up_hw and o not in top_hw and o.Name not in fixed_names]
    log(f"   after following bolts: {len(up_hw)} loose hardware parts move up")
    for o in unclassified[:60]:
        b = before[o.Name]; log(f"   unclassified: {o.Label} [{parent_of(o).Label if parent_of(o) else ''}] X {b.XMin:.1f}..{b.XMax:.1f} Y {b.YMin:.1f}..{b.YMax:.1f} Z {b.ZMin:.1f}..{b.ZMax:.1f}")
    log(f"moving up {DZ:.0f}: {len(move)} solids; bowden tubes regenerated: {len(tubes0)}")
    if unclassified:
        errs.append(f"{len(unclassified)} solids at gantry level are neither moved nor fixed: " +
                    ", ".join(sorted({o.Label for o in unclassified})[:40]))
        log("UNCLASSIFIED: " + errs[-1])
    # ---------- collision baseline (lite-9 positions): moved/changed parts vs everything ----------
    changed_labels = list(Z_RAILS.values()) + list(RODS.values())
    posts = [o for o in leaves0 if 'Z post' in o.Label]
    rear_v = [o for o in leaves0 if o.Name in fixed_names and '2020' in o.Label and abs(before[o.Name].ZMax - 370) < 2.5
              and before[o.Name].ZLength > 300]
    log(f"Z posts: {[o.Label for o in posts]}; rear vertical under the gantry: {[(o.Label, round(before[o.Name].ZMin,1), round(before[o.Name].ZMax,1)) for o in rear_v]}")
    if len(posts) != 2 or len(rear_v) != 1: errs.append(f"expected 2 Z posts and 1 rear 2020 vertical, got {len(posts)}, {len(rear_v)}")
    stop_leaves = {k: leaves_under(one(v)) for k, v in RAIL_STOPS.items()}
    focus0 = list(move.values()) + [one(l) for l in changed_labels] + posts + rear_v + [x for v in stop_leaves.values() for x in v]
    both_moved = lambda a, b: a.Name in move and b.Name in move
    base = overlaps(focus0, leaves0, skip=lambda a, b: both_moved(a, b) or a.Name in tube_names or b.Name in tube_names
                    or a.Name in removed or b.Name in removed)
    # remove the printed X endstop
    for gl in REMOVE_GROUPS:
        g = one(gl); todo = [g] + descendants(g)
        for x in reversed(todo):
            try: doc.removeObject(x.Name)
            except Exception: pass
    log(f"baseline overlaps in lite-9 among the parts this pass touches: {len(base)}")
    # ---------- 1) raise the gantry ----------
    for o in move.values(): translate_global(o, T_UP)
    # ---------- 2) Z posts + rear vertical: +DZ at the top ----------
    ext = {}
    for o in posts + rear_v:
        s0 = gshape(o); s1, zc, area = extend_top(s0, DZ)
        ok = s1.isValid() and abs(s1.Volume - (s0.Volume + area * DZ)) < 0.5 and abs(s1.BoundBox.ZMax - (s0.BoundBox.ZMax + DZ)) < 1e-3
        log(f"{o.Label}: Z {s0.BoundBox.ZMin:.1f}..{s0.BoundBox.ZMax:.1f} -> ..{s1.BoundBox.ZMax:.1f} (cut at Z {zc:.1f}, section {area:.1f} mm2), valid {s1.isValid()}, volume ok {ok}")
        if not ok: errs.append(f"{o.Label}: extension failed checks")
        lab = o.Label; n = replace_shape(o, s1); ext[n.Name] = (lab, s0.BoundBox, s1.BoundBox)
    # ---------- 3) Z rails 300 -> 400, stops onto the new tops ----------
    rail_top = {}; rail_bot = {}; rail_screw_shift = {}
    for k, l in Z_RAILS.items():
        o = one(l); s0 = gshape(o); s1, zc, area = extend_top(s0, RAIL_EXT, start_below=5.0)
        ok = s1.isValid() and len(s1.Solids) == 1 and abs(s1.Volume - (s0.Volume + area * RAIL_EXT)) < 0.5
        log(f"Z rail {k}: Z {s0.BoundBox.ZMin:.1f}..{s0.BoundBox.ZMax:.1f} -> ..{s1.BoundBox.ZMax:.1f} (MGN9 400; cut at Z {zc:.1f}), valid {s1.isValid()}, volume ok {ok}")
        if not ok: errs.append(f"Z rail {k}: failed checks")
        rail_top[k] = s1.BoundBox.ZMax; rail_bot[k] = s1.BoundBox.ZMin
        rb0 = s0.BoundBox
        for x in doc.Objects:
            if not is_leaf(x) or not is_hw(x.Label) or x.Name in move or x.Name in rail_screw_shift: continue
            xb = gbox(x)
            if xb.ZMin > zc and rb0.XMin - 0.5 <= xb.XMin and xb.XMax <= rb0.XMax + 0.5 and rb0.YMin - 6 <= xb.YMin and xb.YMax <= rb0.YMax + 6 and xb.ZMax <= rb0.ZMax + 0.5:
                translate_global(x, V(0, 0, RAIL_EXT)); rail_screw_shift[x.Name] = RAIL_EXT
                log(f"   {x.Label}: in the rail's top piece above the cut, moved +{RAIL_EXT:.0f} with it")
        par = parent_of(o); n = replace_shape(o, s1); ext[n.Name] = (l, s0.BoundBox, s1.BoundBox)
        if par is not None and '300mm' in par.Label: par.Label = par.Label.replace('300mm', '400mm')
    stop_shift = {}
    for k, ls in stop_leaves.items():
        b = boxes_of(ls); d = rail_top[k] - b.ZMin
        log(f"rail stop {k}: Z {b.ZMin:.1f}..{b.ZMax:.1f} -> on the rail top {rail_top[k]:.1f} (moved {d:+.1f}"
            f"{'; it was floating ' + format(b.ZMin - (rail_top[k] - RAIL_EXT), '.1f') + ' mm above the 300 rail' if abs(b.ZMin - (rail_top[k] - RAIL_EXT)) > 0.05 else ''})")
        b0 = {x.Name: gbox(x) for x in ls}
        for x in ls:                                  # bodies first; attached fasteners follow on recompute
            if not is_hw(x.Label): translate_global(x, V(0, 0, d))
            stop_shift[x.Name] = d
        doc.recompute(); _BOX.clear()
        for x in ls:
            if is_hw(x.Label) and not close(gbox(x), shifted(b0[x.Name], V(0, 0, d))): translate_global(x, V(0, 0, d))
    # ---------- 4) lead screws 300 -> 400 ----------
    screw_top = {}
    for k, l in RODS.items():
        o = one(l); s0 = gshape(o); s1, zc, area = extend_top(s0, SCREW_EXT, start_below=2.0)
        ok = s1.isValid() and abs(s1.Volume - (s0.Volume + area * SCREW_EXT)) < 0.5
        log(f"lead screw {k}: Z {s0.BoundBox.ZMin:.1f}..{s0.BoundBox.ZMax:.1f} -> ..{s1.BoundBox.ZMax:.1f}, valid {s1.isValid()}, volume ok {ok}")
        if not ok: errs.append(f"lead screw {k}: failed checks")
        screw_top[k] = s1.BoundBox.ZMax
        par = parent_of(o); n = replace_shape(o, s1); ext[n.Name] = (l, s0.BoundBox, s1.BoundBox)
        for p in [par] + ancestors(par) if par is not None else []:
            if 'Leadscrew 300mm' in p.Label: p.Label = p.Label.replace('300mm', '400mm')
    doc.recompute()
    # ---------- Z travel ----------
    bed = {}
    for gl in BED_GROUPS:
        for g in doc.getObjectsByLabel(gl):
            for x in leaves_under(g): bed[x.Name] = x
    plate = one(PLATE); bed[plate.Name] = plate
    for x in leaves_under(one("Z_Bed_Rear")): bed[x.Name] = x
    chain = {x.Name for x in leaves_under(one(CHAIN))}
    screw_names = {o.Name for o in doc.Objects if is_leaf(o) and o.Label in RODS.values()}
    cand = [o for o in doc.Objects if is_leaf(o) and o.Name not in bed and o.Name not in move and o.Name not in chain
            and is_hw(o.Label) and o.Name not in screw_names]
    att = overlaps(cand, list(bed.values()))
    attached = sorted({doc.getObject(a).Label for a, b in att})
    for a, b in att: bed[a] = doc.getObject(a)
    loose_parents = ("4040-350 VT Frame v12", "4040-350x350x250 Voron Trident v4 v33")
    frame_beds = [gbox(x) for x in leaves_under(one("Bed frame"))] + [gbox(plate)]
    for o in cand:
        if o.Name in bed or parent_of(o) is None or parent_of(o).Label not in loose_parents: continue
        b = gbox(o)
        if any(b.intersect(fb) for fb in frame_beds): bed[o.Name] = o; attached.append(o.Label + " (in the bed frame)")
    log(f"hardware sitting in bed parts at the model pose, moved with the bed: {len(attached)} {attached}")
    pt = gbox(plate).ZMax
    noz = min(gbox(one(n)).ZMin for n in NOZZLES)
    log(f"plate top Z {pt:.2f} (model pose); nozzle tip Z {noz:.2f} after the raise; gap {noz - pt:.2f}")
    up = {}; down = {}
    for k in Z_RAILS:
        bb = boxes_of(leaves_under(one(BLOCK_GROUPS[k]))) if k != "Rear" else boxes_of(leaves_under(one(BLOCK_GROUPS[k])))
        up[f"{k} Z block reaches its rail stop"] = rail_top[k] - bb.ZMax
        down[f"{k} Z block reaches its rail's bottom end"] = rail_bot[k] - bb.ZMin
        nb = gbox(one(NUTS[k]))
        up[f"{k} nut top reaches its 400 screw's top"] = screw_top[k] - nb.ZMax
        up[f"(300 screw) {k} nut top reaches the screw's top"] = (screw_top[k] - SCREW_EXT) - nb.ZMax
    up["plate reaches the nozzle"] = noz - pt
    fixed_now = [o for o in doc.Objects if is_leaf(o) and o.Name not in bed and o.Name not in move and not o.Label.startswith('Bowden ')
                 and o.Name not in chain]
    nut_rod = {tuple(sorted((one(NUTS[k]).Name, one(RODS[k]).Name))) for k in RODS}
    for m in bed.values():
        mb = gbox(m)
        for f in fixed_now:
            fb = gbox(f)
            if is_hw(f.Label): continue                   # fixed screws: the boolean check at the bottom pose covers them
            if fb.ZMax <= mb.ZMin + 0.01 and fb.XMin < mb.XMax and mb.XMin < fb.XMax and fb.YMin < mb.YMax and mb.YMin < fb.YMax:
                key = f"{m.Label} lands on {f.Label}"
                d = fb.ZMax - mb.ZMin
                if d > max(down.values(), default=-1e9) - 50: down[key] = max(down.get(key, -1e9), d)
    real_up = {k: v for k, v in up.items() if not k.startswith('(300')}
    up_k = min(real_up, key=real_up.get); dn_k = max(down, key=down.get)
    log("Z travel limits from the model pose (dZ of the bed):")
    for k, v in sorted(up.items(), key=lambda kv: kv[1]): log(f"   up   {v:+8.2f}  {k}")
    for k, v in sorted(down.items(), key=lambda kv: -kv[1])[:8]: log(f"   down {v:+8.2f}  {k}")
    top_d, bot_d = real_up[up_k], down[dn_k]
    log(f"TOP: bed stops at dZ {top_d:+.2f} ({up_k}); BOTTOM: dZ {bot_d:+.2f} ({dn_k}, bounding-box estimate)")
    lowest_pt = pt + bot_d
    log(f"MAX PRINT HEIGHT (nozzle tip to plate top at the bottom of travel): {noz - lowest_pt:.1f} mm "
        f"(plate top at Z {lowest_pt:.1f}); bed reaches the nozzle: {top_d >= noz - pt - 1e-6}")
    s300 = min(v for k, v in up.items() if k.startswith('(300'))
    log(f"300 mm lead screws instead: the bed tops out at dZ {s300:+.2f}, i.e. {noz - pt - s300:.1f} mm under the nozzle (needs the bed raised on its carriages, or a lower gantry)")
    if top_d < noz - pt - 1e-6: errs.append(f"bed cannot reach the nozzle: top dZ {top_d:.2f} < {noz - pt:.2f}")
    # interference at both ends of travel
    for nm, d in (("top (plate at the nozzle)", noz - pt), ("bottom", bot_d)):
        sh = {n: V(0, 0, d) for n in bed}
        ov = overlaps(list(bed.values()), list(bed.values()) + fixed_now + list(move.values()),
                      skip=lambda a, b: (a.Name in bed and b.Name in bed) or tuple(sorted((a.Name, b.Name))) in nut_rod, shift=sh)
        log(f"bed at the {nm}: {len(ov)} overlaps > 1 mm3 with fixed or gantry parts")
        for (a, b), v in sorted(ov.items(), key=lambda kv: -kv[1])[:15]:
            A, B = doc.getObject(a), doc.getObject(b)
            log(f"     {v:8.1f} mm3  {A.Label} [{parent_of(A).Label if parent_of(A) else ''}] x {B.Label} [{parent_of(B).Label if parent_of(B) else ''}]")
    # ---------- gantry sweep over Y travel ----------
    sweep = []
    for gl in SWEEP_GROUPS: sweep += leaves_under(one(gl))
    sweep += [one(l) for l in SWEEP_LEAVES]
    targets = [("lead screw " + k, one_n) for k, one_n in ((k, None) for k in RODS)]
    tgt = []
    for k, l in RODS.items(): tgt += [("lead screw " + k, o) for o in doc.Objects if is_leaf(o) and o.Label == l]
    for k, v in RAIL_STOPS.items(): tgt += [("rail stop " + k, x) for x in leaves_under(one(v))]
    for o in doc.Objects:
        if is_leaf(o) and ('Z post' in o.Label or (o.Name in ext and '2020' in ext[o.Name][0])): tgt.append((o.Label, o))
    for k, l in Z_RAILS.items(): tgt += [("Z rail " + k, o) for o in doc.Objects if is_leaf(o) and o.Label == l]
    clear = {}
    for name, t in tgt:
        tb = gbox(t)
        for s in sweep:
            sb = gbox(s)
            if sb.XMin < tb.XMax and tb.XMin < sb.XMax and sb.YMin + Y_TRAVEL[0] < tb.YMax and tb.YMin < sb.YMax + Y_TRAVEL[1]:
                c = sb.ZMin - tb.ZMax
                if name not in clear or c < clear[name][0]: clear[name] = (c, s.Label)
    log("gantry swept over its full Y travel: smallest vertical clearance above each Z part it passes over")
    for name, (c, lab) in sorted(clear.items(), key=lambda kv: kv[1][0]):
        log(f"   {c:+8.2f} mm  {name}  under {lab}")
        if c < 2.0: errs.append(f"gantry sweep: {name} only {c:.2f} mm under {lab}")
    for name, t in tgt:
        if name not in clear: log(f"   (never under the gantry) {name}")
    # ---------- 5) bowden tubes ----------
    bg = parent_of(tubes0[0]) if tubes0 else None
    old_tube = {t.Label: (t.MinBendRadius.Value if hasattr(t, 'MinBendRadius') else None, t.PathLength.Value if hasattr(t, 'PathLength') else None) for t in tubes0}
    for t in tubes0: doc.removeObject(t.Name)
    def route(P0, a, b):
        P1 = V(P0.x, EXIT_Y, EXIT_Z)
        c = Part.BezierCurve(); c.setPoles([P0, P0 + V(0, 0, a), P1 - EXIT_DIR * b, P1])
        rmin = min(1 / max(c.curvature(i / 400), 1e-12) for i in range(401))
        zmax = max(c.value(i / 200).z for i in range(201))
        return c, P1, rmin, zmax
    tubes = []
    for side, cl in INLETS.items():
        cb_ = gbox(one(cl)); P0 = V((cb_.XMin + cb_.XMax) / 2, (cb_.YMin + cb_.YMax) / 2, cb_.ZMax)
        c0, P1, r0, z0 = route(P0, *HANDLES)
        best = None
        for a in range(20, 301, 5):
            for b in range(20, 301, 5):
                c, _, r, zm = route(P0, float(a), float(b))
                if zm <= EXIT_Z + 1e-6 and (best is None or r > best[0]): best = (r, a, b)
        r1, a1, b1 = best
        c, P1, rmin, _ = route(P0, float(a1), float(b1))
        log(f"tube {side}: inlet Z {P0.z:.1f} (lite-9: {P0.z - DZ:.1f}), rise to the exit {EXIT_Z - P0.z:.1f} mm. lite-9 tube: min bend R "
            f"{old_tube.get('Bowden ' + side, (None,))[0] or float('nan'):.1f}. lite-5 handles {HANDLES}: R {r0:.1f}, top of curve Z {z0:.1f}"
            f"{' (ABOVE the exit)' if z0 > EXIT_Z else ''}. Best handles ({a1}, {b1}): R {r1:.1f}")
        path = Part.Wire([c.toShape(), Part.LineSegment(P1, P1 + EXIT_DIR * BEYOND).toShape()])
        tube = path.makePipeShell([Part.Wire(Part.makeCircle(OD / 2, P0, V(0, 0, 1)))], True, True)
        L = c.length() + BEYOND
        loc = tube.copy(); Cg = container_global(bg) if bg is not None else FreeCAD.Placement()
        loc.Placement = Cg.inverse().multiply(loc.Placement)
        t = doc.addObject('Part::Feature', 'BowdenTube'); t.Shape = loc
        if bg is not None: bg.addObject(t)
        t.Label = f"Bowden {side}"
        for prop, typ, val in (('OD', 'App::PropertyLength', OD), ('Inlet', 'App::PropertyVector', P0),
                               ('ExitPoint', 'App::PropertyVector', P1), ('ExitDir', 'App::PropertyVector', EXIT_DIR),
                               ('HandleInlet', 'App::PropertyLength', float(a1)), ('HandleExit', 'App::PropertyLength', float(b1)),
                               ('Beyond', 'App::PropertyLength', BEYOND), ('MinBendRadius', 'App::PropertyLength', rmin),
                               ('PathLength', 'App::PropertyLength', L)):
            t.addProperty(typ, prop, 'Bowden', 'route parameters (global mm); regenerate by script for other poses'); setattr(t, prop, val)
        if t.ViewObject is not None:
            try: t.ViewObject.ShapeAppearance = (FreeCAD.Material(DiffuseColor=(0.95, 0.95, 0.95), Transparency=0.4),)
            except Exception: pass
        log(f"   Bowden {side}: length {L:.0f} mm, min bend R {rmin:.1f} mm, valid {tube.isValid()}")
        if not tube.isValid() or rmin < 50: errs.append(f"tube {side}: valid={tube.isValid()} R={rmin:.1f}")
        tubes.append(t)
    doc.recompute()
    allnow = [o for o in doc.Objects if is_leaf(o)]
    tov = overlaps(tubes, allnow, skip=lambda a, b: b in tubes or b.Label in INLETS.values())
    log(f"bowden tubes: {len(tov)} overlaps > 1 mm3 with other parts")
    for (a, b), v in sorted(tov.items(), key=lambda kv: -kv[1])[:10]:
        A, B = doc.getObject(a), doc.getObject(b); log(f"     {v:8.1f} mm3  {A.Label} x {B.Label} [{parent_of(B).Label if parent_of(B) else ''}]")
    # ---------- verify ----------
    now = {o.Name: o for o in doc.Objects}
    replaced = {ext[n][0] for n in ext}
    for nm, b in before.items():
        if nm in tube_names or nm in removed: continue
        if label0[nm] in replaced and nm not in now: continue
        if nm not in now: errs.append(f"lost {label0[nm]}"); continue
        exp = shifted(b, T_UP) if nm in move else shifted(b, V(0, 0, stop_shift[nm])) if nm in stop_shift else \
              shifted(b, V(0, 0, rail_screw_shift[nm])) if nm in rail_screw_shift else b
        gb_ = gbox(now[nm])
        if not close(gb_, exp):
            followed = [d for d in set(stop_shift.values()) if close(gb_, shifted(b, V(0, 0, d)))]
            if followed and is_hw(now[nm].Label): log(f"   {now[nm].Label}: attached to a rail stop, followed it {followed[0]:+.0f}")
            else: errs.append(f"{'moved wrongly' if nm in move else 'changed'}: {now[nm].Label} [{parent_of(now[nm]).Label if parent_of(now[nm]) else ''}]"
                              f" expected Z {exp.ZMin:.2f} got {gb_.ZMin:.2f} (dX {gb_.XMin - exp.XMin:+.2f} dY {gb_.YMin - exp.YMin:+.2f}); in stop_shift {nm in stop_shift}, rail-screw {nm in rail_screw_shift}")
    # ---------- new collisions ----------
    focus1 = [now[n] for n in move if n in now] + [now[n] for n in ext] + [now[n] for n in stop_shift if n in now]
    after = overlaps(focus1, allnow, skip=lambda a, b: both_moved(a, b) or a in tubes or b in tubes)
    base = {p: v for p, v in base.items() if p[0] not in removed and p[1] not in removed}
    name_of = {n: ext[n][0] for n in ext}
    def key(p):
        a, b = p
        la = name_of.get(a, now[a].Label if a in now else a); lb = name_of.get(b, now[b].Label if b in now else b)
        return tuple(sorted((la, lb)))
    base_k = {tuple(sorted((label0.get(a, a), label0.get(b, b)))) for a, b in base}
    new = {p: v for p, v in after.items() if key(p) not in base_k}
    log(f"collisions > 1 mm3 among touched parts: {len(after)}; {len(after) - len(new)} already in lite-9; {len(new)} new")
    for (a, b), v in sorted(new.items(), key=lambda kv: -kv[1]):
        A, B = now[a], now[b]
        kind = "hardware" if (is_hw(A.Label) or is_hw(B.Label)) else "PART"
        log(f"   {kind:8} {v:8.1f} mm3  {A.Label} [{parent_of(A).Label if parent_of(A) else ''}] x {B.Label} [{parent_of(B).Label if parent_of(B) else ''}]")
        if kind == "PART": errs.append(f"new collision: {A.Label} x {B.Label} ({v:.1f} mm3)")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
