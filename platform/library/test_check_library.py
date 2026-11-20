#!/usr/bin/env python3
"""Tests for platform/library/check_library.py (vt350#268).

Each test builds a small library in a temp dir (removed with addCleanup) and runs the real check on it; the last
ones run it as a subprocess, and on this repository's own cad/library.

Run: python3 platform/library/test_check_library.py
"""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_library.py")
REPO = os.path.dirname(os.path.dirname(HERE))
SCHEMA = os.path.join(REPO, "cad", "library", "schema.json")

spec = importlib.util.spec_from_file_location("check_library", SCRIPT)
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)

DATA = b"ISO-10303-21; a tiny STEP\n"
SHA = hashlib.sha256(DATA).hexdigest()


def entry(**over):
    e = {"category": "electronics", "title": "Widget", "author": "Someone", "source_url": "https://example.com/widget",
         "licence": "CC-BY-SA-4.0", "licence_source": "the page, 2026-11-20", "downloaded": "2026-11-20",
         "redistributable": True, "files": [{"path": "widget.step", "sha256": SHA}]}
    e.update(over)
    return e


class Library(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="test-library-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.lib = os.path.join(self.root, "cad", "library")
        os.makedirs(self.lib)
        shutil.copy(SCHEMA, os.path.join(self.lib, "schema.json"))
        self.write("README.md", b"# library\n")

    def write(self, rel, data):
        path = os.path.join(self.lib, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def add(self, src="electronics/widget/someone", data=DATA, **over):
        self.write(f"{src}/source.json", json.dumps(entry(**over)).encode())
        if data is not None:
            self.write(f"{src}/widget.step", data)

    def probs(self, **kw):
        probs, _ = cl.check(self.lib, **kw)
        return probs

    def assertOneProblem(self, needle, **kw):
        probs = self.probs(**kw)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn(needle, probs[0])

    def test_good_entry_passes(self):
        self.add()
        self.write("electronics/widget/someone/README.md", b"notes\n")
        probs, n = cl.check(self.lib)
        self.assertEqual((probs, n), ([], 1))

    def test_sha256_mismatch_fails(self):
        self.add(data=b"edited after download\n")
        self.assertOneProblem("sha256")

    def test_listed_file_missing_fails(self):
        self.add(data=None)
        self.assertOneProblem("missing")

    def test_file_without_source_json_fails(self):
        self.write("electronics/loose/thing.step", DATA)
        self.assertOneProblem("no source.json covers")

    def test_unlisted_file_beside_source_json_fails(self):
        self.add()
        self.write("electronics/widget/someone/extra.stl", DATA)
        self.assertOneProblem("not listed in source.json")

    def test_stray_file_at_top_fails(self):
        self.write("loose.step", DATA)
        self.assertOneProblem("no source.json covers")

    def test_file_present_when_not_redistributable_fails(self):
        self.add(redistributable=False, licence="LicenseRef-GrabCAD-NC-attribution")
        self.assertOneProblem("isn't redistributable")

    def test_no_file_entry_passes(self):
        self.add(data=None, redistributable=False, licence="LicenseRef-GrabCAD-NC-attribution")
        self.assertEqual(self.probs(), [])

    def test_committed_false_keeps_files_out(self):
        self.add(data=None, committed=False, notes=["large; add if wanted"])
        self.assertEqual(self.probs(), [])
        self.write("electronics/widget/someone/widget.step", DATA)
        self.assertOneProblem("committed: false")

    def test_committed_true_without_redistribution_fails(self):
        self.add(data=None, redistributable=False, committed=True)
        self.assertOneProblem("isn't redistributable")

    def test_schema_missing_field_fails(self):
        e = entry()
        del e["licence"]
        self.write("electronics/widget/someone/source.json", json.dumps(e).encode())
        self.write("electronics/widget/someone/widget.step", DATA)
        self.assertOneProblem("missing required field 'licence'")

    def test_schema_bad_values_fail(self):
        self.add(licence="CC BY-SA 4.0", downloaded="20 Nov 2026", source_url="http://example.com", surprise=1)
        probs = self.probs()
        for needle in (".licence", ".downloaded", ".source_url", "unknown field 'surprise'"):
            self.assertTrue(any(needle in p for p in probs), (needle, probs))

    def test_bad_sha_format_fails(self):
        self.add(files=[{"path": "widget.step", "sha256": "ABC"}])
        self.assertOneProblem("files[0].sha256")

    def test_unreadable_json_fails(self):
        self.write("electronics/widget/someone/source.json", b"{not json")
        self.assertOneProblem("can't read")

    def test_entry_at_wrong_depth_fails(self):
        self.add(src="electronics/widget")
        self.assertOneProblem("entries go in")

    def test_category_must_match_folder(self):
        self.add(src="hotend/widget/someone")
        self.assertOneProblem("but it sits in hotend/")

    def test_unknown_category_fails(self):
        self.add(src="gadgets/widget/someone", category="gadgets")
        self.assertOneProblem(".category")

    def test_variants_side_by_side_with_part_readme(self):
        self.add(src="electronics/widget/someone")
        self.add(src="electronics/widget/official", data=None, committed=False)
        self.write("electronics/widget/README.md", b"the model uses someone's\n")
        probs, n = cl.check(self.lib)
        self.assertEqual((probs, n), ([], 2))

    def test_reuse_label_must_match(self):
        self.add()
        reuse = os.path.join(self.root, "REUSE.toml")
        with open(reuse, "w") as f:
            f.write('version = 1\n[[annotations]]\npath = "**"\nSPDX-License-Identifier = "GPL-3.0-or-later"\n'
                    'SPDX-FileCopyrightText = "us"\n')
        self.assertOneProblem("REUSE.toml says GPL-3.0-or-later", reuse_path=reuse)
        with open(reuse, "a") as f:
            f.write('[[annotations]]\npath = "cad/library/electronics/widget/someone/*.step"\nprecedence = "override"\n'
                    'SPDX-License-Identifier = "CC-BY-SA-4.0"\nSPDX-FileCopyrightText = "Someone"\n')
        self.assertEqual(self.probs(reuse_path=reuse), [])

    def test_credit_must_be_a_project(self):
        self.add(credit="widget")
        projects = os.path.join(self.root, "credits.json")
        with open(projects, "w") as f:
            json.dump({"projects": [{"key": "other"}]}, f)
        self.assertOneProblem("credit 'widget'", projects_path=projects)
        with open(projects, "w") as f:
            json.dump({"projects": [{"key": "widget"}]}, f)
        self.assertEqual(self.probs(projects_path=projects), [])

    def test_cli_exit_codes_and_marker(self):
        self.add()
        ok = subprocess.run([sys.executable, SCRIPT, "--library", self.lib], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertEqual(ok.stdout.strip().splitlines()[-1], "library-check: OK")
        self.write("electronics/widget/someone/extra.stl", DATA)
        bad = subprocess.run([sys.executable, SCRIPT, "--library", self.lib], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertNotIn("library-check: OK", bad.stdout)


class ThisRepo(unittest.TestCase):
    def test_repo_library_passes(self):
        r = subprocess.run([sys.executable, SCRIPT, "--library", "cad/library", "--reuse", "REUSE.toml",
                            "--projects", "cad/credits.json"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "library-check: OK")


if __name__ == "__main__":
    unittest.main(verbosity=2)
