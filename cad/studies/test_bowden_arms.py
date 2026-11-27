"""Tests for the bowden-arm geometry study (vt350#312). Plain python3 + numpy + scipy.

    python3 cad/studies/test_bowden_arms.py"""
import math, os, sys, unittest
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bowden_arms_reach as ba
import bowden_arms_dancer as bd
import lrod


def num_grad(f, v, h=1e-5):
    return np.array([(f(v + h * e) - f(v - h * e)) / (2 * h) for e in np.eye(v.size)])


class TestGeometry(unittest.TestCase):
    def test_dock_lock_is_lite80s_lock(self):
        # lite-79 probe: slot 1's lock box X -414.82..-404.02 (centre -409.42), Y -12.71..-0.68; the channel sits
        # +0.615 in Y from the box centre (lite-35: box centre 10.305, lrod/rod DOCK_Y 10.92). lite-80 moved the
        # docks 3 mm forward (#243).
        x, y = ba.dock_lock(1)
        self.assertAlmostEqual(x, -409.42, places=2)
        self.assertAlmostEqual(y, (-12.71 - 0.68) / 2 + 0.615 - 3.0, delta=0.02)
        self.assertAlmostEqual(ba.dock_lock(5)[0], (-85.42 - 74.62) / 2, places=2)

    def test_path_covers_the_printable_area(self):
        for slot in (1, 3, 5):
            P = np.array(ba.path(slot, 34.0))
            lx0, ly0 = ba.lock_xy((ba.REACH_X[0], ba.REACH_Y[0]))
            lx1, ly1 = ba.lock_xy((ba.REACH_X[1], ba.REACH_Y[1]))
            for cx, cy in ((lx0, ly0), (lx0, ly1), (lx1, ly0), (lx1, ly1)):
                self.assertLess(np.min(np.hypot(P[:, 0] - cx, P[:, 1] - cy)), 1e-6)
            self.assertTrue(np.all(P[:, 2] == ba.HEAD_Z))
            np.testing.assert_allclose(P[0, :2], ba.dock_lock(slot))
            steps = np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1)
            self.assertLessEqual(steps.max(), 34.0 + 1e-6)        # a walk: no jumps for the continuation
            self.assertGreater(steps.min(), 1e-6)

    def test_loop_on_the_arm_circle(self):
        h = (490.0, 643.0)
        y, z = ba.loop_at(h, 200.0, 600.0)
        self.assertAlmostEqual(math.hypot(y - h[0], z - h[1]), 200.0)
        self.assertLess(y, h[0])
        self.assertIsNone(ba.loop_at(h, 20.0, 600.0))

    def test_arm_clear_of_moving(self):
        h = (490.0, 640.0)
        lo = ba.loop_at(h, 200.0, 640.0)                         # flat: the ring's underside is the lowest point
        self.assertAlmostEqual(ba.arm_clear_of_moving(h, lo), 640.0 - ba.LOOP_R - 550.37, places=6)
        self.assertAlmostEqual(ba.arm_clear_of_moving(h, lo, 10.3), 640.0 - ba.LOOP_R - 560.67, places=6)
        self.assertEqual(ba.arm_clear_of_moving((495.0, 640.0), (470.0, 600.0)), math.inf)   # behind all travel


