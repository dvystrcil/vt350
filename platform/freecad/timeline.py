"""Turn a kalisim move timeline into frames of model group translations, for a FreeCAD or Blender player (vt350#135).

    python3 platform/freecad/timeline.py --timeline toolchange_timeline.jsonl --rig rig.json --fps 30   # sampled
    python3 platform/freecad/timeline.py --timeline toolchange_timeline.jsonl --rig rig.json --moves    # move ends

Prints one JSON object per frame:
    {"t": 1.25, "seq": 17, "pos": [x, y, z], "carried": "Left" | null, "groups": {"carriage": [dx, dy, dz], ...}}
t is seconds from the first position (each move at its commanded speed, no acceleration, so timing is approximate;
the path is exact, since every planned move is a straight line). pos is printer X/Y/Z. groups are translations
from the model's saved pose, in model coordinates.

The rig (JSON) describes a machine whose carriage rides a gantry, with a bed that moves in Z and tool heads that
wait in docks and ride the carriage:
    xy              {"origin_model_xy": [x, y], "sign_xy": [sx, sy]}: printer = sign * (model - origin)
    bed             {"group": name, "top_dz": dz}: the bed's dZ at printer Z 0; printer Z+ moves the bed down
    gantry_groups   names that move in Y with the carriage (the gantry, the belt runs on it)
    carriage_group  name
    reference_head  the head whose offsets place the carriage when it carries none
    heads           {name: {"group", "nozzle": docked nozzle tip (model), "pickup": carriage offset from its saved
                    pose when it picks this head up (model), "dock": the docked nozzle point (printer XY),
                    "into": the direction the carriage moves to push into the dock (printer XY, unit)}}
A head couples when the carriage passes its dock point moving "into" the dock, and uncouples when it passes it
moving out. The timeline's "tool" field isn't used: Kalico switches extruders before the pickup moves, so it names
the next head while the carriage is still empty.

Generic: no printer's labels or numbers. Plain python3, standard library only.
"""
import argparse
import json
import math
import sys

TOL = 0.01          # mm: how close to a dock's line the carriage must pass to couple
DECIMALS = 6


def to_model(rig, x, y):
    """Printer XY -> model XY (the nozzle tip of a carried head)."""
    (ox, oy), (sx, sy) = rig["xy"]["origin_model_xy"], rig["xy"]["sign_xy"]
    return (ox + sx * x, oy + sy * y)


def groups(rig, pos, carried):
    """{group: (dx, dy, dz)}: every moving group's translation with the nozzle at printer pos and head carried."""
    mx, my = to_model(rig, pos[0], pos[1])
    h = rig["heads"][carried or rig["reference_head"]]
    (nx, ny, _), (tx, ty, tz) = h["nozzle"], h["pickup"]
    tc = (mx - nx + tx, my - ny + ty, 0.0)
    out = {rig["carriage_group"]: tc}
    out.update({g: (0.0, tc[1], 0.0) for g in rig["gantry_groups"]})
    out[rig["bed"]["group"]] = (0.0, 0.0, rig["bed"]["top_dz"] - pos[2])
    for name, head in rig["heads"].items():
        out[head["group"]] = (mx - nx, my - ny, -tz) if name == carried else (0.0, 0.0, 0.0)
    return out


def _crossings(rig, a, b):
    """[(fraction along a->b, head, +1 into / -1 out of its dock)] where the segment crosses a dock point."""
    out = []
    for name, h in rig["heads"].items():
        (dx, dy), (ix, iy) = h["dock"], h["into"]
        s0 = (a[0] - dx) * ix + (a[1] - dy) * iy          # how far past the dock point, along "into"
        s1 = (b[0] - dx) * ix + (b[1] - dy) * iy
        side0 = (a[0] - dx) * -iy + (a[1] - dy) * ix      # how far off the dock's line
        side1 = (b[0] - dx) * -iy + (b[1] - dy) * ix
        if abs(side0) > TOL or abs(side1) > TOL:
            continue
        if s0 <= 0 < s1:
            out.append((-s0 / (s1 - s0), name, 1))
        elif s1 < 0 <= s0:
            out.append((s0 / (s0 - s1), name, -1))
    return sorted(out)


