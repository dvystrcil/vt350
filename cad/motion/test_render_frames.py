#!/usr/bin/env python3
"""Tests for cad/motion/render_frames.py (vt350#135 AC4): the export's cache key, the dock camera, the frames file, the
batch-lane command and the export judgement. Plain python3, no FreeCAD or Blender:

    python3 cad/motion/test_render_frames.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_frames as rf  # noqa: E402

with open(os.path.join(HERE, "rig.json")) as _f:
    RIG = json.load(_f)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="render-frames-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        with open(p, "w") as f:
            f.write(text)
        return p


class ExportKey(Tmp):
    """The export is made once and reused while nothing that shapes it changes."""
    def setUp(self):
        super().setUp()
        self.groups = self.write("groups.json", '{"groups": {}}')
        self.code = [self.write("export_meshes.py", "a"), self.write("colours.json", "{}")]

    def test_the_same_inputs_give_the_same_key(self):
        self.assertEqual(rf.export_key(self.groups, self.code), rf.export_key(self.groups, self.code))

    def test_a_changed_groups_file_or_exporter_changes_it(self):
        k = rf.export_key(self.groups, self.code)
        self.write("colours.json", '{"roles": {}}')
        k2 = rf.export_key(self.groups, self.code)
        self.write("groups.json", '{"groups": {"bed": []}}')
        self.assertEqual(len({k, k2, rf.export_key(self.groups, self.code)}), 3)


class ExportJudgement(Tmp):
    """An export counts only if export.log says done and has no FAILED line but the part index's (non-fatal, #90)."""
    def test_done(self):
        self.write("export.log", "[ 1.0s] index: FAILED for x\n[ 2.0s] done: 9 buckets\n")
        self.assertIsNone(rf.export_problem(self.tmp))

    def test_no_log(self):
        self.assertIn("no export.log", rf.export_problem(self.tmp))

    def test_failed(self):
        self.write("export.log", "[ 1.0s] FAILED\nTraceback\n[ 2.0s] done: 9 buckets\n")
        self.assertIn("FAILED", rf.export_problem(self.tmp))

    def test_not_done(self):
        self.write("export.log", "[ 1.0s] opened x\n")
        self.assertIn("never finished", rf.export_problem(self.tmp))


class DockView(unittest.TestCase):
    """The camera frames both docks from the front, above the nozzles: computed from the rig, not typed in."""
    def setUp(self):
        self.v = rf.dock_view(RIG)

    def test_it_looks_at_the_middle_of_the_docks(self):
        xs = [h["nozzle"][0] for h in RIG["heads"].values()]
        self.assertAlmostEqual(self.v["look"][0], (min(xs) + max(xs)) / 2)
        self.assertAlmostEqual(self.v["look"][2], RIG["heads"]["Left"]["nozzle"][2])

    def test_it_stands_on_the_side_the_carriage_pushes_into_the_docks(self):
        # "into" is printer XY; the model's Y has the rig's sign. From the other side the back panel hides the docks
        into_y = RIG["heads"]["Left"]["into"][1] * RIG["xy"]["sign_xy"][1]
        self.assertGreater((self.v["pos"][1] - self.v["look"][1]) * into_y, 0)
        self.assertGreater(abs(self.v["pos"][1] - self.v["look"][1]), 500)
        self.assertGreater(self.v["pos"][2], self.v["look"][2])        # from above

    def test_it_has_a_name_and_a_lens(self):
        self.assertEqual(self.v["name"], "docks")
        self.assertGreater(self.v["lens_mm"], 0)


class Frames(unittest.TestCase):
    def test_the_committed_timeline_gives_frames_for_every_group(self):
        ff = rf.make_frames(RIG, rf.TIMELINE, fps=30, every=1)
        self.assertGreater(len(ff["frames"]), 100)
        groups = set(ff["frames"][0]["groups"])
        self.assertEqual(groups, {"bed", "gantry", "belt", "carriage", "Left", "Right"})

    def test_at_picks_the_frames_at_a_printer_xy(self):         # AC5: the T0 pickup at park X 21 / attach Y -68.96
        ff = rf.make_frames(RIG, rf.TIMELINE, fps=None, every=1)     # move ends: sampled frames miss exact points
        at = rf.frames_at(ff, 21.0, -68.96)
        self.assertTrue(at)
        for f in at:
            self.assertAlmostEqual(f["pos"][0], 21.0, places=3)
            self.assertAlmostEqual(f["pos"][1], -68.96, places=3)

    def test_at_nowhere_is_refused(self):
        ff = rf.make_frames(RIG, rf.TIMELINE, fps=None, every=1)
        with self.assertRaisesRegex(ValueError, "no frame"):
            rf.frames_at(ff, 999.0, 999.0)


class Submit(unittest.TestCase):
    def test_the_lane_command(self):
        cmd = rf.submit_cmd("/w/export", samples=32, size="1280x720", n=481, notify="dvystrcil/vt350#135",
                            deadline=7200)
        self.assertEqual(cmd[:2], ["python3", os.path.join(rf.HOMELAB, "bin", "gpu-batch-submit.py")])
        self.assertIn("blender", cmd)
        self.assertEqual(cmd[cmd.index("--input") + 1], "/w/export")
        self.assertEqual(cmd[cmd.index("--script") + 1], os.path.join(rf.ROOT, "platform", "render", "render.py"))
        self.assertEqual(cmd[cmd.index("--expect") + 1], "out/frame-*.png")
        self.assertEqual(cmd[cmd.index("--min-outputs") + 1], "481")     # every frame, or the job failed
        self.assertEqual(cmd[cmd.index("--deadline") + 1], "7200")
        tail = cmd[cmd.index("--", cmd.index("--min-outputs")) + 1:]
        self.assertEqual(tail, ["32", "--frames", "frames.json", "--view", "docks", "--size", "1280x720"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
