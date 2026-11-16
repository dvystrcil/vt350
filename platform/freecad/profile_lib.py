"""Clean extrusion profiles (vt350#195).

The imported 2020/2040/4040s are heavy and broken for OCC: the 2040s carry 94-pole B-spline edges, vertex tolerances up to
0.006, 0.0046 mm gaps and a profile 0.002 mm out of flat, so every boolean on them fails, and their tapped end bores are
modelled as thread rings (one 2040 is ~20 MB of BRep). This module rebuilds a straight member as an exact prism:

  mid_profile(s, ax)    the member's cross-section, sliced at several points along it (not its end face: the ends carry
                        the tapped bore, Ø5 against the Ø4.2 bore along the length), each slice rebuilt as exact lines and
                        arcs on an exact plane with shared vertices; the area most slices agree on wins, so a slice through
                        a cross-hole or a lite-46 extension piece made from an end face is outvoted
  cross_holes(s, ax)    every cylindrical hole across the member (axis not along it), one cylinder per face, at the face's
                        own extent: cut from the prism they put back exactly the material the original lacks there
  rebuild(s, ax, ...)   the prism from lo to hi with the holes cut, plus a report

and sample_diff, a boolean-free comparison of two solids by point sampling (the originals can't be booleaned).
"""
import FreeCAD, Part, math, random
V = FreeCAD.Vector


def unit(ax):
    return V(*[1.0 if i == ax else 0.0 for i in range(3)])


def axis_of(s):
    """The member's long axis (0, 1, 2) and its optimal box."""
    ob = s.optimalBoundingBox()
    dims = (ob.XLength, ob.YLength, ob.ZLength)
    return max(range(3), key=lambda i: dims[i]), ob


def snap_end(v, grid=0.1, tol=0.01):
    """A box end µm off a round number (-520.0009, 480.0023) -> the round number; anything else unchanged."""
    r = round(v / grid) * grid
    return r if abs(r - v) <= tol else v


def clean_wires(in_wires, ax, at, snap=0.01):
    """Wires (closed, or open with gaps up to `snap`; roughly on the plane coordinate[ax] == at) -> (exact planar face,
    report). Each edge becomes a line, an arc (a circle or a spline within 0.01 of one), a full circle, or (only where no
    arc fits) an interpolated B-spline; all on the exact plane, with points within `snap` merged into one vertex."""
    def proj(p):
        c = [p.x, p.y, p.z]; c[ax] = at; return V(*c)
    verts = []
    def key(p):
        q = proj(p)
        for v in verts:
            if (v - q).Length < snap: return v
        verts.append(q); return q
    rep = {"line": 0, "arc": 0, "spline_as_arc": 0, "spline_kept": 0, "worst_arc_dev": 0.0}
    es = []                      # pooled: a slice can split one loop across several open wires
    for w in in_wires:
        for e in (w.OrderedEdges if w.isClosed() else w.Edges):
            a, b = e.FirstParameter, e.LastParameter
            p0, p1 = key(e.valueAt(a)), key(e.valueAt(b))
            if e.Orientation == "Reversed": p0, p1 = p1, p0
            t = type(e.Curve).__name__
            if t == "Line":
                if (p1 - p0).Length > 1e-7: es.append(Part.LineSegment(p0, p1).toShape()); rep["line"] += 1
                continue
            pts = [proj(e.valueAt(a + (b - a) * k / 24)) for k in range(25)]
            if e.Orientation == "Reversed": pts.reverse()
            if t == "Circle" and e.isClosed():
                es.append(Part.Circle(proj(e.Curve.Center), unit(ax), e.Curve.Radius).toShape()); rep["arc"] += 1; continue
            if (p1 - p0).Length < 1e-6:          # a closed edge (a full circle stored as a spline): circle fit
                c3 = Part.Circle(pts[0], pts[8], pts[16])
                dev = max(abs((p - c3.Center).Length - c3.Radius) for p in pts)
                if dev < 0.01:
                    es.append(c3.toShape()); rep["spline_as_arc"] += 1; rep["worst_arc_dev"] = max(rep["worst_arc_dev"], dev)
                else:
                    bs = Part.BSplineCurve(); bs.interpolate(pts[:-1], PeriodicFlag=True); es.append(bs.toShape()); rep["spline_kept"] += 1
                continue
            arc = Part.Arc(p0, pts[12], p1)
            dev = max(arc.toShape().distToShape(Part.Vertex(p))[0] for p in pts)
            if t in ("Circle", "Ellipse") or dev < 0.01:
                es.append(arc.toShape())
                rep["arc" if t in ("Circle", "Ellipse") else "spline_as_arc"] += 1
                rep["worst_arc_dev"] = max(rep["worst_arc_dev"], dev)
            else:
                bs = Part.BSplineCurve(); bs.interpolate([p0] + pts[1:-1] + [p1]); es.append(bs.toShape()); rep["spline_kept"] += 1
    wires = [Part.Wire(g) for g in Part.sortEdges(es)]
    bad = [w for w in wires if not w.isClosed()]
    if bad: raise RuntimeError(f"{len(bad)} of {len(wires)} profile loops not closed after snapping")
    wires.sort(key=lambda w: -Part.Face(w).Area)
    f = Part.makeFace(wires, "Part::FaceMakerBullseye")
    f = f.Faces[0] if f.ShapeType != "Face" else f
    rep["loops"] = len(wires)
    return f, rep


