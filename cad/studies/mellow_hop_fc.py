# freecadcmd stage of cad/studies/mellow_hop.py (vt350#291): read-only, never saves. Driven by MELLOW_HOP_JOB (JSON);
# writes MELLOW_HOP_OUT (JSON).
#
# Height maps, then clearances:
#  - the underside of what the carriage carries (a head, or nothing), as heights above the carried nozzle tip on a grid
#    round the nozzle: the head moved by -T (the plan stage's pickup translation: carried, the carriage at the model
#    pose), the carriage group (carriage, clips, Beacon) as it is. The Beacon can be slid in Y (a y_offset what-if).
#  - the top of the nozzle-offset probe (the Mellow MultiHead Zero and its bracket, lite-78), as heights above the
#    print surface (the PEI sheet's top).
# Every motion is a polyline of nozzle positions (model XY) at a nozzle Z above the print surface; its clearance is the
# smallest (underside + Z - probe top) over the motion, with the part and the place where it happens.
import FreeCAD, os, sys, json, math, traceback
import numpy as np

job = json.load(open(os.environ["MELLOW_HOP_JOB"]))
OUT = os.environ["MELLOW_HOP_OUT"]
sys.path[:0] = [job["platform"]]
import linkgeo
STEP = job["step"]
logf = open(OUT + ".log", "w")
def log(*a): logf.write(" ".join(str(x) for x in a) + "\n"); logf.flush()


def tris(shape, tol, zmax=None):
    """(N, 3, 3) triangles of shape, keeping those with a vertex under zmax."""
    pts, fs = shape.tessellate(tol)
    if not fs: return np.zeros((0, 3, 3))
    P = np.array([(p.x, p.y, p.z) for p in pts]); T = P[np.array(fs)]
    if zmax is not None: T = T[T[:, :, 2].min(axis=1) < zmax]
    return T


def raster(T, ids, x0, y0, nx, ny, lowest):
    """Height map (nx, ny) at x0 + i*STEP, y0 + j*STEP: the lowest (or highest) Z of the triangles over each cell
    centre, +inf (-inf) where none; and the index into ids of the part that gives it."""
    H = np.full((nx, ny), np.inf if lowest else -np.inf); I = np.full((nx, ny), -1, dtype=int)
    for t, pid in zip(T, ids):
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12: continue                      # vertical: its neighbours cover it
        i0 = max(0, int(math.floor((min(ax, bx, cx) - x0) / STEP))); i1 = min(nx - 1, int(math.ceil((max(ax, bx, cx) - x0) / STEP)))
        j0 = max(0, int(math.floor((min(ay, by, cy) - y0) / STEP))); j1 = min(ny - 1, int(math.ceil((max(ay, by, cy) - y0) / STEP)))
        if i1 < i0 or j1 < j0: continue
        X, Y = np.meshgrid(x0 + STEP * np.arange(i0, i1 + 1), y0 + STEP * np.arange(j0, j1 + 1), indexing="ij")
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d
        l3 = 1 - l1 - l2
        m = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        if not m.any(): continue
        Z = l1 * az + l2 * bz + l3 * cz
        sub = H[i0:i1 + 1, j0:j1 + 1]; si = I[i0:i1 + 1, j0:j1 + 1]
        better = m & ((Z < sub) if lowest else (Z > sub))
        sub[better] = Z[better]; si[better] = pid
    return H, I


