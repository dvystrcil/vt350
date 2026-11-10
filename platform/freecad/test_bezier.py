# Tests for bezier.py (#6): the bowden tube's cubic Bezier (vertical out of the inlet, into the exit along its
# direction), its smallest bend radius, and the handle search that maximises it. Plain python3, no FreeCAD, so they
# run in CI:
#   python3 platform/freecad/test_bezier.py      # "Ran N tests" + "OK"
import math, os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bezier


class Curvature(unittest.TestCase):
    def test_a_straight_line_has_no_bend(self):
        poles = [(0, 0, 0), (0, 0, 10), (0, 0, 20), (0, 0, 30)]
        self.assertEqual(bezier.min_radius(poles), math.inf)

    def test_a_quarter_circle_approximation_has_radius_near_r(self):
        r, k = 50.0, 4 / 3 * (math.sqrt(2) - 1)           # the standard cubic quarter circle
        poles = [(r, 0, 0), (r, r * k, 0), (r * k, r, 0), (0, r, 0)]
        rmin = bezier.min_radius(poles, n=2000)
        self.assertLess(abs(rmin - r) / r, 0.01)
        self.assertLessEqual(rmin, r)                      # the approximation is a hair tighter somewhere

    def test_radius_scales_with_the_curve(self):
        poles = [(0, 0, 0), (0, 0, 40), (30, 0, 80), (60, 0, 80)]
        big = [tuple(2 * c for c in p) for p in poles]
        self.assertAlmostEqual(bezier.min_radius(big), 2 * bezier.min_radius(poles), places=6)

    def test_radius_is_the_same_in_any_plane(self):
        a = [(0, 0, 0), (0, 0, 40), (30, 0, 80), (60, 0, 80)]
        b = [(0, 0, 0), (0, 0, 40), (0, 30, 80), (0, 60, 80)]
        c = [(0, 0, 0), (40, 0, 0), (80, 30, 0), (80, 60, 0)]
        self.assertAlmostEqual(bezier.min_radius(a), bezier.min_radius(b), places=9)
        self.assertAlmostEqual(bezier.min_radius(a), bezier.min_radius(c), places=9)

    def test_the_tightest_point_is_found_not_just_the_ends(self):
        # an S bend: tight in the middle region, straight-ish at both ends
        poles = [(0, 0, 0), (0, 0, 100), (20, 0, -20), (20, 0, 80)]
        ends = min(bezier.radius_at(poles, 0.0), bezier.radius_at(poles, 1.0))
        self.assertLess(bezier.min_radius(poles), ends)

    def test_a_curve_bending_in_all_three_axes_matches_the_circle_through_three_close_points(self):
        poles = [(0, 0, 0), (0, 0, 60), (40, 70, 110), (90, 120, 150)]
        for u in (0.2, 0.5, 0.8):
            h = 1e-4
            def B(t):
                v = 1 - t
                return [v ** 3 * poles[0][i] + 3 * v * v * t * poles[1][i] + 3 * v * t * t * poles[2][i]
                        + t ** 3 * poles[3][i] for i in range(3)]
            a, b, c = B(u - h), B(u), B(u + h)
            ab, bc, ca = (math.dist(a, b), math.dist(b, c), math.dist(c, a))
            cr = [(b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
                  (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
                  (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])]
            circ = ab * bc * ca / (2 * math.sqrt(sum(x * x for x in cr)))       # circumradius
            self.assertLess(abs(bezier.radius_at(poles, u) - circ) / circ, 1e-4, msg=f"u {u}")

    def test_the_last_sample_is_the_exit_end(self):
        # tightest exactly at u = 1: the samples must include it
        poles = [(0, 0, 0), (0, 0, 100), (10, 0, 110), (12, 0, 110)]
        self.assertEqual(bezier.min_radius(poles, n=10), bezier.radius_at(poles, 1.0))


class Poles(unittest.TestCase):
    def test_poles_leave_vertically_and_arrive_along_the_exit(self):
        p = bezier.tube_poles((1, 2, 3), (50, 60, 200), (0, 0.6, 0.8), 40.0, 25.0)
        self.assertEqual(p[0], (1, 2, 3)); self.assertEqual(p[1], (1, 2, 43))
        self.assertEqual(p[3], (50, 60, 200))
        for a, b in zip(p[2], (50, 60 - 15.0, 200 - 20.0)): self.assertAlmostEqual(a, b)


class Best(unittest.TestCase):
    P0, P1, ED = (0, 0, 0), (120, 300, 200), (0, 0.7071067811865476, 0.7071067811865476)

    def test_the_best_handles_beat_or_match_every_handle_on_the_grid(self):
        grid = list(range(20, 401, 20))
        a, b, r = bezier.best_handles(self.P0, self.P1, self.ED, grid, grid)
        for x in grid:
            for y in grid:
                self.assertLessEqual(bezier.min_radius(bezier.tube_poles(self.P0, self.P1, self.ED, x, y)), r + 1e-9)
        self.assertIn(a, grid); self.assertIn(b, grid)
        self.assertAlmostEqual(r, bezier.min_radius(bezier.tube_poles(self.P0, self.P1, self.ED, a, b)))

    def test_a_tie_keeps_the_first_pair(self):
        a, b, r = bezier.best_handles((0, 0, 0), (0, 0, 100), (0, 0, 1), [10, 20], [30, 40])
        self.assertEqual((a, b, r), (10, 30, math.inf))

    def test_ranked_handles_are_sorted_by_radius_and_start_with_the_best(self):
        grid = list(range(20, 401, 40))
        ranked = bezier.ranked_handles(self.P0, self.P1, self.ED, grid, grid)
        self.assertEqual(len(ranked), len(grid) ** 2)
        self.assertEqual(ranked[0], bezier.best_handles(self.P0, self.P1, self.ED, grid, grid))
        rs = [r for _, _, r in ranked]
        self.assertEqual(rs, sorted(rs, reverse=True))

    def test_ranked_handles_keep_grid_order_on_ties(self):
        ranked = bezier.ranked_handles((0, 0, 0), (0, 0, 100), (0, 0, 1), [10, 20], [30, 40])
        self.assertEqual([(a, b) for a, b, _ in ranked], [(10, 30), (10, 40), (20, 30), (20, 40)])

    def test_empty_grids_refuse(self):
        with self.assertRaises(ValueError): bezier.best_handles(self.P0, self.P1, self.ED, [], [10])
        with self.assertRaises(ValueError): bezier.best_handles(self.P0, self.P1, self.ED, [10], [])


if __name__ == "__main__":
    unittest.main()
