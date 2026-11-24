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


def group_parents(objects):
    """{object Name: the container it sits in} for every object some container's Group lists. An object inside a
    group inside an App::Part is listed in both Groups; its container is the innermost one (the group), so a path
    walked up from it keeps every group. Taking the first container found instead dropped groups such as "Monolith
    gantry" from export_meshes.py's paths, and the licence rules written on the part index's paths missed 267 parts
    (vt350#220, lite-72). Pure Python over .Name / .Group: test_group_parents.py."""
    cands = {}
    for g in objects:
        for k in (getattr(g, 'Group', []) or []): cands.setdefault(k.Name, []).append(g)

    def above(g, seen=()):           # every container g sits in, transitively
        r = set()
        for c in cands.get(g.Name, []):
            if c.Name not in seen and c.Name not in r: r |= {c.Name} | above(c, seen + (g.Name,))
        return r

    par = {}
    for n, cs in cands.items():
        inner = [c for c in cs if not any(c.Name in above(x) for x in cs if x is not c)]
        par[n] = inner[0] if inner else cs[0]
    return par


def group_path(o, par):
    """The labels of the containers o sits in, outermost first (par: group_parents())."""
    r, q = [], par.get(o.Name)
    while q is not None: r.append(q.Label); q = par.get(q.Name)
    return list(reversed(r))


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
