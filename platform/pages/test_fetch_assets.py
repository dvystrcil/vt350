# Tests for fetch_assets.py (no network: --from-dir).   python3 platform/pages/test_fetch_assets.py
import hashlib, json, os, sys, tempfile, unittest, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_assets


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f: f.write(data)


class FetchAssets(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = self.t.name
        self.src = os.path.join(self.d, "src"); self.site = os.path.join(self.d, "site")
        os.makedirs(self.src)
        with zipfile.ZipFile(os.path.join(self.src, "frames.zip"), "w") as z:
            z.writestr("frames/a.jpg", b"a"); z.writestr("frames/b.jpg", b"bb")
        write(os.path.join(self.src, "model.glb"), b"glTF....")
        os.makedirs(self.site)

    def tearDown(self): self.t.cleanup()

    def manifest(self, **over):
        entries = [{"release": "r1", "asset": "frames.zip", "into": "tt",
                    "sha256": fetch_assets.sha256(os.path.join(self.src, "frames.zip"))},
                   {"release": "r1", "asset": "model.glb", "into": "viewer",
                    "sha256": hashlib.sha256(b"glTF....").hexdigest()}]
        entries[1].update(over)
        p = os.path.join(self.site, "assets.json"); json.dump({"assets": entries}, open(p, "w")); return p

    def test_places_zip_and_file(self):
        self.assertEqual(fetch_assets.run(self.manifest(), from_dir=self.src), [])
        self.assertEqual(open(os.path.join(self.site, "tt/frames/b.jpg"), "rb").read(), b"bb")
        self.assertTrue(os.path.isfile(os.path.join(self.site, "viewer/model.glb")))

    def test_wrong_sha_fails_and_places_nothing(self):
        problems = fetch_assets.run(self.manifest(sha256="0" * 64), from_dir=self.src)
        self.assertEqual(len(problems), 1); self.assertIn("model.glb: sha256", problems[0])
        self.assertFalse(os.path.exists(os.path.join(self.site, "viewer")))
        self.assertFalse(os.path.exists(os.path.join(self.site, "tt")))   # the good asset isn't placed either

    def test_missing_asset_fails(self):
        self.assertIn("missing", fetch_assets.run(self.manifest(asset="nope.glb"), from_dir=self.src)[0])

    def test_zip_escaping_its_folder_is_refused(self):
        with zipfile.ZipFile(os.path.join(self.src, "frames.zip"), "w") as z: z.writestr("../evil.txt", b"x")
        with self.assertRaises(ValueError): fetch_assets.run(self.manifest(), from_dir=self.src)
        self.assertFalse(os.path.exists(os.path.join(self.site, "evil.txt")))

    def test_main_prints_marker(self):
        self.assertEqual(fetch_assets.main([self.manifest(), "--from-dir", self.src]), 0)


if __name__ == "__main__":
    unittest.main()
