# GUI pass: vt350-lite-71 -> vt350-lite-72   (headless = dry run, never saves)   vt350#59
# Print fixes to lite-68's dock parts, found on the owner's first slice (2026-11-18/19):
#  1. the cowls: lite-23's old rear-bottom boss removed (below);
#  2. the keyslot plates: lite-68 filled the old rear-bottom keyslot only in part, leaving its nut pocket open from the
#     bed under a flat roof and a sloped sliver above it (Orca bridges and overhang walls inside the plate). The old
#     site is filled solid, from the bed to the plate's inner face;
#  3. the keyslot plates: where a pad's footprint passes the plate's edge it overhangs from the pad's base (h 4 mm);
#     the overhang is extruded down to the bed ("extrude that surface back down the plate", owner).
#  4. the keyslot plates: a pad thinner than THIN slices as one stray layer. lite-68 cut the Left plate's rear-top pad
#     back to 0.16 mm (the Left head's Crossbow lever, an 8 mm sleeve); the owner saw it on the slice (2026-11-19) and
#     chose to drop it: lite-68's keyslot there is lowered by the pad's thickness, so its face is the plate face (h 6)
#     and its lips sit at MadMax's h 4. The 8 mm standoff stays; the hook sits 0.16 mm further from the cowl, inside
#     the 6 mm pickup slide's play.
#  The flat roofs left inside the keyslots (the lips that hold the hook screw heads, over the hex below) stay: they
#  are the keyslot. The log compares them with MadMax's own plate (lite-67).
#
# 1. Removes lite-23's old rear-bottom dock boss from both cowls (owner, 2026-11-18: "you did not remove the old lower
# docking standoff"). lite-68 moved the rear-bottom insert 18.5 mm forward and 6.25 mm up into the cowl's solid
# corner, but kept lite-67's cowl, so the old boss stayed on: a dia 8 stub, 138 mm3 proud of DW-Tas's duct, with its
# old dia 2.9 screw tail still in it. Nothing uses it now.
#
# The stub is found as a solid of (cowl - DW-Tas's original duct), the original read from lite-22 (before any dock
# boss; same frame as the cowl, since the head groups move as wholes). Of the three such solids, the two top stubs
# carry the top inserts (a dia 4.8 pocket on their axis) and stay; the third, 54 mm from the rear-top axis on lite-23's
# screw square, is cut off. The old pocket lies wholly in the stub, so the cowl there becomes the original duct again.
# Checks (refuses to save on any):
#  - two cowls, three added solids each, exactly one of them pocket-free and on the 20 x 54 screw square;
#  - after the cut: one valid solid, volume = before - stub; (new - original) = the two top stubs only; (original -
#    new) unchanged (only lite-68's moved rear-bottom spot-face + pocket); no dia 2.9 tail left;
#  - the cut is >= 0.5 mm from lite-68's rear-bottom spot-face;
#  - every other solid's box unchanged; the head copies (links) follow their cowl.
import FreeCAD, Part, math, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC = os.environ.get("VT350_SRC", f"{MODELS}/vt350-lite-71.FCStd")    # dry runs may point at lite-70
DST = f"{MODELS}/vt350-lite-72.FCStd"
ORIG = f"{MODELS}/vt350-lite-22.FCStd"                                 # DW-Tas's ducts, before lite-23's bosses
DUCTS = {"Left": "[a]_Duct-4010-left MadMax dock bosses (remix, CC BY-NC-SA 4.0)",
         "Right": "[a]_Duct-4010-right MadMax dock bosses (remix, CC BY-NC-SA 4.0)"}
ORIG_DUCTS = {"Left": "[a]_Duct-4010-left", "Right": "[a]_Duct-4010-right001"}
POCKET_R, TAIL_R, SPOT_R = 2.4, 1.45, 2.75     # lite-68's insert pocket, lite-23's screw tail, lite-68's spot-face
UPSTREAM = f"{MODELS}/vt350-lite-67.FCStd"                             # MadMax's keyslot plates, before lite-68's pads
KEYS = "Dock Asembly"                                                  # the keyslot plate (MadMax's spelling)
DOCKS = {"Left": "Left Dock", "Right": "Right Dock"}
MOVE_RB = (-18.5, 6.25)                        # lite-68's rear-bottom keyslot move (global y, z)
KEYHOLE_R = 3.65                               # the keyslot's entry circle
OLD_BOX = ((-5.24, 8.96), (-4.4, 4.5))         # the old rear-bottom keyslot + its nut pocket, about its entry circle (y, z)
EDGE_Y = -38.30                                # ... capped inside the plate's long-edge chamfer foot (y -38.26)
STEEP = 0.75                                   # n . down above this is an overhang (the 45 deg chamfers are 0.71-0.72)
THIN = 1.0                                     # a pad standing less than this off the plate's inner face is dropped
THIN_PADS = {"Left": 1, "Right": 0}            # lite-68's log: only the Left rear-top pad (0.16 mm, 8 mm sleeve)


