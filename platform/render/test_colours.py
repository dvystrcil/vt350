#!/usr/bin/env python3
"""Tests for platform/render/colours.py (#38). Run: python3 platform/render/test_colours.py"""
import importlib.util
import json
import shutil
import tempfile
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PRINTER_RENDER = os.path.join(ROOT, "cad", "render")      # the VT350's colour map + its own exports (vt350#122)
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
        m = json.load(open(os.path.join(PRINTER_RENDER, "colours.json")))
        co.validate(m)
        self.assertTrue({"frame", "printed", "accent"} <= set(m["roles"]))

    def test_frame_is_the_tentative_ral_6011_render(self):
        # vt350#101 AC1: Fern green render of DLLPDF's in-stock RAL 6011, tentative until the #102 sample arrives
        frame = json.load(open(os.path.join(PRINTER_RENDER, "colours.json")))["roles"]["frame"]
        self.assertEqual(frame["hex"], "#4F7942")
        self.assertIn("TENTATIVE", frame["note"])
        self.assertIn("RAL 6011", frame["note"])
        self.assertIn("issues/102", frame["note"])

    def test_committed_rules_on_real_lite26_labels(self):
        m = co.load()
        frame = "4040-350x350x250 Voron Trident v4 v33 / 4040-350 VT Frame v12 / Horizontals"
        self.assertEqual(co.role_of(m, "2040 (2) (new front)", frame, "Aluminum-6061-T6"), "frame")
        self.assertIsNone(co.role_of(m, "Dock", frame, "Aluminum-6061-T6"))           # milled dock, not extrusion
        self.assertEqual(co.role_of(m, "Dock crossbar (placeholder, 2040)", frame, "Aluminum-6061-T6"), "frame")  # user, 2026-11-08
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

    def test_committed_rules_on_lite27_stand_and_filter(self):
        m = co.load()
        stand = "4040-350x350x250 Voron Trident v4 v33 / Stand: levelling feet + base board (#83, placeholders)"
        self.assertEqual(co.role_of(m, "Base board (18 mm, plywood/MDF, placeholder)", stand, "Default"), "board")
        self.assertEqual(co.role_of(m, "Levelling foot pad 3 (rubber, placeholder D50)", stand, "Default"), "rubber")
        self.assertEqual(co.role_of(m, "Levelling foot 1 T-slot bracket (4040, placeholder)", stand, "Default"), "foot_metal")
        self.assertEqual(co.role_of(m, "Levelling foot 4 M8 stud (placeholder)", stand, "Default"), "foot_metal")
        sm = "StealthMax 300 (nevermore3d a3451c5, GPL-3.0), recessed concept"
        for lab in ("StealthMax M_2.0_Body", "StealthMax M_3.0_Body", "StealthMax M_1a.0_Body_BPM", "StealthMax M_2.1_CarbonBasket"):
            self.assertEqual(co.role_of(m, lab, sm, "Default"), "printed", lab)
        for lab in ("StealthMax 3.3_LidLatch001", "StealthMax M_2.5a_LogoCap", "StealthMax 3.2_LidFrontHinge"):
            self.assertEqual(co.role_of(m, lab, sm, "Default"), "accent", lab)
        self.assertEqual(co.role_of(m, "StealthMax hanger lip, left (remix concept)", sm, "Default"), "accent")
        self.assertEqual(co.role_of(m, "StealthMax cradle half, right (remix concept)", sm, "Default"), "accent")  # lite-29
        self.assertIsNone(co.role_of(m, "StealthMax Acrylic Panel", sm, "Default"))
        self.assertIsNone(co.role_of(m, "StealthMax fan (Delta BFB0712HF)", sm, "Default"))

    def test_drag_chains_are_orange(self):
        """User, 2026-11-08: all drag chains, the Z chain included, in the orange accent; their screws are not."""
        m = co.load()
        z = "4040-350x350x250 Voron Trident v4 v33 / Z Assembly (1) / 10x11 Chain Z"
        for lab in ("10x11 Chain Link", "10x11 Chain Link017", "10x11 Fixed End", "10x11 Unfixed End"):
            self.assertEqual(co.role_of(m, lab, z, "Default"), "accent", lab)
        self.assertIsNone(co.role_of(m, "M3x8-Screw034", z, "Default"))



