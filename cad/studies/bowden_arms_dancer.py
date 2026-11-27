"""Bowden arms with a dancer: the slack stays in the chamber (vt350#312 follow-up). Plain python3 + numpy + scipy;
read-only, opens no model.

    python3 cad/studies/bowden_arms_dancer.py          # ~10 min on 10 workers (ARMS_WORKERS)

The owner's correction (2026-11-25): the lines from the EMU to the roof are static, so the roof exit CLAMPS each bundle
and its whole length from there to the head is fixed. bowden_arms_reach.py's sliding loop assumed a take-up above the
roof; this replaces it with the owner's dancer, pulled down through a slot in the arm, its loop hanging behind the
gantry's rear stop where nothing moves (bowden_arms_rear_space.py measured that room). The route, per tool:

  roof exit (clamped, its 45 deg bore) -> the exit span, to a guide at Z_G above the pulley's nearer leg (the bundle
  leaves it straight down) -> the exit leg, straight down -> the dancer pulley, R RP, turning in the back wall's plane
  (axis along Y) -> the return leg, straight up -> its guide at Z_G -> the return span, up and forward to the arm's tip
  (point Q, Y_Q, arriving along the arm) -> the loop -> the head span (as bowden_arms_reach.py: pinned at the loop,
  clamped straight down into the O2S lock). The guides (Z_G, just above the heads' top) hold the free spans out of
  the gantry's and the heads' way: a first run without them bowed both spans into the gantry's rear-stop box.

The arms stay over their roof exits (owner, 2026-11-25). The pulleys hang low, behind the bed (bowden_arms_rear_space.py
with REAR_Z_LO=60: behind Y ~430 the rear is open from the gantry's level down to Z ~60, apart from the rear-centre Z
axis at X -263..-230, the corner idler plates and steppers, and the Z drag chain behind Y ~481). Their legs rise
through the 40 mm between the gantry at its rear stop (Y 440) and the rear 2020 (Y 480-500, Z 420-440). Layout,
PULLEY: two stacks of pulleys, one either side of the Z axis, each centred in its gap between a rear corner idler plate
and the Z axis (X -385.5..-262.9 and -229.8..-104.5; sheave 2 (RP + 4.6) wide with a 2 mm rim leaves ~2 mm a side),
each tool in its own plane Y (446 / 459 / 472, 13 mm apart): T0 T1 left, T2 T3 T4 right (T2 on the left, in plane
472, ran its leg 0.1 mm from a corner plate's M5 screw head). Both stacks return on their right leg (RETURN_SIDE),
planes in tool order: of 12 side / order layouts searched, this one bends least (every channel R >= 69). A stack's return channels leave from the same leg and fan
out to their arms (RETURN_SIDE). The channels are designed one after another, each keeping KEEP from those before it
(design_channels()): designed alone, neighbouring tools' channels crossed. The sheaves stay below the
gantry (the pulley's highest centre Z_TOP); only the legs pass up through the gap behind it, in planes Y 446..472. In
the sheave's groove the bundle lies with its two tubes one above the other (5.1 wide across the groove; the inner
tube at R RP - 2.55 = 52.45), so a sheave is ~10 mm thick.

The dancer is a weight W on the pulley (gravity: the same pull everywhere, so the bend at the lock stays put). Pull at
the pulley W/2 in each leg; the bundle's own weight adds w per mm of height up the legs, so the head span's pull at the
loop is T = W/2 + w (Z_ARM - z_pulley). The dancer hangs where the fixed total length puts it:
    L_rear(z) + L_arm + L_head(position, T) = L_total,
L_total chosen so that at the position needing the most length the pulley sits at its highest (Z_TOP). Each position
is solved twice (T from the first pass's pulley height, then again), which converges to well under a millimetre.

Reported per tool, EI and W: every position solved; the dancer's travel and lowest point (must clear the floor the
rear-space probe found: FLOOR); the bends: exit turn, return turn into the arm, the loop (the turn from the arm into
the head span: the loop's saddle must give at least R 51 over that angle), the head span away from the lock, the lock
zone; nothing below its lock; the pull at the loop. EI not measured yet (#3).
Writes cad/data/logs/bowden_arms_dancer.log and cad/data/bowden_arms_dancer.json."""
import json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import bowden_arms_reach as ba
lrod = ba.lrod

