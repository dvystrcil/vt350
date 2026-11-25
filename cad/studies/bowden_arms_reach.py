"""Per-tool bowden arms (vt350#312), AC1: the geometry. Plain python3 + numpy + scipy; read-only, opens no model.

The idea (owner, 2026-11-24): one arm per tool, hinged on the rear top bar, each with a loop at its free end that the
tool's bundle (PTFE + O2S USB cable) passes through. A five-lobe cam on one shaft, turned by a stepper, lowers only
the active tool's arm, so its bundle hangs below the four parked ones, which stay up near the ceiling. It adds to the
roof-exit clamps (lite-36/70) and the cable channel (lite-40/71).

Model: each bundle is an inextensible elastic rod (the discrete rod of #244's cad/studies/lanyard/lrod.py and
flap_guide/rod.py, with its numbers: weight, ceiling Z 679, walls, roof exits). The arm's loop splits it into two
spans: the roof span (from the 45 deg roof exit, lite-70, its bore setting the direction, to the loop) and the head
span (from the loop, where the direction is free, to the head's O2S lock, entered straight down). Two loop modes:
  - tied: the bundle is zip-tied in the loop. The roof span gets one fixed length that suits the raised and the
    lowered loop; the head span is cut to the longest any head position needs (free length under a light take-up,
    as #244), then walked at that fixed length. Its slack has nowhere to go: it sags below the lock and bends tight;
    no design passes (the search logs it, for the record);
  - slide: the bundle slides through the loop and through a guide in the roof exit, and a take-up above the roof
    (#218's reel, a weight or a spring) keeps a light pull TAKEUP on it. Both spans take whatever length the pull
    leaves them. This is the mode the study verifies; its take-up travel is reported.
At the loop the bundle turns from one span into the other; the loop's flare takes that turn (its angle is reported).
The bend at the lock: wherever the head is, the bundle leaves the lock straight up and is pulled sideways, and the
tightest bend sits right there, set by the tube's stiffness and the pull (an elastica's boundary layer, length
~sqrt(EI / T)), not by the arm. #244's no-arm route shows the same (R ~42 at EI 2000). So the bends within LOCK_ZONE
of the lock are reported apart from all the others.

Per arm design (hinge, arm length, raised and lowered loop) the study walks every head over the lite-78 printable
area with its arm lowered, parks it (docked, arm raised), and checks: every position solved, every bend >= R 51
(lite-40's limit, 10 x the O2S cable's 5.1 OD) away from the lock and, apart, at the lock; no bundle sags below its
own lock (into the gantry); the lowered loop and arm stay clear of the moving gantry and heads (their top as a
profile over Y, from lite-79); how close the active bundle comes to the four parked ones. The verification also
walks a head with its arm stuck up (a cam stall, AC3).

Head positions are the O2S LOCK's, not the nozzle's: the lock's channel sits (+0.28, +43.38) from the nozzle tip on
both head types (lite-79: nozzle Y -49.46, lock box Y -12.71..-0.68; lite-78's front +17 moved the docks and locks
17.00 mm forward of lite-35's). The printable area is the nozzle's: X -416 .. -74 (sweep_toolhead, both heads), Y
30.5 .. 370.69 (the print square's front edge; the gantry's rear stop), from cad/data/logs/sweep_toolhead.log on
lite-78. So the lock covers X -415.72 .. -73.72, Y 73.88 .. 414.07.

    python3 cad/studies/bowden_arms_reach.py            # search, then verify the best design (10 workers)
    python3 cad/studies/bowden_arms_reach.py verify     # verify only the design in bowden_arms_design.json
Writes cad/data/logs/bowden_arms_reach.log, and cad/data/bowden_arms_design.json (the chosen design, read by the
FreeCAD clearance study cad/studies/bowden_arms.py). Tests: cad/studies/test_bowden_arms.py."""
import json, math, os, sys, time
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_v, "1")
import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lanyard"))
import lrod  # noqa: E402
from rod import seg_dist  # noqa: E402  (flap_guide/rod.py, on lrod's path)

CAD = os.path.dirname(HERE)
LOG = os.path.join(CAD, "data", "logs", "bowden_arms_reach.log")
DESIGN = os.path.join(CAD, "data", "bowden_arms_design.json")

