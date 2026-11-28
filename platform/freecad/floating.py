# SPDX-License-Identifier: GPL-3.0-or-later
"""Floating regions: where a part printed in a given orientation starts in mid-air (the slicer's "floating regions"
warning, OrcaSlicer). Plain python on a triangle mesh, so it runs without FreeCAD: give it a FreeCAD shape's
tessellate() output, or an STL's triangles.

A floating start is a vertex, an edge or a flat patch that is lower than everything it touches and faces down: a
connected group of vertices at one height (within `tol`), above the bed, whose every neighbour outside the group is
higher, and with at least one face touching it that points down. A pit (a hole's floor, an upward-facing pocket) has
no downward face and isn't one: something under it holds it up.

    starts = floating_starts(points, triangles, bed_z=0.0)   # [(z, (xmin, xmax, ymin, ymax), n_vertices)]

vt350#312: the dancer stacks' 45-degree chevron rungs left a 1 mm sliver of plate hanging inside each window where
the post's window ran past the post; Orca found it on the wear rig ("It seems object rig_1 has floating regions").
"""


def floating_starts(points, triangles, bed_z=0.0, tol=1e-3, down=-0.05):
    """points: [(x, y, z)]; triangles: [(i, j, k)] into points; up is +Z. -> [(z, (xmin, xmax, ymin, ymax), n)]"""
    # merge coincident points (a tessellation repeats a vertex per face)
    key = lambda p: (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
    ids, pts, remap = {}, [], []
    for p in points:
        k = key(p)
        if k not in ids: ids[k] = len(pts); pts.append(tuple(p))
        remap.append(ids[k])
    tris = [tuple(remap[i] for i in t) for t in triangles]
    nb = [set() for _ in pts]
    downward = [False] * len(pts)
    for a, b, c in tris:
        if len({a, b, c}) < 3: continue
        for u, v in ((a, b), (b, c), (c, a)):
            nb[u].add(v); nb[v].add(u)
        pa, pb, pc = pts[a], pts[b], pts[c]
        ux, uy, uz = (pb[i] - pa[i] for i in range(3))
        vx, vy, vz = (pc[i] - pa[i] for i in range(3))
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        ln = (nx * nx + ny * ny + nz * nz) ** 0.5
        if ln > 0 and nz / ln < down:
            downward[a] = downward[b] = downward[c] = True
    # group the vertices joined by level edges
    par = list(range(len(pts)))
    def find(v):
        while par[v] != v: par[v] = par[par[v]]; v = par[v]
        return v
    for v, ns in enumerate(nb):
        for u in ns:
            if abs(pts[u][2] - pts[v][2]) <= tol: par[find(u)] = find(v)
    groups = {}
    for v in range(len(pts)):
        if nb[v]: groups.setdefault(find(v), []).append(v)
    out = []
    for g in groups.values():
        z = pts[g[0]][2]
        if z <= bed_z + tol or not any(downward[v] for v in g): continue
        gs = set(g)
        ext = [u for v in g for u in nb[v] if u not in gs]
        if ext and all(pts[u][2] > z + tol for u in ext):
            xs, ys = [pts[v][0] for v in g], [pts[v][1] for v in g]
            out.append((z, (min(xs), max(xs), min(ys), max(ys)), len(g)))
    return sorted(out)


def stl_triangles(path):
    """(points, triangles) of an ASCII or binary STL"""
    import struct
    data = open(path, "rb").read()
    pts = []
    if data[:5] == b"solid" and b"facet" in data[:400]:
        for ln in data.decode("ascii", "replace").splitlines():
            ln = ln.strip()
            if ln.startswith("vertex"): pts.append(tuple(float(x) for x in ln.split()[1:4]))
    else:
        n = struct.unpack("<I", data[80:84])[0]
        for i in range(n):
            o = 84 + i * 50 + 12
            for k in range(3): pts.append(struct.unpack("<3f", data[o + 12 * k:o + 12 * k + 12]))
    return pts, [(i, i + 1, i + 2) for i in range(0, len(pts), 3)]
