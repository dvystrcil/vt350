#!/usr/bin/env python3
"""Tests for step_parts.py (vt350#40 AC3). Plain python3: python3 platform/docs/test_step_parts.py"""
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step_parts  # noqa: E402

MANIFEST = ("path,part,qty,stage,bom,source,repo,commit,upstream_path,sha256,license,variant,link,material,notes\n"
            "a/[a]_part one.stl,Part one,2,12,,,o/r,abc,STL/[a]_part one.stl,,GPL-3.0,,,,\n"
            "a/missing.stl,Not committed,1,12,,,o/r,abc,STL/missing.stl,,CC BY-NC-SA 4.0,,,,\n"
            ",Linked only,as-needed,12,,,,,,,CC0-1.0,,https://example.com/x,,\n"
            "a/old.stl,Replaced part,0,12,,,o/r,abc,STL/old.stl,,GPL-3.0,,,,\n"
            "a/v1.stl,Alt one,1,12,,,o/r,abc,STL/v1.stl,,GPL-3.0,rear,,,\n"
            "a/frame.stl,Frame part,1,9,,,o/r,abc,STL/frame.stl,,GPL-3.0,,,,\n")
BOM = ("category,item,qty_needed,qty_owned,vendor,link,unit_price,currency,status,stage,notes\n"
       "per head,Insert | short,3,0,Shop,https://shop.example/i,,USD,ordered,#12,\n"
       "toolchanger,Probe,1,0,Shop,,,USD,to buy,#12,\n"
       "frame,Bar,4,0,,,,,decide,#7,\n")
PAGE = "# Stage 12\n\n## Parts for this step\n\n" + step_parts.BEGIN + "\n" + step_parts.END + "\n\n## Notes\n\nkeep me\n"


class StepPartsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.write("parts/printed/manifest.csv", MANIFEST)
        self.write("parts/printed/a/[a]_part one.stl", "solid")
        self.write("bom/bom.csv", BOM)
        self.page = self.write("docs/assembly/stage-12-heads.md", PAGE)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def read(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def main(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = step_parts.main(["--root", self.root, *args])
        return code, out.getvalue()

    def test_generates_then_check_passes(self):
        code, out = self.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("stale", out)
        self.assertEqual(self.read(self.page), PAGE, "--check must not write")
        code, out = self.main()
        self.assertEqual(code, 0, out)
        self.assertIn("wrote docs/assembly/stage-12-heads.md", out)
        code, out = self.main("--check")
        self.assertEqual(code, 0, out)
        self.assertTrue(out.rstrip().endswith("step-parts: OK"))

    def test_tables(self):
        self.main()
        text = self.read(self.page)
        block = text[text.index(step_parts.BEGIN):text.index(step_parts.END)]
        # committed file: relative link from the page, URL-quoted, brackets escaped in the text
        self.assertIn("[\\[a\\]_part one.stl](../../parts/printed/a/%5Ba%5D_part%20one.stl)", block)
        # not committed: the upstream file at its pinned commit
        self.assertIn("(https://github.com/o/r/blob/abc/STL/missing.stl)", block)
        # no path: the row's link
        self.assertIn("[upstream](https://example.com/x)", block)
        self.assertNotIn("Replaced part", block)          # qty 0
        self.assertIn("Alt one (alternatives `rear`: print one)", block)
        self.assertNotIn("Frame part", block)             # another stage
        # buy: "#12" matched, per head, pipe escaped, vendor linked when there's a link
        self.assertIn("| Insert \\| short | 3 per head | ordered | [Shop](https://shop.example/i) |", block)
        self.assertIn("| Probe | 1 | to buy | Shop |", block)
        self.assertNotIn("Bar", block)
        # the rest of the page is kept
        self.assertTrue(text.startswith("# Stage 12\n\n## Parts for this step\n\n"))
        self.assertTrue(text.endswith(step_parts.END + "\n\n## Notes\n\nkeep me\n"))

    def test_regenerating_is_stable(self):
        self.main()
        first = self.read(self.page)
        self.main()
        self.assertEqual(self.read(self.page), first)

    def test_page_without_markers_fails(self):
        self.write("docs/assembly/stage-12-heads.md", "# Stage 12\n")
        code, out = self.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("no <!-- step-parts:begin -->", out)
        code, out = self.main()
        self.assertEqual(code, 1, "writing must fail too: there's nowhere to put the tables")

    def test_broken_markers_fail(self):
        for text in (step_parts.END + "\n" + step_parts.BEGIN + "\n",
                     step_parts.BEGIN + "\n",
                     (step_parts.BEGIN + "\n" + step_parts.END + "\n") * 2):
            self.write("docs/assembly/stage-12-heads.md", text)
            code, out = self.main("--check")
            self.assertEqual(code, 1, text)
            self.assertIn("needs exactly one", out)

    def test_stage_without_page_is_a_warning(self):
        code, out = self.main()
        self.assertEqual(code, 0, out)
        self.assertIn("warning: stage 9 has parts but no page", out)
        self.assertIn("warning: stage 7 has parts but no page", out)

    def test_page_without_parts_gets_empty_tables(self):
        self.write("docs/assembly/stage-8-wiring.md", step_parts.BEGIN + "\n" + step_parts.END + "\n")
        code, out = self.main()
        self.assertEqual(code, 0, out)
        text = self.read(os.path.join(self.root, "docs/assembly/stage-8-wiring.md"))
        self.assertIn("Nothing to print for this step.", text)
        self.assertIn("Nothing to buy for this step.", text)

    def test_page_without_markers_and_without_parts_is_fine(self):
        self.write("docs/assembly/stage-8-wiring.md", "# Stage 8\n")
        self.main()
        code, out = self.main("--check")
        self.assertEqual(code, 0, out)

    def test_two_pages_for_one_stage_fail(self):
        self.write("docs/assembly/stage-12-other.md", PAGE)
        code, out = self.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("stage 12 has two pages", out)

    def test_both_stage_spellings(self):
        self.assertEqual(step_parts.stage_of("12", "x"), 12)
        self.assertEqual(step_parts.stage_of(" #12 ", "x"), 12)
        self.assertIsNone(step_parts.stage_of("", "x"))
        with self.assertRaises(step_parts.StepPartsError):
            step_parts.stage_of("stage 12", "x")

    def test_bad_stage_fails(self):
        self.write("bom/bom.csv", BOM + "frame,Odd,1,0,,,,,to buy,twelve,\n")
        code, out = self.main("--check")
        self.assertEqual(code, 1)
        self.assertIn("bom/bom.csv line 5: stage 'twelve'", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
