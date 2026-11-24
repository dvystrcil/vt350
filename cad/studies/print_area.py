#!/usr/bin/env python3
"""Draw the bed plate, the 350 print square, the area the carried nozzle can reach (#67) and the Beacon's (#291).

Reads the reach from sweep_toolhead.py's log and the plate constants from sweep_toolhead.py itself, so the
drawing follows the model: re-run this after every sweep. Plain python3, no FreeCAD.

  python3 cad/studies/print_area.py [--log cad/data/logs/sweep_toolhead.log] [--out cad/data/print-area.svg]

Coordinates in the drawing are plate coordinates: the plate's front-left corner = 0,0, X to the right, Y to the
rear, viewed from above. The printable area is the reach of the TIGHTEST head on each side, clamped to the square.
"""
import argparse, json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
NUM = r"(-?\d+(?:\.\d+)?)"


def parse_plate(src):
    m = re.search(rf"^PLATE_X0, PLATE_Y0, PLATE_W, PRINT_W = {NUM}, {NUM}, {NUM}, {NUM}", src, re.M)
    if not m:
        raise ValueError("PLATE_X0 / PLATE_Y0 / PLATE_W / PRINT_W line not found in sweep_toolhead.py")
    return tuple(float(v) for v in m.groups())


def parse_reach(log):
    m = re.search(r"model \S*/(vt350-[\w-]+)\.FCStd", log)
    model = m.group(1) if m else "unknown model"
    y = re.findall(rf"^\S+\s+\S+ (\w+) carried: .*nozzle Y reach {NUM} \.\. {NUM}", log, re.M)
    x = re.findall(rf"^\S+\s+\S+\s+(\w+) head, (left|right) side: first nozzle X with no new overlap {NUM}", log, re.M)
    heads = sorted({h for h, *_ in y})
    xs = {(h, s): float(v) for h, s, v in x}
    if not heads or any((h, s) not in xs for h in heads for s in ("left", "right")):
        raise ValueError(f"sweep log incomplete: Y reach for {heads}, X reach for {sorted(xs)}")
    return {
        "model": model,
        "heads": heads,
        "x_min": max(xs[h, "left"] for h in heads),
        "x_max": min(xs[h, "right"] for h in heads),
        "y_min": max(float(a) for _, a, _ in y),
        "y_max": min(float(b) for _, _, b in y),
    }


def printable(reach, plate):
    x0, y0, plate_w, print_w = plate
    inset = (plate_w - print_w) / 2
    sq = (inset, inset, inset + print_w, inset + print_w)
    r = lambda v: round(v, 2)
    area = (r(max(sq[0], reach["x_min"] - x0)), r(max(sq[1], reach["y_min"] - y0)),
            r(min(sq[2], reach["x_max"] - x0)), r(min(sq[3], reach["y_max"] - y0)))
    return {"model": reach["model"], "heads": reach["heads"], "plate": (0.0, 0.0, plate_w, plate_w), "origin": (x0, y0),
            "square": sq, "area": area, "width": r(area[2] - area[0]), "depth": r(area[3] - area[1]),
            "loss": {"left": r(area[0] - sq[0]), "right": r(sq[2] - area[2]), "front": r(area[1] - sq[1]),
                     "rear": r(sq[3] - area[3])}}


# vt350#291: the Beacon is to move to y_offset 15 (owner, 2026-11-22; lite-78's front +17 was sized for it). Until
# beacon.cfg says so, the drawing shows the coil at the planned offset and says beacon.cfg's value beside it.
PLANNED_BEACON_DY = 15.0
BEACON_CFG = os.path.join(CAD, "klipper", "beacon.cfg")
FRONT_REACH = os.path.join(CAD, "data", "front_reach_front17.json")     # per-X front reach (lite-77 + 17 = lite-78)
MAPPING = os.path.join(CAD, "klipper", "xy_mapping.json")


