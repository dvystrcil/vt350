# GUI pass: vt350-lite-43 -> vt350-lite-44   (headless = dry run, never saves)
# vt350#83. The user (2026-11-15): "go with the Asmith DK-08 feet, board stays". The placeholder feet since lite-27
# (an M8 stud stub and a D50 x 18 rubber pad under each 40x40x8 bracket) become Asmith DK-0808035A swivel levelling
# feet, modelled from the catalog drawing (asmith.com.tw, Leveling Glide p. 88: M8x1.25, L 35, D 40, H1 20, H2 15,
# H3 6.5, W 13). The vendor's IGES/x_t come in a RAR archive this laptop can't unpack, so the base profile above the
# drawing's figures (the cushion thickness, the cup's taper) is estimated from the drawing's proportions.
# Fit (the user's pick, same day): the bottom 4040's slots are 6 mm wide, so the M8 stud can't go up into the frame.
# Each stud is cut from 35 to 19.5 mm so it ends flush with the top of the bracket (tapped M8), with the supplied jam
# nut tight under the bracket and 5 mm of levelling thread showing between the nut and the bolt's hex.
# Floor (board top) = bracket bottom - 6.5 nut - 5 thread - 20 (H1): Z -89.5, so the board drops 8.5 mm from lite-43.
# Per foot, 4 solids replace 2: NBR cushion, steel base, bolt (hex + cut stud, one part), jam nut. The bracket gets
# its M8 hole.
# Checks (refuses to save on any): 4 feet; each nut tight under its bracket, 5 mm of thread showing, the stud flush
# with the bracket top (nothing enters the frame), the cushion standing on the board; the board moved -8.5; nothing but
# the stand below the frame bottom (Z -50); the stand overlaps nothing in the printer and its parts overlap each other
# nowhere; 8 solids more than lite-43.
import FreeCAD, Part, os, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-43.FCStd", f"{MODELS}/vt350-lite-44.FCStd"
FRAME_BOT = -50.0
# catalog DK-0808035A
M8_D, D_BASE, H1, H2, H3, W_AF, L_BOUGHT = 8.0, 40.0, 20.0, 15.0, 6.5, 13.0, 35.0
SHOW = 5.0                      # levelling thread showing between the jam nut and the bolt's hex (the user)
CUSHION_T = 4.0                 # estimated from the drawing
CUP_TOP_D = 26.0                # estimated from the drawing: the steel cup tapers from D 40 to this at H2
STEEL, RUBBER = (0.78, 0.79, 0.80), (0.08, 0.08, 0.08)


def hexagon(af, h, x, y, z):
    r = af / math.sqrt(3)
    pts = [V(x + r * math.cos(math.radians(30 + 60 * k)), y + r * math.sin(math.radians(30 + 60 * k)), z) for k in range(7)]
    return Part.Face(Part.makePolygon(pts)).extrude(V(0, 0, h))


