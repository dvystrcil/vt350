#!/usr/bin/env python3
"""Tests for mellow_edge_reach.py (vt350#291). Run: python3 cad/studies/test_mellow_edge_reach.py"""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mellow_edge_reach as mer  # noqa: E402


class Geometry(unittest.TestCase):
    def test_four_sides(self):
        self.assertEqual(mer.approach_points(100, -10, 5), [(100, -15), (95, -10), (105, -10), (100, -5)])

    def test_windows_join_neighbours(self):
        limit = lambda x: -20.0 if 10 <= x <= 30 else -5.0      # deep reach only between X 10 and 30
        # the side points (bx +- 5) must land in 10..30 too; the front point (Y -15) is 5 behind the -20 limit
        self.assertEqual(mer.windows(limit, -10.0, 5.0, range(0, 40)), [(15, 25, 5.0)])
        self.assertEqual(mer.windows(limit, -16.0, 5.0, range(0, 40)), [])         # the front point is past -20


class Committed(unittest.TestCase):
    def test_lite61_spot_unreachable_and_two_windows(self):
        limit = mer.both_heads(json.load(open(mer.DATA)))
        self.assertLess(mer.margin(limit, 175, -12.5, 5.0), 0)
        w = mer.windows(limit, -9.5, 5.0)
        self.assertTrue(any(a <= 50 <= b for a, b, _ in w) and any(a <= 215 <= b for a, b, _ in w), w)


if __name__ == "__main__":
    unittest.main()
