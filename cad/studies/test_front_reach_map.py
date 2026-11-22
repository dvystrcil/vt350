#!/usr/bin/env python3
"""Tests for front_reach_map.py (vt350#291). Run: python3 cad/studies/test_front_reach_map.py"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import front_reach_map as frm  # noqa: E402

MAP = {"origin_model_xy": [-420.0, 30.5], "sign_xy": [1, 1]}


class Limits(unittest.TestCase):
    def test_model_to_printer_plus_the_offset(self):
        d = {"beacon_dy": 27.4, "heads": {"Left": [{"x": -416.0, "blocked": None, "clear": 3.1},
                                                     {"x": -74.0, "blocked": 34.34, "clear": 35.54}]}}
        self.assertEqual(frm.limits(d, MAP), {"Left": [(4.0, 0.0), (346.0, 32.44)]})


class Committed(unittest.TestCase):
    def test_svg_is_current(self):
        self.assertEqual(frm.main(["--check"]), 0, "run python3 cad/studies/front_reach_map.py")

    def test_both_heads_are_drawn(self):
        text = frm.build()
        self.assertIn("Left head carried", text); self.assertIn("Right head carried", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
