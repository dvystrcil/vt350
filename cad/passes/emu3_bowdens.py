# GUI pass: vt350-emu-2.FCStd -> vt350-emu-3.FCStd   (reads vt350-lite-61 for the roof ends; headless = dry run)
# vt350#187 AC3. The bowden from each roof exit to its EMU lane (owner, 2026-11-16: "we need to add a bowden from the
# roof to the emu. I think this can be part of the EMU document"). The printer model's five "Bowden ..." tubes end
# 20 mm past their roof clamps (lite-36), heading up and back at 45 deg; each EMU lane's filament outlet is a push-fit
# coupler ("Main body" + "Release clip") on the EMU's rear wall, facing +Y. Lanes and heads pair in X order (lane 1
# = the leftmost head, slot 1 ... lane 5 = slot 5); the X shift between them is <= 20 mm.
#  - Route, in the YZ plane, then X: from the roof end along the tube's own direction, ARC 1 (R 100) turns it up and
#    over to head forward (-Y) at its top (Z ~882), staying in front of the cable channel (Y 533) at Y <= 525; then an
#    S down to the coupler's height (two arcs R 100, a straight between), then >= 25 mm straight into the coupler.
#    The X shift is spread over the S (smoothstep). A cubic Bezier was tried first: 26 mm smallest bend radius under
#    the Y 525 limit, too tight for PTFE; this keeps >= 80 (R 100 arcs; the B-spline through them dips to ~86 where
#    an arc meets a straight).
#  - Tube: PTFE 4.12 OD (measured, lite-36), swept (binormal fixed along X) along a B-spline through the route; it ends on the coupler's face
#    (the push-fit grips ~10 mm inside it; not modelled into the coupler).
#  - Saved in the EMU document (its own group, global frame), so the printer model is unchanged.
# Checks (refuses to save on any): five head tube ends and five couplers found and paired; each new tube one valid
# solid, starting on its head tube's end along its direction (<= 0.05 mm, <= 0.5 deg) and ending on its coupler's face
# along -Y; smallest bend radius >= 80 mm; max Y <= 525; no tube overlaps an EMU part, a printer part (lite-61;
# envelopes excepted, the head tubes it continues excepted) or another new tube.
import FreeCAD, Part, os, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
PRINTER, EMU, EMU3 = f"{MODELS}/vt350-lite-61.FCStd", f"{MODELS}/vt350-emu-2.FCStd", f"{MODELS}/vt350-emu-3.FCStd"
ROOT = "EMU 5-lane (DW-Tas)"
R_T = 4.12 / 2
R1, R2, LF_MIN, MIN_R, Y_MAX = 100.0, 100.0, 25.0, 80.0, 525.0   # arcs R 100; the spline through them dips to ~86 where an arc meets a straight


def route_yz(e, ed, o):
    """[(y, z)] samples, 1 mm apart, from the roof end e (y, z) heading ed (dy, dz) to the coupler face o (y, z),
    arriving along -Y. Arc 1 (R1, ccw) to head -Y, an S of two R2 arcs with a straight between, a straight run in."""
    pts = []
    ang0 = math.atan2(ed[1], ed[0])                               # 45 deg
    n = (-math.sin(ang0), math.cos(ang0))                         # left normal: the centre is that way (ccw)
    c = (e[0] + R1 * n[0], e[1] + R1 * n[1])
    a0, a1 = ang0 - math.pi / 2, math.pi / 2                      # point angles round c: start .. top
    k = max(2, int(R1 * (a1 - a0)))
    pts += [(c[0] + R1 * math.cos(a0 + (a1 - a0) * i / k), c[1] + R1 * math.sin(a0 + (a1 - a0) * i / k)) for i in range(k + 1)]
    top = pts[-1]; i_top = len(pts) - 1
    drop, span = top[1] - o[1], top[0] - o[0]
    for th in [math.radians(t) for t in range(5, 80)]:
        ls = (drop - 2 * R2 * (1 - math.cos(th))) / math.sin(th)
        lf = span - 2 * R2 * math.sin(th) - ls * math.cos(th)
        if ls >= 0 and lf >= LF_MIN: break
    else:
        raise RuntimeError(f"no S fits: drop {drop:.1f}, span {span:.1f}")
    # S arc 2: heading -Y, turning down (cw seen with +Y right): centre below
    c2 = (top[0], top[1] - R2)
    k = max(2, int(R2 * th))
    pts += [(c2[0] - R2 * math.sin(th * i / k), c2[1] + R2 * math.cos(th * i / k)) for i in range(1, k + 1)]
    p, d = pts[-1], (-math.cos(th), -math.sin(th))
    k = max(1, int(ls))
    pts += [(p[0] + d[0] * ls * i / k, p[1] + d[1] * ls * i / k) for i in range(1, k + 1)]
    p = pts[-1]
    c3 = (p[0] - R2 * math.sin(th), p[1] + R2 * math.cos(th))                       # centre above (cw back to -Y)
    k = max(2, int(R2 * th))
    pts += [(c3[0] + R2 * math.sin(th * (1 - i / k)), c3[1] - R2 * math.cos(th * (1 - i / k))) for i in range(1, k + 1)]
    p = pts[-1]; i_in = len(pts) - 1
    k = max(1, int(p[0] - o[0]))
    pts += [(p[0] - (p[0] - o[0]) * i / k, o[1]) for i in range(1, k + 1)]
    return pts, i_top, i_in, math.degrees(th), ls, lf


