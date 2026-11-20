#!/usr/bin/env python3
"""Tests for platform/parts/orca_projects.py (vt350#217): work units, plates, filament slots, index and --check.

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
import struct
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


def binary_stl(w, d, h=5.0):
    """a binary STL whose bounding box is w x d x h (two triangles are enough for a box)"""
    tris = [((0, 0, 0), (w, 0, 0), (w, d, h)), ((0, 0, 0), (0, d, 0), (w, d, h))]
    out = b"\0" * 80 + struct.pack("<I", len(tris))
    for t in tris:
        out += struct.pack("<3f", 0, 0, 1) + b"".join(struct.pack("<3f", *v) for v in t) + b"\0\0"
    return out


class Fixture(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        for rel, body in {"printed/a/one.stl": "one", "printed/a/two.stl": "two", "printed/b/hinge.stl": "hinge",
                          "slice/orca/process/p.json": "{}",
                          "slice/orca/filament/gf.json": "{}", "slice/orca/filament/petg.json": "{}"}.items():
            self.put(rel, body)
        self.put("slice/orca/orca.json", json.dumps({"vendors": [], "machine": "machine/m.json", "process": "process/p.json"}))
        self.put("slice/orca/machine/m.json", json.dumps({"change_filament_gcode": "MMU_CHANGE"}))
        self.rows = [("a/one.stl", "2", "chamber material (#8 AC1)"), ("a/two.stl", "1", "chamber material (#8 AC1)"),
                     ("b/hinge.stl", "3", "PET-GF (owner)"), ("", "1", "link only"), ("a/old.stl", "0", "chamber material")]
        self.sets = {"manifest": "../printed/manifest.csv", "stl_root": "../printed", "orca": "orca/orca.json",
                     "out": "projects", "bed_mm": [100, 100], "materials": MATERIALS,
                     "units": {"toolhead": "", "door": ""},
                     "parts": {"a/one.stl": "toolhead", "a/two.stl": "toolhead", "b/hinge.stl": "door", "a/old.stl": "toolhead"}}
        self.write()

    def put(self, rel, body):
        p = os.path.join(self.d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb" if isinstance(body, bytes) else "w") as f: f.write(body)

    def write(self):
        lic = getattr(self, "lic", {})
        self.put("printed/manifest.csv", HEAD + "".join(f"{p},x,{q},12,,{lic.get(p, 'GPL-3.0')},{m},\n"
                                                         for p, q, m in self.rows))
        self.put("slice/sets.json", json.dumps(self.sets))

    def cfg(self):
        return op.load_sets(os.path.join(self.d, "slice/sets.json"))

    def plan(self):
        c = self.cfg(); return op.plan(op.load_manifest(c["manifest"]), c)

    def build_index(self):
        """an index as the generator writes it, without Orca"""
        c = self.cfg(); projects, errors = self.plan(); self.assertEqual(errors, [])
        os.makedirs(c["out"], exist_ok=True)
        idx = {"projects": {n: op.index_entry(n, pr, op.preset_shas(c, sorted({f["preset"] for f in pr["filaments"]})),
                                              len(pr["plates"])) for n, pr in projects.items()}}
        for n in projects: open(os.path.join(c["out"], n + ".3mf"), "w").close()
        op.write_index(c["out"], idx)

    def check(self, *extra):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = op.main([os.path.join(self.d, "slice/sets.json"), "--check", *extra])
        return rc, buf.getvalue()

    def mixed_door(self):
        """the door unit gets a chamber-material part too: a second plate"""
        self.put("printed/b/latch.stl", "latch"); self.rows.append(("b/latch.stl", "1", "chamber material"))
        self.sets["parts"]["b/latch.stl"] = "door"; self.write()


class TestUnitsAndPlates(Fixture):
    def test_one_project_per_unit(self):
        projects, errors = self.plan()
        self.assertEqual(errors, [])
        self.assertEqual(list(projects), ["door", "toolhead"])
        th = projects["toolhead"]
        self.assertEqual(len(th["plates"]), 1)
        self.assertEqual([(p["path"], p["qty"]) for p in th["plates"][0]["parts"]], [("a/one.stl", 2), ("a/two.stl", 1)])

    def test_a_plate_per_material_in_materials_order(self):
        self.mixed_door()
        door = self.plan()[0]["door"]
        self.assertEqual([pl["material"] for pl in door["plates"]], ["pet-gf", "chamber-tbd"])
        self.assertEqual(door["filaments"], [{"preset": "filament/gf.json", "label": "PET-GF"},
                                             {"preset": "filament/petg.json", "label": "chamber, TBD"}])
        self.assertEqual([pl["filaments"] for pl in door["plates"]], [[1], [2]])
        self.assertEqual(door["plates"][1]["parts"][0]["filament"], 2)

    def test_own_plate(self):
        self.sets["own_plate"] = ["a/two.stl"]; self.write()
        th = self.plan()[0]["toolhead"]
        self.assertEqual([[p["path"] for p in pl["parts"]] for pl in th["plates"]], [["a/one.stl"], ["a/two.stl"]])

    def test_overflow_spills_onto_more_plates(self):
        # bed 100 x 100, fill 0.6 -> 6000 mm2; each copy (60 + 6) x (40 + 6) = 3036 mm2: one plate holds 1 copy
        self.put("printed/a/one.stl", binary_stl(60, 40)); self.put("printed/a/two.stl", binary_stl(10, 10))
        th = self.plan()[0]["toolhead"]
        self.assertEqual([[(p["path"], p["qty"]) for p in pl["parts"]] for pl in th["plates"]],
                         [[("a/one.stl", 1)], [("a/one.stl", 1), ("a/two.stl", 1)]])

    def test_footprint_of_binary_and_ascii(self):
        self.put("printed/x.stl", binary_stl(12, 7))
        self.assertEqual(tuple(round(v, 3) for v in op.footprint(os.path.join(self.d, "printed/x.stl"))), (12, 7))
        self.put("printed/y.stl", "solid y\n vertex 1 2 3\n vertex 4 8 3\nendsolid")
        self.assertEqual(op.footprint(os.path.join(self.d, "printed/y.stl")), (3, 6))

    def test_material_prefix_first_match(self):
        self.assertEqual(op.material_of("chamber material (#8 AC1)", MATERIALS)["id"], "chamber-tbd")
        self.assertEqual(op.material_of("pet-gf (owner)", MATERIALS)["id"], "pet-gf")
        self.assertIsNone(op.material_of("ASA", MATERIALS))

    def test_unmapped_part_is_an_error(self):
        del self.sets["parts"]["a/two.stl"]; self.write()
        self.assertTrue(any("a/two.stl: no work unit" in e for e in self.plan()[1]))

    def test_unknown_material_and_unit(self):
        self.rows[1] = ("a/two.stl", "1", "ASA"); self.sets["parts"]["b/hinge.stl"] = "nowhere"; self.write()
        errs = " | ".join(self.plan()[1])
        self.assertIn("a/two.stl: material 'ASA' matches no", errs)
        self.assertIn("b/hinge.stl: unknown work unit 'nowhere'", errs)

    def test_as_needed_needs_a_qty(self):
        self.rows[1] = ("a/two.stl", "as-needed", "chamber material"); self.write()
        self.assertTrue(any("isn't a whole number" in e for e in self.plan()[1]))
        self.sets["qty"] = {"a/two.stl": 4}; self.write()
        projects, errors = self.plan()
        self.assertEqual(errors, [])
        self.assertEqual(projects["toolhead"]["plates"][0]["parts"][1]["qty"], 4)

    def test_sets_keys_must_name_manifest_rows(self):
        self.sets["parts"]["gone.stl"] = "door"; self.sets["skip"] = {"gone2.stl": "x"}; self.write()
        errs = " | ".join(self.plan()[1])
        self.assertIn("gone.stl: in the sets file's `parts` but not in the manifest", errs)
        self.assertIn("gone2.stl: in the sets file's `skip` but not in the manifest", errs)

    def test_skip_leaves_a_row_unplaced(self):
        self.sets["skip"] = {"a/two.stl": "the other variant is used"}; self.write()
        projects, errors = self.plan()
        self.assertEqual(errors, [])
        self.assertEqual([p["path"] for p in projects["toolhead"]["plates"][0]["parts"]], ["a/one.stl"])

    def test_missing_stl(self):
        os.remove(os.path.join(self.d, "printed/a/one.stl"))
        self.assertTrue(any("a/one.stl: STL missing" in e for e in self.plan()[1]))

    def test_assemble_list(self):
        c = self.cfg(); al = op.assemble_list(self.plan()[0]["toolhead"], c)
        pl = al["plates"][0]
        self.assertEqual((pl["plate_name"], pl["need_arrange"]), ("chamber, TBD", True))
        o = pl["objects"][0]
        self.assertEqual((o["path"], o["count"], o["filaments"]), (os.path.join(c["stl_root"], "a/one.stl"), 2, [1]))
        self.assertNotIn("assemble_index", o)                    # a shared index would merge the copies

    def test_start_positions_are_each_plates_centre(self):
        self.sets["own_plate"] = ["a/two.stl"]; self.write()
        c = self.cfg(); al = op.assemble_list(self.plan()[0]["toolhead"], c, "/centred")
        o = al["plates"][1]["objects"][0]
        self.assertEqual(op.plate_centre(1, 2, [100, 100]), (170.0, 50.0))   # 2 plates: 2 columns, a fifth apart
        self.assertEqual((o["path"], o["pos_x"], o["pos_y"]), ("/centred/a/two.stl", [170.0], [50.0]))
        self.assertEqual(op.plate_centre(2, 4, [100, 100]), (50.0, -70.0))   # 4 plates: the second row goes -Y

    def test_write_centred(self):
        self.put("printed/x.stl", binary_stl(60, 40, 12))
        src = os.path.join(self.d, "printed/x.stl"); dst = os.path.join(self.d, "c/x.stl")
        op.write_centred(src, dst)
        lo, hi = op.stl_bbox(dst)
        self.assertEqual([round(v, 4) for v in lo + hi], [-30, -20, 0, 30, 20, 12])


class TestSlots(Fixture):
    """a 4-lane MMU: a plate carries its material, then accent / clear slots, at most max_filaments"""
    def mmu(self, **slots):
        self.sets.update(max_filaments=4, slot_filaments={"accent": None, "clear": "filament/petg.json"}, slots=slots)
        self.write()

    def test_accent_and_clear_slots(self):
        self.rows[1] = ("a/two.stl", "1", "PET-GF"); self.sets["parts"]["a/two.stl"] = "door"
        self.mmu(**{"a/two.stl": "clear"})
        self.put("printed/a/acc.stl", "acc"); self.rows.append(("a/acc.stl", "1", "PET-GF"))
        self.sets["parts"]["a/acc.stl"] = "door"; self.sets["slots"]["a/acc.stl"] = "accent"; self.write()
        projects, errors = self.plan()
        self.assertEqual(errors, [])
        d = projects["door"]
        self.assertEqual(d["filaments"], [{"preset": "filament/gf.json", "label": "PET-GF"},
                                          {"preset": "filament/gf.json", "label": "PET-GF, accent"},
                                          {"preset": "filament/petg.json", "label": "clear"}])
        self.assertEqual(d["plates"][0]["filaments"], [1, 2, 3])
        self.assertEqual({p["path"]: p["filament"] for p in d["plates"][0]["parts"]},
                         {"b/hinge.stl": 1, "a/two.stl": 3, "a/acc.stl": 2})

    def test_too_many_filaments_on_a_plate_fails(self):
        self.mmu(**{"a/two.stl": "clear"})
        self.sets["max_filaments"] = 1; self.write()
        self.assertTrue(any("toolhead plate 1: needs 2 filaments (main, clear), the machine takes 1" in e
                            for e in self.plan()[1]))

    def test_the_cap_is_per_plate_not_per_project(self):
        self.mixed_door()                                         # door: PET-GF plate + chamber plate, 1 each
        self.assertEqual(self.plan()[1], [])                      # max_filaments 1 (default) still holds per plate

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
        self.assertIn("a/two.stl: filament [1] -> [2]", out)
        self.assertIn("filaments changed", out)


class TestIndexAndCheck(Fixture):
    def test_index_records_plates_sha_qty_filament(self):
        self.mixed_door(); self.build_index()
        idx = json.load(open(os.path.join(self.d, "slice/projects/index.json")))
        e = idx["projects"]["door"]
        self.assertEqual(e["copies"], 4)
        self.assertEqual(e["plates"][1], {"material": "chamber-tbd", "label": "chamber, TBD", "filaments": [2],
                                          "parts": [{"path": "b/latch.stl", "qty": 1, "filament": 2,
                                                     "sha256": op.sha256(os.path.join(self.d, "printed/b/latch.stl"))}]})
        self.assertEqual(e["licenses"], ["GPL-3.0"])
        self.assertEqual(set(e["presets"]), {"machine", "process", "filament: filament/gf.json", "filament: filament/petg.json"})

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
        self.assertIn("STALE toolhead: a/one.stl: STL changed (sha256)", out)
        self.assertNotIn("STALE door", out)
        self.assertIn("--only toolhead", out)
        self.assertTrue(out.strip().splitlines()[-1].startswith("orca-projects: FAILED"))

    def test_changed_qty(self):
        self.build_index()
        self.rows[2] = ("b/hinge.stl", "4", "PET-GF"); self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door: b/hinge.stl: qty 3 -> 4", out)

    def test_moved_to_another_plate(self):
        self.build_index()
        self.sets["own_plate"] = ["a/two.stl"]; self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("a/two.stl: plates [1] -> [2]", out)

    def test_material_change_moves_plate(self):
        self.build_index()
        self.rows[2] = ("b/hinge.stl", "3", "chamber material"); self.write()     # the hinge's material opens up
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door:", out)
        self.assertIn("filaments changed", out)

    def test_new_row_without_project(self):
        self.build_index()
        self.sets["units"]["jigs"] = ""
        self.put("printed/b/guide.stl", "guide"); self.rows.append(("b/guide.stl", "1", "chamber material"))
        self.sets["parts"]["b/guide.stl"] = "jigs"; self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE jigs: no project yet", out)

    def test_new_row_in_existing_project(self):
        self.build_index()
        self.mixed_door()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door: b/latch.stl: not in the project", out)

    def test_new_row_without_grouping(self):
        self.build_index()
        self.put("printed/b/latch.stl", "latch"); self.rows.append(("b/latch.stl", "1", "chamber material")); self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("ERROR b/latch.stl: no work unit", out)

    def test_removed_part(self):
        self.build_index()
        del self.rows[1]; del self.sets["parts"]["a/two.stl"]; self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE toolhead: a/two.stl: in the project but no longer in this work unit", out)

    def test_removed_unit(self):
        self.build_index()
        self.sets["parts"]["b/hinge.stl"] = "toolhead"; self.write()
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door: work unit no longer exists", out)

    def test_preset_change(self):
        self.mixed_door(); self.build_index()
        self.put("slice/orca/filament/gf.json", '{"nozzle_temperature": ["290"]}')
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door: filament: filament/gf.json preset changed", out)
        self.assertNotIn("STALE toolhead", out)

    def test_missing_3mf(self):
        self.build_index()
        os.remove(os.path.join(self.d, "slice/projects/door.3mf"))
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door: .3mf missing", out)

    def test_no_index_at_all(self):
        rc, out = self.check()
        self.assertEqual(rc, 1)
        self.assertIn("STALE door: no project yet", out)


REUSE = """version = 1