def parse_beacon(cfg):
    """beacon.cfg -> {dx, dy, mesh_min, mesh_max} (printer mm; offsets = coil centre less nozzle)."""
    def val(key):
        m = re.search(rf"^{key}:\s*(.+)$", cfg, re.M)
        if not m:
            raise ValueError(f"beacon.cfg: no {key}")
        return [float(v) for v in m.group(1).split("#")[0].split(",")]
    return {"dx": val("x_offset")[0], "dy": val("y_offset")[0], "mesh_min": tuple(val("mesh_min")),
            "mesh_max": tuple(val("mesh_max"))}


def beacon_area(reach, plate, beacon, front, mapping, dy=PLANNED_BEACON_DY):
    """Where the coil reaches with both heads (the worse head at each X), in plate coordinates, and the planned mesh
    against it. front: front_reach JSON (per head, per X: "clear" = the nozzle's furthest forward model Y; the file's
    beacon_dy doesn't enter, any coil offset dy is added here); reach: parse_reach (model coords, for X and the rear)."""
    (ox, oy), (gx, gy) = mapping["origin_model_xy"], mapping["sign_xy"]
    x0, y0, plate_w, _ = plate
    to_plate = lambda px, py: (round(px + ox - x0, 2), round(py + oy - y0, 2))      # printer -> plate (sign +1)
    pr = lambda mx, my: (gx * (mx - ox), gy * (my - oy))                           # model -> printer
    noz = {h: [(round(gx * (r["x"] - ox), 2), round(gy * (r["clear"] - oy), 2)) for r in rows]
           for h, rows in front["heads"].items()}
    step = max(max(b - a for (a, _), (b, _) in zip(v, v[1:])) for v in noz.values())
    def nozzle_front(x):                       # worst head, worst row within one X step (as front_reach_map)
        return max(max(y for a, y in v if abs(a - x) <= step + 1e-6) for v in noz.values())
    (nx0, _), (nx1, ny1) = pr(reach["x_min"], reach["y_min"]), pr(reach["x_max"], reach["y_max"])
    xs = sorted({nx0, nx1} | {a for v in noz.values() for a, _ in v if nx0 <= a <= nx1})
    pf, pb = to_plate(0, 0)[1] * -1, plate_w - to_plate(0, 0)[1]                    # plate front / rear in printer Y
    cfront = [(x + beacon["dx"], max(pf, nozzle_front(x) + dy)) for x in xs]
    rear = min(pb, ny1 + dy)
    poly = [to_plate(x, y) for x, y in cfront] + [to_plate(cfront[-1][0], rear), to_plate(cfront[0][0], rear)]
    (mx0, my0), (mx1, my1) = beacon["mesh_min"], beacon["mesh_max"]
    worst = max(y for x, y in cfront if mx0 - step <= x <= mx1 + step)
    r2 = lambda v: round(v, 2)
    return {"dy": dy, "cfg_dy": beacon["dy"], "poly": poly, "mesh": to_plate(mx0, my0) + to_plate(mx1, my1),
            "mesh_printer": (mx0, my0, mx1, my1),
            "margin": {"front": r2(my0 - worst), "rear": r2(rear - my1), "left": r2(mx0 - cfront[0][0]),
                       "right": r2(cfront[-1][0] - mx1)},
            "model": front.get("model", ""), "stretch": front.get("stretch")}