class TestSpan(unittest.TestCase):
    a = lrod.exit_point(3)
    b = np.array([-245.0, 200.0, lrod.HEAD_Z])
    P = np.array([lrod.EXIT_X[3], 330.0, 620.0])

    def test_both_clamped_is_lrods_rod(self):
        R0 = lrod.Rod(2000.0, n=12)
        R1 = ba.Span(2000.0, 12, g0=-lrod.EXIT_DIR, g1=ba.DOWN)
        for L, T in ((700.0, 0.0), (None, 0.3)):
            v = R0.initial(self.a, self.b, L) + np.random.default_rng(3).normal(0, 0.5, 33 + (L is None))
            E0, g0 = R0.energy(v, self.a, self.b, L, T)
            E1, g1 = R1.energy(v, self.a, self.b, L, T)
            self.assertAlmostEqual(E0, E1, places=8)
            np.testing.assert_allclose(g0, g1, atol=1e-9)

    def test_gradients_every_end_type(self):
        rng = np.random.default_rng(4)
        for g0, g1 in ((None, ba.DOWN), (-lrod.EXIT_DIR, None), (None, None)):
            R = ba.Span(2000.0, 10, g0=g0, g1=g1)
            for L, T in ((420.0, 0.0), (None, 0.2)):
                v = R.initial(self.P, self.b, L) + rng.normal(0, 0.5, 27 + (L is None))
                g = R.energy(v, self.P, self.b, L, T)[1]
                gn = num_grad(lambda u: R.energy(u, self.P, self.b, L, T)[0], v)
                self.assertLess(np.abs(g - gn).max() / np.abs(gn).max(), 1e-6, (g0, g1, L))
                ceq, jeq, cin, Jin = R.cons(self.P, self.b, L)
                np.testing.assert_allclose(jeq(v), num_grad(ceq, v).T, atol=1e-5)
                np.testing.assert_allclose(Jin, num_grad(cin, v).T, atol=1e-6)

    def test_head_span_solves_feasibly(self):
        R = ba.Span(2000.0, 12, g1=ba.DOWN)
        x, ok, r = R.solve(self.P, self.b, R.initial(self.P, self.b, 420.0), 420.0, 0.0)
        self.assertTrue(ok)
        X, _ = R.unpack(x, self.P, self.b, 420.0)
        np.testing.assert_allclose(np.linalg.norm(np.diff(X, axis=0), axis=1), 35.0, rtol=1e-3)
        self.assertLessEqual(X[:, 2].max(), lrod.Z_CEIL + 1e-3)
        m = ba.shape(R, X)
        self.assertLess(m["t1"][2], -0.7)    # arrives going down (the clamp is a ghost joint; its angle counts in minR)

    def test_initial_refuses_a_short_span(self):
        R = ba.Span(2000.0, 12, g1=ba.DOWN)
        self.assertIsNone(R.initial(self.P, self.b, 0.9 * np.linalg.norm(self.b - self.P)))

    def test_free_length_grows_as_take_up_drops(self):
        R = ba.Span(2000.0, 12, g1=ba.DOWN)
        Ls = []
        for T in (2.0, 0.2):
            x, ok, r = R.solve(self.P, self.b, R.initial(self.P, self.b, None), None, T)
            self.assertTrue(ok); Ls.append(x[-1])
        self.assertLess(Ls[0], Ls[1])
        self.assertGreater(Ls[0], np.linalg.norm(self.b - self.P))

    def test_roof_span_suits_both_loop_positions(self):
        d = dict(loop_up=[300.0, 662.0], loop_down=[310.0, 610.0])
        for mode in ("slide", "tied"):
            r = ba.roof_span(3, d, 2000.0, mode)
            self.assertIsNotNone(r, mode)
            for which, (y, z) in (("up", d["loop_up"]), ("down", d["loop_down"])):
                np.testing.assert_allclose(r[which]["X"][-1], [lrod.EXIT_X[3], y, z], atol=1e-6)
                np.testing.assert_allclose(r[which]["X"][0], self.a, atol=1e-6)
                self.assertGreater(r["L_" + which], np.linalg.norm(np.array([lrod.EXIT_X[3], y, z]) - self.a))
            if mode == "tied": self.assertAlmostEqual(r["L_up"], r["L_down"])

    def test_lock_zone_split(self):
        # a quarter circle of R 100, starting down and ending along +Y, into a lock clamped -Z: the clamp's ghost
        # joint (a 90 deg turn) is in the zone, the body has only the arc's joints
        R = ba.Span(2000.0, 20, g1=ba.DOWN)
        th = np.linspace(0, np.pi / 2, 21)
        X = np.c_[np.zeros(21), 100 * (1 - np.cos(th)), -100 * np.sin(th)] + np.array([0, 0, 600.0])
        m = ba.shape(R, X, zone=60.0)
        self.assertAlmostEqual(m["minR_body"], 100.0, delta=1.0)              # the arc: R 100
        self.assertLess(m["minR_zone"], m["minR_body"])                      # the ghost joint into -Z
        self.assertEqual(min(m["minR_body"], m["minR_zone"]), m["minR"])
        self.assertTrue(math.isinf(ba.shape(R, X)["minR_zone"]))               # no zone asked: none reported


