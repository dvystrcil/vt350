# GUI pass: vt350-lite-16.FCStd -> vt350-lite-17.FCStd   (headless = dry run, never saves)
# Kinematic bed: tanaes's laser-cut Trident set (whopping_Voron_mods/kinematic_bed, GPL-3.0; the user owns West3D's
# aluminium kit) replaces the printed Z_Bed holders and the V2.4 kinematic parts the model carried.
#  Parts come from his DXFs (DXFs/Trident/*.dxf -> $VT350_DL/tanaes_trident_parts.json via tanaes_dxf2json.py),
#  extruded to the BOM thicknesses: A/B/E/F/G/I 3 mm, C/D/H 2 mm, J 28 ga (0.38 mm) spring steel.
#  Anchors (all from holes, see notes/kinematic-bed.md):
#   A, B, G: bore concentric with the existing GE5C; A/B M5s then sit on the front extrusion slot, G's M3s on the spine.
#   I: on the bore, its 6 holes on A/B/G's 6 tapped holes.
#   C/E, D/F: E's two end holes on the front extrusion's slot centreline, slid along it until the pin groove runs
#   through the bed's own front mount hole (tanaes README: the balls hang from the bed's standard mount points). This
#   lands C/E 54.7 mm inboard of A's bore, the spacing his DXFs are drawn at.
#   H on G (holes); rear ball = the bed's rear hole projected on G's groove.
#  Stack (README): GE5C from below into A/B/G with I on top, so the outer ring's top = A/B/G top; pins (M5x20) rest in
#   E/G's 3.84 mm slots; 9 mm sphere nut on two pins; M3 thin hex nut; leaf spring; plate.
#  The GE5Cs and the Z carriages under them move to the new bearing height (Z is the carriage's free axis).
#  Build plate: the user's LDO plate is 10 mm (measured 2026-11-05; 13.5 with heater + magnet), so the model's 6 mm
#  plate is thickened 4 mm downward (holes carried through) and set on the springs.
#  Spring is shown flat (as cut); preload bends its tip down onto C/D/H's tapped hole. Fasteners are not modelled.
import FreeCAD, Part, sys, os, time, traceback, math, json
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
DL = os.environ.get("VT350_DL", "/tmp/claude-1000/-home-dan-Code/ef5a4752-63f8-463b-aef7-f9a279c0ffd2/scratchpad/dl_lite17")
SRC = "/home/dan/Documents/VT350/vt350-lite-16.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-17.FCStd"
DRY = not FreeCAD.GuiUp
THK = dict(A=3.0, B=3.0, C=2.0, D=2.0, E=3.0, F=3.0, G=3.0, H=2.0, I=3.0, J=0.3797)
NAMES = dict(A="A left bearing plate", B="B right bearing plate", C="C left top", D="D right top", E="E left bottom",
             F="F right bottom", G="G back bottom", H="H back top", I="I bearing retain", J="J leaf spring")