# --- the printer (lite-78/79) ---------------------------------------------------------------------------------------
MIN_R = 51.0                                   # lite-40: 10 x the O2S cable's OD (5.1 mm, measured)
NOZZLE_DOCK = {1: -409.70, 2: -324.54, 3: -248.42, 4: -156.42, 5: -80.30}   # docked nozzle X (lite-79 probe)
NOZZLE_DOCK_Y = -49.46
LOCK_FROM_NOZZLE = (0.28, 43.38)               # lock channel - nozzle tip, XY, both head types (lite-79)
REACH_X, REACH_Y = (-416.0, -74.0), (30.5, 370.69)   # nozzle, lite-78 printable area (sweep_toolhead.log)
HEAD_Z = lrod.HEAD_Z                           # 550.11, the lock's top (lite-79 probe: 550.11)
GANTRY_RAISE = {"now": 0.0, "+10.3": 10.3}     # #243
# what moves in XY, as a profile over Y: (Y max, Z top) over the whole travel, gantry at its rear stop (dY +145.43)
MOVING = [(423.58, 550.37), (440.0, 448.5)]    # carried head (O2S restraint body top), gantry (VC9-J* joints)
MARGIN = 10.0                                  # what the lowered arm and loop keep above the moving parts' top
LOOP_R = 14.0                                  # the loop ring's outer radius (bundle 9.2 wide + the flare)
ARM_HALF = 6.0                                 # the arm's half depth (12 mm tall section)
BUNDLE_W = 9.2                                 # PTFE 4 + cable 5.1 side by side (#244)
EIS = [700.0, 2000.0, 7000.0]                  # N mm^2; not measured yet (#3 asks for a cantilever test)
N_HEAD, N_ROOF = 30, 12                        # rod segments per span
TAKEUP = 0.2                                   # N, the take-up's pull on a sliding bundle (#244's value)
LOCK_ZONE = 60.0                               # mm of bundle above the O2S lock whose bends are reported apart
DOWN = np.array([0.0, 0.0, -1.0])              # into the lock: the head span arrives going down


def lock_xy(nozzle_xy):
    return (nozzle_xy[0] + LOCK_FROM_NOZZLE[0], nozzle_xy[1] + LOCK_FROM_NOZZLE[1])


def dock_lock(slot):
    return lock_xy((NOZZLE_DOCK[slot], NOZZLE_DOCK_Y))


def _grid(lo, hi, step):
    v = list(np.arange(lo, hi - 1e-6, step))
    return np.array(v + [hi])


def path(slot, step, dz=0.0):
    """Lock positions: docked, out of the dock, then a serpentine over the printable area (nearest side first)."""
    xs, ys = _grid(*REACH_X, step), _grid(*REACH_Y, step)
    dx = NOZZLE_DOCK[slot]
    n_out = int(math.ceil((ys[0] - NOZZLE_DOCK_Y) / step))
    P = [(dx, NOZZLE_DOCK_Y)] + [(dx, y) for y in np.linspace(NOZZLE_DOCK_Y, ys[0], n_out + 1)[1:]]
    xo = xs if abs(xs[0] - dx) < abs(xs[-1] - dx) else xs[::-1]
    n_side = int(math.ceil(abs(xo[0] - dx) / step))
    P += [(x, ys[0]) for x in np.linspace(dx, xo[0], n_side + 1)[1:-1]]
    for j, y in enumerate(ys):
        P += [(x, y) for x in (xo if j % 2 == 0 else xo[::-1])]
    return [np.array([*lock_xy(p), HEAD_Z + dz]) for p in P]


# --- the arm -------------------------------------------------------------------------------------------------------
def loop_at(hinge, arm, z):
    """Loop centre (Y, Z) on the arm's circle at height z, forward of the hinge (-Y). None if out of reach."""
    hy, hz = hinge
    d = arm * arm - (hz - z) ** 2
    return None if d < 0 else (hy - math.sqrt(d), z)


def moving_top(y, dz=0.0):
    """Top Z of anything that moves in XY and can be at this Y (None = nothing reaches it)."""
    for ymax, ztop in MOVING:
        if y <= ymax: return ztop + dz
    return None


def arm_clear_of_moving(hinge, loop, dz=0.0, n=200):
    """Smallest gap (mm) between the arm (a bar from hinge to loop, ARM_HALF deep) plus the loop ring and the moving
    parts' top profile, over the arm's length. +inf if nothing moving reaches under it."""
    hy, hz = hinge; ly, lz = loop
    gap = math.inf
    pts = [(hy + t * (ly - hy), hz + t * (lz - hz) - ARM_HALF) for t in np.linspace(0, 1, n)]
    pts += [(ly + LOOP_R, lz - LOOP_R), (ly - LOOP_R, lz - LOOP_R)]
    for y, z in pts:
        top = moving_top(y, dz)
        if top is not None: gap = min(gap, z - top)
    return gap


