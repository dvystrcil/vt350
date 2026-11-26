"""vt350#312: arms raised by their parked heads, not a cam (owner's idea, 2026-11-25). Plain python3 + numpy; read-only,
opens no model (a few seconds):

    python3 cad/studies/dock_lever.py          # log cad/data/logs/dock_lever.log, route cad/data/dock_lever.json

The idea: while a head sits in its dock it holds its arm up; when the carriage takes it away, the arm drops by its own
weight; when the head is parked again, the arm goes back up. No cam, no stepper, no driver, no G-code.

The layout this study tries, per tool:
  - a PLUNGER in a printed block hung under the front 2020 dock bar (Y -92.5..-72.5, Z 469.3..489.3), along Y, its
    ball tip toward the docked head's Orbiter hub housing (front face Y -64.5). The head pushes it in as it docks
    (dropoff: forward to the keyslots' large opening, 6 mm past parked, then back 6 mm to parked) and lets it out as
    it leaves (pickup: forward 6, sideways 5, then back toward the bed);
  - a CABLE: a sheathed pull cable (housing, inner wire) from the plunger block up in front of the dock bar, under the
    front top 2040, rearward along the ceiling in its own lane beside the arm (LANE_DX from the bundle's X), to a
    housing stop above the arm near its hinge; the inner wire runs straight down to a tab on the arm TAB_D in front of
    the hinge. Pulling the wire lifts the arm;
  - the arm: as bowden_arms.py (hinge Y 490, Z 640; bar 8 x 12, ARM_SIDE -12 from the bundle; loop ring R 14). Down,
    it rests on a stop; up, on an up-stop; a COMPLIANCE SPRING in the plunger takes the head's travel beyond what lifts
    the arm.

What this computes (the FreeCAD half, dock_lever_clear.py, checks the route against the model):
  - travel: the tab's lift between the arm down and up, against the plunger's stroke (parked, and at the large opening);
  - forces: the arm's moment about the hinge (its weight + the bundle's pull at the loop, from the dancer study's pull),
    the wire's tension, the housing's friction (capstan, over the route's total bend angle), so the push the parked
    head carries and the force the carriage pushes against at the large opening;
  - room: each tool's cable lane and wire against every tool's bundle (bowden_arms_dancer.py's shapes: the channels,
    the free runs, the parked spans, the active head span at every lock position) and every arm (up and down);
  - failure cases: a wire that breaks or slips leaves an arm DOWN with its head parked: that tool's bundle then takes
    the walk's first shape (the lock in its dock, loop down), checked against every other tool's bundle; a plunger
    that sticks leaves an arm UP with its head out: the reference page's "cam stalled" case (every position solves).
"""
import json, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np

CAD = os.path.dirname(HERE)
LOG = os.path.join(CAD, "data", "logs", "dock_lever.log")
OUT = os.path.join(CAD, "data", "dock_lever.json")
SHAPES = os.path.join(CAD, "data", "bowden_arms_dancer_shapes.json")
ROWS = os.path.join(CAD, "data", "bowden_arms_dancer.json")
DESIGN = json.load(open(os.path.join(CAD, "data", "bowden_arms_design.json")))["design"]

EXIT_X = {1: -409.7, 2: -324.54, 3: -248.42, 4: -156.42, 5: -80.3}   # = the docked nozzles' X (lite-79)
HINGE = DESIGN["hinge"]                       # (Y, Z)
ARM_W, ARM_HALF, ARM_SIDE = 8.0, 6.0, -12.0   # bowden_arms.py
LOOP_R = 14.0
BUNDLE_R = 4.6

# --- the dock end (lite-79, from dock_lever_clear.py's probe: the bar, the hub housings' front faces) -----------------
BAR_BACK, BAR_FRONT, BAR_ZLO = -72.5, -92.5, 469.3
HEAD_FRONT = float(os.environ.get("LEVER_HEAD_FRONT", "-63.3"))   # the docked hub housing's front face, Y, where the
                                              # tip presses (a scan of all five: flat within 0.25 mm over X nozzle
                                              # -12..+4 and Z 459..463, so under the tip parked and detached either way)
SLIDE, DETACH = 6.0, 5.0                      # keyslot slide forward to the large opening; sideways detach
P_DX = float(os.environ.get("LEVER_P_DX", "-4"))    # plunger X from the nozzle's X (the hub housing's flat front;
                                              # at -12 the logo's recess left the face 15 mm uneven)
