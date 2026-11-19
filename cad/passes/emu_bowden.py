# emu_bowden: the roof-exit -> EMU-lane bowden route and tube, shared by the EMU passes (vt350#187).
# route_yz is emu3_bowdens.py's, copied unchanged (that pass already ran and stays as it was); tube() is its sweep.
import math
import FreeCAD, Part
V = FreeCAD.Vector
N_CURV = 8000                # curvature samples along a tube (2000 missed a 3 mm curl)
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


def tube(e, ax, o, lead=0.0):
    """The tube from the head tube's roof end e (heading ax) to the coupler face o: (sweep, edge, rmin, th, lf).
    `lead` mm straight on along ax first (out of the roof clamp's bore: emu-3's arc began inside it and cut 1.25 mm
    into the cap), then the route. X follows the head up to the top of arc 1, then a smoothstep over the S."""
    k0 = int(round(lead))
    lead_pts = [V(e.x, e.y + ax.y * lead * i / k0, e.z + ax.z * lead * i / k0) for i in range(k0)] if k0 else []
    e1 = e + ax * lead
    yz, i_top, i_in, th, ls, lf = route_yz((e1.y, e1.z), (ax.y, ax.z), (o.y, o.z))
    pts = list(lead_pts)
    for k, (y, z) in enumerate(yz):
        t = min(1.0, max(0.0, (k - i_top) / (i_in - i_top)))
        t = t * t * (3 - 2 * t)
        pts.append(V(e.x + (o.x - e.x) * t, y, z))
    pts = pts[::3] + ([pts[-1]] if (len(pts) - 1) % 3 else [])
    # no FinalTangent: with it, the fit curls in the last ~3 mm before the coupler (a cusp, radius ~0), which
    # emu3_bowdens' 2000-sample check stepped over (LESSONS.md); the >= 25 mm straight run in sets the end direction
    bs = Part.BSplineCurve(); bs.interpolate(pts, InitialTangent=ax)
    edge = bs.toShape()
    rmin = min(1 / max(1e-12, edge.curvatureAt(edge.FirstParameter + (edge.LastParameter - edge.FirstParameter) * j / N_CURV))
               for j in range(N_CURV + 1))
    prof = Part.Wire(Part.makeCircle(R_T, pts[0], ax))
    # fixed binormal along X (LESSONS.md: Frenet twists, corrected Frenet can't close, makePipe segfaults)
    ps = Part.BRepOffsetAPI.MakePipeShell(Part.Wire(edge)); ps.setBiNormalMode(V(1, 0, 0)); ps.add(prof)
    ps.build(); ps.makeSolid(); sweep = ps.shape()
    if sweep.Volume < 0: sweep.reverse()
    return sweep, edge, rmin, th, lf