class Audit(unittest.TestCase):
    """vt350#91: the parts no colour rule matched, grouped by group path and material, with counts. The export
    writes it to out/colour-audit.txt. The fixture is a parts list as export_meshes.py sees each part, because
    scene.json keeps at most 40 labels per bucket and no group per part."""
    FIXTURE = os.path.join(HERE, "fixtures", "colour-audit-parts.json")
    FRAME = "4040-350x350x250 Voron Trident v4 v33 / 4040-350 VT Frame v12 / Horizontals"
    CROSSBAR = "Dock crossbar (placeholder, 2040)"

    def parts(self):
        return [tuple(p) for p in json.load(open(self.FIXTURE))["parts"]]

    def without_the_pr88_rule(self):
        m = co.load()
        frame = [r for r in m["rules"] if r["role"] == "frame"]
        self.assertEqual(len(frame), 1)
        before = frame[0]["label"]
        frame[0]["label"] = before.replace("|^Dock crossbar", "")
        self.assertNotEqual(frame[0]["label"], before, "the vt350#88 crossbar rule is no longer written this way")
        return m

    def listed(self, groups):
        return {lab for g in groups for lab in g["labels"]}

    def test_the_crossbar_is_listed_without_the_pr88_rule(self):
        groups = co.audit(self.without_the_pr88_rule(), self.parts())
        self.assertIn(self.CROSSBAR, self.listed(groups))
        g = next(g for g in groups if self.CROSSBAR in g["labels"])
        self.assertEqual((g["group"], g["material"]), (self.FRAME, "Aluminum-6061-T6"))
        self.assertIn(self.CROSSBAR, co.audit_text(groups, len(self.parts())))

    def test_the_crossbar_is_not_listed_with_it(self):
        groups = co.audit(co.load(), self.parts())
        self.assertNotIn(self.CROSSBAR, self.listed(groups))
        self.assertNotIn(self.CROSSBAR, co.audit_text(groups, len(self.parts())))

    def test_groups_by_group_and_material_with_counts(self):
        groups = co.audit(co.load(), self.parts())
        got = [(g["n"], g["group"], g["material"], g["labels"]) for g in groups]
        chain = "4040-350x350x250 Voron Trident v4 v33 / Z Assembly (1) / 10x11 Chain Z"
        sm = "StealthMax 300 (nevermore3d a3451c5, GPL-3.0), recessed concept"
        self.assertEqual(got, [                       # most parts first, then group, then material
            (2, self.FRAME, "Steel-Generic", {"M5x16": 1, "M5x16001": 1}),     # not Default: the old log missed these
            (2, chain, "Default", {"M3x8-Screw034": 2}),                        # the same label twice (an extra file)
            (2, sm, "Default", {"StealthMax Acrylic Panel": 1, "StealthMax fan (Delta BFB0712HF)": 1}),
            (1, self.FRAME, "Aluminum-6061-T6", {"Dock": 1}),
            (1, "Enclosure extras (lite-16)", "Default", {"Nocturne lens": 1}),
        ])

    def test_text_first_line_is_the_count(self):
        text = co.audit_text(co.audit(co.load(), self.parts()), len(self.parts()))
        lines = text.splitlines()
        self.assertEqual(lines[0], "unmatched: 8 of 12 parts, in 5 group/material sets")
        self.assertIn("  2  Steel-Generic  " + self.FRAME, lines)
        self.assertIn("       M3x8-Screw034  x2", lines)
        self.assertTrue(text.endswith("\n"))

    def test_a_part_in_no_group(self):
        text = co.audit_text(co.audit(co.load(), [("loose", "", "Default")]), 1)
        self.assertIn("  1  Default  (no group)", text.splitlines())

    def test_nothing_unmatched(self):
        self.assertEqual(co.audit_text([], 3), "unmatched: 0 of 3 parts\n")

    def test_colour_map_off(self):
        self.assertEqual(co.audit_text(None, 3), "unmatched: n/a (colour map off: every part keeps the model's colour)\n")

    def test_export_writes_the_audit_from_every_part(self):
        # the export's own grouping is colours.audit over every part it gave the map, not a dict of Default ones
        src = open(os.path.join(HERE, "export_meshes.py")).read()
        self.assertIn("colours.audit(CMAP, ", src)
        self.assertIn('"colour-audit.txt"', src)
        self.assertNotIn("uncoloured", src)


