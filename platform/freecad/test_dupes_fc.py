# Tests for dupes.py's FreeCAD side (vt350#195): finding copies, fitting them, and replacing them with App::Links that
# land exactly where the copies were. Needs FreeCAD:
#
#   APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage
#   $APP freecadcmd $PWD/platform/freecad/test_dupes_fc.py     # prints "Ran N tests" + "OK"/"FAILED", exit code 0/1
#
# Not in CI (no FreeCAD there); the plain-python side is test_dupes.py, which is.
#
# Fixture: a chiral solid (three unequal arms; so orientation and handedness show) in App::Part "Head" (turned 90 deg about Z):
#   Master    the L, raw at the origin, Placement P0
#   Same      the same raw L, its own Placement (a plain copy, as the O2S boards are)
#   Shifted   the L baked 40 mm along X into its raw shape (as an STL import does)
#   Turned    the L baked turned 180 deg about Y and moved, with its own turned Placement (as the SpeedClips are)
#   Mirror    the L reflected in YZ (a mirrored dock's part): never linked
#   Near      the chiral solid scaled 1.00002: fits within FIT_TOL but would land ~0.6 um off (landing() catches it)
#   Tool      a copy a Part::Cut uses: left alone
#   MMaster/MCopy: one mesh of the L twice, the copy with StandInFor (a lite-50 mesh stand-in)
import os, sys, tempfile, traceback, unittest

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "platform/freecad")
sys.path.insert(0, HERE)
import FreeCAD, Part, Mesh
import dupes, linkgeo

V = FreeCAD.Vector
HEAD_PL = FreeCAD.Placement(V(100, 0, 0), FreeCAD.Rotation(V(0, 0, 1), 90))
P0 = FreeCAD.Placement(V(5, 5, 0), FreeCAD.Rotation(V(0, 0, 1), 10))
TURN = FreeCAD.Placement(V(7, -3, 20), FreeCAD.Rotation(V(0, 1, 0), 180))


def l_shape():
    """Three unequal arms from one corner (x 30, y 20, z 25): chiral, so its mirror image is no rotation of it."""
    return Part.makeBox(30, 5, 5).fuse([Part.makeBox(5, 20, 5), Part.makeBox(5, 5, 25)]).removeSplitter()


def baked(t):
    s = l_shape(); s.transformShape(t.toMatrix()); return s


def build_fixture(path):
    doc = FreeCAD.newDocument("dupes_fixture")
    head = doc.addObject("App::Part", "Head"); head.Placement = HEAD_PL

    def part(name, shape, pl):
        o = doc.addObject("Part::Feature", name); o.Shape = shape; o.Placement = pl; head.addObject(o); return o
    part("Master", l_shape(), P0)
    part("Same", l_shape(), FreeCAD.Placement(V(60, 0, 0), FreeCAD.Rotation()))
    part("Shifted", baked(FreeCAD.Placement(V(40, 0, 0), FreeCAD.Rotation())), FreeCAD.Placement(V(0, 30, 0), FreeCAD.Rotation()))
    part("Turned", baked(TURN), FreeCAD.Placement(V(0, -40, 3), FreeCAD.Rotation(V(1, 0, 0), 180)))
    m = l_shape().mirror(V(0, 0, 0), V(1, 0, 0))
    part("Mirror", m, FreeCAD.Placement(V(0, 80, 0), FreeCAD.Rotation()))
    near = l_shape(); near.scale(1.00002)                 # a near-copy: fits within FIT_TOL, lands ~0.6 um off
    part("Near", near, FreeCAD.Placement(V(0, -90, 0), FreeCAD.Rotation()))
    tool = part("Tool", l_shape(), FreeCAD.Placement(V(-50, 0, 0), FreeCAD.Rotation()))
    base = part("Base", Part.makeBox(100, 100, 2, V(-80, -20, -1)), FreeCAD.Placement())
    cut = doc.addObject("Part::Cut", "Cut"); cut.Base = base; cut.Tool = tool; head.addObject(cut)
    for name, pl in (("MMaster", P0), ("MCopy", FreeCAD.Placement(V(0, 0, 50), FreeCAD.Rotation()))):
        mo = doc.addObject("Mesh::Feature", name); mo.Mesh = Mesh.Mesh(l_shape().tessellate(0.1)); mo.Placement = pl
        head.addObject(mo)
    doc.getObject("MCopy").addProperty("App::PropertyString", "StandInFor", "StandIn"); doc.getObject("MCopy").StandInFor = "Same"
    doc.getObject("Same").Visibility = False
    doc.recompute(); doc.saveAs(path); FreeCAD.closeDocument(doc.Name)


