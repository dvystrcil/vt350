# Geometry of a model's parts when some are App::Links (vt350#195): one place that every walker (litelib, clashlib,
# part_index, player, export_meshes, tess_cost, dupes) asks "is this a part, and where is it?".
#
# Why: a copy stored as an App::Link costs the file nothing (the shape is stored once) and the GUI tessellates it once.
# But a link is not a Part::Feature and has no getGlobalPlacement, so walkers that filter on Part::Feature drop links
# silently. FreeCAD 26.3 also deprecates getGlobalPlacement (removed in 27.2); gplace() replaces it everywhere.
#
# Only FreeCAD imports, nothing of ours: a gpu-batch pod stages this file flat beside the scripts that use it.
# Tests: test_links_fc.py (needs FreeCAD).
import FreeCAD


def gplace(o):
    """o's global placement: its parents' (App::Part) placements times its own. Matches getGlobalPlacement for an
    ordinary object, and works for an App::Link, which has none."""
    par = o.getParentGeoFeatureGroup()
    return (gplace(par) if par is not None else FreeCAD.Placement()).multiply(o.Placement)


def link_target(o):
    """What an App::Link finally points to (through chains of links); any other object itself."""
    return o.getLinkedObject(True) if o.TypeId == 'App::Link' else o


def drawn_vo(o):
    """The view object whose ShapeAppearance / Transparency the GUI draws for o (None headless). For an App::Link
    that's its target's, unless the link overrides (OverrideMaterial / OverrideMaterialList): a link's own
    ShapeAppearance can hold a default that is never drawn. lite-52 (vt350#195): its links' undrawn defaults came out
    teal in the render, and a colour check that read them failed all 1,001 correct links."""
    vo = getattr(o, "ViewObject", None)
    if vo is None or o.TypeId != 'App::Link': return vo
    if getattr(vo, "OverrideMaterial", False) or any(getattr(vo, "OverrideMaterialList", None) or []): return vo
    t = link_target(o)
    return getattr(t, "ViewObject", None) if t is not None else vo


def is_leaf(o):
    """A part with solids: a Part::Feature, or an App::Link to one. Not containers (App::Part), not meshes."""
    t = link_target(o)
    if t is None or t.TypeId == 'App::Part' or not t.isDerivedFrom('Part::Feature'): return False
    return not o.Shape.isNull() and bool(o.Shape.Solids)


def gshape(o):
    """o's shape in the global frame. For a link, the target's shape where the link puts it. (A link's Shape is a
    Compound wrapper: use .Solids, not .CenterOfMass, on the result.)"""
    s = o.Shape.copy(); s.Placement = gplace(o); return s


def is_mesh(o):
    """A Mesh::Feature, or a link to one (a lite-50 mesh stand-in)."""
    t = link_target(o)
    return t is not None and t.isDerivedFrom('Mesh::Feature')


def gmesh(o):
    """o's mesh in the global frame (a Mesh::Feature or a link to one)."""
    import Mesh
    m = Mesh.Mesh(link_target(o).Mesh); m.Placement = FreeCAD.Placement(); m.transform(gplace(o).toMatrix()); return m
