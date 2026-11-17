# Tests that the walkers treat an App::Link to a part like the part itself (vt350#195 AC1/AC3: copies become links
# so the file stores each shape once). A link is not a Part::Feature and has no getGlobalPlacement, so before this
# every walker (litelib.Model, clashlib, part_index, player, export_meshes, tess_cost) silently dropped links.
# Needs FreeCAD:
#
#   APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage
#   $APP freecadcmd $PWD/platform/freecad/test_links_fc.py     # prints "Ran N tests" + "OK"/"FAILED", exit code 0/1
#
# Not in CI (no FreeCAD there).
#
# Fixture (saved and reopened, as a model would be): App::Part "Root" at (100, 0, 0) turned 90 deg about Z, holding
# App::Part "Inner" (turned 30 deg about X). "Orig" (an L-shaped, so orientation-revealing, solid) sits in Inner.
# In Root: "Copy", a link to Orig with its own turned Placement, and "Ref", a Part::Feature with Orig's raw shape at
# that same Placement: Ref is what Copy must look like to every walker. The same pair for a mesh ("MOrig", "MCopy",
# "MRef"), and a link to an App::Part ("PartLink"), which is not a leaf.
import os, sys, tempfile, traceback, unittest

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "platform/freecad")
sys.path.insert(0, HERE)
import FreeCAD, Part, Mesh
import linkgeo, litelib, player

V = FreeCAD.Vector
ROOT_PL = FreeCAD.Placement(V(100, 0, 0), FreeCAD.Rotation(V(0, 0, 1), 90))
INNER_PL = FreeCAD.Placement(V(0, 5, 7), FreeCAD.Rotation(V(1, 0, 0), 30))
ORIG_PL = FreeCAD.Placement(V(3, 0, 0), FreeCAD.Rotation(V(0, 1, 0), 15))
COPY_PL = FreeCAD.Placement(V(-40, 12, 9), FreeCAD.Rotation(V(1, 1, 0), 120))


def l_shape():
    return Part.makeBox(30, 10, 5).fuse(Part.makeBox(10, 10, 25)).removeSplitter()


def build_fixture(path):
    doc = FreeCAD.newDocument("links_fixture")
    root = doc.addObject("App::Part", "Root"); root.Placement = ROOT_PL
    inner = doc.addObject("App::Part", "Inner"); inner.Placement = INNER_PL; root.addObject(inner)
    orig = doc.addObject("Part::Feature", "Orig"); orig.Shape = l_shape(); orig.Placement = ORIG_PL; inner.addObject(orig)
    morig = doc.addObject("Mesh::Feature", "MOrig"); morig.Mesh = Mesh.Mesh(l_shape().tessellate(0.1))
    morig.Placement = ORIG_PL; inner.addObject(morig)
    for name, target in (("Copy", orig), ("MCopy", morig), ("PartLink", inner)):
        ln = doc.addObject("App::Link", name); ln.LinkedObject = target; ln.Placement = COPY_PL; root.addObject(ln)
    ref = doc.addObject("Part::Feature", "Ref"); ref.Shape = l_shape(); ref.Placement = COPY_PL; root.addObject(ref)
    mref = doc.addObject("Mesh::Feature", "MRef"); mref.Mesh = Mesh.Mesh(l_shape().tessellate(0.1))
    mref.Placement = COPY_PL; root.addObject(mref)
    doc.recompute(); doc.saveAs(path); FreeCAD.closeDocument(doc.Name)


def box6(b):
    return (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)


