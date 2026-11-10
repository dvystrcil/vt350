# Voron logos, orange with a white inset (user, 2026-11-09, #74). Shared by every export (export_meshes.py for the
# full printer, export_exploded.py), so all renders show the logos the same way. Needs FreeCAD; tested by
# test_logos.py.
#
# Each logo is one solid, so the inset is picked by FACE: the three slash floors (planar, facing out along N, DEPTH mm
# below the part's own outermost point along N) plus every face touching a floor that lies between the floor and
# 1.5 mm above it (the slash walls and chamfers). Measured from the part itself, not a global level, so the same part
# works wherever a model puts it. Exactly 3 floors, or it raises: a changed part must not silently colour wrong faces.
import re
import FreeCAD

V = FreeCAD.Vector
# label: (outward normal of the logo face, slash floor depth below the part's outermost point along it), measured on
# vt350-filter-3 from the outermost VERTEX (a curved face's bounding box overshoots it): hinge -Y 81.913 vs floors
# 85.094 (3.18); cap top Z -10.907 vs floors -11.507 (0.60). Faces 0.08 mm off (chamfer steps) stay out (tol 0.05).
LOGOS = {"StealthMax 3.2_LidFrontHinge": (V(0, -1, 0), 3.18),
         "StealthMax M_2.5a_LogoCap": (V(0, 0, 1), 0.60)}
SLASHES = 3


def _facing(f, n):
    try: return f.normalAt(*f.Surface.parameter(f.CenterOfMass)).dot(n) > 0.95
    except Exception: return False


def inset(s, n, depth):
    """(inset faces, rest faces) of shape s for a logo facing n with its slash floors `depth` below the outermost."""
    top = max(v.Point.dot(n) for v in s.Vertexes)
    level = top - depth
    lv = lambda f: f.CenterOfMass.dot(n)
    floors = [f for f in s.Faces if f.Surface.__class__.__name__ == "Plane" and _facing(f, n) and abs(lv(f) - level) < 0.05]
    if len(floors) != SLASHES:
        raise RuntimeError(f"logo: {len(floors)} slash floors {depth} mm below the outer face, expected {SLASHES}")
    fe = [e for f in floors for e in f.Edges]
    walls = [f for f in s.Faces if not any(f.isSame(g) for g in floors) and level - 0.05 < lv(f) < level + 1.5
             and not _facing(f, n) and any(e.isSame(g) for e in f.Edges for g in fe)]
    ins = floors + walls
    return ins, [f for f in s.Faces if not any(f.isSame(g) for g in ins)]


def split(label, s):
    """(inset, rest) faces if `label` (or a FreeCAD copy of it: Label001) is a logo part, else None."""
    base = re.sub(r"\d{3}$", "", label)
    if base not in LOGOS: return None
    return inset(s, *LOGOS[base])
