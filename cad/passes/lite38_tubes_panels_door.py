# GUI pass: vt350-lite-37 -> vt350-lite-38   (headless = dry run, never saves)
# vt350#19 (user, 2026-11-14, on lite-37's render): "two of the bowden tubes is offset - from the left its 3 and 5"; "the
# outsides [of the panels] should be the frame color or slightly off to indicate I painted them with a spray can";
# "just add the left panel for now while we decide" (aluminium or acrylic: #4); "I would like to see the pexi on the
# door with the gasket (black gasket)". Four changes:
#
# 1. THE R HEADS' TUBES. On slots 3 and 5 the tube's lower end is 10.7 mm -X of the Smart Sensor's inlet bore (the r 2.05
#    bore over the Orbiter's filament path); on the L heads it is on it (0.00). Each R tube is moved by the measured
#    dX (the route is planar in X = const, so a shift keeps it), and its route points (Inlet, ExitPoint; the handles
#    are lengths) take the plane's X measured from the solid (vt350#174, for these two tubes; the L tubes stay #174's).
#    lite-36's roof cut and clamp follow the tube: the roof layers are rebuilt from lite-35's uncut ones minus each
#    exit's removed material, the R exits' moved by dX; the R clamps (base + cap) move by dX.
# 2. PANEL PAINT. Each panel (right, back, roof, and the new left) is split into its inside and a 0.2 mm skin on its
#    outward faces: skin = P - P shifted 0.2 inward, core = P common that. The skin is `panel_paint` (a rattle-can shade
#    of the frame green); the core keeps the object, label and the model's white.
# 3. THE LEFT PANEL: the right panel mirrored about the frame's centre plane in X (3 mm, X -523..-520). Its material is
#    open (#4); placeholder like the right one.
# 4. THE DOOR WINDOW: a 3 mm clear sheet over the door's 2040 frame on its outside face, on a 2 mm black EPDM gasket
#    ring (20 mm wide, along the frame's 40 mm faces). Clicky-Clack (the door's design) uses a 3 mm panel held by
#    Panel_Clips; the clips aren't modelled. Both go in the door's App::Part, so they swing with it.
# Checks (refuses to save on any): R tube ends on their sensor bores and the L tubes already were (0.00); both R
# tubes moved by the same dX; each tube planar (section centres at 5 heights share X); its props now match its solid;
# the R tube sits in its sensor as the L tubes do (same overlap, +-0.05 mm3); the roof layers stay one valid solid
# each, lose exactly the old volume (an R exit's material moved, not more or less), and no tube crosses them; the
# clamps clear each other by >= 10 mm and hit nothing; paint skin + core = the panel (+-1e-3 mm3), skin thin; the left
# panel, window and gasket hit nothing; roles; solids + 7.
import FreeCAD, Part, os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))
import litelib
from litelib import is_leaf, gshape, MODELS
SRC, DST, UNCUT = f"{MODELS}/vt350-lite-37.FCStd", f"{MODELS}/vt350-lite-38.FCStd", f"{MODELS}/vt350-lite-35.FCStd"
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path.insert(0, f"{REPO}/platform/render")
import colours
V = FreeCAD.Vector

HEADS = [("Left Toolhead", "Bowden Left", "L", 1), ("Toolhead slot 2 (L)", "Bowden slot 2", "L", 2),
         ("Toolhead slot 3 (R)", "Bowden slot 3", "R", 3), ("Toolhead slot 4 (L)", "Bowden slot 4", "L", 4),
         ("Right Toolhead", "Bowden Right", "R", 5)]
SENSOR, BORE_R = "Orbiter Smart Sensor v4.2 ", 2.05
ROOF = ["Roof panel (3 mm)", "Roof felt strip (pad 3)", "Roof felt strip liner, inner", "Roof felt strip liner, outer"]
CLAMP = "Roof exit clamp {part} slot {n} (vt350, GPL-3.0-or-later)"
PANELS = [("Right side panel (3 mm)", V(1, 0, 0)), ("Back Panel001", V(0, 1, 0)), ("Roof panel (3 mm)", V(0, 0, 1))]
LEFT = "Left side panel (3 mm)"
SKIN, PAINT = 0.2, "{label} paint, outside"
FRAME_GROUP = "4040-350 VT Frame v12"
DOOR, DOOR_FRAME = "Door (1) (1)", "Door Frame"
WIN_T, GASKET_T, GASKET_IN, GASKET_OUT = 3.0, 2.0, 10.0, 30.0   # gasket ring: 10..30 mm in from the frame's outline
WINDOW = "Door window (3 mm clear sheet, acrylic or polycarbonate per #4)"
GASKET = "Door window gasket (EPDM foam, black)"
EXTRAS = "Enclosure extras (lite-16)"
TOL = 1e-3


