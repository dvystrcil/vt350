# Unit tests for part_index.py's plain-python3 side (#90): sidecar name, schema, staleness and the --check CLI. No
# FreeCAD, so they run in CI:   python3 cad/scripts/test_part_index.py      # "Ran N tests" + "OK"
# The FreeCAD side (the boxes against FreeCAD's own, on a fixture document) is in test_part_index_fc.py.
import copy, hashlib, io, json, os, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import part_index


def a_part(**kw):
    p = {"name": "Box", "label": "a box", "path": ["root", "grp"], "material": "Default", "consumed": False,
         "bbox": {"xmin": 0.0, "ymin": 0.0, "zmin": -80.0, "xmax": 10.0, "ymax": 10.0, "zmax": -60.5}}
    p.update(kw); return p


def an_index(model, parts=None, mode="headless"):
    return {"format": part_index.FORMAT, "model": os.path.basename(model), "source": part_index.fingerprint(model),
            "bbox": {"method": part_index.METHOD, "mode": mode, "freecad": "26.3.0"},
            "generated": "2026-11-09T00:00:00Z", "seconds": 1.5, "parts": [a_part()] if parts is None else parts}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="part-index-test-")
        self.model = os.path.join(self.tmp, "vt350-x-1.FCStd")
        open(self.model, "wb").write(b"not really a FreeCAD file" * 100)


class Names(Base):
    def test_sidecar_replaces_the_fcstd_suffix(self):
        self.assertEqual(part_index.sidecar("/d/vt350-lite-29.FCStd"), "/d/vt350-lite-29.parts.json")

    def test_sidecar_keeps_other_suffixes_whole(self):
        self.assertEqual(part_index.sidecar("/d/odd.step"), "/d/odd.step.parts.json")


