# litelib: the shared skeleton of a lite-N model pass (#93), so a pass is a short spec: inputs, the new parts, and
# named checks. Imported by liteNN_*.py under FreeCAD (GUI = writes the model, headless freecadcmd = dry run).
#
#   import os, sys
#   sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
#   import litelib
#   from litelib import box, gshape, obb, BED_LOWEST_DZ
#
#   def main(p):
#       pr = p.open(SRC); fd = p.open(FSRC)                          # Model: .doc .leaves .shapes .boxes (global, obb)
#       lip = box(x0, x1, y0, y1, z0, z1)
#       p.on_face(lip, -2.0, "lip bottom on the backbone top", top=2.0)
#       p.no_overlap([("left", lip)], pr, lambda r: f"lip x printer: {r.hits[:5]}", exclude=(env.Name,))
#       ... add_solids / resize_envelope / dump ...
#       p.finish([(fd.doc, FDST), (pr.doc, DST)])                      # NOT SAVED / DRY RUN / SAVED, in that order
#   litelib.Pass("liteNN_what").run(main)                               # log at $VT350_WORK/logs/liteNN_what.log
#
# Every named check logs exactly one "ok   ..." or "FAIL ..." line, records a failure, and returns a result that is
# truthy when the check passed and carries the measured numbers (r.frac, r.gap, r.hits, ...). The message `what` is a
# plain string, or a callable that gets the result, so the log line can show the numbers: lambda r: f"... {r.gap:.2f}".
# Anything without a named check goes through p.check(ok, what) like before.
#
# Named checks:
#   on_face(shape, z, what, top=None)              a bottom face of `shape` (area > min_area) lies on the plane Z = z
#   over_material(foot, material, what, min_frac)  fraction of the footprint solid inside `material` (r.frac)
#   clear_of_bed_travel(items, model, what, ...)   bed parts moved down to the bottom of Z travel stay >= min_gap above
#                                                  every item (r.gap, r.who); box test: exact for box-shaped items,
#                                                  conservative for the bed
#   no_overlap(items, model, what, exclude)        no item overlaps a printer solid at the model pose (r.hits)
#   min_distance(shape, others, what, min_d)       shape keeps >= min_d off each of `others` (r.near, r.d)
#   lift_out_clear(shape, boxes, what, ...)        nothing of `shape` in the column above any of `boxes` (r.blocked)
#
# Parallel (#45): the named checks' heavy work goes through ONE hook, Pass.map(fn, tasks) -> [fn(*task), ...], with
# fn one of the module-level ops below: _t_vol (no_overlap's booleans, via Pass.volumes), _t_dist (min_distance),
# _t_col + _t_above (lift_out_clear's column booleans and its exact line grid, split into strips) and _t_obb
# (Model.boxes, the only heavy work in clear_of_bed_travel). With workers > 1 (Pass(workers=N), else VT350_WORKERS,
# else available CPUs - 2, see litepool.py) map runs the tasks on N persistent headless freecadcmd workers.
# Results are bit-identical to serial: a shape that comes from a saved document is NOT serialised (a binary BREP
# round trip moved one StealthMax part's placement by 1 ulp); the worker opens the same file and rebuilds it with
# gshape(), the same code as Model. Only shapes the pass made itself (a box, a fused ring) travel as binary BREP.
# Every shipped shape carries a fingerprint (placement matrix + plain BoundBox); a worker whose copy doesn't match
# (the pass changed the document in memory, or a GUI tessellation changed the box) answers Stale and the parent
# redoes that task itself (counted in Pass.stale). Logging stays in the parent, in order, so a parallel run's log is
# line-for-line the serial one. Pass.volumes(pairs) is kept; Pass(volumes=f) still replaces it.
# In a GUI pass the workers are headless: an optimalBoundingBox they compute is the headless one (see Gotchas).
# Memory: each worker opens its own copy of every document it needs. So a task on a shape of a document bigger than
# worker_doc_mb (default WORKER_DOC_MB, env VT350_WORKER_DOC_MB) runs in the parent: the workers never open the
# printer model. A distance (_t_dist) to a shape with more than heavy_faces faces (default HEAVY_FACES, env
# VT350_HEAVY_FACES) also runs in the parent, so at most one such 10 GB task runs at a time, as in serial. Workers
# give freed memory back after every task (litepool.trim). The worker count is capped by free memory
# (litepool.worker_count): each worker <= ~1.5 GB, the reserve covers the parent at its serial peak.
#
# Gotchas: optimalBoundingBox differs slightly GUI vs headless (tessellation, ~0.14 mm on the StealthMax STEP); some
# STEP parts have a polluted plain BoundBox (StealthMax M_1a.0_Body_BPM: Y to -419, Z to -372). Use obb(), or slice
# with common(), for anything that matters.
import json, os, sys, time, traceback

