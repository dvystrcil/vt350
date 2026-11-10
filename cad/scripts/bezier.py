# bezier: the bowden tube's route curve (#6). No FreeCAD here, so test_bezier.py runs in CI.
#
#   tube_poles(P0, P1, ED, a, b)          -> the 4 poles: inlet P0, P0 + a straight up, P1 - b * ED, exit P1
#   radius_at(poles, u) / min_radius(poles, n)   -> bend radius at u in [0, 1] / the smallest over n + 1 samples
#   ranked_handles(P0, P1, ED, as_, bs)   -> every grid pair as (a, b, radius), largest smallest radius first
#   best_handles(P0, P1, ED, as_, bs)     -> the first of those
#
# It is the curve the lite-N passes build with Part.BezierCurve (lite-5, lite-10, lite-23): the tube leaves the inlet
# vertically and arrives at the exit along ExitDir, then runs straight on (Beyond). lite-10 picked the handles for the
# largest bend radius; best_handles is that search. The radius is 1 / curvature, |B' x B''| / |B'|^3, sampled.
import math


def tube_poles(P0, P1, ED, a, b):
    return [tuple(P0), (P0[0], P0[1], P0[2] + a), tuple(P1[i] - ED[i] * b for i in range(3)), tuple(P1)]


def _d(poles, u):
    p0, p1, p2, p3 = poles; v = 1 - u
    d1 = [3 * (v * v * (p1[i] - p0[i]) + 2 * u * v * (p2[i] - p1[i]) + u * u * (p3[i] - p2[i])) for i in range(3)]
    d2 = [6 * (v * (p2[i] - 2 * p1[i] + p0[i]) + u * (p3[i] - 2 * p2[i] + p1[i])) for i in range(3)]
    return d1, d2


def radius_at(poles, u):
    d1, d2 = _d(poles, u)
    c = [d1[1] * d2[2] - d1[2] * d2[1], d1[2] * d2[0] - d1[0] * d2[2], d1[0] * d2[1] - d1[1] * d2[0]]
    num = math.sqrt(sum(x * x for x in c)); sp = math.sqrt(sum(x * x for x in d1))
    return math.inf if num == 0 else sp ** 3 / num


def min_radius(poles, n=400):
    return min(radius_at(poles, i / n) for i in range(n + 1))


def ranked_handles(P0, P1, ED, as_, bs, n=400):
    """[(a, b, radius)] for every pair on the grid, largest radius first (ties keep grid order)"""
    if not as_ or not bs: raise ValueError("empty handle grid")
    out = [(a, b, min_radius(tube_poles(P0, P1, ED, a, b), n)) for a in as_ for b in bs]
    return sorted(out, key=lambda x: -x[2])


def best_handles(P0, P1, ED, as_, bs, n=400):
    return ranked_handles(P0, P1, ED, as_, bs, n)[0]
