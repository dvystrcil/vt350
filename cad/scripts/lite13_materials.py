# GUI pass: vt350-lite-12.FCStd -> vt350-lite-13.FCStd   (headless = dry run, never saves)
# Fills in materials the user confirmed after lite-12 (2026-11-04): the backbone is steel, the kinematic bed-mount
# supports are aluminium (alloy not given -> Aluminum-Generic). Also the back kinematic ball, which lite-12's rule
# missed (label "Ball001"), is steel like the other two. Geometry and colours unchanged (appearance saved/restored,
# as in lite12_materials.py). Rewrites data/materials.tsv: the current material of every solid.
import FreeCAD, Materials, sys, os, re, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-12.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-13.FCStd"
DRY = not FreeCAD.GuiUp
CARDS = {"Steel-Generic": "90bbd8ef-8623-4d78-b3bf-e0bdb9b74dd3", "Aluminum-Generic": "9bf060e9-1663-44a2-88e2-2ff6ee858efe"}
# (label regex, group-path substring, material, expected count)
ASSIGN = [
    (r"^backbone-350", "", "Steel-Generic", 1),
    (r"^(front|back)_support", "Kinematic bed mount", "Aluminum-Generic", 5),
    (r"^Ball\d*(\(Mirror\))?$", "Kinematic bed mount", "Steel-Generic", 3),
]
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite13_materials.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def parent_of(o):
    return next((x for x in o.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))
                 and o in getattr(x, 'Group', [])), None)
def path(o):
    r = []; p = parent_of(o)
    while p is not None: r.append(p.Label); p = parent_of(p)
    return ' / '.join(reversed(r))
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def look(o):
    vo = getattr(o, 'ViewObject', None)
    return [(a.DiffuseColor, a.Transparency) for a in vo.ShapeAppearance] if vo is not None and hasattr(vo, 'ShapeAppearance') else None
try:
    mm = Materials.MaterialManager(); mats = {n: mm.getMaterial(u) for n, u in CARDS.items()}
    for n, m in mats.items():
        if m.Name != n: raise RuntimeError(f"card {CARDS[n]} is {m.Name}, expected {n}")
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    leaves = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: (o.Shape.BoundBox.DiagonalLength, o.getGlobalPlacement(), o.ShapeMaterial.Name) for o in leaves}
    errs, changed, restored = [], {}, 0
    for rx, grp, mat, n_exp in ASSIGN:
        hit = [o for o in leaves if re.match(rx, o.Label) and grp in path(o)]
        if len(hit) != n_exp: errs.append(f"{rx}: {len(hit)} matches, expected {n_exp}")
        for o in hit:
            app = look(o); old = o.ShapeMaterial.Name
            o.ShapeMaterial = mats[mat]; changed[o.Name] = mat
            log(f"  {o.Label:34} {old:16} -> {mat}")
            if app is not None and look(o) != app:
                ap = o.ViewObject.ShapeAppearance
                for a, (dc, tr) in zip(ap, app): a.DiffuseColor = dc; a.Transparency = tr
                o.ViewObject.ShapeAppearance = ap; restored += 1
                if look(o) != app: errs.append(f"colour changed: {o.Label}")
    doc.recompute()
    log(f"{len(changed)} materials set; appearance restored on {restored}")
    rows = []
    for o in leaves:
        dl, g, m0 = before[o.Name]
        if abs(o.Shape.BoundBox.DiagonalLength - dl) > 1e-6 or not o.getGlobalPlacement().isSame(g, 1e-9): errs.append(f"geometry changed: {o.Label}")
        if o.Name not in changed and o.ShapeMaterial.Name != m0: errs.append(f"material changed unexpectedly: {o.Label}")
        if o.Name in changed and o.ShapeMaterial.Name != changed[o.Name]: errs.append(f"{o.Label}: {o.ShapeMaterial.Name}, wanted {changed[o.Name]}")
        rows.append(f"{o.Label}\t{path(o)}\t{o.ShapeMaterial.Name}")
    open(WORK + "/materials.tsv", "w").write("label\tgroup path\tShapeMaterial\n" + "\n".join(sorted(rows)) + "\n")
    left = sum(1 for o in leaves if o.ShapeMaterial.Name == 'Default')
    log(f"solids still on Default: {left} of {len(leaves)}")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
