"""Tests for pages.py's licence check inputs (vt350#220 AC3): a selection export is checked on its scene.json's parts,
a whole-model export (the printer: no selection) on the part indexes of its model and every extra file. Stdlib only.

    python3 cad/viewer/test_pages.py
"""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pages


class LicenceInputs(unittest.TestCase):
    def setUp(self):
        for a in ("docs", "run"):
            t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); setattr(self, a, t.name)
        os.makedirs(os.path.join(self.run, "export"))
        pages.DOCS = self.docs
        pages.index_problems = lambda models: []                   # every index fresh, unless a test says otherwise

    def scene(self, **kw):
        json.dump(dict({"model": "vt350-lite-71.FCStd", "extra": ["vt350-ebox-3.FCStd"]}, **kw),
                  open(os.path.join(self.run, "export", "scene.json"), "w"))

    def index(self, model):
        p = os.path.join(self.docs, model[:-6] + ".parts.json"); open(p, "w").write("{}"); return p

    def test_selection_export_uses_its_scene(self):
        self.scene(parts=[{"label": "x", "path": "M"}])
        self.assertEqual(pages.licence_inputs(self.run), [os.path.join(self.run, "export", "scene.json")])

    def test_whole_export_uses_model_and_extra_indexes(self):
        self.scene()
        want = [self.index("vt350-lite-71.FCStd"), self.index("vt350-ebox-3.FCStd")]
        self.assertEqual(pages.licence_inputs(self.run), want)

    def test_whole_export_without_an_index_refuses(self):
        self.scene(); self.index("vt350-lite-71.FCStd")              # the ebox has none
        with self.assertRaises(SystemExit):
            pages.licence_inputs(self.run)

    def test_whole_export_with_a_stale_index_refuses(self):
        self.scene(); self.index("vt350-lite-71.FCStd"); self.index("vt350-ebox-3.FCStd")
        pages.index_problems = lambda models: ["stale    " + models[0]]
        with self.assertRaises(SystemExit):
            pages.licence_inputs(self.run)


class PrinterSelection(unittest.TestCase):
    """cad/viewer/printer.json: the whole printer but the GrabCAD Raspberry Pi 5 model, whose author isn't read yet
    (#252). The rest of the e-box's Electronics group is Voron Trident CAD, GPL-3.0 (2026-11-19)."""

    PI5 = ["Electronics", "Pi Assembly", "RASPBERRY_PI_5_1 v1"]

    def setUp(self):
        sys.path.insert(0, os.path.join(pages.PLATFORM, "viewer")); import rules
        self.sel = rules.load_selection(os.path.join(pages.HERE, "printer.json"))
        self.lic = json.load(open(pages.LICENCES)); self.rules = rules

    def test_pi5_left_out_rest_kept(self):
        self.assertFalse(self.sel.pick("BROADCOM_1", self.PI5)[0])
        for path in (["4040-350x350x250 Voron Trident v4 v33", "Z Assembly (1)"], ["Enclosure extras (lite-16)"],
                     ["E-box layout, concept C on the inner frame (lite-54)"], ["EMU 5-lane (DW-Tas)"],
                     ["Electronics", "SSR"], ["Electronics", "Pi Assembly"], ["Electronics", "Controllers", "Octopus"]):
            self.assertTrue(self.sel.pick("x", path)[0], path)

    def test_pi5_not_shareable(self):
        _, problems = self.rules.check(self.lic, [{"label": "BROADCOM_1", "path": self.PI5}])
        self.assertTrue(problems and problems[0].startswith("NOT SHAREABLE"))

    def test_voron_electronics_cleared(self):
        for label, path in (("Main Relay Body", ["Electronics", "SSR"]),
                            ("Raspberry_Bracket", ["Electronics", "Pi Assembly"]),
                            ("SOLID057", ["Electronics", "Pi Assembly", "DIN Clip (2)"]),
                            ("Octopus Bracket", ["Electronics", "Controllers", "Octopus"])):
            lines, problems = self.rules.check(self.lic, [{"label": label, "path": path}])
            self.assertEqual(problems, [], label)
            self.assertIn("GPL-3.0-only", lines[0])

    def licence(self, label, path):
        lines, problems = self.rules.check(self.lic, [{"label": label, "path": path}])
        self.assertEqual(problems, [], label)
        return lines[0].split()[1]

    def test_z_parts_from_trident_cad_credit_voron(self):
        z = ["4040-350x350x250 Voron Trident v4 v33", "Z Assembly (1)"]
        for label, path in (("Motor_Body", z + ["Z_Motors", "Z_Motor_Left", "NEMA17 Leadscrew 400mm"]),
                            ("10x11 Chain Link003", z + ["10x11 Chain Z"]),
                            ("MGN9H - Carriage_end_cap (1)", z + ["Z_Left", "MGN9H (2)"]),
                            ("SOLID029", z + ["Z_Left", "MGN9 - 400mm (2)"]),
                            ("GE5C001", z + ["Z_Rear", "Z_Bed_Rear"]),
                            ("M3 Locknut", z + ["Z_Left", "Z_Carriage_Left"]),
                            ("M3 Hammerhead T-Nut", z + ["Z_Left", "rail_stop (1)", "Fasteners022"])):
            self.assertEqual(self.licence(label, path), "GPL-3.0-only", label)

    def test_z_parts_not_in_trident_cad_stay_owners(self):
        z = ["4040-350x350x250 Voron Trident v4 v33", "Z Assembly (1)"]
        for label, path in (("COMPOUND", z + ["Z_Left", "Z_Carriage_Left"]),
                            ("M3x8-Screw", z + ["10x11 Chain Z", "Fasteners040"]),
                            ("M3x8-Screw", z + ["Z_Left", "MGN9 - 400mm (2)", "Fasteners021"]),
                            ("Leadscrew (rod)", z + ["Z_Motors", "Z_Motor_Left", "NEMA17 Leadscrew 400mm"])):
            self.assertEqual(self.licence(label, path), "GPL-3.0-or-later", label)

    def test_din_holders_cleared(self):
        lines, problems = self.rules.check(self.lic, [{"label": "DIN rail holder (owner's Neptune DIN_frame_mount), "
                                                       "mains rail, front upright",
                                                       "path": ["E-box layout, concept C on the inner frame (lite-54)"]}])
        self.assertEqual(problems, [])
        self.assertIn("GPL-3.0-only", lines[0])

    def test_page_credits_the_remixes(self):
        credits = pages.settings("printer")["turntable"]["page"]["credits"]
        for who in ("Voron Design", "elliottc", "clee", "DW-Tas", "Monolith3D"):
            self.assertIn(who, credits)

    def test_settings_use_it(self):
        self.assertEqual(pages.settings("printer")["selection"], "cad/viewer/printer.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
