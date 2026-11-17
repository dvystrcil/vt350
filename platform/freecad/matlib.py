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


# ---- writing cards (plain python): FreeCAD's .FCMat layout, as its own cards use it -------------------------------
FATHER = "9cdda8b6-b606-4778-8f13-3934d8668e67"           # model "Father" (material family)
DENSITY = "454661e5-265b-4320-8e6f-fcf6223ac3af"          # model "Density"
BASIC_RENDERING = "f006c7e4-35b7-43d5-bbf9-c5d572309e6e"  # appearance model "Basic Rendering"


def card_uuid(namespace, name):
    """A stable UUID for a card: the same name always gets the same UUID, so a regenerated card keeps the identity
    that models saved against it."""
    import uuid
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{namespace}/{name}"))


def rgba(hex_rgb, alpha=1.0):
    h = hex_rgb.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return f"({r:.6g},{g:.6g},{b:.6g},{alpha:.6g})"


def _q(v):
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def card_text(general, father=None, density_kg_m3=None, inherits=None, colour=None, transparency=0.0, shininess=0.2):
    """A card's text. general: ordered {"UUID", "Name", "Author", ...}. inherits: (name, uuid) of the parent card.
    colour: "#rrggbb" for a Basic Rendering appearance."""
    out = ["---", "# Generated: do not edit by hand (see the README in this folder)", "General:"]
    out += [f"  {k}: {_q(v)}" for k, v in general.items() if v is not None]
    if inherits:
        out += ["Inherits:", f"  {inherits[0]}:", f"    UUID: {_q(inherits[1])}"]
    models = []
    if father: models += ["  Father:", f"    UUID: {_q(FATHER)}", f"    Father: {_q(father)}"]
    if density_kg_m3 is not None: models += ["  Density:", f"    UUID: {_q(DENSITY)}", f"    Density: {_q(f'{density_kg_m3:g} kg/m^3')}"]
    if models: out += ["Models:"] + models
    if colour:
        h = colour.lstrip("#"); dim = "#" + "".join(f"{int(int(h[i:i + 2], 16) * 0.3):02x}" for i in (0, 2, 4))
        out += ["AppearanceModels:", "  Basic Rendering:", f"    UUID: {_q(BASIC_RENDERING)}",
                f"    AmbientColor: {_q(rgba(dim))}", f"    DiffuseColor: {_q(rgba(colour))}",
                f"    EmissiveColor: {_q('(0,0,0,1)')}", f"    Shininess: {_q(f'{shininess:g}')}",
                f"    SpecularColor: {_q('(0.1,0.1,0.1,1)')}", f"    Transparency: {_q(f'{transparency:g}')}"]
    return "\n".join(out) + "\n"