def main():
    doc = FreeCAD.openDocument(job["model"])
    leaves = {o.Name: o for o in doc.Objects if linkgeo.is_leaf(o)}
    gp = linkgeo.group_parents(doc.Objects)
    def path(o): return linkgeo.group_path(o, gp)
    sheet = [o for o in leaves.values() if o.Label.startswith("PEI spring-steel sheet")]
    assert len(sheet) == 1, f"one PEI sheet ({len(sheet)})"
    pei = linkgeo.gshape(sheet[0]).BoundBox.ZMax
    # the probe: every leaf under a group whose label starts with the prefix
    probe = [o for o in leaves.values() if any(l.startswith(job["probe_prefix"]) for l in path(o))]
    log(f"print surface (PEI top) Z {pei:.3f}; probe parts: {[o.Label for o in probe]}")
    assert probe, "no probe parts found"
    bx, by = job["ball_model_xy"]; R = job["probe_half"]
    pnx = pny = int(2 * R / STEP) + 1; px0, py0 = bx - R, by - R
    PT, Pid = [], []
    for k, o in enumerate(probe):
        t = tris(linkgeo.gshape(o), 0.02); PT.append(t); Pid += [k] * len(t)
    PH, PI = raster(np.concatenate(PT), Pid, px0, py0, pnx, pny, lowest=False)
    PH = PH - pei
    top = np.nanmax(np.where(np.isfinite(PH), PH, np.nan))
    ti = np.unravel_index(np.argmax(np.where(np.isfinite(PH), PH, -1e9)), PH.shape)
    log(f"probe top {top:.3f} above the print surface at model ({px0 + ti[0] * STEP:.2f}, {py0 + ti[1] * STEP:.2f}) ({probe[PI[ti]].Label})")
    cells = np.argwhere(np.isfinite(PH) & (PH > -job["probe_depth"]))          # only what stands near the surface
    cxy = np.stack([px0 + cells[:, 0] * STEP, py0 + cells[:, 1] * STEP], axis=1); ch = PH[cells[:, 0], cells[:, 1]]
    out = dict(pei_z=pei, probe_top=round(float(top), 3), probe_parts=[o.Label for o in probe], unders={}, motions={})
    (dxl, dxh), (dyl, dyh) = job["under_window"]
    unx, uny = int((dxh - dxl) / STEP) + 1, int((dyh - dyl) / STEP) + 1
    unders = {}
    for key, u in job["unders"].items():
        nxm, nym, tip = u["nozzle"]; T = u["T"]
        names = u["parts"]; labels = []
        allT, ids = [], []
        for k, n in enumerate(names):
            o = leaves[n]; s = linkgeo.gshape(o).copy()
            mv = [0.0, 0.0, 0.0]
            if n in u.get("head", []): mv = [-T[0], -T[1], -T[2]]
            if n == u.get("beacon") and u.get("beacon_dy"): mv[1] += u["beacon_dy"]
            s.translate(FreeCAD.Vector(*mv))
            b = s.BoundBox
            if b.ZMin > tip + job["under_depth"] or b.XMax < nxm + dxl or b.XMin > nxm + dxh or b.YMax < nym + dyl or b.YMin > nym + dyh:
                continue
            t = tris(s, 0.05, tip + job["under_depth"])
            if len(t): allT.append(t); ids += [len(labels)] * len(t); labels.append(o.Label)
        H, I = raster(np.concatenate(allT), ids, nxm + dxl, nym + dyl, unx, uny, lowest=True)
        H = H - tip
        lo = np.unravel_index(np.argmin(H), H.shape)
        log(f"underside {key}: {len(labels)} parts, lowest {H[lo]:.3f} above the tip at d({dxl + lo[0] * STEP:.2f}, {dyl + lo[1] * STEP:.2f}) ({labels[I[lo]]})")
        unders[key] = (H, I, labels, (nxm, nym))
        out["unders"][key] = dict(parts=len(labels), lowest=round(float(H[lo]), 3), lowest_part=labels[I[lo]])
    for name, mo in job["motions"].items():
        H, I, labels, _ = unders[mo["under"]]; Z = mo["z"]
        best = None
        pts = mo["points"]
        for k in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / job["sample"]))
            for j in range(n + 1):
                x = x0 + (x1 - x0) * j / n; y = y0 + (y1 - y0) * j / n
                if abs(x - bx) > max(-dxl, dxh) + R or not (dyl - R <= by - y <= dyh + R): continue
                ii = np.rint((cxy[:, 0] - x - dxl) / STEP).astype(int); jj = np.rint((cxy[:, 1] - y - dyl) / STEP).astype(int)
                ok = (ii >= 0) & (ii < unx) & (jj >= 0) & (jj < uny)
                if not ok.any(): continue
                u = H[ii[ok], jj[ok]]; c = u + Z - ch[ok]
                if not np.isfinite(c).any(): continue
                q = int(np.argmin(c))
                if best is None or c[q] < best[0]:
                    sel = np.flatnonzero(ok)[q]
                    best = (float(c[q]), x, y, labels[I[ii[ok][q], jj[ok][q]]], float(ch[ok][q]), float(cxy[sel, 0]), float(cxy[sel, 1]))
        if best is None:
            out["motions"][name] = dict(z=Z, clearance=None, note="never over the probe"); log(f"{name}: never over the probe"); continue
        c, x, y, part, h, mx, my = best
        out["motions"][name] = dict(z=Z, clearance=round(c, 3), nozzle_model_xy=[round(x, 2), round(y, 2)], part=part,
                                    probe_point_model_xy=[round(mx, 2), round(my, 2)], probe_height=round(h, 3))
        log(f"{name}: Z {Z}: clearance {c:.3f} ({part} over the probe at model ({mx:.2f}, {my:.2f}), probe {h:.2f} above the "
            f"surface; nozzle at model ({x:.2f}, {y:.2f}))")
    json.dump(out, open(OUT, "w"), indent=1)


try:
    main()
except Exception:
    log("FATAL\n" + traceback.format_exc())
    json.dump(dict(fatal=traceback.format_exc()), open(OUT, "w"))
