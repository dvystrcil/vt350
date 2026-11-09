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
# Parallel clash checks (#45, clashlib.py) run on a SAVED model; a pass checks shapes it has not saved yet. The hot
# spot is no_overlap's boolean step, so it goes through Pass.volumes(pairs) -> [volume, ...], which a pass can replace
# (Pass(..., volumes=f)) with a parallel runner without touching the checks.
#
# Gotchas: optimalBoundingBox differs slightly GUI vs headless (tessellation, ~0.14 mm on the StealthMax STEP); some
# STEP parts have a polluted plain BoundBox (StealthMax M_1a.0_Body_BPM: Y to -419, Z to -372). Use obb(), or slice
# with common(), for anything that matters.
import json, os, time, traceback

import FreeCAD, Part

V = FreeCAD.Vector
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
WORK = os.environ.get("VT350_WORK", f"{REPO}/cad/data")
MODELS = "/home/dan/Documents/VT350"
BED_LOWEST_DZ = -241.98       # the bed's bottom of Z travel from the model pose (#74, boolean vs the backbone)
BED_Z = (230.0, 300.0)        # bed-side solids at the model pose: ZMin in this band and ZMax <= its top


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


class Result:
    """A check's outcome: truthy when it passed; the measured values are attributes."""
    def __init__(self, ok, **kw):
        self.ok = bool(ok); self.__dict__.update(kw)

    def __bool__(self): return self.ok

    def __repr__(self): return f"Result({self.__dict__})"


class Model:
    """An opened document: its leaf solids, their global shapes and (lazily) their optimal bounding boxes."""
    def __init__(self, doc):
        self.doc = doc
        self.refresh()

    def refresh(self):
        self.leaves = [o for o in self.doc.Objects if is_leaf(o)]
        self.shapes = {o.Name: gshape(o) for o in self.leaves}
        self._boxes = None

    @property
    def boxes(self):
        if self._boxes is None: self._boxes = {n: obb(s) for n, s in self.shapes.items()}
        return self._boxes

    def root(self, prefix):
        return next(o for o in self.doc.Objects if o.TypeId == 'App::Part' and o.Label.startswith(prefix))

    def leaf(self, prefix):
        return next(o for o in self.leaves if o.Label.startswith(prefix))

    def by_label(self):
        return {o.Label: self.shapes[o.Name] for o in self.leaves}


class Pass:
    def __init__(self, name, work=None, dry=None, volumes=None):
        self.name = name
        self.work = work or WORK
        self.dry = (not FreeCAD.GuiUp) if dry is None else dry
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
        if not self.log_f.closed: self.log_f.close()

    def vol(self, a, b):
        try: return a.common(b).Volume
        except Exception as e: self.log("  boolean failed:", e); return float("inf")

    def volumes(self, pairs):
        """[(a, b), ...] -> [common volume, ...]. Replace (Pass(volumes=...)) to run the booleans in parallel (#45)."""
        return [self.vol(a, b) for a, b in pairs]

    def open(self, path):
        doc = FreeCAD.openDocument(path); self.log("opened", path)
        return Model(doc)

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
        for k, s in others.items():
            if k in skip: continue
            d = shape.distToShape(s)[0]
            dmin = min(dmin, d)
            if d < min_d: near.append((k, round(d, 2)))
        return self._named(Result(not near, near=near, d=dmin), what)

    def lift_out_clear(self, shape, boxes, what, height=200.0, start_z=None, tol=1e-3):
        """boxes {key: BoundBox}: nothing of `shape` (> tol mm3) in the column over each box's XY, from its ZMin (or
        start_z[key]) up to ZMin + height, so each part lifts straight out. r.blocked [(key, volume rounded to 0.1)]."""
        start_z = start_z or {}
        blocked = []
        for k, b in boxes.items():
            col = box(b.XMin, b.XMax, b.YMin, b.YMax, start_z.get(k, b.ZMin), b.ZMin + height)
            v = self.vol(shape, col)
            if v > tol: blocked.append((k, round(v, 1)))
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
