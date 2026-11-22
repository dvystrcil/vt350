# GUI pass: vt350-lite-75 -> vt350-lite-76   (headless = dry run, never saves)   vt350#237
# The five printer steppers (A and B, the CoreXY pair; the three Z motors) render all black. The real ones are black
# with silver end caps (owner, 2026-11-18, #237: "if these are for the X Y Z steppers yes, silver end caps").
# Each motor body is one solid, so its caps can't take their own colour. This pass cuts each body across its axis at
# its two seams into front cap (shaft end), stator and rear cap, keeping the outer shape.
#  - Two source bodies: `_Stepper_stator` (A/B, 49 mm) and `Motor_Body` (Z, 40.6 mm). The other three motors are
#    App::Links to them (`_Stepper_stator001`, `Motor_Body001`, `Motor_Body002`).
#  - The seams are measured, not typed in: the stator stack is 42.2 mm across, the caps 42.0. Slicing along the axis
#    every 0.1 mm finds the 42.2 run, and each end snaps to the body's own planar face there.
#  - Each source body keeps its name, label and colour as the stator. Two new Part::Features beside it,
#    `<label> front cap` / `<label> rear cap`, take the same Placement, material and look. Each link to a body gets
#    two new links to its caps, with the link's own Placement, in the link's group, labelled the same way.
#  - cad/render/colours.json gives the caps the `brushed_aluminium` role (the Crossbow's silver, owner-chosen).
# Checks (refuses to save on any): 5 motor bodies, 2 sources, 3 links to them; along Z; each source's 42.2 run found and
# its ends on a planar face of the body; for every one of the 5 motors after: three pieces (each one solid, or one
# plus the tie-bolt ends the cut frees, < 1 % and inside it) in the order front
# cap / stator / rear cap along the axis, their volumes adding up to the body's within 0.1 %, their box the body's box,
# the shaft-end boss in the front cap; every other solid's box unchanged; 10 new leaves.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-75.FCStd", f"{MODELS}/vt350-lite-76.FCStd"
SOURCES = ("_Stepper_stator", "Motor_Body")
LINKS = {"_Stepper_stator001": "_Stepper_stator", "Motor_Body001": "Motor_Body", "Motor_Body002": "Motor_Body"}
STACK, CAP = 42.2, 42.0          # mm across: the stator lamination stack, the end caps
STEP = 0.1                       # slice spacing along the axis
VOL_TOL = 1e-3                   # 0.1 % (#237 AC1)
BOX_TOL = 1e-3


def seams(s):
    """The stator's ends along Z: the 42.2-wide run of the body's slices, each end snapped to the nearest Z of one of
    the body's planar faces normal to Z. Returns (z0, z1, the run's slice ends, the snap distances)."""
    b = s.BoundBox; run = []; z = b.ZMin + STEP / 2
    while z < b.ZMax:
        ws = s.slice(V(0, 0, 1), z)
        w = max((x.BoundBox.XLength for x in ws), default=0)
        if abs(w - STACK) < 0.05: run.append(z)
        z += STEP
    if not run: return None
    planes = sorted({round(f.BoundBox.ZMin, 4) for f in s.Faces
                     if f.Surface.__class__.__name__ == "Plane" and abs(f.Surface.Axis.z) > 0.999})
    lo, hi = run[0] - STEP / 2, run[-1] + STEP / 2        # the run's ends lie within half a step of these
    z0 = min(planes, key=lambda p: abs(p - lo)); z1 = min(planes, key=lambda p: abs(p - hi))
    return z0, z1, (run[0], run[-1]), (abs(z0 - lo), abs(z1 - hi))


def pieces(s, z0, z1):
    """s cut at z0 and z1 into (low, middle, high), each the common of s with a slab."""
    b = s.BoundBox; m = 5.0
    slab = lambda a, c: Part.makeBox(b.XLength + 2 * m, b.YLength + 2 * m, c - a, V(b.XMin - m, b.YMin - m, a))
    return [s.common(slab(a, c)) for a, c in ((b.ZMin - m, z0), (z0, z1), (z1, b.ZMax + m))]


