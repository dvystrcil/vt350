# GUI pass: vt350-lite-32 -> vt350-lite-33   (headless = dry run, never saves)
# vt350#19 AC7 follow-up (user, 2026-11-14): "plastic fatigues, and the weight of the toolhead will make the hanger bend
# forward" -- lite-32's keyslot brackets and the slots 3+4 hanger hold the bar's FRONT face only. A head weighs ~350 g
# (user: an LH Stinger head, a little less plastic, 289 g without its control board; + the O2S board, the filament
# sensor and the dock bosses), and it hangs BEHIND the bar: each keyslot plate pivots on its front top edge under the
# bar, its rear drops, and its lower front pushes the bracket forward -- constant bending in printed plastic (creep).
# And the bigger load (user, 2026-11-14): at pickup the carriage's magnets tug the head REARWARD; a bracket that rocks
# lets the holders catch and the carriage not seat, and the head falls. So each bracket becomes a SADDLE CLAMPED TO
# BOTH FACES of the bar (user's choice): its front M5 in the front T-slot (lite-32) plus a rear leg behind the bar with
# an M3 into an M3 T-nut in the REAR T-slot, joined by a bridge over the bar's top. Rocking about either bottom edge is
# then stopped by the aluminium in bearing (front face one way, rear face the other), not by plastic in bending.
#  - Slots 1, 2, 5 (side brackets): the web on the plate's outer face holds the plate with 4 x M3 BEHIND the bar's rear
#    face (heat-sets at Y -54.26/-45.26). It gains a rear leg (RL deep behind the bar, from the plate's top to the
#    bridge's top) with the rear M3 (counterbored from behind), and a bridge over the bar's top (over the bar only).
#    The leg covers the web and the plate up to KNOB_Z; above it, slot 2's covers the plate + 2 mm only, because slot 1
#    detaches toward it and slot 1's Orbiter knob (Z 480..492) then passes 2.42 mm from it (dry run, 2026-11-14).
#    Slots 1 and 5 sit next to the bar end brackets: the bridge is clipped 1 mm clear of them, and the end brackets are
#    trimmed 1 mm clear of the legs. Rear screws are M3 (an M4 counterbore doesn't fit slot 2's 8 mm leg top).
#  - Slots 3+4 (the printed pair + hanger): the hanger gains a bridge over the bar and a rear block on the pair's top
#    behind the bar (inside the plates' outer faces by 2 mm, as its lower block) with the rear M3, counterbored from the
#    block's back. No screw into the pair's top: the keyslot plates are hollow there (probe, 2026-11-14), and clamped
#    both faces the hanger holds the pair through lite-32's 2 front M3s.
#  - Same labels, groups, material; the bar, the plates and every other part unchanged. Rear T-slot: 4 x M3 T-nut + M3x10
#    SHCS (the heads pass 2.00 mm behind the bar's rear face at the keyslot slide, so only between heads).
# Checks (refuses to save on any): each changed part is one valid solid and contains its lite-32 shape; it covers the
# bar's top and its rear face (the hook); it overlaps nothing in the printer (but its own lite-32 self) and no other
# changed part; the carried head of every slot (head + MadMax plate + tube + the empty carriage at the pickup) clears
# every changed part by >= 2 mm at every dock move (lite-32's 38 poses); each rear M3 lands on the bar's rear slot
# (centred on the slot, at the bar's mid-height); roles stay `printed`; solid count unchanged.
import FreeCAD, Part, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                if "__file__" in globals() else os.environ.get("VT350_REPO", "/home/dan/Code/vt350"),
                                "platform/freecad"))      # litelib, which puts the other code folders on the path
import litelib
from litelib import is_leaf, MODELS
SRC, DST = f"{MODELS}/vt350-lite-32.FCStd", f"{MODELS}/vt350-lite-33.FCStd"
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path.insert(0, f"{REPO}/platform/render")
import colours

V = FreeCAD.Vector
PAT = "LLRLR"
SLOTS = [("Left Toolhead", "Left Dock"), ("Toolhead slot 2 (L)", "Dock slot 2 (L)"), ("Toolhead slot 3 (R)", "Dock slot 3 (R)"),
         ("Toolhead slot 4 (L)", "Dock slot 4 (L)"), ("Right Toolhead", "Right Dock")]