# --- the rod --------------------------------------------------------------------------------------------------------
class Span:
    """One span of the bundle, as lrod.Rod (same discrete energy: bending EI, weight w, inextensible chords; the
    ceiling and the frame's inner faces as contact), but each end either CLAMPED along a given tangent (traversed
    from end a to end b) or PINNED (None: the tangent is free). Clamped at both ends it is lrod.Rod exactly."""

    def __init__(s, EI, n, g0=None, g1=None, w=lrod.W_LIN, z_ceil=lrod.Z_CEIL):
        s.EI, s.n, s.w, s.zc = EI, n, w, z_ceil
        s.g0 = None if g0 is None else np.asarray(g0, float)
        s.g1 = None if g1 is None else np.asarray(g1, float)

    def unpack(s, v, a, b, L):
        X = np.empty((s.n + 1, 3)); X[0] = a; X[-1] = b; X[1:-1] = v[:3 * (s.n - 1)].reshape(-1, 3)
        return X, (v[-1] if L is None else L)

    def energy(s, v, a, b, L, T):
        free = L is None
        X, L = s.unpack(v, a, b, L)
        n, EI, w = s.n, s.EI, s.w
        ds = L / n
        D = np.diff(X, axis=0)
        S = np.sum(D[1:] * D[:-1])
        J = (n - 1) + (s.g0 is not None) + (s.g1 is not None)        # joints, the clamps' ghosts included
        c0 = float(s.g0 @ D[0]) if s.g0 is not None else 0.0
        c1 = float(s.g1 @ D[-1]) if s.g1 is not None else 0.0
        E = EI * J / ds - EI * S / ds**3 - EI * (c0 + c1) / ds**2
        zs = X[1:-1, 2].sum() + 0.5 * (X[0, 2] + X[-1, 2])
        E += w * ds * zs + T * L
        gD = np.zeros_like(D)
        gD[1:] += -EI / ds**3 * D[:-1]; gD[:-1] += -EI / ds**3 * D[1:]
        if s.g0 is not None: gD[0] += -EI / ds**2 * s.g0
        if s.g1 is not None: gD[-1] += -EI / ds**2 * s.g1
        gX = np.zeros_like(X)
        gX[1:] += gD; gX[:-1] -= gD
        gX[1:-1, 2] += w * ds
        g = gX[1:-1].ravel()
        if free:
            dEds = -EI * J / ds**2 + 3 * EI * S / ds**4 + 2 * EI * (c0 + c1) / ds**3 + w * zs
            g = np.append(g, dEds / n + T)
        return E, g

    def cons(s, a, b, L):
        n, m, free = s.n, s.n - 1, L is None
        def ceq(v):
            X, LL = s.unpack(v, a, b, L)
            D = np.diff(X, axis=0)
            return (np.sum(D * D, axis=1) - (LL / n) ** 2) / (LL / n)
        def jeq(v):
            X, LL = s.unpack(v, a, b, L)
            D = np.diff(X, axis=0); ds = LL / n
            Jm = np.zeros((n, v.size))
            for i in range(n):
                if i < m: Jm[i, 3 * i:3 * i + 3] += 2 * D[i] / ds
                if i > 0: Jm[i, 3 * (i - 1):3 * i] -= 2 * D[i] / ds
            if free:
                Jm[:, -1] = (-np.sum(D * D, axis=1) / ds**2 - 1) / n
            return Jm
        def cin(v):
            P = v[:3 * m].reshape(-1, 3)
            return np.concatenate([s.zc - P[:, 2], P[:, 0] - lrod.X_WALL[0], lrod.X_WALL[1] - P[:, 0],
                                   P[:, 1] - lrod.Y_WALL[0], lrod.Y_WALL[1] - P[:, 1]])
        Jin = np.zeros((5 * m, 3 * m + (1 if free else 0)))
        for i in range(m):
            Jin[i, 3 * i + 2] = -1; Jin[m + i, 3 * i] = 1; Jin[2 * m + i, 3 * i] = -1
            Jin[3 * m + i, 3 * i + 1] = 1; Jin[4 * m + i, 3 * i + 1] = -1
        return ceq, jeq, cin, Jin

    def solve(s, a, b, x0, L, T, iters=500):
        ceq, jeq, cin, Jin = s.cons(a, b, L)
        cons = [{"type": "eq", "fun": ceq, "jac": jeq}, {"type": "ineq", "fun": cin, "jac": lambda v: Jin}]
        bounds = None
        if L is None:
            bounds = [(None, None)] * (3 * (s.n - 1)) + [(np.linalg.norm(b - a) * 1.0005, 3000.0)]
        r = minimize(s.energy, x0, args=(a, b, L, T), jac=True, method="SLSQP", constraints=cons, bounds=bounds,
                     options={"maxiter": iters, "ftol": 1e-10})
        ok = bool(r.success and np.max(np.abs(ceq(r.x))) < 1e-3 and np.min(cin(r.x)) > -1e-3)
        return r.x, ok, r

    def initial(s, a, b, L, ta=None, tb=None):
        """A Bezier leaving a along ta and arriving at b along tb (the clamps' tangents where clamped), resampled to n
        equal chords, its handles picked to match L; None if L is shorter than the straight span."""
        free = L is None
        d = np.linalg.norm(b - a)
        if not free and L < d * 1.0005: return None
        L0 = 1.15 * d + 20 if free else L
        u = (b - a) / d
        ta = s.g0 if s.g0 is not None else (u if ta is None else ta)
        tb = s.g1 if s.g1 is not None else (u if tb is None else tb)
        t = np.linspace(0, 1, 1501)[:, None]; best = None
        for h in np.linspace(0.02, 1.6, 50):
            c1, c2 = a + ta * h * L0 * 0.5, b - tb * h * L0 * 0.5
            Q = (1 - t)**3 * a + 3 * (1 - t)**2 * t * c1 + 3 * (1 - t) * t**2 * c2 + t**3 * b
            Q[:, 2] = np.minimum(Q[:, 2], s.zc - 0.01)
            l = np.sum(np.linalg.norm(np.diff(Q, axis=0), axis=1))
            if best is None or abs(l - L0) < abs(best[0] - L0): best = (l, Q)
        l, Q = best
        cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))])
        X = np.array([np.interp(np.linspace(0, l, s.n + 1), cum, Q[:, j]) for j in range(3)]).T
        v = X[1:-1].ravel()
        return np.append(v, l) if free else v


