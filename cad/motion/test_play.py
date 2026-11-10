#!/usr/bin/env python3
"""Tests for play.py, the VT350's launcher for the FreeCAD motion player (vt350#135 AC3): the plan's groups named the
way the rig names them, the cached groups file, the default model, and the FreeCAD command.

Plain python3, no FreeCAD (the plan stage is a fake):  python3 cad/motion/test_play.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import play  # noqa: E402

with open(os.path.join(HERE, "rig.json")) as _f:
    RIG = json.load(_f)
PLAN = {"bed": ["B1", "B2"], "gantry": ["G1"], "belt": ["E1"], "carriage": ["C1"],
        "heads": {"Left": ["L1", "LP"], "Right": ["R1"]}, "exclude": ["X"], "poses": {}, "labels": {"B1": "bed frame"}}


def write(path, data):
    with open(path, "wb") as f:
        f.write(data)


class GroupsFromPlan(unittest.TestCase):
    def test_the_rig_names_every_group(self):
        self.assertEqual(play.groups_from_plan(PLAN, RIG),
                         {"bed": ["B1", "B2"], "gantry": ["G1"], "belt": ["E1"], "carriage": ["C1"],
                          "Left": ["L1", "LP"], "Right": ["R1"]})

    def test_a_group_the_plan_lacks_is_refused(self):
        plan = {k: v for k, v in PLAN.items() if k != "belt"}
        with self.assertRaisesRegex(ValueError, "belt"):
            play.groups_from_plan(plan, RIG)

    def test_a_head_the_plan_lacks_is_refused(self):
        plan = dict(PLAN, heads={"Left": ["L1"]})
        with self.assertRaisesRegex(ValueError, "Right"):
            play.groups_from_plan(plan, RIG)


class GroupsFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="play-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.model = os.path.join(self.tmp, "vt350-lite-30.FCStd")
        write(self.model, b"model bytes")
        self.calls = []

    def run_plan(self, model):
        self.calls.append(model)
        return PLAN

    def get(self):
        return play.groups_file(self.model, RIG, self.tmp, self.run_plan)

    def test_the_plan_runs_once_then_the_file_is_reused(self):
        p1 = self.get(); p2 = self.get()
        self.assertEqual((p1, len(self.calls)), (p2, 1))
        self.assertEqual(os.path.dirname(p1), os.path.join(self.tmp, "motion"))
        with open(p1) as f:
            g = json.load(f)
        self.assertEqual(g["groups"]["Left"], ["L1", "LP"])
        self.assertEqual(g["model"], self.model)

    def test_each_belt_is_clipped_to_the_sweeps_band(self):     # the whole loop shot out of the frame (vt350#135)
        sys.path.insert(0, os.path.join(ROOT, "cad", "studies"))
        import sweep_toolhead
        with open(self.get()) as f:
            g = json.load(f)
        self.assertEqual(g["clip"], {"E1": list(sweep_toolhead.BELT_CLIP)})

    def test_new_model_bytes_run_the_plan_again(self):
        p1 = self.get(); write(self.model, b"other bytes"); p2 = self.get()
        self.assertNotEqual(p1, p2)
        self.assertEqual(len(self.calls), 2)

    def test_a_failed_plan_leaves_no_file(self):
        def boom(model): raise SystemExit("plan stage failed")
        with self.assertRaises(SystemExit):
            play.groups_file(self.model, RIG, self.tmp, boom)
        self.assertEqual(os.listdir(os.path.join(self.tmp, "motion")), [])


class DefaultModel(unittest.TestCase):
    def test_the_model_the_committed_sweep_log_ran_on(self):    # the rig's numbers come from that log
        self.assertEqual(play.default_model(os.path.join(ROOT, "cad", "data", "logs", "sweep_toolhead.log"), "/models"),
                         "/models/vt350-lite-30.FCStd")

    def test_a_log_with_no_model_line_is_refused(self):
        tmp = tempfile.mkdtemp(prefix="play-test-")
        self.addCleanup(shutil.rmtree, tmp, True)
        log = os.path.join(tmp, "sweep.log"); write(log, b"[ 1.0s] nothing here\n")
        with self.assertRaisesRegex(ValueError, "model"):
            play.default_model(log, "/models")


class Command(unittest.TestCase):
    CFG = {"model": "/m/vt350-lite-30.FCStd", "groups": "/w/g.json", "timeline": "/t.jsonl", "rig": "/r.json",
           "fps": 30.0, "speed": 0.5, "carried": None, "autotest": None, "copy_dir": "/w/motion"}

    def test_the_gui_runs_the_player_macro_with_the_motion_environment(self):
        argv, env = play.command(self.CFG, ["/app/FreeCAD.AppImage"])
        self.assertEqual(argv, ["/app/FreeCAD.AppImage", os.path.join(ROOT, "platform", "freecad", "player_gui.FCMacro")])
        self.assertEqual(env, {"MOTION_MODEL": "/m/vt350-lite-30.FCStd", "MOTION_GROUPS": "/w/g.json",
                               "MOTION_TIMELINE": "/t.jsonl", "MOTION_RIG": "/r.json", "MOTION_FPS": "30.0",
                               "MOTION_SPEED": "0.5", "MOTION_COPY_DIR": "/w/motion"})

    def test_autotest_runs_under_xvfb_and_says_where_to_write(self):
        argv, env = play.command(dict(self.CFG, autotest="/w/out.json", carried="Left"), ["/app/FreeCAD.AppImage"])
        self.assertEqual(argv[:3], ["xvfb-run", "-a", "/app/FreeCAD.AppImage"])
        self.assertEqual((env["MOTION_AUTOTEST"], env["MOTION_CARRIED"]), ("/w/out.json", "Left"))

    def test_the_environment_is_what_the_player_reads(self):    # player.config() accepts exactly this
        sys.path.insert(0, os.path.join(ROOT, "platform", "freecad"))
        import player
        _, env = play.command(dict(self.CFG, autotest="/o.json", carried="Right"), ["fc"])
        self.assertEqual(player.config(env), dict(self.CFG, autotest="/o.json", carried="Right"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
