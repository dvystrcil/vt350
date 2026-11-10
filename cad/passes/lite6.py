# GUI pass: vt350-lite-5-dan.FCStd -> vt350-lite-6.FCStd   (headless = dry run, never saves)
#  1) GO DEEP: +DY (80 mm, from the A4Tv2 + O2S head, #19 AC9 / notes/dock-survey.md) added at the FRONT.
#     Backbone, Z, bed and the rear frame stay. Everything in front of the front verticals' rear face (Y = 10)
#     moves -DY in Y: new front frame plane, door, docks, docked heads. The Y bars that cross Y = 10 are spliced
#     (+DY of their own cross-section, so end taps and drilled holes survive).
#     - The old front 2040 verticals carry the front Z rails, so they STAY as "Z posts", cut between the bottom
#       side bar and the gantry side bar (Z -10..370). New front verticals = copies moved -DY.
#     - The old bottom front 2040 STAYS (Backbone's front holes bolt to it); a copy goes to the new front.
#     - Front dock crossbar (placeholder until the dock design): a copy of the top front 2040 between the new
#       front verticals, just above the docked heads.
#  2) Gantry -> LDO Monolith milled kit, 2WD VT 9 mm (Front 2WD_VT_9mm, Rear VT_9mm NP, XY 2WD_9mm), aligned per
#     station on the printed parts' pulley axes; Y rails -> MGN9 (longest 10 mm step that fits between the mounts);
#     X beam -> Carbonara 20x20 CF tube, 430 mm (section from Monolith's CF_tube_mounting STEP); the XY joints' slot
#     T-nuts + M5x10 into the beam are dropped (a CF tube is through-bolted; that hardware is not modelled).
#     Belts spliced +DY with a copy of their own 80 mm stretch (40 GT2 teeth), so the teeth stay continuous.
#  3) Both Z cable anchors removed.
#  4) Bowden tubes regenerated from the moved Orbiter inlets (same route parameters as lite-5).
#  Verifies everything else is untouched; refuses to save on any failed check.
import FreeCAD, Part, Import, sys, os, time, math, traceback, collections
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
DL = os.environ.get("VT350_DL", "/tmp/claude-1000/-home-dan-Code/49170e9e-d71c-4cd7-8f69-23f113691ee5/scratchpad")
SRC = "/home/dan/Documents/VT350/vt350-lite-5-dan.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-6.FCStd"
DRY = not FreeCAD.GuiUp
DY, YC = 80.0, 10.0
T_FRONT = V(0, -DY, 0)
SPLICE_Y = tuple(float(y) for y in range(30, 460, 5))  # first (front-most) clean section wins: no hole crosses it
Y_BARS = ["4040 (1)", "4040 (1)001", "4040 (1)002", "4040 (1)003", "2040 (3)", "2040 (3)001", "2040 (2) (2)"]
OLD_VERTICALS = {"2040": "R", "2040(Mirror)": "L"}  # drilled bars from lite-5 (Part::Feature 'Bar*')
POST_Z = (-10.0, 370.0)
BOTTOM_FRONT, TOP_FRONT = "2040 (2)", "2040 (2)001"
MOVE_GROUPS = ["Door (1) (1)", "Left Dock", "Right Dock", "Left Toolhead", "Right Toolhead"]
REMOVE_GROUPS = ["Z_Cable_Anchor", "_16_Printed_VT_9mm_rear_motor_mounts_NP_0 v5",
                 "_4_Printed_VT_9mm_front_motorless_mounts_FT v1", "_4_Printed_9mm_AWD_X_axis v2"]