class Links(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="links_fc_")
        cls.path = os.path.join(cls.tmp, "fixture.FCStd")
        build_fixture(cls.path)
        cls.doc = FreeCAD.openDocument(cls.path, True)
        cls.o = {n: cls.doc.getObject(n) for n in ("Orig", "Copy", "Ref", "MOrig", "MCopy", "MRef", "PartLink", "Inner")}

    @classmethod
    def tearDownClass(cls):
        FreeCAD.closeDocument(cls.doc.Name)

    def assertSamePlacement(self, a, b):
        self.assertTrue(a.isSame(b, 1e-9), f"{a} != {b}")

    def assertSameBox(self, a, b):
        for x, y in zip(box6(a), box6(b)):
            self.assertAlmostEqual(x, y, places=6)

    def test_gplace_agrees_with_freecad_for_ordinary_objects(self):
        for n in ("Orig", "Ref", "MOrig", "Inner"):
            self.assertSamePlacement(litelib.gplace(self.o[n]), self.o[n].getGlobalPlacement())

    def test_a_link_has_no_getGlobalPlacement_but_gplace_works(self):
        self.assertFalse(hasattr(self.o["Copy"], "getGlobalPlacement"))      # why gplace exists
        self.assertSamePlacement(litelib.gplace(self.o["Copy"]), litelib.gplace(self.o["Ref"]))

    def test_is_leaf(self):
        self.assertTrue(litelib.is_leaf(self.o["Copy"]))
        self.assertTrue(litelib.is_leaf(self.o["Ref"]))
        self.assertFalse(litelib.is_leaf(self.o["PartLink"]))                # a link to a container is not a part
        self.assertFalse(litelib.is_leaf(self.o["MCopy"]))                   # nor is one to a mesh
        self.assertFalse(litelib.is_leaf(self.o["Inner"]))

    def test_gshape_of_a_link_is_its_reference_part(self):
        a, b = litelib.gshape(self.o["Copy"]), litelib.gshape(self.o["Ref"])
        self.assertSameBox(a.BoundBox, b.BoundBox)
        self.assertAlmostEqual(a.Volume, b.Volume, places=6)
        self.assertEqual(len(a.Solids), len(b.Solids))   # a link's Shape is a Compound wrapper (no CenterOfMass)
        self.assertAlmostEqual((a.Solids[0].CenterOfMass - b.Solids[0].CenterOfMass).Length, 0.0, places=6)
        self.assertAlmostEqual(a.common(b).Volume, b.Volume, places=3)       # the same solid, not just the same box

    def test_gmesh_of_a_mesh_link_is_its_reference_mesh(self):
        self.assertTrue(litelib.is_mesh(self.o["MCopy"]) and litelib.is_mesh(self.o["MRef"]))
        self.assertFalse(litelib.is_mesh(self.o["Copy"]))
        self.assertSameBox(litelib.gmesh(self.o["MCopy"]).BoundBox, litelib.gmesh(self.o["MRef"]).BoundBox)

    def test_model_lists_the_link_with_its_global_shape(self):
        m = litelib.Model(self.doc)
        names = {o.Name for o in m.leaves}
        self.assertTrue({"Orig", "Copy", "Ref"} <= names)
        self.assertFalse({"PartLink", "MCopy", "Inner"} & names)
        self.assertSameBox(m.shapes["Copy"].BoundBox, m.shapes["Ref"].BoundBox)

    def test_player_moves_a_link_by_a_global_translation(self):
        be, d = player.FreeCADBackend(), (1.5, -2.0, 3.25)
        for n in ("Copy", "Ref"):
            o = self.o[n]; before = litelib.gplace(o).Base
            saved = be.save(o); be.move(o, saved, d)
            moved = litelib.gplace(o).Base - before
            self.assertAlmostEqual((moved - V(*d)).Length, 0.0, places=9, msg=n)
            be.restore(o, saved)
            self.assertAlmostEqual((litelib.gplace(o).Base - before).Length, 0.0, places=9)


if __name__ in ("__main__", "test_links_fc"):            # freecadcmd runs a script as module "test_links_fc"
    try:
        r = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Links))
        print("OK" if r.wasSuccessful() else "FAILED")
        code = 0 if r.wasSuccessful() else 1
    except Exception:
        traceback.print_exc(); code = 1
    sys.stdout.flush(); os._exit(code)
