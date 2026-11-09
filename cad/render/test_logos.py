# Tests for logos.py: the Voron logo inset picked by face (#74). Needs FreeCAD (not in the stdlib CI job):
#   $APP freecadcmd $PWD/cad/render/test_logos.py
# Fixture: a 40 x 30 x 3 plate (top at Z 3) with three 1 mm deep slots in its top: the logo-cap shape, built in the
# test. It is moved around so the depth is shown to be measured from the part's own outer face, not a global level.
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD, Part
import logos
V = FreeCAD.Vector


def plate(slots=3, depth=1.0, at=V(0, 0, 0)):
    s = Part.makeBox(40, 30, 3)
    for i in range(slots):
        s = s.cut(Part.makeBox(4, 20, depth, V(6 + 10 * i, 5, 3 - depth)))
    s = s.removeSplitter(); s.translate(at); return s


class Inset(unittest.TestCase):
    def test_three_slots_give_floors_and_walls(self):
        inset, rest = logos.inset(plate(), V(0, 0, 1), 1.0)
        floors = [f for f in inset if abs(f.CenterOfMass.z - 2.0) < 1e-6 and f.Surface.__class__.__name__ == "Plane"]
        self.assertEqual(len(floors), 3)
        self.assertEqual(len(inset), 3 + 3 * 4)                     # each slot: a floor and 4 walls
        self.assertAlmostEqual(sum(f.Area for f in floors), 3 * 4 * 20, places=6)

    def test_inset_and_rest_partition_the_faces(self):
        s = plate(); inset, rest = logos.inset(s, V(0, 0, 1), 1.0)
        self.assertEqual(len(inset) + len(rest), len(s.Faces))
        self.assertFalse(any(f.isSame(g) for f in inset for g in rest))
        self.assertAlmostEqual(sum(f.Area for f in inset + rest), s.Area, places=6)

    def test_depth_is_from_the_parts_own_outer_face(self):        # same part, anywhere in the model
        a, _ = logos.inset(plate(at=V(-245, 200, -14)), V(0, 0, 1), 1.0)
        self.assertEqual(len(a), 15)

    def test_other_facing_direction(self):                          # hinge-style: logo faces -Y
        s = plate(); s.rotate(V(0, 0, 0), V(1, 0, 0), 90)             # top (+Z) now faces -Y
        inset, _ = logos.inset(s, V(0, -1, 0), 1.0)
        self.assertEqual(len(inset), 15)

    def test_wrong_depth_raises(self):
        with self.assertRaises(RuntimeError):
            logos.inset(plate(), V(0, 0, 1), 1.5)

    def test_wrong_slot_count_raises(self):
        with self.assertRaises(RuntimeError):
            logos.inset(plate(slots=2), V(0, 0, 1), 1.0)

    def test_wall_must_touch_a_floor(self):                         # a step elsewhere at the same depth band is not inset
        s = plate().cut(Part.makeBox(2, 30, 0.5, V(38, 0, 2.5))).removeSplitter()
        inset, _ = logos.inset(s, V(0, 0, 1), 1.0)
        self.assertEqual(len(inset), 15)


class Split(unittest.TestCase):
    def test_known_labels(self):
        self.assertIn("StealthMax 3.2_LidFrontHinge", logos.LOGOS)
        self.assertIn("StealthMax M_2.5a_LogoCap", logos.LOGOS)

    def test_split_returns_none_for_other_parts(self):
        self.assertIsNone(logos.split("StealthMax M_2.0_Body", plate()))

    def test_split_matches_a_copy_suffix(self):                    # FreeCAD numbers copies: Label001
        lab = "StealthMax M_2.5a_LogoCap"
        n, d = logos.LOGOS[lab]
        logos.LOGOS["Fixture logo"] = (V(0, 0, 1), 1.0)
        try:
            r = logos.split("Fixture logo001", plate())
            self.assertIsNotNone(r); self.assertEqual(len(r[0]), 15)
        finally:
            del logos.LOGOS["Fixture logo"]


if __name__ in ("__main__", "test_logos"):
    suite = unittest.TestSuite()
    for c in (Inset, Split): suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(c))
    ok = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite).wasSuccessful()
    sys.stdout.flush(); os._exit(0 if ok else 1)
