"""render.py writes the README images (homelab#1961 AC8).

cad/README.md shows renders/<model>-obico.jpg and renders/<model>-outside.jpg:
1920x1080 JPEGs at quality 85 (2.4 MB PNGs would bloat this public repo's
history on every re-render). render.py keeps the PNG as the lossless master and
writes that JPEG next to it, so a render, on the laptop or in the batch lane,
produces files that drop straight into cad/renders/.

Needs Blender, so it is not in the render-colours CI job (that one is stdlib-only):

    python3 cad/render/test_render.py                     # `blender` on PATH
    VT350_BLENDER="docker run --rm -v /tmp:/tmp -v $PWD:$PWD -w $PWD --entrypoint blender gpu-batch-blender:local" \\
        python3 cad/render/test_render.py                 # the batch lane's image

It renders a one-box fixture scene at 1 sample on the CPU (~1 min), not a model.
"""
import json, os, shlex, struct, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = shlex.split(os.environ.get("VT350_BLENDER", "blender"))

# IJG's standard luminance table (natural order); libjpeg's jpeg_set_quality(q) scales it.
IJG_LUMA = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56,
            14, 17, 22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
            49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99]


def ijg_table(q):
    scale = 5000 // q if q < 50 else 200 - 2 * q
    return [min(255, max(1, (v * scale + 50) // 100)) for v in IJG_LUMA]


def jpeg_info(data):
    """(width, height, luminance quant table as a sorted list) of a baseline JPEG, or None."""
    if data[:2] != b"\xff\xd8":
        return None
    i, dims, luma = 2, None, None
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return None
        marker, seg = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        body = data[i + 4:i + 2 + seg]
        if marker == 0xDB:                                   # DQT: one or more tables
            j = 0
            while j < len(body):
                pq, tq = body[j] >> 4, body[j] & 15
                n = 128 if pq else 64
                if tq == 0:
                    luma = sorted(body[j + 1:j + 1 + n])
                j += 1 + n
        elif marker in (0xC0, 0xC1, 0xC2):                   # SOF
            h, w = struct.unpack(">HH", body[1:5])
            dims = (w, h)
        elif marker == 0xDA:                                 # scan data follows
            break
        i += 2 + seg
    return (dims[0], dims[1], luma) if dims and luma else None


def write_fixture(src, labels=("box",)):
    """A scene.json + one 200 mm box, the shape export_meshes.py writes."""
    x0, y0, z0, s = -345.0, 50.0, 200.0, 200.0
    v = [(x0 + dx * s, y0 + dy * s, z0 + dz * s) for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)]
    faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
             (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    with open(os.path.join(src, "box.stl"), "w") as f:
        f.write("solid box\n")
        for a, b, c in faces:
            f.write("facet normal 0 0 0\nouter loop\n")
            for k in (a, b, c):
                f.write("vertex %f %f %f\n" % v[k])
            f.write("endloop\nendfacet\n")
        f.write("endsolid box\n")
    scene = {"model": "fixture.FCStd",
             "buckets": {"box": {"material": "", "labels": list(labels), "color": [0.6, 0.6, 0.6]}},
             "lights": [{"label": "strip", "bbox": [-445, -45, 500, 516, 640, 648]}],
             "camera": {"pos": [-245, -52, 628], "dir": [0, 0.6, -0.8], "fov_diag_deg": 96}}
    with open(os.path.join(src, "scene.json"), "w") as f:
        json.dump(scene, f)


class RenderWritesReadmeImages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vt350-render-test-")
        src, cls.out = os.path.join(cls.tmp, "export"), os.path.join(cls.tmp, "out")
        os.makedirs(src)
        write_fixture(src)
        cls.blender = subprocess.run(BLENDER + ["-b", "--python-exit-code", "1", "-P", os.path.join(HERE, "render.py"),
                                            "--", src, cls.out, "1"], capture_output=True, text=True)

    def test_blender_ran(self):
        self.assertEqual(self.blender.returncode, 0, self.blender.stdout[-3000:] + self.blender.stderr[-3000:])

    def test_png_master_per_view(self):
        for view in ("obico", "outside"):
            with open(os.path.join(self.out, f"fixture-{view}.png"), "rb") as f:
                head = f.read(24)
            self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n", view)
            self.assertEqual(struct.unpack(">II", head[16:24]), (1920, 1080), view)

    def test_readme_jpeg_per_view(self):
        for view in ("obico", "outside"):
            path = os.path.join(self.out, f"fixture-{view}.jpg")
            self.assertTrue(os.path.isfile(path), f"{path} missing; out/ has {sorted(os.listdir(self.out))}")
            with open(path, "rb") as f:
                info = jpeg_info(f.read())
            self.assertIsNotNone(info, f"{path} is not a JPEG")
            w, h, luma = info
            self.assertEqual((w, h), (1920, 1080), view)
            self.assertEqual(luma, sorted(ijg_table(85)), f"{view}: not quality 85, the README images' quality")

    def test_render_reports_each_file(self):
        for view in ("obico", "outside"):
            for ext in ("png", "jpg"):
                self.assertIn(f"wrote {os.path.join(self.out, f'fixture-{view}.{ext}')}", self.blender.stdout)

    def test_no_low_views_without_a_stand(self):
        self.assertFalse([n for n in os.listdir(self.out) if "-low_" in n])


class LowViewsWhenTheModelStandsOnABoard(unittest.TestCase):
    """#83/#74: a model with the stand (base board + feet) also gets two low views of the base and the
    recessed filter (low_front, low_side); the README pair is unchanged."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vt350-render-test-")
        src, cls.out = os.path.join(cls.tmp, "export"), os.path.join(cls.tmp, "out")
        os.makedirs(src)
        write_fixture(src, labels=("Base board (18 mm, plywood/MDF, placeholder)",))
        cls.blender = subprocess.run(BLENDER + ["-b", "--python-exit-code", "1", "-P", os.path.join(HERE, "render.py"),
                                            "--", src, cls.out, "1"], capture_output=True, text=True)

    def test_low_views_written(self):
        self.assertEqual(self.blender.returncode, 0, self.blender.stdout[-3000:] + self.blender.stderr[-3000:])
        for view in ("obico", "outside", "low_front", "low_side"):
            for ext in ("png", "jpg"):
                self.assertTrue(os.path.isfile(os.path.join(self.out, f"fixture-{view}.{ext}")), (view, ext))


class JpegInfoReadsTheReadmeImages(unittest.TestCase):
    """The parser above, against the JPEGs already in cad/renders (made at quality 85)."""

    def test_committed_readme_images(self):
        renders = os.path.join(HERE, "..", "renders")
        names = [n for n in sorted(os.listdir(renders)) if n.endswith(".jpg")]
        self.assertTrue(names)
        for n in names:
            with open(os.path.join(renders, n), "rb") as f:
                w, h, luma = jpeg_info(f.read())
            self.assertEqual((w, h), (1920, 1080), n)
            self.assertEqual(luma, sorted(ijg_table(85)), n)

    def test_not_a_jpeg(self):
        self.assertIsNone(jpeg_info(b"\x89PNG\r\n\x1a\n" + b"\0" * 16))


if __name__ == "__main__":
    unittest.main(verbosity=2)
