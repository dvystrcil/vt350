# SPDX-License-Identifier: GPL-3.0-or-later
"""frame.py (vt350#322). The plain tests run in python3; the solver tests need CalculiX: set CCX to a ccx >= 2.20
binary (they skip without it). The expected numbers are the textbook beam formulas."""
import math, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frame as F

PROF = {"2020": {"w": 20, "h": 20, "A": 183, "Iw": 7420, "Ih": 7420, "J": 3000},
        "2040": {"w": 40, "h": 20, "A": 324, "Iw": 5.13e4, "Ih": 1.358e4, "J": 6000}}
AL = {"E": 69000.0, "nu": 0.33, "rho": 2.7e-9}
CCX = os.environ.get("CCX")


def part(label, x, y, z):
    return {"name": label.replace(" ", "_"), "label": label,
            "bbox": {"xmin": x[0], "xmax": x[1], "ymin": y[0], "ymax": y[1], "zmin": z[0], "zmax": z[1]}}


def cantilever():
    """A 2040 along X, 500 long, its wide side along Z."""
    return {"parts": [part("2040 beam", (0, 500), (-10, 10), (-20, 20))]}


def ell():
    """A 2020 upright (Z 0..500) and a 2020 arm along X resting on its side at the top (X 10..410)."""
    return {"parts": [part("2020 up", (-10, 10), (-10, 10), (0, 500)), part("2020 arm", (10, 410), (-10, 10), (480, 500))]}


class Bars(unittest.TestCase):
    def test_axis_centre_and_wide_side(self):
        [b] = F.bars_from_index(cantilever(), PROF)
        self.assertEqual((b.axis, b.lo, b.hi, b.c, b.wide), (0, 0, 500, {1: 0.0, 2: 0.0}, 2))

    def test_only_profile_labels(self):
        ix = cantilever(); ix["parts"].append(part("Bed plate", (0, 300), (0, 300), (0, 6)))
        self.assertEqual(len(F.bars_from_index(ix, PROF)), 1)

    def test_box_not_matching_its_profile_is_an_error(self):
        with self.assertRaises(F.FrameError):
            F.bars_from_index({"parts": [part("2040 odd", (0, 500), (-10, 10), (-10, 10))]}, PROF)

    def test_longest_prefix_wins(self):
        prof = dict(PROF, **{"20": {"w": 20, "h": 20, "A": 1, "Iw": 1, "Ih": 1, "J": 1}})
        [b] = F.bars_from_index(cantilever(), prof)
        self.assertEqual(b.profile, "2040")


class Joints(unittest.TestCase):
    def test_corner_joint_is_offset_by_the_half_widths(self):
        bars = F.bars_from_index(ell(), PROF)
        self.assertEqual(F.joints(bars), [(0, 490.0, 1, 10)])
        m = F.Mesh(bars, F.joints(bars))
        [(a, b, _)] = m.links
        self.assertAlmostEqual(math.dist(m.nodes[a - 1], m.nodes[b - 1]), math.hypot(10, 0), places=6)

    def test_apart_bars_dont_join(self):
        ix = ell(); ix["parts"][1] = part("2020 arm", (12, 410), (-10, 10), (480, 500))
        self.assertEqual(F.joints(F.bars_from_index(ix, PROF)), [])

    def test_parallel_side_by_side_join_at_both_overlap_ends(self):
        ix = {"parts": [part("2020 a", (0, 300), (-10, 10), (0, 20)), part("2020 b", (100, 500), (10, 30), (0, 20))]}
        self.assertEqual(F.joints(F.bars_from_index(ix, PROF)), [(0, 100, 1, 100), (0, 300, 1, 300)])

    def test_meeting_centre_lines_share_a_node(self):
        ix = {"parts": [part("2020 a", (0, 300), (-10, 10), (-10, 10)), part("2020 b", (300, 600), (-10, 10), (-10, 10))]}
        bars = F.bars_from_index(ix, PROF)
        m = F.Mesh(bars, F.joints(bars))
        self.assertEqual(m.links, [])
        self.assertEqual(len(m.nodes), 25)                         # 12 + 12 elements, one shared node


