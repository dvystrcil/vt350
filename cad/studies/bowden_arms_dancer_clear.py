# vt350#312: does the dancer route clear the printer? Headless, read-only, never saves:
#   VT350_REPO=$PWD $APP freecadcmd $PWD/cad/studies/bowden_arms_dancer_clear.py     (VT350_MODEL; default lite-80)
# Log: $VT350_WORK/logs/bowden_arms_dancer_clear.log (+ .json). Its verdict lines: "T<n> dancer: clear" (or NOT clear),
# "tools apart: clear", and "dancer route: clear" at the end.
#
# The route comes from bowden_arms_dancer.py (cad/data/bowden_arms_dancer.json + _shapes.json: EI 2000, the weight
# DANCER_W, default 0.2 N). Per tool, over the pulley heights the walk actually uses (its rear spans solved every 10 mm
# of pulley height, from just above the highest to just below the lowest):
#   - the bundle: the exit channel + exit leg, and the return leg + return channel + the free run to the loop (arm
#     up and down), as tubes of the bundle's half width (BUNDLE_R), the legs down to the pulley's lowest point;
#   - the sheave: a disc of R RP + BUNDLE_R + RIM, SHEAVE_T thick (axis along Y), swept over its whole travel.
# Checked against:
#   - every fixed solid (not the moving groups; not the bundles themselves: they re-route; not sweep_toolhead's
#     exclusions), exact distToShape for each solid within NEAR;
#   - the moving envelope from bowden_arms_rear_space.py's last run (cad/data/logs/bowden_arms_rear_space.json: the
#     gantry, the carriage + heads at the rear stop, the bed's rear parts over their Z travel), at today's height and
#     #243's +10.3, as boxes (conservative);
#   - each other: the active tool's whole travel against every other tool at its parked pulley height.
# Not modelled: the arms and the head spans (bowden_arms.py and bowden_arms_reach.py check those), the sheave's mount.
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE] + [p for p in (os.path.join(os.path.dirname(os.path.dirname(HERE)), d)
                                     for d in ("cad/scripts", "platform/freecad")) if os.path.isdir(p)]

MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-80.FCStd")
DATA = os.path.join(os.path.dirname(HERE), "data")
W = os.environ.get("DANCER_W", "0.2")
BUNDLE_R = 4.6                     # half the bundle's width (PTFE 4 + O2S cable 5.1 side by side, 9.2)
RIM, SHEAVE_T = 2.0, 10.0          # the flange beyond the bundle; thickness (the bundle on edge, 5.1, + 2 x 2.45)
NEAR, CLEAR = 5.0, 1.0
BUNDLE = ("Bowden ", "O2S USB cable", "Zip tie, black (2.5 mm) slot")


