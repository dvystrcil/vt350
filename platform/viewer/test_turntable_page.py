# Tests for turntable_page.py (no network: --upload 0).   python3 platform/viewer/test_turntable_page.py
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pages"))
import turntable_page as tp
import check_index

CFG = {"title": "VT350 ·", "title_accent": "test head", "model": "lite-1", "prefix": "m", "elevations": [-10, 25],
       "azimuths": 4, "start_elevation": 25, "credits": "Parts: CC0.", "links": [{"href": "index.html", "text": "All"}],
       "page_title": "Test Turntable", "blurb": "A test.", "issue": "x#1"}
INDEX = ('<!doctype html><html><meta charset="utf-8"><title>Index</title>\n<main>\n  <ul class="pages">\n'
         '  </ul>\n</main>\n')


class TurntablePage(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); d = self.t.name
        self.run = os.path.join(d, "run"); self.frames = os.path.join(self.run, "out"); os.makedirs(self.frames)
        for f in tp.frame_names(CFG): open(os.path.join(self.frames, f), "wb").write(f.encode())
        self.cfgp = os.path.join(d, "page.json"); json.dump(CFG, open(self.cfgp, "w"))
        self.pages = os.path.join(d, "pages"); os.makedirs(self.pages)
        open(os.path.join(self.pages, "index.html"), "w").write(INDEX)

    def tearDown(self): self.t.cleanup()

    def test_frame_names_match_frame_view(self):
        names = tp.frame_names(CFG)
        self.assertEqual(len(names), 8)
        self.assertIn("m-tt-e-10-a090.jpg", names); self.assertIn("m-tt-e25-a270.jpg", names)

    def test_missing_frame_writes_nothing(self):
        os.remove(os.path.join(self.frames, "m-tt-e25-a180.jpg"))
        out = os.path.join(self.t.name, "stage")
        self.assertEqual(tp.main(["stage", self.frames, self.cfgp, out]), 1)
        self.assertFalse(os.path.exists(out))

    def test_stage_is_an_artifact_body(self):
        out = os.path.join(self.t.name, "stage")
        self.assertEqual(tp.main(["stage", self.frames, self.cfgp, out]), 0)
        page = open(os.path.join(out, "index.html")).read()
        self.assertTrue(page.startswith("<title>Test Turntable</title>"))
        self.assertNotIn("__BASE__", page); self.assertIn('fetch("turntable.json")', page)
        self.assertEqual(len(os.listdir(os.path.join(out, "frames"))), 8)
        self.assertNotIn("blurb", json.load(open(os.path.join(out, "turntable.json"))))

    def test_publish_passes_the_index_check_and_is_repeatable(self):
        args = ["publish", self.frames, self.cfgp, self.pages, "tt", "--release", "r1", "--upload", "0"]
        self.assertEqual(tp.main(args), 0)
        page = open(os.path.join(self.pages, "tt.html")).read()
        self.assertTrue(page.startswith("<!doctype html>")); self.assertIn('fetch("tt/turntable.json")', page)
        self.assertEqual(check_index.problems(self.pages), [])
        assets = json.load(open(os.path.join(self.pages, "assets.json")))["assets"]
        self.assertEqual(len(assets), 1); self.assertEqual(assets[0]["into"], "tt")
        self.assertTrue(os.path.isfile(os.path.join(self.run, assets[0]["asset"])))
        self.assertEqual(tp.main(args), 0)                   # again: same zip, one entry, one index line
        again = json.load(open(os.path.join(self.pages, "assets.json")))["assets"]
        self.assertEqual(again, assets)
        self.assertEqual(open(os.path.join(self.pages, "index.html")).read().count('href="tt.html"'), 1)


if __name__ == "__main__":
    unittest.main(buffer=True)