PIN_D, PIN_L, BALL_D = 5.0, 20.0, 9.0
PLATE_T = 10.0                                  # user's LDO plate, measured
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite17_kinematic.log", "w"); t0 = time.time()
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
    for c in getattr(g, 'Group', []):
        out.append(c); out += descendants(c)
    return out
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def shifted(b, v): return FreeCAD.BoundBox(b.XMin + v.x, b.YMin + v.y, b.ZMin + v.z, b.XMax + v.x, b.YMax + v.y, b.ZMax + v.z)
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax), (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
def translate_global(o, T):
    par_g = container_global(o); g = o.getGlobalPlacement()
    o.Placement = par_g.inverse().multiply(FreeCAD.Placement(T, FreeCAD.Rotation())).multiply(g)
def one(label, cond=lambda o: True):
    c = [o for o in doc.getObjectsByLabel(label) if cond(o)]
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {label!r}")
    return c[0]
def centre(b): return V((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, (b.ZMin + b.ZMax) / 2)
def add(s, label, parent, color=None):
    n = doc.addObject('Part::Feature', 'Kin'); loc = s.copy()
    loc.Placement = frame_of_parent(parent).inverse().multiply(loc.Placement)
    n.Shape = loc; parent.addObject(n); n.Label = label
    if color and FreeCAD.GuiUp: n.ViewObject.ShapeColor = color
    return n
# ---------------------------------------------------------------- DXF -> solids
P = json.load(open(os.path.join(DL, "tanaes_trident_parts.json")))
def bulge_arc(a, b, bu):
    if abs(bu) < 1e-9: return Part.LineSegment(a, b).toShape()
    m = V((a.x + b.x) / 2 + bu / 2 * (b.y - a.y), (a.y + b.y) / 2 - bu / 2 * (b.x - a.x), 0)
    return Part.Arc(a, m, b).toShape()
def ent_edges(e):
    t = e[0]
    if t == "L": return [Part.LineSegment(V(*e[1], 0), V(*e[2], 0)).toShape()]
    if t == "C": return [Part.makeCircle(e[2], V(*e[1], 0))]
    if t == "A":
        s, en = math.radians(e[3]), math.radians(e[4])
        if en < s: en += 2 * math.pi
        return [Part.ArcOfCircle(Part.Circle(V(*e[1], 0), V(0, 0, 1), e[2]), s, en).toShape()]
    pts = e[1]; n = len(pts) if e[2] else len(pts) - 1
    return [bulge_arc(V(pts[i][0], pts[i][1], 0), V(pts[(i + 1) % len(pts)][0], pts[(i + 1) % len(pts)][1], 0), pts[i][2]) for i in range(n)]
def solid_of(key, keep=lambda e: True):
    edges = [x for e in P[key] if keep(e) for x in ent_edges(e)]
    groups = Part.sortEdges(edges)
    wires = [Part.Wire(g) for g in groups]
    bad = [w for w in wires if not w.isClosed()]
    if bad: raise RuntimeError(f"{key}: {len(bad)} open wires")
    f = Part.makeFace(wires, "Part::FaceMakerBullseye")
    s = f.extrude(V(0, 0, THK[key]))
    if not s.isValid() or len(s.Solids) != 1: raise RuntimeError(f"{key}: bad solid")
    return s
def circles(key, d=None, tol=0.02):
    return [(V(e[1][0], e[1][1], 0), 2 * e[2]) for e in P[key] if e[0] == "C" and (d is None or abs(2 * e[2] - d) < tol)]
def rects(key):   # the pin slots: plain 4-point closed polylines
    out = []
    for e in P[key]:
        if e[0] == "P" and len(e[1]) == 4 and all(abs(p[2]) < 1e-9 for p in e[1]):
            q = [V(p[0], p[1], 0) for p in e[1]]
            a, b = (q[1] - q[0]).Length, (q[2] - q[1]).Length
            ax = (q[1] - q[0]) if a > b else (q[2] - q[1]); ax.normalize()
            out.append((sum(q, V()) * 0.25, ax, max(a, b), min(a, b)))
    return out
# placements: R = 180 deg about Z, (x, y) -> (-x + cx, -y + cy);  M = mirror, (x, y) -> (x + cx, -y + cy)
def mp(mode, cx, cy):
    return (lambda p: V(-p.x + cx, -p.y + cy, 0)) if mode == "R" else (lambda p: V(p.x + cx, -p.y + cy, 0))
def place(s, mode, cx, cy, z):
    s = s.copy()
    if mode == "R": s.rotate(V(0, 0, 0), V(0, 0, 1), 180)
    else: s = s.mirror(V(0, 0, 0), V(0, 1, 0))
    s.translate(V(cx, cy, z)); return s
try:
    errs, notes = [], []
    def check(ok, msg):
        log(("  ok   " if ok else "  FAIL ") + msg)
        if not ok: errs.append(msg)
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    leaves0 = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: gbox(o) for o in leaves0}; label0 = {o.Name: o.Label for o in leaves0}
    pl0 = {o.Name: o.getGlobalPlacement() for o in leaves0}
    # ---- the model as it is
    gL, gR, gB = one("GE5C"), one("GE5C002"), one("GE5C001")
    cL, cR, cB = centre(gbox(gL)), centre(gbox(gR)), centre(gbox(gB))
    ring = [f for f in gshape(gL).Faces if f.Surface.TypeId == 'Part::GeomCylinder' and abs(f.Surface.Radius - 7.0) < 0.05]
    ring_h = max(f.BoundBox.ZLength for f in ring) if ring else None
    log(f"GE5C centres L {cL}  R {cR}  rear {cB}; outer ring height {ring_h}")
    check(ring_h is not None and abs(ring_h - 4.0) < 0.05, f"GE5C outer ring is 4 mm tall (GE5C: B 6, C 4)")
    fx, sp = one("2020 (1)"), one("2020 (2)")
    fb, sb = gbox(fx), gbox(sp); YC = (fb.YMin + fb.YMax) / 2; FT, ST = fb.ZMax, sb.ZMax; XS = (sb.XMin + sb.XMax) / 2
    log(f"front extrusion X {fb.XMin:.1f}..{fb.XMax:.1f}, slot centreline Y {YC:.2f}, top Z {FT}; spine X centre {XS:.2f}, Y {sb.YMin:.1f}..{sb.YMax:.1f}, top Z {ST}")
    plate = one("Universal Build Plate 350 v1"); ps = gshape(plate); pb = ps.BoundBox
    ph = sorted({(round(f.Surface.Center.x, 3), round(f.Surface.Center.y, 3)) for f in ps.Faces
                 if f.Surface.TypeId == 'Part::GeomCylinder' and abs(f.Surface.Radius - 1.7) < 0.01})
    hF = sorted([V(x, y, 0) for x, y in ph if abs(y - YC) < 5], key=lambda v: v.x)
    hR = [V(x, y, 0) for x, y in ph if abs(x - XS) < 2 and y > sb.YMax - 60]
    log(f"plate {pb}; front mount holes {[(round(h.x, 2), round(h.y, 2)) for h in hF]}; rear {[(round(h.x, 2), round(h.y, 2)) for h in hR]}")
    if len(hF) != 2 or len(hR) != 1: raise RuntimeError("plate mount holes not found")
    old_ball = next(o for o in leaves0 if o.Label == "Ball001"); old_nut = next(o for o in leaves0 if o.Label == "M3 thin hex nut002")
    bb_, nb_ = gbox(old_ball), gbox(old_nut)
    ball_flat = bb_.ZMax - (bb_.ZMin + BALL_D / 2)
    log(f"tanaes sphere nut: {bb_.XLength:.2f} wide, flat {ball_flat:.2f} above centre; thin hex nut {nb_.ZLength:.2f} thick")
    ball_src, nut_src = gshape(old_ball), gshape(old_nut)
    # ---- new bearing height: ring top = A/G top = extrusion top + 3
    zF = FT + THK["A"] - ring_h / 2; zB = ST + THK["G"] - ring_h / 2
    dF, dB = zF - cL.z, zB - cB.z
    check(abs(cR.z - cL.z) < 0.01, f"front GE5Cs level ({cL.z:.2f} / {cR.z:.2f})")
    log(f"GE5C centre: front {cL.z:.2f} -> {zF:.2f} ({dF:+.2f}); rear {cB.z:.2f} -> {zB:.2f} ({dB:+.2f})")
    # ---- delete the printed holders (GE5C + its M5x16 stay) and the V2.4 kinematic parts
    dels = []
    for g in ("Z_Bed_Left", "Z_Bed_Right", "Z_Bed_Rear"):
        for o in descendants(one(g)):
            # the printed holder and its screws only (these groups also hold a rail carriage, which stays)
            if is_leaf(o) and o.Label.startswith(("SOLID", "M5x10-Screw", "M3x6-Screw")) and o not in dels: dels.append(o)
    check(len(dels) == 18, f"18 holder solids/screws to delete ({len(dels)})")
    KG = one("Kinematic bed mount")
    kin_old = list({o.Name: o for o in descendants(KG)}.values())
    log("deleting:", ", ".join(o.Label for o in dels), "| V2.4:", ", ".join(o.Label for o in kin_old))
    for o in dels: doc.removeObject(o.Name)
    for o in reversed(kin_old):
        if doc.getObject(o.Name) is not None: doc.removeObject(o.Name)
    KG.Label = "Kinematic bed mount (tanaes Trident, laser-cut Al)"
    # ---- move bearings + Z carriages
    mgn = [o for o in doc.Objects if o.Label.startswith("MGN9H") and (o.isDerivedFrom('App::Part') or o.isDerivedFrom('App::DocumentObjectGroup'))]
    def nearest_mgn(c):
        best = None
        for g in mgn:
            ls = [x for x in descendants(g) if is_leaf(x)]
            if not ls: continue
            b = gbox(ls[0])
            for x in ls[1:]: b.add(gbox(x))
            d = math.hypot(centre(b).x - c.x, centre(b).y - c.y)
            if best is None or d < best[0]: best = (d, g)
        return best
    moves = []
    for side, g, dz, grps, scr in (("left", gL, dF, ["Z_Carriage_Left"], "M5x16-Screw067"),
                                   ("right", gR, dF, ["Z_Carriage_Right"], "M5x16-Screw069"),
                                   ("rear", gB, dB, ["Z_Carriage_Rear_2-hole (IGUS)", "Z_Carriage_Rear_3-Hole (Generic)"], "M5x16-Screw068")):
        d_, m_ = nearest_mgn(centre(gbox(g)))
        log(f"{side}: rail carriage {m_.Label} ({d_:.1f} mm from the GE5C)")
        if d_ > 60: errs.append(f"{side}: no rail carriage near the GE5C")
        objs = [g, one(scr)] + [one(x) for x in grps] + [m_]
        if side == "rear":
            cb = None
            for x in grps:
                for y in descendants(one(x)):
                    if is_leaf(y): cb = gbox(y) if cb is None else (cb.add(gbox(y)) or cb)
            ch = one("10x11 Chain Z"); chb = None
            for y in descendants(ch):
                if is_leaf(y): chb = gbox(y) if chb is None else (chb.add(gbox(y)) or chb)
            log(f"   rear: the Z cable chain (bolted to this carriage) moves with it; chain extent {chb}")
            objs += [ch]
        moves.append((side, V(0, 0, dz), objs))
    # contacts of the parts about to move, to find any that the move breaks (overlap checks can't see a gap opening)
    to_move = []
    for side, T, objs in moves:
        for o in objs: to_move += [x for x in ([o] + descendants(o)) if is_leaf(x)]
    to_move = list({x.Name: x for x in to_move}.values()); tm = {x.Name for x in to_move}
    contact0 = set(); cur = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    for a in to_move:
        sa = gshape(a); ba = gbox(a)
        for b in cur:
            if b.Name in tm or not ba.intersect(gbox(b)): continue
            try:
                if sa.distToShape(gshape(b))[0] < 0.05: contact0.add((a.Name, b.Name))
            except Exception: pass
    moved = {}
    for side, T, objs in moves:
        for o in objs:
            inner = [x.Name for x in ([o] + descendants(o)) if x.Name in moved]
            if inner: log(f"   {o.Label}: already moved with its group, skipped"); continue
            if o.isDerivedFrom('App::Part'):
                translate_global(o, T); ls = [x for x in descendants(o) if is_leaf(x)]
            elif o.isDerivedFrom('App::DocumentObjectGroup'):
                ls = [x for x in descendants(o) if is_leaf(x)]
                for x in ls: translate_global(x, T)
            else:
                translate_global(o, T); ls = [o]
            for x in ls: moved[x.Name] = T
    doc.recompute(); _BOX.clear()
    cL, cR, cB = centre(gbox(gL)), centre(gbox(gR)), centre(gbox(gB))
    # ---- the plates
    AL, ST_, SPR = (0.72, 0.73, 0.76), (0.55, 0.56, 0.6), (0.35, 0.36, 0.4)
    new = []; balls = []
    def boreof(key, d): return max(circles(key, d), key=lambda c: c[1])[0]
    def plate_add(key, mode, cx, cy, z, label=None):
        s = place(solid_of(key, (lambda e: e[0] == "P") if key == "J" else (lambda e: True)), mode, cx, cy, z)
        n = add(s, f"Trident kinematic {label or NAMES[key]} ({THK[key]:g} mm)", KG, SPR if key == "J" else AL)
        new.append(n); return n, mp(mode, cx, cy)
    # A (left, R), B (right, M), G (rear, R): bore on the GE5C
    a0 = boreof("A", 14.03); b0 = boreof("B", 14.03); g0 = boreof("G", 14.0); i0 = boreof("I", 12.0)
    _, mA = plate_add("A", "R", cL.x + a0.x, cL.y + a0.y, FT)
    _, mB = plate_add("B", "M", cR.x - b0.x, cR.y + b0.y, FT)
    _, mG = plate_add("G", "R", cB.x + g0.x, cB.y + g0.y, ST)
    _, mIL = plate_add("I", "R", cL.x + i0.x, cL.y + i0.y, FT + 3, "I bearing retain, left")
    _, mIR = plate_add("I", "M", cR.x - i0.x, cR.y + i0.y, FT + 3, "I bearing retain, right")
    _, mIB = plate_add("I", "R", cB.x + i0.x, cB.y + i0.y, ST + 3, "I bearing retain, rear")
    log("hole checks (bearing plates):")
    for k, m, c in (("A", mA, cL), ("B", mB, cR), ("G", mG, cB)):
        bore = m(boreof(k, 14.03 if k != "G" else 14.0))
        check(math.hypot(bore.x - c.x, bore.y - c.y) < 0.01, f"{k} bore on the GE5C ({bore.x:.2f}, {bore.y:.2f})")
    for k, m in (("A", mA), ("B", mB)):
        for h, d in circles(k, 5.5):
            p = m(h); check(abs(p.y - YC) < 0.05 and fb.XMin + 5 < p.x < fb.XMax - 5, f"{k} M5 at ({p.x:.2f}, {p.y:.2f}) on the front slot")
    for h, d in circles("G", 3.4):
        p = mG(h); check(abs(p.x - XS) < 0.5 and sb.YMin < p.y < sb.YMax - 5, f"G M3 at ({p.x:.2f}, {p.y:.2f}) on the spine slot ({p.x - XS:+.2f} off its centreline)")
    for k, m, mi in (("A", mA, mIL), ("B", mB, mIR), ("G", mG, mIB)):
        tap = sorted((m(h).x, m(h).y) for h, d in circles(k, 2.529))[:]
        tap = [t for t in tap if math.hypot(t[0] - m(boreof(k, 14.03 if k != 'G' else 14.0)).x, t[1] - m(boreof(k, 14.03 if k != 'G' else 14.0)).y) < 12]
        ih = [(mi(h).x, mi(h).y) for h, d in circles("I", 3.4)]
        miss = max(min(math.hypot(a[0] - b[0], a[1] - b[1]) for b in tap) for a in ih) if tap else 99
        check(len(tap) == 6 and miss < 0.01, f"I's 6 holes on {k}'s 6 tapped holes (worst {miss:.3f})")
    # ---- front sandwiches: E end holes on the slot centreline, groove through the bed hole
    def top_on_pins(top, sl, zbot_top):
        # the top plate's cutout edges bear on the pins (README: the pins are sandwiched between the plates), so it sits
        # where its cutout edge meets a pin resting in the bottom plate's slot
        w = sl[0][3]; zp = zbot_top + math.sqrt((PIN_D / 2) ** 2 - (w / 2) ** 2)
        f = solid_of(top).Faces; f0 = min((x for x in f if x.Surface.TypeId == 'Part::GeomPlane' and x.BoundBox.ZLength < 1e-6), key=lambda x: x.BoundBox.ZMin)
        dc = min(Part.LineSegment(c - ax * (PIN_L / 2), c + ax * (PIN_L / 2)).toShape().distToShape(Part.Compound(f0.Edges))[0] for c, ax, L, _w in sl)
        if dc >= PIN_D / 2: return zbot_top
        z = zp + math.sqrt((PIN_D / 2) ** 2 - dc ** 2)
        log(f"{top}: cutout edge {dc:.3f} from the pin axes, so it rests on the pins {z - zbot_top:.2f} above the bottom plate")
        return z
    def sandwich(top, bot, hole, side):
        sl = rects(bot)
        if len(sl) != 2: raise RuntimeError(f"{bot}: {len(sl)} pin slots")
        mc = (sl[0][0] + sl[1][0]) * 0.5; u = sl[0][1]
        ends = circles(bot, 3.4); ey = ends[0][0].y
        cy = YC + ey                                   # R: -ey + cy = YC
        p0y = -mc.y + cy; ux, uy = -u.x, -u.y
        cx = hole.x + mc.x - (hole.y - p0y) * ux / uy  # groove line through the hole
        nb, m = plate_add(bot, "R", cx, cy, FT)
        zt = top_on_pins(top, sl, FT + THK[bot]); nt, _ = plate_add(top, "R", cx, cy, zt)
        for h, d in ends:
            p = m(h); check(abs(p.y - YC) < 0.01 and fb.XMin < p.x < fb.XMax, f"{bot} end hole ({p.x:.2f}, {p.y:.2f}) on the front slot")
        tb = [(m(h).x, m(h).y) for h, d in circles(bot, 2.529)]; tt = [(m(h).x, m(h).y) for h, d in circles(top, 3.4)]
        miss = max(min(math.hypot(a[0] - b[0], a[1] - b[1]) for b in tt) for a in tb)
        check(miss < 0.01, f"{top}'s clamp holes on {bot}'s tapped pair (worst {miss:.3f})")
        miss2 = max(min(math.hypot(m(h).x - b[0], m(h).y - b[1]) for b in tt) for h, d in ends)
        check(miss2 < 0.01, f"{top}'s end holes on {bot}'s (worst {miss2:.3f})")
        tap = m(circles(top, 2.529)[0][0])
        return m, sl, FT + THK[bot], tap, V(ux, uy, 0), zt
    def rear():
        mH = mG
        sl = rects("G"); u = sl[0][1]
        zt = top_on_pins("H", sl, ST + THK["G"])
        n, _ = plate_add("H", "R", cB.x + g0.x, cB.y + g0.y, zt)
        th = [(mH(h).x, mH(h).y) for h, d in circles("H", 3.4)]; tg = [(mG(h).x, mG(h).y) for h, d in circles("G")]
        miss = max(min(math.hypot(a[0] - b[0], a[1] - b[1]) for b in tg) for a in th)
        check(miss < 0.01, f"H's 4 holes on G's holes (worst {miss:.3f})")
        return mG, sl, ST + THK["G"], mH(circles("H", 2.529)[0][0]), V(-u.x, -u.y, 0), zt
    mounts = [("front left", *sandwich("C", "E", hF[0], "left"), hF[0]),
              ("front right", *sandwich("D", "F", hF[1], "right"), hF[1]),
              ("rear", *rear(), hR[0])]
    # ---- pins, balls, nuts, springs
    centroid = V(sum(h.x for h in (hF[0], hF[1], hR[0])) / 3, sum(h.y for h in (hF[0], hF[1], hR[0])) / 3, 0)
    spring_dxf = [e for e in P["J"] if e[0] == "P"]
    outline = max(spring_dxf, key=lambda e: len(e[1]))
    oval = next(e for e in spring_dxf if len(e[1]) == 4 and any(abs(p[2]) > 1e-9 for p in e[1]))
    oc = V(sum(p[0] for p in oval[1]) / 4, sum(p[1] for p in oval[1]) / 4, 0)
    tip = max((V(p[0], p[1], 0) for p in outline[1]), key=lambda v: (v - oc).Length)
    tops = []
    for name, m, sl, ztop, tap, u, ztp, hole in mounts:
        w = sl[0][3]; zp = ztop + math.sqrt((PIN_D / 2) ** 2 - (w / 2) ** 2)
        axes = []
        for c, ax, L, _w in sl:
            pc = m(c); a = V(-ax.x, -ax.y, 0) if True else ax
            cyl = Part.makeCylinder(PIN_D / 2, PIN_L, pc - a * (PIN_L / 2) + V(0, 0, zp), a)
            new.append(add(cyl, f"Trident kinematic M5x20 dowel pin, {name}", KG, ST_)); axes.append(pc)
        sep = abs((axes[1] - axes[0]).cross(u).z)
        mid = (axes[0] + axes[1]) * 0.5
        t = (hole - mid).dot(u); bxy = mid + u * t
        zb = zp + math.sqrt((PIN_D / 2 + BALL_D / 2) ** 2 - (sep / 2) ** 2)
        bc = V(bxy.x, bxy.y, zb)
        b = ball_src.copy(); b.translate(bc - V(centre(bb_).x, centre(bb_).y, bb_.ZMin + BALL_D / 2))
        new.append(add(b, f"Trident kinematic 9 mm M3 sphere nut, {name}", KG, ST_))
        ztop_ball = zb + ball_flat
        nt = nut_src.copy(); nt.translate(V(bc.x - centre(nb_).x, bc.y - centre(nb_).y, ztop_ball - nb_.ZMin))
        new.append(add(nt, f"Trident kinematic M3 thin hex nut, {name}", KG, ST_))
        zs = ztop_ball + nb_.ZLength
        # spring: oval over the tapped hole, long axis toward the ball
        js = solid_of("J", lambda e: e[0] == "P")
        want = math.degrees(math.atan2(bc.y - tap.y, bc.x - tap.x)); have = math.degrees(math.atan2(tip.y - oc.y, tip.x - oc.x))
        js.translate(-oc); js.rotate(V(0, 0, 0), V(0, 0, 1), want - have); js.translate(V(tap.x, tap.y, zs))
        new.append(add(js, f"Trident kinematic J leaf spring, {name} (flat, before preload)", KG, SPR))
        inside = js.isInside(V(bc.x, bc.y, zs + THK["J"] / 2), 0.01, True)
        tops.append(zs + THK["J"])
        g_ang = math.degrees(math.atan2(u.y, u.x)) % 180
        c_ang = math.degrees(math.atan2(centroid.y - bc.y, centroid.x - bc.x)) % 180
        log(f"{name}: ball ({bc.x:.2f}, {bc.y:.2f}, {bc.z:.2f}); bed hole ({hole.x:.2f}, {hole.y:.2f}), off by {math.hypot(bc.x - hole.x, bc.y - hole.y):.2f}; "
            f"{t:+.2f} along the groove from its middle (pins +-{PIN_L / 2:.0f}); pins {sep:.2f} apart, centres Z {zp:.2f}; "
            f"groove {g_ang:.1f} deg, toward the 3-ball centroid {c_ang:.1f} deg; tapped hole to ball {math.hypot(bc.x - tap.x, bc.y - tap.y):.1f} mm; "
            f"ball bolt inside the spring: {inside}")
        check(math.hypot(bc.x - hole.x, bc.y - hole.y) < 0.6, f"{name} ball under the bed's mount hole")
        check(abs(t) < PIN_L / 2 - BALL_D / 4, f"{name} ball within the pins")
        notes.append((name, bc, hole, t, sep, g_ang, c_ang))
    check(max(tops) - min(tops) < 0.01, f"the three spring tops are level ({min(tops):.3f}..{max(tops):.3f})")
    # ---- plate: 10 mm, sitting on the springs
    zbot = max(tops)
    bot = min((f for f in ps.Faces if f.Surface.TypeId == 'Part::GeomPlane' and abs(f.BoundBox.ZLength) < 1e-6),
              key=lambda f: f.BoundBox.ZMin)
    thick = ps.fuse(bot.extrude(V(0, 0, -(PLATE_T - pb.ZLength)))).removeSplitter()
    thick.translate(V(0, 0, zbot - thick.BoundBox.ZMin))
    loc = thick.copy(); loc.Placement = container_global(plate).inverse().multiply(loc.Placement)
    plate.Shape = loc
    doc.recompute(); _BOX.clear()
    nb = gbox(plate)
    check(abs(nb.ZLength - PLATE_T) < 0.01 and len(gshape(plate).Solids) == 1, f"plate now {nb.ZLength:.2f} mm, one solid")
    log(f"plate: bottom {pb.ZMin:.2f} -> {nb.ZMin:.2f}, top {pb.ZMax:.2f} -> {nb.ZMax:.2f}; relative to the front Z carriages "
        f"the top moved {nb.ZMax - pb.ZMax - dF:+.2f} (rear carriage {nb.ZMax - pb.ZMax - dB:+.2f})")
    # ---- materials
    try:
        import Materials
        mm = Materials.MaterialManager()
        st_m = mm.getMaterial("90bbd8ef-8623-4d78-b3bf-e0bdb9b74dd3"); al_m = mm.getMaterial("9bf060e9-1663-44a2-88e2-2ff6ee858efe")
        for n in new:
            col = n.ViewObject.ShapeColor if FreeCAD.GuiUp else None
            n.ShapeMaterial = al_m if " mm)" in n.Label and "spring" not in n.Label else st_m
            if col and FreeCAD.GuiUp: n.ViewObject.ShapeColor = col
    except Exception as e: log("materials not set:", e)
    doc.recompute(); _BOX.clear()
    # ---- verify
    now = {o.Name: o for o in doc.Objects if is_leaf(o)}; allnow = list(now.values())
    newn = {n.Name for n in new}
    chk = new + [now[x] for x in moved] + [plate]
    seen = set(); ov = []
    for a in chk:
        sa = None
        for b in allnow:
            if a.Name == b.Name or (b.Name, a.Name) in seen or not gbox(a).intersect(gbox(b)): continue
            seen.add((a.Name, b.Name))
            if a.Name in moved and b.Name in moved: continue
            try:
                sa = sa or gshape(a); v = sa.common(gshape(b)).Volume
            except Exception: continue
            if v > 0.5:
                v0 = 0.0
                ma, mb = moved.get(a.Name), moved.get(b.Name)
                if (ma or mb) and a.Name not in newn and b.Name not in newn and a.Name != plate.Name and b.Name != plate.Name:
                    s0 = gshape(a); s0.translate(-ma) if ma else None
                    s1 = gshape(b); s1.translate(-mb) if mb else None
                    try: v0 = s0.common(s1).Volume
                    except Exception: v0 = 0.0
                if v - v0 > 0.5: ov.append((v, a, b))
                elif v0: log(f"     (already overlapping before the move: {a.Label} x {b.Label} {v0:.2f} mm3)")
    log(f"overlaps > 0.5 mm3 involving new/moved parts: {len(ov)}")
    for v, a, b in sorted(ov, key=lambda x: -x[0]):
        log(f"     {v:9.2f} mm3  {a.Label} x {b.Label} [{parent_of(b).Label if parent_of(b) else ''}]")
        errs.append(f"{a.Label} overlaps {b.Label} ({v:.2f} mm3)")
    broken = []
    for a_, b_ in sorted(contact0):
        if a_ not in now or b_ not in now: continue
        d = gshape(now[a_]).distToShape(gshape(now[b_]))[0]
        if d >= 0.05: broken.append((d, now[a_].Label, now[b_].Label, parent_of(now[b_]).Label if parent_of(now[b_]) else ''))
    log(f"contacts broken by the moves: {len(broken)}")
    for d, a_, b_, pb_ in broken:
        log(f"     {d:6.2f} mm gap  {a_} / {b_} [{pb_}]"); errs.append(f"move opened a gap: {a_} / {b_} ({d:.2f} mm)")
    deleted = {o for o in before if o not in now}
    exp_del = {label0[n] for n in deleted}
    log(f"deleted {len(deleted)} solids")
    for nm, b in before.items():
        if nm not in now: continue
        if nm == plate.Name: continue
        T = moved.get(nm, V()); p1 = now[nm].getGlobalPlacement()
        if (p1.Base - pl0[nm].Base - T).Length > 1e-6 or not p1.Rotation.isSame(pl0[nm].Rotation, 1e-9):
            g_ = gbox(now[nm]); errs.append(f"changed: {now[nm].Label} (moved {g_.ZMin - b.ZMin:+.3f} in Z, expected {(moved[nm].z if nm in moved else 0):+.3f}; X {g_.XMin - b.XMin:+.3f}, Y {g_.YMin - b.YMin:+.3f}) [{parent_of(now[nm]).Label if parent_of(now[nm]) else ''}]")
    log(f"added {len(new)} parts, moved {len(moved)}")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
