# GUI pass: vt350-lite-30 -> vt350-lite-31   (headless = dry run, never saves)
# vt350#19 (user, 2026-11-13): a front ROW of five MadMax docks, LLRLR, held by a 2020 across the front.
#  - Pattern and nozzle gaps from cad/studies/dock_layout.py's committed result (cad/data/logs/dock_layout.json, 2 mm
#    clearance): L|L 85.16, L|R 76.12, R|L 92.00. L = the left dock's style (keyslot plate on -X, detach +X), R = the
#    right dock's (mirrored). The row is CENTRED in the carriage's nozzle-X reach (sweep_toolhead.log), so both outer
#    slots keep the same margin to the reach limit (user's choice).
#  - Slot 1 = the existing Left head + Left Dock, slot 5 = the existing Right head + Right Dock, moved in X. Slots 2-4
#    are copies (head, MadMax plate, keyslot plate, bowden tube moved with the head) of the Left (L) or Right (R)
#    template. The copies get NO carriage copy: the dock's carriage copy is only the pickup reference that
#    sweep_toolhead.py reads from Left/Right Dock, and a ghost carriage in a parked dock would be a fixed solid there.
#  - Mount (AC7, user: "by a 2020"): the 2040 placeholder (`Dock crossbar (placeholder, 2040)`, Y -90..-70, Z 517..557)
#    is replaced by a 2020 resting on the keyslot plates' tops, its rear face 2 mm in front of the carried head at
#    attach_y in that height band (the head's front there is the Orbiter hub, well behind the duct below). The bar is the
#    model's own `2020 (1)` (bed frame, X -480..-10, the same span) moved. Both corner dock arms are removed: the bar
#    takes their place. The bracket joining each keyslot plate to the bar is NOT modelled (logged).
#  - Bowden tubes: each slot keeps its head's rigid tube, moved with the head (route parameters unchanged; #3).
# Checks (refuses to save on any): the committed row fits the reach, centred, both margins >= 5 mm; every slot's docked
# nozzle lands on its target X (0.01 mm) with Y/Z unchanged; each slot (head + dock + tube) overlaps nothing outside
# itself; the bar overlaps nothing; it ends on a frame part at both ends; it sits on every keyslot plate (gap <= 0.01);
# the carried head and the carriage at attach_y (slot 1 and slot 5) stay >= 1.5 mm off it; solid count adds up.
import FreeCAD, Part, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))      # litelib, which puts the other code folders on the path
import litelib
from litelib import box, gshape, is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-30.FCStd", f"{MODELS}/vt350-lite-31.FCStd"
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
LAYOUT = f"{REPO}/cad/data/logs/dock_layout.json"
SWEEP = f"{REPO}/cad/data/logs/sweep_toolhead.log"
CLEAR = "clearance 2.0"
SLIDE, CARRIED_DZ = 6.0, -0.315            # keyslot slide (attach_y = parked - 6); carried head vs docked (sweep_toolhead)
BAR_GAP = 2.0                              # bar rear face to the carried head's front at attach_y
NOZZLE = "E3D v6 HotEnd - Nozzle"
OLD_BAR, BAR_SRC = "Dock crossbar (placeholder, 2040)", "2020 (1)"
ROOT = "4040-350x350x250 Voron Trident v4 v33"
T = {"L": dict(head="Left Toolhead", dock="Left Dock", tube="Bowden Left"),
     "R": dict(head="Right Toolhead", dock="Right Dock", tube="Bowden Right")}


def tree(o):
    out = [o]
    for k in (getattr(o, 'Group', []) or []): out += tree(k)
    return out


