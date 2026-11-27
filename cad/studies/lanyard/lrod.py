"""Bowden lanyard + ceiling study (vt350#218, #3, #243): the rod model of cad/studies/flap_guide/rod.py, changed for
the route the model has now (lite-70) and for a lanyard.

Each bundle (PTFE + O2S cable, zip-tied) is a discrete inextensible elastic rod from its roof exit to its head:
  - roof end: CLAMPED where the 45 deg roof clamp's bore meets the ceiling, its tangent along the bore (lite-70);
  - head end: clamped, the bundle leaves the O2S lock straight up (+Z);
  - gravity; the ceiling (felt underside, Z 679 since lite-69) and the frame's inner faces as contact surfaces;
  - a LANYARD: a constant pull F from a reel point on the top front frame to one node of the rod (a badge reel's
    spring is close to constant over its travel), energy F * |reel - node|.
The length is either free with a take-up pull T on it (to find how much tube the farthest position needs) or fixed
(the tube as cut).

The force the bundle puts on the head comes from the Lagrange multipliers at the solution (envelope theorem:
dE*/db = dE/db + lambda . dc/db); test_lrod.py checks it against re-solving with the head moved.
Run the tests: python cad/studies/lanyard/test_lrod.py (numpy + scipy)."""
import math, os, sys
import numpy as np
from scipy.optimize import minimize
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "flap_guide"))
from rod import seg_dist, W_LIN, HEAD_Z, DOCK_X, DOCK_Y, REACH_X, REACH_Y   # noqa: E402,F401  (shared geometry)

Z_CEIL = 679.0                      # roof felt underside (lite-69 moved the felt inside; lite69_insulation_inside.log)
X_WALL = (-480.0, -10.0)            # inner faces of the side 4040 top bars
Y_WALL = (-70.0, 480.0)             # inner faces of the front 2040 and rear 4040 top bars
EXIT_X = {1: -409.7, 2: -324.54, 3: -248.42, 4: -156.42, 5: -80.3}   # lite70_roof_exit_low.json axis_x
EXIT_DIR = np.array([0.0, 1.0, 1.0]) / math.sqrt(2.0)                 # the clamp's bore, outward (lite-36/70)
EXIT_ON_ROOF = (460.0, 690.0)                                          # the bore's axis at the roof panel (Y, Z)
N = 30


def exit_point(slot):
    """Where the bore leaves the ceiling: back along the 45 deg axis from the roof panel to the felt underside."""
    y0, z0 = EXIT_ON_ROOF
    d = z0 - Z_CEIL
    return np.array([EXIT_X[slot], y0 - d, Z_CEIL])