def layer(b0, up, h0, h1):
    """The slab between heights h0 and h1 above the bed (the plates print on a face normal to X)."""
    a, c = b0.x + up.x * h0, b0.x + up.x * h1
    return Part.makeBox(abs(c - a), 4000, 4000, V(min(a, c), -2000, -2000))


def axes(S, r):
    """(y, z) of S's cylinder faces of radius r along X (the screw axes, in the duct's frame)."""
    return sorted({(round(f.Surface.Center.y, 3), round(f.Surface.Center.z, 3)) for f in S.Faces
                   if f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - r) < 1e-6
                   and abs(abs(f.Surface.Axis.x) - 1) < 1e-6})


def near(c, a, tol=1.0): return math.hypot(c.y - a[0], c.z - a[1]) < tol


def bed(s):
    """(bed point, down) of a part printed on its largest planar face."""
    f = max((x for x in s.Faces if x.Surface.__class__.__name__ == "Plane"), key=lambda x: x.Area)
    u0, u1, v0, v1 = f.ParameterRange
    return f.CenterOfMass, f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)


def overhangs(s, b0, down):
    """[(face, h_min, n.down max, shadow-in-plate-outline fraction)] of the faces facing down steeper than STEEP, off
    the bed. The fraction: 1 = over a hole inside the plate's outline (a keyslot lip), 0 = past the plate's edge."""
    up = -down
    out_f = outline(s, b0, down)
    res = []
    for f in s.Faces:
        if f.Area < 0.05: continue
        u0, u1, v0, v1 = f.ParameterRange; ns = []
        for a in (0.1, 0.5, 0.9):
            for c in (0.1, 0.5, 0.9):
                try: ns.append(f.normalAt(u0 + a * (u1 - u0), v0 + c * (v1 - v0)).dot(down))
                except Exception: pass
        if not ns or max(ns) <= STEEP: continue
        h = min((v.Point - b0).dot(up) for v in f.Vertexes)
        if h < 0.05: continue
        P = f.extrude(down * (max((v.Point - b0).dot(up) for v in f.Vertexes) + 1))
        res.append((f, h, max(ns), P.common(out_f).Volume / P.Volume if P.Volume > 1e-6 else 1.0))
    return res


def outline(s, b0, down, h=3.5):
    """The plate's outer outline (holes ignored) at height h, as a prism from below the bed to above the part."""
    up = -down
    ws = s.slice(up, b0.dot(up) + h)
    w = max(ws, key=lambda w: Part.Face(w).Area)
    f = Part.Face(w); f.translate(down * (h + 1))
    return f.extrude(up * 40)


def outer_area(s, b0, down, h):
    ws = s.slice(-down, b0.dot(-down) + h)
    return max(Part.Face(w).Area for w in ws), Part.makeFace(ws, "Part::FaceMakerBullseye").Area   # outline, material


