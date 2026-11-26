# SPDX-License-Identifier: GPL-3.0-or-later
"""A beam model of an extrusion frame, solved by CalculiX (ccx) (vt350#322). Plain python3 (stdlib); no FreeCAD.

The frame comes from a part index (<model>.parts.json, platform/freecad/part_index.py), not from the model file:
  - BARS: each part whose label names a profile ("2020 ...", "4040 (1)003") is a straight beam along its bounding box's
    long axis, through the box's centre. Its cross-section is the profile's (area, two bending inertias, torsion), from
    the printer's data; for an oblong profile (2040) the wide side is the box's wider cross dimension. A bar whose box
    doesn't match its profile's size is an error (a mislabelled or rotated part), not a guess.
  - JOINTS: two bars whose boxes touch (within TOUCH) are joined. A link runs from a node on one centre line to a node
    on the other at their closest points (a corner joint's link is offset by half the widths, as the real joint is).
    The link's stiffness is the JOINT STYLE: "rigid", or a rotational spring k_rot (N mm/rad) for a bolted joint.
  - Each bar is cut into elements no longer than MAX_ELEM, so the first modes come out right.

CalculiX element U1 (a linear beam with a general section, ccx >= 2.20); units mm, N, tonne, s (so MPa, t/mm^3).

    from frame import bars_from_index, joints, Mesh, deck, read_dat
"""
import math
import os
import re
import subprocess

TOUCH = 0.6                 # mm: boxes this close count as touching (index boxes are rounded; slots leave gaps)
MAX_ELEM = 25.0             # mm
AXES = "XYZ"


class FrameError(ValueError):
    pass


class Bar:
    """A straight bar: axis 0/1/2, from lo to hi along it, its centre line at c (the other two coordinates)."""

    def __init__(self, name, label, profile, axis, lo, hi, c, wide):
        self.name, self.label, self.profile = name, label, profile
        self.axis, self.lo, self.hi, self.c, self.wide = axis, lo, hi, c, wide     # c: {axis index: coordinate}
        self.half = {}                                                              # {cross axis: half width}

    def point(self, t):
        p = [0.0, 0.0, 0.0]
        p[self.axis] = t
        for k, v in self.c.items():
            p[k] = v
        return tuple(p)

    def __repr__(self):
        return f"Bar({self.label!r}, {self.profile}, {AXES[self.axis]} {self.lo:g}..{self.hi:g})"


def bars_from_index(index, profiles, select=None):
    """index: a parsed parts.json. profiles: {"2040": {"w": 40, "h": 20, ...}} (w >= h). select(part) -> bool narrows
    the parts (default: every part whose label starts with a profile's name). -> [Bar]"""
    pat = re.compile(r"^(" + "|".join(sorted(map(re.escape, profiles), key=len, reverse=True)) + r")\b")
    out = []
    for p in index["parts"]:
        m = pat.match(p["label"])
        if not m or (select and not select(p)):
            continue
        prof = profiles[m.group(1)]
        b = p["bbox"]
        lo = [b["xmin"], b["ymin"], b["zmin"]]
        hi = [b["xmax"], b["ymax"], b["zmax"]]
        size = [h - l for l, h in zip(lo, hi)]
        axis = max(range(3), key=lambda k: size[k])
        cross = [k for k in range(3) if k != axis]
        want = sorted([prof["w"], prof["h"]], reverse=True)
        got = sorted((size[k] for k in cross), reverse=True)
        if any(abs(g - w) > TOUCH for g, w in zip(got, want)) or size[axis] < want[0]:
            raise FrameError(f"{p['label']!r}: box {[round(s, 2) for s in size]} isn't a {m.group(1)} bar")
        wide = None if abs(want[0] - want[1]) < 1e-9 else max(cross, key=lambda k: size[k])
        bar = Bar(p["name"], p["label"], m.group(1), axis, lo[axis], hi[axis],
                  {k: (lo[k] + hi[k]) / 2 for k in cross}, wide)
        bar.half = {k: (want[0] if k == wide else want[1]) / 2 for k in cross}
        out.append(bar)
    return out


def _box(bar):
    lo, hi = [0.0] * 3, [0.0] * 3
    lo[bar.axis], hi[bar.axis] = bar.lo, bar.hi
    for k, v in bar.c.items():
        lo[k], hi[k] = v - bar.half[k], v + bar.half[k]
    return lo, hi


def _gap(a, b):
    """Largest gap between two bars' boxes over the three axes (<= 0: they overlap on every axis)."""
    (la, ha), (lb, hb) = _box(a), _box(b)
    return max(max(lb[k] - ha[k], la[k] - hb[k]) for k in range(3))