P_Z = float(os.environ.get("LEVER_P_Z", "463"))     # plunger height: under the bar's bottom (Z 469.3), its block's
                                              # floor 2.7 above the head's body (Z 455.8), which slides under it
P_FREE = 15.0                                 # the plunger tip's reach behind the bar's back face, head away
BLOCK = (16.0, 31.5, 10.8)                    # the plunger block under the bar: X; Y from the bar's back face to the
                                              # riser (Y -104..-72.5); Z down from the bar's bottom

# --- the cable ---------------------------------------------------------------------------------------------------
HOUSING_R = 2.5                               # 5 mm housing
WIRE_R = 0.6
LANE_DX = float(os.environ.get("LEVER_LANE_DX", "-24"))   # the lane's X from the bundle's X (the bar's far side)
Y_UP = -101.0                                 # the riser, in front of the dock bar and its brackets (Y -97.5)
BLOCK_TOP = BAR_ZLO                           # the riser starts at the block's top, which is the bar's bottom
PULLEY_R, PULLEY_DY = 6.0, 14.0               # the ceiling pulley (wire radius); the housing stop in front of it
Z_UNDER = 640.0                               # under the front top 2040 (Z 650 at Y -107..-87)
Z_LANE = 672.0                                # along the ceiling (felt at 679)
TAB_D = float(os.environ.get("LEVER_TAB_D", "44"))       # the tab's distance in front of the hinge, along Y
BEND_R = 25.0                                 # the housing's bends
MU = 0.15                                     # inner wire in a PTFE-lined housing (0.1..0.2)

# --- the arm's loads ----------------------------------------------------------------------------------------------
RHO = 1.27e-3 * 0.6                           # g/mm^3: PETG at ~60 % (walls + infill)
G = 9.81e-3                                   # N per g


def fillet(corners, R, step=1.0):
    """A polyline through `corners` with each inner corner rounded to radius R (or the most the legs allow)."""
    C = [np.asarray(c, float) for c in corners]
    out = [C[0]]
    for i in range(1, len(C) - 1):
        a, b, c = C[i - 1], C[i], C[i + 1]
        u, v = (a - b) / np.linalg.norm(a - b), (c - b) / np.linalg.norm(c - b)
        ang = math.acos(float(np.clip(u @ v, -1, 1)))                 # the inner angle
        if abs(ang - math.pi) < 1e-6: out.append(b); continue
        r = R; t = r / math.tan(ang / 2)
        t = min(t, 0.49 * np.linalg.norm(a - b), 0.49 * np.linalg.norm(c - b)); r = t * math.tan(ang / 2)
        p, q = b + u * t, b + v * t
        w = (u + v) / np.linalg.norm(u + v); o = b + w * (r / math.sin(ang / 2))
        n = max(4, int(math.ceil(r * (math.pi - ang) / step)))
        e1, e2 = p - o, q - o
        th = math.acos(float(np.clip(e1 @ e2 / (np.linalg.norm(e1) * np.linalg.norm(e2)), -1, 1)))
        k = np.cross(e1, e2); k = k / np.linalg.norm(k)
        for j in range(n + 1):                                        # Rodrigues: rotate e1 about k
            a_ = th * j / n
            out.append(o + e1 * math.cos(a_) + np.cross(k, e1) * math.sin(a_) + k * (k @ e1) * (1 - math.cos(a_)))
    out.append(C[-1])
    return dense(np.array(out), step)


def tab_point(slot, up):
    """Where the wire meets the arm's tab: TAB_D in front of the hinge, on the arm's line, at the lane's X; the tab's
    top (the bar's half depth above the line)."""
    hy, hz = HINGE; ly, lz = DESIGN["loop_up" if up else "loop_down"]
    y = hy - TAB_D; z = hz + (lz - hz) * (hy - y) / (hy - ly)
    return np.array([EXIT_X[slot] + LANE_DX, y, z + ARM_HALF])