import FreeCAD, Part
import litepool

V = FreeCAD.Vector
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
WORK = os.environ.get("VT350_WORK", f"{REPO}/cad/data")
MODELS = "/home/dan/Documents/VT350"
BED_LOWEST_DZ = -241.98       # the bed's bottom of Z travel from the model pose (#74, boolean vs the backbone)
BED_Z = (230.0, 300.0)        # bed-side solids at the model pose: ZMin in this band and ZMax <= its top
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get("FREECAD_APPIMAGE", "/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage")
FREECADCMD = os.environ.get("FREECADCMD", f"{APP} freecadcmd").split()
WORKER_DOC_MB = 100.0         # tasks on shapes of a saved document bigger than this run in the parent (#45): a worker
                              # that opens the 173 MB printer model costs GBs; the 49 MB filter document is fine
HEAVY_FACES = 10000           # a distance to a shape with more faces runs in the parent (#45): distToShape(ring,
                              # StealthMax carbon basket, 18,651 faces) took 10.2 GB and 239 s; every other op on
                              # every lite-30 part stayed under 1.5 GB. One at a time, as serial would.


def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s


def obb(s):
    try: return s.optimalBoundingBox(True, False)
    except Exception: return s.BoundBox


def is_leaf(o):
    return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and bool(o.Shape.Solids) and o.TypeId != 'App::Part'


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def print_area(log=None, src=None):
    """(width, depth) in mm the VT350 can print, as print_area.py computes it from the committed sweep log
    (data/logs/sweep_toolhead.log) and sweep_toolhead.py's plate constants."""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("print_area", os.path.join(here, "print_area.py"))
    pa = importlib.util.module_from_spec(spec); spec.loader.exec_module(pa)
    log = log or os.path.join(os.path.dirname(here), "data", "logs", "sweep_toolhead.log")
    src = src or os.path.join(here, "sweep_toolhead.py")
    a = pa.printable(pa.parse_reach(open(log).read()), pa.parse_plate(open(src).read()))
    return a["width"], a["depth"]


def overlaps_xy(a, b):
    return a.XMin < b.XMax and a.XMax > b.XMin and a.YMin < b.YMax and a.YMax > b.YMin


# ---- the ops Pass.map runs (in the parent, or by name in a worker). Arguments are shapes, or in a worker the
# references _S() turns back into shapes.
class _Err:
    """An op that raised: its message, as map returns it."""
    def __init__(self, msg): self.msg = msg

    def __repr__(self): return f"_Err({self.msg!r})"


_wshapes, _wdocs, _wpieces = {}, {}, {}      # worker side: shape key -> shape (or None = stale), path -> doc, pieces
_STALE = object()


def _fp(s):
    b = s.BoundBox
    return tuple(s.Placement.Matrix.A), (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)


