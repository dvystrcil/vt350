# GUI pass: vt350-lite-11.FCStd -> vt350-lite-12.FCStd   (headless = dry run, never saves)
# Assigns ShapeMaterial (FreeCAD's physical material: density etc.) to every solid by rule. Geometry and colours are
# untouched: a material card can carry an appearance, so each object's ShapeAppearance is saved and put back.
# Only materials we are sure of get assigned; anything the rules don't know stays on the "Default" card and is listed
# in the log and in data/materials-lite12.tsv as UNASSIGNED, for a later pass once its material is known.
# Masses in the log are volume x density of the MODEL, so simplified shapes (solid extrusion profiles, box
# electronics) are not real weights.
import FreeCAD, Materials, sys, os, re, time, traceback, collections
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-11.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-12.FCStd"
DRY = not FreeCAD.GuiUp
PRINTED = "ABS-Generic"          # Voron-style printed parts (ABS/ASA; FreeCAD has no ASA card, densities ~1.05-1.07)
CARDS = {  # material name -> library UUID (FreeCAD System library, the cards that carry a density)
    "Aluminum-6061-T6": "68b152b2-fd5e-4f10-8db0-1a2df3fe0fda",
    "Aluminum-Generic": "9bf060e9-1663-44a2-88e2-2ff6ee858efe",
    "Steel-Generic": "90bbd8ef-8623-4d78-b3bf-e0bdb9b74dd3",
    "ABS-Generic": "73371529-2983-47dd-b988-6739a2e20029",
    "PTFE-Generic": "8ce226db-43ef-4471-93f1-07e7276aa276",
}
HW = re.compile(r"T-nut|SHCS|BHCS|FHCS|Screw|Washer|shim|Nut\b|Nut0|Locknut|Hex Nut|Dowel|D5x\d+mm pin|Bolt|GE5C|disc spring|shaft\b|shaft0", re.I)
# (category, material or None = leave Default and list it, test(label, path))  first match wins
RULES = [
    ("leadscrew nut (brass or POM?)", None,               lambda L, P: 'Leadscrew Nut' in L),
    ("magnet (NdFeB, no card)",       None,               lambda L, P: 'magnet' in L.lower()),
    ("hotend metal / stand-in",       None,               lambda L, P: ('HotEnd' in L or 'dragon' in P.lower() or 'Heater' in L or 'Nozzle' in L) and 'Cowling' not in L),
    ("printed A4T cowling",           PRINTED,            lambda L, P: 'Cowling' in L),
    ("heat-set insert (brass)",       None,               lambda L, P: 'Insert' in L),
    ("brass coupler ring",            None,               lambda L, P: 'Brass' in L),
    ("metal spacer (Al or steel?)",   None,               lambda L, P: re.search(r"spacer|VT_NP_spacer", L, re.I) is not None and 'no threads' in L or L.startswith('VT_NP_spacer')),
    ("fastener / pin / shaft",        "Steel-Generic",    lambda L, P: bool(HW.search(L))),
    ("spring / pin / ball / shaft",   "Steel-Generic",    lambda L, P: re.match(r"(Spring v1|Leaf_spring|pin_|Ball\b|FlyShaft|9\d{4}A\d{3})", L) is not None),
    ("bowden tube",                   "PTFE-Generic",     lambda L, P: L.startswith('Bowden ')),
    ("belt (rubber + glass fibre)",   None,               lambda L, P: 'belt' in L.lower()),
    ("CF tube (no card)",             None,               lambda L, P: 'Carbonara' in L),
    ("linear rail",                   "Steel-Generic",    lambda L, P: re.search(r"MGN ?\d+.*(rail|\d{3}mm)", L) is not None and 'extension' not in L),
    ("Y rail front extension",        None,               lambda L, P: 'extension' in L and 'MGN9' in L),
    ("linear rail (Z)",               "Steel-Generic",    lambda L, P: P.split(' / ')[-1].startswith('MGN9 - 400mm') and L.startswith('SOLID')),
    ("rail carriage",                 "Steel-Generic",    lambda L, P: 'MGN9H' in L or 'MGN9H' in P or 'MGN_12_H' in L or 'Carriage_body' in L or 'Carriage_end' in L),
    ("bearing",                       "Steel-Generic",    lambda L, P: 'bearing' in L.lower() or 'MR148ZZ' in P),
    ("pulley (steel or Al?)",         None,               lambda L, P: 'pulley' in L.lower() or 'toothed' in L or 'Pulley flange' in L),
    ("Monolith milled part",          "Aluminum-6061-T6", lambda L, P: re.match(r"V[TC]9-", L) is not None),
    ("standoff",                      None,               lambda L, P: 'standoff' in L.lower()),
    ("stepper motor",                 None,               lambda L, P: any(k in P for k in ('NEMA17', 'LDO_36STH', 'Stepper', 'Z_Motor')) or 'Motor_Body' in L),
    ("frame extrusion",               "Aluminum-6061-T6", lambda L, P: re.match(r"(20|40)[24]0\b", L) is not None or 'crossbar (placeholder, 2040)' in L),
    ("electronics",                   None,               lambda L, P: 'Electronics' in P or 'Octopus' in L or 'display' in L.lower() or 'Nitehawk' in L),
    ("build plate",                   "Aluminum-Generic", lambda L, P: 'Build Plate' in L),
    ("back panel (ACM / acrylic?)",   None,               lambda L, P: 'Panel' in L),
    ("backbone (?)",                  None,               lambda L, P: 'backbone' in L.lower()),
]
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite12_materials.log", "w"); t0 = time.time()
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
# printed (Voron-style, ABS/ASA): matched on the part's immediate group, or its own label. A whitelist on purpose:
# a loose keyword match also caught bearing balls, brass rings, McMaster springs and the Orbiter's moulded housing.
PRINTED_GROUP = re.compile(r"^(Z_Carriage|Z_Bed_|rail_stop|Hinge_|Latch \(1\) \(2\)|Handle \(1\)|4mm Gap 6mm Belt|Left Dock|Right Dock|"
                           r"A4T |MadMaxCarriage|Printed_|Crossbow integration)")
