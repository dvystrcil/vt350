# GUI pass: vt350-lite-44 -> vt350-lite-45   (headless = dry run, never saves)
# vt350#83. How each foot's bracket (40 x 40 x 8, tapped M8 for the DK-08 stud) is held to the side 4040. The user
# (2026-11-16): "I would use M5 bolts with lock washers. its in an area that cannot be seen ... what I need is
# stability", and no counterbore. So, per bracket, 4 x M5 socket-head screws (DIN 912) with split lock washers
# (DIN 127) from below, two in each of the 4040's two bottom slots, at the plate's corners (+-10 in X = the slot
# centres, +-12 in Y), into drop-in M5 T-nuts. Four screws on a 20 x 24 pattern resist the foot tipping the plate in
# any direction; the foot itself doesn't move.
# The slot was read from a cross-section of the side 4040s (constants below, spot-checked on the solid at every
# screw): a 20-series slot 6, lip top Z -48, cavity ceiling Z -44, so the cavity is only 4 mm tall. The T-nut is a
# 7.4 x 10 x 3 block on the lip, and the screw is the LONGEST stock length (10/12/14/16) whose tip stays >= 0.3 under
# the ceiling with >= 2.5 mm of thread in the nut: M5x14 (tip Z -45.2, 2.8 mm in the nut). The printer's weight pushes
# the bracket up against the frame; the screws hold it there and take load only when the printer is lifted or tipped.
# The bracket gets 4 clearance holes (D 5.5). The bracket, screws, washers and T-nuts render brushed steel (#192).
# Checks (refuses to save on any): 4 brackets; every screw position has the measured slot; each washer clears the jam
# nut (>= 1 mm); each screw has >= 2.5 mm in its T-nut and its tip >= 0.3 under the ceiling; the new parts overlap
# nothing in the printer (the extrusion included) and each other only where they're meant to touch; 48 solids more.
import FreeCAD, Part, os, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-44.FCStd", f"{MODELS}/vt350-lite-45.FCStd"
FRAME_BOT = -50.0
DX, DY = 10.0, 12.0                     # screw offsets from the bracket centre: X = the 4040's slot centres
HOLE_D = 5.5                            # M5 clearance, medium
HEAD_D, HEAD_H = 8.5, 5.0               # DIN 912 M5
WASH_ID, WASH_OD, WASH_T = 5.1, 9.2, 1.2   # DIN 127 B M5 (flattened when tight)
NUT_L, M5 = 10.0, 5.0                  # drop-in T-nut: length along the slot; nominal thread
MIN_ENGAGE, TIP_CLEAR = 2.5, 0.3       # thread in the T-nut; screw tip to the cavity ceiling
LENGTHS = [10.0, 12.0, 14.0, 16.0]
JAM_NUT_R = 13.0 / math.sqrt(3)         # the DK-08 jam nut's corner radius (13 AF)
STEEL = (0.65, 0.67, 0.69)


# The bottom slot, read from a cross-section of the side 4040s (lite-44, slice at Y -62 and Y 200; both 4040s the
# same): a 20-series slot 6. Opening 6.0 wide through a 2.0 lip (Z -50..-48); the cavity is 12.0 wide at the lip
# (Z -48..-47.06) and tapers to 5.88 at its ceiling, Z -44.0; solid above that up to the corner bore (Z -41.6).
# A vertical line through the slot crosses material, cavity, material, bore, material, so it can't be bisected
# (an earlier probe here did, and read the bore as the cavity); the numbers are constants and every screw position
# is spot-checked against them on the solid.
SLOT_LIP_TOP, SLOT_CEIL, SLOT_OPEN_HALF = FRAME_BOT + 2.0, FRAME_BOT + 6.0, 3.0
NUT_W, NUT_T = 7.4, 3.0     # T-nut block: 7.4 wide fits the taper up to Z -44.75 (cavity 7.88 wide at its top, -45.0)


