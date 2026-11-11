#!/usr/bin/env python3
"""Tests for player.py's plain-python side (vt350#135 AC3): the playback clock, the group check, the mover that applies
frames and restores every Placement, the read-only copy of the model, and the environment the GUI reads.

Plain python3, no FreeCAD:  python3 platform/freecad/test_player.py
The FreeCAD side (real Placements under a rotated parent) is test_player_fc.py, run under freecadcmd.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import player  # noqa: E402


def read(path):
    with open(path, "rb") as f:
        return f.read()


def fr(t, **groups):
    return {"t": t, "seq": 1, "pos": [0.0, 0.0, 0.0], "carried": None, "groups": groups}


FRAMES = [fr(0.0), fr(0.5), fr(1.0), fr(1.5), fr(2.0)]


class Clock(unittest.TestCase):
    def setUp(self):
        self.c = player.Clock(FRAMES)

    def test_starts_paused_on_the_first_frame(self):
        self.assertEqual((self.c.index, self.c.playing, self.c.speed), (0, False, 1.0))

    def test_advance_does_nothing_while_paused(self):
        self.assertEqual(self.c.advance(10.0), 0)

    def test_advance_shows_the_last_frame_at_or_before_the_time(self):
        self.c.play()
        self.assertEqual(self.c.advance(0.49), 0)
        self.assertEqual(self.c.advance(0.02), 1)       # t 0.51
        self.assertEqual(self.c.advance(0.6), 2)        # t 1.11

    def test_the_speed_factor_scales_time(self):
        self.c.set_speed(4.0); self.c.play()
        self.assertEqual(self.c.advance(0.25), 2)       # 1.0 s of timeline

    def test_slow_motion(self):
        self.c.set_speed(0.25); self.c.play()
        self.assertEqual(self.c.advance(1.9), 0)        # 0.475 s
        self.assertEqual(self.c.advance(0.1), 1)        # 0.5 s

    def test_a_speed_of_zero_or_less_is_refused(self):
        for bad in (0.0, -1.0):
            with self.assertRaisesRegex(ValueError, "speed"):
                self.c.set_speed(bad)

    def test_it_stops_playing_at_the_end(self):
        self.c.play()
        self.assertEqual(self.c.advance(99.0), 4)
        self.assertFalse(self.c.playing)
        self.assertTrue(self.c.at_end)

    def test_play_at_the_end_starts_again(self):
        self.c.play(); self.c.advance(99.0); self.c.play()
        self.assertEqual((self.c.index, self.c.playing), (0, True))
        self.assertEqual(self.c.advance(0.5), 1)

    def test_pause_keeps_the_frame(self):
        self.c.play(); self.c.advance(1.2); self.c.pause()
        self.assertEqual((self.c.index, self.c.playing), (2, False))
        self.assertEqual(self.c.advance(5.0), 2)

    def test_play_after_pause_resumes_from_the_paused_time(self):
        self.c.play(); self.c.advance(1.2); self.c.pause(); self.c.play()
        self.assertEqual(self.c.advance(0.29), 2)       # 1.49
        self.assertEqual(self.c.advance(0.02), 3)       # 1.51

    def test_step_pauses_and_moves_one_frame(self):
        self.c.play(); self.c.advance(0.6)
        self.assertEqual(self.c.step(1), 2)
        self.assertFalse(self.c.playing)
        self.assertEqual(self.c.step(-1), 1)

    def test_step_is_clamped_to_the_ends(self):
        self.assertEqual(self.c.step(-1), 0)
        self.assertEqual(self.c.step(99), 4)

    def test_play_after_step_continues_from_that_frame(self):
        self.c.step(3); self.c.play()
        self.assertEqual(self.c.advance(0.49), 3)
        self.assertEqual(self.c.advance(0.02), 4)

    def test_seek(self):
        self.assertEqual(self.c.seek(2), 2)
        self.assertEqual(self.c.seek(-5), 0)
        self.assertEqual(self.c.seek(50), 4)

    def test_rewind(self):
        self.c.play(); self.c.advance(1.7); self.c.rewind()
        self.assertEqual((self.c.index, self.c.playing), (0, False))

    def test_no_frames_is_refused(self):
        with self.assertRaisesRegex(ValueError, "no frames"):
            player.Clock([])


class FakeBackend:
    """A Placement is a (x, y, z) tuple; move() adds d to the saved one, the way the FreeCAD backend does."""
    def __init__(self):
        self.moves = 0

    def save(self, obj):
        return obj["pl"]

    def move(self, obj, saved, d):
        self.moves += 1
        obj["pl"] = tuple(a + b for a, b in zip(saved, d))

    def restore(self, obj, saved):
        obj["pl"] = saved


class Mover(unittest.TestCase):
    def setUp(self):
        self.a1, self.a2, self.b = {"pl": (1.0, 2.0, 3.0)}, {"pl": (0.0, 0.0, 0.0)}, {"pl": (5.0, 5.0, 5.0)}
        self.be = FakeBackend()
        self.m = player.Mover({"a": [self.a1, self.a2], "b": [self.b]}, self.be)

    def test_apply_translates_each_group_from_its_saved_pose(self):
        self.m.apply(fr(0, a=[10.0, 0.0, 0.0], b=[0.0, 0.0, -1.0]))
        self.assertEqual((self.a1["pl"], self.a2["pl"], self.b["pl"]), ((11.0, 2.0, 3.0), (10.0, 0.0, 0.0), (5.0, 5.0, 4.0)))

    def test_translations_do_not_accumulate(self):           # each frame is from the SAVED pose, not the last frame
        self.m.apply(fr(0, a=[10.0, 0.0, 0.0])); self.m.apply(fr(1, a=[20.0, 0.0, 0.0]))
        self.assertEqual(self.a1["pl"], (21.0, 2.0, 3.0))

    def test_an_unchanged_group_is_not_touched(self):        # a docked head: 0 0 0 every frame
        self.m.apply(fr(0, a=[1.0, 0.0, 0.0], b=[0.0, 0.0, 0.0]))
        n = self.be.moves
        self.m.apply(fr(1, a=[2.0, 0.0, 0.0], b=[0.0, 0.0, 0.0]))
        self.assertEqual(self.be.moves - n, 2)                # only a's two objects

    def test_restore_puts_every_placement_back(self):
        self.m.apply(fr(0, a=[10.0, 1.0, 0.0], b=[0.0, 0.0, -1.0]))
        self.assertEqual(self.m.restore(), 3)
        self.assertEqual((self.a1["pl"], self.a2["pl"], self.b["pl"]), ((1.0, 2.0, 3.0), (0.0, 0.0, 0.0), (5.0, 5.0, 5.0)))

    def test_apply_after_restore_moves_again(self):          # restore forgets the last translation
        self.m.apply(fr(0, a=[10.0, 0.0, 0.0])); self.m.restore(); self.m.apply(fr(1, a=[10.0, 0.0, 0.0]))
        self.assertEqual(self.a1["pl"], (11.0, 2.0, 3.0))

    def test_a_frame_group_with_no_objects_is_refused(self):
        with self.assertRaisesRegex(KeyError, "c"):
            self.m.apply(fr(0, c=[1.0, 0.0, 0.0]))


class CheckGroups(unittest.TestCase):
    FR = [fr(0, bed=[0, 0, 1], Left=[0, 0, 0])]

    def test_ok(self):
        player.check_groups({"bed": ["A"], "Left": ["B", "C"], "extra": ["D"]}, self.FR)

    def test_a_frame_group_missing_from_the_groups_file(self):
        with self.assertRaisesRegex(ValueError, "Left"):
            player.check_groups({"bed": ["A"]}, self.FR)

    def test_an_object_in_two_groups(self):
        with self.assertRaisesRegex(ValueError, "B.*two groups|two groups.*B"):
            player.check_groups({"bed": ["B"], "Left": ["B"]}, self.FR)

    def test_an_empty_group(self):
        with self.assertRaisesRegex(ValueError, "Left.*empty|empty.*Left"):
            player.check_groups({"bed": ["A"], "Left": []}, self.FR)


class CheckClip(unittest.TestCase):
    """clip {Name: [xmin, ymin, zmin, xmax, ymax, zmax]}: a part shown cut down to a box (global, at the model pose),
    because the whole part doesn't move rigidly (a belt loop: its side runs change length)."""
    G = {"belt": ["B1", "B2"], "bed": ["A"]}

    def test_ok(self):
        player.check_clip({"B1": [0, 0, 0, 1, 1, 1]}, self.G)

    def test_a_name_in_no_group(self):
        with self.assertRaisesRegex(ValueError, "Z"):
            player.check_clip({"Z": [0, 0, 0, 1, 1, 1]}, self.G)

    def test_a_box_without_six_numbers(self):
        with self.assertRaisesRegex(ValueError, "B1"):
            player.check_clip({"B1": [0, 0, 0, 1, 1]}, self.G)

    def test_an_empty_box(self):
        with self.assertRaisesRegex(ValueError, "B1"):
            player.check_clip({"B1": [0, 0, 0, 1, -1, 1]}, self.G)


