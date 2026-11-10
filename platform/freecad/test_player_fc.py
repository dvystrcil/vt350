# Tests for player.py's FreeCAD side (vt350#135 AC3) on a small fixture document built here: a frame's global
# translation moves objects inside a ROTATED App::Part by exactly that translation, Stop puts every Placement back,
# and the saved model's bytes never change. Needs FreeCAD:
#
#   APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage
#   $APP freecadcmd $PWD/platform/freecad/test_player_fc.py     # prints "Ran N tests" + "OK"/"FAILED", exit code 0/1
#
# Not in CI (no FreeCAD there); the plain-python3 side is test_player.py, which is.
#
# Fixture (global mm): App::Part "Rig (fixture)" at (100, 0, 0) turned 90 deg about Z, holding a group with "carriage"
# (a box) and, inside it too, "bed" (a box); outside it, "loose" (a box with no parent). Each is its own group.
import hashlib, os, shutil, sys, tempfile, traceback, unittest

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "platform/freecad")
sys.path.insert(0, HERE)
import FreeCAD, Part
import player

V = FreeCAD.Vector
ROOT_PL = FreeCAD.Placement(V(100, 0, 0), FreeCAD.Rotation(V(0, 0, 1), 90))


def build_fixture(path):
    doc = FreeCAD.newDocument("player_fixture")
    root = doc.addObject('App::Part', 'Root'); root.Label = "Rig (fixture)"; root.Placement = ROOT_PL
    grp = doc.addObject('App::DocumentObjectGroup', 'Grp'); root.addObject(grp)
    for name, into in (("Carriage", grp), ("Bed", grp), ("Loose", None)):
        o = doc.addObject('Part::Feature', name); o.Shape = Part.makeBox(10, 20, 30)
        o.Placement = FreeCAD.Placement(V(1, 2, 3), FreeCAD.Rotation(V(1, 0, 0), 30))
        if into: into.addObject(o)
    belt = doc.addObject('Part::Feature', 'Belt')             # a long loop: global Y -100 .. 500, stored local to root
    s = Part.makeBox(10, 600, 5, V(0, -100, 0)); s.Placement = ROOT_PL.inverse().multiply(s.Placement)
    belt.Shape = s; belt.Label = "belt (fixture)"; grp.addObject(belt)
    doc.recompute(); doc.saveAs(path); FreeCAD.closeDocument(doc.Name)


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def gbox(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); b = s.BoundBox
    return (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)


