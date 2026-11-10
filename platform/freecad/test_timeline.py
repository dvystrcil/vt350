# Tests for timeline.py: kalisim timeline -> frames of group translations, with the dock handover (vt350#135 AC1).
#   python3 platform/freecad/test_timeline.py      # "Ran N tests" + "OK"
import io, json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline

# A small rig: model = origin + sign * printer; two heads docked at printer Y -60, approached from +Y (into = -Y).
RIG = {
    "xy": {"origin_model_xy": [-400.0, 30.0], "sign_xy": [1, 1]},
    "bed": {"group": "bed", "top_dz": 90.0},
    "gantry_groups": ["gantry", "belt"],
    "carriage_group": "carriage",
    "reference_head": "A",
    "heads": {
        # docked nozzle (model) and the carriage's offset from the gantry carriage at pickup (model)
        "A": {"group": "head A", "nozzle": [-380.0, -30.0, 380.0], "pickup": [-150.0, -250.0, 0.5],
              "dock": [20.0, -60.0], "into": [0, -1]},
        "B": {"group": "head B", "nozzle": [-80.0, -30.0, 380.0], "pickup": [150.0, -250.0, 0.5],
              "dock": [320.0, -60.0], "into": [0, -1]},
    },
}


def mv(seq, x, y, z=10.0, speed=100.0):
    return {"seq": seq, "kind": "move", "pos": [x, y, z, 0.0], "speed": speed, "tool": "extruder"}


def setpos(seq, x, y, z=10.0):
    return {"seq": seq, "kind": "set_position", "pos": [x, y, z, 0.0], "tool": "extruder"}


# pick up A: approach (20, -40) -> push to -66 (couples at -60) -> sideways -> out; then drop A: reverse
PICK_DROP_A = [setpos(1, 175, 175), mv(2, 20, -40), mv(3, 20, -66), mv(4, 25, -66), mv(5, 25, 50),
               mv(6, 25, -66), mv(7, 20, -66), mv(8, 20, -40), mv(9, 175, 175)]


class Kinematics(unittest.TestCase):
    def test_to_model(self):
        self.assertEqual(timeline.to_model(RIG, 20.0, -60.0), (-380.0, -30.0))
        flipped = dict(RIG, xy={"origin_model_xy": [0.0, 0.0], "sign_xy": [-1, 1]})
        self.assertEqual(timeline.to_model(flipped, 20.0, 5.0), (-20.0, 5.0))

    def test_groups_with_a_head_carried(self):
        # nozzle of A at its docked point: the carriage sits at A's pickup offset, A doesn't move, B never moves
        g = timeline.groups(RIG, (20.0, -60.0, 0.0), "A")
        self.assertEqual(g["carriage"], (-150.0, -250.0, 0.0))
        self.assertEqual(g["gantry"], (0.0, -250.0, 0.0))
        self.assertEqual(g["belt"], (0.0, -250.0, 0.0))
        self.assertEqual(g["head A"], (0.0, 0.0, -0.5))
        self.assertEqual(g["head B"], (0.0, 0.0, 0.0))
        self.assertEqual(g["bed"], (0.0, 0.0, 90.0))

    def test_carried_head_follows_and_bed_drops_with_z(self):
        g = timeline.groups(RIG, (120.0, 40.0, 30.0), "B")
        self.assertEqual(g["head B"], (-200.0, 100.0, -0.5))     # model (-280, 70) - docked (-80, -30)
        self.assertEqual(g["carriage"], (-280.0 + 80.0 + 150.0, 70.0 + 30.0 - 250.0, 0.0))
        self.assertEqual(g["bed"], (0.0, 0.0, 60.0))
        self.assertEqual(g["head A"], (0.0, 0.0, 0.0))

    def test_empty_carriage_uses_the_reference_head(self):
        self.assertEqual(timeline.groups(RIG, (20.0, -60.0, 0.0), None)["carriage"], (-150.0, -250.0, 0.0))
        self.assertEqual(timeline.groups(RIG, (20.0, -60.0, 0.0), None)["head A"], (0.0, 0.0, 0.0))