CAD = os.path.dirname(HERE)
LOG = os.path.join(CAD, "data", "logs", "bowden_arms_dancer.log")
OUT = os.path.join(CAD, "data", "bowden_arms_dancer.json")
DESIGN = json.load(open(ba.DESIGN))["design"]          # hinge (490, 640), arm 240, loop Z 662 up / 640 down

RP = 53.6                                  # dancer pulley: the bundle's centreline radius; the inner tube at 51.05
PULLEY = {1: (-324.2, 446.0), 2: (-324.2, 459.0),                       # (centre X, plane Y) per tool: each stack
          3: (-167.0, 446.0), 4: (-167.0, 459.0), 5: (-167.0, 472.0)}   # centred in its gap (corner plate | Z axis)
RETURN_SIDE = {1: +1, 2: +1, 3: +1, 4: +1, 5: +1}   # the return leg (cx + side RP): a stack's returns share a leg and
                                                    # fan out to their arms without crossing
Z_ARM = DESIGN["hinge"][1]                  # the arm's hinge-end height
LOCK_DZ = ba.GANTRY_RAISE["lite-80"]          # the locks ride with the gantry: lite-80 = lite-79's lock Z + 10
Y_Q = 255.0                                # the return span meets the arm's line here (Y): at its tip, by the loop
Z_G = float(os.environ.get("DANCER_Z_G", "470"))   # the channels' lower ends: just above the gantry (458.5 at lite-80's +10)
C_Y, C_Z = 340.0, 640.0                    # the return channel's upper end: forward over the heads, level, at X arm
                                           # (searched: Y 340..400 x Z 625..655; Y 340, Z 640 bends least, R >= 84)
HEAD_TOP = 560.37 + 10.0 + ba.BUNDLE_W / 2 + 4.0   # nothing of a channel in front of Y_HEADS lower than this
Y_HEADS = 423.58 + ba.BUNDLE_W / 2 + 4.0
Z_TOP = float(os.environ.get("DANCER_Z_TOP", "340"))   # the pulley's highest centre: the sheave (R RP + 4.6 + 3 rim)
                                                       # stays under the gantry (Z 411.5): only its legs pass up
FLOOR = float(os.environ.get("DANCER_FLOOR", "60"))    # lowest pulley bottom (rear-space probe: open to Z 60)
WEIGHTS = [0.2, 0.4, 0.8]                  # N, the dancer (pulley + weight): 20, 41, 82 g
N_REAR, N_HEAD = 16, ba.N_HEAD
STEP = 34.0
UP = np.array([0.0, 0.0, 1.0])


def arm_x(slot):
    return lrod.EXIT_X[slot]


def legs(slot):
    """(exit leg X, return leg X): RETURN_SIDE picks the return leg, the exit leg is the other."""
    cx = PULLEY[slot][0]
    return cx - RETURN_SIDE[slot] * RP, cx + RETURN_SIDE[slot] * RP


def arm_dir(loop):
    hy, hz = DESIGN["hinge"]
    d = np.array([0.0, loop[0] - hy, loop[1] - hz]); return d / np.linalg.norm(d)


def q_point(slot, loop):
    """Where the return span meets the arm's line (Y_Q), on the arm raised or lowered."""
    hy, hz = DESIGN["hinge"]; u = arm_dir(loop)
    t = (Y_Q - hy) / u[1]
    return np.array([arm_x(slot), Y_Q, hz + t * u[2]])


def clear_of_moving(X, dz):
    """Smallest gap (mm) from the bundle's surface to the moving parts' top profile (bowden_arms_reach.MOVING: the
    carried heads to Y 423.58, the gantry to Y 440), over a span's nodes. +inf where nothing moving reaches."""
    g = math.inf
    for x, y, z in X:
        top = ba.moving_top(y, dz)
        if top is not None: g = min(g, z - ba.BUNDLE_W / 2 - top)
    return g


def bezier(a, ta, b, tb, h0, h1, n=400):
    t = np.linspace(0, 1, n)[:, None]
    c1, c2 = a + ta * h0, b - tb * h1
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * b