def mid_profile(s, ax, fracs=(0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85), ob=None, prefer=()):
    """The member's cross-section -> (face on the plane coordinate[ax] == lo, report). Sliced at each fraction of its
    length; the area (to 0.01 mm²) most slices share wins (ties: the earlier fraction), except that an area in `prefer` beats
    any area not in it."""
    ob = ob or s.optimalBoundingBox()
    lo = (ob.XMin, ob.YMin, ob.ZMin)[ax]; L = (ob.XLength, ob.YLength, ob.ZLength)[ax]
    got, fails = [], []
    for fr in fracs:
        at = lo + L * fr
        try:
            f, rep = clean_wires(s.slice(unit(ax), at), ax, at)
            got.append((round(f.Area, 2), fr, at, f, rep))
        except Exception as e:
            fails.append((fr, repr(e)[:80]))
    if not got: raise RuntimeError(f"no slice gave a profile: {fails}")
    votes = {}
    for g in got: votes.setdefault(g[0], []).append(g)
    # a member whose slices disagree (lite-46 extended rails with pieces extruded from an end face, tapped bore and
    # all) takes the area `prefer` names if one of its slices has it: what the members that agree with themselves have
    pool = {a: g for a, g in votes.items() if a in prefer} or votes
    area, win = max(pool.items(), key=lambda kv: (len(kv[1]), -kv[1][0][1]))
    _, fr, at, f, rep = win[0]
    f = f.translated(unit(ax) * (lo - at))
    rep.update(area=f.Area, slice_at=fr, votes={a: len(g) for a, g in votes.items()}, slice_fails=fails)
    return f, rep


def cross_holes(s, ax, r_max=6.0):
    """Every cylindrical face across the member (axis on a coordinate axis other than ax, radius <= r_max) ->
    [dict(dir, line, r, lo, hi)], one per stretch of one axis line and radius (overlapping faces merged): the hole's
    cylinder from lo to hi along dir, through the point `line` (its coordinate on dir is 0)."""
    spans = {}
    for f in s.Faces:
        su = f.Surface
        if type(su).__name__ != "Cylinder" or su.Radius > r_max: continue
        a = su.Axis; comp = (abs(a.x), abs(a.y), abs(a.z))
        d = max(range(3), key=lambda i: comp[i])
        if d == ax or comp[d] < 1 - 1e-6: continue
        c = [su.Center.x, su.Center.y, su.Center.z]; c[d] = 0.0
        b = f.BoundBox
        k = (d, tuple(round(x, 2) for x in c), round(su.Radius, 3))
        spans.setdefault(k, (tuple(c), su.Radius, []))[2].append(((b.XMin, b.YMin, b.ZMin)[d], (b.XMax, b.YMax, b.ZMax)[d]))
    # one hole per stretch: faces of one hole (halves, pieces either side of a slot) that overlap or touch are merged,
    # since coaxial cutting tools of one radius with coincident faces leave OCC an invalid solid (lite-47's 4040 (2))
    out = []
    for (d, _, _), (c, r, iv) in spans.items():
        iv.sort(); cur = list(iv[0])
        for lo, hi in iv[1:]:
            if lo <= cur[1] + 0.05: cur[1] = max(cur[1], hi)
            else: out.append(dict(dir=d, line=c, r=r, lo=cur[0], hi=cur[1])); cur = [lo, hi]
        out.append(dict(dir=d, line=c, r=r, lo=cur[0], hi=cur[1]))
    return out


