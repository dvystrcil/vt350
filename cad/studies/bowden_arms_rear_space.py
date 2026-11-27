# vt350#312: is there room behind the gantry's rear stop for each tool's slack loop? Headless, read-only, never saves:
#   VT350_REPO=$PWD $APP freecadcmd $PWD/cad/studies/bowden_arms_rear_space.py     (VT350_MODEL to pick; default lite-80)
# Log: $VT350_WORK/logs/bowden_arms_rear_space.log (+ .json).
#
# The owner's lines from the EMU to the roof are static, so the roof exit clamps each bundle and up to ~315 mm of slack
# (T0/T4; ~195 for T2) has to stay inside the chamber. The idea: a dancer pulls it down through a slot in the arm into
# a hanging U near the hinge end, behind the gantry's rear stop, where nothing moves. A U stores about twice its drop,
# so ~315 mm needs ~160 mm of drop: from the lowered arm (Z 640) to ~Z 480.
#
# This maps the space there. For each tool (its roof exit's X, +-SPAN in X), each Z from Z_LO to the ceiling, it casts
# a line along +Y from Y_FROM and records what it meets:
#   - the moving envelope: the gantry, and the carriage + carried heads swept over X, all at the rear stop
#     (sweep_toolhead.Y_TRAVEL), as boxes (conservative), at today's height and #243's +10.3;
#   - the bed's parts that reach behind Y_FROM, each swept over the bed's Z travel (saved pose up to its top,
#     sweep_toolhead's dz_top) as its own box;
#   - every fixed solid (not the bed or the moving groups; the bundles themselves listed apart, since they re-route).
# The free depth at (X, Z) = from the moving envelope's back (or Y_FROM if nothing moving is at that height) to the
# first fixed solid behind it. Reported per tool as the free depth at each Z (the narrowest over the tool's X band and
# at the exit's X), and every fixed solid in the region, with its box.
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE] + [p for p in (os.path.join(os.path.dirname(os.path.dirname(HERE)), d)
                                     for d in ("cad/scripts", "platform/freecad")) if os.path.isdir(p)]

MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-80.FCStd")
EXIT_X = {1: -409.7, 2: -324.54, 3: -248.42, 4: -156.42, 5: -80.3}   # lanyard/lrod.py (lite70_roof_exit_low.json)
EXIT_Y, CEIL = 449.0, 679.0
SPAN, DX = 40.0, 10.0              # each tool's X band (a U turning in the back wall's plane is ~100 wide at R 51)
Z_LO, DZ = float(os.environ.get("REAR_Z_LO", "440")), 10.0   # REAR_Z_LO: how far down to look
Y_FROM, Y_TO = 380.0, 560.0
RAISE = {"lite-80": 0.0}           # run on lite-80: the gantry is already at #243's +10
BUNDLE = ("Bowden ", "O2S USB cable", "Zip tie, black (2.5 mm) slot")