REMOVE_LEAVES = ["MGN12-400mm v1", "MGN12-400mm v001"]          # the two Y rails (MGN12); the X rail v002 stays
BELTS = ["_9mm_2WD_belt_FT_FT", "_9mm_2WD_belt_FT_FT001"]
BELT_SPLICE_Y = tuple(float(y) for y in range(100, 170, 1))   # straight strands between front idlers and joints
# Monolith STEP (printer-centred) -> model, per station. X/Y from the printed parts' pulley axes (front pulley
# (-23.5|-466.5, 4.4) <- (+-171.5, -190.6); rear stepper (-32.5|-457.5, 479.0) <- NP (+-162.5, 184.0)); the FT rear
# file would use the same offset and sit 4 mm further back: in this frame that puts the VC9-RTA tensioners 4 mm into
# the rear gantry 2020 (911 mm3, lite-6 dry run 3), so NP (= what the printed mounts were). Z: gantry bar centre 380.
DXR, DXL, DZ = -195.0, -295.0, 380.0
MONO = [  # (file, offset, station label)
    ("dl-monolith/Front_right_LDO_2WD_VT_9mm.step", V(DXR, 195.0 - DY, DZ), "Front right"),
    ("dl-monolith/Front_left_LDO_2WD_VT_9mm.step",  V(DXL, 195.0 - DY, DZ), "Front left"),
    ("dl-monolith/Rear_right_LDO_VT_9mm_0_NP.step", V(DXR, 295.0, DZ), "Rear right"),
    ("dl-monolith/Rear_left_LDO_VT_9mm_0_NP.step",  V(DXL, 295.0, DZ), "Rear left"),
    ("dl-monolith/XY_right_LDO_2WD_9mm.step",       V(DXR, 260.0, DZ), "XY right"),
    ("dl-monolith/XY_left_LDO_2WD_9mm.step",        V(DXL, 260.0, DZ), "XY left"),
]
# printed-part axes (global, lite-5-dan) to check the alignment against: label -> (x, y) ; after the move for front
AXES = {"Front right": ((-23.5, 4.4 - DY), "D5x36mm pin"), "Front left": ((-466.5, 4.4 - DY), "D5x36mm pin"),
        "Rear right": ((-32.5, 479.0), "_Stepper_shaft_S45R"), "Rear left": ((-457.5, 479.0), "_Stepper_shaft_S45R"),
        "XY right": ((-35.3, 265.0), "_LDO 5 mm shaft"), "XY left": ((-455.3, 265.0), "_LDO 5 mm shaft")}
CF_STEP, CF_LEN = "dl-carbonara/cf_tube_mounting_v6.step", 430.0
OLD_BEAM = dict(x=(-457.8, -27.8), y=(273.5, 293.5))
RAIL_SRC = "SOLID029"                           # front-left Z rail, MGN9, 300 mm along Z: section source
RAIL_X = {"R": -10.0, "L": -480.0}              # gantry side bars' inner faces (rail base)
# bowden (same as lite-5)
OD = 4.12
EXIT_Y, EXIT_Z, EXIT_DIR, HANDLES, BEYOND = 460.0, 690.0, V(0, 1, 1).normalize(), (240.0, 160.0), 30.0
INLETS = {"Left": "4mm Bowden Coupler v1 (1)", "Right": "4mm Bowden Coupler v1 (1) (1)"}

os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite6.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()

def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
def gbox(o):
    s = gshape(o)
    try: return s.optimalBoundingBox(True, False)
    except Exception: return s.BoundBox
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
    return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.TypeId != 'App::Origin'
def copy_view(src, dst):
    if src.ViewObject is None or dst.ViewObject is None: return
    for prop in ('ShapeAppearance', 'ShapeColor', 'DiffuseColor', 'LineColor', 'Transparency', 'Visibility'):
        try: setattr(dst.ViewObject, prop, getattr(src.ViewObject, prop))
        except Exception: pass
