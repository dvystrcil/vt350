# vt350#174: each bowden tube's stored route (Inlet, ExitPoint, ExitDir, HandleInlet, HandleExit, the curve
# bezier.tube_poles builds) must run down the middle of its own solid. Needs FreeCAD and the model (not in git):
#
#   APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage
#   VT350_MODEL=~/Documents/VT350/vt350-lite-N.FCStd $APP freecadcmd $PWD/cad/studies/test_bowden_props_fc.py
#
# Prints "Ran N tests" + "OK"/"FAILED". Not in CI (no FreeCAD there).
#
# Since vt350#195 the five tubes are one Part::Feature ("Bowden Left", which holds the props) and four App::Links to
# it, so a link's route is the target's, moved by the link's placement relative to the target's. lite-31 made the
# slot copies by translating Bowden Left and kept its props; they were already 10.7 mm off in X then (lite36_roof_exit.py
# measured around it, o2s_route.py still does).
import os, sys, traceback, unittest

REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(REPO, "platform/freecad")]
import FreeCAD, Part
import bezier, linkgeo

V = FreeCAD.Vector
MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-65.FCStd")
ZS = (530.0, 560.0, 600.0, 650.0, 680.0)     # heights where every tube is one straight-ish loop (lite36_roof_exit.py)
TOL = 0.1                                    # mm: the curve against the section's centre
PROPS = ("Inlet", "ExitPoint", "ExitDir", "HandleInlet", "HandleExit")


def route(o):
    """o's stored route as a global Part.BezierCurve: its link target's props, moved as o is moved relative to it."""
    t = linkgeo.link_target(o)
    poles = bezier.tube_poles(tuple(V(t.Inlet)), tuple(V(t.ExitPoint)), tuple(V(t.ExitDir)),
                              t.HandleInlet.Value, t.HandleExit.Value)
    rel = linkgeo.gplace(o).multiply(linkgeo.gplace(t).inverse())
    c = Part.BezierCurve()
    c.setPoles([rel.multVec(V(*q)) for q in poles])
    return c


class BowdenProps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = FreeCAD.openDocument(MODEL)
        cls.tubes = [o for o in cls.doc.Objects if o.Label.startswith("Bowden ") and linkgeo.is_leaf(o)]

    @classmethod
    def tearDownClass(cls):
        FreeCAD.closeDocument(cls.doc.Name)

    def test_five_tubes_one_set_of_props(self):
        self.assertEqual(len(self.tubes), 5, [o.Label for o in self.tubes])
        targets = {linkgeo.link_target(o).Name for o in self.tubes}
        self.assertEqual(len(targets), 1, targets)
        t = linkgeo.link_target(self.tubes[0])
        self.assertTrue(all(hasattr(t, p) for p in PROPS), [p for p in PROPS if not hasattr(t, p)])

    def test_route_runs_down_each_tube(self):
        for o in self.tubes:
            s, c = linkgeo.gshape(o), route(o).toShape()
            for z in ZS:
                with self.subTest(tube=o.Label, z=z):
                    sec = s.slice(V(0, 0, 1), z)
                    self.assertEqual(len(sec), 1, f"{o.Label} at Z {z}: {len(sec)} loops")
                    centre = Part.Face(sec[0]).CenterOfMass
                    d = c.distToShape(Part.Vertex(centre))[0]
                    self.assertLess(d, TOL, f"{o.Label} at Z {z}: centre {tuple(round(x, 2) for x in centre)} is "
                                            f"{d:.2f} mm from its stored route")


if __name__ in ("__main__", "test_bowden_props_fc"):      # freecadcmd runs a script as module "test_bowden_props_fc"
    try:
        print(f"model: {MODEL}")
        r = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(BowdenProps))
        print("OK" if r.wasSuccessful() else "FAILED")
        code = 0 if r.wasSuccessful() else 1
    except Exception:
        traceback.print_exc(); code = 1
    sys.stdout.flush(); os._exit(code)
