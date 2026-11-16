# Stand-ins (vt350#195 AC3): a cheap shape shown in the FreeCAD GUI in place of a part that costs seconds to
# tessellate. The real part stays in the model, hidden, and the render export draws it instead of its stand-in
# (colours.standin_skip). A hidden object is not tessellated when the GUI opens a document; a visible object under a
# hidden App::Part is (measured 2026-11-16: cad/data/logs/open_time.log, 5 "Spring v1": 14.4 s visible, 0.2 s hidden).
# Plain python3 (no FreeCAD), so it runs in CI: test_standins.py.
import math


def _circle(pts2):
    """Algebraic (Kasa) least-squares circle through 2-D points -> (cx, cy)."""
    # x^2 + y^2 + D x + E y + F = 0, linear in D, E, F: solve the 3x3 normal equations.
    A = [[0.0] * 3 for _ in range(3)]; b = [0.0] * 3
    for x, y in pts2:
        row, rhs = (x, y, 1.0), -(x * x + y * y)
        for i in range(3):
            b[i] += row[i] * rhs
            for j in range(3): A[i][j] += row[i] * row[j]
    for i in range(3):                                  # Gaussian elimination with partial pivoting
        k = max(range(i, 3), key=lambda r: abs(A[r][i]))
        A[i], A[k], b[i], b[k] = A[k], A[i], b[k], b[i]
        if abs(A[i][i]) < 1e-12: raise ValueError("degenerate points: no circle fits")
        for r in range(i + 1, 3):
            f = A[r][i] / A[i][i]
            for j in range(i, 3): A[r][j] -= f * A[i][j]
            b[r] -= f * b[i]
    s = [0.0] * 3
    for i in (2, 1, 0): s[i] = (b[i] - sum(A[i][j] * s[j] for j in range(i + 1, 3))) / A[i][i]
    return -s[0] / 2, -s[1] / 2


def fit_coil(pts):
    """Points on a coil spring's surface (its own frame, the coil along a coordinate axis) -> the tube that holds it:
    dict(axis, centre (the other two coordinates, in order), rmin, rmax, lo, hi, spread). The axis is the coordinate
    axis about which the points' radial distances spread least; for a round-wire coil the spread is the wire's
    diameter, so a large spread means the points aren't a coil about any axis (the caller checks it)."""
    best = None
    for ax in range(3):
        o = [k for k in range(3) if k != ax]
        try: cx, cy = _circle([(p[o[0]], p[o[1]]) for p in pts])
        except ValueError: continue
        rs = [math.hypot(p[o[0]] - cx, p[o[1]] - cy) for p in pts]
        fit = dict(axis=ax, centre=(cx, cy), rmin=min(rs), rmax=max(rs),
                   lo=min(p[ax] for p in pts), hi=max(p[ax] for p in pts), spread=max(rs) - min(rs))
        if best is None or fit["spread"] < best["spread"]: best = fit
    if best is None: raise ValueError("no axis fits a circle")
    return best