def _lerp(a, b, f):
    return [a[i] + (b[i] - a[i]) * f for i in range(3)]


def segments(rig, records, carried=None):
    """Straight segments with which head rides the carriage: [{"seq", "start", "end", "carried", "duration"}].
    A move that crosses a dock point is split there."""
    out, pos = [], None
    for r in records:
        new = [float(v) for v in r["pos"][:3]]
        if r["kind"] == "set_position":
            pos = new
            continue
        if pos is None:
            raise ValueError(f"seq {r['seq']}: a move before any position")
        cuts = [(0.0, None, 0)] + _crossings(rig, pos, new) + [(1.0, None, 0)]
        for (f0, _, _), (f1, name, way) in zip(cuts, cuts[1:]):
            a, b = _lerp(pos, new, f0), (new if f1 == 1.0 else _lerp(pos, new, f1))
            if f1 > f0:
                out.append({"seq": r["seq"], "start": a, "end": b, "carried": carried,
                            "duration": math.dist(a, b) / r["speed"]})
            if way == 1:
                if carried is not None:
                    raise ValueError(f"seq {r['seq']}: the carriage reaches {name}'s dock but already carries {carried}")
                carried = name
            elif way == -1 and carried == name:
                carried = None
        pos = new
    return out


def _frame(rig, t, seq, pos, carried):
    r = lambda v: round(v, DECIMALS) + 0.0                # +0.0: no "-0.0" in the output
    return {"t": r(t), "seq": seq, "pos": [r(v) for v in pos], "carried": carried,
            "groups": {g: [r(v) for v in d] for g, d in groups(rig, pos, carried).items()}}


def frames(rig, records, fps=None, carried=None):
    """fps=None: the start and every segment's end. Otherwise frames every 1/fps s, plus the last position."""
    segs = segments(rig, records, carried)
    if not segs:                                          # positions only: show the last one
        last = [r for r in records if r["kind"] == "set_position"]
        return [_frame(rig, 0.0, last[-1]["seq"], [float(v) for v in last[-1]["pos"][:3]], carried)] if last else []
    # the start frame belongs to the last record before the first move (segments() refuses a move with none)
    before = [r["seq"] for r in records if r["seq"] < segs[0]["seq"]]
    out = [_frame(rig, 0.0, before[-1], segs[0]["start"], segs[0]["carried"])]
    t0 = 0.0
    if fps is None:
        for s in segs:
            t0 += s["duration"]
            out.append(_frame(rig, t0, s["seq"], s["end"], s["carried"]))
        return out
    k = 1
    for s in segs:
        while k / fps <= t0 + s["duration"] + 1e-9:
            f = (k / fps - t0) / s["duration"] if s["duration"] else 1.0
            out.append(_frame(rig, k / fps, s["seq"], _lerp(s["start"], s["end"], min(f, 1.0)), s["carried"]))
            k += 1
        t0 += s["duration"]
    if out[-1]["t"] < round(t0, DECIMALS) - 1e-9:
        out.append(_frame(rig, t0, segs[-1]["seq"], segs[-1]["end"], segs[-1]["carried"]))
    return out


def main(argv):
    ap = argparse.ArgumentParser(prog="timeline", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--timeline", required=True, help="kalisim timeline (JSONL)")
    ap.add_argument("--rig", required=True, help="the machine's rig file (JSON)")
    how = ap.add_mutually_exclusive_group(required=True)
    how.add_argument("--fps", type=float, help="frames per second")
    how.add_argument("--moves", action="store_true", help="one frame per move end")
    ap.add_argument("--carried", default=None, help="the head on the carriage at the start (default: none)")
    a = ap.parse_args(argv)
    with open(a.rig) as f:
        rig = json.load(f)
    with open(a.timeline) as f:
        records = [json.loads(l) for l in f if l.strip()]
    return [json.dumps(fr) for fr in frames(rig, records, None if a.moves else a.fps, a.carried)]


if __name__ == "__main__":
    print("\n".join(main(sys.argv[1:])))
