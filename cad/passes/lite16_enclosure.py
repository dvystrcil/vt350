# GUI pass: vt350-lite-15.FCStd -> vt350-lite-16.FCStd   (headless = dry run, never saves)
# Enclosure extras: insulation, chamber camera, chamber lights.
#  Insulation: the user's 3 carbon-felt welding pads (10 mm, 508 x 508 mm each). Each sheet is sealed in 0.5 mm
#   aluminium (liner on both faces, foil tape on the edges), so no fibres get out. Roof and back go on the OUTSIDE of
#   their panels: no chamber space lost and the panel clips only hold the panel. The right wall faces the electronics,
#   so its sheet sits between the side panel and the electronics. Cut plan: pad 1 = roof; pad 2 = back (top 508 mm);
#   pad 3 = a 470 x 42 roof strip + 508 x 466 for the right wall.
#  Camera: Luke's Laboratory Nocturne (38 x 38 mm board, 96 deg diagonal FOV, 1080p, rated -20..+70 C), in a printed
#   housing (Printables 305428, public domain: camera_front_cover-v4 + camera_case_back_cover-v1, read from
#   $VT350_DL/dl_camhousing, not in git), top front centre, aimed at the build plate's centre. Visibility is checked by rays to a grid on the plate
#   at the top and bottom of the bed's travel, against every solid in the model (heads parked).
#  Lights: 24 V warm-white COB strip (3500-4000 K, CRI 90+) in 16 x 8 mm aluminium channel under the left and right
#   top extrusions.
import FreeCAD, Part, sys, os, time, traceback, math
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
DL = os.environ.get("VT350_DL", "/tmp/claude-1000/-home-dan-Code/49170e9e-d71c-4cd7-8f69-23f113691ee5/scratchpad")
CAM_DIR = os.path.join(DL, "dl_camhousing")
SRC = "/home/dan/Documents/VT350/vt350-lite-15.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-16.FCStd"
DRY = not FreeCAD.GuiUp
PAD, FELT, LINER, PANEL = 508.0, 10.0, 0.5, 3.0
# chamber openings (inside faces of the frame): X -480..-10, Y -70..480, Z -10..650; frame outer X -520..30, Y -90..520, Z -50..690
SHEETS = [  # label, (x0, x1, y0, y1, z0, z1) of the FELT, which pad
    ("Roof felt (pad 1)",            (-480, -10, -70, 438, 693.5, 703.5)),
    ("Roof felt strip (pad 3)",      (-480, -10, 438, 480, 693.5, 703.5)),
    ("Back felt (pad 2)",            (-480, -10, 508.5, 518.5, 142, 650)),
    ("Right wall felt (pad 3)",      (33.5, 43.5, -28, 480, -10, 456)),
]
PANELS = [  # new panels (the back panel already exists)
    ("Roof panel (3 mm)",            (-520, 30, -90, 520, 690, 693)),
    ("Right side panel (3 mm)",      (30, 33, -76, 520, -50, 690)),   # starts behind the door latch (Y -77)
]
CAM_C, CAM_FOV, CAM_AR = V(-245.0, -52.0, 628.0), 96.0, 16 / 9
PLATE = (-422.5, -67.5, 28.0, 388.5)           # build plate X/Y
BED_Z = (271.0, 380.8 - 0.2, 33.0)              # plate top now, at the top of travel (first layer), near the bottom
LED = [("LED channel left (24 V COB, warm white)", (-480, -464, -20, 470, 642, 650)),
       ("LED channel right (24 V COB, warm white)", (-26, -10, -20, 470, 642, 650))]
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite16_enclosure.log", "w"); t0 = time.time()
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
    """global placement of the coordinate frame a child of `par` lives in"""
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
def box(b):
    x0, x1, y0, y1, z0, z1 = b; return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
def add(s, label, parent, color=None):
    n = doc.addObject('Part::Feature', 'Encl'); loc = s.copy()
    loc.Placement = frame_of_parent(parent).inverse().multiply(loc.Placement)
    n.Shape = loc; parent.addObject(n); n.Label = label
    if color and FreeCAD.GuiUp: n.ViewObject.ShapeColor = color
    return n
