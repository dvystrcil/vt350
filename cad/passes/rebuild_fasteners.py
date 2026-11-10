# GUI pass: vt350-lite.FCStd + fasteners.json -> vt350-lite-2.FCStd
# Adds Fasteners-workbench parts (Thread=False) where the STEP fasteners were,
# re-adds the 'keep' originals (T-nuts, square washers, self-tappers) from BREP,
# verifies every placement against the original geometry, then saves a NEW file.
import FreeCAD, FreeCADGui, Part, json, os, sys, time, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd
WORK = os.environ.get("VT350_WORK", os.path.expanduser("~/Code/vt350/cad/data"))  # data in, logs out

SCR = WORK
SRC = "/home/dan/Documents/VT350/vt350-lite.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-2.FCStd"
TOL = 0.5  # mm
log_f = open(SCR + "/rebuild.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()

Z = FreeCAD.Vector(0, 0, 1)
SCREWS = ('ISO4762', 'ISO7380-1', 'ISO10642', 'ISO4026')
PRETTY = {'ISO4762': 'SHCS', 'ISO7380-1': 'BHCS', 'ISO10642': 'FHCS', 'ISO4026': 'set screw',
          'ISO7089': 'washer', 'ISO4032': 'hex nut', 'ISO4035': 'thin hex nut', 'IUTHeatInsert': 'heat insert'}

def fmt(x):
    return f"{x:g}"

def set_length(o, want):
    """Set Length; use Custom when the standard table lacks it. Return the built length."""
    opts = o.getEnumerationsOfProperty('Length') if 'Length' in o.PropertiesList else None
    if opts is None:
        return None
    s = fmt(want)
    if s in opts:
        o.Length = s
    elif 'Custom' in opts and 'LengthCustom' in o.PropertiesList:
        o.Length = 'Custom'; o.LengthCustom = want
    return o.Length

def built_length(o):
    if 'Length' not in o.PropertiesList: return None
    if o.Length == 'Custom': return float(o.LengthCustom)
    try: return float(str(o.Length).replace('mm', '').strip())
    except ValueError: return None

try:
    recs = json.load(open(SCR + "/fasteners/fasteners.json"))
    doc = FreeCAD.openDocument(SRC)
    log("opened", len(doc.Objects), "objects;", len(recs), "records")
    root = next(o for o in doc.Objects if o.TypeId == 'App::Part' and not [p for p in o.InList if p.isDerivedFrom('App::Part')])
    groups = {}
    def group_for(rec):
        host = next((doc.getObject(n) for n in rec['chain'] if doc.getObject(n) is not None), root)
        g = groups.get(host.Name)
        if g is None:
            g = doc.addObject('App::DocumentObjectGroup', 'FastenersGroup'); g.Label = 'Fasteners'
            host.addObject(g); groups[host.Name] = g
        return host, g

    made, kept, skipped, bad, len_diff = 0, 0, 0, [], []
    checks = []
    for r in recs:
        if doc.getObject(r['name']) is not None:   # never removed from lite: leave it alone
            skipped += 1; continue
        host, g = group_for(r)
        inv = host.getGlobalPlacement().inverse()
        if r['kind'] == 'keep':
            s = Part.read(r['brep'] if os.path.isabs(r['brep']) else os.path.join(WORK, 'fasteners', r['brep']))
            o = doc.addObject('Part::Feature', 'KeptFastener'); o.Label = r['label']
            o.Shape = s; o.Placement = inv.multiply(s.Placement)
            g.addObject(o); kept += 1; continue
        d = FreeCAD.Vector(*r['axis']); tip = FreeCAD.Vector(*r['tip'])
        k = r['kind']
        if k in SCREWS:
            origin = tip + d * float(r['len'])
        elif k == 'IUTHeatInsert':
            origin = tip + d * float(r['total'])
        else:                                      # washers, nuts sit on z=0 going +Z
            origin = tip
        G = FreeCAD.Placement(origin, FreeCAD.Rotation(Z, d))
        o = doc.addObject('Part::FeaturePython', 'Fastener')
        FastenersCmd.FSScrewObject(o, k, None)
        o.Diameter = f"M{fmt(float(r['dia']))}"
        if k in SCREWS:
            set_length(o, float(r['len']))
        if 'Thread' in o.PropertiesList: o.Thread = False
        FastenersCmd.FSViewProviderTree(o.ViewObject)
        o.Placement = inv.multiply(G)
        L = built_length(o)
        o.Label = f"M{fmt(float(r['dia']))}" + (f"x{fmt(L)}" if (L and k in SCREWS) else "") + f" {PRETTY.get(k, k)}"
        o.addProperty('App::PropertyString', 'SourceName', 'Provenance', 'Original STEP object in vt350-good')
        o.SourceName = r['name']
        g.addObject(o); made += 1
        if k in SCREWS and L is not None and abs(L - float(r['len'])) > 0.01:
            len_diff.append(f"{r['label']}: wanted {r['len']} built {L}")
        checks.append((o, r, tip, d))

    doc.recompute()
    # Placement check: centre of mass of the new part vs the original STEP part.
    # Independent of holes/sockets, and an upside-down screw moves it by mm.
    from collections import Counter
    stats = Counter()
    for o, r, tip, d in checks:
        k = r['kind']
        if o.Shape.isNull():
            bad.append(f"{o.Label} ({r['label']}): null shape"); stats[(k, 'null')] += 1; continue
        sh = o.Shape.copy(); sh.Placement = o.getGlobalPlacement()
        cm_new = sh.Solids[0].CenterOfMass if sh.Solids else sh.BoundBox.Center
        cm_old = FreeCAD.Vector(*r['com']) if r.get('nsolids') == 1 else None
        if cm_old is None:
            stats[(k, 'unchecked (multi-solid original)')] += 1; continue
        v = cm_new - cm_old; along = abs(v.dot(d)); radial = (v - d * v.dot(d)).Length
        lim_along = 1.0 + 0.05 * float(r['total'])
        if radial > TOL or along > lim_along:
            bad.append(f"{o.Label} ({r['label']}): COM off {along:.2f} mm along axis (limit {lim_along:.2f}), {radial:.2f} mm radial")
            stats[(k, 'FAIL')] += 1
        else:
            stats[(k, 'ok')] += 1
    log("placement check by type:"); [log(f"  {k:14} {res:34} {n}") for (k, res), n in sorted(stats.items())]
    log(f"fasteners made {made}, originals kept {kept}, already present {skipped}")
    log(f"length fallbacks {len(len_diff)}:"); [log("  " + x) for x in len_diff]
    log(f"placement check failures {len(bad)} of {len(checks)}:"); [log("  " + x) for x in bad]
    doc.saveAs(DST)
    log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close()
    os._exit(0)
