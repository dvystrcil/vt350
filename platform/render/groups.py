"""Which bucket each exported part goes in, for a motion render (vt350#135 AC4, split out of motion.py by vt350#144).

The mesh export (export_meshes.py with VT350_GROUPS) needs only this, so the motion renderer's export cache key hashes
this file, not motion.py: editing the frames or encode code no longer forces a full FreeCAD re-export.

Stdlib only: FreeCAD, Blender and the tests all import it. Generic: no printer's names or numbers.
"""

SEP = "__"                                           # a moving group's bucket key: "<group>__<colour key>"


class Assign:
    """Which bucket an exported part goes in, from a groups file (cad/motion/play.py's, also the FreeCAD player's):
    {"groups": {group: [Name]}, "clip": {Name: [xmin, ymin, zmin, xmax, ymax, zmax]}, "hide": [Name]}.
    None: no groups, every part keeps its bucket (a still render)."""

    def __init__(self, data):
        data = data or {}
        self.group, seen = {}, {}
        for g, names in data.get("groups", {}).items():
            for n in names:
                if n in seen and seen[n] != g:
                    raise ValueError(f"object {n} is in two groups: {seen[n]} and {g}")
                seen[n] = g
        self.group = seen
        self.hide = set(data.get("hide", []))
        moving = sorted(self.hide & set(self.group))
        if moving:
            raise ValueError(f"hide: {', '.join(moving)} moves; hide only parts that stay put")
        self._clip = dict(data.get("clip", {}))

    def bucket(self, name, key):
        """-> (the bucket key, the group or None)."""
        g = self.group.get(name)
        return (key, None) if g is None else (f"{g}{SEP}{key}", g)

    def hidden(self, name):
        return name in self.hide

    def clip(self, name):
        return self._clip.get(name)