class CheckHide(unittest.TestCase):
    """hide [Name]: objects shown nowhere while the player is open (a copy of a moving part, e.g. the carriage copy
    each dock holds at its pickup pose, which would stay behind as a ghost). A hidden object must not move."""
    G = {"carriage": ["C1"], "bed": ["A"]}

    def test_ok(self):
        player.check_hide(["D1", "D2"], self.G)

    def test_a_moving_object_is_refused(self):
        with self.assertRaisesRegex(ValueError, "C1.*carriage"):
            player.check_hide(["D1", "C1"], self.G)


class Resolve(unittest.TestCase):
    class Doc:
        def __init__(self, names): self.names = names
        def getObject(self, n): return {"Name": n} if n in self.names else None

    def test_names_become_objects(self):
        got = player.resolve(self.Doc({"A", "B"}), {"g": ["A", "B"]})
        self.assertEqual(got, {"g": [{"Name": "A"}, {"Name": "B"}]})

    def test_a_missing_name_is_refused_with_its_group(self):
        with self.assertRaisesRegex(ValueError, "g.*Z|Z.*g"):
            player.resolve(self.Doc({"A"}), {"g": ["A", "Z"]})


class ReadOnlyCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="player-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.model = os.path.join(self.tmp, "m.FCStd")
        with open(self.model, "wb") as f:
            f.write(b"PK model bytes")

    def test_the_copy_has_the_bytes_and_removing_it_leaves_the_model(self):
        before = hashlib.sha256(read(self.model)).hexdigest()
        path, cleanup = player.private_copy(self.model)
        self.assertNotEqual(os.path.dirname(path), self.tmp)
        self.assertEqual(os.path.basename(path), "m.FCStd")
        self.assertEqual(read(path), b"PK model bytes")
        with open(path, "wb") as f:                          # a stray Save lands on the copy
            f.write(b"changed")
        cleanup()
        self.assertFalse(os.path.exists(os.path.dirname(path)))
        self.assertEqual(hashlib.sha256(read(self.model)).hexdigest(), before)

    def test_the_copy_goes_under_the_dir_given(self):     # /tmp can be too small (Disk quota exceeded on lite-30)
        where = os.path.join(self.tmp, "copies")
        path, cleanup = player.private_copy(self.model, where)
        self.assertEqual(os.path.dirname(os.path.dirname(path)), where)
        cleanup()
        self.assertEqual(os.listdir(where), [])

    def test_cleanup_twice_is_harmless(self):
        _, cleanup = player.private_copy(self.model)
        cleanup(); cleanup()

    def test_a_missing_model_is_refused(self):
        with self.assertRaises(FileNotFoundError):
            player.private_copy(os.path.join(self.tmp, "nope.FCStd"))


