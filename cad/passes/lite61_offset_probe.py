# GUI pass: vt350-lite-60 -> vt350-lite-61   (headless = dry run, never saves)
# vt350#186. The nozzle offset calibration probe goes on the front of the bed (owner, 2026-11-16: "don't forget to add
# the offset nozzel calibration to the front of the bed"). #186 picked the Mellow MultiHead Zero (West3D MEL2020) in
# place of MadMax's Nudge; Mellow shows it fixed to the bed's edge, its ball just above the plate.
#  - The Zero, as Mellow's drawing gives it (~/Documents/VT350/references/toolhead/mellow-multihead-zero): an aluminium
#    body 20 x 17.2 x 22 tall; the probe 23 above it. The probe's parts are ESTIMATED from the photo: a D 13 bushing
#    10 tall, a D 5 pin, a D 10 ball on top. Its two counterbored through-holes cross the 20 mm face (M3 assumed).
#  - Where: in front of the plate (Y 28..383, magnet top Z 287.16), centred on it in X (-245). Ball centre Y 18, so the
#    bushing clears the plate's front edge by 2.5 and the ball by 5; ball centre 5 above the magnet top (the spring
#    steel sheet, not modelled, adds ~1), so a nozzle touching the ball's side from the rear is still above the plate.
#    The body's 20 mm mounting face looks to the rear; its top (Z 274.2) is below the plate (275.8).
#  - The bed has nothing at its front edge: its front 2020 (X -480..-10, Y 60.8..80.8, Z 240..260) is 33 mm behind the
#    plate's front edge. A PRINTED BRACKET (ABS): a back plate on the 2020's front face (2 x M3 + T-nut into its slot,
#    Z 250), an arm forward under the plate's overhang, and a front plate the Zero bolts to (2 x M3x25 + nut, through
#    the body's holes; positions read from the photo, to confirm on the part). It keeps >= 3 mm below the heater pad.
# Hardware (listed, not modelled): 2 x M3x8 + T-nut (bracket to the bed frame), 2 x M3x25 + nut (the Zero to the bracket).
# Checks (refuses to save on any): the plate, heater and the bed's front 2020 where expected; each new part one valid
# solid; nothing overlaps a lite-60 part (envelopes excepted) or another new part; the back plate sits on the 2020's
# face; >= 3 mm under the heater pad; the bushing and ball clear the plate's edge; the ball's equator >= 4 mm above the
# magnet top; the nozzle can reach every side of the ball (print square X, the nozzles' Y reach); over the bed's whole Z
# travel (BED_LOWEST_DZ .. plate at the nozzle) the probe and bracket hit no part that doesn't move with the bed (the
# docks, the docked heads, the frame); colour roles; solids = lite-60 + 4.
import FreeCAD, Part, os, sys, re
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "platform/render")]
import litelib, linkgeo, colours
from litelib import MODELS, BED_LOWEST_DZ, BED_Z
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-60.FCStd", f"{MODELS}/vt350-lite-61.FCStd"
PLATE, MAGNET, HEATER, BED2020 = "LDO 350 build plate", "Magnetic sheet", "Heater pad LDO", "2020 (1)"
X0, BALL_Y, BALL_D, BALL_UP = -245.0, 18.0, 10.0, 5.0
BODY_X, BODY_Y, BODY_H, PROBE_H = 20.0, 17.2, 22.0, 23.0
BUSH_D, BUSH_H, PIN_D = 13.0, 10.0, 5.0
T, HEATER_GAP = 4.0, 3.0
PRINT_X = (-420.0, -70.0)                      # the print square (sweep_toolhead.py), both heads
LIC = "(printed ABS, vt350, GPL-3.0-or-later)"