class TestDancer(unittest.TestCase):
    def test_legs_two_radii_apart(self):
        for s in range(1, 6):
            le, lr = bd.legs(s)
            self.assertAlmostEqual(abs(le - lr), 2 * bd.RP)
            self.assertAlmostEqual((le + lr) / 2, bd.PULLEY[s][0])
            self.assertAlmostEqual(lr, bd.PULLEY[s][0] + bd.RETURN_SIDE[s] * bd.RP)
        self.assertGreaterEqual(bd.RP - 2.55, ba.MIN_R)            # the inner tube in the groove

    def test_stacks_fit_their_gaps(self):
        # left gap: the rear-left corner idler plate (X <= -385.5) | the Z axis's bed carriage (X >= -262.9);
        # right gap: the Z axis (X <= -229.8) | the rear-right plate (X >= -104.5). Legs +-4.6, sheaves RP + 4.6 + 2.
        for s, (cx, y) in bd.PULLEY.items():
            half = bd.RP + ba.BUNDLE_W / 2 + 2.0
            lo, hi = (-385.5, -262.9) if cx < -246 else (-229.8, -104.5)
            self.assertGreater(cx - half, lo + 1.0, s)
            self.assertLess(cx + half, hi - 1.0, s)

    def test_pulleys_clear_the_z_axis_and_each_other(self):
        # the rear-centre Z axis (carriage, leadscrew, 2020 (3)) at X -263..-230: no pulley spans it; pulleys that
        # overlap in X sit in different planes, 14 mm apart or more (bundle 9.2)
        half = bd.RP + ba.BUNDLE_W / 2 + 2.0
        for s, (cx, y) in bd.PULLEY.items():
            self.assertTrue(cx + half < -263.0 or cx - half > -230.0, s)
            for o, (cx2, y2) in bd.PULLEY.items():
                if o != s and abs(cx - cx2) < 2 * half: self.assertGreaterEqual(abs(y - y2), 12.0, (s, o))

    def test_q_on_the_arm(self):
        for loop in (bd.DESIGN["loop_down"], bd.DESIGN["loop_up"]):
            Q = bd.q_point(3, loop)
            hy, hz = bd.DESIGN["hinge"]
            # on the line hinge -> loop
            cross = (Q[1] - hy) * (loop[1] - hz) - (Q[2] - hz) * (loop[0] - hy)
            self.assertAlmostEqual(cross, 0.0, places=6)
            self.assertAlmostEqual(Q[1], bd.Y_Q)
            self.assertAlmostEqual(Q[0], lrod.EXIT_X[3])

    def test_pulley_height_inverts_rear_length(self):
        # a synthetic rear table: each span grows 1 mm per mm the pulley drops -> 2 per mm in all
        rear = {z: (1000.0 - z, 900.0 - z, 60.0, 60.0, None, None, 10.0) for z in (500.0, 400.0, 300.0)}
        for z in (480.0, 420.0, 300.0):
            need = bd.rear_length(rear, z)
            self.assertAlmostEqual(bd.pulley_at(rear, need), z, places=6)
        top = bd.rear_length(rear, 500.0)
        self.assertAlmostEqual(bd.pulley_at(rear, top - 20.0), 510.0)      # above the grid: 10 higher (2 per mm)
        self.assertIsNone(bd.rear_length(rear, 520.0))

    def test_clear_of_moving(self):
        X = [(-245.0, 300.0, 600.0), (-245.0, 450.0, 420.0)]          # over a head; behind all travel
        self.assertAlmostEqual(bd.clear_of_moving(X, 0.0), 600.0 - ba.BUNDLE_W / 2 - 550.37)
        self.assertEqual(bd.clear_of_moving([(-245.0, 450.0, 420.0)], 0.0), math.inf)

if __name__ == "__main__":
    unittest.main()