def min_radius(X):
    D = np.diff(X, axis=0); ds = np.linalg.norm(D, axis=1); t = D / ds[:, None]
    ang = np.arccos(np.clip(np.sum(t[1:] * t[:-1], axis=1), -1, 1))
    return float(np.min((ds[1:] + ds[:-1]) / 2 / np.maximum(ang, 1e-12)))


KEEP = 2 * ba.BUNDLE_W / 2 + 1.0 + 0.5      # centreline to centreline between tools' channels: touching + 1 + 0.5


def channel(a, ta, b, tb, avoid=()):
    """A fixed channel (printed or bent tube) from a along ta to b along tb: the cubic Bezier whose handles give the
    largest smallest bend radius while keeping out of the heads' reach (nothing in front of Y_HEADS below HEAD_TOP)
    and KEEP from every polyline in avoid. -> (polyline, length, min radius); None if no handle pair keeps out."""
    d = np.linalg.norm(b - a); best = None
    av = np.vstack(avoid) if len(avoid) else None
    for h0 in np.linspace(0.05, 1.6, 32) * d:
        for h1 in np.linspace(0.05, 1.6, 32) * d:
            X = bezier(a, ta, b, tb, h0, h1)
            if np.any((X[:, 1] < Y_HEADS) & (X[:, 2] < HEAD_TOP)): continue
            if np.any(X[:, 2] > lrod.Z_CEIL): continue
            r = min_radius(X)
            if best is not None and r <= best[2]: continue
            if av is not None:
                Xs = X[::4]
                if np.min(np.linalg.norm(Xs[:, None] - av[None], axis=2)) < KEEP: continue
            best = (X, h0, r, h1)
    if best is None: return None
    X = refine(a, ta, b, tb, best[1], best[3], av)
    if X is None: X = best[0]
    return X, float(np.sum(np.linalg.norm(np.diff(X, axis=0), axis=1))), min_radius(X)


def quintic(a, ta, b, tb, v, n=400):
    """A quintic Bezier from a along ta to b along tb: v = (h0, h1, P2 xyz, P3 xyz)."""
    P = [a, a + ta * v[0], v[2:5], v[5:8], b - tb * v[1], b]
    t = np.linspace(0, 1, n)[:, None]; c = [1, 5, 10, 10, 5, 1]
    return sum(c[i] * (1 - t) ** (5 - i) * t ** i * np.asarray(P[i]) for i in range(6))


def refine(a, ta, b, tb, h0, h1, av):
    """Loosen the best cubic channel: as a quintic (the cubic, degree-raised, to start), its two inner control points
    and both handles free, maximise the smallest bend radius under the same rules (Powell; penalties). None if the
    result breaks a rule."""
    from scipy.optimize import minimize
    c1, c2 = a + ta * h0, b - tb * h1
    # the cubic as a quintic: Q1 = (2 a + 3 c1)/5 etc.; keep its handles' directions, so only the lengths change
    q1 = (2 * a + 3 * c1) / 5; q2 = (a + 6 * c1 + 3 * c2) / 10; q3 = (3 * c1 + 6 * c2 + b) / 10; q4 = (3 * c2 + 2 * b) / 5
    v0 = np.concatenate([[np.linalg.norm(q1 - a), np.linalg.norm(b - q4)], q2, q3])
    def bad(X):
        pen = np.sum(np.clip(HEAD_TOP - X[:, 2], 0, None) * (X[:, 1] < Y_HEADS)) \
            + np.sum(np.clip(X[:, 2] - lrod.Z_CEIL, 0, None))
        if av is not None:
            dmin = np.min(np.linalg.norm(X[::4][:, None] - av[None], axis=2), axis=1)
            pen += np.sum(np.clip(KEEP - dmin, 0, None))
        return pen
    def f(v):
        if v[0] < 1 or v[1] < 1: return 1e6
        X = quintic(a, ta, b, tb, v)
        return -min(min_radius(X), 400.0) + 1e3 * bad(X)
    r = minimize(f, v0, method="Powell", options=dict(maxfev=6000, xtol=0.05, ftol=1e-3))
    X = quintic(a, ta, b, tb, r.x)
    if bad(X) > 0 or min_radius(X) < min_radius(quintic(a, ta, b, tb, v0)): return None
    return X


def dense(P, step=3.0):
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out += [a + (b - a) * (i / n) for i in range(1, n + 1)]
    return np.array(out)


