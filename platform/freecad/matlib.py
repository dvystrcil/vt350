# SPDX-License-Identifier: GPL-3.0-or-later
"""A folder of FreeCAD material cards (.FCMat) as the "Custom" material library (vt350#60).

A model stores only each part's material UUID, not the material: opened where the card's library isn't registered,
the part silently falls back to "Default" (measured 2026-11-17, FreeCAD 26.3 and 1.1.4). A printer keeps its cards
in its repo and registers that folder before opening its models, here for scripts and the batch lane; in the GUI
it's Preferences > Material > "Use materials from user defined directory".

Note: FreeCAD saves the setting in the user's config (user.cfg) on exit, so a script that calls use_dir() leaves
the folder registered for that FreeCAD install.
"""
import os

PARAM = "User parameter:BaseApp/Preferences/Mod/Material/Resources"


def use_dir(path):
    """Register `path` as FreeCAD's custom material folder and reload the libraries. Returns the MaterialManager."""
    import FreeCAD, Materials
    if not os.path.isdir(path): raise FileNotFoundError(f"no material card folder {path}")
    p = FreeCAD.ParamGet(PARAM)
    p.SetBool("UseMaterialsFromCustomDir", True); p.SetString("CustomMaterialsDir", path)
    mm = Materials.MaterialManager(); mm.refresh()
    return mm


def card(mm, name):
    """The one material named `name` (KeyError if none, ValueError if several)."""
    hits = [m for _, m in mm.Materials.items() if m.Name == name]
    if not hits: raise KeyError(f"no material card named {name!r}")
    if len(hits) > 1: raise ValueError(f"{len(hits)} material cards named {name!r}")
    return hits[0]


def read_card(path):
    """A .FCMat card's fields without FreeCAD (plain python, for tests): {'UUID', 'Name', 'SourceURL', ...,
    'Density'}. The format is FreeCAD's YAML subset; only "key: value" lines are read, by indentation."""
    out = {}
    for line in open(path, encoding="utf-8-sig"):
        s = line.strip()
        if not s or s.startswith(("#", "---")) or ":" not in s: continue
        k, v = s.split(":", 1); v = v.strip().strip('"')
        if line.startswith("  ") and not line.startswith("    ") and v:     # General: fields
            out.setdefault(k, v)
        elif line.startswith("    ") and k != "UUID":                       # a model's property
            out[k] = v
    return out