BAR_LABEL = "2020 dock bar (front; holds the 5 keyslot plates, #19)"
SIDE = {1: "Dock bracket slot 1 (L) (keyslot plate to bar)", 2: "Dock bracket slot 2 (L) (keyslot plate to bar)",
        5: "Dock bracket slot 5 (R) (keyslot plate to bar)"}
HANGER, FILLER = "Dock pair hanger slots 3+4 (keyslot pair to bar)", "Dock pair filler slots 3+4 (prints with both keyslot plates)"
ENDS = ("Dock bar end bracket (left)", "Dock bar end bracket (right)")
SLIDE, CARRIED_DZ, DETACH = 6.0, -0.315, 5.0      # toolchanger.cfg keyslot slide / detach; carried vs docked (sweep_toolhead)
CLEAR = 2.0
DY_DETACH = range(-6, 61, 2)
DY_PARK = (-6, -4, -2, 0)
WEB_T, UP_W, TF, PL_T = 6.0, 14.0, 5.0, 6.0       # lite-32's web, upright reach, front plate; the keyslot plate's thickness
PAIR_W, PAIR_IN = 10.0, 2.0                       # lite-32's hanger upright reach past the pair; lower block inset
TT, RL = 5.0, 10.0                                # bridge thickness over the bar top; rear leg depth behind the bar
M3_R, M3_CB_R, UNDER_HEAD = 1.7, 3.0, 4.0         # rear M3: clearance hole, counterbore (head D5.5), plastic under the head
LEG_OUT = {1: 6.0, 2: 2.0, 5: 6.0}                # rear leg reach outboard of the plate ABOVE KNOB_Z: slot 2's faces slot 1's head,
KNOB_Z = 477.9                                    # whose Orbiter knob (Z 480.2..492.0, carried -0.315) comes over it at detach_x
END_CLEAR = 1.0


def tree(o):
    out = [o]
    for k in (getattr(o, 'Group', []) or []): out += tree(k)
    return out


def bx(x0, x1, y0, y1, z0, z1):
    x0, x1 = min(x0, x1), max(x0, x1)
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(r, p, d, h): return Part.makeCylinder(r, h, V(*p), V(*d))


def vbox(shape):
    b = FreeCAD.BoundBox()
    for v in shape.Vertexes: b.add(v.Point)
    return b


