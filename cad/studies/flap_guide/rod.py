"""Flap + guide cable study (vt350 #3). Each bundle (PTFE + Nitehawk cable) passes through a fixed guide (flared
eyelet) at the inner edge of its ceiling flap. Only the free span guide -> head is modelled, as a discrete
inextensible elastic rod:
  - guide end: pinned (the flare lets the tangent swing), on the flap underside;
  - head end: clamped, bundle leaves the head straight up (+Z);
  - gravity, ceiling contact (z <= Z_CEIL), walls;
  - the bundle SLIDES through the guide. Two ways to set how much hangs:
      mode "T=<N>": a constant pull T on the slack side (a take-up: bungee, weight, spring). The span's length is a
                    variable; equilibrium minimises bending + gravity + T*L.
      mode "fixed": nothing pulls the slack back (friction only). The span keeps the longest length it was pulled
                    to: L = L_FIX for every position (pessimistic for sag near the guide).
Solver: SLSQP over node positions (+ L), exact gradients, continuation along a serpentine (each solve starts from
the previous shape). Tested by test_rod.py: exact gradients vs central differences, and a limp rod vs the analytic catenary.
vt350#3. Rebuilt 2026-11-16 (the 2026-11-15 loops/rod.py was lost with its scratchpad), now kept in the repo."""
import json, sys, math, numpy as np
from scipy.optimize import minimize

W_LIN = 5.8e-4          # N/mm (0.58 g/mm, estimate; #3)
Z_CEIL = 690.0          # flap underside / ceiling
X_WALL = (-480.0, -10.0)
HEAD_Z = 550.11         # O2S lock top
DOCK_Y = 10.92
DOCK_X = {1: -409.42, 2: -324.26, 3: -248.14, 4: -156.14, 5: -80.02}
REACH_X, REACH_Y = (-416.0, -74.0), (30.5, 370.7)   # nozzle reach (sweep_toolhead.log); lock assumed above nozzle
N = 30


class Rod:
    def __init__(s, EI, w=W_LIN, n=N):
        s.EI, s.w, s.n = EI, w, n

    # vars: x_1..x_{n-1} (3 each) [+ L]
    def unpack(s, v, a, b, L):
        X = np.empty((s.n + 1, 3)); X[0] = a; X[-1] = b; X[1:-1] = v[:3 * (s.n - 1)].reshape(-1, 3)
        if L is None: L = v[-1]
        return X, L

    def energy(s, v, a, b, L, T):
        free = L is None
        X, L = s.unpack(v, a, b, L)
        n, EI, w = s.n, s.EI, s.w
        ds = L / n
        D = np.diff(X, axis=0)                      # n segments
        S = np.sum(D[1:] * D[:-1])
        dz = D[-1, 2]                               # ghost: head tangent, traversed guide->head, is -Z
        E = EI * n / ds - EI * S / ds**3 + EI * dz / ds**2
        zs = X[1:-1, 2].sum() + 0.5 * (X[0, 2] + X[-1, 2])
        E += w * ds * zs + T * L
        gD = np.zeros_like(D)
        gD[1:] += -EI / ds**3 * D[:-1]; gD[:-1] += -EI / ds**3 * D[1:]
        gD[-1, 2] += EI / ds**2
        gX = np.zeros_like(X)
        gX[1:] += gD; gX[:-1] -= gD
        gX[1:-1, 2] += w * ds
        g = gX[1:-1].ravel()
        if free:
            dEds = -EI * n / ds**2 + 3 * EI * S / ds**4 - 2 * EI * dz / ds**3 + w * zs
            g = np.append(g, dEds / n + T)
        return E, g

    def solve(s, a, b, x0, L, T, iters=400):
        free = L is None
        n = s.n
        m = n - 1
        def ceq(v):
            X, LL = s.unpack(v, a, b, L)
            D = np.diff(X, axis=0)
            return (np.sum(D * D, axis=1) - (LL / n) ** 2) / (LL / n)
        def jeq(v):
            X, LL = s.unpack(v, a, b, L)
            D = np.diff(X, axis=0); ds = LL / n
            J = np.zeros((n, v.size))
            for i in range(n):
                if i < m: J[i, 3 * i:3 * i + 3] += 2 * D[i] / ds          # x_{i+1}
                if i > 0: J[i, 3 * (i - 1):3 * i] -= 2 * D[i] / ds        # x_i
            if free:
                q = np.sum(D * D, axis=1)
                J[:, -1] = (-q / ds**2 - 1) / n
            return J
        def cin(v):
            X, _ = s.unpack(v, a, b, L)
            P = X[1:-1]
            return np.concatenate([Z_CEIL - P[:, 2], P[:, 0] - X_WALL[0], X_WALL[1] - P[:, 0]])
        Jin = np.zeros((3 * m, 3 * m + (1 if free else 0)))
        for i in range(m):
            Jin[i, 3 * i + 2] = -1; Jin[m + i, 3 * i] = 1; Jin[2 * m + i, 3 * i] = -1
        cons = [{"type": "eq", "fun": ceq, "jac": jeq}, {"type": "ineq", "fun": cin, "jac": lambda v: Jin}]
        bounds = None
        if free:
            dmin = np.linalg.norm(b - a)
            bounds = [(None, None)] * (3 * m) + [(dmin * 1.0005, 3000.0)]
        r = minimize(s.energy, x0, args=(a, b, L, T), jac=True, method="SLSQP", constraints=cons, bounds=bounds,
                     options={"maxiter": iters, "ftol": 1e-10})
        ok = r.success and np.max(np.abs(ceq(r.x))) < 1e-3 * max(1, 1) and np.min(cin(r.x)) > -1e-3
        return r.x, ok, r

    def initial(s, a, b, L):
        """A Bezier from guide (heading down/inward) to head (coming up), resampled to n equal chords of L/n."""
        L0 = L or 1.15 * np.linalg.norm(b - a) + 20
        best = None
        for h in np.linspace(0.1, 1.2, 23):
            c = [a, a + np.array([0, 0, -1.0]) * h * L0 * 0.5, b + np.array([0, 0, 1.0]) * h * L0 * 0.5, b]
            t = np.linspace(0, 1, 2001)[:, None]
            P = (1 - t)**3 * c[0] + 3 * (1 - t)**2 * t * c[1] + 3 * (1 - t) * t**2 * c[2] + t**3 * c[3]
            l = np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1))
            if best is None or abs(l - L0) < abs(best[0] - L0): best = (l, P)
        l, P = best
        cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        X = np.array([np.interp(np.linspace(0, l, s.n + 1), cum, P[:, k]) for k in range(3)]).T
        v = X[1:-1].ravel()
        return np.append(v, l) if L is None else v