try:
    errs, notes = [], []
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    leaves0 = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: gbox(o) for o in leaves0}; label0 = {o.Name: o.Label for o in leaves0}
    G = doc.addObject('App::Part', 'Enclosure'); G.Label = "Enclosure extras (lite-16)"
    Gi = doc.addObject('App::Part', 'Insul'); Gi.Label = "Insulation: carbon felt sealed in aluminium"; G.addObject(Gi)
    new = []
    for lab, b in PANELS:
        new.append(add(box(b), lab, G, (0.75, 0.75, 0.78)))
    for lab, b in SHEETS:
        x0, x1, y0, y1, z0, z1 = b
        dims = sorted([x1 - x0, y1 - y0, z1 - z0])
        if abs(dims[0] - FELT) > 1e-6: errs.append(f"{lab}: felt not {FELT} mm thick")
        if dims[1] > PAD + 1e-6 or dims[2] > PAD + 1e-6: errs.append(f"{lab}: {dims[2]:.0f} x {dims[1]:.0f} is bigger than a pad")
        felt = box(b)
        # thin axis -> liners on both faces
        ax = [x1 - x0, y1 - y0, z1 - z0].index(dims[0])
        lo = list(b); hi = list(b)
        lo[2 * ax + 1] = lo[2 * ax]; lo[2 * ax] -= LINER
        hi[2 * ax] = hi[2 * ax + 1]; hi[2 * ax + 1] += LINER
        new.append(add(felt, lab, Gi, (0.12, 0.12, 0.12)))
        new.append(add(box(lo), lab.split(" (")[0] + " liner, inner", Gi, (0.85, 0.85, 0.88)))
        new.append(add(box(hi), lab.split(" (")[0] + " liner, outer", Gi, (0.85, 0.85, 0.88)))
        log(f"{lab}: {dims[2]:.0f} x {dims[1]:.0f} mm, area {dims[2] * dims[1] / 1e6:.3f} m2")
    # pad accounting
    use = {}
    for lab, b in SHEETS:
        p = lab.split("(")[1].rstrip(")"); x0, x1, y0, y1, z0, z1 = b
        d = sorted([x1 - x0, y1 - y0, z1 - z0]); use[p] = use.get(p, 0) + d[1] * d[2]
    for p, a in sorted(use.items()):
        log(f"{p}: {a / 1e6:.3f} of {PAD * PAD / 1e6:.3f} m2 used"); 
        if a > PAD * PAD + 1: errs.append(f"{p} over-used")
    # camera: board + printed housing, aimed at the plate centre (mid travel)
    half_d = math.radians(CAM_FOV / 2); k = math.tan(half_d) / math.hypot(CAM_AR, 1)
    def cam_rot(t):
        z = t - CAM_C; z.normalize(); x = z.cross(V(0, 0, 1)); x.normalize(); y = z.cross(x)
        return FreeCAD.Rotation(x, y, z, "ZXY")   # local +Z = view, local X = horizontal (no roll)
    def framed(rot, bz, N=9):
        inv = rot.inverted(); n = 0
        for i in range(N):
            for j in range(N):
                p = V(PLATE[0] + (PLATE[1] - PLATE[0]) * i / (N - 1), PLATE[2] + (PLATE[3] - PLATE[2]) * j / (N - 1), bz)
                q = inv.multVec(p - CAM_C)
                if q.z > 0 and abs(q.x / q.z) <= k * CAM_AR and abs(q.y / q.z) <= k: n += 1
        return n
    best = None
    for ty in range(int(PLATE[2]), int(PLATE[3]) + 1, 10):
        for tz in range(int(BED_Z[2]) - 100, int(BED_Z[1]) + 1, 10):
            t = V((PLATE[0] + PLATE[1]) / 2, ty, tz); r = cam_rot(t)
            sc = (min(framed(r, BED_Z[1]), framed(r, BED_Z[2])), framed(r, BED_Z[1]) + framed(r, BED_Z[2]))
            if best is None or sc > best[0]: best = (sc, t)
    tgt = best[1]; rot = cam_rot(tgt); d = tgt - CAM_C; d.normalize()
    log(f"camera aim search: best frames {best[0][0]}/81 of the plate at worst bed height")
    # housing parts in a local frame: lens at the origin looking +Z (the STEPs look -Z, lens bore centred at x -88)
    flip = FreeCAD.Placement(V(0, 0, 0), FreeCAD.Rotation(V(1, 0, 0), 180))
    front = Part.read(os.path.join(CAM_DIR, "camera_front_cover-v4.step")); front.translate(V(88, 0, 0))
    front = front.transformGeometry(flip.toMatrix())                   # now z -15.8..0, front face at z 0
    back = Part.read(os.path.join(CAM_DIR, "camera_case_back_cover-v1.step"))
    back = back.transformGeometry(flip.toMatrix()); back.translate(V(0, 0, -15.8))   # z -20.5..-15.8
    board = Part.makeBox(38, 38, 1.6, V(-19, -19, -9.0))                # the camera PCB (38 x 38) inside the cover
    lens = Part.makeCylinder(7.0, 7.0, V(0, 0, -7.4))                    # lens barrel up to the bore
    place = FreeCAD.Placement(CAM_C, rot)
    for shp, lab, col in ((front, "Camera housing front (Printables 305428, public domain)", (0.15, 0.15, 0.15)),
                          (back, "Camera housing back (Printables 305428, public domain)", (0.15, 0.15, 0.15)),
                          (board, "Nocturne USB camera board (Luke's Laboratory, 96 deg FOV)", (0.0, 0.35, 0.1)),
                          (lens, "Nocturne lens", (0.02, 0.02, 0.02))):
        g = shp.copy(); g.Placement = place.multiply(g.Placement); new.append(add(g, lab, G, col))
    for lab, b in LED:
        new.append(add(box(b), lab, G, (1.0, 0.85, 0.6)))
    doc.recompute(); _BOX.clear()
    # ---- collisions: new parts vs everything else
    now = {o.Name: o for o in doc.Objects if is_leaf(o)}; allnow = list(now.values())
    newn = {n.Name for n in new}
    ov = overlaps(new, allnow, skip=lambda a, b: b.Name in newn)
    log(f"new parts vs the printer: {len(ov)} overlaps > 1 mm3")
    holes = []
    for (a_, b_), v in sorted(ov.items(), key=lambda kv: -kv[1]):
        A, B = now[a_], now[b_]
        if B.Label.startswith("Bowden") and ("Roof" in A.Label):
            holes.append((A.Label, B.Label, gbox(B))); continue
        log(f"     {v:9.1f} mm3  {A.Label} x {B.Label} [{parent_of(B).Label if parent_of(B) else ''}]")
        errs.append(f"{A.Label} overlaps {B.Label} ({v:.1f} mm3)")
    for lab_a, lab_b, bb in holes:
        log(f"   pass-through needed: {lab_b} crosses {lab_a}")
    tubes = [o for o in allnow if o.Label.startswith("Bowden ")]
    for t in tubes:
        s = gshape(t); sec = s.common(box((-520, 30, -90, 520, 690, 693)))
        if sec.Volume > 0:
            c = sec.BoundBox.Center; log(f"   roof hole for {t.Label}: centre ({c.x:.1f}, {c.y:.1f}), cut {max(sec.BoundBox.XLength, sec.BoundBox.YLength) + 4:.0f} mm across (tube + 2 mm each side)")
    # ---- camera view
    hfov, vfov = 2 * math.degrees(math.atan(k * CAM_AR)), 2 * math.degrees(math.atan(k))
    log(f"camera at ({CAM_C.x:.0f}, {CAM_C.y:.0f}, {CAM_C.z:.0f}), aimed at ({tgt.x:.0f}, {tgt.y:.0f}, {tgt.z:.0f}); "
        f"16:9 FOV {hfov:.1f} x {vfov:.1f} deg (from {CAM_FOV} deg diagonal)")
    inv = rot.inverted()
    up = rot.multVec(V(0, 1, 0)); right = rot.multVec(V(1, 0, 0))
    lens_pt = CAM_C + d * 0.5
    blockers = [o for o in allnow if o.Name not in newn or o.Label.startswith("LED")]
    bb_block = [(o, gbox(o)) for o in blockers]
    N = 9
    for bz in BED_Z:
        inside = vis = 0; blocked_by = {}
        for i in range(N):
            for j in range(N):
                p = V(PLATE[0] + (PLATE[1] - PLATE[0]) * i / (N - 1), PLATE[2] + (PLATE[3] - PLATE[2]) * j / (N - 1), bz + 0.05)
                q = inv.multVec(p - lens_pt)
                if q.z <= 0 or abs(q.x / q.z) > k * CAM_AR or abs(q.y / q.z) > k: continue
                inside += 1
                seg = Part.LineSegment(lens_pt, p).toShape(); sb = seg.BoundBox
                hit = None
                for o, ob in bb_block:
                    if o.Label.startswith("Universal Build Plate") or not ob.intersect(sb): continue
                    try:
                        if seg.common(gshape(o)).Length > 0.2: hit = o; break
                    except Exception: pass
                if hit is None: vis += 1
                elif hit.Label.startswith(("Camera", "Nocturne")): vis += 1
                else:
                    k2 = hit.Label if not parent_of(hit) else parent_of(hit).Label
                    blocked_by[k2] = blocked_by.get(k2, 0) + 1
        log(f"plate at Z {bz:.1f}: {inside}/{N * N} grid points in frame, {vis} visible; blocked by: " +
            (", ".join(f"{k_} {n}" for k_, n in sorted(blocked_by.items(), key=lambda kv: -kv[1])[:6]) or "nothing"))
        notes.append((bz, inside, vis))
        if inside < N * N * 0.9: errs.append(f"camera frames only {inside}/{N * N} of the plate at Z {bz}")
    # ---- verify the rest is untouched
    for nm, b in before.items():
        if nm not in now: errs.append(f"lost {label0[nm]}"); continue
        if not close(gbox(now[nm]), b): errs.append(f"changed: {now[nm].Label}")
    log(f"added {len(new)} parts")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
