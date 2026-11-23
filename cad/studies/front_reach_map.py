#!/usr/bin/env python3
"""Top view of the Beacon coil's front reach on the plate, per carried head (vt350#291).

    python3 cad/studies/front_reach_map.py            # writes cad/data/beacon-coverage.svg
    python3 cad/studies/front_reach_map.py --check    # fails when the committed SVG isn't what the data gives

Reads cad/data/front_reach.json (cad/studies/front_reach.py: each head's nozzle front limit per X, model coordinates),
cad/klipper/xy_mapping.json (model -> printer XY) and cad/klipper/beacon.cfg (the Beacon offset, the mesh). For each
head the line is the coil's front limit (nozzle limit + y_offset); red is the planned mesh that neither head's coil
reaches. Plain python3, standard library only. VT350-specific.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "cad", "motion")]
import beacon_scan  # noqa: E402  (reads beacon.cfg)

DATA = os.path.join(ROOT, "cad", "data", "front_reach.json")
MAPPING = os.path.join(ROOT, "cad", "klipper", "xy_mapping.json")
OUT = os.path.join(ROOT, "cad", "data", "beacon-coverage.svg")
PLATE_Y = (-2.5, 352.5)            # the 355 plate in printer Y (model -33 .. 322)
COLOURS = {"Left": ("#1f5fbf", ""), "Right": ("#d98400", "9 5")}


def limits(data=None, mapping=None):
    """{head: [(printer nozzle X, coil front Y), ...]}. A pose never blocked is clear to the scan's front end."""
    data = data or json.load(open(DATA))
    mp = mapping or json.load(open(MAPPING))
    (ox, oy), (gx, gy) = mp["origin_model_xy"], mp["sign_xy"]
    dy = data["beacon_dy"]
    return {h: [(round(gx * (r["x"] - ox), 2), round(gy * (r["clear"] - oy) + dy, 2)) for r in rows]
            for h, rows in data["heads"].items()}


def nozzle_limit(lim, beacon_dy, x):
    """A head's nozzle front limit (printer Y) at printer X, from its coil limits: the worst of the rows within one X
    step of x (conservative between samples). inf when no row is near (outside the measured X range)."""
    xs = [a for a, _ in lim]
    step = max(b - a for a, b in zip(xs, xs[1:])) if len(xs) > 1 else 0.0
    near = [y - beacon_dy for a, y in lim if abs(a - x) <= step + 1e-6]
    return max(near) if near else float("inf")


def tilt_reach(points, lim, beacon_dy, margin=1.0):
    """[(point, head, nozzle limit, ok)] for each Z-tilt point and head: ok when the point is margin behind the limit."""
    return [((x, y), h, nozzle_limit(lim[h], beacon_dy, x), y >= nozzle_limit(lim[h], beacon_dy, x) + margin)
            for x, y in points for h in sorted(lim)]


