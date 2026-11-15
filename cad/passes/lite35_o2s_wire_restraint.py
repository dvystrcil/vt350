# GUI pass: vt350-lite-34 -> vt350-lite-35   (headless = dry run, never saves)
# vt350#19 (user, 2026-11-14): "we may need to print a strain relief for the electrical cable which plugs into [the
# O2S]" -> "add the O2S wire restraint for the strain relief". lite-30 left the STEP's `Orbitool O2S Wire restrain` out
# (a printed part: parts/printed needed it first); this pass adds it to each of the 5 heads, and parts/printed gets its
# two STLs (orbiter-toolboards/, CC0-1.0).
# Source: LorinczElectronics/Orbiter-Toolboards @ 52a5a33, "Orbiter O2S Toolboard/3D CAD/Orbitool O2S Wire restrain.step"
# (2 solids: `O2S WirerestrainBody`, `O2S Wirestrain_Lock`), read from $VT350_DL (o2s_wire_restrain.step), checked by
# size and sha256. It is the restraint's CURRENT design: upstream updated it (and the body STL) on 2025-11-03, after
# the assembly STEP lite-30 used (2025-04-23), whose copy of the body is older (2593.1 mm3 vs 2869.9; the lock is
# the same). Both STEPs share one frame: the lock's and the body's boxes are identical in the two (checked), so the
# current restraint goes where the assembly puts its old one. The printable files are the upstream STLs of the same
# two parts (`O2S WirerestrainBody.stl`, `O2S Wirestrain_Lock.stl`): volumes 2870.8 / 828.9 vs the STEP's 2869.9 /
# 829.2 (mesh vs exact).
# Pose: each head's board, heat sink (lite-34), USB stub and Smart Sensor were placed by lite-30 (lite-31 copied the
# heads) with one rigid transform from the assembly STEP. This pass recovers it per head by register.register on those
# 4 parts (STEP vs model, centres of mass, labels paired) and places the restraint with it, in the head's App::Part.
# Checks (refuses to save on any): both STEPs are the pinned files; the restraint STEP's 2 solids and their boxes match
# the assembly's restraint; in each head the 4-part fit is register's "same part" (centres <= 0.05 mm, volumes <=
# 0.5 mm3); the parts land where registered; against this head's O2S parts and Orbiter, only the overlaps the STEP
# itself has (as designed, per part, +-0.05 mm3); nothing else in the printer overlaps them; the carried head's
# restraint clears everything but its own head and carriage by >= 2 mm at lite-32's 38 dock poses; roles `printed`;
# solids + 10.
import FreeCAD, Part, Import, hashlib, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))
import litelib
import register
from litelib import gshape, is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-34.FCStd", f"{MODELS}/vt350-lite-35.FCStd"
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path.insert(0, f"{REPO}/platform/render")
import colours

V = FreeCAD.Vector
DL = os.environ.get("VT350_DL", f"{MODELS}/downloads/upstream/orbiter-toolboards-52a5a33")
ASM = ("o2s_assembly.step", 25950842, "0140eb363daff45621b93dceefdfaaa6195ab17374aa1288d25ffc187df205f6")
RST = ("o2s_wire_restrain.step", 379883, "bee4906e7030b9e1ae7c5f45da0f8b2a2ff9df86944f5302259c8a9ff3fbc969")
RESTRAINT = "Orbitool O2S Wire restrain"         # the assembly's subtree (lite-30's SKIP)
BODY, LOCK = "O2S WirerestrainBody", "O2S Wirestrain_Lock"
PARTS = {BODY: ("body", 2869.9), LOCK: ("lock", 829.2)}
LABEL = "Orbitool O2S wire restraint {part} {side} (Orbiter-Toolboards 52a5a33, CC0-1.0){suffix}"
# the 4 parts that fix each head's pose: assembly STEP selector -> the model label prefix (lite-30 / lite-34)
STEP_BOARD, STEP_USB, STEP_SENSOR = "Orbitool USB O2S v3.3", "Toolboard_USB Cable v1", ("Orbiter Sensor v4.2", "SensorConnector")
HS_VOL, HS_DIMS = 2113.1, (12.0, 23.4, 30.4)     # the board's heat sink (lite-34's test)
MODEL = {"board": "Orbitool O2S v3.3 toolboard ", "hs": "Orbitool O2S heat sink ", "usb": "Orbitool O2S USB cable stub ",
         "sensor": "Orbiter Smart Sensor v4.2 ", "mount": "Orbitool O2S standoffs + screws "}
