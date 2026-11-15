# GUI pass: vt350-lite-39 -> vt350-lite-40   (headless = dry run, never saves)
# vt350#3 AC2 (+ AC5) and #19. The user (2026-11-14): "when will the electrical cables be fully added and zip tied to
# the bowdens (black zip ties)"; the cables are ~3 m ("I will not worry about length"); "find a way to route them
# nicely to the sidepack"; for the wiring, "elegant but accessible. Some people use printed channels with covers (like
# flat conduit)".
#
# Per head (5), one cable (Ø5.1, measured) from its O2S wire restraint's lock to the side pack:
#  1. IN THE CHAMBER: cad/scripts/o2s_route.py's route (the study's, unchanged): straight up out of the lock, a lead-in
#     to the LOWEST point on the tube it can join with bend R >= 51 (10 x OD, assumed), then beside the tube to the
#     roof. Along the bundle the cable turns round the tube from where the lead-in puts it to where lite-36's clamp
#     holds it (beside the tube in X, on the restraint's side, 6.21 mm centre to centre): side and spacing are
#     interpolated along the bundle. 4 BLACK ZIP TIES per head round tube + cable, ~100 mm apart.
#  2. THROUGH THE ROOF: in the clamp's cable bore, along the exit axis (45 deg up and back), to the clamp's top end.
#  3. ABOVE THE ROOF: a lead-in (Bezier, bend R >= 51, handles searched) from the clamp's top end into its LANE of a
#     printed CABLE CHANNEL behind the roof's rear edge. Lanes are stacked in Z, one per head, slot 1 on top: each
#     cable rises into the channel from below, so it only crosses lanes that are still empty there (the heads to its
#     right enter further right). The channel sits above the tubes' own line (each tube carries on up and back along
#     the exit axis, past the end of its modelled stub), checked against that line extended.
#  4. The channel runs +X, turns DOWN at the right (R 60 on the inner lane), and drops behind the side pack to Z 380,
#     where the cables leave it towards the pack (its enclosure and wiring are #5: not designed yet).
# The channel: a printed U (white), open to the BACK, with a printed COVER (accent orange) over the opening, so the
# cables lie in from behind and the cover clips over them: the user's "flat conduit". Entry slots in its floor, open
# to the back, for each cable. Printed POSTS from the rear top 4040 (M5 into its rear slot, through the roof panel)
# carry the horizontal run; printed ARMS from the rear-right upright's back face carry the vertical run. Fasteners
# and clips aren't modelled; the channel is one solid here and prints in segments (BOM).
# Feasibility (scratchpad probe, 2026-11-14): a channel on the rear 4040's back face gives bend R ~27 (fails); a rack
# above the roof with the lanes at Y 540, bottom lane Z 795 gives >= 77 for every head.
# Checks (refuses to save on any): the route's own checks (o2s_route.py); every cable's whole centreline bends no
# tighter than MIN_R (discrete, 3-point radius every ~4 mm); each cable is one valid solid, volume = pi r^2 L (+-1 %);
# the cables hit nothing (tubes, clamps, roof, channel, posts, each other); the channel, cover, posts, arms and ties hit
# nothing but what they're meant to touch; the tubes' extended lines clear the channel and posts by >= 2 mm; roles;
# solids + 5 cables + 20 ties + channel + cover + posts + arms.
import FreeCAD, Part, os, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "cad/scripts"), os.path.join(_REPO, "platform/render")]
import litelib, bezier, colours
from litelib import is_leaf, MODELS
import o2s_route as R
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-39.FCStd", f"{MODELS}/vt350-lite-40.FCStd"
EXTRAS = "Enclosure extras (lite-16)"
GROUP = "O2S cables + channel (lite-40)"
SG = {"Left Toolhead": -1, "Toolhead slot 2 (L)": -1, "Toolhead slot 3 (R)": +1, "Toolhead slot 4 (L)": -1, "Right Toolhead": +1}
SLOT = {"Left Toolhead": 1, "Toolhead slot 2 (L)": 2, "Toolhead slot 3 (R)": 3, "Toolhead slot 4 (L)": 4, "Right Toolhead": 5}
CLAMP = "Roof exit clamp {part} slot {n} (vt350, GPL-3.0-or-later)"
SEP, CL_S1 = 4.12 / 2 + 5.1 / 2 + 1.6, 46.0            # lite-36: cable beside the tube in the clamp; clamp's top end
RC = R.R_CABLE
# the channel
LANE_Y, LANE_Z0, PITCH = 540.0, 795.0, 6.5               # cable plane; bottom lane (slot 5); lane pitch
X_A, R0, Z_END = 40.0, 60.0, 380.0                       # the horizontal run ends at X_A (past every lead-in's end: slot
                                                         # 5's reaches X +26); inner lane radius; bottom end
