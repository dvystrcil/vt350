# GUI pass: vt350-lite-42-none -> vt350-lite-43   (headless = dry run, never saves)
# vt350#19, #115. The user (2026-11-15), on lite-42-none's taller foot bodies: "the foot pads got thicker", and "the
# filter is no longer there". The StealthMax came off the printer at lite-31 (#115), but its transparent "Filter
# envelope" box (Z -84 .. 2) stayed in the model. lite-42-none's check hit that stale box when it tried to raise the
# stand, so it grew the foot bodies instead.
# This pass:
#  - removes the stale Filter envelope (z_sweep stops loading vt350-filter-3's solids through it, which is right: the
#    filter isn't on the printer);
#  - puts the foot pads back to their lite-27 18 mm height, top still 5 mm under each bracket (5 mm of M8 thread);
#  - raises the base board 19 mm to meet them (top Z -100 -> -81).
# The feet are still placeholders: a real, bought levelling foot replaces them next (user, same day).
# Checks (refuses to save on any): the envelope is gone and nothing else of the printer reaches below the frame
# bottom (Z -50) except the stand; each pad 18 tall, 5 mm under its bracket, standing on the board; the stand overlaps
# nothing; one solid fewer than lite-42-none.
import FreeCAD, Part, os, sys, re
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-42-none.FCStd", f"{MODELS}/vt350-lite-43.FCStd"
PAD_H, LEVEL_GAP, FRAME_BOT = 18.0, 5.0, -50.0
ENV = "Filter envelope (contents in vt350-filter-3.FCStd)"


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n_before = len(pr.leaves)
    env = [o for o in pr.leaves if o.Label == ENV]
    p.check(len(env) == 1, f"one stale filter envelope ({len(env)})")
    for o in env: doc.removeObject(o.Name)
    doc.recompute(); pr.refresh()
    pads = sorted([o for o in pr.leaves if o.Label.startswith("Levelling foot pad")], key=lambda o: o.Label)
    studs = sorted([o for o in pr.leaves if o.Label.startswith("Levelling foot") and "M8 stud" in o.Label], key=lambda o: o.Label)
    brackets = [o for o in pr.leaves if o.Label.startswith("Levelling foot") and "bracket" in o.Label]
    board = next(o for o in pr.leaves if o.Label.startswith("Base board"))
    p.check(len(pads) == 4 and len(studs) == 4 and len(brackets) == 4, f"4 feet ({len(pads)} pads, {len(studs)} studs, {len(brackets)} brackets)")
    lows = []
    for pd, st in zip(pads, studs):
        bk = min(brackets, key=lambda o: pr.shapes[o.Name].distToShape(pr.shapes[st.Name])[0])
        top = pr.boxes[bk.Name].ZMin - LEVEL_GAP; b = pr.shapes[pd.Name].BoundBox
        cx, cy, r_ = (b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, b.XLength / 2
        g = Part.makeCylinder(r_, PAD_H, V(cx, cy, top - PAD_H))
        par = pd.getGlobalPlacement().multiply(pd.Placement.inverse())
        g.Placement = par.inverse().multiply(g.Placement); pd.Shape = g; pd.Placement = FreeCAD.Placement()
        pd.Label = re.sub(r"\(rubber, \d+ tall body, ", "(rubber, ", pd.Label)
        lows.append(top - PAD_H)
    p.check(max(lows) - min(lows) < 0.01, f"pad bottoms level: {min(lows):.2f} .. {max(lows):.2f}")
    dz = lows[0] - pr.boxes[board.Name].ZMax
    par = board.getGlobalPlacement().multiply(board.Placement.inverse())
    pl = board.Placement.copy(); pl.Base = pl.Base + par.Rotation.inverted().multVec(V(0, 0, dz)); board.Placement = pl
    doc.recompute(); pr.refresh()
    p.log(f"board raised {dz:.2f} mm")
    p.check(abs(dz - 19.0) < 0.01, f"board raised {dz:.2f} mm (expected 19)")
    for pd, st in zip(pads, studs):
        bk = min(brackets, key=lambda o: pr.shapes[o.Name].distToShape(pr.shapes[st.Name])[0])
        gap = pr.boxes[bk.Name].ZMin - pr.boxes[pd.Name].ZMax
        p.check(abs(gap - LEVEL_GAP) < 0.01, f"{pd.Label[:22]}: top to bracket {gap:.2f} mm (= {LEVEL_GAP:.0f})")
        p.check(abs(pr.boxes[pd.Name].ZLength - PAD_H) < 0.01, f"{pd.Label[:22]}: {pr.boxes[pd.Name].ZLength:.2f} tall (= {PAD_H:.0f})")
        p.check(abs(pr.boxes[pd.Name].ZMin - pr.boxes[board.Name].ZMax) < 0.01, f"{pd.Label[:22]}: stands on the board")
    stand = {o.Name for o in pads + studs + brackets + [board]}
    below = [o.Label for o in pr.leaves if o.Name not in stand and pr.boxes[o.Name].ZMin < FRAME_BOT - 0.01]
    p.check(not below, f"nothing but the stand below the frame bottom: {below[:6]}")
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in pads + studs + [board]], pr, lambda r: f"the stand vs the printer: {r.hits[:6]}",
                 exclude={o.Name for o in pads + studs + [board]})
    p.check(len(pr.leaves) == n_before - 1, f"solids: {len(pr.leaves)} (lite-42-none less the envelope, {n_before - 1})")
    p.dump({"board_top": pr.boxes[board.Name].ZMax, "board_raised": dz, "pad_h": PAD_H, "level_gap": LEVEL_GAP})
    return p.finish([(doc, DST)])


litelib.Pass("lite43_stand_up").run(main)
