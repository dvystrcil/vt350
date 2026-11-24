#!/usr/bin/env python3
"""Tests for cad/studies/beacon_scan_footprint.py (vt350#291, #309).

Run: python3 cad/studies/test_beacon_scan_footprint.py
"""
import importlib.util, json, os, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fp", os.path.join(HERE, "beacon_scan_footprint.py"))
fp = importlib.util.module_from_spec(spec); spec.loader.exec_module(fp)
MAPPING = {"origin_model_xy": [0.0, 0.0], "sign_xy": [1, 1]}


class Footprint(unittest.TestCase):
    def test_worse_head_and_numbers(self):
        front = {"heads": {"Left": [{"x": 175.0, "clear": -20.0}, {"x": 50.0, "clear": -16.2}, {"x": 205.0, "clear": -18.0}],
                           "Right": [{"x": 175.0, "clear": -11.67}, {"x": 50.0, "clear": -17.0}, {"x": 205.0, "clear": -18.47}]}}
        rows, half = fp.footprints(front, MAPPING, 27.4)
        self.assertAlmostEqual(half, 8.7, places=2)                     # 8.5 + 0.04375 * 4.6
        r = {x["x"]: x for x in rows}
        self.assertEqual(r[175.0]["nozzle"], -11.67)                    # the worse (more rearward) head
        self.assertAlmostEqual(r[175.0]["coil"], 15.73, places=2)
        self.assertAlmostEqual(r[175.0]["plate_coil"], 18.23, places=2)
        self.assertAlmostEqual(r[175.0]["plate_front"], 9.53, places=2)
        self.assertEqual(r[205.0]["nozzle"], -18.0)

    def test_repo_data_draws(self):
        with open(fp.FRONT_REACH) as f, open(fp.MAPPING) as g:
            rows, half = fp.footprints(json.load(f), json.load(g), 27.4)
        self.assertEqual(len(rows), 3)
        self.assertIn("<svg", fp.svg(rows, half, 27.4))


if __name__ == "__main__":
    unittest.main()