class Handover(unittest.TestCase):
    def setUp(self):
        self.segs = timeline.segments(RIG, PICK_DROP_A)

    def states(self):
        return [(s["start"][:2], s["end"][:2], s["carried"]) for s in self.segs]

    def test_couples_at_the_dock_point_and_rides_through_the_push(self):
        st = self.states()
        # approach split at the dock point: empty up to Y -60, then A rides the 6 mm push to -66
        self.assertIn(([20.0, -40.0], [20.0, -60.0], None), st)
        self.assertIn(([20.0, -60.0], [20.0, -66.0], "A"), st)
        self.assertIn(([20.0, -66.0], [25.0, -66.0], "A"), st)     # the sideways move out of the keyslots
        self.assertIn(([25.0, -66.0], [25.0, 50.0], "A"), st)

    def test_uncouples_at_the_dock_point_on_the_way_out(self):
        st = self.states()
        self.assertIn(([20.0, -66.0], [20.0, -60.0], "A"), st)     # pushed back into the dock
        self.assertIn(([20.0, -60.0], [20.0, -40.0], None), st)    # then the carriage leaves it there
        self.assertEqual(st[-1][2], None)

    def test_docked_head_stays_put_after_dropoff(self):
        last = self.segs[-1]
        self.assertEqual(timeline.groups(RIG, last["end"], last["carried"])["head A"], (0.0, 0.0, 0.0))

    def test_pushed_head_sits_at_the_large_opening(self):
        seg = [s for s in self.segs if s["end"][:2] == [20.0, -66.0] and s["carried"] == "A"][0]
        self.assertEqual(timeline.groups(RIG, seg["end"], "A")["head A"], (0.0, -6.0, -0.5))

    def test_tool_field_is_ignored(self):
        other = [dict(r, tool="extruder1") for r in PICK_DROP_A]
        self.assertEqual(timeline.segments(RIG, other), self.segs)

    def test_passing_beside_the_dock_doesnt_couple(self):
        segs = timeline.segments(RIG, [setpos(1, 175, 175), mv(2, 21, -40), mv(3, 21, -66)])
        self.assertEqual({s["carried"] for s in segs}, {None})

    def test_a_second_head_while_carrying_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "already carries A"):
            timeline.segments(RIG, PICK_DROP_A[:5] + [mv(6, 320, -40), mv(7, 320, -66)])

    def test_a_dock_entered_along_x(self):
        rig = json.loads(json.dumps(RIG))
        rig["heads"]["A"].update(dock=[0.0, 100.0], into=[-1, 0])            # dock on the left wall, pushed in -X
        segs = timeline.segments(rig, [setpos(1, 30, 100), mv(2, -6, 100), mv(3, -6, 140), mv(4, -6, 100),
                                       mv(5, 30, 100)])
        self.assertEqual([(s["start"][:2], s["carried"]) for s in segs],
                         [([30.0, 100.0], None), ([0.0, 100.0], "A"), ([-6.0, 100.0], "A"), ([-6.0, 140.0], "A"),
                          ([-6.0, 100.0], "A"), ([0.0, 100.0], None)])

    def test_reaching_the_dock_point_diagonally_doesnt_couple(self):
        # the carriage must arrive along the dock's line; one end on it isn't enough
        segs = timeline.segments(RIG, [setpos(1, 10, -40), mv(2, 20, -66)])
        self.assertEqual({s["carried"] for s in segs}, {None})

    def test_starting_past_the_dock_point_doesnt_couple(self):
        segs = timeline.segments(RIG, [setpos(1, 20, -60.5), mv(2, 20, -66)])
        self.assertEqual([s["carried"] for s in segs], [None])

    def test_starting_on_the_dock_point_couples_at_once(self):
        segs = timeline.segments(RIG, [setpos(1, 20, -60), mv(2, 20, -66)])
        self.assertEqual([(s["start"], s["carried"]) for s in segs], [([20.0, -60.0, 10.0], "A")])

    def test_backing_part_way_out_keeps_the_head(self):
        segs = timeline.segments(RIG, [setpos(1, 20, -66), mv(2, 20, -60.5)], carried="A")
        self.assertEqual([s["carried"] for s in segs], ["A"])

    def test_starting_inside_and_leaving_uncouples(self):
        segs = timeline.segments(RIG, [setpos(1, 20, -60.5), mv(2, 20, -40)], carried="A")
        self.assertEqual([(s["start"][:2], s["carried"]) for s in segs], [([20.0, -60.5], "A"), ([20.0, -60.0], None)])

    def test_leaving_another_head_s_dock_keeps_the_carried_head(self):
        segs = timeline.segments(RIG, [setpos(1, 20, -66), mv(2, 20, -40)], carried="B")
        self.assertEqual({s["carried"] for s in segs}, {"B"})

    def test_initial_head(self):
        segs = timeline.segments(RIG, [setpos(1, 175, 175), mv(2, 100, 100)], carried="B")
        self.assertEqual(segs[0]["carried"], "B")

    def test_set_position_jumps_without_a_segment(self):
        segs = timeline.segments(RIG, [setpos(1, 0, 0), setpos(2, 175, 175), mv(3, 175, 100)])
        self.assertEqual([(s["start"], s["end"]) for s in segs], [([175.0, 175.0, 10.0], [175.0, 100.0, 10.0])])

    def test_a_move_before_any_position_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "before any position"):
            timeline.segments(RIG, [mv(1, 1, 1)])

    def test_durations_from_speed(self):
        segs = timeline.segments(RIG, [setpos(1, 0, 0, 0), mv(2, 30, 40, 0, speed=50)])
        self.assertAlmostEqual(segs[0]["duration"], 1.0)
        self.assertEqual(segs[0]["seq"], 2)


