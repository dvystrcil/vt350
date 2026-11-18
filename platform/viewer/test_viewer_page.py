# Tests for viewer_page.py and the shared sitepub helpers (no network: --upload 0).
#   python3 platform/viewer/test_viewer_page.py
import json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "pages"))
import viewer_page as vp
import check_index, sitepub

CFG = {"title": "VT350 ·", "title_accent": "test head", "model": "lite-1", "prefix": "m",
       "cam": {"pos": [1, 2, 3], "look": [0, 0, 0], "lens_mm": 35}, "caption": "c", "about": "a", "credits": "cr",
       "links": [{"href": "index.html", "text": "All"}], "page_title": "Test Viewer", "blurb": "b", "issue": "x#1"}
INDEX = ('<!doctype html><html><meta charset="utf-8"><title>Index</title>\n<main>\n  <ul class="pages">\n'
         '  </ul>\n</main>\n')


class ViewerPage(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); d = self.t.name
        self.run = os.path.join(d, "run"); os.makedirs(self.run)
        self.glb = os.path.join(self.run, "m.glb"); open(self.glb, "wb").write(b"glTF\x02\x00\x00\x00")
        self.jpg = os.path.join(self.run, "c.jpg"); open(self.jpg, "wb").write(b"\xff\xd8jpg")
        self.cfgp = os.path.join(d, "page.json"); json.dump(CFG, open(self.cfgp, "w"))
        self.pages = os.path.join(d, "pages"); os.makedirs(self.pages)
        open(os.path.join(self.pages, "index.html"), "w").write(INDEX)

    def tearDown(self): self.t.cleanup()

    def test_stage_is_an_artifact_body(self):
        out = os.path.join(self.t.name, "stage")
        self.assertEqual(vp.main(["stage", self.glb, self.jpg, self.cfgp, out]), 0)
        page = open(os.path.join(out, "index.html")).read()
        self.assertTrue(page.startswith("<title>Test Viewer</title>")); self.assertNotIn("__BASE__", page)
        self.assertEqual(json.load(open(os.path.join(out, "viewer.json")))["glb"], "m.glb")
        self.assertTrue(os.path.isfile(os.path.join(out, "render-compare.jpg")))

    def test_publish(self):
        args = ["publish", self.glb, self.jpg, self.cfgp, self.pages, "vw", "--release", "r1", "--upload", "0"]
        self.assertEqual(vp.main(args), 0)
        page = open(os.path.join(self.pages, "vw.html")).read()
        self.assertTrue(page.startswith("<!doctype html>")); self.assertIn('fetch("vw/viewer.json")', page)
        self.assertEqual(check_index.problems(self.pages), [])
        glb = json.load(open(os.path.join(self.pages, "vw", "viewer.json")))["glb"]
        self.assertRegex(glb, r"^m-vw-[0-9a-f]{8}\.glb$")
        self.assertTrue(os.path.isfile(os.path.join(self.run, glb)))
        self.assertEqual(json.load(open(os.path.join(self.pages, "assets.json")))["assets"][0]["asset"], glb)

    def test_publish_refuses_embedded_json(self):
        j = os.path.join(self.run, "m.gltf.json"); open(j, "w").write("{}")
        with self.assertRaises(SystemExit):
            vp.main(["publish", j, self.jpg, self.cfgp, self.pages, "vw", "--release", "r1", "--upload", "0"])


class SetAsset(unittest.TestCase):
    def test_one_entry_per_folder_and_type(self):
        with tempfile.TemporaryDirectory() as d:
            m = os.path.join(d, "assets.json")
            sitepub.set_asset(m, {"release": "r", "asset": "a-1.zip", "into": "x", "sha256": "1"})
            sitepub.set_asset(m, {"release": "r", "asset": "b-1.glb", "into": "x", "sha256": "2"})
            sitepub.set_asset(m, {"release": "r", "asset": "a-2.zip", "into": "x", "sha256": "3"})
            got = sorted(a["asset"] for a in json.load(open(m))["assets"])
            self.assertEqual(got, ["a-2.zip", "b-1.glb"])


if __name__ == "__main__":
    unittest.main(buffer=True)
