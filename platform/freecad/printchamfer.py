# printchamfer: chamfer a printed part's edges by its print orientation (vt350 owner rule, 2026-11-18, in
# parts/printed/README.md): the edges of the face on the bed get `bottom` (0.6 mm: no elephant's foot), the edges of
# every face that looks up get `top` (1.0 mm: not sharp). Generic: any part, any print direction `up`.
#
#   import printchamfer as pc
#   new, info = pc.chamfer(shape, up=FreeCAD.Vector(0, 0, 1))      # bottom 0.6, top 1.0, in 0.2 mm layers by default
#   left = pc.unchamfered(shape, new, up)                            # [] when every bed/top edge got its chamfer
#
# - Bores are left sharp (owner: "bores do not need chaphers unless its for a flathead screw"): an edge on a hole's
#   wall (is_bore) is skipped. A flat-head screw's countersink is part of the design, not added here.
# - Only CONVEX edges are chamfered (a chamfer on a concave edge would add material), and only where the two faces
#   meet at more than SHARP_DEG (a near-tangent edge isn't sharp).
# - A narrow face can't take the full size on both its edges (a 2 mm rim with 1.0 mm each side would vanish): an edge
#   gets at most NARROW_FRAC of its narrower face's width (2 x area / perimeter), rounded down to a whole number of
#   layers (`step`), and at least one layer (smaller is skipped and reported). info["reduced"] / info["skipped"] list them, for the pass's log.
# - All edges go in ONE Part::Chamfer (per-edge sizes) in a scratch document, closed afterwards; the input is untouched.
#   OCC can quietly leave edges out of a big chamfer, so every edge still where it was afterwards is then done on its
#   own (longest first), at its size or else a layer or two less; one that takes neither is listed in info["failed"].
# Never saves anything.
import FreeCAD, Part, math

SHARP_DEG = 30.0           # faces meeting at more than this (normals apart) make an edge worth chamfering
NARROW_FRAC = 0.3          # an edge's chamfer <= this x its narrower face's width
STEP = 0.2                 # mm: the layer height. A 45 deg chamfer on a first-layer or top edge rises as much as it is
                           # wide, so every size is a whole number of layers (owner, 2026-11-18: "the print layer
                           # height is 0.2 so the slicer will fight trying to make 0.25 work"); below one layer: none
PLANE_TOL = 0.01           # mm: a face this close to the lowest point (along up) is on the bed


def _normal_at(face, pt):
    u, v = face.Surface.parameter(pt)
    return face.normalAt(u, v)


def _width(face):
    per = sum(e.Length for e in face.Edges)
    return 2.0 * face.Area / per if per > 0 else 0.0


def _faces_of(shape, edge):
    return shape.ancestorsOfType(edge, Part.Face)


def _edge_info(shape, edge):
    """(f1, f2, n1, n2, convex, angle_deg) for an edge shared by two faces, else None"""
    fs = _faces_of(shape, edge)
    if len(fs) != 2: return None
    a0, a1 = edge.FirstParameter, edge.LastParameter
    m = edge.valueAt((a0 + a1) / 2)
    n1, n2 = _normal_at(fs[0], m), _normal_at(fs[1], m)
    # the sharpest along the edge (a slanted hole's mouth is 45 deg on one side, 135 on the other)
    ang = max(math.degrees(_normal_at(fs[0], q).getAngle(_normal_at(fs[1], q)))
              for q in (edge.valueAt(a0 + (a1 - a0) * k / 8) for k in range(1, 8)))
    d = n2 - n1 * n1.dot(n2)                      # face 2's normal, in face 1's plane
    if d.Length < 1e-9: return None
    d.normalize()
    # convex: face 1 goes on AWAY from face 2's normal (a box's top runs on from its side edge towards -n2);
    # at a concave edge face 1 runs on along +n2 (the step's top runs out from the wall it meets)
    convex = fs[0].distToShape(Part.Vertex(m - d * 0.02))[0] < 1e-6
    return fs[0], fs[1], n1, n2, convex, ang


