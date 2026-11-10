# Read-only: map Z extents of everything in vt350-lite-2 so we can find the cut plane
# between the gantry and the top of the frame. Writes frame_map.json + frame_map.txt.
import FreeCAD, Part, sys, json, os, traceback
WORK = os.environ.get("VT350_WORK", os.path.expanduser("~/Code/vt350/cad/data"))  # data in, logs out
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
try:
    import FastenersCmd  # so Fasteners objects restore
except Exception:
    pass
SCR = WORK
OUT = SCR + "/frame_map"
os.makedirs(OUT, exist_ok=True)
txt = open(OUT + "/frame_map.txt", "w")
try:
    doc = FreeCAD.openDocument("/home/dan/Documents/VT350/vt350-lite-2.FCStd")
    def path(o):
        out = []; p = o
        while True:
            par = next((x for x in p.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup')) and p in getattr(x, 'Group', [])), None)
            if par is None: return list(reversed(out))
            out.append(par.Label); p = par
    recs = []
    for o in doc.Objects:
        if not o.isDerivedFrom('Part::Feature') or o.Shape.isNull():
            continue
        s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
        try:
            bb = s.optimalBoundingBox(True, False)   # tight box, not control-point hull
        except Exception:
            bb = s.BoundBox
        # long axis of the part's own (local) box, to tell vertical bars from horizontal ones
        recs.append(dict(name=o.Name, label=o.Label, type=o.TypeId, path=path(o),
                         x=[bb.XMin, bb.XMax], y=[bb.YMin, bb.YMax], z=[bb.ZMin, bb.ZMax]))
    json.dump(recs, open(OUT + "/frame_map.json", "w"), indent=0)
    ov = FreeCAD.BoundBox()
    for r in recs: ov.add(FreeCAD.BoundBox(r['x'][0], r['y'][0], r['z'][0], r['x'][1], r['y'][1], r['z'][1]))
    txt.write(f"overall X {ov.XMin:.1f}..{ov.XMax:.1f}  Y {ov.YMin:.1f}..{ov.YMax:.1f}  Z {ov.ZMin:.1f}..{ov.ZMax:.1f}\n")
    txt.write(f"{len(recs)} shapes\nDONE\n")
except Exception:
    txt.write("FAILED\n" + traceback.format_exc())
finally:
    txt.close(); os._exit(0)
