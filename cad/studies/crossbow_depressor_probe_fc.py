# SPDX-License-Identifier: GPL-3.0-or-later
"""vt350#78: where each head's Crossbow lever is with the head on the carriage (the carried pose: docked pose minus the
pickup offset, the same T_pick as sweep_toolhead.py), the carriage, beam and XY joints, and the boxes of DW-Tas's
Monolith depressor (CC BY-NC-SA 4.0, read from $VT350_DL; never copied into the repo). Read-only.

    $APP freecadcmd $PWD/cad/studies/crossbow_depressor_probe_fc.py     # -> cad/data/crossbow_depressor_probe.json
    VT350_MODEL=<.FCStd> to read another model (default vt350-lite-81)
"""
import json, os, sys, traceback
REPO = os.environ.get("VT350_REPO", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = REPO + "/cad/data/crossbow_depressor_probe.json"
MODEL = os.environ.get("VT350_MODEL", os.path.expanduser("~/Documents/VT350/vt350-lite-81.FCStd"))
DL = os.environ.get("VT350_DL", os.path.expanduser("~/Documents/VT350/dl"))
sys.path[:0] = [REPO + "/cad/studies", REPO + "/platform/freecad", REPO + "/cad/scripts"]
res = {"model": os.path.basename(MODEL)}
try:
    import FreeCAD, Part, Import
    import linkgeo
    import sweep_toolhead as ST
    V = FreeCAD.Vector
    doc = FreeCAD.openDocument(MODEL)
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, "Group", []) or []): par.setdefault(k.Name, o)
    def path(o):
        r, p = [], par.get(o.Name)
        while p is not None: r.append(p.Label); p = par.get(p.Name)
        return r
    leaves = [o for o in doc.Objects if linkgeo.is_leaf(o)]
    P = {o.Name: path(o) for o in leaves}
    def box(s):
        b = s.BoundBox; return [round(b.XMin, 2), round(b.YMin, 2), round(b.ZMin, 2), round(b.XMax, 2), round(b.YMax, 2), round(b.ZMax, 2)]
    def com(s):
        vs = [(x.Volume, x.CenterOfMass) for x in s.Solids]; tv = sum(v for v, _ in vs)
        return sum((c * (v / tv) for v, c in vs), V(0, 0, 0))
    real = [o for o in leaves if o.Label == ST.CARRIAGE_PART[1] and ST.CARRIAGE_PART[0] in P[o.Name]][0]
    sr = linkgeo.gshape(real)
    res["carriage"] = box(sr)
    for h, d in ST.HEADS.items():
        cp = [o for o in leaves if o.Label == d["copy"] and d["dock"] in P[o.Name]][0]
        t = com(linkgeo.gshape(cp)) - com(sr)
        hl = [o for o in leaves if d["group"] in P[o.Name]]
        hb = None
        for o in hl:
            s = linkgeo.gshape(o).copy(); s.translate(-t)
            hb = s.BoundBox if hb is None else hb.united(s.BoundBox)
        cb = [o for o in hl if "rossbow" in o.Label or "rossbow" in " ".join(P[o.Name])]
        items = []
        for o in cb:
            s = linkgeo.gshape(o).copy(); s.translate(-t)
            items.append({"label": o.Label, "path": P[o.Name][:3], "box_carried": box(s), "vol": round(s.Volume, 1)})
        res[h] = {"T_pick": [round(t.x, 3), round(t.y, 3), round(t.z, 3)],
                  "head_box_carried": [round(v, 2) for v in (hb.XMin, hb.YMin, hb.ZMin, hb.XMax, hb.YMax, hb.ZMax)],
                  "crossbow": items}
    for side in ("XY left: _XY_left", "XY right: _XY_right"):
        g = [o for o in leaves if side in P[o.Name]]
        bb = None; parts = []
        for o in g:
            s = linkgeo.gshape(o); bb = s.BoundBox if bb is None else bb.united(s.BoundBox)
            parts.append((o.Label, box(s)))
        res[side] = {"box": [round(v, 2) for v in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)],
                     "parts": sorted(parts, key=lambda p: -p[1][5])[:25]}
    beam = [o for o in leaves if o.Label in ST.GANTRY_LABELS]
    res["beam"] = [box(linkgeo.gshape(o)) for o in beam]
    # DW-Tas Monolith depressor
    step = DL + "/crossbow-repo/CAD/Crossbow Depressor Arm and Holder [Monolith Gantry].step"
    sh = Part.Shape(); sh.read(step)
    res["dwtas_monolith"] = {"box": box(sh), "solids": [box(s) for s in sh.Solids], "vols": [round(s.Volume, 1) for s in sh.Solids]}
except Exception:
    res["error"] = traceback.format_exc()
json.dump(res, open(OUT, "w"), indent=1)
os._exit(0)
