# SPDX-License-Identifier: GPL-3.0-or-later
"""fingerprint.py (vt350#324): plain python."""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fingerprint as fp


def index(path, parts):
    json.dump({"parts": parts}, open(path, "w"))


def part(label, x=0.0, material="Aluminum"):
    return {"name": label, "label": label, "material": material,
            "bbox": {"xmin": x, "xmax": x + 10, "ymin": 0.0, "ymax": 1.0, "zmin": 0.0, "zmax": 1.0}}


class Fingerprint(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(); self.addCleanup(self._tmp.cleanup)
        self.d = self._tmp.name
        open(os.path.join(self.d, "tool.py"), "w").write("print(1)\n")
        self.ix = os.path.join(self.d, "m.parts.json")
        index(self.ix, [part("a"), part("b", 20)])
        self.decl = {"files": ["tool.py"], "indexes": [self.ix]}

    def fp(self):
        return fp.fingerprint(self.d, self.decl)[0]

    def test_colour_or_material_only_change_keeps_it(self):
        a = self.fp()
        index(self.ix, [part("b", 20, "Default"), part("a")])     # other order, a field outside GEOMETRY
        self.assertEqual(a, self.fp())

    def test_moved_part_changes_it(self):
        a = self.fp()
        index(self.ix, [part("a", 0.01), part("b", 20)])
        self.assertNotEqual(a, self.fp())

    def test_added_or_renamed_part_changes_it(self):
        a = self.fp()
        index(self.ix, [part("a"), part("b", 20), part("c", 40)])
        self.assertNotEqual(a, self.fp())
        index(self.ix, [part("a"), part("B", 20)])
        self.assertNotEqual(a, self.fp())

    def test_float_noise_ignored(self):
        a = self.fp()
        index(self.ix, [part("a", 1e-7), part("b", 20.0000001)])
        self.assertEqual(a, self.fp())

    def test_code_change_changes_it(self):
        a = self.fp()
        open(os.path.join(self.d, "tool.py"), "w").write("print(2)\n")
        self.assertNotEqual(a, self.fp())

    def test_missing_file_then_present(self):
        self.decl["files"].append("later.log")
        a = self.fp()
        open(os.path.join(self.d, "later.log"), "w").write("x")
        self.assertNotEqual(a, self.fp())

    def test_excluded_files_ignored(self):
        self.decl["files"] = ["*.py"]; self.decl["exclude"] = ["test_*"]
        a = self.fp()
        open(os.path.join(self.d, "test_tool.py"), "w").write("x")
        self.assertEqual(a, self.fp())

    def test_same_parts_in_the_next_models_index(self):
        a = self.fp()
        nxt = os.path.join(self.d, "m2.parts.json")
        index(nxt, [part("a"), part("b", 20)])
        self.decl["indexes"] = [nxt]
        self.assertEqual(a, self.fp())

    def test_fields_can_include_material(self):
        self.decl["fields"] = ["label", "bbox", "material"]
        a = self.fp()
        index(self.ix, [part("a", material="Default"), part("b", 20)])
        self.assertNotEqual(a, self.fp())


class Decide(unittest.TestCase):
    DEPS = {"sweep": [], "z_sweep": [], "print_area": ["sweep", "z_sweep"], "test_print_area": ["print_area"]}

    def test_verdicts(self):
        self.assertEqual(fp.decide("x", None, None, None, set())[0], "run")
        self.assertEqual(fp.decide("x", {"always": "cheap"}, None, "f", set()), ("always", "cheap"))
        self.assertEqual(fp.decide("x", {}, "f", "f", set())[0], "reused")
        self.assertEqual(fp.decide("x", {}, "f", "f", {"x"})[0], "forced")
        self.assertEqual(fp.decide("x", {}, "g", "f", set()), ("run", "inputs changed"))
        self.assertEqual(fp.decide("x", {}, "g", None, set()), ("run", "no earlier run recorded"))

    def test_forced_set(self):
        links = list(self.DEPS)
        self.assertEqual(fp.forced_set(None, links, self.DEPS), set())
        self.assertEqual(fp.forced_set([], links, self.DEPS), set(links))
        self.assertEqual(fp.forced_set(["z_sweep"], links, self.DEPS), {"z_sweep", "print_area", "test_print_area"})
        with self.assertRaises(ValueError):
            fp.forced_set(["nope"], links, self.DEPS)

    def test_records_round_trip(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        p = os.path.join(tmp.name, "logs", "r.json")
        r = fp.Records(p)
        self.assertIsNone(r.get("sweep"))
        r.put("sweep", "abc", "vt350-lite-80", "2026-11-26T00:00:00Z")
        self.assertEqual(fp.Records(p).get("sweep"), "abc")


if __name__ == "__main__":
    unittest.main()