def route(slot):
    """The housing's centreline and the wire beyond it, per tool:
      the plunger block's front (the wire turns up inside it on a small pulley) -> the riser, straight up in front of
      the dock bar (Y_UP) -> rearward under the front top 2040 (Z_UNDER) -> up to the ceiling lane (Z_LANE), moving
      over to the lane's X -> along the ceiling to the housing stop, PULLEY_DY in front of a small pulley on the
      ceiling above the tab -> the wire over that pulley and straight down to the tab.
    -> (housing polyline, wire with the arm up, wire with the arm down)."""
    x = EXIT_X[slot]; xp = x + P_DX; xl = x + LANE_DX
    t_up, t_dn = tab_point(slot, True), tab_point(slot, False)
    pul = np.array([xl, t_up[1], Z_LANE - PULLEY_R])               # the ceiling pulley's centre (axis along X)
    stop = np.array([xl, t_up[1] - PULLEY_DY, Z_LANE])
    corners = [[xp, Y_UP, BLOCK_TOP], [xp, Y_UP, Z_UNDER], [xp, -40.0, Z_UNDER], [xl, 20.0, Z_LANE], [xl, stop[1], Z_LANE]]
    H = fillet(corners, BEND_R)
    def wire(t):
        top = np.array([xl, t_up[1], Z_LANE]); side = np.array([xl, t_up[1] + PULLEY_R, Z_LANE - PULLEY_R])
        arc_ = [pul + PULLEY_R * np.array([0, math.sin(a), math.cos(a)]) for a in np.linspace(0, math.pi / 2, 12)]
        return dense(np.vstack([[stop], arc_, [side], [[xl, side[1], t[2]]]]), 1.0)
    return H, wire(t_up), wire(t_dn)


def bend_angle(P):
    D = np.diff(P, axis=0); D = D[np.linalg.norm(D, axis=1) > 1e-9]; t = D / np.linalg.norm(D, axis=1)[:, None]
    return float(np.sum(np.arccos(np.clip(np.sum(t[1:] * t[:-1], axis=1), -1, 1))))


def min_radius(P):
    D = np.diff(P, axis=0); ds = np.linalg.norm(D, axis=1); keep = ds > 1e-6; D, ds = D[keep], ds[keep]
    t = D / ds[:, None]; ang = np.arccos(np.clip(np.sum(t[1:] * t[:-1], axis=1), -1, 1))
    r = (ds[1:] + ds[:-1]) / 2 / np.maximum(ang, 1e-12)
    return float(np.min(r[ang > 1e-4])) if np.any(ang > 1e-4) else math.inf


def arm_parts(slot, up):
    """The arm as capsules: the bar's centreline (a box 8 x 12 taken as a tube of the half diagonal) and the ring."""
    hy, hz = HINGE; ly, lz = DESIGN["loop_up" if up else "loop_down"]; x = EXIT_X[slot]
    bar = np.array([[x + ARM_SIDE, hy, hz], [x + ARM_SIDE, ly, lz]])
    return [(dense(bar, 2.0), math.hypot(ARM_W / 2, ARM_HALF)), (np.array([[x, ly, lz]]), LOOP_R)]


def dense(P, step=2.0):
    P = np.asarray(P, float); out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        out += [a + (b - a) * (i / n) for i in range(1, n + 1)]
    return np.array(out)


def gap(A, ra, B, rb):
    """Smallest surface gap between two tubes (dense centrelines A, B; radii ra, rb)."""
    best = math.inf
    for i in range(0, len(A), 400):
        d = np.linalg.norm(A[i:i + 400, None] - B[None], axis=2)
        best = min(best, float(d.min()))
    return best - ra - rb


