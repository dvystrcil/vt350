# Printable STLs of remixed parts, in the UPSTREAM part's print orientation.   (headless, read-only on the models)
#   VT350_UPSTREAM=<dir with the upstream STLs> freecadcmd /home/dan/Code/vt350/cad/scripts/derive_stls.py
# For each part: the part as it sat in the OLD model (before the remix) is matched to the upstream STL by a rigid
# transform: principal axes of inertia (old solid vs the upstream mesh, 4 proper sign choices), refined by closest-point
# iterations (Kabsch), then checked: every sampled upstream vertex within TOL of the transformed old part. Upstream
# prints are often at non-right angles (the A4Tv2 ducts are). The same transform then takes the REMIXED part from the
# new model to the print orientation. A part that doesn't match is reported and not written.
import FreeCAD, Part, Mesh, MeshPart, os, time, traceback
import numpy as np
V = FreeCAD.Vector
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
UP = os.environ.get("VT350_UPSTREAM", "/home/dan/Documents/VT350/downloads/upstream")
M = "/home/dan/Documents/VT350/vt350-lite-{}.FCStd"
TOL = 0.05
DUCTS = f"{REPO}/cad/derived/a4tv2-duct-4010-madmax-dock"
ARMS = f"{REPO}/cad/derived/madmax-andrewmcgr-dock-arm"
CARRIAGE = f"{REPO}/cad/derived/madmax-andrewmcgr-carriage-beacon"
ONLY = os.environ.get("VT350_ONLY")          # write only the jobs whose output name contains this
# (old model, new model, output, upstream STL, old label + group, new label + group, which solid: "low" = lowest Z)
JOBS = [
    (22, 23, f"{DUCTS}/A4Tv2 Duct-4010-left MadMax dock.stl", f"{UP}/A4Tv2_4010_Ducts.stl",
     ("[a]_Duct-4010-left", "Left Toolhead"), ("[a]_Duct-4010-left MadMax dock bosses (remix, CC BY-NC-SA 4.0)", "Left Toolhead"), None),
    (22, 23, f"{DUCTS}/A4Tv2 Duct-4010-right MadMax dock.stl", f"{UP}/A4Tv2_4010_Ducts.stl",
     ("[a]_Duct-4010-right001", "Right Toolhead"), ("[a]_Duct-4010-right MadMax dock bosses (remix, CC BY-NC-SA 4.0)", "Right Toolhead"), None),
    (22, 23, f"{ARMS}/Dock Arm {{net}}.stl", f"{ARMS}/Dock Arm +5mm.stl",
     ("Dock Arm v1 Bottom +5mm", "Left Dock"), ("Dock Arm v1 Bottom *", "Left Dock"), "low"),
    (23, 24, f"{CARRIAGE}/MadMaxCarriage Beacon RevH pocket.stl", f"{UP}/MadMaxCarriage.stl",
     ("COMPOUND", "Carriage (1)"), ("COMPOUND", "Carriage (1)"), None),
]
log_f = open(f"{REPO}/cad/data/logs/derive_stls" + (f"_{ONLY.split()[0].lower()}" if ONLY else "") + ".log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def mesh_inertia(m):
    """volume, centroid, inertia tensor (about the centroid) of a closed triangle mesh"""
    P = np.array([[p.x, p.y, p.z] for p in m.Points]); F = np.array([list(f.PointIndices) for f in m.Facets])
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    v = np.einsum('ij,ij->i', a, np.cross(b, c)) / 6.0; V_ = v.sum()
    cen = ((a + b + c) / 4.0 * v[:, None]).sum(0) / V_
    a, b, c = a - cen, b - cen, c - cen
    # second moments of each tetrahedron (origin, a, b, c): int x_i x_j = v/20 (sum_k p_ki p_kj + s_i s_j), s = a+b+c
    S = a + b + c
    C = (np.einsum('ni,nj->nij', a, a) + np.einsum('ni,nj->nij', b, b) + np.einsum('ni,nj->nij', c, c)
         + np.einsum('ni,nj->nij', S, S))
    C = (C * (v / 20.0)[:, None, None]).sum(0)
    return V_, cen, np.trace(C) * np.eye(3) - C
def shape_inertia(sh):
    """volume, centroid, inertia tensor about the centroid; a compound sums its solids (parallel-axis theorem)"""
    parts = []
    for x in sh.Solids:
        M = x.MatrixOfInertia; c = x.CenterOfMass
        parts.append((x.Volume, np.array([c.x, c.y, c.z]), np.array([[M.A11, M.A12, M.A13], [M.A21, M.A22, M.A23], [M.A31, M.A32, M.A33]])))
    V_ = sum(v for v, _, _ in parts); cen = sum(v * c for v, c, _ in parts) / V_
    I = sum(Ii + v * (np.dot(c - cen, c - cen) * np.eye(3) - np.outer(c - cen, c - cen)) for v, c, Ii in parts)
    return V_, cen, I
def mat(R, t):
    M = FreeCAD.Matrix()
    M.A11, M.A12, M.A13, M.A14 = R[0, 0], R[0, 1], R[0, 2], t[0]
    M.A21, M.A22, M.A23, M.A24 = R[1, 0], R[1, 1], R[1, 2], t[1]
    M.A31, M.A32, M.A33, M.A34 = R[2, 0], R[2, 1], R[2, 2], t[2]
    return M
def moved(sh, R, t):
    r = sh.copy(); r.transformShape(mat(R, t), True); return r
def dists(sh, pts):
    return np.array([sh.distToShape(Part.Vertex(V(*p)))[0] for p in pts])
def register(so, cm, n=300, iters=6):
    """rigid (R, t) taking so onto the mesh cm, and the max distance of sampled mesh vertices to the moved solid"""
    _, cs, Is = shape_inertia(so); _, cmn, Im = mesh_inertia(cm)
    ws, Es = np.linalg.eigh(Is); wm, Em = np.linalg.eigh(Im)
    sep = min(abs(ws[1] - ws[0]), abs(ws[2] - ws[1])) / ws[2]
    P = np.array([[p.x, p.y, p.z] for p in cm.Points]); pts = P[:: max(1, len(P) // n)]
    best = None
    for sg in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)):
        R = Em @ np.diag(sg) @ Es.T
        if np.linalg.det(R) < 0: R = Em @ np.diag((-sg[0], sg[1], sg[2])) @ Es.T
        t = cmn - R @ cs
        d = dists(moved(so, R, t), pts[::5])
        if best is None or d.max() < best[0]: best = (d.max(), R, t)
    _, R, t = best
    for _ in range(iters):     # closest points on the moved solid -> Kabsch
        r = moved(so, R, t); q = []
        for p in pts:
            q.append(np.array(r.distToShape(Part.Vertex(V(*p)))[1][0][0]))
        Q = np.array(q)                                    # on the moved solid, paired with pts
        Qs = (np.linalg.inv(R) @ (Q - t).T).T              # back in the solid's own frame
        mp, mq = pts.mean(0), Qs.mean(0)
        U, _, Wt = np.linalg.svd((Qs - mq).T @ (pts - mp))
        D = np.diag([1, 1, np.sign(np.linalg.det(Wt.T @ U.T))])
        R = Wt.T @ D @ U.T; t = mp - R @ mq
    d = dists(moved(so, R, t), pts)
    return R, t, d.max(), float(np.median(d)), sep
def part(doc, label, group, which):
    """(shape, label); a label ending in ' *' matches by prefix (and must not be the old part's exact label)"""
    if label.endswith(" *"):
        c = [o for o in doc.Objects if o.Label.startswith(label[:-1]) and "Mirror" not in o.Label and "+5mm" not in o.Label
             and group in [a.Label for a in o.InListRecursive]]
    else: c = [o for o in doc.getObjectsByLabel(label) if group in [a.Label for a in o.InListRecursive]]
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects {label!r} under {group!r}")
    s = c[0].Shape.copy(); s.Placement = c[0].getGlobalPlacement()
    if which == "low": s = min(s.Solids, key=lambda x: x.BoundBox.ZMin)
    return s, c[0].Label
try:
    docs = {}
    def model(n):
        if n not in docs: docs[n] = FreeCAD.openDocument(M.format(n))
        return docs[n]
    res = []
    for mo, mn, out, up, (ol, og), (nl, ng), which in JOBS:
        if ONLY and ONLY not in out: continue
        so, _ = part(model(mo), ol, og, which); sn, nlab = part(model(mn), nl, ng, which)
        out = out.replace("{net}", nlab.split()[-1])
        comps = [c for c in Mesh.Mesh(up).getSeparateComponents() if c.CountFacets >= 50]
        # the upstream component with the same volume (the A4Tv2 STL holds both ducts)
        ci, cm = min(enumerate(comps), key=lambda x: abs(x[1].Volume - so.Volume))
        if abs(cm.Volume - so.Volume) > 0.005 * so.Volume:
            log(f"NO MATCH {os.path.basename(out)}: no upstream component within 0.5% of volume {so.Volume:.1f} "
                + str([round(c.Volume, 1) for c in comps])); res.append((out, None)); continue
        R, t, dmax, dmed, sep = register(so, cm)
        if dmax > TOL:
            log(f"NO MATCH {os.path.basename(out)}: component {ci}, max vertex distance {dmax:.4f} (median {dmed:.4f}), "
                f"inertia axes separation {sep:.3f}"); res.append((out, None)); continue
        ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
        log(f"{os.path.basename(out)}: old part = component {ci} of {os.path.basename(up)} (volume {cm.Volume:.1f} vs {so.Volume:.1f}); "
            f"rotation {ang:.2f} deg; max vertex distance {dmax:.4f} mm (median {dmed:.4f})")
        r = moved(sn, R, t)
        msh = MeshPart.meshFromShape(Shape=r, LinearDeflection=0.01, AngularDeflection=0.1)
        os.makedirs(os.path.dirname(out), exist_ok=True); msh.write(out)
        b = r.BoundBox
        log(f"   wrote {os.path.relpath(out, REPO)}: {msh.CountFacets} facets, {b.XLength:.2f} x {b.YLength:.2f} x {b.ZLength:.2f} mm, volume {r.Volume:.1f} (old {so.Volume:.1f}); solid valid {r.isValid()}")
        res.append((out, dict(volume=r.Volume, size=(b.XLength, b.YLength, b.ZLength), old_volume=so.Volume)))
    log("done:", sum(1 for _, x in res if x), "of", len(res), "written")
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
