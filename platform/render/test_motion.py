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
                         # each frame once: listing the last again adds a frame (EncodeWithFfmpeg)
                         [os.path.join(d, motion.frame_name(i)) for i in (0, 4, 8)])
        self.assertIn("duration %s" % (1 / 7.5), listing)

    def test_a_missing_frame_is_refused(self):
        d = tempfile.mkdtemp(prefix="motion-test-")
        self.addCleanup(shutil.rmtree, d, True)
        with self.assertRaisesRegex(ValueError, "frame-00004"):
            motion.encode_cmd(d, {"fps": 30, "frames": [{"i": 4}]}, "/x/out.mp4")

    def test_the_listing_is_read_from_a_file_not_stdin(self):
        # ffmpeg 9 resolves a stdin listing's entries against fd:, which can't open them (vt350#135, 2026-11-10)
        d = tempfile.mkdtemp(prefix="motion-test-")
        self.addCleanup(shutil.rmtree, d, True)
        open(os.path.join(d, motion.frame_name(0)), "w").close()
        cmd, listing = motion.encode_cmd(d, {"fps": 30, "frames": [{"i": 0}]}, "/x/out.mp4")
        src = cmd[cmd.index("-i") + 1]
        self.assertEqual(src, os.path.join(d, motion.LISTING))
        self.assertNotEqual(src, "-")


def png(path, w=16, h=16, rgb=(200, 80, 40)):
    """A tiny solid-colour PNG, stdlib only."""
    import struct
    import zlib

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    raw = b"".join(b"\0" + bytes(rgb) * w for _ in range(h))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs ffmpeg + ffprobe")
class EncodeWithFfmpeg(unittest.TestCase):
    """The real ffmpeg: the command's shape passing proves nothing about whether ffmpeg accepts it."""

    def test_three_frames_make_a_three_frame_video(self):
        d = tempfile.mkdtemp(prefix="motion-test-")
        self.addCleanup(shutil.rmtree, d, True)
        for i in (0, 2, 4):
            png(os.path.join(d, motion.frame_name(i)))
        out = os.path.join(d, "out.mp4")
        motion.encode(d, {"fps": 15, "frames": [{"i": 0}, {"i": 2}, {"i": 4}]}, out)
        import subprocess
        n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames,r_frame_rate", "-of", "default=nw=1", out],
                           capture_output=True, text=True, check=True).stdout
        self.assertIn("nb_read_frames=3", n)             # one per rendered frame, no extra copy of the last
        self.assertIn("r_frame_rate=15/1", n)
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                             capture_output=True, text=True, check=True).stdout
        self.assertAlmostEqual(float(dur), 3 / 15, places=3)


if __name__ == "__main__":
    unittest.main(verbosity=1)
