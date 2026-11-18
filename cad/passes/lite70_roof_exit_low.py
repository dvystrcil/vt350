# GUI pass: vt350-lite-69 -> vt350-lite-70   (headless = dry run, never saves)   vt350#3, #4, #187
# The roof exit, rebuilt after lite-69 moved the roof insulation inside. Owner, 2026-11-18:
#  - "remove the exess height and have them flush against the roof": lite-36's clamps had a flange on the roof felt
#    (Z 704..708) stepping down to the panel; with the felt gone the flange stood 11 mm in the air.
#  - "lower the channel, it will give us back some cable lenght": lite-40's cable channel ran at Z 790..826 on posts.
#  - "the components you create need a champher ... 0.5mm for a bottom surface ... 1.0mm on the top surface"
#    (parts/printed/README.md): every part this pass makes is chamfered in its print orientation (printchamfer.py).
#
# Per head (5):
#  - CLAMP: lite-36's base + cap (same bores, split, screws, along the same measured 45 deg exit axis), moved 11 mm down
#    ALONG that axis (15.56 mm), so the bores stay on the tube's and the cable's lines; the base's flange is one plate
#    flat on the roof panel (Z 693..697, Y 444..498). The M5s into the rear bar and the front M3 through-bolts stay.
#    Prints: base flange down (up +Z); cap on its split face (up = the clamp's normal).
#  - CABLE: lite-40's cable is kept up to where the new clamp ends; from there a new lead-out (Bezier, the same
#    search as lite-40: run along X and both handles for the gentlest bend) into its lane of the lowered channel,
#    then the lane, the corner and the drop to the side pack as before.
# The CHANNEL (lite-40's U + cover, posts, arms; same section, lanes, corner and drop) comes down to the lowest lane
# height where every lead-out still bends at R >= MIN_R (51, 10 x OD) and the posts keep their 12 mm arm under it.
# Prints: body and cover flat (up +Y: the body on its front wall, open side up); posts on their side (up +X); arms flat.
# Checks (refuses to save on any):
#  - the printer model is lite-69 (a dry run can read lite-68, the roof insulation it moves left out of the checks);
#  - the 18 parts it replaces exist and nothing else links to them; the clamp axis measured from each tube (as lite-36);
#  - each new part one valid solid; the base's flange bottom on the roof's top; chamfers: every bed / top edge done,
#    narrow faces reduced (logged), none missed (printchamfer.unchamfered);
#  - each cable: one valid solid, volume = kept piece + pi r^2 L of the new tail (+-1 %), tail bends >= MIN_R,
#    starts on the kept piece's end along the clamp axis;
#  - no overlap: clamps, channel, cover, posts, arms vs the printer; cables vs everything; cable vs cable; against the
#    channel body each cable's centre line stays >= its radius off (a swept tube's boolean isn't trusted, LESSONS.md);
#    the side pack's envelope (a stand-in box the channel's drop and arms run into, as since lite-40): no more than before;
#  - the solid count unchanged (18 replaced, 5 cables rebuilt in place); every role as before.
import FreeCAD, Part, os, re, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "cad/scripts"), os.path.join(_REPO, "platform/render")]
import litelib, linkgeo, bezier, colours, printchamfer
from litelib import MODELS
import o2s_route as R
V = FreeCAD.Vector
LITE69, LITE68, DST = f"{MODELS}/vt350-lite-69.FCStd", f"{MODELS}/vt350-lite-68.FCStd", f"{MODELS}/vt350-lite-70.FCStd"
ROOF_INS = re.compile(r"^Roof felt ")
TOL = 1e-3

