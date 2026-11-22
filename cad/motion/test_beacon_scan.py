#!/usr/bin/env python3
"""Tests for beacon_scan.py (vt350#291). Run: python3 cad/motion/test_beacon_scan.py"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beacon_scan as bs  # noqa: E402


class Overscan(unittest.TestCase):
    def test_vt350_rear_room_limits_it(self):
        # nozzle Y range 5.48-27.4 .. 344.52-27.4 = -21.92 .. 317.12; rooms 60.49 front, 23.07 rear; spacing+2 = 26.22
        self.assertAlmostEqual(bs.overscan(), 340.19 - (344.52 - 27.4), places=6)

    def test_spacing_limits_it_with_room(self):
        self.assertAlmostEqual(bs.overscan((50, 50), (150, 150), (11, 11), (0, 0), (0, 0), (300, 300)), 12.0)


class Path(unittest.TestCase):
    def test_extent_is_the_mesh_less_the_offset_plus_the_overscan(self):
        p = bs.scan_path()
        o = bs.overscan()
        xs, ys = [q[0] for q in p], [q[1] for q in p]
        self.assertAlmostEqual(min(xs), 5.48); self.assertAlmostEqual(max(xs), 344.52)
        self.assertAlmostEqual(min(ys), 5.48 - 27.4 - o, places=3)
        self.assertAlmostEqual(max(ys), 344.52 - 27.4 + o, places=3)

    def test_lines_run_along_y_serpentine(self):
        p = bs.scan_path()
        self.assertEqual(p[0], (5.48, 5.48 - 27.4)); self.assertEqual(p[1], (5.48, 344.52 - 27.4))
        self.assertAlmostEqual(p[-1][0], 344.52); self.assertAlmostEqual(p[-1][1], 344.52 - 27.4)   # 15 lines: ends at the back

    def test_steps_stay_inside_the_axis_limits(self):
        for x, y in bs.scan_path():
            self.assertTrue(bs.AXIS_MIN[0] <= x <= bs.AXIS_MAX[0] and bs.AXIS_MIN[1] - 1e-9 <= y <= bs.AXIS_MAX[1] + 1e-9)

    def test_order_is_coarse_home_pickup_tilt_tap_scan(self):
        """Owner 2026-11-22: coarse Z by proximity with no head, then T0, the tilt taps, the Z0 tap, the scan."""
        g = bs.gcode().splitlines()
        dive, t0 = g.index("G1 Z2 F300"), g.index("T0")
        taps = [i for i, l in enumerate(g) if l == "G1 Z0 F180"]
        scan = g.index("G1 Z2 F600")
        self.assertLess(dive, t0)
        self.assertEqual(len(taps), len(bs.TILT_POINTS) + 1)
        self.assertLess(t0, taps[0]); self.assertLess(taps[-1], scan)
        self.assertIn(f"G1 X175 Y175 Z5 F18000", g[taps[-1] - 1])     # the last tap is the Z0 one, at home


if __name__ == "__main__":
    unittest.main(verbosity=2)
