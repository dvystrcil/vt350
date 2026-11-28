# Tests for printchamfer.py (vt350 owner rule 2026-11-18: 0.5 mm on the bed face's edges, 1.0 mm on the top edges).
# Needs FreeCAD:
#
#   APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage
#   $APP freecadcmd $PWD/platform/freecad/test_printchamfer_fc.py     # prints "Ran N tests" + "OK"/"FAILED", exit 0/1
#
# Not in CI (no FreeCAD there).
import os, sys, traceback, unittest

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "platform/freecad")
sys.path.insert(0, HERE)
import FreeCAD, Part
import printchamfer as pc

V = FreeCAD.Vector
UP = V(0, 0, 1)
P = dict(bottom=0.5, top=1.0, step=0.2)          # a printer's profile (the VT350's today)


class PrintChamfer(unittest.TestCase):
    def test_block(self):
        """a 20 x 10 x 8 block: 4 bed edges at 0.5, 4 top edges at 1.0, vertical edges untouched"""
        SHAPE = b = Part.makeBox(20, 10, 8)
        new, info = pc.chamfer(b, UP, **P)
        self.assertEqual((info["bottom"], info["top"]), (4, 4))
        self.assertEqual(info["reduced"] + info["skipped"], [])
        # a chamfer of d on an edge of length L removes d^2/2 * L (less at the corners)
        want = 0.5 ** 2 / 2 * 60 + 1.0 ** 2 / 2 * 60
        self.assertAlmostEqual(info["removed_mm3"], want, delta=0.05 * want)
        self.assertEqual(pc.sharp_edges(new, UP), [])
        self.assertEqual(pc.unchamfered(SHAPE, new, UP, **P), [])
        self.assertAlmostEqual(new.BoundBox.ZLength, 8.0, places=9)               # chamfers don't change the outline

    def test_turned(self):
        """the same block printed on its side (up = +Y): the bed is the Y = 0 face"""
        b = Part.makeBox(20, 10, 8)
        new, info = pc.chamfer(b, V(0, 1, 0), **P)
        self.assertEqual((info["bottom"], info["top"]), (4, 4))
        f = [x for x in new.Faces if isinstance(x.Surface, Part.Plane) and abs(x.CenterOfMass.y) < 1e-6][0]
        self.assertAlmostEqual(f.Area, (20 - 1) * (8 - 1), places=3)   # the bed face shrank 0.5 all round

    def test_u_channel_rims_reduced(self):
        """a U with 2 mm walls, open at the top: its rims (2 mm wide) get less than 1.0 and are reported"""
        SHAPE = u = Part.makeBox(20, 14, 10).cut(Part.makeBox(22, 10, 9, V(-1, 2, 1)))
        new, info = pc.chamfer(u, UP, **P)
        self.assertTrue(new.isValid())
        self.assertTrue(info["reduced"])
        self.assertTrue(all(d < 1.0 for k, w, d in info["reduced"]))
        self.assertTrue(all(abs(d / 0.2 - round(d / 0.2)) < 1e-6 for k, w, d in info["reduced"]))   # whole layers
        skip = {x for k, x, c in info["skipped"]}             # the U-shaped ends (2 mm walls) are too narrow for 0.5
        self.assertEqual({k for k, x, c in info["skipped"]}, {"bottom"})
        self.assertEqual(pc.sharp_edges(new, UP, skip=skip), [])
        self.assertEqual(pc.unchamfered(SHAPE, new, UP, **P, skip=skip), [])

    def test_sizes(self):
        """the top is whole layers (0.5 refused); the first-layer size is one tuned value, never stepped: on a 20 x 2.5 x 8
        fin the long top edges (face 2.5 wide: 0.3 x 2.5 = 0.75) get 0.6, the short ones (the 2.5 x 8 end faces:
        2A/P = 1.9, 0.57) 0.4; the first-layer edges take 0.5 where the face allows 0.5 and are skipped where it doesn't"""
        b = Part.makeBox(20, 10, 8)
        with self.assertRaises(ValueError): pc.chamfer(b, UP, bottom=0.5, top=0.5, step=0.2)
        w = Part.makeBox(20, 2.5, 8)
        new, info = pc.chamfer(w, UP, **P)
        self.assertEqual(sorted({d for k, x, d in info["reduced"] if k == "top"}), [0.4, 0.6])
        self.assertEqual([x for x in info["reduced"] if x[0] == "bottom"], [])
        self.assertEqual(info["skipped"], [])                       # every face here allows 0.5 (narrowest: 0.57)
        self.assertEqual(pc.unchamfered(w, new, UP, **P), [])
        # a 1.5 mm fin: its faces allow 0.42 and 0.38, under the 0.5 first-layer size: those edges are skipped (reported),
        # not given an untested 0.4; its top edges step down to 0.2 (0.38) and 0.4 (0.42)
        t = Part.makeBox(20, 1.5, 8)
        new, info = pc.chamfer(t, UP, **P)
        self.assertEqual(info["bottom"], 0)
        self.assertEqual(sorted({k for k, x, c in info["skipped"]}), ["bottom"])
        self.assertEqual(sorted({d for k, x, d in info["reduced"]}), [0.2, 0.4])
        self.assertEqual(pc.unchamfered(t, new, UP, **P, skip={x for k, x, c in info["skipped"]}), [])

    def test_bore_left_sharp_boss_chamfered(self):
        """a plate with a through hole and a round boss: the hole's mouth stays sharp (owner: bores need none),
        the boss (an outside curve) is chamfered"""
        SHAPE = p = Part.makeBox(20, 20, 5).cut(Part.makeCylinder(2, 7, V(10, 10, -1))).fuse(
            Part.makeCylinder(3, 8, V(30, 10, 0))).removeSplitter()
        new, info = pc.chamfer(p, UP, **P)
        self.assertEqual((info["bottom"], info["top"]), (5, 5))         # the box's 4 + the boss's 1, each
        hole = [f for f in new.Faces if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 2) < 1e-6]
        self.assertTrue(hole and all(abs(f.Area - 2 * 3.14159265 * 2 * 5) < 0.01 for f in hole))   # untouched
        self.assertEqual(pc.sharp_edges(new, UP), [])
        self.assertEqual(pc.unchamfered(SHAPE, new, UP, **P), [])

    def test_force_and_leave(self):
        """the part's own exceptions: a 0.5 lead-in forced on a bore's top mouth (the rules leave bores sharp), and
        one top edge left sharp (a seat): both listed, the rest as the rules say"""
        p = Part.makeBox(20, 20, 5).cut(Part.makeCylinder(2, 7, V(10, 10, -1)))
        mouth = lambda e: 0.5 if (isinstance(e.Curve, Part.Circle) and e.BoundBox.ZMin > 4.9) else None
        seat = lambda e: e.BoundBox.ZMin > 4.9 and e.BoundBox.XMax < 0.1               # the top edge at X 0
        new, info = pc.chamfer(p, UP, force=mouth, leave=seat, **P)
        self.assertEqual((len(info["forced"]), len(info["left"])), (1, 1))
        self.assertEqual((info["bottom"], info["top"]), (4, 4))        # the box's 4 + the mouth; 3 box tops
        hole = [f for f in new.Faces if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 2) < 1e-6]
        self.assertTrue(hole and all(f.Area < 2 * 3.14159265 * 2 * 5 - 1.0 for f in hole))   # the mouth cut back
        self.assertEqual(len(pc.sharp_edges(new, UP)), 1)              # the seat, and only it
        self.assertEqual(pc.unchamfered(p, new, UP, force=mouth, leave=seat, **P), [])

    def test_unchamfered_finds_a_missed_edge(self):
        """unchamfered() names an edge that should have been chamfered and wasn't"""
        b = Part.makeBox(20, 10, 8)
        want = pc.select(b, UP, **P)[0]
        i = sorted(want)[0]
        part = b.makeChamfer(1.0, [b.Edges[k] for k in sorted(want)[1:]])       # all but one
        self.assertEqual(pc.unchamfered(b, part, UP, **P), [pc._mid(b.Edges[i])])

    def test_concave_left_alone(self):
        """an L (step): the inside corner of the step is concave and isn't chamfered"""
        SHAPE = l = Part.makeBox(20, 10, 4).fuse(Part.makeBox(8, 10, 10)).removeSplitter()
        new, info = pc.chamfer(l, UP, **P)
        self.assertTrue(new.isValid())
        self.assertEqual(info["bottom"], 4)
        self.assertEqual(info["top"], 7)                     # the tall top's 4 + the step's 3 outer (not the inside one)
        self.assertEqual(pc.sharp_edges(new, UP), [])
        self.assertEqual(pc.unchamfered(SHAPE, new, UP, **P), [])


if __name__ in ("__main__", "test_printchamfer_fc"):
    try:
        r = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PrintChamfer))
        print("OK" if r.wasSuccessful() else "FAILED")
        code = 0 if r.wasSuccessful() else 1
    except Exception:
        traceback.print_exc(); code = 1
    sys.stdout.flush(); os._exit(code)