def metrics(X):
    D = np.diff(X, axis=0); ds = np.linalg.norm(D, axis=1).mean()
    t = D / np.linalg.norm(D, axis=1)[:, None]
    ang = np.arccos(np.clip(np.sum(t[1:] * t[:-1], axis=1), -1, 1))
    tN = np.vstack([t, [[0, 0, -1.0]]])
    angh = np.arccos(np.clip(np.sum(tN[1:] * tN[:-1], axis=1), -1, 1))
    R = ds / max(angh.max(), 1e-9)
    guide_angle = math.degrees(math.acos(np.clip(-t[0, 2], -1, 1)))  # 0 = straight down out of the guide
    return {"lowest": float(X[:, 2].min()), "minR": float(R), "guide_deg_from_down": guide_angle}


def seg_dist(P, Q):
    """Exact minimum distance between two polylines: every segment pair, clamped closest points (Ericson,
    Real-Time Collision Detection 5.1.9). Vertex-to-segment alone misses two segments crossing in an X."""
    A0, A1, B0, B1 = P[:-1, None], P[1:, None], Q[None, :-1], Q[None, 1:]
    d1, d2, r = A1 - A0, B1 - B0, A0 - B0
    a = np.sum(d1 * d1, -1); e = np.sum(d2 * d2, -1); f = np.sum(d2 * r, -1)
    c = np.sum(d1 * r, -1); b = np.sum(d1 * d2, -1)
    den = a * e - b * b
    s = np.where(den > 1e-12, np.clip((b * f - c * e) / np.where(den > 1e-12, den, 1), 0, 1), 0.0)
    t = (b * s + f) / e
    s = np.where(t < 0, np.clip(-c / a, 0, 1), np.where(t > 1, np.clip((b - c) / a, 0, 1), s))
    t = np.clip(t, 0, 1)
    C1 = A0 + s[..., None] * d1; C2 = B0 + t[..., None] * d2
    return float(np.linalg.norm(C1 - C2, axis=-1).min())
