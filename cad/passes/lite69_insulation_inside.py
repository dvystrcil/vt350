# GUI pass: vt350-lite-68 -> vt350-lite-69   (headless = dry run, never saves)   vt350#4, #14
# The roof and back insulation move inside the printer. lite-16 put the owner's carbon-felt pads (10 mm, sealed in
# aluminium foil both faces) OUTSIDE the roof and back panels; the owner, 2026-11-18, after the whole-printer turntable
# (#220): "move the insulation to the opposite side of the panel so its on the inside of the printer". Each stack (felt
# + inner and outer liner, and the roof strip) moves straight across its panel, by a plain translation, until its top
# (roof) / rear (back) face lies on the panel's inside face. The right wall pad already sits inside its panel: logged,
# not moved. Labels keep their meaning: the "inner" liner is the one nearer the panel before, the chamber after.
# The back has only ~5 mm between the frame's rear face and the panel; the 10 mm pad would cut into the rear 2020s,
# the A/B motors and mounts, and the moving rear Z carriage and chain. Owner, 2026-11-18: "I will test how well the
# insulation compresses, for now consider the rear insulation as thinner". So the back felt is rebuilt THINNER, to fill
# the gap exactly (placeholder until the compression test): its own box, no longer a link to the roof felt. The roof
# strip gets a hole for each bowden tube and O2S USB cable that crosses it (lite-16: "the roof needs pass-throughs").
# The EMU envelope comes down onto the roof panel with it (owner, 2026-11-18), named emu-4 (emu4_lower.py).
# Checks (refuses to save on any):
#  - 9 parts found (roof pad + strip with 2 liners each, back pad with 2 liners), Part::Features or App::Links;
#  - each roof part's box moved by exactly dz, each back part's by dy; the stacks' faces on the panels' inside faces;
#  - every other solid's box unchanged, the count unchanged;
#  - the back felt was a box (volume = its box's), the new one is gap-thick, the stack's front on the frame's rear face;
#  - holes only where a bowden tube or O2S USB cable crosses the roof strip (anything else hitting it fails);
#  - the EMU envelope = the EMU's box lowered onto the roof's top (paint included);
#  - no NEW overlap between a moved part and any other solid (overlaps that existed before are listed, not failed).
import FreeCAD, Part, os, re, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
from litelib import MODELS
SRC, DST = f"{MODELS}/vt350-lite-68.FCStd", f"{MODELS}/vt350-lite-69.FCStd"
EMU3 = f"{MODELS}/vt350-emu-3.FCStd"           # read only: the EMU's own box, for its envelope
GROUP = "Insulation: carbon felt sealed in aluminium"
ROOF = re.compile(r"^Roof felt (\(pad 1\)|liner, |strip)")
BACK = re.compile(r"^Back felt ")
ROOF_PANEL, BACK_PANEL = re.compile(r"^Roof panel \(3 mm\)$"), re.compile(r"^Back Panel001$")
TOL = 1e-3
REAR_FACE = re.compile(r"^2020 \(3\)$")   # the rear vertical 2020 behind the back pad
HOLE_OK = re.compile(r"^(Bowden (Left|Right|slot \d)|O2S USB cable slot \d) ")
HOLE_OK2 = re.compile(r"^Bowden (Left|Right|slot \d)$")
CLEAR = 1.0                  # mm round each hole
GAP = 0.5                    # mm: 'on the face' before the move (lite-16 placed them by hand)


def bb(s): return s.BoundBox