def plate(p, side, S):
    """(fixed keyslot plate, global; info)."""
    b0, down = bed(S); up = -down
    p.check(abs(abs(down.x) - 1) < 1e-9, f"{side} plate: prints on a face normal to X ({down})")
    tops = [f for f in S.Faces if f.Surface.__class__.__name__ == "Plane" and f.normalAt(0, 0).dot(up) > 0.999]
    top = max(tops, key=lambda f: f.Area); H = (top.CenterOfMass - b0).dot(up)
    p.check(abs(H - 6.0) < 1e-3, f"{side} plate: MadMax's 6 mm plate under the pads (inner face at h {H:.3f})")
    # 2. the old rear-bottom keyslot: lite-68's moved entry circle minus the move
    holes = sorted({(round(f.Surface.Center.y, 3), round(f.Surface.Center.z, 3)) for f in S.Faces
                    if f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - KEYHOLE_R) < 1e-6
                    and abs(abs(f.Surface.Axis.x) - 1) < 1e-6})
    sloped = [f for f, h, n, fr in overhangs(S, b0, down) if n < 0.99]
    olds = [(y - MOVE_RB[0], z - MOVE_RB[1]) for y, z in holes]
    near = [o for o in olds if sloped and all(math.hypot(f.CenterOfMass.y - o[0], f.CenterOfMass.z - o[1]) < 9 for f in sloped)]
    p.check(len(holes) == 3 and len(near) == 1, f"{side} plate: three keyslots {holes}; the old rear-bottom site among "
                                                f"{[(round(a, 2), round(b, 2)) for a, b in olds]} holds the {len(sloped)} sloped overhangs ({near})")
    if p.errs: return None
    oy, oz = near[0]
    y0, y1 = oy + OLD_BOX[0][0], min(oy + OLD_BOX[0][1], EDGE_Y)
    z0, z1 = oz + OLD_BOX[1][0], oz + OLD_BOX[1][1]
    x0 = b0.x if down.x < 0 else b0.x - H
    box = Part.makeBox(H, y1 - y0, z1 - z0, V(x0, y0, z0))
    void = box.cut(S).Volume
    out_f = outline(S, b0, down)
    p.check(abs(box.common(out_f).Volume - box.Volume) < 1e-6, f"{side} plate: the old-keyslot fill lies inside the plate's outline")
    keep = [(y, z) for y, z in holes]
    p.check(all(not (y0 - KEYHOLE_R < y < y1 + KEYHOLE_R and z0 - KEYHOLE_R < z < z1 + KEYHOLE_R) for y, z in keep),
            f"{side} plate: no live keyslot near the fill")
    B = S.fuse(box).removeSplitter()
    p.check(box.cut(B).Volume < 1e-6, f"{side} plate: the old keyslot is solid ({void:.2f} mm3 filled)")
    for h in (0.3, 2.0, 3.9, 4.1, 5.0, 5.9):
        o0, t0 = outer_area(S, b0, down, h); o1, t1 = outer_area(B, b0, down, h)
        p.check(abs(o1 - o0) < 0.01 and t1 >= t0 - 1e-6, f"{side} plate h {h}: outline unchanged ({o0:.2f} -> {o1:.2f}), only holes filled (material {t0:.2f} -> {t1:.2f})")
    # 3. a pad past the plate's edge: its overhang extruded down to the bed
    fills = []
    for f, h, n, fr in overhangs(B, b0, down):
        if fr < 0.02:
            p.check(n > 0.99, f"{side} plate: the overhang past the edge at h {h:.2f} is flat ({n:.2f})")
            fills.append(f.extrude(down * h))
    p.check(1 <= len(fills) <= 4, f"{side} plate: overhangs past the edge to fill ({len(fills)})")
    N = B.fuse(fills).removeSplitter() if fills else B
    # 4. a pad too thin to print: that keyslot back to MadMax's plate (lite-67)
    pads = [s for s in N.common(layer(b0, up, H + 1e-4, H + 40)).Solids if s.Volume > 1e-3]
    tall = [max((v.Point - b0).dot(up) for v in s.Vertexes) - H for s in pads]
    thin = [s for s, t in zip(pads, tall) if t < THIN]
    p.check(len(thin) == THIN_PADS[side], f"{side} plate: pads under {THIN} mm ({[round(t, 3) for t in tall if t < THIN]} "
                                          f"of {[round(t, 3) for t in sorted(tall)]}); expected {THIN_PADS[side]}")
    if p.errs: return None
    # lite-68 built that keyslot's channel and lips 0.16 mm higher with the pad (lips at h 4.17, not MadMax's 4.0; the
    # same flat-lipped channel as the other two pads, not MadMax's sloped one). So the keyslot is lowered, not
    # replaced: inside the pad's footprint, a slice as thick as the pad is taken out of a straight-walled band just
    # below the lips and everything above it closes down. The pad face lands on the plate face (h 6), the lips at
    # h 4.0, and the screw head's 2 mm channel keeps its depth.
    thin_mm3, regions = 0.0, []
    sec = lambda X, h: sum(Part.makeFace(ws, "Part::FaceMakerBullseye").Area for ws in [X.slice(up, b0.dot(up) + h)] if ws)
    for s in thin:
        t = max((v.Point - b0).dot(up) for v in s.Vertexes) - H
        # its top: the face with every vertex at the pad's height (lite-68's pad faces aren't all Plane surfaces)
        ftop = max((f for f in s.Faces if all(abs((v.Point - b0).dot(up) - H - t) < 1e-4 for v in f.Vertexes)), key=lambda f: f.Area)
        F = Part.Face(ftop.OuterWire); F.translate(down * (H + t + 1)); F = F.extrude(up * (H + t + 3))
        p.check(s.cut(F).Volume < 1e-4, f"{side} plate: the thin pad ({t:.3f} mm, {s.Volume:.2f} mm3) lies in its footprint prism")
        Pf = N.common(F)
        roofs = sorted(h for f, h, n, fr in overhangs(Pf, b0, down) if 3.0 < h < H)
        p.check(bool(roofs) and abs(roofs[0] - 4.0 - t) < 0.02, f"{side} plate: the pad's lips sit {t:.3f} mm above MadMax's h 4 ({[round(h, 3) for h in roofs]})")
        if p.errs: return None
        a = roofs[0] - t - 0.05                                   # the band [a, a + t], just below the lips
        inband = [v for v in Pf.Vertexes if a - 1e-6 <= (v.Point - b0).dot(up) <= a + t + 1e-6]
        s0, s1 = sec(Pf, a), sec(Pf, a + t)
        p.check(not inband and abs(s0 - s1) < 1e-3, f"{side} plate: the band h {a:.3f}..{a + t:.3f} is straight-walled ({len(inband)} vertices in it; section {s0:.3f} / {s1:.3f} mm2)")
        if p.errs: return None
        lo = Pf.common(layer(b0, up, -1, a)); hi = Pf.common(layer(b0, up, a + t, H + 40)); hi.translate(down * t)
        M = N.cut(F).fuse([lo, hi]).removeSplitter()
        p.check(abs((N.Volume - M.Volume) - t * s0) < 0.05, f"{side} plate: lowering takes out the band ({N.Volume - M.Volume:.3f} vs {t * s0:.3f} mm3)")
        Mf = M.common(F)
        p.check(Mf.common(layer(b0, up, H + 1e-4, H + 40)).Volume < 1e-4, f"{side} plate: nothing stands above the plate face in the footprint")
        same = [(round(h, 2), round(sec(Mf, h), 3), round(sec(Pf, h + t), 3)) for h in (a + 0.05, roofs[0] - t + 0.05, 5.0, 5.9)]
        p.check(all(abs(x - y) < 1e-3 for _, x, y in same), f"{side} plate: above the band the keyslot is lite-68's, {t:.3f} mm lower (h, section now, section was +t: {same})")
        thin_mm3 += N.Volume - M.Volume; regions.append(F); N = M
    p.check(N.isValid() and len(N.Solids) == 1, f"{side} plate: one valid solid ({len(N.Solids)}, valid {N.isValid()})")
    left = [max((v.Point - b0).dot(up) for v in s.Vertexes) - H for s in N.common(layer(b0, up, H + 1e-4, H + 40)).Solids if s.Volume > 1e-3]
    p.check(all(t >= THIN for t in left) and len(left) == len(pads) - len(thin),
            f"{side} plate: every pad left stands >= {THIN} mm ({[round(t, 3) for t in sorted(left)]})")
    rest = overhangs(N, b0, down)
    for R in regions:
        at = [h for f, h, n, fr in rest if R.BoundBox.isInside(f.CenterOfMass)]
        p.check(at and all(abs(h - 4.0) < 0.02 for h in at), f"{side} plate: the lowered keyslot's lips are at h 4, as MadMax's ({[round(h, 3) for h in at]})")
    p.check(all(fr > 0.98 for f, h, n, fr in rest), f"{side} plate: every overhang left is over a hole in the plate "
                                                     f"({[(round(h, 2), round(fr, 2)) for f, h, n, fr in rest]})")
    nb, _ = bed(N)
    p.check(abs((nb - b0).dot(up)) < 1e-6, f"{side} plate: still prints on the same face")
    info = dict(old_keyslot_yz=[round(oy, 2), round(oz, 2)], old_keyslot_filled_mm3=round(void, 2),
                edge_fill_mm3=round(sum(x.Volume for x in fills), 2), thin_pad_dropped_mm3=round(thin_mm3, 2),
                lips=sorted((round(h, 2), round(f.Area, 2)) for f, h, n, fr in rest),
                volume=[round(S.Volume, 2), round(N.Volume, 2)])
    return N, info


