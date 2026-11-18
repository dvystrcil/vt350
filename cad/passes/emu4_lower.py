# GUI pass: vt350-emu-3.FCStd -> vt350-emu-4.FCStd   (reads vt350-lite-70; headless = dry run, never saves)   vt350#187, #4
# The EMU comes down onto the roof panel. Its rubber feet were at Z 712.1 (8 mm over the roof felt's top, though
# lite-55 meant them on it); lite-69 moved the roof insulation under the panel, so it floated 19.1 mm up. Owner, 2026-11-18: "lower the EMU onto the roof panel".
#  - The whole EMU (its root App::Part) moves straight down until its lowest part sits on the roof panel's top face.
#  - Its five roof-exit bowdens (emu-3) are rebuilt: the head tubes' roof ends don't move, the lane couplers do, so each
#    is re-routed with emu3_bowdens' route (cad/passes/emu_bowden.py: R 100 arcs, an S down, >= 25 mm straight in),
#    after a straight lead-in out of the roof clamp's bore (emu-3's first arc began inside it: 1.25 mm into the cap).
# Checks (refuses to save on any):
#  - the printer model is lite-70 (lite-69's insulation inside + lite-70's roof exit); a dry run can read lite-68 minus
#    the roof insulation lite-69 moves (its clamps and cables are then lite-36/40's); never saves;
#  - every EMU part moved by exactly dz (links included), the count unchanged; its bottom on the roof's (paint) top;
#  - five new tubes: one valid solid within 1 % of pi r2 L, starting on the head tube's end along it, ending on the
#    coupler face along -Y, smallest bend radius >= 80, Y max <= 528 (5 mm in front of the cable channel);
#  - no overlap: tubes vs EMU parts, tubes vs printer (envelopes and the head tubes they continue excepted),
#    the EMU's low parts vs printer, tube vs tube; each tube's centre line >= its radius off every printer part near it.
import FreeCAD, os, re, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.dirname(os.path.abspath(__file__))]
import litelib, linkgeo, emu_bowden as eb
from litelib import MODELS
V = FreeCAD.Vector
LITE70, LITE68 = f"{MODELS}/vt350-lite-70.FCStd", f"{MODELS}/vt350-lite-68.FCStd"
EMU3, EMU4 = f"{MODELS}/vt350-emu-3.FCStd", f"{MODELS}/vt350-emu-4.FCStd"
ROOT = "EMU 5-lane (DW-Tas)"
BOWDENS = "Bowdens, roof exits to the lanes"
ROOF_PANEL = re.compile(r"^Roof panel \(3 mm\)$")
ROOF_INS = re.compile(r"^Roof felt ")          # under the panel from lite-69; still on top in lite-68
TOL = 1e-3
Y_MAX = 528.0                # emu-3's 525 less 3: the 17 mm lead-in out of the clamp puts arc 1's top at Y 527.0;
                             # the cable channel starts at Y 533, so >= 5 mm in front of it (the clearance check measures it)
CLEAR_C = 0.2                 # mm: the lead-in ends where the tube is this far clear of the clamp
LOW = 30.0                                      # mm: EMU parts this close to the bottom are checked against the printer


