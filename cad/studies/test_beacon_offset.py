#!/usr/bin/env python3
"""Tests for beacon_offset.py's plain-python parts (vt350#291). Run: python3 cad/studies/test_beacon_offset.py"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beacon_offset as bo  # noqa: E402


class Poses(unittest.TestCase):
    def test_head_at_minus_T_and_the_beacon_slid_forward(self):
        p = bo.poses((1.0, 2.0, 3.0), offsets=(27.4, 15.0))
        self.assertEqual(p["27.4"], {"head": (-1.0, -2.0, -3.0), "beacon": (0.0, -0.0, 0.0)})
        self.assertAlmostEqual(p["15.0"]["beacon"][1], -12.4)


class FirstClear(unittest.TestCase):
    def test_scans_down_and_stops_at_the_first_contact(self):
        offs = (27.4, 16.0, 15.0, 14.0, 10.0)
        self.assertEqual(bo.first_clear({"14.0": [1], "10.0": [1]}, offs), 15.0)

    def test_a_clear_offset_below_a_contact_does_not_count(self):
        self.assertEqual(bo.first_clear({"15.0": [1]}, (27.4, 16.0, 15.0, 14.0)), 16.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
