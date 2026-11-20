#!/usr/bin/env python3
"""Tests for platform/parts/orca_projects.py (vt350#217): grouping, index and the staleness check.

None of these need OrcaSlicer: each test builds a small fixture (manifest, sets file, STLs, presets) in a temp dir
and runs the plan / index / --check logic. The last test runs --check on this repository itself.

Run: python3 platform/parts/test_orca_projects.py
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("orca_projects", os.path.join(HERE, "orca_projects.py"))
op = importlib.util.module_from_spec(spec)
spec.loader.exec_module(op)

HEAD = "path,part,qty,stage,sha256,license,material,notes\n"
MATERIALS = [
    {"match": "PET-GF", "id": "pet-gf", "label": "PET-GF", "filament": "filament/gf.json"},
    {"match": "chamber material", "id": "chamber-tbd", "label": "chamber, TBD", "filament": "filament/petg.json"},
]


class Fixture(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        for rel, body in {"printed/a/one.stl": "one", "printed/a/two.stl": "two", "printed/b/hinge.stl": "hinge",
                          "slice/orca/machine/m.json": "{}", "slice/orca/process/p.json": "{}",
                          "slice/orca/filament/gf.json": "{}", "slice/orca/filament/petg.json": "{}"}.items():
            self.put(rel, body)
        self.put("slice/orca/orca.json", json.dumps({"vendors": [], "machine": "machine/m.json", "process": "process/p.json"}))
        self.put("slice/orca/machine/m.json", json.dumps({"change_filament_gcode": "MMU_CHANGE"}))
        self.rows = [("a/one.stl", "2", "chamber material (#8 AC1)"), ("a/two.stl", "1", "chamber material (#8 AC1)"),
                     ("b/hinge.stl", "3", "PET-GF (owner)"), ("", "1", "link only"), ("a/old.stl", "0", "chamber material")]
        self.sets = {"manifest": "../printed/manifest.csv", "stl_root": "../printed", "orca": "orca/orca.json",
                     "out": "projects", "materials": MATERIALS,
                     "subassemblies": {"toolhead": "", "door": ""},
                     "parts": {"a/one.stl": "toolhead", "a/two.stl": "toolhead", "b/hinge.stl": "door", "a/old.stl": "toolhead"},
                     "qty": {}}
        self.write()

    def put(self, rel, body):
        p = os.path.join(self.d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f: f.write(body)

    def write(self):
        self.put("printed/manifest.csv", HEAD + "".join(f"{p},x,{q},12,,GPL-3.0,{m},\n" for p, q, m in self.rows))
        self.put("slice/sets.json", json.dumps(self.sets))

    def cfg(self):
        return op.load_sets(os.path.join(self.d, "slice/sets.json"))

    def plan(self):
        c = self.cfg(); return op.plan(op.load_manifest(c["manifest"]), c)

    def build_index(self):
        """an index as the generator writes it, without Orca"""
        c = self.cfg(); sets, errors = self.plan(); self.assertEqual(errors, [])
        os.makedirs(c["out"], exist_ok=True)
        idx = {"projects": {n: op.index_entry(n, s, op.preset_shas(c, s["filaments"]), 1) for n, s in sets.items()}}
        for n in sets: open(os.path.join(c["out"], n + ".3mf"), "w").close()
        op.write_index(c["out"], idx)

    def check(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = op.main([os.path.join(self.d, "slice/sets.json"), "--check"])
        return rc, buf.getvalue()


class TestGrouping(Fixture):
    def test_sets_by_subassembly_and_material(self):
        sets, errors = self.plan()
        self.assertEqual(errors, [])
        self.assertEqual(list(sets), ["door-pet-gf", "toolhead-chamber-tbd"])
        self.assertEqual([(p["path"], p["qty"]) for p in sets["toolhead-chamber-tbd"]["parts"]],
                         [("a/one.stl", 2), ("a/two.stl", 1)])
        self.assertEqual(sets["door-pet-gf"]["filament"], "filament/gf.json")

    def test_material_prefix_first_match(self):
        self.assertEqual(op.material_of("chamber material (#8 AC1)", MATERIALS)["id"], "chamber-tbd")
        self.assertEqual(op.material_of("pet-gf (owner)", MATERIALS)["id"], "pet-gf")
        self.assertIsNone(op.material_of("ASA", MATERIALS))

    def test_unmapped_part_is_an_error(self):
        del self.sets["parts"]["a/two.stl"]; self.write()
        self.assertTrue(any("a/two.stl: no subassembly" in e for e in self.plan()[1]))

    def test_unknown_material_and_subassembly(self):
        self.rows[1] = ("a/two.stl", "1", "ASA"); self.sets["parts"]["b/hinge.stl"] = "nowhere"; self.write()
        errs = " | ".join(self.plan()[1])
        self.assertIn("a/two.stl: material 'ASA' matches no", errs)
        self.assertIn("b/hinge.stl: unknown subassembly 'nowhere'", errs)

    def test_as_needed_needs_a_qty(self):
        self.rows[1] = ("a/two.stl", "as-needed", "chamber material"); self.write()
        self.assertTrue(any("isn't a whole number" in e for e in self.plan()[1]))
        self.sets["qty"]["a/two.stl"] = 4; self.write()
        sets, errors = self.plan()
        self.assertEqual(errors, [])
        self.assertEqual(sets["toolhead-chamber-tbd"]["parts"][1]["qty"], 4)

    def test_sets_entry_without_manifest_row(self):
        self.sets["parts"]["gone.stl"] = "door"; self.write()
        self.assertTrue(any("gone.stl: in the sets file's `parts` but not in the manifest" in e for e in self.plan()[1]))

    def test_missing_stl(self):
        os.remove(os.path.join(self.d, "printed/a/one.stl"))
        self.assertTrue(any("a/one.stl: STL missing" in e for e in self.plan()[1]))


class TestSlots(Fixture):
    """a 4-lane MMU: a project carries its material, then accent / clear slots, at most max_filaments"""
    def mmu(self, **slots):
        self.sets.update(max_filaments=4, slot_filaments={"accent": None, "clear": "filament/petg.json"}, slots=slots)
        self.write()

    def test_one_filament_without_slots(self):
        sets, _ = self.plan()
        self.assertEqual(sets["door-pet-gf"]["filaments"], ["filament/gf.json"])
        self.assertEqual([p["filament"] for p in sets["door-pet-gf"]["parts"]], [1])

    def test_accent_and_clear_slots(self):
        self.rows[1] = ("a/two.stl", "1", "PET-GF"); self.sets["parts"]["a/two.stl"] = "door"
        self.mmu(**{"a/two.stl": "clear"})
        self.put("printed/a/acc.stl", "acc"); self.rows.append(("a/acc.stl", "1", "PET-GF"))
        self.sets["parts"]["a/acc.stl"] = "door"; self.sets["slots"]["a/acc.stl"] = "accent"; self.write()
        sets, errors = self.plan()
        self.assertEqual(errors, [])
        d = sets["door-pet-gf"]
        self.assertEqual(d["slots"], ["main", "accent", "clear"])
        self.assertEqual(d["filaments"], ["filament/gf.json", "filament/gf.json", "filament/petg.json"])
        self.assertEqual({p["path"]: p["filament"] for p in d["parts"]}, {"b/hinge.stl": 1, "a/two.stl": 3, "a/acc.stl": 2})

    def test_too_many_filaments_fails(self):
        self.mmu(**{"a/two.stl": "clear"})
        self.sets["max_filaments"] = 1; self.write()
        self.assertTrue(any("toolhead-chamber-tbd: needs 2 filaments (main, clear), the machine takes 1" in e
                            for e in self.plan()[1]))

    def test_unknown_slot_is_an_error(self):
        self.sets["slots"] = {"a/two.stl": "glow"}; self.write()
        with self.assertRaises(ValueError): self.cfg()

    def test_several_filaments_need_an_mmu_machine(self):
        self.mmu(**{"a/two.stl": "clear"})
        self.build_index()
        self.put("slice/orca/machine/m.json", "{}")
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("no change_filament_gcode", out)

    def test_slot_change_is_stale(self):
        self.build_index()
        self.mmu(**{"a/two.stl": "clear"})
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("a/two.stl: filament slot 1 -> 2", out)
        self.assertIn("filaments changed", out)

    def test_skip_leaves_a_row_unplaced(self):
        self.sets["skip"] = {"a/two.stl": "the other variant is used"}; self.write()
        sets, errors = self.plan()
        self.assertEqual(errors, [])
        self.assertEqual([p["path"] for p in sets["toolhead-chamber-tbd"]["parts"]], ["a/one.stl"])

    def test_sets_keys_must_name_manifest_rows(self):
        self.sets["skip"] = {"gone.stl": "x"}; self.write()
        self.assertTrue(any("gone.stl: in the sets file's `skip` but not in the manifest" in e for e in self.plan()[1]))


class TestIndexAndCheck(Fixture):
    def test_index_records_sha_and_qty(self):
        self.build_index()
        idx = json.load(open(os.path.join(self.d, "slice/projects/index.json")))
        e = idx["projects"]["toolhead-chamber-tbd"]
        self.assertEqual(e["copies"], 3)
        self.assertEqual(e["parts"][0], {"path": "a/one.stl", "qty": 2, "filament": 1,
                                         "sha256": op.sha256(os.path.join(self.d, "printed/a/one.stl"))})
        self.assertEqual(e["licenses"], ["GPL-3.0"])
        self.assertEqual(set(e["presets"]), {"machine", "process", "filament: filament/petg.json"})

    def test_check_ok(self):
        self.build_index()
        rc, out = self.check()
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.strip().splitlines()[-1], "orca-projects: OK")

    def test_changed_stl_names_its_project(self):
        self.build_index()
        self.put("printed/a/one.stl", "one, deeper pocket")
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE toolhead-chamber-tbd: a/one.stl: STL changed (sha256)", out)
        self.assertNotIn("STALE door-pet-gf", out)
        self.assertIn("--only toolhead-chamber-tbd", out)
        self.assertTrue(out.strip().splitlines()[-1].startswith("orca-projects: FAILED"))

    def test_changed_qty(self):
        self.build_index()
        self.rows[2] = ("b/hinge.stl", "4", "PET-GF"); self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door-pet-gf: b/hinge.stl: qty 3 -> 4", out)

    def test_new_row_without_project(self):
        self.build_index()
        self.put("printed/b/latch.stl", "latch")
        self.rows.append(("b/latch.stl", "1", "chamber material")); self.sets["parts"]["b/latch.stl"] = "door"; self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door-chamber-tbd: no project yet", out)

    def test_new_row_without_grouping(self):
        self.build_index()
        self.put("printed/b/latch.stl", "latch"); self.rows.append(("b/latch.stl", "1", "chamber material")); self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("ERROR b/latch.stl: no subassembly", out)

    def test_removed_part(self):
        self.build_index()
        del self.rows[1]; del self.sets["parts"]["a/two.stl"]; self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE toolhead-chamber-tbd: a/two.stl: in the project but no longer in this set", out)

    def test_moved_part_and_removed_set(self):
        self.build_index()
        self.rows[2] = ("b/hinge.stl", "3", "chamber material"); self.write()     # hinge's material opens up
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door-chamber-tbd: no project yet", out)
        self.assertIn("STALE door-pet-gf: set no longer exists", out)

    def test_preset_change(self):
        self.build_index()
        self.put("slice/orca/filament/gf.json", '{"nozzle_temperature": ["290"]}')
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door-pet-gf: filament: filament/gf.json preset changed", out)
        self.assertNotIn("STALE toolhead", out)

    def test_missing_3mf(self):
        self.build_index()
        os.remove(os.path.join(self.d, "slice/projects/door-pet-gf.3mf"))
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door-pet-gf: .3mf missing", out)

    def test_no_index_at_all(self):
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door-pet-gf: no project yet", out)


class TestRepo(unittest.TestCase):
    def test_this_repo_is_current(self):
        sets = os.path.join(REPO, "parts", "slice", "sets.json")
        if not os.path.isfile(sets): self.skipTest("no parts/slice/sets.json")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = op.main([sets, "--check"])
        self.assertEqual(rc, 0, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
