# Find the parts in a FreeCAD model that are copies of each other, price them in the file, and (from a pass) replace
# the copies with App::Links to one of them, so the file stores each shape once (vt350#195 AC1/AC3).
#
# Why: every Part::Feature stores its whole shape, even when another part has the same one. In vt350-lite-50, 184
# groups of same-shaped parts cost 80 MB of a 124 MB file. A link stores no shape, and the GUI tessellates the target
# once for all its links. Links are only for copies a rigid move reproduces: a reflected copy stays a real part.
#
# Report (headless, read-only, never saves):
#   APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage
#   DUPES_MODEL=~/Documents/VT350/vt350-lite-50.FCStd $APP freecadcmd $PWD/platform/freecad/dupes.py
#   optional: DUPES_OUT=<file.json> (every group), DUPES_TOP=25 (groups printed), DUPES_MIN_KB=0 (smaller groups hidden)
#
# From a pass (see cad/passes/lite51_links.py):
#   import dupes
#   for g in dupes.find(doc, dupes.object_bytes(path)):           # groups, the biggest saving first
#       results = dupes.link_copies(doc, g)                       # [(name, box_diff_mm)]; check them, then save
#
# How copies are found: parts are grouped by (face count, volume, area), meshes by (area, box size), within KEY_REL; within a group each part is fitted to the
# first one (its "master") in their own (raw, placement-free) geometry: no move, a translation, or a rotation from the
# principal axes. A fit counts only if every vertex lands within FIT_TOL of a master vertex. A part a reflection fits
# is reported as reflected; one nothing fits is reported as different.
#
# Only plain Part::Features and Mesh::Features whose only parents are containers are candidates: a part another feature
# uses (a Cut's tool, say) or one that rebuilds itself (Part::FeaturePython, e.g. Fasteners screws) is left alone.
# Tests: test_dupes.py (plain python: the file sizes), test_dupes_fc.py (FreeCAD: fit, link).
import os, re, sys, zipfile
import xml.etree.ElementTree as ET

FIT_TOL = 0.02           # mm: a fitted vertex must land within this (a grid cell, +-1 cell) of a master vertex
KEY_REL = 1e-4           # same-key parts: volume and area within this fraction of each other (no rounding boundaries)
CONTAINERS = ("App::Part", "App::DocumentObjectGroup", "App::Link")   # parents that don't use the part's shape


# ---- plain python: what each object costs in the file ----

def object_bytes(fcstd):
    """{object Name: compressed bytes of the files it stores (its shape .brp, its mesh .bms, ...)} of an .FCStd."""
    with zipfile.ZipFile(fcstd) as z:
        size = {i.filename: i.compress_size for i in z.infolist()}
        root = ET.fromstring(z.read("Document.xml"))
    out = {}
    data = root.find("ObjectData")
    for o in (data if data is not None else []):
        n = sum(size.get(e.get("file"), 0) for e in o.iter() if e.get("file"))
        if n: out[o.get("name")] = n
    return out


def file_breakdown(fcstd):
    """{kind: compressed bytes} by file extension (brp shapes, bms meshes, xml, ...) and the total."""
    out = {}
    with zipfile.ZipFile(fcstd) as z:
        for i in z.infolist():
            k = i.filename.rsplit(".", 1)[-1] if "." in i.filename else i.filename
            out[k] = out.get(k, 0) + i.compress_size
    out["total"] = sum(out.values())
    return out


# ---- FreeCAD: grouping, fitting, linking ----

def _fc():
    import FreeCAD
    return FreeCAD


def candidate(o):
    """A part that may be a master or a copy: a plain Part::Feature with solids, or a Mesh::Feature, used by nothing
    but containers."""
    if o.TypeId == "Part::Feature":
        if o.Shape.isNull() or not o.Shape.Solids: return False
    elif o.TypeId != "Mesh::Feature":
        return False
    return all(x.TypeId in CONTAINERS for x in o.InList)


def raw(o):
    """o's geometry in its own frame (placement dropped): a shape, or a mesh."""
    FreeCAD = _fc()
    if o.TypeId == "Mesh::Feature":
        import Mesh
        m = Mesh.Mesh(o.Mesh); m.Placement = FreeCAD.Placement(); return m
    s = o.Shape.copy(); s.Placement = FreeCAD.Placement(); return s


def points(g):
    FreeCAD = _fc()
    if hasattr(g, "Vertexes"): return [v.Point for v in g.Vertexes]
    return [FreeCAD.Vector(*p) for p in g.Topology[0]]