class Frames(unittest.TestCase):
    def test_moves_mode_gives_one_frame_per_segment_end_plus_the_start(self):
        fr = timeline.frames(RIG, PICK_DROP_A, fps=None)
        segs = timeline.segments(RIG, PICK_DROP_A)
        self.assertEqual(len(fr), len(segs) + 1)
        self.assertEqual(fr[0]["pos"], [175.0, 175.0, 10.0])
        self.assertEqual(fr[0]["carried"], None)
        self.assertEqual([f["t"] for f in fr], sorted(f["t"] for f in fr))

    def test_sampled_frames_interpolate_and_keep_the_handover(self):
        fr = timeline.frames(RIG, [setpos(1, 20, -40), mv(2, 20, -66, speed=26)], fps=10)
        self.assertEqual(len(fr), 11)                          # 1 s of motion at 10 fps, both ends
        self.assertEqual(fr[5]["pos"][:2], [20.0, -53.0])
        carried = [f["carried"] for f in fr]
        self.assertEqual(carried[:8], [None] * 8)              # t 0 .. 0.7: before the dock point (t 0.769)
        self.assertEqual(carried[8:], ["A"] * 3)
        self.assertEqual(fr[-1]["groups"]["head A"], [0.0, -6.0, -0.5])

    def test_frame_record(self):
        f = timeline.frames(RIG, [setpos(1, 20, -60)], fps=None)[0]
        self.assertEqual(sorted(f), ["carried", "groups", "pos", "seq", "t"])
        self.assertEqual(f["pos"], [20.0, -60.0, 10.0])
        self.assertEqual(f["groups"]["carriage"], [-150.0, -250.0, 0.0])

    def test_start_frame_is_the_last_position_set(self):
        fr = timeline.frames(RIG, [setpos(1, 0, 0), setpos(2, 175, 175), mv(3, 175, 100), mv(4, 100, 100)], fps=None)
        self.assertEqual([f["seq"] for f in fr], [2, 3, 4])

    def test_last_frame_is_the_last_position_when_fps_doesnt_divide(self):
        fr = timeline.frames(RIG, [setpos(1, 0, 0, 0), mv(2, 10, 0, 0, speed=100), mv(3, 10, 25, 0, speed=100)], fps=4)
        self.assertEqual([f["t"] for f in fr], [0.0, 0.25, 0.35])
        self.assertEqual((fr[-1]["seq"], fr[-1]["pos"]), (3, [10.0, 25.0, 0.0]))

    def test_rounded_to_six_decimals(self):
        fr = timeline.frames(RIG, [setpos(1, 0, 0, 0), mv(2, 0, 100, 0, speed=300)], fps=None)
        self.assertEqual(fr[-1]["t"], 0.333333)


class Cli(unittest.TestCase):
    def test_reads_files_and_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as d:
            tl, rig = os.path.join(d, "t.jsonl"), os.path.join(d, "rig.json")
            with open(tl, "w") as f:
                f.write("\n".join(json.dumps(r) for r in PICK_DROP_A) + "\n\n")
            with open(rig, "w") as f:
                json.dump(RIG, f)
            out = timeline.main(["--timeline", tl, "--rig", rig, "--moves"])
            self.assertEqual([json.loads(l) for l in out], timeline.frames(RIG, PICK_DROP_A, fps=None))
            out = timeline.main(["--timeline", tl, "--rig", rig, "--fps", "5"])
            self.assertEqual(json.loads(out[-1])["carried"], None)

    def test_needs_fps_or_moves(self):
        with self.assertRaises(SystemExit):
            timeline.main(["--timeline", "x", "--rig", "y"])

    def test_needs_a_timeline_and_a_rig(self):
        for argv in (["--rig", "y", "--moves"], ["--timeline", "x", "--moves"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                timeline.main(argv)


if __name__ == "__main__":
    unittest.main(verbosity=2)
