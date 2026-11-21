# GUI pass: vt350-lite-73 -> vt350-lite-74   (headless = dry run, never saves)   vt350#263
# Fix lite-73's Right Dock carriage copy. COMPOUND004 (a Part; the Left Dock's COMPOUND003 links the carriage) is the
# gantry carriage TRANSLATED to its pickup pose (lite-24, lite-25, lite-62). lite73_dav.py cut it "the same way" with a
# cut tool mirrored in X by transformGeometry. The place came out right (the cut is centred on the carriage in X, so
# the mirror and the translation agree), but transformGeometry turns the tool's planes into B-spline faces, and the
# copy's BoundBox overshoots on them: 7.8 mm in Y. sweep_toolhead.py compares boxes, so it refused lite-73 ("Right:
# dock carriage copy isn't the gantry carriage part", box residual 7.836).
# This pass sets COMPOUND004's shape to the lite-73 gantry carriage (already cut correctly) moved by T, the pickup
# offset measured on lite-72 (before any lite-73 cut): T = COM(copy) - COM(carriage), the sweep's own definition.
# Checks (refuses to save on any):
#  - on lite-72: the copy is the carriage translated by T (sample vertices of the copy within 0.02 of the moved carriage,
#    both ways). The X mirror fits there too (the carriage is symmetric in X at the sampled points): logged, not a check;
#  - on lite-73: the gantry carriage is lite-72's less the pocket cut (volume), the copy fails the sweep's test, its
#    cut is in the right place, and what's wrong is its faces: B-splines (lite-73's mirrored cut tool), whose BoundBox
#    overshoots, while the tight box agrees; the Left copy is still a link to the carriage;
#  - after: the copy has the carriage's faces (no extra B-splines);
#  - after: the copy passes the sweep's test (volume diff < 0.5, box residual < 0.05) with the same T as lite-72
#    (< 1e-3), its vertices on the moved carriage, placement and colour kept; no new or worse overlap of the copy
#    against lite-72's copy; every other solid's box unchanged.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC = os.environ.get("VT350_SRC", f"{MODELS}/vt350-lite-73.FCStd")
REF = os.environ.get("VT350_REF", f"{MODELS}/vt350-lite-72.FCStd")      # read only: the copy before lite-73's cut
DST = f"{MODELS}/vt350-lite-74.FCStd"
CARRIAGE, CAR_GROUP = "COMPOUND", "Carriage (1)"   # the gantry carriage (sweep_toolhead.CARRIAGE_PART)
COPY, DOCK = "COMPOUND004", "Right Dock"
LEFT_COPY = "COMPOUND003"
CUT_VOL = (1.0, 200.0)       # lite-73 took a few mm3 off the carriage (its log: the 0.30 cut); a sanity window
CLIP = "SpeedClip 4mm Gap 9mm"   # the dock's belt clips sit in the copy's 9 mm pockets (lite-25): a known overlap,
CLIP_CAP, CLIP_SUM = 5.0, 1.0    # each <= 5 mm3, the pair's total no more than 1 mm3 over lite-72's (the copy moved <= 0.0142)
NPTS = 30                    # sample vertices for the point tests (each distToShape ~0.5 s on the carriage)
PT_TOL = 0.02                # lite-72's copy sits up to 0.0142 off the carriage moved by its COM offset (separate
                             # booleans in lite-24/25/62; the sweep allows 0.05); a mirror is off by millimetres


def com(s):
    """Volume-weighted centre of mass over the solids (compounds have none): sweep_toolhead.py's."""
    vs = [(x.Volume, x.CenterOfMass) for x in s.Solids]; tv = sum(v for v, _ in vs)
    return sum((c * (v / tv) for v, c in vs), V(0, 0, 0))