X_START = -470.0                                         # the horizontal run's left (closed) end
WALL, CLR = 2.0, 0.4                                     # wall; cable to wall
Y_IN0, Y_IN1 = LANE_Y - RC - 2.0, LANE_Y + RC + 3.95    # inner Y: front wall face, back opening (11 deep)
COV_T = 2.0
DXS = [40.0, 70.0, 100.0, 140.0]                         # lead-in: run along X before the lane starts
HANDLES = [5.0 * i for i in range(2, 41)]
TIE_W, TIE_T, TIE_CLR = 2.5, 1.2, 0.3                    # zip tie band width, thickness, clearance (0.15 overlapped
                                                         # the tube solid by ~1 mm3: it sits up to 0.1 off the rebuilt curve)
TIE_AT = [20.0, 120.0, 220.0, 320.0]                     # mm along the bundle from the join
POST_W, POST_Y0, POST_Y1, PANEL_TOP = 12.0, 506.0, 518.0, 693.0
ARM_Z = [460.0, 620.0]
TOL = 1e-3


def bez(poles, u): return R.bez(poles, u)


def pts_of(poles, n):
    return [bez(poles, i / n) for i in range(n + 1)]


def min_r3(pts, step=4.0):
    """smallest 3-point circumradius along a polyline resampled every ~step mm"""
    rs = [pts[0]]
    acc = 0.0
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


def resample(pts, step):
    out, acc = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        acc += (b - a).Length
        if acc >= step: out.append(b); acc = 0.0
    if (out[-1] - pts[-1]).Length > 0.5: out.append(pts[-1])
    else: out[-1] = pts[-1]
    return out


def sweep(edge, r):
    """a circle of radius r swept along one smooth edge (corrected Frenet)"""
    w = Part.Wire(edge)
    t = edge.tangentAt(edge.FirstParameter)
    prof = Part.Wire(Part.makeCircle(r, edge.valueAt(edge.FirstParameter), t))
    s = w.makePipeShell([prof], True, False)
    return s if s.ShapeType == "Solid" else Part.Solid(s)


def cable_solid(pc, r):
    """the cable from its route's pieces: lead-in Bezier, bundle (BSpline), straight through the clamp, lead-out
    Bezier, straight run, the corner (a quarter torus), straight down. Returns (solid, centreline length, how)."""
    segs, L = [], 0.0
    def bez_edge(poles):
        c = Part.BezierCurve(); c.setPoles([V(*q) for q in poles]); return c.toShape()
    e = bez_edge(pc["lead"]); segs.append(sweep(e, r)); L += e.Length
    bs = Part.BSplineCurve(); bs.interpolate(resample(pc["bun"], 3.0)); e = bs.toShape(); segs.append(sweep(e, r)); L += e.Length
    for a, b in ((pc["Ec"], pc["Ctop"]), pc["run"], pc["down"]):
        segs.append(Part.makeCylinder(r, (b - a).Length, a, b - a)); L += (b - a).Length
    e = bez_edge(pc["out"]); segs.append(sweep(e, r)); L += e.Length
    top, ax = pc["corner"]
    disc = Part.Face(Part.Wire(Part.makeCircle(r, top, V(1, 0, 0))))
    segs.append(disc.revolve(ax, V(0, 1, 0), 90)); L += math.pi / 2 * (top.z - ax.z)
    s = segs[0].multiFuse(segs[1:]).removeSplitter()
    return s, L, f"{len(segs)} pieces fused"