def group_paths(doc):
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, "Group", None) or []): par.setdefault(k.Name, o)
    def path(o):
        r, q = [], par.get(o.Name)
        while q is not None: r.append(q.Label); q = par.get(q.Name)
        return r
    return {o.Name: path(o) for o in doc.Objects}


def to_local(shape, pl):
    s = shape.copy(); s.transformShape(pl.inverse().toMatrix(), True, False); s.Placement = pl
    return s


def main(p):
    od = FreeCAD.openDocument(ORIG); p.log("opened (read-only)", ORIG)
    orig = {}
    for side, lab in ORIG_DUCTS.items():
        c = [o for o in od.Objects if o.Label == lab and hasattr(o, "Shape") and o.Shape.Volume > 1000]
        p.check(len(c) == 1, f"{side}: one original duct {lab!r} in lite-22 ({len(c)})")
        if c: orig[side] = c[0].Shape.copy()
    if p.errs: return p.finish([])
    ud = FreeCAD.openDocument(UPSTREAM); p.log("opened (read-only)", UPSTREAM)
    UG, up_lips = group_paths(ud), {}
    for side, dk in DOCKS.items():
        c = [o for o in ud.Objects if o.TypeId == "Part::Feature" and o.Label.startswith(KEYS) and dk in UG.get(o.Name, [])]
        p.check(len(c) == 1, f"{side}: MadMax's keyslot plate in lite-67 ({[o.Label for o in c]})")
        if not c: continue
        U = linkgeo.gshape(c[0]); ub, ud_ = bed(U)
        up_lips[side] = sorted((round(h, 2), round(f.Area, 2), round(fr, 2)) for f, h, n, fr in overhangs(U, ub, ud_))
        p.log(f"{side}: MadMax's plate's overhangs (h, mm2, over-a-hole): {up_lips[side]}")
    FreeCAD.closeDocument(ud.Name)
    pr = p.open(SRC); doc = pr.doc
    targets = {}
    for side, lab in DUCTS.items():
        c = [o for o in doc.getObjectsByLabel(lab) if o.TypeId == "Part::Feature"]
        p.check(len(c) == 1, f"{side}: one cowl {lab!r} ({len(c)})")
        if c: targets[side] = c[0]
    if p.errs: return p.finish([])
    copies = {s: [o for o in pr.leaves if linkgeo.link_target(o).Name == t.Name and o.Name != t.Name] for s, t in targets.items()}
    p.log("cowl copies (links):", {s: [o.Label for o in v] for s, v in copies.items()})
    box0 = {n: s.BoundBox for n, s in pr.shapes.items()}
    mine = {t.Name for t in targets.values()} | {o.Name for v in copies.values() for o in v}
    made, info = {}, {}
    for side, t in targets.items():
        S, O = t.Shape.copy(), orig[side]
        common = S.common(O).Volume
        p.check(common > 0.97 * O.Volume, f"{side}: the cowl overlays the original duct (less pockets and print chamfers, lite-70/71) ({common:.1f} of {O.Volume:.1f} mm3)")
        add = [s for s in S.cut(O).Solids if s.Volume > 1.0]
        rem0 = S.cut(O).Volume, O.cut(S).Volume
        pk = axes(S, POCKET_R)
        p.check(len(add) == 3, f"{side}: three solids proud of the original duct ({[round(s.Volume, 2) for s in add]})")
        p.check(len(pk) == 3, f"{side}: three insert pockets ({pk})")
        if p.errs: return p.finish([])
        keep = [s for s in add if any(near(s.BoundBox.Center, a) for a in pk)]
        stub = [s for s in add if not any(near(s.BoundBox.Center, a) for a in pk)]
        p.check(len(keep) == 2 and len(stub) == 1, f"{side}: two top stubs carry pockets, one stub doesn't ({len(keep)}, {len(stub)})")
        if p.errs: return p.finish([])
        st = stub[0]
        tops = [a for a in pk if any(near(s.BoundBox.Center, a) for s in keep)]
        # the stub's axis is its old screw tail's (its box centre is off-axis: the print face trims it at a slant)
        tail = [a for a in axes(S, TAIL_R) if st.common(Part.makeCylinder(TAIL_R + 0.5, 4000, V(-2000, *a), V(1, 0, 0))).Volume > 1.0]
        p.check(len(tail) == 1, f"{side}: the stub holds lite-23's dia {2 * TAIL_R} screw tail ({axes(S, TAIL_R)})")
        if p.errs: return p.finish([])
        c = V(0, *tail[0])
        d54 = sorted(math.hypot(c.y - a[0], c.z - a[1]) for a in tops)
        p.check(abs(math.dist(*tops) - 20.0) < 0.05 and any(abs(d - 54.0) < 0.1 for d in d54),
                f"{side}: the stub sits on lite-23's 20 x 54 screw square (tops {math.dist(*tops):.3f} apart; stub {[round(d, 3) for d in d54]} from them)")
        rb = [a for a in pk if a not in tops][0]
        gap = math.hypot(c.y - rb[0], c.z - rb[1]) - 4.0 - SPOT_R
        p.check(gap >= 0.5, f"{side}: the stub is {gap:.2f} mm clear of lite-68's rear-bottom spot-face")
        N = S.cut(st).removeSplitter()
        p.check(N.isValid() and len(N.Solids) == 1, f"{side}: one valid solid after the cut ({len(N.Solids)}, valid {N.isValid()})")
        p.check(abs(N.Volume - (S.Volume - st.Volume)) < 0.05, f"{side}: volume {S.Volume:.2f} - stub {st.Volume:.2f} = {N.Volume:.2f}")
        add1 = [s for s in N.cut(O).Solids if s.Volume > 1.0]
        p.check(len(add1) == 2 and abs(N.cut(O).Volume - (rem0[0] - st.Volume)) < 0.05,
                f"{side}: proud of the original now: the two top stubs only ({[round(s.Volume, 2) for s in add1]})")
        p.check(abs(O.cut(N).Volume - rem0[1]) < 0.05, f"{side}: cut into the original unchanged ({O.cut(N).Volume:.2f} vs {rem0[1]:.2f} mm3)")
        p.check(not axes(N, TAIL_R), f"{side}: no screw tail left ({axes(N, TAIL_R)})")
        made[side] = N
        info[side] = {"stub_mm3": round(st.Volume, 2), "stub_axis_yz": [round(c.y, 3), round(c.z, 3)],
                      "clear_of_rb_spot_mm": round(gap, 2), "volume": [round(S.Volume, 2), round(N.Volume, 2)]}
        p.log(f"{side}: {info[side]}")
    FreeCAD.closeDocument(od.Name)
    if p.errs: return p.finish([])
    # the keyslot plates and their slot-dock copies (Part::Feature copies of a side's plate, or links to it)
    G = group_paths(doc)
    keys, pmade, pinfo = {}, {}, {}
    for side, dk in DOCKS.items():
        k = [o for o in pr.leaves if o.Label.startswith(KEYS) and o.TypeId == "Part::Feature" and dk in G.get(o.Name, [])]
        p.check(len(k) == 1, f"{side}: one keyslot plate in {dk} ({[o.Label for o in k]})")
        if k: keys[side] = k[0]
    if p.errs: return p.finish([])
    kcop = {side: [o for o in pr.leaves if o.Name != K.Name and (
        (o.TypeId == "App::Link" and linkgeo.link_target(o).Name == K.Name) or
        (o.TypeId == "Part::Feature" and o.Label.startswith(KEYS) and abs(o.Shape.Volume - K.Shape.Volume) < 1e-3
         and o.Placement.isSame(K.Placement, 1e-9)))] for side, K in keys.items()}
    p.log("keyslot plate copies:", {s_: [(o.Label, o.TypeId) for o in v] for s_, v in kcop.items()})
    p.check(sum(len(v) for v in kcop.values()) == 3, f"the three slot docks' plates ({sum(len(v) for v in kcop.values())})")
    for side, K in keys.items():
        r = plate(p, side, linkgeo.gshape(K))
        if r is None: return p.finish([])
        pmade[side], pinfo[side] = r
        p.log(f"{side} plate: {pinfo[side]}")
    if p.errs: return p.finish([])
    pl_names = {K.Name for K in keys.values()} | {o.Name for v in kcop.values() for o in v}
    mine |= pl_names
    pairs = [(a.Name, b.Name) for a in pr.leaves if a.Name in pl_names for b in pr.leaves
             if b.Name not in pl_names and pr.shapes[a.Name].BoundBox.intersect(pr.shapes[b.Name].BoundBox)]
    base = dict(zip(pairs, p.volumes([(pr.shapes[a], pr.shapes[b]) for a, b in pairs])))
    p.log("plate overlaps before:", {(doc.getObject(a).Label, doc.getObject(b).Label): round(v, 2) for (a, b), v in base.items() if v > 1e-3})
    gui = FreeCAD.GuiUp
    for side, K in keys.items():
        pl = FreeCAD.Placement(K.Placement)
        ap = list(K.ViewObject.ShapeAppearance) if gui and hasattr(K.ViewObject, "ShapeAppearance") else None
        cpl = linkgeo.gplace(K).multiply(K.Placement.inverse())
        loc = pmade[side].copy(); loc.transformShape(cpl.inverse().toMatrix(), True, False)
        K.Shape = to_local(loc, pl)
        if ap is not None: K.ViewObject.ShapeAppearance = ap
        p.check(K.Placement.isSame(pl, 1e-9), f"{side}: the keyslot plate keeps its placement")
        for o in kcop[side]:
            if o.TypeId != "Part::Feature": continue
            ap = list(o.ViewObject.ShapeAppearance) if gui and hasattr(o.ViewObject, "ShapeAppearance") else None
            o.Shape = K.Shape.copy()
            if ap is not None: o.ViewObject.ShapeAppearance = ap
    gui = FreeCAD.GuiUp
    for side, t in targets.items():
        pl = FreeCAD.Placement(t.Placement)
        ap = list(t.ViewObject.ShapeAppearance) if gui and hasattr(t.ViewObject, "ShapeAppearance") else None
        s = made[side].copy(); s.transformShape(pl.inverse().toMatrix(), True, False); s.Placement = pl
        # t.Shape is the container-frame shape: the same placement, local geometry (lite68's to_local)
        t.Shape = s
        if ap is not None: t.ViewObject.ShapeAppearance = ap
        p.check(t.Placement.isSame(pl, 1e-9), f"{side}: the cowl keeps its placement")
    doc.recompute(); pr.refresh()
    for side, t in targets.items():
        p.check(abs(t.Shape.Volume - made[side].Volume) < 0.05 and t.Shape.isValid(), f"{side}: saved shape valid, {t.Shape.Volume:.2f} mm3")
        for o in copies[side]:
            p.check(abs(pr.shapes[o.Name].Volume - made[side].Volume) < 0.05, f"{side}: copy {o.Label} follows ({pr.shapes[o.Name].Volume:.2f})")
    for side, K in keys.items():
        p.check(K.Shape.isValid() and abs(pr.shapes[K.Name].Volume - pmade[side].Volume) < 0.05,
                f"{side} keyslot plate: saved shape valid, {pr.shapes[K.Name].Volume:.2f} mm3")
        for o in kcop[side]:
            p.check(abs(pr.shapes[o.Name].Volume - pmade[side].Volume) < 0.05, f"{side}: copy {o.Label} follows ({pr.shapes[o.Name].Volume:.2f})")
    pairs = [(a.Name, b.Name) for a in pr.leaves if a.Name in pl_names for b in pr.leaves
             if b.Name not in pl_names and pr.shapes[a.Name].BoundBox.intersect(pr.shapes[b.Name].BoundBox)]
    vols = dict(zip(pairs, p.volumes([(pr.shapes[a], pr.shapes[b]) for a, b in pairs])))
    worse = sorted(((v, doc.getObject(a).Label, doc.getObject(b).Label) for (a, b), v in vols.items()
                    if v > base.get((a, b), 0.0) + 0.01), reverse=True)
    p.check(not worse, f"no new overlap of a keyslot plate ({len(worse)}: {[(round(v, 2), a, b) for v, a, b in worse[:4]]})")
    moved = [doc.getObject(k).Label for k, b in box0.items() if k not in mine
             and (k not in pr.shapes or not pr.shapes[k].BoundBox.isInside(b) or not b.isInside(pr.shapes[k].BoundBox))]
    p.check(not moved, f"every other solid's box unchanged ({len(moved)}: {moved[:5]})")
    p.dump({"cowl": info, "plates": pinfo, "madmax_plate_overhangs": up_lips, "src": os.path.basename(SRC)})
    return p.finish([(doc, DST)])


if not os.environ.get("LITE72_AS_LIB"): litelib.Pass("lite72_dock_print_fixes").run(main)