def mechanics(slot, rows):
    """The arm's moment about the hinge and what the plunger has to push."""
    hy, hz = HINGE; ly, lz = DESIGN["loop_up"]; L = math.hypot(hy - ly, lz - hz)
    m_bar = ARM_W * 2 * ARM_HALF * L * RHO
    m_ring = math.pi * (LOOP_R ** 2 - 10.0 ** 2) * 10.0 * RHO
    T = max(r["T_loop"][1] for r in rows if r["tool"] == slot - 1 and r["EI"] == 2000.0 and r["W"] == 0.2)
    # the bundle's pull on the raised loop: tension T along both legs (to the return channel's end C, and down the
    # parked span to the lock), its vertical part about the hinge
    C = np.array([340.0, 640.0]); P = np.array(DESIGN["loop_up"]); lock = np.array([-6.08, 550.11])
    u1 = (C - P) / np.linalg.norm(C - P); u2 = (lock - P) / np.linalg.norm(lock - P)
    F = T * (u1 + u2)                                       # (Fy, Fz) on the loop
    arm = P - np.array(HINGE)                               # loop relative to the hinge (Y, Z)
    M_bundle = arm[0] * F[1] - arm[1] * F[0]                # about +X; positive turns the loop down
    M_weight = (m_bar * G) * (hy - ly) / 2 + (m_ring * G) * (hy - ly)
    M = M_weight + M_bundle
    H, wu, wd = route(slot)
    theta = bend_angle(H)
    cap = math.exp(MU * theta) * 1.05 * 1.05               # the housing's bends; the two small pulleys (block, ceiling)
    T_tab = M / TAB_D                                      # wire tension at the tab to hold the arm up
    lift = float(tab_point(slot, True)[2] - tab_point(slot, False)[2])
    stroke_parked = P_FREE - (HEAD_FRONT - BAR_BACK)       # how far the parked head has pushed the plunger in
    stroke_open = stroke_parked + SLIDE
    k_c = 0.4                                              # N/mm, the compliance spring
    pre = T_tab * cap * 1.25                               # its preload: lifts the arm with 25 % to spare
    ret = 1.0                                              # N, the plunger's own return spring
    push_parked = pre + k_c * max(0.0, stroke_parked - lift) + ret
    push_open = pre + k_c * max(0.0, stroke_open - lift) + ret
    return dict(arm_g=round(m_bar + m_ring, 1), T_loop=T, M_weight=round(M_weight, 1), M_bundle=round(M_bundle, 1),
                M=round(M, 1), T_tab=round(T_tab, 2), bend_deg=round(math.degrees(theta)), capstan=round(cap, 2),
                pull_at_plunger=round(T_tab * cap, 2), lift=round(lift, 2), stroke_parked=round(stroke_parked, 1),
                stroke_open=round(stroke_open, 1), spare=round(stroke_parked - lift, 1), preload=round(pre, 2),
                push_parked=round(push_parked, 2), push_open=round(push_open, 2),
                drop_pull=round(T_tab / cap, 2), housing_minR=round(min_radius(H), 1),
                housing_len=round(float(np.sum(np.linalg.norm(np.diff(H, axis=0), axis=1)))))


