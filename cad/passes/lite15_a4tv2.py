# GUI pass: vt350-lite-14.FCStd -> vt350-lite-15.FCStd   (headless = dry run, never saves)
# A4Tv2 replaces the A4T v1 on both toolheads.
#  Source: DW-Tas/A4Tv2 (CC BY-NC-SA 4.0), CAD/A4Tv2_assembly.zip -> A4Tv2_assembly.step, read from $VT350_DL/A4Tv2.
#  Variant: Dragon Rapido UHF body, Orbiter (o2), XOL carriage mount; 4010 part-cooling ducts; UHF hotend-fan duct
#  + 2510 fan; low LED; Crossbow extruder adapter + Crossbow parts; carriage/duct/HEF/Orbiter hardware; Dragon Ace
#  hotend with its 3 mm spacer (the assembly's own hotend model). Part-cooling fans: the assembly only models 4015s, so
#  none are placed (the v1 model had none either).
#  Placement: the assembly is upright with its front at -Y like the printer, so only a translation per head. X/Z from
#  the MadMax plate's XOL holes (upper pair 31.0 apart, at the A4Tv2's (+-15.5, -5.70)); Y so the A4Tv2's back face
#  sits where the v1's did. All three plate hole pairs are checked against the A4Tv2's screws.
#  Removed: the v1 A4T group (cowling, HE duct, LED, Dragon mock-up) and the v1 Crossbow integration parts.
#  The Orbiter moves onto the new adapter (filament axis over the new hotend, lowered/raised to contact); bowden tubes
#  rebuilt. Reports the new nozzle position, print height and Y margins.
import FreeCAD, Part, Import, sys, os, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
DL = os.environ.get("VT350_DL", "/tmp/claude-1000/-home-dan-Code/49170e9e-d71c-4cd7-8f69-23f113691ee5/scratchpad/dl_a4t")
ASM = os.path.join(DL, "asm", "A4Tv2_assembly.step")
SRC = "/home/dan/Documents/VT350/vt350-lite-14.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-15.FCStd"
DRY = not FreeCAD.GuiUp
HEADS = [  # toolhead group, v1 A4T group, v1 Crossbow group, Orbiter group, MadMax plate
    ("Left Toolhead", "A4T Assembly fixed v1", "Crossbow integration CAD v1", "Orbiter 2.5", "Plate"),
    ("Right Toolhead", "A4T Assembly fixed v001", "Crossbow integration CAD v001", "Orbiter 2.5 (1)", "Plate(Mirror)"),
]
SEL = {  # assembly group -> leaf labels (None = every leaf below it)
    "Standard_main_bodies_UHF": ["main-body_dragon-rapido-UHF_o2_xol"],
    "Ducts_PCF": ["[a]_Duct-4010-left", "[a]_Duct-4010-right"],
    "Ducts_HEF_UHF": ["Duct-HEF-Dragon-UHF001"],
    "HEF_UHF": None, "LED_low": None,
    "Extruder_Adapters_Crossbow": ["[a]_orbiter-crossbow-adapter_o2_xol"],
    "crossbow": None, "Dragon_Ace": None,
    "Hardware_Xol-Carriage": None, "Hardware_Carriage": None, "Hardware_HEF_UHF": None, "Hardware_PCF_Ducts": None, "Hardware_Orbiter": None,
}
BODY = "main-body_dragon-rapido-UHF_o2_xol"
MOUNT = [(15.50, -5.70), (16.20, 2.67), (16.25, -49.00)]   # A4Tv2 carriage screws (half-spacing, Z) in the assembly frame
PRINTED = ("main-body", "Duct", "LED_Carrier", "LED_diffuser", "LED_filter", "adapter")
CNC_AL = ("Crossbow - ",)     # the assembly's Crossbow is DW-Tas's aluminium CNC cutter (same parts/volumes as its CNC STEP)
HW = ('screw', 'Screw', 'nut', 'Nut', 'washer', 'Washer', 'SHCS', 'BHCS', 'Magnet', 'magnet', 'blade', 'D2.3L7.5')
V1_NOZZLE_Z, V1_PRINT_H = 380.80, 347.8      # lite-10 nozzle bottom and max print height
# Known, kept visible on purpose: on the left head the Crossbow lever (sticks out 38 mm to -X) runs into the left dock's
# Dock Bracket and Alternate Bracket. A real design conflict for the user to resolve, not a modelling error.
KNOWN = {("Crossbow - Lever", "Dock Bracket"), ("Crossbow - Lever", "Alternate Bracket v1")}
INLETS = {"Left": "4mm Bowden Coupler v1 (1)", "Right": "4mm Bowden Coupler v1 (1) (1)"}
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite15_a4tv2.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
_BOX = {}
def gbox(o):
    k = (o.Name, tuple(o.getGlobalPlacement().toMatrix().A))
    if k not in _BOX:
        s = gshape(o)
        try: _BOX[k] = s.optimalBoundingBox(True, False)
        except Exception: _BOX[k] = s.BoundBox
    return _BOX[k]