class Deck(unittest.TestCase):
    def test_elements_no_longer_than_max(self):
        bars = F.bars_from_index(cantilever(), PROF)
        m = F.Mesh(bars, [], max_elem=30)
        self.assertEqual(len(m.elems), 17)
        self.assertTrue(all(math.dist(m.nodes[a - 1], m.nodes[b - 1]) <= 30 + 1e-9 for a, b, _ in m.elems))

    def test_section_line_uses_the_wide_side(self):
        bars = F.bars_from_index(cantilever(), PROF)
        m = F.Mesh(bars, [])
        inp = F.deck(m, PROF, AL, {"name": "rigid"}, {"name": "t", "kind": "static", "fixed": [m.at(0, 0)]})
        i = inp.splitlines().index("*BEAM SECTION, ELSET=B0, MATERIAL=FRAME, SECTION=GENERAL")
        self.assertEqual(inp.splitlines()[i + 1:i + 3], ["324, 51300, 0., 13580, 6000", "0, 0, 1"])

    def test_inertial_load_opposes_the_acceleration(self):
        bars = F.bars_from_index(cantilever(), PROF)
        m = F.Mesh(bars, [])
        inp = F.deck(m, PROF, AL, {"name": "rigid"},
                     {"name": "t", "kind": "static", "fixed": [1], "masses": [(m.at(0, 500), 0.002)], "accel": (3000, 0, 0)})
        self.assertIn(f"{m.at(0, 500)}, 1, -6", inp)

    def test_read_dat(self):
        dat = """
 displacements (vx,vy,vz,rx,ry,rz) for set NALL and time  0.1000000E+01

        21  0.000000E+00  4.446720E+00  0.000000E+00  0.000000E+00  0.000000E+00  1.334016E-02

     E I G E N V A L U E   O U T P U T

 MODE NO    EIGENVALUE                       FREQUENCY
                                     REAL PART            IMAGINARY PART
                           (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

      1   0.2116254E+06   0.4600276E+03   0.7321567E+02   0.0000000E+00
      2   0.7977163E+06   0.8931497E+03   0.1421492E+03   0.0000000E+00

     P A R T I C I P A T I O N   F A C T O R S
"""
        r = F.read_dat(dat)
        self.assertAlmostEqual(r["u"][21][1], 4.44672)
        self.assertEqual(r["freq_hz"], [73.21567, 142.1492])


class Solver(unittest.TestCase if CCX else object):     # defined only with CCX: CI's check wants a bare "OK"
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(); self.addCleanup(self._tmp.cleanup)

    def solve(self, ix, style, case):
        bars = F.bars_from_index(ix, PROF)
        m = F.Mesh(bars, F.joints(bars))
        case = case(m)
        return m, F.run(F.deck(m, PROF, AL, style, case), self._tmp.name, CCX, case["name"])

    def test_cantilever_both_ways(self):
        E, L, P = AL["E"], 500.0, 100.0
        for dof, I in ((2, 1.358e4), (3, 5.13e4)):                  # narrow way (Y), wide way (Z)
            m, r = self.solve(cantilever(), {"name": "rigid"}, lambda m: {
                "name": f"c{dof}", "kind": "static", "fixed": [m.at(0, 0)], "loads": [(m.at(0, 500), dof, P)]})
            self.assertAlmostEqual(r["u"][m.at(0, 500)][dof - 1], P * L ** 3 / (3 * E * I), delta=1e-3)

    def test_cantilever_first_modes(self):
        m, r = self.solve(cantilever(), {"name": "rigid"}, lambda m: {
            "name": "f", "kind": "frequency", "fixed": [m.at(0, 0)], "modes": 2})
        f = lambda I: 1.875 ** 2 / (2 * math.pi * 500 ** 2) * math.sqrt(AL["E"] * I / (AL["rho"] * 324))
        for got, want in zip(r["freq_hz"], (f(1.358e4), f(5.13e4))):
            self.assertAlmostEqual(got / want, 1, delta=0.01)

    def test_spring_joint_adds_m_over_k(self):
        k, w = 2e6, 9.81
        case = lambda m: {"name": "l", "kind": "static", "fixed": [m.at(0, 0)], "loads": [(m.at(1, 410), 3, -w)]}
        m, rigid = self.solve(ell(), {"name": "rigid"}, case)
        _, spring = self.solve(ell(), {"name": "spring", "k_rot": k}, case)
        extra = spring["u"][m.at(1, 410)][2] - rigid["u"][m.at(1, 410)][2]
        self.assertAlmostEqual(extra, -w * 410 / k * 400, delta=0.01)   # the joint turns M/k; the 400 mm arm swings


if __name__ == "__main__":
    unittest.main()
