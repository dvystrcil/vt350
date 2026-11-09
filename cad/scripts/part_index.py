# part_index (#90): a per-part bounding-box index saved beside each model, so layout questions are a jq query instead
# of a FreeCAD session. One sidecar per model, <model>.parts.json, written next to <model>.FCStd. The model itself is
# never saved or modified.
#
#   Write (FreeCAD, headless; skips a model whose index is fresh, VT350_INDEX_FORCE=1 rewrites it):
#     VT350_INDEX_MODELS=/home/dan/Documents/VT350/vt350-lite-29.FCStd:... VT350_WORKERS=1 \
#       $APP freecadcmd $PWD/cad/scripts/part_index.py           # log: $VT350_WORK/logs/part_index.log, ends
#                                                                 # "part_index: done" (exit code means nothing)
#   Check (plain python3, no FreeCAD, ~0.3 s per 170 MB):
#     python3 cad/scripts/part_index.py --check MODEL.FCStd ...   # fresh/stale/missing/invalid; exit 0 = all fresh
#   Query:
#     jq -r '.parts[] | select(.bbox.zmax < -60) | .label' ~/Documents/VT350/vt350-filter-3.parts.json
#
# Also written by refresh.py's first step (vt350-lite-N + the companions its pass saved) and by
# cad/render/export_meshes.py for the model and every VT350_EXTRA file it exports (non-fatal there).
#
# Format "vt350-part-index/1":
#   model      the .FCStd basename
#   source     {size, mtime (UTC, informational), sha256} of the model the index was made from. Fresh = size and
#              sha256 match the file now (a copy or restore with a new mtime is still fresh).
#   bbox       {method: "optimalBoundingBox(True, False)", mode: "gui" | "headless", freecad: "26.3.0"}. The optimal box
#              differs slightly GUI vs headless (tessellation, ~0.14 mm on the StealthMax STEP; litelib Gotchas), so
#              the mode is recorded. A GUI run computes every box in the GUI process, never on litelib's (headless)
#              workers, so one index never mixes the two.
#   generated  UTC time; seconds = time spent on the boxes
#   parts      one per litelib leaf solid (litelib.is_leaf, the set every lite-N check uses), sorted by name:
#              name (FreeCAD object Name, unique), label, path (group labels from the root down, [] = top level),
#              material (ShapeMaterial.Name, "Default" when unset), consumed (true when another leaf feature uses it,
#              e.g. a boolean's base/tool: the rule export_meshes.py skips it by), bbox {xmin..zmax} GLOBAL mm, rounded
#              to 0.1 um. A part whose optimalBoundingBox throws gets its plain BoundBox (litelib.obb), as in the checks.
import datetime, hashlib, json, os, sys, time

FORMAT = "vt350-part-index/1"
METHOD = "optimalBoundingBox(True, False)"
MODES = ("gui", "headless")
BOX_KEYS = ("xmin", "ymin", "zmin", "xmax", "ymax", "zmax")
PART_KEYS = {"name": str, "label": str, "path": list, "material": str, "consumed": bool, "bbox": dict}
TOP_KEYS = ("format", "model", "source", "bbox", "generated", "seconds", "parts")
ROUND = 4


# ---- plain python3: names, fingerprint, schema, staleness
def sidecar(model):
    base = model[:-len(".FCStd")] if model.endswith(".FCStd") else model
    return base + ".parts.json"


