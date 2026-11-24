#!/usr/bin/env python3
"""Top view of the front strip: where the nozzle goes during the Beacon scan, against the head's front limit
(vt350#291, #309). Plain python, read-only.

With the Beacon at y_offset 27.4 the front mesh row is the coil centre the head can reach (printer Y 15.73). The scan
path is Beacon's own (cad/motion/beacon_scan.py: _generate_path and the auto overscan). Three choices, one panel each:
  1. scan lines along Y (today's mesh_main_direction) with the auto overscan
  2. scan lines along X (mesh_main_direction: x)
  3. lines along Y with mesh_overscan capped, and mesh_min Y moved back by the cap so the front turns stay clear
The front limit per X is the nozzle's furthest-forward clear Y, worse of the two heads (cad/data/front_reach_front17.json,
lite-78 front). Red: the path in front of it.

Run: python3 cad/studies/beacon_scan_turns.py [--cap 5]  ->  cad/data/beacon_scan_turns.svg
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(CAD, "motion")]
import beacon_scan as bs                     # noqa: E402
import beacon_scan_footprint as fpm          # noqa: E402

OUT = os.path.join(CAD, "data", "beacon_scan_turns.svg")
DY = 27.4
MESH_X = (5.48, 344.52)
MESH_MAX_Y = 344.52


def limits(front, mapping):
    """Sorted [(printer X, nozzle front limit Y)], worse head per sample."""
    (ox, oy), (gx, gy) = mapping["origin_model_xy"], mapping["sign_xy"]
    rows = {}
    for rs in front["heads"].values():
        for r in rs:
            rows.setdefault(round(gx * (r["x"] - ox), 2), []).append(round(gy * (r["clear"] - oy), 2))
    return sorted((x, max(v)) for x, v in rows.items() if len(v) == len(front["heads"]))


def limit_at(lim, x):
    """The limit at X: the worse of the two samples either side (conservative between samples)."""
    lo = [y for a, y in lim if a <= x]; hi = [y for a, y in lim if a >= x]
    c = ([lo[-1]] if lo else []) + ([hi[0]] if hi else [])
    return max(c)


def cases(safe, cap):
    m0y = round(safe + DY, 2)
    c = []
    mn, mx = (MESH_X[0], m0y), (MESH_X[1], MESH_MAX_Y)
    o = bs.overscan(mn, mx, bs.PROBE_COUNT, (0.0, DY), direction="y")
    c.append(dict(title=f"1. Lines along Y, auto overscan {o:.2f} (today's direction)", mesh_min=mn, over=o, d="y"))
    o = bs.overscan(mn, mx, bs.PROBE_COUNT, (0.0, DY), direction="x")
    c.append(dict(title=f"2. Lines along X (mesh_main_direction: x), auto overscan {o:.2f}", mesh_min=mn, over=o, d="x"))
    mn3 = (MESH_X[0], round(m0y + cap, 2))
    c.append(dict(title=f"3. Lines along Y, mesh_overscan {cap:g}, mesh_min Y moved back {cap:g} to {mn3[1]:g}", mesh_min=mn3, over=cap, d="y"))
    for k in c:
        k["path"] = bs.scan_path(k["mesh_min"], (MESH_X[1], MESH_MAX_Y), bs.PROBE_COUNT, (0.0, DY), over=k["over"], direction=k["d"])
    return c


def worst_past(path, lim):
    """How far the path goes in front of the limit (mm, > 0 = past it)."""
    return max(0.0, round(max(limit_at(lim, x) - y for x, y in path), 2))


def svg(cs, lim, safe):
    sc, y0, y1, x0, x1 = 2.6, -52.0, 62.0, -12.0, 362.0        # printer coords window
    PW, PH = (x1 - x0) * sc, (y1 - y0) * sc
    top, gap = 30, 70
    X = lambda x: (x - x0) * sc
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW + 20:.0f}" height="{top + 3 * (PH + gap) + 120:.0f}" font-family="sans-serif" font-size="13">',
         '<rect width="100%" height="100%" fill="white"/>']
    for k, c in enumerate(cs):
        b = top + k * (PH + gap) + 22
        Y = lambda y: b + (y1 - y) * sc
        s.append(f'<text x="10" y="{b - 8:.1f}" font-weight="bold">{c["title"]}</text>')
        s.append(f'<rect x="{X(-2.5):.1f}" y="{Y(y1):.1f}" width="{355 * sc:.1f}" height="{(y1 + 2.5) * sc:.1f}" fill="#ddd"/>')
        s.append(f'<text x="{X(352):.1f}" y="{Y(-2.5) + 14:.1f}" text-anchor="end" fill="#555">plate front edge</text>')
        mn = c["mesh_min"]
        s.append(f'<rect x="{X(mn[0]):.1f}" y="{Y(y1):.1f}" width="{(MESH_X[1] - mn[0]) * sc:.1f}" height="{(y1 - mn[1]) * sc:.1f}" '
                 f'fill="#7a3fbf" fill-opacity="0.12" stroke="#7a3fbf" stroke-dasharray="4 3"/>')
        s.append(f'<text x="{X(mn[0]) + 4:.1f}" y="{Y(mn[1]) - 4:.1f}" fill="#7a3fbf">mesh (coil centres) from Y {mn[1]:g}</text>')
        # the front limit, stepped per X sample
        pts = []
        for i, (x, y) in enumerate(lim):
            if x < x0 or x > x1: continue
            pts.append((X(x), Y(y)))
        s.append(f'<polyline points="{" ".join(f"{u:.1f},{v:.1f}" for u, v in pts)}" fill="none" stroke="#000" stroke-width="2"/>')
        s.append(f'<line x1="{X(x0):.1f}" y1="{Y(safe):.1f}" x2="{X(x1):.1f}" y2="{Y(safe):.1f}" stroke="#000" stroke-dasharray="2 3"/>')
        s.append(f'<text x="{X(x0) + 2:.1f}" y="{Y(safe) + 30:.1f}">nozzle front limit (black; dotted = {safe:g}, the worst X)</text>')
        s.append(f'<rect x="{X(x0):.1f}" y="{Y(-14):.1f}" width="{(x1 - x0) * sc:.1f}" height="{(y0 + 14) * -sc:.1f}" fill="#000" fill-opacity="0.06"/>')
        s.append(f'<text x="{X(175):.1f}" y="{Y(y0) - 6:.1f}" text-anchor="middle" fill="#555">docks / parked heads side</text>')
        # the nozzle path, clipped to the window by drawing segments, red where in front of the limit
        p = c["path"]
        for (ax, ay), (bx, by) in zip(p, p[1:]):
            if max(ay, by) < y0 - 5 or min(ay, by) > y1 + 5: continue
            bad = limit_at(lim, ax) - ay > 0.01 or limit_at(lim, bx) - by > 0.01
            cy = lambda y: min(max(y, y0), y1)
            s.append(f'<line x1="{X(ax):.1f}" y1="{Y(cy(ay)):.1f}" x2="{X(bx):.1f}" y2="{Y(cy(by)):.1f}" '
                     f'stroke="{"#d32f2f" if bad else "#1f5fbf"}" stroke-width="{2.5 if bad else 1.5}"/>')
        w = worst_past(p, lim)
        ymin = min(y for _, y in p)
        txt = (f"nozzle reaches Y {ymin:.2f}: {w:.2f} mm in front of the limit (red)" if w > 0.01
               else f"nozzle reaches Y {ymin:.2f}: clear of the limit everywhere")
        s.append(f'<text x="10" y="{Y(y0) + 18:.1f}" fill="{"#d32f2f" if w > 0.01 else "#1b8a3a"}" font-weight="bold">{txt}. '
                 f'Coil footprint front edge (plate Y) {mn[1] - fpm.footprint(0, 0)["half"] + 2.5:.2f}</text>')
    yb = top + 3 * (PH + gap) + 20
    for i, line in enumerate((
            "Top view of the front strip, printer coordinates (plate Y = printer Y + 2.5), front at the bottom.",
            f"Blue / red: the NOZZLE path of Beacon's scan (beacon_scan.py, its own path and overscan); the coil runs {DY:g} behind it.",
            "Purple: the mesh, in coil-centre positions (the mesh's front row is where the coil centre is when the nozzle is at the limit).",
            "Black: the nozzle's furthest-forward clear Y per X, worse of the two heads (front_reach_front17.json, lite-78 front).",
            f"~10 mm X samples; between samples the worse neighbour counts. 1 mm = {sc:g} px.")):
        s.append(f'<text x="10" y="{yb + 18 * i}">{line}</text>')
    s.append("</svg>")
    return "\n".join(s)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cap", type=float, default=5.0, help="mesh_overscan for choice 3 (mm)")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    with open(fpm.FRONT_REACH, encoding="utf-8") as f, open(fpm.MAPPING, encoding="utf-8") as g:
        front, mapping = json.load(f), json.load(g)
    safe = fpm.safe_nozzle_y(front, mapping)
    lim = limits(front, mapping)
    cs = cases(safe, a.cap)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(svg(cs, lim, safe))
    for c in cs:
        print(f'{c["title"]}: nozzle Y min {min(y for _, y in c["path"]):.2f}, past the limit by {worst_past(c["path"], lim)}')
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
