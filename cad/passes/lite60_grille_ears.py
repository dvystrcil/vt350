# GUI pass: vt350-lite-59 -> vt350-lite-60   (headless = dry run, never saves)
# vt350#5. The e-box front grille gets a fixing about every 10 cm, each an M3 screw into a T-nut in a frame slot
# (owner, 2026-11-16, on the lite-59 renders: "add ears to the grill so every 10cm or so we put a t-nut into the frame").
#  - TOP, BOTTOM, RIGHT: the grille already lies on frame there (the front long rails' faces, Z -50..-10 and 650..690;
#    the e-box front outer upright's face, X 140..160), so a 3.4 mm hole through the grille onto a slot: the rails'
#    outer slots (Z -40, Z 680) at X 60 and 110; the upright's slot (X 150) at 7 heights, clear of the band (the
#    e-box door's latch, notched) and of lite-47's M5 joint screws (Z -40, -20, 660, 680, inside the upright).
#  - LEFT: no frame behind the grille's left edge (X 30). A flat ear further left would sit in the 3 mm gap behind the
#    printer door's frame, under the closing door. So each LEFT EAR is an L: a 3 mm tab on the grille's back, folded
#    onto the printer's front-right upright's side face (the 2040's X 30 face, slot at Y -80), X 30..33, Y -90..-77
#    (1 mm short of the right side panel's front edge, Y -76), 16 tall; the M3 goes in along -X from inside the e-box
#    (through the e-box door). 7 heights, clear of the band (the printer door's latch). The panel edge limits the
#    ear to 3 mm past the slot centre: the M3 head (D 5.7) sits fully on it, with 1.3 mm of wall beside the hole.
#  - Each grille piece keeps its object, label and colour; the shape is reshaped in place.
# Hardware: 18 x M3x8 button head + M3 T-nut for 20-series slot (listed, not modelled).
# Checks (refuses to save on any): the three pieces found; each still one valid solid; every hole goes through
# material all round (a 7 mm boss round each front hole, 6 mm round each ear hole, is solid in the piece); a 3 mm screw shank 4 mm past the face, on each
# hole's axis, overlaps nothing (so it lies in open slot) while the same shank moved 6 mm off the slot hits the
# profile (so the check can fail); ears overlap nothing (envelopes excepted); every piece gets >= 4 fixings; the
# fixings along each edge are <= 120 mm apart, outside the band; solids unchanged.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-59.FCStd", f"{MODELS}/vt350-lite-60.FCStd"
PIECE = "E-box grille panel "
GY0, GY1 = -93.0, -90.0                       # the grille's wall
HOLE_D, SHANK_D, SHANK_L, BOSS_D = 3.4, 3.0, 4.0, 7.0
EAR_BOSS_D = 6.0                              # the ear ends 3 mm past the slot centre: 1.3 mm of wall beside the hole
EAR_X, EAR_Y, EAR_H = (30.0, 33.0), (-90.0, -77.0), 16.0
SLOT_Y = -80.0                                # the upright's X 30 face: one slot, centred
BAND = (400.0, 530.0)
FRONT = ([(x, -40.0) for x in (60.0, 110.0)] + [(x, 680.0) for x in (60.0, 110.0)] +
         [(150.0, z) for z in (10.0, 100.0, 180.0, 260.0, 380.0, 560.0, 640.0)])     # (X, Z) holes along Y
EARS = [10.0, 100.0, 180.0, 260.0, 380.0, 560.0, 640.0]                               # Z of the left ears


