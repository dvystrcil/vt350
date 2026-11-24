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
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):     # its "front_reach_map: OK" would land after unittest's "OK"
            rc = frm.main(["--check"])                     # (stdout is buffered), and CI reads the log's last line
        self.assertEqual(rc, 0, "run python3 cad/studies/front_reach_map.py")

    def test_both_heads_are_drawn(self):
        text = frm.build()
        self.assertIn("Left head carried", text); self.assertIn("Right head carried", text)


class TiltReach(unittest.TestCase):
    def test_limit_is_the_worst_neighbour(self):
        lim = [(0.0, 30.0), (10.0, 40.0), (20.0, 20.0)]
        self.assertEqual(frm.nozzle_limit(lim, 15.0, 10.0), 25.0)
        self.assertEqual(frm.nozzle_limit(lim, 15.0, 99.0), float("inf"))

    def test_every_z_tilt_point_is_reachable_by_both_heads(self):
        """cad/klipper/beacon.cfg [z_tilt] points vs the committed front reach (vt350#291): 1 mm of margin."""
        import json
        data = json.load(open(frm.DATA))
        lim = frm.limits(data)
        bad = [r for r in frm.tilt_reach(frm.beacon_scan.TILT_POINTS, lim, data["beacon_dy"]) if not r[3]]
        self.assertEqual(bad, [], f"z_tilt points too close to a head's front limit: {bad}")


class WhatIfMap(unittest.TestCase):
    def test_committed_front17_map_is_what_its_data_gives(self):
        """cad/data/beacon-coverage-front17.svg from front_reach_front17.json (vt350#291: front +17, Beacon at 15)."""
        d = os.path.join(frm.ROOT, "cad", "data")
        self.assertEqual(open(os.path.join(d, "beacon-coverage-front17.svg")).read(),
                         frm.build(os.path.join(d, "front_reach_front17.json")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
