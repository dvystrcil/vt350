#!/usr/bin/env python3
"""Draw the bed plate, the 350 print square and the area the carried nozzle can reach (#67).

Reads the reach from sweep_toolhead.py's log and the plate constants from sweep_toolhead.py itself, so the
drawing follows the model: re-run this after every sweep. Plain python3, no FreeCAD.

  python3 cad/studies/print_area.py [--log cad/data/logs/sweep_toolhead.log] [--out cad/data/print-area.svg]

Coordinates in the drawing are plate coordinates: the plate's front-left corner = 0,0, X to the right, Y to the
rear, viewed from above. The printable area is the reach of the TIGHTEST head on each side, clamped to the square.
"""
import argparse
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


def svg(a):
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
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size:.0f}" height="{size + 60:.0f}" '
        f'viewBox="0 0 {size:.0f} {size + 60:.0f}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="100%" height="100%" fill="#ffffff"/>',
        rect(a["plate"], fill="#d9d9d9", stroke="#555", stroke_width="1.5"),
        rect(sq, fill="#f2f2f2", stroke="#333", stroke_width="1.5", stroke_dasharray="8 5"),
        rect(ar, fill="#2e9e5b", fill_opacity="0.35", stroke="#1b6e3c", stroke_width="2"),
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
        text(M / 2, size + 40, "Generated by cad/studies/print_area.py from cad/data/logs/sweep_toolhead.log (#67). "
             "Do not edit by hand.", 12, "start", fill="#444"),
        "</svg>",
    ]
    return "\n".join(s for s in out if s) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", default=os.path.join(CAD, "data", "logs", "sweep_toolhead.log"))
    ap.add_argument("--src", default=os.path.join(HERE, "sweep_toolhead.py"))
    ap.add_argument("--out", default=os.path.join(CAD, "data", "print-area.svg"))
    args = ap.parse_args()
    with open(args.log, encoding="utf-8") as fl, open(args.src, encoding="utf-8") as fs:
        a = printable(parse_reach(fl.read()), parse_plate(fs.read()))
    with open(args.out, "w", encoding="utf-8") as fo:
        fo.write(svg(a))
    print(f'{a["model"]}: printable {a["width"]} x {a["depth"]} mm, plate coords X {a["area"][0]}..{a["area"][2]}, '
          f'Y {a["area"][1]}..{a["area"][3]}; loss vs square {a["loss"]} -> {args.out}')


if __name__ == "__main__":
    main()