def svg(a, b=None):
    S, M = 2.0, 70                       # px per mm, margin px
    W = a["plate"][2]
    size = W * S + 2 * M
    px = lambda x: f"{M + x * S:.1f}"
    py = lambda y: f"{M + (W - y) * S:.1f}"          # Y to the rear = up the page

    def rect(b, **attr):
        x0, y0, x1, y1 = b
        extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attr.items())
        return f'<rect x="{px(x0)}" y="{py(y1)}" width="{(x1 - x0) * S:.1f}" height="{(y1 - y0) * S:.1f}" {extra}/>'

    def text(x, y, s, size=13, anchor="middle", weight="normal", fill="#222", rotate=None):
        tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" '
                f'fill="{fill}"{tr}>{s}</text>')

    sq, ar, loss = a["square"], a["area"], a["loss"]
    ox, oy = a["origin"]
    cx, cy = (ar[0] + ar[2]) / 2, (ar[1] + ar[3]) / 2
    f = lambda v: f"{v:g}"
    H = 60 if b is None else 100
    beacon = []
    if b is not None:
        pts = " ".join(f"{px(x)},{py(y)}" for x, y in b["poly"])
        m, mg = b["mesh"], b["margin"]
        ok = all(v >= 0 for v in mg.values())
        which = (f'planned y_offset {f(b["dy"])} (#291; beacon.cfg still {f(b["cfg_dy"])})' if b["dy"] != b["cfg_dy"]
                 else f'beacon.cfg y_offset {f(b["dy"])}')
        beacon = [
            f'<polygon points="{pts}" fill="#1f5fbf" fill-opacity="0.12" stroke="#1f5fbf" stroke-width="2"/>',
            rect(m, fill="none", stroke="#7a2fb0", stroke_width="1.8", stroke_dasharray="4 4"),
            text(float(px(cx)), float(py(cy)) + 92, f'Beacon mesh (purple dashed) {f(b["mesh_printer"][0])}, '
                 f'{f(b["mesh_printer"][1])} … {f(b["mesh_printer"][2])}, {f(b["mesh_printer"][3])} printer', 13,
                 fill="#7a2fb0"),
            text(float(px(cx)), float(py(cy)) + 112,
                 f'coil (blue) past the mesh: front {mg["front"]:g}, rear {mg["rear"]:g}, left {mg["left"]:g}, '
                 f'right {mg["right"]:g}' + ("" if ok else "  NOT REACHED"), 13,
                 fill="#1f5fbf" if ok else "#b03030", weight="bold"),
            text(M / 2, size + 40, f'Blue: where the Beacon coil reaches, both heads, {which}.', 12, "start",
                 fill="#1f5fbf"),
            text(M / 2, size + 60, f'Its front edge per X: cad/data/front_reach_front17.json ({b["model"]}, front +17). '
                 f'Purple dashed: beacon.cfg\'s mesh (coil positions).', 12, "start", fill="#1f5fbf"),
        ]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size:.0f}" height="{size + H:.0f}" '
        f'viewBox="0 0 {size:.0f} {size + H:.0f}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="100%" height="100%" fill="#ffffff"/>',
        rect(a["plate"], fill="#d9d9d9", stroke="#555", stroke_width="1.5"),
        rect(sq, fill="#f2f2f2", stroke="#333", stroke_width="1.5", stroke_dasharray="8 5"),
        rect(ar, fill="#2e9e5b", fill_opacity="0.35", stroke="#1b6e3c", stroke_width="2"),
        *beacon,
        # title + legend
        text(size / 2, 26, f'Printable area on {a["model"]} (both heads: {", ".join(a["heads"])})', 16, weight="bold"),
        text(size / 2, 46, "top view, plate coordinates: front-left plate corner = 0,0, X right, Y to the rear (mm)", 12,
             fill="#555"),
        text(float(px(W)), float(py(0)) + 18, f'grey: {f(W)} × {f(W)} plate (LDO, 10 mm)', 12, "end", fill="#444"),
        text(float(px(0)), float(py(0)) + 18, f'dashed: {f(sq[2] - sq[0])} × {f(sq[3] - sq[1])} print square', 12,
             "start", fill="#333"),
        text(float(px(cx)), float(py(cy)) - 10, f'{a["width"]:.1f} × {a["depth"]:.2f}', 22, weight="bold", fill="#1b6e3c"),
        text(float(px(cx)), float(py(cy)) + 14, "nozzle reach (printable)", 13, fill="#1b6e3c"),
        text(float(px(cx)), float(py(cy)) + 34,
             f'X {f(ar[0])} … {f(ar[2])}, Y {f(ar[1])} … {f(ar[3])}', 12, fill="#1b6e3c"),
        text(float(px(cx)), float(py(cy)) + 52,
             f'model X {f(round(ar[0] + ox, 2))} … {f(round(ar[2] + ox, 2))}, '
             f'Y {f(round(ar[1] + oy, 2))} … {f(round(ar[3] + oy, 2))}', 12, fill="#555"),
        # losses vs the print square, per side
        text(float(px(cx)), float(py(ar[3])) + 20, f'rear −{loss["rear"]:g}' if loss["rear"] else "rear 0", 13,
             weight="bold", fill="#b03030"),
        text(float(px(cx)), float(py(ar[1])) - 10, f'front −{loss["front"]:g}' if loss["front"] else "front 0", 13,
             weight="bold",
             fill="#b03030" if loss["front"] else "#555"),
        text(float(px(sq[0])) - 16, float(py(cy)), f'left −{loss["left"]:g}', 13, weight="bold", fill="#b03030",
             rotate=-90),
        text(float(px(sq[2])) + 24, float(py(cy)), f'right −{loss["right"]:g}', 13, weight="bold", fill="#b03030",
             rotate=90),
        text(size / 2, size - 26, "FRONT (door, docks)", 14, weight="bold", fill="#444"),
        text(size / 2, M - 6, "REAR", 13, weight="bold", fill="#444"),
        text(M / 2, size + 20, "Grey: plate. Dashed: 350 print square (2.5 inset). Green: where the carried nozzle "
             "reaches, tightest head per side.", 12, "start", fill="#444"),
        text(M / 2, size + (80 if b is not None else 40), "Generated by cad/studies/print_area.py from "
             "cad/data/logs/sweep_toolhead.log (#67)" + (" + the Beacon's files" if b is not None else "")
             + ". Do not edit by hand.", 12, "start", fill="#444"),
        "</svg>",
    ]
    return "\n".join(s for s in out if s) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", default=os.path.join(CAD, "data", "logs", "sweep_toolhead.log"))
    ap.add_argument("--src", default=os.path.join(HERE, "sweep_toolhead.py"))
    ap.add_argument("--out", default=os.path.join(CAD, "data", "print-area.svg"))
    ap.add_argument("--beacon", default=BEACON_CFG, help="beacon.cfg (offsets, mesh)")
    ap.add_argument("--front-reach", default=FRONT_REACH, help="per-X front reach JSON (front_reach_map.py)")
    ap.add_argument("--mapping", default=MAPPING, help="xy_mapping.json (model -> printer)")
    args = ap.parse_args()
    with open(args.log, encoding="utf-8") as fl, open(args.src, encoding="utf-8") as fs:
        reach, plate = parse_reach(fl.read()), parse_plate(fs.read())
    a = printable(reach, plate)
    b = None
    if all(os.path.isfile(p) for p in (args.beacon, args.front_reach, args.mapping)):
        with open(args.beacon, encoding="utf-8") as fb, open(args.front_reach, encoding="utf-8") as fr, \
                open(args.mapping, encoding="utf-8") as fm:
            b = beacon_area(reach, plate, parse_beacon(fb.read()), json.load(fr), json.load(fm))
    else:
        print("print_area: no beacon.cfg / front reach / mapping beside it: drawn without the Beacon")
    with open(args.out, "w", encoding="utf-8") as fo:
        fo.write(svg(a, b))
    print(f'{a["model"]}: printable {a["width"]} x {a["depth"]} mm, plate coords X {a["area"][0]}..{a["area"][2]}, '
          f'Y {a["area"][1]}..{a["area"][3]}; loss vs square {a["loss"]} -> {args.out}')


if __name__ == "__main__":
    main()