SRC_ORBITER, MOCKUP = "Orbiter v2.0 mockup v10", "Orbiter V2.0 Mockup"
SLOTS = [("Left Toolhead", "Left Dock", "L"), ("Toolhead slot 2 (L)", "Dock slot 2 (L)", "L"), ("Toolhead slot 3 (R)", "Dock slot 3 (R)", "R"),
         ("Toolhead slot 4 (L)", "Dock slot 4 (L)", "L"), ("Right Toolhead", "Right Dock", "R")]
SLIDE, CARRIED_DZ, DETACH, CLEAR = 6.0, -0.315, 5.0, 2.0
DY_DETACH, DY_PARK = range(-6, 61, 2), (-6, -4, -2, 0)
TOL, DESIGN_TOL, PLACE_TOL = 1e-3, 0.05, 1e-6


def tree(o):
    out = [o]
    for k in (getattr(o, 'Group', []) or []): out += tree(k)
    return out


def doc_paths(doc):
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, 'Group', []) or []): par.setdefault(k.Name, o)
    def path(o):
        r, q = [], par.get(o.Name)
        while q is not None: r.append(q.Label); q = par.get(q.Name)
        return r
    return path


def load(p, name, size, sha):
    path = os.path.join(DL, name)
    got = (os.path.getsize(path), hashlib.sha256(open(path, "rb").read()).hexdigest())
    p.check(got == (size, sha), f"{name} is the pinned file: {got[0]} bytes, sha256 {got[1][:16]}")
    d = FreeCAD.newDocument(name.split(".")[0]); Import.insert(path, d.Name)
    pa = doc_paths(d)
    return d, [(o, pa(o), gshape(o)) for o in d.Objects if is_leaf(o)]


def desc(key, shapes):
    vs = [(x.Volume, x.CenterOfMass) for s in shapes for x in s.Solids]; tv = sum(v for v, _ in vs)
    c = sum((cc * (v / tv) for v, cc in vs), V(0, 0, 0))
    return dict(label=key, vol=tv, com=[c.x, c.y, c.z])


def moved(s, m):
    c = s.copy(); c.Placement = FreeCAD.Placement(m).multiply(c.Placement); return c


def box_gap(a, b):
    d = [max(0.0, a.XMin - b.XMax, b.XMin - a.XMax), max(0.0, a.YMin - b.YMax, b.YMin - a.YMax), max(0.0, a.ZMin - b.ZMax, b.ZMin - a.ZMax)]
    return (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5


def boxes_same(a, b, tol=1e-3):
    return max(abs(x - y) for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax),
                                          (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))) < tol