def is_bore(face):
    """a hole's wall: a cylinder or cone whose surface faces its own axis (an outside curve, like a pipe's or a
    swept corner's, faces away from it). Owner, 2026-11-18: "bores do not need chaphers unless its for a flathead
    screw" (a countersink is designed in, not added here)."""
    srf = face.Surface
    if not isinstance(srf, (Part.Cylinder, Part.Cone)): return False
    u0, u1, v0, v1 = face.ParameterRange
    q = face.valueAt((u0 + u1) / 2, (v0 + v1) / 2); n = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    a = srf.Axis; loc = srf.Center if isinstance(srf, Part.Cylinder) else srf.Apex
    r = q - (loc + a * (q - loc).dot(a))
    return n.dot(r) < 0


def _planar_facing(face, up, sign):
    """face is planar and its outward normal is sign*up"""
    if not isinstance(face.Surface, Part.Plane): return False
    n = _normal_at(face, face.CenterOfMass)
    return n.dot(up) * sign > 1 - 1e-6


def _layers(x, step): return math.floor(x / step + 1e-6) * step


def select(shape, up, bottom=0.6, top=1.0, step=STEP):
    """{edge index (0-based): (size, kind)} and the reduced/skipped lists, for `shape` printed with `up` pointing up"""
    up = FreeCAD.Vector(up); up.normalize()
    lo = min(v.Point.dot(up) for v in shape.Vertexes)
    bed = [f for f in shape.Faces if _planar_facing(f, up, -1) and abs(f.CenterOfMass.dot(up) - lo) < PLANE_TOL]
    tops = [f for f in shape.Faces if _planar_facing(f, up, +1)]
    want, reduced, skipped = {}, [], []
    for kind, faces, size in (("bottom", bed, bottom), ("top", tops, top)):
        for f in faces:
            for e in f.Edges:
                i = next((k for k, x in enumerate(shape.Edges) if x.isSame(e)), None)
                if i is None or i in want: continue
                inf = _edge_info(shape, shape.Edges[i])
                if inf is None: continue
                f1, f2, n1, n2, convex, ang = inf
                if not convex or ang < SHARP_DEG or is_bore(f1) or is_bore(f2): continue
                cap = NARROW_FRAC * min(_width(f1), _width(f2))
                d = round(_layers(min(size, cap), step), 3)
                m = shape.Edges[i].valueAt((shape.Edges[i].FirstParameter + shape.Edges[i].LastParameter) / 2)
                where = tuple(round(c, 1) for c in m)
                if d < step - 1e-9: skipped.append((kind, where, round(cap, 2))); continue
                if d < size - 1e-9: reduced.append((kind, where, d))
                want[i] = (d, kind)
    return want, reduced, skipped, bed, tops