class Rod:
    def __init__(s, EI, w=W_LIN, n=N, g0=-EXIT_DIR, reel=None, k=None, F=0.0, z_ceil=Z_CEIL):
        """g0: tangent of the clamp at the roof end, traversed roof -> head (into the chamber). reel/k/F: the lanyard
        (reel point, attached node index 1..n-1, pull in N); F = 0 or reel None: no lanyard."""
        s.EI, s.w, s.n, s.g0 = EI, w, n, np.asarray(g0, float)
        s.reel, s.k, s.F, s.zc = (None if reel is None else np.asarray(reel, float)), k, F, z_ceil

    def unpack(s, v, a, b, L):
        X = np.empty((s.n + 1, 3)); X[0] = a; X[-1] = b; X[1:-1] = v[:3 * (s.n - 1)].reshape(-1, 3)
        if L is None: L = v[-1]
        return X, L

    def full(s, v, a, b, L, T):
        """Energy, its gradient on every node (incl. both ends), and dE/dds."""
        X, L = s.unpack(v, a, b, L)
        n, EI, w = s.n, s.EI, s.w
        ds = L / n
        D = np.diff(X, axis=0)
        S = np.sum(D[1:] * D[:-1])
        dz = D[-1, 2]                           # head ghost: tangent -Z
        g0D = float(s.g0 @ D[0])                # roof ghost: tangent g0
        E = EI * (n + 1) / ds - EI * S / ds**3 + EI * dz / ds**2 - EI * g0D / ds**2
        zs = X[1:-1, 2].sum() + 0.5 * (X[0, 2] + X[-1, 2])
        E += w * ds * zs + T * L
        gD = np.zeros_like(D)
        gD[1:] += -EI / ds**3 * D[:-1]; gD[:-1] += -EI / ds**3 * D[1:]
        gD[-1, 2] += EI / ds**2
        gD[0] += -EI / ds**2 * s.g0
        gX = np.zeros_like(X)
        gX[1:] += gD; gX[:-1] -= gD
        gX[1:-1, 2] += w * ds
        gX[0, 2] += 0.5 * w * ds; gX[-1, 2] += 0.5 * w * ds
        dEds = -EI * (n + 1) / ds**2 + 3 * EI * S / ds**4 - 2 * EI * dz / ds**3 + 2 * EI * g0D / ds**3 + w * zs
        if s.reel is not None and s.F:
            r = X[s.k] - s.reel; lr = np.linalg.norm(r)
            E += s.F * lr; gX[s.k] += s.F * r / lr
        return E, gX, dEds, X, L

    def energy(s, v, a, b, L, T):
        E, gX, dEds, X, L = s.full(v, a, b, L, T)
        g = gX[1:-1].ravel()
        if len(v) == 3 * (s.n - 1) + 1: g = np.append(g, dEds / s.n + T)
        return E, g

    def _cons(s, a, b, L):
        n, m, free = s.n, s.n - 1, L is None
        def ceq(v):
            X, LL = s.unpack(v, a, b, L)
            D = np.diff(X, axis=0)
            return (np.sum(D * D, axis=1) - (LL / n) ** 2) / (LL / n)
        def jeq(v):
            X, LL = s.unpack(v, a, b, L)
            D = np.diff(X, axis=0); ds = LL / n
            J = np.zeros((n, v.size))
            for i in range(n):
                if i < m: J[i, 3 * i:3 * i + 3] += 2 * D[i] / ds
                if i > 0: J[i, 3 * (i - 1):3 * i] -= 2 * D[i] / ds
            if free:
                q = np.sum(D * D, axis=1)
                J[:, -1] = (-q / ds**2 - 1) / n
            return J
        def cin(v):
            P = v[:3 * m].reshape(-1, 3)
            return np.concatenate([s.zc - P[:, 2], P[:, 0] - X_WALL[0], X_WALL[1] - P[:, 0],
                                   P[:, 1] - Y_WALL[0], Y_WALL[1] - P[:, 1]])
        Jin = np.zeros((5 * m, 3 * m + (1 if free else 0)))
        for i in range(m):
            Jin[i, 3 * i + 2] = -1; Jin[m + i, 3 * i] = 1; Jin[2 * m + i, 3 * i] = -1
            Jin[3 * m + i, 3 * i + 1] = 1; Jin[4 * m + i, 3 * i + 1] = -1
        return ceq, jeq, cin, Jin

    def solve(s, a, b, x0, L, T, iters=500):
        free = L is None
        ceq, jeq, cin, Jin = s._cons(a, b, L)
        cons = [{"type": "eq", "fun": ceq, "jac": jeq}, {"type": "ineq", "fun": cin, "jac": lambda v: Jin}]
        bounds = None
        if free:
            bounds = [(None, None)] * (3 * (s.n - 1)) + [(np.linalg.norm(b - a) * 1.0005, 3000.0)]
        r = minimize(s.energy, x0, args=(a, b, L, T), jac=True, method="SLSQP", constraints=cons, bounds=bounds,
                     options={"maxiter": iters, "ftol": 1e-10})
        ok = r.success and np.max(np.abs(ceq(r.x))) < 1e-3 and np.min(cin(r.x)) > -1e-3
        return r.x, ok, r

    def head_force(s, v, a, b, L, T):
        """Force the bundle puts ON the head (N), from the multipliers of the converged solve (fixed or free L)."""
        E, gX, dEds, X, LL = s.full(v, a, b, L, T)
        ceq, jeq, cin, Jin = s._cons(a, b, L)
        g = s.energy(v, a, b, L, T)[1]
        act = np.where(cin(v) < 1e-3)[0]
        A = np.hstack([jeq(v).T, Jin[act].T])                  # stationarity: g + A . mult = 0
        mult = np.linalg.lstsq(A, -g, rcond=None)[0]
        lam = mult[:s.n]
        ds = LL / s.n
        dc_last_db = 2 * (X[-1] - X[-2]) / ds                  # the last length constraint is the only one with b
        dEdb = gX[-1] + lam[-1] * dc_last_db
        return -dEdb

    def initial(s, a, b, L):
        """A Bezier leaving the roof along g0 and arriving at the head from above, resampled to n equal chords."""
        L0 = L or 1.15 * np.linalg.norm(b - a) + 20
        best = None
        t = np.linspace(0, 1, 2001)[:, None]
        for h in np.linspace(0.05, 1.5, 30):
            c = [a, a + s.g0 * h * L0 * 0.5, b + np.array([0, 0, 1.0]) * h * L0 * 0.5, b]
            P = (1 - t)**3 * c[0] + 3 * (1 - t)**2 * t * c[1] + 3 * (1 - t) * t**2 * c[2] + t**3 * c[3]
            P[:, 2] = np.minimum(P[:, 2], s.zc - 0.01)
            l = np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1))
            if best is None or abs(l - L0) < abs(best[0] - L0): best = (l, P)
        l, P = best
        cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        X = np.array([np.interp(np.linspace(0, l, s.n + 1), cum, P[:, k]) for k in range(3)]).T
        v = X[1:-1].ravel()
        return np.append(v, l) if L is None else v


def metrics(R, X):
    """Shape metrics: lowest point, tightest bend (incl. both clamps), ceiling contact length, the cord."""
    D = np.diff(X, axis=0); ds = np.linalg.norm(D, axis=1).mean()
    t = D / np.linalg.norm(D, axis=1)[:, None]
    tt = np.vstack([[R.g0], t, [[0, 0, -1.0]]])
    ang = np.arccos(np.clip(np.sum(tt[1:] * tt[:-1], axis=1), -1, 1))
    on = X[:, 2] >= R.zc - 0.25
    contact = float(sum(ds for i in range(1, len(X) - 1) if on[i] and on[i + 1]))   # node 0 is the exit itself
    m = {"lowest": float(X[:, 2].min()), "minR": float(ds / max(ang.max(), 1e-9)), "ceiling_mm": contact}
    if R.reel is not None and R.F:
        c = X[R.k] - R.reel
        tk = X[R.k + 1] - X[R.k - 1]; tk /= np.linalg.norm(tk)
        m.update(cord=float(np.linalg.norm(c)), cord_z=float(X[R.k, 2]),
                 cord_deg=float(math.degrees(math.acos(abs(np.clip(tk @ (c / np.linalg.norm(c)), -1, 1))))))
    return m
