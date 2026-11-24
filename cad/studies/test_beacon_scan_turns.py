#!/usr/bin/env python3
"""Tests for cad/studies/beacon_scan_turns.py (vt350#291, #309).

Run: python3 cad/studies/test_beacon_scan_turns.py
"""
import importlib.util, json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("turns", os.path.join(HERE, "beacon_scan_turns.py"))
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)


class Turns(unittest.TestCase):
    def test_limit_between_samples_is_the_worse(self):
        lim = [(0.0, -20.0), (10.0, -12.0), (20.0, -18.0)]
        self.assertEqual(t.limit_at(lim, 5.0), -12.0)
        self.assertEqual(t.limit_at(lim, 10.0), -12.0)
        self.assertEqual(t.worst_past([(5.0, -15.0)], lim), 3.0)
        self.assertEqual(t.worst_past([(5.0, -10.0)], lim), 0.0)

    def test_repo_cases(self):
        with open(t.fpm.FRONT_REACH) as f, open(t.fpm.MAPPING) as g:
            front, mapping = json.load(f), json.load(g)
        safe = t.fpm.safe_nozzle_y(front, mapping)
        lim = t.limits(front, mapping)
        cs = t.cases(safe, 5.0)
        past = [t.worst_past(c["path"], lim) for c in cs]
        self.assertGreater(past[0], 20.0)          # along Y, auto overscan: the front turns run into the dock side
        self.assertEqual(past[1], 0.0)             # along X: clear
        self.assertEqual(past[2], 0.0)             # along Y, capped and moved back: clear
        self.assertIn("<svg", t.svg(cs, lim, safe))


if __name__ == "__main__":
    unittest.main()