class Dupes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dupes_fc_")
        self.path = os.path.join(self.tmp, "fixture.FCStd")
        build_fixture(self.path)
        self.doc = FreeCAD.openDocument(self.path, True)

    def tearDown(self):
        FreeCAD.closeDocument(self.doc.Name)

    def groups(self):
        return {g.master.Name: g for g in dupes.find(self.doc, dupes.object_bytes(self.path))}

    def test_finds_the_copies_and_refuses_the_reflection(self):
        g = self.groups()
        self.assertEqual(len(g), 2)
        self.assertIn("Master", g)
        (mg,) = [x for x in g.values() if x.master.TypeId == "Mesh::Feature"]
        self.assertEqual(sorted(o.Name for o, _ in g["Master"].copies), ["Near", "Same", "Shifted", "Turned"])
        self.assertEqual(g["Master"].unfit[0][0].Name, "Mirror")
        self.assertEqual(g["Master"].unfit[0][1], "reflected")
        self.assertEqual({mg.master.Name, mg.copies[0][0].Name}, {"MMaster", "MCopy"})   # masters: first by Name

    def test_a_part_another_feature_uses_is_left_alone(self):
        self.assertFalse(dupes.candidate(self.doc.getObject("Tool")))
        self.assertTrue(dupes.candidate(self.doc.getObject("Master")))

    def test_savings_are_the_copies_file_bytes(self):
        sizes, g = dupes.object_bytes(self.path), self.groups()["Master"]
        self.assertEqual(g.saving, sum(sizes[n] for n in ("Near", "Same", "Shifted", "Turned")))
        self.assertGreater(g.saving, 0)

    def test_landing_predicts_and_drop_keeps_a_near_copy_real(self):
        g = self.groups()["Master"]
        land = dict(dupes.landing(g))
        self.assertGreater(land["Near"], 1e-6)
        self.assertLess(land["Near"], 0.01)
        for n in ("Same", "Shifted", "Turned"): self.assertLess(land[n], 1e-6, n)
        g.drop([n for n, d in land.items() if d > 1e-6])
        self.assertEqual(sorted(o.Name for o, _ in g.copies), ["Same", "Shifted", "Turned"])
        self.assertEqual(sorted(g.copy_names), ["Same", "Shifted", "Turned"])
        self.assertEqual(self.doc.getObject("Near").TypeId, "Part::Feature")       # landing() changes nothing

    def test_split_and_skip(self):
        gs = dupes.find(self.doc, split=lambda o: o.Name in ("Shifted", "Turned"), skip=("Same",))
        names = sorted(sorted([g.master.Name] + [o.Name for o, _ in g.copies]) for g in gs if g.master.TypeId == "Part::Feature")
        self.assertEqual(names, [["Master", "Near"], ["Shifted", "Turned"]])     # split apart; Same never considered

    def test_linking_keeps_every_copy_where_it_was(self):
        before = {n: linkgeo.gshape(self.doc.getObject(n)) for n in ("Same", "Shifted", "Turned")}
        mbefore = linkgeo.gmesh(self.doc.getObject("MMaster")).BoundBox   # MCopy sorts first: MMaster is its copy
        for g in self.groups().values():
            g.drop([n for n, d in dupes.landing(g) if d > 1e-6])
            for name, d in dupes.link_copies(self.doc, g):
                self.assertLess(d, 1e-6, name)
        path2 = os.path.join(self.tmp, "linked.FCStd"); self.doc.saveAs(path2)
        FreeCAD.closeDocument(self.doc.Name); self.doc = FreeCAD.openDocument(path2, True)
        for n, s in before.items():
            ln = self.doc.getObject(n)
            self.assertEqual(ln.TypeId, "App::Link", n)
            self.assertEqual(ln.LinkedObject.Name, "Master")
            self.assertEqual(ln.getParentGeoFeatureGroup().Name, "Head")
            a = linkgeo.gshape(ln)
            self.assertAlmostEqual(a.common(s).Volume, s.Volume, places=3, msg=n)   # the same solid, same place
        self.assertFalse(self.doc.getObject("Same").Visibility)                    # visibility kept
        mc = self.doc.getObject("MMaster")
        self.assertEqual(mc.TypeId, "App::Link")
        self.assertEqual(self.doc.getObject("MCopy").StandInFor, "Same")
        mb = linkgeo.gmesh(mc).BoundBox
        for k in ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax"):
            self.assertAlmostEqual(getattr(mb, k), getattr(mbefore, k), places=6)
        self.assertEqual(self.doc.getObject("Mirror").TypeId, "Part::Feature")      # the reflection stays real

    def test_the_file_shrinks(self):
        for g in self.groups().values(): dupes.link_copies(self.doc, g)
        path2 = os.path.join(self.tmp, "linked.FCStd"); self.doc.saveAs(path2)
        b1, b2 = dupes.object_bytes(self.path), dupes.object_bytes(path2)
        for n in ("Same", "Shifted", "Turned"):
            self.assertGreater(b1.get(n, 0), 500); self.assertLess(b2.get(n, 0), 50)   # a link stores no shape (12 B)


if __name__ in ("__main__", "test_dupes_fc"):            # freecadcmd runs a script as module "test_dupes_fc"
    try:
        r = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Dupes))
        print("OK" if r.wasSuccessful() else "FAILED")
        code = 0 if r.wasSuccessful() else 1
    except Exception:
        traceback.print_exc(); code = 1
    sys.stdout.flush(); os._exit(code)