def main(p):
    import tempfile
    import FreeCAD, Part
    import sweep_toolhead
    V = FreeCAD.Vector
    p.log(f"model {MODEL} (read-only)")
    pr = p.open(MODEL)
    sweep_toolhead.MODEL = MODEL
    with tempfile.TemporaryDirectory(prefix="rear-space-") as d:
        sweep_toolhead.plan(os.path.join(d, "plan.json"))
        plan = json.load(open(os.path.join(d, "plan.json")))
    moving = set(plan["bed"]) | set(plan["gantry"]) | set(plan["carriage"]) | set(plan["belt"]) \
        | set(plan["heads"]["Left"]) | set(plan["heads"]["Right"])
    x0, x1 = min(EXIT_X.values()) - SPAN - 20, max(EXIT_X.values()) + SPAN + 20
    region = FreeCAD.BoundBox(x0, Y_FROM, Z_LO - 20, x1, Y_TO, CEIL + 30)
    lab = {o.Name: o.Label for o in pr.leaves}
    fixed, bundle = {}, {}
    for o in pr.leaves:
        if o.Name in moving: continue
        s = pr.shapes[o.Name]
        if s is None or s.isNull() or not s.BoundBox.isValid() or not s.BoundBox.intersect(region): continue
        (bundle if o.Label.startswith(BUNDLE) else fixed)[o.Name] = s
    p.log(f"region X {x0:.0f}..{x1:.0f}, Y {Y_FROM:.0f}..{Y_TO:.0f}, Z {Z_LO - 20:.0f}..{CEIL + 30:.0f}: "
          f"{len(fixed)} fixed solids, {len(bundle)} bundle solids (left out: they re-route)")
    for n, s in sorted(fixed.items(), key=lambda t: (t[1].BoundBox.YMin, t[1].BoundBox.ZMin)):
        b = s.BoundBox
        p.log(f"   fixed  X {b.XMin:7.1f}..{b.XMax:7.1f}  Y {b.YMin:6.1f}..{b.YMax:6.1f}  Z {b.ZMin:6.1f}..{b.ZMax:6.1f}  {lab[n]}")

    dy = sweep_toolhead.Y_TRAVEL[1]
    def union(names, t):
        bb = FreeCAD.BoundBox()
        for n in names: bb.add(pr.shapes[n].BoundBox)
        bb.move(V(*t)); return bb
    env = {}
    for rname, dz in RAISE.items():
        boxes = [("gantry", union(plan["gantry"], (0, dy, dz)))]
        for h in ("Left", "Right"):
            nx, ny, nz = plan["carried"][h]["nozzle"]; tx, ty, tz = plan["carried"][h]["T"]
            sq = plan["carried"][h]["square"]
            y_reach = ny + dy - ty
            sw = FreeCAD.BoundBox()
            for x in (sq[0], sq[2]):
                tc = (x - nx + tx, y_reach - ny + ty, 0.0)
                sw.add(union(plan["carriage"], (tc[0], tc[1], dz)))
                sw.add(union(plan["heads"][h], (tc[0] - tx, tc[1] - ty, -tz + dz)))
            boxes.append((f"carriage + {h} head", sw))
        dz_top = max(plan["carried"][h]["dz_top"] for h in ("Left", "Right"))
        for n in plan["bed"]:                      # each bed part swept over its Z travel on its own (the union's box
            b = FreeCAD.BoundBox(pr.shapes[n].BoundBox)   # runs to Y 499 and would block the whole rear)
            if not b.isValid(): continue
            t = FreeCAD.BoundBox(b); t.move(V(0, 0, dz_top)); b.add(t)
            if b.YMax > Y_FROM and b.intersect(region): boxes.append((f"bed part {lab.get(n, n)}, over its Z travel", b))
        env[rname] = boxes
        for what, b in boxes[:3] + [bx for bx in boxes[3:] if rname == "lite-80"]:
            p.log(f"   moving ({rname}) {what} at the rear stop: X {b.XMin:.1f}..{b.XMax:.1f}, Y {b.YMin:.1f}..{b.YMax:.1f}, "
                  f"Z {b.ZMin:.1f}..{b.ZMax:.1f}")

    def hits(x, z):
        """Fixed solids' Y intervals along the line at (x, z), Y_FROM..Y_TO."""
        out = []
        for n, s in fixed.items():
            b = s.BoundBox
            if not (b.XMin - 1e-6 <= x <= b.XMax + 1e-6 and b.ZMin - 1e-6 <= z <= b.ZMax + 1e-6): continue
            if b.YMax < Y_FROM or b.YMin > Y_TO: continue
            try:
                c = Part.makeLine(V(x, Y_FROM, z), V(x, Y_TO, z)).common(s)
            except Exception as e:
                p.log(f"   common failed on {lab[n]}: {e}"); continue
            for e in c.Edges:
                ys = sorted(v.Point.y for v in e.Vertexes)
                if len(ys) == 2 and ys[1] - ys[0] > 1e-3: out.append((ys[0], ys[1], lab[n]))
        return sorted(out)

    zs = [Z_LO + i * DZ for i in range(int((CEIL - Z_LO) / DZ) + 1)]
    result = {}
    for slot, ex in EXIT_X.items():
        xs = [ex - SPAN + i * DX for i in range(int(2 * SPAN / DX) + 1)]
        per = {r: [] for r in RAISE}
        for z in zs:
            for rname in RAISE:
                row = []
                for x in xs:
                    back = Y_FROM
                    for what, b in env[rname]:
                        if b.XMin <= x <= b.XMax and b.ZMin <= z <= b.ZMax: back = max(back, b.YMax)
                    wall = next(((y0, who) for y0, y1, who in hits(x, z) if y1 > back + 1e-6), (Y_TO, "nothing up to Y_TO"))
                    row.append((x, back, max(0.0, wall[0] - back), wall[1]))
                narrow = min(row, key=lambda t: t[2]); at_exit = min(row, key=lambda t: abs(t[0] - ex))
                per[rname].append(dict(z=z, min_free=round(narrow[2], 1), min_at_x=narrow[0], min_wall=narrow[3],
                                       moving_back=round(narrow[1], 1), exit_free=round(at_exit[2], 1),
                                       exit_wall=at_exit[3]))
        result[slot] = per
        p.log(f"T{slot - 1} (roof exit X {ex}, band {xs[0]:.0f}..{xs[-1]:.0f}): free Y depth behind the moving parts, by Z")
        for i, z in enumerate(zs):
            a = per["lite-80"][i]
            p.log(f"   Z {z:5.0f}: {a['min_free']:6.1f} (exit X {a['exit_free']:6.1f}; wall: {a['min_wall']}; "
                  f"moving back Y {a['moving_back']:.1f})")
    # the deepest U each tool could hang: the lowest Z down to which the band keeps at least NEED free, from the arm
    for need in (12.0, 20.0, 30.0):
        line = []
        for slot in EXIT_X:
            rows = result[slot]["lite-80"]
            ok = [r["z"] for r in rows if r["min_free"] >= need]
            # contiguous from the ceiling down
            low = None
            for r in reversed(rows):
                if r["min_free"] >= need: low = r["z"]
                else: break
            line.append(f"T{slot - 1} down to Z {low:.0f}" if low is not None else f"T{slot - 1} none")
        p.log(f"with >= {need:.0f} mm free in Y over the whole band (lite-80): " + "; ".join(line))
    p.dump(dict(model=MODEL, exit_x=EXIT_X, span=SPAN, result=result,
                envelope={r: [(w, [b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax]) for w, b in v] for r, v in env.items()}))
    p.finish([])
    if not p.errs: p.log("bowden_arms_rear_space: done (read-only, nothing saved)")


if __name__ in ("__main__", "bowden_arms_rear_space") and "FreeCAD" in sys.modules:
    import litelib
    litelib.Pass("bowden_arms_rear_space").run(main)