def chamfer(shape, up, bottom=0.6, top=1.0, step=STEP):
    """the chamfered copy of `shape` and info {bottom, top, reduced, skipped, removed_mm3}"""
    for x in (bottom, top):
        if abs(_layers(x, step) - x) > 1e-6: raise ValueError(f"printchamfer: {x} mm is not a whole number of {step} mm layers")
    want, reduced, skipped, bed, tops = select(shape, up, bottom, top, step)
    info = dict(bottom=sum(1 for d, k in want.values() if k == "bottom"), top=sum(1 for d, k in want.values() if k == "top"),
                reduced=reduced, skipped=skipped, bed_faces=len(bed), top_faces=len(tops), removed_mm3=0.0)
    if not want: return shape.copy(), info
    info["failed"] = []
    try: doc = FreeCAD.newDocument("printchamfer_scratch", hidden=True)
    except TypeError: doc = FreeCAD.newDocument("printchamfer_scratch")
    try:
        b = doc.addObject("Part::Feature", "Base"); b.Shape = shape
        c = doc.addObject("Part::Chamfer", "Chamfer"); c.Base = b
        c.Edges = [(i + 1, d, d) for i, (d, k) in sorted(want.items())]
        doc.recompute()
        o = c.Shape
        out = o.copy() if _good(o, shape, shape) else shape.copy()
    finally:
        FreeCAD.closeDocument(doc.Name)
    # OCC can drop edges from a big chamfer without an error: finish each edge still where it was, one at a time on
    # the result (at its size, else half), longest first; an edge that takes neither is listed in info["failed"]
    for i in sorted(want, key=lambda i: -shape.Edges[i].Length):
        e = shape.Edges[i]; d, kind = want[i]
        cur = _on_line(e, out)
        if cur is None: continue
        for dd in [round(d - k * step, 3) for k in range(3)]:      # its size, else a layer or two less
            if dd < step - 1e-9: continue
            try: o = out.makeChamfer(dd, [cur])
            except Exception: continue
            if _good(o, out, shape) and _on_line(e, o) is None:
                out = o
                if dd < d: info["reduced"].append((kind, _mid(e), dd))
                break
        else:
            info["failed"].append((kind, _mid(e)))
    info["bottom"] = sum(1 for i, (d, k) in want.items() if k == "bottom") - sum(1 for k, w in info["failed"] if k == "bottom")
    info["top"] = sum(1 for i, (d, k) in want.items() if k == "top") - sum(1 for k, w in info["failed"] if k == "top")
    info["removed_mm3"] = shape.Volume - out.Volume
    return out, info


def _good(o, before, orig):
    return (not o.isNull()) and o.isValid() and len(o.Solids) == len(orig.Solids) and o.Volume < before.Volume - 1e-9


def _on_line(e, shape):
    """the edge of `shape` still lying on edge e's line (trimmed ends allowed), or None"""
    bb = e.BoundBox; bb.enlarge(0.01)
    for n in shape.Edges:
        if n.Length < 0.3 * e.Length or not bb.isInside(_midv(n)): continue
        if e.distToShape(Part.Vertex(_midv(n)))[0] < 1e-4: return n
    return None


def _midv(e): return e.valueAt((e.FirstParameter + e.LastParameter) / 2)


def _mid(e):
    return tuple(round(c, 1) for c in e.valueAt((e.FirstParameter + e.LastParameter) / 2))


def unchamfered(orig, new, up, bottom=0.6, top=1.0, skip=(), step=STEP):
    """edges of `orig` that select() wants chamfered and that `new` still has where they were (an edge on the same
    line, ends possibly trimmed by a neighbour's chamfer): their midpoints (rounded 0.1). `skip`: midpoints to leave
    out (the skipped and failed lists). [] = every bed and top edge got its chamfer."""
    want = select(orig, up, bottom, top, step)[0]
    return [_mid(orig.Edges[i]) for i in want if _mid(orig.Edges[i]) not in skip and _on_line(orig.Edges[i], new) is not None]


def sharp_edges(shape, up, skip=()):
    """convex edges of the bed face or an upward face whose faces still meet at > 60 deg (a chamfered 90 deg edge is
    two 45 deg ones); `skip` = midpoints (rounded 0.1) to ignore (the skipped list). Returns their midpoints."""
    up = FreeCAD.Vector(up); up.normalize()
    lo = min(v.Point.dot(up) for v in shape.Vertexes)
    faces = [f for f in shape.Faces if (_planar_facing(f, up, -1) and abs(f.CenterOfMass.dot(up) - lo) < PLANE_TOL)
             or _planar_facing(f, up, +1)]
    out, seen = [], set()
    for f in faces:
        for e in f.Edges:
            m = e.valueAt((e.FirstParameter + e.LastParameter) / 2); key = tuple(round(c, 1) for c in m)
            if key in seen or key in skip: continue
            seen.add(key)
            inf = _edge_info(shape, e)
            if inf and inf[4] and inf[5] > 60.0 and not (is_bore(inf[0]) or is_bore(inf[1])): out.append(key)
    return out