def shape(R, X, zone=0.0):
    """Tightest bend over the span (the clamps' ghost joints included, not a pinned end), lowest node, the end
    tangents, the length of ceiling contact. zone > 0: the bends within `zone` mm of end b (the lock) are reported
    apart (minR_zone), and minR_body is every other joint."""
    D = np.diff(X, axis=0); ds = np.linalg.norm(D, axis=1).mean()
    t = D / np.linalg.norm(D, axis=1)[:, None]
    tt = t
    if R.g0 is not None: tt = np.vstack([[R.g0], tt])
    if R.g1 is not None: tt = np.vstack([tt, [R.g1]])
    ang = np.arccos(np.clip(np.sum(tt[1:] * tt[:-1], axis=1), -1, 1))
    Rj = ds / np.maximum(ang, 1e-9)
    # arc distance of each joint from end b: the joints are at the nodes, the last one (a clamp's ghost) at b itself
    nj = len(Rj)
    dist = (nj - 1 - np.arange(nj)) * ds
    inz = dist <= zone + 1e-9 if zone > 0 else np.zeros(nj, bool)
    on = X[:, 2] >= R.zc - 0.25
    ceil = float(sum(ds for i in range(1, len(X) - 1) if on[i] and on[i + 1]))
    return dict(minR=float(Rj.min()), minR_body=float(Rj[~inz].min()) if (~inz).any() else math.inf,
                minR_zone=float(Rj[inz].min()) if inz.any() else math.inf,
                lowest=float(X[:, 2].min()), t0=t[0], t1=t[-1], ceiling_mm=ceil)


def solve_span(R, a, b, L, T, prev=None, ta=None, tb=None):
    """Solve from the previous shape if there is one, else from the Bezier; the converged one with less energy."""
    starts = [x for x in (prev, R.initial(a, b, L, ta, tb)) if x is not None]
    best = None
    for x0 in starts:
        x, ok, r = R.solve(a, b, x0, L, T)
        if ok and (best is None or r.fun < best[2].fun): best = (x, ok, r)
        if ok and prev is not None: break
    return best