class FreeCADMover(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="player-fc-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.model = os.path.join(self.tmp, "fixture.FCStd")
        build_fixture(self.model)
        self.sha = sha(self.model)
        self.copy, cleanup = player.private_copy(self.model)
        self.addCleanup(cleanup)
        self.doc = FreeCAD.openDocument(self.copy)
        self.addCleanup(lambda: FreeCAD.closeDocument(self.doc.Name))
        self.objs = player.resolve(self.doc, {"carriage": ["Carriage"], "bed": ["Bed"], "loose": ["Loose"]})
        self.box0 = {g: gbox(o[0]) for g, o in self.objs.items()}
        self.pl0 = {g: o[0].Placement.copy() for g, o in self.objs.items()}
        self.m = player.Mover(self.objs, player.FreeCADBackend())

    def assertMovedBy(self, g, d):
        got = gbox(self.objs[g][0])
        want = tuple(a + d[i % 3] for i, a in enumerate(self.box0[g]))
        for a, b in zip(got, want):
            self.assertAlmostEqual(a, b, places=6, msg=f"{g}: box {got} != {want}")

    def test_the_fixture_parent_is_rotated(self):              # else the test below proves nothing
        self.assertFalse(self.objs["carriage"][0].getGlobalPlacement().isSame(self.objs["carriage"][0].Placement, 1e-6))

    def test_a_global_translation_moves_by_exactly_that_inside_a_rotated_parent(self):
        self.m.apply({"groups": {"carriage": [10.0, -20.0, 0.5], "bed": [0.0, 0.0, -93.32], "loose": [3.0, 0.0, 0.0]}})
        self.assertMovedBy("carriage", (10.0, -20.0, 0.5))
        self.assertMovedBy("bed", (0.0, 0.0, -93.32))
        self.assertMovedBy("loose", (3.0, 0.0, 0.0))

    def test_frames_do_not_accumulate(self):
        for x in (5.0, 7.0, 2.0):
            self.m.apply({"groups": {"carriage": [x, 0.0, 0.0]}})
        self.assertMovedBy("carriage", (2.0, 0.0, 0.0))

    def test_restore_puts_every_placement_back_exactly(self):
        self.m.apply({"groups": {"carriage": [10.0, -20.0, 0.5], "bed": [0.0, 0.0, -93.32], "loose": [3.0, 1.0, 0.0]}})
        self.assertEqual(self.m.restore(), 3)
        for g, o in self.objs.items():
            self.assertTrue(o[0].Placement.isSame(self.pl0[g], 1e-12), g)
            self.assertMovedBy(g, (0.0, 0.0, 0.0))

    def test_the_rotation_is_untouched(self):
        self.m.apply({"groups": {"carriage": [10.0, -20.0, 0.5]}})
        self.assertTrue(self.objs["carriage"][0].Placement.Rotation.isSame(self.pl0["carriage"].Rotation, 1e-12))

    def test_the_saved_model_never_changes(self):              # moves and even a save land on the copy only
        self.m.apply({"groups": {"carriage": [10.0, 0.0, 0.0]}})
        self.doc.save()
        self.assertEqual(sha(self.model), self.sha)
        self.assertNotEqual(os.path.dirname(self.doc.FileName), self.tmp)


class Clip(unittest.TestCase):
    """A clipped object is shown cut down to its box, moves with its group, and the original never moves."""
    BOX = [-50.0, 243.2, -10.0, 60.0, 294.5, 20.0]

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="player-fc-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        model = os.path.join(self.tmp, "fixture.FCStd"); build_fixture(model)
        copy, cleanup = player.private_copy(model); self.addCleanup(cleanup)
        self.doc = FreeCAD.openDocument(copy)
        self.addCleanup(lambda: FreeCAD.closeDocument(self.doc.Name))
        self.belt = self.doc.getObject("Belt")
        self.pl0 = self.belt.Placement.copy()
        self.objs = player.clip_objects(self.doc, player.resolve(self.doc, {"belt": ["Belt"], "bed": ["Bed"]}),
                                        {"Belt": self.BOX})

    def test_the_fixture_belt_runs_past_the_box(self):           # else clipping proves nothing
        b = gbox(self.belt)
        self.assertLess(b[1], self.BOX[1]); self.assertGreater(b[4], self.BOX[4])

    def test_the_group_holds_the_clipped_part_in_the_belts_place(self):
        (c,) = self.objs["belt"]
        self.assertNotEqual(c.Name, "Belt")
        for a, b in zip(gbox(c), (0.0, 243.2, 0.0, 10.0, 294.5, 5.0)):
            self.assertAlmostEqual(a, b, places=6)
        self.assertEqual([o.Name for o in self.objs["bed"]], ["Bed"])

    def test_the_clipped_part_moves_and_the_original_does_not(self):
        m = player.Mover(self.objs, player.FreeCADBackend())
        m.apply({"groups": {"belt": [0.0, -263.725, 0.0]}})
        self.assertAlmostEqual(gbox(self.objs["belt"][0])[1], 243.2 - 263.725, places=6)
        self.assertTrue(self.belt.Placement.isSame(self.pl0, 1e-12))
        m.restore()
        self.assertAlmostEqual(gbox(self.objs["belt"][0])[1], 243.2, places=6)


if __name__ in ("__main__", "test_player_fc"):           # freecadcmd runs a script as module "test_player_fc"
    try:
        r = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (FreeCADMover, Clip)))
        print("OK" if r.wasSuccessful() else "FAILED")
        code = 0 if r.wasSuccessful() else 1
    except Exception:
        traceback.print_exc(); code = 1
    sys.stdout.flush(); os._exit(code)