def svg(lim, mesh_min, model=""):
    W, H, L, R, T, B = 1100, 540, 80, 30, 70, 95
    X0, X1, Y0, Y1 = 0, 350, -10, 60
    sx = lambda x: L + (x - X0) / (X1 - X0) * (W - L - R)
    sy = lambda y: H - B - (y - Y0) / (Y1 - Y0) * (H - T - B)
    heads = sorted(lim)
    xs = [x for x, _ in lim[heads[0]]]
    edges = [X0] + [(a + b) / 2 for a, b in zip(xs, xs[1:])] + [X1]
    step = lambda ys: [(e, y) for i, y in enumerate(ys) for e in (edges[i], edges[i + 1])]
    pts = lambda p: " ".join(f"{sx(a):.1f},{sy(b):.1f}" for a, b in p)
    best = [min(lim[h][i][1] for h in heads) for i in range(len(xs))]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="DejaVu Sans, sans-serif" '
         f'font-size="13">', f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="{L}" y="28" font-size="18" font-weight="bold">Where the Beacon coil can reach at the front of '
         f'the plate ({model})</text>',
         f'<text x="{L}" y="50" fill="#555">Top view, printer coordinates (mm). Each line is the furthest forward '
         f'the coil gets with that head carried. Red: planned mesh neither head reaches.</text>',
         f'<rect x="{sx(0):.1f}" y="{sy(Y1):.1f}" width="{sx(350) - sx(0):.1f}" height="{sy(PLATE_Y[0]) - sy(Y1):.1f}" '
         f'fill="#f3ead8" stroke="#b9a37a"/>']
    poly = [(X0, mesh_min[1])] + [(a, max(b, mesh_min[1])) for a, b in step(best)] + [(X1, mesh_min[1])]
    o.append(f'<polygon points="{pts(poly)}" fill="#e4572e" fill-opacity="0.45"/>')
    for k, h in enumerate(heads):
        c, dash = COLOURS.get(h, ("#444", "4 3"))
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o.append(f'<polyline points="{pts(step([y for _, y in lim[h]]))}" fill="none" stroke="{c}" stroke-width="3"{d}/>')
        ly = 57 - 5 * k
        o.append(f'<line x1="{sx(255):.1f}" y1="{sy(ly):.1f}" x2="{sx(270):.1f}" y2="{sy(ly):.1f}" stroke="{c}" '
                 f'stroke-width="3"{d}/><text x="{sx(272):.1f}" y="{sy(ly) + 4:.1f}" font-size="12">{h} head carried</text>')
    o.append(f'<line x1="{sx(mesh_min[0]):.1f}" y1="{sy(mesh_min[1]):.1f}" x2="{sx(350 - mesh_min[0]):.1f}" '
             f'y2="{sy(mesh_min[1]):.1f}" stroke="#222" stroke-dasharray="7 5" stroke-width="1.5"/>'
             f'<text x="{sx(200):.1f}" y="{sy(mesh_min[1]) - 6:.1f}" font-size="11" text-anchor="middle">planned mesh '
             f'front (coil), Y {mesh_min[1]:g}</text>'
             f'<text x="{sx(2):.1f}" y="{sy(PLATE_Y[0]) + 15:.1f}" font-size="11" fill="#8a7550">plate front edge, '
             f'Y {PLATE_Y[0]:g}</text>')
    for x in range(0, 351, 50):
        o.append(f'<line x1="{sx(x):.1f}" y1="{sy(Y0):.1f}" x2="{sx(x):.1f}" y2="{sy(Y0) + 5:.1f}" stroke="#333"/>'
                 f'<text x="{sx(x):.1f}" y="{sy(Y0) + 20:.1f}" text-anchor="middle">{x}</text>')
    for y in range(Y0, Y1 + 1, 10):
        o.append(f'<line x1="{L - 5}" y1="{sy(y):.1f}" x2="{L}" y2="{sy(y):.1f}" stroke="#333"/>'
                 f'<text x="{L - 9}" y="{sy(y) + 4:.1f}" text-anchor="end">{y}</text>')
    o.append(f'<line x1="{L}" y1="{sy(Y0):.1f}" x2="{sx(350):.1f}" y2="{sy(Y0):.1f}" stroke="#333"/>'
             f'<line x1="{L}" y1="{sy(Y0):.1f}" x2="{L}" y2="{sy(Y1):.1f}" stroke="#333"/>'
             f'<text x="{(L + W - R) / 2:.0f}" y="{H - 50}" text-anchor="middle">X (mm)</text>'
             f'<text x="22" y="{(T + H - B) / 2:.0f}" transform="rotate(-90 22 {(T + H - B) / 2:.0f})" '
             f'text-anchor="middle">Y (mm), front of the printer at the bottom</text>'
             f'<text x="{L}" y="{H - 22}" font-size="11" fill="#555">Coil limit = nozzle front limit '
             f'(cad/data/front_reach.json) + the Beacon y_offset; mesh from cad/klipper/beacon.cfg. '
             f'Made by cad/studies/front_reach_map.py.</text>')
    o.append('</svg>')
    return "\n".join(o) + "\n"


def build():
    data = json.load(open(DATA))
    return svg(limits(data), beacon_scan.MESH_MIN, data.get("model", "").replace(".FCStd", ""))


def main(argv):
    text = build()
    if "--check" in argv:
        ok = os.path.exists(OUT) and open(OUT).read() == text
        print("front_reach_map: OK" if ok else "front_reach_map: STALE: run python3 cad/studies/front_reach_map.py")
        return 0 if ok else 1
    with open(OUT, "w") as f:
        f.write(text)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
