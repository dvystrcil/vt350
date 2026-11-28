"""The dancer's section drawing, step 2 of 2 (owner 2026-11-27: "a cutaway of the wheel in the channel", drawn like a
classic mechanical drawing). Plain python3, no FreeCAD:

    python3 cad/render/dancer_section.py <sections.json> <out.svg> [--png out.png]

<sections.json> is step 1's output (cad/render/dancer_section_fc.py): every part's cut outline in three planes through
one tool's sheave. One A3 sheet (420 x 297, mm), third-angle projection, all three views at one scale:
  C-C  front view, the sheave's mid-plane (X right, Z up): spokes, hub, 625 bearing, axle; the cable as phantom lines;
  B-B  above it, the plan at the axle's height (X right, Y up): the stack's rails, post and tie rods, both sheaves;
  A-A  to the right, the side view through the axles (Y right, Z up): the sheaves side by side in their channels.
Drawing conventions (ISO 128 / ISO 6410 style):
  - cut faces hatched at 45 deg; parts that touch get a different angle or spacing; steel denser;
  - a shaft cut along its length (the axle in A-A and B-B) is not hatched;
  - a rolling bearing in section: its outline with a diagonal cross (the simplified symbol);
  - centre lines dash-dot (thin), the cable dash-dot-dot (phantom), cutting planes thick dash-dot with arrows;
  - A-A and C-C are cropped to the drawn tool's wheel, with break lines where the stack runs on.
"""
import json, math, os, subprocess, sys

SHEET_W, SHEET_H, MARGIN = 420.0, 297.0, 10.0
SCALE = 1.15                           # sheet mm per model mm
Z_CROP = 60.0                          # A-A and C-C show the tool's axle Z +- this
INK = "#1a1a1a"
THICK, THIN = 0.5, 0.18                # ISO 128 line widths (wide / narrow), mm
FONT = "font-family='DejaVu Sans, Arial, sans-serif'"

# hatch per part: (angle deg, spacing mm on the sheet)
HATCH = {"stack": (45, 2.4), "sheave0": (-45, 1.8), "sheave1": (45, 1.4), "sheave2": (-45, 1.4),
         "rod": (45, 0.8), "axle": (-45, 0.7)}
CUT_LENGTHWISE = {"A": ("axle",), "B": ("axle",), "C": ()}      # shafts not hatched in these views


def hatch_of(part):
    """(pattern key, (angle, spacing)); a sheave's second half (sheaveNb) mirrors its first's angle: they touch"""
    for k, v in HATCH.items():
        if part.startswith(k):
            if k.startswith("sheave") and part.endswith("b"):
                return part, (-v[0], v[1])
            return k if k in ("rod", "axle") else part, v
    return part, (45, 2.0)


class Sheet:
    def __init__(self):
        self.defs, self.body = [], []
        self.patterns = set()

    def pattern(self, key, angle, gap):
        pid = f"h_{key}"
        if pid not in self.patterns:
            self.patterns.add(pid)
            self.defs.append(f"<pattern id='{pid}' patternUnits='userSpaceOnUse' width='{gap}' height='{gap}' "
                             f"patternTransform='rotate({angle})'><line x1='0' y1='0' x2='0' y2='{gap}' "
                             f"stroke='{INK}' stroke-width='{THIN * 0.8:.3f}'/></pattern>")
        return pid

    def add(self, s): self.body.append(s)

    def svg(self):
        return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{SHEET_W}mm' height='{SHEET_H}mm' "
                f"viewBox='0 0 {SHEET_W} {SHEET_H}'>\n<defs>\n" + "\n".join(self.defs) + "\n</defs>\n"
                f"<rect width='{SHEET_W}' height='{SHEET_H}' fill='white'/>\n" + "\n".join(self.body) + "\n</svg>\n")


