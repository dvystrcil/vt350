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
MAP_FILE = os.path.join(HERE, "colours.json")
FIELDS = ("label", "group", "material")
KINDS = ("plastic", "paint", "aluminium", "steel", "brass", "ptfe", "felt")


def load(path=MAP_FILE):
    m = json.load(open(path, encoding="utf-8")); validate(m); return m


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


def role_of(m, label, group, material):
    vals = dict(label=label or "", group=group or "", material=material or "")
    for rule in m["rules"]:
        if all(re.search(rule[f], vals[f]) for f in FIELDS if rule.get(f)):
            return rule["role"]
    return None


def linear(hexstr):
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", hexstr or ""):
        raise ValueError(f"colour {hexstr!r} is not #RRGGBB")
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(round(lin(int(hexstr[i:i + 2], 16)), 6) for i in (1, 3, 5))