def hole_solid(h, extra=0.0):
    p = list(h["line"]); p[h["dir"]] = h["lo"] - extra
    return Part.makeCylinder(h["r"], h["hi"] - h["lo"] + 2 * extra, V(*p), unit(h["dir"]))


def rebuild(s, ax=None, drop=lambda h: False, extra_holes=(), prefer=()):
    """An imported straight member -> (clean solid, report): the mid profile extruded over the member's (snapped)
    length, minus its cross-holes (those `drop` rejects left out) and any extra hole solids."""
    if ax is None: ax, ob = axis_of(s)
    else: ob = s.optimalBoundingBox()
    lo = snap_end((ob.XMin, ob.YMin, ob.ZMin)[ax]); hi = snap_end((ob.XMax, ob.YMax, ob.ZMax)[ax])
    f, rep = mid_profile(s, ax, ob=ob, prefer=prefer)
    f.translate(unit(ax) * (lo - (ob.XMin, ob.YMin, ob.ZMin)[ax]))
    prism = f.extrude(unit(ax) * (hi - lo))
    holes = cross_holes(s, ax)
    kept = [h for h in holes if not drop(h)]
    tools = [hole_solid(h, 0.01) for h in kept] + list(extra_holes)   # 0.01 past each face: no coplanar skin
    out, split_kept, method = prism, False, "none"
    if tools:
        out, method = prism.cut(tools), "one cut"
        if not out.isValid():                # OCC is not consistent here (lite-47's 4040 (2): "Unorientable shape"):
            out, method = prism, "hole by hole"    # one hole at a time, each step checked
            for t in tools:
                n = out.cut(t)
                if not n.isValid(): raise RuntimeError(f"cutting a hole at {t.BoundBox} leaves an invalid solid")
                out = n
        # merge the faces the cut split, on a COPY: removeSplitter (UnifySameDomain) edits shared sub-shapes of the shape
        # it is called on, so a merge that fails (lite-47's 4040 (2) rail) leaves the original invalid too
        merged = out.copy().removeSplitter()
        if merged.isValid(): out = merged
        else: split_kept = True
    rep.update(ax=ax, lo=lo, hi=hi, holes=len(holes), holes_kept=len(kept), holes_dropped=len(holes) - len(kept),
               extra_holes=len(extra_holes), split_faces_kept=split_kept, cut_method=method, prism_volume=prism.Volume, volume=out.Volume,
               dropped=[(h["dir"], [round(x, 2) for x in h["line"]], round(h["r"], 3), round(h["lo"], 2), round(h["hi"], 2))
                        for h in holes if drop(h)])
    return out, rep


def sample_diff(a, b, ax, n=4000, end_margin=25.0, seed=1):
    """Points in the middle of the member (end_margin clear of each end) where a and b disagree on inside/outside, and
    how many are inside either: a boolean-free shape comparison."""
    r = random.Random(seed); ob = a.optimalBoundingBox()
    lo = [ob.XMin, ob.YMin, ob.ZMin]; hi = [ob.XMax, ob.YMax, ob.ZMax]
    lo[ax] += end_margin; hi[ax] -= end_margin
    inside = bad = 0
    for _ in range(n):
        p = V(*[r.uniform(lo[i], hi[i]) for i in range(3)])
        ia, ib = a.isInside(p, 1e-3, True), b.isInside(p, 1e-3, True)
        if ia or ib: inside += 1
        if ia != ib: bad += 1
    return bad, inside