def turn_deg(t_in, t_out):
    return math.degrees(math.acos(float(np.clip(np.dot(t_in, t_out), -1, 1))))


# --- one arm design -------------------------------------------------------------------------------------------------
def roof_span(slot, design, EI, mode="slide"):
    """The roof span for the raised and the lowered loop. slide: free length under the take-up pull (the bundle runs
    through a guide in the roof exit, its bore still setting the direction). tied: one fixed length, the one with the
    largest tightest bend over both loop positions."""
    a = lrod.exit_point(slot)
    xs = lrod.EXIT_X[slot]
    Ps = [np.array([xs, *design["loop_up"]]), np.array([xs, *design["loop_down"]])]
    def solve_both(L, T):
        out = []
        for P in Ps:
            R = Span(EI, N_ROOF, g0=-lrod.EXIT_DIR)
            s = solve_span(R, a, P, L, T, tb=(P - a) / np.linalg.norm(P - a))
            if s is None: return None
            X, LL = R.unpack(s[0], a, P, L)
            out.append((X, LL, shape(R, X)))
        return out
    if mode == "slide":
        out = solve_both(None, TAKEUP)
        if out is None: return None
        cands = [(min(o[2]["minR"] for o in out), None, out)]
    else:
        dmax = max(np.linalg.norm(P - a) for P in Ps)
        cands = []
        for f in (1.01, 1.03, 1.06, 1.1, 1.15, 1.2, 1.3, 1.4, 1.55, 1.7):
            out = solve_both(dmax * f, 0.0)
            if out is not None: cands.append((min(o[2]["minR"] for o in out), dmax * f, out))
        if not cands: return None
    mr, L, ((Xu, Lu, su), (Xd, Ld, sd)) = max(cands, key=lambda c: c[0])
    return dict(L_up=Lu, L_down=Ld, minR=mr, up=dict(X=Xu, **su), down=dict(X=Xd, **sd))


def walk(args):
    """One slot, one arm design, one EI, one gantry height, one loop mode: the head span over the printable area
    (loop lowered), then parked (docked, loop raised).
      mode slide: free lengths under the take-up pull TAKEUP, everywhere;
      mode tied:  Lfix None = free length with the take-up pull (stage 1, to find the cut length), else that fixed
                  length (stage 2, and parked).
    stuck=True: the cam failed to lower the arm, so the head walks with its loop still up (a stall, AC3)."""
    slot, design, EI, raise_, step, mode, Lfix, stuck = args
    xs = lrod.EXIT_X[slot]
    P_down, P_up = np.array([xs, *design["loop_down"]]), np.array([xs, *design["loop_up"]])
    loop = "up" if stuck else "down"
    P_walk = P_up if stuck else P_down
    roof = roof_span(slot, design, EI, mode)
    T = TAKEUP if (mode == "slide" or Lfix is None) else 0.0
    dz = GANTRY_RAISE[raise_]
    pts = path(slot, step, dz)
    key = (slot, design["name"], EI, raise_, mode) + (("stuck up",) if stuck else ())
    if roof is None:
        return key, dict(roof=None, walk=[dict(ok=False)] * len(pts), parked=dict(ok=False))
    R = Span(EI, N_HEAD, g1=DOWN)
    out, prev = [], None
    for b in pts:
        s = solve_span(R, P_walk, b, Lfix, T, prev, ta=roof[loop]["t1"])
        if s is None:
            out.append(dict(ok=False, head=b[:2].round(2).tolist())); prev = None; continue
        prev = s[0]
        X, LL = R.unpack(s[0], P_walk, b, Lfix)
        m = shape(R, X, LOCK_ZONE)
        out.append(dict(ok=True, head=b[:2].round(2).tolist(), L=float(LL), minR_body=m["minR_body"],
                        minR_lock=m["minR_zone"], lowest=m["lowest"], ceiling_mm=m["ceiling_mm"],
                        turn=turn_deg(roof[loop]["t1"], m["t0"]), X=X.round(2).tolist()))
    parked = dict(ok=False)
    if mode == "slide" or Lfix is not None:
        s = solve_span(R, P_up, pts[0], Lfix, T, ta=roof["up"]["t1"])
        if s is not None:
            X, LL = R.unpack(s[0], P_up, pts[0], Lfix)
            m = shape(R, X, LOCK_ZONE)
            parked = dict(ok=True, L=float(LL), minR_body=m["minR_body"], minR_lock=m["minR_zone"], lowest=m["lowest"],
                          turn=turn_deg(roof["up"]["t1"], m["t0"]), X=X.round(2).tolist())
    rs = dict(L_up=roof["L_up"], L_down=roof["L_down"], minR=roof["minR"], up=roof["up"]["X"].round(2).tolist(),
              down=roof["down"]["X"].round(2).tolist(), lowest=min(roof["up"]["lowest"], roof["down"]["lowest"]))
    return key, dict(roof=rs, walk=out, parked=parked)