def key(o):
    """(kind, a, b): parts are grouped when the kind is equal and a and b agree within KEY_REL.
    A shape: (TypeId + face count, volume, area). A mesh: (TypeId, area, box diagonal), no volume or point count:
    meshes of one shape can differ by a point, and an open mesh's volume isn't stable (lite-50's board stand-ins,
    which fit each other exactly: volumes 6431.0-6435.7, areas within 3e-6)."""
    if o.TypeId == "Mesh::Feature":
        return (o.TypeId,), o.Mesh.Area, raw(o).BoundBox.DiagonalLength   # raw: a mesh's BoundBox has its Placement
    return (o.TypeId, len(o.Shape.Faces)), o.Shape.Volume, o.Shape.Area


def _close(a, b):
    return abs(a - b) <= KEY_REL * max(abs(a), abs(b), 1e-9)


def cluster(keyed):
    """[(key, obj)] -> lists of objects whose keys match: same kind, volume and area within KEY_REL of the
    cluster's first. Sorted by volume, so a cluster is a run."""
    out = []
    by_kind = {}
    for (kind, vol, area), o in keyed: by_kind.setdefault(kind, []).append((vol, area, o))
    for items in by_kind.values():
        items.sort(key=lambda t: t[0])
        run = []
        for vol, area, o in items:
            if run and not (_close(vol, run[0][0]) and _close(area, run[0][1])):
                out.append(run); run = []
            run.append((vol, area, o))
        if run: out.append(run)
    return [[o for _, _, o in r] for r in out]


def _cells(pts, q):
    return {(round(p.x / q), round(p.y / q), round(p.z / q)) for p in pts}


def misses(pts, cells, q=FIT_TOL):
    """How many of pts are not within one grid cell of a cell in `cells`."""
    n = 0
    for p in pts:
        c = (round(p.x / q), round(p.y / q), round(p.z / q))
        if not any((c[0] + a, c[1] + b, c[2] + d) in cells for a in (-1, 0, 1) for b in (-1, 0, 1) for d in (-1, 0, 1)):
            n += 1
    return n


def _frame(g):
    """(centre, [3 principal axes]) of g's biggest solid (or of a mesh's points)."""
    FreeCAD = _fc()
    if hasattr(g, "Solids"):
        so = max(g.Solids, key=lambda x: x.Volume); P = so.PrincipalProperties
        return so.CenterOfMass, [P["FirstAxisOfInertia"], P["SecondAxisOfInertia"], P["ThirdAxisOfInertia"]]
    return None


def _basis(a):
    FreeCAD = _fc()
    return FreeCAD.Matrix(a[0].x, a[1].x, a[2].x, 0, a[0].y, a[1].y, a[2].y, 0, a[0].z, a[1].z, a[2].z, 0)


def _pairs(pts, gk_pts, q=FIT_TOL):
    """For each of pts, the nearest of gk_pts within a grid cell (or None)."""
    grid = {}
    for p in gk_pts: grid.setdefault((round(p.x / q), round(p.y / q), round(p.z / q)), []).append(p)
    out = []
    for p in pts:
        c = (round(p.x / q), round(p.y / q), round(p.z / q))
        near = [r for a in (-1, 0, 1) for b in (-1, 0, 1) for d in (-1, 0, 1) for r in grid.get((c[0] + a, c[1] + b, c[2] + d), ())]
        out.append(min(near, key=lambda r: (r - p).Length) if near else None)
    return out


def refine(p0, pk, M):
    """The rigid placement that best maps p0 onto pk (least squares, Kabsch), starting from the matrix M whose
    image of p0 lands within a grid cell of pk: the principal axes give the rotation only to ~1e-5."""
    import numpy as np
    FreeCAD = _fc()
    moved = [M.multVec(p) for p in p0]
    near = _pairs(moved, pk)
    A = np.array([[p.x, p.y, p.z] for p, n in zip(p0, near) if n is not None])
    B = np.array([[n.x, n.y, n.z] for n in near if n is not None])
    ca, cb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    t = cb - R @ ca
    m = FreeCAD.Matrix(*[float(x) for row in np.hstack([R, t[:, None]]) for x in row])
    return FreeCAD.Placement(m)


