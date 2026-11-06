# GUI pass: vt350-lite-24.FCStd -> vt350-lite-25.FCStd   (headless = dry run, never saves)   #58 AC3
# The belts are 9 mm (Gates GT2 RF, Monolith 9 mm pulleys), but andrewmcgr's MadMax carriage (the one with the
# Beacon/Cartographer pocket, lite-24) is the stock 6 mm-belt carriage, and its SpeedClips are "4mm Gap 6mm Belt".
# Upstream MadMax publishes the 9 mm version of both (zruncho3d/madmax @ 6bf670d, GPL-3.0):
#   STL/Carriage_MGN12H_9mm.stl, STL/SpeedClip_4mm_Gap_9mm.stl   (read from $VT350_MADMAX; not in git)
# The 9 mm carriage differs from the 6 mm one ONLY in the two belt-clip pockets (taller: 20 -> 26 mm, same centre line,
# same depth profile). So the remix swaps those two pockets and keeps everything else, including andrewmcgr's probe
# pocket and lite-24's Beacon ceiling cut:
#   C' = (C - R) u (Carriage_MGN12H_9mm n R),  R = two boxes around the belt pockets (STL frame below)
# on the gantry carriage AND on both docks' carriage copies (same part; the copies are the carriage at pickup).
# Each 6 mm SpeedClip is replaced by the 9 mm one: the old clip is registered to SpeedClip_4mm_Gap.stl (reglib), and
# the 9 mm clip goes in at the same place, centred on the same pocket centre (it's the same clip, 6 mm taller).
# Checks (refuses to save on any):
#  - the STL->model frame of the carriage: andrewmcgr's STL vertices lie on the lite-24 carriage (except in the Beacon
#    ceiling cut), within TOL;
#  - R holds every 6-vs-9 mm difference and none of andrewmcgr's changes (vertex sets, STL frame);
#  - each dock copy = gantry carriage + its offset inside R, before the change;
#  - volumes: C' = C - (C n R) + (9mm n R); valid solids, same solid count;
#  - clips registered within TOL; new clips overlap the new carriage no more than the old clips did the old one;
#    belts overlap the new carriage no more than before;
#  - every other solid unchanged.
# Also writes the printable carriage to cad/derived/ in the upstream STL's own frame (GPL-3.0).
import FreeCAD, Part, Mesh, MeshPart, sys, os, time, traceback
import numpy as np
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path.insert(0, f"{REPO}/cad/scripts")
from reglib import register, moved, dists
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", f"{REPO}/cad/data")
UP = os.environ.get("VT350_MADMAX", "/home/dan/Documents/VT350/downloads/upstream/madmax-6bf670d")
SRC = "/home/dan/Documents/VT350/vt350-lite-24.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-25.FCStd"
OUT_STL = f"{REPO}/cad/derived/madmax-andrewmcgr-carriage-beacon/MadMaxCarriage Beacon RevH pocket 9mm belts.stl"
DRY = not FreeCAD.GuiUp
TOL = 0.05
CLIP_OV = 5.0                              # mm3, flush clip-in-pocket fit of two meshes (see the clip check)
CARRIAGE = ("Carriage (1)", "COMPOUND")
COPIES = {"Left": ("Left Dock", "COMPOUND003"), "Right": ("Right Dock", "COMPOUND004")}
CLIP_GROUP = "4mm Gap 6mm Belt"            # label prefix of each old clip's group
BELTS = ("GT2 9mm belt, lower (Monolith 2WD)", "GT2 9mm belt, upper (Monolith 2WD)")
# swap boxes in the carriage STL frame (bounding-box minimum at 0; X width 54.4, Y height 63.5 from the top, Z depth
# 12.6 from the front face): the two belt-clip pockets, full depth
R_BOXES = [((-1.0, 1.5, -1.0), (12.5, 31.0, 13.6)), ((41.9, 1.5, -1.0), (55.4, 31.0, 13.6))]
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite25_carriage_9mm.log", "w"); t0 = time.time()
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
def container_global(o):
    for p in ancestors(o):
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
    return FreeCAD.Placement()
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax), (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
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
def com(s):
    vs = [(x.Volume, x.CenterOfMass) for x in s.Solids]; tv = sum(v for v, _ in vs)
    return sum((c * (v / tv) for v, c in vs), V(0, 0, 0))
def load_mesh(fn, zero=True):
    m = Mesh.Mesh(os.path.join(UP, fn)); b = m.BoundBox
    if zero: m.translate(-b.XMin, -b.YMin, -b.ZMin)
    return m, b
def mesh_solid(m):
    s = Part.Shape(); s.makeShapeFromMesh(m.Topology, 0.05)
    sol = Part.Solid(Part.Shell(s.Faces))
    if sol.Volume < 0: sol.reverse()
    return sol
def vset(m): return {(round(p.x, 2), round(p.y, 2), round(p.z, 2)) for p in m.Points}
def in_R(p, m=0.0):
    return any(all(lo[i] - m <= p[i] <= hi[i] + m for i in range(3)) for lo, hi in R_BOXES)
def matrix(rows, t):
    M = FreeCAD.Matrix()
    (M.A11, M.A12, M.A13), (M.A21, M.A22, M.A23), (M.A31, M.A32, M.A33) = rows
    M.A14, M.A24, M.A34 = t
    return M
def xformed(sh, M):
    r = sh.copy()
    if M.determinant() > 0: r.transformShape(M, True)
    else: r = r.transformGeometry(M)
    return r

try:
    errs, finds = [], []
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    leaves0 = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: gbox(o) for o in leaves0}; label0 = {o.Name: o.Label for o in leaves0}
    car = one(CARRIAGE[1], CARRIAGE[0]); C = gshape(car); cb = gbox(car)
    copies = {k: one(c, d) for k, (d, c) in COPIES.items()}
    T = {k: com(gshape(c)) - com(C) for k, c in copies.items()}
    for k, t in T.items(): log(f"{k}: dock carriage copy = gantry carriage + ({t.x:.3f}, {t.y:.3f}, {t.z:.3f})")
    log(f"gantry carriage: {len(C.Solids)} solids, volume {C.Volume:.1f}; X {cb.XMin:.2f}..{cb.XMax:.2f} Y {cb.YMin:.2f}..{cb.YMax:.2f} Z {cb.ZMin:.2f}..{cb.ZMax:.2f}")

    # --- upstream meshes, STL frame (bbox minimum at 0)
    mA, bA = load_mesh("MadMaxCarriage.stl")          # bA: its original bounding box (the printable STL goes back there)
    m6, _ = load_mesh("Carriage_MGN12H.stl"); m9, _ = load_mesh("Carriage_MGN12H_9mm.stl")
    for nm, m in (("andrewmcgr", mA), ("6mm", m6), ("9mm", m9)):
        b = m.BoundBox; log(f"STL {nm}: {b.XLength:.2f} x {b.YLength:.2f} x {b.ZLength:.2f}, {m.CountFacets} facets")
        if abs(b.XLength - 54.4) > 0.01 or abs(b.YLength - 63.5) > 0.01 or abs(b.ZLength - 12.6) > 0.01: errs.append(f"{nm} carriage STL size")
    A, S6, S9 = vset(mA), vset(m6), vset(m9)
    mods = [p for p in A - S6 if in_R(p, 0.3)]
    log(f"andrewmcgr's changes vs the stock 6 mm carriage: {len(A - S6)} vertices, {len(mods)} inside R (+0.3)")
    if mods: errs.append(f"{len(mods)} of andrewmcgr's changed vertices are inside the swap boxes")
    out6 = [p for p in S6 - S9 if not in_R(p)]; out9 = [p for p in S9 - S6 if not in_R(p)]
    s6, s9 = mesh_solid(m6), mesh_solid(m9)
    far = [(p, s9.distToShape(Part.Vertex(V(*p)))[0]) for p in out6] + [(p, s6.distToShape(Part.Vertex(V(*p)))[0]) for p in out9]
    far = [(p, d) for p, d in far if d > 0.02]
    log(f"6-vs-9 mm differences: {len(S6 - S9)} / {len(S9 - S6)} vertices; outside R {len(out6)} / {len(out9)}, of which "
        f"{len(far)} are off the other carriage's surface by > 0.02 mm (the rest are re-triangulation of the same faces)")
    if far: errs.append(f"6-vs-9 mm geometry differs outside the swap boxes: {far[:5]}")
    log(f"stock carriage volumes: 6 mm {s6.Volume:.1f}, 9 mm {s9.Volume:.1f}; in R: 6 mm "
        f"{sum(s6.common(Part.makeBox(*(h[i]-l[i] for i in range(3)), V(*l))).Volume for l, h in R_BOXES):.1f}, 9 mm "
        f"{sum(s9.common(Part.makeBox(*(h[i]-l[i] for i in range(3)), V(*l))).Volume for l, h in R_BOXES):.1f}")

    # --- STL frame -> model frame of the gantry carriage: X along X, height down -Z from the top, depth +Y from the
    # front face. Verified on andrewmcgr's STL against the lite-24 carriage (Beacon ceiling cut excepted).
    best = None
    for name, rows, t in (("proper", ((1, 0, 0), (0, 0, 1), (0, -1, 0)), (cb.XMin, cb.YMin, cb.ZMax)),
                          ("mirrored X", ((-1, 0, 0), (0, 0, 1), (0, -1, 0)), (cb.XMax, cb.YMin, cb.ZMax))):
        M = matrix(rows, t)
        P = [M.multiply(V(*p)) for p in list(A)[::40]]
        d = np.array([C.distToShape(Part.Vertex(p))[0] for p in P])
        zc = np.array([p.z for p in P])
        keep = zc > cb.ZMin + 14.0                       # above the Beacon pocket (ceiling cut is in the bottom 14 mm)
        log(f"frame {name}: {len(P)} sample vertices; above the Beacon pocket max {d[keep].max():.4f} median {np.median(d[keep]):.4f}; "
            f"all max {d.max():.4f}")
        if best is None or d[keep].max() < best[0]: best = (d[keep].max(), name, M)
    if best[0] > TOL: raise RuntimeError(f"no STL->model frame fits the carriage (best {best[1]} {best[0]:.4f})")
    _, fname, M = best
    if fname != "proper": errs.append("carriage STL maps by a mirror: check before using it")
    log(f"carriage STL frame: {fname} (max {best[0]:.4f} mm)")

    # --- the swap, gantry carriage
    Rm = Part.makeCompound([xformed(Part.makeBox(*(h[i] - l[i] for i in range(3)), V(*l)), M) for l, h in R_BOXES])
    s9m = xformed(s9, M)
    s9R = s9m.common(Rm)
    FZ = 1e-3
    def vc(a, b): return a.common(b).Volume
    rng = np.random.default_rng(25)
    def mismatch(A, B, boxes, n=800):
        """points sampled in the boxes where A and B disagree on inside/outside (points within 0.02 of either surface
        skipped). Booleans of coincident copies are unreliable here (OCC returned 0 or negative volumes)."""
        bad, tested = 0, 0
        for bx in boxes.Solids:
            b = bx.BoundBox
            P = rng.uniform((b.XMin, b.YMin, b.ZMin), (b.XMax, b.YMax, b.ZMax), size=(n, 3))
            for q in P:
                v = V(*q); ia = A.isInside(v, 1e-4, True); ib = B.isInside(v, 1e-4, True); tested += 1
                if ia != ib and min(A.distToShape(Part.Vertex(v))[0], B.distToShape(Part.Vertex(v))[0]) > 0.02: bad += 1
        return bad, tested
    I = FreeCAD.Matrix()
    def swap(shape, Mx):
        rr = xformed(Rm, Mx); add = xformed(s9R, Mx)
        new = []
        for so in shape.Solids:
            if so.BoundBox.intersect(rr.BoundBox) and vc(so, rr) > 1e-6:
                new += so.cut(rr).fuse(add).Solids
            else: new.append(so)
        return Part.makeCompound(new) if len(new) > 1 else new[0]
    C_in = vc(C, Rm)
    C2 = swap(C, I)
    exp = C.Volume - C_in + s9R.Volume
    log(f"gantry carriage: in R before {C_in:.1f}, 9 mm pockets in R {s9R.Volume:.1f}; after {C2.Volume:.1f} (expected {exp:.1f}); "
        f"valid {C2.isValid()}, solids {len(C2.Solids)} (was {len(C.Solids)})")
    if abs(C2.Volume - exp) > 0.5 or not C2.isValid() or len(C2.Solids) != len(C.Solids): errs.append("gantry carriage swap failed its checks")
    bad, tested = mismatch(C2, s9R, Rm)
    log(f"gantry carriage in R after vs the 9 mm pockets: {bad} of {tested} sample points disagree")
    if bad: errs.append(f"gantry carriage in R differs from the 9 mm carriage at {bad} sample points")
    finds.append(f"carriage: belt-clip pockets swapped for upstream's 9 mm ones ({C_in:.1f} -> {s9R.Volume:.1f} mm3 in the pocket boxes; "
                 f"part {C.Volume:.1f} -> {C2.Volume:.1f} mm3)")
    newshape = {car.Name: C2}
    for k, c in copies.items():
        s0 = gshape(c); b0 = gbox(c)
        cands = []
        for how in ("offset", "mirror"):
            Mx = FreeCAD.Matrix()
            if how == "offset": Mx.A14, Mx.A24, Mx.A34 = b0.XMin - cb.XMin, b0.YMin - cb.YMin, b0.ZMin - cb.ZMin
            else: Mx.A11 = -1; Mx.A14, Mx.A24, Mx.A34 = b0.Center.x + cb.Center.x, b0.YMin - cb.YMin, b0.ZMin - cb.ZMin
            rr = xformed(Rm, Mx); cm = xformed(C, Mx)
            a = vc(s0, rr); bad, tested = mismatch(s0, cm, rr, 300); sym = bad
            log(f"{k} copy as gantry carriage {how}: inside R copy {a:.1f} mm3; {bad} of {tested} sample points disagree")
            cands.append((sym, how, Mx, a))
        sym, how, Mx, a = min(cands, key=lambda q: q[0])
        if sym > 0: errs.append(f"{k} copy is not the gantry carriage (offset or mirror) inside R: {sym} points"); continue
        n = swap(s0, Mx)
        e = s0.Volume - a + s9R.Volume
        log(f"{k} copy ({how}) after: {n.Volume:.1f} (expected {e:.1f}), valid {n.isValid()}, solids {len(n.Solids)}")
        if abs(n.Volume - e) > 0.5 or not n.isValid() or len(n.Solids) != len(s0.Solids): errs.append(f"{k} copy swap failed its checks")
        newshape[c.Name] = n

    # --- clips
    m6c, _ = load_mesh("SpeedClip_4mm_Gap.stl"); m9c, _ = load_mesh("SpeedClip_4mm_Gap_9mm.stl")
    c6, c9 = m6c.BoundBox.Center, m9c.BoundBox.Center
    m9c.translate(c6.x - c9.x, c6.y - c9.y, c6.z - c9.z)              # same clip centre (it grows 3 mm each way in Y)
    sc9 = mesh_solid(m9c)
    mir = FreeCAD.Matrix(); mir.A11 = -1
    m6m = Mesh.Mesh(m6c); m6m.transform(mir); sc9m = sc9.transformGeometry(mir)
    clips = [o for o in leaves0 if any(a.Label.startswith(CLIP_GROUP) for a in ancestors(o))]
    log(f"old clips: {len(clips)}: {[o.Label for o in clips]}")
    if len(clips) != 6: errs.append(f"{len(clips)} old clips, expected 6 (gantry + 2 dock copies)")
    owner = {}
    for o in clips:
        anc = [a.Label for a in ancestors(o)]
        owner[o.Name] = car.Name if CARRIAGE[0] in anc else copies["Left"].Name if "Left Dock" in anc else copies["Right"].Name
    oldC = {car.Name: C, copies["Left"].Name: gshape(copies["Left"]), copies["Right"].Name: gshape(copies["Right"])}
    for o in clips:
        so = gshape(o); fits = []
        for nm, mm, s9x in (("as is", m6c, sc9), ("mirrored", m6m, sc9m)):
            R, t, dmax, dmed, sep = register(so, mm)
            fits.append((dmax, nm, R, t, s9x, dmed))
        dmax, nm, R, t, s9x, dmed = min(fits, key=lambda f: f[0])
        pts = np.array([[p.x, p.y, p.z] for p in (m6c if nm == "as is" else m6m).Points])[::5]
        d = dists(moved(so, R, t), pts); p95 = float(np.percentile(d, 95)); farp = pts[d > TOL]
        where = (f"; the {len(farp)} points > {TOL} lie in STL X {farp[:,0].min():.2f}..{farp[:,0].max():.2f} "
                 f"Y {farp[:,1].min():.2f}..{farp[:,1].max():.2f} Z {farp[:,2].min():.2f}..{farp[:,2].max():.2f}") if len(farp) else ""
        log(f"{o.Label}: registered to SpeedClip_4mm_Gap.stl ({nm}): {len(pts)} points, median {np.median(d):.4f}, 95% {p95:.4f}, "
            f"max {d.max():.4f}{where}")
        # pose = median fit; a minority of points off by more than TOL in ONE cluster is a feature difference between
        # andrewmcgr's STEP clip and the published STL (a pose error would spread over the whole part)
        if np.median(d) > 0.02 or (d <= TOL).mean() < 0.85: errs.append(f"{o.Label}: pose not established against SpeedClip_4mm_Gap.stl"); continue
        Ri = R.T; ti = -Ri @ t
        Mi = matrix(tuple(tuple(float(x) for x in r) for r in Ri), tuple(float(x) for x in ti))
        n = xformed(s9x, Mi)
        ov0 = so.common(oldC[owner[o.Name]]).Volume; ov1 = n.common(newshape.get(owner[o.Name], oldC[owner[o.Name]])).Volume
        nb = n.BoundBox
        log(f"   9 mm clip: Z {nb.ZMin:.2f}..{nb.ZMax:.2f} (old {so.BoundBox.ZMin:.2f}..{so.BoundBox.ZMax:.2f}); "
            f"overlap with its carriage {ov1:.2f} mm3 (old clip in old carriage {ov0:.2f})")
        # The 9 mm clip (26.02 tall, mesh) sits flush in the 26.00 pocket (mesh), so the faceted contact faces overlap a
        # little: 3.81 mm3 over the whole contact area at the centred pose. A scan of the clip along its height (2026-11-06)
        # gave a sharp minimum there: >= 20 mm3 at +-0.5 mm, > 100 mm3 at +-2 mm. So: <= CLIP_OV, or it's misplaced.
        if ov1 > CLIP_OV: errs.append(f"{o.Label}: 9 mm clip overlaps its carriage by {ov1:.2f} mm3 (old {ov0:.2f})")
        newshape[o.Name] = n
    # belts vs the new gantry carriage
    for bl in BELTS:
        bs = gshape(one(bl)); v0 = bs.common(C).Volume; v1 = bs.common(C2).Volume
        log(f"{bl}: overlap with the gantry carriage {v0:.2f} -> {v1:.2f} mm3")
        if v1 > v0 + 0.05: errs.append(f"{bl} overlaps the new carriage more ({v1:.2f} vs {v0:.2f})")

    # --- apply
    if not errs:
        for o in leaves0:
            if o.Name in newshape:
                ap = look(o); set_global_shape(o, newshape[o.Name]); restore_look(o, ap)
                if o in clips: o.Label = "SpeedClip 4mm Gap 9mm (MadMax, GPL-3.0)"
        doc.recompute(); _BOX.clear()
        now = {o.Name: o for o in doc.Objects if is_leaf(o)}
        for nm, b in before.items():
            if nm in newshape: continue
            if nm not in now: errs.append(f"lost {label0[nm]}"); continue
            if not close(gbox(now[nm]), b): errs.append(f"changed: {now[nm].Label}")
        # printable carriage, in the upstream STL's own frame
        back = xformed(C2, M.inverse()); back.translate(V(bA.XMin, bA.YMin, bA.ZMin))
        msh = MeshPart.meshFromShape(Shape=back, LinearDeflection=0.01, AngularDeflection=0.1)
        bb = back.BoundBox
        log(f"printable carriage: {msh.CountFacets} facets, {bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f}, volume {back.Volume:.1f}")
        if DRY: log(f"DRY RUN: would write {os.path.relpath(OUT_STL, REPO)}")
        else: msh.write(OUT_STL); log(f"wrote {os.path.relpath(OUT_STL, REPO)}")
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
