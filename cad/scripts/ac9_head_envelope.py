# Read-only (headless): #19 AC9 head envelope. A4Tv2 parts by exact name + the official Orbiter 2.5/OSS/O2S
# assembly seated on the orbiter-crossbow adapter by its 2 M3 holes and filament axis; then the exact
# per-height depth from 1 mm slabs. Input STEP paths are the constants below (downloaded, not in git).
# Read-only AC9: A4Tv2 (our variant, explicit include list) + Orbiter 2.5/OSS/O2S assembly seated on the
# orbiter-crossbow adapter by its 2 M3 holes + filament axis. Prints the head envelope and any overlaps.
import FreeCAD, Part, Import, os, traceback, collections
V = FreeCAD.Vector
out = open("/tmp/claude-1000/-home-dan-Code/49170e9e-d71c-4cd7-8f69-23f113691ee5/scratchpad/out/ac9_section.txt", "w")
def w(*a): out.write(" ".join(str(x) for x in a) + "\n"); out.flush()
def chain(o):
    n = [o.Label]; p = o
    while True:
        par = next((x for x in p.InList if x.isDerivedFrom('App::Part') and p in getattr(x, 'Group', [])), None)
        if par is None: return list(reversed(n))
        n.append(par.Label); p = par
INCLUDE = ["Standard_main_bodies_UHF <1> / main-body_dragon-rapido-UHF_o2_xol",
                      "Extruder_Adapters_Crossbow <1> / [a]_orbiter-crossbow-adapter_o2_xol",
           "Ducts_PCF <1> / [a]_Duct-4010-left", "Ducts_PCF <1> / [a]_Duct-4010-right", "Ducts_HEF_UHF <1>",
           "Hotend_Fan <1> / HEF_UHF <1>", "Part_Fans <1>", "hotends <1> / Dragon_Ace <1>", "crossbow <1>",
           "LED_high <1>", "Nozzle_LEDs <1>",
           "Hardware_Carriage <1>", "Hardware_HEF_UHF <1>", "Hardware_Orbiter <1>", "Hardware_PCF_Ducts <1>", "Hardware_Xol-Carriage <1>"]
def picked(c):
    p = ' / '.join(c)
    for k in INCLUDE:
        if k in p:
            # exact leaf match for the variant names (avoid '..._left_builtin-flow-inhibitor')
            if k.startswith(('Standard_', 'Extruder_', 'Ducts_PCF')) and not any(p.endswith(k) or (k + ' /') in p for _ in [0]):
                continue
            return k
    return None
def solids(path):
    doc = FreeCAD.newDocument(os.path.basename(path).split('.')[0].replace('-', '_')[:20])
    Import.insert(path, doc.Name)
    r = []
    for o in doc.Objects:
        if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids:
            s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); r.append((chain(o), s))
    return r