def joints(bars, touch=TOUCH):
    """-> [(i, t_i, j, t_j)]: bar i at t_i (along its axis) joins bar j at t_j. Crossing or end-on bars join once at
    their closest points; parallel bars side by side join at both ends of their overlap."""
    out = []
    for i, a in enumerate(bars):
        for j in range(i + 1, len(bars)):
            b = bars[j]
            if _gap(a, b) > touch:
                continue
            if a.axis != b.axis:
                ta = min(max(b.c[a.axis], a.lo), a.hi)
                tb = min(max(a.c[b.axis], b.lo), b.hi)
                out.append((i, ta, j, tb))
            else:
                lo, hi = max(a.lo, b.lo), min(a.hi, b.hi)
                if hi - lo > touch:
                    out += [(i, lo, j, lo), (i, hi, j, hi)]
                else:                                  # end to end, in line
                    t = (lo + hi) / 2
                    out.append((i, t, j, t))
    return out


class Mesh:
    """Nodes and elements: each bar cut at its ends, its joints and any extra stations (load points, supports)."""

    def __init__(self, bars, jts, stations=(), max_elem=MAX_ELEM):
        """stations: [(bar index, t)] that must be nodes."""
        self.bars, self.nodes, self.elems, self.links = bars, [], [], []
        self._at = {}
        for i, ti, j, tj in jts:                       # centre lines that meet: one node, no link
            if math.dist(bars[i].point(ti), bars[j].point(tj)) < 1e-6:
                self._at[(j, round(tj, 6))] = self.node(i, ti)
        cuts = {i: {b.lo, b.hi} for i, b in enumerate(bars)}
        for i, ti, j, tj in jts:
            cuts[i].add(ti); cuts[j].add(tj)
        for i, t in stations:
            cuts[i].add(t)
        for i, b in enumerate(bars):
            ts = sorted(cuts[i])
            prev = self.node(i, ts[0])
            for t0, t1 in zip(ts, ts[1:]):
                n = max(1, math.ceil((t1 - t0) / max_elem - 1e-9))
                for s in range(1, n + 1):
                    cur = self.node(i, t0 + (t1 - t0) * s / n if s < n else t1)
                    self.elems.append((prev, cur, i))
                    prev = cur
        for i, ti, j, tj in jts:
            a, b = self.node(i, ti), self.node(j, tj)
            if a != b:
                self.links.append((a, b, (i, j)))

    def node(self, i, t):
        key = (i, round(t, 6))
        if key not in self._at:
            self.nodes.append(self.bars[i].point(t))
            self._at[key] = len(self.nodes)            # ccx numbers from 1
        return self._at[key]

    def at(self, i, t):
        """The node of bar i at t (it must be a station)."""
        return self._at[(i, round(t, 6))]

    def nearest(self, p):
        return min(range(1, len(self.nodes) + 1),
                   key=lambda n: sum((a - b) ** 2 for a, b in zip(self.nodes[n - 1], p)))


def groups(n_bars, jts):
    """The bars in connected groups (a frame should be one): -> [[bar index]], largest first."""
    up = list(range(n_bars))
    def root(i):
        while up[i] != i:
            up[i] = up[up[i]]; i = up[i]
        return i
    for i, _, j, _ in jts:
        up[root(i)] = root(j)
    out = {}
    for i in range(n_bars):
        out.setdefault(root(i), []).append(i)
    return sorted(out.values(), key=len, reverse=True)


def _normal1(bar):
    """The section's local direction 1 (ccx: the first normal): across the wide side for an oblong bar."""
    k = bar.wide if bar.wide is not None else min(bar.c)
    v = [0.0, 0.0, 0.0]
    v[k] = 1.0
    return v


def _link_length(mesh, a, b):
    return math.dist(mesh.nodes[a - 1], mesh.nodes[b - 1])