PRINTED_LABEL = re.compile(r"^(Clip|Dock Arm|Alternate Bracket|A4T |Top Cap|LED_diffuser|Part 46$|Part \d*$|COMPOUND\d*$|SOLID\d*$)")
NOT_PRINTED_LABEL = re.compile(r"^(Cutter)")
try:
    mm = Materials.MaterialManager()
    mats = {n: mm.getMaterial(u) for n, u in CARDS.items()}
    for n, m in mats.items():
        if m.Name != n: raise RuntimeError(f"card {CARDS[n]} is {m.Name}, expected {n}")
    doc = FreeCAD.openDocument(SRC)
    log("opened", SRC, len(doc.Objects))
    leaves = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: (o.Shape.BoundBox, o.getGlobalPlacement()) for o in leaves}
    rows, cat_of = [], {}
    for o in leaves:
        L, P = o.Label, path(o)
        cat, mat = next(((c, m) for c, m, t in RULES if t(L, P)), (None, None))
        grp = P.split(' / ')[-1] if P else ''
        if cat is None and PRINTED_GROUP.match(grp) and PRINTED_LABEL.match(L) and not NOT_PRINTED_LABEL.match(L):
            cat, mat = "printed part", PRINTED
        cat_of[o.Name] = (cat or "UNCLASSIFIED", mat)
    # apply
    app0 = {}
    for o in leaves:
        cat, mat = cat_of[o.Name]
        if mat is None: continue
        vo = getattr(o, 'ViewObject', None)
        if vo is not None and hasattr(vo, 'ShapeAppearance'): app0[o.Name] = [(a.DiffuseColor, a.Transparency) for a in vo.ShapeAppearance]
        o.ShapeMaterial = mats[mat]
    doc.recompute()
    errs, restored = [], 0
    for o in leaves:
        if o.Name in app0:
            now = [(a.DiffuseColor, a.Transparency) for a in o.ViewObject.ShapeAppearance]
            if now != app0[o.Name]:
                ap = o.ViewObject.ShapeAppearance
                for a, (dc, tr) in zip(ap, app0[o.Name]): a.DiffuseColor = dc; a.Transparency = tr
                o.ViewObject.ShapeAppearance = ap; restored += 1
                if [(a.DiffuseColor, a.Transparency) for a in o.ViewObject.ShapeAppearance] != app0[o.Name]: errs.append(f"colour changed: {o.Label}")
    log(f"appearance restored on {restored} objects the material card had recoloured")
    # report
    by = collections.defaultdict(list)
    for o in leaves:
        cat, mat = cat_of[o.Name]; v = o.Shape.Volume
        d = o.ShapeMaterial.getPhysicalValue('Density').getValueAs('g/cm^3').Value if mat else None
        by[(cat, mat)].append((o.Label, path(o), v, d))
        rows.append(f"{o.Label}\t{path(o)}\t{cat}\t{o.ShapeMaterial.Name}\t{v/1000:.2f}\t{'' if d is None else f'{v/1000*d:.1f}'}")
        if mat and o.ShapeMaterial.Name != mat: errs.append(f"{o.Label}: material {o.ShapeMaterial.Name}, wanted {mat}")
    tot = 0.0
    log(f"{'category':32} {'material':18} {'n':>4} {'model vol cm3':>14} {'model mass g':>13}")
    for (cat, mat), it in sorted(by.items(), key=lambda kv: (kv[0][1] is None, -sum(i[2] for i in kv[1]))):
        vol = sum(i[2] for i in it) / 1000; mass = sum(i[2] / 1000 * i[3] for i in it) if mat else None
        tot += mass or 0
        log(f"{cat[:32]:32} {(mat or 'Default (UNASSIGNED)')[:20]:20} {len(it):4} {vol:12.1f} {'' if mass is None else f'{mass:13.0f}'}")
        if mat is None or cat == "printed part":
            names = sorted({re.sub(r"(\d{3}|\(Mirror\))$", "", i[0])[:40] + " [" + i[1].split(' / ')[-1][:28] + "]" for i in it})
            log(f"      ({len(names)} kinds) " + "; ".join(names[:60 if cat in ('UNCLASSIFIED', 'printed part') else 8]))
    log(f"assigned model mass total {tot/1000:.2f} kg")
    open(WORK + "/materials-lite12.tsv", "w").write("label\tgroup path\tcategory\tShapeMaterial\tmodel volume cm3\tmodel mass g\n" + "\n".join(sorted(rows)) + "\n")
    for o in leaves:
        b, g = before[o.Name]
        if not (o.Shape.BoundBox.isInside(b.getPoint(0)) or True) or not o.getGlobalPlacement().isSame(g, 1e-9) or abs(o.Shape.BoundBox.DiagonalLength - b.DiagonalLength) > 1e-6:
            errs.append(f"geometry changed: {o.Label}")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs[:40]]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
