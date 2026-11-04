# Read-only pass over vt350-good.FCStd: for every STEP fastener, record what a
# Fasteners-workbench replacement needs. Never saves the source document.
#   out: fasteners.json  (one record per fastener)
#        keep/<name>.brep (originals we keep as-is: T-nuts, square washers, self-tappers)
import FreeCAD, Part, re, json, os, math, traceback
WORK = os.environ.get("VT350_WORK", os.path.expanduser("~/Code/vt350/cad/data"))  # data in, logs out

SRC = "/home/dan/Documents/VT350/vt350-good.FCStd"
OUT = WORK + "/fasteners"
os.makedirs(OUT + "/keep", exist_ok=True)
log = open(OUT + "/extract.log", "w")

FASTENER = re.compile(r'screw|bolt|\bnuts?\b|t-nut|washer|threaded insert|heat.?set|91290|91239A118|shcs|bhcs|fhcs|^m[2-6]\s*[x*×]', re.I)
NOT_FASTENER = re.compile(r'leadscrew|dowel', re.I)
FASTENER_PARENT = re.compile(r'^M5\*50 \+ washer', re.I)
KEEP_AS_IS = re.compile(r't-nut|square washer|self-?tapping', re.I)
METRIC = [2, 2.5, 3, 4, 5, 6, 8]

def kind_of(label, parent_label):
    l = label.lower()
    if KEEP_AS_IS.search(l): return 'keep'
    if 'set screw' in l: return 'ISO4026'
    if re.search(r'insert|heat.?set', l): return 'IUTHeatInsert'
    if 'washer' in l: return 'ISO7089'
    if 'thin hex nut' in l: return 'ISO4035'
    if re.search(r'\bnut\b', l): return 'ISO4032'
    if 'fhcs' in l: return 'ISO10642'
    if re.search(r'bhcs|button head', l): return 'ISO7380-1'
    if re.search(r'shcs|socket head|91290|end_cap_screw', l): return 'ISO4762'
    if FASTENER_PARENT.match(parent_label or ''): return 'ISO4762'   # 'SOLID' inside 'M5*50 + washer'
    return 'ISO4762'  # fallback, flagged below

def parse_size(label):
    m = re.search(r'\bM(\d+(?:\.\d)?)\s*[x*×]\s*(\d+(?:\.\d+)?)', label, re.I)
    if m: return float(m.group(1)), float(m.group(2))
    m = re.search(r'\bM(\d+(?:\.\d)?)\b', label, re.I)
    return (float(m.group(1)), None) if m else (None, None)

def parent_chain(o):
    out = []
    p = o
    while True:
        par = next((x for x in p.InList if x.isDerivedFrom('App::Part') and p in x.Group), None)
        if par is None: return out
        out.append(par.Name); p = par

