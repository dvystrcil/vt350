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
