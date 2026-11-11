#!/usr/bin/env python3
"""Tests for motion.py (vt350#135 AC4): the plain-python glue between the timeline's frames, the mesh export and the
Blender frame render. Stdlib only, in CI:  python3 platform/render/test_motion.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import motion  # noqa: E402


def fr(t, **groups):
    return {"t": t, "seq": 1, "pos": [0.0, 0.0, 0.0], "carried": None, "groups": groups}


GROUPS = {"groups": {"bed": ["Bed1", "Bed2"], "carriage": ["Car"], "Left": ["HeadL"]},
          "clip": {"Car": [0, 0, 0, 1, 1, 1]}, "hide": ["Ghost"]}


class Assign(unittest.TestCase):
    """Which bucket an exported part goes in: a moving group's parts get their own buckets, so Blender can move them."""
    def setUp(self):
        self.a = motion.Assign(GROUPS)

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
        a = motion.Assign(None)
        self.assertEqual(a.bucket("Bed1", "k"), ("k", None))
        self.assertFalse(a.hidden("Ghost"))
        self.assertIsNone(a.clip("Car"))

    def test_an_object_in_two_groups_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Bed1.*two groups"):
            motion.Assign({"groups": {"bed": ["Bed1"], "gantry": ["Bed1"]}})

    def test_a_hidden_object_that_moves_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Bed1"):
            motion.Assign({"groups": {"bed": ["Bed1"]}, "hide": ["Bed1"]})


class FramesFile(unittest.TestCase):
    """The frames the Blender job reads: the timeline's group translations, the frames picked, nothing else."""
    FRAMES = [fr(i / 10, bed=[0, 0, -i], carriage=[i, 0, 0]) for i in range(10)]

    def test_every_frame_by_default(self):
        f = motion.frames_file(self.FRAMES, fps=10)
        self.assertEqual(f["fps"], 10)
        self.assertEqual([x["i"] for x in f["frames"]], list(range(10)))
        self.assertEqual(f["frames"][3]["groups"], {"bed": [0, 0, -3], "carriage": [3, 0, 0]})

    def test_every_nth_frame_keeps_the_last_one(self):              # the end pose is the one to check
        f = motion.frames_file(self.FRAMES, fps=10, every=4)
        self.assertEqual([x["i"] for x in f["frames"]], [0, 4, 8, 9])
        self.assertEqual(f["fps"], 2.5)

    def test_carried_and_position_are_kept_for_captions(self):
        f = motion.frames_file([dict(fr(0, bed=[0, 0, 0]), carried="Left", pos=[1, 2, 3])], fps=30)
        self.assertEqual((f["frames"][0]["carried"], f["frames"][0]["pos"]), ("Left", [1, 2, 3]))

    def test_no_frames_is_refused(self):
        with self.assertRaises(ValueError):
            motion.frames_file([], fps=30)


class Offsets(unittest.TestCase):
    """A frame's translation per Blender object (bucket), from the bucket's group; mm."""
    BUCKETS = {"frame": {}, "bed__k": {"group": "bed"}, "carriage__k": {"group": "carriage"}, "Left__k": {"group": "Left"}}

    def test_each_bucket_moves_with_its_group_and_static_ones_stay(self):
        off = motion.offsets({"groups": {"bed": [0, 0, -5], "carriage": [1, 2, 0], "Left": [0, 0, 0]}}, self.BUCKETS)
        self.assertEqual(off, {"frame": (0, 0, 0), "bed__k": (0, 0, -5), "carriage__k": (1, 2, 0), "Left__k": (0, 0, 0)})

    def test_a_moving_bucket_whose_group_the_frame_lacks_is_refused(self):   # it would sit still and lie
        with self.assertRaisesRegex(ValueError, "Left"):
            motion.offsets({"groups": {"bed": [0, 0, 0], "carriage": [0, 0, 0]}}, self.BUCKETS)

    def test_check_scene_names_groups_that_have_no_buckets(self):        # a group the export never wrote
        with self.assertRaisesRegex(ValueError, "gantry"):
            motion.check_scene({"frames": [{"groups": {"bed": [0, 0, 0], "gantry": [0, 0, 0]}}]},
                               {"buckets": {"bed__k": {"group": "bed"}}})
        motion.check_scene({"frames": [{"groups": {"bed": [0, 0, 0]}}]}, {"buckets": {"bed__k": {"group": "bed"}}})


class Names(unittest.TestCase):
    def test_frame_file_names_sort_in_order(self):
        names = [motion.frame_name(i) for i in (0, 9, 10, 480)]
        self.assertEqual(names, sorted(names))
        self.assertEqual(motion.frame_name(7), "frame-00007.png")

    def test_missing_frames(self):
        d = tempfile.mkdtemp(prefix="motion-test-")
        self.addCleanup(shutil.rmtree, d, True)
        for i in (0, 4):
            open(os.path.join(d, motion.frame_name(i)), "w").close()
        self.assertEqual(motion.missing({"frames": [{"i": 0}, {"i": 4}, {"i": 8}]}, d), [8])


class Encode(unittest.TestCase):
    def test_the_video_command_numbers_frames_in_order(self):
        d = tempfile.mkdtemp(prefix="motion-test-")
        self.addCleanup(shutil.rmtree, d, True)
        for i in (0, 4, 8):
            open(os.path.join(d, motion.frame_name(i)), "w").close()
        cmd, listing = motion.encode_cmd(d, {"fps": 7.5, "frames": [{"i": 0}, {"i": 4}, {"i": 8}]}, "/x/out.mp4")
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertEqual(cmd[-1], "/x/out.mp4")
        self.assertIn("libx264", cmd)
        self.assertIn("yuv420p", cmd)                # plays in browsers
        self.assertEqual([l.split("'")[1] for l in listing.splitlines() if l.startswith("file")],
                         # the concat demuxer ignores the last entry's duration unless the file is listed again
                         [os.path.join(d, motion.frame_name(i)) for i in (0, 4, 8, 8)])
        self.assertIn("duration %s" % (1 / 7.5), listing)

    def test_a_missing_frame_is_refused(self):
        d = tempfile.mkdtemp(prefix="motion-test-")
        self.addCleanup(shutil.rmtree, d, True)
        with self.assertRaisesRegex(ValueError, "frame-00004"):
            motion.encode_cmd(d, {"fps": 30, "frames": [{"i": 4}]}, "/x/out.mp4")


if __name__ == "__main__":
    unittest.main(verbosity=1)
