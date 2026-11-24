# freecadcmd worker for cad/studies/beacon_offset.py (vt350#291): Beacon's keep-out solid against the carried head.
# Read-only. Job JSON in $BEACON_CONE_JOB: model, step, now, offsets, heads {h: {ids, T}}; writes $BEACON_CONE_OUT.
# The keep-out solid is the one in Beacon's own STEP (beacon3d/docs mcad, MIT): Z 0..20 above the board top, on the
# coil axis. lite24_beacon.py placed the board rotated 180 about Z with the board top 4.21 above the coil face, so in
# the model the coil axis is 8.5 behind the board's front (-Y) edge and the board top is the body's ZMin + 4.21.
import json, os, sys
import FreeCAD, Part, Import
V = FreeCAD.Vector
job = json.load(open(os.environ["BEACON_CONE_JOB"]))
sys.path.insert(0, job["platform"])
import linkgeo

out = {"heads": {}, "notes": []}
try:
    doc = FreeCAD.openDocument(job["model"])
    byname = {o.Name: o for o in doc.Objects}
    beacon = linkgeo.gshape(byname[job["beacon"]]); bb = beacon.BoundBox
    axis = V((bb.XMin + bb.XMax) / 2, bb.YMin + 8.5, bb.ZMin + 4.21)
    if abs(bb.YMax - axis.y - 19.0) > 0.2: raise RuntimeError(f"Beacon box {bb} isn't the 180-degree placement")
    t = FreeCAD.newDocument("beacon_step"); Import.insert(job["step"], t.Name)
    sol = []
    for o in t.Objects:
        if o.isDerivedFrom("Part::Feature") and not o.Shape.isNull() and o.Shape.Solids:
            s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); sol += s.Solids
    keep = [x for x in sol if abs(x.BoundBox.ZMin) < 0.01 and abs(x.BoundBox.ZMax - 20.0) < 0.01]
    if not keep: raise RuntimeError("no keep-out solid in the STEP")
    k0 = keep[0].copy()
    k0.Placement = FreeCAD.Placement(axis, FreeCAD.Rotation(V(0, 0, 1), 180)).multiply(k0.Placement)
    out["notes"].append(f"coil axis X {axis.x:.2f} Y {axis.y:.2f}; keep-out Z {k0.BoundBox.ZMin:.2f}..{k0.BoundBox.ZMax:.2f}, "
                        f"radius {k0.BoundBox.XLength / 2:.2f} at its widest")
    for h, hd in job["heads"].items():
        tx, ty, tz = hd["T"]
        parts = []
        for n in hd["ids"]:
            o = byname.get(n)
            if o is None: continue
            s = linkgeo.gshape(o).copy(); s.translate(V(-tx, -ty, -tz)); parts.append((o.Label, s))
        rows = []
        for dy in job["offsets"]:
            k = k0.copy(); k.translate(V(0, -(job["now"] - dy), 0)); kb = k.BoundBox
            hits = []
            for lab, s in parts:
                if not s.BoundBox.intersect(kb): continue
                try: v = k.common(s).Volume
                except Exception: v = -1.0
                if v > 0.01 or v < 0: hits.append([round(v, 2), lab])
            rows.append({"offset": dy, "inside": sorted(hits, reverse=True)})
        out["heads"][h] = rows
except Exception as e:
    import traceback; out["fatal"] = traceback.format_exc()
json.dump(out, open(os.environ["BEACON_CONE_OUT"], "w"), indent=1)