def _S(x):
    """A shape reference from the parent -> the shape (loaded once per worker); anything else unchanged."""
    if not (isinstance(x, tuple) and len(x) == 5 and x[0] == "__shape__"): return x
    _, key, kind, src, fp = x
    s = _wshapes.get(key)
    if s is None:
        if kind == "doc":
            path, name = src
            if path not in _wdocs: _wdocs[path] = FreeCAD.openDocument(path)
            o = _wdocs[path].getObject(name)
            s = gshape(o) if o is not None else _STALE
        else:
            s = Part.Shape(); s.importBinary(src)
        if s is not _STALE and _fp(s) != fp: s = _STALE
        _wshapes[key] = s
    if s is _STALE: raise litepool.Stale(f"shape {key} ({kind} {src}) differs from the parent's")
    return s


def _t_vol(a, b):
    return _S(a).common(_S(b)).Volume


def _t_dist(a, b):
    return _S(a).distToShape(_S(b))[0]


def _t_obb(s):
    b = obb(_S(s)); return b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax


def _t_col(s, col):
    """col (x0, x1, y0, y1, z0, z1): volume of `s` inside that box."""
    return _S(s).common(box(*col)).Volume


def _t_above(s, col, part, z0, grid, k=0, n=1):
    """above_material for the piece of `s` inside col, on strip k of n."""
    s, part = _S(s), _S(part)
    key = (id(s), col)
    if key not in _wpieces: _wpieces[key] = (s, s.common(box(*col)))   # s kept: its id can't be reused
    return above_material(_wpieces[key][1], part, z0, grid, k, n)


def _moved(s, v):
    """A copy that shares the geometry, with the placement moved by v (clashlib's _shifted)."""
    c = s.copy(False); c.Placement = FreeCAD.Placement(v, FreeCAD.Rotation()).multiply(s.Placement); return c


def _t_contact(a, b, direction, lo, hi, ta=(0.0, 0.0, 0.0), tb=(0.0, 0.0, 0.0), step=None, eps=None, tol=None):
    """#82: `a` moved by ta, then `direction` (-1 down, +1 up) * d along Z, against `b` moved by tb: contact.py's
    first_contact over d in [lo, hi], each probe a common() volume. -> {"kind": "contact"|"clear"|"start", ...}"""
    import contact
    sa, sb = _S(a), _S(b)
    if any(tb): sb = _moved(sb, V(*tb))
    t = V(*ta)
    def probe(d):
        return _moved(sa, t + V(0, 0, direction * d)).common(sb).Volume
    kw = {k: v for k, v in (("step", step), ("eps", eps), ("tol", tol)) if v is not None}
    return contact.first_contact(probe, lo, hi, **kw)


def _t_zspan(s, pts, z0, z1):
    """#82 ray probes: vertical lines at pts [(x, y)] from z1 down to z0; (lowest, highest) Z of `s`'s material on
    them, or None if no line meets it."""
    s = _S(s)
    zs = []
    for x, y in pts:
        for e in Part.makeLine(V(x, y, z1), V(x, y, z0)).common(s).Edges:
            zs += [v.Point.z for v in e.Vertexes]
    return (min(zs), max(zs)) if zs else None


def grid_columns(lo, hi, grid, k=0, n=1):
    """The grid's column centres from lo to hi (accumulated exactly as the serial loop did), every n-th from k."""
    xs, x = [], lo + grid / 2
    while x < hi:
        xs.append(x); x += grid
    return xs[k::n]


def above_material(piece, part, z0, grid, k=0, n=1):
    """True if, on any vertical line of the grid over `piece`, a stretch of `piece` lies above a stretch of
    `part` (both above z0): lifting the part straight up would run into the piece there. k/n: only the grid's
    X columns k, k+n, ... (a strip of the work; any() over all strips is the answer)."""
    bb = piece.BoundBox
    if not piece.Solids: return False
    pb = part.BoundBox
    def zs(line, s):
        return [(min(v.Point.z for v in e.Vertexes), max(v.Point.z for v in e.Vertexes)) for e in line.common(s).Edges]
    for x in grid_columns(bb.XMin, bb.XMax, grid, k, n):
        y = bb.YMin + grid / 2
        while y < bb.YMax:
            ln = Part.makeLine(V(x, y, max(bb.ZMax, pb.ZMax) + 1), V(x, y, min(z0, pb.ZMin) - 1))
            rz = zs(ln, piece)
            if rz:
                pz = [(a, b) for a, b in zs(ln, part) if b > z0 + 1e-6]
                if any(r0 >= p1 - 1e-6 for r0, _ in rz for _, p1 in pz): return True
            y += grid
    return False