class View:
    """one view: model (u, v) -> sheet (x, y), u right, v up, cropped to [u0, u1] x [v0, v1]"""
    def __init__(self, sheet, name, u0, u1, v0, v1, x, y):
        self.s, self.name = sheet, name
        self.u0, self.u1, self.v0, self.v1, self.x, self.y = u0, u1, v0, v1, x, y
        self.clip = f"clip_{name}"
        sheet.defs.append(f"<clipPath id='{self.clip}'><rect x='{x:.3f}' y='{y:.3f}' "
                          f"width='{(u1 - u0) * SCALE:.3f}' height='{(v1 - v0) * SCALE:.3f}'/></clipPath>")

    def P(self, u, v): return (self.x + (u - self.u0) * SCALE, self.y + (self.v1 - v) * SCALE)
    def w(self): return (self.u1 - self.u0) * SCALE
    def h(self): return (self.v1 - self.v0) * SCALE

    def path(self, loops):
        d = []
        for L in loops:
            pts = [self.P(u, v) for u, v in L]
            d.append("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + " Z")
        return " ".join(d)

    def add(self, s, clip=True):
        self.s.add(f"<g clip-path='url(#{self.clip})'>{s}</g>" if clip else s)

    def line(self, a, b, width=THIN, dash=None, clip=True):
        (x1, y1), (x2, y2) = self.P(*a), self.P(*b)
        da = f" stroke-dasharray='{dash}'" if dash else ""
        self.add(f"<line x1='{x1:.3f}' y1='{y1:.3f}' x2='{x2:.3f}' y2='{y2:.3f}' stroke='{INK}' "
                 f"stroke-width='{width}'{da}/>", clip)

    def circle(self, c, r, width=THIN, dash=None, clip=True):
        x, y = self.P(*c); da = f" stroke-dasharray='{dash}'" if dash else ""
        self.add(f"<circle cx='{x:.3f}' cy='{y:.3f}' r='{r * SCALE:.3f}' fill='none' stroke='{INK}' "
                 f"stroke-width='{width}'{da}/>", clip)

    def arc(self, c, r, a0, a1, width=THIN, dash=None):
        pts = [(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
               for a in [a0 + (a1 - a0) * i / 60 for i in range(61)]]
        da = f" stroke-dasharray='{dash}'" if dash else ""
        d = "M" + " L".join("%.3f,%.3f" % self.P(*p) for p in pts)
        self.add(f"<path d='{d}' fill='none' stroke='{INK}' stroke-width='{width}'{da}/>")


CENTRE = "6,1,0.6,1"           # dash-dot, thin (ISO 128 type 04)
PHANTOM = "6,1,0.6,1,0.6,1"    # dash-dot-dot, thin (type 05)
PLANE = "8,1.5,1,1.5"          # cutting plane, wide ends


def draw_parts(view, cuts, section):
    """hatched cut faces, then their outlines"""
    for c in cuts:
        part, kind, loops = c["part"], c["kind"], c["loops"]
        d = view.path(loops)
        if kind == "bearing" and section == "C":            # seen along its axis: the rings, the ball circle
            view.add(f"<path d='{d}' fill='white' fill-rule='evenodd' stroke='{INK}' stroke-width='{THICK}'/>")
            us = [p[0] for L in loops for p in L]; vs = [p[1] for L in loops for p in L]
            c = ((min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2)
            ro = (max(us) - min(us)) / 2; ri = min(math.hypot(p[0] - c[0], p[1] - c[1]) for L in loops for p in L)
            view.circle(c, (ro + ri) / 2, THIN, CENTRE)
            continue
        if kind == "bearing":
            view.add(f"<path d='{d}' fill='white' fill-rule='evenodd' stroke='{INK}' stroke-width='{THICK}'/>")
            for L in loops:                           # the simplified symbol: a diagonal cross in each ring section
                us, vs = [p[0] for p in L], [p[1] for p in L]
                a, b = (min(us), min(vs)), (max(us), max(vs))
                view.line(a, b, THIN); view.line((a[0], b[1]), (b[0], a[1]), THIN)
            continue
        lengthwise = any(part.startswith(k) for k in CUT_LENGTHWISE[section])
        if lengthwise:
            fill = "white"
        else:
            key, (ang, gap) = hatch_of(part)
            fill = f"url(#{view.s.pattern(key, ang, gap)})"
        view.add(f"<path d='{d}' fill='{fill}' fill-rule='evenodd' stroke='{INK}' stroke-width='{THICK}' "
                 f"stroke-linejoin='round'/>")


def text(sheet, x, y, s, size=3.5, anchor="middle", weight="normal", rotate=None):
    rot = f" transform='rotate({rotate} {x:.3f} {y:.3f})'" if rotate is not None else ""
    sheet.add(f"<text x='{x:.3f}' y='{y:.3f}' font-size='{size}' text-anchor='{anchor}' font-weight='{weight}' "
              f"fill='{INK}' {FONT}{rot}>{s}</text>")


def arrow(sheet, tip, toward, size=2.2):
    """a filled arrowhead at `tip` (sheet mm) pointing from `toward` to tip"""
    dx, dy = tip[0] - toward[0], tip[1] - toward[1]; n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n; px, py = -uy, ux
    a = (tip[0] - ux * size + px * size * 0.3, tip[1] - uy * size + py * size * 0.3)
    b = (tip[0] - ux * size - px * size * 0.3, tip[1] - uy * size - py * size * 0.3)
    sheet.add(f"<path d='M{tip[0]:.3f},{tip[1]:.3f} L{a[0]:.3f},{a[1]:.3f} L{b[0]:.3f},{b[1]:.3f} Z' fill='{INK}'/>")


def dim(view, a, b, off, label, horizontal=True):
    """a linear dimension between model points a and b, its line `off` sheet-mm away (+ = up / right)"""
    s = view.s
    pa, pb = view.P(*a), view.P(*b)
    if horizontal:
        y = min(pa[1], pb[1]) - off if off > 0 else max(pa[1], pb[1]) - off
        for p in (pa, pb):
            s.add(f"<line x1='{p[0]:.3f}' y1='{p[1] - (1 if off > 0 else -1):.3f}' x2='{p[0]:.3f}' "
                  f"y2='{y - (1.5 if off > 0 else -1.5):.3f}' stroke='{INK}' stroke-width='{THIN}'/>")
        x1, x2 = sorted((pa[0], pb[0]))
        inside = x2 - x1 > 9
        if inside:
            s.add(f"<line x1='{x1:.3f}' y1='{y:.3f}' x2='{x2:.3f}' y2='{y:.3f}' stroke='{INK}' stroke-width='{THIN}'/>")
            arrow(s, (x1, y), (x2, y)); arrow(s, (x2, y), (x1, y))
            text(s, (x1 + x2) / 2, y - 1.0, label, 3.0)
        else:                                     # small: arrows outside, pointing in
            s.add(f"<line x1='{x1 - 7:.3f}' y1='{y:.3f}' x2='{x2 + 7:.3f}' y2='{y:.3f}' stroke='{INK}' stroke-width='{THIN}'/>")
            arrow(s, (x1, y), (x1 - 5, y)); arrow(s, (x2, y), (x2 + 5, y))
            text(s, x2 + 8, y + 1.0, label, 3.0, anchor="start")
    else:
        x = max(pa[0], pb[0]) + off if off > 0 else min(pa[0], pb[0]) + off
        for p in (pa, pb):
            s.add(f"<line x1='{p[0] + (1 if off > 0 else -1):.3f}' y1='{p[1]:.3f}' x2='{x + (1.5 if off > 0 else -1.5):.3f}' "
                  f"y2='{p[1]:.3f}' stroke='{INK}' stroke-width='{THIN}'/>")
        y1, y2 = sorted((pa[1], pb[1]))
        inside = y2 - y1 > 9
        if inside:
            s.add(f"<line x1='{x:.3f}' y1='{y1:.3f}' x2='{x:.3f}' y2='{y2:.3f}' stroke='{INK}' stroke-width='{THIN}'/>")
            arrow(s, (x, y1), (x, y2)); arrow(s, (x, y2), (x, y1))
            text(s, x - 1.0, (y1 + y2) / 2, label, 3.0, rotate=-90)
        else:
            s.add(f"<line x1='{x:.3f}' y1='{y1 - 7:.3f}' x2='{x:.3f}' y2='{y2 + 7:.3f}' stroke='{INK}' stroke-width='{THIN}'/>")
            arrow(s, (x, y1), (x, y1 - 5)); arrow(s, (x, y2), (x, y2 + 5))
            text(s, x - 1.0, y2 + 9, label, 3.0, anchor="end", rotate=-90)


def leader(view, at, to, label):
    """a leader from a model point to a label at sheet offset `to` (dx, dy)"""
    s = view.s; p = view.P(*at); q = (p[0] + to[0], p[1] + to[1])
    s.add(f"<line x1='{p[0]:.3f}' y1='{p[1]:.3f}' x2='{q[0]:.3f}' y2='{q[1]:.3f}' stroke='{INK}' stroke-width='{THIN}'/>")
    s.add(f"<circle cx='{p[0]:.3f}' cy='{p[1]:.3f}' r='0.45' fill='{INK}'/>")
    right = to[0] >= 0
    end = q[0] + (4 if right else -4)
    s.add(f"<line x1='{q[0]:.3f}' y1='{q[1]:.3f}' x2='{end:.3f}' y2='{q[1]:.3f}' stroke='{INK}' stroke-width='{THIN}'/>")
    text(s, end + (1 if right else -1), q[1] + 1.0, label, 3.0, anchor="start" if right else "end")


def plane_mark(view, a, b, letter, look):
    plane_path(view, [a, b], letter, look)


def plane_path(view, pts, letter, look):
    """a cutting plane through model points pts (a stepped plane has bends): thin dash-dot along it, thick at both ends
    and at every bend (ISO 128), arrows `look` (dx, dy, sheet) at the ends, each lettered"""
    s = view.s; P = [view.P(*p) for p in pts]
    d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in P)
    s.add(f"<path d='{d}' fill='none' stroke='{INK}' stroke-width='{THIN}' stroke-dasharray='{CENTRE}'/>")

    def unit(p, q):
        n = math.hypot(q[0] - p[0], q[1] - p[1]) or 1.0
        return (q[0] - p[0]) / n, (q[1] - p[1]) / n

    def thick(p, q):
        s.add(f"<line x1='{p[0]:.3f}' y1='{p[1]:.3f}' x2='{q[0]:.3f}' y2='{q[1]:.3f}' stroke='{INK}' "
              f"stroke-width='{THICK * 1.4}'/>")
    for i in range(1, len(P) - 1):                    # a bend: a short thick L along both legs
        for j in (i - 1, i + 1):
            ux, uy = unit(P[i], P[j]); thick(P[i], (P[i][0] + ux * 3, P[i][1] + uy * 3))
    for p, q in ((P[0], P[1]), (P[-1], P[-2])):
        ux, uy = unit(p, q)
        thick(p, (p[0] + ux * 6, p[1] + uy * 6))
        t = (p[0] + look[0] * 7, p[1] + look[1] * 7)
        s.add(f"<line x1='{p[0]:.3f}' y1='{p[1]:.3f}' x2='{t[0]:.3f}' y2='{t[1]:.3f}' stroke='{INK}' stroke-width='{THIN}'/>")
        arrow(s, t, p, 2.5)
        text(s, t[0] + look[0] * 3.5 - ux * 2.5, t[1] + look[1] * 3.5 + 1.5 - uy * 2.5, letter, 5, weight="bold")


def break_line(view, v, rng):
    """a freehand-style break across the view at model height v"""
    s = view.s
    xs = [view.x + i * view.w() / 24 for i in range(25)]
    y = view.P(rng[0], v)[1]
    pts = " L".join(f"{x:.3f},{y + (0.9 if i % 2 else -0.9):.3f}" for i, x in enumerate(xs))
    s.add(f"<path d='M{pts}' fill='none' stroke='{INK}' stroke-width='{THIN}'/>")


def title(view, letter, sub):
    x = view.x + view.w() / 2; y = view.y + view.h() + 9
    text(view.s, x, y, f"SECTION {letter}-{letter}", 5, weight="bold")
    text(view.s, x, y + 5, sub, 3.0)


def drawing(d):
    k = d["k"]; t = str(d["tool"]); cx = d["cx"]
    y1, z1 = d["sheaves"][t]
    S = Sheet()
    sec = d["sections"]

    def ext(name, ui):
        vals = [p[ui] for c in sec[name] for L in c["loops"] for p in L]
        return min(vals), max(vals)
    # model extents
    bu, bv = ext("B", 0), ext("B", 1)
    cu = ext("C", 0)
    au = ext("A", 0)
    zc0, zc1 = z1 - Z_CROP, z1 + Z_CROP
    pad = 4.0
    Cw, Ch = (cu[1] - cu[0] + 2 * pad) * SCALE, (zc1 - zc0) * SCALE
    Bh = (bv[1] - bv[0] + 2 * pad) * SCALE
    Aw = (au[1] - au[0] + 2 * pad) * SCALE
    x0 = MARGIN + 22
    yB = MARGIN + 12
    yC = yB + Bh + 34
    vB = View(S, "B", min(bu[0], cu[0]) - pad, max(bu[1], cu[1]) + pad, bv[0] - pad, bv[1] + pad, x0, yB)
    vC = View(S, "C", vB.u0, vB.u1, zc0, zc1, x0, yC)
    vA = View(S, "A", au[0] - pad, au[1] + pad, zc0, zc1, x0 + vC.w() + 46, yC)

    # sheet frame
    S.add(f"<rect x='{MARGIN / 2}' y='{MARGIN / 2}' width='{SHEET_W - MARGIN}' height='{SHEET_H - MARGIN}' "
          f"fill='none' stroke='{INK}' stroke-width='{THICK}'/>")

    for v, name in ((vC, "C"), (vB, "B"), (vA, "A")):
        draw_parts(v, sec[name], name)

    # --- C-C: centre lines, pitch circle, the cable (phantom), dims
    R, RP = k["SHEAVE_R"], d["RP"]
    vC.line((cx - R - 6, z1), (cx + R + 6, z1), THIN, CENTRE)
    vC.line((cx, z1 - R - 6), (cx, z1 + R + 6), THIN, CENTRE)
    vC.circle((cx, z1), R, THICK * 0.8)                  # the flanges' rim, behind the cut (a visible edge)
    vC.circle((cx, z1), RP, THIN, CENTRE)
    for r in (RP - 5.1, RP + 5.1):                         # the bundle: two Ø5.1 lines side by side in the groove
        vC.arc((cx, z1), r, 180, 360, THIN, PHANTOM)
    for side in (-1, 1):
        for r in (RP - 5.1, RP + 5.1):
            vC.line((cx + side * r, z1), (cx + side * r, zc1), THIN, PHANTOM)
    dim(vC, (cx - R, z1 + R), (cx + R, z1 + R), 14, f"Ø{2 * R:.1f}")
    dim(vC, (cx - k["HUB_R"], z1 - k["HUB_R"]), (cx + k["HUB_R"], z1 - k["HUB_R"]), -10, f"Ø{2 * k['HUB_R']:.0f}")
    a = math.radians(-35)
    leader(vC, (cx + RP * math.cos(a), z1 + RP * math.sin(a)), (24, 14), f"R{RP:.1f} cable pitch")
    a = math.radians(-145)
    leader(vC, (cx + k["GROOVE_IN"] * math.cos(a), z1 + k["GROOVE_IN"] * math.sin(a)), (-24, 16),
           f"R{k['GROOVE_IN']:.1f} groove")
    a = math.radians(60)
    rw = k["GROOVE_IN"] - k["RIM_WALL"] / 2
    leader(vC, (cx + rw * math.cos(a), z1 + rw * math.sin(a)), (30, -22), f"rim wall {k['RIM_WALL']}")
    a = math.radians(115)
    leader(vC, (cx + R * math.cos(a), z1 + R * math.sin(a)), (-26, -10), "flange (beyond the cut)")
    bo, bw = k["BEARING"][0], k["BEARING"][2]
    leader(vC, (cx + bo, z1), (30, -24), f"625-2RS Ø{2 * bo:.0f}×Ø{2 * k['BEARING'][1]:.0f}×{bw:.0f}")
    break_line(vC, zc0, (vC.u0, vC.u1)); break_line(vC, zc1, (vC.u0, vC.u1))
    plane_mark(vC, (cx, zc1 - 1), (cx, zc0 + 1), "A", (1, 0))
    plane_mark(vC, (vC.u0 + 1, z1), (vC.u1 - 1, z1), "B", (0, -1))
    yc = d.get("c_plane", y1)
    where = f"{yc - y1:g} past the split, in half 2" if abs(yc - y1) > 1e-6 else "the sheave's mid-plane"
    title(vC, "C", f"Y {yc:.1f}, {where} (tool T{t}); cable dash-dot-dot")

    # --- B-B: plan at the axle's height
    vB.line((cx, vB.v0 + 1), (cx, vB.v1 - 1), THIN, CENTRE)
    for tt, (yy, zz) in d["sheaves"].items():
        vB.line((cx - R - 4, yy), (cx + R + 4, yy), THIN, CENTRE)
    pl = d["plates"]
    dim(vB, (cx + R + 6, d["sheaves"]["0"][0]), (cx + R + 6, d["sheaves"]["1"][0]), 6,
        f"pitch {k['PITCH']:.0f}", horizontal=False)
    dim(vB, (d["post_x"] - k["POST_W"] / 2, pl[-1] + 2), (d["post_x"] + k["POST_W"] / 2, pl[-1] + 2), 7,
        f"post {k['POST_W']:.0f}")
    rods = [c for c in sec["B"] if c["kind"] == "steel"]
    if rods:
        L = rods[0]["loops"][0]; ru = [p[0] for p in L]; rv = [p[1] for p in L]
        leader(vB, (max(ru), (min(rv) + max(rv)) / 2), (10, 14),
               f"tie rod Ø{2 * k['ROD_R']:.0f} in Ø{2 * k['ROD_HOLE']:.1f}")
    plane_mark(vB, (cx, vB.v1 - 1), (cx, vB.v0 + 1), "A", (1, 0))
    plane_mark(vB, (vB.u0 + 1, d.get("c_plane", y1)), (vB.u1 - 1, d.get("c_plane", y1)), "C", (0, -1))
    steps = ", ".join(f"T{tt} Z {zz:.1f}" for tt, (yy, zz) in sorted(d["sheaves"].items(), key=lambda kv: kv[1][0]))
    title(vB, "B", f"stepped: each sheave at its own axle ({steps})")

    # --- A-A: the sheaves side by side in their channels
    for tt, (yy, zz) in d["sheaves"].items():
        vA.line((yy - 7, zz), (yy + 7, zz), THIN, CENTRE)                        # axle axis (along Y)
        vA.line((yy, zz - R - 3), (yy, zz + R + 3), THIN, CENTRE)                # sheave mid-plane
        for r in (RP - 2.55, RP + 2.55):                                       # the bundle under the wheel, in section
            vA.circle((yy, zz - r), 2.55, THIN, PHANTOM)
    yb = d["sheaves"][t][0]
    dim(vA, (pl[1], z1 + R + 2), (pl[1] + k["PLATE_T"], z1 + R + 2), 6, f"{k['PLATE_T']}")
    dim(vA, (yb - k["SHEAVE_T"] / 2, z1 + R - 3), (yb + k["SHEAVE_T"] / 2, z1 + R - 3), 20, f"{k['SHEAVE_T']:.0f}")
    dim(vA, (yb - k["AXLE_L"] / 2, z1 - 2.5), (yb + k["AXLE_L"] / 2, z1 - 2.5), -30, f"axle {k['AXLE_L']}")
    dim(vA, (yb + 6, z1 - k["BEARING"][0]), (yb + 6, z1 + k["BEARING"][0]), 20, f"Ø{2 * k['BEARING'][0]:.0f}",
        horizontal=False)
    leader(vA, (yb - k["SHEAVE_T"] / 2 - k["PLATE_GAP"] / 2, z1 + 30), (-20, -12), f"gap {k['PLATE_GAP']}")
    root = f", root chamfers {k['GROOVE_ROOT']:g}" if k.get("GROOVE_ROOT") else ""
    leader(vA, (yb, z1 - RP - 2.55), (26, -40),
           f"cable groove {k['GROOVE_W']:g} wide, {R - k['GROOVE_IN']:.1f} deep{root}")
    z0 = min(zz for _, zz in d["sheaves"].values())
    leader(vA, (pl[0] + k["PLATE_T"] / 2 - k["GROOVE_D"] / 2, z0 - 3.5), (-16, -30),
           f"axle slot {k['SLOT_W']:g} wide, {k['GROOVE_D']:g} deep")
    break_line(vA, zc0, (vA.u0, vA.u1)); break_line(vA, zc1, (vA.u0, vA.u1))
    # B-B steps from one sheave's axle height to the next at the plate between them
    path = [(vA.u0 + 1, None)]
    for (ya, za), nxt in zip(sorted(d["sheaves"].values()), sorted(d["sheaves"].values())[1:] + [None]):
        path[-1] = (path[-1][0], za)
        if nxt:
            ystep = min(pl, key=lambda yp: abs(yp - (ya + nxt[0]) / 2))
            path += [(ystep, za), (ystep, None)]
    path.append((vA.u1 - 1, path[-1][1]))
    plane_path(vA, path, "B", (0, -1))
    plane_mark(vA, (d.get("c_plane", y1), zc1 - 1), (d.get("c_plane", y1), zc0 + 1), "C", (-1, 0))
    title(vA, "A", f"through the axles, X {cx:.1f}")

    # --- legend + title block
    lx, ly = vA.x + vA.w() + 34, yC + 6
    text(S, lx, ly, "Cut faces", 3.5, anchor="start", weight="bold")
    rows = [("stack", "stack (printed)"), ("sheave0a", "sheave T0, half 1 (printed)"), ("sheave0b", "sheave T0, half 2"),
            ("sheave1a", "sheave T1, half 1 (printed)"), ("sheave1b", "sheave T1, half 2"),
            ("rod", "steel rod"), ("axle", "axle, cut across (steel)")]
    for i, (key, lab) in enumerate(rows):
        hk, (ang, gap) = hatch_of(key)
        y = ly + 5 + i * 8
        S.add(f"<rect x='{lx:.1f}' y='{y:.1f}' width='10' height='5' fill='url(#{S.pattern(hk, ang, gap)})' "
              f"stroke='{INK}' stroke-width='{THIN}'/>")
        text(S, lx + 13, y + 4, lab, 3.0, anchor="start")
    y = ly + 5 + len(rows) * 8
    S.add(f"<rect x='{lx:.1f}' y='{y:.1f}' width='10' height='5' fill='white' stroke='{INK}' stroke-width='{THIN}'/>"
          f"<line x1='{lx:.1f}' y1='{y:.1f}' x2='{lx + 10:.1f}' y2='{y + 5:.1f}' stroke='{INK}' stroke-width='{THIN}'/>"
          f"<line x1='{lx:.1f}' y1='{y + 5:.1f}' x2='{lx + 10:.1f}' y2='{y:.1f}' stroke='{INK}' stroke-width='{THIN}'/>")
    text(S, lx + 13, y + 4, "625 bearing (simplified)", 3.0, anchor="start")
    y += 8
    S.add(f"<rect x='{lx:.1f}' y='{y:.1f}' width='10' height='5' fill='white' stroke='{INK}' stroke-width='{THIN}'/>")
    text(S, lx + 13, y + 4, "axle, cut lengthwise (not hatched)", 3.0, anchor="start")

    tw, th = 128.0, 34.0
    tx, ty = SHEET_W - MARGIN / 2 - tw, SHEET_H - MARGIN / 2 - th
    S.add(f"<rect x='{tx}' y='{ty}' width='{tw}' height='{th}' fill='white' stroke='{INK}' stroke-width='{THICK}'/>")
    for yy in (ty + 12, ty + 23):
        S.add(f"<line x1='{tx}' y1='{yy}' x2='{tx + tw}' y2='{yy}' stroke='{INK}' stroke-width='{THIN}'/>")
    S.add(f"<line x1='{tx + 66}' y1='{ty + 12}' x2='{tx + 66}' y2='{ty + th}' stroke='{INK}' stroke-width='{THIN}'/>")
    text(S, tx + 3, ty + 8, f"VT350 dancer: sheave T{t} in its stack", 5, anchor="start", weight="bold")
    text(S, tx + 3, ty + 19, "Sections A-A, B-B, C-C", 3.5, anchor="start")
    text(S, tx + 69, ty + 19, f"Scale {SCALE:g} : 1 (on A3)", 3.5, anchor="start")
    text(S, tx + 3, ty + 30, "lite-81 preview (vt350#327), mm", 3.5, anchor="start")
    text(S, tx + 69, ty + 30, "Third-angle projection", 3.5, anchor="start")
    return S.svg()


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    d = json.load(open(argv[0]))
    svg = drawing(d)
    open(argv[1], "w").write(svg)
    if "--png" in argv:
        png = argv[argv.index("--png") + 1]
        subprocess.run(["rsvg-convert", "-d", "200", "-p", "200", "-b", "white", "-o", png, argv[1]], check=True)
    print("dancer section:", argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
