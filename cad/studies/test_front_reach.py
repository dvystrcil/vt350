#!/usr/bin/env python3
"""Tests for front_reach.py's plain-python parts (vt350#291): the swept box, the box filter and the bisection.

Run: python3 cad/studies/test_front_reach.py
"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import front_reach as fr


class SweptBox(unittest.TestCase):
    def test_box_grows_by_the_translation_ranges(self):
        boxes = {"a": [0, 0, 0, 10, 10, 10], "b": [5, -5, 2, 20, 5, 4]}
        self.assertEqual(fr.swept_box(boxes, ["a", "b"], (-100, 50), 3, 30, dz=-1), (-100, -2, -1, 70, 40, 9))

    def test_names_without_a_box_are_ignored(self):
        self.assertEqual(fr.swept_box({"a": [0, 0, 0, 1, 1, 1]}, ["a", "gone"], (0, 0), 0, 0), (0, 0, 0, 1, 1, 1))


class Hits(unittest.TestCase):
    def test_overlap_and_margin(self):
        s = (0, 0, 0, 10, 10, 10)
        self.assertTrue(fr.hits([5, 5, 5, 6, 6, 6], s))
        self.assertTrue(fr.hits([10.4, 0, 0, 12, 1, 1], s))         # within the 0.5 margin
        self.assertFalse(fr.hits([11, 0, 0, 12, 1, 1], s))
        self.assertFalse(fr.hits([0, 0, 20, 1, 1, 21], s))           # clear in Z alone is clear


class Bisection(unittest.TestCase):
    def test_converges_on_the_boundary(self):
        wall = {-400.0: 17.3, -200.0: 41.0}                          # blocked below these Y, clear from them on
        state = {x: [3.1, 80.0] for x in wall}
        while True:
            t = fr.next_round(state, res=2.0)
            if not t: break
            fr.update(state, t, {x: y < wall[x] for x, y in t.items()})
        for x, (b, c) in state.items():
            self.assertLess(b, wall[x]); self.assertGreaterEqual(c, wall[x]); self.assertLessEqual(c - b, 2.0)

    def test_settled_rows_get_no_more_poses(self):
        state = {1.0: [None, 3.1], 2.0: [3.1, None], 3.0: [10.0, 11.0]}   # clear at the front; never clear; done
        self.assertEqual(fr.next_round(state, res=2.0), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