def tree(o):
    out = [o]
    for k in (getattr(o, 'Group', []) or []): out += tree(k)
    return out


def centre_at(p, tag, s, z):
    sec = s.slice(V(0, 0, 1), z)
    p.check(len(sec) == 1, f"{tag}: cut by Z {z} in one loop ({len(sec)})")
    return Part.Face(sec[0]).CenterOfMass


def set_global(o, shape_global_pl):
    par = o.getParentGeoFeatureGroup()
    o.Placement = (par.getGlobalPlacement().inverse() if par else FREECAD_ID()).multiply(shape_global_pl)


def FREECAD_ID(): return FreeCAD.Placement()


def add(doc, pr, parent, name, label, shape, mat_src):
    o = doc.addObject("Part::Feature", name)
    loc = shape.copy()
    if parent is not None:
        loc.Placement = parent.getGlobalPlacement().inverse().multiply(shape.Placement)
        parent.addObject(o)
    o.Shape = loc; o.Label = label
    if mat_src is not None: o.ShapeMaterial = mat_src.ShapeMaterial
    return o


def main(p):
    pr = p.open(SRC); doc = pr.doc
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    cmap = colours.load(f"{REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    # ---------------- 1. the tubes
    fit, shift = {}, {}
    for h, t, k, n in HEADS:
        root = obj(h); ts = pr.shapes[obj(t).Name]
        sens = [o for o in tree(root) if is_leaf(o) and o.Label.startswith(SENSOR)]
        p.check(len(sens) == 1, f"{h}: one Smart Sensor ({len(sens)})")
        ss = pr.shapes[sens[0].Name]
        bores = {(round(f.Surface.Center.x, 4), round(f.Surface.Center.y, 4)) for f in ss.Faces
                 if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - BORE_R) < 1e-6
                 and abs(abs(f.Surface.Axis.z) - 1) < 1e-9}
        p.check(len(bores) == 1, f"{h}: the sensor's r {BORE_R} inlet bore, one axis {sorted(bores)}")
        bx, by = next(iter(bores))
        end = centre_at(p, t, ts, ts.BoundBox.ZMin + 0.5)
        dx, dy = bx - end.x, by - end.y
        p.log(f"{h}: {t} lower end ({end.x:.3f}, {end.y:.3f}); sensor bore ({bx:.3f}, {by:.3f}); off by dX {dx:+.3f} dY {dy:+.3f}")
        p.check(abs(dy) < TOL, f"{h}: {t} in line with its sensor bore in Y ({dy:+.4f})")
        if k == "L": p.check(abs(dx) < TOL, f"{h}: {t} on its sensor bore already ({dx:+.4f})")
        else: shift[t] = dx
        fit[t] = (h, sens[0])
    dxs = list(shift.values())
    p.check(len(dxs) == 2 and abs(dxs[0] - dxs[1]) < TOL and 5 < dxs[0] < 15,
            f"the R tubes are off by the same dX: {[round(x, 4) for x in dxs]}")
    DX = sum(dxs) / len(dxs)
    tube_fit = {}
    for t in [hh[1] for hh in HEADS]:
        o = obj(t); h, sens = fit[t]
        if t in shift:
            g = FreeCAD.Placement(V(shift[t], 0, 0), FreeCAD.Rotation()).multiply(o.getGlobalPlacement())
            par = o.getParentGeoFeatureGroup()
            o.Placement = par.getGlobalPlacement().inverse().multiply(g) if par else g
    doc.recompute(); pr.refresh()
    for h, t, k, n in HEADS:
        o = obj(t); ts = pr.shapes[o.Name]; sens = fit[t][1]
        cs = [centre_at(p, t, ts, z) for z in (530.0, 560.0, 600.0, 650.0, 680.0)]
        X = cs[2].x
        p.check(max(abs(c.x - X) for c in cs) < 0.01, f"{t}: planar, section centres X {[round(c.x, 3) for c in cs]}")
        if t in shift:
            for prop in ("Inlet", "ExitPoint"):                  # the handles are lengths (lite-10), not points
                v = V(getattr(o, prop)); setattr(o, prop, V(X, v.y, v.z))
            end = centre_at(p, t, ts, ts.BoundBox.ZMin + 0.5); ex = centre_at(p, t, ts, 690.0)
            p.check(abs(o.Inlet.x - end.x) < 0.01 and abs(o.Inlet.y - end.y) < 0.01 and abs(o.Inlet.z - ts.BoundBox.ZMin) < 0.01
                    and abs(o.ExitPoint.x - ex.x) < 0.01,
                    f"{t}: moved {shift[t]:+.3f} in X; props now match the solid: Inlet {tuple(round(c, 2) for c in o.Inlet)}, "
                    f"ExitPoint X {o.ExitPoint.x:.2f} (the solid crosses Z 690 at X {ex.x:.2f})")
        tube_fit[t] = ts.common(pr.shapes[sens.Name]).Volume
    lf = [tube_fit[t] for _, t, k, _ in HEADS if k == "L"]
    for _, t, k, _ in HEADS:
        if k == "R":
            p.check(all(abs(tube_fit[t] - v) < 0.05 for v in lf),
                    f"{t}: sits in its sensor as the L tubes do: {tube_fit[t]:.3f} mm3 (L: {[round(v, 3) for v in lf]})")
    # ---------------- the roof cut and the clamps follow
    unc = FreeCAD.openDocument(UNCUT); p.log("opened", UNCUT)
    uncut = {lab: gshape(next(o for o in unc.Objects if o.Label == lab)) for lab in ROOF}
    mids = {}
    for _, _, _, n in HEADS:
        b = pr.shapes[obj(CLAMP.format(part="base", n=n)).Name].BoundBox
        mids[n] = (b.XMin + b.XMax) / 2
    rslots = {n for _, t, k, n in HEADS if k == "R"}
    for lab in ROOF:
        o = obj(lab); now, old = pr.shapes[o.Name], uncut[lab]
        removed = old.cut(now)
        per = {n: [] for n in mids}
        for s in removed.Solids:
            c = s.BoundBox.Center.x
            n = min(mids, key=lambda m: abs(mids[m] - c))
            p.check(abs(mids[n] - c) < 40, f"{lab}: a removed piece at X {c:.1f}, {abs(mids[n] - c):.1f} from exit {n}")
            per[n].append(s)
        new = old
        for n, ps in per.items():
            for s in ps:
                new = new.cut(s.translated(V(DX, 0, 0)) if n in rslots else s)
        new = new.removeSplitter()
        lost_old, lost_new = old.Volume - now.Volume, old.Volume - new.Volume
        moved = {n: (round(sum(s.Volume for s in per[n]), 3),
                     round(sum(old.common(s.translated(V(DX, 0, 0))).Volume for s in per[n]), 3)) for n in rslots}
        p.check(new.isValid() and len(new.Solids) == 1 and abs(lost_new - lost_old) < TOL
                and all(abs(a - b) < TOL for a, b in moved.values()),
                f"{lab}: rebuilt from lite-35 with the R exits moved {DX:+.3f}: cut {lost_new:.3f} mm3 (was {lost_old:.3f}); "
                f"R exits' material there before and after the move {moved}; valid {new.isValid()}, solids {len(new.Solids)}")
        o.Shape = new
    FreeCAD.closeDocument(unc.Name)
    for n in rslots:
        for part in ("base", "cap"):
            o = obj(CLAMP.format(part=part, n=n))
            o.Placement = FreeCAD.Placement(V(DX, 0, 0), FreeCAD.Rotation()).multiply(o.Placement)   # extras: global frame
    # ---------------- 3. the left panel (before the paint: it gets painted like the others)
    rp = obj(PANELS[0][0])
    fr = [o for o in pr.leaves if FRAME_GROUP in [q.Label for q in o.InListRecursive]
          and 'Alumin' in getattr(getattr(o, 'ShapeMaterial', None), 'Name', '')]
    fx0, fx1 = min(pr.shapes[o.Name].BoundBox.XMin for o in fr), max(pr.shapes[o.Name].BoundBox.XMax for o in fr)
    rb = pr.shapes[rp.Name].BoundBox
    p.check(abs(rb.XMin - fx1) < TOL, f"the frame spans X {fx0:.2f}..{fx1:.2f}; the right panel sits on its right face (X {rb.XMin:.2f})")
    xm = (fx0 + fx1) / 2
    lp = pr.shapes[rp.Name].mirror(V(xm, 0, 0), V(1, 0, 0))
    left = add(doc, pr, None, "Left_side_panel", LEFT, lp, rp)
    obj(EXTRAS).addObject(left)
    # ---------------- 4. the door window + gasket
    dfm = [o for o in tree(obj(DOOR_FRAME)) if is_leaf(o) and o.Label.startswith("2040")]
    p.check(len(dfm) == 4, f"the door frame: 4 x 2040 ({[o.Label for o in dfm]})")
    bbs = [pr.shapes[o.Name].BoundBox for o in dfm]
    X0, X1 = min(b.XMin for b in bbs), max(b.XMax for b in bbs)
    Z0, Z1 = min(b.ZMin for b in bbs), max(b.ZMax for b in bbs)
    Y0 = min(b.YMin for b in bbs)
    p.check(all(abs(b.YMin - Y0) < TOL for b in bbs), f"the door frame's outside face is flat at Y {Y0:.2f}; outline X {X0:.2f}..{X1:.2f}, Z {Z0:.2f}..{Z1:.2f}")
    def rect(i, t, y1):
        return Part.makeBox(X1 - X0 - 2 * i, t, Z1 - Z0 - 2 * i, V(X0 + i, y1 - t, Z0 + i))
    gasket = rect(GASKET_IN, GASKET_T, Y0).cut(rect(GASKET_OUT, GASKET_T + 2, Y0 + 1))
    window = rect(0, WIN_T, Y0 - GASKET_T)
    door = obj(DOOR)
    g_o = add(doc, pr, door, "Door_window_gasket", GASKET, gasket, None)
    w_o = add(doc, pr, door, "Door_window", WINDOW, window, None)
    doc.recompute(); pr.refresh()
    # ---------------- 2. paint: every panel, the left one too
    painted, pre = [], {}
    def overlaps(sh, skip):
        r = {}
        for q in pr.leaves:
            if q.Name in skip or not pr.boxes[q.Name].intersect(sh.BoundBox): continue
            v = sh.common(pr.shapes[q.Name]).Volume
            if v > TOL: r[q.Label] = v
        return r
    for lab, out in PANELS + [(LEFT, V(-1, 0, 0))]:
        o = obj(lab); P = pr.shapes[o.Name]
        pre[lab] = overlaps(P, {o.Name})          # what the panel already overlaps (the back panel: the frame's slots)
        inner = P.translated(out * -SKIN)
        skin, core = P.cut(inner).removeSplitter(), P.common(inner).removeSplitter()
        area = sum(f.Area for f in P.Faces if f.normalAt(*f.Surface.parameter(f.CenterOfMass)[:2]).dot(out) > 0.999) if False else None
        p.check(skin.isValid() and core.isValid() and len(core.Solids) == 1 and abs(skin.Volume + core.Volume - P.Volume) < TOL
                and skin.Volume < 0.15 * P.Volume,
                f"{lab}: paint skin {skin.Volume:.1f} + core {core.Volume:.1f} = {P.Volume:.1f} mm3 ({SKIN} mm on the "
                f"{tuple(int(c) for c in out)} faces; skin {len(skin.Solids)} solid(s))")
        par = o.getParentGeoFeatureGroup()
        core_l = core.copy()
        if par is not None: core_l.Placement = par.getGlobalPlacement().inverse().multiply(core.Placement)
        o.Shape = core_l
        sk = add(doc, pr, par, "Panel_paint", PAINT.format(label=lab), skin, o)
        painted.append((o, sk))
    doc.recompute(); pr.refresh()
    # ---------------- checks on the result
    tubes = [obj(t) for _, t, _, _ in HEADS]
    roof = [obj(l) for l in ROOF]
    left_over = [(t.Label, r.Label, round(pr.shapes[t.Name].common(pr.shapes[r.Name]).Volume, 3)) for t in tubes for r in roof
                 if pr.shapes[t.Name].BoundBox.intersect(pr.shapes[r.Name].BoundBox)]
    p.check(all(v < TOL for _, _, v in left_over), f"tubes vs the rebuilt roof layers: {[x for x in left_over if x[2] >= TOL] or 'clear'}")
    clamps = [obj(CLAMP.format(part=part, n=n)) for _, _, _, n in HEADS for part in ("base", "cap")]
    bases = sorted((pr.shapes[obj(CLAMP.format(part='base', n=n)).Name].BoundBox, n) for _, _, _, n in HEADS) if False else \
        sorted(((pr.shapes[obj(CLAMP.format(part='base', n=n)).Name].BoundBox.XMin, pr.shapes[obj(CLAMP.format(part='base', n=n)).Name].BoundBox.XMax, n)
                for _, _, _, n in HEADS))
    for (a0, a1, na), (b0, b1, nb) in zip(bases, bases[1:]):
        p.check(b0 - a1 >= 10.0, f"clamps slot {na} | slot {nb}: {b0 - a1:.1f} mm apart")
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in clamps], pr,
                 lambda r: f"the clamps vs everything (tubes included): {r.hits[:6]}", exclude={o.Name for o in clamps})
    for t in tubes:
        h = fit[t.Label][0]
        excl = {o.Name for o in tree(obj(h)) if is_leaf(o)} | {t.Name}
        p.no_overlap([(t.Label, pr.shapes[t.Name])], pr, lambda r, t=t: f"{t.Label} vs everything outside its head: {r.hits[:6]}",
                     exclude=excl)
    new_parts = [left, g_o, w_o] + [sk for _, sk in painted]
    mine = {o.Name for o in new_parts} | {o.Name for o, _ in painted}
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in (left, g_o, w_o)], pr,
                 lambda r: f"the left panel, door window and gasket vs everything: {r.hits[:6]}", exclude=mine)
    # a panel's skin + core overlap exactly what the panel did before the split: nothing new. The back panel came from
    # the original model sitting in the rear 4040s' slots (4 x 4040 + 2 M5 screws, 18.8 cm3), so its skin shares that
    for o, sk in painted:
        skip = {o.Name, sk.Name}
        a, b = overlaps(pr.shapes[o.Name], skip), overlaps(pr.shapes[sk.Name], skip)
        both = {k: a.get(k, 0.0) + b.get(k, 0.0) for k in set(a) | set(b)}
        was = pre[o.Label]
        bad = {k: (round(both.get(k, 0.0), 3), round(was.get(k, 0.0), 3)) for k in set(both) | set(was)
               if abs(both.get(k, 0.0) - was.get(k, 0.0)) > max(TOL, 1e-4 * was.get(k, 0.0))}   # boolean noise on a
        # 5869 mm3 overlap with a 4040 profile: 0.09 mm3 (skin + core = the panel to 1e-3 mm3, checked above)
        p.check(not bad, f"{o.Label}: skin + core overlap only what the panel did: "
                f"{ {k: round(v, 1) for k, v in sorted(was.items())} or 'nothing'} {bad or ''}")
    def gpath(o):
        r, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r))
    mat = lambda o: getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default'
    want = [(sk, "panel_paint") for _, sk in painted] + [(o, None) for o, _ in painted] + [(g_o, "rubber"), (w_o, "glass_clear")]
    for o, r in want:
        r_ = colours.role_of(cmap, o.Label, gpath(o), mat(o))
        p.check(r_ == r, f"{o.Label}: material {mat(o)} -> role {r_}")
    p.check(len(pr.leaves) == n_before + 7, f"solids: {n_before} + 7 = {len(pr.leaves)}")
    wb, gb = pr.shapes[w_o.Name].BoundBox, pr.shapes[g_o.Name].BoundBox
    p.dump({"r_tube_shift_x": round(DX, 4), "tubes_in_sensor_mm3": {k: round(v, 3) for k, v in tube_fit.items()},
            "frame_x": [round(fx0, 2), round(fx1, 2)], "left_panel_box": [round(v, 2) for v in (pr.shapes[left.Name].BoundBox.XMin,
            pr.shapes[left.Name].BoundBox.YMin, pr.shapes[left.Name].BoundBox.ZMin, pr.shapes[left.Name].BoundBox.XMax,
            pr.shapes[left.Name].BoundBox.YMax, pr.shapes[left.Name].BoundBox.ZMax)],
            "door_window_mm": [round(wb.XLength, 1), round(wb.ZLength, 1), WIN_T], "door_gasket": {"ring_mm": [GASKET_IN, GASKET_OUT],
            "thickness": GASKET_T, "length_m": round(2 * ((X1 - X0 - GASKET_IN - GASKET_OUT) + (Z1 - Z0 - GASKET_IN - GASKET_OUT)) / 1000, 2)},
            "paint_skins_mm3": {sk.Label: round(pr.shapes[sk.Name].Volume, 1) for _, sk in painted}})
    p.finish([(doc, DST)])


litelib.Pass("lite38_tubes_panels_door").run(main)