def designs():
    """The search grid: two hinge places on the rear top 4040 (Y 480..520, Z 650..690), arm lengths, lowered heights.
    Raised: the loop's top 3 mm under the ceiling felt (Z 679)."""
    hinges = {"under the bar": (490.0, 640.0),   # 640: the raised arm, tilting up to its loop, passes 3 mm under the
              "bar front face": (474.0, 665.0)}  # bar's front edge (at 643 it was 0.26, bowden_arms.py)
    z_up = lrod.Z_CEIL - 3.0 - LOOP_R
    out = []
    for hname, h in hinges.items():
        for arm in (120.0, 180.0, 240.0, 300.0, 360.0):
            up = loop_at(h, arm, z_up)
            for z in (640.0, 615.0, 590.0):
                lo = loop_at(h, arm, z)
                if up is None or lo is None or z >= z_up - 5: continue
                d = dict(name=f"{hname}, arm {arm:.0f}, down Z {z:.0f}", hinge=list(h), arm=arm,
                         loop_up=[round(up[0], 2), round(up[1], 2)], loop_down=[round(lo[0], 2), round(lo[1], 2)])
                d["clear_moving"] = {k: round(arm_clear_of_moving(h, lo, dz), 1) for k, dz in GANTRY_RAISE.items()}
                out.append(d)
    return out


def full_polyline(r, which):
    """Roof span + head span, as one polyline. which: 'parked' (loop up, docked) or a walk record (loop down)."""
    roof = np.array(r["roof"]["up" if which == "parked" else "down"])
    head = np.array(r["parked"]["X"] if which == "parked" else which["X"])
    return np.vstack([roof, head[1:]])


def summarise(res, design, slots, raise_, EI, mode):
    """Per design + EI + gantry height + mode: the checks over every slot."""
    rows, parked = {}, {}
    for s in slots:
        r = res[(s, design["name"], EI, raise_, mode)]
        if r["roof"] is not None and r["parked"]["ok"]: parked[s] = full_polyline(r, "parked")
    lock_z = HEAD_Z + GANTRY_RAISE[raise_]
    for s in slots:
        r = res[(s, design["name"], EI, raise_, mode)]
        ok = [p for p in r["walk"] if p.get("ok")]
        pk = r["parked"]
        if r["roof"] is None or not ok or not pk["ok"]:
            rows[s] = dict(solved=False, unsolved=len(r["walk"]) - len(ok), n=len(r["walk"]),
                           roof_ok=r["roof"] is not None, parked_ok=pk["ok"])
            continue
        others = [o for o in parked if o != s]
        gaps = [min(seg_dist(full_polyline(r, p), parked[o]) for o in others) - BUNDLE_W for p in ok[1:]] if others else [math.inf]
        total = [r["roof"]["L_down"] + p["L"] for p in ok] + [r["roof"]["L_up"] + pk["L"]]
        rows[s] = dict(solved=len(ok) == len(r["walk"]), unsolved=len(r["walk"]) - len(ok), n=len(r["walk"]),
                       roof_ok=True, parked_ok=True,
                       bundle_L=[round(min(total)), round(max(total))], takeup_travel=round(max(total) - min(total)),
                       roof_minR=round(r["roof"]["minR"], 1),
                       body_minR=round(min(min(p["minR_body"] for p in ok), pk["minR_body"]), 1),
                       lock_minR=round(min(min(p["minR_lock"] for p in ok), pk["minR_lock"]), 1),
                       lowest_below_lock=round(min(min(p["lowest"] for p in ok), r["roof"]["lowest"]) - lock_z, 1),
                       loop_turn_max=round(max(max(p["turn"] for p in ok), pk["turn"])),
                       ceiling_pct=round(100 * sum(p["ceiling_mm"] > 0 for p in ok) / len(ok)),
                       to_parked_min=round(min(gaps), 1), touch_parked_pct=round(100 * sum(g < 0 for g in gaps) / len(gaps)),
                       parked_lowest=round(pk["lowest"] - lock_z, 1))
    return rows


