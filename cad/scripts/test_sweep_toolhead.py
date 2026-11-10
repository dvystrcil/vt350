# Tests for sweep_toolhead.plan_stage(): the plan JSON's temp dir is removed whether the plan stage succeeds, fails
# or writes nothing. A fake freecadcmd (plain python3) stands in, so these run anywhere, in CI too:
#   python3 cad/scripts/test_sweep_toolhead.py      # "Ran N tests" + "OK"
import os, shutil, sys, tempfile, textwrap, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweep_toolhead

# argv is [fake, sweep_toolhead.py]; FAKE_MODE picks what the plan stage writes to $SWEEP_PLAN.
FAKE = textwrap.dedent("""\
    import json, os
    mode, out = os.environ["FAKE_MODE"], os.environ["SWEEP_PLAN"]
    if mode == "ok": json.dump(dict(notes=["planned"]), open(out, "w"))
    if mode == "fatal": json.dump(dict(fatal="plan blew up"), open(out, "w"))
    """)


class BedBottom(unittest.TestCase):
    """The bed-bottom poses use the configured floor (printer.cfg: 5 mm above the measured lower stop,
    litelib.BED_FLOOR_DZ), never the bounding-box estimate: on lite-29 that landed the 2020 on the filter ENVELOPE box
    at -238.00 (vt350#82). The estimate is still checked against the measured stop (litelib.BED_LOWEST_DZ)."""
    LAND = [(238.0, "2020 (2)", "Filter envelope"), (239.5, "M3 Locknut002", "backbone-350 v2"),
            (239.5, "M3x12-Screw009", "backbone-350 v2")]

    def test_the_configured_floor_sets_the_poses(self):   # printer.cfg stops the bed 5 mm above the measured stop
        dz, note = sweep_toolhead.bed_bottom(self.LAND, -242.0, -237.0)
        self.assertEqual(dz, -237.0)
        self.assertEqual(note, "bed bottom: dZ -237.00 (the configured floor, litelib.BED_FLOOR_DZ: printer.cfg stops "
                               "the bed 5.00 mm above the measured lower stop -242.00 from z_sweep.py); bounding-box "
                               "estimate -238.00 (2020 (2) lands on Filter envelope), next: -239.50 M3 Locknut002 on "
                               "backbone-350 v2; -239.50 M3x12-Screw009 on backbone-350 v2")

    def test_a_floor_at_the_lower_stop_is_allowed(self):          # 0 mm margin, to within rounding
        self.assertEqual(sweep_toolhead.bed_bottom(self.LAND, -242.0, -242.0 - 1e-6)[0], -242.0 - 1e-6)

    def test_a_floor_below_the_lower_stop_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, "floor .* below the measured lower stop"):
            sweep_toolhead.bed_bottom(self.LAND, -242.0, -242.5)

    def test_an_estimate_equal_to_the_stop_is_fine(self):
        self.assertEqual(sweep_toolhead.bed_bottom([(242.0, "a", "b")], -242.0, -237.0)[0], -237.0)

    def test_the_note_lists_three_next_landings(self):
        land = [(238.0 + i, f"p{i}", "q") for i in range(6)]
        note = sweep_toolhead.bed_bottom(land, -245.0, -240.0)[1]
        self.assertTrue(note.endswith("next: -239.00 p1 on q; -240.00 p2 on q; -241.00 p3 on q"), note)

    def test_rounding_at_the_stop_is_tolerated(self):              # within 1e-6 of the stop is the same stop
        self.assertEqual(sweep_toolhead.bed_bottom([(242.0 + 1e-6, "a", "b")], -242.0, -237.0)[0], -237.0)

    def test_a_box_estimate_below_the_measured_stop_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, "below the measured lower stop"):
            sweep_toolhead.bed_bottom([(242.5, "a", "b")], -242.0, -237.0)

    def test_nothing_landing_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, "nothing"):
            sweep_toolhead.bed_bottom([], -242.0, -237.0)


class PlanStage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sweep-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.temp = os.path.join(self.tmp, "temp"); os.makedirs(self.temp)
        old = tempfile.tempdir
        def restore():
            tempfile.tempdir = old
            os.environ.pop("FAKE_MODE", None)
        self.addCleanup(restore)
        tempfile.tempdir = self.temp
        fake = os.path.join(self.tmp, "fake_freecadcmd.py"); open(fake, "w").write(FAKE)
        self.cmd = [sys.executable, fake]

    def plan(self, mode):
        os.environ["FAKE_MODE"] = mode
        return sweep_toolhead.plan_stage(self.cmd)

    def test_a_plan_is_returned_and_its_dir_removed(self):
        self.assertEqual(self.plan("ok"), {"notes": ["planned"]})
        self.assertEqual(os.listdir(self.temp), [])

    def test_a_failed_plan_stage_exits_and_removes_its_dir(self):
        with self.assertRaisesRegex(SystemExit, "plan blew up"):
            self.plan("fatal")
        self.assertEqual(os.listdir(self.temp), [])

    def test_a_plan_stage_that_wrote_nothing_exits_and_removes_its_dir(self):
        with self.assertRaisesRegex(SystemExit, "wrote nothing"):
            self.plan("none")
        self.assertEqual(os.listdir(self.temp), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
