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
    def test_safe_y_is_the_worst_x_and_head(self):
        front = {"heads": {"Left": [{"x": 0.0, "clear": -20.0}, {"x": 175.0, "clear": -14.0}, {"x": 350.0, "clear": -11.67}],
                           "Right": [{"x": 0.0, "clear": -12.5}, {"x": 175.0, "clear": -18.0}, {"x": 350.0, "clear": -23.0}],
                           }}
        self.assertEqual(fp.safe_nozzle_y(front, MAPPING), -11.67)
        # a sample far outside the mesh's X range doesn't count
        front["heads"]["Left"].append({"x": 900.0, "clear": 5.0})
        self.assertEqual(fp.safe_nozzle_y(front, MAPPING, xr=(5.48, 344.52)), -11.67)

    def test_footprint_numbers(self):
        f = fp.footprint(-11.67, 27.4)
        self.assertAlmostEqual(f["half"], 8.7, places=2)               # 8.5 + 0.04375 * 4.6
        self.assertAlmostEqual(f["plate_nozzle"], -9.17, places=2)
        self.assertAlmostEqual(f["plate_coil"], 18.23, places=2)
        self.assertAlmostEqual(f["plate_front"], 9.53, places=2)
        self.assertAlmostEqual(f["plate_rear"], 26.93, places=2)

    def test_repo_data_draws(self):
        with open(fp.FRONT_REACH) as f, open(fp.MAPPING) as g:
            ny = fp.safe_nozzle_y(json.load(f), json.load(g))
        self.assertAlmostEqual(ny, -11.67, places=2)
        self.assertIn("<svg", fp.svg(ny, [fp.footprint(ny, dy) for _, dy, _ in fp.OFFSETS]))


if __name__ == "__main__":
    unittest.main()
