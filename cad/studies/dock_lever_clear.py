# vt350#312: does the dock lever fit lite-79? Headless, read-only, never saves:
#   VT350_REPO=$PWD $APP freecadcmd $PWD/cad/studies/dock_lever_clear.py     (VT350_MODEL; default lite-79)
# Log: $VT350_WORK/logs/dock_lever_clear.log (+ .json). Verdict lines: "T<n> plunger: ok", "T<n> cable: clear",
# "dock lever route: clear" at the end.
#
# The layout comes from dock_lever.py (cad/data/dock_lever.json). Per tool:
#   - the plunger's target: rays along Y at the plunger's axis (and +-3 mm around it, and at the detach X, +-5) to the
#     docked head's front, so the face the ball tip presses is really there, flat enough, at every pose it must be;
#   - the plunger block (a box under the dock bar, Y -104..-72.5) and its rod (R 3, from the bar's back face to the
#     docked head's face): the block against every fixed solid but the dock bar it hangs from, and against its own
#     head docked, slid to the large opening (Y -6) and detached (X +-5 at the large opening);
#   - the cable: the housing (R 2.5) along its route, the wire (R 0.6) arm up and down, and the ceiling pulley
#     (R 8 x 6) against every fixed solid; the moving parts can't reach it (the riser is in front of the frontmost a
#     head ever gets, Y -89.7 at the large opening, and the rest is above Z 571, every moving part's top at +10.3):
#     the log states both from the route.
# The bundles and the arms are dock_lever.py's (numpy) check, not this one's.
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE] + [p for p in (os.path.join(os.path.dirname(os.path.dirname(HERE)), d)
                                     for d in ("cad/scripts", "platform/freecad")) if os.path.isdir(p)]

MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-79.FCStd")
DATA = os.path.join(os.path.dirname(HERE), "data")
EXIT_X = {1: -409.7, 2: -324.54, 3: -248.42, 4: -156.42, 5: -80.3}
NEAR, CLEAR = 5.0, 1.0
ROD_R, PULLEY = 3.0, (8.0, 6.0)
BUNDLE = ("Bowden ", "O2S USB cable", "Zip tie, black (2.5 mm) slot")
NOT_HEAD = ("Dock", "dock", "standoff", "bracket", "2020", "2040", "Bowden", "O2S USB cable slot", "Zip tie", "Door",
            "Roof", "LED channel")
MOVING_TOP = 560.37 + 10.3
FRONTMOST = -89.7