def bx(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl_y(x, z, y0, y1, d): return Part.makeCylinder(d / 2, y1 - y0, V(x, y0, z), V(0, 1, 0))


def cyl_x(y, z, x0, x1, d): return Part.makeCylinder(d / 2, x1 - x0, V(x0, y, z), V(1, 0, 0))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n0 = len(pr.leaves)
    pieces = sorted([o for o in pr.leaves if o.Label.startswith(PIECE)], key=lambda o: pr.boxes[o.Name].ZMin)
    p.check(len(pieces) == 3, f"grille pieces: {len(pieces)} (3)")
    env = {o.Name for o in pr.leaves if "envelope" in o.Label}
    mine = {o.Name for o in pieces} | {o.Name for o in pr.leaves if o.Label.startswith("E-box grille")}

    def hits(shape, skip):
        sb = shape.BoundBox; out = []
        for o in pr.leaves:
            if o.Name in skip or not pr.boxes[o.Name].intersect(sb): continue
            if shape.common(pr.shapes[o.Name]).Volume > 1e-3: out.append(o.Label[:40])
        return out

    # fixings: (kind, Z, hole cylinder, boss, shank on the axis past the face, the shank moved off the slot)
    fix = []
    for x, z in FRONT:
        fix.append(("front", x, z, cyl_y(x, z, GY0 - 1, GY1 + 1, HOLE_D), cyl_y(x, z, GY0, GY1, BOSS_D),
                    cyl_y(x, z, GY1, GY1 + SHANK_L, SHANK_D),
                    cyl_y(x + (6 if x > 140 else 0), z + (0 if x > 140 else 6), GY1, GY1 + SHANK_L, SHANK_D)))
    ears = []
    for z in EARS:
        ear = bx(*EAR_X, *EAR_Y, z - EAR_H / 2, z + EAR_H / 2)
        ears.append((z, ear))
        fix.append(("ear", EAR_X[0], z, cyl_x(SLOT_Y, z, EAR_X[0] - 1, EAR_X[1] + 1, HOLE_D), cyl_x(SLOT_Y, z, *EAR_X, EAR_BOSS_D),
                    cyl_x(SLOT_Y, z, EAR_X[0] - SHANK_L, EAR_X[0], SHANK_D),
                    cyl_x(SLOT_Y + 6, z, EAR_X[0] - SHANK_L, EAR_X[0], SHANK_D)))
    for kind, x, z, hole, boss, shank, off in fix:
        p.check(not (BAND[0] - 5 < z < BAND[1] + 5), f"{kind} fixing at X {x:.0f} Z {z:.0f}: outside the band")
        h = hits(shank, env | mine)
        p.check(not h, f"{kind} fixing X {x:.0f} Z {z:.0f}: a 3 mm shank {SHANK_L:.0f} mm past the face hits nothing (open slot): {h}")
        h = hits(off, env | mine)
        p.check(bool(h), f"{kind} fixing X {x:.0f} Z {z:.0f}: the same shank 6 mm off the slot hits the profile: {h}")
    for z, ear in ears:
        h = hits(ear, env | {o.Name for o in pieces})          # the meshes and badge count here
        p.check(not h, f"left ear Z {z:.0f}: overlaps nothing: {h}")
    counts = {}
    for o in pieces:
        b = pr.boxes[o.Name]; s = pr.shapes[o.Name].copy()
        inside = lambda z: b.ZMin + 1e-6 < z < b.ZMax - 1e-6
        mine_ears = [e for z, e in ears if inside(z)]
        mine_fix = [f for f in fix if inside(f[2])]
        if mine_ears: s = s.fuse(Part.makeCompound(mine_ears))
        s = s.cut(Part.makeCompound([f[3] for f in mine_fix])).removeSplitter()
        for kind, x, z, hole, boss, *_ in mine_fix:
            ring = boss.cut(hole)
            p.check(abs(s.common(ring).Volume - ring.Volume) < 1e-2, f"{o.Label[:22]} {kind} hole X {x:.0f} Z {z:.0f}: material all round it")
        p.check(s.isValid() and len(s.Solids) == 1, f"{o.Label[:30]}: one valid solid ({len(s.Solids)}), {s.Volume:.0f} mm3")
        p.check(len(mine_fix) >= 4, f"{o.Label[:30]}: {len(mine_fix)} fixings (>= 4)")
        counts[o.Label[:30]] = len(mine_fix)
        o.Shape = s
        o.Label = o.Label.replace(" (printed", f", {len(mine_fix)} M3 fixings (lite-60) (printed")
    for name, zs in (("left ears", EARS), ("right holes", [z for _, x, z, *_ in fix if x == 150.0])):
        zs = sorted(zs); gaps = [b - a for a, b in zip(zs, zs[1:]) if not (a < BAND[0] and b > BAND[1])]
        p.check(max(gaps) <= 120, f"{name}: Z {zs}, gaps outside the band {gaps} (<= 120)")
    doc.recompute(); pr.refresh()
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in pieces], pr,
                 lambda r: f"the grille pieces (with ears) overlap no lite-59 part: {len(r.hits)} {r.hits[:8]}", exclude=env | mine)
    p.check(len(pr.leaves) == n0, f"lite-60 solids: {len(pr.leaves)} (= lite-59 {n0})")
    p.dump({"fixings": len(fix), "per_piece": counts, "front_holes": FRONT, "ears_z": EARS,
            "hardware": f"{len(fix)} x M3x8 button head + M3 T-nut (20-series slot)"})
    return p.finish([(doc, DST)])


litelib.Pass("lite60_grille_ears").run(main)