def main(p):
    pr = p.open(SRC); doc = pr.doc
    V, P = FreeCAD.Vector, FreeCAD.Placement
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    root = obj(ROOT)
    p.check(root.getGlobalPlacement().Rotation.isSame(FreeCAD.Rotation(), 1e-9), "printer root not rotated (global X moves)")
    # --- the row, from the committed study
    lay = json.load(open(LAYOUT))["rows"][CLEAR]
    row, gaps = lay["rows"]["5"], lay["gaps"]
    import print_area
    reach = print_area.parse_reach(open(SWEEP).read()); rx = (reach["x_min"], reach["x_max"])
    pat = row["pattern"]
    p.check(pat == "LLRLR", f"committed 5-tool row {pat} ({LAYOUT})")
    det = {"L": 5.0, "R": -5.0}
    span = sum(gaps[f"{a}|{b}"] for a, b in zip(pat, pat[1:]))
    lpad, rpad = max(0.0, -det[pat[0]]), max(0.0, det[pat[-1]])
    margin = (rx[1] - rx[0] - span - lpad - rpad) / 2
    xs = [rx[0] + lpad + margin]
    for a, b in zip(pat, pat[1:]): xs.append(xs[-1] + gaps[f"{a}|{b}"])
    p.log(f"reach {rx}; row {pat}: span {span:.2f}, margin {margin:.2f} each side; slot nozzle X {[round(x, 2) for x in xs]}")
    p.check(margin >= 5.0, f"row fits the reach with {margin:.2f} mm each side (>= 5)")
    # --- template nozzles (docked)
    def nozzle(head):
        n = [o for o in tree(obj(head)) if is_leaf(o) and o.Label.startswith(NOZZLE)]
        if len(n) != 1: raise RuntimeError(f"{head}: {len(n)} nozzles")
        b = pr.boxes[n[0].Name]; return ((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, b.ZMin)
    noz = {k: nozzle(v["head"]) for k, v in T.items()}
    p.log("template docked nozzles:", {k: tuple(round(c, 3) for c in v) for k, v in noz.items()})
    n_before = len(pr.leaves)
    # lite-30's own tubes already run through the roof (the top exit, pass-through not cut yet: #3 AC4). Measure which
    # roof parts they cross BEFORE anything moves; only those are allowed for the moved and copied tubes.
    roof = {}
    for k, v in T.items():
        t = obj(v["tube"]); ts = pr.shapes[t.Name]
        cand = [o for o in pr.leaves if o.Name != t.Name and pr.boxes[o.Name].intersect(ts.BoundBox)]
        vols = p.volumes([(ts, pr.shapes[o.Name]) for o in cand])
        roof[k] = sorted({o.Label for o, vv in zip(cand, vols) if vv > 1e-3})
        p.log(f"lite-30 {v['tube']} crosses (allowed for every tube of this type): {roof[k]}")
    allowed = set(roof["L"]) | set(roof["R"])
    p.check(all(x.startswith("Roof") for x in allowed), f"lite-30 tubes cross only roof parts ({sorted(allowed)})")
    # --- keep the old geometry for later checks
    old = {k: {o.Name for o in tree(obj(v["head"])) + tree(obj(v["dock"])) if is_leaf(o)} for k, v in T.items()}
    tubes = {k: obj(v["tube"]) for k, v in T.items()}
    arms = [o for o in doc.Objects if is_leaf(o) and o.Label.startswith("Dock Arm")]
    p.check(len(arms) == 2, f"two corner dock arms to remove ({[a.Label for a in arms]})")
    def move(o, d):                             # global translation of an App::Part under the (unrotated) root
        o.Placement = P(V(*d), FreeCAD.Rotation()).multiply(o.Placement)
    def set_global(o, g):                       # put a leaf at global placement g under its current parent
        par = o.getParentGeoFeatureGroup()
        o.Placement = (par.getGlobalPlacement().inverse().multiply(g)) if par else g
    slots = []                                  # (n, type, head, dock, tube, dx)
    # slot 1 and slot 5: the existing heads + docks
    for i, k in ((0, pat[0]), (len(pat) - 1, pat[-1])):
        if k != ("L" if i == 0 else "R"): raise RuntimeError("the outer slots are expected to be L ... R")
        dx = xs[i] - noz[k][0]
        tg = tubes[k].getGlobalPlacement()
        move(obj(T[k]["head"]), (dx, 0, 0)); move(obj(T[k]["dock"]), (dx, 0, 0))
        doc.recompute()
        set_global(tubes[k], P(V(dx, 0, 0), FreeCAD.Rotation()).multiply(tg))
        slots.append((i + 1, k, obj(T[k]["head"]), obj(T[k]["dock"]), tubes[k], dx))
    doc.recompute()
    for a in arms: doc.removeObject(a.Name)
    # slots 2..4: copies
    for i in range(1, len(pat) - 1):
        k = pat[i]; src_h, src_d = obj(T[k]["head"]), obj(T[k]["dock"])
        dx = xs[i] - (noz[k][0] + [s for s in slots if s[1] == k][0][5])   # template is already moved: use its new X
        h = doc.copyObject(src_h, True); d = doc.copyObject(src_d, True)
        for c in (h, d):
            if c.getParentGeoFeatureGroup() is None: root.addObject(c)
        h.Label, d.Label = f"Toolhead slot {i + 1} ({k})", f"Dock slot {i + 1} ({k})"
        # the copied dock's carriage copy goes (pickup reference only, Left/Right Dock keep theirs)
        for c in [o for o in tree(d) if o.TypeId == 'App::Part' and o.Label.startswith("Carriage")]:
            for o in reversed(tree(c)): doc.removeObject(o.Name)
        # tubes: the Left head holds BOTH tubes; keep only this template's
        for o in [o for o in tree(h) if is_leaf(o) and o.Label.startswith("Bowden")]:
            if not o.Label.startswith(T[k]["tube"]) or k == "R": doc.removeObject(o.Name)
        doc.recompute()
        move(h, (dx, 0, 0)); move(d, (dx, 0, 0)); doc.recompute()
        tb = [o for o in tree(h) if is_leaf(o) and o.Label.startswith("Bowden")]
        if not tb:                                # R template: its tube lives in the Left head; copy it alone
            t = doc.copyObject(tubes[k], False); h.addObject(t); tb = [t]
            set_global(t, P(V(xs[i] - xs[-1], 0, 0), FreeCAD.Rotation()).multiply(tubes[k].getGlobalPlacement()))
        tb[0].Label = f"Bowden slot {i + 1}"
        slots.insert(i, (i + 1, k, h, d, tb[0], dx))
    doc.recompute()
    # --- the 2020 dock bar
    pr.refresh()
    keyslots = [o for s in slots for o in tree(s[3]) if is_leaf(o) and o.Label.startswith("Dock Asembly")]
    p.check(len(keyslots) == 5, f"five keyslot plates ({len(keyslots)})")
    ktop = max(pr.boxes[o.Name].ZMax for o in keyslots)
    p.log("keyslot plate tops:", [round(pr.boxes[o.Name].ZMax, 3) for o in keyslots])
    z0 = ktop
    band = box(-600, 100, -300, 300, z0, z0 + 20.0)
    def head_at_attach(s):                       # the head's leaves (not the dock) moved to attach_y
        return {o.Label + f" [slot {s[0]}]": pr.shapes[o.Name].translated(V(0, -SLIDE, CARRIED_DZ))
                for o in tree(s[2]) if is_leaf(o) and not o.Label.startswith("Bowden")}
    fronts = []
    for s in (slots[0], slots[-1]):
        for lab, sh in head_at_attach(s).items():
            if not sh.BoundBox.intersect(band.BoundBox): continue
            c = sh.common(band)
            if c.Volume > 1e-6: fronts.append((c.BoundBox.YMin, lab))
    fy, who = min(fronts)
    y1 = fy - BAR_GAP; y0 = y1 - 20.0
    p.log(f"carried head front at attach_y in Z {z0:.2f}..{z0 + 20:.2f}: Y {fy:.2f} ({who}); bar Y {y0:.2f}..{y1:.2f}")
    src = obj(BAR_SRC); sb = pr.boxes[src.Name]
    p.check(abs((sb.ZMax - sb.ZMin) - 20) < 0.05 and abs((sb.YMax - sb.YMin) - 20) < 0.05, f"{BAR_SRC} is a 20x20 bar along X ({sb})")
    bar = pr.shapes[src.Name].translated(V(0, y0 - sb.YMin, z0 - sb.ZMin))
    bb = bar.BoundBox; p.log("2020 dock bar:", bb)
    oldbar = obj(OLD_BAR); grp = oldbar.getParentGeoFeatureGroup()
    pr.refresh()
    excl = {oldbar.Name}
    # --- checks on the new state
    for s in slots:
        n_ = [o for o in tree(s[2]) if is_leaf(o) and o.Label.startswith(NOZZLE)]
        b = pr.boxes[n_[0].Name]; c = ((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, b.ZMin)
        p.check(abs(c[0] - xs[s[0] - 1]) < 0.01 and abs(c[1] - noz[s[1]][1]) < 0.01 and abs(c[2] - noz[s[1]][2]) < 0.01,
                f"slot {s[0]} ({s[1]}): docked nozzle ({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f}), target X {xs[s[0] - 1]:.3f}")
    for s in slots:
        mine = {o.Name for o in tree(s[2]) + tree(s[3]) if is_leaf(o)} | {s[4].Name}
        items = [(o.Label, pr.shapes[o.Name]) for o in pr.leaves if o.Name in mine]
        tubes_ = [it for it in items if it[0].startswith("Bowden")]
        rest = [it for it in items if not it[0].startswith("Bowden")]
        p.no_overlap(rest, pr, lambda r, s=s: f"slot {s[0]} ({s[1]}) head + dock x everything else: {r.hits[:6]}",
                     exclude=tuple(mine | excl))
        roof_ex = tuple(o.Name for o in pr.leaves if o.Label in allowed)
        p.no_overlap(tubes_, pr, lambda r, s=s: f"slot {s[0]} ({s[1]}) tube(s) {[t[0] for t in tubes_]} x everything else "
                     f"but its roof pass-through: {r.hits[:6]}", exclude=tuple(mine | excl) + roof_ex)
    p.no_overlap([("2020 dock bar", bar)], pr, lambda r: f"2020 dock bar x printer: {r.hits[:6]}", exclude=tuple(excl))
    ends = []
    for x in (bb.XMin - 0.5, bb.XMax + 0.5):
        probe = box(x - 0.5, x + 0.5, y0 + 1, y1 - 1, z0 + 1, z0 + 19)
        ends.append([o.Label for o in pr.leaves if o.Name not in excl and pr.boxes[o.Name].intersect(probe.BoundBox)
                     and pr.shapes[o.Name].common(probe).Volume > 1e-3])
    p.check(all(ends), f"bar ends on frame parts: left {ends[0][:3]}, right {ends[1][:3]}")
    kg = [round(z0 - pr.boxes[o.Name].ZMax, 3) for o in keyslots]
    p.check(max(kg) <= 0.01, f"bar bottom on every keyslot plate top (gaps {kg})")
    for s in (slots[0], slots[-1]):
        p.min_distance(bar, head_at_attach(s), lambda r, s=s: f"slot {s[0]}: carried head at attach_y vs the bar: "
                       f"{r.d:.2f} mm ({r.near[:2]})", min_d=BAR_GAP - 0.5)
    # carriage + Beacon at attach_y for slot 1: the dock's carriage copy minus the gantry carriage = the pickup offset
    copy_c = next(o for o in tree(slots[0][3]) if is_leaf(o) and o.Label == "COMPOUND003")
    real_c = next(o for o in tree(obj("Carriage (1)")) if is_leaf(o) and o.Label == "COMPOUND")
    off = pr.boxes[copy_c.Name].Center - pr.boxes[real_c.Name].Center
    carr = {o.Label: pr.shapes[o.Name].translated(V(off.x, off.y - SLIDE, 0)) for o in tree(obj("Carriage (1)")) if is_leaf(o)}
    p.min_distance(bar, carr, lambda r: f"slot 1: carriage + Beacon at attach_y vs the bar: {r.d:.2f} mm ({r.near[:2]})",
                   min_d=BAR_GAP - 0.5)
    # --- write the bar in place of the 2040
    doc.removeObject(oldbar.Name)
    nb = doc.addObject('Part::Feature', 'DockBar'); nb.Shape = bar; grp.addObject(nb)
    nb.Placement = grp.getGlobalPlacement().inverse().multiply(nb.Placement)
    nb.Label = "Dock bar 2020 (holds the 5 keyslot plates; brackets not modelled, #19 AC7)"
    if FreeCAD.GuiUp:
        try: nb.ViewObject.ShapeAppearance = src.ViewObject.ShapeAppearance
        except Exception: nb.ViewObject.ShapeColor = src.ViewObject.ShapeColor
    doc.recompute(); pr.refresh()
    p.log("NOT MODELLED: the bracket joining each keyslot plate to the bar (#19 AC7); the tubes' routes for the new heads (#3)")
    names = {o.Name for o in pr.leaves}
    new = {o.Name for s in slots[1:-1] for o in tree(s[2]) + tree(s[3]) if is_leaf(o)}
    lost = sorted(o.Label for s in slots[1:-1] for o in tree(s[2]) + tree(s[3]) if is_leaf(o) and o.Name not in names)
    p.log(f"slots 2-4: {len(new)} new solids; in a slot tree but not a model leaf: {lost[:10]}")
    p.check(len(pr.leaves) == n_before - 2 + len(new), f"solids: {n_before} - 2 arms + {len(new)} (slots 2-4) = {len(pr.leaves)}")
    p.dump({"pattern": pat, "slot_x": xs, "margin": margin, "bar": [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax],
            "slots": [dict(slot=s[0], type=s[1], head=s[2].Label, dock=s[3].Label, tube=s[4].Label, dx=s[5]) for s in slots]})
    p.finish([(doc, DST)])


litelib.Pass("lite31_dock_row").run(main)
