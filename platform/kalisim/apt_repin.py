#!/usr/bin/env python3
"""Move a Dockerfile's Debian snapshot to a new moment and re-pin every apt package to the version that snapshot
serves (vt350#224).

    python3 platform/kalisim/apt_repin.py <Dockerfile> <timestamp> [--image REF=IMAGE ...]

    e.g. python3 platform/kalisim/apt_repin.py platform/kalisim/Dockerfile 20261201T000000Z

Sets `ARG DEBIAN_SNAPSHOT=<timestamp>`, then for each stage that runs `apt-get install -y --no-install-recommends`
with `name=version` words: starts that stage's base image (docker run, as root), points apt at the snapshot with the
apt_snapshot.sh next to the Dockerfile, and writes each package's candidate version (`apt-cache policy`) in place of
the old one. Packages keep their order and line breaks; only the versions change. Prints one line per change and a
last line "apt-repin: <n> changed".

A stage FROM another stage uses that stage's base. A base that's an ARG (`FROM ${KALISIM_IMAGE}`) takes the ARG's
default; --image REF=IMAGE runs IMAGE wherever the base would be REF (e.g. --image kalisim:local=<a pulled image>).

Generic: no printer knowledge. Plain python3 and docker (and the network, for the images and snapshot.debian.org).
"""
import os
import re
import subprocess
import sys

TS = re.compile(r"^\d{8}T\d{6}Z$")
INSTALL = "apt-get install -y --no-install-recommends"
PKG = re.compile(r"(?<![\w.+-])([a-z0-9][a-z0-9.+-]*)=([0-9][^\s=\\]*)")


def stages(lines):
    """Per line index, the base image of the stage it's in (None before the first FROM)."""
    args, names, out, base = {}, {}, [], None
    seen_from = False
    for line in lines:
        m = re.match(r"^ARG\s+([A-Za-z_][A-Za-z0-9_]*)=(\S+)\s*$", line)
        if m and not seen_from:
            args[m.group(1)] = m.group(2)
        m = re.match(r"^FROM\s+(\S+)(?:\s+AS\s+(\S+))?", line, re.I)
        if m:
            seen_from = True
            ref = re.sub(r"\$\{(\w+)\}|\$(\w+)", lambda a: args.get(a.group(1) or a.group(2), ""), m.group(1))
            base = names.get(ref, ref)
            if m.group(2):
                names[m.group(2)] = base
        out.append(base)
    return out


def install_blocks(lines):
    """(first line, last line) of each apt-get install command's package list (up to its `&&`)."""
    blocks = []
    i = 0
    while i < len(lines):
        if INSTALL in lines[i]:
            j = i
            while ("&&" not in lines[j].split(INSTALL)[-1] and lines[j].rstrip().endswith("\\")
                   and j + 1 < len(lines)):
                j += 1
            blocks.append((i, j))
            i = j
        i += 1
    return blocks


def block_text(lines, a, b):
    """The package words of a block: after INSTALL on its first line, up to the `&&` that ends it."""
    parts = []
    for k in range(a, b + 1):
        s = lines[k].split(INSTALL, 1)[1] if k == a else lines[k]
        parts.append(s.split("&&")[0])
    return " ".join(parts)


def docker_candidates(image, packages, snapshot, apt_snapshot):
    """{package: candidate version} from apt-cache policy in `image`, apt pointed at the snapshot."""
    script = ('sh /apt_snapshot.sh "$1" >/dev/null && apt-get update -qq >/dev/null && shift && apt-cache policy "$@"')
    r = subprocess.run(["docker", "run", "--rm", "-u", "0", "--entrypoint", "sh",
                        "-v", f"{os.path.abspath(apt_snapshot)}:/apt_snapshot.sh:ro", image,
                        "-c", script, "sh", snapshot, *packages], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{image}: apt-cache policy failed:\n{r.stdout}{r.stderr}")
    return parse_policy(r.stdout)


def parse_policy(text):
    out, name = {}, None
    for line in text.splitlines():
        m = re.match(r"^(\S+):$", line)
        if m:
            name = m.group(1).split(":")[0]
            continue
        m = re.match(r"^\s+Candidate:\s+(\S+)", line)
        if m and name:
            out[name] = m.group(1)
    return out


def repin(text, snapshot, images=None, candidates=None, apt_snapshot="apt_snapshot.sh"):
    """`text` with the snapshot set and every apt package at its candidate version; returns (text, changes)."""
    if not TS.match(snapshot):
        raise ValueError(f"'{snapshot}' is not a timestamp like 20261201T000000Z")
    images = images or {}
    candidates = candidates or (lambda image, pkgs: docker_candidates(image, pkgs, snapshot, apt_snapshot))
    text, n = re.subn(r"(?m)^ARG DEBIAN_SNAPSHOT=\S+$", f"ARG DEBIAN_SNAPSHOT={snapshot}", text)
    if n != 1:
        raise ValueError(f"expected one ARG DEBIAN_SNAPSHOT=, found {n}")
    lines = text.split("\n")
    bases = stages(lines)
    blocks = install_blocks(lines)
    if not blocks:
        raise ValueError("no apt-get install lines")
    wanted = {}
    for a, b in blocks:
        image = images.get(bases[a], bases[a])
        if not image:
            raise ValueError(f"line {a + 1}: apt-get install before any FROM")
        pkgs = [m.group(1) for m in PKG.finditer(block_text(lines, a, b))]
        if not pkgs:
            raise ValueError(f"line {a + 1}: apt-get install with no name=version packages")
        wanted.setdefault(image, set()).update(pkgs)
    versions = {image: candidates(image, sorted(pkgs)) for image, pkgs in wanted.items()}
    changes = []
    for a, b in blocks:
        image = images.get(bases[a], bases[a])
        for k in range(a, b + 1):
            head, sep, rest = lines[k].partition(INSTALL) if k == a else ("", "", lines[k])
            body, amp, tail = rest.partition("&&")

            def sub(m, image=image):
                name, old = m.groups()
                new = versions[image].get(name)
                if not new or new == "(none)":
                    raise ValueError(f"{name}: no candidate in {image} at the snapshot")
                if new != old:
                    changes.append(f"{name}={old} -> {name}={new} ({image})")
                return f"{name}={new}"
            lines[k] = head + sep + PKG.sub(sub, body) + amp + tail
            if amp:
                break
    return "\n".join(lines), changes


def main(argv):
    images = {}
    args = []
    it = iter(argv)
    for a in it:
        if a == "--image":
            ref, _, image = next(it, "").partition("=")
            if not image:
                print("apt-repin: --image needs REF=IMAGE")
                return 2
            images[ref] = image
        else:
            args.append(a)
    if len(args) != 2:
        print(__doc__)
        return 2
    path, snapshot = args
    with open(path) as f:
        text = f.read()
    new, changes = repin(text, snapshot, images,
                         apt_snapshot=os.path.join(os.path.dirname(os.path.abspath(path)), "apt_snapshot.sh"))
    if new != text:
        with open(path, "w") as f:
            f.write(new)
    for c in changes:
        print(f"  {c}")
    print(f"apt-repin: {path}: {len(changes)} changed (snapshot {snapshot})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (ValueError, RuntimeError) as e:
        print(f"apt-repin: {e}")
        sys.exit(1)