try:
    a4t = [(c, s, picked(c)) for c, s in solids("/tmp/claude-1000/-home-dan-Code/b279da99-5634-4c88-a9ae-89fd7f47818b/scratchpad/dl-a4tv2-asm/A4Tv2_assembly.step")]
    a4t = [(c, s, k) for c, s, k in a4t if k]
    used = collections.Counter(k for _, _, k in a4t)
    w("A4Tv2 parts used per include key:"); [w(f"  {used.get(k,0):3}  {k}") for k in INCLUDE]
    adapter = next(s for c, s, k in a4t if k.endswith('orbiter-crossbow-adapter_o2_xol'))
    body = next(s for c, s, k in a4t if k.endswith('main-body_dragon-rapido-UHF_o2_xol'))
    o2s = solids("/tmp/claude-1000/-home-dan-Code/b279da99-5634-4c88-a9ae-89fd7f47818b/scratchpad/dl-o2s/orbiter25_oss_o2s.step")
    hub = next(s for c, s in o2s if any('HubHousing' in x for x in c))
    # seat: filament axis (1.34,-7.88) -> (0,0); housing underside -> adapter top
    T = V(-1.34, 7.88, adapter.BoundBox.ZMax - hub.BoundBox.ZMin)
    w(f"translation for the O2S assembly: {T}")
    moved = []
    for c, s in o2s:
        s = s.copy(); s.translate(T); moved.append((c, s))
    hub2 = hub.copy(); hub2.translate(T)
    w(f"hub vs adapter overlap {hub2.common(adapter).Volume:.2f} mm3; lowered 0.3 mm: {hub2.copy().translated(V(0,0,-0.3)).common(adapter).Volume:.2f} mm3 (>0 = faces touch)")
    # check M3 holes line up: hub holes r=1.6 vs adapter holes r=1.7
    def vh(s, r0, r1):
        return sorted({(round(f.Surface.Center.x, 2), round(f.Surface.Center.y, 2)) for f in s.Faces
                       if isinstance(f.Surface, Part.Cylinder) and abs(abs(f.Surface.Axis.z) - 1) < 1e-6 and r0 <= f.Surface.Radius <= r1})
    w("adapter M3 holes", vh(adapter, 1.65, 1.75), " hub M3 holes after move", vh(hub2, 1.55, 1.65))
    # overlaps O2S parts vs A4Tv2 parts
    hits = []
    for c2, s2 in moved:
        for c1, s1, k in a4t:
            if not s2.BoundBox.intersect(s1.BoundBox): continue
            try: v = s2.common(s1).Volume
            except Exception: continue
            if v > 0.5: hits.append((v, c2[-1], c1[-1]))
    w(f"O2S-assembly vs A4Tv2 overlaps > 0.5 mm3: {len(hits)}")
    for v, a, b in sorted(hits, reverse=True)[:25]: w(f"   {v:8.1f}  {a[:45]:45} x {b[:50]}")
    head = FreeCAD.BoundBox(); a4b = FreeCAD.BoundBox(); o2b = FreeCAD.BoundBox()
    for _, s, _ in a4t: a4b.add(s.BoundBox)
    for _, s in moved: o2b.add(s.BoundBox)
    head.add(a4b); head.add(o2b)
    def bx(b): return f"X {b.XMin:7.1f}..{b.XMax:6.1f} ({b.XLength:5.1f})  Y {b.YMin:7.1f}..{b.YMax:6.1f} ({b.YLength:5.1f})  Z {b.ZMin:7.1f}..{b.ZMax:6.1f} ({b.ZLength:5.1f})"
    w("A4Tv2 parts only      ", bx(a4b)); w("Orbiter+OSS+O2S placed", bx(o2b)); w("WHOLE HEAD            ", bx(head))
    w(f"main body             ", bx(body.BoundBox))
    w("parts reaching behind the main body's rear face (Y > %.1f):" % body.BoundBox.YMax)
    for c, s in sorted(moved, key=lambda cs: -cs[1].BoundBox.YMax):
        b = s.BoundBox
        if b.YMax > body.BoundBox.YMax + 0.1 and s.Volume > 20: w(f"   {' / '.join(c[1:])[:70]:70} {bx(b)}")

    # --- Z seat: lower the O2S assembly until the housing touches the adapter ---
    lo, hi = 0.0, 15.0
    def ov(d):
        h = hub2.copy(); h.translate(V(0, 0, -d)); return h.common(adapter).Volume
    if ov(hi) < 1e-3: w("housing never touches the adapter within 15 mm")
    else:
        for _ in range(30):
            m = (lo + hi) / 2
            if ov(m) > 1e-3: hi = m
            else: lo = m
        w(f"Z seat: housing first touches the adapter after lowering {lo:.2f} mm")
    seat = lo
    # --- exact per-height depth: intersect every part with 1 mm slabs ---
    shapes = [s for _, s, _ in a4t] + [s.copy().translated(V(0, 0, -seat)) for _, s in moved]
    body_rear = body.BoundBox.YMax
    rows = []
    for zi in range(-66, 105):
        z0, z1 = float(zi), zi + 1.0
        slab = Part.makeBox(400, 400, 1.0, V(-200, -200, z0))
        ys = []
        for s in shapes:
            bb = s.BoundBox
            if bb.ZMax <= z0 or bb.ZMin >= z1: continue
            try:
                c = s.common(slab)
                if c.Volume > 1e-4: ys.append((c.BoundBox.YMin, c.BoundBox.YMax))
            except Exception: pass
        if ys: rows.append((zi, min(y[0] for y in ys), max(y[1] for y in ys)))
    worst = max(rows, key=lambda r: r[2] - r[1])
    w(f"EXACT per-height depth: max {worst[2]-worst[1]:.1f} mm at Z {worst[0]}..{worst[0]+1} (Y {worst[1]:.1f}..{worst[2]:.1f}); body rear face Y {body_rear:.1f}")
    for zi, y0, y1 in rows:
        if zi % 4 == 0 or worst[0] - 3 <= zi <= worst[0] + 3: w(f"   Z {zi:4}..{zi+1:<4} Y {y0:7.1f}..{y1:6.1f}  depth {y1-y0:5.1f}")
    # MadMax plate proxy (from lite-5-dan: Plate +3.5 mm behind the body rear over the body height, Plate Back
    # +13.0 mm over the body's top 9 mm)
    bz = body.BoundBox
    def plate_rear(z):
        r = None
        if bz.ZMin <= z <= bz.ZMax: r = body_rear + 3.5
        if bz.ZMax - 9 <= z <= bz.ZMax: r = body_rear + 13.0
        return r
    wp = max(((zi, y0, max(y1, plate_rear(zi + 0.5) or y1)) for zi, y0, y1 in rows), key=lambda r: r[2] - r[1])
    w(f"WITH MadMax plate proxy: max depth {wp[2]-wp[1]:.1f} mm at Z {wp[0]}..{wp[0]+1} (Y {wp[1]:.1f}..{wp[2]:.1f})")
    w("DONE")
except Exception:
    w("FAILED\n" + traceback.format_exc())
finally:
    out.close(); os._exit(0)