def deck(mesh, profiles, material, style, case):
    """-> the .inp text. material: {"E", "nu", "rho"} (MPa, -, t/mm^3). style: {"name", "k_rot": N mm/rad or None}.
    case: {"name", "kind": "static"|"frequency", "fixed": [node], "loads": [(node, dof 1..6, N or N mm)],
           "masses": [(node, t)], "accel": (ax, ay, az) mm/s^2, the masses' acceleration (static: each mass loads
           its node with -m a), "gravity": True (the bars' own weight), "modes": n (frequency)}."""
    E, nu, rho = material["E"], material["nu"], material["rho"]
    G = E / (2 * (1 + nu))
    L = ["*HEADING", f"frame {case['name']} joint style {style['name']}", "*NODE, NSET=NALL"]
    L += [f"{n}, {x:.4f}, {y:.4f}, {z:.4f}" for n, (x, y, z) in enumerate(mesh.nodes, 1)]
    L += ["*USER ELEMENT, TYPE=U1, INTEGRATION POINTS=2, MAXDOF=6, NODES=2"]
    e = 0
    sets = {}
    for a, b, i in mesh.elems:
        e += 1
        sets.setdefault(f"B{i}", []).append((e, a, b))
    links = {"LINKS_Z": [], "LINKS_XY": []}          # direction 1 must not lie along the link
    for a, b, pair in mesh.links:
        e += 1
        d = [q - p for p, q in zip(mesh.nodes[a - 1], mesh.nodes[b - 1])]
        links["LINKS_Z" if abs(d[2]) > 0.7 * math.hypot(*d) else "LINKS_XY"].append((e, a, b))
    links = {k: v for k, v in links.items() if v}
    for name, rows in list(sets.items()) + list(links.items()):
        L.append(f"*ELEMENT, TYPE=U1, ELSET={name}")
        L += [f"{n}, {a}, {b}" for n, a, b in rows]
    L += ["*ELSET, ELSET=EBARS"] + [", ".join(sets)]
    masses = case.get("masses", [])
    for k, (node, m) in enumerate(masses):
        e += 1
        L += [f"*ELEMENT, TYPE=MASS, ELSET=M{k}", f"{e}, {node}"]
    L += ["*MATERIAL, NAME=FRAME", "*ELASTIC", f"{E:g}, {nu:g}", "*DENSITY", f"{rho:g}"]
    stiff = max(max(p["A"], p["Iw"], p["Ih"], p["J"]) for p in profiles.values())
    L += ["*MATERIAL, NAME=LINK", "*ELASTIC", f"{E:g}, {nu:g}", "*DENSITY", "1e-15"]
    for name, rows in sets.items():
        bar = mesh.bars[int(name[1:])]
        p = profiles[bar.profile]
        # direction 1 is across the wide side: bending that deflects along it uses Iw
        L += [f"*BEAM SECTION, ELSET={name}, MATERIAL=FRAME, SECTION=GENERAL",
              f"{p['A']:g}, {p['Iw']:g}, 0., {p['Ih']:g}, {p['J']:g}", ", ".join(f"{v:g}" for v in _normal1(bar))]
    if links:
        # axial and shear stiff; bending and torsion from the joint style (a short beam of length l bends by
        # M l / (E I): I = k_rot l / E gives the spring k_rot)
        A = 100 * stiff
        lmean = sum(_link_length(mesh, a, b) for rows in links.values() for _, a, b in rows) / sum(map(len, links.values()))
        I, J = (style["k_rot"] * lmean / E, style["k_rot"] * lmean / G) if style.get("k_rot") else (100 * stiff,) * 2
        for name, normal in (("LINKS_Z", "1, 0, 0"), ("LINKS_XY", "0, 0, 1")):
            if name in links:
                L += [f"*BEAM SECTION, ELSET={name}, MATERIAL=LINK, SECTION=GENERAL", f"{A:g}, {I:g}, 0., {I:g}, {J:g}",
                      normal]
    for k, (node, m) in enumerate(masses):
        L += [f"*MASS, ELSET=M{k}", f"{m:g}"]
    L += ["*BOUNDARY"] + [f"{n}, 1, 6" for n in case["fixed"]]
    L += ["*STEP"]
    if case["kind"] == "static":
        L += ["*STATIC"]
        loads = list(case.get("loads", []))
        ax = case.get("accel")
        if ax:                                          # d'Alembert: a mass m accelerating at a feels -m a
            for node, m in masses:
                loads += [(node, d + 1, -m * ax[d]) for d in range(3) if ax[d]]
        if loads:
            L += ["*CLOAD"] + [f"{n}, {d}, {v:.6g}" for n, d, v in loads]
        if case.get("gravity"):
            L += ["*DLOAD", "EBARS, GRAV, 9810., 0., 0., -1."]
        L += ["*NODE PRINT, NSET=NALL", "U"]
    else:
        L += ["*FREQUENCY", f"{case.get('modes', 6)}"]
    L += ["*END STEP"]
    return "\n".join(x for x in L if x != "") + "\n"


def read_dat(text):
    """ccx .dat -> {"u": {node: (ux, uy, uz, rx, ry, rz)}, "freq_hz": [..]}."""
    u, freq, mode = {}, [], None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("displacements"):
            mode = "u"; continue
        if "E I G E N V A L U E   O U T P U T" in s:
            mode = "eig"; continue
        if "P A R T I C I P A T I O N" in s or "E F F E C T I V E" in s:
            mode = None; continue
        f = s.split()
        if mode == "u" and len(f) >= 4:
            try:
                u[int(f[0])] = tuple(float(x) for x in f[1:])
            except ValueError:
                mode = None
        elif mode == "eig" and len(f) == 5:
            try:
                int(f[0]); freq.append(float(f[3]))           # mode, eigenvalue, rad/s, Hz, imaginary
            except ValueError:
                pass
    return {"u": u, "freq_hz": freq}


def run(inp, workdir, ccx, name="frame"):
    """Write inp to workdir/name.inp, run ccx there, -> read_dat of the result. A ccx error raises FrameError."""
    os.makedirs(workdir, exist_ok=True)
    with open(os.path.join(workdir, name + ".inp"), "w") as f:
        f.write(inp)
    r = subprocess.run([ccx, "-i", name], cwd=workdir, capture_output=True, text=True, timeout=600)
    with open(os.path.join(workdir, name + ".log"), "w") as f:
        f.write(r.stdout + r.stderr)
    errs = [l.strip() for l in (r.stdout + r.stderr).splitlines() if "*ERROR" in l]
    dat = os.path.join(workdir, name + ".dat")
    if r.returncode or errs or not os.path.isfile(dat):
        raise FrameError(f"ccx {name}: rc {r.returncode}; {errs[:3] or 'no .dat'} (log {workdir}/{name}.log)")
    with open(dat) as f:
        return read_dat(f.read())