[[annotations]]
path = "**"
SPDX-FileCopyrightText = "me"
SPDX-License-Identifier = "GPL-3.0-or-later"

[[annotations]]
path = "slice/projects/door.3mf"
precedence = "override"
SPDX-FileCopyrightText = "them"
SPDX-License-Identifier = "GPL-3.0-only"

[[annotations]]
path = ["slice/projects/tool*.3mf"]
precedence = "override"
SPDX-FileCopyrightText = ["them", "others"]
SPDX-License-Identifier = "GPL-3.0-only AND CC-BY-NC-SA-4.0"
"""


class TestReuse(Fixture):
    """#278: each project's REUSE label must be its own and name every licence of its parts"""
    def setUp(self):
        super().setUp()
        self.sets["spdx"] = {"GPL-3.0": "GPL-3.0-only", "CC BY-NC-SA 4.0": "CC-BY-NC-SA-4.0"}
        self.lic = {"a/two.stl": "CC BY-NC-SA 4.0"}
        self.write(); self.put("REUSE.toml", REUSE); self.build_index()

    def reuse_check(self):
        return self.check("--reuse", os.path.join(self.d, "REUSE.toml"))

    def test_matching_labels_pass(self):
        rc, out = self.reuse_check()
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.strip().splitlines()[-1], "orca-projects: OK")

    def test_part_moved_into_a_project_whose_label_lacks_its_licence(self):
        self.sets["parts"]["a/two.stl"] = "door"; self.write(); self.build_index()
        rc, out = self.reuse_check()
        self.assertEqual(rc, 1)
        self.assertIn("ERROR REUSE door: REUSE label 'GPL-3.0-only' for slice/projects/door.3mf lacks CC-BY-NC-SA-4.0", out)

    def test_project_renamed_out_of_its_label(self):
        self.sets["units"] = {"heads": "", "door": ""}
        self.sets["parts"] = {k: ("heads" if v == "toolhead" else v) for k, v in self.sets["parts"].items()}
        self.write(); self.build_index()
        rc, out = self.reuse_check()
        self.assertEqual(rc, 1)
        self.assertIn("ERROR REUSE heads: slice/projects/heads.3mf has no REUSE label of its own", out)

    def test_without_reuse_the_label_isnt_checked(self):
        self.sets["parts"]["a/two.stl"] = "door"; self.write(); self.build_index()
        self.assertEqual(self.check()[0], 0)

    def test_spdx_ids(self):
        self.assertEqual(op.spdx_ids("A AND (B OR C WITH D)"), {"A", "B", "C", "D"})


class TestRepo(unittest.TestCase):
    def test_this_repo_is_current(self):
        sets = os.path.join(REPO, "parts", "slice", "sets.json")
        if not os.path.isfile(sets): self.skipTest("no parts/slice/sets.json")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = op.main([sets, "--check", "--reuse", os.path.join(REPO, "REUSE.toml")])
        self.assertEqual(rc, 0, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
