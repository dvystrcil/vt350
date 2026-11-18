#!/usr/bin/env python3
"""Add a camera framed on everything in an export to its scene.json (vt350#220 AC2), so render.py renders the same
parts the viewer shows, from a view the viewer page can match.

    python3 platform/viewer/frame_view.py <export dir> [--name NAME] [--from DX,DY,DZ] [--lens MM] [--fill F]

Reads every bucket's binary STL (model mm) for the box, then writes scene.json "views": [{name, pos, look, lens_mm}]
(render.py renders exactly those, key-lit) and "frame": {"bbox", "view"} for the page. The camera looks at the box
centre from the direction --from (default 3/4 front-right, from above, as render.py's "outside" view) at the
distance where the box's bounding sphere fills --fill (default 0.9) of the narrower field of view of a 16:9 frame.
Stdlib only.
"""
import json, math, os, struct, sys

SENSOR_W = 36.0                                      # render.py's add_cam: lens_mm on a 36 mm wide sensor, 16:9


def stl_bbox(fn):
    with open(fn, "rb") as f:
        f.seek(80); n = struct.unpack("<I", f.read(4))[0]
        lo, hi = [math.inf] * 3, [-math.inf] * 3
        for _ in range(n):
            rec = f.read(50)
            for k in range(3):
                x, y, z = struct.unpack_from("<3f", rec, 12 + 12 * k)
                for i, v in enumerate((x, y, z)):
                    if v < lo[i]: lo[i] = v
                    if v > hi[i]: hi[i] = v
    return lo + hi


def union(boxes):
    boxes = [b for b in boxes if b[0] <= b[3]]
    return [min(b[i] for b in boxes) for i in range(3)] + [max(b[i] for b in boxes) for i in range(3, 6)]


def frame(bbox, direction, lens_mm, fill=0.9, aspect=16 / 9):
    """-> (pos, look): the camera at look + unit(direction) * d, d so the box's bounding sphere fills `fill` of the
    vertical field of view (the narrower one at 16:9)."""
    c = [(bbox[i] + bbox[i + 3]) / 2 for i in range(3)]
    r = math.dist(bbox[:3], bbox[3:]) / 2
    hfov = 2 * math.atan(SENSOR_W / 2 / lens_mm)
    vfov = 2 * math.atan(math.tan(hfov / 2) / aspect)
    d = r / math.sin(vfov / 2 * fill)
    n = math.sqrt(sum(v * v for v in direction))
    return [c[i] + direction[i] / n * d for i in range(3)], c


def main(argv):
    opts, args = {}, []
    it = iter(argv)
    for a in it:
        if a.startswith("--"): opts[a[2:]] = next(it)
        else: args.append(a)
    if len(args) != 1: sys.exit(__doc__)
    exp = args[0]
    sj = os.path.join(exp, "scene.json"); scene = json.load(open(sj, encoding="utf-8"))
    boxes = [stl_bbox(os.path.join(exp, k + ".stl")) for k in scene["buckets"] if os.path.exists(os.path.join(exp, k + ".stl"))]
    bb = union(boxes)
    direction = [float(v) for v in opts.get("from", "725,-1715,850").split(",")]   # render.py "outside": cam - look
    lens = float(opts.get("lens", 35)); name = opts.get("name", "compare")
    pos, look = frame(bb, direction, lens, float(opts.get("fill", 0.9)))
    view = {"name": name, "pos": [round(v, 3) for v in pos], "look": [round(v, 3) for v in look], "lens_mm": lens}
    scene["views"] = [view]; scene["frame"] = {"bbox": [round(v, 3) for v in bb], "view": view}
    json.dump(scene, open(sj, "w", encoding="utf-8"), indent=1)
    print(json.dumps(scene["frame"]))
    print("frame-view: OK")


if __name__ == "__main__":
    main(sys.argv[1:])
