# GUI pass: vt350-lite-22.FCStd -> vt350-lite-23.FCStd   (headless = dry run, never saves)   #53
# Dock screws on the A4Tv2 part-cooling duct instead of andrewmcgr's MadMax plate bracket, so each head gets back the
# X reach the bracket's rear-upper corner cost (#52/#53: it hit the LDO XY joint).
#
# Per head (left = -X dock side, right = +X, mirror image):
#  1. Remix the dock-side 4010 duct (DW-Tas A4Tv2, CC BY-NC-SA 4.0): 3 bosses for the MadMax dock screws, outer faces
#     on the plane the old bracket face was on (head X -/+39), so the dock doesn't move in X. Same pocket as the
#     bracket (Voron M3 heat-set: dia 4.8 x 4.4 deep, then a dia 2.9 x 4.2 tail). Square 20 x 54 (dock unchanged), at head
#     frame Y -8.8 / -28.8, Z 7.5 / 61.5 (rear-bottom, rear-top, front-top: the dock has no front-bottom slot). That keeps
#     every boss forward of the joint band (Y >= 13), clear of the duct's two top body-screw counterbores (Y 6.13 and
#     -17.5, Z 62) and the fan's tab screws, and outside the fan intake. Each boss stops 0.2 mm short of the inner
#     surface of the duct's solid wall under its whole footprint, so it doesn't reach into the air channel.
#  2. Delete both plate-bracket variants (Dock Bracket, Alternate Bracket). Plate and Plate Back stay.
#  3. Park the head HEAD_BACK further back (+Y): MadMax picks up by pushing the parked head 6.0 mm forward along the
#     keyslots to their large opening, then leaves sideways in X (#52 AC1). lite-14 took the parked carriage copy as
#     the pickup pose and left 2.19 mm, so pickup was ~3.8 mm out of reach. Moves: the toolhead group, the dock's
#     carriage copy, Plate Assembly, Plate Back.
#  4. Move the keyslot plate (Dock Asembly) so its parked screw positions (the old bracket's screw axes) land on the
#     new bosses: D = (0, -14.06, -5.78). The dock arms: whole arm down D.z (its M5s ride in the 2040's Z slot), and
#     shortened by -D.y through its constant-section straight run (both cut sections checked identical).
#  5. Rebuild the bowden tubes from the moved couplers (exits fixed).
# Checks before saving: screws line up with the moved keyslots (<= 0.05 mm), pickup at the large-opening pose is
# reachable (>= 1 mm), boss/pocket geometry, no new collisions vs lite-22, everything else unchanged.
# Exports STLs of the remixed ducts and arms to data/stl/ (the printable copies live in cad/derived/).
import FreeCAD, Part, MeshPart, sys, os, time, traceback, math
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-22.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-23.FCStd"
DRY = not FreeCAD.GuiUp
HEAD_BACK = 12.5                 # mm (+Y) the parked heads move back (sets the arm cut: 14.06 of a 14.65 constant run)
SLIDE = 6.0                      # keyslot slide from the parked position to the large opening (#52, sliced)
REACH_Y = -21.19                 # gantry carriage front face at the front travel limit (lite9_rails.log)
FACE_X = 39.0                    # |head X| of the boss outer faces = old bracket outer face = dock inner face
BOSS_R = 4.0
POCKET = (2.4, 4.4)              # insert pocket radius, depth (from andrewmcgr's Dock Bracket)
TAIL = (1.45, 4.2)               # screw tail radius, depth beyond the pocket
SCREWS = {"rear-top": (-8.8, 61.5), "rear-bottom": (-8.8, 7.5), "front-top": (-28.8, 61.5)}   # head frame (Y, Z)
FAN_SCREWS = [(7.37, 19.6), (-27.1, 19.6), (7.37, 54.6), (-27.1, 54.6)]   # 4010 fan tab screws (head Y, Z), r 2.3, inside
FAN_R = 2.3
CBORE = (3.0, (60.0, 64.0))      # the duct's two body-screw (M3x6 BHCS) counterbores: r, head-Z band. Their axes are
                                 # tilted ~10 deg with the duct face, so clearance is checked along the axis, out past the plane
