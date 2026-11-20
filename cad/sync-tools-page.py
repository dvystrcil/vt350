#!/usr/bin/env python3
"""Carry pin changes onto cad/tools.md (#124, vt350#224): for every pin cad/check-tools-page.sh reads that differs
from <base> (a git ref), replace the old value on the page with the new one.

    python3 cad/sync-tools-page.py <base>          e.g. origin/main, or HEAD before a repin's uncommitted edits

Pins are paired by what they are (check-tools-page.sh's label) and their name (the part before @, == or =), so
`git=1:2.39.5-0+deb12u3` becomes `git=1:2.39.5-0+deb12u4` everywhere the page lists it. A pin with no old value
to replace (a new package, a new action) is reported for a hand edit. Then runs cad/check-tools-page.sh; its last
line is this script's last line, and its exit code this script's.

Used by Renovate's PRs (.github/workflows/repin-virtualprinter.yml, renovate-fixup) and the monthly repin.
"""
import os
import re
import subprocess
import sys
import tempfile
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "cad", "tools.md")
READS = ["cad/check-tools-page.sh", "cad/tools.md", "platform/README.md", "platform/kalisim/Dockerfile",
         "platform/virtualprinter", ".github/workflows"]
LINE = re.compile(r"^(?:ok  |FAIL) (.+?): (.+?)(?: is not on cad/tools\.md)?$")


def pins(root):
    """{(label, name): {value, ...}} as check-tools-page.sh in `root` reads them."""
    r = subprocess.run(["bash", os.path.join(root, "cad", "check-tools-page.sh")], capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        m = LINE.match(line)
        if m and m.group(2) != "no pin found in the repo":
            out.setdefault((m.group(1), name(m.group(2))), set()).add(m.group(2))
    return out


def name(value):
    for sep in ("@", "==", "="):
        if sep in value:
            return value.split(sep)[0].split(":")[0] if sep == "@" else value.split(sep)[0]
    return ""


def replace(page, old, new):
    return re.sub(r"(?<![\w.+:~@/-])" + re.escape(old) + r"(?![\w.+:~-])", lambda m: new, page)


def sync(page, before, after):
    """`page` with each changed pin's old value replaced; returns (page, notes)."""
    notes = []
    for key in sorted(set(before) | set(after)):
        gone = sorted(before.get(key, set()) - after.get(key, set()))
        new = sorted(after.get(key, set()) - before.get(key, set()))
        if not gone and not new:
            continue
        if len(gone) == len(new):
            for o, n in zip(gone, new):
                page = replace(page, o, n)
                notes.append(f"  {key[0]}: {o} -> {n}")
        else:
            notes += [f"  {key[0]}: {n} is new: add it to cad/tools.md by hand" for n in new if n not in page]
            notes += [f"  {key[0]}: {o} is no longer pinned (left on the page)" for o in gone]
    return page, notes


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    base = argv[0]
    tmp = tempfile.mkdtemp()
    try:
        have = subprocess.run(["git", "-C", ROOT, "ls-tree", "-r", "--name-only", base, "--", *READS],
                              capture_output=True, text=True, check=True).stdout.split()
        arc = subprocess.run(["git", "-C", ROOT, "archive", base, "--", *have], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", tmp], input=arc.stdout, check=True)
        before = pins(tmp)
    finally:
        shutil.rmtree(tmp)
    with open(PAGE) as f:
        page = f.read()
    new, notes = sync(page, before, pins(ROOT))
    if new != page:
        with open(PAGE, "w") as f:
            f.write(new)
    print("\n".join(notes) if notes else "  no pin changed")
    r = subprocess.run(["bash", os.path.join(ROOT, "cad", "check-tools-page.sh")], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("FAIL"):
            print(line)
    print(r.stdout.strip().splitlines()[-1].replace("check-tools-page", "sync-tools-page"))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