def parent_of(o):
    return next((x for x in o.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))
                 and o in getattr(x, 'Group', [])), None)
def ancestors(o):
    r = []; p = parent_of(o)
    while p is not None: r.append(p); p = parent_of(p)
    return r
def frame_of_parent(par):
    """global placement of the coordinate frame a child of `par` lives in"""
    if par is None: return FreeCAD.Placement()
    if par.isDerivedFrom('App::Part'): return par.getGlobalPlacement()
    for p in ancestors(par):
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
    return FreeCAD.Placement()
def container_global(o): return frame_of_parent(parent_of(o))
def descendants(g):
    out = []
    for c in getattr(g, 'Group', []):
        out.append(c); out += descendants(c)
    return out
def is_leaf(o): return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
def shifted(b, v): return FreeCAD.BoundBox(b.XMin + v.x, b.YMin + v.y, b.ZMin + v.z, b.XMax + v.x, b.YMax + v.y, b.ZMax + v.z)
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax), (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
def translate_global(o, T):
    par_g = container_global(o); g = o.getGlobalPlacement()
    o.Placement = par_g.inverse().multiply(FreeCAD.Placement(T, FreeCAD.Rotation())).multiply(g)
def one(label, cond=lambda o: True):
    c = [o for o in doc.getObjectsByLabel(label) if cond(o)]
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {label!r}")
    return c[0]
def overlaps(objs_a, objs_all, skip=lambda a, b: False):
    out = {}
    for a in objs_a:
        sa = None
        for b in objs_all:
            if a.Name == b.Name or skip(a, b) or not gbox(a).intersect(gbox(b)): continue
            try:
                sa = sa or gshape(a); v = sa.common(gshape(b)).Volume
            except Exception: continue
            if v > 1.0: out[(a.Name, b.Name)] = v
    return out
def is_hw(lab): return any(k in lab for k in HW)
def yholes(s, r=(1.4, 1.8)):
    out = []
    for f in s.Faces:
        su = f.Surface
        if isinstance(su, Part.Cylinder) and r[0] <= su.Radius <= r[1] and abs(abs(su.Axis.y) - 1) < 1e-3:
            out.append((su.Center.x, su.Center.z))
    return out
def add_shape(s, label, parent):
    n = doc.addObject('Part::Feature', 'A4Tv2'); loc = s.copy(); loc.Placement = frame_of_parent(parent).inverse().multiply(loc.Placement)
    n.Shape = loc; parent.addObject(n); n.Label = label; return n
try:
    errs, notes = [], []
    # ---- the A4Tv2 parts, from the assembly
    adoc = FreeCAD.newDocument("a4tv2")
    Import.insert(ASM, adoc.Name); adoc.recompute()
    picked = []
    for o in adoc.Objects:
        if not (o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids): continue
        anc = [a.Label.replace(' <1>', '') for a in [o] + ancestors(o)]
        for g, labs in SEL.items():
            if g in anc[1:] and (labs is None or o.Label in labs):
                s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); picked.append((o.Label, g, s)); break
    log(f"A4Tv2 assembly: picked {len(picked)} solids from {len(SEL)} groups: " + ", ".join(f"{g} {sum(1 for p in picked if p[1] == g)}" for g in SEL))
    for g in SEL:
        if not any(p[1] == g for p in picked): errs.append(f"nothing picked from {g}")
    body = [p for p in picked if p[0] == BODY]
    if len(body) != 1: raise RuntimeError(f"{len(body)} bodies")
    bodyb = body[0][2].BoundBox
    # the spacer must be in the hotend stack
    if not any('spacer' in p[0] for p in picked): errs.append("no hotend spacer in the picked parts")
    nozzle_a = min((p for p in picked if 'Nozzle' in p[0] or 'nozzle' in p[0]), key=lambda p: p[2].BoundBox.ZMin)[2].BoundBox
    FreeCAD.closeDocument(adoc.Name)
    # ---- the printer
    doc = FreeCAD.openDocument(SRC); log("opened", SRC, len(doc.Objects))
    leaves0 = list({o.Name: o for o in doc.Objects if is_leaf(o)}.values())
    before = {o.Name: gbox(o) for o in leaves0}; label0 = {o.Name: o.Label for o in leaves0}
    tubes0 = [o for o in leaves0 if o.Label.startswith('Bowden ')]; tube_names = {t.Name for t in tubes0}
    removed, moved, new = set(), {}, []
    for th, a4t, xb, orb, plate in HEADS:
        TH, A1, XB, OR, PL = one(th), one(a4t), one(xb), one(orb), one(plate)
        cow = [x for x in descendants(A1) if is_leaf(x) and x.Label.startswith("A4T Cowling")]
        if len(cow) != 1: raise RuntimeError(f"{th}: {len(cow)} v1 cowlings")
        v1b = gbox(cow[0])
        v1noz = min((x for x in descendants(A1) if is_leaf(x) and 'Nozzle' in x.Label), key=lambda x: gbox(x).ZMin)
        v1n = gbox(v1noz)
        # plate holes -> translation
        ph = yholes(gshape(PL))
        up = [h for h in ph if abs(abs(h[0] - sum(x for x, _ in ph) / len(ph)) - 15.5) < 0.6]
        zs = sorted({round(z, 1) for _, z in ph})
        pairs = {}
        for x, z in ph:
            pairs.setdefault(round(z, 1), set()).add(round(x, 2))
        xc = None
        for z, xsx in pairs.items():
            if len(xsx) == 2 and abs(abs(max(xsx) - min(xsx)) - 31.0) < 0.05: xc, zu = (max(xsx) + min(xsx)) / 2, z
        if xc is None: raise RuntimeError(f"{plate}: no 31.0 mm hole pair")
        T = V(xc, v1b.YMax - bodyb.YMax, zu - MOUNT[0][1])
        log(f"{th}: plate XOL pair centre x {xc:.2f}, z {zu:.2f}; A4Tv2 translation ({T.x:.2f}, {T.y:.2f}, {T.z:.2f})")
        for hx, hz in MOUNT:
            gz = hz + T.z
            ok = any(abs(z - gz) < 0.15 and abs(abs(xs_ - xc) - hx) < 0.15 for xs_, z in ph)
            log(f"   A4Tv2 screw pair +-{hx:.2f} at z {gz:.2f}: plate hole {'found' if ok else 'MISSING'}")
            if not ok: errs.append(f"{th}: no plate hole for the A4Tv2 screw pair +-{hx} at z {gz:.2f}")
        # remove v1 parts
        gone = [x for g in (A1, XB) for x in descendants(g) if is_leaf(x)]
        removed |= {x.Name for x in gone}
        for g in (A1, XB):
            for x in reversed(descendants(g)):
                try: doc.removeObject(x.Name)
                except Exception: pass
        A1.Label = a4t.replace("A4T Assembly fixed", "A4Tv2 (DW-Tas, CC BY-NC-SA 4.0)")
        XB.Label = xb + " (v1, replaced by the A4Tv2 Crossbow parts)"
        for lab, g, s in picked:
            s2 = s.copy(); s2.translate(T)
            n = add_shape(s2, lab, A1); new.append(n)
        nz = T + V((nozzle_a.XMin + nozzle_a.XMax) / 2, (nozzle_a.YMin + nozzle_a.YMax) / 2, nozzle_a.ZMin)
        log(f"   nozzle: v1 ({(v1n.XMin + v1n.XMax) / 2:.2f}, {(v1n.YMin + v1n.YMax) / 2:.2f}, {v1n.ZMin:.2f}) -> A4Tv2 ({nz.x:.2f}, {nz.y:.2f}, {nz.z:.2f})")
        # Orbiter: filament axis over the new hotend, then seat it on the new adapter/crossbow
        dxy = V(nz.x - (v1n.XMin + v1n.XMax) / 2, nz.y - (v1n.YMin + v1n.YMax) / 2, 0)
        orb_l = [x for x in descendants(OR) if is_leaf(x) and x.Name not in tube_names]
        seat = [n for n in new[-len(picked):] if any(k in n.Label for k in ('adapter', 'Crossbow - Main', 'Crossbow - Top', 'Crossbow - Lever', 'main-body'))]
        doc.recompute(); _BOX.clear()
        def hits(dz):
            for o in orb_l:
                so = gshape(o); so.translate(dxy + V(0, 0, dz)); bo = so.BoundBox
                for sn in seat:
                    if not bo.intersect(gbox(sn)): continue
                    try:
                        if so.common(gshape(sn)).Volume > 0.5: return True
                    except Exception: pass
            return False
        if hits(0.0):
            dz = 0.0
            while hits(dz) and dz < 15: dz += 0.1
        else:
            dz = 0.0
            while not hits(dz - 0.1) and dz > -15: dz -= 0.1
        log(f"   Orbiter: moved ({dxy.x:+.2f}, {dxy.y:+.2f}, {dz:+.2f}) to sit on the new adapter")
        if abs(dz) >= 14.9: errs.append(f"{th}: Orbiter found no seat")
        Tor = dxy + V(0, 0, dz)
        translate_global(OR, Tor)
        for x in orb_l: moved[x.Name] = Tor
        notes.append((th, nz, Tor))
    doc.recompute(); _BOX.clear()
    # materials + colours for the new parts
    try:
        import Materials
        mm = Materials.MaterialManager()
        abs_m = mm.getMaterial("73371529-2983-47dd-b988-6739a2e20029"); st_m = mm.getMaterial("90bbd8ef-8623-4d78-b3bf-e0bdb9b74dd3")
        al_m = mm.getMaterial("9bf060e9-1663-44a2-88e2-2ff6ee858efe")
        for n in new:
            if is_hw(n.Label): n.ShapeMaterial = st_m
            elif any(k in n.Label for k in CNC_AL): n.ShapeMaterial = al_m
            elif any(k in n.Label for k in PRINTED): n.ShapeMaterial = abs_m
    except Exception as e: log("materials not set:", e)
    # ---- bowden tubes (the couplers moved with the Orbiters)
    made = []
    for t in tubes0:
        side = t.Label.split()[1]
        cb = gbox(one(INLETS[side])); P0 = V((cb.XMin + cb.XMax) / 2, (cb.YMin + cb.YMax) / 2, cb.ZMax)
        P1 = V(t.ExitPoint); ED = V(t.ExitDir); a_ = t.HandleInlet.Value; b_ = t.HandleExit.Value; BY = t.Beyond.Value; OD = t.OD.Value
        c = Part.BezierCurve(); c.setPoles([P0, P0 + V(0, 0, a_), P1 - ED * b_, P1])
        path = Part.Wire([c.toShape(), Part.LineSegment(P1, P1 + ED * BY).toShape()])
        tube = path.makePipeShell([Part.Wire(Part.makeCircle(OD / 2, P0, V(0, 0, 1)))], True, True)
        rmin = min(1 / max(c.curvature(i / 400), 1e-12) for i in range(401))
        props = {p: getattr(t, p) for p in ('OD', 'Inlet', 'ExitPoint', 'ExitDir', 'HandleInlet', 'HandleExit', 'Beyond', 'MinBendRadius', 'PathLength')}
        props.update(Inlet=P0, MinBendRadius=rmin, PathLength=path.Length)
        par = parent_of(t); doc.removeObject(t.Name)
        n = add_shape(tube, f"Bowden {side}", par); n.Label = f"Bowden {side}"
        for p, v in props.items():
            n.addProperty('App::PropertyVector' if p in ('Inlet', 'ExitPoint', 'ExitDir') else 'App::PropertyLength', p, 'Bowden',
                          'route parameters (global mm); regenerate by script for other poses'); setattr(n, p, v)
        doc.recompute(); _BOX.clear()
        log(f"tube {side}: inlet ({P0.x:.2f}, {P0.y:.2f}, {P0.z:.2f}); starts {gbox(n).ZMin - P0.z:+.2f} from it; min bend R {rmin:.1f}; valid {tube.isValid()}")
        if abs(gbox(n).ZMin - P0.z) > 0.05 or not tube.isValid() or rmin < 100: errs.append(f"tube {side}: bad rebuild")
        made.append(n)
    # ---- collisions: new parts and moved Orbiters vs everything else
    now = {o.Name: o for o in doc.Objects if is_leaf(o)}; allnow = list(now.values())
    newn = {n.Name for n in new}
    ov = overlaps(new, allnow, skip=lambda a, b: b.Name in newn)
    log(f"A4Tv2 parts vs the rest of the printer: {len(ov)} overlaps > 1 mm3")
    for (a_, b_), v in sorted(ov.items(), key=lambda kv: -kv[1]):
        A, B = now[a_], now[b_]; p = parent_of(B)
        kind = "hardware" if is_hw(A.Label) or is_hw(B.Label) else "PART"
        log(f"     {kind:8} {v:8.1f} mm3  {A.Label} x {B.Label} [{p.Label if p else ''}]")
        if kind == "PART" and (A.Label, B.Label) not in KNOWN: errs.append(f"{A.Label} overlaps {B.Label} ({v:.1f} mm3)")
        elif kind == "PART": log(f"              ^ KNOWN design conflict, left visible in the model")
    tov = overlaps(made, allnow, skip=lambda a, b: b in made or b.Label in INLETS.values())
    log(f"tubes: {len(tov)} overlaps")
    for (a_, b_), v in tov.items(): errs.append(f"{now[a_].Label} overlaps {now[b_].Label} ({v:.1f} mm3)")
    # ---- what it means
    for th, nz, Tor in notes:
        dzn = nz.z - V1_NOZZLE_Z
        log(f"{th}: nozzle bottom Z {nz.z:.2f} ({dzn:+.2f} vs v1) -> max print height ~{V1_PRINT_H - dzn:.1f} mm (was {V1_PRINT_H})")
    dy = notes[0][1].y - (-44.08)
    log(f"nozzle Y vs v1: {dy:+.2f} mm (negative = further forward of the carriage): on-steel margin at the plate front "
        f"+0.28 -> {0.28 - dy:+.2f}; nozzle vs plate rear edge -8.2 -> {-8.2 + dy:+.2f}")
    # ---- verify
    for nm, b in before.items():
        if nm in removed or nm in tube_names: continue
        if nm not in now: errs.append(f"lost {label0[nm]}"); continue
        exp = shifted(b, moved[nm]) if nm in moved else b
        if not close(gbox(now[nm]), exp): errs.append(f"{'moved wrongly' if nm in moved else 'changed'}: {now[nm].Label}")
    log(f"removed {len(removed)} v1 solids, added {len(new)} A4Tv2 solids")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
