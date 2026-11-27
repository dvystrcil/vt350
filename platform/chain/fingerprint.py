# SPDX-License-Identifier: GPL-3.0-or-later
"""Skip a chain link whose inputs haven't changed (vt350#324). Plain python3 (stdlib), no FreeCAD.

A LINK declares what it reads:
  - files: paths or glob patterns under the checkout (its code, config, the logs an earlier link wrote);
  - indexes: part indexes (<model>.parts.json, platform/freecad/part_index.py) whose parts it looks at, and which of
    each part's fields count (default GEOMETRY: the label and the bounding box). A pass that recolours parts or hides
    them leaves the fingerprint as it was, whatever the .FCStd's bytes; one that moves, resizes, adds, removes or
    renames a part changes it.
Its FINGERPRINT is the sha256 of all of that. A RECORD (one JSON file the caller keeps, committed beside the logs)
holds each link's fingerprint from its last successful run. decide() says, per link, run / reused / forced / always:
  - reused: the fingerprint equals the record's;
  - forced: named by --fresh (or downstream of a named link; an empty --fresh forces every link);
  - always: a link declared {"always": "<why>"} (cheap, or it skips by itself);
  - run: anything else, and every link with no declaration (the caller says "no declared inputs").
A downstream link needn't know whether its upstream ran: it lists the upstream's output files among its own files,
so new outputs change its fingerprint and identical ones don't.

    from fingerprint import fingerprint, Records, decide
"""
import fnmatch
import glob
import hashlib
import json
import os

GEOMETRY = ("label", "bbox")
ROUND = 3                                     # bbox to the micrometre: no noise from float formatting


def file_digest(path):
    if not os.path.isfile(path):
        return "missing"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def _round(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(float(v), ROUND) + 0.0               # 20 and 20.0 alike; -0.0 -> 0.0
    if isinstance(v, dict):
        return {k: _round(x) for k, x in sorted(v.items())}
    if isinstance(v, list):
        return [_round(x) for x in v]
    return v


def index_digest(path, fields=GEOMETRY, select=None):
    """sha256 of the selected parts' fields, order-free. A missing index -> 'missing' (the link then runs)."""
    if not os.path.isfile(path):
        return "missing"
    parts = json.load(open(path, encoding="utf-8"))["parts"]
    rows = sorted(json.dumps([_round(p.get(k)) for k in fields], sort_keys=True)
                  for p in parts if select is None or select(p))
    h = hashlib.sha256()
    for r in rows:
        h.update(r.encode()); h.update(b"\n")
    return h.hexdigest()


def expand(root, patterns, exclude=()):
    """Patterns (relative to root, globs allowed) -> sorted relative paths, less those whose basename matches an
    exclude pattern (e.g. "test_*"); a pattern matching nothing stays itself (it hashes as 'missing', so a file that
    appears later changes the fingerprint)."""
    keep = lambda r: not any(fnmatch.fnmatch(os.path.basename(r), x) for x in exclude)
    out = set()
    for pat in patterns:
        hits = [os.path.relpath(h, root) for h in glob.glob(os.path.join(root, pat)) if os.path.isfile(h)]
        hits = [h for h in hits if keep(h)]
        out.update(hits or [pat])               # only excluded files (or none): the pattern itself, as before
    return sorted(out)


def fingerprint(root, decl):
    """decl: {"files": [patterns], "exclude": [basename patterns], "indexes": [paths], "fields": [..]}
    -> (hex, {item: digest})."""
    items = {}
    for rel in expand(root, decl.get("files", []), decl.get("exclude", ())):
        items["file:" + rel] = file_digest(os.path.join(root, rel))
    for i, ix in enumerate(decl.get("indexes", [])):    # by position, not name: lite-79's and lite-80's indexes are
        items[f"index:{i}"] = index_digest(ix, tuple(decl.get("fields", GEOMETRY)))   # the same input, two versions
    h = hashlib.sha256()
    for k in sorted(items):
        h.update(f"{k}={items[k]}\n".encode())
    return h.hexdigest(), items


class Records:
    """{link: {"fingerprint": hex, "model": str, "at": iso}} in one JSON file."""

    def __init__(self, path):
        self.path = path
        try:
            self.data = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            # lint-allow-silent: no record (first run, or a damaged file) only means nothing is reused: every link runs
            self.data = {}

    def get(self, link):
        return (self.data.get(link) or {}).get("fingerprint")

    def put(self, link, fp, model, at):
        self.data[link] = {"fingerprint": fp, "model": model, "at": at}
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1, sort_keys=True); f.write("\n")
        os.replace(tmp, self.path)


def downstream(names, deps):
    """names plus every link that depends on one of them, transitively. deps: {link: [upstream links]}."""
    out, grew = set(names), True
    while grew:
        grew = False
        for link, ups in deps.items():
            if link not in out and out.intersection(ups):
                out.add(link); grew = True
    return out


def forced_set(fresh, links, deps):
    """fresh: None (nothing forced), [] (all), [names] (them and downstream)."""
    if fresh is None:
        return set()
    if not fresh:
        return set(links)
    unknown = [f for f in fresh if f not in links]
    if unknown:
        raise ValueError(f"--fresh: unknown links {unknown}; links are {list(links)}")
    return downstream(fresh, deps)


def decide(link, decl, fp, recorded, forced):
    """One link, just before it would run: -> (verdict, why)."""
    if decl is None:
        return "run", "no declared inputs"
    if "always" in decl:
        return "always", decl["always"]
    if link in forced:
        return "forced", "--fresh"
    if fp is not None and fp == recorded:
        return "reused", "inputs unchanged"
    return "run", "inputs changed" if recorded else "no earlier run recorded"