_CH = {}
def design_channels():
    """Every tool's exit and return channel, designed in turn (exits first, then returns), each keeping KEEP from the
    channels already designed, from the top of every tool's legs (Z_G - 60 .. Z_G) and from every tool's free run
    (C -> the loop, arm down and up). -> {slot: (exit channel, return channel)}."""
    if _CH: return _CH
    ends, fixed = {}, []
    for s in PULLEY:
        (xe, xb), y = legs(s), PULLEY[s][1]
        ends[s] = (lrod.exit_point(s), np.array([xe, y, Z_G]), np.array([xb, y, Z_G]),
                   np.array([arm_x(s), C_Y, C_Z]))
        for x in (xe, xb):
            fixed.append(dense(np.array([[x, y, Z_G - 60.0], [x, y, Z_G]])))
        for loop in (DESIGN["loop_down"], DESIGN["loop_up"]):
            fixed.append(dense(np.array([ends[s][3], [arm_x(s), *loop]])))
    own = lambda s, X: [f for f in X if not f[1] is s]
    done = []                                   # (slot, dense polyline)
    ex, rt = {}, {}
    for s in sorted(PULLEY):
        a, Ge, Gr, C = ends[s]
        mine = {tuple(Ge.round(3)), tuple(Gr.round(3))}
        av = [f for f in fixed if tuple(f[-1].round(3)) not in mine and not np.allclose(f[0], C)] + [X for t, X in done]
        ex[s] = channel(a, -lrod.EXIT_DIR, Ge, ba.DOWN, av)
        if ex[s] is not None: done.append((s, ex[s][0][::4]))
    for s in sorted(PULLEY):
        a, Ge, Gr, C = ends[s]
        mine = {tuple(Ge.round(3)), tuple(Gr.round(3))}
        av = [f for f in fixed if tuple(f[-1].round(3)) not in mine and not np.allclose(f[0], C)] \
            + [X for t, X in done if t != s]
        rt[s] = channel(Gr, UP, C, np.array([0.0, -1.0, 0.0]), av)
        if rt[s] is not None: done.append((s, rt[s][0][::4]))
    _CH.update({s: (ex[s], rt[s]) for s in PULLEY})
    return _CH


def rear_spans(args):
    """The bundle behind the gantry, per tool: the exit channel (roof exit, along its 45 deg bore -> straight down at
    G_e, Z_G, over the exit leg), the legs (straight, G -> the pulley), the return channel (straight up at G_r -> level,
    forward, at C over the arm's X), and the free run from C to the loop (taut: a straight line, its length; the arm
    up or down). The channels' shapes are designed (channel()), not solved: they set the bends there.
    -> {z: (exit channel + leg, leg + return channel + free run, minR_exit, minR_return, exit polyline + leg,
    leg + return polyline + loop, clearance over the moving parts)} per pulley height, arm up and down."""
    slot, EI, W, zs = args
    a = lrod.exit_point(slot); (xe, xb), y = legs(slot), PULLEY[slot][1]
    Ge, Gr = np.array([xe, y, Z_G]), np.array([xb, y, Z_G])
    C = np.array([arm_x(slot), C_Y, C_Z])
    ce, cr = design_channels()[slot]
    out = {}
    for which, loop in (("down", DESIGN["loop_down"]), ("up", DESIGN["loop_up"])):
        if ce is None or cr is None: out[which] = {z: None for z in zs}; continue
        P = np.array([arm_x(slot), *loop])
        free = float(np.linalg.norm(P - C))
        Xe, Le, Re_R = ce; Xr, Lr, Rr_R = cr
        Xe_s, Xr_s = Xe[::25], np.vstack([Xr[::25], [Xr[-1]], [P]])
        clear = min(clear_of_moving(Xe_s, 10.0), clear_of_moving(Xr_s, 10.0))
        rows = {}
        for z in zs:
            leg = Z_G - z
            rows[z] = (Le + leg, leg + Lr + free, Re_R, Rr_R,
                       Xe_s.round(1).tolist() + [Ge.round(1).tolist(), [xe, y, round(z, 1)]],
                       [[xb, y, round(z, 1)]] + Xr_s.round(1).tolist(), clear)
        out[which] = rows
    return (slot, EI, W), out