def base_cup(x, y, z0):
    # steel cup on the cushion: D 40 straight for 4 mm, then a cone to CUP_TOP_D at H2 (revolved profile)
    zc = z0 + CUSHION_T; r0, r1 = D_BASE / 2, CUP_TOP_D / 2
    prof = Part.makePolygon([V(x, y, zc), V(x + r0, y, zc), V(x + r0, y, zc + 4), V(x + r1, y, z0 + H2), V(x, y, z0 + H2), V(x, y, zc)])
    return Part.Face(prof).revolve(V(x, y, 0), V(0, 0, 1), 360)


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n_before = len(pr.leaves)
    lab = lambda pre, key: sorted([o for o in pr.leaves if o.Label.startswith(pre) and key in o.Label], key=lambda o: o.Label)
    pads, studs = lab("Levelling foot pad", ""), lab("Levelling foot", "M8 stud")
    brackets = lab("Levelling foot", "bracket")
    board = next(o for o in pr.leaves if o.Label.startswith("Base board"))
    p.check(len(pads) == 4 and len(studs) == 4 and len(brackets) == 4, f"4 feet ({len(pads)} pads, {len(studs)} studs, {len(brackets)} brackets)")
    group = pads[0].getParentGroup()
    par = pads[0].getGlobalPlacement().multiply(pads[0].Placement.inverse())   # the stand group's frame

    def local(s):
        s = s.copy(); s.Placement = par.inverse().multiply(s.Placement); return s

    feet = []                                       # per foot: dict of global shapes
    for st in studs:
        i = st.Label.split()[2]
        sb = pr.boxes[st.Name]; x, y = (sb.XMin + sb.XMax) / 2, (sb.YMin + sb.YMax) / 2
        bk = min(brackets, key=lambda o: pr.shapes[o.Name].distToShape(pr.shapes[st.Name])[0])
        zb = pr.boxes[bk.Name].ZMin; zt = pr.boxes[bk.Name].ZMax
        hex_top = zb - H3 - SHOW; floor = hex_top - H1
        stud_len = zt - hex_top
        nut = hexagon(W_AF, H3, x, y, zb - H3).cut(Part.makeCylinder(M8_D / 2, H3, V(x, y, zb - H3)))
        bolt = hexagon(W_AF, H1 - H2, x, y, floor + H2).fuse(Part.makeCylinder(M8_D / 2, stud_len, V(x, y, hex_top))).removeSplitter()
        feet.append(dict(i=i, x=x, y=y, bk=bk, zb=zb, zt=zt, floor=floor, stud_len=stud_len,
                         cushion=Part.makeCylinder(D_BASE / 2, CUSHION_T, V(x, y, floor)), base=base_cup(x, y, floor), bolt=bolt, nut=nut))
        # the bracket's tapped M8 hole
        g = pr.shapes[bk.Name].cut(Part.makeCylinder(M8_D / 2, zt - zb, V(x, y, zb)))
        bk.Shape = local(g); bk.Placement = FreeCAD.Placement()
        bk.Label = bk.Label.replace("placeholder)", "placeholder, tapped M8)")
    floors = [f["floor"] for f in feet]
    p.check(max(floors) - min(floors) < 0.01, f"feet level: floor Z {min(floors):.2f} .. {max(floors):.2f}")
    p.check(all(abs(f["stud_len"] - (L_BOUGHT - 15.5)) < 0.01 for f in feet), f"studs cut to {[round(f['stud_len'], 2) for f in feet]} (= 19.5)")
    for o in pads + studs: doc.removeObject(o.Name)
    new = []
    for f in feet:
        d = f"Levelling foot {f['i']} Asmith DK-0808035A"
        new += p.add_solids(doc, group, [("", local(f["cushion"]))], "Stand", d + " NBR cushion (D40, est. 4 thick)", RUBBER)
        new += p.add_solids(doc, group, [("", local(f["base"]))], "Stand", d + " base (D40, zinc-plated steel)", STEEL)
        new += p.add_solids(doc, group, [("", local(f["bolt"]))], "Stand", d + f" bolt (M8x1.25, cut {L_BOUGHT:.0f} -> {f['stud_len']:.1f})", STEEL)
        new += p.add_solids(doc, group, [("", local(f["nut"]))], "Stand", d + " jam nut (M8, 13 AF)", STEEL)
    dz = floors[0] - pr.boxes[board.Name].ZMax
    bpar = board.getGlobalPlacement().multiply(board.Placement.inverse())
    pl = board.Placement.copy(); pl.Base = pl.Base + bpar.Rotation.inverted().multVec(V(0, 0, dz)); board.Placement = pl
    doc.recompute(); pr.refresh()
    p.log(f"board moved {dz:.2f} mm, top Z {pr.boxes[board.Name].ZMax:.2f}")
    p.check(abs(dz + 8.5) < 0.01, f"board moved {dz:.2f} mm (expected -8.5)")
    by = {o.Label: o for o in pr.leaves}
    for f in feet:
        d = f"Levelling foot {f['i']} Asmith DK-0808035A"
        nut = next(o for l, o in by.items() if l.startswith(d + " jam nut")); bolt = next(o for l, o in by.items() if l.startswith(d + " bolt"))
        cush = next(o for l, o in by.items() if l.startswith(d + " NBR"))
        nb, bb, cb = pr.boxes[nut.Name], pr.boxes[bolt.Name], pr.boxes[cush.Name]
        p.check(abs(nb.ZMax - f["zb"]) < 0.01, f"foot {f['i']}: jam nut tight under the bracket ({nb.ZMax:.2f} vs {f['zb']:.2f})")
        show = nb.ZMin - (bb.ZMin + H1 - H2)          # the bolt starts at its hex, H2 above the floor
        p.check(abs(show - SHOW) < 0.01, f"foot {f['i']}: {show:.2f} mm thread showing (= {SHOW:.0f})")
        p.check(bb.ZMax <= f["zt"] + 0.01 and bb.ZMax <= FRAME_BOT + 0.01, f"foot {f['i']}: stud top {bb.ZMax:.2f} flush with the bracket top, below the frame")
        p.check(abs(cb.ZMin - pr.boxes[board.Name].ZMax) < 0.01, f"foot {f['i']}: cushion stands on the board")
    stand = {o.Name for o in new + brackets + [board]}
    below = [o.Label for o in pr.leaves if o.Name not in stand and pr.boxes[o.Name].ZMin < FRAME_BOT - 0.01]
    p.check(not below, f"nothing but the stand below the frame bottom: {below[:6]}")
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in new + [board]], pr, lambda r: f"the stand vs the printer: {r.hits[:6]}",
                 exclude=stand)
    pairs = [(a, b) for k, a in enumerate(new + brackets + [board]) for b in (new + brackets + [board])[k + 1:]
             if pr.boxes[a.Name].intersect(pr.boxes[b.Name])]
    vols = p.volumes([(pr.shapes[a.Name], pr.shapes[b.Name]) for a, b in pairs])
    clash = [(a.Label[:40], b.Label[:40], round(v, 3)) for (a, b), v in zip(pairs, vols) if v > 1e-3]
    p.check(not clash, f"stand parts overlap each other nowhere ({len(pairs)} touching pairs): {clash[:4]}")
    p.check(len(pr.leaves) == n_before + 8, f"solids: {len(pr.leaves)} (lite-43 - 8 placeholders + 16 foot parts = {n_before + 8})")
    p.dump({"board_top": pr.boxes[board.Name].ZMax, "board_moved": dz, "stud_len": feet[0]["stud_len"], "thread_showing": SHOW,
            "foot": "Asmith DK-0808035A", "feet_xy": [(f["x"], f["y"]) for f in feet]})
    return p.finish([(doc, DST)])


litelib.Pass("lite44_dk08_feet").run(main)
