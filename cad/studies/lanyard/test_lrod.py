"""Tests for the lanyard rod model (vt350#218). Needs numpy + scipy.  python3 cad/studies/lanyard/test_lrod.py"""
import os, sys, unittest
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lrod


def num_grad(R, v, a, b, L, T, h=1e-5):
    return np.array([(R.energy(v + h * e, a, b, L, T)[0] - R.energy(v - h * e, a, b, L, T)[0]) / (2 * h)
                     for e in np.eye(v.size)])


class TestLRod(unittest.TestCase):
    a = lrod.exit_point(3)
    b = np.array([-245.0, 150.0, lrod.HEAD_Z])
    reel = np.array([-248.0, -62.0, 640.0])

    def rod(self, EI=2000.0, n=12, F=1.0):
        return lrod.Rod(EI, n=n, reel=self.reel, k=n - n // 3, F=F)

    def test_exit_point_on_the_bore(self):
        a = lrod.exit_point(1)
        self.assertAlmostEqual(a[2], lrod.Z_CEIL)
        on_roof = a + lrod.EXIT_DIR * (lrod.EXIT_ON_ROOF[1] - lrod.Z_CEIL) * np.sqrt(2)
        self.assertAlmostEqual(on_roof[1], lrod.EXIT_ON_ROOF[0]); self.assertAlmostEqual(on_roof[2], lrod.EXIT_ON_ROOF[1])

    def test_gradient_fixed_length_with_lanyard(self):
        R = self.rod()
        v = R.initial(self.a, self.b, 600.0) + np.random.default_rng(1).normal(0, 1, 3 * 11)
        g = R.energy(v, self.a, self.b, 600.0, 0.0)[1]
        gn = num_grad(R, v, self.a, self.b, 600.0, 0.0)
        self.assertLess(np.abs(g - gn).max() / np.abs(gn).max(), 1e-6)

    def test_gradient_free_length_with_lanyard(self):
        R = self.rod(EI=7000.0)
        v = R.initial(self.a, self.b, None) + np.random.default_rng(0).normal(0, 1, 3 * 11 + 1)
        g = R.energy(v, self.a, self.b, None, 0.3)[1]
        gn = num_grad(R, v, self.a, self.b, None, 0.3)
        self.assertLess(np.abs(g - gn).max() / np.abs(gn).max(), 1e-6)

    def test_head_force_matches_resolving(self):
        # the multiplier force must equal -dE*/db, measured by re-solving with the head moved +-h on each axis
        for F in (0.0, 1.0):
            R = self.rod(EI=2000.0, n=16, F=F)
            L = 620.0
            x, ok, r = R.solve(self.a, self.b, R.initial(self.a, self.b, L), L, 0.0, iters=1000)
            self.assertTrue(ok)
            f = R.head_force(x, self.a, self.b, L, 0.0)
            h = 0.05
            for ax in range(3):
                e = np.zeros(3); e[ax] = h
                Es = []
                for sgn in (1, -1):
                    xs, oks, rs = R.solve(self.a, self.b + sgn * e, x, L, 0.0, iters=1000)
                    self.assertTrue(oks); Es.append(rs.fun)
                self.assertAlmostEqual(f[ax], -(Es[0] - Es[1]) / (2 * h), delta=0.01 + 0.02 * abs(f[ax]))

    def test_solution_is_feasible(self):
        R = self.rod(EI=700.0, n=30, F=2.0)
        x, ok, _ = R.solve(self.a, self.b, R.initial(self.a, self.b, 700.0), 700.0, 0.0)
        self.assertTrue(ok)
        X, L = R.unpack(x, self.a, self.b, 700.0)
        seg = np.linalg.norm(np.diff(X, axis=0), axis=1)
        self.assertLess(np.abs(seg - L / R.n).max(), 0.01)
        self.assertLessEqual(X[:, 2].max(), lrod.Z_CEIL + 1e-3)
        self.assertGreaterEqual(X[:, 1].min(), lrod.Y_WALL[0] - 1e-3)
        m = lrod.metrics(R, X)
        self.assertIn("cord", m); self.assertGreater(m["minR"], 0)

    def test_lanyard_lifts_the_rod(self):
        # a pull up and forward must raise the attached node versus no lanyard
        R0, R1 = self.rod(EI=700.0, n=30, F=0.0), self.rod(EI=700.0, n=30, F=2.0)
        L = 750.0
        x0, ok0, _ = R0.solve(self.a, self.b, R0.initial(self.a, self.b, L), L, 0.0)
        x1, ok1, _ = R1.solve(self.a, self.b, x0, L, 0.0)
        self.assertTrue(ok0 and ok1)
        k = R1.k
        self.assertGreater(R1.unpack(x1, self.a, self.b, L)[0][k, 2], R0.unpack(x0, self.a, self.b, L)[0][k, 2])


if __name__ == "__main__":
    unittest.main()
