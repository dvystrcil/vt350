"""Tests for the flap + guide rod model (vt350#3). Needs numpy + scipy.  python3 cad/studies/flap_guide/test_rod.py"""
import os, sys, unittest
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rod, study
from scipy.optimize import brentq


def num_grad(R, v, a, b, L, T, h=1e-5):
    return np.array([(R.energy(v + h * e, a, b, L, T)[0] - R.energy(v - h * e, a, b, L, T)[0]) / (2 * h)
                     for e in np.eye(v.size)])


class TestRod(unittest.TestCase):
    a = np.array([-380.0, 200.0, 685.0])
    b = np.array([-245.0, 150.0, rod.HEAD_Z])

    def test_gradient_free_length(self):
        R = rod.Rod(7000.0, n=12)
        v = R.initial(self.a, self.b, None) + np.random.default_rng(0).normal(0, 1, 3 * 11 + 1)
        g = R.energy(v, self.a, self.b, None, 0.3)[1]
        gn = num_grad(R, v, self.a, self.b, None, 0.3)
        self.assertLess(np.abs(g - gn).max() / np.abs(gn).max(), 1e-6)

    def test_gradient_fixed_length(self):
        R = rod.Rod(700.0, n=12)
        v = R.initial(self.a, self.b, 400.0) + np.random.default_rng(1).normal(0, 1, 3 * 11)
        g = R.energy(v, self.a, self.b, 400.0, 0.0)[1]
        gn = num_grad(R, v, self.a, self.b, 400.0, 0.0)
        self.assertLess(np.abs(g - gn).max() / np.abs(gn).max(), 1e-6)

    def test_limp_rod_is_a_catenary(self):
        # EI -> 0, both ends at one height, 300 apart, 400 long: sag must match c (cosh(150/c) - 1)
        R = rod.Rod(0.01, n=40)
        a, b = np.array([-400.0, 200, 300]), np.array([-100.0, 200, 300])
        x, ok, _ = R.solve(a, b, R.initial(a, b, 400.0), 400.0, 0.0, iters=1000)
        self.assertTrue(ok)
        X, _ = R.unpack(x, a, b, 400.0)
        c = brentq(lambda c: 2 * c * np.sinh(150 / c) - 400, 10, 1e4)
        self.assertAlmostEqual(300 - X[:, 2].min(), c * (np.cosh(150 / c) - 1), delta=0.5)

    def test_solution_is_feasible(self):
        R = rod.Rod(2000.0)
        x, ok, _ = R.solve(self.a, self.b, R.initial(self.a, self.b, None), None, 0.2)
        self.assertTrue(ok)
        X, L = R.unpack(x, self.a, self.b, None)
        seg = np.linalg.norm(np.diff(X, axis=0), axis=1)
        self.assertLess(np.abs(seg - L / R.n).max(), 0.01)            # inextensible
        self.assertLessEqual(X[:, 2].max(), rod.Z_CEIL + 1e-3)        # under the ceiling
        self.assertGreater(L, np.linalg.norm(self.b - self.a))        # longer than the chord

    def test_seg_dist(self):
        P = np.array([[0.0, 0, 0], [10, 0, 0]]); Q = np.array([[5.0, -5, 3], [5, 5, 3]])
        self.assertAlmostEqual(rod.seg_dist(P, Q), 3.0)            # an X crossing: no vertex is near the other line
        self.assertAlmostEqual(rod.seg_dist(P, P + [0, 4, 0]), 4.0)  # parallel
        self.assertAlmostEqual(rod.seg_dist(P, np.array([[13.0, 4, 0], [20, 4, 0]])), 5.0)  # end to end
        rng = np.random.default_rng(2)                                # vs brute force on dense samples
        for _ in range(20):
            P, Q = rng.normal(0, 10, (4, 3)), rng.normal(0, 10, (4, 3))
            dense = lambda X: np.vstack([np.linspace(X[i], X[i + 1], 400) for i in range(len(X) - 1)])
            brute = np.linalg.norm(dense(P)[:, None] - dense(Q)[None], axis=2).min()
            self.assertLessEqual(rod.seg_dist(P, Q), brute + 1e-9)
            self.assertAlmostEqual(rod.seg_dist(P, Q), brute, delta=0.1)

    def test_path_starts_at_the_dock_and_covers_the_reach(self):
        for s in range(1, 6):
            P = np.array(study.path(s))
            self.assertAlmostEqual(P[0, 0], rod.DOCK_X[s]); self.assertAlmostEqual(P[0, 1], rod.DOCK_Y)
            self.assertLessEqual(P[1:, 0].min(), rod.REACH_X[0] + 1e-6)
            self.assertGreaterEqual(P[1:, 1].max(), rod.REACH_Y[1] - study.STEP)


if __name__ == "__main__":
    unittest.main()
