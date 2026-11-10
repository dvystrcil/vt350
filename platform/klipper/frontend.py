#!/usr/bin/env python3
"""The printer's web front end (Fluidd or Mainsail): which one a config includes, and switching it.

    python3 platform/klipper/frontend.py --config cad/klipper/frontend.cfg                # "front end: fluidd"
    python3 platform/klipper/frontend.py --config cad/klipper/frontend.cfg --use mainsail

Both front ends talk to Moonraker and ship a client config with the same sections ([virtual_sdcard],
[pause_resume], [display_status], [respond]) and the PAUSE / RESUME / CANCEL_PRINT macros. Each is vendored unchanged
in frontends/<name>/client.cfg (GPL-3.0). The printer's config includes exactly one of them; --use rewrites that one
line and nothing else.

Generic: no printer knowledge. Plain python3, standard library only.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# upstream repo, pinned commit, git blob id of client.cfg at that commit
FRONTENDS = {
    "fluidd": {"repo": "fluidd-core/fluidd-config", "sha": "807175d72e3a00cdc6b5e249444a4630e1e03a55",
               "blob": "8f2eadf1fe7cdbc8f6011aec7b385a1f581207db"},
    "mainsail": {"repo": "mainsail-crew/mainsail-config", "sha": "ff3869a621db17ce3ef660adbbd3fa321995ac42",
                 "blob": "83eaf8d9d0b895d9821220f6cd06a55ea6b75b84"},
}
INCLUDE = re.compile(r"(?m)^\[include ([^\]]*?frontends/(\w+)/client\.cfg)\]\s*$")


def client_cfg(name):
    return os.path.join(HERE, "frontends", name, "client.cfg")


def _one(text):
    found = INCLUDE.findall(text)
    if len(found) != 1:
        raise ValueError(f"need exactly one [include .../frontends/<name>/client.cfg], found {len(found)}")
    path, name = found[0]
    if name not in FRONTENDS:
        raise ValueError(f"unknown front end {name!r}: one of {sorted(FRONTENDS)}")
    return path, name


def chosen(text):
    """The front end a config includes."""
    return _one(text)[1]


def include_path(text):
    """The include's path, as written (relative to the config's folder)."""
    return _one(text)[0]


def use(text, name):
    """The config with its front-end include switched to name; every other line unchanged."""
    if name not in FRONTENDS:
        raise ValueError(f"unknown front end {name!r}: one of {sorted(FRONTENDS)}")
    _, old = _one(text)
    return INCLUDE.sub(lambda m: m.group(0).replace(f"frontends/{old}/", f"frontends/{name}/"), text)


def main(argv):
    ap = argparse.ArgumentParser(prog="frontend", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", required=True, help="the config file that includes the front end")
    ap.add_argument("--use", choices=sorted(FRONTENDS), help="switch to this front end")
    a = ap.parse_args(argv)
    with open(a.config) as f:
        text = f.read()
    old = chosen(text)
    if not a.use:
        return [f"front end: {old}"]
    with open(a.config, "w") as f:
        f.write(use(text, a.use))
    return [f"front end: {old} -> {a.use}"]


if __name__ == "__main__":
    print("\n".join(main(sys.argv[1:])))
