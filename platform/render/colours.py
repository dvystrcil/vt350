"""Render-time colour map (#38): which role a model part plays, and that role's colour. Stdlib only, so the
FreeCAD export (export_meshes.py), Blender (render.py) and the tests all share it.

colours.json = {"roles": {name: {hex, kind, roughness, note}}, "rules": [{role, label?, group?, material?}]}.
A rule matches when every regex it gives is found (re.search) in the part's label, group path (" / "-joined
ancestors) and ShapeMaterial name. Rules are tried in order and the first one that matches wins. A part no rule
matches keeps the model's own colour. Colours are sRGB hex; Blender gets them linearised.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def map_file(here=HERE, root=ROOT):
    """The colour map to read: the map is the printer's data, this code is generic (vt350#122). $VT350_COLOURS
    (unless "none", export_meshes.py's "the model's own colours"), else a colours.json beside this file (a gpu-batch
    pod stages everything flat), else the checkout's cad/render/colours.json."""
    env = os.environ.get("VT350_COLOURS")
    if env and env != "none":
        return env
    tried = [os.path.join(here, "colours.json"), os.path.join(root, "cad", "render", "colours.json")]
    for p in tried:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError("colours.json not found: " + ", ".join(tried))


try:
    MAP_FILE = map_file()
except FileNotFoundError:
    MAP_FILE = None                                  # load() then needs a path; a render without a map still runs
FIELDS = ("label", "group", "material")
KINDS = ("plastic", "paint", "aluminium", "steel", "brass", "ptfe", "felt", "glass")


def load(path=None):
    m = json.load(open(path or map_file(), encoding="utf-8")); validate(m); return m


def validate(m):
    for name, r in m["roles"].items():
        linear(r["hex"])
        if r.get("kind", "plastic") not in KINDS:
            raise ValueError(f"role {name}: kind {r.get('kind')!r} not in {KINDS}")
    for i, rule in enumerate(m["rules"]):
        if rule.get("role") not in m["roles"]:
            raise ValueError(f"rule {i}: role {rule.get('role')!r} is not defined in roles")
        if not any(rule.get(f) for f in FIELDS):
            raise ValueError(f"rule {i}: needs at least one of {FIELDS}")
        for f in FIELDS:
            if rule.get(f): re.compile(rule[f])
    for i, v in enumerate(m.get("visibility", [])):    # render visibility flags: {tag, label|group, hide: "all"|[views]}
        if not v.get("tag"): raise ValueError(f"visibility {i}: needs a tag")
        if not (v.get("label") or v.get("group")): raise ValueError(f"visibility {i} ({v['tag']}): needs a label or group")
        h = v.get("hide")
        if not (h == "all" or (isinstance(h, list) and h)):
            raise ValueError(f"visibility {i} ({v['tag']}): hide must be \"all\" or a list of view names")
        for f in ("label", "group"):
            if v.get(f): re.compile(v[f])


def role_of(m, label, group, material):
    vals = dict(label=label or "", group=group or "", material=material or "")
    for rule in m["rules"]:
        if all(re.search(rule[f], vals[f]) for f in FIELDS if rule.get(f)):
            return rule["role"]
    return None


def vis_tag(m, label, group):
    """The visibility flag a part carries (the first matching rule's tag), or None."""
    for v in (m or {}).get("visibility", []):
        if all(re.search(v[f], {"label": label or "", "group": group or ""}[f]) for f in ("label", "group") if v.get(f)):
            return v["tag"]
    return None


def hidden_in(m, tag, view):
    """Whether parts flagged `tag` are left out of the render of `view`."""
    v = next((v for v in (m or {}).get("visibility", []) if v["tag"] == tag), None) if tag else None
    return bool(v) and (v["hide"] == "all" or view in v["hide"])


def standin_skip(name, visible, standin_for, real, use_standins=False):
    """Whether the render export leaves this part out (vt350#195 AC3). A stand-in (standin_for = its real part's
    Name) is a cheap shape the GUI shows; its real part stays in the model hidden, since a hidden part is never
    tessellated when the GUI opens the file. `real` = the Names stand-ins stand in for. The render draws the real
    part and leaves out its stand-in, or the other way round with use_standins (a quick preview). Every other part,
    and a hidden stand-in, follows its own visibility."""
    if standin_for: return not (use_standins and visible)
    if name in real: return use_standins
    return not visible


def audit(m, parts):
    """The parts no rule matches (vt350#91), grouped by (group path, material): a list of {"group", "material", "n",
    "labels": {label: count}}, most parts first, then by group and material. parts = (label, group, material) for
    every part the export gave the map, whatever its material."""
    sets = {}
    for label, group, material in parts:
        if role_of(m, label, group, material) is None:
            g = sets.setdefault((group or "", material or ""), {})
            g[label] = g.get(label, 0) + 1
    out = [{"group": k[0], "material": k[1], "n": sum(v.values()), "labels": dict(sorted(v.items()))}
           for k, v in sets.items()]
    return sorted(out, key=lambda g: (-g["n"], g["group"], g["material"]))


def audit_text(groups, total):
    """colour-audit.txt. The first line is the count, so a report can quote it alone; then each set
    ("<n>  <material>  <group>", "(no group)" for a top-level part) with its labels under it, "x<k>" when a label occurs k > 1 times.
    groups None = the colour map is off."""
    if groups is None:
        return "unmatched: n/a (colour map off: every part keeps the model's colour)\n"
    n = sum(g["n"] for g in groups)
    if not n:
        return f"unmatched: 0 of {total} parts\n"
    lines = [f"unmatched: {n} of {total} parts, in {len(groups)} group/material sets",
             "(they keep the model's colour; a printed part among them needs a rule in colours.json)", ""]
    for g in groups:
        lines.append(f"{g['n']:>3}  {g['material']}  {g['group'] or '(no group)'}")
        lines += [f"       {lab}" + (f"  x{k}" if k > 1 else "") for lab, k in g["labels"].items()]
    return "\n".join(lines) + "\n"


def linear(hexstr):
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", hexstr or ""):
        raise ValueError(f"colour {hexstr!r} is not #RRGGBB")
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(round(lin(int(hexstr[i:i + 2], 16)), 6) for i in (1, 3, 5))