class Config(unittest.TestCase):
    ENV = {"MOTION_MODEL": "/m.FCStd", "MOTION_GROUPS": "/g.json", "MOTION_TIMELINE": "/t.jsonl", "MOTION_RIG": "/r.json"}

    def test_defaults(self):
        c = player.config(self.ENV)
        self.assertEqual(c, {"model": "/m.FCStd", "groups": "/g.json", "timeline": "/t.jsonl", "rig": "/r.json",
                             "fps": 30.0, "speed": 1.0, "carried": None, "autotest": None, "copy_dir": None})

    def test_everything_set(self):
        c = player.config(dict(self.ENV, MOTION_FPS="60", MOTION_SPEED="0.5", MOTION_CARRIED="Left",
                               MOTION_AUTOTEST="/out.json", MOTION_COPY_DIR="/work/motion"))
        self.assertEqual((c["fps"], c["speed"], c["carried"], c["autotest"], c["copy_dir"]),
                         (60.0, 0.5, "Left", "/out.json", "/work/motion"))

    def test_each_required_variable_is_named_when_missing(self):
        for k in self.ENV:
            with self.assertRaisesRegex(ValueError, k):
                player.config({x: v for x, v in self.ENV.items() if x != k})


class GuiMain(unittest.TestCase):
    """Under MOTION_AUTOTEST every failure, the panel's own included, writes {"fatal": ...} and quits FreeCAD: a
    panel that failed to open once left FreeCAD running until the 25 min timeout."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="player-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = os.path.join(self.tmp, "out.json")
        self.env = dict(Config.ENV, MOTION_AUTOTEST=self.out)
        self.exits = []

    def run_main(self, panel, test):
        player.gui_main(self.env, panel=panel, test=test, keep=lambda p: None, exit=self.exits.append)
        with open(self.out) as f:
            return json.load(f)

    def test_a_panel_that_fails_to_open_is_reported_and_quits(self):
        def panel(cfg): raise OSError("Disk quota exceeded")
        res = self.run_main(panel, None)
        self.assertIn("Disk quota exceeded", res["fatal"])
        self.assertEqual(self.exits, [0])

    def test_a_failing_test_is_reported_and_quits(self):
        def test(p, out): raise RuntimeError("boom")
        self.assertIn("boom", self.run_main(lambda cfg: "panel", test)["fatal"])
        self.assertEqual(self.exits, [0])

    def test_a_passing_test_writes_its_result_and_quits(self):
        def test(p, out):
            with open(out, "w") as f:
                json.dump({"panel": p}, f)
        self.assertEqual(self.run_main(lambda cfg: "panel", test), {"panel": "panel"})
        self.assertEqual(self.exits, [0])

    def test_without_autotest_it_returns_the_panel_and_stays_open(self):
        env = {k: v for k, v in self.env.items() if k != "MOTION_AUTOTEST"}
        self.assertEqual(player.gui_main(env, panel=lambda cfg: "panel", keep=lambda p: None, exit=self.exits.append), "panel")
        self.assertEqual(self.exits, [])


class Load(unittest.TestCase):
    """load() builds the frames with timeline.py and the groups from the groups file, and checks they fit."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="player-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        root = os.path.dirname(os.path.dirname(HERE))
        self.rig = os.path.join(root, "cad", "motion", "rig.json")
        self.timeline = os.path.join(root, "cad", "klipper", "toolchange_timeline.jsonl")
        with open(self.rig) as f:
            rig = json.load(f)
        self.groups = {g: [f"{g}-obj"] for g in [rig["bed"]["group"], rig["carriage_group"], *rig["gantry_groups"],
                                                 *(h["group"] for h in rig["heads"].values())]}
        self.gpath = os.path.join(self.tmp, "groups.json")

    def cfg(self, groups, **extra):
        with open(self.gpath, "w") as f:
            json.dump(dict({"model": "x", "groups": groups}, **extra), f)
        return dict(player.config({"MOTION_MODEL": "/m", "MOTION_GROUPS": self.gpath, "MOTION_TIMELINE": self.timeline,
                                   "MOTION_RIG": self.rig}), fps=10.0)

    def test_the_committed_timeline_loads(self):
        frames, groups, clip, hide = player.load(self.cfg(self.groups))
        self.assertEqual((groups, clip, hide), (self.groups, {}, []))
        self.assertGreater(len(frames), 10)
        self.assertEqual({fr_["carried"] for fr_ in frames}, {None, "Left", "Right"})

    def test_the_clips_are_loaded_and_checked(self):
        _, _, clip, _ = player.load(self.cfg(self.groups, clip={"belt-obj": [0, 0, 0, 1, 2, 3]}))
        self.assertEqual(clip, {"belt-obj": [0, 0, 0, 1, 2, 3]})
        with self.assertRaisesRegex(ValueError, "nope"):
            player.load(self.cfg(self.groups, clip={"nope": [0, 0, 0, 1, 2, 3]}))

    def test_the_hidden_objects_are_loaded_and_checked(self):
        self.assertEqual(player.load(self.cfg(self.groups, hide=["dock-copy"]))[3], ["dock-copy"])
        with self.assertRaisesRegex(ValueError, "bed-obj"):
            player.load(self.cfg(self.groups, hide=["bed-obj"]))

    def test_a_groups_file_without_a_rig_group_is_refused(self):
        g = dict(self.groups); del g["Right"]
        with self.assertRaisesRegex(ValueError, "Right"):
            player.load(self.cfg(g))


if __name__ == "__main__":
    unittest.main(verbosity=1)
