#!/usr/bin/env python3
"""Where on the bed's front edge can a fixed Mellow MultiHead Zero sit, so both heads reach all four sides of its ball?
(vt350#291)

    python3 cad/studies/mellow_edge_reach.py [front_reach json]     # plain python, reads the measured reach, ~1 s

The owner wants to try the Mellow back on the bed's front edge (lite-61's spot) but lower: Nudge's INSTRUCTIONS.md puts
a fixed mount's probe top about 1 mm above the print surface. tools_calibrate probes the ball from the front, back,
left and right, so each head's nozzle must get OVERTRAVEL past the ball's centre on each side:
  - lower_z 0.2 (madmax/tc_offset_calibration_macros.cfg) touches a D 10 ball where it is 1.4 mm in radius; with the
    nozzle tip (~0.5 radius) contact is ~1.9 from the axis, and sample_retract_dist 3 backs off to ~4.9: so 5 mm;
  - Nudge's own table asks for at least 6 mm.
The reach is cad/data/front_reach_front17.json (front +17, Beacon y_offset 15; 2 mm bisection, X every ~10 mm), both
heads, the worst row within one X step (front_reach_map.nozzle_limit), so it is conservative between samples.
Ball centre Y: -9.5 puts the D 13 bushing 0.5 mm in front of the plate's front edge (printer Y -2.5); lite-61 had -12.5.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import front_reach_map as frm  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(HERE)), "cad", "data", "front_reach_front17.json")
BALL_YS = (-9.5, -11.0, -12.5)
OVERTRAVELS = (5.0, 6.0)


def approach_points(bx, by, o):
    """The nozzle's furthest points probing a ball at (bx, by): front, left, right, back."""
    return [(bx, by - o), (bx - o, by), (bx + o, by), (bx, by + o)]


def margin(limit, bx, by, o):
    """The smallest distance (mm) any approach point is behind the nozzle front limit; negative = unreachable."""
    return min(y - limit(x) for x, y in approach_points(bx, by, o))


def windows(limit, by, o, xs=range(4, 347)):
    """[(x_from, x_to, best margin)] of ball X where every approach point is reachable."""
    out = []
    for bx in xs:
        mg = margin(limit, bx, by, o)
        if mg < 0: continue
        if out and bx == out[-1][1] + 1: out[-1] = (out[-1][0], bx, max(out[-1][2], round(mg, 2)))
        else: out.append((bx, bx, round(mg, 2)))
    return out


def both_heads(data, mapping=None):
    lim, dy = frm.limits(data, mapping), data["beacon_dy"]
    return lambda x: max(frm.nozzle_limit(lim[h], dy, x) for h in lim)


def main(argv):
    data = json.load(open(argv[0] if argv else DATA))
    limit = both_heads(data)
    print(f"mellow_edge_reach: {data['model']}, front stretch {data['stretch'][0]}, Beacon y_offset {data['beacon_dy']}")
    for by in BALL_YS:
        for o in OVERTRAVELS:
            w = windows(limit, by, o)
            txt = ", ".join(f"X {a}..{b} (margin {m})" for a, b, m in w) or "nowhere"
            print(f"  ball centre Y {by:6.1f}, overtravel {o}: {txt}")
    print(f"  lite-61's spot (175, -12.5), overtravel 5: margin {margin(limit, 175, -12.5, 5.0):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