def fit(g0, gk):
    """How gk's raw geometry is g0's moved: -> ("same" | "moved", Placement T with gk = T * g0), ("reflected", None)
    or ("different", None). T is checked: every vertex of T * g0 lands within FIT_TOL of one of gk's."""
    FreeCAD = _fc()
    p0, pk = points(g0), points(gk)
    if len(p0) != len(pk) and abs(len(p0) - len(pk)) > max(2, len(p0) // 1000): return "different", None
    ck = _cells(pk, FIT_TOL)
    if misses(p0, ck) == 0: return "same", FreeCAD.Placement()
    b0, bk = g0.BoundBox, gk.BoundBox
    d = FreeCAD.Vector(bk.XMin - b0.XMin, bk.YMin - b0.YMin, bk.ZMin - b0.ZMin)
    if misses([p + d for p in p0], ck) == 0:          # a box-corner offset is only near: refine it (0.4 um off
        T = refine(p0, pk, FreeCAD.Placement(d, FreeCAD.Rotation()).toMatrix())   # on lite-50's SpeedClips)
        if misses([T.multVec(p) for p in p0], ck) == 0: return "moved", T
    f0, fk = _frame(g0), _frame(gk)
    if f0 is None or fk is None: return "different", None
    (c0, a0), (cK, ak) = f0, fk
    ak = [ak[0], ak[1], ak[0].cross(ak[1])]          # FreeCAD's principal axes aren't always right-handed
    Bk = _basis(ak)
    reflected = False
    for sx in (1, -1):
        for sy in (1, -1):
            for hand in (1, -1):                         # hand -1: a reflection, reported but never linked
                b = [a0[0] * sx, a0[1] * sy, (a0[0] * sx).cross(a0[1] * sy) * hand]
                R = Bk.multiply(_basis(b).transposed())
                M = FreeCAD.Matrix(R); M.move(cK - R.multVec(c0))
                if misses([M.multVec(p) for p in p0], ck) == 0:
                    if hand == -1: reflected = True; continue
                    T = refine(p0, pk, M)
                    if misses([T.multVec(p) for p in p0], ck) == 0: return "moved", T
    return ("reflected" if reflected else "different"), None


class Group:
    """Same-key parts: the master, the copies a rigid move fits [(obj, T)], and the reflections [(obj, "reflected")].
    A same-key part that fits neither way starts a group of its own."""

    def __init__(self, master, copies, unfit, each_bytes):
        self.master, self.copies, self.unfit, self.each_bytes = master, copies, unfit, each_bytes
        self.copy_names = [o.Name for o, _ in copies]          # kept: link_copies deletes the copies

    @property
    def saving(self):
        return sum(self.each_bytes.get(n, 0) for n in self.copy_names)

    def drop(self, names):
        """Leave these copies out (they stay real parts)."""
        names = set(names)
        self.copies = [(o, T) for o, T in self.copies if o.Name not in names]
        self.copy_names = [n for n in self.copy_names if n not in names]

    def __repr__(self):
        return (f"Group({self.master.Label!r}: {len(self.copies)} copies, {len(self.unfit)} unfit, "
                f"saves {self.saving / 1e6:.2f} MB)")


def find(doc, sizes=None, names=None, split=None, skip=()):
    """Groups of copies in doc, the biggest saving first. sizes: object_bytes() of the saved file (else savings are 0).
    names: only consider these object Names (a pass's explicit list). skip: never consider these.
    split(obj) -> a hashable: parts are only grouped with parts of the same value. A link shows its master's colour,
    so a pass that links copies splits by colour (lite-52: 32 copies coloured unlike their master)."""
    sizes = sizes or {}
    skip = set(skip)
    keyed = [(key(o), o) for o in doc.Objects
             if (names is None or o.Name in names) and o.Name not in skip and candidate(o)]
    clusters = cluster(keyed)
    if split is not None:
        parts = []
        for objs in clusters:
            by = {}
            for o in objs: by.setdefault(split(o), []).append(o)
            parts += list(by.values())
        clusters = parts
    out = []
    for objs in clusters:
        if len(objs) < 2: continue
        objs.sort(key=lambda o: o.Name)
        rest = objs
        while len(rest) > 1:                            # a key may hold two different shapes: split by fit
            m, g0 = rest[0], raw(rest[0])
            copies, unfit, left = [], [], []
            for o in rest[1:]:
                how, T = fit(g0, raw(o))
                if T is not None: copies.append((o, T))
                elif how == "reflected": unfit.append((o, how))
                else: left.append(o)
            if copies or unfit: out.append(Group(m, copies, unfit, sizes))
            rest = left
    out.sort(key=lambda g: -g.saving)
    return out


def landing(group):
    """Where each copy's link WOULD land, before linking: [(Name, global box difference in mm)]. The document is
    not changed. A fit within FIT_TOL can still be microns off (lite-51's zip ties: up to 3 um): drop those copies
    (Group.drop) and keep them real, rather than move a part."""
    import linkgeo
    FreeCAD = _fc()
    g0 = raw(group.master)
    out = []
    for o, T in group.copies:
        par = o.getParentGeoFeatureGroup()
        place = (linkgeo.gplace(par) if par is not None else FreeCAD.Placement()).multiply(o.Placement).multiply(T)
        if o.TypeId == "Mesh::Feature":
            import Mesh
            m = Mesh.Mesh(g0); m.transform(place.toMatrix()); want, got = m.BoundBox, linkgeo.gmesh(o).BoundBox
        else:
            sh = g0.copy(); sh.Placement = place; want, got = sh.BoundBox, linkgeo.gshape(o).BoundBox
        out.append((o.Name, max(abs(getattr(want, k) - getattr(got, k))
                                for k in ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax"))))
    return out


def is_trimesh(o, min_faces=500):
    """A solid made from an STL: every face a planar triangle. removeSplitter() can't fix one (LESSONS.md)."""
    if o.TypeId != "Part::Feature" or o.Shape.isNull(): return False
    f = o.Shape.Faces
    return len(f) >= min_faces and all(len(x.Edges) == 3 for x in f)


def link_copies(doc, group):
    """Replace each fitted copy in `group` with an App::Link to the master: same Name, Label, parent, Visibility and
    StandInFor; Placement = the copy's Placement x the fit. -> [(Name, global box difference in mm)] for the caller
    to check. Doesn't recompute the rest of the document or save."""
    import linkgeo
    FreeCAD = _fc()
    out = []
    for o, T in group.copies:
        before = linkgeo.gshape(o).BoundBox if o.TypeId != "Mesh::Feature" else linkgeo.gmesh(o).BoundBox
        name, label, pl, vis = o.Name, o.Label, o.Placement, o.Visibility
        gvis = o.ViewObject.Visibility if getattr(o, "ViewObject", None) is not None else None
        sif = getattr(o, "StandInFor", "")
        parents = [x for x in o.InList if x.TypeId in ("App::Part", "App::DocumentObjectGroup")]
        doc.removeObject(name)
        ln = doc.addObject("App::Link", name)
        if ln.Name != name: raise RuntimeError(f"{name}: the link got Name {ln.Name}; names must be kept")
        ln.LinkedObject = group.master; ln.Label = label; ln.Placement = pl.multiply(T); ln.Visibility = vis
        if gvis is not None and getattr(ln, "ViewObject", None) is not None: ln.ViewObject.Visibility = gvis
        if sif:
            ln.addProperty("App::PropertyString", "StandInFor", "StandIn", "the real part this stands in for")
            ln.StandInFor = sif
        for p in parents: p.addObject(ln)
        ln.recompute()
        after = linkgeo.gshape(ln).BoundBox if not linkgeo.is_mesh(ln) else linkgeo.gmesh(ln).BoundBox
        out.append((name, max(abs(getattr(before, k) - getattr(after, k))
                              for k in ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax"))))
    return out


def report(model, top=25, min_kb=0.0, out=None):
    FreeCAD = _fc()
    sizes = object_bytes(model)
    br = file_breakdown(model)
    doc = FreeCAD.openDocument(model, True)
    groups = find(doc, sizes)
    print(f"{os.path.basename(model)}: {br['total'] / 1e6:.1f} MB compressed "
          f"({', '.join(f'{k} {v / 1e6:.1f}' for k, v in sorted(br.items(), key=lambda kv: -kv[1]) if k != 'total' and v > 1e5)})")
    total = sum(g.saving for g in groups)
    n_unfit = sum(len(g.unfit) for g in groups)
    print(f"{len(groups)} groups of copies; linking every fitted copy saves {total / 1e6:.1f} MB; "
          f"{n_unfit} copies are reflections (they stay real parts)\n")
    print("   saves  each MB  copies  unfit  STL?  master")
    for g in groups[:top]:
        if g.saving < min_kb * 1e3: continue
        print(f"  {g.saving / 1e6:6.2f}  {sizes.get(g.master.Name, 0) / 1e6:7.2f}  {len(g.copies):6d}  {len(g.unfit):5d}"
              f"  {'yes' if is_trimesh(g.master) else '   '}   {g.master.Label[:70]}  [{g.master.Name}]")
    if out:
        import json
        json.dump({"model": os.path.basename(model), "bytes": br, "saving": total,
                   "groups": [{"master": g.master.Name, "label": g.master.Label, "saving": g.saving,
                               "each": sizes.get(g.master.Name, 0), "stl_solid": is_trimesh(g.master),
                               "copies": [o.Name for o, _ in g.copies],
                               "unfit": [[o.Name, why] for o, why in g.unfit]} for g in groups]},
                  open(out, "w"), indent=1)
        print(f"\nwrote {out}")


if __name__ in ("__main__", "dupes"):                     # freecadcmd runs a script as module "dupes"
    if os.environ.get("DUPES_MODEL"):
        try:
            report(os.path.expanduser(os.environ["DUPES_MODEL"]), int(os.environ.get("DUPES_TOP", "25")),
                   float(os.environ.get("DUPES_MIN_KB", "0")), os.environ.get("DUPES_OUT"))
            code = 0
        except Exception:
            import traceback; traceback.print_exc(); code = 1
        sys.stdout.flush(); os._exit(code)                 # os._exit skips the flush (LESSONS.md)
    elif __name__ == "__main__":
        raise SystemExit("set DUPES_MODEL to the .FCStd to report on")
