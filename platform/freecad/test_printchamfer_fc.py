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


class PrintChamfer(unittest.TestCase):
    def test_block(self):
        """a 20 x 10 x 8 block: 4 bed edges at 0.6, 4 top edges at 1.0, vertical edges untouched"""
        SHAPE = b = Part.makeBox(20, 10, 8)
        new, info = pc.chamfer(b, UP)
        self.assertEqual((info["bottom"], info["top"]), (4, 4))
        self.assertEqual(info["reduced"] + info["skipped"], [])
        # a chamfer of d on an edge of length L removes d^2/2 * L (less at the corners)
        want = 0.6 ** 2 / 2 * 60 + 1.0 ** 2 / 2 * 60
        self.assertAlmostEqual(info["removed_mm3"], want, delta=0.05 * want)
        self.assertEqual(pc.sharp_edges(new, UP), [])
        self.assertEqual(pc.unchamfered(SHAPE, new, UP), [])
        self.assertAlmostEqual(new.BoundBox.ZLength, 8.0, places=9)               # chamfers don't change the outline

    def test_turned(self):
        """the same block printed on its side (up = +Y): the bed is the Y = 0 face"""
        b = Part.makeBox(20, 10, 8)
        new, info = pc.chamfer(b, V(0, 1, 0))
        self.assertEqual((info["bottom"], info["top"]), (4, 4))
        f = [x for x in new.Faces if isinstance(x.Surface, Part.Plane) and abs(x.CenterOfMass.y) < 1e-6][0]
        self.assertAlmostEqual(f.Area, (20 - 1.2) * (8 - 1.2), places=3)   # the bed face shrank 0.6 all round

    def test_u_channel_rims_reduced(self):
        """a U with 2 mm walls, open at the top: its rims (2 mm wide) get less than 1.0 and are reported"""
        SHAPE = u = Part.makeBox(20, 14, 10).cut(Part.makeBox(22, 10, 9, V(-1, 2, 1)))
        new, info = pc.chamfer(u, UP)
        self.assertTrue(new.isValid())
        self.assertTrue(info["reduced"])
        self.assertTrue(all(d < 1.0 for k, w, d in info["reduced"]))
        self.assertTrue(all(abs(d / 0.2 - round(d / 0.2)) < 1e-6 for k, w, d in info["reduced"]))   # whole layers
        self.assertEqual(pc.sharp_edges(new, UP), [])
        self.assertEqual(pc.unchamfered(SHAPE, new, UP), [])

    def test_sizes_in_layers(self):
        """sizes are whole 0.2 mm layers: 0.5 is refused; on a 20 x 2.5 x 8 fin the long top edges (face 2.5 wide:
        0.3 x 2.5 = 0.75) get 0.6, the short ones (the 2.5 x 8 end faces: 2A/P = 1.9, 0.57) get 0.4"""
        b = Part.makeBox(20, 10, 8)
        with self.assertRaises(ValueError): pc.chamfer(b, UP, bottom=0.5)
        w = Part.makeBox(20, 2.5, 8)                                   # top face 2.5 wide: 0.3 x 2.5 = 0.75
        new, info = pc.chamfer(w, UP)
        self.assertEqual(sorted({d for k, x, d in info["reduced"]}), [0.4, 0.6])
        self.assertEqual(pc.unchamfered(w, new, UP), [])

    def test_bore_left_sharp_boss_chamfered(self):
        """a plate with a through hole and a round boss: the hole's mouth stays sharp (owner: bores need none),
        the boss (an outside curve) is chamfered"""
        SHAPE = p = Part.makeBox(20, 20, 5).cut(Part.makeCylinder(2, 7, V(10, 10, -1))).fuse(
            Part.makeCylinder(3, 8, V(30, 10, 0))).removeSplitter()
        new, info = pc.chamfer(p, UP)
        self.assertEqual((info["bottom"], info["top"]), (5, 5))         # the box's 4 + the boss's 1, each
        hole = [f for f in new.Faces if isinstance(f.Surface, Part.Cylinder) and abs(f.Surface.Radius - 2) < 1e-6]
        self.assertTrue(hole and all(abs(f.Area - 2 * 3.14159265 * 2 * 5) < 0.01 for f in hole))   # untouched
        self.assertEqual(pc.sharp_edges(new, UP), [])
        self.assertEqual(pc.unchamfered(SHAPE, new, UP), [])

    def test_unchamfered_finds_a_missed_edge(self):
        """unchamfered() names an edge that should have been chamfered and wasn't"""
        b = Part.makeBox(20, 10, 8)
        want = pc.select(b, UP)[0]
        i = sorted(want)[0]
        part = b.makeChamfer(1.0, [b.Edges[k] for k in sorted(want)[1:]])       # all but one
        self.assertEqual(pc.unchamfered(b, part, UP), [pc._mid(b.Edges[i])])

    def test_concave_left_alone(self):
        """an L (step): the inside corner of the step is concave and isn't chamfered"""
        SHAPE = l = Part.makeBox(20, 10, 4).fuse(Part.makeBox(8, 10, 10)).removeSplitter()
        new, info = pc.chamfer(l, UP)
        self.assertTrue(new.isValid())
        self.assertEqual(info["bottom"], 4)
        self.assertEqual(info["top"], 7)                     # the tall top's 4 + the step's 3 outer (not the inside one)
        self.assertEqual(pc.sharp_edges(new, UP), [])
        self.assertEqual(pc.unchamfered(SHAPE, new, UP), [])


if __name__ in ("__main__", "test_printchamfer_fc"):
    try:
        r = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PrintChamfer))
        print("OK" if r.wasSuccessful() else "FAILED")
        code = 0 if r.wasSuccessful() else 1
    except Exception:
        traceback.print_exc(); code = 1
    sys.stdout.flush(); os._exit(code)
