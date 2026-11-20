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
    """cad/viewer/printer.json: the whole printer but the GrabCAD electronics (owner, 2026-11-19, #252)."""

    def setUp(self):
        sys.path.insert(0, os.path.join(pages.PLATFORM, "viewer")); import rules
        self.sel = rules.load_selection(os.path.join(pages.HERE, "printer.json"))
        self.lic = json.load(open(pages.LICENCES)); self.rules = rules

    def test_electronics_left_out_rest_kept(self):
        self.assertFalse(self.sel.pick("Main Relay Body", ["Electronics", "SSR"])[0])
        for path in (["4040-350x350x250 Voron Trident v4 v33", "Z Assembly (1)"], ["Enclosure extras (lite-16)"],
                     ["E-box layout, concept C on the inner frame (lite-54)"], ["EMU 5-lane (DW-Tas)"]):
            self.assertTrue(self.sel.pick("x", path)[0], path)

    def test_electronics_not_shareable(self):
        _, problems = self.rules.check(self.lic, [{"label": "Main Relay Body", "path": ["Electronics", "SSR"]}])
        self.assertTrue(problems and problems[0].startswith("NOT SHAREABLE"))

    def test_settings_use_it(self):
        self.assertEqual(pages.settings("printer")["selection"], "cad/viewer/printer.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
