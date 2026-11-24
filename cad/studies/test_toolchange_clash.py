#!/usr/bin/env python3
"""Tests for toolchange_clash.py's timeline handling (vt350#116 AC5): plain python3, no FreeCAD, in CI."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import toolchange_clash as tc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))


class Params(unittest.TestCase):
    def test_reads_the_committed_config(self):
        attach, park = tc.read_params(open(os.path.join(ROOT, "cad/klipper/toolchanger.cfg")).read())
        self.assertEqual(attach, -85.96)                 # lite-78: the docks 17 forward (#291)
        self.assertEqual(park, {"extruder": 10.3, "extruder1": 339.7})


class States(unittest.TestCase):
    PARK = {"Left": 10.3, "Right": 339.7}

    def test_grab_detach_carry_and_let_go(self):
        m = [(10.3, -26.96, 10), (10.3, -68.96, 10), (15.3, -68.96, 10), (15.3, 48.04, 10),   # pick up Left
             (15.3, -68.96, 11), (10.3, -68.96, 11), (10.3, -26.96, 11)]                       # drop it off
        s = tc.carried_states(m, -68.96, self.PARK)
        self.assertEqual([(a[0], b[0]) for a, b in s],
                         [(None, "Left"),        # approach empty, grabbed on arrival at the dock
                          ("Left", "Left"),      # detach move: carried
                          ("Left", "Left"),      # out to safe_toolhead_y
                          ("Left", "Left"),      # back in at detach_x
                          ("Left", "Left"),      # sideways onto the screws
                          (None, None)])         # leave in Y: let go at (10.3, -68.96)
        self.assertEqual(s[-1][1][1]["Left"], (10.3, -68.96))
        self.assertIsNone(s[0][1][1]["Left"])

    def test_the_committed_timeline(self):
        tl = [json.loads(l) for l in open(os.path.join(ROOT, "cad/klipper/toolchange_timeline.jsonl"))]
        moves = [tuple(r["pos"][:3]) for r in tl if r["kind"] == "move"]
        ends = [b[0] for _, b in tc.carried_states(moves, -85.96, self.PARK)]
        self.assertIn("Left", ends)
        self.assertIn("Right", ends)
        self.assertIsNone(ends[-1])                      # it ends with both heads back in their docks


class Samples(unittest.TestCase):
    def test_step(self):
        p = tc.samples((0, 0, 0), (100, 0, 0), 25)
        self.assertEqual(len(p), 4)
        self.assertEqual(p[-1], (100, 0, 0))
        self.assertEqual(tc.samples((0, 0, 0), (0, 0, 1), 25), [(0, 0, 1)])


if __name__ == "__main__":
    unittest.main()