def box_gap(a, b):
    d = [max(0.0, a.XMin - b.XMax, b.XMin - a.XMax), max(0.0, a.YMin - b.YMax, b.YMin - a.YMax), max(0.0, a.ZMin - b.ZMax, b.ZMin - a.ZMax)]
    return (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5


def clip_x(x0, x1, ends):
    """[x0, x1] (any order) shortened to stay END_CLEAR off each end bracket box it reaches: an end box on the low
    side (its centre below the range's) raises lo, else it lowers hi."""
    lo, hi = min(x0, x1), max(x0, x1)
    for e in ends:
        if e.XMax <= lo - END_CLEAR or e.XMin >= hi + END_CLEAR: continue
        if (e.XMin + e.XMax) / 2 < (lo + hi) / 2: lo = max(lo, e.XMax + END_CLEAR)
        else: hi = min(hi, e.XMin - END_CLEAR)
    return lo, hi


def rear_m3(shape, x, bar, y_back):
    """An M3 along Y from y_back (the leg's back face) into the bar's rear slot at X x, the bar's mid-height:
    clearance hole through, counterbored from the back to leave UNDER_HEAD of plastic under the head."""
    zc = (bar.ZMin + bar.ZMax) / 2
    shape = shape.cut(cyl(M3_R, (x, bar.YMax - 1, zc), (0, 1, 0), y_back - bar.YMax + 2))
    return shape.cut(cyl(M3_CB_R, (x, bar.YMax + UNDER_HEAD, zc), (0, 1, 0), y_back - bar.YMax - UNDER_HEAD + 1))


def side_saddle(old, bar, kb, F, o, ends, out):
    """lite-32 side bracket + rear leg (behind the bar, plate top .. bridge top: over the web and the plate up to KNOB_Z,
    over the plate and `out` of the web above it, with the rear M3 there) + bridge (over the bar's top only, the front
    upright's X). F: the plate's outer face X; o: outward (L -1, R +1)."""
    yf, yr = bar.YMin - TF, bar.YMax + RL
    span = lambda w: (min(F + o * w, F - o * PL_T), max(F + o * w, F - o * PL_T))
    lo, lx = span(WEB_T), span(out)
    leg = bx(lo[0], lo[1], bar.YMax, yr, kb.ZMax, KNOB_Z).fuse(bx(lx[0], lx[1], bar.YMax, yr, kb.ZMax, bar.ZMax + TT))
    bxr = clip_x(F - o * PL_T, F + o * UP_W, ends)
    bridge = bx(bxr[0], bxr[1], yf, bar.YMax, bar.ZMax, bar.ZMax + TT)
    sh = rear_m3(old.fuse([leg, bridge]), (lx[0] + lx[1]) / 2, bar, yr)
    return sh.removeSplitter(), leg, (lx, bxr)


def pair_saddle(old_h, bar, ka, kb):
    """lite-32 hanger + bridge over the bar (its upright's X) + rear block on the pair's top behind the bar (inside the
    plates' outer faces by PAIR_IN), the rear M3 through it."""
    yf, xc = bar.YMin - TF, (ka.XMax + kb.XMin) / 2
    bridge = bx(ka.XMin - PAIR_W, kb.XMax + PAIR_W, yf, bar.YMax, bar.ZMax, bar.ZMax + TT)
    block = bx(ka.XMin + PAIR_IN, kb.XMax - PAIR_IN, bar.YMax, ka.YMax, ka.ZMax, bar.ZMax + TT)
    return rear_m3(old_h.fuse([bridge, block]), xc, bar, ka.YMax).removeSplitter(), xc


def main(p):
    pr = p.open(SRC); doc = pr.doc
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    cmap = colours.load(f"{REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    bar_o = obj(BAR_LABEL); bar = vbox(pr.shapes[bar_o.Name]); bar_s = pr.shapes[bar_o.Name]
    p.log(f"bar: {bar}")
    slots = []
    for i, (h, d) in enumerate(SLOTS, 1):
        ks = [o for o in tree(obj(d)) if is_leaf(o) and o.Label.startswith("Dock Asembly")]
        if len(ks) != 1: raise RuntimeError(f"{d}: {len(ks)} keyslot plates")
        k = PAT[i - 1]; kb = vbox(pr.shapes[ks[0].Name])
        F, o = (kb.XMin, -1) if k == "L" else (kb.XMax, +1)
        slots.append(dict(n=i, k=k, head=obj(h), dock=obj(d), ks=ks[0], kb=kb, F=F, o=o))
    ends = [vbox(pr.shapes[obj(lab).Name]) for lab in ENDS]
    p.log("end brackets:", [(round(e.XMin, 2), round(e.XMax, 2)) for e in ends])
    # --- the new shapes
    changed, legs = [], []                       # (object, new global shape); the side legs (for the end-bracket trim)
    for s in slots:
        if s["n"] not in SIDE: continue
        ob = obj(SIDE[s["n"]])
        sh, leg, (lx, bxr) = side_saddle(pr.shapes[ob.Name], bar, s["kb"], s["F"], s["o"], ends, LEG_OUT[s["n"]])
        p.log(f"slot {s['n']}: rear leg X {lx[0]:.2f}..{lx[1]:.2f}, bridge X {bxr[0]:.2f}..{bxr[1]:.2f}")
        p.check(bxr[1] - bxr[0] >= 8.0, f"slot {s['n']}: bridge {bxr[1] - bxr[0]:.2f} mm wide (>= 8 after the end-bracket clip)")
        p.check((lx[1] - lx[0]) - 2 * M3_CB_R >= 2.0, f"slot {s['n']}: rear leg {lx[1] - lx[0]:.2f} mm wide, "
                f"{((lx[1] - lx[0]) - 2 * M3_CB_R) / 2:.2f} mm walls beside the M3 counterbore (>= 1)")
        changed.append((ob, sh)); legs.append(leg)
    a, b = slots[2], slots[3]
    ho = obj(HANGER)
    hs, xc = pair_saddle(pr.shapes[ho.Name], bar, a["kb"], b["kb"])
    blk_w = (b["kb"].XMax - PAIR_IN) - (a["kb"].XMin + PAIR_IN)
    p.check(blk_w - 2 * M3_CB_R >= 2.0, f"pair rear block {blk_w:.2f} mm wide, {(blk_w - 2 * M3_CB_R) / 2:.2f} mm walls beside the M3 counterbore (>= 1)")
    changed.append((ho, hs))
    # the end brackets, trimmed END_CLEAR clear of the slot 1/5 rear legs
    for lab in ENDS:
        eo = obj(lab); es = pr.shapes[eo.Name]
        cut = [l for l in legs if l.BoundBox.intersect(FreeCAD.BoundBox(es.BoundBox.XMin - 2, es.BoundBox.YMin - 2, es.BoundBox.ZMin - 2,
                                                                         es.BoundBox.XMax + 2, es.BoundBox.YMax + 2, es.BoundBox.ZMax + 2))]
        if not cut: continue
        for l in cut:
            g = l.BoundBox
            es = es.cut(bx(g.XMin - END_CLEAR, g.XMax + END_CLEAR, g.YMin - END_CLEAR, g.YMax + END_CLEAR, g.ZMin - END_CLEAR, g.ZMax + END_CLEAR))
        es = es.removeSplitter()
        p.log(f"{lab}: trimmed {pr.shapes[eo.Name].Volume - es.Volume:.1f} mm3 clear of the rear leg")
        changed.append((eo, es))

    for ob, sh in changed:
        old = pr.shapes[ob.Name]
        p.check(sh.isValid() and len(sh.Solids) == 1, f"{ob.Label}: one valid solid, {old.Volume:.1f} -> {sh.Volume:.1f} mm3, {sh.BoundBox}")
        if ob.Label not in ENDS:
            p.check(old.cut(sh).Volume < 50.0, f"{ob.Label}: keeps its lite-32 shape (less only the rear M3 hole, "
                    f"{old.cut(sh).Volume:.1f} mm3)")
    # the hook: each saddle covers the bar's top and reaches down its rear face
    for ob, sh in changed:
        if ob.Label in ENDS: continue
        top = sh.common(bx(bar.XMin, bar.XMax, bar.YMin, bar.YMax, bar.ZMax, bar.ZMax + 0.1)).Volume
        rear = sh.common(bx(bar.XMin, bar.XMax, bar.YMax, bar.YMax + 0.1, bar.ZMin, bar.ZMax)).Volume
        p.check(top > 1.0 and rear > 1.0, f"{ob.Label}: on the bar's top ({top * 10:.0f} mm2) and down its rear face ({rear * 10:.0f} mm2)")
        p.check(sh.distToShape(bar_s)[0] < 0.01, f"{ob.Label}: sits on the bar")
    # --- static checks
    names = {ob.Name for ob, _ in changed}
    p.no_overlap([(ob.Label, sh) for ob, sh in changed], pr, lambda r: f"changed parts x printer (but their lite-32 selves): {r.hits[:6]}",
                 exclude=names)
    pairs = [(i, j) for i in range(len(changed)) for j in range(i + 1, len(changed)) if changed[i][1].BoundBox.intersect(changed[j][1].BoundBox)]
    vols = p.volumes([(changed[i][1], changed[j][1]) for i, j in pairs])
    hit = [(changed[i][0].Label, changed[j][0].Label, round(v, 3)) for (i, j), v in zip(pairs, vols) if v > 1e-3]
    p.check(not hit, f"changed parts x each other: {hit}")
    # --- every slot's carried head at the dock moves vs the changed parts (lite-32's method: distToShape is wrong for
    # some head solids here, so each result is raised to the box gap, a lower bound, and raised pairs are logged)
    tubes = {s["n"]: [o for o in tree(s["head"]) if is_leaf(o) and o.Label.startswith("Bowden")] for s in slots}
    tubes[1] = [o for o in tubes[1] if o.Label == "Bowden Left"]
    tubes[5] = [obj("Bowden Right")]
    car = {}
    for s in (slots[0], slots[-1]):
        car[s["k"]] = (s, [o for c in tree(s["dock"]) if c.TypeId == 'App::Part' and c.Label.startswith("Carriage")
                           for o in tree(c) if is_leaf(o)])
    new = [(ob.Label, sh) for ob, sh in changed]
    for s in slots:
        rs, cl = car[s["k"]]
        cdx = s["kb"].XMin - rs["kb"].XMin
        mine = [o for o in tree(s["head"]) + tree(s["dock"]) if is_leaf(o) and not o.Label.startswith(("Bowden", "Dock Asembly", "Dock bracket", "Dock pair"))
                and o.Name not in {c.Name for c in cl}] + tubes[s["n"]]
        group = [(o.Label, pr.shapes[o.Name]) for o in mine] + [(o.Label, pr.shapes[o.Name].translated(V(cdx, 0, 0))) for o in cl]
        det = DETACH if s["k"] == "L" else -DETACH
        poses = [(0.0, dy) for dy in DY_PARK] + [(det, dy) for dy in DY_DETACH]
        tasks, keys = [], []
        for dx, dy in poses:
            for lab, sh in group:
                m = sh.BoundBox; mb = FreeCAD.BoundBox(m.XMin + dx, m.YMin + dy, m.ZMin + CARRIED_DZ, m.XMax + dx, m.YMax + dy, m.ZMax + CARRIED_DZ)
                for plab, psh in new:
                    g = box_gap(mb, psh.BoundBox)
                    if g < CLEAR + 1.0:
                        tasks.append((psh, sh.translated(V(dx, dy, CARRIED_DZ)))); keys.append((f"{lab} @x{dx:+.0f} y{dy:+.0f}", plab, g))
        ds = p.map(litelib._t_dist, tasks)
        res, raised = [], []
        for (k, plab, g), d in zip(keys, ds):
            if isinstance(d, litelib._Err): raise RuntimeError(f"distToShape failed for {k} vs {plab}: {d.msg}")
            if d < g - 1e-6: raised.append((k, plab, round(d, 2), round(g, 2)))
            res.append((max(d, g), k, plab))
        if raised: p.log(f"slot {s['n']}: {len(raised)} distToShape results below their box gap, raised to it: {raised[:4]}")
        dmin = min(res)[0] if res else float("inf")
        near = sorted((round(d, 2), k, plab) for d, k, plab in res if d < CLEAR)
        p.log(f"slot {s['n']}: nearest {sorted((round(d, 2), k, plab) for d, k, plab in res)[:3]}")
        p.check(not near, f"slot {s['n']} ({s['k']}) carried head + carriage, {len(poses)} dock poses ({len(tasks)} pairs measured): "
                f"min {dmin:.2f} mm to the changed parts {near[:3]}")
    # --- write
    for ob, sh in changed:
        g = ob.getParentGeoFeatureGroup()
        ob.Shape = sh
        if g is not None: ob.Placement = g.getGlobalPlacement().inverse().multiply(ob.Placement)
    doc.recompute(); pr.refresh()
    for ob, sh in changed:
        d = abs(pr.shapes[ob.Name].Volume - sh.Volume)
        p.check(d < 1e-3 and pr.shapes[ob.Name].BoundBox.isInside(sh.BoundBox.Center), f"{ob.Label}: written in place (volume diff {d:.4f})")
    def gpath(o):
        r, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r))
    mat = lambda o: getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default'
    for ob, _ in changed:
        r_ = colours.role_of(cmap, ob.Label, gpath(ob), mat(ob))
        p.check(r_ == "printed", f"{ob.Label}: material {mat(ob)} -> role {r_}")
    p.check(len(pr.leaves) == n_before, f"solids: {n_before} -> {len(pr.leaves)} (unchanged)")
    p.dump({"parts": [dict(label=ob.Label, volume=round(sh.Volume, 1),
                           box=[round(v, 2) for v in (sh.BoundBox.XMin, sh.BoundBox.YMin, sh.BoundBox.ZMin,
                                                      sh.BoundBox.XMax, sh.BoundBox.YMax, sh.BoundBox.ZMax)]) for ob, sh in changed],
            "fasteners_added": {"M3x10 SHCS + M3 T-nut, bar rear slot (slots 1, 2, 5 legs; pair hanger block)": 4},
            "design_load_per_head_g": 350})
    p.finish([(doc, DST)])


litelib.Pass("lite33_dock_saddles").run(main)