def arc_pts(c, r, a0, a1, n, y):
    """points on a circle in the XZ plane at Y y, centre c (x, z), angle a0 -> a1 (radians, from +X towards +Z)"""
    return [V(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), y, c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def main(p):
    pr = p.open(SRC); doc = pr.doc
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    cmap = colours.load(f"{_REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    src = {k: obj(k) for k in ("Bowden Left", "Bowden Right")}
    cables, ties, data, tube_lines, pieces, tube_of = {}, [], {}, [], {}, {}
    zc = {h: LANE_Z0 + (5 - SLOT[h]) * PITCH for h, _, _ in R.HEADS}     # slot 1 on top
    zc_c = LANE_Z0 + 2 * PITCH                                          # the channel's centre lane (Z)
    for h, tlab, slab in R.HEADS:
        sg, n = SG[h], SLOT[h]
        pts_in, I = R.route(p, pr, obj, h, tlab, slab, src)
        tp, u0, u1 = I["tube_poles"], I["u_join"], I["u_roof"]
        # the exit axis, measured from the tube solid (as lite-36 did)
        t = I["tube"]
        def centre(z):
            sec = pr.shapes[t.Name].slice(V(0, 0, 1), z)
            p.check(len(sec) == 1, f"{h}: {tlab} cut by Z {z} in one loop"); return Part.Face(sec[0]).CenterOfMass
        E, E2 = centre(690.0), centre(700.0); Dv = E2 - E; Dv = V(0, Dv.y, Dv.z); Dv.normalize()
        X = V(1, 0, 0); Ec = E + X * (sg * SEP)
        cb = pr.shapes[obj(CLAMP.format(part="base", n=n)).Name].BoundBox
        p.check(cb.XMin - 1 < Ec.x < cb.XMax + 1, f"{h}: the cable's clamp axis X {Ec.x:.2f} is inside clamp slot {n} (X {cb.XMin:.1f}..{cb.XMax:.1f})")
        # the bundle: side vector turns from the lead-in's (w at the join) to sg*X at the roof; spacing sgap -> SEP
        w0 = I["sides"][0]; sgap = I["sgap"]
        bun = []
        N = len(I["pts_tube"]) - 1
        for i, q in enumerate(I["pts_tube"]):
            f = i / N; uu = u0 + (u1 - u0) * f
            Ti = R.tangent(tp, uu)
            a = w0 - Ti * w0.dot(Ti); a.normalize()
            b = X * sg - Ti * (X * sg).dot(Ti); b.normalize()
            ang = math.acos(max(-1.0, min(1.0, a.dot(b))))
            ax = a.cross(b)
            if ax.Length < 1e-9: s = a
            else:
                ax.normalize(); s = FreeCAD.Rotation(ax, math.degrees(ang * f)).multVec(a)
            bun.append(q + s * (sgap + (SEP - sgap) * f))
        end_in = bun[-1]
        p.check((end_in - Ec).Length < 0.3, f"{h}: the bundle reaches the roof at the clamp's cable axis (off by {(end_in - Ec).Length:.3f} mm)")
        through = [Ec + Dv * (CL_S1 * k / 12) for k in range(1, 13)]
        Ctop = Ec + Dv * CL_S1
        # lead-in into the lane: search the run along X and both handles for the gentlest bend
        best = None
        for dx in DXS:
            P3 = V(Ctop.x + dx, LANE_Y, zc[h])
            for a in HANDLES:
                for b in HANDLES:
                    pl = [tuple(Ctop), tuple(Ctop + Dv * a), tuple(P3 - X * b), tuple(P3)]
                    r = bezier.min_radius(pl, 120)
                    if best is None or r > best[0]: best = (r, dx, a, b, pl)
        r_out, dx, a, b, pl_out = best
        p.check(r_out >= R.MIN_R, f"{h}: clamp -> lane lead-in bends R {r_out:.1f} (run {dx:.0f} along X, handles {a:.0f}/{b:.0f})")
        out = pts_of(pl_out, 80)
        # the lane: +X to X_A, the corner, down to Z_END
        rl = R0 + (zc[h] - LANE_Z0); cz = LANE_Z0 - R0
        p.check(X_A - out[-1].x > 5.0, f"{h}: its lane runs forward: from X {out[-1].x:.1f} to the corner at X {X_A:.0f}")
        run = [V(out[-1].x + (X_A - out[-1].x) * k / 40, LANE_Y, zc[h]) for k in range(1, 41)]
        corner = arc_pts((X_A, cz), rl, math.pi / 2, 0.0, 40, LANE_Y)[1:]
        down = [V(X_A + rl, LANE_Y, cz - (cz - Z_END) * k / 40) for k in range(1, 41)]
        path = I["pts_lead"] + bun[1:] + through + out[1:] + run + corner + down
        r_min, where = min_r3(path)
        p.check(r_min >= R.MIN_R - 0.5, f"{h}: the whole cable bends no tighter than R {r_min:.1f} (at Z {where.z:.0f}; MIN_R {R.MIN_R:.0f})")
        cables[h] = path
        pieces[h] = dict(lead=I["lead"], bun=bun, Ec=Ec, Ctop=Ctop, out=pl_out, run=(out[-1], V(X_A, LANE_Y, zc[h])),
                         corner=(V(X_A, LANE_Y, zc[h]), V(X_A, 0, cz)), down=(V(X_A + rl, LANE_Y, cz), V(X_A + rl, LANE_Y, Z_END)))
        tube_lines.append((h, Ctop - X * (sg * SEP), Dv)); tube_of[h] = t
        # ties: round tube + cable at TIE_AT along the bundle
        L, acc, k = 0.0, [0.0], 0
        for i in range(1, len(bun)): acc.append(acc[-1] + (bun[i] - bun[i - 1]).Length)
        for s_at in TIE_AT:
            i = min(range(len(acc)), key=lambda j: abs(acc[j] - s_at))
            qt, qc = I["pts_tube"][i], bun[i]
            Ti = R.tangent(tp, u0 + (u1 - u0) * i / N)
            ties.append((h, s_at, qt, qc, Ti))
        data[h] = dict(join_z=round(bez(tp, u0).z, 1), r_lead_in=round(I["r_lead"], 1), r_out=round(r_out, 1),
                       r_min_whole=round(r_min, 1), lane_z=zc[h], run_dx=dx)
    # ---------------- solids
    grp = doc.addObject("App::DocumentObjectGroup", "O2S_cables"); grp.Label = GROUP
    obj(EXTRAS).addObject(grp)
    made, cab_objs, tie_objs, cab_shape = [], [], [], {}
    def add(name, label, shape):
        o = doc.addObject("Part::Feature", name); o.Shape = shape; o.Label = label; grp.addObject(o); made.append(o); return o
    for h, path in cables.items():
        s, L, how = cable_solid(pieces[h], RC)
        want = math.pi * RC * RC * L
        p.check(s.isValid() and len(s.Solids) == 1 and abs(s.Volume - want) < 0.01 * want,
                f"{h}: cable solid ({how}), {L:.0f} mm, {s.Volume:.0f} mm3 (pi r^2 L {want:.0f}), valid {s.isValid()}")
        data[h]["modelled_mm"] = round(L)
        cab_shape[h] = s
        cab_objs.append(add("O2S_cable", f"O2S USB cable slot {SLOT[h]} (Ø5.1, ~3 m; modelled lock to the side pack)", s))
    for h, s_at, qt, qc, Ti in ties:
        # a stadium band round both: hull of two circles (tube r + clr, cable r + clr), TIE_T thick, TIE_W wide
        ax = qc - qt; d = ax.Length; ax.normalize()
        ri_t, ri_c = R.R_TUBE + TIE_CLR, RC + TIE_CLR
        def stadium(rt, rc_):
            c1 = Part.makeCylinder(rt, TIE_W, qt - Ti * (TIE_W / 2), Ti)
            c2 = Part.makeCylinder(rc_, TIE_W, qc - Ti * (TIE_W / 2), Ti)
            hull = c1.fuse(c2)
            # the band between: a box-ish loft of the two tangent lines (approximated by a wedge prism)
            nrm = Ti.cross(ax); nrm.normalize()
            sphi = (rc_ - rt) / d; cphi = math.sqrt(1 - sphi * sphi)        # the circles' outer common tangents
            up, dn = nrm * cphi - ax * sphi, nrm * -cphi - ax * sphi
            poly = [qt + up * rt, qc + up * rc_, qc + dn * rc_, qt + dn * rt, qt + up * rt]
            f = Part.Face(Part.makePolygon([q - Ti * (TIE_W / 2) for q in poly]))
            return hull.fuse(f.extrude(Ti * TIE_W)).removeSplitter()
        band = stadium(ri_t + TIE_T, ri_c + TIE_T).cut(stadium(ri_t, ri_c))
        nrm = Ti.cross(ax); nrm.normalize()
        head = Part.makeBox(4.5, 4.0, 3.5)                    # local X along nrm, Y outward along ax, Z along -Ti
        bk = -Ti                                              # (nrm, ax, -Ti) is right-handed: nrm x ax = -Ti
        m = FreeCAD.Matrix(nrm.x, ax.x, bk.x, 0, nrm.y, ax.y, bk.y, 0, nrm.z, ax.z, bk.z, 0, 0, 0, 0, 1)
        head.Placement = FreeCAD.Placement(m)
        head.translate(qc + ax * (ri_c + TIE_T - 0.3) - nrm * 2.25 + Ti * 1.75)
        p.check(head.common(band).Volume > 1.0, f"{h}: tie head sits on its band ({head.common(band).Volume:.2f} mm3 shared)")
        tie = band.fuse(head).removeSplitter()
        nominal = tie.Volume
        ov_c, ov_t = tie.common(cab_shape[h]).Volume, tie.common(pr.shapes[tube_of[h].Name]).Volume; ov = ov_c + ov_t
        tie = tie.cut(cab_shape[h]).cut(pr.shapes[tube_of[h].Name]).removeSplitter()
        sols = sorted(tie.Solids, key=lambda x: -x.Volume); sliver = sum(x.Volume for x in sols[1:])
        tie = sols[0]                                          # the cut can leave a sliver beside the cable: dropped
        # measured 0 with the head placed right; the cut and the 2 % allowance only absorb solid-modelling noise
        p.check(ov < 0.02 * nominal and ov_t < 0.01 and sliver < 0.01 * nominal and tie.isValid(),
                f"{h}: tie at {s_at:.0f} mm overlapped its cable by {ov_c:.3f}, its tube by {ov_t:.3f} mm3 before fitting "
                f"(< 2 % of {nominal:.0f}; tube ~0); fitted round both: {len(sols)} piece(s), slivers {sliver:.3f} dropped; {tie.Volume:.1f} mm3")
        tie_objs.append(add("Zip_tie", f"Zip tie, black (2.5 mm) slot {SLOT[h]} at {s_at:.0f} mm", tie))
    # the channel: U in the lane plane, swept along the centre lane's path; open to the back (+Y)
    hz = 2 * PITCH + RC + CLR                                   # half-height of the inner space about the centre lane
    cz = LANE_Z0 - R0                                           # the corner's axis height (along Y, at X_A)
    def section(y0, y1, n0, n1):
        """a rectangle (Y y0..y1; Z zc_c+n0..zc_c+n1) in the plane X = X_A, carried along the channel: extruded back
        to X_START, revolved 90 deg down round the corner's axis, then straight down to Z_END"""
        z0, z1 = zc_c + n0, zc_c + n1
        f = Part.Face(Part.makePolygon([V(X_A, y0, z0), V(X_A, y1, z0), V(X_A, y1, z1), V(X_A, y0, z1), V(X_A, y0, z0)]))
        hor = f.extrude(V(X_START - X_A, 0, 0))
        cor = f.revolve(V(X_A, 0, cz), V(0, 1, 0), 90)
        ver = Part.makeBox(z1 - z0, y1 - y0, cz - Z_END, V(X_A + (z0 - cz), y0, Z_END))
        return hor.fuse([cor, ver]).removeSplitter()
    outer = section(Y_IN0 - WALL, Y_IN1, -hz - WALL, hz + WALL)
    inner = section(Y_IN0, Y_IN1 + 1, -hz, hz)
    body = outer.cut(inner)
    body = body.fuse(Part.makeBox(WALL, Y_IN1 - Y_IN0 + WALL, 2 * hz + 2 * WALL, V(X_START - WALL, Y_IN0 - WALL, zc_c - hz - WALL)))
    cover = section(Y_IN1, Y_IN1 + COV_T, -hz - WALL, hz + WALL)
    p.check(body.isValid() and cover.isValid(), f"channel body {body.Volume:.0f} mm3, cover {cover.Volume:.0f} mm3, valid")
    # entry slots: where each cable's lead-in passes the body, a box from there to the open back
    slots = []
    for h, path in cables.items():
        inside = [q for q in pts_of(pieces[h]["out"], 200) if outer.BoundBox.isInside(q)]   # the lead-out, up to its lane
        if not inside: continue
        xs, ys, zs = [q.x for q in inside], [q.y for q in inside], [q.z for q in inside]
        e = RC + 0.8
        slots.append(Part.makeBox(max(xs) - min(xs) + 2 * e, Y_IN1 + 1 - (min(ys) - e), max(zs) - min(zs) + 2 * e,
                                  V(min(xs) - e, min(ys) - e, min(zs) - e)))
    for sl in slots: body = body.cut(sl)
    body = body.removeSplitter()
    p.check(body.isValid() and len(body.Solids) == 1, f"channel body with {len(slots)} entry slots: one valid solid ({len(body.Solids)})")
    ch_o = add("Cable_channel", "Cable channel body, roof to side pack (printed, vt350, GPL-3.0-or-later)", body)
    cv_o = add("Cable_channel_cover", "Cable channel cover, roof to side pack (printed, vt350, GPL-3.0-or-later)", cover)
    # posts: from the roof panel over the rear 4040's rear slot up to under the channel; X picked clear of the cables
    zb = zc_c - hz - WALL
    cab_shapes = [o.Shape for o in cab_objs]
    clamps = [obj(CLAMP.format(part=pt, n=n)) for n in range(1, 6) for pt in ("base", "cap")]
    def post_at(x):
        col = Part.makeBox(POST_W, POST_Y1 - POST_Y0, zb - PANEL_TOP, V(x - POST_W / 2, POST_Y0, PANEL_TOP))
        arm = Part.makeBox(POST_W, Y_IN0 - WALL - POST_Y0, 12.0, V(x - POST_W / 2, POST_Y0, zb - 12.0))
        return col.fuse(arm).removeSplitter()
    free = []
    for x in range(int(X_START) + 10, int(X_A) - 10, 5):
        ps = post_at(float(x)); bb = ps.BoundBox
        if any(c.BoundBox.intersect(bb) and c.common(ps).Volume > TOL for c in cab_shapes): continue
        if any(pr.boxes[c.Name].intersect(bb) and pr.shapes[c.Name].common(ps).Volume > TOL for c in clamps): continue
        if any(R.box_gap(o + Dv * k, bb) < 2.0 + R.R_TUBE for _, o, Dv in tube_lines for k in range(0, 200, 4)): continue
        free.append(float(x))
    chosen = []
    for target in [X_START + 15 + (X_A - 40 - X_START - 15) * k / 3 for k in range(4)]:
        if free: chosen.append(min(free, key=lambda x: abs(x - target)))
    chosen = sorted(set(chosen))
    gaps = [b - a for a, b in zip([X_START] + chosen, chosen + [X_A])]
    p.check(len(chosen) == 4 and max(gaps) <= 200, f"posts at X {chosen} (clear of cables, clamps and tube lines); spans {[round(g) for g in gaps]}")
    posts = [add("Cable_channel_post", f"Cable channel post {i + 1} (printed, M5 to the rear 4040)", post_at(x)) for i, x in enumerate(chosen)]
    # arms: from the rear-right upright's back face (Y 520, X -10..30) to the vertical run's front wall
    xv0 = X_A + R0 - RC - CLR - WALL                            # the vertical run's inner side (lane 5's side)
    arms = [add("Cable_channel_arm", f"Cable channel arm {i + 1} (printed, M5 to the rear-right upright)",
                Part.makeBox(xv0 + 20 - 10, Y_IN0 - WALL - 520.0, 12.0, V(10.0, 520.0, z - 6)).cut(outer)) for i, z in enumerate(ARM_Z)]
    doc.recompute(); pr.refresh()
    # ---------------- checks on the result
    mine = {o.Name for o in made}
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in cab_objs], pr, lambda r: f"the cables vs everything: {r.hits[:6]}",
                 exclude={o.Name for o in cab_objs})
    for i, a in enumerate(cab_objs):
        for b in cab_objs[i + 1:]:
            v = pr.shapes[a.Name].common(pr.shapes[b.Name]).Volume if pr.shapes[a.Name].BoundBox.intersect(pr.shapes[b.Name].BoundBox) else 0.0
            p.check(v < TOL, f"{a.Label[:30]} vs {b.Label[:30]}: {v:.3f} mm3")
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in tie_objs], pr, lambda r: f"the zip ties vs everything: {r.hits[:6]}", exclude=mine)
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in tie_objs], pr, lambda r: f"the zip ties vs the cables: {r.hits[:6]}",
                 exclude=mine - {o.Name for o in cab_objs})
    rigid = [ch_o, cv_o] + posts + arms
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in rigid], pr, lambda r: f"channel, cover, posts, arms vs the printer: {r.hits[:6]}", exclude=mine)
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in [ch_o, cv_o]], pr, lambda r: f"channel + cover vs the cables: {r.hits[:6]}",
                 exclude=mine - {o.Name for o in cab_objs})
    for h, o, Dv in tube_lines:
        line = Part.LineSegment(o, o + Dv * 250).toShape()
        d = min(line.distToShape(pr.shapes[x.Name])[0] for x in rigid)
        p.check(d >= R.R_TUBE + 2.0, f"{h}: its tube's line, extended 250 mm past the clamp, clears the channel/posts by {d - R.R_TUBE:.1f} mm")
    def gpath(o):
        r_, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r_.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r_))
    want = [(cab_objs[0], "black_plastic"), (tie_objs[0], "black_plastic"), (ch_o, "printed"), (cv_o, "accent"), (posts[0], "printed"), (arms[0], "printed")]
    for o, r in want:
        r_ = colours.role_of(cmap, o.Label, gpath(o), "Default")
        p.check(r_ == r, f"{o.Label[:50]}: role {r_}")
    added = len(cab_objs) + len(tie_objs) + 2 + len(posts) + len(arms)
    p.check(len(pr.leaves) == n_before + added == n_before + 5 + 20 + 2 + 4 + 2, f"solids: {n_before} + {added} = {len(pr.leaves)}")
    p.dump({"heads": data, "channel": {"lane_y": LANE_Y, "lanes_z": [zc[h] for h, _, _ in R.HEADS], "inner_r": R0, "end_z": Z_END,
            "body_mm3": round(body.Volume), "cover_mm3": round(cover.Volume), "posts_x": chosen},
            "ties": len(tie_objs)})
    p.finish([(doc, DST)])


litelib.Pass("lite40_o2s_cables").run(main)