def main(p):
    import FreeCAD, Part
    from litelib import _t_dist, _Err
    V = FreeCAD.Vector
    d = json.load(open(os.path.join(DATA, "dock_lever.json")))
    P = d["params"]
    pr = p.open(MODEL)
    lab = {o.Name: o.Label for o in pr.leaves}
    sol = {o.Name: pr.shapes[o.Name] for o in pr.leaves if pr.shapes[o.Name] is not None
           and not pr.shapes[o.Name].isNull() and pr.shapes[o.Name].BoundBox.isValid()}
    p.log(f"model {MODEL} (read-only); {len(sol)} solids; layout from dock_lever.py: plunger X nozzle {P['P_DX']:+}, Z "
          f"{P['P_Z']}, lane X {P['LANE_DX']:+}, Z {P['Z_LANE']}")
    bar = [n for n in sol if lab[n].startswith("2020 dock bar")]
    if len(bar) != 1: raise RuntimeError(f"{len(bar)} dock bars")

    def head_of(x):
        out = []
        for n, s in sol.items():
            b = s.BoundBox
            if any(k in lab[n] for k in NOT_HEAD): continue
            cx, cy, cz = (b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, (b.ZMin + b.ZMax) / 2
            if x - 45 <= cx <= x + 40 and -90 <= cy <= 5 and 378 <= cz <= 556 and b.XLength < 90: out.append(n)
        return out

    def front_y(names, x, z, dx=0.0, dy=0.0):
        """The head's first surface along +Y from the bar's back face at (x, z), the head moved by (dx, dy)."""
        best = None
        for n in names:
            s = sol[n]; b = s.BoundBox
            if not (b.XMin + dx - 1e-6 <= x <= b.XMax + dx + 1e-6 and b.ZMin - 1e-6 <= z <= b.ZMax + 1e-6): continue
            c = Part.makeLine(V(x - dx, -110, z), V(x - dx, 10, z)).common(s)
            for e in c.Edges:
                y0 = min(v.Point.y for v in e.Vertexes) + dy
                if y0 > P["BAR"][1] - 1e-6 and (best is None or y0 < best[0]): best = (y0, lab[n])
        return best

    def tube(X, r, step=6.0):
        out, last = [], None
        pts = [X[0]]
        for q in X[1:]:
            if ((q[0] - pts[-1][0]) ** 2 + (q[1] - pts[-1][1]) ** 2 + (q[2] - pts[-1][2]) ** 2) ** 0.5 >= step: pts.append(q)
        if pts[-1] != X[-1]: pts.append(X[-1])
        for a, b in zip(pts[:-1], pts[1:]):
            va, vb = V(*a), V(*b); L = (vb - va).Length
            if L > 1e-6: out.append(Part.makeCylinder(r, L, va, (vb - va) * (1.0 / L)))
            out.append(Part.makeSphere(r, vb))
        return out

    def near_fixed(shape, skip=()):
        bb = shape.BoundBox; bb.enlarge(NEAR)
        names = [n for n, s in sol.items() if n not in skip and not lab[n].startswith(BUNDLE) and s.BoundBox.intersect(bb)]
        ds = p.map(_t_dist, [(shape, sol[n]) for n in names])
        bad = [(n, x.msg) for n, x in zip(names, ds) if isinstance(x, _Err)]
        if bad: raise RuntimeError(f"distToShape failed: {bad[:3]}")
        return sorted(((round(x, 2), lab[n]) for n, x in zip(names, ds) if x < NEAR), key=lambda t: t[0])

    allok, result = True, {}
    bx, by, bz = P["BLOCK"]; bar_front, bar_back, bar_zlo = P["BAR"]
    for s, r in d["routes"].items():
        s = int(s); x = EXIT_X[s]; xp, pz = r["plunger"]
        heads = head_of(x)
        p.log(f"T{s - 1}: {len(heads)} head solids in its dock")
        # the face: rays parked (at the axis and +-3), at the large opening, and detached either way
        faces = {}
        for name, dx, dy in (("parked", 0.0, 0.0), ("large opening", 0.0, -6.0), ("detached +X", 5.0, -6.0),
                             ("detached -X", -5.0, -6.0)):
            hits = [front_y(heads, xp + ox, pz + oz, dx, dy) for ox in (-3.0, 0.0, 3.0) for oz in (-3.0, 0.0, 3.0)]
            faces[name] = hits
        ys = [h[0] for h in faces["parked"] if h]
        flat = len(ys) == 9 and max(ys) - min(ys) <= 1.5
        on_detach = all(h for h in faces["detached +X"]) or all(h for h in faces["detached -X"])
        face_y = min(ys) if ys else None
        # the block and the rod
        block = Part.makeBox(bx, by, bz, V(xp - bx / 2, bar_back - by, bar_zlo - bz))
        rod = Part.makeCylinder(ROD_R, (face_y if face_y else bar_back + 8) - bar_back, V(xp, bar_back, pz), V(0, 1, 0))
        nb = near_fixed(block, skip=set(bar) | set(heads))
        head_shape = Part.makeCompound([sol[n] for n in heads])
        hp = {}
        for name, dx, dy in (("parked", 0, 0), ("large opening", 0, -6), ("detached +X", 5, -6), ("detached -X", -5, -6)):
            h = head_shape.copy(); h.translate(V(dx, dy, 0))
            hp[name] = round(block.distToShape(h)[0], 2)
        nr = near_fixed(rod, skip=set(bar) | set(heads))
        worst_block = min([g for g, _ in nb] + list(hp.values()) + [g for g, _ in nr] + [float("inf")])
        ok_p = flat and on_detach and worst_block >= CLEAR
        p.check(ok_p, f"T{s - 1} plunger: {'ok' if ok_p else 'NOT ok'} (face Y {face_y} parked, "
                      f"{'flat' if flat else 'NOT flat'} within 1.5 over +-3 mm; "
                      f"{'still under the tip' if on_detach else 'NOT under the tip'} detached; block/rod gap "
                      f"{worst_block:.2f}, needs >= {CLEAR})")
        for name, hits in faces.items():
            got = [h for h in hits if h]
            p.log(f"      face {name}: {len(got)}/9 rays hit, Y {min(h[0] for h in got):.2f}..{max(h[0] for h in got):.2f} "
                  f"({', '.join(sorted({h[1][:28] for h in got}))})" if got else f"      face {name}: no ray hits")
        p.log(f"      block to its head: " + ", ".join(f"{k} {v}" for k, v in hp.items()))
        for g, what in nb + nr: p.log(f"      {g:7.2f}  {what}")
        # the cable
        H = r["housing"]; parts = tube(H, P["HOUSING_R"]) + tube(r["wire_up"], P["WIRE_R"], 2.0) + tube(r["wire_down"], P["WIRE_R"], 2.0)
        wu = r["wire_up"]; pul_c = V(wu[0][0], (wu[0][1] + 14.0), P["Z_LANE"] - 6.0)
        parts.append(Part.makeCylinder(PULLEY[0], PULLEY[1], pul_c - V(PULLEY[1] / 2, 0, 0), V(1, 0, 0)))
        cable = Part.makeCompound(parts)
        nc = near_fixed(cable, skip=set(heads))
        low_front = [q for q in H if q[1] > FRONTMOST - P["HOUSING_R"] - 1.0 and q[2] < MOVING_TOP + P["HOUSING_R"] + 1.0]
        worst_c = min([g for g, _ in nc] + [float("inf")])
        ok_c = worst_c >= CLEAR and not low_front
        p.check(ok_c, f"T{s - 1} cable: {'clear' if ok_c else 'NOT clear'} (smallest gap {worst_c:.2f}, needs >= {CLEAR}; "
                      f"{len(low_front)} route points where a moving part could reach)")
        for g, what in nc: p.log(f"      {g:7.2f}  {what}")
        allok &= ok_p and ok_c
        result[s] = dict(face_y=face_y, flat=flat, on_detach=on_detach, block=hp, near_block=nb + nr, near_cable=nc,
                         ok=ok_p and ok_c)
    p.log(f"dock lever route: {'clear' if allok else 'NOT clear'}")
    p.dump(dict(model=MODEL, result=result))
    p.finish([])
    if not p.errs: p.log("dock_lever_clear: done (read-only, nothing saved)")


if __name__ in ("__main__", "dock_lever_clear") and "FreeCAD" in sys.modules:
    import litelib
    litelib.Pass("dock_lever_clear").run(main)
