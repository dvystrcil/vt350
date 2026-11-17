# SPDX-License-Identifier: GPL-3.0-or-later
# What sits lowest above the carried nozzle tip (vt350#114, AC1 + AC2): read-only, headless.
#
#   $APP freecadcmd $PWD/cad/studies/carriage_clearance.py          # VT350_MODEL=<lite-N.FCStd> to pick the model
#
# For each head carried (the head moved by -T_pick, as sweep_toolhead.py does: T_pick is the dock's carriage copy
# minus the gantry carriage, same part), every solid on the gantry carriage plus the carried head is cut by a slab
# from the nozzle tip to BAND mm above it. A part that reaches into the slab is listed with the true Z of its lowest
# point (boolean, not the bounding box), and the lowest face's centre X/Y relative to the nozzle. The bed comes up
# from below, so this is the order things meet a flat plate under the nozzle.
#
# Output: cad/data/logs/carriage_clearance.log (written and flushed line by line: a FreeCAD crash keeps what came
# before). Ends with "carriage_clearance: done".
import os, sys, time

WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-61.FCStd")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE] + [os.path.join(os.path.dirname(os.path.dirname(HERE)), d) for d in ("platform/freecad", "cad/studies")]
BAND = 5.0                             # mm above the carried nozzle tip (AC2)
HEADS = {"Left": dict(group="Left Toolhead", dock="Left Dock", copy="COMPOUND003"),
         "Right": dict(group="Right Toolhead", dock="Right Dock", copy="COMPOUND004")}
TUBES = ("Bowden Left", "Bowden Right")
CARRIAGE_PART = ("Carriage (1)", "COMPOUND")
CARRIAGE_PATHS = {"Carriage (1)"}
CARRIAGE_LABELS = ("MGN_12_H_CARRAGE v1",)
NOZZLE = "E3D v6 HotEnd - Nozzle"
BEACON = "Beacon RevH"
LOG = os.path.join(WORK, "logs", "carriage_clearance.log")
T0 = time.time()
_f = open(LOG, "w")


def log(s=""):
    _f.write(f"[{time.time() - T0:7.1f}s] {s}\n"); _f.flush()


def main():
    import FreeCAD, Part
    import linkgeo
    V = FreeCAD.Vector
    doc = FreeCAD.openDocument(MODEL)
    log(f"opened {MODEL}")
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, "Group", []) or []): par.setdefault(k.Name, o)
    def path(o):
        r, p = [], par.get(o.Name)
        while p is not None: r.append(p.Label); p = par.get(p.Name)
        return r
    leaves = [o for o in doc.Objects if linkgeo.is_leaf(o)]
    P = {o.Name: set(path(o)) for o in leaves}
    def one(label, under=None):
        c = [o for o in leaves if o.Label == label and (under is None or under in P[o.Name])]
        if len(c) != 1: raise RuntimeError(f"{len(c)} leaves labelled {label!r} under {under!r}")
        return c[0]
    def com(s):
        vs = [(x.Volume, x.CenterOfMass) for x in s.Solids]; tv = sum(v for v, _ in vs)
        return sum((c * (v / tv) for v, c in vs), V(0, 0, 0))
    real = linkgeo.gshape(one(CARRIAGE_PART[1], CARRIAGE_PART[0]))
    carriage = [o for o in leaves if P[o.Name] & CARRIAGE_PATHS or o.Label in CARRIAGE_LABELS]
    log(f"carriage group: {len(carriage)} solids")
    for h, d in HEADS.items():
        t = com(linkgeo.gshape(one(d["copy"], d["dock"]))) - com(real)
        nz = [o for o in leaves if o.Label.startswith(NOZZLE) and d["group"] in P[o.Name]]
        if len(nz) != 1: raise RuntimeError(f"{h}: {len(nz)} nozzles")
        b = linkgeo.gshape(nz[0]).BoundBox
        tip = V((b.XMin + b.XMax) / 2 - t.x, (b.YMin + b.YMax) / 2 - t.y, b.ZMin - t.z)
        log("")
        log(f"== {h} head carried: T_pick ({t.x:.3f}, {t.y:.3f}, {t.z:.3f}); nozzle tip ({tip.x:.2f}, {tip.y:.2f}, {tip.z:.3f})")
        head = [o for o in leaves if d["group"] in P[o.Name] and o.Label not in TUBES]
        slab = Part.makeBox(4000, 4000, BAND + 1.0, V(-2000, -2000, tip.z - 1.0))
        rows = []
        for o, moved in [(o, False) for o in carriage] + [(o, True) for o in head]:
            s = linkgeo.gshape(o)
            if moved: s = s.copy(); s.translate(-t)
            if s.BoundBox.ZMin > tip.z + BAND or not s.Solids and not s.Faces: continue
            try:
                c = s.common(slab)
            except Exception as e:
                log(f"   ?? {o.Label}: common failed ({e}); box bottom {s.BoundBox.ZMin - tip.z:+.3f}"); continue
            if c.isNull() or not c.Faces: continue
            zmin = c.BoundBox.ZMin
            low = [f for f in c.Faces if f.BoundBox.ZMin < zmin + 0.01]
            fb = low[0].BoundBox
            for f in low[1:]: fb.add(f.BoundBox)
            where = "carried head" if moved else "carriage"
            rows.append((zmin - tip.z, o.Label, where, (fb.XMin + fb.XMax) / 2 - tip.x, (fb.YMin + fb.YMax) / 2 - tip.y,
                         fb.XLength, fb.YLength))
        rows.sort()
        log(f"parts within {BAND} mm above the carried nozzle tip, lowest first (dz = height above the tip; dx, dy = the "
            f"lowest face's centre from the nozzle; w x d = its extent):")
        for dz, lab, where, dx, dy, w, dd in rows:
            tag = "  <- Beacon coil face" if lab.startswith(BEACON) else ""
            log(f"   {dz:+7.3f}  {lab[:70]:70s} [{where}] at dx {dx:+7.2f} dy {dy:+7.2f}, {w:.1f} x {dd:.1f}{tag}")
        bea = [r for r in rows if r[1].startswith(BEACON)]
        lower = [r for r in rows if bea and r[0] < bea[0][0] - 1e-3 and not r[1].startswith(NOZZLE)]
        if bea: log(f"Beacon face {bea[0][0]:.3f} above the tip (nominal 2.6); {len(lower)} other part(s) lower than it: "
                    + ", ".join(f"{r[1][:40]} {r[0]:+.3f}" for r in lower))
    log("")
    log("carriage_clearance: done")


try:
    main()
except Exception:
    import traceback
    log(traceback.format_exc())
_f.close()
