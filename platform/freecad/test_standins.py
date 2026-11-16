# Unit tests for standins.py (vt350#195 AC3): fitting a coil spring's envelope from points on its surface. No FreeCAD,
# so they run in CI:   python3 platform/freecad/test_standins.py      # "Ran N tests" + "OK"
import math, os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import standins


def helix_tube(axis=1, c=(1.0, 2.0), R=3.4, r=0.42, turns=6.25, pitch=1.56, lo=-59.0, nu=400, nv=12):
    """Points on a round wire wound as a helix along coordinate `axis`, its coil centred at c in the other two."""
    pts = []
    for i in range(nu + 1):
        t = turns * 2 * math.pi * i / nu
        a = lo + r + pitch * t / (2 * math.pi)
        for j in range(nv):
            v = 2 * math.pi * j / nv
            rho = R + r * math.cos(v)                       # the wire's cross-section, in the coil's radial plane
            u, w = c[0] + rho * math.cos(t), c[1] + rho * math.sin(t)
            h = a + r * math.sin(v)
            p = [0.0, 0.0, 0.0]
            others = [k for k in range(3) if k != axis]
            p[axis], p[others[0]], p[others[1]] = h, u, w
            pts.append(tuple(p))
    return pts


class FitCoil(unittest.TestCase):
    def test_axis_and_centre(self):
        f = standins.fit_coil(helix_tube())
        self.assertEqual(f["axis"], 1)
        self.assertAlmostEqual(f["centre"][0], 1.0, places=2)
        self.assertAlmostEqual(f["centre"][1], 2.0, places=2)

    def test_partial_last_turn(self):
        """A coil whose wire ends part-way round a turn: the fit is still the coil's own axis and radius."""
        for turns in (1.3, 6.1):
            f = standins.fit_coil(helix_tube(turns=turns))
            self.assertEqual(f["axis"], 1)
            self.assertAlmostEqual(f["centre"][0], 1.0, delta=0.01)   # Kasa's fit leans a little on an uneven arc
            self.assertAlmostEqual(f["centre"][1], 2.0, delta=0.01)
            self.assertAlmostEqual(f["rmax"], 3.4 + 0.42, delta=0.01)

    def test_tube_holds_every_point(self):
        """rmin/rmax are measured about the fitted centre, so the tube holds the whole coil even if the fit leans."""
        for turns in (1.3, 6.25):
            pts = helix_tube(turns=turns); f = standins.fit_coil(pts); (cx, cy) = f["centre"]
            for p in pts:
                rho = math.hypot(p[0] - cx, p[2] - cy)
                self.assertTrue(f["rmin"] - 1e-9 <= rho <= f["rmax"] + 1e-9 and f["lo"] <= p[1] <= f["hi"])

    def test_radial_range_is_the_wire(self):
        f = standins.fit_coil(helix_tube())
        self.assertAlmostEqual(f["rmin"], 3.4 - 0.42, places=2)
        self.assertAlmostEqual(f["rmax"], 3.4 + 0.42, places=2)

    def test_axial_extent(self):
        f = standins.fit_coil(helix_tube())
        self.assertAlmostEqual(f["lo"], -59.0, places=2)
        self.assertAlmostEqual(f["hi"], -59.0 + 2 * 0.42 + 6.25 * 1.56, places=2)

    def test_other_axes(self):
        for ax in (0, 2):
            f = standins.fit_coil(helix_tube(axis=ax, c=(-5.0, 7.0)))
            self.assertEqual(f["axis"], ax)
            self.assertAlmostEqual(f["centre"][0], -5.0, places=2)
            self.assertAlmostEqual(f["centre"][1], 7.0, places=2)

    def test_not_a_coil(self):
        """Points on a solid block don't sit at one radius from any axis: the spread says so."""
        pts = [(x, y, z) for x in range(-3, 4) for y in range(-3, 4) for z in range(-5, 6)]
        f = standins.fit_coil(pts)
        self.assertGreater(f["spread"], 2.0)

    def test_coil_spread_is_the_wire_diameter(self):
        self.assertAlmostEqual(standins.fit_coil(helix_tube())["spread"], 2 * 0.42, places=2)


if __name__ == "__main__":
    unittest.main()
