#!/usr/bin/env python3
"""Write sha256 hashes into a pip pin list (vt350#224), so `pip install --require-hashes` installs exactly the files
that were pinned.

    python3 platform/virtualprinter/pip_lock.py platform/virtualprinter/moonraker-requirements.txt

The file keeps its comment lines and one `name==version` per package; every other line (old hashes) is replaced.
For each pin it asks PyPI's JSON API for that release's files and writes a `--hash=sha256:...` for each wheel a
Linux CPython 3.13 can install (pure-python wheels, cp313 wheels, abi3 wheels; any Linux architecture), sorted, so
a refresh with no new releases changes nothing. Fails if a pin has no such wheel (the image installs wheels only).

Generic: no printer knowledge. Plain python3, standard library only (and the network, for PyPI).
"""
import json
import re
import sys
import urllib.request

PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\;]+)")
PYTHON = (3, 13)


def wheel_fits(filename, python=PYTHON):
    """Whether a wheel file can install on Linux CPython `python` (major, minor)."""
    if not filename.endswith(".whl"):
        return False
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return False
    pytags, abi, plat = parts[-3].split("."), parts[-2], parts[-1]
    if plat != "any" and "linux" not in plat:
        return False
    cp = f"cp{python[0]}{python[1]}"
    for t in pytags:
        if t in ("py3", f"py{python[0]}{python[1]}") and abi == "none":
            return True
        if t == cp:
            return True
        m = re.fullmatch(r"cp3(\d+)", t)
        if m and abi == "abi3" and int(m.group(1)) <= python[1]:
            return True
    return False


def pypi_files(name, version):
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=60) as r:
        return json.load(r)["urls"]


def lock(text, fetch=pypi_files):
    """The pin list `text` with fresh hashes: comments kept, each pin followed by its wheels' hashes."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            out.append(line)
            continue
        m = PIN.match(s)
        if not m:
            if s.startswith("--hash="):
                continue
            raise ValueError(f"not a name==version pin: {line!r}")
        name, version = m.groups()
        hashes = sorted({f["digests"]["sha256"] for f in fetch(name, version) if wheel_fits(f["filename"])})
        if not hashes:
            raise ValueError(f"{name}=={version}: no wheel for Linux CPython {PYTHON[0]}.{PYTHON[1]} on PyPI")
        out.append(f"{name}=={version} \\")
        out += [f"    --hash=sha256:{h}" + (" \\" if i < len(hashes) - 1 else "") for i, h in enumerate(hashes)]
    return "\n".join(out) + "\n"


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    path = argv[0]
    with open(path) as f:
        text = f.read()
    new = lock(text)
    with open(path, "w") as f:
        f.write(new)
    print(f"pip-lock: {path}: {sum(1 for l in new.splitlines() if PIN.match(l))} pins hashed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ValueError as e:
        print(f"pip-lock: {e}")
        sys.exit(1)
