"""Tests for frame_view.py (vt350#220): framing distance and the turntable's cameras. Stdlib only (CI: viewer.yml).

    python3 platform/viewer/test_frame_view.py
"""
import math, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frame_view as fv

BOX = [-100, -50, 0, 100, 50, 200]                      # centre (0, 0, 100)


class Frame(unittest.TestCase):
    def test_looks_at_centre_from_direction(self):
        pos, look = fv.frame(BOX, [0, -1, 0], 35)
        self.assertEqual(look, [0, 0, 100])
        self.assertAlmostEqual(pos[0], 0); self.assertAlmostEqual(pos[2], 100); self.assertLess(pos[1], -100)

    def test_sphere_fits_vertical_fov(self):
        pos, look = fv.frame(BOX, [1, 1, 1], 35, fill=1.0)
        r = math.dist(BOX[:3], BOX[3:]) / 2
        vfov = 2 * math.atan(math.tan(math.atan(18 / 35)) / (16 / 9))
        self.assertAlmostEqual(math.asin(r / math.dist(pos, look)), vfov / 2, places=9)


class Turntable(unittest.TestCase):
    def test_ring(self):
        vs = fv.turntable(BOX, 4, [0, 30], 35)
        self.assertEqual([v["name"] for v in vs][:4], ["tt-e00-a000", "tt-e00-a090", "tt-e00-a180", "tt-e00-a270"])
        self.assertEqual(len(vs), 8)
        d = [math.dist(v["pos"], v["look"]) for v in vs]
        self.assertAlmostEqual(max(d), min(d), places=2)             # all at one distance (positions rounded to 0.001)
        self.assertLess(vs[0]["pos"][1], 0)                          # az 0: in front (-Y)
        self.assertGreater(vs[1]["pos"][0], 0)                       # az 90: on +X
        self.assertAlmostEqual(vs[4]["pos"][2] - 100, d[4] * math.sin(math.radians(30)), places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