CLEAR = 0.4                      # min gap boss <-> counterbore cylinder (incl. the screw's way in)
JOINT_BAND_Y = 13.0
SIDES = {"Left": dict(s=-1, head="Left Toolhead", dock="Left Dock", duct="[a]_Duct-4010-left",
                      brackets=["Dock Bracket", "Alternate Bracket v1"], keys="Dock Asembly",
                      arm="Dock Arm v1 Bottom +5mm", madmax="MadMax 4 XOL v11 v1",
                      ride=["Carriage", "Plate Assembly", "Plate Back"], copy="COMPOUND003"),
         "Right": dict(s=1, head="Right Toolhead", dock="Right Dock", duct="[a]_Duct-4010-right001",
                       brackets=["Dock Bracket(Mirror)", "Alternate Bracket v1(Mirror)"], keys="Dock Asembly(Mirror)",
                       arm="Dock Arm v1 Bottom +5mm(Mirror)", madmax="MadMax 4 XOL v11 v1(Mirror)",
                       ride=["Carriage(Mirror)", "Plate Assembly(Mirror)", "Plate Back(Mirror)"], copy="COMPOUND004")}
NOZZLE = "E3D v6 HotEnd - Nozzle"
INLETS = {"Left": "4mm Bowden Coupler v1 (1)", "Right": "4mm Bowden Coupler v1 (1) (1)"}
os.makedirs(WORK + "/logs", exist_ok=True); os.makedirs(WORK + "/stl", exist_ok=True)
log_f = open(WORK + "/logs/lite23_cowl_docks.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
_BOX = {}
def gbox(o):
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
def frame_of_parent(par):
    if par is None: return FreeCAD.Placement()
    if par.isDerivedFrom('App::Part'): return par.getGlobalPlacement()
    for p in ancestors(par):
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
    return FreeCAD.Placement()
def container_global(o): return frame_of_parent(parent_of(o))
def descendants(g):
    out = []
    for c in getattr(g, 'Group', []) or []:
        out.append(c); out += descendants(c)
    return out
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def shifted(b, v): return FreeCAD.BoundBox(b.XMin + v.x, b.YMin + v.y, b.ZMin + v.z, b.XMax + v.x, b.YMax + v.y, b.ZMax + v.z)
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax), (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
def translate_global(o, T):
    par_g = container_global(o); g = o.getGlobalPlacement()
    o.Placement = par_g.inverse().multiply(FreeCAD.Placement(T, FreeCAD.Rotation())).multiply(g)
def set_global_shape(o, s):
    loc = s.copy(); loc.Placement = container_global(o).inverse().multiply(loc.Placement); o.Shape = loc
def one(label, under=None):
    c = [o for o in doc.getObjectsByLabel(label) if under is None or under in [a.Label for a in ancestors(o)]]
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {label!r} under {under!r}")
    return c[0]
def look(o):
    vo = getattr(o, 'ViewObject', None)
    return [(a.DiffuseColor, a.Transparency) for a in vo.ShapeAppearance] if vo is not None and hasattr(vo, 'ShapeAppearance') else None
def restore_look(o, ap0):
    if ap0 is None: return
    try:
        ap = o.ViewObject.ShapeAppearance
        if len(ap) != len(ap0): ap = [ap[0]] if ap else ap
        for x in ap: x.DiffuseColor = ap0[0][0]; x.Transparency = ap0[0][1]
        o.ViewObject.ShapeAppearance = ap
    except Exception: pass
def overlaps(objs_a, objs_all, skip=lambda a, b: False):
    out = {}
    for a in objs_a:
        sa = None
        for b in objs_all:
            if a.Name == b.Name or skip(a, b) or not gbox(a).intersect(gbox(b)): continue
            try:
                sa = sa or gshape(a); v = sa.common(gshape(b)).Volume
            except Exception: continue
            if v > 1.0: out[(a.Name, b.Name)] = v
    return out
def xcyl(r, x0, x1, y, z):
    """cylinder of radius r along X from x0 to x1 (either order) through (y, z)"""
    lo, hi = min(x0, x1), max(x0, x1)
    return Part.makeCylinder(r, hi - lo, V(lo, y, z), V(1, 0, 0))
def wall_along_x(solid, y, z, x_out, x_in):
    """first solid run met going from x_out toward x_in at (y, z): (face x, run length) or None"""
    e = Part.makeLine(V(x_out, y, z), V(x_in, y, z))
    c = e.common(solid)
    runs = []
    for ed in c.Edges:
        a, b = ed.Vertexes[0].Point.x, ed.Vertexes[-1].Point.x
        near, far = (a, b) if abs(a - x_out) < abs(b - x_out) else (b, a)
        runs.append((abs(near - x_out), near, abs(far - near)))
    if not runs: return None
    runs.sort(); return runs[0][1], runs[0][2]
def section(s, y):
    return Part.makeFace(s.slice(V(0, 1, 0), y), "Part::FaceMakerBullseye")

try:
    errs, finds = [], []
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    leaves0 = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: gbox(o) for o in leaves0}; label0 = {o.Name: o.Label for o in leaves0}
    tube_names = {o.Name for o in leaves0 if o.Label.startswith('Bowden ')}
    plan = {}
    for side, d in SIDES.items():
        s = d["s"]; head = one(d["head"]); mm = one(d["madmax"], d["dock"])
        nz = [o for o in descendants(head) if is_leaf(o) and o.Label.startswith(NOZZLE)]
        if len(nz) != 1: raise RuntimeError(f"{side}: {len(nz)} nozzles")
        b = gbox(nz[0]); O = V((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, b.ZMin)
        duct = one(d["duct"], d["head"]); brackets = [one(x, d["dock"]) for x in d["brackets"]]
        keys = one(d["keys"], d["dock"]); arm = one(d["arm"], d["dock"]); copy = one(d["copy"], d["dock"])
        ride = [one(x, d["dock"]) for x in d["ride"]]
        # old parked screw axes = the Dock Bracket's three dia-2.9 screw holes (axis X); map them to the new screws
        bs = gshape(brackets[0]); holes = set()
        for f in bs.Faces:
            su = f.Surface
            if isinstance(su, Part.Cylinder) and abs(su.Radius - 1.45) < 0.01 and abs(abs(su.Axis.x) - 1) < 1e-6:
                holes.add((round(su.Center.y - O.y, 3), round(su.Center.z - O.z, 3)))
        holes = sorted(holes)
        if len(holes) != 3: raise RuntimeError(f"{side}: {len(holes)} dock-screw holes in {brackets[0].Label}")
        ys = sorted({h[0] for h in holes}); zs = sorted({h[1] for h in holes})
        old = {"rear-top": (ys[-1], zs[-1]), "rear-bottom": (ys[-1], zs[0]), "front-top": (ys[0], zs[-1])}
        if set(old.values()) != set(holes): raise RuntimeError(f"{side}: hole pattern isn't rear-top/rear-bottom/front-top: {holes}")
        D = {k: (SCREWS[k][0] + HEAD_BACK - old[k][0], SCREWS[k][1] - old[k][1]) for k in SCREWS}
        dy = [v[0] for v in D.values()]; dz = [v[1] for v in D.values()]
        if max(dy) - min(dy) > 1e-3 or max(dz) - min(dz) > 1e-3: raise RuntimeError(f"{side}: new square isn't the old one translated: {D}")
        Dk = V(0, dy[0], dz[0])
        log(f"{side}: docked nozzle tip ({O.x:.2f}, {O.y:.2f}, {O.z:.2f}); old dock screws (head Y, Z) {old}; "
            f"keyslot plate moves ({Dk.x:.2f}, {Dk.y:.2f}, {Dk.z:.2f})")
        plan[side] = dict(O=O, duct=duct, brackets=brackets, keys=keys, arm=arm, copy=copy, ride=ride, head=head, old=old, D=Dk)
    # every leaf that moves, and how
    TH = V(0, HEAD_BACK, 0)
    exp_move = {}
    for side, p in plan.items():
        for g in [p["head"]] + p["ride"]:
            for x in ([g] + descendants(g)):
                if is_leaf(x) and x.Name not in tube_names: exp_move[x.Name] = TH
        exp_move[p["keys"].Name] = p["D"]
    special = {p["duct"].Name for p in plan.values()} | {p["arm"].Name for p in plan.values()} | tube_names
    deleted = {b.Name for p in plan.values() for b in p["brackets"]}
    movers0 = [o for o in leaves0 if (o.Name in exp_move or o.Name in special) and o.Name not in tube_names]
    skip = lambda a, b: b.Name in exp_move or b.Name in special
    ov0 = overlaps(movers0, leaves0, skip); log(f"lite-22 overlaps of the parts that move or change with the rest: {len(ov0)}")
    for (a_, b_), v in sorted(ov0.items(), key=lambda kv: -kv[1]): log(f"     {v:8.1f} mm3  {label0[a_]} x {label0[b_]}")
    # ---------------------------------------------------------------- 1. ducts (in the docked frame, before any move)
    stls = []
    for side, p in plan.items():
        s, O, duct = SIDES[side]["s"], p["O"], p["duct"]
        sd = gshape(duct); v0 = sd.Volume; ap0 = look(duct)
        if len(sd.Solids) != 1: errs.append(f"{side} duct: {len(sd.Solids)} solids")
        x_plane = O.x + s * FACE_X; x_far = O.x + s * 5.0
        # features the bosses must keep off: the fan tab screws (inside the duct) and the two body-screw counterbores
        cyl = [(f, f.Surface.Center, f.Surface.Radius) for f in sd.Faces if isinstance(f.Surface, Part.Cylinder)]
        for ky, kz in FAN_SCREWS:
            if not any(abs(r - FAN_R) < 0.05 and math.hypot(c.y - O.y - ky, c.z - O.z - kz) < 0.3 for _, c, r in cyl):
                errs.append(f"{side} duct: no fan screw r{FAN_R} at head (Y {ky}, Z {kz})")
        cb = [(f, c) for f, c, r in cyl if abs(r - CBORE[0]) < 0.01 and abs(f.Surface.Axis.x) > 0.95
              and CBORE[1][0] <= c.z - O.z <= CBORE[1][1]]
        if len(cb) != 2: errs.append(f"{side} duct: {len(cb)} body-screw counterbores (want 2)")
        cb_lines = []
        for f, c in cb:
            a = f.Surface.Axis; fb = f.BoundBox
            x_in = fb.XMax if s < 0 else fb.XMin                       # inner end of the counterbore
            x_out = x_plane + s * 8.0                                  # its way in, out past the boss plane
            p_in = c + a * ((x_in - c.x) / a.x); p_out = c + a * ((x_out - c.x) / a.x)
            cb_lines.append(Part.makeLine(p_in, p_out))
            log(f"{side} duct: body-screw counterbore r{CBORE[0]} at head Z {c.z - O.z:.2f}: inner end head (X {p_in.x - O.x:.2f}, Y {p_in.y - O.y:.2f}), "
                f"at the boss plane head Y {(c + a * ((x_plane - c.x) / a.x)).y - O.y:.2f}")
        bosses, holes_, checks = [], [], []
        for k, (y, z) in SCREWS.items():
            for ky, kz in FAN_SCREWS:
                gap = math.hypot(y - ky, z - kz) - BOSS_R - FAN_R
                if gap < CLEAR: errs.append(f"{side} {k}: boss {gap:.2f} mm from the fan screw at ({ky}, {kz})")
            if y + BOSS_R >= JOINT_BAND_Y: errs.append(f"{side} {k}: boss reaches the joint band")
            # wall under the footprint: face depth from the plane, and how far solid material goes
            faces, ends, n_miss = [], [], 0
            for i in range(-8, 9):
                for j in range(-8, 9):
                    dy_, dz_ = i * 0.5, j * 0.5
                    if math.hypot(dy_, dz_) > BOSS_R: continue
                    w = wall_along_x(sd, O.y + y + dy_, O.z + z + dz_, x_plane, x_far)
                    if w is None: n_miss += 1; continue
                    xf, run = w; faces.append(abs(xf - x_plane)); ends.append(abs(xf - x_plane) + run)
            depth = min(ends) - 0.2                                   # stop inside the solid everywhere
            touch = sum(1 for f_ in faces if f_ < depth - 0.3) / max(1, len(faces) + n_miss)
            need = POCKET[1] + TAIL[1] + 0.6
            log(f"{side} {k} (head Y {y}, Z {z}): duct face {min(faces):.2f}..{max(faces):.2f} mm in from the plane, "
                f"solid wall ends {min(ends):.2f}..{max(ends):.2f}; boss {depth:.2f} long, fused over {touch:.0%} of its "
                f"footprint; {n_miss} footprint points with no duct behind them")
            if depth < need: errs.append(f"{side} {k}: boss {depth:.2f} mm < pocket + tail + 0.6 ({need:.1f})")
            if touch < 0.25: errs.append(f"{side} {k}: boss touches the duct over only {touch:.0%}")
            bosses.append(xcyl(BOSS_R, x_plane, x_plane - s * depth, O.y + y, O.z + z))
            axis = Part.makeLine(V(x_plane, O.y + y, O.z + z), V(x_plane - s * depth, O.y + y, O.z + z))
            for ln in cb_lines:
                gap = axis.distToShape(ln)[0] - BOSS_R - CBORE[0]
                log(f"   {k}: {gap:.2f} mm from a body-screw counterbore (or its way in)")
                if gap < CLEAR: errs.append(f"{side} {k}: boss {gap:.2f} mm from a body-screw counterbore")
            checks.append(xcyl(POCKET[0], x_plane, x_plane - s * POCKET[1], O.y + y, O.z + z))
            checks.append(xcyl(TAIL[0], x_plane - s * POCKET[1], x_plane - s * (POCKET[1] + TAIL[1]), O.y + y, O.z + z))
            holes_.append(xcyl(POCKET[0], x_plane + s * 0.01, x_plane - s * POCKET[1], O.y + y, O.z + z))
            holes_.append(xcyl(TAIL[0], x_plane - s * POCKET[1], x_plane - s * (POCKET[1] + TAIL[1]), O.y + y, O.z + z))
        solid = sd.Solids[0]
        fused = solid.multiFuse(bosses).removeSplitter()
        # the tails and pockets must sit in material: nothing of them outside boss + duct before cutting
        outside = sum(h.cut(fused).Volume for h in checks)
        if outside > 0.05: errs.append(f"{side}: {outside:.2f} mm3 of the pockets/tails would be in air")
        new = fused.cut(holes_).removeSplitter()
        bv = Part.makeCompound(bosses).Volume
        ov = sum(b_.common(solid).Volume for b_ in bosses)
        hv = sum(h.Volume for h in checks)
        want = v0 + bv - ov - hv
        log(f"{side} duct: volume {v0:.1f} -> {new.Volume:.1f} (bosses {bv:.1f}, into the wall {ov:.1f}, holes {hv:.1f}; want {want:.1f}); "
            f"valid {new.isValid()}, solids {len(new.Solids)}")
        if abs(new.Volume - want) > 0.5 or not new.isValid() or len(new.Solids) != 1: errs.append(f"{side} duct: bad remix")
        nb = new.BoundBox; edge = nb.XMin if s < 0 else nb.XMax
        if abs(edge - x_plane) > 1e-3: errs.append(f"{side} duct: outer face at {edge:.3f}, want {x_plane:.3f}")
        set_global_shape(duct, new); restore_look(duct, ap0)
        duct.Label = f"{SIDES[side]['duct'].replace('001', '')} MadMax dock bosses (remix, CC BY-NC-SA 4.0)"
        m = MeshPart.meshFromShape(Shape=new, LinearDeflection=0.02, AngularDeflection=0.2)
        fn = f"{WORK}/stl/a4tv2_duct_4010_{side.lower()}_madmax_dock.stl"; m.write(fn); stls.append(fn)
        log(f"   STL {os.path.relpath(fn, WORK)}: {m.CountFacets} facets")
    doc.recompute(); _BOX.clear()
    # ---------------------------------------------------------------- 2. delete the bracket variants
    for p in plan.values():
        for b in p["brackets"]: log(f"delete {b.Label}"); doc.removeObject(b.Name)
    doc.recompute(); _BOX.clear()
    # ---------------------------------------------------------------- 3./4. move heads, plates, carriage copies, keyslot plates
    for side, p in plan.items():
        for g in [p["head"]] + p["ride"]: translate_global(g, TH)
        translate_global(p["keys"], p["D"])
    doc.recompute(); _BOX.clear()
    # ---------------------------------------------------------------- 4b. dock arms
    for side, p in plan.items():
        arm = p["arm"]; s0 = gshape(arm); ap0 = look(arm); L = -p["D"].y
        a_ref = section(s0, -51.6).Area
        ys_ = [-62 + 0.05 * i for i in range(361)]
        const = [y for y in ys_ if abs(section(s0, y).Area - a_ref) < 0.01]
        lo_, hi_ = -51.6, -51.6                         # contiguous constant run around -51.6
        while round(lo_ - 0.05, 2) in [round(y, 2) for y in const]: lo_ -= 0.05
        while round(hi_ + 0.05, 2) in [round(y, 2) for y in const]: hi_ += 0.05
        span = hi_ - lo_
        log(f"{side} arm: constant section {a_ref:.1f} mm2 over Y {lo_:.2f}..{hi_:.2f} ({span:.2f} mm); shorten {L:.2f}")
        if span < L + 0.2: raise RuntimeError(f"{side} arm: constant run {span:.2f} < {L:.2f} + 0.2")
        y1 = lo_ + (span - L) / 2; y2 = y1 + L
        f1 = section(s0, y1); f2 = section(s0, y2); f2.translate(V(0, -L, 0))
        diff = f1.cut(f2).Area + f2.cut(f1).Area
        log(f"   cut at Y {y1:.2f} and {y2:.2f}; sections differ by {diff:.4f} mm2")
        if diff > 0.01: errs.append(f"{side} arm: cut sections differ ({diff:.3f} mm2)")
        bb = s0.BoundBox; big = 2000
        lo = s0.common(Part.makeBox(big, y1 - bb.YMin + 1, big, V(-big / 2, bb.YMin - 1, -big / 2)))
        hi = s0.common(Part.makeBox(big, bb.YMax - y2 + 1, big, V(-big / 2, y2, -big / 2)))
        hi.translate(V(0, -L, 0))
        parts = lo.Solids + hi.Solids
        r = parts[0].multiFuse(parts[1:]).removeSplitter(); r.translate(V(0, 0, p["D"].z))
        want = s0.Volume - f1.Area * L
        log(f"   volume {s0.Volume:.1f} -> {r.Volume:.1f} (want {want:.1f}); valid {r.isValid()}, solids {len(r.Solids)} (was {len(s0.Solids)})")
        if abs(r.Volume - want) > 0.5 or not r.isValid() or len(r.Solids) != len(s0.Solids): errs.append(f"{side} arm: bad shortened shape")
        rb = r.BoundBox
        if abs(rb.YMin - bb.YMin) > 1e-3 or abs(rb.YMax - (bb.YMax - L)) > 1e-3 or abs(rb.ZMin - (bb.ZMin + p["D"].z)) > 1e-3:
            errs.append(f"{side} arm: ends in the wrong place")
        set_global_shape(arm, r); restore_look(arm, ap0)
        net = 5.0 - L
        arm.Label = arm.Label.replace("+5mm", f"{net:+.2f}mm")
        m = MeshPart.meshFromShape(Shape=r, LinearDeflection=0.02, AngularDeflection=0.2)
        fn = f"{WORK}/stl/dock_arm_v1_bottom_{'minus' if net < 0 else 'plus'}{abs(net):.2f}mm{'_mirror' if 'Mirror' in arm.Label else ''}.stl"
        m.write(fn); stls.append(fn); log(f"   STL {os.path.relpath(fn, WORK)}: {m.CountFacets} facets")
    doc.recompute(); _BOX.clear()
    # ---------------------------------------------------------------- checks: screws vs keyslots, pickup reach
    for side, p in plan.items():
        s, O = SIDES[side]["s"], p["O"]; On = O + TH
        nd = gshape(p["duct"])
        cyl = {(round(f.Surface.Center.y, 3), round(f.Surface.Center.z, 3)) for f in nd.Faces
               if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - POCKET[0]) < 1e-3}
        for k, (y, z) in SCREWS.items():
            oy, oz = p["old"][k]
            slot = V(0, O.y + oy, O.z + oz) + p["D"]                     # parked screw axis of the moved keyslot plate
            got = min(cyl, key=lambda c: math.hypot(c[0] - slot.y, c[1] - slot.z)) if cyl else None
            off = math.hypot(got[0] - slot.y, got[1] - slot.z) if got else 99
            log(f"{side} {k}: pocket axis (Y {got[0]:.3f}, Z {got[1]:.3f}) vs moved keyslot (Y {slot.y:.3f}, Z {slot.z:.3f}): {off:.4f} mm")
            if off > 0.05: errs.append(f"{side} {k}: screw {off:.3f} mm off its keyslot")
        cf = gbox(p["copy"]).YMin
        margin = cf - SLIDE - REACH_Y
        log(f"{side}: parked carriage copy front face Y {cf:.2f}; at the large opening {cf - SLIDE:.2f}; reach {REACH_Y} -> margin {margin:+.2f}")
        finds.append(f"{side}: pickup at the keyslots' large opening has {margin:+.2f} mm before the hard stop (lite-22: {2.19 - SLIDE:+.2f})")
        if margin < 1.0: errs.append(f"{side}: pickup margin {margin:.2f} < 1")
        rear = max(c[0] for c in cyl) + BOSS_R - On.y
        log(f"{side}: bosses reach head Y {rear:.2f} (joint band starts at {JOINT_BAND_Y})")
    # ---------------------------------------------------------------- 5. bowden tubes
    tubes0 = [o for o in doc.Objects if is_leaf(o) and o.Label.startswith('Bowden ')]
    made = []
    for t in tubes0:
        side = t.Label.split()[1]
        cb = gbox(one(INLETS[side]))
        P0 = V((cb.XMin + cb.XMax) / 2, (cb.YMin + cb.YMax) / 2, cb.ZMax)
        old_ = V(t.Inlet)
        log(f"tube {side}: coupler top now {P0.x:.2f},{P0.y:.2f},{P0.z:.2f} (was {old_.x:.2f},{old_.y:.2f},{old_.z:.2f})")
        if (P0 - old_ - TH).Length > 0.05: errs.append(f"tube {side}: coupler moved {P0 - old_}, expected {TH}")
        P1 = V(t.ExitPoint); ED = V(t.ExitDir); a_ = t.HandleInlet.Value; b_ = t.HandleExit.Value; BY = t.Beyond.Value; OD = t.OD.Value
        c = Part.BezierCurve(); c.setPoles([P0, P0 + V(0, 0, a_), P1 - ED * b_, P1])
        path = Part.Wire([c.toShape(), Part.LineSegment(P1, P1 + ED * BY).toShape()])
        tube = path.makePipeShell([Part.Wire(Part.makeCircle(OD / 2, P0, V(0, 0, 1)))], True, True)
        rmin = min(1 / max(c.curvature(i / 400), 1e-12) for i in range(401))
        props = {q: getattr(t, q) for q in ('OD', 'Inlet', 'ExitPoint', 'ExitDir', 'HandleInlet', 'HandleExit', 'Beyond', 'MinBendRadius', 'PathLength')}
        props['Inlet'] = P0; props['MinBendRadius'] = rmin; props['PathLength'] = path.Length
        par = parent_of(t); Cg = frame_of_parent(par); app = look(t)
        doc.removeObject(t.Name)
        loc = tube.copy(); loc.Placement = Cg.inverse().multiply(loc.Placement)
        n = doc.addObject('Part::Feature', 'BowdenTube'); n.Shape = loc
        if par is not None: par.addObject(n)
        n.Label = f"Bowden {side}"
        for q, v in props.items():
            typ = 'App::PropertyVector' if q in ('Inlet', 'ExitPoint', 'ExitDir') else 'App::PropertyLength'
            n.addProperty(typ, q, 'Bowden', 'route parameters (global mm); regenerate by script for other poses'); setattr(n, q, v)
        restore_look(n, app)
        doc.recompute(); _BOX.clear()
        nb = gshape(n).BoundBox
        log(f"   rebuilt: starts {nb.ZMin - P0.z:+.2f} from the coupler top; min bend R {rmin:.1f}; length {path.Length:.1f}; valid {tube.isValid()}")
        if abs(nb.ZMin - P0.z) > 0.05 or not tube.isValid() or rmin < 100: errs.append(f"tube {side}: bad rebuild")
        made.append(n)
    # ---------------------------------------------------------------- collisions vs lite-22
    now = {o.Name: o for o in doc.Objects if is_leaf(o)}
    allnow = list(now.values())
    movers1 = [now[n] for n in [o.Name for o in movers0] if n in now]
    ov1 = overlaps(movers1, allnow, skip)
    new_ = {k: v for k, v in ov1.items() if k not in ov0 or v > ov0[k] + 1.0}
    gone = {k: v for k, v in ov0.items() if k not in ov1}
    log(f"moving/changed parts vs the rest: {len(ov1)} overlaps ({len(new_)} new or larger than in lite-22; {len(gone)} gone)")
    for (a_, b_), v in sorted(gone.items(), key=lambda kv: -kv[1]): log(f"     gone {v:8.1f} mm3  {label0.get(a_, a_)} x {label0.get(b_, b_)}")
    for (a_, b_), v in sorted(new_.items(), key=lambda kv: -kv[1]):
        A, B = now[a_], now[b_]; pb = parent_of(B)
        log(f"     NEW {v:8.1f} mm3  {A.Label} x {B.Label} [{pb.Label if pb else ''}]  (lite-22: {ov0.get((a_, b_), 0):.1f})")
        errs.append(f"new overlap {A.Label} x {B.Label} ({v:.1f} mm3)")
    tov = overlaps(made, allnow, skip=lambda a, b: b in made or b.Label in INLETS.values())
    log(f"tubes: {len(tov)} overlaps")
    for (a_, b_), v in tov.items():
        A, B = now[a_], now[b_]
        if B.Label.startswith("Roof felt"):          # lite-16: planned pass-throughs (a hole in the roof felt per tube)
            c = gshape(A).common(gshape(B)).BoundBox
            log(f"   pass-through {A.Label} x {B.Label}: {v:.1f} mm3, centre ({(c.XMin + c.XMax) / 2:.1f}, {(c.YMin + c.YMax) / 2:.1f}, {(c.ZMin + c.ZMax) / 2:.1f})")
            finds.append(f"{A.Label} still crosses {B.Label} (lite-16 pass-through); centre Y {(c.YMin + c.YMax) / 2:.1f}")
        else: errs.append(f"{A.Label} overlaps {B.Label} ({v:.1f} mm3)")
    # ---------------------------------------------------------------- everything else unchanged
    for nm, b in before.items():
        if nm in tube_names or nm in special: continue
        if nm in deleted:
            if nm in now: errs.append(f"not deleted: {label0[nm]}")
            continue
        if nm not in now: errs.append(f"lost {label0[nm]}"); continue
        exp = shifted(b, exp_move[nm]) if nm in exp_move else b
        if not close(gbox(now[nm]), exp): errs.append(f"{'moved wrongly' if nm in exp_move else 'changed'}: {now[nm].Label}")
    log(f"moved: {len(exp_move)} solids; deleted {len(deleted)}; remixed {len(special) - len(tube_names)}")
    log("FINDINGS:"); [log("  " + f) for f in finds]
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else:
        doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
        FreeCAD.closeDocument(doc.Name)
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