def main(p):
    pr = p.open(SRC); doc = pr.doc
    cmap = colours.load(f"{REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    # --- the two STEPs
    ad, al = load(p, *ASM)
    rd, rl = load(p, *RST)
    old = {o.Label: s for o, pp, s in al if RESTRAINT in pp}
    new = {o.Label: s for o, pp, s in rl}
    p.check(set(new) == set(PARTS) and set(old) == set(PARTS), f"restraint STEP solids {sorted(new)}; the assembly's {sorted(old)}")
    for k, (_, vol) in PARTS.items():
        p.check(abs(new[k].Volume - vol) < 0.5 and boxes_same(new[k].BoundBox, old[k].BoundBox),
                f"{k}: {new[k].Volume:.1f} mm3 (the assembly's {old[k].Volume:.1f}); same box in both STEPs (same frame): "
                f"{new[k].BoundBox}")
    def is_hs(s):
        d = sorted((s.BoundBox.XLength, s.BoundBox.YLength, s.BoundBox.ZLength))
        return abs(s.Volume - HS_VOL) < 0.5 and all(abs(a - b) < 0.1 for a, b in zip(d, HS_DIMS))
    in_board = [s for o, pp, s in al if STEP_BOARD in pp and o.Label != STEP_USB]
    hs = [x for s in in_board for x in s.Solids if is_hs(x)]
    step_groups = {
        "board": [x for s in in_board for x in s.Solids if not is_hs(x)],
        "hs": hs, "usb": [s for o, pp, s in al if o.Label == STEP_USB],
        "sensor": [s for o, pp, s in al if STEP_SENSOR[0] in pp or o.Label == STEP_SENSOR[1]]}
    p.check(all(step_groups.values()) and len(hs) == 1, f"STEP fit parts: { {k: len(v) for k, v in step_groups.items()} }")
    s_desc = [desc(k, v) for k, v in step_groups.items()]
    # as designed: the current restraint vs the assembly's O2S parts and Orbiter, in the STEP's frame
    s_others = {"board": step_groups["board"], "hs": hs, "usb": step_groups["usb"], "sensor": step_groups["sensor"],
                "mount": [s for o, pp, s in al if "Nuts&Bolts (1)" in pp and o.Label != STEP_USB],
                "orbiter": [s for o, pp, s in al if SRC_ORBITER in pp]}
    def ov(a, ss): return sum(a.common(y).Volume for s in ss for y in s.Solids if y.BoundBox.intersect(a.BoundBox))
    design = {(k, g): round(ov(new[k], ss), 3) for k in PARTS for g, ss in s_others.items()}
    p.log("as designed (STEP frame), restraint x O2S/Orbiter overlaps mm3:", {f"{a} x {b}": v for (a, b), v in design.items() if v > TOL})
    # --- per head: the pose, the parts
    abs_src = next(o for o in pr.leaves if 'ABS' in getattr(getattr(o, 'ShapeMaterial', None), 'Name', ''))
    made, heads = [], []
    for h, d, k in SLOTS:
        root = obj(h); mine = [o for o in tree(root) if is_leaf(o)]
        got = {key: [o for o in mine if o.Label.startswith(pre)] for key, pre in MODEL.items()}
        p.check(all(len(v) == 1 for v in got.values()), f"{h}: one each of {list(MODEL)}: { {a: len(b) for a, b in got.items()} }")
        got = {a: b[0] for a, b in got.items()}
        r = register.register(s_desc, [desc(key, [pr.shapes[got[key].Name]]) for key in ("board", "hs", "usb", "sensor")])
        p.check(r["ok"] and r["n"] == 4, f"{h}: the O2S pose from 4 parts: n {r['n']}, COM max {r['com_max']:.5f} ({r['com_worst']}), "
                f"volume max {r['vol_max']:.4f} ({r['vol_worst']})")
        m = FreeCAD.Matrix(*sum(r["matrix"], []))
        b = got["board"].Label
        side = "Left" if " Left " in b else "Right"
        suffix = b[b.rindex(")") + 1:]
        rg = root.getGlobalPlacement()
        items = []
        for key, (part, _) in PARTS.items():
            g = moved(new[key], m)
            n = doc.addObject('Part::Feature', "O2S_restraint_" + part)
            local = g.copy(); local.Placement = rg.inverse().multiply(g.Placement)
            n.Shape = local; root.addObject(n)
            n.Label = LABEL.format(part=part, side=side, suffix=suffix); n.ShapeMaterial = abs_src.ShapeMaterial
            if FreeCAD.GuiUp:
                try: n.ViewObject.ShapeAppearance = abs_src.ViewObject.ShapeAppearance
                except Exception: n.ViewObject.ShapeColor = abs_src.ViewObject.ShapeColor
            items.append((key, n, g))
        made.append((h, d, k, root, got, items))
    doc.recompute(); pr.refresh()
    allnew = []
    for h, d, k, root, got, items in made:
        orb = [o for o in tree(root) if is_leaf(o) and any(x.Label.startswith(MOCKUP) for x in tree_parents(o))]
        for key, n, g in items:
            sh = pr.shapes[n.Name]
            p.check(boxes_same(sh.BoundBox, g.BoundBox, PLACE_TOL), f"{n.Label}: lands where registered; {sh.BoundBox}")
            mdl = {"board": ov(sh, [pr.shapes[got["board"].Name]]), "hs": ov(sh, [pr.shapes[got["hs"].Name]]),
                   "usb": ov(sh, [pr.shapes[got["usb"].Name]]), "sensor": ov(sh, [pr.shapes[got["sensor"].Name]]),
                   "mount": ov(sh, [pr.shapes[got["mount"].Name]]), "orbiter": ov(sh, [pr.shapes[o.Name] for o in orb])}
            off = {gname: (round(v, 3), design[(key, gname)]) for gname, v in mdl.items() if abs(v - design[(key, gname)]) > DESIGN_TOL}
            p.check(not off, f"{n.Label}: overlaps with its head's O2S/Orbiter as designed "
                    f"({ {a: round(b, 2) for a, b in mdl.items() if b > TOL} }) {off or ''}")
            allnew.append((h, n, sh))
        excl = {o.Name for o in tree(root) if is_leaf(o)}
        p.no_overlap([(n.Label, pr.shapes[n.Name]) for _, n, _ in items], pr,
                     lambda r, h=h: f"{h}: restraint vs every solid outside its head: {r.hits[:6]}", exclude=excl)
    # --- the carried head's restraint at lite-32's dock poses vs everything that stays put (lite-33's carried group:
    # the head, its dock's moving parts, its tube, both dock carriage copies; distToShape raised to the box gap)
    car = [o for dname in ("Left Dock", "Right Dock") for c in tree(obj(dname))
           if c.TypeId == 'App::Part' and c.Label.startswith("Carriage") for o in tree(c) if is_leaf(o)]
    moving = {o.Name for o in car} | {o.Name for o in pr.leaves if o.Label.startswith("Bowden")}
    for h, d, k, root, got, items in made:
        moving |= {o.Name for o in tree(obj(h)) + tree(obj(d)) if is_leaf(o)
                   and not o.Label.startswith(("Dock Asembly", "Dock bracket", "Dock pair"))}
    for h, d, k, root, got, items in made:
        own = {o.Name for o in tree(obj(h)) + tree(obj(d)) if is_leaf(o)
               and not o.Label.startswith(("Dock Asembly", "Dock bracket", "Dock pair"))}
        obst = [o for o in pr.leaves if o.Name not in own and o.Name not in {c.Name for c in car}
                and not o.Label.startswith("Bowden")]
        det = DETACH if k == "L" else -DETACH
        poses = [(0.0, dy) for dy in DY_PARK] + [(det, dy) for dy in DY_DETACH]
        tasks, keys, gmin = [], [], (float("inf"), "")
        for dx, dy in poses:
            for key, n, _ in items:
                sh = pr.shapes[n.Name]; m = sh.BoundBox
                mb = FreeCAD.BoundBox(m.XMin + dx, m.YMin + dy, m.ZMin + CARRIED_DZ, m.XMax + dx, m.YMax + dy, m.ZMax + CARRIED_DZ)
                for o in obst:
                    g = box_gap(mb, pr.boxes[o.Name])
                    gmin = min(gmin, (g, f"{key} @x{dx:+.0f} y{dy:+.0f} vs {o.Label}"))
                    if g < CLEAR + 1.0:
                        tasks.append((pr.shapes[o.Name], sh.translated(V(dx, dy, CARRIED_DZ)))); keys.append((f"{key} @x{dx:+.0f} y{dy:+.0f}", o.Label, g))
        ds = p.map(litelib._t_dist, tasks)
        res, raised = [], []
        for (kk, ol, g), dd in zip(keys, ds):
            if isinstance(dd, litelib._Err): raise RuntimeError(f"distToShape failed for {kk} vs {ol}: {dd.msg}")
            if dd < g - 1e-6: raised.append((kk, ol, round(dd, 2), round(g, 2)))
            res.append((max(dd, g), kk, ol))
        if raised: p.log(f"{h}: {len(raised)} distToShape results below their box gap, raised to it: {raised[:4]}")
        near = sorted((round(a, 2), b, c) for a, b, c in res if a < CLEAR)
        p.log(f"{h}: nearest {sorted((round(a, 2), b, c) for a, b, c in res)[:3]}")
        p.check(not near and gmin[0] < float("inf"), f"{h}: its restraint at {len(poses)} dock poses ({len(tasks)} pairs "
                f"within {CLEAR + 1.0:.0f} mm by box, measured; nearest box gap {gmin[0]:.2f}: {gmin[1]}): "
                f"min {min(res)[0] if res else float('inf'):.2f} mm to anything that stays put {near[:3]}")
    def gpath(o):
        r, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r))
    mat = lambda o: getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default'
    for h, n, sh in allnew:
        r_ = colours.role_of(cmap, n.Label, gpath(n), mat(n))
        p.check(r_ == "printed", f"{n.Label}: material {mat(n)} -> role {r_}")
    p.check(len(pr.leaves) == n_before + len(allnew), f"solids: {n_before} + {len(allnew)} = {len(pr.leaves)}")
    p.dump({"restraints": [dict(label=n.Label, head=h, volume=round(sh.Volume, 1),
                                box=[round(v, 2) for v in (sh.BoundBox.XMin, sh.BoundBox.YMin, sh.BoundBox.ZMin,
                                                           sh.BoundBox.XMax, sh.BoundBox.YMax, sh.BoundBox.ZMax)]) for h, n, sh in allnew],
            "design_overlaps_mm3": {f"{a} x {b}": v for (a, b), v in design.items() if v > TOL}})
    FreeCAD.closeDocument(ad.Name); FreeCAD.closeDocument(rd.Name)
    p.finish([(doc, DST)])


def tree_parents(o):
    out, q = [], o.getParentGeoFeatureGroup()
    while q is not None: out.append(q); q = q.getParentGeoFeatureGroup()
    # an App::DocumentObjectGroup parent isn't a GeoFeatureGroup: walk InList too
    for x in o.InList:
        if x not in out and getattr(x, 'Group', None) is not None and o in x.Group:
            out.append(x); out += [y for y in tree_parents(x) if y not in out]
    return out


litelib.Pass("lite35_o2s_wire_restraint").run(main)
