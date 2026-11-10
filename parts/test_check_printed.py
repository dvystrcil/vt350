#!/usr/bin/env python3
"""Tests for parts/check-printed.py (#63 AC6).

Each test builds a small fixture repo in a temp dir and runs the real script
(imported for the unit cases, and as a subprocess for the exit-code case).
The last test runs it on this repository itself.

Run: python3 parts/test_check_printed.py
"""
import csv
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check-printed.py")
REPO = os.path.dirname(HERE)

spec = importlib.util.spec_from_file_location("check_printed", SCRIPT)
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

BOM = """# Printed parts

| Folder / part | Status | Why |
|---|---|---|
| `Z_Assembly/z_widget` | print | |
| `Gantry/thing` | replaced | bought |

| Source | Parts | Qty | Status |
|---|---|---|---|
| [Kit](https://example.com/kit) | clip | 1 | print |
| [Other](https://example.com/other) | thing | — | decide |
"""


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Fixture:
    """A minimal repo: one source folder, two STLs, one link row."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.write("bom/printed-parts.md", BOM)
        self.write("parts/printed/src/LICENSE", "GPL")
        self.write("parts/printed/src/README.md", "readme")
        self.widget = b"solid widget"
        self.write("parts/printed/src/widget.stl", self.widget)
        self.rows = [
            self.row(path="src/widget.stl", part="Widget", qty="2", stage="10",
                     bom="Z_Assembly/z_widget", sha256=sha(self.widget)),
            self.row(path="", part="Clip", qty="as-needed", stage="11", bom="Kit",
                     link="https://example.com/kit/clip.stl"),
        ]
        self.save()

    @staticmethod
    def row(**kw):
        r = {c: "" for c in cp.COLUMNS}
        r.update(source="src", repo="example/src", commit="abc", license="GPL-3.0")
        r.update(kw)
        return r

    def write(self, rel, data):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode())

    def save(self, index=True):
        p = os.path.join(self.root, cp.MANIFEST)
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cp.COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(self.rows)
        if index:
            cp.write_index(self.root)

    def errors(self):
        return cp.check(self.root)


class CheckPrinted(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.tmp.cleanup()

    def assertFails(self, needle):
        errs = self.fx.errors()
        self.assertTrue(any(needle in e for e in errs), f"no error containing {needle!r} in {errs}")

    def test_clean_fixture_passes(self):
        self.assertEqual(self.fx.errors(), [])

    def test_sha256_mismatch_fails(self):
        self.fx.write("parts/printed/src/widget.stl", b"solid widget, edited")
        self.assertFails("sha256 mismatch")

    def test_file_not_in_manifest_fails(self):
        self.fx.write("parts/printed/src/stray.stl", b"x")
        self.assertFails("not in manifest")

    def test_3mf_not_in_manifest_fails(self):
        self.fx.write("parts/printed/src/stray.3mf", b"x")
        self.assertFails("not in manifest")

    def test_source_files_beside_a_part_are_allowed(self):
        self.fx.write("parts/printed/src/widget.step", b"ISO-10303-21;")
        self.assertEqual(self.fx.errors(), [])

    def test_manifest_row_without_file_fails(self):
        os.remove(os.path.join(self.fx.root, "parts/printed/src/widget.stl"))
        self.assertFails("no file")

    def test_bom_print_row_without_part_or_link_fails(self):
        self.fx.rows = [r for r in self.fx.rows if r["bom"] != "Kit"]
        self.fx.save()
        self.assertFails("no part or link")

    def test_bom_non_print_rows_need_nothing(self):
        # "replaced" and "decide" rows have no manifest rows and that's fine
        self.assertEqual(self.fx.errors(), [])

    def test_unknown_bom_key_fails(self):
        self.fx.rows[0]["bom"] = "Z_Assembly/z_wigdet"
        self.fx.save()
        self.assertFails("not a row in bom/printed-parts.md")

    def test_missing_stage_fails(self):
        self.fx.rows[0]["stage"] = ""
        self.fx.save()
        self.assertFails("stage")

    def test_stage_outside_7_to_15_fails(self):
        self.fx.rows[0]["stage"] = "16"
        self.fx.save()
        self.assertFails("stage")

    def test_bad_qty_fails(self):
        self.fx.rows[0]["qty"] = "two"
        self.fx.save()
        self.assertFails("qty")

    def test_row_with_neither_file_nor_link_fails(self):
        self.fx.rows[1]["link"] = ""
        self.fx.save()
        self.assertFails("neither a path nor a link")

    def test_duplicate_path_fails(self):
        self.fx.rows.append(dict(self.fx.rows[0]))
        self.fx.save()
        self.assertFails("duplicate")

    def test_missing_licence_fails(self):
        os.remove(os.path.join(self.fx.root, "parts/printed/src/LICENSE"))
        self.assertFails("LICENSE")

    def test_own_design_needs_no_licence_file(self):
        # the user's own design (this repo, no upstream) is covered by the root LICENSE (vt350#122: GPL-3.0)
        os.remove(os.path.join(self.fx.root, "parts/printed/src/LICENSE"))
        for r in self.fx.rows:
            r.update(repo=cp.THIS_REPO, commit="", upstream_path="", license=cp.REPO_LICENSE)
        self.fx.save()
        self.assertEqual(self.fx.errors(), [])

    def test_third_party_part_under_the_repo_licence_still_needs_its_licence_file(self):
        # the old "MIT needs no LICENSE" rule keyed on the licence string; GPL-3.0 parts from upstream must still ship
        # their own LICENSE even though the repo is GPL now
        os.remove(os.path.join(self.fx.root, "parts/printed/src/LICENSE"))
        self.fx.rows[0]["license"] = cp.REPO_LICENSE
        self.fx.save()
        self.assertEqual(self.fx.errors(), ["parts/printed/manifest.csv:2 (src/widget.stl): no LICENSE in its folder "
                                            "or a parent under parts/printed/"])

    def test_own_design_must_carry_the_repo_licence(self):
        r = self.fx.rows[0]
        r.update(repo=cp.THIS_REPO, commit="", upstream_path="", license="MIT")
        self.fx.save()
        self.assertEqual(self.fx.errors(), ["parts/printed/manifest.csv:2 (src/widget.stl): own design must carry the "
                                            "repo licence GPL-3.0-or-later, not 'MIT'"])

    def test_missing_readme_fails(self):
        os.remove(os.path.join(self.fx.root, "parts/printed/src/README.md"))
        self.assertFails("README")

    def test_in_repo_copy_drifting_from_its_source_fails(self):
        self.fx.write("cad/derived/widget.stl", self.fx.widget)
        self.fx.rows[0].update(repo=cp.THIS_REPO, upstream_path="cad/derived/widget.stl")
        self.fx.save()
        self.assertEqual(self.fx.errors(), [])
        self.fx.write("cad/derived/widget.stl", b"solid widget v2")
        self.assertFails("differs from its source")

    def test_stale_index_fails(self):
        self.fx.rows[0]["qty"] = "3"
        self.fx.save(index=False)
        self.assertFails("index")

    def test_index_lists_every_row_and_a_total(self):
        idx = cp.read(os.path.join(self.fx.root, cp.README))
        self.assertIn("Widget", idx)
        self.assertIn("Clip", idx)
        self.assertIn("src/widget.stl", idx)
        self.assertIn("Full set", idx)

    def test_variant_group_counts_once_in_total(self):
        b = b"solid widget b"
        self.fx.write("parts/printed/src/widget_b.stl", b)
        self.fx.rows[0]["variant"] = "pick one"
        self.fx.rows.append(Fixture.row(path="src/widget_b.stl", part="Widget B", qty="2", stage="10",
                                        bom="Z_Assembly/z_widget", sha256=sha(b), variant="pick one"))
        self.fx.save()
        self.assertEqual(self.fx.errors(), [])
        self.assertEqual(cp.full_set(cp.load_manifest(self.fx.root))["pieces"], 2)

    def test_cli_exit_codes(self):
        ok = subprocess.run([sys.executable, SCRIPT, "--root", self.fx.root], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.fx.write("parts/printed/src/stray.stl", b"x")
        bad = subprocess.run([sys.executable, SCRIPT, "--root", self.fx.root], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("not in manifest", bad.stdout)

    def test_this_repository_passes(self):
        self.assertEqual(cp.check(REPO), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