class MapFile(unittest.TestCase):
    """Which colours.json load() reads by default (vt350#122): the map is the printer's data, the code is generic.
    $VT350_COLOURS, else one beside colours.py (a gpu-batch pod stages everything flat), else the checkout's
    cad/render/colours.json."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="colours-test-"); self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = os.environ.pop("VT350_COLOURS", None)
        self.addCleanup(lambda: self.env is None or os.environ.__setitem__("VT350_COLOURS", self.env))
        self.addCleanup(os.environ.pop, "VT350_COLOURS", None)

    def test_the_checkout_map_by_default(self):
        self.assertEqual(co.map_file(), os.path.join(PRINTER_RENDER, "colours.json"))
        self.assertEqual(co.MAP_FILE, co.map_file())

    def test_a_map_beside_the_code_wins_over_the_checkout(self):
        open(os.path.join(self.tmp, "colours.json"), "w").write("{}")
        self.assertEqual(co.map_file(here=self.tmp, root=ROOT), os.path.join(self.tmp, "colours.json"))

    def test_the_environment_wins_over_both(self):
        open(os.path.join(self.tmp, "colours.json"), "w").write("{}")
        os.environ["VT350_COLOURS"] = "/some/where/map.json"
        self.assertEqual(co.map_file(here=self.tmp, root=ROOT), "/some/where/map.json")

    def test_none_is_not_a_path(self):
        os.environ["VT350_COLOURS"] = "none"           # export_meshes.py's "model's own colours" switch
        self.assertEqual(co.map_file(), os.path.join(PRINTER_RENDER, "colours.json"))

    def test_no_map_anywhere_names_where_it_looked(self):
        with self.assertRaisesRegex(FileNotFoundError, "colours.json not found: .*" + self.tmp):
            co.map_file(here=self.tmp, root=self.tmp)


class Portable(unittest.TestCase):
    """The render scripts run in the gpu-batch pods (homelab#1961 AC5) as well as
    on this laptop: they find colours.py next to themselves, never at a home path."""
    def test_scripts_import_colours_from_their_own_dir(self):
        for name in ("export_meshes.py", "render.py"):
            src = open(os.path.join(HERE, name)).read()
            self.assertNotIn("/home/dan/Code", src.split("import colours")[0], name)
            self.assertIn("sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))", src, name)

class Aligned(unittest.TestCase):
    """Every view of the printer looks the same (user, 2026-11-09): each export colours parts from the ONE colour map
    (colours.role_of) and the ONE logo split (logos.split), never its own copy. A diagnostic view that colours by a
    different scheme on purpose is listed in DIAGNOSTIC. A new export_*.py on neither list fails here, so it can't
    drift unnoticed."""
    SHARED = {"export_meshes.py", "export_exploded.py"}
    DIAGNOSTIC = {"export_pose.py": "colours by sweep role (head, plate, clash volumes), not the printer's look"}

    def exports(self):
        return sorted(f for d in (HERE, PRINTER_RENDER) for f in os.listdir(d) if f.startswith("export_") and f.endswith(".py"))

    def src(self, f):
        return open(next(p for p in (os.path.join(d, f) for d in (HERE, PRINTER_RENDER)) if os.path.exists(p))).read()

    def test_every_export_is_classified(self):
        for f in self.exports():
            self.assertIn(f, self.SHARED | set(self.DIAGNOSTIC), f"{f}: add it to SHARED (uses colours + logos) "
                          "or DIAGNOSTIC (with the reason) in test_colours.Aligned")

    def test_shared_exports_use_the_colour_map_and_the_logo_split(self):
        for f in self.SHARED:
            src = self.src(f)
            for call in ("import colours", "import logos", "colours.role_of(", "logos.split("):
                self.assertIn(call, src, f"{f} must use {call}")

    def test_no_export_keeps_its_own_logo_table(self):
        for f in self.exports():
            src = self.src(f)
            self.assertNotIn("LidFrontHinge", src, f"{f}: logo parts belong in logos.LOGOS")
            self.assertNotIn("LogoCap", src, f"{f}: logo parts belong in logos.LOGOS")

    def test_lists_name_real_files(self):
        for f in self.SHARED | set(self.DIAGNOSTIC):
            self.assertTrue(any(os.path.exists(os.path.join(d, f)) for d in (HERE, PRINTER_RENDER)), f)

if __name__ == "__main__":
    unittest.main(verbosity=2)
