#!/usr/bin/env python3
"""Every folder that ships its own LICENSE/COPYING must be labelled in REUSE.toml by an annotation of its own, with a
licence that matches that text (vt350#122).

`reuse lint` only proves every file HAS a label. REUSE.toml's first annotation labels everything ("**") as the
user's own GPL-3.0-or-later work, so a newly vendored third-party folder would pass lint wearing the wrong licence.
This check catches that: a folder with its own licence text that falls through to the repo default fails, and so
does an override whose licence family (GPL-3.0 vs CC BY-NC-SA 4.0) differs from the text in the folder.

    python3 .github/scripts/check_reuse_labels.py [repo root]    # prints "check-reuse-labels: OK"
"""
import os, re, subprocess, sys, tomllib

LICENCE_FILES = ("LICENSE", "COPYING")
HEADER_LABELLED = ("cad/klipper/kalisim",)   # folders whose files carry SPDX headers instead of an annotation


def parse(toml_text):
    """[(compiled patterns, licence id)] in file order."""
    out = []
    for a in tomllib.loads(toml_text).get("annotations", []):
        paths = a["path"] if isinstance(a["path"], list) else [a["path"]]
        out.append(([_glob(p) for p in paths], a["SPDX-License-Identifier"]))
    return out


def _glob(pattern):
    """REUSE.toml globbing: ** crosses folders, * doesn't."""
    rx = "".join(".*" if tok == "**" else "[^/]*" if tok == "*" else re.escape(tok)
                 for tok in re.split(r"(\*\*|\*)", pattern))
    return re.compile(rx + r"\Z")


def label(annotations, path):
    """Index and licence of the last annotation matching path, or (None, None)."""
    hit = (None, None)
    for i, (pats, lic) in enumerate(annotations):
        if any(p.match(path) for p in pats):
            hit = (i, lic)
    return hit


def family(text):
    if "GNU GENERAL PUBLIC LICENSE" in text and "Version 3" in text:
        return "GPL-3.0"
    if "NonCommercial-ShareAlike 4.0" in text:
        return "CC BY-NC-SA 4.0"
    return None


def _family_of_id(lic):
    return "GPL-3.0" if lic.startswith("GPL-3.0") else "CC BY-NC-SA 4.0" if lic == "CC-BY-NC-SA-4.0" else lic


def check(annotations, files, header_labelled=HEADER_LABELLED):
    """files: {repo-relative path: text, or None for files that aren't licence texts}. Returns error strings."""
    errs = []
    for path, text in sorted(files.items()):
        if os.path.basename(path) not in LICENCE_FILES or text is None:
            continue
        folder = os.path.dirname(path)
        if any(folder == h or folder.startswith(h + "/") for h in header_labelled):
            continue
        fam = family(text)
        if fam is None:
            errs.append(f"{path}: can't tell which licence this text is")
            continue
        idx, lic = label(annotations, path)
        if folder and idx == 0:
            errs.append(f"{folder}/: has its own {fam} licence but falls through to the repo default {lic} in "
                        f"REUSE.toml; add an annotation for it")
        elif lic is None:
            errs.append(f"{path}: no REUSE.toml annotation matches")
        elif _family_of_id(lic) != fam:
            errs.append(f"{folder or '.'}/: REUSE.toml labels it {lic}, but its {os.path.basename(path)} is {fam}")
    return errs


def _listed(root):
    """Tracked files; without git (act copies the checkout with no .git), every file outside .git/."""
    git = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, text=True)
    if git.returncode == 0:
        return [p for p in git.stdout.split("\0") if p]
    out = []
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x != ".git"]
        out += [os.path.relpath(os.path.join(d, n), root) for n in names]
    return out


def main(argv):
    root = os.path.abspath(argv[0] if argv else os.path.join(os.path.dirname(__file__), "..", ".."))
    files = {}
    for p in _listed(root):
        if os.path.basename(p) in LICENCE_FILES:
            with open(os.path.join(root, p), encoding="utf-8", errors="replace") as f:
                files[p] = f.read()
    with open(os.path.join(root, "REUSE.toml"), encoding="utf-8") as f:
        errs = check(parse(f.read()), files)
    for e in errs:
        print(e)
    print("check-reuse-labels: OK" if not errs else f"check-reuse-labels: FAILED ({len(errs)})")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
