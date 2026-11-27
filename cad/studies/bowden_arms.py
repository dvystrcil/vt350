# vt350#312 AC2: do the per-tool bowden arms clear the printer? Headless, read-only, never saves:
#   $APP freecadcmd $PWD/cad/studies/bowden_arms.py          (VT350_MODEL to pick a model; default lite-80)
# Log: $VT350_WORK/logs/bowden_arms.log (+ bowden_arms.json). Its verdict lines: "arms up: clear" (or NOT clear), and
# "arm N down: clear" for each arm lowered on its own, each part within 5 mm listed with its gap.
#
# The arms come from AC1's design (cad/data/bowden_arms_design.json, written by bowden_arms_reach.py): a hinge on
# the rear top 4040, one arm per slot in the plane of its bundle, a loop at the free end. Modelled here as:
#   - the arm: a bar ARM_W wide (X) x 2 * ARM_HALF deep, from the hinge axis to the loop, beside its bundle (its
#     centre ARM_SIDE in X from the bundle, so the bar itself never sits under the bundle);
#   - the loop: a ring around the bundle (outer LOOP_R, inner LOOP_IN, LOOP_LEN long, axis along Y), joined to the bar;
#   - the cam: an envelope only (its lobes as a cylinder of CAM_R on one shaft along X, under the arms CAM_AT from the
#     hinge, touching the raised arm's underside). The cam's real shape, its stepper and the hinge brackets are #312's
#     next step if the owner takes it on; they are not checked here.
# Checked against:
#   - every fixed solid (not the bed, gantry, carriage or heads, which move; not the bundles themselves: the "Bowden *"
#     tubes, "O2S USB cable *" and their zip ties, which the arms carry and re-route; not sweep_toolhead's exclusions).
#     Exact distToShape for each solid whose box comes within 5 mm of an arm;
#   - what moves in XY, swept: the gantry at its rear stop (sweep_toolhead.Y_TRAVEL), and the carriage + carried head
#     at the rear stop, as one box over their whole X travel (conservative). At today's gantry height and #243's
#     +10.3 mm.
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE] + [p for p in (os.path.join(os.path.dirname(os.path.dirname(HERE)), d)
                                     for d in ("cad/scripts", "platform/freecad")) if os.path.isdir(p)]

MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-80.FCStd")
DESIGN = os.environ.get("BOWDEN_ARMS_DESIGN", os.path.join(os.path.dirname(HERE), "data", "bowden_arms_design.json"))
EXIT_X = {1: -409.7, 2: -324.54, 3: -248.42, 4: -156.42, 5: -80.3}   # lanyard/lrod.py (lite70_roof_exit_low.json)
ARM_W, ARM_HALF, ARM_SIDE = 8.0, 6.0, -12.0
LOOP_R, LOOP_IN, LOOP_LEN = 14.0, 10.0, 10.0
CAM_R, CAM_AT = 16.0, 40.0
NEAR = 5.0                       # list every part this close
CLEAR = 1.0                      # "clear" = every gap at least this
RAISE = {"lite-80": 0.0}           # the model is lite-80: the gantry is already at #243's +10
BUNDLE = ("Bowden ", "O2S USB cable slot", "Zip tie, black (2.5 mm) slot")


def arm_solids(V, Part, design, slot, loop):
    """The arm bar (hinge -> loop) and the loop ring, for the loop at (Y, Z)."""
    import FreeCAD
    hy, hz = design["hinge"]; ly, lz = loop
    x = EXIT_X[slot]
    u = V(0, ly - hy, lz - hz); L = u.Length; u.normalize()
    bar = Part.makeBox(L, ARM_W, 2 * ARM_HALF, V(0, -ARM_W / 2, -ARM_HALF))
    m = FreeCAD.Matrix(0, 1, 0, x + ARM_SIDE,
                       u.y, 0, u.z, hy,
                       u.z, 0, -u.y, hz,
                       0, 0, 0, 1)
    bar = bar.transformGeometry(m)
    ring = Part.makeCylinder(LOOP_R, LOOP_LEN, V(x, ly - LOOP_LEN / 2, lz), V(0, 1, 0)).cut(
        Part.makeCylinder(LOOP_IN, LOOP_LEN, V(x, ly - LOOP_LEN / 2, lz), V(0, 1, 0)))
    web = Part.makeBox(abs(ARM_SIDE), LOOP_LEN, 2 * ARM_HALF, V(x + ARM_SIDE, ly - LOOP_LEN / 2, lz - ARM_HALF))
    return bar.fuse([web, ring]).removeSplitter()


def cam_envelope(V, Part, design):
    """One cylinder over every slot, under the raised arms CAM_AT from the hinge, touching their underside."""
    hy, hz = design["hinge"]; uy, uz = design["loop_up"]
    import math
    L = math.hypot(uy - hy, uz - hz)
    y = hy + (uy - hy) * CAM_AT / L
    z = hz + (uz - hz) * CAM_AT / L - ARM_HALF - CAM_R
    x0 = min(EXIT_X.values()) + ARM_SIDE - ARM_W
    x1 = max(EXIT_X.values()) + ARM_SIDE + ARM_W
    return Part.makeCylinder(CAM_R, x1 - x0, V(x0, y, z), V(1, 0, 0))


