import FreeCAD, sys
import os
WORK = os.environ.get("VT350_WORK", os.path.expanduser("~/Code/vt350/cad/data"))  # data in, logs out
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
out = open(WORK + "/fs_probe.out", "w")
try:
    import FastenersCmd
    d = FreeCAD.newDocument("probe")
    for t, dia, ln in [("ISO4762","M3","8"), ("ISO7380-1","M5","16"), ("ISO10642","M3","6"), ("ISO7089","M5",None), ("ISO4032","M3",None), ("IUTHeatInsert","M3",None), ("ISO4026","M4","3")]:
        o = d.addObject("Part::FeaturePython", t)
        FastenersCmd.FSScrewObject(o, t, None)
        o.Diameter = dia
        if ln is not None and hasattr(o, "Length"):
            try: o.Length = ln
            except Exception as e: out.write(f"{t} length {ln}: {e} opts={o.getEnumerationsOfProperty('Length')[:12]}\n")
        d.recompute()
        bb = o.Shape.BoundBox
        out.write(f"{t:14} {dia} L={getattr(o,'Length','-')} thread={getattr(o,'Thread','-')} faces={len(o.Shape.Faces)} z=[{bb.ZMin:.2f},{bb.ZMax:.2f}] xy={bb.XLength:.2f}\n")
    out.write("types with tapping/self: " + str([k for k in FastenersCmd.screwTables if '7049' in k or 'tapp' in FastenersCmd.screwTables[k][0].lower()]) + "\n")
except Exception:
    import traceback; out.write(traceback.format_exc())
out.close()