def geometry(shape):
    """Axis (unit, pointing tip->head), tip point, total length, shank radius, head radius, underside offset from tip."""
    cyls = [f for f in shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    if not cyls: return None
    ax_face = max(cyls, key=lambda f: f.Area)
    d = ax_face.Surface.Axis.normalize(); c = ax_face.Surface.Center
    pts = [v.Point for v in shape.Vertexes] or [shape.BoundBox.Center]
    # sample edges too: vertices alone miss round heads
    for e in shape.Edges:
        try: pts += e.discretize(8)
        except Exception: pass
    ts = [(p - c).dot(d) for p in pts]
    tmin, tmax = min(ts), max(ts); L = tmax - tmin
    def rad(p):
        v = p - c; t = v.dot(d); return (v - d * t).Length
    band = max(L * 0.15, 0.3)
    r_lo = max([rad(p) for p, t in zip(pts, ts) if t <= tmin + band] or [0])
    r_hi = max([rad(p) for p, t in zip(pts, ts) if t >= tmax - band] or [0])
    # Head = heavier end. Edge sampling misses domed heads (M3x6 BHCS read 1.5 mm at
    # both ends), so decide by where the centre of mass sits along the axis.
    try:
        t_com = (shape.Solids[0].CenterOfMass - c).dot(d) if shape.Solids else (shape.BoundBox.Center - c).dot(d)
    except Exception:
        t_com = (tmin + tmax) / 2
    if t_com < (tmin + tmax) / 2:   # head is at the tmin end -> flip so +d points tip->head
        d = d * -1; ts = [-t for t in ts]; tmin, tmax = -tmax, -tmin; r_lo, r_hi = r_hi, r_lo
    tip = c + d * tmin
    r_shank = min(f.Surface.Radius for f in cyls if abs(abs(f.Surface.Axis.normalize().dot(d)) - 1) < 1e-3)
    # underside: first t (from tip) where the profile exceeds the shank by 25%
    under = None
    for p, t in sorted(zip(pts, ts), key=lambda pt: pt[1]):
        if rad(p) > r_shank * 1.25 + 0.05: under = t - tmin; break
    return dict(axis=[d.x, d.y, d.z], tip=[tip.x, tip.y, tip.z], total=L,
                r_shank=r_shank, r_head=r_hi, under=under)

def snap_metric(diam):
    return min(METRIC, key=lambda m: abs(m - diam))

try:
    doc = FreeCAD.openDocument(SRC)
    log.write(f"opened {len(doc.Objects)}\n"); log.flush()
    recs = []
    for o in doc.Objects:
        if o.TypeId != 'Part::Feature': continue
        chain = parent_chain(o)
        plabel = doc.getObject(chain[0]).Label if chain else ''
        if not ((FASTENER.search(o.Label) and not NOT_FASTENER.search(o.Label)) or FASTENER_PARENT.match(plabel)):
            continue
        s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
        k = kind_of(o.Label, plabel)
        rec = dict(name=o.Name, label=o.Label, parent_label=plabel, chain=chain, kind=k)
        if k == 'keep':
            fn = f"{OUT}/keep/{o.Name}.brep"; s.exportBrep(fn); rec['brep'] = 'keep/' + os.path.basename(fn)
            recs.append(rec); continue
        g = geometry(s)
        if g is None:
            rec['kind'] = 'keep'; fn = f"{OUT}/keep/{o.Name}.brep"; s.exportBrep(fn); rec['brep'] = 'keep/' + os.path.basename(fn)
            rec['note'] = 'no cylindrical face; kept original'; recs.append(rec); continue
        # Thin, ring-shaped parts are washers whatever their parent group is called
        # ('SOLID' inside 'M5*50 + washer' is the washer, not the screw).
        if k != 'ISO7089' and g['total'] <= 2.0 and g['r_head'] > g['r_shank'] * 1.4 and 'nut' not in o.Label.lower():
            k = rec['kind'] = 'ISO7089'; rec['note'] = 'reclassified as washer from geometry'
        dia, ln = parse_size(o.Label if parse_size(o.Label)[0] else plabel)
        if k == 'ISO7089': ln = None
        geo_dia = snap_metric(g['r_shank'] * 2) if k not in ('ISO7089', 'ISO4032', 'ISO4035', 'IUTHeatInsert') else None
        rec.update(g)
        sol = s.Solids[0] if len(s.Solids) == 1 else s
        try:
            cm = sol.CenterOfMass if len(s.Solids) == 1 else Part.makeCompound(s.Solids).Solids[0].CenterOfMass
        except Exception:
            cm = s.BoundBox.Center
        rec['com'] = [cm.x, cm.y, cm.z]; rec['nsolids'] = len(s.Solids)
        rec['dia'] = dia or geo_dia
        rec['dia_source'] = 'label' if dia else 'geometry'
        if k in ('ISO4762', 'ISO7380-1', 'ISO4026'):
            geo_len = g['under'] if (g['under'] and k != 'ISO4026') else g['total']
            rec['len'] = ln or round(geo_len)
            rec['len_geo'] = round(geo_len, 2)
        elif k == 'ISO10642':
            rec['len'] = ln or round(g['total']); rec['len_geo'] = round(g['total'], 2)
        if dia is None and k in ('ISO7089', 'ISO4032', 'ISO4035', 'IUTHeatInsert'):
            rec['dia'] = snap_metric(min(f.Surface.Radius for f in s.Faces if isinstance(f.Surface, Part.Cylinder)) * 2)
            rec['dia_source'] = 'geometry(hole)'
        rec['t_com_toward_head'] = True
        if False and rec.get('dia') and dia and geo_dia and abs(geo_dia - dia) > 0.01:  # geometry dia reads the hex socket; labels verified correct
            rec['warn'] = f"label M{dia} vs geometry M{geo_dia}"
        recs.append(rec)
    json.dump(recs, open(OUT + "/fasteners.json", "w"), indent=1)
    from collections import Counter
    log.write(f"records {len(recs)}\n" + "\n".join(f"{v:4d} {k}" for k, v in Counter(r['kind'] for r in recs).most_common()) + "\n")
    log.write("warnings:\n" + "\n".join(f"  {r['label']}: {r['warn']}" for r in recs if 'warn' in r) + "\n")
    log.write("DONE\n")
except Exception:
    log.write("FAILED\n" + traceback.format_exc())
finally:
    log.close()
    os._exit(0)
