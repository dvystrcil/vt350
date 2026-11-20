"""Which parts go into a viewer export, and the licence each one is shared under (vt350#220).

Stdlib only: FreeCAD (export_meshes.py), the licence check and the tests all import it. Generic: the printer's
selection and licence files hold its names; nothing here does.

A **match** is a dict of conditions, all of which must hold for a part (its label and its group path, the labels
of the groups it sits in, outermost first):
    "group":          a group in the path has exactly this label
    "group_prefix":   a group in the path has a label starting with this
    "label":          the part's label is exactly this
    "label_prefix":   the part's label starts with this
    "label_contains": the part's label contains this
An empty match matches nothing (so a typo can't select the whole model).

A **selection file** (RENDER_SELECT for export_meshes.py):
    {"include": [match + optional "move": <name>], "exclude": [match],
     "moves": {<name>: {"from": <object Name>, "to": <object Name>}}}
A part is exported if some include matches it and no exclude does. A move translates the part by the vector that
takes the "from" object's bounding box onto the "to" object's (two copies of one part, such as a carriage at the
dock and on the gantry): export_meshes.py measures it and refuses if the two boxes differ in size.

A **licence file**:
    {"shareable": [SPDX id, ...],
     "rules": [match + "licence": SPDX id + "source": where the licence was read]}
The first rule that matches a part gives its licence. check() fails a part no rule matches (unknown) and a part
whose licence isn't in "shareable". A rule whose licence is "unknown" records an open question in its "source"
(e.g. a part whose origin isn't traced yet): its parts fail as unknown, with the question in the log.
"""
import json

UNKNOWN = "unknown"                      # a rule's licence for a part whose licence is an open question
KEYS = ("group", "group_prefix", "label", "label_prefix", "label_contains")


def matches(m, label, path):
    """Whether the match dict m holds for a part with this label and group path (a list of group labels)."""
    conds = [k for k in KEYS if k in m]
    if not conds:
        return False
    label = label or ""
    for k in conds:
        v = m[k]
        ok = {"group": lambda: v in path,
              "group_prefix": lambda: any(g.startswith(v) for g in path),
              "label": lambda: label == v,
              "label_prefix": lambda: label.startswith(v),
              "label_contains": lambda: v in label}[k]()
        if not ok:
            return False
    return True


def split_path(gpath):
    """export_meshes.py's group path string ("A / B / C") -> ["A", "B", "C"]."""
    return [g for g in (gpath or "").split(" / ") if g]


class Selection:
    def __init__(self, data):
        data = data or {}
        self.include = list(data.get("include", []))
        self.exclude = list(data.get("exclude", []))
        self.moves = dict(data.get("moves", {}))
        for r in self.include + self.exclude:
            unknown = set(r) - set(KEYS) - {"move", "note"}
            if unknown:
                raise ValueError(f"selection rule {r}: unknown keys {sorted(unknown)}")
        for r in self.include:
            if "move" in r and r["move"] not in self.moves:
                raise ValueError(f"selection rule {r}: no move named {r['move']!r}")
        for n, mv in self.moves.items():
            if not (mv.get("from") and mv.get("to")):
                raise ValueError(f"move {n!r} needs 'from' and 'to' object Names")

    def pick(self, label, path):
        """-> (exported?, move name or None)."""
        if any(matches(r, label, path) for r in self.exclude):
            return False, None
        for r in self.include:
            if matches(r, label, path):
                return True, r.get("move")
        return False, None


def load_selection(fn):
    return Selection(json.load(open(fn, encoding="utf-8")))


def translation(box_from, box_to, tol=0.01):
    """The vector taking box_from onto box_to (each [xmin, ymin, zmin, xmax, ymax, zmax]); ValueError if the two
    boxes differ in size by more than tol on any axis (then they aren't two copies of one part)."""
    for i in range(3):
        a, b = box_from[i + 3] - box_from[i], box_to[i + 3] - box_to[i]
        if abs(a - b) > tol:
            raise ValueError(f"move: the boxes differ in size on axis {'xyz'[i]}: {a:.3f} vs {b:.3f}")
    return [box_to[i] - box_from[i] for i in range(3)]


def licence_of(lic, label, path):
    """-> (licence, source) of the first rule matching the part, or (None, None)."""
    for r in lic["rules"]:
        if matches(r, label, path):
            return r["licence"], r["source"]
    return None, None


def check(lic, parts):
    """parts: [{"label", "path"}] (path: a list or export_meshes.py's " / " string).
    -> (lines, problems): one log line per part, and the parts that fail (unknown or not shareable)."""
    share = set(lic.get("shareable", []))
    for r in lic["rules"]:
        if not (r.get("licence") and r.get("source")):
            raise ValueError(f"licence rule {r}: needs 'licence' and 'source'")
    lines, problems = [], []
    for p in parts:
        path = p["path"] if isinstance(p["path"], list) else split_path(p["path"])
        licence, source = licence_of(lic, p["label"], path)
        where = " / ".join(path[1:] or path)
        if licence in (None, UNKNOWN):
            q = f"  (open question: {source})" if source else ""
            problems.append(f"UNKNOWN licence: {p['label']}  [{where}]{q}")
            lines.append(f"UNKNOWN  {p['label']}  [{where}]{q}")
        elif licence not in share:
            problems.append(f"NOT SHAREABLE ({licence}): {p['label']}  [{where}]")
            lines.append(f"NO-SHARE {licence}  {p['label']}  [{where}]  ({source})")
        else:
            lines.append(f"ok  {licence}  {p['label']}  [{where}]  ({source})")
    return lines, problems