def passes(rows, design, raise_):
    """AC1 away from the lock: every position solved and parked, every bend >= MIN_R except within LOCK_ZONE of the
    O2S lock (reported apart: the arms can't change it), nothing below its lock, the arm clear of the moving parts."""
    if not all(r["solved"] and r["parked_ok"] for r in rows.values()): return False
    return (min(min(r["body_minR"], r["roof_minR"]) for r in rows.values()) >= MIN_R
            and min(r["lowest_below_lock"] for r in rows.values()) >= -0.5
            and design["clear_moving"][raise_] >= MARGIN)


def lock_ok(rows):
    return all(r.get("lock_minR", 0) >= MIN_R for r in rows.values())


def run_modes(pool, ds, slots, EIs, raises, step, modes):
    """slide: one stage. tied: free length -> the head span's cut length -> fixed length + parked."""
    jobs = [(s, d, e, h, step, m, None, False) for m in modes for d in ds for s in slots for e in EIs for h in raises]
    res = dict(pool.imap_unordered(walk, jobs))
    if "tied" in modes:
        jobs = []
        for d in ds:
            for s in slots:
                for e in EIs:
                    for h in raises:
                        r = res[(s, d["name"], e, h, "tied")]
                        ok = [p for p in r["walk"] if p.get("ok")]
                        if ok and len(ok) == len(r["walk"]):
                            jobs.append((s, d, e, h, step, "tied", max(p["L"] for p in ok), False))
                        else:
                            r["parked"] = dict(ok=False)
        res.update(dict(pool.imap_unordered(walk, jobs)))
    return res