class Fingerprint(Base):
    def test_size_sha256_and_utc_mtime(self):
        fp = part_index.fingerprint(self.model)
        data = open(self.model, "rb").read()
        self.assertEqual(fp["size"], len(data))
        self.assertEqual(fp["sha256"], hashlib.sha256(data).hexdigest())
        self.assertRegex(fp["mtime"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


class Validate(Base):
    def test_a_good_index_has_no_problems(self):
        self.assertEqual(part_index.validate(an_index(self.model)), [])

    def test_an_empty_parts_list_is_valid(self):
        self.assertEqual(part_index.validate(an_index(self.model, parts=[])), [])

    def test_wrong_format_is_reported(self):
        i = an_index(self.model); i["format"] = "vt350-part-index/0"
        self.assertTrue(any("format" in p for p in part_index.validate(i)))

    def test_each_missing_top_level_key_is_reported(self):
        for k in ("format", "model", "source", "bbox", "generated", "seconds", "parts"):
            i = an_index(self.model); del i[k]
            self.assertTrue(any(k in p for p in part_index.validate(i)), k)

    def test_mode_must_be_gui_or_headless(self):
        for m in ("gui", "headless"):
            self.assertEqual(part_index.validate(an_index(self.model, mode=m)), [], m)
        for m in ("GUI", "", None, "mixed"):
            self.assertTrue(any("mode" in p for p in part_index.validate(an_index(self.model, mode=m))), m)

    def test_method_must_be_the_optimal_box(self):
        i = an_index(self.model); i["bbox"]["method"] = "BoundBox"
        self.assertTrue(any("method" in p for p in part_index.validate(i)))

    def test_source_needs_size_mtime_sha256(self):
        for k in ("size", "mtime", "sha256"):
            i = an_index(self.model); del i["source"][k]
            self.assertTrue(any(k in p for p in part_index.validate(i)), k)

    def test_each_part_key_is_required(self):
        for k in ("name", "label", "path", "material", "consumed", "bbox"):
            p = a_part(); del p[k]
            self.assertTrue(any(k in x for x in part_index.validate(an_index(self.model, parts=[p]))), k)

    def test_part_types(self):
        for bad in (a_part(path="root / grp"), a_part(consumed="no"), a_part(label=3), a_part(material=None),
                    a_part(path=["root", 3])):
            self.assertNotEqual(part_index.validate(an_index(self.model, parts=[bad])), [], bad)

    def test_bbox_needs_six_numbers_min_le_max(self):
        p = a_part(); del p["bbox"]["zmax"]
        self.assertNotEqual(part_index.validate(an_index(self.model, parts=[p])), [])
        p = a_part(); p["bbox"]["xmin"] = "0"
        self.assertNotEqual(part_index.validate(an_index(self.model, parts=[p])), [])
        p = a_part(); p["bbox"]["xmin"] = True
        self.assertNotEqual(part_index.validate(an_index(self.model, parts=[p])), [])
        p = a_part(); p["bbox"]["ymin"], p["bbox"]["ymax"] = 5.0, 4.0
        self.assertTrue(any("ymin" in x for x in part_index.validate(an_index(self.model, parts=[p]))))
        p = a_part(); p["bbox"]["zmin"] = p["bbox"]["zmax"]                       # a flat box is fine
        self.assertEqual(part_index.validate(an_index(self.model, parts=[p])), [])

    def test_duplicate_names_are_reported(self):
        i = an_index(self.model, parts=[a_part(), a_part(label="other")])
        self.assertTrue(any("Box" in p for p in part_index.validate(i)))

    def test_not_a_dict(self):
        self.assertNotEqual(part_index.validate([]), [])


class WriteAndRead(Base):
    def test_write_then_load_round_trips(self):
        i = an_index(self.model); path = part_index.sidecar(self.model)
        part_index.write(i, path)
        self.assertEqual(part_index.load(path), i)

    def test_write_refuses_an_invalid_index_and_leaves_the_old_file(self):
        path = part_index.sidecar(self.model)
        part_index.write(an_index(self.model), path); before = open(path).read()
        bad = an_index(self.model); bad["bbox"]["mode"] = "mixed"
        with self.assertRaises(ValueError): part_index.write(bad, path)
        self.assertEqual(open(path).read(), before)
        self.assertEqual([f for f in os.listdir(self.tmp) if f.endswith(".tmp")], [])

    def test_write_never_touches_the_model(self):
        before = open(self.model, "rb").read(), os.stat(self.model).st_mtime_ns
        part_index.write(an_index(self.model), part_index.sidecar(self.model))
        self.assertEqual((open(self.model, "rb").read(), os.stat(self.model).st_mtime_ns), before)

    def test_a_failed_write_leaves_no_tmp_file(self):
        path = os.path.join(self.tmp, "a-dir.parts.json"); os.mkdir(path)          # os.replace onto a folder fails
        with self.assertRaises(OSError): part_index.write(an_index(self.model), path)
        self.assertFalse(os.path.exists(path + ".tmp"))

    def test_load_of_a_missing_or_broken_file_is_none(self):
        self.assertIsNone(part_index.load(os.path.join(self.tmp, "nope.parts.json")))
        bad = os.path.join(self.tmp, "bad.parts.json"); open(bad, "w").write("{not json")
        self.assertIsNone(part_index.load(bad))


class Status(Base):
    def test_missing(self):
        self.assertEqual(part_index.status(self.model), "missing")
        self.assertFalse(part_index.is_fresh(self.model))

    def test_fresh_after_writing(self):
        part_index.write(an_index(self.model), part_index.sidecar(self.model))
        self.assertEqual(part_index.status(self.model), "fresh")
        self.assertTrue(part_index.is_fresh(self.model))

    def test_stale_when_the_model_changes_even_at_the_same_size(self):
        part_index.write(an_index(self.model), part_index.sidecar(self.model))
        data = bytearray(open(self.model, "rb").read()); data[0] ^= 1
        open(self.model, "wb").write(bytes(data))
        self.assertEqual(part_index.status(self.model), "stale")

    def test_stale_when_the_size_changes(self):
        part_index.write(an_index(self.model), part_index.sidecar(self.model))
        open(self.model, "ab").write(b"x")
        self.assertEqual(part_index.status(self.model), "stale")

    def test_a_copy_with_a_new_mtime_is_still_fresh(self):
        part_index.write(an_index(self.model), part_index.sidecar(self.model))
        os.utime(self.model, (1, 1))
        self.assertEqual(part_index.status(self.model), "fresh")

    def test_invalid_when_the_sidecar_is_broken_or_off_schema(self):
        open(part_index.sidecar(self.model), "w").write("{not json")
        self.assertEqual(part_index.status(self.model), "invalid")
        i = an_index(self.model); i["format"] = "something else"
        json.dump(i, open(part_index.sidecar(self.model), "w"))
        self.assertEqual(part_index.status(self.model), "invalid")

    def test_index_of_another_model_is_stale(self):
        other = os.path.join(self.tmp, "other.FCStd"); open(other, "wb").write(b"other")
        part_index.write(an_index(other), part_index.sidecar(self.model))
        self.assertEqual(part_index.status(self.model), "stale")


class Cli(Base):
    def run_cli(self, *args):
        r = subprocess.run([sys.executable, os.path.join(HERE, "part_index.py"), *args], capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    def test_check_fresh_exits_0(self):
        part_index.write(an_index(self.model), part_index.sidecar(self.model))
        rc, out, _ = self.run_cli("--check", self.model)
        self.assertEqual(rc, 0); self.assertIn(f"fresh    {self.model}", out)

    def test_check_any_not_fresh_exits_1_and_lists_each(self):
        part_index.write(an_index(self.model), part_index.sidecar(self.model))
        other = os.path.join(self.tmp, "other.FCStd"); open(other, "wb").write(b"other")
        rc, out, _ = self.run_cli("--check", self.model, other)
        self.assertEqual(rc, 1)
        self.assertIn(f"fresh    {self.model}", out); self.assertIn(f"missing  {other}", out)

    def test_check_of_a_missing_model_exits_2(self):
        rc, _, err = self.run_cli("--check", os.path.join(self.tmp, "nope.FCStd"))
        self.assertEqual(rc, 2); self.assertIn("no such model", err)

    def test_no_arguments_prints_usage_and_exits_2(self):
        rc, _, err = self.run_cli()
        self.assertEqual(rc, 2); self.assertIn("usage", err.lower())

    def test_check_with_no_models_or_another_verb_exits_2(self):
        for args in (["--check"], ["--write", self.model], [self.model]):
            rc, _, err = self.run_cli(*args)
            self.assertEqual(rc, 2, args); self.assertIn("usage", err.lower(), args)

    def test_importing_does_not_need_freecad(self):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import part_index; "
                            "print('FreeCAD' in sys.modules)" % HERE], capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "False", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
