# contact: the pure logic of the Z travel sweep (#82). No FreeCAD here, so test_contact.py runs in CI.
#
#   window(a_box, b_box, direction)       -> (lo, hi) travel that can bring moving a into fixed b, or None
#   first_contact(probe, lo, hi)           -> the first travel in [lo, hi] where probe(d) (an overlap volume) > TOL
#   search(pairs, run, cap)                -> the first contact over many pairs, pruned by the best one so far
#   line(key, value, why) / parse(log)     -> the log's "key=value (why)" limit lines, and reading them back
#
# Travel d is always >= 0, measured along `direction` (-1 = the bed moving down, +1 = up). Boxes are (xmin, ymin,
# zmin, xmax, ymax, zmax); they only bound where to look, a limit always comes from probe (a boolean common() volume
# in z_sweep.py). The scan steps STEP mm from lo, then bisects the first overlapping step down to EPS. A part thinner
# than STEP in Z could be stepped over; the thinnest in the bed's path are the 1.4 mm magnet sheet and ~1 mm washers.
import re

STEP = 0.5          # mm, scan step
EPS = 0.005         # mm, bisection stops when the clear..overlapping bracket is this narrow
TOL = 1e-3          # mm3, a common() volume above this is an overlap (litelib no_overlap's tol)
MARGIN = 0.5        # mm each box grows by before windows are taken (optimal boxes come from a triangulation)
REPORT = 10.0       # mm past the first contact that the runners-up are still listed
BATCH = 16          # pairs per round of the pruned search
DONE = "z_sweep: done (read-only, nothing saved)"
KEYS = ("z_lower_limit_mm", "z_upper_limit_mm", "print_height_mm",
        "klipper_position_max_mm", "z_negative_limit_mm", "z_travel_mm")     # the last three: #82 AC6


def window(a, b, direction, margin=MARGIN, cap=None):
    """Travel range [lo, hi] over which moving box a (going `direction` in Z) can touch fixed box b: from where the
    grown boxes first meet to where a has passed wholly beyond b. None if they never meet (no XY overlap, b on the
    other side, or lo at or past cap); hi is trimmed to cap."""
    if direction not in (-1, 1): raise ValueError(f"direction {direction!r} must be -1 or +1")
    ax0, ay0, az0, ax1, ay1, az1 = a
    bx0, by0, bz0, bx1, by1, bz1 = b
    g = 2 * margin
    if bx0 - ax1 > g or ax0 - bx1 > g or by0 - ay1 > g or ay0 - by1 > g: return None
    if direction == -1: lo, hi = az0 - bz1 - g, az1 - bz0 + g
    else: lo, hi = bz0 - az1 - g, bz1 - az0 + g
    if hi <= 0: return None
    lo = max(0.0, lo)
    if cap is not None:
        if lo >= cap: return None
        hi = min(hi, cap)
    return lo, hi


def first_contact(probe, lo, hi, step=STEP, eps=EPS, tol=TOL):
    """Scan d = lo, lo + step, ... (hi last) for probe(d) > tol, then bisect the first overlapping step.
    -> {"kind": "contact", "d": first overlapping travel found, <= eps past the touch}
       {"kind": "clear", "d": None}                         nothing in [lo, hi]
       {"kind": "start", "d": lo, "volume": v}             already overlapping at lo"""
    if step <= 0 or eps <= 0: raise ValueError(f"step {step} and eps {eps} must be > 0")
    if hi < lo: raise ValueError(f"window {lo}..{hi} is empty")
    v = probe(lo)
    if v > tol: return {"kind": "start", "d": lo, "volume": v}
    clear, i, d = lo, 0, lo
    while d < hi:
        i += 1
        d = lo + i * step
        if d >= hi: d = hi
        if probe(d) > tol:
            a, b = clear, d
            while b - a > eps:
                m = (a + b) / 2
                if probe(m) > tol: b = m
                else: a = m
            return {"kind": "contact", "d": b}
        clear = d
    return {"kind": "clear", "d": None}


def search(pairs, run, cap, report=REPORT, batch=BATCH):
    """pairs [(key, lo, hi)]; run([(key, lo, hi), ...]) -> [first_contact result, ...] in the same order (z_sweep
    runs a batch through Pass.map). Pairs go in order of lo, `batch` at a time; once a contact is known, a pair whose
    window starts past best + report is never run, and windows are trimmed to it. A pair already overlapping at
    travel 0 is a fit (a nut on its screw), not a limit. -> {best: (d, key) | None, contacts: [(d, key)] within
    report of best, by d, fits: [(key, volume)], runs: pairs run}"""
    order = sorted(pairs, key=lambda p: p[1])
    best, contacts, fits, runs, i = None, [], [], 0, 0
    while i < len(order):
        limit = cap if best is None else min(cap, best[0] + report)
        chunk = []
        while i < len(order) and len(chunk) < batch and order[i][1] < limit:
            k, lo, hi = order[i]
            chunk.append((k, lo, min(hi, limit))); i += 1
        if not chunk: break
        res = run(chunk)
        if len(res) != len(chunk): raise RuntimeError(f"run answered {len(res)} of {len(chunk)} pairs")
        for (k, lo, _), r in zip(chunk, res):
            runs += 1
            if r["kind"] == "start":
                if lo > 0: raise RuntimeError(f"{k}: overlaps at the start of its window (travel {lo}): the box "
                                              "prefilter is not conservative")
                fits.append((k, r["volume"]))
            elif r["kind"] == "contact":
                contacts.append((r["d"], k))
                if best is None or r["d"] < best[0]: best = (r["d"], k)
    if best is not None: contacts = sorted((c for c in contacts if c[0] <= best[0] + report), key=lambda c: c[0])
    return {"best": best, "contacts": contacts, "fits": fits, "runs": runs}


def line(key, value, why=None):
    return f"{key}={value:.2f}" + (f" ({why})" if why else "")


def parse(log, keys=KEYS):
    """The last value of each of keys in a finished z_sweep log -> {key: float}. keys=KEYS[:3] reads a log from
    before the full-travel lines."""
    if not any(l.endswith(DONE) for l in log.splitlines()): raise ValueError(f"z_sweep log not finished: no {DONE!r} line")
    out = {}
    for k in keys:
        m = re.findall(rf"\b{k}=(-?\d+(?:\.\d+)?)", log)
        if not m: raise ValueError(f"z_sweep log has no {k}=")
        out[k] = float(m[-1])
    return out