def bundles(sh, d):
    """Every tool's bundle pieces from the dancer study: {slot: dict(fixed=[polylines], parked=polyline,
    walk=[polylines], dock_down=polyline)} (EI 2000, 20 g)."""
    out = {}
    for s in EXIT_X:
        c = sh[f"T{s - 1}|0.2"]
        k = next(k for k, v in c["rear"].items() if v is not None)
        fixed = [np.array(c["rear"][k][0][:-1]), np.array(c["rear"][k][1][1:]), np.array(c["rear_up"][k][1][1:])]
        walk = [np.array(X) for X in c["walk"] if X is not None]
        out[s] = dict(fixed=[dense(f) for f in fixed], parked=dense(c["parked"]), walk=[dense(w) for w in walk],
                      dock_down=dense(c["walk"][0]))
    return out


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    f = open(LOG, "w"); t0 = time.time()
    def log(*a):
        s = f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a); print(s, flush=True); f.write(s + "\n"); f.flush()
    log("vt350#312 dock lever: each parked head holds its arm up through a plunger and a pull cable; the arm drops "
        "when the head leaves (read-only; dock_lever.py)")
    log(f"plunger X nozzle {P_DX:+}, Z {P_Z}, free reach {P_FREE} behind the bar (Y {BAR_BACK}); head front Y "
        f"{HEAD_FRONT}; lane X bundle {LANE_DX:+}, Z {Z_LANE}; tab {TAB_D} in front of the hinge; housing bends R "
        f"{BEND_R}, mu {MU}")
    sh, d = json.load(open(SHAPES)), json.load(open(ROWS))
    B = bundles(sh, d)
    res, ok_all = {}, True
    for s in EXIT_X:
        m = mechanics(s, d["rows"])
        H, wu, wd = route(s)
        Hd, Wd = dense(H, 2.0), dense(np.vstack([wu, wd]), 1.0)
        # the cable against every bundle piece (both of its own: the parked span and the walk: its own head moves
        # under its own lane) and every arm, up and down
        g = []
        for o in EXIT_X:
            pieces = [("channels/free runs", p) for p in B[o]["fixed"]] + [("parked span", B[o]["parked"])]
            pieces += [("head span (walk)", w) for w in B[o]["walk"]]
            pieces += [("head span, parked, arm down", B[o]["dock_down"])]
            for what, P in pieces:
                g.append((round(min(gap(Hd, HOUSING_R, P, BUNDLE_R), gap(Wd, WIRE_R, P, BUNDLE_R)), 2), f"T{o - 1} {what}"))
            for up in (True, False):
                for P, r in arm_parts(o, up):
                    if o == s:     # its own arm: the wire meets its tab by design; check the housing only
                        g.append((round(gap(Hd, HOUSING_R, P, r), 2), f"T{o - 1} arm {'up' if up else 'down'} (own; housing)"))
                    else:
                        g.append((round(min(gap(Hd, HOUSING_R, P, r), gap(Wd, WIRE_R, P, r)), 2),
                                  f"T{o - 1} arm {'up' if up else 'down'}"))
        g.sort()
        ok = g[0][0] >= 1.0 and m["spare"] >= 1.0 and m["housing_minR"] >= BEND_R - 1.0
        ok_all &= ok
        res[s] = dict(mech=m, gaps=g[:6], ok=ok)
        log(f"T{s - 1}: {'ok' if ok else 'NOT ok'}  closest {g[0][0]:.1f} ({g[0][1]}), next {g[1][0]:.1f} ({g[1][1]})")
        log(f"    arm ~{m['arm_g']} g; moment {m['M']} N.mm (weight {m['M_weight']}, bundle {m['M_bundle']} at "
            f"{m['T_loop']} N); wire {m['T_tab']} N at the tab; housing {m['housing_len']} mm, bends {m['bend_deg']} deg "
            f"(R >= {m['housing_minR']}), friction x{m['capstan']} -> {m['pull_at_plunger']} N at the plunger")
        log(f"    tab lift {m['lift']} mm; plunger in {m['stroke_parked']} parked ({m['spare']} spare), {m['stroke_open']} "
            f"at the large opening; push on the parked head {m['push_parked']} N, at the large opening {m['push_open']} N "
            f"(compliance preload {m['preload']} N); dropping, the arm pulls {m['drop_pull']} N at the plunger end")
    # failure: a wire breaks, the arm stays down with its head parked: that bundle against the others, every position
    log("failure cases:")
    base = []
    for s in EXIT_X:
        for o in EXIT_X:
            if o != s:
                base.append((round(min(gap(B[s]["parked"], BUNDLE_R, w, BUNDLE_R) for w in B[o]["walk"]), 1),
                             f"T{s - 1} parked, arm up vs T{o - 1} active"))
    base.sort()
    log(f"   normal (arms of parked heads up): {base[0][1]}: {base[0][0]} mm (smallest of {len(base)} pairs; below 0 the "
        f"bundles brush, which the dancer study's walks already allow)")
    worst = []
    for s in EXIT_X:
        for o in EXIT_X:
            if o == s: continue
            gs = [gap(B[s]["dock_down"], BUNDLE_R, w, BUNDLE_R) for w in B[o]["walk"]]
            worst.append((round(min(gs), 1), f"T{s - 1} parked with its arm down vs T{o - 1} active",
                          sum(g < 0 for g in gs), len(gs)))
    worst.sort()
    for g_, what, n, tot in [w for w in worst if w[0] < 1.0]:
        log(f"   wire broken: {what}: {g_} mm; the bundles press together at {n} of {tot} positions")
    if worst[0][0] >= 1.0: log(f"   wire broken: {worst[0][1]}: {worst[0][0]} mm (smallest of {len(worst)} pairs): clear")
    log("   plunger stuck in: the arm stays up with its head out: the reference page's 'cam stalled' case "
        "(bowden_arms_reach.py: every position solves)")
    fail_ok = worst[0][0] >= min(base[0][0], 1.0) - 0.5     # no worse than today's arms-up case
    log(f"dock lever: {'ok' if ok_all else 'NOT ok'} (travel, forces, room against the bundles and the arms)")
    log(f"dock lever, a wire broken: {'no worse than today' if fail_ok else 'bundles press together'} "
        f"(a risk to weigh, not part of the verdict above)")
    json.dump(dict(params=dict(P_DX=P_DX, P_Z=P_Z, P_FREE=P_FREE, HEAD_FRONT=HEAD_FRONT, LANE_DX=LANE_DX, Z_LANE=Z_LANE,
                               TAB_D=TAB_D, HOUSING_R=HOUSING_R, WIRE_R=WIRE_R, BLOCK=BLOCK, BAR=[BAR_FRONT, BAR_BACK, BAR_ZLO]),
                   routes={s: dict(housing=np.round(route(s)[0], 2).tolist(), wire_up=np.round(route(s)[1], 2).tolist(),
                                   wire_down=np.round(route(s)[2], 2).tolist(),
                                   plunger=[EXIT_X[s] + P_DX, P_Z]) for s in EXIT_X},
                   result={s: dict(ok=r["ok"], mech=r["mech"], gaps=r["gaps"]) for s, r in res.items()},
                   failure=[w for w in worst if w[0] < 1.0] or worst[:1], baseline=base[:5]), open(OUT, "w"), indent=1)
    log(f"wrote {OUT}")


if __name__ == "__main__":
    main()