def head_walk(args):
    """The head span over the walk (loop lowered) and parked (raised), each position at its own pull T (a list, one
    per position, + parked last), warm-started along the walk."""
    slot, EI, Ts = args
    xb = arm_x(slot)
    P_down, P_up = np.array([xb, *DESIGN["loop_down"]]), np.array([xb, *DESIGN["loop_up"]])
    pts = ba.path(slot, STEP, dz=LOCK_DZ)
    R = ba.Span(EI, N_HEAD, g1=ba.DOWN)
    def rec(P, b, prev, T, t_arm):
        s = ba.solve_span(R, P, b, None, T, prev, ta=t_arm)
        if s is None: return None, dict(ok=False)
        X, L = R.unpack(s[0], P, b, None); m = ba.shape(R, X, ba.LOCK_ZONE)
        return s[0], dict(ok=True, L=float(L), minR_body=m["minR_body"], minR_lock=m["minR_zone"],
                          lowest=m["lowest"], turn=ba.turn_deg(t_arm, m["t0"]), X=X.round(2).tolist())
    out, prev = [], None
    for b, T in zip(pts, Ts[:-1]):
        prev, r = rec(P_down, b, prev, T, arm_dir(DESIGN["loop_down"])); out.append(r)
    parked = rec(P_up, pts[0], None, Ts[-1], arm_dir(DESIGN["loop_up"]))[1]
    return (slot, EI), dict(walk=out, parked=parked, heads=[p[:2].round(2).tolist() for p in pts])


def rear_length(rear, z):
    """L_rear at pulley height z (linear between grid heights), + the pulley's half turn."""
    zs = sorted(k for k, v in rear.items() if v is not None)
    if not zs or z < zs[0] - 1e-6 or z > zs[-1] + 1e-6: return None
    L = [rear[k][0] + rear[k][1] for k in zs]
    return float(np.interp(z, zs, L)) + math.pi * RP


def pulley_at(rear, need):
    """The pulley height whose rear length is `need` (the rear length grows as the pulley drops)."""
    zs = sorted(k for k, v in rear.items() if v is not None)
    L = [rear[k][0] + rear[k][1] + math.pi * RP for k in zs]
    if need < min(L) - 1e-6: return zs[-1] + (min(L) - need) / 2            # above the grid: report how far
    if need > max(L) + 1e-6: return zs[0] - (need - max(L)) / 2              # below: likewise
    return float(np.interp(need, L[::-1], zs[::-1]))