def main(p):
    pr = p.open(SRC); doc = pr.doc
    ins = [o for o in pr.leaves if any(g.Label == GROUP for g in o.InListRecursive)]
    roof = [o for o in ins if ROOF.match(o.Label)]
    back = [o for o in ins if BACK.match(o.Label)]
    rest = [o for o in ins if o not in roof and o not in back]
    p.check(len(roof) == 6 and len(back) == 3, f"6 roof + 3 back parts ({len(roof)}, {len(back)}: {[o.Label for o in roof + back]})")
    # 5 of the 9 are App::Links (lite-51): a link and its master each move by their own Placement; moving a master
    # never moves its links (LESSONS.md), and the box check below proves each one landed where it should.
    p.check(all(o.TypeId in ("Part::Feature", "App::Link") for o in roof + back), "all Part::Features or App::Links")
    rp = [o for o in pr.leaves if ROOF_PANEL.match(o.Label)]; bp = [o for o in pr.leaves if BACK_PANEL.match(o.Label)]
    p.check(len(rp) == 1 and len(bp) == 1, f"one roof panel, one back panel ({len(rp)}, {len(bp)})")
    if p.errs: return p.finish([])
    # the panels' plain BoundBox is loose (the roof panel's read 8.1 mm for 3 mm): use the optimal boxes (LESSONS.md)
    rpb, bpb = pr.boxes[rp[0].Name], pr.boxes[bp[0].Name]
    r0 = min(bb(pr.shapes[o.Name]).ZMin for o in roof); r1 = max(bb(pr.shapes[o.Name]).ZMax for o in roof)
    b0 = min(bb(pr.shapes[o.Name]).YMin for o in back); b1 = max(bb(pr.shapes[o.Name]).YMax for o in back)
    p.log(f"roof panel Z {rpb.ZMin:.3f}..{rpb.ZMax:.3f}; roof stack Z {r0:.3f}..{r1:.3f}")
    p.log(f"back panel Y {bpb.YMin:.3f}..{bpb.YMax:.3f}; back stack Y {b0:.3f}..{b1:.3f}")
    p.check(abs(r0 - rpb.ZMax) < GAP, f"before: the roof stack sits on the roof panel's outside (top) face (gap {r0 - rpb.ZMax:.3f})")
    p.check(abs(b0 - bpb.YMax) < GAP, f"before: the back stack sits on the back panel's outside (rear) face (gap {b0 - bpb.YMax:.3f})")
    for o in rest:
        b = bb(pr.shapes[o.Name]); p.log(f"not moved: {o.Label}  X {b.XMin:.1f}..{b.XMax:.1f}")
    if p.errs: return p.finish([])
    dz = (rpb.ZMin - (r1 - r0)) - r0
    dy = (bpb.YMin - (b1 - b0)) - b0
    p.log(f"move: roof dz {dz:.3f}, back dy {dy:.3f}")
    rf = [o for o in pr.leaves if REAR_FACE.match(o.Label)]
    p.check(len(rf) == 1, f"the rear vertical 2020 found ({len(rf)})")
    if p.errs: return p.finish([])
    # the stack's front: the rearmost face of anything inside the panel within the pad's footprint (the A/B motors
    # stand ~0.05 mm proud of the 2020s' rear face)
    fp = bb(pr.shapes[next(o for o in back if o.Label == "Back felt (pad 2)").Name])
    near = [(pr.boxes[o.Name].YMax, o.Label) for o in pr.leaves
            if o.Name not in {x.Name for x in ins} and o.Name != bp[0].Name and not o.Label.startswith(bp[0].Label)
            and pr.boxes[o.Name].YMax < bpb.YMin + TOL and pr.boxes[o.Name].YMax > bpb.YMin - 20
            and pr.boxes[o.Name].XMax > fp.XMin and pr.boxes[o.Name].XMin < fp.XMax
            and pr.boxes[o.Name].ZMax > fp.ZMin and pr.boxes[o.Name].ZMin < fp.ZMax]
    face, who = max(near)
    p.log(f"rear 2020 face Y {pr.boxes[rf[0].Name].YMax:.3f}; rearmost part behind the pad: {who} at Y {face:.3f}")
    felt = next(o for o in back if o.Label == "Back felt (pad 2)")
    inner = next(o for o in back if o.Label == "Back felt liner, inner")
    fb = bb(pr.shapes[felt.Name]); fs = pr.shapes[felt.Name]
    p.check(abs(fs.Volume - fb.XLength * fb.YLength * fb.ZLength) < 1e-3 * fs.Volume, f"the back felt is a box ({fs.Volume:.0f} mm3)")
    shrink = face - (b0 + dy)                     # how far the stack's front would sit inside the frame
    t = fb.YLength - shrink
    p.log(f"frame rear face Y {face:.3f}; gap to the panel {bpb.YMin - face:.3f}; back felt {fb.YLength:.3f} -> {t:.3f} mm")
    p.check(0 < t < fb.YLength, f"a thinner back felt fits ({t:.3f} mm)")
    if p.errs: return p.finish([])
    moved = {o.Name: FreeCAD.Vector(0, 0, dz) for o in roof}
    moved.update({o.Name: FreeCAD.Vector(0, dy, 0) for o in back})
    moved[inner.Name] = FreeCAD.Vector(0, dy + shrink, 0)          # the chamber-side liner follows the thinner felt
    # the EMU comes down onto the roof (owner, 2026-11-18: "lower the EMU onto the roof panel"): the EMU itself in
    # cad/passes/emu4_lower.py (emu-3 -> emu-4); here its envelope, rebuilt to the lowered EMU's own box (lite-55's was
    # 8 mm deeper than the EMU: its rubber feet are at Z 712.1, the envelope's bottom at 704), named emu-4 (z_sweep
    # reads the name). The roof's top is its paint layer's (0.2 mm over the panel).
    env = [o for o in pr.leaves if o.Label.startswith("EMU envelope")]
    paint = [o for o in pr.leaves if o.Label == rp[0].Label + " paint, outside"]
    p.check(len(env) == 1 and len(paint) == 1, f"one EMU envelope, one roof paint layer ({len(env)}, {len(paint)})")
    if p.errs: return p.finish([])
    env = env[0]; roof_top = max(rpb.ZMax, pr.boxes[paint[0].Name].ZMax)
    em = p.open(EMU3)
    body = [o for o in em.leaves if not any(g.Label.startswith("Bowdens") for g in o.InListRecursive)]
    eb0 = FreeCAD.BoundBox()
    for o in body: eb0.add(em.boxes[o.Name])
    dze = roof_top - eb0.ZMin
    p.log(f"EMU (emu-3, {len(body)} parts): Z {eb0.ZMin:.3f}..{eb0.ZMax:.3f}; roof top {roof_top:.3f}; dz {dze:.3f}")
    p.check(-25 < dze < 0, f"the EMU comes down a little ({dze:.3f} mm)")
    if p.errs: return p.finish([])
    ebn = FreeCAD.BoundBox(eb0.XMin, eb0.YMin, eb0.ZMin + dze, eb0.XMax, eb0.YMax, eb0.ZMax + dze)
    FreeCAD.closeDocument(em.doc.Name)
    env_name = env.Name
    p.resize_envelope(pr, env, ebn, "EMU envelope (contents in vt350-emu-4.FCStd)")
    moved[env_name] = FreeCAD.Vector()               # in the overlap check; its box is checked below, not the move
    # overlaps before, of these parts at their NEW place, are what this pass adds; at the old place, what was there
    others = [o for o in pr.leaves if o.Name not in moved]
    def overlaps(model):
        cand = [(n, o) for n in moved for o in others
                if model.boxes[o.Name].intersect(model.shapes[n].BoundBox)]
        vols = p.volumes([(model.shapes[n], model.shapes[o.Name]) for n, o in cand])
        return {(doc.getObject(n).Label, o.Label): round(v, 1) for (n, o), v in zip(cand, vols) if v > TOL}
    before = overlaps(pr)
    for k, v in sorted(before.items()): p.log(f"  overlap before: {k[0]} x {k[1]}: {v} mm3")
    box0 = {n: bb(s) for n, s in pr.shapes.items()}; n0 = len(pr.leaves)
    for n, v in moved.items():
        o = doc.getObject(n); par = o.getParentGeoFeatureGroup()
        pp = par.getGlobalPlacement() if par else FreeCAD.Placement()
        o.Placement = pp.inverse().multiply(FreeCAD.Placement(v, FreeCAD.Rotation())).multiply(pp).multiply(o.Placement)
    # the back felt: a new gap-thick box in place of the link, same Name/Label/group/material/colour
    gname, glabel, grp = felt.Name, felt.Label, felt.getParentGeoFeatureGroup()
    master = felt.LinkedObject if felt.TypeId == "App::Link" else felt
    mat = getattr(master, "ShapeMaterial", None)
    look = list(master.ViewObject.ShapeAppearance) if FreeCAD.GuiUp and hasattr(master.ViewObject, "ShapeAppearance") else None
    rear = fb.YMax + dy
    gp = grp.getGlobalPlacement() if grp else FreeCAD.Placement()
    bx = Part.makeBox(fb.XLength, t, fb.ZLength, FreeCAD.Vector(fb.XMin, rear - t, fb.ZMin))
    back_names = [o.Name for o in back]
    doc.removeObject(gname)
    nf = doc.addObject("Part::Feature", gname)
    p.check(nf.Name == gname, f"the new back felt keeps the Name {gname} ({nf.Name})")
    nf.Label = glabel; nf.Shape = bx
    nf.Placement = gp.inverse()                   # the box is built global: undo the group's placement (LESSONS.md)
    if grp: grp.addObject(nf)
    if mat is not None: nf.ShapeMaterial = mat
    if look is not None: nf.ViewObject.ShapeAppearance = look
    doc.recompute(); pr.refresh()
    back = [doc.getObject(n) for n in back_names]
    p.check(abs(pr.shapes[gname].Volume - fb.XLength * t * fb.ZLength) < 1e-3 * fs.Volume,
            f"the new back felt is {fb.XLength:.0f} x {t:.3f} x {fb.ZLength:.0f} mm")
    nb = bb(pr.shapes[gname])
    p.check(abs(nb.YMax - rear) < TOL and abs(nb.XMin - fb.XMin) < TOL and abs(nb.ZMin - fb.ZMin) < TOL,
            f"the new back felt sits where the old one's rear face went (Y {nb.YMin:.3f}..{nb.YMax:.3f})")
    # holes in the roof strip (felt + its two liners) for whatever crosses it: only bowden tubes and USB cables
    strip = [o for o in roof if o.Label.startswith("Roof felt strip")]
    sb = [bb(pr.shapes[o.Name]) for o in strip]
    band = Part.makeBox(max(b.XMax for b in sb) - min(b.XMin for b in sb), max(b.YMax for b in sb) - min(b.YMin for b in sb),
                        max(b.ZMax for b in sb) - min(b.ZMin for b in sb) - 2 * TOL,
                        FreeCAD.Vector(min(b.XMin for b in sb), min(b.YMin for b in sb), min(b.ZMin for b in sb) + TOL))
    hits = [o for o in pr.leaves if o.Name not in moved and o.Name != gname and pr.boxes[o.Name].intersect(band.BoundBox)
            and p.vol(band, pr.shapes[o.Name]) > TOL]
    odd = [o.Label for o in hits if not (HOLE_OK.match(o.Label) or HOLE_OK2.match(o.Label))]
    p.check(not odd, f"only bowden tubes and USB cables cross the roof strip ({len(hits)}; others: {odd})")
    if p.errs: return p.finish([])
    cutters = []
    for o in hits:
        c = band.common(pr.shapes[o.Name]).BoundBox
        cutters.append(Part.makeBox(c.XLength + 2 * CLEAR, c.YLength + 2 * CLEAR, band.BoundBox.ZLength + 2,
                                    FreeCAD.Vector(c.XMin - CLEAR, c.YMin - CLEAR, band.BoundBox.ZMin - 1)))   # only the strip is cut
    cut = cutters[0].multiFuse(cutters[1:]) if len(cutters) > 1 else cutters[0]
    p.log(f"roof strip: {len(hits)} holes ({', '.join(o.Label.split(' (')[0] for o in hits)})")
    for o in strip:
        if o.TypeId == "App::Link": continue            # the outer liner links the inner: the master's holes show in it
        par = o.getParentGeoFeatureGroup(); C = par.getGlobalPlacement() if par else FreeCAD.Placement()
        P0 = FreeCAD.Placement(o.Placement)
        raw = o.Shape.copy(); raw.Placement = FreeCAD.Placement()
        cl = cut.copy(); cl.Placement = C.multiply(P0).inverse().multiply(cl.Placement)
        new = raw.cut(cl); new.Placement = P0
        v0 = o.Shape.Volume; o.Shape = new
        p.check(o.Placement.isSame(P0, 1e-9), f"{o.Label}: Placement kept (its links stay put)")
        p.log(f"  {o.Label}: volume {v0:.0f} -> {o.Shape.Volume:.0f} mm3")
    doc.recompute(); pr.refresh()
    bad = []
    for n, b in box0.items():
        if n in (gname, env_name): continue           # rebuilt: checked on their own
        v = moved.get(n, FreeCAD.Vector()); c = bb(pr.shapes[n])
        if any(abs(a - e) > TOL for a, e in zip((c.XMin, c.YMin, c.ZMin, c.XMax, c.YMax, c.ZMax),
                                                  (b.XMin + v.x, b.YMin + v.y, b.ZMin + v.z, b.XMax + v.x, b.YMax + v.y, b.ZMax + v.z))):
            bad.append(doc.getObject(n).Label)
    p.check(not bad, f"each moved part moved by exactly its offset, every other solid's box unchanged ({len(bad)}: {bad[:5]})")
    p.check(len(pr.leaves) == n0, f"solids {len(pr.leaves)} (was {n0})")
    r1n = max(bb(pr.shapes[o.Name]).ZMax for o in roof); b1n = max(bb(pr.shapes[o.Name]).YMax for o in back)
    p.check(abs(r1n - rpb.ZMin) < TOL, f"after: the roof stack's top on the roof panel's underside (Z {r1n:.3f})")
    p.check(abs(b1n - bpb.YMin) < TOL, f"after: the back stack's rear on the back panel's inside face (Y {b1n:.3f})")
    b0n = min(bb(pr.shapes[o.Name]).YMin for o in back)
    p.check(abs(b0n - face) < TOL, f"after: the back stack's front on the rearmost part behind it (Y {b0n:.3f})")
    after = overlaps(pr)
    for k, v in sorted(after.items()): p.log(f"  overlap after: {k[0]} x {k[1]}: {v} mm3")
    new = sorted({k[1] for k in after} - {k[1] for k in before})
    p.check(not new, f"no new overlap with another part ({len(new)}: {new})")
    eb1 = bb(pr.shapes[env_name])
    p.check(all(abs(a - b) < TOL for a, b in zip((eb1.XMin, eb1.YMin, eb1.ZMin, eb1.XMax, eb1.YMax, eb1.ZMax),
                                                  (ebn.XMin, ebn.YMin, ebn.ZMin, ebn.XMax, ebn.YMax, ebn.ZMax))),
            f"after: the EMU envelope is the lowered EMU's box, its bottom on the roof's top (Z {eb1.ZMin:.3f})")
    p.dump({"dz": dz, "dy": dy, "before": {" x ".join(k): v for k, v in before.items()},
            "after": {" x ".join(k): v for k, v in after.items()}})
    return p.finish([(doc, DST)])


litelib.Pass("lite69_insulation_inside").run(main)