def sweep_test(sc, sr):
    """sweep_toolhead.py's 'same part' test of a dock copy sc against the gantry carriage sr: (t, dv, resid)."""
    t = com(sc) - com(sr); m = sr.copy(); m.translate(t)
    k = ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")
    return t, abs(sc.Volume - sr.Volume), max(abs(getattr(m.BoundBox, a) - getattr(sc.BoundBox, a)) for a in k)


def samples(s, n=NPTS):
    vs = s.Vertexes
    return [v.Point for v in vs[::max(1, len(vs) // n)]]


def off(pts, s):
    """How many points lie more than PT_TOL off shape s, and the worst distance."""
    ds = [s.distToShape(Part.Vertex(q))[0] for q in pts]
    return sum(1 for d in ds if d > PT_TOL), max(ds)


def find(pr, label, group):
    par = linkgeo.group_parents(pr.doc.Objects)
    hits = [o for o in pr.leaves if o.Label == label]
    def anc(o):
        out, g = [], par.get(o.Name)
        while g is not None: out.append(g.Label); g = par.get(g.Name)
        return out
    hits = [o for o in hits if group in anc(o)] or hits
    return hits


def main(p):
    # ---- lite-72: what the copy is
    rf = p.open(REF)
    c72, k72 = find(rf, CARRIAGE, CAR_GROUP), find(rf, COPY, DOCK)
    p.check(len(c72) == 1 and len(k72) == 1, f"lite-72: one gantry carriage, one {COPY} ({len(c72)}, {len(k72)})")
    if p.errs: return p.finish([])
    R72, K72 = rf.shapes[c72[0].Name], rf.shapes[k72[0].Name]
    T, dv, resid = sweep_test(K72, R72)
    p.check(dv < 0.5 and resid < 0.05, f"lite-72: {COPY} passes the sweep's test (T ({T.x:.3f}, {T.y:.3f}, {T.z:.3f}), "
                                       f"volume diff {dv:.3f}, box residual {resid:.4f})")
    moved = R72.copy(); moved.translate(T)
    b1, w1 = off(samples(K72), moved); b2, w2 = off(samples(moved), K72)
    p.check(b1 == 0 and b2 == 0, f"lite-72: {COPY} is the carriage translated by T (copy -> carriage {b1} points off, worst "
                                 f"{w1:.5f}; carriage -> copy {b2} off, worst {w2:.5f})")
    cb, kb = R72.BoundBox, K72.BoundBox                       # lite-73's mirror, rebuilt the way it built it
    # x -> (kb.XMin + cb.XMax) - x, as lite-73's matrix; Shape.mirror keeps the exact geometry (transformGeometry
    # turns it into B-splines and each distToShape then takes minutes)
    mir = R72.mirror(V((kb.XMin + cb.XMax) / 2, 0, 0), V(1, 0, 0)); mir.translate(V(0, kb.YMin - cb.YMin, kb.ZMin - cb.ZMin))
    bm, wm = off(samples(K72), mir)
    p.log(f"lite-72: the X mirror fits the copy too ({bm} of {len(samples(K72))} points off it, worst {wm:.4f}): "
          f"the carriage is symmetric in X there, so lite-72 can't tell; lite-73's off-centre cut can (below)")
    ov72 = {}
    for o in rf.leaves:
        if o.Name != k72[0].Name and K72.BoundBox.intersect(rf.shapes[o.Name].BoundBox): ov72[o.Name] = o.Shape
    v72 = dict(zip(ov72, p.volumes([(K72, rf.shapes[n]) for n in ov72])))
    if p.errs: return p.finish([])
    # ---- lite-73: the model to fix
    pr = p.open(SRC); doc = pr.doc
    car, cp = find(pr, CARRIAGE, CAR_GROUP), find(pr, COPY, DOCK)
    lk = [o for o in pr.leaves if o.Label == LEFT_COPY]
    p.check(len(car) == 1 and len(cp) == 1 and cp[0].TypeId == "Part::Feature", f"lite-73: one gantry carriage, {COPY} a Part")
    if p.errs: return p.finish([])
    car, cp = car[0], cp[0]
    p.check(len(lk) == 1 and lk[0].TypeId == "App::Link" and linkgeo.link_target(lk[0]) is car,
            f"lite-73: the Left Dock's {LEFT_COPY} links the carriage (follows it, nothing to fix)")
    G = pr.shapes[car.Name]
    cut = R72.Volume - G.Volume
    p.check(CUT_VOL[0] < cut < CUT_VOL[1], f"lite-73: the carriage is lite-72's less lite-73's pocket cut ({cut:.2f} mm3)")
    t0, dv0, r0 = sweep_test(pr.shapes[cp.Name], G)
    p.check(dv0 < 0.5 and r0 >= 0.05, f"lite-73: {COPY} fails the sweep's test as reported (volume diff {dv0:.3f}, box residual "
                                      f"{r0:.4f}): the fix applies")
    # what is wrong with it: not the geometry (lite-73's cut sits where T puts the carriage's; the cut is centred in X,
    # so a mirror puts it there too) but the faces. lite-73 cut it with a tool made by transformGeometry(mirror matrix),
    # which turns planes into B-splines, and BoundBox overshoots on B-splines; the tight box (obb) still agrees.
    bsp = lambda sh: sum(1 for f in sh.Faces if f.Surface.__class__.__name__.startswith("BSpline"))
    K3 = pr.shapes[cp.Name]; ob, om = litelib.obb(K3), litelib.obb(G)
    k_ = ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")
    tres = max(abs(getattr(ob, a) - getattr(om, a) - (T.x, T.y, T.z, T.x, T.y, T.z)[n]) for n, a in enumerate(k_))
    mt = G.copy(); mt.translate(T)                  # booleans of near-coincident copies are unreliable (LESSONS.md): points
    cutv = [v.Point for f in K3.Faces if f.Surface.__class__.__name__.startswith("BSpline") for v in f.Vertexes]
    bc, wc = off(cutv, mt)
    p.log(f"lite-73's cut on the copy, measured: {len(cutv)} vertices of its B-spline (cut) faces vs the carriage moved by T: "
          f"{bc} more than {PT_TOL} off, worst {wc:.4f} (replaced below either way)")
    p.check(bsp(K3) > bsp(K72) and tres < 0.05, f"the copy's fault is its faces: B-spline faces {bsp(K72)} in lite-72 -> {bsp(K3)}; "
            f"tight box residual {tres:.4f} vs BoundBox's {r0:.3f}")
    box0 = {n: s.BoundBox for n, s in pr.shapes.items()}
    if p.errs: return p.finish([])
    # ---- write: the carriage moved by T, in the copy's own frame
    # Shape.translate only changes Shape.Placement (gshape puts the global placement there too), and the frame change
    # below sets the Placement: bake it into the geometry first, or the move is lost
    N = G.copy(); N.translate(T); pl = N.Placement; N.Placement = FreeCAD.Placement(); N.transformShape(pl.toMatrix(), True, False)
    p.check(N.Placement.isIdentity() and (com(N) - com(G) - T).Length < 1e-6, "the new copy: the carriage moved by T, placement baked")
    gui = FreeCAD.GuiUp
    P0 = FreeCAD.Placement(cp.Placement); Cg = linkgeo.gplace(cp).multiply(cp.Placement.inverse())
    ap = list(cp.ViewObject.ShapeAppearance) if gui and hasattr(cp.ViewObject, "ShapeAppearance") else None
    g_ = N.copy(); g_.transformShape(Cg.multiply(P0).inverse().toMatrix(), True, False); g_.Placement = P0; cp.Shape = g_
    if ap is not None: cp.ViewObject.ShapeAppearance = ap
    doc.recompute(); pr.refresh()
    # ---- after
    K = pr.shapes[cp.Name]
    p.check(cp.Placement.isSame(P0, 1e-9) and K.isValid() and len(K.Solids) == len(G.Solids),
            f"{COPY}: placement kept, valid, {len(K.Solids)} solids")
    t1, dv1, r1 = sweep_test(K, pr.shapes[car.Name])
    p.check(dv1 < 0.5 and r1 < 0.05, f"{COPY} passes the sweep's test (volume diff {dv1:.4f}, box residual {r1:.4f})")
    p.check((t1 - T).Length < 1e-3, f"the pickup offset is lite-72's ({t1.x:.3f}, {t1.y:.3f}, {t1.z:.3f}; moved {(t1 - T).Length:.5f})")
    mv = pr.shapes[car.Name].copy(); mv.translate(T)
    b3, w3 = off(samples(K), mv)
    p.check(b3 == 0, f"{COPY}: its vertices on the moved carriage ({b3} off, worst {w3:.5f})")
    p.check(bsp(K) == bsp(G), f"{COPY}: the carriage's faces again (B-spline faces {bsp(K)}, carriage {bsp(G)})")
    tl, dvl, rl = sweep_test(pr.shapes[lk[0].Name], pr.shapes[car.Name])
    p.check(dvl < 0.5 and rl < 0.05, f"{LEFT_COPY} (Left) still passes the sweep's test (box residual {rl:.4f})")
    others = [o.Name for o in pr.leaves if o.Name != cp.Name and K.BoundBox.intersect(pr.shapes[o.Name].BoundBox)]
    va = dict(zip(others, p.volumes([(K, pr.shapes[n]) for n in others])))
    lab = lambda n: doc.getObject(n).Label
    worse = [(round(v, 3), lab(n), round(v72.get(n, 0.0), 3)) for n, v in va.items() if v > v72.get(n, 0.0) + 0.01]
    p.log(f"{COPY} overlaps now (lite-72): {[(lab(n), round(v, 3), round(v72.get(n, 0.0), 3)) for n, v in va.items() if v > 1e-3]}")
    clips = [n for n, v in va.items() if lab(n).startswith(CLIP) and v > 1e-3]
    csum, csum0 = sum(va[n] for n in clips), sum(v72.get(n, 0.0) for n in clips)
    p.check(len(clips) == 2 and all(va[n] <= CLIP_CAP and v72.get(n, 0.0) > 1 for n in clips) and csum <= csum0 + CLIP_SUM,
            f"known: the dock's two belt clips in the copy's pockets {[round(va[n], 3) for n in clips]} mm3 "
            f"(lite-72 {[round(v72.get(n, 0.0), 3) for n in clips]}; total {csum:.3f} vs {csum0:.3f})")
    worse = [w for w in worse if not w[1].startswith(CLIP)]
    p.check(not worse, f"no other new or worse overlap of {COPY} against lite-72's copy ({worse[:8]})")
    moved_ = [lab(n) for n, b in box0.items() if n != cp.Name and (n not in pr.shapes or not pr.shapes[n].BoundBox.isInside(b)
              or not b.isInside(pr.shapes[n].BoundBox))]
    p.check(not moved_, f"every other solid's box unchanged ({len(moved_)}: {moved_[:5]})")
    p.dump({"T_lite72": [round(T.x, 4), round(T.y, 4), round(T.z, 4)], "mirror_points_off": bm, "bspline_faces": {"lite72": bsp(K72), "lite73": bsp(K3), "lite74": bsp(K)},
            "before": {"volume_diff": round(dv0, 4), "box_residual": round(r0, 4)},
            "after": {"volume_diff": round(dv1, 4), "box_residual": round(r1, 4)}, "carriage_cut_mm3": round(cut, 3),
            "src": os.path.basename(SRC), "ref": os.path.basename(REF)})
    FreeCAD.closeDocument(rf.doc.Name)
    return p.finish([(doc, DST)])


if not os.environ.get("LITE74_AS_LIB"): litelib.Pass("lite74_dock_copy").run(main)
