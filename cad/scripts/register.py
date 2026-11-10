# register: put a STEP assembly where a model already has a copy of the same part (#6). No FreeCAD here, so
# test_register.py runs in CI.
#
#   norm_label(label)                    -> the label without FreeCAD's copy suffixes (" (1)", "001")
#   pair(src, dst, min_vol)              -> [(label, s, d)]: solids whose label is unique on both sides
#   fit(P, Q)                            -> (R, t): the rotation (rows) + translation that best maps points P onto Q
#   residuals(P, Q, R, t)                -> |R p + t - q| for each pair
#   register(src, dst, ...)              -> the fit of the paired solids' centres of mass, with its residuals
#   plane_offset(src_z, dst_z)           -> one Z shift that moves every horizontal face of a part onto its copy's
#
# A solid is a dict {label, vol, com: [x, y, z]} in global coordinates (the volume-weighted centre of mass of all its
# solids, as sweep_toolhead's com() does for the dock carriage copies). The fit is Horn's closed-form least squares
# (unit quaternion, 1987): a proper rotation, never a mirror, so a mirrored copy shows up as residual, not as a fit.
# The check is the one sweep_toolhead makes for "the same part": every paired volume within VOL_TOL mm3, and here
# every paired centre of mass within COM_TOL mm of where the fit puts it.
import math, re

COM_TOL = 0.05      # mm, worst centre-of-mass residual after the fit (sweep_toolhead's box residual limit)
VOL_TOL = 0.5       # mm3, worst volume difference between paired solids (sweep_toolhead's limit)
MIN_VOL = 10.0      # mm3: smaller solids (bearing balls, 0402 parts) don't pair; they are many and alike
_SUFFIX = re.compile(r"(?: \(\d+\)|\d{3})+$")


def norm_label(label):
    return _SUFFIX.sub("", label)


def pair(src, dst, min_vol=0.0):
    def uniq(solids):
        by = {}
        for s in solids: by.setdefault(norm_label(s["label"]), []).append(s)
        return {k: v[0] for k, v in by.items() if len(v) == 1}
    a, b = uniq(src), uniq(dst)
    return [(k, a[k], b[k]) for k in sorted(set(a) & set(b)) if a[k]["vol"] >= min_vol]


def det(R):
    return (R[0][0] * (R[1][1] * R[2][2] - R[1][2] * R[2][1]) - R[0][1] * (R[1][0] * R[2][2] - R[1][2] * R[2][0])
            + R[0][2] * (R[1][0] * R[2][1] - R[1][1] * R[2][0]))


def _centroid(P):
    n = len(P); return [sum(p[i] for p in P) / n for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _top_eigvec(N, sweeps=100):
    """The eigenvector of the largest eigenvalue of a symmetric matrix (cyclic Jacobi)."""
    n = len(N); A = [row[:] for row in N]; V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(sweeps):
        off = sum(A[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off < 1e-30: break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-300: continue
                th = (A[q][q] - A[p][p]) / (2 * A[p][q])
                t = (1.0 if th >= 0 else -1.0) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1); s = t * c
                for k in range(n):
                    akp, akq = A[k][p], A[k][q]; A[k][p], A[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(n):
                    apk, aqk = A[p][k], A[q][k]; A[p][k], A[q][k] = c * apk - s * aqk, s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = V[k][p], V[k][q]; V[k][p], V[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    i = max(range(n), key=lambda k: A[k][k])
    return [V[k][i] for k in range(n)]


def fit(P, Q):
    if len(P) != len(Q): raise ValueError(f"{len(P)} points vs {len(Q)}")
    if len(P) < 3: raise ValueError(f"{len(P)} points: a rigid fit needs at least 3")
    pc, qc = _centroid(P), _centroid(Q)
    p0 = [[p[i] - pc[i] for i in range(3)] for p in P]; q0 = [[q[i] - qc[i] for i in range(3)] for q in Q]
    scale = max(math.sqrt(sum(x * x for x in p)) for p in p0)
    span = max((math.sqrt(sum(x * x for x in _cross(a, b))) for a in p0 for b in p0), default=0.0)
    if scale == 0 or span < 1e-9 * scale * scale: raise ValueError("the points are collinear: the rotation is not fixed")
    S = [[sum(p[i] * q[j] for p, q in zip(p0, q0)) for j in range(3)] for i in range(3)]
    (xx, xy, xz), (yx, yy, yz), (zx, zy, zz) = S
    N = [[xx + yy + zz, yz - zy, zx - xz, xy - yx],
         [yz - zy, xx - yy - zz, xy + yx, zx + xz],
         [zx - xz, xy + yx, -xx + yy - zz, yz + zy],
         [xy - yx, zx + xz, yz + zy, -xx - yy + zz]]
    w, x, y, z = _top_eigvec(N)
    n = math.sqrt(w * w + x * x + y * y + z * z); w, x, y, z = w / n, x / n, y / n, z / n
    R = [[w * w + x * x - y * y - z * z, 2 * (x * y - w * z), 2 * (x * z + w * y)],
         [2 * (x * y + w * z), w * w - x * x + y * y - z * z, 2 * (y * z - w * x)],
         [2 * (x * z - w * y), 2 * (y * z + w * x), w * w - x * x - y * y + z * z]]
    t = [qc[i] - sum(R[i][j] * pc[j] for j in range(3)) for i in range(3)]
    return R, t


def residuals(P, Q, R, t):
    return [math.sqrt(sum((sum(R[i][j] * p[j] for j in range(3)) + t[i] - q[i]) ** 2 for i in range(3)))
            for p, q in zip(P, Q)]


def register(src, dst, min_vol=MIN_VOL, com_tol=COM_TOL, vol_tol=VOL_TOL):
    pairs = pair(src, dst, min_vol)
    if len(pairs) < 3: raise ValueError(f"{len(pairs)} solids pair by label: a rigid fit needs at least 3")
    P = [s["com"] for _, s, _ in pairs]; Q = [d["com"] for _, _, d in pairs]
    R, t = fit(P, Q)
    res = residuals(P, Q, R, t)
    dv = [abs(s["vol"] - d["vol"]) for _, s, d in pairs]
    ic, iv = max(range(len(res)), key=res.__getitem__), max(range(len(dv)), key=dv.__getitem__)
    out = dict(n=len(pairs), labels=[k for k, _, _ in pairs], R=R, t=t,
               matrix=[R[0] + [t[0]], R[1] + [t[1]], R[2] + [t[2]], [0.0, 0.0, 0.0, 1.0]],
               com_max=res[ic], com_rms=math.sqrt(sum(r * r for r in res) / len(res)), com_worst=pairs[ic][0],
               vol_max=dv[iv], vol_worst=pairs[iv][0])
    out["ok"] = out["com_max"] <= com_tol and out["vol_max"] <= vol_tol
    return out


PLANE_TOL = 1e-3    # mm: every horizontal face must move by the same amount to within this


def plane_offset(src_z, dst_z, tol=PLANE_TOL):
    """The Z shift that takes a part's horizontal faces (heights src_z) onto the same part's faces dst_z, matched in
    height order. Raises unless there is at least one face, the counts agree and every face moved alike."""
    if not src_z or len(src_z) != len(dst_z): raise ValueError(f"{len(src_z)} faces vs {len(dst_z)}")
    d = [b - a for a, b in zip(sorted(src_z), sorted(dst_z))]
    if max(d) - min(d) > tol: raise ValueError(f"the faces moved by {min(d):.4f} .. {max(d):.4f}: not one shift")
    return sum(d) / len(d)