def main(p):
    final = os.path.exists(LITE70)
    pr = p.open(LITE70 if final else LITE68)
    if not final: p.log("lite-70 not saved yet: dry run against lite-68 without its roof insulation; will not save")
    p.check(final or p.dry, "the printer model is lite-70 (a GUI save needs it)")
    rp = [o for o in pr.leaves if ROOF_PANEL.match(o.Label)]
    p.check(len(rp) == 1, f"one roof panel ({len(rp)})")
    if p.errs: return p.finish([])
    paint = [o for o in pr.leaves if o.Label == rp[0].Label + " paint, outside"]
    p.check(len(paint) == 1, f"the roof's paint layer ({len(paint)})")
    if p.errs: return p.finish([])
    top = max(pr.boxes[rp[0].Name].ZMax, pr.boxes[paint[0].Name].ZMax)      # the roof's top is its paint's
    heads = sorted([o for o in pr.leaves if o.Label.startswith("Bowden") and pr.boxes[o.Name].ZMax > 700],
                   key=lambda o: pr.boxes[o.Name].XMin)
    p.check(len(heads) == 5, f"head tubes reaching the roof: {len(heads)} (5)")
    ends = []
    for o in heads:
        import Part
        circ = [e for e in pr.shapes[o.Name].Edges if isinstance(e.Curve, Part.Circle)]
        c = max(circ, key=lambda e: e.Curve.Center.z)
        ax = c.Curve.Axis; ax = ax if ax.z > 0 else -ax
        ends.append((o, c.Curve.Center, ax))
    em = p.open(EMU3); ed = em.doc
    root = em.root(ROOT)
    grp = next(o for o in ed.Objects if o.TypeId == "App::Part" and o.Label.startswith(BOWDENS))
    old = [o for o in em.leaves if grp in o.InListRecursive]
    p.check(len(old) == 5, f"emu-3's five roof-exit bowdens ({len(old)})")
    parts = [o for o in em.leaves if o not in old]
    z0 = min(em.boxes[o.Name].ZMin for o in parts)
    dz = top - z0
    p.log(f"roof top (paint) Z {top:.3f}; EMU bottom (its rubber feet) Z {z0:.3f}; move dz {dz:.3f}")
    p.check(-25 < dz < 0, f"the EMU comes down a little ({dz:.3f} mm)")
    if p.errs: return p.finish([])
    box0 = {o.Name: FreeCAD.BoundBox(em.shapes[o.Name].BoundBox) for o in parts}; n0 = len(parts)
    rp0 = root.getParentGeoFeatureGroup(); C = rp0.getGlobalPlacement() if rp0 else FreeCAD.Placement()
    root.Placement = C.inverse().multiply(FreeCAD.Placement(V(0, 0, dz), FreeCAD.Rotation())).multiply(C).multiply(root.Placement)
    for o in old: ed.removeObject(o.Name)
    ed.recompute(); em.refresh()
    parts = [o for o in em.leaves if o.Name in box0]
    bad = [o.Label for o in parts
           if any(abs(a - b) > TOL for a, b in zip(
               (em.shapes[o.Name].BoundBox.XMin, em.shapes[o.Name].BoundBox.YMin, em.shapes[o.Name].BoundBox.ZMin,
                em.shapes[o.Name].BoundBox.XMax, em.shapes[o.Name].BoundBox.YMax, em.shapes[o.Name].BoundBox.ZMax),
               (box0[o.Name].XMin, box0[o.Name].YMin, box0[o.Name].ZMin + dz,
                box0[o.Name].XMax, box0[o.Name].YMax, box0[o.Name].ZMax + dz)))]
    p.check(not bad and len(parts) == n0, f"every EMU part moved by exactly dz ({len(bad)} off: {bad[:5]}; {len(parts)} of {n0})")
    z1 = min(em.boxes[o.Name].ZMin for o in parts)
    p.check(abs(z1 - top) < TOL, f"the EMU's bottom on the roof's top (Z {z1:.3f})")
    rear = lambda o: em.boxes[o.Name].YMax > 180
    clips = sorted([o for o in em.leaves if o.Label.startswith("Release clip") and rear(o)], key=lambda o: em.boxes[o.Name].XMin)
    p.check(len(clips) == 5, f"EMU rear couplers: {len(clips)} (5)")
    if p.errs: return p.finish([])
    outs = [V((em.boxes[c.Name].XMin + em.boxes[c.Name].XMax) / 2, em.boxes[c.Name].YMax,
              (em.boxes[c.Name].ZMin + em.boxes[c.Name].ZMax) / 2) for c in clips]
    import Part
    clamps = [o for o in pr.leaves if o.Label.startswith("Roof exit clamp")]
    made = []
    for i, ((tube, e, ax), o) in enumerate(zip(ends, outs), 1):
        # straight on out of the clamp's bore first: the first 0.5 mm step where the centre line is R_T + CLEAR_C off
        # every clamp part (emu-3's arc began inside the bore and cut 1.25 mm into the cap; booleans missed it)
        near = [pr.shapes[c.Name] for c in clamps if pr.boxes[c.Name].isInside(e) or pr.boxes[c.Name].intersect(
                FreeCAD.BoundBox(e.x - 5, e.y - 5, e.z - 5, e.x + 5, e.y + 5, e.z + 5))]
        lead = next((s / 2 for s in range(0, 100) if all(
            not c.isInside(e + ax * (s / 2), 0.0, True) and c.distToShape(Part.Vertex(e + ax * (s / 2)))[0] > eb.R_T + CLEAR_C
            for c in near)), None)
        p.check(lead is not None, f"lane {i}: the bore's exit found ({len(near)} clamp parts round the end, lead {lead} mm)")
        if lead is None: continue
        try: sweep, edge, rmin, th, lf = eb.tube(e, ax, o, lead)
        except RuntimeError as x: p.check(False, f"lane {i}: {x}"); continue
        want = math.pi * eb.R_T ** 2 * edge.Length
        p.check(sweep.isValid() and len(sweep.Solids) == 1 and abs(sweep.Volume - want) < 0.01 * want,
                f"lane {i} tube: one valid solid, {sweep.Volume:.0f} mm3 (pi r2 L = {want:.0f}), length {edge.Length:.0f}")
        p.check(rmin >= eb.MIN_R, f"lane {i} tube: smallest bend radius {rmin:.1f} (>= {eb.MIN_R:.0f}); S {th:.0f} deg, straight in {lf:.0f}")
        p.check(sweep.BoundBox.YMax <= Y_MAX, f"lane {i} tube: Y max {sweep.BoundBox.YMax:.1f} (<= {Y_MAX:.0f}), Z max {sweep.BoundBox.ZMax:.1f}")
        t0, t1 = edge.tangentAt(edge.FirstParameter), edge.tangentAt(edge.LastParameter)
        p.check(edge.Vertexes[0].Point.distanceToPoint(e) <= 0.05 and math.degrees(t0.getAngle(ax)) <= 0.5,
                f"lane {i}: starts on {tube.Label}'s end along it ({edge.Vertexes[0].Point.distanceToPoint(e):.3f} mm)")
        p.check(edge.Vertexes[-1].Point.distanceToPoint(o) <= 0.05 and math.degrees(t1.getAngle(V(0, -1, 0))) <= 0.5,
                f"lane {i}: ends on its coupler's face along -Y ({edge.Vertexes[-1].Point.distanceToPoint(o):.3f} mm)")
        obj = ed.addObject("Part::Feature", "Bowden_roof_emu"); grp.addObject(obj)
        loc = sweep.copy(); loc.Placement = linkgeo.gplace(grp).inverse().multiply(loc.Placement)
        obj.Shape = loc
        obj.Label = f"Bowden lane {i} to {tube.Label} (PTFE 4.12 OD, roof exit to the EMU, {edge.Length:.0f} mm)"
        if FreeCAD.GuiUp:
            try: obj.ViewObject.ShapeAppearance = (linkgeo.drawn_vo(tube) or tube.ViewObject).ShapeAppearance
            except Exception: pass
        made.append((obj, sweep, edge.Length, rmin, edge))
    if p.errs: return p.finish([])
    grp.Label = "Bowdens, roof exits to the lanes (emu-4, #187)"
    ed.recompute(); em.refresh()
    items = [(o.Label, s) for o, s, *_ in made]
    p.no_overlap(items, em, lambda r: f"no tube overlaps an EMU part: {len(r.hits)} {r.hits[:8]}", exclude={o.Name for o, *_ in made})
    skip = {o.Name for o in pr.leaves if "envelope" in o.Label} | {t.Name for t, *_ in ends}
    if not final: skip |= {o.Name for o in pr.leaves if ROOF_INS.match(o.Label)}
    p.no_overlap(items, pr, lambda r: f"no tube overlaps a printer part: {len(r.hits)} {r.hits[:8]}", exclude=skip)
    low = [(o.Label, em.shapes[o.Name]) for o in parts if em.boxes[o.Name].ZMin < top + LOW]
    p.log(f"EMU parts within {LOW:.0f} mm of its bottom: {len(low)}")
    p.no_overlap(low, pr, lambda r: f"no low EMU part overlaps a printer part: {len(r.hits)} {r.hits[:8]}", exclude=skip)
    # clearance from each tube's centre line: >= R_T from every printer part near it (booleans on these sweeps gave
    # 0 for a real 1.25 mm overlap in emu-3, and a volume outside both shapes here: LESSONS.md)
    for o, sw, L, r, edge in made:
        bx = FreeCAD.BoundBox(sw.BoundBox); bx.enlarge(1.0)
        cand = [c for c in pr.leaves if c.Name not in skip and pr.boxes[c.Name].intersect(bx)]
        tight = [(c.Label, round(d, 3)) for c in cand for d in [pr.shapes[c.Name].distToShape(edge)[0]] if d < eb.R_T + 0.01]
        p.check(not tight, f"{o.Label[:14]}: centre line >= {eb.R_T:.2f} mm off the {len(cand)} printer parts near it ({tight[:4]})")
    for a in range(len(made)):
        for b in range(a + 1, len(made)):
            v = made[a][1].common(made[b][1]).Volume
            p.check(v < 1e-3, f"tube {a + 1} vs tube {b + 1}: {v:.4f} mm3")
    p.dump({"dz": dz, "printer": os.path.basename(pr.doc.FileName),
            "tubes": [{"label": o.Label, "length": round(L), "min_radius": round(r, 1)} for o, s, L, r, _ in made],
            "total_ptfe_mm": round(sum(L for _, _, L, _, _ in made))})
    return p.finish([(ed, EMU4)])


litelib.Pass("emu4_lower").run(main)
