# reglib: rigid registration of a FreeCAD solid to a triangle mesh (an upstream STL), shared by derive_stls.py and
# the lite-N passes that place or replace upstream parts.
#   register(solid, mesh) -> (R, t, max_dist, median_dist, axes_separation): R @ p + t takes the solid onto the mesh.
# Principal axes of inertia (4 proper sign choices), refined by closest-point iterations (Kabsch); the distances are
# from sampled mesh vertices to the moved solid. Proper rotations only: register a mirrored part to a mirrored mesh.
import FreeCAD, Part
import numpy as np
V = FreeCAD.Vector
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
