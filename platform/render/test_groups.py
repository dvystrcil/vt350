#!/usr/bin/env python3
"""Tests for groups.py (vt350#135 AC4, vt350#144): which bucket each exported part goes in. Stdlib only, in CI:
python3 platform/render/test_groups.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import groups  # noqa: E402
import motion  # noqa: E402

GROUPS = {"groups": {"bed": ["Bed1", "Bed2"], "carriage": ["Car"], "Left": ["HeadL"]},
          "clip": {"Car": [0, 0, 0, 1, 1, 1]}, "hide": ["Ghost"]}


class Assign(unittest.TestCase):
    """Which bucket an exported part goes in: a moving group's parts get their own buckets, so Blender can move them."""
    def setUp(self):
        self.a = groups.Assign(GROUPS)

    def test_a_static_part_keeps_its_bucket(self):
        self.assertEqual(self.a.bucket("Frame1", "role_frame_t0"), ("role_frame_t0", None))

    def test_a_moving_part_gets_its_groups_bucket(self):
        self.assertEqual(self.a.bucket("Bed2", "role_frame_t0"), ("bed__role_frame_t0", "bed"))

    def test_the_same_colour_in_two_groups_is_two_buckets(self):
        self.assertNotEqual(self.a.bucket("Bed1", "k")[0], self.a.bucket("HeadL", "k")[0])

    def test_hidden_parts_are_left_out(self):
        self.assertTrue(self.a.hidden("Ghost"))
        self.assertFalse(self.a.hidden("Bed1"))

    def test_clip_box(self):
        self.assertEqual(self.a.clip("Car"), [0, 0, 0, 1, 1, 1])
        self.assertIsNone(self.a.clip("Bed1"))

    def test_without_a_groups_file_nothing_changes(self):
        a = groups.Assign(None)
        self.assertEqual(a.bucket("Bed1", "k"), ("k", None))
        self.assertFalse(a.hidden("Ghost"))
        self.assertIsNone(a.clip("Car"))

    def test_an_object_in_two_groups_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Bed1.*two groups"):
            groups.Assign({"groups": {"bed": ["Bed1"], "gantry": ["Bed1"]}})

    def test_a_hidden_object_that_moves_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Bed1"):
            groups.Assign({"groups": {"bed": ["Bed1"]}, "hide": ["Bed1"]})


class MotionStillOffersIt(unittest.TestCase):
    """motion.py re-exports Assign and SEP, so code that imported them from there keeps working."""
    def test_same_objects(self):
        self.assertIs(motion.Assign, groups.Assign)
        self.assertEqual(motion.SEP, groups.SEP)


class TheExportKeyLeavesMotionOut(unittest.TestCase):
    """vt350#144: the motion renderer's export cache key hashes groups.py, not motion.py."""
    def test_export_code(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "cad", "motion"))
        src = open(os.path.join(os.path.dirname(os.path.dirname(HERE)), "cad", "motion", "render_frames.py")).read()
        line = next(l for l in src.splitlines() if l.startswith("EXPORT_CODE"))
        self.assertIn('"groups.py"', line)
        self.assertNotIn('"motion.py"', line)

    def test_the_export_does_not_import_motion(self):
        src = open(os.path.join(HERE, "export_meshes.py")).read()
        self.assertNotIn("import motion", src)


if __name__ == "__main__":
    unittest.main()
