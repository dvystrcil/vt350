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


class Classify(unittest.TestCase):
    def res(self, results=(), errors=()):
        return dict(results=[dict(pose=p, a=a, b=b, la=a, lb=b, volume=v) for p, a, b, v in results],
                    errors=[dict(pose=p, a=a, b=b, la=a, lb=b, error="Null shape") for p, a, b in errors])

    def test_baseline_pairs_are_ignored(self):
        got = fr.classify(self.res([("-400.00 3.10", "n", "o", 5.0), ("-400.00 3.10", "p", "q", 1.0)]),
                          {-400.0: 3.1}, base={("p", "q")})
        self.assertEqual(got, {-400.0: [(5.0, "n", "o")]})

    def test_a_common_error_blocks_the_pose(self):
        """A failed common() can't prove a pose clear, so it counts as a contact (vt350#291: 3 Null-shape errors)."""
        got = fr.classify(self.res(errors=[("-134.35 3.10", "smart sensor", "o2s")]), {-134.35: 3.1, -100.0: 3.1}, set())
        self.assertTrue(got[-134.35]); self.assertEqual(got[-134.35][0][0], -1.0)
        self.assertEqual(got[-100.0], [])


class FrontSet(unittest.TestCase):
    """The what-if's front set (vt350#291): boxes in front of FRONT_Y, plus whole head and dock groups."""
    def test_group_members_move_even_when_they_end_behind_the_cut(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            model = os.path.join(d, "m.FCStd")
            parts = [dict(name="tb", path=["root", "Toolhead slot 2 (L)"]), dict(name="dock", path=["root", "Left Dock"]),
                     dict(name="rail", path=["root", "Frame"]), dict(name="bar", path=["root", "Frame"])]
            json.dump(dict(parts=parts), open(os.path.join(d, "m.parts.json"), "w"))
            boxes = {"tb": [0, -40, 0, 1, -3, 1], "dock": [0, -60, 0, 1, 20, 1], "rail": [0, -30, 0, 1, 400, 1],
                     "bar": [0, -75, 0, 1, -55, 1]}
            self.assertEqual(fr.front_names(model, boxes), {"tb", "dock", "bar"})

    def test_no_listing_is_an_error_not_an_empty_set(self):
        with self.assertRaises(SystemExit):
            fr.front_names("/nonexistent/m.FCStd", {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
