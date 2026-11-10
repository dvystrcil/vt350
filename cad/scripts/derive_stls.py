# Printable STLs of remixed parts, in the UPSTREAM part's print orientation.   (headless, read-only on the models)
#   VT350_UPSTREAM=<dir with the upstream STLs> freecadcmd /home/dan/Code/vt350/cad/scripts/derive_stls.py
#   VT350_MODELS=<dir with vt350-lite-N.FCStd> (default ~/Documents/VT350), VT350_REPO=<checkout> (homelab#1961)
# For each part: the part as it sat in the OLD model (before the remix) is matched to the upstream STL by a rigid
# transform: principal axes of inertia (old solid vs the upstream mesh, 4 proper sign choices), refined by closest-point
# iterations (Kabsch), then checked: every sampled upstream vertex within TOL of the transformed old part. Upstream
# prints are often at non-right angles (the A4Tv2 ducts are). The same transform then takes the REMIXED part from the
# new model to the print orientation. A part that doesn't match is reported and not written.
import FreeCAD, Part, Mesh, MeshPart, os, time, traceback
import numpy as np
V = FreeCAD.Vector
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
UP = os.environ.get("VT350_UPSTREAM", "/home/dan/Documents/VT350/downloads/upstream")
M = os.environ.get("VT350_MODELS", "/home/dan/Documents/VT350") + "/vt350-lite-{}.FCStd"   # dir; the batch lane sets it
TOL = 0.05
DUCTS = f"{REPO}/cad/derived/a4tv2-duct-4010-madmax-dock"
ARMS = f"{REPO}/cad/derived/madmax-andrewmcgr-dock-arm"
CARRIAGE = f"{REPO}/cad/derived/madmax-andrewmcgr-carriage-beacon"
ONLY = os.environ.get("VT350_ONLY")          # write only the jobs whose output name contains this
# (old model, new model, output, upstream STL, old label + group, new label + group, which solid: "low" = lowest Z)
JOBS = [
    (22, 23, f"{DUCTS}/A4Tv2 Duct-4010-left MadMax dock.stl", f"{UP}/A4Tv2_4010_Ducts.stl",
     ("[a]_Duct-4010-left", "Left Toolhead"), ("[a]_Duct-4010-left MadMax dock bosses (remix, CC BY-NC-SA 4.0)", "Left Toolhead"), None),
    (22, 23, f"{DUCTS}/A4Tv2 Duct-4010-right MadMax dock.stl", f"{UP}/A4Tv2_4010_Ducts.stl",
     ("[a]_Duct-4010-right001", "Right Toolhead"), ("[a]_Duct-4010-right MadMax dock bosses (remix, CC BY-NC-SA 4.0)", "Right Toolhead"), None),
    (22, 23, f"{ARMS}/Dock Arm {{net}}.stl", f"{ARMS}/Dock Arm +5mm.stl",
     ("Dock Arm v1 Bottom +5mm", "Left Dock"), ("Dock Arm v1 Bottom *", "Left Dock"), "low"),
    (23, 24, f"{CARRIAGE}/MadMaxCarriage Beacon RevH pocket.stl", f"{UP}/MadMaxCarriage.stl",
     ("COMPOUND", "Carriage (1)"), ("COMPOUND", "Carriage (1)"), None),
]
log_f = open(f"{REPO}/cad/data/logs/derive_stls" + (f"_{ONLY.split()[0].lower()}" if ONLY else "") + ".log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
import sys; sys.path[:0] = [f"{REPO}/cad/scripts", f"{REPO}/platform/freecad"]   # reglib: beside this (a gpu-batch pod), or platform/ (vt350#122)
from reglib import mesh_inertia, shape_inertia, mat, moved, dists, register   # noqa: F401 (moved there)
def part(doc, label, group, which):
    """(shape, label); a label ending in ' *' matches by prefix (and must not be the old part's exact label)"""
    if label.endswith(" *"):
        c = [o for o in doc.Objects if o.Label.startswith(label[:-1]) and "Mirror" not in o.Label and "+5mm" not in o.Label
             and group in [a.Label for a in o.InListRecursive]]
    else: c = [o for o in doc.getObjectsByLabel(label) if group in [a.Label for a in o.InListRecursive]]
    if len(c) != 1: raise RuntimeError(f"{len(c)} objects {label!r} under {group!r}")
    s = c[0].Shape.copy(); s.Placement = c[0].getGlobalPlacement()
    if which == "low": s = min(s.Solids, key=lambda x: x.BoundBox.ZMin)
    return s, c[0].Label
try:
    docs = {}
    def model(n):
        if n not in docs: docs[n] = FreeCAD.openDocument(M.format(n))
        return docs[n]
    res = []
    for mo, mn, out, up, (ol, og), (nl, ng), which in JOBS:
        if ONLY and ONLY not in out: continue
        so, _ = part(model(mo), ol, og, which); sn, nlab = part(model(mn), nl, ng, which)
        out = out.replace("{net}", nlab.split()[-1])
        comps = [c for c in Mesh.Mesh(up).getSeparateComponents() if c.CountFacets >= 50]
        # the upstream component with the same volume (the A4Tv2 STL holds both ducts)
        ci, cm = min(enumerate(comps), key=lambda x: abs(x[1].Volume - so.Volume))
        if abs(cm.Volume - so.Volume) > 0.005 * so.Volume:
            log(f"NO MATCH {os.path.basename(out)}: no upstream component within 0.5% of volume {so.Volume:.1f} "
                + str([round(c.Volume, 1) for c in comps])); res.append((out, None)); continue
        R, t, dmax, dmed, sep = register(so, cm)
        if dmax > TOL:
            log(f"NO MATCH {os.path.basename(out)}: component {ci}, max vertex distance {dmax:.4f} (median {dmed:.4f}), "
                f"inertia axes separation {sep:.3f}"); res.append((out, None)); continue
        ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
        log(f"{os.path.basename(out)}: old part = component {ci} of {os.path.basename(up)} (volume {cm.Volume:.1f} vs {so.Volume:.1f}); "
            f"rotation {ang:.2f} deg; max vertex distance {dmax:.4f} mm (median {dmed:.4f})")
        r = moved(sn, R, t)
        msh = MeshPart.meshFromShape(Shape=r, LinearDeflection=0.01, AngularDeflection=0.1)
        os.makedirs(os.path.dirname(out), exist_ok=True); msh.write(out)
        b = r.BoundBox
        log(f"   wrote {os.path.relpath(out, REPO)}: {msh.CountFacets} facets, {b.XLength:.2f} x {b.YLength:.2f} x {b.ZLength:.2f} mm, volume {r.Volume:.1f} (old {so.Volume:.1f}); solid valid {r.isValid()}")
        res.append((out, dict(volume=r.Volume, size=(b.XLength, b.YLength, b.ZLength), old_volume=so.Volume)))
    log("done:", sum(1 for _, x in res if x), "of", len(res), "written")
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