def to_local(o, g):
    """A global shape in o's own frame (o's container placements and o.Placement taken off)."""
    g = g.copy(); pl = g.Placement; g.Placement = FreeCAD.Placement(); g.transformShape(pl.toMatrix(), True, False)
    g.transformShape(linkgeo.gplace(o).inverse().toMatrix(), True, False)
    g.Placement = o.Placement                   # assigning a shape sets the feature's Placement from the shape's
    return g


def main(p):
    m = p.open(SRC); doc = m.doc
    by = {o.Label: o for o in m.leaves if o.Label in SOURCES or o.Label in LINKS}
    src = [by.get(l) for l in SOURCES]; lnk = [by.get(l) for l in LINKS]
    p.check(None not in src and None not in lnk and all(o.TypeId == "Part::Feature" for o in src)
            and all(o.TypeId == "App::Link" and linkgeo.link_target(o).Label == LINKS[o.Label] for o in lnk),
            f"the 5 motor bodies: 2 Part::Features ({[o and o.TypeId for o in src]}), 3 links to them "
            f"({[(o.Label, linkgeo.link_target(o).Label) for o in lnk if o]})")
    if p.errs: return p.finish([])
    motors = src + lnk
    before = {o.Name: m.shapes[o.Name] for o in motors}
    for o in motors:
        b = before[o.Name].BoundBox
        p.check(abs(b.XLength - STACK) < 1.0 and abs(b.YLength - STACK) < 1.0 and b.ZLength > 40,   # BoundBox overshoots ~0.5
                f"{o.Label}: along Z ({b.XLength:.2f} x {b.YLength:.2f} x {b.ZLength:.2f})")
    if p.errs: return p.finish([])
    boxes0 = {n: s.BoundBox for n, s in m.shapes.items() if n not in before}
    n0 = len(m.leaves)
    # ---- the seams, on each source body (global = the frame the slices are in)
    cut = {}
    for o in src:
        g = before[o.Name]; r = seams(g)
        p.check(r is not None and max(r[3]) <= STEP / 2 + 1e-6,
                f"{o.Label}: the {STACK} stack from Z {r and r[2][0] - STEP / 2:.2f} to {r and r[2][1] + STEP / 2:.2f}; "
                f"seams on its planes at Z {r and r[0]} / {r and r[1]} (snapped {r and [round(x, 3) for x in r[3]]})")
        if r is None: continue
        z0, z1 = r[0], r[1]; b = g.BoundBox
        lo, mid, hi = pieces(g, z0, z1)
        # the shaft end: the slice nearest it is the small boss (22 mm), the other end is the full 42 mm cap
        def width(z): return max((x.BoundBox.XLength for x in g.slice(V(0, 0, 1), z)), default=0)
        shaft_low = width(b.ZMin + 0.05) < 30
        p.check(shaft_low != (width(b.ZMax - 0.05) < 30), f"{o.Label}: the shaft boss at one end "
                f"({'low' if shaft_low else 'high'} Z; widths {width(b.ZMin + 0.05):.1f} / {width(b.ZMax - 0.05):.1f})")
        front, rear = (lo, hi) if shaft_low else (hi, lo)
        for k, x in (("low", lo), ("mid", mid), ("high", hi)):
            if len(x.Solids) > 1:
                p.log(f"  {o.Label} {k} piece: {len(x.Solids)} solids: " + "; ".join(
                    f"{y.Volume:.2f} mm3 {[round(v, 2) for v in (y.BoundBox.XMin, y.BoundBox.XMax, y.BoundBox.YMin, y.BoundBox.YMax, y.BoundBox.ZMin, y.BoundBox.ZMax)]}"
                    for y in sorted(x.Solids, key=lambda y: -y.Volume)))
        cut[o.Name] = dict(front=front, stator=mid, rear=rear, z=(z0, z1),
                           lens=(z0 - b.ZMin, z1 - z0, b.ZMax - z1))
        p.log(f"  {o.Label}: lengths low cap / stator / high cap {[round(x, 2) for x in cut[o.Name]['lens']]}")
    if p.errs: return p.finish([])
    # ---- write: the source keeps the stator; two cap features beside it; two cap links beside each link
    gui = FreeCAD.GuiUp
    caps = {}                                            # source Name -> {"front": obj, "rear": obj}
    new = {}                                             # motor Name -> [front, stator, rear] objects
    for o in src:
        par = o.getParentGeoFeatureGroup(); c = cut[o.Name]; caps[o.Name] = {}
        mat = getattr(o, "ShapeMaterial", None)
        for k in ("front", "rear"):
            f = doc.addObject("Part::Feature", f"{o.Name}_{k}cap"); par.addObject(f)
            f.Label = f"{o.Label} {k} cap"; f.Placement = o.Placement
            f.Shape = to_local(f, c[k])
            if mat is not None:
                try: f.ShapeMaterial = mat
                except Exception as e: p.log(f"  material not copied to {f.Label}: {e}")
            caps[o.Name][k] = f
        o.Shape = to_local(o, c["stator"])
        new[o.Name] = [caps[o.Name]["front"], o, caps[o.Name]["rear"]]
    for o in lnk:
        par = o.getParentGeoFeatureGroup(); t = linkgeo.link_target(o); row = []
        for k in ("front", "rear"):
            l = doc.addObject("App::Link", f"{o.Name}_{k}cap"); par.addObject(l)
            l.LinkedObject = caps[t.Name][k]; l.Placement = o.Placement
            if hasattr(o, "LinkTransform"): l.LinkTransform = o.LinkTransform
            l.Label = f"{o.Label} {k} cap"; row.append(l)
        new[o.Name] = [row[0], o, row[1]]
    doc.recompute()
    if gui:                                               # the caps look like the stator until colours.json recolours them
        for o, (fr, _, re_) in ((o, new[o.Name]) for o in src):
            for f in (fr, re_):
                try: f.ViewObject.ShapeAppearance = o.ViewObject.ShapeAppearance
                except Exception as e: p.log(f"  look not copied to {f.Label}: {e}")
    m.refresh()
    # ---- after
    for o in motors:
        g0 = before[o.Name]; parts = [m.shapes.get(x.Name) for x in new[o.Name]]
        if None in parts:
            p.check(False, f"{o.Label}: all three pieces are leaves ({[x.Label for x in new[o.Name]]})"); continue
        sol = [len(x.Solids) for x in parts]
        # a piece is one main solid, plus (the Z motors' rear caps) the 4 tie-bolt ends the cut frees from the stator:
        # small, inside the main solid's box
        def whole(x):
            ss = sorted(x.Solids, key=lambda y: -y.Volume); mb = ss[0].BoundBox
            return all(y.Volume < 0.01 * ss[0].Volume and mb.isInside(y.BoundBox) for y in ss[1:])
        one = all(whole(x) for x in parts)
        vol = sum(x.Volume for x in parts)
        bb = FreeCAD.BoundBox(); [bb.add(x.BoundBox) for x in parts]
        db = max(abs(getattr(bb, k) - getattr(g0.BoundBox, k)) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"))
        zs = [(x.BoundBox.ZMin, x.BoundBox.ZMax) for x in parts]
        lowfirst = zs[0][0] < zs[2][0]
        seq = zs if lowfirst else zs[::-1]
        order = all(seq[i][1] <= seq[i + 1][0] + 1e-4 for i in range(2))
        p.check(one and abs(vol - g0.Volume) <= VOL_TOL * g0.Volume and db < BOX_TOL and order,
                f"{o.Label}: front cap / stator / rear cap, each one solid or one + small bits inside it {sol}, volume {vol:.1f} of {g0.Volume:.1f} "
                f"({(vol / g0.Volume - 1) * 100:+.4f} %), box within {db:.5f}, in order along Z "
                f"{[(round(a, 2), round(b, 2)) for a, b in zs]}")
    moved = [m.doc.getObject(n).Label for n, b in boxes0.items()
             if n not in m.shapes or not (m.shapes[n].BoundBox.isInside(b) and b.isInside(m.shapes[n].BoundBox))]
    p.check(not moved, f"every other solid's box unchanged ({len(moved)}: {moved[:5]})")
    p.check(len(m.leaves) == n0 + 10, f"leaves {n0} -> {len(m.leaves)} (+10: two caps for each of 5 motors)")
    p.dump({o.Label: {"seams_z": list(cut[o.Name]["z"]), "lengths_low_mid_high": [round(x, 3) for x in cut[o.Name]["lens"]]}
            for o in src})
    return p.finish([(doc, DST)])


if not os.environ.get("LITE76_AS_LIB"): litelib.Pass("lite76_stepper_caps").run(main)