def main():
    from multiprocessing import Pool
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    f = open(LOG, "w"); t0 = time.time()
    def log(*a):
        s = f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a); print(s, flush=True); f.write(s + "\n"); f.flush()
    log("vt350#312 bowden arms with a dancer: the roof exit clamps the bundle; the slack hangs behind the gantry "
        "(read-only; bowden_arms_dancer.py)")
    log(f"design {DESIGN['name']}: hinge {DESIGN['hinge']}, loop down {DESIGN['loop_down']}, up {DESIGN['loop_up']}")
    log(f"pulley R {RP} in the back wall's plane; highest centre Z {Z_TOP}; floor for its bottom Z {FLOOR}; "
        f"weights {WEIGHTS} N; bundle w {lrod.W_LIN} N/mm; the return span meets the arm at Y {Y_Q}")
    for s in range(1, 6):
        le, lr = legs(s)
        log(f"   T{s - 1}: exit X {lrod.EXIT_X[s]}; pulley centre X {PULLEY[s][0]}, plane Y {PULLEY[s][1]}; exit leg X "
            f"{le:.0f}, return leg X {lr:.0f}; arm + loop at X {arm_x(s):.1f}")
    zs = [float(z) for z in np.arange(Z_TOP, FLOOR + RP + 5 - 1e-6, -10.0)]
    workers = int(os.environ.get("ARMS_WORKERS", "10"))
    res = {}
    ch = design_channels()                                  # once, before the workers fork
    for s in sorted(ch):
        e, r = ch[s]
        log(f"T{s - 1} channels: exit " + (f"R {e[2]:.1f}, {e[1]:.0f} long" if e else "NONE (no shape keeps clear)")
            + "; return " + (f"R {r[2]:.1f}, {r[1]:.0f} long" if r else "NONE (no shape keeps clear)"))
    with Pool(workers) as pool:
        rear = dict(pool.imap_unordered(rear_spans, [(s, e, W, zs) for s in range(1, 6) for e in ba.EIS for W in WEIGHTS]))
        log(f"rear spans solved: {sum(1 for r in rear.values() for v in r['down'].values() if v is not None)} of "
            f"{len(rear) * len(zs)} heights (arm down)")
        # pass 1: every position at the pull with the pulley at mid-height; pass 2: at its own height's pull
        for p in (1, 2):
            jobs = []
            for s in range(1, 6):
                n = len(ba.path(s, STEP, dz=LOCK_DZ))
                for e in ba.EIS:
                    for W in WEIGHTS:
                        Ts = [W / 2 + lrod.W_LIN * (Z_ARM - (Z_TOP - 60))] * (n + 1)
                        if p == 2 and res[(s, e, W)]["T_next"] is not None: Ts = res[(s, e, W)]["T_next"]
                        jobs.append(((s, e, W), (s, e, Ts)))
            out = dict(zip([j[0] for j in jobs], pool.map(head_walk, [j[1] for j in jobs])))
            for key, (_, hw) in out.items():
                s, e, W = key
                rd, ru = rear[key]["down"], rear[key]["up"]
                Q_d, Q_u = q_point(s, DESIGN["loop_down"]), q_point(s, DESIGN["loop_up"])
                arm_d = float(np.linalg.norm(np.array([arm_x(s), *DESIGN["loop_down"]]) - Q_d))
                arm_u = float(np.linalg.norm(np.array([arm_x(s), *DESIGN["loop_up"]]) - Q_u))
                ok = [w for w in hw["walk"] if w["ok"]]
                if not ok or not hw["parked"]["ok"]:
                    res[key] = dict(hw=hw, failed=True, T_next=None); continue
                # the total: the most any position needs with the pulley at its highest
                need = [arm_d + w["L"] for w in ok] + [arm_u + hw["parked"]["L"]]
                Lmax_rear_top = rear_length(rd, Z_TOP)
                L_total = Lmax_rear_top + max(need[:-1]) if max(need[:-1]) >= need[-1] else rear_length(ru, Z_TOP) + need[-1]
                zc = [pulley_at(rd, L_total - (arm_d + w["L"])) if w["ok"] else None for w in hw["walk"]]
                zc_p = pulley_at(ru, L_total - (arm_u + hw["parked"]["L"]))
                Tn = [W / 2 + lrod.W_LIN * (Z_ARM - (z if z is not None else Z_TOP - 60)) for z in zc]
                Tn.append(W / 2 + lrod.W_LIN * (Z_ARM - zc_p))
                res[key] = dict(hw=hw, failed=False, zc=zc, zc_parked=zc_p, L_total=L_total, T_next=Tn,
                                arm_d=arm_d, arm_u=arm_u, T_used=None if p == 1 else res[key]["T_next"])
            log(f"pass {p}: {sum(1 for r in res.values() if not r['failed'])} of {len(res)} walks solved")

    # report
    rows = []
    for s in range(1, 6):
        for e in ba.EIS:
            for W in WEIGHTS:
                r = res[(s, e, W)]
                key = (s, e, W)
                if r["failed"]:
                    rows.append(dict(tool=s - 1, EI=e, W=W, solved=False)); log(f"   T{s - 1} EI {e:.0f} W {W}: UNSOLVED"); continue
                hw = r["hw"]; ok = [w for w in hw["walk"] if w["ok"]]
                zc = [z for z in r["zc"] if z is not None] + [r["zc_parked"]]
                rd = rear[key]["down"]
                zgrid = [z for z in sorted(rd) if rd[z] is not None and min(zc) - 10 <= z <= max(zc) + 10]
                exit_R = min(rd[z][2] for z in zgrid) if zgrid else float("nan")
                ret_R = min(rd[z][3] for z in zgrid) if zgrid else float("nan")
                ru = rear[key]["up"]
                ret_R = min([ret_R] + [ru[z][3] for z in sorted(ru) if ru[z] is not None and abs(z - r["zc_parked"]) <= 10])
                clear = min(rd[z][6] for z in zgrid) if zgrid else float("nan")
                T_used = r["T_used"] or []
                row = dict(tool=s - 1, EI=e, W=W, solved=len(ok) == len(hw["walk"]) and hw["parked"]["ok"],
                           unsolved=len(hw["walk"]) - len(ok), L_total=round(r["L_total"]),
                           pulley_top=round(max(zc), 1), pulley_low=round(min(zc), 1),
                           travel=round(max(zc) - min(zc), 1), pulley_bottom=round(min(zc) - RP - 5, 1),
                           T_loop=[round(min(T_used), 3), round(max(T_used), 3)] if T_used else None,
                           exit_R=round(exit_R, 1), return_R=round(ret_R, 1), rear_clear=round(clear, 1),
                           loop_turn=round(max(max(w["turn"] for w in ok), hw["parked"]["turn"])),
                           body_R=round(min(min(w["minR_body"] for w in ok), hw["parked"]["minR_body"]), 1),
                           lock_R=round(min(min(w["minR_lock"] for w in ok), hw["parked"]["minR_lock"]), 1),
                           lowest=round(min(w["lowest"] for w in ok) - (ba.HEAD_Z + LOCK_DZ), 1))
                row["fits_top"] = row["pulley_top"] <= Z_TOP + 0.5
                row["floor_ok"] = row["pulley_bottom"] >= FLOOR
                rows.append(row)
                log(f"   T{s - 1} EI {e:5.0f} W {W:.1f} N: pulley Z {row['pulley_low']:.0f}..{row['pulley_top']:.0f} "
                    f"(travel {row['travel']:.0f}, bottom {row['pulley_bottom']:.0f}); pull at the loop {row['T_loop']}; "
                    f"rear spans {clear:.0f} over the moving parts (lite-80, +10); bends: exit {exit_R:.0f}, return {ret_R:.0f}, head span {row['body_R']:.0f}, lock {row['lock_R']:.1f}; "
                    f"loop turn {row['loop_turn']} deg; lowest {row['lowest']:+.1f}; {row['unsolved']} unsolved")
    ok_rows = [r for r in rows if r.get("solved")]
    log("summary, by weight (all tools, all EI):")
    for W in WEIGHTS:
        rr = [r for r in ok_rows if r["W"] == W]
        if not rr: log(f"   W {W}: nothing solved"); continue
        log(f"   W {W:.1f} N ({W / 9.81 * 1000:.0f} g): pulley bottom down to Z {min(r['pulley_bottom'] for r in rr):.0f}, "
            f"travel up to {max(r['travel'] for r in rr):.0f}; tightest bends: exit {min(r['exit_R'] for r in rr):.0f}, "
            f"return {min(r['return_R'] for r in rr):.0f}, rear spans >= {min(r['rear_clear'] for r in rr):.0f} over the moving parts, head span {min(r['body_R'] for r in rr):.0f}; lock R "
            + " / ".join(f"{min(r['lock_R'] for r in rr if r['EI'] == e):.1f}" for e in ba.EIS)
            + f" at EI {' / '.join(f'{e:.0f}' for e in ba.EIS)}; loop turn up to {max(r['loop_turn'] for r in rr)} deg; "
            f"lowest {min(r['lowest'] for r in rr):+.1f}")
    json.dump(dict(design=DESIGN, RP=RP, pulley=PULLEY, legs={s: legs(s) for s in range(1, 6)}, y_q=Y_Q,
                   z_top=Z_TOP, floor=FLOOR, weights=WEIGHTS, rows=rows),
              open(OUT, "w"), indent=1)
    shapes = {}
    for (s, e, W), r in res.items():
        if r["failed"] or e != 2000.0: continue
        shapes[f"T{s - 1}|{W}"] = dict(zc=r["zc"], zc_parked=r["zc_parked"],
                                       walk=[w.get("X") for w in r["hw"]["walk"]], parked=r["hw"]["parked"].get("X"),
                                       heads=r["hw"]["heads"],
                                       rear={k: [v[4], v[5]] if v else None for k, v in rear[(s, e, W)]["down"].items()},
                                       rear_up={k: [v[4], v[5]] if v else None for k, v in rear[(s, e, W)]["up"].items()})
    json.dump(shapes, open(OUT.replace(".json", "_shapes.json"), "w"), separators=(",", ":"))
    log(f"wrote {OUT}")


if __name__ == "__main__":
    main()