def main(p):
    import json, tempfile
    import FreeCAD, Part
    import sweep_toolhead
    from litelib import _t_dist, _Err
    V = FreeCAD.Vector
    design = json.load(open(DESIGN))["design"]
    p.log(f"model {MODEL} (read-only)")
    p.log(f"design (bowden_arms_reach.py): {design['name']}; hinge (Y, Z) {design['hinge']}, arm {design['arm']}, "
          f"loop up {design['loop_up']}, down {design['loop_down']}")
    p.log(f"arm {ARM_W} wide x {2 * ARM_HALF} deep, centre {ARM_SIDE:+} in X from its bundle; loop ring R {LOOP_R}/{LOOP_IN} "
          f"x {LOOP_LEN}; cam envelope R {CAM_R} at {CAM_AT} from the hinge (a guess: the cam isn't designed yet)")
    pr = p.open(MODEL)
    sweep_toolhead.MODEL = MODEL
    with tempfile.TemporaryDirectory(prefix="bowden-arms-") as d:
        sweep_toolhead.plan(os.path.join(d, "plan.json"))
        plan = json.load(open(os.path.join(d, "plan.json")))
    lab = plan["labels"]
    moving = set(plan["bed"]) | set(plan["gantry"]) | set(plan["carriage"]) | set(plan["belt"]) \
        | set(plan["heads"]["Left"]) | set(plan["heads"]["Right"])
    skip = moving | set(plan["exclude"])
    bundle = {o.Name for o in pr.leaves if o.Label.startswith(BUNDLE)}
    fixed = {o.Name: pr.shapes[o.Name] for o in pr.leaves if o.Name not in skip and o.Name not in bundle}
    p.log(f"fixed solids {len(fixed)}; left out: {len(moving)} moving, {len(plan['exclude'])} sweep_toolhead exclusions, "
          f"{len(bundle)} bundle solids ({', '.join(sorted({lab.get(n, n) for n in bundle})[:3])}, ...)")

    up = {s: arm_solids(V, Part, design, s, design["loop_up"]) for s in EXIT_X}
    down = {s: arm_solids(V, Part, design, s, design["loop_down"]) for s in EXIT_X}
    cam = cam_envelope(V, Part, design)
    up_all = Part.makeCompound(list(up.values()) + [cam])
    p.log(f"arms up: box {[round(v, 1) for v in (lambda b: (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax))(up_all.BoundBox)]}")

    def near_parts(shape):
        bb = shape.BoundBox; bb.enlarge(NEAR)
        names = [n for n, s in fixed.items() if s.BoundBox.intersect(bb)]
        ds = p.map(_t_dist, [(shape, fixed[n]) for n in names])
        bad = [(n, x.msg) for n, x in zip(names, ds) if isinstance(x, _Err)]
        if bad: raise RuntimeError(f"distToShape failed: {bad[:3]}")
        return sorted(((round(x, 2), lab.get(n, n)) for n, x in zip(names, ds) if x < NEAR), key=lambda t: t[0])

    # what moves in XY, swept to the gantry's rear stop
    dy = sweep_toolhead.Y_TRAVEL[1]
    def union(names, t):
        bb = FreeCAD.BoundBox()
        for n in names: bb.add(pr.shapes[n].BoundBox)
        bb.move(V(*t)); return bb
    sweeps = {}
    for rname, dz in RAISE.items():
        g = union(plan["gantry"], (0, dy, dz))
        boxes = [("gantry at its rear stop", g)]
        for h in ("Left", "Right"):
            nx, ny, nz = plan["carried"][h]["nozzle"]; tx, ty, tz = plan["carried"][h]["T"]
            sq = plan["carried"][h]["square"]
            y_reach = ny + dy - ty
            sw = FreeCAD.BoundBox()
            for x in (sq[0], sq[2]):                      # the carriage moves by tc, the head by tc - T (sweep_toolhead)
                tc = (x - nx + tx, y_reach - ny + ty, 0.0)
                sw.add(union(plan["carriage"], (tc[0], tc[1], dz)))
                sw.add(union(plan["heads"][h], (tc[0] - tx, tc[1] - ty, -tz + dz)))
            boxes.append((f"carriage + carried {h} head at the rear stop, swept over X", sw))
        sweeps[rname] = boxes
        for what, b in boxes:
            p.log(f"   moving ({rname}): {what}: Y {b.YMin:.1f}..{b.YMax:.1f}, Z {b.ZMin:.1f}..{b.ZMax:.1f}")

    def moving_gaps(shape, rname):
        out = []
        for what, b in sweeps[rname]:
            box = Part.makeBox(b.XLength, b.YLength, b.ZLength, V(b.XMin, b.YMin, b.ZMin))
            out.append((round(shape.distToShape(box)[0], 2), what))
        return sorted(out)

    result = {}
    for case, shape in [("arms up", up_all)] + [(f"arm {s} down", Part.makeCompound([down[s], cam] + [up[o] for o in EXIT_X if o != s]))
                                                for s in EXIT_X]:
        near = near_parts(shape)
        mv = {r: moving_gaps(shape if case == "arms up" else down[int(case.split()[1])], r) for r in RAISE}
        worst = min([g for g, _ in near] + [g for r in mv for g, _ in mv[r]] + [float("inf")])
        ok = worst >= CLEAR
        p.check(ok, f"{case}: {'clear' if ok else 'NOT clear'} (smallest gap {worst:.2f}, needs >= {CLEAR})")
        for g, what in near: p.log(f"      {g:7.2f}  {what}")
        if not near: p.log(f"      nothing fixed within {NEAR}")
        for r in RAISE:
            g, what = mv[r][0]
            p.log(f"      {g:7.2f}  moving, gantry {r}: {what} (box, conservative)")
        result[case] = dict(ok=ok, near=near, moving=mv)
    p.dump(dict(model=MODEL, design=design, result=result))
    p.finish([])                                                       # nothing to save, ever
    if not p.errs: p.log("bowden_arms: done (read-only, nothing saved)")


if __name__ in ("__main__", "bowden_arms") and "FreeCAD" in sys.modules:     # freecadcmd runs it as "bowden_arms"
    import litelib
    litelib.Pass("bowden_arms").run(main)