def shifted(b, v):
    return FreeCAD.BoundBox(b.XMin + v.x, b.YMin + v.y, b.ZMin + v.z, b.XMax + v.x, b.YMax + v.y, b.ZMax + v.z)
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax),
                                                    (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
def holes_not_along(s, axis):
    """cylindrical faces whose axis is not parallel to `axis` (side holes of a bar running along `axis`)"""
    return sum(1 for f in s.Faces if isinstance(f.Surface, Part.Cylinder) and abs(abs(f.Surface.Axis.dot(axis)) - 1) > 1e-6)
def translate_global(o, T):
    """move an object (leaf or App::Part) by global vector T, keeping its parent"""
    par_g = container_global(o) if not o.isDerivedFrom('App::Part') else \
        next((p.getGlobalPlacement() for p in ancestors(o) if p.isDerivedFrom('App::Part')), FreeCAD.Placement())
    g = o.getGlobalPlacement()
    o.Placement = par_g.inverse().multiply(FreeCAD.Placement(T, FreeCAD.Rotation())).multiply(g)
def add_feature(shape_global, label, parent, view_src=None, name='Feature'):
    loc = shape_global.copy()
    Cg = FreeCAD.Placement()
    if parent is not None:
        Cg = parent.getGlobalPlacement() if parent.isDerivedFrom('App::Part') else container_global(parent)
    loc.Placement = Cg.inverse().multiply(loc.Placement)
    o = doc.addObject('Part::Feature', name); o.Shape = loc
    if parent is not None: parent.addObject(o)
    o.Label = label
    if view_src is not None: copy_view(view_src, o)
    return o
def remove_tree(o):
    names = [x.Name for x in reversed(descendants(o))] + [o.Name]
    n = 0
    for nm in names:
        if doc.getObject(nm) is not None:
            try: doc.removeObject(nm); n += 1
            except Exception: pass
    return n
def section_at(s, ys):
    """planar cut faces of s at Y = ys (from a boolean, robust where slice() returns open wires)"""
    bb = s.BoundBox; big = 5000
    back = s.common(Part.makeBox(big, bb.YMax - ys + 1, big, V(-big/2, ys, -big/2)))
    fs = [f for f in back.Faces if isinstance(f.Surface, Part.Plane) and abs(abs(f.normalAt(0, 0).y) - 1) < 1e-6
          and abs(f.CenterOfMass.y - ys) < 1e-6]
    return back, fs
def splice(s, ys_candidates, dy, probe=7.0):
    """cut shape s at Y = ys, move the Y < ys part by -dy, fill with the cut section extruded by dy.
    A section is clean when it is identical (area) to the one `probe` mm further along: no hole crosses it."""
    bb = s.BoundBox; big = 5000
    for ys in ys_candidates:
        if not (bb.YMin + probe + 1 < ys < bb.YMax - probe - 1): continue
        back, fs = section_at(s, ys)
        _, fs2 = section_at(s, ys + probe)
        a1, a2 = sum(f.Area for f in fs), sum(f.Area for f in fs2)
        if not fs or abs(a1 - a2) > 1e-3: continue
        front = s.common(Part.makeBox(big, ys - bb.YMin + 1, big, V(-big/2, bb.YMin - 1, -big/2)))
        front.translate(V(0, -dy, 0))
        fills = [f.extrude(V(0, -dy, 0)) for f in fs]
        new = back.fuse([front] + fills).removeSplitter()
        return new, ys, a1, len(fs)
    return None, None, None, None

def splice_copy(s, ys_candidates, dy):
    """belts (a compound of strand solids): per solid, cut at Y = ys, move the Y < ys part by -dy and fill with a copy
    of the solid's own stretch ys..ys+dy (dy a multiple of the 2 mm GT2 pitch, so the teeth stay continuous).
    A cut is clean when the section at ys equals the one at ys+dy. Solids behind every candidate cut stay;
    solids in front of them move. Returns (compound, [ys per spliced solid], added volume, n spliced)."""
    big = 5000; out, cuts, added = [], [], 0.0
    lo, hi = min(ys_candidates), max(ys_candidates)
    for so in s.Solids:
        bb = so.BoundBox
        if bb.YMin >= hi: out.append(so); continue
        if bb.YMax <= lo: m = so.copy(); m.translate(V(0, -dy, 0)); out.append(m); continue
        done = False
        for ys in ys_candidates:
            if not (bb.YMin + 1 < ys and ys + dy < bb.YMax - 1): continue
            back, fs = section_at(so, ys); _, fs2 = section_at(so, ys + dy)
            a1, a2 = sum(f.Area for f in fs), sum(f.Area for f in fs2)
            if not fs or abs(a1 - a2) > 1e-3 or len(fs) != len(fs2): continue
            seg = so.common(Part.makeBox(big, dy, big, V(-big/2, ys, -big/2))); seg.translate(V(0, -dy, 0))
            front = so.common(Part.makeBox(big, ys - bb.YMin + 1, big, V(-big/2, bb.YMin - 1, -big/2))); front.translate(V(0, -dy, 0))
            parts = back.Solids + front.Solids + seg.Solids
            new = parts[0].fuse(parts[1:]).removeSplitter()
            out += new.Solids; cuts.append(ys); added += seg.Volume; done = True; break
        if not done: return None, None, None, None
    return Part.makeCompound(out), cuts, added, len(cuts)
HW = ('T-nut', 'SHCS', 'BHCS', 'Screw', 'Washer', 'washer', 'shim', 'Nut', 'Insert', 'pin', 'Dowel')
def is_hw(lab): return any(k in lab for k in HW)
def overlaps(objs_a, objs_all, skip=lambda a, b: False):
    """{(a.Name, b.Name): mm3} for solid overlaps > 1 mm3 (bounding-box prefiltered)"""
    boxes = {o.Name: gbox(o) for o in objs_all}; shapes = {}
    out = {}
    for a in objs_a:
        for b in objs_all:
            if a.Name == b.Name or skip(a, b) or (b.Name, a.Name) in out: continue
            if not boxes[a.Name].intersect(boxes[b.Name]): continue
            try:
                sa = shapes.setdefault(a.Name, gshape(a)); sb = shapes.setdefault(b.Name, gshape(b))
                v = sa.common(sb).Volume
            except Exception: continue
            if v > 1.0: out[(a.Name, b.Name)] = v
    return out

try:
    errs, notes = [], []
    doc = FreeCAD.openDocument(SRC)
    log("opened", SRC, len(doc.Objects), "objects")
    root = next(o for o in doc.Objects if o.TypeId == 'App::Part' and not [p for p in o.InList if p.isDerivedFrom('App::Part')]
                and o.Label.startswith('4040'))
    Rg = root.getGlobalPlacement()
    leaves0 = [o for o in doc.Objects if is_leaf(o)]
    before = {o.Name: gbox(o) for o in leaves0}
    log(f"{len(before)} shapes snapshotted; root = {root.Label}")
    touched, moved = set(), {}            # moved: name -> expected global shift
    origin, shift_of = {}, {}             # new object -> the original it was made from (for the collision baseline)

    def by_label(lab, cond=lambda o: True):
        c = [o for o in doc.getObjectsByLabel(lab) if cond(o)]
        if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {lab!r} (expected 1)")
        return c[0]

    # ---------- 3) + 2a) removals ----------
    removed_names = set()
    for lab in REMOVE_GROUPS:
        g = by_label(lab, lambda o: o.isDerivedFrom('App::Part') or o.isDerivedFrom('App::DocumentObjectGroup'))
        leaves = [x.Name for x in descendants(g) if is_leaf(x)]
        removed_names |= set(leaves)
        n = remove_tree(g); log(f"removed {lab}: {len(leaves)} shapes ({n} objects)")
    for lab in REMOVE_LEAVES:
        o = by_label(lab, is_leaf); removed_names.add(o.Name); doc.removeObject(o.Name); log("removed", lab)
    touched |= removed_names

    # ---------- 1a) classify everything around Y = YC ----------
    group_objs = [by_label(l, lambda o: o.isDerivedFrom('App::Part') or o.isDerivedFrom('App::DocumentObjectGroup'))
                  for l in MOVE_GROUPS]
    in_groups = {x.Name for g in group_objs for x in descendants(g) if is_leaf(x)}
    zasm = {x.Name for x in doc.Objects if is_leaf(x) and any(a.Label == 'Z Assembly (1)' for a in ancestors(x))}
    vert = {lab: by_label(lab, lambda o: o.TypeId == 'Part::Feature' and o.Name.startswith('Bar')) for lab in OLD_VERTICALS}
    bottom = by_label(BOTTOM_FRONT, is_leaf); top = by_label(TOP_FRONT, is_leaf)
    ybars = {lab: by_label(lab, is_leaf) for lab in Y_BARS}
    special = {o.Name for o in list(vert.values()) + [bottom, top] + list(ybars.values())}
    backbone = [o for o in doc.Objects if is_leaf(o) and o.Label.startswith('backbone')]
    stay_span = zasm | {o.Name for o in backbone}
    front_leaves, unclassified = [], []
    for o in doc.Objects:
        if not is_leaf(o) or o.Name not in before or o.Name in in_groups or o.Name in special: continue
        if o.Label.startswith('Bowden '): continue
        b = before[o.Name]
        if b.YMax <= YC + 1e-6:
            if o.Name in zasm: continue                       # Z motor screws / T-nuts: Z stays
            front_leaves.append(o)
        elif b.YMin < YC - 1e-6:                               # spans the plane
            if o.Name in stay_span: continue
            if o.Label.startswith('M5x16-Screw') and parent_of(o) is not None and parent_of(o).Label.startswith('4040-350 VT Frame'):
                front_leaves.append(o)                           # frame joint screws: follow the front plane
            else: unclassified.append(o)
    if unclassified:
        errs.append("unclassified shapes spanning Y=10: " + ", ".join(f"{o.Label} [{'/'.join(a.Label for a in reversed(ancestors(o)))}]" for o in unclassified))
    log(f"front move: {len(front_leaves)} loose shapes + {len(in_groups)} shapes in {len(group_objs)} groups")

    # ---------- baseline collisions (lite-5-dan geometry) for everything that moves or is rebuilt ----------
    replaced = [o for o in list(vert.values()) + [bottom, top] + list(ybars.values()) + [by_label(l, is_leaf) for l in BELTS]]
    movers = [doc.getObject(n) for n in in_groups] + front_leaves
    all0 = [o for o in doc.Objects if is_leaf(o) and o.Shape.Solids]
    base = overlaps([o for o in replaced + movers if o.Shape.Solids], all0)
    base = {tuple(sorted(k)): v for k, v in base.items()}
    log(f"baseline: {len(base)} overlaps > 1 mm3 already in lite-5-dan among moved/rebuilt parts and their neighbours")

    # ---------- 1b) move ----------
    for g in group_objs:
        if g.isDerivedFrom('App::Part'): translate_global(g, T_FRONT)
        else:
            for x in descendants(g):
                if is_leaf(x): translate_global(x, T_FRONT)
    for o in front_leaves: translate_global(o, T_FRONT)
    for n in in_groups | {o.Name for o in front_leaves}: moved[n] = T_FRONT
    translate_global(top, T_FRONT); moved[top.Name] = T_FRONT

    # ---------- 1c) splice the Y bars ----------
    yax = V(0, 1, 0)
    for lab, o in ybars.items():
        s = gshape(o)
        new, ys, area, nf = splice(s, SPLICE_Y, DY)
        if new is None: errs.append(f"{lab}: no clean section at {SPLICE_Y}"); log(f"splice {lab}: NO clean section"); continue
        h0, h1 = holes_not_along(s, yax), holes_not_along(new, yax)
        want = s.Volume + area * DY
        ok = h0 == h1 and len(new.Solids) == 1 and new.isValid() and abs(new.Volume - want) < 1e-3 * want
        log(f"splice {lab} at Y={ys} (section {area:.1f} mm2): y {s.BoundBox.YMin:.1f}..{s.BoundBox.YMax:.1f} -> {new.BoundBox.YMin:.1f}..{new.BoundBox.YMax:.1f}, "
            f"side holes {h0}->{h1}, solids {len(new.Solids)}, valid {new.isValid()}, vol {new.Volume:.0f} (want {want:.0f})")
        if not ok: errs.append(f"splice {lab} failed checks")
        par = parent_of(o)
        n = add_feature(new, lab + " (new)", par, o, 'Bar'); origin[n.Name] = o.Name; touched |= {o.Name, n.Name}
        doc.removeObject(o.Name); n.Label = lab

    # ---------- 1d) front frame plane: Z posts, new verticals, bottom crossbars, dock crossbar ----------
    for lab, side in OLD_VERTICALS.items():
        o = vert[lab]; s = gshape(o); par = parent_of(o); bb = s.BoundBox
        post = s.common(Part.makeBox(200, 200, POST_Z[1] - POST_Z[0], V(bb.XMin - 50, bb.YMin - 50, POST_Z[0]))).removeSplitter()
        p = add_feature(post, f"{lab} Z post ({side})", par, o, 'ZPost')
        newv = s.copy(); newv.translate(T_FRONT)
        nv = add_feature(newv, lab + " (new)", par, o, 'Bar')
        origin[p.Name] = o.Name; origin[nv.Name] = o.Name; shift_of[nv.Name] = T_FRONT
        touched |= {o.Name, p.Name, nv.Name}; doc.removeObject(o.Name); nv.Label = lab
        log(f"{lab}: Z post z {p.Shape.BoundBox.ZMin:.0f}..{p.Shape.BoundBox.ZMax:.0f} (front Z rail stays on it); "
            f"new front vertical y {gbox(nv).YMin:.1f}..{gbox(nv).YMax:.1f}")
        if len(post.Solids) != 1 or not post.isValid(): errs.append(f"{lab}: Z post invalid")
    s = gshape(bottom); s.translate(T_FRONT)
    nb = add_feature(s, BOTTOM_FRONT + " (new front)", parent_of(bottom), bottom, 'Bar'); touched.add(nb.Name)
    origin[nb.Name] = bottom.Name; shift_of[nb.Name] = T_FRONT
    log(f"bottom front 2040 stays for the Backbone; copy at y {gbox(nb).YMin:.1f}..{gbox(nb).YMax:.1f}")
    # dock crossbar: above everything docked between the front verticals
    docked = [x for g in group_objs if g.Label in ('Left Dock', 'Right Dock', 'Left Toolhead', 'Right Toolhead')
              for x in descendants(g) if is_leaf(x)]
    ztop = max(gbox(x).ZMax for x in docked)
    s = gshape(top)                       # already moved to the new front
    s.translate(V(0, 0, (ztop + 5.0) - s.BoundBox.ZMin))
    dc = add_feature(s, "Dock crossbar (placeholder, 2040)", parent_of(top), top, 'Bar'); touched.add(dc.Name)
    log(f"dock crossbar: x {gbox(dc).XMin:.0f}..{gbox(dc).XMax:.0f} y {gbox(dc).YMin:.0f}..{gbox(dc).YMax:.0f} z {gbox(dc).ZMin:.1f}..{gbox(dc).ZMax:.1f} "
        f"(docked parts top at z {ztop:.1f})")

    # ---------- 2b) Monolith milled parts ----------
    gm = doc.addObject('App::DocumentObjectGroup', 'Monolith'); gm.Label = 'Monolith gantry (LDO milled, 2WD VT 9mm)'
    root.addObject(gm)
    station = {}
    for f, off, lab in MONO:
        names0 = {o.Name for o in doc.Objects}
        Import.insert(os.path.join(DL, f), doc.Name)
        new = [o for o in doc.Objects if o.Name not in names0]
        tops = [o for o in new if not o.InList]          # top-level imports (Origins are referenced by their Part)
        for t in tops:
            t.Placement = Rg.inverse().multiply(FreeCAD.Placement(off, FreeCAD.Rotation())).multiply(t.Placement)
            gm.addObject(t)
            if t.isDerivedFrom('App::Part') or t.isDerivedFrom('App::DocumentObjectGroup'): t.Label = f"{lab}: {t.Label}"
        sol = [o for o in new if is_leaf(o) and o.Shape.Solids]
        station[lab] = sol; touched |= {o.Name for o in new}
        (ax, ay), key = AXES[lab]
        ref = [o for o in sol if key in o.Label]
        if not ref: errs.append(f"{lab}: no '{key}' to check alignment"); continue
        c = gbox(ref[0]); cx, cy = (c.XMin + c.XMax) / 2, (c.YMin + c.YMax) / 2
        d = math.hypot(cx - ax, cy - ay)
        log(f"Monolith {lab}: {len(sol)} solids; {key} axis at ({cx:.2f}, {cy:.2f}), printed part's at ({ax:.2f}, {ay:.2f}): off {d:.2f} mm")
        if d > 3.0: errs.append(f"{lab}: axis {d:.2f} mm off the printed part's")
        elif d > 0.05: notes.append(f"{lab}: milled axis {d:.2f} mm from the printed AWD part's (2WD vs AWD joint geometry)")

    # ---------- 2c) Carbonara X beam ----------
    cf = Part.read(os.path.join(DL, CF_STEP))
    tube = max(cf.Solids, key=lambda s: s.BoundBox.XLength if abs(s.BoundBox.YLength - 20) < 0.5 and abs(s.BoundBox.ZLength - 20) < 0.5 else 0)
    tb = tube.BoundBox
    sec = Part.makeFace(tube.slice(V(1, 0, 0), (tb.XMin + tb.XMax) / 2), 'Part::FaceMakerBullseye')
    sec.translate(V(-(tb.XMin + tb.XMax) / 2, 0, 0))
    yc = (OLD_BEAM['y'][0] + OLD_BEAM['y'][1]) / 2
    sec.translate(V(OLD_BEAM['x'][0], yc - (tb.YMin + tb.YMax) / 2, DZ - (tb.ZMin + tb.ZMax) / 2))
    beam = sec.extrude(V(CF_LEN, 0, 0))
    cb = add_feature(beam, f"Carbonara CF X beam 20x20 {CF_LEN:.0f}", gm, None, 'XBeam'); touched.add(cb.Name)
    if cb.ViewObject is not None:
        try: cb.ViewObject.ShapeAppearance = (FreeCAD.Material(DiffuseColor=(0.12, 0.12, 0.12)),)
        except Exception: pass
    drop = [o for lab_ in ("XY right", "XY left") for o in station[lab_]
            if is_hw(o.Label) and gbox(o).intersect(beam.BoundBox) and gshape(o).common(beam).Volume > 0.1]
    drop_labels = sorted(set(o.Label.rstrip('0123456789') for o in drop))
    for o in drop:
        station[[k for k, v in station.items() if o in v][0]].remove(o); touched.discard(o.Name); doc.removeObject(o.Name)
    log(f"XY joints: dropped {len(drop)} slot T-nuts/screws that would sit inside the CF tube: {drop_labels}")
    if len(drop) != 12: errs.append(f"expected 12 XY-joint beam fasteners (3 T-nuts + 3 screws per joint), dropped {len(drop)}")
    log(f"Carbonara beam: section {sec.Area:.1f} mm2 (hollow: {len(sec.Wires)} wires), x {beam.BoundBox.XMin:.1f}..{beam.BoundBox.XMax:.1f} "
        f"y {beam.BoundBox.YMin:.1f}..{beam.BoundBox.YMax:.1f} z {beam.BoundBox.ZMin:.1f}..{beam.BoundBox.ZMax:.1f}")

    # ---------- 2d) MGN9 Y rails ----------
    src = by_label(RAIL_SRC, is_leaf); s = gshape(src); sb = s.BoundBox
    zmid = (sb.ZMin + sb.ZMax) / 2 + 3.3      # between the rail's M3 holes (40 mm pitch)
    _bk = s.common(Part.makeBox(500, 500, sb.ZMax - zmid + 1, V(sb.XMin - 200, sb.YMin - 200, zmid)))
    rfs = [f for f in _bk.Faces if isinstance(f.Surface, Part.Plane) and abs(abs(f.normalAt(0, 0).z) - 1) < 1e-6 and abs(f.CenterOfMass.z - zmid) < 1e-6]
    if len(rfs) != 1: raise RuntimeError(f"rail section: {len(rfs)} faces")
    rsec = rfs[0]
    rb = rsec.BoundBox                         # width along X (9), height along +Y from the base at YMin
    rsec.translate(V(-(rb.XMin + rb.XMax) / 2, -rb.YMin, -rsec.BoundBox.ZMin))
    def frontmost(lab_part): return min(gbox(o).YMin for o in station[lab_part])
    def rearmost(lab_part): return max(gbox(o).YMax for o in station[lab_part])
    for side, sgn in (("R", -1), ("L", +1)):
        fl, rl = (f"Front right", "Rear right") if side == "R" else ("Front left", "Rear left")
        # rail must sit between the front station's rearmost and the rear station's frontmost part along the bar face
        near = lambda o: abs(((gbox(o).XMin + gbox(o).XMax) / 2) - RAIL_X[side]) < 40
        y0 = max(gbox(o).YMax for o in station[fl] if near(o))
        y1 = min(gbox(o).YMin for o in station[rl] if near(o))
        L = math.floor((y1 - y0) / 10.0) * 10.0
        # section x (width) -> Z, section y (height, base->top) -> -X for the right rail, +X for the left rail
        ex, ey = V(0, 0, 1), V(sgn, 0, 0)
        ez = ex.cross(ey)
        m = FreeCAD.Matrix(ex.x, ey.x, ez.x, 0, ex.y, ey.y, ez.y, 0, ex.z, ey.z, ez.z, 0)
        f = rsec.copy(); f = f.transformGeometry(m)
        ystart = (y0 + y1) / 2 - L / 2
        f.translate(V(RAIL_X[side], ystart, DZ))
        rail = f.extrude(V(0, L, 0))
        r = add_feature(rail, f"MGN9-{L:.0f}mm Y rail ({side})", gm, src, 'YRail'); touched.add(r.Name)
        log(f"Y rail {side}: gap between mounts y {y0:.1f}..{y1:.1f} ({y1-y0:.1f}) -> MGN9 {L:.0f} mm at y {ystart:.1f}..{ystart+L:.1f}, "
            f"x {rail.BoundBox.XMin:.1f}..{rail.BoundBox.XMax:.1f}, z {rail.BoundBox.ZMin:.1f}..{rail.BoundBox.ZMax:.1f}, valid {rail.isValid()}")
        if not rail.isValid() or L < 400: errs.append(f"Y rail {side}: L={L} valid={rail.isValid()}")

    # ---------- 2e) belts ----------
    for lab in BELTS:
        o = by_label(lab, is_leaf); s = gshape(o)
        new, ys, segv, nf = splice_copy(s, BELT_SPLICE_Y, DY)
        if new is None: errs.append(f"belt {lab}: no clean section"); continue
        want = s.Volume + segv
        log(f"belt {lab} spliced at Y={ys}: {nf} strand(s) cut at y {ys} and lengthened with a copy of their own {DY:.0f} mm, "
            f"y {s.BoundBox.YMin:.1f}..{s.BoundBox.YMax:.1f} -> {new.BoundBox.YMin:.1f}..{new.BoundBox.YMax:.1f}, solids {len(s.Solids)}->{len(new.Solids)}, "
            f"vol {new.Volume:.0f} (want {want:.0f})")
        if len(new.Solids) != len(s.Solids) or abs(new.Volume - want) > 1e-3 * want or nf < 1 or not new.isValid():
            errs.append(f"belt {lab}: splice checks failed")
        n = add_feature(new, lab + " (new)", parent_of(o), o, 'Belt'); origin[n.Name] = o.Name
        touched |= {o.Name, n.Name}; doc.removeObject(o.Name); n.Label = lab

    # ---------- 4) bowden tubes ----------
    old_tubes = [o for o in doc.Objects if o.TypeId == 'Part::Feature' and o.Label.startswith('Bowden ')]
    bg = parent_of(old_tubes[0]) if old_tubes else None
    for t in old_tubes: touched.add(t.Name); doc.removeObject(t.Name)
    tubes = []
    for side, cl in INLETS.items():
        cb_ = gbox(by_label(cl))
        P0 = V((cb_.XMin + cb_.XMax) / 2, (cb_.YMin + cb_.YMax) / 2, cb_.ZMax); P1 = V(P0.x, EXIT_Y, EXIT_Z)
        a, b = HANDLES
        curve = Part.BezierCurve(); curve.setPoles([P0, P0 + V(0, 0, a), P1 - EXIT_DIR * b, P1])
        path = Part.Wire([curve.toShape(), Part.LineSegment(P1, P1 + EXIT_DIR * BEYOND).toShape()])
        tube = path.makePipeShell([Part.Wire(Part.makeCircle(OD / 2, P0, V(0, 0, 1)))], True, True)
        rmin = min(1 / max(curve.curvature(i / 400), 1e-12) for i in range(401)); L = curve.length() + BEYOND
        t = add_feature(tube, f"Bowden {side}", bg, None, 'BowdenTube')
        for prop, typ, val in (('OD', 'App::PropertyLength', OD), ('Inlet', 'App::PropertyVector', P0),
                               ('ExitPoint', 'App::PropertyVector', P1), ('ExitDir', 'App::PropertyVector', EXIT_DIR),
                               ('HandleInlet', 'App::PropertyLength', a), ('HandleExit', 'App::PropertyLength', b),
                               ('Beyond', 'App::PropertyLength', BEYOND), ('MinBendRadius', 'App::PropertyLength', rmin),
                               ('PathLength', 'App::PropertyLength', L)):
            t.addProperty(typ, prop, 'Bowden', 'route parameters (global mm); regenerate by script for other poses'); setattr(t, prop, val)
        if t.ViewObject is not None:
            try: t.ViewObject.ShapeAppearance = (FreeCAD.Material(DiffuseColor=(0.95, 0.95, 0.95), Transparency=0.4),)
            except Exception: pass
        touched.add(t.Name); tubes.append(t)
        log(f"tube {side}: inlet {P0.x:.1f},{P0.y:.1f},{P0.z:.1f}; length {L:.0f} mm (lite-5: 568), min bend R {rmin:.1f} mm, valid {tube.isValid()}")
        if not tube.isValid() or rmin < 50: errs.append(f"tube {side}: valid={tube.isValid()} R={rmin:.1f}")

    doc.recompute()
    # ---------- verify ----------
    now = {o.Name: o for o in doc.Objects if is_leaf(o)}
    for n, b in before.items():
        if n in touched: continue
        o = now.get(n)
        if o is None: errs.append(f"lost: {n}"); continue
        want = shifted(b, moved[n]) if n in moved else b
        if not close(gbox(o), want): errs.append(f"{'moved wrong' if n in moved else 'changed'}: {o.Label} {gbox(o)} want {want}")
    log(f"unchanged/moved check over {len(before)} original shapes done")
    gone = [n for n in removed_names if doc.getObject(n) is not None]
    if gone: errs.append(f"not removed: {gone}")
    # ---------- collisions: new / rebuilt / moved solids vs everything, minus the lite-5-dan baseline ----------
    allsol = [o for o in now.values() if o.Shape.Solids]
    stn = {o.Name: lab for lab, ss in station.items() for o in ss}
    check = [o for o in allsol if o.Name in touched or o.Name in moved]
    hits = overlaps(check, allsol, skip=lambda a, b: bool(stn.get(a.Name)) and stn.get(a.Name) == stn.get(b.Name))
    def where(o): return stn.get(o.Name) or '/'.join(x.Label for x in reversed(ancestors(o)))[-45:]
    new_hits, pre, hw = [], 0, 0
    for (na, nb), v in sorted(hits.items(), key=lambda kv: -kv[1]):
        oa, ob = now[na], now[nb]
        k = tuple(sorted((origin.get(na, na), origin.get(nb, nb))))
        if k in base and abs(base[k] - v) <= 0.1 * base[k] + 1: pre += 1; continue
        if is_hw(oa.Label) or is_hw(ob.Label): hw += 1; new_hits.append(("hardware", v, oa, ob)); continue
        new_hits.append(("PART", v, oa, ob))
    log(f"collisions > 1 mm3: {len(hits)} total; {pre} already in lite-5-dan (unchanged); "
        f"{len(new_hits) - hw} new part-part; {hw} new involving hardware (screws/T-nuts in holes and slots)")
    for kind, v, oa, ob in new_hits:
        log(f"   {kind:8} {v:8.1f} mm3  {oa.Label} [{where(oa)}]  x  {ob.Label} [{where(ob)}]")
    for n in notes: log("NOTE", n)
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
