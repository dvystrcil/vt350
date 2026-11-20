#!/usr/bin/env python3
"""Check a parts library: every entry's source.json is valid and every file in the library is accounted for.

    python3 platform/library/check_library.py --library cad/library [--reuse REUSE.toml] [--projects cad/credits.json]
    # last line "library-check: OK"; exit 1 with every problem listed otherwise

Generic (stdlib only); the layout is <library>/<category>/<part>/<variant>/source.json, several variants of one part
side by side (README.md in the library says why):
- each source.json validates against <library>/schema.json (or --schema): a small JSON Schema subset is read
  (type, required, properties, additionalProperties, items, minItems, minLength, pattern, enum); the schema's
  enum on "category" is the list of categories, and the entry's first folder must be its category;
- a committed entry (by default, a redistributable one) has each listed file, with the listed sha256;
- a no-file entry (redistributable false, or committed false) has none of its listed files present, and a
  redistributable false entry can't say committed true;
- any other file fails: one beside source.json that it doesn't list, or one in a folder with no source.json.
  README.md is allowed anywhere, and schema.json at the top;
- with --reuse, each committed file's licence in REUSE.toml (the last matching annotation) must be the entry's;
- with --projects (a credits projects file, platform/pages/credits.py format), an entry's "credit" must be a key in it.
"""
import argparse, hashlib, json, os, re, sys, tomllib

ENTRY = "source.json"
ALWAYS_OK = {"README.md"}
TOP_OK = {"README.md", "schema.json"}
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int}


def validate(value, schema, where="$"):
    """-> [problem strings]. The subset of JSON Schema the library's schema uses."""
    probs = []
    t = schema.get("type")
    if t:
        ok = isinstance(value, TYPES[t]) and not (t == "integer" and isinstance(value, bool))
        if not ok:
            return [f"{where}: expected {t}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        probs.append(f"{where}: {value!r} is not one of {schema['enum']}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            probs.append(f"{where}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            probs.append(f"{where}: {value!r} doesn't match {schema['pattern']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            probs.append(f"{where}: needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for i, v in enumerate(value):
                probs += validate(v, schema["items"], f"{where}[{i}]")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in value:
                probs.append(f"{where}: missing required field {k!r}")
        for k, v in value.items():
            if k in props:
                probs += validate(v, props[k], f"{where}.{k}")
            elif schema.get("additionalProperties") is False:
                probs.append(f"{where}: unknown field {k!r}")
    return probs


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _glob(pattern):
    """REUSE.toml globbing: ** crosses folders, * doesn't."""
    rx = "".join(".*" if tok == "**" else "[^/]*" if tok == "*" else re.escape(tok)
                 for tok in re.split(r"(\*\*|\*)", pattern))
    return re.compile(rx + r"\Z")


def reuse_licences(reuse_path):
    """-> [(compiled patterns, SPDX id)] in file order (the last match wins)."""
    with open(reuse_path, "rb") as f:
        data = tomllib.load(f)
    out = []
    for a in data.get("annotations", []):
        paths = a["path"] if isinstance(a["path"], list) else [a["path"]]
        out.append(([_glob(p) for p in paths], a.get("SPDX-License-Identifier")))
    return out


def reuse_licence_of(rel, annotations):
    lic = None
    for pats, l in annotations:
        if any(p.match(rel) for p in pats):
            lic = l
    return lic


def check_entry(entry_dir, schema, reuse=None, reuse_root=None, credits=None, category=None):
    """-> (problems, set of file names the entry accounts for)."""
    name = os.path.join(entry_dir, ENTRY)
    try:
        with open(name, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        return [f"{name}: can't read: {e}"], {ENTRY}
    probs = [f"{name}: {p}" for p in validate(data, schema)]
    if probs:
        return probs, {ENTRY} | {f.get("path") for f in data.get("files", []) if isinstance(f, dict)}
    if category is not None and data.get("category") != category:
        probs.append(f"{name}: category {data.get('category')!r} but it sits in {category}/")
    redist = data["redistributable"]
    committed = data.get("committed", redist)
    if committed and not redist:
        probs.append(f"{name}: committed is true but the part isn't redistributable")
    paths = [f["path"] for f in data["files"]]
    for p in sorted({p for p in paths if paths.count(p) > 1}):
        probs.append(f"{name}: {p} listed twice")
    if credits is not None and "credit" in data and data["credit"] not in credits:
        probs.append(f"{name}: credit {data['credit']!r} is not a project in the projects file")
    for f in data["files"]:
        path = os.path.join(entry_dir, f["path"])
        present = os.path.isfile(path)
        if committed and redist:
            if not present:
                probs.append(f"{path}: listed in {ENTRY} but missing")
                continue
            got = sha256(path)
            if got != f["sha256"]:
                probs.append(f"{path}: sha256 {got} != {f['sha256']} in {ENTRY}")
            if reuse is not None:
                rel = os.path.relpath(os.path.abspath(path), reuse_root).replace(os.sep, "/")
                lic = reuse_licence_of(rel, reuse)
                if lic != data["licence"]:
                    probs.append(f"{path}: REUSE.toml says {lic}, {ENTRY} says {data['licence']}")
        elif present:
            why = "isn't redistributable" if not redist else "says committed: false"
            probs.append(f"{path}: present, but {ENTRY} {why}")
    return probs, {ENTRY} | set(paths)


def check(library, schema_path=None, reuse_path=None, projects_path=None):
    """-> (problems, number of entries)."""
    schema_path = schema_path or os.path.join(library, "schema.json")
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    reuse = reuse_licences(reuse_path) if reuse_path else None
    reuse_root = os.path.dirname(os.path.abspath(reuse_path)) if reuse_path else None
    credits = None
    if projects_path:
        with open(projects_path, encoding="utf-8") as f:
            credits = {p["key"] for p in json.load(f).get("projects", [])}
    probs, n = [], 0
    lib = os.path.normpath(library)
    for d, dirs, files in os.walk(lib):
        dirs.sort()
        rel = os.path.relpath(d, lib)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if ENTRY in files:
            if depth != 3:
                probs.append(f"{os.path.join(d, ENTRY)}: entries go in <library>/<category>/<part>/<variant>/, not here")
            n += 1
            p, covered = check_entry(d, schema, reuse, reuse_root, credits, rel.split(os.sep)[0])
            probs += p
            for name in sorted(set(files) - covered - ALWAYS_OK):
                probs.append(f"{os.path.join(d, name)}: not listed in {ENTRY}")
            for sub in dirs:
                probs.append(f"{os.path.join(d, sub)}: sub-folder in an entry (list files flat beside {ENTRY})")
            dirs[:] = []
            continue
        ok = TOP_OK if depth == 0 else ALWAYS_OK
        for name in sorted(set(files) - ok):
            probs.append(f"{os.path.join(d, name)}: no {ENTRY} covers this file")
    return probs, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--library", required=True, help="the library folder")
    ap.add_argument("--schema", help="source.json schema (default: <library>/schema.json)")
    ap.add_argument("--reuse", help="REUSE.toml: committed files' licences must match it")
    ap.add_argument("--projects", help="credits projects file: an entry's 'credit' must be a key in it")
    a = ap.parse_args(argv)
    probs, n = check(a.library, a.schema, a.reuse, a.projects)
    for p in probs:
        print(f"library-check: FAIL {p}")
    if probs:
        print(f"library-check: {len(probs)} problem(s) in {n} entr{'y' if n == 1 else 'ies'}")
        return 1
    print(f"library-check: {n} entr{'y' if n == 1 else 'ies'} checked")
    print("library-check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