class Result:
    """A check's outcome: truthy when it passed; the measured values are attributes."""
    def __init__(self, ok, **kw):
        self.ok = bool(ok); self.__dict__.update(kw)

    def __bool__(self): return self.ok

    def __repr__(self): return f"Result({self.__dict__})"


class Model:
    """An opened document: its leaf solids, their global shapes and (lazily) their optimal bounding boxes.
    Opened through a Pass (p.open), the boxes are computed through p.map, and its shapes are known to come from
    the saved file (so a worker can rebuild them from it instead of receiving them)."""
    def __init__(self, doc, p=None):
        self.doc, self.p = doc, p
        self.refresh()

    def refresh(self):
        self.leaves = [o for o in self.doc.Objects if is_leaf(o)]
        self.shapes = {o.Name: gshape(o) for o in self.leaves}
        self._boxes = None
        if self.p is not None and self.doc.FileName:
            mb = os.path.getsize(self.doc.FileName) / 2 ** 20
            for n, s in self.shapes.items(): self.p._origin[id(s)] = (s, self.doc.FileName, n, mb)

    @property
    def boxes(self):
        if self._boxes is None:
            names = list(self.shapes)
            vals = (self.p.map(_t_obb, [(self.shapes[n],) for n in names]) if self.p is not None
                    else [_t_obb(self.shapes[n]) for n in names])
            bad = [(n, v.msg) for n, v in zip(names, vals) if isinstance(v, _Err)]
            if bad: raise RuntimeError(f"optimal boxes failed: {bad[:3]}")
            self._boxes = {n: FreeCAD.BoundBox(*v) for n, v in zip(names, vals)}
        return self._boxes

    def root(self, prefix):
        return next(o for o in self.doc.Objects if o.TypeId == 'App::Part' and o.Label.startswith(prefix))

    def leaf(self, prefix):
        return next(o for o in self.leaves if o.Label.startswith(prefix))

    def by_label(self):
        return {o.Label: self.shapes[o.Name] for o in self.leaves}


