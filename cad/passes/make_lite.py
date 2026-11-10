# Build vt350-lite.FCStd from vt350-good.FCStd (source is never saved over).
#  - delete fasteners (screws, washers, nuts, T-nuts, inserts)
#  - replace each PCB assembly with one box of its local bounding box
#  - replace the 3 leadscrews with plain cylinders
#  - delete containers left with no geometry
# Run in the GUI (so GuiDocument/colors survive):  FreeCAD.AppImage /abs/path/make_lite.py
import FreeCAD, Part, re, os, time, traceback
WORK = os.environ.get("VT350_WORK", os.path.expanduser("~/Code/vt350/cad/data"))  # data in, logs out

SRC = "/home/dan/Documents/VT350/vt350-good.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite.FCStd"
LOG = WORK + "/make_lite.log"
log_f = open(LOG, "w")
t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()

FASTENER = re.compile(r'screw|bolt|\bnuts?\b|t-nut|washer|threaded insert|heat.?set|91290|91239A118|shcs|bhcs|fhcs|^m[2-6]\s*[x*×]', re.I)
KEEP = re.compile(r'leadscrew|dowel', re.I)          # real parts the regex would otherwise hit
FASTENER_PARENT = re.compile(r'^M5\*50 \+ washer', re.I)
PCB_ROOT = re.compile(r'^(Octopus_Pro|Nitehawk-36)', re.I)
PCB_GROUP = re.compile(r'^PCB( \(\d+\))?$')
ORIGIN_TYPES = ('App::Origin', 'App::Plane', 'App::Line', 'App::Point')

def parent_of(o):
    for p in o.InList:
        if p.isDerivedFrom('App::Part') and o in p.Group:
            return p
    return None

def descendants(o):
    out = []
    for c in getattr(o, 'Group', []) or []:
        out.append(c); out += descendants(c)
    return out

def alive(doc, o):
    try:
        return doc.getObject(o.Name) is not None
    except ReferenceError:
        return False

def nuke(doc, o):
    """Remove a container and everything in it, including its Origin."""
    if not alive(doc, o):
        return
    for c in list(getattr(o, 'Group', []) or []):
        nuke(doc, c)
    # Capture names first: removing an App::Part can delete its Origin itself,
    # and touching a deleted object raises ReferenceError.
    org = getattr(o, 'Origin', None)
    names = []
    if org is not None:
        names = [f.Name for f in org.OriginFeatures] + [org.Name]
    doc.removeObject(o.Name)
    for n in [names[-1]] + names[:-1] if names else []:
        if doc.getObject(n) is not None:
            doc.removeObject(n)

def local_bbox(root):
    """Bounding box of all shapes under root, expressed in root's own frame."""
    inv = root.getGlobalPlacement().inverse()
    bb = FreeCAD.BoundBox()
    for f in descendants(root):
        if f.TypeId == 'Part::Feature' and not f.Shape.isNull():
            s = f.Shape.copy(); s.Placement = inv.multiply(f.getGlobalPlacement())
            bb.add(s.BoundBox)
    return bb

try:
    doc = FreeCAD.openDocument(SRC)
    log("opened", len(doc.Objects), "objects")

    # 1) PCBs -> boxes
    roots = [o for o in doc.Objects if o.TypeId == 'App::Part' and PCB_ROOT.match(o.Label)]
    roots += [o for o in doc.Objects if o.TypeId == 'App::Part' and PCB_GROUP.match(o.Label)
              and not any(PCB_ROOT.match(a.Label) for a in o.InListRecursive)]
    for r in roots:
        if not alive(doc, r):
            continue
        bb = local_bbox(r); par = parent_of(r); lbl = r.Label
        box = doc.addObject('Part::Box', 'PCB_Box')
        box.Label = f"{lbl} (simplified box)"
        box.Length, box.Width, box.Height = bb.XLength, bb.YLength, bb.ZLength
        box.Placement = r.Placement.multiply(FreeCAD.Placement(FreeCAD.Vector(bb.XMin, bb.YMin, bb.ZMin), FreeCAD.Rotation()))
        if par: par.addObject(box)
        n = len([d for d in descendants(r) if d.TypeId == 'Part::Feature'])
        nuke(doc, r)
        log(f"PCB  {lbl!r}: {n} shapes -> box {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f}")

    # 2) leadscrews -> cylinders
    for o in [o for o in doc.Objects if o.TypeId == 'Part::Feature' and re.match(r'^Leadscrew\d*$', o.Label)]:
        s = o.Shape.copy(); s.Placement = FreeCAD.Placement(); bb = s.BoundBox
        dims = {'x': bb.XLength, 'y': bb.YLength, 'z': bb.ZLength}
        ax = max(dims, key=dims.get); dia = max(v for k, v in dims.items() if k != ax)
        c = bb.Center
        base = {'x': FreeCAD.Vector(bb.XMin, c.y, c.z), 'y': FreeCAD.Vector(c.x, bb.YMin, c.z), 'z': FreeCAD.Vector(c.x, c.y, bb.ZMin)}[ax]
        rot = {'x': FreeCAD.Rotation(FreeCAD.Vector(0,0,1), FreeCAD.Vector(1,0,0)),
               'y': FreeCAD.Rotation(FreeCAD.Vector(0,0,1), FreeCAD.Vector(0,1,0)), 'z': FreeCAD.Rotation()}[ax]
        cyl = doc.addObject('Part::Cylinder', 'Leadscrew_Rod'); cyl.Label = o.Label + " (rod)"
        cyl.Radius, cyl.Height = dia / 2, dims[ax]
        cyl.Placement = o.Placement.multiply(FreeCAD.Placement(base, rot))
        par = parent_of(o)
        if par: par.addObject(cyl)
        log(f"LEAD {o.Label!r}: -> rod d={dia:.1f} L={dims[ax]:.1f}")
        doc.removeObject(o.Name)

    # 3) fasteners
    gone = 0
    for o in list(doc.Objects):
        if not alive(doc, o) or o.TypeId != 'Part::Feature':
            continue
        par = parent_of(o)
        if (FASTENER.search(o.Label) and not KEEP.search(o.Label)) or (par is not None and FASTENER_PARENT.match(par.Label)):
            doc.removeObject(o.Name); gone += 1
    log("fasteners removed:", gone)

    # 4) empty containers, deepest first
    emptied = 0
    for _ in range(20):
        empt = [o for o in doc.Objects if o.TypeId == 'App::Part'
                and not any(d.TypeId not in ORIGIN_TYPES and d.TypeId != 'App::Part' for d in descendants(o))]
        if not empt: break
        for o in empt:
            if alive(doc, o):
                nuke(doc, o); emptied += 1
    log("empty containers removed:", emptied)

    doc.recompute()
    log("objects now:", len(doc.Objects))
    doc.saveAs(DST)
    log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close()
    os._exit(0)