def main(p):
    pr = p.open(PRINTER)
    tubes = sorted([o for o in pr.leaves if o.Label.startswith("Bowden") and pr.boxes[o.Name].ZMax > 700],
                   key=lambda o: pr.boxes[o.Name].XMin)
    p.check(len(tubes) == 5, f"head tubes reaching the roof: {len(tubes)} (5): {[o.Label for o in tubes]}")
    ends = []
    for o in tubes:
        circ = [e for e in pr.shapes[o.Name].Edges if isinstance(e.Curve, Part.Circle)]
        top = max(circ, key=lambda e: e.Curve.Center.z)
        ax = top.Curve.Axis; ax = ax if ax.z > 0 else -ax
        ends.append((o, top.Curve.Center, ax, top.Curve.Radius))
        p.log(f"{o.Label}: end {tuple(round(v, 2) for v in top.Curve.Center)}, dir {tuple(round(v, 3) for v in ax)}, r {top.Curve.Radius:.2f}")
    em = p.open(EMU); ed = em.doc
    # each lane has two push-fits (one inside the box at Y ~144, one on the rear wall at Y ~197): the rear wall's
    rear = lambda o: em.boxes[o.Name].YMax > 180
    clips = sorted([o for o in em.leaves if o.Label.startswith("Release clip") and rear(o)], key=lambda o: em.boxes[o.Name].XMin)
    bodies = sorted([o for o in em.leaves if o.Label.startswith("Main body") and rear(o)], key=lambda o: em.boxes[o.Name].XMin)
    p.check(len(clips) == 5 and len(bodies) == 5, f"EMU couplers: {len(clips)} release clips, {len(bodies)} bodies (5 each)")
    outs = []
    for c in clips:
        b = em.boxes[c.Name]
        outs.append(V((b.XMin + b.XMax) / 2, b.YMax, (b.ZMin + b.ZMax) / 2))
    p.log(f"coupler faces: {[tuple(round(v, 1) for v in o) for o in outs]}")
    root = em.root(ROOT)
    grp = ed.addObject("App::Part", "Bowdens"); grp.Label = "Bowdens, roof exits to the lanes (emu-3, #187)"
    root.addObject(grp)
    made = []
    for i, ((tube, e, ax, r), o) in enumerate(zip(ends, outs), 1):
        p.check(abs(e.x - o.x) <= 25, f"lane {i}: head X {e.x:.1f}, lane X {o.x:.1f} (paired in X order, shift {o.x - e.x:+.1f})")
        yz, i_top, i_in, th, ls, lf = route_yz((e.y, e.z), (ax.y, ax.z), (o.y, o.z))
        # X: the head's X up to the top of arc 1, then a smoothstep over the S to the lane's, straight in at the lane's
        pts = []
        for k, (y, z) in enumerate(yz):
            t = min(1.0, max(0.0, (k - i_top) / (i_in - i_top)))
            t = t * t * (3 - 2 * t)
            pts.append(V(e.x + (o.x - e.x) * t, y, z))
        pts = pts[::3] + ([pts[-1]] if (len(pts) - 1) % 3 else [])
        bs = Part.BSplineCurve(); bs.interpolate(pts, InitialTangent=ax, FinalTangent=V(0, -1, 0))
        edge = bs.toShape()
        rmin = min(1 / max(1e-12, edge.curvatureAt(edge.FirstParameter + (edge.LastParameter - edge.FirstParameter) * j / 2000))
                   for j in range(2001))
        prof = Part.Wire(Part.makeCircle(R_T, pts[0], ax))
        # Fixed binormal (+X: each route is nearly in a plane X = const). Frenet twists the circle on the straights
        # (a solid of 57 % the tube's volume), corrected Frenet can't close the solid, makePipe segfaults (LESSONS.md).
        ps = Part.BRepOffsetAPI.MakePipeShell(Part.Wire(edge)); ps.setBiNormalMode(V(1, 0, 0)); ps.add(prof)
        ps.build(); ps.makeSolid(); sweep = ps.shape()
        if sweep.Volume < 0: sweep.reverse()                    # an inside-out sweep: turn it right side out
        want = math.pi * R_T ** 2 * edge.Length
        p.check(sweep.isValid() and len(sweep.Solids) == 1 and abs(sweep.Volume - want) < 0.01 * want,
                f"lane {i} tube: one valid solid, {sweep.Volume:.0f} mm3 (pi r2 L = {want:.0f}), length {edge.Length:.0f}")
        p.check(rmin >= MIN_R, f"lane {i} tube: smallest bend radius {rmin:.1f} (>= {MIN_R:.0f}); S {th:.0f} deg, straight in {lf:.0f}")
        bb = sweep.BoundBox
        p.check(bb.YMax <= Y_MAX, f"lane {i} tube: Y max {bb.YMax:.1f} (<= {Y_MAX:.0f}, in front of the cable channel), Z max {bb.ZMax:.1f}")
        t0, t1 = edge.tangentAt(edge.FirstParameter), edge.tangentAt(edge.LastParameter)
        p.check(edge.Vertexes[0].Point.distanceToPoint(e) <= 0.05 and math.degrees(t0.getAngle(ax)) <= 0.5,
                f"lane {i}: starts on {tube.Label}'s end along its direction ({edge.Vertexes[0].Point.distanceToPoint(e):.3f} mm, {math.degrees(t0.getAngle(ax)):.2f} deg)")
        p.check(edge.Vertexes[-1].Point.distanceToPoint(o) <= 0.05 and math.degrees(t1.getAngle(V(0, -1, 0))) <= 0.5,
                f"lane {i}: ends on its coupler's face along -Y ({edge.Vertexes[-1].Point.distanceToPoint(o):.3f} mm)")
        obj = ed.addObject("Part::Feature", "Bowden_roof_emu"); grp.addObject(obj)
        loc = sweep.copy(); loc.Placement = linkgeo.gplace(grp).inverse().multiply(loc.Placement)
        obj.Shape = loc
        obj.Label = f"Bowden lane {i} to {tube.Label} (PTFE 4.12 OD, roof exit to the EMU, {edge.Length:.0f} mm)"
        if FreeCAD.GuiUp:
            try: obj.ViewObject.ShapeAppearance = (linkgeo.drawn_vo(tube) or tube.ViewObject).ShapeAppearance
            except Exception: pass
        made.append((obj, sweep, edge.Length, rmin))
    ed.recompute(); em.refresh()
    items = [(o.Label, s) for o, s, *_ in made]
    p.no_overlap(items, em, lambda r: f"no tube overlaps an EMU part: {len(r.hits)} {r.hits[:8]}", exclude={o.Name for o, *_ in made})
    skip = {o.Name for o in pr.leaves if "envelope" in o.Label} | {t.Name for t, *_ in ends}
    p.no_overlap(items, pr, lambda r: f"no tube overlaps a printer part (lite-61): {len(r.hits)} {r.hits[:8]}", exclude=skip)
    for a in range(len(made)):
        for b in range(a + 1, len(made)):
            v = made[a][1].common(made[b][1]).Volume
            p.check(v < 1e-3, f"tube {a + 1} vs tube {b + 1}: {v:.4f} mm3")
    p.dump({"tubes": [{"label": o.Label, "length": round(L), "min_radius": round(r, 1)} for o, s, L, r in made],
            "total_ptfe_mm": round(sum(L for *_, L, r in made))})
    return p.finish([(ed, EMU3)])


litelib.Pass("emu3_bowdens").run(main)
