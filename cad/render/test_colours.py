#!/usr/bin/env python3
"""Tests for cad/render/colours.py (#38). Run: python3 cad/render/test_colours.py"""
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("colours", os.path.join(HERE, "colours.py"))
co = importlib.util.module_from_spec(spec)
spec.loader.exec_module(co)

MAP = {
    "roles": {"frame": {"hex": "#8FD5B9", "kind": "paint", "roughness": 0.45},
              "accent": {"hex": "#E8682A", "kind": "plastic", "roughness": 0.65},
              "printed": {"hex": "#ECEAE4", "kind": "plastic", "roughness": 0.65}},
    "rules": [{"role": "frame", "group": "VT Frame|Door Frame", "material": "Alumin"},
              {"role": "accent", "label": r"^\[a\]_"},
              {"role": "printed", "material": "ABS"}],
}


class Match(unittest.TestCase):
    def test_frame_needs_group_and_material(self):
        self.assertEqual(co.role_of(MAP, "2040 (2)", "Trident / 4040-350 VT Frame v12 / Horizontals", "Aluminum-6061-T6"), "frame")
        # a steel screw inside the frame group is not the frame
        self.assertIsNone(co.role_of(MAP, "M5x16", "Trident / 4040-350 VT Frame v12 / Horizontals", "Steel-Generic"))

    def test_first_rule_wins(self):
        # an [a]_ part made of ABS is accent, not printed
        self.assertEqual(co.role_of(MAP, "[a]_Duct-4010-left", "Left Toolhead", "ABS-Generic"), "accent")
        self.assertEqual(co.role_of(MAP, "Top Cap", "Gantry", "ABS-Generic"), "printed")

    def test_no_rule_keeps_the_model_colour(self):
        self.assertIsNone(co.role_of(MAP, "Motor", "Z", "Default"))

    def test_unknown_role_in_a_rule_is_rejected(self):
        bad = dict(MAP, rules=[{"role": "nope", "label": "x"}])
        with self.assertRaises(ValueError):
            co.validate(bad)

    def test_rule_without_a_matcher_is_rejected(self):
        bad = dict(MAP, rules=[{"role": "frame"}])
        with self.assertRaises(ValueError):
            co.validate(bad)


class Colour(unittest.TestCase):
    def test_srgb_hex_to_linear(self):
        self.assertEqual(co.linear("#FFFFFF"), (1.0, 1.0, 1.0))
        self.assertEqual(co.linear("#000000"), (0.0, 0.0, 0.0))
        r, g, b = co.linear("#808080")          # sRGB 0.502 -> linear ~0.216
        self.assertAlmostEqual(r, 0.2158, places=3)

    def test_bad_hex_is_rejected(self):
        with self.assertRaises(ValueError):
            co.linear("8FD5B9")


class TheCommittedMap(unittest.TestCase):
    def test_colours_json_is_valid_and_has_the_chosen_roles(self):
        m = json.load(open(os.path.join(HERE, "colours.json")))
        co.validate(m)
        self.assertTrue({"frame", "printed", "accent"} <= set(m["roles"]))

    def test_committed_rules_on_real_lite26_labels(self):
        m = co.load()
        frame = "4040-350x350x250 Voron Trident v4 v33 / 4040-350 VT Frame v12 / Horizontals"
        self.assertEqual(co.role_of(m, "2040 (2) (new front)", frame, "Aluminum-6061-T6"), "frame")
        self.assertIsNone(co.role_of(m, "Dock", frame, "Aluminum-6061-T6"))           # milled dock, not extrusion
        self.assertEqual(co.role_of(m, "[a]_Duct-4010-left MadMax dock bosses (remix, CC BY-NC-SA 4.0)",
                                    "Left Toolhead", "ABS-Generic"), "accent")
        self.assertEqual(co.role_of(m, "Camera housing front (Printables 305428, public domain)",
                                    "Enclosure extras (lite-16)", "Default"), "printed")
        self.assertIsNone(co.role_of(m, "Nocturne lens", "Enclosure extras (lite-16)", "Default"))
        self.assertEqual(co.role_of(m, "GT2 9mm belt, lower (Monolith 2WD)", "4040-350x350x250 Voron Trident v4 v33", "Default"), "belt")
        for lab in ("VC9-JLA", "VT9-RRB", "VT9-FIA001"):
            self.assertEqual(co.role_of(m, lab, "4040-350x350x250 Voron Trident v4 v33 / XY left: _XY_left", "Aluminum-6061-T6"), "monolith")
        for lab in ("695 W5 bearing005", "F695 flanged bearing022", "_MR148ZZ Outer Ring (1)", "_MR148ZZ Ball013"):
            self.assertEqual(co.role_of(m, lab, "x", "Steel-Generic"), "bearing", lab)
        self.assertIsNone(co.role_of(m, "D5x36mm pin001", "x", "Steel-Generic"))
        self.assertEqual(co.role_of(m, "backbone-350 v2", "4040-350x350x250 Voron Trident v4 v33", "Steel-Generic"), "backbone")


if __name__ == "__main__":
    unittest.main(verbosity=2)