class Pass:
    def __init__(self, name, work=None, dry=None, volumes=None, workers=None, worker_doc_mb=None, heavy_faces=None):
        self.name = name
        self.work = work or WORK
        self.dry = (not FreeCAD.GuiUp) if dry is None else dry
        self.workers = litepool.worker_count() if workers is None else int(workers)
        if self.workers < 1: raise ValueError(f"workers={workers} must be >= 1")
        self.worker_doc_mb = float(worker_doc_mb if worker_doc_mb is not None
                                   else os.environ.get("VT350_WORKER_DOC_MB", WORKER_DOC_MB))
        self.heavy_faces = int(heavy_faces if heavy_faces is not None else os.environ.get("VT350_HEAVY_FACES", HEAVY_FACES))
        self.parent_tasks, self._faces = 0, {}
        self._pool, self._origin, self._refs, self.stale = None, {}, {}, 0
        os.makedirs(self.work + "/logs", exist_ok=True)
        self.log_path = f"{self.work}/logs/{name}.log"
        self.log_f = open(self.log_path, "w"); self.t0 = time.time()
        self.errs = []
        if volumes is not None: self.volumes = volumes

    # ---- skeleton
    def log(self, *a):
        self.log_f.write(f"[{time.time()-self.t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); self.log_f.flush()

    def check(self, ok, what):
        self.log(("ok   " if ok else "FAIL ") + what)
        if not ok: self.errs.append(what)
        return bool(ok)

    def _named(self, res, what):
        self.check(res.ok, what(res) if callable(what) else what)
        return res

    def close(self):
        if self._pool is not None:
            self._pool.close(); self._pool = None
        if not self.log_f.closed: self.log_f.close()

    def vol(self, a, b):
        try: return a.common(b).Volume
        except Exception as e: self.log("  boolean failed:", e); return float("inf")

    # ---- the parallel hook (#45)
    def map(self, fn, tasks):
        """[fn(*task), ...] in order, an op that raises -> _Err(message). fn: a module-level op of this module.
        Serial (in this process) with workers == 1 or fewer than 2 tasks; else on the worker pool."""
        tasks = [tuple(t) for t in tasks]
        if self.workers == 1: return [self._inline(fn, t) for t in tasks]
        if sys.modules[__name__].__dict__.get(fn.__name__) is not fn: raise ValueError(f"{fn!r} is not a litelib op")
        far = [i for i, t in enumerate(tasks) if not self._big(t) and not self._heavy(fn, t)]   # the rest stays here
        if len(far) < 2: return [self._inline(fn, t) for t in tasks]
        if self._pool is None:
            self._pool = litepool.Pool(self.workers, cmd=FREECADCMD, path=[HERE])
            print(f"litelib: {self.workers} workers for {self.name}", file=sys.stderr, flush=True)
        res = dict(zip(far, self._pool.map(__name__, fn.__name__, [tuple(self._enc(a) for a in tasks[i]) for i in far])))
        out = []
        for i, t in enumerate(tasks):
            if i not in res: self.parent_tasks += 1; out.append(self._inline(fn, t)); continue
            st, v = res[i]
            if st == "ok": out.append(v)
            elif st == "err": out.append(_Err(v))
            else: self.stale += 1; out.append(self._inline(fn, t))
        return out

    def _heavy(self, fn, t):
        """True for a distance to a shape with more than heavy_faces faces (counted once per shape)."""
        if fn is not _t_dist: return False
        for a in t:
            if isinstance(a, Part.Shape):
                e = self._faces.get(id(a))
                if e is None or e[0] is not a: e = self._faces[id(a)] = (a, len(a.Faces))
                if e[1] > self.heavy_faces: return True
        return False

    def _big(self, t):
        """True if a shape in task t comes from a saved document over worker_doc_mb."""
        for a in t:
            org = self._origin.get(id(a)) if isinstance(a, Part.Shape) else None
            if org is not None and org[0] is a and org[3] > self.worker_doc_mb: return True
        return False

    @staticmethod
    def _inline(fn, t):
        try: return fn(*t)
        except Exception as e: return _Err(str(e))

    def _enc(self, x):
        if isinstance(x, Part.Shape):
            e = self._refs.get(id(x))
            if e is None or e[0] is not x:                       # e[0] keeps x alive, so its id stays unique
                key = len(self._refs)
                org = self._origin.get(id(x))
                if org is not None and org[0] is x: kind, src = "doc", (org[1], org[2])
                else:
                    src = os.path.join(self._pool.dir, f"s{key}.brp"); x.exportBinary(src); kind = "brep"
                e = (x, ("__shape__", key, kind, src, _fp(x))); self._refs[id(x)] = e
            return e[1]
        return x

    def volumes(self, pairs):
        """[(a, b), ...] -> [common volume, ...] through map (a failed boolean: logged, inf). Pass(volumes=f) replaces it."""
        out = []
        for v in self.map(_t_vol, pairs):
            if isinstance(v, _Err): self.log("  boolean failed:", v.msg); v = float("inf")
            out.append(v)
        return out

    def open(self, path):
        doc = FreeCAD.openDocument(path); self.log("opened", path)
        return Model(doc, self)

    def run(self, body, exit=True):
        """body(self) inside the pass's try/except: an exception is logged as FAILED + traceback, never raised.
        exit=True ends the process with os._exit(0) (a GUI run closes FreeCAD's script without the app's handler)."""
        try:
            body(self)
        except Exception:
            self.log("FAILED\n" + traceback.format_exc())
        finally:
            self.close()
            if exit: os._exit(0)

    # ---- named checks
    def on_face(self, shape, z, what, top=None, min_area=100.0, tol=1e-6):
        """A planar face of `shape`, area > min_area, lies at Z = z with the material above it (a bottom face);
        with `top`, the shape's top is also at Z = top."""
        bottom = []
        for f in shape.Faces:
            fb = f.BoundBox
            if abs(fb.ZMin - z) > tol or abs(fb.ZMax - z) > tol or f.Area <= min_area: continue
            c = f.CenterOfMass
            if f.isInside(c, tol, True) and shape.isInside(c + V(0, 0, 0.01), tol, False):   # material above it
                bottom.append(f)
        ok = bool(bottom) and (top is None or abs(shape.BoundBox.ZMax - top) < tol)
        return self._named(Result(ok, faces=len(bottom), zmax=shape.BoundBox.ZMax), what)

    def over_material(self, foot, material, what, min_frac=0.9):
        """foot: a thin solid under the part's footprint; frac = its volume inside `material` / its volume."""
        frac = self.vol(foot, material) / foot.Volume
        return self._named(Result(frac > min_frac, frac=frac), what)

    def clear_of_bed_travel(self, items, model, what, dz=BED_LOWEST_DZ, min_gap=5.0, bed_z=BED_Z):
        """items [(tag, shape)]: every bed-side solid of `model` (box ZMin in bed_z, ZMax <= bed_z[1]) moved by dz,
        over an item's XY box, keeps >= min_gap above the item's top. r.gap = worst (999 if none), r.who."""
        boxes = model.boxes
        bed = [o for o in model.leaves if bed_z[0] <= boxes[o.Name].ZMin <= bed_z[1] and boxes[o.Name].ZMax <= bed_z[1]]
        worst = (999, "")
        for tag, s in items:
            hb = s.BoundBox
            for o in bed:
                b = boxes[o.Name]
                if overlaps_xy(b, hb):
                    gap = b.ZMin + dz - hb.ZMax
                    if gap < worst[0]: worst = (gap, f"{tag} vs {o.Label}")
        return self._named(Result(worst[0] >= min_gap, gap=worst[0], who=worst[1]), what)

    def no_overlap(self, items, model, what, exclude=(), tol=1e-3):
        """items [(tag, shape)] vs every leaf of `model` but `exclude` (Names): box prefilter (the leaf's optimal box
        vs the item's BoundBox), then the common() volume through self.volumes(). r.hits [(tag, leaf Label)]."""
        cand = [(tag, s, o) for tag, s in items for o in model.leaves
                if o.Name not in exclude and model.boxes[o.Name].intersect(s.BoundBox)]
        vols = self.volumes([(s, model.shapes[o.Name]) for _, s, o in cand])
        hits = [(tag, o.Label) for (tag, _, o), v in zip(cand, vols) if v > tol]
        return self._named(Result(not hits, hits=hits), what)

    def min_distance(self, shape, others, what, min_d, skip=()):
        """others {key: shape}: r.near [(key, distance rounded to 0.01)] for those closer than min_d; r.d = the
        smallest distance (inf with none)."""
        near, dmin = [], float("inf")
        keys = [k for k in others if k not in skip]
        for k, d in zip(keys, self.map(_t_dist, [(shape, others[k]) for k in keys])):
            if isinstance(d, _Err): raise RuntimeError(f"distToShape failed for {k}: {d.msg}")
            dmin = min(dmin, d)
            if d < min_d: near.append((k, round(d, 2)))
        return self._named(Result(not near, near=near, d=dmin), what)

    def lift_out_clear(self, shape, boxes, what, height=200.0, start_z=None, tol=1e-3, parts=None, grid=1.0):
        """boxes {key: BoundBox}: nothing of `shape` (> tol mm3) in the column over each box's XY, from its ZMin (or
        start_z[key]) up to ZMin + height, so each part lifts straight out. r.blocked [(key, volume rounded to 0.1)].
        The box column is conservative: a part's box also covers XY it has no material over (a chamfered corner, an
        L). With parts {key: shape}, a flagged part gets an exact second stage: vertical lines on a `grid` mm grid
        through the piece of `shape` in its column; blocked only where that piece lies above the part's own material
        (above start_z)."""
        start_z = start_z or {}
        keys = list(boxes)
        cols = [(b.XMin, b.XMax, b.YMin, b.YMax, start_z.get(k, b.ZMin), b.ZMin + height)
                for k, b in ((k, boxes[k]) for k in keys)]
        vs = []
        for v in self.map(_t_col, [(shape, c) for c in cols]):
            if isinstance(v, _Err): self.log("  boolean failed:", v.msg); v = float("inf")
            vs.append(v)
        exact = [i for i, k in enumerate(keys) if vs[i] > tol and parts is not None and k in parts]
        n = 1 if self.workers == 1 else 2 * self.workers                 # strips per part for the exact stage
        res = self.map(_t_above, [(shape, cols[i], parts[keys[i]], cols[i][4], grid, j, n) for i in exact for j in range(n)]) \
            if exact else []
        bad = [r.msg for r in res if isinstance(r, _Err)]
        if bad: raise RuntimeError(f"lift-out exact stage failed: {bad[0]}")
        above = {i: any(res[j * n:(j + 1) * n]) for j, i in enumerate(exact)}
        blocked = [(k, round(vs[i], 1)) for i, k in enumerate(keys) if vs[i] > tol and above.get(i, True)]
        return self._named(Result(not blocked, blocked=blocked), what)

    def fits_print_area(self, shape, what, area=None, margin=0.0):
        """A part printed flat (as modelled, Z up) fits the VT350's printable area, either way round, with `margin`
        spare on every side. area (width, depth): default print_area(). r.size (dx, dy), r.area, r.rotated."""
        area = area or print_area()
        bb = obb(shape); dx, dy = bb.XLength, bb.YLength
        w, d = area[0] - 2 * margin, area[1] - 2 * margin
        straight, turned = dx <= w and dy <= d, dy <= w and dx <= d
        return self._named(Result(straight or turned, size=(round(dx, 2), round(dy, 2)), area=tuple(area),
                                  rotated=not straight and turned), what)

    # ---- writing
    def add_solids(self, doc, group, items, name, label, color=(0.89, 0.4, 0.16)):
        """items [(tag, shape)] -> new Part::Features in `group`, Label = label.format(tag); colour in GUI mode."""
        objs = []
        for tag, s in items:
            n = doc.addObject('Part::Feature', name); n.Shape = s; group.addObject(n)
            n.Label = label.format(tag)
            if FreeCAD.GuiUp: n.ViewObject.ShapeColor = color
            objs.append(n)
        doc.recompute()
        return objs

    def resize_envelope(self, model, env, bb, label, root="4040-350x350x250 Voron Trident"):
        """The printer's placeholder box for a separate document (ebox, filter): reshaped to the GLOBAL box bb,
        stored in the root App::Part's frame; the document is recomputed and the new box logged."""
        e = box(bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)
        e.Placement = model.root(root).getGlobalPlacement().inverse().multiply(e.Placement)
        env.Shape = e; env.Label = label
        model.doc.recompute()
        self.log("envelope:", gshape(env).BoundBox)

    def dump(self, obj):
        json.dump(obj, open(f"{self.work}/logs/{self.name}.json", "w"), indent=1)

    def finish(self, saves):
        """saves [(doc, path)]: written in order only in GUI mode and only with no failed check."""
        self.log(f"verify: {len(self.errs)} problems"); [self.log("  " + x) for x in self.errs]
        if self.errs: self.log("NOT SAVED")
        elif self.dry: self.log("DRY RUN (headless): all checks passed, not saved")
        else:
            for doc, path in saves:
                doc.saveAs(path); self.log("SAVED", path, os.path.getsize(path))