def same_slot(ext, x, y):
    """Spot checks that (x, y) is over a slot of this profile: the opening and the cavity are empty, the lips, the
    cavity's sloped sides and the core above the ceiling are solid."""
    inside = lambda px, pz: ext.isInside(V(px, y, pz), 1e-4, True)
    return (not inside(x, FRAME_BOT + 1.0) and not inside(x, FRAME_BOT + 4.0)
            and not inside(x - 5.0, FRAME_BOT + 2.5) and not inside(x + 5.0, FRAME_BOT + 2.5)
            and inside(x - 4.0, FRAME_BOT + 1.0) and inside(x + 4.0, FRAME_BOT + 1.0)
            and inside(x - 4.0, FRAME_BOT + 5.5) and inside(x + 4.0, FRAME_BOT + 5.5)
            and inside(x, SLOT_CEIL + 0.5))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n_before = len(pr.leaves)
    brackets = sorted([o for o in pr.leaves if o.Label.startswith("Levelling foot") and "bracket" in o.Label], key=lambda o: o.Label)
    nuts_m8 = [o for o in pr.leaves if "DK-0808035A jam nut" in o.Label]
    p.check(len(brackets) == 4 and len(nuts_m8) == 4, f"4 brackets, 4 jam nuts ({len(brackets)}, {len(nuts_m8)})")
    group = brackets[0].getParentGroup()
    par = brackets[0].getGlobalPlacement().multiply(brackets[0].Placement.inverse())

    def local(s):
        s = s.copy(); s.Placement = par.inverse().multiply(s.Placement); return s

    new_items, slots, feet = [], [], []
    for bk in brackets:
        i = bk.Label.split()[2]
        b = pr.boxes[bk.Name]; cx, cy = (b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2; zb, zt = b.ZMin, b.ZMax
        ext = next(o for o in pr.leaves if o.Label.startswith("4040") and pr.boxes[o.Name].ZMin < FRAME_BOT + 0.01
                   and pr.boxes[o.Name].XMin <= cx <= pr.boxes[o.Name].XMax and pr.boxes[o.Name].YMin <= cy <= pr.boxes[o.Name].YMax)
        es = pr.shapes[ext.Name]
        jam = min(nuts_m8, key=lambda o: pr.shapes[o.Name].distToShape(pr.shapes[bk.Name])[0])
        jb = pr.boxes[jam.Name]; jx, jy = (jb.XMin + jb.XMax) / 2, (jb.YMin + jb.YMax) / 2
        g = pr.shapes[bk.Name]
        for k, (sx, sy) in enumerate([(-DX, -DY), (DX, -DY), (-DX, DY), (DX, DY)], 1):
            x, y = cx + sx, cy + sy
            ok = same_slot(es, x, y)
            p.check(ok, f"foot {i} screw {k}: the slot at ({x:.1f}, {y:.1f}) has the measured profile (opening, lips, "
                        f"cavity, ceiling Z {SLOT_CEIL:.2f})")
            if not ok: continue
            z_lip, z_ceil = SLOT_LIP_TOP, SLOT_CEIL; slots.append((x, y))
            nut_t = NUT_T
            nut_z0 = z_lip; nut_z1 = nut_z0 + nut_t
            nut_w = NUT_W
            z_head = zb - WASH_T
            fits = [l for l in LENGTHS if z_head + l <= z_ceil - TIP_CLEAR and z_head + l - nut_z0 >= MIN_ENGAGE]
            L = max(fits) if fits else None
            p.check(L is not None, f"foot {i} screw {k}: a stock M5 length fits (lip top {z_lip:.2f}, ceiling {z_ceil:.2f}, "
                                   f"cavity 12.0 -> 5.88 wide)")
            if L is None: continue
            screw = Part.makeCylinder(HEAD_D / 2, HEAD_H, V(x, y, z_head - HEAD_H)).fuse(
                Part.makeCylinder(M5 / 2, L, V(x, y, z_head))).removeSplitter()
            washer = Part.makeCylinder(WASH_OD / 2, WASH_T, V(x, y, z_head)).cut(Part.makeCylinder(WASH_ID / 2, WASH_T, V(x, y, z_head)))
            tnut = Part.makeBox(nut_w, NUT_L, nut_t, V(x - nut_w / 2, y - NUT_L / 2, nut_z0)).cut(
                Part.makeCylinder(M5 / 2, nut_t, V(x, y, nut_z0)))
            g = g.cut(Part.makeCylinder(HOLE_D / 2, zt - zb, V(x, y, zb)))
            clear = math.hypot(x - jx, y - jy) - WASH_OD / 2 - JAM_NUT_R
            p.check(clear >= 1.0, f"foot {i} screw {k}: washer clears the jam nut by {clear:.2f} mm")
            p.check(z_head + L - nut_z0 >= MIN_ENGAGE and z_head + L <= z_ceil - TIP_CLEAR + 0.001,
                    f"foot {i} screw {k}: M5x{L:.0f}, tip Z {z_head + L:.2f}, {min(z_head + L, nut_z1) - nut_z0:.2f} mm in the "
                    f"T-nut ({nut_z0:.2f}..{nut_z1:.2f}), {z_ceil - z_head - L:.2f} under the ceiling")
            d = f"Levelling foot {i}"
            new_items += [(d + f" M5x{L:.0f} screw {k} (DIN 912)", screw), (d + f" M5 lock washer {k} (DIN 127)", washer),
                          (d + f" M5 T-nut {k} (drop-in, slot)", tnut)]
        bk.Shape = local(g); bk.Placement = FreeCAD.Placement()
        bk.Label = bk.Label.replace("tapped M8)", "tapped M8, 4 x M5 holes)")
        feet.append(dict(i=i, ext=ext.Label))
    p.check(len(slots) == 16, f"16 screw positions over the slot: {len(slots)}")
    new = []
    for label, s in new_items:
        new += p.add_solids(doc, group, [("", local(s))], "Stand", label, STEEL)
    doc.recompute(); pr.refresh()
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in new], pr, lambda r: f"the screws, washers and T-nuts vs the printer: {r.hits[:6]}",
                 exclude={o.Name for o in new})
    parts = new + brackets
    pairs = [(a, b) for k, a in enumerate(parts) for b in parts[k + 1:] if pr.boxes[a.Name].intersect(pr.boxes[b.Name])]
    vols = p.volumes([(pr.shapes[a.Name], pr.shapes[b.Name]) for a, b in pairs])
    clash = [(a.Label[:44], b.Label[:44], round(v, 3)) for (a, b), v in zip(pairs, vols) if v > 1e-3]
    p.check(not clash, f"the foot hardware overlaps itself nowhere ({len(pairs)} touching pairs): {clash[:4]}")
    p.check(len(pr.leaves) == n_before + 48, f"solids: {len(pr.leaves)} (lite-44 + 16 screws, 16 washers, 16 T-nuts = {n_before + 48})")
    p.dump({"slot": {"lip_top": SLOT_LIP_TOP, "ceiling": SLOT_CEIL, "opening": 2 * SLOT_OPEN_HALF, "cavity": "12.0 at the lip, 5.88 at the ceiling", "t_nut": [NUT_W, NUT_L, NUT_T]},
            "screw": sorted({l.split()[3] for l, _ in new_items if " screw " in l}), "pattern": [2 * DX, 2 * DY], "feet": feet})
    return p.finish([(doc, DST)])


litelib.Pass("lite45_bracket_screws").run(main)