def main(p):
    import tempfile
    import FreeCAD, Part
    import sweep_toolhead
    from litelib import _t_dist, _Err
    V = FreeCAD.Vector
    d = json.load(open(os.path.join(DATA, "bowden_arms_dancer.json")))
    shapes = json.load(open(os.path.join(DATA, "bowden_arms_dancer_shapes.json")))
    env = json.load(open(os.path.join(DATA, "logs", "bowden_arms_rear_space.json")))["envelope"]
    RP = d["RP"]
    p.log(f"model {MODEL} (read-only); route from bowden_arms_dancer.py, EI 2000, dancer weight {W} N; sheave R "
          f"{RP + BUNDLE_R + RIM:.1f} x {SHEAVE_T}; bundle tube R {BUNDLE_R}")
    pr = p.open(MODEL)
    sweep_toolhead.MODEL = MODEL
    with tempfile.TemporaryDirectory(prefix="dancer-clear-") as td:
        sweep_toolhead.plan(os.path.join(td, "plan.json"))
        plan = json.load(open(os.path.join(td, "plan.json")))
    moving = set(plan["bed"]) | set(plan["gantry"]) | set(plan["carriage"]) | set(plan["belt"]) \
        | set(plan["heads"]["Left"]) | set(plan["heads"]["Right"])
    skip = moving | set(plan["exclude"])
    lab = {o.Name: o.Label for o in pr.leaves}
    fixed = {o.Name: pr.shapes[o.Name] for o in pr.leaves
             if o.Name not in skip and not o.Label.startswith(BUNDLE) and pr.shapes[o.Name] is not None
             and not pr.shapes[o.Name].isNull()}
    p.log(f"fixed solids {len(fixed)}")

    def tube(X):
        out = []
        for a, b in zip(X[:-1], X[1:]):
            va, vb = V(*a), V(*b); L = (vb - va).Length
            if L > 1e-6: out.append(Part.makeCylinder(BUNDLE_R, L, va, (vb - va) * (1.0 / L)))
            out.append(Part.makeSphere(BUNDLE_R, vb))
        return out

    def route_at(sh, s, z_leg, z_sheave_lo, z_sheave_hi):
        """The tool's bundle with its legs down to z_leg (both arm positions' free runs) + its sheave swept between."""
        cx, y = d["pulley"][str(s)]
        k = min((k for k in sh["rear"] if sh["rear"][k] is not None), key=lambda k: abs(float(k) - z_leg))
        parts = []
        for X in sh["rear"][k] + [sh["rear_up"][k][1]]:
            parts += tube(X)
        R = RP + BUNDLE_R + RIM
        cyl = lambda z: Part.makeCylinder(R, SHEAVE_T, V(cx, y - SHEAVE_T / 2, z), V(0, 1, 0))
        sheave = cyl(z_sheave_lo)
        if z_sheave_hi - z_sheave_lo > 0.01:
            sheave = sheave.fuse([cyl(z_sheave_hi), Part.makeBox(2 * R, SHEAVE_T, z_sheave_hi - z_sheave_lo,
                                                                 V(cx - R, y - SHEAVE_T / 2, z_sheave_lo))]).removeSplitter()
        return Part.makeCompound(parts + [sheave])

    routes, parked, travel = {}, {}, {}
    for s in range(1, 6):
        key = f"T{s - 1}|{W}"
        if key not in shapes: raise RuntimeError(f"no shapes for {key} in bowden_arms_dancer_shapes.json")
        sh = shapes[key]
        zc = [z for z in sh["zc"] if z is not None] + [sh["zc_parked"]]
        lo, hi = min(zc), max(zc)
        routes[s] = route_at(sh, s, lo, lo, hi)                 # active: legs to the lowest, sheave over its travel
        parked[s] = route_at(sh, s, sh["zc_parked"], sh["zc_parked"], sh["zc_parked"])
        travel[s] = (lo, hi, sh["zc_parked"])
        b = routes[s].BoundBox
        p.log(f"T{s - 1}: pulley centre X {d['pulley'][str(s)][0]}, plane Y {d['pulley'][str(s)][1]}, Z {lo:.0f}..{hi:.0f} "
              f"(parked {sh['zc_parked']:.0f}); route box X {b.XMin:.0f}..{b.XMax:.0f}, Y {b.YMin:.0f}..{b.YMax:.0f}, "
              f"Z {b.ZMin:.0f}..{b.ZMax:.0f}")

    def near_fixed(shape):
        bb = shape.BoundBox; bb.enlarge(NEAR)
        names = [n for n, s in fixed.items() if s.BoundBox.isValid() and s.BoundBox.intersect(bb)]
        ds = p.map(_t_dist, [(shape, fixed[n]) for n in names])
        bad = [(n, x.msg) for n, x in zip(names, ds) if isinstance(x, _Err)]
        if bad: raise RuntimeError(f"distToShape failed: {bad[:3]}")
        return sorted(((round(x, 2), lab.get(n, n)) for n, x in zip(names, ds) if x < NEAR), key=lambda t: t[0])

    def near_moving(shape, rname):
        out = []
        for what, (x0, x1, y0, y1, z0, z1) in env[rname]:
            bb = FreeCAD.BoundBox(x0, y0, z0, x1, y1, z1); sb = shape.BoundBox; sb.enlarge(NEAR)
            if not sb.intersect(bb): continue
            box = Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
            g = shape.distToShape(box)[0]
            if g < NEAR: out.append((round(g, 2), what))
        return sorted(out)

    result, allok = {}, True
    for s, shape in routes.items():
        nf = near_fixed(shape)
        nm = {r: near_moving(shape, r) for r in env}
        worst = min([g for g, _ in nf] + [g for r in nm for g, _ in nm[r]] + [float("inf")])
        ok = worst >= CLEAR; allok &= ok
        p.check(ok, f"T{s - 1} dancer: {'clear' if ok else 'NOT clear'} (smallest gap {worst:.2f}, needs >= {CLEAR}; "
                    f"pulley Z {travel[s][0]:.0f}..{travel[s][1]:.0f})")
        for g, what in nf: p.log(f"      {g:7.2f}  {what}")
        for r in nm:
            for g, what in nm[r]: p.log(f"      {g:7.2f}  moving ({r}): {what} (box, conservative)")
        if not nf and not any(nm.values()): p.log(f"      nothing within {NEAR}")
        result[s] = dict(ok=ok, worst=worst, fixed=nf, moving=nm, travel=travel[s])
    pairs = []
    for a in routes:                    # the active tool's whole travel against every other tool parked
        for b in routes:
            if b == a: continue
            g = routes[a].distToShape(parked[b])[0]
            pairs.append((round(g, 2), f"T{a - 1} active, T{b - 1} parked"))
    pairs.sort()
    ok = pairs[0][0] >= CLEAR; allok &= ok
    p.check(ok, f"tools apart: {'clear' if ok else 'NOT clear'} (closest {pairs[0][1]} {pairs[0][0]:.2f}; the active "
                f"tool's whole travel against the others parked)")
    for g, what in pairs: p.log(f"      {g:7.2f}  {what}")
    p.log(f"dancer route: {'clear' if allok else 'NOT clear'}")
    p.dump(dict(model=MODEL, weight=W, result=result, pairs=pairs))
    p.finish([])
    if not p.errs: p.log("bowden_arms_dancer_clear: done (read-only, nothing saved)")


if __name__ in ("__main__", "bowden_arms_dancer_clear") and "FreeCAD" in sys.modules:
    import litelib
    litelib.Pass("bowden_arms_dancer_clear").run(main)