def main():
    from multiprocessing import Pool
    verify_only = len(sys.argv) > 1 and sys.argv[1] == "verify"
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    f = open(LOG, "w"); t0 = time.time()
    def log(*a):
        s = f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a); print(s, flush=True); f.write(s + "\n"); f.flush()
    log("vt350#312 bowden arms, AC1 geometry (read-only; bowden_arms_reach.py)")
    log(f"lock reach X {lock_xy((REACH_X[0], 0))[0]:.2f} .. {lock_xy((REACH_X[1], 0))[0]:.2f}, "
        f"Y {lock_xy((0, REACH_Y[0]))[1]:.2f} .. {lock_xy((0, REACH_Y[1]))[1]:.2f}; lock top Z {HEAD_Z}; ceiling Z {lrod.Z_CEIL}")
    log(f"moving parts' top (Y max, Z top): {MOVING}; the lowered arm + loop keep >= {MARGIN} above; bend limit R {MIN_R}; "
        f"the lock zone (reported apart) is the bundle's last {LOCK_ZONE:.0f} mm; take-up pull {TAKEUP} N")
    with Pool(int(os.environ.get("ARMS_WORKERS", "10"))) as pool:
        if verify_only:
            best = json.load(open(DESIGN))["design"]
        else:
            ds = designs()
            log(f"search: {len(ds)} designs x loop tied / sliding; slots 1, 3, 5; EI 2000; gantry now; step 68")
            for d in ds: log(f"   {d['name']}: loop up {d['loop_up']}, down {d['loop_down']}, arm clear of moving {d['clear_moving']}")
            ds_ok = [d for d in ds if d["clear_moving"]["+10.3"] >= MARGIN]
            log(f"   {len(ds_ok)} keep >= {MARGIN} over the moving parts with the gantry +10.3; searching those")
            res = run_modes(pool, ds_ok, (1, 3, 5), [2000.0], ["now"], 68.0, ("tied", "slide"))
            scored = []
            for mode in ("tied", "slide"):
                npass = 0
                for d in ds_ok:
                    rows = summarise(res, d, (1, 3, 5), "now", 2000.0, mode)
                    ok = passes(rows, d, "now")
                    npass += ok
                    log(f"   {'PASS' if ok else 'fail'} [{mode}] {d['name']}")
                    for s, r in rows.items(): log(f"        slot {s}: {r}")
                    if mode == "slide":
                        # the lock's bend first (the lower the loop drops, the tighter the bundle turns out of the
                        # lock: 40 mm over it, ~90 deg in 40 mm), then no contact with a parked bundle, then the
                        # take-up's travel
                        scored.append(((ok, round(min(r.get("lock_minR", 0) for r in rows.values())),
                                        -max(r.get("touch_parked_pct", 100) for r in rows.values()),
                                        -max(r.get("takeup_travel", 9999) for r in rows.values())), d))
                log(f"search [{mode}]: {npass} of {len(ds_ok)} designs pass (bends away from the lock, sag, arm clearance)")
            scored.sort(key=lambda t: t[0], reverse=True)
            best = scored[0][1]
            log(f"search: {'best' if scored[0][0][0] else 'NO design passes; closest'} (sliding loop): {best['name']}")
        log(f"verify: {best['name']}, sliding loop; all 5 slots; EI {EIS}; gantry {list(GANTRY_RAISE)}; step 34")
        res = run_modes(pool, [best], (1, 2, 3, 4, 5), EIS, list(GANTRY_RAISE), 34.0, ("slide",))
        stuck = dict(pool.imap_unordered(walk, [(s, best, e, "now", 34.0, "slide", None, True)
                                                for s in range(1, 6) for e in EIS]))
    allok, lockok, table = True, True, []
    for h in GANTRY_RAISE:
        for e in EIS:
            rows = summarise(res, best, (1, 2, 3, 4, 5), h, e, "slide")
            ok, lk = passes(rows, best, h), lock_ok(rows)
            allok &= ok; lockok &= lk
            table.append(dict(raise_=h, EI=e, ok=ok, lock_ok=lk, slots=rows))
            lr = min(r.get("lock_minR", 0) for r in rows.values())
            log(f"   {'PASS' if ok else 'FAIL'} gantry {h}, EI {e:.0f}: away from the lock "
                f"{'ok' if ok else 'NOT ok'}; at the lock R {lr:.1f} ({'ok' if lk else f'< {MIN_R:.0f}'})")
            for s, r in rows.items(): log(f"      slot {s}: {r}")
    log("if the cam stalls with the new tool's arm still UP (sliding loop, gantry now):")
    for e in EIS:
        for s in range(1, 6):
            r = stuck[(s, best["name"], e, "now", "slide", "stuck up")]
            ok = [p for p in r["walk"] if p.get("ok")]
            log(f"   EI {e:.0f} slot {s}: {len(r['walk']) - len(ok)} of {len(r['walk'])} positions unsolved"
                + (f"; tightest bend away from the lock {min(p['minR_body'] for p in ok):.1f}, at the lock "
                   f"{min(p['minR_lock'] for p in ok):.1f}; lowest {min(p['lowest'] for p in ok) - HEAD_Z:+.1f} from "
                   f"the lock top" if ok else ""))
    json.dump(dict(design=best, mode="slide", takeup_N=TAKEUP, verify=table), open(DESIGN, "w"), indent=1)
    lock_by_ei = {e: min(min(r.get("lock_minR", 0) for r in t["slots"].values()) for t in table if t["EI"] == e) for e in EIS}
    body = min(min(r.get("body_minR", 0), r.get("roof_minR", 0)) for t in table for r in t["slots"].values())
    if allok and lockok:
        log(f"reach: every bed point reached, min bend R >= {MIN_R:.0f} (tightest {min(body, *lock_by_ei.values()):.1f}; "
            f"{best['name']}, sliding loop)")
    elif allok:
        # R at the lock grows about as sqrt(EI) (an elastica's boundary layer at a clamp, length sqrt(EI / T))
        need = max(e * (MIN_R / lock_by_ei[e]) ** 2 for e in EIS if lock_by_ei[e] > 0)
        log(f"reach: every bed point reached; every bend >= R {MIN_R:.0f} (tightest {body:.1f}) EXCEPT within "
            f"{LOCK_ZONE:.0f} mm of the O2S lock: R " + " / ".join(f"{lock_by_ei[e]:.1f}" for e in EIS)
            + f" at EI " + " / ".join(f"{e:.0f}" for e in EIS)
            + f"; that needs a bend limiter at the lock, or a bundle with EI >= ~{need:.0f} N mm^2 ({best['name']}, sliding loop)")
    else:
        log(f"reach: NOT every case passes; see the FAIL lines ({best['name']}, sliding loop)")
    log(f"wrote {DESIGN}")
    return 0 if allok and lockok else 1


if __name__ == "__main__":
    sys.exit(main())