def bx(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    cmap = colours.load(f"{_REPO}/cad/render/colours.json")
    n0 = len(pr.leaves)
    one = lambda pre: [o for o in pr.leaves if o.Label.startswith(pre)]
    pl, mg, ht = one(PLATE), one(MAGNET), one(HEATER)
    fr = [o for o in pr.leaves if o.Label == BED2020 and pr.boxes[o.Name].ZMin > 200 and pr.boxes[o.Name].YMax < 100]
    p.check(len(pl) == len(mg) == len(ht) == len(fr) == 1, f"plate {len(pl)}, magnet {len(mg)}, heater {len(ht)}, bed front 2020 {len(fr)}")
    pb, mb, hb, fb = (pr.boxes[o[0].Name] for o in (pl, mg, ht, fr))
    p.check(abs(pb.YMin - 28) < 0.1 and abs(mb.ZMax - 287.16) < 0.05 and abs(fb.YMin - 60.8) < 0.1 and abs(fb.ZMin - 240) < 0.1,
            f"plate front Y {pb.YMin:.2f}, magnet top Z {mb.ZMax:.2f}, bed front 2020 face Y {fb.YMin:.2f} Z {fb.ZMin:.1f}..{fb.ZMax:.1f}")
    top = mb.ZMax
    # the read-in nozzle reach (sweep_toolhead's log): the probe must sit where every head's nozzle gets to
    ylog = open(f"{_REPO}/cad/data/logs/sweep_toolhead.log").read()
    reach = [tuple(map(float, m)) for m in re.findall(r"carried: .*?nozzle Y reach (-?[0-9.]+) \.\. (-?[0-9.]+)", ylog)]
    nz = [float(z) for z in re.findall(r"carried: nozzle tip Z ([0-9.]+)", ylog)]
    p.check(len(reach) >= 2 and len(nz) >= 2, f"nozzle reach from sweep_toolhead.log: Y {reach}, tip Z {nz}")
    y_lo, y_hi = max(r[0] for r in reach), min(r[1] for r in reach)
    bed_top_dz = min(nz) - top                      # the bed's top of travel: the plate at the nozzle
    # ---- the Zero
    bz = top + BALL_UP                                       # ball centre
    ball_top = bz + BALL_D / 2
    body_top = ball_top - PROBE_H; body_bot = body_top - BODY_H
    body = bx(X0 - BODY_X / 2, X0 + BODY_X / 2, BALL_Y - BODY_Y / 2, BALL_Y + BODY_Y / 2, body_bot, body_top)
    bush = Part.makeCylinder(BUSH_D / 2, BUSH_H, V(X0, BALL_Y, body_top))
    pin = Part.makeCylinder(PIN_D / 2, bz - (body_top + BUSH_H), V(X0, BALL_Y, body_top + BUSH_H))
    ball = Part.makeSphere(BALL_D / 2, V(X0, BALL_Y, bz))
    probe = bush.fuse([pin, ball]).removeSplitter()
    # ---- the bracket: back plate on the 2020's face, arm, front plate behind the body
    yb = BALL_Y + BODY_Y / 2                                 # the body's rear (mounting) face
    zc_top = hb.ZMin - HEATER_GAP                            # nothing of the bracket above this (heater pad)
    back = bx(X0 - 15, X0 + 15, fb.YMin - T, fb.YMin, fb.ZMin, fb.ZMax)
    front = bx(X0 - 12, X0 + 12, yb, yb + T, body_bot - 4, min(zc_top, body_top))
    arm = bx(X0 - 8, X0 + 8, yb, fb.YMin - T, fb.ZMin + 6, fb.ZMin + 16)
    rib = bx(X0 - 2, X0 + 2, yb + T, fb.YMin - T, fb.ZMin + 16, min(zc_top, fb.ZMax))   # a web on the arm, stiffer in Z
    holes = [Part.makeCylinder(1.7, T + 2, V(X0 + dx, fb.YMin - T - 1, (fb.ZMin + fb.ZMax) / 2), V(0, 1, 0)) for dx in (-10, 10)]
    zc = (body_bot + body_top) / 2
    holes += [Part.makeCylinder(1.7, T + 2, V(X0 + dx, yb - 1, zc + dz), V(0, 1, 0)) for dx, dz in ((-5, 5), (5, -5))]
    bracket = back.fuse([front, arm, rib]).cut(Part.makeCompound(holes)).removeSplitter()
    root = pr.root("4040-350x350x250 Voron Trident")
    grp = doc.addObject("App::Part", "OffsetProbe"); grp.Label = "Nozzle offset probe (lite-61, #186)"
    root.addObject(grp)
    made = []
    def add(name, label, s):
        p.check(s.isValid() and len(s.Solids) == 1, f"{label[:50]}: one valid solid ({len(s.Solids)}), {s.Volume:.0f} mm3")
        o = doc.addObject("Part::Feature", name); grp.addObject(o)
        loc = s.copy(); loc.Placement = linkgeo.gplace(grp).inverse().multiply(loc.Placement)
        o.Shape = loc; o.Label = label; made.append(o); return o
    add("MHZ_body", "Mellow MultiHead Zero body (aluminium, 20 x 17.2 x 22, from Mellow's drawing)", body)
    add("MHZ_probe", "Mellow MultiHead Zero probe (bushing, pin, D 10 ball; estimated from the photo)", probe)
    add("MHZ_switch", "Mellow MultiHead Zero switch + XH2.54 plug (in the body's slot, stand-in)",
        bx(X0 - 4, X0 + 4, BALL_Y - BODY_Y / 2 - 6, BALL_Y - BODY_Y / 2, body_bot, body_bot + 6))
    add("Probe_bracket", f"Nozzle offset probe bracket {LIC}", bracket)
    doc.recompute(); pr.refresh()
    mine = {o.Name for o in made}
    env = {o.Name for o in pr.leaves if "envelope" in o.Label}
    # ---- checks
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in made], pr, lambda r: f"no new part overlaps a lite-60 part: {len(r.hits)} {r.hits[:8]}",
                 exclude=env | mine)
    for i, a in enumerate(made):
        for b in made[i + 1:]:
            v = pr.shapes[a.Name].common(pr.shapes[b.Name]).Volume
            p.check(v < 1e-3, f"{a.Label[:28]} vs {b.Label[:28]}: {v:.4f} mm3")
    d = pr.shapes[made[-1].Name].distToShape(pr.shapes[fr[0].Name])[0]
    p.check(d < 1e-3, f"the bracket's back plate sits on the bed 2020's face (gap {d:.4f})")
    zmax_br = pr.boxes[made[-1].Name].ZMax
    p.check(hb.ZMin - zmax_br >= HEATER_GAP - 1e-6, f"bracket top Z {zmax_br:.1f}: {hb.ZMin - zmax_br:.1f} below the heater pad (>= {HEATER_GAP})")
    gap_b, gap_ball = pb.YMin - (BALL_Y + BUSH_D / 2), pb.YMin - (BALL_Y + BALL_D / 2)
    p.check(gap_b >= 2 and gap_ball >= 4, f"the bushing clears the plate's front edge by {gap_b:.1f}, the ball by {gap_ball:.1f}")
    p.check(bz - top >= 4, f"ball centre (its equator) Z {bz:.2f}: {bz - top:.2f} above the magnet top (>= 4)")
    side = BALL_D / 2 + 5                                      # a nozzle 5 mm off the ball's side, each way
    p.check(PRINT_X[0] <= X0 - side and X0 + side <= PRINT_X[1] and y_lo <= BALL_Y - side and BALL_Y + side <= y_hi,
            f"nozzle reaches all 4 sides: X {X0 - side:.0f}..{X0 + side:.0f} in {PRINT_X}, Y {BALL_Y - side:.0f}..{BALL_Y + side:.0f} in {y_lo:.1f}..{y_hi:.1f}")
    # the bed's whole Z travel: the swept box of the new parts against everything that doesn't move with the bed
    allb = FreeCAD.BoundBox()
    for o in made: allb.add(pr.boxes[o.Name])
    sweep = bx(allb.XMin, allb.XMax, allb.YMin, allb.YMax, allb.ZMin + BED_LOWEST_DZ, allb.ZMax + bed_top_dz)
    bedside = lambda b: BED_Z[0] <= b.ZMin <= BED_Z[1] and b.ZMax <= BED_Z[1]
    hits = []
    for o in pr.leaves:
        b = pr.boxes[o.Name]
        if o.Name in mine or o.Name in env or bedside(b) or not b.intersect(sweep.BoundBox): continue
        if sweep.common(pr.shapes[o.Name]).Volume > 1e-3: hits.append(o.Label[:40])
    p.check(not hits, f"over the bed's Z travel (dZ {BED_LOWEST_DZ:.1f} .. +{bed_top_dz:.2f}), the probe's swept box "
                      f"X {allb.XMin:.0f}..{allb.XMax:.0f} Y {allb.YMin:.0f}..{allb.YMax:.0f} hits no fixed part: {len(hits)} {hits[:10]}")
    p.check(all(bedside(pr.boxes[o.Name]) for o in made), "every new part is bed-side by the motion code's Z band (moves with the bed)")
    def gpath(o):
        r_, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r_.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r_))
    roles = {o.Label.split(" (")[0]: colours.role_of(cmap, o.Label, gpath(o), "Default") for o in made}
    p.check(roles == {"Mellow MultiHead Zero body": "brushed_aluminium", "Mellow MultiHead Zero probe": "brushed_steel",
                      "Mellow MultiHead Zero switch + XH2.54 plug": "black_plastic", "Nozzle offset probe bracket": "printed"},
            f"roles {roles}")
    p.check(len(pr.leaves) == n0 + 4, f"lite-61 solids: {len(pr.leaves)} (lite-60 {n0} + 4)")
    p.dump({"ball_centre": [X0, BALL_Y, round(bz, 2)], "body_z": [round(body_bot, 2), round(body_top, 2)],
            "bed_top_dz": round(bed_top_dz, 2), "y_reach": [y_lo, y_hi], "swept_box": [allb.XMin, allb.XMax, allb.YMin, allb.YMax],
            "hardware": "2 x M3x8 + T-nut (bracket to bed 2020), 2 x M3x25 + nut (Zero to bracket)"})
    return p.finish([(doc, DST)])


litelib.Pass("lite61_offset_probe").run(main)
