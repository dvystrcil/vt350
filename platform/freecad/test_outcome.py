# Tests for outcome.py (vt350#280): the text a model pass shows when it ends. Plain python3, no FreeCAD:
#
#   python3 platform/freecad/test_outcome.py
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outcome

LOG = "/repo/cad/data/logs/lite99_x.log"


class Saved(unittest.TestCase):
    def setUp(self):
        self.r = outcome.outcome("lite99_x", errs=[], dry=False, log_path=LOG, checks=12,
                                 saved=[("/m/vt350-ebox-9.FCStd", 12_036_134), ("/m/vt350-lite-99.FCStd", 37_254_679)])

    def test_kind_and_title(self):
        self.assertEqual(self.r.kind, "saved")
        self.assertEqual(self.r.title, "lite99_x: SAVED")

    def test_text_names_every_file_with_its_size_and_the_log(self):
        t = self.r.text
        self.assertIn("/m/vt350-ebox-9.FCStd (12.0 MB)", t)
        self.assertIn("/m/vt350-lite-99.FCStd (37.3 MB)", t)
        self.assertIn("All 12 checks passed", t)
        self.assertIn(LOG, t)

    def test_the_log_lines_are_the_ones_passes_always_wrote(self):
        self.assertEqual(self.r.log_lines, ["SAVED /m/vt350-ebox-9.FCStd 12036134", "SAVED /m/vt350-lite-99.FCStd 37254679"])


class Size(unittest.TestCase):
    def test_megabytes_from_one_mb_kilobytes_below(self):
        self.assertEqual(outcome.size(37_254_679), "37.3 MB")
        self.assertEqual(outcome.size(7059), "7.1 kB")


class NotSaved(unittest.TestCase):
    def setUp(self):
        self.errs = [f"check {i} failed" for i in range(7)]
        self.r = outcome.outcome("lite99_x", errs=self.errs, dry=False, log_path=LOG, checks=20, saved=[])

    def test_kind_and_title(self):
        self.assertEqual(self.r.kind, "not_saved")
        self.assertEqual(self.r.title, "lite99_x: NOT SAVED")

    def test_text_lists_the_first_five_failures_then_how_many_more(self):
        t = self.r.text
        self.assertIn("7 of 20 checks failed", t)
        for i in range(5): self.assertIn(f"check {i} failed", t)
        self.assertNotIn("check 5 failed", t)
        self.assertIn("and 2 more", t)
        self.assertIn(LOG, t)

    def test_a_long_failure_is_shortened(self):
        r = outcome.outcome("p", errs=["x" * 500], dry=False, log_path=LOG, checks=1, saved=[])
        line = next(l for l in r.text.splitlines() if "xxx" in l)
        self.assertLessEqual(len(line), 210)
        self.assertTrue(line.endswith("…"))

    def test_the_log_line_is_unchanged(self):
        self.assertEqual(self.r.log_lines, ["NOT SAVED"])

    def test_failures_win_over_a_dry_run(self):
        self.assertEqual(outcome.outcome("p", errs=["e"], dry=True, log_path=LOG, checks=3, saved=[]).kind, "not_saved")


class DryRun(unittest.TestCase):
    def test_a_dry_run_says_nothing_was_saved(self):
        r = outcome.outcome("p", errs=[], dry=True, log_path=LOG, checks=3, saved=[])
        self.assertEqual(r.kind, "dry")
        self.assertEqual(r.log_lines, ["DRY RUN (headless): all checks passed, not saved"])
        self.assertIn("not saved", r.text)


class NoticeMode(unittest.TestCase):
    def test_default_is_the_message_box(self):
        self.assertEqual(outcome.notice_mode({}), "box")

    def test_report_and_none_switch_the_box_off(self):
        self.assertEqual(outcome.notice_mode({"PASS_GUI_NOTICE": "report"}), "report")
        self.assertEqual(outcome.notice_mode({"PASS_GUI_NOTICE": "none"}), "none")

    def test_an_unknown_value_keeps_the_box(self):
        self.assertEqual(outcome.notice_mode({"PASS_GUI_NOTICE": "loud"}), "box")


if __name__ == "__main__":
    unittest.main(verbosity=2)