def _utc(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()


def fingerprint(model):
    st = os.stat(model)
    return {"size": st.st_size, "mtime": _utc(st.st_mtime), "sha256": _sha256(model)}


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate(idx):
    """Problems with an index (list of strings); [] = valid."""
    if not isinstance(idx, dict): return ["index is not an object"]
    bad = [f"missing {k}" for k in TOP_KEYS if k not in idx]
    if bad: return bad
    if idx["format"] != FORMAT: bad.append(f"format {idx['format']!r} is not {FORMAT!r}")
    if not isinstance(idx["model"], str): bad.append("model is not a string")
    src = idx["source"]
    if not isinstance(src, dict): bad.append("source is not an object")
    else:
        if not isinstance(src.get("size"), int) or isinstance(src.get("size"), bool): bad.append("source.size missing or not an int")
        if not isinstance(src.get("mtime"), str): bad.append("source.mtime missing or not a string")
        if not isinstance(src.get("sha256"), str) or len(src.get("sha256")) != 64: bad.append("source.sha256 missing or not a sha256")
    bb = idx["bbox"]
    if not isinstance(bb, dict): bad.append("bbox is not an object")
    else:
        if bb.get("method") != METHOD: bad.append(f"bbox.method {bb.get('method')!r} is not {METHOD!r}")
        if bb.get("mode") not in MODES: bad.append(f"bbox.mode {bb.get('mode')!r} is not one of {MODES}")
        if not isinstance(bb.get("freecad"), str): bad.append("bbox.freecad missing or not a string")
    if not isinstance(idx["generated"], str): bad.append("generated is not a string")
    if not _num(idx["seconds"]): bad.append("seconds is not a number")
    if not isinstance(idx["parts"], list): return bad + ["parts is not a list"]
    seen = set()
    for i, p in enumerate(idx["parts"]):
        where = f"parts[{i}]"
        if not isinstance(p, dict): bad.append(f"{where} is not an object"); continue
        where = f"parts[{i}] {p.get('name')!r}"
        for k, t in PART_KEYS.items():
            if k not in p: bad.append(f"{where}: missing {k}")
            elif not isinstance(p[k], t): bad.append(f"{where}: {k} is not {t.__name__}")
        if isinstance(p.get("path"), list) and not all(isinstance(x, str) for x in p["path"]):
            bad.append(f"{where}: path has a non-string")
        b = p.get("bbox")
        if isinstance(b, dict):
            if not all(_num(b.get(k)) for k in BOX_KEYS): bad.append(f"{where}: bbox needs numbers {BOX_KEYS}")
            else:
                for a in "xyz":
                    if b[a + "min"] > b[a + "max"]: bad.append(f"{where}: bbox {a}min > {a}max")
        if p.get("name") in seen: bad.append(f"{where}: duplicate name")
        seen.add(p.get("name"))
    return bad


def load(path):
    """The parsed index, or None if the file is missing or isn't JSON."""
    try:
        with open(path) as f: return json.load(f)
    except (OSError, ValueError): return None


def write(idx, path):
    """Validate, then write atomically (tmp file + rename in the same folder). Invalid -> ValueError, nothing written."""
    bad = validate(idx)
    if bad: raise ValueError(f"invalid index for {path}: {bad[:5]}")
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as f: json.dump(idx, f, indent=1); f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.remove(tmp)


def status(model):
    """'fresh' | 'stale' | 'missing' | 'invalid' for the model's sidecar."""
    path = sidecar(model)
    if not os.path.exists(path): return "missing"
    idx = load(path)
    if idx is None or validate(idx): return "invalid"
    src = idx["source"]
    if src["size"] != os.path.getsize(model) or src["sha256"] != _sha256(model): return "stale"
    return "fresh"


def is_fresh(model):
    return status(model) == "fresh"


def main(argv):
    if len(argv) < 2 or argv[0] != "--check":
        print("usage: part_index.py --check MODEL.FCStd [...]   (writing an index needs FreeCAD: see the header)",
              file=sys.stderr)
        return 2
    rc = 0
    for m in argv[1:]:
        if not os.path.isfile(m): print(f"part_index: no such model {m}", file=sys.stderr); return 2
        s = status(m)
        print(f"{s:<8} {m}")
        if s != "fresh": rc = 1
    return rc


# ---- FreeCAD side
def _rbox(b):
    return {k: round(float(v), ROUND) for k, v in zip(BOX_KEYS, (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))}


def index_doc(doc, model, p=None):
    """The index of an opened document `doc` saved at `model`. p: a litelib.Pass whose workers compute the boxes
    (headless only; a GUI run computes them here, so the mode is one or the other)."""
    import FreeCAD, litelib
    gui = bool(FreeCAD.GuiUp)
    t0 = time.time()
    m = litelib.Model(doc, None if gui else p)
    boxes = m.boxes
    seconds = time.time() - t0
    leaves = {o.Name for o in m.leaves}
    cands = {}                       # object Name -> every container whose Group lists it
    for g in doc.Objects:
        for k in (getattr(g, 'Group', []) or []): cands.setdefault(k.Name, []).append(g)

    def above(g, seen=()):           # every container g sits in, transitively
        r = set()
        for c in cands.get(g.Name, []):
            if c.Name not in seen and c.Name not in r: r |= {c.Name} | above(c, seen + (g.Name,))
        return r

    par = {}                         # the innermost container: an object inside a group inside an App::Part is listed
    for n, cs in cands.items():      # in both Groups; the group is the one the App::Part is above
        inner = [c for c in cs if not any(c.Name in above(x) for x in cs if x is not c)]
        par[n] = inner[0] if inner else cs[0]

    def path(o):
        r, q = [], par.get(o.Name)
        while q is not None: r.append(q.Label); q = par.get(q.Name)
        return list(reversed(r))

    parts = []
    for o in sorted(m.leaves, key=lambda o: o.Name):
        parts.append({"name": o.Name, "label": o.Label, "path": path(o),
                      "material": getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default',
                      "consumed": any(x.Name in leaves for x in o.InList if x.TypeId != 'App::Part'),
                      "bbox": _rbox(boxes[o.Name])})
    return {"format": FORMAT, "model": os.path.basename(model), "source": fingerprint(model),
            "bbox": {"method": METHOD, "mode": "gui" if gui else "headless", "freecad": ".".join(FreeCAD.Version()[:3])},
            "generated": _utc(time.time()), "seconds": round(seconds, 2), "parts": parts}


def refresh(doc, model, p=None, force=False):
    """Write the sidecar of `model` (open as `doc`) unless it is fresh. -> 'fresh' (skipped) or 'written'."""
    if not force and is_fresh(model): return "fresh"
    write(index_doc(doc, model, p), sidecar(model))
    return "written"


def run(models, force=False):
    """freecadcmd entry: index each model through a litelib Pass (log + workers), closing each document after."""
    import FreeCAD, litelib
    p = litelib.Pass("part_index")
    def body(p):
        if not models: raise ValueError("no models: set VT350_INDEX_MODELS (':'-separated .FCStd paths)")
        for model in models:
            if not os.path.isfile(model): raise FileNotFoundError(f"no such model {model}")
            if not force and is_fresh(model): p.log(f"fresh   {sidecar(model)}"); continue
            doc = FreeCAD.openDocument(model); p.log("opened", model)
            try:
                idx = index_doc(doc, model, p); write(idx, sidecar(model))
                p.log(f"written {sidecar(model)}  {len(idx['parts'])} parts, {idx['bbox']['mode']} boxes in "
                      f"{idx['seconds']} s, {os.path.getsize(sidecar(model))} bytes")
            finally:
                FreeCAD.closeDocument(doc.Name)
        p.log(f"part_index: done ({len(models)} models)")
    p.run(body)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
elif __name__ == "part_index" and os.path.basename(sys.argv[-1] if sys.argv else "") == "part_index.py" \
        and "FreeCAD" in sys.modules:                      # run by freecadcmd / the GUI (module "part_index")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    run([x for x in os.environ.get("VT350_INDEX_MODELS", "").split(":") if x],
        force=os.environ.get("VT350_INDEX_FORCE") == "1")