# lite-36 (the clamp)
R_T, R_C = 4.12 / 2, 5.1 / 2
SEP = R_T + R_C + 1.6
CLR, BORE, SPLIT = 1.0, 0.05, 0.15
PANEL_TOP, FELT_TOP_36 = 693.0, 704.0
FL_T, FL_HW, FL_Y0, FL_Y1 = 4.0, 18.0, 444.0, 498.0
BAR_SLOT_Y = 490.0
CL_HW, CL_T = 13.0, 7.0
DROP = FELT_TOP_36 - PANEL_TOP                          # 11 mm down ...
DS = DROP / math.sin(math.radians(45))                  # ... = 15.56 mm back along the 45 deg axis
CL_S0, CL_S1 = 12.0 - DS, 46.0 - DS
M3, M3_INS, M5, INS_DEPTH = 1.7, 2.0, 2.75, 5.5
HEADS = [(1, "Bowden Left", -1), (2, "Bowden slot 2", -1), (3, "Bowden slot 3", +1), (4, "Bowden slot 4", -1), (5, "Bowden Right", +1)]
CLAMP = "Roof exit clamp {part} slot {n} (vt350, GPL-3.0-or-later)"
CABLE = "O2S USB cable slot {n} "

# lite-40 (the channel)
RC = R.R_CABLE
LANE_Y, PITCH = 540.0, 6.5
X_A, R0, Z_END, X_START = 40.0, 60.0, 380.0, -470.0
WALL, CCLR, COV_T = 2.0, 0.4, 2.0
Y_IN0, Y_IN1 = LANE_Y - RC - 2.0, LANE_Y + RC + 3.95
DXS = [40.0, 70.0, 100.0, 140.0]
HANDLES = [5.0 * i for i in range(2, 41)]
POST_W, POST_Y0, POST_Y1, POST_ARM = 12.0, 506.0, 518.0, 12.0
ARM_Z = [460.0, 620.0]
CHAN = {"body": "Cable channel body, roof to side pack (printed, vt350, GPL-3.0-or-later)",
        "cover": "Cable channel cover, roof to side pack (printed, vt350, GPL-3.0-or-later)"}
POSTS = "Cable channel post {i} (printed, M5 to the rear 4040)"
ARMS = "Cable channel arm {i} (printed, M5 to the rear-right upright)"
LANE_Z0_MIN = PANEL_TOP + POST_ARM + RC + CCLR + WALL   # the channel's bottom leaves room for the post's arm under it
UP = {"base": V(0, 0, 1), "body": V(0, 1, 0), "cover": V(0, 1, 0), "post": V(1, 0, 0), "arm": V(0, 0, 1)}


def frame(Dv):
    X = V(1, 0, 0); N = X.cross(Dv); N.normalize(); return X, Dv, N


def lbox(o, X, Dv, N, u0, u1, s0, s1, n0, n1):
    b = Part.makeBox(u1 - u0, s1 - s0, n1 - n0)
    m = FreeCAD.Matrix(X.x, Dv.x, N.x, 0, X.y, Dv.y, N.y, 0, X.z, Dv.z, N.z, 0, 0, 0, 0, 1)
    b.Placement = FreeCAD.Placement(m).multiply(FreeCAD.Placement(V(u0, s0, n0), FreeCAD.Rotation()))
    b.translate(o); return b


def cyl(p, d, r, s0, s1): return Part.makeCylinder(r, s1 - s0, p + d * s0, d)
def above(z): return Part.makeBox(4000, 4000, 2000, V(-2000, -2000, z))
def bez(poles, u): return R.bez(poles, u)
def pts_of(poles, n): return [bez(poles, i / n) for i in range(n + 1)]


def min_r3(pts, step=4.0):
    rs, acc = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        acc += (b - a).Length
        if acc >= step: rs.append(b); acc = 0.0
    if (rs[-1] - pts[-1]).Length > 1e-6: rs.append(pts[-1])
    best = (1e9, None)
    for p0, p1, p2 in zip(rs, rs[1:], rs[2:]):
        a, b, c = (p1 - p0).Length, (p2 - p1).Length, (p2 - p0).Length
        cr = (p1 - p0).cross(p2 - p0).Length
        r = a * b * c / (2 * cr) if cr > 1e-9 else 1e9
        if r < best[0]: best = (r, p1)
    return best


def sweep(edge, r):
    w = Part.Wire(edge); t = edge.tangentAt(edge.FirstParameter)
    s = w.makePipeShell([Part.Wire(Part.makeCircle(r, edge.valueAt(edge.FirstParameter), t))], True, False)
    return s if s.ShapeType == "Solid" else Part.Solid(s)


