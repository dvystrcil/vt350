"""Tests for rules.py (vt350#220): part selection and the licence check. Stdlib only (CI: viewer.yml).

    python3 platform/viewer/test_rules.py
"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules

P_HEAD = ["Model v33", "Left Toolhead", "A4Tv2 (DW-Tas, CC BY-NC-SA 4.0) v1"]


class Matches(unittest.TestCase):
    def test_each_key(self):
        self.assertTrue(rules.matches({"group": "Left Toolhead"}, "x", P_HEAD))
        self.assertFalse(rules.matches({"group": "Left"}, "x", P_HEAD))
        self.assertTrue(rules.matches({"group_prefix": "A4Tv2 (DW-Tas"}, "x", P_HEAD))
        self.assertTrue(rules.matches({"label": "Plate"}, "Plate", []))
        self.assertFalse(rules.matches({"label": "Plate"}, "Plate Back", []))
        self.assertTrue(rules.matches({"label_prefix": "Bowden"}, "Bowden Left", []))
        self.assertTrue(rules.matches({"label_contains": "CC0-1.0)"}, "O2S board (X, CC0-1.0)", []))

    def test_all_conditions_must_hold(self):
        m = {"group": "Left Toolhead", "label_prefix": "Bowden"}
        self.assertTrue(rules.matches(m, "Bowden Left", P_HEAD))
        self.assertFalse(rules.matches(m, "Bowden Left", ["Right Toolhead"]))

    def test_empty_match_matches_nothing(self):
        self.assertFalse(rules.matches({}, "anything", P_HEAD))
        self.assertFalse(rules.matches({"note": "only a note"}, "anything", P_HEAD))

    def test_split_path(self):
        self.assertEqual(rules.split_path("A / B (1) / C"), ["A", "B (1)", "C"])
        self.assertEqual(rules.split_path(""), [])


class SelectionT(unittest.TestCase):
    SEL = {"include": [{"group": "Carriage (1)"}, {"group": "Left Toolhead", "move": "on"}],
           "exclude": [{"label_prefix": "Bowden"}],
           "moves": {"on": {"from": "A", "to": "B"}}}

    def test_pick(self):
        s = rules.Selection(self.SEL)
        self.assertEqual(s.pick("Beacon", ["M", "Carriage (1)"]), (True, None))
        self.assertEqual(s.pick("Fan", P_HEAD), (True, "on"))
        self.assertEqual(s.pick("Bowden Left", P_HEAD), (False, None))      # exclude wins
        self.assertEqual(s.pick("Frame", ["M", "Frame"]), (False, None))

    def test_bad_files_refused(self):
        with self.assertRaises(ValueError):
            rules.Selection({"include": [{"group": "X", "move": "nope"}]})
        with self.assertRaises(ValueError):
            rules.Selection({"include": [{"grop": "X"}]})                   # a typo'd key
        with self.assertRaises(ValueError):
            rules.Selection({"include": [], "moves": {"m": {"from": "A"}}})

    def test_translation(self):
        self.assertEqual(rules.translation([0, 0, 0, 1, 2, 3], [10, 20, 30, 11, 22, 33]), [10, 20, 30])
        with self.assertRaises(ValueError):
            rules.translation([0, 0, 0, 1, 2, 3], [0, 0, 0, 1, 2, 3.5])


class Licences(unittest.TestCase):
    LIC = {"shareable": ["GPL-3.0-only", "CC-BY-NC-SA-4.0"],
           "rules": [{"label_prefix": "Own fan", "licence": "GPL-3.0-only", "source": "ours"},
                     {"group_prefix": "A4Tv2 (DW-Tas", "licence": "CC-BY-NC-SA-4.0", "source": "A4Tv2 LICENSE"},
                     {"label": "Vendor block", "licence": "LicenseRef-no-share", "source": "vendor page"}]}

    def test_first_rule_wins(self):
        self.assertEqual(rules.licence_of(self.LIC, "Own fan L", P_HEAD), ("GPL-3.0-only", "ours"))
        self.assertEqual(rules.licence_of(self.LIC, "Duct", P_HEAD), ("CC-BY-NC-SA-4.0", "A4Tv2 LICENSE"))

    def test_check_ok(self):
        lines, problems = rules.check(self.LIC, [{"label": "Duct", "path": " / ".join(P_HEAD)}])
        self.assertEqual(problems, [])
        self.assertTrue(lines[0].startswith("ok  CC-BY-NC-SA-4.0  Duct"))

    def test_check_fails_unknown_and_no_share(self):
        _, problems = rules.check(self.LIC, [{"label": "Mystery", "path": ["M", "Other"]},
                                             {"label": "Vendor block", "path": ["M"]}])
        self.assertEqual(len(problems), 2)
        self.assertTrue(problems[0].startswith("UNKNOWN"))
        self.assertTrue(problems[1].startswith("NOT SHAREABLE"))

    def test_rule_without_source_refused(self):
        with self.assertRaises(ValueError):
            rules.check({"rules": [{"label": "x", "licence": "MIT"}]}, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