def arc_pts(c, r, a0, a1, n, y):
    return [V(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), y, c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def lead_out(Ctop, Dv, zl):
    """lite-40's search: the gentlest Bezier from the clamp's end (along Dv) to (x + dx, LANE_Y, zl) along +X"""
    X, best = V(1, 0, 0), None
    for dx in DXS:
        P3 = V(Ctop.x + dx, LANE_Y, zl)
        for a in HANDLES:
            for b in HANDLES:
                pl = [tuple(Ctop), tuple(Ctop + Dv * a), tuple(P3 - X * b), tuple(P3)]
                r = bezier.min_radius(pl, 120)
                if best is None or r > best[0]: best = (r, dx, a, b, pl)
    return best


def gplace(o):
    par = o.getParentGeoFeatureGroup()
    return par.getGlobalPlacement() if par else FreeCAD.Placement()


def set_shape_keep_placement(o, g):
    """o (a Part::Feature) gets the global-frame shape g; its Placement stays P0 (LESSONS.md)"""
    P0 = FreeCAD.Placement(o.Placement)
    loc = g.copy(); loc.transformShape(gplace(o).multiply(P0).inverse().toMatrix(), True)
    loc.Placement = P0; o.Shape = loc


def main(p):
    final = os.path.exists(LITE69)
    pr = p.open(LITE69 if final else LITE68); doc = pr.doc
    if not final: p.log("lite-69 not saved yet: dry run against lite-68, its roof insulation (on top there) left out of the checks; will not save")
    p.check(final or p.dry, "the printer model is lite-69 (a GUI save needs it)")
    felt = {o.Name for o in pr.leaves if ROOF_INS.match(o.Label)} if not final else set()
    by = {o.Label: o for o in doc.Objects}
    cmap = colours.load(f"{_REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    # ---------------- the parts this pass replaces
    old = {}
    for n, _, _ in HEADS:
        for part in ("base", "cap"): old[("clamp", part, n)] = by.get(CLAMP.format(part=part, n=n))
    for k, lab in CHAN.items(): old[("chan", k, 0)] = by.get(lab)
    for i in range(1, 5): old[("post", "", i)] = by.get(POSTS.format(i=i))
    for i in range(1, 3): old[("arm", "", i)] = by.get(ARMS.format(i=i))
    p.check(all(old.values()), f"the 18 parts to replace: {sum(1 for v in old.values() if v)} found; missing {[k for k, v in old.items() if not v]}")
    if p.errs: return p.finish([])
    names = {o.Name for o in old.values()}
    users = sorted({u.Label for o in old.values() for u in o.InList if u.Name not in names and u.TypeId != "App::DocumentObjectGroup"
                    and not u.TypeId.startswith("App::Part")})
    p.check(not users, f"nothing else uses them (links, features): {users[:6]}")
    cables = {n: next((o for o in pr.leaves if o.Label.startswith(CABLE.format(n=n))), None) for n, _, _ in HEADS}
    p.check(all(c is not None and c.TypeId == "Part::Feature" for c in cables.values()), "the 5 O2S cables are plain Part::Features")
    if p.errs: return p.finish([])
    # remember where each old part lived and how it looked
    keep = {k: dict(parent=o.getParentGeoFeatureGroup() or next((g for g in o.InList if g.TypeId == "App::DocumentObjectGroup"), None),
                    group=next((g for g in o.InList if g.TypeId == "App::DocumentObjectGroup"), None),
                    label=o.Label, mat=getattr(o.LinkedObject if o.TypeId == "App::Link" else o, "ShapeMaterial", None),
                    app=(o.LinkedObject if o.TypeId == "App::Link" else o).ViewObject.ShapeAppearance if FreeCAD.GuiUp else None)
            for k, o in old.items()}
    envs = [o for o in pr.leaves if o.Label.startswith("Ebox envelope")]
    p.check(len(envs) == 1, f"the side pack's envelope ({len(envs)})")
    if p.errs: return p.finish([])
    env = envs[0]
    def env_vol(sh): return sh.common(pr.shapes[env.Name]).Volume if sh.BoundBox.intersect(pr.boxes[env.Name]) else 0.0
    env_before = {o.Label: env_vol(pr.shapes[o.Name]) for o in list(old.values()) + list(cables.values())}
    def gpath(o):
        r_, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r_.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r_))
    role_before = {o.Label: colours.role_of(cmap, o.Label, gpath(o), "Default") for o in old.values()}
    # ---------------- per head: the axis (lite-36's measurement), the new clamp
    data, axes, clamp_new = {}, {}, {}
    for n, tlab, sgn in HEADS:
        t = by[tlab]
        def centre(z):
            sec = pr.shapes[t.Name].slice(V(0, 0, 1), z)
            p.check(len(sec) == 1, f"slot {n}: {tlab} cut by Z {z} in one loop ({len(sec)})"); return Part.Face(sec[0]).CenterOfMass
        E, E2 = centre(690.0), centre(700.0); Dv = E2 - E
        p.check(abs(Dv.x) / Dv.Length < 1e-3, f"slot {n}: exit axis in a plane X = const (dX/len {Dv.x / Dv.Length:.1e})")
        Dv = V(0, Dv.y, Dv.z); Dv.normalize(); X, Dv, N = frame(Dv)
        Ec = E + X * (sgn * SEP); mid = E + X * (sgn * SEP / 2)
        axes[n] = (E, Ec, Dv, X, N, sgn)
        fl = Part.makeBox(2 * FL_HW, FL_Y1 - FL_Y0, FL_T, V(mid.x - FL_HW, FL_Y0, PANEL_TOP))
        lower = lbox(mid, X, Dv, N, -CL_HW, CL_HW, CL_S0, CL_S1, -CL_T, -SPLIT).common(above(PANEL_TOP))
        base = fl.fuse(lower)
        cap = lbox(mid, X, Dv, N, -CL_HW, CL_HW, CL_S0, CL_S1, SPLIT, CL_T).common(above(PANEL_TOP + FL_T + 0.5))
        s_fl = (PANEL_TOP + FL_T - E.z) / Dv.z + 0.5            # clearance (not grip) through the flange
        base = base.cut(cyl(E, Dv, R_T + CLR, -15, s_fl)).cut(cyl(Ec, Dv, R_C + CLR, -15, s_fl))
        bores = cyl(E, Dv, R_T + BORE, -15, CL_S1 + 15).fuse(cyl(Ec, Dv, R_C + BORE, -15, CL_S1 + 15))
        base, cap = base.cut(bores), cap.cut(bores)
        m5 = [V(mid.x + sx * 11.0, BAR_SLOT_Y, PANEL_TOP - 3) for sx in (-1, 1)]
        m3f = [V(mid.x + sx * 13.0, 451.0, PANEL_TOP - 10) for sx in (-1, 1)]
        capc = [mid + X * (sx * 9.5) + Dv * ((CL_S0 + CL_S1) / 2 + 4) for sx in (-1, 1)]
        for q in m5: base = base.cut(Part.makeCylinder(M5, 40, q))
        for q in m3f: base = base.cut(Part.makeCylinder(M3, 40, q))
        for q in capc:
            cap = cap.cut(Part.makeCylinder(M3, 20, q - N * 1, N))
            base = base.cut(Part.makeCylinder(M3_INS, INS_DEPTH + SPLIT, q - N * (SPLIT + INS_DEPTH), N))
        base, cap = base.removeSplitter(), cap.removeSplitter()
        p.check(base.isValid() and len(base.Solids) == 1 and cap.isValid() and len(cap.Solids) == 1,
                f"slot {n}: base {base.Volume:.0f}, cap {cap.Volume:.0f} mm3, one valid solid each; base Z {base.BoundBox.ZMin:.2f}..{base.BoundBox.ZMax:.2f}, "
                f"cap Z {cap.BoundBox.ZMin:.2f}..{cap.BoundBox.ZMax:.2f} (lite-36: 693.00..724.36, 706.77..727.47)")
        p.on_face(base, PANEL_TOP, f"slot {n}: the base's flange lies flat on the roof's top (Z {PANEL_TOP})")
        clamp_new[n] = {"base": base, "cap": cap}
        data[n] = dict(axis_x=round(E.x, 2), cable_x=round(Ec.x, 2))
    # ---------------- the channel: the lowest lanes every lead-out reaches at R >= MIN_R
    zc_of = lambda z0: {n: z0 + (5 - n) * PITCH for n, _, _ in HEADS}
    lane_z0, outs = None, None
    z0 = LANE_Z0_MIN
    while z0 <= 800.0:
        zc = zc_of(z0); trial = {}
        for n, _, _ in HEADS:
            E, Ec, Dv, X, N, sgn = axes[n]
            trial[n] = lead_out(Ec + Dv * CL_S1, Dv, zc[n])
            if trial[n][0] < R.MIN_R: break
        else:
            lane_z0, outs = z0, trial; break
        z0 += 2.5
    p.check(lane_z0 is not None, f"lanes: the lowest bottom lane where every lead-out bends >= R {R.MIN_R:.0f}: Z {lane_z0} "
            f"(lite-40: 795; tried from {LANE_Z0_MIN:.2f})")
    if p.errs: return p.finish([])
    zc = zc_of(lane_z0); zc_c = lane_z0 + 2 * PITCH
    hz = 2 * PITCH + RC + CCLR; cz = lane_z0 - R0
    def section(y0, y1, n0, n1):
        z0_, z1_ = zc_c + n0, zc_c + n1
        f = Part.Face(Part.makePolygon([V(X_A, y0, z0_), V(X_A, y1, z0_), V(X_A, y1, z1_), V(X_A, y0, z1_), V(X_A, y0, z0_)]))
        hor = f.extrude(V(X_START - X_A, 0, 0)); cor = f.revolve(V(X_A, 0, cz), V(0, 1, 0), 90)
        ver = Part.makeBox(z1_ - z0_, y1 - y0, cz - Z_END, V(X_A + (z0_ - cz), y0, Z_END))
        return hor.fuse([cor, ver]).removeSplitter()
    outer = section(Y_IN0 - WALL, Y_IN1, -hz - WALL, hz + WALL)
    body = outer.cut(section(Y_IN0, Y_IN1 + 1, -hz, hz))
    body = body.fuse(Part.makeBox(WALL, Y_IN1 - Y_IN0 + WALL, 2 * hz + 2 * WALL, V(X_START - WALL, Y_IN0 - WALL, zc_c - hz - WALL)))
    cover = section(Y_IN1, Y_IN1 + COV_T, -hz - WALL, hz + WALL)
    # ---------------- the cables: kept to the clamp's new end, then the new tail
    new_cab, tails = {}, {}
    for n, _, _ in HEADS:
        E, Ec, Dv, X, N, sgn = axes[n]
        Ctop = Ec + Dv * CL_S1
        r_out, dx, a, b, pl = outs[n]
        run0, run1 = bez(pl, 1.0), V(X_A, LANE_Y, zc[n])
        rl = R0 + (zc[n] - lane_z0)
        corner = arc_pts((X_A, cz), rl, math.pi / 2, 0.0, 40, LANE_Y)
        down0, down1 = V(X_A + rl, LANE_Y, cz), V(X_A + rl, LANE_Y, Z_END)
        path = pts_of(pl, 80) + [run1] + corner[1:] + [down1]
        rmin, where = min_r3(pts_of(pl, 200) + corner[1:])
        p.check(rmin >= R.MIN_R - 0.5 and X_A - run0.x > 5.0, f"slot {n}: tail bends >= R {rmin:.1f} (lead-out {r_out:.1f}: run {dx:.0f} along X, "
                f"handles {a:.0f}/{b:.0f}; lane Z {zc[n]}, corner R {rl:.1f}); its lane runs X {run0.x:.1f} -> {X_A:.0f}")
        old_s = pr.shapes[cables[n].Name]
        hs = Part.makeCylinder(3000, 6000, Ctop - Dv * 6000, Dv)          # the side of the clamp end the chamber is on
        pieces = old_s.common(hs).Solids
        inside = Ec + Dv * (CL_S1 - 5.0)
        kept = [s for s in pieces if s.isInside(inside, 1e-6, True)]
        p.check(len(kept) == 1, f"slot {n}: the old cable cut at the clamp's new end: {len(pieces)} piece(s), the chamber's found ({len(kept)})")
        if not kept: continue
        kept = kept[0]
        ends = [f for f in kept.Faces if isinstance(f.Surface, Part.Plane) and abs(abs(f.normalAt(0, 0).dot(Dv)) - 1) < 1e-6
                and abs((f.CenterOfMass - Ctop).dot(Dv)) < 1e-6]
        p.check(len(ends) == 1 and (ends[0].CenterOfMass - Ctop).Length < 0.05,
                f"slot {n}: the kept cable ends on the clamp axis at the clamp's end (off by {min([(f.CenterOfMass - Ctop).Length for f in ends] or [9e9]):.3f} mm)")
        c = Part.BezierCurve(); c.setPoles([V(*q) for q in pl]); e_out = c.toShape()
        segs = [sweep(e_out, RC), Part.makeCylinder(RC, (run1 - run0).Length, run0, run1 - run0),
                Part.Face(Part.Wire(Part.makeCircle(RC, run1, V(1, 0, 0)))).revolve(V(X_A, 0, cz), V(0, 1, 0), 90),
                Part.makeCylinder(RC, (down1 - down0).Length, down0, down1 - down0)]
        L = e_out.Length + (run1 - run0).Length + math.pi / 2 * rl + (down1 - down0).Length
        s = kept.multiFuse(segs).removeSplitter()
        want = kept.Volume + math.pi * RC * RC * L
        p.check(s.isValid() and len(s.Solids) == 1 and abs(s.Volume - want) < 0.01 * want,
                f"slot {n}: cable one valid solid ({len(s.Solids)}), {s.Volume:.0f} mm3 (kept {kept.Volume:.0f} + pi r^2 x {L:.0f} = {want:.0f})")
        saved = (old_s.Volume - s.Volume) / (math.pi * RC * RC)
        data[n].update(lane_z=zc[n], r_tail=round(rmin, 1), tail_mm=round(L), shorter_mm=round(saved))
        new_cab[n] = s; tails[n] = path
    if p.errs: return p.finish([])
    # entry windows: where each lead-out passes the body, a box from there to the open back (lite-40's rule)
    slots = 0
    for n, _, _ in HEADS:
        near = FreeCAD.BoundBox(outer.BoundBox); near.enlarge(RC + 1.0)     # the cable's surface reaches the wall
        inside = [q for q in pts_of(outs[n][4], 400) if near.isInside(q)]      # before its centre line does
        if not inside: continue
        xs, ys, zs = [q.x for q in inside], [q.y for q in inside], [q.z for q in inside]
        e = RC + 1.0
        body = body.cut(Part.makeBox(max(xs) - min(xs) + 2 * e, Y_IN1 + 1 - (min(ys) - e), max(zs) - min(zs) + 2 * e,
                                     V(min(xs) - e, min(ys) - e, min(zs) - e))); slots += 1
    body = body.removeSplitter()
    p.check(body.isValid() and len(body.Solids) == 1, f"channel body with {slots} entry windows: one valid solid; Z {body.BoundBox.ZMin:.2f}..{body.BoundBox.ZMax:.2f} (lite-40: 790..826)")
    # posts: lite-40's, from the roof to under the lowered channel; X clear of the new cables and clamps
    zb = zc_c - hz - WALL
    def post_at(x):
        col = Part.makeBox(POST_W, POST_Y1 - POST_Y0, zb - PANEL_TOP, V(x - POST_W / 2, POST_Y0, PANEL_TOP))
        arm = Part.makeBox(POST_W, Y_IN0 - WALL - POST_Y0, POST_ARM, V(x - POST_W / 2, POST_Y0, zb - POST_ARM))
        return col.fuse(arm).removeSplitter()
    blockers = list(new_cab.values()) + [c for d in clamp_new.values() for c in d.values()]
    free = []
    for x in range(int(X_START) + 10, int(X_A) - 10, 5):
        ps = post_at(float(x)); bb = ps.BoundBox; bb.enlarge(1.0)
        if any(c.BoundBox.intersect(bb) and c.distToShape(ps)[0] < 1.0 for c in blockers): continue
        free.append(float(x))
    chosen = sorted({min(free, key=lambda x: abs(x - tg)) for tg in [X_START + 15 + (X_A - 40 - X_START - 15) * k / 3 for k in range(4)]} if free else set())
    gaps = [b - a for a, b in zip([X_START] + chosen, chosen + [X_A])]
    p.check(len(chosen) == 4 and max(gaps) <= 200, f"posts at X {chosen} ({zb - PANEL_TOP:.1f} tall; lite-40: 97) clear of cables and clamps by >= 1 mm; spans {[round(g) for g in gaps]}")
    xv0 = X_A + R0 - RC - CCLR - WALL
    arms = [Part.makeBox(xv0 + 20 - 10, Y_IN0 - WALL - 520.0, 12.0, V(10.0, 520.0, z - 6)).cut(outer) for z in ARM_Z]
    # ---------------- chamfers, in print orientation
    made = {}
    def chamf(key, shape, up, what):
        s, info = printchamfer.chamfer(shape, up)
        left = printchamfer.unchamfered(shape, s, up, skip={w for k, w, c in info["skipped"]} | {w for k, w in info["failed"]})
        p.check(s.isValid() and len(s.Solids) == 1 and not left,
                f"{what}: chamfered (up {tuple(round(c, 3) for c in up)}): {info['bottom']} first-layer edges 0.6, {info['top']} top edges 1.0, "
                f"{len(info['reduced'])} reduced on narrow faces (smallest {min([c for k, w, c in info['reduced']] or [1.0]):.2f}), "
                f"{len(info['skipped'])} skipped, {len(info['failed'])} OCC couldn't build {info['failed'][:3]}; -{info['removed_mm3']:.0f} mm3; missed: {left[:4]}")
        if left and os.environ.get("VT350_DEBUG_BREP"):               # the unchamfered part, to look at by hand
            shape.exportBrep(os.path.join(os.environ["VT350_DEBUG_BREP"], re.sub(r"\W+", "_", what)[:40] + ".brep"))
        made[key] = s; return s
    for n, _, _ in HEADS:
        E, Ec, Dv, X, N, sgn = axes[n]
        chamf(("clamp", "base", n), clamp_new[n]["base"], UP["base"], f"slot {n} base")
        chamf(("clamp", "cap", n), clamp_new[n]["cap"], N, f"slot {n} cap (printed on its split face)")
    chamf(("chan", "body", 0), body, UP["body"], "channel body (on its front wall)")
    chamf(("chan", "cover", 0), cover, UP["cover"], "channel cover")
    for i, x in enumerate(chosen, 1): chamf(("post", "", i), post_at(x), UP["post"], f"post {i} (on its side)")
    for i, a in enumerate(arms, 1): chamf(("arm", "", i), a, UP["arm"], f"arm {i}")
    if p.errs: return p.finish([])
    # ---------------- into the document: delete the 18, add the new ones in their places; cables rebuilt in place
    for o in sorted(old.values(), key=lambda o: o.TypeId != "App::Link"): doc.removeObject(o.Name)
    for k, s in made.items():
        kp = keep[k]
        o = doc.addObject("Part::Feature", re.sub(r"\W", "_", kp["label"].split(" (")[0])[:40])
        par = kp["group"] or kp["parent"]
        if par is not None: par.addObject(o)
        loc = s.copy(); loc.Placement = gplace(o).inverse().multiply(loc.Placement); o.Shape = loc
        o.Label = kp["label"]
        if kp["mat"] is not None and hasattr(o, "ShapeMaterial"): o.ShapeMaterial = kp["mat"]
        if kp["app"] is not None: o.ViewObject.ShapeAppearance = kp["app"]
    for n, s in new_cab.items(): set_shape_keep_placement(cables[n], s)
    doc.recompute(); pr.refresh()
    newo = [o for o in pr.leaves if o.Label in {kp["label"] for kp in keep.values()}]
    p.check(len(newo) == 18, f"the 18 replacements are in the model ({len(newo)})")
    for n, s in new_cab.items():
        g = pr.shapes[cables[n].Name]
        p.check(abs(g.Volume - s.Volume) < 1e-3 and g.BoundBox.isInside(s.BoundBox.Center) and
                all(abs(a - b) < 1e-4 for a, b in zip((g.BoundBox.XMin, g.BoundBox.ZMax), (s.BoundBox.XMin, s.BoundBox.ZMax))),
                f"slot {n}: the cable's object now holds the new shape in place (Placement kept)")
    # ---------------- overlaps
    cab_names = {cables[n].Name for n in new_cab}
    if os.environ.get("VT350_DEBUG_BREP"):                      # the finished parts + the ebox envelope, to look at by hand
        for o in newo + [cables[n] for n in new_cab] + [o for o in pr.leaves if o.Label.startswith("Ebox envelope")]:
            pr.shapes[o.Name].exportBrep(os.path.join(os.environ["VT350_DEBUG_BREP"], "fin_" + re.sub(r"\W+", "_", o.Label)[:40] + ".brep"))
        p.check(False, "VT350_DEBUG_BREP: stopped after exporting the finished parts"); return p.finish([])
    mine = {o.Name for o in newo}
    body_o = next(o for o in newo if o.Label == CHAN["body"])
    rigid = [(o.Label, pr.shapes[o.Name]) for o in newo]
    p.no_overlap(rigid, pr, lambda r: f"clamps, channel, cover, posts, arms vs the printer: {r.hits[:6]}", exclude=mine | felt | cab_names | {env.Name})
    p.no_overlap([x for x in rigid if x[0] != CHAN["body"]], pr, lambda r: f"clamps, cover, posts, arms vs the 5 cables (bores have clearance): {r.hits[:6]}",
                 exclude=(mine | felt | {o.Name for o in pr.leaves}) - cab_names)
    p.no_overlap([(cables[n].Label, pr.shapes[cables[n].Name]) for n in new_cab], pr,
                 lambda r: f"the cables vs everything (the channel body and the envelope below): {r.hits[:6]}", exclude=cab_names | felt | {env.Name, body_o.Name})
    # booleans of a swept cable against the body give slivers outside both (LESSONS.md): its centre line instead
    bsh = pr.shapes[body_o.Name]
    for n in new_cab:
        pts, q = [], tails[n]
        for a, b in zip(q, q[1:]):
            k = max(1, int((b - a).Length / 1.0))
            pts += [a + (b - a) * (j / k) for j in range(k)]
        d, pairs, _ = bsh.distToShape(Part.Compound([Part.Vertex(x) for x in pts + [q[-1]]]))
        at = pairs[0][1] if pairs else V()
        p.check(d >= RC - 0.01, f"slot {n}: the cable's centre line in and through the channel stays {d:.2f} mm off the body "
                f"(radius {RC:.2f}; closest at {tuple(round(c, 1) for c in at)})")
    # the side pack's envelope: the drop (X 95..131, Z 380..636) and arms run into it as in lite-40; no more than before
    for o in newo + [cables[n] for n in new_cab]:
        a, b = env_vol(pr.shapes[o.Name]), env_before.get(o.Label, 0.0)
        if a > TOL or b > TOL:
            p.check(a <= b + 1.0, f"{o.Label[:40]} in the side pack's envelope: {a:.0f} mm3 (lite-69: {b:.0f})")
    ns = sorted(new_cab)
    for i, a in enumerate(ns):
        for b in ns[i + 1:]:
            sa, sb = pr.shapes[cables[a].Name], pr.shapes[cables[b].Name]
            v = sa.common(sb).Volume if sa.BoundBox.intersect(sb.BoundBox) else 0.0
            p.check(v < TOL, f"cable {a} vs cable {b}: {v:.3f} mm3")
    # ---------------- roles and count
    for o in newo:
        r_ = colours.role_of(cmap, o.Label, gpath(o), "Default")
        p.check(r_ == role_before[o.Label], f"{o.Label[:50]}: role {r_} (lite-69: {role_before[o.Label]})")
    p.check(len(pr.leaves) == n_before, f"solids: {n_before} -> {len(pr.leaves)} (18 replaced, 5 cables rebuilt in place)")
    p.dump({"lane_z0": lane_z0, "lanes_z": zc, "channel_z": [round(body.BoundBox.ZMin, 2), round(body.BoundBox.ZMax, 2)],
            "posts_x": chosen, "post_height": round(zb - PANEL_TOP, 2), "clamp_drop_mm": DROP, "heads": data})
    p.finish([(doc, DST)])


litelib.Pass("lite70_roof_exit_low").run(main)
